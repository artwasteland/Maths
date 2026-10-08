#!/usr/bin/env python3
"""How much of the (23,65) tree would the rhombus-linear filter remove, and how much generation cost with it?

Sampled descent through the real (23,65) Mode-74 tree (speed.py's method, the (23,65) reach table of the pilot):
level-12 stage files are the production ones (hash-checked against the pilot's hashes.json; 12-23 recomputed, its
keep file hash-checked too), and from a uniform sample of level 12 each level keeps a uniform sample of its
TU-pruned kept graphs as the next level's parents (one canonical parent per graph, so all children of uniformly
sampled parents are a uniform, if clustered, sample of the next level). At each level L a measurement sample S_L
(<= --measure graphs) is classified by the rhombus probe and by 398-containment, and udenum is timed on the whole
sample and on its unflagged part, for every target cell of level L+1: by heredity (a flagged graph's canonical
descendants are all flagged, since the parent is an induced subgraph), cpu(unflagged)/cpu(all) is the fraction of
level-(L+1) generation the filter would leave, and children(unflagged)/children(all) that of the prune and verify steps.
"""
import json, os, random, sys, time, collections
from pathlib import Path
sys.path.insert(0, "<repo>/research/unit-distance-22/enum/test-398")
sys.path.insert(0, "<repo>/research/unit-distance-23/tools")
from t398lib import F398, F74, NEW_UDENUM, g6_lines, g6_order_size, run_udenum, sha256, write_lines
from speed import min_degree, udfilter_verdicts, sources
import networkx as nx
from rhombus_probe import probe

W = Path(sys.argv[1]); W.mkdir(parents=True, exist_ok=True)
SEED = int(os.environ.get("SEED", "20260926"))
FSET = os.environ.get("FSET", "398")
UDX = dict(extra=["--forbidden-set", "398"], forbidden=F398) if FSET == "398" else {}
N12 = int(os.environ.get("N12", "3000"))         # level-12 parents sampled
SIZES = {int(k): int(v) for k, v in (x.split(":") for x in os.environ.get("SIZES", "13:3000,14:4000,15:6000,16:30000,17:30000,18:30000,19:30000").split(","))}
MEASURE = int(os.environ.get("MEASURE", "1500"))
TOP = int(os.environ.get("TOP", "19"))
PILOT = Path("<scratch>/scratchpad/pilot/research/unit-distance-23/results/u23/23-65-f74-L12/s0of1920")
PROD12 = Path("<repo>/research/unit-distance-22/enum/out-22/dag-22-61-f12")
table = json.loads((PILOT / "reach.json").read_text())["table"]
hashes = json.loads((PILOT / "hashes.json").read_text())["files"]
rng = random.Random(SEED)
log = open(W / "log.txt", "a")
def say(*a):
    print(time.strftime("%H:%M:%S"), *a, file=log, flush=True)

def grow(parents, n, tag):
    """All TU-kept, reach-filtered children at level n+1 of the given level-n parents, per target cell."""
    by_m = collections.defaultdict(list)
    for g in parents:
        by_m[g6_order_size(g)[1]].append(g)
    kids, cpu, written = [], 0.0, 0
    for M in sorted(int(x) for x in table[str(n + 1)]):
        src = [g for m in sources(table, n, M) for g in by_m.get(m, [])]
        if not src:
            continue
        pf = W / f"{tag}-{n + 1}-{M}.parents.g6"; write_lines(pf, src)
        st = run_udenum(NEW_UDENUM, pf, n + 1, M, W / f"{tag}-{n + 1}-{M}.g6", **UDX)
        cpu += st["cpu_seconds"]; written += st["children_written"]
        k = table[str(n + 1)][str(M)]
        kids += [g for g in g6_lines(W / f"{tag}-{n + 1}-{M}.g6") if min_degree(g) >= k]
        os.unlink(W / f"{tag}-{n + 1}-{M}.g6")
    after_reach = len(kids)
    if kids:
        v = udfilter_verdicts(kids, W, f"{tag}-{n + 1}-tu", FSET)
        if "forbidden" in v:
            raise SystemExit(f"generator bug: a child is not {FSET}-free")
        kids = [g for g, x in zip(kids, v) if x != "tu"]
        os.unlink(W / f"{tag}-{n + 1}-tu.in.g6")
    return kids, {"cpu": cpu, "written": written, "after_reach": after_reach, "kept": len(kids)}

