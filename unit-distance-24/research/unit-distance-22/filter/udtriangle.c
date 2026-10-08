/* udtriangle: the triangle-orientation case-tree prover of research/unit-distance-23/RHOMBUS-SPEC.md, Section 4.
 *
 * I/O (spec Section 3 contract, witness key "tri").  Reads graph6 lines on stdin, one graph per line, at most 24
 * vertices, no header.  Writes exactly one JSON line per input line to stdout, in input order:
 *     {"verdict":"pass"}
 *     {"verdict":"refuted","witness":{"tri":{"tree":NODE}}}
 *     {"verdict":"tu","witness":{"tri":{"tree":NODE}}}
 * NODE is Section 4's case tree.  One statistics line goes to stderr at the end.  An input line that is not a graph6
 * string of order <= 24 is an error: a message on stderr and exit status 2 (nothing is guessed).  The output is a
 * deterministic function of the input bytes.
 *
 *     udtriangle [-b N | --budget N] [--no-mirror] < graphs.g6 > verdicts.jsonl
 *
 *   -b, --budget N   node budget per graph (default 4096, at most 100000, Section 4 rule 1's cap).  A graph whose
 *                    case tree would need more nodes (splits plus leaves) passes, counted as "budget".
 *   --no-mirror      build the minus subtree of the root split by search instead of as the mirror image of the plus
 *                    subtree.  The output is identical either way (a test aid; see "Mirror" below).
 *
 * The rows.  Positions are complex numbers f(0..n-1).  Every 4-cycle [u,v,w,x] gives the rhombus row
 * r = e_u - e_v + e_w - e_x (Lemma R).  A triangle T = (a,b,c), a < b < c, split with sign s gives
 * t(T,s) = e_c - e_a - w^s (e_b - e_a) (Lemma T), w = e^(i pi/3), w^2 = w - 1.
 *
 * The search.  Depth first over triangle splits.  A node CLOSES when its rows (all rhombus rows plus the triangle rows
 * of its path) force a collision, e_a - e_b in their span (the lexicographically first pair a < b), or else a unit
 * distance on a non-edge, e_a - e_b - w^k (e_p - e_q) in their span with ab a non-edge and pq an edge (the
 * lexicographically first non-edge a < b, then the first edge p < q, then the smallest k; the first ordered edge
 * that forces a pair is always one with p < q, since (q,p) with k is (p,q) with k + 3).  Otherwise the node splits
 * a triangle whose orientation its rows do not already decide (neither t(T,+) nor t(T,-) in the span), preferring
 * the first such triangle that shares an edge with a triangle split on the path (one of its children then closes at
 * once: same-side third vertices collide), else the first such triangle.  A node that cannot close and has nothing
 * left to split is OPEN: the graph passes.  Every split adds an independent row, so depth <= n - 1.
 *
 * Exact arithmetic.  The linear algebra runs mod p = 2^61 - 1 with w -> W, a root of x^2 - x + 1 (p = 1 mod 3).
 * For n <= 24 this decides membership in the span exactly, not probabilistically: each row has Euclidean norm at
 * most 2 as a complex vector and each target at most sqrt(6), so every minor involved has modulus at most
 * 2^23 * sqrt(6) < 2^24.3; a nonzero element of the kernel ideal of Z[w] -> F_p has norm (squared modulus) at
 * least p > 2^60; so a minor vanishes mod p only if it vanishes in Z[w], and every rank is the rank over Q(w).
 * The state of a node is the row-reduced null space of its basis rows (one vector per free column) plus the dual
 * vectors of the basis rows and the determinant of the basis on its pivot columns (the product of the pivots).  At a
 * leaf with target v, the coefficient of basis row i is c_i = <v, dual_i>; by Cramer, det * c_i is a minor of the
 * basis with one row replaced by v, an element of Z[w] of modulus < 2^24.3, and so is det.  Each is recovered from
 * its residue as the unique element of Z[w] of norm < 2^58 in its class (Babai rounding in a reduced basis of the
 * kernel lattice, which has minimum norm >= p).  The leaf lists only the rows with c_i != 0, and the integer content
 * of (scale, coefficients) is divided out.
 *
 * Mirror.  Complex conjugation maps an embedding to an embedding, t(T,s) to t(T,-s), fixes the rhombus rows and
 * sends w^k to w^(-k).  So the minus subtree of the root split is the plus subtree with plus and minus exchanged at
 * every split and every leaf conjugated (coefficients x + y w -> (x + y) - y w, zeta k -> -k mod 6).  This is only
 * how the prover BUILDS that half: the tree still branches explicitly, every leaf carries its own certificate, and
 * the whole tree is verified below exactly like a searched one.  (The search makes the same choices on the mirror
 * image, so the bytes equal those of --no-mirror; the test suite checks that.)
 *
 * The "cycles" list of a leaf is empty when the leaf needs no rhombus row.  Section 4 rule 2 reads "its cycles are
 * 4-cycles of G as in Section 2 rule 2", and Section 2 rule 2 also says "non-empty"; this prover reads the reference
 * as the per-entry condition only.  No such leaf has been seen (two triangles on an edge always span a 4-cycle, whose
 * rhombus row already decides the second one's orientation); the stderr line counts them as leaves_without_cycles.
 *
 * Self-verification.  Every tree is serialised, the bytes are parsed back by a strict parser into a fresh structure,
 * and that structure is checked against Section 4 rules 1 to 5 in exact Z[w] arithmetic (__int128 accumulators,
 * every coefficient |.| < 2^62).  Only then is the line written; on any failure the graph passes and the failure is
 * counted on stderr ("verify_fail").  A certificate that cannot be built (a lift without a short representative,
 * which the bounds above exclude) passes as "lift_fail".  Nothing here removes a graph without a certificate that
 * has already been checked.
 *
 * Red-control mutants (tests only; never build them for production):
 *   -DMUT_ROTATION     triangle rows use w^(2s) in place of w^s, in the search AND in the self-verifier;
 *   -DMUT_EDGE_CLOSE   a node may close on a forced unit distance on an EDGE ab (pq != ab), in the search AND in
 *                      the self-verifier's rule 3;
 *   -DMUT_SEARCH_ONLY  with either of the above, mutate the search only: the self-verifier stays true to the spec
 *                      and must catch every mutant certificate (they then pass, counted as verify_fail).
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

__extension__ typedef __int128 i128;
__extension__ typedef unsigned __int128 u128;
typedef uint64_t u64;
typedef int64_t i64;
typedef uint32_t u32;

#define MAXN 24                 /* the u(23) programme's host limit (udfilter.h UDF_MAX_VERTICES) */
#define MAXE (MAXN * (MAXN - 1) / 2)
#define MAXTRI 2048             /* C(24,3) = 2024 */
#define MAXCYC 65536            /* <= C(24,2) * C(22,2) = 63756 four-cycles */
#define DEFAULT_BUDGET 4096
#define SPEC_MAX_NODES 100000   /* Section 4 rule 1 */
#define SPEC_MAX_DEPTH 64       /* Section 4 rule 1 */
#define COEF_BOUND ((i64)1 << 62)   /* Section 4 rule 2: |x| < 2^62 */

/* ------------------------------------------------------------------------------------------------------------ */
/* Arithmetic mod p = 2^61 - 1.                                                                                   */

