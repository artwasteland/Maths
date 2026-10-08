#!/usr/bin/env python3
"""Audit complete round-two artifacts and write the measured report appendix."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from fractions import Fraction
from msolve_exact import limits, sha
from round2 import OUT, HERE, RESULTS, SAMPLES, task_id, write_json
from exact import graph6


def main():
    limits()
    summary = json.loads((OUT / 'summary.json').read_text())
    checker = json.loads((OUT / 'run/out/report.json').read_text())
    final_line = (OUT / 'run/checker.log').read_text().splitlines()[-1]
    assert checker['status'] == 'ACCEPT' and final_line == 'ACCEPT run verified'
    records = [json.loads(line) for line in (OUT / 'union-records.jsonl').read_text().splitlines()]
    by_code = {r['g6']: r for r in records}
    assert len(by_code) == len(records) == summary['union']['records']
    assert all(set(r) == {'g6', 'verdict', 'cert'} for r in records)
    assert not any(r['verdict'] == 'refuted' for r in records)
    counts = dict(Counter(r['verdict'] for r in records))
    assert counts.get('embedded', 0) == summary['union']['embedded']
    assert counts.get('unknown', 0) == summary['union']['unknown']
    assert checker['counts']['embedded'] == counts['embedded']
    assert checker['counts']['unknown'] == counts['unknown']
    expected_input = ''.join(c + '\n' for c in sorted(by_code))
    expected_unknown = ''.join(c + '\n' for c in sorted(by_code) if by_code[c]['verdict'] == 'unknown')
    assert (OUT / 'run/input.g6').read_text() == expected_input
    assert (OUT / 'UNKNOWN.g6').read_text() == expected_unknown
    assert (OUT / 'run/UNKNOWN.g6').read_text() == expected_unknown
    manifest = json.loads((OUT / 'run/run.json').read_text())
    assert manifest['input_sha256'] == sha(expected_input.encode())
    assert checker['input_sha256'] == manifest['input_sha256']
    assert any(Path(row['path']).resolve() == (OUT / 'union-records.jsonl').resolve()
               and row['sha256'] == sha((OUT / 'union-records.jsonl').read_bytes()) for row in checker['files'])
    assert checker['checker_sha256'] == sha((HERE.parent / 'check/gp10check.py').read_bytes())
    assert summary['union']['union_sha256'] == sha((OUT / 'union-records.jsonl').read_bytes())
    stats = [json.loads(line) for line in (OUT / 'stats.jsonl').read_text().splitlines()]
    first_stats = [s for s in stats if s['pass'] == 1]
    assert len(first_stats) == 1337
    assert {s: summary[s]['requested'] for s in SAMPLES} == {'maximal': 1202, 'B9p': 88, 'uniform500': 47}
    assert summary['union']['round2_unique_inputs'] == 1314
    for row in stats:
        assert row['cap_seconds'] == (20 if row['pass'] == 1 else 120)
        if row['pass'] == 2:
            prior = next(s for s in first_stats if s['sample'] == row['sample'] and s['g6'] == row['g6'])
            assert prior.get('timeout')
        directory = OUT / row['sample'] / ('pass' + str(row['pass'])) / task_id(row['g6'])
        for filename, key in [('input.ms', 'input_sha256'), ('output.ms', 'output_sha256')]:
            if key in row: assert sha((directory / filename).read_bytes()) == row[key]
    for sample in SAMPLES:
        assert summary[sample]['attempted'] == summary[sample]['requested']
        codes = (OUT / sample / 'input.g6').read_text().splitlines()
        rows = [json.loads(line) for line in (OUT / sample / 'records.jsonl').read_text().splitlines()]
        assert [r['g6'] for r in rows] == codes
        assert len(codes) == len(set(codes))
        for code in codes:
            directory = OUT / sample / 'pass1' / task_id(code)
            assert (directory / 'record.json').exists() and (directory / 'stats.json').exists()
            if (directory / 'system.json').exists():
                system = json.loads((directory / 'system.json').read_text())
                _, edges = graph6(code)
                assert tuple(system['frame']) in edges
                assert len(system['pins']) == system['k']
                assert '(' not in system['text'] and ')' not in system['text']
                assert len(system['text'].encode()) < 1048576
                for pin in system['pins']:
                    assert Fraction(pin['cos'])**2 + Fraction(pin['sin'])**2 == 1
    triage = (OUT / 'rigid-no-embedding.g6').read_text().splitlines()
    assert triage == sorted(set(triage)) and len(triage) == summary['union']['rigid_triage']
    triage_rows = [json.loads(line) for line in (OUT / 'rigid-no-embedding.jsonl').read_text().splitlines()]
    assert [r['g6'] for r in triage_rows] == triage
    for row in triage_rows:
        assert row['triage'] and row['k'] == 0 and row['pins'] == []
        assert not row['timeout'] and row['returncode'] == 0
        assert by_code[row['g6']]['verdict'] == 'unknown'
    for number in (1, 2):
        expected = sorted({s['g6'] for s in stats if s['pass'] == number and s.get('timeout')})
        assert (OUT / f'timeouts-pass{number}.g6').read_text().splitlines() == expected
    tests = json.loads((OUT / 'selftest-results.json').read_text())
    assert all(t['status'] == 'PASS' for t in tests['checks'])
    controls = json.loads((OUT / 'official-control-results.json').read_text())
    assert [r['status'] for r in controls] == ['ACCEPT', 'ACCEPT', 'REJECT']
    assert 'edge_equation' in (OUT / 'controls/official-red/out/records.jsonl').read_text()
    second = json.loads((OUT / 'second-pass-decision.json').read_text())
    second_stats = [s for s in stats if s['pass'] == 2]
    assert len(second_stats) == len(second['new_attempts'])
    assert sum(o['quiet'] for o in second['observations']) == len(second_stats)
    pending_timeouts = sum(s.get('timeout', False) for s in first_stats) - len(second_stats)
    degrees = Counter(s['degree'] for s in stats if 'degree' in s)
    cert_degrees = Counter()
    new_codes = (OUT / 'new-embedded.g6').read_text().splitlines()
    for code in new_codes: cert_degrees[len(by_code[code]['cert']['field']['minpoly'])-1] += 1
    reasons = Counter(s['reason'].split('{', 1)[0] for s in stats)
    rejected_param = [s for s in stats if 'parametrization:' in s['reason'] or 'parse:' in s['reason']]
    positive_dim_rigid = sum(s.get('k') == 0 and s.get('reason') == 'msolve_positive_dimension' for s in stats)
    source_names = ['msolve_exact.py', 'rigid_system.py', 'msolve_seed.c', 'round2.py', 'round2_phase.py',
                    'round2_selftest.py', 'round2_reconvert.py', 'round2_quiet.py', 'official_check.py',
                    'round2_finish.py', 'exact.py', 'numeric.py']
    audit = {'status': 'PASS', 'complete_input_memberships': len(first_stats),
        'unique_round2_inputs': summary['union']['round2_unique_inputs'], 'union_counts': counts,
        'new_unique_embeddings': len(new_codes), 'triage_count': len(triage),
        'certificate_degree_distribution_new_unique': dict(sorted(cert_degrees.items())),
        'eliminant_degree_distribution_attempts': dict(sorted(degrees.items())),
        'reason_categories': dict(reasons), 'positive_dimensional_unpinned_attempts': positive_dim_rigid,
        'rejected_parametrizations': [{'g6': s['g6'], 'sample': s['sample'], 'reason': s['reason']} for s in rejected_param],
        'official_checker_final_line': final_line,
        'second_pass_attempts': len(second_stats), 'pending_timeout_memberships': pending_timeouts,
        'code_sha256': {name: sha((HERE / name).read_bytes()) for name in source_names},
        'official_checker_sha256': sha((HERE.parent / 'check/gp10check.py').read_bytes()),
        'union_sha256': sha((OUT / 'union-records.jsonl').read_bytes()),
        'maximum_record_bytes': max(len(json.dumps(r).encode()) for r in records)}
    assert audit['maximum_record_bytes'] < 8 * 1024 * 1024
    write_json(OUT / 'final-audit.json', audit)
    report = (HERE / 'REPORT.md').read_text()
    if '\n## Round 2\n' in report: report = report.split('\n## Round 2\n', 1)[0]
    if '\n## UNCERTAIN\n' in report:
        report = report.replace('\n## UNCERTAIN\n', '\n## Round 1 limitations (historical)\n\nThe following limitations describe the round-one run. Round-two results follow.\n', 1)
    lines = ['\n## Round 2\n',
        f'Processed all {len(first_stats):,} requested input memberships ({summary["union"]["round2_unique_inputs"]:,} distinct graphs), in the requested cohort order. '
        f'The new union has {summary["union"]["embedded"]:,} embedded records and {summary["union"]["unknown"]:,} unknown records, '
        f'with {len(new_codes):,} new unique embeddings. No refuted record is emitted.\n',
        'The official checker accepted the merged sample run. Its exact final line is:\n\n```text\n' + final_line + '\n```\n',
        'Measured coverage on the round-one unknown lists follows. Embedded and unknown are this producer\'s per-cohort outcomes; overlaps are deduplicated in the union.\n',
        '| Cohort | Inputs processed | Embedded | Unknown | msolve calls | First-pass timeouts | Rigid triage |\n|---|---:|---:|---:|---:|---:|---:|']
    for sample in SAMPLES:
        row = summary[sample]
        lines.append(f'| {sample} | {row["attempted"]} | {row["embedded"]} | {row["unknown"]} | {row["msolve_calls"]} | {row["first_timeouts"]} | {row["rigid_triage"]} |')
    lines += ['\nEvery input has a record. A failed numerical preparation is unknown without an msolve call. '
              'The stated cohorts are the requested research samples; no additional full-B10 solve was run. '
              'Long work was divided into recorded index batches.\n',
        f'The triage file has {len(triage)} unique graphs, all unpinned with k=0 and all still unknown. '
        'It is a lead for the refuter, not a refutation certificate. The audit found no triage/embedding conflict.\n',
        '| Cohort | Pinned msolve calls | Pinned embeddings | Sum of graph wall time (s) | msolve time (s) |\n|---|---:|---:|---:|---:|']
    for sample in SAMPLES:
        row = summary[sample]
        lines.append(f'| {sample} | {row["pinned_calls"]} | {row["pinned_successes"]} | {row["wall_seconds_sum"]:.3f} | {row["msolve_seconds_sum"]:.3f} |')
    lines += [f'\nThe sums include saved-output conversion retries and any second-pass attempts. They exclude development, imports before batch timing, and preliminary experiments. '
              f'The final official checker took {checker["elapsed_seconds"]:.3f} s.\n']
    second_attempts = sum(summary[s]['second_attempted'] for s in SAMPLES)
    lines += [f'The first msolve cap was 20 s per graph; preparation and conversion had separate hard caps of 8 s and 15 s. '
              f'There were {second_attempts} attempts at the conditional second-pass cap of 120 s. '
              f'These recovered {sum(s.get("reason") == "exact_embedding" for s in second_stats)} embeddings; '
              f'{sum(s.get("timeout", False) for s in second_stats)} retried entries reached the longer cap. '
              f'{pending_timeouts} first-pass timeout memberships were not retried.\n']
    if second.get('stopped_when_busy'):
        observation = second['observations'][-1]
        lines += [f'The second pass stopped before the next pending timeout because the shared-box check was not quiet: '
                  f'one-minute load {observation["load_average"][0]:.3f}, CPU idle fraction {observation["cpu_idle_fraction_2s"]:.3f}, '
                  f'available memory {observation["available_memory_kib"]:,} KiB. '
                  'The previously recorded thresholds were load at most 2.0, idle fraction at least 0.5, and available memory at least 1,572,864 KiB. '
                  'The observations and any attempted retries are in `second-pass-decision.json`.\n']
    else:
        lines += ['The saved shared-box observations permitted every performed second-pass attempt. All pending timeout entries were considered.\n']
    lines += ['Completed-output eliminant degrees, including rejected parametrizations, are counted per solver attempt:\n',
              '| Eliminant degree | Outputs |\n|---:|---:|']
    for degree, count in sorted(degrees.items()): lines.append(f'| {degree} | {count} |')
    lines += ['\nNew unique certificates use these irreducible-factor degrees: ' + ', '.join(f'{d}: {n}' for d, n in sorted(cert_degrees.items())) + '.\n',
        'The primitive element remains the printed separating variable. Factoring its eliminant permits smaller exact certificates. '
        'The parser handles reordered coordinate boxes, an added separator, rational coordinate denominators, exact rational roots, and ideal multiplicities. '
        'It inverts denominators modulo each factor and checks input equations before the local E-exact checks.\n',
        f'{positive_dim_rigid} unpinned k=0 attempts returned a positive-dimensional complex solution set. '
        'Thus generic rigidity did not guarantee a finite unit-length system. Such outputs never entered triage. '
        'No distinctness saturation or component decomposition was added.\n',
        f'The final local suite passed {tests["passed"]} controls in {tests["wall_seconds"]:.3f} s. '
        'It includes a triangle, a rationally pinned unit rhombus, repeated-root multiplicity, reordered variables, reproducible added separators, '
        'coincident points with exact edge lengths, one-coordinate and one-interval mutations, malformed output, and native child exit/timeout handling. '
        'The independent pilot checker accepted its saved new certificates and rejected a one-coordinate mutation with `edge_equation`.\n',
        'The stock msolve CLI segfaulted under the contract memory cap because it allocated a 1 GiB header buffer. '
        'The scratch copy changes five guarded input-buffer immediates to 1 MiB. Input size is checked against that bound. '
        'Solver arithmetic and the installed binary are unchanged. A small srand interposer seeds random separators from the graph hash. '
        'Exact offsets, binary hashes, inputs, outputs and logs are retained.\n',
        'The checker hardcodes `/tmp/gp10-check`, outside the allowed write paths. '
        '`official_check.py` redirects only its scratch globals and environment to `/tmp/gp10-embed/official-check`, '
        'then invokes the unchanged checker\'s main. This is the necessary deviation from the brief\'s literal checker command. '
        'The checker source hash is recorded and checked for stability.\n',
        'Commands supplying these measurements are `round2.py batch` with the bounds recorded in `results/round2/batches/`, '
        '`round2_reconvert.py --sample maximal`, `round2_quiet.py`, `round2.py collect`, `round2_selftest.py`, '
        '`official_check.py results/round2/run --output results/round2/run/out` (with module-prefixed paths), and `round2_finish.py`. '
        'Every Python command was launched with the frozen interpreter, `-B`, niceness 15 and the address-space cap shown in [COMMANDS.md](COMMANDS.md). '
        'The official checker further increased its own niceness to 19, as recorded in its report.\n',
        'Deliverables: [summary](results/round2/summary.json), [new union](results/round2/union-records.jsonl), '
        '[unknowns](results/round2/UNKNOWN.g6), [rigid triage](results/round2/rigid-no-embedding.g6), '
        '[triage summaries](results/round2/rigid-no-embedding.jsonl), [first-pass timeouts](results/round2/timeouts-pass1.g6), '
        '[second-pass timeouts](results/round2/timeouts-pass2.g6), [checker log](results/round2/run/checker.log), '
        '[checker report](results/round2/run/out/report.json), [audit](results/round2/final-audit.json), '
        'and [usage and design](ROUND2.md).\n',
        '## UNCERTAIN\n',
        '- Rational direction pins are proposals near a numerical solution. No certified implicit-function neighborhood or persistence radius was constructed. '
        'Successful pins have exact embeddings; a failed pinned system cannot exclude another embedding.\n',
        '- Generic rank is bounded and checked exactly, but special unit-length components can still be positive-dimensional. '
        'The current solver does not saturate coincidences or decompose those components.\n',
        f'- {len(rejected_param)} completed solver outputs were rejected by parametrization/schema checks. '
        'Details are in `final-audit.json` and the original outputs are retained. '
        'Three fail the printed separator relation under the current interpretation; one fails original input equations on some factors. '
        'Diagnostic factor checks found valid original equations throughout the three separator failures, but did not resolve the separator mismatch. '
        'The msolve output parser, especially unusual nonradical cases, remains the most likely integration failure point.\n',
        '- Triage relies on the completeness of msolve\'s result and is not independently certified as a refutation. '
        'The official sample checker validates the embedded records and accepts unknown records as unknown.\n',
        '- The memory workaround is specific to the guarded installed binary. A different msolve build requires a reviewed replacement. '
        'Actual large-solver OOM was not deliberately forced; child exit and hard timeout were exercised, as was the stock CLI allocation crash.\n',
        '- This run does not close the classification gates. Remaining unknowns, full small-order pipeline controls, and refutation/minimality work remain outside this embedder result.\n']
    report = report.rstrip() + '\n' + '\n'.join(lines)
    assert '\u2014' not in report
    (HERE / 'REPORT.md').write_text(report)
    for name in source_names + ['REPORT.md', 'ROUND2.md', 'COMMANDS.md', 'LABNOTES.md']:
        assert '\u2014' not in (HERE / name).read_text(), name
    print(json.dumps(audit, indent=2))


if __name__ == '__main__': main()
