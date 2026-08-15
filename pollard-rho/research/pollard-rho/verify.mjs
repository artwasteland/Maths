// verify.mjs — every claim "The Shape of the Rho" makes, checked from scratch.
// Run: node research/pollard-rho/verify.mjs
//
// Two independent methods must agree on the graph structure (the calibration),
// Pollard's rho must actually factor a battery of semiprimes, and the random-map
// statistics must come out where Flajolet–Odlyzko (1990) say they should for a
// generic c — and visibly NOT for the degenerate c∈{0,−2}.

import {
  mapFn, analyze, orbit, pollardRho, rhoModP, gcd,
  meanRhoLen, expectedRhoLen, sequences,
} from './engine.mjs';

let pass = 0, fail = 0;
const eq = (a, b, msg) => {
  const ok = JSON.stringify(a) === JSON.stringify(b);
  console.log(`${ok ? 'ok  ' : 'FAIL'}  ${msg}`);
  if (ok) pass++; else { fail++; console.log(`      got ${JSON.stringify(a)}\n      exp ${JSON.stringify(b)}`); }
};
const ok = (cond, msg) => { console.log(`${cond ? 'ok  ' : 'FAIL'}  ${msg}`); cond ? pass++ : fail++; };

// ---------------------------------------------------------------------------
// A. CALIBRATION — analyze() vs a from-scratch brute force, all n≤200, several c.
//    Brute force owes nothing to the fast walk: it iterates every point and uses
//    a Map to find the cycle directly. Agreement on every (n,c) certifies analyze().
// ---------------------------------------------------------------------------
function bruteAnalyze(n, c) {
  const f = mapFn(n, c);
  const onCycle = new Uint8Array(n);
  const compId = new Int32Array(n).fill(-1);
  const cyclen = [];
  for (let s = 0; s < n; s++) {
    if (compId[s] !== -1) continue;
    // follow until we hit a node we've classified or repeat within this walk
    const seen = new Map(); const walk = [];
    let x = s;
    while (compId[x] === -1 && !seen.has(x)) { seen.set(x, walk.length); walk.push(x); x = f(x); }
    let cid;
    if (compId[x] !== -1) { cid = compId[x]; }
    else {                                    // new cycle, starts at first repeat
      const start = seen.get(x); let L = 0, y = x;
      do { onCycle[y] = 1; y = f(y); L++; } while (y !== x);
      cid = cyclen.push(L) - 1;
    }
    for (const w of walk) compId[w] = cid;
  }
  let periodic = 0, fixed = 0;
  for (let i = 0; i < n; i++) { if (onCycle[i]) periodic++; if (f(i) === i) fixed++; }
  cyclen.sort((a, b) => a - b);
  return { cycles: cyclen.length, periodic, fixed, longest: cyclen.length ? cyclen[cyclen.length - 1] : 0 };
}
let calOk = true;
for (const c of [0, 1, 2, 3, 5]) {
  for (let n = 1; n <= 200; n++) {
    const a = analyze(n, c), b = bruteAnalyze(n, c);
    if (a.cycles !== b.cycles || a.periodic !== b.periodic || a.fixed !== b.fixed || a.longest !== b.longest) {
      calOk = false; console.log(`   mismatch n=${n} c=${c}: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`); break;
    }
  }
}
ok(calOk, 'CALIBRATION: analyze() == brute force for all n≤200, c∈{0,1,2,3,5} (cycles, periodic, fixed, longest)');

// ---------------------------------------------------------------------------
// B. Fixed points of x²+c are exactly the roots of x²−x+c ≡ 0 (mod n).
// ---------------------------------------------------------------------------
{
  let allOk = true;
  for (const c of [1, 2, 4, 7]) for (let n = 1; n <= 300; n++) {
    let roots = 0; for (let x = 0; x < n; x++) if (((x * x - x + c) % n + n) % n === 0) roots++;
    if (analyze(n, c).fixed !== roots) { allOk = false; break; }
  }
  ok(allOk, 'fixed points of x²+c == #roots of x²−x+c (mod n), all n≤300, c∈{1,2,4,7}');
}

