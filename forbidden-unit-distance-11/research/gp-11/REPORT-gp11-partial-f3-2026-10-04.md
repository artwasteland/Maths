GP-11 partial f3 — 2026-10-04

Added `research/gp-11/tools/b11_stopped.py` and `test_b11_stopped.py`.
Added the optional `--not-run FILE|auto` path to `b11_residue.py`,
`--round-input`/`--assembly` to `make_packets.py`, and stopped-round provenance
binding to `b11_final.py`. The wrapper also supplies lean's existing `--scratch`
option beside staging, preventing cross-filesystem snapshot renames. Default
residue assembly still requires all 80 returns.
Other additions are this report and `b11-endgame-dry/` (saved returns, logs,
assembly, packets and validation receipts).
No frozen checker/input, F9/F10 list, pipeline stage, campaign code, or git history/remote was changed.

The stopped path validates checked bundles and the pinned f3 input/predecessors.
Each returned assignment must equal its entire driver shard, using the first
eight SHA256 digest bytes interpreted big-endian modulo 80. The explicit sorted
NOT RUN list must complement the returned shards. A present invalid return is
an error. Missing returns contribute only their original f3-input UNKNOWNs;
interrupted `/tmp/gp11-f3-NNN` states are not read. Exact shard equality and the
shard partition prove disjoint, exhaustive graph coverage. Final UNKNOWN must
equal the original 525 minus f3 decisions minus independently admitted targets.
Late returns during assembly are rejected.

Lean assembly emits generic UNKNOWN placeholders, so the wrapper restores the
remaining carried records byte for byte, then structurally checks the result.
`assembly.json` records all shard/graph lists, carried-record hashes and admitted
targets, and binds `residue-audit.json` as an output. The final launcher validates
that binding, copies both receipts, and includes the stopped provenance in its seal.

The packet route is an additive round-input source, not a fabricated checked
bundle. Returned UNKNOWN packets use exactly the f3 bundles named by the assembly;
carried packets use exact input record bytes and prior budgets, marked **NOT RUN**,
with no invented f3 attempt/frontier/checker receipt. Source assignments cannot
overlap. `--select` must match the assembly's current UNKNOWN set, including after
analyst admissions. No predecessors are passed to packet generation.

Validation: **221 tests pass** (45 stopped-f3, 104 workflow, 38 endgame,
22 control-campaign, 12 packet). Expected graph sets and shard memberships are
hand-written. Every new rejection has a guard-disable case: **all 37 go red**;
the existing 129 also go red. Omitting scratch placement also goes red. The tiny integration fixture uses two graphs,
executes lean assembly/structural checking, preserves the exact carried bytes,
and prepares a final rehearsal seal containing the NOT RUN provenance.
Carried packets also pass tiny-fixture campaign prepare/scan without an analyst run. Other
cases cover absent/all returns, truncated/wrong shard assignments, malformed
lists, overlap, late returns, source tampering/re-export and admitted carried targets.
All fixture commands use nice 15 and a 540-second cap; the longest normal test suite
takes under 20 seconds. Reproduce sequentially:

```bash
PY=<repo>/pyenv-gp10/bin/python
T=research/gp-11/tools
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_b11_stopped.py" --mutations
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_b11_workflow.py" --mutations
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_b11_endgame.py" --mutations
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_control51_campaign.py"
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_make_packets.py"
```

The real dry snapshot was captured at **2026-10-04 02:06:42 UTC**:
**25 returned shards** (`000`–`023`, `025`), **55 NOT RUN shards** (`024`,
`026`–`079`). Explicit lists are in `b11-endgame-dry/not-run.json`,
`snapshot.json`, and the assembly receipt. The returns assign 144 graphs:
20 embedded, zero refuted, 124 UNKNOWN. The other 381 graphs are carried.
The published residue is **505 UNKNOWN = 525 − 20 − 0 admitted targets**,
and packet generation produced **505 packets** (124 returned, 381 carried).

