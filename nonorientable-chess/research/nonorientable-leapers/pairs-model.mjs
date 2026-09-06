// pairs-model.mjs — the constraint count in closed form, and how much of the
// leaper count it actually explains.
//
// WHAT THIS ADDS TO density.mjs, which came first and is the parent of this file.
// density.mjs computes P (attacking pairs in distinct rows and columns) numerically
// per surface, prints the independence heuristic n! * exp(-P/(n(n-1))), and asks one
// yes/no question: is P the same on the torus and the Klein bottle? Its answer is NO.
// That answer is true and it is also the least informative true thing available,
// because the two numbers differ by a CONSTANT (6, 8, 10 or 16 depending on leaper and
// parity) against a quantity of size 4n^2. This file replaces the yes/no with the
// closed forms, which turn out to be exact and to say something structural:
//
//     torus    P = 4n^2                          (no boundary at all)
//     klein    P = 4n^2 - k(a,b,n mod 2)         (closed; k is a small constant)
//     mobius   P = 4n^2 - 2(a+b)n - k'           (ONE free boundary)
//     flat     P = 4(n-a)(n-b)                   (TWO free boundaries)
//                = 4n^2 - 4(a+b)n + 4ab
//
// Read the linear term: it is 0, 0, -2(a+b)n, -4(a+b)n as the number of free
// boundaries goes 0, 0, 1, 2. Every difference in constraint count between these four
// surfaces is a boundary effect and nothing else, and the twist contributes only O(1).
// That is why the Mobius counts sit far above the torus counts while the Klein counts
// sit almost on top of them: the Mobius band is the only one of the four that is open
// in a direction, so it is the only one that loses a term of order n.
//
// AND THE LEADING TERMS ARE NOT A FIT. They are a two-line count, which a reader can
// redo by hand; the code below only checks that the count is right. A leaper (a,b) has
// the 8 move vectors (+-a,+-b) and (+-b,+-a), four of them with row-step +-a and four
// with row-step +-b. For one vector v = (dr,dc), the number of ORDERED pairs
// (cell, cell+v) with both ends on the board is just the number of starting cells whose
// image lands somewhere, and that depends only on which axes wrap:
//
//   flat    rows and columns both bounded   (n-|dr|)(n-|dc|)
//   torus   both wrap                       n^2
//   klein   both wrap (rows with a flip)    n^2
//   mobius  columns wrap, rows are free     (n-|dr|) * n
//
// Halve the sum over the 8 vectors, since each unordered pair is reached from both ends:
//
//   flat     [4(n-a)(n-b) + 4(n-b)(n-a)] / 2 = 4(n-a)(n-b)
//   mobius   [4(n-a)n     + 4(n-b)n    ] / 2 = 4n^2 - 2(a+b)n
//   torus    [8 n^2]                     / 2 = 4n^2
//   klein    same as torus                   = 4n^2
//
// The O(1) leftovers are the pairs thrown away for sharing a row or a column once
// folded, which the permutation convention already forbids, and they are where the
// half-twist and the parity of n show up. So the FORMS below are fitted on three points
// and then TESTED on the rest of the range as an arithmetic check on the paragraph
// above; the run prints the smallest n from which each holds and fails loudly if one
// breaks, and it separately asserts the three leading terms this derivation predicts.
//
// SECOND THING THIS ADDS: the residual. Write
//
//     a(n) = n! * exp(-P/(n(n-1))) * R(n)
//
// so R is exactly the factor the independence heuristic misses. R is not 1 and does
// not look like it is heading to 1 quickly. But it is SMOOTH, and that makes it a
// predictor: carry R(n-1) forward one step and you get a(n) without enumerating it.
//
// The test set is not ours. The four FLAT rows are published in the OEIS out to
// n = 23, 24 and (for the knight, via Martin Fuller's b-file) n = 30, far past
// anything this project has enumerated, so carrying R forward one step over that
// range scores the rule against 45 integers nobody here computed. The rule has no
// free parameters, so there is nothing to tune to make it fit.
//
// ⚠ WHAT IS NOT OURS, STATED BEFORE THE RESULT RATHER THAN AFTER IT.
// The LIMIT of this heuristic is published, and it is published for exactly this
// family. A137774 carries, in its own FORMULA lines:
//
//     "Asymptotics: a(n)/n! -> 1/e^4."
//     "General asymptotic formulas for number of ways to place n nonattacking
//      pieces rook + leaper[r,s] on an n X n board:
//        a(n)/n! -> 1/e^2 for 0<r=s
//        a(n)/n! -> 1/e^4 for 0<r<s"
//
// crediting V. Kotesovec, "Non-attacking chess pieces" 6ed (2013), pp. 636, 637, 685.
// That is precisely lim exp(-E) here, since a leaper with 0<r<s has 8 distinct
// vectors and E -> 4, while r=s gives 4 vectors and E -> 2. So the ASYMPTOTIC IS
// HIS. density.mjs already said so and this file repeats it, because the fact that
// a number falls out of your own model is not evidence that you found it.
//
// What is left, and it is narrow: the exact finite-n P on the three glued surfaces
// with the boundary law that orders them; the observation that the finite-n residual
// is smooth enough to carry one step and land inside half a per cent; and the
// negative control that says where that stops being true. Kotesovec's book runs to
// 795 pages and an asymptotic chapter, so a finite-n expansion for the flat row may
// well be in it; this file does not claim otherwise. What is certainly not in it is
// the Mobius and Klein rows, because those sequences did not exist until this
// project computed them.
//
// Run:
//   node pairs-model.mjs              closed forms, the OEIS out-of-sample score
//   node pairs-model.mjs --predict    the same, plus predictions for n = 15
//   node pairs-model.mjs --score      score those predictions against terms-1-15.tsv

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { attackGraph, leaperVectors, LEAPERS } from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const TOPOS = ['flat', 'torus', 'mobius', 'klein'];

