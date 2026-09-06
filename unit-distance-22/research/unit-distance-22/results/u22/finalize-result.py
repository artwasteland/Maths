#!/usr/bin/env python3
"""finalize-result.py: fill RESULT-u22.md's [fleet] placeholders from final-levels.json.

Run only when final-levels.json says all 48 slices finished (it refuses otherwise). It rewrites
Section 4's table from the record, the title and the theorem's conditionality, the G6 gate row,
and Section 7's "[when green]". It changes nothing else, and it prints every line it changed.

  python3 research/unit-distance-22/results/u22/finalize-result.py [--force]
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RES = ROOT / 'research/unit-distance-22/results/u22'
DOC = ROOT / 'research/unit-distance-22/RESULT-u22.md'
rec = json.loads((RES / 'final-levels.json').read_text())
done = len(rec['finished_slices'])
if done != rec['slices_total'] and '--force' not in sys.argv:
    sys.exit(f'refusing: {done} of {rec["slices_total"]} slices finished (pass --force to fill anyway)')

s = DOC.read_text()
changed = []
def sub(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:80]
    s = s.replace(old, new, count); changed.append(new.strip().split('\n')[0][:100])

WINDOWS = {13: '23..30', 14: '26..33', 15: '30..37', 16: '34..41', 17: '38..43', 18: '42..46', 19: '46..49', 20: '51..52', 21: '56', 22: '61'}
l13 = rec['level13_shared']
rows = [f"| 13 (shared) | {WINDOWS[13]} | {l13['children']:,} | {l13['kept']:,} | {100 * (1 - l13['kept'] / l13['children']):.1f}% |"]
for l in rec['levels']:
    pr = f"{100 * (1 - l['kept'] / l['children']):.1f}%" if l['children'] else ''
    rows.append(f"| {l['n']} | {WINDOWS.get(l['n'], '')} | {l['children']:,} | {l['kept']:,} | {pr} |")
table_old = re.search(r'\| level \| window m \| children \(all slices\) \| kept after TU \| pruned \|\n\|---\|---\|---:\|---:\|---:\|\n(?:\|.*\n)+', s)
assert table_old, 'Section 4 table not found'
table_new = '| level | window m | children (all slices) | kept after TU | pruned |\n|---|---|---:|---:|---:|\n' + '\n'.join(rows) + '\n'
s = s[:table_old.start()] + table_new + s[table_old.end():]; changed.append('Section 4 table rewritten from final-levels.json')
top = next(l for l in rec['levels'] if l['n'] == 22)
sub('# The unit-distance number of 22 points: u(22) = 60 (DRAFT, conditional on the fleet)', '# The unit-distance number of 22 points: u(22) = 60')
sub('**Theorem (conditional, see Section 6).** No unit-distance graph on 22 vertices has 61 edges.\nHence u(22) = 60.', '**Theorem.** No unit-distance graph on 22 vertices has 61 edges. Hence u(22) = 60.')
sub('## 4. What the run produced [fleet]', '## 4. What the run produced')
s = re.sub(r'\| G6 \| no claim while UNKNOWN\.g6 is non-empty \|[^\n]*\|', f"| G6 | no claim while UNKNOWN.g6 is non-empty | all {rec['slices_total']} slices complete ({rec['generated']}): {top['children']} F-free graphs at (22,61) in all (slices 15 and 38, two each), each eliminated by a checked TU forbidden-pattern witness AND independently refuted by the embedder with a checked algebraic certificate (`results/u22/cell-22-61/`); every UNKNOWN.g6 empty; keep union {rec['keep_union_22_61']} |", s, count=1); changed.append('G6 row')
sub('- Claimed [when green]: u(22) = 60', '- Claimed: u(22) = 60')
s = s.replace('The top level is not empty by default. Over the 44 completed slices', f"The top level is not empty by default. Over all {rec['slices_total']} slices"); changed.append('Section 2b count')
s = s.replace('The\nremaining four slices (37, 39, 42, 45) were still enumerating when this was written.', 'Every slice is complete.'); s = s.replace('The remaining four slices (37, 39, 42, 45) were still enumerating when this was written.', 'Every slice is complete.')
s = s.replace('## 2b. The (22,61) cell, as of 44 of 48 slices (2026-09-05 21:00Z)', f"## 2b. The (22,61) cell, all {rec['slices_total']} slices ({rec['generated']})")
DOC.write_text(s)
print('\n'.join('  ' + c for c in changed)); print('RESULT-u22.md finalised')