Assembly passed `STRUCTURE OK`. The independent `b11-endgame-dry/verify.py`
check passed exact shard/set coverage, all 381 carried records' byte equality
in assembly and packets, returned packet records, and every packet file hash.
`b11-endgame-dry/validation.json` retains counts, source/output hashes and test
log hashes. Logs are in that directory and `test-logs/`.

The successful structural assembly took about 36 minutes under nice 15;
packets took about one minute. Earlier aggregate caps of 540 and 1800 seconds
expired without publication. Another attempt exposed the snapshot rename
`EXDEV`, fixed by the additive scratch option; the tiny fixture reproduces it
when that option is omitted. Their logs are retained as
`assembly-timeout-{540,1800}s.log` and `assembly-cross-device.log`. Only the
failed attempts' unpublished builder scratch was removed. The successful
assembly had a 3600-second cap; this was assembly/structural validation, not
a proof replay or analyst search.

The session permits writes only in this worktree and `/tmp`; it cannot write
`<repo>/b11-endgame-dry/`. Dry artifacts are instead generated in
`<repo>/b11-endgame-dry/`. This is the one requested
destination not fulfilled here. No campaign or full population checker was
started, and the live f3 runner was not stopped. The dry run uses a saved snapshot
of current checked returns, not a claim that the live process stopped.

Coordinator commands, in order (run on the host, where the f3 process tree is
visible). First find the top-level L3/f3 launcher, including any enclosing local
loop; selecting only a driver/shard would allow its parent to start more work:

```bash
cd <repo>
set -euo pipefail
PY=<repo>/pyenv-gp10/bin/python
nice -n 15 pgrep -af 'gp11-frontier|f3-input|local-f3'
CANDIDATE_PID=REPLACE_WITH_MATCHED_F3_PID
nice -n 15 pstree -aps "$CANDIDATE_PID"
F3_PID=REPLACE_WITH_TOP_LEVEL_F3_LAUNCHER_PID

# Freeze the tree before collecting children; kill descendants even if they
# created new process groups/sessions. pidfds prevent signalling a reused PID.
nice -n 15 "$PY" -B - "$F3_PID" <<'PY'
import os, signal, sys, time
from pathlib import Path
root = int(sys.argv[1])
assert root > 1 and root != os.getpid()
print('Stopping tree:', root, Path(f'/proc/{root}/cmdline').read_bytes().replace(b'\0', b' '), flush=True)
queue, frozen = [root], {}
while queue:
    pid = queue.pop(0)
    if pid in frozen:
        continue
    try:
        fd = os.pidfd_open(pid)
        signal.pidfd_send_signal(fd, signal.SIGSTOP)
    except ProcessLookupError:
        continue
    frozen[pid] = fd
    # Do not enumerate children while this parent can still fork.
    while True:
        try:
            state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
        except FileNotFoundError:
            break
        if state in ('T', 't', 'Z', 'X'):
            break
        time.sleep(0.01)
    for task in Path(f'/proc/{pid}/task').glob('*/children'):
        try:
            queue.extend(map(int, task.read_text().split()))
        except FileNotFoundError:
            pass
for pid, fd in reversed(list(frozen.items())):
    try:
        signal.pidfd_send_signal(fd, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.close(fd)
print('Killed PIDs:', sorted(frozen))
PY
nice -n 15 pgrep -af 'gp11-frontier|f3-input|local-f3' || [ "$?" -eq 1 ]
```

Inspect the last listing for any separate f3 launcher before continuing. Keep
the interrupted shard directories and returned bundles. Do not run git merge,
reset, push, or the frontier launcher. Then assemble into a fresh output:

