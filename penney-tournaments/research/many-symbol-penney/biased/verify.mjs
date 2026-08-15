// research/many-symbol-penney/biased/verify.mjs — the correctness gate for
// LOAD THE DIE: the length-2, three-symbol Penney tournament under a *biased* die.
//
// The fair engine (../engine.mjs) already proves Conway(base-q) == absorbing-Markov
// on every ordered pair. This gate adds the biased layer and its phase diagram:
//
//   (1) BIASED CONWAY == BIASED MARKOV on EVERY ordered pair of the nine 2-letter
//       words, over many rational bias points (including doubled-letter words like
//       AA/CC) — the two-independent-methods discipline, carried to arbitrary bias.
//       The biased-Conway odds use the generalized (Guibas-Odlyzko) correlation with
//       1/P(overlap) weights; the Markov solver is first-principles. They must agree.
//   (2) THE EXACT SURVIVAL INEQUALITIES for the two fair triangles hold on every
//       grid point (6486 edge-decisions), matched against the Markov engine:
//         T1 = AB->BC->CA survives  iff  a>c(1-a),  b>a(1-b),  c>b(1-c)
//         T2 = AC->CB->BA survives  iff  a>b(1-a),  c>a(1-c),  b>c(1-b)
//   (3) THE REVERSAL THEOREM, both as a symbolic identity and a dense-grid backstop:
//       no biased die can reverse a triangle. The three reversal inequalities sum to
//       1 < 1 - (ab+bc+ca), impossible for positive probabilities. 0 grid points.
//   (4) MEASURED PHASE FRACTIONS on a fine grid, pinned so the in-browser page can
//       self-check against them: both triangles ~2.38%, some cycle ~65.7%, a best
//       (unbeatable) word ~44.1%; the best word, when it exists, is ALWAYS a doubled
//       letter (checked exhaustively on the grid); on the symmetric line a=b the
//       doubled letter CC becomes unbeatable at exactly c = 1/2 (an exact tie there).
//
// Run: node research/many-symbol-penney/biased/verify.mjs   (~1 min)

import {
  pAfirst_markov_biased, sccDecompose, words, Q, HALF, ONE,
} from '../engine.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; } else { fail++; console.log(`  ✗ FAIL: ${m}`); } };
const one = ONE;

// ---------- the biased-Conway odds via 1/P(overlap)-weighted correlation ----------
function corrBiased(X, Y, prob) {
  const L = X.length; let s = new Q(0n);
  for (let j = 1; j <= L; j++) {
    if (X.slice(-j) === Y.slice(0, j)) {
      let w = one;
      for (const ch of X.slice(-j)) w = w.div(prob[ch]);
      s = s.add(w);
    }
  }
  return s;
}
function pAfirst_conway_biased(X, Y, prob) {
  const AA = corrBiased(X, X, prob), AB = corrBiased(X, Y, prob);
  const BA = corrBiased(Y, X, prob), BB = corrBiased(Y, Y, prob);
  const num = BB.sub(BA), den = AA.sub(AB);   // odds (X first):(Y first)
  return num.div(num.add(den));
}
const S9 = words(2, 3);                         // all nine 2-letter words over {A,B,C}
const bias = (a, b, c) => {
  const t = BigInt(a + b + c);
  return { A: new Q(BigInt(a), t), B: new Q(BigInt(b), t), C: new Q(BigInt(c), t) };
};

// ---------- (1) biased Conway == biased Markov on every ordered pair ----------
console.log('(1) biased Conway == biased Markov, all nine words, many biases');
{
  const pts = [[1, 1, 1], [2, 1, 1], [1, 2, 1], [1, 1, 2], [5, 3, 2], [1, 1, 8],
    [3, 3, 4], [7, 2, 1], [1, 4, 5], [9, 5, 1], [2, 7, 3], [4, 1, 10], [11, 13, 17], [1, 1, 50]];
  let checks = 0, mism = 0;
  for (const [a, b, c] of pts) {
    const prob = bias(a, b, c);
    for (const X of S9) for (const Y of S9) if (X !== Y) {
      const pm = pAfirst_markov_biased(X, Y, 3, prob);
      const pc = pAfirst_conway_biased(X, Y, prob);
      checks++;
      if (!pm.eq(pc)) mism++;
      // complement identity, biased: p(X,Y) + p(Y,X) = 1
      const back = pAfirst_markov_biased(Y, X, 3, prob);
      if (!pm.add(back).eq(one)) mism++;
    }
  }
  ok(mism === 0, `biased two-method + complement agree on all ${checks} ordered pairs`);
  console.log(`    ${checks} ordered pairs x ${pts.length} biases, 0 disagreements`);
}