#define PM ((UINT64_C(1) << 61) - 1)

static inline u64 madd(u64 a, u64 b) { u64 s = a + b; return s >= PM ? s - PM : s; }
static inline u64 msub(u64 a, u64 b) { return a >= b ? a - b : a + (PM - b); }
static inline u64 mmul(u64 a, u64 b) {
    u128 z = (u128)a * b;
    u64 s = ((u64)z & PM) + (u64)(z >> 61);
    return s >= PM ? s - PM : s;
}
static u64 mpow(u64 a, u64 e) {
    u64 r = 1;
    while (e) { if (e & 1) r = mmul(r, a); a = mmul(a, a); e >>= 1; }
    return r;
}
static u64 minv(u64 a) { return mpow(a, PM - 2); }
static u64 imod(i64 x) { i64 r = x % (i64)PM; if (r < 0) r += (i64)PM; return (u64)r; }

static u64 WM;          /* W: a root of x^2 - x + 1 mod p */
static u64 WMK[6];      /* W^k */

/* ------------------------------------------------------------------------------------------------------------ */
/* Z[w], w^2 = w - 1.  Elements are pairs (x, y) meaning x + y w.                                                */

typedef struct { i64 x, y; } zw;
static const zw WK[6] = {{1, 0}, {0, 1}, {-1, 1}, {-1, 0}, {0, -1}, {1, -1}};   /* w^k, k = 0..5 */

static u64 zw_mod(zw a) { return madd(imod(a.x), mmul(imod(a.y), WM)); }

/* The coefficients of t(T, s) at a, b, c: t = e_c - e_a - rho (e_b - e_a) with rho = w^s, so a gets rho - 1,
   b gets -rho and c gets 1. */
/* Build tag printed in the stats line as mutant=N: 0 for the production build, nonzero for a red-control build
   (bit 1 MUT_ROTATION, bit 2 MUT_EDGE_CLOSE, bit 4 MUT_SEARCH_ONLY), so enum/prune.py can refuse a mutant. */
#define BUILD_MUTANT_ROT 0
#define BUILD_MUTANT_EDGE 0
#define BUILD_MUTANT_SEARCH 0
#ifdef MUT_ROTATION
#undef BUILD_MUTANT_ROT
#define BUILD_MUTANT_ROT 1
#endif
#ifdef MUT_EDGE_CLOSE
#undef BUILD_MUTANT_EDGE
#define BUILD_MUTANT_EDGE 2
#endif
#ifdef MUT_SEARCH_ONLY
#undef BUILD_MUTANT_SEARCH
#define BUILD_MUTANT_SEARCH 4
#endif
#define BUILD_MUTANT (BUILD_MUTANT_ROT | BUILD_MUTANT_EDGE | BUILD_MUTANT_SEARCH)

#if defined(MUT_ROTATION) && !defined(MUT_SEARCH_ONLY)
__attribute__((unused))
#endif
static void tri_coefs_true(int s, zw co[3]) {
    zw rho = s > 0 ? WK[1] : WK[5];                 /* w, or w^-1 = 1 - w */
    co[0].x = rho.x - 1; co[0].y = rho.y;
    co[1].x = -rho.x;    co[1].y = -rho.y;
    co[2].x = 1;         co[2].y = 0;
}
#ifdef MUT_ROTATION
static void tri_coefs_mut(int s, zw co[3]) {        /* RED CONTROL: w^2 in place of w */
    zw rho = s > 0 ? WK[2] : WK[4];
    co[0].x = rho.x - 1; co[0].y = rho.y;
    co[1].x = -rho.x;    co[1].y = -rho.y;
    co[2].x = 1;         co[2].y = 0;
}
#define TRI_SEARCH tri_coefs_mut
#ifdef MUT_SEARCH_ONLY
#define TRI_VERIFY tri_coefs_true
#else
#define TRI_VERIFY tri_coefs_mut
#endif
#else
#define TRI_SEARCH tri_coefs_true
#define TRI_VERIFY tri_coefs_true
#endif

#if defined(MUT_EDGE_CLOSE)
#define SEARCH_EDGE_CLOSE 1
#ifdef MUT_SEARCH_ONLY
#define VERIFY_EDGE_CLOSE 0
#else
#define VERIFY_EDGE_CLOSE 1
#endif
#else
#define SEARCH_EDGE_CLOSE 0
#define VERIFY_EDGE_CLOSE 0
#endif

/* ------------------------------------------------------------------------------------------------------------ */
/* The short lift F_p -> Z[w].  L = {(x, y) : x + y W = 0 mod p} is the kernel lattice; its norm form
   Q(x, y) = x^2 + x y + y^2 = |x + y w|^2 is >= p on L \ {0}.  So a residue has at most one preimage of norm
   < p / 4, and lift() returns it when its norm is < 2^58, else fails.                                           */

static i128 LB[2][2];          /* reduced basis of L: LB[0] = (x, y), LB[1] = (x, y) */
static i128 LDET;              /* LB[0].x LB[1].y - LB[1].x LB[0].y = +-p */

static i128 qform(i128 x, i128 y) { return x * x + x * y + y * y; }
static i128 bform(const i128 *a, const i128 *b) { return 2 * a[0] * b[0] + a[0] * b[1] + a[1] * b[0] + 2 * a[1] * b[1]; }
static i128 div_round(i128 a, i128 b) {            /* nearest integer to a / b, halves up; b != 0 */
    if (b < 0) { a = -a; b = -b; }
    i128 q = a / b, r = a % b;
    if (r < 0) { q -= 1; r += b; }
    if (2 * r >= b) q += 1;
    return q;
}
static void lattice_init(void) {
    i128 b1[2] = {(i128)PM, 0}, b2[2] = {(i128)(PM - WM), 1}, t[2];
    for (;;) {
        if (qform(b2[0], b2[1]) < qform(b1[0], b1[1])) { memcpy(t, b1, sizeof t); memcpy(b1, b2, sizeof t); memcpy(b2, t, sizeof t); }
        i128 mu = div_round(bform(b1, b2), bform(b1, b1));
        if (mu == 0) break;
        b2[0] -= mu * b1[0]; b2[1] -= mu * b1[1];
    }
    memcpy(LB[0], b1, sizeof b1); memcpy(LB[1], b2, sizeof b2);
    LDET = LB[0][0] * LB[1][1] - LB[1][0] * LB[0][1];
}
static int lift(u64 r, zw *out) {
    i128 a = div_round((i128)r * LB[1][1], LDET), b = div_round(-(i128)r * LB[0][1], LDET);
    i128 bx = 0, by = 0, bq = -1;
    for (int da = -1; da <= 1; da++)
        for (int db = -1; db <= 1; db++) {
            i128 sx = (i128)r - (a + da) * LB[0][0] - (b + db) * LB[1][0];
            i128 sy = -(a + da) * LB[0][1] - (b + db) * LB[1][1];
            i128 q = qform(sx, sy);
            if (bq < 0 || q < bq) { bq = q; bx = sx; by = sy; }
        }
    if (bq >= ((i128)1 << 58)) return 0;
    out->x = (i64)bx; out->y = (i64)by;
    return 1;
}

/* ------------------------------------------------------------------------------------------------------------ */
/* The current graph.                                                                                            */

