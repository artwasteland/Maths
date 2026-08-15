// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/nonorientable-kings/derive.mjs
// Regenerate the two staged b-files (non-orientable king totals) from the verified
// transfer-matrix counter. Fast: the whole run is a few seconds.
//   node oversight/oeis/nonorientable-kings/derive.mjs
//
// Every term written here is cross-checked two independent ways and asserted in
// research/nonorientable-queens/verify-kings.mjs (DFS ray-trace == transfer matrix
// for n<=7; flat==A063443 and torus==A067958 for n<=13).
import { kingTotal } from '../../../research/nonorientable-queens/kings-transfer.mjs';
import { writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = dirname(fileURLToPath(import.meta.url));

const NHI = 13;
const seq = topo => { const a = []; for (let n = 1; n <= NHI; n++) a.push(kingTotal(topo, n)); return a; };
const bfile = (name, terms) => {
  writeFileSync(`${HERE}/${name}`, terms.map((t, i) => `${i + 1} ${t}`).join('\n') + '\n');
  console.log(`  ${name}: ${terms.length} terms — ${terms.slice(0,6).join(', ')}, …`);
};

console.log('regenerating non-orientable king b-files (offset n=1)…');
bfile('b-mobius-total.txt', seq('mobius'));
bfile('b-klein-total.txt',  seq('klein'));
// print calibration siblings for the record (not staged: already in OEIS)
console.log('  [calibration] flat  == A063443:', seq('flat').slice(0,8).join(', '), '…');
console.log('  [calibration] torus == A067958:', seq('torus').slice(0,8).join(', '), '…');
console.log('done.');
