// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// Rewrites the b-files for the fault-free domino-tiling rectangle sequences,
// straight from the verified engine. Run: node oversight/oeis/fault-free-tilings/derive.mjs
import { FF } from '../../../research/fault-free-tilings/ff.mjs';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const here = dirname(fileURLToPath(import.meta.url));
function bfile(name, arr, note){
  const lines = arr.map(([n,v]) => `${n} ${v}`);
  writeFileSync(join(here, name), `# ${note}\n` + lines.join('\n') + '\n');
  return arr.slice(0,10).map(x=>x[1]).join(',');
}
// rows a(n) = FF(m,n), n = 1..N  (leading zeros kept — the honest sequence)
const rows = { 5:44, 6:40, 7:34, 8:28 };
for (const m in rows){
  const N = rows[m], arr = [];
  for (let n=1;n<=N;n++) arr.push([n, FF(+m,n).toString()]);
  console.log(`5..: ff-${m}xn ->`, bfile(`b-ff-${m}xn.txt`, arr, `Number of fault-free domino tilings of the ${m} X n rectangle. a(n)=FF(${m},n), n>=1.`));
}
// the full array T(m,n), m,n>=1, read by antidiagonals upward:
// T(1,1),T(1,2),T(2,1),T(1,3),T(2,2),T(3,1),...  (offset 1)
const AR = 18; const anti = []; let idx = 1;
for (let s=2;s<=2*AR;s++) for (let n=1;n<s;n++){ const m=s-n; if(m>=1&&m<=AR&&n<=AR){ anti.push([idx++, FF(m,n).toString()]); } }
console.log('array antidiag ->', bfile('b-ff-array-antidiagonals.txt', anti,
  'Array T(m,n) = number of fault-free domino tilings of the m X n rectangle, m,n>=1, read by antidiagonals upward: T(1,1),T(1,2),T(2,1),T(1,3),T(2,2),T(3,1),... Main diagonal T(n,n) restricted to 2n X 2n is OEIS A124997.'));
console.log('done');
