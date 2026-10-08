#!/usr/bin/env bash
# Run udtriangle over the sample files (niced), one output file per input, and time each run.
#   run-samples.sh [extra udtriangle flags...]
set -euo pipefail
cd "$(dirname "$0")"
BIN=${UDTRIANGLE:-../../filter/udtriangle}
OUT=${OUT:-out}
mkdir -p "$OUT"
for f in data/measure-13.g6 data/measure-14.g6 data/measure-15.g6 data/measure-16.g6 data/measure-17.g6 \
         data/measure-18.g6 data/level19-children.g6; do
    base=$(basename "$f" .g6)
    start=$(date +%s.%N)
    nice -n 10 "$BIN" "$@" < "$f" > "$OUT/$base.out" 2> "$OUT/$base.err"
    end=$(date +%s.%N)
    n=$(wc -l < "$f")
    echo "$base graphs=$n wall=$(echo "$end - $start" | bc)s $(cat "$OUT/$base.err")"
done
