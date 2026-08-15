// s-Bulgarian solitaire on the partitions of n (well-behaved sigma-Bulgarian, sigma(h)=min(h,s)).
//
// Move B_s: from every pile of size h remove min(h, s) cards; collect ALL removed cards into
// ONE new pile; drop emptied piles; re-sort descending. s=1 is classic Bulgarian solitaire.
//
// Deterministic map on partitions(n) => every trajectory is a transient tail feeding a cycle.
// We compute the full functional-graph statistics for any s, using a reverse-BFS tail method
// that is INDEPENDENT of the Python forward-memo path (research/bulgarian-solitaire/s_explore.py),
// so every settling number is cross-checked two ways before it is trusted.

export function partitions(n) {
  const res = [], cur = [];
  (function rec(rem, max) {
    if (rem === 0) { res.push(cur.slice()); return; }
    for (let k = Math.min(rem, max); k >= 1; k--) { cur.push(k); rec(rem - k, k); cur.pop(); }
  })(n, n);
  return res; // weakly decreasing
}
const key = p => p.join(',');

export function move(p, s) {
  let removed = 0;
  const np = [];
  for (const x of p) {
    const take = x < s ? x : s;
    removed += take;
    if (x - take > 0) np.push(x - take);
  }
  if (removed > 0) np.push(removed);
  np.sort((a, b) => b - a);
  return np;
}

// The step-s staircase fixed point (a, a-s, ..., r), r in [1,s], if one sums to n; else null.
export function staircase(n, s) {
  for (let m = 1; m <= n; m++) {
    for (let r = 1; r <= s; r++) {
      const total = m * r + s * m * (m - 1) / 2;
      if (total === n) return Array.from({ length: m }, (_, i) => (r + (m - 1) * s) - i * s);
      if (total > n) break;
    }
  }
  return null;
}

function graph(n, s) {
  const parts = partitions(n), N = parts.length, idx = new Map();
  parts.forEach((p, i) => idx.set(key(p), i));
  const next = parts.map(p => idx.get(key(move(p, s))));
  const stt = new Uint8Array(N), cyclic = new Uint8Array(N);
  for (let a = 0; a < N; a++) {
    if (stt[a]) continue;
    const path = []; let u = a;
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

export function analyze(n, s) {
  const g = graph(n, s), { N, next, cyclic } = g;
  const indeg = new Array(N).fill(0);
  for (const j of next) indeg[j]++;
  const goe = indeg.reduce((acc, d) => acc + (d === 0 ? 1 : 0), 0);

  const seen = new Uint8Array(N), cycleLens = [];
  for (let a = 0; a < N; a++) if (cyclic[a] && !seen[a]) { let len = 0, v = a; do { seen[v] = 1; len++; v = next[v]; } while (v !== a); cycleLens.push(len); }
  const numCycles = cycleLens.length;
  const fixed = cycleLens.filter(l => l === 1).length;
  const longest = cycleLens.length ? Math.max(...cycleLens) : 0;
  const recurrent = cyclic.reduce((acc, c) => acc + c, 0);

  const dist = tails(g);
  let maxTail = 0, totalSettle = 0; for (let i = 0; i < N; i++) { if (dist[i] > maxTail) maxTail = dist[i]; totalSettle += dist[i]; }
  let maxTailCount = 0; for (let i = 0; i < N; i++) if (dist[i] === maxTail) maxTailCount++;

  return { n, s, parts: N, fixed, numCycles, recurrent, goe, longest, maxTail, maxTailCount, totalSettle, cycleLens: cycleLens.sort((a, b) => a - b) };
}

// independent transient check: forward iteration with a per-node memo (no reverse graph)
export function maxTailForward(n, s) {
  const g = graph(n, s), { N, next, cyclic } = g;
  const memo = new Int32Array(N).fill(-1);
  const dof = u => {
    const stack = []; let v = u;
    while (memo[v] < 0 && !cyclic[v]) { stack.push(v); v = next[v]; }
    let base = cyclic[v] ? 0 : memo[v];
    while (stack.length) { memo[stack.pop()] = ++base; }
    return memo[u] = cyclic[u] ? 0 : memo[u];
  };
  let m = 0; for (let a = 0; a < N; a++) m = Math.max(m, cyclic[a] ? 0 : dof(a));
  return m;
}
