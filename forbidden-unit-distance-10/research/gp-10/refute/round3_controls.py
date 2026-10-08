"""Close the forbidden controls and validate the read-only external tree library."""
from round3 import *
from candidate_batches import snapshot

def main():
 configure();R.mkdir(exist_ok=True);C.mkdir(parents=True,exist_ok=True);f39=next(records(R/'F39.null-dag.jsonl'));results={}
 for name,old,limit in [('GP74','checker-GP74-round2',0),('B9p-forbidden','checker-B9p-final',8)]:
  rows=[f39 if r['g6']==f39['g6'] else r for r in records(MODULE/'evidence/round2'/old/'records.jsonl')]
  assert all(r['verdict']=='refuted' for r in rows);results[name]=check_run(R/('checker-'+name),rows,limit)
  if name=='GP74':
   with (R/'GP74.refuted.jsonl').open('w') as f:
    for row in rows:flush_line(f,row)
  del rows
 codes,tree,emb,snap=snapshot();assert set(codes)<=set((ROOT/'research/gp-10/data/B10.g6').read_text().splitlines())
 rows=[r for r in tree.values() if r['verdict']=='refuted'];results['external-tree']=check_run(C/'tree-library-check',rows,9)
 with (C/'tree-library.jsonl').open('w') as f:
  for row in rows:flush_line(f,row)
 results['external_snapshot']=snap;(R/'control-closure.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:v for k,v in results.items() if k!='external_snapshot'}),flush=True)
if __name__=='__main__':main()
