// engine.mjs — the functional graph of the quadratic map x ↦ x² + c (mod n),
// and Pollard's rho factoring built on top of it. Shared, dependency-free, exact.
//
// Iterating f(x) = x² + c (mod n) turns Z_n into a FUNCTIONAL GRAPH: every node
// has out-degree exactly 1, so each weakly-connected component is a single
// directed cycle with trees ("tails") draining into it. Any orbit therefore looks
// like the Greek letter ρ — a tail running into a loop. That picture is the whole
// reason Pollard's 1975 factoring method is called "rho."
//
// The arithmetic here is integer-only (BigInt where a modulus can exceed 2^53);
// no floating point, no estimation. Floats appear only in `randomMapSpectrum`,
// which is an explicitly-labelled statistical comparison, not a claim of fact.

/** The map f(x) = x² + c mod n, as a closure. Small-modulus (Number) version. */
export function mapFn(n, c) {
  const cc = ((c % n) + n) % n;
  return (x) => (x * x + cc) % n;
}

/**
 * The rho of a single seed under x²+c mod n: its tail length and cycle length.
 * Returns { seq, tail, cycleLen, enters }. tail+cycleLen is the "rho length" —
 * how many distinct points the orbit visits before it closes.
 */
export function orbit(n, c, seed) {
  const f = mapFn(n, c);
  const seen = new Map();
  const seq = [];
  let x = ((seed % n) + n) % n, t = 0;
  while (!seen.has(x)) { seen.set(x, t); seq.push(x); x = f(x); t++; }
  const tail = seen.get(x);              // first index where the cycle is re-entered
  return { seq, tail, cycleLen: t - tail, enters: x };
}

/**
 * Full structural analysis of the graph of x²+c mod n.
 *  cycles    — number of cycles  (= number of weakly-connected components)
 *  periodic  — number of periodic points: x with fᵏ(x)=x for some k≥1
 *  fixed     — number of fixed points: x with f(x)=x  (solutions of x²−x+c≡0)
 *  longest   — length of the longest cycle
 *  spectrum  — sorted multiset of cycle lengths (Σ spectrum = periodic)
 *  tailSum   — Σ over all x of the tail length of x (used for mean-rho stats)
 */
export function analyze(n, c) {
  const f = mapFn(n, c);
  const color = new Int8Array(n);        // 0 unseen, 1 on current walk, 2 done
  const onCycle = new Uint8Array(n);
  const depth = new Int32Array(n).fill(-1); // distance from x to the cycle it feeds
  const spectrum = [];
  for (let s = 0; s < n; s++) {
    if (color[s]) continue;
    const path = [];
    let x = s;
    while (color[x] === 0) { color[x] = 1; path.push(x); x = f(x); }
    if (color[x] === 1) {                 // closed a brand-new cycle
      let y = x, L = 0;
      do { onCycle[y] = 1; depth[y] = 0; y = f(y); L++; } while (y !== x);
      spectrum.push(L);
    }
    // walk the path backwards from where it joined known territory, assigning depth
    // (the joining node x already has a depth if it's cyclic or previously done)
    for (let i = path.length - 1; i >= 0; i--) {
      const p = path[i];
      if (depth[p] === -1) depth[p] = depth[f(p)] + 1;
      color[p] = 2;
    }
  }
  spectrum.sort((a, b) => a - b);
  let periodic = 0, tailSum = 0;
  for (let i = 0; i < n; i++) { if (onCycle[i]) periodic++; tailSum += depth[i]; }
  let fixed = 0;
  for (let i = 0; i < n; i++) if (f(i) === i) fixed++;
  return {
    cycles: spectrum.length,
    periodic,
    fixed,
    longest: spectrum.length ? spectrum[spectrum.length - 1] : 0,
    spectrum,
    tailSum,
  };
}

// ---------------------------------------------------------------------------
// Pollard's rho factoring (BigInt — moduli here can be far past 2^53).
// ---------------------------------------------------------------------------

export function gcd(a, b) { while (b) { [a, b] = [b, a % b]; } return a < 0n ? -a : a; }

/** f(x) = x² + c mod N, BigInt. */
function fBig(x, c, N) { return (x * x + c) % N; }

/**
 * Pollard's rho with Floyd (tortoise & hare) cycle detection.
 * Returns { factor, iters, trace } where factor is a nontrivial divisor of N
 * (or null on failure — caller should retry with a different c/seed).
 * `traceLimit` caps how many (tortoise,hare) steps are recorded for display.
 */
