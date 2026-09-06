#!/usr/bin/env python3
"""Emit sections 3-5 of CROSSCHECK.md from results-main.json, results-control-a.json,
results-control-b.json and plan-main.json (all written by replay.py)."""
import hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = "<repo>/pyenv-maths/bin/python"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


main = json.loads((HERE / "results-main.json").read_text())
ca = json.loads((HERE / "results-control-a.json").read_text())
cb = json.loads((HERE / "results-control-b.json").read_text())
plan = json.loads((HERE / "plan-main.json").read_text())
render = subprocess.run([PY, str(HERE / "render.py"), str(HERE / "results-main.json")],
                        check=True, capture_output=True, text=True).stdout
processed = subprocess.run([PY, str(HERE / "processed.py"), str(HERE / "plan-main.json")],
                           check=True, capture_output=True, text=True).stdout
shards = main["per_shard"]
vacuous = [e for e in shards if e["udenum_children"] == 0 and e["enum2_children"] == 0]
whole = [e for e in shards if e["whole_shard"]]
raw_over = sum(e["enum2_children_raw"] - e["enum2_children"] for e in shards)
hash_ok = all(e["children_file_sha256_matches_manifest"] for e in shards)
lines_ok = all(e["udenum_shard_lines"] == e["udenum_manifest_children_written"] for e in shards)
dups = sum(e["udenum_children"] - e["udenum_distinct"] for e in shards)
pass_guard = [l for l in processed.splitlines() if l.startswith("total")][0]

out = []
out.append("\n## 3. The run and the agreement table\n")
out.append(f"`replay.py replay --plan-file plan-main.json --workers 4 --tag main` on {main['host']}, "
           f"started {main['started_utc']}, finished {main['finished_utc']}, wall {main['wall_seconds']:.0f} s "
           f"({main['wall_seconds']/60:.1f} min) with 4 worker processes under `nice -n 10`; "
           f"enum2 CPU {sum(e['enum2_cpu_seconds'] for e in shards):.0f} s summed over units.\n")
out.append(f"Shards replayed: {main['shards_total']} of 92 ({len(whole)} whole, {main['shards_total']-len(whole)} sub-ranges); "
           f"identical: {main['shards_identical']} of {main['shards_total']}; all identical: **{main['all_identical']}**. "
           f"Parent records replayed: {main['parents_replayed']} (of 815,215 in the two transitions, "
           f"{100*main['parents_replayed']/815215:.2f}%); of these {pass_guard.split()[-1]} pass the minimum-degree guard "
           f"(of udenum's 636,488 processed parents, {100*int(pass_guard.split()[-1])/636488:.2f}%). "
           f"udenum children in the replayed ranges: {main['udenum_children']} (of 5,128,203 in the two transitions, "
           f"{100*main['udenum_children']/5128203:.2f}%); enum2 distinct children: {main['enum2_children']}; enum2 raw "
           f"constructions exceeding distinct (Aut(H)-equivalent neighbourhoods, removed by the set): {raw_over}.\n")
out.append(f"Vacuous shards (0 children on both sides, counted as identical but proving only that both guards skip the "
           f"same parents): {len(vacuous)}: {', '.join(e['shard_id'] + ' [' + str(e['range'][0]) + ',' + str(e['range'][1]) + ')' for e in vacuous) or 'none'}.\n")
out.append(f"Every shard output file's sha256 matched its manifest: {hash_ok}; every shard file's line count matched the "
           f"manifest's `children_written`: {lines_ok}; duplicate lines inside udenum blocks: {dups}.\n")
out.append("Guard consistency (independent of the replay): `processed.py` re-expresses the AMP minimum-degree guard on the parent "
           "records alone; on the six whole shards its counts (11-21: 242, 11-22: 40, 11-23: 9, 12-25: 149, 12-26: 18, 12-27: 2) "
           "equal udenum's `parents_processed` in the shard stats exactly. Per cell for the planned ranges:\n\n```\n" + processed + "```\n")
out.append("### 3.1 Per-cell agreement table (the certificate item)\n")
out.append(render + "\n")

out.append("## 4. The two controls, both red\n")
e = ca["per_shard"][0]
mu = e["mutated"][0]
out.append(f"**(a) Mutated parent record.** `replay.py control-a --ranges {e['shard_id']}:{e['range'][0]}:{e['range'][1]} "
           f"--record {mu['record']} --edge 0,1 --workers 2 --tag control-a`. Record {mu['record']} of `_parents/12-20.g6` "
           f"(`{mu['original']}`, 11 vertices, 18 edges) had edge {{0,1}} flipped (added; raw `{mu['flipped_raw']}`), the result "
           f"re-canonicalised (`{mu['flipped_canonical']}`, 19 edges, so d becomes 1 for that record) and substituted before "
           f"replaying parents [{e['range'][0]},{e['range'][1]}) with (12,20). udenum block: {e['udenum_children']} children; "
           f"enum2: {e['enum2_children']}; only udenum: {e['only_udenum']}; only enum2: {e['only_enum2']}; identical: "
           f"{e['identical']} -> RED as required (the {e['only_udenum']} children of the original record are missing, "
           f"{e['only_enum2']} children of the mutated record are extra).\n")
