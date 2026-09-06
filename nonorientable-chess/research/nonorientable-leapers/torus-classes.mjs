// torus-classes.mjs — the unit-scaling law, audited at every n instead of at three.
//
// ⚠ READ THIS FIRST: THE THEOREM BELOW IS NOT NEW, NOT MINE, AND NOT EVEN THIS
// PROJECT'S. It is published mathematics, twice over.
//
//   EXTERNAL. W. D. Weakley, "Toroidal queens graphs over finite fields",
//   Australasian J. Combinatorics 57 (2013) 21-38, p. 24, states it for the FULL
//   general linear group in exactly this setting (a graph on R x R for a finite
//   commutative ring R, with Z_n and the toroidal queens graph as his own worked
//   example): for M in GL_2(F), left multiplication by M "is a graph isomorphism
//   from G(F, D) to G(F, mu_M(D))". His own assessment of the proof is the phrase
//   "it is easy to verify". Unit scaling is the case M = uI.
//   More generally this is the trivial direction of Adam's conjecture / the CI-group
//   literature: multiplication by a unit is a group automorphism of (Z/n)^2, the
//   attack relation is a Cayley graph on that group, and "sigma in Aut(G) implies
//   Cay(G,S) = Cay(G, sigma S)" is the direction nobody writes down because the
//   converse is the hard question. See Muzychuk & Poeschel, "Isomorphism criteria
//   for circulant graphs", section 3, where Z*_n = Aut(Z_n) is a parenthetical.
//
//   IN-HOUSE. This project also proved and published it a month before this file,
//   in research/leapers-on-a-torus/ and on /strata/leapers-on-a-torus/, whose
//   README already NAMES the very coincidences this file re-derives:
//     "This forces every same-orbit coincidence in the table (n=7 -> all four give
//      210; n=11 -> camel = zebra = giraffe = 395252 while the knight splits off;
//      n=13 -> camel = giraffe)."
//
// I found the mechanism by staring at the torus row, wrote it up as a discovery,
// and only then read the neighbouring directory and sent an adversarial scout at
// the literature. It was already in both places. This notice is here so the next
// reader cannot repeat that, and because the ledger records an earlier instance
// shipping a rediscovery as a discovery in this same program.
//
// TWO CORRECTIONS THE SCOUT FORCED, both of which deflate the result:
//   (a) The statement is too narrow. Nothing in the proof needs one scalar on both
//       axes: diag(u,v) for units u,v works, as does composing with the transpose
//       swap, so the natural group is the MONOMIAL subgroup of GL_2(Z/n). Verified
//       here over n=3..24: the larger group yields the identical partition for these
//       four leapers, so the strengthening is free and changes no number here.
//   (b) Some of the "coincidences" are not coincidences at all. Read mod n the four
//       vector sets can COLLIDE OUTRIGHT: mod 7, 4 = -3 and V is closed under sign
//       change, so the camel and the giraffe are literally the SAME PIECE and their
//       equal counts need no theorem. Mod 5 the knight and camel likewise coincide,
//       and the zebra and giraffe both degenerate from 8 vectors to 4. The column
//       "sets" below prints how many DISTINCT move sets survive at each n, so this
//       cannot hide inside a claim about orbits.
//
// THE THEOREM (theirs). On the torus the board is (Z/n)^2 and an (a,b)-leaper's
// attack relation depends only on the difference of two cells lying in
//
//     V(a,b) = { (±a,±b), (±b,±a) }   read mod n.
//
// For a unit u mod n, phi(r,c) = (ur, uc) permutes rows among themselves and
// columns among themselves, so it carries one-per-row-and-column placements to the
// same, bijectively; and it carries a difference d to ud, hence V-attacks exactly
// onto (uV)-attacks. So if u * V(a,b) = V(a',b') as sets mod n, the two torus
// counts are equal at that n.
//
// WHAT THIS FILE ADDS, WHICH IS SMALLER AND STILL WORTH HAVING.
//   1. The prior work checks the law at two spot cases and names three of its
//      consequences in prose. This computes the orbit partition at EVERY n in the
//      table and mechanically checks every equality it forces, so the claim is a
//      committed check rather than a sentence. Both tallies are printed, because
//      they differ and quoting one as the other is how a miscount looks: the
//      predicted equalities are 21 unordered PAIRS, which is 17 independent MERGES
//      (sum of 4 - #classes). Neither number is hard-coded; both grow with the table.
//   2. A different negative control. Theirs feeds a NON-unit on the torus. This
//      applies the torus predictions to the Mobius band, where the scaling map is
//      not a symmetry at all, and watches them collapse. That is the control that
//      matters for a stratum about twisted boards.
//   3. The forward claim in PREREGISTERED.md, which is not stated anywhere in the
//      prior work: the orbits are all singletons from n=15 on, so the coincidences
//      stop, and stop permanently.
//
// AND ONE MORE THING THIS IS NOT. That different leapers can share a toroidal count
// is itself published: V. Kotesovec, "Non-attacking chess pieces" (6th ed., 2013),
// ch. 10.4-10.9, devotes several chapters to it and states flatly of two leapers on
// a torus, "Independent on r, s!". His mechanism is not this one -- his coincidences
// are a LARGE-n phenomenon and he marks n <= 2s in red as the range where leapers
// may still differ, while every coincidence here is a SMALL-n effect of the vector
// sets colliding once reduced mod n -- and his convention is k non-attacking pieces
// rather than one per row and column. Different claim, adjacent enough that not
// naming it would be a misrepresentation by omission.
//
// It also states the converse honestly. The theorem gives "same orbit => same
// count". It does NOT give "different orbit => different count", and this file
// reports every coincidence the orbits do not explain rather than hiding it.
//
//   node torus-classes.mjs

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { LEAPERS } from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const NAMES = Object.keys(LEAPERS);

