#!/usr/bin/env bash
# Throughput of udtriangle in graphs per CPU-second (= graphs/s/core; the box is shared, so CPU time, not wall).
# Each sample is repeated until the run has >= 40,000 graphs; three runs each, the median reported.
set -euo pipefail
cd "$(dirname "$0")"
BIN=${UDTRIANGLE:-../../filter/udtriangle}
TMP=${TMPDIR:-/tmp}/udtriangle-throughput.$$
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT
for spec in "15:data/measure-15.g6" "17:data/measure-17.g6" "17w:data/level17-parents-w1.g6" \
            "18:data/measure-18.g6" "19:data/level19-children.g6"; do
    label=${spec%%:*}; f=${spec#*:}
    n=$(wc -l < "$f"); reps=$(( (40000 + n - 1) / n ))
    for _ in $(seq "$reps"); do cat "$f"; done > "$TMP/in.g6"
    total=$((n * reps))
    rates=()
    for run in 1 2 3; do
        /usr/bin/time -o "$TMP/time" -f "%U %S" nice -n 10 "$BIN" < "$TMP/in.g6" > "$TMP/out" 2> "$TMP/err"
        read -r u s < "$TMP/time"
        rates+=("$(echo "scale=0; $total / ($u + $s)" | bc)")
    done
    med=$(printf '%s\n' "${rates[@]}" | sort -n | sed -n 2p)
    bytes=$(wc -c < "$TMP/out")
    echo "level $label: $(basename "$f") x$reps = $total graphs; graphs/CPU-s runs: ${rates[*]}; median $med; output $(( bytes / total )) bytes/graph; $(cat "$TMP/err")"
done
