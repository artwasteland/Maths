#ifndef UDFILTER_H
#define UDFILTER_H

#include <stdint.h>

/* Host order limit.  Every host structure is a row of uint32_t bitmasks (udf_graph.adj, the
   search's allowed/used masks, the host summary's degree masks), so this may not exceed 32;
   udfilter.c asserts that.  Raised from 22 to 24 for the u(23) programme, whose top level
   (23,65) has 23-vertex hosts; hosts with at most 22 vertices are filtered exactly as before. */
#define UDF_MAX_VERTICES 24
#define UDF_MAX_PATTERN_VERTICES 15
#define UDF_MAX_PATTERN_EDGES 105
#define UDF_MAX_PATTERNS 128      /* TU gadgets */
#define UDF_MAX_FORBIDDEN 400     /* forbidden graphs: 74 or 398 */

/* The accepted forbidden lists.  Set 74 is Globus and Parshall's list with exactly the guard of
   the u(22) run (74 graphs).  Set 398 adds GP-10's 324 graphs on 10 vertices; its file must be
   data/forbidden-398.json, pinned by sha256, and hold 398 graphs of order at most 10. */
#define UDF_FORBIDDEN_SET_74 74
#define UDF_FORBIDDEN_SET_398 398

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
    udf_pattern forbidden[UDF_MAX_FORBIDDEN];
    int tu_count;
    udf_pattern tu[UDF_MAX_PATTERNS];
    int tu_pair_a[UDF_MAX_PATTERNS];
    int tu_pair_b[UDF_MAX_PATTERNS];
} udf_database;

int udf_graph6_decode(const char *line, udf_graph *out);
/* Loads forbidden set 74 (unchanged behaviour). */
int udf_database_load(udf_database *db, const char *forbidden_json,
                      const char *tu_json, char *error, int error_size);
/* forbidden_set is UDF_FORBIDDEN_SET_74 or UDF_FORBIDDEN_SET_398. */
int udf_database_load_set(udf_database *db, const char *forbidden_json,
                          const char *tu_json, int forbidden_set,
                          char *error, int error_size);
int udf_find(const udf_database *db, const udf_graph *host, udf_witness *out);

#endif