static int N;
static u32 ADJ[MAXN];
static int NE, EP[MAXE], EQ[MAXE];                 /* edges p < q, lexicographic */
static int EID[MAXN][MAXN];
static int NNE, NA_[MAXE], NB_[MAXE];              /* non-edges a < b, lexicographic */
static int NC;
static unsigned char CYC[MAXCYC][4];               /* [u, v, w, x]: u = min, w opposite u, v < x */
static int NT;
static unsigned char TRI[MAXTRI][3];               /* a < b < c */
static int TRI_E[MAXTRI][3];                       /* its edges */
static int ETRI_N[MAXE], *ETRI[MAXE];              /* triangles on each edge */
static int ETRI_POOL[MAXTRI * 3];

static inline int is_edge(int a, int b) { return (ADJ[a] >> b) & 1u; }

static int decode_g6(const char *s, size_t len) {
    if (len < 1) return 0;
    int c0 = (unsigned char)s[0];
    if (c0 < 63 || c0 > 125) return 0;              /* n >= 63 (126 header) is out of range anyway */
    int n = c0 - 63;
    if (n > MAXN) return 0;
    int bits = n * (n - 1) / 2, chars = (bits + 5) / 6;
    if (len != (size_t)(1 + chars)) return 0;
    for (int i = 0; i < chars; i++) {
        int ch = (unsigned char)s[1 + i];
        if (ch < 63 || ch > 126) return 0;
    }
    memset(ADJ, 0, sizeof ADJ);
    int k = 0;
    for (int j = 1; j < n; j++)
        for (int i = 0; i < j; i++, k++) {
            int v = (unsigned char)s[1 + k / 6] - 63;
            if ((v >> (5 - k % 6)) & 1) { ADJ[i] |= 1u << j; ADJ[j] |= 1u << i; }
        }
    for (; k < chars * 6; k++) {                     /* padding bits must be zero */
        int v = (unsigned char)s[1 + k / 6] - 63;
        if ((v >> (5 - k % 6)) & 1) return 0;
    }
    N = n;
    return 1;
}

static int setup_graph(void) {
    NE = NNE = NC = NT = 0;
    for (int p = 0; p < N; p++)
        for (int q = p + 1; q < N; q++) {
            if (is_edge(p, q)) { EID[p][q] = EID[q][p] = NE; EP[NE] = p; EQ[NE] = q; NE++; }
            else { EID[p][q] = EID[q][p] = -1; NA_[NNE] = p; NB_[NNE] = q; NNE++; }
        }
    for (int u = 0; u < N; u++)
        for (int w = u + 1; w < N; w++) {
            u32 common = ADJ[u] & ADJ[w] & ~((2u << u) - 1u);      /* common neighbours > u */
            for (int v = u + 1; v < N; v++) {
                if (!((common >> v) & 1u)) continue;
                for (int x = v + 1; x < N; x++) {
                    if (!((common >> x) & 1u)) continue;
                    if (NC >= MAXCYC) return 0;
                    CYC[NC][0] = (unsigned char)u; CYC[NC][1] = (unsigned char)v;
                    CYC[NC][2] = (unsigned char)w; CYC[NC][3] = (unsigned char)x;
                    NC++;
                }
            }
        }
    for (int a = 0; a < N; a++)
        for (int b = a + 1; b < N; b++) {
            if (!is_edge(a, b)) continue;
            for (int c = b + 1; c < N; c++) {
                if (!is_edge(a, c) || !is_edge(b, c)) continue;
                if (NT >= MAXTRI) return 0;
                TRI[NT][0] = (unsigned char)a; TRI[NT][1] = (unsigned char)b; TRI[NT][2] = (unsigned char)c;
                TRI_E[NT][0] = EID[a][b]; TRI_E[NT][1] = EID[a][c]; TRI_E[NT][2] = EID[b][c];
                NT++;
            }
        }
    for (int e = 0; e < NE; e++) ETRI_N[e] = 0;
    for (int t = 0; t < NT; t++) for (int i = 0; i < 3; i++) ETRI_N[TRI_E[t][i]]++;
    int off = 0;
    for (int e = 0; e < NE; e++) { ETRI[e] = ETRI_POOL + off; off += ETRI_N[e]; ETRI_N[e] = 0; }
    for (int t = 0; t < NT; t++) for (int i = 0; i < 3; i++) { int e = TRI_E[t][i]; ETRI[e][ETRI_N[e]++] = t; }
    return 1;
}

/* ------------------------------------------------------------------------------------------------------------ */
/* Node state: the basis rows (independent, in insertion order), their dual vectors, the row-reduced null space
   (one vector per free column, Y[j][fcol[j]] = 1 and Y[j][fcol[j']] = 0) and det = the product of the pivots.     */

typedef struct {
    int k, d;
    int fcol[MAXN];
    u64 Y[MAXN][MAXN];
    u64 D[MAXN][MAXN];
    int bkind[MAXN];            /* 0: rhombus row (bid = cycle index); 1: triangle row (bid = triangle index) */
    int bid[MAXN];
    u64 det;
} state_t;

static state_t ST[MAXN + 2];

static void state_init(state_t *st) {
    st->k = 0; st->d = N; st->det = 1;
    memset(st->Y, 0, sizeof st->Y);
    for (int j = 0; j < N; j++) { st->fcol[j] = j; st->Y[j][j] = 1; }
}

/* Insert the sparse row (col[t], val[t]) if it is independent of the basis; returns 1 if inserted. */
static int state_insert(state_t *st, const int *col, const u64 *val, int len, int kind, int id) {
    int n = N, d = st->d, j0 = -1;
    u64 c[MAXN], nd[MAXN];
    for (int j = 0; j < d; j++) {
        u64 s = 0;
        for (int t = 0; t < len; t++) s = madd(s, mmul(val[t], st->Y[j][col[t]]));
        c[j] = s;
        if (s && j0 < 0) j0 = j;
    }
    if (j0 < 0) return 0;
    u64 inv = minv(c[j0]);
    for (int v = 0; v < n; v++) nd[v] = mmul(st->Y[j0][v], inv);
    for (int i = 0; i < st->k; i++) {
        u64 e = 0;
        for (int t = 0; t < len; t++) e = madd(e, mmul(val[t], st->D[i][col[t]]));
        if (e) for (int v = 0; v < n; v++) st->D[i][v] = msub(st->D[i][v], mmul(e, nd[v]));
    }
    for (int j = 0; j < d; j++) {
        if (j == j0 || !c[j]) continue;
        u64 f = mmul(c[j], inv);
        for (int v = 0; v < n; v++) st->Y[j][v] = msub(st->Y[j][v], mmul(f, st->Y[j0][v]));
    }
    for (int j = j0; j < d - 1; j++) { memcpy(st->Y[j], st->Y[j + 1], sizeof(u64) * (size_t)n); st->fcol[j] = st->fcol[j + 1]; }
    st->d = d - 1;
    memcpy(st->D[st->k], nd, sizeof(u64) * (size_t)n);
    st->bkind[st->k] = kind; st->bid[st->k] = id; st->k++;
    st->det = mmul(st->det, c[j0]);
    return 1;
}

