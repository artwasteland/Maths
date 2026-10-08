#!/bin/bash
# Run one validation job detached from the calling shell, at nice 15, logging to runs/<name>.log.
#   bash detach.sh <name> <script.py> [args...]
# Prints the PID; poll the log, stop by that PID only.
set -e
cd "$(dirname "$0")"
mkdir -p runs
name="$1"
shift
PY="${ENUM2_PYTHON:-$HOME/tools/pyenv-maths/bin/python}"
setsid nohup nice -n 15 "$PY" "$@" > "runs/$name.log" 2>&1 < /dev/null &
echo "$!" > "runs/$name.pid"
echo "started $name pid $!"
