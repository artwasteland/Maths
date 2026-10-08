#!/usr/bin/env bash
# Reproduce the independent GP-10 recount from the repository root.
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
SCRATCH_DIR=${GP10_RECOUNT_SCRATCH:-/tmp/gp10-recount}
PYTHON_BIN=${GP10_RECOUNT_PYTHON:-<repo>/pyenv-gp10/bin/python}
PATTERNS="$ROOT_DIR/research/unit-distance-22/data/forbidden-74.g6"
JSON_PATTERNS="$ROOT_DIR/research/unit-distance-22/data/forbidden-74.json"
MATCHER="$SCRATCH_DIR/matcher"

ulimit -v 1500000
nice -n 15 mkdir -p "$SCRATCH_DIR"

nice -n 15 cc -O3 -std=c11 -Wall -Wextra -pedantic "$ROOT_DIR/research/gp-10/recount/matcher.c" -lz -o "$MATCHER"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/check_inputs.py" "$JSON_PATTERNS" "$PATTERNS"

nice -n 15 nauty-geng -Cq 8 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --max-pattern-n 7 --survivors "$SCRATCH_DIR/B8p.raw.g6" --witness "$SCRATCH_DIR/B8p.witness.tsv.gz" --summary "$SCRATCH_DIR/B8p.summary"
nice -n 15 nauty-labelg -q < "$SCRATCH_DIR/B8p.raw.g6" > "$SCRATCH_DIR/B8p.canon.g6"
nice -n 15 env LC_ALL=C sort "$SCRATCH_DIR/B8p.canon.g6" > "$SCRATCH_DIR/B8p.sorted.g6"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/compare_lists.py" "$ROOT_DIR/research/gp-10/data/B8p.g6" "$SCRATCH_DIR/B8p.sorted.g6"

nice -n 15 nauty-geng -Cq 9 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --max-pattern-n 8 --survivors "$SCRATCH_DIR/B9p.raw.g6" --witness "$SCRATCH_DIR/B9p.witness.tsv.gz" --summary "$SCRATCH_DIR/B9p.summary"
nice -n 15 nauty-labelg -q < "$SCRATCH_DIR/B9p.raw.g6" > "$SCRATCH_DIR/B9p.canon.g6"
nice -n 15 env LC_ALL=C sort "$SCRATCH_DIR/B9p.canon.g6" > "$SCRATCH_DIR/B9p.sorted.g6"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/compare_lists.py" "$ROOT_DIR/research/gp-10/data/B9p.g6" "$SCRATCH_DIR/B9p.sorted.g6"

nice -n 15 nauty-geng -Cq 8 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --summary "$SCRATCH_DIR/B8-all74.summary"
nice -n 15 nauty-geng -Cq 9 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --summary "$SCRATCH_DIR/B9-all74.summary"

nice -n 15 nauty-geng -Cq 10 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --survivors "$SCRATCH_DIR/B10.raw.g6" --witness "$SCRATCH_DIR/B10.witness.tsv.gz" --summary "$SCRATCH_DIR/B10.summary"
nice -n 15 nauty-labelg -q < "$SCRATCH_DIR/B10.raw.g6" > "$SCRATCH_DIR/B10.canon.g6"
nice -n 15 env LC_ALL=C sort "$SCRATCH_DIR/B10.canon.g6" > "$SCRATCH_DIR/B10.sorted.g6"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/compare_lists.py" "$ROOT_DIR/research/gp-10/data/B10.g6" "$SCRATCH_DIR/B10.sorted.g6"

nice -n 15 nauty-geng -Cq 10 | nice -n 15 "$MATCHER" --patterns "$PATTERNS" --drop-index 0 --summary "$SCRATCH_DIR/B10-drop0.summary"

nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/verify_witness.py" --patterns "$PATTERNS" --witness "$SCRATCH_DIR/B8p.witness.tsv.gz"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/verify_witness.py" --patterns "$PATTERNS" --witness "$SCRATCH_DIR/B9p.witness.tsv.gz"
nice -n 15 "$PYTHON_BIN" "$ROOT_DIR/research/gp-10/recount/verify_witness.py" --patterns "$PATTERNS" --witness "$SCRATCH_DIR/B10.witness.tsv.gz"

nice -n 15 printf '%s\n' "recount outputs are in $SCRATCH_DIR"
