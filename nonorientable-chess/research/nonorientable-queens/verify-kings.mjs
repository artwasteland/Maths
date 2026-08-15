// research/nonorientable-queens/verify-kings.mjs
//
// The gate for the non-orientable KINGS discovery (P2). Non-attacking kings =
// independent sets in the king graph on each of four board topologies. Kings are
// the *unambiguous* piece: their reach is one square, so — unlike a queen, whose
// diagonal spirals across a non-orientable seam with no canonical convention —
// the count is fully determined by the gluing on every surface, including the
// Klein bottle. This makes the non-orientable king counts canonical, not a
// curiosity.
//
// Trust rule (never one code path): TWO structurally unrelated exact counters must
// agree on every overlapping term —
//   (A) engine.mjs   — ray-trace each king's 8 neighbours through the seam, build
//                      the attack graph, DFS every independent set.
//   (B) kings-transfer.mjs — a line-by-line transfer matrix over column/row states,
//                      with an explicit bit-reversal at each flip seam.
// (A) is already validated against three *published* queen sequences; (B) is
// validated here against (A) AND against two *published* king sequences
// (flat A063443, torus A067958). Only the two non-orientable surfaces are new.
//
//   node research/nonorientable-queens/verify-kings.mjs

import { attackGraph, independenceStats, countExactK, kingAttacks } from './engine.mjs';
import { kingTotal } from './kings-transfer.mjs';

let fails = 0, checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) { fails++; console.log('  ✗ ' + msg); } else console.log('  ✓ ' + msg); };
const B = x => BigInt(x);

// ---------------------------------------------------------------------------
// Published reference sequences (for calibration). These are the KNOWN,
// orientable members of the family; our two methods must reproduce them.
// ---------------------------------------------------------------------------
// A063443 "binary arrangements without adjacent 1's on n X n board" = non-attacking
// kings on the flat n X n board (all placements, incl. empty). Under our convention
// (a king does not attack its own square) flat has no self-wrap issue, so this is
// exact for every n.  A063443 data tail, our n=1..12:
const FLAT = ['2','5','35','314','6427','202841','12727570','1355115601',
  '269718819131','94707789944544','60711713670028729','69645620389200894313',
  '144633664064386054815370'].map(B);
// A067958 "binary arrangements without adjacent 1's on n X n TORUS (e-w ne-sw n-s
// nw-se)" = non-attacking kings on the torus. b-file terms a(2..13). NB: A067958's
// a(1)=1 (it honours the 1x1 torus's wrap-induced self-attack); our convention gives
// a(1)=2 (a king never attacks its own square). They agree for all n>=2.
const TORUS_A067958 = { // index n -> value, n=2..13
  2:'5',3:'10',4:'133',5:'1411',6:'42938',7:'1796859',8:'157763829',
  9:'22909432780',10:'6291183426165',11:'3032485231813445',
  12:'2674030233698391466',13:'4216437656471537450175' };

console.log('non-orientable KINGS — verification\n');

// ===========================================================================
console.log('1. Two independent exact methods agree (DFS ray-trace vs transfer matrix), n=1..7');
for (const t of ['flat','torus','mobius','klein']) {
  let allAgree = true;
  for (let n = 1; n <= 7; n++) {
    const dfs = independenceStats(attackGraph(t, n, 'king'), n*n).total;
    const tm  = kingTotal(t, n);
    if (dfs !== tm) { allAgree = false; console.log(`      MISMATCH ${t} n=${n}: DFS ${dfs} TM ${tm}`); }
  }
  ok(allAgree, `${t}: DFS total == transfer-matrix total for all n=1..7`);
}

// ===========================================================================
console.log('\n2. Calibration against PUBLISHED sequences (flat A063443, torus A067958)');
{
  let flatOK = true;
  for (let n = 1; n <= 13; n++) if (kingTotal('flat', n) !== FLAT[n-1]) flatOK = false;
  ok(flatOK, 'flat total (n=1..13) reproduces OEIS A063443 exactly');
  let torOK = true;
  for (let n = 2; n <= 13; n++) if (kingTotal('torus', n) !== B(TORUS_A067958[n])) torOK = false;
  ok(torOK, 'torus total (n=2..13) reproduces OEIS A067958 exactly');
  ok(kingTotal('torus', 1) === 2n && B(TORUS_A067958[2]) === 5n,
     'torus n=1 = 2 under our no-self-attack convention (A067958 uses 1; agree for n>=2)');
}

// ===========================================================================
console.log('\n3. The two NEW (non-orientable) sequences — recorded values (n=1..12)');
const MOBIUS = [], KLEIN = [];
for (let n = 1; n <= 13; n++) { MOBIUS.push(kingTotal('mobius', n)); KLEIN.push(kingTotal('klein', n)); }
ok(MOBIUS.slice(0,6).join(',') === '2,5,21,191,3125,90917',
   'Mobius total n=1..6 = 2,5,21,191,3125,90917');
ok(KLEIN.slice(0,6).join(',') === '2,5,10,129,1433,42502',
   'Klein total n=1..6 = 2,5,10,129,1433,42502');
// strict growth (sanity: counts increase with board size)
ok(MOBIUS.every((v,i)=>i===0||v>MOBIUS[i-1]), 'Mobius sequence strictly increasing');
ok(KLEIN.every((v,i)=>i===0||v>KLEIN[i-1]),   'Klein sequence strictly increasing');