/* Rhombus rows at the root: a fast pass for the (mostly dependent) +-1 rows. */
static void insert_cycles(state_t *st) {
    for (int ci = 0; ci < NC; ci++) {
        int u = CYC[ci][0], v = CYC[ci][1], w = CYC[ci][2], x = CYC[ci][3];
        int any = 0;
        for (int j = 0; j < st->d && !any; j++)
            any = madd(st->Y[j][u], st->Y[j][w]) != madd(st->Y[j][v], st->Y[j][x]);
        if (!any) continue;
        int col[4] = {u, v, w, x};
        u64 val[4] = {1, PM - 1, 1, PM - 1};
        state_insert(st, col, val, 4, 0, ci);
        if (st->d <= 1) return;         /* rank n - 1: everything is determined (and collides) */
    }
}

static void tri_row_mod(int t, int s, int col[3], u64 val[3]) {
    zw co[3];
    TRI_SEARCH(s, co);
    for (int i = 0; i < 3; i++) { col[i] = TRI[t][i]; val[i] = zw_mod(co[i]); }
}

/* ------------------------------------------------------------------------------------------------------------ */
/* Closure test.  y = a fixed pseudo-random element of the null space; a relation that holds on the whole null
   space holds at y, so y only proposes candidates, and each is confirmed on every null vector.                  */

static u64 RHO[MAXN];
static u64 Yv[MAXN];

static void compute_y(const state_t *st) {
    for (int v = 0; v < N; v++) Yv[v] = 0;
    for (int j = 0; j < st->d; j++) {
        u64 r = RHO[st->fcol[j]];
        for (int v = 0; v < N; v++) Yv[v] = madd(Yv[v], mmul(r, st->Y[j][v]));
    }
}

/* is e_a - e_b - W^k (e_p - e_q) (or e_a - e_b when p < 0) in the span? */
static int in_span_target(const state_t *st, int a, int b, int p, int q, int k) {
    for (int j = 0; j < st->d; j++) {
        const u64 *y = st->Y[j];
        u64 lhs = msub(y[a], y[b]);
        if (p >= 0) lhs = msub(lhs, mmul(WMK[k], msub(y[p], y[q])));
        if (lhs) return 0;
    }
    return 1;
}

typedef struct { int a, b, p, q, k; } closure_t;    /* p < 0: collision */

#define HBITS 11
#define HSIZE (1 << HBITS)
static u64 HKEY[HSIZE];
static int HVAL[HSIZE];
static u32 HSTAMP[HSIZE], HCUR;

static inline u32 hslot(u64 key) { return (u32)((key * UINT64_C(0x9E3779B97F4A7C15)) >> (64 - HBITS)); }
static inline u64 pow6(u64 x) { u64 x2 = mmul(x, x), x3 = mmul(x2, x); return mmul(x3, x3); }

static int closure(const state_t *st, closure_t *out) {
    for (int a = 0; a < N; a++)
        for (int b = a + 1; b < N; b++)
            if (Yv[a] == Yv[b] && in_span_target(st, a, b, -1, -1, 0)) {
                out->a = a; out->b = b; out->p = out->q = -1; out->k = 0;
                return 1;
            }
    if (++HCUR == 0) { memset(HSTAMP, 0, sizeof HSTAMP); HCUR = 1; }
    for (int e = 0; e < NE; e++) {             /* edges in lexicographic order; linear probing keeps that order */
        u64 d = msub(Yv[EP[e]], Yv[EQ[e]]);
        if (!d) continue;
        u64 key = pow6(d);
        u32 h = hslot(key);
        while (HSTAMP[h] == HCUR) h = (h + 1) & (HSIZE - 1);
        HSTAMP[h] = HCUR; HKEY[h] = key; HVAL[h] = e;
    }
    for (int a = 0; a < N; a++)
        for (int b = a + 1; b < N; b++) {
            if (is_edge(a, b) && !SEARCH_EDGE_CLOSE) continue;
            u64 t = msub(Yv[a], Yv[b]);
            if (!t) continue;
            u64 key = pow6(t);
            for (u32 h = hslot(key); HSTAMP[h] == HCUR; h = (h + 1) & (HSIZE - 1)) {
                if (HKEY[h] != key) continue;
                int e = HVAL[h], p = EP[e], q = EQ[e];
                if (SEARCH_EDGE_CLOSE && p == a && q == b) continue;
                u64 d = msub(Yv[p], Yv[q]);
                for (int k = 0; k < 6; k++) {
                    if (mmul(WMK[k], d) != t) continue;
                    if (in_span_target(st, a, b, p, q, k)) {
                        out->a = a; out->b = b; out->p = p; out->q = q; out->k = k;
                        return 1;
                    }
                    break;                      /* at most one k matches at y */
                }
            }
        }
    return 0;
}

/* is t(T, s) independent of the span?  (y decides "independent"; "dependent" is confirmed on every null vector) */
static int tri_independent(const state_t *st, int t, int s) {
    int col[3]; u64 val[3];
    tri_row_mod(t, s, col, val);
    u64 z = 0;
    for (int i = 0; i < 3; i++) z = madd(z, mmul(val[i], Yv[col[i]]));
    if (z) return 1;
    for (int j = 0; j < st->d; j++) {
        u64 s2 = 0;
        for (int i = 0; i < 3; i++) s2 = madd(s2, mmul(val[i], st->Y[j][col[i]]));
        if (s2) return 1;
    }
    return 0;
}

static int ONPATH[MAXTRI], ADJCNT[MAXTRI];

static int choose_split(const state_t *st) {
    int first = -1;
    for (int t = 0; t < NT; t++) {
        if (ONPATH[t]) continue;
        if (first >= 0 && ADJCNT[t] == 0) continue;
        if (!tri_independent(st, t, 1) || !tri_independent(st, t, -1)) continue;
        if (ADJCNT[t] > 0) return t;
        first = t;
    }
    return first;
}

static void path_push(int t, int delta) {
    ONPATH[t] += delta;
    for (int i = 0; i < 3; i++) {
        int e = TRI_E[t][i];
        for (int j = 0; j < ETRI_N[e]; j++) if (ETRI[e][j] != t) ADJCNT[ETRI[e][j]] += delta;
    }
}

/* ------------------------------------------------------------------------------------------------------------ */
/* The tree under construction.                                                                                  */

typedef struct { int leaf; int tri; int plus, minus; } node_t;     /* leaf >= 0: a leaf node */
typedef struct { int ncyc, cyc_off, ntri, tri_off; zw scale; int a, b, p, q, k; } leaf_t;

static int BUDGET = DEFAULT_BUDGET, MIRROR = 1;
static node_t *NODES;
static leaf_t *LEAVES;
static int *LCYC, *LTRI;
static zw *LCYCC, *LTRIC;
static int NNODES, NLEAVES, NLCYC, NLTRI, NODE_LIMIT;

enum { AB_NONE, AB_OPEN, AB_BUDGET, AB_LIFT, AB_INTERNAL };
static int ABORT;

static i64 gcd64(i64 a, i64 b) { if (a < 0) a = -a; if (b < 0) b = -b; while (b) { i64 t = a % b; a = b; b = t; } return a; }

