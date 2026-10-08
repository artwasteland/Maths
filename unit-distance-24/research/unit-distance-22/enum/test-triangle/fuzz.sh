#!/usr/bin/env bash
# Fuzz: (1) unit-distance graphs with known embeddings (fuzz_ud.py): never refuted, every tu tree followed by the
# embedding and its mirror to a true unit leaf; (2) random G(n, p) graphs and near-lattice graphs (fuzz_random.py):
# every certificate accepted by the dev checker, and the verdicts equal the prototype's on a subsample.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
BIN=${UDTRIANGLE:-../../filter/udtriangle}
COUNT=${COUNT:-3000}
SEED=${SEED:-20260926}
mkdir -p out/fuzz
nice -n 10 "$PY" fuzz_ud.py out/fuzz "$COUNT" "$SEED"
nice -n 10 "$BIN" < out/fuzz/fuzz-ud.g6 > out/fuzz/fuzz-ud.out
nice -n 10 "$PY" fuzz_ud.py --check out/fuzz
nice -n 10 "$PY" devcheck_tri.py out/fuzz/fuzz-ud.g6 out/fuzz/fuzz-ud.out
RCOUNT=${RCOUNT:-3000}
nice -n 10 "$PY" fuzz_random.py out/fuzz/fuzz-random.g6 "$RCOUNT" "$SEED"
nice -n 10 "$BIN" < out/fuzz/fuzz-random.g6 > out/fuzz/fuzz-random.out
nice -n 10 "$PY" devcheck_tri.py out/fuzz/fuzz-random.g6 out/fuzz/fuzz-random.out
nice -n 10 "$PY" prototype_verdicts.py out/fuzz/fuzz-random.g6 out/fuzz/fuzz-random.prototype.txt
nice -n 10 "$PY" agree.py out/fuzz/fuzz-random.g6 out/fuzz/fuzz-random.prototype.txt out/fuzz/fuzz-random.out fuzz-random
