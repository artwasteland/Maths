#!/usr/bin/env python3
"""replay-398: replay a seeded sample of a production run's parent records with enum2.

Gate G4 of research/unit-distance-23/CONTRACT.md (section 4.4): "an independent replay of
a stated fraction of shards by an enumerator sharing no code with udenum (u(22)'s enum2,
extended to the 398), with a red control".  enum2 shares no code with udenum; this tool
reads only the run directory's files and manifests.

USAGE

  replay-398.py --run-dir DIR [--run-dir DIR ...] --fraction F --seed S --out OUTDIR
                [--forbidden-set 398|74|auto] [--min-per-shard K] [--whole-max K]
                [--max-per-shard K] [--levels A-B] [--cells n-m,...] [--seeds off|sample|full]
                [--stages check|off] [--no-parent-check] [--workers W] [--resume] [--red]
                [--plan-only]

  Example (one u(23) slice, 0.5% of every shard, at least 2 parents per shard, shards of at
  most 400 parents whole, level-10 seeds recomputed in full, red controls, 4 cores):
    nice -n 15 ~/tools/pyenv-maths/bin/python replay-398.py --run-dir <slice dir> \\
        --forbidden-set 398 --fraction 0.005 --seed <published seed> --min-per-shard 2 \\
        --whole-max 400 --seeds full --red --workers 4 --out <out dir>
  --plan-only prints the per-cell sample sizes from the manifests alone.

  DIR     a run directory of enum/run-dag2.py (a u(23) slice, a u(22) slice, a calibration
          run): level stage files <n>-<m>.g6 (+ .reach.g6, .keep.g6, .slice-*.g6), their
          aggregate manifests <n>-<m>.manifest.json, optionally _parents/ and shards/.
  F, S    the stated fraction and the seed.  The sample is stratified by production shard:
          for every augmentation cell (n, m) and every shard [a, b) of its parent range (read
          from the aggregate manifest's list of shard files; the whole range when they do not
          tile it), k = min(b-a, max(K_min, ceil(F * (b-a)))) parent records (every record when
          b-a <= whole-max; at most --max-per-shard), drawn without replacement by
          random.Random("S/<run dir name>/n-m/a-b").  So every shard is touched, and the
          sample of a copied or moved run directory is the same.
  OUTDIR  replay.jsonl (one line per replayed parent, streamed; --resume continues it),
          summary.json (per cell, per level, totals, timing, hashes), red.json (--red).

WHAT IS COMPARED, PER SAMPLED PARENT
  The parent is record i of the cell's parent sequence: the concatenation, in manifest
  order, of the files named in the aggregate manifest's parent_sources (each located by its
  path, else by its base name in the run directory, and checked against the manifest's
  sha256 and record count; the concatenation's sha256 must equal the manifest's hash of
  the parent file udenum read).  enum2 computes the parent's children for the cell's target
  (n, m).  The production children of that parent are recovered from the cell's children
  file <n>-<m>.g6 (checked against the aggregate manifest; it is the file the next level's
  stage files are made from; only when it is absent, from the shard file covering i, checked
  against the shard manifest): udenum writes children in parent order, and the parent of a
  canonical child is the child minus its first minimum-degree vertex, canonicalised
  (CROSSCHECK.md 2.3), so the children
  of parent i are one contiguous block, found by binary search on the recovered parent
  index; every line of the block must recover to i, the line before it to an index < i
  and the line after it to an index > i.
  identical  <=>  set(enum2 children) == set(block)  and the block has no repeated line.
  (Equal counts and one-sided inclusion are reported, never used: --red shows them passing
  on broken outputs.)  Also checked per parent: the record is canonical graph6, it contains
  none of the forbidden graphs (--no-parent-check skips this), and every enum2 child
  recovers to the parent.

STAGES BETWEEN LEVELS (--stages check, the default)
  Every parent source of a replayed cell is re-derived, in full, from the file it was made
  from: a reach file = the level file's records with minimum degree >= k (k from its
  manifest, equal to reach.json's table); a slice file = its input's records whose slice
  number (sha256 of the record, first 8 bytes big-endian, mod count) is the slice index;
  a keep file (TU pruning, certified by prune.py and its checker, not by this tool) must be
  an order-preserving subsequence of its input.  So a replayed parent sequence is tied to
  the previous level's production output, not only to its manifest.

SEED LEVELS (cells without parent_sources: geng + the Mode-398 filter)
  --seeds sample: the sampled seed records are canonical and forbidden-free.
  --seeds full: additionally, the seed file of (10, m) must equal, as a set, enum2's
  canonical augmentation of every forbidden-free graph on 9 vertices (nauty-geng + enum2's
  own decider) with m edges.  Seeds of other orders are only checked by sample.

RED CONTROLS (--red, on this run's own data; each must turn the verdict red)
  R1 mutated parent:   one edge of a sampled parent flipped, re-canonicalised; its enum2
                       children against the original production block.
  R2 dropped record:   one line removed from a non-empty production block.
  R3 member dropped:   enum2 without one member of the 324 (Mode 398 only), on a parent where
                       that member alone rejects a child: extra children.  The parent is taken
                       from the sample first; a small sample may hold none, so then from further
                       parents of the replayed cells, per cell in a seeded order (the seed S),
                       each re-checked identical to its production block before it is used (one
                       that is not is reported as a discrepancy, never as red); --red-budget
                       processed parents are tried in all.
  R4 wrong block:      enum2's children of parent i against the block of parent i+1.
  R5 wrong checks:     a block with one record replaced by another graph of the cell passes
                       the equal-count check and fails the set check; enum2's set minus one
                       record passes the subset check and fails the set check.

Exit status 0 iff every sampled parent is identical, every sampled cell was replayable,
and (with --red) every control went red.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import time
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enum2  # noqa: E402

CELL_MANIFEST = re.compile(r"^(\d+)-(\d+)\.manifest\.json$")
GENG = "/usr/bin/nauty-geng"


# ------------------------------------------------------------------ small helpers
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_record(line: bytes) -> bool:
    return bool(line.strip()) and not line.startswith(b">>graph6<<")


def read_records(path: Path) -> list[str]:
    out = []
    with Path(path).open("rb") as stream:
        for line in stream:
            if is_record(line):
                out.append(line.strip().decode("ascii"))
    return out


def recover_parent(code: str) -> str:
    """Canonical graph6 of a canonical child minus its first minimum-degree vertex."""
    g = enum2.graph6_decode(code)
    degrees = [g.degree(v) for v in range(g.n)]
    w = degrees.index(min(degrees))
    keep = [v for v in range(g.n) if v != w]
    adj = []
    for v in keep:
        row = 0
        for j, u in enumerate(keep):
            if (g.adj[v] >> u) & 1:
                row |= 1 << j
        adj.append(row)
    return enum2.canonical_g6(enum2.Graph(tuple(adj)))


def compare(block: list[str], kids: list[str]) -> dict:
    bs, ks = set(block), set(kids)
    only_p = sorted(bs - ks)
    only_e = sorted(ks - bs)
    return {"production": len(block), "production_distinct": len(bs), "enum2": len(ks),
            "enum2_raw": len(kids), "only_production": len(only_p), "only_enum2": len(only_e),
            "only_production_first": only_p[:5], "only_enum2_first": only_e[:5],
            "equal_counts": len(block) == len(ks), "enum2_subset_of_production": ks <= bs,
            "identical": not only_p and not only_e and len(block) == len(bs)}


class LineFile:
    """Random access to the records of a text file (one graph6 per line)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.offsets = array("q")
        self.lengths = array("i")
        pos = 0
        with self.path.open("rb") as stream:
            for line in stream:
                if is_record(line):
                    self.offsets.append(pos)
                    self.lengths.append(len(line.rstrip(b"\r\n")))
                pos += len(line)
        self.stream = self.path.open("rb")

    def __len__(self) -> int:
        return len(self.offsets)

    def __getitem__(self, i: int) -> str:
        self.stream.seek(self.offsets[i])
        return self.stream.read(self.lengths[i]).decode("ascii").strip()

    def close(self) -> None:
        self.stream.close()


