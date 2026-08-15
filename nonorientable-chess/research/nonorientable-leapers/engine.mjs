// research/nonorientable-leapers/engine.mjs
//
// Non-attacking (a,b)-LEAPER placements on four board topologies, one piece per
// row and per column (the permutation / "semiqueen" convention behind OEIS
// A007705 and the torus leaper table in research/leapers-on-a-torus/).
//
//   flat    — the ordinary board, no edges glued.
//   torus   — both edge-pairs glued straight (the modular board).
//   mobius  — left/right columns glued with a vertical FLIP; top/bottom free
//             (an open Mobius BAND — rows do not wrap).  A queen -> A137279.
//   klein   — columns wrap straight; top/bottom rows glued with a horizontal
//             flip (a closed Klein bottle).
//
// WHY THIS IS CANONICAL FOR A LEAPER (and only "convention-dependent" for a
// slider). A leaper makes a single fixed-vector jump, so its landing square is
// defined by the STANDARD universal-cover rule: unfold the surface to its cover
// (the infinite plane, or the infinite strip for the Mobius band), read the
// leaper's vector there, and fold the target back through the surface's deck
// group. This is trajectory-independent — it does not matter "which way round the
// L" the knight goes — exactly BECAUSE the move is a single jump, not a swept
// ray. A queen's diagonal has no such canonical answer on a non-orientable board
// (it spirals; see research/nonorientable-queens), which is why the clean twisted
// extension was always a bounded-move piece (a king — or a leaper).
//
// The attack model is CERTIFIED three ways (verify.mjs):
//   (1) fed the eight unit leapers {(1,0),(0,1),(1,1)}, it reproduces the
//       nonorientable-queens KING attack graph cell-for-cell on ALL four
//       topologies — i.e. it agrees with the already-validated ray-tracer on the
//       one move where the two definitions must coincide (a single step);
//   (2) its torus leaper permutation counts reproduce research/leapers-on-a-torus
//       (knight 1,2,0,8,10,72,210,1408,... etc.) bit-for-bit;
//   (3) two independent enumerators (a graph backtracker and a from-scratch
//       column DFS) agree, and a C backtracker (leap.c) agrees again.

// ---------------------------------------------------------------------------
// Folding a plane target (R,C) back to a board cell [r,c] in {0..n-1}^2, or null
// if it falls off a free boundary. R = row (vertical), C = column (horizontal).
// The four deck groups:
//   torus  : <(R,C)->(R,C+n), (R,C)->(R+n,C)>            both straight.
//   mobius : <g:(R,C)->((n-1)-R, C+n)>, rows in [0,n-1]. glide; band, R never wraps.
//   klein  : <t_C:(R,C)->(R,C+n),  t_R:(R,C)->(R+n,(n-1)-C)>   column-flip on row wrap.
// Each reduction below lands (R,C) on its unique representative in {0..n-1}^2.
// ---------------------------------------------------------------------------
function foldCell(topology, R, C, n) {
  if (topology === 'flat') {
    if (R < 0 || R >= n || C < 0 || C >= n) return null;
    return [R, C];
  }
  if (topology === 'torus') {
    return [((R % n) + n) % n, ((C % n) + n) % n];
  }
  if (topology === 'mobius') {
    // Rows are a free boundary: a target outside [0,n-1] leaves the band.
    if (R < 0 || R >= n) return null;
    const k = Math.floor(C / n);            // signed count of left/right seam crossings
    const c = C - k * n;                    // in [0,n-1]
    const r = (k % 2 !== 0) ? (n - 1 - R) : R;   // odd #crossings flips the row
    return [r, c];
  }
  if (topology === 'klein') {
    // Reduce rows first (each row-seam crossing flips the column), then columns.
    const kR = Math.floor(R / n);
    const r = R - kR * n;                   // in [0,n-1]
    let C2 = (kR % 2 !== 0) ? (n - 1 - C) : C;   // odd #row-crossings flips the column
    const kC = Math.floor(C2 / n);
    const c = C2 - kC * n;                   // in [0,n-1]
    return [r, c];
  }
  throw new Error('unknown topology ' + topology);
}

// The 8 leaper vectors (dr,dc) for an (a,b)-leaper: (±a,±b) and (±b,±a).
// For a==b this set collapses; our catalogued leapers all have a!=b.
function leaperVectors(a, b) {
  const s = new Set();
  for (const [p, q] of [[a, b], [b, a]])
    for (const sr of [1, -1])
      for (const sc of [1, -1])
        s.add(sr * p + ',' + sc * q);
  return [...s].map(t => t.split(',').map(Number));
}

// Cells a leaper at (i,j) attacks on `topology` (size n). Returns a Set of codes r*n+c.
function leaperAttacks(topology, i, j, n, vectors) {
  const out = new Set();
  const start = i * n + j;
  for (const [dr, dc] of vectors) {
    const cell = foldCell(topology, i + dr, j + dc, n);
    if (cell === null) continue;
    const code = cell[0] * n + cell[1];
    if (code !== start) out.add(code);
  }
  return out;
}

