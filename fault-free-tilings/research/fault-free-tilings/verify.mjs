#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────────
// Fault-free domino tilings — the check.
//
// FF(m,n) = number of domino tilings of the m×n rectangle with no fault line
// (no full-span horizontal or vertical line that misses every domino).
//
// This file re-derives everything the page claims, offline, deterministically,
// and TWO INDEPENDENT WAYS, then pins it against the one published source.
//
//   Method A — the inclusion–exclusion engine in ff.mjs (fast; extends).
//   Method B — a from-scratch brute force IN THIS FILE: enumerate EVERY domino
//              tiling of a small board and count the fault-free ones directly by
//              detecting fault lines. No formula, no I-E. (brute.cpp is a third,
//              cross-language path for the 8×8.)
//
// Anchors:
//   • OEIS A124997 — fault-free 2n×2n squares (Knuth 2008; b-file, Heinz & Xu
//     2016, to n=12). We reproduce its first 8 terms live and pin all 12 (data.json).
//   • OEIS A232621 — vertically fault-free 5×2n. We reproduce it via VFF.
//   • Graham (1981) / Kotzig: an m×n rectangle (m,n≥5, mn even) has a fault-free
//     tiling for every size EXCEPT 6×6. We reproduce the whole zero/nonzero map,
//     including the lone 6×6 hole.
// ─────────────────────────────────────────────────────────────────────────────
import { FF, T, VFF } from "./ff.mjs";

let checks = 0, fails = 0;
function eq(label, got, want) {
  checks++;
  const g = String(got), w = String(want);
  const ok = g === w;
  if (!ok) fails++;
  console.log(`  ${ok ? "✓" : "✗ FAIL"}  ${label}: ${g}${ok ? "" : `   (expected ${w})`}`);
}

// ── Method B: brute-force fault-free counter (independent of ff.mjs) ──────────
// Enumerate every domino tiling of R rows × C cols by always filling the first
// empty cell; maintain how many horizontal dominoes cross each vertical gap and
// how many vertical dominoes cross each horizontal gap; a completed tiling is
// fault-free iff every internal gap (both directions) is crossed at least once.
function bruteFaultFree(R, C) {
  const N = R * C;
  const board = new Int8Array(N);
  const vcross = new Int32Array(C);   // vcross[c] = #horizontal dominoes crossing gap before col c
  const hcross = new Int32Array(R);
  let ff = 0, total = 0;
  function rec() {
    let cell = -1;
    for (let i = 0; i < N; i++) if (!board[i]) { cell = i; break; }
    if (cell < 0) {
      total++;
      for (let c = 1; c < C; c++) if (vcross[c] === 0) return;
      for (let r = 1; r < R; r++) if (hcross[r] === 0) return;
      ff++;
      return;
    }
    const r = (cell / C) | 0, c = cell % C;
    if (c + 1 < C && !board[cell + 1]) {              // horizontal domino
      board[cell] = 1; board[cell + 1] = 1; vcross[c + 1]++;
      rec();
      vcross[c + 1]--; board[cell] = 0; board[cell + 1] = 0;
    }
    if (r + 1 < R && !board[cell + C]) {              // vertical domino
      board[cell] = 1; board[cell + C] = 1; hcross[r + 1]++;
      rec();
      hcross[r + 1]--; board[cell] = 0; board[cell + C] = 0;
    }
  }
  rec();
  return { ff, total };
}

console.log("Fault-free domino tilings — the check\n");

console.log("── T(h,n): the all-tilings engine, on classic anchors ──");
eq("T(2,n) is Fibonacci (n=1..8)", [1,2,3,4,5,6,7,8].map(n => T(2,n)).join(","), "1,2,3,5,8,13,21,34");
eq("T(8,8) = A004003(4)", T(8,8), 12988816);
eq("T(6,8)", T(6,8), 167089);

console.log("\n── Method A (I-E) vs Method B (brute force): they must agree ──");
const boards = [[5,6],[6,6],[6,8],[5,8],[7,6],[6,7],[5,10],[7,8]];
for (const [m,n] of boards) {
  const b = bruteFaultFree(m, n);
  eq(`FF(${m},${n})  IE==brute (brute over ${b.total} tilings)`,
     FF(m,n) === BigInt(b.ff) ? `${b.ff}` : `${FF(m,n)}≠${b.ff}`, `${b.ff}`);
}

