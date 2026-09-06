"""CONTROL (coordinate-derived, the direction the real theorem needs): push the real Pegg (15,31) configuration (15-torsion of the acnodal
cubic y^2 = x^2(x-1), real branch = circle group) through the exact machinery exist.py
uses at (15,32): Lemma 3 row fix, Lemma 4 reorientation, Lemma 7 cube choice, Lemma 8
G2 lex descent, and then evaluate EVERY clause of the monolithic and of the cube CNF.

Why this control exists (referee panel of 2026-09-05, encoding lens): every other control in
chiro/ is a solver-found model checked by a verifier that shares the encoder's sign convention,
so an encoder that rejects every REAL chirotope while admitting some spurious sign vector would
leave them all green and make the four (15,32) UNSATs vacuous. Only a chirotope computed from
coordinates tests that direction. Exit status: 0 iff the real chirotope falsifies no clause of
either CNF AND the negative control (one sign flipped) falsifies some. Written by the referee
agent, adopted unchanged apart from the path and the exit status."""
import itertools, sys, time
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mpmath as mp
mp.mp.dps = 60
from chirosat import PTS, ordered_base
from exist import (derive_reduction, sign_anchors, build_existence_encoding, row_stabiliser_generators,
                   apply_to_triple, apply_to_config, enumerate_cubes, group_closure, pair_exchange, cube_units)

def log(*a):
    print(*a, flush=True)

n = 15
def point(k):
    if k % n == 0:
        return (mp.mpf(0), mp.mpf(1), mp.mpf(0))
    th = 2*mp.pi*k/n
    t = mp.cot(th/2)
    return (t*t+1, t**3+t, mp.mpf(1))
P = [point(k) for k in range(n)]
def det3(p,q,r):
    (a,b,c),(d,e,f),(g,h,i) = p,q,r
    return a*(e*i-f*h) - b*(d*i-f*g) + c*(d*h-e*g)
zero_sum = {t for t in itertools.combinations(range(n),3) if sum(t) % n == 0}
mx_zero = 0; mn_nonzero = mp.inf
for t in itertools.combinations(range(n),3):
    d = abs(det3(*(P[i] for i in t)))
    if t in zero_sum: mx_zero = max(mx_zero, d)
    else: mn_nonzero = min(mn_nonzero, d)
log("zero-sum triples:", len(zero_sum), " max|det| on them:", mp.nstr(mx_zero,5), " min|det| off them:", mp.nstr(mn_nonzero,5))
assert mx_zero < mp.mpf(10)**-40 < mn_nonzero
def sgn(x):
    return 0 if abs(x) < mp.mpf(10)**-40 else (1 if x > 0 else -1)

pts = PTS(n, tuple(sorted(zero_sum)))
triples = tuple(itertools.combinations(range(n),3))

def chi_of(points):
    return {t: sgn(det3(*(points[i] for i in t))) for t in triples}

def relabel(points, blocks, perm):
    newpoints = [None]*n
    for old, new in enumerate(perm): newpoints[new] = points[old]
    return newpoints, {apply_to_triple(perm, b) for b in blocks}

def reorient_to_anchors(chi, anchors):
    for a in anchors: assert chi[a] != 0
    # brute force is fine: 2^15 reorientations
    masks = [sum(1<<p for p in a) for a in anchors]
    for s in range(1<<n):
        if all(((-1)**bin(s & m).count('1')) * chi[a] == 1 for m, a in zip(masks, anchors)):
            break
    else:
        raise AssertionError("no reorientation fixes the anchors")
    chi2 = {t: ((-1)**bin(s & sum(1<<p for p in t)).count('1')) * v for t, v in chi.items()}
    return chi2

