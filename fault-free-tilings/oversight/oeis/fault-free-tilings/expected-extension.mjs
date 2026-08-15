// Expected values for the 35 array cells the default staged check does not
// recompute: every cell of the 18 x 18 array with m = 18 or n = 18.
//
// WHY THEY ARE HERE. The cost of FF(m,n) through research/fault-free-tilings/ff.mjs
// is dominated by the transfer matrix T(h,k), whose state space is 2^h. Going from
// max(m,n) = 17 to max(m,n) = 18 costs roughly 25 to 40 extra seconds on the
// machine that measured it, which is more than the default gate should spend.
// Everything with max(m,n) <= 17 is recomputed live, every run.
//
// WHAT THIS TABLE IS, EXACTLY. Each value below was produced by ff.mjs on
// 2026-07-27, in a run that recomputed all 470 staged terms across all five
// b-files and found zero mismatches. The values were transcribed from that run's
// output, not read out of the b-files and not taken from derive.mjs. The same day,
// `verify-staged.mjs --full` was run against the finished table and re-earned all
// 35 values live from the engine; its output is committed beside this file as
// full-array-run-2026-07-27.txt.
//
// WHAT THIS TABLE IS NOT. Comparing a staged line against this table is DRIFT
// PROTECTION, not an independent recomputation: it is the same engine, recorded
// once instead of re-executed. It catches a staged term that changed after
// 2026-07-27; it does not add a second opinion about the mathematics.
//
// HOW TO RE-EARN IT. The values are not a dead end. Run
//
//     node oversight/oeis/fault-free-tilings/verify-staged.mjs --full
//
// and all 35 are recomputed by ff.mjs in the gate and compared against both the
// staged b-file and this table (roughly 25 to 40 seconds more than the default
// run). A disagreement between the engine and this table is itself a failure.
//
// Rows are [antidiagonal index in b-ff-array-antidiagonals.txt, m, n, FF(m,n)].
// The reading order is the one stated in that file's own header and written by
// derive.mjs: antidiagonals upward, T(1,1), T(1,2), T(2,1), T(1,3), ...

const ARRAY_SIDE = 18;

const LARGE_CELLS = [
  [154, 18, 1, '0'],
  [171, 1, 18, '0'],
  [172, 18, 2, '0'],
  [188, 2, 18, '0'],
  [189, 18, 3, '0'],
  [204, 3, 18, '0'],
  [205, 18, 4, '0'],
  [219, 4, 18, '0'],
  [220, 18, 5, '3870468'],
  [233, 5, 18, '3870468'],
  [234, 18, 6, '33682250'],
  [246, 6, 18, '33682250'],
  [247, 18, 7, '1089517092974'],
  [258, 7, 18, '1089517092974'],
  [259, 18, 8, '36137421117096'],
  [269, 8, 18, '36137421117096'],
  [270, 18, 9, '105313323090903808'],
  [279, 9, 18, '105313323090903808'],
  [280, 18, 10, '6991572970067005909'],
  [288, 10, 18, '6991572970067005909'],
  [289, 18, 11, '6159045535795050539958'],
  [296, 11, 18, '6159045535795050539958'],
  [297, 18, 12, '603021275020758841153394'],
  [303, 12, 18, '603021275020758841153394'],
  [304, 18, 13, '272595759785400395067070226'],
  [309, 13, 18, '272595759785400395067070226'],
  [310, 18, 14, '33308130329176220847158078352'],
  [314, 14, 18, '33308130329176220847158078352'],
  [315, 18, 15, '10161195521376166013096464227542'],
  [318, 15, 18, '10161195521376166013096464227542'],
  [319, 18, 16, '1408445744825055513980632800921880'],
  [321, 16, 18, '1408445744825055513980632800921880'],
  [322, 18, 17, '337985863607502598809991526343059336'],
  [323, 17, 18, '337985863607502598809991526343059336'],
  // FF(18,18) is A124997(9). This is the ONLY place in the repository where the
  // ninth term of A124997 is recorded as an engine output rather than as a
  // literal transcribed from the OEIS b-file. See README.md, "What this repository
  // recomputes of A124997, and what it copies".
  [324, 18, 18, '50272239752141442901464758051467073726'],
];

// An internally consistent table is the least this can offer: the array is
// symmetric (FF(m,n) = FF(n,m)), so the two cells of each transposed pair must
// carry the same value. A typo in one of a pair is caught right here, at import.
function buildExpectedLargeCells() {
  const table = new Map();
  const byPair = new Map();
  for (const [index, m, n, value] of LARGE_CELLS) {
    if (Math.max(m, n) !== ARRAY_SIDE) {
      throw new Error(`expected-extension: index ${index} is cell (${m},${n}), not on the ${ARRAY_SIDE} edge`);
    }
    if (table.has(index)) throw new Error(`expected-extension: duplicate index ${index}`);
    table.set(index, { m, n, value: BigInt(value) });
    const key = `${Math.min(m, n)},${Math.max(m, n)}`;
    const seen = byPair.get(key);
    if (seen === undefined) byPair.set(key, value);
    else if (seen !== value) {
      throw new Error(`expected-extension: transposed cells disagree for (${key}): ${seen} != ${value}`);
    }
  }
  return table;
}

const EXPECTED_LARGE_CELLS = buildExpectedLargeCells();

export { EXPECTED_LARGE_CELLS, ARRAY_SIDE };
