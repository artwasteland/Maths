// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/nonorientable-queens/derive.mjs
// Regenerate the staged b-files from the verified engine.
//   node oversight/oeis/nonorientable-queens/derive.mjs
// Every term written here is asserted in research/nonorientable-queens/verify.mjs (85/85).
import { attackGraph, independenceStats, countExactK } from '../../../research/nonorientable-queens/engine.mjs';
import { writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = dirname(fileURLToPath(import.meta.url));

const total = (topo, nhi) => { const a = []; for (let n = 1; n <= nhi; n++) a.push(independenceStats(attackGraph(topo, n, 'queen'), n * n).total); return a; };
const pairs = (topo, nhi) => { const a = []; for (let n = 1; n <= nhi; n++) a.push(BigInt(countExactK(attackGraph(topo, n, 'queen'), n * n, 2))); return a; };
const bfile = (name, terms) => {
  const body = terms.map((t, i) => `${i + 1} ${t}`).join('\n') + '\n';
  writeFileSync(`${HERE}/${name}`, body);
  console.log(`  ${name}: ${terms.length} terms`);
};

console.log('regenerating b-files (a few minutes for the torus total)…');
bfile('b-mobius-total.txt', total('mobius', 13));   // ~1 min at n=13
bfile('b-mobius-pairs.txt', pairs('mobius', 18));
bfile('b-torus-total.txt',  total('torus', 12));    // ~2 min at n=12
bfile('b-klein-total.txt',  total('klein', 12));    // convention-dependent (see README)
console.log('done.');
