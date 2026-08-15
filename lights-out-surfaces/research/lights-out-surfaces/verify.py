#!/usr/bin/env python3
# verify.py — a THIRD, independent computation of the surface Lights Out nullities,
# in a different language with a separately-coded neighbourhood function and a
# separately-coded GF(2) elimination (Python big-int row bitmasks). If this agrees
# with engine.mjs (JavaScript Gauss-Jordan) and brute.mjs (direct kernel count),
# and both published grounds (A159257 flat, A165738 torus) come out right, the new
# sequences rest on three structurally independent code paths, not one.
#
# Run:  python3 verify.py [NMAX=30]
# Prints one line per surface; a driver diffs these against engine.mjs.

import sys

SURFACES = ['plane', 'cylinder', 'torus', 'mobius', 'klein', 'projective']

def neighbours(r, c, n, surface):
    """Closed neighbourhood of cell (r,c) on the n x n board, as a set of (r,c).
    Coded independently of engine.mjs. Column-wrap glues col n-1<->0; row-wrap glues
    row n-1<->0; 'flip' surfaces reverse the transverse index on that wrap."""
    col_wrap = {'plane': None, 'cylinder': 'plain', 'torus': 'plain',
                'mobius': 'flip', 'klein': 'flip', 'projective': 'flip'}[surface]
    row_wrap = {'plane': None, 'cylinder': None, 'torus': 'plain',
                'mobius': None, 'klein': 'plain', 'projective': 'flip'}[surface]
    s = {(r, c)}  # self-toggle
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if nc < 0 or nc >= n:            # off left/right -> column wrap
            if col_wrap is None:
                continue
            nc %= n
            if col_wrap == 'flip':
                nr = n - 1 - nr
        if nr < 0 or nr >= n:            # off top/bottom -> row wrap
            if row_wrap is None:
                continue
            nr %= n
            if row_wrap == 'flip':
                nc = n - 1 - nc
        if 0 <= nr < n and 0 <= nc < n:
            s.add((nr, nc))
    return s

def nullity(n, surface):
    N = n * n
    idx = lambda r, c: r * n + c
    # Build symmetric matrix rows as Python ints (row i, bit j set iff button j hits light i)
    rows = [0] * N
    for r in range(n):
        for c in range(n):
            j = idx(r, c)
            for (nr, nc) in neighbours(r, c, n, surface):
                rows[idx(nr, nc)] |= (1 << j)
    # GF(2) rank by elimination (independent of engine.mjs's ordering)
    rank = 0
    for col in range(N):
        bit = 1 << col
        piv = -1
        for i in range(rank, N):
            if rows[i] & bit:
                piv = i
                break
        if piv == -1:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        pr = rows[rank]
        for i in range(N):
            if i != rank and (rows[i] & bit):
                rows[i] ^= pr
        rank += 1
    return N - rank

if __name__ == '__main__':
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    for s in SURFACES:
        vals = [str(nullity(n, s)) for n in range(1, nmax + 1)]
        print(f"{s:11s}: {', '.join(vals)}")
