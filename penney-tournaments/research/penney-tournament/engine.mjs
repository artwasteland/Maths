// research/penney-tournament — the Penney's-game DOMINANCE TOURNAMENT at length k.
//
// Background. In Penney's game two players each name a length-k pattern of coin
// flips; a fair coin is tossed until one pattern appears as a run; that player
// wins. For length k there are n = 2^k patterns, and "A appears before B" is a
// well-defined probability p(A,B) in [0,1] for every ordered pair (A != B).
// Draw an edge A -> B whenever p(A,B) > 1/2 ("A beats B"). That digraph is the
// Penney tournament at length k. It is famously NON-transitive: from k=3 on it
// contains directed 3-cycles (rock-paper-scissors hidden in a fair coin).
//
// This file is the shared, reusable engine. Two INDEPENDENT exact methods compute
// every win-probability as a BigInt rational; verify.mjs asserts they agree on
// every pair (the calibration discipline), then derives the tournament invariants
// staged for OEIS. Win-probabilities themselves were already validated three ways
// (Conway / Markov / brute force, 152 checks) in research/penneys-game.

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

export const patterns = (k) =>
  Array.from({ length: 1 << k }, (_, i) =>
    i.toString(2).padStart(k, '0').replace(/0/g, 'H').replace(/1/g, 'T'));

// ---------- ENGINE 1: Conway's leading numbers (closed form, O(k)) ----------
// corr(X,Y): sum over overlaps k where the last k chars of X equal the first k of Y,
// of 2^(k-1). Odds (A first):(B first) = (BB-BA):(AA-AB).  (Conway; Li 1980.)
export function corr(X, Y) {
  const L = X.length; let t = 0n;
  for (let k = 1; k <= L; k++) if (X.slice(-k) === Y.slice(0, k)) t += 2n ** BigInt(k - 1);
  return t;
}
export function pAfirst_conway(A, B) {
  const AA = corr(A, A), AB = corr(A, B), BA = corr(B, A), BB = corr(B, B);
  const a = BB - BA, b = AA - AB;          // odds (A first):(B first)
  return new Q(a, a + b);
}

// ---------- ENGINE 2: exact absorbing-Markov linear solver (first principles) ----------
// State = the flip-history suffix (length 0..L-1) that could still grow into A or B.
// p[h] = P(A appears before B | history h). Solve the linear system over exact
// rationals by Gauss-Jordan; the answer is p[''] (empty start).
function* histories(L) {
  for (let k = 0; k < L; k++)
    for (let m = 0; m < (1 << k); m++)
      yield Array.from({ length: k }, (_, i) => (m >> (k - 1 - i)) & 1 ? 'T' : 'H').join('');
}
export function pAfirst_markov(A, B) {
  const L = A.length;
  const states = [...histories(L)];
  const idx = new Map(states.map((s, i) => [s, i]));
  const n = states.length;
  const M = Array.from({ length: n }, () => Array.from({ length: n + 1 }, () => Z));
  for (const h of states) {
    const i = idx.get(h);
    M[i][i] = M[i][i].add(ONE);
    for (const c of 'HT') {
      const s = h + c;
      if (s.endsWith(A)) M[i][n] = M[i][n].add(HALF);   // A wins -> +1 with prob 1/2
      else if (s.endsWith(B)) { /* B wins -> +0 */ }
      else {
        const suff = L - 1 > 0 ? s.slice(-(L - 1)) : '';
        M[i][idx.get(suff)] = M[i][idx.get(suff)].sub(HALF);
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

// ---------- the tournament and its invariants ----------
// rel[i][j] in {+1,-1,0}: i beats j / loses to j / ties j.  Built with `pfn`.
export function tournament(k, pfn = pAfirst_conway) {
  const S = patterns(k), n = S.length;
  const rel = Array.from({ length: n }, () => new Array(n).fill(0));
  const probs = new Set();
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const p = pfn(S[i], S[j]);
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
  const out = rel.map((r) => r.filter((x) => x === 1).length);
  const maxout = n > 1 ? Math.max(...out) : 0;
  const nMax = out.filter((x) => x === maxout).length;
  // 3-cycles: triples whose three edges are all decided and form a directed cycle.
  let cyc3 = 0, transTri = 0;
  for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) for (let c = b + 1; c < n; c++) {
    const ab = rel[a][b], bc = rel[b][c], ac = rel[a][c];
    if (ab === 0 || bc === 0 || ac === 0) continue;
    const od = [(ab === 1 ? 1 : 0) + (ac === 1 ? 1 : 0),
                (ab === -1 ? 1 : 0) + (bc === 1 ? 1 : 0),
                (ac === -1 ? 1 : 0) + (bc === -1 ? 1 : 0)];
    if (od[0] === 1 && od[1] === 1 && od[2] === 1) cyc3++; else transTri++;
  }
  return { ties, maxout, nMax, cyc3, transTri, distinctP: probs.size, out };
}
