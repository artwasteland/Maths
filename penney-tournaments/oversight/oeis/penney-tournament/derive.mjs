// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/penney-tournament/derive.mjs
// Emits the staged Penney-tournament sequences and writes the OEIS b-files.
// Reproducible from a fresh checkout:  node oversight/oeis/penney-tournament/derive.mjs
// The underlying win-probabilities use Conway's leading-number formula, which is
// cross-validated against an independent first-principles Markov solver on EVERY
// pair (k<=6 in full, k=7 sampled) by research/penney-tournament/verify.mjs.

import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { patterns, pAfirst_conway, HALF, ONE } from '../../../research/penney-tournament/engine.mjs';

const here = dirname(fileURLToPath(import.meta.url));

// fast popcount over BigInt bitsets
const pc32 = (n) => { n = n - ((n >> 1) & 0x55555555); n = (n & 0x33333333) + ((n >> 2) & 0x33333333);
  n = (n + (n >> 4)) & 0x0f0f0f0f; return (n * 0x01010101) >> 24; };
const popc = (x) => { let c = 0; while (x > 0n) { c += pc32(Number(x & 0xffffffffn)); x >>= 32n; } return c; };
const bitlow = (v) => { let i = 0n, x = v & -v; while (x > 1n) { x >>= 1n; i++; } return i; };

function build(k, withCyc) {
  const S = patterns(k), n = S.length;
  const beats = new Array(n).fill(0n), loses = new Array(n).fill(0n);
  let ties = 0n;
  const probs = new Set();                          // distinct win-probability values
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const p = pAfirst_conway(S[i], S[j]);
    probs.add(p.s); probs.add(ONE.sub(p).s);
    const c = p.cmp(HALF);
    if (c > 0) { beats[i] |= 1n << BigInt(j); loses[j] |= 1n << BigInt(i); }
    else if (c < 0) { beats[j] |= 1n << BigInt(i); loses[i] |= 1n << BigInt(j); }
    else ties++;
  }
  let maxout = 0n;
  for (const x of beats) { const p = BigInt(popc(x)); if (p > maxout) maxout = p; }
  const distinctP = BigInt(probs.size);
  let cyc3 = null, transTri = null;
  if (withCyc) {                                   // directed 3-cycles (each counted 3 times)
    let cyc = 0n;
    for (let i = 0; i < n; i++) { const li = loses[i]; let v = beats[i];
      while (v > 0n) { const j = Number(bitlow(v)); v &= v - 1n; cyc += BigInt(popc(beats[j] & li)); } }
    cyc3 = cyc / 3n;
    // decided triples = triangles in the "decided" (non-tie) graph; each is cyclic or transitive.
    const dec = beats.map((b, i) => b | loses[i]);   // decided-neighbour bitset
    let decTri = 0n;
    for (let i = 0; i < n; i++) { let v = dec[i] >> BigInt(i + 1);  // only j>i
      let j = i + 1;
      while (v > 0n) { if (v & 1n) { const hi = dec[i] & dec[j] & (-(1n << BigInt(j + 1)));
        decTri += BigInt(popc(hi)); } v >>= 1n; j++; } }
    transTri = decTri - cyc3;                        // acyclic (transitive) decided triples
  }
  return { ties, maxout, cyc3, transTri, distinctP };
}

const TIES_MAX = 12, MAXOUT_MAX = 12, CYC3_MAX = 10, TRANS_MAX = 10, DISTP_MAX = 12;
const ties = [], maxout = [], cyc3 = [], transTri = [], distinctP = [];
const KMAX = Math.max(TIES_MAX, MAXOUT_MAX, CYC3_MAX, TRANS_MAX, DISTP_MAX);
for (let k = 1; k <= KMAX; k++) {
  const b = build(k, k <= Math.max(CYC3_MAX, TRANS_MAX));
  if (k <= TIES_MAX) ties.push(b.ties);
  if (k <= MAXOUT_MAX) maxout.push(b.maxout);
  if (k <= CYC3_MAX) cyc3.push(b.cyc3);
  if (k <= TRANS_MAX) transTri.push(b.transTri);
  if (k <= DISTP_MAX) distinctP.push(b.distinctP);
}

const bfile = (name, arr, off = 1) =>
  writeFileSync(join(here, name), arr.map((v, i) => `${i + off} ${v}`).join('\n') + '\n');
bfile('b-ties.txt', ties);
bfile('b-cyc3.txt', cyc3);
bfile('b-maxout.txt', maxout);
bfile('b-transtri.txt', transTri);
bfile('b-distinctp.txt', distinctP);

console.log('ties      (offset 1):', ties.join(', '));
console.log('cyc3      (offset 1):', cyc3.join(', '));
console.log('maxout    (offset 1):', maxout.join(', '));
console.log('transTri  (offset 1):', transTri.join(', '));
console.log('distinctP (offset 1):', distinctP.join(', '));
console.log('\nb-files written to', here);
