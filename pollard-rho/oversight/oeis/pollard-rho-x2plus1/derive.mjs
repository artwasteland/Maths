// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// derive.mjs — regenerate the b-files for the three sequences staged here.
// Run: node oversight/oeis/pollard-rho-x2plus1/derive.mjs [Nper] [Nsum]
//   Nper — terms for the per-modulus x²+1 sequences (default 1000)
//   Nsum — terms for the Σ_c sequences (default 400; these are O(n²) per term)
//
// All counts are EXACT integer enumerations of the functional graph of x²+c mod n.
// The engine is the same one verified in research/pollard-rho/verify.mjs (26/26),
// where analyze() is cross-checked against an independent brute force for all n≤200.
//
// THIS IS A PRODUCER, NOT A CHECK. Running it overwrites all three staged b-files,
// so it can never confirm them: it can only make them agree with whatever the engine
// says today. The check is oversight/oeis/pollard-rho-x2plus1/verify-staged.mjs,
// which reads the staged bytes and recomputes all 1,800 terms two ways. If that gate
// ever disagrees with a staged term, do NOT run this script: the disagreement is a
// finding to report, and regenerating the file would destroy the evidence.

import { analyze } from '../../../research/pollard-rho/engine.mjs';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const Nper = Number(process.argv[2] || 1000);
const Nsum = Number(process.argv[3] || 400);

function bfile(name, fn, N) {
  const lines = [];
  for (let n = 1; n <= N; n++) lines.push(`${n} ${fn(n)}`);
  writeFileSync(join(here, name), lines.join('\n') + '\n');
  console.log(`${name}: ${N} terms — first 12: ${Array.from({ length: 12 }, (_, i) => fn(i + 1)).join(',')}`);
}

// 1. Periodic points of x²+1 mod n  (sibling of A352635 = its cycle count)
bfile('b-periodic-x2plus1.txt', (n) => analyze(n, 1).periodic, Nper);

// 2. Σ over c=0..n-1 of (periodic points of x²+c mod n)
bfile('b-sum-periodic.txt', (n) => { let s = 0; for (let c = 0; c < n; c++) s += analyze(n, c).periodic; return s; }, Nsum);

// 3. Σ over c=0..n-1 of (cycles of x²+c mod n)
bfile('b-sum-cycles.txt', (n) => { let s = 0; for (let c = 0; c < n; c++) s += analyze(n, c).cycles; return s; }, Nsum);

console.log('\nb-files written.');