# ------------------------------------------------------------------ the run directory
class Cell:
    def __init__(self, run_dir: Path, n: int, m: int, manifest: dict, search_dirs: list[Path]):
        self.run_dir = run_dir
        self.n, self.m = n, m
        self.name = f"{n}-{m}"
        self.manifest = manifest
        self.search_dirs = search_dirs
        self.problems: list[str] = []
        self.parents: list[str] | None = None
        self.sources: list[dict] = []

    @property
    def is_seed(self) -> bool:
        return str(self.manifest.get("shard_id", "")).startswith("seed-")

    def locate(self, recorded: str, want_sha: str | None) -> tuple[Path, bytes] | None:
        """The file a manifest names: at its recorded path, else by its base name in one of the
        run directories; accepted only with the manifest's sha256.  Returns (path, bytes)."""
        name = Path(recorded).name
        candidates = ([Path(recorded)] + [d / name for d in self.search_dirs] +
                      [d / "_parents" / name for d in self.search_dirs])
        for c in candidates:
            if c.is_file():
                data = c.read_bytes()
                if want_sha is None or hashlib.sha256(data).hexdigest() == want_sha:
                    return c, data
        return None

    def load_parents(self) -> bool:
        """The parent sequence udenum read, rebuilt from parent_sources and checked (a manifest
        without parent_sources, from enum/run-dag.py, names only the concatenated parent file:
        then that file itself, hash-checked, is the sequence and there are no stages to check)."""
        seq: list[str] = []
        digest = hashlib.sha256()
        if "parent_sources" not in self.manifest:
            recorded = self.manifest.get("parent_file", "")
            want = self.manifest.get("inputs_sha256", {}).get(recorded)
            found = self.locate(recorded, want) if recorded and want else None
            if found is None:
                self.problems.append(f"no parent_sources, and the parent file {recorded} is missing or changed")
                return False
            seq = [ln.strip().decode("ascii") for ln in found[1].split(b"\n") if is_record(ln)]
            if len(seq) != int(self.manifest["parent_range"][1]):
                self.problems.append(f"parent file has {len(seq)} records, manifest range says "
                                     f"{self.manifest['parent_range'][1]}")
                return False
            self.parent_concat_sha256 = want
            self.parents = seq
            return True
        for src in self.manifest["parent_sources"]:
            found = self.locate(src["file"], src.get("sha256"))
            if found is None:
                self.problems.append(f"parent source {src['file']} not found with sha256 {src.get('sha256')}")
                return False
            path, data = found
            digest.update(data)
            records = [ln.strip().decode("ascii") for ln in data.split(b"\n") if is_record(ln)]
            if len(records) != int(src["records"]):
                self.problems.append(f"{path}: {len(records)} records, manifest says {src['records']}")
                return False
            self.sources.append({"level": src["level"], "d": src["d"], "kind": src.get("kind"),
                                 "file": str(path), "records": len(records), "offset": len(seq)})
            seq.extend(records)
        total = int(self.manifest["parent_range"][1])
        if len(seq) != total:
            self.problems.append(f"parent sequence has {len(seq)} records, manifest range says {total}")
            return False
        want = self.manifest.get("inputs_sha256", {}).get(self.manifest.get("parent_file"))
        self.parent_concat_sha256 = digest.hexdigest()
        if want is not None and want != self.parent_concat_sha256:
            self.problems.append("the concatenated parent sources do not hash to the manifest's parent file")
            return False
        self.parents = seq
        return True

    def children_file(self) -> Path | None:
        path = self.run_dir / f"{self.name}.g6"
        if not path.is_file():
            self.problems.append(f"{path} missing")
            return None
        if sha256_file(path) != self.manifest.get("children_file_sha256"):
            self.problems.append(f"{path}: sha256 differs from the aggregate manifest")
            return None
        with path.open("rb") as stream:
            lines = sum(1 for line in stream if is_record(line))
        if lines != int(self.manifest.get("children_written", -1)):
            self.problems.append(f"{path}: {lines} records, the manifest says {self.manifest.get('children_written')}")
            return None
        return path

    def _shard_table(self) -> list[tuple[int, int, Path, str]]:
        if getattr(self, "_shards", None) is None:
            table = []
            shard_dir = self.run_dir / "shards" / self.name
            if shard_dir.is_dir():
                for mf in shard_dir.glob(f"{self.name}-*.manifest.json"):
                    try:
                        info = json.loads(mf.read_text())
                        start, end = (int(x) for x in info["parent_range"])
                    except (ValueError, KeyError, OSError, json.JSONDecodeError):
                        continue
                    table.append((start, end, shard_dir / f"{info['shard_id']}.g6",
                                  info.get("children_file_sha256", "")))
            table.sort()
            self._shards = table
            self._shard_ok: dict[Path, bool] = {}
        return self._shards

    def shard_for(self, i: int) -> tuple[Path, int, int] | None:
        """(shard file, start, end) covering parent i, if the file exists and matches its
        manifest (checked once per shard); otherwise None and the cell file is used."""
        for start, end, path, want in self._shard_table():
            if start <= i < end:
                if path not in self._shard_ok:
                    self._shard_ok[path] = path.is_file() and sha256_file(path) == want
                return (path, start, end) if self._shard_ok[path] else None
        return None