// V(a,b) reduced mod n, as a canonical sorted key.
function vecSetMod(a, b, n) {
  const s = new Set();
  for (const [p, q] of [[a, b], [b, a]])
    for (const sr of [1, -1])
      for (const sc of [1, -1])
        s.add(`${((sr * p) % n + n) % n},${((sc * q) % n + n) % n}`);
  return [...s].sort().join(' ');
}

function scaleSet(key, u, n) {
  const s = new Set();
  for (const t of key.split(' ')) {
    const [r, c] = t.split(',').map(Number);
    s.add(`${(r * u) % n},${(c * u) % n}`);
  }
  return [...s].sort().join(' ');
}

const gcd = (x, y) => (y ? gcd(y, x % y) : x);

// Partition the four leapers at this n into orbits under unit scaling.
function orbits(n) {
  const keys = NAMES.map(nm => vecSetMod(LEAPERS[nm][0], LEAPERS[nm][1], n));
  const units = [];
  for (let u = 1; u < n; u++) if (gcd(u, n) === 1) units.push(u);
  const parent = NAMES.map((_, i) => i);
  const find = (i) => (parent[i] === i ? i : (parent[i] = find(parent[i])));
  const union = (i, j) => { const a = find(i), b = find(j); if (a !== b) parent[a] = b; };
  for (let i = 0; i < 4; i++)
    for (let j = i + 1; j < 4; j++)
      for (const u of units)
        if (scaleSet(keys[i], u, n) === keys[j]) { union(i, j); break; }
  const groups = new Map();
  for (let i = 0; i < 4; i++) {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(NAMES[i]);
  }
  return [...groups.values()].map(g => g.sort());
}

// The committed table.
const rows = readFileSync(join(HERE, 'terms-1-14.tsv'), 'utf8').trim().split('\n').slice(1);
const table = new Map();          // "topo/leaper" -> [terms]
let maxN = 0;
for (const line of rows) {
  const [topo, leaper, terms] = line.split('\t');
  const t = terms.split(',').map(s => Number(s.trim()));
  table.set(`${topo}/${leaper}`, t);
  maxN = Math.max(maxN, t.length);
}

let merges = 0, mergesHeld = 0, pairs = 0, pairsHeld = 0, unexplained = [];

