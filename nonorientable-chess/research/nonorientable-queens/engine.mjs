// research/nonorientable-queens/engine.mjs
//
// Non-attacking piece placements on four board topologies, by exact enumeration.
//
//   flat    — the ordinary board (no edges glued).            queens -> A000170
//   torus   — both edge-pairs glued straight (modular board). queens -> A007705
//   mobius  — left/right edges glued with a vertical FLIP.    queens -> A137279  (Bell & Stevens 2008)
//   klein   — left/right glued straight, top/bottom glued     queens -> (absent from OEIS)
//             with a horizontal flip.
//
// The whole correctness argument rests on ONE idea: instead of transcribing each
// surface's (board-shape-dependent) diagonal carry-over algebra, we RAY-TRACE a
// piece's lines of attack one square at a time, applying an explicit, geometric
// seam rule when a ray crosses a glued edge. The ray-tracer is then validated by
// reproducing THREE independently-published sequences (flat, torus, Mobius) exactly.
// Any surface that reproduces those cannot have a wrong attack model; the Klein
// results are produced by the SAME traced code with the Klein identification.
//
// Coordinates follow Bell & Stevens: rows i = 0..m-1 (top to bottom), columns
// j = 0..n-1 (left to right); square (i,j). We use square boards m = n throughout
// (the published sequences are the square diagonal of the m x n family).

// ---------------------------------------------------------------------------
// The seam rule. cross(topology, r, c, dr, dc, n) advances ONE square from (r,c)
// heading (dr,dc) and returns the next square + possibly-updated direction, or
// null if the ray leaves the board (falls off an unglued edge). n = board size.
//
// Geometry of each gluing, for a step that would land at column c+dc / row r+dr:
//   flat  : no wrap. Off any edge -> ray ends.
//   torus : columns wrap mod n, rows wrap mod n. Direction never changes.
//   mobius: columns are glued with a vertical flip. Crossing the left/right seam
//           reflects the row (r -> n-1-r for the square being entered) and flips
//           the vertical direction (dr -> -dr). Rows do NOT wrap (top/bottom are
//           free boundary). This realises "a row i carries over to row n-1-i".
//   klein : columns wrap straight (like the torus). Rows are glued with a
//           horizontal flip: crossing the top/bottom seam reflects the column
//           (c -> n-1-c for the square being entered) and flips the horizontal
//           direction (dc -> -dc).
// ---------------------------------------------------------------------------
function step(topology, r, c, dr, dc, n) {
  let nr = r + dr, nc = c + dc;
  let ndr = dr, ndc = dc;

  if (topology === 'flat') {
    if (nr < 0 || nr >= n || nc < 0 || nc >= n) return null;
    return [nr, nc, ndr, ndc];
  }

  if (topology === 'torus') {
    nr = ((nr % n) + n) % n;
    nc = ((nc % n) + n) % n;
    return [nr, nc, ndr, ndc];
  }

  if (topology === 'mobius') {
    // vertical (row) direction is a free boundary: no wrap
    if (nc >= 0 && nc < n) {
      if (nr < 0 || nr >= n) return null;
      return [nr, nc, ndr, ndc];
    }
    // crossed the left/right seam -> Mobius twist
    nc = ((nc % n) + n) % n;
    nr = (n - 1) - nr;      // reflect the row being entered
    ndr = -ndr;             // vertical direction flips with the strip
    if (nr < 0 || nr >= n) return null;  // (defensive; nr is in range after reflect)
    return [nr, nc, ndr, ndc];
  }

  if (topology === 'klein') {
    // columns wrap straight
    if (nr >= 0 && nr < n) {
      nc = ((nc % n) + n) % n;
      return [nr, nc, ndr, ndc];
    }
    // crossed the top/bottom seam -> Klein twist (horizontal flip)
    nr = ((nr % n) + n) % n;
    nc = (n - 1) - nc;      // reflect the column being entered
    ndc = -ndc;             // horizontal direction flips
    nc = ((nc % n) + n) % n;
    return [nr, nc, ndr, ndc];
  }

  throw new Error('unknown topology ' + topology);
}

// The 8 queen ray directions (rook + bishop); kings use the same 8 but distance 1.
const DIRS = [
  [-1, 0], [1, 0], [0, -1], [0, 1],
  [-1, -1], [-1, 1], [1, -1], [1, 1],
];