def full_assignment(enc, chi, blocks):
    base = enc.chiro; val = {}
    for t in base.triples:
        val[base.var(t,1)] = chi[t] == 1
        val[base.var(t,-1)] = chi[t] == -1
        val[base.nonzero_variables[t]] = chi[t] != 0
    aux = 3*len(base.triples)
    def chiv(o):
        t,s = ordered_base(o); return s*chi[t]
    for five in itertools.combinations(range(n),5):
        for pivot in five:
            b,c,d,e = (x for x in five if x != pivot)
            prods = (chiv((pivot,b,c))*chiv((pivot,d,e)), -chiv((pivot,b,d))*chiv((pivot,c,e)), chiv((pivot,b,e))*chiv((pivot,c,d)))
            for k in range(3):
                aux += 1; val[aux] = prods[k] == 1
                aux += 1; val[aux] = prods[k] == -1
    assert aux == base.nvars
    for t, var in enc.block_variables.items():
        val[var] = t in blocks
    return val

def propagate_and_check(enc, val):
    val = dict(val)
    clauses = enc.clauses
    occ = {}
    for ci, cl in enumerate(clauses):
        for l in cl:
            occ.setdefault(abs(l), []).append(ci)
    def status(ci):
        cl = clauses[ci]
        if any(abs(l) in val and val[abs(l)] == (l > 0) for l in cl): return "sat", None
        un = [l for l in cl if abs(l) not in val]
        return ("false", None) if not un else ("unit", un[0]) if len(un) == 1 else ("open", None)
    work = list(range(len(clauses)))
    falsified = []
    while work:
        ci = work.pop()
        st, l = status(ci)
        if st == "false": falsified.append(clauses[ci]); continue
        if st == "unit":
            val[abs(l)] = l > 0
            work.extend(occ.get(abs(l), []))
    free = [v for v in range(1, enc.nvars+1) if v not in val]
    open_cl = [cl for cl in clauses if not any(abs(l) in val and val[abs(l)] == (l>0) for l in cl)]
    return {"falsified": len(falsified), "example": falsified[:3], "free_vars": len(free), "unsatisfied_clauses": len(open_cl)}

red = derive_reduction(15, 31)
covered = {p for b in pts.blocks for p in itertools.combinations(b,2)}
deg = [sum(tuple(sorted((p,q))) not in covered for q in range(n) if q != p) for p in range(n)]
log("leave degrees (Z/15 labelling):", deg)
root = deg.index(min(deg)); assert deg[root] == red.min_leave_degree
incident = sorted(b for b in pts.blocks if root in b)
old_pairs = [tuple(p for p in b if p != root) for b in incident]
perm = [None]*n; perm[root] = 0
for op, nb in zip(old_pairs, red.row_blocks):
    perm[op[0]], perm[op[1]] = nb[1], nb[2]
assert all(x is not None for x in perm)
pts1, blocks1 = relabel(P, set(pts.blocks), tuple(perm))
assert {b for b in blocks1 if 0 in b} == set(red.row_blocks)

# ---- monolithic CNF with the G0 generator lex-leader (Lemma 8) ----
gens0 = row_stabiliser_generators(red, fix_point_one=False)
ptsM, blocksM = pts1, set(blocks1)
steps = 0
while True:
    vec = tuple(t in blocksM for t in triples)
    moved = False
    for g in gens0:
        img = {apply_to_triple(g, b) for b in blocksM}
        if tuple(t in img for t in triples) < vec:
            ptsM, blocksM = relabel(ptsM, blocksM, g); moved = True; steps += 1; break
    if not moved: break
log("G0 lex descent steps:", steps)
chiM = chi_of(ptsM)
assert {t for t in triples if chiM[t] == 0} == blocksM
t0 = time.time()
encM = build_existence_encoding(15, 31, lex=True)
chiM = reorient_to_anchors(chiM, sign_anchors(red))
valM = full_assignment(encM, chiM, blocksM)
log("MONOLITH (15,31), G0 lex:", propagate_and_check(encM, valM), "vars", encM.nvars, "clauses", len(encM.clauses), f"{time.time()-t0:.0f}s")

