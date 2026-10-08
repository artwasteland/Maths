#!/usr/bin/env python3
"""(b2) Brute force at order 10, where the 324 first act: the generator against every graph.

  brute74  = every graph on 10 vertices (nauty-geng -q 10: 12,005,168 graphs) minus those that
             contain one of the first 74, decided by GP-10's UNMODIFIED matcher (10-vertex hosts),
             canonically relabelled with nauty-labelg and sorted;
  brute398 = the same minus those containing any of the 398 (the matcher chained over chunks of
             at most 128 patterns of data/forbidden-398.g6);
  gen74, gen398 = udenum (set 74 / set 398) run for every m = 0..45 on ALL 74-free 9-vertex graphs
             (geng -q 9, labelg, matcher with the 74), relabelled and sorted.

PASS iff gen74 == brute74, gen398 == brute398, the old binary's gen74 is byte-identical to the new
binary's, and brute74 minus brute398 is EXACTLY GP-10's 509 refuted graphs.  The last equality is
forced by the mathematics, not by this code: a 74-free 10-vertex graph containing one of the 324
contains it as a spanning subgraph, so it is 2-connected and in B10, and it is not a unit-distance
graph, so it is refuted; conversely a refuted B10 graph is 74-free on 10 vertices and its minimal
non-unit-distance subgraph has 10 vertices, i.e. is one of the 324.

Red controls (--red): gen398 with one record dropped (-> gen398 != brute398); the set-74 generator
judged against brute398 (-> differs by the 509); brute398 recomputed without member 74 (L10 line 0,
which as a host contains no other member and none of the 74 -> the difference loses it).
"""
from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path

from t398lib import (F398, F398_G6, F74, HERE, MATCHER10, NEW_UDENUM, OLD_UDENUM, REPO, SCRATCH, g6_lines,
                     run_matcher, run_udenum, sha256, write_lines)


def labelg_sorted(src: Path, dst: Path) -> list[bytes]:
    tmp = dst.with_suffix(".labelg.g6")
    subprocess.run(["nice", "-n", "10", "nauty-labelg", "-q", str(src), str(tmp)], check=True)
    lines = sorted(g6_lines(tmp))
    write_lines(dst, lines)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--records", type=Path, default=REPO / "research/gp-10/cloud/lean3/records.jsonl.gz")
    ap.add_argument("--work", type=Path, default=SCRATCH / "brute10")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "brute10.json")
    ap.add_argument("--red", action="store_true")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    out: dict = {}

    # all graphs on 9 and 10 vertices
    for n in (9, 10):
        f = w / f"geng-{n}.g6"
        if not f.exists():
            with open(f, "wb") as stdout:
                subprocess.run(["nice", "-n", "10", "nauty-geng", "-q", str(n)], stdout=stdout, check=True)
        out[f"geng_{n}"] = sum(1 for _ in open(f, "rb"))
    print(f"geng: {out['geng_9']} graphs on 9 vertices, {out['geng_10']} on 10", flush=True)

    pats = g6_lines(F398_G6)
    p74 = w / "patterns-74.g6"
    write_lines(p74, pats[:74])

    # 9-vertex parents: canonical, 74-free (= 398-free: the 324 have 10 vertices)
    m9 = run_matcher(MATCHER10, p74, w / "geng-9.g6", w / "m9", witnesses=False)
    raw9 = w / "free9.raw.g6"
    write_lines(raw9, m9["survivors"])
    free9 = labelg_sorted(raw9, w / "free9.g6")
    out["free9"] = len(free9)

    # brute force at 10
    m10_74 = run_matcher(MATCHER10, p74, w / "geng-10.g6", w / "m10-74", witnesses=False)
    raw74 = w / "brute74.raw.g6"
    write_lines(raw74, m10_74["survivors"])
    brute74 = labelg_sorted(raw74, w / "brute74.g6")
    m10_398 = run_matcher(MATCHER10, F398_G6, raw74, w / "m10-398")    # the 74 again, then the 324
    raw398 = w / "brute398.raw.g6"
    write_lines(raw398, m10_398["survivors"])
    brute398 = labelg_sorted(raw398, w / "brute398.g6")
    out.update({"brute74": len(brute74), "brute398": len(brute398)})
    print(f"brute force: {len(brute74)} 74-free and {len(brute398)} 398-free graphs on 10 vertices", flush=True)

    # the generator, all m, three configurations
    gens = {}
    for name, binary, extra, forb in (("old74", OLD_UDENUM, [], F74), ("new74", NEW_UDENUM, [], F74),
                                      ("new398", NEW_UDENUM, ["--forbidden-set", "398"], F398)):
        chunks = []
        for m in range(0, 46):
            o = w / f"gen-{name}-10-{m}.g6"
            run_udenum(binary, w / "free9.g6", 10, m, o, extra=extra, forbidden=forb)
            chunks.append(o.read_bytes())
        raw = w / f"gen-{name}.raw.g6"
        raw.write_bytes(b"".join(chunks))
        gens[name] = (raw.read_bytes(), labelg_sorted(raw, w / f"gen-{name}.g6"))
        print(f"generator {name}: {len(gens[name][1])} graphs on 10 vertices", flush=True)

    refuted = set()
    with gzip.open(a.records, "rb") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["verdict"] == "refuted":
                    refuted.add(r["g6"].encode())
    ref_file = w / "refuted.raw.g6"
    write_lines(ref_file, sorted(refuted))
    refuted_c = set(labelg_sorted(ref_file, w / "refuted.g6"))
    diff = set(brute74) - set(brute398)
    checks = {
        "gen74_equals_brute74": gens["new74"][1] == brute74,
        "gen398_equals_brute398": gens["new398"][1] == brute398,
        "old74_bytes_equal_new74": gens["old74"][0] == gens["new74"][0],
        "brute398_subset_of_brute74": set(brute398) <= set(brute74),
        "brute74_minus_brute398_is_the_509_refuted": diff == refuted_c and len(refuted_c) == 509,
    }
    out.update({"gen": {k: len(v[1]) for k, v in gens.items()}, "difference": len(diff),
                "refuted": len(refuted_c), "checks": checks})
    for k, v in checks.items():
        print(f"{'ok ' if v else 'BAD'} {k}", flush=True)
    ok = all(checks.values())

    reds = []
    if a.red:
        g398 = gens["new398"][1]
        reds.append({"control": "gen398 with its last record dropped", "went_red": g398[:-1] != brute398})
        reds.append({"control": "the set-74 generator judged against brute398", "went_red": gens["new74"][1] != brute398})
        # drop member 74 (L10 line 0): as a host, that graph contains no other member (the list is an
        # antichain) and none of the 74, so at least it must fall out of the difference
        J = 0
        red_pats = w / "patterns-drop.g6"
        write_lines(red_pats, pats[:74 + J] + pats[74 + J + 1:])
        m_red = run_matcher(MATCHER10, red_pats, raw74, w / "m10-drop")
        red_raw = w / "red398.raw.g6"
        write_lines(red_raw, m_red["survivors"])
        red398 = set(labelg_sorted(red_raw, w / "red398.g6"))
        reds.append({"control": f"brute398 without member {74 + J}", "difference": len(set(brute74) - red398),
                     "went_red": (set(brute74) - red398) != refuted_c})
        for r in reds:
            print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {r['control']} "
                  f"{r.get('difference', '')}", flush=True)
        ok = ok and all(r["went_red"] for r in reds)
    out["red_controls"] = reds
    out["pass"] = ok
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(out, indent=1) + "\n")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
