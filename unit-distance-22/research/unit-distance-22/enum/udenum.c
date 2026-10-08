#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/resource.h>
#include <sys/stat.h>

#include "nauty.h"
#include "gtools.h"

#define MAXV 32
/* Structural limits.  A forbidden graph F has at most MAX_FORBIDDEN_ORDER vertices, so a
   deletion pattern F - v has at most MAX_PATTERN_ORDER vertices and its set S = N_F(v) has at
   most MAX_PATTERN_ORDER members.  The limits only size arrays; which list is accepted is
   decided by the guards of the selected forbidden set (ForbiddenSetGuards below). */
#define MAX_FORBIDDEN_ORDER 10
#define MAX_PATTERN_ORDER (MAX_FORBIDDEN_ORDER - 1)
#define MAXF 400
#define MAXPAT 4000
#define MAX_AUT_GENS 512
#define MAX_SOFTWARE 16

/* sha256 of data/forbidden-398.json, the only file forbidden set 398 accepts.  A test build may
   override it with -D to exercise the other guards on a mutated file (enum/test-398). */
#ifndef FORBIDDEN_398_SHA256
#define FORBIDDEN_398_SHA256 "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
#endif

typedef struct {
    int n;
    int m;
    uint32_t adj[MAX_FORBIDDEN_ORDER];
} SmallGraph;

typedef struct {
    int n;
    int m;
    int ssize;
    int s_complete_depth;
    int source;
    int deleted;
    uint32_t adj[MAX_PATTERN_ORDER];
    uint32_t smask;
    unsigned char degree[MAX_PATTERN_ORDER];
    unsigned char order[MAX_PATTERN_ORDER];
} Pattern;

typedef struct {
    SmallGraph forbidden[MAXF];
    int forbidden_count;
    Pattern patterns[MAXPAT];
    int pattern_count;
    int size_distribution[MAX_FORBIDDEN_ORDER];
} ForbiddenData;

/* The two accepted forbidden lists.  Set 74 keeps exactly the guards of the u(22) run (count,
   pattern count, size distribution, orders at most 9, no file hash).  Set 398 pins the file by
   its sha256 and then checks the same quantities. */
typedef struct {
    int set;
    int max_order;
    int max_graphs;        /* capacity while parsing: set 74 keeps the old MAXF 80 / MAXPAT 700, */
    int max_patterns;      /* so every input is rejected where and as it was before */
    int graphs;
    int patterns;
    int size_distribution[MAX_FORBIDDEN_ORDER];
    const char *sha256;
} ForbiddenSetGuards;

static const ForbiddenSetGuards FORBIDDEN_SET_74 = {
    74, 9, 80, 700, 74, 635, {0, 0, 61, 413, 130, 26, 4, 1, 0, 0}, NULL
};
static const ForbiddenSetGuards FORBIDDEN_SET_398 = {
    398, 10, MAXF, MAXPAT, 398, 3875, {0, 0, 251, 2474, 920, 192, 34, 4, 0, 0}, FORBIDDEN_398_SHA256
};

_Static_assert(MAX_PATTERN_ORDER + 1 == MAX_FORBIDDEN_ORDER, "pattern order is forbidden order minus one");
_Static_assert(MAX_FORBIDDEN_ORDER < MAXV, "forbidden graphs must fit the host bitsets");
_Static_assert(MAXF >= 398 && MAXPAT >= 3875, "array limits below the 398 list");
_Static_assert(MAXF >= 80 && MAXPAT >= 700, "set 74 parses up to the old capacities");

typedef struct {
    uint32_t *mark;
    uint32_t epoch;
    size_t mark_count;
    uint32_t *sets;
    size_t count;
    size_t capacity;
} BadFamily;

typedef struct {
    uint64_t parents_seen;
    uint64_t parents_processed;
    uint64_t parents_degree_skipped;
    uint64_t bad_sets;
    uint64_t neighbourhoods;
    uint64_t neighbourhood_orbit_reps;
    uint64_t neighbourhoods_bad;
    uint64_t child_orbit_rejected;
    uint64_t children_written;
} RunStats;

typedef struct {
    const char *name;
    const char *path;
} NamedPath;

typedef struct {
    const char *parents;
    const char *forbidden;
    const char *output;
    const char *manifest;
    const char *shard_id;
    long start;
    long end;
    int target_n;
    int target_m;
    int filter_mode;
    int forbidden_set;
    int pattern_stats;
    int verify_parents;
    int overwrite;
    int mutation_drop_first_badset;
    int mutation_no_child_orbit;
    NamedPath software[MAX_SOFTWARE];
    int software_count;
} Config;

static int aut_gen_count;
static int aut_gens[MAX_AUT_GENS][MAXV];

static void die(const char *message)
{
    fprintf(stderr, "udenum: %s\n", message);
    exit(2);
}

static void die_errno(const char *message)
{
    fprintf(stderr, "udenum: %s: %s\n", message, strerror(errno));
    exit(2);
}

static void *xmalloc(size_t n)
{
    void *p = malloc(n == 0 ? 1 : n);
    if (!p) die_errno("malloc");
    return p;
}

static void *xcalloc(size_t n, size_t s)
{
    void *p = calloc(n == 0 ? 1 : n, s == 0 ? 1 : s);
    if (!p) die_errno("calloc");
    return p;
}

static void *xrealloc(void *p, size_t n)
{
    void *q = realloc(p, n == 0 ? 1 : n);
    if (!q) die_errno("realloc");
    return q;
}

static char *read_whole_file(const char *path, size_t *size_out)
{
    FILE *f = fopen(path, "rb");
    char *buf;
    long size;
    if (!f) die_errno(path);
    if (fseek(f, 0, SEEK_END) != 0) die_errno("fseek");
    size = ftell(f);
    if (size < 0) die_errno("ftell");
    if (fseek(f, 0, SEEK_SET) != 0) die_errno("fseek");
    buf = xmalloc((size_t)size + 1);
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) die_errno("fread");
    if (fclose(f) != 0) die_errno("fclose");
    buf[size] = '\0';
    *size_out = (size_t)size;
    return buf;
}

static int popcount32(uint32_t x)
{
    return __builtin_popcount(x);
}

static int ctz32(uint32_t x)
{
    return __builtin_ctz(x);
}

static void compute_order(int n, const uint32_t *adj, unsigned char *order)
{
    uint32_t chosen = 0;
    int depth;
    for (depth = 0; depth < n; ++depth) {
        int best = -1;
        int best_links = -1;
        int best_degree = -1;
        int v;
        for (v = 0; v < n; ++v) {
            int links;
            int degree;
            if (chosen & (UINT32_C(1) << v)) continue;
            links = popcount32(adj[v] & chosen);
            degree = popcount32(adj[v]);
            if (links > best_links ||
                (links == best_links && degree > best_degree) ||
                (links == best_links && degree == best_degree && v < best)) {
                best = v;
                best_links = links;
                best_degree = degree;
            }
        }
        order[depth] = (unsigned char)best;
        chosen |= UINT32_C(1) << best;
    }
}

static void finalize_forbidden_graph(ForbiddenData *data, SmallGraph *g,
                                     const ForbiddenSetGuards *guards)
{
    int v;
    if (data->forbidden_count >= guards->max_graphs) die("too many forbidden graphs");
    if (g->n < 1 || g->n > guards->max_order) {
        char message[64];
        snprintf(message, sizeof(message), "forbidden graph order is outside 1..%d",
                 guards->max_order);
        die(message);
    }
    data->forbidden[data->forbidden_count++] = *g;
    for (v = 0; v < g->n; ++v) {
        Pattern *p;
        int old_to_new[MAX_FORBIDDEN_ORDER];
        int a, b;
        if (data->pattern_count >= guards->max_patterns) die("too many deletion patterns");
        p = &data->patterns[data->pattern_count];
        memset(p, 0, sizeof(*p));
        p->n = g->n - 1;
        p->source = data->forbidden_count - 1;
        p->deleted = v;
        for (a = 0, b = 0; a < g->n; ++a) {
            if (a == v) old_to_new[a] = -1;
            else old_to_new[a] = b++;
        }
        for (a = 0; a < g->n; ++a) {
            int na;
            if (a == v) continue;
            na = old_to_new[a];
            if (g->adj[v] & (UINT32_C(1) << a))
                p->smask |= UINT32_C(1) << na;
            for (b = a + 1; b < g->n; ++b) {
                int nb;
                if (b == v) continue;
                if (!(g->adj[a] & (UINT32_C(1) << b))) continue;
                nb = old_to_new[b];
                p->adj[na] |= UINT32_C(1) << nb;
                p->adj[nb] |= UINT32_C(1) << na;
                ++p->m;
            }
        }
        p->ssize = popcount32(p->smask);
        if (p->ssize < 0 || p->ssize >= MAX_FORBIDDEN_ORDER) die("bad pattern S size");
        ++data->size_distribution[p->ssize];
        for (a = 0; a < p->n; ++a)
            p->degree[a] = (unsigned char)popcount32(p->adj[a]);
        compute_order(p->n, p->adj, p->order);
        for (a = 0; a < p->n; ++a)
            if (p->smask & (UINT32_C(1) << p->order[a]))
                p->s_complete_depth = a + 1;
        ++data->pattern_count;
    }
}

static int compare_patterns(const void *aa, const void *bb)
{
    const Pattern *a = aa;
    const Pattern *b = bb;
    if (a->ssize != b->ssize) return a->ssize - b->ssize;
    if (a->m != b->m) return b->m - a->m;
    if (a->n != b->n) return b->n - a->n;
    if (a->source != b->source) return a->source - b->source;
    return a->deleted - b->deleted;
}

static void sha256_hex_buffer(const unsigned char *bytes, size_t len, char hex[65]);

static void load_forbidden_json(const char *path, ForbiddenData *data,
                                const ForbiddenSetGuards *guards)
{
    size_t size;
    char *text = read_whole_file(path, &size);
    size_t i = 0;
    int depth = 0;
    int pair[2];
    int pair_count = 0;
    int s;
    SmallGraph current;
    memset(data, 0, sizeof(*data));
    memset(&current, 0, sizeof(current));

    if (guards->sha256) {
        /* Hash the very bytes that are parsed below. */
        char hex[65];
        sha256_hex_buffer((const unsigned char *)text, size, hex);
        if (strcmp(hex, guards->sha256) != 0) {
            fprintf(stderr, "udenum: forbidden JSON sha256 %s is not the pinned %s of "
                    "forbidden set %d\n", hex, guards->sha256, guards->set);
            exit(2);
        }
    }

    while (i < size) {
        unsigned char ch = (unsigned char)text[i];
        if (ch == '[') {
            ++depth;
            if (depth == 2) memset(&current, 0, sizeof(current));
            if (depth == 3) pair_count = 0;
            ++i;
        } else if (ch == ']') {
            if (depth == 3) {
                int a, b;
                if (pair_count != 2) die("malformed edge in forbidden JSON");
                a = pair[0];
                b = pair[1];
                if (a < 0 || b < 0 || a >= guards->max_order || b >= guards->max_order || a == b)
                    die("bad forbidden edge");
                if (current.adj[a] & (UINT32_C(1) << b))
                    die("duplicate forbidden edge");
                current.adj[a] |= UINT32_C(1) << b;
                current.adj[b] |= UINT32_C(1) << a;
                ++current.m;
                if (a + 1 > current.n) current.n = a + 1;
                if (b + 1 > current.n) current.n = b + 1;
            } else if (depth == 2) {
                finalize_forbidden_graph(data, &current, guards);
            }
            --depth;
            if (depth < 0) die("unbalanced forbidden JSON");
            ++i;
        } else if (ch >= '0' && ch <= '9') {
            long value = 0;
            while (i < size && text[i] >= '0' && text[i] <= '9') {
                value = value * 10 + (text[i] - '0');
                ++i;
            }
            if (depth != 3 || pair_count >= 2) die("unexpected number in forbidden JSON");
            pair[pair_count++] = (int)value;
        } else {
            ++i;
        }
    }
    free(text);
    if (depth != 0) die("unbalanced forbidden JSON at end of file");
    qsort(data->patterns, (size_t)data->pattern_count,
          sizeof(data->patterns[0]), compare_patterns);
    if (data->forbidden_count != guards->graphs) {
        char message[80];
        snprintf(message, sizeof(message), "forbidden JSON does not contain %d graphs",
                 guards->graphs);
        die(message);
    }
    if (data->pattern_count != guards->patterns) {
        char message[80];
        snprintf(message, sizeof(message), "forbidden JSON does not yield %d deletion patterns",
                 guards->patterns);
        die(message);
    }
    /* Every size is compared.  For set 74 this is the old check of sizes 2..7: those sum to 635,
       so once the pattern count is 635 the other sizes are necessarily zero. */
    for (s = 0; s < MAX_FORBIDDEN_ORDER; ++s)
        if (data->size_distribution[s] != guards->size_distribution[s])
            die("forbidden pattern size distribution does not match the contract");
}

