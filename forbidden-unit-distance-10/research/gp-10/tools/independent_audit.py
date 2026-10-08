"""Independent audit of the GP-10 result: re-derive what can be re-derived WITHOUT the official checker or the driver.

usage: python independent_audit.py B10.g6 RECORDS.jsonl L10.g6 [--stages 1234v] [--out FILE] [--dps 120] [--spot 100]

Uses only networkx, pynauty (nauty canonical labelling) and mpmath, written against CONTRACT.md's definitions, never
importing gp10check.py, udcheck.py or anything under drive/. It trusts the records' VERDICTS only where it says so,
and tests them against each other and against the definitions:

  1. Input: the 33,162 B10 graphs are pairwise non-isomorphic (nauty certificates), and the records cover exactly B10.
  2. Minimality, recounted from scratch: for every refuted graph, every one-edge deletion is built, identified by its
     nauty certificate among the B10 graphs (never through the driver's poset), and looked up. A refuted graph is
     minimal iff every biconnected deletion is embedded (a non-biconnected deletion has blocks on at most 9
     vertices, F9-free, hence unit-distance by Globus-Parshall, re-derived by the controls). The recount must equal
     L10.g6 exactly; a biconnected deletion missing from B10 would mean B10 is incomplete (alarm).
  3. Every exact embedding, evaluated independently at high precision: the root of minpoly in its interval by
     bisection at 120 digits (--dps), the coordinates evaluated there, every edge length compared with 1 and every
     pair's distance with 0; re-run at a higher --dps, a true zero's residue falls with the precision. Every pointer: the map is injective and edge-preserving in the contract's direction, the
     target carries the required verdict, and every chain ends at a non-pointer certificate.
  4. Cross-consistency: the up-set of L10 in B10 (by one-edge additions, nauty lookups) equals the refuted set, so
     no embedded graph contains an L10 member and every refuted graph contains one; plus a VF2 monomorphism spot
     check of the densest embedded graphs (--spot, default 100) against all of L10. A hit would mean two accepted certificates
     contradict each other.
"""
import sys, json, itertools, time
from fractions import Fraction
import networkx as nx
import pynauty
import mpmath

B10_PATH, REC_PATH, L10_PATH = sys.argv[1:4]
STAGES = sys.argv[sys.argv.index("--stages") + 1] if "--stages" in sys.argv else "1234v"   # v: the VF2 spot check
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "independent-audit.json"
DPS = int(sys.argv[sys.argv.index("--dps") + 1]) if "--dps" in sys.argv else 120
SPOT = int(sys.argv[sys.argv.index("--spot") + 1]) if "--spot" in sys.argv else 100   # VF2 hosts, densest first
report = {"alarms": []}
T0 = time.time()


def alarm(msg):
    report["alarms"].append(msg)
    print("ALARM", msg, flush=True)


def graph(g6):
    return nx.from_graph6_bytes(g6.encode())


def ncert(G):
    n = G.number_of_nodes()
    return pynauty.certificate(pynauty.Graph(n, adjacency_dict={v: list(G[v]) for v in G}))


# 1. input
B10 = [l.strip() for l in open(B10_PATH) if l.strip()]
G = {g: graph(g) for g in B10}
cmap = {}
for g in B10:
    c = ncert(G[g])
    if c in cmap:
        alarm(f"B10 duplicate isomorphism class: {g} ~ {cmap[c]}")
    cmap[c] = g
verdict, cert = {}, {}
with open(REC_PATH) as f:
    for line in f:
        r = json.loads(line)
        if r["g6"] in verdict:
            alarm(f"duplicate record {r['g6']}")
        verdict[r["g6"]] = r["verdict"]
        c = r.get("cert") or {}
        t = c.get("type")
        if t == "exact":
            cert[r["g6"]] = c                                   # small: coordinates in the number field
        elif t in ("super", "sub"):
            cert[r["g6"]] = {k: c[k] for k in ("type", "g6", "map", "index") if k in c}
        else:
            cert[r["g6"]] = {"type": t}                         # refutation bodies are the checker's business
        del r, c
if set(verdict) != set(B10):
    alarm(f"records do not cover B10 exactly: {len(set(B10) - set(verdict))} missing, {len(set(verdict) - set(B10))} extra")
from collections import Counter
report["input"] = {"B10": len(B10), "distinct_iso_classes": len(cmap), "verdicts": dict(Counter(verdict.values()))}
print(json.dumps(report["input"]), flush=True)

