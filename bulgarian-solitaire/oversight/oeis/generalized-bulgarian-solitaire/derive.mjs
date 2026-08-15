// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// Standalone, self-contained derivation of the settling statistics of s-Bulgarian solitaire
// (well-behaved sigma-Bulgarian with sigma(h)=min(h,s); Hopkins's operation H_s; s=1 is classic).
//
// Move B_s on a partition of n: from every pile of size h remove min(h, s) cards; collect ALL
// removed cards into ONE new pile; drop emptied piles; re-sort. Deterministic map on partitions(n)
// => every hand runs a transient tail into a cycle. We build the full functional graph and read off
// the settling statistics. Reproducible from scratch (no external imports).
//
//   node derive.mjs [N=55] [s=2]        # prints the sequences; rewrites the b-files for that s
import { writeFileSync } from 'node:fs';

function partitions(n) { const r = [], c = []; (function go(rem, mx) { if (rem === 0) { r.push(c.slice()); return; } for (let k = Math.min(rem, mx); k >= 1; k--) { c.push(k); go(rem - k, k); c.pop(); } })(n, n); return r; }
function move(p, s) { let removed = 0; const np = []; for (const x of p) { const t = x < s ? x : s; removed += t; if (x - t > 0) np.push(x - t); } if (removed > 0) np.push(removed); np.sort((a, b) => b - a); return np; }

function analyze(n, s) {
  const parts = partitions(n), N = parts.length, idx = new Map();
  parts.forEach((p, i) => idx.set(p.join(','), i));
  const next = parts.map(p => idx.get(move(p, s).join(',')));
  const stt = new Uint8Array(N), cyc = new Uint8Array(N);
  for (let a = 0; a < N; a++) { if (stt[a]) continue; const pa = []; let u = a; while (stt[u] === 0) { stt[u] = 1; pa.push(u); u = next[u]; } if (stt[u] === 1) { let v = u; do { cyc[v] = 1; v = next[v]; } while (v !== u); } for (const w of pa) stt[w] = 2; }
  const rev = Array.from({ length: N }, () => []); next.forEach((j, i) => rev[j].push(i));
  const d = new Int32Array(N).fill(-1), q = []; for (let i = 0; i < N; i++) if (cyc[i]) { d[i] = 0; q.push(i); }
  for (let h = 0; h < q.length; h++) { const u = q[h]; for (const w of rev[u]) if (d[w] < 0) { d[w] = d[u] + 1; q.push(w); } }
  const seen = new Uint8Array(N), lens = []; for (let a = 0; a < N; a++) if (cyc[a] && !seen[a]) { let L = 0, v = a; do { seen[v] = 1; L++; v = next[v]; } while (v !== a); lens.push(L); }
  const indeg = new Int32Array(N); for (let i = 0; i < N; i++) indeg[next[i]]++;
  let goe = 0, maxTail = 0, totalSettle = 0, recurrent = 0; for (let i = 0; i < N; i++) { if (indeg[i] === 0) goe++; if (d[i] > maxTail) maxTail = d[i]; totalSettle += d[i]; if (cyc[i]) recurrent++; }
  return { totalSettle, maxTail, goe, numCycles: lens.length, recurrent };
}

const N = parseInt(process.argv[2] || '55', 10);
const s = parseInt(process.argv[3] || '2', 10);
const keys = ['totalSettle', 'maxTail', 'goe', 'numCycles', 'recurrent'];
const names = { totalSettle: 'b-total-settle', maxTail: 'b-max-tail', goe: 'b-goe', numCycles: 'b-num-cycles', recurrent: 'b-recurrent' };
const cols = {}; for (const k of keys) cols[k] = [];
for (let n = 1; n <= N; n++) { const a = analyze(n, s); for (const k of keys) cols[k].push(a[k]); }
for (const k of keys) {
  console.log(`${k} (s=${s}), n=1..${N}:\n  ${cols[k].join(', ')}`);
  writeFileSync(new URL(`./${names[k]}-s${s}.txt`, import.meta.url), cols[k].map((v, i) => `${i + 1} ${v}`).join('\n') + '\n');
}
console.log(`\nrewrote ${keys.length} b-files for s=${s}.`);
