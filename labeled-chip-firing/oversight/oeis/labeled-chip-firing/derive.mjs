// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// Rewrites b282901.txt from the verified enumerators. Reproducible from a fresh
// checkout: `node oversight/oeis/labeled-chip-firing/derive.mjs`.
// a(0..4) via the JS enumerator (fast); a(5) via the JS enumerator too (~40 s) —
// the C++ (research/labeled-chip-firing/cf.cpp) is the fast path and agrees.
import { enumFast, enumMap } from '../../../research/labeled-chip-firing/enum.mjs';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const DIR = dirname(fileURLToPath(import.meta.url));

// JS (enumFast) reproduces a(0..5) exactly; a(6) at N=13 is beyond the JS methods
// (the visited set exceeds JS memory) — it is computed by research/labeled-chip-firing/cf.cpp
// (two independent C++ builds agree: 2555). We carry it as a documented constant so this
// script never silently drops it.
const A6 = { n: 6, value: 2555 };
const N_MAX = 5;
const rows = [];
for (let n = 0; n <= N_MAX; n++) {
  const N = 2 * n + 1;
  const a = enumFast(N).perms;                      // odd N: nibble enumerator
  rows.push(`${n} ${a}`);
  console.error(`a(${n}) = ${a}`);
}
rows.push(`${A6.n} ${A6.value}`);
console.error(`a(${A6.n}) = ${A6.value}  (from cf.cpp; JS cannot reach N=13)`);
const header = [
  '# A282901: Number of permutations of 1,2,...,2n+1 obtainable via labeled chip-firing.',
  '# Hopkins, McConville, Propp, "Sorting via chip-firing", EJC 24 (2017) #P3.13; arXiv:1612.06816.',
  '# a(0..4) = 1,3,12,54,232 were on record (OEIS, keyword `more`, no b-file).',
  '# a(5) = 819 computed and verified three independent ways in the Artificial Wasteland,',
  '#   2026-07-12 (research/labeled-chip-firing/, verify.mjs 29/29). Offset 0.',
  '# a(6) = 2555 computed at N=13 (705,592,802 configs) by two independent C++ enumerators',
  '#   (cf.cpp flat-hash/linear + a second FNV/quadratic build); the JS methods cannot reach N=13.',
].join('\n');
writeFileSync(join(DIR, 'b282901.txt'), header + '\n' + rows.join('\n') + '\n');
console.error('wrote b282901.txt');
