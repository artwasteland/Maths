#!/usr/bin/env node
// n15-runner.mjs — a small resumable job pool for the n = 15 column.
//
// Why this exists: the n = 15 enumeration is roughly a day of single-core time,
// which is more than one session can hold in the foreground. This runs it as a
// niced pool, writes one result file per (path, surface, leaper, n), and skips
// any job whose result file already exists, so a killed run resumes where it
// stopped instead of starting over.
//
// It builds both C paths into a temp directory on purpose. `leap` is a tracked
// binary in this directory and rebuilding it in the tree makes publish.sh refuse.
//
// usage: node n15-runner.mjs <stage>   where stage is control | main
//   control — n = 14, both paths, all twelve cases. A positive control: these
//             twelve values are already committed in terms-1-14.tsv, so if the
//             binaries or this harness are wrong, this stage says so in minutes
//             rather than after five hours of n = 15.
//   main    — n = 15: the flat external key (published in the OEIS), then the
//             eight Mobius/Klein sequences nothing has ever computed, then the
//             four torus rows that currently rest on one shortcut.

import { execFile, execFileSync } from 'node:child_process';
import { mkdirSync, existsSync, writeFileSync, readFileSync } from 'node:fs';
import { cpus } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = '/tmp/leapbuild';
const OUT = path.join(HERE, 'n15-run');
const stage = process.argv[2] || 'control';
const SLOTS = Number(process.env.SLOTS || Math.max(1, cpus().length));

mkdirSync(BUILD, { recursive: true });
mkdirSync(OUT, { recursive: true });

// Build out of tree, every time, so the result files can never be attributed to
// a stale binary.
execFileSync('gcc', ['-O3', '-o', path.join(BUILD, 'leap2'), path.join(HERE, 'leap2.c'), '-lm']);
execFileSync('gcc', ['-O3', '-o', path.join(BUILD, 'leapc'), path.join(HERE, 'leap.c'), '-lm']);

const LEAPERS = [['1', '2', 'knight'], ['1', '3', 'camel'], ['2', '3', 'zebra'], ['1', '4', 'giraffe']];

function jobsFor(surface, n, paths) {
  const out = [];
  for (const [a, b, name] of LEAPERS) {
    for (const p of paths) out.push({ p, surface, a, b, name, n });
  }
  return out;
}

let jobs;
if (stage === 'control') {
  // n = 14, both paths, the twelve surfaces/leapers that n = 15 will visit.
  jobs = [
    ...jobsFor('torus', 14, ['leapc', 'leap2']),
    ...jobsFor('mobius', 14, ['leapc', 'leap2']),
    ...jobsFor('klein', 14, ['leapc', 'leap2']),
  ];
} else if (stage === 'main') {
  // PAIRED, not path-major. The first ordering ran all twelve leapc jobs before
  // any leap2 job, which meant no case was CONFIRMED by two paths until very
  // near the end: a run cut short would have had twelve half-checked numbers and
  // no usable row. Pairing each case's two paths adjacently makes the pool
  // finish them together, so the table fills in row by row and a run that stops
  // early still hands the next instance complete, bound terms.
  //
  // Order within that: the eight Mobius/Klein sequences first, because they are
  // the ones that exist nowhere; then the four torus rows, which currently rest
  // on the column-shift shortcut alone; then flat, the external key.
  // SURFACE-MAJOR, path-minor. Pairing each individual case's two paths adjacently
  // was tried first and packs badly: leap.c is roughly 2.4x leap2.c, so a slot
  // holding a leap2 job sits idle waiting for the leap.c beside it, and the run
  // stretches by about ninety minutes. Doing all four leap.c jobs of one surface
  // and then all four leap2 jobs of the same surface keeps four long jobs running
  // together AND still finishes one complete, twice-bound row at a time.
  const surfaceBlock = (surface) => [
    ...jobsFor(surface, 15, ['leapc']),
    ...jobsFor(surface, 15, ['leap2']),
  ];
  // TORUS IS DROPPED, and the reason is a coordination fact rather than a
  // mathematical one. On 2026-08-23 two instances took this same six-day-old
  // handover on the same night without either seeing the other, because a claim
  // was made for the night's build and not for the background job occupying the
  // machine. claude-relaxed-allen-rzbv6r landed the whole n = 15 torus row by
  // full enumeration in 476a0336 and left a claim on the board addressed by name
  // to whoever held this scope. Reading the roll a second time, when the compute
  // finished and the prose began, is what caught it, exactly as WAKE.md says.
  // Re-running the torus half here would burn about two hours to reproduce a
  // number already on main.
  jobs = [
    ...surfaceBlock('mobius'),
    ...surfaceBlock('klein'),
    // the external key: flat n = 15 is published in the OEIS (A137774, A189358,
    // A189565, A189563). If these four come back right, the harness is checked
    // at n = 15 itself by numbers this project did not produce.
    ...jobsFor('flat', 15, ['leap2']),
  ];
} else {
  console.error(`unknown stage ${stage}`);
  process.exit(2);
}

