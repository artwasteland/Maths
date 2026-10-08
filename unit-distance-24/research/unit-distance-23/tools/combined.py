"""Generation retention of the rhombus + triangle rule on a descent's measurement samples."""
import json, os, sys, collections
from pathlib import Path
sys.path.insert(0, "<repo>/research/unit-distance-22/enum/test-398")
sys.path.insert(0, "<repo>/research/unit-distance-23/tools")
from t398lib import F398, NEW_UDENUM, g6_lines, g6_order_size, run_udenum, write_lines
from speed import min_degree, udfilter_verdicts, sources
import networkx as nx
from rhombus_probe import probe
from triangle_probe import triangle_verdict
W = Path(sys.argv[1]); FSET = sys.argv[2] if len(sys.argv) > 2 else "74"
UDX = dict(extra=["--forbidden-set", "398"], forbidden=F398) if FSET == "398" else {}
PILOT = Path("<scratch>/scratchpad/pilot/research/unit-distance-23/results/u23/23-65-f74-L12/s0of1920")
table = json.loads((PILOT / "reach.json").read_text())["table"]
T = W / "comb"; T.mkdir(exist_ok=True)
def grow(parents, n, tag):
    by_m = collections.defaultdict(list)
    for g in parents: by_m[g6_order_size(g)[1]].append(g)
    kids, cpu, written = [], 0.0, 0
    for M in sorted(int(x) for x in table[str(n + 1)]):
        src = [g for m in sources(table, n, M) for g in by_m.get(m, [])]
        if not src: continue
        pf = T / f"{tag}-{n + 1}-{M}.parents.g6"; write_lines(pf, src)
        st = run_udenum(NEW_UDENUM, pf, n + 1, M, T / f"{tag}-{n + 1}-{M}.g6", **UDX)
        cpu += st["cpu_seconds"]; written += st["children_written"]
    return {"cpu": cpu, "written": written, "parents": len(parents)}
out = {}
meas = json.loads((W / "measure.json").read_text())
for L in sorted(int(x) for x in meas):
    S = g6_lines(W / f"measure-{L}.g6")
    if FSET == "74" and "free398" in meas[str(L)] and False: pass
    verdict = []
    for g in S:
        G = nx.from_graph6_bytes(g)
        r = probe(G)[0]
        verdict.append(r if r != "none" else triangle_verdict(G))
    openset = [g for g, v in zip(S, verdict) if v in ("open", "no-triangles", "too-many-cases")]
    def best(sub, tag):   # min CPU over 2 alternating repetitions: the box is shared, so time both sets side by side
        if not sub: return {"cpu": 0.0, "written": 0, "parents": 0}
        runs = [grow(sub, L, tag) for _ in range(2)]
        return min(runs, key=lambda r: r["cpu"])
    a1 = best(S, f"a{L}"); o1 = best(openset, f"o{L}")
    rec = {"n": len(S), "verdicts": collections.Counter(verdict), "open": o1, "all": a1}
    rec["gen_retention"] = rec["open"]["cpu"] / rec["all"]["cpu"] if rec["all"]["cpu"] else 1
    rec["children_retention"] = rec["open"]["written"] / rec["all"]["written"] if rec["all"]["written"] else 1
    out[L] = rec
    print(L, json.dumps({k: v for k, v in rec.items() if k != "verdicts"}), dict(rec["verdicts"]), flush=True)
json.dump(out, open(W / "combined.json", "w"), indent=1, default=str)
