#!/usr/bin/env bash
# Red controls: compile-time mutants of udtriangle.c (never built by the Makefile).
#   mut-rotation   triangle rows use w^(2s) for w^s, in the search and in the self-verifier
#   mut-edge       a node may close on a forced unit distance on an EDGE ab (pq != ab), search and self-verifier
#   *-searchonly   the same mutation in the search only: the (true) self-verifier must catch every bad certificate
# A full mutant must (1) have certificates the dev checker rejects and (2) flag at least one positive-control graph
# (a real unit-distance graph: GP-10's embedded B10 graphs, AMP's 56 known graphs).  A search-only mutant must write
# only certificates the dev checker accepts, with the self-verifier's failures counted on stderr.
set -uo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
SRC=../../filter/udtriangle.c
CC=${CC:-cc}
mkdir -p bin out/red
build() { nice -n 10 "$CC" -std=c17 -O2 -Wall -Wextra -Wpedantic "$@"; }
build -DMUT_ROTATION -o bin/udtriangle-mut-rotation "$SRC" || exit 2
build -DMUT_ROTATION -DMUT_SEARCH_ONLY -o bin/udtriangle-mut-rotation-searchonly "$SRC" || exit 2
build -DMUT_EDGE_CLOSE -o bin/udtriangle-mut-edge "$SRC" || exit 2
build -DMUT_EDGE_CLOSE -DMUT_SEARCH_ONLY -o bin/udtriangle-mut-edge-searchonly "$SRC" || exit 2
status=0
for m in rotation edge; do
    pos_flagged=0
    rejected_total=0
    for f in amp-known56 B10-embedded measure-18; do
        out=out/red/$m.$f
        nice -n 10 "bin/udtriangle-mut-$m" < "data/$f.g6" > "$out.jsonl" 2> "$out.err"
        flagged=$(/usr/bin/grep -c -v '"verdict":"pass"' "$out.jsonl")
        rep=$(nice -n 10 "$PY" devcheck_tri.py "data/$f.g6" "$out.jsonl" --count)
        rej=$(echo "$rep" | sed -n 's/.* rejected=\([0-9]*\).*/\1/p')
        rejected_total=$((rejected_total + rej))
        [ "$f" != measure-18 ] && pos_flagged=$((pos_flagged + flagged))
        echo "mut-$m on $f: flagged=$flagged  devcheck: $rep"
        so=out/red/$m-searchonly.$f
        nice -n 10 "bin/udtriangle-mut-$m-searchonly" < "data/$f.g6" > "$so.jsonl" 2> "$so.err"
        sflag=$(/usr/bin/grep -c -v '"verdict":"pass"' "$so.jsonl")
        srep=$(nice -n 10 "$PY" devcheck_tri.py "data/$f.g6" "$so.jsonl")
        vfail=$(sed -n 's/.*verify_fail=\([0-9]*\).*/\1/p' "$so.err")
        echo "mut-$m-searchonly on $f: flagged=$sflag verify_fail=$vfail  devcheck: ${srep:0:60}"
        case "$srep" in ACCEPT*) ;; *) echo "  RED CONTROL FAILED: a search-only mutant emitted a bad certificate"; status=1;; esac
    done
    if [ "$rejected_total" -gt 0 ] && [ "$pos_flagged" -gt 0 ]; then
        echo "mut-$m: RED as required (dev checker rejected $rejected_total certificates; $pos_flagged positive-control graphs flagged)"
    else
        echo "mut-$m: RED CONTROL FAILED (rejected=$rejected_total, positive controls flagged=$pos_flagged)"; status=1
    fi
done
exit $status
