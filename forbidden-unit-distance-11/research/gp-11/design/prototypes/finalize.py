from common import *
import json,hashlib,collections,gzip
m=json.loads((OUT/'MEASUREMENTS.json').read_text());sample=json.loads((OUT/'sample-manifest.json').read_text());check=json.loads((OUT/'sample-check-summary.json').read_text());pop=json.loads((OUT/'population-summary.json').read_text());poset=json.loads((OUT/'population-poset.json').read_text());prop=json.loads((OUT/'propagation-summary.json').read_text());tu=json.loads((OUT/'tu-summary.json').read_text());stream=json.loads((OUT/'stream-check-summary.json').read_text())
notes=['GP-11 measured design consultation. Repository untouched. All artifacts are in /tmp/gp11-architect/.',
'All numbers in this measurement section were measured here, except explicitly named projections. Detailed design and build jobs follow.',
'',
'REPRODUCIBILITY',
'Generated all 68232100 graphs with nauty-geng -Ckq 11 11:24. keep.c calls the existing udfilter.c with the pinned 398 JSON and six TU gadgets; only survivors are printed. This changes output plumbing, not matching. Ran nauty-labelg -q, then LC_ALL=C sort -u. Drew sorted(random.Random(20261001).sample(range(448708),500)) from that byte-sorted canonical list. Exact indices are in sample-manifest.json.',
'B11 sha256: '+sample['population_sha256'],'Sample sha256: '+sample['sample_sha256'],
'Enumeration: 363.707 seconds. Population: 448708; degree2=437793, min degree3=10915. Actual candidate edge counts range 11..23 (24 remains the proved enumeration cap).',
'Environment: '+json.dumps(pop['environment'],sort_keys=True),
'At most two compute processes concurrently, including CAS children; single-thread BLAS/CAS. Python/CAS address-space cap 1024000000 bytes; nice15. Memory monitored by MemAvailable with a 1572864 KiB floor. Lowest recorded available RAM among successful measurement stages: '+str(min(json.loads(p.read_text()).get('min_MemAvailable_kib',10**12) for p in OUT.glob('*-summary.json') if not p.name.startswith('debug-')))+' KiB. No floor stop occurred.',
'',
'METHOD RESULTS (overlap; conditional cohorts explicitly named; warm setup excluded)',
'Method | cohort | budget | accepted output | search seconds | individual checker seconds']
budgets={'lattice':'0.5s, 20000 nodes','lattice36':'0.5s, 20000 nodes','lattice30':'0.5s, 20000 nodes','host':'1s, 20000 match nodes','numeric':'2s total, three numerical starts','extension':'3s, all available degree2 deletions, both intersections','tree':'1s, 1200 states','tu':'C fixed-point closure','null':'3s, default frame/saturation','real':'3s, default frame/saturation','msolve':'20s nominal, two frames; n ceiling scratch port','portfolio':'10s, all nonedge saturation pairs, DAG auto'}
for name,row in m['stages'].items():notes.append(f"{name} | {row['attempted']} | {budgets[name]} | {row['counts']} | {row['search_seconds']:.3f} | {row['check_seconds']:.3f}")
notes += [
'Host/lattice36/lattice30 cohort: the94 lattice18 misses. Null/real/msolve cohort: the15 remaining after the union of initial stages. Portfolio cohort: the13 still unresolved after msolve. All other methods used all500. TU verifier time is included in the final combined replay, not its0.383-second C search time.',
'Numeric fit:488/500 reached residual<=1e-8,44 had minimum pair distance>=1e-3;2 exact certificates within budget. Distances below that threshold are search diagnostics, not proofs of collision.',
'Extension:445/500 exact certificates;476 graphs had an available B10 base in recorded metadata;6 degree2 graphs had no such lookup;1 timeout censored metadata. Full structural degree2 sample count483. GP10 source: cloud/lean3/records.jsonl.gz;3879 direct exact embeddings and28774 embedding pointers,32653 total. prepare.py indexes all records in gp10.sqlite; extension.py resolves/composes maps and converts arbitrary base generators before circle extension.',
'Order11 msolve: only the producer generic_rank ceiling was changed from10 to11 in a scratch module; scratch paths redirected. Other make_system/msolve_stage/invoke/certify routines and certificate checker were unchanged. The existing pinned msolve binary was accepted by its wrapper.',
'Complete certificate union: '+json.dumps(check['sample_counts'])+';2 old refutation dependencies replayed; sample-profile ACCEPT in13.373 seconds. The13 UNKNOWN records remain explicit. This is not B11 classification acceptance.',
'Checker sha256: '+check['checker_sha256'],'Kernel sha256: '+check['kernel_sha256'],
'Red checks: '+json.dumps(check['reds']),
'TU full-population search:3323 terminal-refutation proposals in349.172 seconds,3064 one-step,257 two-step,2 three-step. Only sample chains/dependencies were independently replayed.154192 original graphs have a TU hit;294516 have none. The remaining445385 search outcomes are not refutations.',
'Full compact poset:4721083 relations,24037 maxima,112 minima;16.724 seconds build. Relation pairs file:37768664 bytes; each CSR direction about25.4 MB including uint8 data and index arrays. The500 sampled parents have5279 relations, exactly matching independent GP10 Python one-edge deletion/canonicalization checks.',
'Closure from sample certificates: '+json.dumps({k:prop[k] for k in ('direct_E','direct_R','closure_E','closure_R','sample_unknown')})+'. These larger closures were structurally computed, not submitted as a full certificate run. No additional sampled unknown was decided by these sample-seed closures.',
'Fanout: '+json.dumps(m['propagation_fanout']),
'All-unknown full-B11 checker plumbing benchmark: '+json.dumps(stream),
'',
'PROJECTIONS (not measured full-run outcomes)',
'Uniform sample UNKNOWN13/500: point11666 over B11, nominal Wilson95%6846..19730. This refers to the bounded per-graph policy before full-population propagation/closure optimization and heavier analyst effort.',
'Ordered schedule inferred from separate per-graph timings:438.657 seconds/500;27.337 ideal four-core machine-hours. Runtime planning range40..100 machine-hours; with a120-second escalation on7000..20000 unresolved inputs, budget110..450 machine-hours. Neither extra time nor propagation is assigned an unmeasured success rate.',
'',
'SCRATCH PROTOTYPE NOTES',
'The first TU wrapper iteration incorrectly used raw gadget pair labels; it aborted before any claimed result. It was corrected to witness.map[pair_a], witness.map[pair_b]. Final measured TU certificates pass independent sample checking, including a deliberate wrong-pair red fixture.',
'The extension harness first encountered an embed/refute round2 import collision, then a GP script invocation formatting error (retained as debug-unexecuted-*), then non-monic base-field generator mismatch (retained as debug-basefield-*). These are excluded from reported method timings. The corrected final prototype used proper field conversion and all reported successes passed the frozen verifier. Scratch prototypes are evidence and starting points, not hardened production replacements.',
'Files: AUDIT.txt (source audit), BUILD-JOBS.txt (inputs/outputs/tests/red rules), PLAN.txt (six-day schedule and risks), MEASUREMENTS.json (machine-readable calculations), sample-check/checked/report.json (independent checker output), *-records.jsonl and *-stats.jsonl (per-graph evidence). source-files.txt and extended-source-index.txt locate historical order/profile assumptions.',
'']
report='\n'.join(notes)+'\n\n'+(OUT/'PLAN.txt').read_text()+'\n\n'+(OUT/'AUDIT.txt').read_text()+'\n\n'+(OUT/'BUILD-JOBS.txt').read_text();(OUT/'REPORT.txt').write_text(report)
manifest={}
for p in list(OUT.glob('*.py'))+list(OUT.glob('*.c'))+[OUT/'B11.g6',OUT/'sample.g6',GP/'check/gp10check.py',ROOT/'research/unit-distance-22/check/udcheck.py',GP/'cloud/lean3/records.jsonl.gz']:
 manifest[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'ARTIFACT-HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'report':str(OUT/'REPORT.txt'),'bytes':len(report.encode()),'sample_counts':check['sample_counts'],'minimum_available_kib':min(json.loads(p.read_text()).get('min_MemAvailable_kib',10**12) for p in OUT.glob('*-summary.json') if not p.name.startswith('debug-'))}))
