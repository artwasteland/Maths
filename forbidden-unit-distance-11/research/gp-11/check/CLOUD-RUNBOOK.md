# GP-11 B10 control replay

The full B10 replay was not run on the shared desktop by job A.
GP-10's recorded full replay took 3156 seconds on a cloud worker.
This run must recheck all 33162 certificates, not just compare an old report.
Budget at least an hour on a dedicated worker; retain the logs and run tree.
No new Python dependencies are required.

Use the project's pinned GP-10 environment (`sympy 1.14.0`, `python-flint 0.9.0`,
NetworkX as recorded by that environment) and nauty 2.8.8 at
`/usr/bin/nauty-labelg`. The report records the actual environment.
The job-A desktop tests used Python 3.12.3 and NetworkX 3.7, with the
SymPy and python-flint versions above. GP-10's recorded cloud run used Python 3.11.15.
The existing frozen checker/kernel SHA-256 pins are enforced at import.
The final record hash is checked when the scratch tree is built.
Do not run `build_bundle.sh`: its destructive OUT-directory behavior is unnecessary here.

From the repository root, using a fresh output path:

```sh
set -eu
GP11_PY=<repo>/pyenv-gp10/bin/python
GP11_WORK=/tmp/gp11-control-replay
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/tools/prepare_controls.py "$GP11_WORK"
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/tools/small_controls.py "$GP11_WORK/tree" > "$GP11_WORK/small-controls.txt" 2>&1
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/check/gp11check.py "$GP11_WORK/tree" --require-complete-b10 > "$GP11_WORK/B10-check.txt" 2>&1
tail -3 "$GP11_WORK/B10-check.txt"
```

On a cloud worker set GP11_PY to its equivalent pinned interpreter path.
The guard runs one command at a time, caps address space at 1024000000 bytes,
sets numerical thread counts to one, and checks MemAvailable every 0.5 seconds.
It kills the command's process group if available memory falls below 1572864 KiB.
A resource stop is not a control PASS.
Keep a watcher on the log and the process; a completed command must be followed
by the explicit complete-control line below.

Required final lines include:

```
ACCEPT run verified
PASS B10 COMPLETE derived=324
```

Read `tree/checked/report.json` too: profile B10; counts embedded=32653,
refuted=509, unknown=0; conditional=false; conditional_minimal=[];
direct_rejections=0; minimal_count=324; minimal_file=L10.g6.
The exact derived list is compared against the canonical ten-vertex F10 entries
by `complete_b10`; cardinality alone cannot pass.
`checked/F10-provenance.json` records that comparison.
The 324 are not supplied as forbidden axioms to the B10 replay.

For deployment copy the entire verified tree to B11_RUN/controls/B10, and
its named11 directory to B11_RUN/controls/named11 (ordinary copies, no external
symlinks). Point the six lower control names and regressions at the corresponding
directories under controls/B10/controls, as in FORMAT.md.
Update absolute frozen-input paths if moving machines, then replay on that machine.
B11 will replay the controls again before checking its own records; archived
receipts do not bypass that step.
Freeze and commit PREDICTIONS.md before beginning the B11 run.

Retain the full scratch tree, B10-check.txt, small-controls.txt, F10-provenance.json,
environment record and source hashes for the coordinator and reviewer.
Only the coordinator commits or lands changes; this job runs no state-changing git commands.