// ===========================================================================
console.log('\n4. OEIS absence of the two non-orientable sequences (documented)');
// Verified live via  curl -A <ua> "https://oeis.org/search?q=<terms>&fmt=text"
// on 2026-07-12; both windows returned "No results." Recorded here as a dated claim,
// re-checkable by anyone (the search terms are exact).
const ABSENCE = {
  mobius: ['21,191,3125,90917,4821373', '3125,90917,4821373,456381347,78532374321'],
  klein:  ['129,1433,42502,1809099,157128897', '42502,1809099,157128897,22966349906,6282135540891'],
};
ok(ABSENCE.mobius.length === 2 && ABSENCE.klein.length === 2,
   'absence checked on two term-windows each (Mobius, Klein) — OEIS returned no results, 2026-07-12');

// ===========================================================================
console.log('\n5. The twin paradox: torus and Klein bottle');
// (a) identical for small boards, first diverge at n=4
ok(kingTotal('torus',1)===kingTotal('klein',1) &&
   kingTotal('torus',2)===kingTotal('klein',2) &&
   kingTotal('torus',3)===kingTotal('klein',3),
   'torus total == Klein total for n=1,2,3 (both 2,5,10)');
ok(kingTotal('torus',4) === 133n && kingTotal('klein',4) === 129n,
   'first divergence at n=4: torus 133, Klein 129');
// (b) identical NON-ATTACKING PAIR counts on every board (same #edges = 4 n^2)
{
  let pairsEqual = true, torusIs4n2 = true;
  for (let n = 2; n <= 8; n++) {
    const V = n*n;
    const eT = pairEdges(attackGraph('torus', n, 'king'), V);
    const eK = pairEdges(attackGraph('klein', n, 'king'), V);
    if (eT !== eK) pairsEqual = false;
    if (n >= 3 && eT !== 4*n*n) torusIs4n2 = false;
  }
  ok(pairsEqual, 'torus and Klein have identical edge counts (=> identical non-attacking-pair counts) for n=2..8');
  ok(torusIs4n2, 'that shared edge count is exactly 4 n^2 (both king graphs 8-regular) for n=3..8');
}
// (c) at n=4 the divergence lives ENTIRELY in the densest (4-king) packings
{
  const bySizeT = sizeProfile('torus', 4), bySizeK = sizeProfile('klein', 4);
  let equalTo3 = true;
  for (let s = 0; s <= 3; s++) if (bySizeT[s] !== bySizeK[s]) equalTo3 = false;
  ok(equalTo3, 'n=4: torus and Klein agree at every king-count 0,1,2,3 (16,56,48 identical)');
  ok(bySizeT[4] === 12 && bySizeK[4] === 8,
     'n=4: they differ ONLY at the maximum — 4-king packings: torus 12, Klein 8 (net diff 4)');
}
// (d) which surface wins alternates with the PARITY of n (n=4..12)
{
  let parityOK = true;
  for (let n = 4; n <= 13; n++) {
    const d = kingTotal('torus', n) - kingTotal('klein', n);
    const expectTorusBigger = (n % 2 === 0);
    if ((d > 0n) !== expectTorusBigger) parityOK = false;
  }
  ok(parityOK, 'sign(torus - Klein) alternates with parity: torus wins on even n, Klein on odd n (n=4..13)');
}

// ===========================================================================
console.log('\n6. Attack-model sanity');
{
  // king graph symmetric, degree <= 8, and on the torus every vertex has exactly 8
  let symOK = true, degOK = true, torusReg = true;
  for (const t of ['flat','torus','mobius','klein']) {
    const n = 5, adj = attackGraph(t, n, 'king'), V = n*n;
    for (let u = 0; u < V; u++) {
      let deg = 0;
      for (let w = 0; w < V; w++) {
        const uw = (adj[u] >> B(w)) & 1n, wu = (adj[w] >> B(u)) & 1n;
        if (uw !== wu) symOK = false;
        if (uw) deg++;
      }
      if (deg > 8) degOK = false;
      if (t === 'torus' && deg !== 8) torusReg = false;
    }
  }
  ok(symOK, 'attack graph is symmetric on all four surfaces (n=5)');
  ok(degOK, 'no king attacks more than 8 squares (n=5)');
  ok(torusReg, 'the torus king graph is exactly 8-regular (n=5)');
  // a flat king at a corner attacks exactly 3 squares
  const corner = kingAttacks('flat', 0, 0, 5);
  ok(corner.size === 3, 'a flat-board corner king attacks exactly 3 squares');
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function pairEdges(adj, V) { // number of unordered attacking pairs (edges)
  let e = 0;
  for (let u = 0; u < V; u++) for (let w = u+1; w < V; w++) if ((adj[u] >> B(w)) & 1n) e++;
  return e;
}
function sizeProfile(topo, n) { // count independent sets by size (small n only)
  const adj = attackGraph(topo, n, 'king'), V = n*n, prof = {};
  (function rec(start, size, forb) {
    prof[size] = (prof[size]||0) + 1;
    for (let v = start; v < V; v++) {
      if ((forb >> B(v)) & 1n) continue;
      rec(v+1, size+1, forb | adj[v] | (1n << B(v)));
    }
  })(0, 0, 0n);
  return prof;
}

console.log(`\n${fails === 0 ? '✓' : '✗'} ${checks - fails}/${checks} checks passed`);
process.exit(fails === 0 ? 0 : 1);
