// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// oversight/oeis/graceful-census/derive.mjs
//
// Regenerates the staged b-files for the four graceful-labeling TOTAL sequences
// that are absent from the OEIS census (fan, friendship, helm, quadrilateral
// book), using the exact counter in research/graceful-census/. Small terms are
// counted in JS; larger terms use the C++ engine if a compiler is present.
//
//   node oversight/oeis/graceful-census/derive.mjs        # print
//   node oversight/oeis/graceful-census/derive.mjs --write # rewrite b-files
//
// Trust: see research/graceful-census/verify.mjs — two JS counters + a C++
// engine agree, six published sequences are reproduced, the friendship zeros
// match the Bermond–Kotzig theorem, and helm/book reduce (Aut x complement) to
// the published "fundamentally different" sequences A387800 / A387795.

import { FAMILIES, countByVertices } from '../../../research/graceful-census/graceful.mjs';
import { execSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const RES = join(HERE, '../../../research/graceful-census');
let cpp = null;
try {
  execSync('command -v g++', { stdio: 'ignore' });
  execSync(`g++ -O3 -o ${join(RES, 'graceful')} ${join(RES, 'graceful.cpp')}`, { stdio: 'ignore' });
  cpp = (v, e) => execSync(join(RES, 'graceful'), { input: `${v} ${e.length}\n` + e.map(([a, b]) => `${a} ${b}`).join('\n') + '\n' }).toString().trim();
} catch { cpp = null; }
const count = g => (g.v <= 10 || !cpp) ? String(countByVertices(g.v, g.e)) : cpp(g.v, g.e);

// family, offset, count of terms, output filename
const SEQ = [
  { fam: 'fan',        idx: 'n', from: 2, terms: 11, file: 'b-fan.txt' },
  { fam: 'friendship', idx: 'k', from: 1, terms: 5,  file: 'b-friendship.txt' },
  { fam: 'helm',       idx: 'n', from: 3, terms: 5,  file: 'b-helm.txt' },
  { fam: 'bookQuad',   idx: 'n', from: 1, terms: 5,  file: 'b-book-quadrilateral.txt' },
];
const write = process.argv.includes('--write');
for (const s of SEQ) {
  const lines = [];
  for (let i = 0; i < s.terms; i++) { const n = s.from + i; lines.push(`${n} ${count(FAMILIES[s.fam](n))}`); }
  const body = lines.join('\n') + '\n';
  console.log(`\n# ${s.fam} (offset ${s.idx}=${s.from})\n${body.trim()}`);
  if (write) { writeFileSync(join(HERE, s.file), body); console.log(`  → wrote ${s.file}`); }
}
