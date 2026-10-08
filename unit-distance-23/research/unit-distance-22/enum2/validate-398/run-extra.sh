#!/bin/bash
# Larger replays after run-all.sh, one job at a time at nice 15 (see run-all.sh).
#   C    a Mode-398 (17,43) run (reach, shards of 2000), then a 1% replay of it with seeds and red controls
#   U22  the original u(22) run, levels 11-12, 2% of every shard (Mode 74, production data)
#   SUP  the unpruned (18,46) DAG of the repository (run-dag.py manifests, Mode 74), every cell whose
#        parent file is in the repository, 5% of every shard
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
[ -d "$S/runs/C-17-43" ] || job make-run-C make-test-run.py --out "$S/runs/C-17-43" --target-n 17 --target-m 43 \
  --shard-size 2000
job replay-C "$TOOL" --run-dir "$S/runs/C-17-43" --forbidden-set 398 --fraction 0.01 --seed 20260926 \
  --min-per-shard 2 --whole-max 40 --seeds full --red --out "$S/replay-C"
job replay-U22 "$TOOL" --run-dir <repo>/research/unit-distance-22/enum/out-22/dag-22-61-f12 \
  --forbidden-set 74 --levels 11-12 --fraction 0.02 --seed 20260926 --min-per-shard 2 --whole-max 40 --red \
  --out "$S/replay-U22"
SUPCELLS=$(cd ../../enum/out-sup/dag-18-46/_parents && ls *.g6 | sed 's/\.g6$//' | paste -sd, -)
job replay-SUP "$TOOL" --run-dir ../../enum/out-sup/dag-18-46 --forbidden-set 74 --cells "$SUPCELLS" \
  --fraction 0.05 --seed 20260926 --min-per-shard 2 --whole-max 40 --seeds off --red --out "$S/replay-SUP"
echo "$(date +%FT%T) extra done"