export function pollardRho(N, { c = 1n, x0 = 2n, traceLimit = 0 } = {}) {
  N = BigInt(N); c = BigInt(c); x0 = BigInt(x0);
  if (N % 2n === 0n) return { factor: 2n, iters: 0, trace: [] };
  let tortoise = x0, hare = x0, d = 1n, iters = 0;
  const trace = [];
  do {
    tortoise = fBig(tortoise, c, N);
    hare = fBig(fBig(hare, c, N), c, N);
    const diff = tortoise > hare ? tortoise - hare : hare - tortoise;
    d = gcd(diff, N);
    iters++;
    if (trace.length < traceLimit) trace.push({ tortoise, hare, d });
  } while (d === 1n && iters < 50_000_000);
  if (d === N) return { factor: null, iters, trace };          // collision wrapped mod N — retry
  return { factor: d, iters, trace };
}

/**
 * The rho's behaviour MOD a prime factor p of N — the thing Pollard's method
 * secretly rides. Returns when the sequence (reduced mod p) first collides, and
 * how many steps that took. This is the "hidden small rho" the gcd detects.
 */
export function rhoModP(p, c, x0) {
  p = BigInt(p); c = BigInt(c); x0 = BigInt(x0);
  const seen = new Map();
  let x = ((x0 % p) + p) % p, t = 0;
  while (!seen.has(x)) { seen.set(x, t); x = (x * x + c) % p; t++; }
  return { tail: seen.get(x), cycleLen: t - seen.get(x), rhoLen: t };
}

// ---------------------------------------------------------------------------
// Statistical reference: the Flajolet–Odlyzko (1990) random-mapping constants.
// These are the *predictions* a truly random map would obey; we MEASURE how
// close x²+c comes. Floating point lives only here, by design.
// ---------------------------------------------------------------------------

/** √(πn/2) — expected rho length of a random starting point in a random n-map. */
export const expectedRhoLen = (n) => Math.sqrt(Math.PI * n / 2);
/** √(πn/8) — expected tail length, and (separately) expected cycle length. */
export const expectedTail = (n) => Math.sqrt(Math.PI * n / 8);
/** ~½·ln(n) — expected number of components (cycles). */
export const expectedComponents = (n) => 0.5 * Math.log(n);

/**
 * Mean rho length measured over ALL n starting points of x²+c mod n, averaged
 * over a given set of c values. Returns the empirical mean (a float) — used to
 * compare a quadratic map against the random-map prediction.
 */
export function meanRhoLen(n, cs) {
  let total = 0, count = 0;
  for (const c of cs) {
    // depth[x] = tail length of x; cycleLen of x = the cycle its component owns.
    const f = mapFn(n, c);
    const color = new Int8Array(n);
    const cycleOf = new Int32Array(n).fill(-1);   // cycle length of x's component
    const depth = new Int32Array(n).fill(-1);
    const compCycleLen = [];
    const comp = new Int32Array(n).fill(-1);
    for (let s = 0; s < n; s++) {
      if (color[s]) continue;
      const path = [];
      let x = s;
      while (color[x] === 0) { color[x] = 1; path.push(x); x = f(x); }
      let cid;
      if (color[x] === 1) {
        let y = x, L = 0; do { y = f(y); L++; } while (y !== x);
        cid = compCycleLen.push(L) - 1;
        let z = x; do { depth[z] = 0; comp[z] = cid; z = f(z); } while (z !== x);
      } else { cid = comp[x]; }
      for (let i = path.length - 1; i >= 0; i--) {
        const p = path[i];
        if (depth[p] === -1) { depth[p] = depth[f(p)] + 1; comp[p] = cid; }
        color[p] = 2;
      }
    }
    for (let x = 0; x < n; x++) { total += depth[x] + compCycleLen[comp[x]]; count++; }
  }
  return total / count;
}

/** The four catalogued statistics of x²+c mod n as arrays a(1..N), for a fixed c. */
export function sequences(N, c) {
  const cycles = [], periodic = [], fixed = [], longest = [];
  for (let n = 1; n <= N; n++) {
    const g = analyze(n, c);
    cycles.push(g.cycles); periodic.push(g.periodic);
    fixed.push(g.fixed); longest.push(g.longest);
  }
  return { cycles, periodic, fixed, longest };
}
