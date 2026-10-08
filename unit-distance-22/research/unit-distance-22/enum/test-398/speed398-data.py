#!/usr/bin/env python3
"""The orbit-class deduplication of the 3,875 deletion patterns, recomputed independently.

udenum (set 398) keeps a deletion pattern (F, v) iff v is the least vertex of its Aut(F)-orbit,
with the orbits from nauty, and pins the result: 3,387 patterns, by |S| = deg_F(v)
{2: 209, 3: 2126, 4: 830, 5: 184, 6: 34, 7: 4}.  Here Aut(F) is computed with networkx (VF2
isomorphisms of F onto itself, no code shared with udenum) for each of the 398 graphs of
data/forbidden-398.json, and
  1. the counts and the |S| distribution must equal the pinned ones;
  2. the kept list itself must equal udenum's: a test build of the new source, changed only to
     print every kept (source, deleted) pair, is run with --pattern-stats;
  3. every dropped (F, v') has an automorphism of F taking the kept orbit minimum v to v' (it is
     in the same orbit by construction; the map is exhibited and checked edge by edge);
  4. the isomorphism classes of the kept patterns' graphs F - v (S forgotten), which udenum uses to
     share one existence search per class: 1,843 classes, and udenum's partition (printed by the
     same test build) must equal the partition by nauty-labelg canonical form of networkx's F - v.
Red (--red): the comparison of 2 must fail when one kept pair is removed from udenum's list, and
when one orbit is split in the networkx list; the comparison of 4 must fail when two classes of
udenum's partition are merged.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import networkx as nx
from networkx.algorithms import isomorphism as iso

from speed398lib import F398, F398_SHA256, NEW_SOURCE, SCRATCH, build_variant, sha256

PINNED_COUNT = 3387
PINNED_DISTRIBUTION = {2: 209, 3: 2126, 4: 830, 5: 184, 6: 34, 7: 4}


def networkx_kept(graphs):
    kept, witnesses, fv = [], [], []
    for i, edges in enumerate(graphs):
        g = nx.Graph()
        n = max(max(e) for e in edges) + 1
        g.add_nodes_from(range(n))
        g.add_edges_from(tuple(e) for e in edges)
        auts = list(iso.GraphMatcher(g, g).isomorphisms_iter())
        orbit = {v: sorted({a[v] for a in auts}) for v in range(n)}
        for v in range(n):
            if orbit[v][0] == v:
                kept.append((i, v, g.degree(v)))
                h = g.copy()
                h.remove_node(v)
                fv.append(nx.to_graph6_bytes(nx.convert_node_labels_to_integers(h), header=False).strip())
            else:
                rep = orbit[v][0]
                sigma = next(a for a in auts if a[rep] == v)
                ok = all(g.has_edge(sigma[x], sigma[y]) for x, y in g.edges()) and len(set(sigma.values())) == n
                witnesses.append((i, v, rep, ok))
    return kept, witnesses, fv


def udenum_kept(work: Path) -> tuple[list[tuple[int, int]], list[int]]:
    src = NEW_SOURCE.read_text()
    old = "        search_graph_build(&s->patterns[s->pattern_count++], p->n, p->m, p->adj, p->smask, p->order);\n"
    new = old + '        fprintf(stderr, "KEPT %d %d\\n", p->source, p->deleted);\n'
    old2 = "    if (s->class_count != SEARCH_398_GRAPH_CLASSES)\n"
    new2 = ('    for (i = 0; i < s->pattern_count; ++i) fprintf(stderr, "CLASS %d %d\\n", i, s->graph_class[i]);\n'
            + old2)
    if src.count(old) != 1 or src.count(old2) != 1:
        raise SystemExit("cannot locate the kept-pattern or class lines in udenum.c")
    path = work / "udenum-print-kept.c"
    path.write_text(src.replace(old, new).replace(old2, new2))
    binary = build_variant(path, work / "udenum-print-kept")
    p = subprocess.run(["nice", "-n", "15", str(binary), "--forbidden", str(F398), "--forbidden-set", "398",
                        "--pattern-stats"], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"print-kept build failed to run: {p.stderr}")
    kept = [tuple(int(x) for x in line.split()[1:]) for line in p.stderr.splitlines() if line.startswith("KEPT ")]
    classes = [int(line.split()[2]) for line in p.stderr.splitlines() if line.startswith("CLASS ")]
    return kept, classes


def same_partition(labels_a: list, labels_b: list) -> bool:
    """True iff two labellings of the same items induce the same partition."""
    if len(labels_a) != len(labels_b):
        return False
    ab, ba = {}, {}
    for x, y in zip(labels_a, labels_b):
        if ab.setdefault(x, y) != y or ba.setdefault(y, x) != x:
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-data")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-data.json")
    ap.add_argument("--red", action="store_true")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    if sha256(F398) != F398_SHA256:
        print("data/forbidden-398.json is not the pinned file")
        return 2
    graphs = json.loads(F398.read_text())
    kept, witnesses, fv = networkx_kept(graphs)
    dist: dict[int, int] = {}
    for _, _, s in kept:
        dist[s] = dist.get(s, 0) + 1
    checks = {"count": len(kept) == PINNED_COUNT, "distribution": dict(sorted(dist.items())) == PINNED_DISTRIBUTION,
              "patterns_total": len(kept) + len(witnesses) == 3875,
              "every_dropped_pattern_has_a_verified_automorphism": all(w[3] for w in witnesses)}
    nx_list = sorted((i, v) for i, v, _ in kept)
    c_list, c_classes = udenum_kept(a.work)
    # canonical forms of the kept patterns' graphs, in udenum's kept order
    with tempfile.TemporaryDirectory(dir=a.work) as tmp:
        where = {(i, v): k for k, (i, v, _) in enumerate(kept)}
        src = Path(tmp) / "fv.g6"
        src.write_bytes(b"".join(fv[where[x]] + b"\n" for x in c_list))
        subprocess.run(["nice", "-n", "15", "nauty-labelg", "-q", str(src), str(Path(tmp) / "fv.canon.g6")], check=True)
        canon = [x for x in (Path(tmp) / "fv.canon.g6").read_bytes().split(b"\n") if x]
    checks["udenum_kept_list_equals_networkx"] = sorted(c_list) == nx_list
    checks["udenum_kept_list_in_data_order_without_repeats"] = len(set(c_list)) == len(c_list)
    checks["graph_classes_1843"] = len(set(canon)) == 1843 and len(set(c_classes)) == 1843
    checks["udenum_class_partition_equals_labelg"] = same_partition(c_classes, canon)
    print(f"networkx: {len(kept)} orbit classes, |S| distribution {dict(sorted(dist.items()))}; "
          f"{len(witnesses)} dropped patterns, automorphisms verified {sum(w[3] for w in witnesses)}", flush=True)
    print(f"udenum kept {len(c_list)} patterns", flush=True)
    reds = []
    if a.red:
        reds.append({"control": "one kept pair removed from udenum's list",
                     "went_red": sorted(c_list[1:]) != nx_list})
        split = list(nx_list)
        i, v = next((i, v) for i, v, rep, ok in witnesses)
        split.append((i, v))
        reds.append({"control": f"orbit of (F{i}, {v}) split in the networkx list", "went_red": sorted(c_list) != sorted(split)})
        a0 = c_classes[0]
        a1 = next(x for x in c_classes if x != a0)
        merged = [a0 if x == a1 else x for x in c_classes]
        reds.append({"control": "two of udenum's graph classes merged", "went_red": not same_partition(merged, canon)})
        for r in reds:
            print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {r['control']}")
    for k, v in checks.items():
        print(f"{'ok ' if v else 'BAD'} {k}")
    ok = all(checks.values()) and all(r["went_red"] for r in reds)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps({"checks": checks, "distribution": dist, "kept": len(kept),
                                     "red_controls": reds, "pass": ok}, indent=1) + "\n")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
