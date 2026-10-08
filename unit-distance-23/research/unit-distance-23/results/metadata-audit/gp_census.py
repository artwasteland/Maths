from pathlib import Path
from collections import Counter
import json, gzip, hashlib
R=Path('<repo>')
O=Path('/tmp/metadata-audit')
report=json.loads((R/'research/gp-10/runs/B10-final-2026-09-25/report.json').read_text())
records={}; h=hashlib.sha256(); duplicates=0
with gzip.open(R/'research/gp-10/cloud/lean3/records.jsonl.gz','rb') as f:
    for line in f:
        h.update(line);r=json.loads(line)
        duplicates+=r['g6'] in records
        records[r['g6']]={'verdict':r['verdict'],'type':r['cert']['type']}
inp=set((R/'research/gp-10/data/B10.g6').read_text().splitlines())
counts=Counter(r['verdict'] for r in records.values())
minimal=(R/'research/gp-10/runs/B10-final-2026-09-25/L10.g6').read_text().splitlines()
out=[f"certificate_stream_sha256 {h.hexdigest()}; matches_checker_consumed_hash {h.hexdigest()==report['files'][0]['sha256']}",f"records {len(records)}; duplicates {duplicates}; missing {len(inp-set(records))}; extra {len(set(records)-inp)}; verdicts {dict(counts)}",f"minimal_member_certificate_types {dict(sorted(Counter(records[c]['type'] for c in minimal).items()))}"]
print('\n'.join(out),flush=True)
def dec(c):
    n=ord(c[0])-63;bits=[(ord(z)-63>>b)&1 for z in c[1:] for b in range(5,-1,-1)]
    return n,{(i,j) for k,(i,j) in enumerate((i,j) for j in range(1,n) for i in range(j)) if bits[k]}
def enc(n,E):
    bits=[int((i,j) in E) for j in range(1,n) for i in range(j)];bits += [0]*((-len(bits))%6)
    return chr(n+63)+''.join(chr(63+sum(bits[k+b]<<(5-b) for b in range(6))) for k in range(0,len(bits),6))
def biconnected(n,E):
    adj=[set() for _ in range(n)]
    for a,b in E:adj[a].add(b);adj[b].add(a)
    for removed in range(-1,n):
        root=next(v for v in range(n) if v!=removed);seen={root};todo=[root]
        while todo:
            v=todo.pop()
            for w in adj[v]:
                if w!=removed and w not in seen:seen.add(w);todo.append(w)
        if len(seen)!=n-(removed>=0):return False
    return True
deletions=[];block=0
with (O/'gp-deletions.g6').open('w') as f:
    for c,r in records.items():
        if r['verdict']!='refuted':continue
        n,E=dec(c)
        for e in sorted(E):
            D=E-{e}
            if biconnected(n,D):
                f.write(enc(n,D)+'\n');deletions.append([c,list(e)])
            else:block+=1
out.append(f'minimality_deletions_for_canonicalization {len(deletions)}; nonbiconnected_deletions {block}')
print(out[-1],flush=True)
(O/'gp-record-index.json').write_text(json.dumps(records))
(O/'gp-deletions-index.json').write_text(json.dumps(deletions))
(O/'gp-census.txt').write_text('\n'.join(out)+'\n')
