"""Red-on-purpose controls for independent_audit.py.

usage: python independent_audit_redteam.py B10.g6 RECORDS.jsonl L10.g6 WORKDIR

Each control mutates ONE thing in a copy of the inputs, reruns the audit on the stages that should see it, and passes
only if the audit says FAIL with the alarm that names the mutation. A last control reruns stage 3 on the true inputs at
240 digits: the embeddings are exact, so the worst edge residue must fall far below the 120-digit one (rounding),
where a genuinely wrong coordinate would leave it where it was.
"""
import sys, json, os, subprocess, random, time
from fractions import Fraction
import networkx as nx

B10_PATH, REC_PATH, L10_PATH, W = sys.argv[1:5]
AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "independent_audit.py")
PY = sys.executable
os.makedirs(W, exist_ok=True)
B10 = [l.strip() for l in open(B10_PATH) if l.strip()]
L10 = [l.strip() for l in open(L10_PATH) if l.strip()]
graph = lambda g6: nx.from_graph6_bytes(g6.encode())


def maps_into(small, big, m):
    return len(set(m)) == len(m) and all(big.has_edge(m[u], m[v]) for u, v in small.edges())


def mutate_records(out, pick, change):
    """Copy RECORDS to out, applying change() to the first record pick() selects. Returns that record's g6."""
    hit = None
    with open(REC_PATH) as f, open(out, "w") as o:
        for line in f:
            if hit is None:
                r = json.loads(line)
                if pick(r):
                    change(r)
                    hit = r["g6"]
                    o.write(json.dumps(r) + "\n")
                    continue
            o.write(line)
    assert hit, "no record matched"
    return hit


def run(name, stages, b10=B10_PATH, rec=REC_PATH, l10=L10_PATH, dps=None):
    out = os.path.join(W, name + ".json")
    cmd = [PY, AUDIT, b10, rec, l10, "--stages", stages, "--out", out] + (["--dps", str(dps)] if dps else [])
    t = time.time()
    with open(os.path.join(W, name + ".log"), "w") as log:
        rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, SYMPY_GROUND_TYPES="python"))
    rep = json.load(open(out)) if os.path.exists(out) else {"verdict": f"NO REPORT (exit {rc})", "alarms": []}
    rep["_seconds"] = round(time.time() - t)
    return rep


results = []


def control(name, rep, expect):
    ok = rep["verdict"] == "INDEPENDENT AUDIT FAIL" and any(expect in a for a in rep["alarms"])
    results.append({"control": name, "red": ok, "expected_alarm": expect, "verdict": rep["verdict"],
                    "alarms": rep["alarms"][:3], "seconds": rep["_seconds"]})
    print(("RED  " if ok else "GREEN?! ") + name, rep["verdict"], rep["alarms"][:2], flush=True)


# M1: one exact coordinate moved by 10^-40 (far below double precision, far above the 120-digit rounding)
p = os.path.join(W, "m1.jsonl")
def bump(r):
    x = r["cert"]["coords"][0][0]
    x[0] = str(Fraction(x[0]) + Fraction(1, 10 ** 40))
g = mutate_records(p, lambda r: r["verdict"] == "embedded" and (r.get("cert") or {}).get("type") == "exact", bump)
control(f"M1 exact coordinate of {g} moved by 1e-40", run("m1", "3", rec=p), "off unit length")
os.remove(p)

# M2: one super-pointer map with two entries swapped so that an edge lands on a non-edge
p = os.path.join(W, "m2.jsonl")
def is_breakable(r):
    c = r.get("cert") or {}
    if c.get("type") != "super":
        return False
    G, H, m = graph(r["g6"]), graph(c["g6"]), c["map"]
    for i in range(len(m)):
        for j in range(i + 1, len(m)):
            mm = list(m); mm[i], mm[j] = mm[j], mm[i]
            if not maps_into(G, H, mm):
                c["_broken"] = mm
                return True
    return False
def swap(r):
    r["cert"]["map"] = r["cert"].pop("_broken")
g = mutate_records(p, is_breakable, swap)
control(f"M2 super-pointer map of {g} broken by one swap", run("m2", "3", rec=p), "does not resolve")
os.remove(p)

