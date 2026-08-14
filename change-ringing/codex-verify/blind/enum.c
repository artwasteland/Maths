#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { NPERM = 120, MAXL = 13, MAXDEG = 7 };

static unsigned char perm[NPERM][5];
static unsigned char nbr[NPERM][MAXDEG];
static unsigned char deg[NPERM];
static uint64_t path_count[MAXL + 1];
static uint64_t cyclic_including_close[MAXL + 1];
static uint64_t cyclic_excluding_close[MAXL + 1];

static int rank_perm(const unsigned char p[5]) {
    int rank = 0;
    for (int i = 0; i < 5; ++i) {
        int smaller = 0;
        for (int j = i + 1; j < 5; ++j)
            smaller += p[j] < p[i];
        rank = rank * (5 - i) + smaller;
    }
    return rank;
}

static int adjacent_to_start(int v) {
    for (int i = 0; i < deg[v]; ++i)
        if (nbr[v][i] == 0) return 1;
    return 0;
}

static void dfs(int v, int length, uint64_t lo, uint64_t hi) {
    /* Every recursive state is a sequence of distinct permutations. */
    if (length >= 2) ++path_count[length];

    /* Add the final repeated 12345, but do not include it in this length. */
    if (length == 1 || adjacent_to_start(v))
        ++cyclic_excluding_close[length];

    /* Here the repeated closing row is included, so it adds one to length. */
    if (length == 1)
        ++cyclic_including_close[1]; /* the one-row sequence (12345) */
    if (length < MAXL && (length == 1 || adjacent_to_start(v)))
        ++cyclic_including_close[length + 1];

    if (length == MAXL) return;
    for (int i = 0; i < deg[v]; ++i) {
        int w = nbr[v][i];
        if (w < 64) {
            uint64_t bit = UINT64_C(1) << w;
            if (!(lo & bit)) dfs(w, length + 1, lo | bit, hi);
        } else {
            uint64_t bit = UINT64_C(1) << (w - 64);
            if (!(hi & bit)) dfs(w, length + 1, lo, hi | bit);
        }
    }
}

static void make_permutations(void) {
    /* Lexicographic order makes 12345 vertex zero. */
    for (int r = 0; r < NPERM; ++r) {
        int x = r;
        unsigned char available[5] = {1, 2, 3, 4, 5};
        int digits[5];
        for (int i = 4; i >= 0; --i) {
            digits[i] = x % (5 - i);
            x /= 5 - i;
        }
        int n = 5;
        for (int i = 0; i < 5; ++i) {
            int k = digits[i];
            perm[r][i] = available[k];
            memmove(&available[k], &available[k + 1], (size_t)(n-k-1));
            --n;
        }
    }
}

static void make_graph(void) {
    /* A legal non-identity move is a nonempty matching of the four gaps:
       swap any set of pairwise non-adjacent neighboring positions. */
    for (int v = 0; v < NPERM; ++v) {
        for (int mask = 1; mask < 16; ++mask) {
            if (mask & (mask << 1)) continue;
            unsigned char q[5];
            memcpy(q, perm[v], sizeof q);
            for (int i = 0; i < 4; ++i)
                if (mask & (1 << i)) {
                    unsigned char t = q[i]; q[i] = q[i+1]; q[i+1] = t;
                }
            nbr[v][deg[v]++] = (unsigned char)rank_perm(q);
        }
    }
}

int main(void) {
    make_permutations();
    make_graph();
    dfs(0, 1, UINT64_C(1), 0);
    puts("L path_count cyclic_count_including_close cyclic_count_excluding_close");
    for (int l = 1; l <= MAXL; ++l)
        printf("%d %llu %llu %llu\n", l,
               (unsigned long long)path_count[l],
               (unsigned long long)cyclic_including_close[l],
               (unsigned long long)cyclic_excluding_close[l]);
    return 0;
}