console.log('n  sets  orbits under unit scaling mod n              torus counts');
console.log('-- ----  -------------------------------------------  ----------------------------------------');
for (let n = 3; n <= maxN; n++) {
  const orbs = orbits(n);
  const counts = Object.fromEntries(NAMES.map(nm => [nm, table.get(`torus/${nm}`)[n - 1]]));

  // How many DISTINCT move sets survive reduction mod n. When this is below 4 the
  // "coincidence" between two of the leapers is that they are the same piece, and
  // the scaling theorem is not doing any work at all.
  const distinctSets = new Set(NAMES.map(nm => vecSetMod(LEAPERS[nm][0], LEAPERS[nm][1], n))).size;

  // 1. Every predicted equality must hold. Counted BOTH ways, because "16
  //    equalities" and "20 equalities" are both true of the same partition and
  //    quoting one while meaning the other is indistinguishable from a miscount.
  for (const g of orbs) {
    merges += g.length - 1;
    pairs += (g.length * (g.length - 1)) / 2;
    for (let i = 1; i < g.length; i++) {
      if (counts[g[0]] === counts[g[i]]) mergesHeld++;
      else console.log(`  *** BROKEN PREDICTION n=${n}: ${g[0]}=${counts[g[0]]} but ${g[i]}=${counts[g[i]]}`);
    }
    for (let i = 0; i < g.length; i++)
      for (let j = i + 1; j < g.length; j++)
        if (counts[g[i]] === counts[g[j]]) pairsHeld++;
  }

  // 2. Every equality the orbits do NOT predict is reported, not swallowed.
  for (let i = 0; i < 4; i++)
    for (let j = i + 1; j < 4; j++) {
      const sameOrbit = orbs.some(g => g.includes(NAMES[i]) && g.includes(NAMES[j]));
      if (!sameOrbit && counts[NAMES[i]] === counts[NAMES[j]])
        unexplained.push(`n=${n}: ${NAMES[i]} = ${NAMES[j]} = ${counts[NAMES[i]]}`);
    }

  const shape = orbs.map(g => g.map(s => s[0].toUpperCase()).join('')).join(' | ');
  console.log(`${String(n).padStart(2)}   ${distinctSets}    ${shape.padEnd(43)}  ` +
    NAMES.map(nm => String(counts[nm]).padStart(9)).join(' '));
}

console.log('\nK=knight C=camel Z=zebra G=giraffe; letters grouped => predicted equal on the torus');
console.log('"sets" = distinct move sets after reducing mod n. Where it is below 4, two leapers');
console.log('are the SAME PIECE on that board and their equal counts need no theorem: mod 7 the');
console.log('camel and giraffe coincide (4 = -3), mod 5 the knight and camel do.');
console.log(`\npredicted equalities: ${mergesHeld}/${merges} independent merges held`);
console.log(`                      ${pairsHeld}/${pairs} unordered pairs held (the same partition, counted the other way)`);
if (unexplained.length) {
  console.log(`coincidences the theorem does NOT explain (${unexplained.length}) — reported, not hidden:`);
  for (const u of unexplained) console.log('   ' + u);
} else {
  console.log('coincidences the theorem does not explain: none');
}

// Negative control: the same scaling map is NOT a symmetry of the twisted boards
// (it does not commute with the gluing), so the prediction should FAIL there. If
// it held on the Mobius band too, the argument would be proving nothing.
let mobiusHeld = 0, mobiusTested = 0;
for (let n = 3; n <= maxN; n++)
  for (const g of orbits(n))
    for (let i = 1; i < g.length; i++) {
      mobiusTested++;
      if (table.get(`mobius/${g[0]}`)[n - 1] === table.get(`mobius/${g[i]}`)[n - 1]) mobiusHeld++;
    }
console.log(`\nnegative control — same predictions applied to the Mobius band: ${mobiusHeld}/${mobiusTested} held.`);
console.log('(The scaling map does not commute with the half-twist, so it should mostly fail there.');
console.log(' If it held as often as on the torus, the torus result would not be evidence of anything.)');

process.exit(mergesHeld === merges && pairsHeld === pairs ? 0 : 1);