// ---------- exact survival predicates (the claim) ----------
// T1 = AB->BC->CA ; T2 = AC->CB->BA (the two fair triangles)
const gt = (x, y) => x.cmp(y) > 0;
const survT1 = (a, b, c) => gt(a, c.mul(one.sub(a))) && gt(b, a.mul(one.sub(b))) && gt(c, b.mul(one.sub(c)));
const survT2 = (a, b, c) => gt(a, b.mul(one.sub(a))) && gt(c, a.mul(one.sub(c))) && gt(b, c.mul(one.sub(b)));
const T1edges = [['AB', 'BC'], ['BC', 'CA'], ['CA', 'AB']];
const T2edges = [['AC', 'CB'], ['CB', 'BA'], ['BA', 'AC']];
const engineDirs = (edges, prob) => edges.map(([X, Y]) => pAfirst_markov_biased(X, Y, 3, prob).cmp(HALF) === 1);

// ---------- (2) the exact inequalities match the engine, everywhere ----------
console.log('(2) exact survival inequalities == engine edge-decisions, whole grid');
{
  const N = 48; let mism = 0, edgeChecks = 0;
  for (let a = 1; a < N; a++) for (let b = 1; b < N - a; b++) {
    const c = N - a - b; if (c < 1) continue;
    const t = BigInt(N);
    const A = new Q(BigInt(a), t), B = new Q(BigInt(b), t), C = new Q(BigInt(c), t);
    const prob = { A, B, C };
    const c1 = [gt(A, C.mul(one.sub(A))), gt(B, A.mul(one.sub(B))), gt(C, B.mul(one.sub(C)))];
    const c2 = [gt(A, B.mul(one.sub(A))), gt(C, A.mul(one.sub(C))), gt(B, C.mul(one.sub(B)))];
    const e1 = engineDirs(T1edges, prob), e2 = engineDirs(T2edges, prob);
    for (let i = 0; i < 3; i++) { edgeChecks += 2; if (c1[i] !== e1[i]) mism++; if (c2[i] !== e2[i]) mism++; }
  }
  ok(mism === 0, `predicate/engine disagreements: ${mism}`);
  console.log(`    ${edgeChecks} edge-decisions on the N=${N} grid, 0 disagreements`);
}

// ---------- (3) the reversal theorem ----------
console.log('(3) no biased die reverses a triangle');
{
  // symbolic backstop: reversal of T1 needs a<c(1-a), b<a(1-b), c<b(1-c);
  // summing gives 1 < 1 - (ab+bc+ca). We check the summed identity on many points:
  const revT1 = (a, b, c) => a.cmp(c.mul(one.sub(a))) < 0 && b.cmp(a.mul(one.sub(b))) < 0 && c.cmp(b.mul(one.sub(c))) < 0;
  const revT2 = (a, b, c) => a.cmp(b.mul(one.sub(a))) < 0 && c.cmp(a.mul(one.sub(c))) < 0 && b.cmp(c.mul(one.sub(b))) < 0;
  const N = 240; let rev = 0, sumViol = 0;
  for (let a = 1; a < N; a++) for (let b = 1; b < N - a; b++) {
    const c = N - a - b; if (c < 1) continue;
    const t = BigInt(N);
    const A = new Q(BigInt(a), t), B = new Q(BigInt(b), t), C = new Q(BigInt(c), t);
    if (revT1(A, B, C) || revT2(A, B, C)) rev++;
    // the sum-of-three-reversal-LHS - sum-of-RHS must be strictly positive (identity ab+bc+ca)
    const lhsMinusRhs = A.add(B).add(C).sub(C.mul(one.sub(A)).add(A.mul(one.sub(B))).add(B.mul(one.sub(C))));
    const abbcca = A.mul(B).add(B.mul(C)).add(C.mul(A));
    if (!lhsMinusRhs.eq(abbcca)) sumViol++;   // identity: sum(x) - sum(x(1-next)) == ab+bc+ca
  }
  ok(rev === 0, `reversed-triangle grid points found: ${rev}`);
  ok(sumViol === 0, `algebraic identity sum(x)-sum(x*(1-x_next)) == ab+bc+ca held (${sumViol} violations)`);
  console.log(`    the three reversal inequalities sum to 1 < 1-(ab+bc+ca) -> impossible; 0 of ${'~'}grid points reverse`);
}

