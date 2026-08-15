// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/nonorientable-leapers/derive.mjs
// Regenerate the staged b-files for the eight NEW (Möbius + Klein) leaper
// sequences, from the verified engine. Every term written here is asserted in
// research/nonorientable-leapers/verify.mjs (25/25) up to n=11 and reproduced by
// the C backtracker leap.c up to n=13.
//   node oversight/oeis/nonorientable-leapers/derive.mjs [NMAX]
import { attackGraph, countPermutations, leaperVectors, LEAPERS } from '../../../research/nonorientable-leapers/engine.mjs';
import { writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = dirname(fileURLToPath(import.meta.url));
const NMAX = Number(process.argv[2] ?? 12);   // n=13 is slow in Node; use leap.c for the last term

function seq(topo, leaper, nhi) {
  const [a, b] = LEAPERS[leaper]; const V = leaperVectors(a, b);
  const out = [];
  for (let n = 1; n <= nhi; n++) out.push(countPermutations(attackGraph(topo, n, V), n));
  return out;
}
function bfile(name, terms) {
  writeFileSync(`${HERE}/${name}`, terms.map((t, i) => `${i + 1} ${t}`).join('\n') + '\n');
  console.log(`  ${name}: ${terms.length} terms`);
}

console.log(`regenerating leaper b-files to n=${NMAX} (Node; use leap.c for n=13)…`);
for (const topo of ['mobius', 'klein'])
  for (const leaper of ['knight', 'camel', 'zebra', 'giraffe'])
    bfile(`b-${topo}-${leaper}.txt`, seq(topo, leaper, NMAX));
console.log('done. (verify.mjs asserts these; leap.c reaches n=13.)');
