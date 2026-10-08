#!/usr/bin/env bash
# The mirror construction of the root split's minus subtree must give the same bytes as searching it (--no-mirror),
# on every sample; and a small budget must only turn verdicts into pass, identically in both modes.
set -euo pipefail
cd "$(dirname "$0")"
BIN=${UDTRIANGLE:-../../filter/udtriangle}
mkdir -p out/mirror
status=0
for f in units.g6 data/measure-13.g6 data/measure-14.g6 data/measure-15.g6 data/measure-16.g6 data/measure-17.g6 \
         data/measure-18.g6 data/level19-children.g6 data/B10-embedded.g6 data/amp-known56.g6; do
    base=$(basename "$f" .g6)
    for b in 4096 7; do
        nice -n 10 "$BIN" -b "$b" < "$f" > "out/mirror/$base.b$b.m" 2>/dev/null
        nice -n 10 "$BIN" -b "$b" --no-mirror < "$f" > "out/mirror/$base.b$b.s" 2>/dev/null
        if cmp -s "out/mirror/$base.b$b.m" "out/mirror/$base.b$b.s"; then
            echo "same bytes: $base budget $b ($(sha256sum < "out/mirror/$base.b$b.m" | cut -c1-16))"
        else
            echo "DIFFERENT: $base budget $b"; status=1
        fi
    done
done
exit $status
