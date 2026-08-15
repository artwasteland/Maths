// research/graceful-census/graceful.mjs
//
// Exact counters for GRACEFUL LABELINGS of a graph, plus the standard named
// graph families whose graceful-labeling counts this notebook computes.
//
// A graceful labeling of a graph with m edges assigns DISTINCT integer labels
// from {0,1,...,m} to the vertices so that the m induced edge labels
// |f(u) - f(v)| are exactly {1, 2, ..., m} (each difference occurs once). We
// count ALL graceful labelings (both members of every complement pair f, m-f),
// which is the convention of OEIS's graceful-labeling "total" census
// (A333720 cycle, A333719 ladder, A333672 wheel, A336677 prism, A337795 gear).
//
// TRUST RULE (never one code path). Two structurally UNRELATED exact counters
// must agree on every term:
//   (A) countByVertices — backtracking that assigns a LABEL to each vertex, in a
//       greedy most-constrained-first order, pruning on the difference set.
//   (B) countByLabels   — backtracking that walks the LABEL VALUES 0..m in order
//       and decides which (if any) vertex receives each value; a different search
//       tree entirely. Used as the independent cross-check (smaller graphs).
// Both are validated in verify.mjs against FIVE published OEIS sequences before
// any new value is trusted, and a plain brute force pins the smallest cases.

// ---------------------------------------------------------------------------
// Graph helpers
// ---------------------------------------------------------------------------
function adjacency(v, edges) {
  const adj = Array.from({ length: v }, () => []);
  for (const [a, b] of edges) { adj[a].push(b); adj[b].push(a); }
  return adj;
}

// Greedy vertex order: repeatedly take the unplaced vertex with the most
// already-placed neighbours (ties broken by higher degree, then lower id).
// This front-loads the difference constraints so the search prunes hardest.
function greedyOrder(v, adj) {
  const placed = new Array(v).fill(false);
  const order = [];
  const deg = adj.map(a => a.length);
  for (let step = 0; step < v; step++) {
    let best = -1, bestBack = -1, bestDeg = -1;
    for (let u = 0; u < v; u++) {
      if (placed[u]) continue;
      let back = 0;
      for (const w of adj[u]) if (placed[w]) back++;
      if (back > bestBack || (back === bestBack && deg[u] > bestDeg)) {
        best = u; bestBack = back; bestDeg = deg[u];
      }
    }
    placed[best] = true; order.push(best);
  }
  return order;
}

// (A) assign a label to each vertex, greedy order, prune on difference set.
export function countByVertices(v, edges) {
  const m = edges.length;
  const adj = adjacency(v, edges);
  const order = greedyOrder(v, adj);
  const pos = new Array(v); order.forEach((vv, i) => pos[vv] = i);
  // earlier-order neighbours of order[idx] (already labelled when it is placed)
  const back = order.map(vv => adj[vv].filter(u => pos[u] < pos[vv]));
  const label = new Array(v).fill(-1);
  const usedLabel = new Uint8Array(m + 1);
  const usedDiff = new Uint8Array(m + 1);
  let count = 0;
  (function rec(idx) {
    if (idx === v) { count++; return; }
    const vv = order[idx], bn = back[idx];
    for (let L = 0; L <= m; L++) {
      if (usedLabel[L]) continue;
      let ok = true; let k = 0; const added = [];
      for (; k < bn.length; k++) {
        const d = Math.abs(L - label[bn[k]]);
        if (d < 1 || d > m || usedDiff[d]) { ok = false; break; }
        usedDiff[d] = 1; added.push(d);
      }
      if (ok) { usedLabel[L] = 1; label[vv] = L; rec(idx + 1); label[vv] = -1; usedLabel[L] = 0; }
      for (let j = 0; j < added.length; j++) usedDiff[added[j]] = 0;
    }
  })(0);
  return count;
}

// (B) walk label values 0..m; at each, either leave it unused or give it to one
// still-unlabelled vertex. A structurally different search from (A).
export function countByLabels(v, edges) {
  const m = edges.length;
  const adj = adjacency(v, edges);
  const label = new Array(v).fill(-1);      // label[vertex] or -1
  const usedDiff = new Uint8Array(m + 1);
  let placed = 0;
  let count = 0;
  (function rec(val, remainingLabels) {
    if (placed === v) { count++; return; }
    // prune: not enough label values left to place all remaining vertices
    if (remainingLabels < v - placed) return;
    // option 1: skip this label value (only if we can still fit everyone)
    if (remainingLabels - 1 >= v - placed) rec(val + 1, remainingLabels - 1);
    // option 2: assign val to some unlabelled vertex
    for (let u = 0; u < v; u++) {
      if (label[u] !== -1) continue;
      let ok = true; const added = [];
      for (const w of adj[u]) {
        if (label[w] === -1) continue;
        const d = Math.abs(val - label[w]);
        if (d < 1 || d > m || usedDiff[d]) { ok = false; break; }
        usedDiff[d] = 1; added.push(d);
      }
      if (ok) { label[u] = val; placed++; rec(val + 1, remainingLabels - 1); placed--; label[u] = -1; }
      for (let j = 0; j < added.length; j++) usedDiff[added[j]] = 0;
    }
  })(0, m + 1);
  return count;
}

