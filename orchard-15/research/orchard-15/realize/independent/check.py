#!/usr/bin/env python3
"""
Independent (from-scratch) check of the claim that the unique pseudoline-admitting
PTS(13,23) has NO realization by 13 points over any field of characteristic 0 whose
collinear triples are exactly its 23 blocks.

Only sympy is used.  Nothing is imported from realize/core.py, realize/realize.py or
realize/check_realization.py, and none of them was read while writing this file.

Method (see README.md next to this file):
  frame      four points, no three in a block, first pair preferably uncovered
  chart      frame -> (1,0,0),(0,1,0),(0,0,1),(1,1,1); other points (x,y,1),
             except the (at most one) point p with {f0,f1,p} a block, which gets (x,1,0)
  ideal      I = < det(p_a,p_b,p_c) : {a,b,c} a block >
  basis      reduced Groebner basis of I (grevlex) computed DIRECTLY by sympy
  radical    for a non-block triple T:  det_T in sqrt(I)  <=>  GB(I + <1 - t det_T>) == {1}
             one such T suffices:  g = prod of all non-block dets is then in sqrt(I),
             i.e. I : g^oo = (1)  (the builder's certificate).
  fallback   incremental saturation I : (d1 d2 ... )^oo via elimination of t with a
             product order, only if no single T is forced.
"""
import argparse
import itertools
import json
import os
import resource
import sys
import time

from sympy import Integer, Poly, QQ, Rational, S, expand, groebner, symbols
from sympy.polys.orderings import ProductOrder, grevlex as _grevlex, lex as _lex


class _Slice:
    """hashable monomial slicer for ProductOrder (sympy 1.14's build_product_order is unhashable)"""
    def __init__(self, a, b):
        self.a, self.b = a, b
    def __call__(self, m):
        return m[self.a:self.b]
    def __eq__(self, o):
        return isinstance(o, _Slice) and (self.a, self.b) == (o.a, o.b)
    def __hash__(self):
        return hash(("_Slice", self.a, self.b))

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- PTS
def parse_pts(line):
    """'v b : a b c , d e f , ... ;'  ->  (v, [sorted triples])"""
    head, body = line.split(":", 1)
    v, b = (int(s) for s in head.split())
    body = body.strip()
    if body.endswith(";"):
        body = body[:-1]
    blocks = []
    for part in body.split(","):
        part = part.strip()
        if not part:
            continue
        t = tuple(sorted(int(s) for s in part.split()))
        blocks.append(t)
    if len(blocks) != b:
        raise ValueError(f"header says {b} blocks, found {len(blocks)}")
    validate_pts(v, blocks)
    return v, blocks


def validate_pts(v, blocks):
    seen_pairs = set()
    seen_blocks = set()
    for t in blocks:
        if len(t) != 3 or len(set(t)) != 3:
            raise ValueError(f"bad block {t}")
        if any(p < 0 or p >= v for p in t):
            raise ValueError(f"point out of range in {t}")
        if t in seen_blocks:
            raise ValueError(f"repeated block {t}")
        seen_blocks.add(t)
        for pr in itertools.combinations(t, 2):
            if pr in seen_pairs:
                raise ValueError(f"pair {pr} in two blocks: not a partial STS")
            seen_pairs.add(pr)


def covered_pairs(blocks):
    return {pr for t in blocks for pr in itertools.combinations(t, 2)}


def nonblock_triples(v, blocks):
    bs = set(blocks)
    return [t for t in itertools.combinations(range(v), 3) if t not in bs]


def pts_line(v, blocks):
    return f"{v} {len(blocks)} : " + " , ".join(" ".join(map(str, t)) for t in blocks) + " ;"


# ----------------------------------------------------------------------------- frames
def all_frames(v, blocks):
    """Ordered 4-tuples (f0,f1,f2,f3), f0<f1, f2<f3, no three in a block.
    Returns list of (frame, first_pair_covered)."""
    bs = set(blocks)
    cov = covered_pairs(blocks)
    out = []
    for f0, f1 in itertools.combinations(range(v), 2):
        rest = [p for p in range(v) if p not in (f0, f1)]
        for f2, f3 in itertools.combinations(rest, 2):
            fr = (f0, f1, f2, f3)
            if any(tuple(sorted(tr)) in bs for tr in itertools.combinations(fr, 3)):
                continue
            out.append((fr, (f0, f1) in cov))
    return out


def choose_frame(v, blocks, avoid=None, which=0):
    """Prefer frames whose first pair is uncovered (then no point can sit on z=0).
    `avoid`: a frame to differ from (second-frame check); `which`: index among candidates."""
    cands = all_frames(v, blocks)
    good = [fr for fr, covered in cands if not covered]
    pool = good if good else [fr for fr, _ in cands]
    if avoid is not None:
        # prefer a frame disjoint from `avoid`, else at least a different first pair
        disjoint = [fr for fr in pool if not set(fr) & set(avoid)]
        diffpair = [fr for fr in pool if (fr[0], fr[1]) != (avoid[0], avoid[1])]
        pool = disjoint or diffpair or [fr for fr in pool if fr != avoid]
    if not pool:
        raise ValueError("no projective frame (4 points, no 3 in a block) exists")
    return pool[which % len(pool)], bool(good)


