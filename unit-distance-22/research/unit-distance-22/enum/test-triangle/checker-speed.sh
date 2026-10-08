#!/usr/bin/env bash
# CPU cost of the (pure Python) dev checker per certificate, for scale against the prover's.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
T=$(mktemp)
trap 'rm -f "$T"' EXIT
for f in measure-17 measure-18; do
    /usr/bin/time -o "$T" -f "%U %S" nice -n 10 "$PY" devcheck_tri.py "data/$f.g6" "out/$f.out" > /dev/null
    read -r u s < "$T"
    certs=$(/usr/bin/grep -c -v '"verdict":"pass"' "out/$f.out")
    echo "$f: dev checker $(echo "scale=1; $certs / ($u + $s)" | bc) certificates/CPU-s ($certs certificates, $(echo "$u + $s" | bc) s)"
done
