from common import *
import json,hashlib
import gp10check as ck
redirect();start_monitor();run=OUT/'all-unknown-check';run.mkdir(exist_ok=True)
raw=(OUT/'B11.g6').read_bytes();(run/'input.g6').write_bytes(raw);(run/'UNKNOWN.g6').write_bytes(raw)
with open(run/'records.jsonl','w') as f:
 for g in raw.decode().splitlines():f.write(json.dumps({'g6':g,'verdict':'unknown','cert':{'reason':'streaming throughput benchmark only','budget':{}}},separators=(',',':'))+'\n')
(run/'run.json').write_text(json.dumps({'profile':'sample','input':'input.g6','input_sha256':hashlib.sha256(raw).hexdigest(),'records':['records.jsonl'],'forbidden_limit':9,'derive':False}))
t=time.monotonic()
with open(run/'checker.log','w') as log:r=ck.Run(run,emit=lambda s:log.write(s+'\n')).execute()
summary={'status':r['status'],'counts':r.get('counts'),'conditional':r.get('conditional'),'seconds':time.monotonic()-t,'scope':'All-unknown sample-profile streaming benchmark; no certificates or B11 minimality checked',**usage()};(OUT/'stream-check-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
assert r['status']=='ACCEPT' and r['counts']['unknown']==448708 and r['conditional']
