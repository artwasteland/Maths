#!/bin/bash
# driver.sh — run the extension computations in sequence, checkpointed.
# Each run is skipped if its .done marker exists, and resumes from its
# checkpoint file otherwise, so the driver is safe to re-run after any death.
set -u
cd "$(dirname "$0")"
mkdir -p runs

run() {
  local tag=$1; shift
  if [ -f "runs/$tag.done" ]; then echo "== $tag already done"; return 0; fi
  echo "== $tag start $(date -u +%FT%TZ)"
  ./count "$@" -c "runs/$tag.ck" > "runs/$tag.out" 2> "runs/$tag.log"
  local rc=$?
  if [ $rc -eq 0 ]; then
    touch "runs/$tag.done"
    echo "== $tag DONE $(date -u +%FT%TZ)"
  else
    echo "== $tag FAILED rc=$rc $(date -u +%FT%TZ) (see runs/$tag.log)"
  fi
  return 0
}

run n6-L14 -n 6 -L 14 -k 5 -t 4 --progress 120
run n7-L12 -n 7 -L 12 -k 4 -t 4 --progress 120
run n5-L20 -n 5 -L 20 -k 6 -t 4 --engine mask --progress 300
run n6-L15 -n 6 -L 15 -k 5 -t 4 --progress 300
run n7-L13 -n 7 -L 13 -k 5 -t 4 --progress 300
echo "== ALL RUNS COMPLETE $(date -u +%FT%TZ)"
