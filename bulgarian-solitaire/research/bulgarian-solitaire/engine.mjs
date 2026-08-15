// Bulgarian solitaire on the partitions of n.
// Move B: remove one card from every pile (empty piles vanish), then add one new
// pile whose size equals the number of piles present BEFORE removal. Deterministic
// map on a finite set ⇒ every trajectory is a transient "tail" feeding a cycle.
//
// We compute the full functional-graph statistics — five of them calibrated against
// catalogued OEIS sequences — plus the worst-case TRANSIENT length maxTail(n): the
// largest number of moves any partition of n needs to FIRST become periodic.

export function partitions(n) {
  const res = [], cur = [];
  (function rec(rem, max) {
    if (rem === 0) { res.push(cur.slice()); return; }
    for (let k = Math.min(rem, max); k >= 1; k--) { cur.push(k); rec(rem - k, k); cur.pop(); }
  })(n, n);
  return res; // weakly decreasing
}
const key = p => p.join(',');
export function move(p) {
  const piles = p.length, np = [];
  for (const x of p) if (x - 1 > 0) np.push(x - 1);
  np.push(piles);
  np.sort((a, b) => b - a);
  return np;
}

function graph(n) {
  const parts = partitions(n), N = parts.length, idx = new Map();
  parts.forEach((p, i) => idx.set(key(p), i));
  const next = parts.map(p => idx.get(key(move(p))));
  // cyclic (recurrent) nodes
  const stt = new Uint8Array(N), cyclic = new Uint8Array(N);
  for (let s = 0; s < N; s++) {
    if (stt[s]) continue;
    const path = []; let u = s;
    while (stt[u] === 0) { stt[u] = 1; path.push(u); u = next[u]; }
    if (stt[u] === 1) { let v = u; do { cyclic[v] = 1; v = next[v]; } while (v !== u); }
    for (const w of path) stt[w] = 2;
  }
  return { parts, N, next, cyclic };
}

// transient length of every node = distance to the cyclic set, by reverse BFS
function tails({ N, next, cyclic }) {
  const rev = Array.from({ length: N }, () => []);
  next.forEach((j, i) => rev[j].push(i));
  const dist = new Int32Array(N).fill(-1), q = [];
  for (let i = 0; i < N; i++) if (cyclic[i]) { dist[i] = 0; q.push(i); }
  for (let h = 0; h < q.length; h++) { const u = q[h]; for (const w of rev[u]) if (dist[w] < 0) { dist[w] = dist[u] + 1; q.push(w); } }
  return dist;
}

export function analyze(n) {
  const g = graph(n), { N, next, cyclic } = g;
  const indeg = new Array(N).fill(0);
  for (const j of next) indeg[j]++;
  const goe = indeg.reduce((s, d) => s + (d === 0 ? 1 : 0), 0);

  const seen = new Uint8Array(N), cycleLens = [];
  for (let s = 0; s < N; s++) if (cyclic[s] && !seen[s]) { let len = 0, v = s; do { seen[v] = 1; len++; v = next[v]; } while (v !== s); cycleLens.push(len); }
  const numCycles = cycleLens.length;
  const fixed = cycleLens.filter(l => l === 1).length;
  const longest = cycleLens.length ? Math.max(...cycleLens) : 0;
  const recurrent = cyclic.reduce((s, c) => s + c, 0);

  const dist = tails(g);
  let maxTail = 0, totalSettle = 0; for (let i = 0; i < N; i++) { if (dist[i] > maxTail) maxTail = dist[i]; totalSettle += dist[i]; }
  let maxTailCount = 0; for (let i = 0; i < N; i++) if (dist[i] === maxTail) maxTailCount++;

  return { n, parts: N, fixed, numCycles, recurrent, goe, longest, maxTail, maxTailCount, totalSettle, cycleLens: cycleLens.sort((a, b) => a - b) };
}

// independent transient check: forward iteration with a per-node memo (no reverse graph)
export function maxTailForward(n) {
  const g = graph(n), { N, next, cyclic } = g;
  const memo = new Int32Array(N).fill(-1);
  const dof = u => { // depth-of-tail, iterative
    const stack = []; let v = u;
    while (memo[v] < 0 && !cyclic[v]) { stack.push(v); v = next[v]; }
    let base = cyclic[v] ? 0 : memo[v];
    while (stack.length) { memo[stack.pop()] = ++base; }
    return memo[u] = cyclic[u] ? 0 : memo[u];
  };
  let m = 0; for (let s = 0; s < N; s++) m = Math.max(m, cyclic[s] ? 0 : dof(s));
  return m;
}
