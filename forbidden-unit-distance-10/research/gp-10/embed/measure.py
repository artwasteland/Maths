"""Reproducible module samples and method-by-method measurements."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time
from collections import Counter
from gp10embed import limits,warm,run_one,METHODS
from exact import graph6,adjacency,verify
from hosts import monomorphism

HERE=Path(__file__).resolve().parent
RESULTS=HERE/'results'
DATA=HERE.parent/'data'
REFERENCE=Path('<scratch>/scratchpad')
SAMPLES=('maximal','uniform500','B9p','named')

def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(codes):
    result=subprocess.run(['nauty-labelg','-q'],input='\n'.join(codes)+'\n',text=True,capture_output=True,timeout=20)
    lines=result.stdout.splitlines()
    if len(lines)!=len(codes):raise ValueError('labelg:missing_exact_graph6_output')
    for before,after in zip(codes,lines):
        n,e=graph6(before);m,f=graph6(after)
        if n!=m or len(e)!=len(f) or monomorphism(adjacency(n,e),adjacency(m,f))[0] is None:
            raise ValueError('labelg:not_isomorphic')
    return lines

def prepare():
    import networkx as nx
    RESULTS.mkdir(exist_ok=True)
    for name in SAMPLES:(RESULTS/name).mkdir(exist_ok=True)
    sources={'maximal':REFERENCE/'poset/maximal.g6','uniform500':DATA/'B10.g6','B9p':DATA/'B9p.g6'}
    manifest={'sources':{},'samples':{},'sampling_seed':20260924}
    for name,p in sources.items():
        lines=p.read_text().splitlines()
        if name=='uniform500':lines=random.Random(20260924).sample(lines,500)
        if len(set(lines))!=len(lines):raise ValueError('duplicate sample')
        (RESULTS/name/'input.g6').write_text('\n'.join(lines)+'\n')
        manifest['sources'][name]={'path':str(p),'sha256':digest(p)}
        manifest['samples'][name]={'size':len(lines),'sha256':digest(RESULTS/name/'input.g6')}
    named={'Petersen':nx.petersen_graph(),'pentagonal_prism':nx.circular_ladder_graph(5),
           'Moebius_ladder':nx.cycle_graph(10),
           'Moser_spindle':nx.Graph([(0,1),(0,2),(1,2),(1,3),(2,3),(0,4),(0,5),(4,5),(4,6),(5,6),(3,6)]),
           'K4':nx.complete_graph(4),'K2_3':nx.complete_bipartite_graph(2,3)}
    named['Moebius_ladder'].add_edges_from((i,i+5) for i in range(5))
    codes={name:nx.to_graph6_bytes(g,header=False).decode().strip() for name,g in named.items()}
    codes['Golomb']='I|eMI?P@W';codes['extremal_10']='IISpZATaw'
    forbidden=json.loads((HERE.parents[1]/'unit-distance-22/data/forbidden-74.json').read_text())
    for i in (4,9,10,17,18):
        g=nx.Graph(forbidden[i]);g=nx.convert_node_labels_to_integers(g,ordering='sorted')
        codes['complex_only_'+str(i)]=nx.to_graph6_bytes(g,header=False).decode().strip()
    canon=canonical(list(codes.values()));codes=dict(zip(codes,canon))
    (RESULTS/'named'/'input.g6').write_text('\n'.join(codes.values())+'\n')
    write_json(RESULTS/'named'/'names.json',codes)
    manifest['samples']['named']={'size':len(codes),'sha256':digest(RESULTS/'named'/'input.g6')}
    t=time.monotonic();patterns=[]
    for i,edges in enumerate(forbidden):
        n=1+max(max(e) for e in edges)
        patterns.append((i,n,len(edges),adjacency(n,edges)))
    labels={};witnesses={}
    for code in (RESULTS/'B9p'/'input.g6').read_text().splitlines():
        n,edges=graph6(code);host=adjacency(n,edges);witness=None
        for i,k,m,pattern in patterns:
            if k>n or m>len(edges):continue
            mapping,nodes=monomorphism(pattern,host,1000000)
            if mapping is not None:
                assert len(set(mapping))==k
                assert all(host[mapping[u]]>>mapping[v]&1 for u in range(k) for v in range(u) if pattern[u]>>v&1)
                witness={'index':i,'map':mapping};break
            if nodes>1000000:raise RuntimeError('F9 classification node cap')
        labels[code]='forbidden' if witness else 'F9_free'
        if witness:witnesses[code]=witness
    write_json(RESULTS/'B9p'/'labels.json',labels);write_json(RESULTS/'B9p'/'forbidden-witnesses.json',witnesses)
    manifest['B9_classification']={'counts':dict(Counter(labels.values())),'seconds':time.monotonic()-t}
    write_json(RESULTS/'manifest.json',manifest)
    print(json.dumps(manifest,indent=2),flush=True)

def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

def stages(sample):
    files=list((RESULTS/sample).glob('*.meta.json'))
    return sorted(files,key=lambda p:json.loads(p.read_text())['started'])

def decided(sample,exclude=None):
    out={}
    for p in stages(sample):
        label=p.name[:-len('.meta.json')]
        if label==exclude:continue
        for r in read_records(p.with_name(label+'.records.jsonl')):
            if r['verdict']=='embedded':out.setdefault(r['g6'],r)
    return out

def stage(sample,method,seconds,node_cap,take,label):
    folder=RESULTS/sample;source=(folder/'input.g6').read_text().splitlines()
    known=decided(sample,exclude=label)
    remaining=[c for c in source if c not in known]
    if take and len(remaining)>take:remaining=random.Random(20260924).sample(remaining,take)
    start=time.monotonic();warm((method,));warm_seconds=time.monotonic()-start
    records_path=folder/(label+'.records.jsonl');stats_path=folder/(label+'.stats.jsonl')
    start=time.monotonic();counts=Counter();started=time.time()
    labels=json.loads((folder/'labels.json').read_text()) if sample=='B9p' else {}
    with records_path.open('w') as records,stats_path.open('w') as stats:
        for i,c in enumerate(remaining):
            record,meta=run_one(c,seconds,(method,),node_cap)
            if labels.get(c)=='forbidden' and record['verdict']=='embedded':
                with (HERE/'LABNOTES.md').open('a') as f:f.write('\nControl failure: forbidden B9 input accepted: '+c+'\n')
                raise AssertionError('forbidden control accepted; stopped')
            counts[record['verdict']]+=1
            records.write(json.dumps(record,separators=(',',':'))+'\n');records.flush()
            stats.write(json.dumps(meta,separators=(',',':'))+'\n');stats.flush()
            if (i+1)%100==0:print(sample,method,i+1,dict(counts),round(time.monotonic()-start,3),flush=True)
    summary={'sample':sample,'method':method,'label':label,'started':started,'input_size':len(source),
             'already_embedded':len(known),'remaining_before':len(source)-len(known),'attempted':len(remaining),
             'counts':dict(counts),'seconds':time.monotonic()-start,'warm_seconds':warm_seconds,
             'time_limit':seconds,'node_cap':node_cap,'sample_cap':take or None}
    write_json(folder/(label+'.meta.json'),summary)
    print(json.dumps(summary),flush=True)
    aggregate(sample)

def aggregate(sample):
    folder=RESULTS/sample;source=(folder/'input.g6').read_text().splitlines();by_code={};stats={};summary=[]
    for p in stages(sample):
        meta=json.loads(p.read_text());label=meta['label'];summary.append(meta)
        for r in read_records(folder/(label+'.records.jsonl')):
            if r['verdict']=='embedded':by_code.setdefault(r['g6'],r)
        for s in read_records(folder/(label+'.stats.jsonl')):stats.setdefault(s['g6'],[]).append(s)
    unknown=[]
    with (folder/'records.jsonl').open('w') as out:
        for c in source:
            if c in by_code:r=by_code[c]
            else:
                unknown.append(c);attempts=stats.get(c,[])
                r={'g6':c,'verdict':'unknown','cert':{'reason':'measured_searches_incomplete',
                   'budget':{'wall_seconds':sum(s['budget']['wall_seconds'] for s in attempts),
                             'stages':[{'method':s['budget']['attempts'][0]['method'] if s['budget']['attempts'] else s['budget'].get('interrupted_method'),
                                        'limit_seconds':s['budget']['limit_seconds'],'wall_seconds':s['budget']['wall_seconds']} for s in attempts]}}}
            out.write(json.dumps(r,separators=(',',':'))+'\n')
    (folder/'UNKNOWN.g6').write_text(''.join(c+'\n' for c in unknown))
    final={'input':len(source),'embedded':len(by_code),'unknown':len(unknown),'methods':summary}
    if sample=='B9p':
        labels=json.loads((folder/'labels.json').read_text())
        final['classes']={name:{'total':sum(x==name for x in labels.values()),'embedded':sum(labels[c]==name for c in by_code)} for name in sorted(set(labels.values()))}
    if sample=='named':
        names=json.loads((folder/'names.json').read_text());final['named']={name:('embedded' if c in by_code else 'unknown') for name,c in names.items()}
    write_json(folder/'summary.json',final)
    return final

def audit():
    unique={};summaries={};unknown=set();fallback={}
    for sample in SAMPLES:
        if not stages(sample):continue
        summary=aggregate(sample);summaries[sample]={k:v for k,v in summary.items() if k!='methods'}
        expected=(RESULTS/sample/'input.g6').read_text().splitlines()
        records=read_records(RESULTS/sample/'records.jsonl')
        assert [r['g6'] for r in records]==expected
        assert [r['g6'] for r in records if r['verdict']=='unknown']==(RESULTS/sample/'UNKNOWN.g6').read_text().splitlines()
        for r in records:
            fallback.setdefault(r['g6'],r)
            if r['verdict']=='embedded':verify(r['g6'],r['cert']);unique[r['g6']]=r
            else:unknown.add(r['g6'])
    unknown-=unique.keys()
    (HERE/'UNKNOWN.g6').write_text(''.join(c+'\n' for c in sorted(unknown)))
    # Propagate successes across overlapping samples without misattributing
    # method-specific measurements. The union is an additional artifact.
    all_codes=set()
    for sample in SAMPLES:
        p=RESULTS/sample/'input.g6'
        if p.exists():all_codes.update(p.read_text().splitlines())
    with (RESULTS/'union-records.jsonl').open('w') as out:
        for c in sorted(all_codes):
            if c in unique:r=unique[c]
            else:
                r=fallback.get(c,{'g6':c,'verdict':'unknown','cert':{'reason':'not_measured','budget':{}}})
            out.write(json.dumps(r,separators=(',',':'))+'\n')
    summary={'samples':summaries,'union_input':len(all_codes),'union_embedded':len(unique),'union_unknown':len(all_codes-unique.keys()),'all_embedded_self_checks':'accepted'}
    assert set((HERE/'UNKNOWN.g6').read_text().splitlines())==all_codes-unique.keys()
    write_json(RESULTS/'audit.json',summary);print(json.dumps(summary,indent=2),flush=True)

def main():
    limits();p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare');sub.add_parser('audit')
    stagep=sub.add_parser('stage');stagep.add_argument('sample',choices=SAMPLES);stagep.add_argument('method',choices=METHODS)
    stagep.add_argument('--seconds',type=float,required=True);stagep.add_argument('--node-cap',type=int,default=1500)
    stagep.add_argument('--take',type=int,default=0);stagep.add_argument('--label')
    a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='audit':audit()
    else:stage(a.sample,a.method,a.seconds,a.node_cap,a.take,a.label or a.method)
if __name__=='__main__':main()
