// expected-tail.mjs: the staged tail n=49..64, copied from two recorded runs.
//
// WHAT THIS IS, AND WHAT IT IS NOT.
// verify-staged.mjs recomputes staged terms n=1..48 from
// research/lights-out-surfaces/engine.mjs, live, every run. Recomputing the rest
// of the staged range is not affordable in a gate: one pass over n=1..64 for the
// four staged surfaces takes about 133 s of JavaScript, and the elimination cost
// grows roughly as n^5, so almost all of that is spent above n=48. The tail
// n=49..64 is therefore compared against the table below instead.
//
// That comparison is DRIFT PROTECTION for the b-files. It catches a b-file that
// changes after 2026-07-27, by editing, corruption, or a stray regeneration. It
// is NOT an independent recomputation of those sixteen terms per surface, and it
// cannot detect an error that was already present in both this table and the
// b-file when they were written. No committed check in this repository re-derives
// n=49..64 in under a minute. Anything the README says about the tail has to say
// that much.
//
// PROVENANCE. Every value below was produced twice on 2026-07-27, by two code
// paths that share no source, and both runs agreed with each other and with the
// staged b-files on all 256 terms (n=1..64, four surfaces):
//
//   (a) research/lights-out-surfaces/engine.mjs, surfaceNullity(n, surface) for
//       n=1..64, JavaScript Gauss-Jordan over GF(2) on BigInt row masks.
//       Wall time 133 s. Reproduce with:
//         node -e "import('./research/lights-out-surfaces/engine.mjs').then(async m=>{for(const s of ['cylinder','klein','mobius','projective']){const v=[];for(let n=1;n<=64;n++)v.push(m.surfaceNullity(n,s));console.log(s, v.join(','));}})"
//
//   (b) research/lights-out-surfaces/verify.py at NMAX=64, stdlib Python with a
//       separately written neighbourhood function and a separately written
//       elimination. Wall time 3 m 55 s. Reproduce with:
//         python3 research/lights-out-surfaces/verify.py 64
//
// Neither (a) nor (b) is run by any committed gate at n=64: verify.mjs stops its
// Python cross-check at n=40, and verify-staged.mjs recomputes to n=48. To check
// this table against a live recomputation rather than trusting it, run:
//         node oversight/oeis/lights-out-surfaces/verify-staged.mjs --to 64
// which ignores the table entirely and recomputes the whole staged range (slow,
// several minutes).

export const TAIL_FROM = 49;
export const TAIL_TO = 64;

// surface -> values for n = TAIL_FROM .. TAIL_TO, in order.
const TAIL_VALUES = {
  cylinder:   [0, 2, 2, 0, 1, 0, 0, 4, 2, 0, 1, 0, 0, 2, 2, 0],
  klein:      [0, 8, 12, 0, 0, 6, 4, 0, 4, 0, 0, 28, 0, 40, 28, 0],
  mobius:     [0, 3, 2, 0, 1, 0, 0, 2, 2, 0, 1, 0, 0, 3, 2, 0],
  projective: [3, 6, 10, 3, 2, 2, 2, 3, 2, 3, 2, 22, 2, 38, 26, 3],
};

function buildExpectedTail() {
  const table = {};
  const width = TAIL_TO - TAIL_FROM + 1;
  for (const [surface, values] of Object.entries(TAIL_VALUES)) {
    if (values.length !== width) {
      throw new Error(`expected-tail.mjs: ${surface} has ${values.length} values, expected ${width}`);
    }
    const m = new Map();
    values.forEach((v, i) => m.set(TAIL_FROM + i, BigInt(v)));
    table[surface] = m;
  }
  return table;
}

export const EXPECTED_TAIL = buildExpectedTail();
