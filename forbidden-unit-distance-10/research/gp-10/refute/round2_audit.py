"""Assemble and officially check only current-format Round 2 results."""
from round2 import *
import contextlib,collections

def checked(tag,paths,limit):
 run=export(tag,paths,limit)
 with (run/'check.log').open('w') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):rc=check(run)
 output=(run/'check.log').read_text().splitlines()
 rows=list(records(run/'records.jsonl'));result={'run':str(run.relative_to(MODULE)),'checker_exit':rc,'final_line':output[-1],'records':len(rows),'refuted':sum(r['verdict']=='refuted' for r in rows),'unknown':[r['g6'] for r in rows if r['verdict']=='unknown'],'certificate_types':dict(collections.Counter(r['cert']['type'] for r in rows if r['verdict']=='refuted')),'max_line_bytes':max(map(len,(run/'records.jsonl').read_bytes().splitlines(keepends=True)))}
 assert rc==0 and output[-1]=='ACCEPT run verified',result
 print(json.dumps(result),flush=True);return result

def main():
 configure();result={};retries=[R/(tag+'.jsonl') for tag in ['controls-tree-retry12','controls-tree-retry40','controls-null-retry10','final-stall22','final-stall38','final-stall66']]
 result['retry_records']=checked('checker-focused-retries',retries,0)
 result['GP74']=checked('checker-GP74-round2',[MODULE/'evidence/GP74.combined.jsonl',*retries],0)
 for suite,limit in [('B8p',7),('B9p',8)]:
  allowed=set((R/(suite+'.g6')).read_text().splitlines());paths=[R/(suite+'-'+m+'.jsonl') for m in ['tu','tree','null','real']]+retries
  filtered=R/(suite+'-fresh-candidates.jsonl')
  with filtered.open('w') as f:
   for path in paths:
    for rec in records(path):
     if rec['g6'] in allowed:flush_line(f,rec)
  result[suite]=checked('checker-'+suite+'-final',[filtered],limit)
  result[suite+'-replay']=checked('checker-'+suite+'-replay',[R/(suite+'-replay.jsonl')],limit)
  method_success={}
  for method in ['tu','tree','null','real']:
   done={rec['g6'] for path in paths for rec in records(path) if rec['g6'] in allowed and rec['verdict']=='refuted' and rec['cert']['type']==method}
   method_success[method]=len(done)
  result[suite]['fresh_cumulative_by_certificate_type']=method_success
  timings=list(records(R/(suite+'-replay.jsonl.timings.jsonl')))
  result[suite+'-replay']['graph_seconds']=sum(sum(a['seconds'] for a in r['attempts']) for r in timings)
 (R/'round2-final-audit.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
