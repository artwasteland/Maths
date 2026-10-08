#!/usr/bin/env python3
"""(b) Semantics: forbidden set 398 = forbidden set 74 minus exactly the graphs containing one of the 324.

For a cell with parent file P74 and production output C74 (byte-identical to the new binary in
set 74, see regress-74.py):

  R(X)  = the records of X that contain one of the 398 as a (not necessarily induced) subgraph,
          decided by an independent matcher (GP-10's matcher.c widened to 31-vertex hosts,
          matcher32.c, chained over chunks of at most 128 patterns of data/forbidden-398.g6);
  P398  = P74 minus R(P74), in order: the 398 tree's parent file for this cell;
  E     = C74 minus R(C74), in order: the expected set-398 output;
  C398  = udenum --forbidden-set 398 on P398.

PASS for the cell iff C398 == E as byte strings (same records, same order), hence as sets and
counts.  Why equality and not inclusion: a graph's canonical parent is an induced subgraph and
398-freeness is hereditary, so the set-398 tree is exactly the set-74 tree restricted to
398-free graphs; and the orbit representative udenum picks for a neighbourhood depends only on
Aut(parent) and a domain that is Aut(parent)-invariant in both sets, so even the order agrees.

THE WRONG CONTROL, which this script refuses to rely on: `set(C398) <= set(C74)`.  It passes
when set 398 drops valid graphs or writes nothing.  --red demonstrates that on this data:
  W1 an empty C398                           subset check PASSES, equality FAILS
  W2 C398 with one expected record dropped   subset check PASSES, equality FAILS
  W3 C398 from a generator without the 324   subset check PASSES, equality FAILS
     (the old binary, set 74, run on P398)
  W4 C398 from set 398 run on P74 unfiltered (children of 324-containing parents)
  W5a E computed by the matcher with the 74 only: the expected side must be sensitive too
  W5b E computed without a single 324-member (informational: a host may contain several)
  W6 udenum --forbidden-set 398 --verify-parents on P74 must refuse (a parent contains a 324)

Independent evidence for the matcher itself: every positive's witness (pattern index and map)
is re-verified here in pure Python against data/forbidden-398.g6 (injective, edge-preserving);
the NEW udfilter in set 398 (a third implementation, a different search) must call exactly the
same hosts "forbidden" on every record of P74 and C74, and its witnesses are re-verified
against data/forbidden-398.json; random claimed-free graphs of E are re-decided with networkx
VF2 against all 398 within a time budget per cell; matcher hits on the first 74 must be zero
(P74 and C74 are 74-free).
"""
from __future__ import annotations

import argparse
import json
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

from t398lib import (ENUM, F398, F398_G6, F398_G6_SHA256, F398_SHA256, MATCHER32, NEW_UDENUM,
                     NEW_UDFILTER, OLD_UDENUM, SCRATCH, TU, decode_g6, g6_lines, run_matcher, run_udenum,
                     sha256, witness_ok, write_lines)

OUT22 = ENUM / "out-22" / "dag-22-61"
SUP = ENUM / "out-sup" / "dag-18-46"


def cells(slices: Path | None) -> list[dict]:
    out = []
    for d, names in ((OUT22, ["11-19", "11-20", "11-21", "11-22", "11-23",
                              "12-23", "12-24", "12-25", "12-26", "12-27"]),
                     (SUP, ["15-34", "15-35", "15-36", "15-37", "16-38", "16-39", "16-40", "16-41",
                            "17-42", "17-43", "18-46"])):
        for name in names:
            n, m = map(int, name.split("-"))
            out.append({"cell": f"{d.name}/{name}", "parents": d / "_parents" / f"{name}.g6",
                        "c74": d / f"{name}.g6", "n": n, "m": m})
    if slices is not None:
        # the 48 slices of the final cell are one cell: their union (each graph has one parent)
        out.append({"cell": "u22-all-48-slices/22-61", "slices": slices, "n": 22, "m": 61})
    return out


def materialise(c: dict, work: Path) -> None:
    if "slices" not in c:
        return
    parents, children = [], []
    for s in range(48):
        parents += g6_lines(c["slices"] / f"s{s}of48" / "21-56.keep.g6")
        children += g6_lines(c["slices"] / f"s{s}of48" / "22-61.g6")
    c["parents"] = work / "u22-final.parents.g6"
    c["c74"] = work / "u22-final.c74.g6"
    write_lines(c["parents"], parents)
    write_lines(c["c74"], children)