# ---- cube CNF: Lemma 7 then Lemma 8 under G2 ----
cs = enumerate_cubes(red)
G1 = group_closure(cs.generators, n)
log("(15,31): row1 configs", len(cs.configurations), "cubes", len(cs.representatives), "orbits", cs.orbit_sizes, "|G1|", len(G1))
cov1 = {p for b in blocks1 for p in itertools.combinations(b,2)}
deg1 = [sum(tuple(sorted((p,q))) not in cov1 for q in range(n) if q != p) for p in range(n)]
full = [x for x in range(1,n) if deg1[x] == red.min_leave_degree]
log("full points besides 0 (canonical labelling):", full)
y = full[0]
pair_of = {}
for b in red.row_blocks:
    pair_of[b[1]] = (b[1], b[2]); pair_of[b[2]] = (b[1], b[2])
g = pair_exchange(n, (1,2), pair_of[y])
ptsC, blocksC = relabel(pts1, blocks1, g)
def degrees(blocks):
    cov = {p for b in blocks for p in itertools.combinations(b,2)}
    return [sum(tuple(sorted((p,q))) not in cov for q in range(n) if q != p) for p in range(n)], cov
degC, covC = degrees(blocksC)
if degC[1] != red.min_leave_degree:
    g = (0,2,1) + tuple(range(3,n)); ptsC, blocksC = relabel(ptsC, blocksC, g); degC, covC = degrees(blocksC)
assert degC[1] == red.min_leave_degree and {b for b in blocksC if 0 in b} == set(red.row_blocks)
config = (tuple(sorted(tuple(sorted(x for x in b if x != 1)) for b in blocksC if 1 in b and b != (0,1,2))),
          tuple(sorted(q for q in range(3,n) if tuple(sorted((1,q))) not in covC)))
assert config in set(cs.configurations)
rep = None
for h in G1:
    img = apply_to_config(h, config)
    if img in cs.representatives:
        rep = img; ptsC, blocksC = relabel(ptsC, blocksC, h); break
assert rep is not None
ci = cs.representatives.index(rep)
G2 = [h for h in G1 if apply_to_config(h, rep) == rep]
log("Pegg lands in cube", ci, "orbit size", cs.orbit_sizes[ci], "|G2| =", len(G2))
best = None
for h in G2:
    img = {apply_to_triple(h, b) for b in blocksC}
    v = tuple(t in img for t in triples)
    if best is None or v < best[0]: best = (v, h)
ptsC, blocksC = relabel(ptsC, blocksC, best[1])
chiC = chi_of(ptsC)
assert {t for t in triples if chiC[t] == 0} == blocksC
t0 = time.time()
encC = build_existence_encoding(15, 31, lex=False, cube=(rep,), cube_group=G2)
chiC = reorient_to_anchors(chiC, sign_anchors(red))
cu = cube_units(red, (rep,))
assert all((t in blocksC) == v for t, v in cu.items())
valC = full_assignment(encC, chiC, blocksC)
log("CUBE (15,31) cube", ci, "G2 lex:", propagate_and_check(encC, valC), "vars", encC.nvars, "clauses", len(encC.clauses), "lex elements", encC.counts["lex_generators"], f"{time.time()-t0:.0f}s")

# ---- negative control: a WRONG row (point 1 not full) must falsify cube units; a wrong sign must falsify GP ----
bad = dict(valC)
some_t = next(t for t in triples if chiC[t] != 0 and 0 not in t and 1 not in t)
bad[encC.chiro.var(some_t, 1)], bad[encC.chiro.var(some_t, -1)] = bad[encC.chiro.var(some_t, -1)], bad[encC.chiro.var(some_t, 1)]
neg = propagate_and_check(encC, bad)["falsified"]
log("negative control (one sign flipped):", neg, "falsified clauses (must be > 0)")
resM = propagate_and_check(encM, valM)["falsified"]; resC = propagate_and_check(encC, valC)["falsified"]
ok = (resM == 0 and resC == 0 and neg > 0)
log("PEGG_E2E", "PASS" if ok else "FAIL", f"monolith falsified={resM} cube falsified={resC} negative={neg}")
sys.exit(0 if ok else 1)
