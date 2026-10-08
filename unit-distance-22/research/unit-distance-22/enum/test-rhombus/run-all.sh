#!/usr/bin/env bash
# The rhombus prover's tests. Each writes runs/<name>.txt and ends with a PASS or FAIL line; the script
# stops at the first failure. Run from anywhere; everything is niced; at most two cores are used.
#
#   units.py            (standard library)  K2,3, the six gadgets, Moser, rhombus, W6, AMP's 56, bad input,
#                                           tampered certificates (dev replay, in process)
#   agreement.py        (networkx)          udrhombus = rhombus_probe.py on every descent sample graph
#   exact-crosscheck.py (standard library)  verdict, pair and edge = an exact rational computation (no modulus)
#   b10.py              (mpmath)            GP-10's 32,653 embedded graphs: none refuted, every tu confirmed in
#                                           the exact embedding at 80 digits
#   mutants.py          (standard library)  five compile-time mutants caught; the counted fallback
#   through-checker.py  (standard library)  the binding controls of RHOMBUS-SPEC amendment 2 THROUGH THE CHECKER
#                                           check/udcheck_rhombus.py: known56, B10, mutants, int64 wrap, samples
#   bench.py            (standard library)  graphs per CPU-second on the level 13 to 19 samples
#   e2e.py              (standard library)  default off byte-identical; (16,41), (17,43), (18,46) plain, --rhombus,
#                                           --triangles, replayed by the real checker; red controls (about 45 minutes)
#   filterset.py        (standard library)  --prune-filter-set 74: same level files; a planted superset still caught
#   runbook-rh.py       (standard library)  coordination/cloud-workers/u23-slice.sh with U23_RHOMBUS=1 and U23_TRIANGLES=1
#   checkpar.py         (standard library)  prune.py's parallel replay above PRUNE_CHECK_PARALLEL_ABOVE records: nothing
#                                           changes below it; same outputs above it; a planted bad certificate caught in
#                                           its chunk; timing against the landed prune.py (about 30 minutes)
#   vchain.py           (standard library)  verify-chain.py derives the required cells from the target (G5): the
#                                           reviewer's tamperings refused, explicit PARTIAL, --summary-only; resume
#                                           reruns a prune step whose target, checker or ACCEPT line is not current
#   g5close.py          (standard library)  G5 round 2: the closure read's reproductions, landed tool against fixed, on
#                                           the runbook's own (16,41) slices (keep swap on resume, seed 24, shares 75 of 74,
#                                           80 and -6, [12,0,0], hashes.json and G4 bindings, native counts, (16,40))
#
# Environment: GP10_PY (default ~/tools/pyenv-gp10/bin/python, needs networkx and mpmath), MATHS_PY (default
# ~/tools/pyenv-maths/bin/python, runs the pinned kernels), SKIP_LONG=1 skips e2e.py, filterset.py, runbook-rh.py, checkpar.py, vchain.py and g5close.py.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
GP10_PY=${GP10_PY:-$HOME/tools/pyenv-gp10/bin/python}
MATHS_PY=${MATHS_PY:-$HOME/tools/pyenv-maths/bin/python}
cd "$HERE"
(cd ../../filter && make -s udrhombus udtriangle)
mkdir -p runs
run() {   # name python script args...
  local name=$1 py=$2; shift 2
  echo "== $name"
  nice -n 10 "$py" "$@" > "runs/$name.txt" 2>&1 || { tail -5 "runs/$name.txt"; echo "== $name FAILED"; exit 1; }
  tail -1 "runs/$name.txt"
}
run units "$MATHS_PY" units.py
run agreement "$GP10_PY" agreement.py
run exact-crosscheck "$MATHS_PY" exact-crosscheck.py
run b10 "$GP10_PY" b10.py
run mutants "$MATHS_PY" mutants.py
run through-checker "$MATHS_PY" through-checker.py
run bench-w1 "$MATHS_PY" bench.py samples/w1-measure-13.g6 samples/w1-measure-14.g6 samples/w1-measure-15.g6 \
    samples/w1-measure-16.g6 samples/w1-measure-17.g6 samples/w1-measure-18.g6 samples/w1-measure-19.g6
if [ "${SKIP_LONG:-0}" != 1 ]; then
  run e2e "$MATHS_PY" e2e.py --phases I,IR,C,R --jobs 2
  run filterset "$MATHS_PY" filterset.py --jobs 2
  run runbook-rh "$MATHS_PY" runbook-rh.py
  run checkpar "$MATHS_PY" checkpar.py --jobs 2
  run vchain "$MATHS_PY" vchain.py --jobs 2
  run g5close "$MATHS_PY" g5close.py --jobs 2
fi
echo "ALL RHOMBUS TESTS PASSED"