static void bad_family_init(BadFamily *bad, int n)
{
    memset(bad, 0, sizeof(*bad));
    bad->mark_count = (size_t)UINT32_C(1) << n;
    bad->mark = xcalloc(bad->mark_count, sizeof(*bad->mark));
    bad->epoch = 1;
}

static void bad_family_reset(BadFamily *bad)
{
    bad->count = 0;
    ++bad->epoch;
    if (bad->epoch == 0) {
        memset(bad->mark, 0, bad->mark_count * sizeof(*bad->mark));
        bad->epoch = 1;
    }
}

static int bad_family_contains_subset(const BadFamily *bad, uint32_t mask)
{
    uint32_t sub = mask;
    while (sub) {
        if (bad->mark[sub] == bad->epoch) return 1;
        sub = (sub - 1) & mask;
    }
    return 0;
}

static void bad_family_add(BadFamily *bad, uint32_t mask)
{
    if (bad_family_contains_subset(bad, mask)) return;
    if (bad->count == bad->capacity) {
        bad->capacity = bad->capacity ? 2 * bad->capacity : 256;
        bad->sets = xrealloc(bad->sets, bad->capacity * sizeof(*bad->sets));
    }
    bad->mark[mask] = bad->epoch;
    bad->sets[bad->count++] = mask;
}

static void bad_family_drop_first(BadFamily *bad)
{
    size_t i;
    uint32_t dropped;
    if (bad->count == 0) return;
    dropped = bad->sets[0];
    bad->mark[dropped] = 0;
    for (i = 1; i < bad->count; ++i) bad->sets[i - 1] = bad->sets[i];
    --bad->count;
}

typedef struct {
    const Pattern *pattern;
    const uint32_t *host_adj;
    const unsigned char *host_degree;
    int host_n;
    int map[MAX_PATTERN_ORDER];
    uint32_t used;
    uint32_t force_mask;
    int max_bad_size;
    BadFamily *bad;
} BadMatchContext;

static void find_bad_matches(BadMatchContext *ctx, int depth)
{
    const Pattern *p = ctx->pattern;
    int pv;
    uint32_t candidates;
    int q;
    if (depth == p->n) {
        uint32_t image = 0;
        uint32_t s = p->smask;
        while (s) {
            int v = ctz32(s);
            s &= s - 1;
            image |= UINT32_C(1) << ctx->map[v];
        }
        image |= ctx->force_mask;
        if (popcount32(image) <= ctx->max_bad_size) bad_family_add(ctx->bad, image);
        return;
    }
    if (depth == p->s_complete_depth) {
        uint32_t image = 0;
        uint32_t s = p->smask;
        while (s) {
            int s_vertex = ctz32(s);
            s &= s - 1;
            image |= UINT32_C(1) << ctx->map[s_vertex];
        }
        image |= ctx->force_mask;
        if (popcount32(image) > ctx->max_bad_size ||
            bad_family_contains_subset(ctx->bad, image)) return;
    }

    pv = p->order[depth];
    candidates = (((UINT32_C(1) << ctx->host_n) - 1) & ~ctx->used);
    for (q = 0; q < depth; ++q) {
        int mapped_pv = p->order[q];
        if (p->adj[pv] & (UINT32_C(1) << mapped_pv))
            candidates &= ctx->host_adj[ctx->map[mapped_pv]];
    }
    while (candidates) {
        int hv = ctz32(candidates);
        candidates &= candidates - 1;
        if (ctx->host_degree[hv] < p->degree[pv]) continue;
        ctx->map[pv] = hv;
        ctx->used |= UINT32_C(1) << hv;
        find_bad_matches(ctx, depth + 1);
        ctx->used &= ~(UINT32_C(1) << hv);
    }
}

static void build_bad_family(const ForbiddenData *data, const uint32_t *host_adj,
                             int host_n, int host_m, int max_bad_size,
                             uint32_t force_mask, BadFamily *bad)
{
    unsigned char degree[MAXV];
    int i;
    BadMatchContext ctx;
    bad_family_reset(bad);
    for (i = 0; i < host_n; ++i) degree[i] = (unsigned char)popcount32(host_adj[i]);
    memset(&ctx, 0, sizeof(ctx));
    ctx.host_adj = host_adj;
    ctx.host_degree = degree;
    ctx.host_n = host_n;
    ctx.force_mask = force_mask;
    ctx.max_bad_size = max_bad_size;
    ctx.bad = bad;
    for (i = 0; i < data->pattern_count; ++i) {
        const Pattern *p = &data->patterns[i];
        if (p->n > host_n || p->m > host_m || p->ssize > max_bad_size) continue;
        ctx.pattern = p;
        ctx.used = 0;
        find_bad_matches(&ctx, 0);
    }
}

typedef struct {
    const Pattern *pattern;
    const uint32_t *host_adj;
    const unsigned char *host_degree;
    int host_n;
    int map[MAX_PATTERN_ORDER];
    uint32_t mapped_pattern;
    uint32_t used_host;
    int s_vertices[MAX_PATTERN_ORDER];
    int t_vertices[MAX_PATTERN_ORDER];
    int ssize;
} AnchoredContext;

static int anchored_extend(AnchoredContext *ctx)
{
    const Pattern *p = ctx->pattern;
    int pv;
    int best = -1;
    int best_links = -1;
    int best_degree = -1;
    uint32_t candidates;
    int v;
    if (popcount32(ctx->mapped_pattern) == p->n) return 1;
    for (pv = 0; pv < p->n; ++pv) {
        int links;
        int degree;
        if (ctx->mapped_pattern & (UINT32_C(1) << pv)) continue;
        links = popcount32(p->adj[pv] & ctx->mapped_pattern);
        degree = p->degree[pv];
        if (links > best_links ||
            (links == best_links && degree > best_degree) ||
            (links == best_links && degree == best_degree && pv < best)) {
            best = pv;
            best_links = links;
            best_degree = degree;
        }
    }
    pv = best;
    candidates = (((UINT32_C(1) << ctx->host_n) - 1) & ~ctx->used_host);
    for (v = 0; v < p->n; ++v) {
        if ((ctx->mapped_pattern & (UINT32_C(1) << v)) &&
            (p->adj[pv] & (UINT32_C(1) << v)))
            candidates &= ctx->host_adj[ctx->map[v]];
    }
    while (candidates) {
        int hv = ctz32(candidates);
        candidates &= candidates - 1;
        if (ctx->host_degree[hv] < p->degree[pv]) continue;
        ctx->map[pv] = hv;
        ctx->mapped_pattern |= UINT32_C(1) << pv;
        ctx->used_host |= UINT32_C(1) << hv;
        if (anchored_extend(ctx)) return 1;
        ctx->mapped_pattern &= ~(UINT32_C(1) << pv);
        ctx->used_host &= ~(UINT32_C(1) << hv);
    }
    return 0;
}

static int anchored_assign_s(AnchoredContext *ctx, int depth)
{
    const Pattern *p = ctx->pattern;
    int pv;
    int i;
    if (depth == ctx->ssize) return anchored_extend(ctx);
    pv = ctx->s_vertices[depth];
    for (i = 0; i < ctx->ssize; ++i) {
        int hv = ctx->t_vertices[i];
        int q;
        int compatible = 1;
        if (ctx->used_host & (UINT32_C(1) << hv)) continue;
        if (ctx->host_degree[hv] < p->degree[pv]) continue;
        for (q = 0; q < depth; ++q) {
            int other_pv = ctx->s_vertices[q];
            if ((p->adj[pv] & (UINT32_C(1) << other_pv)) &&
                !(ctx->host_adj[hv] & (UINT32_C(1) << ctx->map[other_pv]))) {
                compatible = 0;
                break;
            }
        }
        if (!compatible) continue;
        ctx->map[pv] = hv;
        ctx->mapped_pattern |= UINT32_C(1) << pv;
        ctx->used_host |= UINT32_C(1) << hv;
        if (anchored_assign_s(ctx, depth + 1)) return 1;
        ctx->mapped_pattern &= ~(UINT32_C(1) << pv);
        ctx->used_host &= ~(UINT32_C(1) << hv);
    }
    return 0;
}

static int pattern_has_s_image(const Pattern *p, const uint32_t *host_adj,
                               const unsigned char *host_degree, int host_n,
                               uint32_t target)
{
    AnchoredContext ctx;
    uint32_t s;
    int count = 0;
    memset(&ctx, 0, sizeof(ctx));
    ctx.pattern = p;
    ctx.host_adj = host_adj;
    ctx.host_degree = host_degree;
    ctx.host_n = host_n;
    ctx.ssize = p->ssize;
    s = p->smask;
    while (s) {
        int v = ctz32(s);
        s &= s - 1;
        ctx.s_vertices[count++] = v;
    }
    count = 0;
    s = target;
    while (s) {
        int v = ctz32(s);
        s &= s - 1;
        ctx.t_vertices[count++] = v;
    }
    return anchored_assign_s(&ctx, 0);
}

static int __attribute__((unused)) has_bad_image_within(const ForbiddenData *data,
                                const uint32_t *host_adj,
                                const unsigned char *host_degree,
                                int host_n, int host_m, uint32_t neighbourhood)
{
    int i;
    int neighbourhood_size = popcount32(neighbourhood);
    for (i = 0; i < data->pattern_count; ++i) {
        const Pattern *p = &data->patterns[i];
        uint32_t image;
        if (p->ssize > neighbourhood_size) break;
        if (p->n > host_n || p->m > host_m) continue;
        image = neighbourhood;
        while (image) {
            if (popcount32(image) == p->ssize &&
                pattern_has_s_image(p, host_adj, host_degree, host_n, image)) return 1;
            image = (image - 1) & neighbourhood;
        }
    }
    return 0;
}

static void __attribute__((unused)) build_candidate_bad_family(const ForbiddenData *data,
                                       const uint32_t *host_adj, int host_n,
                                       int host_m, int max_bad_size,
                                       BadFamily *bad)
{
    unsigned char degree[MAXV];
    int size;
    int i;
    for (i = 0; i < host_n; ++i) degree[i] = (unsigned char)popcount32(host_adj[i]);
    bad_family_reset(bad);
    for (size = 2; size <= max_bad_size; ++size) {
        uint32_t mask = (UINT32_C(1) << size) - 1;
        uint32_t limit = UINT32_C(1) << host_n;
        while (mask < limit) {
            if (!bad_family_contains_subset(bad, mask)) {
                for (i = 0; i < data->pattern_count; ++i) {
                    const Pattern *p = &data->patterns[i];
                    if (p->ssize < size) continue;
                    if (p->ssize > size) break;
                    if (p->n > host_n || p->m > host_m) continue;
                    if (pattern_has_s_image(p, host_adj, degree, host_n, mask)) {
                        bad_family_add(bad, mask);
                        break;
                    }
                }
            }
            {
                uint32_t low = mask & (uint32_t)(-(int32_t)mask);
                uint32_t next = mask + low;
                mask = next | (((mask ^ next) >> 2) / low);
            }
        }
    }
}

typedef struct {
    const SmallGraph *pattern;
    const uint32_t *host_adj;
    const unsigned char *host_degree;
    int host_n;
    unsigned char order[MAX_FORBIDDEN_ORDER];
    int map[MAX_FORBIDDEN_ORDER];
    uint32_t used;
} ExistsContext;

