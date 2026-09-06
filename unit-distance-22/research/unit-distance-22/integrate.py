#!/usr/bin/env python3
"""Gate G2/G3: reproduce AMP Table 1 through the pipeline.
For n = 16..21 with m = u(n): count F-free graphs from enum/out/<n>-<m>.g6, run the filter
(expect the after-TU counts), and (when the embedder is wired) embed the survivors (expect the
embeddable counts and exactly the known extremal graphs). Also u-bar(22) = 62 with two graphs.
Usage: integrate.py [--enum-dir enum/out] [--embed]"""
import subprocess, json, sys, os, collections, argparse
HERE=os.path.dirname(os.path.abspath(__file__))
ap=argparse.ArgumentParser(); ap.add_argument('--enum-dir', default=os.path.join(HERE,'enum','out')); ap.add_argument('--embed', action='store_true'); a=ap.parse_args()
U={16:41,17:43,18:46,19:50,20:54,21:57}
EXP_FFREE={16:1,17:15,18:84,19:17,20:7,21:149}; EXP_TU={16:1,17:8,18:38,19:5,20:1,21:19}; EXP_EMB={16:1,17:7,18:16,19:3,20:1,21:5}
known=collections.defaultdict(set)
for l in open(os.path.join(HERE,'sources','amp','anc','graph6.txt')):
    l=l.strip()
    if l: known[ord(l[0])-63].add(l)
ok=True
def canon(lines):
    p=subprocess.run(['nauty-labelg','-q'],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True); return p.stdout.split()
for n,m in U.items():
    f=os.path.join(a.enum_dir,f'{n}-{m}.g6')
    if not os.path.exists(f):
        for alt in (f+'.zst',):
            if os.path.exists(alt):
                lines=subprocess.run(['zstd','-dc',alt],capture_output=True,text=True,check=True).stdout.split(); break
        else:
            print(f'n={n}: MISSING {f}'); ok=False; continue
    else:
        lines=[l.strip() for l in open(f) if l.strip()]
    c=canon(lines); dup=len(c)-len(set(c))
    p=subprocess.run(['./udfilter'],input='\n'.join(c)+'\n',capture_output=True,text=True,check=True,cwd=os.path.join(HERE,'filter'))
    recs=[json.loads(l) for l in p.stdout.splitlines() if l.strip()]
    hist=collections.Counter(r['verdict'] for r in recs); survivors=[r['g6'] for r in recs if r['verdict']=='pass']
    miss=known[n]-set(c)
    line=f'n={n} m={m}: F-free={len(c)} (expect {EXP_FFREE[n]}), dups={dup}, filter={dict(hist)}, pass={len(survivors)} (expect {EXP_TU[n]}), known-in-list={len(known[n])-len(miss)}/{len(known[n])}'
    good=(len(c)==EXP_FFREE[n] and dup==0 and len(survivors)==EXP_TU[n] and not miss)
    print(('OK   ' if good else 'FAIL ')+line); ok&=good
    open(os.path.join(HERE,f'survivors-{n}-{m}.g6'),'w').write('\n'.join(survivors)+'\n')
for n,m,exp in ((22,62,2),(22,63,0)):
    f=os.path.join(a.enum_dir,f'{n}-{m}.g6')
    if os.path.exists(f):
        c=[l.strip() for l in open(f) if l.strip()]; good=(len(c)==exp); ok&=good
        print(('OK   ' if good else 'FAIL ')+f'n={n} m={m}: F-free={len(c)} (expect {exp})')
    else: print(f'n={n} m={m}: MISSING'); ok=False

# Engel et al. completeness control: every extracted class must be in our full level file
import glob
eng=sorted(glob.glob(os.path.join(HERE,'sources','engel-dataset','engel-*.g6')))
for f in eng:
    n,m=map(int,os.path.basename(f)[6:-3].split('-'))
    lf=os.path.join(a.enum_dir,f'{n}-{m}.g6')
    if not os.path.exists(lf): continue
    ours=set(canon([l.strip() for l in open(lf) if l.strip()]))
    theirs=[l.strip() for l in open(f) if l.strip()]
    miss=[g for g in theirs if g not in ours]
    good=not miss; ok&=good
    print(('OK   ' if good else 'FAIL ')+f'engel ({n},{m}): {len(theirs)} classes, missing {len(miss)}')

print('GATE G2:', 'PASS' if ok else 'NOT YET')