def forbidden_sets_named(manifest: dict) -> tuple[str, ...]:
    """The pinned forbidden sets whose file hash the manifest lists among its inputs."""
    hashes = set(manifest.get("inputs_sha256", {}).values())
    return tuple(name for name, spec in enum2.FORBIDDEN_SPECS.items() if spec.sha256 in hashes)


def discover(run_dirs: list[Path]) -> list[Cell]:
    cells = []
    for rd in run_dirs:
        for mf in sorted(rd.glob("*.manifest.json")):
            match = CELL_MANIFEST.match(mf.name)
            if not match:
                continue
            n, m = int(match.group(1)), int(match.group(2))
            manifest = json.loads(mf.read_text())
            cells.append(Cell(rd, n, m, manifest, [rd] + [d for d in run_dirs if d != rd]))
    cells.sort(key=lambda c: (c.n, c.m, str(c.run_dir)))
    return cells


# ------------------------------------------------------------------ block location
class BlockFinder:
    """The production children of parent i: a contiguous block of a children file."""

    def __init__(self, lines: LineFile, parents: list[str], lo: int, hi: int):
        self.lines = lines
        self.index = {parents[j]: j for j in range(lo, hi)}
        self.cache: dict[int, int] = {}
        self.recoveries = 0

    def parent_index(self, line_no: int) -> int:
        if line_no not in self.cache:
            self.recoveries += 1
            parent = recover_parent(self.lines[line_no])
            if parent not in self.index:
                raise LookupError(f"line {line_no} of {self.lines.path}: recovered parent {parent} "
                                  f"is not a parent record of this range")
            self.cache[line_no] = self.index[parent]
        return self.cache[line_no]

    def block(self, i: int) -> tuple[int, int]:
        lo, hi = 0, len(self.lines)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.parent_index(mid) < i:
                lo = mid + 1
            else:
                hi = mid
        start = lo
        end = start
        while end < len(self.lines) and self.parent_index(end) == i:
            end += 1
        if start > 0 and not self.parent_index(start - 1) < i:
            raise LookupError(f"block of parent {i}: the line before it does not come from an earlier parent")
        if end < len(self.lines) and not self.parent_index(end) > i:
            raise LookupError(f"block of parent {i}: the line after it does not come from a later parent")
        return start, end


# ------------------------------------------------------------------ enum2 side
_FS: dict[str, enum2.ForbiddenSet] = {}


def forbidden(name: str, drop: tuple[int, ...] = ()) -> enum2.ForbiddenSet:
    key = f"{name}/{','.join(map(str, drop))}"
    if key not in _FS:
        _FS[key] = enum2.load_forbidden_set(name, drop_members=drop)
    return _FS[key]


def enum2_children(record: str, m: int, set_name: str, check_parent: bool,
                   drop: tuple[int, ...] = ()) -> dict:
    fs = forbidden(set_name, drop)
    g = enum2.graph6_decode(record)
    stats: dict = {}
    t0 = time.process_time()
    kids = list(enum2.extend_parent(g, m, fs, stats=stats))
    seconds = time.process_time() - t0
    out = {"kids": kids, "seconds": seconds, "processed": stats.get("parents_processed", 0) > 0,
           "d": m - g.m}
    if check_parent:
        t1 = time.process_time()
        out["canonical"] = enum2.canonical_g6(g) == record
        hit = forbidden(set_name).tester.first(g)
        out["parent_contains"] = hit
        out["parent_check_seconds"] = time.process_time() - t1
    return out


def _pool_task(args: tuple) -> dict:
    record, m, set_name, check_parent = args
    return enum2_children(record, m, set_name, check_parent)


# ------------------------------------------------------------------ sampling
SHARD_NAME = re.compile(r"(\d+)-(\d+)-(\d+)-(\d+)\.g6$")


def strata(cell: Cell, total: int) -> tuple[list[tuple[int, int]], str]:
    """The production shards of a cell as parent ranges, from the aggregate manifest's list
    of shard files (so it works after shard files are deleted); one stratum [0, total) when
    they do not tile the parent range."""
    ranges = set()
    for path in cell.manifest.get("inputs_sha256", {}):
        mt = SHARD_NAME.search(Path(path).name)
        if mt and int(mt.group(1)) == cell.n and int(mt.group(2)) == cell.m and "/shards/" in path:
            ranges.add((int(mt.group(3)), int(mt.group(4))))
    ranges = sorted(ranges)
    pos = 0
    for start, end in ranges:
        if start != pos or end < start:
            break
        pos = end
    else:
        if ranges and pos == total:
            return ranges, "shards"
    return [(0, total)], "cell"


def sample_indices(seed: str, run_label: str, cell: str, total: int, fraction: float,
                   minimum: int, whole_max: int, maximum: int | None,
                   ranges: list[tuple[int, int]] | None = None) -> list[int]:
    """The seeded sample: per stratum (production shard) [a, b), every record when b - a <=
    whole_max, else k = min(b - a, max(minimum, ceil(fraction * (b - a)))) records (at most
    maximum), drawn without replacement by random.Random("seed/run/cell/a-b")."""
    out: list[int] = []
    for a, b in (ranges or [(0, total)]):
        size = b - a
        if size <= 0:
            continue
        if size <= whole_max:
            out.extend(range(a, b))
            continue
        k = min(size, max(minimum, math.ceil(fraction * size)))
        if maximum is not None:
            k = min(k, maximum)
        rng = random.Random(f"{seed}/{run_label}/{cell}/{a}-{b}")
        out.extend(sorted(rng.sample(range(a, b), k)))
    return sorted(out)


def parse_levels(spec: str) -> tuple[int, int] | None:
    if not spec:
        return None
    a, _, b = spec.partition("-")
    return int(a), int(b or a)


# ------------------------------------------------------------------ seeds
def g9_free(set_name: str) -> list[str]:
    fs = forbidden(set_name)
    out = []
    raw = subprocess.run([GENG, "-q", "9"], check=True, stdout=subprocess.PIPE, text=True).stdout.split()
    for code in raw:
        g = enum2.graph6_decode(code)
        if not fs.tester.contains(g):
            out.append(enum2.canonical_g6(g))
    return sorted(set(out))


