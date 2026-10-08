"""Bounded candidate batches, live-input snapshots, and official checking."""
from round3 import *
from gp10refute import run_method,repair_tail
from graphs import patterns,canonical
import argparse,collections,fcntl

def snapshot_file(path):
 result={};h=hashlib.sha256();consumed=0;size=path.stat().st_size if path.exists() else 0
 if path.exists():
  with path.open('rb') as f:
   while f.tell()<size:
    line=f.readline()
    if f.tell()>size or not line.endswith(b'\n'):break
    rec=json.loads(line);code=rec['g6']
    if code in result:raise ValueError('duplicate source record '+str(path))
    result[code]=rec;h.update(line);consumed+=len(line)
 return result,{'path':str(path),'snapshot_bytes':size,'consumed_bytes':consumed,'sha256':h.hexdigest(),'verdicts':dict(collections.Counter(r['verdict'] for r in result.values()))}

def snapshot():
 data=(SOURCE/'cand1515.g6').read_bytes();codes=data.decode().splitlines();assert len(codes)==len(set(codes))==1515
 tree,tm=snapshot_file(SOURCE/'tree5.jsonl');emb,em=snapshot_file(SOURCE/'emb.jsonl')
 assert set(tree)<=set(codes) and set(emb)<=set(codes)
 meta=json.loads((SOURCE/'tree5.jsonl.meta.json').read_text())
 if meta['source_sha256']['amp_core.py']!=hashlib.sha256((MODULE/'amp_core.py').read_bytes()).hexdigest():raise ValueError('tree core differs: fixed-point reuse not authorized by this schedule')
 return codes,tree,emb,{'candidate_sha256':hashlib.sha256(data).hexdigest(),'tree':tm,'embed':em,'tree_configuration':meta}

def old_results():
 result={}
 for d in sorted(C.glob('batch-*')):
  p=d/'work.jsonl'
  if not p.exists():continue
  for r in records(p):
   if r['g6'] in result:raise ValueError('duplicate candidate across batches')
   result[r['g6']]={'verdict':r['verdict'],'path':str(p)}
 return result

def needs_tree(rec):
 attempts=rec['cert'].get('budget',{}).get('attempts',[])
 return not attempts or any('reason' in a or a.get('stops',{}).get('state_limit') for a in attempts)

def best_frame(code):
 n,edges=decode(code);adj=[set() for _ in range(n)]
 for u,v in edges:adj[u].add(v);adj[v].add(u)
 return list(min(edges,key=lambda e:(-len(adj[e[0]]&adj[e[1]]),-len(adj[e[0]])-len(adj[e[1]]),e)))

