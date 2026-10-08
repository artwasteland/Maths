"""Slice cost with a pruning rule: pilot per-level costs x retention from combined.json (gen and children)."""
import json, sys
sys.path.insert(0, "<scratch>/scratchpad/rh65")
from project import levels
kind, tags, comb = sys.argv[1], sys.argv[2].split(","), json.load(open(sys.argv[3]))
t_prover = float(sys.argv[4]) if len(sys.argv) > 4 else 5e-4     # seconds per graph through the prover (one core)
ret = {int(L): (r["gen_retention"], r["children_retention"]) for L, r in comb.items()}
per = levels(kind, tags); old = new = prov = 0.0
for n in sorted(per):
    p = per[n]; g, c = ret.get(n - 1, (1.0, 1.0)); g = min(g, 1.0)
    o = p["gen"] + p["prune"] + p["verify"]; nw = p["gen"] * g + (p["prune"] + p["verify"]) * c
    pr = p["children"] * c * t_prover / 4
    old += o; new += nw; prov += pr
    print(f"  level {n}: {o:7.0f} s -> {nw:7.0f} s (+ prover {pr:5.0f} s)   gen x{g:.3f} children x{c:.3f}")
print(f"  total {old:.0f} s -> {new:.0f} s + prover {prov:.0f} s = {new + prov:.0f} s: ratio {(new + prov) / old:.3f}")
