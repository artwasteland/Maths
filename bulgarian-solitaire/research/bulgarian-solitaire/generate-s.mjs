// Generate the dataset + staging b-files for s-Bulgarian solitaire (sigma(h)=min(h,s)).
//   node generate-s.mjs [Nembed=48] [Nbfile=55]
// Writes:
//   data-s.json                          — sequences for s=1..5, n=1..Nembed (page + verifier)
//   ../../oversight/oeis/generalized-bulgarian-solitaire/b-*.txt  — staged b-files (settling, GoE, cycles, recurrent) for s=2,3
import { analyze } from './engine-s.mjs';
import { writeFileSync, mkdirSync } from 'node:fs';

const Nembed = parseInt(process.argv[2] || '48', 10);
const Nbfile = parseInt(process.argv[3] || '55', 10);
const S = [1, 2, 3, 4, 5];

function seqs(N) {
  const out = {};
  for (const s of S) {
    const r = { parts: [], maxTail: [], totalSettle: [], goe: [], numCycles: [], recurrent: [], longest: [], maxTailCount: [] };
    for (let n = 1; n <= N; n++) {
      const a = analyze(n, s);
      r.parts.push(a.parts); r.maxTail.push(a.maxTail); r.totalSettle.push(a.totalSettle);
      r.goe.push(a.goe); r.numCycles.push(a.numCycles); r.recurrent.push(a.recurrent);
      r.longest.push(a.longest); r.maxTailCount.push(a.maxTailCount);
    }
    out['s' + s] = r;
  }
  return out;
}

// ---- embedded dataset for the page ----
const embed = seqs(Nembed);
writeFileSync(new URL('./data-s.json', import.meta.url),
  JSON.stringify({ Nembed, generated: 'node generate-s.mjs', data: embed }, null, 0));
console.log('wrote data-s.json  (s=1..5, n=1..' + Nembed + ')');

// ---- staged b-files (n=1..Nbfile) ----
const dir = new URL('../../oversight/oeis/generalized-bulgarian-solitaire/', import.meta.url);
mkdirSync(dir, { recursive: true });
function bfile(name, s, key) {
  const lines = [];
  for (let n = 1; n <= Nbfile; n++) lines.push(n + ' ' + analyze(n, s)[key]);
  writeFileSync(new URL('./' + name, dir), lines.join('\n') + '\n');
  console.log('wrote ' + name);
}
for (const s of [2, 3]) {
  bfile(`b-total-settle-s${s}.txt`, s, 'totalSettle');
  bfile(`b-max-tail-s${s}.txt`, s, 'maxTail');
  bfile(`b-goe-s${s}.txt`, s, 'goe');
  bfile(`b-num-cycles-s${s}.txt`, s, 'numCycles');
  bfile(`b-recurrent-s${s}.txt`, s, 'recurrent');
}
console.log('done.');
