// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/many-symbol-penney/derive.mjs
// Emits the many-symbol Penney dominance-tournament invariant sequences and writes
// the OEIS b-files. Reproducible from a fresh checkout:
//     node oversight/oeis/many-symbol-penney/derive.mjs
//
// The underlying win-probabilities use Conway's leading-number formula with base-q
// leading numbers, cross-validated against an independent first-principles
// absorbing-Markov linear solver on every pair (q=3,4; k<=3 full, k=4 sampled) by
// research/many-symbol-penney/verify.mjs, which ALSO reproduces the published binary
// (q=2) sequences exactly as a calibration against known ground truth.
//
// Sequences staged (indexed by word length k, offset 1):
//   q=3 (three-sided die), k=1..7:  cyc3, transTri, ties, maxout, distinctP
//   q=4 (four-sided die),  k=1..5:  cyc3, transTri, ties, maxout, distinctP

import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tournament, invariants } from '../../../research/many-symbol-penney/engine.mjs';

const here = dirname(fileURLToPath(import.meta.url));

function seqs(q, kmax) {
  const out = { cyc3: [], transTri: [], ties: [], maxout: [], distinctP: [] };
  for (let k = 1; k <= kmax; k++) {
    const inv = invariants(tournament(k, q));
    out.cyc3.push(inv.cyc3); out.transTri.push(inv.transTri);
    out.ties.push(inv.ties); out.maxout.push(inv.maxout); out.distinctP.push(inv.distinctP);
    process.stderr.write(`  q=${q} k=${k} done\n`);
  }
  return out;
}

function writeB(name, arr) {
  const body = arr.map((v, i) => `${i + 1} ${v}`).join('\n') + '\n';
  writeFileSync(join(here, `b-${name}.txt`), body);
  console.log(`  wrote b-${name}.txt  (${arr.length} terms):  ${arr.join(', ')}`);
}

console.log('q=3 (three-sided die), k=1..7:');
const q3 = seqs(3, 7);
writeB('q3-cyc3', q3.cyc3);
writeB('q3-transtri', q3.transTri);
writeB('q3-ties', q3.ties);
writeB('q3-maxout', q3.maxout);
writeB('q3-distinctp', q3.distinctP);

console.log('\nq=4 (four-sided die), k=1..5:');
const q4 = seqs(4, 5);
writeB('q4-cyc3', q4.cyc3);
writeB('q4-transtri', q4.transTri);
writeB('q4-ties', q4.ties);
writeB('q4-maxout', q4.maxout);
writeB('q4-distinctp', q4.distinctP);

console.log('\nAll b-files written. Absence from OEIS was confirmed 2026-07-05 (each searched');
console.log('at https://oeis.org/search?q=<terms> → "No results"). Re-check before any submission.');
