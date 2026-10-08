#!/usr/bin/env python3
"""Agreement: udtriangle's refuted/tu-versus-pass classification against the prototypes', graph by graph.

The prototype flags a graph when rhombus_probe says collision or hidden-edge, or triangle_probe says closed,
closed-collision or closed-inconsistent.  udtriangle flags it when it writes refuted or tu.  Every disagreement is
printed with its graph.  Also a cross-tab of the finer verdicts (whether the root alone closes, and refuted vs tu).

usage: agree.py GRAPHS.g6 PROTOTYPE.txt VERDICTS.jsonl [label]
"""
import collections
import json
import sys

FLAG_T = {"closed", "closed-collision", "closed-inconsistent"}


def main(gpath, ppath, vpath, label=""):
    graphs = [l.strip() for l in open(gpath) if l.strip()]
    proto = [l.split() for l in open(ppath)]
    ours = [json.loads(l) for l in open(vpath)]
    assert len(graphs) == len(proto) == len(ours), (len(graphs), len(proto), len(ours))
    cross = collections.Counter()
    dis = []
    for g, (r, t), rec in zip(graphs, proto, ours):
        pflag = r != "none" or t in FLAG_T
        v = rec["verdict"]
        uflag = v != "pass"
        root = ""
        if uflag:
            tree = rec["witness"]["tri"]["tree"]
            root = "root-leaf" if "leaf" in tree else "split"
        cross[(r, t, v, root)] += 1
        if pflag != uflag:
            dis.append((g, r, t, v))
    flagged = sum(1 for (r, t), rec in zip(proto, ours) if rec["verdict"] != "pass")
    print(f"{label} graphs={len(graphs)} udtriangle_flagged={flagged} disagreements={len(dis)}")
    for (r, t, v, root), c in sorted(cross.items(), key=lambda x: -x[1]):
        print(f"    prototype rhombus={r:11s} triangle={t:19s} -> udtriangle {v:7s} {root:9s} x{c}")
    for g, r, t, v in dis:
        print(f"    DISAGREE {g}: prototype {r}/{t}, udtriangle {v}")
    return 1 if dis else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