# M3: an L10 member's verdict flipped to embedded (its refutation left in place)
p = os.path.join(W, "m3.jsonl")
g = mutate_records(p, lambda r: r["g6"] == L10[0], lambda r: r.__setitem__("verdict", "embedded"))
rep = run("m3", "24", rec=p)
control(f"M3 L10 member {g} relabelled embedded (minimality)", rep, "minimality recount differs")
control(f"M3 L10 member {g} relabelled embedded (up-set)", rep, "contains an L10 member")
os.remove(p)

# M4: a non-minimal refuted graph (a sub pointer) relabelled embedded: only the up-set can see this directly
p = os.path.join(W, "m4.jsonl")
g = mutate_records(p, lambda r: (r.get("cert") or {}).get("type") == "sub", lambda r: r.__setitem__("verdict", "embedded"))
control(f"M4 non-minimal refuted {g} relabelled embedded", run("m4", "4", rec=p), "contains an L10 member")
os.remove(p)

# M5: one L10 member dropped from the claimed list
p = os.path.join(W, "m5-L10.g6")
open(p, "w").write("".join(x + "\n" for x in L10[1:]))
rep = run("m5", "24", l10=p)
control(f"M5 L10 without {L10[0]} (minimality)", rep, "minimality recount differs")
control(f"M5 L10 without {L10[0]} (up-set)", rep, "up-set of L10")

# M6: one non-minimal refuted graph added to the claimed list
p = os.path.join(W, "m6-L10.g6")
nonmin = None
with open(REC_PATH) as f:
    for line in f:
        if '"sub"' in line:
            r = json.loads(line)
            if (r.get("cert") or {}).get("type") == "sub":
                nonmin = r["g6"]; break
open(p, "w").write("".join(x + "\n" for x in sorted(L10 + [nonmin])))
control(f"M6 L10 plus non-minimal {nonmin}", run("m6", "2", l10=p), "minimality recount differs")

# M7: B10 with one graph replaced by a relabelled copy of another (a duplicate class, and a hole)
p = os.path.join(W, "m7-B10.g6")
rng = random.Random(20260925)
H = graph(B10[1]); n = H.number_of_nodes(); perm = list(range(n))
for _ in range(1000):
    # Built explicitly with nodes inserted 0..n-1: graph6 follows insertion order, so relabel_nodes (and even
    # to_graph6_bytes(nodes=...), which goes through subgraph()) writes the original string back and undoes the perm.
    rng.shuffle(perm)
    R = nx.Graph(); R.add_nodes_from(range(n)); R.add_edges_from((perm[u], perm[v]) for u, v in H.edges())
    dup = nx.to_graph6_bytes(R, header=False).decode().strip()
    if dup != B10[1]:
        break
else:
    sys.exit("M7: no relabelling changed the graph6 string")
open(p, "w").write("".join(x + "\n" for x in [dup] + B10[1:]))
rep = run("m7", "", b10=p)
control(f"M7 B10 with {B10[0]} replaced by a relabelled {B10[1]} (duplicate)", rep, "duplicate isomorphism class")
control(f"M7 B10 with {B10[0]} replaced by a relabelled {B10[1]} (coverage)", rep, "do not cover B10")

# P1: precision scaling on the true inputs (must PASS, with a residue far below the 120-digit one)
rep = run("p1-dps240", "3", dps=240)
e = rep.get("embeddings_and_pointers", {})
worst = float(e.get("worst_edge_error", "1")) if e else 1.0
ok = rep["verdict"] == "INDEPENDENT AUDIT PASS" and worst < 1e-200
results.append({"control": "P1 stage 3 at 240 digits on the true inputs", "passes_and_shrinks": ok,
                "worst_edge_error_240": e.get("worst_edge_error"), "smallest_point_gap": e.get("smallest_point_gap"),
                "exact_embeddings": e.get("exact_embeddings"), "seconds": rep["_seconds"]})
print(("OK   " if ok else "BAD  ") + "P1 240 digits", e.get("worst_edge_error"), flush=True)

allred = all(r.get("red", r.get("passes_and_shrinks")) for r in results)
summary = {"controls": results, "all_controls_behaved": allred,
           "verdict": "REDTEAM PASS: every mutation turned the audit red with its named alarm" if allred else "REDTEAM FAIL"}
json.dump(summary, open(os.path.join(W, "redteam.json"), "w"), indent=1)
print(summary["verdict"], flush=True)
