/*
 * Independent graph6 subgraph matcher for the GP-10 input recount.
 *
 * A host has at most 10 vertices and a pattern has at most 9 vertices.
 * The search is an injective, non-induced monomorphism search.  Witnesses
 * are emitted as one tab-separated record per removed host and are gzip
 * compressed while the host stream is still being read.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

#define MAXN 10
#define MAXPAT 128
#define LINE_MAX_LEN 256

typedef struct {
    int n;
    int m;
    uint16_t adj[MAXN];
    int degree[MAXN];
    int original_index;
} Pattern;

typedef struct {
    const Pattern *pattern;
    int host_n;
    const uint16_t *host_adj;
    uint16_t candidate_base[MAXN];
    int map[MAXN];
    uint16_t used_hosts;
} Search;

static uint64_t popcount16(uint16_t x) {
    uint64_t count = 0;
    while (x != 0) {
        x &= (uint16_t)(x - 1U);
        ++count;
    }
    return count;
}

static int next_set_bit(uint16_t *bits) {
    uint16_t value = *bits;
    int bit;
    if (value == 0) {
        return -1;
    }
    bit = 0;
    while ((value & 1U) == 0U) {
        value >>= 1;
        ++bit;
    }
    *bits = (uint16_t)(*bits & (uint16_t)~(1U << bit));
    return bit;
}

static void clear_graph(uint16_t adj[MAXN]) {
    int i;
    for (i = 0; i < MAXN; ++i) {
        adj[i] = 0;
    }
}

/* Decode graph6 for the small orders used here. */
static int decode_graph6(const char *line, int *out_n, uint16_t out_adj[MAXN]) {
    size_t pos = 0;
    unsigned int first;
    int n;
    int i;
    int j;
    int bit_index = 0;
    int total_bits;

    clear_graph(out_adj);
    if (strncmp(line, ">>graph6<<", 10) == 0) {
        pos = 10;
    }
    if (line[pos] == '\0') {
        return 0;
    }
    first = (unsigned int)((unsigned char)line[pos++]);
    if (first < 63U || first > 125U) {
        /* Extended graph6 orders are outside this recount's 10-vertex bound. */
        return 0;
    }
    n = (int)first - 63;
    if (n < 0 || n > MAXN) {
        return 0;
    }

    total_bits = n * (n - 1) / 2;
    for (i = 0; i < (total_bits + 5) / 6; ++i) {
        unsigned int value;
        int b;
        if (line[pos] == '\0') {
            return 0;
        }
        value = (unsigned int)((unsigned char)line[pos++]) - 63U;
        for (b = 5; b >= 0 && bit_index < total_bits; --b, ++bit_index) {
            if ((value & (1U << b)) != 0U) {
                int seen = 0;
                int high;
                for (high = 1; high < n; ++high) {
                    int width = high;
                    if (bit_index < seen + width) {
                        j = high;
                        {
                            int low = bit_index - seen;
                            out_adj[low] |= (uint16_t)(1U << j);
                            out_adj[j] |= (uint16_t)(1U << low);
                        }
                        break;
                    }
                    seen += width;
                }
            }
        }
    }
    *out_n = n;
    return 1;
}

static int parse_pattern_line(const char *line, Pattern *pattern, int original_index) {
    uint16_t adj[MAXN];
    int n;
    int i;

    if (!decode_graph6(line, &n, adj)) {
        return 0;
    }
    pattern->n = n;
    pattern->m = 0;
    pattern->original_index = original_index;
    for (i = 0; i < MAXN; ++i) {
        pattern->adj[i] = adj[i];
        pattern->degree[i] = 0;
    }
    for (i = 0; i < n; ++i) {
        pattern->degree[i] = (int)popcount16(adj[i]);
        pattern->m += pattern->degree[i];
    }
    pattern->m /= 2;
    return 1;
}

