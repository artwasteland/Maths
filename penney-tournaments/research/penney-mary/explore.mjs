// research/penney-mary/explore.mjs — surfaces the concrete objects the stratum
// shows: the smallest nontransitive Penney triangle on a 3-sided die (length-2
// words), with every exact win-probability, and the binary contrast.
// Run: node research/penney-mary/explore.mjs

import { words, pAfirst_conway, tournament, invariants } from './engine.mjs';

const m = 3, k = 2, S = words(m, k), t = tournament(m, k), { rel, n } = t;
const tris = [];
for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) for (let c = b + 1; c < n; c++) {
  const ab = rel[a][b], bc = rel[b][c], ac = rel[a][c];
  if (ab === 0 || bc === 0 || ac === 0) continue;
  const oa = (ab === 1 ? 1 : 0) + (ac === 1 ? 1 : 0);
  const ob = (ab === -1 ? 1 : 0) + (bc === 1 ? 1 : 0);
  const oc = (ac === -1 ? 1 : 0) + (bc === -1 ? 1 : 0);
  if (oa === 1 && ob === 1 && oc === 1)
    tris.push((ab === 1 && bc === 1 && ac === -1) ? [a, b, c] : [a, c, b]);
}
console.log(`m=3, k=2 — directed (rock-paper-scissors) triangles: ${tris.length}`);
for (const T of tris) {
  const W = T.map((i) => S[i]);
  const probs = W.map((w, i) => `${w}▸${W[(i + 1) % 3]} = ${pAfirst_conway(m, w, W[(i + 1) % 3]).s}`);
  console.log(`  ${W.join(' → ')} → ${W[0]}   [${probs.join(',  ')}]`);
}

const W = tris[0].map((i) => S[i]);
console.log(`\nfull pairwise for the triangle {${W.join(', ')}} (a fair 3-sided die):`);
for (const x of W) for (const y of W) if (x !== y)
  console.log(`  P(${x} before ${y}) = ${pAfirst_conway(m, x, y).s}`);

console.log(`\nbinary contrast: k=3 cyc3 = ${invariants(tournament(2, 3)).cyc3} (no triangle — smallest cycle is the famous 4-square),`);
console.log(`                 k=4 cyc3 = ${invariants(tournament(2, 4)).cyc3} (triangles finally appear).`);
