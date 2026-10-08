# u(23) fleet aggregate, 23-65-L12-tri-pf74
`<scratch>/scratchpad/fleet/results`: 1,955 slice copies read in 101 worker directories, 0 skipped as incomplete, 0 misfiled, 0 unfinished; 41.3 s

## 1. Coverage (1,920 slices at level 12, target (23,65))
- complete: **1,920**; missing: **0**
- every copy has resumed cells (fresh rerun needed): 0
- several copies: 35: 24, 120, 216, 312, 408, 504, 600, 696, 792, 888, 984, 1080, 1176, 1272, 1368, 1464, 1560, 1656, 1752, 1848 in f25-s2mr9v + f25-svchkh; 94 in f100-b704du + f95-ly5jl3; 253 in f62-yc40t5 + f97-t4t9v7; 263 in f72-c25ju0 + f97-t4t9v7; 282 in f100-b704du + f91-tn2qku; 453 in f70-bf3dnc + f97-t4t9v7; 472 in f100-b704du + f89-hg51z1; 534 in f55-drjag9 + f97-t4t9v7; 579 in f04-dam5h4 + f98-lqpsag; 606 in f31-mtewf0 + f98-lqpsag; 835 in f68-x88y9f + f98-lqpsag; 1227 in f100-b704du + f76-03g6uj; 1354 in f11-bqjl8k + f98-lqpsag; 1405 in f62-yc40t5 + f99-wsyxyj; 1735 in f08-qn74wg + f99-wsyxyj; 1773 in f46-s4mdou + f99-wsyxyj; counts, shipped files and kept graphs agree: yes

