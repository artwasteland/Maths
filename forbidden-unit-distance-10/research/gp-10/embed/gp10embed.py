#!<repo>/pyenv-gp10/bin/python
"""Bounded exact embedding producer, with one isolated child at a time."""
from __future__ import annotations
import os
os.environ['SYMPY_GROUND_TYPES']='python'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import resource
import signal
import sys
import time
from contextlib import contextmanager
from exact import graph6, verify, CertificateError

METHODS=('lattice18','lattice36','lattice30','constructive','host','numeric')
WEIGHTS={'lattice18':3,'lattice36':2,'lattice30':1,'constructive':2,'host':3,'numeric':3}
MEMORY_BYTES=1000000*1024

from budget import StageTimeout

def limits():
    current=os.getpriority(os.PRIO_PROCESS,0)
    if current<15:os.nice(15-current)
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    cap=min(MEMORY_BYTES,hard) if hard!=resource.RLIM_INFINITY else MEMORY_BYTES
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

@contextmanager
def timer(seconds):
    def expire(signum,frame):raise StageTimeout()
    old=signal.signal(signal.SIGALRM,expire)
    signal.setitimer(signal.ITIMER_REAL,max(seconds,0.000001))
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)

def propose(method,code,n,edges,seed,node_cap):
    if method.startswith('lattice'):
        from lattice import search
        return search(n,edges,seed,method,node_cap)
    if method=='constructive':
        from algebraic import constructive
        return constructive(n,edges,seed,node_cap)
    if method=='host':
        from hosts import search
        return search(n,edges,seed,node_cap*20)
    if method=='numeric':
        from numeric import search
        return search(code,n,edges,seed)
    raise ValueError('method:unknown')

def worker(conn,code,options,callback=None):
    started=time.monotonic()
    try:
        limits()
        n,edges=graph6(code)
        if n>64:raise ValueError('search:vertex_cap')
        seed=int.from_bytes(hashlib.sha256(code.encode('ascii')).digest(),'big')
        methods=options['methods'];total_weight=sum(WEIGHTS[m] for m in methods)
        attempts=[]
        for method in methods:
            left=options['time_limit']-(time.monotonic()-started)
            if left<=0:break
            allocation=left*WEIGHTS[method]/total_weight
            total_weight-=WEIGHTS[method]
            conn.send({'event':'start','method':method,'limit_seconds':allocation})
            t=time.monotonic();candidate=None;meta={}
            try:
                with timer(allocation):
                    if callback is not None:
                        candidate,meta=callback(method,code,n,edges,seed,options['node_cap'])
                    else:
                        candidate,meta=propose(method,code,n,edges,seed,options['node_cap'])
                    if candidate is not None:
                        candidate=verify(code,candidate)
            except StageTimeout:
                candidate=None;meta={'reason':'method_timeout'}
            except MemoryError:
                candidate=None;meta={'reason':'memory_limit'}
            except CertificateError as exc:
                candidate=None;meta={'reason':'self_check:'+str(exc)}
            except Exception as exc:
                candidate=None;meta={'reason':'method_exception:'+type(exc).__name__+':'+str(exc)[:200]}
            attempt=dict(meta,method=method,seconds=time.monotonic()-t,limit_seconds=allocation)
            attempts.append(attempt);conn.send({'event':'attempt','attempt':attempt})
            if candidate is not None:
                conn.send({'event':'result','record':{'g6':code,'verdict':'embedded','cert':candidate},
                           'method':method,'attempts':attempts})
                return
        conn.send({'event':'result','record':{'g6':code,'verdict':'unknown',
                   'cert':{'reason':'search_exhausted','budget':{}}},'attempts':attempts})
    except BaseException as exc:
        try:
            conn.send({'event':'result','record':{'g6':code,'verdict':'unknown',
                'cert':{'reason':'worker_exception:'+type(exc).__name__+':'+str(exc)[:200],'budget':{}}}})
        except BaseException:pass
    finally:conn.close()

