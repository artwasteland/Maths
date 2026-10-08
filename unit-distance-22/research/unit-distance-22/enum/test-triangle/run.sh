#!/usr/bin/env bash
# The udtriangle test suite (recorded run: runs/suite-2026-09-26.txt; write-up: REPORT.md).
#   run.sh             everything except the throughput measurement
#   run.sh --speed     also the throughput measurement (throughput.sh)
# Exits nonzero if any step fails.  Everything is niced; at most one CPU-heavy process runs at a time.
set -uo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
BIN=../../filter/udtriangle
export PY
mkdir -p out
fails=0
step() { echo; echo "=== $*"; }
check() { if "$@"; then :; else echo "*** STEP FAILED: $*"; fails=$((fails + 1)); fi; }

step "build"
check nice -n 10 make -s -C ../../filter udtriangle
sha256sum ../../filter/udtriangle.c

step "a. unit graphs (expected verdicts in units.tsv)"
check nice -n 10 "$PY" units.py units.tsv
cut -f2 units.tsv > units.g6
nice -n 10 "$BIN" < units.g6 > out/units.out
units_ok() {
    local bad=0
    while IFS=$'\t' read -r name g6 want && IFS= read -r line <&3; do
        got=$(echo "$line" | sed -n 's/^{"verdict":"\([a-z]*\)".*/\1/p')
        if [ "$got" = "$want" ]; then echo "  ok   $name: $got"; else echo "  FAIL $name: $got, want $want"; bad=1; fi
    done < units.tsv 3< out/units.out
    return $bad
}
check units_ok
check nice -n 10 "$PY" devcheck_tri.py units.g6 out/units.out

step "samples of the (23,65) Mode-74 tree (levels 13-18: the w1 measurement samples; level 19: sampled children)"
check bash run-samples.sh
for f in measure-13 measure-14 measure-15 measure-16 measure-17 measure-18 level19-children; do
    echo -n "  $f: "; check nice -n 10 "$PY" devcheck_tri.py "data/$f.g6" "out/$f.out"
done

step "b. positive controls: AMP's 56 known graphs and GP-10's 32,653 embedded B10 graphs"
nice -n 10 "$BIN" < data/amp-known56.g6 > out/amp-known56.out
nice -n 10 "$BIN" < data/B10-embedded.g6 > out/B10-embedded.out
check nice -n 10 "$PY" devcheck_tri.py data/amp-known56.g6 out/amp-known56.out
check nice -n 10 "$PY" devcheck_tri.py data/B10-embedded.g6 out/B10-embedded.out
amp_flagged=$(/usr/bin/grep -c -v '"verdict":"pass"' out/amp-known56.out)
b10_refuted=$(/usr/bin/grep -c '"verdict":"refuted"' out/B10-embedded.out)
echo "  AMP flagged: $amp_flagged (must be 0); B10 refuted: $b10_refuted (must be 0)"
[ "$amp_flagged" = 0 ] && [ "$b10_refuted" = 0 ] || { echo "*** STEP FAILED: positive controls"; fails=$((fails + 1)); }
echo "  B10 tu trees followed with the real embeddings:"
check bash run-b10-embed.sh out/B10-embedded.out

step "c. agreement with the prototype (per graph, levels 13-18)"
for L in 13 14 15 16 17 18; do
    [ -s "out/prototype-$L.txt" ] || nice -n 10 "$PY" prototype_verdicts.py "data/measure-$L.g6" "out/prototype-$L.txt"
    check nice -n 10 "$PY" agree.py "data/measure-$L.g6" "out/prototype-$L.txt" "out/measure-$L.out" "level-$L"
done

step "mirror construction = search, byte for byte"
check bash mirror-equiv.sh

step "d. red controls (compile-time mutants)"
check bash red-controls.sh

step "input handling, budgets, determinism"
check bash robustness.sh

step "fuzz: known-embedding unit-distance graphs; random graphs vs the prototype"
check env COUNT=6000 RCOUNT=3000 bash fuzz.sh

if [ "${1:-}" = "--speed" ]; then
    step "throughput"
    check bash throughput.sh
fi

echo
if [ "$fails" = 0 ]; then echo "ALL STEPS PASSED"; else echo "$fails STEP(S) FAILED"; fi
exit $(( fails > 0 ))
