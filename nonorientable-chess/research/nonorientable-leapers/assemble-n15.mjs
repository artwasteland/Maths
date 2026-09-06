#!/usr/bin/env node
// assemble-n15.mjs -- turn the n = 15 run directory into the table, and say
// honestly how much of it is bound.
//
// Safe to run at any point during the run: it reports what is complete, what is
// half-done, and what has not started, and it only WRITES terms-1-15.tsv and the
// staged b-files when every case it would write is confirmed by two independent
// paths. Nothing here believes a single path.
//
//   node assemble-n15.mjs            report only
//   node assemble-n15.mjs --apply    also write terms-1-15.tsv and the b-files

import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, 'n15-run');
const APPLY = process.argv.includes('--apply');

const LEAPERS = [['1', '2', 'knight'], ['1', '3', 'camel'], ['2', '3', 'zebra'], ['1', '4', 'giraffe']];
const SURFACES = ['flat', 'torus', 'mobius', 'klein'];

// ---- read the run directory -------------------------------------------------
const got = new Map();   // "path|surface|a|b|n" -> {count, secs}
for (const f of existsSync(RUN) ? readdirSync(RUN) : []) {
  if (!f.endsWith('.txt')) continue;
  const [p, surface, a, b, n, count, secs] = readFileSync(path.join(RUN, f), 'utf8').trim().split('\t');
  got.set(`${p}|${surface}|${a}|${b}|${n}`, { count, secs: Number(secs) });
}

// ---- the committed table ----------------------------------------------------
const tsvPath = path.join(HERE, 'terms-1-14.tsv');
const table = new Map();
for (const line of readFileSync(tsvPath, 'utf8').trim().split('\n').slice(1)) {
  const [topo, leaper, terms] = line.split('\t');
  table.set(`${topo}-${leaper}`, terms.split(',').map((s) => s.trim()));
}

// ---- the pre-registered external key ----------------------------------------
const key = JSON.parse(readFileSync(path.join(HERE, 'external-key-n15.json'), 'utf8'));

// ---- the torus row, computed by another instance the same night -------------
// Not re-enumerated here: claude-relaxed-allen-rzbv6r landed it by both full
// paths, and this session confirmed all four by the column-shift shortcut in 473
// seconds rather than duplicating two hours of enumeration. The provenance file
// records which route came from where; nothing is retyped from a commit message.
const torusProv = JSON.parse(readFileSync(path.join(HERE, 'torus-n15-provenance.json'), 'utf8'));

// ---- reconcile --------------------------------------------------------------
const rows = [];
let complete = 0, half = 0, none = 0, disagree = 0;
const problems = [];

for (const surface of SURFACES) {
  for (const [a, b, name] of LEAPERS) {
    const c = got.get(`leapc|${surface}|${a}|${b}|15`);
    const d = got.get(`leap2|${surface}|${a}|${b}|15`);
    const paths = [c && ['leap.c', c], d && ['leap2.c', d]].filter(Boolean);
    let state, value = null;
    if (paths.length === 2) {
      if (c.count === d.count) { state = 'BOUND (two paths)'; value = c.count; complete++; }
      else { state = 'DISAGREE'; disagree++; problems.push(`${surface} ${name}: leap.c ${c.count} vs leap2.c ${d.count}`); }
    } else if (paths.length === 1) {
      state = `one path only (${paths[0][0]})`; value = paths[0][1].count; half++;
    } else if (surface === 'torus') {
      state = 'BOUND (peer, 3 routes)'; value = torusProv.row[name]; complete++;
    } else { state = 'not run'; none++; }
    rows.push({ surface, name, a, b, state, value,
      secs: paths.map(([n2, r]) => `${n2} ${(r.secs / 60).toFixed(1)}m`).join(', ') });
  }
}

console.log('n = 15, case by case\n');
for (const r of rows) {
  console.log(`  ${r.surface.padEnd(7)} ${r.name.padEnd(8)} ${(r.value ?? '').toString().padStart(14)}  ${r.state.padEnd(20)} ${r.secs}`);
}
console.log(`\n  bound by two paths ${complete} · one path only ${half} · not run ${none} · DISAGREEING ${disagree}`);
if (problems.length) { console.log('\nPROBLEMS:'); problems.forEach((p) => console.log('  ' + p)); }

// ---- the external key -------------------------------------------------------
console.log('\nexternal key, flat n = 15 against the OEIS (fetched before the run returned):');
let keyChecked = 0, keyBad = 0;
for (const [a, b, name] of LEAPERS) {
  const want = key.n15_expected[name].value;
  const c = got.get(`leapc|flat|${a}|${b}|15`), d = got.get(`leap2|flat|${a}|${b}|15`);
  const mine = (c || d)?.count;
  if (!mine) { console.log(`  ${name.padEnd(8)} ${key.n15_expected[name].oeis}  not run yet, want ${Number(want).toLocaleString('en-US')}`); continue; }
  keyChecked++;
  const okv = mine === want;
  if (!okv) keyBad++;
  console.log(`  ${name.padEnd(8)} ${key.n15_expected[name].oeis}  ours ${Number(mine).toLocaleString('en-US')}  published ${Number(want).toLocaleString('en-US')}  ${okv ? 'MATCH' : '*** MISMATCH ***'}`);
}
if (keyChecked) console.log(`  ${keyChecked - keyBad} of ${keyChecked} match`);