def check_seed(cell: Cell, set_name: str, mode: str, seed: str, fraction: float, minimum: int,
               g9: list[str] | None) -> dict:
    path = cell.run_dir / f"{cell.name}.g6"
    rec = {"cell": cell.name, "run_dir": str(cell.run_dir), "kind": "seed"}
    if not path.is_file() or sha256_file(path) != cell.manifest.get("children_file_sha256"):
        rec.update({"replayable": False, "problem": "seed file missing or not matching its manifest"})
        return rec
    records = read_records(path)
    idx = sample_indices(seed, cell.run_dir.name, cell.name, len(records), fraction, minimum, 0, None)
    fs = forbidden(set_name)
    bad = []
    for i in idx:
        g = enum2.graph6_decode(records[i])
        if enum2.canonical_g6(g) != records[i] or fs.tester.contains(g) or g.n != cell.n or g.m != cell.m:
            bad.append(records[i])
    rec.update({"replayable": True, "records": len(records), "sampled": len(idx), "sample_bad": bad[:5],
                "sample_ok": not bad})
    if mode == "full" and cell.n == 10 and g9 is not None:
        t0 = time.process_time()
        mine = set()
        for code in g9:
            mine.update(enum2.extend_parent(enum2.graph6_decode(code), cell.m, fs))
        cmp_ = compare(records, sorted(mine))
        rec.update({"full_check": True, "enum2_records": cmp_["enum2"], "only_seed_file": cmp_["only_production"],
                    "only_enum2": cmp_["only_enum2"], "full_identical": cmp_["identical"],
                    "full_seconds": round(time.process_time() - t0, 1)})
    rec["identical"] = rec["sample_ok"] and rec.get("full_identical", True)
    return rec


# ------------------------------------------------------------------ stage files between levels
def min_degree(code: str) -> int:
    g = enum2.graph6_decode(code)
    return min((g.degree(v) for v in range(g.n)), default=0)


def slice_number(code: str, count: int) -> int:
    """The slice rule as run-dag2's slice manifests state it: sha256(graph6 record), first 8
    bytes big-endian, mod count."""
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big") % count


def check_stage(cell: Cell, src: dict, cache: dict) -> dict:
    """Re-derive one parent source of a cell from the file it was made from.

    reach: the records of <n>-<m>.g6 with minimum degree >= k (k from its manifest, and equal
           to reach.json's table when the run directory has one), in order;
    slice: the records of its input stage file whose slice number is the slice index, in order,
           then the input stage itself is checked;
    keep:  (TU pruning, certified by prune.py and its checker, not re-derived here) must be an
           order-preserving subsequence of its input (the reach file, else the full file);
    full:  the level file itself: nothing between the levels."""
    key = (src["file"], src.get("sha256"))
    if key in cache:
        return cache[key]
    n, m = (int(x) for x in src["level"])
    kind = src.get("kind", "full")
    rec = {"source": Path(src["file"]).name, "level": [n, m], "kind": kind}
    found = cell.locate(src["file"], src.get("sha256"))
    if found is None:
        rec.update({"status": "missing", "ok": False})
        cache[key] = rec
        return rec
    records = [ln.strip().decode("ascii") for ln in found[1].split(b"\n") if is_record(ln)]
    rec.update(_check_stage_records(cell, n, m, kind, records))
    cache[key] = rec
    return rec


def _stage_input(cell: Cell, manifest_name: str) -> tuple[dict | None, list[str] | None, str]:
    path = cell.run_dir / manifest_name
    if not path.is_file():
        return None, None, f"{manifest_name} missing"
    info = json.loads(path.read_text())
    found = cell.locate(info["input_file"], info.get("input_sha256"))
    if found is None:
        return info, None, f"input {Path(info['input_file']).name} of {manifest_name} missing or changed"
    return info, [ln.strip().decode("ascii") for ln in found[1].split(b"\n") if is_record(ln)], ""


def _check_stage_records(cell: Cell, n: int, m: int, kind: str, records: list[str]) -> dict:
    if kind == "full":
        return {"status": "no stage", "ok": True}
    if kind.endswith("+slice"):
        base_kind = kind[:-len("+slice")]
        mf = [p for p in cell.run_dir.glob(f"{n}-{m}.slice-*-of-*.manifest.json")]
        if len(mf) != 1:
            return {"status": f"{len(mf)} slice manifests for ({n},{m})", "ok": False}
        info, inputs, problem = _stage_input(cell, mf[0].name)
        if inputs is None:
            return {"status": problem, "ok": False}
        index, count = (int(x) for x in info["slice"])
        derived = [r for r in inputs if slice_number(r, count) == index]
        inner = _check_stage_records(cell, n, m, base_kind, inputs)
        ok = derived == records and inner["ok"]
        return {"status": "re-derived" if ok else "MISMATCH", "ok": ok, "slice": [index, count],
                "input_records": len(inputs), "records": len(records), "derived_records": len(derived),
                "input_stage": inner}
    if kind == "reach":
        info, inputs, problem = _stage_input(cell, f"{n}-{m}.reach.manifest.json")
        if inputs is None:
            return {"status": problem, "ok": False}
        k = int(info["k"])
        table_k = None
        reach_json = cell.run_dir / "reach.json"
        if reach_json.is_file():
            table_k = json.loads(reach_json.read_text()).get("table", {}).get(str(n), {}).get(str(m))
        derived = [r for r in inputs if min_degree(r) >= k]
        ok = derived == records and (table_k is None or int(table_k) == k)
        return {"status": "re-derived" if ok else "MISMATCH", "ok": ok, "k": k, "reach_json_k": table_k,
                "input_records": len(inputs), "records": len(records), "derived_records": len(derived)}
    if kind == "keep":
        base = cell.run_dir / f"{n}-{m}.reach.g6"
        if not base.is_file():
            base = cell.run_dir / f"{n}-{m}.g6"
        if not base.is_file():
            return {"status": "keep input missing", "ok": False}
        inputs = read_records(base)
        it = iter(inputs)
        subsequence = all(any(r == x for x in it) for r in records)
        return {"status": "subsequence of its input" if subsequence else "NOT A SUBSEQUENCE",
                "ok": subsequence, "input": base.name, "input_records": len(inputs),
                "records": len(records), "pruned": len(inputs) - len(records)}
    return {"status": f"unknown stage kind {kind}", "ok": False}


