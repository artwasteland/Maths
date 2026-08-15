#!/bin/bash
# par.sh family n  -> parallel sharded exact count (root-label sharding across 4 cores)
fam=$1; n=$2
f=/tmp/g_${fam}${n}.txt
node togr.mjs $fam $n > "$f"
m=$(head -1 "$f" | cut -d' ' -f2)
seq 0 $m | xargs -P 4 -I{} sh -c "./graceful {} < $f" \
  | python3 -c "import sys;print('$fam($n) =',sum(int(x) for x in sys.stdin))"