static int make_leaf(const state_t *st, const closure_t *cl) {
    int vc[4], vl = 0;
    u64 vv[4];
    int cols[4] = {cl->a, cl->b, cl->p, cl->q};
    u64 vals[4] = {1, PM - 1, 0, 0};
    int m = 2;
    if (cl->p >= 0) { vals[2] = msub(0, WMK[cl->k]); vals[3] = WMK[cl->k]; m = 4; }
    for (int i = 0; i < m; i++) {                   /* merge repeated columns */
        int j;
        for (j = 0; j < vl; j++) if (vc[j] == cols[i]) break;
        if (j == vl) { vc[vl] = cols[i]; vv[vl] = 0; vl++; }
        vv[j] = madd(vv[j], vals[i]);
    }
    zw scale, coef[MAXN];
    int sup[MAXN], ns = 0;
    if (!lift(st->det, &scale)) return -1;
    for (int i = 0; i < st->k; i++) {
        u64 c = 0;
        for (int t = 0; t < vl; t++) c = madd(c, mmul(vv[t], st->D[i][vc[t]]));
        if (!c) continue;
        if (!lift(mmul(st->det, c), &coef[ns])) return -1;
        sup[ns++] = i;
    }
    i64 g = gcd64(scale.x, scale.y);
    for (int i = 0; i < ns; i++) g = gcd64(g, gcd64(coef[i].x, coef[i].y));
    if (g == 0) return -1;
    scale.x /= g; scale.y /= g;
    for (int i = 0; i < ns; i++) { coef[i].x /= g; coef[i].y /= g; }
    leaf_t *L = &LEAVES[NLEAVES];
    L->ncyc = L->ntri = 0; L->cyc_off = NLCYC; L->tri_off = NLTRI;
    for (int i = 0; i < ns; i++)
        if (st->bkind[sup[i]] == 0) { LCYC[NLCYC] = st->bid[sup[i]]; LCYCC[NLCYC] = coef[i]; NLCYC++; L->ncyc++; }
    for (int i = 0; i < ns; i++)
        if (st->bkind[sup[i]] == 1) { LTRI[NLTRI] = st->bid[sup[i]]; LTRIC[NLTRI] = coef[i]; NLTRI++; L->ntri++; }
    L->scale = scale; L->a = cl->a; L->b = cl->b; L->p = cl->p; L->q = cl->q; L->k = cl->k;
    return NLEAVES++;
}

static int build(int depth) {
    state_t *st = &ST[depth];
    if (NNODES >= NODE_LIMIT) { ABORT = AB_BUDGET; return -1; }
    int me = NNODES++;
    compute_y(st);
    closure_t cl;
    if (closure(st, &cl)) {
        int lf = make_leaf(st, &cl);
        if (lf < 0) { ABORT = AB_LIFT; return -1; }
        NODES[me].leaf = lf; NODES[me].tri = -1; NODES[me].plus = NODES[me].minus = -1;
        return me;
    }
    int t = choose_split(st);
    if (t < 0) { ABORT = AB_OPEN; return -1; }
    if (depth + 1 > MAXN) { ABORT = AB_INTERNAL; return -1; }
    NODES[me].leaf = -1; NODES[me].tri = t;
    path_push(t, 1);
    int kids[2] = {-1, -1};
    for (int side = 0; side < 2; side++) {
        int s = side == 0 ? 1 : -1;
        if (side == 1 && depth == 0 && MIRROR) break;
        int col[3]; u64 val[3];
        memcpy(&ST[depth + 1], st, sizeof(state_t));
        tri_row_mod(t, s, col, val);
        if (!state_insert(&ST[depth + 1], col, val, 3, 1, t)) { ABORT = AB_INTERNAL; return -1; }
        kids[side] = build(depth + 1);
        if (kids[side] < 0) return -1;
    }
    path_push(t, -1);
    NODES[me].plus = kids[0]; NODES[me].minus = kids[1];
    return me;
}

static zw zw_conj(zw a) { zw r; r.x = a.x + a.y; r.y = -a.y; return r; }

/* The mirror image of the subtree at `src` (plus and minus exchanged, leaves conjugated); returns its root. */
static int mirror(int src) {
    if (NNODES >= BUDGET) { ABORT = AB_BUDGET; return -1; }
    int me = NNODES++;
    if (NODES[src].leaf >= 0) {
        const leaf_t *S = &LEAVES[NODES[src].leaf];
        leaf_t *L = &LEAVES[NLEAVES];
        *L = *S;
        L->cyc_off = NLCYC; L->tri_off = NLTRI;
        for (int i = 0; i < S->ncyc; i++) { LCYC[NLCYC] = LCYC[S->cyc_off + i]; LCYCC[NLCYC] = zw_conj(LCYCC[S->cyc_off + i]); NLCYC++; }
        for (int i = 0; i < S->ntri; i++) { LTRI[NLTRI] = LTRI[S->tri_off + i]; LTRIC[NLTRI] = zw_conj(LTRIC[S->tri_off + i]); NLTRI++; }
        L->scale = zw_conj(S->scale);
        if (S->p >= 0) L->k = (6 - S->k) % 6;
        NODES[me].leaf = NLEAVES++; NODES[me].tri = -1; NODES[me].plus = NODES[me].minus = -1;
        return me;
    }
    NODES[me].leaf = -1; NODES[me].tri = NODES[src].tri;
    int a = mirror(NODES[src].minus);
    if (a < 0) return -1;
    int b = mirror(NODES[src].plus);
    if (b < 0) return -1;
    NODES[me].plus = a; NODES[me].minus = b;
    return me;
}

/* ------------------------------------------------------------------------------------------------------------ */
/* Serialisation.                                                                                                */

static char *OB;
static size_t OBLEN, OBCAP;

static void ob_reserve(size_t extra) {
    if (OBLEN + extra <= OBCAP) return;
    size_t cap = OBCAP ? OBCAP : 1 << 16;
    while (cap < OBLEN + extra) cap *= 2;
    char *p = realloc(OB, cap);
    if (!p) { fprintf(stderr, "udtriangle: out of memory\n"); exit(2); }
    OB = p; OBCAP = cap;
}
static void ob_str(const char *s) { size_t l = strlen(s); ob_reserve(l); memcpy(OB + OBLEN, s, l); OBLEN += l; }
static void ob_int(i64 v) {
    char tmp[24]; int l = 0;
    u64 u = v < 0 ? (u64)0 - (u64)v : (u64)v;
    do { tmp[l++] = (char)('0' + u % 10); u /= 10; } while (u);
    ob_reserve(22);
    if (v < 0) OB[OBLEN++] = '-';
    while (l) OB[OBLEN++] = tmp[--l];
}
static void ob_zw(zw z) { ob_str("["); ob_int(z.x); ob_str(","); ob_int(z.y); ob_str("]"); }