# ------------------------------------------------------------------ the replay
def replay_cell(cell: Cell, idx: list[int], set_name: str, args, jsonl, done: set, pool) -> list[dict]:
    results = []
    todo = [i for i in idx if (str(cell.run_dir), cell.name, i) not in done]
    if not todo:
        return results
    tasks = [(cell.parents[i], cell.m, set_name, not args.no_parent_check) for i in todo]
    computed = pool.imap(_pool_task, tasks, chunksize=1) if pool else map(_pool_task, tasks)
    # The cell file is what propagates (the next level's stage files are made from it), so
    # blocks are taken from it; a shard file (checked against its own manifest) is used only
    # when the cell file is absent.
    cell_file = cell.children_file()
    if cell_file is None and (cell.run_dir / f"{cell.name}.g6").exists():
        # present but not what the manifest says: never fall back to the shards
        raise LookupError("; ".join(cell.problems))
    finders: dict[tuple, BlockFinder] = {}
    try:
        for i, got in zip(todo, computed):
            record = cell.parents[i]
            if cell_file is not None:
                if ("whole",) not in finders:
                    finders[("whole",)] = BlockFinder(LineFile(cell_file), cell.parents, 0, len(cell.parents))
                finder = finders[("whole",)]
                where = "cell file"
            else:
                shard = cell.shard_for(i)
                if shard is None:
                    raise LookupError("; ".join(cell.problems) + f"; no verified shard file covers parent {i}")
                key = shard
                if key not in finders:
                    for old_key in list(finders):
                        finders.pop(old_key).lines.close()
                    finders[key] = BlockFinder(LineFile(shard[0]), cell.parents, shard[1], shard[2])
                finder = finders[key]
                where = f"shard {shard[0].name}"
            before = finder.recoveries
            start, end = finder.block(i)
            block = [finder.lines[j] for j in range(start, end)]
            res = compare(block, got["kids"])
            wrong_parent = sum(1 for k in set(got["kids"]) if recover_parent(k) != record)
            entry = {"run_dir": str(cell.run_dir), "cell": cell.name, "n": cell.n, "m": cell.m,
                     "index": i, "record": record, "d": got["d"], "processed": got["processed"],
                     "where": where, "block": [start, end], "recoveries": finder.recoveries - before,
                     **{k: res[k] for k in ("production", "enum2", "enum2_raw", "only_production",
                                            "only_enum2", "only_production_first", "only_enum2_first")},
                     "production_duplicates": res["production"] - res["production_distinct"],
                     "enum2_children_not_recovering_to_parent": wrong_parent,
                     "enum2_seconds": round(got["seconds"], 4)}
            if "canonical" in got:
                entry.update({"parent_canonical": got["canonical"],
                              "parent_contains_forbidden": got["parent_contains"],
                              "parent_check_seconds": round(got["parent_check_seconds"], 4)})
            entry["identical"] = (res["identical"] and wrong_parent == 0 and
                                  entry.get("parent_canonical", True) and
                                  entry.get("parent_contains_forbidden") is None)
            jsonl.write(json.dumps(entry) + "\n")
            jsonl.flush()
            results.append(entry)
    finally:
        for f in finders.values():
            f.lines.close()
    return results


