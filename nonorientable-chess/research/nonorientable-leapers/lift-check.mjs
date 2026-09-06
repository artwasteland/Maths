// lift-check.mjs — check the attack geometry the other way round.
//
// engine.mjs, leap.c and leap2.c all answer "which board cell does this jump land
// on?" by FOLDING: take the plane target and push it back into the fundamental
// domain. They differ in how (closed-form floor/modulo in the first two, iterated
// generators in the third), but they are all the same direction of travel, and a
// shared misunderstanding of the deck group would survive all three.
//
// This file goes the other way. It UNFOLDS: it takes each board cell, generates
// its lifts in the cover by applying deck elements forwards, and asks whether any
// lift sits exactly one leaper vector from the source cell. That is the definition
// of the universal-cover rule as prose states it, with no reduction step anywhere,
// so it fails differently from a fold.
//
//   attacks((r,c), (r2,c2))  iff  exists a leaper vector (dr,dc) and a deck
//                                 element g with  g.(r2,c2) = (r+dr, c+dc).
//
// The deck elements, enumerated over p,q in [-W..W] (W=2 is ample: a leaper
// vector moves at most 4 cells and n >= 5 here, so at most one seam is crossed):
//
//   flat    identity only, and the target must already be on the board.
//   torus   g_{p,q}(R,C) = (R + p n, C + q n)
//   mobius  g_k(R,C)     = (k even ? R : n-1-R,  C + k n)      rows never wrap
//   klein   g_{p,q}(R,C) = (R + p n,  (p odd ? n-1-C : C) + q n)
//
// Usage:  node lift-check.mjs [maxN]        (default 14)
// Prints PASS/FAIL per topology and a positive control that the check can fail.

import { attackGraph, leaperVectors, LEAPERS } from './engine.mjs';

const W = 2;

// All lifts of board cell (r2,c2) into the cover, as [R,C] pairs.
function lifts(topology, r2, c2, n) {
  const out = [];
  if (topology === 'flat') { out.push([r2, c2]); return out; }
  if (topology === 'torus') {
    for (let p = -W; p <= W; p++)
      for (let q = -W; q <= W; q++) out.push([r2 + p * n, c2 + q * n]);
    return out;
  }
  if (topology === 'mobius') {
    for (let k = -W; k <= W; k++) {
      const R = (((k % 2) + 2) % 2 === 0) ? r2 : (n - 1 - r2);
      out.push([R, c2 + k * n]);
    }
    return out;
  }
  if (topology === 'klein') {
    for (let p = -W; p <= W; p++) {
      const odd = (((p % 2) + 2) % 2) === 1;
      const Cbase = odd ? (n - 1 - c2) : c2;
      for (let q = -W; q <= W; q++) out.push([r2 + p * n, Cbase + q * n]);
    }
    return out;
  }
  throw new Error('unknown topology ' + topology);
}

// The attack relation built purely by unfolding. Returns BigInt adjacency masks
// in the same encoding attackGraph() uses, symmetrised the same way.
function attackGraphByLifting(topology, n, vectors) {
  const V = n * n;
  const adj = new Array(V).fill(0n);
  for (let r = 0; r < n; r++)
    for (let c = 0; c < n; c++)
      for (let r2 = 0; r2 < n; r2++)
        for (let c2 = 0; c2 < n; c2++) {
          if (r === r2 && c === c2) continue;
          let hit = false;
          for (const [R, C] of lifts(topology, r2, c2, n)) {
            for (const [dr, dc] of vectors)
              if (R === r + dr && C === c + dc) { hit = true; break; }
            if (hit) break;
          }
          if (hit) {
            const u = r * n + c, w = r2 * n + c2;
            adj[u] |= 1n << BigInt(w);
            adj[w] |= 1n << BigInt(u);
          }
        }
  return adj;
}

const maxN = Number(process.argv[2] || 14);
let fail = 0, cells = 0;

for (const topo of ['flat', 'torus', 'mobius', 'klein']) {
  for (const name of Object.keys(LEAPERS)) {
    const [a, b] = LEAPERS[name];
    const V = leaperVectors(a, b);
    for (let n = 3; n <= maxN; n++) {
      const byFold = attackGraph(topo, n, V);
      const byLift = attackGraphByLifting(topo, n, V);
      for (let i = 0; i < n * n; i++) {
        cells++;
        if (byFold[i] !== byLift[i]) {
          fail++;
          if (fail <= 5)
            console.log(`  DISAGREE ${topo} ${name} n=${n} cell ${i}: fold ${byFold[i].toString(2)} lift ${byLift[i].toString(2)}`);
        }
      }
    }
  }
  console.log(`${fail === 0 ? 'ok  ' : 'FAIL'} ${topo}`);
}

// Positive control: the comparison must be able to report a disagreement. Feed
// the lifting side a deliberately wrong leaper (a camel where a knight belongs)
// and require a mismatch. Without this, a bug that made both sides empty would
// print the same "0 disagreements" as a real pass.
const ctlFold = attackGraph('mobius', 8, leaperVectors(1, 2));
const ctlLift = attackGraphByLifting('mobius', 8, leaperVectors(1, 3));
let ctlDiff = 0;
for (let i = 0; i < 64; i++) if (ctlFold[i] !== ctlLift[i]) ctlDiff++;

console.log(`\ncompared ${cells} adjacency masks over n=3..${maxN}, 4 topologies x 4 leapers`);
console.log(`positive control (knight fold vs camel lift, mobius n=8): ${ctlDiff} cells differ — the check can fail`);
if (fail === 0 && ctlDiff > 0) {
  console.log('PASS — unfolding and folding agree everywhere');
} else {
  console.log(`FAILED — ${fail} disagreements${ctlDiff === 0 ? ', AND the positive control did not fire' : ''}`);
  process.exit(1);
}
