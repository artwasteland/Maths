#!/usr/bin/env python3
"""Build GP-11's publication gates file (FORMAT.md, "G6 writer and gate receipt") for the B11 final run.

Run on the VM, from any directory, with the frozen checker's Python. Every evidence path is relative to RUN and inside
it. Each gate's attestation is the coordinator's (claude-answering-alexeev-u22), on the evidence named; the 'statement'
fields are for human readers and are not read by the writer.
"""
import hashlib
import json
import sys
from pathlib import Path

RUN = Path.home() / 'gp11-data/b11-endgame/B11-final-1'
SRC = Path.home() / 'gp11-final-src'
sys.path.insert(0, str(SRC / 'research/gp-11/check'))
import gp11check as ck  # noqa: E402

report = json.loads((RUN / 'checked/report.json').read_text())


def ev(*rels):
    out = []
    for rel in rels:
        p = (RUN / rel).resolve()
        assert p.is_file() and p.is_relative_to(RUN.resolve()), rel
        out.append({'path': rel, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    return out


def under(d):
    return sorted(p.relative_to(RUN).as_posix() for p in (RUN / d).rglob('*') if p.is_file())


sources = ck.source_hashes()
assert report.get('profile_sources') == sources, 'report profile_sources differ from the checker source map'
gates = {
    'G0': {'status': 'PASS', 'input_sha256': report['input_sha256'],
           'statement': 'B11 frozen (448,708 graphs, sha256 ec9a7109...); its count agrees with geng over OEIS A002218(11) '
                        'and with two independent recounts (the G0 recount, and a third implementation in Arturo\'s 0020 read).',
           'evidence': ev(*under('gate-evidence/G0'))},
    'G1': {'status': 'PASS', 'sources': sources, 'selftest_committed': True,
           'statement': 'The B11 profile of the checker built; every red fixture rejected; the self-test, kernel self-test, '
                        'GP-10 regression and small controls committed (research/gp-11/check/results/).',
           'evidence': ev(*under('gate-evidence/G1'))},
    'G2': {'status': 'PASS', 'predictions_sha256': report['predictions']['sha256'], 'predictions_committed_before_run': True,
           'statement': 'Controls 5.1 to 5.4 pass (5.1: PASS B10 COMPLETE derived=324; the others in the control reports), '
                        'with PREDICTIONS.md committed before any frontier input (prediction-chronology.json).',
           'evidence': ev('PREDICTIONS.md', 'prediction-chronology.json', 'control51-final-status.json',
                          *under('gate-evidence/G2'))},
    'G3': {'status': 'PASS', 'report_sha256': hashlib.sha256((RUN / 'checked/report.json').read_bytes()).hexdigest(),
           'statement': 'Every B11 graph has a record; the final run ACCEPTs with counts.unknown == 0, conditional false and '
                        'no direct rejections, read from report.json (outcome VERIFIED_B11).',
           'evidence': ev('checked/report.json', 'execution/outcome.json')},
    'G4': {'status': 'PASS', 'L11_sha256': hashlib.sha256((RUN / 'checked/L11.g6').read_bytes()).hexdigest(),
           'statement': 'L11 derived by the checker: 2,833 minimal graphs. An independent audit derives the identical list '
                        '(same sha256); a blind second verifier accepts all 5,264 refutations; no second certificates claimed.',
           'evidence': ev('checked/L11.g6', 'checked/minimality.jsonl', *under('gate-evidence/G4'))},
    'G5': {'status': 'PASS', 'sources': sources, 'findings_answered': True,
           'outside_reviewer': 'Arturo (Kimi K3; waste-drop 0019 and 0020) and Cairn (OpenAI-assisted; the 0021 follow-up)',
           'statement': 'Independent reads of PROOFS.md\'s new parts and the checker\'s B11 changes; every finding answered '
                        'in writing (G5-RESPONSE.md); the follow-up approved.',
           'evidence': ev(*under('gate-evidence/G5'))},
}
out = RUN / 'gate-evidence/gates.json'
out.write_text(json.dumps(gates, indent=1, sort_keys=True) + '\n')
print('wrote', out, {g: len(v['evidence']) for g, v in gates.items()})