## 2. Tree above level 12 (1,920 slices, one copy each)
| n | cells | children | kept | pruned | tu | tri_tu | tri_refuted | refuted | % pruned |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 13 | 8 | 17,770,330 | 14,227,296 | 3,543,034 | 2,649,736 | 877,724 | 15,574 | 0 | 19.9 |
| 14 | 8 | 149,368,305 | 111,094,819 | 38,273,486 | 26,673,717 | 11,240,806 | 358,963 | 0 | 25.6 |
| 15 | 9 | 842,594,946 | 492,690,622 | 349,904,324 | 214,552,374 | 127,976,366 | 7,375,584 | 0 | 41.5 |
| 16 | 9 | 1,058,712,809 | 580,930,642 | 477,782,167 | 251,563,636 | 211,707,116 | 14,511,415 | 0 | 45.1 |
| 17 | 7 | 430,213,696 | 213,648,700 | 216,564,996 | 106,789,432 | 101,641,378 | 8,134,186 | 0 | 50.3 |
| 18 | 6 | 148,671,082 | 69,977,653 | 78,693,429 | 40,355,890 | 35,233,396 | 3,104,143 | 0 | 52.9 |
| 19 | 6 | 11,975,593 | 4,368,436 | 7,607,157 | 3,456,001 | 3,738,733 | 412,423 | 0 | 63.5 |
| 20 | 4 | 154,347 | 75,745 | 78,602 | 38,816 | 35,515 | 4,271 | 0 | 50.9 |
| 21 | 2 | 2,026 | 1,320 | 706 | 360 | 308 | 38 | 0 | 34.8 |
| 22 | 1 | 30 | 29 | 1 | 0 | 0 | 1 | 0 | 3.3 |
| 23 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0 |
| (23,65) | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0 |
Other count keys summed over these cells: input 2,659,463,165, survivors 2,013,383,203, tri_silent_passes 0, tri_survivors 1,487,015,263, embedded 0, unknown 1,487,015,263. Children minus prune input (the reach filter's drops): 0.

## 3. Top level (23,65)
- children **1**, kept **1**; slices with children: 50; slices that kept anything: 50 (1: `V?_QPIGD@AGOoHKE_o?Q??HK?WqH@PO_m@CWCaHN_?F_`)
- records under research/unit-distance-23/results/u23/top-level: 50
- top_level_check.py: TOP-LEVEL OK: 1 slice(s) with kept graphs, 1 cop(ies), 0 problem(s) (exit 0)

## 4. G4 replays (fleet_status.py's rule, chosen copies)
- verdicts: PASS 1,920; modes: full 99, slice 1,821; full-mode replays with every red control red: 99
- parents sampled 2,237,909, processed 1,374,989; production children compared 3,576,629; mismatching parents 0; stage files re-derived 131,946
- not PASS/EMPTY: none; other copies: none; runbook verdict differs from the rule: 0

## 5. Cost (fleet_status.py's rule: step timings of the cells above level 12, none resumed)
- 1,920 slices timed, 0 excluded for resumed cells: **1,304,030.4 s** (362.23 h)
- per slice: median 556.8 s, p90 987.4 s, max 13,270.6 s; heaviest: s344 13,270.6 s (f57-w2xriy), s1535 11,289.4 s (f96-fi9jlf), s50 9,734.2 s (f51-2h4ksy), s1082 9,594.1 s (f27-ldx6e0), s1651 8,559.4 s (f20-bvpkkh)
- runbook clocks over 1,920 chosen copies (replay/fingerprint.json): run-dag2.py 1,468,404 s, G4 replay 89,973 s

## 6. Provenance
- prefix (levels <= 12, hashes.json): 70 files, identical sha256 in all 1,955 copies
- software (15 source/tool entries from the aggregate, prune and 162,265 verify manifests and the replay summaries) and data inputs (8): one hash each in every copy; enum2.py d967fc90, exact_verify.py ab55ce77, prune.py b4858cab, python /usr/local/bin/python3 3.11.15, replay-398.py 2c81ae65, run-dag2.py 0c6fb312, udcheck.py 63b7f1b5, udcheck398.py 783d368c, udcheck_rhombus.py 06db27ec, udembed.py 75886c63, udenum 84adaddf, udfilter 6e0771bb, udtriangle 0ca59908
- run options (run-summary header, run-config.json) identical in every copy: yes
- worker directories: 101 of 109 hold slice copies; none in f05-bzu3pr, f10-tpm85f, f16-tmuwg3, f17-wpwwci, f32-5ogu26, f36-u5pa8t, f38-3t9yir, f43-edg6dr; plan tags with several directories: f05 (f05-bzu3pr f05-c14id5), f10 (f10-nqgab1 f10-tpm85f), f16 (f16-tmuwg3 f16-tw83zk), f17 (f17-km962c f17-wpwwci), f25 (f25-s2mr9v f25-svchkh), f32 (f32-5ogu26 f32-xtnvj5), f36 (f36-t46q8t f36-u5pa8t), f38 (f38-3t9yir f38-rdljrj), f43 (f43-8zowl2 f43-edg6dr); copies outside the plan's owner: {'f100-b704du': 4, 'f97-t4t9v7': 4, 'f98-lqpsag': 4, 'f99-wsyxyj': 3}

## Self-check
- PASS coverage: complete 1,920 + missing 0 = 1,920, each of 0..1,919 once
- PASS cell_partition: kept + pruned = children - reach-dropped in all 117,120 cells above level 12 of 1,920 slices (reach dropped 0 there, per run-summary.json)
- PASS pruned_by_kind: pruned = tu + tri_tu + tri_refuted + refuted in every such cell
- PASS counts_vs_summary: counts.json = run-summary.json (children and prune counts, every cell) in 1,920 chosen copies
- PASS counts_vs_files: 36,480 record counts of the shipped level files (hashes.json, the target's keep file, the prune manifests' counts and verified_counts) = counts.json
- PASS totals: every count summed per slice = per cell = per level (13 keys), and the target cell
- PASS copies_agree: the 35 slices with several complete copies: every copy's counts.json rows, shipped level files and kept graphs identical
- PASS fleet_status: fleet_status.py's slice_record and selection over the same 1,955 directories: 1,920 slices done, target cell kept 1; per chosen copy the target cell's kept, timing, resumed cells and replay verdict
SELF-CHECK OK: 8 of 8 identities hold

Problems: none
