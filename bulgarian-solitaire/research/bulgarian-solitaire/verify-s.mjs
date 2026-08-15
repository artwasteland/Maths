// verify-s.mjs — offline proof that every claim in "The Longer Way Home" holds.
// s-Bulgarian solitaire (well-behaved sigma-Bulgarian, sigma(h)=min(h,s)); s=1 is classic.
//
// The trust ladder, in order:
//   0. The move is Hopkins's H_s three independent ways (min-subtraction; multiplicity formula;
//      s=1 == the classic Bulgarian move) — the map itself is never taken on one derivation.
//   1. s=1 reproduces SIX catalogued facts of the classic game exactly (Pascal, A037306, A123975,
//      A183110, the k^2-k Igusa bound, and the predecessor's total-settling sequence).
//   2. s>=2 recurrent counts reproduce Hopkins (2024, INTEGERS 24A #A9, Thm 5) closed form exactly.
//   3. The generalized Brandt law (unique attractor at n=s*T_k) and the NEW generalized Igusa law
//      (worst-case settling = k^2 for s>=2, k^2-k for s=1) hold on every checked case.
//   4. The two independent tail methods (reverse-BFS vs forward memo) agree on the WORST-CASE
//      tail. maxTailForward returns only the maximum, so this rung says nothing about
//      totalSettle; that cross-check lives in the staged directory's own gate.
// Only after all of that are the settling sequences reported as new / OEIS-absent.
//
// SCOPE. This file checks the MATHEMATICS. It does not open a b-file and never has, so a
// green run here says nothing about the numbers staged for deposit in
// oversight/oeis/generalized-bulgarian-solitaire/. Those are bound by
// `node oversight/oeis/generalized-bulgarian-solitaire/verify-staged.mjs`, which reads all ten
// staged b-files and reproduces every one of their 550 terms. Run both.
import { partitions, move, staircase, analyze, maxTailForward } from './engine-s.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; } else { fail++; console.log('  ✗ ' + m); } };
const eqArr = (a, b, L) => { for (let i = 0; i < L; i++) if (a[i] !== b[i]) return false; return true; };
const T = k => k * (k + 1) / 2;

// ---------- 0. the move, three ways ----------
// (a) classic Bulgarian move (predecessor engine, s=1 only)
function classicMove(p) { const piles = p.length, np = []; for (const x of p) if (x - 1 > 0) np.push(x - 1); np.push(piles); np.sort((a, b) => b - a); return np; }
// (b) Hopkins H_s via multiplicities: new leading part = s*P - sum_{j=1..s-1}(s-j)*m_j; others = x-s (>0).
function hopkinsMove(p, s) {
  const P = p.length, m = {}; for (const x of p) m[x] = (m[x] || 0) + 1;
  let lead = s * P; for (let j = 1; j < s; j++) lead -= (s - j) * (m[j] || 0);
  const np = []; for (const x of p) if (x - s > 0) np.push(x - s);
  if (lead > 0) np.push(lead); np.sort((a, b) => b - a); return np;
}
{
  let a = 0, b = 0, sums = 0;
  for (let n = 1; n <= 24; n++) for (const p of partitions(n)) {
    if (move(p, 1).join(',') !== classicMove(p).join(',')) a++;
    for (const s of [1, 2, 3, 4, 5]) {
      const mv = move(p, s);
      if (mv.join(',') !== hopkinsMove(p, s).join(',')) b++;
      if (mv.reduce((x, y) => x + y, 0) !== n) sums++;   // sum-preserving
    }
  }
  ok(a === 0, 's=1 move == classic Bulgarian move (all partitions n<=24)');
  ok(b === 0, 'move == Hopkins H_s via multiplicities, s=1..5 (all partitions n<=24)');
  ok(sums === 0, 'move preserves n (all partitions n<=24, s=1..5)');
}

// ---------- 1. s=1 anchors to the catalogued classic game ----------
const A007318 = [1, 2, 1, 3, 3, 1, 4, 6, 4, 1, 5, 10, 10, 5, 1, 6, 15, 20, 15, 6, 1, 7, 21, 35, 35, 21, 7, 1]; // recurrent (Etienne)
const A037306 = [1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 2, 1, 1, 1, 3, 4, 3, 1, 1, 1, 3, 5, 5, 3, 1, 1];        // numCycles
const A123975 = [0, 0, 1, 1, 2, 3, 5, 7, 10, 14, 20, 27, 37, 49, 66, 86, 113, 147, 190, 243];                // Garden of Eden
const A183110 = [1, 2, 1, 3, 3, 1, 4, 4, 4, 1, 5, 5, 5, 5, 1, 6, 6, 6, 6, 6, 1];                             // longest cycle
const PRED_totalSettle = [0, 0, 3, 3, 8, 33, 26, 41, 86, 267, 206, 242, 374, 831, 2133, 1629, 1517, 1919, 3353, 7209]; // predecessor S(n)
{
  const rec = [], cyc = [], goe = [], lon = [], tot = [];
  for (let n = 1; n <= 28; n++) { const a = analyze(n, 1); rec.push(a.recurrent); cyc.push(a.numCycles); goe.push(a.goe); lon.push(a.longest); tot.push(a.totalSettle); }
  ok(eqArr(rec, A007318, A007318.length), 's=1 recurrent == Pascal A007318 (Etienne)');
  ok(eqArr(cyc, A037306, A037306.length), 's=1 numCycles == A037306');
  ok(eqArr(goe, A123975, A123975.length), 's=1 Garden of Eden == A123975');
  ok(eqArr(lon, A183110, A183110.length), 's=1 longest cycle == A183110');
  ok(eqArr(tot, PRED_totalSettle, PRED_totalSettle.length), 's=1 total settling == predecessor S(n) (research/bulgarian-solitaire)');
}

