// Verifier — Bulgarian-solitaire settling-time program (ledger P2).
//
// The honesty design: the SAME engine must reproduce FIVE catalogued OEIS sequences
// exactly (the anchors) and the proven Igusa/Etienne convergence bound; only then are
// its NEW outputs trustworthy. The new sequences (total settling time S(n); worst-case
// settling time maxTail(n); its multiplicity) are each cross-checked.
// Every claim here is recomputed from scratch — no value is taken on faith.
//
// Coverage note (read before trusting the words "two-way" / "n<=61"):
//   - The catalogued anchors and the k^2-k theorem are checked to n=40 (their literals
//     reach that far; that is the calibration range, not a staged sequence).
//   - S(n), the ONE sequence we stage, is checked to n=55 (every term in the deposit
//     b-file) by two in-file distance methods AND read back against the staged
//     oversight b-file term by term.
//   - The A188160 relation is checked to n=61 (an A188160 b-file literal to 61).
// The two in-file S-methods share graph construction, the move, and cycle detection
// (settleTimes builds ONE functional graph and both methods walk it); they differ ONLY
// in how the distance-to-cycle is computed (reverse BFS vs forward memoised iteration).
// A genuinely independent implementation — separate language, own partitioner, own move,
// own cycle detection, forward-memo tails — lives in s_explore.py and reproduces all 55
// S(n) terms; run `python3 research/bulgarian-solitaire/s_explore.py 55 1` to confirm.
import { readFileSync } from 'fs';
import { analyze, maxTailForward, partitions, move } from './engine.mjs';

let pass = 0, fail = 0;
const ok = (name, cond) => { if (cond) pass++; else { fail++; console.log('  ✗ ' + name); } };

const NMAX = 40; // calibration range for the catalogued anchors and the k^2-k theorem
const rows = []; for (let n = 1; n <= NMAX; n++) rows.push(analyze(n));
const col = k => rows.map(r => r[k]);

// ===== Anchors: the engine reproduces catalogued OEIS sequences exactly (n<=40) =====
const Cf = (a, b) => { let r = 1; for (let i = 0; i < b; i++) r = r * (a - i) / (i + 1); return Math.round(r); };
{ // recurrent(n): block for n in (T_{k-1},T_k] is C(k,1..k) — Pascal w/o left edge (A135278). Etienne 1991.
  const want = []; for (let k = 1; want.length < NMAX; k++) for (let j = 1; j <= k && want.length < NMAX; j++) want.push(Cf(k, j));
  ok('recurrent = Pascal rows C(k,1..k)   [Etienne 1991; A135278/A007318]', col('recurrent').every((v, i) => v === want[i]));
}
{ // fixed(n)=1 iff n triangular (Brandt 1982: unique staircase fixed point).
  const tri = new Set(); for (let k = 1; k * (k + 1) / 2 <= NMAX; k++) tri.add(k * (k + 1) / 2);
  ok('fixed = [n triangular]               [Brandt 1982; A010054 support]', col('fixed').every((v, i) => v === (tri.has(i + 1) ? 1 : 0)));
}
{ const A123975 = [0,0,1,1,2,3,5,7,10,14,20,27,37,49,66,86,113,147,190,243,311,394,499,627,786,980,1220,1510,1865,2294,2816,3443,4202,5110,6203,7507,9067,10923,13135,15755];
  ok('goe = A123975 (Garden of Eden)       [catalogued]', col('goe').every((v, i) => v === A123975[i])); }
{ const A037306 = [1,1,1,1,1,1,1,2,1,1,1,2,2,1,1,1,3,4,3,1,1,1,3,5,5,3,1,1,1,4,7,10,7,4,1,1,1,4,10,14];
  ok('numCycles = A037306 (flattened)      [necklace/cycle bijection]', col('numCycles').every((v, i) => v === A037306[i])); }
{ const A183110 = [1,2,1,3,3,1,4,4,4,1,5,5,5,5,1,6,6,6,6,6,1,7,7,7,7,7,7,1,8,8,8,8,8,8,8,1,9,9,9,9];
  ok('longest = A183110 (orbit of [1^n])   [catalogued]', col('longest').every((v, i) => v === A183110[i])); }

// ===== The proven theorem, reproduced (n<=40) =====
{ let good = true; for (let k = 1; k * (k + 1) / 2 <= NMAX; k++) { const n = k * (k + 1) / 2; if (rows[n - 1].maxTail !== k * k - k) good = false; }
  ok('maxTail(T_k) = k^2 - k              [Igusa 1985 / Etienne — tight]', good); }

// ===== maxTail cross-checked two ways (same graph, two distance methods) (n<=40) =====
{ let same = true; for (let n = 1; n <= NMAX; n++) if (rows[n - 1].maxTail !== maxTailForward(n)) same = false;
  ok('maxTail: reverse-BFS == forward-iteration', same); }

