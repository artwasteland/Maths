#!/usr/bin/env python3
"""Hereditary pruning of one level file of the F-free DAG (see enum/PRUNING.md, L1 to L3).

Input: a level file ``<n>-<m>.g6`` or ``<n>-<m>.reach.g6`` (canonical graph6, one graph per
line, every graph with n vertices and m edges).  Steps, all recorded in the manifest:

1. filter/udfilter on every graph.  Only the verdicts "tu" and "pass" are legal here; a
   "forbidden" verdict means the generator emitted a non-F-free graph and the step aborts.
2. embed/udembed.py on the survivors, in chunks, up to --jobs processes at a time, with a
   wall-clock budget per graph.  A graph whose chunk and individual reruns both time out is
   recorded as "unknown" (conservative: it is kept).
3. ``<n>-<m>.certs.jsonl``: one certificate per input graph, in input order, in the schema of
   check/udcheck.py; ``<n>-<m>.UNKNOWN.g6``: the unknown graphs in order (always written);
   ``<n>-<m>.keep.g6``: the embedded and unknown graphs in input order (the parents the next
   level is built from); ``<n>-<m>.prune.manifest.json``.
4. check/udcheck.py replays every certificate against the input list; a rejection aborts.
   With --jobs > 1, a cell of more than $PRUNE_CHECK_PARALLEL_ABOVE records (default 20,000) is
   replayed in up to --jobs contiguous chunks at once (each at most $PRUNE_CHECK_CHUNK), every
   chunk with its own graph list, unknown list and work directory; the ACCEPT counts are summed,
   one chunk's rejection fails the step with that chunk's reason, and the manifest records the
   chunks ("checker_chunking"). Smaller cells, and --jobs 1, are checked exactly as before.
5. An independent re-read of the written files verifies that keep + pruned = input.

The TU verdict is a refutation only at or above the proved maximum edge count of the TARGET
(CONTRACT Section 1 and PRUNING.md L2), so --target-n and --target-m are required and the
step refuses to run when the target lies below the proved bound.

--forbidden-set 398 (the driver's set, run-dag2.py --forbidden-set) filters with
``udfilter -s 398`` and data/forbidden-398.json (pinned by sha256), so a graph containing any of
the 398 is a GENERATOR BUG here, and replays the certificates with check/udcheck398.py (the
unchanged check/udcheck.py with the 398 list). The default, set 74, is the u(22) step unchanged.
--filter-set 74 in a set-398 run makes udfilter re-check only the 74 (its TU verdicts and witnesses
are the same, since it looks for the gadgets independently of the forbidden list); the replay kernel
stays the run's, and the manifest records "filter_set": 74. The re-check of the 324 is then the
stage verification's (run-dag2.py --verify-stages), which it duplicates: PRUNING.md 5.6.

--rhombus (research/unit-distance-23/RHOMBUS-SPEC.md; enum/PRUNING.md L5) runs filter/udrhombus on
udfilter's survivors, in --jobs parts, between steps 1 and 2: a graph it calls "refuted" (a
collision forced by the 4-cycles, Corollary R1) or "tu" (a forced unit distance on a non-edge,
Corollary R2) is pruned with its linear certificate, and only its "pass" graphs go on to the
embedder (or become unknown with --filter-only). The certificate file then holds rhombus records
beside udcheck.py's, and step 4 replays the WHOLE file with check/udcheck_rhombus.py (udcheck.py's
arguments plus --data-dir and --forbidden-set). The manifest records "rhombus": true, the counts
rhombus_tu, rhombus_refuted and rhombus_silent_passes (graphs the prover passed without a
certificate after a detection, e.g. a failed self-verification: SPEC amendment 2), the prover's
statistics, and the prover's and checker's paths and hashes. Without --rhombus nothing of this runs
and every output byte is as before.

--triangles is the same step with filter/udtriangle (RHOMBUS-SPEC.md Section 4: case trees over
triangle orientations, witness "tri"; its verdicts contain udrhombus's) in place of udrhombus: the
manifest records "triangles": true, the counts tri_tu, tri_refuted, tri_silent_passes (budget,
verify_fail, lift_fail and internal passes) and the prover's whole statistics line (triangles_stats:
refuted, tu, pass, open, budget, verify_fail, lift_fail, internal, ...). The two flags exclude each
other; each is one entry of RULES (prover and witness key).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Proved upper bounds on u(n): AMP Theorem 1(a) gives u(n) exactly for n <= 21 and
# Theorem 1(b) gives u(22) <= 61.  The TU rule (L2) needs target_m >= UPPER[target_n].
# u(23) <= 65 rests on u(22) = 60 (research/unit-distance-22/RESULT-u22.md) and AMP's Lemma
# (Schade): a graph on 23 vertices with 66 edges has an induced subgraph on 22 vertices with at
# least ceil(66 * 21 / 23) = 61 edges (research/unit-distance-23/CONTRACT.md Section 0).
# Keep 23: 65 and its source: existing prune manifests record this proved bound.
# u(24) <= 69 uses u(23) = 64 (RESULT-u23.md, COMPLETE, gates G2 to G6 met): a (24,70)
# graph would have an induced 23-vertex subgraph with ceil(70 * 22 / 24) = 65 > 64 edges.
UPPER = {16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57, 22: 61, 23: 65, 24: 69}
UPPER_SOURCE = {23: "u(22) = 60 (research/unit-distance-22/RESULT-u22.md) and Schade's lemma: "
                    "ceil(66 * 21 / 23) = 61 > u(22)",
                24: "u(23) = 64 (research/unit-distance-23/RESULT-u23.md, COMPLETE, gates G2 to G6 met) "
                    "and Schade's lemma: ceil(70 * 22 / 24) = 65 > u(23)"}

FORBIDDEN_FILES = {74: "forbidden-74.json", 398: "forbidden-398.json"}
FORBIDDEN_398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"

FILTER_VERDICTS = {"tu", "pass"}
EMBED_VERDICTS = {"embedded", "refuted", "unknown"}
KEEP_VERDICTS = {"embedded", "unknown"}

# The linear-certificate rules that run on udfilter's survivors (research/unit-distance-23/RHOMBUS-SPEC.md). A rule
# is ONE parameter: its prover (the argparse option naming its binary) and its witness key, plus how its statistics
# line counts silent passes (graphs it detected or searched but passed without a certificate; SPEC amendment 2
# requires them in the manifest) and, if it reports one, the field that marks a red-control build. The flag name is
# the rule name (prune.py --rhombus, recorded as "rhombus": true); the counts of its records carry the checker's
# prefix (the ACCEPT line's rhombus_tu / tri_tu). --triangles runs udtriangle (SPEC Section 4, witness "tri"), whose
# verdicts contain udrhombus's, IN PLACE of udrhombus: at most one rule per prune step.
RULES = {
    "rhombus": {"prover_option": "udrhombus", "witness": "rhombus", "count_prefix": "rhombus",
                "silent": ("certificate_failures",), "mutant_field": "mutant"},
    "triangles": {"prover_option": "udtriangle", "witness": "tri", "count_prefix": "tri",
                  "silent": ("budget", "verify_fail", "lift_fail", "internal"), "mutant_field": "mutant"},
}
RULE_VERDICTS = {"pass", "refuted", "tu"}

# The rules' checker, check/udcheck_rhombus.py (it verifies every rule's records, SPEC amendment 2).
# PRUNE_UDCHECK_RHOMBUS replaces the default path; it exists for the prover builder's end-to-end tests while
# check/udcheck_rhombus.py is being written, and every manifest records the checker's path, its sha256 and whether
# the environment chose it.
RHOMBUS_CHECKER_ENV = "PRUNE_UDCHECK_RHOMBUS"


class PruneError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decode_graph6(code: str) -> tuple[int, int, int]:
    """Return (vertices, edges, minimum degree) of a short-form graph6 string."""
    if not code or ord(code[0]) < 63 or ord(code[0]) > 126:
        raise PruneError(f"invalid graph6 record {code!r}")
    n = ord(code[0]) - 63
    if n > 62:
        raise PruneError("long graph6 forms are not supported")
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    needed = n * (n - 1) // 2
    if len(bits) < needed or len(bits) - needed >= 6:
        raise PruneError(f"graph6 record of wrong length {code!r}")
    if any(ch != "0" for ch in bits[needed:]):
        raise PruneError(f"graph6 padding is not zero {code!r}")
    degree = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                degree[i] += 1
                degree[j] += 1
            k += 1
    return n, sum(degree) // 2, (min(degree) if n else 0)


def read_g6(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise PruneError(f"{path}: missing final newline")
    lines = raw.decode("ascii").split("\n")[:-1] if raw else []
    if any(not line or line.startswith(">>") for line in lines):
        raise PruneError(f"{path}: blank or header line in graph list")
    return lines


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(line + "\n" for line in lines), encoding="ascii")


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.endswith("\n") or not line.strip():
                raise PruneError(f"{path}:{lineno}: malformed JSON line")
            records.append(json.loads(line))
    return records


def iter_jsonl(path: Path):
    """Stream the records of a JSON-lines file; the (13,23) cell has 19.5 million of them and
    materialising them as dicts needs about 14 GB (a cloud worker was OOM-killed doing so)."""
    with path.open("r", encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.endswith("\n") or not line.strip():
                raise PruneError(f"{path}:{lineno}: malformed JSON line")
            yield json.loads(line)


def dump(record: dict) -> str:
    return json.dumps(record, separators=(",", ":"), sort_keys=True)


def level_from_name(path: Path) -> tuple[int, int]:
    match = re.match(r"^(\d+)-(\d+)(\.reach)?\.g6$", path.name)
    if not match:
        raise PruneError(f"level file name must be <n>-<m>.g6 or <n>-<m>.reach.g6: {path.name}")
    return int(match.group(1)), int(match.group(2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=Path, required=True, help="<n>-<m>.g6 or <n>-<m>.reach.g6")
    parser.add_argument("--target-n", type=int, required=True)
    parser.add_argument("--target-m", type=int, required=True)
    parser.add_argument("--jobs", type=int, choices=tuple(range(1, 17)), default=1)
    parser.add_argument("--tries", type=int, default=24, help="udembed --tries")
    parser.add_argument("--max-states", type=int, default=400, help="udembed --max-states")
    parser.add_argument("--chunk", type=int, default=25, help="graphs per embedder process")
    parser.add_argument("--graph-timeout", type=float, default=120.0,
                        help="wall-clock seconds allowed per graph before it is recorded unknown")
    parser.add_argument("--python", type=Path,
                        default=Path(os.path.expanduser("~/tools/pyenv-maths/bin/python")))
    parser.add_argument("--udfilter", type=Path, default=ROOT / "filter" / "udfilter")
    parser.add_argument("--udembed", type=Path, default=ROOT / "embed" / "udembed.py")
    parser.add_argument("--udcheck", type=Path, default=ROOT / "check" / "udcheck.py")
    parser.add_argument("--udcheck398", type=Path, default=ROOT / "check" / "udcheck398.py",
                        help="the checker used with --forbidden-set 398")
    parser.add_argument("--forbidden-set", type=int, choices=(74, 398), default=74,
                        help="74 (default, the u(22) step) or 398: udfilter -s 398 with data/forbidden-398.json")
    parser.add_argument("--filter-set", type=int, choices=(74, 398), default=None,
                        help="the forbidden set of udfilter's re-check (default: --forbidden-set). 74 in a set-398 "
                             "run re-checks only the 74 (PRUNING.md 5.6); the replay kernel stays the run's")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--record", action="append", default=[], metavar="NAME=PATH",
                        help="extra input file whose hash goes into the manifest (for example reach.json)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--filter-only", action="store_true",
                        help="hereditary TU pruning only: skip the embedder, survivors become unknown (kept)")
    parser.add_argument("--rhombus", action="store_true",
                        help="run filter/udrhombus on udfilter's survivors and prune with its linear "
                             "certificates (RHOMBUS-SPEC.md); replay with check/udcheck_rhombus.py")
    parser.add_argument("--udrhombus", type=Path, default=ROOT / "filter" / "udrhombus")
    parser.add_argument("--triangles", action="store_true",
                        help="run filter/udtriangle (the triangle-orientation case trees, RHOMBUS-SPEC.md Section 4, "
                             "witness \"tri\"; its verdicts contain udrhombus's) in place of udrhombus")
    parser.add_argument("--udtriangle", type=Path, default=ROOT / "filter" / "udtriangle")
    parser.add_argument("--udcheck-rhombus", type=Path,
                        default=Path(os.environ.get(RHOMBUS_CHECKER_ENV) or ROOT / "check" / "udcheck_rhombus.py"),
                        help=f"the checker used with --rhombus (default check/udcheck_rhombus.py, or "
                             f"${RHOMBUS_CHECKER_ENV} when set; recorded in the manifest)")
    parser.add_argument("--mutation-unknown-as-pruned", action="store_true",
                        help="TEST ONLY: drop unknown graphs from keep and UNKNOWN (must go red)")
    return parser.parse_args()


def nice(command: list[str]) -> list[str]:
    return ["nice", "-n", "10", *command]


FILTER_PART_MAX = 200_000   # graphs per udfilter process: a killed run loses at most one part


def run_filter_part(args: argparse.Namespace, codes: list[str], prefix: Path) -> Path:
    out = prefix.with_suffix(".jsonl")
    err = prefix.with_suffix(".stderr")
    source = prefix.with_suffix(".g6")
    # Resume: a part whose input is byte-identical to these codes and whose output has one
    # record per graph was completed by an earlier (killed) run of the same level; udfilter is
    # deterministic per graph, so the records are reused. Anything else is redone from scratch.
    if source.is_file() and out.is_file():
        expected = "".join(code + "\n" for code in codes).encode("ascii")
        try:
            if source.read_bytes() == expected and sum(1 for _ in out.open("rb")) == len(codes):
                return out
        except OSError:
            pass
        out.unlink(missing_ok=True)
    write_lines(source, codes)
    # set 74: exactly the u(22) command; set 398: udfilter checks the file against its pin. The set is
    # the FILTER set (--filter-set, by default the run's forbidden set)
    set_option = [] if args.filter_set == 74 else ["-s", str(args.filter_set)]
    with prefix.with_suffix(".g6").open("rb") as stdin, out.open("wb") as stdout, err.open("wb") as stderr:
        result = subprocess.run(nice([str(args.udfilter), *set_option,
                                      "-f", str(args.data_dir / FORBIDDEN_FILES[args.filter_set]),
                                      "-t", str(args.data_dir / "tu-gadgets.json")]),
                                stdin=stdin, stdout=stdout, stderr=stderr)
    if result.returncode != 0:
        raise PruneError(f"udfilter failed with status {result.returncode}: {err.read_text()}")
    return out


def run_filter(args: argparse.Namespace, codes: list[str], workdir: Path,
               gadgets: list) -> tuple[list[str], int, float]:
    """Filter every graph, in --jobs contiguous parts; the filter is deterministic per graph.
    Returns the survivors (verdict pass, in input order), the tu count and the wall time; the
    records themselves stay on disk in filter.jsonl and are streamed again when written out."""
    out = workdir / "filter.jsonl"
    start = time.monotonic()
    n = len(codes)
    # Reuse finished parts OF ANY SIZE from an earlier run of this level: an older prune.py wrote
    # parts of ceil(N/jobs) graphs, this one writes parts of at most FILTER_PART_MAX, and a
    # restart must not re-filter a cell whose output already exists (2.5 h at (13,23)). A part
    # is reused when its input file equals the codes at its offset and its output has one record
    # per graph; udfilter is deterministic per graph, so the concatenation is the same bytes.
    done: dict[int, tuple[int, Path]] = {}
    for src in sorted(workdir.glob("filter-*.g6")):
        match = re.fullmatch(r"filter-(\d+)\.g6", src.name)
        jsonl = src.with_suffix(".jsonl")
        if not match or not jsonl.is_file():
            continue
        offset = int(match.group(1))
        try:
            data = src.read_bytes()
        except OSError:
            continue
        length = data.count(b"\n")
        if length == 0 or offset + length > n:
            continue
        expected = "".join(code + "\n" for code in codes[offset:offset + length]).encode("ascii")
        if data == expected and sum(1 for _ in jsonl.open("rb")) == length:
            done[offset] = (length, jsonl)
    size = max(1, min(-(-n // args.jobs), FILTER_PART_MAX))
    parts: list[tuple[int, list[str]]] = []      # gaps still to filter
    plan: list[tuple[int, Path | None]] = []     # output order: (offset, reused jsonl or None)
    pos = 0
    for offset in sorted(done):
        length, jsonl = done[offset]
        if offset < pos:
            continue                              # overlaps a part already planned: ignore it
        while pos < offset:
            k = min(size, offset - pos)
            parts.append((pos, codes[pos:pos + k])); plan.append((pos, None)); pos += k
        plan.append((offset, jsonl)); pos = offset + length
    while pos < n:
        k = min(size, n - pos)
        parts.append((pos, codes[pos:pos + k])); plan.append((pos, None)); pos += k
    reused = sum(length for length, _ in done.values() if True)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        produced = dict(zip([offset for offset, _ in parts], executor.map(
            lambda spec: run_filter_part(args, spec[1], workdir / f"filter-{spec[0]:08d}"), parts)))
    with out.open("wb") as stream:
        for offset, jsonl in plan:
            stream.write((jsonl if jsonl is not None else produced[offset]).read_bytes())
    wall = time.monotonic() - start
    print(f"prune.py: filter reused {reused} of {n} records from finished parts", file=sys.stderr)
    survivors: list[str] = []
    n_tu = 0
    count = 0
    for index, record in enumerate(iter_jsonl(out)):
        if index >= len(codes):
            raise PruneError(f"udfilter wrote more than {len(codes)} records for {len(codes)} graphs")
        code = codes[index]
        if record.get("g6") != code:
            raise PruneError("udfilter records are out of order")
        verdict = record.get("verdict")
        if verdict == "forbidden":
            raise PruneError("GENERATOR BUG: the level file contains a non-F-free graph "
                             f"{code} (forbidden witness {record.get('witness')})")
        if verdict not in FILTER_VERDICTS:
            raise PruneError(f"unexpected filter verdict {verdict!r} for {code}")
        if verdict == "tu":
            convert_tu_witness(record.get("witness"), gadgets, code)   # validated here, converted when written
            n_tu += 1
        else:
            survivors.append(code)
        count = index + 1
    if count != len(codes):
        raise PruneError(f"udfilter wrote {count} records for {len(codes)} graphs")
    return survivors, n_tu, wall


def convert_tu_witness(witness: object, gadgets: list, code: str) -> dict:
    """The filter's "pair" is the gadget's own pair (gadget-local indices, checked by
    filter/verify-witness.py); the binding checker schema (check/udcheck.py) wants the two
    candidate vertices the pair maps to.  CONTRACT 9.1: the producer ships the converter."""
    if not isinstance(witness, dict) or set(witness) != {"index", "map", "pair"}:
        raise PruneError(f"malformed tu witness for {code}")
    index, mapping, pair = witness["index"], witness["map"], witness["pair"]
    if not isinstance(index, int) or not 0 <= index < len(gadgets):
        raise PruneError(f"tu witness gadget index out of range for {code}")
    gadget = gadgets[index]
    if (not isinstance(mapping, list) or len(mapping) != gadget["n"] or
            len(set(mapping)) != len(mapping)):
        raise PruneError(f"tu witness map is not an injection of the gadget for {code}")
    if list(pair) != list(gadget["pair"]):
        raise PruneError(f"tu witness pair {pair} is not gadget {index}'s pair {gadget['pair']} for {code}")
    return {"index": index, "map": mapping, "pair": [mapping[pair[0]], mapping[pair[1]]]}


RULE_PART_MAX = 200_000   # graphs per prover process
RULE_STATS_MAX = ("max_cycles", "max_rank", "max_nodes", "budget_limit", "mirror")   # maxima over parts, not sums


def rule_of(args: argparse.Namespace) -> str | None:
    """The linear rule selected on the command line (at most one per prune step), or None."""
    chosen = [name for name in RULES if getattr(args, name, False)]
    if len(chosen) > 1:
        raise PruneError(f"at most one linear rule per prune step, not {chosen}")
    return chosen[0] if chosen else None


def rule_prover(args: argparse.Namespace, rule: str) -> Path:
    return getattr(args, RULES[rule]["prover_option"])


def parse_prover_stats(text: str) -> dict | None:
    """A prover's statistics line (its last line on stderr) as {field: int}: udrhombus writes
    {"udrhombus_stats": {...}}, udtriangle "udtriangle: graphs=N refuted=N tu=N pass=N (open=N ...) ..."."""
    lines = text.strip().splitlines()
    if not lines:
        return None
    line = lines[-1].strip()
    if line.startswith("{"):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict) and len(value) == 1 and isinstance(next(iter(value.values())), dict):
            value = next(iter(value.values()))
        return {k: v for k, v in value.items() if type(v) is int} if isinstance(value, dict) else None
    stats = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
    return stats or None


def check_build(args: argparse.Namespace, rule: str, stats: dict) -> None:
    field = RULES[rule].get("mutant_field")
    if field is not None and stats.get(field) != 0:
        raise PruneError(f"{rule_prover(args, rule)} is a red-control build ({field} {stats.get(field)})")


def rule_preflight(args: argparse.Namespace, rule: str) -> None:
    """The prover on no input must run and print a statistics line (naming no mutant), before any work,
    so a wrong or red-control build is refused even at a level with no survivors."""
    prover = rule_prover(args, rule)
    result = subprocess.run([str(prover)], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    stats = parse_prover_stats(result.stderr)
    if result.returncode != 0 or result.stdout or stats is None or stats.get("graphs") != 0:
        raise PruneError(f"{prover} does not behave as the {rule} prover on empty input: {result.stderr[-300:]}")
    check_build(args, rule, stats)


def run_rule_part(args: argparse.Namespace, rule: str, codes: list[str], prefix: Path) -> tuple[Path, dict]:
    prover = rule_prover(args, rule)
    source = prefix.with_suffix(".g6")
    out = prefix.with_suffix(".jsonl")
    err = prefix.with_suffix(".stderr")
    write_lines(source, codes)
    with source.open("rb") as stdin, out.open("wb") as stdout, err.open("wb") as stderr:
        result = subprocess.run(nice([str(prover)]), stdin=stdin, stdout=stdout, stderr=stderr)
    if result.returncode != 0:
        raise PruneError(f"{prover.name} failed with status {result.returncode}: {err.read_text()[-500:]}")
    stats = parse_prover_stats(err.read_text())
    if stats is None:
        raise PruneError(f"{prover.name} wrote no statistics line ({prefix})")
    if stats.get("graphs") != len(codes):
        raise PruneError(f"{prover.name} statistics do not count the {len(codes)} graphs of {source.name}")
    check_build(args, rule, stats)
    return out, stats


def run_rule(args: argparse.Namespace, rule: str, survivors: list[str], workdir: Path
             ) -> tuple[list[str], dict, dict, int, float]:
    """The rule's prover on udfilter's survivors, in --jobs contiguous parts (it is deterministic per
    graph, so the concatenation is the bytes of one run). Returns the graphs it passes (in order), its
    verdict counts, its statistics (summed over parts, maxima for RULE_STATS_MAX), its silent passes
    (the rule's "silent" fields: graphs passed without a certificate for a reason other than finding
    none) and the wall time. The records stay on disk in <rule>.jsonl, one per survivor in order, and
    are streamed again when the certificates are written; here every line is checked to be a pass, or a
    refuted or tu record whose witness is exactly {<witness key>: ...} (the checker verifies the
    certificates themselves)."""
    spec = RULES[rule]
    name = rule_prover(args, rule).name
    out = workdir / f"{rule}.jsonl"
    start = time.monotonic()
    n = len(survivors)
    size = max(1, min(-(-n // args.jobs), RULE_PART_MAX))
    parts = [(k, survivors[k:k + size]) for k in range(0, n, size)]
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        results = list(executor.map(
            lambda part: run_rule_part(args, rule, part[1], workdir / f"{rule}-{part[0]:08d}"), parts))
    totals: dict = {"graphs": 0, "pass": 0, "refuted": 0, "tu": 0, **{key: 0 for key in spec["silent"]}}
    with out.open("wb") as stream:
        for path, stats in results:
            stream.write(path.read_bytes())
            for key, value in stats.items():
                if key == spec.get("mutant_field"):
                    continue
                totals[key] = max(totals.get(key, 0), value) if key in RULE_STATS_MAX else totals.get(key, 0) + value
    wall = time.monotonic() - start
    passed: list[str] = []
    counts = {"pass": 0, "refuted": 0, "tu": 0}
    count = 0
    for index, record in enumerate(iter_jsonl(out)):
        if index >= n:
            raise PruneError(f"{name} wrote more than {n} records for {n} graphs")
        verdict = record.get("verdict") if isinstance(record, dict) else None
        if verdict not in RULE_VERDICTS:
            raise PruneError(f"unexpected {name} verdict {verdict!r} for {survivors[index]}")
        if verdict == "pass":
            if set(record) != {"verdict"}:
                raise PruneError(f"{name} pass record with extra keys for {survivors[index]}")
            passed.append(survivors[index])
        else:
            witness = record.get("witness")
            if set(record) != {"verdict", "witness"} or not isinstance(witness, dict) or set(witness) != {spec["witness"]}:
                raise PruneError(f"malformed {name} {verdict} record for {survivors[index]}")
        counts[verdict] += 1
        count = index + 1
    if count != n:
        raise PruneError(f"{name} wrote {count} records for {n} graphs")
    if totals.get("graphs") != n or any(totals.get(v) != counts[v] for v in RULE_VERDICTS):
        raise PruneError(f"{name} statistics {totals} do not match its records {counts}")
    silent = sum(totals.get(key, 0) for key in spec["silent"])
    if silent:
        print(f"prune.py: WARNING: {name} passed {silent} graphs silently ({', '.join(spec['silent'])}): kept, "
              f"and counted as {rule}_silent_passes in the manifest", file=sys.stderr)
    return passed, counts, totals, silent, wall


def embed_command(args: argparse.Namespace, path: Path, seed: int) -> list[str]:
    return nice([str(args.python), "-u", str(args.udembed), str(path), "--seed", str(seed),
                 "--tries", str(args.tries), "--max-states", str(args.max_states),
                 "--unknown-file", ""])


def run_embed_process(args: argparse.Namespace, codes: list[str], seed: int, prefix: Path,
                      timeout: float) -> list[dict] | None:
    """Run one udembed process; None on timeout, else the records (validated)."""
    write_lines(prefix.with_suffix(".g6"), codes)
    out = prefix.with_suffix(".jsonl")
    err = prefix.with_suffix(".stderr")
    with out.open("wb") as stdout, err.open("wb") as stderr:
        try:
            result = subprocess.run(embed_command(args, prefix.with_suffix(".g6"), seed),
                                    stdout=stdout, stderr=stderr, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
    if result.returncode != 0:
        raise PruneError(f"udembed failed with status {result.returncode}: {err.read_text()}")
    records = read_jsonl(out)
    if len(records) != len(codes):
        raise PruneError(f"udembed wrote {len(records)} records for {len(codes)} graphs ({prefix})")
    for code, record in zip(codes, records):
        if record.get("g6") != code:
            raise PruneError(f"udembed records are out of order ({prefix})")
        if record.get("verdict") not in EMBED_VERDICTS:
            raise PruneError(f"unexpected embedder verdict {record.get('verdict')!r} for {code}")
    return records


def run_embedder(args: argparse.Namespace, survivors: list[str], workdir: Path
                 ) -> tuple[list[dict], dict, float]:
    """Embed the survivors in chunks; seeds equal 1 + global index, as one long run would use."""
    start = time.monotonic()
    chunks = [(k, survivors[k:k + args.chunk]) for k in range(0, len(survivors), args.chunk)]
    timeouts: list[str] = []
    chunk_timeouts = 0
    startup = 60.0

    def run_chunk(spec: tuple[int, list[str]]) -> tuple[int, list[dict]]:
        nonlocal chunk_timeouts
        offset, codes = spec
        prefix = workdir / f"part-{offset:08d}"
        records = run_embed_process(args, codes, 1 + offset, prefix,
                                    startup + args.graph_timeout * len(codes))
        if records is not None:
            return offset, records
        chunk_timeouts += 1
        records = []
        for i, code in enumerate(codes):
            single = workdir / f"single-{offset + i:08d}"
            got = run_embed_process(args, [code], 1 + offset + i, single, startup + args.graph_timeout)
            if got is None:
                timeouts.append(code)
                records.append({"g6": code, "verdict": "unknown"})
            else:
                records.extend(got)
        return offset, records

    results: list[tuple[int, list[dict]]] = []
    if chunks:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            results = list(executor.map(run_chunk, chunks))
    results.sort(key=lambda item: item[0])
    records = [record for _, chunk_records in results for record in chunk_records]
    if [r["g6"] for r in records] != survivors:
        raise PruneError("embedder records do not match the survivor list")
    stats = {"tries": args.tries, "max_states": args.max_states, "seed_base": 1,
             "chunk": args.chunk, "chunks": len(chunks), "graph_timeout_seconds": args.graph_timeout,
             "chunk_timeouts": chunk_timeouts, "graph_timeouts": timeouts}
    return records, stats, time.monotonic() - start


CHECK_CHUNK = int(os.environ.get("PRUNE_CHECK_CHUNK", "1000000"))   # certificates per udcheck process
# A cell of more than CHECK_PARALLEL_ABOVE records, with --jobs > 1, is checked in up to --jobs contiguous chunks
# at once (check_in_parallel; each chunk at most CHECK_CHUNK records). At or below it, and with --jobs 1, the
# check is exactly what it was: one call, or chunks of CHECK_CHUNK in turn.
CHECK_PARALLEL_ABOVE = int(os.environ.get("PRUNE_CHECK_PARALLEL_ABOVE", "20000"))


def checker(args: argparse.Namespace) -> Path:
    """The blind checker for the run's set: udcheck.py (set 74) or udcheck398.py, which is
    udcheck.py itself, unchanged and hash-checked, with the pinned 398 list."""
    return args.udcheck if args.forbidden_set == 74 else args.udcheck398


def checker_command(args: argparse.Namespace, n: int, m: int, graphs: Path, certs: Path,
                    unknown: Path, work_dir: Path | None = None) -> list[str]:
    """Without a rule, exactly the u(22) call of udcheck.py (udcheck398.py for set 398). With one
    (--rhombus), the rules' checker check/udcheck_rhombus.py on the whole file: udcheck.py's arguments
    plus --data-dir, --forbidden-set and --work-dir (its derived files, inside prune.py's work
    directory; RHOMBUS-SPEC.md Section 3)."""
    if rule_of(args):
        return nice([str(args.python), str(args.udcheck_rhombus), "--expect-n", str(n), "--expect-m", str(m),
                     "--graphs", str(graphs), "--unknown-file", str(unknown), "--data-dir", str(args.data_dir),
                     "--forbidden-set", str(args.forbidden_set),
                     *(["--work-dir", str(work_dir)] if work_dir is not None else []), str(certs)])
    return nice([str(args.python), str(checker(args)), "--expect-n", str(n), "--expect-m", str(m),
                 "--graphs", str(graphs), "--unknown-file", str(unknown), str(certs)])


def udcheck_process(args: argparse.Namespace, n: int, m: int, graphs: Path, certs: Path,
                    unknown: Path, work_dir: Path) -> subprocess.CompletedProcess:
    """One checker process. With a rule its derived files go to work_dir, created fresh here."""
    if rule_of(args):
        shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True)
    command = checker_command(args, n, m, graphs, certs, unknown, work_dir if rule_of(args) else None)
    return subprocess.run(command, capture_output=True, text=True)


def udcheck_once(args: argparse.Namespace, n: int, m: int, graphs: Path, certs: Path,
                 unknown: Path, work_dir: Path) -> tuple[str, str]:
    """One checker call. With a rule its derived files go to work_dir, a fresh directory that is
    removed after an ACCEPT (kept after a rejection, for the post-mortem)."""
    result = udcheck_process(args, n, m, graphs, certs, unknown, work_dir)
    if result.returncode != 0:
        raise PruneError(f"udcheck REJECTED the certificates: {result.stderr.strip()}")
    accept = [line for line in result.stdout.splitlines() if line.startswith("ACCEPT certificates")]
    if len(accept) != 1:
        raise PruneError("udcheck exited 0 without an ACCEPT line")
    if rule_of(args):
        shutil.rmtree(work_dir, ignore_errors=True)
    return accept[0], result.stdout + result.stderr


def line_cuts(path: Path, ranges: list[tuple[int, int]], total: int) -> list[int]:
    """Byte offsets cutting a file of one record per line at the chunk boundaries: bytes cuts[i]..cuts[i+1] are
    its lines ranges[i][0]..ranges[i][1]-1, so the chunks are the file's own bytes, in order, with nothing over."""
    cuts = [0]
    lines = position = 0
    with path.open("rb") as stream:
        for line in stream:
            lines += 1
            position += len(line)
            if len(cuts) <= len(ranges) and lines == ranges[len(cuts) - 1][1]:
                cuts.append(position)
    if lines != total:
        raise PruneError(f"{path.name} has {lines} lines, the level file {total} graphs")
    if len(cuts) != len(ranges) + 1 or cuts[-1] != path.stat().st_size:
        raise PruneError(f"{path.name} could not be cut at the chunk boundaries")
    return cuts


