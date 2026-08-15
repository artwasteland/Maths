// Extend the sequences: q=3 to k=7 (all), q=4 to k=6 (cheap invariants; cyc3/transTri
// only where the O(n^3) triple census is affordable). Prints term lists for the b-files.
import { tournament, invariants, sccDecompose } from './engine.mjs';

function cheap(k, q) {
  // ties, maxout, nMax, distinctP, SCC structure — no O(n^3) triple census
  const t = tournament(k, q);
  const { n, rel, probs } = t;
  let ties = 0;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (rel[i][j] === 0) ties++;
  const out = rel.map((r) => r.filter((x) => x === 1).length);
  const maxout = n > 1 ? Math.max(...out) : 0;
  const nMax = out.filter((x) => x === maxout).length;
  const scc = sccDecompose(t);
  const giant = Math.max(...scc.sizes);
  return { n, ties, maxout, nMax, distinctP: probs.size, nc: scc.nc, giant };
}

for (const [q, kFull, kCheap] of [[3, 7, 7], [4, 5, 6]]) {
  console.log(`\n===== q=${q} =====`);
  const seq = { cyc3: [], transTri: [], ties: [], maxout: [], nMax: [], distinctP: [], giant: [], nc: [] };
  for (let k = 1; k <= kCheap; k++) {
    const c = cheap(k, q);
    seq.ties.push(c.ties); seq.maxout.push(c.maxout); seq.nMax.push(c.nMax);
    seq.distinctP.push(c.distinctP); seq.giant.push(c.giant); seq.nc.push(c.nc);
    let cyc = '-', tri = '-';
    if (k <= kFull) {
      const inv = invariants(tournament(k, q));
      seq.cyc3.push(inv.cyc3); seq.transTri.push(inv.transTri);
      cyc = inv.cyc3; tri = inv.transTri;
    }
    console.log(`  k=${k}: n=${c.n} cyc3=${cyc} transTri=${tri} ties=${c.ties} maxout=${c.maxout}(x${c.nMax}) distinctP=${c.distinctP} giant=${c.giant} nc=${c.nc}`);
  }
  console.log(`  cyc3     : ${seq.cyc3.join(', ')}`);
  console.log(`  transTri : ${seq.transTri.join(', ')}`);
  console.log(`  ties     : ${seq.ties.join(', ')}`);
  console.log(`  maxout   : ${seq.maxout.join(', ')}`);
  console.log(`  distinctP: ${seq.distinctP.join(', ')}`);
  console.log(`  giant    : ${seq.giant.join(', ')}`);
}