static int exists_match(ExistsContext *ctx, int depth)
{
    const SmallGraph *p = ctx->pattern;
    int pv;
    uint32_t candidates;
    int q;
    if (depth == p->n) return 1;
    pv = ctx->order[depth];
    candidates = (((UINT32_C(1) << ctx->host_n) - 1) & ~ctx->used);
    for (q = 0; q < depth; ++q) {
        int mapped_pv = ctx->order[q];
        if (p->adj[pv] & (UINT32_C(1) << mapped_pv))
            candidates &= ctx->host_adj[ctx->map[mapped_pv]];
    }
    while (candidates) {
        int hv = ctz32(candidates);
        candidates &= candidates - 1;
        if (ctx->host_degree[hv] < popcount32(p->adj[pv])) continue;
        ctx->map[pv] = hv;
        ctx->used |= UINT32_C(1) << hv;
        if (exists_match(ctx, depth + 1)) return 1;
        ctx->used &= ~(UINT32_C(1) << hv);
    }
    return 0;
}

static int contains_forbidden(const ForbiddenData *data, const uint32_t *adj,
                              int n, int m)
{
    unsigned char degree[MAXV];
    int i;
    ExistsContext ctx;
    for (i = 0; i < n; ++i) degree[i] = (unsigned char)popcount32(adj[i]);
    memset(&ctx, 0, sizeof(ctx));
    ctx.host_adj = adj;
    ctx.host_degree = degree;
    ctx.host_n = n;
    for (i = 0; i < data->forbidden_count; ++i) {
        const SmallGraph *p = &data->forbidden[i];
        if (p->n > n || p->m > m) continue;
        ctx.pattern = p;
        compute_order(p->n, p->adj, ctx.order);
        ctx.used = 0;
        if (exists_match(&ctx, 0)) return 1;
    }
    return 0;
}

static void build_restricted_bad_family(const ForbiddenData *data,
                                        const uint32_t *host_adj, int host_n,
                                        int host_m, int max_bad_size,
                                        uint32_t required, BadFamily *bad)
{
    int size;
    bad_family_reset(bad);
    for (size = popcount32(required) > 2 ? popcount32(required) : 2;
         size <= max_bad_size; ++size) {
        uint32_t mask;
        uint32_t limit = UINT32_C(1) << host_n;
        if (size == 0) mask = 0;
        else mask = (UINT32_C(1) << size) - 1;
        while (mask < limit) {
            if ((mask & required) == required && !bad_family_contains_subset(bad, mask)) {
                uint32_t child_adj[MAXV];
                int i;
                for (i = 0; i < host_n; ++i) child_adj[i] = host_adj[i];
                child_adj[host_n] = 0;
                for (i = 0; i < host_n; ++i) {
                    if (mask & (UINT32_C(1) << i)) {
                        child_adj[i] |= UINT32_C(1) << host_n;
                        child_adj[host_n] |= UINT32_C(1) << i;
                    }
                }
                if (contains_forbidden(data, child_adj, host_n + 1, host_m + size))
                    bad_family_add(bad, mask);
            }
            if (size == 0) break;
            {
                uint32_t low = mask & (uint32_t)(-(int32_t)mask);
                uint32_t next = mask + low;
                mask = next | (((mask ^ next) >> 2) / low);
            }
        }
    }
}

static void collect_automorphism(int count, int *perm, int *orbits,
                                 int numorbits, int stabvertex, int n)
{
    int i;
    (void)count;
    (void)orbits;
    (void)numorbits;
    (void)stabvertex;
    if (aut_gen_count >= MAX_AUT_GENS) die("too many nauty automorphism generators");
    for (i = 0; i < n; ++i) aut_gens[aut_gen_count][i] = perm[i];
    ++aut_gen_count;
}

static void adjacency_to_nauty(const uint32_t *adj, int n, graph *g)
{
    int i, j;
    EMPTYGRAPH(g, 1, n);
    for (i = 0; i < n; ++i)
        for (j = i + 1; j < n; ++j)
            if (adj[i] & (UINT32_C(1) << j)) ADDONEEDGE(g, i, j, 1);
}

static void nauty_to_adjacency(const graph *g, int n, uint32_t *adj)
{
    int i, j;
    for (i = 0; i < n; ++i) adj[i] = 0;
    for (i = 0; i < n; ++i)
        for (j = i + 1; j < n; ++j)
            if (ISELEMENT(GRAPHROW(g, i, 1), j)) {
                adj[i] |= UINT32_C(1) << j;
                adj[j] |= UINT32_C(1) << i;
            }
}

static void canonicalize(const uint32_t *adj, int n, graph *canong,
                         int *lab, int *orbits, int collect_aut)
{
    graph g[MAXV];
    int ptn[MAXV];
    statsblk stats;
    DEFAULTOPTIONS_GRAPH(options);
    if (n < 1 || n >= MAXV || SETWORDSNEEDED(n) != 1)
        die("graph order is unsupported");
    adjacency_to_nauty(adj, n, g);
    options.getcanon = TRUE;
    options.defaultptn = TRUE;
    if (collect_aut) {
        aut_gen_count = 0;
        options.userautomproc = collect_automorphism;
    }
    densenauty(g, lab, ptn, orbits, &options, &stats, 1, n, canong);
}

static int graph_edge_count(const uint32_t *adj, int n)
{
    int total = 0;
    int i;
    for (i = 0; i < n; ++i) total += popcount32(adj[i]);
    return total / 2;
}

static int parse_graph6_line(char *line, uint32_t *adj)
{
    graph g[MAXV];
    int n = graphsize(line);
    if (n == 0) {
        if (strcmp(line, "?") != 0) die("bad zero-vertex graph6 line");
        return 0;
    }
    if (n < 0 || n >= MAXV || SETWORDSNEEDED(n) != 1) die("bad or unsupported graph6 line");
    stringtograph(line, g, 1);
    nauty_to_adjacency(g, n, adj);
    return n;
}

static uint64_t choose_table[MAXV][MAXV];

static void init_choose_table(void)
{
    int n, k;
    memset(choose_table, 0, sizeof(choose_table));
    for (n = 0; n < MAXV; ++n) {
        choose_table[n][0] = choose_table[n][n] = 1;
        for (k = 1; k < n; ++k)
            choose_table[n][k] = choose_table[n - 1][k - 1] + choose_table[n - 1][k];
    }
}

/* =============================================================================================
   Forbidden set 398, faster.  Validation: enum/test-398/speed398-*.py (identity against the
   unmodified Mode 398 in test-398/base398, red controls, speed).

   Everything in this block is used by forbidden set 398 only; forbidden set 74 runs exactly the
   code above, unchanged.  Each function here replaces one set-74 function and computes the same
   thing: contains_forbidden_398 gives contains_forbidden's answer, anchored_images_398 makes
   exactly build_bad_family's additions in the same order, and build_restricted_bad_family_398
   builds build_restricted_bad_family's family set for set and in order.  So every output byte and
   every counter (bad_sets included) is unchanged, whatever the input.  The arguments are written
   next to each function.

   Notation.  P is the parent on vertices 0..n-1, w the new vertex, child(M) is P plus w joined to
   the vertex set M.  "G embeds in H" means an injective map psi: V(G) -> V(H) taking edges to
   edges (a not necessarily induced subgraph), the relation exists_match and find_bad_matches
   search for.  A pattern (F, v) is a forbidden graph F with a deleted vertex v; its graph is F - v
   and its set S = N_F(v); an image of the pattern is psi(S) for an embedding psi of F - v in P.

   Filters.  Every search here is a complete backtracking search.  Besides the old degree test it
   discards candidate vertices using further conditions that hold for EVERY embedding psi of a
   graph G, so a discarded branch contains no embedding and no search result changes:
     degree     deg_P(psi(u)) >= deg_G(u)                    (the old test);
     triangles  t_P(psi(u)) >= t_G(u), t = triangles at the vertex: psi maps the triangles at u
                injectively to triangles at psi(u);
     squares    q_P(psi(u)) >= q_G(u), q(u) = sum over x != u of C(|N(u) & N(x)|, 2), the 4-cycles
                through u counted by their opposite corner x: psi maps (x, {a, b}) injectively to
                (psi(x), {psi(a), psi(b)}) with psi(a), psi(b) in N(psi(u)) & N(psi(x));
     nbcount    for k = 2..6, #{x in N_P(psi(u)): deg_P(x) >= k} >= #{y in N_G(u): deg_G(y) >= k}:
                y -> psi(y) is injective into N_P(psi(u)) and deg_P(psi(y)) >= deg_G(y);
     pairs      for an earlier position a of the search order with a ~ u or c(a,u) > 0, where
                c(a,u) = |N_G(a) & N_G(u)|: psi(a) ~ psi(u) when a ~ u, and
                |N_P(psi(a)) & N_P(psi(u))| >= min(c(a,u), 4): common neighbours map injectively
                to common neighbours;
     count      for t = 1..10, P has at least as many vertices of degree >= t as G (psi maps them
                injectively to vertices of degree >= t); otherwise G is not searched at all.
   ============================================================================================= */

#define SG_MAX MAX_FORBIDDEN_ORDER            /* a search graph: a pattern F - v or a whole F */
#define SG_NB_LOW 2                           /* nbcount thresholds k = SG_NB_LOW..SG_NB_HIGH */
#define SG_NB_HIGH 6
#define SG_CN_CAP 4                           /* common-neighbour counts are capped at this */
#define SG_COUNT_CAP 63                       /* host triangle and square counts are capped here */
#define SG_PAIR_TYPES (2 * (SG_CN_CAP + 1))   /* pair type = (SG_CN_CAP + 1) * adjacent + c */

/* Pinned by an independent computation (enum/test-398/speed398-data.py, networkx): the 3,875
   deletion patterns of set 398 fall into 3,387 Aut(F)-orbit classes, by |S| as below. */
#define SEARCH_398_PATTERNS 3387
static const int SEARCH_398_SIZE_DISTRIBUTION[MAX_FORBIDDEN_ORDER] = {0, 0, 209, 2126, 830, 184, 34, 4, 0, 0};
/* ... and their graphs F - v (S forgotten) fall into 1,843 isomorphism classes (same script). */
#define SEARCH_398_GRAPH_CLASSES 1843

/* The restricted path switches from testing each candidate child to the anchored family only
   when enough candidates remain.  The family grows dearer with the parent's order n faster than
   one child test does; the thresholds below were measured on the sampled parents of levels 12..21
   (instructions retired).  A speed choice only: the family built is the same either way
   (build_restricted_bad_family_398).  A test build may fix the threshold with
   -DRESTRICTED_SWITCH_CANDIDATES=k (k >= 1). */
#ifndef RESTRICTED_SWITCH_CANDIDATES
#define RESTRICTED_SWITCH_CANDIDATES 0
#endif

static uint64_t restricted_switch_threshold(int host_n)
{
    if (RESTRICTED_SWITCH_CANDIDATES > 0) return (uint64_t)RESTRICTED_SWITCH_CANDIDATES;
    if (host_n <= 14) return 32;
    if (host_n <= 20) return 256;
    return 2048;
}

/* The pattern path tracks the s-sets not yet covered (anchored_images_398) on parents of at least
   UNCOVERED_MIN_ORDER vertices, and tests them one by one once at most UNCOVERED_DIRECT remain.
   Speed choices only (measured on levels 12..18: the bookkeeping pays from about 15 vertices up);
   the family built is the same either way.  A test build may override both with -D. */
#ifndef UNCOVERED_MIN_ORDER
#define UNCOVERED_MIN_ORDER 15
#endif
#ifndef UNCOVERED_DIRECT
#define UNCOVERED_DIRECT 16
#endif
#define UNCOVERED_LIST (1 << 18)

_Static_assert(SG_MAX * (SG_MAX - 1) / 2 < SG_COUNT_CAP, "a search vertex has fewer triangles than the cap");
_Static_assert(SG_NB_HIGH < MAXV, "nbcount thresholds fit");

typedef struct {
    int n;
    int m;
    int ssize;                                   /* |S| of a pattern, 0 for a whole graph */
    int s_complete_depth;                        /* 1 + last search position in S, 0 if none */
    uint32_t smask;                              /* S, as search positions */
    unsigned char degree[SG_MAX];                /* per search position: */
    unsigned char triangles[SG_MAX];
    unsigned char squares[SG_MAX];
    unsigned char nbcount[SG_MAX][SG_NB_HIGH + 1];
    unsigned char ncons[SG_MAX];                 /* pair constraints with earlier positions */
    unsigned char cons_pos[SG_MAX][SG_MAX];
    unsigned char cons_type[SG_MAX][SG_MAX];
    unsigned char count_degree_at_least[SG_MAX + 1];
    uint32_t avoid_required;                     /* rooted graphs: positions kept out of R */
} SearchGraph;