// ---------------------------------------------------------------------------
// P: attacking pairs in distinct rows AND distinct columns. Same definition as
// density.mjs, recomputed here rather than imported so the two files are
// independent readings of the same quantity.
// ---------------------------------------------------------------------------
function forbiddenPairs(topo, n, V) {
  const adj = attackGraph(topo, n, V);
  let p = 0;
  for (let u = 0; u < n * n; u++) {
    const ru = (u / n) | 0, cu = u % n;
    for (let w = u + 1; w < n * n; w++) {
      if (!((adj[u] >> BigInt(w)) & 1n)) continue;
      const rw = (w / n) | 0, cw = w % n;
      if (ru === rw || cu === cw) continue;
      p++;
    }
  }
  return p;
}

const logFact = n => { let s = 0; for (let i = 2; i <= n; i++) s += Math.log(i); return s; };

// ---------------------------------------------------------------------------
// The published FLAT rows, read from the OEIS JSON API on 2026-08-20; the knight row is extended to n = 30 from
// Martin Fuller's b-file b137774.txt, fetched the same day.
// Stored as a(1), a(2), ... so the index is n-1 for every row regardless of the
// sequence's own offset. THAT NORMALISATION IS THE EXACT PLACE THIS GOES WRONG
// (the README records an earlier off-by-one here from counting positions in a
// comma-separated string), so alignment is asserted below against the committed
// table rather than trusted.
// ---------------------------------------------------------------------------
const OEIS = {
  knight: { id: 'A137774', offset: 1, terms: ['1', '2', '2', '8', '20', '94', '438', '2766', '19480', '163058', '1546726', '16598282', '197708058', '2586423174', '36769177348', '563504645310', '9248221393974', '161670971937362', '2996936692836754', '58689061747521430', '1210222434323163704', '26204614054454840842', '594313769819021397534', '14086979362268860896282', '348273084172862569577746', '8964776053304919407882910', '239863132830252316498762876', '6660991630521722556456207606', '191718651591688523895594715990', '5711947913120301491306465073690'] },
  camel: { id: 'A189358', offset: 0, terms: ['1', '2', '6', '8', '24', '126', '524', '3072', '22854', '189646', '1827114', '19889946', '238648524', '3131979014', '44540692612', '681114241416', '11136984461270', '193789753475756', '3573917236166756', '69613817201521582', '1427770479914412342', '30751016323750655016', '693825367670892366304', '16363895618578740904048'] },
  zebra: { id: 'A189565', offset: 0, terms: ['1', '2', '6', '12', '36', '174', '708', '4334', '31424', '263732', '2503296', '26844578', '316692056', '4090634212', '57274447458', '863488976620', '13936836270282', '239671043845414', '4373134317035736', '84359695604398332', '1715005778751119200', '36640921525885388532', '820633826572411883562', '19223689999433522041322'] },
  giraffe: { id: 'A189563', offset: 0, terms: ['1', '2', '6', '24', '48', '182', '868', '5752', '37156', '296944', '2738820', '28894206', '335399468', '4285522402', '59536763892', '892785282788', '14347054185602', '245880923199152', '4473839857744204', '86101137756244992', '1746946085050010604', '37260139829836652906', '833279639470464066112'] },
};

