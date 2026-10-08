from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, itertools, sys
sys.dont_write_bytecode = True
R = Path('<repo>')
S = Path('<scratch>/scratchpad')
O = Path('/tmp/metadata-audit')
O.mkdir(exist_ok=True)
def codes(p):
    return [x.strip() for x in p.read_text().splitlines() if x.strip() and not x.startswith('>>')]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(c):
    n=ord(c[0])-63
    assert 0<=n<=62
    bits=[(ord(z)-63 >> b)&1 for z in c[1:] for b in range(5,-1,-1)]
    E=set(); k=0
    for j in range(1,n):
        for i in range(j):
            if bits[k]: E.add((i,j))
            k+=1
    return n,E
def enc(n,E):
    bits=[int((i,j) in E) for j in range(1,n) for i in range(j)]
    bits += [0]*((-len(bits))%6)
    return chr(n+63)+''.join(chr(63+sum(bits[k+b]<<(5-b) for b in range(6))) for k in range(0,len(bits),6))
out=[]
def log(*args):
    line=' '.join(map(str,args)); print(line,flush=True); out.append(line)
forms={}
for title,base,sub,target in [('control22',S/'control22','u23','22-61'),('calibration',S/'calib-snap','calib-21-57','21-57')]:
    ds=sorted(base.glob(f'*/research/unit-distance-23/results/{sub}/{target}-L12-tri-pf74/s*of1920'))
    indices={int(d.name[1:].split('of')[0]) for d in ds}
    union=set(); bad=[]; total=0
    for d in ds:
        p=d/f'{target}.keep.g6'; h=json.loads((d/'hashes.json').read_text())['files'].get(p.name)
        cs=codes(p); total+=len(cs); union.update(cs)
        if h is None or h['sha256']!=sha(p) or h['records']!=len(cs): bad.append(str(p))
    log(title,'copies',len(ds),'indices',len(indices),'missing',sorted(set(range(1920))-indices),'keep_records',total,'distinct_g6',len(union),'hash_or_count_mismatches',len(bad))
    forms[title]=sorted(union)
    assert len(indices)==1920 and not bad
fleet=sorted((S/'fleet/results').glob('*/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s*of1920'))
union=defaultdict(set); bad=[]
for d in fleet:
    p=d/'22-60.keep.g6'; cs=codes(p)
    h=json.loads((d/'hashes.json').read_text())['files'][p.name]
    if h['sha256']!=sha(p) or h['records']!=len(cs):bad.append(str(p))
    for c in cs:union[c].add(d.name)
log('level22','copies',len(fleet),'distinct_g6',len(union),'in_multiple_slices',sum(len(v)>1 for v in union.values()),'hash_or_count_mismatches',len(bad))
forms['level22']=sorted(union)
known22=codes(R/'research/unit-distance-22/sources/engel-dataset/engel-22-60.g6')
required=[]
for i,c in enumerate(known22):
    n,E=decode(c); assert (n,len(E))==(22,60)
    degree=[sum(v in e for e in E) for v in range(n)]
    if min(degree)>=4:required.append(i)
log('known22','graphs',len(known22),'min_degree_at_least_4',len(required),'indices',required)
known21=codes(R/'research/unit-distance-22/sources/engel-dataset/engel-21-57.g6')
forms['known22']=known22; forms['known21']=known21
(O/'canonical-input.json').write_text(json.dumps(forms))
(O/'canonical-input.g6').write_text(''.join(c+'\n' for group in forms.values() for c in group))
ds=sorted((S/'u22-slices').glob('s*of48'))
raw=[]; nonempty=[]; bad=[]
for d in ds:
    p=d/'22-61.g6'; cs=codes(p); raw+=cs
    if cs:nonempty.append((d.name,len(cs)))
    h=json.loads((d/'22-61.manifest.json').read_text())
    if h['children_file_sha256']!=sha(p) or h['children_written']!=len(cs):bad.append(d.name)
known4=codes(R/'research/unit-distance-22/results/u22/cell-22-61/all4.g6')
log('u22_original_target','slice_files',len(ds),'indices',len({int(d.name[1:].split('of')[0]) for d in ds}),'raw_records',len(raw),'nonempty',nonempty,'manifest_mismatches',bad,'equals_all4',sorted(raw)==sorted(known4))
F=json.loads((R/'research/unit-distance-22/data/forbidden-74.json').read_text())
dp=R/'research/unit-distance-22/delta4'
recs=[json.loads(l) for l in (dp/'filter-verdicts.jsonl').read_text().splitlines() if l.strip()]
checked=0
for r in recs:
    n,E=decode(r['g6']); w=r['witness']; pat=F[w['index']]; m=w['map']
    assert r['verdict']=='forbidden' and (n,len(E))==(22,61)
    assert len(m)==1+max(max(e) for e in pat) and len(set(m))==len(m) and all(0<=x<n for x in m)
    assert all(tuple(sorted((m[a],m[b]))) in E for a,b in pat)
    checked+=1
can=codes(dp/'children-22-61.g6')
log('D4','canonical_file',len(can),'unique',len(set(can)),'witnesses',checked,'exact_coverage',sorted(can)==sorted(r['g6'] for r in recs))
parents=[c for c in codes(R/'research/unit-distance-22/sources/amp/anc/graph6.txt') if ord(c[0])-63==21]
assert len(parents)==5
with (O/'d4-raw.g6').open('w') as f:
    for c in parents:
        n,E=decode(c); assert len(E)==57
        for ns in itertools.combinations(range(n),4):f.write(enc(22,E|{(v,21) for v in ns})+'\n')
log('D4','fresh_labelled_extensions',5*len(list(itertools.combinations(range(21),4))))
p=R/'research/gp-10/runs/B10-final-2026-09-25'
j=json.loads((p/'report.json').read_text()); inp=codes(R/'research/gp-10/data/B10.g6'); minimal=codes(p/'L10.g6')
ev=[json.loads(l) for l in (p/'minimality.jsonl').read_text().splitlines()]
log('GP10','frozen_input_count',len(inp),'unique',len(set(inp)),'hash_match',sha(R/'research/gp-10/data/B10.g6')==j['input_sha256'],'L10_count',len(minimal),'unique',len(set(minimal)),'report_list_equal',sorted(minimal)==sorted(j['minimal']),'minimality_rows',len(ev),'statuses',dict(Counter(r['status'] for r in ev)),'derived_minimal_list_equal',sorted(r['g6'] for r in ev if r['status']=='minimal')==sorted(minimal))
by_m=Counter(); by_min=Counter(); by_max=Counter()
for c in minimal:
    n,E=decode(c);ds=[sum(v in e for e in E) for v in range(n)];by_m[len(E)]+=1;by_min[min(ds)]+=1;by_max[max(ds)]+=1
log('GP10','edge_histogram',dict(sorted(by_m.items())),'min_degree',dict(sorted(by_min.items())),'max_degree',dict(sorted(by_max.items())))
(O/'data-checks.txt').write_text('\n'.join(out)+'\n')
