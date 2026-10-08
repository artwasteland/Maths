#!/usr/bin/env python3
"""check/udcheck.py plus the rhombus certificates of research/unit-distance-23/RHOMBUS-SPEC.md.

Written blind to the prover (filter/udrhombus): this file knows the certificate schema of
RHOMBUS-SPEC.md Section 2 and nothing else about how the certificates are made.

What a rhombus certificate proves (RHOMBUS-SPEC.md Section 1).  In an injective unit-distance
embedding f, every 4-cycle C = [u, v, w, x] of G (four distinct vertices, uv, vw, wx, xu edges)
is a rhombus: f(u) + f(w) = f(v) + f(x).  With r(C) = e_u - e_v + e_w - e_x, an integer identity
sum_j l_j r(C_j) = s (e_a - e_b), s != 0, a != b, forces f(a) = f(b), so G is not a unit-distance
graph (verdict "refuted").  An identity sum_j l_j r(C_j) = s (e_a - e_b - e_p + e_q) with pq an
edge forces |f(a) - f(b)| = |f(p) - f(q)| = 1; with ab a non-edge this is the hereditary TU rule
of enum/PRUNING.md L2 (verdict "tu").

Command line: udcheck.py's (certificate path, --graphs, --unknown-file, --manifest-dir,
--data-dir, --expect-n, --expect-m, --allow-any-size, --labelg), plus --forbidden-set {74,398}
(default 74) and --work-dir (where the derived files go; default the system temp directory).

What it does:

  1. Refuses to run (exit 2) unless check/udcheck.py, and for set 398 check/udcheck398.py, hash
     to the pins below.  The kernel later runs from private copies of exactly the bytes that were
     hashed (for set 398 the copy of udcheck398.py hashes the copy of udcheck.py again).
  2. Reads the certificate file exactly as udcheck.py reads it (text mode, UTF-8, universal
     newlines, every line ending in a newline, no blank line, JSON with duplicate keys refused)
     and checks the structure of EVERY record itself: exact top-level keys, graph6 decoding with
     udcheck.py's rules, --expect-n/--expect-m, no duplicate graph6 string anywhere in the file
     (so a rhombus record and a kernel record cannot share a graph), a verdict among the five,
     and with --graphs that the records' graph6 sequence equals the list exactly.
  3. A record is a rhombus record when its witness is an object with the key "rhombus".  Such a
     record must have verdict refuted or tu, and it is verified here against rules 1 to 6 of
     RHOMBUS-SPEC.md Section 2 in Python's arbitrary-precision integers, never a fixed width
     (verify_rhombus); the target is a vector sum, so a pair and an edge sharing a vertex just
     accumulate.  A record whose witness has the key "tri" (Section 4, amendment 2) must have verdict
     refuted or tu and exactly that key, and goes to check/tri_verify.py (class TriVerifier); without
     that module every tri record is rejected, saying so.  The graph6 strings of rhombus and tri records
     must be nauty-labelg canonical (one labelg process for all of them, fed while the file is read,
     compared line by line exactly as udcheck.py's check_canonical_g6_list compares).
  4. Every other record is written, byte for byte as read, to a derived certificate file, and the
     pinned kernel (udcheck.py for set 74, udcheck398.py for set 398) is run on it as a subprocess
     with the same size options, --data-dir, --labelg and --manifest-dir, the same UNKNOWN.g6,
     and, when --graphs was given, a derived graph list cut from the SUPPLIED list at the kernel
     records' positions (so the kernel compares two independently read sources).
  5. Accepts only if the kernel accepts, and its ACCEPT line and UNKNOWN lines agree with this
     file's own tally of the records it handed over (a kernel that checked nothing, or something
     else, cannot pass).  Prints

         ACCEPT certificates records=R forbidden=F tu=T embedded=E refuted=X unknown=U
             proof_nodes=P rhombus_tu=RT rhombus_refuted=RX tri_tu=TT tri_refuted=TX   (one line)

     where tu and refuted include the rhombus and tri records (the two tri counts extend Section 3's
     line for amendment 2's tri records), then udcheck.py's "UNKNOWN <g6>" lines and
     its "ACCEPT manifests" line if any, and exits 0.  Otherwise "REJECT: <reason>" on stderr and
     exit 1 (a kernel rejection is relayed with its line numbers mapped back to this file's).

Decisions the spec leaves open, and why:

  * The UNKNOWN.g6 the kernel is given is the one udcheck.py would use for the original file:
    --unknown-file if given, else UNKNOWN.g6 beside the certificate file (NOT beside the derived
    file).  Rhombus records are never unknown, so the kernel's unknown records are all of them.
  * The kernel is called even when every record is a rhombus record (an empty derived file).
    udcheck.py accepts an empty file, and the call keeps three checks in the kernel's hands with
    no special case here: a stale UNKNOWN.g6 that lists graphs when the file has no unknown
    record is rejected, the trusted data directory is validated, and --manifest-dir is checked.
    The cost is one Python start per call (prune.py calls once per chunk of up to 10^6 records).
  * With no rhombus or tri record the kernel sees exactly the original lines, so the counts are the
    kernel's own, plus rhombus_tu=0 rhombus_refuted=0 tri_tu=0 tri_refuted=0.
  * The order of the pair (a, b) and of the edge (p, q) is free (the spec does not ask a < b);
    reversing one is the same certificate with the sign of s changed.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import signal
import subprocess
import sys
import tempfile
import types
from array import array
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
KERNEL = HERE / "udcheck.py"
KERNEL_SHA256 = "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de"   # udcheck398.KERNEL_SHA256
FRONT398 = HERE / "udcheck398.py"
FRONT398_SHA256 = "783d368c34626ad6fe20574d1ecf7a38aea9d2ebb6aef65e9d88785f16262018"

LIMIT = 1 << 62              # every coefficient and the scale: nonzero, absolute value below 2^62
MAX_CYCLES = 4096
VERDICTS = ("forbidden", "tu", "embedded", "refuted", "unknown")
TOP_KEYS = frozenset(("g6", "verdict"))
TOP_KEYS_W = frozenset(("g6", "verdict", "witness"))
KEYS_REFUTED = frozenset(("cycles", "coefficients", "scale", "pair"))
KEYS_TU = frozenset(("cycles", "coefficients", "scale", "pair", "edge"))
KERNEL_KEYS = ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes")
KERNEL_ACCEPT = re.compile(r"ACCEPT certificates records=(\d+) forbidden=(\d+) tu=(\d+) embedded=(\d+) "
                           r"refuted=(\d+) unknown=(\d+) proof_nodes=(\d+)")


class CheckError(Exception):
    pass


class PinError(Exception):
    pass


def fail(message: str) -> None:
    raise CheckError(message)


# ---------------------------------------------------------------- JSON and graph6, as udcheck.py

def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = dict(pairs)
    if len(out) != len(pairs):
        seen: set[str] = set()
        for key, _ in pairs:
            if key in seen:
                fail(f"JSON object has duplicate key {key!r}")
            seen.add(key)
    return out


def _no_constant(name: str) -> None:
    raise ValueError(f"{name} is not JSON")


_DECODE = json.JSONDecoder(object_pairs_hook=_no_duplicate_object, parse_constant=_no_constant).decode


def parse_json_line(line: str) -> Any:
    try:
        return _DECODE(line)
    except CheckError as exc:
        fail(f"invalid JSON: {exc}")
    except (ValueError, RecursionError) as exc:      # JSONDecodeError is a ValueError
        fail(f"invalid JSON: {type(exc).__name__}: {exc}")


_G6 = re.compile(r"[?-~]+")                                              # graph6 bytes 63..126
_MINUS63 = bytes(c - 63 if 63 <= c <= 126 else 0 for c in range(256))


def decode_graph6(code: Any, where: str = "g6") -> tuple[int, str, int]:
    """(n, bits, m) for a graph6 string, accepting and rejecting exactly what udcheck.py's
    decode_graph6 does (the selftest compares the two on valid and malformed strings).

    bits is the body as a string of "0"/"1", EIGHT characters per graph6 byte: "00" and then the
    byte's six data bits.  So bits[0] is always "0", and the pair uv (u != v) is an edge iff
    bits[pair_index(u, v)] == "1".  m is the number of edges."""
    if type(code) is not str or not code:
        fail(f"{where}: expected nonempty graph6 string")
    if _G6.fullmatch(code) is None:
        fail(f"{where}: unsupported header or non-graph6 byte")
    first = ord(code[0]) - 63
    if first <= 62:
        n, body = first, code[1:]
    elif len(code) >= 4 and code[1] != "~":
        n = ((ord(code[1]) - 63) << 12) | ((ord(code[2]) - 63) << 6) | (ord(code[3]) - 63)
        body = code[4:]
    else:
        fail(f"{where}: graph order encoding is unsupported")
    need = n * (n - 1) // 2
    size = len(body)
    if size != (need + 5) // 6:
        fail(f"{where}: wrong graph6 length for n={n}")
    value = int.from_bytes(body.encode("ascii").translate(_MINUS63), "big")
    if value & ((1 << (6 * size - need)) - 1):          # the padding is the last byte's low bits
        fail(f"{where}: nonzero graph6 padding bits")
    bits = bin(value)[2:].zfill(8 * size)
    return n, bits, bits.count("1")


def pair_index(u: int, v: int) -> int:
    """The character of bits (decode_graph6) holding the pair uv, u != v: graph6 bit
    k = j(j-1)/2 + i for i < j, stored at 8 (k // 6) + 2 + k % 6."""
    i, j = (u, v) if u < v else (v, u)
    k = j * (j - 1) // 2 + i
    return 8 * (k // 6) + 2 + k % 6


_P64 = [[pair_index(u, v) if u != v else 0 for v in range(64)] for u in range(64)]   # diagonal -> bits[0] == "0"


class _PairRows:
    """pair_index rows for n > 64, computed on first use (the programme's graphs have n <= 23)."""

    def __init__(self, n: int):
        self.n = n
        self.rows: dict[int, list[int]] = {}

    def __getitem__(self, u: int) -> list[int]:
        row = self.rows.get(u)
        if row is None:
            row = self.rows[u] = [pair_index(u, v) if u != v else 0 for v in range(self.n)]
        return row


def read_graph_list(path: Path) -> list[str]:
    """udcheck.py's read_graph_list."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read graph list {path}: {exc}")
    if raw and not raw.endswith(b"\n"):
        fail(f"{path}: missing final newline")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        fail(f"{path}: non-ASCII graph list: {exc}")
    if any(not line for line in lines):
        fail(f"{path}: blank graph6 record")
    return lines


# ---------------------------------------------------------------- the rhombus rules, Section 2

def _vertex_pair(value: Any, n: int, rule: str, name: str) -> tuple[int, int]:
    if type(value) is not list or len(value) != 2:
        fail(f"{rule}: {name} must be a list of two JSON integers")
    a, b = value
    if type(a) is not int or type(b) is not int:
        fail(f"{rule}: {name} must be two JSON integers (not booleans, floats or strings)")
    if not (0 <= a < n and 0 <= b < n):
        fail(f"{rule}: {name} {value} has a vertex outside [0, {n})")
    if a == b:
        fail(f"{rule}: {name} {value} is not two distinct vertices")
    return a, b


def _cycle_index(cycles: list, c: Any) -> int:
    return next(i for i, x in enumerate(cycles) if x is c)


def _cycles_exact(cycles: list, coefficients: list, n: int, bits: str, P) -> list[int]:
    """The per-cycle part of rules 2 and 3, check by check, raising CheckError at the first violation
    with its rule; returns sum_j l_j r(C_j) as a list of n integers."""
    acc = [0] * n
    for c, l in zip(cycles, coefficients):
        if type(c) is not list or len(c) != 4:
            fail(f"rule 2: cycles[{_cycle_index(cycles, c)}] is not a list of four vertices")
        u, v, w, x = c
        if not (type(u) is int is type(v) is type(w) is type(x)):
            fail(f"rule 2: cycles[{_cycle_index(cycles, c)}] has a vertex that is not a JSON integer")
        if not (0 <= u < n and 0 <= v < n and 0 <= w < n and 0 <= x < n):
            fail(f"rule 2: cycles[{_cycle_index(cycles, c)}] {c} has a vertex outside [0, {n})")
        if u == v or u == w or u == x or v == w or v == x or w == x:
            fail(f"rule 2: cycles[{_cycle_index(cycles, c)}] {c} repeats a vertex")
        Pu = P[u]
        Pw = P[w]
        if bits[Pu[v]] != "1" or bits[Pw[v]] != "1" or bits[Pw[x]] != "1" or bits[Pu[x]] != "1":
            missing = [[y, z] for y, z in ((u, v), (v, w), (w, x), (x, u)) if bits[P[y][z]] != "1"]
            fail(f"rule 2: cycles[{_cycle_index(cycles, c)}] {c} is not a 4-cycle of G: {missing} not edges")
        if type(l) is not int:
            fail(f"rule 3: coefficients[{_cycle_index(cycles, c)}] is not a JSON integer "
                 f"(booleans, floats and strings are refused)")
        if not l:
            fail(f"rule 3: coefficients[{_cycle_index(cycles, c)}] is zero")
        if not -LIMIT < l < LIMIT:
            fail(f"rule 3: coefficients[{_cycle_index(cycles, c)}] has absolute value 2^62 or more")
        acc[u] += l
        acc[v] -= l
        acc[w] += l
        acc[x] -= l
    return acc


_VERTICES = [list(range(n)) for n in range(257)]     # _VERTICES[n][i] is the int i


def _cycles_fast(cycles: list, coefficients: list, n: int, bits: str, P, lim: int = LIMIT,
                 nlim: int = -LIMIT) -> list[int] | None:
    """The same checks as _cycles_exact, faster, with no verdict of its own: it returns the sum only when
    every check holds, and None (hand over to _cycles_exact) otherwise.  Three shortcuts, each unable to
    let an invalid cycle through:
      * V[u] is u, for V = list(range(n)), holds only when u IS one of the int objects 0..n-1: a boolean,
        float, string or list raises or yields another object, a negative index yields a different
        value.  (CPython shares small ints, so a JSON vertex below 257 passes; any other goes to the
        exact pass, which decides it.)
      * u == v, v == w, w == x and x == u fail the edge test, as P[i][i] == 0 and bits[0] == "0".
      * an entry that is not a list of four makes the unpacking or V[...] raise."""
    V = _VERTICES[n] if n <= 256 else list(range(n))
    acc = [0] * n
    try:
        for (u, v, w, x), l in zip(cycles, coefficients):
            if V[u] is not u or V[v] is not v or V[w] is not w or V[x] is not x or u == w or v == x:
                return None
            Pu = P[u]
            Pw = P[w]
            if bits[Pu[v]] != "1" or bits[Pw[v]] != "1" or bits[Pw[x]] != "1" or bits[Pu[x]] != "1":
                return None
            if type(l) is not int or not l or l >= lim or l <= nlim:
                return None
            acc[u] += l
            acc[v] -= l
            acc[w] += l
            acc[x] -= l
    except (TypeError, ValueError, IndexError):
        return None
    return acc


def verify_rhombus(rh: Any, tu: bool, n: int, bits: str) -> None:
    """Rules 1 to 6 of RHOMBUS-SPEC.md Section 2 for the value of witness["rhombus"] of a record
    of verdict tu (tu=True) or refuted (tu=False) whose graph is (n, bits); the caller has checked
    that the witness object has the key "rhombus" and that the verdict is one of the two.
    Raises CheckError naming the rule on the first violation."""
    want = KEYS_TU if tu else KEYS_REFUTED
    if type(rh) is not dict:
        fail("rule 1: the rhombus witness must be an object")
    if rh.keys() != want:
        fail(f"rule 1: a {'tu' if tu else 'refuted'} rhombus witness has exactly the keys {sorted(want)}; "
             f"missing {sorted(want - rh.keys())}, extra {sorted(rh.keys() - want)}")
    cycles = rh["cycles"]
    coefficients = rh["coefficients"]
    s = rh["scale"]
    if type(cycles) is not list or not cycles:
        fail("rule 2: cycles must be a non-empty list")
    k = len(cycles)
    if k > MAX_CYCLES:
        fail(f"rule 2: {k} cycles, more than {MAX_CYCLES}")
    if type(coefficients) is not list:
        fail("rule 3: coefficients must be a list")
    if len(coefficients) != k:
        fail(f"rule 3: {len(coefficients)} coefficients for {k} cycles")
    if type(s) is not int:
        fail("rule 3: scale must be a JSON integer (not a boolean, float or string)")
    if not s:
        fail("rule 3: scale is zero")
    if not -LIMIT < s < LIMIT:
        fail("rule 3: scale has absolute value 2^62 or more")
    P = _P64 if n <= 64 else _PairRows(n)
    a, b = _vertex_pair(rh["pair"], n, "rule 4", "pair")
    if tu and bits[P[a][b]] == "1":
        fail(f"rule 4: pair [{a}, {b}] is an edge of G; a tu pair must be a non-edge")
    if tu:
        p, q = _vertex_pair(rh["edge"], n, "rule 5", "edge")
        if bits[P[p][q]] != "1":
            fail(f"rule 5: edge [{p}, {q}] is not an edge of G")
    acc = _cycles_fast(cycles, coefficients, n, bits, P)
    if acc is None:
        acc = _cycles_exact(cycles, coefficients, n, bits, P)
    acc[a] -= s
    acc[b] += s
    if tu:
        acc[p] += s
        acc[q] -= s
    if any(acc):
        off = [i for i, z in enumerate(acc) if z]
        target = "s(e_a - e_b - e_p + e_q)" if tu else "s(e_a - e_b)"
        fail(f"rule 6: sum_j l_j r(C_j) is not {target}: they differ at vertices {off[:10]}")


def rhombus_record(record: dict, n: int, bits: str) -> bool:
    """False if the record is not a rhombus record (it goes to the kernel); True if it is one and
    passes Section 2; CheckError otherwise.  The caller has checked the top-level keys, the graph
    (n, bits = decode_graph6(record["g6"])) and that the verdict is one of udcheck.py's five."""
    witness = record.get("witness")
    if type(witness) is not dict or "rhombus" not in witness:
        return False
    verdict = record["verdict"]
    if verdict != "tu" and verdict != "refuted":
        fail(f"witness: verdict {verdict!r} never carries a rhombus witness (rhombus verdicts are refuted "
             f"and tu)")
    if len(witness) != 1:
        fail(f"witness: rule 1: the witness has exactly the key 'rhombus'; extra keys "
             f"{sorted(k for k in witness if k != 'rhombus')}")
    try:
        verify_rhombus(witness["rhombus"], verdict == "tu", n, bits)
    except CheckError as exc:
        fail(f"witness.rhombus: {exc}")
    return True


# ---------------------------------------------------------------- tri witnesses (Section 4), routed

TRI_VERIFY = HERE / "tri_verify.py"
TRI_VERIFY_SHA256: str | None = "78a541004def35e62374fda379ec10392ff8b843a6c7ceeb72855dff6b961299"   # check/tri_verify.py as landed 2026-09-26 (851691456)


class TriVerifier:
    """RHOMBUS-SPEC.md Section 4, amendment 2: a record whose witness has the key "tri" is verified by
    check/tri_verify.py's verify_tri_witness(n, edges, verdict, witness) -> (ok, reason, stats), a module
    written separately and loaded (from the bytes that are hashed, as udcheck398.py loads the kernel) on
    the first tri record, so a file without tri records never touches it.  If the module is absent,
    fails to load, lacks the function or, once TRI_VERIFY_SHA256 is set, hashes to anything else, every
    tri record is rejected with that reason.  The call gets n, the edge set as a frozenset of (i, j)
    with i < j, the verdict string and the record's witness object (the one with the single key "tri")
    as read; the record is accepted only if it returns a 3-tuple (or list) whose first item IS True."""

    def __init__(self, path: Path = TRI_VERIFY, pin: str | None = TRI_VERIFY_SHA256):
        self.path = path
        self.pin = pin
        self.function: Any = None
        self.error: str | None = None

    def load(self) -> Any:
        if self.function is None and self.error is None:
            try:
                raw = self.path.read_bytes()
            except FileNotFoundError:
                self.error = f"no tri verifier: {self.path} is absent, so a tri witness cannot be checked"
            except OSError as exc:
                self.error = f"cannot read the tri verifier {self.path}: {exc}"
            else:
                digest = hashlib.sha256(raw).hexdigest()
                if self.pin is not None and digest != self.pin:
                    self.error = f"{self.path} has sha256 {digest}, not the pinned tri_verify.py {self.pin}"
                else:
                    module = types.ModuleType("tri_verify")
                    module.__file__ = str(self.path)
                    sys.modules[module.__name__] = module       # for dataclasses and the like
                    try:
                        exec(compile(raw, str(self.path), "exec"), module.__dict__)
                    except Exception as exc:
                        self.error = f"the tri verifier {self.path} failed to load: {type(exc).__name__}: {exc}"
                    else:
                        function = getattr(module, "verify_tri_witness", None)
                        if callable(function):
                            self.function = function
                        else:
                            self.error = f"the tri verifier {self.path} has no function verify_tri_witness"
        if self.error is not None:
            fail(f"witness.tri: {self.error}")
        return self.function


def tri_record(record: dict, n: int, bits: str, verifier: TriVerifier) -> bool:
    """False if the record has no tri witness; True if it has one and the tri verifier accepts it;
    CheckError otherwise.  Same preconditions as rhombus_record, which has already returned False."""
    witness = record.get("witness")
    if type(witness) is not dict or "tri" not in witness:
        return False
    verdict = record["verdict"]
    if verdict != "tu" and verdict != "refuted":
        fail(f"witness: verdict {verdict!r} never carries a tri witness (tri verdicts are refuted and tu)")
    if len(witness) != 1:
        fail(f"witness: the witness has exactly the key 'tri'; extra keys "
             f"{sorted(k for k in witness if k != 'tri')}")
    function = verifier.load()
    P = _P64 if n <= 64 else _PairRows(n)
    edges = frozenset((i, j) for j in range(1, n) for i in range(j) if bits[P[i][j]] == "1")
    collecting = gc.isenabled()
    gc.enable()                       # the read loop runs without the cyclic collector; a tree verifier may not
    try:
        result = function(n, edges, verdict, witness)
    except (Exception, SystemExit) as exc:
        fail(f"witness.tri: the tri verifier raised {type(exc).__name__}: {exc}")
    finally:
        if not collecting:
            gc.disable()
    if type(result) not in (tuple, list) or len(result) != 3:
        fail(f"witness.tri: the tri verifier returned {type(result).__name__} {str(result)[:80]}, "
             f"not (ok, reason, stats)")
    ok, reason = result[0], result[1]
    if ok is not True:
        fail(f"witness.tri: {reason if isinstance(reason, str) and reason else 'rejected by the tri verifier'}"
             f"{'' if ok is False else f' (ok was {ok!r}, not True)'}")
    return True


# ---------------------------------------------------------------- the kernel

def pinned_kernel(forbidden_set: int) -> dict[str, bytes]:
    files = [("udcheck.py", KERNEL, KERNEL_SHA256)]
    if forbidden_set == 398:
        files.append(("udcheck398.py", FRONT398, FRONT398_SHA256))
    out: dict[str, bytes] = {}
    for name, path, pin in files:
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PinError(f"cannot read the pinned kernel {path}: {exc}") from None
        digest = hashlib.sha256(raw).hexdigest()
        if digest != pin:
            raise PinError(f"{path} has sha256 {digest}, not the pinned {name} {pin}")
        out[name] = raw
    return out


class Labelg:
    """nauty-labelg -q, fed one graph6 string per line while the file is read, its output compared
    at the end with its input, as udcheck.py's check_canonical_g6_list compares."""

    def __init__(self, labelg: str, tmp: Path, where: str):
        self.labelg = labelg
        self.where = where
        self.out_path = tmp / "rhombus.labelg.out"
        self.err_path = tmp / "rhombus.labelg.err"
        self.codes: list[str] = []
        self.lines = array("q")                # the certificate file's line number of each code
        self.sent = 0
        self.proc: subprocess.Popen | None = None

    def add(self, code: str, lineno: int) -> None:
        if self.proc is None:
            try:
                with self.out_path.open("wb") as out, self.err_path.open("wb") as err:
                    self.proc = subprocess.Popen([self.labelg, "-q"], stdin=subprocess.PIPE, stdout=out,
                                                 stderr=err)
            except OSError as exc:
                fail(f"canonical graph6 check could not run {self.labelg}: {exc}")
        self.codes.append(code)
        self.lines.append(lineno)
        if len(self.codes) - self.sent >= 2048:
            self._send()

    def _send(self) -> None:
        batch = self.codes[self.sent:]
        self.sent = len(self.codes)
        try:
            self.proc.stdin.write(("\n".join(batch) + "\n").encode("ascii"))
        except OSError as exc:        # labelg died early; its exit status is reported by finish()
            self.finish(broken=exc)

    def finish(self, broken: OSError | None = None) -> None:
        if self.proc is None:
            return
        if broken is None and self.sent < len(self.codes):
            self._send()
            if self.proc is None:
                return
        proc, self.proc = self.proc, None
        try:
            proc.stdin.close()
        except OSError as exc:
            broken = broken or exc
        returncode = proc.wait()
        if returncode != 0 or broken is not None:
            err = self.err_path.read_bytes().decode(errors="replace").strip()
            fail(f"canonical graph6 check failed (exit {returncode}): {err or broken}")
        try:
            lines = self.out_path.read_bytes().decode("ascii").splitlines()
        except UnicodeError as exc:
            fail(f"canonical graph6 check: labelg output is not ASCII: {exc}")
        if lines != self.codes:
            first = next((i for i in range(max(len(lines), len(self.codes)))
                          if i >= len(lines) or i >= len(self.codes) or lines[i] != self.codes[i]), 0)
            if first >= len(self.codes):
                fail(f"canonical graph6 check: labelg wrote {len(lines)} lines for {len(self.codes)} graphs")
            fail(f"{self.where}:{self.lines[first]}.g6: {self.codes[first]} is not nauty-labelg canonical "
                 f"(labelg gives {lines[first] if first < len(lines) else 'nothing'})")
        self.codes = []
        self.lines = array("q")

    def kill(self) -> None:
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait()
            self.proc = None


# ---------------------------------------------------------------- the file

def check(args: argparse.Namespace, kernel_files: dict[str, bytes], tmp: Path) -> list[str]:
    cert_path: Path = args.certificates
    unknown_path = (args.unknown_file if args.unknown_file is not None
                    else cert_path.parent / "UNKNOWN.g6").absolute()
    expect_n = None if args.allow_any_size else args.expect_n
    expect_m = None if args.allow_any_size else args.expect_m
    graphs = read_graph_list(args.graphs) if args.graphs is not None else None
    kdir = tmp / "check"
    kdir.mkdir()
    for name, raw in kernel_files.items():
        (kdir / name).write_bytes(raw)
    kernel_entry = kdir / ("udcheck398.py" if args.forbidden_set == 398 else "udcheck.py")
    kernel_certs = tmp / "kernel.certs.jsonl"
    kernel_graphs = tmp / "kernel.g6"

    seen: set[str] = set()
    kernel_lines = array("q")                  # original line number of each record handed to the kernel
    kernel_tally = dict.fromkeys(VERDICTS, 0)
    unknown_codes: list[str] = []
    rhombus_tu = rhombus_refuted = tri_tu = tri_refuted = 0
    records = 0
    tri = TriVerifier()
    labelg = Labelg(args.labelg, tmp, str(cert_path))
    decode = _DECODE
    # Every object made below is a tree that reference counting frees; the cyclic collector would
    # only re-scan the parser's young objects (about a tenth of the time).
    gc.disable()
    try:
        try:
            stream = cert_path.open("r", encoding="utf-8")
        except OSError as exc:
            fail(f"cannot open certificate file {cert_path}: {exc}")
        with stream, kernel_certs.open("w", encoding="utf-8", newline="\n") as kout, \
                kernel_graphs.open("w", encoding="ascii", newline="\n") as gout:
            lineno = 0
            try:
                for line in stream:
                    lineno += 1
                    if not line.endswith("\n"):
                        fail(f"{cert_path}:{lineno}: missing final newline")
                    if line.isspace():
                        fail(f"{cert_path}:{lineno}: blank certificate record")
                    try:
                        record = decode(line)
                    except CheckError as exc:
                        fail(f"{cert_path}:{lineno}: invalid JSON: {exc}")
                    except (ValueError, RecursionError) as exc:      # JSONDecodeError is a ValueError
                        fail(f"{cert_path}:{lineno}: invalid JSON: {type(exc).__name__}: {exc}")
                    if type(record) is not dict or (record.keys() != TOP_KEYS_W and record.keys() != TOP_KEYS):
                        keys = sorted(record) if type(record) is dict else type(record).__name__
                        fail(f"{cert_path}:{lineno}: a record has exactly the keys g6, verdict and optionally "
                             f"witness; got {keys}")
                    code = record["g6"]
                    try:
                        n, bits, m = decode_graph6(code)
                    except CheckError as exc:
                        fail(f"{cert_path}:{lineno}.{exc}")
                    if expect_n is not None and n != expect_n:
                        fail(f"{cert_path}:{lineno}: expected {expect_n} vertices, got {n}")
                    if expect_m is not None and m != expect_m:
                        fail(f"{cert_path}:{lineno}: expected {expect_m} edges, got {m}")
                    if code in seen:
                        fail(f"{cert_path}:{lineno}: duplicate graph6 record {code}")
                    seen.add(code)
                    if graphs is not None and (records >= len(graphs) or graphs[records] != code):
                        fail(f"{cert_path}:{lineno}: record {records + 1} is {code}, but line {records + 1} of "
                             f"{args.graphs} is {graphs[records] if records < len(graphs) else 'absent'}: the "
                             f"records' graph6 sequence must equal the graph list exactly")
                    records += 1
                    verdict = record["verdict"]
                    if type(verdict) is not str or verdict not in kernel_tally:
                        fail(f"{cert_path}:{lineno}.verdict: unsupported verdict {verdict!r}")
                    try:
                        rhombus = rhombus_record(record, n, bits)
                        triangle = not rhombus and tri_record(record, n, bits, tri)
                    except CheckError as exc:
                        fail(f"{cert_path}:{lineno}.{exc}")
                    if rhombus:
                        if verdict == "tu":
                            rhombus_tu += 1
                        else:
                            rhombus_refuted += 1
                        labelg.add(code, lineno)
                    elif triangle:
                        if verdict == "tu":
                            tri_tu += 1
                        else:
                            tri_refuted += 1
                        labelg.add(code, lineno)
                    else:
                        kout.write(line)
                        kernel_lines.append(lineno)
                        kernel_tally[verdict] += 1
                        if graphs is not None:
                            gout.write(graphs[records - 1] + "\n")
                        if verdict == "unknown":
                            unknown_codes.append(code)
            except UnicodeDecodeError as exc:
                fail(f"{cert_path}: not UTF-8 at or after line {lineno + 1}: {exc}")
        if graphs is not None and records != len(graphs):
            fail(f"certificate graph6 records do not exactly equal the supplied graph list in order: "
                 f"{records} records, {len(graphs)} listed graphs")
        del graphs, seen
        labelg.finish()
    finally:
        gc.enable()
        labelg.kill()

    command = [sys.executable, str(kernel_entry), "--data-dir", str(args.data_dir.absolute()),
               "--labelg", args.labelg]
    if args.allow_any_size:
        command.append("--allow-any-size")
    else:
        command += ["--expect-n", str(args.expect_n), "--expect-m", str(args.expect_m)]
    if args.graphs is not None:
        command += ["--graphs", str(kernel_graphs)]
    command += ["--unknown-file", str(unknown_path)]
    if args.manifest_dir is not None:
        command += ["--manifest-dir", str(args.manifest_dir.absolute())]
    command.append(str(kernel_certs))
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        fail(f"could not run the pinned kernel {kernel_entry.name}: {exc}")
    kernel_name = "udcheck398.py" if args.forbidden_set == 398 else "udcheck.py"
    if proc.returncode != 0:
        def original(match: re.Match) -> str:
            i = int(match.group(1))
            return f"{cert_path}:{kernel_lines[i - 1]}" if 1 <= i <= len(kernel_lines) else match.group(0)
        message = re.sub(re.escape(str(kernel_certs)) + r":(\d+)", original, proc.stderr.strip())
        fail(f"the pinned kernel {kernel_name} rejected the records handed to it, those with neither a rhombus "
             f"nor a tri witness (exit {proc.returncode}): {message}")
    out = proc.stdout.splitlines()
    got = KERNEL_ACCEPT.fullmatch(out[0]) if out else None
    if got is None:
        fail(f"the pinned kernel {kernel_name} exited 0 without its ACCEPT line: {proc.stdout[:200]!r}")
    counts = dict(zip(KERNEL_KEYS, map(int, got.groups())))
    handed = {"records": len(kernel_lines), **kernel_tally}
    for key, value in handed.items():
        if counts[key] != value:
            fail(f"the pinned kernel counted {key}={counts[key]} on the {len(kernel_lines)} records it was "
                 f"given, which hold {key}={value}")
    tail = out[1:]
    if tail[:len(unknown_codes)] != [f"UNKNOWN {c}" for c in unknown_codes]:
        fail("the pinned kernel's UNKNOWN lines are not the unknown records in order")
    tail = tail[len(unknown_codes):]
    manifests = [t for t in tail if t.startswith("ACCEPT manifests ")]
    if len(tail) != (1 if args.manifest_dir is not None else 0) or len(manifests) != len(tail):
        fail(f"the pinned kernel printed unexpected lines: {tail[:3]}")
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    summary = {**counts, "records": records, "tu": counts["tu"] + rhombus_tu + tri_tu,
               "refuted": counts["refuted"] + rhombus_refuted + tri_refuted,
               "rhombus_tu": rhombus_tu, "rhombus_refuted": rhombus_refuted,
               "tri_tu": tri_tu, "tri_refuted": tri_refuted}
    keys = (*KERNEL_KEYS, "rhombus_tu", "rhombus_refuted", "tri_tu", "tri_refuted")
    return ["ACCEPT certificates " + " ".join(f"{key}={summary[key]}" for key in keys),
            *(f"UNKNOWN {c}" for c in unknown_codes), *manifests]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("certificates", type=Path,
                        help="JSON-lines certificate file (udcheck.py's, plus rhombus and tri witnesses)")
    parser.add_argument("--graphs", type=Path, help="graph6 list which certificates must match exactly")
    parser.add_argument("--unknown-file", type=Path, help="UNKNOWN.g6 path (default beside certificates)")
    parser.add_argument("--manifest-dir", type=Path, help="directory of shard JSON manifests (checked by the kernel)")
    parser.add_argument("--data-dir", type=Path, default=HERE.parent / "data")
    parser.add_argument("--expect-n", type=int, default=22)
    parser.add_argument("--expect-m", type=int, default=61)
    parser.add_argument("--allow-any-size", action="store_true",
                        help="disable the default (22,61) order and size gate for self-checks")
    parser.add_argument("--labelg", default="/usr/bin/nauty-labelg")
    parser.add_argument("--forbidden-set", type=int, choices=(74, 398), default=74,
                        help="kernel for the records with neither a rhombus nor a tri witness: "
                             "74 = udcheck.py, 398 = udcheck398.py")
    parser.add_argument("--work-dir", type=Path, help="where the derived files go (default: system temp)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        kernel_files = pinned_kernel(args.forbidden_set)
    except PinError as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 2
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))   # clean up the temp dir
    try:
        with tempfile.TemporaryDirectory(prefix="udcheck-rhombus-", dir=args.work_dir) as tmp:
            lines = check(args, kernel_files, Path(tmp))
    except CheckError as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
