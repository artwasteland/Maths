// research/penney-mary — the Penney's-game DOMINANCE TOURNAMENT over an m-SYMBOL
// alphabet (an m-sided fair die), generalizing research/penney-tournament (m = 2).
//
// Background. In Penney's game two players each name a length-k word; a fair
// m-sided die is rolled until one word appears as a run; that player wins. For
// alphabet size m and length k there are n = m^k words, and "A appears before B"
// is a well-defined probability p(A,B) in [0,1] for every ordered pair A != B
// (i.i.d. uniform symbols, each probability 1/m). Draw an edge A -> B whenever
// p(A,B) > 1/2 ("A beats B"). That digraph is the Penney tournament T(m,k).
//
// The famous facts are the BINARY ones (m = 2): the tournament is non-transitive
// from k = 3 (a 4-cycle), yet contains no directed *triangle* until k = 4 — "the
// smallest cycle is a square" (research/penney-tournament). This file asks the
// natural open question: what happens with a 3-, 4-, 5-sided die?
//
// Two INDEPENDENT exact methods compute every win-probability as a BigInt
// rational. verify.mjs asserts they agree on every pair (the calibration
// discipline), cross-checks a third way (Monte-Carlo), and — the load-bearing
// honesty check — reproduces the published BINARY invariant sequences exactly
// before trusting any m > 2 number.

// ---------- exact rational arithmetic (BigInt) ----------
const g = (a, b) => (b ? g(b, a % b) : a < 0n ? -a : a);
export class Q {
  constructor(n, d = 1n) {
    if (d < 0n) { n = -n; d = -d; }
    const k = g(n < 0n ? -n : n, d) || 1n;
    this.n = n / k; this.d = d / k;
  }
  add(o) { return new Q(this.n * o.d + o.n * this.d, this.d * o.d); }
  sub(o) { return new Q(this.n * o.d - o.n * this.d, this.d * o.d); }
  mul(o) { return new Q(this.n * o.n, this.d * o.d); }
  div(o) { return new Q(this.n * o.d, this.d * o.n); }
  eq(o)  { return this.n === o.n && this.d === o.d; }
  cmp(o) { const x = this.n * o.d - o.n * this.d; return x > 0n ? 1 : x < 0n ? -1 : 0; }
  get s() { return `${this.n}/${this.d}`; }
}
export const Z = new Q(0n), HALF = new Q(1n, 2n), ONE = new Q(1n);

// digits 0..m-1 as the alphabet (kept as strings so slice/endsWith work on words)
export const words = (m, k) => {
  const out = [];
  const total = m ** k;
  for (let i = 0; i < total; i++) {
    let s = '', x = i;
    for (let p = 0; p < k; p++) { s = (x % m) + s; x = Math.floor(x / m); }
    out.push(s);
  }
  return out;
};

// ---------- ENGINE 1: Conway/Guibas–Odlyzko leading numbers (closed form) ----------
// corr_m(X,Y): sum over overlap lengths p where the last p chars of X equal the
// first p of Y, of m^(p-1). Odds (A first):(B first) = (BB-BA):(AA-AB).
// (Conway's binary rule is the m = 2 case; the alphabet size is the base.)
export function corr(m, X, Y) {
  const L = X.length; const M = BigInt(m); let t = 0n;
  for (let p = 1; p <= L; p++) if (X.slice(-p) === Y.slice(0, p)) t += M ** BigInt(p - 1);
  return t;
}
export function pAfirst_conway(m, A, B) {
  const AA = corr(m, A, A), AB = corr(m, A, B), BA = corr(m, B, A), BB = corr(m, B, B);
  const a = BB - BA, b = AA - AB;          // odds (A first):(B first)
  return new Q(a, a + b);
}

// ---------- ENGINE 2: exact absorbing-Markov linear solver (first principles) ----------
// State = the roll-history suffix (length 0..L-1) that could still grow into A or B.
// p[h] = P(A appears before B | history h). Each symbol arrives with prob 1/m.
// Solve the linear system over exact rationals by Gauss-Jordan; answer is p[''].
function histories(m, L) {
  const out = [];
  for (let k = 0; k < L; k++) {
    const total = m ** k;
    for (let i = 0; i < total; i++) {
      let s = '', x = i;
      for (let p = 0; p < k; p++) { s = (x % m) + s; x = Math.floor(x / m); }
      out.push(s);
    }
  }
  return out;
}
export function pAfirst_markov(m, A, B) {
  const L = A.length;
  const INV = new Q(1n, BigInt(m));               // 1/m per symbol
  const states = histories(m, L);
  const idx = new Map(states.map((s, i) => [s, i]));
  const n = states.length;
  const M = Array.from({ length: n }, () => Array.from({ length: n + 1 }, () => Z));
  for (const h of states) {
    const i = idx.get(h);
    M[i][i] = M[i][i].add(ONE);
    for (let c = 0; c < m; c++) {
      const s = h + c;
      if (s.endsWith(A)) M[i][n] = M[i][n].add(INV);          // A wins -> +1 with prob 1/m
      else if (s.endsWith(B)) { /* B wins -> +0 */ }
      else {
        const suff = L - 1 > 0 ? s.slice(-(L - 1)) : '';
        M[i][idx.get(suff)] = M[i][idx.get(suff)].sub(INV);
      }
    }
  }
  for (let col = 0; col < n; col++) {
    let piv = col; while (M[piv][col].eq(Z)) piv++;
    [M[col], M[piv]] = [M[piv], M[col]];
    const pv = M[col][col];
    M[col] = M[col].map((x) => x.div(pv));
    for (let r = 0; r < n; r++) if (r !== col && !M[r][col].eq(Z)) {
      const f = M[r][col];
      M[r] = M[r].map((x, j) => x.sub(f.mul(M[col][j])));
    }
  }
  return M[idx.get('')][n];
}

