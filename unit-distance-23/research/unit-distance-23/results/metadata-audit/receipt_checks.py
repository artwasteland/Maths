from pathlib import Path
from collections import Counter, defaultdict
import sys, json, hashlib, re
sys.dont_write_bytecode=True
R=Path('<repo>')
S=Path('<scratch>/scratchpad')
O=Path('/tmp/metadata-audit')
sys.path.insert(0,str(R/'research/unit-distance-23/tools'))
import verify_sample as vs
import target_check as tc
out=[]
def log(*x):
    t=' '.join(map(str,x));print(t,flush=True);out.append(t)
fleet=sorted((S/'fleet/results').glob('*/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s*of1920'))
shards=defaultdict(dict);prefix_shards={}
for d in fleet:
    i=int(d.name[1:].split('of')[0]);rs=json.loads((d/'run-summary.json').read_text())
    for e in rs['levels']:
        if e.get('shards'):
            cell=e['n'],e['m'];nsh=len(e['shards'])
            assert cell not in shards[i] or shards[i][cell]==nsh
            shards[i][cell]=nsh
            if e['n']<=12:
                assert cell not in prefix_shards or prefix_shards[cell]==nsh
                prefix_shards[cell]=nsh
for i in shards:shards[i].update(prefix_shards)
(O/'receipt-shard-counts.json').write_text(json.dumps({str(i):{f'{n}-{m}':c for (n,m),c in cs.items()} for i,cs in shards.items()}))
d=fleet[0];problems=[]
der=tc.vc().derive(json.loads((d/'run-config.json').read_text()),json.loads((d/'run-summary.json').read_text()),json.loads((d/'reach.json').read_text()),problems)
assert not problems,problems
ref={'counts':dict.fromkeys(der['required'])}
log('required_cells_independently_derived',len(ref['counts']),'level12_cells',sum(n==12 for n,m in ref['counts']))
for title,root,plan in [('sample',S/'fleet/verify-results',vs.plan_from_jobs(vs.JOBS.read_text())),('all',S/'verify-all-claude',vs.plan_from_all(vs.ALL_PLAN))]:
    receipts=defaultdict(list)
    for p in sorted(root.glob('*/research/unit-distance-23/results/u23/verify/s*of1920-*.txt')):
        tag=p.relative_to(root).parts[0].split('-')[0]
        mm=re.fullmatch(rf's(\d+)of1920-{tag}(\.lean)?\.txt',p.name)
        if not mm:continue
        o=vs.parse_output(p.read_text());o['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();o['file_kind']='lean' if mm.group(2) else 'g5'
        receipts[tag,int(mm.group(1))].append(o)
    bad=[];stats=Counter();covered=[];nodigest=[]
    for tag,sl in plan['workers'].items():
        first=sl[0]
        for i in sl:
            os=receipts.get((tag,i),[])
            gs=[o for o in os if o['file_kind']=='g5'];ls=[o for o in os if o['file_kind']=='lean']
            chosen=ls if ls else gs
            if not chosen:bad.append((tag,i,'no receipt'));continue
            if ls:
                if not gs or any(not o['killed'] for o in gs):bad.append((tag,i,'non-memory fallback'))
                stats['lean_slices']+=1
            whole=False
            for o in chosen:
                skipped=o['head']['id'] and 'whole check skipped' in o['head']['id'][3]
                whole=i==first and not skipped
                why=vs.judge_output(o,tag,i,first,plan,kind=o['file_kind'])+vs.record_scope(o,ref,whole,shards[i])
                if why:bad.append((tag,i,why))
                stats['accepted_receipt_copies']+=1
                stats['digest_present' if o['head']['digest'] else 'digest_absent']+=1
                if not o['head']['digest']:nodigest.append((tag,i))
            stats['whole_slices' if whole else 'from13_slices']+=1
            covered.append(i)
    log(title,'planned',sum(map(len,plan['workers'].values())),'covered_unique',len(set(covered)),'stats',dict(stats),'scope_or_verdict_errors',len(bad))
    if bad:log('errors',bad[:10])
    if nodigest:log(title,'no_digest_slices',nodigest)
    assert not bad
    if title=='sample':
        import random
        drawn=sorted(random.Random(plan['seed']).sample(sorted(set(range(1920))-set(plan['restarted'])),plan['k']))
        log('sample','random_rule_matches',drawn==sorted(plan['random']),'seed',plan['seed'],'random',len(drawn),'restarted',len(plan['restarted']))
(O/'receipt-checks.txt').write_text('\n'.join(out)+'\n')