def unknown_cuts(unknown: Path, codes: list[str],
                 ranges: list[tuple[int, int]]) -> tuple[list[int], list[int]]:
    """Cut <n>-<m>.UNKNOWN.g6, the file prune.py wrote, at the chunk boundaries: bytes cuts[i]..cuts[i+1] are
    its entries whose graph lies in ranges[i], sizes[i] of them. Its entries must be a subsequence of the level
    file in its order; anything else (a duplicate, a foreign or blank line, a wrong order) fails here, before any
    chunk runs, where one checker call on the whole cell would reject it."""
    cuts, sizes = [0], [0]
    index = position = 0
    with unknown.open("rb") as stream:
        for raw in stream:
            code = raw[:-1].decode("ascii", errors="replace") if raw.endswith(b"\n") else None
            while code is not None and index < len(codes) and codes[index] != code:
                index += 1
            if code is None or index == len(codes):
                raise PruneError(f"{unknown.name} is not a subsequence of the level file in its order "
                                 f"(entry {sum(sizes) + 1}: {raw[:40]!r})")
            while index >= ranges[len(cuts) - 1][1]:
                cuts.append(position)
                sizes.append(0)
            sizes[-1] += 1
            position += len(raw)
            index += 1
    while len(sizes) < len(ranges):
        cuts.append(position)
        sizes.append(0)
    cuts.append(position)
    return cuts, sizes


