#!/bin/bash
ulimit -v 1300000
PY=~/tools/pyenv-maths/bin/python
cd <repo>/research/orchard-15/realize/independent
echo "=== selftest ==="
timeout 1500 $PY -u check.py selftest 2>&1 | grep -v 'IS forced'
echo "=== controls ==="
timeout 2400 $PY -u check.py controls --sat-budget 240 2>&1 | grep -v 'IS forced'
echo "=== DONE chainB ==="
