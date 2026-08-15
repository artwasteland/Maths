// research/penney-mary/verify.mjs — de-risks the m-ary Penney-tournament results.
//
//   1. CALIBRATION: generalized-Conway and the first-principles Markov solver must
//      agree on EVERY ordered pair's win-probability (full for small (m,k), sampled
//      for larger). Markov is first-principles; agreement validates the generalized
//      Conway leading-number formula empirically for m = 2..5.
//   2. HONESTY ANCHOR: the m = 2 invariants reproduce the PUBLISHED binary sequences
//      (research/penney-tournament) exactly — ties, cyc3, maxout. If these don't
//      match, nothing below is trusted.
//   3. MONTE-CARLO: a third, independent method (simulated races) agrees in sign
//      with the exact p(A,B) on a sample of pairs (the edge directions are real).
//   4. STRUCTURE: antisymmetry; the m! symbol-relabelling automorphisms; girth and
//      the two onset thresholds (nontransitivity vs first directed triangle).
//   5. The m-ary invariant tables that go outward are printed.
//
// Run: node research/penney-mary/verify.mjs

import {
  words, pAfirst_conway, pAfirst_markov, pAfirst_mc,
  tournament, invariants, girth, Q, ONE, HALF,
} from './engine.mjs';

let checks = 0, fails = 0;
const ok = (cond, msg) => { checks++; if (!cond) { fails++; console.log('  ✗ ' + msg); } };

// deterministic RNG (LCG) so the run is reproducible
const mkrng = (seed) => { let x = seed >>> 0; return () => (x = (x * 1103515245 + 12345) >>> 0) / 2 ** 32; };

// ============================================================================
// 1. CALIBRATION — generalized Conway vs first-principles Markov
// ============================================================================
console.log('1. Calibration — generalized Conway vs first-principles Markov:');
// full agreement on every ordered pair, for these (m,k):
const fullCal = [[2, 4], [2, 5], [3, 2], [3, 3], [4, 2], [5, 2]];
for (const [m, k] of fullCal) {
  const S = words(m, k); let mism = 0;
  for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++) {
    if (i === j) continue;
    if (!pAfirst_conway(m, S[i], S[j]).eq(pAfirst_markov(m, S[i], S[j]))) mism++;
  }
  ok(mism === 0, `m=${m},k=${k}: ${mism} Conway/Markov probability mismatches`);
  console.log(`   m=${m},k=${k}: all ${S.length * (S.length - 1)} ordered pairs agree exactly ✓`);
}
// sampled agreement at larger (m,k) where full Markov is heavy
const sampCal = [[3, 4], [4, 3], [5, 3]];
for (const [m, k] of sampCal) {
  const S = words(m, k); const rng = mkrng(20260621 + m * 100 + k); let mism = 0, tested = 0;
  for (let t = 0; t < 200; t++) {
    const A = S[(rng() * S.length) | 0], B = S[(rng() * S.length) | 0];
    if (A === B) continue; tested++;
    if (!pAfirst_conway(m, A, B).eq(pAfirst_markov(m, A, B))) mism++;
  }
  ok(mism === 0, `m=${m},k=${k} sample: ${mism}/${tested} mismatches`);
  console.log(`   m=${m},k=${k}: ${tested} random pairs cross-checked, ${mism} mismatch ✓`);
}

// ============================================================================
// 2. HONESTY ANCHOR — reproduce the PUBLISHED binary sequences exactly
// ============================================================================
console.log('\n2. Honesty anchor — reproduce the published m=2 (coin) sequences:');
// from research/penney-tournament (offset k=1):
const REF = {
  ties:   [1, 4, 10, 32, 120, 478, 1860, 7192, 28490],
  cyc3:   [0, 0, 0, 14, 182, 1790, 16792, 146894, 1208544],
  maxout: [0, 1, 4, 10, 22, 47, 97, 197, 398],
};
{
  const got = { ties: [], cyc3: [], maxout: [] };
  for (let k = 1; k <= 9; k++) {
    const inv = invariants(tournament(2, k));
    got.ties.push(inv.ties); got.cyc3.push(inv.cyc3); got.maxout.push(inv.maxout);
  }
  for (const key of ['ties', 'cyc3', 'maxout']) {
    const match = REF[key].every((v, i) => v === got[key][i]);
    ok(match, `binary ${key} must match published: got ${got[key].join(',')}`);
    console.log(`   ${key.padEnd(7)} = ${got[key].join(', ')}  ${match ? '✓ matches published' : '✗ MISMATCH'}`);
  }
}

// ============================================================================
// 3. MONTE-CARLO — a third method agrees in sign with exact p on a sample
// ============================================================================
console.log('\n3. Monte-Carlo — simulated races agree in sign with exact p(A,B):');
for (const [m, k] of [[3, 3], [4, 2]]) {
  const S = words(m, k); const rng = mkrng(777 + m + k); let bad = 0, tested = 0;
  for (let t = 0; t < 40; t++) {
    let A = S[(rng() * S.length) | 0], B = S[(rng() * S.length) | 0];
    if (A === B) continue;
    const p = pAfirst_conway(m, A, B);
    if (p.eq(HALF)) continue;                          // skip ties (sign undefined)
    tested++;
    const emp = pAfirst_mc(m, A, B, 4000, rng);
    // exact says A favoured iff p>1/2; empirical must agree (clear margin pairs)
    const exactA = p.cmp(HALF) > 0, empA = emp > 0.5;
    if (Math.abs(emp - 0.5) > 0.07 && exactA !== empA) bad++;
  }
  ok(bad === 0, `m=${m},k=${k}: ${bad}/${tested} Monte-Carlo sign disagreements`);
  console.log(`   m=${m},k=${k}: ${tested} pairs raced 4000x each, ${bad} sign disagreement ✓`);
}

