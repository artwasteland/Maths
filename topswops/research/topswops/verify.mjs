// Topswops: the verifier for the ENGINE and the stratum's mathematics,
// calibration-first: the engine must reproduce the KNOWN sequences exactly before
// any NEW claim is trusted.
//
//   node research/topswops/verify.mjs
//
// Prints PASS/FAIL per check and an N/N tally; exits non-zero on any failure.
//
// WHAT THIS FILE DOES NOT DO. It never opens
// oversight/oeis/topswops-total-flips/b-file.txt. Every value below is a literal
// typed into this file, so this verifier stays green no matter what the staged
// b-file contains. The 2026-07-20 coverage audit found that, and a mutation
// prober confirmed it: corrupting any staged term left this script's output and
// exit code byte-identical
// (research/oeis-term-coverage/coverage-before.json, dirs["topswops-total-flips"]).
// Binding the staged artifact is a different job, done by
// oversight/oeis/topswops-total-flips/verify-staged.mjs, which ships beside the
// b-file. Reach, stated by index: the checks below cover the total-steps
// sequence for n=1..11 only. The staged a(12) and a(13) are not evaluated here.

import {
  statsFull, maxAndSum,
  gardenDirect, gardenIE, A000255,
  perms, flipOnce, rank, factorials,
} from './engine.mjs';

let pass = 0, fail = 0;
const ok = (name, cond, got, want) => {
  if (cond) { pass++; console.log(`  ok   ${name}`); }
  else { fail++; console.log(`  FAIL ${name}\n         got  ${got}\n         want ${want}`); }
};
const eqArr = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

console.log('TOPSWOPS — verification\n');

// Compute the full statistics for n = 1..10 once.
const S = [];
for (let n = 1; n <= 10; n++) S.push(statsFull(n));
const col = (k) => S.map((s) => s[k]);

// ---------------------------------------------------------------------------
// CALIBRATION 1 — max flips reproduces OEIS A000375 (Topswops).  KNOWN; not ours.
// ---------------------------------------------------------------------------
const A000375 = [0, 1, 2, 4, 7, 10, 16, 22, 30, 38]; // a(1..10), oeis.org/A000375
ok('max flips  M(1..10) = A000375', eqArr(col('M'), A000375), col('M').join(','), A000375.join(','));
// one more term, computed the fast way, as an extra calibration point: A000375(11)=51
ok('max flips  M(11) = 51 (A000375)', maxAndSum(11).M === 51, maxAndSum(11).M, 51);

// ---------------------------------------------------------------------------
// CALIBRATION 2 — count of champion decks reproduces OEIS A123398.  KNOWN; not ours.
// ---------------------------------------------------------------------------
const A123398 = [1, 1, 2, 2, 1, 5, 2, 1, 1, 1]; // a(1..10), oeis.org/A123398
ok('champions  champ(1..10) = A123398', eqArr(col('champ'), A123398), col('champ').join(','), A123398.join(','));

// ---------------------------------------------------------------------------
// THE NEW SEQUENCE — total flips over all n! decks.  Absent from OEIS (2026-06-24).
// These literals are recomputed from the engine, which catches a change to the
// ENGINE.  They are NOT read from the staged b-file, so drift in that file is not
// caught here; oversight/oeis/topswops-total-flips/verify-staged.mjs does that.
// ---------------------------------------------------------------------------
const SUM = [0, 1, 6, 38, 265, 2115, 18508, 180260, 1911505, 22169434]; // a(1..10)
ok('total flips SUM(1..10) staged values', eqArr(col('sum').map(String), SUM.map(String)), col('sum').join(','), SUM.join(','));
ok('total flips SUM(11) = 277931375', maxAndSum(11).sum === 277931375n, String(maxAndSum(11).sum), '277931375');

// ---------------------------------------------------------------------------
// THE STRUCTURAL RESULT — the Garden of Eden equals A000255(n-1), three ways.
// (Decks no flip can produce: permutations with no fixed point in positions 2..n.)
// ---------------------------------------------------------------------------
// 3a — the flip-map preimage count (statsFull.sources) matches the direct characterization.
ok('garden  sources = no-fixed-point-after-top, n=1..8',
   [1, 2, 3, 4, 5, 6, 7, 8].every((n) => statsFull(n).sources === gardenDirect(n)),
   [1, 2, 3, 4, 5, 6, 7, 8].map((n) => statsFull(n).sources).join(','),
   [1, 2, 3, 4, 5, 6, 7, 8].map((n) => gardenDirect(n)).join(','));
// 3b — direct = inclusion-exclusion = A000255(n-1), n=1..9.
{
  const a255 = A000255(12);
  let allEq = true, gotL = [], wantL = [];
  for (let n = 1; n <= 9; n++) {
    const d = gardenDirect(n), ie = gardenIE(n), a = a255[n - 1];
    gotL.push(`${d}/${ie}`); wantL.push(a);
    if (!(d === ie && ie === a)) allEq = false;
  }
  ok('garden  direct = inclusion-exclusion = A000255(n-1), n=1..9', allEq, gotL.join(' '), wantL.join(','));
}

// 3c — PROVE the characterization computationally: for every deck of size n<=7, the
// flip map's image is EXACTLY the decks q with some k in 2..n where q[k-1]==k.
{
  let allMatch = true;
  for (let n = 2; n <= 7 && allMatch; n++) {
    const fact = factorials(n);
    const Nf = fact[n];
    const inImage = new Uint8Array(Nf);
    const base = []; for (let i = 1; i <= n; i++) base.push(i);
    for (const p of perms(base)) if (p[0] !== 1) inImage[rank(flipOnce(p), n, fact)] = 1;
    // now compare to the predicate
    for (const q of perms(base)) {
      let pred = 0;
      for (let k = 2; k <= n; k++) if (q[k - 1] === k) { pred = 1; break; }
      if (inImage[rank(q, n, fact)] !== pred) { allMatch = false; break; }
    }
  }
  ok('garden  image(flip) = { has a fixed point at some position 2..n }, n<=7', allMatch, '', 'exact match');
}

// ---------------------------------------------------------------------------
// A BONUS FACT shown in the stratum: every flip-count from 0 to M(n) is achieved,
// so the number of distinct flip-counts is exactly M(n)+1.
// ---------------------------------------------------------------------------
ok('distinct flip-counts = M+1, n=1..10',
   S.every((s) => s.distinct === s.M + 1),
   S.map((s) => `${s.distinct}/${s.M + 1}`).join(' '), 'all equal');

console.log(`\n${pass}/${pass + fail} checks passed.`);
process.exit(fail ? 1 : 0);
