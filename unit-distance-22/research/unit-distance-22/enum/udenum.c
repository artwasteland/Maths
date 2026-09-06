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
#define MAXF 80
#define MAXPAT 700
#define MAX_AUT_GENS 512
#define MAX_SOFTWARE 16

typedef struct {
    int n;
    int m;
    uint32_t adj[9];
} SmallGraph;

typedef struct {
    int n;
    int m;
    int ssize;
    int s_complete_depth;
    int source;
    int deleted;
    uint32_t adj[8];
    uint32_t smask;
    unsigned char degree[8];
    unsigned char order[8];
} Pattern;

typedef struct {
    SmallGraph forbidden[MAXF];
    int forbidden_count;
    Pattern patterns[MAXPAT];
    int pattern_count;
    int size_distribution[10];
} ForbiddenData;

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

static void finalize_forbidden_graph(ForbiddenData *data, SmallGraph *g)
{
    int v;
    if (data->forbidden_count >= MAXF) die("too many forbidden graphs");
    if (g->n < 1 || g->n > 9) die("forbidden graph order is outside 1..9");
    data->forbidden[data->forbidden_count++] = *g;
    for (v = 0; v < g->n; ++v) {
        Pattern *p;
        int old_to_new[9];
        int a, b;
        if (data->pattern_count >= MAXPAT) die("too many deletion patterns");
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
        if (p->ssize < 0 || p->ssize >= 10) die("bad pattern S size");
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

static void load_forbidden_json(const char *path, ForbiddenData *data)
{
    size_t size;
    char *text = read_whole_file(path, &size);
    size_t i = 0;
    int depth = 0;
    int pair[2];
    int pair_count = 0;
    SmallGraph current;
    memset(data, 0, sizeof(*data));
    memset(&current, 0, sizeof(current));

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
                if (a < 0 || b < 0 || a >= 9 || b >= 9 || a == b)
                    die("bad forbidden edge");
                if (current.adj[a] & (UINT32_C(1) << b))
                    die("duplicate forbidden edge");
                current.adj[a] |= UINT32_C(1) << b;
                current.adj[b] |= UINT32_C(1) << a;
                ++current.m;
                if (a + 1 > current.n) current.n = a + 1;
                if (b + 1 > current.n) current.n = b + 1;
            } else if (depth == 2) {
                finalize_forbidden_graph(data, &current);
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
    if (data->forbidden_count != 74) die("forbidden JSON does not contain 74 graphs");
    if (data->pattern_count != 635) die("forbidden JSON does not yield 635 deletion patterns");
    if (data->size_distribution[2] != 61 ||
        data->size_distribution[3] != 413 ||
        data->size_distribution[4] != 130 ||
        data->size_distribution[5] != 26 ||
        data->size_distribution[6] != 4 ||
        data->size_distribution[7] != 1)
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
    int map[9];
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
    int map[9];
    uint32_t mapped_pattern;
    uint32_t used_host;
    int s_vertices[8];
    int t_vertices[8];
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
    unsigned char order[9];
    int map[9];
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
                           BadFamily *bad, const uint32_t *adj, int parent_n,
                           int parent_m, const char *input_g6, FILE *out,
                           RunStats *stats)
{
    int d = cfg->target_m - parent_m;
    int delta;
    uint32_t minimum_vertices;
    uint32_t required = 0;
    NeighbourhoodOrbits neighbourhoods;
    size_t i;

    if (parent_n + 1 != cfg->target_n) die("parent order does not match target order");
    if (d < 0 || d > parent_n) return;
    canonical_parent_and_group(adj, parent_n, input_g6);
    if (cfg->verify_parents && contains_forbidden(data, adj, parent_n, parent_m))
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
    if (required)
        build_restricted_bad_family(data, adj, parent_n, parent_m, d, required, bad);
    else
        build_bad_family(data, adj, parent_n, parent_m, d, 0, bad);
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
                         const uint32_t *adj, int n, int m, FILE *out,
                         RunStats *stats)
{
    graph canong[MAXV];
    int lab[MAXV], orbits[MAXV];
    if (n != cfg->target_n || m != cfg->target_m)
        die("filter input does not match --n and --m");
    ++stats->parents_processed;
    if (n == 0) {
        if (fputs("?\n", out) == EOF) die_errno("write filtered graph6");
        ++stats->children_written;
        return;
    }
    if (contains_forbidden(data, adj, n, m)) {
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
    ForbiddenData data;
    FILE *parents;
    FILE *out;
    char *line = NULL;
    size_t line_capacity = 0;
    ssize_t line_length;
    long record = 0;
    long record_count;
    long range_end;
    BadFamily bad;
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
    load_forbidden_json(cfg.forbidden, &data);
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
        if (cfg.filter_mode) filter_graph(&cfg, &data, adj, n, m, out, &stats);
        else process_parent(&cfg, &data, &bad, adj, n, m, line, out, &stats);
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
    return 0;
}
