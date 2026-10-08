"""Resumable GP-10 poset driver.

The driver owns only orchestration.  It never trusts a producer's prose or
exit status as a verdict.  It accepts one well-formed record per requested
graph, propagates only the two contract pointer directions, and converts all
missing, malformed, crashed, or timed-out work into explicit unknown records.

The producer command lines are the interfaces from Brief D. Real producer CLI
entry points run in-process, with their own single worker, under the contract's
stricter memory cap. The default paths point at the sibling modules. Every
request uses fresh output paths because completed unknowns are durable in both
producers and cannot be retried by reusing an output file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from .aggregate import (
        AggregateError,
        read_jsonl,
        records_by_g6,
        validate_record_shape,
        write_aggregate,
    )
    from .graph6 import (
        load_graph6,
        save_graph6,
    )
    from .poset import Poset, build_poset, load_poset
except ImportError:
    from aggregate import (  # type: ignore
        AggregateError,
        read_jsonl,
        records_by_g6,
        validate_record_shape,
        write_aggregate,
    )
    from graph6 import (  # type: ignore
        load_graph6,
        save_graph6,
    )
    from poset import Poset, build_poset, load_poset  # type: ignore


PYTHON_DEFAULT = str(Path.home() / "tools" / "pyenv-gp10" / "bin" / "python")
ADDRESS_LIMIT = 1_000_000_000


@dataclass
class BatchResult:
    records: dict[str, dict[str, object]]
    unknown: dict[str, dict[str, object]]
    logs: list[str]


def _child_limits() -> None:
    """Apply the common child policy before exec."""

    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 15:
        os.nice(15 - current)
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = min(ADDRESS_LIMIT, hard) if hard != resource.RLIM_INFINITY else ADDRESS_LIMIT
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record_key(record: Mapping[str, object]) -> str:
    value = record.get("g6")
    return value if isinstance(value, str) else ""


def _unknown_detail(
    graph: str,
    reason: str,
    budget: float,
    kind: str,
    round_number: int,
    history: Mapping[str, object] | None = None,
) -> dict[str, object]:
    prior = []
    if history and isinstance(history.get("budget"), Mapping):
        prior.extend(history["budget"].get("history", []))
    prior.append({"kind": kind, "time_limit": budget, "round": round_number, "reason": reason})
    return {
        "reason": reason,
        "budget": {
            "producer": kind,
            "time_limit": budget,
            "round": round_number,
            "history": prior,
        },
    }


def _make_command(
    python: str,
    script: str,
    kind: str,
    input_path: Path,
    output_path: Path,
    unknown_path: Path,
    time_limit: float,
    forbidden: Path | None,
    known_refuted: Path | None,
    extra: Sequence[str] = (),
) -> list[str]:
    command = [python, script]
    if Path(script).name == "stub_producers.py":
        command.append(kind)
    command.extend(
        [
            str(input_path),
            "--out",
            str(output_path),
            "--unknown",
            str(unknown_path),
            "--time-limit",
            str(time_limit),
        ]
    )
    if kind == "refute":
        if forbidden is None:
            raise ValueError("refuter batches require an explicit forbidden-list path")
        command.extend(["--forbidden", str(forbidden)])
        if known_refuted is not None:
            command.extend(["--refuted", str(known_refuted)])
    command.extend(str(item) for item in extra)
    return command


def _write_known_refuted(path: Path, resolved: Mapping[str, Mapping[str, object]]) -> None:
    # The v1 loader only supports tree/tu/null/real, not driver sub pointers.
    # Keep a closed subset: omit any TU depending on an omitted record.
    supported = {g: r for g, r in resolved.items() if r.get("verdict") == "refuted"
                 and r.get("cert", {}).get("type") in {"tree", "tu", "null", "real"}}
    while True:
        missing = [g for g, r in supported.items()
                   if r['cert'].get('type') == 'tu'
                   and 'refuted' in r['cert'].get('end', {})
                   and r['cert']['end']['refuted'] not in supported]
        if not missing:
            break
        for graph in missing:
            del supported[graph]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for graph in sorted(supported):
            handle.write(json.dumps(supported[graph], sort_keys=True, separators=(",", ":")) + "\n")


def _parse_batch_records(
    kind: str,
    requested: Sequence[str],
    output_path: Path,
    returncode: int | None,
    time_limit: float,
    round_number: int,
    previous_unknown: Mapping[str, Mapping[str, object]],
) -> BatchResult:
    records: dict[str, dict[str, object]] = {}
    unknown: dict[str, dict[str, object]] = {}
    requested_set = set(requested)
    try:
        raw_records = read_jsonl(output_path) if output_path.exists() else []
    except Exception as exc:
        raw_records = []
        parse_failure = f"producer output could not be parsed: {type(exc).__name__}: {exc}"
    else:
        parse_failure = ""
    duplicate: set[str] = set()
    seen: set[str] = set()
    for raw in raw_records:
        valid, reason = validate_record_shape(raw)
        graph = _record_key(raw)
        if graph in requested_set:
            if graph in seen:
                duplicate.add(graph)
                records.pop(graph, None)
                continue
            seen.add(graph)
        if not valid:
            if graph in requested_set:
                unknown[graph] = _unknown_detail(
                    graph, f"malformed producer record: {reason}", time_limit, kind, round_number,
                    previous_unknown.get(graph),
                )
            continue
        if graph not in requested_set:
            continue
        verdict = raw["verdict"]
        if kind == "embed" and verdict not in {"embedded", "unknown"}:
            unknown[graph] = _unknown_detail(
                graph, f"embedder returned unsupported verdict {verdict!r}", time_limit, kind, round_number,
                previous_unknown.get(graph),
            )
        elif kind == "refute" and verdict not in {"refuted", "unknown"}:
            unknown[graph] = _unknown_detail(
                graph, f"refuter returned unsupported verdict {verdict!r}", time_limit, kind, round_number,
                previous_unknown.get(graph),
            )
        elif verdict == "unknown":
            cert = raw["cert"]
            reason_value = cert.get("reason") if isinstance(cert, Mapping) else None
            unknown[graph] = _unknown_detail(
                graph,
                str(reason_value or "producer returned unknown"),
                time_limit,
                kind,
                round_number,
                previous_unknown.get(graph),
            )
            unknown[graph]['budget']['producer_budget'] = dict(cert.get('budget', {}))
            unknown[graph]['budget']['history'][-1]['producer_budget'] = dict(cert.get('budget', {}))
        else:
            records[graph] = dict(raw)
    for graph in duplicate:
        unknown[graph] = _unknown_detail(
            graph, "producer returned duplicate records", time_limit, kind, round_number,
            previous_unknown.get(graph),
        )
    for graph in requested:
        if graph in records or graph in unknown:
            continue
        reason = parse_failure or (
            f"producer exited with status {returncode}" if returncode not in (None, 0) else "producer omitted graph"
        )
        unknown[graph] = _unknown_detail(
            graph, reason, time_limit, kind, round_number, previous_unknown.get(graph)
        )
    return BatchResult(records, unknown, [str(output_path)])


def _run_batches(
    kind: str,
    graphs: Sequence[str],
    round_number: int,
    time_limit: float,
    run_dir: Path,
    workers: int,
    python: str,
    script: str,
    forbidden: Path | None,
    resolved: Mapping[str, Mapping[str, object]],
    previous_unknown: Mapping[str, Mapping[str, object]],
    extra: Sequence[str] = (),
) -> BatchResult:
    if not graphs:
        return BatchResult({}, {}, [])
    if Path(script).name in {'gp10embed.py', 'gp10refute.py'}:
        if workers != 1:
            raise ValueError('real producers require --processes 1: each has its own worker')
        try:
            from .integration import invoke
        except ImportError:
            from integration import invoke
        combined = BatchResult({}, {}, [])
        # Each shard is a stated sample with at most 240 seconds of search
        # budget. The full control is streamed through consecutive samples.
        size = max(1, min(32, int(240 / time_limit)))
        request_dir = run_dir / 'requests'
        request_dir.mkdir(parents=True, exist_ok=True)
        import tempfile
        for start in range(0, len(graphs), size):
            chunk = list(graphs[start:start + size])
            job = Path(tempfile.mkdtemp(prefix=f'{kind}-round-{round_number:03d}-', dir=request_dir))
            save_graph6(job / 'input.g6', chunk)
            _write_known_refuted(job / 'known-refuted.jsonl', resolved)
            command = _make_command(python, script, kind, job / 'input.g6',
                                    job / 'records.jsonl', job / 'unknown.g6', time_limit,
                                    forbidden, job / 'known-refuted.jsonl' if kind == 'refute' else None, extra)
            _atomic_json(job / 'command.json', {'command': command, 'sample_count': len(chunk)})
            print(json.dumps({'event': 'producer-start', 'kind': kind, 'budget': time_limit,
                              'sample_count': len(chunk), 'request': str(job)}), flush=True)
            status = invoke(script, command[2:], job / 'producer.log')
            result = _parse_batch_records(kind, chunk, job / 'records.jsonl', status,
                                          time_limit, round_number, previous_unknown)
            combined.records.update(result.records)
            combined.unknown.update(result.unknown)
            combined.logs.append(str(job / 'producer.log'))
            print(json.dumps({'event': 'producer-finished', 'kind': kind, 'status': status,
                              'resolved': len(result.records), 'unknown': len(result.unknown)}), flush=True)
            if status:
                # Keep the full original stderr and also attach it to the
                # unknown evidence. Exit 2 need not mean argparse failed.
                diagnostic = (job / 'producer.log').read_text()[-8000:]
                for detail in result.unknown.values():
                    detail['budget']['producer_log'] = str(job / 'producer.log')
                    detail['budget']['stderr_tail'] = diagnostic
        return combined
    workers = max(1, min(2, int(workers)))
    import tempfile
    request_root = run_dir / 'requests'
    request_root.mkdir(parents=True, exist_ok=True)
    request_dir = Path(tempfile.mkdtemp(prefix=f'{kind}-round-{round_number:03d}-', dir=request_root))
    log_dir = request_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    chunk_count = min(workers, len(graphs))
    chunk_size = math.ceil(len(graphs) / chunk_count)
    chunks = [list(graphs[start : start + chunk_size]) for start in range(0, len(graphs), chunk_size)]
    known_refuted = request_dir / "known-refuted.jsonl"
    _write_known_refuted(known_refuted, resolved)
    pending: list[tuple[int, list[str]]] = list(enumerate(chunks))
    active: dict[int, tuple[subprocess.Popen[bytes], object, Path, Path, list[str]]] = {}
    completed: list[BatchResult] = []

    def launch(index: int, chunk: list[str]) -> None:
        stem = f"{kind}-round-{round_number:03d}-part-{index:03d}"
        input_path = request_dir / f"{stem}.g6"
        output_path = request_dir / f"{stem}.jsonl"
        unknown_path = request_dir / f"{stem}.unknown.g6"
        save_graph6(input_path, chunk)
        command = _make_command(
            python,
            script,
            kind,
            input_path,
            output_path,
            unknown_path,
            time_limit,
            forbidden,
            known_refuted if kind == "refute" else None,
            extra,
        )
        log_path = log_dir / f"{stem}.log"
        log_handle = log_path.open("wb")
        try:
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=_child_limits,
            )
        except Exception:
            log_handle.close()
            raise
        active[index] = (process, log_handle, output_path, unknown_path, chunk)

    while pending or active:
        while pending and len(active) < workers:
            index, chunk = pending.pop(0)
            launch(index, chunk)
        if not active:
            continue
        index = sorted(active)[0]
        process, log_handle, output_path, unknown_path, chunk = active.pop(index)
        returncode = process.wait()
        log_handle.close()
        completed.append(
            _parse_batch_records(
                kind,
                chunk,
                output_path,
                returncode,
                time_limit,
                round_number,
                previous_unknown,
            )
        )

    combined_records: dict[str, dict[str, object]] = {}
    combined_unknown: dict[str, dict[str, object]] = {}
    logs: list[str] = []
    for result in completed:
        logs.extend(result.logs)
        for graph, record in result.records.items():
            if graph in combined_records:
                combined_unknown[graph] = _unknown_detail(
                    graph, "graph appeared in multiple producer batches", time_limit, kind, round_number,
                    previous_unknown.get(graph),
                )
                combined_records.pop(graph, None)
            else:
                combined_records[graph] = record
        combined_unknown.update(result.unknown)
    for graph in list(combined_unknown):
        combined_records.pop(graph, None)
    return BatchResult(combined_records, combined_unknown, logs)


def _resolved_count(resolved: Mapping[str, Mapping[str, object]]) -> int:
    return len(resolved)


def _drop_resolved_unknowns(
    resolved: Mapping[str, Mapping[str, object]], unknown: dict[str, dict[str, object]]
) -> None:
    for graph in list(unknown):
        if graph in resolved:
            unknown.pop(graph, None)


def _propagate(poset: Poset, resolved: dict[str, dict[str, object]]) -> int:
    """Propagate accepted embedded/refuted records over all cover relations."""

    changed = 0
    embedded_queue = [graph for graph, record in resolved.items() if record.get("verdict") == "embedded"]
    refuted_queue = [graph for graph, record in resolved.items() if record.get("verdict") == "refuted"]
    seen_embedded: set[str] = set()
    seen_refuted: set[str] = set()

    while embedded_queue or refuted_queue:
        if embedded_queue:
            parent = embedded_queue.pop()
            if parent in seen_embedded:
                continue
            seen_embedded.add(parent)
            for relation in poset.children.get(parent, ()):
                child = relation.child
                pointer = {
                    "g6": child,
                    "verdict": "embedded",
                    "cert": {
                        "type": "super",
                        "g6": parent,
                        "map": list(relation.map),
                    },
                }
                if child in resolved:
                    existing = resolved[child]
                    if existing.get("verdict") == "refuted":
                        raise AggregateError(f"graph {child} is both embedded and refuted")
                else:
                    resolved[child] = pointer
                    changed += 1
                    embedded_queue.append(child)
        else:
            child = refuted_queue.pop()
            if child in seen_refuted:
                continue
            seen_refuted.add(child)
            for relation in poset.parents.get(child, ()):
                parent = relation.parent
                pointer = {
                    "g6": parent,
                    "verdict": "refuted",
                    "cert": {
                        "type": "sub",
                        "g6": child,
                        "map": list(relation.map),
                    },
                }
                if parent in resolved:
                    existing = resolved[parent]
                    if existing.get("verdict") == "embedded":
                        raise AggregateError(f"graph {parent} is both embedded and refuted")
                else:
                    resolved[parent] = pointer
                    changed += 1
                    refuted_queue.append(parent)
    return changed


def _state_value(
    input_g6: Sequence[str],
    resolved: Mapping[str, Mapping[str, object]],
    unknown: Mapping[str, Mapping[str, object]],
    next_limit_index: int,
    finished: bool = False,
) -> dict[str, object]:
    return {
        "schema": 1,
        "input_sha256": hashlib.sha256(("\n".join(input_g6) + "\n").encode("ascii")).hexdigest(),
        "input_count": len(input_g6),
        "resolved": {graph: resolved[graph] for graph in sorted(resolved)},
        "unknown": {graph: unknown[graph] for graph in sorted(unknown)},
        "next_limit_index": next_limit_index,
        "finished": finished,
    }


def _load_state(path: Path, input_g6: Sequence[str]) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], int, bool]:
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = hashlib.sha256(("\n".join(input_g6) + "\n").encode("ascii")).hexdigest()
    if value.get("schema") != 1 or value.get("input_sha256") != expected:
        raise AggregateError("state file does not match the current input")
    resolved = {str(graph): dict(record) for graph, record in value.get("resolved", {}).items()}
    unknown = {str(graph): dict(detail) for graph, detail in value.get("unknown", {}).items()}
    return resolved, unknown, int(value.get("next_limit_index", 0)), bool(value.get("finished", False))


def run_pipeline(
    input_path: str | Path,
    run_dir: str | Path,
    embedder: str,
    refuter: str,
    forbidden: str | Path | None,
    time_limits: Sequence[float],
    workers: int = 1,
    python: str = PYTHON_DEFAULT,
    poset_path: str | Path | None = None,
    resume: bool = False,
    hosts_path: str | Path | None = None,
    forbidden_g6_path: str | Path | None = None,
    embedder_extra: Sequence[str] = (),
    refuter_extra: Sequence[str] = (),
    exhaustive_fallback: bool = False,
    seed_paths: Sequence[str | Path] = (),
    validate_seeds: bool = False,
    no_producers: bool = False,
    seed_sample_size: int = 128,
    profile: str = 'sample',
    derive: bool = False,
) -> dict[str, object]:
    """Run the staged pipeline and write its final aggregate."""

    if not no_producers and (not time_limits or any(float(value) <= 0 for value in time_limits)):
        raise ValueError("time_limits must be positive and nonempty")
    workers = int(workers)
    if workers not in {1, 2}:
        raise ValueError("GP-10 permits one or two producer processes")
    input_g6 = load_graph6(input_path)
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    state_path = run / "STATE.json"
    chosen_poset_path = Path(poset_path) if poset_path else run / "poset.json"
    if chosen_poset_path.exists():
        poset = load_poset(chosen_poset_path)
        if tuple(poset.vertices) != tuple(input_g6):
            raise AggregateError("poset vertices do not equal pipeline input")
    else:
        poset = build_poset(input_g6, progress_every=1000)
        poset.write(chosen_poset_path)
    hosts = {}
    if resume and hosts_path is None and (run / 'hosts.jsonl').exists():
        hosts_path = run / 'hosts.jsonl'
    if hosts_path:
        hosts = records_by_g6(read_jsonl(hosts_path))
    forbidden_path = Path(forbidden) if forbidden else run / "empty-forbidden.json"
    if not forbidden_path.exists():
        if forbidden is not None:
            raise FileNotFoundError(forbidden_path)
        forbidden_path.write_text("[]\n", encoding="utf-8")
    full_list_path = Path(__file__).resolve().parents[2] / 'unit-distance-22' / 'data' / 'forbidden-74.json'
    full_list = json.loads(full_list_path.read_text())
    selected_list = json.loads(forbidden_path.read_text())
    if not isinstance(selected_list, list) or selected_list != full_list[:len(selected_list)]:
        raise ValueError('forbidden list must be a prefix of forbidden-74.json (amendment 4)')
    forbidden_g6 = (load_graph6(forbidden_g6_path) if forbidden_g6_path else
                    load_graph6(full_list_path.with_suffix('.g6'))[:len(selected_list)])

    resolved: dict[str, dict[str, object]] = {}
    unknown: dict[str, dict[str, object]] = {}
    next_limit = 0
    finished = False
    if resume and state_path.exists():
        resolved, unknown, next_limit, finished = _load_state(state_path, input_g6)
        if finished:
            summary_path = run / "SUMMARY.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            if summary.get("unknown_count", 0) == 0 and not seed_paths and not no_producers:
                return summary
            # A covered run can still be resumed with a longer or different
            # budget schedule.  Keep accepted records and retry unresolved
            # graphs from the first configured budget.
            next_limit = 0
            finished = False
    try:
        from .seeds import forbidden_limit, load_seeds
        from .runfiles import write_manifests
    except ImportError:
        from seeds import forbidden_limit, load_seeds
        from runfiles import write_manifests
    seed_bytes = {}
    if resume and (run / 'records.jsonl').exists():
        with (run / 'records.jsonl').open('rb') as stream:
            for raw in stream:
                row = json.loads(raw)
                if row == resolved.get(row.get('g6')):
                    seed_bytes[row['g6']] = raw
    if seed_paths:
        if set(hosts) & set(input_g6):
            raise AggregateError('host/input overlap')
        paths = [*seed_paths, *([hosts_path] if hosts_path else [])]
        seed_records, seed_hosts, seed_report = load_seeds(
            paths, input_g6, run, forbidden_limit(selected_list), validate_seeds, seed_sample_size)
        # Explicit seeds take precedence over resume state for their graphs.
        # Later duplicate seed lines never overwrite the first selection.
        resolved.update({g: s.record() for g, s in seed_records.items()})
        seed_bytes.update({g: s.raw for g, s in seed_records.items()})
        hosts.update({g: s.record() for g, s in seed_hosts.items()})
        with (run / 'hosts.jsonl').open('wb') as output:
            for graph in sorted(hosts):
                raw = seed_hosts[graph].raw if graph in seed_hosts else (
                    json.dumps(hosts[graph], sort_keys=True) + '\n').encode()
                output.write(raw)
    elif hosts:
        with (run / 'hosts.jsonl').open('w') as output:
            for graph in sorted(hosts):
                output.write(json.dumps(hosts[graph], sort_keys=True) + '\n')
    _propagate(poset, resolved)
    _drop_resolved_unknowns(resolved, unknown)
    _atomic_json(state_path, _state_value(input_g6, resolved, unknown, next_limit))

    for limit_index in ([] if no_producers else range(next_limit, len(time_limits))):
        budget = float(time_limits[limit_index])
        round_number = limit_index
        attempted_embed: set[str] = set()
        attempted_refute: set[str] = set()
        while True:
            unresolved = set(poset.vertices) - set(resolved)
            if not unresolved:
                break
            progress = False
            # Failed graphs leave this budget's frontier. Their undecided
            # subgraphs must still get an embedding attempt.
            maxima = poset.maximal(unresolved - attempted_embed)
            if maxima:
                attempted_embed.update(maxima)
                result = _run_batches(
                    "embed",
                    maxima,
                    round_number,
                    budget,
                    run,
                    workers,
                    python,
                    embedder,
                    forbidden_path,
                    resolved,
                    unknown,
                    embedder_extra,
                )
                for graph, record in result.records.items():
                    if graph in resolved and resolved[graph].get("verdict") != record.get("verdict"):
                        raise AggregateError(f"graph {graph} got conflicting producer verdicts")
                    resolved[graph] = record
                    unknown.pop(graph, None)
                    progress = True
                for graph, detail in result.unknown.items():
                    if graph not in resolved:
                        unknown[graph] = detail
                if _propagate(poset, resolved):
                    progress = True
                _drop_resolved_unknowns(resolved, unknown)
                _atomic_json(state_path, _state_value(input_g6, resolved, unknown, limit_index))
                continue

            unresolved = set(poset.vertices) - set(resolved)
            # A failed minimal graph must not hide its supergraphs. Proving a
            # refutation does not require proving minimality first; the latter
            # is independently derived by the aggregator and official checker.
            minima = poset.minimal(unresolved - attempted_refute)
            if minima:
                attempted_refute.update(minima)
                result = _run_batches(
                    "refute",
                    minima,
                    round_number,
                    budget,
                    run,
                    workers,
                    python,
                    refuter,
                    forbidden_path,
                    resolved,
                    unknown,
                    refuter_extra,
                )
                for graph, record in result.records.items():
                    if graph in resolved and resolved[graph].get("verdict") != record.get("verdict"):
                        raise AggregateError(f"graph {graph} got conflicting producer verdicts")
                    resolved[graph] = record
                    unknown.pop(graph, None)
                    progress = True
                for graph, detail in result.unknown.items():
                    if graph not in resolved:
                        unknown[graph] = detail
                if _propagate(poset, resolved):
                    progress = True
                _drop_resolved_unknowns(resolved, unknown)
                _atomic_json(state_path, _state_value(input_g6, resolved, unknown, limit_index))
                continue
            if exhaustive_fallback:
                unresolved = set(poset.vertices) - set(resolved)
                fallback = [graph for graph in sorted(unresolved) if graph not in attempted_embed]
                if fallback:
                    attempted_embed.update(fallback)
                    result = _run_batches(
                        "embed",
                        fallback,
                        round_number,
                        budget,
                        run,
                        workers,
                        python,
                        embedder,
                        forbidden_path,
                        resolved,
                        unknown,
                        embedder_extra,
                    )
                    for graph, record in result.records.items():
                        if graph in resolved and resolved[graph].get("verdict") != record.get("verdict"):
                            raise AggregateError(f"graph {graph} got conflicting producer verdicts")
                        resolved[graph] = record
                        unknown.pop(graph, None)
                        progress = True
                    for graph, detail in result.unknown.items():
                        if graph not in resolved:
                            unknown[graph] = detail
                    if _propagate(poset, resolved):
                        progress = True
                    _drop_resolved_unknowns(resolved, unknown)
                    _atomic_json(state_path, _state_value(input_g6, resolved, unknown, limit_index))
                    if progress:
                        continue
            if not progress:
                break
        next_limit = limit_index + 1
        _atomic_json(state_path, _state_value(input_g6, resolved, unknown, next_limit))
        if len(resolved) == len(poset.vertices):
            break

    for graph in poset.vertices:
        if graph not in resolved and graph not in unknown:
            unknown[graph] = {
                "reason": "assembly only: no seed or monotone consequence" if no_producers else "all configured budgets exhausted",
                "budget": {'no_producers': True} if no_producers else {"time_limits": [float(value) for value in time_limits]},
            }
    _atomic_json(state_path, _state_value(input_g6, resolved, unknown, len(time_limits), finished=False))
    summary = write_aggregate(
        input_g6,
        resolved,
        unknown,
        run,
        poset,
        hosts=hosts,
        forbidden_g6=forbidden_g6,
        verbatim=seed_bytes,
    )
    _atomic_json(state_path, _state_value(input_g6, resolved, unknown, len(time_limits), finished=True))
    if no_producers or seed_paths:
        write_manifests(run, input_path, forbidden_limit(selected_list), profile, derive)
    return summary


def _parse_limits(value: str) -> list[float]:
    result = [float(part.strip()) for part in value.split(",") if part.strip()]
    if not result or any(item <= 0 for item in result):
        raise argparse.ArgumentTypeError("time limits must be positive comma-separated numbers")
    return result


def _cli(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--embedder", default="research/gp-10/embed/gp10embed.py")
    parser.add_argument("--refuter", default="research/gp-10/refute/gp10refute.py")
    parser.add_argument("--forbidden", type=Path)
    parser.add_argument("--forbidden-g6", type=Path)
    parser.add_argument("--hosts", type=Path)
    parser.add_argument("--poset", type=Path)
    parser.add_argument("--python", default=PYTHON_DEFAULT)
    parser.add_argument("--time-limits", type=_parse_limits, default=[1.0, 5.0, 30.0, 120.0])
    parser.add_argument("--processes", type=int, choices=(1, 2), default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--embedder-arg", action="append", default=[])
    parser.add_argument("--refuter-arg", action="append", default=[])
    parser.add_argument("--exhaustive-fallback", action="store_true")
    parser.add_argument('--seed', action='append', type=Path, default=[])
    parser.add_argument('--validate-seeds', action='store_true')
    parser.add_argument('--no-producers', action='store_true')
    parser.add_argument('--seed-sample-size', type=int, default=128)
    parser.add_argument('--profile', choices=('sample', 'B10'), default='sample')
    parser.add_argument('--derive', action='store_true')
    args = parser.parse_args(argv)
    summary = run_pipeline(
        args.input,
        args.run_dir,
        args.embedder,
        args.refuter,
        args.forbidden,
        args.time_limits,
        workers=args.processes,
        python=args.python,
        poset_path=args.poset,
        resume=args.resume,
        hosts_path=args.hosts,
        forbidden_g6_path=args.forbidden_g6,
        embedder_extra=args.embedder_arg,
        refuter_extra=args.refuter_arg,
        exhaustive_fallback=args.exhaustive_fallback,
        seed_paths=args.seed,
        validate_seeds=args.validate_seeds,
        no_producers=args.no_producers,
        seed_sample_size=args.seed_sample_size,
        profile=args.profile,
        derive=args.derive,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