def validate_frame(v, blocks, frame):
    bs = set(blocks)
    if len(set(frame)) != 4 or any(p < 0 or p >= v for p in frame):
        raise ValueError(f"bad frame {frame}")
    for tr in itertools.combinations(frame, 3):
        if tuple(sorted(tr)) in bs:
            raise ValueError(f"frame {frame} has three points in block {tuple(sorted(tr))}")


# ----------------------------------------------------------------------------- chart
def chart(v, blocks, frame, wrong_chart=False):
    """Coordinates for every point after fixing the frame.
    Returns (coords: point -> 3-tuple, gens: list of symbols, inf_point or None).
    wrong_chart=True is ONLY for the worked-wrong control: it (incorrectly) gives the
    point that must lie on z=0 an affine chart (x,y,1) instead of (x,1,0)."""
    f0, f1, f2, f3 = frame
    one, zero = Integer(1), Integer(0)
    coords = {f0: (one, zero, zero), f1: (zero, one, zero), f2: (zero, zero, one), f3: (one, one, one)}
    bs = set(blocks)
    gens = []
    inf_point = None
    for p in range(v):
        if p in frame:
            continue
        on_infinity = tuple(sorted((f0, f1, p))) in bs
        if on_infinity and not wrong_chart:
            # p is collinear with (1,0,0),(0,1,0): p=(a,b,0); p != f0 forces b != 0; scale b=1
            x = symbols(f"x{p}")
            coords[p] = (x, one, zero)
            gens.append(x)
            inf_point = p
        else:
            if on_infinity:
                inf_point = p  # recorded so the wrong control can report it
            x, y = symbols(f"x{p} y{p}")
            coords[p] = (x, y, one)
            gens += [x, y]
    return coords, gens, inf_point


def det3(P, Q, R):
    (a0, a1, a2), (b0, b1, b2), (c0, c1, c2) = P, Q, R
    return expand(a0 * (b1 * c2 - b2 * c1) - a1 * (b0 * c2 - b2 * c0) + a2 * (b0 * c1 - b1 * c0))


def block_ideal(coords, blocks, allow_constant=False):
    """Generators of I; identically-zero generators (a block already forced by the chart)
    are dropped and reported.  A nonzero constant would mean the chart is wrong
    (guarded; only the worked-wrong control switches the guard off)."""
    gensI, auto = [], []
    for t in blocks:
        d = det3(coords[t[0]], coords[t[1]], coords[t[2]])
        if d == 0:
            auto.append(t)
        elif d.is_number and not allow_constant:
            raise RuntimeError(f"block {t} gives constant {d}: chart/frame inconsistent")
        else:
            gensI.append(d)
    return gensI, auto


# ----------------------------------------------------------------------------- algebra
def is_one(G):
    ex = list(G.exprs) if hasattr(G, "exprs") else list(G)
    return len(ex) == 1 and ex[0] == 1


def krull_dimension(Gexprs, gens, order="grevlex"):
    """dim Q[gens]/I from leading monomials of a Groebner basis (graded order):
    the largest S subset of gens such that no leading monomial lives in Q[S]."""
    n = len(gens)
    masks = set()
    for g in Gexprs:
        if g == 1:
            return -1
        p = Poly(g, *gens, domain=QQ)
        exps = p.LM(order=order).exponents
        mask = 0
        for i, e in enumerate(exps):
            if e > 0:
                mask |= 1 << i
        masks.add(mask)
    masks = sorted(masks)
    if not masks:
        return n
    for k in range(n, -1, -1):
        for Ssub in itertools.combinations(range(n), k):
            Smask = 0
            for i in Ssub:
                Smask |= 1 << i
            if all((m & ~Smask) != 0 for m in masks):
                return k
    return 0


def reduced_gb(polys, gens, order="grevlex", method="buchberger"):
    t0 = time.time()
    G = groebner(polys, *gens, order=order, domain=QQ, method=method)
    return G, time.time() - t0


def in_radical(Gexprs, f, gens, method="buchberger"):
    """f in sqrt(I)  <=>  1 in I + <1 - t f>   (Rabinowitsch)."""
    t = symbols("t_rab")
    H = groebner(list(Gexprs) + [1 - t * f], t, *gens, order="grevlex", domain=QQ, method=method)
    return is_one(H)


def saturate(Gexprs, f, gens, method="buchberger"):
    """I : f^oo = (I + <1 - t f>) intersect Q[gens], via a t-eliminating product order."""
    t = symbols("t_rab")
    allgens = (t,) + tuple(gens)
    order = ProductOrder((_lex, _Slice(0, 1)), (_grevlex, _Slice(1, len(allgens))))
    H = groebner(list(Gexprs) + [1 - t * f], *allgens, order=order, domain=QQ, method=method)
    kept = [h for h in H.exprs if not h.has(t)]
    if not kept:
        kept = [Integer(0)]
    return kept


