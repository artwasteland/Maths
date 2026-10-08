/* Keep TU hits: they are F10-free and are not refutations at these edge counts. */
#include "udfilter.h"

#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    static udf_database database;
    char line[256], error[256];
    unsigned long long counts[3] = {0, 0, 0};
    FILE *survivors, *witnesses;
    if (argc != 5) {
        fprintf(stderr, "usage: filter forbidden.json tu.json survivors.g6 witnesses.tsv\n");
        return 2;
    }
    if (!udf_database_load_set(&database, argv[1], argv[2], 398, error, sizeof(error))) {
        fprintf(stderr, "%s\n", error);
        return 2;
    }
    survivors = fopen(argv[3], "w");
    witnesses = fopen(argv[4], "w");
    if (survivors == NULL || witnesses == NULL) return 2;
    setvbuf(survivors, NULL, _IOFBF, 1U << 20);
    setvbuf(witnesses, NULL, _IOFBF, 1U << 20);
    while (fgets(line, sizeof(line), stdin)) {
        udf_graph host;
        udf_witness witness;
        int result;
        line[strcspn(line, "\r\n")] = '\0';
        if (!udf_graph6_decode(line, &host)) return 3;
        result = udf_find(&database, &host, &witness);
        if (result < 0 || result > 2) return 3;
        ++counts[result];
        if (result == 1) {
            fprintf(witnesses, "%s\t%d\t", line, witness.index);
            for (int i = 0; i < witness.pattern_vertices; ++i)
                fprintf(witnesses, "%s%d", i ? "," : "", witness.map[i]);
            fputc('\n', witnesses);
        } else {
            fprintf(survivors, "%s\n", line);
        }
    }
    if (ferror(stdin) || ferror(survivors) || ferror(witnesses)) return 4;
    if (fclose(survivors) != 0 || fclose(witnesses) != 0) return 4;
    printf("{\"input\":%llu,\"pass\":%llu,\"removed\":%llu,\"tu\":%llu,\"survivors\":%llu}\n",
           counts[0] + counts[1] + counts[2], counts[0], counts[1], counts[2],
           counts[0] + counts[2]);
    return ferror(stdout) ? 4 : 0;
}
