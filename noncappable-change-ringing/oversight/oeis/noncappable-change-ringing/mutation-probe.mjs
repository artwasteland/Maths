// mutation-probe.mjs: does the artifact gate actually bite?
//
//   node mutation-probe.mjs      (about 2 min: it runs verify-staged.mjs seven times)
//
// The 2026-07-27 measurement in research/oeis-term-coverage/ established that a
// staging directory can carry a full suite of green checks while every number in
// its b-files is bound to nothing. Asserting "our gate would catch that" is the
// same species of claim that measurement falsified, so this asks the question
// operationally instead: copy the directory somewhere disposable, corrupt one
// staged term, run verify-staged.mjs, and see whether it goes red.
//
// One case is chosen from each binding class, plus a truncation, plus a control
// that corrupts nothing. The control matters: a gate that fails on everything is
// not a gate, it is a broken script, and a probe with no control cannot tell the
// difference.
//
// It never writes inside this directory. Everything happens in a temp copy.

import { cpSync, mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));

const CASES = [
  { file: 'b-bells4.txt', from: '24 48156', to: '24 48157', label: 'recomputed range, last term' },
  { file: 'b-bells5.txt', from: '21 300947562874178', to: '21 300947562874179', label: 'drift-guarded deepest term' },
  { file: 'b-bells6.txt', from: '13 1526242691836', to: '13 1526242691837', label: 'published-pair-only term' },
  { file: 'b-bells8.txt', from: '9 969410528032', to: '9 969410528033', label: 'eight bells, last derivable term' },
  { file: 'b-bells9.txt', from: '3 1866', to: '3 1867', label: 'nine bells, recomputed term' },
  { file: 'b-bells7.txt', from: '13 1488223219474714', to: null, label: 'truncation: drop the last line' },
  { file: null, label: 'control: corrupt nothing' },
];

const work = mkdtempSync(join(tmpdir(), 'noncappable-mutation-'));
cpSync(HERE, work, { recursive: true });

function runGate() {
  const r = spawnSync('node', ['verify-staged.mjs'], { cwd: work, encoding: 'utf8', timeout: 600_000 });
  const lines = (r.stdout || '').trim().split('\n').filter((l) => l.trim());
  return { red: r.status !== 0, tail: lines[lines.length - 1] || '(no output)' };
}

let wrong = 0;
console.log('mutation probe: one corruption per binding class, plus a control.\n');
for (const c of CASES) {
  let original = null;
  const path = c.file ? join(work, c.file) : null;
  if (path) {
    original = readFileSync(path, 'utf8');
    if (!original.includes(`${c.from}\n`)) {
      console.log(`  SKIP   ${c.file.padEnd(14)} ${c.label}   (line not found; probe is stale)`);
      wrong++;
      continue;
    }
    writeFileSync(path, original.replace(`${c.from}\n`, c.to ? `${c.to}\n` : ''));
  }
  const { red, tail } = runGate();
  const shouldBeRed = Boolean(c.file);
  const correct = red === shouldBeRed;
  if (!correct) wrong++;
  console.log(`  ${red ? 'RED  ' : 'green'}  ${(c.file || '-').padEnd(14)} ${c.label.padEnd(34)} ${tail}${correct ? '' : '   <-- WRONG'}`);
  if (path) writeFileSync(path, original);
}

rmSync(work, { recursive: true, force: true });
console.log(`\n${wrong === 0 ? 'ALL AS EXPECTED' : `${wrong} WRONG`}: every corrupted term turns the gate red, and the control stays green.`);
process.exit(wrong ? 1 : 0);