# level 12: production stage files, checked by hash against the pilot's (23,65) prefix
stage12 = []
for m in sorted(table["12"], key=int):
    name = f"12-{m}.keep.g6"
    f = PROD12 / name
    if m != "23" and f.exists() and sha256(f) == hashes[name]["sha256"]:
        stage12 += g6_lines(f); continue
    # 12-23 differs from (22,61)'s (k = 0 here): recompute it from the level-11 files (identical in both runs)
    srcs = []
    for m11 in sources(table, 11, int(m)):
        f11 = PROD12 / f"11-{m11}.reach.g6"
        assert sha256(f11) == hashes[f"11-{m11}.reach.g6"]["sha256"], f11
        srcs += g6_lines(f11)
    pf = W / f"p12-{m}.parents.g6"; write_lines(pf, srcs)
    run_udenum(NEW_UDENUM, pf, 12, int(m), W / f"p12-{m}.g6")
    k = table["12"][m]
    c = [g for g in g6_lines(W / f"p12-{m}.g6") if min_degree(g) >= k]
    v = udfilter_verdicts(c, W, f"p12-{m}-tu", "74")
    keep = [g for g, x in zip(c, v) if x != "tu"]
    write_lines(W / name, keep)
    ok = sha256(W / name) == hashes[name]["sha256"]
    say(f"recomputed {name}: {len(keep)} graphs, sha256 {'MATCHES' if ok else 'DIFFERS FROM'} the pilot's"
        f" ({hashes[name]['records']} records)", "" if ok else f"sorted-set equal: {sorted(keep) == sorted(g6_lines(W / name))}")
    stage12 += keep
say(f"level 12 stage: {len(stage12)} graphs")
# the pilot slices at level 12, so level 13 in full would be ~23M graphs: descend from a uniform level-12 sample
parents = rng.sample(stage12, min(N12, len(stage12)))
del stage12
if FSET == "398":
    vv = udfilter_verdicts(parents, W, "s12-398", "398")
    say(f"level-12 sample: {len(parents)}, 398-free {sum(x != 'forbidden' for x in vv)}, tu {sum(x == 'tu' for x in vv)}")
    parents = [g for g, x in zip(parents, vv) if x == "pass"]
samples = {}
yields = {}
for n in range(12, TOP):
    kids, st = grow(parents, n, "d")
    st["sampled_parents"] = len(parents)
    yields[n + 1] = st
    say(f"level {n + 1}: {st}")
    samples[n + 1] = kids
    parents = kids if len(kids) <= SIZES.get(n + 1, 30000) else rng.sample(kids, SIZES.get(n + 1, 30000))
    if not kids:
        break
json.dump(yields, open(W / "yields.json", "w"), indent=1)

# measurement per level
results = {}
for L in sorted(samples):
    if L >= TOP or not samples[L]:
        continue
    S = samples[L] if len(samples[L]) <= MEASURE else rng.sample(samples[L], MEASURE)
    write_lines(W / f"measure-{L}.g6", S)
    t0 = time.time()
    verdict = [probe(nx.from_graph6_bytes(g))[0] for g in S]
    probe_s = time.time() - t0
    free = [x != "forbidden" for x in udfilter_verdicts(S, W, f"m{L}-398", "398")]
    rec = {"n": len(S), "probe_seconds": round(probe_s, 1), "verdicts": collections.Counter(verdict),
           "free398": sum(free),
           "flagged_among_free398": sum(1 for v, f in zip(verdict, free) if f and v != "none")}
    for name, keep in (("all", [True] * len(S)), ("unflagged", [v == "none" for v in verdict]),
                       ("free398", free), ("free398_unflagged", [f and v == "none" for v, f in zip(verdict, free)])):
        sub = [g for g, k in zip(S, keep) if k]
        if not sub:
            rec[name] = {"parents": 0, "cpu": 0.0, "written": 0, "kept": 0}; continue
        _, st2 = grow(sub, L, f"m{L}-{name}")
        rec[name] = {"parents": len(sub), **{k: st2[k] for k in ("cpu", "written", "kept")}}
    results[L] = rec
    say(f"measure level {L}: {json.dumps(rec, default=str)}")
    json.dump(results, open(W / "measure.json", "w"), indent=1, default=str)
say("done")
