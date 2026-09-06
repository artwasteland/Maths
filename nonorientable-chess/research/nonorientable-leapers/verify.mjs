// research/nonorientable-leapers/verify.mjs
//
// The correctness gate for the non-orientable leaper sequences. Prints
// "<pass>/<total> PASS" and exits non-zero on any mismatch. ~1-2 min.
//
// The attack model is certified against FOUR independent published grounds
// before any new number is believed:
//   (A) flat  leaper permutation counts  = OEIS A137774 (knight/"empresses"),
//       A189358 (camel), A189565 (zebra), A189563 (giraffe);
//   (B) torus leaper permutation counts  = research/leapers-on-a-torus (which
//       itself reproduces the queen anchor A051906/A007705, and whose C code
//       independently reaches n=13);
//   (C) the model fed the eight UNIT leapers reproduces the already-validated
//       nonorientable-queens KING attack graph cell-for-cell on ALL four
//       topologies (the single move where universal-cover == single-step);
//   (D) two independent enumerators (bitmask backtracker + column-DFS) agree.
// Only then are the NEW Mobius and Klein leaper sequences asserted (regression
// guard), plus the headline structural fact: the torus unit-scaling collapse
// (all four leapers -> 210 at n=7) is BROKEN by the twist.

import { readFileSync } from 'node:fs';
import {
  attackGraph, countPermutations, countPermutationsAlt,
  leaperVectors, LEAPERS,
} from './engine.mjs';
import { attackGraph as queensGraph } from '../nonorientable-queens/engine.mjs';

let pass = 0, fail = 0;
const eq = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
function check(name, got, want) {
  const ok = Array.isArray(want) ? eq(got, want) : got === want;
  if (ok) { pass++; }
  else { fail++; console.log(`  FAIL ${name}\n    got  ${JSON.stringify(got)}\n    want ${JSON.stringify(want)}`); }
}
function seq(topo, leaper, nlo, nhi) {
  const [a, b] = LEAPERS[leaper]; const V = leaperVectors(a, b);
  const out = [];
  for (let n = nlo; n <= nhi; n++) out.push(countPermutations(attackGraph(topo, n, V), n));
  return out;
}

// ---- (A) flat anchor: catalogued in OEIS -------------------------------------
const FLAT = {
  knight:  [1, 2, 2, 8, 20, 94, 438, 2766, 19480, 163058],       // A137774
  camel:   [1, 2, 6, 8, 24, 126, 524, 3072, 22854, 189646],       // A189358 (offset)
  zebra:   [1, 2, 6, 12, 36, 174, 708, 4334, 31424, 263732],      // A189565 (offset)
  giraffe: [1, 2, 6, 24, 48, 182, 868, 5752, 37156, 296944],      // A189563 (offset)
};
for (const L of Object.keys(FLAT)) check(`flat ${L} = OEIS`, seq('flat', L, 1, 10), FLAT[L]);

// ---- (B) torus anchor: research/leapers-on-a-torus ---------------------------
const TORUS = {
  knight:  [1, 2, 0, 8, 10, 72, 210, 1408, 8334, 67400],
  camel:   [1, 0, 6, 0, 10, 120, 210, 720, 6156, 41020],
  zebra:   [1, 2, 6, 8, 10, 144, 210, 1408, 6156, 61900],
  giraffe: [1, 2, 0, 24, 10, 72, 210, 4864, 8334, 61900],
};
for (const L of Object.keys(TORUS)) check(`torus ${L} = leapers-on-a-torus`, seq('torus', L, 1, 10), TORUS[L]);

// ---- (C) king cross-check: unit leapers == validated king ray-tracer ---------
const KING = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
for (const topo of ['flat', 'torus', 'mobius', 'klein']) {
  let same = true;
  for (let n = 1; n <= 8 && same; n++) {
    const A = attackGraph(topo, n, KING), B = queensGraph(topo, n, 'king');
    for (let v = 0; v < n * n; v++) if (A[v] !== B[v]) { same = false; break; }
  }
  check(`king graph identical on ${topo} (n<=8)`, same, true);
}

// ---- (D) two enumerators agree -----------------------------------------------
{
  let agree = true;
  for (const topo of ['flat', 'torus', 'mobius', 'klein'])
    for (const L of Object.keys(LEAPERS)) {
      const [a, b] = LEAPERS[L]; const V = leaperVectors(a, b);
      for (let n = 1; n <= 8 && agree; n++)
        if (countPermutations(attackGraph(topo, n, V), n) !== countPermutationsAlt(topo, n, V)) agree = false;
    }
  check('two enumerators agree (all topo x leaper, n<=8)', agree, true);
}

