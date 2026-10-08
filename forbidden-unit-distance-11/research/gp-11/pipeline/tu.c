/* The filter only proposes witnesses; the frozen checker verifies every step. */
#include "udfilter.h"
static udf_database database;
int init(const char *forbidden, const char *gadgets) {
    char error[256];
    return udf_database_load_set(&database, forbidden, gadgets, 398, error, sizeof error);
}
int closure(const char *code, int *output, int capacity) {
    udf_graph graph;
    udf_witness witness;
    if (!udf_graph6_decode(code, &graph) || graph.n != 11) return -1;
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
        if (++steps > 55) return -5;
    }
}
