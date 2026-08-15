// ca-garden-of-eden — verifier. Never one path.
//
// Run: node research/ca-garden-of-eden/verify.mjs
//
// Establishes, by independent methods that must agree, the Garden-of-Eden counts
// GoE_R(n) = 2^n - |image(F_R on the ring of length n)| for elementary CA rules R.
//
// Cross-checks:
//   (A) BRUTE FORCE (enumerate all 2^n configs, apply F_R, count distinct images)
//   (B) TRANSFER MATRIX over the de Bruijn transition monoid (big-int, all n)
//   (C) SUBSET-DFS predecessor finder (a third, per-configuration method)
// must all agree, and every non-orphan witness must reproduce its target under one step.
//
// Positive controls (established facts the machinery must reproduce):
//   * the SIX reversible elementary rules {15,51,85,170,204,240} are bijective on every
//     ring, so GoE_R(n)=0 for all n (no orphans, ever);
//   * constant rules 0 and 255 have image {one fixed config}, so GoE(n) = 2^n - 1;
//   * the identity rule 204 has image = everything, GoE(n)=0;
//   * linear rule 150 (XOR of all three) has GoE(n)>0 exactly when 3 | n (observed law);
//   * the headline new values reproduce the recorded b-file data exactly.

'use strict';
import {
  bruteImageGoE, goeSizes, imageSizes, findPredecessor, step, localMap,
} from './engine.mjs';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log(`  ok   ${name}`); }
  else { fail++; console.log(`  FAIL ${name}`, extra ?? ''); }
};

console.log(`node ${process.version}\n`);

// ---------------------------------------------------------------------------
console.log('POSITIVE CONTROLS');

// (1) the six reversible ECAs are bijective on every ring => GoE(n)=0 for all n.
{
  const REV = [15, 51, 85, 170, 204, 240];
  let good = true, why = '';
  for (const r of REV) {
    const g = goeSizes(r, 24).slice(1);
    if (g.some(v => v !== 0n)) { good = false; why = `rule ${r} has an orphan`; break; }
  }
  ok('the 6 reversible ECAs {15,51,85,170,204,240} give GoE(n)=0 for all n (n<=24)', good, why);
}

// (2) constant rules 0 and 255: image is a single fixed config => GoE(n) = 2^n - 1.
{
  let good = true;
  for (const r of [0, 255]) {
    for (let n = 1; n <= 22; n++) {
      const want = (1n << BigInt(n)) - 1n;
      if (goeSizes(r, n)[n] !== want) { good = false; break; }
    }
  }
  ok('constant rules 0 and 255 give GoE(n) = 2^n - 1 (n<=22)', good);
}

// (3) linear rule 150 (and its complement 105): GoE(n) > 0 exactly when 3 | n.
{
  for (const r of [150, 105]) {
    const g = goeSizes(r, 24).slice(1); // g[i] = GoE(i+1)
    let good = true;
    for (let n = 1; n <= 24; n++) {
      const nonzero = g[n - 1] !== 0n;
      if (nonzero !== (n % 3 === 0)) { good = false; break; }
    }
    ok(`linear rule ${r}: GoE(n) > 0  <=>  3 | n  (observed, n<=24)`, good);
  }
}

// (4) the local-rule bit extraction is the standard Wolfram numbering:
//     rule 90 = x_{i-1} XOR x_{i+1}; rule 110 truth table 0,1,1,1,0,1,1,0.
{
  const f110 = localMap(110);
  const tt110 = [];
  for (let a = 0; a < 2; a++) for (let b = 0; b < 2; b++) for (let c = 0; c < 2; c++) tt110.push(f110(a, b, c));
  // Wolfram: neighbourhood 111->? bit7 ... 000->bit0. rule 110 = 0b01101110.
  // our tt110 is indexed a,b,c ascending = neighbourhood value 4a+2b+c = 0..7 => bits 0..7 of R.
  const asRule = tt110.reduce((acc, bit, k) => acc | (bit << k), 0);
  ok('local-map uses standard Wolfram numbering (rule 110 truth table round-trips)', asRule === 110, `got ${asRule}`);

  const f90 = localMap(90);
  let xorOk = true;
  for (let a = 0; a < 2; a++) for (let b = 0; b < 2; b++) for (let c = 0; c < 2; c++) if (f90(a, b, c) !== (a ^ c)) xorOk = false;
  ok('rule 90 == x_{i-1} XOR x_{i+1}', xorOk);
}

// ---------------------------------------------------------------------------
console.log('\nCROSS-METHOD AGREEMENT (brute force == transfer matrix)');
const FEATURED = [30, 110, 184, 22, 126, 54, 146, 90, 150, 45, 60, 105, 30];
{
  const NB = 20; // brute-force ceiling for the sweep
  let good = true, why = '';
  for (const r of [...new Set(FEATURED)]) {
    const gt = goeSizes(r, NB);
    for (let n = 1; n <= NB; n++) {
      const b = BigInt(bruteImageGoE(r, n).goe);
      if (b !== gt[n]) { good = false; why = `rule ${r} n=${n}: brute=${b} transfer=${gt[n]}`; break; }
    }
    if (!good) break;
  }
  ok(`brute force == transfer matrix, GoE for all featured rules, n=1..${NB}`, good, why);
}