static int choose_pattern_vertex(const Search *search, uint16_t assigned, uint16_t *out_candidates) {
    const Pattern *pattern = search->pattern;
    uint16_t best_candidates = 0;
    int best_vertex = -1;
    uint64_t best_count = UINT64_MAX;
    int best_mapped_neighbors = -1;
    int p;

    for (p = 0; p < pattern->n; ++p) {
        uint16_t candidates;
        int q;
        int mapped_neighbors = 0;
        if ((assigned & (uint16_t)(1U << p)) != 0U) {
            continue;
        }
        candidates = search->candidate_base[p] & (uint16_t)~search->used_hosts;
        for (q = 0; q < pattern->n; ++q) {
            if ((assigned & (uint16_t)(1U << q)) != 0U &&
                (pattern->adj[p] & (uint16_t)(1U << q)) != 0U) {
                candidates &= search->host_adj[search->map[q]];
                ++mapped_neighbors;
            }
        }
        if (popcount16(candidates) < best_count ||
            (popcount16(candidates) == best_count &&
             mapped_neighbors > best_mapped_neighbors)) {
            best_count = popcount16(candidates);
            best_vertex = p;
            best_candidates = candidates;
            best_mapped_neighbors = mapped_neighbors;
        }
    }
    *out_candidates = best_candidates;
    return best_vertex;
}

static int search_match(Search *search, uint16_t assigned) {
    const Pattern *pattern = search->pattern;
    uint16_t candidates;
    int p;
    int h;

    if (assigned == (uint16_t)((1U << pattern->n) - 1U)) {
        return 1;
    }
    p = choose_pattern_vertex(search, assigned, &candidates);
    if (p < 0 || candidates == 0) {
        return 0;
    }
    while ((h = next_set_bit(&candidates)) >= 0) {
        search->map[p] = h;
        search->used_hosts |= (uint16_t)(1U << h);
        if (search_match(search, (uint16_t)(assigned | (uint16_t)(1U << p)))) {
            return 1;
        }
        search->used_hosts &= (uint16_t)~(uint16_t)(1U << h);
        search->map[p] = -1;
    }
    return 0;
}

static int pattern_matches(const Pattern *pattern, int host_n, const uint16_t host_adj[MAXN], int out_map[MAXN]) {
    Search search;
    int i;
    int h;
    int host_edges = 0;
    int max_host_degree = 0;

    if (pattern->n > host_n) {
        return 0;
    }
    for (i = 0; i < host_n; ++i) {
        int degree = (int)popcount16(host_adj[i]);
        host_edges += degree;
        if (degree > max_host_degree) {
            max_host_degree = degree;
        }
    }
    if (pattern->m > host_edges / 2 || pattern->n == 0) {
        return 0;
    }
    if (pattern->n > 0 && pattern->degree[0] > max_host_degree) {
        /* This is only a quick rejection for one vertex. The full loop below
         * applies the same test to every pattern vertex. */
        return 0;
    }
    search.pattern = pattern;
    search.host_n = host_n;
    search.host_adj = host_adj;
    search.used_hosts = 0;
    for (i = 0; i < MAXN; ++i) {
        search.map[i] = -1;
    }
    for (i = 0; i < pattern->n; ++i) {
        uint16_t candidates = 0;
        for (h = 0; h < host_n; ++h) {
            if ((int)popcount16(host_adj[h]) >= pattern->degree[i]) {
                candidates |= (uint16_t)(1U << h);
            }
        }
        if (candidates == 0) {
            return 0;
        }
        search.map[i] = -1;
        search.candidate_base[i] = candidates;
    }
    if (!search_match(&search, 0)) {
        return 0;
    }
    for (i = 0; i < pattern->n; ++i) {
        out_map[i] = search.map[i];
    }
    return 1;
}