typedef struct {
    SearchGraph forbidden[MAXF];    /* every forbidden graph, in data order */
    int forbidden_count;
    SearchGraph patterns[MAXPAT];   /* the first pattern of each Aut(F)-orbit class, in data order */
    int pattern_count;
    /* rooted[rooted_start[i] + j]: pattern i searched from its j-th S vertex (S in increasing
       label order), with the S vertices before it marked in avoid_required; see anchored_family_398 */
    SearchGraph *rooted;
    int rooted_start[MAXPAT];
    /* s_first[i]: pattern i searched with the vertices of S first (anchored_images_398) */
    SearchGraph s_first[MAXPAT];
    /* graph_class[i]: the isomorphism class of pattern i's graph F - v; patterns of one class
       differ only in S, and "F - v embeds in P" is one question for all of them */
    int graph_class[MAXPAT];
    int class_size[MAXPAT];
    int class_count;
} Search398;

typedef struct {
    int n;
    uint32_t pair[SG_PAIR_TYPES][MAXV];
    uint32_t degree_at_least[MAXV + 1];
    uint32_t triangles_at_least[SG_COUNT_CAP + 1];
    uint32_t squares_at_least[SG_COUNT_CAP + 1];
    uint32_t nbcount_at_least[SG_NB_HIGH + 1][MAXV + 1];
    unsigned char count_degree_at_least[MAXV + 1];
} HostTables;

/* A graph on 0..n-1 (adjacency adj, S = smask) relabelled to search positions: position k is
   order[k].  The search visits positions 0, 1, ..., n-1, i.e. exactly the old order. */
static void search_graph_build(SearchGraph *g, int n, int m, const uint32_t *adj, uint32_t smask,
                               const unsigned char *order)
{
    int k, j, t;
    if (n < 1 || n > SG_MAX) die("search graph order out of range");
    memset(g, 0, sizeof(*g));
    g->n = n;
    g->m = m;
    g->ssize = popcount32(smask);
    for (k = 0; k < n && k < SG_MAX; ++k) {
        int v = order[k];
        uint32_t nb = adj[v];
        int triangles = 0;
        int squares = 0;
        g->degree[k] = (unsigned char)popcount32(adj[v]);
        if (smask & (UINT32_C(1) << v)) {
            g->smask |= UINT32_C(1) << k;
            g->s_complete_depth = k + 1;
        }
        while (nb) {
            int b = ctz32(nb);
            nb &= nb - 1;
            triangles += popcount32(adj[v] & adj[b]);
            for (t = SG_NB_LOW; t <= SG_NB_HIGH; ++t)
                if (popcount32(adj[b]) >= t) ++g->nbcount[k][t];
        }
        g->triangles[k] = (unsigned char)(triangles / 2);
        for (j = 0; j < n; ++j) {
            int c = popcount32(adj[v] & adj[j]);
            if (j != v) squares += c * (c - 1) / 2;
        }
        /* a host count capped at SG_COUNT_CAP still bounds a search count below the cap */
        if (squares >= SG_COUNT_CAP) die("search graph has too many 4-cycles at a vertex");
        g->squares[k] = (unsigned char)squares;
        for (j = 0; j < k; ++j) {
            int u = order[j];
            int adjacent = (int)((adj[v] >> u) & 1);
            int c = popcount32(adj[u] & adj[v]);
            if (c > SG_CN_CAP) c = SG_CN_CAP;
            if (!adjacent && c == 0) continue;
            g->cons_pos[k][g->ncons[k]] = (unsigned char)j;
            g->cons_type[k][g->ncons[k]] = (unsigned char)((SG_CN_CAP + 1) * adjacent + c);
            ++g->ncons[k];
        }
    }
    for (t = 0; t <= SG_MAX; ++t)
        for (k = 0; k < n; ++k)
            if (g->degree[k] >= t) ++g->count_degree_at_least[t];
}

/* The orbits of Aut(F) on V(F); orbits[v] is the least vertex of v's orbit (nauty's convention). */
static void forbidden_orbits(const SmallGraph *f, int *orbits)
{
    graph g[MAXV];
    int lab[MAXV], ptn[MAXV];
    uint32_t adj[MAXV];
    statsblk stats;
    DEFAULTOPTIONS_GRAPH(options);
    int i;
    for (i = 0; i < f->n; ++i) adj[i] = f->adj[i];
    adjacency_to_nauty(adj, f->n, g);
    options.getcanon = FALSE;
    options.defaultptn = TRUE;
    densenauty(g, lab, ptn, orbits, &options, &stats, 1, f->n, NULL);
}

/* A search order that starts at root and continues like compute_order (most links to the chosen
   vertices, then highest degree, then lowest label).  Any order gives a complete search. */
static void rooted_order(const Pattern *p, int root, unsigned char *order)
{
    uint32_t chosen = UINT32_C(1) << root;
    int depth;
    order[0] = (unsigned char)root;
    for (depth = 1; depth < p->n; ++depth) {
        int best = -1, best_links = -1, best_degree = -1, v;
        for (v = 0; v < p->n; ++v) {
            int links, degree;
            if (chosen & (UINT32_C(1) << v)) continue;
            links = popcount32(p->adj[v] & chosen);
            degree = popcount32(p->adj[v]);
            if (links > best_links || (links == best_links && degree > best_degree)) {
                best = v;
                best_links = links;
                best_degree = degree;
            }
        }
        order[depth] = (unsigned char)best;
        chosen |= UINT32_C(1) << best;
    }
}

/* A search order with the vertices of S first (then the others), each step taking the vertex with
   the most links to the chosen ones, then the highest degree, then the lowest label. */
static void s_first_order(const Pattern *p, unsigned char *order)
{
    uint32_t chosen = 0;
    uint32_t all = ((UINT32_C(1) << (p->n - 1)) << 1) - 1;
    int depth;
    for (depth = 0; depth < p->n; ++depth) {
        uint32_t pool = (p->smask & ~chosen) ? (p->smask & ~chosen) : (all & ~chosen);
        int best = -1, best_links = -1, best_degree = -1;
        while (pool) {
            int v = ctz32(pool);
            int links = popcount32(p->adj[v] & chosen);
            int degree = popcount32(p->adj[v]);
            pool &= pool - 1;
            if (links > best_links || (links == best_links && degree > best_degree)) {
                best = v;
                best_links = links;
                best_degree = degree;
            }
        }
        order[depth] = (unsigned char)best;
        chosen |= UINT32_C(1) << best;
    }
}

typedef struct {
    int n;
    int index;
    graph rows[MAX_PATTERN_ORDER];   /* nauty's canonical form of the pattern's graph F - v */
} PatternGraphKey;

static int compare_pattern_graphs(const PatternGraphKey *a, const PatternGraphKey *b)
{
    int k;
    if (a->n != b->n) return a->n - b->n;
    for (k = 0; k < a->n; ++k)
        if (a->rows[k] != b->rows[k]) return a->rows[k] < b->rows[k] ? -1 : 1;
    return 0;
}

static int compare_pattern_keys(const void *aa, const void *bb)
{
    const PatternGraphKey *a = aa;
    const PatternGraphKey *b = bb;
    int c = compare_pattern_graphs(a, b);
    return c ? c : a->index - b->index;
}

/* The whole forbidden graphs are searched in compute_order, as contains_forbidden does; the
   patterns in their own p->order, as find_bad_matches does.  Of the patterns (F, v) only those with
   v least in its Aut(F)-orbit are kept (why that loses nothing: anchored_images_398).  Each kept
   pattern also gets one rooted copy per S vertex, used only for the family T, a copy searched
   with S first, used only by the direct tests (pattern_has_image), and the isomorphism class of
   its graph F - v (nauty canonical form), used by the existence cache. */
static void build_search_398(const ForbiddenData *data, Search398 *s)
{
    static int orbits[MAXF][MAXV];
    static PatternGraphKey keys[MAXPAT];
    int size_distribution[MAX_FORBIDDEN_ORDER];
    int i, rooted_count = 0;
    memset(s, 0, sizeof(*s));
    memset(size_distribution, 0, sizeof(size_distribution));
    for (i = 0; i < data->forbidden_count; ++i) {
        const SmallGraph *f = &data->forbidden[i];
        unsigned char order[MAX_FORBIDDEN_ORDER];
        forbidden_orbits(f, orbits[i]);
        compute_order(f->n, f->adj, order);
        search_graph_build(&s->forbidden[s->forbidden_count++], f->n, f->m, f->adj, 0, order);
    }
    for (i = 0; i < data->pattern_count; ++i)
        if (orbits[data->patterns[i].source][data->patterns[i].deleted] == data->patterns[i].deleted)
            rooted_count += data->patterns[i].ssize;
    s->rooted = xmalloc((size_t)rooted_count * sizeof(*s->rooted));
    rooted_count = 0;
    for (i = 0; i < data->pattern_count; ++i) {
        const Pattern *p = &data->patterns[i];
        uint32_t rest = p->smask;
        if (orbits[p->source][p->deleted] != p->deleted) continue;
        s->rooted_start[s->pattern_count] = rooted_count;
        while (rest) {
            int root = ctz32(rest);
            uint32_t before = p->smask & ((UINT32_C(1) << root) - 1);
            unsigned char order[MAX_PATTERN_ORDER];
            SearchGraph *g = &s->rooted[rooted_count++];
            int k;
            rest &= rest - 1;
            rooted_order(p, root, order);
            search_graph_build(g, p->n, p->m, p->adj, p->smask, order);
            for (k = 0; k < p->n; ++k)
                if (before & (UINT32_C(1) << order[k])) g->avoid_required |= UINT32_C(1) << k;
        }
        {
            graph canong[MAXV];
            int lab[MAXV], orb[MAXV];
            unsigned char order[MAX_PATTERN_ORDER];
            PatternGraphKey *key = &keys[s->pattern_count];
            canonicalize(p->adj, p->n, canong, lab, orb, 0);
            key->n = p->n;
            key->index = s->pattern_count;
            memcpy(key->rows, canong, (size_t)p->n * sizeof(graph));
            s_first_order(p, order);
            search_graph_build(&s->s_first[s->pattern_count], p->n, p->m, p->adj, p->smask, order);
        }
        search_graph_build(&s->patterns[s->pattern_count++], p->n, p->m, p->adj, p->smask, p->order);
        ++size_distribution[p->ssize];
    }
    if (s->pattern_count != SEARCH_398_PATTERNS ||
        memcmp(size_distribution, SEARCH_398_SIZE_DISTRIBUTION, sizeof(size_distribution)) != 0)
        die("forbidden set 398: the Aut(F)-orbit classes of the deletion patterns do not match "
            "the pinned statistics");
    /* isomorphism classes of the graphs F - v: equal canonical forms, found by sorting */
    qsort(keys, (size_t)s->pattern_count, sizeof(keys[0]), compare_pattern_keys);
    for (i = 0; i < s->pattern_count; ++i) {
        if (i == 0 || compare_pattern_graphs(&keys[i - 1], &keys[i]) != 0) ++s->class_count;
        s->graph_class[keys[i].index] = s->class_count - 1;
        ++s->class_size[s->class_count - 1];
    }
    if (s->class_count != SEARCH_398_GRAPH_CLASSES)
        die("forbidden set 398: the isomorphism classes of the pattern graphs do not match the "
            "pinned statistics");
}

/* popcount32 without a library call: the build has no -mpopcnt, so __builtin_popcount is a call
   to libgcc's __popcountdi2, which showed in the profile.  Same value, inline. */
static inline int bitcount32(uint32_t x)
{
    x = x - ((x >> 1) & UINT32_C(0x55555555));
    x = (x & UINT32_C(0x33333333)) + ((x >> 2) & UINT32_C(0x33333333));
    x = (x + (x >> 4)) & UINT32_C(0x0f0f0f0f);
    return (int)((x * UINT32_C(0x01010101)) >> 24);
}

