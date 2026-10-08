#!/usr/bin/env python3
"""(c) Filter: udfilter in set 398 calls exactly GP-10's 509 refuted B10 graphs "forbidden".

Ground truth: research/gp-10/cloud/lean3/records.jsonl.gz, the checked record of every one of the
33,162 graphs of data/B10.g6 (32,653 "embedded", 509 "refuted", sha256s pinned below).

PASS iff
  F1 udfilter -s 398 writes one record per B10 graph, in order;
  F2 its "forbidden" set equals the 509 refuted graphs, and none of the 32,653 embedded graphs is
     called "forbidden" (they may be "tu" or "pass": a unit-distance graph can hold a gadget);
  F3 every forbidden witness verifies independently here (pure Python: the map is injective, in
     range and edge-preserving from data/forbidden-398.json[index] into the graph), its index is
     >= 74 (B10 is 74-free), and forbidden-398.json[index] is exactly L10.g6 line index-74;
  F4 GP-10's own matcher (unmodified matcher.c, 10-vertex hosts, chained over chunks of at most
     128 patterns of data/forbidden-398.g6) removes exactly the same 509 graphs, and its witnesses
     verify against data/forbidden-398.g6;
  F5 set 74: the new udfilter (no flag, and -s 74) and the old udfilter write byte-identical output
     on all of B10, with no "forbidden" verdict (B10 is 74-free by construction).

Red controls (--red), each must turn a check red:
  X1 the old udfilter (the 74 only) in place of the set-398 run          -> F2
  X2 the set-398 output with one "forbidden" record turned into "pass"   -> F2
  X3 the set-398 output with one witness map made non-injective          -> F3
  X4 udfilter rebuilt with the pin moved to a forbidden-398 file in which member J (one of the
     324) is replaced by a copy of member J+1: graph L10[J] itself is in B10 and must turn "pass" -> F2
  X5 the matcher with member J dropped (--drop-index)                    -> F4
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from t398lib import (F398, F398_G6, F398_SHA256, F398_G6_SHA256, HERE, MATCHER10, NEW_UDFILTER, OLD_UDFILTER,
                     REPO, SCRATCH, TU, UD, decode_g6, g6_lines, run_matcher, sha256, sha256_bytes, witness_ok,
                     write_lines)

B10_SHA256 = "3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f"
RECORDS_SHA256 = "577c1f8de771dc80832c4cddce39f7efc2fad5dee3363480805b379e7e87f20e"   # decompressed
L10_SHA256 = "a899e36cec0f135f253e0c9942d2fecd29280da44189a01d00752e8a5af971b8"


def run_udfilter(binary: Path, hosts: Path, out: Path, args: list[str]) -> list[dict]:
    with open(hosts, "rb") as stdin, open(out, "wb") as stdout:
        p = subprocess.run(["nice", "-n", "10", str(binary), "-t", str(TU), *args],
                           stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f"udfilter failed ({p.returncode}): {p.stderr.decode()}")
    return [json.loads(x) for x in out.read_bytes().split(b"\n") if x]


def judge(recs: list[dict], b10: list[bytes], truth: dict[bytes, str], f398: list, l10: list[bytes]) -> dict:
    """F1-F3 on one set of udfilter records; returns the counts and the list of problems."""
    problems = []
    if [r["g6"].encode() for r in recs] != b10:
        problems.append("F1: records are not one per B10 graph in order")
    verdicts = {}
    for r in recs:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    forb = {r["g6"].encode() for r in recs if r["verdict"] == "forbidden"}
    refuted = {g for g, v in truth.items() if v == "refuted"}
    embedded_forbidden = sorted(g.decode() for g in forb if truth.get(g) == "embedded")
    missing = sorted(g.decode() for g in refuted - forb)
    if forb != refuted:
        problems.append(f"F2: forbidden set differs from the refuted set: {len(missing)} refuted not called "
                        f"forbidden (first {missing[:3]}), {len(embedded_forbidden)} embedded called forbidden "
                        f"(first {embedded_forbidden[:3]})")
    bad_w, low_index, not_l10 = 0, 0, 0
    index_hist: dict[int, int] = {}
    for r in recs:
        if r["verdict"] != "forbidden":
            continue
        idx, mp = r["witness"]["index"], r["witness"]["map"]
        index_hist[idx] = index_hist.get(idx, 0) + 1
        if not (0 <= idx < len(f398)) or not witness_ok(r["g6"].encode(), f398[idx], mp):
            bad_w += 1
            continue
        if idx < 74:
            low_index += 1
        else:
            _, want = decode_g6(l10[idx - 74])
            if {frozenset(e) for e in f398[idx]} != want:
                not_l10 += 1
    if bad_w:
        problems.append(f"F3: {bad_w} forbidden witnesses do not verify")
    if low_index:
        problems.append(f"F3: {low_index} witnesses name one of the 74 (B10 is 74-free)")
    if not_l10:
        problems.append(f"F3: {not_l10} witness patterns are not their L10 graph")
    tu_on_embedded = sum(1 for r in recs if r["verdict"] == "tu" and truth.get(r["g6"].encode()) == "embedded")
    return {"verdicts": verdicts, "forbidden": len(forb), "refuted": len(refuted),
            "refuted_called_forbidden": len(refuted & forb), "embedded_called_forbidden": len(embedded_forbidden),
            "tu_on_embedded": tu_on_embedded, "witnesses_verified": sum(index_hist.values()) - bad_w,
            "distinct_witness_members": len(index_hist), "problems": problems}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--b10", type=Path, default=REPO / "research/gp-10/data/B10.g6")
    ap.add_argument("--records", type=Path, default=REPO / "research/gp-10/cloud/lean3/records.jsonl.gz")
    ap.add_argument("--l10", type=Path, default=REPO / "research/gp-10/runs/B10-final-2026-09-25/L10.g6")
    ap.add_argument("--work", type=Path, default=SCRATCH / "filter-b10")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "filter-b10.json")
    ap.add_argument("--red", action="store_true")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    out = {}

    # stream the records (hundreds of MB decompressed): hash every byte, keep only g6 -> verdict
    h = hashlib.sha256()
    truth: dict[bytes, str] = {}
    with gzip.open(a.records, "rb") as f:
        for line in f:
            h.update(line)
            if line.strip():
                r = json.loads(line)
                if r["g6"].encode() in truth:
                    print("duplicate record in records.jsonl")
                    return 2
                truth[r["g6"].encode()] = r["verdict"]
    for name, got, want in (("B10.g6", sha256(a.b10), B10_SHA256), ("records.jsonl", h.hexdigest(), RECORDS_SHA256),
                            ("L10.g6", sha256(a.l10), L10_SHA256), ("forbidden-398.json", sha256(F398), F398_SHA256),
                            ("forbidden-398.g6", sha256(F398_G6), F398_G6_SHA256)):
        if got != want:
            print(f"input {name} sha256 {got} is not the pinned {want}")
            return 2
    b10 = g6_lines(a.b10)
    counts = {v: sum(1 for x in truth.values() if x == v) for v in set(truth.values())}
    print(f"B10 {len(b10)} graphs; records {len(truth)}: {counts}")
    if set(truth) != set(b10) or counts != {"embedded": 32653, "refuted": 509}:
        print("records do not cover B10 with 32,653 embedded and 509 refuted")
        return 2
    f398 = json.loads(F398.read_text())
    l10 = g6_lines(a.l10)

    # F1-F3: the new udfilter in set 398
    recs398 = run_udfilter(NEW_UDFILTER, a.b10, a.work / "b10.udfilter398.jsonl", ["-s", "398", "-f", str(F398)])
    out["set398"] = judge(recs398, b10, truth, f398, l10)
    print(f"set 398: {out['set398']['verdicts']}; refuted called forbidden {out['set398']['refuted_called_forbidden']} "
          f"of 509; embedded called forbidden {out['set398']['embedded_called_forbidden']}; witnesses verified "
          f"{out['set398']['witnesses_verified']} naming {out['set398']['distinct_witness_members']} distinct members; "
          f"problems {out['set398']['problems']}")

    # F4: GP-10's unmodified matcher over the 398 patterns
    m = run_matcher(MATCHER10, F398_G6, a.b10, a.work / "matcher10")
    pat_edges = [[tuple(sorted(e)) for e in decode_g6(p)[1]] for p in g6_lines(F398_G6)]
    bad = sum(1 for h, (i, mp) in m["removed"].items() if not witness_ok(h, pat_edges[i], mp))
    refuted = {g for g, v in truth.items() if v == "refuted"}
    f4 = {"removed": len(m["removed"]), "equals_refuted": set(m["removed"]) == refuted,
          "witnesses_bad": bad, "first_74_hits": sum(1 for i, _ in m["removed"].values() if i < 74)}
    out["matcher10"] = f4
    print(f"matcher.c (unmodified) on B10 with the 398: removed {f4['removed']}, equals refuted {f4['equals_refuted']}, "
          f"bad witnesses {bad}, hits on the 74 {f4['first_74_hits']}")

    # F5: set 74, old and new
    old = a.work / "b10.old.jsonl"
    new_default = a.work / "b10.new-default.jsonl"
    new_74 = a.work / "b10.new74.jsonl"
    r_old = run_udfilter(OLD_UDFILTER, a.b10, old, ["-f", str(UD / "data/forbidden-74.json")])
    run_udfilter(NEW_UDFILTER, a.b10, new_default, ["-f", str(UD / "data/forbidden-74.json")])
    run_udfilter(NEW_UDFILTER, a.b10, new_74, ["-s", "74", "-f", str(UD / "data/forbidden-74.json")])
    f5 = {"old_equals_new_default": old.read_bytes() == new_default.read_bytes(),
          "old_equals_new_74": old.read_bytes() == new_74.read_bytes(),
          "forbidden_verdicts_set74": sum(1 for r in r_old if r["verdict"] == "forbidden"),
          "output_sha256": sha256(old)}
    out["set74"] = f5
    print(f"set 74: old == new(default) {f5['old_equals_new_default']}, old == new(-s 74) {f5['old_equals_new_74']}, "
          f"forbidden verdicts {f5['forbidden_verdicts_set74']}, output sha256 {f5['output_sha256']}")

    ok = (not out["set398"]["problems"] and f4["equals_refuted"] and bad == 0 and f4["first_74_hits"] == 0
          and f5["old_equals_new_default"] and f5["old_equals_new_74"] and f5["forbidden_verdicts_set74"] == 0)

    reds = []
    if a.red:
        # X1
        j1 = judge(r_old, b10, truth, f398, l10)
        reds.append({"control": "X1 old udfilter (the 74 only) judged as the set-398 run",
                     "went_red": bool(j1["problems"]), "problems": j1["problems"]})
        # X2
        x2 = json.loads(json.dumps(recs398))
        k = next(i for i, r in enumerate(x2) if r["verdict"] == "forbidden")
        x2[k] = {"g6": x2[k]["g6"], "verdict": "pass"}
        j2 = judge(x2, b10, truth, f398, l10)
        reds.append({"control": f"X2 record {k} ({x2[k]['g6']}) turned from forbidden into pass",
                     "went_red": any(p.startswith("F2") for p in j2["problems"]), "problems": j2["problems"]})
        # X3
        x3 = json.loads(json.dumps(recs398))
        k = next(i for i, r in enumerate(x3) if r["verdict"] == "forbidden")
        x3[k]["witness"]["map"][1] = x3[k]["witness"]["map"][0]
        j3 = judge(x3, b10, truth, f398, l10)
        reds.append({"control": f"X3 witness of record {k} made non-injective",
                     "went_red": any(p.startswith("F3") for p in j3["problems"]), "problems": j3["problems"]})
        # X4: rebuild udfilter pinned to a mutated list (member J replaced by member J+1)
        J = 74 + 100
        mutated = json.loads(F398.read_text())
        mutated[J] = mutated[J + 1]
        mut_path = a.work / "forbidden-398-member-replaced.json"
        mut_path.write_bytes(json.dumps(mutated).encode())
        build = a.work / "udfilter-pinned-to-mutation"
        src = UD / "filter"
        cmd = ["nice", "-n", "10", "cc", "-std=c17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
               f"-DUDF_FORBIDDEN_398_SHA256=\"{sha256(mut_path)}\"", "-o", str(build),
               str(src / "udfilter.c"), str(src / "udfilter-cli.c")]
        subprocess.run(cmd, check=True)
        r4 = run_udfilter(build, a.b10, a.work / "b10.x4.jsonl", ["-s", "398", "-f", str(mut_path)])
        j4 = judge(r4, b10, truth, mutated, l10)
        lost = [r["g6"] for r in r4 if r["verdict"] != "forbidden" and truth[r["g6"].encode()] == "refuted"]
        reds.append({"control": f"X4 udfilter rebuilt with its pin moved to a list whose member {J} "
                                f"({l10[J - 74].decode()}) is replaced by member {J + 1}",
                     "refuted_now_not_forbidden": lost, "went_red": any(p.startswith("F2") for p in j4["problems"]),
                     "problems": j4["problems"]})
        # X5: matcher with member J dropped (chunk-local index)
        pats = g6_lines(F398_G6)
        reduced = a.work / "matcher-drop.g6"
        write_lines(reduced, pats[:J] + pats[J + 1:])
        m5 = run_matcher(MATCHER10, reduced, a.b10, a.work / "matcher10-drop")
        reds.append({"control": f"X5 matcher without member {J}", "removed": len(m5["removed"]),
                     "went_red": set(m5["removed"]) != refuted})
        for r in reds:
            print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {r['control']}: "
                  f"{r.get('problems', r.get('removed'))}")
        ok = ok and all(r["went_red"] for r in reds)
    out["red_controls"] = reds
    out["pass"] = ok
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(out, indent=1) + "\n")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
