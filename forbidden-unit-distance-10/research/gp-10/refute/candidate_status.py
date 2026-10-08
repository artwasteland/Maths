"""Reconcile checked candidate work with complete prefixes of live streams."""
from candidate_batches import *

def main():
 configure();codes,tree,emb,snap=snapshot();attempts=collections.Counter();times=collections.Counter();types=collections.Counter();own={};batches=[]
 for directory in sorted(C.glob('batch-*')):
  if not (directory/'verification.json').exists():raise ValueError('unchecked batch '+str(directory))
  verification=json.loads((directory/'verification.json').read_text());assert verification['final_line']=='ACCEPT run verified'
  meta=json.loads((directory/'batch-summary.json').read_text());batches.append({k:meta.get(k) for k in ['directory','records','refuted','search_seconds','seconds','dependency_records','method_counts','final_line']})
  for rec in records(directory/'work.jsonl'):
   if rec['g6'] in own:raise ValueError('duplicate processed graph')
   own[rec['g6']]={'verdict':rec['verdict'],'path':str(directory/'work.jsonl'),'type':rec['cert'].get('type')}
   if rec['verdict']=='refuted':types[rec['cert']['type']]+=1
  for row in records(directory/'timings.jsonl'):
   for a in row['attempts']:attempts[a['method']]+=1;times[a['method']]+=a['seconds']
 external_ref={g for g,r in tree.items() if r['verdict']=='refuted'};external_emb={g for g,r in emb.items() if r['verdict']=='embedded'};new_ref={g for g,r in own.items() if r['verdict']=='refuted'}
 assert not new_ref & external_emb,'conflicting positive verdicts'
 eligible={g for g in codes if tree.get(g,{}).get('verdict')=='unknown' and g not in external_emb}
 remaining=eligible-set(own);unknown=set(codes)-external_ref-external_emb-new_ref
 for name,values in [('UNKNOWN.g6',unknown),('UNPROCESSED.g6',remaining),('REFUTED.g6',new_ref),('eligible.g6',eligible)]:
  (C/name).write_text(''.join(g+'\n' for g in sorted(values)))
 result={'candidate_count':len(codes),'tree_completed':len(tree),'external_refuted':len(external_ref),'external_embedded':len(external_emb),'processed':len(own),'new_refuted':len(new_ref),'current_eligible':len(eligible),'unprocessed':len(remaining),'pending_tree':len(set(codes)-set(tree)),'still_undecided':len(unknown),'processed_later_embedded':len(set(own)&external_emb),'per_method_attempts':dict(attempts),'per_method_seconds':dict(times),'new_certificate_types':dict(types),'batch_search_seconds':sum(b['search_seconds'] for b in batches),'batch_check_seconds':sum(b['seconds'] for b in batches),'snapshot':snap,'batches':batches}
 (C/'STATUS.json').write_text(json.dumps(result,indent=2)+'\n');(R/'candidate-status.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['snapshot','batches']}),flush=True)
if __name__=='__main__':main()
