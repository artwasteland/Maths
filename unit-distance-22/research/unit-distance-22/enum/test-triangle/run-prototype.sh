#!/usr/bin/env bash
# The prototype's per-graph verdicts on the six measurement samples (slow: pure Python; run detached).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
mkdir -p out
for L in 13 14 15 16 17 18; do
    nice -n 10 "$PY" prototype_verdicts.py "data/measure-$L.g6" "out/prototype-$L.txt"
    echo "level $L done $(date +%T)"
done
echo ALL-DONE
