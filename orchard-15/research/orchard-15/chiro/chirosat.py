#!/usr/bin/env python3
"""Decide rank-3 chirotope feasibility for a partial Steiner triple system.

The input format is the orchard contract PTS format::

    v b : a b c , d e f , ... ;

For every increasing triple I, the two Boolean variables ``pos(I)`` and
``neg(I)`` represent chi(I)=+1 and chi(I)=-1.  Neither variable means zero.
The clauses prescribe zero exactly on the listed blocks and require exactly
one sign everywhere else.  For an arbitrary ordered triple, chi is obtained
from the increasing representative using the parity of the sorting
permutation.  This is chirotope axiom (B1), alternation.

The remaining clauses encode the rank-3 three-term Grassmann-Pluecker form
of axiom (B2).  For distinct a,b,c,d,e, with a the pivot, the signs

    chi(a,b,c) chi(a,d,e),
   -chi(a,b,d) chi(a,c,e),
    chi(a,b,e) chi(a,c,d)

must either include both signs or all be zero.  We impose this for every
5-subset and each of its five pivots.  This is the standard local form of
(B2), with a common (r-2)-tuple.  A PTS has blocks intersecting in at most
one element, so declaring precisely those triples to be nonbases gives a
simple rank-3 sparse paving matroid.  On this fixed matroid support, the
three-term axiom is equivalent to the chirotope exchange axiom.  Relations
with repeated elements are tautologies, so the distinct five-element cases
suffice.  Together with (B0), imposed by requiring at least one nonzero
triple, these are axioms (B0)-(B2) of Björner, Las Vergnas, Sturmfels, White
and Ziegler, Oriented Matroids, second edition, Section 3.5, including its
three-term Grassmann-Pluecker formulation.

The first nonzero increasing triple is fixed positive.  This is sound because
global sign reversal chi -> -chi preserves zeros and every product in (B2).

UNSAT results are accepted only after an external CaDiCaL DRAT proof has
been checked by the independent drat-trim program.  SAT results are checked
again by direct evaluation of the prescribed zeros and all GP relations.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Sequence


Triple = tuple[int, int, int]
Clause = list[int]


class InputError(ValueError):
    """A malformed or non-PTS input line."""


@dataclass(frozen=True)
class PTS:
    v: int
    blocks: tuple[Triple, ...]

    @property
    def line(self) -> str:
        body = " , ".join(" ".join(map(str, block)) for block in self.blocks)
        return f"{self.v} {len(self.blocks)} : {body} ;"


@dataclass
class Encoding:
    pts: PTS
    triples: tuple[Triple, ...]
    index: dict[Triple, int]
    clauses: list[Clause]
    gp_relations: int
    gp_active_histogram: tuple[int, int, int, int]

    @property
    def nvars(self) -> int:
        return 2 * len(self.triples)

    def var(self, triple: Triple, sign: int) -> int:
        base = 2 * self.index[triple]
        return base + (1 if sign == 1 else 2)


@dataclass
class BatchEncoding:
    """The v-dependent clauses shared by every batch instance."""

    v: int
    triples: tuple[Triple, ...]
    index: dict[Triple, int]
    clauses: list[Clause]
    gp_relations: int
    auxiliary_variables: int = 0
    nonzero_variables: dict[Triple, int] = field(default_factory=dict)

    @property
    def nvars(self) -> int:
        return 2 * len(self.triples) + self.auxiliary_variables

    def var(self, triple: Triple, sign: int) -> int:
        base = 2 * self.index[triple]
        return base + (1 if sign == 1 else 2)

    def new_auxiliary(self) -> int:
        self.auxiliary_variables += 1
        return 2 * len(self.triples) + self.auxiliary_variables


HEADER_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s*:\s*(.*?)\s*;\s*$")


def parse_pts_line(line: str) -> PTS:
    """Parse and strictly validate one contract-format PTS line."""
    match = HEADER_RE.match(line)
    if not match:
        raise InputError("expected 'v b : triples ;'")
    v, declared_b = int(match.group(1)), int(match.group(2))
    if v < 3:
        raise InputError("v must be at least 3")
    body = match.group(3).strip()
    fields = [] if not body else [part.strip() for part in body.split(",")]
    if any(not field for field in fields):
        raise InputError("empty triple field")
    blocks: list[Triple] = []
    used_pairs: set[tuple[int, int]] = set()
    for field in fields:
        pieces = field.split()
        if len(pieces) != 3:
            raise InputError(f"triple must contain three integers: {field!r}")
        try:
            block = tuple(map(int, pieces))
        except ValueError as exc:
            raise InputError(f"non-integer triple: {field!r}") from exc
        if not (0 <= block[0] < block[1] < block[2] < v):
            raise InputError(f"triple is not strictly sorted or in range: {block}")
        for pair in itertools.combinations(block, 2):
            if pair in used_pairs:
                raise InputError(f"pair {pair} occurs in more than one block")
            used_pairs.add(pair)
        blocks.append(block)  # type: ignore[arg-type]
    if declared_b != len(blocks):
        raise InputError(f"declared b={declared_b}, parsed {len(blocks)} blocks")
    if blocks != sorted(set(blocks)):
        raise InputError("blocks must be unique and lexicographically sorted")
    if len(blocks) == math.comb(v, 3):
        raise InputError("(B0) fails: every triple is prescribed zero")
    return PTS(v=v, blocks=tuple(blocks))


def ordered_base(items: Sequence[int]) -> tuple[Triple, int]:
    """Return increasing representative and permutation sign of three items."""
    if len(set(items)) != 3:
        raise ValueError("ordered_base requires three distinct elements")
    inversions = sum(items[i] > items[j] for i in range(3) for j in range(i + 1, 3))
    return tuple(sorted(items)), (-1 if inversions % 2 else 1)  # type: ignore[return-value]


def product_assignments(
    encoding: Encoding,
    left: tuple[Triple, int],
    right: tuple[Triple, int],
    coefficient: int,
    desired: int,
) -> list[tuple[int, int]]:
    """Assignments of the two stored signs that give a desired product sign."""
    left_triple, left_orientation = left
    right_triple, right_orientation = right
    needed = desired * coefficient * left_orientation * right_orientation
    result = []
    for left_sign in (1, -1):
        right_sign = needed * left_sign
        result.append(
            (
                encoding.var(left_triple, left_sign),
                encoding.var(right_triple, right_sign),
            )
        )
    return result


def build_encoding(pts: PTS, drop_gp_family: str | None = None) -> Encoding:
    """Build CNF.  ``drop_gp_family`` exists only for the mutation control."""
    if drop_gp_family not in (None, "positive", "negative"):
        raise ValueError("drop_gp_family must be positive, negative, or None")
    triples = tuple(itertools.combinations(range(pts.v), 3))
    index = {triple: i for i, triple in enumerate(triples)}
    encoding = Encoding(pts, triples, index, [], 0, (0, 0, 0, 0))
    blocks = set(pts.blocks)

    for triple in triples:
        positive, negative = encoding.var(triple, 1), encoding.var(triple, -1)
        encoding.clauses.append([-positive, -negative])
        if triple in blocks:
            encoding.clauses.extend(([-positive], [-negative]))
        else:
            encoding.clauses.append([positive, negative])

    first_basis = next(triple for triple in triples if triple not in blocks)
    encoding.clauses.append([encoding.var(first_basis, 1)])

    histogram = [0, 0, 0, 0]
    relation_count = 0
    for five in itertools.combinations(range(pts.v), 5):
        for pivot in five:
            b, c, d, e = (x for x in five if x != pivot)
            terms = (
                (ordered_base((pivot, b, c)), ordered_base((pivot, d, e)), 1),
                (ordered_base((pivot, b, d)), ordered_base((pivot, c, e)), -1),
                (ordered_base((pivot, b, e)), ordered_base((pivot, c, d)), 1),
            )
            active = [term for term in terms if term[0][0] not in blocks and term[1][0] not in blocks]
            histogram[len(active)] += 1
            relation_count += 1
            if len(active) == 0:
                continue
            if len(active) == 1:
                encoding.clauses.append([])
                continue
            for desired, family in ((1, "positive"), (-1, "negative")):
                if drop_gp_family == family:
                    continue
                choices = [
                    product_assignments(encoding, left, right, coefficient, desired)
                    for left, right, coefficient in active
                ]
                for assignment in itertools.product(*choices):
                    # This assignment makes all nonzero GP products have the
                    # same sign.  Its negation is the required CNF clause.
                    encoding.clauses.append([-literal for pair in assignment for literal in pair])

    encoding.gp_relations = relation_count
    encoding.gp_active_histogram = tuple(histogram)  # type: ignore[assignment]
    return encoding


def build_base_encoding(v: int) -> BatchEncoding:
    """Build all clauses that depend only on v, with no prescribed zeros.

    The base contains exactly-one-or-zero support clauses and both sign families
    of every three-term Grassmann-Pluecker relation.  A PTS is supplied later
    through assumptions, so this function is intentionally independent of any
    particular block list.
    """
    if v < 3:
        raise InputError("v must be at least 3")
    triples = tuple(itertools.combinations(range(v), 3))
    index = {triple: i for i, triple in enumerate(triples)}
    base = BatchEncoding(v, triples, index, [], 0)

    for triple in triples:
        positive, negative = base.var(triple, 1), base.var(triple, -1)
        nonzero = base.new_auxiliary()
        base.nonzero_variables[triple] = nonzero
        base.clauses.extend(
            (
                [-positive, -negative],
                [-positive, nonzero],
                [-negative, nonzero],
                [-nonzero, positive, negative],
            )
        )

    relation_count = 0
    for five in itertools.combinations(range(v), 5):
        for pivot in five:
            b, c, d, e = (x for x in five if x != pivot)
            terms = (
                (ordered_base((pivot, b, c)), ordered_base((pivot, d, e)), 1),
                (ordered_base((pivot, b, d)), ordered_base((pivot, c, e)), -1),
                (ordered_base((pivot, b, e)), ordered_base((pivot, c, d)), 1),
            )
            relation_count += 1
            product_signs: list[tuple[int, int]] = []
            for left, right, coefficient in terms:
                positive = base.new_auxiliary()
                negative = base.new_auxiliary()
                product_signs.append((positive, negative))
                for desired, predicate in ((1, positive), (-1, negative)):
                    alternatives = product_assignments(
                        base, left, right, coefficient, desired
                    )
                    for first, second in alternatives:
                        base.clauses.append([-first, -second, predicate])
                    for first in alternatives[0]:
                        for second in alternatives[1]:
                            base.clauses.append([-predicate, first, second])
            for product_index, (positive, negative) in enumerate(product_signs):
                base.clauses.append(
                    [-positive]
                    + [product_signs[index][1] for index in range(3)]
                )
                base.clauses.append(
                    [-negative]
                    + [product_signs[index][0] for index in range(3)]
                )
    base.gp_relations = relation_count
    return base


def batch_assumptions(base: BatchEncoding, pts: PTS) -> list[int]:
    """Return the instance support and sign-symmetry assumptions."""
    if pts.v != base.v:
        raise InputError(f"batch contains v={pts.v}, expected v={base.v}")
    blocks = set(pts.blocks)
    assumptions: list[int] = []
    for triple in base.triples:
        nonzero = base.nonzero_variables[triple]
        if triple in blocks:
            assumptions.append(-nonzero)
        else:
            assumptions.append(nonzero)
    first_basis = next(triple for triple in base.triples if triple not in blocks)
    assumptions.append(base.var(first_basis, 1))
    return assumptions


def write_dimacs(encoding: Encoding, path: Path) -> None:
    write_clauses(encoding.nvars, encoding.clauses, path)


def write_clauses(nvars: int, clauses: Sequence[Clause], path: Path) -> None:
    with path.open("w", encoding="ascii") as handle:
        handle.write(f"p cnf {nvars} {len(clauses)}\n")
        for clause in clauses:
            handle.write(" ".join(map(str, clause)))
            handle.write(" 0\n")


def parse_solver_model(path: Path, nvars: int) -> set[int]:
    values: set[int] = set()
    status = None
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("s "):
            status = line[2:].strip()
        elif line.startswith("v "):
            values.update(int(item) for item in line[2:].split() if item != "0")
    if status != "SATISFIABLE":
        raise RuntimeError(f"solver model file has unexpected status {status!r}")
    assignment = {abs(value): value > 0 for value in values}
    missing = [var for var in range(1, nvars + 1) if var not in assignment]
    if missing:
        raise RuntimeError(f"solver model omits {len(missing)} variables")
    return {var for var, truth in assignment.items() if truth}


def witness_from_model(encoding: Encoding, true_vars: set[int]) -> str:
    chars = []
    for triple in encoding.triples:
        positive = encoding.var(triple, 1) in true_vars
        negative = encoding.var(triple, -1) in true_vars
        if positive and not negative:
            chars.append("+")
        elif negative and not positive:
            chars.append("-")
        elif not positive and not negative:
            chars.append("0")
        else:
            raise RuntimeError(f"model gives both signs to triple {triple}")
    return "".join(chars)


def chi_value(witness: str, encoding: Encoding, ordered: Sequence[int]) -> int:
    triple, orientation = ordered_base(ordered)
    value = {"+": 1, "-": -1, "0": 0}[witness[encoding.index[triple]]]
    return orientation * value


def verify_witness(encoding: Encoding, witness: str) -> None:
    """Independent direct check of (B0)-(B2) and the exact zero set."""
    if len(witness) != len(encoding.triples) or set(witness) - set("+-0"):
        raise RuntimeError("malformed chirotope witness")
    zeros = {triple for triple, value in zip(encoding.triples, witness) if value == "0"}
    if zeros != set(encoding.pts.blocks):
        raise RuntimeError("witness zero set differs from the prescribed blocks")
    if not set(witness) & set("+-"):
        raise RuntimeError("witness violates (B0)")
    for five in itertools.combinations(range(encoding.pts.v), 5):
        for pivot in five:
            b, c, d, e = (x for x in five if x != pivot)
            products = (
                chi_value(witness, encoding, (pivot, b, c))
                * chi_value(witness, encoding, (pivot, d, e)),
                -chi_value(witness, encoding, (pivot, b, d))
                * chi_value(witness, encoding, (pivot, c, e)),
                chi_value(witness, encoding, (pivot, b, e))
                * chi_value(witness, encoding, (pivot, c, d)),
            )
            signs = set(products)
            if signs != {0} and not ({-1, 1} <= signs):
                raise RuntimeError(f"witness violates GP at {five}, pivot {pivot}: {products}")


def find_executable(explicit: str | None, candidates: Iterable[str]) -> str:
    if explicit:
        found = shutil.which(explicit) if os.sep not in explicit else explicit
        if found and os.access(found, os.X_OK):
            return found
        raise RuntimeError(f"executable not found: {explicit}")
    for candidate in candidates:
        expanded = os.path.expanduser(candidate)
        found = shutil.which(expanded) if os.sep not in expanded else expanded
        if found and os.access(found, os.X_OK):
            return found
    raise RuntimeError(f"none of these executables was found: {', '.join(candidates)}")


DRAT_TRIM_TIME_LIMIT = 10_000_000  # seconds; drat-trim's compiled default is 20000 and it then prints "s TIMEOUT" with exit 0


def run_drat_trim(checker: str, cnf: Path, proof: Path,
                  time_limit: int = DRAT_TRIM_TIME_LIMIT) -> tuple[float, str]:
    """Run drat-trim and accept only an exact "s VERIFIED" line with exit 0.

    A substring test on "VERIFIED" would also accept "s NOT VERIFIED" from a checker build that
    exits 0 (the real binary exits 1 there, but the acceptance must not depend on that), and
    "s TIMEOUT" exits 0 with no VERIFIED line at all, so both are rejected explicitly. The full
    checker output is kept next to the proof as <proof>.drat-trim.log.
    """
    started = time.perf_counter()
    process = subprocess.run(
        [checker, str(cnf), str(proof), "-t", str(int(time_limit))],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter() - started
    lines = process.stdout.strip().splitlines()
    tail = "\n".join(lines[-8:])
    try:
        Path(str(proof) + ".drat-trim.log").write_text(
            process.stdout + f"\n[exit {process.returncode}, {elapsed:.3f} s]\n")
    except OSError:
        pass
    verified = any(line.strip() == "s VERIFIED" for line in lines)
    rejected = any(line.strip() in ("s NOT VERIFIED", "s TIMEOUT") for line in lines)
    if process.returncode != 0 or not verified or rejected:
        raise RuntimeError(
            f"drat-trim rejected proof (exit {process.returncode}):\n{tail}"
        )
    return elapsed, tail


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def solve_one(
    pts: PTS,
    artifact_dir: Path,
    solver: str,
    checker: str,
    drop_gp_family: str | None = None,
) -> dict[str, object]:
    total_started = time.perf_counter()
    encode_started = time.perf_counter()
    encoding = build_encoding(pts, drop_gp_family=drop_gp_family)
    encode_seconds = time.perf_counter() - encode_started
    digest = hashlib.sha256(pts.line.encode("ascii")).hexdigest()[:16]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cnf = artifact_dir / f"{pts.v}-{len(pts.blocks)}-{digest}.cnf"
    proof = artifact_dir / f"{pts.v}-{len(pts.blocks)}-{digest}.drat"
    model = artifact_dir / f"{pts.v}-{len(pts.blocks)}-{digest}.model"
    write_started = time.perf_counter()
    write_dimacs(encoding, cnf)
    write_seconds = time.perf_counter() - write_started

    command = [solver, "--binary=false", "-q", "-w", str(model), str(cnf), str(proof)]
    started = time.perf_counter()
    process = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    solve_seconds = time.perf_counter() - started
    common: dict[str, object] = {
        "pts": pts.line,
        "variables": encoding.nvars,
        "clauses": len(encoding.clauses),
        "gp_relations": encoding.gp_relations,
        "gp_active_histogram": list(encoding.gp_active_histogram),
        "encode_seconds": round(encode_seconds, 6),
        "write_seconds": round(write_seconds, 6),
        "solve_seconds": round(solve_seconds, 6),
    }
    if process.returncode == 10:
        true_vars = parse_solver_model(model, encoding.nvars)
        witness = witness_from_model(encoding, true_vars)
        if drop_gp_family is None:
            verify_witness(encoding, witness)
        return common | {
            "verdict": "pseudoline",
            "witness": witness,
            "total_seconds": round(time.perf_counter() - total_started, 6),
        }
    if process.returncode == 20:
        check_seconds, checker_tail = run_drat_trim(checker, cnf, proof)
        return common | {
            "verdict": "no-pseudoline",
            "witness": str(proof.resolve()),
            "cnf": str(cnf.resolve()),
            "proof_sha256": file_sha256(proof),
            "cnf_sha256": file_sha256(cnf),
            "proof_verified": True,
            "check_seconds": round(check_seconds, 6),
            "checker_tail": checker_tail,
            "total_seconds": round(time.perf_counter() - total_started, 6),
        }
    tail = "\n".join(process.stdout.strip().splitlines()[-12:])
    raise RuntimeError(f"solver failed with exit {process.returncode}:\n{tail}")


def iter_input_lines(path: str) -> Iterator[str]:
    decompressor: subprocess.Popen[str] | None = None
    if path == "-":
        handle = sys.stdin
    elif path.endswith(".zst"):
        decompressor = subprocess.Popen(
            ["zstd", "-q", "-dc", path],
            text=True,
            stdout=subprocess.PIPE,
        )
        if decompressor.stdout is None:
            raise RuntimeError("failed to open zstd output pipe")
        handle = decompressor.stdout
    else:
        handle = open(path, encoding="ascii")
    try:
        for line in handle:
            if line.strip() and not line.lstrip().startswith("#"):
                yield line.rstrip("\n")
    finally:
        if handle is not sys.stdin:
            handle.close()
        if decompressor is not None:
            returncode = decompressor.wait()
            if returncode != 0:
                raise RuntimeError(f"zstd failed with exit {returncode}: {path}")


def validate_batch_done(path: str) -> tuple[int, str]:
    """Require and validate the completion marker mandated by the contract."""
    source = Path(path)
    marker = Path(f"{path}.DONE")
    if not marker.is_file():
        raise InputError(f"batch input is missing completion marker: {marker}")
    fields: dict[str, str] = {}
    for line in marker.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            raise InputError(f"malformed completion marker line: {line!r}")
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    try:
        count = int(fields["count"])
        expected_hash = fields["sha256"]
    except (KeyError, ValueError) as exc:
        raise InputError("completion marker needs count and sha256") from exc
    if count < 1 or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise InputError("completion marker has invalid count or sha256")
    actual_hash = file_sha256(source)
    if actual_hash != expected_hash:
        raise InputError(
            f"completion marker sha256 mismatch: expected {expected_hash}, got {actual_hash}"
        )
    actual_count = sum(1 for _ in iter_input_lines(path))
    if actual_count != count:
        raise InputError(
            f"completion marker count mismatch: expected {count}, got {actual_count}"
        )
    return count, actual_hash


def run_kissat(kissat: str, nvars: int, clauses: Sequence[Clause], directory: Path) -> dict[str, object]:
    """Cross-check one UNSAT instance using a temporary exact CNF."""
    directory.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", dir=directory, prefix="kissat-", suffix=".cnf", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(f"p cnf {nvars} {len(clauses)}\n")
            for clause in clauses:
                handle.write(" ".join(map(str, clause)))
                handle.write(" 0\n")
        started = time.perf_counter()
        process = subprocess.run(
            [kissat, str(temporary)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = time.perf_counter() - started
        output = process.stdout or ""
        if process.returncode == 20 or "s UNSATISFIABLE" in output:
            verdict = "no-pseudoline"
        elif process.returncode == 10 or "s SATISFIABLE" in output:
            verdict = "pseudoline"
        else:
            tail = "\n".join(output.strip().splitlines()[-12:])
            raise RuntimeError(f"kissat failed with exit {process.returncode}:\n{tail}")
        return {
            "solver": "kissat",
            "verdict": verdict,
            "agreement": verdict == "no-pseudoline",
            "seconds": round(elapsed, 6),
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def solve_batch(
    instances: Sequence[PTS],
    artifact_dir: Path,
    batch_solver_name: str = "Cadical153",
    standalone_solver: str | None = None,
    checker: str | None = None,
    kissat: str | None = None,
    proof_sample_rate: float = 0.01,
    seed: int = 0,
    reset_every: int | None = None,
) -> list[dict[str, object]]:
    """Solve homogeneous instances with one cached base and a persistent solver."""
    if not instances:
        raise InputError("batch contains no PTS lines")
    if not 0.0 <= proof_sample_rate <= 1.0:
        raise InputError("proof sample rate must be between 0 and 1")
    v = instances[0].v
    if any(instance.v != v for instance in instances):
        raise InputError("all lines in one batch must have the same v")
    if reset_every is not None and reset_every < 1:
        raise InputError("reset-every must be positive")
    try:
        from pysat.solvers import Cadical153, Cadical195
    except ImportError as exc:
        raise RuntimeError("python-sat with Cadical153 or Cadical195 is required") from exc
    solver_classes = {"Cadical153": Cadical153, "Cadical195": Cadical195}
    if batch_solver_name not in solver_classes:
        raise InputError("batch solver must be Cadical153 or Cadical195")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    base_started = time.perf_counter()
    base = build_base_encoding(v)
    base_encode_seconds = time.perf_counter() - base_started
    solver_class = solver_classes[batch_solver_name]
    init_started = time.perf_counter()
    solver = solver_class(bootstrap_with=base.clauses)
    solver_init_seconds = time.perf_counter() - init_started
    rng = __import__("random").Random(seed)
    results: list[dict[str, object]] = []
    reset_count = 0
    try:
        for index, pts in enumerate(instances):
            instance_started = time.perf_counter()
            assumptions = batch_assumptions(base, pts)
            solve_started = time.perf_counter()
            satisfiable = solver.solve(assumptions=assumptions)
            solve_seconds = time.perf_counter() - solve_started
            common: dict[str, object] = {
                "mode": "batch",
                "batch_index": index,
                "pts": pts.line,
                "verdict": "pseudoline" if satisfiable else "no-pseudoline",
                "variables": base.nvars,
                "clauses": len(base.clauses),
                "gp_relations": base.gp_relations,
                "base_encode_seconds": round(base_encode_seconds, 6),
                "solver_init_seconds": round(solver_init_seconds, 6),
                "solve_seconds": round(solve_seconds, 6),
                "assumption_count": len(assumptions),
                "solver": batch_solver_name,
                "proof_sampled": False,
            }
            if satisfiable:
                model = solver.get_model() or []
                true_vars = {literal for literal in model if literal > 0}
                witness = witness_from_model(
                    Encoding(pts, base.triples, base.index, base.clauses, base.gp_relations, (0, 0, 0, 0)),
                    true_vars,
                )
                check_started = time.perf_counter()
                verify_witness(
                    Encoding(pts, base.triples, base.index, base.clauses, base.gp_relations, (0, 0, 0, 0)),
                    witness,
                )
                common["witness"] = witness
                common["check_seconds"] = round(time.perf_counter() - check_started, 6)
            else:
                if rng.random() < proof_sample_rate:
                    if standalone_solver is None:
                        standalone_solver = find_executable(None, ("/usr/bin/cadical", "cadical"))
                    if checker is None:
                        checker = find_executable(
                            None,
                            (
                                "~/tools/sat/drat-trim/drat-trim",
                                str(Path(__file__).resolve().parent / "scratch" / "drat-trim"),
                                "drat-trim",
                            ),
                        )
                    sampled = solve_one(
                        pts,
                        artifact_dir / "proof-samples" / str(index),
                        standalone_solver,
                        checker,
                    )
                    if sampled["verdict"] != "no-pseudoline" or not sampled.get("proof_verified"):
                        raise RuntimeError("sampled standalone proof did not verify the batch UNSAT")
                    common["proof_sampled"] = True
                    common["proof_sample"] = {
                        "proof_verified": sampled["proof_verified"],
                        "cnf": sampled["cnf"],
                        "witness": sampled["witness"],
                        "proof_sha256": sampled["proof_sha256"],
                        "cnf_sha256": sampled["cnf_sha256"],
                    }
                if kissat is not None:
                    cross_clauses = list(base.clauses) + [[literal] for literal in assumptions]
                    common["second_solver"] = run_kissat(
                        kissat, base.nvars, cross_clauses, artifact_dir
                    )
                    if not common["second_solver"]["agreement"]:  # type: ignore[index]
                        raise RuntimeError("Kissat disagreed with the persistent CaDiCaL verdict")
            common["total_seconds"] = round(time.perf_counter() - instance_started, 6)
            results.append(common)
            if reset_every is not None and (index + 1) % reset_every == 0 and index + 1 < len(instances):
                solver.delete()
                reset_started = time.perf_counter()
                solver = solver_class(bootstrap_with=base.clauses)
                solver_init_seconds += time.perf_counter() - reset_started
                reset_count += 1
    finally:
        solver.delete()
    for result in results:
        result["solver_resets"] = reset_count
    return results


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="PTS file, or - for stdin")
    parser.add_argument("--artifacts", default="artifacts", help="CNF, model and proof directory")
    parser.add_argument("--solver", help="CaDiCaL executable")
    parser.add_argument("--drat-trim", help="drat-trim executable")
    parser.add_argument("--batch", metavar="PTS_FILE", help="homogeneous PTS batch input")
    parser.add_argument("--out", metavar="JSONL", help="batch JSONL output path")
    parser.add_argument(
        "--batch-solver", choices=("Cadical153", "Cadical195"), default="Cadical153",
        help="python-sat persistent solver for batch mode",
    )
    parser.add_argument(
        "--second-solver", choices=("kissat",), help="cross-check batch UNSAT results with Kissat",
    )
    parser.add_argument("--proof-sample-rate", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=0, help="seed for batch proof sampling")
    parser.add_argument("--reset-every", type=int, help="recreate the persistent solver every N instances")
    parser.add_argument(
        "--drop-gp-family",
        choices=("positive", "negative"),
        help="mutation control only: deliberately omit half of every GP constraint",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.batch is not None:
            if args.input != "-":
                raise InputError("use either the positional input or --batch, not both")
            if args.out is None:
                raise InputError("--batch requires --out")
            validate_batch_done(args.batch)
            raw_lines = list(iter_input_lines(args.batch))
            instances = [parse_pts_line(raw_line) for raw_line in raw_lines]
            kissat = None
            if args.second_solver == "kissat":
                kissat = find_executable(
                    None,
                    ("~/tools/sat/kissat/build/kissat", "kissat"),
                )
            standalone_solver = find_executable(None, ("/usr/bin/cadical", "cadical"))
            checker = None
            if args.proof_sample_rate > 0.0:
                checker = find_executable(
                    args.drat_trim,
                    (
                        "~/tools/sat/drat-trim/drat-trim",
                        str(Path(__file__).resolve().parent / "scratch" / "drat-trim"),
                        "drat-trim",
                    ),
                )
            results = solve_batch(
                instances,
                Path(args.artifacts),
                batch_solver_name=args.batch_solver,
                standalone_solver=standalone_solver,
                checker=checker,
                kissat=kissat,
                proof_sample_rate=args.proof_sample_rate,
                seed=args.seed,
                reset_every=args.reset_every,
            )
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as handle:
                for result in results:
                    handle.write(json.dumps(result, sort_keys=True) + "\n")
            return 0
        if args.out is not None:
            raise InputError("--out is valid only with --batch")
        solver = find_executable(args.solver, ("/usr/bin/cadical", "cadical"))
        checker = find_executable(
            args.drat_trim,
            (
                "~/tools/sat/drat-trim/drat-trim",
                str(Path(__file__).resolve().parent / "scratch" / "drat-trim"),
                "drat-trim",
            ),
        )
        count = 0
        for raw_line in iter_input_lines(args.input):
            pts = parse_pts_line(raw_line)
            result = solve_one(
                pts,
                Path(args.artifacts),
                solver,
                checker,
                drop_gp_family=args.drop_gp_family,
            )
            print(json.dumps(result, sort_keys=True), flush=True)
            count += 1
        if count == 0:
            raise InputError("input contains no PTS lines")
        return 0
    except (InputError, OSError, RuntimeError, ValueError) as exc:
        print(f"chirosat: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
