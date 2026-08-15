// research/many-symbol-penney/discover.mjs — the discovery run.
// Computes the q-ary Penney tournament invariants and structure, and prints them.
// Validation (Conway == Markov) lives in verify.mjs; this is the exploration.
import { tournament, invariants, sccDecompose, words, pAfirst_conway, pAfirst_markov, alphabet } from './engine.mjs';

function analyze(k, q) {
  const t = tournament(k, q, pAfirst_conway);
  const inv = invariants(t);
  const scc = sccDecompose(t);
  // sinks: components with cout === 0; sources: cin === 0
  const sinkComps = []; const sourceComps = [];
  for (let c = 0; c < scc.nc; c++) { if (scc.cout[c] === 0) sinkComps.push(c); if (scc.cin[c] === 0) sourceComps.push(c); }
  const sizeHist = {};
  for (const s of scc.sizes) sizeHist[s] = (sizeHist[s] || 0) + 1;
  // which words are singleton sinks?
  const sinkWords = [];
  for (let i = 0; i < t.n; i++) if (sinkComps.includes(scc.comp[i]) && scc.sizes[scc.comp[i]] === 1) sinkWords.push(t.S[i]);
  const giant = Math.max(...scc.sizes);
  return { k, q, n: t.n, inv, nc: scc.nc, giant, sizeHist, nSinks: sinkComps.length, nSources: sourceComps.length, sinkWords };
}

for (const q of [2, 3, 4]) {
  console.log(`\n================= q = ${q} (alphabet ${alphabet(q).join('')}) =================`);
  const KMAX = q === 2 ? 8 : q === 3 ? 6 : 4;
  const seqs = { n: [], cyc3: [], transTri: [], ties: [], maxout: [], nMax: [], distinctP: [], nc: [], giant: [], nSinks: [] };
  for (let k = 1; k <= KMAX; k++) {
    const r = analyze(k, q);
    seqs.n.push(r.n); seqs.cyc3.push(r.inv.cyc3); seqs.transTri.push(r.inv.transTri);
    seqs.ties.push(r.inv.ties); seqs.maxout.push(r.inv.maxout); seqs.nMax.push(r.inv.nMax);
    seqs.distinctP.push(r.inv.distinctP); seqs.nc.push(r.nc); seqs.giant.push(r.giant); seqs.nSinks.push(r.nSinks);
    const qkMinusQ = r.n - q;
    console.log(
      `k=${k}: n=${r.n}  cyc3=${r.inv.cyc3}  transTri=${r.inv.transTri}  ties=${r.inv.ties}  ` +
      `maxout=${r.inv.maxout}(x${r.inv.nMax})  distinctP=${r.inv.distinctP}  ` +
      `| SCC: nc=${r.nc} giant=${r.giant} sinks=${r.nSinks} sources=${r.nSources} ` +
      `giant==q^k-q? ${r.giant === qkMinusQ}  sinkWords=[${r.sinkWords.join(',')}]  sizes=${JSON.stringify(r.sizeHist)}`
    );
  }
  console.log(`\n  -- sequences (k=1..${KMAX}) for q=${q} --`);
  for (const [name, arr] of Object.entries(seqs)) console.log(`    ${name.padEnd(10)}: ${arr.join(', ')}`);
}