static void ob_node(int nd) {
    if (NODES[nd].leaf < 0) {
        int t = NODES[nd].tri;
        ob_str("{\"split\":["); ob_int(TRI[t][0]); ob_str(","); ob_int(TRI[t][1]); ob_str(","); ob_int(TRI[t][2]);
        ob_str("],\"plus\":"); ob_node(NODES[nd].plus);
        ob_str(",\"minus\":"); ob_node(NODES[nd].minus);
        ob_str("}");
        return;
    }
    const leaf_t *L = &LEAVES[NODES[nd].leaf];
    ob_str("{\"leaf\":{\"cycles\":[");
    for (int i = 0; i < L->ncyc; i++) {
        const unsigned char *c = CYC[LCYC[L->cyc_off + i]];
        if (i) ob_str(",");
        ob_str("["); ob_int(c[0]); ob_str(","); ob_int(c[1]); ob_str(","); ob_int(c[2]); ob_str(","); ob_int(c[3]); ob_str("]");
    }
    ob_str("],\"cycle_coefficients\":[");
    for (int i = 0; i < L->ncyc; i++) { if (i) ob_str(","); ob_zw(LCYCC[L->cyc_off + i]); }
    ob_str("],\"triangles\":[");
    for (int i = 0; i < L->ntri; i++) {
        const unsigned char *t = TRI[LTRI[L->tri_off + i]];
        if (i) ob_str(",");
        ob_str("["); ob_int(t[0]); ob_str(","); ob_int(t[1]); ob_str(","); ob_int(t[2]); ob_str("]");
    }
    ob_str("],\"triangle_coefficients\":[");
    for (int i = 0; i < L->ntri; i++) { if (i) ob_str(","); ob_zw(LTRIC[L->tri_off + i]); }
    ob_str("],\"scale\":"); ob_zw(L->scale);
    ob_str(",\"pair\":["); ob_int(L->a); ob_str(","); ob_int(L->b); ob_str("]");
    if (L->p >= 0) {
        ob_str(",\"edge\":["); ob_int(L->p); ob_str(","); ob_int(L->q); ob_str("],\"zeta\":"); ob_int(L->k);
    }
    ob_str("}}");
}

/* ------------------------------------------------------------------------------------------------------------ */
/* Strict re-parse of the serialised line into a fresh structure (the self-verifier never reads the search's
   structures).                                                                                                  */

typedef struct { int leaf; i64 v[3]; int plus, minus; } pnode_t;
typedef struct { int ncyc, cyc_off, ntri, tri_off, has_edge; i64 sx, sy, a, b, p, q, zeta; } pleaf_t;

static pnode_t *PN;
static pleaf_t *PL;
static i64 (*PCYC)[4], (*PTRI)[3], (*PCYCC)[2], (*PTRIC)[2];
static int NPN, NPL, NPCYC, NPTRI, NPCYCC, NPTRIC, PCAP_NODES, PCAP_ROWS;
static const char *PS;          /* parse cursor */
static int PFAIL;

static void lit(const char *s) {
    size_t l = strlen(s);
    if (PFAIL || strncmp(PS, s, l) != 0) { PFAIL = 1; return; }
    PS += l;
}
static int peek(const char *s) { return !PFAIL && strncmp(PS, s, strlen(s)) == 0; }
static i64 pint(void) {
    if (PFAIL) return 0;
    int neg = 0;
    if (*PS == '-') { neg = 1; PS++; }
    if (*PS < '0' || *PS > '9') { PFAIL = 1; return 0; }
    if (*PS == '0' && PS[1] >= '0' && PS[1] <= '9') { PFAIL = 1; return 0; }    /* no leading zeros */
    if (neg && *PS == '0') { PFAIL = 1; return 0; }                             /* no "-0" */
    u64 v = 0; int digits = 0;
    while (*PS >= '0' && *PS <= '9') {
        if (++digits > 19) { PFAIL = 1; return 0; }
        v = v * 10 + (u64)(*PS++ - '0');
    }
    if (v > (u64)INT64_MAX) { PFAIL = 1; return 0; }
    return neg ? -(i64)v : (i64)v;
}
static void pints(i64 *out, int k) {       /* [i,i,...] with exactly k integers */
    lit("[");
    for (int i = 0; i < k; i++) { if (i) lit(","); out[i] = pint(); }
    lit("]");
}

static int parse_node(int depth) {
    if (PFAIL) return -1;
    if (depth > SPEC_MAX_DEPTH + 1 || NPN >= PCAP_NODES) { PFAIL = 1; return -1; }
    int me = NPN++;
    if (peek("{\"split\":")) {
        lit("{\"split\":");
        PN[me].leaf = -1;
        pints(PN[me].v, 3);
        lit(",\"plus\":"); int a = parse_node(depth + 1);
        lit(",\"minus\":"); int b = parse_node(depth + 1);
        lit("}");
        PN[me].plus = a; PN[me].minus = b;
        return PFAIL ? -1 : me;
    }
    lit("{\"leaf\":{\"cycles\":[");
    if (PFAIL || NPL >= PCAP_NODES) { PFAIL = 1; return -1; }
    pleaf_t *L = &PL[NPL];
    PN[me].leaf = NPL++;
    L->cyc_off = NPCYC; L->ncyc = 0;
    while (!PFAIL && *PS != ']') {
        if (L->ncyc) lit(",");
        if (NPCYC >= PCAP_ROWS) { PFAIL = 1; break; }
        pints(PCYC[NPCYC++], 4); L->ncyc++;
    }
    lit("],\"cycle_coefficients\":[");
    int ncc = 0, cc_off = NPCYCC;
    while (!PFAIL && *PS != ']') {
        if (ncc) lit(",");
        if (NPCYCC >= PCAP_ROWS) { PFAIL = 1; break; }
        pints(PCYCC[NPCYCC++], 2); ncc++;
    }
    lit("],\"triangles\":[");
    L->tri_off = NPTRI; L->ntri = 0;
    while (!PFAIL && *PS != ']') {
        if (L->ntri) lit(",");
        if (NPTRI >= PCAP_ROWS) { PFAIL = 1; break; }
        pints(PTRI[NPTRI++], 3); L->ntri++;
    }
    lit("],\"triangle_coefficients\":[");
    int ntc = 0, tc_off = NPTRIC;
    while (!PFAIL && *PS != ']') {
        if (ntc) lit(",");
        if (NPTRIC >= PCAP_ROWS) { PFAIL = 1; break; }
        pints(PTRIC[NPTRIC++], 2); ntc++;
    }
    lit("],\"scale\":");
    i64 sc[2] = {0, 0}; pints(sc, 2); L->sx = sc[0]; L->sy = sc[1];
    lit(",\"pair\":");
    i64 pr[2] = {0, 0}; pints(pr, 2); L->a = pr[0]; L->b = pr[1];
    L->has_edge = 0; L->p = L->q = L->zeta = 0;
    if (peek(",\"edge\":")) {
        lit(",\"edge\":");
        i64 ed[2] = {0, 0}; pints(ed, 2); L->p = ed[0]; L->q = ed[1];
        lit(",\"zeta\":"); L->zeta = pint();
        L->has_edge = 1;
    }
    lit("}}");
    /* rule 2: coefficient lists match their lists in length (positions line up with the row pools) */
    if (ncc != L->ncyc || cc_off != L->cyc_off || ntc != L->ntri || tc_off != L->tri_off) PFAIL = 1;
    return PFAIL ? -1 : me;
}

/* ------------------------------------------------------------------------------------------------------------ */
/* Exact verification of the parsed tree: Section 4 rules 1-5.                                                   */

typedef struct { i128 x, y; } zw128;
static zw128 zmul128(zw128 a, zw128 b) {
    zw128 r;
    r.x = a.x * b.x - a.y * b.y;
    r.y = a.x * b.y + a.y * b.x + a.y * b.y;
    return r;
}
static int coef_ok(i64 x) { return x > -COEF_BOUND && x < COEF_BOUND; }
static int vtx_ok(i64 x) { return x >= 0 && x < N; }

