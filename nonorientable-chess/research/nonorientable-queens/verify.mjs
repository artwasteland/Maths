// research/nonorientable-queens/verify.mjs — the correctness gate.
//
// Nothing about the new (Mobius / torus) sequences is believed until the engine
// has reproduced published ground truth by BOTH of its enumerators:
//
//   (1) Attack model, via the k=n / k=ceil(n/2) counter:
//         flat   n-queens          == A000170   (n = 1..9)
//         torus  n-queens          == A007705   (odd n; 1,10,28,88)
//         mobius ceil(n/2)-queens  == A137279   (n = 1..12)  [Bell & Stevens 2008]
//   (2) Both enumerators, via all-sizes / pairs on the SAME boards:
//         flat   independent sets  == A287227   (n = 1..8)
//         flat   pairs (k=2)       == A036464   (n = 1..12)
//         torus  pairs (k=2)       == A172517   (n = 1..12)
//   (3) Internal consistency:
//         independenceStats.total  == sum_k countExactK    (the two counters agree)
//         the attack graph is symmetric on every topology and piece
//         the Bell-Stevens structural law: a Mobius queen's E-W rook line covers
//         exactly rows {i, n-1-i} (a row "carries over" to n-1-i across the twist)
//
// Only after all of that do we ASSERT the new sequence values. Reproducing three
// independent published sequences with one ray-tracer is the proof the model is
// right; the Klein-bottle numbers use the identical traced code.
//
// Run: node research/nonorientable-queens/verify.mjs   (~1-2 min)

import {
  attackGraph, queenAttacks, countExactK, independenceStats, step,
} from './engine.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log(`  ✗ FAIL: ${m}`); } };
const eq = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

const seqK = (topo, kOf, nlo, nhi) => {
  const out = [];
  for (let n = nlo; n <= nhi; n++) out.push(countExactK(attackGraph(topo, n, 'queen'), n * n, kOf(n)));
  return out;
};
const seqTotal = (topo, piece, nlo, nhi) => {
  const out = [];
  for (let n = nlo; n <= nhi; n++) out.push(independenceStats(attackGraph(topo, n, piece), n * n).total.toString());
  return out;
};

// ---------- (1) attack model vs three published sequences ----------
console.log('(1) attack model reproduces published ground truth');
ok(eq(seqK('flat', n => n, 1, 9),
      [1, 0, 0, 2, 10, 4, 40, 92, 352]),
   'flat n-queens == A000170 (n=1..9)');
ok(eq(seqK('torus', n => n, 1, 11),
      [1, 0, 0, 0, 10, 0, 28, 0, 0, 0, 88]),
   'torus n-queens == A007705 (odd n -> 1,10,28,88)');
ok(eq(seqK('mobius', n => Math.ceil(n / 2), 1, 12),
      [1, 4, 0, 16, 40, 192, 560, 3328, 11772, 63840, 259336, 1550976]),
   'mobius ceil(n/2)-queens == A137279 (n=1..12) [Bell & Stevens]');

// ---------- (2) both enumerators vs published totals / pairs ----------
console.log('(2) both enumerators reproduce published totals & pairs');
ok(eq(seqTotal('flat', 'queen', 1, 8),
      ['2', '5', '18', '87', '462', '2635', '16870', '118969']),
   'flat independent sets == A287227 (n=1..8)');
ok(eq(seqK('flat', () => 2, 1, 12),
      [0, 0, 8, 44, 140, 340, 700, 1288, 2184, 3480, 5280, 7700]),
   'flat non-attacking pairs == A036464 (n=1..12)');
ok(eq(seqK('torus', () => 2, 1, 12),
      [0, 0, 0, 32, 100, 288, 588, 1152, 1944, 3200, 4840, 7200]),
   'torus non-attacking pairs == A172517 (n=1..12)');

