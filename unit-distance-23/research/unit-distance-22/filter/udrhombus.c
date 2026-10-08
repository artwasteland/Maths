/* udrhombus: the prover of the rhombus rule (research/unit-distance-23/RHOMBUS-SPEC.md, binding).

   Lemma R.  If f: V(G) -> R^2 is injective and |f(s) - f(t)| = 1 for every edge st, then every
   4-cycle u-v-w-x of G (four distinct vertices, uv, vw, wx, xu edges) is a rhombus:
   f(u) + f(w) = f(v) + f(x).  With r(C) = e_u - e_v + e_w - e_x this says sum_i r(C)_i f(i) = 0.

   R1 (collision, verdict "refuted"):  sum_j l_j r(C_j) = s (e_a - e_b), s != 0, a != b.
   R2 (forced unit distance, "tu"):     sum_j l_j r(C_j) = s (e_a - e_b - e_p + e_q), s != 0,
                                        pq an edge, ab NOT an edge.

   Contract (spec Section 3).  graph6 lines on stdin; exactly one JSON line per input line on
   stdout, in order: {"verdict":"pass"}, or {"verdict":"refuted","witness":{"rhombus":{"cycles":
   [[u,v,w,x],...],"coefficients":[...],"scale":s,"pair":[a,b]}}}, or the same with verdict "tu"
   and an "edge":[p,q] entry.  Priority: the lexicographically first colliding pair a < b; else
   the lexicographically first NON-adjacent pair a < b whose difference is forced, with the
   lexicographically first ordered edge (p, q) that forces it; else pass.  Every certificate is
   re-verified against Section 2 in exact integer arithmetic before it is written; a failure
   writes pass and is counted in the statistics line on stderr.  Nothing here removes a graph
   without a certificate, and the output is a function of the input bytes alone.

   Method.
   1. The 4-cycles.  For u < w and common neighbours v < x of u and w with u < v, the cycle is
      [u, v, w, x] (u is its smallest vertex).  Each 4-cycle has two diagonals, {u, w} and {v, x};
      the condition u < v keeps exactly the one through the smallest vertex, so every 4-cycle is
      listed once (the other diagonal would give -r(C)).
   2. Detection modulo the prime P = 2^61 - 1.  The rows are inserted into an echelon basis mod P
      (normalised pivots).  This decides the RATIONAL question exactly: every matrix involved has
      rows of Euclidean norm at most sqrt 6 (a cycle row has four entries +-1; a target vector
      e_a - e_b - e_p + e_q has norm 2, or sqrt 6 when a = q or b = p), at most 32 of them are
      independent, so by Hadamard every minor has absolute value at most sqrt(6)^32 < 2^42 < P.
      Hence a minor vanishes mod P iff it vanishes over Z, ranks mod P equal ranks over Q, a
      vector is in the rational row space iff it is in the row space mod P, and a set of rows
      independent mod P is independent over Q.
   3. A fingerprint.  y is an element of the null space mod P (free coordinates from a fixed
      pseudo-random sequence, pivot coordinates by back substitution).  If e_a - e_b lies in the
      row space then y_a = y_b; if e_a - e_b - e_p + e_q does then y_a - y_b = y_p - y_q.  So the
      fingerprint never misses a true instance; every candidate it proposes is then decided
      exactly by reducing the target vector against the basis (step 2), in lexicographic order.
   4. The certificate.  The basis rows are original cycle rows (a maximal independent set, found
      greedily in enumeration order).  With c_0..c_{k-1} their pivot columns, the k x k matrix
      A[j][i] = r(C_i)[c_j] is nonsingular (it is L^-1 times the unit upper triangular echelon
      block, L lower triangular with nonzero diagonal).  Fraction-free Gaussian elimination
      (Bareiss, row interchanges, every division checked exact) solves A x = D t[c] with
      D = +-det A, so x_i = D l_i are Cramer numerators; dividing by gcd(D, x) gives the scale
      s = D / g and the coefficients l_i = x_i / g (sign normalised so s > 0; zero coefficients
      dropped).  All magnitudes are minors, below 2^42 by Hadamard; every product is formed in
      128 bits and every stored value is checked below 2^62.
   5. The self-check re-verifies every condition of spec Section 2 from the certificate data:
      cycle entries in range and pairwise distinct, the four cycle edges present, coefficients
      nonzero and below 2^62, scale nonzero and below 2^62, pair distinct (and a non-edge for tu),
      edge distinct and an edge, and the identity sum_j l_j r(C_j) = s t coordinate by
      coordinate in 128-bit integers.

   Options (none is used by prune.py):
     --pair A B    certify that one given non-adjacent pair is forced (tu with the lexicographically
                   first forcing ordered edge) instead of the priority search; pass if it is not.
                   A documentation aid (enum/PRUNING.md L5 lists the six TU gadgets this way).

   RED-CONTROL BUILDS ONLY (enum/test-rhombus/mutants.py), never for production:
     -DRHOMBUS_MUTANT=1  3-edge paths u-v-w-x (xu not required) are taken as 4-cycles
     -DRHOMBUS_MUTANT=2  the distinct-vertex test is dropped: [u,v,w,v] is taken as a 4-cycle
     -DRHOMBUS_MUTANT=3  sign flip in R2: the target is s (e_a - e_b + e_p - e_q), edge [p,q]
     -DRHOMBUS_MUTANT=4  wrong pairing in Lemma R: r(C) = e_u + e_v - e_w - e_x
     -DRHOMBUS_MUTANT=5  every solved certificate is corrupted (its first coefficient plus one) before
                         the self-check, which must refuse it: every detection becomes a counted pass
   Mutants 1 to 4 share their mutated notion with the self-check, so they write their wrong
   certificates; the positive controls and an independent replay must catch them. Mutant 5 tests
   the fallback itself (SPEC amendment 2: silent passes are counted). */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef RHOMBUS_MUTANT
