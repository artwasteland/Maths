// stage-extension.mjs — fold completed runs into the staged artifacts.
//
// For each completed run output (runs/*.out), this:
//   1. re-checks every published term against the dated OEIS snapshots
//      (delegating the comparison logic to check-oeis.mjs's data),
//   2. extends /oversight/oeis/noncappable-change-ringing/b-bells<n>.txt with
//      the new noncappable terms (asserting every overlapping line agrees),
//   3. prints a markdown table of the NEW terms for all three families
//      (cyclic / path / noncappable) ready for the READMEs.
//
// Usage: node stage-extension.mjs [--write]   (dry run without --write)
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const WRITE = process.argv.includes('--write');
const SNAP_DATE = '2026-07-03';
const IDS = { 5: ['A324944', 'A324945'], 6: ['A324946', 'A324947'], 7: ['A324948', 'A324949'] };
const RUNS = { 5: ['n5-L20'], 6: ['n6-L15', 'n6-L14'], 7: ['n7-L12'] }; // preference order
const STAGE = '../../../oversight/oeis/noncappable-change-ringing';

const snap = (id) =>
  JSON.parse(readFileSync(`oeis-${id}-${SNAP_DATE}.json`, 'utf8'))[0].data.split(',').map(BigInt);

let allOk = true;
const newRows = [];

for (const n of [5, 6, 7]) {
  const tag = RUNS[n].find((t) => existsSync(`runs/${t}.done`) && existsSync(`runs/${t}.out`));
  if (!tag) { console.log(`bells ${n}: no completed run yet — skipped`); continue; }
  const [cycId, pathId] = IDS[n];
  const pubCyc = snap(cycId), pubPath = snap(pathId);
  const rows = readFileSync(`runs/${tag}.out`, 'utf8').trim().split('\n')
    .filter((l) => !l.startsWith('#')).map((l) => l.split(' ').map(BigInt));

  // 1. published-term check (hard gate)
  let ok = 0;
  for (const [L, path, cyc] of rows) {
    const i = Number(L) - 1;
    if (pubPath[i] !== undefined && pubPath[i] !== path) { console.log(`FAIL ${pathId}(${L})`); allOk = false; }
    else if (pubPath[i] !== undefined) ok++;
    if (pubCyc[i] !== undefined && pubCyc[i] !== cyc) { console.log(`FAIL ${cycId}(${L})`); allOk = false; }
    else if (pubCyc[i] !== undefined) ok++;
  }

  // 2. extend the staged noncappable b-file
  const bfile = `${STAGE}/b-bells${n}.txt`;
  const existing = readFileSync(bfile, 'utf8').trim().split('\n')
    .map((l) => l.trim().split(/\s+/).map(BigInt));
  const byL = new Map(rows.map((r) => [Number(r[0]), r]));
  for (const [L, val] of existing) {
    const r = byL.get(Number(L));
    if (r && r[3] !== val) { console.log(`FAIL b-bells${n} overlap at L=${L}: staged ${val}, computed ${r[3]}`); allOk = false; }
  }
  const lastStaged = Number(existing[existing.length - 1][0]);
  const additions = rows.filter(([L]) => Number(L) > lastStaged);
  if (additions.length && allOk) {
    const lines = additions.map(([L, , , nc]) => `${L} ${nc}`);
    if (WRITE) {
      writeFileSync(bfile, readFileSync(bfile, 'utf8').trimEnd() + '\n' + lines.join('\n') + '\n');
      console.log(`bells ${n}: b-file extended by ${additions.length} terms (from ${tag}, ${ok} published terms re-verified)`);
    } else {
      console.log(`bells ${n}: would extend b-file by ${additions.length} terms (${ok} published terms re-verified)`);
    }
  }

  // 3. new-term rows for the table
  for (const [L, path, cyc, nc] of rows) {
    const i = Number(L) - 1;
    if (pubPath[i] === undefined || pubCyc[i] === undefined)
      newRows.push({ n, L: Number(L), cycId, pathId, path, cyc, nc, tag });
  }
}

if (newRows.length) {
  console.log('\n## New terms (markdown)\n');
  console.log('| bells | L | ' + 'cyclic (new term) | path (new term) | noncappable (new term) | run |');
  console.log('|---|---|---|---|---|---|');
  for (const r of newRows)
    console.log(`| ${r.n} | ${r.L} | ${r.cycId}(${r.L}) = ${r.cyc} | ${r.pathId}(${r.L}) = ${r.path} | ${r.nc} | ${r.tag} |`);
}
process.exit(allOk ? 0 : 1);
