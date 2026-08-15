// Reproduce every staged term + the calibration values, on two graphs, and ASSERT
// them. Single-swap (permutohedron, graph A) and disjoint-swap (change-ringing,
// graph B).
//
//   node oversight/oeis/permutohedron-hamiltonian-cycles/verify-all.mjs
//
// Until 2026-07-27 this file printed its numbers and exited 0 no matter what they
// were, so a human eye was the only comparator and nothing here could ever go red.
// A mutation probe on the same date confirmed the consequence: every staged term
// could be rewritten and this script's output would not change. It now compares
// what it computes against fixed expected values and exits nonzero on a mismatch.
// The b-file itself is checked by verify-staged.mjs beside this file.

export function allPerms(n) {
  const r = []; const a = [...Array(n).keys()];
  const rec = (k) => { if (k === n) { r.push(a.slice()); return; } for (let i = k; i < n; i++) { [a[k], a[i]] = [a[i], a[k]]; rec(k + 1); [a[k], a[i]] = [a[i], a[k]]; } };
  rec(0); r.sort((x, y) => (x.join('') < y.join('') ? -1 : 1)); return r;
}
export function matchings(n) {
  const mv = []; const go = (s, c) => { if (c.length) mv.push(c.slice()); for (let e = s; e < n - 1; e++) { if (!c.length || e > c[c.length - 1] + 1) { c.push(e); go(e + 1, c); c.pop(); } } };
  go(0, []); return mv;
}
const apply = (p, es) => { const q = p.slice(); for (const e of es) [q[e], q[e + 1]] = [q[e + 1], q[e]]; return q; };

export function build(n, mode) {
  const ps = allPerms(n); const idx = new Map(); ps.forEach((p, i) => idx.set(p.join(','), i));
  const moves = mode === 'A' ? Array.from({ length: n - 1 }, (_, i) => [i]) : matchings(n);
  const adj = ps.map((p) => { const s = new Set(); for (const m of moves) { const j = idx.get(apply(p, m).join(',')); if (j !== undefined) s.add(j); } return [...s]; });
  return { N: ps.length, adj };
}

export function count(N, adj) {
  const vis = new Uint8Array(N); vis[0] = 1; let c = 0n;
  const dfs = (v, d) => { if (d === N) { if (adj[v].includes(0)) c++; return; } for (const w of adj[v]) if (!vis[w]) { vis[w] = 1; dfs(w, d + 1); vis[w] = 0; } };
  dfs(0, 1); return c / 2n;
}

// a(n) for the single-swap graph. n=1 and n=2 are 0 by inspection rather than by
// the DFS above, which assumes at least three vertices: S_1's graph is a single
// vertex with no edge, S_2's is one edge between two vertices, and neither carries
// a cycle. Stated here so the zeros are a reason, not an omission.
export function permutohedronCycles(n) {
  if (n <= 2) return 0n;
  const { N, adj } = build(n, 'A');
  return count(N, adj);
}

const EXPECTED = {
  a3: 1n, a4: 44n,               // the staged terms the DFS can reach
  b3undirected: 1n,              // sister graph calibration
  b4undirected: 5396n,           // 5396 undirected = 10792 directed = minimus extents
};

function main() {
  let pass = 0, fail = 0;
  const check = (label, got, want) => {
    const ok = got === want;
    ok ? pass++ : fail++;
    console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${label}: ${got}${ok ? '' : `  (expected ${want})`}`);
  };

  console.log('permutohedron (graph A, single adjacent swaps):');
  check('a(1) has no cycle', permutohedronCycles(1), 0n);
  check('a(2) has no cycle', permutohedronCycles(2), 0n);
  check('a(3), the hexagon', permutohedronCycles(3), EXPECTED.a3);
  check('a(4), the truncated octahedron (A343433)', permutohedronCycles(4), EXPECTED.a4);

  console.log('change-ringing (graph B, disjoint adjacent swaps) calibration:');
  const g3 = build(3, 'B');
  check('n=3 undirected', count(g3.N, g3.adj), EXPECTED.b3undirected);
  const g4 = build(4, 'B');
  const b4 = count(g4.N, g4.adj);
  check('n=4 undirected', b4, EXPECTED.b4undirected);
  check('n=4 directed, the minimus extents', b4 * 2n, 10792n);

  console.log(`\n${fail === 0 ? 'PASS' : 'FAIL'} - ${pass}/${pass + fail} checks`);
  process.exit(fail === 0 ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) main();
