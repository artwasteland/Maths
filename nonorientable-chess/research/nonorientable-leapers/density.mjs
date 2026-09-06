// density.mjs — how many forbidden pairs does each surface impose, and does the
// count follow from that number alone?
//
// The question this answers is the one the extended table makes askable. Under the
// permutation convention only one kind of pair can ever both be occupied: two cells
// in different rows AND different columns. Call the number of attacking such pairs
// P. A uniform random permutation seats both cells of a given pair with probability
// 1/(n(n-1)), so the expected number of attacking pairs is
//
//     E = P / (n(n-1))
//
// and if the pairs behaved independently the count would be about n! * exp(-E).
// That is the null this file computes. It is a heuristic, not a theorem, and it is
// printed as a ratio so the reader can see exactly how far off it is.
//
// NOT NEW, and the catalogue says so first: OEIS A137774 already carries the
// asymptotic a(n)/n! -> 1/e^4 for a leaper (r,s) with 0 < r < s, which is exactly
// the limit of exp(-E) here, since a closed board gives P = 4n^2 and hence
// E = 4n/(n-1) -> 4. This file computes the finite-n version of a published limit;
// its only job is to make the per-surface differences in P visible.
//
// The reason to compute it here: the torus and the Klein bottle are BOTH closed,
// so on both of them every cell has the same eight targets and P is the same
// number. The heuristic therefore predicts the same count for both. The table says
// otherwise. What the twist changes is not how many constraints there are but how
// they are arranged -- which is the sharper form of the symmetry-breaking this
// stratum already noticed at n=7.
//
// SUPERSEDED IN PART, 2026-08-20. The yes/no question this file asks ("is P the
// same on the torus and the Klein bottle?") gets the true answer NO, and NO is the
// least informative true thing available here: the two differ by a CONSTANT (6 to
// 16, by leaper and by the parity of n) against a quantity of size 4n^2. See
// `pairs-model.mjs`, which replaces the yes/no with exact closed forms on all four
// surfaces, shows the leading terms are a two-line count rather than a fit, and
// turns the residual this file prints into a one-step predictor with a negative
// control. This file stays because it is the independent second reading of P, and
// because the guess it killed is worth keeping killed.
//
//   node density.mjs [maxN]        default 14

import { attackGraph, leaperVectors, LEAPERS } from './engine.mjs';

const TOPOS = ['flat', 'torus', 'mobius', 'klein'];
const maxN = Number(process.argv[2] || 14);

// P = number of unordered attacking pairs whose two cells differ in BOTH
// coordinates. Pairs sharing a row or a column are dropped: the permutation
// convention already forbids two pieces there, so they constrain nothing.
function forbiddenPairs(topo, n, V) {
  const adj = attackGraph(topo, n, V);
  let p = 0;
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
}

function factorial(n) { let f = 1; for (let i = 2; i <= n; i++) f *= i; return f; }

console.log('P = attacking pairs in distinct rows AND distinct columns');
console.log('E = P/(n(n-1)) = expected attacking pairs in a uniform random permutation');
console.log('predicted = n! * exp(-E)   (independence heuristic, not a theorem)\n');

for (const name of Object.keys(LEAPERS)) {
  const [a, b] = LEAPERS[name];
  const V = leaperVectors(a, b);
  console.log(`--- ${name} (${a},${b}) ---`);
  console.log('  n   ' + TOPOS.map(t => t.padStart(9)).join('  ') + '     (P per surface)');
  for (let n = 5; n <= maxN; n++) {
    const row = TOPOS.map(t => String(forbiddenPairs(t, n, V)).padStart(9));
    console.log(`  ${String(n).padStart(2)}  ${row.join('  ')}`);
  }
  // The claim to test, stated so it can fail: on a closed surface every cell has
  // the same eight targets, so torus and klein should carry identical P.
  let same = true;
  for (let n = 5; n <= maxN; n++)
    if (forbiddenPairs('torus', n, V) !== forbiddenPairs('klein', n, V)) { same = false; break; }
  console.log(`  torus P == klein P for all n=5..${maxN}? ${same ? 'YES' : 'NO'}`);
  console.log('');
}

// Print E and the heuristic prediction next to a term, for whatever terms the
// caller pipes in via TERMS (topo,leaper,n,count per line). Kept separate so this
// file never hard-codes a count it did not compute.
if (process.env.TERMS) {
  console.log('surface  leaper    n           actual        predicted   actual/predicted');
  for (const line of process.env.TERMS.trim().split('\n')) {
    const [topo, leaper, n_, count_] = line.trim().split(/\s+/);
    const n = Number(n_), count = Number(count_);
    const [a, b] = LEAPERS[leaper];
    const P = forbiddenPairs(topo, n, leaperVectors(a, b));
    const E = P / (n * (n - 1));
    const pred = factorial(n) * Math.exp(-E);
    console.log(`${topo.padEnd(8)} ${leaper.padEnd(8)} ${String(n).padStart(2)}  ${String(count).padStart(15)}  ${pred.toExponential(4).padStart(14)}   ${(count / pred).toFixed(4)}`);
  }
}
