#!/usr/bin/env python3
"""Run one command, single-threaded, nice 15, <=1 GB; stop below 1.5 GiB available.

Operational harness only. It grants no checker verdict. Use: guard.py -- COMMAND ...
"""
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


def available():  # B11 harness addition.
    return int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                    if line.startswith("MemAvailable:")))


def limits():  # B11 harness addition.
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (1024000000, 1024000000))


def main():  # B11 harness addition.
    command = sys.argv[1:]
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise SystemExit("guard.py -- COMMAND ...")
    floor = 1572864
    if available() < floor:
        raise SystemExit("RESOURCE STOP MemAvailable below 1572864 KiB")
    env = dict(os.environ, SYMPY_GROUND_TYPES="python", PYTHONDONTWRITEBYTECODE="1")
    env.update({key: "1" for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
    process = subprocess.Popen(command, env=env, start_new_session=True, preexec_fn=limits)
    lowest = available()
    try:
        while process.poll() is None:
            lowest = min(lowest, available())
            if lowest < floor:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                print("RESOURCE STOP MemAvailable below 1572864 KiB", flush=True)
                return 75
            time.sleep(0.5)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        print(f"RESOURCE min_MemAvailable_kib={lowest} exit={process.returncode}", flush=True)
    return process.returncode if process.returncode >= 0 else 128 - process.returncode


if __name__ == "__main__":
    sys.exit(main())
