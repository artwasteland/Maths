// research/penney-tournament/structure.mjs
//
// THE STRUCTURE of the Penney dominance digraph at length k.
//
// The digraph D_k: vertices = the 2^k length-k H/T patterns; a directed edge
// A -> B iff P(A appears before B) > 1/2 (A strictly beats B). Ties (p = 1/2)
// are NON-edges, so D_k is NOT a full tournament — which makes its coarse
// structure a genuine, non-obvious question, not a theorem you can quote.
//
// This file settles three structural invariants, exactly, for every k it can
// reach, reusing the doubly-verified engine (Conway <-> Markov, verify.mjs 49/49):
//
//   (1) STRONG CONNECTIVITY.  Tarjan's SCC decomposition. Is D_k one whirlpool
//       (every pattern reaches every other by a chain of strict upsets), or does
//       it split into a hierarchy of tiers? Also: are there sources (unbeaten by
//       any single pattern) or sinks (beating no one)?
//   (2) GIRTH.  Shortest directed cycle (BFS); reproduced from girth.mjs.
//   (3) CIRCUMFERENCE / PANCYCLICITY (small k only, exact by Held-Karp DP over
//       vertex subsets — feasible for n <= ~18, i.e. k <= 4). For which lengths
//       L does D_k contain a directed cycle of length exactly L?
//
// Everything is exact (BigInt win-probabilities); nothing is sampled.

import { tournament } from './engine.mjs';
import { girth } from './girth.mjs';

// ---------- Tarjan SCC (iterative, safe for n up to a few thousand) ----------
function sccs(n, adj) {
  const index = new Array(n).fill(-1);
  const low = new Array(n).fill(0);
  const onStack = new Array(n).fill(false);
  const stack = [];
  const comps = [];
  let idx = 0;
  for (let s = 0; s < n; s++) {
    if (index[s] !== -1) continue;
    // iterative DFS with an explicit work stack of {v, i(=next neighbour)}
    const work = [{ v: s, i: 0 }];
    index[s] = low[s] = idx++; stack.push(s); onStack[s] = true;
    while (work.length) {
      const top = work[work.length - 1];
      const v = top.v;
      if (top.i < adj[v].length) {
        const w = adj[v][top.i++];
        if (index[w] === -1) {
          index[w] = low[w] = idx++; stack.push(w); onStack[w] = true;
          work.push({ v: w, i: 0 });
        } else if (onStack[w]) {
          if (index[w] < low[v]) low[v] = index[w];
        }
      } else {
        if (low[v] === index[v]) {
          const comp = [];
          for (;;) { const w = stack.pop(); onStack[w] = false; comp.push(w); if (w === v) break; }
          comps.push(comp);
        }
        work.pop();
        if (work.length) { const p = work[work.length - 1].v; if (low[v] < low[p]) low[p] = low[v]; }
      }
    }
  }
  return comps;
}

// ---------- Held-Karp: exact set of directed-cycle lengths present (small n) ----------
// dp over (subset S containing start s, endpoint v in S): is there a simple path
// s -> ... -> v visiting exactly S? Then a cycle of length |S| exists iff some v
// in S has an edge v -> s. Standard O(2^n * n^2); only run for n <= 18.
function cycleLengths(n, adjMat) {
  const lens = new Set();
  for (let s = 0; s < n; s++) {
    const size = 1 << n;
    // dp[S] = bitmask of endpoints reachable as a simple path from s covering exactly S
    const dp = new Int32Array(size);      // works while n <= 31 (endpoint bitmask fits in int32... n<=30)
    dp[1 << s] = 1 << s;
    for (let S = 0; S < size; S++) {
      if (!(S & (1 << s))) continue;
      let ends = dp[S];
      if (!ends) continue;
      while (ends) {
        const v = 31 - Math.clz32(ends & -ends);   // low set bit index
        ends &= ends - 1;
        // close a cycle: v -> s
        if (S !== (1 << s) && adjMat[v][s]) lens.add(popcount(S));
        // extend to w not in S with v -> w
        for (let w = 0; w < n; w++) {
          if (S & (1 << w)) continue;
          if (adjMat[v][w]) dp[S | (1 << w)] |= (1 << w);
        }
      }
    }
    // once s has contributed, we can drop s from later starts to avoid double work,
    // but correctness doesn't require it; keep simple.
  }
  return [...lens].sort((a, b) => a - b);
}
function popcount(x) { let c = 0; while (x) { x &= x - 1; c++; } return c; }

export function structure(k, { doCycles = null } = {}) {
  const t = tournament(k);
  const { n, rel, S } = t;
  const adj = Array.from({ length: n }, (_, i) => {
    const o = []; for (let j = 0; j < n; j++) if (rel[i][j] === 1) o.push(j); return o;
  });
  const outdeg = adj.map((a) => a.length);
  const indeg = new Array(n).fill(0);
  for (let i = 0; i < n; i++) for (const j of adj[i]) indeg[j]++;

  const comps = sccs(n, adj);
  const sizes = comps.map((c) => c.length).sort((a, b) => b - a);
  const nSCC = comps.length;
  const giant = sizes[0];
  const trivial = sizes.filter((s) => s === 1).length;   // singletons

  const sources = [];   // in-degree 0 (no single pattern strictly beats them)
  const sinks = [];     // out-degree 0 (strictly beat no one)
  for (let i = 0; i < n; i++) { if (indeg[i] === 0) sources.push(S[i]); if (outdeg[i] === 0) sinks.push(S[i]); }

  const g = girth(k);

  const runCycles = doCycles === null ? n <= 18 : doCycles;
  let cyc = null;
  if (runCycles) {
    const adjMat = rel.map((r) => r.map((x) => (x === 1 ? 1 : 0)));
    cyc = cycleLengths(n, adjMat);
  }

  return {
    k, n,
    nSCC, sccSizes: sizes, giant, trivialSCC: trivial,
    stronglyConnected: nSCC === 1,
    sources, sinks,
    girth: g.girth, girthWitness: g.witness,
    cycleLengths: cyc,
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const KMAX = Number(process.argv[2] || 10);
  console.log('k\tn\tSCCs\tgiant\ttrivial\tstrong?\tsrc\tsink\tgirth');
  for (let k = 1; k <= KMAX; k++) {
    const r = structure(k, { doCycles: false });
    console.log(
      `${k}\t${r.n}\t${r.nSCC}\t${r.giant}\t${r.trivialSCC}\t${r.stronglyConnected ? 'YES' : 'no'}` +
      `\t${r.sources.length}\t${r.sinks.length}\t${r.girth ?? '-'}`
    );
  }
  console.log('\n--- cycle spectrum (exact, small k) ---');
  for (let k = 1; k <= 4; k++) {
    const r = structure(k, { doCycles: true });
    const set = r.cycleLengths;
    const gg = r.girth ?? '-';
    const maxc = set && set.length ? set[set.length - 1] : '-';
    const full = set && set.length ? (set.length === (r.giant - (r.girth ?? r.giant) + 1)) : false;
    console.log(`k=${k}\tn=${r.n}\tgiant=${r.giant}\tgirth=${gg}\tcirc=${maxc}\tcycle-lengths={${set ? set.join(',') : ''}}`);
  }
}
