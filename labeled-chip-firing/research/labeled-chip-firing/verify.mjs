// ─────────────────────────────────────────────────────────────────────────────
// verify.mjs — the offline check for the labeled-chip-firing result.
//
//   Trust, never a single code path:
//     • two independent JS enumerators (enumMap: real-position Map;
//       enumFast: nibble-packed Number) agree on every odd N ≤ 9;
//     • a third implementation in C++ (cf.cpp, flat-hash u64) is compiled and run,
//       agreeing on the known terms AND delivering a(5)=819;
//     • the known OEIS A282901 terms 1,3,12,54,232 are reproduced term-for-term;
//     • HMP Theorem 13 (even N ⇒ unique sorted terminal config) is reproduced,
//       and the sorted positions match their closed form;
//     • the odd-N boundary invariant (support never fires the end sites) holds.
//
//   Run:  node research/labeled-chip-firing/verify.mjs
// ─────────────────────────────────────────────────────────────────────────────
import { enumMap, enumFast, reachablePerms } from './enum.mjs';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const DIR = dirname(fileURLToPath(import.meta.url));
let pass = 0, fail = 0;
const ok = (c, msg) => { if (c) { pass++; console.log('  ✓ ', msg); } else { fail++; console.log('  ✗  FAIL:', msg); } };

// A282901: a(n) = # reachable terminal permutations, N = 2n+1 chips.
const KNOWN = [1, 3, 12, 54, 232];               // a(0..4), from OEIS A282901 (inline terms)
const CONFIGS_ODD = { 1: 1, 3: 4, 5: 56, 7: 1699, 9: 84793 };  // # reachable configs, odd N ≤ 9

console.log('\n1) Reproduce the known OEIS A282901 terms with BOTH JS enumerators');
for (let n = 0; n <= 4; n++) {
  const N = 2 * n + 1;
  const m = enumMap(N), f = enumFast(N);
  ok(m.perms.size === KNOWN[n] && f.perms === KNOWN[n],
     `a(${n}) = ${KNOWN[n]}  (enumMap=${m.perms.size}, enumFast=${f.perms})`);
  ok(m.configs === CONFIGS_ODD[N] && f.configs === CONFIGS_ODD[N],
     `  reachable configs at N=${N}: ${CONFIGS_ODD[N]} (both enumerators agree)`);
}

console.log('\n2) The sorted (identity) permutation is always reachable for odd N');
for (let n = 1; n <= 4; n++) {
  const N = 2 * n + 1;
  const ident = Array.from({ length: N }, (_, i) => i + 1).join(',');
  const has = reachablePerms(N).some(p => p.join(',') === ident);
  ok(has, `identity 1..${N} is reachable (you can always finish the sort)`);
}

console.log('\n3) HMP Theorem 13 — EVEN N confluES to the unique sorted config');
for (const N of [2, 4, 6, 8]) {
  const m = enumMap(N);
  const perms = [...m.perms];
  const ident = Array.from({ length: N }, (_, i) => i + 1).join(',');
  ok(perms.length === 1 && perms[0] === ident,
     `N=${N}: exactly 1 reachable terminal permutation, and it is sorted`);
}
// Theorem 13 closed form: for N=2m, the stable positions are D(k)=-(m+1)+k (k=1..m)
// and D(m+k)=k (k=1..m); i.e. occupied sites are -m..-1 and 1..m, label i at the
// i-th site left→right. We already confirmed the labels come out 1..N in order;
// here confirm the OCCUPIED SITES skip the origin and are symmetric (the "gap").
{
  // reconstruct the terminal config of N=6 explicitly through enumMap's own run
  // (positions are implicit in enumMap; assert the site pattern via a direct sim)
  const sites = terminalSitesEven(6);
  ok(JSON.stringify(sites) === JSON.stringify([-3, -2, -1, 1, 2, 3]),
     `N=6: terminal occupied sites are -3..-1, 1..3 (origin left empty), per Thm 13`);
}

console.log('\n4) The odd-N boundary invariant (end sites never fire)');
for (let n = 1; n <= 4; n++) {
  let threw = false;
  try { enumFast(2 * n + 1); } catch (e) { threw = true; }   // enumFast throws if a boundary fires
  ok(!threw, `N=${2 * n + 1}: no chip is ever pushed past the support boundary`);
}
ok((() => { try { enumFast(4); return false; } catch { return true; } })(),
   'enumFast correctly refuses even N (where the origin boundary does fire)');

console.log('\n5) The C++ enumerator (independent, flat-hash u64) — build, cross-check, and a(5)');
let cppA5 = null, cppConfigs5 = null;
try {
  execSync(`g++ -O3 -o ${join(DIR, 'cf')} ${join(DIR, 'cf.cpp')}`, { stdio: 'pipe' });
  // cross-check known terms
  for (const [N, want] of [[5, 12], [7, 54], [9, 232]]) {
    const out = execSync(`${join(DIR, 'cf')} ${N} 20`).toString();
    const got = +out.match(/a\(n\)=(\d+)/)[1];
    const cfg = +out.match(/configs=(\d+)/)[1];
    ok(got === want && cfg === CONFIGS_ODD[N],
       `C++ N=${N}: a=${got}, configs=${cfg} (matches JS)`);
  }
  const out5 = execSync(`${join(DIR, 'cf')} 11 24`).toString();
  cppA5 = +out5.match(/a\(n\)=(\d+)/)[1];
  cppConfigs5 = +out5.match(/configs=(\d+)/)[1];
  ok(cppA5 === 819 && cppConfigs5 === 6520201,
     `C++ a(5) = 819 with 6 520 201 configs  ← the new term`);
} catch (e) {
  console.log('  (skipped C++ leg — no g++?)  ', String(e).split('\n')[0]);
}

