// research/many-symbol-penney — Penney's-game DOMINANCE TOURNAMENT over a q-letter
// alphabet ("the coin grows a third face"). Generalizes research/penney-tournament
// (q = 2) to any alphabet size q >= 2, and to a biased letter distribution.
//
// Penney's game: two players each name a length-k word over a q-letter alphabet;
// a fair q-sided die is rolled until one word appears as a run of consecutive
// rolls; that player wins. For length k there are q^k words, and "A appears
// before B" is a well-defined probability p(A,B) in [0,1] for every ordered pair
// A != B. Draw A -> B whenever p(A,B) > 1/2 ("A beats B"). That digraph is the
// q-ary Penney tournament at length k.
//
// TWO INDEPENDENT EXACT METHODS compute every win-probability as a BigInt
// rational; verify.mjs asserts they agree, then reads the tournament invariants
// off the validated relation. This is the same calibration discipline the binary
// notebook used (Conway == Markov on every pair), lifted to general q.

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
export const Z = new Q(0n), ONE = new Q(1n), HALF = new Q(1n, 2n);

// alphabet: letters 'A','B','C',... up to q. Words are strings over these.
export const LETTERS = 'ABCDEFGHIJ';
export const alphabet = (q) => LETTERS.slice(0, q).split('');

// all q^k words, in a stable order (lexicographic by letter index)
export function words(k, q) {
  const A = alphabet(q), out = [];
  const rec = (pre) => {
    if (pre.length === k) { out.push(pre); return; }
    for (const c of A) rec(pre + c);
  };
  rec('');
  return out;
}

// ---------- ENGINE 1: Conway's leading numbers (closed form, O(k)) ----------
// corr(X,Y,q): sum over overlap lengths j (1..L) where the last j chars of X equal
// the first j chars of Y, of q^(j-1). Odds (A first):(B first) = (BB-BA):(AA-AB).
// (Conway; generalized to alphabet size q via the base-q leading number. The q^(j-1)
// convention matches the binary notebook exactly at q=2; any constant factor in the
// per-length weight cancels in the odds ratio.)
export function corr(X, Y, q) {
  const L = X.length; let t = 0n; const Q_ = BigInt(q);
  for (let j = 1; j <= L; j++) if (X.slice(-j) === Y.slice(0, j)) t += Q_ ** BigInt(j - 1);
  return t;
}
export function pAfirst_conway(A, B, q) {
  const AA = corr(A, A, q), AB = corr(A, B, q), BA = corr(B, A, q), BB = corr(B, B, q);
  const a = BB - BA, b = AA - AB;          // odds (A first):(B first)
  return new Q(a, a + b);
}

// ---------- ENGINE 2: exact absorbing-Markov linear solver (first principles) ----------
// State = the roll-history suffix (length 0..L-1) that could still grow into A or B.
// p[h] = P(A appears before B | history h). Fair die: each of q next letters prob 1/q.
// Solve the linear system over exact rationals by Gauss-Jordan; answer is p[''] (empty).
function histories(L, q) {
  const out = [];
  for (let len = 0; len < L; len++) for (const w of words(len, q)) out.push(w);
  return out;
}
export function pAfirst_markov(A, B, q) {
  const L = A.length, A_ = alphabet(q);
  const w = new Q(1n, BigInt(q));              // fair: 1/q per letter
  const states = histories(L, q);
  const idx = new Map(states.map((s, i) => [s, i]));
  const n = states.length;
  const M = Array.from({ length: n }, () => Array.from({ length: n + 1 }, () => Z));
  for (const h of states) {
    const i = idx.get(h);
    M[i][i] = M[i][i].add(ONE);
    for (const c of A_) {
      const s = h + c;
      if (s.endsWith(A)) M[i][n] = M[i][n].add(w);        // A wins -> +w toward 1
      else if (s.endsWith(B)) { /* B wins -> +0 */ }
      else {
        const suff = L - 1 > 0 ? s.slice(-(L - 1)) : '';
        M[i][idx.get(suff)] = M[i][idx.get(suff)].sub(w);
      }
    }
  }
  gaussJordan(M, n);
  return M[idx.get('')][n];
}

