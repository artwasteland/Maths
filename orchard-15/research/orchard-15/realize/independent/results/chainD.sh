#!/bin/bash
ulimit -v 1000000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
W=$1; k=0
while read i j; do
  if [ $((k % 2)) -eq $W ]; then
    s=$(date +%s)
    out=$(timeout 120 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label mut2_drop_${i}_${j} --drop $i $j --no-product --first-triples "2,4,6;0,3,4;0,4,5;0,3,6;0,3,5;0,4,6" 2>&1 | grep -E 'GB\(I\)|IS forced|Traceback|no single' | sed 's/\[mut2_drop_[0-9_]*\] //' | head -2 | tr '\n' ' ')
    e=$(( $(date +%s) - s ))
    [ -z "$out" ] && out="TIMEOUT/none"
    echo "drop $i $j :: ${e}s :: $out"
  fi
  k=$((k+1))
done < results/pairs.txt
echo "=== DONE chainD worker $W ==="
