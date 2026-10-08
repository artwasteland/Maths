#!/usr/bin/env python3
"""CONTRACT Section 3 for the (23,65) fleet: every graph a slice's filter-only prune kept at the top level is refuted.

usage: python top_level_check.py <extraction root> [--records DIR] [--self-test]

The fleet prunes filter-only, so a graph that survives every rule at (23,65) is kept as "unknown", and
verify-chain.py reports it (target_cell kept > 0). Section 3 then asks for an exact embedding (u(23) = 65) or a
refutation certificate that check/udcheck.py accepts. This checks the second, independently of verify-chain.py:

  - it finds every slice directory under the extraction root (<root>/<worker>/research/unit-distance-23/results/u23/
    23-65-L12-tri-pf74/s<i>of1920) whose 23-65.keep.g6 is non-empty, every copy of every slice;
  - each such slice needs a record <records>/s<i>of1920/ (default results/u23/top-level/ beside this tool) whose
    23-65.g6 holds exactly the copy's kept graphs (the same lines, as a set; the copy's 23-65.UNKNOWN.g6 too);
  - the record's 23-65.certs.jsonl is replayed by check/udcheck.py and check/udcheck398.py against the record's graph
    list, and each must ACCEPT with refuted equal to the number of graphs and embedded = unknown = 0.

A slice with a kept graph and no record, a record that disagrees with any copy, or a replay that does not accept
is a problem; exit 0 only when there is none. --self-test also replays a copy of each certificate with one proof-tree
entry changed and requires both checkers to reject it (the check can fail), with a REJECT that names the proof tree:
the checkers write REJECT on standard error, and a crash or any other failure is not that rejection.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
UD = REPO / "research/unit-distance-22"
KIND = "23-65-L12-tri-pf74"
ACCEPT = re.compile(r"^ACCEPT certificates records=(\d+) .*embedded=(\d+) refuted=(\d+) unknown=(\d+)")


def lines(p: Path) -> list[str]:
    return [l.strip() for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def replay(checker: str, graphs: Path, certs: Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as t:
        unknown = Path(t) / "23-65.UNKNOWN.g6"
        unknown.write_text("")
        r = subprocess.run([sys.executable, str(UD / "check" / checker), "--graphs", str(graphs), "--unknown-file",
                            str(unknown), "--data-dir", str(UD / "data"), "--expect-n", "23", "--expect-m", "65",
                            str(certs)], capture_output=True, text=True, cwd=UD)
    # the checkers print ACCEPT on stdout and REJECT on stderr: report the last line of whichever verdict appeared
    out = (r.stdout.strip().splitlines() or [""])[-1]
    err = [l for l in r.stderr.splitlines() if l.startswith("REJECT")]
    return r.returncode == 0 and out.startswith("ACCEPT"), (err[-1] if err else out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--records", type=Path, default=REPO / "research/unit-distance-23/results/u23/top-level")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    problems, report = [], []
    kept: dict[int, list[tuple[Path, set]]] = {}
    for d in sorted(a.root.glob(f"*/research/unit-distance-23/results/u23/{KIND}/s*of1920")):
        g = lines(d / "23-65.keep.g6")
        if not g:
            continue
        idx = int(d.name[1:].split("of")[0])
        unknown = set(lines(d / "23-65.UNKNOWN.g6"))
        if unknown != set(g):
            problems.append(f"s{idx} ({d.parts[len(a.root.parts)]}): 23-65.UNKNOWN.g6 is not its 23-65.keep.g6")
        kept.setdefault(idx, []).append((d, set(g)))
    for idx, copies in sorted(kept.items()):
        rec = a.records / f"s{idx}of1920"
        graphs, certs = rec / "23-65.g6", rec / "23-65.certs.jsonl"
        if not (graphs.exists() and certs.exists()):
            problems.append(f"s{idx}: {sum(len(g) for _, g in copies)} kept graph(s) and no top-level record at {rec}")
            continue
        want = set(lines(graphs))
        for d, g in copies:
            if g != want:
                problems.append(f"s{idx} ({d.parts[len(a.root.parts)]}): kept {sorted(g)} but the record holds {sorted(want)}")
        for checker in ("udcheck.py", "udcheck398.py"):
            ok, last = replay(checker, graphs, certs)
            m = ACCEPT.match(last)
            if not (ok and m and int(m.group(1)) == len(want) and int(m.group(3)) == len(want)
                    and int(m.group(2)) == 0 and int(m.group(4)) == 0):
                problems.append(f"s{idx}: {checker} does not accept a refutation of all {len(want)}: {last[:200]}")
            else:
                report.append(f"s{idx}: {len(want)} kept graph(s) in {len(copies)} cop{'y' if len(copies) == 1 else 'ies'}; "
                              f"{checker}: {last}")
        if a.self_test:
            recs = [json.loads(l) for l in lines(certs)]
            recs[0]["witness"]["tree"]["A"][0][0] = [2] if recs[0]["witness"]["tree"]["A"][0][0] != [2] else [3]
            with tempfile.TemporaryDirectory() as t:
                bad = Path(t) / "23-65.certs.jsonl"
                bad.write_text("".join(json.dumps(r) + "\n" for r in recs))
                for checker in ("udcheck.py", "udcheck398.py"):
                    ok, last = replay(checker, graphs, bad)
                    # a crash is not a rejection: the checker must say REJECT, for the proof tree it was given
                    if ok:
                        problems.append(f"s{idx}: self-test: {checker} accepted a tampered certificate")
                    elif not (last.startswith("REJECT") and "witness.tree" in last):
                        problems.append(f"s{idx}: self-test: {checker} failed on a tampered certificate without "
                                        f"rejecting its proof tree: {last[:200]!r}")
                    else:
                        report.append(f"s{idx}: self-test: {checker} rejects a tampered certificate: {last[:160]}")
    for r in report:
        print(r)
    for p in problems:
        print("PROBLEM:", p)
    print(f"TOP-LEVEL {'OK' if not problems else 'FAIL'}: {len(kept)} slice(s) with kept graphs, "
          f"{sum(len(c) for c in kept.values())} cop(ies), {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
