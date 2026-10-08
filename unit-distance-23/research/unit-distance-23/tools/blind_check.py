#!/usr/bin/env python3
"""The blind second verifier over every top-level record, with red controls made afresh for each certificate.

usage: python blind_check.py [--records DIR] [--verifier FILE]

research/unit-distance-23/blind-verifier/verify_tree.py (README.md there: written from the format and the mathematics
alone, sharing no code with udcheck.py) is run on each record of each slice under results/u23/top-level/s*of*/: the
target cell's graph file and certificates file, one record per kept graph, matched by the record's g6. Every record
must give ACCEPT with exit 0. Then seven tampered copies of each record must each give REJECT <reason> with exit 1
(a crash does not count as a rejection):
  (a) one entry of the root's A changed, (b) one child subtree of the root removed, (c) the root move's first
  coefficient changed, (d) the graph with the root move's first edge removed (the certificate unchanged), (e) the field's
  interval moved off its root, (f) the last L3 split's d changed, (g) the first L1b leaf's omega changed.
A control the certificate cannot express (no L3 split, no L1b leaf) is reported and skipped, not counted.
Last line: BLIND-CHECK OK|FAIL: A of N top-level certificates accepted by the blind verifier (verify_tree.py sha256 S);
R of T tampered inputs rejected. Exit 0 only on OK.
"""
import argparse, copy, hashlib, json, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
RECORDS = REPO / "research/unit-distance-23/results/u23/top-level"
VERIFIER = REPO / "research/unit-distance-23/blind-verifier/verify_tree.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(verifier: Path, g6: Path, cert: Path) -> tuple:
    r = subprocess.run([sys.executable, str(verifier), str(g6), str(cert)], capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1], r.stderr.strip()


def g6_edges(s: str) -> tuple:
    """(n, edges) of a graph6 string with n <= 62."""
    b = [ord(c) - 63 for c in s.strip()]
    n, bits = b[0], [(x >> (5 - k)) & 1 for x in b[1:] for k in range(6)]
    edges, i = [], 0
    for v in range(1, n):
        for u in range(v):
            if bits[i]:
                edges.append((u, v))
            i += 1
    return n, edges


def g6_encode(n: int, edges: list) -> str:
    es = {tuple(sorted(e)) for e in edges}
    bits = [1 if (u, v) in es else 0 for v in range(1, n) for u in range(v)]
    bits += [0] * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2)) for k in range(0, len(bits), 6))


def nodes(n: dict, path: str = "root"):
    yield path, n
    for j, c in enumerate(n.get("children") or []):
        yield from nodes(c, f"{path}.children[{j}]")


def bump(x):
    """A field or rational entry changed: its first nonzero coefficient plus one (a bare rational, plus one)."""
    if isinstance(x, list):
        y = list(x)
        k = next((j for j, v in enumerate(y) if Fraction(str(v)) != 0), 0)
        y[k] = str(Fraction(str(y[k])) + 1)
        return y
    return str(Fraction(str(x)) + 1)


