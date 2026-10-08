#!/usr/bin/env python3
"""Exercise the chain checker's nonempty order-24 replay and its TU target bound.

The tiny chain is a synthetic seed-23 fixture, not an enumeration or a production slice.
Only manifests and one augmentation are constructed; no enumeration is started.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import evidence

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nonempty24"
spec = importlib.util.spec_from_file_location("chain_fixture", evidence.CHECKER)
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)


def encode(n, edges):
    bits = "".join("1" if (i, j) in edges else "0" for j in range(1, n) for i in range(j))
    bits += "0" * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(63 + int(bits[i:i + 6], 2)) for i in range(0, len(bits), 6))


def edges_of(code):
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    pairs = [(i, j) for j in range(ord(code[0]) - 63) for i in range(j)]
    return {p for p, bit in zip(pairs, bits) if bit == "1"}


def make_fixture(run, target=69):
    run.mkdir()
    record = evidence.load(FIXTURE / f"24-{target}.certs.jsonl")
    edges = edges_of(record["g6"])
    windows = chain.schade_windows(24, target, 23, chain.UBAR_BUILTIN)
    vertices = [sum(v in e for e in edges) for v in range(24)]
    deleted = min(range(24), key=lambda v: vertices[v])
    rest = [v for v in range(24) if v != deleted]
    rank = {v: i for i, v in enumerate(rest)}
    parent_edges = {tuple(sorted((rank[a], rank[b]))) for a, b in edges if deleted not in (a, b)}
    pm = len(parent_edges)
    assert windows[23][0] <= pm <= windows[23][1]
    def dump(name, value):
        (run / name).write_text(json.dumps(value) + "\n")
    forbidden = evidence.CHECKER.parent.parent / "data/forbidden-74.json"
    inputs = {str(forbidden): evidence.sha(forbidden)}
    levels, sources = [], []
    for m in range(windows[23][0], windows[23][1] + 1):
        name = f"23-{m}.g6"
        (run / name).write_text(encode(23, parent_edges) + "\n" if m == pm else "")
        dump(f"23-{m}.manifest.json", {"exit_status": 0, "inputs_sha256": inputs,
                                       "children_file_sha256": evidence.sha(run / name)})
        sources.append({"level": [23, m], "kind": "full", "file": str(run / name),
                        "sha256": evidence.sha(run / name), "records": int(m == pm)})
        levels.append({"n": 23, "m": m, "kind": "seed", "children": int(m == pm)})
    cell = f"24-{target}"
    (run / (cell + ".g6")).write_text(record["g6"] + "\n")
    dump(cell + ".certs.jsonl", record)
    for suffix in (".UNKNOWN.g6", ".keep.g6"):
        (run / (cell + suffix)).touch()
    parents = run / "_parents" / (cell + ".g6")
    parents.parent.mkdir()
    parents.write_text(encode(23, parent_edges) + "\n")
    inputs = {**inputs, str(parents): evidence.sha(parents)}
    manifest = {"exit_status": 0, "inputs_sha256": inputs, "parent_file": str(parents),
                "parent_range": [0, 1], "children_file_sha256": evidence.sha(run / (cell + ".g6")),
                "parent_sources": sources, "pruning": {}}
    dump(cell + ".manifest.json", manifest)
    shard = run / "shards" / cell
    shard.mkdir(parents=True)
    (shard / "0-1.manifest.json").write_text(json.dumps(manifest) + "\n")
    dump(cell + ".prune.manifest.json", {"exit_status": 0, "target": [24, target],
         "inputs_sha256": {**inputs, str(run / (cell + ".g6")): evidence.sha(run / (cell + ".g6"))},
         "outputs_sha256": {str(run / (cell + suffix)): evidence.sha(run / (cell + suffix))
                            for suffix in (".certs.jsonl", ".keep.g6", ".UNKNOWN.g6")}})
    levels.append({"n": 24, "m": target, "kind": "augmentation", "children": 1})
    dump("run-config.json", {"target": [24, target], "seed_n": 23, "reach": False, "prune": True, "prune_from": 24})
    dump("run-summary.json", {"target": [24, target], "seed_n": 23, "windows": windows, "completed_through_n": 24,
                              "prune": {"enabled": True, "prune_from": 24}, "levels": levels})


def check(run, target=69):
    p = subprocess.run([sys.executable, "-B", str(evidence.CHECKER), str(run), "--check",
                        "--expect-target", "24", str(target), "--expect-seed", "23"], text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def main():
    with tempfile.TemporaryDirectory(prefix="u24-certificate-") as tmp:
        run = Path(tmp) / "69"
        make_fixture(run)
        green = check(run)
        assert green[0] == 0 and green[1].splitlines()[-1] == "CHAIN OK", green
        assert json.loads(green[1].splitlines()[0])["certs_replayed"] == 1
        print("CERTIFICATE24 green: CHAIN OK; one nonempty 24-69 certificate file replayed")
        path = run / "24-69.certs.jsonl"
        original = path.read_text()
        record = json.loads(original)
        del record["witness"]
        path.write_text(json.dumps(record) + "\n")
        red = check(run)
        want = f"PROBLEM: 24-69.certs.jsonl: pruned graph {record['g6']} has no witness"
        assert red[0] == 1 and want in red[1].splitlines(), red
        print(want)
        path.write_text(original)
        assert check(run) == green
        lower = Path(tmp) / "68"
        make_fixture(lower, 68)
        red = check(lower, 68)
        want = "PROBLEM: 24-68.prune.manifest.json: tu records prune only at a target (N, M) with M >= u(N) proved; (24,68) is below the proved bound 69"
        assert red[0] == 1 and [s for s in red[1].splitlines() if s.startswith("PROBLEM:")] == [want], red
        print(want)
        assert check(run) == green
    print("CERTIFICATE24 OK: nonempty chain replay, missing witness and (24,68) refusal; clean chain restored after each")


if __name__ == "__main__":
    main()