def summarize(entries: list[dict], cells_info: list[dict], seeds: list[dict], args, t0: float,
              set_name: str) -> dict:
    by_cell: dict[tuple, dict] = {}
    for e in entries:
        c = by_cell.setdefault((e["run_dir"], e["cell"]), {
            "run_dir": e["run_dir"], "cell": e["cell"], "n": e["n"], "m": e["m"], "sampled": 0,
            "processed": 0, "production_children": 0, "enum2_children": 0, "mismatches": 0,
            "enum2_seconds": 0.0, "d_values": set()})
        c["sampled"] += 1
        c["processed"] += e["processed"]
        c["production_children"] += e["production"]
        c["enum2_children"] += e["enum2"]
        c["mismatches"] += not e["identical"]
        c["enum2_seconds"] += e["enum2_seconds"]
        c["d_values"].add(e["d"])
    info = {(ci["run_dir"], ci["cell"]): ci for ci in cells_info}
    rows = []
    for key, c in sorted(by_cell.items(), key=lambda kv: (kv[1]["n"], kv[1]["m"], kv[0][0])):
        c["d_values"] = sorted(c["d_values"])
        c["parents_in_cell"] = info.get(key, {}).get("parents")
        c["strata"] = info.get(key, {}).get("strata")
        c["stratum"] = info.get(key, {}).get("stratum")
        c["enum2_seconds"] = round(c["enum2_seconds"], 2)
        rows.append(c)
    levels: dict[int, dict] = {}
    for c in rows:
        lv = levels.setdefault(c["n"], {"n": c["n"], "cells": 0, "parents": 0, "sampled": 0, "processed": 0,
                                        "production_children": 0, "enum2_children": 0, "mismatches": 0,
                                        "enum2_seconds": 0.0})
        lv["cells"] += 1
        lv["parents"] += c["parents_in_cell"] or 0
        for k in ("sampled", "processed", "production_children", "enum2_children", "mismatches"):
            lv[k] += c[k]
        lv["enum2_seconds"] = round(lv["enum2_seconds"] + c["enum2_seconds"], 2)
    for lv in levels.values():
        lv["fraction_sampled"] = round(lv["sampled"] / lv["parents"], 6) if lv["parents"] else None
    secs = [e["enum2_seconds"] for e in entries]
    secs_p = [e["enum2_seconds"] for e in entries if e["processed"]]

    def dist(xs):
        if not xs:
            return None
        xs = sorted(xs)
        return {"count": len(xs), "mean": round(statistics.fmean(xs), 4), "median": round(xs[len(xs) // 2], 4),
                "p90": round(xs[int(0.9 * (len(xs) - 1))], 4), "max": round(xs[-1], 4), "total": round(sum(xs), 1)}

    unreplayable = [ci for ci in cells_info if not ci.get("replayable", True)]
    return {
        "tool": "enum2/replay-398.py", "tool_sha256": sha256_file(Path(__file__)),
        "enum2_sha256": sha256_file(HERE / "enum2.py"), "forbidden_set": set_name,
        "forbidden_sha256": enum2.FORBIDDEN_SPECS[set_name].sha256,
        "run_dirs": [str(p) for p in args.run_dir], "seed": args.seed, "fraction": args.fraction,
        "min_per_shard": args.min_per_shard, "whole_max": args.whole_max, "max_per_shard": args.max_per_shard,
        "levels": args.levels, "host": os.uname().nodename, "workers": args.workers,
        "sampled_parents": len(entries), "processed_parents": sum(e["processed"] for e in entries),
        "production_children_compared": sum(e["production"] for e in entries),
        "enum2_children_compared": sum(e["enum2"] for e in entries),
        "mismatching_parents": sum(not e["identical"] for e in entries),
        "unreplayable_cells": unreplayable,
        "seconds_per_sampled_parent": dist(secs), "seconds_per_processed_parent": dist(secs_p),
        "per_level": [levels[k] for k in sorted(levels)], "per_cell": rows, "seeds": seeds,
        "wall_seconds": round(time.monotonic() - t0, 1),
        "all_identical": (bool(entries) and all(e["identical"] for e in entries) and not unreplayable
                          and all(s.get("identical", False) for s in seeds)),
    }


# ------------------------------------------------------------------ red controls
def flip_first_edge(record: str) -> str:
    g = enum2.graph6_decode(record)
    adj = list(g.adj)
    adj[0] ^= 1 << 1
    adj[1] ^= 1 << 0
    return enum2.canonical_g6(enum2.Graph(tuple(adj)))


def _production_lines(e: dict, cell: Cell) -> tuple[LineFile, tuple[Path, int, int] | None]:
    """The file an entry's block coordinates refer to (the cell file, or a shard file)."""
    if e["where"] == "cell file":
        return LineFile(cell.run_dir / f"{cell.name}.g6"), None
    shard = cell.shard_for(e["index"])
    return LineFile(shard[0]), shard


def _reload(cell: Cell) -> bool:
    if cell.parents is None:
        cell.sources = []
        return cell.load_parents()
    return True


def _entry_block(e: dict, cell: Cell) -> list[str]:
    """A sampled parent's production block, at the coordinates the replay found."""
    _reload(cell)
    lines, _ = _production_lines(e, cell)
    try:
        return [lines[j] for j in range(*e["block"])]
    finally:
        lines.close()


def _cell_block(cell: Cell, i: int) -> list[str]:
    """Parent i's production block in the cell file (raises LookupError if it is not well formed)."""
    lines = LineFile(cell.run_dir / f"{cell.name}.g6")
    try:
        start, end = BlockFinder(lines, cell.parents, 0, len(cell.parents)).block(i)
        return [lines[j] for j in range(start, end)]
    finally:
        lines.close()


def _r3_candidates(entries: list[dict], cells: dict, seed: str, per_cell: int = 1000):
    """R3's parents, in order: the sampled ones (processed, identical to production) in replay order; then, since a
    small sample may hold no parent R3 can use, further parents of the same cells that were not sampled, per cell in
    the order random.Random("S/R3/<run dir name>/n-m") draws them (at most per_cell), their blocks found in the cell
    file. Yields (cell, index, record, block function, sampled)."""
    for e in entries:
        if e["processed"] and e["identical"]:
            cell = cells[(e["run_dir"], e["cell"])]
            yield cell, e["index"], e["record"], (lambda e=e, cell=cell: _entry_block(e, cell)), True
    seen = {(e["run_dir"], e["cell"], e["index"]) for e in entries}
    for key in dict.fromkeys((e["run_dir"], e["cell"]) for e in entries):
        cell = cells[key]
        if not _reload(cell) or cell.children_file() is None:
            continue
        rng = random.Random(f"{seed}/R3/{cell.run_dir.name}/{cell.name}")
        for i in rng.sample(range(len(cell.parents)), min(len(cell.parents), per_cell)):
            if (key[0], key[1], i) not in seen:
                yield cell, i, cell.parents[i], (lambda cell=cell, i=i: _cell_block(cell, i)), False


def red_controls(entries: list[dict], cells: dict, set_name: str, budget_parents: int,
                 seed: str = "") -> list[dict]:
    """Each control breaks one thing on this run's own data and must turn the comparison red.
    A control that cannot be run on the sample is recorded as NOT red (never skipped silently)."""
    required = ["R1", "R2", "R4", "R5a", "R5b"] + (["R3"] if set_name == "398" else [])
    reds: list[dict] = []
    nonempty = [e for e in entries if e["production"] > 0 and e["identical"]]
    chosen = None
    sizes: dict[tuple, tuple[int, int]] = {}      # (run_dir, cell, where) -> (lines, parent range top)
    for e in nonempty[:200]:
        key = (e["run_dir"], e["cell"], e["where"])
        if key not in sizes:
            cell = cells[(e["run_dir"], e["cell"])]
            if not _reload(cell):
                continue
            lines, shard = _production_lines(e, cell)
            sizes[key] = (len(lines), shard[2] if shard else len(cell.parents))
            lines.close()
        total_lines, top = sizes[key]
        has_outside = e["block"][1] < total_lines or e["block"][0] > 0
        if has_outside and e["index"] + 1 < top:
            chosen = e
            break
    if chosen is None and nonempty:
        chosen = nonempty[0]
    if chosen is not None:
        e = chosen
        cell = cells[(e["run_dir"], e["cell"])]
        _reload(cell)
        lines, shard = _production_lines(e, cell)
        block = [lines[j] for j in range(*e["block"])]
        kids0 = list(enum2.extend_parent(enum2.graph6_decode(e["record"]), cell.m, forbidden(set_name)))
        base = compare(block, kids0)
        where = {"cell": e["cell"], "index": e["index"], "block_size": len(block), "baseline_identical":
                 base["identical"]}
        # R1 mutated parent
        mutated = flip_first_edge(e["record"])
        kids = list(enum2.extend_parent(enum2.graph6_decode(mutated), cell.m, forbidden(set_name)))
        r1 = compare(block, kids)
        reds.append({"id": "R1", "control": "mutated parent (edge 0-1 flipped, re-canonicalised) against the "
                     "original production block", **where, "mutated": mutated, "only_production":
                     r1["only_production"], "only_enum2": r1["only_enum2"],
                     "went_red": base["identical"] and not r1["identical"]})
        # R2 dropped production record
        r2 = compare(block[:-1], kids0)
        reds.append({"id": "R2", "control": "one record dropped from the production block", **where,
                     "only_enum2": r2["only_enum2"], "went_red": base["identical"] and not r2["identical"]})
        # R4 wrong block: parent i's children against parent i+1's block
        i = e["index"]
        lo, hi = (shard[1], shard[2]) if shard else (0, len(cell.parents))
        if i + 1 < hi:
            finder = BlockFinder(lines, cell.parents, lo, hi)
            s2, t2 = finder.block(i + 1)
            r4 = compare([lines[j] for j in range(s2, t2)], kids0)
            reds.append({"id": "R4", "control": "enum2's children of parent i against the block of parent i+1",
                         **where, "next_block_size": t2 - s2, "went_red": base["identical"] and not r4["identical"]})
        # R5 the wrong checks
        outside = None
        for j in (e["block"][1], e["block"][0] - 1):
            if 0 <= j < len(lines):
                outside = lines[j]
                break
        if outside is not None:
            r5a = compare(block[:-1] + [outside], kids0)
            reds.append({"id": "R5a", "control": "one production record replaced by a neighbouring child "
                         "(another parent's)", **where,
                         "wrong_equal_count_check": "PASS" if r5a["equal_counts"] else "FAIL",
                         "set_check": "PASS" if r5a["identical"] else "FAIL",
                         "went_red": base["identical"] and r5a["equal_counts"] and not r5a["identical"]})
        r5b = compare(block, sorted(set(kids0))[1:])
        reds.append({"id": "R5b", "control": "enum2's children minus one record", **where,
                     "wrong_subset_check": "PASS" if r5b["enum2_subset_of_production"] else "FAIL",
                     "set_check": "PASS" if r5b["identical"] else "FAIL",
                     "went_red": base["identical"] and r5b["enum2_subset_of_production"] and not r5b["identical"]})
        lines.close()
    # R3 one member of the 324 dropped (Mode 398 only), judged against the production block: on the first parent
    # (_r3_candidates: the sample first) with a child that one member of the 324 alone rejects, re-checked identical
    # to its production block first; at most budget_parents processed parents are tried
    if set_name == "398":
        fs = forbidden("398")
        fs74 = forbidden("74")
        tried = 0
        for c3, i3, record3, block_of, sampled in _r3_candidates(entries, cells, seed):
            if tried >= budget_parents:
                break
            g = enum2.graph6_decode(record3)
            stats: dict = {}
            full = set(enum2.extend_parent(g, c3.m, fs, stats=stats))
            if not stats.get("parents_processed"):
                continue
            tried += 1
            hit = None
            for x in sorted(set(enum2.extend_parent(g, c3.m, fs74)) - full):
                members = fs.tester.all(enum2.graph6_decode(x))
                if len(members) == 1 and members[0] >= 74:
                    hit = (x, members[0])
                    break
            if hit is None:
                continue
            x, member = hit
            where3 = {"cell": c3.name, "index": i3, "from_sample": sampled, "parents_tried": tried}
            try:
                block3 = block_of()
            except LookupError as err:
                reds.append({"id": "R3", "control": "a parent R3 tried has no well-formed production block (a "
                             "discrepancy, not a red control)", **where3, "problem": str(err), "went_red": False})
                break
            base3 = compare(block3, sorted(full))
            if not base3["identical"]:
                reds.append({"id": "R3", "control": "a parent R3 tried has enum2 children that differ from its "
                             "production block (a discrepancy, not a red control)", **where3,
                             **{k: base3[k] for k in ("production", "enum2", "only_production", "only_enum2",
                                                     "only_production_first", "only_enum2_first")},
                             "went_red": False})
                break
            without = list(enum2.extend_parent(g, c3.m, forbidden("398", (member,))))
            r3 = compare(block3, without)
            extra = sorted(set(without) - set(block3))
            exact = all(fs.tester.all(enum2.graph6_decode(y)) == [member] for y in extra)
            reds.append({"id": "R3", "control": f"enum2 without member {member} (one of the 324) "
                         "against the production block", **where3, "baseline_identical": True,
                         "production_children": len(block3), "enum2_children_without_member":
                         r3["enum2"], "extra": len(extra), "missing": r3["only_production"],
                         "extras_contain_exactly_that_member": exact,
                         "went_red": (not r3["identical"]) and x in extra and exact})
            break
    for rid in required:
        if not any(r["id"] == rid for r in reds):
            reds.append({"id": rid, "control": "not exercisable on this sample", "went_red": False})
    return reds


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", type=Path, action="append", required=True)
    ap.add_argument("--fraction", type=float, required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--forbidden-set", default="auto", choices=("auto", "74", "398"))
    ap.add_argument("--min-per-shard", type=int, default=1)
    ap.add_argument("--whole-max", type=int, default=0, help="cells with at most this many parents: all")
    ap.add_argument("--max-per-shard", type=int, default=None)
    ap.add_argument("--levels", default="", help="n range of the cells to replay, e.g. 11-23")
    ap.add_argument("--cells", default="", help="only these cells, e.g. 14-33,15-37")
    ap.add_argument("--seeds", default="sample", choices=("off", "sample", "full"))
    ap.add_argument("--no-parent-check", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--red", action="store_true")
    ap.add_argument("--red-budget", type=int, default=200,
                    help="processed parents R3 may try (the sampled ones first, then further parents of the cells)")
    ap.add_argument("--plan-only", action="store_true",
                    help="print the cells and sample sizes (from the manifests alone) and stop")
    ap.add_argument("--stages", default="check", choices=("off", "check"),
                    help="re-derive every reach and slice file used as a parent source (keep files: "
                         "subsequence check) of the replayed cells")
    args = ap.parse_args()
    args.run_dir = [p.resolve() for p in args.run_dir]
    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    cells = discover(args.run_dir)
    if not cells:
        print("no cell manifests found", file=sys.stderr)
        return 2
    named = {forbidden_sets_named(c.manifest) for c in cells}
    if args.forbidden_set != "auto":
        # every manifest must list the requested set's file (a manifest listing both is accepted)
        if any(args.forbidden_set not in names for names in named):
            print(f"some manifests do not list forbidden set {args.forbidden_set}: {sorted(named)}",
                  file=sys.stderr)
            return 2
        set_name = args.forbidden_set
    else:
        if len(named) != 1 or len(next(iter(named))) != 1:
            print(f"the manifests do not name exactly one pinned forbidden set: {sorted(named)}; "
                  f"give --forbidden-set", file=sys.stderr)
            return 2
        set_name = next(iter(named))[0]
    levels = parse_levels(args.levels)
    wanted = set(x for x in args.cells.split(",") if x)
    if args.plan_only:
        plan = []
        for cell in cells:
            if (levels and not (levels[0] <= cell.n <= levels[1])) or (wanted and cell.name not in wanted):
                continue
            if cell.is_seed:
                plan.append({"run_dir": cell.run_dir.name, "cell": cell.name, "seed_level": True,
                             "records": cell.manifest.get("children_written")})
                continue
            total = int(cell.manifest["parent_range"][1])
            ranges, unit = strata(cell, total)
            k = len(sample_indices(args.seed, cell.run_dir.name, cell.name, total, args.fraction,
                                   args.min_per_shard, args.whole_max, args.max_per_shard, ranges))
            plan.append({"run_dir": cell.run_dir.name, "cell": cell.name, "parents": total, "sampled": k,
                         "strata": len(ranges), "stratum": unit,
                         "d_values": sorted({int(s["d"]) for s in cell.manifest.get("parent_sources", [])})})
        (args.out / "plan.json").write_text(json.dumps({"forbidden_set": set_name, "plan": plan}, indent=1) + "\n")
        for row in plan:
            print(json.dumps(row))
        print(f"cells {sum(1 for r in plan if 'parents' in r)}, parents "
              f"{sum(r.get('parents', 0) for r in plan)}, sampled {sum(r.get('sampled', 0) for r in plan)}")
        return 0
    header = {"seed": args.seed, "fraction": args.fraction, "min_per_shard": args.min_per_shard,
              "whole_max": args.whole_max, "max_per_shard": args.max_per_shard, "forbidden_set": set_name,
              "run_dirs": [str(p) for p in args.run_dir]}
    jsonl_path = args.out / "replay.jsonl"
    done: set = set()
    entries: list[dict] = []
    if args.resume and jsonl_path.exists():
        lines = jsonl_path.read_text().splitlines()
        if not lines or json.loads(lines[0]).get("header") != header:
            print("--resume: replay.jsonl was written with different options", file=sys.stderr)
            return 2
        for ln in lines[1:]:
            e = json.loads(ln)
            entries.append(e)
            done.add((e["run_dir"], e["cell"], e["index"]))
        jsonl = jsonl_path.open("a")
    else:
        jsonl = jsonl_path.open("w")
        jsonl.write(json.dumps({"header": header}) + "\n")
    pool = None
    if args.workers > 1:
        import multiprocessing
        pool = multiprocessing.Pool(args.workers)
    cells_info: list[dict] = []
    seeds: list[dict] = []
    stages: list[dict] = []
    stage_cache: dict = {}
    seen_content: dict[tuple, str] = {}
    by_key: dict[tuple, Cell] = {}
    g9 = None
    try:
        for cell in cells:
            if levels and not (levels[0] <= cell.n <= levels[1]):
                continue
            if wanted and cell.name not in wanted:
                continue
            if cell.is_seed:
                if args.seeds != "off" and cell.n >= 1 and cell.manifest.get("children_written", 0) > 0:
                    if args.seeds == "full" and cell.n == 10 and g9 is None:
                        g9 = g9_free(set_name)
                    seeds.append(check_seed(cell, set_name, args.seeds, args.seed, args.fraction,
                                            args.min_per_shard, g9))
                    print(f"seed {cell.run_dir.name}/{cell.name}: {json.dumps(seeds[-1])[:300]}", flush=True)
                continue
            info = {"run_dir": str(cell.run_dir), "cell": cell.name}
            content = (cell.name, cell.manifest.get("children_file_sha256"),
                       cell.manifest.get("inputs_sha256", {}).get(cell.manifest.get("parent_file")))
            if content in seen_content:
                info.update({"replayable": True, "same_content_as": seen_content[content]})
                cells_info.append(info)
                continue
            seen_content[content] = str(cell.run_dir)
            if not cell.load_parents():
                info.update({"replayable": False, "problems": cell.problems})
                cells_info.append(info)
                print(f"cell {cell.run_dir.name}/{cell.name}: NOT REPLAYABLE {cell.problems}", flush=True)
                continue
            info["parents"] = len(cell.parents)
            if args.stages == "check":
                for src in cell.manifest.get("parent_sources", []):
                    key = (src["file"], src.get("sha256"))
                    if key not in stage_cache:
                        st = check_stage(cell, src, stage_cache)
                        stages.append({"for_cell": cell.name, "run_dir": cell.run_dir.name, **st})
                        if not st["ok"]:
                            print(f"stage {st['source']}: {st['status']}", flush=True)
            ranges, unit = strata(cell, len(cell.parents))
            idx = sample_indices(args.seed, cell.run_dir.name, cell.name, len(cell.parents), args.fraction,
                                 args.min_per_shard, args.whole_max, args.max_per_shard, ranges)
            info.update({"sampled": len(idx), "strata": len(ranges), "stratum": unit})
            try:
                got = replay_cell(cell, idx, set_name, args, jsonl, done, pool)
            except LookupError as err:
                info.update({"replayable": False, "problems": cell.problems + [str(err)]})
                cells_info.append(info)
                print(f"cell {cell.run_dir.name}/{cell.name}: NOT REPLAYABLE {err}", flush=True)
                continue
            info["replayable"] = True
            cells_info.append(info)
            entries.extend(got)
            by_key[(str(cell.run_dir), cell.name)] = cell
            bad = sum(not e["identical"] for e in got)
            print(f"cell {cell.run_dir.name}/{cell.name}: parents {len(cell.parents)} sampled {len(idx)} "
                  f"(new {len(got)}) processed {sum(e['processed'] for e in got)} "
                  f"production {sum(e['production'] for e in got)} enum2 {sum(e['enum2'] for e in got)} "
                  f"mismatching {bad} enum2 {sum(e['enum2_seconds'] for e in got):.1f}s", flush=True)
            cell.parents = None     # free the memory (red controls reload what they use)
    finally:
        jsonl.close()
        if pool:
            pool.terminate()
    summary = summarize(entries, cells_info, seeds, args, t0, set_name)
    summary["stages"] = stages
    summary["stages_checked"] = len(stages)
    summary["stages_ok"] = all(s["ok"] for s in stages)
    summary["all_identical"] = summary["all_identical"] and summary["stages_ok"]
    reds = []
    if args.red:
        reds = red_controls([e for e in entries if (e["run_dir"], e["cell"]) in by_key], by_key, set_name,
                            args.red_budget, args.seed)
        (args.out / "red.json").write_text(json.dumps(reds, indent=1) + "\n")
        for r in reds:
            print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {json.dumps(r)[:400]}",
                  flush=True)
        summary["red_controls"] = reds
        summary["red_all"] = bool(reds) and all(r["went_red"] for r in reds)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    ok = summary["all_identical"] and (not args.red or summary["red_all"])
    print(f"sampled {summary['sampled_parents']} parents ({summary['processed_parents']} processed), "
          f"{summary['production_children_compared']} production children compared, "
          f"{summary['mismatching_parents']} mismatching, {len(summary['unreplayable_cells'])} unreplayable cells; "
          f"RESULT: {'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
