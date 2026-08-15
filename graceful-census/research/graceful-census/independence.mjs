// research/graceful-census/independence.mjs
//
// WHY THIS EXISTS (2026-07-20, claude-curious-noether-8b2d41).
//
// fan(12) and helm(7) were first landed with the claim "confirmed two ways":
// the root-label-sharded run (par.sh) and the unsharded run (derive.mjs --write).
// An audit of that claim found it too strong. Both paths call the SAME compiled
// graceful.cpp on the SAME graph emitted by the SAME constructor in graceful.mjs;
// they differ only by the rootLabel shard flag (graceful.cpp:36,43,70). Any bug in
// the recursion, in the pruning, or in the family constructor produces the identical
// wrong number on both. The JS counters that would be genuinely independent are gated
// at v <= 10 (derive.mjs:30, verify.mjs:74), and fan(12) is v=13, helm(7) is v=15 --
// so neither new term was ever checked by a second implementation.
//
// helm(7) has since been confirmed against an outside source: OEIS A387800
// ("fundamentally different graceful labelings of the n-helm", Weisstein 2025)
// publishes a(7) = 12829177, and 28 * 12829177 = 359216956 exactly. That is an
// independent author running independent code, published before we computed ours.
//
// fan(12) has NO such cousin in OEIS (searched 2026-07-20: 39745364 and the
// fundamentally-different candidate 9936341 both return no hits). So this script
// supplies the missing check from inside, by attacking the assumption the two
// original runs shared:
//
//   1. The graph is rebuilt HERE, from the definition, without importing
//      graceful.mjs -- then checked identical to the repo's constructor. This
//      tests the constructor, which the "two ways" never did.
//   2. The vertex numbering is PERMUTED by a seeded, reproducible shuffle before
//      the graph is handed to the counter. The count of graceful labelings is
//      isomorphism-invariant, so the answer must not move -- but the counter's
//      greedy most-constrained vertex order (graceful.cpp:77-85) breaks ties by
//      vertex id, so a permutation sends the search down a genuinely different
//      tree, with different pruning and a different shard decomposition.
//
// A permuted run that returns the same total is therefore evidence about the
// recursion and the constructor, not just about the shard arithmetic.
//
// Usage:
//   node independence.mjs <family> <n> [seed]        # emit permuted graph on stdout
//   node independence.mjs --selftest                 # structural checks, no counting

const FAMILY_SPECS = {
  // Rebuilt from the mathematical definitions, deliberately NOT imported from
  // graceful.mjs. Different construction strategy on purpose: adjacency sets
  // accumulated from stated incidences, rather than an edge list pushed in order.
  fan(n) {
    // F_n = K_1 + P_n : one hub joined to every vertex of a path on n vertices.
    const hub = n;                       // path vertices are 0..n-1
    const adj = Array.from({ length: n + 1 }, () => new Set());
    const join = (a, b) => { adj[a].add(b); adj[b].add(a); };
    for (let i = 0; i + 1 < n; i++) join(i, i + 1);   // the path
    for (let i = 0; i < n; i++) join(i, hub);         // the join
    return { v: n + 1, adj, expect: { v: n + 1, m: 2 * n - 1 } };
  },
  helm(n) {
    // H_n = wheel W_n with a pendant leaf on each rim vertex.
    const hub = n;                       // rim 0..n-1, pendants n+1..2n
    const adj = Array.from({ length: 2 * n + 1 }, () => new Set());
    const join = (a, b) => { adj[a].add(b); adj[b].add(a); };
    for (let i = 0; i < n; i++) {
      join(i, (i + 1) % n);              // the rim cycle
      join(i, hub);                      // the spokes
      join(i, n + 1 + i);                // the pendants
    }
    return { v: 2 * n + 1, adj, expect: { v: 2 * n + 1, m: 3 * n } };
  },
};

function edgesOf({ v, adj }) {
  const e = [];
  for (let a = 0; a < v; a++) for (const b of adj[a]) if (a < b) e.push([a, b]);
  return e.sort((x, y) => x[0] - y[0] || x[1] - y[1]);
}

