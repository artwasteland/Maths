"""Round-five frontier batches, curve tracing and complete sample merge."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
from curve_trace import CONFIG,trace
from curve_exact import solve
from exact import verify
from generic_exact import run
from msolve_exact import limits,sha
from round2 import HERE,write_json,task_id
from round2_phase import isolated
from round3_finish import run_directory

OUT=HERE/'results/round5'


def jsonl(path):return [json.loads(line) for line in Path(path).read_text().splitlines()]

def stack(start,stop):run(OUT/'input.g6',OUT/'stack',start=start,stop=stop)

def prepare_trace():
    controls=json.loads((OUT/'controls/results.json').read_text());assert controls['status']=='PASS'
    order=json.loads((OUT/'stack/order.json').read_text());eligible=[];skipped=[];unknown=[]
    for row in order:
        rec=json.loads((OUT/'stack/graphs'/task_id(row['g6'])/'record.json').read_text())
        if rec['verdict']=='unknown':
            unknown.append(row['g6'])
            (eligible if row['k']==1 else skipped).append(row)
    manifest={'input_sha256':sha((OUT/'input.g6').read_bytes()),'stack_records_sha256':sha((OUT/'stack/records.jsonl').read_bytes()),'eligible':len(eligible),'skipped_non_k1':len(skipped),'config':CONFIG,'exact_cap':120}
    dest=OUT/'trace';dest.mkdir(exist_ok=True)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==manifest,'trace:changed_input_or_config'
    write_json(dest/'manifest.json',manifest);write_json(dest/'order.json',eligible);write_json(dest/'skipped.json',skipped)
    (OUT/'stack-only-unknown.g6').write_text(''.join(c+'\n' for c in sorted(unknown)))
    (OUT/'trace-skipped.g6').write_text(''.join(r['g6']+'\n' for r in skipped))
    return manifest


def trace_one(row):
    code=row['g6'];directory=OUT/'trace/graphs'/task_id(code);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'record.json').exists():
        record=json.loads((directory/'record.json').read_text());stats=json.loads((directory/'stats.json').read_text())
        assert record['g6']==code
        if record['verdict']=='embedded':verify(code,record['cert'],max_refinements=256)
        return record,stats,True
    began=time.monotonic();stats={'g6':code,'k':row['k'],'exact':None};cert=None
    try:
        numeric=isolated(lambda:trace(code,directory/'numeric'),CONFIG['seconds']+5);stats['numeric']=numeric
        if numeric['sampled_distinct']:
            cert,exact=solve(code,numeric['witness'],directory/'exact',120);stats['exact']=exact
        stats['reason']='exact_embedding' if cert else ('numeric_distinct_but_exact_unresolved' if numeric['sampled_distinct'] else numeric['reason'])
    except Exception as exc:
        stats['reason']=type(exc).__name__+':'+str(exc)[:400]
        progress=directory/'numeric/progress.json';partial=json.loads(progress.read_text()) if progress.exists() else {}
        stats.setdefault('numeric',dict(partial,completed_grid=False,sampled_distinct=False,reason='trace_process_failed_or_timed_out'))
    stats['wall_seconds']=time.monotonic()-began
    if cert is not None:
        stats['degree']=len(cert['field']['minpoly'])-1
        record={'g6':code,'verdict':'embedded','cert':cert}
    else:record={'g6':code,'verdict':'unknown','cert':{'reason':stats['reason'],'budget':{'stack_g118_cap':10,'stack_msolve_cap':20,'trace':CONFIG,'exact_cap':120,'trace_and_exact_wall_seconds':stats['wall_seconds']}}}
    write_json(directory/'stats.json',stats);write_json(directory/'record.json',record);return record,stats,False


def trace_batch(start,stop):
    prepare_trace();order=json.loads((OUT/'trace/order.json').read_text());stop=min(stop,len(order));began=time.monotonic();counts=Counter();fresh=0
    existing=[]
    for row in order:
        f=OUT/'trace/graphs'/task_id(row['g6'])/'record.json'
        if f.exists():existing.append(json.loads(f.read_text()))
    (OUT/'trace/records.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in existing))
    with (OUT/'trace/records.jsonl').open('a') as stream:
        for index,row in enumerate(order[start:stop],start):
            record,stats,resumed=trace_one(row);counts[record['verdict']]+=1
            if not resumed:stream.write(json.dumps(record,sort_keys=True)+'\n');stream.flush();fresh+=1
            num=stats['numeric'];print(json.dumps({'index':index,'g6':row['g6'],'verdict':record['verdict'],'reason':stats['reason'],'samples':num.get('samples'),'numeric_distinct':num.get('sampled_distinct'),'complete_grid':num.get('completed_grid'),'best_separation':num.get('best_minimum_pair_distance'),'degree':stats.get('degree'),'seconds':stats['wall_seconds'],'resumed':resumed}),flush=True)
    summary={'start':start,'stop':stop,'counts':dict(counts),'fresh':fresh,'wall_seconds':time.monotonic()-began};write_json(OUT/'trace/batches'/f'{start}-{stop}.json',summary);print(json.dumps({'batch':summary}),flush=True)


def collect():
    manifest=prepare_trace();codes=(OUT/'input.g6').read_text().splitlines();assert len(codes)==len(set(codes))==702
    order=json.loads((OUT/'stack/order.json').read_text());merged={};stackstats=[];tracestats=[];likely=[]
    for row in order:
        root=OUT/'stack/graphs'/task_id(row['g6']);record=json.loads((root/'record.json').read_text());stats=json.loads((root/'stats.json').read_text());stackstats.append(stats)
        if record['verdict']=='unknown' and row['k']==1:
            target=OUT/'trace/graphs'/task_id(row['g6']);record=json.loads((target/'record.json').read_text());trace_stats=json.loads((target/'stats.json').read_text());tracestats.append(trace_stats)
            num=trace_stats['numeric']
            if num.get('completed_grid') and not num.get('sampled_distinct'):
                assert record['verdict']=='unknown'
                common=sorted(num.get('collision_pairs',{}).items(),key=lambda kv:(-kv[1],kv[0]))[:3]
                likely.append({'g6':row['g6'],'verdict':'unknown','reason':num['reason'],'minimum_pair_distance_seen':num['minimum_pair_distance_seen'],'best_minimum_pair_distance':num['best_minimum_pair_distance'],'least_edge_residual':num['least_edge_residual'],'samples':num['samples'],'real_samples':num['real_samples'],'most_common_close_pairs':common,'warning':'bounded numerical sampling only, not a refutation or exhaustive branch enumeration'})
        assert record['g6']==row['g6'];merged[row['g6']]=record
    def save(path,rows):path.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    save(OUT/'records.jsonl',[merged[c] for c in sorted(merged)]);save(OUT/'stack-stats.jsonl',stackstats);save(OUT/'trace-stats.jsonl',tracestats)
    save(OUT/'likely-forbidden.jsonl',likely)
    (OUT/'likely-forbidden.g6').write_text(''.join(c+'\n' for c in sorted(r['g6'] for r in likely)))
    (OUT/'likely-forbidden.txt').write_text(''.join(r['g6']+' min_seen='+str(r['minimum_pair_distance_seen'])+' best_min_pair='+str(r['best_minimum_pair_distance'])+' '+r['reason']+'; numerical triage only\n' for r in likely))
    (OUT/'UNDECIDED.g6').write_text(''.join(c+'\n' for c in sorted(merged) if merged[c]['verdict']=='unknown'))
    positives=[s['g6'] for s in tracestats if s['numeric'].get('sampled_distinct')]
    (OUT/'numeric-distinct.g6').write_text(''.join(c+'\n' for c in sorted(positives)))
    (OUT/'numeric-distinct-unverified.g6').write_text(''.join(c+'\n' for c in sorted(positives) if merged[c]['verdict']=='unknown'))
    (OUT/'rigid-no-embedding.g6').write_text(''.join(s['g6']+'\n' for s in stackstats if s['triage']))
    run_directory(OUT/'run',[merged[c] for c in sorted(merged)],'../records.jsonl')
    byk={};trace_by_code={s['g6']:s for s in tracestats}
    for st in stackstats:
        r=byk.setdefault(str(st['k']),Counter());r['inputs']+=1;r['final_'+merged[st['g6']]['verdict']]+=1
        r[st.get('method','stack_unknown')]+=1
        if st['g6'] in trace_by_code:
            tr=trace_by_code[st['g6']];r['traced']+=1;r['trace_embedded']+=tr['reason']=='exact_embedding';r['numeric_distinct']+=tr['numeric'].get('sampled_distinct',False)
    summary={'input_count':702,'input_sha256':sha((OUT/'input.g6').read_bytes()),'stack_counts':dict(Counter(s.get('method','unknown') for s in stackstats)),
        'final_counts':dict(Counter(r['verdict'] for r in merged.values())),'by_k':byk,'trace_manifest':manifest,
        'trace_reasons':dict(Counter(s['reason'] for s in tracestats)),'likely_forbidden_triage':len(likely),'numeric_distinct':len(positives),
        'trace_new_embeddings':sum(s['reason']=='exact_embedding' for s in tracestats),'trace_samples':sum(s['numeric'].get('samples',0) for s in tracestats),
        'trace_real_samples':sum(s['numeric'].get('real_samples',0) for s in tracestats),'stack_seconds':sum(s['wall_seconds'] for s in stackstats),
        'trace_and_exact_seconds':sum(s['wall_seconds'] for s in tracestats),'numeric_trace_seconds':sum(s['numeric'].get('wall_seconds',0) for s in tracestats),
        'trace_exact_seconds':sum((s.get('exact') or {}).get('wall_seconds',0) for s in tracestats),'records_sha256':sha((OUT/'records.jsonl').read_bytes())}
    write_json(OUT/'summary.json',summary);return summary


def main():
    limits();p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    for name in ('stack','trace'):
        b=sub.add_parser(name);b.add_argument('--start',type=int,required=True);b.add_argument('--stop',type=int,required=True)
    sub.add_parser('prepare-trace');sub.add_parser('collect');a=p.parse_args()
    if a.command=='stack':stack(a.start,a.stop)
    elif a.command=='trace':trace_batch(a.start,a.stop)
    else:print(json.dumps(prepare_trace() if a.command=='prepare-trace' else collect(),indent=2))

if __name__=='__main__':main()
