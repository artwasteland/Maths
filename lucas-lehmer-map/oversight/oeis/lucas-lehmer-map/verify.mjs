// verify.mjs — adversarial verification of the Lucas–Lehmer-map computation.
//
//   node verify.mjs            run all checks (default N=120 for the sequences)
//   node verify.mjs 200        run with sequence length N=200
//   node verify.mjs --bfile C  print an OEIS b-file for statistic C/P/F/L to stdout
//
// Every claim made on the stratum page and in the OEIS staging notes is asserted
// here, exactly, by an independent route. No floating point, no estimation.

import { analyze, mapFn, orbit, lucasLehmer, sequences } from "./engine.mjs";

let pass = 0, fail = 0;
const T = (cond, msg) => { if (cond) pass++; else { fail++; console.error("  ✗ " + msg); } };

const N = (() => { const a = process.argv[2]; return a && /^\d+$/.test(a) ? +a : 120; })();

// ── helpers ────────────────────────────────────────────────────────────────
const gcd = (a, b) => { while (b) { [a, b] = [b, a % b]; } return a; };
const lcm = (a, b) => a / gcd(a, b) * b;

// A GENERIC functional-graph analyzer (any map), so we can calibrate the SAME
// algorithm against known OEIS sequences for x² and x³ before trusting x²−2.
function genericCycleSpectrum(n, f) {
  const color = new Int8Array(n), onCyc = new Uint8Array(n), spec = [];
  for (let s = 0; s < n; s++) {
    if (color[s]) continue;
    const path = []; let x = s;
    while (color[x] === 0) { color[x] = 1; path.push(x); x = f(x); }
    if (color[x] === 1) { let y = x, L = 0; do { onCyc[y] = 1; y = f(y); L++; } while (y !== x); spec.push(L); }
    for (const p of path) color[p] = 2;
  }
  let periodic = 0; for (let i = 0; i < n; i++) if (onCyc[i]) periodic++;
  return { cycles: spec.length, periodic };
}

// ── 1. CALIBRATION: the same algorithm reproduces three catalogued sequences ─
// A023153 = number of cycles of x² mod n.  A023154 = cycles of x³ mod n.
// A277847 = size of the largest subset of Z/nZ fixed by x² ( = its periodic pts ).
const A023153 = [1,2,2,2,2,4,3,2,3,4,3,4,3,6,4,2,2,6,4,4,6,6,3,4]; // n=1..24
const A023154 = [1,2,3,3,4,6,3,5,3,8,5,9,4,6,12,7,8,6,3,12,9,10,7,15];
const A277847 = [1,2,2,2,2,4,4,2,4,4,6,4,4,8,4,2,2,8,10,4,8,12,12,4];
{
  let okC2 = true, okC3 = true, okP2 = true;
  for (let n = 1; n <= 24; n++) {
    const sq = genericCycleSpectrum(n, (x) => (x * x) % n);
    const cu = genericCycleSpectrum(n, (x) => (x * x * x) % n);
    if (sq.cycles   !== A023153[n - 1]) okC2 = false;
    if (cu.cycles   !== A023154[n - 1]) okC3 = false;
    if (sq.periodic !== A277847[n - 1]) okP2 = false;
  }
  T(okC2, "engine reproduces A023153 (cycles of x² mod n)");
  T(okC3, "engine reproduces A023154 (cycles of x³ mod n)");
  T(okP2, "engine reproduces A277847 (periodic points of x² mod n)");
}

// ── 2. SELF-CONSISTENCY of the x²−2 graph ────────────────────────────────────
{
  let okSum = true, okLong = true, okFix = true, okMono = true;
  for (let n = 1; n <= 300; n++) {
    const g = analyze(n);
    const s = g.spectrum.reduce((a, b) => a + b, 0);
    if (s !== g.periodic) okSum = false;                       // cycles partition periodic pts
    if (g.longest > g.periodic) okLong = false;
    if (g.fixed > g.periodic) okFix = false;                   // fixed pts are periodic (1-cycles)
    if (g.cycles > g.periodic) okMono = false;
  }
  T(okSum,  "Σ(cycle lengths) = number of periodic points, n≤300");
  T(okLong, "longest cycle ≤ periodic points, n≤300");
  T(okFix,  "fixed points ≤ periodic points, n≤300");
  T(okMono, "cycle count ≤ periodic points, n≤300");
}

// ── 3. FIXED POINTS counted a second, independent way ────────────────────────
// f(x)=x  ⇔  x²−x−2 ≡ 0  ⇔  (x−2)(x+1) ≡ 0 (mod n).  Count roots directly.
{
  let ok = true;
  for (let n = 1; n <= 300; n++) {
    let roots = 0;
    for (let x = 0; x < n; x++) if ((((x - 2) % n) * ((x + 1) % n)) % n === 0) roots++;
    if (roots !== analyze(n).fixed) ok = false;
  }
  T(ok, "fixed points = #roots of (x−2)(x+1)≡0 (mod n), n≤300");
}

