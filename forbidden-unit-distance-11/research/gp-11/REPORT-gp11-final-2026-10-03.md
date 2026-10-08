# GP-11 final tooling — 2026-10-03

Built the B11 analyst campaign first, then the residue assembler wrapper and final launcher. All repository changes are new files. No frozen checker, checker input, F9/F10 list, pipeline stage, or existing tool was changed; no additive options to existing tools were needed. No commit, push, reset, checkout, analyst search, population assembly, or population proof replay was performed.

**Added files** (paths below are relative to `research/gp-11/tools/`, except this report):

| File | Purpose |
|---|---|
| `b11_campaign.py` | Prepare, scan, run, recover leases, independently admit, report status, export admissions. Reuses unchanged control campaign filesystem isolation, credential handling, durable writes and hash-chain ledger. |
| `b11_check.py` | Pinned, fresh `fixture11`/F10 single-record replay, strict record boundary, acceptance checks, external deadlines and resource receipts. |
| `b11_heavy.py` | Shared arithmetic/check lock within a campaign; invokes the existing guard. |
| `b11_selfcheck.py` | Fresh analyst self-check directories; these receipts never substitute for coordinator admission. |
| `B11-ANALYST-BRIEF.md` | Canonical labels, A34 intermediate evidence, self-contained proof formats, resource/return contract. |
| `b11_residue.py` | Audit recorded f1-first selection, displaced conflicts, f2/p2 overlays and all 80 f3 returns; invoke lean assembly and compare exact UNKNOWN sets. |
| `b11_final.py` | Verify payload/optional transport receipts, copy and seal inputs/controls/source, and enforce final acceptance. |
| `test_b11_endgame.py`, `test_b11_workflow.py` | Hand-written synthetic expectations, guard-disable tests, tiny real admission and launcher rehearsal. |
| `endgame-evidence/b11-final-{unit,workflow,control,packet}-tests.txt` | Four retained test logs. |
| `endgame-evidence/b11-final-validation.json` | Exact test commands, source/log hashes, real admission/rejection receipts and rehearsal resource/output hashes. |
| `REPORT-gp11-final-2026-10-03.md` (worktree root) | This report and runbook. |

**Campaign behavior.** Packets must be produced with `make_packets.py --select ASSEMBLY/UNKNOWN.g6`. Preparation checks exact selection, packet identities, complete file hashes and the B11 packet/profile contract. Saved proposals and histories survive. Each attempt has a fresh context and bounded workspace; seed files are mounted read-only. Bubblewrap hides the repository, other workspaces, ledger and source bundles. There is no unisolated fallback. The installed Codex controller gets a fresh home, no inherited instructions/plugins/history, and only temporary authentication. Tool network/web/subagents remain disabled. Credentials are removed on completion or recovery.

`--jobs` defaults to 4 and accepts any positive number (including 8 and larger machines). Arithmetic and self-check commands must use the shared `b11_heavy.py` lock; independent checks are also serialized. Analyst compliance with that command contract is required; it is not a syscall-level prohibition on arbitrary arithmetic. The guard and coordinator enforce memory stops. Search defaults to 5,400 seconds; independent proof checking defaults to 540 seconds. Budgets/model are pinned at preparation. Retries use new attempts; changing pinned preparation settings requires a new campaign. `run` attempts every pending obligation once and returns 3 if any remain unresolved.

Queue states are queued, leased, proposed, checking, accepted, retryable and unresolved. Canonical graph plus packet hash identify an obligation. Torn ledger tails are quarantined; durable events recover a crash before append; returned proofs are checked before another search. Opposite/differing accepted records are quarantined. No analyst prose, self-check receipt or arithmetic-only timing admits a record. Accepted records must be self-contained: exact embeddings or direct/indexed F10 refutations; external graph pointers are rejected. The frozen checker judges rational spelling, maps, equations and injectivity. Failed/censored checks retain hash-bound proposals, logs, reports and costs too. Optional construction evidence is limited to 128 regular files / 64 MiB.

The control's **withheld B10 answer**, F9-only rule, ban on F10/ten-vertex evidence, fixed 32 obligations and two-analyst ceiling do not apply to B11. Control 5.1 tested fresh B10 production; B11 explicitly assumes its completed F10 premise. This does not authorize hidden dependencies or unreviewed coordinate ancestry. Workspace isolation, attribution, frozen pins, resource bounds and independent admission still apply. This desktop blocks private network-namespace setup (`NETLINK_ROUTE`). The B11 controller and trusted frozen checker use a shared network namespace with filesystem/PID isolation; the checker receives no credentials or returned executable code. The analyst tool sandbox still disables network access.

