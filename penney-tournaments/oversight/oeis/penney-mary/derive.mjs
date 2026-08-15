// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/penney-mary/derive.mjs
// Re-emits the staged b-files for the m-ary Penney-tournament sequences and
// prints every term list. Reproducible from a fresh checkout:
//   node oversight/oeis/penney-mary/derive.mjs
// The exact methods + cross-checks live in research/penney-mary/verify.mjs.

import { tournament, invariants } from '../../../research/penney-mary/engine.mjs';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const here = dirname(fileURLToPath(import.meta.url));

// (m, kmax) — how far each family is computed exactly here (exhaustive, BigInt-exact
// probabilities; the O(n^3) triangle scan is the binding cost, n = m^k).
const RANGE = { 2: 9, 3: 6, 4: 5, 5: 4 };
const all = {};
for (const m of [2, 3, 4, 5]) {
  const s = { ties: [], cyc3: [], maxout: [] };
  for (let k = 1; k <= RANGE[m]; k++) {
    const inv = invariants(tournament(m, k));
    s.ties.push(inv.ties); s.cyc3.push(inv.cyc3); s.maxout.push(inv.maxout);
  }
  all[m] = s;
}

// write b-files (offset k=1). The m=2 row is the published anchor (not new).
const bfile = (arr) => arr.map((v, i) => `${i + 1} ${v}`).join('\n') + '\n';
const stage = [
  ['b-m3-cyc3.txt', all[3].cyc3], ['b-m3-ties.txt', all[3].ties], ['b-m3-maxout.txt', all[3].maxout],
  ['b-m4-cyc3.txt', all[4].cyc3], ['b-m4-ties.txt', all[4].ties], ['b-m4-maxout.txt', all[4].maxout],
  ['b-m5-cyc3.txt', all[5].cyc3], ['b-m5-ties.txt', all[5].ties], ['b-m5-maxout.txt', all[5].maxout],
];
for (const [name, arr] of stage) writeFileSync(join(here, name), bfile(arr));

console.log('m-ary Penney-tournament sequences (offset k=1):\n');
for (const m of [2, 3, 4, 5]) {
  console.log(`m=${m}  (m-sided fair die; n=m^k words):`);
  console.log(`  cyc3   (directed triangles)  : ${all[m].cyc3.join(', ')}`);
  console.log(`  ties   (tied pairs, p=1/2)   : ${all[m].ties.join(', ')}`);
  console.log(`  maxout (max out-degree)      : ${all[m].maxout.join(', ')}\n`);
}
console.log('Wrote', stage.length, 'b-files to', here);
console.log('m=2 is the PUBLISHED anchor (research/penney-tournament); m=3,4,5 are the new staged families.');
