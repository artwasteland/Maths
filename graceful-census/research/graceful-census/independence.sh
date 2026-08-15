#!/bin/bash
# independence.sh <family> <n> [seed]
#
# Exact graceful-labeling count of a PERMUTED copy of the graph, sharded over 4 cores.
# The count is isomorphism-invariant, so this must reproduce the committed b-file term;
# but the permutation changes the counter's greedy vertex order, so it exercises a
# different search tree, different pruning, and a different shard decomposition.
# See the header of independence.mjs for why this check was added (2026-07-20).
set -euo pipefail
fam=$1; n=$2; seed=${3:-12345}
here="$(cd "$(dirname "$0")" && pwd)"
f=$(mktemp /tmp/perm_${fam}${n}_XXXX.txt)
trap 'rm -f "$f"' EXIT
node "$here/independence.mjs" "$fam" "$n" "$seed" > "$f"
m=$(head -1 "$f" | cut -d' ' -f2)
echo "# $fam($n) seed=$seed  v=$(head -1 "$f" | cut -d' ' -f1) m=$m  shards=$((m+1))"
seq 0 "$m" | xargs -P 4 -I{} sh -c "'$here/graceful' {} < '$f'" \
  | python3 -c "import sys;print('$fam($n) permuted =',sum(int(x) for x in sys.stdin))"
