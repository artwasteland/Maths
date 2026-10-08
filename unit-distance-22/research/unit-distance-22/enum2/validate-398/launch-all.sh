#!/bin/bash
# Launch run-all.sh detached from the calling shell; prints its PID (stop by that PID only).
cd "$(dirname "$0")"
mkdir -p runs
setsid nohup bash run-all.sh > runs/run-all.log 2>&1 < /dev/null &
echo "$!" > runs/run-all.pid
echo "started run-all pid $!"