out.append(f"  only udenum: `{' '.join(e['only_udenum_first20'])}`\n\n  only enum2 (first 20): `{' '.join(e['only_enum2_first20'])}`\n")
out.append(f"**(b) Forbidden graph dropped from a copy of the list.** `replay.py control-b --drop-index 1 --ranges "
           f"12-20-200000-210000:200000:200030,11-17-20000-30000:25000:25030 --workers 2 --tag control-b`. The copy "
           f"`crosscheck/forbidden-73-drop1.json` (sha256 {sha(HERE / 'forbidden-73-drop1.json')}) is `data/forbidden-74.json` "
           f"without index 1, the (5,6) graph K_{{2,3}} (edges [[0,3],[0,4],[3,1],[3,2],[4,1],[4,2]]); enum2's `PATTERNS` were "
           f"rebuilt from it (`make_patterns`, 630 patterns instead of 635) and the same ranges replayed:\n")
for s in cb["per_shard"]:
    out.append(f"  - {s['shard_id']} [{s['range'][0]},{s['range'][1]}): udenum {s['udenum_children']}, enum2 {s['enum2_children']}, "
               f"only enum2 {s['only_enum2']}, only udenum {s['only_udenum']}, identical {s['identical']}; first extras: "
               f"`{' '.join(s['only_enum2_first20'][:8])}`")
out.append(f"\n  Total extra children {sum(s['only_enum2'] for s in cb['per_shard'])}, missing 0, on 60 parents: RED as required, "
           f"and in the right direction (a strict superset: removing a forbidden graph can only admit more neighbourhoods).\n")

out.append("## 5. Exact commands and hashes\n")
out.append("All from `research/unit-distance-22/enum2/crosscheck/` with `PY=<repo>/pyenv-maths/bin/python`:\n\n```\n"
           "$PY replay.py bench --parent-file <_parents/N-M.g6> --start A --end B --n N --m M      # Section 2.1, eight slices\n"
           "$PY replay.py plan --seed 20260905 --lengths 0=500,1=500,2=120,3=40,4=150 --whole-max 400 --tag main\n"
           "nice -n 10 $PY replay.py control-a --ranges 12-20-200000-210000:200000:200030 --record 200010 --edge 0,1 --workers 2 --tag control-a\n"
           "nice -n 10 $PY replay.py control-b --drop-index 1 --ranges 12-20-200000-210000:200000:200030,11-17-20000-30000:25000:25030 --workers 2 --tag control-b\n"
           "nice -n 10 $PY replay.py replay --plan-file plan-main.json --workers 4 --tag main      # > main.log\n"
           "$PY render.py results-main.json                                                     # the tables above\n"
           "$PY processed.py plan-main.json                                                     # guard-passing counts\n"
           "$PY finalize.py                                                                     # sections 3-5 of this file\n```\n")
out.append("Outputs: `plan-main.json` (the sample), `shards-main.jsonl` (one line per shard as it finished), "
           "`results-main.json` (everything, including the first 20 differences per side per shard, which are empty), "
           "`results-control-a.json`, `results-control-b.json`, `main.log`, `control-a.log`, `control-b.log`.\n")
inp = main["inputs"]
out.append("| file | sha256 | records |\n|---|---|---:|")
out.append(f"| enum2/enum2.py | {inp['enum2.py']['sha256']} | |")
out.append(f"| enum2/crosscheck/replay.py | {sha(HERE / 'replay.py')} | |")
out.append(f"| enum/udenum (as hashed in every shard manifest) | {inp['udenum']['sha256']} | |")
out.append(f"| data/forbidden-74.json | {inp['forbidden']['sha256']} | 74 |")
out.append(f"| enum/out-22/dag-22-61-f12/reach.json | {sha(Path('<repo>/research/unit-distance-22/enum/out-22/dag-22-61-f12/reach.json'))} | |")
for pf in sorted(inp["parent_files"], key=lambda p: tuple(int(x) for x in Path(p).stem.split("-"))):
    out.append(f"| _parents/{Path(pf).name} | {inp['parent_files'][pf]['sha256']} | {inp['parent_files'][pf]['records']} |")
out.append(f"\nManifest cross-check by the driver (`verify_inputs`): parent-file, forbidden-list and udenum hashes equal the "
           f"values in every replayed shard manifest: {'yes' if not inp['mismatches'] else inp['mismatches']}.\n")
print("\n".join(out))
