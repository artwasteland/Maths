// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// derive.mjs — the noncappable change-ringing sequences, term by term.
//
// noncappable(L) = path(L) - cyclic(L)  (for every L; =0 at L=1,2 by definition).
// We take the cyclic and path values straight from the published OEIS entries
// (each independently computed by J. K. Sønsteby and reproduced by ../engine.mjs)
// and subtract.  The result is, for each n, a sequence ABSENT from OEIS as of
// 2026-06-15 (verified: numeric search + name search returned nothing).
//
// The point of doing it from the *published* terms (not only our own engine) is
// reach: our DFS counter reproduces these cyclic/path values exactly as far as
// the verifier re-runs it (n=4 full; n=5 to L=12; n=6 to L=9; n=7 to L=7, all
// matching; see ENGINE_REACH below for why these were lowered), which
// certifies the subtraction; for the higher L only the published values exist, so
// the noncappable sequence inherits exactly their length and `more`/`full` status.

// --- published OEIS data (fetched 2026-06-15) ---
const DATA = {
  4: {
    cyclic: 'A324942', kw: 'full',
    c: [1,4,6,6,0,4,28,106,282,660,1496,3344,7176,14616,27560,47672,76092,112416,148808,166960,148848,98560,43424,10792],
    path: 'A324943',
    p: [1,4,12,30,72,186,464,1122,2646,6050,13408,28726,58844,114418,209176,355926,559108,800636,1014616,1086948,930728,595740,256688,58948],
  },
  5: {
    cyclic: 'A324944', kw: 'more',
    c: [1,7,18,50,120,418,2114,10140,41544,164022,730136,3770982,20541820,110476618,580834748,3013771544,15539996378,79715421726],
    path: 'A324945',
    p: [1,7,42,234,1264,6776,36094,190560,997774,5199588,27025854,140092710,723510594,3720320512,19044051770,97051434120,492383872912,2486705768206],
  },
  6: {
    cyclic: 'A324946', kw: 'more',
    c: [1,12,60,364,2040,11640,75572,584306,5025774,44468794,392052540,3439315382,30250738752],
    path: 'A324947',
    p: [1,12,132,1392,14348,146424,1488108,15083740,152484278,1537437464,15465605806,155275855726,1556493430588],
  },
  7: {
    cyclic: 'A324948', kw: 'more',
    c: [1,20,156,1668,17360,194908,2371824,31056188,430029780,6194026170,91889614586],
    path: 'A324949',
    p: [1,20,380,7064,129740,2368008,43069168,781583572,14160543572,256233400004,4631789851254],
  },
  // 8 and 9 bells added 2026-07-28, straight from the live catalogue (see
  // oeis-absence-2026-07-28.json for the fetch). Sønsteby carried the family
  // this far too; nobody had subtracted these pairs either. For these two the
  // cyclic list is LONGER than the path list, so the noncappable sequence stops
  // where the shorter of the pair stops: 8 bells at L=9, 9 bells at L=8. The
  // surplus cyclic terms are kept verbatim rather than trimmed, so the table
  // still matches OEIS line for line.
  8: {
    cyclic: 'A324950', kw: 'more',
    c: [1,33,408,7360,131400,2510632,50991416,1103346172,25248402996,604074338460],
    path: 'A324951',
    p: [1,33,1056,33384,1048280,32797176,1023968632,31928050304,994658931028],
  },
  9: {
    cyclic: 'A324952', kw: 'more',
    c: [1,54,996,28884,834680,26371654,885870328,31508181992,1175640098592],
    path: 'A324953',
    p: [1,54,2862,150690,7905894,413992474,21654687592,1131904942380],
  },
};

// Published term counts, as catalogued 2026-07-28. Asserted rather than assumed:
// a silently truncated or silently extended OEIS entry would otherwise change a
// staged b-file's length without anything noticing.
const PUBLISHED_TERMS = {
  4: { cyclic: 24, path: 24 },
  5: { cyclic: 18, path: 18 },
  6: { cyclic: 13, path: 13 },
  7: { cyclic: 11, path: 11 },
  8: { cyclic: 10, path: 9 },
  9: { cyclic: 9, path: 8 },
};

// How far the subtraction can go for each n: the shorter of the published pair.
const derivableLength = (n) => Math.min(DATA[n].c.length, DATA[n].p.length);

// engine cross-check ranges (how far ../engine.mjs was independently run & matched)
// Lowered 2026-07-23 to the depths verify.mjs actually re-runs (the old
// 13/10/8 claim was not reproducible within the verifier's runtime budget;
// the n=5 L=13 values are nonetheless machine-checked, by the compiled
// from-definition enumerator committed at
// research/change-ringing-sequences/extension/codex-verify/blind/).
// 8 and 9 bells added 2026-07-28, at the depths engine.mjs was actually re-run
// and matched OEIS exactly (n=8 to L=6 in 3.0 s, n=9 to L=5 in 14.0 s, both on
// liam-desktop under nice -n 19). n=9 was additionally matched to L=6 in a
// one-off 43.2 s run, and n=8 to L=7 in a one-off 65.6 s run; both kept out of
// the verifier only for runtime.
const ENGINE_REACH = { 4: 24, 5: 12, 6: 9, 7: 7, 8: 6, 9: 5 };

const BELLS = [4, 5, 6, 7, 8, 9];

function noncappable(n) {
  const { c, p } = DATA[n];
  const len = derivableLength(n);
  const out = [];
  for (let i = 0; i < len; i++) out.push(BigInt(p[i]) - BigInt(c[i]));
  return out;
}

const results = {};
for (const n of BELLS) {
  const nc = noncappable(n);
  results[n] = nc;
  // sanity invariants
  if (nc[0] !== 0n || nc[1] !== 0n) throw new Error(`n=${n}: noncappable(1) or (2) != 0`);
  for (const v of nc) if (v < 0n) throw new Error(`n=${n}: negative noncappable term`);
  // the published lengths are asserted, not assumed
  const want = PUBLISHED_TERMS[n];
  if (DATA[n].c.length !== want.cyclic || DATA[n].p.length !== want.path) {
    throw new Error(`n=${n}: published term counts moved (cyclic ${DATA[n].c.length}/${want.cyclic}, path ${DATA[n].p.length}/${want.path})`);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const n of BELLS) {
    const nc = results[n];
    console.log(`# n=${n} bells: noncappable = ${DATA[n].path} - ${DATA[n].cyclic} (${nc.length} terms, kw:${DATA[n].kw}, engine-checked to L=${ENGINE_REACH[n]})`);
    console.log(nc.map((x) => x.toString()).join(', '));
    console.log();
  }
}

export { results as noncappable, DATA, ENGINE_REACH, PUBLISHED_TERMS, BELLS, derivableLength };
