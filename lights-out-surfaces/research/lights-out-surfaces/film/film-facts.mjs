#!/usr/bin/env node
// film-facts.mjs — offline gate. Re-asserts, without a browser, every number the
// film puts on screen against the project's own verified engine and census file,
// plus the audio's twist-bell schedule. If this is green, the film cannot be
// showing a value the maths does not produce. Run before the render.
import { readFileSync } from 'node:fs';
import { buildMatrix, surfaceNullity } from '../engine.mjs';
import { kernelBasis, toggledBy } from './kernel.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ✓ ' + m); } else { fail++; console.error('  ✗ FAIL: ' + m); } };

const DATA = JSON.parse(readFileSync(new URL('../data.json', import.meta.url)));

// 1. The hero quiet pattern really changes nothing, and the X returns.
const QMASK = kernelBasis(5, 'plane')[0];
ok(toggledBy(QMASK, 5, 'plane') === 0n, 'hero quiet pattern (5×5 flat) toggles NOTHING');
{
  const M = buildMatrix(5, 5, 'plane').rows;
  const START = [0, 6, 12, 18, 24, 4, 8, 16, 20];
  let sx = 0n; for (const i of START) sx |= 1n << BigInt(i);
  const btns = []; for (let i = 0; i < 25; i++) if ((QMASK >> BigInt(i)) & 1n) btns.push(i);
  let bd = sx; for (const j of btns) bd ^= M[j];
  ok(bd === sx, `pressing all ${btns.length} quiet buttons returns the X exactly (d=2 → 16 buttons)`);
  ok(btns.length === 16, 'the hero quiet pattern has 16 buttons');
}

// 2. The census the film draws live (n=1..10, five surfaces) matches data.json.
const surfaces = ['plane', 'torus', 'cylinder', 'mobius', 'klein'];
let censusOK = true;
for (const s of surfaces) for (let n = 1; n <= 10; n++) {
  if (surfaceNullity(n, s) !== DATA.seq[s][n - 1]) censusOK = false;
}
ok(censusOK, 'census n=1..10 (engine) === data.json for all five surfaces');

// 3. The two calibration anchors the film names.
ok(surfaceNullity(3, 'torus') === 4, 'torus d(3) = 4 (matches A165738)');
ok(surfaceNullity(5, 'plane') === 2, 'flat grid d(5) = 2 (matches A159257)');

// 4. The parity finding the film and the soundtrack both enact.
const oddNs = [];
for (let n = 1; n <= 30; n++) if (DATA.seq.cylinder[n - 1] % 2 === 1) oddNs.push(n);
const expect = [5, 11, 17, 23, 29];
ok(JSON.stringify(oddNs) === JSON.stringify(expect), `cylinder d(n) odd (n≤30) exactly at ${expect.join(', ')} — all ≡ 5 (mod 6)`);
ok(oddNs.every(n => n % 6 === 5), 'every odd-nullity cylinder size is ≡ 5 (mod 6)');

// 5. The audio's twist bells ring on exactly those boards (n≤64).
try {
  const tr = JSON.parse(readFileSync(new URL('./audio-trace.json', import.meta.url)));
  const audioOdd = [];
  for (let n = 1; n <= 64; n++) if (DATA.seq.cylinder[n - 1] % 2 === 1) audioOdd.push(n);
  ok(JSON.stringify(tr.oddNs) === JSON.stringify(audioOdd), `audio twist bells at ${tr.oddNs.join(', ')} == odd cylinder d(n)`);
} catch { ok(false, 'audio-trace.json present (run make-audio.mjs first)'); }

console.log(`\n${fail === 0 ? 'PASS' : 'FAIL'} — ${pass} checks passed, ${fail} failed.`);
process.exit(fail === 0 ? 0 : 1);
