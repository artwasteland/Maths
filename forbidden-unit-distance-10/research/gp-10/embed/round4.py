"""Round-four candidate snapshots, bounded search and sample checker merge."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from generic_exact import run,read_codes
from msolve_exact import limits,sha
from round2 import HERE,write_json,task_id

OUT=HERE/'results/round4'
SOURCE=Path('<scratch>/scratchpad/cand')

def jsonl(raw,partial=False):
    lines=raw.splitlines(keepends=True);rows={}
    if partial and lines and not lines[-1].endswith(b'\n'):lines=lines[:-1]
    for line in lines:
        row=json.loads(line);code=row['g6']
        if code in rows:raise ValueError('duplicate:'+code)
        if row['verdict'] not in ('embedded','refuted','unknown'):raise ValueError('verdict')
        rows[code]=row
    return rows

def snapshot(label):
    dest=OUT/'snapshots'/label;meta_path=dest/'snapshot.json'
    if meta_path.exists():
        meta=json.loads(meta_path.read_text())
        for name,item in meta['files'].items():
            if sha((dest/name).read_bytes())!=item['sha256']:raise ValueError('snapshot:hash_changed')
        return meta
    raw={name:(SOURCE/name).read_bytes() for name in ('cand1515.g6','tree5.jsonl','emb.jsonl')}
    codes=raw['cand1515.g6'].decode().splitlines();candidate=set(codes)
    if len(codes)!=1515 or len(candidate)!=1515:raise ValueError('candidate:size_or_duplicates')
    tree=jsonl(raw['tree5.jsonl']);emb=jsonl(raw['emb.jsonl'],partial=True)
    if set(tree)!=candidate or not set(emb)<=candidate:raise ValueError('source:coverage')
    if label=='end' and (set(emb)!=candidate or not raw['emb.jsonl'].endswith(b'\n')):raise ValueError('external_embedding_pass_incomplete:'+str(len(emb)))
    refuted={c for c,r in tree.items() if r['verdict']=='refuted'}
    embedded={c for c,r in emb.items() if r['verdict']=='embedded'}
    if refuted & embedded:raise ValueError('source:contradiction')
    meta={'utc':datetime.now(timezone.utc).isoformat(),'source':str(SOURCE),'candidate_count':len(candidate),
        'tree_counts':dict(Counter(r['verdict'] for r in tree.values())),
        'emb_counts':dict(Counter(r['verdict'] for r in emb.values())),
        'emb_complete':set(emb)==candidate and raw['emb.jsonl'].endswith(b'\n'),
        'unresolved_count':len(candidate-refuted-embedded),'files':{name:{'sha256':sha(data),'bytes':len(data)} for name,data in raw.items()}}
    dest.mkdir(parents=True,exist_ok=True)
    for name,data in raw.items():(dest/name).write_bytes(data)
    (OUT/('input-'+label+'.g6')).write_text(''.join(c+'\n' for c in sorted(candidate-refuted-embedded)))
    write_json(meta_path,meta);return meta

def prepare():
    OUT.mkdir(exist_ok=True)
    controls=json.loads((OUT/'controls/results.json').read_text())
    if not controls['passed'] or any(r['status']!='PASS' for r in controls['checks']):raise ValueError('controls:failed')
    return snapshot('start')

def batch(start,stop):
    if not (OUT/'snapshots/start/snapshot.json').exists():prepare()
    run(OUT/'input-start.g6',OUT/'search',start=start,stop=stop)

def collect():
    end=snapshot('end');start=json.loads((OUT/'snapshots/start/snapshot.json').read_text())
    if start['files']['cand1515.g6']['sha256']!=end['files']['cand1515.g6']['sha256']:raise ValueError('candidate:changed')
    dest=OUT/'snapshots/end';codes=(dest/'cand1515.g6').read_text().splitlines()
    tree=jsonl((dest/'tree5.jsonl').read_bytes());external=jsonl((dest/'emb.jsonl').read_bytes())
    order=json.loads((OUT/'search/order.json').read_text());new={};stats=[];triage=[]
    for row in order:
        root=OUT/'search/graphs'/task_id(row['g6'])
        rec=json.loads((root/'record.json').read_text());stat=json.loads((root/'stats.json').read_text())
        if rec['g6']!=row['g6'] or stat['g6']!=row['g6']:raise ValueError('search:graph_mismatch')
        new[row['g6']]=rec;stats.append(stat)
        if stat['triage']:triage.append(stat)
    expected=set((OUT/'input-start.g6').read_text().splitlines())
    if set(new)!=expected:raise ValueError('search:incomplete')
    merged={};origins={}
    for code in codes:
        choices=[('round4',new.get(code)),('external_embedding',external[code]),('external_tree',tree[code])]
        decided=[(name,r) for name,r in choices if r and r['verdict']!='unknown']
        if len({r['verdict'] for name,r in decided})>1:raise ValueError('merge:contradiction:'+code)
        origin,record=decided[0] if decided else next((name,r) for name,r in choices if r)
        merged[code]=record;origins[code]=origin
    for stat in triage:
        if stat['k']!=0 or merged[stat['g6']]['verdict']=='embedded':raise ValueError('triage:contradiction_or_pinned')
    def records(path,rows):path.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    records(OUT/'new-records.jsonl',[new[c] for c in sorted(new)])
    records(OUT/'merged-records.jsonl',[merged[c] for c in sorted(merged)])
    records(OUT/'stats.jsonl',stats);records(OUT/'rigid-no-embedding.jsonl',triage)
    (OUT/'rigid-no-embedding.g6').write_text(''.join(c+'\n' for c in sorted(s['g6'] for s in triage)))
    undecided=''.join(c+'\n' for c in sorted(merged) if merged[c]['verdict']=='unknown')
    (OUT/'UNDECIDED.g6').write_text(undecided)
    unique=[c for c in new if new[c]['verdict']=='embedded' and external[c]['verdict']!='embedded']
    (OUT/'new-unique-embedded.g6').write_text(''.join(c+'\n' for c in sorted(unique)))
    write_json(OUT/'origins.json',origins)
    by_k={};methods={};reasons=Counter();degrees=Counter()
    for s in stats:
        key=str(s['k']);r=new[s['g6']];entry=by_k.setdefault(key,Counter());entry['attempted']+=1;entry[r['verdict']]+=1;entry['triage']+=int(s['triage'])
        if r['verdict']=='embedded':entry[s['method']]+=1;degrees[str(s['degree'])]+=1
        for stage in s['stages']:
            m=methods.setdefault(stage['method'],{'attempted':0,'embedded':0,'triage':0,'seconds':0,'max_seconds':0,'attempts':0,'frames':Counter(),'pin_proposals':0})
            m['attempted']+=1;m['embedded']+=stage['reason']=='exact_embedding';m['triage']+=stage.get('triage',False);m['seconds']+=stage['wall_seconds'];m['max_seconds']=max(m['max_seconds'],stage['wall_seconds'])
            reasons[stage['method']+':'+stage['reason']]+=1
            for attempt in stage.get('attempts',[]):
                m['attempts']+=1;m['frames'][str(attempt['frame'])]+=1;m['pin_proposals']+=bool(attempt.get('pins'))
    summary={'start':start,'end':end,'search_count':len(new),'search_counts':dict(Counter(r['verdict'] for r in new.values())),
        'merged_counts':dict(Counter(r['verdict'] for r in merged.values())),'new_unique_embeddings':len(unique),'rigid_triage':len(triage),
        'by_k':by_k,'methods':methods,'stage_reasons':dict(reasons),'certificate_degrees':dict(degrees),
        'wall_seconds_sum':sum(s['wall_seconds'] for s in stats),'merged_sha256':sha((OUT/'merged-records.jsonl').read_bytes()),
        'new_records_sha256':sha((OUT/'new-records.jsonl').read_bytes()),'undecided_sha256':sha(undecided.encode())}
    for run_name,input_codes,record_file,unknown in [('run',sorted(merged),'../merged-records.jsonl',undecided),('new-run',sorted(new),'../new-records.jsonl',''.join(c+'\n' for c in sorted(new) if new[c]['verdict']=='unknown'))]:
        directory=OUT/run_name;directory.mkdir(exist_ok=True);text=''.join(c+'\n' for c in input_codes)
        (directory/'input.g6').write_text(text);(directory/'UNKNOWN.g6').write_text(unknown)
        write_json(directory/'run.json',{'profile':'sample','input':'input.g6','input_sha256':sha(text.encode()),'records':[record_file],'unknown':'UNKNOWN.g6','derive':False})
    write_json(OUT/'summary.json',summary);return summary

def main():
    limits();p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare');sub.add_parser('collect');b=sub.add_parser('batch');b.add_argument('--start',type=int,required=True);b.add_argument('--stop',type=int,required=True);a=p.parse_args()
    if a.command=='batch':batch(a.start,a.stop)
    else:print(json.dumps(prepare() if a.command=='prepare' else collect(),indent=2))

if __name__=='__main__':main()
