// gen-data.mjs — emit the verified sequences: b-files for the staged bundle and a
// JSON blob the immersive page embeds (so the page never recomputes what the gate
// already trusted, and the page's own live recount is checked against it).
// Run:  node gen-data.mjs   (writes to ../../oversight/oeis/lights-out-surfaces/ and ./data.json)

import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { SURFACES, surfaceNullity } from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OEIS = join(HERE, '..', '..', 'oversight', 'oeis', 'lights-out-surfaces');
const NMAX = 64;

const seq = {};
for (const s of SURFACES) { seq[s] = []; for (let n = 1; n <= NMAX; n++) seq[s].push(surfaceNullity(n, s)); }

// b-files for the three claimed-absent sequences + projective (flagged exploration).
function bfile(name, arr) {
  const lines = arr.map((v, i) => `${i + 1} ${v}`).join('\n') + '\n';
  writeFileSync(join(OEIS, `b-${name}.txt`), lines);
}
bfile('cylinder', seq.cylinder);
bfile('mobius', seq.mobius);
bfile('klein', seq.klein);
bfile('projective', seq.projective);

// JSON for the page (n=1..NMAX for all surfaces; the page displays a window of it).
writeFileSync(join(HERE, 'data.json'), JSON.stringify({ nmax: NMAX, seq }, null, 0) + '\n');

// Console summary
for (const s of SURFACES) console.log(`${s.padEnd(11)}: ${seq[s].slice(0, 20).join(', ')} ...`);
console.log(`\nwrote b-cylinder.txt, b-mobius.txt, b-klein.txt, b-projective.txt (n=1..${NMAX}) and data.json`);