#define RHOMBUS_MUTANT 0
#endif

#define MAXN 32                      /* adjacency rows are uint32_t */
#define MAX_CERT_CYCLES 4096         /* spec Section 2, rule 2 */
#define P UINT64_C(0x1FFFFFFFFFFFFFFF) /* 2^61 - 1, prime */
#define BOUND62 (INT64_C(1) << 62)   /* coefficients and scale must be below this in absolute value */

__extension__ typedef __int128 i128;
__extension__ typedef unsigned __int128 u128;

typedef struct {
    int n;
    uint32_t adj[MAXN];
} graph;

enum { V_PASS = 0, V_REFUTED = 1, V_TU = 2 };
enum { F_SINGULAR = 0, F_INEXACT, F_OVERFLOW, F_EMPTY, F_SELFCHECK, F_KINDS };
static const char *const FAIL_NAMES[F_KINDS] = {"singular", "inexact", "overflow", "empty", "self_check"};

typedef struct {
    uint64_t graphs, verdict[3], cycles, max_cycles, max_rank, fp_false_positives;
    uint64_t fail[F_KINDS];
} stats_t;

static stats_t stats;

/* ---------------------------------------------------------------- arithmetic modulo P */

static inline uint64_t md_add(uint64_t a, uint64_t b) {
    uint64_t r = a + b;
    return r >= P ? r - P : r;
}

static inline uint64_t md_sub(uint64_t a, uint64_t b) {
    return a >= b ? a - b : a + P - b;
}

/* a, b < P: z < 2^122, (z mod 2^61) + (z >> 61) < 2^62 - 4 (the high part is at most 2^61 - 4
   because a, b <= 2^61 - 2), so one conditional subtraction reduces it below P. */
static inline uint64_t md_mul(uint64_t a, uint64_t b) {
    u128 z = (u128)a * b;
    uint64_t r = ((uint64_t)z & P) + (uint64_t)(z >> 61);
    return r >= P ? r - P : r;
}

static uint64_t md_pow(uint64_t a, uint64_t e) {
    uint64_t r = 1;
    while (e) {
        if (e & 1) r = md_mul(r, a);
        a = md_mul(a, a);
        e >>= 1;
    }
    return r;
}

static inline uint64_t md_inv(uint64_t a) { return md_pow(a, P - 2); }   /* a != 0 */

