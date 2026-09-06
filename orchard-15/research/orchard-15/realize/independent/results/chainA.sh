#!/bin/bash
ulimit -v 1300000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
echo "=== cofactors frame1 (0,2,1,3) triple 0,3,4 ==="
timeout 900 $PY -u check.py cofactors --pts-file ../pts-13-23-pseudoline.txt --frame 0,2,1,3 --triple 0,3,4 --label cofactors_frame1_034 2>&1
echo "=== cofactors frame2 (4,8,5,7) triple 0,1,2 ==="
timeout 900 $PY -u check.py cofactors --pts-file ../pts-13-23-pseudoline.txt --frame 4,8,5,7 --triple 0,1,2 --label cofactors_frame2_012 2>&1
echo "=== DONE chainA ==="
