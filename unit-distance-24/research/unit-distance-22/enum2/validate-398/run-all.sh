#!/bin/bash
# The validation jobs after cells398.py, one after another (one heavy process at a time),
# each at nice 15, each logging to runs/<name>.log.  Launch detached:
#   setsid nohup bash run-all.sh > runs/run-all.log 2>&1 < /dev/null &
# A job's failure is recorded and the next job still runs.
cd "$(dirname "$0")"
PY="${ENUM2_PYTHON:-$HOME/tools/pyenv-maths/bin/python}"
S="${ENUM2_SCRATCH:-<scratch>/scratchpad/v398}"
mkdir -p runs
job() {
  local name="$1"; shift
  echo "$(date +%FT%T) start $name"
  nice -n 15 "$PY" "$@" > "runs/$name.log" 2>&1
  local rc=$?
  echo "$(date +%FT%T) end $name exit $rc"
}
[ -d "$S/runs/A-16-41" ] || job make-run-A make-test-run.py --out "$S/runs/A-16-41" --target-n 16 --target-m 41 \
  --shard-size 300 --verify-parents
[ -d "$S/runs/B-16-41-s1of3" ] || job make-run-B make-test-run.py --out "$S/runs/B-16-41-s1of3" --target-n 16 \
  --target-m 41 --shard-size 300 --slice-level 12 --slice-index 1 --slice-count 3
job replay-test replay-test.py
job mode74 mode74.py
job small-n small-n.py
job brute10 brute10.py --red
job engines engines.py --per-source 6 --variants 2 --budget 900
echo "$(date +%FT%T) all done"
