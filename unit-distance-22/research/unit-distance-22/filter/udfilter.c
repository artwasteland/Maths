#include "udfilter.h"

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Host vertices are bits of a uint32_t (UINT32_C(1) << v for v < n), and so are pattern
   vertices in udf_pattern.adj. */
_Static_assert(UDF_MAX_VERTICES <= 32, "host adjacency rows and masks are uint32_t");
_Static_assert(UDF_MAX_PATTERN_VERTICES <= 32, "pattern adjacency rows are uint32_t");

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

/* sha256 of data/forbidden-398.json, the only file forbidden set 398 accepts.  A test build may
   override it with -D to exercise the count guard on a mutated file (enum/test-398). */
#ifndef UDF_FORBIDDEN_398_SHA256
#define UDF_FORBIDDEN_398_SHA256 "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
#endif

/* Compact SHA-256 (FIPS 180-4), used only to pin the forbidden-398 file. */
static uint32_t sha_rotr(uint32_t x, unsigned n) {
    return (x >> n) | (x << (32 - n));
}

static void sha_block(uint32_t h[8], const unsigned char *block) {
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t w[64], a, b, c, d, e, f, g, hh;
    int i;
    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)block[4*i] << 24) | ((uint32_t)block[4*i+1] << 16) |
               ((uint32_t)block[4*i+2] << 8) | block[4*i+3];
    for (i = 16; i < 64; i++) {
        uint32_t s0 = sha_rotr(w[i-15], 7) ^ sha_rotr(w[i-15], 18) ^ (w[i-15] >> 3);
        uint32_t s1 = sha_rotr(w[i-2], 17) ^ sha_rotr(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    a = h[0]; b = h[1]; c = h[2]; d = h[3]; e = h[4]; f = h[5]; g = h[6]; hh = h[7];
    for (i = 0; i < 64; i++) {
        uint32_t s1 = sha_rotr(e, 6) ^ sha_rotr(e, 11) ^ sha_rotr(e, 25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t t1 = hh + s1 + ch + k[i] + w[i];
        uint32_t s0 = sha_rotr(a, 2) ^ sha_rotr(a, 13) ^ sha_rotr(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = s0 + maj;
        hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

static void sha256_hex(const unsigned char *data, size_t len, char hex[65]) {
    uint32_t h[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
                     0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    unsigned char block[64];
    uint64_t bits = (uint64_t)len * 8;
    size_t off = 0, rest;
    int i;
    while (len - off >= 64) { sha_block(h, data + off); off += 64; }
    rest = len - off;
    memset(block, 0, sizeof(block));
    memcpy(block, data + off, rest);
    block[rest] = 0x80;
    if (rest >= 56) { sha_block(h, block); memset(block, 0, sizeof(block)); }
    for (i = 0; i < 8; i++) block[56 + i] = (unsigned char)(bits >> (56 - 8 * i));
    sha_block(h, block);
    for (i = 0; i < 8; i++)
        snprintf(hex + 8 * i, 9, "%08x", (unsigned)h[i]);
    hex[64] = '\0';
}

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

static int load_forbidden(udf_database *db, const char *path, int forbidden_set,
                          char *error, int error_size) {
    char *data;
    long length;
    const char *p, *end;
    if (forbidden_set != UDF_FORBIDDEN_SET_74 && forbidden_set != UDF_FORBIDDEN_SET_398) {
        set_error(error, error_size, "forbidden set must be 74 or 398");
        return 0;
    }
    data = read_all(path, &length, error, error_size);
    if (data == NULL) return 0;
    if (forbidden_set == UDF_FORBIDDEN_SET_398) {
        /* Hash the very bytes that are parsed below. */
        char hex[65];
        sha256_hex((const unsigned char *)data, (size_t)length, hex);
        if (strcmp(hex, UDF_FORBIDDEN_398_SHA256) != 0) {
            free(data);
            snprintf(error, (size_t)error_size,
                     "forbidden JSON sha256 %s is not the pinned forbidden-398.json", hex);
            return 0;
        }
    }
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
        /* Set 74 keeps the old capacity (UDF_MAX_PATTERNS), so every input is rejected where
           and as it was before; set 398 may use the raised capacity. */
        if (*p++ != '[' || db->forbidden_count >= (forbidden_set == UDF_FORBIDDEN_SET_74
                                                    ? UDF_MAX_PATTERNS : UDF_MAX_FORBIDDEN)) {
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
    if (forbidden_set == UDF_FORBIDDEN_SET_74 && db->forbidden_count != 74) {
        set_error(error, error_size, "forbidden JSON does not contain 74 patterns");
        return 0;
    }
    if (forbidden_set == UDF_FORBIDDEN_SET_398) {
        int i;
        if (db->forbidden_count != 398) {
            set_error(error, error_size, "forbidden JSON does not contain 398 patterns");
            return 0;
        }
        for (i = 0; i < db->forbidden_count; i++) {
            if (db->forbidden[i].n > 10) {
                set_error(error, error_size, "forbidden set 398 has a graph of order above 10");
                return 0;
            }
        }
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

int udf_database_load_set(udf_database *db, const char *forbidden_json,
                          const char *tu_json, int forbidden_set,
                          char *error, int error_size) {
    memset(db, 0, sizeof(*db));
    if (!load_forbidden(db, forbidden_json, forbidden_set, error, error_size)) return 0;
    return load_tu(db, tu_json, error, error_size);
}

int udf_database_load(udf_database *db, const char *forbidden_json,
                      const char *tu_json, char *error, int error_size) {
    return udf_database_load_set(db, forbidden_json, tu_json, UDF_FORBIDDEN_SET_74,
                                 error, error_size);
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
