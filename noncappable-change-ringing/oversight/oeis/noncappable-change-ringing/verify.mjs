// verify.mjs: the checked floor under the six noncappable sequences.
//
// Run:  node verify.mjs        (~80 s here under nice -n 19)
//
// Establishes, by an independent DFS counter (engine.mjs) re-derived from
// Sønsteby's transition rules:
//   1. We reproduce the published cyclic and path OEIS sequences exactly,
//      as far as the counter can run on this machine:
//        n=4: A324942 + A324943  (FULL, all 24 terms)
//        n=5: A324944 + A324945  (first 12 terms)
//        n=6: A324946 + A324947  (first 9 terms)
//        n=7: A324948 + A324949  (first 7 terms)
//        n=8: A324950 + A324951  (first 6 terms)
//        n=9: A324952 + A324953  (first 5 terms)
//   2. The published path/cyclic pairs satisfy path = cyclic + noncappable
//      term by term, and noncappable >= 0 with noncappable(1)=noncappable(2)=0.
//   3. Directly counted and path-minus-cyclic noncappable terms agree at every
//      computed level.
//   4. Every staged b-file term agrees with the published prefix or the
//      committed finished-run extension table, with exact mutual coverage.
//   5. The published term counts are what we recorded them to be, so an entry
//      that grows or is truncated in the catalogue cannot silently change the
//      length of a staged b-file.
//
// What this does NOT establish, said plainly because the 2026-07-20 coverage
// audit found this exact sentence overclaimed here: beyond the depths in (1)
// the noncappable terms are a subtraction, not a second count. Within the
// published range the two sides being subtracted are Sønsteby's; past it they
// are the extension counter's, and check (4) compares the b-file against a
// provenance table naming the run that produced each one. That catches
// truncation and transcription drift. It is not a recomputation.

import fs from 'node:fs';
import { countByLength } from './engine.mjs';
import { DATA, ENGINE_REACH, PUBLISHED_TERMS, BELLS, derivableLength } from './derive.mjs';
import { EXPECTED_EXTENSION } from './expected-extension.mjs';

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; }
  else { fail++; console.log(`  ✗ FAIL: ${name}`); }
}
function eqArr(name, got, want) {
  // compare BigInt array `got` (1-indexed, got[0] unused) against number[] `want`
  let ok = got.length - 1 >= want.length;
  for (let i = 0; i < want.length && ok; i++) ok = got[i + 1] === BigInt(want[i]);
  check(name, ok);
  if (!ok) console.log(`    got  ${got.slice(1, want.length + 1).map(String).join(',')}\n    want ${want.join(',')}`);
}

const REACH = ENGINE_REACH;

for (const n of BELLS) {
  const { cyclic, path, noncappable, noncappableDirect } = countByLength(n, REACH[n]);
  const D = DATA[n];
  // 1. reproduce published cyclic & path prefixes
  eqArr(`n=${n} cyclic reproduces ${D.cyclic}`, cyclic, D.c.slice(0, REACH[n]));
  eqArr(`n=${n} path   reproduces ${D.path}`, path, D.p.slice(0, REACH[n]));
  // 3. direct DFS tally == derived tally == published path - cyclic
  let directOk = true;
  let publishedOk = true;
  for (let L = 1; L <= REACH[n]; L++) {
    const want = BigInt(D.p[L - 1]) - BigInt(D.c[L - 1]);
    if (noncappableDirect[L] !== noncappable[L]) directOk = false;
    if (noncappable[L] !== want) publishedOk = false;
  }
  check(`n=${n} direct noncappable matches derived on all computed L`, directOk);
  check(`n=${n} noncappable matches published difference on all computed L`, publishedOk);
}

// 2. published-data internal consistency for the FULL term lists
for (const n of BELLS) {
  const D = DATA[n];
  const want = PUBLISHED_TERMS[n];
  check(
    `n=${n} published term counts are ${want.cyclic}/${want.path} as catalogued`,
    D.c.length === want.cyclic && D.p.length === want.path,
  );
  let ok = true;
  for (let i = 0; i < derivableLength(n); i++) {
    const nc = BigInt(D.p[i]) - BigInt(D.c[i]);
    if (nc < 0n) ok = false;
    if (i === 0 && nc !== 0n) ok = false; // L=1
    if (i === 1 && nc !== 0n) ok = false; // L=2
  }
  check(`n=${n} noncappable = path-cyclic is >=0 and 0 at L=1,2`, ok);
}

function readBFile(n) {
  const text = fs.readFileSync(new URL(`./b-bells${n}.txt`, import.meta.url), 'utf8');
  const terms = new Map();
  let formatOk = true;
  for (const line of text.split(/\r?\n/)) {
    if (line === '') continue;
    const match = /^(\d+) (\d+)$/.exec(line);
    if (!match) { formatOk = false; continue; }
    const L = Number(match[1]);
    if (terms.has(L)) formatOk = false;
    terms.set(L, BigInt(match[2]));
  }
  check(`n=${n} b-file has valid unique index-value lines`, formatOk);
  return terms;
}

// 4. staged b-files exactly cover the published prefix and expected extension.
for (const n of BELLS) {
  const D = DATA[n];
  const terms = readBFile(n);
  const extension = EXPECTED_EXTENSION[n] || new Map();
  const expected = new Map();
  for (let L = 1; L <= derivableLength(n); L++) {
    expected.set(L, BigInt(D.p[L - 1]) - BigInt(D.c[L - 1]));
  }
  for (const [L, value] of extension) expected.set(L, value);

  let valuesOk = true;
  for (const [L, value] of expected) {
    if (terms.get(L) !== value) valuesOk = false;
  }
  check(`n=${n} b-file values match published prefix and expected extension`, valuesOk);

  const coverageOk = terms.size === expected.size
    && [...terms.keys()].every((L) => expected.has(L));
  check(`n=${n} b-file and expected tables have exact mutual coverage`, coverageOk);
}

console.log(`\n${pass}/${pass + fail} checks pass${fail ? ` (${fail} FAILED)` : ''}.`);
process.exit(fail ? 1 : 0);
