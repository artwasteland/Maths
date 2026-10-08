#include "udfilter.h"

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const udf_graph *host;
    const udf_pattern *pattern;
    uint32_t allowed[UDF_MAX_PATTERN_VERTICES];
    int order[UDF_MAX_PATTERN_VERTICES];
    int map[UDF_MAX_PATTERN_VERTICES];
    uint32_t used;
    int pair_a;
    int pair_b;
    int require_nonedge;
} search_state;

typedef struct {
    int m;
    uint32_t degree_at_least[UDF_MAX_PATTERN_VERTICES];
    int degree_count_at_least[UDF_MAX_PATTERN_VERTICES];
} host_summary;

static void set_error(char *error, int size, const char *message) {
    if (error != NULL && size > 0) {
        snprintf(error, (size_t)size, "%s", message);
    }
}

static int edge(const uint32_t *adj, int a, int b) {
    return (adj[a] & (UINT32_C(1) << b)) != 0;
}

static void finish_pattern(udf_pattern *pattern) {
    int d, i;
    for (d = 0; d < UDF_MAX_PATTERN_VERTICES; d++) {
        for (i = 0; i < pattern->n; i++) {
            pattern->degree_at_least[d] += pattern->degree[i] >= d;
        }
    }
}

static char *read_all(const char *path, long *length, char *error, int error_size);
static const char *next_int(const char *p, const char *end, int *value);

static int read_graph6_char(const char **p, unsigned *value) {
    unsigned char c = (unsigned char)**p;
    if (c < 63 || c > 126) {
        return 0;
    }
    *value = c - 63;
    (*p)++;
    return 1;
}

int udf_graph6_decode(const char *line, udf_graph *out) {
    const char *p = line;
    unsigned value;
    int n, i, j, bit = 0;
    uint32_t adj[UDF_MAX_VERTICES] = {0};

    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    if (strncmp(p, ">>graph6<<", 10) == 0) p += 10;
    if (!read_graph6_char(&p, &value)) return 0;
    if (value < 63) {
        n = (int)value;
    } else {
        unsigned a, b, c;
        if (!read_graph6_char(&p, &a) || !read_graph6_char(&p, &b) ||
            !read_graph6_char(&p, &c)) return 0;
        n = (int)((a << 12) | (b << 6) | c);
    }
    if (n < 0 || n > UDF_MAX_VERTICES) return 0;
    /* graph6 lists the upper triangle by columns: (0,1), then
       (0,2),(1,2), then (0,3),(1,3),(2,3), and so on. */
    for (j = 1; j < n; j++) {
        for (i = 0; i < j; i++) {
            if (bit % 6 == 0 && !read_graph6_char(&p, &value)) return 0;
            int shift = 5 - (bit % 6);
            if (value & (1u << shift)) {
                adj[i] |= UINT32_C(1) << j;
                adj[j] |= UINT32_C(1) << i;
            }
            bit++;
        }
    }
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    if (*p != '\0') return 0;
    out->n = n;
    memcpy(out->adj, adj, sizeof(adj));
    return 1;
}

static const char *skip_space(const char *p, const char *end) {
    while (p < end && isspace((unsigned char)*p)) p++;
    return p;
}

static int load_forbidden(udf_database *db, const char *path,
                          char *error, int error_size) {
    char *data;
    long length;
    const char *p, *end;
    data = read_all(path, &length, error, error_size);
    if (data == NULL) return 0;
    p = skip_space(data, data + length);
    end = data + length;
    if (p >= end || *p++ != '[') {
        free(data); set_error(error, error_size, "invalid forbidden JSON"); return 0;
    }
    db->forbidden_count = 0;
    while (1) {
        udf_pattern *pat;
        int max_vertex = -1, m = 0;
        p = skip_space(p, end);
        if (p >= end) break;
        if (*p == ']') { p++; break; }
        if (*p++ != '[' || db->forbidden_count >= UDF_MAX_PATTERNS) {
            free(data); set_error(error, error_size, "invalid forbidden JSON"); return 0;
        }
        pat = &db->forbidden[db->forbidden_count];
        memset(pat, 0, sizeof(*pat));
        while (1) {
            int a, b;
            p = skip_space(p, end);
            if (p >= end) { free(data); set_error(error, error_size, "invalid forbidden JSON"); return 0; }
            if (*p == ']') { p++; break; }
            if (*p++ != '[' || (p = next_int(p, end, &a)) == NULL ||
                (p = next_int(p, end, &b)) == NULL || a < 0 || b < 0 || a == b ||
                a >= UDF_MAX_PATTERN_VERTICES || b >= UDF_MAX_PATTERN_VERTICES) {
                free(data); set_error(error, error_size, "invalid forbidden edge"); return 0;
            }
            pat->adj[a] |= UINT32_C(1) << b;
            pat->adj[b] |= UINT32_C(1) << a;
            if (a > max_vertex) max_vertex = a;
            if (b > max_vertex) max_vertex = b;
            m++;
            p = skip_space(p, end);
            if (p >= end || *p++ != ']') {
                free(data); set_error(error, error_size, "invalid forbidden edge"); return 0;
            }
            p = skip_space(p, end);
            if (p < end && *p == ',') p++;
        }
        pat->n = max_vertex + 1;
        pat->m = m;
        for (int i = 0; i < pat->n; i++) pat->degree[i] = __builtin_popcount(pat->adj[i]);
        finish_pattern(pat);
        db->forbidden_count++;
        p = skip_space(p, end);
        if (p < end && *p == ',') p++;
    }
    free(data);
    if (db->forbidden_count != 74) {
        set_error(error, error_size, "forbidden JSON does not contain 74 patterns");
        return 0;
    }
    return 1;
}

