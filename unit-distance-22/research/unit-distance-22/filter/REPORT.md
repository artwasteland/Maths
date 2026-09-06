# Filter B2 report

## WHAT WORKS

The module contains a reusable C library in `udfilter.c` and `udfilter.h`, the static
library `libudfilter.a`, the CLI `udfilter`, the thin wrapper `udfilter.py`, the independent
checker `verify-witness.py`, and `selfcheck.py`. The CLI reads graph6 lines on stdin and
writes one JSON object per line. Its witness objects are indexed in the JSON data files:

    {"g6":"C~","verdict":"forbidden","witness":{"index":0,"map":[0,1,2,3]}}
    {"g6":"Elcg","verdict":"tu","witness":{"index":0,"map":[0,1,2,3,4,5],"pair":[1,5]}}
    {"g6":"C^","verdict":"pass"}

The matcher uses 22-bit adjacency masks, pattern degree lower bounds, mapped-neighbour
intersections, forward candidate pruning, and deterministic minimum-candidate branching.
Forbidden patterns are loaded from `data/forbidden-74.json`, so witness labels match the
contract data exactly. The supplied forbidden graph6 file was independently checked to be
isomorphic to the JSON entries in all 74 positions.

Build and full self-check command:

    make clean && make && ./selfcheck.py

Exact output:

    rm -f udfilter libudfilter.a udfilter.o udfilter-cli.o
    cc -std=c17 -O3 -Wall -Wextra -Wpedantic -c -o udfilter.o udfilter.c
    ar rcs libudfilter.a udfilter.o
    cc -std=c17 -O3 -Wall -Wextra -Wpedantic -c -o udfilter-cli.o udfilter-cli.c
    cc -std=c17 -O3 -Wall -Wextra -Wpedantic -o udfilter udfilter-cli.o libudfilter.a
    known_56_pass=56
    forbidden_planted_verified=74
    tu_pair_removed_verified=6
    tu_pair_present_results=[[0,"pass",null],[1,"pass",null],[2,"pass",null],[3,"tu",4],[4,"tu",0],[5,"pass",null]]
    corrupt_witness_rejected=1

The known extremal check exercised every line of `sources/amp/anc/graph6.txt`, and all 56
were `pass`. Each of the 74 forbidden patterns was planted in a decorated 22-vertex host,
and each returned a forbidden result accepted by `verify-witness.py`. Each of the six TU
gadgets was planted with its distinguished pair removed, and all six returned a TU result
accepted by the independent checker. The corrupt-map check changed one mapped vertex to a
duplicate and the checker rejected it.

The wrapper check was:

    ./udfilter.py <<'EOF'
    ?
    C^
    EOF

with output:

    {"g6":"?","verdict":"pass"}
    {"g6":"C^","verdict":"pass"}

Throughput command, using the five 21-vertex known inputs repeated 20 times:

    /usr/bin/time -o /tmp/filter-final-time.txt -f 'elapsed_seconds=%e max_rss_kb=%M' sh -c 'awk '\''substr($0,1,1)=="T" {for (i=0; i<20; i++) print}'\'' ../sources/amp/anc/graph6.txt | ./udfilter >/tmp/filter-final-21-100.jsonl
    wc -l /tmp/filter-final-21-100.jsonl
    cat /tmp/filter-final-time.txt
    awk -F'"verdict":"' '{print $2}' /tmp/filter-final-21-100.jsonl | cut -d'"' -f1 | sort | uniq -c

Exact output:

    100 /tmp/filter-final-21-100.jsonl
    elapsed_seconds=9.14 max_rss_kb=2412
        100 pass

This is 10.94 graphs per second for this run.

The required mutation control was exercised. I temporarily changed the pair non-adjacency
test at line 285 of `udfilter.c` from the edge test to `s->require_nonedge && 0`, and also
changed the early pair rejection at line 315 to `if (0)`. I ran:

    make >/tmp/mutation-build.out && ./selfcheck.py

The command exited with status 1 and went red at the known-graph assertion:

    Traceback (most recent call last):
      File ".../filter/./selfcheck.py", line 84, in <module>
        raise SystemExit(main())
      File ".../filter/./selfcheck.py", line 47, in main
        assert len(out) == 56 and all(x["verdict"] == "pass" for x in out)
    AssertionError

The mutation was restored, the final build was rerun, and the full self-check output above
is from the restored code.

## WHAT DOES NOT

The literal pair-present TU fixture requirement cannot hold for all six supplied gadgets
under the rule that any of the six gadgets is sufficient. With gadget 3 plus its pair
present, the host graph6 is `GrClIo` and the filter finds gadget 4. With gadget 4 plus its
pair present, the host graph6 is `GrClIS` and the filter finds gadget 0. Thus the exact
pair-present results are pass for indices 0, 1, 2, and 5, and TU by a different valid gadget
for indices 3 and 4. The self-check verifies those alternate witnesses and confirms that
the planted gadget index itself is not returned.

The enumerator files required for the Table 1 reproduction were not present. There is no
`enum/out/` directory with `<n>-<m>.g6` inputs, so the after-filter counts 1, 8, 38, 5, 1,
and 19 were not reproduced here.

## UNCERTAIN

- The CLI assumes the fixed JSON layouts supplied in the contract. It is not a general JSON
  parser.
- The CLI accepts valid graph6 with at most 22 vertices but does not independently check
  that the input is canonically labelled by nauty.
- The throughput measurement covers five known 21-vertex inputs, not a statistically broad
  sample of arbitrary 21-vertex graphs.
- The independent checker validates the map, edge preservation, pair identity, and pair
  non-adjacency. It does not prove the mathematical TU lemmas, as required by its narrow
  contract role.
- No Table 1 or 22-vertex enumerator output was available to exercise.

## PROPOSED CONTRACT AMENDMENTS

- Specify the exact filter CLI JSON line shape, including the `pass` verdict, since Section 2
  lists certificate verdicts but does not define the standalone filter output syntax.
- Change the pair-present TU self-check to require that the planted gadget index is not the
  reported index, while allowing a different valid gadget witness. The current six-gadget
  data makes a universal `pass` assertion false for two fixtures.