**Assembly and launch.** Assembly uses the 200 predecessor entries actually recorded in f3 `round.json`: 75 f1, 117 f1b, four f2, four p2; the five displaced f1b copies are checked for conflicts but are not seeds. The completed cheap state supplies the remainder of B11. Seed order is cheap state, recorded predecessors, f3, admitted analyst streams. Rewriting is mandatory (`--rewrite-outside-ends --forbidden-limit 10`); propagation is explicitly off so the independent residue comparison has no unrecorded reductions. All bundle artifact/compressed/uncompressed hashes and actual record coverage are checked. Final UNKNOWN must equal the recorded 525 minus f3 decisions minus admitted analyst targets. Mismatches fail with extra/missing graph diagnostics. `records.jsonl`, `unknown-records.jsonl`, `hosts.jsonl`, `UNKNOWN.g6` and the assembly/audit receipts are preserved. Packet generation uses only the disjoint f3 returns, whose UNKNOWN histories include prior budgets; overlapping rounds are never passed together to `make_packets.py`.

The final launcher requires an independently retained assembly digest, copies the completed fresh-producer B10 tree and named11 evidence, preserves prerequisite reports, and seals all consumed files plus a frozen source snapshot. B10 is additionally tied to the published control-5.1 final-status and MERGE hashes. It checks recursive same-tree manifest paths and rejects links. Input files/directories are read-only; checker outputs and execution receipts are writable. Hashes are checked again at launch and after replay. The owner can change permissions, so the external seal digest remains authoritative. A host-wide final-check lock and exclusive start receipt prohibit concurrent/repeated launches; there is no cached-success or checker-resume path.

B11 has exactly the nine specified controls, with `named` nested under B10. Its manifest has no fixture-only overrides. The guard receives the independently hardcoded B11 digest `ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f`. Success requires exit 0, literal `ACCEPT run verified`, profile B11, 448,708 inputs and the pinned hash, zero UNKNOWN/direct rejections, unconditional status, empty conditional-minimal list, consumed-stream hashes, L11/minimality evidence, complete F10 provenance and all control receipts. UNKNOWN blocks preparation and launch. Only explicit `--dry-rehearsal` permits a partial run; that builds `fixture11`, allows at most 100 inputs, and reports `VERIFIED_REHEARSAL`.

Launcher exits: 0 verified, 2 integrity/configuration failure, 3 incomplete, 4 checker rejection, 74 transport failure, 75 resource stop, 76 censored timeout. A stopped/rejected run needs a new directory. Publication still requires the separate G0–G5/G6 evidence and writer gates.

`coordination/cloud-workers/gp11-check-run.sh` is insufficient: it runs fixture11 without final controls/predictions/external B11 digest, permits stale preparation, and can return zero after delivering a rejected report.

**Validation.** 176 normal tests passed: 38 new record/campaign tests, 104 workflow tests, 22 unchanged control-campaign regressions and 12 unchanged packet regressions. All **129 guard-disable runs went red as intended** (32 record tests, 97 workflow tests). The workflow suite inventories every new campaign/admission `require` guard and requires a manually specified negative test; it does not generate expected verdicts from the implementation. Coverage includes framing, graph identity, pointers/F10 bounds, source/profile/consumed hashes, packets, workspace isolation, ledger binding/recovery/conflicts, round selection/coverage and final acceptance fields. Existing frozen rules were not modified for mutation testing.

The real fixture is eleven isolated vertices at distinct rational points `(i,0)`. A fresh isolated F10 admission accepted it with counts `{embedded:1, refuted:0, unknown:0}`. Coinciding two points produced frozen `exact_collision` and UNRESOLVED admission; a fresh positive passed afterward. Ledger reload/export, outside-end-enabled reassembly, a sealed one-graph launcher rehearsal and refusal to relaunch that directory also passed. These are real fixture11 replays, not arithmetic microbenchmarks or B11 classification evidence. Raw artifacts are under `/tmp/gp11-b11-final-validation-v5`; retained receipts/logs are in the files listed above. All tests/fixtures used nice 15, at most two active test lanes and no fixture near ten minutes; the final real fixture sequence used one lane.

