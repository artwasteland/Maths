#!/bin/bash
# Two last replay checks (see run-extra.sh), one job at a time at nice 15:
#   SUP2     the (18,46) DAG replay again without cell 12-22, whose children file is not in the
#            repository (replay-SUP reported that cell unreplayable, as it must)
#   W2       the multiprocessing path: run A replayed with --workers 2 must give the same
#            replay.jsonl entries as the single-process T1 run (same seed, same options)
cd "$(dirname "$0")"
PY="${ENUM2_PYTHON:-$HOME/tools/pyenv-maths/bin/python}"
S="${ENUM2_SCRATCH:-<scratch>/scratchpad/v398}"
TOOL=../replay-398.py
job() {
  local name="$1"; shift
  echo "$(date +%FT%T) start $name"
  nice -n 15 "$PY" "$@" > "runs/$name.log" 2>&1
  local rc=$?
  echo "$(date +%FT%T) end $name exit $rc"
}
SUPCELLS=$(cd ../../enum/out-sup/dag-18-46/_parents && ls *.g6 | sed 's/\.g6$//' | grep -v '^12-22$' | paste -sd, -)
job replay-SUP2 "$TOOL" --run-dir ../../enum/out-sup/dag-18-46 --forbidden-set 74 --cells "$SUPCELLS" \
  --fraction 0.05 --seed 20260926 --min-per-shard 2 --whole-max 40 --seeds off --red --out "$S/replay-SUP2"
job replay-W2 "$TOOL" --run-dir "$S/runs/A-16-41" --forbidden-set 398 --fraction 0.02 --seed 20260925 \
  --min-per-shard 3 --whole-max 20 --seeds sample --workers 2 --out "$S/replay-W2"
echo "$(date +%FT%T) final done"