// ---------------------------------------------------------------------------
// C. POLLARD'S RHO actually factors a battery of semiprimes. Each result must be
//    a nontrivial divisor and the cofactor must multiply back to N exactly.
// ---------------------------------------------------------------------------
// CORRECTION 2026-07-27. The last entry used to read 3_037_000_499n * 3_037_000_493n
// and was labelled "balanced 10-digit". 3037000499 is NOT prime: it is 13 × 233615423.
// So that N was not a semiprime, and rho "solved" it in 4 iterations by finding the
// factor 13, which demonstrates nothing about the balanced case the label promised.
// 3037000493 is prime; its next prime neighbour is 3037000507. The pair below is a
// genuine balanced 10-digit semiprime, and rho now needs ~7×10^4 iterations for it,
// which is the √(πp/2) ≈ 6.9×10^4 the theory predicts. Third column, where present,
// is the set of factors the run is allowed to return, so the label is asserted and
// not merely printed.
const semiprimes = [
  [101n * 103n, 'small', [101n, 103n]],
  [10_007n * 10_009n, '~10^8', [10_007n, 10_009n]],
  [1_000_003n * 1_000_033n, '~10^12, balanced', [1_000_003n, 1_000_033n]],
  [2n * 3n * 5n * 9999991n, 'composite w/ small + large', null],
  [104_729n * 1_299_709n, 'two primes (10000th & 100000th)', [104_729n, 1_299_709n]],
  [3_037_000_493n * 3_037_000_507n, '~9.2×10^18, balanced 10-digit semiprime', [3_037_000_493n, 3_037_000_507n]],
];
for (const [N, label, mustBe] of semiprimes) {
  let r = pollardRho(N, { c: 1n, x0: 2n });
  // retry policy mirrors the page: bump c until a nontrivial factor appears
  let cc = 1n;
  while (!r.factor && cc < 20n) { cc++; r = pollardRho(N, { c: cc, x0: 2n }); }
  const f = r.factor;
  const nontrivial = f && f > 1n && f < N && N % f === 0n;
  // For the labelled semiprimes, the factor must be one of the two primes claimed:
  // a small factor turning up here would mean the "semiprime" is not one.
  const asClaimed = !mustBe || (nontrivial && mustBe.some((p) => p === f));
  ok(nontrivial && asClaimed, `rho factors ${label}: ${N} = ${f} × ${f ? N / f : '?'} (${r.iters} iters, c=${cc})`);
}

// ---------------------------------------------------------------------------
// D. THE HIDDEN SMALL RHO. For N = p·q the iteration, reduced mod the smaller
//    prime p, collides in O(√p) steps — vastly sooner than mod N (~√N). That
//    early collision mod p, invisible in Z_N, is exactly what the gcd catches.
// ---------------------------------------------------------------------------
{
  const p = 1_000_003n, q = 1_000_033n, N = p * q, c = 1n, x0 = 2n;
  const modP = rhoModP(p, c, x0);
  const expN = expectedRhoLen(Number(N));    // √(πN/2): the scale of a rho mod N
  ok(modP.rhoLen < 4000, `mod p=${p}: rho closes in ${modP.rhoLen} steps (~√p=${Math.round(Math.sqrt(Number(p)))})`);
  ok(modP.rhoLen < expN / 100, `that is ≥100× shorter than the √(πN/2)≈${Math.round(expN)} a rho mod N would run — the hidden rho closes first`);
  // Floyd detects at a step set by the mod-p rho length, not the mod-N scale.
  const r = pollardRho(N, { c, x0 });
  ok(r.factor === p || r.factor === q, `Floyd finds the factor (${r.factor}) in ${r.iters} iters ≪ √N=${Math.round(Math.sqrt(Number(N)))}`);
  ok(r.iters < 5 * modP.rhoLen, `iters (${r.iters}) ~ the mod-p rho length (${modP.rhoLen}), not the mod-N scale (${Math.round(expN)})`);
}

// ---------------------------------------------------------------------------
// E. RANDOM-MAP AGREEMENT. Averaged over generic c, the mean rho length of
//    x²+c mod p tracks Flajolet–Odlyzko's √(πp/2) for a true random map.
//    EMPIRICAL — labelled as such; x²+c is conjectured, not proven, random-like.
// ---------------------------------------------------------------------------
{
  const primes = [401, 809, 1601, 3209, 6421];
  // average over MANY generic c (exclude the degenerate 0 and −2): noise ~1/√#c
  const worstOf = [];
  for (const p of primes) {
    const cs = [];
    for (let c = 1; c < p; c++) { const cm = c % p; if (cm !== 0 && cm !== (p - 2) % p) cs.push(c); }
    const measured = meanRhoLen(p, cs);      // mean over (nearly) all c and all seeds
    const predicted = expectedRhoLen(p);
    const relErr = Math.abs(measured - predicted) / predicted;
    worstOf.push(relErr);
    console.log(`      p=${p}: mean ρ over all generic c =${measured.toFixed(1)}  √(πp/2)=${predicted.toFixed(1)}  err=${(relErr * 100).toFixed(1)}%`);
  }
  const worst = Math.max(...worstOf);
  ok(worst < 0.06, `x²+c averaged over all generic c matches √(πp/2) within 6% across p∈{401..6421} (worst ${(worst * 100).toFixed(1)}%)`);
}