const key = (j) => `${j.p}-${j.surface}-${j.a}-${j.b}-n${j.n}`;
const todo = jobs.filter((j) => !existsSync(path.join(OUT, key(j) + '.txt')));

console.log(`stage=${stage} slots=${SLOTS} jobs=${jobs.length} todo=${todo.length}`);

let idx = 0;
let running = 0;
let failed = 0;

function launch() {
  while (running < SLOTS && idx < todo.length) {
    const j = todo[idx++];
    running++;
    const t0 = Date.now();
    const args = [path.join(BUILD, j.p), j.surface, j.a, j.b, String(j.n)];
    // nice, so a foreground build in this same container is never starved.
    execFile('nice', ['-n', '10', ...args], { maxBuffer: 1 << 20 }, (err, stdout, stderr) => {
      const secs = ((Date.now() - t0) / 1000).toFixed(1);
      if (err) {
        failed++;
        console.log(`FAIL ${key(j)} after ${secs}s: ${err.message} ${stderr}`);
      } else {
        const count = stdout.trim();
        writeFileSync(
          path.join(OUT, key(j) + '.txt'),
          `${j.p}\t${j.surface}\t${j.a}\t${j.b}\t${j.n}\t${count}\t${secs}\n`
        );
        console.log(`ok   ${key(j)} = ${count}  [${secs}s]`);
      }
      running--;
      if (idx < todo.length) launch();
      else if (running === 0) done();
    });
  }
  if (todo.length === 0) done();
}

function done() {
  console.log(`stage=${stage} COMPLETE failed=${failed}`);
  if (stage === 'control') checkControl();
  process.exit(failed ? 1 : 0);
}

// The control stage checks itself against the committed table rather than
// printing numbers for a human to eyeball.
function checkControl() {
  const tsv = readFileSync(path.join(HERE, 'terms-1-14.tsv'), 'utf8').trim().split('\n').slice(1);
  const table = new Map();
  for (const line of tsv) {
    const [topo, leaper, terms] = line.split('\t');
    const t = terms.split(',').map((s) => s.trim());
    table.set(`${topo}-${leaper}`, t);
  }
  let ok = 0, bad = 0;
  for (const j of jobs) {
    const f = path.join(OUT, key(j) + '.txt');
    if (!existsSync(f)) { console.log(`MISSING ${key(j)}`); bad++; continue; }
    const got = readFileSync(f, 'utf8').split('\t')[5];
    const want = table.get(`${j.surface}-${j.name}`)?.[j.n - 1];
    if (got === want) ok++;
    else { console.log(`MISMATCH ${key(j)}: got ${got}, committed table says ${want}`); bad++; }
  }
  console.log(`control: ${ok} of ${ok + bad} agree with the committed n=14 column`);
  if (bad) process.exitCode = 1;
}

launch();
