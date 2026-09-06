#ifndef UDFILTER_H
#define UDFILTER_H

#include <stdint.h>

#define UDF_MAX_VERTICES 22
#define UDF_MAX_PATTERN_VERTICES 15
#define UDF_MAX_PATTERN_EDGES 105
#define UDF_MAX_PATTERNS 128

typedef struct {
    int n;
    uint32_t adj[UDF_MAX_VERTICES];
} udf_graph;

typedef struct {
    int n;
    int m;
    uint32_t adj[UDF_MAX_PATTERN_VERTICES];
    int degree[UDF_MAX_PATTERN_VERTICES];
    int degree_at_least[UDF_MAX_PATTERN_VERTICES];
} udf_pattern;

typedef struct {
    int kind;
    int index;
    int pattern_vertices;
    int map[UDF_MAX_PATTERN_VERTICES];
    int pair_a;
    int pair_b;
} udf_witness;

typedef struct {
    int forbidden_count;
    udf_pattern forbidden[UDF_MAX_PATTERNS];
    int tu_count;
    udf_pattern tu[UDF_MAX_PATTERNS];
    int tu_pair_a[UDF_MAX_PATTERNS];
    int tu_pair_b[UDF_MAX_PATTERNS];
} udf_database;

int udf_graph6_decode(const char *line, udf_graph *out);
int udf_database_load(udf_database *db, const char *forbidden_json,
                      const char *tu_json, char *error, int error_size);
int udf_find(const udf_database *db, const udf_graph *host, udf_witness *out);

#endif