// Plain brute force (tiny graphs only) — the ground-truth pin.
export function countBrute(v, edges) {
  const m = edges.length;
  const label = new Array(v);
  const used = new Uint8Array(m + 1);
  let count = 0;
  (function rec(i) {
    if (i === v) {
      const seen = new Set();
      for (const [a, b] of edges) { const d = Math.abs(label[a] - label[b]); if (d < 1 || d > m || seen.has(d)) return; seen.add(d); }
      if (seen.size === m) count++;
      return;
    }
    for (let L = 0; L <= m; L++) { if (used[L]) continue; used[L] = 1; label[i] = L; rec(i + 1); used[L] = 0; }
  })(0);
  return count;
}

// The main counter used for production values.
export const graceful = countByVertices;

// Enumerate every graceful labeling as a vertex-indexed label vector (small graphs).
export function enumerateGraceful(v, edges) {
  const m = edges.length;
  const adj = adjacency(v, edges);
  const order = greedyOrder(v, adj);
  const pos = new Array(v); order.forEach((vv, i) => pos[vv] = i);
  const back = order.map(vv => adj[vv].filter(u => pos[u] < pos[vv]));
  const label = new Array(v).fill(-1);
  const usedLabel = new Uint8Array(m + 1), usedDiff = new Uint8Array(m + 1);
  const out = [];
  (function rec(idx) {
    if (idx === v) { out.push(label.slice()); return; }
    const vv = order[idx], bn = back[idx];
    for (let L = 0; L <= m; L++) {
      if (usedLabel[L]) continue;
      let ok = true; const added = [];
      for (let k = 0; k < bn.length; k++) { const d = Math.abs(L - label[bn[k]]); if (d < 1 || d > m || usedDiff[d]) { ok = false; break; } usedDiff[d] = 1; added.push(d); }
      if (ok) { usedLabel[L] = 1; label[vv] = L; rec(idx + 1); label[vv] = -1; usedLabel[L] = 0; }
      for (let j = 0; j < added.length; j++) usedDiff[added[j]] = 0;
    }
  })(0);
  return out;
}

// All automorphisms of a graph (vertex permutations preserving adjacency),
// found by degree-respecting backtracking. Returns array of permutations
// (perm[i] = image of vertex i). Fine for the small graphs here.
export function automorphisms(v, edges) {
  const adj = adjacency(v, edges);
  const nbr = adj.map(a => new Set(a));
  const deg = adj.map(a => a.length);
  const order = [...Array(v).keys()].sort((a, b) => deg[b] - deg[a]); // high degree first
  const perm = new Array(v).fill(-1);
  const usedImg = new Array(v).fill(false);
  const autos = [];
  (function rec(idx) {
    if (idx === v) { autos.push(perm.slice()); return; }
    const u = order[idx];
    for (let w = 0; w < v; w++) {
      if (usedImg[w] || deg[w] !== deg[u]) continue;
      // check consistency with already-mapped neighbours
      let ok = true;
      for (let k = 0; k < idx; k++) {
        const x = order[k];
        const adjUX = nbr[u].has(x);
        const adjImg = nbr[w].has(perm[x]);
        if (adjUX !== adjImg) { ok = false; break; }
      }
      if (ok) { perm[u] = w; usedImg[w] = true; rec(idx + 1); usedImg[w] = false; perm[u] = -1; }
    }
  })(0);
  return autos;
}

// "Fundamentally different" graceful labelings: orbits under Aut(G) x {id, complement}.
// Computed by canonicalising every graceful labeling and counting distinct forms —
// no free-action assumption. Used to cross-check totals against published OEIS
// "fundamentally different" sequences (helm A387800, book A387795, gear A387798).
export function fundamentallyDifferent(v, edges) {
  const m = edges.length;
  const autos = automorphisms(v, edges);
  const all = enumerateGraceful(v, edges);
  const canon = new Set();
  for (const lab of all) {
    let best = null;
    for (const g of autos) {
      // g permutes vertices: new label of vertex i is lab[g^{-1}(i)]; equivalently
      // build vector where position i gets lab of the vertex mapping to i.
      const inv = new Array(v);
      for (let i = 0; i < v; i++) inv[g[i]] = i;
      const relabelled = new Array(v);
      for (let i = 0; i < v; i++) relabelled[i] = lab[inv[i]];
      for (const comp of [0, 1]) {
        const cand = comp ? relabelled.map(x => m - x) : relabelled;
        const key = cand.join(',');
        if (best === null || key < best) best = key;
      }
    }
    canon.add(best);
  }
  return canon.size;
}