def copy_bytes(source: Path, start: int, end: int, target: Path) -> None:
    with source.open("rb") as stream, target.open("wb") as out:
        stream.seek(start)
        remaining = end - start
        while remaining > 0:
            block = stream.read(min(remaining, 1 << 20))
            if not block:
                raise PruneError(f"{source} is shorter than when it was cut")
            out.write(block)
            remaining -= len(block)


def check_in_parallel(args: argparse.Namespace, n: int, m: int, certs: Path, unknown: Path, log: Path,
                      codes: list[str], chunking: dict) -> str:
    """The check of a cell of more than CHECK_PARALLEL_ABOVE records with --jobs > 1: contiguous chunks of
    ceil(N / jobs) records, at most CHECK_CHUNK (so more than --jobs chunks only above jobs * CHECK_CHUNK), run
    --jobs at a time. Each chunk gets its own graph list (the level's graphs lo..hi-1), certificates (the same
    lines of the certificate file, byte for byte), unknown list (the entries of the UNKNOWN file prune.py wrote
    that fall in the chunk, so the checker still compares that file with the verdicts) and work directory, all
    in check-chunks/, removed after its ACCEPT. Every chunk must ACCEPT with records = its size and unknown = its
    unknown entries; the ACCEPT counts are summed, rhombus_* and tri_* too. One REJECT (or a chunk that cannot
    be cut or run) fails the step with that chunk's range and reason; chunks not yet started are cancelled, and
    the rejected chunk's files and work directory are kept for the post-mortem. `chunking` receives the plan
    and each chunk's range, unknown count and wall time (the manifest's checker_chunking)."""
    total = len(codes)
    size = min(-(-total // args.jobs), CHECK_CHUNK)
    ranges = [(lo, min(lo + size, total)) for lo in range(0, total, size)]
    workers = min(args.jobs, len(ranges))
    chunking.update({"records": total, "above": CHECK_PARALLEL_ABOVE, "max_chunk": CHECK_CHUNK, "jobs": workers,
                     "chunk_size": size, "chunks": [{"range": [lo, hi]} for lo, hi in ranges]})
    chunk_dir = log.parent / "check-chunks"
    chunk_dir.mkdir(exist_ok=True)
    cert_offsets = line_cuts(certs, ranges, total)
    unknown_offsets, unknown_sizes = unknown_cuts(unknown, codes, ranges)

    def check_chunk(i: int) -> dict:
        lo, hi = ranges[i]
        tag = f"chunk-{lo:09d}"
        files = (chunk_dir / f"{tag}.g6", chunk_dir / f"{tag}.certs.jsonl", chunk_dir / f"{tag}.UNKNOWN.g6")
        write_lines(files[0], codes[lo:hi])
        copy_bytes(certs, cert_offsets[i], cert_offsets[i + 1], files[1])
        copy_bytes(unknown, unknown_offsets[i], unknown_offsets[i + 1], files[2])
        work_dir = chunk_dir / f"work-{lo:09d}"
        start = time.monotonic()
        result = udcheck_process(args, n, m, *files, work_dir)
        done = {"wall_seconds": round(time.monotonic() - start, 3), "output": result.stdout + result.stderr}
        accept = [line for line in result.stdout.splitlines() if line.startswith("ACCEPT certificates")]
        if result.returncode != 0:
            return {**done, "reject": result.stderr.strip() or f"exit status {result.returncode}"}
        if len(accept) != 1:
            return {**done, "reject": "udcheck exited 0 without an ACCEPT line"}
        said = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", accept[0])}
        if said.get("records") != hi - lo or said.get("unknown") != unknown_sizes[i]:
            return {**done, "reject": f"its ACCEPT line counts records={said.get('records')} unknown="
                                      f"{said.get('unknown')}, the chunk holds {hi - lo} and {unknown_sizes[i]}"}
        if rule_of(args):
            shutil.rmtree(work_dir, ignore_errors=True)
        for path in files:
            path.unlink()
        return {**done, "accept": accept[0]}

    results: list[dict | None] = [None] * len(ranges)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_chunk, i): i for i in range(len(ranges))}
        for future in as_completed(futures):
            if future.cancelled():
                continue
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as error:   # a chunk that cannot be cut or run fails the step like a rejection
                results[i] = {"wall_seconds": None, "output": "", "reject": f"{type(error).__name__}: {error}"}
            if "reject" in results[i]:
                for other in futures:
                    other.cancel()
    logs = []
    for i, ((lo, hi), result) in enumerate(zip(ranges, results)):
        entry = chunking["chunks"][i]
        if result is None:
            entry["not_run"] = True
            logs.append(f"# chunk {lo}:{hi} not run (another chunk was rejected)\n")
            continue
        entry.update({"unknown": unknown_sizes[i], "wall_seconds": result["wall_seconds"]})
        if "reject" in result:
            entry["rejected"] = True
        logs.append(f"# chunk {lo}:{hi}\n{result['output']}")
    log.write_text("".join(logs))
    rejected = [i for i, result in enumerate(results) if result is not None and "reject" in result]
    if rejected:
        not_run = results.count(None)
        raise PruneError("udcheck REJECTED the certificates: " + "; ".join(
            f"chunk {i + 1} of {len(ranges)} (records {ranges[i][0]}..{ranges[i][1] - 1} of the cell, lines "
            f"{ranges[i][0] + 1}..{ranges[i][1]} of {certs.name}; its files are kept in {chunk_dir}): "
            f"{results[i]['reject']}" for i in rejected)
            + (f" ({not_run} of {len(ranges)} chunks not run after the rejection)" if not_run else ""))
    if None in results:
        raise PruneError("a checker chunk did not run")
    totals: dict[str, int] = {}
    for result in results:
        for key, value in re.findall(r"(\w+)=(\d+)", result["accept"]):
            totals[key] = totals.get(key, 0) + int(value)
    if totals.get("records") != total or totals.get("unknown") != sum(unknown_sizes):
        raise PruneError(f"the chunks' ACCEPT lines count records={totals.get('records')} unknown="
                         f"{totals.get('unknown')}, the cell holds {total} and {sum(unknown_sizes)}")
    try:
        chunk_dir.rmdir()
    except OSError:
        pass
    # the kernel's seven counts, then every further count the checker reports, in its order
    standard = ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes")
    summary = " ".join(f"{key}={totals[key]}" for key in
                       (*standard, *(key for key in totals if key not in standard)) if key in totals)
    return f"ACCEPT certificates {summary} (parallel: {len(ranges)} chunks of at most {size}, {workers} at a time)"


