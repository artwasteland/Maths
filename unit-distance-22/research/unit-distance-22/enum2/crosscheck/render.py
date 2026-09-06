#!/usr/bin/env python3
"""Render markdown tables from a results-<tag>.json written by replay.py."""
import json
import sys
from pathlib import Path

doc = json.loads(Path(sys.argv[1]).read_text())
rows = doc["per_cell"]
print("| cell | shards replayed / in cell | parent records replayed / in cell | d | udenum children | enum2 children | only udenum | only enum2 | identical |")
print("|---|---:|---:|---|---:|---:|---:|---:|---|")
for c in rows:
    print(f"| {c['cell']} | {c['shards']} / {c['shards_in_cell']} | {c['parents_replayed']} / {c['parents_in_cell']} | "
          f"{','.join(map(str, c['d_values']))} | {c['udenum_children']} | {c['enum2_children']} | "
          f"{c['only_udenum']} | {c['only_enum2']} | {'yes' if c['identical'] else 'NO'} |")
tot_sh = sum(c['shards'] for c in rows); tot_in = sum(c['shards_in_cell'] for c in rows)
tot_p = sum(c['parents_replayed'] for c in rows); tot_pin = sum(c['parents_in_cell'] for c in rows)
print(f"| **total** | **{tot_sh} / {tot_in}** | **{tot_p} / {tot_pin}** | | **{sum(c['udenum_children'] for c in rows)}** | "
      f"**{sum(c['enum2_children'] for c in rows)}** | **{sum(c['only_udenum'] for c in rows)}** | "
      f"**{sum(c['only_enum2'] for c in rows)}** | **{'yes' if all(c['identical'] for c in rows) else 'NO'}** |")
print()
print("Per shard (range = parent-record indices replayed; whole = the entire shard; block = udenum "
      "output lines matched to those parents by parent recovery; rec = parents recovered to locate/verify the block):")
print()
print("| shard | range | whole | d | parents | udenum block | udenum children | enum2 raw | enum2 distinct | only udenum | only enum2 | rec | identical | enum2 cpu s |")
print("|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|")
for e in sorted(doc["per_shard"], key=lambda e: (e["n"], e["m"], e["range"][0])):
    print(f"| {e['shard_id']} | [{e['range'][0]},{e['range'][1]}) | {'y' if e['whole_shard'] else 'n'} | "
          f"{','.join(map(str, e['d_values']))} | {e['parents_replayed']} | [{e['udenum_block'][0]},{e['udenum_block'][1]}) of {e['udenum_shard_lines']} | "
          f"{e['udenum_children']} | {e['enum2_children_raw']} | {e['enum2_children']} | {e['only_udenum']} | {e['only_enum2']} | "
          f"{e['udenum_recovered_parents']} | {'yes' if e['identical'] else 'NO'} | {e['enum2_cpu_seconds']:.0f} |")
diffs = [e for e in doc["per_shard"] if not e["identical"]]
print()
if diffs:
    print("Differences (first 20 per side per shard):")
    for e in diffs:
        print(f"- {e['shard_id']} [{e['range'][0]},{e['range'][1]}): only udenum {e['only_udenum_first20']}; only enum2 {e['only_enum2_first20']}; "
              f"udenum lines {e['udenum_children']} distinct {e['udenum_distinct']}; parents replayed {e['parents_replayed']}; "
              f"shard lines {e['udenum_shard_lines']} vs manifest {e['udenum_manifest_children_written']}; "
              f"children file hash matches manifest: {e['children_file_sha256_matches_manifest']}")
else:
    print("No differences.")
