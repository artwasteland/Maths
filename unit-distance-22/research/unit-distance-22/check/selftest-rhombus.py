#!/usr/bin/env python3
"""Controls for check/udcheck_rhombus.py, the checker of the rhombus certificates
(research/unit-distance-23/RHOMBUS-SPEC.md).  Written blind to the prover (filter/udrhombus).

Every certificate here is made by this file's own test prover: exact Fractions over the rows
r(C) = e_u - e_v + e_w - e_x of ALL the 4-cycles of a graph, kept in reduced row echelon form with the
combination of cycles behind every basis row, and scaled to integers.  A second, deliberately plain
reading of Section 2 (oracle) confirms every certificate before the checker sees it.

Through the real command line, for --forbidden-set 74 and for 398:

  green  K2,3 (refuted); each of the six gadgets of data/tu-gadgets.json, tu on its distinguished pair;
         random graphs with certificates; boundary values (coefficients and scale 2^62 - 1, exactly
         4096 cycles, running sums that pass 2^63 and come back); rewritings that must stay valid (pair
         and edge reversed with s negated, a cycle rotated with its coefficient negated, a cycle
         reversed, a split coefficient, other JSON spellings, CRLF line ends); targets that are vector
         sums with a shared vertex (a == p and b == q, where e_t cancels; q == a on a GP-10 graph, where
         the entry doubles); a mixed file with kernel records (a gadget tu in udcheck.py's own schema,
         forbidden records, an exact embedding of the Moser spindle, unknown records with their
         UNKNOWN.g6) whose ACCEPT line must equal the counts computed here; a file with no rhombus
         record, whose counts must equal the kernel's own when it is run directly; the 324 minimal
         forbidden graphs of GP-10 with every certificate the test prover finds for them; --unknown-file
         elsewhere, and prune.py's chunked calling convention with its exact flags.
  red    one mutation per case, each required to exit 1 AND to name the rule it breaks (rules 1 to 6
         of Section 2, verdicts, file structure, --graphs, duplicates, canonical form, UNKNOWN.g6, a
         bad kernel record inside a mixed file), including amendment 2's binding controls that concern
         rhombus records: a repeated vertex in a cycle, and an int64 checker (a certificate whose sums
         pass 2^63 and which a wrapping 64-bit sum would accept); fake certificates for the Moser
         spindle, a genuine unit-distance graph with no valid certificate (five of them satisfy the
         identity exactly: a repeated vertex, a missing edge, an adjacent tu pair, and the zero targets
         of scale 0 and of a == b); the pinned kernel changed by one byte (exit 2).
  tri    the routing of Section 4's tri witnesses to check/tri_verify.py, with a STUB written into a
         temporary copy of the check directory (the real verifier is another agent's and is not read
         here): absent module, accept, reject, raise, a truthy non-True answer, a malformed answer, the
         arguments it receives, exact witness keys, verdicts, canonical form, the optional sha256 pin.

In-process: decode_graph6 against udcheck.py's own decoder on valid and malformed strings; the
checker's rhombus_record against the oracle on random single-point mutations; and, on every mutation
the checker's fast pass accepts, its exact pass must agree.

--bench N: N distinct canonical graphs (n 13..23, 5..40 cycles per certificate) and the checker's rate.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent
DATA = UD / "data"
CHECKER = HERE / "udcheck_rhombus.py"
UDCHECK = HERE / "udcheck.py"
UDCHECK398 = HERE / "udcheck398.py"
LABELG = "/usr/bin/nauty-labelg"
# the checker's interpreter: $UDCHECK_PYTHON, else the maths venv where it exists, else this one
# (the kernel runs under the same interpreter and needs SymPy for the embedded Moser spindle)
_MATHS = Path.home() / "tools/pyenv-maths/bin/python"
PYTHON = Path(os.environ.get("UDCHECK_PYTHON") or (_MATHS if _MATHS.is_file() else sys.executable))
BIG = 1 << 62
P61 = (1 << 61) - 1          # the prover's detection prime
GADGETS = json.loads((DATA / "tu-gadgets.json").read_text())
F74 = json.loads((DATA / "forbidden-74.json").read_text())
F398 = json.loads((DATA / "forbidden-398.json").read_text())

failures: list[str] = []
passes = 0


def expect(name: str, ok: bool, detail: str = "") -> None:
    global passes
    if ok:
        passes += 1
    else:
        failures.append(name)
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)


def info(text: str) -> None:
    print(f"INFO {text}", flush=True)


# ---------------------------------------------------------------- graphs

def g6_encode(n: int, edges) -> str:
    es = {(min(e), max(e)) for e in edges}
    bits = [1 if (i, j) in es else 0 for j in range(1, n) for i in range(j)]
    bits += [0] * (-len(bits) % 6)
    head = chr(n + 63) if n <= 62 else "~" + "".join(chr(63 + ((n >> s) & 63)) for s in (12, 6, 0))
    return head + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2)) for k in range(0, len(bits), 6))


def g6_decode(code: str) -> tuple[int, set]:
    if code[0] == "~":
        n, body = ((ord(code[1]) - 63) << 12) | ((ord(code[2]) - 63) << 6) | (ord(code[3]) - 63), code[4:]
    else:
        n, body = ord(code[0]) - 63, code[1:]
    bits = "".join(format(ord(c) - 63, "06b") for c in body)
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                edges.add((i, j))
            k += 1
    return n, edges


def canonical(codes: list[str]) -> list[str]:
    out = subprocess.run([LABELG, "-q"], input="".join(c + "\n" for c in codes), text=True,
                         capture_output=True, check=True).stdout.split()
    assert len(out) == len(codes)
    return out


def adjacency(n: int, edges) -> list[set]:
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def embeddings(pn: int, pedges, hn: int, hedges):
    """Injective maps (lists) of the pattern into the host sending every pattern edge onto a host edge."""
    padj, hadj = adjacency(pn, pedges), adjacency(hn, hedges)
    order, seen = [], set()
    for start in sorted(range(pn), key=lambda v: -len(padj[v])):
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        while queue:
            v = queue.pop(0)
            order.append(v)
            for w in sorted(padj[v]):
                if w not in seen:
                    seen.add(w)
                    queue.append(w)
    phi: list = [None] * pn
    used: set = set()

    def extend(i: int):
        if i == pn:
            yield list(phi)
            return
        v = order[i]
        placed = [phi[w] for w in padj[v] if phi[w] is not None]
        cands = (set.intersection(*(hadj[h] for h in placed)) if placed else set(range(hn))) - used
        for h in sorted(cands):
            if len(hadj[h]) < len(padj[v]):
                continue
            phi[v] = h
            used.add(h)
            yield from extend(i + 1)
            phi[v] = None
            used.discard(h)

    yield from extend(0)


def to_canonical(n: int, edges) -> tuple[str, set, list[int]]:
    """(canonical g6, its edges, phi): phi maps the given labelling isomorphically onto the canonical one."""
    edges = {(min(e), max(e)) for e in edges}
    code = canonical([g6_encode(n, edges)])[0]
    cn, cedges = g6_decode(code)
    assert cn == n and len(cedges) == len(edges)
    phi = next(embeddings(n, edges, cn, cedges))        # bijective, edges onto edges, equal counts
    return code, cedges, phi


# ---------------------------------------------------------------- the test prover (exact, over Q)

def four_cycles(n: int, adj: list[set]) -> list[tuple]:
    """Every 4-cycle of the graph once: u its least vertex, v < x fixes the orientation."""
    out = []
    for u in range(n):
        for v in adj[u]:
            if v <= u:
                continue
            for w in adj[v]:
                if w <= u or w == v:
                    continue
                for x in adj[w]:
                    if x <= u or x == v or x == w or u not in adj[x]:
                        continue
                    if v < x:
                        out.append((u, v, w, x))
    return sorted(out)


def cycle_row(n: int, c) -> list[int]:
    r = [0] * n
    u, v, w, x = c
    r[u] += 1
    r[v] -= 1
    r[w] += 1
    r[x] -= 1
    return r


def rhombus_witness(verdict, cycles, coefficients, scale, pair, edge=None):
    rh = {"cycles": cycles, "coefficients": coefficients, "scale": scale, "pair": pair}
    if edge is not None:
        rh["edge"] = edge
    return verdict, {"rhombus": rh}


class TestProver:
    """Reduced row echelon form of the 4-cycle rows over Q; basis entries (pivot, row, combination),
    row == sum_k combination[k] r(cycles[k]) always."""

    def __init__(self, n: int, edges):
        self.n = n
        self.edges = {(min(e), max(e)) for e in edges}
        self.adj = adjacency(n, self.edges)
        self.cycles = four_cycles(n, self.adj)
        self.basis: list = []
        for idx, c in enumerate(self.cycles):
            self._insert(idx, cycle_row(n, c))

    def _reduce(self, target):
        vec, combo = [Fraction(z) for z in target], {}
        for piv, bv, bc in self.basis:
            f = vec[piv]
            if f:
                vec = [p - f * q for p, q in zip(vec, bv)]
                for k, z in bc.items():
                    combo[k] = combo.get(k, 0) + f * z
        return vec, combo                                  # vec == target - sum combo[k] r_k

    def _insert(self, idx: int, row) -> None:
        vec, combo = self._reduce(row)
        piv = next((i for i, z in enumerate(vec) if z), None)
        if piv is None:
            return
        comb = {k: -z for k, z in combo.items()}
        comb[idx] = comb.get(idx, 0) + 1
        c = vec[piv]
        vec = [z / c for z in vec]
        comb = {k: z / c for k, z in comb.items()}
        for i, (bp, bv, bc) in enumerate(self.basis):
            f = bv[piv]
            if f:
                nc = dict(bc)
                for k, z in comb.items():
                    nc[k] = nc.get(k, 0) - f * z
                self.basis[i] = (bp, [p - f * q for p, q in zip(bv, vec)], nc)
        self.basis.append((piv, vec, comb))

    def unit(self, a, b, p=None, q=None) -> list[int]:
        t = [0] * self.n
        t[a] += 1
        t[b] -= 1
        if p is not None:
            t[p] -= 1
            t[q] += 1
        return t

    def solve(self, target):
        """(cycles, coefficients, scale) with sum l_k r(C_k) = scale * target, or None."""
        vec, combo = self._reduce(target)
        if any(vec):
            return None
        combo = {k: z for k, z in combo.items() if z}
        den = 1
        for z in combo.values():
            den = den * z.denominator // gcd(den, z.denominator)
        ls = {k: int(z * den) for k, z in combo.items()}
        g = den
        for z in ls.values():
            g = gcd(g, z)
        keys = sorted(ls)
        return [list(self.cycles[k]) for k in keys], [ls[k] // g for k in keys], den // g

    def force(self, a: int, b: int):
        """A tu witness for the pair (a, b) with the first ordered edge forcing it, or None."""
        ra = self._reduce(self.unit(a, b))[0]
        for p in range(self.n):
            for q in sorted(self.adj[p]):
                if self._reduce(self.unit(p, q))[0] == ra:
                    return rhombus_witness("tu", *self.solve(self.unit(a, b, p, q)), [a, b], [p, q])
        return None

    def doubled(self):
        """A tu witness whose target doubles an entry (edge (p, a), so q == a and the target is
        2 e_a - e_b - e_p), on a graph with no collision; None if there is none."""
        n = self.n
        zero = [Fraction(0)] * n
        res = {(a, b): self._reduce(self.unit(a, b))[0] for a in range(n) for b in range(n) if a != b}
        if any(r == zero for r in res.values()):
            return None
        for (a, b), r in sorted(res.items()):
            if (min(a, b), max(a, b)) in self.edges:
                continue
            for p in sorted(self.adj[a]):
                if res[p, a] == r:
                    return rhombus_witness("tu", *self.solve(self.unit(a, b, p, a)), [a, b], [p, a])
        return None

    def find(self):
        """RHOMBUS-SPEC.md's priority: a collision (first pair a < b), else a forced unit distance on a
        non-adjacent pair (first pair a < b, first ordered edge), else None."""
        n = self.n
        zero = [Fraction(0)] * n
        res = {(a, b): self._reduce(self.unit(a, b))[0] for a in range(n) for b in range(a + 1, n)}
        for (a, b), r in res.items():
            if r == zero:
                return rhombus_witness("refuted", *self.solve(self.unit(a, b)), [a, b])
        for (a, b), r in res.items():
            if (a, b) in self.edges:
                continue
            for p in range(n):
                for q in sorted(self.adj[p]):
                    rpq = res[p, q] if p < q else [-z for z in res[q, p]]
                    if rpq == r:
                        return rhombus_witness("tu", *self.solve(self.unit(a, b, p, q)), [a, b], [p, q])
        return None


# ---------------------------------------------------------------- a second reading of Section 2

def oracle(record: dict, n: int, edges) -> bool | None:
    """None: not a rhombus record (the kernel's).  True/False: a valid/invalid rhombus record."""
    w = record.get("witness")
    if not isinstance(w, dict) or "rhombus" not in w:
        return None
    verdict = record.get("verdict")
    if verdict not in ("refuted", "tu") or list(w) != ["rhombus"]:
        return False
    rh = w["rhombus"]
    want = {"cycles", "coefficients", "scale", "pair"} | ({"edge"} if verdict == "tu" else set())
    if not isinstance(rh, dict) or set(rh) != want:
        return False
    E = {frozenset(e) for e in edges}

    def jint(z):
        return isinstance(z, int) and not isinstance(z, bool)

    def vertex(z):
        return jint(z) and 0 <= z < n

    def small(z):
        return jint(z) and z != 0 and -BIG < z < BIG

    def two(pr):
        return isinstance(pr, list) and len(pr) == 2 and all(map(vertex, pr)) and pr[0] != pr[1]

    cyc, co, s = rh["cycles"], rh["coefficients"], rh["scale"]
    if not isinstance(cyc, list) or not 1 <= len(cyc) <= 4096:
        return False
    for c in cyc:
        if not isinstance(c, list) or len(c) != 4 or not all(map(vertex, c)) or len(set(c)) != 4:
            return False
        if any(frozenset((c[i], c[(i + 1) % 4])) not in E for i in range(4)):
            return False
    if not isinstance(co, list) or len(co) != len(cyc) or not all(map(small, co)) or not small(s):
        return False
    if not two(rh["pair"]):
        return False
    a, b = rh["pair"]
    target = {a: s, b: -s}
    if verdict == "tu":
        if frozenset((a, b)) in E or not two(rh["edge"]):
            return False
        p, q = rh["edge"]
        if frozenset((p, q)) not in E:
            return False
        target[p] = target.get(p, 0) - s
        target[q] = target.get(q, 0) + s
    got: dict = {}
    for c, l in zip(cyc, co):
        for sign, z in zip((1, -1, 1, -1), c):
            got[z] = got.get(z, 0) + sign * l
    return all(got.get(z, 0) == target.get(z, 0) for z in set(got) | set(target))


def record(code: str, verdict: str, w=None) -> dict:
    r = {"g6": code, "verdict": verdict}
    if w is not None:
        r["witness"] = w
    return r


def rhombus_rec(code: str, found) -> dict:
    verdict, w = found
    return record(code, verdict, w)


# ---------------------------------------------------------------- the checker's command line

def dump(records) -> str:
    return "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records)


def run_cli(records=None, *, raw: bytes | None = None, fset: int = 74, graphs="auto", unknown="auto",
            size=None, extra=(), checker: Path = CHECKER, data_dir: Path | None = None,
            unknown_at: str | None = None, beside: list | None = None, env: dict | None = None):
    with tempfile.TemporaryDirectory(prefix="st-rhombus-") as tmp:
        tmp = Path(tmp)
        cert = tmp / "certs.jsonl"
        cert.write_bytes(raw if raw is not None else dump(records).encode())
        cmd = [str(PYTHON), str(checker), "--forbidden-set", str(fset)]
        cmd += ["--expect-n", str(size[0]), "--expect-m", str(size[1])] if size else ["--allow-any-size"]
        if isinstance(graphs, str) and graphs == "auto":
            graphs = [r["g6"] for r in records]
        if graphs is not None:
            (tmp / "graphs.g6").write_text("".join(c + "\n" for c in graphs))
            cmd += ["--graphs", str(tmp / "graphs.g6")]
        if isinstance(unknown, str) and unknown == "auto":
            unknown = [r["g6"] for r in records if r.get("verdict") == "unknown"] or None
        if unknown is not None:
            where = tmp / (unknown_at or "UNKNOWN.g6")
            where.parent.mkdir(parents=True, exist_ok=True)
            where.write_text("".join(c + "\n" for c in unknown))
            if unknown_at:
                cmd += ["--unknown-file", str(where)]
        if beside is not None:
            (tmp / "UNKNOWN.g6").write_text("".join(c + "\n" for c in beside))
        if data_dir is not None:
            cmd += ["--data-dir", str(data_dir)]
        cmd += [*[str(e).replace("{tmp}", str(tmp)) for e in extra], str(cert)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                           env={**os.environ, **env} if env else None)
        return p.returncode, p.stdout, p.stderr


def accept_line(records=0, forbidden=0, tu=0, embedded=0, refuted=0, unknown=0, proof_nodes=0,
                rhombus_tu=0, rhombus_refuted=0, tri_tu=0, tri_refuted=0) -> str:
    return (f"ACCEPT certificates records={records} forbidden={forbidden} tu={tu} embedded={embedded} "
            f"refuted={refuted} unknown={unknown} proof_nodes={proof_nodes} rhombus_tu={rhombus_tu} "
            f"rhombus_refuted={rhombus_refuted} tri_tu={tri_tu} tri_refuted={tri_refuted}")


def expected_line(records) -> str:
    c = dict.fromkeys(("forbidden", "tu", "embedded", "refuted", "unknown", "rhombus_tu", "rhombus_refuted",
                       "tri_tu", "tri_refuted"), 0)
    for r in records:
        c[r["verdict"]] += 1
        w = r.get("witness")
        for kind in ("rhombus", "tri"):
            if isinstance(w, dict) and kind in w:
                c[f"{kind}_{r['verdict']}"] += 1
    return accept_line(records=len(records), **c)


def accept(name: str, records=None, line: str | None = None, **kw) -> str:
    rc, out, err = run_cli(records, **kw)
    first = out.splitlines()[0] if out else ""
    ok = rc == 0 and first.startswith("ACCEPT certificates ") and (line is None or first == line) and not err.strip()
    expect(name, ok, first if ok else f"exit {rc}: {first!r} wanted {line!r} {err.strip()[:300]}")
    return out


def reject(name: str, needle: str, records=None, code: int = 1, **kw) -> None:
    rc, out, err = run_cli(records, **kw)
    err = err.strip()
    ok = rc == code and "ACCEPT" not in out and err.startswith("REJECT: ") and needle in err
    expect(name, ok, err[:360] if ok else f"exit {rc} (wanted {code} naming {needle!r}): {out[:120]!r} {err[:300]}")


# ---------------------------------------------------------------- fixtures

class Fixtures:
    """Graphs and certificates, all in nauty-labelg canonical labelling, all confirmed by the oracle."""

    def __init__(self, rng: random.Random):
        self.graph: dict[str, tuple[int, set]] = {}         # g6 -> (n, edges)
        # K2,3: parts {0,1} and {2,3,4}
        code, edges, _ = to_canonical(5, {(a, b) for a in (0, 1) for b in (2, 3, 4)})
        self.k23 = self.checked(rhombus_rec(code, TestProver(5, edges).find()), edges, "K2,3")
        assert self.k23["witness"]["rhombus"]["scale"] == 1
        # the six gadgets, tu on the distinguished pair
        self.gadgets = []
        for i, g in enumerate(GADGETS):
            code, edges, phi = to_canonical(g["n"], {tuple(e) for e in g["edges"]})
            prover = TestProver(g["n"], edges)
            a, b = phi[g["pair"][0]], phi[g["pair"][1]]
            found = prover.force(a, b)
            expect(f"setup: gadget {i}'s distinguished pair ({g['pair'][0]},{g['pair'][1]}) -> canonical "
                   f"({a},{b}) is forced over Q by its 4-cycle rows", found is not None,
                   f"{len(prover.cycles)} 4-cycles, rank {len(prover.basis)}; certificate "
                   f"{json.dumps(found[1]['rhombus']) if found else None}")
            collision = prover.find()
            if collision is not None and collision[0] == "refuted":
                info(f"gadget {i} has a rhombus COLLISION (it would not be unit-distance): {collision}")
            if found is not None:
                self.gadgets.append(self.checked(rhombus_rec(code, found), edges, f"gadget {i}"))
        # random graphs with certificates
        self.random = self.random_certificates(rng)
        # kernel records
        self.kernel_tu = self.kernel_tu_record(1)
        self.forbidden0 = self.forbidden_record(F74[0], 0, extra_vertices=1)
        self.forbidden74 = self.forbidden_record(F398[74], 74, extra_vertices=1)
        self.unknowns = []
        for n, edges in ((6, [(i, (i + 1) % 6) for i in range(6)]), (5, [(0, 1), (1, 2), (2, 3), (3, 4)]),
                         (8, [(i, (i + 1) % 8) for i in range(8)] + [(0, 4)])):
            code, cedges, _ = to_canonical(n, edges)
            self.graph[code] = (n, cedges)
            self.unknowns.append(record(code, "unknown"))
        self.spindle_setup()
        self.big: list[dict] = []
        self.overlaps = self.overlap_fixtures()

    def checked(self, rec: dict, edges, name: str) -> dict:
        n, dedges = g6_decode(rec["g6"])
        assert dedges == set(edges), name
        ok = oracle(rec, n, dedges)
        if not ok:
            expect(f"setup: the oracle confirms the test prover's certificate for {name}", False, json.dumps(rec))
        self.graph[rec["g6"]] = (n, dedges)
        return rec

    def overlap_fixtures(self) -> list[tuple[str, dict]]:
        """K2,3 (hubs 0, 1; leaves 2, 3, 4) with a pendant vertex 5 on leaf 2.  The leaves collide:
        r(2,0,3,1) - r(3,0,4,1) = e_2 - e_4.  Two tu certificates whose pair and edge share a vertex, the
        target a vector sum in which the shared entry cancels (a collision in disguise, amendment 2)."""
        edges = {(a, b) for a in (0, 1) for b in (2, 3, 4)} | {(2, 5)}
        code, cedges, phi = to_canonical(6, edges)
        cyc = [[phi[v] for v in c] for c in ([2, 0, 3, 1], [3, 0, 4, 1])]
        out = []
        for name, pair, edge, scale in (
                ("a == p: pair [t, z], edge [t, x]; e_t cancels and the target is e_x - e_z", (5, 4), (5, 2), 1),
                ("b == q: pair [z, t], edge [x, t], s = -1; e_t cancels and the target is e_x - e_z",
                 (4, 5), (2, 5), -1)):
            rec = record(code, "tu", {"rhombus": {"cycles": cyc, "coefficients": [1, -1], "scale": scale,
                                                  "pair": [phi[v] for v in pair], "edge": [phi[v] for v in edge]}})
            out.append((name, self.checked(rec, cedges, "overlap " + name[:6])))
        return out

    def random_certificates(self, rng: random.Random) -> list[dict]:
        found = {"refuted": [], "tu": []}
        seen = set()
        for _ in range(400):
            n = rng.randint(7, 11)
            p = rng.uniform(0.22, 0.45)
            edges = {(i, j) for j in range(n) for i in range(j) if rng.random() < p}
            code = canonical([g6_encode(n, edges)])[0]
            if code in seen or code in self.graph:
                continue
            seen.add(code)
            cn, cedges = g6_decode(code)
            got = TestProver(cn, cedges).find()
            if got is not None:
                found[got[0]].append((len(got[1]["rhombus"]["cycles"]), code, cedges, got))
        chosen = []
        for verdict in ("refuted", "tu"):
            best = sorted(found[verdict], key=lambda t: (-t[0], t[1]))[:3]
            for k, code, cedges, got in best:
                chosen.append(self.checked(rhombus_rec(code, got), cedges, f"random {verdict} ({k} cycles)"))
        info(f"random graphs: {len(seen)} tried, {len(found['refuted'])} refuted and {len(found['tu'])} tu "
             f"certificates found; kept the three largest of each: "
             f"{[len(r['witness']['rhombus']['cycles']) for r in chosen]} cycles, scales "
             f"{[r['witness']['rhombus']['scale'] for r in chosen]}")
        return chosen

    def host_with(self, pedges: list, extra_vertices: int) -> tuple[str, set, list[int]]:
        pn = max(max(e) for e in pedges) + 1
        edges = {tuple(sorted(e)) for e in pedges}
        for k in range(extra_vertices):                         # pendant vertices on vertex 0
            edges.add((0, pn + k))
        n = pn + extra_vertices
        code, cedges, _ = to_canonical(n, edges)
        phi = next(embeddings(pn, {tuple(sorted(e)) for e in pedges}, n, cedges))
        self.graph[code] = (n, cedges)
        return code, cedges, phi

    def kernel_tu_record(self, index: int) -> dict:
        g = GADGETS[index]
        code, cedges, phi = self.host_with(g["edges"], 1)
        pair = [phi[g["pair"][0]], phi[g["pair"][1]]]
        assert tuple(sorted(pair)) not in cedges
        return record(code, "tu", {"index": index, "map": phi, "pair": pair})

    def forbidden_record(self, pattern: list, index: int, extra_vertices: int) -> dict:
        code, _, phi = self.host_with(pattern, extra_vertices)
        return record(code, "forbidden", {"index": index, "map": phi})

    def spindle_setup(self) -> None:
        # O=0, A1=1, B1=2, T1=3, A2=4, B2=5, T2=6: two unit rhombi O-A1-T1-B1 and O-A2-T2-B2, and T1T2
        edges = {(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (0, 4), (0, 5), (4, 5), (4, 6), (5, 6), (3, 6)}
        code, cedges, phi = to_canonical(7, edges)
        self.graph[code] = (7, cedges)
        self.spindle_code, self.spindle_phi = code, phi
        # the exact embedding, in Q(alpha), alpha = sqrt3 + sqrt11, alpha^4 = 28 alpha^2 - 64
        def mul(a, b):
            raw = [Fraction(0)] * 7
            for i, x in enumerate(a):
                for j, y in enumerate(b):
                    raw[i + j] += x * y
            for d in (6, 5, 4):
                c, raw[d] = raw[d], Fraction(0)
                raw[d - 2] += 28 * c
                raw[d - 4] -= 64 * c
            return raw[:4]

        def add(a, b, k=1):
            return [x + k * y for x, y in zip(a, b)]

        def const(q):
            return [Fraction(q), Fraction(0), Fraction(0), Fraction(0)]

        sq3 = [Fraction(0), Fraction(-5, 4), Fraction(0), Fraction(1, 16)]      # (alpha^3 - 20 alpha)/16
        sq11 = [Fraction(0), Fraction(9, 4), Fraction(0), Fraction(-1, 16)]     # (36 alpha - alpha^3)/16
        assert mul(sq3, sq3) == const(3) and mul(sq11, sq11) == const(11)
        half = const(Fraction(1, 2))
        cos, sin = const(Fraction(5, 6)), mul(sq11, const(Fraction(1, 6)))

        def rot(pt):
            x, y = pt
            return add(mul(x, cos), mul(y, sin), -1), add(mul(x, sin), mul(y, cos))

        O = (const(0), const(0))
        A1 = (mul(sq3, half), half)
        B1 = (mul(sq3, half), const(Fraction(-1, 2)))
        T1 = (sq3, const(0))
        pts = [O, A1, B1, T1, rot(A1), rot(B1), rot(T1)]
        for i, j in edges:
            dx, dy = add(pts[i][0], pts[j][0], -1), add(pts[i][1], pts[j][1], -1)
            assert add(mul(dx, dx), mul(dy, dy)) == const(1), (i, j)
        assert len({(tuple(p[0]), tuple(p[1])) for p in pts}) == 7

        def enc(el):
            return [int(z) if z.denominator == 1 else str(z) for z in el]

        coords = [None] * 7
        for i in range(7):
            coords[phi[i]] = [enc(pts[i][0]), enc(pts[i][1])]
        self.spindle_embedded = record(code, "embedded", {"field": {"minpoly": [64, 0, -28, 0, 1],
                                                                    "interval": [5, "51/10"]},
                                                          "coordinates": coords})
        o, a1, b1, t1 = (phi[i] for i in (0, 1, 2, 3))
        r = lambda verdict, cyc, co, s, pair, edge=None: record(code, verdict, rhombus_witness(
            verdict, cyc, co, s, pair, edge)[1])
        self.spindle_fakes = [
            ("refuted by a 'cycle' [O,A1,O,B1] that repeats O: all four of its pairs are edges and the identity "
             "holds EXACTLY (r(O,A1,T1,B1) - r(O,A1,O,B1) = -(e_O - e_T1))",
             r("refuted", [[o, a1, t1, b1], [o, a1, o, b1]], [1, -1], -1, [o, t1]), "repeats a vertex"),
            ("refuted by a 'cycle' [O,A1,B1,T1] whose closing pair T1-O is not an edge: the identity holds "
             "EXACTLY (r(O,A1,T1,B1) - r(O,A1,B1,T1) = 2(e_T1 - e_B1))",
             r("refuted", [[o, a1, t1, b1], [o, a1, b1, t1]], [1, -1], 2, [t1, b1]), "is not a 4-cycle of G"),
            ("tu: the rhombus's long diagonal O-T1 forced to the length of the edge A1-B1 (it is sqrt 3)",
             r("tu", [[o, a1, t1, b1]], [1], 1, [o, t1], [b1, a1]), "rule 6"),
            ("tu whose identity holds EXACTLY but whose 'forced' pair O-A1 is already an edge (a TU hit on an "
             "adjacent pair would prune a graph for nothing)",
             r("tu", [[o, a1, t1, b1]], [1], 1, [o, a1], [b1, t1]), "rule 4"),
            ("refuted with coefficient and scale 2^61-1, the prover's detection prime: the identity holds "
             "modulo 2^61-1 (both sides are 0 mod p) but not over the integers",
             r("refuted", [[o, a1, t1, b1]], [P61], P61, [o, t1]), "rule 6"),
            # zero targets: a cycle and its negation sum to 0, so the identity holds EXACTLY whenever the
            # target is 0; only s != 0, a != b and 'a tu pair is a non-edge' stand between these and a
            # refutation of a unit-distance graph
            ("refuted with scale 0 and a canceling pair of cycles: 0 = 0 * (e_O - e_T1) holds EXACTLY",
             r("refuted", [[o, a1, t1, b1], [o, a1, t1, b1]], [1, -1], 0, [o, t1]), "rule 3: scale is zero"),
            ("refuted with pair [O, O] and a canceling pair of cycles: 0 = e_O - e_O holds EXACTLY",
             r("refuted", [[o, a1, t1, b1], [o, a1, t1, b1]], [1, -1], 1, [o, o]), "not two distinct vertices"),
            ("tu whose pair IS its edge (A1-B1) with a canceling pair of cycles: the target is 0, the identity "
             "holds EXACTLY",
             r("tu", [[o, a1, t1, b1], [o, a1, t1, b1]], [1, -1], 1, [a1, b1], [a1, b1]), "rule 4"),
        ]
        for _, rec, _ in self.spindle_fakes:
            assert oracle(rec, 7, cedges) is False


# ---------------------------------------------------------------- in-process controls

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                                   # udcheck.py's dataclasses look it up
    spec.loader.exec_module(mod)
    return mod


def decoder_differential(udr, kernel, rng: random.Random, rounds: int) -> None:
    cases = ["", "?", "@", "A_", "A`", "A?", "B~", "~", "~?", "~??", "~???", "~~??@???", ">>graph6<<A_", "A_\n",
             "a", "DFw", "DF~", "DFw?", "DF", "~??D?Fw", "~??D?F~", "\x7f", "Aé", "~?@?" + "?" * 336]
    cases.append(g6_encode(64, {(i, i + 1) for i in range(63)}))
    cases.append(g6_encode(70, {(0, 69), (3, 5)}))
    for _ in range(rounds):
        n = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 10, 13, 17, 22, 23, 30, 62])
        p = rng.random()
        code = g6_encode(n, {(i, j) for j in range(n) for i in range(j) if rng.random() < p})
        cases.append(code)
        mutated = list(code)
        kind = rng.randrange(6)
        if kind == 0 and len(code) > 1:
            mutated[rng.randrange(len(code))] = chr(rng.randrange(32, 130))
        elif kind == 1:
            mutated = mutated[:-1]
        elif kind == 2:
            mutated.append(chr(rng.randrange(63, 127)))
        elif kind == 3 and len(code) > 1:                     # set a random bit of the last byte
            mutated[-1] = chr(63 + ((ord(code[-1]) - 63) | (1 << rng.randrange(6))))
        elif kind == 4 and n <= 62:                           # the long order header for a small n
            mutated = list("~" + "".join(chr(63 + ((n >> s) & 63)) for s in (12, 6, 0)) + code[1:])
        else:
            mutated[0] = chr(63 + rng.randrange(0, 64))
        cases.append("".join(mutated))
    disagreements = []
    for code in cases:
        try:
            g = kernel.decode_graph6(code)
            want = (g.n, frozenset(g.edges))
        except kernel.CheckError:
            want = "reject"
        try:
            n, bits, m = udr.decode_graph6(code)
            edges = frozenset((i, j) for j in range(n) for i in range(j) if bits[udr.pair_index(i, j)] == "1")
            got = (n, edges) if m == len(edges) else ("bad edge count", m, len(edges))
        except udr.CheckError:
            got = "reject"
        if got != want:
            disagreements.append((code, want if want == "reject" else want[0], got if got == "reject" else got[0]))
    accepted = sum(1 for code in cases if not isinstance(_safe(kernel, code), str))
    expect(f"in-process: decode_graph6 agrees with udcheck.py's decoder on {len(cases)} strings "
           f"({accepted} valid, {len(cases) - accepted} malformed)", not disagreements, str(disagreements[:3]))