static inline uint64_t md_of(int64_t v) {
    if (v >= 0) return (uint64_t)v % P;
    uint64_t r = (uint64_t)(-(v + 1)) % P;   /* -(v+1) >= 0, no overflow for INT64_MIN */
    return md_sub(P - 1, r);                  /* v = -(r + 1) mod P */
}

/* ---------------------------------------------------------------- graph6 */

static int decode_graph6(const char *s, size_t len, graph *g) {
    size_t i;
    int n, need, bit = 0, u, w;
    for (i = 0; i < len; i++)
        if ((unsigned char)s[i] < 63 || (unsigned char)s[i] > 126) return 0;
    if (len < 1) return 0;
    n = (unsigned char)s[0] - 63;
    if (n > MAXN) return 0;                  /* also rejects the long form (first byte 126) */
    need = (n * (n - 1) / 2 + 5) / 6;
    if (len != (size_t)(1 + need)) return 0;
    memset(g, 0, sizeof(*g));
    g->n = n;
    for (w = 1; w < n; w++) {
        for (u = 0; u < w; u++, bit++) {
            unsigned value = (unsigned char)s[1 + bit / 6] - 63u;
            if (value & (1u << (5 - bit % 6))) {
                g->adj[u] |= UINT32_C(1) << w;
                g->adj[w] |= UINT32_C(1) << u;
            }
        }
    }
    if (bit % 6) {                           /* padding bits of the last byte must be zero */
        unsigned last = (unsigned char)s[len - 1] - 63u;
        if (last & ((1u << (6 - bit % 6)) - 1u)) return 0;
    }
    return 1;
}

static inline int is_edge(const graph *g, int a, int b) {
    return (g->adj[a] >> b) & 1u;
}

static inline uint32_t above(int v) {        /* bits of the vertices > v */
    return (uint32_t)~((UINT64_C(2) << v) - 1u);
}

/* ---------------------------------------------------------------- the rule's two notions */

/* r(C) for C = [c0, c1, c2, c3]: e_c0 - e_c1 + e_c2 - e_c3 (added into coef). */
static void add_cycle_row(const int c[4], int64_t coef[MAXN], int64_t times) {
#if RHOMBUS_MUTANT == 4
    coef[c[0]] += times; coef[c[1]] += times; coef[c[2]] -= times; coef[c[3]] -= times;
#else
    coef[c[0]] += times; coef[c[1]] -= times; coef[c[2]] += times; coef[c[3]] -= times;
#endif
}

/* spec Section 2, rule 2 for one entry: in range, pairwise distinct, uv vw wx xu edges */
static int cycle_ok(const graph *g, const int c[4]) {
    int i;
    for (i = 0; i < 4; i++)
        if (c[i] < 0 || c[i] >= g->n) return 0;
#if RHOMBUS_MUTANT != 2
    if (c[0] == c[1] || c[0] == c[2] || c[0] == c[3] || c[1] == c[2] || c[1] == c[3] || c[2] == c[3])
        return 0;
#endif
    if (!is_edge(g, c[0], c[1]) || !is_edge(g, c[1], c[2]) || !is_edge(g, c[2], c[3])) return 0;
#if RHOMBUS_MUTANT != 1
    if (!is_edge(g, c[3], c[0])) return 0;
#endif
    return 1;
}

/* the target vector t: e_a - e_b (refuted), e_a - e_b - e_p + e_q (tu) */
static void target_vector(int verdict, int a, int b, int p, int q, int64_t t[MAXN]) {
    memset(t, 0, sizeof(int64_t) * MAXN);
    t[a] += 1;
    t[b] -= 1;
    if (verdict == V_TU) {
#if RHOMBUS_MUTANT == 3
        t[p] += 1; t[q] -= 1;
#else
        t[p] -= 1; t[q] += 1;
#endif
    }
}

/* ---------------------------------------------------------------- echelon basis mod P */

typedef struct {
    int n, k;
    int pivot_of_col[MAXN];      /* basis row with its pivot in this column, or -1 */
    int pivcol[MAXN];            /* pivot column of basis row i */
    int cyc[MAXN][4];            /* the ORIGINAL cycle of basis row i */
    uint64_t row[MAXN][MAXN];    /* echelon row i: zero left of pivcol[i], 1 at pivcol[i] */
} basis;