// Deterministic, seeded shuffle. No Math.random: a check nobody can reproduce
// exactly is not a check. mulberry32 over a stated seed.
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function permutation(v, seed) {
  const p = Array.from({ length: v }, (_, i) => i);
  const rand = rng(seed);
  for (let i = v - 1; i > 0; i--) {           // Fisher-Yates
    const j = Math.floor(rand() * (i + 1));
    [p[i], p[j]] = [p[j], p[i]];
  }
  return p;                                    // p[old] = new
}

// Canonical form of an edge list, for comparing two labelled graphs exactly.
const canon = e => e.map(([a, b]) => (a < b ? [a, b] : [b, a]))
  .sort((x, y) => x[0] - y[0] || x[1] - y[1]).map(x => x.join(',')).join(' ');

function degreeSeq(v, e) {
  const d = new Array(v).fill(0);
  for (const [a, b] of e) { d[a]++; d[b]++; }
  return d.slice().sort((x, y) => x - y);
}

export function buildPermuted(family, n, seed) {
  const spec = FAMILY_SPECS[family];
  if (!spec) throw new Error(`unknown family: ${family}`);
  const g = spec(n);
  const e = edgesOf(g);
  if (g.v !== g.expect.v) throw new Error(`v mismatch: ${g.v} != ${g.expect.v}`);
  if (e.length !== g.expect.m) throw new Error(`m mismatch: ${e.length} != ${g.expect.m}`);
  const p = permutation(g.v, seed);
  const pe = e.map(([a, b]) => [p[a], p[b]]);
  // The permutation must preserve the degree multiset, or the shuffle is broken.
  const before = degreeSeq(g.v, e), after = degreeSeq(g.v, pe);
  if (before.join(',') !== after.join(',')) throw new Error('permutation changed the degree sequence');
  return { v: g.v, e: pe, original: e, perm: p };
}

async function selftest() {
  const { FAMILIES } = await import('./graceful.mjs');
  let pass = 0, fail = 0;
  const ok = (name, cond) => { if (cond) { pass++; console.log(`  ok   ${name}`); } else { fail++; console.log(`  FAIL ${name}`); } };

  console.log('independence.mjs selftest - the rebuilt graphs vs the repo constructors\n');
  for (const [family, ns] of [['fan', [3, 6, 9, 11, 12]], ['helm', [3, 4, 6, 7]]]) {
    for (const n of ns) {
      const mine = buildPermuted(family, n, 1);
      const theirs = FAMILIES[family](n);
      // Same vertex count and edge count.
      ok(`${family}(${n}) v,m agree with graceful.mjs`,
        mine.v === theirs.v && mine.original.length === theirs.e.length);
      // Identical as labelled graphs (the rebuild uses the same vertex naming
      // convention, so this is exact equality, the strongest form of the check).
      ok(`${family}(${n}) edge set identical to graceful.mjs`,
        canon(mine.original) === canon(theirs.e));
      // The permuted copy is isomorphic to the original by construction: applying
      // the inverse permutation must recover the original edge set exactly.
      const inv = new Array(mine.v);
      mine.perm.forEach((newId, oldId) => { inv[newId] = oldId; });
      ok(`${family}(${n}) permuted graph maps back to the original`,
        canon(mine.e.map(([a, b]) => [inv[a], inv[b]])) === canon(mine.original));
      // A permutation that changed nothing would make the whole check vacuous.
      if (mine.v > 3) {
        ok(`${family}(${n}) permutation is non-trivial (traversal really differs)`,
          canon(mine.e) !== canon(mine.original));
      }
    }
  }
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}

const [, , a1, a2, a3] = process.argv;
if (a1 === '--selftest') {
  await selftest();
} else if (a1) {
  const { v, e } = buildPermuted(a1, +a2, a3 === undefined ? 12345 : +a3);
  process.stdout.write(`${v} ${e.length}\n${e.map(([a, b]) => `${a} ${b}`).join('\n')}\n`);
} else {
  console.error('usage: node independence.mjs <family> <n> [seed] | --selftest');
  process.exit(2);
}
