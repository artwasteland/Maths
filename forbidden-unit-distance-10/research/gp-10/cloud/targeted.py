"""Targeted refutation helper for residue analysis.

usage: python targeted.py G6 --method null|real|dag --frame a b --sat "u,v u,v ..." [--seconds 600] [--out DIR]

Runs the refuter's algebra_search with the default saturation (4-cycle diagonals) PLUS the given pairs, on the
given frame edge, writes the record to DIR/<g6hash>.jsonl, then runs the official blind checker on it (profile
sample, F9 in force) and prints the checker's final line. Nothing is trusted until the checker says ACCEPT.
"""
import os, sys, json, argparse, hashlib, subprocess, tempfile, time
os.environ.setdefault("SYMPY_GROUND_TYPES", "python")
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "refute")
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check", "gp10check.py")
PY = sys.executable
sys.path.insert(0, REF)
from algebra import algebra_search  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("g6")
ap.add_argument("--method", default="null", choices=["null", "real", "dag"])
ap.add_argument("--frame", nargs=2, type=int)
ap.add_argument("--sat", default="")
ap.add_argument("--seconds", type=float, default=600)
ap.add_argument("--out", default=os.environ.get("GP10_TARGETED_OUT", "targeted-out"))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
extra = [tuple(sorted(map(int, p.split(",")))) for p in a.sat.split()] if a.sat.strip() else []
t0 = time.monotonic()
cert, detail = algebra_search(a.g6, "real" if a.method == "dag" else a.method, a.seconds,
                              frame=list(a.frame) if a.frame else None, extra_sat=extra, dag=(a.method == "dag"))
el = time.monotonic() - t0
h = hashlib.sha256(a.g6.encode()).hexdigest()[:16]
if not cert:
    print(json.dumps({"g6": a.g6, "result": "no certificate", "seconds": round(el, 1), "detail": str(detail)[:300]}))
    sys.exit(1)
rec = {"g6": a.g6, "verdict": "refuted", "cert": cert}
path = os.path.join(a.out, h + ".jsonl")
open(path, "w").write(json.dumps(rec) + "\n")
# official checker on a one-record sample run
d = tempfile.mkdtemp(prefix="tchk-")
open(d + "/input.g6", "w").write(a.g6 + "\n"); open(d + "/UNKNOWN.g6", "w").write("")
open(d + "/records.jsonl", "w").write(json.dumps(rec) + "\n")
json.dump({"profile": "sample", "input": "input.g6", "input_sha256": hashlib.sha256((a.g6 + "\n").encode()).hexdigest(),
           "records": ["records.jsonl"], "forbidden_limit": 9}, open(d + "/run.json", "w"))
p = subprocess.run([PY, CHECK, d, "--output", d + "/out"], capture_output=True, text=True,
                   env=dict(os.environ, SYMPY_GROUND_TYPES="python"))
line = [x for x in p.stdout.splitlines() if x.endswith("run verified") or " run " in x][-1:] or [p.stdout[-200:]]
print(json.dumps({"g6": a.g6, "result": "certificate", "type": cert.get("type"), "seconds": round(el, 1),
                  "bytes": len(json.dumps(rec)), "record": path, "checker": line[0]}))
