#!/usr/bin/env python3
"""Audit a (v,b) cube CNF file that a solver refuted: is it the intended cube CNF?

    cnfcheck.py <cnf> --v 15 --b 32 --cube K [--trials 25] [--seed 7]

drat-trim certifies that a FILE is unsatisfiable; this decodes the file and checks it
against an independent recomputation of what exist.py's cube-K CNF must contain:
  1. header: variable count of the chirosat base (2*C(v,3) sign vars, C(v,3) nonzero
     selectors, 6 product vars per three-term relation) plus C(v,3) block vars, and more;
  2. unit clauses decode to exactly: the v sign anchors (Lemma 4), B true on the row of
     point 0 (Lemma 3) and on cube K's row of point 1 (Lemma 7), B false on every other
     triple through 0 or 1, and one prefix-equal start per non-identity element of G2 =
     Stab_G1(cube K) (Lemma 8 inside the cube);
  3. the lex-leader clauses (every clause mentioning a variable at or beyond the first
     prefix-equal start), loaded alone into a SAT solver, accept the G2-orbit minimum of
     random block vectors extending the fixed rows and reject a non-minimal orbit element.
Exit 0 only if every check holds. Adapted from the referee script c0check.py of the
2026-09-05 prevalidation panel. Reads the whole CNF once (about 300 MB of RAM at (15,32)).
"""
import argparse, itertools, random, sys, time
from math import comb
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exist as E
from pysat.solvers import Cadical153


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cnf", type=Path)
    ap.add_argument("--v", type=int, default=15)
    ap.add_argument("--b", type=int, default=32)
    ap.add_argument("--cube", type=int, required=True)
    ap.add_argument("--trials", type=int, default=25)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    v, b = a.v, a.b
    red = E.derive_reduction(v, b)
    triples = tuple(itertools.combinations(range(v), 3))
    n3 = len(triples)
    nch = 2 * n3 + n3 + 6 * (comb(v, 5) * 5)    # chirosat base: signs, selectors, 6 per (5-set, pivot); 5 pivots per 5-set
    idx = {t: i for i, t in enumerate(triples)}
    blockvar = {t: nch + 1 + i for t, i in idx.items()}
    posvar = {t: 2 * i + 1 for t, i in idx.items()}
    inv_block = {var: t for t, var in blockvar.items()}
    inv_pos = {var: t for t, var in posvar.items()}
    problems = []
    # --- parse
    header = None; units = []; clauses = []
    with open(a.cnf) as fh:
        for line in fh:
            if line.startswith("c"): continue
            if line.startswith("p"):
                header = line.split(); continue
            lits = [int(x) for x in line.split()]
            if lits and lits[-1] == 0: lits.pop()
            if not lits: continue
            clauses.append(lits)
            if len(lits) == 1: units.append(lits[0])
    nvars = int(header[2]); ncls = int(header[3])
    print(f"header vars={nvars} clauses={ncls} parsed={len(clauses)} units={len(units)}")
    if ncls != len(clauses): problems.append("clause count differs from header")
    # --- units
    anchors = sorted(inv_pos[u] for u in units if u in inv_pos)
    pos_blocks = sorted(set(inv_block[u] for u in units if u in inv_block))   # a block in both fixed rows is emitted twice
    neg_blocks = sorted(set(inv_block[-u] for u in units if -u in inv_block))
    other = sorted(set(u for u in units if u not in inv_pos and u not in inv_block and -u not in inv_block))
    cs = E.enumerate_cubes(red)
    rep = cs.representatives[a.cube]
    pairs, _leave = rep                      # a representative is (row-1 pairs, leave pairs)
    exp_true = sorted(list(red.row_blocks) + [tuple(sorted((1,) + tuple(pair))) for pair in pairs])
    exp_false = sorted(t for t in triples if (0 in t or 1 in t) and t not in exp_true)
    print("anchors:", len(anchors), anchors)
    print("true block units:", pos_blocks == exp_true, pos_blocks)
    print("false block units:", len(neg_blocks), "expected", len(exp_false), "match:", neg_blocks == exp_false)
    if len(anchors) != v: problems.append(f"{len(anchors)} anchors, expected {v}")
    if pos_blocks != exp_true: problems.append("true block units are not row-0 plus cube rows")
    if neg_blocks != exp_false: problems.append("false block units are not the complement through points 0,1")
    G1 = E.group_closure(cs.generators, v)
    G2 = [g for g in G1 if E.apply_to_config(g, rep) == rep]
    print(f"|G1|={len(G1)} |G2|={len(G2)} prefix-equal starts={len(other)} (expected {len(G2) - 1})")
    if len(other) != len(G2) - 1: problems.append("prefix-equal start count differs from |G2|-1")
    if other and any(u < 0 for u in other): problems.append("negative non-block unit")
    # --- lex clauses semantic test
    first_lex = min(other) if other else nvars + 1
    lex = [c for c in clauses if any(abs(l) >= first_lex for l in c)]
    print("lex clauses:", len(lex))
    free = [t for t in triples if 0 not in t and 1 not in t]
    fixed_true = set(exp_true)
    def vec(blocks): return tuple(int(t in blocks) for t in triples)
    random.seed(a.seed)
    ok = bad = 0
    if len(G2) > 1:
        s = Cadical153(bootstrap_with=lex)
        t0 = time.time()
        for trial in range(a.trials):
            k = random.choice([5, 10, 15, 20, 25])
            blocks = set(random.sample(free, k)) | fixed_true
            orb = [frozenset(E.apply_to_triple(g, t) for t in blocks) for g in G2]
            vecs = sorted((vec(o), o) for o in orb)
            mn = vecs[0][1]
            r_min = s.solve(assumptions=[blockvar[t] if t in mn else -blockvar[t] for t in triples])
            nonmin = [o for (x, o) in vecs if x != vecs[0][0]]
            r_non = None
            if nonmin:
                o = random.choice(nonmin)
                r_non = s.solve(assumptions=[blockvar[t] if t in o else -blockvar[t] for t in triples])
            good = bool(r_min) and (r_non is False or r_non is None)
            ok += good; bad += (not good)
            if not good: print("FAIL trial", trial, r_min, r_non)
        s.delete()
        print(f"lex trials ok={ok} bad={bad} [{time.time() - t0:.1f}s]")
        if bad or ok == 0: problems.append("lex-leader semantic test failed")
    else:
        if lex: problems.append("lex clauses present although G2 is trivial")
    print("PROBLEMS:", problems if problems else "none")
    print("CNFCHECK", "PASS" if not problems else "FAIL", f"cube={a.cube} file={a.cnf}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
