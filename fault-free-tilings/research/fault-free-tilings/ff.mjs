// ─────────────────────────────────────────────────────────────────────────────
// Fault-free domino tilings of the m × n rectangle — the exact engine.
//
//   FF(m,n) = number of tilings of an m-row × n-col rectangle by 1×2 dominoes
//   such that NO "fault line" exists: no straight horizontal or vertical line
//   spanning the whole rectangle can be drawn without slicing through a domino.
//   (A fault line is a structural weakness — the reason a bricklayer staggers
//   courses instead of stacking them. See README.md.)
//
// Two exports:
//   T(h,n)  — ALL domino tilings of h×n (broken-profile transfer matrix, exact
//             BigInt). Anchor: T(8,8)=12988816 (A004003), T(2,n)=Fibonacci.
//   FF(m,n) — fault-free tilings, via inclusion–exclusion over the fault lines,
//             collapsed onto the integer PARTITIONS of m (so the cost is the
//             number of partitions of m, not 2^(m-1)).
//
// The whole file is BigInt-exact and deterministic. It is checked, offline and
// two independent ways, by verify.mjs.
// ─────────────────────────────────────────────────────────────────────────────

// ── T(h,n): every domino tiling of an h×n board ──────────────────────────────
// Broken-profile DP, cell by cell in column-major order. State = bitmask of the
// next h cells' fill status; a set bit means "already covered by a horizontal
// domino protruding from the previous column."
const Tcache = new Map();
export function T(h, n) {
  if ((h * n) & 1) return 0n;                 // odd area ⇒ no tiling
  const key = h + "," + n;
  const hit = Tcache.get(key);
  if (hit !== undefined) return hit;
  let dp = new Map([[0, 1n]]);                 // Number mask → BigInt count
  for (let col = 0; col < n; col++) {
    for (let row = 0; row < h; row++) {
      const ndp = new Map();
      const bit = 1 << row;
      for (const [mask, cnt] of dp) {
        if (mask & bit) {                       // cell already covered ⇒ skip it
          const nm = mask & ~bit;
          ndp.set(nm, (ndp.get(nm) || 0n) + cnt);
        } else {
          // vertical domino downward (needs the cell below empty and in range)
          if (row + 1 < h && !(mask & (bit << 1))) {
            const nm = mask | (bit << 1);
            ndp.set(nm, (ndp.get(nm) || 0n) + cnt);
          }
          // horizontal domino rightward (protrudes into the next column)
          if (col + 1 < n) {
            const nm = mask | bit;
            ndp.set(nm, (ndp.get(nm) || 0n) + cnt);
          }
        }
      }
      dp = ndp;
    }
  }
  const r = dp.get(0) || 0n;
  Tcache.set(key, r);
  return r;
}

// ── the integer partitions of m (each as a descending list of parts) ─────────
function* partitions(m, max = m) {
  if (m === 0) { yield []; return; }
  for (let p = Math.min(m, max); p >= 1; p--)
    for (const rest of partitions(m - p, p)) yield [p, ...rest];
}
function factorial(n) { let f = 1n; for (let i = 2n; i <= BigInt(n); i++) f *= i; return f; }
// number of ORDERED compositions whose part-multiset is `parts`
function compositionCount(parts) {
  const mult = {};
  for (const p of parts) mult[p] = (mult[p] || 0) + 1;
  let d = factorial(parts.length);
  for (const k in mult) d /= factorial(mult[k]);
  return d;
}

// ── FF(m,n): fault-free count, via inclusion–exclusion ───────────────────────
//
// A tiling has some set of horizontal fault lines R ⊆ {1..m-1} and vertical fault
// lines. The number of tilings whose horizontal faults ⊇ R is a product over the
// horizontal strips R cuts the board into (each strip tiled freely). Sieving out
// vertical faults inside a strip-stack is a 1-D deconvolution along the width.
//
//   For a fixed multiset of strip heights (a partition of m):
//     P(k) = ∏_i T(h_i, k)                                        (all fillings)
//     G(k) = P(k) − Σ_{j<k} G(j) P(k-j)   (fillings with no SHARED vertical fault)
//   FF(m,n) = Σ_{partitions λ of m} (#compositions with multiset λ)
//                                    · (−1)^(parts(λ)−1) · G_λ(n)
//
// Grouping by partition (not iterating all 2^(m-1) subsets R) is what makes large
// m fast: the deconvolution G depends only on the multiset of strip heights.
export function FF(m, n) {
  let total = 0n;
  for (const parts of partitions(m)) {
    const q = parts.length;
    const sign = (q - 1) & 1 ? -1n : 1n;
    const cnt = compositionCount(parts);
    const P = new Array(n + 1);
    for (let k = 0; k <= n; k++) {
      let p = 1n;
      for (const h of parts) p *= (k === 0 ? 1n : T(h, k));
      P[k] = p;
    }
    const G = new Array(n + 1);
    G[0] = 1n;
    for (let k = 1; k <= n; k++) {
      let g = P[k];
      for (let j = 1; j < k; j++) g -= G[j] * P[k - j];
      G[k] = g;
    }
    total += sign * cnt * G[n];
  }
  return total;
}

// ── VFF(m,n): tilings with no VERTICAL fault (horizontal faults allowed) ──────
// The single-partition (R=∅) case of the deconvolution — used to cross-check
// against OEIS A232621 (vertically fault-free 5×2n).
export function VFF(m, n) {
  const P = new Array(n + 1);
  for (let k = 0; k <= n; k++) P[k] = (k === 0 ? 1n : T(m, k));
  const G = new Array(n + 1);
  G[0] = 1n;
  for (let k = 1; k <= n; k++) {
    let g = P[k];
    for (let j = 1; j < k; j++) g -= G[j] * P[k - j];
    G[k] = g;
  }
  return G[n];
}
