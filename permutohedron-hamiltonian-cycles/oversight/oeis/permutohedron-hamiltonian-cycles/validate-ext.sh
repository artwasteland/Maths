#!/usr/bin/env bash
# Adversarial validation of count_frontier5_ext against brute force AND
# count_frontier4, on random connected graphs, with deliberately hostile
# knobs (tiny buffers to force constant spilling, varying bucket counts,
# thread counts, and hash seeds to shake out concurrency/merge bugs).
# Usage: bash validate-ext.sh [n_graphs]   (default 40)
set -euo pipefail
cd "$(dirname "$0")"
N=${1:-40}
CF4=${CF4:-/tmp/cf4}
EXT=${EXT:-/tmp/cf5ext}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0
for i in $(seq 1 "$N"); do
  V=$((8 + i % 9))            # 8..16 vertices
  E=$((V + 2 + i % (V) ))     # sparse-ish, keeps frontier <= 24
  node rand_graph.mjs "$V" "$E" "$i" > "$TMP/g.dat"
  want=$(node brute_hc.mjs "$TMP/g.dat")
  got4=$("$CF4" "$TMP/g.dat" 2>/dev/null | sed 's/.*= //')
  rm -rf "$TMP/w"; mkdir "$TMP/w"
  # hostile knobs, varied per graph
  gotE=$(A5_BUFREC=$((7 + i % 23)) A5_BUCKETS=$((1 << (i % 7))) \
         A5_THREADS=$((1 + i % 4)) A5_HASH_SEED=$((i * 2654435761)) \
         "$EXT" "$TMP/g.dat" "$TMP/w" 2>/dev/null | sed 's/.*= //')
  if [[ "$want" != "$got4" || "$want" != "$gotE" ]]; then
    echo "MISMATCH on graph $i (V=$V E=$E): brute=$want cf4=$got4 ext=$gotE"
    cp "$TMP/g.dat" "./mismatch-$i.dat"
    exit 1
  fi
  pass=$((pass+1))
done
echo "ALL $pass RANDOM GRAPHS AGREE (brute == cf4 == ext, hostile knobs)"
