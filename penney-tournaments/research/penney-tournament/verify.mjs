// research/penney-tournament/verify.mjs
// De-risks the Penney-tournament integer sequences staged for OEIS.
//
//   1. CALIBRATION: Conway's closed form and the first-principles Markov solver
//      must agree on EVERY ordered pair's win-probability, for k = 1..6 in full
//      and a random sample at k = 7. (Win-probabilities themselves were already
//      validated three ways in research/penneys-game; this re-proves it for the
//      whole tournament the invariants are read off.)
//   2. The invariants (ties, max out-degree, 3-cycles, distinct probabilities)
//      are recomputed from BOTH engines' relation matrices and must match.
//   3. Structural sanity: antisymmetry, the H<->T complement automorphism, the
//      known k=3 facts, identities among the counts.
//   4. The exact term lists that go into the OEIS b-files are printed.
//
// Run: node research/penney-tournament/verify.mjs

import { patterns, pAfirst_conway, pAfirst_markov, tournament, invariants, Q, ONE, HALF } from './engine.mjs';

let checks = 0, fails = 0;
const ok = (cond, msg) => { checks++; if (!cond) { fails++; console.log('  ✗ ' + msg); } };

// ---------- 1+2. Conway vs Markov on the whole tournament, k = 1..6 ----------
console.log('Calibration — Conway vs first-principles Markov, every ordered pair:');
const KFULL = 6;
const series = { ties: [], maxout: [], nMax: [], cyc3: [], transTri: [], distinctP: [] };
for (let k = 1; k <= KFULL; k++) {
  const S = patterns(k);
  let mism = 0;
  for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++) {
    if (i === j) continue;
    if (!pAfirst_conway(S[i], S[j]).eq(pAfirst_markov(S[i], S[j]))) mism++;
  }
  ok(mism === 0, `k=${k}: ${mism} Conway/Markov probability mismatches`);

  // invariants from each engine, must agree
  const invC = invariants(tournament(k, pAfirst_conway));
  const invM = invariants(tournament(k, pAfirst_markov));
  for (const key of ['ties', 'maxout', 'nMax', 'cyc3', 'transTri', 'distinctP'])
    ok(invC[key] === invM[key], `k=${k}: invariant ${key} disagrees (${invC[key]} vs ${invM[key]})`);

  for (const key of Object.keys(series)) series[key].push(invC[key]);
  console.log(`  k=${k}: pairs ok, ties=${invC.ties} maxout=${invC.maxout} cyc3=${invC.cyc3} ` +
              `transTri=${invC.transTri} distinctP=${invC.distinctP}`);
}

// ---------- 1b. random-sample cross-check at k = 7 ----------
{
  const k = 7, S = patterns(k); let mism = 0, tested = 0;
  const rng = (() => { let x = 123456789 >>> 0; return () => (x = (x * 1103515245 + 12345) >>> 0) / 2 ** 32; })();
  for (let t = 0; t < 250; t++) {
    const A = S[Math.floor(rng() * S.length)], B = S[Math.floor(rng() * S.length)];
    if (A === B) continue; tested++;
    if (!pAfirst_conway(A, B).eq(pAfirst_markov(A, B))) mism++;
  }
  ok(mism === 0, `k=7 sample: ${mism}/${tested} Conway/Markov mismatches`);
  console.log(`  k=7: ${tested} random pairs cross-checked, ${mism} mismatch`);
}

// extend the Conway-only series to k = 9 (Conway is exact by theorem; calibrated above)
for (let k = KFULL + 1; k <= 9; k++) {
  const inv = invariants(tournament(k, pAfirst_conway));
  for (const key of Object.keys(series)) series[key].push(inv[key]);
}

// ---------- 3. structural sanity ----------
console.log('\nStructure:');
// antisymmetry, complement automorphism (swap H<->T relabels the coin, must preserve the tournament)
{
  const k = 5, { S, rel } = tournament(k);
  const comp = (x) => x.replace(/H/g, 'x').replace(/T/g, 'H').replace(/x/g, 'T');
  const idx = new Map(S.map((s, i) => [s, i]));
  let bad = 0;
  for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++) {
    if (rel[i][j] !== -rel[j][i]) bad++;
    if (rel[i][j] !== rel[idx.get(comp(S[i]))][idx.get(comp(S[j]))]) bad++;
  }
  ok(bad === 0, `k=5: ${bad} antisymmetry/complement-automorphism violations`);
  console.log(`  k=5: relation is antisymmetric and H↔T-invariant ✓`);
}
// known k=3 facts (from "Always Bet Second")
{
  ok(pAfirst_conway('THH', 'HHT').eq(new Q(3n, 4n)), 'THH beats HHT should be 3/4');
  ok(pAfirst_conway('THH', 'HHH').eq(new Q(7n, 8n)), 'THH beats HHH should be 7/8');
  ok(pAfirst_conway('HT', 'TH').eq(HALF), 'HT vs TH should tie at k=2');
  console.log('  k=3 spot values match the published Penney odds (3/4, 7/8) ✓');
}
// the famous 4-cycle is genuinely cyclic in the relation
{
  const cyc = ['HHT', 'HTT', 'TTH', 'THH'];   // each beats the next
  let good = true;
  for (let i = 0; i < 4; i++) good = good && pAfirst_conway(cyc[i], cyc[(i + 1) % 4]).cmp(HALF) > 0;
  ok(good, 'the canonical 4-cycle HHT->HTT->TTH->THH->HHT must hold');
  console.log('  the canonical nontransitive 4-cycle holds ✓');
}
// identity: decided triples = C(n,3) - (triples containing >=1 tied pair) ; and cyc3+transTri = decidedTri
{
  const k = 4, t = tournament(k), inv = invariants(t), n = t.n;
  const C3 = (n * (n - 1) * (n - 2)) / 6;
  // count triples with at least one tie directly
  let withTie = 0;
  for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) for (let c = b + 1; c < n; c++)
    if (t.rel[a][b] === 0 || t.rel[b][c] === 0 || t.rel[a][c] === 0) withTie++;
  ok(inv.cyc3 + inv.transTri === C3 - withTie, 'k=4: cyc3+transTri must equal decided triples');
  console.log(`  k=4: cyc3(${inv.cyc3}) + transTri(${inv.transTri}) = decided triples (${C3 - withTie}) ✓`);
}

// ---------- 4. the staged sequences ----------
console.log('\n================  SEQUENCES STAGED FOR OEIS  ================');
const show = (label, arr, off) => console.log(`${label}\n  (offset k=${off})  ${arr.join(', ')}`);
show('A) ties(k)   — # unordered pairs of length-k patterns that tie (p = 1/2):', series.ties, 1);
show('B) cyc3(k)   — # nontransitive (cyclic) triples in the length-k tournament:', series.cyc3, 1);
show('C) maxout(k) — max # of opponents a single length-k pattern beats:', series.maxout, 1);
show('D) transTri(k) — # transitive (acyclic) triples in the length-k tournament:', series.transTri, 1);
show('E) distinctP(k) — # distinct values of p(A,B) over all ordered pairs:', series.distinctP, 1);

console.log(`\n${fails === 0 ? '✓ ALL' : '✗ ' + (checks - fails) + '/'} ${checks} checks ${fails === 0 ? 'PASS' : 'FAIL (' + fails + ' failed)'}`);
process.exit(fails === 0 ? 0 : 1);
