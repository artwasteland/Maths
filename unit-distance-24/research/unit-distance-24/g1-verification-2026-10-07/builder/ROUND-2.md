# Round 2 (2026-10-07): bind every retained manifest's content claims, and enumerate them

Your round-1 patch is landed in the repository (commit 2aba1ff128f): `repo/.../receipt_audit.py` here equals the
repository's. The G1 verifier's second round (`<repo>/REPORT.md`, section "Round 2", and
`<repo>/round2/probe_full_producer.py`) found one more gap.

**The gap.** A retained enumeration stage manifest (`n-m.manifest.json`, for example `23-64.manifest.json`) records
`children_written` and `children_file_sha256` for the level file `n-m.g6`. In legacy-format whole receipts, where that
manifest is not in the validated `manifests`, the audit accepts a manifest that claims 777 children for an empty
`.g6`, or a false child-file hash. Removing the exported aggregate manifest from an expanded receipt also permits
acceptance. A direct measurement of the real fleet (`research/unit-distance-24/tools/retained_scan.py` rule 5, in the
repository) found all 3,872 retained level files equal to their stage manifests, so honest copies satisfy the binding.

Same constraints as BRIEF.md. Please:
1. Fix it on the same principle: every retained stage manifest's `children_written` and `children_file_sha256` must
   equal the measured retained `n-m.g6`, whether or not any aggregate export or `manifests` entry is present. A stage
   manifest describing a level file that is not retained, or a retained level file with no stage manifest, fails.
2. **Enumerate, don't search.** List every field, in every file the retained copy policy keeps, that makes a claim
   about the content of a retained or deleted output. The files are the stage, prune and aggregate manifests, the
   structure, the inventory, `hashes.json`, `counts.json`, `reach.json` and the receipt. Examples of such fields:
   counts, hashes, byte sizes, records, children, inputs and outputs. For each field, give the audit line that binds
   it to a measurement or to another bound value. Or mark it unbound and say what an alteration of it could hide.
   Put this table in REPORT.md. Bind any unbound field that describes retained content. For a field that can only
   describe deleted content, say what binds it, for example the checker's own check before deletion, or say that
   nothing does.
3. **Controls in `g1_controls.py`:**
   - the verifier's round-2 probes (both fields), and the export-removed variant;
   - one control for every newly bound field;
   - exact messages;
   - honest receipts accepted after every red;
   - each control accepted by the round-1 code. Your round-1 patched file is the "unpatched" baseline now; keep it
     as `pristine-r1/`.
4. **Rerun every suite you ran in round 1.** Also run `retained_scan.py --self-test` against a copy of one fixture.
   Write `PATCH-2.diff` relative to the round-1 file.

Final message under about 600 words: the fix, the enumeration table's summary (how many fields, how many bound,
any left unbound and why), test results.