# ----------------------------------------------------------------------------- driver
def analyse(v, blocks, frame=None, label="run", method="buchberger", all_forced=False,
            max_single=None, full_product=True, wrong_chart=False, gb_only=False,
            frame_index=0, avoid_frame=None, skip_if_one=False, sat_budget=None, first_triples=None):
    """The whole certificate check for one PTS and one frame.  Returns a dict."""
    res = {"label": label, "v": v, "b": len(blocks), "pts": pts_line(v, blocks)}
    if frame is None:
        frame, uncovered_exists = choose_frame(v, blocks, avoid=avoid_frame, which=frame_index)
    else:
        validate_frame(v, blocks, frame)
        uncovered_exists = None
    cov = covered_pairs(blocks)
    res["frame"] = list(frame)
    res["first_pair_uncovered"] = (frame[0], frame[1]) not in cov
    coords, gens, inf_point = chart(v, blocks, frame, wrong_chart=wrong_chart)
    res["point_on_infinity"] = inf_point
    res["wrong_chart"] = wrong_chart
    res["variables"] = [str(g) for g in gens]
    gensI, auto = block_ideal(coords, blocks, allow_constant=wrong_chart)
    res["generators"] = len(gensI)
    res["blocks_forced_by_chart"] = auto
    res["generator_degrees"] = sorted(Poly(g, *gens).total_degree() for g in gensI)
    res["constant_generators"] = [str(g) for g in gensI if g.is_number]
    log(f"[{label}] frame={frame} vars={len(gens)} generators={len(gensI)} "
        f"(chart-forced blocks: {auto}) inf_point={inf_point}")

    G, tG = reduced_gb(gensI, gens, method=method)
    Gex = list(G.exprs)
    res["gb_seconds"] = round(tG, 3)
    res["gb_size"] = len(Gex)
    res["gb_is_one"] = is_one(G)
    res["gb_max_degree"] = max(Poly(g, *gens).total_degree() for g in Gex)
    res["gb_zero_dimensional"] = bool(G.is_zero_dimensional)
    dim = krull_dimension(Gex, gens)
    res["gb_dimension"] = dim
    log(f"[{label}] GB(I): {len(Gex)} polys, max deg {res['gb_max_degree']}, dim {dim}, "
        f"is_one={res['gb_is_one']}, {tG:.2f}s")
    if gb_only:
        return res
    if res["gb_is_one"]:
        res["nonrealizable"] = True
        res["verdict"] = "NON-REALIZABLE over every char-0 field: I itself is (1) (no solutions, degenerate or not)"
        return res

    # --- single non-block triples
    nb = nonblock_triples(v, blocks)
    if first_triples:
        head = [T for T in first_triples if T in set(nb)]
        nb = head + [T for T in nb if T not in set(head)]
    res["nonblock_triples"] = len(nb)
    forced, tested, times = [], 0, []
    t0 = time.time()
    for T in nb:
        if max_single is not None and tested >= max_single:
            break
        dT = det3(coords[T[0]], coords[T[1]], coords[T[2]])
        tested += 1
        t1 = time.time()
        if dT.is_number:
            # a non-block triple with constant nonzero determinant: cannot be forced
            ok = False if dT != 0 else True
        else:
            ok = in_radical(Gex, dT, gens, method=method)
        times.append(round(time.time() - t1, 3))
        if ok:
            forced.append(T)
            log(f"[{label}] non-block triple {T} IS forced collinear (det in sqrt I) "
                f"after {tested} tests, {time.time()-t0:.1f}s")
            if not all_forced:
                break
    res["single_triples_tested"] = tested
    res["single_triple_seconds_total"] = round(time.time() - t0, 3)
    res["single_triple_seconds_max"] = max(times) if times else None
    res["forced_single_triples"] = forced
    if forced:
        res["nonrealizable"] = True
        res["verdict"] = "NON-REALIZABLE over every char-0 field (certificate {1})"
        res["certificate"] = ("det of non-block triple %s lies in sqrt(I); hence the product g of "
                              "all non-block determinants lies in sqrt(I); I : g^oo = (1)" % (forced[0],))
        return res

    if not full_product:
        res["nonrealizable"] = None
        res["verdict"] = "no single non-block triple forced (product not attempted)"
        return res

    # --- fallback: incremental saturation by every non-block determinant
    log(f"[{label}] no single triple forced; incremental saturation by all {len(nb)} dets")
    cur = Gex
    t0 = time.time()
    steps = []
    for k, T in enumerate(nb):
        if sat_budget is not None and time.time() - t0 > sat_budget:
            res["saturation_steps"] = steps
            res["saturation_seconds"] = round(time.time() - t0, 3)
            res["nonrealizable"] = None
            res["verdict"] = ("UNDETERMINED by saturation within %ss budget: %d of %d steps done, "
                              "current dimension %d" % (sat_budget, len(steps), len(nb), steps[-1]["dim"] if steps else dim))
            return res
        dT = det3(coords[T[0]], coords[T[1]], coords[T[2]])
        if dT.is_number:
            continue
        t1 = time.time()
        cur = saturate(cur, dT, gens, method=method)
        Gk = groebner(cur, *gens, order="grevlex", domain=QQ, method=method)
        cur = list(Gk.exprs)
        d = krull_dimension(cur, gens)
        steps.append({"triple": T, "seconds": round(time.time() - t1, 3), "dim": d, "size": len(cur)})
        log(f"[{label}]   sat by {T}: dim {d}, size {len(cur)}, {time.time()-t1:.1f}s")
        if is_one(Gk):
            res["saturation_steps"] = steps
            res["saturation_seconds"] = round(time.time() - t0, 3)
            res["nonrealizable"] = True
            res["verdict"] = ("NON-REALIZABLE over every char-0 field: I : (d_1...d_%d)^oo = (1) "
                              "after %d saturation steps" % (k + 1, len(steps)))
            return res
    res["saturation_steps"] = steps
    res["saturation_seconds"] = round(time.time() - t0, 3)
    res["saturated_basis"] = [str(g) for g in cur]
    res["saturated_dimension"] = krull_dimension(cur, gens)
    res["nonrealizable"] = False
    res["verdict"] = ("REALIZABLE over the algebraic closure of Q: I : g^oo != (1), "
                      "dimension %d" % res["saturated_dimension"])
    return res