static i64 VPATH[SPEC_MAX_DEPTH + 2][3];
static int VSIGN[SPEC_MAX_DEPTH + 2];
static int VNODES, VANY_EDGE;

static int verify_leaf(const pleaf_t *L, int depth) {
    zw128 acc[MAXN];
    for (int v = 0; v < N; v++) acc[v].x = acc[v].y = 0;
    for (int i = 0; i < L->ncyc; i++) {                     /* rule 2: 4-cycles of G (Section 2 rule 2) */
        const i64 *c = PCYC[L->cyc_off + i];
        for (int j = 0; j < 4; j++) if (!vtx_ok(c[j])) return 0;
        for (int j = 0; j < 4; j++) for (int l = j + 1; l < 4; l++) if (c[j] == c[l]) return 0;
        for (int j = 0; j < 4; j++) if (!is_edge((int)c[j], (int)c[(j + 1) % 4])) return 0;
        const i64 *co = PCYCC[L->cyc_off + i];
        if (!coef_ok(co[0]) || !coef_ok(co[1])) return 0;
        for (int j = 0; j < 4; j++) {
            int sgn = (j % 2 == 0) ? 1 : -1;
            acc[c[j]].x += sgn * (i128)co[0];
            acc[c[j]].y += sgn * (i128)co[1];
        }
    }
    for (int i = 0; i < L->ntri; i++) {                     /* rule 2: triangles split on the path, path's sign */
        const i64 *t = PTRI[L->tri_off + i];
        int s = 0;
        for (int d = 0; d < depth; d++)
            if (VPATH[d][0] == t[0] && VPATH[d][1] == t[1] && VPATH[d][2] == t[2]) { s = VSIGN[d]; break; }
        if (!s) return 0;
        const i64 *co = PTRIC[L->tri_off + i];
        if (!coef_ok(co[0]) || !coef_ok(co[1])) return 0;
        zw tc[3];
        TRI_VERIFY(s, tc);
        zw128 m = {co[0], co[1]};
        for (int j = 0; j < 3; j++) {
            zw128 e = {tc[j].x, tc[j].y}, pr = zmul128(m, e);
            acc[t[j]].x += pr.x; acc[t[j]].y += pr.y;
        }
    }
    if (!coef_ok(L->sx) || !coef_ok(L->sy) || (L->sx == 0 && L->sy == 0)) return 0;
    if (!vtx_ok(L->a) || !vtx_ok(L->b) || L->a == L->b) return 0;      /* rule 3 */
    zw128 tgt[MAXN];
    for (int v = 0; v < N; v++) tgt[v].x = tgt[v].y = 0;
    tgt[L->a].x += 1; tgt[L->b].x -= 1;
    if (L->has_edge) {
        if (!vtx_ok(L->p) || !vtx_ok(L->q) || L->p == L->q || !is_edge((int)L->p, (int)L->q)) return 0;
        if (is_edge((int)L->a, (int)L->b) && !VERIFY_EDGE_CLOSE) return 0;
        if (L->zeta < 0 || L->zeta > 5) return 0;
        zw wk = WK[L->zeta];
        tgt[L->p].x -= wk.x; tgt[L->p].y -= wk.y;
        tgt[L->q].x += wk.x; tgt[L->q].y += wk.y;
        VANY_EDGE = 1;
    }
    zw128 sc = {L->sx, L->sy};
    for (int v = 0; v < N; v++) {                           /* rule 4 */
        zw128 rhs = zmul128(sc, tgt[v]);
        if (acc[v].x != rhs.x || acc[v].y != rhs.y) return 0;
    }
    return 1;
}

static int verify_node(int nd, int depth) {
    if (nd < 0 || ++VNODES > SPEC_MAX_NODES || VNODES > BUDGET || depth > SPEC_MAX_DEPTH) return 0;
    const pnode_t *P = &PN[nd];
    if (P->leaf >= 0) return verify_leaf(&PL[P->leaf], depth);
    const i64 *t = P->v;                                    /* rule 1 */
    if (!vtx_ok(t[0]) || !vtx_ok(t[1]) || !vtx_ok(t[2])) return 0;
    if (!(t[0] < t[1] && t[1] < t[2])) return 0;
    if (!is_edge((int)t[0], (int)t[1]) || !is_edge((int)t[0], (int)t[2]) || !is_edge((int)t[1], (int)t[2])) return 0;
    for (int d = 0; d < depth; d++)
        if (VPATH[d][0] == t[0] && VPATH[d][1] == t[1] && VPATH[d][2] == t[2]) return 0;
    if (depth >= SPEC_MAX_DEPTH) return 0;
    memcpy(VPATH[depth], t, sizeof VPATH[depth]);
    VSIGN[depth] = 1;
    if (!verify_node(P->plus, depth + 1)) return 0;
    memcpy(VPATH[depth], t, sizeof VPATH[depth]);
    VSIGN[depth] = -1;
    return verify_node(P->minus, depth + 1);
}

/* Parse and verify OB[start..]: the line {"verdict":V,"witness":{"tri":{"tree":NODE}}}. */
static int self_verify(size_t start, int *nodes_out) {
    ob_reserve(1); OB[OBLEN] = '\0';
    PS = OB + start; PFAIL = 0;
    NPN = NPL = NPCYC = NPTRI = NPCYCC = NPTRIC = 0;
    int tu;
    if (peek("{\"verdict\":\"refuted\"")) { lit("{\"verdict\":\"refuted\""); tu = 0; }
    else { lit("{\"verdict\":\"tu\""); tu = 1; }
    lit(",\"witness\":{\"tri\":{\"tree\":");
    int root = parse_node(0);
    lit("}}}\n");
    if (PFAIL || root != 0 || *PS != '\0') return 0;
    VNODES = 0; VANY_EDGE = 0;
    if (!verify_node(root, 0)) return 0;
    if (VNODES != NPN) return 0;
    if (tu != VANY_EDGE) return 0;                          /* rule 5 */
    *nodes_out = VNODES;
    return 1;
}

/* ------------------------------------------------------------------------------------------------------------ */

static long long S_GRAPHS, S_PASS, S_REF, S_TU, S_OPEN, S_BUDGET, S_LIFT, S_INTERNAL, S_VFAIL, S_NODES, S_LEAVES;
static long long S_MAXNODES, S_ROOTLEAF, S_NOCYC;

static void *xcalloc(size_t n, size_t sz) {
    void *p = calloc(n ? n : 1, sz);
    if (!p) { fprintf(stderr, "udtriangle: out of memory\n"); exit(2); }
    return p;
}

