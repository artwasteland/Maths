#!/usr/bin/env node
// make-audio.mjs — the soundtrack for THE LIGHTS THAT HIDE.
//
// 166 s, 44.1 kHz, stereo, deterministic. The honesty core of the audio is
// ENGINE-ENACTMENT of the stratum's own finding: "on the flat grid and the
// torus d(n) is always even; glue the board into a cylinder and the count turns
// ODD at exactly the sizes n ≡ 5 (mod 6) — the parity of the answer can tell you
// the board was twisted." The soundtrack WALKS the boards n = 1, 2, 3, ... one
// per beat, and every beat carries the real computed number d_cylinder(n): a
// soft pitched pluck whose note rises with the hidden dimension d(n), and — on
// exactly the boards where d(n) is ODD — a bright struck bell, the twist made
// audible. Nobody hand-places those bells; they ring where the verified GF(2)
// nullity is odd. The parity read here is taken from the same data.json the
// stratum page and the OEIS deposit are built on, and re-checked against the
// live engine (engine.mjs) at boot, so the rhythm cannot drift from the maths.
//
// The LAYERS (the enactment is L2/L3; the rest is bed):
//   L1 · drone      — tonic/fifth/octave sine bed, slow detune. Cool ground.
//   L2 · THE WALK   — one soft pluck per board n; pitch = a pentatonic-minor
//        step chosen by d_cylinder(n) (the hidden dimension, heard). Pitch
//        mapping + scale are DECLARED CRAFT; the value d(n) it reads is real.
//   L3 · THE TWIST BELL — a bright additive bell struck on exactly the boards
//        whose d(n) is ODD (cylinder: n ≡ 5 mod 6). This IS the finding, sonified.
//   L4 · scene bells — struck tones at the film's phase boundaries.
//   L5 · breath     — a barely-audible noise bed for air.
//
// Output: research/lights-out-surfaces/film/audio.wav (+ audio-trace.json for
// film-facts.mjs to re-assert offline).

import { writeFileSync, readFileSync } from 'node:fs';
import { surfaceNullity } from '../engine.mjs';

const SR = 44100, DUR = 166, N = SR * DUR, TPI = Math.PI * 2;
const TONIC = 98.0;   // G2 — a low, cool root for a binary/structural subject

