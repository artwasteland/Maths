"""Targeted-saturation exact identity and one-field corruption checks."""
from round3 import *
from gp10refute import run_method
from algebra import system,unsparse
from dag import collision_dag
from graphs import encode,canonical
import itertools,copy

def main():
 configure();code=canonical([encode(5,set(itertools.combinations(range(4),2)))])[0]
 cert,detail=run_method(code,'null',5);assert cert is not None,detail
 ctx,coords,gens=system(code,cert['frame'],cert['sat']);n,edges=decode(code);pair=next(p for p in itertools.combinations(range(n),2) if p not in edges and list(p) not in cert['sat'])
 distance=sum(((coords[pair[0]][j]-coords[pair[1]][j])**2 for j in (0,1)),ctx.constant(0))
 helpers=[(p,{key:ctx.constant(1)}) for key,p in gens.items()];cofs=[unsparse(ctx,cert['cofactors'].get(key,[]))*distance for key in gens]
 proof=collision_dag(code,cert['frame'],cert['sat'],ctx,helpers,cofs,distance,pair);rec={'g6':code,'verdict':'refuted','cert':proof}
 results=[check_run(R/'tests-collision-positive',[rec],0)]
 bad=copy.deepcopy(rec);key=f's:{pair[0]},{pair[1]}';bad['cert']['rows'][-1]['cofactors'][key][0][0]='-2';results.append(check_run(R/'tests-collision-red',[bad],0,'REJECT run records_rejected','dag_row_identity'))
 discoveries=[]
 for i in [16,68]:
  code=forbidden_canonical()[i];cert,detail=run_method(code,'portfolio',10);discoveries.append({'index':i,'verdict':'refuted' if cert else 'unknown','detail':detail})
  if cert:results.append(check_run(R/('tests-collision-discovery-'+str(i)),[{'g6':code,'verdict':'refuted','cert':cert}],0))
 named=json.loads((MODULE/'fixtures/named.json').read_text());safe=[]
 for name in ['prism','petersen','spindle']:
  cert,detail=run_method(named[name],'portfolio',1);assert cert is None,('soundness failure',name);safe.append({'name':name,'detail':detail})
 result={'status':'PASS','official_checks':results,'discovery_trials':discoveries,'safe_controls':safe};(R/'collision-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