// ---------------------------------------------------------------------------
// THE NEGATIVE CONTROL, and it is the part that gives the score below a meaning.
//
// "Median error 0.36%" is worth nothing on its own, because a procedure that
// cannot fail is not evidence. So the same procedure, unchanged, is pointed at the
// nearest neighbouring family that uses the SAME convention: the n-queens counts,
// A000170, published to n = 27. A queens placement is a permutation with no two on
// a diagonal, which is one-per-row-and-column exactly as here.
//
// It fails, by about 32 per cent, and it keeps failing all the way out to n = 27.
//
// And the failure is not noise, which is the useful part. A queen is a SLIDER, so
// the number of attacking pairs is
//     P = 2(2C(n,3) + C(n,2)) ~ (2/3)n^3,
// and therefore E = P/(n(n-1)) ~ (2/3)n grows without bound. A leaper's P is
// 4n^2 + O(n), so its E tends to the constant 4. The independence heuristic needs a
// bounded expected number of attacks, and the residual only settles when E does. For
// the queens the residual does not settle at all: it decays by a near-constant factor
// of about 0.76 per step, and 1/0.76 - 1 is the 32 per cent the rule is wrong by.
//
// So the boundary is sharp and it is stated rather than hidden: this rule is for
// FIXED-JUMP pieces, where P is quadratic. It has no business on a slider, and the
// control below proves the comparison could have said so about the leapers too.
// ---------------------------------------------------------------------------
const QUEENS = ['1', '1', '0', '0', '2', '10', '4', '40', '92', '352', '724', '2680', '14200', '73712', '365596', '2279184', '14772512', '95815104', '666090624', '4968057848', '39029188884', '314666222712', '2691008701644', '24233937684440', '227514171973736', '2207893435808352', '22317699616364044', '234907967154122528'];
const binom = (n, k) => { let r = 1; for (let i = 0; i < k; i++) r = r * (n - i) / (i + 1); return Math.round(r); };
const queensP = n => 2 * (2 * binom(n, 3) + binom(n, 2));
// P by brute force, so the closed form above is checked and not asserted
function queensPbrute(n) {
  let p = 0;
  for (let r1 = 0; r1 < n; r1++) for (let c1 = 0; c1 < n; c1++)
    for (let r2 = r1; r2 < n; r2++) for (let c2 = 0; c2 < n; c2++) {
      if (r2 === r1 && c2 <= c1) continue;
      if (r1 === r2 || c1 === c2) continue;
      if (Math.abs(r1 - r2) === Math.abs(c1 - c2)) p++;
    }
  return p;
}

function loadTerms(file) {
  const path = join(HERE, file);
  if (!existsSync(path)) return null;
  const out = {};
  for (const line of readFileSync(path, 'utf8').trim().split('\n').slice(1)) {
    const [topo, leaper, terms] = line.split('\t');
    out[`${topo}/${leaper}`] = terms.split(',').map(s => s.trim());
  }
  return out;
}

