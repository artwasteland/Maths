#!/usr/bin/env python3
"""check/udcheck.py with forbidden set 398: the u(22) blind checker, unchanged, given the 398 list.

udcheck.py is the trusted kernel of GP-10 as well as the checker of the u(22) run, and GP-10 pins
its sha256 (research/gp-10/RESULT.md; research/gp-10/check-audit/verify_deliverables.py asserts
it), so it is not edited. This front end reads udcheck.py's bytes, refuses to run unless they
hash to the pin below, executes exactly those bytes, and replaces one function,
load_trusted_data, so that the forbidden list is data/forbidden-398.json:

  - the file's sha256 must be FORBIDDEN_398_SHA256 (enum/REPORT-398.md: the 74 graphs of
    forbidden-74.json in their order, then GP-10's 324 graphs on 10 vertices);
  - it is validated as udcheck.py validates the 74 (edge lists of integer pairs, contiguous
    vertices, no loop, no duplicate edge), must hold exactly 398 graphs of order at most 10, and
    its first 74 entries must equal forbidden-74.json's, so an index below 74 names the same
    graph in both sets;
  - forbidden-74.json and the TU gadgets are loaded and validated by udcheck.py's own code.

Every certificate decision is then udcheck.py's main(): a "forbidden" witness must give an index
into the 398 list (0 <= index < 398), an injective map of that member's vertices into the
candidate, and every edge of the member must map onto an edge of the candidate. Arguments,
output and exit codes are udcheck.py's (exit 2 if udcheck.py is not the pinned file). Use
udcheck.py itself for set 74. Red controls: check/selftest-398.py.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
KERNEL = HERE / "udcheck.py"
KERNEL_SHA256 = "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de"
FORBIDDEN_398 = "forbidden-398.json"
FORBIDDEN_398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
FORBIDDEN_398_COUNT = 398
FORBIDDEN_398_MAX_ORDER = 10


def load_kernel() -> types.ModuleType:
    """udcheck.py as a module, executed from the very bytes that were hashed."""
    raw = KERNEL.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != KERNEL_SHA256:
        print(f"REJECT: {KERNEL} has sha256 {digest}, not the pinned udcheck.py {KERNEL_SHA256}",
              file=sys.stderr)
        raise SystemExit(2)
    module = types.ModuleType("udcheck_kernel")
    module.__file__ = str(KERNEL)
    sys.modules[module.__name__] = module   # dataclasses look their module up here
    exec(compile(raw, str(KERNEL), "exec"), module.__dict__)
    return module


def make_loader(kernel: types.ModuleType):
    original = kernel.load_trusted_data
    fail = kernel.fail

    def load_trusted_data_398(data_dir: Path) -> tuple[list[Any], list[Any]]:
        forbidden_74, gadgets = original(data_dir)
        path = Path(data_dir) / FORBIDDEN_398
        try:
            raw = path.read_bytes()
        except OSError as exc:
            fail(f"cannot read {path}: {exc}")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != FORBIDDEN_398_SHA256:
            fail(f"{path} has sha256 {digest}, not the pinned forbidden-398.json {FORBIDDEN_398_SHA256}")
        try:
            forbidden = json.loads(raw.decode("utf-8"), object_pairs_hook=kernel.no_duplicate_object)
        except (UnicodeError, json.JSONDecodeError) as exc:
            fail(f"{path}: cannot read JSON: {exc}")
        if not isinstance(forbidden, list) or len(forbidden) != FORBIDDEN_398_COUNT:
            fail(f"forbidden-398.json does not contain {FORBIDDEN_398_COUNT} patterns")
        for index, pattern in enumerate(forbidden):
            if not isinstance(pattern, list):
                fail(f"forbidden pattern {index}: expected edge list")
            n = kernel.pattern_order(pattern)
            if n > FORBIDDEN_398_MAX_ORDER:
                fail(f"forbidden pattern {index}: order {n} above {FORBIDDEN_398_MAX_ORDER}")
            seen: set[tuple[int, int]] = set()
            for j, edge in enumerate(pattern):
                if (not isinstance(edge, list) or len(edge) != 2 or
                        any(isinstance(x, bool) or not isinstance(x, int) for x in edge)):
                    fail(f"forbidden pattern {index} edge {j}: malformed")
                u, v = edge
                if not (0 <= u < n and 0 <= v < n and u != v):
                    fail(f"forbidden pattern {index} edge {j}: invalid endpoints")
                e = (min(u, v), max(u, v))
                if e in seen:
                    fail(f"forbidden pattern {index}: duplicate edge {e}")
                seen.add(e)
        if forbidden[:74] != forbidden_74:
            fail("the first 74 entries of forbidden-398.json are not forbidden-74.json's 74")
        return forbidden, gadgets

    return load_trusted_data_398


def main(argv: Sequence[str] | None = None) -> int:
    kernel = load_kernel()
    kernel.load_trusted_data = make_loader(kernel)
    return kernel.main(argv)


if __name__ == "__main__":
    sys.exit(main())
