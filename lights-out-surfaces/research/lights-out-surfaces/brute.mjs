// brute.mjs — INDEPENDENT check of the nullity for small n by directly counting
// the kernel: enumerate every one of the 2^(n*n) button-press patterns, apply it
// to the all-OFF board under an INDEPENDENTLY CODED press rule (toggle each cell
// of the pressed button's closed neighbourhood), and count how many patterns
// leave the board unchanged. That count is exactly 2^nullity — the number of
// quiet patterns (the kernel). Comparing log2(count) to engine.mjs's nullity is a
// structurally different confirmation: no matrix, no Gaussian elimination, just
// the game's own toggle rule played out on every subset of buttons.
//
// Run:  node brute.mjs            (n=1..4, all surfaces)
//       node brute.mjs 5          (up to n=5; 2^25 patterns per surface ~ tens of s)

import { SURFACES, closedNeighbourhood } from './engine.mjs';

// Independent press-rule: build, for each button, the bitmask of cells it toggles,
// then count press-subsets that leave the board OFF. Shares no elimination code
// with engine.mjs — closedNeighbourhood is used only as the shared geometry oracle.
function bruteNullity(n, surface) {
  const N = n * n;
  const masks = [];
  for (let r = 0; r < n; r++)
    for (let c = 0; c < n; c++) {
      let mask = 0n;
      for (const i of closedNeighbourhood(r, c, n, n, surface)) mask |= 1n << BigInt(i);
      masks.push(mask);
    }
  // Enumerate all 2^N press-subsets via Gray code so each step flips one button.
  let quiet = 0;
  let board = 0n;          // XOR of masks of currently-pressed buttons
  let prevGray = 0;
  const total = 1 << N;    // N <= 25 keeps this in 32-bit range
  for (let k = 0; k < total; k++) {
    const gray = k ^ (k >> 1);
    if (k > 0) {
      const changed = gray ^ prevGray;      // exactly one bit
      const b = Math.log2(changed) | 0;     // which button toggled
      board ^= masks[b];
    }
    prevGray = gray;
    if (board === 0n) quiet++;
  }
  // quiet = 2^nullity
  let d = 0, q = quiet;
  while (q > 1) { q >>= 1; d++; }
  if ((1 << d) !== quiet) throw new Error(`quiet=${quiet} not a power of two (${surface} n=${n})`);
  return d;
}

const NMAX = parseInt(process.argv[2] || '4', 10);
for (let n = 1; n <= NMAX; n++) {
  const row = SURFACES.map(s => `${s.slice(0, 4)}=${bruteNullity(n, s)}`).join('  ');
  console.log(`n=${n}:  ${row}`);
}
