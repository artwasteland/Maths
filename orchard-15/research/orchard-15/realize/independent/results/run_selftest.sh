#!/bin/bash
ulimit -v 1300000
cd <repo>/research/orchard-15/realize/independent
timeout 1800 ~/tools/pyenv-maths/bin/python -u check.py selftest 2>&1
echo "=== DONE selftest ==="
