#!/usr/bin/env bash
# Robust multi-seed SIS estimate of a(5) = # undirected Hamiltonian cycles of
# the S_5 bubble-sort graph. Two independent estimators (uniform sis, Warnsdorff
# sis_w) across several seeds, so the spread across seeds is an empirical check on
# the standard errors and the two methods cross-validate each other.
set -e
cd "$(dirname "$0")"
DIVES=${1:-8000000}
echo "### uniform SIS, $DIVES dives/seed ###"
for sd in 101 202 303 404 505 606 707 808; do
  ./sis 5 "$DIVES" "$sd" | grep UNDIRECTED | sed "s/^/seed $sd  /"
done
echo "### Warnsdorff SIS, $DIVES dives/seed (beta 1.5) ###"
for sd in 111 222 333 444; do
  ./sis_w 5 "$DIVES" "$sd" 1.5 | grep UNDIRECTED | sed "s/^/seed $sd  /"
done
echo "### DONE ###"