static void host_tables_build(HostTables *h, const uint32_t *adj, int n)
{
    int degree[MAXV], triangles[MAXV], squares[MAXV];
    int a, b, t;
    memset(h, 0, sizeof(*h));
    h->n = n;
    for (a = 0; a < n; ++a) {
        degree[a] = bitcount32(adj[a]);
        triangles[a] = 0;
        squares[a] = 0;
    }
    for (a = 0; a < n; ++a) {
        for (b = a + 1; b < n; ++b) {
            int c = bitcount32(adj[a] & adj[b]);
            int adjacent = (int)((adj[a] >> b) & 1);
            squares[a] += c * (c - 1) / 2;
            squares[b] += c * (c - 1) / 2;
            if (adjacent) {
                triangles[a] += c;
                triangles[b] += c;
            }
            if (c > SG_CN_CAP) c = SG_CN_CAP;
            for (t = 1; t <= c; ++t) {
                h->pair[t][a] |= UINT32_C(1) << b;
                h->pair[t][b] |= UINT32_C(1) << a;
            }
            if (adjacent) {
                for (t = 0; t <= c; ++t) {
                    h->pair[(SG_CN_CAP + 1) + t][a] |= UINT32_C(1) << b;
                    h->pair[(SG_CN_CAP + 1) + t][b] |= UINT32_C(1) << a;
                }
            }
        }
    }
    for (a = 0; a < n; ++a) {
        int nbcount[SG_NB_HIGH + 1];
        uint32_t nb = adj[a];
        int tri = triangles[a] / 2;       /* each triangle at a is seen from both other corners */
        memset(nbcount, 0, sizeof(nbcount));
        while (nb) {
            b = ctz32(nb);
            nb &= nb - 1;
            for (t = SG_NB_LOW; t <= SG_NB_HIGH; ++t)
                if (degree[b] >= t) ++nbcount[t];
        }
        int sq = squares[a] > SG_COUNT_CAP ? SG_COUNT_CAP : squares[a];
        if (tri > SG_COUNT_CAP) tri = SG_COUNT_CAP;
        for (t = 0; t <= degree[a]; ++t) h->degree_at_least[t] |= UINT32_C(1) << a;
        for (t = 0; t <= tri; ++t) h->triangles_at_least[t] |= UINT32_C(1) << a;
        for (t = 0; t <= sq; ++t) h->squares_at_least[t] |= UINT32_C(1) << a;
        for (t = SG_NB_LOW; t <= SG_NB_HIGH; ++t) {
            int q;
            for (q = 0; q <= nbcount[t]; ++q) h->nbcount_at_least[t][q] |= UINT32_C(1) << a;
        }
    }
    for (t = 0; t <= MAXV; ++t)
        h->count_degree_at_least[t] = (unsigned char)bitcount32(h->degree_at_least[t]);
}

typedef struct {
    const SearchGraph *g;
    const HostTables *h;
    uint32_t vertex_mask[SG_MAX];   /* host vertices passing the per-vertex filters, per position */
    int map[SG_MAX];
    uint32_t force_mask;            /* anchored images only */
    int max_bad_size;
    BadFamily *family;
} SearchContext;

/* Prepare the search of g in the host; 0 if a filter already shows that g does not embed. */
static int search_prepare(SearchContext *c, const SearchGraph *g, int host_m)
{
    const HostTables *h = c->h;
    int k, t;
    if (g->n > h->n || g->m > host_m) return 0;
    for (t = 1; t <= SG_MAX; ++t)
        if (g->count_degree_at_least[t] > h->count_degree_at_least[t]) return 0;
    c->g = g;
    for (k = 0; k < g->n; ++k) {
        uint32_t mask = h->degree_at_least[g->degree[k]] & h->triangles_at_least[g->triangles[k]] &
                        h->squares_at_least[g->squares[k]];
        for (t = SG_NB_LOW; t <= SG_NB_HIGH; ++t) mask &= h->nbcount_at_least[t][g->nbcount[k][t]];
        if (!mask) return 0;
        c->vertex_mask[k] = mask;
    }
    return 1;
}

/* Host vertices position `depth` may take, given the map of the earlier positions: the old
   candidates (unused, adjacent to the images of earlier neighbours, degree) cut by the filters.
   Increasing index order, as in exists_match and find_bad_matches. */
static uint32_t search_candidates(const SearchContext *c, int depth, uint32_t used)
{
    const SearchGraph *g = c->g;
    uint32_t candidates = c->vertex_mask[depth] & ~used;
    int q;
    for (q = 0; q < g->ncons[depth] && candidates; ++q)
        candidates &= c->h->pair[g->cons_type[depth][q]][c->map[g->cons_pos[depth][q]]];
    return candidates;
}

static int search_exists(SearchContext *c, int depth, uint32_t used)
{
    uint32_t candidates;
    if (depth == c->g->n) return 1;
    candidates = search_candidates(c, depth, used);
    while (candidates) {
        int hv = ctz32(candidates);
        candidates &= candidates - 1;
        c->map[depth] = hv;
        if (search_exists(c, depth + 1, used | (UINT32_C(1) << hv))) return 1;
    }
    return 0;
}

/* contains_forbidden for set 398: the same graphs in the same order, each searched completely
   (the filters discard only branches without an embedding), so the same answer.  h describes the
   host (P, or a child), m its edge count. */
static int contains_forbidden_398(const Search398 *s, const HostTables *h, int m)
{
    SearchContext c;
    int i;
    memset(&c, 0, sizeof(c));
    c.h = h;
    for (i = 0; i < s->forbidden_count; ++i) {
        if (!search_prepare(&c, &s->forbidden[i], m)) continue;
        if (search_exists(&c, 0, 0)) return 1;
    }
    return 0;
}

/* One pattern's part of build_bad_family for set 398.  find_bad_matches visits the embeddings of
   F - v in lexicographic order of (position 0's image, position 1's image, ...) with the positions
   in p->order and each image in increasing index, and at each embedding (a leaf) adds
   image = psi(S) | force when |image| <= max_bad_size and no set of the family lies in it.  This
   search visits positions in the same order with candidates in the same order, so its leaves are
   a subsequence of those, and it only leaves out leaves at which find_bad_matches adds nothing:
     (a) branches without an embedding (the filters);
     (b) when an S vertex is placed and the S vertices placed so far, with force, already make more
         than max_bad_size vertices or contain a set of the family: every image below contains
         that partial image, so it is oversized, or it is covered at the time of the leaf (the
         family only grows; find_bad_matches's own test at s_complete_depth is the case where the
         partial image is the whole image);
     (c) at a node at depth >= s_complete_depth, where every S vertex is placed, once one leaf below
         has been found: every leaf below has that leaf's image, which it has just added or found
         covered, so find_bad_matches adds nothing at the rest.
   By induction over the leaves in order, the family is the same at every leaf both visit, so the
   additions are the same sets in the same order.  At depth >= s_complete_depth, returns 1 iff a
   leaf was found below; above that depth it returns 0 (the value is used only by (c)). */
static int search_images(SearchContext *c, int depth, uint32_t used, uint32_t image)
{
    const SearchGraph *g = c->g;
    uint32_t candidates;
    int in_s;
    if (depth == g->n) {
        uint32_t full = image | c->force_mask;
        if (bitcount32(full) <= c->max_bad_size) bad_family_add(c->family, full);
        return 1;
    }
    candidates = search_candidates(c, depth, used);
    in_s = (int)((g->smask >> depth) & 1);
    while (candidates) {
        int hv = ctz32(candidates);
        uint32_t next_image = image;
        candidates &= candidates - 1;
        if (in_s) {
            uint32_t full;
            next_image |= UINT32_C(1) << hv;
            full = next_image | c->force_mask;
            if (bitcount32(full) > c->max_bad_size || bad_family_contains_subset(c->family, full))
                continue;
        }
        c->map[depth] = hv;
        if (search_images(c, depth + 1, used | (UINT32_C(1) << hv), next_image) &&
            depth >= g->s_complete_depth)
            return 1;
    }
    return 0;
}

/* One anchored test: does pattern i have an embedding with S mapped onto the s-set target (s = |S|)?
   The S-first copy is searched with the S positions restricted to target; an injective map of S
   into a set of |S| vertices is onto it, so this is exactly "target is an image of pattern i". */
static int pattern_has_image(const Search398 *s, const HostTables *h, int host_m, int i, uint32_t target)
{
    SearchContext t;
    const SearchGraph *g = &s->s_first[i];
    int k;
    memset(&t, 0, sizeof(t));
    t.h = h;
    if (!search_prepare(&t, g, host_m)) return 0;
    for (k = 0; k < g->ssize; ++k) {
        t.vertex_mask[k] &= target;
        if (!t.vertex_mask[k]) return 0;
    }
    return search_exists(&t, 0, 0);
}

/* build_bad_family's pattern loop for set 398 (build_bad_family itself also resets the family).
   The same patterns in the same order, less kinds that add nothing:
     - a pattern failing the size tests (n, m, |S| > max_bad_size, as build_bad_family), the count
       test or a per-vertex filter: it has no embedding, or only oversized images;
     - a pattern (F, v') whose v' is not least in its Aut(F)-orbit.  With v the least vertex of
       that orbit and sigma in Aut(F), sigma(v) = v', the restriction of sigma is an isomorphism
       F - v -> F - v' taking N_F(v) onto N_F(v'), so psi -> psi o sigma^-1 maps the embeddings of
       (F, v) onto those of (F, v') with the same images.  (F, v) sorts before (F, v'): same |S|,
       edges, order and source, smaller deleted vertex.  Once (F, v) is searched, each of its
       images (none oversized: |S| <= max_bad_size) is in the family or covered, and so is each
       image of (F, v'), which therefore adds nothing.
     - a pattern whose graph F - v does not embed in P at all.  Patterns whose graphs are
       isomorphic (graph_class, different S) ask the same question, so it is answered once per call
       and class by a complete search (search_exists), or by search_prepare failing, whose tests
       (sizes, degree counts, per-vertex filters) are isomorphism invariants; a pattern without an
       embedding has no image and adds nothing.  Classes of one pattern skip the extra search.
     - every pattern once no s-set is left uncovered, s the |S| of the current patterns.  The
       patterns come in order of |S| and a pattern adds only sets of its size |S| (force is 0), so
       while the patterns of size s run, every addition is an s-set that was not covered, and it
       covers no other s-set: the number of uncovered s-sets, counted when size s begins, falls by
       exactly one per addition.  At 0 every s-set is covered, so is every larger set (it contains
       an s-set), and so is every image of every remaining pattern.
   And a pattern may be replaced by direct tests while at most UNCOVERED_DIRECT s-sets are
   uncovered (their list is refreshed from the family when needed).  The sets the pattern adds are
   exactly its images among those uncovered s-sets U (an image is added iff it is not covered, and
   s-sets do not cover one another); pattern_has_image finds them.  None: the pattern adds nothing.
   One: it adds that set alone, which bad_family_add does here.  Two or more: search_images runs as
   usual and adds them in its own order.
   With search_images this makes the same additions as build_bad_family in the same order. */
static void anchored_images_398(const Search398 *s, const HostTables *h, int host_m,
                                int max_bad_size, BadFamily *family)
{
    static signed char embeds[MAXPAT];   /* per class: 0 unknown, 1 embeds, -1 does not */
    static uint32_t uncovered[UNCOVERED_LIST];
    SearchContext c;
    size_t listed = 0;                   /* uncovered s-sets on the list (valid when tracking) */
    size_t start_uncovered = 0, start_count = 0, listed_at = 0;
    int tracking = 0;                    /* the uncovered s-sets are counted for this size */
    int size = -1;
    int i;
    memset(&c, 0, sizeof(c));
    memset(embeds, 0, (size_t)s->class_count);
    c.h = h;
    c.force_mask = 0;
    c.max_bad_size = max_bad_size;
    c.family = family;
    for (i = 0; i < s->pattern_count; ++i) {
        const SearchGraph *g = &s->patterns[i];
        int cls = s->graph_class[i];
        size_t left = 0;
        if (g->ssize > max_bad_size) continue;
        if (g->ssize != size) {
            size = g->ssize;
            tracking = h->n >= UNCOVERED_MIN_ORDER && choose_table[h->n][size] <= UNCOVERED_LIST;
            listed = 0;
            if (tracking) {
                uint32_t mask = (UINT32_C(1) << size) - 1;
                uint32_t limit = UINT32_C(1) << h->n;
                while (mask < limit) {
                    if (!bad_family_contains_subset(family, mask)) uncovered[listed++] = mask;
                    {
                        uint32_t low = mask & (uint32_t)(-(int32_t)mask);
                        uint32_t next = mask + low;
                        mask = next | (((mask ^ next) >> 2) / low);
                    }
                }
            }
            start_uncovered = listed;
            start_count = family->count;
            listed_at = family->count;
        }
        if (tracking) {
            if (family->count - start_count > start_uncovered)
                die("forbidden set 398: more additions than uncovered sets");
            left = start_uncovered - (family->count - start_count);
            if (left <= UNCOVERED_DIRECT && listed_at != family->count) {
                /* refresh the list from the family; it must agree with the count */
                size_t a, b = 0;
                for (a = 0; a < listed; ++a)
                    if (!bad_family_contains_subset(family, uncovered[a])) uncovered[b++] = uncovered[a];
                listed = b;
                listed_at = family->count;
                if (listed != left) die("forbidden set 398: uncovered set count does not match the family");
            }
            if (left == 0) break;
        }
        if (embeds[cls] < 0) continue;
        if (!search_prepare(&c, g, host_m)) {
            embeds[cls] = -1;
            continue;
        }
        if (embeds[cls] == 0 && s->class_size[cls] > 1) {
            embeds[cls] = search_exists(&c, 0, 0) ? 1 : -1;
            if (embeds[cls] < 0) continue;
        }
        if (tracking && left <= UNCOVERED_DIRECT) {
            uint32_t found = 0;
            int images = 0;
            size_t u;
            for (u = 0; u < listed && images < 2; ++u) {
                if (pattern_has_image(s, h, host_m, i, uncovered[u])) {
                    found = uncovered[u];
                    ++images;
                }
            }
            if (images == 0) continue;
            if (images == 1) {
                bad_family_add(family, found);
                continue;
            }
        }
        search_images(&c, 0, 0, 0);
    }
}

