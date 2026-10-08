"""Bounded, sequential late-stage workers and retained diagnostics."""
from common import *
import subprocess


def analyst_hint(detail):
    return {key: detail[key] for key in
        ("reason", "frame", "candidate_frames", "saturation_pairs", "triangle_choices", "branches",
         "primitive_candidates", "numerical_source", "precision_digits", "refined_error", "refined_gap", "attempts")
        if key in detail}


def command(argv, directory, stem, seconds, output_limit=16000000):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / (stem + ".stdout")
    err = directory / (stem + ".stderr")
    guard = Guard()
    guard.check()
    started = time.monotonic()
    with out.open("w") as stdout, err.open("w") as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            while child.poll() is None:
                guard.check()
                if time.monotonic() - started >= seconds:
                    raise Deadline("wall_budget")
                if out.stat().st_size + err.stat().st_size > output_limit:
                    raise ValueError("tool_output_limit")
                time.sleep(.05)
        finally:
            # Also reap a CAS grandchild if the caller's pipeline timer expires.
            for pid in descendants(child.pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
    if child.returncode:
        raise ValueError("tool_exit:" + str(child.returncode) + ":" + err.read_text()[-300:])
    if out.stat().st_size + err.stat().st_size > output_limit:
        raise ValueError("tool_output_limit")
    return out.read_text()


def isolated(module, code, seconds, directory, **inputs):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    request = directory / "request.json"
    write_json(request, dict(g6=code, seconds=seconds, directory=str(directory), **inputs))
    result = directory / "result.json"
    result.unlink(missing_ok=True)
    started = time.monotonic()
    reason = None
    try:
        command([sys.executable, str(module), "--worker", str(request)], directory,
                "worker", seconds, output_limit=2000000)
    except Deadline:
        reason = "wall_budget"
    except Exception as exc:
        reason = type(exc).__name__ + ":" + str(exc)[-300:]
    hints = directory / "hints.json"
    detail = json.loads(hints.read_text()) if hints.exists() else {}
    detail["search_seconds"] = time.monotonic() - started
    if result.exists() and reason is None:
        value = json.loads(result.read_text())
        detail.update(value["detail"])
        return value["cert"], detail
    detail["reason"] = reason or "worker_no_result"
    return None, detail


def worker_main(worker, search, seconds):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--g6")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seconds", type=float, default=seconds)
    parser.add_argument("--numeric", type=Path)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    if args.worker is None:
        if not args.g6 or not args.output or args.seconds <= 0:
            parser.error("--g6, --output and a positive --seconds are required")
        extra = {}
        if args.numeric:
            extra["evidence"] = json.loads(args.numeric.read_text())
        if args.work:
            extra["work"] = args.work
        cert, detail = search(args.g6, args.seconds, args.output, **extra)
        verdict = "embedded" if cert and cert["type"] == "exact" else "refuted"
        record = dict(g6=args.g6, verdict=verdict, cert=cert) if cert else unknown(args.g6, detail["reason"], {"seconds": args.seconds})
        write_json(args.output / "record.jsonl", record)
        write_json(args.output / "detail.json", detail)
        print(compact(dict(verdict=record["verdict"], reason=detail["reason"], record=str(args.output / "record.jsonl"),
                           search_seconds=detail["search_seconds"], requires_frozen_checker=True)))
        return
    request = json.loads(args.worker.read_text())
    directory = Path(request["directory"])
    limits(directory)
    guard = Guard()
    guard.start()
    detail = {}
    cert = None
    try:
        cert, detail = worker(request)
    except Exception as exc:
        hints = directory / "hints.json"
        detail = json.loads(hints.read_text()) if hints.exists() else {}
        detail["reason"] = type(exc).__name__ + ":" + str(exc)[-400:]
    except Deadline:
        hints = directory / "hints.json"
        detail = json.loads(hints.read_text()) if hints.exists() else {}
        detail["reason"] = "wall_budget"
    detail["minimum_available_kib"] = guard.minimum_kib
    write_json(directory / "result.json", {"cert": cert, "detail": detail})


class Budget:
    def __init__(self, seconds, directory, detail):
        self.deadline = time.monotonic() + seconds
        self.directory = Path(directory)
        self.detail = detail
        self.serial = 0

    def remaining(self):
        value = self.deadline - time.monotonic()
        if value < .1:
            raise Deadline("wall_budget")
        return value

    def save(self):
        write_json(self.directory / "hints.json", self.detail)

    def tool(self, source, suffix, argv, cap=None):
        self.serial += 1
        stem = f"tool-{self.serial:03d}"
        path = self.directory / (stem + suffix)
        path.write_text(source)
        seconds = min(self.remaining(), cap or self.remaining())
        began = time.monotonic()
        row = {"file": path.name, "cap_seconds": seconds}
        self.detail.setdefault("tools", []).append(row)
        self.save()
        try:
            return command(argv + [str(path)], self.directory, stem, seconds)
        finally:
            row["seconds"] = time.monotonic()-began
            self.save()
