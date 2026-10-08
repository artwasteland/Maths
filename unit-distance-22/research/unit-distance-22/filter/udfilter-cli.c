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
    fprintf(stderr, "usage: %s [-s 74|398] [-f forbidden.json] [-t tu-gadgets.json] < graph6\n"
                    "  -s, --forbidden-set  74 (default, ../data/forbidden-74.json) or 398\n"
                    "                       (../data/forbidden-398.json, pinned by sha256)\n", name);
}

int main(int argc, char **argv) {
    const char *forbidden = NULL;
    const char *tu = "../data/tu-gadgets.json";
    int forbidden_set = UDF_FORBIDDEN_SET_74;
    char line[4096], error[256];
    static udf_database db;
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) forbidden = argv[++i];
        else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) tu = argv[++i];
        else if ((strcmp(argv[i], "-s") == 0 || strcmp(argv[i], "--forbidden-set") == 0) &&
                 i + 1 < argc) {
            const char *value = argv[++i];
            if (strcmp(value, "74") == 0) forbidden_set = UDF_FORBIDDEN_SET_74;
            else if (strcmp(value, "398") == 0) forbidden_set = UDF_FORBIDDEN_SET_398;
            else { usage(argv[0]); return 2; }
        }
        else { usage(argv[0]); return 2; }
    }
    if (forbidden == NULL)
        forbidden = forbidden_set == UDF_FORBIDDEN_SET_398 ? "../data/forbidden-398.json"
                                                           : "../data/forbidden-74.json";
    if (!udf_database_load_set(&db, forbidden, tu, forbidden_set, error, sizeof(error))) {
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
