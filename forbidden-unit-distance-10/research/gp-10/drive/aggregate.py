"""Strict GP-10 record aggregation and the driver's minimality report.

The official checker is intentionally independent of this module.  The
aggregator therefore checks only producer-neutral invariants: exact coverage,
record shape, pointer direction, pointer acyclicity, and the L-min edge
deletions used for the driver's comparison report.  It never treats a line
count as coverage.  A duplicate plus a missing graph is rejected even when
the two counts happen to agree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from .graph6 import (
        Graph6Error,
        canonical_g6,
        canonicalize,
        decode_graph6,
        edge_count,
        is_biconnected,
        iter_edges,
        load_graph6,
        map_edges,
        map_is_injective,
        remove_edge,
        save_graph6,
    )
    from .poset import Poset, build_poset, load_poset
except ImportError:
    from graph6 import (  # type: ignore
        Graph6Error,
        canonical_g6,
        canonicalize,
        decode_graph6,
        edge_count,
        is_biconnected,
        iter_edges,
        load_graph6,
        map_edges,
        map_is_injective,
        remove_edge,
        save_graph6,
    )
    from poset import Poset, build_poset, load_poset  # type: ignore


VERDICTS = frozenset({"embedded", "refuted", "unknown"})
RECORD_KEYS = frozenset({"g6", "verdict", "cert"})


class AggregateError(ValueError):
    """Raised when a run cannot be aggregated safely."""


def read_jsonl(path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AggregateError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise AggregateError(f"{path}:{line_number}: record is not an object")
            records.append(value)
    return records


def validate_record_shape(record: Mapping[str, object]) -> tuple[bool, str]:
    if frozenset(record) != RECORD_KEYS:
        return False, "record keys are not exactly g6, verdict, cert"
    g6 = record.get("g6")
    verdict = record.get("verdict")
    cert = record.get("cert")
    if not isinstance(g6, str):
        return False, "g6 is not a string"
    try:
        if canonical_g6(g6) != g6:
            return False, "g6 is not canonical"
    except Graph6Error as exc:
        return False, f"invalid g6: {exc}"
    if verdict not in VERDICTS:
        return False, f"unsupported verdict: {verdict!r}"
    if not isinstance(cert, dict):
        return False, "cert is not an object"
    if verdict == "unknown" and not isinstance(cert.get("reason"), str):
        return False, "unknown record has no string reason"
    if verdict == "unknown" and not isinstance(cert.get("budget"), dict):
        return False, "unknown record has no budget object"
    return True, "ok"


def coverage_errors(input_g6: Sequence[str], records: Sequence[Mapping[str, object]]) -> list[str]:
    """Return all exact-coverage errors, including duplicate/missing pairs."""

    input_list = [str(graph).strip() for graph in input_g6 if str(graph).strip()]
    input_counts: dict[str, int] = {}
    for graph in input_list:
        input_counts[graph] = input_counts.get(graph, 0) + 1
    record_g6: list[str] = []
    errors: list[str] = []
    for index, record in enumerate(records):
        valid, reason = validate_record_shape(record)
        if not valid:
            errors.append(f"record {index}: {reason}")
            continue
        record_g6.append(str(record["g6"]))
    record_counts: dict[str, int] = {}
    for graph in record_g6:
        record_counts[graph] = record_counts.get(graph, 0) + 1
    duplicate = sorted(graph for graph, count in record_counts.items() if count > 1)
    missing = sorted(graph for graph in input_counts if record_counts.get(graph, 0) == 0)
    extra = sorted(graph for graph in record_counts if graph not in input_counts)
    input_duplicate = sorted(graph for graph, count in input_counts.items() if count > 1)
    if input_duplicate:
        errors.append("input has duplicate g6 strings: " + ", ".join(input_duplicate))
    if duplicate:
        errors.append("records have duplicate g6 strings: " + ", ".join(duplicate))
    if missing:
        errors.append("records are missing g6 strings: " + ", ".join(missing))
    if extra:
        errors.append("records have extra g6 strings: " + ", ".join(extra))
    if len(record_g6) != len(input_list):
        errors.append(
            f"record count {len(record_g6)} differs from input count {len(input_list)}"
        )
    return errors


def done_by_set(input_g6: Sequence[str], recorded_g6: Sequence[str]) -> bool:
    """Return true only for a unique, exact set with matching multiplicities."""

    input_list = [str(item).strip() for item in input_g6 if str(item).strip()]
    recorded_list = [str(item).strip() for item in recorded_g6 if str(item).strip()]
    return (
        len(input_list) == len(recorded_list)
        and len(set(input_list)) == len(input_list)
        and len(set(recorded_list)) == len(recorded_list)
        and set(input_list) == set(recorded_list)
    )


def records_by_g6(records: Iterable[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for record in records:
        value = dict(record)
        valid, reason = validate_record_shape(value)
        if not valid:
            raise AggregateError(reason)
        graph = str(value["g6"])
        if graph in result:
            raise AggregateError(f"duplicate record for {graph}")
        result[graph] = value
    return result


def _pointer_target(
    graph: str,
    record: Mapping[str, object],
    records: Mapping[str, Mapping[str, object]],
    hosts: Mapping[str, Mapping[str, object]],
    forbidden_g6: set[str],
) -> tuple[str, Mapping[str, object]] | None:
    cert = record["cert"]
    assert isinstance(cert, Mapping)
    cert_type = cert.get("type")
    if record["verdict"] == "embedded" and cert_type == "super":
        target = cert.get("g6")
        if not isinstance(target, str):
            raise AggregateError(f"{graph}: E-ptr target is not a string")
        if target in records:
            return target, records[target]
        if target in hosts:
            return target, hosts[target]
        raise AggregateError(f"{graph}: E-ptr target {target} is not accepted")
    if record["verdict"] == "refuted" and cert_type == "sub":
        target = cert.get("g6")
        if not isinstance(target, str):
            raise AggregateError(f"{graph}: R-ptr target is not a string")
        if 'index' in cert and target in forbidden_g6:
            return target, {"g6": target, "verdict": "refuted", "cert": {"type": "forbidden"}}
        if target in records:
            return target, records[target]
        if target in forbidden_g6:
            return target, {"g6": target, "verdict": "refuted", "cert": {"type": "forbidden"}}
        raise AggregateError(f"{graph}: R-ptr target {target} is not accepted")
    return None


def validate_pointers(
    records: Mapping[str, Mapping[str, object]],
    poset: Poset | None = None,
    hosts: Mapping[str, Mapping[str, object]] | None = None,
    forbidden_g6: Iterable[str] = (),
) -> list[str]:
    """Validate producer-neutral pointer maps and detect pointer cycles."""

    host_records = dict(hosts or {})
    forbidden = set(forbidden_g6)
    errors: list[str] = []
    state: dict[str, int] = {}

    def visit(graph: str) -> None:
        if graph in state:
            if state[graph] == 1:
                errors.append(f"pointer cycle reaches {graph}")
            return
        state[graph] = 1
        record = records[graph]
        cert = record["cert"]
        assert isinstance(cert, Mapping)
        try:
            target_info = _pointer_target(graph, record, records, host_records, forbidden)
        except AggregateError as exc:
            errors.append(str(exc))
            state[graph] = 2
            return
        if target_info is not None:
            target, target_record = target_info
            target_verdict = target_record.get("verdict")
            mapping = cert.get("map")
            if not isinstance(mapping, list) or not all(isinstance(item, int) for item in mapping):
                errors.append(f"{graph}: pointer map is not an integer list")
            else:
                try:
                    source_n, source_mask = decode_graph6(graph)
                    target_n, target_mask = decode_graph6(target)
                except Graph6Error as exc:
                    errors.append(f"{graph}: pointer graph decode failed: {exc}")
                else:
                    if record["verdict"] == "embedded":
                        if target_verdict != "embedded":
                            errors.append(f"{graph}: E-ptr target is not embedded")
                        if target_n < source_n:
                            errors.append(f"{graph}: E-ptr target has fewer vertices")
                        if (target_n, edge_count(target_n, target_mask)) <= (source_n, edge_count(source_n, source_mask)):
                            errors.append(f"{graph}: E-ptr target is not a strict supergraph")
                        if not map_edges(source_n, source_mask, target_n, target_mask, mapping):
                            errors.append(f"{graph}: E-ptr map is not injective and edge-preserving")
                    else:
                        if target_verdict != "refuted":
                            errors.append(f"{graph}: R-ptr target is not refuted")
                        if target_n > source_n:
                            errors.append(f"{graph}: R-ptr target has more vertices")
                        if ('index' not in cert and
                                (source_n, edge_count(source_n, source_mask)) <= (target_n, edge_count(target_n, target_mask))):
                            errors.append(f"{graph}: R-ptr target is not a strict subgraph")
                        if not map_edges(target_n, target_mask, source_n, source_mask, mapping):
                            errors.append(f"{graph}: R-ptr map is not injective and edge-preserving")
            if target in records and not (record['verdict'] == 'refuted' and 'index' in cert):
                visit(target)
        state[graph] = 2

    for graph in records:
        visit(graph)
    if poset is not None:
        for relation in poset.relations():
            valid, reason = poset.verify_relation(relation)
            if not valid:
                errors.append(f"poset relation {relation.parent}/{relation.child}: {reason}")
    return errors


def _minimality_report(poset: Poset, records: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    minimal: list[str] = []
    conditional: dict[str, list[str]] = {}
    nonminimal: list[str] = []
    edge_status: dict[str, list[dict[str, object]]] = {}
    for graph in poset.vertices:
        record = records[graph]
        if record["verdict"] != "refuted":
            continue
        n, mask = decode_graph6(graph)
        statuses: list[dict[str, object]] = []
        has_bad = False
        unknown_children: list[str] = []
        for u, v in iter_edges(n, mask):
            child_raw = remove_edge(n, mask, u, v)
            child_form = canonicalize(n, child_raw)
            child = child_form.g6
            if not is_biconnected(n, child_raw):
                status = "non-biconnected"
            elif child not in records:
                status = "missing"
                has_bad = True
            else:
                status = str(records[child]["verdict"])
                if status == "refuted":
                    has_bad = True
                elif status == "unknown":
                    unknown_children.append(child)
            statuses.append({"edge": [u, v], "child": child, "status": status})
        edge_status[graph] = statuses
        if has_bad:
            nonminimal.append(graph)
        elif unknown_children:
            conditional[graph] = sorted(set(unknown_children))
        else:
            minimal.append(graph)
    return {
        "refuted_count": sum(record["verdict"] == "refuted" for record in records.values()),
        "minimal_refuted": sorted(minimal),
        "conditional_minimal": {key: conditional[key] for key in sorted(conditional)},
        "nonminimal_refuted": sorted(nonminimal),
        "edge_checks": edge_status,
    }


def _unknown_record(graph: str, value: object | None) -> dict[str, object]:
    if isinstance(value, Mapping):
        reason = str(value.get("reason", "exhausted search"))
        budget = value.get("budget", {})
        if not isinstance(budget, Mapping):
            budget = {"value": budget}
        cert = {"reason": reason, "budget": dict(budget)}
    else:
        cert = {"reason": "exhausted search", "budget": {}}
    return {"g6": graph, "verdict": "unknown", "cert": cert}


def write_aggregate(
    input_g6: Sequence[str],
    resolved: Mapping[str, Mapping[str, object]],
    unknown: Mapping[str, object] | None,
    out_dir: str | Path,
    poset: Poset,
    hosts: Mapping[str, Mapping[str, object]] | None = None,
    forbidden_g6: Iterable[str] = (),
    verbatim: Mapping[str, bytes] | None = None,
) -> dict[str, object]:
    """Write the final one-record-per-input aggregate and comparison report."""

    input_list = [str(graph).strip() for graph in input_g6 if str(graph).strip()]
    resolved_map = {str(key): dict(value) for key, value in resolved.items()}
    unknown_map = dict(unknown or {})
    extra_resolved = sorted(set(resolved_map) - set(input_list))
    if extra_resolved:
        raise AggregateError("resolved map has extra graphs: " + ", ".join(extra_resolved))
    records: list[dict[str, object]] = []
    for graph in input_list:
        if graph in resolved_map:
            record = dict(resolved_map[graph])
        else:
            record = _unknown_record(graph, unknown_map.get(graph))
        records.append(record)
    errors = coverage_errors(input_list, records)
    if errors:
        raise AggregateError("; ".join(errors))
    record_map = records_by_g6(records)
    pointer_errors = validate_pointers(record_map, poset=poset, hosts=hosts, forbidden_g6=forbidden_g6)
    if pointer_errors:
        raise AggregateError("; ".join(pointer_errors))
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    records_path = target / "records.jsonl"
    with records_path.open("wb") as handle:
        for record in records:
            raw = (verbatim or {}).get(record['g6'])
            if raw is not None:
                if json.loads(raw) != record or not raw.endswith(b'\n'):
                    raise AggregateError('verbatim seed changed or has invalid line framing')
                handle.write(raw)
            else:
                handle.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
    unknown_lines = [graph for graph in input_list if record_map[graph]["verdict"] == "unknown"]
    save_graph6(target / "UNKNOWN.g6", unknown_lines)
    minimality = _minimality_report(poset, record_map)
    (target / "MINIMALITY.json").write_text(
        json.dumps(minimality, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    save_graph6(target / "MINIMALITY.g6", minimality["minimal_refuted"])
    done = done_by_set(input_list, [record["g6"] for record in records])
    summary = {
        "input_count": len(input_list),
        "embedded_count": sum(record["verdict"] == "embedded" for record in records),
        "refuted_count": sum(record["verdict"] == "refuted" for record in records),
        "unknown_count": len(unknown_lines),
        "done": done,
        "minimal_count": len(minimality["minimal_refuted"]),
        "conditional_minimal_count": len(minimality["conditional_minimal"]),
    }
    (target / "SUMMARY.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    if done:
        (target / "DONE").write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
    else:
        done_path = target / "DONE"
        if done_path.exists():
            done_path.unlink()
    return summary


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--poset", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--hosts", type=Path)
    parser.add_argument("--forbidden-g6", type=Path)
    args = parser.parse_args()
    input_g6 = load_graph6(args.input)
    raw_records: list[dict[str, object]] = []
    for path in args.records:
        raw_records.extend(read_jsonl(path))
    record_map = records_by_g6(raw_records)
    poset = load_poset(args.poset)
    hosts = records_by_g6(read_jsonl(args.hosts)) if args.hosts else {}
    forbidden = load_graph6(args.forbidden_g6) if args.forbidden_g6 else []
    summary = write_aggregate(input_g6, record_map, {}, args.out_dir, poset, hosts, forbidden)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
