// verify.mjs: the MATHEMATICS gate. Runs every cross-check that makes the
// surface Lights Out nullities trustworthy, and prints PASS/FAIL.
//
// WHAT THIS FILE DOES NOT DO: it never opens the staged b-files in
// oversight/oeis/lights-out-surfaces/. It checks live recomputations only, so it
// stays green no matter what those four files contain. Binding the staged terms
// to a recomputation is a separate script, deliberately kept separate:
//        node oversight/oeis/lights-out-surfaces/verify-staged.mjs
// Both have to be green before anything is deposited.
//
//   1. CALIBRATION. Reproduce the two PUBLISHED OEIS sequences bit-for-bit,
//      n=1..40:
//        plane  == A159257  (flat n x n grid Lights Out rank deficiency)
//        torus  == A165738  (n x n torus Lights Out rank deficiency)
//      If our model reproduces both, its conventions are the standard ones.
//   2. CODE PATHS agree, term by term, on all surfaces, over the ranges named
//      below. They are not equally independent, so the ranges matter:
//        (a) engine.mjs  — JS Gauss-Jordan on BigInt rows. The reference.
//        (b) verify.py   — Python, separately written adjacency AND separately
//                          written elimination. The only genuinely independent
//                          path. Cross-checked n=1..40 (raised from 30 on
//                          2026-07-27; the cost grows about as n^5, and n=1..40
//                          costs about 15 s against about 5 s for n=1..30).
//        (c) brute.mjs   — direct 2^(n^2) kernel count under the game's toggle
//                          rule. Independent of (a)'s LINEAR ALGEBRA but it
//                          imports engine.mjs's closedNeighbourhood, so it shares
//                          (a)'s gluing geometry. n=1..4 only.
//   3. TOPOLOGY. chi.mjs confirms each surface label by Euler characteristic +
//      boundary (torus chi=0 no boundary, Klein chi=0 no boundary, projective
//      chi=1 no boundary, cylinder/Mobius chi=0 with boundary, plane chi=1).
//   4. SANITY. M is symmetric on every surface (adjacency is consistent);
//      nullity <= 2n on the closed surfaces; the observed parity law holds.
//
// Run:  node verify.mjs

import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { SURFACES, buildMatrix, nullity, isSymmetric, surfaceNullity } from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
let pass = 0, fail = 0;
const ok = (c, label) => { if (c) { pass++; console.log('  ✓ ' + label); } else { fail++; console.error('  ✗ FAIL: ' + label); } };

// Published ground truths (from oeis.org, fetched 2026-07-18), n=1..40.
const A159257 = [0,0,0,4,2,0,0,0,8,0,6,0,0,4,0,8,2,0,16,0,0,0,14,4,0,0,0,0,10,20,0,20,16,4,6,0,0,0,32,0];
const A165738 = [0,0,4,0,8,8,0,0,4,16,0,16,0,0,12,0,16,8,0,32,4,0,0,32,8,0,4,0,0,24,40,0,44,32,8,16,0,0,4,64];
const NCAL = 40;

console.log('1. Calibration against published OEIS sequences (n=1..' + NCAL + '):');
{
  let mism = 0;
  for (let n = 1; n <= NCAL; n++) if (surfaceNullity(n, 'plane') !== A159257[n - 1]) mism++;
  ok(mism === 0, 'plane  reproduces A159257 (flat grid) exactly');
  mism = 0;
  for (let n = 1; n <= NCAL; n++) if (surfaceNullity(n, 'torus') !== A165738[n - 1]) mism++;
  ok(mism === 0, 'torus  reproduces A165738 (torus) exactly');
}