// ---------- 2. s>=2 recurrent == Hopkins (2024) closed form ----------
// Thm 5: recurrent(n) = [x^m'] (1+x+...+x^s)^{m+1}, where n = s*T_m + m' (m largest with s*T_m<=n).
function genBinom(s, power, exp) { let c = [1]; for (let t = 0; t < power; t++) { const nc = new Array(c.length + s).fill(0); for (let i = 0; i < c.length; i++) for (let d = 0; d <= s; d++) nc[i + d] += c[i]; c = nc; } return c[exp] || 0; }
function hopkinsRecurrent(n, s) { let m = 0; while (s * T(m + 1) <= n) m++; const mp = n - s * T(m); return genBinom(s, m + 1, mp); }
{
  // s=1 is in the loop deliberately: the README claimed "s=1..5" while this check ran s=2..5,
  // so either the sentence or the loop had to change. The loop was the cheap one (~0.6s).
  let bad = 0;
  for (const s of [1, 2, 3, 4, 5]) for (let n = 1; n <= 40; n++) if (analyze(n, s).recurrent !== hopkinsRecurrent(n, s)) bad++;
  ok(bad === 0, 'recurrent count == Hopkins 2024 (INTEGERS 24A #A9, Thm 5) closed form, s=1..5 n<=40 (staged b-files reach n=55; indices 41..55 are checked in verify-staged.mjs, not here)');
  // corollary: s=2 recurrent at square n = central trinomial A002426
  const A002426 = [1, 1, 3, 7, 19, 51, 141, 393];
  let ct = 0; for (let m = 1; m <= 7; m++) if (analyze(m * m, 2).recurrent !== A002426[m]) ct++;
  ok(ct === 0, 's=2 recurrent at n=m^2 == central trinomial A002426 (corollary of Hopkins Thm 5)');
}

// ---------- 3. generalized Brandt + the NEW generalized Igusa law ----------
{
  let brandt = 0, igusa = 0, stair = 0;
  for (const s of [1, 2, 3, 4, 5, 6, 7]) {
    for (let k = 1; k <= 7; k++) {
      const n = s * T(k); if (n > 56) break;
      const a = analyze(n, s);
      if (a.recurrent !== 1 || a.numCycles !== 1 || a.fixed !== 1) brandt++;   // unique attractor
      const want = (s === 1) ? k * k - k : k * k;
      if (a.maxTail !== want) igusa++;                                          // worst-case settling law
      const sc = staircase(n, s);                                              // fixed point is the step-s staircase
      const expect = Array.from({ length: k }, (_, i) => s * (k - i));
      if (!sc || sc.join(',') !== expect.join(',')) stair++;
    }
  }
  ok(brandt === 0, 'generalized Brandt: n=s*T_k has a UNIQUE attractor (all hands converge), s=1..7');
  ok(stair === 0, 'the attractor at n=s*T_k is the step-s staircase (s*k, s*(k-1), ..., s)');
  ok(igusa === 0, 'generalized Igusa: worst-case settling at n=s*T_k = k^2 (s>=2) vs k^2-k (s=1) [NEW, verified]');
}

// ---------- 4. two independent tail methods agree ----------
{
  let bad = 0;
  for (const s of [1, 2, 3, 4]) for (let n = 1; n <= 30; n++) if (analyze(n, s).maxTail !== maxTailForward(n, s)) bad++;
  ok(bad === 0, 'reverse-BFS MAX tail == forward-memo MAX tail, s=1..4 n<=30 (maxTail only: maxTailForward returns the maximum, not the tail vector, so totalSettle is NOT cross-checked here — see verify-staged.mjs, which does it for s=2,3 n<=50)');
}

// ---------- 5. fixed-point n's = the s-staircase numbers (s=2 == quarter-squares A002620) ----------
{
  const A002620 = [1, 2, 4, 6, 9, 12, 16, 20, 25, 30, 36, 42, 49]; // quarter-squares floor((k+1)^2/4), k>=1
  const fp2 = []; for (let n = 1; n <= 49; n++) if (staircase(n, 2)) fp2.push(n);
  ok(fp2.join(',') === A002620.join(','), 's=2 fixed-point n = quarter-squares A002620 (floor((k+1)^2/4))');
}

// ---------- 6. the NEW sequences, put on the record ----------
// The 2026-07-19 OEIS-absence search is NOT logged anywhere in this repo, so it is printed below
// as what a session reported and not as a fact this file checks. Nothing here searches OEIS.
const NEW = {
  'total settling, s=2': analyzeSeq(2, 'totalSettle', 20),
  'total settling, s=3': analyzeSeq(3, 'totalSettle', 20),
  'Garden of Eden, s=2': analyzeSeq(2, 'goe', 20),
  'worst-case settling, s=2': analyzeSeq(2, 'maxTail', 24),
};
function analyzeSeq(s, key, N) { const a = []; for (let n = 1; n <= N; n++) a.push(analyze(n, s)[key]); return a; }

console.log('\n  ' + pass + '/' + (pass + fail) + ' checks passed.');
if (fail === 0) {
  console.log('\n  The settling sequences a 2026-07-19 session reported absent from OEIS');
  console.log('  (that search is not logged here, so this line is a pointer, not a check):');
  for (const [name, seq] of Object.entries(NEW)) console.log('    ' + name + ': ' + seq.join(', ') + ', ...');
}
process.exit(fail === 0 ? 0 : 1);
