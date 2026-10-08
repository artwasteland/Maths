#!/bin/bash
# Copy the replay summaries (not the per-parent replay.jsonl files, which are large) from the scratch
# directory into runs/replay/, and the one-change diff of the patched run-dag2.py used for the test runs.
cd "$(dirname "$0")"
S="${ENUM2_SCRATCH:-<scratch>/scratchpad/v398}"
mkdir -p runs/replay
for d in replay-C replay-U22 replay-SUP replay-SUP2 replay-W2 replay-test/T0 replay-test/T1 replay-test/T2 \
         replay-test/T3 replay-test/T4 replay-test/T5; do
  name=$(echo "$d" | sed 's#replay-test/#replay-test-#')
  [ -f "$S/$d/summary.json" ] && cp "$S/$d/summary.json" "runs/replay/$name.summary.json"
  [ -f "$S/$d/red.json" ] && cp "$S/$d/red.json" "runs/replay/$name.red.json"
done
cp "$S/runs/A-16-41.run-dag2.diff" runs/replay/run-dag2-398.diff
ls -la runs/replay
