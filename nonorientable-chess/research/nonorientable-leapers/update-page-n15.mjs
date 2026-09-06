#!/usr/bin/env node
// update-page-n15.mjs -- carry terms-1-15.tsv into the shipped immersive page.
//
// The page holds the table as a literal `window.__LEAP_TABLE__` object, which is
// the right shape (a reader can read it) and the wrong shape (it can drift from
// the research table). It has drifted before in the other direction: its comment
// said "n=1..13" while the arrays already held fourteen terms.
//
// So this rewrites the block FROM the tsv rather than by hand, and refuses if the
// tsv is not the full sixteen rows of fifteen terms. verify-page.mjs then checks
// the page against the same tsv from a browser, which is the check that matters.
//
//   node update-page-n15.mjs [--apply]

import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PAGE = path.resolve(HERE, '..', '..', 'public', 'strata', 'leapers-on-a-mobius-strip', 'index.html');
const APPLY = process.argv.includes('--apply');

const rows = readFileSync(path.join(HERE, 'terms-1-15.tsv'), 'utf8').trim().split('\n').slice(1);
const table = new Map();
for (const line of rows) {
  const [topo, leaper, terms] = line.split('\t');
  table.set(`${topo}|${leaper}`, terms.split(',').map((s) => s.trim()));
}
if (table.size !== 16) throw new Error(`terms-1-15.tsv has ${table.size} rows, expected 16`);
for (const [k, v] of table) if (v.length !== 15) throw new Error(`${k} has ${v.length} terms, expected 15`);

const SURFACES = ['flat', 'torus', 'mobius', 'klein'];
const PIECES = ['knight', 'camel', 'zebra', 'giraffe'];

const lines = ['window.__LEAP_TABLE__={'];
SURFACES.forEach((s, si) => {
  lines.push(` ${s}:{`);
  PIECES.forEach((p, pi) => {
    lines.push(`  ${p}:[${table.get(`${s}|${p}`).join(',')}]${pi < PIECES.length - 1 ? ',' : ''}`);
  });
  lines.push(` }${si < SURFACES.length - 1 ? ',' : ''}`);
});
lines.push('};');
const block = lines.join('\n');

let html = readFileSync(PAGE, 'utf8');
const start = html.indexOf('window.__LEAP_TABLE__={');
if (start < 0) throw new Error('the page has no __LEAP_TABLE__ block');
const end = html.indexOf('\n};', start);
if (end < 0) throw new Error('the __LEAP_TABLE__ block has no close');
const before = html.slice(0, start);
const after = html.slice(end + 3);

let out = before + block + after;

// the stale comment: it said n=1..13 while the arrays already held fourteen
const staleComment = /\/\/ ── committed table \(n=1\.\.\d+\)\./;
if (staleComment.test(out)) out = out.replace(staleComment, '// ── committed table (n=1..15).');
else console.log('  (note: the "committed table" comment was not found to update)');

const changed = out !== html;
console.log(`__LEAP_TABLE__ rebuilt from terms-1-15.tsv: 16 rows of 15 terms.`);
console.log(`  page ${changed ? 'WOULD CHANGE' : 'already matches'}`);
if (!APPLY) { console.log('  (report only; pass --apply to write)'); process.exit(0); }
writeFileSync(PAGE, out);
console.log('  written.');