// Trace every square a QUEEN at (i,j) attacks on `topology` (size n). Returns a
// Set of encoded squares (r*n+c). A ray is followed until it leaves the board or
// returns to the queen's own square (a closed geodesic on a glued surface).
function queenAttacks(topology, i, j, n) {
  const out = new Set();
  const start = i * n + j;
  for (const [dr0, dc0] of DIRS) {
    let r = i, c = j, dr = dr0, dc = dc0;
    for (let guard = 0; guard < 8 * n * n + 8; guard++) {
      const nx = step(topology, r, c, dr, dc, n);
      if (nx === null) break;
      [r, c, dr, dc] = nx;
      const code = r * n + c;
      if (code === start) break;   // closed loop
      out.add(code);
      // a piece never "attacks itself"; keep tracing (queens slide arbitrarily far)
    }
  }
  out.delete(start);
  return out;
}

// A KING at (i,j) attacks its (up to 8) immediate neighbours under the same gluing.
function kingAttacks(topology, i, j, n) {
  const out = new Set();
  const start = i * n + j;
  for (const [dr, dc] of DIRS) {
    const nx = step(topology, i, j, dr, dc, n);
    if (nx === null) continue;
    const code = nx[0] * n + nx[1];
    if (code !== start) out.add(code);
  }
  return out;
}

// Build the symmetric attack graph as an array of BigInt bitmasks (one per square):
// adj[v] has bit w set iff a piece on v attacks a piece on w. We symmetrise
// explicitly (u attacks v OR v attacks u) so "non-attacking" is well defined even
// if a raw ray model were ever asymmetric; validation asserts it already is.
function attackGraph(topology, n, piece) {
  const V = n * n;
  const raw = [];
  const atk = piece === 'king' ? kingAttacks : queenAttacks;
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++)
      raw[i * n + j] = atk(topology, i, j, n);
  const adj = new Array(V).fill(0n);
  for (let u = 0; u < V; u++) {
    for (const w of raw[u]) {
      adj[u] |= (1n << BigInt(w));
      adj[w] |= (1n << BigInt(u));   // symmetrise
    }
  }
  return adj;
}

// ---------------------------------------------------------------------------
// Enumerators over the attack graph. All exact; all count UNORDERED placements.
// ---------------------------------------------------------------------------

// Count non-attacking placements of exactly k pieces (independent sets of size k).
// Ordered vertex choice (strictly increasing index) => each set counted once.
function countExactK(adj, V, k) {
  let total = 0;
  const forb = new Array(k + 1);
  // DFS choosing vertices in increasing order.
  function rec(start, placed, forbidden) {
    if (placed === k) { total++; return; }
    // prune: need at least (k-placed) more allowed vertices >= start
    for (let v = start; v <= V - (k - placed); v++) {
      if ((forbidden >> BigInt(v)) & 1n) continue;
      rec(v + 1, placed + 1, forbidden | adj[v] | (1n << BigInt(v)));
    }
  }
  void forb;
  rec(0, 0, 0n);
  return total;
}

// Count ALL independent sets (any size, including empty) and, at the same time,
// the maximum independent-set size and how many sets achieve it. Single DFS.
function independenceStats(adj, V) {
  let total = 0n;         // total independent sets (incl. empty)
  let maxSize = 0, maxCount = 0n;
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
  // maxCount for maxSize 0 (only when V=0) — handle trivially
  if (maxSize === 0) maxCount = 1n;
  return { total, maxSize, maxCount };
}

// Convenience: the k-in-a-family counts as an array a(n) for n in [nlo,nhi].
function sequenceExactK(topology, piece, nlo, nhi, kOf) {
  const out = [];
  for (let n = nlo; n <= nhi; n++) {
    const adj = attackGraph(topology, n, piece);
    out.push(countExactK(adj, n * n, kOf(n)));
  }
  return out;
}

export {
  step, DIRS, queenAttacks, kingAttacks, attackGraph,
  countExactK, independenceStats, sequenceExactK,
};

// CLI: node engine.mjs <topology> <piece> <n> [k]
if (import.meta.url === `file://${process.argv[1]}`) {
  const [, , topo = 'mobius', piece = 'queen', nStr = '6', kStr] = process.argv;
  const n = Number(nStr);
  const adj = attackGraph(topo, n, piece);
  if (kStr !== undefined) {
    const k = Number(kStr);
    console.log(`${topo} ${piece} n=${n} k=${k}: ${countExactK(adj, n * n, k)}`);
  } else {
    const s = independenceStats(adj, n * n);
    console.log(`${topo} ${piece} n=${n}: total independent sets = ${s.total}, max = ${s.maxSize}, #max = ${s.maxCount}`);
  }
}