// ---- score the blind predictions -------------------------------------------
// PREDICTED-N15.md, filed 2026-08-20 before any of these existed. The eight
// Mobius/Klein rows are blind; the four torus rows are not and the file says so.
const PRED = {
  'mobius-knight': 25269523823, 'mobius-camel': 26124295977,
  'mobius-zebra': 31083857079, 'mobius-giraffe': 30474035008,
  'klein-knight': 16789829702, 'klein-camel': 14935667527,
  'klein-zebra': 14820718528, 'klein-giraffe': 14634251035,
};
console.log('\nthe blind predictions of PREDICTED-N15.md (filed 2026-08-20, kill threshold 3%):');
const errs = [];
for (const r of rows) {
  if (r.surface !== 'mobius' && r.surface !== 'klein') continue;
  if (!r.value) { console.log(`  ${r.surface.padEnd(7)} ${r.name.padEnd(8)} not run`); continue; }
  const bound = r.state.startsWith('BOUND');
  const p = PRED[`${r.surface}-${r.name}`];
  const err = (p - Number(r.value)) / Number(r.value) * 100;
  // A one-path count is reported, and labelled, but does NOT go into the score.
  // The directory's rule is that no term counts until two implementations that
  // share no code agree, and a median taken over provisional numbers would be a
  // headline resting on half a check.
  if (bound) errs.push(Math.abs(err));
  console.log(`  ${r.surface.padEnd(7)} ${r.name.padEnd(8)} predicted ${p.toLocaleString('en-US').padStart(14)}  actual ${Number(r.value).toLocaleString('en-US').padStart(14)}  ${err >= 0 ? '+' : ''}${err.toFixed(3)}%${Math.abs(err) > 3 ? '  *** OVER THE 3% KILL THRESHOLD ***' : ''}${bound ? '' : '   [PROVISIONAL, one path]'}`);
}
if (errs.length) {
  errs.sort((x, y) => x - y);
  const med = errs.length % 2 ? errs[(errs.length - 1) / 2] : (errs[errs.length / 2 - 1] + errs[errs.length / 2]) / 2;
  console.log(`  ${errs.length} of 8 scored: median |error| ${med.toFixed(3)}%, worst ${errs[errs.length - 1].toFixed(3)}%`);
}

// ---- write, only if everything that would be written is bound ---------------
// The flat row is REQUIRED here, not optional. An earlier version of this file
// let it fall back to the OEIS value if no flat job had run, which would have put
// a number this project did not compute into terms-1-15.tsv looking exactly like
// the fifteen beside it that it did. The published values are the KEY the
// computed row is checked against; they are not a substitute for computing it.
const needed = rows;
const allBound = needed.every((r) => r.state.startsWith('BOUND') || (r.surface === 'flat' && r.value));
if (!APPLY) {
  console.log(`\n(report only. ${allBound ? 'Every torus/Mobius/Klein case is bound: --apply would write the table.' : 'Not writing: ' + needed.filter((r) => !r.state.startsWith('BOUND')).length + ' case(s) are not yet bound by two paths.'})`);
  process.exit(disagree || keyBad ? 1 : 0);
}
if (!allBound) { console.log('\nrefusing to write: not every case is bound by two independent paths.'); process.exit(1); }
if (disagree || keyBad) { console.log('\nrefusing to write: a disagreement is outstanding.'); process.exit(1); }

// terms-1-15.tsv
const out = ['topo\tleaper\tterms(n=1..15)'];
for (const surface of SURFACES) {
  for (const [a, b, name] of LEAPERS) {
    const prev = table.get(`${surface}-${name}`);
    if (!prev) throw new Error(`terms-1-14.tsv has no ${surface} ${name}`);
    const r = rows.find((x) => x.surface === surface && x.name === name);
    const fifteenth = r.value;
    if (!fifteenth) throw new Error(`no n=15 term for ${surface} ${name}`);
    out.push(`${surface}\t${name}\t${prev.join(', ')}, ${fifteenth}`);
  }
}
writeFileSync(path.join(HERE, 'terms-1-15.tsv'), out.join('\n') + '\n');
console.log('\nwrote terms-1-15.tsv');

// staged b-files
const STAGE = path.resolve(HERE, '..', '..', 'oversight', 'oeis', 'nonorientable-leapers');
for (const surface of ['mobius', 'klein']) {
  for (const [a, b, name] of LEAPERS) {
    const f = path.join(STAGE, `b-${surface}-${name}.txt`);
    const lines = readFileSync(f, 'utf8').trim().split('\n');
    const last = Number(lines[lines.length - 1].split(' ')[0]);
    const r = rows.find((x) => x.surface === surface && x.name === name);
    if (last === 15) { lines[lines.length - 1] = `15 ${r.value}`; }
    else if (last === 14) { lines.push(`15 ${r.value}`); }
    else throw new Error(`${f} ends at n=${last}, expected 14 or 15`);
    writeFileSync(f, lines.join('\n') + '\n');
    console.log(`  ${path.basename(f)}: 15 terms`);
  }
}
console.log('\nnow: node oversight/oeis/nonorientable-leapers/verify-staged.mjs');
