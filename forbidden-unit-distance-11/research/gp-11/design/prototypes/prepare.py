from common import *
import hashlib,json,random,gzip,sqlite3,collections
start_monitor();t=time.monotonic()
lines=(OUT/'B11.g6').read_text().splitlines()
assert lines==sorted(set(lines)) and len(lines)==448708
indices=sorted(random.Random(20261001).sample(range(len(lines)),500))
(OUT/'sample.g6').write_text(''.join(lines[i]+'\n' for i in indices))
(OUT/'sample-manifest.json').write_text(json.dumps({'seed':20261001,'algorithm':'Python random.Random(seed).sample(range(N),500), sorted indices into byte-sorted nauty-labelg default canonical B11','population':len(lines),'zero_based_indices':indices,'population_sha256':hashlib.sha256((OUT/'B11.g6').read_bytes()).hexdigest(),'sample_sha256':hashlib.sha256((OUT/'sample.g6').read_bytes()).hexdigest()},indent=2))
db=sqlite3.connect(OUT/'gp10.sqlite');db.execute('CREATE TABLE IF NOT EXISTS records(g6 TEXT PRIMARY KEY,verdict TEXT,certtype TEXT,raw TEXT)')
counts=collections.Counter();degrees=collections.Counter()
with gzip.open(GP/'cloud/lean3/records.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line);g=r['g6'];c=r['cert'];v=r['verdict'];counts[(v,c['type'])]+=1
  if c['type']=='exact':degrees[len(c['field']['minpoly'])-1]+=1
  db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(g,v,c['type'],line))
  del r,c
  memory()
db.commit();db.close()
(OUT/'prepare-summary.json').write_text(json.dumps({'records':{str(k):v for k,v in counts.items()},'embedding_degrees':degrees,'seconds':time.monotonic()-t,**usage()},indent=2))
print((OUT/'prepare-summary.json').read_text())
