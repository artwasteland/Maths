#!/usr/bin/env python3
"""Independent checks and deliberate red controls for udenum."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
UDENUM = HERE / "udenum"
FORBIDDEN = HERE.parent / "data" / "forbidden-74.json"
KNOWN = HERE.parent / "sources" / "amp" / "anc" / "graph6.txt"
GENG = Path("/usr/bin/nauty-geng")

EXPECTED_PATTERNS = {
    "forbidden_graphs": 74,
    "patterns": 635,
    "size_distribution": {"2": 61, "3": 413, "4": 130,
                          "5": 26, "6": 4, "7": 1},
}

TABLE = {16: (41, 1), 17: (43, 15), 18: (46, 84),
         19: (50, 17), 20: (54, 7), 21: (57, 149)}


class CheckFailure(RuntimeError):
    pass


def run(command: list[str], *, stdout: Path | None = None,
        stderr: Path | None = None, expect_success: bool = True) -> subprocess.CompletedProcess[bytes]:
    out = stdout.open("wb") if stdout else subprocess.PIPE
    err = stderr.open("wb") if stderr else subprocess.PIPE
    try:
        result = subprocess.run(command, stdout=out, stderr=err)
    finally:
        if stdout:
            out.close()
        if stderr:
            err.close()
    if expect_success and result.returncode != 0:
        message = result.stderr.decode(errors="replace") if result.stderr else ""
        raise CheckFailure(f"command failed ({result.returncode}): {' '.join(command)}\n{message}")
    return result


def clean_workdir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def invoke(parents: Path, n: int, m: int, output: Path, manifest: Path,
           shard: str, extra: list[str] | None = None, filter_mode: bool = False) -> dict[str, object]:
    command = [
        "nice", "-n", "10", str(UDENUM), "--parents", str(parents),
        "--forbidden", str(FORBIDDEN), "--n", str(n), "--m", str(m),
        "--output", str(output), "--manifest", str(manifest),
        "--shard-id", shard,
    ]
    if filter_mode:
        command.append("--filter")
    if extra:
        command += extra
    result = run(command)
    stderr = result.stderr.decode().strip()
    return json.loads(stderr.splitlines()[-1])


def lines(path: Path) -> list[bytes]:
    return [line.rstrip(b"\r\n") for line in path.read_bytes().splitlines() if line.strip()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def require_unique(path: Path) -> None:
    values = lines(path)
    require(len(values) == len(set(values)), f"duplicate canonical graph6 in {path}")


def require_equal_sets(left: Path, right: Path) -> None:
    a = sorted(lines(left))
    b = sorted(lines(right))
    require(a == b, f"graph6 sets differ: {left} versus {right}")


def require_equal_bytes(left: Path, right: Path) -> None:
    require(left.read_bytes() == right.read_bytes(),
            f"files are not byte-identical: {left} versus {right}")


def require_manifest(path: Path, output: Path) -> None:
    value = json.loads(path.read_text())
    expected_keys = {
        "shard_id", "parent_file", "parent_range", "software_sha256",
        "inputs_sha256", "started", "finished", "children_written",
        "children_file_sha256", "host", "exit_status",
    }
    require(set(value) == expected_keys, f"manifest field set is wrong in {path}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    require(value["children_file_sha256"] == digest, f"child hash is wrong in {path}")
    require(value["children_written"] == len(lines(output)), f"child count is wrong in {path}")
    require(value["exit_status"] == 0, f"nonzero manifest exit status in {path}")


def prove_red(name: str, check) -> str:
    try:
        check()
    except CheckFailure as error:
        return f"RED {name}: {error}"
    raise CheckFailure(f"control did not go red: {name}")


def quick(workdir: Path) -> dict[str, object]:
    clean_workdir(workdir)
    red: list[str] = []
    result = run([str(UDENUM), "--forbidden", str(FORBIDDEN), "--pattern-stats"])
    pattern_stats = json.loads(result.stdout)
    require(pattern_stats == EXPECTED_PATTERNS, "pattern statistics differ from the contract")

    altered = workdir / "forbidden-73.json"
    forbidden_value = json.loads(FORBIDDEN.read_text())
    altered.write_text(json.dumps(forbidden_value[:-1]) + "\n")
    bad_result = run([str(UDENUM), "--forbidden", str(altered), "--pattern-stats"],
                     expect_success=False)
    require(bad_result.returncode != 0, "73-graph pattern data was accepted")
    red.append("RED pattern validator: deleting forbidden graph 73 made --pattern-stats exit 2")

    k3 = workdir / "k3.g6"
    k3.write_bytes(b"Bw\n")
    normal = workdir / "k4-normal.g6"
    normal_manifest = workdir / "k4-normal.manifest.json"
    normal_stats = invoke(k3, 4, 6, normal, normal_manifest, "k4-normal")
    require(lines(normal) == [], "K4 was emitted with complete bad sets")
    mutant = workdir / "k4-drop-badset.g6"
    mutant_manifest = workdir / "k4-drop-badset.manifest.json"
    mutant_stats = invoke(k3, 4, 6, mutant, mutant_manifest, "k4-drop-badset",
                          ["--mutation-drop-first-badset"])
    red.append(prove_red("forbidden-child rejection",
                         lambda: require(lines(mutant) == [],
                                         "C~ appeared after deleting the K3 bad set")))
    require(lines(mutant) == [b"C~"], "bad-set mutation did not emit K4")

    orbit_parents = workdir / "orbit-parents.g6"
    orbit_parents.write_bytes(b"DDW\nD@s\n")
    orbit_normal = workdir / "orbit-normal.g6"
    orbit_normal_manifest = workdir / "orbit-normal.manifest.json"
    orbit_stats = invoke(orbit_parents, 6, 5, orbit_normal,
                         orbit_normal_manifest, "orbit-normal")
    require_unique(orbit_normal)
    orbit_mutant = workdir / "orbit-mutant.g6"
    orbit_mutant_manifest = workdir / "orbit-mutant.manifest.json"
    orbit_mutant_stats = invoke(orbit_parents, 6, 5, orbit_mutant,
                                orbit_mutant_manifest, "orbit-mutant",
                                ["--mutation-no-child-orbit"])
    red.append(prove_red("child-orbit uniqueness",
                         lambda: require_unique(orbit_mutant)))

    deterministic = workdir / "orbit-repeat.g6"
    deterministic_manifest = workdir / "orbit-repeat.manifest.json"
    invoke(orbit_parents, 6, 5, deterministic, deterministic_manifest, "orbit-repeat")
    require_equal_bytes(orbit_normal, deterministic)
    corrupted = workdir / "orbit-repeat-corrupt.g6"
    corrupted.write_bytes(deterministic.read_bytes() + b"?\n")
    red.append(prove_red("byte determinism",
                         lambda: require_equal_bytes(orbit_normal, corrupted)))

    require_manifest(normal_manifest, normal)
    broken_manifest = json.loads(normal_manifest.read_text())
    broken_manifest["children_file_sha256"] = "0" * 64
    broken_path = workdir / "broken.manifest.json"
    broken_path.write_text(json.dumps(broken_manifest) + "\n")
    red.append(prove_red("manifest hash",
                         lambda: require_manifest(broken_path, normal)))

    return {
        "pattern_stats": pattern_stats,
        "normal_k4": normal_stats,
        "mutant_k4": mutant_stats,
        "normal_orbit": orbit_stats,
        "mutant_orbit": orbit_mutant_stats,
        "red_controls": red,
    }


def concatenate(paths: list[Path], output: Path) -> None:
    with output.open("wb") as destination:
        for path in paths:
            with path.open("rb") as source:
                shutil.copyfileobj(source, destination)


def small(max_n: int, workdir: Path) -> dict[str, object]:
    if max_n < 1 or max_n > 10:
        raise ValueError("small comparison supports 1 <= max_n <= 10")
    clean_workdir(workdir)
    generated_dir = workdir / "generated"
    brute_dir = workdir / "brute"
    raw_dir = workdir / "geng"
    parent_dir = workdir / "parents"
    manifest_dir = workdir / "manifests"
    for path in (generated_dir, brute_dir, raw_dir, parent_dir, manifest_dir):
        path.mkdir()
    results: list[dict[str, object]] = []
    started = time.monotonic()
    for n in range(1, max_n + 1):
        for m in range(0, math.comb(n, 2) + 1):
            raw = raw_dir / f"{n}-{m}.g6"
            run(["nice", "-n", "10", str(GENG), "-q", str(n), f"{m}:{m}"],
                stdout=raw)
            brute = brute_dir / f"{n}-{m}.g6"
            brute_manifest = manifest_dir / f"brute-{n}-{m}.json"
            brute_stats = invoke(raw, n, m, brute, brute_manifest, f"brute-{n}-{m}",
                                 filter_mode=True)
            generated = generated_dir / f"{n}-{m}.g6"
            generated_manifest = manifest_dir / f"generated-{n}-{m}.json"
            if n == 1:
                shutil.copyfile(brute, generated)
                shutil.copyfile(brute_manifest, generated_manifest)
                generator_stats: dict[str, object] = {"seed": True}
            else:
                lower = math.ceil(m * (n - 2) / n)
                upper = min(m, math.comb(n - 1, 2))
                parent_files = [generated_dir / f"{n - 1}-{pm}.g6"
                                for pm in range(lower, upper + 1)]
                parents = parent_dir / f"{n}-{m}.g6"
                concatenate(parent_files, parents)
                generator_stats = invoke(parents, n, m, generated,
                                         generated_manifest, f"generated-{n}-{m}")
            require_unique(generated)
            require_equal_sets(generated, brute)
            require_manifest(brute_manifest, brute)
            results.append({"n": n, "m": m, "count": len(lines(generated)),
                            "brute_stats": brute_stats,
                            "generator_stats": generator_stats})
    nonempty = next(item for item in reversed(results) if item["count"])
    n = int(nonempty["n"])
    m = int(nonempty["m"])
    source = generated_dir / f"{n}-{m}.g6"
    doctored = workdir / "doctored-missing.g6"
    doctored.write_bytes(b"\n".join(lines(source)[1:]) + (b"\n" if len(lines(source)) > 1 else b""))
    red_sets = prove_red("small-order set equality",
                         lambda: require_equal_sets(doctored, brute_dir / f"{n}-{m}.g6"))
    duplicated = workdir / "doctored-duplicate.g6"
    duplicated.write_bytes(source.read_bytes() + lines(source)[0] + b"\n")
    red_unique = prove_red("small-order uniqueness", lambda: require_unique(duplicated))
    return {"max_n": max_n, "pairs": len(results),
            "total_generated": sum(int(item["count"]) for item in results),
            "wall_seconds": time.monotonic() - started,
            "red_controls": [red_sets, red_unique], "results": results}


def graph6_order(code: bytes) -> int:
    first = code[0] - 63
    if first <= 62:
        return first
    raise ValueError("only short graph6 orders are needed here")


def graph6_edges(code: bytes) -> int:
    n = graph6_order(code)
    bits: list[int] = []
    for value in code[1:]:
        value -= 63
        bits.extend((value >> shift) & 1 for shift in range(5, -1, -1))
    position = 0
    count = 0
    for column in range(1, n):
        for row in range(column):
            count += bits[position]
            position += 1
    return count


def known(dag_dir: Path, through_n: int | None = None) -> dict[str, object]:
    codes = [line for line in lines(KNOWN)
             if through_n is None or graph6_order(line) <= through_n]
    grouped: dict[tuple[int, int], list[bytes]] = {}
    for code in codes:
        grouped.setdefault((graph6_order(code), graph6_edges(code)), []).append(code)
    checked = 0
    loaded: dict[tuple[int, int], set[bytes]] = {}
    for key, expected in grouped.items():
        n, m = key
        path = dag_dir / f"{n}-{m}.g6"
        require(path.is_file(), f"missing known-graph target file {path}")
        values = set(lines(path))
        loaded[key] = values
        for code in expected:
            require(code in values, f"known graph missing from {path}: {code.decode()}")
            checked += 1
    first_key = next(iter(grouped))
    first_code = grouped[first_key][0]
    doctored = set(loaded[first_key])
    doctored.discard(first_code)
    red = prove_red("known-graph membership",
                    lambda: require(first_code in doctored,
                                    f"known graph removed: {first_code.decode()}"))
    return {"checked": checked, "groups": len(grouped), "red_controls": [red]}


def checkpoints(dag_dir: Path, through_n: int = 22) -> dict[str, object]:
    counts: dict[str, int] = {}
    for n, (m, expected) in TABLE.items():
        if n > through_n:
            continue
        path = dag_dir / f"{n}-{m}.g6"
        require(path.is_file(), f"missing Table 1 file {path}")
        actual = len(lines(path))
        require(actual == expected, f"Table 1 ({n},{m}) is {actual}, expected {expected}")
        counts[f"{n}-{m}"] = actual
    for m, expected in (() if through_n < 22 else ((62, 2), (63, 0))):
        path = dag_dir / f"22-{m}.g6"
        require(path.is_file(), f"missing u-bar(22) file {path}")
        actual = len(lines(path))
        require(actual == expected, f"checkpoint (22,{m}) is {actual}, expected {expected}")
        counts[f"22-{m}"] = actual
    wrong = dict(counts)
    wrong["16-41"] = 0
    red = prove_red("checkpoint count",
                    lambda: require(wrong == counts,
                                    "doctored checkpoint count differs"))
    return {"counts": counts, "red_controls": [red]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    quick_parser = sub.add_parser("quick")
    quick_parser.add_argument("--work-dir", type=Path, default=HERE / "scratch" / "verify-quick")
    small_parser = sub.add_parser("small")
    small_parser.add_argument("--max-n", type=int, default=10)
    small_parser.add_argument("--work-dir", type=Path, default=HERE / "scratch" / "verify-small")
    known_parser = sub.add_parser("known")
    known_parser.add_argument("dag_dir", type=Path)
    known_parser.add_argument("--through-n", type=int)
    checkpoint_parser = sub.add_parser("checkpoints")
    checkpoint_parser.add_argument("dag_dir", type=Path)
    checkpoint_parser.add_argument("--through-n", type=int, default=22)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "quick":
        value = quick(args.work_dir.resolve())
    elif args.command == "small":
        value = small(args.max_n, args.work_dir.resolve())
    elif args.command == "known":
        value = known(args.dag_dir.resolve(), args.through_n)
    else:
        value = checkpoints(args.dag_dir.resolve(), args.through_n)
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckFailure, OSError, ValueError) as error:
        print(f"verify.py: {error}", file=sys.stderr)
        raise SystemExit(1)
