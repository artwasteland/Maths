from common import *
import json,sqlite3,hashlib,collections,copy
import gp10check as ck
redirect();start_monitor();t=time.monotonic()
methods=sys.argv[1:];sample=(OUT/'sample.g6').read_text().splitlines();selected={};origins={};allaccepted=collections.Counter()
for method in methods:
 for line in open(OUT/(method+'-records.jsonl')):
  r=json.loads(line);g=r['g6'];v=r['verdict']
  if v=='unknown':continue
  allaccepted[method]+=1
  if g in selected:
   assert selected[g]['verdict']==v,(g,origins[g],method)
   if len(json.dumps(r))>=len(json.dumps(selected[g])):continue
  selected[g]=r;origins[g]=method
DB=sqlite3.connect(OUT/'gp10.sqlite');deps={}
def include(g):
 if g in selected or g in deps:return
 raw=DB.execute('SELECT raw FROM records WHERE g6=?',(g,)).fetchone();assert raw,g
 r=json.loads(raw[0]);deps[g]=r;dependency(r)
def dependency(r):
 c=r['cert'];ty=c['type']
 if ty in ('sub','super') and 'index' not in c:include(c['g6'])
 if ty=='tu' and 'refuted' in c['end']:include(c['end']['refuted'])
for r in list(selected.values()):dependency(r)
run=OUT/'sample-check';run.mkdir(exist_ok=True);rows={**selected,**deps}
for g in sample:
 if g not in rows:rows[g]={'g6':g,'verdict':'unknown','cert':{'reason':'No measured method returned an accepted certificate','budget':{'methods':methods}}}
raw=''.join(g+'\n' for g in sorted(rows));(run/'input.g6').write_text(raw);(run/'records.jsonl').write_text(''.join(json.dumps(rows[g],separators=(',',':'))+'\n' for g in sorted(rows)));(run/'UNKNOWN.g6').write_text(''.join(g+'\n' for g in sorted(rows) if rows[g]['verdict']=='unknown'))
(run/'run.json').write_text(json.dumps({'profile':'sample','input':'input.g6','input_sha256':hashlib.sha256(raw.encode()).hexdigest(),'records':['records.jsonl'],'forbidden_limit':9,'derive':False}))
with open(run/'checker.log','w') as log:report=ck.Run(run,emit=lambda s:log.write(s+'\n')).execute()
assert report['status']=='ACCEPT',report
# Local rule-specific mutations of actual positive sample certificates.
reds=[];check=ck.Checker(9);redirect()
for kind in ('exact','tu','tree','null','real','null-dag','real-dag'):
 r=next((copy.deepcopy(r) for r in selected.values() if r['cert']['type']==kind),None)
 if r is None:continue
 if kind=='exact':
  z=r['cert']['coords'][0][0][0];r['cert']['coords'][0][0][0]=str(ck.rational(z)+1);expected='edge_equation'
 elif kind=='tu':
  step=r['cert']['steps'][0];step['pair']=[step['pair'][0],next(i for i in range(11) if i not in step['pair'])];expected='tu_distinguished_pair'
 else:continue
 try:check.verify(r);raise AssertionError('red unexpectedly accepted')
 except ck.Rejection as exc:reds.append({'kind':kind,'reason':exc.reason,'expected':expected});assert exc.reason==expected
summary={'methods':methods,'individual_accepted_counts':dict(allaccepted),'sample_counts':dict(collections.Counter(rows[g]['verdict'] for g in sample)),'dependency_records':len(deps),'report_status':report['status'],'checker_seconds':report['elapsed_seconds'],'checker_sha256':report['checker_sha256'],'kernel_sha256':report['kernel_sha256'],'reds':reds,'seconds':time.monotonic()-t,**usage()}
(OUT/'sample-check-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
