/* leap2.c — a genuinely independent enumerator for non-attacking (a,b)-leaper
 * placements, one piece per row and per column, on flat / torus / mobius / klein
 * boards.  It exists because the committed cross-check in this directory did not
 * cover the terms the page actually prints.
 *
 * WHAT WAS WRONG, AND WHAT THIS FIXES
 * -----------------------------------
 * The README and the published page both said the table was carried by three
 * independent code paths.  In the repository, `agree.mjs` compared exactly two of
 * them and only over n = 1..8, and NOTHING re-ran `leap.c` at all: its agreement
 * "to n = 13" was an uncommitted historical claim.  So the largest and most
 * fragile terms — the ones no other check could reach — rested on one code path.
 * This file is a second path built to disagree if the first one is wrong, and
 * `agree.mjs` now runs both over the whole published range.
 *
 * HOW IT IS INDEPENDENT OF leap.c AND engine.mjs
 * ----------------------------------------------
 * Two places can hide a bug here: the geometry (which cells attack which) and the
 * search (how placements are counted).  Both are done differently.
 *
 *   GEOMETRY.  engine.mjs and leap.c fold a plane target back to the board with
 *   closed-form floor/modulo arithmetic.  This file never divides.  It applies the
 *   surface's deck-group generators one at a time, in a loop, until the point lands
 *   in the fundamental domain — the definition rather than its algebraic shortcut.
 *   A sign slip or an off-by-one in a floor() is exactly the kind of error the two
 *   forms fail differently on.
 *
 *   SEARCH.  leap.c walks rows in the fixed order 0,1,2,... and, for each candidate
 *   column, loops over that cell's <=8 neighbours asking whether any is already
 *   occupied.  This file precomputes, for every (row,col) and every other row, a
 *   bitmask of the columns that placement forbids there; it then propagates those
 *   masks forward and always fills the *most constrained remaining row* next.  The
 *   row order is dynamic and data-dependent, so the two searches visit the tree in
 *   genuinely different orders.  (Every solution is still counted exactly once: at
 *   each node the row to fill is chosen deterministically from the partial state,
 *   so a completed placement is reached by exactly one path.)
 *
 * It is also much faster, which is the point of building it now: the forward
 * masks kill branches leap.c only discovers at the leaf, and the most-constrained
 * rule finds the empty row early.  That is what puts n = 14 and n = 15 in reach.
 *
 *   gcc -O3 -o leap2 leap2.c
 *   ./leap2 <topo> <a> <b> <n>      topo in {flat,torus,mobius,klein}
 *   ./leap2 mobius 1 2 14
 *
 * Prints the count.  With -v it also prints node counts to stderr.
 *
 * THE TORUS SHORTCUT (-t0), and why it is sound only there
 * --------------------------------------------------------
 * On the torus, shifting every column by a constant s is a symmetry: it commutes
 * with both gluings, permutes rows among themselves and columns among themselves,
 * and so carries one-per-row-and-column placements to the same.  The Z_n action is
 * FREE, because a nonzero shift moves the piece in row 0, so no placement is fixed.
 * Every orbit therefore has exactly n members and
 *
 *     count = n * #{ placements whose row-0 piece sits in column 0 }.
 *
 * -t0 computes the right-hand side and multiplies, an n-fold saving that is what
 * puts the torus row at n=15 within reach.  It is REFUSED on the other three
 * surfaces: the half-twist does not commute with a column shift (a piece carried
 * across the seam has its row reflected, so two pieces can land in one row), and
 * the committed table confirms the difference -- the Mobius and Klein counts are
 * not divisible by n, while every torus count is.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXN 20

enum { FLAT = 0, TORUS = 1, MOBIUS = 2, KLEIN = 3 };

static int n;
static int topo;

/* ------------------------------------------------------------------ geometry */

/* Fold a plane point (R,C) to its representative in {0..n-1}^2 by applying deck
 * generators one at a time.  Returns 1 and writes *rr,*cc, or 0 if the point
 * leaves a free boundary (the Mobius band's rows).
 *
 * The deck groups, as stated in engine.mjs:
 *   torus  : <(R,C)->(R,C+n), (R,C)->(R+n,C)>                    both straight
 *   mobius : <g:(R,C)->((n-1)-R, C+n)>, rows a free boundary       glide only
 *   klein  : <t_C:(R,C)->(R,C+n),  t_R:(R,C)->(R+n,(n-1)-C)>     column-flip
 *
 * No division, no modulo, no floor: each loop applies one generator per turn.
 * Bounded because every application moves C (or R) by exactly n toward the domain.
 */
static int foldPoint(int R, int C, int *rr, int *cc) {
  if (topo == FLAT) {
    if (R < 0 || R >= n || C < 0 || C >= n) return 0;
    *rr = R; *cc = C; return 1;
  }
  if (topo == TORUS) {
    while (C < 0) C += n;
    while (C >= n) C -= n;
    while (R < 0) R += n;
    while (R >= n) R -= n;
    *rr = R; *cc = C; return 1;
  }
  if (topo == MOBIUS) {
    /* Rows never wrap: a target off the top or bottom has left the band. */
    if (R < 0 || R >= n) return 0;
    /* g:(R,C)->(n-1-R, C+n) and its inverse (R,C)->(n-1-R, C-n).  Each crossing
     * of the column seam reflects the row; apply one crossing per iteration. */
    while (C >= n) { C -= n; R = n - 1 - R; }
    while (C < 0)  { C += n; R = n - 1 - R; }
    *rr = R; *cc = C; return 1;
  }
  /* KLEIN.  Rows wrap with a column flip; columns wrap straight. */
  while (R >= n) { R -= n; C = n - 1 - C; }
  while (R < 0)  { R += n; C = n - 1 - C; }
  while (C >= n) C -= n;
  while (C < 0)  C += n;
  *rr = R; *cc = C; return 1;
}