# ----------------------------------------------------------------------------- witnesses
def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def check_realization(v, blocks, P):
    """Direct check, frame-free: det == 0 exactly on blocks; points pairwise distinct
    (distinctness is implied by the non-block determinants when v >= 4, but check anyway)."""
    bs = set(blocks)
    bad = []
    for T in itertools.combinations(range(v), 3):
        d = det3(P[T[0]], P[T[1]], P[T[2]])
        if (d == 0) != (T in bs):
            bad.append(T)
    for a, b in itertools.combinations(range(v), 2):
        if all(c == 0 for c in cross(P[a], P[b])):
            bad.append((a, b))
    for p in range(v):
        if all(c == 0 for c in P[p]):
            bad.append((p,))
    return bad


def to_frame(P, frame):
    """Projective map sending frame -> standard frame; returns M (3x3 sympy Matrix)."""
    from sympy import Matrix, linsolve
    f0, f1, f2, f3 = frame
    A = Matrix([[P[f0][i], P[f1][i], P[f2][i]] for i in range(3)])
    lam = A.solve(Matrix([P[f3][i] for i in range(3)]))
    B = Matrix([[lam[j] * P[(f0, f1, f2)[j]][i] for j in range(3)] for i in range(3)])
    return B.inv()


def witness_in_ideal(v, blocks, P, frame):
    """Move a realization into the frame chart, substitute into every generator of I and
    into every non-block determinant: all generators must vanish, all non-block dets not."""
    M = to_frame(P, frame)
    coords, gens, inf_point = chart(v, blocks, frame)
    vals = {}
    for p in range(v):
        q = M * __import__("sympy").Matrix([P[p][0], P[p][1], P[p][2]])
        q = [Rational(q[i]) for i in range(3)]
        if p in frame:
            continue
        if p == inf_point:
            if q[2] != 0 or q[1] == 0:
                return False, f"point {p} should be on z=0 with y!=0, got {q}"
            vals[coords[p][0]] = q[0] / q[1]
        else:
            if q[2] == 0:
                return False, f"point {p} landed on z=0 in the frame chart: {q}"
            vals[coords[p][0]] = q[0] / q[2]
            vals[coords[p][1]] = q[1] / q[2]
    gensI, _ = block_ideal(coords, blocks)
    bad = [g for g in gensI if g.subs(vals) != 0]
    if bad:
        return False, f"{len(bad)} generators do not vanish at the witness"
    for T in nonblock_triples(v, blocks):
        d = det3(coords[T[0]], coords[T[1]], coords[T[2]]).subs(vals)
        if d == 0:
            return False, f"non-block triple {T} vanishes at the witness"
    return True, {str(k): str(val) for k, val in vals.items()}


def pappus_witness(blocks):
    """PTS 9 9 : 0 1 2 , 0 4 6 , 0 5 7 , 1 3 6 , 1 5 8 , 2 3 7 , 2 4 8 , 3 4 5 , 6 7 8.
    0,1,2 on one line, 3,4,5 on another; 6=04^13, 7=05^23, 8=15^24; 678 is Pappus."""
    I = Integer
    for a in itertools.product(range(-3, 6), repeat=6):
        a0, a1, a2, b3, b4, b5 = (I(x) for x in a)
        if len({a0, a1, a2}) < 3 or len({b3, b4, b5}) < 3:
            continue
        P = {0: (a0, I(0), I(1)), 1: (a1, I(0), I(1)), 2: (a2, I(0), I(1)),
             3: (b3, I(1), I(1)), 4: (b4, I(1), I(1)), 5: (b5, I(1), I(1))}
        P[6] = cross(cross(P[0], P[4]), cross(P[1], P[3]))
        P[7] = cross(cross(P[0], P[5]), cross(P[2], P[3]))
        P[8] = cross(cross(P[1], P[5]), cross(P[2], P[4]))
        if not check_realization(9, blocks, P):
            return P
    return None


