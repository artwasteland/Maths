// oversight/oeis/graceful-census/expected-extension.mjs
//
// Provenance-commented expected values for the six staged terms that
// ./verify-staged.mjs cannot recompute inside its budget.
//
// READ THIS BEFORE TRUSTING ANY NUMBER BELOW. Nothing in this file is a
// recomputation. Each entry is a TRANSCRIPTION, and the `from` list names, for
// every value, the committed file and line the transcription was taken from on
// 2026-07-27. A gate that compares the b-file to this table catches truncation
// of the b-file and a transcription slip in it. It does not, on its own,
// re-derive anything.
//
// The `recomputedElsewhere` field is the part that carries real weight, and it
// is deliberately separate from `from`. It is true only when a COMMITTED script
// re-derives the value from the graph definition every time that script runs.
// Where it is true the drift guard is backed by a live recomputation somewhere
// in this repository (just not one that opens the b-file, which is exactly the
// gap ./verify-staged.mjs was written to close). Where it is false, say so.
//
// SHAPE OF THE EVIDENCE, per value:
//
//   fan(10)  = 709732      recomputed by research/graceful-census/verify.mjs §3
//                          on every run of that 342 s gate, against its own
//                          literal at verify.mjs:56. NO permuted-recount
//                          artifact and NO OEIS cousin. This is the WEAKEST
//                          staged term in the directory: one committed engine,
//                          one committed literal, nothing outside.
//   fan(11)  = 4990632     recomputed by verify.mjs §3 (literal at verify.mjs:56)
//                          AND independently recounted under a seeded vertex
//                          permutation, staged at
//                          research/graceful-census/runs/independence-fan12.out:2.
//   fan(12)  = 39745364    NOT recomputed by any committed script (verify.mjs
//                          §3's fan array stops at n=11). Bound only to the
//                          committed permuted recount,
//                          runs/independence-fan12.out:4 (seed 12345) and :18
//                          (seed 9001, in a comment). No OEIS cousin exists.
//   helm(6)  = 7445904     recomputed by verify.mjs §3 (literal at verify.mjs:58)
//                          AND equal to 4*6*A387800(6) = 4*6*310246, where
//                          A387800 is an outside author's published OEIS
//                          sequence recorded at verify.mjs:51.
//   helm(7)  = 359216956   NOT recomputed by any committed script (verify.mjs
//                          §3's helm array stops at n=6). Bound to the committed
//                          permuted recount, runs/independence-fan12.out:6, AND
//                          to 4*7*A387800(7) = 4*7*12829177, the published value
//                          recorded at verify.mjs:212 (fetched 2026-07-20).
//   book(5)  = 4671840     recomputed by verify.mjs §3 (literal at verify.mjs:59)
//                          AND equal to 4*5!*A387795(5) = 4*120*9733, the
//                          published value recorded at verify.mjs:52.
//
// A NOTE ON WHAT THE OEIS IDENTITIES DO AND DO NOT PROVE. helm total =
// 4n*A387800(n) and book total = 4*n!*A387795(n) are exact relations between the
// total count and the up-to-symmetry count; ./verify-staged.mjs checks that the
// relation holds on the terms it recomputes itself (helm n=3..5, book n=2..4)
// before using it on the terms it cannot. Even so, applying the relation is
// arithmetic on somebody else's number, not an enumeration of the graph. It is
// strong evidence from an independent author and it is not a recomputation.