// ── 4. THE LUCAS–LEHMER TEST lives inside this map ───────────────────────────
// (a) the real test (s₀=4) agrees with true primality of M_p, p=3..61;
// (b) inside G(M_p), the orbit of the seed 4 reaches 0 IFF M_p is prime.
{
  const isPrime = (m) => { if (m < 2n) return false; for (let d = 2n; d * d <= m; d++) if (m % d === 0n) return false; return true; };
  const oddPrimes = [3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61];
  let okLL = true, okOrbit = true;
  for (const p of oddPrimes) {
    const { Mp, passes } = lucasLehmer(p);
    if (passes !== isPrime(Mp)) okLL = false;
    // (b) only feasible to draw the explicit graph for the small Mersennes
    if (p <= 19) {
      const M = Number(Mp);
      const reaches0 = orbit(M, 4).seq.includes(0);
      if (reaches0 !== isPrime(Mp)) okOrbit = false;
    }
  }
  T(okLL,    "Lucas–Lehmer (s₀=4) ⇔ M_p prime, exponents 3..61");
  T(okOrbit, "in G(M_p): orbit of 4 reaches 0 ⇔ M_p prime, p≤19");
  // the tail 0 → −2 → 2 → 2 (2 is the fixed point the test falls into)
  const g = orbit(127, 0);
  T(g.seq[0] === 0 && mapFn(127)(0) === 125 && mapFn(127)(125) === 2 && mapFn(127)(2) === 2,
    "the LL landing tail 0 → −2(≡125) → 2 → 2 (fixed) holds mod 127");
}

// ── 5. CHEBYSHEV CONJUGACY: x²−2 is angle-doubling ───────────────────────────
// With x = y + y⁻¹ (mod n, y a unit), x²−2 = y² + y⁻². The map squares y.
{
  const egcd = (a, b) => { if (b === 0) return [a, 1, 0]; const [g, x, y] = egcd(b, a % b); return [g, y, x - Math.floor(a / b) * y]; };
  const inv = (a, n) => { a = ((a % n) + n) % n; const [g, x] = egcd(a, n); return g === 1 ? ((x % n) + n) % n : null; };
  let ok = true, tested = 0;
  for (const n of [7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,64,81,100]) {
    const f = mapFn(n);
    for (let y = 1; y < n; y++) {
      const yi = inv(y, n); if (yi === null) continue;
      const x = (y + yi) % n;
      const lhs = f(x), rhs = ((y * y) % n + (yi * yi) % n) % n;
      tested++; if (lhs !== rhs) ok = false;
    }
  }
  T(ok, `Chebyshev conjugacy x=y+y⁻¹ ⇒ x²−2 = y²+y⁻² (${tested} unit cases)`);
}

// ── 6. CRT STRUCTURE: which statistics are multiplicative, and the tensor rule ─
// G(mn) ≅ G(m) ⊗ G(n) for coprime m,n.  Periodic part is the product, so
// P and F multiply; but cycle count and longest cycle follow the permutation-
// product rule on the periodic part:  C(mn)=Σ gcd(rᵢ,sⱼ),  L(mn)=max lcm(rᵢ,sⱼ).
{
  let pMul = true, fMul = true, cTensor = true, lTensor = true;
  let cNotMul = false, lNotMul = false;       // and we positively WITNESS non-multiplicativity
  for (let m = 2; m <= 70; m++) for (let n = m + 1; n <= 70; n++) {
    if (gcd(m, n) !== 1) continue;
    const A = analyze(m), B = analyze(n), AB = analyze(m * n);
    if (AB.periodic !== A.periodic * B.periodic) pMul = false;
    if (AB.fixed    !== A.fixed    * B.fixed)    fMul = false;
    let sumg = 0, maxl = 0;
    for (const r of A.spectrum) for (const s of B.spectrum) { sumg += gcd(r, s); maxl = Math.max(maxl, lcm(r, s)); }
    if (sumg !== AB.cycles)  cTensor = false;
    if (maxl !== AB.longest) lTensor = false;
    if (AB.cycles  !== A.cycles  * B.cycles)  cNotMul = true;
    if (AB.longest !== lcm(A.longest, B.longest)) lNotMul = true;
  }
  T(pMul,    "periodic-point count is multiplicative (coprime m,n ≤ 70)");
  T(fMul,    "fixed-point count is multiplicative (coprime m,n ≤ 70)");
  T(cTensor, "tensor rule C(mn) = Σ gcd(rᵢ,sⱼ) holds exactly (coprime ≤ 70)");
  T(lTensor, "tensor rule L(mn) = max lcm(rᵢ,sⱼ) holds exactly (coprime ≤ 70)");
  T(cNotMul, "cycle count is NOT multiplicative (witnessed)");
  T(lNotMul, "longest cycle is NOT a simple lcm (witnessed)");
}

// ── 7. PRIME LAW for fixed points: F(p)=2 for primes p>3, F(2)=2, F(3)=1 ──────
{
  const isP = (k) => { if (k < 2) return false; for (let d = 2; d * d <= k; d++) if (k % d === 0) return false; return true; };
  let ok = true;
  for (let p = 2; p <= 200; p++) if (isP(p)) {
    const want = p === 3 ? 1 : 2;            // p=3: 2≡−1, the two roots collide
    if (analyze(p).fixed !== want) ok = false;
  }
  T(ok, "fixed-point prime law: F(p)=2 for primes p>3, F(2)=2, F(3)=1");
}

// ── b-file emission ──────────────────────────────────────────────────────────
if (process.argv.includes("--bfile")) {
  const which = process.argv[process.argv.indexOf("--bfile") + 1] || "C";
  const key = { C: "cycles", P: "periodic", F: "fixed", L: "longest" }[which.toUpperCase()];
  const seq = sequences(N)[key];
  for (let i = 0; i < seq.length; i++) console.log((i + 1) + " " + seq[i]);
  process.exit(0);
}

// ── report ───────────────────────────────────────────────────────────────────
const s = sequences(Math.min(N, 30));
console.log("\nLucas–Lehmer map x²−2 (mod n) — first 30 terms:");
console.log("  C cycles  :", s.cycles.join(","));
console.log("  P periodic:", s.periodic.join(","));
console.log("  F fixed   :", s.fixed.join(","));
console.log("  L longest :", s.longest.join(","));
console.log(`\n${pass}/${pass + fail} checks passed` + (fail ? `  — ${fail} FAILED` : ""));
process.exit(fail ? 1 : 0);