static int read_patterns(const char *path, Pattern patterns[MAXPAT], int *out_count) {
    FILE *file = fopen(path, "r");
    char line[LINE_MAX_LEN];
    int count = 0;
    int line_number = 0;
    if (file == NULL) {
        fprintf(stderr, "cannot open pattern file %s: %s\n", path, strerror(errno));
        return 0;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        size_t length;
        ++line_number;
        length = strlen(line);
        while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r')) {
            line[--length] = '\0';
        }
        if (length == 0 || strncmp(line, ">>graph6<<", 10) == 0) {
            continue;
        }
        if (count >= MAXPAT || !parse_pattern_line(line, &patterns[count], count)) {
            fprintf(stderr, "bad graph6 pattern at line %d\n", line_number);
            fclose(file);
            return 0;
        }
        ++count;
    }
    fclose(file);
    if (count == 0) {
        fprintf(stderr, "pattern file %s is empty\n", path);
        return 0;
    }
    *out_count = count;
    return 1;
}

static int write_witness(gzFile file, const char *host_line, const Pattern *pattern, const int map[MAXN]) {
    char buffer[LINE_MAX_LEN];
    int offset;
    int i;
    int written;
    offset = snprintf(buffer, sizeof(buffer), "%s\t%d\t", host_line, pattern->original_index);
    if (offset < 0 || (size_t)offset >= sizeof(buffer)) {
        return 0;
    }
    for (i = 0; i < pattern->n; ++i) {
        written = snprintf(buffer + offset, sizeof(buffer) - (size_t)offset, "%s%d",
                           i == 0 ? "" : ",", map[i]);
        if (written < 0 || (size_t)written >= sizeof(buffer) - (size_t)offset) {
            return 0;
        }
        offset += written;
    }
    written = snprintf(buffer + offset, sizeof(buffer) - (size_t)offset, "\n");
    if (written < 0 || (size_t)written >= sizeof(buffer) - (size_t)offset) {
        return 0;
    }
    return gzwrite(file, buffer, (unsigned int)(offset + written)) == offset + written;
}

static void usage(const char *program) {
    fprintf(stderr,
            "usage: %s --patterns FILE [--survivors FILE] [--witness FILE] "
            "[--summary FILE] [--max-pattern-n N] [--drop-index I] [--limit N]\n",
            program);
}

