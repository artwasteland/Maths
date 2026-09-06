#include "udfilter.h"

#include <stdio.h>
#include <string.h>

static void json_string(const char *s) {
    putchar('"');
    for (; *s; s++) {
        if (*s == '\\' || *s == '"') putchar('\\');
        putchar((unsigned char)*s);
    }
    putchar('"');
}

static void usage(const char *name) {
    fprintf(stderr, "usage: %s [-f forbidden-74.g6] [-t tu-gadgets.json] < graph6\n", name);
}

int main(int argc, char **argv) {
    const char *forbidden = "../data/forbidden-74.json";
    const char *tu = "../data/tu-gadgets.json";
    char line[4096], error[256];
    udf_database db;
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) forbidden = argv[++i];
        else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) tu = argv[++i];
        else { usage(argv[0]); return 2; }
    }
    if (!udf_database_load(&db, forbidden, tu, error, sizeof(error))) {
        fprintf(stderr, "udfilter: %s\n", error);
        return 2;
    }
    while (fgets(line, sizeof(line), stdin) != NULL) {
        udf_graph graph;
        udf_witness witness;
        char *end = line + strlen(line);
        while (end > line && (end[-1] == '\n' || end[-1] == '\r')) *--end = '\0';
        if (!udf_graph6_decode(line, &graph)) {
            fprintf(stderr, "udfilter: invalid graph6 input\n");
            return 2;
        }
        printf("{\"g6\":"); json_string(line);
        switch (udf_find(&db, &graph, &witness)) {
        case 1:
            printf(",\"verdict\":\"forbidden\",\"witness\":{\"index\":%d,\"map\":[", witness.index);
            for (i = 0; i < witness.pattern_vertices; i++) printf("%s%d", i ? "," : "", witness.map[i]);
            printf("]}}\n");
            break;
        case 2:
            printf(",\"verdict\":\"tu\",\"witness\":{\"index\":%d,\"map\":[", witness.index);
            for (i = 0; i < witness.pattern_vertices; i++) printf("%s%d", i ? "," : "", witness.map[i]);
            printf("],\"pair\":[%d,%d]}}\n", witness.pair_a, witness.pair_b);
            break;
        case 0:
            printf(",\"verdict\":\"pass\"}\n");
            break;
        default:
            fprintf(stderr, "udfilter: graph rejected\n");
            return 2;
        }
    }
    return 0;
}