// ---------------------------------------------------------------------------
// Closed forms. Fit a quadratic through three points at one parity, then TEST it
// on every other n of that parity in the range. Report the first n from which the
// form holds continuously to the end of the range.
// ---------------------------------------------------------------------------
function closedForm(topo, V, parity, lo, hi) {
  const ns = []; for (let n = lo; n <= hi; n++) if (n % 2 === parity) ns.push(n);
  const [[x1, y1], [x2, y2], [x3, y3]] = ns.slice(-3).map(n => [n, forbiddenPairs(topo, n, V)]);
  const d = (x1 - x2) * (x1 - x3) * (x2 - x3);
  const A = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / d;
  const B = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / d;
  const C = (x2 * x3 * (x2 - x3) * y1 + x3 * x1 * (x3 - x1) * y2 + x1 * x2 * (x1 - x2) * y3) / d;
  let firstOk = null;
  for (const n of ns) {
    const ok = Math.abs(forbiddenPairs(topo, n, V) - (A * n * n + B * n + C)) < 1e-6;
    if (ok && firstOk === null) firstOk = n;
    if (!ok) firstOk = null;
  }
  return { A, B, C, firstOk };
}

const fmtQuad = ({ A, B, C }) =>
  `${A}n^2${B ? (B < 0 ? ' - ' + -B : ' + ' + B) + 'n' : ''}${C ? (C < 0 ? ' - ' + -C : ' + ' + C) : ''}`;

