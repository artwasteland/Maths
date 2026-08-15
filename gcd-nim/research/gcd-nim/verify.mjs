// gcd-nim — verifier. Never one path.
//
// Run: node research/gcd-nim/verify.mjs
//
// Establishes, by independent methods that must agree:
//   COPRIME NIM  (remove d, gcd(d,n)=1):  G(0)=0; G(even>=2)=0; G(1)=1;
//                G(odd n>=3) = index of least prime factor of n  (= A055396(n)).
//                => a THEOREM tying a Nim variant to the least-prime-factor index.
//                The odd-pile content is a KNOWN OEIS sequence (A055396); not new.
//   COMMON NIM   (remove d, gcd(d,n)>1):  G(0)=G(1)=0 (the only P-positions, PROVED);
//                G(even 2k)=k; the odd-pile Grundy values are erratic and
//                ABSENT from OEIS (checked by data 2026-07-19) => the discovery.
//
// Cross-checks: (A) direct mex; (B) a structurally different factor-set path;
// (C) a true two-heap minimax whose P/N outcome must equal (G[a] xor G[b])==0;
// plus textbook positive controls (subtraction games) and reproduction of the
// published A055396.
'use strict';
import { gcd, grundy, coprimeMove, commonMove, grundyByFactorSets, lpfIndex } from './engine.mjs';

let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log(`  ok   ${name}`); }
  else { fail++; console.log(`  FAIL ${name}`, extra ?? ''); }
};
const arrEq = (a, b, n) => { for (let i = 0; i <= n; i++) if (a[i] !== b[i]) return i; return -1; };

const N = 20000;
console.log(`node ${process.version}  N=${N}\n`);

const gCop = grundy(N, coprimeMove);
const gCom = grundy(N, commonMove);

// ---------------------------------------------------------------------------
console.log('POSITIVE CONTROLS (the mex harness reproduces known results):');
// (1) subtraction game S={1,2}: textbook Grundy = n mod 3
{
  const g = grundy(300, (d) => d === 1 || d === 2);
  let good = true; for (let n = 0; n <= 300; n++) if (g[n] !== n % 3) good = false;
  ok('S={1,2} Grundy == n mod 3 (Winning Ways)', good);
}
// (2) subtraction game S={1,2,3}: Grundy = n mod 4
{
  const g = grundy(300, (d) => d >= 1 && d <= 3);
  let good = true; for (let n = 0; n <= 300; n++) if (g[n] !== n % 4) good = false;
  ok('S={1,2,3} Grundy == n mod 4 (Winning Ways)', good);
}
// (3) "take any amount" (all d legal): Grundy(n) = n
{
  const g = grundy(300, () => true);
  let good = true; for (let n = 0; n <= 300; n++) if (g[n] !== n) good = false;
  ok('take-any Grundy == n', good);
}
// (4) reproduce the PUBLISHED sequence A055396 (index of least prime factor)
{
  const idx = lpfIndex(N);
  // A055396 leading terms, transcribed from OEIS (offset 1): a(1..24)
  const A055396 = [0,0,1,2,1,3,1,4,1,2,1,5,1,6,1,2,1,7,1,8,1,2,1,9,1]; // index 0 unused; a(1)=0...
  let good = true; for (let n = 1; n <= 24; n++) if (idx[n] !== A055396[n]) good = false;
  ok('least-prime-factor sieve reproduces A055396 (n=1..24)', good);
}

// ---------------------------------------------------------------------------
console.log('\nCROSS-PATH AGREEMENT (two structurally different Grundy computations):');
{
  const M = 4000;
  const gCop2 = grundyByFactorSets(M, false);
  const gCom2 = grundyByFactorSets(M, true);
  ok('Coprime: mex path == factor-set path (n=0..4000)', arrEq(gCop, gCop2, M) === -1, arrEq(gCop, gCop2, M));
  ok('Common:  mex path == factor-set path (n=0..4000)', arrEq(gCom, gCom2, M) === -1, arrEq(gCom, gCom2, M));
}

// ---------------------------------------------------------------------------
console.log('\nTWO-HEAP MINIMAX == Sprague-Grundy XOR (independent validation of the values):');
function twoHeapAgrees(allow, g, M) {
  const P = Array.from({ length: M + 1 }, () => new Uint8Array(M + 1)); // 1 = P-position
  for (let a = 0; a <= M; a++) for (let b = 0; b <= M; b++) {
    let isP = true;
    for (let d = 1; d <= a && isP; d++) if (allow(d, a) && P[a - d][b]) isP = false;
    for (let d = 1; d <= b && isP; d++) if (allow(d, b) && P[a][b - d]) isP = false;
    P[a][b] = isP ? 1 : 0;
  }
  for (let a = 0; a <= M; a++) for (let b = 0; b <= M; b++)
    if (((g[a] ^ g[b]) === 0 ? 1 : 0) !== P[a][b]) return [a, b];
  return null;
}
{
  const M = 60;
  ok('Coprime: 2-heap minimax == (G[a]^G[b]==0), a,b<=60', twoHeapAgrees(coprimeMove, gCop, M) === null, twoHeapAgrees(coprimeMove, gCop, M));
  ok('Common:  2-heap minimax == (G[a]^G[b]==0), a,b<=60', twoHeapAgrees(commonMove, gCom, M) === null, twoHeapAgrees(commonMove, gCom, M));
}