static void basis_init(basis *B, int n) {
    int c;
    B->n = n;
    B->k = 0;
    for (c = 0; c < n; c++) B->pivot_of_col[c] = -1;
}

/* Reduce v (length n, mod P) against the basis in increasing column order.  Returns the first
   column where v stays nonzero and no pivot exists (v is then outside the row space), or -1 if v
   reduces to zero (v is in the row space).  v is modified. */
static int basis_reduce(const basis *B, uint64_t v[MAXN]) {
    int n = B->n, c, j;
    for (c = 0; c < n; c++) {
        uint64_t f = v[c];
        if (!f) continue;
        int i = B->pivot_of_col[c];
        if (i < 0) return c;
        const uint64_t *r = B->row[i];
        for (j = c; j < n; j++)
            if (r[j]) v[j] = md_sub(v[j], md_mul(f, r[j]));
    }
    return -1;
}

/* Insert the cycle's row; returns 1 if it raised the rank. */
static int basis_insert(basis *B, const int c[4]) {
    int64_t coef[MAXN] = {0};
    uint64_t v[MAXN];
    int n = B->n, j, lead;
    add_cycle_row(c, coef, 1);
    for (j = 0; j < n; j++) v[j] = md_of(coef[j]);
    lead = basis_reduce(B, v);
    if (lead < 0) return 0;
    uint64_t inv = md_inv(v[lead]);
    int k = B->k;
    for (j = 0; j < lead; j++) B->row[k][j] = 0;
    for (j = lead; j < n; j++) B->row[k][j] = md_mul(v[j], inv);
    B->pivcol[k] = lead;
    B->pivot_of_col[lead] = k;
    memcpy(B->cyc[k], c, sizeof(B->cyc[k]));
    B->k = k + 1;
    return 1;
}

/* exact membership of an integer vector in the (rational = mod P) row space */
static int in_row_space(const basis *B, const int64_t t[MAXN]) {
    uint64_t v[MAXN];
    int j;
    for (j = 0; j < B->n; j++) v[j] = md_of(t[j]);
    return basis_reduce(B, v) < 0;
}

/* ---------------------------------------------------------------- cycle enumeration */

/* Every 4-cycle once (Method 1), inserted into B; stops early at rank n - 1 (then the row space
   is the whole sum-zero hyperplane and nothing more can change).  Returns the number listed. */
static uint64_t enumerate_cycles(const graph *g, basis *B) {
    int n = g->n, u, w;
    uint64_t count = 0;
    for (u = 0; u < n; u++) {
        for (w = u + 1; w < n; w++) {
            uint32_t common = g->adj[u] & g->adj[w] & above(u);
            uint32_t vs = common;
            while (vs) {
                int v = __builtin_ctz(vs);
                vs &= vs - 1;
#if RHOMBUS_MUTANT == 1
                uint32_t xs = g->adj[w] & above(v) & ~(UINT32_C(1) << u);   /* xu not required */
#else
                uint32_t xs = common & above(v);
#endif
#if RHOMBUS_MUTANT == 2
                {   /* degenerate "cycle" [u, v, w, v] */
                    int c[4] = {u, v, w, v};
                    count++;
                    basis_insert(B, c);
                    if (B->k >= n - 1) return count;
                }
#endif
                while (xs) {
                    int x = __builtin_ctz(xs);
                    int c[4] = {u, v, w, x};
                    xs &= xs - 1;
                    count++;
                    basis_insert(B, c);
                    if (B->k >= n - 1) return count;
                }
            }
        }
    }
    return count;
}

/* ---------------------------------------------------------------- fingerprint */

