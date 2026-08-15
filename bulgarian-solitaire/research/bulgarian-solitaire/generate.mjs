// Generate the full dataset + b-files for the Bulgarian-solitaire program.
import { partitions, move } from './engine.mjs';
import { writeFileSync } from 'fs';

function full(n) {
  const parts = partitions(n), N = parts.length, idx = new Map();
  parts.forEach((p, i) => idx.set(p.join(','), i));
  const next = parts.map(p => idx.get(move(p).join(',')));
  const stt = new Uint8Array(N), cyc = new Uint8Array(N);
  for (let s = 0; s < N; s++) { if (stt[s]) continue; const pa = []; let u = s; while (stt[u] === 0) { stt[u] = 1; pa.push(u); u = next[u]; } if (stt[u] === 1) { let v = u; do { cyc[v] = 1; v = next[v]; } while (v !== u); } for (const w of pa) stt[w] = 2; }
  const indeg = new Int32Array(N); for (const j of next) indeg[j]++;
  const goe = indeg.reduce((s, d) => s + (d === 0 ? 1 : 0), 0);
  const seen = new Uint8Array(N), lens = [];
  for (let s = 0; s < N; s++) if (cyc[s] && !seen[s]) { let L = 0, v = s; do { seen[v] = 1; L++; v = next[v]; } while (v !== s); lens.push(L); }
  const numCycles = lens.length, fixed = lens.filter(l => l === 1).length, longest = lens.length ? Math.max(...lens) : 0;
  const recurrent = cyc.reduce((s, c) => s + c, 0);
  const rev = Array.from({ length: N }, () => []); next.forEach((j, i) => rev[j].push(i));
  const dist = new Int32Array(N).fill(-1), q = []; for (let i = 0; i < N; i++) if (cyc[i]) { dist[i] = 0; q.push(i); }
  for (let h = 0; h < q.length; h++) { const u = q[h]; for (const w of rev[u]) if (dist[w] < 0) { dist[w] = dist[u] + 1; q.push(w); } }
  let maxTail = 0, S = 0; for (let i = 0; i < N; i++) { if (dist[i] > maxTail) maxTail = dist[i]; S += dist[i]; }
  let maxTailCount = 0; for (let i = 0; i < N; i++) if (dist[i] === maxTail) maxTailCount++;
  return { n, parts: N, fixed, numCycles, recurrent, goe, longest, maxTail, maxTailCount, totalSettle: S };
}

const NMAX = +process.argv[2] || 55;
const rows = [];
for (let n = 1; n <= NMAX; n++) { rows.push(full(n)); process.stderr.write(`\r n=${n}`); }
process.stderr.write('\n');
writeFileSync('research/bulgarian-solitaire/data.json', JSON.stringify(rows, null, 0) + '\n');

// b-files (offset 1)
const bfile = (rows, key) => rows.map(r => `${r.n} ${r[key]}`).join('\n') + '\n';
writeFileSync('research/bulgarian-solitaire/b-total-settle.txt', bfile(rows, 'totalSettle'));
writeFileSync('research/bulgarian-solitaire/b-max-tail.txt', bfile(rows, 'maxTail'));
writeFileSync('research/bulgarian-solitaire/b-max-tail-count.txt', bfile(rows, 'maxTailCount'));
const flat = key => rows.map(r => r[key]).join(',');
console.log('totalSettle :', flat('totalSettle'));
console.log('maxTail     :', flat('maxTail'));
