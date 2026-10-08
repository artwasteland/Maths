#!/usr/bin/env python3
"""Run one child at a time, stopping below the shared-machine memory floor."""

import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


SCRATCH = Path('/tmp/gp11-freeze')
MEMORY_FLOOR_KIB = 1572864
SCRATCH_LIMIT = 10_000_000_000


def available_kib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])
    raise RuntimeError('MemAvailable is unavailable')


def scratch_bytes():
    return sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file())


def child_limits():
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (1_500_000_000, 1_500_000_000))


def run(command, *, stdin=None, stdout=None, stderr=None, env=None):
    minimum = available_kib()
    if minimum < MEMORY_FLOOR_KIB:
        raise RuntimeError(f'STOP: MemAvailable={minimum} KiB below {MEMORY_FLOOR_KIB}')
    peak_scratch = scratch_bytes()
    if peak_scratch >= SCRATCH_LIMIT:
        raise RuntimeError('STOP: scratch reached 10 GB')
    start = time.monotonic()
    process = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr,
                               env=env, start_new_session=True, preexec_fn=child_limits)
    try:
        while True:
            minimum = min(minimum, available_kib())
            peak_scratch = max(peak_scratch, scratch_bytes())
            if minimum < MEMORY_FLOOR_KIB:
                raise RuntimeError(f'STOP: MemAvailable={minimum} KiB below {MEMORY_FLOOR_KIB}')
            if peak_scratch >= SCRATCH_LIMIT:
                raise RuntimeError('STOP: scratch reached 10 GB')
            try:
                code = process.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                pass
        if code:
            raise RuntimeError(f'child exited {code}: {command}')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    return {'command': [str(x) for x in command],
            'wall_seconds': round(time.monotonic() - start, 6),
            'min_MemAvailable_kib': minimum,
            'peak_scratch_bytes': peak_scratch,
            'exit_code': code}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--stdout', type=Path, required=True)
    parser.add_argument('--stderr', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    with args.stdout.open('wb') as output, args.stderr.open('wb') as errors:
        receipt = run(command, stdout=output, stderr=errors)
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
