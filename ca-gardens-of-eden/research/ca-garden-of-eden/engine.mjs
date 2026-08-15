// ca-garden-of-eden — engine. Never one path.
//
// An elementary cellular automaton (ECA) rule R in {0,...,255} is a local map
//   f(a,b,c) = bit (4a+2b+c) of R.
// On a RING of n cells (indices mod n) it induces a global map F_R : {0,1}^n -> {0,1}^n,
//   F_R(x)_i = f(x_{i-1}, x_i, x_{i+1}).
// A configuration y is a GARDEN OF EDEN (an orphan) iff it has NO predecessor:
// no x with F_R(x) = y. It can be *displayed* but the rule could never *produce* it.
//   GoE_R(n) = 2^n - |image(F_R on the ring of length n)|.
//
// This file computes image size and GoE two structurally independent ways:
//   (A) BRUTE FORCE  — enumerate all 2^n configs, apply F_R, count distinct outputs.
//                      Exact ground truth; feasible to n ~ 24.
//   (B) TRANSFER MATRIX over the de Bruijn transition MONOID — big-integer exact for
//       every n, and it must agree with (A) on the whole overlap.
//
// Method (B), derived from scratch:
//   Read a target y cyclically. A preimage x exists iff there is a cyclic walk on the
//   de Bruijn graph of *pair-states* s_i=(x_{i-1},x_i) consistent with y. Between pair
//   states s_i=(p,q) and s_{i+1}=(q,r) the emitted symbol is f(p,q,r). So for symbol b
//   define the 4x4 boolean matrix  M_b[(p,q)][(q,r)] = 1  iff  f(p,q,r)=b.
//   Then y in image  <=>  trace( M_{y_0} M_{y_1} ... M_{y_{n-1}} ) != 0  (boolean),
//   because a nonzero diagonal entry is exactly a closed (cyclic) walk. Boolean trace is
//   cyclic-invariant, so image membership does not depend on where the cycle is cut.
//   The boolean products M_{y_0}...M_{y_{n-1}} range over a FINITE monoid; tracking the
//   accumulated product as we read y gives a transfer over monoid elements, and
//     image_size(n) = sum over monoid elements P with trace(P)!=0 of
//                     #{ y of length n : product(y) = P }.
//   That count vector is (transfer)^n applied to the identity, exact in BigInt.

'use strict';

// ----- the local rule --------------------------------------------------------
export function localMap(rule) {
  // f(a,b,c) with a,b,c in {0,1}
  return (a, b, c) => (rule >> ((a << 2) | (b << 1) | c)) & 1;
}

// One global step on a ring of length n; config x is a JS integer bitmask (bit i = cell i).
// n <= 30 keeps 2^n within safe-integer bitmask range.
export function step(rule, n, x) {
  const f = localMap(rule);
  let y = 0;
  for (let i = 0; i < n; i++) {
    const a = (x >>> ((i - 1 + n) % n)) & 1;
    const b = (x >>> i) & 1;
    const c = (x >>> ((i + 1) % n)) & 1;
    if (f(a, b, c)) y |= (1 << i);
  }
  return y >>> 0;
}

// ----- (A) brute force -------------------------------------------------------
// Returns { image, goe } as regular numbers. n must satisfy 2^n <= ~2^26 for RAM/time.
export function bruteImageGoE(rule, n) {
  if (n < 1) throw new Error('n>=1');
  const total = 2 ** n;
  const f = localMap(rule);
  const seen = new Uint8Array(total);
  for (let x = 0; x < total; x++) {
    let y = 0;
    for (let i = 0; i < n; i++) {
      const a = (x >>> ((i - 1 + n) % n)) & 1;
      const b = (x >>> i) & 1;
      const c = (x >>> ((i + 1) % n)) & 1;
      if (f(a, b, c)) y |= (1 << i);
    }
    seen[y] = 1;
  }
  let image = 0;
  for (let y = 0; y < total; y++) image += seen[y];
  return { image, goe: total - image };
}

// Does a given ring config y (bitmask, length n) have a predecessor under rule R?
// Independent of the transfer machinery: subset-construction over pair-states.
// Returns { orphan:boolean, predecessor:int|null } — a witness when one exists.
export function findPredecessor(rule, n, y) {
  const f = localMap(rule);
  // Small rings (n<=2) are wrap-degenerate (a cell neighbours itself / its only partner);
  // test the <=4 candidates by the local rule directly.
  if (n <= 2) {
    for (let x = 0; x < (1 << n); x++) if (step(rule, n, x) === (y >>> 0)) return { orphan: false, predecessor: x >>> 0 };
    return { orphan: true, predecessor: null };
  }
  // We pick x_0=p and x_1=q to fix the first pair, then walk r=x_2,...; the ring
  // constrains the last two cells to equal the first two. Just brute the two seeds.
  for (let x0 = 0; x0 < 2; x0++) {
    for (let x1 = 0; x1 < 2; x1++) {
      // x[0]=x0, x[1]=x1; determine x[2..n-1] greedily where forced, else branch.
      // Constraint at cell i: y_i = f(x_{i-1}, x_i, x_{i+1}) fixes x_{i+1} given x_{i-1},x_i
      // ONLY if exactly one r works; branch when both work.
      const stack = [[2, x0, x1, (x0) | (x1 << 1)]]; // pos, x[i-2]?, ... track last two + partial
      // simpler: DFS filling x[2..n-1], last two cells tracked; verify wrap at the end.
      const dfs = (pos, prev, cur, bits) => {
        if (pos === n) {
          // wrap constraints: cell n-1 uses x_{n-2},x_{n-1},x_0 ; cell 0 uses x_{n-1},x_0,x_1
          const xn1 = cur, xn2 = prev;
          if (f(xn2, xn1, x0) !== ((y >>> (n - 1)) & 1)) return null;
          if (f(xn1, x0, x1) !== (y & 1)) return null;
          return bits;
        }
        // cell (pos-1): y_{pos-1} = f(x_{pos-2}, x_{pos-1}, x_pos) = f(prev, cur, r)
        const want = (y >>> (pos - 1)) & 1;
        for (let r = 0; r < 2; r++) {
          if (f(prev, cur, r) === want) {
            const res = dfs(pos + 1, cur, r, bits | (r << pos));
            if (res !== null) return res;
          }
        }
        return null;
      };
      void stack;
      const bits0 = x0 | (x1 << 1);
      const res = dfs(2, x0, x1, bits0);
      if (res !== null) return { orphan: false, predecessor: res >>> 0 };
    }
  }
  return { orphan: true, predecessor: null };
}