def _safe(kernel, code):
    try:
        return kernel.decode_graph6(code)
    except kernel.CheckError:
        return "reject"


POOL = [0, 1, -1, 2, -2, 3, 4, 5, 6, 7, 10, 22, 23, True, False, 1.0, 0.0, -1.0, "1", "0", None, [], {}, [0, 1],
        [1, 2, 3, 4], BIG, -BIG, BIG - 1, -(BIG - 1), P61, 10 ** 30, -(10 ** 30)]


def mutate(rec: dict, n: int, edges: set, rng: random.Random) -> tuple[dict, set]:
    """One random change (a few of them keep the certificate valid).  Returns (record, edges)."""
    rh = rec["witness"]["rhombus"]
    kind = rng.randrange(25)
    val = rng.choice(POOL) if rng.random() < 0.6 else rng.randrange(-2, n + 2)
    cyc, co = rh["cycles"], rh["coefficients"]
    i = rng.randrange(len(cyc))
    if kind == 0:
        cyc[i][rng.randrange(4)] = val
    elif kind == 1:
        co[i] = val
    elif kind == 2:
        rh["scale"] = val
    elif kind == 3:
        rh["pair"][rng.randrange(2)] = val
    elif kind == 4 and "edge" in rh:
        rh["edge"][rng.randrange(2)] = val
    elif kind == 5:
        del rh[rng.choice(sorted(rh))]
    elif kind == 6:
        rh[rng.choice(["edge", "note", "Scale", "pair2"])] = [0, 1]
    elif kind == 7:
        rh["pair"].reverse()
    elif kind == 8:                                                     # valid: rotate one, negate its l
        cyc[i] = cyc[i][1:] + cyc[i][:1]
        co[i] = -co[i]
    elif kind == 9:                                                     # invalid unless it cancels
        cyc[i] = cyc[i][1:] + cyc[i][:1]
    elif kind == 10:                                                    # valid: reversed cycle
        cyc[i] = [cyc[i][0], cyc[i][3], cyc[i][2], cyc[i][1]]
    elif kind == 11:
        del cyc[i]
        del co[i]
    elif kind == 12:
        del co[i]
    elif kind == 13:                                                    # valid: split a coefficient
        l1 = rng.choice([1, -1, 2, 5])
        if co[i] - l1:
            cyc.append(list(cyc[i]))
            co.append(l1)
            co[i] -= l1
    elif kind == 14:                                                    # valid: scale everything
        k = rng.choice([2, -1, 3, 7])
        rh["coefficients"] = [k * z for z in co]
        rh["scale"] *= k
    elif kind == 15:
        rec["verdict"] = rng.choice(["forbidden", "tu", "embedded", "refuted", "unknown"])
    elif kind == 16:
        rec["witness"][rng.choice(["index", "map", "pair", "Rhombus"])] = 0
    elif kind == 24:                                                    # no longer a rhombus record
        rec["witness"] = {"Rhombus" if rng.random() < 0.5 else "rhombus ": rec["witness"]["rhombus"]}
    elif kind == 17:                                                    # the graph loses an edge
        if edges:
            edges = set(edges)
            edges.discard(rng.choice(sorted(edges)))
    elif kind == 18:                                                    # the graph gains an edge
        non = [(a, b) for b in range(n) for a in range(b) if (a, b) not in edges]
        if non:
            edges = set(edges) | {rng.choice(non)}
    elif kind == 19:
        rh["pair"], rh["scale"] = rh["pair"][::-1], -rh["scale"]        # valid
    elif kind == 20 and "edge" in rh:
        rh["pair"], rh["edge"] = rh["edge"][::-1], rh["pair"][::-1]     # same identity; pair adjacent
    elif kind == 21:
        cyc[i] = [rng.randrange(n) for _ in range(4)]
    elif kind == 22:
        rh["cycles"] = cyc * 2
        rh["coefficients"] = co + [-z for z in co] if rng.random() < 0.5 else co * 2
    else:
        rh["coefficients"] = [z if j != i else z + rng.choice([1, -1]) for j, z in enumerate(co)]
    return rec, edges


