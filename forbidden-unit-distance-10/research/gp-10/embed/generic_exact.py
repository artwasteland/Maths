"""Resumable graph6 input mode for G118 images and framed/pinned exact solving."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import time
from msolve_exact import limits,sha,invoke,decode_output,certify,parse_literal
from exact import verify,graph6,adjacency,textq
from hosts import database,monomorphism,check_mapping
from gp_field import program
from rigid_system import generic_rank,make_system,seed_for
from round2 import stored_system,load_system,write_json,task_id,HERE
from round2_phase import isolated


def allowed_output(path):
    path=Path(path).resolve()
    if not any(path.is_relative_to(root) for root in (HERE,Path('/tmp/gp10-embed'))):
        raise ValueError('output:outside_module_or_scratch')
    return path


def read_codes(path):
    raw=Path(path).read_bytes();codes=[]
    for line in raw.decode('ascii').splitlines():
        code=line.strip()
        if code.startswith('>>graph6<<'):code=code[len('>>graph6<<'):]
        if not code:continue
        graph6(code)
        if code not in codes:codes.append(code)
    return codes,sha(raw)


def plan(input_path,out,config):
    codes,digest=read_codes(input_path);manifest=out/'manifest.json'
    if manifest.exists():
        saved=json.loads(manifest.read_text())
        if saved['input_sha256']!=digest or saved['config']!=config:raise ValueError('resume:input_or_config_changed')
        return json.loads((out/'order.json').read_text())
    rows=[]
    for code in codes:
        n,edges=graph6(code)
        try:
            rank,evidence=generic_rank(code) if edges and n>=2 else (0,{'edgeless':True})
            row={'g6':code,'rank':rank,'k':max(0,2*n-3-rank),'rank_evidence':evidence}
        except Exception as exc:row={'g6':code,'rank':None,'k':None,'rank_error':str(exc)}
        rows.append(row)
    rows.sort(key=lambda row:(row['k'] if row['k'] is not None else 100000,row['g6']))
    write_json(out/'order.json',rows)
    (out/'input.g6').write_text(''.join(row['g6']+'\n' for row in rows))
    write_json(manifest,{'input_source':str(Path(input_path).resolve()),'input_sha256':digest,
        'unique_graphs':len(rows),'order':'increasing generic degrees of freedom, then graph6','config':config})
    return rows


def frame_variants(code,k,frames=3,pins=2):
    n,edges=graph6(code);order=list(edges)
    random.Random(seed_for(code)+49979687).shuffle(order)
    selected=[edges[0]]+[edge for edge in order if edge!=edges[0]]
    selected=selected[:frames]
    return [{'frame':list(edge),'variant':i*pins+j} for i,edge in enumerate(selected) for j in range(pins if k else 1)]


def remaining(deadline):
    value=deadline-time.monotonic()
    if value<=0:raise TimeoutError('method:wall_budget_exhausted')
    return value


def gp_output(code,out,points):
    lines=out.splitlines()
    if not lines or lines[-1]!='GP_FIELD_OK':raise ValueError('pari:missing_exact_success')
    def item(label):
        found=[line[len(label):] for line in lines if line.startswith(label)]
        if len(found)!=1:raise ValueError('pari:output_field')
        return parse_literal(found[0]+':')
    coeff=item('GP_FIELD_POLY ');interval=item('GP_FIELD_INTERVAL ');coords=item('GP_FIELD_COORDS ')
    if not all(type(c) is int for c in coeff):raise ValueError('pari:noninteger_polynomial')
    cert={'type':'exact','field':{'minpoly':coeff,'interval':[textq(str(v)) for v in interval]},
        'coords':[[[textq(str(v)) for v in coords[2*i+j]] for j in (0,1)] for i in range(points)]}
    return verify(code,cert,max_refinements=256)


def host_stage(code,directory,host,seconds):
    began=time.monotonic();deadline=began+seconds;meta={'method':'G118_image','cap_seconds':seconds};cert=None
    directory.mkdir(parents=True,exist_ok=True)
    try:
        n,edges=graph6(code);pattern=adjacency(n,edges)
        mapping,nodes=isolated(lambda:monomorphism(pattern,host['adj'],2000000),min(3.0,remaining(deadline)))
        meta.update(map=mapping,mapping_nodes=nodes)
        if mapping is None:raise ValueError('host:map_node_cap' if nodes>2000000 else 'host:no_map')
        check_mapping(pattern,host['adj'],mapping)
        points=[host['expressions'][i] for i in mapping]
        write_json(directory/'proposal.json',{'g6':code,'map':mapping,'expressions':points})
        source=isolated(lambda:program(points),min(1.5,remaining(deadline)))
        seed=int(sha(code.encode())[:16],16);source='setrand('+str(seed)+');\n'+source
        script=directory/'field.gp';script.write_text(source)
        call_cap=max(.001,remaining(deadline)-min(1.0,remaining(deadline)/4))
        started=time.monotonic()
        with (directory/'field.log').open('w') as stdout,(directory/'field.stderr').open('w') as stderr:
            child=subprocess.Popen(['gp','-fq','-s','128000000',str(script)],stdout=stdout,stderr=stderr)
            try:status=child.wait(timeout=call_cap);timed_out=False
            except subprocess.TimeoutExpired:child.kill();status=child.wait();timed_out=True
            except BaseException:child.kill();child.wait();raise
        meta.update(pari_seconds=time.monotonic()-started,pari_cap_seconds=call_cap,returncode=status,timeout=timed_out,seed=seed,threads=1,input_sha256=sha(source.encode()))
        if timed_out:raise TimeoutError('pari:timeout')
        if status:raise ValueError('pari:child_exit:'+str(status))
        output=directory/'field.log'
        if output.stat().st_size>8*1024*1024:raise ValueError('pari:output_size')
        raw=output.read_text();meta['output_sha256']=sha(raw.encode())
        cert=isolated(lambda:gp_output(code,raw,n),remaining(deadline))
        meta.update(reason='exact_embedding',degree=len(cert['field']['minpoly'])-1)
    except Exception as exc:meta['reason']=type(exc).__name__+':'+str(exc)[:300]
    meta['wall_seconds']=time.monotonic()-began;write_json(directory/'stats.json',meta)
    return cert,meta


def msolve_stage(code,directory,k,seconds,frames,pins):
    began=time.monotonic();deadline=began+seconds;meta={'method':'framed_pinned_msolve','cap_seconds':seconds,'attempts':[],'triage':False};cert=None
    directory.mkdir(parents=True,exist_ok=True)
    try:
        if k is None:raise ValueError('rigidity:unsupported_graph')
        variants=frame_variants(code,k,frames,pins)
        for i,variant in enumerate(variants):
            if deadline-time.monotonic()<.05:break
            target=directory/f'attempt-{i:02d}';target.mkdir(exist_ok=True)
            row={'frame':variant['frame'],'variant':variant['variant'],'k':k,'triage':False};started=time.monotonic()
            try:
                saved=isolated(lambda:stored_system(make_system(code,frame=variant['frame'],variant=variant['variant'])),min(2.5,remaining(deadline)))
                write_json(target/'system.json',saved);system=load_system(target/'system.json');row['pins']=system['pins']
                left=remaining(deadline);cap=max(.001,(left-min(2.0,left/4))/(len(variants)-i))
                raw,call=invoke(system,target,cap,parse=False);row.update(call)
                if raw is not None:
                    def check():
                        parsed=decode_output(raw,system['variables'],progress=lambda p:write_json(target/'conversion-progress.json',p))
                        return certify(code,system,parsed)
                    cert,checked=isolated(check,min(5.0,remaining(deadline)));row.update(checked)
                if row.get('triage'):meta['triage']=True
            except Exception as exc:row['reason']=type(exc).__name__+':'+str(exc)[:400]
            progress=target/'conversion-progress.json'
            if progress.exists():
                for key,value in json.loads(progress.read_text()).items():row.setdefault(key,value)
            row['wall_seconds']=time.monotonic()-started;meta['attempts'].append(row);write_json(target/'stats.json',row)
            if cert is not None or meta['triage']:break
        meta['reason']='exact_embedding' if cert is not None else ('rigid_no_distinct_real_solution' if meta['triage'] else 'no_certificate_within_budget')
    except Exception as exc:meta['reason']=type(exc).__name__+':'+str(exc)[:300]
    meta['wall_seconds']=time.monotonic()-began
    if cert is not None:meta['degree']=len(cert['field']['minpoly'])-1
    write_json(directory/'stats.json',meta);return cert,meta


def one(row,out,config,host):
    code=row['g6'];directory=out/'graphs'/task_id(code);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'record.json').exists():
        record=json.loads((directory/'record.json').read_text());stats=json.loads((directory/'stats.json').read_text())
        if record['g6']!=code:raise ValueError('resume:graph_mismatch')
        if record['verdict']=='embedded':verify(code,record['cert'],max_refinements=256)
        return record,stats,True
    began=time.monotonic();stats=dict(row,stages=[],triage=False);cert=None;n,edges=graph6(code)
    if n<=2 or not edges:
        coords=[[[textq(v if edges else 3*v)],[textq(0)]] for v in range(n)]
        cert=verify(code,{'type':'exact','field':{'minpoly':[0,1],'interval':['-1/1','1/1']},'coords':coords})
        stats['reason']='rational_trivial_graph'
    else:
        for method in config['methods']:
            if method=='g118':cert,meta=host_stage(code,directory/'g118',host,config['host_cap'])
            else:cert,meta=msolve_stage(code,directory/'msolve',row['k'],config['msolve_cap'],config['frames'],config['pins'])
            stats['stages'].append(meta);stats['triage']|=meta.get('triage',False)
            if cert is not None:stats.update(reason='exact_embedding',method=method,degree=len(cert['field']['minpoly'])-1);break
        if cert is None:stats['reason']='rigid_no_distinct_real_solution' if stats['triage'] else 'no_certificate_within_budget'
    stats['wall_seconds']=time.monotonic()-began
    record={'g6':code,'verdict':'embedded','cert':cert} if cert is not None else {'g6':code,'verdict':'unknown','cert':{'reason':stats['reason'],'budget':dict(config,wall_seconds=stats['wall_seconds'])}}
    write_json(directory/'stats.json',stats);write_json(directory/'record.json',record)
    return record,stats,False


def run(input_path,out,methods=('g118','msolve'),start=0,stop=None,msolve_cap=20.,host_cap=10.,frames=3,pins=2):
    limits();out=allowed_output(out);out.mkdir(parents=True,exist_ok=True)
    config={'methods':list(methods),'msolve_cap':float(msolve_cap),'host_cap':float(host_cap),'frames':frames,'pins':pins,'process_ceiling':2,'address_space_bytes':1024000000}
    if any(m not in ('g118','msolve') for m in methods) or len(set(methods))!=len(methods):raise ValueError('method:invalid')
    if min(msolve_cap,host_cap,frames,pins)<=0:raise ValueError('budget:nonpositive')
    rows=plan(input_path,out,config);stop=len(rows) if stop is None else min(stop,len(rows))
    import sympy
    import scipy.optimize
    host=database()['G118'] if 'g118' in methods else None;began=time.monotonic();counts={};fresh=0
    # Rebuild from the durable per-graph files before appending fresh records.
    existing=[]
    for row in rows:
        file=out/'graphs'/task_id(row['g6'])/'record.json'
        if file.exists():existing.append(json.loads(file.read_text()))
    (out/'records.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in existing))
    with (out/'records.jsonl').open('a') as stream:
        for index,row in enumerate(rows[start:stop],start):
            record,stats,resumed=one(row,out,config,host);counts[record['verdict']]=counts.get(record['verdict'],0)+1
            if not resumed:stream.write(json.dumps(record,sort_keys=True)+'\n');stream.flush();fresh+=1
            print(json.dumps({'index':index,'g6':row['g6'],'k':row['k'],'verdict':record['verdict'],'method':stats.get('method'),'degree':stats.get('degree'),'triage':stats['triage'],'seconds':stats['wall_seconds'],'resumed':resumed}),flush=True)
    summary={'start':start,'stop':stop,'count':stop-start,'fresh':fresh,'counts':counts,'wall_seconds':time.monotonic()-began}
    write_json(out/'batches'/f'{start}-{stop}.json',summary);print(json.dumps({'batch':summary}),flush=True)


def cli(default_methods='g118,msolve'):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--out',required=True)
    p.add_argument('--methods',default=default_methods);p.add_argument('--start',type=int,default=0);p.add_argument('--stop',type=int)
    p.add_argument('--msolve-cap',type=float,default=20);p.add_argument('--host-cap',type=float,default=10)
    p.add_argument('--frames',type=int,default=3);p.add_argument('--pins',type=int,default=2);a=p.parse_args()
    run(a.input,a.out,a.methods.split(','),a.start,a.stop,a.msolve_cap,a.host_cap,a.frames,a.pins)


if __name__=='__main__':cli()
