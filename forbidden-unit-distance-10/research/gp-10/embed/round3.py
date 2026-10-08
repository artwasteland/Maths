"""GP host search on stated cohorts, with per-map exact conversion."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
from msolve_exact import limits,sha
from exact import verify,CertificateError,graph6,adjacency,rational,textq
from hosts import database,monomorphism,check_mapping
from gp_field import convert
from round2 import write_json,task_id
from round2_phase import isolated

HERE=Path(__file__).resolve().parent
OUT=HERE/'results/round3'


def controls():
    limits();checks=[]
    for name,points in [('triangle',[['0','0'],['1','0'],['1/2','sqrt(3)/2']]),
                        ('cancelled_extension',[['sqrt(2)-sqrt(2)','0'],['1','0'],['1/2','sqrt(3)/2']])]:
        cert,call=convert(points,OUT/'controls'/name,30,g6='Bw')
        cert=verify('Bw',cert);assert len(cert['field']['minpoly'])==3
        again,repeated=convert(points,OUT/'controls'/(name+'-repeat'),30,g6='Bw')
        assert again==cert and repeated['output_sha256']==call['output_sha256']
        bad=deepcopy(cert);bad['coords'][1][0][0]=textq(rational(bad['coords'][1][0][0])+1)
        try:verify('Bw',bad)
        except CertificateError as exc:reason=str(exc);assert reason.startswith('edge:0,1')
        else:raise AssertionError('mutation accepted')
        checks.append({'name':name,'positive':'PASS','red':'PASS','deterministic_repeat':'PASS','reason':reason,'seconds':call['seconds']+repeated['seconds']})
    write_json(OUT/'controls/pari-results.json',checks);print(json.dumps(checks),flush=True)


def solve(code,sample,host,seconds=180,node_cap=10000000):
    directory=OUT/sample/task_id(code);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'record.json').exists():
        record=json.loads((directory/'record.json').read_text());stats=json.loads((directory/'stats.json').read_text())
        if record['verdict']=='embedded':verify(code,record['cert'],max_refinements=256)
        return record,stats
    start=time.monotonic();stats={'g6':code,'sample':sample,'method':'G118_per_map','cap_seconds':seconds,'mapping_node_cap':node_cap}
    try:
        n,edges=graph6(code);pattern=adjacency(n,edges)
        mapping,nodes=isolated(lambda:monomorphism(pattern,host['adj'],node_cap),60)
        stats.update(map=mapping,mapping_nodes=nodes,mapping_seconds=time.monotonic()-start)
        if mapping is None:raise ValueError('host:no_map_within_node_cap' if nodes>node_cap else 'host:no_map_exhaustive')
        check_mapping(pattern,host['adj'],mapping)
        points=[host['expressions'][i] for i in mapping]
        write_json(directory/'proposal.json',{'g6':code,'host':'G118','map':mapping,'expressions':points})
        candidate,call=convert(points,directory,seconds,g6=code)
        candidate=verify(code,candidate,max_refinements=256)
        record={'g6':code,'verdict':'embedded','cert':candidate}
        stats.update(reason='exact_embedding',degree=len(candidate['field']['minpoly'])-1,pari_seconds=call['seconds'])
    except Exception as exc:
        stats['reason']=type(exc).__name__+':'+str(exc)
        record={'g6':code,'verdict':'unknown','cert':{'reason':stats['reason'],'budget':{'method':'G118_per_map','pari_cap_seconds':seconds,'mapping_node_cap':node_cap}}}
    stats['wall_seconds']=time.monotonic()-start
    if record['verdict']=='unknown':record['cert']['budget']['wall_seconds']=stats['wall_seconds']
    write_json(directory/'stats.json',stats);write_json(directory/'record.json',record)
    return record,stats


def batch(sample,start,stop,seconds):
    limits();OUT.mkdir(exist_ok=True)
    source=HERE/'results/B9-GAPS-13.g6' if sample=='gaps13' else HERE/'results/round2'/sample/'UNKNOWN.g6'
    codes=source.read_text().splitlines();host=database()['G118'];began=time.monotonic();rows=[]
    (OUT/sample).mkdir(exist_ok=True);(OUT/sample/'input.g6').write_text(source.read_text())
    for i,code in enumerate(codes[start:stop],start):
        record,stats=solve(code,sample,host,seconds);rows.append(stats)
        print(json.dumps({'index':i,'g6':code,'verdict':record['verdict'],'degree':stats.get('degree'),'reason':stats['reason'],'seconds':stats['wall_seconds']}),flush=True)
    summary={'sample':sample,'start':start,'stop':min(stop,len(codes)),'count':len(rows),'embedded':sum(r['reason']=='exact_embedding' for r in rows),'wall_seconds':time.monotonic()-began,'input_sha256':sha(source.read_bytes())}
    write_json(OUT/'batches'/f'{sample}-{start}-{stop}.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='input':
        del sys.argv[1]
        from generic_exact import cli
        cli('g118')
        raise SystemExit(0)
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);sub.add_parser('controls')
    b=sub.add_parser('batch');b.add_argument('--sample',choices=['gaps13','maximal','uniform500'],required=True);b.add_argument('--start',type=int,default=0);b.add_argument('--stop',type=int,required=True);b.add_argument('--cap',type=float,default=180)
    a=p.parse_args()
    if a.command=='controls':controls()
    else:batch(a.sample,a.start,a.stop,a.cap)