// ---------------------------------------------------------------------------
// F. THE DEGENERATE c. c≡0 (x→x²) and c≡−2 (Chebyshev, the Lucas–Lehmer map)
//    are the textbook "never use these" choices — their graphs are NOT random.
//    We show c=0 collapses far below √(πp/2); c=−2 is also visibly off.
// ---------------------------------------------------------------------------
{
  const oddpart = (m) => { while (m % 2 === 0) m /= 2; return m; };
  const isPrime = (k) => { if (k < 2) return false; for (let d = 2; d * d <= k; d++) if (k % d === 0) return false; return true; };
  // F1 (EXACT): periodic points of x→x² mod p = 1 + oddpart(p−1). The map is rigidly
  // the doubling map on the cyclic group Z_{p−1} plus the fixed point 0 — nothing random.
  let formulaOk = true;
  for (let p = 3; p < 2000; p++) {
    if (!isPrime(p)) continue;
    if (analyze(p, 0).periodic !== 1 + oddpart(p - 1)) { formulaOk = false; console.log(`   c=0 formula breaks at p=${p}`); break; }
  }
  ok(formulaOk, 'EXACT: periodic points of x→x² mod p == 1 + oddpart(p−1), all primes p<2000 (rigid, not random)');

  // F2: that exact count is FAR from a random map's √(πp/2) — and so is c=−2 —
  // while generic c sits near it. Show the gap with the periodic-point count.
  const primes = [401, 809, 1601, 3209, 6421];
  let c0Far = true, cm2Far = true;
  for (const p of primes) {
    const predPts = expectedRhoLen(p);                    // E[#cyclic pts] ~ √(πp/2) too
    const pts0 = analyze(p, 0).periodic;
    const ptsM2 = analyze(p, ((-2) % p + p) % p).periodic;
    // mean periodic points over generic c
    let sum = 0, cnt = 0;
    for (let c = 1; c < p; c++) { const cm = c % p; if (cm === 0 || cm === (p - 2) % p) continue; sum += analyze(p, c).periodic; cnt++; }
    const ptsGen = sum / cnt;
    const e0 = Math.abs(pts0 - predPts) / predPts, eM2 = Math.abs(ptsM2 - predPts) / predPts, eGen = Math.abs(ptsGen - predPts) / predPts;
    console.log(`      p=${p}: √(πp/2)=${predPts.toFixed(1)}  generic c→${ptsGen.toFixed(1)} (${(eGen*100).toFixed(0)}%)  c=0→${pts0} (${(e0*100).toFixed(0)}%)  c=−2→${ptsM2} (${(eM2*100).toFixed(0)}%)`);
    if (!(e0 > 3 * eGen)) c0Far = false;
    if (!(eM2 > eGen)) cm2Far = false;
  }
  ok(c0Far, 'c=0 periodic-point count deviates from √(πp/2) by ≥3× the generic-c deviation (non-random)');
  ok(cm2Far, 'c=−2 (the Lucas–Lehmer map) deviates from √(πp/2) more than generic c — the other classic "avoid"');
}

// ---------------------------------------------------------------------------
// G. The rho-length constant itself: √(π/2) = 1.25331…  (the birthday constant).
// ---------------------------------------------------------------------------
ok(Math.abs(expectedRhoLen(1) - 1.2533141373) < 1e-9, '√(π/2) = 1.25331… (the constant in front of √n)');