def run_checker(args: argparse.Namespace, n: int, m: int, level: Path, certs: Path,
                unknown: Path, log: Path, codes: list[str],
                chunking: dict | None = None) -> tuple[str, float]:
    """Replay every certificate with the blind checker. A cell of more than CHECK_PARALLEL_ABOVE
    records with --jobs > 1 is checked in up to --jobs chunks at once (check_in_parallel, which fills
    `chunking`). Otherwise, as it always was: a cell above CHECK_CHUNK records is checked in
    consecutive chunks (each with its own graph list and unknown list, cut from the same files in the
    same order) so the checker's memory stays bounded, and the ACCEPT counts are summed; at or below
    CHECK_CHUNK it is the single call it always was."""
    start = time.monotonic()
    if len(codes) > CHECK_PARALLEL_ABOVE and args.jobs > 1:
        accept = check_in_parallel(args, n, m, certs, unknown, log, codes, chunking if chunking is not None else {})
        return accept, time.monotonic() - start
    if len(codes) <= CHECK_CHUNK:
        accept, output = udcheck_once(args, n, m, level, certs, unknown, log.parent / "check-work")
        log.write_text(output)
        return accept, time.monotonic() - start
    totals: dict[str, int] = {}
    chunks = 0
    logs: list[str] = []
    chunk_dir = log.parent / "check-chunks"
    chunk_dir.mkdir(exist_ok=True)
    with certs.open("r", encoding="utf-8") as stream:
        for lo in range(0, len(codes), CHECK_CHUNK):
            hi = min(lo + CHECK_CHUNK, len(codes))
            c_certs = chunk_dir / f"chunk-{lo:09d}.certs.jsonl"
            c_graphs = chunk_dir / f"chunk-{lo:09d}.g6"
            c_unknown = chunk_dir / f"chunk-{lo:09d}.UNKNOWN.g6"
            unknown_here: list[str] = []
            with c_certs.open("w", encoding="utf-8") as out:
                for index in range(lo, hi):
                    line = stream.readline()
                    if not line:
                        raise PruneError("certificate file is shorter than the level file")
                    out.write(line)
                    if json.loads(line).get("verdict") == "unknown":
                        unknown_here.append(codes[index])
            write_lines(c_graphs, codes[lo:hi])
            write_lines(c_unknown, unknown_here)
            accept, output = udcheck_once(args, n, m, c_graphs, c_certs, c_unknown, chunk_dir / f"work-{lo:09d}")
            logs.append(f"# chunk {lo}:{hi}\n{output}")
            for key, value in re.findall(r"(\w+)=(\d+)", accept):
                totals[key] = totals.get(key, 0) + int(value)
            chunks += 1
            for path in (c_certs, c_graphs, c_unknown):
                path.unlink()
        if stream.readline():
            raise PruneError("certificate file is longer than the level file")
    log.write_text("".join(logs))
    # the kernel's seven counts, then every further count the checker reports, in its order
    # (udcheck_rhombus.py: rhombus_tu, rhombus_refuted, tri_tu, tri_refuted); without a rule there are none
    standard = ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes")
    summary = " ".join(f"{key}={totals[key]}" for key in
                       (*standard, *(key for key in totals if key not in standard)) if key in totals)
    return f"ACCEPT certificates {summary} (chunked: {chunks} chunks of at most {CHECK_CHUNK})", time.monotonic() - start


