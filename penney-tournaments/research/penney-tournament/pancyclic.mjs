// research/penney-tournament/pancyclic.mjs
//
// Is the giant whirlpool PANCYCLIC — does it contain a directed cycle of EVERY
// length from the girth up to its own size (Hamiltonian)? For k<=4 structure.mjs
// settles this exactly by Held-Karp. For larger k that DP is infeasible, so here
// we do the honest one-sided thing: SEARCH for an exact witness cycle of each
// length L, and verify every witness edge-by-edge against the exact engine. A
// found+verified witness PROVES a cycle of length L exists; a failure to find one
// within budget proves NOTHING (reported as "not witnessed", never as "absent").

import { tournament } from './engine.mjs';

function giantSCC(k) {
  const t = tournament(k);
  const { n, rel, S } = t;
  const adj = Array.from({ length: n }, (_, i) => {
    const o = []; for (let j = 0; j < n; j++) if (rel[i][j] === 1) o.push(j); return o;
  });
  // Tarjan (iterative)
  const index = new Array(n).fill(-1), low = new Array(n).fill(0), on = new Array(n).fill(false);
  const st = [], comps = []; let idx = 0;
  for (let s = 0; s < n; s++) {
    if (index[s] !== -1) continue;
    const work = [{ v: s, i: 0 }]; index[s] = low[s] = idx++; st.push(s); on[s] = true;
    while (work.length) {
      const top = work[work.length - 1], v = top.v;
      if (top.i < adj[v].length) {
        const w = adj[v][top.i++];
        if (index[w] === -1) { index[w] = low[w] = idx++; st.push(w); on[w] = true; work.push({ v: w, i: 0 }); }
        else if (on[w] && index[w] < low[v]) low[v] = index[w];
      } else {
        if (low[v] === index[v]) { const c = []; for (;;) { const w = st.pop(); on[w] = false; c.push(w); if (w === v) break; } comps.push(c); }
        work.pop(); if (work.length) { const p = work[work.length - 1].v; if (low[v] < low[p]) low[p] = low[v]; }
      }
    }
  }
  comps.sort((a, b) => b.length - a.length);
  const giant = comps[0];
  const gset = new Set(giant);
  const sub = new Map();               // vertex -> local adj within the giant
  for (const v of giant) sub.set(v, adj[v].filter((w) => gset.has(w)));
  return { t, giant, sub, adj, S };
}

// deterministic PRNG so runs are reproducible (no Math.random)
function mulberry32(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let x = Math.imul(a ^ (a >>> 15), 1 | a); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }

// randomized DFS: find a simple directed cycle of length exactly L in the giant.
function findCycleLen(giant, sub, L, rng, budget) {
  const verts = giant.slice();
  for (let tries = 0; tries < budget; tries++) {
    const start = verts[(rng() * verts.length) | 0];
    const path = [start]; const inpath = new Set([start]);
    let ok = true;
    while (path.length < L) {
      const u = path[path.length - 1];
      const nb = sub.get(u).filter((w) => !inpath.has(w));
      if (!nb.length) { ok = false; break; }
      const w = nb[(rng() * nb.length) | 0];
      path.push(w); inpath.add(w);
    }
    if (ok && path.length === L && sub.get(path[L - 1]).includes(start)) return path;
  }
  return null;
}

// verify a cycle witness edge-by-edge against the exact engine
function verifyCycle(t, path) {
  const { rel } = t; const L = path.length;
  for (let i = 0; i < L; i++) {
    const a = path[i], b = path[(i + 1) % L];
    if (rel[a][b] !== 1) return false;
  }
  return true;
}

export function pancyclicWitnesses(k, budgetPerLen = 40000, seed = 12345) {
  const { t, giant, sub, S } = giantSCC(k);
  const m = giant.length;
  const rng = mulberry32(seed + k * 1009);
  const found = []; const missing = [];
  for (let L = 3; L <= m; L++) {
    const w = findCycleLen(giant, sub, L, rng, budgetPerLen);
    if (w && verifyCycle(t, w)) found.push(L);
    else missing.push(L);
  }
  return { k, giantSize: m, found, missing, allFound: missing.length === 0,
           sampleHam: missing.length === 0 ? findCycleLen(giant, sub, m, rng, budgetPerLen)?.map((i) => S[i]) : null };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const KMAX = Number(process.argv[2] || 6);
  const budget = Number(process.argv[3] || 60000);
  for (let k = 3; k <= KMAX; k++) {
    const t0 = Date.now();
    const r = pancyclicWitnesses(k, budget);
    const dt = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`k=${k}  giant=${r.giantSize}  witnessed lengths 3..${r.giantSize}: ${r.allFound ? 'ALL (pancyclic ✓)' : 'missing ' + r.missing.join(',')}  [${dt}s]`);
    if (r.allFound && r.sampleHam) console.log(`   Hamiltonian witness (len ${r.giantSize}): ${r.sampleHam.slice(0, 6).join('→')}→…→${r.sampleHam[0]}`);
  }
}