// ----- (B) transfer matrix over the de Bruijn transition monoid --------------
// Boolean 4x4 matrix packed as a 16-bit integer: bit (4*i+j) = entry [i][j].
// Pair-state index for (p,q) is (p<<1)|q, i in {0,1,2,3}.

function buildSymbolMatrices(rule) {
  const f = localMap(rule);
  const M = [0, 0]; // M[b] packed
  for (let p = 0; p < 2; p++)
    for (let q = 0; q < 2; q++)
      for (let r = 0; r < 2; r++) {
        const b = f(p, q, r);
        const i = (p << 1) | q;     // from state (p,q)
        const j = (q << 1) | r;     // to state (q,r)
        M[b] |= (1 << (4 * i + j));
      }
  return M; // [M0, M1]
}

function boolMul(A, B) {
  // (A·B)[i][j] = OR_k A[i][k] & B[k][j]
  let out = 0;
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      let bit = 0;
      for (let k = 0; k < 4; k++) {
        if (((A >> (4 * i + k)) & 1) && ((B >> (4 * k + j)) & 1)) { bit = 1; break; }
      }
      if (bit) out |= (1 << (4 * i + j));
    }
  }
  return out;
}

function boolTrace(A) {
  for (let i = 0; i < 4; i++) if ((A >> (4 * i + i)) & 1) return 1;
  return 0;
}

const IDENTITY4 = (() => { let m = 0; for (let i = 0; i < 4; i++) m |= (1 << (4 * i + i)); return m; })();

// Build the reachable right-multiplication monoid from identity, plus the transfer.
// Returns { states:[packedMatrix], idx:Map, trans:[[to0,to1]], traceNonZero:[bool] }.
export function buildMonoid(rule) {
  const [M0, M1] = buildSymbolMatrices(rule);
  const idx = new Map();
  const states = [];
  const add = (m) => { if (!idx.has(m)) { idx.set(m, states.length); states.push(m); } return idx.get(m); };
  add(IDENTITY4);
  const trans = [];
  for (let s = 0; s < states.length; s++) {
    const m = states[s];
    const t0 = add(boolMul(m, M0));
    const t1 = add(boolMul(m, M1));
    trans[s] = [t0, t1];
  }
  const traceNonZero = states.map(m => boolTrace(m) === 1);
  return { states, idx, trans, traceNonZero, M0, M1 };
}

// image_size(n) as BigInt, for n>=1, via (transfer)^n on the identity-start distribution.
// Returns an array imageSizes[1..maxN] (index 0 unused / set to 1n for the empty string convention off).
export function imageSizes(rule, maxN) {
  const mon = buildMonoid(rule);
  const S = mon.states.length;
  // distribution over monoid states after reading k symbols, starting at identity (state 0).
  let dist = new Array(S).fill(0n);
  const startIdx = mon.idx.get(IDENTITY4);
  dist[startIdx] = 1n;
  const out = new Array(maxN + 1).fill(0n);
  for (let k = 1; k <= maxN; k++) {
    const next = new Array(S).fill(0n);
    for (let s = 0; s < S; s++) {
      const c = dist[s];
      if (c === 0n) continue;
      const [t0, t1] = mon.trans[s];
      next[t0] += c;
      next[t1] += c;
    }
    dist = next;
    let img = 0n;
    for (let s = 0; s < S; s++) if (mon.traceNonZero[s]) img += dist[s];
    out[k] = img;
  }
  return out; // BigInt image sizes, out[n]
}

export function goeSizes(rule, maxN) {
  const img = imageSizes(rule, maxN);
  const out = new Array(maxN + 1).fill(0n);
  for (let n = 1; n <= maxN; n++) out[n] = (1n << BigInt(n)) - img[n];
  return out;
}

// Convenience: is rule R surjective on all rings? (GoE(n)=0 for all n) — true iff the
// monoid transfer never loses mass, i.e. image_size(n)==2^n for the tested range.
export function goeVector(rule, maxN) {
  const g = goeSizes(rule, maxN);
  return g.slice(1).map(v => v.toString());
}
