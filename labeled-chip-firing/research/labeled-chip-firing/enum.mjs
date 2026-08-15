// ─────────────────────────────────────────────────────────────────────────────
// Labeled chip-firing on Z (Hopkins–McConville–Propp, "Sorting via chip-firing",
// EJC 24 (2017) #P3.13; arXiv:1612.06816). The exact enumerators.
//
//   Start with N labeled chips (labels 1..N) all at the origin of the integer
//   line Z. A vertex is UNSTABLE if it holds ≥2 chips. To FIRE it we "choose any
//   two chips at that vertex and move the lesser-labeled chip to the left and the
//   greater-labeled chip to the right" (their rule, verbatim). A configuration is
//   STABLE when every vertex holds ≤1 chip; then the N chips occupy N consecutive
//   sites and, read left→right, spell a permutation of 1..N.
//
//   HMP Theorem 13: for EVEN N the terminal permutation is ALWAYS the sorted one
//   (1,2,…,N) — confluence, independent of every choice. For ODD N confluence
//   fails; the number of DISTINCT reachable terminal permutations is OEIS
//   A282901 (indexed by n where N = 2n+1): a(n) = 1, 3, 12, 54, 232, …
//
// Two independent enumerators, agreeing on every odd N ≤ 9 (see verify.mjs):
//   • enumMap(N)  — the reference. Configuration = Map(position → sorted labels),
//                   real integer positions (negatives allowed). Handles even & odd.
//   • enumFast(N) — odd N only. Configuration packed as N nibbles of a JS Number
//                   (each label's position ∈ 0..N-1); a Set<number> is the visited
//                   set. Fast enough to reach a(5)=819 in a few seconds; the exact
//                   logic ports to the browser and to C++ (cf.cpp).
//
//   For ODD N the support never reaches the two boundary sites (±n), so those
//   sites never fire — enumFast asserts this, and it holds for every N it is run
//   on. That is why the 0..N-1 nibble window (which cannot represent position −1)
//   is safe for odd N. It is NOT safe for even N (the origin site fires), so
//   enumFast refuses even N; use enumMap there.
// ─────────────────────────────────────────────────────────────────────────────

// ── enumMap: the reference enumerator (any N) ───────────────────────────────
function keyOfMap(cfg) {
  const ps = [...cfg.keys()].sort((a, b) => a - b);
  return ps.map(p => p + ':' + cfg.get(p).join(',')).join('|');
}
function isStable(cfg) { for (const v of cfg.values()) if (v.length > 1) return false; return true; }
function permOfMap(cfg) {
  const ps = [...cfg.keys()].sort((a, b) => a - b);
  return ps.map(p => cfg.get(p)[0]).join(',');
}
export function enumMap(N) {
  const start = new Map([[0, Array.from({ length: N }, (_, i) => i + 1)]]);
  const seen = new Set([keyOfMap(start)]);
  const stack = [start];
  const perms = new Set();
  while (stack.length) {
    const cfg = stack.pop();
    if (isStable(cfg)) { perms.add(permOfMap(cfg)); continue; }
    for (const [p, L] of cfg) {
      if (L.length < 2) continue;
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
        const a = Math.min(L[i], L[j]), b = Math.max(L[i], L[j]);       // lesser←left, greater→right
        const rest = L.filter((_, k) => k !== i && k !== j);
        const nc = new Map();
        for (const [q, ls] of cfg) if (q !== p) nc.set(q, ls.slice());
        if (rest.length) nc.set(p, rest);
        const add = (pos, lab) => { const arr = nc.get(pos) || []; arr.push(lab); arr.sort((x, y) => x - y); nc.set(pos, arr); };
        add(p - 1, a); add(p + 1, b);
        const k = keyOfMap(nc);
        if (!seen.has(k)) { seen.add(k); stack.push(nc); }
      }
    }
  }
  return { perms, configs: seen.size };
}

// ── enumFast: nibble-packed enumerator (odd N only) ─────────────────────────
// State = a JS Number holding N nibbles; nibble `l` = position (0..N-1) of label l.
// N ≤ 13 ⇒ 13·4 = 52 bits ⇒ within Number's 53-bit exact-integer range.
const getp = (s, l) => Math.floor(s / 2 ** (4 * l)) % 16;
export function enumFast(N) {
  if (N % 2 === 0) throw new Error('enumFast is for odd N only (even N fires the origin boundary); use enumMap');
  const origin = (N - 1) / 2;
  let start = 0;
  for (let l = 0; l < N; l++) start += origin * 2 ** (4 * l);
  const seen = new Set([start]);
  const stack = [start];
  let stablePerms = 0;
  const setp = (s, l, p) => s - getp(s, l) * 2 ** (4 * l) + p * 2 ** (4 * l);
  while (stack.length) {
    const s = stack.pop();
    // bucket labels by position
    const at = Array.from({ length: N }, () => []);
    for (let l = 0; l < N; l++) at[getp(s, l)].push(l);
    let stable = true;
    for (let p = 0; p < N; p++) if (at[p].length > 1) { stable = false; break; }
    if (stable) { stablePerms++; continue; }
    for (let p = 0; p < N; p++) {
      if (at[p].length < 2) continue;
      if (p === 0 || p === N - 1) throw new Error(`boundary site ${p} fired at odd N=${N} — support assumption violated`);
      const L = at[p]; // labels already ascending (we scanned l ascending)
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
        const a = L[i], b = L[j];                        // a<b: lesser←left, greater→right
        let ns = setp(s, a, p - 1); ns = setp(ns, b, p + 1);
        if (!seen.has(ns)) { seen.add(ns); stack.push(ns); }
      }
    }
  }
  return { perms: stablePerms, configs: seen.size };
}

// ── the reachable terminal permutations themselves (for the showing / examples)
export function reachablePerms(N) {
  const { perms } = enumMap(N);
  return [...perms].map(s => s.split(',').map(Number));
}

// A282901: a(n) = # reachable terminal permutations with N = 2n+1 chips.
export function a282901(n, fast = true) {
  const N = 2 * n + 1;
  return (fast ? enumFast : enumMap)(N).perms;
}
