#!/usr/bin/env python3
"""Conservative shared-box check for the optional 120-second second pass."""
import json
import os
from pathlib import Path
import time
from msolve_exact import limits
from round2 import OUT, SAMPLES, task_id, solve_one, write_json


def cpu():
    values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    # Linux user/nice include guest times already, so do not add the guest columns.
    return sum(values[:8]), values[3] + values[4]


def quiet_snapshot():
    start_total, start_idle = cpu(); time.sleep(2)
    end_total, end_idle = cpu()
    idle = (end_idle - start_idle) / max(1, end_total - start_total)
    memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    load = os.getloadavg()
    return {'load_average': list(load), 'cpu_idle_fraction_2s': idle,
            'available_memory_kib': memory['MemAvailable'],
            'thresholds': {'maximum_load_1m': 2.0, 'minimum_idle_fraction': .5,
                           'minimum_available_memory_kib': 1572864},
            'quiet': load[0] <= 2.0 and idle >= .5 and memory['MemAvailable'] >= 1572864,
            'time_unix': time.time()}


def main():
    limits(); observations = []; attempts = []
    for sample in SAMPLES:
        codes = (OUT / sample / 'input.g6').read_text().splitlines()
        for code in codes:
            first = OUT / sample / 'pass1' / task_id(code) / 'stats.json'
            if not first.exists() or not json.loads(first.read_text()).get('timeout'): continue
            second = OUT / sample / 'pass2' / task_id(code) / 'record.json'
            if second.exists(): continue
            state = quiet_snapshot(); state.update(sample=sample, g6=code)
            observations.append(state)
            write_json(OUT / 'second-pass-decision.json', {'observations': observations,
                'new_attempts': attempts, 'stopped_when_busy': not state['quiet']})
            print(json.dumps({'quiet_check': state}), flush=True)
            if not state['quiet']: return
            record, stats = solve_one(code, sample, seconds=120, pass_number=2)
            attempts.append({'sample': sample, 'g6': code, 'verdict': record['verdict'], 'reason': stats['reason']})
            print(json.dumps(attempts[-1]), flush=True)
    write_json(OUT / 'second-pass-decision.json', {'observations': observations,
        'new_attempts': attempts, 'stopped_when_busy': False, 'all_pending_timeouts_considered': True})


if __name__ == '__main__': main()
