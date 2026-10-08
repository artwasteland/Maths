"""Project the (23,65) slice cost with the rhombus rule from pilot per-level costs and descent retention factors."""
import json, sys, collections
base = "<scratch>/scratchpad/pilot/research/unit-distance-23/results/u23/"
def levels(kind, tags):
    per = collections.defaultdict(lambda: collections.Counter())
    for t in tags:
        s = json.load(open(f"{base}{kind}/{t}/run-summary.json"))
        for l in s["levels"]:
            if l["n"] <= 12: continue
            walls = [x.get("wall_seconds", 0) or 0 for x in l.get("shards") or []]
            p = per[l["n"]]
            p["gen"] += max(max(walls, default=0), sum(walls) / 4) / len(tags)
            p["prune"] += ((l.get("prune") or {}).get("step_wall_seconds", 0) or 0) / len(tags)
            p["verify"] += ((l.get("verify") or {}).get("wall_seconds", 0) or 0) / len(tags)
            p["children"] += (l.get("children") or 0) / len(tags)
    return per
def retention(path, sub_all, sub_unf):
    m = json.load(open(path)); out = {}
    for L, r in m.items():
        a, u = r[sub_all], r[sub_unf]
        out[int(L)] = (u["cpu"] / a["cpu"] if a["cpu"] else 1.0, u["written"] / a["written"] if a["written"] else 1.0, a["parents"])
    return out
def project(per, ret, t_prover=5e-5, cores=4):
    old = new = 0.0
    rows = []
    for n in sorted(per):
        p = per[n]; o = p["gen"] + p["prune"] + p["verify"]
        g, c, _ = ret.get(n - 1, (1.0, 1.0, 0))
        nw = p["gen"] * g + (p["prune"] + p["verify"]) * c + p["children"] * c * t_prover / cores
        old += o; new += nw; rows.append((n, round(o), round(nw), round(g, 3), round(c, 3)))
    return old, new, rows
if __name__ == "__main__":
    kind, tags, mpath, sa, su = sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4], sys.argv[5]
    old, new, rows = project(levels(kind, tags), retention(mpath, sa, su))
    for r in rows: print("  level %d: %6d s -> %6d s  (gen x%s, children x%s)" % r)
    print(f"  slice total {old:.0f} s -> {new:.0f} s: ratio {new/old:.3f}")
