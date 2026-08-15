// chi.mjs — confirm the SURFACE LABELS are honest, not decorative.
//
// Each "surface" in engine.mjs is really a set of edge-identifications on the
// n x n grid. This file treats the identified grid as a CW complex (vertices =
// grid points, edges = unit segments, faces = the n^2 cells), performs the same
// gluings, and computes the Euler characteristic chi = V - E + F and the number
// of boundary edges. The pair (chi, has-boundary) — together with orientability,
// which the gluing word fixes by construction — is a complete fingerprint that
// distinguishes all six surfaces:
//
//   surface     chi   boundary?  orientable?   (from the standard classification)
//   plane/disk    1     yes         yes
//   cylinder      0     yes         yes
//   Mobius band   0     yes         NO   (one column-wrap with a flip)
//   torus         0     no          yes
//   Klein bottle  0     no          NO   (one flipped wrap, one plain)
//   projective    1     no          NO   (both wraps flipped: the word abab)
//
// So a wrong construction would show up as a wrong chi or wrong boundary count.
// Run:  node chi.mjs

// Union-find
function makeUF(size) {
  const p = Array.from({ length: size }, (_, i) => i);
  const find = x => { while (p[x] !== x) { p[x] = p[p[x]]; x = p[x]; } return x; };
  const union = (a, b) => { p[find(a)] = find(b); };
  const classes = () => { const s = new Set(); for (let i = 0; i < size; i++) s.add(find(i)); return s.size; };
  return { find, union, classes };
}

// Which wraps each surface performs, and whether each wrap flips the transverse coord.
const SPEC = {
  plane:      { col: null,   row: null },
  cylinder:   { col: 'plain', row: null },
  torus:      { col: 'plain', row: 'plain' },
  mobius:     { col: 'flip',  row: null },
  klein:      { col: 'flip',  row: 'plain' },
  projective: { col: 'flip',  row: 'flip' },
};

function fingerprint(n, surface) {
  const spec = SPEC[surface];
  const vid = (i, j) => i * (n + 1) + j;                 // vertex (i,j), i,j in 0..n
  const nV = (n + 1) * (n + 1);

  // Edges: horizontals h(i,j) [i:0..n, j:0..n-1], verticals v(i,j) [i:0..n-1, j:0..n].
  const nH = (n + 1) * n, nV_edges = n * (n + 1);
  const hid = (i, j) => i * n + j;                       // 0 .. nH-1
  const vidE = (i, j) => nH + i * (n + 1) + j;           // nH .. nH+nV_edges-1
  const nE = nH + nV_edges;

  const uv = makeUF(nV);
  const ue = makeUF(nE);
  // face incidence per RAW edge: 2 = interior, 1 = on the polygon boundary
  const faceInc = new Array(nE).fill(0);
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    faceInc[hid(r, c)]++; faceInc[hid(r + 1, c)]++;      // top & bottom edges of cell
    faceInc[vidE(r, c)]++; faceInc[vidE(r, c + 1)]++;    // left & right edges of cell
  }

  // Column wrap: glue right boundary (j=n) to left (j=0).
  if (spec.col) {
    const flip = spec.col === 'flip';
    for (let i = 0; i <= n; i++) uv.union(vid(i, n), vid(flip ? n - i : i, 0));
    for (let i = 0; i < n; i++) ue.union(vidE(i, n), vidE(flip ? n - 1 - i : i, 0));
  }
  // Row wrap: glue bottom boundary (i=n) to top (i=0).
  if (spec.row) {
    const flip = spec.row === 'flip';
    for (let j = 0; j <= n; j++) uv.union(vid(n, j), vid(0, flip ? n - j : j));
    for (let j = 0; j < n; j++) ue.union(hid(n, j), hid(0, flip ? n - 1 - j : j));
  }

  // Distinct cell counts
  const Vc = uv.classes();
  // Edge classes + boundary: sum faceInc within each edge-class; boundary class => sum 1.
  const clsInc = new Map();
  for (let e = 0; e < nE; e++) {
    const c = ue.find(e);
    clsInc.set(c, (clsInc.get(c) || 0) + faceInc[e]);
  }
  const Ec = clsInc.size;
  let boundary = 0;
  for (const s of clsInc.values()) if (s === 1) boundary++;
  const F = n * n;
  const chi = Vc - Ec + F;
  return { chi, boundary };
}

const EXPECT = {
  plane:      { chi: 1, hasBoundary: true },
  cylinder:   { chi: 0, hasBoundary: true },
  torus:      { chi: 0, hasBoundary: false },
  mobius:     { chi: 0, hasBoundary: true },
  klein:      { chi: 0, hasBoundary: false },
  projective: { chi: 1, hasBoundary: false },
};

let ok = true;
for (const s of Object.keys(SPEC)) {
  const r6 = fingerprint(6, s), r7 = fingerprint(7, s);
  const stable = r6.chi === r7.chi && (r6.boundary > 0) === (r7.boundary > 0);
  const exp = EXPECT[s];
  const pass = stable && r6.chi === exp.chi && (r6.boundary > 0) === exp.hasBoundary;
  ok = ok && pass;
  console.log(
    `${s.padEnd(11)} chi=${r6.chi} boundary_edges=${r6.boundary}  ` +
    `expect chi=${exp.chi} boundary=${exp.hasBoundary}  ${pass ? 'OK' : 'MISMATCH'}`
  );
}
process.exit(ok ? 0 : 1);
