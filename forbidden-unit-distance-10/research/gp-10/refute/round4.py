"""Bounded Round 4 batches with live mathematical hints and exact checking."""
from round3 import *
from candidate_batches import best_frame
from gp10refute import run_method, timed, repair_tail, verify
from algebra import algebra_search
from graphs import patterns,canonical
import argparse,collections,fcntl,re
R4=MODULE/'evidence/round4'
C4=SCRATCH/'cand-r2'
FRONTIER=SOURCE/'residue-r2.g6'
HINT_ROOT=Path('<repo>/research/gp-10/embed/results/round5')
TRACKED=['round4.py','gp10refute.py','graphs.py','algebra.py','dag.py','quadratic_sos.py','amp_core.py']

def codes_input():
 data=FRONTIER.read_bytes();codes=data.decode().splitlines()
 assert len(codes)==len(set(codes))==702
 assert hashlib.sha256(data).hexdigest()=='d00de9d6cd2ac8afdc7aed26b93c060ac63bd84c22927c92bc3ecb6e70b22eb3'
 return codes

def read_hints(allowed):
 hints={};files=[];ignored=[]
 for p in sorted(HINT_ROOT.glob('likely-forbidden*')) if HINT_ROOT.exists() else []:
  if not p.is_file() or p.suffix not in {'.g6','.jsonl','.json','.txt','.tsv'}:continue
  raw=p.read_bytes();end=raw.rfind(b'\n')+1;data=raw[:end]
  files.append({'path':str(p),'bytes':len(raw),'complete_bytes':end,'sha256':hashlib.sha256(data).hexdigest()})
  for number,line in enumerate(data.decode().splitlines(),1):
   if not line.strip() or line.lstrip().startswith('#'):continue
   try:obj=json.loads(line)
   except ValueError:obj=None
   if isinstance(obj,dict):
    code=obj.get('g6',obj.get('graph6',obj.get('code')))
    reason=obj.get('reason',obj.get('diagnosis',json.dumps({k:v for k,v in obj.items() if k not in ['g6','graph6','code']},sort_keys=True)))
   else:
    parts=line.split(maxsplit=1);code=parts[0];reason=parts[1] if len(parts)>1 else '';obj={}
   if code not in allowed:
    ignored.append({'path':str(p),'line':number,'text':line[:200],'reason':'outside_frozen_B10_or_unparsed'});continue
   hint=hints.setdefault(code,{'reasons':set(),'pairs':set(),'sources':[]})
   if reason:hint['reasons'].add(str(reason))
   hint['sources'].append({'path':str(p),'line':number})
   pair_candidates=[]
   for key in ['pair','collision_pair','forced_pair']:
    if isinstance(obj.get(key),list):pair_candidates.append(obj[key])
   for key in ['pairs','collision_pairs']:
    if isinstance(obj.get(key),list):pair_candidates.extend(obj[key])
   for entry in obj.get('most_common_close_pairs',[]):
    if isinstance(entry,list) and len(entry)==2 and isinstance(entry[0],str):
     match=re.fullmatch(r'[\[(]\s*(\d+)\s*,\s*(\d+)\s*[\])]',entry[0])
     if match:pair_candidates.append([int(match[1]),int(match[2])])
   text=str(reason)
   if re.search(r'colli|coincid|same point',text,re.I):
    pair_candidates.extend([int(a),int(b)] for a,b in re.findall(r'[\[(]\s*(\d+)\s*,\s*(\d+)\s*[\])]',text))
    pair_candidates.extend([int(a),int(b)] for a,b in re.findall(r'(?:vertices|pair)\D{0,12}(\d+)\s*(?:,|and|=|-)\s*(\d+)',text,re.I))
    pair_candidates.extend([int(a),int(b)] for a,b in re.findall(r'p(\d+)\s*=\s*p(\d+)',text,re.I))
   n,edges=decode(code)
   for pair in pair_candidates:
    if isinstance(pair,(list,tuple)) and len(pair)==2 and all(type(v) is int and 0<=v<n for v in pair):
     pair=tuple(sorted(pair))
     if pair[0]!=pair[1] and pair not in edges:hint['pairs'].add(pair)
 for code,hint in hints.items():
  hint['reasons']=sorted(hint['reasons']);hint['pairs']=[list(p) for p in sorted(hint['pairs'])]
  hint['id']=hashlib.sha256(json.dumps({'reasons':hint['reasons'],'pairs':hint['pairs']},sort_keys=True).encode()).hexdigest()
 return hints,{'files':files,'ignored_lines':ignored,'hints':hints}

