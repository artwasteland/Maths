#!/bin/bash
# extend.sh family lo hi capms
fam=$1; lo=$2; hi=$3; cap=${4:-80000}
for n in $(seq $lo $hi); do
  t0=$(date +%s%N)
  c=$(node togr.mjs $fam $n | ./graceful)
  t1=$(date +%s%N); ms=$(( (t1-t0)/1000000 ))
  echo "$fam($n) = $c   [${ms}ms]"
  if [ $ms -gt $cap ]; then echo "(stop: >${cap}ms)"; break; fi
done