def verify_positives(removed: dict, patterns: list[bytes]) -> tuple[int, int]:
    """Return (verified, first-74 hits); raise on any bad witness."""
    pattern_edges = []
    for p in patterns:
        _, es = decode_g6(p)
        pattern_edges.append([tuple(sorted(e)) for e in es])
    hits74 = 0
    for host, (idx, mp) in removed.items():
        if not witness_ok(host, pattern_edges[idx], mp):
            raise SystemExit(f"matcher witness does not verify: {host.decode()} pattern {idx} map {mp}")
        hits74 += idx < 74
    return len(removed), hits74


class _HostTimeout(Exception):
    pass


def _alarm(signum, frame):  # noqa: ARG001
    raise _HostTimeout()


def networkx_negatives(hosts: list[bytes], patterns: list[bytes], budget: float, per_host: int,
                       rng: random.Random) -> dict:
    """Re-decide random claimed negatives with networkx VF2 against all 398, until `budget`
    seconds are spent.  VF2 needs about a minute per 12-vertex negative and far longer on larger
    hosts, so each host gets at most `per_host` seconds (SIGALRM): a host not finished in time is
    recorded as undecided, never as checked."""
    import networkx as nx
    from networkx.algorithms import isomorphism as iso
    order = list(hosts)
    rng.shuffle(order)
    pats = [nx.from_graph6_bytes(p) for p in patterns]
    pdeg = [sorted((d for _, d in g.degree()), reverse=True) for g in pats]
    t0 = time.monotonic()
    bad, checked, undecided = [], 0, 0
    old = signal.signal(signal.SIGALRM, _alarm)
    try:
        for h in order:
            if time.monotonic() - t0 > budget:
                break
            g = nx.from_graph6_bytes(h)
            hdeg = sorted((d for _, d in g.degree()), reverse=True)
            signal.alarm(per_host)
            try:
                for i, p in enumerate(pats):
                    if p.number_of_nodes() > g.number_of_nodes() or p.number_of_edges() > g.number_of_edges():
                        continue
                    if any(x > y for x, y in zip(pdeg[i], hdeg)):
                        continue
                    if iso.GraphMatcher(g, p).subgraph_is_monomorphic():
                        bad.append((h.decode(), i))
                        break
                checked += 1
            except _HostTimeout:
                undecided += 1
            finally:
                signal.alarm(0)
    finally:
        signal.signal(signal.SIGALRM, old)
    return {"checked": checked, "undecided_timeouts": undecided, "networkx_found_containment": bad,
            "seconds": round(time.monotonic() - t0, 1)}


