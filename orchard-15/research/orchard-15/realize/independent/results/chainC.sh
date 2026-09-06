#!/bin/bash
ulimit -v 1300000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
echo "=== mutations: drop one block (single-triple test only) ==="
for i in $(seq 0 22); do
  timeout 600 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label mut_drop_$i --drop $i --no-product 2>&1 | grep -E 'dropped|GB\(I\)|IS forced' | head -3
done
echo "=== DONE chainC ==="
