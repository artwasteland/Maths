// gcd-nim — the two engines, shared. See README.md.
//
// Two one-pile subtraction games, one word apart:
//   Coprime Nim        — remove d tokens, 1<=d<=n, with gcd(d,n) == 1
//   Common-factor Nim  — remove d tokens, 1<=d<=n, with gcd(d,n)  > 1
// Last player to move wins (normal play). The object of study is the
// Sprague-Grundy value of a single pile of n, which governs multi-pile play.
'use strict';

export function gcd(a, b) { while (b) { const t = a % b; a = b; b = t; } return a; }

// Grundy value of every pile 0..N for a game whose legal removals from a pile
// of size n are { d : 1<=d<=n and allow(d,n) }. allow is a pure predicate.
// This is the DIRECT definition: g(n) = mex { g(n-d) : d legal }.
export function grundy(N, allow) {
  const g = new Int32Array(N + 1);
  for (let n = 1; n <= N; n++) {
    const seen = new Set();
    for (let d = 1; d <= n; d++) if (allow(d, n)) seen.add(g[n - d]);
    let m = 0; while (seen.has(m)) m++;
    g[n] = m;
  }
  return g;
}

// --- the two move predicates ---
export const coprimeMove = (d, n) => gcd(d, n) === 1;
export const commonMove  = (d, n) => gcd(d, n) > 1;

// --- number theory, computed independently of the gcd loop (a second code path) ---

// smallest-prime-factor sieve; spf[1]=1
export function spfSieve(N) {
  const spf = new Int32Array(N + 1);
  for (let i = 2; i <= N; i++) if (!spf[i]) for (let j = i; j <= N; j += i) if (!spf[j]) spf[j] = i;
  spf[1] = 1;
  return spf;
}

// index of least prime factor: 2->1, 3->2, 5->3, 7->4, ... ; idx[1]=0 (A055396 convention)
export function lpfIndex(N) {
  const spf = spfSieve(N);
  const primeRank = new Map();
  let k = 0;
  for (let i = 2; i <= N; i++) if (spf[i] === i) primeRank.set(i, ++k);
  const idx = new Int32Array(N + 1);
  for (let n = 2; n <= N; n++) idx[n] = primeRank.get(spf[n]);
  return idx;
}

// set of distinct prime factors of every n<=N (as a Uint32 bit-free array of arrays)
export function primeFactorSets(N) {
  const spf = spfSieve(N);
  const sets = new Array(N + 1);
  sets[0] = []; sets[1] = [];
  for (let n = 2; n <= N; n++) {
    let m = n; const s = [];
    while (m > 1) { const p = spf[m]; s.push(p); while (m % p === 0) m = (m / p) | 0; }
    sets[n] = s;
  }
  return sets;
}

// SECOND, structurally-different Grundy path: legality decided by whether the
// distinct-prime-factor sets of d and n intersect (share => common; disjoint => coprime),
// never calling gcd(). Used only to cross-check `grundy(...,commonMove/coprimeMove)`.
export function grundyByFactorSets(N, wantShared /* true=common, false=coprime */) {
  const sets = primeFactorSets(N);
  const g = new Int32Array(N + 1);
  for (let n = 1; n <= N; n++) {
    const S = new Set(sets[n]);
    const seen = new Set();
    for (let d = 1; d <= n; d++) {
      const shares = sets[d].some(p => S.has(p));
      if (shares === wantShared) seen.add(g[n - d]);
    }
    let m = 0; while (seen.has(m)) m++;
    g[n] = m;
  }
  return g;
}
