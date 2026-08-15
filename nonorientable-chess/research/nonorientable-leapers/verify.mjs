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

console.log(`\n${pass}/${pass + fail} PASS${fail ? `  (${fail} FAIL)` : ''}`);
process.exit(fail ? 1 : 0);
