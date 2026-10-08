#!/usr/bin/env python3
"""Unit tests of filter/udrhombus (research/unit-distance-23/RHOMBUS-SPEC.md). Standard library only.

PASS iff every line below holds.
  U1 K2,3 is refuted (a collision), and the dev replay accepts the certificate.
  U2 each of the six TU gadgets of data/tu-gadgets.json is tu in the default mode, and --pair with the
     gadget's own distinguished pair certifies exactly that pair; the dev replay accepts all twelve.
  U3 the Moser spindle, the unit rhombus (C4) and the wheel W6 pass.
  U4 AMP's 56 known densest graphs (sources/amp/anc/graph6.txt) ALL pass: each is the full
     unit-distance graph of its point set, so no collision and no forced unit distance on a non-edge
     exists; a single flag is a bug.
  U5 the prover is deterministic (two runs over all the inputs above give the same bytes) and its
     statistics line reports no certificate failure.
  U6 red controls on the replay: tampered certificates (a coefficient, the scale, a cycle vertex, a
     float and a boolean coefficient, an extra key, an adjacent pair, a non-edge "edge", a repeated
     vertex, the pair reversed, the edge reversed, an empty cycle list) are each rejected.
  U7 bad input is refused with exit status 2 (a blank line, a 33-vertex graph, nonzero padding, a
     graph6 header, a character outside the alphabet).

usage: units.py [--udrhombus PATH] [--print-gadget-certificates]
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

from rhlib import UDRHOMBUS, encode_g6, gadgets, known_graphs, log, replay, run_prover

problems: list[str] = []


def expect(cond: bool, message: str) -> None:
    if not cond:
        problems.append(message)
        log("  FAIL:", message)


K23 = encode_g6(5, [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)])
C4 = encode_g6(4, [(0, 1), (1, 2), (2, 3), (3, 0)])
MOSER = encode_g6(7, [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (0, 4), (0, 5), (4, 5), (4, 6), (5, 6), (3, 6)])
W6 = encode_g6(7, [(6, i) for i in range(6)] + [(i, (i + 1) % 6) for i in range(6)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--udrhombus", type=Path, default=UDRHOMBUS)
    ap.add_argument("--print-gadget-certificates", action="store_true")
    a = ap.parse_args()
    binary = a.udrhombus.resolve()
    all_inputs: list[str] = []

    # U1
    (r,), stats, _ = run_prover([K23], binary)
    ok, why = replay(K23, r)
    log(f"U1 K2,3 {K23}: {json.dumps(r, separators=(',', ':'))}; replay {'accepts' if ok else 'REJECTS: ' + why}")
    expect(r["verdict"] == "refuted" and ok, "U1: K2,3 is not refuted with a valid certificate")
    all_inputs.append(K23)

    # U2
    for i, gd in enumerate(gadgets()):
        code = encode_g6(gd["n"], gd["edges"])
        all_inputs.append(code)
        (d,), _, _ = run_prover([code], binary)
        a_, b_ = sorted(gd["pair"])
        (p,), _, _ = run_prover([code], binary, ["--pair", str(a_), str(b_)])
        ok_d, why_d = replay(code, d)
        ok_p, why_p = replay(code, p)
        own = d.get("verdict") == "tu" and d["witness"]["rhombus"]["pair"] == [a_, b_]
        log(f"U2 gadget {i} ({gd['n']} vertices, {gd['m']} edges, pair {gd['pair']}): default {d['verdict']}"
            f"{' pair ' + str(d['witness']['rhombus']['pair']) if d['verdict'] != 'pass' else ''}"
            f" ({'its own pair' if own else 'another pair first'}), replay {'ok' if ok_d else why_d}; "
            f"--pair {a_} {b_}: {p['verdict']}, replay {'ok' if ok_p else why_p}")
        expect(d["verdict"] == "tu" and ok_d, f"U2: gadget {i} is not tu with a valid certificate")
        expect(p["verdict"] == "tu" and p["witness"]["rhombus"]["pair"] == [a_, b_] and ok_p,
               f"U2: gadget {i}'s distinguished pair {gd['pair']} is not certified by --pair")
        if a.print_gadget_certificates:
            print("CERT", i, code, json.dumps(p["witness"]["rhombus"], separators=(",", ":")))

    # U3
    for name, code in (("Moser spindle", MOSER), ("unit rhombus C4", C4), ("wheel W6", W6)):
        (r,), _, _ = run_prover([code], binary)
        log(f"U3 {name} {code}: {r['verdict']}")
        expect(r["verdict"] == "pass", f"U3: {name} is not pass")
        all_inputs.append(code)

    # U4
    known = known_graphs()
    recs, stats, _ = run_prover(known, binary)
    flagged = [(code, rec) for code, rec in zip(known, recs) if rec["verdict"] != "pass"]
    log(f"U4 AMP's {len(known)} known graphs: {len(known) - len(flagged)} pass, {len(flagged)} flagged "
        f"(4-cycles listed {stats.get('cycles')}, largest rank {stats.get('max_rank')})")
    for code, rec in flagged:
        log(f"  FLAGGED {code}: {json.dumps(rec)}")
    expect(len(known) == 56 and not flagged, "U4: a known densest graph is flagged")
    all_inputs += known

    # U5
    _, stats1, raw1 = run_prover(all_inputs, binary)
    _, stats2, raw2 = run_prover(all_inputs, binary)
    log(f"U5 {len(all_inputs)} inputs twice: identical output {raw1 == raw2}; stats {json.dumps(stats1)}")
    expect(raw1 == raw2, "U5: the prover is not deterministic")
    expect(stats1.get("certificate_failures") == 0, "U5: certificate failures reported")

    # U6
    (k,), _, _ = run_prover([K23], binary)
    g0 = gadgets()[0]
    g0code = encode_g6(g0["n"], g0["edges"])
    (t,), _, _ = run_prover([g0code], binary, ["--pair", *map(str, sorted(g0["pair"]))])
    tu_edges = {tuple(sorted(e)) for e in g0["edges"]}

    def tamper(code, rec, name, fn):
        bad = copy.deepcopy(rec)
        fn(bad["witness"]["rhombus"], bad)
        ok, why = replay(code, bad)
        log(f"U6 red {name}: {'ACCEPTED (bug)' if ok else 'rejected: ' + why[:110]}")
        expect(not ok, f"U6: the replay accepted a tampered certificate ({name})")

    def non_neighbour_swap(rh, _):
        c = rh["cycles"][0]
        c[3] = next(v for v in range(5) if v not in c)
    tamper(K23, k, "K2,3 coefficient + 1", lambda rh, _: rh["coefficients"].__setitem__(0, rh["coefficients"][0] + 1))
    tamper(K23, k, "K2,3 scale * 2", lambda rh, _: rh.__setitem__("scale", rh["scale"] * 2))
    tamper(K23, k, "K2,3 scale 0", lambda rh, _: rh.__setitem__("scale", 0))
    tamper(K23, k, "K2,3 cycle vertex replaced", non_neighbour_swap)
    tamper(K23, k, "K2,3 float coefficient", lambda rh, _: rh["coefficients"].__setitem__(0, float(rh["coefficients"][0])))
    tamper(K23, k, "K2,3 boolean coefficient", lambda rh, _: rh["coefficients"].__setitem__(1, True))
    tamper(K23, k, "K2,3 extra key", lambda rh, _: rh.__setitem__("note", 1))
    tamper(K23, k, "K2,3 pair reversed", lambda rh, _: rh.__setitem__("pair", rh["pair"][::-1]))
    tamper(K23, k, "K2,3 empty cycle list", lambda rh, _: (rh.__setitem__("cycles", []), rh.__setitem__("coefficients", [])))
    tamper(K23, k, "K2,3 repeated vertex", lambda rh, _: rh["cycles"][0].__setitem__(2, rh["cycles"][0][0]))
    tamper(K23, k, "K2,3 verdict tu without edge", lambda rh, rec: rec.__setitem__("verdict", "tu"))
    tamper(g0code, t, "gadget 0 edge reversed", lambda rh, _: rh.__setitem__("edge", rh["edge"][::-1]))
    tamper(g0code, t, "gadget 0 pair made an edge", lambda rh, _: rh.__setitem__(
        "pair", list(next(e for e in sorted(tu_edges)))))
    tamper(g0code, t, "gadget 0 edge made a non-edge", lambda rh, _: rh.__setitem__(
        "edge", list(next((u, v) for u in range(6) for v in range(u + 1, 6) if (u, v) not in tu_edges))))
    tamper(g0code, t, "gadget 0 edge key dropped", lambda rh, _: rh.pop("edge"))
    tamper(g0code, t, "gadget 0 verdict refuted", lambda rh, rec: rec.__setitem__("verdict", "refuted"))

    # U7
    for name, data in (("blank line", b"\n"), ("33 vertices", encode_g6(33, [(0, 1)]).encode() + b"\n"),
                       ("nonzero padding", b"Bx\n"),   # 'x' = 111001: the triangle plus a padding bit
                       ("graph6 header", b">>graph6<<Bw\n"), ("bad character", b"C~ \n")):
        p = subprocess.run([str(binary)], input=data, capture_output=True)
        log(f"U7 {name} {data!r}: exit {p.returncode}: {p.stderr.decode().strip()[:80]}")
        expect(p.returncode == 2, f"U7: {name} was not refused with exit 2")

    for x in problems:
        log("PROBLEM:", x)
    log("UNITS", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