```bash
T="$PWD/research/gp-11/tools"
ROUND="$PWD/research/gp-11/pipeline/cloud/f3-input"
F3=<repo>/research/gp-11/pipeline/cloud
CHEAP=<repo>/population-cheap-state
WORK=<repo>/b11-endgame
nice -n 15 mkdir -p "$WORK"

# Compute and retain the explicit list after stopping. Assembly validates every
# summary-bearing return; a corrupt return is never silently treated as absent.
nice -n 15 "$PY" -B - "$F3" "$WORK/f3-not-run.json" <<'PY'
import json, sys
from pathlib import Path
returned = sorted(int(p.name[3:]) for p in Path(sys.argv[1]).glob('f3-[0-9][0-9][0-9]') if (p/'summary.json').exists())
missing = sorted(set(range(80)) - set(returned))
with Path(sys.argv[2]).open('x') as stream:
    stream.write(json.dumps(missing) + '\n')
print('Returned candidates:', returned)
print('NOT RUN:', missing)
PY
nice -n 15 "$PY" -B "$T/b11_residue.py" --round "$ROUND" --f3 "$F3" \
  --not-run "$WORK/f3-not-run.json" --cheap "$CHEAP" --out "$WORK/assembly-0" --python "$PY"

# Use only the checked returns pinned by that assembly, plus the disjoint carry.
mapfile -t f3 < <(nice -n 15 "$PY" -B - "$WORK/assembly-0/residue-audit.json" <<'PY'
import json, sys
from pathlib import Path
for item in json.loads(Path(sys.argv[1]).read_text())['f3']:
    print(item['bundle'])
PY
)
nice -n 15 "$PY" -B "$T/make_packets.py" "${f3[@]}" --round-input "$ROUND" \
  --assembly "$WORK/assembly-0" --select "$WORK/assembly-0/UNKNOWN.g6" --python "$PY" --out "$WORK/packets-0"
nice -n 15 "$PY" -B "$T/b11_campaign.py" prepare --assembly "$WORK/assembly-0" \
  --packets "$WORK/packets-0" --out "$WORK/campaign-0" --python "$PY" --seconds 5400 --check-seconds 540
nice -n 15 "$PY" -B "$T/b11_campaign.py" scan --out "$WORK/campaign-0"
nice -n 15 "$PY" -B "$T/b11_campaign.py" run --out "$WORK/campaign-0" --jobs 2 || [ "$?" -eq 3 ]
nice -n 15 "$PY" -B "$T/b11_campaign.py" status --out "$WORK/campaign-0"
```

`run` exit 3 means unresolved cases remain. Use a new cumulative export and new
assembly for each subsequent pass, retaining the same NOT RUN list:

```bash
nice -n 15 "$PY" -B "$T/b11_campaign.py" export --out "$WORK/campaign-0" --destination "$WORK/admitted-1"
nice -n 15 "$PY" -B "$T/b11_residue.py" --round "$ROUND" --f3 "$F3" \
  --not-run "$WORK/f3-not-run.json" --cheap "$CHEAP" --analyst-export "$WORK/admitted-1" \
  --out "$WORK/assembly-1" --python "$PY"
```

Choose **two analysts** on this 7.6 GiB desktop. Control 5.1's 32 saved
`<repo>/control51-campaign/results/*/attempt-0001/event.json`
analyst receipts record a minimum available
memory of 4,813,152 KiB (4.59 GiB) during its two-analyst campaign. They do not
record Codex/analyst RSS; checker RSS is not a substitute. Planning assumption:
allow 1 GiB per analyst/controller plus 1 GiB for the serialized heavy process,
and retain the existing 1.5 GiB system-available floor. These are allowances,
not measured per-process maxima. The shared heavy lock and memory guards remain
in force; f3 must be stopped first.

For the requested real-data dry destination, set
`WORK=<repo>/b11-endgame-dry` in the assembly/packet commands above
and stop after packet generation. Use a fresh directory; do not prepare or run
the campaign for that dry run. The existing final-check runbook applies after
UNKNOWN is empty; the new stopped provenance is carried automatically.
