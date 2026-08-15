// Expected values for the two staged terms this directory's gate cannot recompute.
//
// WHAT THIS FILE IS, AND WHAT IT IS NOT. This is DRIFT PROTECTION, not an
// independent recomputation. verify-staged.mjs recomputes a(1)..a(11) from
// research/topswops/engine.mjs inside its time budget; a(12) and a(13) are
// beyond it, because the engine enumerates all n! decks and 13! is about 6.2
// billion. For those two terms the gate reads the staged b-file and compares it
// against the table below. That catches truncation of the b-file and a
// transcription slip in it. It CANNOT catch a wrong original computation: if
// the 2026-06-24 run was wrong, this table is wrong in exactly the same way,
// and the gate will agree with it and go green.
//
// PROVENANCE OF EACH VALUE, honestly. The originating run is NOT committed.
// There is no stdout log, no runs/*.out file, and no recorded transcript for
// the computation that produced a(12) and a(13) anywhere in this repository,
// unlike (for one contrasting example) the change-ringing extension, whose
// sibling table at oversight/oeis/noncappable-change-ringing/expected-extension.mjs
// cites committed run files line by line. What exists here is the number as it
// was transcribed into several committed places on 2026-06-24, plus a
// re-derivation of BOTH values done on 2026-07-27 and recorded per value in the
// comments below. Those re-derivations used the same engine as the original, so
// they establish that the numbers are reproducible from the committed code and
// were transcribed without error. They do not make either term independently
// verified, and they are not a second method.
//
// The `witnesses` listed per value are independent TRANSCRIPTIONS, not
// independent COMPUTATIONS. They all descend from the same single 2026-06-24
// engine run. Their agreement rules out a typo in any one of them; it says
// nothing about whether that run was correct. buildExpected() throws if they
// ever disagree, which is the only thing their agreement can honestly buy.
'use strict';

const SOURCES = {
  // ---------------------------------------------------------------------
  // a(12) = 3758940272
  //   Origin: an uncommitted run of maxAndSum(12) from research/topswops/engine.mjs
  //   on 2026-06-24, described at memory/log.d/2026-06-24T2130Z-topswops-machine.md:21
  //   as "n=12 = 479M decks in ~75s". The run's output was never committed.
  //   RE-DERIVED 2026-07-27 in this container (Node v22.22.2) by calling
  //   maxAndSum(12) directly: returned sum=3758940272, M=65, in 98.6 s. That
  //   re-derivation used the SAME engine as the original, so it confirms the
  //   number was transcribed correctly and is reproducible from the committed
  //   code. It is not a second method and does not make a(12) independently
  //   verified. Its output was not committed either, so this comment, not a
  //   file, is the record of it.
  // ---------------------------------------------------------------------
  12: {
    value: '3758940272',
    witnesses: [
      ['draft.txt:16 (%S line)', '3758940272'],
      ['README.md:11 (sequence listing)', '3758940272'],
      ['.zenodo.json (description and notes, both listings)', '3758940272'],
      ['memory/log.d/2026-06-24T2130Z-topswops-machine.md:25 (n=1..12 listing)', '3758940272'],
      ['public/strata/topswops-machine/index.html (built stratum page)', '3758940272'],
    ],
  },

  // ---------------------------------------------------------------------
  // a(13) = 54349566758
  //   Origin: an uncommitted longer run, reported at
  //   memory/log.d/2026-06-24T2130Z-topswops-machine.md:53 as "a(13) =
  //   54,349,566,758 landed (M(13)=80, another A000375 calibration point)".
  //   No output file, no timing record, no transcript was committed.
  //   RE-DERIVED 2026-07-27 in this container (Node v22.22.2) by calling
  //   maxAndSum(13) directly: returned sum=54349566758, M=80, in 1348.1 s
  //   (22.5 min, on a machine shared with other work). Same caveat as a(12):
  //   the SAME engine, so this confirms the number is reproducible from the
  //   committed code and was transcribed correctly. It is NOT a second method
  //   and does not make a(13) independently verified. 22 minutes is far outside
  //   a gate's budget, which is why the value is tabulated here instead.
  //   One genuinely external fact did come out of that run: M(13)=80 matches
  //   the catalogued A000375(13)=80. That is real outside evidence about the
  //   ENGINE at n=13, though it says nothing about the total-steps sum itself.
  //   The run's stdout was not committed, so this comment is its record.
  // ---------------------------------------------------------------------
  13: {
    value: '54349566758',
    witnesses: [
      ['draft.txt:16 (%S line)', '54349566758'],
      ['README.md:11 (sequence listing)', '54349566758'],
      ['.zenodo.json (description and notes, both listings)', '54349566758'],
      ['memory/log.d/2026-06-24T2130Z-topswops-machine.md:53 (hand-off note)', '54349566758'],
      ['public/strata/topswops-machine/index.html (built stratum page)', '54349566758'],
    ],
  },
};

function buildExpected() {
  const table = new Map();
  for (const [n, entry] of Object.entries(SOURCES)) {
    for (const [where, seen] of entry.witnesses) {
      if (seen !== entry.value) {
        throw new Error(`Conflicting transcriptions for a(${n}): ${entry.value} != ${seen} (${where})`);
      }
    }
    table.set(Number(n), BigInt(entry.value));
  }
  return table;
}

const EXPECTED_EXTENSION = buildExpected();

// Exported so the gate can print the witness count and say, in its own output,
// how thin this evidence is rather than making the reader open this file.
const EXPECTED_WITNESSES = new Map(
  Object.entries(SOURCES).map(([n, e]) => [Number(n), e.witnesses.map(([w]) => w)]),
);

export { EXPECTED_EXTENSION, EXPECTED_WITNESSES };
