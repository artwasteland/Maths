// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// Rewrites b-file.txt for the Topswops total-flips sequence from the engine.
// Reproducible:  node oversight/oeis/topswops-total-flips/derive.mjs 13
//
// NMAX defaults to 11 (about 9 s cumulative). Measured 2026-07-27 on Node
// v22.22.2: cumulative wall time for n=1..10 is 0.7 s, n=1..11 is 9.1 s,
// n=1..12 is 107.8 s. n=13 is roughly thirteen times the n=12 term on its own.
//
// THE B-FILE STAGES 13 TERMS, so `derive.mjs` with anything less than 13 will
// NOT reproduce the staged artifact, and is REFUSED rather than allowed to
// shrink it. See the guard below.
//
// WHY THE GUARD EXISTS. This script writes b-file.txt from scratch for
// n=1..NMAX. Until 2026-07-27 the bundle's own printed instructions disagreed
// with each other about NMAX: README.md said 13, while draft.txt and
// .zenodo.json said 12. Following either of the latter would have silently
// deleted the committed n=13 term, and no committed check read the b-file at
// n=13, so nothing would have gone red. The 2026-07-20 coverage audit flagged
// this (findings-2026-07-20.json, dir "topswops-total-flips"). The three
// instruction sites now all say 13, and this script will not truncate the file
// even if someone asks it to. There is deliberately no --force flag: removing a
// staged term is not something a reproduce command should be able to do by
// accident.

import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { maxAndSum } from '../../../research/topswops/engine.mjs';

// Count the term lines already in a b-file, ignoring comments and blanks.
// Returns null if there is no file yet (the first-ever run is not a shrink).
export function countExistingTerms(path) {
  if (!existsSync(path)) return null;
  let n = 0;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    n++;
  }
  return n;
}

// The guard, as a pure function so it can be tested without running the
// producer. Returns { ok: true } or { ok: false, message }. A run that would
// write FEWER terms than the file already holds is refused.
export function checkNoShrink(existingTerms, wouldWriteTerms, path = 'b-file.txt') {
  if (existingTerms === null) return { ok: true };
  if (wouldWriteTerms >= existingTerms) return { ok: true };
  return {
    ok: false,
    message:
      `REFUSING TO SHRINK ${path}.\n` +
      `  the file on disk holds ${existingTerms} terms; this run would write ${wouldWriteTerms}.\n` +
      `  Writing it would delete ${existingTerms - wouldWriteTerms} staged term(s) that no other\n` +
      `  committed check recomputes. Re-run with NMAX >= ${existingTerms}:\n` +
      `      node oversight/oeis/topswops-total-flips/derive.mjs ${existingTerms}\n` +
      `  If you genuinely intend to remove staged terms, edit the b-file deliberately\n` +
      `  and say why in the README. This script will not do it for you.`,
  };
}

// Only run the producer when this file is executed directly. Importing it (for
// example to test the guard) must not enumerate a single deck.
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];

if (isMain) {
  const NMAX = parseInt(process.argv[2] || '11', 10);
  const here = dirname(fileURLToPath(import.meta.url));
  const target = join(here, 'b-file.txt');

  // Check BEFORE spending the compute, not after.
  const existing = countExistingTerms(target);
  const verdict = checkNoShrink(existing, NMAX, target);
  if (!verdict.ok) {
    console.error(verdict.message);
    process.exit(1);
  }

  const lines = ['# Total Topswops steps summed over all n! starting decks of n cards.',
    '# Offset 1.  Reproduce:  node oversight/oeis/topswops-total-flips/derive.mjs ' + NMAX];
  const terms = [];
  for (let n = 1; n <= NMAX; n++) {
    const { sum } = maxAndSum(n);
    lines.push(`${n} ${sum.toString()}`);
    terms.push(sum.toString());
    console.error(`n=${n}\tSUM=${sum}`);
  }
  writeFileSync(target, lines.join('\n') + '\n');
  console.log('\nwrote b-file.txt  (' + terms.length + ' terms)');
  console.log('%S ' + terms.join(', '));
}