def run(a):
 configure();C.mkdir(exist_ok=True,parents=True)
 with (C/'producer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  codes,tree,emb,snap=snapshot();old=old_results()
  library={r['g6']:{'path':str(C/'tree-library.jsonl')} for r in records(C/'tree-library.jsonl')} if (C/'tree-library.jsonl').exists() else {}
  library.update({g:row for g,row in old.items() if row['verdict']=='refuted' and (Path(row['path']).parent/'verification.json').exists()})
  known={g:True for g in library}
  incomplete=[d for d in sorted(C.glob('batch-*')) if (d/'plan.json').exists() and not (d/'verification.json').exists()]
  if incomplete:
   directory=incomplete[0];plan=json.loads((directory/'plan.json').read_text());selected=plan['selected'];print('RESUME',directory.name,flush=True)
  else:
   remaining=[g for g in codes if g not in old and tree.get(g,{}).get('verdict')!='refuted' and emb.get(g,{}).get('verdict')!='embedded']
   level=min((len(decode(g)[1]) for g in remaining),default=None)
   eligible=sorted((g for g in remaining if tree.get(g,{}).get('verdict')=='unknown' and len(decode(g)[1])==level),key=lambda g:(len(decode(g)[1]),g))
   selected=[];worst=0
   for code in eligible:
    retry=needs_tree(tree[code]);allocation=0.5+a.algebra_seconds+(12 if retry else 0)
    if len(selected)>=a.count or worst+allocation>240:break
    selected.append({'g6':code,'edges':len(decode(code)[1]),'tree_retry':retry,'external_tree':tree[code]['cert'].get('budget',{}).get('attempts',[])});worst+=allocation
   if not selected:print(json.dumps({'selected':0,'tree_records':len(tree),'embedded':sum(r['verdict']=='embedded' for r in emb.values()),'already_processed':len(old),'edge_level':level,'waiting_for_tree':sum(g not in tree and len(decode(g)[1])==level for g in remaining)}));return
   directory=C/f'batch-{len(list(C.glob("batch-*")))+1:04d}';directory.mkdir()
   plan={'selected':selected,'maximum_method_budget_seconds':worst,'algebra_seconds':a.algebra_seconds,'all_sat':a.all_sat,'known_refutations':sorted(known),'known_library_sha256':hashlib.sha256((C/'tree-library.jsonl').read_bytes()).hexdigest() if (C/'tree-library.jsonl').exists() else None,'algebra_policy':'shared null/real basis, DAG on expansion-size estimate; triangle-rich edge frame','snapshot':snap,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob('*.py')}}
   (directory/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
  known={g:True for g in plan.get('known_refutations',[])}
  if not set(known)<=set(library):raise ValueError('known dependency disappeared')
  for name,sha in plan['source_sha256'].items():
   if name in ['gp10refute.py','graphs.py','algebra.py','dag.py','quadratic_sos.py','amp_core.py','candidate_batches.py'] and hashlib.sha256((MODULE/name).read_bytes()).hexdigest()!=sha:raise ValueError('resume source changed '+name)
  out=directory/'work.jsonl';timings=directory/'timings.jsonl';pending=directory/'pending.json';repair_tail(out);repair_tail(timings)
  prior=list(records(out)) if out.exists() else [];selected_codes=[x['g6'] for x in selected]
  if [r['g6'] for r in prior]!=selected_codes[:len(prior)]:raise ValueError('batch resume coverage or order mismatch')
  completed={r['g6']:r for r in prior}
  if pending.exists():
   interrupted=json.loads(pending.read_text());code=interrupted['g6']
   if code not in selected_codes:raise ValueError('pending graph outside batch')
   if code not in completed:
    if len(completed)>=len(selected_codes) or code!=selected_codes[len(completed)]:raise ValueError('pending graph order mismatch')
    rec={'g6':code,'verdict':'unknown','cert':{'reason':'interrupted method recovered on resume','budget':interrupted}}
    with out.open('a') as f:flush_line(f,rec)
    completed[code]=rec
   pending.unlink()
  forbidden=patterns(json.loads((UD/'data/forbidden-74.json').read_text()));forbidden_canonical()
  if any(x['tree_retry'] for x in selected):import amp_core
  started=time.monotonic()
  with out.open('a') as f,timings.open('a') as log:
   for item in selected:
    code=item['g6']
    if code in completed:continue
    attempts=[];cert=None
    schedule=[('tu',0.5)]+([('tree',12)] if item['tree_retry'] else [])+[('portfolio',plan.get('algebra_seconds',5))]
    for method,seconds in schedule:
     pending.write_text(json.dumps({'g6':code,'method':method,'seconds':seconds,'attempts':attempts})+'\n')
     cert,detail=run_method(code,method,seconds,forbidden,known,1000,all_pairs=plan.get('all_sat',False),frame=best_frame(code))
     attempts.append(detail)
     if cert:break
    rec={'g6':code,'verdict':'refuted' if cert else 'unknown','cert':cert or {'reason':'bounded full-method schedule exhausted','budget':{'attempts':attempts,'external_tree':item['external_tree'],'tree_retried':item['tree_retry'],'dag_policy':'automatic sharing when cofactor expansion term bound exceeds 60000','frame':best_frame(code),'shared_null_real_budget':plan.get('algebra_seconds',5),'all_sat':plan.get('all_sat',False)}}}
    flush_line(f,rec);flush_line(log,{'g6':code,'edges':item['edges'],'attempts':attempts});pending.unlink()
    print(json.dumps({'g6':code,'edges':item['edges'],'verdict':rec['verdict'],'method':attempts[-1]['method'],'seconds':sum(x['seconds'] for x in attempts)}),flush=True)
    if out.stat().st_size>4*1024*1024:break
  rows=list(records(out));_,tree_now,emb_now,lastsnap=snapshot()
  conflict=[r['g6'] for r in rows if r['verdict']=='refuted' and emb_now.get(r['g6'],{}).get('verdict')=='embedded']
  if conflict:raise ValueError('fatal producer conflict with live embed stream: '+repr(conflict))
  own_rows=rows;expanded={r['g6']:r for r in rows};queue=list(rows)
  while queue:
   r=queue.pop();cert=r['cert'];target=cert.get('end',{}).get('refuted') if cert.get('type')=='tu' else cert.get('g6') if cert.get('type')=='sub' and 'index' not in cert else None
   if target and target not in expanded:
    dependency=next(r for r in records(library[target]['path']) if r['g6']==target)
    expanded[target]=dependency;queue.append(dependency)
  result=check_run(directory,expanded.values(),9);result['verified_records']=result['records'];result['records']=len(own_rows);result['refuted']=sum(r['verdict']=='refuted' for r in own_rows);result['dependency_records']=len(expanded)-len(own_rows);result['actual_selected']=[r['g6'] for r in own_rows];result['search_seconds']=time.monotonic()-started-result['seconds'];result['last_snapshot']=lastsnap
  result['method_counts']=dict(collections.Counter(r['cert']['type'] for r in rows if r['verdict']=='refuted'))
  (directory/'batch-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['records','refuted','final_line','search_seconds','method_counts']}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=22);p.add_argument('--all-sat',action='store_true');p.add_argument('--algebra-seconds',type=float,default=5);a=p.parse_args();assert a.count>0 and 0<a.algebra_seconds<=120;run(a)
if __name__=='__main__':main()
