"""G4 count: L10 members with a checker-accepted refutation of a different type from the final record's.

usage: python g4_count.py RECORDS.jsonl L10.g6 OUTDIR G4RECORDS...   (G4RECORDS: the cloud workers' records, .gz or not)

Keeps, for each L10 member, the first refutation in G4RECORDS whose certificate type differs from the final record's
(and is not a pointer), writes them as a sample-profile run in OUTDIR and runs the official checker over it.
"""
import json, gzip, glob, os, sys, hashlib, subprocess
REC, L10_PATH, out, sources = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
HERE = os.path.dirname(os.path.abspath(__file__))
L10 = set(open(L10_PATH).read().split())
primary = {}
with open(REC, "rb") as f:
    for raw in f:
        r = json.loads(raw)
        if r["g6"] in L10:
            primary[r["g6"]] = (r.get("cert") or {}).get("type")
alt = {}
for p in sources:
    op = gzip.open if p.endswith(".gz") else open
    for raw in op(p, "rt"):
        try: r = json.loads(raw)
        except ValueError: continue
        if r.get("verdict") != "refuted" or r.get("g6") not in L10: continue
        t = (r.get("cert") or {}).get("type")
        if t in (None, "sub", primary[r["g6"]]): continue
        if len(raw.encode()) > 8 * 1024 * 1024: continue
        alt.setdefault(r["g6"], raw if raw.endswith("\n") else raw + "\n")
os.makedirs(out, exist_ok=True)
gs = sorted(alt)
inp = "".join(g + "\n" for g in gs)
open(out + "/input.g6", "w").write(inp); open(out + "/UNKNOWN.g6", "w").write("")
open(out + "/records.jsonl", "w").write("".join(alt[g] for g in gs))
json.dump({"profile": "sample", "input": "input.g6", "input_sha256": hashlib.sha256(inp.encode()).hexdigest(),
           "records": ["records.jsonl"], "forbidden_limit": 9}, open(out + "/run.json", "w"))
p = subprocess.run([sys.executable, os.path.join(HERE, "..", "check", "gp10check.py"),
                    out, "--output", out + "/out"], capture_output=True, text=True, env=dict(os.environ, SYMPY_GROUND_TYPES="python"))
acc = [l.split()[2] for l in p.stdout.splitlines() if l.startswith("ACCEPT record ")]
rej = [l for l in p.stdout.splitlines() if l.startswith("REJECT")]
from collections import Counter
print(json.dumps({"L10": len(L10), "candidates_with_alternate": len(gs), "checker_accepted": len(acc),
                  "final_line": [l for l in p.stdout.splitlines() if " run " in l][-1:], "rejects": rej[:5],
                  "alternate_types_accepted": dict(Counter(json.loads(alt[g])["cert"]["type"] for g in acc)),
                  "primary_types_covered": dict(Counter(primary[g] for g in acc))}))
