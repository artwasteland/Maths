"""Write ordinary checker manifests without asserting that controls passed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def write_manifests(run, input_path, limit, profile='sample', derive=False):
    run, input_path = Path(run).resolve(), Path(input_path).resolve()
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    frozen = Path(__file__).resolve().parents[1] / 'data' / 'B10.g6'
    is_b10 = digest == hashlib.sha256(frozen.read_bytes()).hexdigest()
    common = {'input': str(input_path), 'input_sha256': digest,
              'records': [str(run / 'records.jsonl')], 'unknown': str(run / 'UNKNOWN.g6')}
    if (run / 'hosts.jsonl').exists():
        common['hosts'] = str(run / 'hosts.jsonl')
    sample = {**common, 'profile': 'sample', 'forbidden_limit': limit,
              'derive': bool(derive or is_b10)}
    if profile == 'sample':
        primary = sample
    elif profile == 'B10':
        if not is_b10 or limit != 9:
            raise ValueError('B10 profile requires the frozen full B10 input and F9 in force')
        primary = {**common, 'profile': 'B10'}
        predictions = run / 'PREDICTIONS.md'
        if predictions.exists():
            primary['predictions'] = {'path': str(predictions),
                                      'sha256': hashlib.sha256(predictions.read_bytes()).hexdigest()}
        # This is an assembly, not a fabricated controls bundle. The official
        # B10 gate will reject until real accepted control directories exist.
    else:
        raise ValueError('assembly profiles are sample or B10')
    (run / 'run.json').write_text(json.dumps(primary, indent=2, sort_keys=True) + '\n')
    sample_dir = run / 'sample'
    sample_dir.mkdir(exist_ok=True)
    (sample_dir / 'run.json').write_text(json.dumps(sample, indent=2, sort_keys=True) + '\n')
    return sample_dir
