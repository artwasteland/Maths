#!/usr/bin/env bash
# Strong positive control: follow every B10 tu tree with GP-10's real embedding (b10_embed_check.py).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
RECORDS=../../../gp-10/cloud/lean3/records.jsonl.gz
VERDICTS=${1:-out/B10-embedded.out}
nice -n 10 "$PY" b10_embed_check.py "$RECORDS" data/B10-embedded.g6 "$VERDICTS"