static char *read_all(const char *path, long *length, char *error, int error_size) {
    FILE *fp = fopen(path, "rb");
    char *data;
    long size;
    if (fp == NULL) {
        snprintf(error, (size_t)error_size, "cannot open TU data: %s", path);
        return NULL;
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (size = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fclose(fp);
        set_error(error, error_size, "cannot size TU data");
        return NULL;
    }
    data = malloc((size_t)size + 1);
    if (data == NULL || fread(data, 1, (size_t)size, fp) != (size_t)size) {
        free(data);
        fclose(fp);
        set_error(error, error_size, "cannot read TU data");
        return NULL;
    }
    data[size] = '\0';
    fclose(fp);
    *length = size;
    return data;
}

static const char *find_key(const char *start, const char *end, const char *key) {
    size_t len = strlen(key);
    const char *p = start;
    while (p + len + 2 <= end) {
        if (p[0] == '"' && strncmp(p + 1, key, len) == 0 && p[len + 1] == '"')
            return p + len + 2;
        p++;
    }
    return NULL;
}

static const char *next_int(const char *p, const char *end, int *value) {
    char *q;
    long x;
    while (p < end && !isdigit((unsigned char)*p) && *p != '-') p++;
    if (p >= end) return NULL;
    errno = 0;
    x = strtol(p, &q, 10);
    if (q == p || errno != 0 || x < -1 || x > 1000) return NULL;
    *value = (int)x;
    return q;
}

static int load_tu(udf_database *db, const char *path, char *error, int error_size) {
    long length;
    char *data = read_all(path, &length, error, error_size);
    const char *p, *end;
    if (data == NULL) return 0;
    db->tu_count = 0;
    p = data;
    end = data + length;
    while ((p = strchr(p, '{')) != NULL && p < end) {
        const char *close = strchr(p, '}');
        const char *q, *edges_key, *pair_key;
        int n, m, a, b, i;
        if (close == NULL) break;
        if (db->tu_count >= UDF_MAX_PATTERNS ||
            (q = find_key(p, close, "n")) == NULL ||
            (q = next_int(q, close, &n)) == NULL ||
            (q = find_key(q, close, "m")) == NULL ||
            (q = next_int(q, close, &m)) == NULL ||
            (edges_key = find_key(q, close, "edges")) == NULL) {
            free(data); set_error(error, error_size, "invalid TU object"); return 0;
        }
        q = edges_key;
        udf_pattern *pat = &db->tu[db->tu_count];
        memset(pat, 0, sizeof(*pat));
        pat->n = n; pat->m = m;
        for (i = 0; i < m; i++) {
            if ((q = next_int(q, close, &a)) == NULL ||
                (q = next_int(q, close, &b)) == NULL || a < 0 || b < 0 ||
                a >= n || b >= n || a == b) {
                free(data); set_error(error, error_size, "invalid TU edge list"); return 0;
            }
            pat->adj[a] |= UINT32_C(1) << b;
            pat->adj[b] |= UINT32_C(1) << a;
        }
        for (i = 0; i < n; i++) {
            int j;
            for (j = 0; j < n; j++) pat->degree[i] += edge(pat->adj, i, j);
        }
        finish_pattern(pat);
        if ((pair_key = find_key(q, close, "pair")) == NULL ||
            (q = next_int(pair_key, close, &a)) == NULL ||
            (q = next_int(q, close, &b)) == NULL || a < 0 || b < 0 ||
            a >= n || b >= n || a == b) {
            free(data); set_error(error, error_size, "invalid TU pair"); return 0;
        }
        db->tu_pair_a[db->tu_count] = a;
        db->tu_pair_b[db->tu_count] = b;
        db->tu_count++;
        p = close + 1;
    }
    free(data);
    if (db->tu_count != 6) {
        set_error(error, error_size, "TU data does not contain 6 gadgets");
        return 0;
    }
    return 1;
}

int udf_database_load(udf_database *db, const char *forbidden_json,
                      const char *tu_json, char *error, int error_size) {
    memset(db, 0, sizeof(*db));
    if (!load_forbidden(db, forbidden_json, error, error_size)) return 0;
    return load_tu(db, tu_json, error, error_size);
}

static uint32_t candidates(const search_state *s, int pv) {
    return s->allowed[pv] & ~s->used;
}

static int search(search_state *s, int depth) {
    int k, pv = -1, best_count = 1000;
    uint32_t mask, best_mask = 0;
    if (depth == s->pattern->n) {
        if (s->require_nonedge && edge(s->host->adj, s->map[s->pair_a], s->map[s->pair_b]))
            return 0;
        return 1;
    }
    for (k = depth; k < s->pattern->n; k++) {
        int candidate_count;
        int v = s->order[k];
        mask = candidates(s, v);
        candidate_count = __builtin_popcount(mask);
        if (candidate_count < best_count) {
            best_count = candidate_count;
            pv = v;
            best_mask = mask;
            if (candidate_count == 0) return 0;
        }
    }
    if (pv < 0) return 0;
    for (k = depth; k < s->pattern->n; k++) {
        if (s->order[k] == pv) {
            int temp = s->order[depth]; s->order[depth] = s->order[k]; s->order[k] = temp;
            break;
        }
    }
    mask = best_mask;
    while (mask != 0) {
        int j, ok = 1;
        uint32_t changed = 0;
        uint32_t old_allowed[UDF_MAX_PATTERN_VERTICES];
        k = __builtin_ctz(mask);
        mask &= mask - 1;
        s->map[pv] = k;
        if (s->require_nonedge && ((pv == s->pair_a && s->map[s->pair_b] >= 0) ||
                                   (pv == s->pair_b && s->map[s->pair_a] >= 0))) {
            int other = pv == s->pair_a ? s->map[s->pair_b] : s->map[s->pair_a];
            if (edge(s->host->adj, k, other)) ok = 0;
        }
        if (ok) {
            s->used |= UINT32_C(1) << k;
            for (j = 0; j < s->pattern->n; j++) {
                if (s->map[j] < 0) {
                    if (edge(s->pattern->adj, pv, j)) {
                        old_allowed[j] = s->allowed[j];
                        s->allowed[j] &= s->host->adj[k];
                        changed |= UINT32_C(1) << j;
                    }
                    if (candidates(s, j) == 0) {
                        ok = 0;
                        break;
                    }
                }
            }
            if (ok && search(s, depth + 1)) return 1;
            while (changed != 0) {
                j = __builtin_ctz(changed);
                s->allowed[j] = old_allowed[j];
                changed &= changed - 1;
            }
            s->used &= ~(UINT32_C(1) << k);
        }
        s->map[pv] = -1;
    }
    return 0;
}

static int find_pattern(const udf_graph *host, const udf_pattern *pattern,
                        const host_summary *summary,
                        int pair_a, int pair_b, int require_nonedge,
                        int *map_out) {
    search_state s;
    int i, j;
    if (pattern->n > host->n || pattern->m > summary->m) return 0;
    for (i = 1; i < UDF_MAX_PATTERN_VERTICES; i++) {
        if (pattern->degree_at_least[i] > summary->degree_count_at_least[i]) return 0;
    }
    memset(&s, 0, sizeof(s));
    s.host = host; s.pattern = pattern; s.pair_a = pair_a; s.pair_b = pair_b;
    s.require_nonedge = require_nonedge;
    for (i = 0; i < pattern->n; i++) {
        s.map[i] = -1;
        s.order[i] = i;
        s.allowed[i] = summary->degree_at_least[pattern->degree[i]];
    }
    for (i = 0; i < pattern->n; i++) {
        for (j = i + 1; j < pattern->n; j++) {
            int a = s.order[i], b = s.order[j];
            if (pattern->degree[b] > pattern->degree[a]) {
                s.order[i] = b; s.order[j] = a;
            }
        }
    }
    if (!search(&s, 0)) return 0;
    for (i = 0; i < pattern->n; i++) map_out[i] = s.map[i];
    return 1;
}

int udf_find(const udf_database *db, const udf_graph *host, udf_witness *out) {
    host_summary summary = {0};
    int i, v;
    if (host->n > UDF_MAX_VERTICES) return -1;
    for (v = 0; v < host->n; v++) {
        int d, degree = __builtin_popcount(host->adj[v]);
        uint32_t bit = UINT32_C(1) << v;
        summary.m += degree;
        if (degree >= UDF_MAX_PATTERN_VERTICES) degree = UDF_MAX_PATTERN_VERTICES - 1;
        for (d = 0; d <= degree; d++) {
            summary.degree_at_least[d] |= bit;
            summary.degree_count_at_least[d]++;
        }
    }
    summary.m /= 2;
    for (i = 0; i < db->forbidden_count; i++) {
        if (find_pattern(host, &db->forbidden[i], &summary, 0, 0, 0, out->map)) {
            out->kind = 1; out->index = i; out->pattern_vertices = db->forbidden[i].n;
            out->pair_a = out->pair_b = -1;
            return 1;
        }
    }
    for (i = 0; i < db->tu_count; i++) {
        if (find_pattern(host, &db->tu[i], &summary,
                         db->tu_pair_a[i], db->tu_pair_b[i], 1,
                         out->map)) {
            out->kind = 2; out->index = i; out->pattern_vertices = db->tu[i].n;
            out->pair_a = db->tu_pair_a[i]; out->pair_b = db->tu_pair_b[i];
            return 2;
        }
    }
    out->kind = 0; out->index = -1; out->pattern_vertices = 0;
    return 0;
}