// ---------- WAV writer (16-bit stereo) ----------
function writeWav(filename, L, R) {
  const n = L.length, dataSize = n * 4, buf = Buffer.alloc(44 + dataSize);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + dataSize, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28);
  buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(dataSize, 40);
  for (let i = 0; i < n; i++) {
    const lo = Math.max(-1, Math.min(1, L[i])), ro = Math.max(-1, Math.min(1, R[i]));
    buf.writeInt16LE(Math.round(lo * 32767), 44 + i * 4);
    buf.writeInt16LE(Math.round(ro * 32767), 44 + i * 4 + 2);
  }
  writeFileSync(filename, buf);
}
function mul32(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const L = new Float32Array(N), R = new Float32Array(N);

// ── the data the walk reads: d_cylinder(n), n = 1..64 ──
// Loaded from the project's own computed census, then re-checked against the
// live engine so the rhythm and the maths cannot disagree.
const DATA = JSON.parse(readFileSync(new URL('../data.json', import.meta.url)));
const CYL = DATA.seq.cylinder;                       // length 64
const NWALK = 64;
// self-check: the engine reproduces the file for a scattered sample of n.
for (const n of [3, 5, 8, 14, 27, 35, 60]) {
  const live = surfaceNullity(n, 'cylinder');
  if (live !== CYL[n - 1]) { console.error(`ENGINE/DATA MISMATCH cylinder n=${n}: engine ${live} vs data ${CYL[n - 1]}`); process.exit(1); }
}

// pentatonic-minor ladder (just intonation), three octaves over the tonic.
// DECLARED CRAFT: the scale and the d→step mapping are a musical choice; only
// the value d(n) that selects the step is the real, verified number.
const PENT = [1, 6 / 5, 4 / 3, 3 / 2, 9 / 5];        // minor pentatonic ratios
const LADDER = [];
for (let oct = 0; oct <= 2; oct++) for (const r of PENT) LADDER.push(TONIC * r * Math.pow(2, oct));
LADDER.sort((a, b) => a - b);
// d(n) → ladder index. d=0 sits at the root; the biggest d in range (8) reaches
// the top. A board with more hidden patterns sings a higher note.
const DMAX = Math.max(...CYL);
function pitchOfD(d) {
  const idx = Math.round((d / DMAX) * (LADDER.length - 1));
  return LADDER[Math.max(0, Math.min(LADDER.length - 1, idx))];
}

// walk time-map: board n = 1..64 spread across the body of the film.
const WALK_T0 = 8, WALK_T1 = 158;
function tOfN(n) { return WALK_T0 + ((n - 1) / (NWALK - 1)) * (WALK_T1 - WALK_T0); }

// a short pluck (sine + light 2nd partial, fast attack, exp decay).
function pluck(t0, f, amp, pan, decay = 0.14) {
  const i0 = Math.floor(t0 * SR); if (i0 < 0 || i0 >= N) return;
  const len = Math.min(Math.floor(decay * 5 * SR), N - i0);
  const p = Math.max(-1, Math.min(1, pan));
  const lg = 0.5 * (1 - p), rg = 0.5 * (1 + p);
  for (let k = 0; k < len; k++) {
    const tau = k / SR;
    const env = Math.exp(-tau / decay) * Math.min(1, tau / 0.004);
    const s = amp * env * (Math.sin(TPI * f * tau) + 0.25 * Math.sin(TPI * f * 2 * tau));
    L[i0 + k] += s * lg; R[i0 + k] += s * rg;
  }
}
// an additive struck bell (four just partials, long decay).
function strike(t0, f0, dur, amp, pan, partials = [1, 2, 3, 4], pamp = [1, 0.55, 0.32, 0.18], decay = 1.4) {
  const i0 = Math.floor(t0 * SR), len = Math.floor(dur * SR);
  const p = Math.max(-1, Math.min(1, pan));
  const lg = 0.5 * (1 - p), rg = 0.5 * (1 + p);
  for (let k = 0; k < len && i0 + k < N && i0 + k >= 0; k++) {
    const tt = k / SR, env = Math.exp(-tt / decay) * Math.min(1, tt / 0.004);
    let s = 0; for (let h = 0; h < partials.length; h++) s += pamp[h] * Math.sin(TPI * f0 * partials[h] * tt);
    L[i0 + k] += amp * env * s * lg; R[i0 + k] += amp * env * s * rg;
  }
}

// ==========================================================================
// L2 + L3 — THE WALK and THE TWIST BELL. The enactment.
// ==========================================================================
let twistBells = 0, oddNs = [];
for (let n = 1; n <= NWALK; n++) {
  const d = CYL[n - 1];
  const t = tOfN(n);
  const pan = -0.6 + 1.2 * ((n - 1) / (NWALK - 1));   // walk sweeps left → right
  // L2 · the pitched pluck; a board with d=0 (unique solutions) is quiet and low.
  const amp = d === 0 ? 0.055 : 0.075;
  pluck(t, pitchOfD(d), amp, pan);
  // L3 · the twist bell rings iff d(n) is ODD — the parity that detects the twist.
  if (d % 2 === 1) {
    strike(t, TONIC * 3 * Math.pow(2, (n % 12) / 24), 2.6, 0.10, pan);  // bright, high
    twistBells++; oddNs.push(n);
  }
}

// ==========================================================================
// L1 — the drone bed (tonic / fifth / octave), slow detune, fade in/out.
// ==========================================================================
{
  const fs_ = [TONIC, TONIC * 3 / 2, TONIC * 2], amps = [1, 0.5, 0.34], ph = [0, 0, 0];
  for (let i = 0; i < N; i++) {
    const t = i / SR, lfo = 1 + 0.003 * Math.sin(TPI * 0.06 * t);
    const env = Math.min(1, t / 6) * Math.min(1, (DUR - t) / 5);
    for (let k = 0; k < 3; k++) {
      ph[k] += (TPI * fs_[k] * (k === 1 ? 1 / lfo : lfo)) / SR;
      const a = 0.10 * amps[k] * env;
      L[i] += a * Math.sin(ph[k] + k * 0.02); R[i] += a * Math.sin(ph[k] - k * 0.02);
    }
  }
}

// ==========================================================================
// L4 — bells at the scene boundaries (aligned to film.html's phase clock).
// ==========================================================================
{
  const P = [
    [2.0, TONIC * 3 / 2, 0.11],    // title / first press
    [15.0, TONIC * 9 / 8, 0.09],   // the rule
    [34.0, TONIC * 6 / 5, 0.12],   // the quiet pattern (the heart)
    [68.0, TONIC * 2, 0.10],       // the one number d
    [86.0, TONIC * 3 / 2, 0.11],   // glue the board — the twist
    [120.0, TONIC * 9 / 5, 0.10],  // the census with holes
    [148.0, TONIC * 2, 0.12],      // the parity finding
    [162.0, TONIC * 3, 0.10],      // sign-off
  ];
  for (let i = 0; i < P.length; i++) strike(P[i][0], P[i][1], 3.6, P[i][2], i % 2 ? 0.14 : -0.14);
}

// ==========================================================================
// L5 — the breath (quiet noise bed).
// ==========================================================================
{
  const rnd = mul32(1998);   // 1998 — Anderson & Feil, Turning Lights Out with Linear Algebra
  let lp = 0;
  for (let i = 0; i < N; i++) {
    const t = i / SR, nz = rnd() * 2 - 1; lp = lp * 0.96 + nz * 0.04;
    const env = Math.min(1, t / 8) * Math.min(1, (DUR - t) / 5);
    const lfo = 0.5 + 0.5 * Math.sin(TPI * 0.05 * t);
    const a = 0.010 * env * (0.5 + 0.5 * lfo);
    L[i] += a * lp; R[i] += a * lp * 0.92;
  }
}

// ---------- soft limiter ----------
let peak = 0;
for (let i = 0; i < N; i++) { L[i] = Math.tanh(L[i] * 1.05); R[i] = Math.tanh(R[i] * 1.05); peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i])); }

writeWav(new URL('./audio.wav', import.meta.url).pathname, L, R);

writeFileSync(new URL('./audio-trace.json', import.meta.url).pathname, JSON.stringify({
  DUR, NWALK, DMAX, peak, twistBells, oddNs,
  cylinderParityOdd: oddNs,
}, null, 1));

console.log(`wrote audio.wav (${DUR}s, 44.1kHz stereo) — peak ${peak.toFixed(3)}`);
console.log(`  walked ${NWALK} boards; ${twistBells} twist bells on odd d(n) at n = ${oddNs.join(', ')}`);
