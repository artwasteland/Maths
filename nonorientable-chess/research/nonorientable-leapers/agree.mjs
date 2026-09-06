// agree.mjs — do the four code paths actually agree, and OVER WHAT RANGE?
//
// WHY THIS FILE WAS REWRITTEN (2026-08-17)
// ---------------------------------------
// The old version of this file compared two enumerators over n = 1..8 and printed
// "PASS - two enumerators agree". Meanwhile the README and the published page both
// said the table was carried by THREE independent code paths, and the page said
// every number on it re-derives from the committed enumerators on every run. Both
// claims outran the file: nothing in the repository ever ran leap.c, and no check
// of any kind reached the terms above n = 8 — which are exactly the terms a reader
// cannot recompute by hand and the only ones that were ever in doubt.
//
// The census (oversight/oeis/CENSUS-2026-07-26.md) flagged this. It is not that the
// numbers were wrong; it is that the sentence describing how they were checked was
// larger than the check. This file now covers the whole published range, prints the
// range it actually covered next to every verdict, and refuses to say "agree"
// about an n it did not visit.
//
// THE FOUR PATHS, and how they are independent of each other
//   1. engine.mjs countPermutations     JS, BigInt cell mask, row-major DFS
//   2. engine.mjs countPermutationsAlt  JS, integer arrays, columns scanned descending
//   3. leap.c                           C, closed-form floor/modulo fold, adjacency list
//   4. leap2.c                          C, iterated deck generators, forward-propagated
//                                       column masks, most-constrained-row ordering
// The geometry underneath all four is checked from the opposite direction by
// lift-check.mjs, which unfolds instead of folding.
//
// USAGE
//   node agree.mjs                 fast tier: JS to n=10, C to n=12   (~2 min)
//   node agree.mjs --full          the whole published table          (slow; see README)
//   node agree.mjs --js 9 --c 13   pick the two ceilings yourself
//   node agree.mjs --selftest      prove the comparison can report a disagreement
//
// Exit code 0 only if every pair compared agreed AND the self-test fired.

import { execFileSync } from 'node:child_process';
import { existsSync, statSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { attackGraph, countPermutations, countPermutationsAlt, leaperVectors, LEAPERS } from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const TOPOS = ['flat', 'torus', 'mobius', 'klein'];

const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const num = (f, d) => { const i = argv.indexOf(f); return i >= 0 ? Number(argv[i + 1]) : d; };

const FULL = has('--full');
const JS_MAX = num('--js', FULL ? 11 : 10);
const C_MAX = num('--c', FULL ? 14 : 12);

// Build the C paths if they are missing or older than their source. gcc is on PATH
// in this environment; if it is not, install it rather than skipping the path --
// a skipped path is the failure mode this file exists to end.
//
// The binaries are built into a temp directory, NOT beside the source. `leap` is a
// tracked file in this repository, so compiling in place would rewrite a committed
// binary and leave the working tree dirty, which makes coordination/publish.sh
// refuse to land. A check that cannot be run before shipping is the same problem
// as a check that was never run.
function ensureC(stem, extra = []) {
  const src = join(HERE, `${stem}.c`);
  const outDir = join(tmpdir(), 'aw-leapers');
  mkdirSync(outDir, { recursive: true });
  const bin = join(outDir, stem);
  if (!existsSync(bin) || statSync(bin).mtimeMs < statSync(src).mtimeMs) {
    execFileSync('gcc', ['-O3', '-o', bin, src, ...extra], { stdio: 'inherit' });
  }
  return bin;
}

const LEAP = ensureC('leap', ['-lm']);
const LEAP2 = ensureC('leap2');

const runC = (bin, topo, a, b, n) =>
  Number(execFileSync(bin, [topo, String(a), String(b), String(n)], { encoding: 'utf8' }).trim());

// --------------------------------------------------------------------------
// The comparison. Every path is run over its own ceiling and the ceilings are
// reported, so a reader can see precisely which terms are covered by how many
// independent paths -- which is the thing the old file left to the imagination.
// --------------------------------------------------------------------------
function compare() {
  const disagreements = [];
  const coverage = new Map();      // n -> Set of path names that reached it
  const note = (n, path) => { if (!coverage.has(n)) coverage.set(n, new Set()); coverage.get(n).add(path); };
  let comparisons = 0;

  for (const topo of TOPOS) {
    for (const name of Object.keys(LEAPERS)) {
      const [a, b] = LEAPERS[name];
      const V = leaperVectors(a, b);
      const maxN = Math.max(JS_MAX, C_MAX);
      for (let n = 1; n <= maxN; n++) {
        const vals = {};
        if (n <= JS_MAX) {
          const g = attackGraph(topo, n, V);
          vals['engine:bitmask'] = countPermutations(g, n);
          vals['engine:colDFS'] = countPermutationsAlt(topo, n, V);
        }
        if (n <= C_MAX) {
          vals['leap.c'] = runC(LEAP, topo, a, b, n);
          vals['leap2.c'] = runC(LEAP2, topo, a, b, n);
        }
        const paths = Object.keys(vals);
        for (const p of paths) note(n, p);
        for (let i = 0; i < paths.length; i++)
          for (let j = i + 1; j < paths.length; j++) {
            comparisons++;
            if (vals[paths[i]] !== vals[paths[j]])
              disagreements.push(`${topo} ${name} n=${n}: ${paths[i]}=${vals[paths[i]]} vs ${paths[j]}=${vals[paths[j]]}`);
          }
      }
      process.stderr.write(`  ${topo} ${name} done\n`);
    }
  }
  return { disagreements, coverage, comparisons };
}

// --------------------------------------------------------------------------
// Positive control. A comparison that cannot report a disagreement is not
// evidence, and "0 disagreements" is byte-identical whether the check looked or
// not. So: hand two paths DIFFERENT leapers and require the comparison to fire.
// --------------------------------------------------------------------------
function selftest() {
  const g = attackGraph('mobius', 7, leaperVectors(1, 2));
  const wrong = countPermutations(g, 7);                       // knight
  const right = runC(LEAP2, 'mobius', 1, 3, 7);                // camel
  const fired = wrong !== right;
  console.log(`self-test: mobius n=7 knight=${wrong} vs camel=${right} -> comparison ${fired ? 'FIRES' : 'IS BLIND'}`);
  return fired;
}

if (has('--selftest')) {
  process.exit(selftest() ? 0 : 1);
}

const t0 = Date.now();
console.log(`agree.mjs — 4 topologies x 4 leapers; JS paths to n=${JS_MAX}, C paths to n=${C_MAX}`);
const { disagreements, coverage, comparisons } = compare();
const fired = selftest();
const secs = ((Date.now() - t0) / 1000).toFixed(1);

console.log('\ncoverage — how many independent paths reached each n:');
for (const n of [...coverage.keys()].sort((x, y) => x - y)) {
  const s = coverage.get(n);
  console.log(`  n=${String(n).padStart(2)}  ${s.size} paths  (${[...s].join(', ')})`);
}
console.log(`\n${comparisons} pairwise comparisons in ${secs}s`);

if (disagreements.length === 0 && fired) {
  console.log(`PASS — every path agrees everywhere it was run (n=1..${Math.max(JS_MAX, C_MAX)}), and the comparison is not blind`);
} else {
  for (const d of disagreements.slice(0, 20)) console.log('  DISAGREE ' + d);
  console.log(`FAILED — ${disagreements.length} disagreements${fired ? '' : '; AND the self-test did not fire'}`);
  process.exit(1);
}