/* The <=8 leaper vectors for an (a,b)-leaper: (+-a,+-b) and (+-b,+-a). */
static int vec[8][2], nvec;
static void buildVectors(int a, int b) {
  int cand[8][2], m = 0, i, j;
  int pq[2][2] = {{a, b}, {b, a}};
  for (i = 0; i < 2; i++)
    for (j = 0; j < 4; j++) {
      int sr = (j & 1) ? -1 : 1, sc = (j & 2) ? -1 : 1;
      cand[m][0] = sr * pq[i][0];
      cand[m][1] = sc * pq[i][1];
      m++;
    }
  nvec = 0;
  for (i = 0; i < m; i++) {
    int dup = 0;
    for (j = 0; j < nvec; j++)
      if (vec[j][0] == cand[i][0] && vec[j][1] == cand[i][1]) { dup = 1; break; }
    if (!dup) { vec[nvec][0] = cand[i][0]; vec[nvec][1] = cand[i][1]; nvec++; }
  }
}

/* forb[r][c][r2] = bitmask of columns in row r2 that a piece at (r,c) attacks.
 * Symmetrised, exactly as engine.mjs's attackGraph does. */
static unsigned int forb[MAXN][MAXN][MAXN];

static void buildForb(void) {
  int r, c, k, r2, c2;
  memset(forb, 0, sizeof forb);
  for (r = 0; r < n; r++)
    for (c = 0; c < n; c++)
      for (k = 0; k < nvec; k++) {
        if (!foldPoint(r + vec[k][0], c + vec[k][1], &r2, &c2)) continue;
        if (r2 == r && c2 == c) continue;          /* a cell never attacks itself */
        forb[r][c][r2] |= 1u << c2;
        forb[r2][c2][r] |= 1u << c;                /* symmetrise */
      }
}

/* -------------------------------------------------------------------- search */

static unsigned int full;
static long long total;
static long long nodes;

/* live[r] = columns still legal for row r given everything placed so far.
 * Rows already filled are marked in `done`. */
static void rec(unsigned int done, unsigned int usedCols, unsigned int live[MAXN], int depth) {
  int r, best = -1, bestCount = 99;
  unsigned int avail, saved[MAXN];
  nodes++;
  if (depth == n) { total++; return; }

  /* Most constrained remaining row.  A row with zero options ends the branch here
   * rather than n levels down, which is where the speed comes from. */
  for (r = 0; r < n; r++) {
    if (done & (1u << r)) continue;
    avail = live[r] & ~usedCols;
    if (!avail) return;
    {
      int cnt = __builtin_popcount(avail);
      if (cnt < bestCount) { bestCount = cnt; best = r; if (cnt == 1) break; }
    }
  }

  r = best;
  avail = live[r] & ~usedCols;
  while (avail) {
    unsigned int bit = avail & (~avail + 1u);
    int c = __builtin_ctz(bit);
    int q;
    avail ^= bit;
    memcpy(saved, live, sizeof(unsigned int) * n);
    for (q = 0; q < n; q++) live[q] &= ~forb[r][c][q];
    rec(done | (1u << r), usedCols | bit, live, depth + 1);
    memcpy(live, saved, sizeof(unsigned int) * n);
  }
}

int main(int argc, char **argv) {
  int a, b, i, verbose = 0, shortcut = 0;
  unsigned int live[MAXN];
  if (argc < 5) {
    fprintf(stderr, "usage: %s <flat|torus|mobius|klein> <a> <b> <n> [-v] [-t0]\n", argv[0]);
    return 2;
  }
  if      (!strcmp(argv[1], "flat"))   topo = FLAT;
  else if (!strcmp(argv[1], "torus"))  topo = TORUS;
  else if (!strcmp(argv[1], "mobius")) topo = MOBIUS;
  else if (!strcmp(argv[1], "klein"))  topo = KLEIN;
  else { fprintf(stderr, "unknown topology %s\n", argv[1]); return 2; }
  a = atoi(argv[2]); b = atoi(argv[3]); n = atoi(argv[4]);
  for (i = 5; i < argc; i++) {
    if (!strcmp(argv[i], "-v")) verbose = 1;
    else if (!strcmp(argv[i], "-t0")) shortcut = 1;
  }
  if (n < 1 || n > MAXN) { fprintf(stderr, "n out of range\n"); return 2; }
  if (shortcut && topo != TORUS) {
    fprintf(stderr, "-t0 is sound only on the torus (see the header); refusing\n");
    return 2;
  }

  buildVectors(a, b);
  buildForb();

  full = (n == 32) ? 0xffffffffu : ((1u << n) - 1u);
  for (i = 0; i < n; i++) live[i] = full;
  total = 0; nodes = 0;

  if (shortcut) {
    /* Seat row 0 in column 0, count, then multiply by the orbit size n. */
    int q;
    for (q = 0; q < n; q++) live[q] &= ~forb[0][0][q];
    rec(1u, 1u, live, 1);
    total *= n;
  } else {
    rec(0u, 0u, live, 0);
  }

  printf("%lld\n", total);
  if (verbose) fprintf(stderr, "nodes %lld\n", nodes);
  return 0;
}
