/* ancestry.c: the canonical-parent chain of a graph6 record, by udenum's rule.
   udenum.c accepts a child iff the new vertex lies in the automorphism orbit of the FIRST
   minimum-degree vertex in nauty's canonical order (densenauty, defaultptn, getcanon), so the
   canonical parent of G is G minus that vertex, written in canonical form. This program repeats
   that step down to a given order and prints "n m g6" per level. Same libnauty as udenum.
   Usage: ancestry <stop_n> < graphs.g6 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nauty.h"
#include "gtools.h"
#define MAXV 32
static void canon(graph *g, int n, graph *canong, int *lab, int *orbits) {
    int ptn[MAXV]; statsblk stats; DEFAULTOPTIONS_GRAPH(options);
    options.getcanon = TRUE; options.defaultptn = TRUE;
    densenauty(g, lab, ptn, orbits, &options, &stats, 1, n, canong);
}
int main(int argc, char **argv) {
    int stop = argc > 1 ? atoi(argv[1]) : 13;
    char line[4096];
    while (fgets(line, sizeof line, stdin)) {
        char *nl = strchr(line, '\n'); if (nl) *nl = 0;
        if (!line[0] || line[0] == '>') continue;
        int n = graphsize(line);
        graph g[MAXV], canong[MAXV]; int lab[MAXV], orbits[MAXV];
        stringtograph(line, g, 1);
        printf("START %s\n", line);
        while (n > stop) {
            int deg[MAXV], delta = 1 << 30, m = 0;
            for (int i = 0; i < n; ++i) { deg[i] = POPCOUNT(g[i]); m += deg[i]; if (deg[i] < delta) delta = deg[i]; }
            m /= 2;
            canon(g, n, canong, lab, orbits);
            int v = -1;
            for (int i = 0; i < n; ++i) if (deg[lab[i]] == delta) { v = lab[i]; break; }
            if (v < 0) { fprintf(stderr, "no min vertex\n"); return 1; }
            /* delete v: relabel remaining vertices 0..n-2 in order */
            graph h[MAXV]; int map[MAXV], k = 0;
            for (int i = 0; i < n; ++i) if (i != v) map[i] = k++; else map[i] = -1;
            EMPTYGRAPH(h, 1, n - 1);
            for (int i = 0; i < n; ++i) if (i != v) for (int j = i + 1; j < n; ++j) if (j != v && ISELEMENT(&g[i], j)) { ADDONEEDGE(h, map[i], map[j], 1); }
            n -= 1;
            canon(h, n, canong, lab, orbits);
            memcpy(g, canong, sizeof(graph) * n);
            int m2 = 0; for (int i = 0; i < n; ++i) m2 += POPCOUNT(g[i]); m2 /= 2;
            printf("  %d %d %s\n", n, m2, ntog6(g, 1, n));
        }
    }
    return 0;
}
