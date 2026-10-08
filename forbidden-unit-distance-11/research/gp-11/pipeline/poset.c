/* Each map sends canonical child labels into parent labels. */
#include <nauty/naututil.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define N 448708
#define HS (1 << 20)
static char codes[N][12];
static uint32_t table[HS];

static unsigned code_hash(const char *code) {
    uint64_t key = 0;
    for (int j = 1; j < 11; j++) key = (key << 6) | (code[j] - 63);
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
        if (n >= N || strlen(line) != 12 || line[0] != 'J' || line[11] != '\n') return 4;
        line[11] = 0;
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
    graph g[11], h[11], canonical[11];
    int lab[11], partition[11], orbits[11], degree[11];
    static DEFAULTOPTIONS_GRAPH(options);
    options.getcanon = TRUE;
    statsblk stats;
    nauty_check(WORDSIZE, 1, 11, NAUTYVERSIONID);
    uint64_t count = 0;
    for (int parent = 0; parent < n; parent++) {
        EMPTYGRAPH(g, 1, 11);
        memset(degree, 0, sizeof degree);
        int bit_index = 0;
        for (int v = 1; v < 11; v++) for (int u = 0; u < v; u++, bit_index++) {
            if ((codes[parent][1+bit_index/6]-63) & (1 << (5-bit_index%6))) {
                ADDONEEDGE(g, u, v, 1);
                degree[u]++;
                degree[v]++;
            }
        }
        int seen[55], used = 0;
        for (int v = 1; v < 11; v++) for (int u = 0; u < v; u++) {
            if (!ISELEMENT(&g[u], v) || degree[u] == 2 || degree[v] == 2) continue;
            memcpy(h, g, sizeof h);
            DELELEMENT(&h[u], v);
            DELELEMENT(&h[v], u);
            densenauty(h, lab, partition, orbits, &options, &stats, 1, 11, canonical);
            char code[12];
            code[0] = 'J';
            memset(code+1, 63, 10);
            code[11] = 0;
            bit_index = 0;
            for (int y = 1; y < 11; y++) for (int x = 0; x < y; x++, bit_index++) {
                if (ISELEMENT(&canonical[x], y)) code[1+bit_index/6] += 1 << (5-bit_index%6);
            }
            int child = find(code), duplicate = 0;
            if (child < 0) continue;
            for (int j = 0; j < used; j++) if (seen[j] == child) duplicate = 1;
            if (duplicate) continue;
            seen[used++] = child;
            /* Explicit little endian avoids native structure padding and endian dependence. */
            unsigned char row[19];
            for (int j = 0; j < 4; j++) {
                row[j] = ((uint32_t)parent >> (8*j)) & 255;
                row[4+j] = ((uint32_t)child >> (8*j)) & 255;
            }
            for (int j = 0; j < 11; j++) row[8+j] = lab[j];
            if (fwrite(row, 19, 1, output) != 1) return 8;
            count++;
        }
    }
    if (fclose(output)) return 9;
    fprintf(stderr, "relations=%llu\n", (unsigned long long)count);
    return 0;
}
