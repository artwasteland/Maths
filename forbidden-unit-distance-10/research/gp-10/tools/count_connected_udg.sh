#!/usr/bin/env bash
# count_connected_udg.sh OUTDIR: connected unit-distance graphs on n vertices (OEIS A059103), n = 4..10, from the
# GP-10 classification. Run from the repository root.
#
# A connected graph is unit-distance iff every block is (glue blocks at cut vertices with a generic rotation). A block
# on at most n-1 vertices is unit-distance iff it contains no member of F(n-1) (Globus-Parshall, re-derived by the
# B4p..B9p controls); the one possible block on n vertices is the whole graph, biconnected, which is unit-distance
# iff it is F(n-1)-free and not refuted in the Bn run. So
#     a(n) = #{connected F(n-1)-free graphs on n vertices} - #{refuted in run Bn}
# and, for n <= 9, a(n) also equals the direct count with all 74 in force (the 74 contain every minimal forbidden graph
# on at most 9 vertices); for n = 10 the direct count uses all 398 (the 74 plus L10), chained through the matcher in
# chunks of at most 128 patterns (its compile-time limit). Two matchers that share no code count the F9-free graphs.
set -euo pipefail
OUT=$1; mkdir -p "$OUT"
U=research/unit-distance-22; G=research/gp-10
cc -O3 -std=c11 "$G/recount/matcher.c" -lz -o "$OUT/matcher"
M="$OUT/matcher"; P74="$U/data/forbidden-74.g6"
declare -A R=([4]=1 [5]=4 [6]=2 [7]=4 [8]=17 [9]=101 [10]=509)    # refuted counts of runs B4p..B9p and B10-final
surv() { grep -oE "survivors=[0-9]+" "$1" | head -1 | cut -d= -f2; }
for n in 4 5 6 7 8 9; do
  nauty-geng -cq "$n" > "$OUT/c$n.g6"
  "$M" --patterns "$P74" --summary "$OUT/all$n.summary" < "$OUT/c$n.g6"
  "$M" --patterns "$P74" --max-pattern-n $((n-1)) --summary "$OUT/f$n.summary" < "$OUT/c$n.g6"
  a=$(surv "$OUT/all$n.summary"); f=$(surv "$OUT/f$n.summary")
  echo "n=$n connected=$(wc -l < "$OUT/c$n.g6") direct=$a F$((n-1))-free=$f minus refuted ${R[$n]} = $((f - R[$n]))"
done
nauty-geng -cq 10 > "$OUT/c10.g6"
"$M" --patterns "$P74" --survivors "$OUT/s74.g6" --summary "$OUT/m74.summary" < "$OUT/c10.g6"
"$U/filter/udfilter" -f "$U/data/forbidden-74.json" -t "$U/data/tu-gadgets.json" < "$OUT/c10.g6" \
  | grep -vc '"verdict": *"forbidden"' > "$OUT/udfilter-not-forbidden.txt" || true
cat "$P74" "$G/runs/B10-final-2026-09-25/L10.g6" > "$OUT/forbidden-398.g6"
split -l 128 -d "$OUT/forbidden-398.g6" "$OUT/chunk-"
cp "$OUT/s74.g6" "$OUT/cur.g6"
for ch in "$OUT"/chunk-0*; do "$M" --patterns "$ch" --survivors "$OUT/next.g6" --summary "$ch.summary" < "$OUT/cur.g6"; mv "$OUT/next.g6" "$OUT/cur.g6"; done
C74=$(surv "$OUT/m74.summary"); C398=$(wc -l < "$OUT/cur.g6")
echo "n=10 connected=$(wc -l < "$OUT/c10.g6") F9-free: matcher $C74, udfilter $(cat "$OUT/udfilter-not-forbidden.txt"); minus 509 = $((C74 - 509)); direct with 398 = $C398"
