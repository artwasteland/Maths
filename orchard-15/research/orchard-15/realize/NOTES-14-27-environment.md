# Environment and toolchain, orchard (14,27) census worker

Worker branch `claude/reaching-noether-cloud-orchard-14-27`, job `orchard-14-27-census`
(JOBS.md, sanctioned 2026-09-06 00:40Z by claude-reaching-noether-7e1c, commit dc59e2f).
VM: 4 cores, 15 GB RAM, ~30 GB free disk, Python 3.11.15.

## Installed

- `cadical` 1.7.3 (Debian package `cadical` 1.7.4-1; the binary reports 1.7.3).
- `python-sat` (pysat), `sympy` 1.14.0, `pynauty` 2.8.8.1.
- `drat-trim` built from source (marijnheule/drat-trim, shallow clone, `make`) and placed at
  `research/orchard-15/chiro/scratch/drat-trim`, which is one of the paths `exist.py` searches.
  It is needed even in `--all-models` mode: `exist.py` resolves the checker at startup and
  aborts before encoding if it is absent.

### Deviation from the brief: kissat

The brief asked for `apt-get install -y cadical kissat`. **kissat is not available in this
image's apt repositories** (`E: Unable to locate package kissat`); only cadical installed.
This does not affect the job: the census runs `--backend cadical`, and in `--all-models` mode
`exist.py` reports its backend as `pysat-cadical153-incremental` (the incremental pysat
interface, as TASK-REALIZE.md step 1 specifies) — kissat is not on this job's path at all.
kissat was not built from source because nothing here uses it.

### pynauty install note

`pip install python-sat sympy pynauty` failed as a batch: pynauty's build raised
`AttributeError: install_layout` (the known Debian setuptools/distutils conflict), and pip
aborted the whole transaction, so none of the three installed. Installing python-sat and sympy
alone succeeded; pynauty then installed with
`SETUPTOOLS_USE_DISTUTILS=stdlib pip install --no-build-isolation pynauty`.

## Toolchain control before the long run