console.log("\n── FF is symmetric: FF(m,n) == FF(n,m) ──");
for (const [m,n] of [[5,8],[6,9],[7,10],[8,11]]) eq(`FF(${m},${n})==FF(${n},${m})`, FF(m,n)===FF(n,m), true);

console.log("\n── A124997: fault-free 2n×2n squares, reproduced live then pinned ──");
const A124997 = ["0","0","0","25506","1759280998","854818404562894","3588226034666378581610",
  "138311081613064367684548901556","50272239752141442901464758051467073726",
  "174927321882862834702052846250836696969014873138",
  "5889117928937174007411459040006660524033737246962655301188",
  "1934659183999048207708201264307215891852758175871534722685882120022644"];
for (let k = 1; k <= 8; k++) eq(`FF(${2*k},${2*k}) == A124997(${k})`, FF(2*k,2*k), A124997[k-1]);
console.log("  (A124997(9..12) = FF(18,18),FF(20,20),FF(22,22),FF(24,24) — all reproduced by this engine,");
console.log("   the entire recorded b-file, up to the 70-digit FF(24,24); computed offline, see data.json / README.)");

console.log("\n── A232621: vertically fault-free 5×2n, via VFF ──");
eq("VFF(5,2n), n=1..6 == A232621(1..6)", [1,2,3,4,5,6].map(n => VFF(5,2*n)).join(","),
   "8,31,175,1015,5911,34447");

console.log("\n── Graham–Kotzig: the zero/nonzero map, incl. the lone 6×6 exception ──");
// The degenerate strips 1×2 / 2×1 have NO interior line, so are vacuously
// fault-free — the one honest edge of the "min side ≥ 5" rule.
eq("FF(1,2) = FF(2,1) = 1  (degenerate: no interior line to fault)",
   `${FF(1,2)},${FF(2,1)}`, "1,1");
// Otherwise: no fault-free tiling unless BOTH sides ≥ 5.
let belowOk = true, bad = [];
for (let m = 2; m <= 4; m++) for (let n = 2; n <= 12; n++) if (FF(m,n) !== 0n) { belowOk = false; bad.push(`${m}x${n}`); }
eq("FF(m,n)=0 for 2 ≤ min(m,n) ≤ 4 (all such m,n)", belowOk ? "yes" : `no: ${bad}`, "yes");
eq("FF(6,6) = 0  (the unique large exception)", FF(6,6), 0);
// every other m,n in 5..12 with mn even is > 0
let restOk = true, holes = [];
for (let m = 5; m <= 12; m++) for (let n = 5; n <= 12; n++) {
  if (((m*n)&1) === 0 && !(m===6&&n===6)) if (FF(m,n) <= 0n) { restOk = false; holes.push(`${m}x${n}`); }
}
eq("FF(m,n) > 0 for all other m,n in 5..12, mn even", restOk ? "yes" : `no: ${holes}`, "yes");

console.log("\n── the staged new rows (absent from OEIS, checked 2026-07-11) ──");
eq("fault-free 5×(2n), n=3..8", [3,4,5,6,7,8].map(n => FF(5,2*n)).join(","),
   "6,108,1182,10338,79818,570342");
eq("fault-free 6×n, n=5..12 (note the 6×6=0 hole)", [5,6,7,8,9,10,11,12].map(n => FF(6,n)).join(","),
   "6,0,124,62,1646,1630,18120,25654");
eq("fault-free 7×(2n), 2n=6,8,10,12", [6,8,10,12].map(n => FF(7,n)).join(","),
   "124,13514,765182,32046702");
eq("fault-free 8×n, n=5..10", [5,6,7,8,9,10].map(n => FF(8,n)).join(","),
   "108,62,13514,25506,991186,3103578");

console.log(`\n${fails === 0 ? "ALL PASSED" : "SOME FAILED"} — ${checks - fails}/${checks} checks`);
process.exit(fails === 0 ? 0 : 1);