def verify_outputs(level: Path, certs: Path, keep: Path, unknown: Path, rule: str | None = None) -> dict:
    """Independent re-read of the files on disk: keep + pruned must equal the input. With a rule,
    the records carrying its witness are counted as well (<prefix>_tu, <prefix>_refuted, prefix
    rhombus or tri; tu and refuted include them), and any OTHER rule's witness is a problem."""
    codes = read_g6(level)
    problems = []
    counts = {"records": 0, "tu": 0, "refuted": 0, "embedded": 0, "unknown": 0}
    witness_key = RULES[rule]["witness"] if rule else None
    prefix = RULES[rule]["count_prefix"] if rule else None
    foreign = {spec["witness"] for spec in RULES.values()} - {witness_key}
    if rule:
        counts.update({f"{prefix}_tu": 0, f"{prefix}_refuted": 0})
    expected_keep: list[str] = []
    expected_unknown: list[str] = []
    order_ok = True
    witness_problem: str | None = None
    partition_ok = True
    # One streamed pass: the graph list must equal the level file in order, every record is
    # either kept (embedded, unknown) or pruned (tu, refuted), which is the partition check.
    for index, r in enumerate(iter_jsonl(certs)):
        counts["records"] += 1
        code = r.get("g6")
        if index >= len(codes) or code != codes[index]:
            order_ok = False
        verdict = r.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
        if verdict in KEEP_VERDICTS:
            expected_keep.append(code)
        if verdict == "unknown":
            expected_unknown.append(code)
        if verdict in ("tu", "refuted", "embedded") and not isinstance(r.get("witness"), dict) and witness_problem is None:
            witness_problem = f"pruned or embedded record without witness: {code}"
        if rule and isinstance(r.get("witness"), dict) and witness_key in r["witness"]:
            if verdict in ("tu", "refuted"):
                counts[f"{prefix}_{verdict}"] += 1
            elif witness_problem is None:
                witness_problem = f"{witness_key} witness on a {verdict} record: {code}"
        if rule and isinstance(r.get("witness"), dict) and foreign & set(r["witness"]) and witness_problem is None:
            witness_problem = f"a witness of another rule ({sorted(foreign & set(r['witness']))}) for {code}"
        if verdict not in ("tu", "refuted", "embedded", "unknown"):
            partition_ok = False
    if counts["records"] != len(codes):
        order_ok = False
    if not order_ok:
        problems.append("certificate graph list differs from the level file")
    if read_g6(keep) != expected_keep:
        problems.append("keep file is not exactly the embedded and unknown records in order")
    if read_g6(unknown) != expected_unknown:
        problems.append("UNKNOWN file is not exactly the unknown records in order")
    if witness_problem:
        problems.append(witness_problem)
    if not partition_ok or not order_ok:
        problems.append("keep and pruned sets do not partition the level file")
    if problems:
        raise PruneError("output verification failed: " + "; ".join(problems))
    counts["kept"] = len(expected_keep)
    return counts


