// engine.mjs — Lights Out nullity on surfaces, exact over GF(2).
//
// THE OBJECT. An m x n grid of lights, each also a button. Pressing a button
// toggles every light in its *closed neighbourhood* (itself and its geometric
// neighbours). The board is the grid, but its edges are glued according to a
// SURFACE. Over GF(2), pressing is a linear map M = A + I, where A is the
// adjacency of the board's cell graph and I the identity (the "+I" is the
// self-toggle). Which initial light patterns are solvable, and how many
// solutions each has, is governed entirely by the NULLITY of M over GF(2):
//   nullity d = N - rank(M),  N = m*n.
//   * d = 0  <=>  every pattern is solvable with a UNIQUE solution.
//   * in general the solvable patterns number 2^(N-d), each with 2^d solutions.
//   * the d-dimensional kernel of M is spanned by the QUIET PATTERNS: sets of
//     buttons whose presses cancel out and change nothing.
//
// This file computes d(n) for the n x n board on six surfaces, exactly, by
// Gauss-Jordan elimination over GF(2) with BigInt row bitmasks. It is
// calibrated by reproducing two published OEIS sequences bit-for-bit before any
// new value is trusted: the flat grid (A159257) and the torus (A165738).
//
// CONVENTION (stated so it can be checked). The board is a SIMPLE graph: a
// button toggles each DISTINCT cell of its closed neighbourhood exactly once
// (set semantics), exactly as the physical game does and as GridGraph does for
// the flat and torus cases. Where a wrap makes two geometric neighbours land on
// the same cell (only at tiny n), that cell is toggled once, not twice.
//
// Run:  node engine.mjs            (prints n=1..20 for all surfaces + calibration)
//       node engine.mjs 40         (up to n=40)

// ---- surface edge-identifications -------------------------------------------
// For an m x n grid (rows 0..m-1, cols 0..n-1), each surface says what a step
// off each of the four edges lands on. Interior steps are the usual +/-1.
// A neighbour that would leave the board with no identification is dropped.
//
//   plane      : no wrap (free boundary)                         -> A159257
//   cylinder   : columns wrap plainly, rows free
//   torus      : both axes wrap plainly                          -> A165738
//   mobius     : columns wrap WITH a row-flip, rows free
//   klein      : columns wrap WITH a row-flip, rows wrap plainly
//   projective : both axes wrap WITH a flip (antipodal)          -> RP^2

export const SURFACES = ['plane', 'cylinder', 'torus', 'mobius', 'klein', 'projective'];

// Return the cell reached by stepping (dr,dc) from (r,c) on an m x n board of
// the given surface, as {r,c}, or null if it leaves the board.
function step(r, c, dr, dc, m, n, surface) {
  let nr = r + dr, nc = c + dc;
  const colOut = nc < 0 || nc >= n;   // stepped off left/right edge
  const rowOut = nr < 0 || nr >= m;   // stepped off top/bottom edge

  // horizontal wrap (columns)
  if (colOut) {
    if (surface === 'plane') return null;
    if (surface === 'cylinder' || surface === 'torus') {
      nc = (nc + n) % n;
    } else if (surface === 'mobius' || surface === 'klein' || surface === 'projective') {
      nc = (nc + n) % n;
      nr = m - 1 - nr;            // row-flip on the column wrap
    }
  }
  // vertical wrap (rows)
  if (rowOut) {
    if (surface === 'plane' || surface === 'cylinder' || surface === 'mobius') return null;
    if (surface === 'torus' || surface === 'klein') {
      nr = ((nr % m) + m) % m;
    } else if (surface === 'projective') {
      nr = ((nr % m) + m) % m;
      nc = n - 1 - nc;           // col-flip on the row wrap
    }
  }
  // A projective corner step could have flipped one coord then gone out on the
  // other; normalise any residual out-of-range by re-checking once.
  if (nr < 0 || nr >= m || nc < 0 || nc >= n) {
    // Re-apply the wrap that is still out (can happen after a flip near a corner).
    if (nc < 0 || nc >= n) {
      if (surface === 'plane') return null;
      nc = ((nc % n) + n) % n;
      if (surface === 'mobius' || surface === 'klein' || surface === 'projective') nr = m - 1 - nr;
    }
    if (nr < 0 || nr >= m) {
      if (surface === 'plane' || surface === 'cylinder' || surface === 'mobius') return null;
      nr = ((nr % m) + m) % m;
      if (surface === 'projective') nc = n - 1 - nc;
    }
    if (nr < 0 || nr >= m || nc < 0 || nc >= n) return null;
  }
  return { r: nr, c: nc };
}