# 2. minimality recount
L10 = [l.strip() for l in open(L10_PATH) if l.strip()]
mine, nonmin, missing = [], 0, 0
for g in (B10 if '2' in STAGES else []):
    if verdict[g] != "refuted":
        continue
    H = G[g]
    minimal = True
    for e in list(H.edges()):
        D = H.copy(); D.remove_edge(*e)
        if not nx.is_biconnected(D):
            continue                      # blocks on <= 9 vertices, F9-free: unit-distance by GP
        h = cmap.get(ncert(D))
        if h is None:
            missing += 1
            alarm(f"biconnected deletion of {g} (edge {e}) is not in B10")
            minimal = False
            continue
        if verdict[h] != "embedded":
            minimal = False
    if minimal:
        mine.append(g)
    else:
        nonmin += 1
if '2' in STAGES:
  report["minimality"] = {"recounted_minimal": len(mine), "refuted_not_minimal": nonmin,
                        "equals_L10": sorted(mine) == sorted(L10), "deletions_missing_from_B10": missing,
                        "L10_pairwise_nonisomorphic": len({ncert(G[g]) for g in L10}) == len(L10)}
  if sorted(mine) != sorted(L10):
    alarm(f"minimality recount differs from L10: only mine {sorted(set(mine) - set(L10))[:5]}, only L10 {sorted(set(L10) - set(mine))[:5]}")
  print(json.dumps(report["minimality"]), flush=True)

# 3. embeddings at high precision, and pointer structure
mpmath.mp.dps = DPS                                  # rounding error must fall as DPS rises


def rat(s):
    q = Fraction(s)
    return mpmath.mpf(q.numerator) / q.denominator


def peval(c, t):
    acc = mpmath.mpf(0)
    for a in reversed(c):
        acc = acc * t + a
    return acc


worst_edge, worst_gap, n_exact = mpmath.mpf(0), mpmath.mpf(10), 0
for g in (B10 if '3' in STAGES else []):
    c = cert[g]
    if verdict[g] != "embedded" or c.get("type") != "exact":
        continue
    n_exact += 1
    mp = [mpmath.mpf(int(x)) for x in c["field"]["minpoly"]]
    lo, hi = rat(c["field"]["interval"][0]), rat(c["field"]["interval"][1])
    flo, fhi = peval(mp, lo), peval(mp, hi)
    if flo * fhi >= 0:
        alarm(f"{g}: no sign change on its interval")
        continue
    for _ in range(int(DPS * 3.33) + 30):  # bisection to below 10^-DPS
        mid = (lo + hi) / 2
        fm = peval(mp, mid)
        if fm == 0:
            lo = hi = mid; break
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    t = (lo + hi) / 2
    P = [(peval([rat(a) for a in X], t), peval([rat(a) for a in Y], t)) for X, Y in c["coords"]]
    Hg = G[g]
    if len(P) != Hg.number_of_nodes():
        alarm(f"{g}: {len(P)} coordinates for {Hg.number_of_nodes()} vertices"); continue
    for u, v in Hg.edges():
        d = abs((P[u][0] - P[v][0]) ** 2 + (P[u][1] - P[v][1]) ** 2 - 1)
        worst_edge = max(worst_edge, d)
    gap = min(mpmath.sqrt((P[u][0] - P[v][0]) ** 2 + (P[u][1] - P[v][1]) ** 2) for u, v in itertools.combinations(range(len(P)), 2))
    worst_gap = min(worst_gap, gap)
    if gap < mpmath.mpf("1e-30"):
        alarm(f"{g}: two points coincide (distance {mpmath.nstr(gap, 5)})")
if worst_edge > mpmath.mpf(10) ** (30 - DPS):
    alarm(f"an embedding edge is off unit length by {mpmath.nstr(worst_edge, 5)}")


def maps_into(small, big, m):
    if len(set(m)) != len(m) or any(not (0 <= x < big.number_of_nodes()) for x in m):
        return False
    return all(big.has_edge(m[u], m[v]) for u, v in small.edges())


ptr_bad, resolved = 0, {}


def resolve(g, want, seen=()):
    """Follow pointers from g; True iff the chain ends at a non-pointer certificate with the wanted verdict."""
    if g in seen:
        return False
    c = cert.get(g, {})
    if verdict.get(g) != want:
        return False
    t = c.get("type")
    if t == "super" and want == "embedded":
        h = c["g6"]
        return h in G and maps_into(G[g], G[h], c["map"]) and resolve(h, want, seen + (g,))
    if t == "sub" and want == "refuted":
        h = c["g6"]
        if "index" in c:
            return False                   # an F9 member inside an F9-free graph: impossible
        return h in G and maps_into(G[h], G[g], c["map"]) and resolve(h, want, seen + (g,))
    return t not in ("super", "sub")