// index -> [value, ...citations]. A citation is "file:line  what is there".
const SOURCES = {
  "b-fan.txt": {
    10: {
      value: "709732",
      recomputedElsewhere: true,
      from: [
        "research/graceful-census/verify.mjs:56  NEW.fan data[8], recomputed and asserted by §3",
        "research/oeis-term-coverage/absence/absence-2026-07-27.json:1278  the committed OEIS absence-search payload (a record of a search, not a count)",
      ],
      // Recorded because it happened, and explicitly NOT counted as evidence.
      // On 2026-07-27 this repair session recomputed fan(10) out of band and got
      // 709732 from both engines (countByVertices 41.1 s, graceful.cpp 16.7 s).
      // That run's log was not committed, and by this project's standing rule a
      // check that is not committed to this repository does not exist. It is
      // written down so a later reader knows the observation was made, not so
      // the claim can lean on it.
      uncommittedObservation: "2026-07-27 out-of-band recompute agreed (JS 41.1 s, C++ 16.7 s); log not committed, so it counts for nothing",
    },
    11: {
      value: "4990632",
      recomputedElsewhere: true,
      from: [
        "research/graceful-census/verify.mjs:56  NEW.fan data[9], recomputed and asserted by §3",
        "research/graceful-census/runs/independence-fan12.out:2  fan(11) permuted = 4990632 (seed 12345, 2026-07-20)",
      ],
    },
    12: {
      value: "39745364",
      recomputedElsewhere: false,
      from: [
        "research/graceful-census/runs/independence-fan12.out:4  fan(12) permuted = 39745364 (seed 12345, 2026-07-20)",
        "research/graceful-census/runs/independence-fan12.out:18  fan(12) permuted = 39745364 (seed 9001, same date, recorded in a comment)",
        "research/graceful-census/verify.mjs:205  §8 literal, compared against the b-file's last line only",
      ],
    },
  },
  "b-helm.txt": {
    6: {
      value: "7445904",
      recomputedElsewhere: true,
      from: [
        "research/graceful-census/verify.mjs:58  NEW.helm data[3], recomputed and asserted by §3",
        "research/graceful-census/verify.mjs:51  A387800(6) = 310246, and §5(b) asserts helm(6) = 4*6*A387800(6)",
      ],
    },
    7: {
      value: "359216956",
      recomputedElsewhere: false,
      from: [
        "research/graceful-census/runs/independence-fan12.out:6  helm(7) permuted = 359216956 (seed 12345, 2026-07-20)",
        "research/graceful-census/verify.mjs:212  A387800(7) = 12829177 (fetched 2026-07-20), and §8(a) asserts helm(7) = 4*7*A387800(7)",
        "research/graceful-census/verify.mjs:206  §8 literal, compared against the b-file's last line only",
      ],
    },
  },
  "b-book-quadrilateral.txt": {
    5: {
      value: "4671840",
      recomputedElsewhere: true,
      from: [
        "research/graceful-census/verify.mjs:59  NEW.bookQuad data[4], recomputed and asserted by §3",
        "research/graceful-census/verify.mjs:52  A387795(5) = 9733, and §5(b) asserts book(5) = 4*5!*A387795(5)",
      ],
    },
  },
  // b-friendship.txt has no entry on purpose: ./verify-staged.mjs recomputes all
  // five of its staged terms (k=1..5) from the graph definition, so none of them
  // needs a transcription.
};

// Published "fundamentally different" (up-to-symmetry) counts by an outside
// author, used for the exact reductions above. Transcribed 2026-07-27 from
// research/graceful-census/verify.mjs, which records them with its own fetch
// dates. These are NOT our numbers.
//   A387800  "fundamentally different graceful labelings of the n-helm",
//            E. W. Weisstein, 2025. n=3..6 at verify.mjs:51; n=7 at verify.mjs:212.
//   A387795  "... of the n-quadrilateral book". n=1..5 at verify.mjs:52.
const PUBLISHED_FD = {
  A387800: { 3: 109n, 4: 777n, 5: 13077n, 6: 310246n, 7: 12829177n },
  A387795: { 1: 1n, 2: 16n, 3: 0n, 4: 417n, 5: 9733n },
};

function build() {
  const table = {};
  const provenance = {};
  for (const [file, rows] of Object.entries(SOURCES)) {
    table[file] = new Map();
    provenance[file] = new Map();
    for (const [idx, row] of Object.entries(rows)) {
      if (!row.from.length) throw new Error(`${file}: index ${idx} has no cited source`);
      if (!/^\d+$/.test(row.value)) throw new Error(`${file}: index ${idx} value is not an integer literal`);
      table[file].set(Number(idx), BigInt(row.value));
      provenance[file].set(Number(idx), row);
    }
  }
  return { table, provenance };
}

const { table: EXPECTED_EXTENSION, provenance: EXPECTED_PROVENANCE } = build();

export { EXPECTED_EXTENSION, EXPECTED_PROVENANCE, PUBLISHED_FD };
