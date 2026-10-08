#!/usr/bin/env python3
"""B10 positive control of filter/udrhombus: GP-10's 32,653 embedded 2-connected 10-vertex graphs.

Source: research/gp-10/runs/B10-final-2026-09-25 (README: the checker's ACCEPT over every graph of
research/gp-10/data/B10.g6; its records are research/gp-10/cloud/lean3/records.jsonl.gz, sha256 pinned
in the README's inputs.sha256). A record is "embedded" with an exact certificate (a number field
Q(alpha), alpha the root of an integer polynomial in a rational interval, and coordinates in Q(alpha))
or a "super" pointer (the graph maps injectively and edge-preservingly into another embedded graph,
whose embedding it inherits), or "refuted".

PASS iff
  B1 the records are exactly the graphs of data/B10.g6, 32,653 of them embedded, and the records'
     sha256 is the one pinned in inputs.sha256;
  B2 udrhombus refutes NONE of the embedded graphs (a collision is impossible in a unit-distance graph);
  B3 for EVERY tu verdict on an embedded graph, the forced pair is at unit distance in that graph's
     GP-10 embedding, and more: f(a) - f(b) = f(p) - f(q) (the identity the certificate proves),
     both to within 1e-40 with the coordinates evaluated at 80 significant digits (alpha refined by
     bisection to the same precision). As a check on the evaluation itself, every EDGE of the graph
     must come out at unit length to within 1e-40 and the points must be pairwise distinct;
  B4 every certificate written for these graphs is accepted by the dev replay, and the prover reports
     no certificate failure.
Also reported (information): the verdicts on GP-10's 509 refuted graphs.

usage: b10.py [--udrhombus PATH]      needs mpmath (pyenv-gp10)
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import mpmath

from rhlib import REPO, UDRHOMBUS, decode_g6, g6_lines, log, replay, run_prover

GP10 = REPO / "research" / "gp-10"
RECORDS = GP10 / "cloud" / "lean3" / "records.jsonl.gz"
PINS = GP10 / "runs" / "B10-final-2026-09-25" / "inputs.sha256"
B10 = GP10 / "data" / "B10.g6"
DPS = 80
TOL = mpmath.mpf(10) ** -40


def records():
    with gzip.open(RECORDS, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def evaluate_exact(cert: dict) -> list[tuple]:
    """Coordinates of an exact certificate, at DPS digits: alpha by bisection in the interval."""
    poly = [int(c) for c in cert["field"]["minpoly"]]
    lo, hi = (Fraction(x) for x in cert["field"]["interval"])
    mpmath.mp.dps = DPS

    def peval(x):
        acc = mpmath.mpf(0)
        for c in reversed(poly):
            acc = acc * x + c
        return acc
    a, b = mpmath.mpf(lo.numerator) / lo.denominator, mpmath.mpf(hi.numerator) / hi.denominator
    fa = peval(a)
    if fa * peval(b) >= 0:
        raise ValueError("no sign change on the interval")
    for _ in range(DPS * 4):
        mid = (a + b) / 2
        fm = peval(mid)
        if fm == 0:
            a = b = mid
            break
        if (fm > 0) == (fa > 0):
            a, fa = mid, fm
        else:
            b = mid
    alpha = (a + b) / 2

    def value(coeffs):
        acc = mpmath.mpf(0)
        for c in reversed(coeffs):
            q = Fraction(c)
            acc = acc * alpha + mpmath.mpf(q.numerator) / q.denominator
        return acc
    return [(value(x), value(y)) for x, y in cert["coords"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--udrhombus", type=Path, default=UDRHOMBUS)
    a = ap.parse_args()
    problems: list[str] = []
    t0 = time.monotonic()
    # B1 (the pin: inputs.sha256 names records.jsonl, the uncompressed stream)
    pinned = {line.split()[1]: line.split()[0] for line in PINS.read_text().splitlines() if line.strip()}
    digest = hashlib.sha256()
    with gzip.open(RECORDS, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    pin_ok = digest.hexdigest() == pinned.get("records.jsonl")
    embedded: list[str] = []
    refuted: list[str] = []
    pointer: dict[str, tuple[str, list[int]]] = {}
    kinds = collections.Counter()
    for r in records():
        kinds[(r["verdict"], r.get("cert", {}).get("type"))] += 1
        if r["verdict"] == "embedded":
            embedded.append(r["g6"])
            if r["cert"]["type"] == "super":
                pointer[r["g6"]] = (r["cert"]["g6"], r["cert"]["map"])
        elif r["verdict"] == "refuted":
            refuted.append(r["g6"])
    b10 = g6_lines(B10)
    same = sorted(b10) == sorted(embedded + refuted) and len(set(b10)) == len(b10)
    log(f"B1 records sha256 {'= pinned' if pin_ok else 'DIFFERS from the pin'}; {len(embedded)} embedded, "
        f"{len(refuted)} refuted; kinds {dict(kinds)}; the records are exactly data/B10.g6 ({len(b10)}): {same}")
    if not pin_ok or not same or len(embedded) != 32653:
        problems.append("B1: the B10 records are not the pinned 32,653 embedded graphs of B10.g6")

    # B2, B4
    recs, stats, _ = run_prover(embedded, a.udrhombus)
    verdicts = collections.Counter(r["verdict"] for r in recs)
    log(f"B2 udrhombus on the {len(embedded)} embedded graphs: {dict(verdicts)}; statistics {json.dumps(stats)}")
    if verdicts["refuted"]:
        problems.append(f"B2: {verdicts['refuted']} embedded graphs refuted")
        for code, r in zip(embedded, recs):
            if r["verdict"] == "refuted":
                log(f"  REFUTED {code}: {json.dumps(r)}")
    rejected = [(code, why) for code, r in zip(embedded, recs) if r["verdict"] != "pass"
                for ok, why in [replay(code, r)] if not ok]
    log(f"B4 dev replay of the {verdicts['tu'] + verdicts['refuted']} certificates: {len(rejected)} rejected; "
        f"certificate failures {stats.get('certificate_failures')}")
    if rejected or stats.get("certificate_failures"):
        problems.append(f"B4: {len(rejected)} certificates rejected, {stats.get('certificate_failures')} failures")
        for code, why in rejected[:10]:
            log(f"  REJECTED {code}: {why}")

    # B3: resolve every tu graph's pointer chain to an exact record, then evaluate
    tu = [(code, r["witness"]["rhombus"]) for code, r in zip(embedded, recs) if r["verdict"] == "tu"]
    chain: dict[str, tuple[str, list[int]]] = {}
    for code, _ in tu:
        g, m = code, list(range(10))
        steps = 0
        while g in pointer and steps < 64:
            target, mp = pointer[g]
            m = [mp[v] for v in m]      # vertex v of code -> vertex m[v] of the current target
            g = target
            steps += 1
        chain[code] = (g, m)
    needed = {g for g, _ in chain.values()}
    coords: dict[str, list[tuple]] = {}
    for r in records():
        if r["g6"] in needed and r["verdict"] == "embedded" and r["cert"]["type"] == "exact":
            coords[r["g6"]] = evaluate_exact(r["cert"])
    missing = needed - set(coords)
    if missing:
        problems.append(f"B3: {len(missing)} pointer targets without an exact embedding")
    mpmath.mp.dps = DPS
    worst = {"pair": mpmath.mpf(0), "identity": mpmath.mpf(0), "edge": mpmath.mpf(0)}
    closest = mpmath.mpf(10)
    bad: list[str] = []
    for code, rh in tu:
        target, m = chain[code]
        if target not in coords:
            continue
        pts = [coords[target][m[v]] for v in range(10)]
        n, edges = decode_g6(code)

        def d2(u, v):
            return (pts[u][0] - pts[v][0]) ** 2 + (pts[u][1] - pts[v][1]) ** 2
        edge_err = max(abs(d2(u, v) - 1) for u, v in edges)
        close = min(mpmath.sqrt(d2(u, v)) for u in range(n) for v in range(u + 1, n))
        (x, y), (p, q) = rh["pair"], rh["edge"]
        pair_err = abs(d2(x, y) - 1)
        ident = max(abs((pts[x][i] - pts[y][i]) - (pts[p][i] - pts[q][i])) for i in (0, 1))
        worst["pair"] = max(worst["pair"], pair_err)
        worst["identity"] = max(worst["identity"], ident)
        worst["edge"] = max(worst["edge"], edge_err)
        closest = min(closest, close)
        if pair_err > TOL or ident > TOL or edge_err > TOL or close < TOL:
            bad.append(f"{code}: pair {rh['pair']} |d^2-1| {mpmath.nstr(pair_err, 5)}, identity "
                       f"{mpmath.nstr(ident, 5)}, worst edge {mpmath.nstr(edge_err, 5)}, closest {mpmath.nstr(close, 5)}")
    log(f"B3 {len(tu)} tu verdicts; {len(needed)} exact embeddings evaluated at {DPS} digits; "
        f"forced pair at unit distance and f(a)-f(b) = f(p)-f(q) for {len(tu) - len(bad) - len(missing)}; "
        f"worst |d(a,b)^2 - 1| {mpmath.nstr(worst['pair'], 3)}, worst identity {mpmath.nstr(worst['identity'], 3)}, "
        f"worst edge |d^2 - 1| {mpmath.nstr(worst['edge'], 3)}, closest pair of points {mpmath.nstr(closest, 6)}")
    for line in bad[:20]:
        log("  BAD", line)
    if bad:
        problems.append(f"B3: {len(bad)} tu verdicts not confirmed by the embedding")

    # information: GP-10's refuted graphs
    rrecs, rstats, _ = run_prover(refuted, a.udrhombus)
    rv = collections.Counter(r["verdict"] for r in rrecs)
    rrej = sum(1 for code, r in zip(refuted, rrecs) if r["verdict"] != "pass" and not replay(code, r)[0])
    log(f"info: the {len(refuted)} refuted graphs of B10: {dict(rv)}; certificates rejected by the dev replay {rrej}")
    if rrej:
        problems.append(f"B4: {rrej} certificates on the refuted graphs rejected")

    for p in problems:
        log("PROBLEM:", p)
    log(f"B10 {'PASS' if not problems else 'FAIL (' + str(len(problems)) + ')'} ({time.monotonic() - t0:.0f} s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
