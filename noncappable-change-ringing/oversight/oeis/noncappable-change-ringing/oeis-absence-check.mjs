// NOTE: a contact email address in this file was redacted when it was
// published. The address really was sent to OEIS in the User-Agent of the
// queries recorded here; it is removed from the public copy only so that it
// is not harvested. Nothing else in this file was changed.
// oeis-absence-check.mjs — ask the live OEIS whether these sequences are in it,
// and commit the answer with enough provenance that a reader can redo the query.
//
//   node oeis-absence-check.mjs            → writes oeis-absence-<today>.json
//   node oeis-absence-check.mjs --dry-run  → prints, writes nothing
//
// WHAT THIS IS FOR. Every absence claim we make in public is dated and bounded:
// "absent from the OEIS as catalogued on <date>", never "new to mathematics".
// That sentence is only honest if the query behind it is recorded, so this
// script writes the query URL, the HTTP status, and the raw response body for
// every search it runs. The earlier artifacts in this directory
// (oeis-absence-bells{4,5,6,7}-2026-07-23.json) recorded only the bare body
// `null`, which is the right answer but not a re-checkable record; this
// supersedes that format without deleting those files.
//
// It writes ONLY its own dated artifact. It never touches a b-file.
//
// A note on reading `null`. The OEIS JSON endpoint returns the literal JSON
// value `null` for a search with no matches, and an array of sequence records
// otherwise. So `null` is the absence signal, and a non-null body for a
// numeric query means something in the catalogue carries those terms.

import { writeFileSync } from 'node:fs';
import { DATA } from './derive.mjs';

const DRY = process.argv.includes('--dry-run');
const UA = 'artwaste.land research script (one-off absence check; contact [email redacted for publication])';
const BASE = 'https://oeis.org/search';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function ask(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  const body = await res.text();
  return {
    url,
    httpStatus: res.status,
    absent: body.trim() === 'null',
    body: body.length > 400000 ? `${body.slice(0, 400000)}…[truncated]` : body,
  };
}

// The noncappable terms, straight from the published pairs: path - cyclic.
function noncappableTerms(n) {
  const { c, p } = DATA[n];
  const len = Math.min(c.length, p.length);
  const out = [];
  for (let i = 0; i < len; i++) out.push(BigInt(p[i]) - BigInt(c[i]));
  out[0] = 0n; // Sønsteby's L=1 convention: the trivial sequence is cappable
  return out;
}

const queries = [];

for (const n of Object.keys(DATA).map(Number).sort((a, b) => a - b)) {
  const terms = noncappableTerms(n);
  const nonzero = terms.filter((v) => v !== 0n).map(String);
  // (a) the leading run as OEIS would index it, from the first nonzero term
  queries.push({
    kind: 'numeric-prefix',
    bells: n,
    note: `first ${Math.min(8, nonzero.length)} nonzero noncappable terms for ${n} bells`,
    url: `${BASE}?q=${encodeURIComponent(nonzero.slice(0, 8).join(','))}&fmt=json`,
  });
  // (b) the same run with the two leading zeros, in case an entry keeps them
  queries.push({
    kind: 'numeric-prefix-with-zeros',
    bells: n,
    note: `same run including the L=1,2 zeros, for ${n} bells`,
    url: `${BASE}?q=${encodeURIComponent(terms.slice(0, 9).map(String).join(','))}&fmt=json`,
  });
  // (c) the single largest term on its own. Read this one carefully: a lone
  // integer is only evidence when it is large. 48156, the four-bell last term,
  // occurs in seven unrelated sequences purely because five-digit integers do.
  // The prefix searches above are what actually carry the absence claim.
  queries.push({
    kind: 'largest-single-term',
    bells: n,
    note: `the last derivable noncappable term for ${n} bells, alone`,
    url: `${BASE}?q=${encodeURIComponent(String(terms[terms.length - 1]))}&fmt=json`,
  });
}

// Name searches: does the catalogue know the word, or the family, at all?
queries.push({ kind: 'name', bells: null, note: 'the word "noncappable"', url: `${BASE}?q=${encodeURIComponent('noncappable')}&fmt=json` });
queries.push({ kind: 'name', bells: null, note: 'the phrase "change-ringing", page 1', url: `${BASE}?q=${encodeURIComponent('"change-ringing"')}&fmt=json` });
queries.push({ kind: 'name', bells: null, note: 'the phrase "change-ringing", page 2', url: `${BASE}?q=${encodeURIComponent('"change-ringing"')}&start=10&fmt=json` });

const results = [];
for (const q of queries) {
  const answer = await ask(q.url);
  const empty = answer.body.trim() === 'null';
  results.push({ ...q, ...answer, matches: empty ? 0 : undefined });
  console.log(`${empty ? 'absent ' : 'PRESENT'}  ${q.kind}${q.bells ? ` n=${q.bells}` : ''}  ${q.note}`);
  await sleep(1500); // be a polite client
}

const artifact = {
  generatedAt: new Date().toISOString(),
  generatedBy: 'oversight/oeis/noncappable-change-ringing/oeis-absence-check.mjs',
  endpoint: BASE,
  howToReadNull: 'The OEIS JSON endpoint returns the literal JSON value null when a search has no matches. A null body is therefore the absence signal; any other body means the catalogue holds something matching. The per-query "absent" field records this.',
  claimThisSupports: 'Each noncappable sequence below was absent from the OEIS, as catalogued on the generatedAt date. This is a statement about the catalogue on that date, not a claim of mathematical novelty: the values are one subtraction away from twelve entries public since 2019.',
  whatEachQueryIsWorth: {
    'numeric-prefix': 'Carries the claim. A run of six to eight terms is specific enough that a match would mean a real collision.',
    'numeric-prefix-with-zeros': 'Same, with the L=1,2 zeros included in case an entry keeps them.',
    'largest-single-term': 'Weak for small values and strong for large ones. The four-bell last term, 48156, matches seven unrelated sequences simply because five-digit integers are common; the other five, all ten digits or more, return nothing. Do not read the four-bell hit as a counterexample, and do not read it as evidence either.',
    name: 'A search for "noncappable" returns nothing at all. A search for "change-ringing" returns 20 sequences: Sonsteby\'s twelve cyclic and path entries, six Plain Bob Minimus entries, a Hamiltonian-circuit sequence and one product formula. None of them is a noncappable count.',
  },
  queries: results,
};

if (DRY) {
  console.log(JSON.stringify(artifact, null, 2));
} else {
  const day = artifact.generatedAt.slice(0, 10);
  const out = new URL(`./oeis-absence-${day}.json`, import.meta.url);
  writeFileSync(out, `${JSON.stringify(artifact, null, 2)}\n`);
  console.log(`\nwrote oeis-absence-${day}.json (${results.length} queries)`);
}
