#!/bin/bash
# Start run-final.sh detached once the engines re-run has finished.
cd "$(dirname "$0")"
setsid nohup bash -c 'until grep -q "end engines" runs/engines-launch.log 2>/dev/null; do sleep 20; done; bash run-final.sh' \
  > runs/run-final.log 2>&1 < /dev/null &
echo "$!" > runs/run-final.pid
echo "queued run-final pid $!"