def results():
 latest={};applied=set();library={r['g6']:r for r in records(C4/'known.jsonl')}
 for directory in sorted(C4.glob('batch-*')):
  if not (directory/'work.jsonl').exists():continue
  plan=json.loads((directory/'plan.json').read_text());items={r['g6']:r for r in plan['selected']}
  for r in records(directory/'work.jsonl'):
   g=r['g6'];old=latest.get(g)
   if old is None or old['verdict']!='refuted':latest[g]=r
   hint=items[g].get('hint')
   if hint:applied.add((g,hint['id']))
   if r['verdict']=='refuted' and (directory/'verification.json').exists():library[g]=r
 return latest,applied,library

def prepare():
 configure();C4.mkdir(parents=True,exist_ok=True);R4.mkdir(parents=True,exist_ok=True)
 codes=codes_input();b10=set((ROOT/'research/gp-10/data/B10.g6').read_text().splitlines())
 assert set(codes)<=b10 and canonical(codes)==codes
 if not (C4/'known.jsonl').exists():
  source=C/'all-refuted.jsonl';inventory=json.loads((R/'round3-inventory.json').read_text())
  assert hashlib.sha256(source.read_bytes()).hexdigest()==inventory['artifacts'][str(source)]['sha256']
  (C4/'known.jsonl').write_bytes(source.read_bytes())
  (C4/'input.g6').write_bytes(FRONTIER.read_bytes())
  (R4/'preparation.json').write_text(json.dumps({'input_sha256':hashlib.sha256(FRONTIER.read_bytes()).hexdigest(),'count':len(codes),'edge_counts':dict(collections.Counter(len(decode(g)[1]) for g in codes)),'known_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'known_records':len(list(records(source))),'b10_sha256':hashlib.sha256((ROOT/'research/gp-10/data/B10.g6').read_bytes()).hexdigest(),'source_sha256':source_hashes()},indent=2)+'\n')
 return codes,b10

def source_hashes():return {name:hashlib.sha256((MODULE/name).read_bytes()).hexdigest() for name in TRACKED}

def distance_two(code):
 n,edges=decode(code);adj=[set() for _ in range(n)]
 for u,v in edges:adj[u].add(v);adj[v].add(u)
 return [[u,v] for u in range(n) for v in range(u+1,n) if (u,v) not in edges and adj[u]&adj[v]]

def algebra_attempt(code,method,seconds,hint):
 started=time.monotonic();stages=[];pairs=hint.get('pairs',[]) if hint else []
 extra=(pairs if pairs else distance_two(code)) if method=='null' else pairs
 try:
  with timed(seconds):
   cert,detail=algebra_search(code,method,seconds,frame=best_frame(code),extra_sat=extra,dag='auto',quadratic=method=='real',quadratic_rows=600,trace=lambda name:stages.append({'stage':name,'seconds':time.monotonic()-started}))
  if cert:
   with timed(max(.001,seconds-(time.monotonic()-started))):verify(code,cert,[],{})
  return cert,{**detail,'method':method,'seconds':time.monotonic()-started,'limit':seconds,'extra_sat':extra,'stages':stages}
 except (Exception,MemoryError) as exc:
  return None,{'method':method,'seconds':time.monotonic()-started,'limit':seconds,'extra_sat':extra,'stages':stages,'reason':type(exc).__name__+': '+str(exc)[:300]}

def closure(rows,library):
 expanded={r['g6']:r for r in rows};queue=list(rows)
 while queue:
  r=queue.pop();cert=r['cert'];target=cert.get('end',{}).get('refuted') if cert.get('type')=='tu' else cert.get('g6') if cert.get('type')=='sub' and 'index' not in cert else None
  if target and target not in expanded:expanded[target]=library[target];queue.append(library[target])
 return list(expanded.values())

def run(count):
 configure();C4.mkdir(parents=True,exist_ok=True)
 with (C4/'producer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  codes,allowed=prepare();latest,applied,library=results();hints,snapshot=read_hints(allowed)
  incomplete=[d for d in sorted(C4.glob('batch-*')) if not (d/'verification.json').exists()]
  if incomplete:
   directory=incomplete[0];plan=json.loads((directory/'plan.json').read_text());assert plan['source_sha256']==source_hashes(),'resume source changed'
  else:
   candidates=[]
   for g in set(codes)|set(hints):
    if latest.get(g,{}).get('verdict')=='refuted':continue
    hint=hints.get(g);retry=g in latest
    if retry and (not hint or (g,hint['id']) in applied):continue
    candidates.append({'g6':g,'edges':len(decode(g)[1]),'hint':hint,'retry':retry,'scope':'frontier' if g in codes else 'external_hint'})
   candidates.sort(key=lambda r:(not bool(r['hint']),r['edges'],r['g6']))
   selected=[];budget=0
   for item in candidates:
    allocation=(60 if item['retry'] else .5+40+(60 if item['hint'] else 20))
    if len(selected)>=count or budget+allocation>270:break
    selected.append(item);budget+=allocation
   if not selected:
    print(json.dumps({'selected':0,'processed_frontier':len(set(latest)&set(codes)),'hints':len(hints),'hint_files':len(snapshot['files'])}),flush=True);return
   directory=C4/f'batch-{len(list(C4.glob("batch-*")))+1:04d}';directory.mkdir()
   plan={'selected':selected,'maximum_method_budget_seconds':budget,'hints_snapshot':snapshot,'known':sorted(library),'source_sha256':source_hashes(),'input_sha256':hashlib.sha256(FRONTIER.read_bytes()).hexdigest()}
   (directory/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
  known={g:True for g in plan['known']};assert set(known)<=set(library)
  out=directory/'work.jsonl';log=directory/'timings.jsonl';pending=directory/'pending.json';repair_tail(out);repair_tail(log)
  done=list(records(out)) if out.exists() else [];selected=plan['selected'];assert [r['g6'] for r in done]==[r['g6'] for r in selected[:len(done)]]
  if pending.exists():
   interrupted=json.loads(pending.read_text());g=interrupted['g6']
   if g not in {r['g6'] for r in done}:
    assert g==selected[len(done)]['g6']
    recovered={'g6':g,'verdict':'unknown','cert':{'reason':'interrupted graph recovered','budget':interrupted}}
    with out.open('a') as f:flush_line(f,recovered)
    done.append(recovered)
   pending.unlink()
  forbidden=patterns(json.loads((UD/'data/forbidden-74.json').read_text()));forbidden_canonical()
  if any(not r['retry'] for r in selected):import amp_core
  started=time.monotonic()
  with out.open('a') as f,log.open('a') as timing:
   for item in selected[len(done):]:
    g=item['g6'];hint=item['hint'];seconds=30 if hint else 10
    schedule=[] if item['retry'] else [('tu',.5),('tree',40)]
    schedule += [('null',seconds),('real',seconds)]
    attempts=[];cert=None
    for method,limit in schedule:
     with pending.open('w') as checkpoint:flush_line(checkpoint,{'g6':g,'method':method,'limit':limit,'attempts':attempts})
     if method in ['null','real']:cert,detail=algebra_attempt(g,method,limit,hint)
     else:cert,detail=run_method(g,method,limit,forbidden,known,10000)
     attempts.append(detail)
     if cert:break
    row={'g6':g,'verdict':'refuted' if cert else 'unknown','cert':cert or {'reason':'Round 4 bounded methods exhausted','budget':{'attempts':attempts,'hint':hint,'frame':best_frame(g),'tree_states':10000,'retry':item['retry']}}}
    if len(json.dumps(row,separators=(',',':')).encode())+1>8*1024*1024:
     row={'g6':g,'verdict':'unknown','cert':{'reason':'verified identity exceeds official JSONL size limit','budget':{'attempts':attempts}}}
    flush_line(f,row);flush_line(timing,{'g6':g,'edges':item['edges'],'hint':hint,'retry':item['retry'],'attempts':attempts});pending.unlink()
    print(json.dumps({'g6':g,'edges':item['edges'],'verdict':row['verdict'],'method':attempts[-1]['method'],'seconds':sum(a['seconds'] for a in attempts)}),flush=True)
  rows=list(records(out));search_seconds=time.monotonic()-started
  result=check_run(directory,closure(rows,library),9)
  result.update({'work_records':len(rows),'work_refuted':sum(r['verdict']=='refuted' for r in rows),'search_seconds':search_seconds,'method_counts':dict(collections.Counter(r['cert']['type'] for r in rows if r['verdict']=='refuted'))})
  (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({'batch':directory.name,**{k:result[k] for k in ['work_records','work_refuted','search_seconds','method_counts','final_line']}}),flush=True)

def status():
 configure();codes,allowed=prepare();latest,applied,library=results();hints,snapshot=read_hints(allowed)
 attempts=collections.Counter();times=collections.Counter();types=collections.Counter();batches=[]
 for directory in sorted(C4.glob('batch-*')):
  if not (directory/'summary.json').exists():raise ValueError('unfinished batch '+str(directory))
  meta=json.loads((directory/'summary.json').read_text());assert meta['final_line']=='ACCEPT run verified';batches.append(meta)
  for row in records(directory/'timings.jsonl'):
   for a in row['attempts']:attempts[a['method']]+=1;times[a['method']]+=a['seconds']
 unknown={g for g in codes if latest.get(g,{}).get('verdict')!='refuted'};unprocessed=set(codes)-set(latest);refuted=set(codes)-unknown
 for g in refuted:types[latest[g]['cert']['type']]+=1
 pending_hints={g for g,h in hints.items() if latest.get(g,{}).get('verdict')!='refuted' and (g,h['id']) not in applied}
 for name,values in [('UNKNOWN.g6',unknown),('UNPROCESSED.g6',unprocessed),('REFUTED.g6',refuted)]:
  (C4/name).write_text(''.join(g+'\n' for g in sorted(values)))
 result={'frontier_count':len(codes),'processed':len(set(codes)&set(latest)),'new_refuted':len(refuted),'still_undecided':len(unknown),'unprocessed':len(unprocessed),'certificate_types':dict(types),'attempts':dict(attempts),'method_seconds':dict(times),'search_seconds':sum(b['search_seconds'] for b in batches),'checker_seconds':sum(b['seconds'] for b in batches),'batch_count':len(batches),'hint_count':len(hints),'pending_hints':len(pending_hints),'extra_graphs':len(set(latest)-set(codes)),'hints_snapshot':snapshot}
 (C4/'STATUS.json').write_text(json.dumps(result,indent=2)+'\n');(R4/'status.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='hints_snapshot'}),flush=True);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','batch','status']);p.add_argument('--count',type=int,default=4);a=p.parse_args()
 if a.action=='prepare':prepare();print('prepared',flush=True)
 elif a.action=='batch':run(a.count)
 else:status()
if __name__=='__main__':main()
