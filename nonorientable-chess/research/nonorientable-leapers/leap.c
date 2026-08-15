/* Independent C backtracker for non-attacking (a,b)-leaper placements, one piece
 * per row and per column, on flat / torus / mobius / klein boards. A from-scratch
 * second code path for research/nonorientable-leapers/engine.mjs: it re-implements
 * the universal-cover fold in C and enumerates by a small per-cell adjacency list
 * (a leaper has <=8 targets), so it reaches larger n than the Node BigInt version.
 *
 *   gcc -O3 -o leap leap.c
 *   ./leap <topo> <a> <b> <n>      topo in {flat,torus,mobius,klein}
 *   ./leap mobius 1 2 13           # Mobius knight, n=13
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static int n;

/* Fold plane target (R,C) to a board cell; return cell index r*n+c, or -1 if off
 * a free boundary. Mirrors foldCell() in engine.mjs exactly. */
static int fold(int topo, int R, int C) {
  int r, c, k, C2;
  if (topo == 0) {                 /* flat */
    if (R < 0 || R >= n || C < 0 || C >= n) return -1;
    return R * n + C;
  }
  if (topo == 1) {                 /* torus */
    r = ((R % n) + n) % n; c = ((C % n) + n) % n; return r * n + c;
  }
  if (topo == 2) {                 /* mobius: rows free, columns glued with flip */
    if (R < 0 || R >= n) return -1;
    k = (int)floor((double)C / n);          /* signed seam crossings */
    c = C - k * n;
    r = (((k % 2) + 2) % 2) ? (n - 1 - R) : R;
    return r * n + c;
  }
  /* klein: rows glued with column-flip, columns straight */
  k = (int)floor((double)R / n);
  r = R - k * n;
  C2 = (((k % 2) + 2) % 2) ? (n - 1 - C) : C;
  { int kC = (int)floor((double)C2 / n); c = C2 - kC * n; }
  return r * n + c;
}

static int adjN[400][8];   /* neighbours of each cell (n<=20 -> 400 cells) */
static int adjCnt[400];
static int col[64];        /* col[row] = chosen column */
static unsigned char used[64];
static long long total;

static void place(int row) {
  if (row == n) { total++; return; }
  for (int c = 0; c < n; c++) {
    if (used[c]) continue;
    int cell = row * n + c, ok = 1;
    for (int t = 0; t < adjCnt[cell]; t++) {
      int w = adjN[cell][t], nr = w / n, nc = w % n;
      if (nr < row && col[nr] == nc) { ok = 0; break; }
    }
    if (!ok) continue;
    used[c] = 1; col[row] = c; place(row + 1); used[c] = 0;
  }
}

int main(int argc, char **argv) {
  if (argc < 5) { fprintf(stderr, "usage: %s <flat|torus|mobius|klein> a b n\n", argv[0]); return 1; }
  int topo = !strcmp(argv[1],"flat")?0 : !strcmp(argv[1],"torus")?1 : !strcmp(argv[1],"mobius")?2 : 3;
  int a = atoi(argv[2]), b = atoi(argv[3]); n = atoi(argv[4]);
  int vec[8][2] = {{a,b},{a,-b},{-a,b},{-a,-b},{b,a},{b,-a},{-b,a},{-b,-a}};
  for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) {
    int cell = i * n + j; adjCnt[cell] = 0;
    for (int v = 0; v < 8; v++) {
      int w = fold(topo, i + vec[v][0], j + vec[v][1]);
      if (w < 0 || w == cell) continue;
      int dup = 0; for (int t = 0; t < adjCnt[cell]; t++) if (adjN[cell][t] == w) dup = 1;
      if (!dup && adjCnt[cell] < 8) adjN[cell][adjCnt[cell]++] = w;
    }
  }
  memset(used, 0, sizeof used); total = 0;
  place(0);
  printf("%lld\n", total);
  return 0;
}
