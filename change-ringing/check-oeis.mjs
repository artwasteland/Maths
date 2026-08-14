// check-oeis.mjs — compare a count.c output file against the dated OEIS
// snapshots in this directory. Every published term must match exactly;
// terms beyond the published range are reported as NEW.
//
// Usage: node check-oeis.mjs <n> <count-output-file>
import { readFileSync } from 'node:fs';

const SNAP_DATE = process.env.SNAP_DATE || '2026-07-03';
const IDS = { 5: ['A324944', 'A324945'], 6: ['A324946', 'A324947'], 7: ['A324948', 'A324949'] };

const n = parseInt(process.argv[2], 10);
const file = process.argv[3];
if (!IDS[n] || !file) { console.error('usage: node check-oeis.mjs <5|6|7> <output-file>'); process.exit(2); }
const [cycId, pathId] = IDS[n];

const snap = (id) =>
  JSON.parse(readFileSync(`oeis-${id}-${SNAP_DATE}.json`, 'utf8'))[0].data.split(',').map((s) => BigInt(s));

const pubCyc = snap(cycId), pubPath = snap(pathId);

const rows = readFileSync(file, 'utf8').trim().split('\n').filter((l) => !l.startsWith('#'))
  .map((l) => l.split(' ').map(BigInt));

let ok = 0, bad = 0;
const newTerms = [];
for (const [L, path, cyc, nc] of rows) {
  const i = Number(L) - 1;
  const checks = [[pathId, pubPath[i], path], [cycId, pubCyc[i], cyc]];
  for (const [id, pub, got] of checks) {
    if (pub === undefined) continue;
    if (pub === got) ok++;
    else { bad++; console.log(`MISMATCH ${id}(${L}): published ${pub}, computed ${got}`); }
  }
  if (pubPath[i] === undefined || pubCyc[i] === undefined)
    newTerms.push({ L: Number(L), path, cyc, noncappable: nc });
  else if (path - cyc !== nc && Number(L) !== 1) { bad++; console.log(`IDENTITY FAIL at L=${L}`); }
}
console.log(`${ok} published terms reproduced exactly (${cycId} + ${pathId}), ${bad} mismatches`);
for (const t of newTerms)
  console.log(`NEW  L=${t.L}:  path=${t.path}  cyclic=${t.cyc}  noncappable=${t.noncappable}`);
process.exit(bad === 0 ? 0 : 1);
