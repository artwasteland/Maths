#!/usr/bin/env python3
"""Retry conversion of saved complete solver output without rerunning msolve."""
import argparse
import json
import time
from msolve_exact import limits, decode_output, certify
from round2 import OUT, write_json, load_system
from round2_phase import isolated


def main():
    limits()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', required=True)
    args = parser.parse_args()
    total = 0
    for directory in sorted((OUT / args.sample / 'pass1').iterdir()):
        if not (directory / 'record.json').exists(): continue
        record = json.loads((directory / 'record.json').read_text())
        stats = json.loads((directory / 'stats.json').read_text())
        if (record['verdict'] == 'embedded' or stats.get('returncode') != 0
                or stats.get('timeout') or stats.get('reconversion')
                or stats.get('solver_status') in ('positive_dimension', 'empty')): continue
        saved = directory / 'output.ms'
        if not saved.exists() or saved.stat().st_size > 32 * 1024 * 1024: continue
        system = load_system(directory / 'system.json'); code = record['g6']
        raw = saved.read_text(); started = time.monotonic(); candidate = None
        info = {}
        def convert():
            parsed = decode_output(raw, system['variables'],
                progress=lambda row: write_json(directory / 'conversion-progress.json', row))
            return certify(code, system, parsed)
        try: candidate, info = isolated(convert, 15)
        except Exception as exc: info['reason'] = type(exc).__name__ + ':' + str(exc)
        elapsed = time.monotonic() - started
        write_json(directory / 'stats-before-reconversion.json', stats)
        write_json(directory / 'record-before-reconversion.json', record)
        retry = {'wall_seconds': elapsed, 'previous_reason': stats['reason']}
        stats.update(info); stats['reconversion'] = retry; stats['wall_seconds'] += elapsed
        if (directory / 'conversion-progress.json').exists():
            progress = json.loads((directory / 'conversion-progress.json').read_text())
            stats.update({k: v for k, v in progress.items() if k not in stats})
        if candidate is not None:
            record = {'g6': code, 'verdict': 'embedded', 'cert': candidate}
        else:
            record['cert']['reason'] = stats['reason']
            record['cert']['budget']['wall_seconds'] = stats['wall_seconds']
            record['cert']['budget']['conversion_retry_seconds'] = elapsed
        write_json(directory / 'stats.json', stats); write_json(directory / 'record.json', record)
        total += 1
        print(json.dumps({'g6': code, 'verdict': record['verdict'], 'degree': stats.get('degree'),
                          'reason': stats['reason'], 'seconds': elapsed}), flush=True)
    print(json.dumps({'reconverted': total}), flush=True)


if __name__ == '__main__': main()
