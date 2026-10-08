"""Render REPORT.md from measured records and their command provenance."""
import json
from collections import Counter
from pathlib import Path
from measure import HERE,RESULTS,SAMPLES,stages,read_records

def read(p):return json.loads(p.read_text())
def command(meta):
    sample,method,label=meta['sample'],meta['method'],meta['label']
    if label=='host_g118_subset':return 'host-subset-pass'
    if method=='lattice18':return 'named-lattice' if sample=='named' else ('max-lattice' if sample=='maximal' else 'baseline')
    if method in ('lattice36','lattice30'):return 'wide'
    if method=='constructive':return 'named-construct' if sample=='named' else 'circles'
    if method=='host':return 'host-pass'
    return 'numeric'

def main():
    audit=read(RESULTS/'audit.json');final=read(RESULTS/'final-audit.json');tests=read(HERE/'selftest-results.json')
    lines=['# GP-10 embedder report','',
      'The producer and all requested development artifacts are present. Accepted records contain ordinary E-exact coordinates, checked locally before emission. The blind checker has not been run, and the global pipeline gates remain open. The unresolved inputs are retained explicitly.','',
      'Entry point: [gp10embed.py](gp10embed.py). Usage and resume behaviour: [README.md](README.md). Exact commands: [COMMANDS.md](COMMANDS.md). Raw records, per-method statistics and audits: [results/](results/). The cross-sample union is [union-records.jsonl](results/union-records.jsonl), with [UNKNOWN.g6](UNKNOWN.g6) containing exactly those measured graph codes that no measured method embedded. Each input set also has its own records and UNKNOWN.g6.','',
      '## Scope and coverage','',
      'Counts below come from `measure.py prepare`, the method commands linked in the next table, and [the audit command](COMMANDS.md#audit). The maximal file and the prescribed random sample were used in full for the first lattice pass. Every line of B9p was exercised. Later circle and numeric stages used deterministic samples of unresolved inputs. This is a development measurement, with no full B10 classification claim.','',
      '| Input | Graphs | Embedded | Unknown | Unknown rate |','|---|---:|---:|---:|---:|']
    for sample in SAMPLES:
        s=audit['samples'][sample]
        lines.append(f"| {sample} | {s['input']} | {s['embedded']} | {s['unknown']} | {100*s['unknown']/s['input']:.2f}% |")
    b9=audit['samples']['B9p']['classes']
    for name,c in b9.items():
        u=c['total']-c['embedded'];lines.append(f"| B9p: {name} | {c['total']} | {c['embedded']} | {u} | {100*u/c['total']:.2f}% |")
    lines.extend(['',f"The deduplicated measured union contains {audit['union_input']} graph codes: {audit['union_embedded']} embedded and {audit['union_unknown']} unknown. Its unknown rate is {100*audit['union_unknown']/audit['union_input']:.2f}%. Success in another overlapping sample can settle a graph that remains unknown in an individual sample's historical results.", '',
      '## Coverage and time by method','',
      'These are incremental hits on inputs still unresolved at that stage, not independent success rates on the whole set. `Attempted` is the denominator. A sample cap is shown where only a deterministic subset was exercised. Wall time includes workers and output writes; import and host-loading time is recorded separately in each meta file. The graph limit is a watchdog deadline, with process cleanup included in reported wall time. Unknown rates above use the exact combination of budgets below.','',
      '| Input | Stage | Attempted | New embedded | Unknown | Wall s | Limit s/graph | Node cap | Sample cap | Command |',
      '|---|---|---:|---:|---:|---:|---:|---:|---:|---|'])
    for sample in SAMPLES:
        for p in stages(sample):
            m=read(p);c=m['counts'];cmd=command(m)
            lines.append(f"| {sample} | {m['label']} | {m['attempted']} | {c.get('embedded',0)} | {c.get('unknown',0)} | {m['seconds']:.3f} | {m['time_limit']:g} | {m['node_cap']} | {m['sample_cap'] or 'all remaining'} | [{cmd}](COMMANDS.md#{cmd}) |")
    lines.extend(['','`host_g118_subset` repeats the host stage after the new G118 subhost was compiled. Its hits are attributed to their actual source in the saved statistics. The host matcher node cap is the displayed base cap multiplied by the factor in the implementation. All graph time limits still apply.','',
      '## Methods and exact acceptance','',
      '- The lattice DFS stores integer coefficients in a fixed real algebraic basis. It uses the spindle rotation, wider roots of unity, and a rational Pythagorean rotation. Each new point is reached from a placed neighbour by a chosen direction; other incident edges are checked exactly. Trying every placed neighbour fixed the initial spindle miss. Closing-edge directions are allowed outside the finite proposal set.',
      '- Constructive placement peels low-degree vertices, embeds the remaining core, then uses exact unit-circle intersections and rational free directions. A structural search for two regular polygon layers derives unit spokes algebraically and supplies the Petersen control. It contains no named graph-code or coordinate lookup.',
      '- Host search uses an injective, non-induced bitset matcher. Numeric host adjacency only proposes maps. Selected coordinates are flattened and verified as ordinary E-exact certificates against the input graph. Library hits are separate from general search.',
      '- Numeric search uses seeded least squares with a coincidence penalty, then rational free directions and exact circle reconstruction. Every reconstructed candidate must pass the same exact check. No msolve, Singular, z3 or integer-relation wrapper was used.',
      '- The local verifier checks the strict rational endpoint sign change, reduces every required squared edge distance exactly modulo the supplied polynomial, and proves all pair distances positive using rational interval arithmetic. Interval refinement retains a strict sign change. It does not assume irreducibility or use float separation to accept.',
      '- Search seeds are SHA256 of graph6. Coordinate order is the input graph6 order. One worker is alive at a time. The parent turns timeouts and abrupt worker exits into unknown records, flushes records, and resumes by streaming and rechecking prior exact records. Existing unknown records are skipped on resume too.','',
      '## Host preparation','',
      'Preparation commands: [hosts](COMMANDS.md#hosts) and [subset](COMMANDS.md#subset). The full G118 edge count below is numeric proposal adjacency; its entire coordinate field was not certified.','',
      '| Host | Vertices | Proposed edges | Exact degree | Status | Wall s | Limit s |',
      '|---|---:|---:|---:|---|---:|---:|'])
    for h in read(HERE/'host-preparation.json'):
        lines.append(f"| {h['host']} | {h['vertices']} | {h['edges']} | {h.get('degree','')} | {h['status']} | {h['seconds']:.3f} | {h['limit_seconds']} |")
    h=read(HERE/'g118-subset-preparation.json')
    lines.append(f"| G118 simple subset | {h['vertices']} | {h['edges']} | {h['degree']} | {h['status']} | {h['seconds']:.3f} | {h['limit_seconds']} |")
    lines.extend(['',f"The subset's one-coordinate mutation failed with `{h['mutation_reason']}`. The audit counted these library hits across the per-sample method records, including repeated graph codes across samples: "+', '.join(f"{k}: {v}" for k,v in sorted(final['host_hits_by_source'].items()))+'.','',
      '## Named controls and regressions','',
      'The named positive records were obtained through general search before the host pass. The embedder cannot produce the refutations required by the whole pipeline. Its negative controls therefore remain unknown.','',
      '| Graph | Canonical graph6 | Verdict | First successful general method |','|---|---|---|---|'])
    names=read(RESULTS/'named'/'names.json');verdicts=audit['samples']['named']['named'];winning={}
    for p in stages('named'):
        m=read(p)
        if m['method']=='host':continue
        for r in read_records(p.with_name(m['label']+'.records.jsonl')):
            if r['verdict']=='embedded':winning.setdefault(r['g6'],m['method'])
    for name,c in names.items():lines.append(f"| {name} | ``{c}`` | {verdicts[name]} | {winning.get(c,'')} |")
    lines.extend(['','The Golomb input code was taken from the existing scratch brief cited by this job, then canonicalised. Named graphs, including the extremal input, are searched in the canonical labelling. No AMP or GP coordinate lookup contributed to these successful controls.','',
      '## Validation and numeric refusal','',
      f"[selftest.py](selftest.py) passed {tests['passed']} controls. [selftest-results.json](selftest-results.json) gives the actual positive and rejection results. The [controls command](COMMANDS.md#controls) exercises coordinate, sign-change, coincident-point, reducible-polynomial and nonreal-field mutations; host-map injectivity and edge preservation; deterministic certificates; worker exceptions, hard exits and hard timeouts; continuation after a crash; and resume repair.", '',
      'The deliberately permissive numeric diagnostic disables the repulsion term to exhibit the residual-only failure mode. It solves the edge equations for K2,3 near collapsed circle intersections. This is a diagnostic mode of the same fitting routine, not a claim that the production penalised solve accepted that configuration.'])
    diagnostic=next(c for c in tests['checks'] if c['control']=='numeric convergence does not certify')
    lines.append(f"Its maximum squared-edge residual was {diagnostic['numeric']['residual']:g}, while the minimum numeric point separation was {diagnostic['numeric']['minimum_distance']:g}. The exact collapsed candidate failed with `{diagnostic['exact_refusal']}`. A genuine exact positive and a single-coordinate coincidence mutation separately exercise that rejection branch.")
    cases=final['numeric_converged_and_refused']
    if cases:
        lines.append('The production sample also recorded converged candidates that were not certified. These diagnostics are in final-audit.json; exact refusal is not a proof of non-embeddability.')
        for c in cases[:3]:lines.append(f"- `{c['g6']}` ({c['sample']}): residual {c['residual']:.6g}, `{c['reason']}`.")
    else:lines.append('No production sample retained both a residual at most 1e-12 and a completed exact-refusal result. Watchdog interruptions can omit these diagnostics. The explicit diagnostic above supplies the required example.')
    lines.extend(['','[final-audit.json](results/final-audit.json) verifies every saved stage certificate, input/certificate label agreement, primary coverage and unknown projections, canonical input codes, negative controls, valid finite JSON numbers, and source syntax. These are local checks, not the blind checker.','',
      '## Environment and procedural notes',''])
    e=final['environment']
    lines.append('Measured by the [audit command](COMMANDS.md#audit): '+', '.join(f'`{k}={v}`' for k,v in e.items())+'.')
    lines.extend(['','All work products are inside this module or the permitted scratch directory. No git commands, package installs, npm, oversight execution, or edits to the earlier unit-distance module were used. The common brief gives a looser memory ceiling than the contract; the stricter contract ceiling was used. The initial read-only COMMON.md bootstrap used `nice -n 10` without an explicit ulimit before its detailed rules were known. All later shell commands used `nice -n 15` and `ulimit -v 1000000`; this bootstrap is the procedural exception.','',
      'The shared PROOFS.md and PREDICTIONS.md were absent. The module [PREDICTIONS.md](PREDICTIONS.md) records predictions before coverage measurements. [LABNOTES.md](LABNOTES.md) explains the initial named-control misses and the incomplete B9 control coverage. No shared proof file, global gate, independent checker acceptance or commit is claimed.','',
      '## UNCERTAIN','',
      '- The official blind checker was not available in this module run. Local arithmetic, mutations and audits do not substitute for that gate.',
      '- The unresolved F9-free B9 graphs show that search coverage is incomplete. The numeric and circle methods were sampled on unresolved graphs, and wider lattice searches often reached their time limits. Unknown never means forbidden.',
      '- Full G118 flattening timed out. The certified subhost is usable; difficult matches in the full host still require per-map conversion and can time out or exceed the field-degree cap. The matcher tries one map per host, so a difficult first map can hide an easier alternative.',
      '- Search decisions are deterministic from each graph code, but wall-time cutoffs and recorded durations vary with scheduling. Literal record equality is therefore expected for completed successful searches, not for elapsed-time fields or borderline timeouts.',
      '- Actual operating-system OOM killing and a native-library segmentation fault were not injected. Abrupt worker exit, Python exceptions and an uncooperative timeout were exercised. Parent I/O failure and concurrent writers are outside the tested recovery case.',
      '- The likeliest implementation errors are in algebraic field conversion, source-coordinate parsing and labelling at graph/coordinate boundaries. Exact checks protect each emitted result, but a shared arithmetic or parser mistake still needs an independent checker. Golomb identity was inherited from the supplied scratch definition, rather than independently looked up.',
      '- The union covers only the measured input sets. No completeness claim for B10, minimal forbidden list, or full control-pipeline PASS follows from this report.',''])
    report='\n'.join(lines)
    assert chr(0x2014) not in report
    (HERE/'REPORT.md').write_text(report)
    print(json.dumps({'report':'research/gp-10/embed/REPORT.md','union':{k:v for k,v in audit.items() if k!='samples'},'tests':tests['passed']},indent=2))
if __name__=='__main__':main()