// ---------- full biased tournament helper ----------
function biasTournament(prob) {
  const n = S9.length;
  const rel = Array.from({ length: n }, () => new Array(n).fill(0));
  const out = new Array(n).fill(0);
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const c = pAfirst_markov_biased(S9[i], S9[j], 3, prob).cmp(HALF);
    rel[i][j] = c; rel[j][i] = -c;
    if (c > 0) out[i]++; else if (c < 0) out[j]++;
  }
  return { S: S9, n, rel, out };
}

// ---------- (4) fine-grid phase fractions, pinned for the page's self-check ----------
console.log('(4) fine-grid phase fractions (the numbers the page self-checks against)');
{
  const N = 120; let tot = 0, both = 0, either = 0, cyc = 0, best = 0;
  const bestWords = new Set();
  let bestAlwaysDoubled = true;
  for (let a = 1; a < N; a++) for (let b = 1; b < N - a; b++) {
    const c = N - a - b; if (c < 1) continue;
    const t = BigInt(N);
    const A = new Q(BigInt(a), t), B = new Q(BigInt(b), t), C = new Q(BigInt(c), t);
    const s1 = survT1(A, B, C), s2 = survT2(A, B, C);
    tot++; if (s1 && s2) both++; if (s1 || s2) either++;
    const T = biasTournament({ A, B, C });
    if (Math.max(...sccDecompose(T).sizes) > 1) cyc++;
    const winners = T.S.filter((_, i) => T.out[i] === 8);
    if (winners.length) { best++; for (const w of winners) { bestWords.add(w); if (w[0] !== w[1]) bestAlwaysDoubled = false; } }
  }
  const frac = (x) => (100 * x / tot);
  const near = (x, y, tol) => Math.abs(x - y) < tol;
  console.log(`    grid ${tot} pts | both=${frac(both).toFixed(2)}% either=${frac(either).toFixed(2)}% cycle=${frac(cyc).toFixed(2)}% best=${frac(best).toFixed(2)}%`);
  ok(near(frac(both), 2.38, 0.6), `both fair triangles ~2.4% (got ${frac(both).toFixed(2)}%)`);
  ok(near(frac(cyc), 65.7, 1.5), `some directed cycle ~65.7% (got ${frac(cyc).toFixed(2)}%)`);
  ok(near(frac(best), 44.1, 1.5), `a best word exists ~44.1% (got ${frac(best).toFixed(2)}%)`);
  ok(bestAlwaysDoubled, 'the unbeatable word, when it exists, is always a doubled letter');
  ok([...bestWords].every((w) => ['AA', 'BB', 'CC'].includes(w)), `best words seen: {${[...bestWords].sort().join(',')}}`);
}

// ---------- (5) the exact symmetric-line threshold: CC unbeatable iff c > 1/2 ----------
console.log('(5) on a=b, CC becomes unbeatable exactly at c = 1/2 (an exact tie)');
{
  // at (1/4,1/4,1/2): CC vs AC and CC vs BC are exact ties (1/2); all other CC edges > 1/2
  const prob = { A: new Q(1n, 4n), B: new Q(1n, 4n), C: new Q(1n, 2n) };
  const edges = S9.filter((w) => w !== 'CC').map((X) => [X, pAfirst_markov_biased('CC', X, 3, prob)]);
  const ties = edges.filter(([, p]) => p.eq(HALF)).map(([w]) => w).sort();
  const strictWins = edges.filter(([X]) => !['AC', 'BC'].includes(X)).every(([, p]) => p.cmp(HALF) > 0);
  ok(ties.length === 2 && ties[0] === 'AC' && ties[1] === 'BC', `exactly CC~AC and CC~BC tie at c=1/2 (got {${ties.join(',')}})`);
  ok(strictWins, 'every other CC edge is a strict win at c=1/2 (so CC is unbeatable the instant c>1/2)');
  // just below and above: c=0.49 -> not unbeatable; c=0.51 -> unbeatable
  const beatsAll = (cn, cd) => {
    const c = new Q(BigInt(cn), BigInt(cd)); const rest = one.sub(c).div(new Q(2n));
    const p = { A: rest, B: rest, C: c };
    return S9.filter((w) => w !== 'CC').every((X) => pAfirst_markov_biased('CC', X, 3, p).cmp(HALF) === 1);
  };
  ok(!beatsAll(49, 100) && beatsAll(51, 100), 'CC unbeatable at c=0.51, not at c=0.49');
}

console.log(`\n${fail === 0 ? '✓' : '✗'} biased gate: ${pass}/${pass + fail} passed`);
process.exit(fail === 0 ? 0 : 1);