// Symmetric attack graph as BigInt bitmasks, exactly like nonorientable-queens.
function attackGraph(topology, n, vectors) {
  const V = n * n;
  const adj = new Array(V).fill(0n);
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const u = i * n + j;
      for (const w of leaperAttacks(topology, i, j, n, vectors)) {
        adj[u] |= (1n << BigInt(w));
        adj[w] |= (1n << BigInt(u));   // symmetrise
      }
    }
  }
  return adj;
}

// ---------------------------------------------------------------------------
// The permutation enumerator: count placements with exactly one piece per row
// and per column, no two attacking. Backtrack row by row over the attack graph.
// `placedMask` is a bitmask of occupied cells; `usedCols` a bitmask of columns.
// ---------------------------------------------------------------------------
function countPermutations(adj, n) {
  let total = 0;
  function rec(row, usedCols, placedMask) {
    if (row === n) { total++; return; }
    for (let c = 0; c < n; c++) {
      if ((usedCols >> BigInt(c)) & 1n) continue;
      const cell = row * n + c;
      if (adj[cell] & placedMask) continue;      // attacks a placed piece
      rec(row + 1, usedCols | (1n << BigInt(c)), placedMask | (1n << BigInt(cell)));
    }
  }
  rec(0, 0n, 0n);
  return total;
}

// Independent second path: same count, but choose a COLUMN for each row in a
// different traversal (iterate rows, but seat by scanning columns descending and
// tracking a plain array) — deliberately different control flow so a shared bug
// is unlikely to survive agreement. Uses integer arrays, no bitmask on cells.
function countPermutationsAlt(topology, n, vectors) {
  // Precompute, for each pair of rows and each column-of-row0, the set of columns
  // in the other row that are attacked. attackedCols[i][j] = array over rows r of
  // a boolean bitmask (as JS number ok for n<=30) of columns c' with (i,j)~(r,c').
  const V = n * n;
  const adj = attackGraph(topology, n, vectors);
  const colChoice = new Array(n).fill(-1);
  let total = 0;
  const usedCol = new Uint8Array(n);
  function rec(row) {
    if (row === n) { total++; return; }
    for (let c = n - 1; c >= 0; c--) {           // descending: different order
      if (usedCol[c]) continue;
      const cell = row * n + c;
      let ok = true;
      for (let r = 0; r < row; r++) {
        const other = r * n + colChoice[r];
        if ((adj[cell] >> BigInt(other)) & 1n) { ok = false; break; }
      }
      if (!ok) continue;
      usedCol[c] = 1; colChoice[row] = c; rec(row + 1); usedCol[c] = 0;
    }
  }
  rec(0);
  return total;
}

// Free-placement stats (bonus): total independent sets, max size, #max. Only for
// small n (leapers are sparse -> many independent sets -> DFS blows up quickly).
function independenceStats(adj, V) {
  let total = 0n, maxSize = 0, maxCount = 0n;
  function rec(start, size, forbidden) {
    total += 1n;
    if (size > maxSize) { maxSize = size; maxCount = 1n; }
    else if (size === maxSize && size > 0) { maxCount += 1n; }
    for (let v = start; v < V; v++) {
      if ((forbidden >> BigInt(v)) & 1n) continue;
      rec(v + 1, size + 1, forbidden | adj[v] | (1n << BigInt(v)));
    }
  }
  rec(0, 0, 0n);
  if (maxSize === 0) maxCount = 1n;
  return { total, maxSize, maxCount };
}

const LEAPERS = {
  knight: [1, 2], camel: [1, 3], zebra: [2, 3], giraffe: [1, 4],
};

function leaperSequence(topology, leaper, nlo, nhi) {
  const [a, b] = LEAPERS[leaper] || leaper;
  const vectors = leaperVectors(a, b);
  const out = [];
  for (let n = nlo; n <= nhi; n++) {
    const adj = attackGraph(topology, n, vectors);
    out.push(countPermutations(adj, n));
  }
  return out;
}

export {
  foldCell, leaperVectors, leaperAttacks, attackGraph,
  countPermutations, countPermutationsAlt, independenceStats,
  leaperSequence, LEAPERS,
};

// CLI: node engine.mjs <topology> <leaper|a b> <nlo> [nhi]
if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = process.argv.slice(2);
  const topo = argv[0] || 'mobius';
  let idx = 1, a, b, name;
  if (LEAPERS[argv[1]]) { [a, b] = LEAPERS[argv[1]]; name = argv[1]; idx = 2; }
  else { a = Number(argv[1]); b = Number(argv[2]); name = `(${a},${b})`; idx = 3; }
  const nlo = Number(argv[idx] ?? 1), nhi = Number(argv[idx + 1] ?? nlo);
  const vectors = leaperVectors(a, b);
  const seq = [];
  for (let n = nlo; n <= nhi; n++) {
    const adj = attackGraph(topo, n, vectors);
    seq.push(countPermutations(adj, n));
  }
  console.log(`${topo} ${name} n=${nlo}..${nhi}: ${seq.join(', ')}`);
}
