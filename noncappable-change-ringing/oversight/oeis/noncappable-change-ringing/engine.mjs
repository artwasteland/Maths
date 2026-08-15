// engine.mjs — exact counts of change-ringing sequences by length, for n bells.
//
// Faithful port of Jonas K. Sønsteby's definition (github.com/jonassonsteby/
// change-ringing), the source of OEIS A324942 (n=4, cyclic), A324944 (n=5),
// A324946 (n=6).  We re-derive his transition rules and count three families
// of sequences by length L exactly (BigInt), with NO path storage — a depth-
// first traversal that *counts* rather than *lists*, so memory is O(n!) not
// O(number of sequences).
//
// A "change-ringing sequence" of length L for n bells is a sequence of L
// DISTINCT rows (permutations) P_1..P_L with:
//   (crit 3) P_1 = rounds = (1,2,...,n)
//   (crit 1) each P_i -> P_{i+1} is one "change": every bell moves <= 1 place
//            (a product of disjoint adjacent transpositions; >=1 swap)
//   (crit 2) no row repeats
// i.e. a SIMPLE PATH of L vertices from rounds in the change-ringing graph G_n.
// The length is the number of unique rows (Sønsteby's convention).
//
//   PATH       (option 1): any such simple path.                       [all]
//   CYCLIC     (option 0): path whose last row is adjacent to rounds   [cappable]
//                          (so appending rounds closes it legally).
//   NONCAPPABLE(option 2): path whose last row is NOT adjacent to rounds.
// For every L >= 2:  path(L) = cyclic(L) + noncappable(L).
// L = 1 is the trivial sequence {rounds}: Sønsteby sets path(1)=cyclic(1)=1,
// noncappable(1)=0.
//
// Usage: node engine.mjs <n> [maxL]
//        node engine.mjs 4            -> full (maxL defaults to n!)
//        node engine.mjs 5 14         -> partial (5 bells, up to L=14)

// ---- transition rules: faithful port of Sønsteby's recursive transitions() ----
// A rule is a position-permutation array `r` of length n; applying it to a row p
// yields row q with q[i] = p[r[i]].  The set of rules = nonempty products of
// disjoint adjacent transpositions (count = Fibonacci(n+1) - 1 = OEIS A000071).
function transitions(n) {
  if (n < 2) return [];
  if (n === 2) return [[1, 0]];
  const prev = transitions(n - 1).map((c) => c.concat([n - 1])); // extend with fixed top bell
  const temp = prev.map((c) => c.slice());
  temp.push(Array.from({ length: n }, (_, i) => i)); // identity
  const add = [];
  for (const t of temp) {
    if (t[t.length - 2] === n - 2) {
      add.push(t.slice(0, -2).concat([t[t.length - 1], t[t.length - 2]]));
    }
  }
  return prev.concat(add);
}

// ---- permutation indexing (Lehmer code <-> rank) so a row is one integer ----
function factorials(n) {
  const f = [1n];
  for (let i = 1; i <= n; i++) f.push(f[i - 1] * BigInt(i));
  return f;
}

function permToRank(p, fact) {
  // p is an array (a permutation of 0..n-1); returns its lexicographic rank.
  const n = p.length;
  const seen = new Array(n).fill(false);
  let rank = 0n;
  for (let i = 0; i < n; i++) {
    let smaller = 0;
    for (let j = 0; j < p[i]; j++) if (!seen[j]) smaller++;
    rank += BigInt(smaller) * fact[n - 1 - i];
    seen[p[i]] = true;
  }
  return Number(rank); // n! <= 9! = 362880 fits in a JS number comfortably
}

function rankToPerm(rank, n, fact) {
  const avail = Array.from({ length: n }, (_, i) => i);
  const p = [];
  let r = BigInt(rank);
  for (let i = 0; i < n; i++) {
    const f = fact[n - 1 - i];
    const idx = Number(r / f);
    r = r % f;
    p.push(avail[idx]);
    avail.splice(idx, 1);
  }
  return p;
}

function buildGraph(n) {
  const fact = factorials(n);
  const N = Number(fact[n]);
  const rules = transitions(n);
  // adjacency: for each row (by rank), the ranks reachable by one change.
  const adj = new Array(N);
  for (let v = 0; v < N; v++) {
    const p = rankToPerm(v, n, fact);
    const nbrs = [];
    for (const r of rules) {
      const q = new Array(n);
      for (let i = 0; i < n; i++) q[i] = p[r[i]];
      nbrs.push(permToRank(q, fact));
    }
    adj[v] = nbrs;
  }
  const rounds = 0; // identity has rank 0
  const nbrOfRounds = new Set(adj[rounds]);
  return { N, adj, rounds, nbrOfRounds, NoTR: rules.length };
}

// ---- count simple paths from `rounds` by length, without storing paths ----
function countByLength(n, maxL) {
  const G = buildGraph(n);
  const { N, adj, rounds, nbrOfRounds } = G;
  if (maxL === undefined) maxL = N; // n!
  const path = new Array(maxL + 1).fill(0n);   // option 1 (all simple paths)
  const cyclic = new Array(maxL + 1).fill(0n); // option 0 (endpoint ~ rounds)
  const noncappableDirect = new Array(maxL + 1).fill(0n); // endpoint not ~ rounds
  const visited = new Uint8Array(N);

  // L=1 trivial sequence {rounds}
  path[1] = 1n;
  cyclic[1] = 1n;

  visited[rounds] = 1;
  // DFS; `depth` = number of vertices on the current path (>=1).
  function dfs(v, depth) {
    if (depth >= maxL) return;
    const nd = depth + 1;
    for (const w of adj[v]) {
      if (visited[w]) continue;
      visited[w] = 1;
      path[nd] += 1n;
      if (nbrOfRounds.has(w)) cyclic[nd] += 1n;
      else noncappableDirect[nd] += 1n;
      dfs(w, nd);
      visited[w] = 0;
    }
  }
  dfs(rounds, 1);

  const noncappable = new Array(maxL + 1).fill(0n);
  for (let L = 1; L <= maxL; L++) noncappable[L] = path[L] - cyclic[L];
  noncappable[1] = 0n; // Sønsteby's L=1 convention (option 2 empty at L=1)
  return { G, path, cyclic, noncappable, noncappableDirect, maxL };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const n = parseInt(process.argv[2] || '4', 10);
  const maxL = process.argv[3] ? parseInt(process.argv[3], 10) : undefined;
  const t0 = Date.now();
  const { G, path, cyclic, noncappable, maxL: ML } = countByLength(n, maxL);
  const dt = ((Date.now() - t0) / 1000).toFixed(2);
  const fmt = (a) => a.slice(1).map((x) => x.toString()).join(', ');
  console.log(`# n=${n} bells, |G|=${G.N} rows, ${G.NoTR} changes/row, maxL=${ML}, ${dt}s`);
  console.log(`CYCLIC      (A324942-family): ${fmt(cyclic)}`);
  console.log(`PATH        (option 1):       ${fmt(path)}`);
  console.log(`NONCAPPABLE (option 2):       ${fmt(noncappable)}`);
}

export { transitions, buildGraph, countByLength };