/* The family T of build_restricted_bad_family_398, for the parent in h, required = R and
   d = max_bad_size.  Only coverage matters for T (never the order of its sets), and T must
     (i)  consist of sets image | R of size <= d, image = psi(S) for an embedding psi of a pattern;
     (ii) cover every such set.
   (i) holds because a set is added only at an embedding, and only when its size is <= d.  For
   (ii) take a pattern (F, v) and psi with |psi(S) | R| <= d.  The pattern is searched here unless
   it is not kept, and then an earlier kept pattern has the same images (anchored_images_398), or
   |S| > d, and then no image | R fits.  The searches prune only branches that hold no embedding
   (the filters), whose images | R all exceed d (the size bound), whose images | R all contain a
   set already in T (T only grows), or, after one embedding, whose embeddings all have its image
   (search_images).  Which embeddings are visited:
     |S| <= d - |R|: the search from the pattern's own order visits all of them;
     |S| >  d - |R|: then psi(S) meets R, since |psi(S) - R| <= d - |R| < |S|.  Let u be the
       least-labelled vertex of S with psi(u) in R.  The rooted copy starting at u, with its
       first position restricted to R and the S vertices below u kept out of R, visits psi.  The
       restrictions only remove candidates, so the rooted searches visit nothing else. */
static void anchored_family_398(const Search398 *s, const HostTables *h, int host_m,
                                int max_bad_size, uint32_t required, BadFamily *family)
{
    static signed char embeds[MAXPAT];   /* per graph class, as in anchored_images_398 */
    SearchContext c;
    int slack = max_bad_size - popcount32(required);
    int i, j, k;
    memset(&c, 0, sizeof(c));
    memset(embeds, 0, (size_t)s->class_count);
    c.h = h;
    c.force_mask = required;
    c.max_bad_size = max_bad_size;
    c.family = family;
    for (i = 0; i < s->pattern_count; ++i) {
        const SearchGraph *g = &s->patterns[i];
        int cls = s->graph_class[i];
        if (g->ssize > max_bad_size || embeds[cls] < 0) continue;
        if (embeds[cls] == 0 && s->class_size[cls] > 1) {
            /* a graph that does not embed in P has no image (anchored_images_398) */
            embeds[cls] = search_prepare(&c, g, host_m) && search_exists(&c, 0, 0) ? 1 : -1;
            if (embeds[cls] < 0) continue;
        }
        if (g->ssize <= slack) {
            if (search_prepare(&c, g, host_m)) search_images(&c, 0, 0, 0);
            continue;
        }
        for (j = 0; j < g->ssize; ++j) {
            const SearchGraph *rooted = &s->rooted[s->rooted_start[i] + j];
            int empty = 0;
            /* the per-vertex filters do not depend on the order: if one fails, all roots fail */
            if (!search_prepare(&c, rooted, host_m)) break;
            c.vertex_mask[0] &= required;
            for (k = 1; k < rooted->n; ++k)
                if (rooted->avoid_required & (UINT32_C(1) << k)) c.vertex_mask[k] &= ~required;
            for (k = 0; k < rooted->n; ++k)
                if (!c.vertex_mask[k]) empty = 1;
            if (!empty) search_images(&c, 0, 0, 0);
        }
    }
}

/* build_restricted_bad_family for set 398.  The old function visits the candidates M
   (required = R subset of M, s0 = max(|R|, 2) <= |M| <= d, by size, each size in increasing
   numeric order), skips M if a set already in the family lies in it, and otherwise adds M iff
   child(M) contains a forbidden graph.  This function runs the SAME loop and replaces only that
   test, by one with the same answer:

     child(M) contains a forbidden graph  iff  P contains one, or some pattern (F, v) has an
     embedding psi of F - v in P with psi(S) inside M.
   (An embedding of F in child(M) avoids w, and then lies in P, or sends some v to w; then its
   restriction to F - v lies in P and sends N_F(v) into N(w) = M.  Conversely each kind extends
   to an embedding of F, sending v to w.)

   First the test is contains_forbidden_398 on child(M) itself.  The first time it answers "no",
   child(M) is free of the 398, and so is its subgraph P.  From then on (and from the start when
   --verify-parents has already shown P free) it may be "M contains a set of T", T built by
   anchored_family_398: sets image | R of size <= d, covering every such set (all patterns,
   through the orbit classes).  For M containing R with |M| <= d, some image lies in M iff some
   image | R does, iff (the size bound holds inside M) M contains a set of T.  The switch is made
   only when at least restricted_switch_threshold(n) candidates remain, a speed choice that cannot
   change any answer; the family is the old one, set for set and in order. */
static void build_restricted_bad_family_398(const Search398 *s, const uint32_t *host_adj,
                                            const HostTables *host, int host_n, int host_m,
                                            int max_bad_size, uint32_t required,
                                            int parent_known_free, BadFamily *bad,
                                            BadFamily *anchored)
{
    int r = popcount32(required);
    int size;
    uint64_t total = 0;
    uint64_t visited = 0;
    int use_anchored = 0;
    uint64_t threshold = restricted_switch_threshold(host_n);
    bad_family_reset(bad);
    for (size = r > 2 ? r : 2; size <= max_bad_size; ++size)
        total += choose_table[host_n - r][size - r];
    if (parent_known_free && total >= threshold) {
        bad_family_reset(anchored);
        anchored_family_398(s, host, host_m, max_bad_size, required, anchored);
        use_anchored = 1;
    }
    for (size = r > 2 ? r : 2; size <= max_bad_size; ++size) {
        uint32_t mask = (UINT32_C(1) << size) - 1;
        uint32_t limit = UINT32_C(1) << host_n;
        while (mask < limit) {
            if ((mask & required) == required) {
                ++visited;
                if (!bad_family_contains_subset(bad, mask)) {
                    if (use_anchored) {
                        if (bad_family_contains_subset(anchored, mask)) bad_family_add(bad, mask);
                    } else {
                        uint32_t child_adj[MAXV];
                        HostTables child;
                        int i;
                        for (i = 0; i < host_n; ++i) child_adj[i] = host_adj[i];
                        child_adj[host_n] = 0;
                        for (i = 0; i < host_n; ++i) {
                            if (mask & (UINT32_C(1) << i)) {
                                child_adj[i] |= UINT32_C(1) << host_n;
                                child_adj[host_n] |= UINT32_C(1) << i;
                            }
                        }
                        host_tables_build(&child, child_adj, host_n + 1);
                        if (contains_forbidden_398(s, &child, host_m + size)) {
                            bad_family_add(bad, mask);
                        } else if (total - visited >= threshold) {
                            bad_family_reset(anchored);
                            anchored_family_398(s, host, host_m, max_bad_size, required, anchored);
                            use_anchored = 1;
                        }
                    }
                }
            }
            {
                uint32_t low = mask & (uint32_t)(-(int32_t)mask);
                uint32_t next = mask + low;
                mask = next | (((mask ^ next) >> 2) / low);
            }
        }
    }
}

/* ======================================= end set 398 ========================================= */

static size_t __attribute__((unused)) rank_combination(uint32_t mask)
{
    size_t rank = 0;
    int ordinal = 1;
    while (mask) {
        int pos = ctz32(mask);
        mask &= mask - 1;
        rank += (size_t)choose_table[pos][ordinal];
        ++ordinal;
    }
    return rank;
}

static uint32_t permute_mask(uint32_t mask, const int *perm)
{
    uint32_t result = 0;
    while (mask) {
        int v = ctz32(mask);
        mask &= mask - 1;
        result |= UINT32_C(1) << perm[v];
    }
    return result;
}

static size_t dsu_find(size_t *parent, size_t x)
{
    size_t root = x;
    while (parent[root] != root) root = parent[root];
    while (parent[x] != x) {
        size_t next = parent[x];
        parent[x] = root;
        x = next;
    }
    return root;
}

static void dsu_union(size_t *parent, size_t a, size_t b)
{
    a = dsu_find(parent, a);
    b = dsu_find(parent, b);
    if (a == b) return;
    if (a < b) parent[b] = a;
    else parent[a] = b;
}

typedef struct {
    uint32_t *masks;
    size_t *parent;
    uint32_t *minimum;
    size_t count;
} NeighbourhoodOrbits;

static size_t find_mask_index(const uint32_t *masks, size_t count, uint32_t target)
{
    size_t low = 0;
    size_t high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (masks[middle] < target) low = middle + 1;
        else high = middle;
    }
    if (low >= count || masks[low] != target) die("automorphism left the neighbourhood domain");
    return low;
}

static void build_neighbourhood_orbits(int n, int d, uint32_t required,
                                       const BadFamily *bad,
                                       NeighbourhoodOrbits *o)
{
    uint32_t mask;
    size_t i;
    int g;
    memset(o, 0, sizeof(*o));
    {
        size_t domain_count = (size_t)choose_table[n - popcount32(required)][d - popcount32(required)];
        o->masks = xmalloc(domain_count * sizeof(*o->masks));
        o->parent = xmalloc(domain_count * sizeof(*o->parent));
        o->minimum = xmalloc(domain_count * sizeof(*o->minimum));
    }
    if (d == 0) {
        if (!bad_family_contains_subset(bad, 0)) o->masks[o->count++] = 0;
    } else {
        uint32_t limit = UINT32_C(1) << n;
        mask = (UINT32_C(1) << d) - 1;
        while (mask < limit) {
            if ((mask & required) == required &&
                !bad_family_contains_subset(bad, mask)) o->masks[o->count++] = mask;
            {
                uint32_t low = mask & (uint32_t)(-(int32_t)mask);
                uint32_t next = mask + low;
                mask = next | (((mask ^ next) >> 2) / low);
            }
        }
    }
    for (i = 0; i < o->count; ++i) o->parent[i] = i;
    for (g = 0; g < aut_gen_count; ++g) {
        for (i = 0; i < o->count; ++i) {
            uint32_t image = permute_mask(o->masks[i], aut_gens[g]);
            size_t j = find_mask_index(o->masks, o->count, image);
            if (j >= o->count || o->masks[j] != image) die("combination rank mismatch");
            dsu_union(o->parent, i, j);
        }
    }
    for (i = 0; i < o->count; ++i) o->minimum[i] = UINT32_MAX;
    for (i = 0; i < o->count; ++i) {
        size_t root = dsu_find(o->parent, i);
        if (o->masks[i] < o->minimum[root]) o->minimum[root] = o->masks[i];
    }
}

static int is_neighbourhood_representative(NeighbourhoodOrbits *o, size_t i)
{
    size_t root = dsu_find(o->parent, i);
    return o->masks[i] == o->minimum[root];
}

static void free_neighbourhood_orbits(NeighbourhoodOrbits *o)
{
    free(o->masks);
    free(o->parent);
    free(o->minimum);
}