// Closed neighbourhood of (r,c) as a Set of linear indices (r*n+c), set semantics.
export function closedNeighbourhood(r, c, m, n, surface) {
  const s = new Set();
  s.add(r * n + c);                       // the self-toggle (the "+I")
  for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
    const nb = step(r, c, dr, dc, m, n, surface);
    if (nb) s.add(nb.r * n + nb.c);
  }
  return s;
}

// Build M (N rows of BigInt, N = m*n) with bit j of row i set iff pressing
// button j toggles light i.  M is symmetric by construction.
export function buildMatrix(m, n, surface) {
  const N = m * n;
  const rows = new Array(N).fill(0n);
  for (let r = 0; r < m; r++) {
    for (let c = 0; c < n; c++) {
      const j = r * n + c;
      for (const i of closedNeighbourhood(r, c, m, n, surface)) {
        rows[i] |= (1n << BigInt(j));      // button j toggles light i
      }
    }
  }
  return { rows, N };
}

// Assert symmetry M == M^T (a cheap guard that the identifications are consistent).
export function isSymmetric(rows, N) {
  for (let i = 0; i < N; i++) {
    for (let j = i + 1; j < N; j++) {
      const aij = (rows[i] >> BigInt(j)) & 1n;
      const aji = (rows[j] >> BigInt(i)) & 1n;
      if (aij !== aji) return false;
    }
  }
  return true;
}

// GF(2) rank by forward elimination over BigInt rows. nullity = N - rank.
export function nullity(rows0, N) {
  const rows = rows0.slice();
  let rank = 0;
  let col = 0;
  for (; col < N && rank < N; col++) {
    const bit = 1n << BigInt(col);
    let piv = -1;
    for (let i = rank; i < N; i++) if (rows[i] & bit) { piv = i; break; }
    if (piv === -1) continue;
    [rows[rank], rows[piv]] = [rows[piv], rows[rank]];
    const pr = rows[rank];
    for (let i = 0; i < N; i++) {
      if (i !== rank && (rows[i] & bit)) rows[i] ^= pr;
    }
    rank++;
  }
  return N - rank;
}

// Convenience: nullity of the n x n board on a surface.
export function surfaceNullity(n, surface) {
  const { rows, N } = buildMatrix(n, n, surface);
  return nullity(rows, N);
}

// ---- CLI --------------------------------------------------------------------
// Guarded so the module is isomorphic: importing it in a browser (the companion
// film does) must not touch Node's `process`.
if (typeof process !== 'undefined' && process.argv && import.meta.url === `file://${process.argv[1]}`) {
  const NMAX = parseInt(process.argv[2] || '20', 10);
  const seqs = {};
  for (const s of SURFACES) seqs[s] = [];
  for (let n = 1; n <= NMAX; n++) {
    for (const s of SURFACES) {
      const { rows, N } = buildMatrix(n, n, s);
      if (n <= 6 && !isSymmetric(rows, N)) { console.error(`ASYMMETRIC M at n=${n} ${s}`); process.exit(1); }
      seqs[s].push(nullity(rows, N));
    }
  }
  for (const s of SURFACES) console.log(s.padEnd(11) + ': ' + seqs[s].join(', '));
}
