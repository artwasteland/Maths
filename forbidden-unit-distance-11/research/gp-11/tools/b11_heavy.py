#!/usr/bin/env python3
"""Shared desktop arithmetic lane. The coordinator binds the same lock in every workspace."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    command = sys.argv[1:]
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        raise SystemExit('b11_heavy.py -- COMMAND ...')
    root = Path.cwd()
    with (root / 'HEAVY.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # The guard also inherits the locked descriptor, retaining the lane if
        # this wrapper exits first. The namespace owns descendant cleanup.
        os.set_inheritable(lock.fileno(), True)
        raise SystemExit(subprocess.call([sys.executable, '-B', str(root / 'research/gp-11/tools/guard.py'), '--', *command],
                                         close_fds=False))
