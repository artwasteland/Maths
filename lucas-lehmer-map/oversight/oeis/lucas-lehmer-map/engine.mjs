// engine.mjs — the functional graph of the Lucas–Lehmer map x ↦ x²−2 (mod n)
// over ALL of Z_n = {0,1,…,n−1}. Shared, dependency-free, exact (integer only).
//
// The map f(x) = x² − 2 mod n is the iteration at the heart of the Lucas–Lehmer
// Mersenne primality test (s₀ = 4, s_{k+1} = s_k² − 2 mod M_p). Iterating it on a
// fixed modulus n turns Z_n into a functional graph: every node has out-degree 1,
// so each weakly-connected component is a single directed cycle ("rho head") with
// trees ("tails") flowing into it. This file computes that graph's structure.
//
// Everything here is integer arithmetic; no floating point, no estimation.

/** The map itself, as a closure over the modulus. */
export function mapFn(n) {
  return (x) => (((x * x - 2) % n) + n) % n;
}

/**
 * Full structural analysis of the graph of x²−2 mod n.
 * Returns the four catalogued statistics plus the raw cycle-length spectrum.
 *
 *  cycles    — number of cycles  (= number of weakly-connected components,
 *              since every functional-graph component has exactly one cycle)
 *  periodic  — number of periodic (recurrent) points: x with fᵏ(x)=x for some k≥1
 *  fixed     — number of fixed points: x with f(x)=x  (= solutions of (x−2)(x+1)≡0)
 *  longest   — length of the longest cycle
 *  spectrum  — sorted multiset of cycle lengths (Σ spectrum = periodic)
 */
export function analyze(n) {
  const f = mapFn(n);
  const color = new Int8Array(n);          // 0 unseen, 1 on current walk, 2 done
  const onCycle = new Uint8Array(n);
  const spectrum = [];
  for (let s = 0; s < n; s++) {
    if (color[s]) continue;
    const path = [];
    let x = s;
    while (color[x] === 0) { color[x] = 1; path.push(x); x = f(x); }
    if (color[x] === 1) {                   // first time we close a brand-new cycle
      let y = x, L = 0;
      do { onCycle[y] = 1; y = f(y); L++; } while (y !== x);
      spectrum.push(L);
    }
    for (const p of path) color[p] = 2;
  }
  spectrum.sort((a, b) => a - b);
  let periodic = 0;
  for (let i = 0; i < n; i++) if (onCycle[i]) periodic++;
  let fixed = 0;
  for (let i = 0; i < n; i++) if (f(i) === i) fixed++;
  return {
    cycles: spectrum.length,
    periodic,
    fixed,
    longest: spectrum.length ? spectrum[spectrum.length - 1] : 0,
    spectrum,
  };
}

/** Convenience: the four staged statistics as arrays a(1..N). */
export function sequences(N) {
  const cycles = [], periodic = [], fixed = [], longest = [];
  for (let n = 1; n <= N; n++) {
    const g = analyze(n);
    cycles.push(g.cycles); periodic.push(g.periodic);
    fixed.push(g.fixed); longest.push(g.longest);
  }
  return { cycles, periodic, fixed, longest };
}

/** The orbit of a single seed under x²−2 mod n, with rho (tail length, cycle length). */
export function orbit(n, seed) {
  const f = mapFn(n);
  const seen = new Map();
  const seq = [];
  let x = ((seed % n) + n) % n, t = 0;
  while (!seen.has(x)) { seen.set(x, t); seq.push(x); x = f(x); t++; }
  const tail = seen.get(x);                 // first index where the cycle is entered
  return { seq, tail, cycleLen: t - tail, enters: x };
}

/**
 * The real Lucas–Lehmer test, in BigInt: M_p = 2^p − 1 is prime  ⇔  s_{p−2} ≡ 0,
 * where s₀ = 4, s_{k+1} = s_k² − 2 (mod M_p).  p must be an odd prime exponent.
 */
export function lucasLehmer(p) {
  const M = (1n << BigInt(p)) - 1n;
  let s = 4n % M;
  for (let k = 0; k < p - 2; k++) s = (((s * s - 2n) % M) + M) % M;
  return { Mp: M, passes: s === 0n };
}