// ---- the NEW sequences: regression guard -------------------------------------
const MOBIUS = {
  knight:  [1, 2, 0, 0, 6, 22, 200, 1266, 11048, 93510, 956498],
  camel:   [1, 0, 6, 2, 2, 64, 150, 1454, 9114, 97966, 848378],
  zebra:   [1, 2, 6, 4, 6, 32, 270, 1226, 12102, 108926, 1129588],
  giraffe: [1, 2, 0, 24, 6, 24, 184, 1008, 12072, 113896, 1145510],
};
const KLEIN = {
  knight:  [1, 0, 0, 0, 4, 4, 136, 628, 6740, 53280, 576360],
  camel:   [1, 0, 4, 0, 2, 64, 54, 612, 4100, 45992, 403342],
  zebra:   [1, 0, 2, 0, 0, 8, 28, 248, 3588, 31508, 409334],
  giraffe: [1, 0, 0, 16, 0, 0, 56, 864, 4348, 34872, 414950],
};
for (const L of Object.keys(MOBIUS)) check(`mobius ${L} (new)`, seq('mobius', L, 1, 11), MOBIUS[L]);
for (const L of Object.keys(KLEIN)) check(`klein ${L} (new)`, seq('klein', L, 1, 11), KLEIN[L]);

// ---- the structural finding: the unit-scaling collapse is broken by the twist -
// On the torus all four leapers share the count 210 at n=7 (the unit-scaling
// theorem forces same-orbit coincidence; 7 prime => full collapse). The Mobius
// band and Klein bottle destroy the symmetry between the two axes, so the four
// counts must split.
const n7 = topo => Object.keys(LEAPERS).map(L => seq(topo, L, 7, 7)[0]);
check('torus n=7 collapses to a single value', new Set(n7('torus')).size, 1);
check('torus n=7 value is 210', n7('torus')[0], 210);
check('mobius n=7 splits (twist breaks the law)', new Set(n7('mobius')).size > 1, true);
check('klein  n=7 splits (twist breaks the law)', new Set(n7('klein')).size > 1, true);

// ---- added 2026-08-17: guard the things the old gate left ungated ------------
// None of these are expensive. They exist because the audit of this directory found
// that the expensive terms were the unchecked ones, and the cheap structural facts
// around them were unchecked too.

// (E) the committed table and the staged b-files must agree, INCLUDING n=14.
// The eight n=14 terms were staged on 2026-07-20 and were "unbound": no committed
// route could recompute them, so nothing would have noticed one being edited.
{
  const tsv = readFileSync(new URL('./terms-1-15.tsv', import.meta.url), 'utf8')
    .trim().split('\n').slice(1);
  const table = new Map();
  for (const line of tsv) {
    const [topo, leaper, terms] = line.split('\t');
    table.set(`${topo}-${leaper}`, terms.split(',').map(s => s.trim()));
  }
  check('terms-1-15.tsv has 16 rows of 15 terms',
    [...table.values()].every(r => r.length === 15) && table.size === 16, true);
  for (const topo of ['mobius', 'klein'])
    for (const L of Object.keys(LEAPERS)) {
      const staged = readFileSync(
        new URL(`../../oversight/oeis/nonorientable-leapers/b-${topo}-${L}.txt`, import.meta.url), 'utf8')
        .trim().split('\n').map(l => l.trim().split(/\s+/)[1]);
      check(`staged b-${topo}-${L}.txt matches terms-1-15.tsv`, staged, table.get(`${topo}-${L}`));
    }
}

// (F) the unit-scaling audit: every equality the orbit partition forces on the
// torus row must hold, and the same predictions applied to the Mobius band must
// mostly FAIL. The second half is the control: if the twisted board obeyed a law
// that has no reason to hold there, the law would be evidence of nothing.
{
  const gcd = (x, y) => (y ? gcd(y, x % y) : x);
  const vkey = (a, b, n) => {
    const s = new Set();
    for (const [p, q] of [[a, b], [b, a]])
      for (const sr of [1, -1]) for (const sc of [1, -1])
        s.add(`${((sr * p) % n + n) % n},${((sc * q) % n + n) % n}`);
    return [...s].sort().join(' ');
  };
  const scale = (k, u, n) => k.split(' ').map(t => {
    const [r, c] = t.split(',').map(Number);
    return `${(r * u) % n},${(c * u) % n}`;
  }).sort().join(' ');
  const NAMES = Object.keys(LEAPERS);
  let torusHeld = 0, tested = 0, mobiusHeld = 0;
  for (let n = 3; n <= 9; n++) {
    const keys = NAMES.map(nm => vkey(LEAPERS[nm][0], LEAPERS[nm][1], n));
    for (let i = 0; i < 4; i++)
      for (let j = i + 1; j < 4; j++) {
        let linked = false;
        for (let u = 1; u < n; u++)
          if (gcd(u, n) === 1 && scale(keys[i], u, n) === keys[j]) { linked = true; break; }
        if (!linked) continue;
        tested++;
        if (seq('torus', NAMES[i], n, n)[0] === seq('torus', NAMES[j], n, n)[0]) torusHeld++;
        if (seq('mobius', NAMES[i], n, n)[0] === seq('mobius', NAMES[j], n, n)[0]) mobiusHeld++;
      }
  }
  check('unit scaling forces every torus equality it predicts (n=3..9)', torusHeld, tested);
  check('and the same predictions mostly FAIL on the Mobius band (the control)', mobiusHeld < tested, true);
}

