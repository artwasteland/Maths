#!/usr/bin/env python3
"""Valid shards can offer short circular alternatives and longer grounded proofs."""
from common import *
import argparse
import subprocess
from graph6 import canonicalize, decode_graph6, pair_index
from poset import Poset
from store import Store
from tu import TU


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    limits(args.output / "scratch")
    guard = Guard()
    guard.start()
    poset = Poset(args.index)
    tu = TU(poset)
    for code in (GP11 / "design/prototypes/tu-all-refuted.g6").read_text().splitlines():
        chain = tu.closure(code)
        if len(chain["steps"]) < 2:
            continue
        n, mask = decode_graph6(code)
        steps = chain["steps"][:1]
        endpoint = canonicalize(n, mask | 1 << pair_index(n, *steps[0]["pair"]))
        if endpoint.g6 in poset.ids:
            break
    else:
        raise AssertionError("no_real_two_step_fixture")
    store = Store(args.output / "fixture", poset, [poset.ids[code], poset.ids[endpoint.g6]],
                  {"policy": "cycle_fixture"}, guard)
    original, _ = tu.propose(code, store)
    store.accept(original, "fixture")
    direct, _ = tu.propose(endpoint.g6, store)
    store.accept(direct, "fixture")
    prefix = {"g6": endpoint.g6, "old_to_new": list(endpoint.old_to_new), "steps": steps}
    chain_to_endpoint = tu.transport(code, prefix, store)
    pointer_to_parent = {"g6": endpoint.g6, "verdict": "refuted", "cert": {
        "type": "sub", "g6": code, "map": list(endpoint.old_to_new)}}
    store.verify(chain_to_endpoint)
    store.verify(pointer_to_parent)
    assert len(compact(chain_to_endpoint)) < len(compact(original))
    assert len(compact(pointer_to_parent)) < len(compact(direct))
    support = [store.read(value) for target, value in store.db.execute("SELECT g6,hash FROM accepted ORDER BY seq")
               if target not in (code, endpoint.g6)]
    store.close()
    definitions = {"left": ([code], support + [direct, chain_to_endpoint]),
                   "right": ([endpoint.g6], support + [original, pointer_to_parent]),
                   "cycle": ([code, endpoint.g6], support + [chain_to_endpoint, pointer_to_parent])}
    for name, (codes, records) in definitions.items():
        atomic(args.output / (name + ".g6"), "".join(c + "\n" for c in sorted(codes)))
        atomic(args.output / (name + ".jsonl"), "".join(compact(row) + "\n" for row in records))
    atomic(args.output / "merged.g6", "".join(c + "\n" for c in sorted((code, endpoint.g6))))

    def run(name, extra, expected=None):
        source = name if name in definitions else "merged"
        command = [sys.executable, "-B", str(HERE / "drive.py"), "run", "--index", str(args.index),
                   "--state", str(args.output / (name + "-state")),
                   "--output", str(args.output / (name + "-result")),
                   "--input", str(args.output / (source + ".g6")), "--policy", "cheap", "--intake-only"] + extra
        log_path = args.output / (name + ".log")
        with log_path.open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=log)
        if expected:
            assert process.returncode != 0 and expected in log_path.read_text(), log_path.read_text()
            return
        assert process.returncode == 0, log_path.read_text()
        report = json.loads((args.output / (name + "-result/summary.json")).read_text())
        assert report["checker_status"] == "ACCEPT"
        return report["counts"]

    for name in ("left", "right"):
        assert run(name, ["--records", str(args.output / (name + ".jsonl"))]) == {"embedded": 0, "refuted": 1, "unknown": 0}
    bundles = ["--bundle", str(args.output / "left-result"), "--bundle", str(args.output / "right-result")]
    assert run("merged", bundles) == {"embedded": 0, "refuted": 2, "unknown": 0}
    run("cycle", ["--records", str(args.output / "cycle.jsonl")], "intake_dependency_cycle")
    assert run("positive-after", bundles) == {"embedded": 0, "refuted": 2, "unknown": 0}
    result = {"status": "PASS", "graphs": [code, endpoint.g6], "individual_shards": "ACCEPT",
              "shortest_alternatives_form_cycle": True, "grounded_merge": "ACCEPT",
              "unanchored_cycle": "intake_dependency_cycle", "positive_after": "ACCEPT"}
    write_json(args.output / "merge-cycles.json", result)
    print(compact(result))
    guard.stop.set()


if __name__ == "__main__":
    main()