// deeper single-rule brute check for the headline (rule 30), n up to 24
{
  let good = true, why = '';
  const gt = goeSizes(30, 24);
  for (let n = 21; n <= 24; n++) {
    const b = BigInt(bruteImageGoE(30, n).goe);
    if (b !== gt[n]) { good = false; why = `n=${n}: brute=${b} transfer=${gt[n]}`; break; }
  }
  ok('rule 30: brute == transfer for n=21..24 (2^24 enumeration)', good, why);
}

// ---------------------------------------------------------------------------
console.log('\nTHIRD METHOD (subset-DFS predecessor finder) == brute image membership');
{
  let good = true, why = '';
  for (const r of [30, 110, 184, 22, 126, 54, 146, 90, 45]) {
    for (let n = 1; n <= 13 && good; n++) {
      const img = new Set();
      for (let x = 0; x < (1 << n); x++) img.add(step(r, n, x));
      let orphanCount = 0;
      for (let y = 0; y < (1 << n); y++) {
        const fp = findPredecessor(r, n, y);
        const inImg = img.has(y);
        if (fp.orphan === inImg) { good = false; why = `rule ${r} n=${n} y=${y}: DFS orphan=${fp.orphan} brute inImage=${inImg}`; break; }
        if (!fp.orphan && step(r, n, fp.predecessor) !== y) { good = false; why = `rule ${r} n=${n} y=${y}: bad witness`; break; }
        if (fp.orphan) orphanCount++;
      }
      if (!good) break;
      const gt = Number(goeSizes(r, n)[n]);
      if (orphanCount !== gt) { good = false; why = `rule ${r} n=${n}: DFS orphan count ${orphanCount} != ${gt}`; }
    }
    if (!good) break;
  }
  ok('subset-DFS orphan/predecessor == brute (rules 30,110,184,22,126,54,146,90,45; n<=13; witnesses verified)', good, why);
}

// ---------------------------------------------------------------------------
console.log('\nRECORDED DATA (b-files reproduce the engine, if present)');
function readBfile(path) {
  if (!existsSync(path)) return null;
  const rows = readFileSync(path, 'utf8').split('\n').filter(l => l.trim() && !l.startsWith('#'));
  const m = new Map();
  for (const row of rows) { const [n, v] = row.trim().split(/\s+/); m.set(Number(n), BigInt(v)); }
  return m;
}
{
  const OEIS = join(HERE, '..', '..', 'oversight', 'oeis', 'ca-garden-of-eden');
  const files = [
    ['b-rule30-goe.txt', 30, 'goe'],
    ['b-rule30-image.txt', 30, 'image'],
    ['b-rule110-goe.txt', 110, 'goe'],
    ['b-rule184-goe.txt', 184, 'goe'],
    ['b-rule22-goe.txt', 22, 'goe'],
    ['b-rule126-goe.txt', 126, 'goe'],
    ['b-rule54-goe.txt', 54, 'goe'],
    ['b-rule146-goe.txt', 146, 'goe'],
  ];
  for (const [fname, rule, kind] of files) {
    const bf = readBfile(join(OEIS, fname));
    if (!bf) { ok(`${fname} matches engine`, false, 'b-file MISSING (run gen-data.mjs)'); continue; }
    const maxN = Math.max(...bf.keys());
    const series = kind === 'goe' ? goeSizes(rule, maxN) : imageSizes(rule, maxN);
    let good = true, why = '';
    for (const [n, v] of bf) if (series[n] !== v) { good = false; why = `n=${n}: file=${v} engine=${series[n]}`; break; }
    ok(`${fname} matches engine (n=1..${maxN})`, good, why);
  }
}

// ---------------------------------------------------------------------------
console.log('\nOBSERVED PHENOMENON (rule 30 orphan density -> 0 while count -> infinity)');
{
  const img = imageSizes(30, 40);
  const goe = goeSizes(30, 40);
  // density of orphans is strictly decreasing over n=10..40 (observed) and count strictly increasing
  let densDown = true, countUp = true;
  let prevDens = Infinity, prevCount = -1n;
  for (let n = 10; n <= 40; n++) {
    const dens = Number(goe[n] * 1000000n / (1n << BigInt(n))) / 1000000;
    if (dens >= prevDens) densDown = false;
    if (goe[n] <= prevCount) countUp = false;
    prevDens = dens; prevCount = goe[n];
    void img;
  }
  ok('rule 30: orphan DENSITY strictly decreasing, n=10..40 (observed)', densDown);
  ok('rule 30: orphan COUNT strictly increasing, n=10..40 (observed)', countUp);
  const d40 = Number(goe[40] * 1000000n / (1n << 40n)) / 1000000;
  console.log(`       (at n=40: ${goe[40]} orphans, density ${d40.toFixed(6)})`);
}

// ---------------------------------------------------------------------------
console.log(`\n${pass}/${pass + fail} checks passed`);
if (fail) process.exit(1);
