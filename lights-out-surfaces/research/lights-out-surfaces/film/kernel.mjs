// kernel.mjs — quiet patterns (kernel basis) and single-solve on top of the
// project's verified Lights-Out engine. It adds NO new mathematics: buildMatrix
// and the closed-neighbourhood rule are imported byte-for-byte from
// ../engine.mjs (the same file the stratum page and verifier trust), and this
// file only extracts an explicit kernel basis by the standard free-column
// construction over GF(2). Used by film.html (in the browser, served as a
// module) and by film-facts.mjs (offline gate). Deterministic.
import { buildMatrix, nullity } from '../engine.mjs';

// Reduced row echelon form over GF(2) on BigInt rows. Returns the reduced rows,
// the rank, and the ordered list of pivot columns.
function rref(rows0, N) {
  const rows = rows0.slice();
  let rank = 0;
  const pivCols = [];
  for (let col = 0; col < N && rank < N; col++) {
    const bit = 1n << BigInt(col);
    let piv = -1;
    for (let i = rank; i < N; i++) if (rows[i] & bit) { piv = i; break; }
    if (piv < 0) continue;
    [rows[rank], rows[piv]] = [rows[piv], rows[rank]];
    const pr = rows[rank];
    for (let i = 0; i < N; i++) if (i !== rank && (rows[i] & bit)) rows[i] ^= pr;
    pivCols.push(col);
    rank++;
  }
  return { rows, rank, pivCols };
}

// A basis of the kernel of M (the quiet patterns) for the n x n board on a
// surface. Each vector is a BigInt bitmask over the n*n buttons: bit j set means
// "press button j". Pressing every set button in a kernel vector changes nothing.
export function kernelBasis(n, surface) {
  const { rows: M, N } = buildMatrix(n, n, surface);
  const { rows, pivCols } = rref(M, N);
  const pivSet = new Set(pivCols);
  const rowForCol = {};
  let ri = 0;
  for (const col of pivCols) rowForCol[col] = ri++;
  const basis = [];
  for (let free = 0; free < N; free++) {
    if (pivSet.has(free)) continue;
    let v = 1n << BigInt(free);
    for (const col of pivCols) {
      if ((rows[rowForCol[col]] >> BigInt(free)) & 1n) v |= 1n << BigInt(col);
    }
    basis.push(v);
  }
  return basis; // length === nullity(n, surface)
}

// The set of light-indices toggled when the buttons in `mask` are all pressed,
// as a parity map over the closed neighbourhoods. Returned as a BigInt: bit i
// set means light i ended up flipped. For a kernel vector this must be 0n.
export function toggledBy(mask, n, surface) {
  const { rows, N } = buildMatrix(n, n, surface);
  // rows[i] has bit j set iff pressing button j toggles light i. So the light
  // vector is XOR over set buttons j of column j == (M symmetric) XOR of rows.
  let out = 0n;
  for (let j = 0; j < N; j++) {
    if ((mask >> BigInt(j)) & 1n) out ^= rows[j]; // M is symmetric: row j == column j
  }
  return out & ((1n << BigInt(N)) - 1n);
}

export { nullity };

// CLI: print a quiet pattern for a chosen board and prove it is quiet.
if (typeof process !== 'undefined' && process.argv && import.meta.url === `file://${process.argv[1]}`) {
  const n = parseInt(process.argv[2] || '5', 10);
  const s = process.argv[3] || 'plane';
  const basis = kernelBasis(n, s);
  const N = n * n;
  console.log(`${s} ${n}x${n}: nullity d = ${basis.length}`);
  basis.forEach((v, k) => {
    const changed = toggledBy(v, n, s);
    const cells = [];
    for (let i = 0; i < N; i++) if ((v >> BigInt(i)) & 1n) cells.push(i);
    console.log(`  quiet #${k}: ${cells.length} buttons ${JSON.stringify(cells)}  -> changes ${changed === 0n ? 'NOTHING ✓' : 'SOMETHING ✗'}`);
  });
}
