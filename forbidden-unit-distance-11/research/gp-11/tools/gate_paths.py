#!/usr/bin/env python3
"""Pre-write containment check for the G6 writer's gate file (G5 follow-up 0020, MINOR-2).

The writer (tools/write_result.py) resolves each gate's evidence path against RUN but does not refuse a path that
leaves RUN, such as an absolute or ../ path (the evidence digests still bind the bytes). The writer is pinned in the
frozen profile (b11_check.PINS), so it is not changed before publication. This check runs before the writer instead
and refuses any gate evidence path that does not resolve inside RUN, following symlinks.

Usage: gate_paths.py RUN GATES.json   (exit 0: every evidence path is inside RUN; 1: at least one is not)
"""
import json
from pathlib import Path
import sys


def uncontained(gates, run):
    """Every (gate, path) whose evidence path is missing, not a string, or resolves outside RUN."""
    run = Path(run).resolve()
    bad = []
    for name, gate in sorted(gates.items()):
        evidence = gate.get("evidence") if isinstance(gate, dict) else None
        # A gate without a nonempty evidence list fails closed here too (the writer also refuses it).
        for item in evidence if isinstance(evidence, list) and evidence else [None]:
            value = item.get("path") if isinstance(item, dict) else None
            if not isinstance(value, str) or not value or not (run / value).resolve().is_relative_to(run):
                bad.append((name, value))
    return bad


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    run, gates_path = args
    bad = uncontained(json.loads(Path(gates_path).read_text()), run)
    for name, value in bad:
        print(f"REJECT {name}: evidence path {value!r} is not inside RUN")
    if not bad:
        print("PASS every gate evidence path resolves inside RUN")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