// ---------- (3) internal consistency ----------
console.log('(3) internal consistency: two counters agree, graph symmetric, structural law');
for (const topo of ['flat', 'torus', 'mobius', 'klein']) {
  for (const piece of ['queen', 'king']) {
    for (const n of [3, 4, 5]) {
      const adj = attackGraph(topo, n, piece), V = n * n;
      // symmetry
      let sym = true;
      for (let u = 0; u < V && sym; u++)
        for (let w = 0; w < V; w++)
          if ((((adj[u] >> BigInt(w)) & 1n) !== ((adj[w] >> BigInt(u)) & 1n))) { sym = false; break; }
      ok(sym, `attack graph symmetric (${topo} ${piece} n=${n})`);
      // total == sum_k countExactK
      const stats = independenceStats(adj, V);
      let s = 0n;
      for (let k = 0; k <= stats.maxSize; k++) s += BigInt(countExactK(adj, V, k));
      ok(s === stats.total, `total == sum_k C(k) (${topo} ${piece} n=${n}): ${s} vs ${stats.total}`);
    }
  }
}

// Bell-Stevens structural law: the E-W rook line of a Mobius queen at (i,j) lies
// exactly in rows {i, n-1-i} and covers every other square in those rows.
console.log('(3b) Bell-Stevens: a Mobius queen carries over row i -> row n-1-i');
for (const n of [5, 6, 7, 8]) {
  for (let i = 0; i < n; i++) {
    // trace only the two horizontal directions
    const rowsHit = new Set();
    for (const [dr0, dc0] of [[0, -1], [0, 1]]) {
      let r = i, c = 0, dr = dr0, dc = dc0;   // start at column 0 of row i
      const start = i * n + 0;
      for (let g = 0; g < 8 * n; g++) {
        const nx = step('mobius', r, c, dr, dc, n);
        if (nx === null) break;
        [r, c, dr, dc] = nx;
        if (r * n + c === start) break;
        rowsHit.add(r);
      }
    }
    const expect = new Set([i, n - 1 - i]);
    ok(rowsHit.size === expect.size && [...rowsHit].every(x => expect.has(x)),
       `mobius E-W rows == {i, n-1-i} (n=${n}, i=${i}): got {${[...rowsHit].sort((a,b)=>a-b)}}`);
  }
}

// ---------- (4) the NEW sequences — asserted so a regression is caught ----------
console.log('(4) the new (absent-from-OEIS) sequences, asserted');
// Mobius queen total independent sets (incl. empty) — absent (analogue of A287227).
// n=13 recomputed here too (~1 min) so every staged b-file term is gated.
ok(eq(seqTotal('mobius', 'queen', 1, 13),
      ['2', '5', '10', '33', '146', '445', '2346', '8193', '49222', '175541', '1193094', '4593217', '34531602']),
   'NEW: mobius queen total independent sets (n=1..13)');
// Torus queen total independent sets — absent (analogue of A287227); n=12 ~ 100 s.
ok(eq(seqTotal('torus', 'queen', 1, 12),
      ['2', '5', '10', '49', '286', '1189', '6350', '41153', '217810', '1623941', '9326890', '87306481']),
   'NEW: torus queen total independent sets (n=1..12)');
// Mobius queen non-attacking pairs — absent (analogue of A036464 / A172517)
ok(eq(seqK('mobius', () => 2, 1, 18),
      [0, 0, 0, 16, 80, 216, 504, 960, 1728, 2800, 4400, 6480, 9360, 12936, 17640, 23296, 30464, 38880]),
   'NEW: mobius queen non-attacking pairs (n=1..18)');
// Mobius maximum non-attacking queens == ceil(n/2) except the unique dip at n=3
{
  const mx = [];
  for (let n = 1; n <= 12; n++) mx.push(independenceStats(attackGraph('mobius', n, 'queen'), n * n).maxSize);
  ok(eq(mx, [1, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6, 6]), 'NEW: mobius max non-attacking queens (dip at n=3)');
  ok(mx[2] === 1 && Math.ceil(3 / 2) === 2, 'the 3x3 Mobius board cannot hold ceil(3/2)=2 non-attacking queens');
}

console.log(`\n${fail === 0 ? '✓ ALL PASS' : '✗ FAILURES'} — ${pass} passed, ${fail} failed.`);
process.exit(fail === 0 ? 0 : 1);
