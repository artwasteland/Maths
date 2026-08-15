// research/penney-tournament/verify-structure.mjs
//
// Rigorously assert every STRUCTURAL claim the whirlpool section makes, from the
// same doubly-verified engine (Conway <-> Markov, verify.mjs 49/49). Everything
// here is exact; the only one-sided part is pancyclicity for k>=5, which is
// proven by EXHIBITED, edge-verified witnesses (existence, never absence).
//
//   node research/penney-tournament/verify-structure.mjs

import { tournament, invariants } from './engine.mjs';
import { structure } from './structure.mjs';
import { pancyclicWitnesses } from './pancyclic.mjs';

let pass = 0, fail = 0;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function check(name, got, want) {
  const ok = eq(got, want);
  if (ok) pass++; else { fail++; console.log(`  ✗ ${name}\n      got : ${JSON.stringify(got)}\n      want: ${JSON.stringify(want)}`); return; }
  console.log(`  ✓ ${name}`);
}
function ok(name, cond) { if (cond) { pass++; console.log(`  ✓ ${name}`); } else { fail++; console.log(`  ✗ ${name}`); } }

console.log('\nA) The three strongly-connected components (exact, Tarjan) — k = 1..10');
// Expected: k=1 -> {isolated}; k=2 -> all singletons; k=3 -> giant 4 + 4 singletons (2 of them sinks);
//           k>=4 -> exactly {giant 2^k-2, two singleton sinks}.
for (let k = 1; k <= 10; k++) {
  const r = structure(k, { doCycles: false });
  if (k >= 4) {
    check(`k=${k}: SCC sizes = [2^k-2, 1, 1]`, r.sccSizes, [(1 << k) - 2, 1, 1]);
    ok(`k=${k}: giant strongly-connected of size 2^k-2 = ${(1 << k) - 2}`, r.giant === (1 << k) - 2);
    check(`k=${k}: the two sinks are the constant runs`, r.sinks.slice().sort(), ['H'.repeat(k), 'T'.repeat(k)].sort());
    ok(`k=${k}: no sources (every pattern is beaten by some pattern)`, r.sources.length === 0);
  }
}
check('k=3: SCC sizes = [4,1,1,1,1] (lone 4-cycle + 4 strays)', structure(3).sccSizes, [4, 1, 1, 1, 1]);
check('k=3: sinks = {HHH, TTT}', structure(3).sinks.slice().sort(), ['HHH', 'TTT']);
ok('k=3: no sources', structure(3).sources.length === 0);

console.log('\nB) Girth of the dominance digraph (shortest directed cycle) — k = 1..9');
const girthSeq = [];
for (let k = 1; k <= 9; k++) girthSeq.push(structure(k).girth);
check('girth = [null,null,4,3,3,3,3,3,3]', girthSeq, [null, null, 4, 3, 3, 3, 3, 3, 3]);

console.log('\nC) Cycle spectrum — exact by Held-Karp for k = 3, 4');
check('k=3: directed-cycle lengths present = {4}', structure(3, { doCycles: true }).cycleLengths, [4]);
check('k=4: cycle lengths = {3,4,…,14} (pancyclic whirlpool)',
  structure(4, { doCycles: true }).cycleLengths, [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]);

console.log('\nD) Pancyclicity — witnessed & edge-verified for k = 5, 6, 7 (existence, not absence)');
for (let k = 5; k <= 7; k++) {
  const w = pancyclicWitnesses(k, 120000, 20260703);
  ok(`k=${k}: a directed cycle of EVERY length 3..${w.giantSize} exhibited & verified` +
     (w.allFound ? '' : ` (missing ${w.missing.join(',')})`), w.allFound);
}

console.log('\nE) The staged sequences match the exact engine — k = 1..9');
const transTri = [], distinctP = [];
for (let k = 1; k <= 9; k++) { const inv = invariants(tournament(k)); transTri.push(inv.transTri); distinctP.push(inv.distinctP); }
check('transTri = 0,0,8,198,1964,16652,139570,1163520,9456630', transTri,
  [0, 0, 8, 198, 1964, 16652, 139570, 1163520, 9456630]);
check('distinctP = 1,3,15,31,87,191,415,871,1781', distinctP,
  [1, 3, 15, 31, 87, 191, 415, 871, 1781]);

console.log(`\n${fail === 0 ? '✓ ALL' : '✗'} ${pass} checks pass${fail ? `, ${fail} FAIL` : ''}.`);
process.exit(fail ? 1 : 0);
