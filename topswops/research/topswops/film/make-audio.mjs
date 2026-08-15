#!/usr/bin/env node
// make-audio.mjs — the audio track for THE TOPSWOPS MACHINE companion film.
// 150 seconds, 44.1 kHz, stereo, fully deterministic.
//
// Mode: a 5-limit just-intonation MAJOR scale over C3 = 130.81 Hz — bright but
// resolving, fitting a one-rule game whose every deal ends, sorted, on the ace.
// Card value c ∈ 1..7 maps to scale degree c, so card 1 (the ace) = the tonic.
//
// HONEST NOTE (kept in code, NOT asserted on screen): the film makes claims
// about the cards and the counts; it does NOT claim the music "is" the maths.
// Two craft mappings are declared here, both read from the stratum's own engine
// (../engine.mjs), not invented:
//
//   • THE MELODY IS THE LONGEST GAME. We take the deck [4,7,6,2,1,5,3] — which
//     the engine confirms lasts 16 flips, the maximum for 7 cards (OEIS A000375)
//     — and play, at each flip, the card the machine reads off the top, pitched
//     to its scale degree. The tune literally traces the game and RESOLVES to
//     the tonic the instant the ace surfaces. (The film's centre draws this same
//     game in step.)
//   • THE PULSE WALKS THAT GAME ON A LOOP. A beat lands HARD on a big reversal
//     — when the card read off the top is 4 or more — and soft otherwise. So the
//     channel's rhythm is a real fingerprint of the longest topswops game.
//
//   L1 · drone   — tonic / fifth / octave sine bed, slow detune shimmer
//   L2 · pulse   — tabla-like thumb; accent schedule = the longest game, looped
//   L3 · bells   — struck additive tones at the film's phase boundaries
//   L4 · melody  — plucked card-notes through the centre cascade (the longest game)
//   L5 · pad     — harmonic swell under the Garden-of-Eden reveal
//   L6 · breath  — quiet wide pink-ish noise for humanity
//
// Output: research/topswops/film/audio.wav

import { writeFileSync } from 'node:fs';
import { flips, statsFull } from '../engine.mjs';

const SR = 44100, DUR = 150, N = SR * DUR, TONIC = 130.81, TPI = Math.PI * 2;

/* ---------- WAV writer (verbatim from the house pattern) ---------- */
function writeWav(filename, L, R) {
  const n = L.length, dataSize = n * 4;
  const buf = Buffer.alloc(44 + dataSize);
  buf.write('RIFF',0); buf.writeUInt32LE(36+dataSize,4); buf.write('WAVE',8);
  buf.write('fmt ',12); buf.writeUInt32LE(16,16); buf.writeUInt16LE(1,20);
  buf.writeUInt16LE(2,22); buf.writeUInt32LE(SR,24); buf.writeUInt32LE(SR*4,28);
  buf.writeUInt16LE(4,32); buf.writeUInt16LE(16,34);
  buf.write('data',36); buf.writeUInt32LE(dataSize,40);
  for (let i=0;i<n;i++){
    const lo=Math.max(-1,Math.min(1,L[i])), ro=Math.max(-1,Math.min(1,R[i]));
    buf.writeInt16LE(Math.round(lo*32767), 44+i*4);
    buf.writeInt16LE(Math.round(ro*32767), 44+i*4+2);
  }
  writeFileSync(filename, buf);
}

/* ---------- 5-limit just major; card c (1..7) -> degree c ---------- */
const MAJOR = [1/1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8, 2/1];   // index 0..7 (degrees 1..8)
function cardHz(c, oct = 1) { return TONIC * MAJOR[Math.max(0, Math.min(7, c - 1))] * oct; }

/* ---------- mulberry32 ---------- */
function mul32(seed){ let s=seed>>>0; return ()=>{ s=(s+0x6D2B79F5)>>>0; let t=s; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296; }; }

/* ---------- the longest 7-card game, read off the engine ---------- */
const DECK0 = [4, 7, 6, 2, 1, 5, 3];            // engine: flips(DECK0) = 16 = M(7) (A000375)
function topsRead(deck) {                         // the card read off the top at each flip
  const a = deck.slice(), tops = [];
  while (a[0] !== 1) { const k = a[0]; tops.push(k); let i=0,j=k-1; while(i<j){const t=a[i];a[i]=a[j];a[j]=t;i++;j--;} }
  return tops;
}
const M7 = statsFull(7).M;
if (flips(DECK0) !== 16 || M7 !== 16) throw new Error('engine drift: DECK0 must last M(7)=16 flips');
const TOPS = topsRead(DECK0);                     // [4,2,6,5,2,7,3,5,4,6,2,5,3,4,2,3]

const L=new Float32Array(N), R=new Float32Array(N);

/* ===== L1 · drone ===== */
{
  const fs=[TONIC, TONIC*3/2, TONIC*2], amps=[1,0.5,0.34], ph=[0,0,0];
  for(let i=0;i<N;i++){
    const t=i/SR;
    const lfo=1+0.003*Math.sin(TPI*0.08*t);
    const env=Math.min(1,t/6)*Math.min(1,(DUR-t)/5);
    for(let k=0;k<3;k++){
      ph[k]+=(TPI*fs[k]*(k===1?1/lfo:lfo))/SR;
      const a=0.150*amps[k]*env;
      L[i]+=a*Math.sin(ph[k]+k*0.02);
      R[i]+=a*Math.sin(ph[k]-k*0.02);
    }
  }
}

