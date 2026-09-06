import re, glob, json, collections, sys
rows = []
for f in ['results/chainD0.log','results/chainD0b.log','results/chainD1b.log']:
    try:
        for line in open(f):
            m = re.match(r'drop (\d+) (\d+) :: (?:(\d+)s :: )?(.*)', line.strip())
            if m: rows.append((int(m[1]), int(m[2]), m[3], m[4]))
    except FileNotFoundError: pass
seen = {}
for i,j,t,out in rows: seen[(i,j)] = (t,out)
forced = {k:v for k,v in seen.items() if 'IS forced' in v[1]}
timeouts = {k:v for k,v in seen.items() if 'TIMEOUT' in v[1]}
nosingle = {k:v for k,v in seen.items() if 'no single' in v[1]}
other = {k:v for k,v in seen.items() if k not in forced and k not in timeouts and k not in nosingle}
trip = collections.Counter(re.search(r'triple \((\d+), (\d+), (\d+)\)', v[1]).group(0) for v in forced.values())
print(f"double drops finished: {len(seen)} of 253 pairs")
print(f"  forced non-block triple found (non-realizable): {len(forced)}")
print(f"  timed out within the per-run cap: {len(timeouts)} -> {sorted(timeouts)}")
print(f"  no single triple forced (needs product/witness): {len(nosingle)} -> {sorted(nosingle)}")
print(f"  other/errors: {len(other)} -> {sorted(other)}")
print("  forced triples seen:", dict(trip))
slow = {}
for f in glob.glob('results/mut2slow_*.json'):
    r = json.load(open(f)); slow[r['label']] = r
for k, r in sorted(slow.items()):
    print(f"  {k}: dropped {r.get('dropped_blocks')} frame {r['frame']} GB {r['gb_size']} polys deg {r['gb_max_degree']} dim {r['gb_dimension']} {r['gb_seconds']}s; forced {r.get('forced_single_triples')} tested {r.get('single_triples_tested')} verdict {r.get('verdict')}")
