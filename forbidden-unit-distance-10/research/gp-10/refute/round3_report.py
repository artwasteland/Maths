"""Append a source-bound Round 3 report and audit its retained evidence."""
from round3 import *
import ast,collections,resource

def main():
 configure()
 read=lambda name:json.loads((R/name).read_text())
 final=read('candidate-final.json');status=final['candidate_status'];close=read('F39.summary.json');controls=read('control-closure.json')
 assert status['unprocessed']==status['pending_tree']==0
 assert final['combined_check']['final_line']=='ACCEPT run verified'
 prep=json.loads((MODULE/'evidence/preparation.json').read_text())
 unchanged={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in prep['input_sha256'].items()};assert all(unchanged.values())
 frozen={name:sha for sha,name in (line.split() for line in (ROOT/'research/gp-10/data/SHA256SUMS').read_text().splitlines())}
 assert final['b10_membership']['sha256']==frozen['B10.g6']
 assert final['combined_check']['checker_sha256']==hashlib.sha256((ROOT/'research/gp-10/check/gp10check.py').read_bytes()).hexdigest()
 assert all(b['final_line']=='ACCEPT run verified' for b in status['batches'])
 assert read('dag-tests.json')['status']==read('collision-tests.json')['status']==read('quadratic-tests.json')['status']==read('dag-replay-test.json')['status']=='PASS'
 regression=json.loads((R/'regression/evidence/selftest.json').read_text());assert regression['status']=='PASS'
 methodrows=[]
 for method,label in [('tu','TU'),('tree','Tree retries'),('null','Separate null pilot'),('real','Separate real pilot'),('portfolio','Shared null + real')]:
  methodrows.append(f"| {label} | {status['per_method_attempts'][method]} | {status['new_certificate_types'].get(method,0)} | {status['per_method_seconds'][method]:.3f} |")
 newrows=[]
 for row in final['new_refutations']:
  end=('F9 index '+str(row['terminal']['forbidden'])) if row['terminal'] else 'AMP proof tree'
  newrows.append(f"| ``{row['g6']}`` | {row['edges']} | {row['type']} | {end} |")
 pilot=final['all_sat_pilot'][0]
 report=f"""
## Round 3

**Index 39 is now accepted in the adopted DAG format. The candidate pass is
complete at the recorded budgets: {status['new_refuted']} new refutations,
{status['still_undecided']} still undecided, and no eligible graph left unattempted.**
This section supersedes the earlier statements that index 39 requires an
unapproved encoding. Earlier round sections remain historical records.
Amendment 5 is accepted; no additional amendment is needed for these proofs.

### Index 39 and the closed controls

`HGEAXjw`, F9 index 39, is emitted in
`evidence/round3/F39.null-dag.jsonl`: {close['row_count']} rows and
{close['record_bytes']} bytes including the JSONL newline. The rows retain
the exact ideal derivation from Round 2. They use original generators or
strictly earlier `aux:j` rows and finish with the polynomial 1. No forbidden
pointer or unapproved generator is used.

| Official sample run | forbidden_limit | Seconds | Exact final line |
|---|---:|---:|---|
"""
 for run in close['runs']:
  report+=f"| `{Path(run['directory']).name}` | {run['forbidden_limit']} | {run['seconds']:.3f} | `{run['final_line']}` |\n"
 report+=f"""
Both runs exited 0. The retained GP library now has **74/74** refutations
with an empty list in force (`checker-GP74`, {controls['GP74']['seconds']:.3f}
seconds). The forbidden-containing B9p control sample now has **101/101**
refutations with F8 in force (`checker-B9p-forbidden`,
{controls['B9p-forbidden']['seconds']:.3f} seconds). Both exact final lines are
`ACCEPT run verified`. These close the prior missing-control cases by
combining retained accepted certificates with the new index 39 record;
they are not fresh per-method discoveries or complete B9 gate runs.
The actual proof library is `evidence/round3/GP74.refuted.jsonl`.

### Candidate coverage and new certificates

The supplied candidate file contains {status['candidate_count']} distinct
isomorphism classes, all present in frozen `data/B10.g6`. Their edge-count
histogram is `{final['candidate_edge_counts']}`. Candidate SHA256:
`{status['snapshot']['candidate_sha256']}`.
All discovery batches followed nondecreasing edge count; finalization
checked that order from the emitted records.

The completed external tree stream has {status['external_refuted']} refutations
and {status['candidate_count']-status['external_refuted']} unknowns. Its actual
refutations were independently accepted in `tree-library-final-check`.
The completed external embedder stream reports {status['external_embedded']}
embeddings. Those embedding certificates were used as the requested
scheduling exclusions and were not independently checked by this module.
Both streams were read only. Their complete-prefix byte counts and hashes
are retained in `candidate-final.json` and `/tmp/gp10-refute/cand/FINAL.json`.

This producer processed {status['processed']} candidates in {final['batch_count']}
checked batches. Of those, {status['processed_later_embedded']} were subsequently
reported embedded by the live embedder. The final eligible set therefore
has {status['current_eligible']} graphs, with {status['new_refuted']} new
refutations and {status['still_undecided']} unknowns. There is no refuted/embedded
conflict and `UNPROCESSED.g6` is empty. The final partition is
{status['external_refuted']} external tree refutations + {status['new_refuted']}
new refutations + {status['external_embedded']} reported embeddings +
{status['still_undecided']} undecided = {status['candidate_count']}.

| New graph6 | Edges | Certificate | Terminal |
|---|---:|---|---|
"""+'\n'.join(newrows)+f"""

All new records are in `/tmp/gp10-refute/cand/new-refuted.jsonl`.
The complete accepted refutation collection, including external tree proofs,
is `all-refuted.jsonl` in the same directory. The exact remaining list is
`/tmp/gp10-refute/cand/UNKNOWN.g6`, with {status['still_undecided']} lines and
edge-count histogram `{final['unknown_edge_counts']}`.
`REFUTED.g6` lists only this round's new discoveries; external decisions
have separately named lists. `own-results.jsonl` preserves all local work,
including unknown records later excluded by the embedder.

Every batch ended `ACCEPT run verified`. The final combined sample run
`/tmp/gp10-refute/cand/checker-final` also ended exactly
`ACCEPT run verified`, exit 0: {final['combined_check']['records']} records,
{final['combined_check']['refuted']} refuted, and {status['still_undecided']}
unknown, in {final['combined_check']['seconds']:.3f} seconds. F9, all 74 graphs,
was in force (`forbidden_limit: 9`). The combined input excludes the
externally reported embeddings. Sample acceptance validates the emitted
refutations and coverage accounting; it does not decide unknowns or pass
the complete GP-10 gates.

### Methods, budgets and measured time

| Local method | Attempts | New refutations | Observed method seconds |
|---|---:|---:|---:|
"""+'\n'.join(methodrows)+f"""

These are actual per-attempt timings from `batch-*/timings.jsonl`. The
shared null/real basis is counted once; its time must not be added again
as two separate method runs. The DAG choice is a certificate representation
inside that search, not an additional independent attempt. No candidate
was newly refuted by null, real or DAG search.

The first batch used separate null and real budgets of 2.5 seconds each
on 22 candidates. Subsequent batches shared one Groebner basis with a
5-second null/real budget, using a triangle-rich actual edge as frame.
TU received 0.5 seconds first. Previously completed tree fixed points
were retained from the external pass using the identical `amp_core.py`
hash. Prior deadline or state-limit exits received a 12-second, 1000-state
tree retry unless TU had already refuted the graph. There were
{status['per_method_attempts']['tree']} actual tree retries. The original
external tree pass used 5 seconds and 200 states; its work is not counted
as new local tree discovery or time.

The all-nonedge saturation pilot (`batch-0010`) used 10 seconds for each
shared algebra attempt on {pilot['records']} candidates. It found no new
refutations and took {pilot['search_seconds']:.3f} search seconds, so remaining
batches returned to 5 seconds with four-cycle diagonal saturation.
Unsuccessful algebra reasons and final trace stages are tabulated in
`candidate-final.json`. No recorded stage exposed a positive target waiting
for a longer lift. This is a search observation, not a proof of feasibility.

Each invocation selected a stated sample of at most 40 candidates and
reserved at most {final['maximum_allocated_batch_seconds']:g} seconds of
method budgets. The total across all bounded samples was
{status['batch_search_seconds']:.3f} search seconds and
{status['batch_check_seconds']:.3f} batch-check seconds. These exclude external
passes, development and controls, startup/canonicalization before the batch
timer, and the separately timed final check. Timings depend on machine load.

### Implementation and checks

`dag.py` locally checks canonical sparse rows, exact cofactor expansions,
strict backward references, the last target and real positivity. The CLI
accepts optional `dag` and `portfolio` methods and can load accepted DAG
records. Ordinary default method names remain available. The automatic
DAG policy avoids a large final cofactor expansion when its conservative
term bound exceeds 60000. Final official checking still enforces the
contract's limits. The largest record in accepted candidate batch streams,
the final stream and the required index 39 stream is
{final['max_accepted_record_bytes']} bytes, below the 8 MiB ceiling.

The shared search also tries exact collision identities and a bounded
quadratic SOS discovery step. The latter uses a single-threaded numerical
linear program only to propose rational weights. It reconstructs and
checks an exact rational polynomial identity, then requires an exact lift
to the original ideal and local and official proof verification. LP
infeasibility, numerical failure or the quadratic row budget simply leaves
the graph unknown. `PROOFS.md` records the algebra behind both additions.
The quadratic control recovered the known centroid target for index 66,
but that target alone is not counted as a new refutation. Code evolved
during the samples; each plan preserves its actual source hashes.

`round3_tests.py` exercised accepted null-DAG and real-DAG records and
one-field corruptions. Official rejection reasons include
`dag_row_identity`, `dag_reference_order`, `sparse_noncanonical` and
`sos_constant_positive`. Additional controls exercised Sturm and constant
real-DAG targets, automatic DAG selection, rational normalization and the
collision construction. The LP positive control and one-constant negative
control both behaved as required. The prism, Petersen graph and Moser
spindle were not refuted in the bounded new-method controls.

The producer-interface DAG replay control loaded the genuine index 39
record, replayed it with `--methods reuse --time-limit 5`, resumed without
changing output bytes, and passed the official checker. Changing one row
coefficient in its known-library record rejected with `dag: row identity 0`.
`dag-replay-test.json` records the exact producer argv and official result.

The final-source regression suite passed all {regression['count']} controls,
including wrong-frame, coefficient and generator mutations, nonempty TU
chains, Singular positive/negative wrappers, exception and worker-crash
recovery, both L3 children, resume configuration checks and pointer cycles.
Evidence is under `evidence/round3/regression/`. The first DAG test draft
accidentally mutated an aliased polynomial twice, and the rational parser
initially delegated an allowed spelling to a stricter FLINT parser. Both
issues were corrected and positive/negative controls rerun; `LABNOTES.md`
retains those development failures. No false refutation was emitted from them.

The official-checker adapter changes only its scratch directory and
`TMPDIR`/`SQLITE_TMPDIR`, keeping every write under the authorized tree.
No mathematical rule, parser rule or resource limit is relaxed. Checker
SHA256: `{final['combined_check']['checker_sha256']}`.

### Commands and reproduction

Every invocation used this prefix, with the frozen interpreter:

```sh
ulimit -v 976562
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B SCRIPT_AND_ARGUMENTS
```

Commands run for retained evidence, relative to the repository:

```text
research/gp-10/refute/round3.py
research/gp-10/refute/round3_controls.py
research/gp-10/refute/round3_tests.py
research/gp-10/refute/round3_extra_tests.py
research/gp-10/refute/collision_tests.py
research/gp-10/refute/quadratic_tests.py
research/gp-10/refute/candidate_batches.py --count 22
research/gp-10/refute/candidate_batches.py --count 30
research/gp-10/refute/candidate_batches.py --count 40
research/gp-10/refute/candidate_batches.py --count 20 --all-sat --algebra-seconds 10
research/gp-10/refute/candidate_status.py
research/gp-10/refute/round3_finish.py
research/gp-10/refute/round3_report.py
```

The bounded batch command was repeated as needed, sequentially. Actual
selected inputs, budgets, external snapshots, method timings, source hashes
and checker logs are in every `batch-*` directory. Discovery replay needs
those source versions and budgets; current code on a live shared machine
need not reproduce a near-deadline result exactly. Certificate checking is
reproducible from each run directory using `round2.check(Path(RUN_DIR))`.
The inline DAG replay control called `gp10refute.main` twice with the exact
argv in `dag-replay-test.json`, used `load_known` on the genuine and mutated
records, and called `check_run` on the replayed record.
The final regression command inserted `research/gp-10/refute` into
`sys.path` and called
`selftest.main('research/gp-10/refute/evidence/round3/regression')` in frozen
Python. The completed external-tree library was built by
`round3.check_run(C/'tree-library-final-check', refuted_tree_rows, 9)`.
Inline portfolio controls called `run_method(code, 'portfolio', 5)` on GP
indices 1 and 4 and `check_run` on their results. The automatic DAG control
used `run_method(forbidden_canonical()[68], 'portfolio', 10, all_pairs=True)`.

`round3_report.py` derives these tables from retained evidence, verifies the
original frozen input hashes and B10 checksum, parses every module Python
file without bytecode, and checks for prohibited em dash characters.
`round3-inventory.json` records the resulting source and artifact hashes.
Only this module and `/tmp/gp10-refute/` were written. No git commands,
installs, oversight programs or source-repository mutations were used.
Jobs were niced with a stricter approximately 1 GB address-space cap;
CAS and worker children were sequential, at most one child at a time.

## UNCERTAIN

- {status['still_undecided']} candidates remain undecided. This is completion of
  the requested bounded pass, not a complete classification of B10.
  Null/real discovery yielded no new candidate certificate. Longer budgets,
  different frames or saturation sets, or new mathematical ideas may help.
- The least independently checked premise is the external candidate
  reduction: this module checked B10 membership and isomorphism distinctness,
  but not every one-edge deletion or every external embedding certificate.
  The seven new certificates establish non-embeddability. Minimality relies
  on the brief's supplied deletion premise and is not independently claimed.
- External embeddings are scheduling exclusions at the recorded completed
  stream snapshot. A later correction to those inputs requires another
  reconciliation. There is no refuted/embedded conflict in this snapshot.
- The SOS LP is an incomplete numerical discovery heuristic. Exact rational
  reconstruction, ideal lifts and the official checker protect emitted
  proofs, but cannot turn its failed searches into feasibility certificates.
  The row cap, square dictionary and saturation choices all limit discovery.
- The full historical 559-input-per-method embeddable soundness sweep was
  not rerun in Round 3. Targeted new-method controls, official mutations and
  the full local regression suite were run. Earlier batches were not rerun
  after later optional collision/SOS discovery additions; their source hashes
  document this. Search completeness is not claimed for any code version.
- Large FLINT cofactor expansions and native failures remain resource risks.
  Durable per-graph checkpoints support crash recovery, but no new native
  crash was intentionally induced in candidate production. The focused
  worker-exit regression covers its existing recovery path. Oversized raw
  historical experiments remain outside accepted record streams.
- The retained index 39 derivation was re-encoded and independently checked,
  not rediscovered from scratch in this round. The GP74 and B9p closure runs
  are sample checks, not full gate profiles. No minimality, embedding or
  all-B10 gate run was performed by this module.
"""
 path=MODULE/'REPORT.md';previous=path.read_text();head=previous.split('\n## Round 3\n')[0]
 path.write_text(head.rstrip()+'\n'+report)
 for p in MODULE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 invalid=[]
 for p in MODULE.rglob('*'):
  if p.is_file() and p.suffix in {'.py','.md','.json','.jsonl','.txt'}:
   with p.open() as f:
    for number,line in enumerate(f,1):
     if chr(0x2014) in line:invalid.append([str(p),number])
 assert not invalid,invalid
 bytecode=[str(p) for p in MODULE.rglob('*.pyc')];assert not bytecode,bytecode
 artifacts=[C/'UNKNOWN.g6',C/'UNPROCESSED.g6',C/'REFUTED.g6',C/'new-refuted.jsonl',C/'all-refuted.jsonl',C/'checker-final/records.jsonl',MODULE/'REPORT.md',R/'F39.null-dag.jsonl']
 inventory={'input_hashes_unchanged':unchanged,'b10_hash_matches_frozen':True,'python_files_parsed':len(list(MODULE.glob('*.py'))),'em_dash_lines':invalid,'bytecode':bytecode,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(MODULE.glob('*.py'))},'checker_sha256':final['combined_check']['checker_sha256'],'contract_sha256':hashlib.sha256((ROOT/'research/gp-10/CONTRACT.md').read_bytes()).hexdigest(),'artifacts':{str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts},'environment':{'nice':os.getpriority(os.PRIO_PROCESS,0),'RLIMIT_AS':resource.getrlimit(resource.RLIMIT_AS),'SYMPY_GROUND_TYPES':os.environ['SYMPY_GROUND_TYPES']}}
 (R/'round3-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
 (C/'README.md').write_text(f"# GP-10 Round 3 candidate results\n\n{status['new_refuted']} new checked refutations; {status['still_undecided']} unknown; zero unprocessed.\n\n- `new-refuted.jsonl`: new proofs only.\n- `all-refuted.jsonl`: {final['combined_check']['refuted']} accepted refutations including the external tree pass.\n- `UNKNOWN.g6`: exact undecided list at the recorded snapshot.\n- `UNPROCESSED.g6`: empty, all eligible candidates attempted.\n- `checker-final/`: combined official sample run with F9 in force.\n- `FINAL.json`: provenance, counts, times, snapshots and hashes.\n- `batch-*/`: source-bound discovery and independent checker evidence.\n\nExternal reported embeddings were excluded from scheduling, not verified here.\nThe complete report is `{MODULE/'REPORT.md'}`.\n")
 print(json.dumps({'report':str(path),'new_refuted':status['new_refuted'],'unknown':status['still_undecided'],'unprocessed':status['unprocessed'],'batch_count':final['batch_count'],'python_files_parsed':inventory['python_files_parsed'],'frozen_hashes_unchanged':True,'final_line':final['combined_check']['final_line']}),flush=True)
if __name__=='__main__':main()