// ---------------------------------------------------------------------------
console.log('\nCOPRIME NIM — the theorem:');
{
  const idx = lpfIndex(N);
  let evenOK = true, oddOK = true, firstOddExc = null;
  for (let n = 2; n <= N; n++) {
    if (n % 2 === 0) { if (gCop[n] !== 0) evenOK = false; }
    else if (gCop[n] !== idx[n] && firstOddExc === null) { oddOK = false; firstOddExc = [n, gCop[n], idx[n]]; }
  }
  ok('G(even n) == 0  (n=2..N)', evenOK);
  ok('G(1) == 1 (boundary; 1 has no prime factor)', gCop[1] === 1);
  ok('G(odd n>=3) == index of least prime factor (== A055396(n)) (n=3..N)', oddOK, firstOddExc);
  // odd prime p_k -> G = k
  const spfIsPrime = (p) => { for (let q = 2; q * q <= p; q++) if (p % q === 0) return false; return p >= 2; };
  let rank = 0, primeOK = true;
  for (let p = 3; p <= N; p += 2) if (spfIsPrime(p)) { rank; }
  // count including 2: rank of odd prime = its prime index
  rank = 1; // 2 is p_1
  for (let p = 3; p <= N; p += 2) if (spfIsPrime(p)) { rank++; if (gCop[p] !== rank) primeOK = false; }
  ok('G(odd prime p_k) == k (k = its prime index)', primeOK);
}

// ---------------------------------------------------------------------------
console.log('\nCOMMON-FACTOR NIM — the proved core and the open frontier:');
{
  // PROVED: from any n>=2, d=n is legal (gcd(n,n)=n>1) -> reach 0. So P-positions = {0,1}.
  let onlyP01 = (gCom[0] === 0 && gCom[1] === 0);
  for (let n = 2; n <= N; n++) if (gCom[n] === 0) { onlyP01 = false; break; }
  ok('P-positions (G==0) are exactly {0,1}  (n=2..N all N-positions)', onlyP01);
  // the "d=n always legal for n>=2" fact underlying the proof
  let takeAll = true; for (let n = 2; n <= N; n++) if (gcd(n, n) <= 1) takeAll = false;
  ok('take-the-whole-pile is legal for every n>=2 (the {0,1} proof)', takeAll);
  // even law
  let evenLaw = true, firstEvenExc = null;
  for (let n = 2; n <= N; n += 2) if (gCom[n] !== n / 2) { evenLaw = false; if (!firstEvenExc) firstEvenExc = [n, gCom[n]]; }
  ok('G(even 2k) == k  (verified n=2..N)', evenLaw, firstEvenExc);
  // odd primes -> 1
  const isPrime = (p) => { for (let q = 2; q * q <= p; q++) if (p % q === 0) return false; return p >= 2; };
  let oddPrime1 = true; for (let p = 3; p <= N; p += 2) if (isPrime(p) && gCom[p] !== 1) oddPrime1 = false;
  ok('G(odd prime) == 1  (only move is take-all -> 0)', oddPrime1);
  // observed sub-law: odd prime SQUARES -> 2
  let sq2 = true, sq2seen = 0;
  for (let p = 3; p * p <= N; p += 2) if (isPrime(p)) { sq2seen++; if (gCom[p * p] !== 2) sq2 = false; }
  ok(`G(odd prime^2) == 2  (observed, ${sq2seen} cases to N)`, sq2);
}

// ---------------------------------------------------------------------------
console.log('\nOEIS ABSENCE (checked separately by curl on 2026-07-19; here we just print the data):');
const line = (label, a, lo, hi, step = 1) => {
  const t = []; for (let n = lo; n <= hi; n += step) t.push(a[n]);
  console.log(`  ${label}: ${t.join(',')}`);
};
line('Coprime Nim  G(n), n=0..30        ', gCop, 0, 30);
line('Common Nim   G(n), n=0..30  [NEW]  ', gCom, 0, 30);
line('Common Nim   odd G, n=1,3..59 [NEW]', gCom, 1, 59, 2);

console.log(`\n${fail === 0 ? 'ALL PASS' : 'FAILURES PRESENT'}  —  ${pass}/${pass + fail} checks`);
process.exit(fail === 0 ? 0 : 1);
