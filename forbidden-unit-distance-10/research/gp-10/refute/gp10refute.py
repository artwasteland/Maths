#!<repo>/pyenv-gp10/bin/python
"""Bounded, resumable GP-10 refutation producer. See FORMAT.md and REPORT.md."""
from __future__ import annotations
import os
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import sys
sys.dont_write_bytecode = True
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import random
import resource
import signal
import tempfile
import time
from pathlib import Path
from graphs import (MODULE, SCRATCH, canonical, decode, patterns, seed,
                    tu_search, verify_tu, verify_tree, verify_sub, validate_forbidden, forbidden_canonical)
from algebra import algebra_search, verify_algebra

MEMORY = 1_000_000_000
METHODS = ("tu", "tree", "null", "real")
SELECTABLE_METHODS = METHODS + ("reuse", "dag", "portfolio")

class Deadline(Exception):
    pass

def configure():
    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 15:
        os.nice(15-current)
    soft,hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MEMORY if hard == resource.RLIM_INFINITY else min(MEMORY,hard)
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    SCRATCH.mkdir(exist_ok=True)

def alarm(signum, frame):
    raise Deadline("graph time limit")

@contextlib.contextmanager
def timed(seconds):
    old = signal.signal(signal.SIGALRM,alarm)
    signal.setitimer(signal.ITIMER_REAL,max(0.001,seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)

def verify(code,cert,forbidden,known):
    if cert.get("type")=="tree":
        verify_tree(code,cert)
    elif cert.get("type")=="sub":
        verify_sub(code,cert,forbidden,known)
    elif cert.get("type")=="tu":
        verify_tu(code,cert,forbidden,known)
    elif cert.get("type") in ("null-dag","real-dag"):
        from dag import verify_dag
        verify_dag(code,cert)
    else:
        verify_algebra(code,cert)

def tree_search(code,max_states):
    import amp_core as amp
    graph=amp.Graph.from_graph6(code)
    trace=amp.SearchTrace()
    cycles,rows=amp.four_cycle_rows(graph)
    initial=amp.canonical_matrix(rows,graph.n)
    budget=amp.SearchBudget(max_states,0,random.Random(seed(code)),trace)
    verdict,payload=amp.reduce_state(graph,initial,budget)
    detail={"states":trace.states_visited,"moves":dict(trace.moves),"stops":dict(trace.stops),
            "l3_triples":trace.l3_triples_tested,"initial_rank":initial.rows}
    if verdict!="refuted":
        return None,detail
    root=amp.state_node(graph,amp.sp.zeros(0,graph.n),{"kind":"L0"},[payload])
    cert={"type":"tree","witness":amp.refutation_certificate(root)}
    detail["checked_nodes"]=verify_tree(code,cert)
    return cert,detail

def isolated(function,seconds):
    # One child only. The TU/tree child never launches an external program.
    with tempfile.TemporaryDirectory(prefix="worker-",dir=SCRATCH) as tmp:
        path=Path(tmp)/"result.json"
        child=os.fork()
        if child==0:
            try:
                with timed(seconds):
                    cert,detail=function()
                result={"cert":cert,"detail":detail}
            except BaseException as exc:
                result={"cert":None,"detail":{"reason":type(exc).__name__+": "+str(exc)[:300]}}
            try:
                path.write_text(json.dumps(result,sort_keys=True))
            finally:
                os._exit(0)
        deadline=time.monotonic()+seconds+0.1
        try:
            while True:
                pid,status=os.waitpid(child,os.WNOHANG)
                if pid:
                    break
                if time.monotonic()>=deadline:
                    os.kill(child,signal.SIGKILL)
                    os.waitpid(child,0)
                    return None,{"reason":"timeout: worker killed"}
                time.sleep(0.005)
        except BaseException:
            with contextlib.suppress(ProcessLookupError):
                os.kill(child,signal.SIGKILL)
            with contextlib.suppress(ChildProcessError):
                os.waitpid(child,0)
            raise
        if not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0 or not path.exists():
            return None,{"reason":f"worker crash: wait status {status}"}
        result=json.loads(path.read_text())
        return result["cert"],result["detail"]

def run_method(code,method,seconds,forbidden=(),known=None,max_states=200,all_pairs=False,extra_sat=(),frame=None):
    known={} if known is None else known
    started=time.monotonic();stages=[]
    def record_stage(stage):stages.append({"stage":stage,"seconds":time.monotonic()-started})
    try:
        if method=="tu":
            validate_forbidden(forbidden)
            if forbidden:
                forbidden_canonical()
            cert,detail=isolated(lambda:(tu_search(code,forbidden,known),{}),seconds)
        elif method=="reuse":
            record=known.get(code)
            cert=record.get("cert") if isinstance(record,dict) else None
            detail={"reason":"checked prior certificate" if cert else "no checked prior certificate"}
        elif method=="tree":
            cert,detail=isolated(lambda:tree_search(code,max_states),seconds)
        else:
            with timed(seconds):
                cert,detail=algebra_search(code,"real" if method=="dag" else method,seconds,all_pairs,extra_sat=extra_sat,frame=frame,trace=record_stage,dag="auto" if method=="portfolio" else method=="dag")
        if cert is not None:
            # Tree verification already runs inside the same bounded worker.
            if method!="tree":
                with timed(max(0.001,seconds-(time.monotonic()-started))):
                    verify(code,cert,forbidden,known)
        detail={**detail,"method":method,"seconds":time.monotonic()-started,"limit":seconds,**({"stages":stages} if stages else {})}
        return cert,detail
    except (Exception,MemoryError) as exc:
        return None,{"method":method,"seconds":time.monotonic()-started,"limit":seconds,"stages":stages,
                     "reason":type(exc).__name__+": "+str(exc)[:300]}

def produce(code,seconds,forbidden,known,methods=METHODS,max_states=200,all_pairs=False,extra_sat=()):
    start=time.monotonic(); attempts=[]
    cert=None
    for i,method in enumerate(methods):
        remaining=seconds-(time.monotonic()-start)
        if remaining<=0:
            break
        allocation=remaining/(len(methods)-i)
        cert,detail=run_method(code,method,allocation,forbidden,known,max_states,all_pairs,extra_sat)
        attempts.append(detail)
        if cert is not None:
            break
    if cert is None:
        cert={"reason":"bounded methods exhausted", "budget":{"seconds":seconds,"max_states":max_states,
              "all_pairs":all_pairs,"extra_sat":list(extra_sat),"methods":list(methods),"attempts":attempts}}
        verdict="unknown"
    else:
        verdict="refuted"
    return {"g6":code,"verdict":verdict,"cert":cert},attempts

def load_known(path,forbidden):
    if path is None:
        return {}
    records={}
    for line in Path(path).read_text().splitlines():
        rec=json.loads(line)
        if rec.get("verdict")!="refuted":
            continue
        if rec["g6"] in records:
            raise ValueError("duplicate known record")
        records[rec["g6"]]=rec
    if canonical(list(records)) != list(records):
        raise ValueError("known records are not canonical")
    accepted,visiting={},set()
    def visit(code):
        if code in accepted:
            return
        if code in visiting:
            raise ValueError("known pointer cycle")
        visiting.add(code)
        cert=records[code]["cert"]
        if cert.get("type")=="tu" and "refuted" in cert.get("end",{}):
            h=cert["end"]["refuted"]
            if h not in records:
                raise ValueError("known pointer missing target")
            visit(h)
        if cert.get("type")=="sub" and "index" not in cert:
            h=cert["g6"]
            if h not in records:
                raise ValueError("known pointer missing target")
            visit(h)
        with timed(30):
            verify(code,cert,forbidden,accepted)
        visiting.remove(code);accepted[code]=records[code]
    for code in records:
        visit(code)
    return accepted

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def flush_line(handle,obj):
    handle.write(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n")
    handle.flush();os.fsync(handle.fileno())

def repair_tail(path):
    if not path.exists():
        return
    data=path.read_bytes()
    if data and not data.endswith(b"\n"):
        end=data.rfind(b"\n")+1
        try:
            json.loads(data[end:])
        except (ValueError,UnicodeDecodeError):
            with path.open("r+b") as handle:
                handle.truncate(end)
        else:
            with path.open("ab") as handle:
                handle.write(b"\n")

def main(argv=None):
    configure()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--unknown",type=Path,required=True)
    p.add_argument("--time-limit",type=float,required=True)
    p.add_argument("--forbidden",type=Path,required=True)
    p.add_argument("--refuted",type=Path)
    p.add_argument("--methods",default=",".join(METHODS))
    p.add_argument("--max-states",type=int,default=200)
    p.add_argument("--all-sat",action="store_true")
    p.add_argument("--extra-sat",type=int,nargs=2,action="append",default=[])
    args=p.parse_args(argv)
    methods=tuple(args.methods.split(","))
    if not math.isfinite(args.time_limit) or args.time_limit<=0 or args.max_states<1:
        p.error("positive finite limits required")
    if not methods or len(set(methods))!=len(methods) or any(m not in SELECTABLE_METHODS for m in methods):
        p.error("invalid methods")
    inputs={p.resolve() for p in [args.input,args.forbidden,args.refuted] if p is not None}
    outputs={args.out.resolve(),args.unknown.resolve()}
    if len(outputs)!=2 or inputs & outputs:
        p.error("input and output paths must be different")
    if "tree" in methods:
        import amp_core
    source=json.loads(args.forbidden.read_text())
    if not isinstance(source,list):
        p.error("forbidden list must be a JSON list")
    forbidden=patterns(source)
    validate_forbidden(forbidden)
    codes=canonical([s.strip() for s in args.input.read_text().splitlines() if s.strip() and s.strip()!=">>graph6<<"])
    if len(set(codes))!=len(codes):
        p.error("input has duplicate isomorphism classes")
    known=load_known(args.refuted,forbidden)
    meta={"input_sha256":digest(args.input),"forbidden_sha256":digest(args.forbidden),
          "known_sha256":digest(args.refuted) if args.refuted else None,
          "methods":methods,"seconds":args.time_limit,"states":args.max_states,"all_sat":args.all_sat,"extra_sat":args.extra_sat,
          "source_sha256":{f.name:digest(f) for f in sorted(MODULE.glob("*.py")) if f.name in
             {"gp10refute.py","graphs.py","amp_core.py","algebra.py","dag.py","quadratic_sos.py"}}}
    meta=json.loads(json.dumps(meta))
    for path in [args.out,args.unknown]:
        path.parent.mkdir(parents=True,exist_ok=True)
    meta_path=Path(str(args.out)+".meta.json")
    log_path=Path(str(args.out)+".timings.jsonl")
    pending_path=Path(str(args.out)+".pending.json")
    with Path(str(args.out)+".lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if meta_path.exists():
            if json.loads(meta_path.read_text())!=meta:
                raise ValueError("resume configuration or source changed; choose a new output")
        elif args.out.exists() and args.out.stat().st_size:
            raise ValueError("nonempty output without resume metadata")
        else:
            meta_path.write_text(json.dumps(meta,sort_keys=True,indent=2)+"\n")
        repair_tail(args.out);repair_tail(log_path)
        done=[]
        if args.out.exists():
            for line in args.out.read_text().splitlines():
                rec=json.loads(line)
                if len(done)>=len(codes) or rec["g6"]!=codes[len(done)]:
                    raise ValueError("resume coverage or order mismatch")
                if rec["verdict"]=="refuted":
                    with timed(30):
                        verify(rec["g6"],rec["cert"],forbidden,known)
                elif rec["verdict"]!="unknown":
                    raise ValueError("resume invalid verdict")
                done.append(rec)
        if pending_path.exists():
            pending=json.loads(pending_path.read_text())
            if pending.get("g6") not in codes:
                raise ValueError("pending graph is not in input")
            if pending["g6"] not in {rec["g6"] for rec in done}:
                if len(done)>=len(codes) or codes[len(done)]!=pending["g6"]:
                    raise ValueError("pending graph order mismatch")
                recovered={"g6":pending["g6"],"verdict":"unknown","cert":{
                    "reason":"producer interrupted while processing this graph; recovered on resume",
                    "budget":{"seconds":args.time_limit}}}
                with args.out.open("a") as output:
                    flush_line(output,recovered)
                done.append(recovered)
            pending_path.unlink()
        # Rebuild UNKNOWN from durable records, including after an interrupted write.
        with args.unknown.open("w") as unknown:
            for rec in done:
                if rec["verdict"]=="unknown":
                    unknown.write(rec["g6"]+"\n")
            unknown.flush();os.fsync(unknown.fileno())
            with args.out.open("a") as output,log_path.open("a") as timings:
                for code in codes[len(done):]:
                    with pending_path.open("w") as checkpoint:
                        flush_line(checkpoint,{"g6":code})
                    try:
                        rec,attempts=produce(code,args.time_limit,forbidden,known,methods,args.max_states,args.all_sat,args.extra_sat)
                    except Exception as exc:
                        rec={"g6":code,"verdict":"unknown","cert":{"reason":type(exc).__name__+": "+str(exc)[:300],
                             "budget":{"seconds":args.time_limit}}}
                        attempts=[]
                    flush_line(output,rec)
                    flush_line(timings,{"g6":code,"attempts":attempts})
                    if rec["verdict"]=="unknown":
                        unknown.write(code+"\n");unknown.flush();os.fsync(unknown.fileno())
                    pending_path.unlink()
                    # Only explicit --refuted records are search dependencies. This keeps
                    # results invariant under input order. Resume also validates earlier rows.
        print(json.dumps({"records":len(codes),"resumed":len(done),"out":str(args.out)}))
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (ValueError,OSError) as exc:
        print("gp10refute: "+str(exc),file=sys.stderr)
        raise SystemExit(2)
