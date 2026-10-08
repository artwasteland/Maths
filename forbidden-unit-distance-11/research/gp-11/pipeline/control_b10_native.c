/* Order-ten sibling of poset.c and tu.c. No B11 files or F10 are consumed. */
#ifdef CONTROL_TU
#include "udfilter.h"
static udf_database database;
int init(const char *forbidden, const char *gadgets) {
    char error[256];
    return udf_database_load_set(&database, forbidden, gadgets, 74, error, sizeof error);
}
int closure(const char *code, int *output, int capacity) {
    udf_graph graph;
    udf_witness witness;
    if (!udf_graph6_decode(code, &graph) || graph.n != 10) return -1;
    int steps = 0, offset = 1;
    for (;;) {
        int result = udf_find(&database, &graph, &witness);
        if (offset + 5 + UDF_MAX_PATTERN_VERTICES >= capacity) return -2;
        output[0] = steps;
        output[offset] = result;
        if (!result) return offset + 1;
        if (result != 1 && result != 2) return -3;
        int n = witness.pattern_vertices;
        output[offset+1] = witness.index;
        output[offset+2] = n;
        for (int i = 0; i < n; i++) output[offset+3+i] = witness.map[i];
        if (result == 1) return offset + 3 + n;
        int a = witness.map[witness.pair_a], b = witness.map[witness.pair_b];
        if (graph.adj[a] & (1u << b)) return -4;
        output[offset+3+n] = a;
        output[offset+4+n] = b;
        graph.adj[a] |= 1u << b;
        graph.adj[b] |= 1u << a;
        offset += 5 + n;
        if (++steps > 45) return -5;
    }
}
#else
#include <nauty/naututil.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define N 33162
#define HS (1 << 17)
static char codes[N][10];
static uint32_t table[HS];
static unsigned code_hash(const char *code) {
    uint64_t key = 0;
    for (int j = 1; j < 9; j++) key = (key << 6) | (code[j] - 63);
    key ^= key >> 30;
    key *= 0xbf58476d1ce4e5b9ULL;
    key ^= key >> 27;
    return key & (HS - 1);
}
static int find(const char *code) {
    unsigned slot = code_hash(code);
    while (table[slot] && strcmp(code, codes[table[slot] - 1])) slot = (slot + 1) & (HS - 1);
    return table[slot] ? (int)table[slot] - 1 : -1;
}
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    FILE *input = fopen(argv[1], "r");
    if (!input) return 3;
    char line[256];
    int n = 0;
    while (fgets(line, sizeof line, input)) {
        if (n >= N || strlen(line) != 10 || line[0] != 'I' || line[9] != '\n') return 4;
        line[9] = 0;
        if (n && strcmp(codes[n-1], line) >= 0) return 5;
        strcpy(codes[n], line);
        unsigned slot = code_hash(line);
        while (table[slot]) slot = (slot + 1) & (HS - 1);
        table[slot] = ++n;
    }
    fclose(input);
    if (n != N) return 6;
    FILE *output = fopen(argv[2], "wb");
    if (!output) return 7;
    graph g[10], h[10], canonical[10];
    int lab[10], partition[10], orbits[10], degree[10];
    static DEFAULTOPTIONS_GRAPH(options);
    options.getcanon = TRUE;
    statsblk stats;
    nauty_check(WORDSIZE, 1, 10, NAUTYVERSIONID);
    uint64_t count = 0;
    for (int parent = 0; parent < n; parent++) {
        EMPTYGRAPH(g, 1, 10);
        memset(degree, 0, sizeof degree);
        int bit_index = 0;
        for (int v = 1; v < 10; v++) for (int u = 0; u < v; u++, bit_index++) {
            if ((codes[parent][1+bit_index/6]-63) & (1 << (5-bit_index%6))) {
                ADDONEEDGE(g, u, v, 1);
                degree[u]++; degree[v]++;
            }
        }
        int seen[45], used = 0;
        for (int v = 1; v < 10; v++) for (int u = 0; u < v; u++) {
            if (!ISELEMENT(&g[u], v) || degree[u] == 2 || degree[v] == 2) continue;
            memcpy(h, g, sizeof h);
            DELELEMENT(&h[u], v); DELELEMENT(&h[v], u);
            densenauty(h, lab, partition, orbits, &options, &stats, 1, 10, canonical);
            char code[10];
            code[0] = 'I'; memset(code+1, 63, 8); code[9] = 0;
            bit_index = 0;
            for (int y = 1; y < 10; y++) for (int x = 0; x < y; x++, bit_index++)
                if (ISELEMENT(&canonical[x], y)) code[1+bit_index/6] += 1 << (5-bit_index%6);
            int child = find(code), duplicate = 0;
            if (child < 0) continue;
            for (int j = 0; j < used; j++) if (seen[j] == child) duplicate = 1;
            if (duplicate) continue;
            seen[used++] = child;
            unsigned char row[18];
            for (int j = 0; j < 4; j++) {
                row[j] = ((uint32_t)parent >> (8*j)) & 255;
                row[4+j] = ((uint32_t)child >> (8*j)) & 255;
            }
            for (int j = 0; j < 10; j++) row[8+j] = lab[j];
            if (fwrite(row, 18, 1, output) != 1) return 8;
            count++;
        }
    }
    if (fclose(output)) return 9;
    fprintf(stderr, "B10 relations=%llu\n", (unsigned long long)count);
    return 0;
}
#endif