Repeat the bounded validation from this worktree with a fresh fixture output:

```bash
PY=<repo>/pyenv-gp10/bin/python
T=research/gp-11/tools
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_b11_endgame.py" --mutations --real-out /tmp/gp11-b11-review-fixture
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_b11_workflow.py" --mutations
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_control51_campaign.py"
nice -n 15 timeout --kill-after=15s 540 "$PY" -B "$T/test_make_packets.py"
```

**Coordinator runbook — future production commands, not executed here.** Obtain the complete checked f3 returns first. Keep source bundles/read-only cheap state unchanged. Choose fresh output directories with sufficient disk; the campaign must be outside the repository. The commands below run sequentially except the requested analysts.

```bash
cd <repo>
PY=<repo>/pyenv-gp10/bin/python
T="$PWD/research/gp-11/tools"
WORK=<repo>/b11-endgame
F3=<repo>/research/gp-11/pipeline/cloud
CHEAP=<repo>/population-cheap-state
mkdir -p "$WORK"
f3=("$F3"/f3-[0-9][0-9][0-9])

# 1. All rounds -> audited assembly. Refuses missing f3 shards before reading predecessors.
nice -n 15 "$PY" -B "$T/b11_residue.py" --f3 "$F3" --cheap "$CHEAP" --out "$WORK/assembly-0"

# 2. The assembled UNKNOWN set -> packets from disjoint f3 returns.
nice -n 15 "$PY" -B "$T/make_packets.py" "${f3[@]}" --select "$WORK/assembly-0/UNKNOWN.g6" --python "$PY" --out "$WORK/packets-0"

# 3. Prepare/scan without starting Codex; run includes independent admission of every return.
nice -n 15 "$PY" -B "$T/b11_campaign.py" prepare --assembly "$WORK/assembly-0" --packets "$WORK/packets-0" --out "$WORK/campaign-0" --python "$PY" --seconds 5400 --check-seconds 540
nice -n 15 "$PY" -B "$T/b11_campaign.py" scan --out "$WORK/campaign-0"
nice -n 15 "$PY" -B "$T/b11_campaign.py" run --out "$WORK/campaign-0" --jobs 4
nice -n 15 "$PY" -B "$T/b11_campaign.py" status --out "$WORK/campaign-0"

# 4. Hash-bound admissions -> export -> complete reassembly.
nice -n 15 "$PY" -B "$T/b11_campaign.py" export --out "$WORK/campaign-0" --destination "$WORK/admitted-1"
nice -n 15 "$PY" -B "$T/b11_residue.py" --f3 "$F3" --cheap "$CHEAP" --analyst-export "$WORK/admitted-1" --out "$WORK/assembly-1"
```

`run` exit 3 is an incomplete batch, not an accepted result. Repeat `run` to retry remaining cases with fresh contexts. Export the cumulative ledger to a **new** `admitted-2`, then reassemble to **new** `assembly-2`, replacing the export argument with the newest cumulative export. For different campaigns with disjoint targets, repeat `--analyst-export`. Do not combine overlapping cumulative exports. For a separately returned record/provenance/cost directory, independent admission is:

```bash
nice -n 15 "$PY" -B "$T/b11_campaign.py" admit --out "$WORK/campaign-0" --case "$PACKET_ID" --return-dir "$RETURN_DIRECTORY"
```

Before the final commands: inspect all new proof cost receipts and use the existing `endgame_inventory.py` / `measure_check_cost.py --seconds 540` on explicitly selected, hash-verified hard-tail records (including dependency closure for pointers). Timeouts are censored, never accepted timings. Use a larger reviewed observation budget later if needed; do not alter parser/format limits. This builder did not run a hard-tail or full-controls pilot.