// ---------------------------------------------------------------------------
// H. CANDIDATE NEW SEQUENCES — the cycle-structure statistics of x²+1 mod n.
//    Printed for an OEIS-absence check (the P2 bonus). Computed exactly.
// ---------------------------------------------------------------------------
{
  const N = 40;
  const s1 = sequences(N, 1);
  console.log('\n   x²+1 mod n, n=1..40 (exact):');
  console.log('     cycles  :', s1.cycles.join(','));
  console.log('     periodic:', s1.periodic.join(','));
  console.log('     fixed   :', s1.fixed.join(','));
  console.log('     longest :', s1.longest.join(','));
  // summed over c=0..n-1 (a c-independent invariant of the modulus)
  const periodicSum = [], cyclesSum = [];
  for (let n = 1; n <= N; n++) {
    let ps = 0, cs = 0;
    for (let c = 0; c < n; c++) { const g = analyze(n, c); ps += g.periodic; cs += g.cycles; }
    periodicSum.push(ps); cyclesSum.push(cs);
  }
  console.log('   Σ_c periodic points of x²+c mod n, n=1..40:');
  console.log('     ', periodicSum.join(','));
  console.log('   Σ_c cycles of x²+c mod n, n=1..40:');
  console.log('     ', cyclesSum.join(','));
}