def controls(rec: dict, g6: str) -> list:
    """[(name, graph6, record or None if inexpressible)] for the seven tamperings."""
    out, w = [], rec["witness"]
    r = copy.deepcopy(rec)
    r["witness"]["tree"]["A"][0][0] = bump(r["witness"]["tree"]["A"][0][0])
    out.append(("(a) one entry of the root's A changed", g6, r))
    r = copy.deepcopy(rec)
    ch = r["witness"]["tree"].get("children") or []
    if ch:
        ch.pop()
    out.append(("(b) one child subtree of the root removed", g6, r if rec["witness"]["tree"].get("children") else None))
    r = copy.deepcopy(rec)
    mv = r["witness"]["tree"].get("move") or {}
    if mv.get("coefficients"):
        mv["coefficients"][0] = bump(mv["coefficients"][0])
    out.append(("(c) the root move's first coefficient changed", g6, r if mv.get("coefficients") else None))
    n, edges = g6_edges(g6)
    e0 = tuple(sorted((w["tree"].get("move") or {}).get("edges", [[None, None]])[0]))
    out.append(("(d) the graph with the root move's first edge removed", g6_encode(n, [e for e in edges if e != e0]),
                rec if e0 in set(edges) else None))
    r = copy.deepcopy(rec)
    lo, hi = (Fraction(str(x)) for x in r["witness"]["field"]["interval"])
    r["witness"]["field"]["interval"] = [str(hi + 1), str(hi + 2)]   # beyond the isolated root, the only one inside
    out.append(("(e) the field's interval moved off its root", g6, r))
    r = copy.deepcopy(rec)
    l3 = [n_ for _, n_ in nodes(r["witness"]["tree"]) if (n_.get("move") or {}).get("kind") == "L3"]
    if l3:
        l3[-1]["move"]["d"] = bump(l3[-1]["move"]["d"])
    out.append(("(f) the last L3 split's d changed", g6, r if l3 else None))
    r = copy.deepcopy(rec)
    l1b = [n_ for _, n_ in nodes(r["witness"]["tree"]) if (n_.get("move") or {}).get("kind") == "L1b"]
    if l1b:
        om = l1b[0]["move"]["omega"]
        om["re"] = bump(om["re"])
    out.append(("(g) the first L1b leaf's omega changed", g6, r if l1b else None))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--verifier", type=Path, default=VERIFIER)
    a = ap.parse_args()
    vsha = hashlib.sha256(a.verifier.read_bytes()).hexdigest()
    print(f"verifier: {a.verifier.relative_to(REPO) if a.verifier.is_relative_to(REPO) else a.verifier} sha256 {vsha}")
    accepted = total = rejected = tried = 0
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for d in sorted(a.records.glob("s*of*")):
            gfiles = sorted(d.glob("*.g6"))
            for gf in gfiles:
                cf = gf.with_name(gf.name[:-len(".g6")] + ".certs.jsonl")
                graphs = [x for x in gf.read_text().splitlines() if x.strip()]
                recs = [json.loads(x) for x in cf.read_text().splitlines() if x.strip()] if cf.exists() else []
                for k, g6 in enumerate(graphs):
                    total += 1
                    rec = next((r for r in recs if r.get("g6") == g6), None)
                    name = f"{d.name}/{gf.name} graph {k}"
                    if rec is None:
                        problems.append(f"{name}: no certificate record with its g6")
                        print(f"{name}: NO RECORD")
                        continue
                    pg, pc = tmp / f"{d.name}-{k}.g6", tmp / f"{d.name}-{k}.jsonl"
                    pg.write_text(g6 + "\n")
                    pc.write_text(json.dumps(rec) + "\n")
                    code, last, err = run(a.verifier, pg, pc)
                    ok = code == 0 and last == "ACCEPT"
                    accepted += ok
                    print(f"{name} {g6} certs {sha(cf)}: {last} (exit {code})" + (f"; stderr {err[:200]}" if err else ""))
                    if not ok:
                        problems.append(f"{name}: the blind verifier did not accept: {last} (exit {code})")
                    for cname, cg6, crec in controls(rec, g6):
                        if crec is None:
                            print(f"  {cname}: not expressible in this certificate, skipped")
                            continue
                        tried += 1
                        qg, qc = tmp / "c.g6", tmp / "c.jsonl"
                        qg.write_text(cg6 + "\n")
                        qc.write_text(json.dumps(crec) + "\n")
                        c2, l2, e2 = run(a.verifier, qg, qc)
                        red = c2 == 1 and l2.startswith("REJECT ") and "Traceback" not in e2
                        rejected += red
                        print(f"  {cname}: {l2[:160]} (exit {c2})")
                        if not red:
                            problems.append(f"{name} control {cname}: not rejected with a reason: {l2[:120]} "
                                            f"(exit {c2}){'; it crashed' if 'Traceback' in e2 else ''}")
    for p in problems:
        print("PROBLEM:", p)
    good = not problems and total > 0 and accepted == total and rejected == tried and tried > 0
    print(f"BLIND-CHECK {'OK' if good else 'FAIL'}: {accepted} of {total} top-level certificates accepted by the "
          f"blind verifier (verify_tree.py sha256 {vsha[:16]}); {rejected} of {tried} tampered inputs rejected")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
