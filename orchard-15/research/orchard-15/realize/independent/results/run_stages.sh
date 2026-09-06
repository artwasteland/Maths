#!/bin/bash
ulimit -v 1300000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
echo "=== target all-forced frame1 ===" 
timeout 900 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label target_frame1_allforced --all-forced 2>&1 | grep -v '^{'
echo "=== target frame2 (disjoint from frame1) ==="
timeout 900 $PY -u check.py run --pts-file ../pts-13-23-pseudoline.txt --label target_frame2 --avoid-frame 0,2,1,3 --all-forced 2>&1 | grep -v '^{'
echo "=== controls ==="
timeout 1800 $PY -u check.py controls 2>&1 | grep -v '^{'
echo "=== DONE stages ==="