static int child_canonical_accept(const uint32_t *parent_adj, int parent_n,
                                  uint32_t neighbourhood, FILE *out,
                                  int skip_test)
{
    uint32_t adj[MAXV];
    unsigned char degree[MAXV];
    graph canong[MAXV];
    int lab[MAXV], orbits[MAXV];
    int n = parent_n + 1;
    int new_vertex = parent_n;
    int i;
    int delta = INT_MAX;
    int canonical_minimum = -1;
    for (i = 0; i < parent_n; ++i) adj[i] = parent_adj[i];
    adj[new_vertex] = 0;
    for (i = 0; i < parent_n; ++i) {
        if (neighbourhood & (UINT32_C(1) << i)) {
            adj[i] |= UINT32_C(1) << new_vertex;
            adj[new_vertex] |= UINT32_C(1) << i;
        }
    }
    for (i = 0; i < n; ++i) {
        degree[i] = (unsigned char)popcount32(adj[i]);
        if (degree[i] < delta) delta = degree[i];
    }
    canonicalize(adj, n, canong, lab, orbits, 0);
    if (!skip_test) {
        for (i = 0; i < n; ++i) {
            if (degree[lab[i]] == delta) {
                canonical_minimum = lab[i];
                break;
            }
        }
        if (canonical_minimum < 0) die("failed to locate canonical minimum-degree vertex");
        if (orbits[new_vertex] != orbits[canonical_minimum]) return 0;
    }
    if (fputs(ntog6(canong, 1, n), out) == EOF) die_errno("write child graph6");
    return 1;
}

static void canonical_parent_and_group(const uint32_t *adj, int n,
                                       const char *input_g6)
{
    graph canong[MAXV];
    int lab[MAXV], orbits[MAXV];
    const char *canonical;
    canonicalize(adj, n, canong, lab, orbits, 1);
    canonical = ntog6(canong, 1, n);
    if (strncmp(canonical, input_g6, strlen(input_g6)) != 0 ||
        (canonical[strlen(input_g6)] != '\n' && canonical[strlen(input_g6)] != '\0')) {
        fprintf(stderr, "udenum: noncanonical parent record: %s\n", input_g6);
        exit(2);
    }
}

static int minimum_degree(const uint32_t *adj, int n, uint32_t *minimum_vertices)
{
    int delta = n;
    int i;
    uint32_t vertices = 0;
    for (i = 0; i < n; ++i) {
        int d = popcount32(adj[i]);
        if (d < delta) {
            delta = d;
            vertices = UINT32_C(1) << i;
        } else if (d == delta) {
            vertices |= UINT32_C(1) << i;
        }
    }
    *minimum_vertices = vertices;
    return delta;
}

static long count_graph_records(const char *path)
{
    FILE *f = fopen(path, "r");
    char *line = NULL;
    size_t capacity = 0;
    ssize_t length;
    long count = 0;
    if (!f) die_errno(path);
    while ((length = getline(&line, &capacity, f)) >= 0) {
        if (length == 0 || line[0] == '\n' || line[0] == '\r') continue;
        if (strncmp(line, ">>graph6<<", 10) == 0) continue;
        ++count;
    }
    if (ferror(f)) die_errno("read parent file");
    free(line);
    if (fclose(f) != 0) die_errno("close parent file");
    return count;
}

static void trim_line(char *line)
{
    size_t n = strlen(line);
    while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = '\0';
}

static void process_parent(const Config *cfg, const ForbiddenData *data,
                           const Search398 *search, BadFamily *bad, BadFamily *anchored,
                           const uint32_t *adj, int parent_n,
                           int parent_m, const char *input_g6, FILE *out,
                           RunStats *stats)
{
    int d = cfg->target_m - parent_m;
    int delta;
    uint32_t minimum_vertices;
    uint32_t required = 0;
    NeighbourhoodOrbits neighbourhoods;
    size_t i;
    HostTables host;

    if (parent_n + 1 != cfg->target_n) die("parent order does not match target order");
    if (d < 0 || d > parent_n) return;
    canonical_parent_and_group(adj, parent_n, input_g6);
    if (cfg->forbidden_set == 398) host_tables_build(&host, adj, parent_n);
    if (cfg->verify_parents &&
        (cfg->forbidden_set == 398 ? contains_forbidden_398(search, &host, parent_m)
                                   : contains_forbidden(data, adj, parent_n, parent_m)))
        die("parent file contains a forbidden graph");
    delta = minimum_degree(adj, parent_n, &minimum_vertices);
    if (delta <= d - 2) {
        ++stats->parents_degree_skipped;
        return;
    }
    if (delta == d - 1) {
        required = minimum_vertices;
        if (popcount32(required) > d) {
            ++stats->parents_degree_skipped;
            return;
        }
    }
    ++stats->parents_processed;
    if (cfg->forbidden_set == 398) {
        if (required) {
            build_restricted_bad_family_398(search, adj, &host, parent_n, parent_m, d, required,
                                            cfg->verify_parents, bad, anchored);
        } else {
            bad_family_reset(bad);
            anchored_images_398(search, &host, parent_m, d, bad);
        }
    } else if (required) {
        build_restricted_bad_family(data, adj, parent_n, parent_m, d, required, bad);
    } else {
        build_bad_family(data, adj, parent_n, parent_m, d, 0, bad);
    }
    if (cfg->mutation_drop_first_badset) bad_family_drop_first(bad);
    stats->bad_sets += bad->count;
    {
        size_t domain_count = (size_t)choose_table[parent_n - popcount32(required)]
                                                 [d - popcount32(required)];
        build_neighbourhood_orbits(parent_n, d, required, bad, &neighbourhoods);
        stats->neighbourhoods += domain_count;
        stats->neighbourhoods_bad += domain_count - neighbourhoods.count;
    }
    for (i = 0; i < neighbourhoods.count; ++i) {
        uint32_t mask = neighbourhoods.masks[i];
        if (!is_neighbourhood_representative(&neighbourhoods, i)) continue;
        ++stats->neighbourhood_orbit_reps;
        if ((mask & required) != required) continue;
        if (child_canonical_accept(adj, parent_n, mask, out,
                                   cfg->mutation_no_child_orbit)) {
            ++stats->children_written;
        } else {
            ++stats->child_orbit_rejected;
        }
    }
    free_neighbourhood_orbits(&neighbourhoods);
}

static void filter_graph(const Config *cfg, const ForbiddenData *data,
                         const Search398 *search, const uint32_t *adj, int n, int m, FILE *out,
                         RunStats *stats)
{
    graph canong[MAXV];
    int lab[MAXV], orbits[MAXV];
    HostTables host;
    if (n != cfg->target_n || m != cfg->target_m)
        die("filter input does not match --n and --m");
    ++stats->parents_processed;
    if (n == 0) {
        if (fputs("?\n", out) == EOF) die_errno("write filtered graph6");
        ++stats->children_written;
        return;
    }
    if (cfg->forbidden_set == 398) host_tables_build(&host, adj, n);
    if (cfg->forbidden_set == 398 ? contains_forbidden_398(search, &host, m)
                                  : contains_forbidden(data, adj, n, m)) {
        ++stats->neighbourhoods_bad;
        return;
    }
    canonicalize(adj, n, canong, lab, orbits, 0);
    if (fputs(ntog6(canong, 1, n), out) == EOF) die_errno("write filtered graph6");
    ++stats->children_written;
}

/* Compact SHA-256 implementation for reproducible manifests. */
typedef struct {
    uint32_t h[8];
    uint64_t bytes;
    unsigned char block[64];
    size_t used;
} Sha256;

static uint32_t rotr32(uint32_t x, unsigned n)
{
    return (x >> n) | (x << (32 - n));
}