console.log('2. Code paths agree over the ranges each one actually covers:');
{
  // (a) engine values n=1..NMAX. NMAX bounds the Python cross-check, which is the
  // only structurally independent path here; it was 30 until 2026-07-27.
  const NMAX = 40;
  const engineSeq = {};
  for (const s of SURFACES) { engineSeq[s] = []; for (let n = 1; n <= NMAX; n++) engineSeq[s].push(surfaceNullity(n, s)); }

  // (c) Python
  let pyOut;
  try {
    pyOut = execFileSync('python3', [join(HERE, 'verify.py'), String(NMAX)], { encoding: 'utf8' });
  } catch (e) { pyOut = ''; }
  const pySeq = {};
  for (const line of pyOut.trim().split('\n')) {
    const [name, rest] = line.split(':');
    if (!rest) continue;
    pySeq[name.trim()] = rest.trim().split(',').map(x => parseInt(x.trim(), 10));
  }
  let allMatch = pyOut.length > 0;
  for (const s of SURFACES) allMatch = allMatch && pySeq[s] && pySeq[s].join(',') === engineSeq[s].join(',');
  ok(allMatch, 'Python (independent adjacency + elimination) matches engine.mjs on all 6 surfaces, n=1..' + NMAX);

  // (b) brute force n=1..4 (fast); compare to engine
  const bruteOut = execFileSync('node', [join(HERE, 'brute.mjs'), '4'], { encoding: 'utf8' });
  // parse lines like "n=3:  plan=0  cyli=2  toru=4 ..."
  const abbr = { plan: 'plane', cyli: 'cylinder', toru: 'torus', mobi: 'mobius', klei: 'klein', proj: 'projective' };
  let bruteMatch = true;
  for (const line of bruteOut.trim().split('\n')) {
    const m = line.match(/^n=(\d+):/); if (!m) continue;
    const n = parseInt(m[1], 10);
    for (const tok of line.split(/\s+/)) {
      const mm = tok.match(/^(\w+)=(\d+)$/); if (!mm || !abbr[mm[1]]) continue;
      if (parseInt(mm[2], 10) !== engineSeq[abbr[mm[1]]][n - 1]) bruteMatch = false;
    }
  }
  ok(bruteMatch, 'brute-force kernel count (2^(n^2) subsets, no linear algebra, but SHARES engine.mjs\'s closedNeighbourhood geometry) matches engine.mjs, n=1..4, all surfaces');
}

console.log('3. Topology confirms each surface label (Euler characteristic + boundary):');
{
  let chiPass = true;
  try { execFileSync('node', [join(HERE, 'chi.mjs')], { encoding: 'utf8' }); } catch (e) { chiPass = false; }
  ok(chiPass, 'chi.mjs: all six surfaces show the expected (chi, boundary) fingerprint');
}

console.log('4. Sanity — symmetry, bounds, parity law:');
{
  let sym = true;
  for (const s of SURFACES) for (let n = 1; n <= 8; n++) { const { rows, N } = buildMatrix(n, n, s); if (!isSymmetric(rows, N)) sym = false; }
  ok(sym, 'M = M^T (adjacency consistent) on all surfaces, n=1..8');

  // Closed surfaces: nullity <= 2n (a standard bound for the torus; check it holds).
  let bound = true;
  for (let n = 1; n <= 30; n++) if (surfaceNullity(n, 'torus') > 2 * n) bound = false;
  ok(bound, 'torus nullity <= 2n for n=1..30 (matches A165738 formula a(n) <= 2n)');

  // Observed parity law: plane & torus always even; cylinder odd exactly at n=5 mod 6 (5..47).
  let evenOK = true;
  for (let n = 1; n <= 48; n++) { if (surfaceNullity(n, 'plane') % 2 || surfaceNullity(n, 'torus') % 2) evenOK = false; }
  ok(evenOK, 'plane & torus nullity is even for every n=1..48 (the pairing symmetry)');

  let cylOK = true;
  for (let n = 3; n <= 48; n++) { const odd = surfaceNullity(n, 'cylinder') % 2 === 1; if (odd !== (n % 6 === 5)) cylOK = false; }
  ok(cylOK, 'cylinder nullity is odd exactly at n = 5 (mod 6), for n=3..48 (the twist shows in the parity)');

  // The Mobius half of the same observation. The README and the stratum page both
  // state it; until 2026-07-27 nothing checked it. n=1,2 are the degenerate wrap
  // sizes, so the rule is stated from n=3 as the cylinder's is.
  let mobOK = true;
  for (let n = 3; n <= 48; n++) { const odd = surfaceNullity(n, 'mobius') % 2 === 1; if (odd !== (n % 6 === 5 || n % 12 === 2)) mobOK = false; }
  ok(mobOK, 'Mobius nullity is odd exactly at n = 5 (mod 6) or n = 2 (mod 12), for n=3..48');
}

console.log('\nNOTE: this gate reads no b-file. The staged terms in');
console.log('oversight/oeis/lights-out-surfaces/ are bound to a recomputation by');
console.log('  node oversight/oeis/lights-out-surfaces/verify-staged.mjs');
console.log('which must also be green before deposit.');

console.log(`\n${fail === 0 ? 'PASS' : 'FAIL'} — ${pass} checks passed, ${fail} failed.`);
process.exit(fail === 0 ? 0 : 1);