static uint64_t splitmix64(uint64_t *state) {
    uint64_t z = (*state += UINT64_C(0x9E3779B97F4A7C15));
    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

/* y in the null space mod P: free coordinates fixed pseudo-random, pivot coordinates solved from
   the echelon rows, highest pivot column first (row i involves only columns >= pivcol[i]). */
static void null_vector(const basis *B, uint64_t y[MAXN]) {
    int n = B->n, c, j;
    uint64_t state = UINT64_C(0x5EED2026092601);
    for (c = 0; c < n; c++) {
        uint64_t r = splitmix64(&state) % P;
        y[c] = B->pivot_of_col[c] < 0 ? (r ? r : 1) : 0;
    }
    for (c = n - 1; c >= 0; c--) {
        int i = B->pivot_of_col[c];
        if (i < 0) continue;
        uint64_t acc = 0;
        for (j = c + 1; j < n; j++)
            if (B->row[i][j]) acc = md_add(acc, md_mul(B->row[i][j], y[j]));
        y[c] = md_sub(0, acc);
    }
}

/* ---------------------------------------------------------------- ordered-edge hash */

#define HT_BITS 11
#define HT_SIZE (1 << HT_BITS)
typedef struct {
    uint32_t stamp[HT_SIZE];
    uint64_t key[HT_SIZE];
    int head[HT_SIZE], tail[HT_SIZE];
    int ep[MAXN * MAXN], eq[MAXN * MAXN], next[MAXN * MAXN];
    uint32_t now;
} edge_table;

static edge_table table;

static inline unsigned ht_slot(uint64_t key) {
    return (unsigned)((key * UINT64_C(0x9E3779B97F4A7C15)) >> (64 - HT_BITS));
}

static void table_build(const graph *g, const uint64_t y[MAXN]) {
    int p, count = 0;
    if (++table.now == 0) {                  /* stamp wrapped: clear once */
        memset(table.stamp, 0, sizeof(table.stamp));
        table.now = 1;
    }
    for (p = 0; p < g->n; p++) {             /* ordered edges (p, q) in lexicographic order */
        uint32_t qs = g->adj[p];
        while (qs) {
            int q = __builtin_ctz(qs);
            qs &= qs - 1;
#if RHOMBUS_MUTANT == 3
            uint64_t key = md_sub(y[q], y[p]);
#else
            uint64_t key = md_sub(y[p], y[q]);
#endif
            unsigned h = ht_slot(key);
            while (table.stamp[h] == table.now && table.key[h] != key) h = (h + 1) & (HT_SIZE - 1);
            table.ep[count] = p;
            table.eq[count] = q;
            table.next[count] = -1;
            if (table.stamp[h] != table.now) {
                table.stamp[h] = table.now;
                table.key[h] = key;
                table.head[h] = table.tail[h] = count;
            } else {
                table.next[table.tail[h]] = count;
                table.tail[h] = count;
            }
            count++;
        }
    }
}

static int table_first(uint64_t key) {       /* first ordered edge with this key, or -1 */
    unsigned h = ht_slot(key);
    while (table.stamp[h] == table.now) {
        if (table.key[h] == key) return table.head[h];
        h = (h + 1) & (HT_SIZE - 1);
    }
    return -1;
}

/* ---------------------------------------------------------------- exact certificate */

typedef struct {
    int verdict, a, b, p, q, count;
    int cyc[MAXN][4];
    int64_t coef[MAXN];
    int64_t scale;
} certificate;

static int64_t gcd64(int64_t x, int64_t y) {
    if (x < 0) x = -x;
    if (y < 0) y = -y;
    while (y) {
        int64_t r = x % y;
        x = y;
        y = r;
    }
    return x;
}

static inline int fits(i128 v) { return v > -(i128)BOUND62 && v < (i128)BOUND62; }

/* Solve sum_i l_i r(C_i) = s t over the basis rows exactly (Method 4).  Returns 1 on success,
   else 0 with *why set. */
static int exact_solve(const basis *B, const int64_t t[MAXN], certificate *cert, int *why) {
    int k = B->k, i, j, c, r;
    int64_t A[MAXN][MAXN + 1];
    int64_t rows[MAXN][MAXN];
    int64_t x[MAXN];
    int64_t prev = 1, D, g;
    if (k == 0) { *why = F_EMPTY; return 0; }
    for (i = 0; i < k; i++) {
        memset(rows[i], 0, sizeof(rows[i]));
        add_cycle_row(B->cyc[i], rows[i], 1);
    }
    for (j = 0; j < k; j++) {                /* equation j: pivot column c_j */
        c = B->pivcol[j];
        for (i = 0; i < k; i++) A[j][i] = rows[i][c];
        A[j][k] = t[c];
    }
    for (i = 0; i < k; i++) {                /* Bareiss with row interchanges */
        for (r = i; r < k && A[r][i] == 0; r++) {}
        if (r == k) { *why = F_SINGULAR; return 0; }
        if (r != i)
            for (c = 0; c <= k; c++) { int64_t tmp = A[i][c]; A[i][c] = A[r][c]; A[r][c] = tmp; }
        for (r = i + 1; r < k; r++) {
            for (c = i + 1; c <= k; c++) {
                i128 num = (i128)A[i][i] * A[r][c] - (i128)A[r][i] * A[i][c];
                if (num % prev != 0) { *why = F_INEXACT; return 0; }
                num /= prev;
                if (!fits(num)) { *why = F_OVERFLOW; return 0; }
                A[r][c] = (int64_t)num;
            }
            A[r][i] = 0;
        }
        prev = A[i][i];
    }
    D = prev;                                /* A[k-1][k-1] = +- det A, nonzero */
    for (i = k - 1; i >= 0; i--) {           /* x_i = D l_i, Cramer numerators */
        i128 acc = (i128)D * A[i][k];
        for (j = i + 1; j < k; j++) acc -= (i128)A[i][j] * x[j];
        if (acc % A[i][i] != 0) { *why = F_INEXACT; return 0; }
        acc /= A[i][i];
        if (!fits(acc)) { *why = F_OVERFLOW; return 0; }
        x[i] = (int64_t)acc;
    }
    g = D;
    for (i = 0; i < k; i++) g = gcd64(g, x[i]);
    if (g == 0) { *why = F_SINGULAR; return 0; }
    if (D < 0) g = -g;                       /* scale positive */
    cert->scale = D / g;
    cert->count = 0;
    for (i = 0; i < k; i++) {
        int64_t l = x[i] / g;
        if (l == 0) continue;
        memcpy(cert->cyc[cert->count], B->cyc[i], sizeof(cert->cyc[0]));
        cert->coef[cert->count] = l;
        cert->count++;
    }
    if (cert->count == 0) { *why = F_EMPTY; return 0; }
    return 1;
}

/* spec Section 2, every rule, from the certificate alone */
static int self_check(const graph *g, const certificate *cert) {
    int n = g->n, j, i;
    i128 sum[MAXN];
    int64_t t[MAXN];
    if (cert->count < 1 || cert->count > MAX_CERT_CYCLES) return 0;
    if (cert->scale == 0 || !fits(cert->scale)) return 0;
    if (cert->a < 0 || cert->a >= n || cert->b < 0 || cert->b >= n || cert->a == cert->b) return 0;
    if (cert->verdict == V_TU) {
        if (is_edge(g, cert->a, cert->b)) return 0;
        if (cert->p < 0 || cert->p >= n || cert->q < 0 || cert->q >= n || cert->p == cert->q) return 0;
        if (!is_edge(g, cert->p, cert->q)) return 0;
    } else if (cert->verdict != V_REFUTED) {
        return 0;
    }
    for (i = 0; i < n; i++) sum[i] = 0;
    for (j = 0; j < cert->count; j++) {
        int64_t row[MAXN] = {0};
        if (!cycle_ok(g, cert->cyc[j])) return 0;
        if (cert->coef[j] == 0 || !fits(cert->coef[j])) return 0;
        add_cycle_row(cert->cyc[j], row, 1);
        for (i = 0; i < n; i++) sum[i] += (i128)row[i] * cert->coef[j];
    }
    target_vector(cert->verdict, cert->a, cert->b, cert->p, cert->q, t);
    for (i = 0; i < n; i++)
        if (sum[i] != (i128)cert->scale * t[i]) return 0;
    return 1;
}

/* ---------------------------------------------------------------- output */

static char out[1 << 16];
static size_t out_len;

static void put_str(const char *s) {
    size_t l = strlen(s);
    memcpy(out + out_len, s, l);
    out_len += l;
}

static void put_int(int64_t v) {
    char buf[24];
    int len = 0;
    uint64_t u;
    if (v < 0) { out[out_len++] = '-'; u = (uint64_t)(-(v + 1)) + 1u; } else u = (uint64_t)v;
    do { buf[len++] = (char)('0' + u % 10); u /= 10; } while (u);
    while (len) out[out_len++] = buf[--len];
}

static void flush_out(void) {
    if (out_len && fwrite(out, 1, out_len, stdout) != out_len) {
        fprintf(stderr, "udrhombus: write error\n");
        exit(3);
    }
    out_len = 0;
}

static void write_pass(void) { put_str("{\"verdict\":\"pass\"}\n"); }

static void write_certificate(const certificate *cert) {
    int j, i;
    put_str(cert->verdict == V_TU ? "{\"verdict\":\"tu\"" : "{\"verdict\":\"refuted\"");
    put_str(",\"witness\":{\"rhombus\":{\"cycles\":[");
    for (j = 0; j < cert->count; j++) {
        put_str(j ? ",[" : "[");
        for (i = 0; i < 4; i++) {
            if (i) put_str(",");
            put_int(cert->cyc[j][i]);
        }
        put_str("]");
    }
    put_str("],\"coefficients\":[");
    for (j = 0; j < cert->count; j++) {
        if (j) put_str(",");
        put_int(cert->coef[j]);
    }
    put_str("],\"scale\":");
    put_int(cert->scale);
    put_str(",\"pair\":[");
    put_int(cert->a); put_str(","); put_int(cert->b);
    put_str("]");
    if (cert->verdict == V_TU) {
        put_str(",\"edge\":[");
        put_int(cert->p); put_str(","); put_int(cert->q);
        put_str("]");
    }
    put_str("}}}\n");
}

/* ---------------------------------------------------------------- one graph */

static basis B;

/* Certify (verdict, a, b, p, q) or fall back to pass, counting the reason. */
static void emit(const graph *g, int verdict, int a, int b, int p, int q) {
    certificate cert;
    int64_t t[MAXN];
    int why = F_SELFCHECK;
    cert.verdict = verdict; cert.a = a; cert.b = b; cert.p = p; cert.q = q;
    target_vector(verdict, a, b, p, q, t);
#if RHOMBUS_MUTANT == 5
    if (exact_solve(&B, t, &cert, &why) && (cert.coef[0] += 1, 1) && self_check(g, &cert)) {
#else
    if (exact_solve(&B, t, &cert, &why) && self_check(g, &cert)) {
#endif
        write_certificate(&cert);
        stats.verdict[verdict]++;
        return;
    }
    stats.fail[why]++;
    stats.verdict[V_PASS]++;
    write_pass();
}

/* the lexicographically first forcing ordered edge of the non-adjacent pair (a, b), or -1 */
static int forcing_edge(const uint64_t y[MAXN], int a, int b) {
    int e;
    for (e = table_first(md_sub(y[a], y[b])); e >= 0; e = table.next[e]) {
        int64_t t[MAXN];
        target_vector(V_TU, a, b, table.ep[e], table.eq[e], t);
        if (in_row_space(&B, t)) return e;
        stats.fp_false_positives++;
    }
    return -1;
}

static void process(const graph *g, int pair_a, int pair_b) {
    int n = g->n, a, b;
    uint64_t y[MAXN];
    uint64_t count;
    basis_init(&B, n);
    count = enumerate_cycles(g, &B);
    stats.graphs++;
    stats.cycles += count;
    if (count > stats.max_cycles) stats.max_cycles = count;
    if ((uint64_t)B.k > stats.max_rank) stats.max_rank = (uint64_t)B.k;
    if (B.k == 0) { stats.verdict[V_PASS]++; write_pass(); return; }
    null_vector(&B, y);
    table_build(g, y);
    if (pair_a >= 0) {                       /* --pair: one given pair, tu or pass */
        int e = (pair_a < n && pair_b < n && pair_a != pair_b && !is_edge(g, pair_a, pair_b))
                    ? forcing_edge(y, pair_a, pair_b) : -1;
        if (e >= 0) emit(g, V_TU, pair_a, pair_b, table.ep[e], table.eq[e]);
        else { stats.verdict[V_PASS]++; write_pass(); }
        return;
    }
    for (a = 0; a < n; a++) {                /* R1: the first colliding pair */
        for (b = a + 1; b < n; b++) {
            if (y[a] != y[b]) continue;
            int64_t t[MAXN];
            target_vector(V_REFUTED, a, b, 0, 0, t);
            if (in_row_space(&B, t)) { emit(g, V_REFUTED, a, b, 0, 0); return; }
            stats.fp_false_positives++;
        }
    }
    for (a = 0; a < n; a++) {                /* R2: the first forced non-adjacent pair */
        for (b = a + 1; b < n; b++) {
            if (is_edge(g, a, b)) continue;
            int e = forcing_edge(y, a, b);
            if (e >= 0) { emit(g, V_TU, a, b, table.ep[e], table.eq[e]); return; }
        }
    }
    stats.verdict[V_PASS]++;
    write_pass();
}

static void usage(const char *name) {
    fprintf(stderr, "usage: %s [--pair A B] < graph6\n"
                    "  one JSON line per input line: pass, refuted or tu with a rhombus certificate\n"
                    "  (research/unit-distance-23/RHOMBUS-SPEC.md); statistics on stderr at the end\n", name);
}

int main(int argc, char **argv) {
    char line[512];
    int pair_a = -1, pair_b = -1, i, f;
    uint64_t lineno = 0, failures = 0;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--pair") == 0 && i + 2 < argc) {
            char *end1, *end2;
            long x = strtol(argv[i + 1], &end1, 10), z = strtol(argv[i + 2], &end2, 10);
            if (*end1 || *end2 || x < 0 || z < 0 || x >= MAXN || z >= MAXN) { usage(argv[0]); return 2; }
            pair_a = (int)x; pair_b = (int)z;
            i += 2;
        } else {
            usage(argv[0]);
            return 2;
        }
    }
    while (fgets(line, sizeof(line), stdin) != NULL) {
        size_t len = strlen(line);
        graph g;
        lineno++;
        if (len && line[len - 1] == '\n') line[--len] = '\0';
        else if (!feof(stdin)) {
            fprintf(stderr, "udrhombus: line %" PRIu64 " is too long\n", lineno);
            return 2;
        }
        if (len && line[len - 1] == '\r') line[--len] = '\0';
        if (!decode_graph6(line, len, &g)) {
            fprintf(stderr, "udrhombus: line %" PRIu64 ": invalid graph6 record (at most %d vertices)\n",
                    lineno, MAXN);
            return 2;
        }
        process(&g, pair_a, pair_b);
        if (out_len > sizeof(out) - 4096) flush_out();
    }
    if (ferror(stdin)) {
        fprintf(stderr, "udrhombus: read error\n");
        return 2;
    }
    flush_out();
    if (fflush(stdout) != 0 || ferror(stdout)) {
        fprintf(stderr, "udrhombus: write error\n");
        return 3;
    }
    for (f = 0; f < F_KINDS; f++) failures += stats.fail[f];
    fprintf(stderr, "{\"udrhombus_stats\":{\"graphs\":%" PRIu64 ",\"pass\":%" PRIu64 ",\"refuted\":%" PRIu64
                    ",\"tu\":%" PRIu64 ",\"certificate_failures\":%" PRIu64,
            stats.graphs, stats.verdict[V_PASS], stats.verdict[V_REFUTED], stats.verdict[V_TU], failures);
    for (f = 0; f < F_KINDS; f++) fprintf(stderr, ",\"failure_%s\":%" PRIu64, FAIL_NAMES[f], stats.fail[f]);
    fprintf(stderr, ",\"fingerprint_false_positives\":%" PRIu64 ",\"cycles\":%" PRIu64
                    ",\"max_cycles\":%" PRIu64 ",\"max_rank\":%" PRIu64 ",\"mutant\":%d}}\n",
            stats.fp_false_positives, stats.cycles, stats.max_cycles, stats.max_rank, RHOMBUS_MUTANT);
    return 0;
}
