#!/bin/bash
# Start run-extra.sh detached once run-all.sh has finished (so only one heavy job runs at a time).
cd "$(dirname "$0")"
setsid nohup bash -c 'until grep -q "all done" runs/run-all.log 2>/dev/null; do sleep 20; done; bash run-extra.sh' \
  > runs/run-extra.log 2>&1 < /dev/null &
echo "$!" > runs/run-extra.pid
echo "queued run-extra pid $!"
