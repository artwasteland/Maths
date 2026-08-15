#!/usr/bin/env python3
"""ca-garden-of-eden -- independent Python cross-check (a separate language and
a separately written codebase from engine.mjs). Must agree with the Node engine.

Methods:
  (A) brute force: enumerate all 2^n ring configs, apply the rule, count distinct images.
  (B) transfer matrix over the de Bruijn transition monoid, using plain nested-list
      boolean 4x4 matrices and Python big-ints (structurally distinct from the packed
      16-bit representation in engine.mjs).

Checks:
  * positive controls (reversible ECAs, constant rules);
  * brute == transfer within Python, n<=18, for all featured rules;
  * Python transfer reproduces the recorded 16-term heads;
  * EVERY staged b-file term (all 8 files, n=1..64) equals the Python transfer
    value, so every published term is confirmed by a second implementation that
    shares no code with the Node generator.

Run: python3 research/ca-garden-of-eden/verify.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OEIS_DIR = os.path.join(HERE, "..", "..", "oversight", "oeis", "ca-garden-of-eden")


def read_bfile(path):
    if not os.path.exists(path):
        return None
    m = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            n, v = line.split()
            m[int(n)] = int(v)
    return m


def local_map(rule):
    return lambda a, b, c: (rule >> ((a << 2) | (b << 1) | c)) & 1

def step(rule, n, x):
    f = local_map(rule)
    y = 0
    for i in range(n):
        a = (x >> ((i - 1) % n)) & 1
        b = (x >> i) & 1
        c = (x >> ((i + 1) % n)) & 1
        if f(a, b, c):
            y |= (1 << i)
    return y

def brute_goe(rule, n):
    seen = bytearray(1 << n)
    f = local_map(rule)
    for x in range(1 << n):
        y = 0
        for i in range(n):
            a = (x >> ((i - 1) % n)) & 1
            b = (x >> i) & 1
            c = (x >> ((i + 1) % n)) & 1
            if f(a, b, c):
                y |= (1 << i)
        seen[y] = 1
    image = sum(seen)
    return (1 << n) - image

# ---- transfer matrix over the de Bruijn transition monoid (boolean 4x4 as tuple-of-tuples)
def symbol_matrices(rule):
    f = local_map(rule)
    M = [[[0] * 4 for _ in range(4)] for _ in range(2)]
    for p in range(2):
        for q in range(2):
            for r in range(2):
                b = f(p, q, r)
                i = (p << 1) | q
                j = (q << 1) | r
                M[b][i][j] = 1
    return (tuple(tuple(row) for row in M[0]), tuple(tuple(row) for row in M[1]))

def bmul(A, B):
    return tuple(tuple(1 if any(A[i][k] and B[k][j] for k in range(4)) else 0
                       for j in range(4)) for i in range(4))

def btrace(A):
    return 1 if any(A[i][i] for i in range(4)) else 0

IDENT = tuple(tuple(1 if i == j else 0 for j in range(4)) for i in range(4))

def image_sizes(rule, maxn):
    M0, M1 = symbol_matrices(rule)
    # build reachable monoid + transition, then iterate the count distribution
    states = [IDENT]
    idx = {IDENT: 0}
    trans = []
    s = 0
    while s < len(states):
        m = states[s]
        row = []
        for Mb in (M0, M1):
            t = bmul(m, Mb)
            if t not in idx:
                idx[t] = len(states)
                states.append(t)
            row.append(idx[t])
        trans.append(row)
        s += 1
    trace_nz = [btrace(m) for m in states]
    dist = [0] * len(states)
    dist[0] = 1
    out = [0] * (maxn + 1)
    for k in range(1, maxn + 1):
        nxt = [0] * len(states)
        for st, c in enumerate(dist):
            if c:
                t0, t1 = trans[st]
                nxt[t0] += c
                nxt[t1] += c
        dist = nxt
        out[k] = sum(c for st, c in enumerate(dist) if trace_nz[st])
    return out

def goe_sizes(rule, maxn):
    img = image_sizes(rule, maxn)
    return [0] + [(1 << n) - img[n] for n in range(1, maxn + 1)]


def main():
    npass = nfail = 0

    def ok(name, cond, extra=""):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print(f"  ok   {name}")
        else:
            nfail += 1
            print(f"  FAIL {name} {extra}")

    print("POSITIVE CONTROLS")
    # reversible ECAs -> GoE=0 everywhere
    good = all(all(v == 0 for v in goe_sizes(r, 18)[1:]) for r in (15, 51, 85, 170, 204, 240))
    ok("reversible ECAs {15,51,85,170,204,240} -> GoE(n)=0 for n<=18", good)
    # constant rules -> 2^n - 1
    good = all(goe_sizes(r, 18)[n] == (1 << n) - 1 for r in (0, 255) for n in range(1, 19))
    ok("constant rules 0,255 -> GoE(n)=2^n-1 (n<=18)", good)

    print("\nBRUTE == TRANSFER (Python), and PYTHON == NODE headline values")
    for r in (30, 110, 184, 22, 126, 54, 146, 90, 150):
        gt = goe_sizes(r, 18)
        good = all(brute_goe(r, n) == gt[n] for n in range(1, 19))
        ok(f"rule {r}: brute == transfer, n=1..18", good)

    # explicit reproduction of the recorded headline sequences (must match engine.mjs / staged data)
    KNOWN = {
        30:  [1, 1, 3, 5, 6, 12, 22, 33, 57, 101, 166, 280, 482, 813, 1373, 2337],
        110: [1, 2, 3, 6, 10, 23, 49, 102, 210, 442, 935, 1971, 4134, 8647, 18043, 37542],
        184: [0, 0, 0, 4, 10, 24, 56, 124, 270, 580, 1232, 2596, 5434, 11312, 23440, 48380],
        22:  [1, 1, 6, 5, 6, 30, 50, 89, 249, 466, 870, 2046, 4109, 8079, 17531, 35785],
    }
    for r, seq in KNOWN.items():
        gt = goe_sizes(r, len(seq))[1:]
        ok(f"rule {r}: Python transfer reproduces the recorded 16-term GoE head", gt == seq,
           f"got {gt}")

    print("\nSTAGED B-FILES == PYTHON TRANSFER (every term, independent of the Node generator)")
    bfiles = [
        ("b-rule30-goe.txt", 30, "goe"),
        ("b-rule30-image.txt", 30, "image"),
        ("b-rule110-goe.txt", 110, "goe"),
        ("b-rule184-goe.txt", 184, "goe"),
        ("b-rule22-goe.txt", 22, "goe"),
        ("b-rule126-goe.txt", 126, "goe"),
        ("b-rule54-goe.txt", 54, "goe"),
        ("b-rule146-goe.txt", 146, "goe"),
    ]
    for fname, rule, kind in bfiles:
        bf = read_bfile(os.path.join(OEIS_DIR, fname))
        if bf is None:
            ok(f"{fname} == Python transfer", False, "b-file MISSING")
            continue
        maxn = max(bf)
        series = goe_sizes(rule, maxn) if kind == "goe" else image_sizes(rule, maxn)
        bad = next((n for n in sorted(bf) if series[n] != bf[n]), None)
        ok(f"{fname} == Python transfer, every term (n=1..{maxn})", bad is None,
           "" if bad is None else f"first mismatch n={bad}: file={bf[bad]} python={series[bad]}")

    print(f"\n{npass}/{npass + nfail} checks passed")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