static u64 splitmix(u64 *s) {
    u64 z = (*s += UINT64_C(0x9E3779B97F4A7C15));
    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

static int init_constants(void) {
    u64 s3 = mpow(PM - 3, (PM + 1) / 4);                    /* sqrt(-3): p = 3 mod 4 */
    if (mmul(s3, s3) != PM - 3) return 0;
    WM = mmul(madd(1, s3), minv(2));
    if (madd(msub(mmul(WM, WM), WM), 1) != 0) return 0;     /* W^2 - W + 1 = 0 */
    WMK[0] = 1;
    for (int k = 1; k < 6; k++) WMK[k] = mmul(WMK[k - 1], WM);
    if (mmul(WMK[5], WM) != 1 || WMK[3] != PM - 1) return 0;
    for (int k = 0; k < 6; k++) if (zw_mod(WK[k]) != WMK[k]) return 0;
    lattice_init();
    if (!(LDET == (i128)PM || LDET == -(i128)PM)) return 0;
    for (int i = 0; i < 2; i++)                             /* basis vectors lie in the kernel lattice */
        if (madd(imod((i64)(LB[i][0] % (i128)PM)), mmul(imod((i64)(LB[i][1] % (i128)PM)), WM)) != 0) return 0;
    u64 seed = UINT64_C(20260926);
    for (int i = 0; i < 2000; i++) {                        /* lift round trip on short elements */
        zw a, b;
        a.x = (i64)(splitmix(&seed) % (UINT64_C(1) << 27)) - ((i64)1 << 26);
        a.y = (i64)(splitmix(&seed) % (UINT64_C(1) << 27)) - ((i64)1 << 26);
        if (!lift(zw_mod(a), &b) || b.x != a.x || b.y != a.y) return 0;
    }
    for (int v = 0; v < MAXN; v++) RHO[v] = splitmix(&seed) % PM;
    return 1;
}

static void usage(void) {
    fprintf(stderr, "usage: udtriangle [-b N | --budget N] [--no-mirror] < graphs.g6 > verdicts.jsonl\n"
                    "  -b, --budget N  case-tree node budget per graph (default %d, 1..%d); beyond it the graph passes\n"
                    "  --no-mirror     search the minus subtree of the root split instead of mirroring (same output)\n",
            DEFAULT_BUDGET, SPEC_MAX_NODES);
}

int main(int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        if ((strcmp(argv[i], "-b") == 0 || strcmp(argv[i], "--budget") == 0) && i + 1 < argc) {
            char *end;
            long v = strtol(argv[++i], &end, 10);
            if (*end || v < 1 || v > SPEC_MAX_NODES) { usage(); return 2; }
            BUDGET = (int)v;
        } else if (strcmp(argv[i], "--no-mirror") == 0) MIRROR = 0;
        else { usage(); return 2; }
    }
    if (!init_constants()) { fprintf(stderr, "udtriangle: arithmetic self-test failed\n"); return 2; }
    NODES = xcalloc((size_t)BUDGET, sizeof *NODES);
    LEAVES = xcalloc((size_t)BUDGET, sizeof *LEAVES);
    LCYC = xcalloc((size_t)BUDGET * MAXN, sizeof *LCYC);
    LTRI = xcalloc((size_t)BUDGET * MAXN, sizeof *LTRI);
    LCYCC = xcalloc((size_t)BUDGET * MAXN, sizeof *LCYCC);
    LTRIC = xcalloc((size_t)BUDGET * MAXN, sizeof *LTRIC);
    PCAP_NODES = BUDGET; PCAP_ROWS = BUDGET * MAXN;
    PN = xcalloc((size_t)PCAP_NODES, sizeof *PN);
    PL = xcalloc((size_t)PCAP_NODES, sizeof *PL);
    PCYC = xcalloc((size_t)PCAP_ROWS, sizeof *PCYC);
    PTRI = xcalloc((size_t)PCAP_ROWS, sizeof *PTRI);
    PCYCC = xcalloc((size_t)PCAP_ROWS, sizeof *PCYCC);
    PTRIC = xcalloc((size_t)PCAP_ROWS, sizeof *PTRIC);

    char *line = NULL;
    size_t cap = 0;
    ssize_t got;
    while ((got = getline(&line, &cap, stdin)) != -1) {
        size_t len = (size_t)got;
        if (len && line[len - 1] == '\n') len--;
        if (len && line[len - 1] == '\r') len--;
        if (!decode_g6(line, len)) { fprintf(stderr, "udtriangle: invalid graph6 input (or more than %d vertices) at graph %lld\n", MAXN, S_GRAPHS + 1); return 2; }
        if (!setup_graph()) { fprintf(stderr, "udtriangle: graph too large for the cycle table\n"); return 2; }
        S_GRAPHS++;
        memset(ONPATH, 0, sizeof(int) * (size_t)NT);
        memset(ADJCNT, 0, sizeof(int) * (size_t)NT);
        state_init(&ST[0]);
        insert_cycles(&ST[0]);
        NNODES = NLEAVES = NLCYC = NLTRI = 0;
        ABORT = AB_NONE;
        NODE_LIMIT = MIRROR ? 1 + (BUDGET - 1) / 2 : BUDGET;
        int root = build(0);
        if (root == 0 && MIRROR && NODES[0].leaf < 0) {
            NODE_LIMIT = BUDGET;
            int m = mirror(NODES[0].plus);
            if (m < 0) root = -1; else NODES[0].minus = m;
        }
        OBLEN = 0;
        int emitted = 0, nodes = 0;
        if (root == 0) {
            int any_edge = 0;
            for (int i = 0; i < NLEAVES; i++) if (LEAVES[i].p >= 0) any_edge = 1;
            ob_str(any_edge ? "{\"verdict\":\"tu\"" : "{\"verdict\":\"refuted\"");
            ob_str(",\"witness\":{\"tri\":{\"tree\":");
            ob_node(0);
            ob_str("}}}\n");
            if (self_verify(0, &nodes)) {
                emitted = 1;
                if (any_edge) S_TU++; else S_REF++;
                S_NODES += nodes; S_LEAVES += NLEAVES;
                if (nodes > S_MAXNODES) S_MAXNODES = nodes;
                if (nodes == 1) S_ROOTLEAF++;
                for (int i = 0; i < NLEAVES; i++) if (LEAVES[i].ncyc == 0) S_NOCYC++;   /* see the "cycles" note */
            } else S_VFAIL++;
        } else {
            switch (ABORT) {
            case AB_OPEN: S_OPEN++; break;
            case AB_BUDGET: S_BUDGET++; break;
            case AB_LIFT: S_LIFT++; break;
            default: S_INTERNAL++; break;
            }
        }
        if (!emitted) { OBLEN = 0; ob_str("{\"verdict\":\"pass\"}\n"); S_PASS++; }
        if (fwrite(OB, 1, OBLEN, stdout) != OBLEN) { fprintf(stderr, "udtriangle: write error\n"); return 2; }
    }
    free(line);
    if (fflush(stdout) != 0) { fprintf(stderr, "udtriangle: write error\n"); return 2; }
    fprintf(stderr, "udtriangle: graphs=%lld refuted=%lld tu=%lld pass=%lld (open=%lld budget=%lld verify_fail=%lld "
                    "lift_fail=%lld internal=%lld) root_leaf=%lld tree_nodes=%lld leaves=%lld leaves_without_cycles=%lld "
                    "max_nodes=%lld budget_limit=%d mirror=%d mutant=%d\n",
            S_GRAPHS, S_REF, S_TU, S_PASS, S_OPEN, S_BUDGET, S_VFAIL, S_LIFT, S_INTERNAL, S_ROOTLEAF, S_NODES, S_LEAVES,
            S_NOCYC, S_MAXNODES, BUDGET, MIRROR, BUILD_MUTANT);
    return 0;
}