def desargues_witness(blocks):
    """PTS 10 10 : 0 1 4 , 0 2 5 , 0 3 6 , 1 2 7 , 1 3 8 , 2 3 9 , 4 5 7 , 4 6 8 , 5 6 9 , 7 8 9.
    0 = centre; triangles 123 and 456 with 4 on 01, 5 on 02, 6 on 03;
    7=12^45, 8=13^46, 9=23^56; 789 is Desargues."""
    I = Integer
    base = {0: (I(0), I(0), I(1)), 1: (I(1), I(0), I(1)), 2: (I(0), I(1), I(1)), 3: (I(2), I(3), I(1))}
    for s in itertools.product(range(2, 9), repeat=3):
        P = dict(base)
        for k, (p, sk) in enumerate(zip((1, 2, 3), s)):
            P[4 + k] = tuple(P[0][i] + I(sk) * (P[p][i] - P[0][i]) for i in range(3))
        P[7] = cross(cross(P[1], P[2]), cross(P[4], P[5]))
        P[8] = cross(cross(P[1], P[3]), cross(P[4], P[6]))
        P[9] = cross(cross(P[2], P[3]), cross(P[5], P[6]))
        if not check_realization(10, blocks, P):
            return P
    return None


# ----------------------------------------------------------------------------- controls
CONTROLS = {
    "fano": "7 7 : 0 1 2 , 0 3 4 , 0 5 6 , 1 3 5 , 1 4 6 , 2 3 6 , 2 4 5 ;",
    "pappus": "9 9 : 0 1 2 , 0 4 6 , 0 5 7 , 1 3 6 , 1 5 8 , 2 3 7 , 2 4 8 , 3 4 5 , 6 7 8 ;",
    "desargues": "10 10 : 0 1 4 , 0 2 5 , 0 3 6 , 1 2 7 , 1 3 8 , 2 3 9 , 4 5 7 , 4 6 8 , 5 6 9 , 7 8 9 ;",
    "nonreal_10_3": "10 10 : 0 4 6 , 0 5 7 , 0 8 9 , 1 2 3 , 1 4 5 , 1 6 7 , 2 4 8 , 2 5 9 , 3 6 8 , 3 7 9 ;",
}
EXPECT = {"fano": "one", "pappus": "not_one", "desargues": "not_one", "nonreal_10_3": "one", "bgs_14_27": "one"}


