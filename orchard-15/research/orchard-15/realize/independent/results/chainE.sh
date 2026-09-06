#!/bin/bash
ulimit -v 1100000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
for pr in "0 1" "0 5"; do
  set -- $pr
  echo "=== slow pair drop $1 $2 : gb-only first ==="
  timeout 900 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label mut2slow_gb_${1}_${2} --drop $1 $2 --gb-only 2>&1 | grep -E 'dropped|frame=|GB\(I\)|Traceback'
  echo "=== slow pair drop $1 $2 : single-triple loop ==="
  timeout 1500 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label mut2slow_${1}_${2} --drop $1 $2 --no-product --first-triples "2,4,6;0,3,4;0,4,5;0,3,6;0,3,5;0,4,6" 2>&1 | grep -E 'GB\(I\)|IS forced|no single|Traceback|verdict' | cut -c1-200
done
echo "=== DONE chainE ==="