// ============================================================================
// 4. STRUCTURE — antisymmetry, symbol-relabelling automorphisms, girth
// ============================================================================
console.log('\n4. Structure:');
// every relabelling of the m symbols is a tournament automorphism (the die is fair)
{
  const m = 3, k = 3, { S, rel } = tournament(m, k);
  const idx = new Map(S.map((s, i) => [s, i]));
  const perms = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]];
  let bad = 0, anti = 0;
  for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++) {
    if (rel[i][j] !== -rel[j][i]) anti++;
  }
  for (const P of perms) {
    const relabel = (w) => [...w].map((c) => P[+c]).join('');
    for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++)
      if (rel[i][j] !== rel[idx.get(relabel(S[i]))][idx.get(relabel(S[j]))]) bad++;
  }
  ok(anti === 0, `m=3,k=3: ${anti} antisymmetry violations`);
  ok(bad === 0, `m=3,k=3: ${bad} symbol-relabelling automorphism violations (all ${perms.length} perms)`);
  console.log(`   m=3,k=3: antisymmetric + invariant under all ${perms.length} symbol relabellings ✓`);
}
// girth + onsets, computed per (m,k)
console.log('\n   girth(T(m,k)) — length of the shortest directed cycle (∞ = acyclic):');
const onset = {};                       // m -> {nontrans:k, triangle:k}
for (const m of [2, 3, 4, 5]) {
  const KMAX = m === 2 ? 5 : m === 3 ? 4 : m === 4 ? 3 : 3;
  const row = [];
  onset[m] = { nontrans: null, triangle: null };
  for (let k = 1; k <= KMAX; k++) {
    const t = tournament(m, k);
    const gir = girth(t);
    row.push(gir === Infinity ? '∞' : gir);
    if (onset[m].nontrans === null && gir !== Infinity) onset[m].nontrans = k;
    if (onset[m].triangle === null && gir === 3) onset[m].triangle = k;
  }
  console.log(`     m=${m}: [${row.join(', ')}]   (k=1..${KMAX})`);
}
// the binary anchor: nontransitivity onsets at k=3, first triangle at k=4 (gap = 1)
ok(onset[2].nontrans === 3, `binary nontransitivity must onset at k=3 (got ${onset[2].nontrans})`);
ok(onset[2].triangle === 4, `binary first directed triangle must be at k=4 (got ${onset[2].triangle})`);
console.log('\n   onset table — first k with (any directed cycle) / (a directed triangle):');
for (const m of [2, 3, 4, 5]) {
  const o = onset[m];
  const gap = (o.triangle != null && o.nontrans != null) ? o.triangle - o.nontrans : '?';
  console.log(`     m=${m}: nontransitivity at k=${o.nontrans ?? '>range'}, triangle at k=${o.triangle ?? '>range'}, gap=${gap}`);
}

// ============================================================================
// 5. THE m-ARY INVARIANT TABLES (what goes outward)
// ============================================================================
console.log('\n5. Invariant tables by alphabet size m (offset k=1):');
const seq = {};                          // m -> {ties, cyc3, maxout, transTri, distinctP}
const RANGE = { 2: 9, 3: 6, 4: 5, 5: 4 };
for (const m of [2, 3, 4, 5]) {
  const s = { ties: [], cyc3: [], maxout: [], nMax: [], transTri: [], distinctP: [] };
  for (let k = 1; k <= RANGE[m]; k++) {
    const inv = invariants(tournament(m, k));
    for (const key of Object.keys(s)) s[key].push(inv[key]);
  }
  seq[m] = s;
  console.log(`\n   ── m = ${m} (alphabet/die size), k = 1..${RANGE[m]} ──`);
  console.log(`      n=m^k        : ${Array.from({ length: RANGE[m] }, (_, i) => m ** (i + 1)).join(', ')}`);
  console.log(`      ties(k)      : ${s.ties.join(', ')}`);
  console.log(`      cyc3(k)      : ${s.cyc3.join(', ')}`);
  console.log(`      maxout(k)    : ${s.maxout.join(', ')}  (×${s.nMax.join(', ')})`);
  console.log(`      transTri(k)  : ${s.transTri.join(', ')}`);
  console.log(`      distinctP(k) : ${s.distinctP.join(', ')}`);
}

// machine-readable dump for staging / the page
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const here = dirname(fileURLToPath(import.meta.url));
writeFileSync(join(here, 'results.json'), JSON.stringify({
  generated: new Date().toISOString().slice(0, 10),
  note: 'Penney dominance tournament over an m-symbol fair alphabet. cyc3=directed triangles, ties=tied pairs (p=1/2), maxout=max out-degree. Offset k=1.',
  onset, sequences: seq,
}, null, 2));

console.log(`\n${fails === 0 ? '✓ ALL' : '✗ ' + (checks - fails) + '/'} ${checks} checks ${fails === 0 ? 'PASS' : 'FAIL (' + fails + ' failed)'}`);
process.exit(fails === 0 ? 0 : 1);
