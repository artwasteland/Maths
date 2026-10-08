#!/usr/bin/env python3
"""Run the G5-closed verify-chain.py and its memory-bounded copy verify-chain-lean.py on the same run directories
and compare what they print.

usage: python lean_diff.py [--check] [--faults] [--g5 FILE] [--lean FILE] RUN_DIR [RUN_DIR ...] [-- CHECKER ARGS]

For each run directory, both checkers run with the same arguments (--check replays every certificate file too; the
arguments after -- are passed to both, e.g. --from-n 13 --expect-target 23 65). Their stdout, stderr and exit status
must be identical, byte for byte. Each run's peak resident memory is printed beside it.

--faults: for each run directory with a pruned cell the check inspects (n >= the --from-n given), a scratch copy is
made; unchanged, it must get the original's verdict from both checkers, and then faults are planted in it, one at a
time (a certificate's g6 changed, a keep line dropped, a verdict renamed, a refuted record's witness removed, a
certificate file without its final newline, a non-ASCII byte in a certificate file, a parent source changed). Both
checkers must refuse each: CHAIN FAIL, with an exit other than the faithful copy's. Their stdout must still be identical, except for the files lean
reads differently: the non-ASCII byte and the missing final newline, where only the wording of the one "could not be
checked" problem may differ.

Last line: LEAN-DIFF OK|FAIL: R of R run directories identical, F of F planted faults refused by both (identical: I),
peak memory g5 X MB / lean Y MB. Exit 0 only on OK.
"""
import argparse, hashlib, json, resource, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
ENUM = REPO / "research/unit-distance-22/enum"
G5_SHA256 = "d253338569dedb41740cdb4774a6a361f6498f036787a52c3f985caca5d6ddd8"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def child_peak(checker: Path, rundir: Path, args: list) -> dict:
    """run() in a fresh helper process, so each measurement's RUSAGE_CHILDREN maximum is its own."""
    code = ("import json, resource, subprocess, sys, time\n"
            "t0 = time.time()\n"
            "p = subprocess.run(sys.argv[1:], capture_output=True)\n"
            "sys.stdout.buffer.write(json.dumps({'code': p.returncode, 'out': p.stdout.decode('latin-1'), "
            "'err': p.stderr.decode('latin-1'), 's': time.time() - t0, "
            "'rss_mb': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024}).encode())\n")
    r = subprocess.run([sys.executable, "-c", code, sys.executable, str(checker), str(rundir), *args],
                       capture_output=True)
    return json.loads(r.stdout)


def pruned_cell(rundir: Path, min_n: int = 0) -> tuple | None:
    """A pruned cell the check inspects (n >= min_n, the --from-n given) with a nonempty certificate file and some
    refuted or tu record: (n, m) or None. A fault in a cell the check does not inspect proves nothing."""
    for certs in sorted(rundir.glob("*.certs.jsonl"), key=lambda q: tuple(int(x) for x in q.name.split(".")[0].split("-"))):
        if certs.stat().st_size == 0 or int(certs.name.split("-")[0]) < min_n:
            continue
        for line in certs.read_text().splitlines():
            if json.loads(line).get("verdict") in ("refuted", "tu"):
                n, m = certs.name.split(".")[0].split("-")
                return int(n), int(m)
    return None


def faults(rundir: Path, cell: tuple) -> list:
    """(name, relative file, function turning its bytes into the faulty bytes, lean reads it differently)."""
    n, m = cell
    certs, keep = f"{n}-{m}.certs.jsonl", f"{n}-{m}.keep.g6"

    def edit_record(pred, change):
        def f(b: bytes) -> bytes:
            lines = b.decode().split("\n")
            for k, l in enumerate(lines):
                if l and pred(json.loads(l)):
                    r = json.loads(l)
                    change(r)
                    lines[k] = json.dumps(r)
                    return "\n".join(lines).encode()
            raise SystemExit(f"no record to change in {certs}")
        return f

    def g6_changed(r):
        r["g6"] = r["g6"][:-1] + ("A" if r["g6"][-1] != "A" else "B")

    out = [
        ("a certificate's g6 changed", certs, edit_record(lambda r: True, g6_changed), False),
        ("a verdict renamed", certs, edit_record(lambda r: True, lambda r: r.__setitem__("verdict", "bogus")), False),
        ("a refuted or tu record's witness removed", certs,
         edit_record(lambda r: r.get("verdict") in ("refuted", "tu"), lambda r: r.pop("witness", None)), False),
        ("the certificate file without its final newline", certs, lambda b: b[:-1], True),
        ("a non-ASCII byte in the certificate file", certs, lambda b: b[:1] + b"\xe9" + b[1:], True),
    ]
    kp = rundir / keep
    if kp.exists() and kp.stat().st_size:
        out.append(("a keep line dropped", keep, lambda b: b"".join(b.splitlines(keepends=True)[1:]), False))
    am = rundir / f"{n}-{m}.manifest.json"
    if am.exists():
        src = (json.loads(am.read_text()).get("parent_sources") or [{}])[0].get("file")
        if src and Path(src).is_file() and rundir in Path(src).parents:
            out.append(("a parent source changed", str(Path(src).relative_to(rundir)),
                        lambda b: b[:-2] + (b"A" if b[-2:-1] != b"A" else b"B") + b"\n", False))
    return out