// ---------------------------------------------------------------------------
// I–K. THE SPECIAL-c THEORY, DERIVED (see research/pollard-rho/special-c.md).
//    The two textbook "avoid" maps are rigid: their periodic structure is fixed
//    by multiplicative order theory. We certify the closed forms TWO ways —
//    by the formula, AND by constructing the periodic set from group theory and
//    comparing it element-for-element to what the graph walker analyze() finds.
// ---------------------------------------------------------------------------
{
  const oddpart = (m) => { m = Math.abs(m); while (m % 2 === 0) m /= 2; return m; };
  const isPrime = (k) => { if (k < 2) return false; for (let d = 2; d * d <= k; d++) if (k % d === 0) return false; return true; };
  const powmod = (a, e, m) => { a = ((a % m) + m) % m; let r = 1; while (e > 0) { if (e & 1) r = (r * a) % m; a = (a * a) % m; e = Math.floor(e / 2); } return r; };
  const divisors = (n) => { const d = []; for (let i = 1; i * i <= n; i++) if (n % i === 0) { d.push(i); if (i !== n / i) d.push(n / i); } return d; };
  const phi = (n) => { let r = n, m = n; for (let p = 2; p * p <= m; p++) { if (m % p === 0) { while (m % p === 0) m /= p; r -= r / p; } } if (m > 1) r -= r / m; return r; };
  const ord = (a, m) => { if (m === 1) return 1; a %= m; let k = 1, c = a % m; while (c !== 1) { c = (c * a) % m; k++; if (k > m + 2) return -1; } return k; };
  const doublingOrbits = (b) => { let s = 0; for (const d of divisors(b)) s += phi(d) / ord(2, d); return s; };

  // The actual periodic-point SET of x²+c mod p, straight from the functional graph.
  const periodicSet = (p, c) => {
    const f = mapFn(p, c), color = new Int8Array(p), onc = new Set();
    for (let st = 0; st < p; st++) {
      if (color[st]) continue;
      const seen = new Set(); const path = []; let x = st;
      while (color[x] === 0 && !seen.has(x)) { seen.add(x); color[x] = 1; path.push(x); x = f(x); }
      if (seen.has(x)) { let y = x; do { onc.add(y); y = f(y); } while (y !== x); }
      for (const w of path) color[w] = 2;
    }
    return onc;
  };
  const setEq = (A, B) => A.size === B.size && [...A].every((x) => B.has(x));

  // --- I. c=0 : full structural theory (Theorem 1) ------------------------
  let f0form = true, f0fix = true, f0long = true, f0cyc = true;
  for (let p = 3; p < 2000; p++) {
    if (!isPrime(p)) continue;
    const b = oddpart(p - 1), g = analyze(p, 0);
    if (g.periodic !== 1 + b) { f0form = false; break; }
    if (g.fixed !== 2) f0fix = false;
    if (g.longest !== Math.max(1, ord(2, b))) f0long = false;
    if (g.cycles !== 1 + doublingOrbits(b)) f0cyc = false;
  }
  ok(f0form, 'Thm1 c=0: periodic points == 1 + oddpart(p−1), all primes p<2000');
  ok(f0fix,  'Thm1 c=0: fixed points == 2 (x=0,1), all primes p<2000');
  ok(f0long, 'Thm1 c=0: longest cycle == ord_2(oddpart(p−1)), all primes p<2000');
  ok(f0cyc,  'Thm1 c=0: #cycles == 1 + Σ_{d|b} φ(d)/ord_d(2),  b=oddpart(p−1), all primes p<2000');

  // I-set. The periodic set IS {0} ∪ (odd-order subgroup of F_p^*), built independently.
  let f0set = true;
  for (let p = 3; p < 500; p++) {
    if (!isPrime(p)) continue;
    const b = oddpart(p - 1), built = new Set([0]);
    for (let x = 1; x < p; x++) if (powmod(x, b, p) === 1) built.add(x);   // odd-order ⟺ x^oddpart(p−1)=1
    if (!setEq(built, periodicSet(p, 0))) { f0set = false; console.log(`   c=0 set breaks at p=${p}`); break; }
  }
  ok(f0set, 'Thm1 c=0: periodic SET == {0} ∪ {x : x^oddpart(p−1)=1} (set equality, primes p<500)');

  // --- J. c=−2 : the Lucas–Lehmer map (Theorem 2) -------------------------
  let fm2form = true, fm2fix = true;
  for (let p = 3; p < 2000; p++) {
    if (!isPrime(p)) continue;
    const pred = (oddpart(p - 1) + oddpart(p + 1)) / 2;
    if (analyze(p, -2).periodic !== pred) { fm2form = false; console.log(`   c=−2 formula breaks at p=${p}`); break; }
    const expectFixed = (p === 3) ? 1 : 2;                                  // 2≡−1 only at p=3
    if (analyze(p, -2).fixed !== expectFixed) fm2fix = false;
  }
  ok(fm2form, 'Thm2 c=−2: periodic points == (oddpart(p−1)+oddpart(p+1))/2, all primes p<2000  [NEW exact form]');
  ok(fm2fix,  'Thm2 c=−2: fixed points == 2 (x=2,−1), collapsing to 1 at p=3, all primes p<2000');

  // J-set. Build the c=−2 periodic set from group theory: x = y+1/y over the
  // odd-order elements of F_p^* (order p−1) AND of the norm-1 subgroup of F_{p²}
  // (order p+1). The two routes together must reproduce the graph's periodic set.
  const nonResidue = (p) => { for (let s = 2; s < p; s++) if (powmod(s, (p - 1) / 2, p) === p - 1) return s; return -1; };
  const mul2 = (A, B, s, p) => [(((A[0] * B[0] + A[1] * B[1] % p * s) % p) + p) % p, (((A[0] * B[1] + A[1] * B[0]) % p) + p) % p];
  const pow2 = (A, e, s, p) => { let R = [1, 0]; while (e > 0) { if (e & 1) R = mul2(R, A, s, p); A = mul2(A, A, s, p); e = Math.floor(e / 2); } return R; };
  let fm2set = true;
  for (let p = 5; p < 200; p++) {
    if (!isPrime(p)) continue;
    const b1 = oddpart(p - 1), b2 = oddpart(p + 1), s = nonResidue(p), built = new Set();
    for (let y = 1; y < p; y++) if (powmod(y, b1, p) === 1) built.add(((y + powmod(y, p - 2, p)) % p + p) % p); // F_p^* side
    for (let a = 0; a < p; a++) for (let bb = 0; bb < p; bb++) {            // norm-1 F_{p²} side
      if ((((a * a - s * bb * bb) % p) + p) % p !== 1) continue;            //   norm == 1
      const yb = pow2([a, bb], b2, s, p);
      if (yb[0] === 1 && yb[1] === 0) built.add((2 * a) % p);               //   odd order ⟹ x = y+1/y = 2a
    }
    if (!setEq(built, periodicSet(p, -2))) { fm2set = false; console.log(`   c=−2 set breaks at p=${p}`); break; }
  }
  ok(fm2set, 'Thm2 c=−2: periodic SET == {y+1/y : odd-order y in F_p^* ∪ norm-1 F_{p²}} (set equality, primes p<200)');

  // --- K. The conjugacy the c=−2 proof rides on: (y+1/y)²−2 == y²+1/y². ----
  let conj = true;
  for (const p of [7, 11, 13, 31, 101]) {
    for (let y = 1; y < p; y++) {
      const yi = powmod(y, p - 2, p);
      const lhs = ((((y + yi) % p) ** 2 - 2) % p + p) % p;
      const rhs = ((y * y % p + yi * yi % p) % p + p) % p;
      if (lhs !== rhs) { conj = false; break; }
    }
  }
  ok(conj, 'Chebyshev identity (y+1/y)²−2 == y²+1/y² holds over F_p (exhaustive, p∈{7,11,13,31,101})');
}

console.log(`\n${pass}/${pass + fail} checks passed${fail ? ` — ${fail} FAILED` : ''}.`);
process.exit(fail ? 1 : 0);