// biased variant: prob[c] is a Q for each letter c (must sum to 1). Markov only
// (the trivially-correct method for arbitrary bias).
export function pAfirst_markov_biased(A, B, q, prob) {
  const L = A.length, A_ = alphabet(q);
  const states = histories(L, q);
  const idx = new Map(states.map((s, i) => [s, i]));
  const n = states.length;
  const M = Array.from({ length: n }, () => Array.from({ length: n + 1 }, () => Z));
  for (const h of states) {
    const i = idx.get(h);
    M[i][i] = M[i][i].add(ONE);
    for (const c of A_) {
      const wc = prob[c];
      const s = h + c;
      if (s.endsWith(A)) M[i][n] = M[i][n].add(wc);
      else if (s.endsWith(B)) { /* +0 */ }
      else {
        const suff = L - 1 > 0 ? s.slice(-(L - 1)) : '';
        M[i][idx.get(suff)] = M[i][idx.get(suff)].sub(wc);
      }
    }
  }
  gaussJordan(M, n);
  return M[idx.get('')][n];
}

function gaussJordan(M, n) {
  for (let col = 0; col < n; col++) {
    let piv = col; while (piv < n && M[piv][col].eq(Z)) piv++;
    [M[col], M[piv]] = [M[piv], M[col]];
    const pv = M[col][col];
    M[col] = M[col].map((x) => x.div(pv));
    for (let r = 0; r < n; r++) if (r !== col && !M[r][col].eq(Z)) {
      const f = M[r][col];
      M[r] = M[r].map((x, j) => x.sub(f.mul(M[col][j])));
    }
  }
}

// ---------- the tournament and its invariants ----------
// rel[i][j] in {+1,-1,0}: i beats j / loses to j / ties j.
export function tournament(k, q, pfn = pAfirst_conway) {
  const S = words(k, q), n = S.length;
  const rel = Array.from({ length: n }, () => new Array(n).fill(0));
  const probs = new Set();
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const p = pfn(S[i], S[j], q);
    probs.add(p.s); probs.add(ONE.sub(p).s);
    const c = p.cmp(HALF);
    rel[i][j] = c; rel[j][i] = -c;
  }
  return { S, n, rel, probs, q, k };
}

export function invariants(t) {
  const { n, rel, probs } = t;
  let ties = 0;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (rel[i][j] === 0) ties++;
  const out = rel.map((r) => r.filter((x) => x === 1).length);
  const maxout = n > 1 ? Math.max(...out) : 0;
  const nMax = out.filter((x) => x === maxout).length;
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

// ---------- structure: Tarjan SCC, sources/sinks ----------
export function sccDecompose(t) {
  const { n, rel } = t;
  const adj = Array.from({ length: n }, (_, i) =>
    rel[i].map((x, j) => (x === 1 ? j : -1)).filter((j) => j >= 0));
  let idxc = 0; const stack = []; const onstk = new Array(n).fill(false);
  const low = new Array(n).fill(-1), num = new Array(n).fill(-1), comp = new Array(n).fill(-1);
  let nc = 0;
  // iterative Tarjan (n can be ~700+)
  for (let s = 0; s < n; s++) {
    if (num[s] !== -1) continue;
    const callStack = [[s, 0]];
    while (callStack.length) {
      const frame = callStack[callStack.length - 1];
      const [v, pi] = frame;
      if (pi === 0) { num[v] = low[v] = idxc++; stack.push(v); onstk[v] = true; }
      if (pi < adj[v].length) {
        frame[1]++;
        const w = adj[v][pi];
        if (num[w] === -1) callStack.push([w, 0]);
        else if (onstk[w]) low[v] = Math.min(low[v], num[w]);
      } else {
        if (low[v] === num[v]) {
          while (true) { const w = stack.pop(); onstk[w] = false; comp[w] = nc; if (w === v) break; }
          nc++;
        }
        callStack.pop();
        if (callStack.length) { const p = callStack[callStack.length - 1][0]; low[p] = Math.min(low[p], low[v]); }
      }
    }
  }
  // component sizes and condensation edges to find sources/sinks
  const sizes = new Array(nc).fill(0); for (let i = 0; i < n; i++) sizes[comp[i]]++;
  const cin = new Array(nc).fill(0), cout = new Array(nc).fill(0);
  const seen = new Set();
  for (let i = 0; i < n; i++) for (const j of adj[i]) {
    if (comp[i] !== comp[j]) { const key = comp[i] * nc + comp[j]; if (!seen.has(key)) { seen.add(key); cout[comp[i]]++; cin[comp[j]]++; } }
  }
  return { nc, comp, sizes, cin, cout, adj };
}
