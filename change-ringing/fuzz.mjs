// fuzz.mjs — adversarial validation of count.c on random graphs.
//
// For each random graph: count simple paths from `start` by length (and the
// "cyclic" variant: last vertex adjacent to start) with a trivially-correct
// BigInt enumerator written independently of count.c, then require bit-exact
// agreement from every count.c mode: --simple, job mode with the cnt engine,
// job mode with the mask engine (N<=128), across several prefix depths K,
// plus a checkpoint-resume pass (run twice with the same -c file; second run
// must skip all jobs and still aggregate identical totals).
//
// Usage: node fuzz.mjs [rounds=60] [seed=1]
import { execFileSync } from 'node:child_process';
import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'node:fs';

const rounds = parseInt(process.argv[2] || '60', 10);
let seed = BigInt(parseInt(process.argv[3] || '1', 10));
const rng = () => {
  // xorshift64*
  seed ^= seed << 13n; seed &= 0xffffffffffffffffn;
  seed ^= seed >> 7n;
  seed ^= seed << 17n; seed &= 0xffffffffffffffffn;
  return Number((seed * 2685821657736338717n & 0xffffffffffffffffn) >> 11n) / 2 ** 53;
};
const ri = (a, b) => a + Math.floor(rng() * (b - a + 1));

function randomGraph() {
  const N = ri(4, 40);
  const p = 0.05 + rng() * 0.4;
  const adj = Array.from({ length: N }, () => new Set());
  for (let v = 0; v < N; v++)
    for (let w = v + 1; w < N; w++)
      if (rng() < p) { adj[v].add(w); adj[w].add(v); }
  const start = ri(0, N - 1);
  return { N, start, adj: adj.map((s) => [...s].sort((a, b) => a - b)) };
}

// trivially-correct reference: explicit recursive enumeration, BigInt tallies
function reference(G, maxL) {
  const path = Array(maxL + 1).fill(0n);
  const cyc = Array(maxL + 1).fill(0n);
  path[1] = 1n; cyc[1] = 1n; // Sønsteby L=1 convention
  const inR = new Set(G.adj[G.start]);
  const visited = new Array(G.N).fill(false);
  visited[G.start] = true;
  (function rec(v, depth) {
    if (depth >= maxL) return;
    for (const w of G.adj[v]) {
      if (visited[w]) continue;
      path[depth + 1]++;
      if (inR.has(w)) cyc[depth + 1]++;
      visited[w] = true;
      rec(w, depth + 1);
      visited[w] = false;
    }
  })(G.start, 1);
  const lines = ['# L path cyclic noncappable'];
  for (let L = 1; L <= maxL; L++) {
    const nc = L === 1 ? 0n : path[L] - cyc[L];
    lines.push(`${L} ${path[L]} ${cyc[L]} ${nc}`);
  }
  return lines.join('\n') + '\n';
}

function writeGraph(G, file) {
  const lines = [`${G.N} ${G.start}`];
  for (let v = 0; v < G.N; v++) lines.push(`${G.adj[v].length} ${G.adj[v].join(' ')}`.trim());
  writeFileSync(file, lines.join('\n') + '\n');
}

const run = (args) => execFileSync('./count', args, { stdio: ['ignore', 'pipe', 'ignore'] }).toString();

let fails = 0;
for (let r = 0; r < rounds; r++) {
  const G = randomGraph();
  const maxL = ri(4, Math.min(G.N, 12));
  const gfile = `/tmp/fuzz-g${r}.txt`;
  writeGraph(G, gfile);
  const want = reference(G, maxL);

  const modes = [['--simple']];
  for (const K of [2, 3, ri(2, Math.max(2, maxL - 2))])
    if (K <= maxL - 2) {
      modes.push(['-k', String(K), '-t', '2', '--engine', 'cnt']);
      if (G.N <= 128) modes.push(['-k', String(K), '-t', '2', '--engine', 'mask']);
    }
  for (const m of modes) {
    let got;
    try {
      got = run(['--graph', gfile, '-L', String(maxL), ...m]);
    } catch (e) {
      console.log(`FAIL round ${r} mode ${m.join(' ')} — crashed: ${e.message}`);
      fails++; continue;
    }
    if (got !== want) {
      console.log(`FAIL round ${r} mode ${m.join(' ')} (N=${G.N} start=${G.start} maxL=${maxL})`);
      console.log('want:\n' + want + 'got:\n' + got);
      fails++;
    }
  }

  // checkpoint-resume: run once, run again with same file → identical output
  if (maxL >= 5) {
    const ck = `/tmp/fuzz-ck${r}.txt`;
    if (existsSync(ck)) unlinkSync(ck);
    const a = run(['--graph', gfile, '-L', String(maxL), '-k', '3', '-t', '2', '-c', ck]);
    // partial-resume: drop the second half of the job lines, rerun
    const lines = readFileSync(ck, 'utf8').trimEnd().split('\n');
    const jobs = lines.slice(1);
    const keep = [lines[0], ...jobs.slice(0, Math.floor(jobs.length / 2))];
    writeFileSync(ck, keep.join('\n') + '\n');
    const b = run(['--graph', gfile, '-L', String(maxL), '-k', '3', '-t', '2', '-c', ck]);
    if (a !== want || b !== want) {
      console.log(`FAIL round ${r} checkpoint resume (a ok: ${a === want}, b ok: ${b === want})`);
      fails++;
    }
    unlinkSync(ck);
  }
  unlinkSync(gfile);
}
console.log(fails === 0 ? `PASS — ${rounds} random graphs, all modes agree with the BigInt reference` : `${fails} FAILURES`);
process.exit(fails === 0 ? 0 : 1);
