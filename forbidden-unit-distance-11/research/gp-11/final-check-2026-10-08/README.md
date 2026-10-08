# GP-11: the B11 final check, 2026-10-06 to 2026-10-08

One serial run of the frozen checker (`research/gp-11/check/gp11check.py`, B11 profile) over the sealed complete
assembly, on the u24 VM. It was prepared and launched by `research/gp-11/tools/b11_final.py`: seal sha256
f1e1e4a2d6d42b05f51ac8c24005d7437d987f913bb16fe9d42e87d0dcf44261, launched 2026-10-06T22:06:01Z.

- **Outcome: VERIFIED_B11, exit 0** (`outcome.json`). 105,409 s wall and 104,912 s user CPU; peak RSS 509 MB; the
  memory floor was never approached (`cost.json`).
- **Report** (`checked/report.json`, sha256 7fa5b9e3...): ACCEPT verified, profile B11. 448,708 inputs: 443,444
  embedded, 5,264 refuted, 0 unknown. Not conditional; no direct rejections.
- **L11**: 2,833 minimal forbidden graphs (`checked/L11.g6`, sha256
  498ac6bf3fd6e8dc5e4a14ceb0790e8bb1431778526f2b39fa31dff78bbde035). **Byte-identical to the list derived independently
  from the records alone** (`../independent-checks-2026-10-07/audit/L11.g6`).
  - Every other refuted graph is non-minimal: 2,431 of them (`checked/minimality.jsonl.gz`).
  - The pre-registered forecast (`../PREDICTIONS.md`) was about 3,000, with a 95% range of 1,500 to 6,000.
- **Publication gates G0 to G5**: `gates.json`, the coordinator's attestations, each with its evidence inside the run
  directory (34 files, under `gate-evidence/` and the run's own files).
  - `gate_paths.out`: PASS. Every evidence path resolves inside RUN; the guard ran immediately before the writer.
  - The frozen writer (`tools/write_result.py`) accepted every gate and wrote `../RESULT.md`: "WROTE ...: 2833 members".
- Also kept: the check log (`check.log.gz`), the checked records (`checked/records.jsonl.gz`), the seal and the launch
  record.

- **Gate evidence** (added 2026-10-08, before the run machine was deleted): `gate-evidence/` holds the 27 evidence files
  under G0, G1, G2, G4 and G5 that `gates.json` names, copied from the run directory, with
  `control51-final-status.json`, `prediction-chronology.json` and `make_gates.py` (the script that wrote `gates.json`).
  `python3 verify_gate_evidence.py --self-test` checks all 34 evidence files `gates.json` names against the copies
  here, by sha256 on the uncompressed bytes. Three of them are kept under a different name: `PREDICTIONS.md` one
  level up, `outcome.json` for `execution/outcome.json`, and `checked/minimality.jsonl.gz` for
  `checked/minimality.jsonl`. It prints `34 evidence files match gates.json, 0 do not`, and the self-test shows that
  one flipped bit in a copy is caught.