def run_one(code,time_limit=1.0,methods=METHODS,node_cap=20000,callback=None):
    """Parent survives a segfault, OOM or hard timeout in the sole worker."""
    started=time.monotonic();ctx=mp.get_context('fork');reader,writer=ctx.Pipe(duplex=False)
    options={'time_limit':time_limit,'methods':list(methods),'node_cap':node_cap}
    process=ctx.Process(target=worker,args=(writer,code,options,callback))
    try:
        process.start()
    except Exception as exc:
        reader.close();writer.close()
        budget={'limit_seconds':time_limit,'wall_seconds':time.monotonic()-started,
                'node_cap':node_cap,'memory_bytes':MEMORY_BYTES,'attempts':[],
                'seed_sha256':hashlib.sha256(code.encode()).hexdigest()}
        record={'g6':code,'verdict':'unknown','cert':{'reason':'worker_start:'+type(exc).__name__,'budget':budget}}
        return record,{'g6':code,'verdict':'unknown','method':None,'budget':budget}
    writer.close()
    attempts=[];result=None;active=None;failure=None
    try:
        while True:
            remaining=time_limit-(time.monotonic()-started)
            if remaining<=0:
                failure='timeout';break
            if reader.poll(min(remaining,0.02)):
                try:event=reader.recv()
                except (EOFError,OSError):
                    failure='worker_crash';break
                if event['event']=='start':active=event
                elif event['event']=='attempt':
                    attempts.append(event['attempt']);active=None
                elif event['event']=='result':
                    result=event;break
            if not process.is_alive():
                if reader.poll():continue
                failure='worker_crash';break
    finally:
        if process.is_alive():
            # A completed worker has no further computation to preserve.
            process.kill()
        process.join();reader.close()
    budget={'limit_seconds':time_limit,'wall_seconds':time.monotonic()-started,
            'node_cap':node_cap,'memory_bytes':MEMORY_BYTES,
            'seed_sha256':hashlib.sha256(code.encode()).hexdigest(),'attempts':attempts}
    if active is not None:budget['interrupted_method']=active['method']
    if result is None:
        record={'g6':code,'verdict':'unknown','cert':{'reason':failure or 'worker_crash','budget':budget}}
        budget['worker_exitcode']=process.exitcode
        method=None
    else:
        record=result['record'];method=result.get('method')
        if record['verdict']=='unknown':record['cert']['budget']=budget
    stats={'g6':code,'verdict':record['verdict'],'method':method,'budget':budget}
    return record,stats

def recover_output(path):
    """Discard only a malformed final fragment left by a killed writer."""
    if not path.exists():return []
    with path.open('r+b') as handle:
        handle.seek(0,2);end=handle.tell()
        if end:
            handle.seek(end-1)
            if handle.read(1)!=b'\n':
                block_end=end;start=0
                while block_end:
                    block_start=max(0,block_end-8192)
                    handle.seek(block_start);block=handle.read(block_end-block_start)
                    offset=block.rfind(b'\n')
                    if offset>=0:
                        start=block_start+offset+1;break
                    block_end=block_start
                handle.seek(start);tail=handle.read(end-start)
                try:json.loads(tail)
                except (ValueError,UnicodeError):handle.truncate(start)
                else:
                    handle.seek(end);handle.write(b'\n')
    records=[];seen=set()
    with path.open('rb') as handle:
        for line in handle:
            r=json.loads(line)
            if r.get('verdict') not in ('embedded','unknown') or not isinstance(r.get('g6'),str) or r['g6'] in seen:
                raise ValueError('resume:invalid_or_duplicate_record')
            if r['verdict']=='embedded':verify(r['g6'],r['cert'])
            elif (not isinstance(r.get('cert',{}).get('budget'),dict)
                  or not isinstance(r.get('cert',{}).get('reason'),str)):
                raise ValueError('resume:missing_reason_or_budget')
            records.append({'g6':r['g6'],'verdict':r['verdict']});seen.add(r['g6'])
    return records

def warm(methods):
    # Imported once in the parent so short graph budgets measure searches.
    if any(m in methods for m in ('constructive','host','numeric')):
        import sympy
    if 'host' in methods:
        from hosts import database
        database()
    if 'numeric' in methods:
        import scipy.optimize

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--unknown',type=Path,required=True)
    parser.add_argument('--time-limit',type=float,required=True)
    parser.add_argument('--methods',default=','.join(METHODS))
    parser.add_argument('--node-cap',type=int,default=20000)
    parser.add_argument('--stats',type=Path)
    args=parser.parse_args(argv)
    methods=tuple(args.methods.split(','))
    if (not math.isfinite(args.time_limit) or args.time_limit<=0 or args.node_cap<1
            or not methods or len(set(methods))!=len(methods) or any(m not in METHODS for m in methods)):
        parser.error('positive finite limits and unique known methods are required')
    paths=[args.input.resolve(),args.out.resolve(),args.unknown.resolve()]
    if args.stats:paths.append(args.stats.resolve())
    if len(set(paths))!=len(paths):parser.error('input, output, unknown and stats paths must differ')
    limits();warm(methods)
    records=recover_output(args.out);seen={r['g6'] for r in records}
    # Rebuild the projection on every resume. It can lag the record stream
    # after a crash between the two writes.
    args.unknown.parent.mkdir(parents=True,exist_ok=True)
    temp=args.unknown.with_name(args.unknown.name+'.repair')
    temp.write_text(''.join(r['g6']+'\n' for r in records if r['verdict']=='unknown'))
    temp.replace(args.unknown)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.stats:args.stats.parent.mkdir(parents=True,exist_ok=True)
    stats_file=args.stats.open('a') if args.stats else None
    try:
        with args.input.open() as source,args.out.open('a') as output,args.unknown.open('a') as unknown:
            for raw in source:
                code=raw.strip()
                if not code or code=='>>graph6<<':continue
                if code in seen:continue
                record,stats=run_one(code,args.time_limit,methods,args.node_cap)
                output.write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n');output.flush()
                if record['verdict']=='unknown':unknown.write(code+'\n');unknown.flush()
                if stats_file:stats_file.write(json.dumps(stats,separators=(',',':'),allow_nan=False)+'\n');stats_file.flush()
                seen.add(code)
    finally:
        if stats_file:stats_file.close()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
