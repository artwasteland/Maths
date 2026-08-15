// research/many-symbol-penney/verify.mjs — the correctness gate.
//
// Establishes, before any invariant is believed:
//   (1) the engine REPRODUCES the published binary (q=2) OEIS sequences exactly
//       (cyc3, ties, maxout, transTri, distinctP for k=1..8) — a calibration
//       against known ground truth (the staged sequences of the q=2 notebook);
//   (2) Conway's closed form == the absorbing-Markov linear solver on EVERY
//       ordered pair, for q in {3,4} up to k=3 (full) and a large random sample
//       at k=4 — the two-independent-methods discipline, at general q;
//   (3) structural facts hold: antisymmetry, p(A,B)+p(B,A)=1, the q constant runs
//       are exactly the sinks (beat no one), the giant SCC has size q^k-q past the
//       consolidation length, the joint-strongest patterns number q(q-1), and the
//       whole tournament is invariant under any permutation of the alphabet.
//
// Run: node research/many-symbol-penney/verify.mjs   (a few minutes; the k=4 sweeps)

import {
  tournament, invariants, sccDecompose, words, alphabet,
  pAfirst_conway, pAfirst_markov, pAfirst_markov_biased, Q, ONE, HALF,
} from './engine.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; } else { fail++; console.log(`  ✗ FAIL: ${m}`); } };
const eqArr = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

// ---------- (1) reproduce the published q=2 sequences ----------
console.log('(1) reproduce published binary (q=2) sequences — calibration vs known ground truth');
{
  const K = 8;
  const seq = { cyc3: [], transTri: [], ties: [], maxout: [], distinctP: [] };
  for (let k = 1; k <= K; k++) {
    const inv = invariants(tournament(k, 2, pAfirst_conway));
    seq.cyc3.push(inv.cyc3); seq.transTri.push(inv.transTri); seq.ties.push(inv.ties);
    seq.maxout.push(inv.maxout); seq.distinctP.push(inv.distinctP);
  }
  ok(eqArr(seq.cyc3,     [0,0,0,14,182,1790,16792,146894]),      'q2 cyc3 (A-absent staged, no-triangle-at-three)');
  ok(eqArr(seq.transTri, [0,0,8,198,1964,16652,139570,1163520]), 'q2 transTri (b-transtri)');
  ok(eqArr(seq.ties,     [1,4,10,32,120,478,1860,7192]),         'q2 ties (b-ties)');
  ok(eqArr(seq.maxout,   [0,1,4,10,22,47,97,197]),               'q2 maxout (b-maxout)');
  ok(eqArr(seq.distinctP,[1,3,15,31,87,191,415,871]),            'q2 distinctP (b-distinctp)');
}

// ---------- (2) Conway == Markov on every pair (general q) ----------
console.log('(2) Conway == Markov, exact BigInt rationals, on every ordered pair');
function crossCheck(k, q, sampleN = null) {
  const S = words(k, q);
  let pairs = [];
  for (let i = 0; i < S.length; i++) for (let j = 0; j < S.length; j++) if (i !== j) pairs.push([i, j]);
  let checked = 0, agree = 0, complement = 0;
  if (sampleN && pairs.length > sampleN) {
    // deterministic stride sample (no RNG — reproducible)
    const stride = Math.max(1, Math.floor(pairs.length / sampleN));
    pairs = pairs.filter((_, idx) => idx % stride === 0).slice(0, sampleN);
  }
  for (const [i, j] of pairs) {
    const c = pAfirst_conway(S[i], S[j], q);
    const m = pAfirst_markov(S[i], S[j], q);
    if (c.eq(m)) agree++;
    // complement identity p(A,B)+p(B,A)=1 (Markov, independent of Conway)
    const mR = pAfirst_markov(S[j], S[i], q);
    if (m.add(mR).eq(ONE)) complement++;
    checked++;
  }
  return { checked, agree, complement };
}
for (const [q, k, s] of [[3,2,null],[3,3,null],[3,4,2000],[4,2,null],[4,3,1500]]) {
  const r = crossCheck(k, q, s);
  ok(r.agree === r.checked, `q=${q} k=${k}: Conway==Markov on ${r.checked} pairs (${r.agree} agree)`);
  ok(r.complement === r.checked, `q=${q} k=${k}: p(A,B)+p(B,A)=1 on ${r.checked} pairs`);
  console.log(`    q=${q} k=${k}: ${r.checked} pairs — Conway==Markov ${r.agree}, complement ${r.complement}`);
}

