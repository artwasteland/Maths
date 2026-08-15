// Topswops — the engine.  Conway's flip process, computed exactly.
//
// A deck is a permutation a[0..n-1] of 1..n.  One STEP: read the top card k = a[0];
// if k = 1 the deck is DONE; otherwise reverse the first k cards.  Repeat.  Conway
// proved the process always terminates (the number of steps is bounded), so every
// statistic below is exact and finite.
//
// This file is pure computation, no I/O.  research/topswops/verify.mjs asserts the
// results; oversight/oeis/topswops-total-flips/derive.mjs rewrites the b-file from it.

export function factorials(n) {
  const f = [1];
  for (let i = 1; i <= n; i++) f[i] = f[i - 1] * i;
  return f;
}

// Number of flips a single deck takes to reach a top card of 1.  Mutates a copy.
export function flips(deck) {
  const a = deck.slice();
  let c = 0;
  while (a[0] !== 1) {
    const k = a[0];
    let i = 0, j = k - 1;
    while (i < j) { const t = a[i]; a[i] = a[j]; a[j] = t; i++; j--; }
    c++;
  }
  return c;
}

// Rank a permutation of {1..n} to its index 0..n!-1 (factorial number system).
export function rank(a, n, fact) {
  let r = 0;
  const seen = new Uint8Array(n + 1);
  for (let i = 0; i < n; i++) {
    let less = 0;
    for (let v = 1; v < a[i]; v++) if (!seen[v]) less++;
    seen[a[i]] = 1;
    r += less * fact[n - 1 - i];
  }
  return r;
}

// Iterate every permutation of `arr` (Heap's algorithm).  Yields the SAME array each
// time (mutated in place) — copy it if you need to keep it.
export function* perms(arr) {
  const a = arr.slice();
  const n = a.length;
  const c = new Array(n).fill(0);
  yield a;
  let i = 0;
  while (i < n) {
    if (c[i] < i) {
      if (i % 2 === 0) { const t = a[0]; a[0] = a[i]; a[i] = t; }
      else { const t = a[c[i]]; a[c[i]] = a[i]; a[i] = t; }
      yield a;
      c[i]++; i = 0;
    } else { c[i] = 0; i++; }
  }
}

// One step of the flip MAP on a non-terminal deck: reverse the first a[0] cards.
// Returns a new array.  (Defined only when a[0] !== 1.)
export function flipOnce(a) {
  const k = a[0];
  const q = a.slice();
  let i = 0, j = k - 1;
  while (i < j) { const t = q[i]; q[i] = q[j]; q[j] = t; i++; j--; }
  return q;
}

// All four statistics over the full n! decks, computed exactly.
//   M       = max flips over all decks                     (calibration: OEIS A000375)
//   champ   = # decks achieving M                          (calibration: OEIS A123398)
//   sum     = total flips summed over all decks  [the NEW sequence; absent from OEIS]
//   sources = # decks that are NOT the image of any flip   (the Garden of Eden; = A000255(n-1))
//   distinct= # distinct flip-counts achieved (observed to be M+1 for all n tested)
// `sources` uses an n!-byte preimage bitmap, so keep n small enough (n<=11 is fine).
export function statsFull(n) {
  const fact = factorials(n);
  const Nf = fact[n];
  const base = [];
  for (let i = 1; i <= n; i++) base.push(i);

  const stepArr = new Int32Array(Nf);
  const hasPre = new Uint8Array(Nf);
  let M = 0;
  let sum = 0n;
  let acc = 0;
  const seen = new Set();

  for (const p of perms(base)) {
    const r = rank(p, n, fact);
    const c = flips(p);
    stepArr[r] = c;
    if (c > M) M = c;
    acc += c; if (acc > 2e15) { sum += BigInt(acc); acc = 0; }
    seen.add(c);
    if (p[0] !== 1) {
      const q = flipOnce(p);
      hasPre[rank(q, n, fact)] = 1;
    }
  }
  sum += BigInt(acc);

  let champ = 0, sources = 0;
  for (let r = 0; r < Nf; r++) {
    if (stepArr[r] === M) champ++;
    if (!hasPre[r]) sources++;
  }
  return { n, M, champ, sum, sources, distinct: seen.size };
}

// Fast path for M and sum only (no n!-byte arrays) — reaches larger n.
export function maxAndSum(n) {
  const base = [];
  for (let i = 1; i <= n; i++) base.push(i);
  const work = new Int32Array(n);
  let M = 0, sum = 0n, acc = 0;
  for (const p of perms(base)) {
    for (let i = 0; i < n; i++) work[i] = p[i];
    let c = 0;
    while (work[0] !== 1) {
      const k = work[0];
      let i = 0, j = k - 1;
      while (i < j) { const t = work[i]; work[i] = work[j]; work[j] = t; i++; j--; }
      c++;
    }
    if (c > M) M = c;
    acc += c; if (acc > 2e15) { sum += BigInt(acc); acc = 0; }
  }
  sum += BigInt(acc);
  return { n, M, sum };
}

// --- The Garden of Eden, three independent ways (all must agree) ---

// (1) Direct: a deck of size n is unreachable iff it has NO fixed point in positions
// 2..n (1-indexed).  [Proof: q is the image of some flip iff there is a k in 2..n with
// q at position k equal to k — invert by reversing the first k cards.  So q is
// unreachable iff no such k exists, i.e. q has no fixed point away from the top.]
export function gardenDirect(n) {
  const base = [];
  for (let i = 1; i <= n; i++) base.push(i);
  let cnt = 0;
  for (const p of perms(base)) {
    let ok = true;
    for (let j = 1; j < n; j++) if (p[j] === j + 1) { ok = false; break; }
    if (ok) cnt++;
  }
  return cnt;
}

// (2) Inclusion-exclusion: permutations of [n] with no fixed point among the n-1
// positions 2..n  =  Sum_{j} (-1)^j C(n-1, j) (n-j)!.
export function gardenIE(n) {
  const f = factorials(n);
  const C = (a, b) => { if (b < 0 || b > a) return 0; let r = 1; for (let i = 0; i < b; i++) r = r * (a - i) / (i + 1); return Math.round(r); };
  let s = 0;
  const m = n - 1;
  for (let j = 0; j <= m; j++) s += (j % 2 ? -1 : 1) * C(m, j) * f[n - j];
  return s;
}

// (3) The catalogued sequence A000255: a(k) = k*a(k-1) + (k-1)*a(k-2), a0=a1=1.
// The claim is gardenDirect(n) = gardenIE(n) = A000255(n-1).
export function A000255(upto) {
  const a = [1, 1];
  for (let i = 2; i <= upto; i++) a[i] = i * a[i - 1] + (i - 1) * a[i - 2];
  return a;
}