int main(int argc, char **argv) {
    const char *pattern_path = NULL;
    const char *survivor_path = NULL;
    const char *witness_path = NULL;
    const char *summary_path = NULL;
    FILE *survivors = NULL;
    gzFile witnesses = NULL;
    Pattern patterns[MAXPAT];
    int pattern_count = 0;
    int max_pattern_n = MAXN;
    int drop_index = -1;
    uint64_t host_limit = 0;
    uint64_t hosts = 0;
    uint64_t kept = 0;
    uint64_t removed = 0;
    char line[LINE_MAX_LEN];
    int i;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--patterns") == 0 && i + 1 < argc) {
            pattern_path = argv[++i];
        } else if (strcmp(argv[i], "--survivors") == 0 && i + 1 < argc) {
            survivor_path = argv[++i];
        } else if (strcmp(argv[i], "--witness") == 0 && i + 1 < argc) {
            witness_path = argv[++i];
        } else if (strcmp(argv[i], "--summary") == 0 && i + 1 < argc) {
            summary_path = argv[++i];
        } else if (strcmp(argv[i], "--max-pattern-n") == 0 && i + 1 < argc) {
            max_pattern_n = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--drop-index") == 0 && i + 1 < argc) {
            drop_index = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--limit") == 0 && i + 1 < argc) {
            host_limit = strtoull(argv[++i], NULL, 10);
        } else {
            usage(argv[0]);
            return 2;
        }
    }
    if (pattern_path == NULL || max_pattern_n < 0 || max_pattern_n > MAXN) {
        usage(argv[0]);
        return 2;
    }
    if (!read_patterns(pattern_path, patterns, &pattern_count)) {
        return 2;
    }
    if (survivor_path != NULL) {
        survivors = fopen(survivor_path, "w");
        if (survivors == NULL) {
            fprintf(stderr, "cannot open survivor file %s: %s\n", survivor_path, strerror(errno));
            return 2;
        }
        setvbuf(survivors, NULL, _IOFBF, 1U << 20);
    }
    if (witness_path != NULL) {
        witnesses = gzopen(witness_path, "wb9");
        if (witnesses == NULL) {
            fprintf(stderr, "cannot open witness file %s: %s\n", witness_path, strerror(errno));
            if (survivors != NULL) {
                fclose(survivors);
            }
            return 2;
        }
    }

    while (fgets(line, sizeof(line), stdin) != NULL) {
        size_t length;
        int host_n;
        uint16_t host_adj[MAXN];
        int matched = 0;
        const Pattern *matched_pattern = NULL;
        int matched_map[MAXN];
        ++hosts;
        length = strlen(line);
        while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r')) {
            line[--length] = '\0';
        }
        if (length == 0 || !decode_graph6(line, &host_n, host_adj)) {
            fprintf(stderr, "bad graph6 host at input record %llu\n",
                    (unsigned long long)hosts);
            if (witnesses != NULL) {
                gzclose(witnesses);
            }
            if (survivors != NULL) {
                fclose(survivors);
            }
            return 3;
        }
        for (i = 0; i < pattern_count; ++i) {
            int current_map[MAXN];
            if (patterns[i].original_index == drop_index || patterns[i].n > max_pattern_n) {
                continue;
            }
            if (pattern_matches(&patterns[i], host_n, host_adj, current_map)) {
                matched = 1;
                matched_pattern = &patterns[i];
                for (int j = 0; j < matched_pattern->n; ++j) {
                    matched_map[j] = current_map[j];
                }
                break;
            }
        }
        if (matched) {
            ++removed;
            if (witnesses != NULL && !write_witness(witnesses, line, matched_pattern, matched_map)) {
                fprintf(stderr, "failed writing witness for input record %llu\n",
                        (unsigned long long)hosts);
                gzclose(witnesses);
                if (survivors != NULL) {
                    fclose(survivors);
                }
                return 4;
            }
        } else {
            ++kept;
            if (survivors != NULL && fprintf(survivors, "%s\n", line) < 0) {
                fprintf(stderr, "failed writing survivor at input record %llu\n",
                        (unsigned long long)hosts);
                if (witnesses != NULL) {
                    gzclose(witnesses);
                }
                fclose(survivors);
                return 4;
            }
        }
        if (host_limit != 0 && hosts >= host_limit) {
            break;
        }
    }

    if (witnesses != NULL && gzclose(witnesses) != Z_OK) {
        fprintf(stderr, "failed closing witness file %s\n", witness_path);
        if (survivors != NULL) {
            fclose(survivors);
        }
        return 4;
    }
    if (survivors != NULL && fclose(survivors) != 0) {
        fprintf(stderr, "failed closing survivor file %s\n", survivor_path);
        return 4;
    }
    if (summary_path != NULL) {
        FILE *summary = fopen(summary_path, "w");
        if (summary == NULL) {
            fprintf(stderr, "cannot open summary file %s: %s\n", summary_path, strerror(errno));
            return 4;
        }
        fprintf(summary, "input_graphs=%llu\n", (unsigned long long)hosts);
        fprintf(summary, "survivors=%llu\n", (unsigned long long)kept);
        fprintf(summary, "removed=%llu\n", (unsigned long long)removed);
        fprintf(summary, "patterns=%d\n", pattern_count);
        fprintf(summary, "max_pattern_n=%d\n", max_pattern_n);
        fprintf(summary, "drop_index=%d\n", drop_index);
        fclose(summary);
    }
    fprintf(stderr, "input_graphs=%llu survivors=%llu removed=%llu patterns=%d max_pattern_n=%d drop_index=%d\n",
            (unsigned long long)hosts, (unsigned long long)kept,
            (unsigned long long)removed, pattern_count, max_pattern_n, drop_index);
    return 0;
}