def udfilter_forbidden(hosts_file: Path, work: Path, tag: str) -> dict[bytes, tuple[int, list[int]]]:
    """Hosts that the NEW udfilter in set 398 calls "forbidden", with their witnesses (JSON labelling)."""
    out = work / f"{tag}.udfilter398.jsonl"
    with open(hosts_file, "rb") as stdin, open(out, "wb") as stdout:
        p = subprocess.run(["nice", "-n", "10", str(NEW_UDFILTER), "-s", "398", "-f", str(F398), "-t", str(TU)],
                           stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit(f"udfilter failed: {p.stderr.decode()}")
    res = {}
    for line in out.read_bytes().split(b"\n"):
        if line:
            r = json.loads(line)
            if r["verdict"] == "forbidden":
                res[r["g6"].encode()] = (r["witness"]["index"], r["witness"]["map"])
    return res


def run_cell(c: dict, work: Path, nx_budget: float, nx_per_host: int, rng: random.Random, log) -> dict:
    tag = c["cell"].replace("/", "_")
    materialise(c, work)
    patterns = g6_lines(F398_G6)
    json_edges = json.loads(F398.read_text())
    p74, c74 = g6_lines(c["parents"]), g6_lines(c["c74"])
    t0 = time.monotonic()
    mp = run_matcher(MATCHER32, F398_G6, c["parents"], work / f"{tag}-mp")
    mc = run_matcher(MATCHER32, F398_G6, c["c74"], work / f"{tag}-mc")
    t_match = time.monotonic() - t0
    vp, hp74 = verify_positives(mp["removed"], patterns)
    vc, hc74 = verify_positives(mc["removed"], patterns)
    # second, independent decision of the same question: udfilter in set 398 on every host
    up = udfilter_forbidden(c["parents"], work, f"{tag}-p")
    uc = udfilter_forbidden(c["c74"], work, f"{tag}-c")
    udf_agree = set(up) == set(mp["removed"]) and set(uc) == set(mc["removed"])
    for host, (idx, mpx) in list(up.items()) + list(uc.items()):
        if not witness_ok(host, json_edges[idx], mpx):
            raise SystemExit(f"udfilter witness does not verify: {host.decode()} index {idx} map {mpx}")
    p398 = [x for x in p74 if x not in mp["removed"]]
    expected = [x for x in c74 if x not in mc["removed"]]
    if p398 != mp["survivors"] or expected != mc["survivors"]:
        raise SystemExit("matcher survivors are not the input minus the removed hosts, in order")
    p398_file, e_file = work / f"{tag}.p398.g6", work / f"{tag}.expected.g6"
    write_lines(p398_file, p398)
    write_lines(e_file, expected)
    stats = run_udenum(NEW_UDENUM, p398_file, c["n"], c["m"], work / f"{tag}.c398.g6",
                       extra=["--forbidden-set", "398"], forbidden=F398)
    c398 = g6_lines(work / f"{tag}.c398.g6")
    verify = run_udenum(NEW_UDENUM, p398_file, c["n"], c["m"], work / f"{tag}.c398v.g6",
                        extra=["--forbidden-set", "398", "--verify-parents"], forbidden=F398)
    same_bytes = (work / f"{tag}.c398.g6").read_bytes() == e_file.read_bytes()
    same_verify = (work / f"{tag}.c398v.g6").read_bytes() == e_file.read_bytes()
    neg = networkx_negatives(expected if expected else mp["survivors"], patterns, nx_budget, nx_per_host, rng)
    rec = {"cell": c["cell"], "P74": len(p74), "P74_containing_398": len(mp["removed"]), "P398": len(p398),
           "C74": len(c74), "C74_containing_398": len(mc["removed"]), "expected": len(expected),
           "C398": len(c398), "equal_bytes": same_bytes, "equal_with_verify_parents": same_verify,
           "equal_sets": set(c398) == set(expected), "equal_counts": len(c398) == len(expected),
           "subset_check_would_say": set(c398) <= set(c74),
           "witnesses_verified": vp + vc, "matcher_hits_on_first_74": hp74 + hc74,
           "udfilter398_agrees_on_every_host": udf_agree, "udfilter398_witnesses_verified": len(up) + len(uc),
           "networkx_negatives": neg, "matcher_seconds": round(t_match, 2),
           "udenum_398_cpu_seconds": stats["cpu_seconds"]}
    rec["pass"] = (same_bytes and same_verify and rec["equal_sets"] and rec["equal_counts"] and udf_agree
                   and rec["matcher_hits_on_first_74"] == 0 and not neg["networkx_found_containment"])
    print(f"{c['cell']:28s} P74 {len(p74):6d} (398-hits {len(mp['removed']):6d}) P398 {len(p398):6d} | "
          f"C74 {len(c74):6d} (398-hits {len(mc['removed']):6d}) expected {len(expected):6d} "
          f"C398 {len(c398):6d} | {'EQUAL' if rec['pass'] else 'NOT EQUAL'} "
          f"(udfilter agrees {udf_agree}, nx negatives {neg['checked']} decided/{neg['undecided_timeouts']} "
          f"timed out, witnesses {vp + vc})", file=log, flush=True)
    c.update({"p398_file": p398_file, "e_file": e_file, "expected": expected, "c74_lines": c74,
              "p74_lines": p74, "removed_c": mc["removed"]})
    return rec


def red_controls(cs: list[dict], work: Path, log) -> list[dict]:
    reds = []
    c = max((x for x in cs if "expected" in x), key=lambda x: (len(x["expected"]) > 0 and
                                                               len(x["removed_c"]) > 0, len(x["expected"])))
    e = c["expected"]

    def judge(name, candidate: list[bytes], expected=e, c74=c["c74_lines"]):
        eq = candidate == expected
        sub = set(candidate) <= set(c74)
        reds.append({"control": name, "candidate_records": len(candidate), "expected_records": len(expected),
                     "equality_check": "PASS" if eq else "FAIL", "wrong_subset_check": "PASS" if sub else "FAIL",
                     "went_red": not eq})
    judge(f"W1 empty set-398 output ({c['cell']})", [])
    judge(f"W2 one expected record dropped ({c['cell']})", e[:-1])
    old = run_udenum(OLD_UDENUM, c["p398_file"], c["n"], c["m"], work / "w3.g6")
    judge(f"W3 generator without the 324: old binary (set 74) on P398 ({c['cell']})", g6_lines(work / "w3.g6"))
    run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / "w4.g6", extra=["--forbidden-set", "398"],
               forbidden=F398)
    judge(f"W4 set 398 run on unfiltered P74 ({c['cell']})", g6_lines(work / "w4.g6"))
    # W5a: the expected side computed with the 74 only (all 324 dropped from the matcher)
    pats = g6_lines(F398_G6)
    c398_actual = g6_lines(work / f"{c['cell'].replace('/', '_')}.c398.g6")
    only74 = work / "w5a-patterns.g6"
    write_lines(only74, pats[:74])
    m5 = run_matcher(MATCHER32, only74, c["c74"], work / "w5a-m")
    judge(f"W5a expected side computed with the 74 only ({c['cell']})", c398_actual, expected=m5["survivors"])
    # W5b: drop ONE 324-member.  A host whose first match was that member may contain another,
    # so try the members that removed the most records until one changes E; informational.
    counts: dict[int, int] = {}
    for idx, _ in c["removed_c"].values():
        counts[idx] = counts.get(idx, 0) + 1
    for culprit in sorted((i for i in counts if i >= 74), key=lambda i: -counts[i])[:8]:
        reduced = work / f"w5b-{culprit}.g6"
        write_lines(reduced, pats[:culprit] + pats[culprit + 1:])
        m5b = run_matcher(MATCHER32, reduced, c["c74"], work / f"w5b-{culprit}-m")
        if m5b["survivors"] != e:
            judge(f"W5b expected side computed without the single member {culprit} ({c['cell']})",
                  c398_actual, expected=m5b["survivors"])
            break
    else:
        print("W5b: no single-member drop among the top 8 changed E (each such host contains "
              "another member); W5a stands as the matcher-side control", file=log)
    v = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / "w6.g6",
                   extra=["--forbidden-set", "398", "--verify-parents"], forbidden=F398, expect_ok=False)
    reds.append({"control": f"W6 --forbidden-set 398 --verify-parents on unfiltered P74 ({c['cell']})",
                 "returncode": v["returncode"], "stderr": v["stderr"], "went_red": v["returncode"] != 0})
    for r in reds:
        extra = (f"equality {r['equality_check']}, wrong subset check {r['wrong_subset_check']}, "
                 f"{r['candidate_records']} vs {r['expected_records']} expected"
                 if "equality_check" in r else f"exit {r['returncode']}: {r['stderr']}")
        print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {r['control']}: {extra}",
              file=log, flush=True)
    return reds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, default=None)
    ap.add_argument("--work", type=Path, default=SCRATCH / "semantics-398")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "semantics-398.json")
    ap.add_argument("--nx-seconds", type=float, default=60.0,
                    help="networkx VF2 budget per cell for re-deciding expected (claimed 398-free) graphs")
    ap.add_argument("--nx-per-host", type=int, default=90, help="networkx VF2 limit per host, seconds")
    ap.add_argument("--only", default=None, help="run only cells whose name contains this text")
    ap.add_argument("--red", action="store_true")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    log = sys.stdout
    for path, want in ((F398, F398_SHA256), (F398_G6, F398_G6_SHA256)):
        if sha256(path) != want:
            print(f"{path} does not have the pinned sha256")
            return 2
    print(f"new udenum {sha256(NEW_UDENUM)}; new udfilter {sha256(NEW_UDFILTER)}; matcher32 {sha256(MATCHER32)}; "
          f"forbidden-398.g6 {F398_G6_SHA256}", file=log)
    rng = random.Random(20260925)
    cs = [c for c in cells(a.slices) if a.only is None or a.only in c["cell"]]
    results = [run_cell(c, a.work, a.nx_seconds, a.nx_per_host, rng, log) for c in cs]
    reds = red_controls(cs, a.work, log) if a.red else []
    ok = all(r["pass"] for r in results) and all(r["went_red"] for r in reds)
    summary = {"cells": results, "red_controls": reds, "pass": ok,
               "cells_equal": sum(r["pass"] for r in results), "cells_total": len(results),
               "totals": {k: sum(r[k] for r in results) for k in
                          ("P74", "P74_containing_398", "P398", "C74", "C74_containing_398", "expected", "C398",
                           "witnesses_verified")},
               "networkx_negatives_checked": sum(r["networkx_negatives"]["checked"] for r in results),
               "networkx_negatives_timed_out": sum(r["networkx_negatives"]["undecided_timeouts"] for r in results)}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"cells equal: {summary['cells_equal']} of {summary['cells_total']}; totals {summary['totals']}; "
          f"networkx negatives {summary['networkx_negatives_checked']}; red controls "
          f"{sum(r['went_red'] for r in reds)} of {len(reds)} went red", file=log)
    print("RESULT:", "PASS" if ok else "FAIL", file=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
