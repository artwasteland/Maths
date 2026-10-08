#!/bin/bash
# Re-run engines.py (with the structured decider checks) detached, once run-extra.sh has finished.
cd "$(dirname "$0")"
PY="${ENUM2_PYTHON:-$HOME/tools/pyenv-maths/bin/python}"
setsid nohup bash -c "until grep -q 'extra done' runs/run-extra.log 2>/dev/null; do sleep 20; done; \
  echo \"\$(date +%FT%T) start engines\"; nice -n 15 $PY engines.py --per-source 6 --variants 2 --budget 900 \
  > runs/engines.log 2>&1; rc=\$?; echo \"\$(date +%FT%T) end engines exit \$rc\"" > runs/engines-launch.log 2>&1 < /dev/null &
echo "$!" > runs/engines-launch.pid
echo "queued engines pid $!"
