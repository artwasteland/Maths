"""Reconcile the finished candidate samples and check the combined run."""
from candidate_batches import *
import candidate_status
import datetime

def main():
 configure();candidate_status.main()
 status=json.loads((C/'STATUS.json').read_text())
 codes,tree,emb,snap=snapshot()
 assert snap==status['snapshot']
 assert status['unprocessed']==status['pending_tree']==0
 assert len(tree)==len(emb)==len(codes)
 own={};method_reasons=collections.defaultdict(collections.Counter);stages=collections.Counter();order=[]
 for directory in sorted(C.glob('batch-*')):
  for row in records(directory/'work.jsonl'):
   assert row['g6'] not in own;own[row['g6']]=row;order.append(len(decode(row['g6'])[1]))
  for row in records(directory/'timings.jsonl'):
   for a in row['attempts']:
    method_reasons[a['method']][a.get('reason','completed')]+=1
    if a.get('stages'):stages[a['stages'][-1]['stage']]+=1
 assert order==sorted(order),'edge-count ordering'
 external_ref={g:r for g,r in tree.items() if r['verdict']=='refuted'}
 external_emb={g for g,r in emb.items() if r['verdict']=='embedded'}
 new_ref={g:r for g,r in own.items() if r['verdict']=='refuted'}
 assert not (set(external_ref)|set(new_ref))&external_emb
 assert not set(new_ref)&set(external_ref)
 combined=dict(external_ref)
 for g in codes:
  if g not in external_ref and g not in external_emb:combined[g]=own[g]
 unresolved={g for g,r in combined.items() if r['verdict']=='unknown'}
 assert unresolved==set((C/'UNKNOWN.g6').read_text().splitlines())
 for name,rows in [('new-refuted.jsonl',new_ref),('all-refuted.jsonl',dict(external_ref,**new_ref)),('own-results.jsonl',own)]:
  with (C/name).open('w') as f:
   for g in sorted(rows):flush_line(f,rows[g])
 for name,values in [('EXTERNAL-EMBEDDED.g6',external_emb),('EXTERNAL-TREE-REFUTED.g6',external_ref)]:
  (C/name).write_text(''.join(g+'\n' for g in sorted(values)))
 check_result=check_run(C/'checker-final',[combined[g] for g in sorted(combined)],9)
 assert len(set(canonical(codes)))==len(codes),'isomorphic duplicate input'
 remaining=set(codes);b10=ROOT/'research/gp-10/data/B10.g6'
 h=hashlib.sha256();b10_count=0
 with b10.open('rb') as f:
  for line in f:
   h.update(line);b10_count+=1;remaining.discard(line.decode().strip())
 assert not remaining,'candidate outside frozen B10'
 sizes=[]
 for path in list(C.glob('batch-*/records.jsonl'))+[C/'checker-final/records.jsonl',R/'F39.null-dag.jsonl']:
  with path.open('rb') as f:
   for line in f:
    assert len(line)<=8*1024*1024,(path,len(line));sizes.append(len(line))
 plans=[json.loads(p.read_text()) for p in sorted(C.glob('batch-*/plan.json'))]
 allsat=[{'directory':str(p.parent),'records':len(list(records(p.parent/'work.jsonl'))),'search_seconds':json.loads((p.parent/'batch-summary.json').read_text())['search_seconds']} for p in sorted(C.glob('batch-*/plan.json')) if json.loads(p.read_text()).get('all_sat')]
 result={'status':'COMPLETE bounded candidate pass','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'candidate_status':status,'combined_check':check_result,'new_refutations':[{'g6':g,'edges':len(decode(g)[1]),'type':r['cert']['type'],'terminal':r['cert'].get('end'),'steps':r['cert'].get('steps')} for g,r in sorted(new_ref.items())],
  'candidate_edge_counts':dict(collections.Counter(len(decode(g)[1]) for g in codes)),
  'processed_edge_counts':dict(collections.Counter(order)),
  'unknown_edge_counts':dict(collections.Counter(len(decode(g)[1]) for g in unresolved)),
  'method_reasons':dict(method_reasons),'last_stages':dict(stages),'all_sat_pilot':allsat,
  'batch_count':len(plans),'maximum_allocated_batch_seconds':max(p['maximum_method_budget_seconds'] for p in plans),
  'max_accepted_record_bytes':max(sizes),'b10_membership':{'path':str(b10),'lines':b10_count,'sha256':h.hexdigest(),'all_candidates_present':True},
  'canonical_distinct_candidates':len(codes),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob('*.py')}}
 (C/'FINAL.json').write_text(json.dumps(result,indent=2)+'\n');(R/'candidate-final.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'combined_check':check_result,'new_refutations':result['new_refutations'],'still_undecided':len(unresolved),'batch_count':len(plans)}),flush=True)
if __name__=='__main__':main()