def save(res, name):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name + ".json")
    with open(path, "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    log(f"saved {path}")


def cmd_run(args):
    if args.pts_file:
        line = open(args.pts_file).read().strip().splitlines()[0]
    else:
        line = args.pts
    v, blocks = parse_pts(line)
    if args.drop is not None:
        dropped = [blocks[i] for i in args.drop]
        blocks = [b for i, b in enumerate(blocks) if i not in set(args.drop)]
        log(f"dropped blocks {dropped}")
    frame = tuple(int(s) for s in args.frame.split(",")) if args.frame else None
    avoid = tuple(int(s) for s in args.avoid_frame.split(",")) if args.avoid_frame else None
    res = analyse(v, blocks, frame=frame, label=args.label, method=args.method,
                  all_forced=args.all_forced, max_single=args.max_single,
                  full_product=not args.no_product, gb_only=args.gb_only,
                  frame_index=args.frame_index, avoid_frame=avoid, sat_budget=args.sat_budget,
                  first_triples=[tuple(int(s) for s in t.split(",")) for t in args.first_triples.split(";")] if args.first_triples else None)
    if args.drop is not None:
        res["dropped_blocks"] = dropped
    save(res, args.label)
    print(json.dumps({k: res[k] for k in res if k not in ("saturated_basis",)}, default=str))


def cmd_controls(args):
    table = {}
    for name, line in CONTROLS.items():
        if args.only and name not in args.only:
            continue
        v, blocks = parse_pts(line)
        res = analyse(v, blocks, label=name, method=args.method, sat_budget=args.sat_budget)
        res["expected"] = EXPECT[name]
        got = "one" if res.get("nonrealizable") else ("not_one" if res.get("nonrealizable") is False else "undetermined")
        if name in ("pappus", "desargues"):
            P = pappus_witness(blocks) if name == "pappus" else desargues_witness(blocks)
            res["witness"] = {str(p): [str(c) for c in P[p]] for p in P} if P else None
            res["witness_direct_check"] = (check_realization(v, blocks, P) == []) if P else False
            ok, info = witness_in_ideal(v, blocks, P, tuple(res["frame"])) if P else (False, "no witness")
            res["witness_vanishes_on_ideal"] = ok
            res["witness_chart_values"] = info
            # a point of V(I) with every non-block determinant nonzero proves I : g^oo != (1)
            if ok and res["witness_direct_check"] and got != "one":
                got = "not_one"
            elif got != "one":
                got = "undetermined"
        res["got"] = got
        res["control_passed"] = (got == EXPECT[name])
        save(res, "control_" + name)
        table[name] = res
        log(f"CONTROL {name}: expected {EXPECT[name]} got {got} passed={res['control_passed']}")
    if not args.only or "bgs_14_27" in args.only:
        path = os.path.join(HERE, "..", "..", "chiro", "scratch", "exist-14-27.pts")
        v, blocks = parse_pts(open(path).read().strip().splitlines()[0])
        res = analyse(v, blocks, label="bgs_14_27", method=args.method, sat_budget=args.sat_budget)
        res["expected"] = "one"
        got = "one" if res.get("nonrealizable") else "not_one"
        res["got"] = got
        res["control_passed"] = (got == "one")
        save(res, "control_bgs_14_27")
        table["bgs_14_27"] = res
        log(f"CONTROL bgs_14_27: expected one got {got} passed={res['control_passed']}")
    print(json.dumps({k: {"expected": r["expected"], "got": r["got"], "passed": r["control_passed"],
                          "frame": r["frame"], "dim_I": r["gb_dimension"],
                          "forced": r.get("forced_single_triples"), "gb_s": r["gb_seconds"],
                          "single_s": r.get("single_triple_seconds_total")}
                      for k, r in table.items()}, indent=1, default=str))


def cmd_selftest(args):
    """Worked WRONG controls: things a naive check would get wrong, shown to fail here."""
    out = {}
    # 1. Pappus with a frame whose first pair IS covered, and the WRONG chart for the third
    #    point: the ideal becomes inconsistent and a naive check would report {1} for a
    #    realizable configuration.  The correct chart (x,1,0) must NOT give {1}.
    v, blocks = parse_pts(CONTROLS["pappus"])
    cov_frames = [fr for fr, covered in all_frames(v, blocks) if covered]
    fr = cov_frames[0]
    wrong = analyse(v, blocks, frame=fr, label="selftest_pappus_wrongchart", wrong_chart=True, full_product=False)
    right = analyse(v, blocks, frame=fr, label="selftest_pappus_rightchart", wrong_chart=False, full_product=False)
    out["wrong_chart_frame"] = list(fr)
    out["wrong_chart_gives_one"] = wrong["gb_is_one"] or bool(wrong.get("forced_single_triples"))
    out["wrong_chart_constant_generators"] = wrong.get("constant_generators")
    out["right_chart_gives_one"] = right["gb_is_one"] or bool(right.get("forced_single_triples"))
    out["wrong_chart_point"] = wrong["point_on_infinity"]
    # 2. a perturbed witness must be rejected by the direct check
    P = pappus_witness(blocks)
    Q = dict(P)
    Q[8] = (P[8][0] + 1, P[8][1], P[8][2])
    out["perturbed_pappus_witness_rejected"] = bool(check_realization(v, blocks, Q))
    out["perturbed_pappus_witness_rejected_by_ideal"] = not witness_in_ideal(v, blocks, Q, tuple(right["frame"]))[0]
    # 3. radical membership must be able to say NO: for Pappus, a non-block triple is not forced
    coords, gens, _ = chart(v, blocks, tuple(right["frame"]))
    gensI, _ = block_ideal(coords, blocks)
    G, _ = reduced_gb(gensI, gens)
    T = nonblock_triples(v, blocks)[0]
    out["pappus_first_nonblock_not_forced"] = not in_radical(list(G.exprs), det3(*(coords[i] for i in T)), gens)
    # 4. and YES on something true: Pappus' theorem itself.  Drop block 678 and ask
    #    whether 678 is forced by the other eight.
    b8 = [b for b in blocks if b != (6, 7, 8)]
    coords, gens, _ = chart(v, b8, tuple(right["frame"]))
    gensI, _ = block_ideal(coords, b8)
    G, _ = reduced_gb(gensI, gens)
    d678 = det3(coords[6], coords[7], coords[8])
    out["pappus_theorem_678_in_radical_of_8_blocks"] = in_radical(list(G.exprs), d678, gens)
    # (it is NOT expected to be in the radical: degenerate components of the 8-block ideal
    #  exist on which 678 is not collinear; the saturated statement is the theorem.)
    sat = list(G.exprs)
    for T in nonblock_triples(v, b8):
        if T == (6, 7, 8):
            continue
        sat = list(groebner(saturate(sat, det3(*(coords[i] for i in T)), gens), *gens, order="grevlex", domain=QQ).exprs)
        if is_one(groebner(sat, *gens, order="grevlex", domain=QQ)):
            break
    out["pappus_theorem_678_in_radical_after_saturation"] = in_radical(sat, d678, gens)
    out["pappus_8block_saturated_dim"] = krull_dimension(sat, gens)
    save(out, "selftest")
    print(json.dumps(out, indent=1, default=str))




# ----------------------------------------------------------------------------- cofactors
# An explicit certificate that does NOT use the Groebner engine:  target = sum_k a_k f_k,
# with the f_k the block determinants and the a_k explicit polynomials, verified by expand().
def _linear_echelon(lin_polys, gens):
    """Row-reduce linear generators.  Returns (rows, M): rows[j] = (pivot symbol, e_j) meaning
    E_j = pivot - e_j with e_j affine in non-pivot variables, and E_j = sum_k M[j][k] lin_polys[k]."""
    from sympy import Matrix, eye
    n = len(gens)
    A = []
    for f in lin_polys:
        p = Poly(f, *gens, domain=QQ)
        row = [p.coeff_monomial(g) for g in gens] + [p.coeff_monomial(1)]
        A.append(row)
    m = len(lin_polys)
    Aug = Matrix(A).row_join(eye(m))
    R, piv = Aug.rref()
    rows, M = [], []
    for j, pc in enumerate(piv):
        if pc >= n:  # pivot in the constant column: 1 in the ideal
            raise RuntimeError("linear generators are inconsistent: 1 in I")
        pivot = gens[pc]
        # E_j = sum_c R[j,c] g_c + R[j,n] ; pivot coefficient 1
        e = -sum(R[j, c] * gens[c] for c in range(n) if c != pc) - R[j, n]
        rows.append((pivot, expand(e)))
        M.append([R[j, n + 1 + k] for k in range(m)])
    return rows, M


def cofactor_certificate(gensI, gens, target, D=2):
    """Find polynomials a_k with target = sum_k a_k * gensI[k] (cofactors of degree <= D in the
    free variables for the nonlinear generators).  Returns (cofactors list, info dict) or None."""
    from sympy import Matrix, cancel, Symbol
    from sympy.polys.matrices import DomainMatrix
    lin_idx = [k for k, f in enumerate(gensI) if Poly(f, *gens).total_degree() == 1]
    non_idx = [k for k, f in enumerate(gensI) if Poly(f, *gens).total_degree() > 1]
    rows, M = _linear_echelon([gensI[k] for k in lin_idx], gens)
    sigma = {p: e for p, e in rows}
    free = [g for g in gens if g not in sigma]
    fbar = [expand(gensI[k].subs(sigma, simultaneous=True)) for k in non_idx]
    lbar = expand(target.subs(sigma, simultaneous=True))
    info = {"linear_generators": len(lin_idx), "nonlinear_generators": len(non_idx),
            "free_variables": [str(g) for g in free], "cofactor_degree_bound": D}
    if lbar == 0:
        abar = [Integer(0)] * len(non_idx)
    else:
        # Macaulay system: unknown c_{i,m}, sum c_{i,m} m fbar_i = lbar
        mons = [m for d in range(D + 1) for m in itertools.combinations_with_replacement(free, d)]
        monexprs = [Integer(1) if not m else expand(__import__("functools").reduce(lambda a, b: a * b, m)) for m in mons]
        cols = []
        rowkeys = {}
        for i, fb in enumerate(fbar):
            for me in monexprs:
                p = Poly(expand(me * fb), *free, domain=QQ)
                col = {}
                for mon, c in p.terms():
                    if mon not in rowkeys:
                        rowkeys[mon] = len(rowkeys)
                    col[rowkeys[mon]] = c
                cols.append(col)
        pl = Poly(lbar, *free, domain=QQ)
        bvec = {}
        for mon, c in pl.terms():
            if mon not in rowkeys:
                rowkeys[mon] = len(rowkeys)
            bvec[rowkeys[mon]] = c
        nr, nc = len(rowkeys), len(cols)
        info["macaulay_rows"] = nr
        info["macaulay_cols"] = nc
        A = [[QQ(0)] * (nc + 1) for _ in range(nr)]
        for j, col in enumerate(cols):
            for r, c in col.items():
                A[r][j] = QQ.from_sympy(c)
        for r, c in bvec.items():
            A[r][nc] = QQ.from_sympy(c)
        t0 = time.time()
        dm = DomainMatrix(A, (nr, nc + 1), QQ)
        R, piv = dm.rref()
        info["rref_seconds"] = round(time.time() - t0, 3)
        if nc in piv:
            info["consistent"] = False
            return None, info
        info["consistent"] = True
        sol = [QQ(0)] * nc
        Rl = R.to_Matrix()
        for r, pc in enumerate(piv):
            sol[pc] = Rl[r, nc]
        abar = []
        j = 0
        for i in range(len(fbar)):
            a = Integer(0)
            for me in monexprs:
                if sol[j] != 0:
                    a += Rational(sol[j].numerator, sol[j].denominator) * me
                j += 1
            abar.append(expand(a))
    # lift: r = target - sum abar_i f_i  must lie in the ideal of the linear echelon rows
    cof = [Integer(0)] * len(gensI)
    for i, k in enumerate(non_idx):
        cof[k] = abar[i]
    r = expand(target - sum(abar[i] * gensI[k] for i, k in enumerate(non_idx)))
    q = []
    for pivot, e in rows:
        rsub = expand(r.subs({pivot: e}))
        num = expand(r - rsub)
        quo = cancel(num / (pivot - e))
        if quo.as_numer_denom()[1].free_symbols:
            raise RuntimeError("inexact division in lift")
        q.append(expand(quo))
        r = rsub
    if r != 0:
        info["lift_remainder"] = str(r)
        return None, info
    for j in range(len(rows)):
        for k2, k in enumerate(lin_idx):
            cof[k] = expand(cof[k] + q[j] * M[j][k2])
    # independent verification by expansion
    check = expand(target - sum(cof[k] * gensI[k] for k in range(len(gensI))))
    info["identity_verified_by_expand"] = (check == 0)
    dens = set()
    for a in cof:
        for c in Poly(a, *gens, domain=QQ).coeffs():
            dens.add(int(QQ.from_sympy(c).denominator))
    from math import lcm
    N = 1
    for d in dens:
        N = lcm(N, d)
    info["cofactor_denominator_lcm"] = N
    info["cofactor_max_degree"] = max(Poly(a, *gens).total_degree() if a != 0 else 0 for a in cof)
    return cof, info


def cmd_cofactors(args):
    line = open(args.pts_file).read().strip().splitlines()[0]
    v, blocks = parse_pts(line)
    frame = tuple(int(s) for s in args.frame.split(","))
    validate_frame(v, blocks, frame)
    T = tuple(int(s) for s in args.triple.split(","))
    coords, gens, inf_point = chart(v, blocks, frame)
    gensI, auto = block_ideal(coords, blocks)
    det = det3(coords[T[0]], coords[T[1]], coords[T[2]])
    # which power of det lies in I (not just in sqrt I)?  Guided by normal forms modulo the
    # reduced basis; the certificate itself is verified by expand() below, independently.
    from sympy import reduced
    G, _ = reduced_gb(gensI, gens)
    power = args.power
    if power is None:
        for k in range(1, 7):
            if reduced(det ** k, list(G.exprs), *gens, order="grevlex", domain=QQ)[1] == 0:
                power = k
                break
    if power is None:
        raise SystemExit("no power <= 6 of the determinant reduces to 0 modulo the basis")
    target = expand(det ** power)
    out = {"frame": list(frame), "triple": list(T), "det": str(det), "power": power,
           "target": str(target) if len(str(target)) < 4000 else f"det^{power} ({len(str(target))} chars)",
           "generators": {str(b): str(g) for b, g in zip([b for b in blocks if b not in auto], gensI)}}
    t0 = time.time()
    for D in range(0, args.max_degree + 1):
        cof, info = cofactor_certificate(gensI, gens, target, D=D)
        if cof is not None:
            break
    out["seconds"] = round(time.time() - t0, 3)
    out["info"] = info
    if cof is None:
        out["found"] = False
    else:
        out["found"] = True
        out["cofactors"] = {str(b): str(a) for b, a in zip([b for b in blocks if b not in auto], cof)}
        out["identity"] = f"det{tuple(T)}^{power} == sum_k cofactor_k * det_k"
    save(out, args.label)
    print(json.dumps({k: out[k] for k in out if k not in ("generators", "cofactors")}, indent=1, default=str))
    if cof is not None:
        for b, a in zip([b for b in blocks if b not in auto], cof):
            if a != 0:
                print(f"  det{b} * ({a})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--pts")
    r.add_argument("--pts-file")
    r.add_argument("--frame", help="a,b,c,d")
    r.add_argument("--avoid-frame", help="a,b,c,d: choose a frame different from this one")
    r.add_argument("--frame-index", type=int, default=0)
    r.add_argument("--label", default="run")
    r.add_argument("--method", default="buchberger")
    r.add_argument("--all-forced", action="store_true")
    r.add_argument("--max-single", type=int)
    r.add_argument("--no-product", action="store_true")
    r.add_argument("--gb-only", action="store_true")
    r.add_argument("--drop", type=int, nargs="*", help="indices of blocks to drop (mutation)")
    r.add_argument("--sat-budget", type=float, default=None)
    r.add_argument("--first-triples", help="'a,b,c;d,e,f' non-block triples to test first")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("controls")
    c.add_argument("--only", nargs="*")
    c.add_argument("--method", default="buchberger")
    c.add_argument("--sat-budget", type=float, default=300.0)
    c.set_defaults(fn=cmd_controls)
    s = sub.add_parser("selftest")
    s.set_defaults(fn=cmd_selftest)
    k = sub.add_parser("cofactors")
    k.add_argument("--pts-file", required=True)
    k.add_argument("--frame", required=True)
    k.add_argument("--triple", required=True)
    k.add_argument("--max-degree", type=int, default=3)
    k.add_argument("--power", type=int, default=None)
    k.add_argument("--label", default="cofactors")
    k.set_defaults(fn=cmd_cofactors)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
