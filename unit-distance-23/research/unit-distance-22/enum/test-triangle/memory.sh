#!/usr/bin/env bash
# Peak resident memory of udtriangle at the default and the maximum budget (level-18 sample).
set -euo pipefail
cd "$(dirname "$0")"
BIN=${UDTRIANGLE:-../../filter/udtriangle}
T=$(mktemp)
trap 'rm -f "$T"' EXIT
for b in 4096 100000; do
    /usr/bin/time -o "$T" -f "%M %U" nice -n 10 "$BIN" -b "$b" < data/measure-18.g6 > /dev/null 2>&1
    read -r rss user < "$T"
    echo "budget $b: peak RSS ${rss} KB, ${user} s user for 1500 level-18 graphs"
done
