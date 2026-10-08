"""Memory-lean B10 assembler: the driver's --no-producers assembly without holding certificates in memory.

usage: python lean_assemble.py B10.g6 POSET.json OUT_DIR SEED.jsonl[.gz] ...

Same semantics as drive/driver.py with --no-producers and no validation (drive/aggregate.py write_aggregate):
first row per graph wins across the seed files in argument order (only refuted/embedded rows, only input graphs, rows
over 8 MiB skipped and counted, as the checker's record limit requires); embedded verdicts propagate to children and
refuted verdicts to parents over the poset's cover relations, writing the same pointer records
{"cert":{"g6":..,"map":..,"type":"super"|"sub"},"g6":..,"verdict":..}; seed rows are written verbatim; one record per
input graph in input order; UNKNOWN.g6 lists the rest. Only (file, offset) is kept per seed, never the certificate.
The output is a producer artifact: the official checker is what verifies it.
"""
import sys, json, gzip, os

MAX_LINE = 8 * 1024 * 1024
inp, poset_path, out_dir, seeds = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
inputs = [l.strip() for l in open(inp) if l.strip()]
input_set = set(inputs)


def opener(p):
    return open(p, "rb")


# random access into gzip streams re-decompresses from the start on every backward seek: use plain copies
os.makedirs(out_dir, exist_ok=True)
plain = []
for i, p in enumerate(seeds):
    if p.endswith(".gz"):
        q = os.path.join(out_dir, f".seed{i}.jsonl")
        with gzip.open(p, "rb") as src, open(q, "wb") as dst:
            while True:
                b = src.read(1 << 20)
                if not b:
                    break
                dst.write(b)
        plain.append(q)
    else:
        plain.append(p)
seeds = plain

seed_at, verdict, skipped = {}, {}, {"over_8MiB": 0, "not_input": 0, "not_decided": 0, "duplicate": 0}
for fi, p in enumerate(seeds):
    with opener(p) as f:
        while True:
            off = f.tell()
            raw = f.readline()
            if not raw:
                break
            if len(raw) > MAX_LINE:
                skipped["over_8MiB"] += 1
                continue
            r = json.loads(raw)
            g, v = r.get("g6"), r.get("verdict")
            del r
            if v not in ("refuted", "embedded"):
                skipped["not_decided"] += 1; continue
            if g not in input_set:
                skipped["not_input"] += 1; continue
            if g in seed_at:
                skipped["duplicate"] += 1; continue
            seed_at[g] = (fi, off, len(raw))
            verdict[g] = v

poset = json.load(open(poset_path))
assert set(poset["vertices"]) == input_set, "poset vertices differ from the input list"
children, parents = {}, {}
for rel in poset["relations"]:
    children.setdefault(rel["parent"], []).append(rel)
    parents.setdefault(rel["child"], []).append(rel)
del poset

pointer = {}
emb = [g for g, v in verdict.items() if v == "embedded"]
ref = [g for g, v in verdict.items() if v == "refuted"]
seen_e, seen_r = set(), set()
while emb or ref:
    if emb:
        parent = emb.pop()
        if parent in seen_e:
            continue
        seen_e.add(parent)
        for rel in children.get(parent, ()):
            c = rel["child"]
            if c in verdict:
                if verdict[c] == "refuted":
                    raise SystemExit(f"CONFLICT: {c} is both embedded and refuted")
                continue
            verdict[c] = "embedded"
            pointer[c] = {"cert": {"g6": parent, "map": list(rel["map"]), "type": "super"}, "g6": c, "verdict": "embedded"}
            emb.append(c)
    else:
        child = ref.pop()
        if child in seen_r:
            continue
        seen_r.add(child)
        for rel in parents.get(child, ()):
            p = rel["parent"]
            if p in verdict:
                if verdict[p] == "embedded":
                    raise SystemExit(f"CONFLICT: {p} is both embedded and refuted")
                continue
            verdict[p] = "refuted"
            pointer[p] = {"cert": {"g6": child, "map": list(rel["map"]), "type": "sub"}, "g6": p, "verdict": "refuted"}
            ref.append(p)

os.makedirs(out_dir, exist_ok=True)
handles = [opener(p) for p in seeds]
unknown = []
counts = {"embedded": 0, "refuted": 0, "unknown": 0, "seed": 0, "pointer": 0}
with open(out_dir + "/records.jsonl", "wb") as o:
    for g in inputs:
        if g in seed_at:
            fi, off, n = seed_at[g]
            handles[fi].seek(off)
            raw = handles[fi].readline()
            assert len(raw) == n and raw.endswith(b"\n")
            o.write(raw); counts["seed"] += 1
        elif g in pointer:
            o.write((json.dumps(pointer[g], sort_keys=True, separators=(",", ":")) + "\n").encode()); counts["pointer"] += 1
        else:
            rec = {"cert": {"budget": {"no_producers": True}, "reason": "assembly only: no seed or monotone consequence"},
                   "g6": g, "verdict": "unknown"}
            o.write((json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode())
            unknown.append(g)
        counts[verdict.get(g, "unknown")] += 1
with open(out_dir + "/UNKNOWN.g6", "w") as o:
    o.write("".join(g + "\n" for g in unknown))
summary = {"input_count": len(inputs), **counts, "skipped": skipped, "done": not unknown}
json.dump(summary, open(out_dir + "/SUMMARY.json", "w"), indent=1, sort_keys=True)
print(json.dumps(summary, sort_keys=True))