// ---------------------------------------------------------------------------
function main() {
  const argv = process.argv.slice(2);
  const wantPredict = argv.includes('--predict');
  const wantScore = argv.includes('--score');
  let failures = 0;

  const committed = loadTerms('terms-1-14.tsv');
  if (!committed) { console.error('terms-1-14.tsv missing'); process.exit(1); }

  // -- POSITIVE CONTROL on the OEIS alignment ------------------------------
  // A comparison that cannot fire is not evidence. Every OEIS row must reproduce
  // the committed flat term at n = 14 under the index rule this file uses, and the
  // control below deliberately checks a NEIGHBOURING index too, so that an
  // off-by-one shows up as a pass where a pass is impossible.
  console.log('OEIS alignment control (index rule: a(n) = terms[n-1])');
  for (const L of Object.keys(OEIS)) {
    const mine = committed[`flat/${L}`][13];            // our n = 14
    const theirs = String(OEIS[L].terms[13]);
    const neighbour = String(OEIS[L].terms[14]);
    const ok = mine === theirs, wrongOk = mine === neighbour;
    console.log(`  ${OEIS[L].id} ${L.padEnd(8)} n=14 ours ${mine.padStart(12)} vs theirs ${theirs.padStart(12)}  ${ok ? 'MATCH' : 'MISMATCH'}` +
      `   (shifted index would give ${neighbour}: ${wrongOk ? 'ALSO MATCHES, control is blind' : 'does not match, control can fire'})`);
    if (!ok || wrongOk) failures++;
  }
  console.log('');

  // -- closed forms ---------------------------------------------------------
  console.log('Closed forms for P, fitted on three points and tested to n = 24');
  console.log('  (P = attacking pairs in distinct rows AND distinct columns)\n');
  const forms = {};
  for (const L of Object.keys(LEAPERS)) {
    const [a, b] = LEAPERS[L], V = leaperVectors(a, b);
    console.log(`--- ${L} (${a},${b}) ---`);
    for (const t of TOPOS) {
      const even = closedForm(t, V, 0, 6, 24), odd = closedForm(t, V, 1, 7, 25);
      forms[`${t}/${L}`] = { even, odd };
      const same = even.A === odd.A && even.B === odd.B && even.C === odd.C;
      if (same) console.log(`  ${t.padEnd(7)} P = ${fmtQuad(even)}   holds from n = ${Math.max(even.firstOk, odd.firstOk)}`);
      else console.log(`  ${t.padEnd(7)} P = ${fmtQuad(even)} (n even, from ${even.firstOk}) / ${fmtQuad(odd)} (n odd, from ${odd.firstOk})`);
      if (even.firstOk === null || odd.firstOk === null) { console.log(`     ^ FORM DOES NOT HOLD`); failures++; }
    }
    // The structural claim, checked rather than asserted: the linear coefficient
    // is 0, 0, -2(a+b), -4(a+b) as free boundaries go 0, 0, 1, 2.
    const want = { flat: -4 * (a + b), torus: 0, mobius: -2 * (a + b), klein: 0 };
    for (const t of TOPOS) {
      const got = forms[`${t}/${L}`].even.B;
      if (got !== want[t]) { console.log(`  BOUNDARY LAW FAILS: ${t} linear term ${got}, expected ${want[t]}`); failures++; }
    }
    // and the flat form should be exactly 4(n-a)(n-b)
    const f = forms[`flat/${L}`].even;
    if (f.A !== 4 || f.B !== -4 * (a + b) || f.C !== 4 * a * b) { console.log(`  FLAT FORM != 4(n-a)(n-b)`); failures++; }
  }
  console.log('\n  boundary law: linear coefficient of P is -4(a+b), -2(a+b), 0, 0');
  console.log('  for 2, 1, 0, 0 free boundaries (flat, mobius, klein, torus). CHECKED above.');
  console.log('  flat closed form is exactly 4(n-a)(n-b). CHECKED above.\n');

  // -- the residual, and the naive rule, scored on the OEIS out-of-sample set --
  const R = (topo, L, n, term) => {
    const [a, b] = LEAPERS[L];
    const p = forbiddenPairs(topo, n, leaperVectors(a, b));
    return Math.exp(logTerm(term) - logFact(n) + (n > 1 ? p / (n * (n - 1)) : 0));
  };
  console.log('The residual R(n) = a(n) / (n! exp(-P/(n(n-1)))), and the one-step rule');
  console.log('  RULE (no free parameters): predict a(n) from R(n-1). Scored below on the');
  console.log('  published FLAT rows for n = 15 upward, none of which this project computed.\n');
  const errs = [];
  for (const L of Object.keys(OEIS)) {
    const T = OEIS[L].terms;
    const line = [];
    for (let n = 15; n <= T.length; n++) {
      const rPrev = R('flat', L, n - 1, T[n - 2]);
      const [a, b] = LEAPERS[L];
      const p = forbiddenPairs('flat', n, leaperVectors(a, b));
      const predLog = logFact(n) - p / (n * (n - 1)) + Math.log(rPrev);
      const rel = Math.exp(predLog - logTerm(T[n - 1])) - 1;
      errs.push(Math.abs(rel));
      line.push(`n=${n} ${(rel * 100 >= 0 ? '+' : '')}${(rel * 100).toFixed(2)}%`);
    }
    console.log(`  ${OEIS[L].id} ${L.padEnd(8)} ${line.join('  ')}`);
  }
  errs.sort((x, y) => x - y);
  const med = errs[errs.length >> 1], max = errs[errs.length - 1];
  console.log(`\n  ${errs.length} out-of-sample published values: median |error| ${(med * 100).toFixed(3)}%, worst ${(max * 100).toFixed(3)}%`);
  if (!(med < 0.01)) { console.log('  RULE FAILED its own bar (median under 1%)'); failures++; }

  // -- the negative control: the same rule, unchanged, on the n-queens ---------
  console.log('\nNegative control: the identical rule on A000170 (n-queens, a SLIDER)');
  for (let n = 3; n <= 9; n++)
    if (queensPbrute(n) !== queensP(n)) { console.log(`  queens P formula wrong at n=${n}`); failures++; }
  console.log('  P = 2(2C(n,3)+C(n,2)) checked against brute force over n = 3..9');
  const qErrs = [], qRatio = [];
  const qR = n => Math.exp(logTerm(QUEENS[n]) - logFact(n) + queensP(n) / (n * (n - 1)));
  for (let n = 15; n <= 27; n++) {
    const predLog = logFact(n) - queensP(n) / (n * (n - 1)) + Math.log(qR(n - 1));
    qErrs.push(Math.abs(Math.exp(predLog - logTerm(QUEENS[n])) - 1));
    qRatio.push(qR(n) / qR(n - 1));
  }
  qErrs.sort((x, y) => x - y);
  const qMed = qErrs[qErrs.length >> 1];
  const meanRatio = qRatio.reduce((a, b) => a + b, 0) / qRatio.length;
  console.log(`  n = 15..27: median |error| ${(qMed * 100).toFixed(1)}%, worst ${(qErrs[qErrs.length - 1] * 100).toFixed(1)}%`);
  console.log(`  because the queens residual does not settle: R(n)/R(n-1) averages ${meanRatio.toFixed(3)},`);
  console.log(`  and 1/${meanRatio.toFixed(3)} - 1 = ${((1 / meanRatio - 1) * 100).toFixed(1)}% is exactly what the rule is wrong by.`);
  console.log(`  A slider's P ~ (2/3)n^3 so E grows without bound; a leaper's P = 4n^2 + O(n) so E -> 4.`);
  console.log(`  THE RULE IS FOR FIXED-JUMP PIECES. The control shows it could have failed here too.`);
  // the control must actually fail, or it is decoration
  if (!(qMed > 0.10)) { console.log('  CONTROL DID NOT FIRE: the rule was supposed to fail on sliders'); failures++; }
  if (!(meanRatio < 0.95)) { console.log('  CONTROL DID NOT FIRE: the queens residual was supposed to keep moving'); failures++; }

  // -- predictions for n = 15 on the three surfaces the OEIS does not carry ----
  if (wantPredict || wantScore) {
    console.log('\nPredictions for n = 15 (torus, mobius, klein), by the same one-step rule');
    console.log('  from the committed n = 14 terms. These surfaces have no published row.\n');
    const preds = {};
    for (const t of ['torus', 'mobius', 'klein']) {
      for (const L of Object.keys(LEAPERS)) {
        const prev = committed[`${t}/${L}`][13];
        const rPrev = R(t, L, 14, prev);
        const [a, b] = LEAPERS[L];
        const p = forbiddenPairs(t, 15, leaperVectors(a, b));
        const predLog = logFact(15) - p / (15 * 14) + Math.log(rPrev);
        preds[`${t}/${L}`] = Math.exp(predLog);
        console.log(`  ${t.padEnd(7)} ${L.padEnd(8)} R(14) = ${rPrev.toFixed(5)}   predicted a(15) = ${Math.round(preds[`${t}/${L}`]).toLocaleString('en-US')}`);
      }
    }
    if (wantScore) {
      const t15 = loadTerms('terms-1-15.tsv');
      if (!t15) { console.log('\n  terms-1-15.tsv not present yet: nothing to score.'); }
      else {
        console.log('\nScored against the exhaustive enumeration:\n');
        console.log('  surface leaper     predicted            actual        error');
        const rel = [];
        for (const t of ['torus', 'mobius', 'klein']) {
          for (const L of Object.keys(LEAPERS)) {
            const actual = t15[`${t}/${L}`][14];
            const e = preds[`${t}/${L}`] / Number(actual) - 1;
            rel.push(Math.abs(e));
            console.log(`  ${t.padEnd(7)} ${L.padEnd(8)} ${Math.round(preds[`${t}/${L}`]).toLocaleString('en-US').padStart(16)} ${Number(actual).toLocaleString('en-US').padStart(16)}   ${(e * 100 >= 0 ? '+' : '')}${(e * 100).toFixed(3)}%`);
          }
        }
        rel.sort((x, y) => x - y);
        console.log(`\n  12 pre-registered predictions: median |error| ${(rel[6] * 100).toFixed(3)}%, worst ${(rel[11] * 100).toFixed(3)}%`);
      }
    }
  }

  console.log(failures === 0 ? '\nPASS' : `\nFAIL (${failures})`);
  process.exit(failures === 0 ? 0 : 1);
}

// exact-ish log of a decimal integer string, so 24-digit OEIS terms do not lose
// their leading digits to a double before the ratio is taken
function logTerm(s) {
  const str = String(s);
  return Math.log(Number(str.slice(0, 15))) + (str.length - Math.min(15, str.length)) * Math.log(10);
}

main();