```bash
# 5. Preserve/replay the small general-search named control in a new tree.
cp -R research/gp-11/check/fixtures/named11 "$WORK/named11"
nice -n 15 "$PY" -B "$T/guard.py" -- "$PY" -B research/gp-11/check/gp11check.py "$WORK/named11" > "$WORK/named11.log" 2>&1

# 6. Only after UNKNOWN is empty, seal the final tree.
ASSEMBLY="$WORK/assembly-1"  # Set to the latest successful reassembly.
ASSEMBLY_SHA=$(sha256sum "$ASSEMBLY/assembly.json" | cut -d ' ' -f 1)
nice -n 15 "$PY" -B "$T/b11_final.py" prepare --assembly "$ASSEMBLY" --assembly-sha256 "$ASSEMBLY_SHA" \
  --b10 <repo>/control51-campaign/B10-final --named11 "$WORK/named11" \
  --chronology "$WORK/prediction-chronology.json" --run "$WORK/B11-final-1" --python "$PY"

# 7. Retain the printed seal digest independently, then launch once in a durable session.
SEAL_SHA=$(cut -d ' ' -f 1 "$WORK/B11-final-1/seal.json.sha256")
nice -n 15 "$PY" -B "$T/b11_final.py" launch --run "$WORK/B11-final-1" --seal-sha256 "$SEAL_SHA"
```

`prediction-chronology.json` is a **required reviewed attestation**, not a timestamp inference generated by the launcher: fields `predictions_sha256`, `commit` (40 hex), `predates_B11_run: true`, `attested_by`, and `evidence`. The original file hash is `12a37f573d087c304dc6ab629d2abf49ec555f038174ca63605aa53fd750b906`; read-only history identifies its introduction at `601258c057e6f22142cca92e4c5ee031a8e2e27b` (2026-10-01 04:57 +10). `git show` of that file reproduced the hash. The first frontier-input commit is `2dcaf813459fe86e51482986beb355bea87f5f6a` (10:58 +10). These observations support review but do not prove actual execution chronology; this builder did not fabricate the attestation. For transported payloads, also supply `--transport-root`, `--transport-receipt` (JSON path/hash map) and its independently retained `--transport-sha256` to preparation. Locally assembled payloads need no transport-part receipt.

**Measurements, disagreements and remaining limits.**

- The Oct-1 report describes control 5.1 as open and missing frozen dependencies. The current checkout has the frozen pieces and COMPLETE control receipts. Its `research/gp-11/control51/` is an evidence archive, not a replayable B10 tree; the full tree is `<repo>/control51-campaign/B10-final`. The launcher requires that tree, tied to the published completion/merge hashes.
- The report's two-to-four analyst guidance is superseded by this brief's configurable four-to-eight. Heavy work remains one lane per campaign. The old campaign's fixed 32/F9/withheld-answer restrictions are not silently carried into B11.
- `make_packets.py` already emits fixture11 for B11, but its standalone checksum list omits F10 and some files read by `gp11check.source_hashes()`. The new campaign copies and pins the complete required source/data set and replaces the packet self-check wrapper. Existing packet code is unchanged.
- The lean assembler does not validate bundle summaries or provide final controls; the new wrapper validates receipts first. Legacy sample cannot check F10 rewrites; fixture11 is used explicitly. This brief's ten-minute fixture limit led to 540-second test/admission defaults instead of the report's 900-second measurement window.
- No checked f3 directories were visible at inspection. The actual post-f3 UNKNOWN equality and full-population path therefore remain unexecuted; synthetic round fixtures exercise f1 priority, overlays, displaced conflicts and missing/extra f3 coverage. The tool refuses to guess a residue or treat missing returns as UNKNOWN.
- Root free space measured 14,725,447,680 bytes (about 13.7 GiB), versus the older report's 44 GB. Final preparation requires actual payload/control bytes plus 12.5 GiB for scratch/output/headroom; a projected 2–4 GiB payload exceeds current headroom. No unrelated data was removed.
- Report measurements: favorable serial baseline 13–15 hours; reserve **24–72 serial hours** for final verification after preflight. The completed B10 control took 3,665 seconds and lower controls replay more than once. Expensive measured exact cases ranged about 39–241 seconds; A34 examples were about 45/89 arithmetic seconds and selected analyst cases about 10/12 minutes. Degree alone predicts cost poorly. These are planning measurements, not bounds or throughput guarantees. At 300–350 cases, the 90-minute search cap alone permits roughly 56–132 analyst wall hours at 8–4 concurrency, with the serialized heavy lane and checking adding constraints; unresolved cases may remain.
- New tiny fixture costs and peak RSS are in the validation receipt; they are not population estimates. CPU and peak-process RSS use GNU time; tree RSS/CPU and scratch are sampled lower bounds. Final scratch sampling includes the existing shared `/tmp/gp10-check` directory. No relocation of frozen scratch, parser-limit relaxation, final B11 claim, or publication was attempted.
