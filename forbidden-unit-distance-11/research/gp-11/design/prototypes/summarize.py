from common import *
import json,collections,math,statistics,hashlib
def timed_out(x):
 if isinstance(x,dict):return x.get('timeout') is True or any(timed_out(v) for k,v in x.items() if k!='timeout')
 if isinstance(x,list):return any(timed_out(v) for v in x)
 return isinstance(x,str) and any(t in x.lower() for t in ('timeout','timed out','deadline'))
methods=['lattice','lattice36','lattice30','host','numeric','extension','tree','tu','null','real','msolve','portfolio']
sample=(OUT/'sample.g6').read_text().splitlines();results={};stage={};sets={}
for m in methods:
 p=OUT/(m+'-stats.jsonl')
 if not p.exists():continue
 rr=[json.loads(s) for s in p.read_text().splitlines()];results[m]={r['g6']:r for r in rr};stage[m]={'attempted':len(rr),'counts':dict(collections.Counter(r['verdict'] for r in rr)),'search_seconds':sum(r['seconds'] for r in rr),'check_seconds':sum(r.get('checker_seconds',0) for r in rr),'timeouts':sum(timed_out(r.get('meta',{})) for r in rr)}
 recs=[json.loads(x) for x in (OUT/(m+'-records.jsonl')).read_text().splitlines()];sets[m]={r['g6'] for r in recs if r['verdict']!='unknown'}
# Cost of two concrete serial per-graph schedules, inferred from the independently timed method calls.
orders=[['tu','lattice','extension','host','tree','null','real','msolve','portfolio'],['tu','extension','lattice','host','tree','null','real','msolve','portfolio']]
schedules=[]
for order in orders:
 unknown=set(sample);times={};hits={}
 for m in order:
  if m not in results:continue
  times[m]=sum(r['seconds']+r.get('checker_seconds',0) for g,r in results[m].items() if g in unknown)
  gain=unknown&sets[m];hits[m]=len(gain);unknown-=gain
 total=sum(times.values());schedules.append({'order':order,'stage_seconds':times,'incremental_hits':hits,'unknown':len(unknown),'seconds_500':total,'ideal_4core_machine_hours_B11':total*448708/500/14400})
u=len(set(sample)-set().union(*sets.values()));p=u/500;z=1.95996398454;den=1+z*z/500;mid=(p+z*z/1000)/den;half=z*math.sqrt(p*(1-p)/500+z*z/(4*500**2))/den
structure=json.loads((OUT/'propagation-per-sample.json').read_text());struct={r['g6']:r for r in structure}
E=set();R=set()
for m in results:
 for g,r in results[m].items():
  if r['verdict']=='embedded':E.add(g)
  if r['verdict']=='refuted':R.add(g)
assert not E&R
strata={}
for name,pred in [('degree2',lambda r:r['degree2']>0),('min_degree3',lambda r:r['degree2']==0),('maximal',lambda r:r['direct_parents']==0),('nonmaximal',lambda r:r['direct_parents']>0)]:
 ss={g for g in sample if pred(struct[g])};strata[name]={'n':len(ss),'E':len(ss&E),'R':len(ss&R),'unknown':len(ss-E-R)}
fanout={}
for name,ss,key in [('all_as_E',set(sample),'descendants_including_self'),('all_as_R',set(sample),'ancestors_including_self'),('actual_E',E,'descendants_including_self'),('actual_R',R,'ancestors_including_self')]:
 vv=[struct[g][key] for g in ss];fanout[name]={'n':len(vv),'mean':statistics.mean(vv),'median':statistics.median(vv),'maximum':max(vv),'sum':sum(vv)}
numeric=list(results['numeric'].values());converged=[r for r in numeric if r.get('meta',{}).get('residual',1)>-1 and r.get('meta',{}).get('residual',1)<=1e-8];separated=[r for r in converged if r['meta'].get('minimum_distance',0)>=1e-3]
ext=list(results['extension'].values());extmeta={'eligible_degree2':sum(r.get('meta',{}).get('degree2_vertices',0)>0 for r in ext),'base_found':sum(r.get('meta',{}).get('deletions_in_B10',0)>0 for r in ext),'no_degree2':sum(r.get('meta',{}).get('degree2_vertices')==0 for r in ext),'no_B10_base_despite_degree2':sum(r.get('meta',{}).get('degree2_vertices',0)>0 and r['meta'].get('deletions_in_B10',0)==0 for r in ext),'timeouts_or_errors_losing_meta':sum('degree2_vertices' not in r.get('meta',{}) for r in ext)}
res={'stages':stage,'sample_E':len(E),'sample_R':len(R),'sample_U':u,'unknown_fraction_Wilson95':[mid-half,mid+half],'unknown_population_projection_Wilson95':[(mid-half)*448708,(mid+half)*448708],'point_unknown_population':p*448708,'schedules':schedules,'sample_strata':strata,'propagation_fanout':fanout,'numeric_converged':len(converged),'numeric_separated_1e_3':len(separated),'extension_bases':extmeta}
(OUT/'MEASUREMENTS.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