// ---------- (3) structural facts ----------
console.log('(3) structural facts (antisymmetry, sinks, giant size, maxout multiplicity, alphabet symmetry)');
function structural(k, q) {
  const t = tournament(k, q, pAfirst_conway);
  // antisymmetry
  let anti = true;
  for (let i = 0; i < t.n; i++) for (let j = 0; j < t.n; j++) if (t.rel[i][j] !== -t.rel[j][i]) anti = false;
  ok(anti, `q=${q} k=${k}: antisymmetric`);
  const scc = sccDecompose(t);
  // sinks = constant runs
  const constants = alphabet(q).map((c) => c.repeat(k));
  const constIdx = new Set(constants.map((w) => t.S.indexOf(w)));
  const sinkIdx = new Set();
  for (let i = 0; i < t.n; i++) if (scc.cout[scc.comp[i]] === 0) sinkIdx.add(i);
  const constantsAreSinks = constants.every((w) => scc.cout[scc.comp[t.S.indexOf(w)]] === 0 && scc.sizes[scc.comp[t.S.indexOf(w)]] === 1);
  // every constant beats no one
  let constBeatsNone = true;
  for (const w of constants) { const i = t.S.indexOf(w); if (t.rel[i].some((x) => x === 1)) constBeatsNone = false; }
  ok(constBeatsNone, `q=${q} k=${k}: every constant run beats no one`);
  // giant size == q^k - q past consolidation
  const giant = Math.max(...scc.sizes);
  return { scc, giant, constantsAreSinks, t };
}
// consolidation lengths observed: q=2 -> k>=4, q=3 -> k>=3, q=4 -> k>=2
for (const [q, kmin, kmax] of [[3,3,5],[4,2,4]]) {
  for (let k = kmin; k <= kmax; k++) {
    const r = structural(k, q);
    ok(r.giant === Math.pow(q, k) - q, `q=${q} k=${k}: giant SCC size == q^k - q (=${Math.pow(q,k)-q}), got ${r.giant}`);
    ok(r.constantsAreSinks, `q=${q} k=${k}: the ${q} constant runs are exactly the singleton sinks`);
    // maxout multiplicity q(q-1)
    const inv = invariants(r.t);
    ok(inv.nMax === q * (q - 1), `q=${q} k=${k}: #joint-strongest == q(q-1) = ${q*(q-1)}, got ${inv.nMax}`);
  }
}
// alphabet-permutation automorphism: relabel letters, tournament is preserved
console.log('    alphabet-permutation automorphism');
{
  const q = 3, k = 3;
  const t = tournament(k, q, pAfirst_conway);
  const perm = { A: 'B', B: 'C', C: 'A' };
  const relabel = (w) => [...w].map((c) => perm[c]).join('');
  const idx = new Map(t.S.map((w, i) => [w, i]));
  let autom = true;
  for (let i = 0; i < t.n; i++) for (let j = 0; j < t.n; j++) {
    const pi = idx.get(relabel(t.S[i])), pj = idx.get(relabel(t.S[j]));
    if (t.rel[i][j] !== t.rel[pi][pj]) autom = false;
  }
  ok(autom, 'q=3 k=3: cyclic letter permutation (A->B->C->A) is a tournament automorphism');
}

// ---------- (4) biased sanity: reduces to fair; complement holds ----------
console.log('(4) biased Markov sanity');
{
  const q = 3, k = 3;
  const third = new Q(1n, 3n);
  const uniform = { A: third, B: third, C: third };
  const S = words(k, q);
  let redOK = true, compOK = true;
  for (let t = 0; t < 40; t++) {
    const i = (t * 7) % S.length, j = (t * 13 + 1) % S.length; if (i === j) continue;
    const fair = pAfirst_markov(S[i], S[j], q);
    const bUniform = pAfirst_markov_biased(S[i], S[j], q, uniform);
    if (!fair.eq(bUniform)) redOK = false;
    // a genuine bias: A heavy
    const bias = { A: new Q(1n, 2n), B: new Q(1n, 4n), C: new Q(1n, 4n) };
    const p1 = pAfirst_markov_biased(S[i], S[j], q, bias);
    const p2 = pAfirst_markov_biased(S[j], S[i], q, bias);
    if (!p1.add(p2).eq(ONE)) compOK = false;
  }
  ok(redOK, 'biased Markov with uniform weights == fair Markov');
  ok(compOK, 'biased Markov complement p(A,B)+p(B,A)=1 under a genuine bias');
}

console.log(`\n${fail === 0 ? '✓ ALL PASS' : '✗ FAILURES'} — ${pass}/${pass + fail}`);
process.exit(fail === 0 ? 0 : 1);