// ---------------------------------------------------------------------------
// Graph families
// ---------------------------------------------------------------------------
// Validators (already in OEIS) — used to prove the counters correct:
export const path = n => { const e = []; for (let i = 0; i < n - 1; i++) e.push([i, i + 1]); return { v: n, e }; };
export const cycle = n => { const e = []; for (let i = 0; i < n; i++) e.push([i, (i + 1) % n]); return { v: n, e }; };
// ladder L_n = P_n x K2  (A333719, indexed from n=1: L_1 = K_2)
export const ladder = n => { const e = []; for (let i = 0; i < n - 1; i++) { e.push([i, i + 1]); e.push([n + i, n + i + 1]); } for (let i = 0; i < n; i++) e.push([i, n + i]); return { v: 2 * n, e }; };
// prism / circular ladder CL_n = C_n x K2  (A336677, from n=3)
export const prism = n => { const e = []; for (let i = 0; i < n; i++) { e.push([i, (i + 1) % n]); e.push([n + i, n + (i + 1) % n]); e.push([i, n + i]); } return { v: 2 * n, e }; };
// wheel W_n = C_n + K1  (A333672, from n=3; hub = n)
export const wheel = n => { const e = []; for (let i = 0; i < n; i++) { e.push([i, (i + 1) % n]); e.push([i, n]); } return { v: n + 1, e }; };
// gear G_n = wheel with a vertex subdividing each rim edge  (A337795, from n=3; hub = 2n)
export const gear = n => { const e = []; const hub = 2 * n; for (let i = 0; i < 2 * n; i++) e.push([i, (i + 1) % (2 * n)]); for (let i = 0; i < 2 * n; i += 2) e.push([i, hub]); return { v: 2 * n + 1, e }; };

// The TARGETS (graceful-labeling total absent from OEIS):
// fan F_n = K1 + P_n  : hub joined to every vertex of a path on n vertices. v=n+1, m=2n-1.
export const fan = n => { const e = []; for (let i = 0; i < n - 1; i++) e.push([i, i + 1]); for (let i = 0; i < n; i++) e.push([i, n]); return { v: n + 1, e }; };
// friendship / Dutch windmill F_k : k triangles sharing one common vertex (center=0). v=2k+1, m=3k.
export const friendship = k => { const e = []; for (let i = 0; i < k; i++) { const a = 1 + 2 * i, b = 2 + 2 * i; e.push([0, a]); e.push([0, b]); e.push([a, b]); } return { v: 2 * k + 1, e }; };
// helm H_n = wheel W_n + a pendant leaf on each rim vertex. hub=n, pendants n+1..2n. v=2n+1, m=3n.
export const helm = n => { const e = []; const hub = n; for (let i = 0; i < n; i++) { e.push([i, (i + 1) % n]); e.push([i, hub]); e.push([i, n + 1 + i]); } return { v: 2 * n + 1, e }; };
// triangular book B(n) = K_{1,1,n} : n triangles sharing the spine edge 0-1. v=n+2, m=2n+1.
export const bookTri = n => { const e = [[0, 1]]; for (let i = 0; i < n; i++) { e.push([0, 2 + i]); e.push([1, 2 + i]); } return { v: n + 2, e }; };
// quadrilateral book : n 4-cycles sharing the spine edge 0-1. v=2n+2, m=3n+1.
export const bookQuad = n => { const e = [[0, 1]]; for (let i = 0; i < n; i++) { const a = 2 + 2 * i, b = 3 + 2 * i; e.push([0, a]); e.push([a, b]); e.push([b, 1]); } return { v: 2 + 2 * n, e }; };

export const FAMILIES = { path, cycle, ladder, prism, wheel, gear, fan, friendship, helm, bookTri, bookQuad };

// CLI: node graceful.mjs <family> <lo> <hi> [method]
if (import.meta.url === `file://${process.argv[1]}`) {
  const [, , fam = 'validate', lo = '1', hi = '8', method = 'A'] = process.argv;
  const fn = method === 'B' ? countByLabels : method === 'brute' ? countBrute : countByVertices;
  if (fam === 'validate') {
    const T = { cycle: [3, 9], ladder: [2, 6], wheel: [3, 7], prism: [3, 6], gear: [3, 5] };
    for (const [name, [a, b]] of Object.entries(T)) {
      const out = [];
      for (let n = a; n <= b; n++) { const g = FAMILIES[name](n); const t0 = Date.now(); out.push(countByVertices(g.v, g.e)); if (Date.now() - t0 > 20000) break; }
      console.log(name, '(' + a + '..):', out.join(','));
    }
  } else {
    const out = [];
    for (let n = +lo; n <= +hi; n++) {
      const g = FAMILIES[fam](n); const t0 = Date.now();
      out.push(fn(g.v, g.e));
      const dt = Date.now() - t0;
      process.stderr.write(`${fam}(${n}) = ${out[out.length - 1]}  [${dt}ms, v=${g.v}, m=${g.e.length}]\n`);
      if (dt > 30000) break;
    }
    console.log(fam + ':', out.join(','));
  }
}
