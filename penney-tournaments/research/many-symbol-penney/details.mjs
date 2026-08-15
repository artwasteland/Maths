import { tournament, words, pAfirst_conway, pAfirst_markov, sccDecompose, invariants, alphabet, ONE, HALF } from './engine.mjs';

// --- the explicit ternary length-2 triangles ---
console.log('=== ternary (q=3) length-2 directed triangles ===');
{
  const k = 2, q = 3;
  const t = tournament(k, q);
  const tris = [];
  for (let a = 0; a < t.n; a++) for (let b = 0; b < t.n; b++) for (let c = 0; c < t.n; c++) {
    if (a < b && b < c) {
      // check the 6 orientations for a directed 3-cycle among {a,b,c}
      const edge = (x, y) => t.rel[x][y] === 1;
      const cyc = (x, y, z) => edge(x, y) && edge(y, z) && edge(z, x);
      if (cyc(a, b, c)) tris.push([a, b, c]);
      else if (cyc(a, c, b)) tris.push([a, c, b]);
    }
  }
  console.log(`  found ${tris.length} directed triangles (each listed once, in cycle order):`);
  for (const [a, b, c] of tris) {
    const p1 = pAfirst_conway(t.S[a], t.S[b], q), p2 = pAfirst_conway(t.S[b], t.S[c], q), p3 = pAfirst_conway(t.S[c], t.S[a], q);
    console.log(`    ${t.S[a]} -> ${t.S[b]} -> ${t.S[c]} -> ${t.S[a]}   (odds ${p1.s}, ${p2.s}, ${p3.s})`);
  }
}

// --- a worked win-probability: does BA beat AA? etc. show full pair table at k=2,q=3 ---
console.log('\n=== q=3 k=2 full relation (row beats column: > . < , tie 0) ===');
{
  const t = tournament(2, 3);
  const hdr = '     ' + t.S.map(s => s.padStart(3)).join(' ');
  console.log(hdr);
  for (let i = 0; i < t.n; i++) {
    const row = t.S.map((_, j) => i === j ? ' · ' : (t.rel[i][j] === 1 ? ' > ' : t.rel[i][j] === -1 ? ' < ' : ' = ')).join(' ');
    console.log(`  ${t.S[i]}  ${row}`);
  }
}

// --- consolidation length by q (when does the giant reach q^k - q?) ---
console.log('\n=== consolidation length: smallest k where giant SCC == q^k - q ===');
for (const q of [2, 3, 4, 5]) {
  const kmax = q === 2 ? 6 : q === 3 ? 5 : q === 4 ? 4 : 3;
  let cons = null;
  const line = [];
  for (let k = 1; k <= kmax; k++) {
    const t = tournament(k, q);
    const scc = sccDecompose(t);
    const giant = Math.max(...scc.sizes);
    const target = Math.pow(q, k) - q;
    const isCons = giant === target && scc.nc === q + 1;
    line.push(`k${k}:${giant}${isCons ? '*' : ''}`);
    if (isCons && cons === null) cons = k;
  }
  console.log(`  q=${q}: consolidates at k=${cons}   [${line.join('  ')}]  (target q^k-q; * = giant==q^k-q AND nc==q+1)`);
}

// --- a clean worked example for the page: a 3-cycle with exact odds & a strategy line ---
console.log('\n=== worked example: the ternary length-2 loop, exact odds ===');
{
  const q = 3, t = tournament(2, q);
  // pick the triangle to feature; recompute both engines to show agreement
  const show = (X, Y) => {
    const c = pAfirst_conway(X, Y, q), m = pAfirst_markov(X, Y, q);
    console.log(`  P(${X} before ${Y}) = ${c.s}  [Conway]  = ${m.s}  [Markov]  ${c.eq(m) ? 'AGREE' : 'DISAGREE'}`);
  };
  show('AB','BB'); show('AB','BC'); show('BC','CA');
}
