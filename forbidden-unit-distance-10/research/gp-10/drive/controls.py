"""Run the registered B8' and B9' GP-10 controls in separate directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from .driver import PYTHON_DEFAULT, _parse_limits, run_pipeline
    from .graph6 import contains_subgraph, decode_graph6, load_graph6, save_graph6
except ImportError:
    from driver import PYTHON_DEFAULT, _parse_limits, run_pipeline  # type: ignore
    from graph6 import contains_subgraph, decode_graph6, load_graph6, save_graph6  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_JSON = ROOT.parent / "unit-distance-22" / "data" / "forbidden-74.json"
FORBIDDEN_G6 = ROOT.parent / "unit-distance-22" / "data" / "forbidden-74.g6"


def _read_forbidden_edges() -> list[list[list[int]]]:
    return json.loads(FORBIDDEN_JSON.read_text(encoding="utf-8"))


def _force_for_order(order: int) -> tuple[list[list[list[int]]], list[str]]:
    all_edges = _read_forbidden_edges()
    force_edges = []
    for edges in all_edges:
        maximum = max((max(pair) for pair in edges), default=-1) + 1
        if maximum <= order - 1:
            force_edges.append(edges)
    if force_edges != all_edges[:len(force_edges)]:
        raise ValueError('list in force is not the required F9 prefix')
    frozen_g6 = [graph for graph in load_graph6(FORBIDDEN_G6) if decode_graph6(graph)[0] <= order - 1]
    return force_edges, frozen_g6


def _expected_order(order: int) -> list[str]:
    return [graph for graph in load_graph6(FORBIDDEN_G6) if decode_graph6(graph)[0] == order]


def _run_one(
    label: str,
    input_path: Path,
    order: int,
    root: Path,
    embedder: str,
    refuter: str,
    python: str,
    limits: list[float],
    processes: int,
    resume: bool,
    embedder_extra: list[str],
    refuter_extra: list[str],
    exhaustive_fallback: bool,
) -> tuple[bool, dict[str, object]]:
    run_dir = root / label
    run_dir.mkdir(parents=True, exist_ok=True)
    force_edges, force_g6 = _force_for_order(order)
    force_json = run_dir / "forbidden-in-force.json"
    force_g6_path = run_dir / "forbidden-in-force.g6"
    force_json.write_text(json.dumps(force_edges, separators=(",", ":")) + "\n", encoding="utf-8")
    save_graph6(force_g6_path, force_g6)
    summary = run_pipeline(
        input_path,
        run_dir,
        embedder,
        refuter,
        force_json,
        limits,
        workers=processes,
        python=python,
        resume=resume,
        forbidden_g6_path=force_g6_path,
        embedder_extra=embedder_extra,
        refuter_extra=refuter_extra,
        exhaustive_fallback=exhaustive_fallback,
    )
    records = {}
    records_path = run_dir / "records.jsonl"
    if records_path.exists():
        for line in records_path.read_text(encoding="utf-8").splitlines():
            if line:
                record = json.loads(line)
                records[record["g6"]] = record
    expected = set(_expected_order(order))
    actual = set(json.loads((run_dir / "MINIMALITY.json").read_text(encoding="utf-8"))["minimal_refuted"])
    f9_patterns = [
        graph
        for graph in load_graph6(FORBIDDEN_G6)
        if decode_graph6(graph)[0] <= order
    ]
    f9_forms = [decode_graph6(pattern) for pattern in f9_patterns]
    ffree = set()
    for graph in load_graph6(input_path):
        host_n, host_mask = decode_graph6(graph)
        if not any(
            contains_subgraph(pattern_n, pattern_mask, host_n, host_mask)
            for pattern_n, pattern_mask in f9_forms
        ):
            ffree.add(graph)
    ffree_embedded = all(records.get(graph, {}).get("verdict") == "embedded" for graph in ffree)
    passed = (
        summary.get("unknown_count") == 0
        and actual == expected
        and ffree_embedded
    )
    # The official checker derives the control list independently. The
    # driver's comparison never authorizes an official PASS by itself.
    manifest = {'profile': f'B{order}p', 'input': str(input_path.resolve()),
                'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
                'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6'}
    (run_dir / 'run.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    try:
        from .integration import invoke
    except ImportError:
        from integration import invoke
    checker_log = run_dir / 'checker.log'
    checker_status = invoke(ROOT / 'check' / 'gp10check.py', [str(run_dir)], checker_log)
    checker_lines = [line for line in checker_log.read_text().splitlines()
                     if line.startswith(('ACCEPT run ', 'REJECT run '))]
    final_line = checker_lines[-1] if checker_lines else 'no checker final line'
    passed = passed and checker_status == 0 and final_line == 'ACCEPT run verified'
    control = {
        "label": label,
        "order": order,
        "input_count": len(load_graph6(input_path)),
        "expected_minimal_count": len(expected),
        "actual_minimal_count": len(actual),
        "unknown_count": summary.get("unknown_count"),
        "all_nonminimal_graphs_embedded": ffree_embedded,
        "minimal_set_equal": actual == expected,
        "pass": passed,
        "checker_status": checker_status,
        "checker_final_line": final_line,
        "summary": summary,
    }
    (run_dir / "CONTROL.json").write_text(json.dumps(control, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (run_dir / "CONTROL.md").write_text(
        f"# {label}\n\n"
        f"PASS: {passed}\n\n"
        f"Input graphs: {control['input_count']}\n"
        f"Expected minimal graphs: {control['expected_minimal_count']}\n"
        f"Actual minimal graphs: {control['actual_minimal_count']}\n"
        f"Unknown graphs: {control['unknown_count']}\n"
        f"All F-free graphs embedded: {control['all_nonminimal_graphs_embedded']}\n",
        encoding="utf-8",
    )
    if not passed:
        (run_dir / 'LABNOTES.md').write_text(
            '# Control stopped\n\n' + final_line + '\n\n'
            'See UNKNOWN.g6, STATE.json attempt histories, and requests/*/producer.log '
            'for the outstanding evidence. This run does not authorize B10.\n')
    return passed, control


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", choices=("b8", "b9", "both"), default="both")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent / "controls")
    parser.add_argument("--embedder", default=str(ROOT / "embed" / "gp10embed.py"))
    parser.add_argument("--refuter", default=str(ROOT / "refute" / "gp10refute.py"))
    parser.add_argument("--python", default=PYTHON_DEFAULT)
    parser.add_argument("--time-limits", type=_parse_limits, default=[1.0, 5.0, 40.0])
    parser.add_argument("--processes", type=int, choices=(1,), default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--embedder-arg", action="append", default=[])
    parser.add_argument("--refuter-arg", action="append", default=[])
    parser.add_argument("--exhaustive-fallback", action="store_true")
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    jobs = []
    if args.control in {"b8", "both"}:
        jobs.append(("B8p-F7", ROOT / "data" / "B8p.g6", 8))
    if args.control in {"b9", "both"}:
        jobs.append(("B9p-F8", ROOT / "data" / "B9p.g6", 9))
    controls = []
    all_pass = True
    for label, input_path, order in jobs:
        passed, value = _run_one(
            label,
            input_path,
            order,
            args.root,
            args.embedder,
            args.refuter,
            args.python,
            args.time_limits,
            args.processes,
            args.resume,
            args.embedder_arg,
            args.refuter_arg,
            args.exhaustive_fallback,
        )
        controls.append(value)
        all_pass = all_pass and passed
        if not passed:
            break
    summary = {"pass": all_pass, "controls": controls}
    (args.root / "CONTROLS.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
