#!/usr/bin/env python3
"""Agreement of filter/udrhombus with the supervisor's prototype, research/unit-distance-23/tools/rhombus_probe.py.

Inputs: the supervisor's descent samples of TU-kept graphs of the real (23,65) tree, copied into
samples/ (w1 and w2 levels 13 to 18, and w3 when present; plus w1 level 19 made by make-level19.py).
For EVERY graph the verdict classes must be equal: pass = "none", refuted = "collision",
tu = "hidden-edge". The prototype is independent code (networkx, a reduced row echelon form mod
2^61 - 1 over all 4-cycles counted from both diagonals, full reduced vectors compared); the prover
deduplicates the cycles, keeps an echelon basis and compares null-space fingerprints before an exact
test. Both decide the rational question (Hadamard, see udrhombus.c), so a single disagreement is a bug.
Every certificate the prover writes is also replayed by the dev replay (dev_replay_rhombus.py) and
must be accepted, and the prover's statistics must report no certificate failure.

usage: agreement.py [FILE.g6 ...]   (default: every samples/*.g6)    needs networkx (pyenv-gp10)
"""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

import networkx as nx

from rhlib import HERE, REPO, g6_lines, log, replay, run_prover

sys.path.insert(0, str(REPO / "research" / "unit-distance-23" / "tools"))
from rhombus_probe import probe  # noqa: E402

CLASS = {"none": "pass", "collision": "refuted", "hidden-edge": "tu"}


def main() -> int:
    files = [Path(x) for x in sys.argv[1:]] or sorted((HERE / "samples").glob("*.g6"))
    problems: list[str] = []
    totals = collections.Counter()
    for f in files:
        lines = g6_lines(f)
        t0 = time.monotonic()
        records, stats, _ = run_prover(lines)
        t_prover = time.monotonic() - t0
        t0 = time.monotonic()
        proto = [CLASS[probe(nx.from_graph6_bytes(code.encode()))[0]] for code in lines]
        t_proto = time.monotonic() - t0
        mine = [r["verdict"] for r in records]
        disagree = [(code, a, b) for code, a, b in zip(lines, mine, proto) if a != b]
        rejected = []
        for code, r in zip(lines, records):
            if r["verdict"] != "pass":
                ok, why = replay(code, r)
                if not ok:
                    rejected.append((code, why))
        c = collections.Counter(mine)
        totals.update(c)
        totals["graphs"] += len(lines)
        totals["disagreements"] += len(disagree)
        totals["replay_rejections"] += len(rejected)
        log(f"{f.name}: {len(lines)} graphs; prover pass {c['pass']} refuted {c['refuted']} tu {c['tu']}; "
            f"prototype identical on {len(lines) - len(disagree)}; certificates replayed {c['refuted'] + c['tu']}, "
            f"rejected {len(rejected)}; certificate failures {stats.get('certificate_failures')}; "
            f"seconds prover {t_prover:.2f} prototype {t_proto:.1f}")
        for code, a, b in disagree[:20]:
            log(f"  DISAGREE {code}: prover {a}, prototype {b}")
            problems.append(f"{f.name}: {code} prover {a} prototype {b}")
        for code, why in rejected[:20]:
            log(f"  REPLAY REJECTS {code}: {why}")
            problems.append(f"{f.name}: replay rejects {code}")
        if stats.get("certificate_failures"):
            problems.append(f"{f.name}: {stats['certificate_failures']} certificate failures")
    log(f"TOTAL {json.dumps(dict(totals))}")
    log("AGREEMENT", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