// ===== The staged sequence S(n): two distance methods, checked to EVERY staged term =====
//  Both methods below run on ONE functional graph built here (shared partitions/move/cycle
//  detection); they differ only in the distance-to-cycle computation. This is a method
//  cross-check, not two independent implementations — see the header for the independent one.
function settleTimes(n) {
  const parts = partitions(n), N = parts.length, idx = new Map();
  parts.forEach((p, i) => idx.set(p.join(','), i));
  const next = parts.map(p => idx.get(move(p).join(',')));
  const stt = new Uint8Array(N), cyc = new Uint8Array(N);
  for (let s = 0; s < N; s++) { if (stt[s]) continue; const pa = []; let u = s; while (stt[u] === 0) { stt[u] = 1; pa.push(u); u = next[u]; } if (stt[u] === 1) { let v = u; do { cyc[v] = 1; v = next[v]; } while (v !== u); } for (const w of pa) stt[w] = 2; }
  // distance method A: reverse BFS from the cyclic set
  const rev = Array.from({ length: N }, () => []); next.forEach((j, i) => rev[j].push(i));
  const d = new Int32Array(N).fill(-1), q = []; for (let i = 0; i < N; i++) if (cyc[i]) { d[i] = 0; q.push(i); }
  for (let h = 0; h < q.length; h++) { const u = q[h]; for (const w of rev[u]) if (d[w] < 0) { d[w] = d[u] + 1; q.push(w); } }
  let SA = 0; for (let i = 0; i < N; i++) SA += d[i];
  // distance method B: forward memoised per-node tail, summed independently
  const m = new Int32Array(N).fill(-1);
  const td = u => { const st = []; let v = u; while (m[v] < 0 && !cyc[v]) { st.push(v); v = next[v]; } let b = cyc[v] ? 0 : m[v]; if (cyc[v]) m[v] = 0; while (st.length) m[st.pop()] = ++b; return m[u] = cyc[u] ? 0 : m[u]; };
  let SB = 0; for (let s = 0; s < N; s++) SB += (cyc[s] ? 0 : td(s));
  return { SA, SB };
}
const SMAX = 55; // every term staged in the deposit b-file
// Read the STAGED deposit b-file and hold the verifier to it, term by term.
const stagedPath = new URL('../../oversight/oeis/bulgarian-solitaire-settling/b-file.txt', import.meta.url);
const staged = readFileSync(stagedPath, 'utf8').trim().split('\n').map(line => {
  const [idx, val] = line.trim().split(/\s+/); return { n: +idx, v: +val };
});
ok('staged b-file has ' + SMAX + ' terms (n=1..' + SMAX + ')', staged.length === SMAX && staged.every((r, i) => r.n === i + 1));
{ let same = true; for (let n = 1; n <= SMAX; n++) { const { SA, SB } = settleTimes(n); if (SA !== SB || SA !== staged[n - 1].v) same = false; }
  ok('S(n) to n=' + SMAX + ': BFS == forward == staged b-file (every deposit term)', same); }

// ===== The honest relation to A188160 (so maxTail is never over-claimed), to n=61 =====
//  A188160(n) = "max steps until a partition repeats" = max_s(tail(s)+period(s)) - 1.
//  It BUNDLES one full cycle into the count; maxTail = max_s tail(s) isolates the transient.
//  Verified here for n<=61 (the A188160 literal below is OEIS b188160 to n=61):
//    maxTail(n) = A188160(n) - longest(n) + 1.
//  This is NON-trivial — cycle lengths within a single n genuinely differ (e.g. n=8 -> {2,4},
//  n=17 -> {3,6,6}) — so it asserts the worst transient always flows into a LONGEST cycle.
const RMAX = 61;
{ const A188160 = [0,1,2,4,5,6,7,8,10,12,12,12,13,18,20,20,17,18,21,28,30,30,24,24,25,32,40,42,42,35,31,32,36,45,54,56,56,48,40,40,41,50,60,70,72,72,63,54,49,50,55,66,77,88,90,90,80,70,60,60,61];
  let rel = true;
  for (let n = 1; n <= RMAX; n++) {
    const r = n <= NMAX ? rows[n - 1] : analyze(n);
    if (r.maxTail !== A188160[n - 1] - r.longest + 1) rel = false;
  }
  ok('maxTail = A188160 - longest + 1 to n=' + RMAX + ' [worst transient -> longest cycle]', rel);
  // and confirm cycle lengths really do differ (so the relation is not a triviality)
  ok('cycle lengths differ within an n (n=8 -> {2,4}; relation non-trivial)', JSON.stringify(rows[7].cycleLens) === JSON.stringify([2, 4])); }

// ===== A concrete instance worth naming =====
ok('n=45 worst-case settling = 72 = 9^2-9 (staircase 1..9)', analyze(45).maxTail === 72);

console.log(`\nBulgarian solitaire verifier: ${pass}/${pass + fail} passed.`);
process.exit(fail ? 1 : 0);