def shifted(rec: dict, n: int, edges: set, n_big: int, offset: int) -> tuple[dict, set]:
    """The same certificate on the graph moved to vertices offset.. of an n_big-vertex graph."""
    rec = copy.deepcopy(rec)
    rh = rec["witness"]["rhombus"]
    rh["cycles"] = [[v + offset for v in c] for c in rh["cycles"]]
    for key in ("pair", "edge"):
        if key in rh:
            rh[key] = [v + offset for v in rh[key]]
    big = {(i + offset, j + offset) for i, j in edges}
    rec["g6"] = g6_encode(n_big, big)
    return rec, big


def fuzz_against_oracle(udr, fx: Fixtures, rng: random.Random, rounds: int) -> None:
    for base, n_big, offset in ((fx.k23, 90, 64), (fx.gadgets[0], 90, 60), (fx.random[0], 90, 70),
                                (fx.k23, 300, 270), (fx.gadgets[1], 300, 280)):
        rec, big = shifted(base, *fx.graph[base["g6"]], n_big, offset)
        fx.graph[rec["g6"]] = (n_big, big)
        fx.big.append(rec)
    bases = [fx.k23, *fx.gadgets, *fx.random, *fx.big]
    # the fast pass must take every valid certificate whose vertices are below 257, and hand the others over
    handed = []
    for rec in bases:
        n, edges = fx.graph[rec["g6"]]
        rh = rec["witness"]["rhombus"]
        _, bits, _ = udr.decode_graph6(rec["g6"])
        P = udr._P64 if n <= 64 else udr._PairRows(n)
        fast = udr._cycles_fast(rh["cycles"], rh["coefficients"], n, bits, P)
        if (fast is None) != (max(max(c) for c in rh["cycles"]) >= 257):
            handed.append(rec["g6"][:12])
    expect(f"in-process: the fast pass accepts each of the {len(bases)} valid base certificates with vertices "
           f"below 257 and hands the two with larger vertices to the exact pass", not handed, str(handed))
    tally = {"valid": 0, "invalid": 0, "kernel": 0}
    disagreements, fast_vs_exact, fast_taken = [], [], 0
    for _ in range(rounds):
        base = rng.choice(bases)
        n, edges = fx.graph[base["g6"]]
        rec, medges = mutate(copy.deepcopy(base), n, edges, rng)
        code = g6_encode(n, medges)
        want = {None: "kernel", True: "valid", False: "invalid"}[oracle(rec, n, medges)]
        _, bits, _ = udr.decode_graph6(code)
        try:
            got = "valid" if udr.rhombus_record(rec, n, bits) else "kernel"
        except udr.CheckError:
            got = "invalid"
        tally[want] += 1
        if got != want:
            disagreements.append((want, got, json.dumps(rec)[:200]))
        # whenever the fast pass returns a sum, the exact pass must return the same sum without objecting
        rh = (rec.get("witness") or {}).get("rhombus")
        if isinstance(rh, dict) and isinstance(rh.get("cycles"), list) and isinstance(rh.get("coefficients"), list) \
                and len(rh["cycles"]) == len(rh["coefficients"]):
            P = udr._P64 if n <= 64 else udr._PairRows(n)
            fast = udr._cycles_fast(rh["cycles"], rh["coefficients"], n, bits, P)
            if fast is not None:
                fast_taken += 1
                try:
                    exact = udr._cycles_exact(rh["cycles"], rh["coefficients"], n, bits, P)
                except udr.CheckError as exc:
                    exact = f"CheckError: {exc}"
                if exact != fast:
                    fast_vs_exact.append((str(exact)[:80], json.dumps(rh)[:160]))
    expect(f"in-process: the checker agrees with the oracle on {rounds} random single mutations "
           f"({tally['valid']} still valid, {tally['invalid']} invalid, {tally['kernel']} no longer rhombus)",
           not disagreements and tally["valid"] > rounds // 20 and tally["invalid"] > rounds // 3,
           str(disagreements[:3]))
    expect(f"in-process: on the {fast_taken} mutations the fast pass took, the exact pass returns the same sum "
           f"and objects to nothing", not fast_vs_exact and fast_taken > rounds // 10, str(fast_vs_exact[:3]))


# ---------------------------------------------------------------- the command-line controls

def mutated(base: dict, change) -> dict:
    rec = copy.deepcopy(base)
    change(rec, rec["witness"]["rhombus"] if isinstance(rec.get("witness"), dict) and
           isinstance(rec["witness"].get("rhombus"), dict) else None)
    return rec


def pad(rec: dict, total: int, coefficient: int = 3) -> dict:
    """Add canceling copies of the first cycle (l and then -l) and, if needed for parity, one triple,
    until there are `total` cycles; the identity is unchanged."""
    rec = copy.deepcopy(rec)
    rh = rec["witness"]["rhombus"]
    c = rh["cycles"][0]
    while len(rh["cycles"]) < total:
        left = total - len(rh["cycles"])
        if left == 3 or left == 1:
            if left == 1:
                raise ValueError("cannot pad by exactly one")
            rh["cycles"] += [list(c), list(c), c[2:] + c[:2]]
            rh["coefficients"] += [2 * coefficient, -coefficient, -coefficient]
        else:
            rh["cycles"] += [list(c), c[2:] + c[:2]]
            rh["coefficients"] += [coefficient, -coefficient]
    return rec


def int64_wrap(rec: dict) -> dict:
    """The certificate plus 2^64 r(C): exact sums differ from the target, sums modulo 2^64 do not."""
    rec = copy.deepcopy(rec)
    rh = rec["witness"]["rhombus"]
    c = rh["cycles"][0]
    rh["cycles"] += [list(c) for _ in range(5)]
    rh["coefficients"] += [BIG - 1] * 4 + [4]
    return rec


def running_sums(rec: dict) -> dict:
    """The certificate plus three copies of one cycle with 2^62-1 and three with -(2^62-1): valid, and the
    running sums pass 2^63 before they come back."""
    rec = copy.deepcopy(rec)
    rh = rec["witness"]["rhombus"]
    c = rh["cycles"][0]
    rh["cycles"] += [list(c) for _ in range(6)]
    rh["coefficients"] += [BIG - 1] * 3 + [-(BIG - 1)] * 3
    return rec


def sums(rec: dict, n: int) -> tuple[list[int], int]:
    """(sum_j l_j r(C_j) - s * target, the largest absolute running entry), exactly."""
    rh = rec["witness"]["rhombus"]
    vec, peak = [0] * n, 0
    for c, l in zip(rh["cycles"], rh["coefficients"]):
        for sign, z in zip((1, -1, 1, -1), c):
            vec[z] += sign * l
            peak = max(peak, abs(vec[z]))
    a, b = rh["pair"]
    vec[a] -= rh["scale"]
    vec[b] += rh["scale"]
    if "edge" in rh:
        vec[rh["edge"][0]] += rh["scale"]
        vec[rh["edge"][1]] -= rh["scale"]
    return vec, peak


def rhombus_red_controls(fx: Fixtures, fset: int) -> int:
    k23, g0 = fx.k23, fx.gadgets[0]
    n23, e23 = fx.graph[k23["g6"]]
    rk = k23["witness"]["rhombus"]
    # K2,3's canonical labels: hubs are the two vertices of degree 3
    adj = adjacency(n23, e23)
    hubs = [v for v in range(n23) if len(adj[v]) == 3]
    leaves = [v for v in range(n23) if len(adj[v]) == 2]
    h1, h2 = hubs
    x, y, z = leaves
    rg = g0["witness"]["rhombus"]
    n0, e0 = fx.graph[g0["g6"]]
    a, b = rg["pair"]
    p, q = rg["edge"]
    non_edge_of_g0 = next((u, v) for v in range(n0) for u in range(v) if (u, v) not in e0 and {u, v} != {a, b})
    S = f"[set {fset}] "

    cases = [
        # rule 1
        ("rule 1: witness with an extra key beside rhombus", "rule 1: the witness has exactly the key 'rhombus'",
         mutated(k23, lambda r, rh: r["witness"].update(index=0))),
        ("rule 1: rhombus object with an extra key", "rule 1: a refuted rhombus witness has exactly the keys",
         mutated(k23, lambda r, rh: rh.update(note=1))),
        ("rule 1: rhombus object missing 'scale'", "missing ['scale']",
         mutated(k23, lambda r, rh: rh.pop("scale"))),
        ("rule 1: verdict refuted carrying an 'edge'", "extra ['edge']",
         mutated(k23, lambda r, rh: rh.update(edge=[h1, x]))),
        ("rule 1: verdict tu without an 'edge'", "rule 1: a tu rhombus witness has exactly the keys",
         mutated(g0, lambda r, rh: rh.pop("edge"))),
        ("rule 1: rhombus is a list, not an object", "rule 1: the rhombus witness must be an object",
         mutated(k23, lambda r, rh: r["witness"].update(rhombus=[rk]))),
        # rule 2
        ("rule 2: empty cycle list", "rule 2: cycles must be a non-empty list",
         mutated(k23, lambda r, rh: (rh.update(cycles=[], coefficients=[])))),
        ("rule 2: 4097 cycles (identity intact)", "rule 2: 4097 cycles, more than 4096", pad(k23, 4097)),
        ("rule 2: a cycle of three vertices", "is not a list of four vertices",
         mutated(k23, lambda r, rh: rh["cycles"][1].pop())),
        ("rule 2: a cycle vertex equal to n", "has a vertex outside [0, 5)",
         mutated(k23, lambda r, rh: rh["cycles"][0].__setitem__(0, n23))),
        ("rule 2: a cycle vertex -1", "has a vertex outside [0, 5)",
         mutated(k23, lambda r, rh: rh["cycles"][0].__setitem__(2, -1))),
        ("rule 2: a cycle vertex true (a boolean)", "has a vertex that is not a JSON integer",
         mutated(k23, lambda r, rh: rh["cycles"][0].__setitem__(0, True))),
        ("rule 2: a cycle vertex 1.0 (a float)", "has a vertex that is not a JSON integer",
         mutated(k23, lambda r, rh: rh["cycles"][1].__setitem__(1, float(rh["cycles"][1][1])))),
        ("rule 2: a cycle vertex \"1\" (a string)", "has a vertex that is not a JSON integer",
         mutated(k23, lambda r, rh: rh["cycles"][1].__setitem__(3, str(rh["cycles"][1][3])))),
        ("rule 2: repeated cycle vertex at opposite corners (all four pairs are edges)", "repeats a vertex",
         mutated(k23, lambda r, rh: rh.update(cycles=[[x, h1, x, h2], rh["cycles"][1]]))),
        ("rule 2: repeated cycle vertex at adjacent corners", "repeats a vertex",
         mutated(k23, lambda r, rh: rh.update(cycles=[[x, x, y, h2], rh["cycles"][1]]))),
        ("rule 2: a cycle with an edge missing (x-y and h1-h2 are not edges)", "is not a 4-cycle of G",
         mutated(k23, lambda r, rh: rh.update(cycles=[[x, y, h1, h2], rh["cycles"][1]]))),
        # rule 3
        ("rule 3: coefficient true (a boolean)", "coefficients[0] is not a JSON integer",
         mutated(k23, lambda r, rh: rh["coefficients"].__setitem__(0, True))),
        ("rule 3: coefficient 1.0 (a float)", "coefficients[0] is not a JSON integer",
         mutated(k23, lambda r, rh: rh["coefficients"].__setitem__(0, float(rh["coefficients"][0])))),
        ("rule 3: coefficient \"-1\" (a string)", "coefficients[1] is not a JSON integer",
         mutated(k23, lambda r, rh: rh["coefficients"].__setitem__(1, str(rh["coefficients"][1])))),
        ("rule 3: a zero coefficient (on an extra cycle, identity intact)", "coefficients[2] is zero",
         mutated(k23, lambda r, rh: (rh["cycles"].append(rh["cycles"][0]), rh["coefficients"].append(0)))),
        ("rule 3: a coefficient of 2^62 (in a canceling pair, identity intact)",
         "coefficients[2] has absolute value 2^62 or more", pad(k23, 4, coefficient=BIG)),
        ("rule 3: a coefficient of -2^62 (in a canceling pair, identity intact)",
         "coefficients[2] has absolute value 2^62 or more", pad(k23, 4, coefficient=-BIG)),
        ("rule 3: one coefficient more than cycles", "rule 3: 3 coefficients for 2 cycles",
         mutated(k23, lambda r, rh: rh["coefficients"].append(1))),
        ("rule 3: coefficients is an object", "rule 3: coefficients must be a list",
         mutated(k23, lambda r, rh: rh.update(coefficients={"0": 1}))),
        ("rule 3: scale 0", "rule 3: scale is zero", mutated(k23, lambda r, rh: rh.update(scale=0))),
        ("rule 3: scale true, which would satisfy the identity if read as 1", "rule 3: scale must be a JSON integer",
         mutated(k23, lambda r, rh: rh.update(scale=True))),
        ("rule 3: scale 1.0 (a float)", "rule 3: scale must be a JSON integer",
         mutated(k23, lambda r, rh: rh.update(scale=float(rh["scale"])))),
        ("rule 3: scale 2^62 with every coefficient 2^61 (identity intact)",
         "rule 3: scale has absolute value 2^62 or more",
         mutated(k23, lambda r, rh: rh.update(cycles=[rh["cycles"][0]] * 2 + [rh["cycles"][1]] * 2,
                                              coefficients=[z << 61 for z in (rh["coefficients"][0],) * 2 +
                                                            (rh["coefficients"][1],) * 2],
                                              scale=rh["scale"] << 62))),
        # rule 4
        ("rule 4: pair with a == b", "is not two distinct vertices",
         mutated(k23, lambda r, rh: rh.update(pair=[rh["pair"][0]] * 2))),
        ("rule 4: pair vertex out of range", "rule 4: pair [0, 5] has a vertex outside",
         mutated(k23, lambda r, rh: rh.update(pair=[0, 5]))),
        ("rule 4: pair of three vertices", "rule 4: pair must be a list of two",
         mutated(k23, lambda r, rh: rh.update(pair=rh["pair"] + [h1]))),
        ("rule 4: pair with a boolean", "rule 4: pair must be two JSON integers",
         mutated(k23, lambda r, rh: rh.update(pair=[rh["pair"][0], False]))),
        ("rule 4: tu pair adjacent (pair and edge swapped: the same identity, exactly)",
         "rule 4: pair", mutated(g0, lambda r, rh: rh.update(pair=[q, p], edge=[b, a]))),
        # rule 5
        ("rule 5: tu 'edge' that is not an edge", "rule 5: edge",
         mutated(g0, lambda r, rh: rh.update(edge=list(non_edge_of_g0)))),
        ("rule 5: tu edge with p == q", "rule 5: edge",
         mutated(g0, lambda r, rh: rh.update(edge=[p, p]))),
        ("rule 5: tu edge vertex out of range", "has a vertex outside",
         mutated(g0, lambda r, rh: rh.update(edge=[p, n0]))),
        # rule 6
        ("rule 6: one coefficient off by one", "rule 6",
         mutated(k23, lambda r, rh: rh["coefficients"].__setitem__(0, rh["coefficients"][0] + 1))),
        ("rule 6: wrong scale (doubled)", "rule 6", mutated(k23, lambda r, rh: rh.update(scale=2 * rh["scale"]))),
        ("rule 6: pair moved to another vertex", "rule 6",
         mutated(k23, lambda r, rh: rh.update(pair=[rh["pair"][0], next(v for v in (x, y, z)
                                                                         if v not in rh["pair"])]))),
        ("rule 6: pair reversed without negating s", "rule 6",
         mutated(k23, lambda r, rh: rh["pair"].reverse())),
        ("rule 6: a cycle rotated by one place without negating its coefficient", "rule 6",
         mutated(k23, lambda r, rh: rh["cycles"].__setitem__(0, rh["cycles"][0][1:] + rh["cycles"][0][:1]))),
        ("rule 6: a cycle replaced by another genuine 4-cycle of G", "rule 6",
         mutated(k23, lambda r, rh: rh["cycles"].__setitem__(0, [x, h1, z, h2]
                                                             if sorted(rh["cycles"][0]) != sorted([x, h1, z, h2])
                                                             else [y, h1, z, h2]))),
        ("rule 6: tu edge reversed without negating s", "rule 6",
         mutated(g0, lambda r, rh: rh["edge"].reverse())),
        ("rule 6: identity true modulo 2^61-1 only (coefficient and scale 2^61-1)", "rule 6",
         mutated(k23, lambda r, rh: rh.update(cycles=rh["cycles"][:1], coefficients=[P61], scale=P61))),
        ("rule 6, binding control 'an int64 checker': five more copies of one cycle with coefficients 2^62-1 "
         "(four times) and 4, each below 2^62, add 2^64 r(C); the sums pass 2^63 and a wrapping 64-bit sum "
         "sees the identity", "rule 6", int64_wrap(k23)),
        # verdicts
        ("verdict unknown with a rhombus witness", "never carries a rhombus witness",
         mutated(k23, lambda r, rh: r.update(verdict="unknown"))),
        ("verdict embedded with a rhombus witness", "never carries a rhombus witness",
         mutated(k23, lambda r, rh: r.update(verdict="embedded"))),
        ("verdict forbidden with a rhombus witness", "never carries a rhombus witness",
         mutated(k23, lambda r, rh: r.update(verdict="forbidden"))),
        ("verdict refuted with a tu-shaped witness", "extra ['edge']",
         mutated(g0, lambda r, rh: r.update(verdict="refuted"))),
    ]
    wrapped = int64_wrap(k23)
    diff, peak = sums(wrapped, n23)
    expect(S + "premise of the int64 control: its exact sums miss the target, its sums modulo 2^64 hit it, and "
           "a running sum passes 2^63", any(diff) and all(z % (1 << 64) == 0 for z in diff) and peak > 1 << 63,
           f"difference {[z for z in diff if z][:2]}, peak {peak} > 2^63 = {1 << 63}")
    for name, needle, rec in cases:
        n, edges = fx.graph[rec["g6"]]
        assert oracle(rec, n, edges) is False, name
        reject(S + name, needle, [rec], fset=fset)
    return len(cases)


def raw_line_controls(fx: Fixtures, fset: int) -> int:
    k23 = fx.k23
    line = json.dumps(k23, separators=(",", ":"))
    S = f"[set {fset}] "
    rk = k23["witness"]["rhombus"]
    cases = [
        ("JSON: duplicate key 'scale' inside rhombus", "duplicate key 'scale'",
         line.replace('"scale":', '"scale":%d,"scale":' % rk["scale"], 1)),
        ("JSON: NaN as a coefficient", "invalid JSON",
         line.replace('"coefficients":[', '"coefficients":[NaN,', 1).replace('"cycles":[', '"cycles":[%s,'
                                                                                  % json.dumps(rk["cycles"][0]), 1)),
        ("JSON: a 5000-digit coefficient", "invalid JSON",
         line.replace('"coefficients":[', '"coefficients":[%s,' % ("7" * 5000), 1)
             .replace('"cycles":[', '"cycles":[%s,' % json.dumps(rk["cycles"][0]), 1)),
        ("JSON: truncated record", "invalid JSON", line[:-7]),
        ("JSON: top-level extra key", "exactly the keys g6, verdict", line[:-1] + ',"note":1}'),
        ("JSON: verdict 'pass' (the prover's stdout verdict)", "unsupported verdict 'pass'",
         line.replace('"verdict":"refuted"', '"verdict":"pass"')),
    ]
    for name, needle, text in cases:
        reject(S + name, needle, raw=(text + "\n").encode(), graphs=[k23["g6"]], unknown=None, fset=fset)
    reject(S + "file: last record without its final newline", "missing final newline",
           raw=line.encode(), graphs=[k23["g6"]], unknown=None, fset=fset)
    reject(S + "file: a blank line", "blank certificate record",
           raw=(line + "\n\n" + json.dumps(fx.gadgets[0], separators=(",", ":")) + "\n").encode(),
           graphs=None, unknown=None, fset=fset)
    reject(S + "file: a byte that is not UTF-8", "not UTF-8", raw=(line + "\n").encode() + b"\xff\n",
           graphs=None, unknown=None, fset=fset)
    return len(cases) + 3


def one_per_graph(records: list[dict]) -> list[dict]:
    """A certificate file holds each graph once: gadgets 3 and 4 of tu-gadgets.json are the same graph
    with different pairs, so a file takes the first of them."""
    return list({r["g6"]: r for r in reversed(records)}.values())[::-1]


def mixed_records(fx: Fixtures, fset: int, rng: random.Random) -> list[dict]:
    recs = one_per_graph([fx.k23, *fx.gadgets, *fx.random, fx.kernel_tu, fx.forbidden0, fx.spindle_embedded,
                          *fx.unknowns])
    if fset == 398:
        recs.append(fx.forbidden74)
    rng.shuffle(recs)
    return recs


def cli_controls(fx: Fixtures, fset: int) -> None:
    S = f"[set {fset}] "
    rng = random.Random(1000 + fset)
    k23, g0 = fx.k23, fx.gadgets[0]
    # green: single certificates
    accept(S + "K2,3 refuted by rhombus (with --graphs, no UNKNOWN.g6)", [k23],
           accept_line(records=1, refuted=1, rhombus_refuted=1), fset=fset)
    for i, rec in enumerate(fx.gadgets):
        accept(S + f"gadget {i}: tu on its distinguished pair {rec['witness']['rhombus']['pair']} via edge "
               f"{rec['witness']['rhombus']['edge']}, {len(rec['witness']['rhombus']['cycles'])} cycles",
               [rec], accept_line(records=1, tu=1, rhombus_tu=1), fset=fset)
    every = one_per_graph([k23, *fx.gadgets, *fx.random])
    accept(S + f"K2,3, the gadgets (3 and 4 are one graph) and the random graphs: {len(every)} records in one "
           f"all-rhombus file", every, expected_line(every), fset=fset)
    accept(S + "all-rhombus file beside an EMPTY UNKNOWN.g6", [k23, g0], expected_line([k23, g0]),
           unknown=[], fset=fset)
    accept(S + "all-rhombus file without --graphs", [k23, g0], expected_line([k23, g0]), graphs=None, fset=fset)
    # green: boundaries and rewritings that keep a certificate valid
    top = BIG - 1
    variants = [
        ("coefficients +-(2^62-1) and scale 2^62-1",
         mutated(k23, lambda r, rh: rh.update(coefficients=[z * top for z in rh["coefficients"]],
                                              scale=rh["scale"] * top))),
        ("exactly 4096 cycles", pad(k23, 4096)),
        ("pair reversed and s negated", mutated(k23, lambda r, rh: rh.update(pair=rh["pair"][::-1],
                                                                                scale=-rh["scale"]))),
        ("a cycle rotated by one with its coefficient negated",
         mutated(k23, lambda r, rh: (rh["cycles"].__setitem__(0, rh["cycles"][0][1:] + rh["cycles"][0][:1]),
                                     rh["coefficients"].__setitem__(0, -rh["coefficients"][0])))),
        ("a cycle traversed backwards (same row)",
         mutated(k23, lambda r, rh: rh["cycles"].__setitem__(0, [rh["cycles"][0][0]] + rh["cycles"][0][:0:-1]))),
        ("a coefficient split over a repeated cycle",
         mutated(k23, lambda r, rh: (rh["cycles"].append(list(rh["cycles"][0])),
                                     rh["coefficients"].append(3),
                                     rh["coefficients"].__setitem__(0, rh["coefficients"][0] - 3)))),
        ("tu with pair and edge both reversed and s negated",
         mutated(g0, lambda r, rh: rh.update(pair=rh["pair"][::-1], edge=rh["edge"][::-1], scale=-rh["scale"]))),
        ("running sums pass 2^63 and come back (three coefficients 2^62-1 on one cycle, three -(2^62-1))",
         running_sums(k23)),
        *[("pair and edge share a vertex, " + name, rec) for name, rec in fx.overlaps],
    ]
    for name, rec in variants:
        n, edges = fx.graph[rec["g6"]]
        assert oracle(rec, n, edges) is True, name
        accept(S + "boundary/rewrite: " + name, [rec], expected_line([rec]), fset=fset)
    spaced = json.dumps(k23, sort_keys=True, separators=(" , ", " :  ")) + "  \n" + \
        json.dumps(g0, indent=None) + "\n"
    accept(S + "other JSON spellings (spaces, sorted keys)", raw=spaced.encode(), graphs=[k23["g6"], g0["g6"]],
           unknown=None, line=expected_line([k23, g0]), fset=fset)
    accept(S + "CRLF line ends (udcheck.py reads them too)", raw=dump([k23, g0]).replace("\n", "\r\n").encode(),
           graphs=[k23["g6"], g0["g6"]], unknown=None, line=expected_line([k23, g0]), fset=fset)

    # green: a mixed file
    mixed = mixed_records(fx, fset, rng)
    kinds = {}
    for r in mixed:
        kind = r["verdict"] + ("/rhombus" if "rhombus" in (r.get("witness") or {}) else "")
        kinds[kind] = kinds.get(kind, 0) + 1
    out = accept(S + f"mixed file {kinds}", mixed, expected_line(mixed), fset=fset)
    want_unknown = [f"UNKNOWN {r['g6']}" for r in mixed if r["verdict"] == "unknown"]
    expect(S + "mixed file: the UNKNOWN lines are the unknown records in order",
           out.splitlines()[1:] == want_unknown, str(out.splitlines()[1:]))
    accept(S + "mixed file without --graphs", mixed, expected_line(mixed), graphs=None, fset=fset)
    accept(S + "mixed file with --work-dir", mixed, expected_line(mixed), extra=["--work-dir", "{tmp}"], fset=fset)
    # green: no rhombus record -> exactly the kernel's counts
    plain = [r for r in mixed if "rhombus" not in (r.get("witness") or {})]
    kernel = UDCHECK398 if fset == 398 else UDCHECK
    rc_k, out_k, err_k = _run_kernel(kernel, plain)
    rc_r, out_r, err_r = run_cli(plain, fset=fset)
    k_lines, r_lines = out_k.splitlines(), out_r.splitlines()
    same = (rc_k == 0 and rc_r == 0 and
            r_lines[0] == k_lines[0] + " rhombus_tu=0 rhombus_refuted=0 tri_tu=0 tri_refuted=0"
            and r_lines[1:] == k_lines[1:])
    expect(S + f"no rhombus record: the counts are {kernel.name}'s own", same,
           f"{kernel.name}: {k_lines[:1]} / checker: {r_lines[:1]} {err_k.strip()[:200]} {err_r.strip()[:200]}")

    # red: file level
    graphs = [r["g6"] for r in mixed]
    stranger = canonical([g6_encode(9, {(i, i + 1) for i in range(8)})])[0]
    reject(S + "--graphs: one line differs", "must equal the graph list exactly", mixed,
           graphs=graphs[:3] + [stranger] + graphs[4:], fset=fset)
    reject(S + "--graphs: two lines swapped", "must equal the graph list exactly", mixed,
           graphs=graphs[:1] + [graphs[2], graphs[1]] + graphs[3:], fset=fset)
    reject(S + "--graphs: one line too many", f"{len(mixed)} records, {len(mixed) + 1} listed graphs", mixed,
           graphs=graphs + [stranger], fset=fset)
    reject(S + "--graphs: one line too few", "must equal the graph list exactly", mixed, graphs=graphs[:-1],
           fset=fset)
    reject(S + "duplicate rhombus record", "duplicate graph6 record", [k23, g0, k23], fset=fset)
    reject(S + "duplicate across kinds: a rhombus record and an unknown record of the same graph",
           "duplicate graph6 record", [k23, record(k23["g6"], "unknown")], unknown=[k23["g6"]], fset=fset)
    # a non-canonical rhombus record: relabel the graph and the certificate together
    n, edges = fx.graph[g0["g6"]]
    perm, _ = noncanonical(n, edges, rng)
    rh = copy.deepcopy(g0["witness"]["rhombus"])
    rh["cycles"] = [[perm[v] for v in c] for c in rh["cycles"]]
    rh["pair"] = [perm[v] for v in rh["pair"]]
    rh["edge"] = [perm[v] for v in rh["edge"]]
    pedges = {(min(perm[i], perm[j]), max(perm[i], perm[j])) for i, j in edges}
    noncanon = record(g6_encode(n, pedges), "tu", {"rhombus": rh})
    assert noncanon["g6"] != g0["g6"] and oracle(noncanon, n, pedges) is True
    reject(S + "a rhombus record whose graph6 is not canonical (certificate relabelled with it, so valid)",
           "is not nauty-labelg canonical", [k23, noncanon], fset=fset)
    un = fx.unknowns[0]
    _, un_nc = noncanonical(*fx.graph[un["g6"]], rng)
    reject(S + "a kernel (unknown) record whose graph6 is not canonical", "rejected the records handed to it",
           [k23, record(un_nc, "unknown")], fset=fset)
    bad_tu = copy.deepcopy(fx.kernel_tu)
    bad_tu["witness"]["pair"] = [bad_tu["witness"]["map"][0], bad_tu["witness"]["map"][1]]
    reject(S + "a bad kernel tu record (pair not the mapped gadget pair) inside the mixed file",
           "rejected the records handed to it", [bad_tu if r is fx.kernel_tu else r for r in mixed], fset=fset)
    if fset == 74:
        reject(S + "a forbidden record citing member 74 under set 74 (inside a mixed file)", "out of range",
               mixed + [fx.forbidden74], fset=fset)
    reject(S + "stale UNKNOWN.g6 beside an all-rhombus file", "UNKNOWN.g6 does not exactly list", [k23, g0],
           unknown=[fx.unknowns[0]["g6"]], fset=fset)
    reject(S + "UNKNOWN.g6 missing although the file has unknown records", "cannot read graph list", mixed,
           unknown=None, fset=fset)
    reject(S + "UNKNOWN.g6 in the wrong order", "UNKNOWN.g6 does not exactly list", mixed,
           unknown=[r["g6"] for r in mixed if r["verdict"] == "unknown"][::-1], fset=fset)
    n0, e0 = fx.graph[g0["g6"]]
    reject(S + "--expect-n differs from a rhombus record's order", f"expected {n0 + 1} vertices, got {n0}", [g0],
           size=(n0 + 1, len(e0)), fset=fset)
    reject(S + "--expect-m differs from a rhombus record's size", f"expected {len(e0) - 1} edges, got {len(e0)}",
           [g0], size=(n0, len(e0) - 1), fset=fset)
    accept(S + "--expect-n/--expect-m equal to the record's order and size", [g0], expected_line([g0]),
           size=(n0, len(e0)), fset=fset)
    reject(S + "--manifest-dir with no manifests (passed through to the kernel)", "contains no JSON manifests",
           [k23], extra=["--manifest-dir", "{tmp}/nothing"], fset=fset)
    reject(S + "--labelg that cannot run (an all-rhombus file: the canonical check is this checker's own)",
           "could not run", [k23, g0], extra=["--labelg", "{tmp}/no-such-labelg"], fset=fset)
    # --unknown-file elsewhere, as prune.py passes it; a stale UNKNOWN.g6 beside the file must not matter
    unknown_list = [r["g6"] for r in mixed if r["verdict"] == "unknown"]
    accept(S + "mixed file, --unknown-file elsewhere, and a STALE UNKNOWN.g6 beside the certificates (ignored)",
           mixed, expected_line(mixed), unknown=unknown_list, unknown_at="chunks/c0.UNKNOWN.g6",
           beside=[k23["g6"]], fset=fset)
    reject(S + "--unknown-file elsewhere listing the unknowns in the wrong order", "UNKNOWN.g6 does not exactly list",
           mixed, unknown=unknown_list[::-1], unknown_at="chunks/c0.UNKNOWN.g6", beside=unknown_list, fset=fset)
    accept(S + "all-rhombus file, an EMPTY --unknown-file elsewhere (prune.py's chunk files) and a stale one beside",
           [k23, g0], expected_line([k23, g0]), unknown=[], unknown_at="chunks/c1.UNKNOWN.g6",
           beside=unknown_list, fset=fset)
    # a 70-vertex graph: the long graph6 header and the pair rows computed on demand
    big_code, big_edges, _ = to_canonical(70, {(a + 61, b + 61) for a in (0, 1) for b in (2, 3, 4)})
    found = TestProver(70, big_edges).find()
    big = rhombus_rec(big_code, found)
    assert big_code.startswith("~") and oracle(big, 70, big_edges) is True
    accept(S + "K2,3 inside a 70-vertex graph (long graph6 header)", [big], expected_line([big]), fset=fset)
    isolated = next(v for v in range(70) if all(v not in e for e in big_edges))
    reject(S + "the same with a cycle vertex moved to an isolated vertex", "is not a 4-cycle of G",
           [mutated(big, lambda r, rh: rh["cycles"][0].__setitem__(0, isolated))], fset=fset)
    prune_style_replay(fx, fset)


def prune_style_replay(fx: Fixtures, fset: int) -> None:
    """prune.py's run_checker: consecutive chunks, each with its own graph list and (possibly empty) unknown
    list, the exact flags of udcheck_once (--expect-n --expect-m --graphs --unknown-file), counts summed."""
    S = f"[set {fset}] "
    recs, _ = _GP10[0] if _GP10 else (None, None)
    if recs is None:
        _GP10.append(gp10_records())
        recs, _ = _GP10[0]
    by_m: dict[int, list] = {}
    for r in recs:
        by_m.setdefault(len(g6_decode(r["g6"])[1]), []).append(r)
    m, cell = max(by_m.items(), key=lambda kv: (len(kv[1]), kv[0]))
    totals: dict[str, int] = {}
    chunks = 0
    with tempfile.TemporaryDirectory(prefix="st-rhombus-prune-") as tmp:
        tmp = Path(tmp)
        for lo in range(0, len(cell), 7):
            part = cell[lo:lo + 7]
            certs, graphs, unknown = tmp / f"chunk-{lo:09d}.certs.jsonl", tmp / f"chunk-{lo:09d}.g6", \
                tmp / f"chunk-{lo:09d}.UNKNOWN.g6"
            certs.write_text(dump(part))
            graphs.write_text("".join(r["g6"] + "\n" for r in part))
            unknown.write_text("".join(r["g6"] + "\n" for r in part if r["verdict"] == "unknown"))
            p = subprocess.run([str(PYTHON), str(CHECKER), "--forbidden-set", str(fset), "--expect-n", "10",
                                "--expect-m", str(m), "--graphs", str(graphs), "--unknown-file", str(unknown),
                                str(certs)], capture_output=True, text=True, timeout=900)
            accept_lines = [line for line in p.stdout.splitlines() if line.startswith("ACCEPT certificates")]
            if p.returncode != 0 or len(accept_lines) != 1:
                expect(S + "prune-style chunked replay", False, p.stderr.strip()[:300])
                return
            for key, value in (kv.split("=") for kv in accept_lines[0].split()[2:]):
                totals[key] = totals.get(key, 0) + int(value)
            chunks += 1
    want = expected_line(cell)
    got = accept_line(**totals)
    expect(S + f"prune-style chunked replay of the (10,{m}) cell of GP-10 ({len(cell)} records, {chunks} chunks "
           f"of at most 7, exact flags): summed counts equal the whole file's", got == want, got)


def noncanonical(n: int, edges, rng: random.Random) -> tuple[list[int], str]:
    """A relabelling perm of the graph whose graph6 string is not the canonical one, and that string."""
    code = g6_encode(n, edges)
    while True:
        perm = rng.sample(range(n), n)
        other = g6_encode(n, {(min(perm[i], perm[j]), max(perm[i], perm[j])) for i, j in edges})
        if other != code:
            return perm, other


def _run_kernel(kernel: Path, records: list[dict]):
    with tempfile.TemporaryDirectory(prefix="st-rhombus-k-") as tmp:
        tmp = Path(tmp)
        (tmp / "certs.jsonl").write_text(dump(records))
        (tmp / "graphs.g6").write_text("".join(r["g6"] + "\n" for r in records))
        unknown = [r["g6"] for r in records if r["verdict"] == "unknown"]
        (tmp / "UNKNOWN.g6").write_text("".join(c + "\n" for c in unknown))
        p = subprocess.run([str(PYTHON), str(kernel), "--allow-any-size", "--graphs", str(tmp / "graphs.g6"),
                            str(tmp / "certs.jsonl")], capture_output=True, text=True, timeout=900)
        return p.returncode, p.stdout, p.stderr


def spindle_controls(fx: Fixtures, fset: int) -> None:
    S = f"[set {fset}] "
    accept(S + "Moser spindle: its exact embedding in Q(sqrt3 + sqrt11) is ACCEPTED (a unit-distance graph)",
           [fx.spindle_embedded], accept_line(records=1, embedded=1), fset=fset)
    for name, rec, needle in fx.spindle_fakes:
        reject(S + "Moser spindle fake: " + name, needle, [rec], fset=fset)


_GP10: list = []


def gp10_controls(fset: int) -> None:
    S = f"[set {fset}] "
    if not _GP10:
        _GP10.append(gp10_records())
    recs, tally = _GP10[0]
    accept(S + f"GP-10's 324 graphs: {tally['tu'] + tally['refuted']} rhombus certificates and "
           f"{tally['neither']} unknown records in one file", recs, expected_line(recs), fset=fset)
    if tally.get("doubled"):
        rec = tally["doubled"]
        rh = rec["witness"]["rhombus"]
        accept(S + f"a GP-10 graph with no collision, tu with q == a (target 2 e_a - e_b - e_p, the entry at a "
               f"doubles): pair {rh['pair']}, edge {rh['edge']}, {len(rh['cycles'])} cycles", [rec],
               expected_line([rec]), fset=fset)
    else:
        info("no GP-10 graph has a doubled-entry certificate (q == a) without a collision")


def gp10_records():
    codes = canonical([g6_encode(max(max(e) for e in F398[i]) + 1, {tuple(e) for e in F398[i]})
                       for i in range(74, 398)])
    recs, tally = [], {"refuted": 0, "tu": 0, "neither": 0}
    for code in codes:
        n, edges = g6_decode(code)
        got = TestProver(n, edges).find()
        if got is None:
            tally["neither"] += 1
            recs.append(record(code, "unknown"))
        else:
            tally[got[0]] += 1
            rec = rhombus_rec(code, got)
            assert oracle(rec, n, edges) is True
            recs.append(rec)
    for code in codes:
        n, edges = g6_decode(code)
        got = TestProver(n, edges).doubled()
        if got is not None:
            rec = rhombus_rec(code, got)
            assert oracle(rec, n, edges) is True
            tally["doubled"] = rec
            break
    info(f"GP-10's 324 minimal forbidden graphs, exact test prover: {tally['tu']} forced unit distance, "
         f"{tally['refuted']} collision, {tally['neither']} neither (LABNOTES 2026-09-26, mod 2^61-1: 218, 3, 103)")
    return recs, tally


def pin_controls(fx: Fixtures) -> None:
    with tempfile.TemporaryDirectory(prefix="st-rhombus-pin-") as tmp:
        for target in ("udcheck.py", "udcheck398.py"):
            d = Path(tmp) / target.replace(".", "_") / "check"
            d.mkdir(parents=True)
            shutil.copy2(CHECKER, d / CHECKER.name)
            for name in ("udcheck.py", "udcheck398.py"):
                raw = (HERE / name).read_bytes()
                (d / name).write_bytes(raw + b"\n" if name == target else raw)
            for fset in (74, 398):
                if target == "udcheck398.py" and fset == 74:
                    accept(f"[set 74] pins: udcheck398.py changed by one byte does not matter to set 74",
                           [fx.k23], expected_line([fx.k23]), checker=d / CHECKER.name, data_dir=DATA, fset=74)
                    continue
                reject(f"[set {fset}] pins: {target} changed by one byte -> refuse to run (exit 2)",
                       f"not the pinned {target}", [fx.k23], code=2, checker=d / CHECKER.name, data_dir=DATA,
                       fset=fset)


# ---------------------------------------------------------------- tri witnesses: the routing only

TRI_STUB = '''"""A TEST DOUBLE for check/tri_verify.py, written by selftest-rhombus.py into a temporary copy of the
check directory.  It verifies nothing: it logs its arguments and answers as $TRI_STUB_MODE says."""
import json
import os
MODE = os.environ.get("TRI_STUB_MODE", "accept")


def verify_tri_witness(n, edges, verdict, witness):
    log = os.environ.get("TRI_STUB_LOG")
    if log:
        with open(log, "a") as out:
            out.write(json.dumps([n, sorted(map(list, edges)), verdict, witness, type(edges).__name__]) + "\\n")
    if MODE == "accept":
        return (True, "", {"nodes": 1})
    if MODE == "reject":
        return (False, "the stub rejects this tree", {})
    if MODE == "raise":
        raise ValueError("the stub raises")
    if MODE == "truthy":
        return (1, "", {})
    if MODE == "short":
        return (True, "")
    raise RuntimeError(MODE)
'''


def as_tri(rec: dict) -> dict:
    """A rhombus certificate as a Section 4 leaf with no split (coefficients x + 0 w; zeta 0 for tu), which is
    a valid tri certificate too.  The stub does not look at it; the real verifier should accept it."""
    rh = rec["witness"]["rhombus"]
    leaf = {"cycles": rh["cycles"], "cycle_coefficients": [[l, 0] for l in rh["coefficients"]],
            "triangles": [], "triangle_coefficients": [], "scale": [rh["scale"], 0], "pair": rh["pair"]}
    if "edge" in rh:
        leaf["edge"] = rh["edge"]
        leaf["zeta"] = 0
    return record(rec["g6"], rec["verdict"], {"tri": {"tree": {"leaf": leaf}}})


def checker_copy(root: Path, stub: str | None, pin: str | None = None) -> Path:
    d = root / "check"
    d.mkdir(parents=True)
    src = CHECKER.read_text()
    if pin is not None:
        marker = "TRI_VERIFY_SHA256: str | None = None"
        assert src.count(marker) == 1
        src = src.replace(marker, f'TRI_VERIFY_SHA256: str | None = "{pin}"')
    (d / CHECKER.name).write_text(src)
    for name in ("udcheck.py", "udcheck398.py"):
        shutil.copy2(HERE / name, d / name)
    if stub is not None:
        (d / "tri_verify.py").write_text(stub)
    return d / CHECKER.name


def tri_controls(fx: Fixtures) -> None:
    info(f"check/tri_verify.py in this checkout: {'present' if (HERE / 'tri_verify.py').exists() else 'absent'} "
         f"(the controls below use temporary copies of the check directory, with a stub or without)")
    k23, g0 = fx.k23, fx.gadgets[0]
    t_ref, t_tu = as_tri(fx.random[1]), as_tri(fx.gadgets[2])
    assert t_ref["verdict"] == "refuted" and t_tu["verdict"] == "tu"
    mixed = [k23, t_ref, g0, t_tu, fx.kernel_tu, fx.unknowns[0]]
    stub_hash = hashlib.sha256(TRI_STUB.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="st-rhombus-tri-") as tmp:
        tmp = Path(tmp)
        absent = checker_copy(tmp / "absent", None)
        stub = checker_copy(tmp / "stub", TRI_STUB)
        pinned = checker_copy(tmp / "pinned", TRI_STUB, pin=stub_hash)
        wrong_pin = checker_copy(tmp / "wrongpin", TRI_STUB, pin="0" * 64)
        no_function = checker_copy(tmp / "nofunction", "def something_else():\n    return None\n")
        broken = checker_copy(tmp / "broken", "def verify_tri_witness(:\n")
        log = tmp / "calls.jsonl"

        def env(mode: str) -> dict:
            if log.exists():
                log.unlink()
            return {"TRI_STUB_MODE": mode, "TRI_STUB_LOG": str(log)}

        def calls() -> list:
            return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

        reject("tri: check/tri_verify.py absent -> a tri record is rejected, saying why", "no tri verifier",
               [k23, t_ref], checker=absent, data_dir=DATA, fset=398)
        accept("tri: check/tri_verify.py absent does not matter to a file without tri records", [k23, g0],
               expected_line([k23, g0]), checker=absent, data_dir=DATA, fset=398)
        for fset in (74, 398):
            accept(f"[set {fset}] tri: stub verifier accepting; rhombus, tri and kernel records in one file",
                   mixed, expected_line(mixed), checker=stub, data_dir=DATA, env=env("accept"), fset=fset)
            want = []
            for rec in (t_ref, t_tu):
                n, edges = fx.graph[rec["g6"]]
                want.append([n, sorted(map(list, edges)), rec["verdict"], rec["witness"], "frozenset"])
            expect(f"[set {fset}] tri: the verifier was called once per tri record, in order, with n, the edge set "
                   f"(a frozenset of (i, j), i < j), the verdict and the witness object as read", calls() == want,
                   str(calls())[:300])
        reject("tri: stub verifier rejecting -> REJECT with its reason", "the stub rejects this tree", [t_ref],
               checker=stub, data_dir=DATA, env=env("reject"), fset=398)
        reject("tri: stub verifier raising -> REJECT", "the tri verifier raised ValueError: the stub raises", [t_tu],
               checker=stub, data_dir=DATA, env=env("raise"), fset=398)
        reject("tri: stub verifier returning ok = 1 (truthy, not True) -> REJECT", "(ok was 1, not True)", [t_tu],
               checker=stub, data_dir=DATA, env=env("truthy"), fset=398)
        reject("tri: stub verifier returning a 2-tuple -> REJECT", "not (ok, reason, stats)", [t_tu],
               checker=stub, data_dir=DATA, env=env("short"), fset=398)
        extra = copy.deepcopy(t_ref)
        extra["witness"]["note"] = 1
        reject("tri: a witness with a key beside 'tri'", "the witness has exactly the key 'tri'", [extra],
               checker=stub, data_dir=DATA, env=env("accept"), fset=398)
        expect("tri: ... and the verifier was not called for it", calls() == [], str(calls())[:200])
        both = copy.deepcopy(t_ref)
        both["witness"]["rhombus"] = fx.random[1]["witness"]["rhombus"]
        reject("tri: a witness with both 'rhombus' and 'tri'", "extra keys ['tri']", [both], checker=stub,
               data_dir=DATA, env=env("accept"), fset=398)
        reject("tri: verdict unknown with a tri witness", "never carries a tri witness",
               [dict(t_ref, verdict="unknown")], checker=stub, data_dir=DATA, env=env("accept"), unknown=[t_ref["g6"]],
               fset=398)
        _, other = noncanonical(*fx.graph[t_tu["g6"]], random.Random(5))
        reject("tri: a tri record whose graph6 is not canonical", "is not nauty-labelg canonical",
               [dict(t_tu, g6=other)], checker=stub, data_dir=DATA, env=env("accept"), fset=398)
        reject("tri: a tri record duplicating a rhombus record's graph", "duplicate graph6 record",
               [fx.random[1], t_ref], checker=stub, data_dir=DATA, env=env("accept"), fset=398)
        accept("tri: TRI_VERIFY_SHA256 set to the stub's hash -> accepted", [t_ref, t_tu],
               expected_line([t_ref, t_tu]), checker=pinned, data_dir=DATA, env=env("accept"), fset=398)
        reject("tri: TRI_VERIFY_SHA256 set to another hash -> rejected", "not the pinned tri_verify.py", [t_ref],
               checker=wrong_pin, data_dir=DATA, env=env("accept"), fset=398)
        reject("tri: a tri_verify.py without verify_tri_witness", "has no function verify_tri_witness", [t_ref],
               checker=no_function, data_dir=DATA, fset=398)
        reject("tri: a tri_verify.py that does not compile", "failed to load: SyntaxError", [t_ref],
               checker=broken, data_dir=DATA, fset=398)
        accept("tri: a broken tri_verify.py is never loaded for a file without tri records", [k23, g0],
               expected_line([k23, g0]), checker=broken, data_dir=DATA, fset=398)


# ---------------------------------------------------------------- the benchmark

def bench(count: int, fset: int, seed: int = 4242, keep: Path | None = None) -> None:
    rng = random.Random(seed)
    t0 = time.monotonic()
    raw = []
    while len(raw) < int(count * 1.05) + 10:
        n = rng.randint(13, 23)
        m = rng.randint(int(2.2 * n), int(2.8 * n))
        perm = rng.sample(range(n), n)
        if rng.random() < 0.5:
            h1, h2, a, b, c = perm[:5]
            edges = {(min(u, v), max(u, v)) for u in (h1, h2) for v in (a, b, c)}
            avoid = set()
        else:
            g = GADGETS[0]
            edges = {(min(perm[u], perm[v]), max(perm[u], perm[v])) for u, v in g["edges"]}
            avoid = {(min(perm[g["pair"][0]], perm[g["pair"][1]]), max(perm[g["pair"][0]], perm[g["pair"][1]]))}
        while len(edges) < m:
            u, v = rng.sample(range(n), 2)
            e = (min(u, v), max(u, v))
            if e not in avoid:
                edges.add(e)
        raw.append(g6_encode(n, edges))
    codes = list(dict.fromkeys(canonical(raw)))[:count]
    records = []
    for index, code in enumerate(codes):
        n, edges = g6_decode(code)
        adj = adjacency(n, edges)
        if index % 2:
            cert = _bench_gadget0(adj, edges) or _bench_k23(adj)
        else:
            cert = _bench_k23(adj) or _bench_gadget0(adj, edges)
        assert cert is not None
        verdict, rh = cert
        cyc = [list(c) for c in rh["cycles"]]
        co = list(rh["coefficients"])
        want = rng.randint(5, 40)
        if want - len(cyc) == 1:
            want += 1
        spare = four_cycles_sample(n, adj, rng, 12) or [list(c) for c in rh["cycles"]]
        while len(cyc) < want:
            c = rng.choice(spare)
            l = rng.choice([1, -1, 2, -2, 3, -5, 12, -40, 1000])
            if want - len(cyc) == 3:
                cyc += [list(c), c[2:] + c[:2], [c[0], c[3], c[2], c[1]]]
                co += [2 * l, -l, -l]
            else:
                cyc += [list(c), c[2:] + c[:2] if rng.random() < 0.5 else [c[0], c[3], c[2], c[1]]]
                co += [l, -l]
        k = rng.choice([1, 1, 1, 1, -1, 2, 3])
        rh = dict(rh, cycles=cyc, coefficients=[k * z for z in co], scale=k * rh["scale"])
        records.append(record(code, verdict, {"rhombus": rh}))
    t1 = time.monotonic()
    ncyc = [len(r["witness"]["rhombus"]["cycles"]) for r in records]
    orders = [ord(r["g6"][0]) - 63 for r in records]
    info(f"bench: {len(records)} distinct canonical graphs, n {min(orders)}..{max(orders)}, cycles "
         f"{min(ncyc)}..{max(ncyc)} (mean {sum(ncyc) / len(ncyc):.1f}), "
         f"{sum(1 for r in records if r['verdict'] == 'tu')} tu, built in {t1 - t0:.0f}s")
    sample = rng.sample(records, min(300, len(records)))
    bad = [r for r in sample if oracle(r, *g6_decode(r["g6"])) is not True]
    expect("bench: the oracle confirms a sample of 300 bench certificates", not bad, str(bad[:1])[:200])
    want_line = expected_line(records)
    with tempfile.TemporaryDirectory(prefix="st-rhombus-bench-") as tmp:
        tmp = Path(keep) if keep else Path(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "certs.jsonl").write_text(dump(records))
        (tmp / "graphs.g6").write_text("".join(r["g6"] + "\n" for r in records))
        (tmp / "expected.txt").write_text(want_line + "\n")
        size = (tmp / "certs.jsonl").stat().st_size
        count = len(records)
        del records, raw, codes, sample
        # /usr/bin/time -v measures the checker from a small parent (a fork of this big process would count
        # this process's pages as the child's)
        cmd = ["/usr/bin/time", "-v", "nice", "-n", "10", str(PYTHON), str(CHECKER), "--allow-any-size",
               "--forbidden-set", str(fset), "--graphs", str(tmp / "graphs.g6"), str(tmp / "certs.jsonl")]
        for attempt in range(3):
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start = time.monotonic()
            p = subprocess.run(cmd, capture_output=True, text=True)
            wall = time.monotonic() - start
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
            rss = next((int(line.split()[-1]) for line in p.stderr.splitlines()
                        if "Maximum resident set size" in line), 0)
            load = os.getloadavg()[0]
            expect(f"bench run {attempt + 1}: the checker ACCEPTS the {count} records", p.returncode == 0 and
                   p.stdout.startswith(want_line), (p.stdout + p.stderr)[:200])
            info(f"bench [set {fset}] run {attempt + 1}: {count} records, {size / 1e6:.1f} MB, wall {wall:.2f}s = "
                 f"{count / wall:,.0f} records/s; CPU (checker, labelg, kernel) {cpu:.2f}s = "
                 f"{count / cpu:,.0f} records/s; largest process {rss / 1024:.0f} MB; "
                 f"1-min load average {load:.2f} on {os.cpu_count()} logical CPUs")


def four_cycles_sample(n: int, adj: list[set], rng: random.Random, want: int) -> list[list[int]]:
    out = []
    for _ in range(40 * want):
        u = rng.randrange(n)
        if len(adj[u]) < 2:
            continue
        v, x = rng.sample(sorted(adj[u]), 2)
        common = sorted((adj[v] & adj[x]) - {u})
        if common:
            out.append([u, v, rng.choice(common), x])
            if len(out) >= want:
                break
    return out


def _bench_k23(adj: list[set]):
    n = len(adj)
    for h1 in range(n):
        for h2 in range(h1 + 1, n):
            common = sorted(adj[h1] & adj[h2])
            if len(common) >= 3:
                x, y, z = common[:3]
                return "refuted", {"cycles": [[x, h1, y, h2], [y, h1, z, h2]], "coefficients": [1, -1],
                                   "scale": 1, "pair": [x, z]}
    return None


def _bench_gadget0(adj: list[set], edges: set):
    n = len(adj)
    for c2 in range(n):
        for c3 in adj[c2]:
            for c1 in adj[c2] - {c3}:
                for c0 in (adj[c1] & adj[c3]) - {c2}:
                    for c5 in adj[c2] - {c3, c1, c0}:
                        if c5 in adj[c1]:
                            continue
                        for c4 in (adj[c5] & adj[c3]) - {c2, c1, c0}:
                            if c4 in adj[c0]:
                                return "tu", {"cycles": [[c0, c1, c2, c3], [c2, c3, c4, c5]],
                                              "coefficients": [-1, 1], "scale": 1, "pair": [c1, c5],
                                              "edge": [c0, c4]}
    return None


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bench", type=int, metavar="N", help="also time the checker on N bench records")
    parser.add_argument("--bench-only", action="store_true", help="skip the controls")
    parser.add_argument("--bench-keep", type=Path, help="write the bench files here and keep them")
    parser.add_argument("--fuzz", type=int, default=6000, help="random mutations checked against the oracle")
    args = parser.parse_args()
    if not PYTHON.is_file():
        print(f"missing {PYTHON}", file=sys.stderr)
        return 2
    print(f"checker {CHECKER} (sha256 {hashlib.sha256(CHECKER.read_bytes()).hexdigest()[:16]}...), "
          f"interpreter {PYTHON}", flush=True)
    if not args.bench_only:
        rng = random.Random(20260926)
        fx = Fixtures(rng)
        udr = load_module(CHECKER, "udcheck_rhombus_under_test")
        kernel = load_module(UDCHECK, "udcheck_kernel_for_selftest")
        expect("setup: the in-process kernel is the pinned udcheck.py",
               hashlib.sha256(UDCHECK.read_bytes()).hexdigest() == udr.KERNEL_SHA256)
        decoder_differential(udr, kernel, random.Random(7), 3000)
        fuzz_against_oracle(udr, fx, random.Random(11), args.fuzz)
        reds = 0
        for fset in (74, 398):
            cli_controls(fx, fset)
            reds += rhombus_red_controls(fx, fset)
            reds += raw_line_controls(fx, fset)
            spindle_controls(fx, fset)
            gp10_controls(fset)
        pin_controls(fx)
        tri_controls(fx)
        info(f"{reds} rhombus-record and file-structure red controls across the two sets, besides the file-level ones")
    if args.bench:
        bench(args.bench, 398, keep=args.bench_keep)
    print(f"SELFTEST-RHOMBUS {'PASS' if not failures else 'FAIL'}: {passes} passed, {len(failures)} failed")
    for f in failures:
        print("FAILED:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
