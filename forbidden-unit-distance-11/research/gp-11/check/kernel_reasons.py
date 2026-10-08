#!/usr/bin/env python3
"""Retain the original kernel corpus, adding exact refusal-text assertions and restoration.

Only temporary-path prefixes are normalised. The legacy fixture labelled
'L2 modulus mutation' actually reaches the L2 ratio guard; the expected text
states that guard explicitly and makes no claim to test the modulus guard.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import runpy
import sys
import tempfile
import types

sys.dont_write_bytecode = True
import gp11check as ck


def normalise(text):  # B11 kernel harness addition: preserve the complete rule/node text.
    text = text.replace(str(ck.ROOT), "<repo>")
    return re.sub(r"/tmp/gp10-check/kernel-selftest/selftest-[^/ :\n]+", "<run>", text)


def main():  # B11 kernel harness addition; checker, old test source and fixtures stay unchanged.
    harness = runpy.run_path(str(ck.GP10 / "check/kernel_selftest.py"))
    namespace = harness["namespace"]
    retained, positives = [], []

    class RetainedTemporary:
        def __init__(self, *args, **kwargs):  # B11 test helper: keep original files for the final replay.
            self.actual = tempfile.TemporaryDirectory(*args, **kwargs)
            retained.append(self.actual)

        def __enter__(self):  # B11 test helper.
            return self.actual.name

        def __exit__(self, *args):  # B11 test helper: main's finally owns cleanup.
            return False

    namespace["tempfile"] = types.SimpleNamespace(TemporaryDirectory=RetainedTemporary)

    def adapter(original):  # B11 test helper: remember positive bytes, including later-mutated lists.
        def invoke(name, cert, accept, *extra):  # B11 test helper.
            result = original(name, cert, accept, *extra)
            if accept:
                snapshot = {p: p.read_bytes() for tmp in retained
                            for p in Path(tmp.name).rglob("*") if p.is_file()}
                positives.append((original, name, cert, extra, snapshot, result))
            return result
        return invoke

    for name in ("invoke", "invoke_default"):
        namespace[name] = adapter(namespace[name])
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            assert namespace["main"]() == 0
        output = captured.getvalue()
        print(output, end="")
        observed = {}
        for line in output.splitlines():
            marker = ": exit=1: REJECT: "
            if line.startswith("PASS ") and marker in line:
                name, reason = line[5:].split(marker, 1)
                observed[name] = normalise(reason)
            elif line.startswith("PASS PROOFS.md coefficient mutation: rejected: "):
                observed["PROOFS.md coefficient mutation"] = line.split(": rejected: ", 1)[1]
        expected = json.loads((ck.HERE / "kernel-rejections.json").read_text())
        assert observed == expected, (observed, expected)
        for original, name, cert, extra, snapshot, result in positives:
            for path, data in snapshot.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with contextlib.redirect_stdout(io.StringIO()):
                restored = original("restore " + name, cert, True, *extra)
            assert restored == result, (name, restored, result)
        namespace["validate_written_tu_proofs"](ck.read_json(ck.U22 / "data/tu-gadgets.json"))
        print(f"KERNEL EXACT REASONS PASS rejections={len(observed)} restored_positive_invocations={len(positives)}")
        print("KERNEL WRITTEN PROOF MODELS RESTORED")
    finally:
        for tmp in retained:
            tmp.cleanup()


if __name__ == "__main__":
    main()