/* ===== L2 · pulse — accents = the longest game, looped (big reversal = loud) ===== */
{
  const BPM=66, beatN=Math.floor(DUR*BPM/60);
  for(let b=0;b<beatN;b++){
    const k = TOPS[b % TOPS.length];               // the card read at this looping step
    const loud = k >= 4;                            // a big reversal
    const t0=b*60/BPM, i0=Math.floor(t0*SR), len=Math.floor(0.18*SR);
    const amp=(loud?0.30:0.10)*(b<4?b/4:1)*Math.min(1,(DUR-t0)/3);
    let phase=0;
    for(let kk=0;kk<len && i0+kk<N;kk++){
      const tau=kk/SR;
      const f=110*Math.exp(-tau/0.04)+40*(1-Math.exp(-tau/0.04));
      phase+=TPI*f/SR;
      const env=Math.exp(-tau/0.055);
      const s=amp*env*(Math.sin(phase)+0.3*Math.sin(phase*1.5));
      L[i0+kk]+=s*0.9; R[i0+kk]+=s*0.9;
    }
  }
}

/* ===== L3 · bells at the phase boundaries ===== */
{
  // film phase starts: title, rule, cascade, stops, histogram, garden, table, close
  const PHASES=[0,11,25,66,80,104,127,145];
  const CARD  =[5, 3,  4,  1,  5,  3,  6,  1];      // degree picked per phase; close = ace=tonic
  const GARDEN=5;                                   // the garden reveal bell (t=104), octave + louder
  const PART=[1,2,3,4], PAMP=[1.0,0.5,0.3,0.16];
  for(let p=0;p<PHASES.length;p++){
    const t0=PHASES[p], f0=cardHz(CARD[p], p===GARDEN?2:1);
    const i0=Math.floor(t0*SR), len=Math.floor(3.5*SR);
    for(let k=0;k<len && i0+k<N;k++){
      const tau=k/SR, env=Math.exp(-tau/1.25);
      let s=0; for(let h=0;h<PART.length;h++) s+=PAMP[h]*Math.sin(TPI*f0*PART[h]*tau);
      const amp=0.115*env*(p===GARDEN?1.3:1.0);
      L[i0+k]+=amp*s*(1-0.12*(p%2)); R[i0+k]+=amp*s*(1+0.12*(p%2));
    }
  }
}

/* ===== L4 · melody — the longest game plays through the centre cascade ===== */
{
  // The film deals the cards in over [25,27], then takes one flip every 2.25 s.
  // Play the card read at each flip, then resolve to the ace (tonic) when it surfaces.
  const T_FIRST = 27.0, DT = 2.25;
  function pluck(t0, f, gain) {
    const i0=Math.floor(t0*SR), len=Math.floor(1.4*SR);
    let ph=0, ph2=0;
    for(let k=0;k<len && i0+k>=0 && i0+k<N;k++){
      const tau=k/SR;
      const env=Math.exp(-tau/0.55)*Math.min(1,tau/0.006);
      ph+=TPI*f/SR; ph2+=TPI*f*2/SR;
      const s=gain*env*(Math.sin(ph)+0.32*Math.sin(ph2));
      L[i0+k]+=s; R[i0+k]+=s;
    }
  }
  for(let i=0;i<TOPS.length;i++){
    const t0 = T_FIRST + i*DT;
    pluck(t0, cardHz(TOPS[i], 2), 0.085);          // top-octave card-note at each flip
  }
  // the ace surfaces just after the last flip — resolve, low and warm
  pluck(T_FIRST + TOPS.length*DT, cardHz(1, 1), 0.11);
  pluck(T_FIRST + TOPS.length*DT, cardHz(1, 2), 0.07);
}

/* ===== L5 · pad — harmonic swell under the Garden-of-Eden reveal ===== */
{
  const T0=105, T1=126, PADS=[TONIC,TONIC*2,TONIC*3,TONIC*4,TONIC*5,TONIC*6], OFF=[0,0.1,0.5,0.3,0.7,0.2];
  for(let h=0;h<PADS.length;h++){
    for(let i=Math.floor(T0*SR); i<Math.floor(T1*SR) && i<N; i++){
      const t=i/SR;
      const env=Math.min(1,(t-T0)/4)*Math.min(1,(T1-t)/4);
      if(env<=0) continue;
      const lfo=1+0.002*Math.sin(TPI*0.08*t+h);
      const s=0.040*env*Math.sin(TPI*PADS[h]*lfo*t+OFF[h])/(1+h*0.6);
      L[i]+=s*(h%2===0?1:0.7); R[i]+=s*(h%2===0?0.7:1);
    }
  }
}

/* ===== L6 · breath ===== */
{
  const rnd=mul32(2718); let lp=0;
  for(let i=0;i<N;i++){
    const t=i/SR, n=rnd()*2-1;
    lp=lp*0.96+n*0.04;
    const env=Math.min(1,t/8)*Math.min(1,(DUR-t)/5);
    const lfo=0.5+0.5*Math.sin(TPI*0.06*t);
    const a=0.011*env*(0.5+0.5*lfo);
    L[i]+=a*lp; R[i]+=a*lp*0.92;
  }
}

/* ---------- soft limiter ---------- */
for(let i=0;i<N;i++){ L[i]=Math.tanh(L[i]*1.06); R[i]=Math.tanh(R[i]*1.06); }

writeWav(new URL('./audio.wav', import.meta.url).pathname, L, R);
const loud = TOPS.filter(k=>k>=4).length;
console.log(`wrote audio.wav (${DUR}s, 44.1kHz stereo) — melody = the 16-flip longest game; ${loud}/${TOPS.length} flips are big reversals (loud beats).`);