// ---------- ENGINE 3: Monte-Carlo (independent sanity, not exact) ----------
// Plays N races of A vs B with a seeded uniform m-ary stream; returns the
// empirical fraction of races A won (no ties: a race ends when one word appears).
export function pAfirst_mc(m, A, B, N, rng) {
  const L = A.length; let wins = 0;
  for (let t = 0; t < N; t++) {
    let suf = '';
    while (true) {
      suf = (suf + Math.floor(rng() * m)).slice(-L);
      if (suf.endsWith(A)) { wins++; break; }
      if (suf.endsWith(B)) break;
    }
  }
  return wins / N;
}

// ---------- the tournament and its invariants ----------
// rel[i][j] in {+1,-1,0}: i beats j / loses to j / ties j.
export function tournament(m, k, pfn = pAfirst_conway) {
  const S = words(m, k), n = S.length;
  const rel = Array.from({ length: n }, () => new Int8Array(n));
  const probs = new Set();
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const p = pfn(m, S[i], S[j]);
    probs.add(p.s); probs.add(ONE.sub(p).s);
    const c = p.cmp(HALF);
    rel[i][j] = c; rel[j][i] = -c;          // antisymmetric by construction
  }
  return { S, n, rel, probs };
}

export function invariants(t) {
  const { n, rel, probs } = t;
  let ties = 0;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (rel[i][j] === 0) ties++;
  const out = Array.from({ length: n }, (_, i) => {
    let d = 0; const r = rel[i]; for (let j = 0; j < n; j++) if (r[j] === 1) d++; return d;
  });
  const maxout = n > 1 ? Math.max(...out) : 0;
  const nMax = out.filter((x) => x === maxout).length;
  // directed triangles vs transitive triples (only triples with all 3 edges decided)
  let cyc3 = 0, transTri = 0;
  for (let a = 0; a < n; a++) {
    const ra = rel[a];
    for (let b = a + 1; b < n; b++) {
      const ab = ra[b]; const rb = rel[b];
      for (let c = b + 1; c < n; c++) {
        const bc = rb[c], ac = ra[c];
        if (ab === 0 || bc === 0 || ac === 0) continue;
        // out-degrees within the triple; (1,1,1) => directed 3-cycle
        const oa = (ab === 1 ? 1 : 0) + (ac === 1 ? 1 : 0);
        const ob = (ab === -1 ? 1 : 0) + (bc === 1 ? 1 : 0);
        const oc = (ac === -1 ? 1 : 0) + (bc === -1 ? 1 : 0);
        if (oa === 1 && ob === 1 && oc === 1) cyc3++; else transTri++;
      }
    }
  }
  return { ties, maxout, nMax, cyc3, transTri, distinctP: probs.size, out };
}

// girth helpers — smallest directed cycle length in the relation (ties = non-edges)
// returns Infinity if acyclic. Used to locate "nontransitivity onset" and the
// "first directed triangle" thresholds.
export function hasDirectedTriangle(t) { return invariants(t).cyc3 > 0; }

// shortest directed cycle through the win-edges (BFS from each node back to itself)
export function girth(t) {
  const { n, rel } = t;
  const adj = Array.from({ length: n }, (_, i) => {
    const r = rel[i], a = []; for (let j = 0; j < n; j++) if (r[j] === 1) a.push(j); return a;
  });
  let best = Infinity;
  for (let s = 0; s < n; s++) {
    // BFS for shortest cycle starting/ending at s
    const dist = new Int32Array(n).fill(-1); dist[s] = 0;
    const queue = [s];
    for (let qi = 0; qi < queue.length; qi++) {
      const u = queue[qi];
      if (dist[u] + 1 >= best) continue;
      for (const v of adj[u]) {
        if (v === s) { best = Math.min(best, dist[u] + 1); continue; }
        if (dist[v] === -1) { dist[v] = dist[u] + 1; queue.push(v); }
      }
    }
    if (best === 3) break; // can't do better than a triangle
  }
  return best;
}