def main() -> int:
    argv = sys.argv[1:]
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--faults", action="store_true")
    ap.add_argument("--g5", type=Path, default=ENUM / "verify-chain.py")
    ap.add_argument("--lean", type=Path, default=ENUM / "verify-chain-lean.py")
    a = ap.parse_args(argv)
    if sha(a.g5) != G5_SHA256:
        raise SystemExit(f"{a.g5} is not the G5-closed checker")
    args = (["--check"] if a.check else []) + extra
    print(f"g5 {a.g5.name} sha256 {sha(a.g5)[:16]}; lean {a.lean.name} sha256 {sha(a.lean)[:16]}; args {args}")
    same = total = refused = planted = ident = 0
    peak = {"g5": 0.0, "lean": 0.0}
    problems = []
    for rd in a.runs:
        rd = rd.resolve()
        g, l = child_peak(a.g5, rd, args), child_peak(a.lean, rd, args)
        peak["g5"], peak["lean"] = max(peak["g5"], g["rss_mb"]), max(peak["lean"], l["rss_mb"])
        total += 1
        base_code = g["code"]
        eq = (g["code"], g["out"], g["err"]) == (l["code"], l["out"], l["err"])
        same += eq
        last = (g["out"].strip().splitlines() or [""])[-1]
        print(f"{rd.name}: {'identical' if eq else 'DIFFERENT'} (exit {g['code']}/{l['code']}; {last[:90]}); "
              f"peak {g['rss_mb']:.0f}/{l['rss_mb']:.0f} MB; {g['s']:.0f}/{l['s']:.0f} s")
        if not eq:
            problems.append(f"{rd.name}: the two checkers differ")
            for k in ("out", "err"):
                if g[k] != l[k]:
                    ga, la = g[k].splitlines(), l[k].splitlines()
                    j = next((i for i, (x, y) in enumerate(zip(ga, la)) if x != y), min(len(ga), len(la)))
                    print(f"  {k} first difference at line {j}: g5 {ga[j:j+1]} / lean {la[j:j+1]}")
        if not a.faults:
            continue
        min_n = int(extra[extra.index("--from-n") + 1]) if "--from-n" in extra else 0
        cell = pruned_cell(rd, min_n)
        if cell is None:
            print(f"  no pruned cell with a refuted or tu record: no faults planted in {rd.name}")
            continue
        # the unchanged scratch copy first: it must get the original's verdict from both checkers, or a planted
        # fault could be refused for the copy's own sake (a check that cannot fail)
        for name, rel, change, reads_differently in [("none (the faithful copy)", None, None, False)] + faults(rd, cell):
            with tempfile.TemporaryDirectory() as tmp:
                td = Path(tmp) / rd.name
                shutil.copytree(rd, td, symlinks=True)
                # manifests name files by absolute path: the copy's own paths must be the ones it names
                for mf in td.rglob("*.json"):
                    t = mf.read_text()
                    if str(rd) in t:
                        mf.write_text(t.replace(str(rd), str(td)))
                g, l = None, None
                if rel is None:
                    g, l = child_peak(a.g5, td, args), child_peak(a.lean, td, args)
                    faithful = g["code"] == l["code"] == base_code
                    print(f"  scratch copy of {rd.name}: exit {g['code']}/{l['code']} (original {base_code}): "
                          f"{'faithful' if faithful else 'NOT FAITHFUL'}")
                    if not faithful:
                        problems.append(f"{rd.name}: its scratch copy does not reproduce its verdict; no fault "
                                        "planted in it counts")
                        break
                    continue
                p = td / rel
                p.write_bytes(change(p.read_bytes()))
                g, l = child_peak(a.g5, td, args), child_peak(a.lean, td, args)
                planted += 1
                # refused: its verdict is CHAIN FAIL and its exit is not the faithful copy's (a check from level 13
                # passes with exit 3, so "nonzero" is not a refusal; the first run of this tool counted it as one)
                fails = lambda r: r["code"] != base_code and any(x.startswith("CHAIN FAIL") for x in r["out"].splitlines())
                both = fails(g) and fails(l)
                refused += both
                eq = g["out"] == l["out"] and g["code"] == l["code"]
                ident += eq
                ok = both and (eq or reads_differently)
                gl = [x for x in g["out"].splitlines() if x.startswith(("PROBLEM", "CHAIN"))][:2]
                ll = [x for x in l["out"].splitlines() if x.startswith(("PROBLEM", "CHAIN"))][:2]
                print(f"  fault in {rd.name} ({cell[0]},{cell[1]}): {name}: {'ok' if ok else 'FAIL'}: exit "
                      f"{g['code']}/{l['code']}, {'identical' if eq else 'worded differently'}")
                if not eq:
                    print(f"    g5: {gl}\n    lean: {ll}")
                if not ok:
                    problems.append(f"{rd.name}: {name}: exit {g['code']}/{l['code']}, identical {eq}")
    for p in problems:
        print("PROBLEM:", p)
    good = not problems and total > 0 and same == total and (not a.faults or (planted > 0 and refused == planted))
    print(f"LEAN-DIFF {'OK' if good else 'FAIL'}: {same} of {total} run directories identical, {refused} of "
          f"{planted} planted faults refused by both (identical: {ident}), peak memory g5 {peak['g5']:.0f} MB / "
          f"lean {peak['lean']:.0f} MB")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
