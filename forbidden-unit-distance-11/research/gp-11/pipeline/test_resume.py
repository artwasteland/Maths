#!/usr/bin/env python3
"""SIGKILL a real worker, replay committed records, and compare mathematical output."""
from common import *
import argparse
import gzip
import sqlite3
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    codes = []
    with gzip.open(GP11 / "embed/results/extension/architect-500/records.jsonl.gz", "rt") as source:
        for line in source:
            record = json.loads(line)
            if record["verdict"] == "embedded":
                codes.append(record["g6"])
            if len(codes) == 30:
                break
    input_path = args.output / "input.g6"
    atomic(input_path, "".join(code+"\n" for code in sorted(codes)))

    def start(name, resume=False):
        command = [sys.executable, "-B", str(HERE / "drive.py"), "run", "--index", str(args.index),
                   "--state", str(args.output / (name+"-state")), "--output", str(args.output / (name+"-result")),
                   "--input", str(input_path), "--policy", "cheap"]
        if resume:
            command.append("--resume")
        log = (args.output / (name+".log")).open("a")
        process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
        log.close()
        return process

    baseline = start("baseline")
    assert baseline.wait() == 0
    interrupted = start("interrupted")
    deadline = time.monotonic()+180
    committed = 0
    while time.monotonic() < deadline and interrupted.poll() is None:
        path = args.output / "interrupted-state/state.sqlite"
        if path.exists():
            db = sqlite3.connect(path)
            try:
                committed = db.execute("SELECT COUNT(*) FROM accepted WHERE origin='extension'").fetchone()[0]
                leases = db.execute("SELECT COUNT(*) FROM leases WHERE stage='extension'").fetchone()[0]
            except sqlite3.OperationalError:
                leases = 0
            finally:
                db.close()
            if committed >= 3 and leases:
                os.killpg(interrupted.pid, signal.SIGKILL)
                break
        time.sleep(.01)
    assert interrupted.wait() == -signal.SIGKILL, "did_not_kill_mid_shard"
    # Also exercise recovery of a torn append after the committed boundary.
    with (args.output / "interrupted-state/certificates.jsonl").open("ab") as stream:
        stream.write(b'{"uncommitted":')
    resumed = start("interrupted", True)
    assert resumed.wait() == 0
    names = ("records.jsonl.gz", "UNKNOWN.g6", "input.g6", "assigned.g6", "frontier.jsonl.gz", "packets.jsonl.gz", "attempts.jsonl.gz")
    results = {}
    for name in names:
        a = digest(args.output / "baseline-result" / name)
        b = digest(args.output / "interrupted-result" / name)
        assert a == b, (name, a, b)
        results[name] = a
    repeated = start("interrupted", True)
    assert repeated.wait() == 0
    for name, expected in results.items():
        assert digest(args.output / "interrupted-result" / name) == expected
    summary = {"status": "PASS", "kill": "SIGKILL process group while extension lease active",
               "committed_embeddings_before_kill": committed, "identical_artifacts": results,
               "torn_append_recovered": True, "idempotent_resume": True,
               "operational_receipts_excluded": ["checker-report.json", "summary.json", "metrics.json"]}
    write_json(args.output / "resume.json", summary)
    print(compact(summary))


if __name__ == "__main__":
    main()