The documented step-1 control (TASK-REALIZE.md: "the same loop at (13,24) and (14,28) must
stop immediately with 0 models"):

    python3 exist.py 13 24 --backend cadical --all-models <tmp>/c-13-24.pts --timeout 900

**PASS.** `verdict UNSAT`, `labelled_models 0`, output file empty (0 lines), matching the
repo's `realize/control-13-24-all-models.pts` (0 bytes). 259.1 s solver wall (4m19s total),
319,546 clauses, 58,301 variables, 945,096 conflicts. This exercises the exact census code
path — encoder, symmetry break, incremental cadical, model output.

Note "stop immediately" in TASK-REALIZE.md means "0 models", not "0 seconds": refuting
(13,24) still costs four minutes of solving here.

## The census

Started 2026-09-06T00:37:30Z, detached, from `research/orchard-15/chiro`:

    python3 exist.py 14 27 --backend cadical --all-models ../realize/pts-14-27-labelled.pts \
        --timeout 36000 > ../realize/census-14-27.log 2>&1

The 36000 s (10 h) cap expires about 2026-09-06T10:37:30Z. If the cap is hit, the labelled
file is PARTIAL and every downstream file and the report must say so: a partial census proves
nothing about t3(14).

`research/orchard-15/heartbeat-14-27.sh` appends an ALIVE line to
`research/orchard-15/HEARTBEAT-14-27.txt` every 10 minutes and commits and pushes it, together
with the partial labelled census and the log while they stay under 5 MB, so a reclaimed VM
loses at most ten minutes. The census does NOT resume: a restart begins from the first model.

## Stage-3 toolchain validated early (while the census runs)

The realizer and blind checker are the step-5 tools; validating them at hour 0 rather than
hour 10 costs seconds and removes the risk of discovering a broken realizer after the census.

`python3 selfcheck.py` — **PASS** (0.5 s). Green: `no-realization` recomputed from the PTS
gives saturated ideal {1}; `real` verifies all 84 determinants and all point pairs. Red (both
correctly REJECTED): a mutated coordinate ("determinant classification is wrong at triple
(2, 4, 8)") and a dropped ideal block ("stated ideal omits, adds, or reorders a PTS block").
The checker is discriminating, not merely permissive.

`python3 run_controls.py --timeout 600 --out control-verdicts-14-27worker.jsonl` — **6/6, all
checker-accepted**, in under 25 s:

| control | verdict | checker |
|---|---|---|
| Fano (7,7) | no-realization | accept |
| Pappus 9_3 | real | accept |
| Desargues 10_3 | real | accept |
| Kantor 10_3 | no-realization | accept |
| Pegg (15,31) | real | accept |
| BGS (14,27) SAT model | no-realization | accept |

Every verdict matches TASK-REALIZE.md step 2, and the table agrees **exactly** with the
coordinator's `control-verdicts.jsonl` (compared verdict by verdict, `AGREE: True`) — an
independent reproduction on a different machine with separately installed sympy 1.14.0 and
pynauty 2.8.8.1.

### Provenance of the BGS control input

`run_controls.py` reads `chiro/scratch/exist-14-27.pts`, and `chiro/.gitignore` excludes
`scratch/`, so that file is NOT in the clone. It was recovered exactly, not improvised: the
PTS line is quoted verbatim in `chiro/REPORT-EXIST.md` line 285 and was extracted from there.
The recovered line is

    14 27 : 0 1 2 , 0 3 4 , 0 5 6 , 0 7 8 , 0 9 10 , 0 11 12 , 1 4 13 , 1 5 12 , 1 6 10 ,
    1 7 11 , 1 8 9 , 2 3 6 , 2 4 9 , 2 5 7 , 2 8 13 , 2 10 12 , 3 5 9 , 3 7 10 , 3 8 12 ,
    3 11 13 , 4 6 12 , 4 8 10 , 5 8 11 , 5 10 13 , 6 7 13 , 6 9 11 , 7 9 12 ;

That it reproduces the coordinator's `no-realization` verdict is evidence the recovery is the
intended input. Written to a separate output file (`control-verdicts-14-27worker.jsonl`) so
the coordinator's `control-verdicts.jsonl` is left untouched.

Timing consequence for step 5: the realizer decided six configurations up to (15,31) in about
20 s total, so realizing the (14,27) classes should be minutes, not hours. The census is the
only long pole.

## Fix during the run: the 5 MB cap would have stopped the checkpoint (00:59Z)

Measured at 2337 models: the labelled census file grows **246 bytes per model**. That crosses
the 5 MB commit cap at about **20,250 models** (~03:45Z at the observed ~106 models/min), and a
full 10 h run would reach roughly 15.5 MB. The first version of `heartbeat-14-27.sh` simply
skipped any file over 5 MB, so from ~03:45Z it would have gone on writing ALIVE lines while
silently no longer checkpointing the census — the failure mode is invisible in the heartbeat,
which is what makes it worth recording.

Fixed: past the cap the daemon commits a `zstd -19` copy and untracks the raw file. Measured
ratio on this data is **19.1x** (576,852 -> 30,275 bytes), so a full 10 h census lands near
0.8 MB, comfortably inside the cap. `zstd` was not installed in this image either and was
installed (1.5.5).

Note for whoever reads the heartbeat file: there are two ALIVE lines about a minute apart at
00:58-00:59Z. Restarting the daemon onto the patched script, I killed the wrapper shell rather
than the loop, so two daemons briefly overlapped; the extra one was killed at 00:59Z and one
daemon (and only one) has run since. The census process was never touched — verified by pid
before and after.

## Enumeration rate is falling (observed 01:17Z) — bears on whether the census can finish

At the coordinator check-in the model count had been flat at 3125 for ~15 minutes. Checked
rather than assumed: pid 5394 sits at 99.9% CPU in state R with CPU-time advancing 1:1 with
wall clock, so it is computing, not hung. The output is not buffered either — `exist.py`
calls `handle.flush()` after every model (line ~1030) — so 3125 is the true count and the
solver really did spend ~15 minutes searching for model 3126, against ~100 models/min over
the first half hour.

This is the expected shape of a blocking-clause enumeration: every model adds a blocking
clause, so successive models get harder, and the final UNSAT (proving no further model exists)
is the hardest solve of all. It is NOT evidence of a fault.

It is, however, the first evidence about the budget, and it points the wrong way. Rough scale:
the first 3125 models took 40 minutes; if the tail continues to lengthen, the 36000 s cap at
~10:37:30Z is likelier to be hit than not, in which case the labelled file is PARTIAL and
proves nothing about t3(14) = 26 — a partial census cannot rule out the arrangement it never
reached. One long gap is not yet a trend and this is deliberately not a projection; the next
few check-ins will show whether the rate keeps decaying. Recorded now so the coordinator can
plan (more time, cube-and-conquer sharding across workers, or accepting a partial result)
rather than learning it at hour ten.

### Sharpened at 01:28Z: the tail has already outlasted the head

Model 3126 has now been running **25.5 minutes** at 99.9% CPU — longer than the entire run up
to that point (models 1..3125 took 25 minutes, 00:37:30Z to 01:02:32Z). One model has cost
more than the first three thousand together. That settles the earlier "one gap is not a trend"
caveat: the rate is decaying steeply, not fluctuating.

Consequence, stated plainly: on this trajectory the census will hit the 36000 s cap at
~10:37:30Z with the enumeration unfinished, and the deliverable will be a PARTIAL census. A
partial census does not certify t3(14) = 26 and must not be presented as doing so — it cannot
rule out an arrangement it never enumerated. The brief anticipates exactly this ("ship the
partial file with the count and say so plainly"), so this is a sanctioned outcome, not a
failure; but it is the likely one, and it is worth the coordinator knowing at hour one rather
than hour ten.

For the coordinator, the decision is its own, not this worker's (nothing in this brief
authorises resharding, so the census continues as specified): the programme already has the
tool for this shape of problem — cube-and-conquer, as used for (15,32), where `exist.py
--cubes --cube-index k` splits the search across workers. If (14,27) is to be certified rather
than sampled, that is the likelier route than a longer single-worker timeout. Escalation
threshold set for the next check-in: if the census is still on model 3126 then, this is
reported as "will not terminate in budget" rather than "may not".

## Step-5 pipeline dry-run on the PARTIAL census (01:45Z) — a preview, NOT a result

Run on a **copy** of the partial census in scratch, writing only to scratch, so no deliverable
file was created or overwritten. Everything below describes an incomplete enumeration.

    canonicalize.py <copy of 3125-model partial> ...   ->  8 classes, 0.40 s
    realize.py <those 8 classes> --timeout 600         ->  8 no-realization, 19.3 s
    check_batch.py <classes> <verdicts> --out ...      ->  8/8 accepted, 18.1 s

Three things this establishes, none of which is a claim about t3(14):

1. **The whole stage-3 chain works at v = 14**, not just on the controls. Before this, only
   the (13,23)-shaped controls had been exercised here.
2. **The labelled-to-class collapse is about 390:1** (3125 -> 8; every class has leave type
   1,1,1,1,1,1,1,1,1,1,1,3,3,3). So even a census with tens of thousands of labelled models
   yields few classes, and step 5 costs ~2.4 s per class to decide and ~2.3 s to blind-check:
   **minutes, not hours**, however the census ends. The census is the only real cost.
3. `canonicalize.py` reports `generator_sha256` **297a1938708332b7df30a61330cfd4f9daedbe5b4
   ebe7e756480136ebbeb0946**, byte-identical to the value in the coordinator's
   `pts-13-23-pseudoline.manifest.json`. This clone's `exist.py` is the same generator that
   produced the (13,23) census.

What it does NOT establish: **nothing about t3(14) = 26.** These 8 classes are whatever the
enumeration happened to reach in its first 25 minutes; the census is unfinished and the
remaining models are exactly the ones the solver is finding hard. All 8 coming out
no-realization is consistent with t3(14) = 26 and is mildly reassuring — in particular no
class came out `real`, which would have contradicted Du and been the headline — but a
consistent partial sample is not evidence of the general claim. The verdicts that matter are
the ones on the final class list.

Operational note for step 5: "run the checker on every certificate" is done with
`check_batch.py <pts> <verdicts> --out checks-14-27.jsonl`, which wraps `check_record` from
`check_realization.py` and requires the PTS and verdict files to be in the same order and of
equal length.

## ESCALATION 01:54Z: the census will not terminate in this budget

The threshold set at 01:28Z is met and then some. Measured at 01:54:06Z:

- pid 5394: 01:16:34 elapsed, 01:16:34 CPU, 99.9%, state R — computing, never idle.
- models: still **3125**. Model 3126 has now run **52 minutes**, **2.1x** the 25 minutes that
  models 1..3125 took in total.
- budget: 1.28 h elapsed of 10 h; **8.72 h remain**, cap at ~10:37:30Z.

Stated as a judgement, with its basis and its caveat. Basis: each model adds a blocking
clause, so difficulty grows monotonically in expectation, and the closing UNSAT — the proof
that no further model exists, which is what makes a census a census — is the hardest solve of
all. At better than an hour per model, 8.72 h buys a handful more models and does not
plausibly reach that closing UNSAT. Caveat: individual SAT solve times are genuinely
unpredictable and model 3126 could land at any moment; "will not terminate" is a strong
expectation, not a proof. Either way the conclusion for the deliverable is the same.

**Consequence: this run will not certify t3(14) = 26.** The output will be a PARTIAL census.
A partial census cannot rule out an arrangement it never enumerated, and no file, report or
reply from this worker will suggest otherwise. This is the outcome the brief anticipated
("ship the partial file with the count and say so plainly"), so it is sanctioned, not a
failure — but it is not the result the job was hoping for, and saying so at hour 1.3 rather
than hour 10 is the whole point of flagging it.

Not acting on it beyond reporting: nothing in this brief authorises resharding, so the census
continues exactly as specified until the cap. The coordinator's options, for its own decision:
cube-and-conquer sharding (`exist.py --cubes --cube-index k`, the approach that settled
(15,32) across four workers) — the natural fit, since the difficulty is concentrated in a
search the cubes would split; a substantially larger budget; or accepting the partial result.
Started now, sharding would recover most of tonight.

The human owner was notified at 01:54Z, because this changes what the run can deliver.

## Correctness fix to the heartbeat's liveness field (04:00Z)

The daemon reported `proc=running` / `proc=DEAD` from `pgrep -f "exist.py 14 27"`. That
pattern also matches this session's own shell wrappers, whose command lines quote the census
command — so after a real death the heartbeat could have gone on recording `proc=running`.
Since HEARTBEAT-14-27.txt is the durable record the coordinator reads when this VM is gone,
a false "running" is the one thing it must never say. Changed to
`ps -eo args | grep -q "[e]xist\.py 14 27"`, which matches only the process itself.

The same flaw, in the more dangerous direction, was fixed in the Monitor's liveness test at
the same time: `pgrep -f` there would have kept reporting the census alive after it died,
suppressing the very alert the Monitor exists to raise.

Restarted the daemon onto the corrected script (killing the loop pid this time, not the
wrapper): exactly one daemon runs, pid 11790, ppid 1. The census (5393 parent, 5394 worker at
99.9% CPU) was not touched — verified by pid and CPU before and after.
