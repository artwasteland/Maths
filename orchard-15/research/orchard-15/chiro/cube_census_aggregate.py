#!/usr/bin/env python3
"""cube_census_aggregate.py: audit a cube census (cube_census.py JSONL records) and name its classes.

Checks, each reported and any failure fatal (exit 1):
  1. coverage: every cube name that exist.py --list-cubes lists for (v, b, depth) appears exactly
     once, and every record is UNSAT_VERIFIED (loop UNSAT, kissat UNSAT, drat-trim VERIFIED);
  2. the models: every model line parses as a PTS(v, b), and each cube's models are distinct;
  3. the classes: the union of the models, canonicalised with the stage-3 canonicaliser (pynauty
     on the coloured point-block incidence graph), compared with --known (a file of canonical
     representatives): reports classes found, missing from --known, and NEW (absent from --known).
Writes the class file (canonical lines, sorted) and a manifest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "realize"))
from chirosat import file_sha256, parse_pts_line  # noqa: E402
from canonicalize import canonical_pts  # noqa: E402


def expected_names(v: int, b: int, depth: int, python: str) -> list[str]:
    out = subprocess.run(
        [python, str(HERE / "exist.py"), str(v), str(b), "--backend", "pysat", "--list-cubes", "--cube-depth", str(depth)],
        text=True, capture_output=True, check=True,
    ).stdout.strip().splitlines()[-1]
    listing = json.loads(out)
    if depth == 1:
        return [f"cube{i:03d}" for i in range(listing["level1_cubes"])]
    names = []
    for i in range(listing["level1_cubes"]):
        for j in range(listing["level2"][str(i)]["cubes"]):
            names.append(f"cube{i:03d}-{j:03d}")
    return names


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("v", type=int)
    p.add_argument("b", type=int)
    p.add_argument("--depth", type=int, choices=(1, 2), required=True)
    p.add_argument("--jsonl", type=Path, nargs="+", required=True)
    p.add_argument("--known", type=Path, help="canonical representatives the census is expected to find (one PTS line each)")
    p.add_argument("--classes-out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--python", default=sys.executable)
    args = p.parse_args(argv)

    failures: list[str] = []
    expected = expected_names(args.v, args.b, args.depth, args.python)
    records: dict[str, dict] = {}
    duplicates: list[str] = []
    for path in args.jsonl:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if (r["v"], r["b"], r["depth"]) != (args.v, args.b, args.depth):
                failures.append(f"{path}: record for ({r['v']},{r['b']}) depth {r['depth']} in a ({args.v},{args.b}) depth {args.depth} audit")
                continue
            if r["cube_name"] in records:
                prev = records[r["cube_name"]]
                # two independent runs of the same cube are welcome if they agree exactly
                # (same verdict, same model lines); a disagreement is a coverage failure
                if prev.get("verdict") == "UNSAT_VERIFIED" and r.get("verdict") == "UNSAT_VERIFIED" and sorted(prev.get("models", [])) == sorted(r.get("models", [])):
                    prev.setdefault("agreeing_duplicates", 0)
                    prev["agreeing_duplicates"] += 1
                    continue
                if prev.get("verdict") != "UNSAT_VERIFIED" and r.get("verdict") == "UNSAT_VERIFIED":
                    records[r["cube_name"]] = r  # a verified record supersedes a timed-out one
                    continue
                if prev.get("verdict") == "UNSAT_VERIFIED" and r.get("verdict") != "UNSAT_VERIFIED":
                    continue
                duplicates.append(r["cube_name"])
                continue
            records[r["cube_name"]] = r
    missing = [n for n in expected if n not in records]
    unexpected = [n for n in records if n not in set(expected)]
    not_verified = [n for n, r in records.items() if r.get("verdict") != "UNSAT_VERIFIED"]
    weak = [n for n, r in records.items() if r.get("verdict") == "UNSAT_VERIFIED" and not (
        r.get("loop_verdict") == "UNSAT" and r.get("closure", {}).get("verdict") == "UNSAT" and r.get("closure", {}).get("proof_verified") is True
        and r.get("closure", {}).get("blocking_clauses") == r.get("models_count") and r.get("mutation") is None)]
    if missing:
        failures.append(f"coverage: {len(missing)} of {len(expected)} cubes have no record (first: {missing[:5]})")
    if unexpected:
        failures.append(f"coverage: {len(unexpected)} records name cubes the listing does not have (first: {unexpected[:5]})")
    if duplicates:
        failures.append(f"coverage: DISAGREEING duplicate records for {sorted(set(duplicates))[:5]}")
    agreeing = sum(r.get("agreeing_duplicates", 0) for r in records.values())
    if not_verified:
        failures.append(f"certificates: {len(not_verified)} cubes are not UNSAT_VERIFIED (first: {[(n, records[n]['verdict']) for n in not_verified[:5]]})")
    if weak:
        failures.append(f"certificates: {len(weak)} UNSAT_VERIFIED records fail the field-level check (first: {weak[:5]})")

    labelled = 0
    classes: dict[bytes, object] = {}
    per_class_labelled: dict[bytes, int] = {}
    for name, r in records.items():
        lines = r.get("models", [])
        if len(set(lines)) != len(lines):
            failures.append(f"models: cube {name} lists a model twice")
        for line in lines:
            pts = parse_pts_line(line)
            if pts.v != args.v or len(pts.blocks) != args.b:
                failures.append(f"models: cube {name} has a line that is not a PTS({args.v},{args.b})")
                continue
            labelled += 1
            certificate, canonical = canonical_pts(pts)
            previous = classes.setdefault(certificate, canonical)
            if previous.line != canonical.line:
                failures.append("canonical form collision with unequal lines")
            per_class_labelled[certificate] = per_class_labelled.get(certificate, 0) + 1
    ordered = sorted(pts.line for pts in classes.values())
    args.classes_out.parent.mkdir(parents=True, exist_ok=True)
    args.classes_out.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="ascii")

    known_missing: list[str] = []
    new_classes: list[str] = []
    known_count = None
    if args.known:
        known = {}
        for line in args.known.read_text(encoding="ascii").splitlines():
            if line.strip():
                cert, canon = canonical_pts(parse_pts_line(line))
                known[cert] = canon.line
        known_count = len(known)
        known_missing = [known[c] for c in known if c not in classes]
        new_classes = [classes[c].line for c in classes if c not in known]
        if known_missing:
            failures.append(f"classes: {len(known_missing)} known classes were NOT found by the census")
        if new_classes:
            failures.append(f"classes: {len(new_classes)} classes are NEW (absent from --known)")

    manifest = {
        "v": args.v, "b": args.b, "depth": args.depth,
        "cubes_expected": len(expected), "cubes_recorded": len(records),
        "cubes_unsat_verified": sum(1 for r in records.values() if r.get("verdict") == "UNSAT_VERIFIED"),
        "labelled_models": labelled, "classes": len(ordered),
        "labelled_per_class": sorted(per_class_labelled.values(), reverse=True),
        "known_count": known_count, "known_missing": known_missing, "new_classes": new_classes,
        "cubes_with_models": sum(1 for r in records.values() if r.get("models_count", 0) > 0),
        "agreeing_duplicate_records": agreeing,
        "closure_proof_bytes_total": sum(r.get("closure", {}).get("proof_bytes") or 0 for r in records.values()),
        "closure_solve_seconds_total": round(sum(r.get("closure", {}).get("solve_seconds") or 0 for r in records.values()), 3),
        "closure_check_seconds_total": round(sum(r.get("closure", {}).get("check_seconds") or 0 for r in records.values()), 3),
        "loop_seconds_total": round(sum(r.get("loop_seconds") or 0 for r in records.values()), 3),
        "classes_sha256": file_sha256(args.classes_out),
        "jsonl": [str(p) for p in args.jsonl], "jsonl_sha256": [file_sha256(p) for p in args.jsonl],
        "failures": failures,
        "verdict": "COMPLETE" if not failures else "FAILED",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("verdict", "cubes_expected", "cubes_recorded", "cubes_unsat_verified", "labelled_models", "classes", "known_count", "known_missing", "new_classes", "failures")}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
