from pathlib import Path
import sys,json,shutil,hashlib
sys.dont_write_bytecode=True
R=Path('<repo>');O=Path('/tmp/metadata-audit')
S=Path('<scratch>/scratchpad')
sys.path.insert(0,str(R/'research/unit-distance-23/tools'))
import target_check as tc, aggregate_fleet as af, verify_sample as vs
src=next((S/'fleet/results').glob('*/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s0of1920'))
base=O/'kind-count-probe';d=base/'f01-probe/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s0of1920'
shutil.copytree(src,d,dirs_exist_ok=True)
def change(c):
    c['tu']+=1;c['tri_tu']-=1;c['survivors']-=1
rs=json.loads((d/'run-summary.json').read_text());en=next(e for e in rs['levels'] if (e['n'],e['m'])==(13,23));before=dict(en['prune']['counts']);change(en['prune']['counts'])
(d/'run-summary.json').write_text(json.dumps(rs))
rows=json.loads((d/'counts.json').read_text());change(next(r for r in rows if r[:2]==[13,23])[3]);(d/'counts.json').write_text(json.dumps(rows))
problems=[];unresolved=[]
import argparse
args=argparse.Namespace(pins={'target':[23,65],'seed':10,'slices':[12,1920]},require={'hashes','g4'})
tc.vc().summary_audit(d,args,problems,unresolved)
c=tc.read_copy(d,23,65,5,False);scope=tc.replay_scope(c,c['audit'],23)
orig=af.read_copy(src,S/'fleet/results');changed=af.read_copy(d,base)
orig_digest=vs.copy_digest(orig);new_digest=vs.copy_digest(changed)
# The second producer's count copy can agree with the same wrong counts while its data and check receipt do not change.
twin=dict(orig,counts=changed['counts'],summary_digest=changed['summary_digest'])
diff=vs.judge_copy(changed,twin)
ch=en['children'];pc=en['prune']['counts']
arithmetic=(pc['input']==pc['kept']+pc['pruned']==ch and pc['pruned']==pc['tu']+pc['tri_tu']+pc['tri_refuted']+pc['refuted'] and pc['survivors']==pc['input']-pc['tu'] and pc['tri_survivors']==pc['survivors']-pc['tri_tu']-pc['tri_refuted'])
lines=[f"source {src}",f"changed intermediate (13,23) counts only: tu {before['tu']} -> {pc['tu']}, tri_tu {before['tri_tu']} -> {pc['tri_tu']}, survivors {before['survivors']} -> {pc['survivors']}",f'summary audit problems {problems}; unresolved {unresolved}',f'target read_copy reasons {c["why"]}; G4 scope reasons {scope}',f'counts arithmetic holds {arithmetic}; checked-file digest unchanged {orig_digest==new_digest}',f'judge_copy against equally changed count metadata (unaltered graph hashes) {diff}']
print('\n'.join(lines));(O/'kind-count-probe.txt').write_text('\n'.join(lines)+'\n')