def main() -> int:
    args = parse_args()
    level = args.level.resolve()
    if not level.is_file():
        raise PruneError(f"level file not found: {level}")
    n, m = level_from_name(level)
    if args.target_n not in UPPER:
        raise PruneError(f"no proved upper bound on u({args.target_n}); TU pruning is not justified")
    if args.target_m < UPPER[args.target_n]:
        raise PruneError(f"target ({args.target_n},{args.target_m}) lies below the proved bound "
                         f"u({args.target_n}) <= {UPPER[args.target_n]}; TU pruning is not justified")
    if n > args.target_n or (n == args.target_n and m != args.target_m):
        raise PruneError(f"level ({n},{m}) is not an ancestor level of the target")
    if args.filter_set is None:
        args.filter_set = args.forbidden_set
    if args.filter_set == 398 and args.forbidden_set == 74:
        raise PruneError("--filter-set 398 in a set-74 run would call the tree's graphs that contain one of GP-10's "
                         "324 a generator bug; the filter set is the run's set or 74")
    tools = [args.python, args.udfilter, args.udembed, args.udcheck]
    if args.forbidden_set != 74:
        tools.append(args.udcheck398)
    rule = rule_of(args)
    if rule:
        tools += [rule_prover(args, rule), args.udcheck_rhombus]
        if os.environ.get(RHOMBUS_CHECKER_ENV):
            print(f"prune.py: NOTE: the rules' checker is {args.udcheck_rhombus} "
                  f"(from ${RHOMBUS_CHECKER_ENV}); the manifest records it", file=sys.stderr)
    for tool in tools:
        if not Path(tool).is_file():
            raise PruneError(f"missing tool: {tool}")
    if rule:
        rule_preflight(args, rule)
    forbidden_file = args.data_dir / FORBIDDEN_FILES[args.forbidden_set]
    if args.forbidden_set == 398 and sha256(forbidden_file) != FORBIDDEN_398_SHA256:
        raise PruneError(f"{forbidden_file} is not the pinned forbidden-398.json "
                         f"(sha256 {FORBIDDEN_398_SHA256})")
    outdir = level.parent
    stem = f"{n}-{m}"
    certs = outdir / f"{stem}.certs.jsonl"
    keep = outdir / f"{stem}.keep.g6"
    unknown = outdir / f"{stem}.UNKNOWN.g6"
    manifest = outdir / f"{stem}.prune.manifest.json"
    workdir = outdir / "_prune" / stem
    for path in (certs, keep, unknown, manifest):
        if path.exists() and not args.overwrite:
            raise PruneError(f"{path} exists, use --overwrite to replace it")
    # Keep completed filter parts (filter-<offset>.{g6,jsonl}) from an earlier killed run of the
    # same level: run_filter_part reuses a part only if its input is byte-identical to the codes
    # it is asked for. Everything else in the work directory is stale and removed. Parts made
    # with the other forbidden set are removed too: a set-398 part holds "forbidden" where a
    # set-74 part holds "tu" or "pass", so reusing one across sets could hide a generator bug.
    # The set of the parts is the file forbidden-set.txt (written only for set 398; no file means
    # set 74, which is every u(22) work directory). It is udfilter's set, the filter set.
    workdir.mkdir(parents=True, exist_ok=True)
    set_marker = workdir / "forbidden-set.txt"
    parts_set = set_marker.read_text().strip() if set_marker.is_file() else "74"
    for stale in workdir.iterdir():
        if (stale.name.startswith("filter-") and stale.suffix in (".g6", ".jsonl", ".stderr")
                and parts_set == str(args.filter_set)):
            continue
        if stale.is_dir():
            shutil.rmtree(stale)
        else:
            stale.unlink()
    if args.filter_set != 74:
        set_marker.write_text(f"{args.filter_set}\n")
    started = utc_now()
    total_start = time.monotonic()

    codes = read_g6(level)
    if len(set(codes)) != len(codes):
        raise PruneError("duplicate graph6 record in the level file")
    for code in codes:
        vertices, edges, _ = decode_graph6(code)
        if vertices != n or edges != m:
            raise PruneError(f"{code} has ({vertices},{edges}), expected ({n},{m})")

    gadgets = json.loads((args.data_dir / "tu-gadgets.json").read_text())
    if not isinstance(gadgets, list) or len(gadgets) != 6:
        raise PruneError("tu-gadgets.json must list the six gadgets")
    survivors, n_tu, filter_wall = run_filter(args, codes, workdir, gadgets)
    write_lines(workdir / "survivors.g6", survivors)
    # a rule (--rhombus): its prover on udfilter's survivors; only its pass graphs go on to the embedder
    to_embed = survivors
    if rule:
        to_embed, rule_counts, rule_stats, rule_silent, rule_wall = run_rule(args, rule, survivors, workdir)
        write_lines(workdir / f"{rule}-survivors.g6", to_embed)
    if args.filter_only:
        by_code = None   # every survivor is recorded unknown; no per-record dict is kept in memory
        embed_counts = {"embedded": 0, "refuted": 0, "unknown": len(to_embed)}
        embed_stats, embed_wall = {"skipped": True, "filter_only": True, "survivors": len(to_embed)}, 0.0
    else:
        embed_records, embed_stats, embed_wall = run_embedder(args, to_embed, workdir)
        by_code = {r["g6"]: r for r in embed_records}
        embed_counts = {v: sum(1 for r in embed_records if r["verdict"] == v)
                        for v in ("embedded", "refuted", "unknown")}

    # The certificate file is written in one streamed pass over filter.jsonl, in input order:
    # a tu record with its witness converted to the checker's schema, otherwise the embedder's
    # record (or {g6, unknown} in filter-only mode). Byte-identical to the former in-memory path.
    # With a rule, a udfilter survivor takes the next line of <rule>.jsonl (one per survivor, in
    # order): a refuted or tu record is written with the rule's witness, a pass goes on as above.
    unknown_codes: list[str] = []
    keep_codes: list[str] = []
    embedded_codes: list[str] = []
    rule_records = iter_jsonl(workdir / f"{rule}.jsonl") if rule else None
    with certs.open("w", encoding="utf-8") as stream:
        for code, filtered in zip(codes, iter_jsonl(workdir / "filter.jsonl")):
            rule_record = None
            if filtered["verdict"] != "tu" and rule_records is not None:
                rule_record = next(rule_records, None)
                if rule_record is None:
                    raise PruneError(f"{rule}.jsonl is shorter than the survivor list")
            if filtered["verdict"] == "tu":
                record = {"g6": code, "verdict": "tu",
                          "witness": convert_tu_witness(filtered.get("witness"), gadgets, code)}
            elif rule_record is not None and rule_record["verdict"] != "pass":
                record = {"g6": code, "verdict": rule_record["verdict"], "witness": rule_record["witness"]}
            elif by_code is None:
                record = {"g6": code, "verdict": "unknown"}
            else:
                record = by_code[code]
            verdict = record["verdict"]
            if verdict == "unknown":
                unknown_codes.append(code)
            if verdict == "embedded":
                embedded_codes.append(code)
            if verdict in KEEP_VERDICTS:
                keep_codes.append(code)
            stream.write(dump(record) + "\n")
    if rule_records is not None and next(rule_records, None) is not None:
        raise PruneError(f"{rule}.jsonl is longer than the survivor list")
    if args.mutation_unknown_as_pruned:
        unknown_codes = []
        keep_codes = embedded_codes
    write_lines(unknown, unknown_codes)
    write_lines(keep, keep_codes)

    problems: list[str] = []
    accept_line = ""
    check_wall = 0.0
    check_chunking: dict = {}   # filled only when the check runs in parallel chunks (manifest: checker_chunking)
    try:
        accept_line, check_wall = run_checker(args, n, m, level, certs, unknown, workdir / "udcheck.log", codes,
                                              check_chunking)
    except PruneError as error:
        problems.append(str(error))
    counts: dict = {}
    try:
        counts = verify_outputs(level, certs, keep, unknown, rule=rule)
    except PruneError as error:
        problems.append(str(error))
    if rule and accept_line and counts:
        # three counts of the rule's records must agree: the prover's, the file's and the checker's
        # (the checker's ACCEPT line names them <prefix>_tu and <prefix>_refuted, rhombus_ or tri_, and
        # its tu and refuted include them: RHOMBUS-SPEC.md Section 3)
        said = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", accept_line)}
        for verdict in ("tu", "refuted"):
            key = f"{RULES[rule]['count_prefix']}_{verdict}"
            if said.get(key) != rule_counts[verdict] or counts.get(key) != rule_counts[verdict]:
                problems.append(f"{key}: prover {rule_counts[verdict]}, certificate file {counts.get(key)}, "
                                f"checker {said.get(key)}")
        if said.get("tu") != n_tu + rule_counts["tu"] or \
                said.get("refuted") != embed_counts["refuted"] + rule_counts["refuted"]:
            problems.append(f"checker tu/refuted counts {said} do not include the {rule} records as the spec says")
    finished = utc_now()

    software = {
        "prune.py": sha256(Path(__file__).resolve()),
        "udfilter": sha256(args.udfilter),
        "udembed.py": sha256(args.udembed),
        "exact_verify.py": sha256(args.udembed.parent / "exact_verify.py"),
        "udcheck.py": sha256(args.udcheck),
        "python": f"{args.python} {platform.python_version()}",
    }
    if args.forbidden_set != 74:
        software["udcheck398.py"] = sha256(args.udcheck398)
    if rule:
        software[RULES[rule]["prover_option"]] = sha256(rule_prover(args, rule))
        software["udcheck_rhombus.py"] = sha256(args.udcheck_rhombus)
    inputs = {str(level): sha256(level),
              str(forbidden_file): sha256(forbidden_file),
              str(args.data_dir / "tu-gadgets.json"): sha256(args.data_dir / "tu-gadgets.json")}
    if args.filter_set != args.forbidden_set:   # udfilter read the filter set's file
        filter_file = args.data_dir / FORBIDDEN_FILES[args.filter_set]
        inputs[str(filter_file)] = sha256(filter_file)
    for item in args.record:
        name, _, path = item.partition("=")
        inputs[name] = sha256(Path(path))
    tu_rule_bound: dict = {"n": args.target_n, "proved_upper_bound": UPPER[args.target_n]}
    if args.target_n in UPPER_SOURCE:
        tu_rule_bound["source"] = UPPER_SOURCE[args.target_n]
    outputs = {str(certs): sha256(certs), str(keep): sha256(keep),
               str(unknown): sha256(unknown),
               str(workdir / "filter.jsonl"): sha256(workdir / "filter.jsonl"),
               str(workdir / "survivors.g6"): sha256(workdir / "survivors.g6")}
    rule_entries: dict = {}
    if rule:
        outputs[str(workdir / f"{rule}.jsonl")] = sha256(workdir / f"{rule}.jsonl")
        outputs[str(workdir / f"{rule}-survivors.g6")] = sha256(workdir / f"{rule}-survivors.g6")
        rule_entries = {rule: True,
                        f"{rule}_prover": {"path": str(rule_prover(args, rule)), "witness": RULES[rule]["witness"]},
                        f"{rule}_checker": {"path": str(args.udcheck_rhombus),
                                            "from_environment": bool(os.environ.get(RHOMBUS_CHECKER_ENV)),
                                            "command": " ".join(checker_command(args, n, m, level, certs, unknown,
                                                                                workdir / "check-work"))},
                        f"{rule}_stats": rule_stats,
                        f"{rule}_silent_passes": rule_silent}
    counts_value = {"input": len(codes), "tu": n_tu, "survivors": len(survivors)}
    if rule:
        prefix = RULES[rule]["count_prefix"]
        counts_value.update({f"{prefix}_tu": rule_counts["tu"], f"{prefix}_refuted": rule_counts["refuted"],
                             f"{prefix}_silent_passes": rule_silent, f"{prefix}_survivors": len(to_embed)})
    counts_value.update({"embedded": embed_counts["embedded"],
                         "refuted": embed_counts["refuted"],
                         "unknown": embed_counts["unknown"],
                         "kept": len(keep_codes), "pruned": len(codes) - len(keep_codes)})
    wall_value = {"filter": filter_wall}
    if rule:
        wall_value[rule] = rule_wall
    wall_value.update({"embed": embed_wall, "check": check_wall, "total": time.monotonic() - total_start})
    value = {
        "kind": "prune",
        "level": [n, m],
        "level_file": str(level),
        "target": [args.target_n, args.target_m],
        **({"forbidden_set": args.forbidden_set} if args.forbidden_set != 74 else {}),
        **({"filter_set": args.filter_set} if args.filter_set != args.forbidden_set else {}),
        **rule_entries,
        "tu_rule_bound": tu_rule_bound,
        "software_sha256": software,
        "inputs_sha256": inputs,
        "outputs_sha256": outputs,
        "counts": counts_value,
        "embedder": embed_stats,
        "jobs": args.jobs,
        "wall_seconds": wall_value,
        "checker": accept_line,
        **({"checker_chunking": check_chunking} if check_chunking else {}),
        "verified_counts": counts,
        "mutation": {"unknown_as_pruned": bool(args.mutation_unknown_as_pruned)},
        "started": started,
        "finished": finished,
        "host": socket.gethostname(),
        "exit_status": 1 if problems else 0,
        "problems": problems,
    }
    manifest.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"level": [n, m], "counts": value["counts"], "wall_seconds": value["wall_seconds"],
                      "checker": accept_line, "problems": problems}))
    if problems:
        print("prune.py: RED: " + " | ".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PruneError, subprocess.CalledProcessError) as error:
        print(f"prune.py: {error}", file=sys.stderr)
        raise SystemExit(2)