static void sha256_transform(Sha256 *s, const unsigned char *block)
{
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
    uint32_t w[64];
    uint32_t a,b,c,d,e,f,g,h;
    int i;
    for (i = 0; i < 16; ++i)
        w[i] = ((uint32_t)block[4*i] << 24) | ((uint32_t)block[4*i+1] << 16) |
               ((uint32_t)block[4*i+2] << 8) | block[4*i+3];
    for (i = 16; i < 64; ++i) {
        uint32_t s0 = rotr32(w[i-15],7) ^ rotr32(w[i-15],18) ^ (w[i-15] >> 3);
        uint32_t s1 = rotr32(w[i-2],17) ^ rotr32(w[i-2],19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    a=s->h[0]; b=s->h[1]; c=s->h[2]; d=s->h[3];
    e=s->h[4]; f=s->h[5]; g=s->h[6]; h=s->h[7];
    for (i = 0; i < 64; ++i) {
        uint32_t s1 = rotr32(e,6) ^ rotr32(e,11) ^ rotr32(e,25);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t t1 = h + s1 + ch + k[i] + w[i];
        uint32_t s0 = rotr32(a,2) ^ rotr32(a,13) ^ rotr32(a,22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = s0 + maj;
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    s->h[0]+=a; s->h[1]+=b; s->h[2]+=c; s->h[3]+=d;
    s->h[4]+=e; s->h[5]+=f; s->h[6]+=g; s->h[7]+=h;
}

static void sha256_init(Sha256 *s)
{
    static const uint32_t initial[8] = {
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    };
    memcpy(s->h, initial, sizeof(initial));
    s->bytes = 0;
    s->used = 0;
}

static void sha256_update(Sha256 *s, const unsigned char *data, size_t len)
{
    s->bytes += len;
    while (len) {
        size_t take = 64 - s->used;
        if (take > len) take = len;
        memcpy(s->block + s->used, data, take);
        s->used += take;
        data += take;
        len -= take;
        if (s->used == 64) {
            sha256_transform(s, s->block);
            s->used = 0;
        }
    }
}

static void sha256_final(Sha256 *s, unsigned char digest[32])
{
    uint64_t bits = s->bytes * 8;
    int i;
    s->block[s->used++] = 0x80;
    if (s->used > 56) {
        while (s->used < 64) s->block[s->used++] = 0;
        sha256_transform(s, s->block);
        s->used = 0;
    }
    while (s->used < 56) s->block[s->used++] = 0;
    for (i = 7; i >= 0; --i) s->block[s->used++] = (unsigned char)(bits >> (8*i));
    sha256_transform(s, s->block);
    for (i = 0; i < 8; ++i) {
        digest[4*i] = (unsigned char)(s->h[i] >> 24);
        digest[4*i+1] = (unsigned char)(s->h[i] >> 16);
        digest[4*i+2] = (unsigned char)(s->h[i] >> 8);
        digest[4*i+3] = (unsigned char)s->h[i];
    }
}

static void sha256_hex_buffer(const unsigned char *bytes, size_t len, char hex[65])
{
    unsigned char digest[32];
    int i;
    Sha256 s;
    sha256_init(&s);
    sha256_update(&s, bytes, len);
    sha256_final(&s, digest);
    for (i = 0; i < 32; ++i) sprintf(hex + 2*i, "%02x", digest[i]);
    hex[64] = '\0';
}

static void sha256_file(const char *path, char hex[65])
{
    unsigned char buf[65536];
    unsigned char digest[32];
    size_t got;
    int i;
    Sha256 s;
    FILE *f = fopen(path, "rb");
    if (!f) die_errno(path);
    sha256_init(&s);
    while ((got = fread(buf, 1, sizeof(buf), f)) != 0) sha256_update(&s, buf, got);
    if (ferror(f)) die_errno("hash read");
    if (fclose(f) != 0) die_errno("hash close");
    sha256_final(&s, digest);
    for (i = 0; i < 32; ++i) sprintf(hex + 2*i, "%02x", digest[i]);
    hex[64] = '\0';
}

static void json_string(FILE *f, const char *s)
{
    const unsigned char *p = (const unsigned char *)s;
    fputc('"', f);
    while (*p) {
        if (*p == '"' || *p == '\\') fprintf(f, "\\%c", *p);
        else if (*p == '\n') fputs("\\n", f);
        else if (*p == '\r') fputs("\\r", f);
        else if (*p == '\t') fputs("\\t", f);
        else if (*p < 0x20) fprintf(f, "\\u%04x", *p);
        else fputc(*p, f);
        ++p;
    }
    fputc('"', f);
}

static void utc_timestamp(time_t value, char out[32])
{
    struct tm tm_value;
    if (!gmtime_r(&value, &tm_value)) die("gmtime_r failed");
    if (strftime(out, 32, "%Y-%m-%dT%H:%M:%SZ", &tm_value) == 0)
        die("strftime failed");
}

static void write_manifest(const Config *cfg, long range_end,
                           const char *started, const char *finished,
                           uint64_t children_written)
{
    FILE *f;
    char hash[65];
    char hostname[256];
    int i;
    if (gethostname(hostname, sizeof(hostname)) != 0) die_errno("gethostname");
    hostname[sizeof(hostname)-1] = '\0';
    f = fopen(cfg->manifest, "w");
    if (!f) die_errno(cfg->manifest);
    fputs("{\n  \"shard_id\": ", f); json_string(f, cfg->shard_id);
    fputs(",\n  \"parent_file\": ", f); json_string(f, cfg->parents);
    fprintf(f, ",\n  \"parent_range\": [%ld, %ld],", cfg->start, range_end);
    fputs("\n  \"software_sha256\": {", f);
    sha256_file("/proc/self/exe", hash);
    fputs("\n    \"udenum\": ", f); json_string(f, hash);
    for (i = 0; i < cfg->software_count; ++i) {
        sha256_file(cfg->software[i].path, hash);
        fputs(",\n    ", f); json_string(f, cfg->software[i].name);
        fputs(": ", f); json_string(f, hash);
    }
    fputs("\n  },\n  \"inputs_sha256\": {\n    ", f);
    json_string(f, cfg->parents); fputs(": ", f); sha256_file(cfg->parents, hash); json_string(f, hash);
    fputs(",\n    ", f); json_string(f, cfg->forbidden); fputs(": ", f);
    sha256_file(cfg->forbidden, hash); json_string(f, hash);
    fputs("\n  },\n  \"started\": ", f); json_string(f, started);
    fputs(",\n  \"finished\": ", f); json_string(f, finished);
    fprintf(f, ",\n  \"children_written\": %" PRIu64 ",", children_written);
    fputs("\n  \"children_file_sha256\": ", f);
    sha256_file(cfg->output, hash); json_string(f, hash);
    fputs(",\n  \"host\": ", f); json_string(f, hostname);
    fputs(",\n  \"exit_status\": 0\n}\n", f);
    if (fclose(f) != 0) die_errno("close manifest");
}

static long parse_long_arg(const char *text, const char *name)
{
    char *end;
    long value;
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno || *text == '\0' || *end != '\0') {
        fprintf(stderr, "udenum: invalid %s: %s\n", name, text);
        exit(2);
    }
    return value;
}

static void usage(FILE *f)
{
    fputs(
        "usage: udenum --parents FILE --forbidden FILE --n N --m M\\\n\n"
        "              --output FILE --manifest FILE --shard-id ID [options]\n"
        "options:\n"
        "  --start I --end J       parent record range [I,J), default all\n"
        "  --forbidden-set S       74 (default: Globus-Parshall, orders <= 9) or 398\n"
        "                          (the 74 plus GP-10's 324 on 10 vertices; the file must be\n"
        "                          data/forbidden-398.json, pinned by sha256)\n"
        "  --filter                filter full graphs instead of augmenting parents\n"
        "  --verify-parents        independently check that every parent is F-free\n"
        "  --software NAME=PATH   add a script or binary hash to the manifest\n"
        "  --overwrite             permit replacing output and manifest files\n"
        "  --pattern-stats         print validated forbidden pattern statistics\n"
        "test-only mutations:\n"
        "  --mutation-drop-first-badset\n"
        "  --mutation-no-child-orbit\n", f);
}

static void parse_args(int argc, char **argv, Config *cfg)
{
    int i;
    memset(cfg, 0, sizeof(*cfg));
    cfg->start = 0;
    cfg->end = LONG_MAX;
    cfg->target_n = -1;
    cfg->target_m = -1;
    cfg->forbidden_set = 74;
    for (i = 1; i < argc; ++i) {
        const char *a = argv[i];
        if (strcmp(a, "--parents") == 0 && i + 1 < argc) cfg->parents = argv[++i];
        else if (strcmp(a, "--forbidden") == 0 && i + 1 < argc) cfg->forbidden = argv[++i];
        else if (strcmp(a, "--output") == 0 && i + 1 < argc) cfg->output = argv[++i];
        else if (strcmp(a, "--manifest") == 0 && i + 1 < argc) cfg->manifest = argv[++i];
        else if (strcmp(a, "--shard-id") == 0 && i + 1 < argc) cfg->shard_id = argv[++i];
        else if (strcmp(a, "--start") == 0 && i + 1 < argc) cfg->start = parse_long_arg(argv[++i], "start");
        else if (strcmp(a, "--end") == 0 && i + 1 < argc) cfg->end = parse_long_arg(argv[++i], "end");
        else if (strcmp(a, "--n") == 0 && i + 1 < argc) cfg->target_n = (int)parse_long_arg(argv[++i], "n");
        else if (strcmp(a, "--m") == 0 && i + 1 < argc) cfg->target_m = (int)parse_long_arg(argv[++i], "m");
        else if (strcmp(a, "--forbidden-set") == 0 && i + 1 < argc) {
            long requested = parse_long_arg(argv[++i], "forbidden-set");
            if (requested != 74 && requested != 398) die("--forbidden-set must be 74 or 398");
            cfg->forbidden_set = (int)requested;
        }
        else if (strcmp(a, "--filter") == 0) cfg->filter_mode = 1;
        else if (strcmp(a, "--pattern-stats") == 0) cfg->pattern_stats = 1;
        else if (strcmp(a, "--verify-parents") == 0) cfg->verify_parents = 1;
        else if (strcmp(a, "--overwrite") == 0) cfg->overwrite = 1;
        else if (strcmp(a, "--mutation-drop-first-badset") == 0) cfg->mutation_drop_first_badset = 1;
        else if (strcmp(a, "--mutation-no-child-orbit") == 0) cfg->mutation_no_child_orbit = 1;
        else if (strcmp(a, "--software") == 0 && i + 1 < argc) {
            char *value = argv[++i];
            char *equals = strchr(value, '=');
            if (!equals || equals == value || !equals[1]) die("--software requires NAME=PATH");
            if (cfg->software_count >= MAX_SOFTWARE) die("too many --software arguments");
            *equals = '\0';
            cfg->software[cfg->software_count].name = value;
            cfg->software[cfg->software_count].path = equals + 1;
            ++cfg->software_count;
        } else if (strcmp(a, "--help") == 0) {
            usage(stdout);
            exit(0);
        } else {
            fprintf(stderr, "udenum: unknown or incomplete option: %s\n", a);
            usage(stderr);
            exit(2);
        }
    }
    if (!cfg->forbidden) die("--forbidden is required");
    if (cfg->pattern_stats) return;
    if (!cfg->parents || !cfg->output || !cfg->manifest || !cfg->shard_id)
        die("--parents, --output, --manifest, and --shard-id are required");
    if (cfg->target_n < 0 || cfg->target_n >= MAXV || cfg->target_m < 0)
        die("valid --n and --m are required");
    if (!cfg->filter_mode && cfg->target_n < 2)
        die("augmentation mode requires --n at least 2");
    if (cfg->start < 0 || cfg->end < cfg->start) die("invalid parent range");
    if (!cfg->overwrite && (access(cfg->output, F_OK) == 0 || access(cfg->manifest, F_OK) == 0))
        die("output or manifest already exists, use --overwrite to replace it");
}

int main(int argc, char **argv)
{
    Config cfg;
    static ForbiddenData data;   /* about 360 KB at the raised limits: kept off the stack */
    static Search398 search;     /* forbidden set 398 only: about 3 MB, and 4 MB of rooted copies */
    FILE *parents;
    FILE *out;
    char *line = NULL;
    size_t line_capacity = 0;
    ssize_t line_length;
    long record = 0;
    long record_count;
    long range_end;
    BadFamily bad;
    BadFamily anchored;          /* forbidden set 398 only: T of build_restricted_bad_family_398 */
    RunStats stats;
    clock_t cpu_start;
    double wall_seconds;
    double cpu_seconds;
    struct timespec wall_start, wall_finish;
    struct rusage usage_data;
    time_t started_time, finished_time;
    char started[32], finished[32];

    parse_args(argc, argv, &cfg);
    init_choose_table();
    nauty_check(WORDSIZE, 1, MAXV - 1, NAUTYVERSIONID);
    load_forbidden_json(cfg.forbidden, &data,
                        cfg.forbidden_set == 398 ? &FORBIDDEN_SET_398 : &FORBIDDEN_SET_74);
    if (cfg.forbidden_set == 398) build_search_398(&data, &search);
    if (cfg.pattern_stats) {
        printf("{\"forbidden_graphs\":%d,\"patterns\":%d,"
               "\"size_distribution\":{\"2\":%d,\"3\":%d,\"4\":%d,"
               "\"5\":%d,\"6\":%d,\"7\":%d}}\n",
               data.forbidden_count, data.pattern_count,
               data.size_distribution[2], data.size_distribution[3],
               data.size_distribution[4], data.size_distribution[5],
               data.size_distribution[6], data.size_distribution[7]);
        return 0;
    }

    record_count = count_graph_records(cfg.parents);
    range_end = cfg.end < record_count ? cfg.end : record_count;
    if (cfg.start > record_count) die("parent range starts after end of file");
    memset(&stats, 0, sizeof(stats));
    if (!cfg.filter_mode) bad_family_init(&bad, cfg.target_n - 1);
    else memset(&bad, 0, sizeof(bad));
    if (!cfg.filter_mode && cfg.forbidden_set == 398) bad_family_init(&anchored, cfg.target_n - 1);
    else memset(&anchored, 0, sizeof(anchored));
    parents = fopen(cfg.parents, "r");
    if (!parents) die_errno(cfg.parents);
    out = fopen(cfg.output, "w");
    if (!out) die_errno(cfg.output);
    started_time = time(NULL);
    utc_timestamp(started_time, started);
    if (clock_gettime(CLOCK_MONOTONIC, &wall_start) != 0) die_errno("clock_gettime");
    cpu_start = clock();

    while ((line_length = getline(&line, &line_capacity, parents)) >= 0) {
        uint32_t adj[MAXV];
        int n, m;
        if (line_length == 0 || line[0] == '\n' || line[0] == '\r') continue;
        if (strncmp(line, ">>graph6<<", 10) == 0) continue;
        if (record >= range_end) break;
        if (record++ < cfg.start) continue;
        trim_line(line);
        n = parse_graph6_line(line, adj);
        m = graph_edge_count(adj, n);
        ++stats.parents_seen;
        if (cfg.filter_mode) filter_graph(&cfg, &data, &search, adj, n, m, out, &stats);
        else process_parent(&cfg, &data, &search, &bad, &anchored, adj, n, m, line, out, &stats);
    }
    if (ferror(parents)) die_errno("read parent file");
    free(line);
    if (fclose(parents) != 0) die_errno("close parent file");
    if (fclose(out) != 0) die_errno("close child file");
    cpu_seconds = (double)(clock() - cpu_start) / CLOCKS_PER_SEC;
    if (clock_gettime(CLOCK_MONOTONIC, &wall_finish) != 0) die_errno("clock_gettime");
    wall_seconds = (double)(wall_finish.tv_sec - wall_start.tv_sec) +
                   1e-9 * (double)(wall_finish.tv_nsec - wall_start.tv_nsec);
    finished_time = time(NULL);
    utc_timestamp(finished_time, finished);
    write_manifest(&cfg, range_end, started, finished, stats.children_written);
    if (getrusage(RUSAGE_SELF, &usage_data) != 0) die_errno("getrusage");
    fprintf(stderr,
            "{\"parents_seen\":%" PRIu64 ",\"parents_processed\":%" PRIu64
            ",\"parents_degree_skipped\":%" PRIu64 ",\"bad_sets\":%" PRIu64
            ",\"neighbourhoods\":%" PRIu64 ",\"neighbourhood_orbit_reps\":%" PRIu64
            ",\"neighbourhoods_bad\":%" PRIu64 ",\"child_orbit_rejected\":%" PRIu64
            ",\"children_written\":%" PRIu64 ",\"wall_seconds\":%.6f,"
            "\"cpu_seconds\":%.6f,\"max_rss_kib\":%ld}\n",
            stats.parents_seen, stats.parents_processed, stats.parents_degree_skipped,
            stats.bad_sets, stats.neighbourhoods, stats.neighbourhood_orbit_reps,
            stats.neighbourhoods_bad, stats.child_orbit_rejected, stats.children_written,
            wall_seconds, cpu_seconds, usage_data.ru_maxrss);
    free(bad.mark);
    free(bad.sets);
    free(anchored.mark);
    free(anchored.sets);
    return 0;
}