// (H) added 2026-08-20: n divides every torus count, and only the torus.
// This is not an observation, it is the shortcut's own argument used as an assertion.
// On the torus, shifting every column by one carries non-attacking placements to
// non-attacking placements (attacks depend only on differences), and sigma^k fixes a
// placement only when k = 0 mod n, so the Z_n action is FREE and every orbit has size
// exactly n. Hence n | a(n). It costs nothing and it independently constrains the
// largest terms in the table, which are the ones no reader can check by hand.
// The control is the other three surfaces: a column shift does not commute with the
// half-twist, which is why leap2 refuses -t0 there, and their counts are duly NOT
// divisible by n. A check that passed everywhere would be reading nothing.
{
  const tsv = readFileSync(new URL('./terms-1-15.tsv', import.meta.url), 'utf8')
    .trim().split('\n').slice(1);
  const tab = new Map();
  for (const line of tsv) {
    const [topo, leaper, terms] = line.split('\t');
    tab.set(`${topo}/${leaper}`, terms.split(',').map(s => BigInt(s.trim())));
  }
  const nmax = tab.get('torus/knight').length;
  let torusDiv = 0, torusTried = 0, otherDiv = 0, otherTried = 0;
  for (let n = 5; n <= nmax; n++)
    for (const L of Object.keys(LEAPERS)) {
      const t = tab.get(`torus/${L}`)[n - 1];
      torusTried++; if (t % BigInt(n) === 0n) torusDiv++;
      for (const topo of ['flat', 'mobius', 'klein']) {
        const v = tab.get(`${topo}/${L}`)[n - 1];
        if (v === 0n) continue;              // a zero is divisible by everything
        otherTried++; if (v % BigInt(n) === 0n) otherDiv++;
      }
    }
  check(`n divides every torus count (the free column-shift orbit, n=5..${nmax})`, torusDiv, torusTried);
  check('and the same test FAILS on the twisted and flat boards (the control)',
    otherDiv < otherTried, true);
}

// (G) added 2026-08-20: the constraint count P, in closed form.
// The leading terms are a two-line count (see pairs-model.mjs), and they are the
// reason the four surfaces sit where they do. Asserted here rather than only in
// pairs-model.mjs so the lab's own gate goes red if the geometry ever moves.
{
  const P = (topo, n, V) => {
    const adj = attackGraph(topo, n, V); let p = 0;
    for (let u = 0; u < n * n; u++) {
      const ru = (u / n) | 0, cu = u % n;
      for (let w = u + 1; w < n * n; w++) {
        if (!((adj[u] >> BigInt(w)) & 1n)) continue;
        const rw = (w / n) | 0, cw = w % n;
        if (ru === rw || cu === cw) continue;
        p++;
      }
    }
    return p;
  };
  let flatOk = 0, torusOk = 0, mobLin = 0, kleinConst = 0, trials = 0;
  for (const L of Object.keys(LEAPERS)) {
    const [a, b] = LEAPERS[L], V = leaperVectors(a, b);
    for (let n = 10; n <= 16; n++) {
      trials++;
      if (P('flat', n, V) === 4 * (n - a) * (n - b)) flatOk++;
      if (P('torus', n, V) === 4 * n * n) torusOk++;
      // Mobius: one free boundary, so exactly 2(a+b)n below the closed value,
      // up to the O(1) same-row/column leftovers. Bound that leftover.
      const mobGap = 4 * n * n - P('mobius', n, V) - 2 * (a + b) * n;
      if (mobGap >= 0 && mobGap <= 16) mobLin++;
      // Klein: closed in both directions, so no term of order n at all.
      const kGap = 4 * n * n - P('klein', n, V);
      if (kGap >= 0 && kGap <= 16) kleinConst++;
    }
  }
  check('flat constraint count is exactly 4(n-a)(n-b), n=10..16, all four leapers', flatOk, trials);
  check('torus constraint count is exactly 4n^2 over the same range', torusOk, trials);
  check('Mobius sits 2(a+b)n below it, to within O(1)', mobLin, trials);
  check('Klein sits below it by O(1) only, with no term of order n', kleinConst, trials);
  // The control: the boundary law must DISTINGUISH the surfaces. If the Mobius
  // linear term were also 0, the comparison above would be reading nothing.
  const [ka, kb] = LEAPERS.knight, KV = leaperVectors(ka, kb);
  check('and the law can fire: Mobius P at n=16 is not the torus value',
    P('mobius', 16, KV) !== P('torus', 16, KV), true);
}

console.log(`\n${pass}/${pass + fail} PASS${fail ? `  (${fail} FAIL)` : ''}`);
process.exit(fail ? 1 : 0);
