"""Generate a source-bound Round 2 report without rerunning discovery."""
from round2 import *
import ast,collections

def main():
 configure()
 read=lambda name:json.loads((R/name).read_text())
 audit=read('round2-final-audit.json');methods=read('control-method-results.json');proposal=read('39-ideal-derivation-test.json')
 prep=json.loads((MODULE/'evidence/preparation.json').read_text())
 unchanged={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in prep['input_sha256'].items()};assert all(unchanged.values())
 oversized=[];invalid=[]
 for path in sorted(MODULE.glob('*.py')):ast.parse(path.read_text(),filename=str(path))
 for path in sorted(MODULE.rglob('*')):
  if not path.is_file():continue
  if path.suffix in {'.py','.md','.json','.jsonl','.txt'}:
   with path.open('r',errors='strict') as f:
    for n,line in enumerate(f,1):
     if chr(0x2014) in line:invalid.append([str(path.relative_to(MODULE)),n])
     if path.suffix=='.jsonl' and len(line.encode())>8*1024*1024:oversized.append({'file':str(path.relative_to(MODULE)),'line':n,'bytes':len(line.encode())})
 assert not invalid,invalid
 bytecode=[str(p.relative_to(MODULE)) for p in MODULE.rglob('*.pyc')];assert not bytecode,bytecode
 inventory={'input_hashes_unchanged':unchanged,'python_files_parsed':len(list(MODULE.glob('*.py'))),'em_dash_lines':invalid,'bytecode':bytecode,'oversized_raw_records':oversized,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(MODULE.glob('*.py'))},'checker_sha256':hashlib.sha256((ROOT/'research/gp-10/check/gp10check.py').read_bytes()).hexdigest(),'contract_sha256':hashlib.sha256((ROOT/'research/gp-10/CONTRACT.md').read_bytes()).hexdigest(),'gp_tex_sha256':hashlib.sha256((UD/'sources/gp/smallUD.tex').read_bytes()).hexdigest(),'evidence':{str(p.relative_to(R)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(R.glob('*')) if p.is_file() and p.name!='round2-inventory.json'}}
 (R/'round2-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
 attempt_rows=[]
 for p in sorted(R.glob('*.attempts.jsonl')):
  rows=list(records(p));attempt_rows.append(f"| {p.name} | {len(rows)} | {sum(x.get('seconds',0) for x in rows):.3f} | {sorted({x.get('limit') for x in rows})} |")
 notes="""# Round 2 exploration notes

Accepted claims are restricted to official checker runs listed in REPORT.md.
Raw exploration output is not an accepted proof library. In particular, the
following records exceed the official 8 MiB line limit and are not selected:

"""
 notes+='\n'.join(f"- `{x['file']}`, line {x['line']}, {x['bytes']} bytes." for x in oversized)+'\n'
 notes+="""
The factored centroid experiment recorded a native FLINT abort under the
address-space cap in `stalls-66-factored-crash.json`. Several exploratory
index 39 expansions similarly exhausted memory or exceeded the certificate
term budget. These are unknown attempts. Exact local expansion of an
oversized identity is not official certificate acceptance.

The index 39 direct, homogeneous, quotient-ring, saturation and elimination
experiments remain in `evidence/round2/`. Empty JSONL output means no
certificate was emitted; consult the neighboring attempt or summary file.
The final compact derivation is a proposal document, not a record stream.
The final full expansion has 446203 terms; the earlier triangle reduction
had 434887. Both exceed the current term guard and remain unknown.

The first Round 2 test run selected a direct-containment fixture from B8p,
but that sweep contained only nonempty TU proofs. The fixture was corrected
to explicit in-force K4 containment. A subsequent quotient-wrapper test
exposed a Singular loop-variable redeclaration warning between its exact
markers. Separate loop variable names fixed parsing; the full positive
and negative wrapper controls then passed. Neither issue emitted a false
refutation. FGLM now recreates the actual source variable order before
marking a saved basis as a standard basis; its changed-order positive and
positive-dimensional red control both pass.

Recorded edge-frame sweeps and focused trials:

| Attempt log | Frames | Observed seconds | Per-frame limits |
|---|---:|---:|---|
"""+ '\n'.join(attempt_rows)+'\n'
 notes+="""
The source GP picture for the intended index 22 graph differs from the
frozen edge list: replacing the drawn 1--4 edge by 3--4 gives an exact
isomorphism. `appendix-maps.json` preserves the proposed correction and the
checked map. The source itself was not changed. The generated certificates
use the frozen graph and are checked independently of that identification.
The other three Appendix maps match without a correction.
"""
 (MODULE/'LABNOTES-ROUND2.md').write_text(notes)
 methodtable=[]
 for method in ['tu','tree','null','real']:
  a,b=methods['B8p-'+method],methods['B9p-'+method]
  methodtable.append(f"| {method} | {a['budget']:g} | {a['refuted']}/17 | {a['elapsed']:.3f} | {b['refuted']}/101 | {b['elapsed']:.3f} |")
 stalls=[]
 for i,label in [(22,'F(9,14,2), intended picture'),(38,'F(9,14,18)'),(66,'F(9,15,27)')]:
  s=read(f'final-stall{i}.summary.json');cert=next(records(R/f'final-stall{i}.jsonl'))['cert']
  stalls.append(f"| {i} | {label} | {cert['frame']} | {s['limit']:g} | {s['seconds']:.3f} | {(R/f'final-stall{i}.jsonl').stat().st_size} |")
 runrows=[]
 for key,limit in [('retry_records',0),('GP74',0),('B8p',7),('B9p',8),('B8p-replay',7),('B9p-replay',8)]:
  x=audit[key];runrows.append(f"| `{x['run']}` | {limit} | {x['refuted']}/{x['records']} | `{x['final_line']}` |")
 report="""
## Round 2

The current-contract result is **three of the four stalls refuted, 17/17
B8p forbidden controls, 100/101 B9p forbidden controls, and 73/74 GP graphs**.
Index 39, `HGEAXjw`, remains unknown. The complete B9p and GP74 requirements
are therefore not met. Official sample acceptance below includes the
explicit unknown record; it is not a claim of a complete gate pass.
This section supersedes the historical checker-availability and TU-format
uncertainties above. No new certificate type is emitted.

### The four stalls

All three successful constructions produce existing R-real certificates
with an empty forbidden list. These are final-source regeneration timings,
including local exact verification, not estimates:

| F9 index | GP Appendix identification | Edge frame | Budget seconds | Observed seconds | Record bytes |
|---:|---|---|---:|---:|---:|
"""+ '\n'.join(stalls)+"""

Index 39 is F(9,14,19). `evidence/round2/appendix-maps.json` contains the
zero-based picture-to-canonical maps. Index 22 requires the explicitly
recorded one-edge picture correction; see LABNOTES-ROUND2.md. That textual
identification is not a premise trusted by the checker.

The TU pass with F8 and the 70 prior refutations found none of the four.
A second index 39 TU pass with the other 73 GP proofs also found none.
All edge frames were tried with distance-two saturation for indices 22,
38 and 39. Larger focused experiments also used all nonedges, different
orders, FGLM coordinate elimination, standard and slimgb bases, and
homogeneous lifts. The centroid proof succeeded before exhausting every
frame for index 66. Attempts and failed budgets are retained, not counted
as proofs. See the attempt table in LABNOTES-ROUND2.md.

For 22 and 38, the GP arguments suggest a sum of squares that vanishes on
the edge ideal. Exact lifts prove that identity and a unit identity after
adjoining its square factors. The weighted Lagrange identity compiles both
into a single permitted R-real certificate. For 66, the target is
`6 + qx^2 + qy^2`, where q is the difference between the sums of the two
triangle vertex sets. Homogenization with padding 6 produces a smaller
lift, dehomogenized and expanded before output. PROOFS.md gives the exact
identities, including the preprocessing and positivity arguments.

### Index 39: proposed encoding amendment, not an accepted refutation

The two-circle argument gives an exact rational ideal derivation. Its
ordinary expansion remains too large: the last attempt has 446203
cofactor terms. It returns unknown before emitting a certificate.
`evidence/round2/39-ideal-derivation.json` stores shared intermediate ideal
identities and has no verdict or certificate type. The proposal uses
"""+f"""{proposal['rows']} rows and {proposal['bytes']} bytes. Generation and local checking took
{proposal['seconds']:.3f} seconds. A one-coefficient mutation fails with
`{proposal['one_coefficient_mutation']}`.
"""+"""

PROOFS.md proposes R-null-dag: every row must expand exactly as a polynomial
combination of original generators and strictly earlier rows, and the last
row must be one. Induction proves every row is in the regenerated ideal.
It specifies source validation, ordering, sparse encoding and resource
checks. This changes proof sharing in the encoding, not the underlying
Nullstellensatz theorem. An ordinary small R-null proof would also solve
the problem, but none was found. The proposal needs a contract amendment
and an independent official-checker implementation before it can count.
`ideal_derivation.py` is only a local prototype. No proposal document is
included in an official run manifest.

### Control budgets

`round2.py prepare` scanned all 383 B8p and 3085 B9p inputs with this
module's deterministic subgraph matcher. It selected exactly 17 and 101
by containment of a frozen F9 member. `selection.json` records the global
index and an explicit map for every selected graph. F7 means the first
6 F9 entries; F8 means the first 19.

The first independent sweeps gave the following results. Every successful
record in each sweep was accepted by the official checker under limit 7
or 8. Times are measured totals for the stated control subset:

| Method | Seconds per graph | B8p success | B8p seconds | B9p success | B9p seconds |
|---|---:|---:|---:|---:|---:|
"""+ '\n'.join(methodtable)+"""

The initial union was 14/17 and 85/101. Fresh tree retries at 12 seconds
refuted indices 17, 18, 71, 59, 73, 58, 64, 56, 61, 67, 65 and 63. Index
69 needed the 40-second retry (13.036 seconds observed). All-nonedge null
retries with a 10-second budget refuted indices 16 and 68, in 0.386 and
2.815 seconds. The three guided R-real constructions above supply the
remaining successful nine-vertex cases. These fresh discoveries, without
copying the old library, give the final 17/17 and 100/101 runs.

Cumulative fresh success counts, after those focused retries:

| Method | B8p | B9p |
|---|---:|---:|
"""+ '\n'.join(f"| {m} | {audit['B8p']['fresh_cumulative_by_certificate_type'][m]}/17 | {audit['B9p']['fresh_cumulative_by_certificate_type'][m]}/101 |" for m in ['tu','tree','null','real'])+"""

For scheduling, use the measured cheap passes first: TU at 0.5 seconds,
tree at 2.5 seconds, then tree at 12 and 40 seconds on remaining graphs.
Use a 10-second all-nonedge null retry for the remaining algebraic cases.
The generic 2.5-second real sweep does not discover the three new guided
proofs. Retain the documented specialized commands for those graphs.
These are control-derived budgets, not completion guarantees on 10 vertices.
The CLI's default equal sharing of a total graph budget is unchanged;
separate single-method calls reproduce the table's allocations.

For existing checked proofs, the new optional `--methods reuse,tu` verifies
and replays matching records from `--refuted`, then searches containment or
TU closure. It produced 17/17 and 100/101 with a 2.5-second total per-graph
budget. This is explicitly replay, not fresh discovery. Measured graph
processing totals were """+f"""{audit['B8p-replay']['graph_seconds']:.3f} and {audit['B9p-replay']['graph_seconds']:.3f} seconds; these exclude
the upfront known-library validation and canonicalization.
"""+"""
The library `evidence/round2/GP73.refuted.jsonl` contains actual prior
certificates, all independently accepted in `checker-GP74-final`. A match
copies and rechecks its certificate; it does not issue a self pointer.

### Official verification and regression evidence

Each directory below has a `sample` manifest, exact sorted input coverage,
SHA256, records, UNKNOWN.g6, checker output, and captured `check.log`.
The adapter relocates only official checker scratch to the authorized
scratch tree. It changes no checking rule or size limit.

| Run directory | forbidden_limit | Refuted / records | Exact final line |
|---|---:|---:|---|
"""+ '\n'.join(runrows)+"""

All eight initial method-run logs also end `ACCEPT run verified`; their
paths and counts are in `control-method-results.json`. The final GP74,
fresh B8p and fresh B9p maximum record sizes are """+f"""{audit['GP74']['max_line_bytes']},
{audit['B8p']['max_line_bytes']}, and {audit['B9p']['max_line_bytes']} bytes, respectively.
"""+"""
The independent coefficient mutation rejects with `cofactor_identity`;
the SOS-constant mutation rejects with `sos_constant_positive`. Both run
logs end `REJECT run records_rejected`. The genuine matching certificate
passes. `round2-tests.json` records 15 controls covering those official
checks, global prefix/index rules, noninjective maps, empty TU rejection,
ordinary and homogeneous std/slimgb lifts, FGLM source ordering, and the
quotient wrapper, and a corrupted replayed certificate. Every new wrapper has a positive and one-field negative
control. The existing regression suite again passed all 21 controls;
its isolated outputs are under `round2/regression/`.

The Round 1 soundness evidence remains historical: 559 known-embeddable
inputs per method, zero false refutations, plus the deliberate wrong-frame
prism red control. That complete soundness sweep was not rerun in Round 2.
The changed algebraic constructions were instead checked through exact
identities, targeted red controls and the independent official checker.

Amendment 4 is implemented: lists must be frozen prefixes, indices remain
global, TU chains are nonempty, and direct containment uses `sub`. Existing
R1 source-bound streams retain their historical provenance. No unsupported
type is emitted. Raw oversized exploratory records remain outside the
accepted libraries; LABNOTES-ROUND2.md lists their sizes. Native FLINT
aborts and memory failures are also recorded as unsuccessful exploration.

### Commands and reproducibility

Every invocation below used:

```sh
ulimit -v 976562
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B SCRIPT_AND_ARGUMENTS
```

Concrete commands run in this round (paths relative to the repository):

```text
research/gp-10/refute/round2.py prepare
research/gp-10/refute/round2.py sweep --suite stalls --method tu --seconds 20 --prefix 19 --known --tag stalls-tu-f8-known
research/gp-10/refute/stall_search.py --index 22 --seconds 15 --sat distance2 --tag stalls-22-d2-frames
research/gp-10/refute/stall_search.py --index 38 --seconds 15 --sat distance2 --tag stalls-38-d2-frames
research/gp-10/refute/stall_search.py --index 39 --seconds 12 --sat distance2 --count 14 --tag stalls-39-allframes-d2
research/gp-10/refute/round2_retry.py --indices 17 18 71 69 59 73 58 64 56 61 67 65 63 --method tree --seconds 12 --tag controls-tree-retry12
research/gp-10/refute/round2_retry.py --indices 69 --method tree --seconds 40 --tag controls-tree-retry40
research/gp-10/refute/round2_retry.py --indices 16 68 --method null --seconds 10 --all-sat --tag controls-null-retry10
research/gp-10/refute/real_radical.py --index 22 --seconds 60 --tag final-stall22
research/gp-10/refute/real_radical.py --index 38 --seconds 90 --tag final-stall38
research/gp-10/refute/centroid66.py --frame 6 7 --reduce --scale --homogeneous --padding 6 --seconds 55 --tag final-stall66
research/gp-10/refute/analytic39.py --tag stalls-39-projected-restoration --seconds 55
research/gp-10/refute/quotient39.py --seconds 55 --tag stalls-39-quotient
research/gp-10/refute/round2_proposal.py
research/gp-10/refute/round2_tests.py
research/gp-10/refute/round2_audit.py
research/gp-10/refute/round2_report.py
```

The eight initial sweeps used `round2.py sweep --suite B8p|B9p --method
METHOD --seconds LIMIT --prefix PREFIX --tag SUITE-METHOD`, with exactly
the table's limits and prefix 6 for B8p or 19 for B9p. Their summary files
retain the complete actual argv and source hashes. Fresh tags are required
when repeating discovery. The replay CLI invocations used the selected
`round2/B8p.g6` or `round2/B9p.g6`, `--methods reuse,tu --time-limit 2.5`,
`--refuted evidence/round2/GP73.refuted.jsonl`, and `--forbidden fixtures/F6.json`
or `fixtures/F19.json`. Their complete configuration, input hashes,
per-graph timings and source hashes are beside `B8p-replay.jsonl` and
`B9p-replay.jsonl`. Module-relative paths in this paragraph are prefixed by
`research/gp-10/refute/` when invoking the CLI from the repository root.
The regression suite was run in frozen Python as
`selftest.main(round2.R / "regression")`, keeping the original fixtures.
Earlier exploratory command lines are retained in neighboring `.meta.json`
and `.summary.json` files; frame trials are indexed in LABNOTES-ROUND2.md.

`round2_audit.py` assembles and checks the final results.
`round2_report.py` computes the report and inventory from actual evidence,
checks the original frozen-input hashes, parses every module Python file
without bytecode, and checks for prohibited em dash characters. The
inventory records current source, checker, contract and input hashes.
All writes were confined to this module and `/tmp/gp10-refute/`; no git,
package installation, oversight program or source-repository mutation was
used. CAS and worker jobs were sequential, with at most one child, under
the stated niceness and the stricter approximately 1 GB address-space cap.
No individual discovery invocation allocated more than five minutes; the
control and edge-frame samples and budgets are stated above.

## UNCERTAIN

- Index 39 is still unknown to the current official checker. Thus the
  requested all-101 B9p control and all-74 GP coverage are incomplete.
  Sample `ACCEPT` does not resolve this gap or establish a full GP-10 gate.
- The compact index 39 derivation has only local exact verification. Its
  proposed encoding is unapproved, and its prototype shares the producer's
  system builder. A separate checker implementation, rejection controls,
  resource review and contract amendment are required before counting it.
  No proof that a small certificate in the current encoding is impossible
  is claimed. The quotient-ring timeout is only a bounded failed search.
- The least certain source interpretation is the index 22 GP picture
  correction. Frozen-graph isomorphism and official algebra verification
  protect the accepted certificate from that interpretation, but the
  intended historical figure should still be reviewed.
- Large cofactor expansion remains the main resource risk. Native FLINT
  aborts can bypass Python exceptions; a main-process crash still requires
  resume to turn its pending graph into unknown. Some raw experimental
  identities exceed the line limit. They are excluded from accepted runs.
- The complete Round 1 embeddable-input soundness suite was not rerun after
  every Round 2 change. New identities, checker mutations, wrapper controls
  and the full local regression suite were exercised. A deeper generic
  search can still expose untested paths. No B10 run, minimality pipeline,
  full B8/B9 gate profile or new package was exercised.
- Budgets are observations on this machine. Near-limit outcomes depend on
  load; small regeneration timings do not justify reducing the allocated
  guided-proof budgets automatically. No exhaustive alternative tree order
  or universal algebraic discovery guarantee is claimed.
"""
 target=MODULE/'REPORT.md';old=target.read_text().split('\n## Round 2\n',1)[0];target.write_text(old.rstrip()+'\n'+report)
 print(json.dumps({'report':'REPORT.md','source_files_parsed':inventory['python_files_parsed'],'input_hashes_unchanged':all(unchanged.values()),'oversized_raw_records':len(oversized),'round2_status':'partial, index 39 remains unknown'},indent=2))
if __name__=='__main__':main()