types = Counter()
for g in (B10 if '3' in STAGES else []):
    types[(verdict[g], cert[g].get("type"))] += 1
    if cert[g].get("type") in ("super", "sub") and not resolve(g, verdict[g]):
        ptr_bad += 1
        if ptr_bad <= 5:
            alarm(f"pointer chain from {g} does not resolve")
if '3' in STAGES:
    report["embeddings_and_pointers"] = {"digits": DPS, "exact_embeddings": n_exact, "worst_edge_error": mpmath.nstr(worst_edge, 3),
                                         "smallest_point_gap": mpmath.nstr(worst_gap, 6), "bad_pointer_chains": ptr_bad,
                                         "record_types": {f"{a}/{b}": k for (a, b), k in sorted(types.items(), key=str)}}
    print(json.dumps(report["embeddings_and_pointers"]), flush=True)

# 4. cross-consistency. The up-set of L10 inside B10 (everything reachable from an L10 member by adding edges) must be
#    exactly the refuted set: an embedded graph in it would contain a forbidden graph, and a refuted graph outside it
#    would contain no minimal forbidden graph. Every graph between an L10 member and a B10 supergraph of it is a
#    subgraph of an F9-free graph (so F9-free) with a biconnected spanning subgraph (so biconnected), so it is in B10
#    and one-edge additions reach every B10 supergraph. The lookups are nauty certificates against B10; if they
#    silently failed, the up-set would stop short of the refuted set and the equality would go red.
up, frontier, grown = set(L10) if "4" in STAGES else set(), list(L10) if "4" in STAGES else [], 0
while frontier:
    nxt = []
    for g in frontier:
        H = G[g]
        for u, v in itertools.combinations(range(H.number_of_nodes()), 2):
            if H.has_edge(u, v):
                continue
            D = H.copy(); D.add_edge(u, v)
            h = cmap.get(ncert(D))
            if h is not None and h not in up:
                up.add(h); nxt.append(h); grown += 1
    frontier = nxt
refuted = {g for g in B10 if verdict.get(g) == "refuted"}
contra = sorted(g for g in up if verdict.get(g) != "refuted")
for g in contra[:5]:
    alarm(f"{g} is {verdict.get(g)} but contains an L10 member")
if "4" in STAGES and up != refuted:
    alarm(f"up-set of L10 ({len(up)}) differs from the refuted set ({len(refuted)}): {sorted(refuted - up)[:5]}")
# A method-diverse spot check (VF2 monomorphism, no canonical forms): the densest embedded graphs against every L10
# member. Capped (about 15 s per dense host), and the cap is reported.
LAG = {g: G[g] for g in L10}
LA = [(g, sorted((d for _, d in G[g].degree()), reverse=True), G[g].number_of_edges()) for g in L10]
emb_all = sorted((g for g in B10 if verdict.get(g) == "embedded"), key=lambda g: -G[g].number_of_edges())
spot = emb_all[:SPOT] if "v" in STAGES else []
pairs, vf2_hits = 0, 0
for b in spot:
    Bg = G[b]
    db = sorted((d for _, d in Bg.degree()), reverse=True); mb = Bg.number_of_edges()
    for a, da, ma in LA:
        if ma > mb or any(x < y for x, y in zip(db, da)):
            continue
        pairs += 1
        if nx.algorithms.isomorphism.GraphMatcher(Bg, LAG[a]).subgraph_is_monomorphic():
            vf2_hits += 1
            alarm(f"VF2: embedded {b} contains L10 member {a}")
if "4" in STAGES:
    report["cross_consistency"] = {"upset_of_L10_in_B10": len(up), "refuted": len(refuted), "upset_equals_refuted": up == refuted,
                                   "non_refuted_in_upset": len(contra)}
    print(json.dumps(report["cross_consistency"]), flush=True)
if "v" in STAGES:
    report["vf2_spot"] = {"densest_embedded_scanned": len(spot), "of_embedded": len(emb_all),
                          "edge_range": [G[spot[-1]].number_of_edges(), G[spot[0]].number_of_edges()] if spot else None,
                          "pairs_tested": pairs, "hits": vf2_hits}
    print(json.dumps(report["vf2_spot"]), flush=True)
report["seconds"] = round(time.time() - T0)
report["verdict"] = "INDEPENDENT AUDIT PASS" if not report["alarms"] else "INDEPENDENT AUDIT FAIL"
print(json.dumps({"verdict": report["verdict"], "alarms": len(report["alarms"]), "seconds": report["seconds"]}), flush=True)
json.dump(report, open(OUT, "w"), indent=1)
