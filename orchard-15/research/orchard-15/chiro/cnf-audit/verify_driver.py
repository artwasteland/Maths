#!/usr/bin/env python3
"""Check that emit_cube_cnf.py writes exactly the CNF run_cubes() would write.

Runs the real exist.run_cubes() with the real argparse namespace for
`15 32 --backend cadical --cubes --cube-index k`, with solve_standalone
replaced by a stub that performs only its CNF write (exist.py:971-977) and
then returns a fake UNSAT record instead of launching cadical.  Everything
upstream of the solver -- derive_reduction, enumerate_cubes, group_closure,
the cube_group filter, build_existence_encoding -- is the untouched frozen
code.  The stub's CNF is then compared byte-for-byte with the driver's.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
CHIRO = HERE.parent.parent.parent
sys.path.insert(0, str(CHIRO))

import exist  # noqa: E402
from chirosat import write_clauses  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stub_solve_standalone(encoding, encode_seconds, artifact_dir, backend, checker,
                          timeout, corrupt_proof, stem=None):
    """exist.solve_standalone minus the solver: only the CNF write."""
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or f"exist-{encoding.reduction.v}-{encoding.reduction.b}"
    cnf = artifact_dir / f"{stem}.cnf"
    write_clauses(encoding.nvars, encoding.clauses, cnf)
    return exist.common_result(encoding, encode_seconds) | {
        "verdict": "UNSAT",
        "proof_verified": True,
        "cnf": str(cnf.resolve()),
        "cnf_sha256": exist.file_sha256(cnf),
        "total_seconds": 0.0,
    }


def main() -> int:
    out = HERE.parent / "verify"
    ref_dir = out / "reference"
    drv_dir = out / "driver"
    for d in (ref_dir, drv_dir):
        d.mkdir(parents=True, exist_ok=True)

    ok = True
    for k in range(4):
        # --- reference: real run_cubes, solver stubbed ---
        args = exist.make_parser().parse_args(
            ["15", "32", "--backend", "cadical", "--cubes", "--cube-index", str(k),
             "--artifacts", str(ref_dir)]
        )
        real = exist.solve_standalone
        exist.solve_standalone = stub_solve_standalone
        try:
            started = time.perf_counter()
            exist.run_cubes(args, checker="/nonexistent-checker")
            ref_seconds = time.perf_counter() - started
        finally:
            exist.solve_standalone = real

        # --- driver ---
        subprocess.run(
            [sys.executable, str(HERE.parent / "emit_cube_cnf.py"), "15", "32",
             "--cube-index", str(k), "--artifacts", str(drv_dir)],
            check=True, stdout=subprocess.DEVNULL,
        )

        ref = ref_dir / f"exist-15-32-cube{k:03d}.cnf"
        drv = drv_dir / f"exist-15-32-cube{k:03d}.cnf"
        a, b = sha256(ref), sha256(drv)
        same = a == b
        ok &= same
        print(f"cube{k:03d}  run_cubes={a}  driver={b}  "
              f"{'MATCH' if same else 'MISMATCH'}  ({ref_seconds:.1f}s, {ref.stat().st_size} bytes)")

    print("ALL MATCH" if ok else "MISMATCH FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