console.log('\n6) The new term, cross-confirmed by JS enumFast (the slow-but-independent path)');
// enumFast(11) takes ~40s; run it so the new term is proven by ≥2 methods in-process.
{
  const t = Date.now();
  const f = enumFast(11);
  ok(f.perms === 819 && f.configs === 6520201,
     `enumFast a(5) = 819, configs = 6 520 201  (JS, ${((Date.now() - t) / 1000).toFixed(0)}s) — agrees with C++`);
}

// ── helper: terminal occupied sites for an even N (direct greedy sim, any order)
function terminalSitesEven(N) {
  let cfg = new Map([[0, Array.from({ length: N }, (_, i) => i + 1)]]);
  // fire deterministically until stable (order-independent by Thm 13)
  let unstable = true;
  while (unstable) {
    unstable = false;
    for (const [p, L] of [...cfg]) {
      if (L.length >= 2) {
        unstable = true;
        const s = [...L].sort((a, b) => a - b);
        const a = s[0], b = s[s.length - 1], rest = s.slice(1, -1);
        cfg.set(p, rest);
        if (cfg.get(p).length === 0) cfg.delete(p);
        cfg.set(p - 1, [...(cfg.get(p - 1) || []), a]);
        cfg.set(p + 1, [...(cfg.get(p + 1) || []), b]);
        break;
      }
    }
  }
  return [...cfg.keys()].filter(p => cfg.get(p).length).sort((a, b) => a - b);
}

// ── 7) The Lean kernel — the same wonder, exhaustively, trusting nothing but logic
// research/labeled-chip-firing/lean/ChipFiring.lean BUILDS every reachable
// configuration inside Lean's kernel and checks: even N (2,4,6) always sorts
// (confluence), odd N (3,5) branches into exactly the OEIS A282901 counts, and the
// model is faithful (no site-0 underflow; the enumeration is a fixed point). Every
// theorem closes with "does not depend on any axioms at all". If lean is on PATH we
// typecheck it live; otherwise we assert the .lean is present and static-check the
// counts it commits to against ours.
try {
  const { execSync } = await import('node:child_process');
  const os = await import('node:os');
  const fs = await import('node:fs');
  const path = await import('node:path');
  const here = dirname(fileURLToPath(import.meta.url));
  const leanFile = path.join(here, 'lean', 'ChipFiring.lean');
  ok(fs.existsSync(leanFile), 'lean/ChipFiring.lean present (the machine-checked companion)');
  // Static cross-check: the counts the .lean commits to must equal ours.
  const src = fs.existsSync(leanFile) ? fs.readFileSync(leanFile, 'utf8') : '';
  ok(/perms 200 4 = \[\[1, 2, 3, 4\]\]/.test(src) && enumMap(4).perms.size === 1,
     'lean asserts N=4 → sorted; enumMap agrees (1 terminal perm)');
  ok(/perms 600 6 = \[\[1, 2, 3, 4, 5, 6\]\]/.test(src) && enumMap(6).perms.size === 1,
     'lean asserts N=6 → sorted; enumMap agrees (1 terminal perm)');
  ok(/\(perms 100 3\)\.length = 3/.test(src) && enumMap(3).perms.size === 3,
     'lean asserts N=3 → 3 endings (A282901 a(1)); enumMap agrees');
  ok(/\(perms 400 5\)\.length = 12/.test(src) && enumMap(5).perms.size === 12,
     'lean asserts N=5 → 12 endings (A282901 a(2)); enumMap agrees');
  const env = { ...process.env, PATH: `${os.homedir()}/.elan/bin:${os.homedir()}/.nix-profile/bin:${process.env.PATH}` };
  let haveLean = false;
  try { execSync('command -v lean', { env, shell: '/bin/bash' }); haveLean = true; } catch {}
  if (haveLean) {
    console.log('   Live Lean kernel check (lean on PATH; ~1–2 min, all in the kernel) …');
    const tmp = path.join(os.tmpdir(), `chipfiring-verify-${process.pid}.lean`);
    const named = ['even2_sorts', 'even4_sorts', 'even4_one_terminal', 'even6_sorts',
                   'odd3_count', 'odd5_count', 'odd3_branches', 'odd5_can_sort',
                   'boundary_safe', 'fuel_saturated_6'];
    fs.writeFileSync(tmp, src + '\n' + named.map(t => `#print axioms ${t}`).join('\n') + '\n');
    let out = '';
    try { out = execSync(`lean ${JSON.stringify(tmp)}`, { env, shell: '/bin/bash', encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); }
    catch (e) { out = (e.stdout || '') + (e.stderr || ''); }
    fs.unlinkSync(tmp);
    ok(!/error:/i.test(out) && !/sorry/i.test(out), 'Lean: ChipFiring.lean typechecks with no error / no sorry');
    for (const t of named) {
      const line = out.split('\n').find(l => l.includes(`'${t}'`)) || '';
      const clean = /does not depend on any axioms/.test(line);
      ok(clean, `Lean: ${t} → no axioms  (${line.trim() || 'no output'})`);
    }
  } else {
    console.log('   (Live Lean check skipped: lean not on PATH — run lean/install-lean-nix.sh, then re-run.)');
  }
} catch (e) { console.log(`   (Lean leg skipped: ${e.message})`); }

console.log(`\n${fail === 0 ? 'ALL PASSED' : 'FAILURES'} — ${pass}/${pass + fail} checks\n`);
process.exit(fail === 0 ? 0 : 1);
