#!/usr/bin/env python3
"""Forbidden set 398 in the blind checker (udcheck398.py) and the witness verifier: controls.

Every case runs the real command line and states the exit it must give. Hosts are built from
members of data/forbidden-398.json, put in nauty-labelg canonical form (udcheck.py requires it),
and their witnesses come from filter/udfilter -s 398; the checker then has to agree with them
without trusting them.

  host A  member 74 itself (the first of GP-10's 324), 10 vertices
  host B  member 397 itself (the last), 10 vertices
  host C  K4 plus a pendant vertex: member 0, the same graph in both sets
  host D  member 200 inside a 23-vertex host with 15 extra edges (a (23,m)-sized record)

Positive: udcheck398.py accepts A, B, C, D and a tu and an unknown record in the same file;
udcheck.py (set 74) accepts C; verify-witness.py -s 398 accepts A, B, C, D, and without -s
accepts C; a tu witness verifies under -s 398 as under set 74.

Red (each must be rejected):
  R1 wrong member: A's map with index 75, with index 73, and (in-process, through udcheck398's
     own loader and udcheck.py's verify_certificates) with every index other than 74; A is
     member 74 exactly, so no other member of the antichain can map onto it
  R2 non-injective map: A's map with two vertices sent to the same host vertex
  R3 a set-74 run citing an index >= 74: A (74), B (397) and D (200) given to udcheck.py and
     to verify-witness.py without -s
  R4 forbidden-398.json with one byte appended (a copied data directory)
  R5 forbidden-74.json with two entries swapped: the 398 file still hashes to its pin, but its
     first 74 entries no longer equal the 74 list
  R6 udcheck.py changed by one byte: udcheck398.py refuses to run (exit 2)
  R7 verify-witness.py -s 398 against a tampered file (exit 2) and -s 399 (exit 2)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent
DATA = UD / "data"
# the checker's interpreter: $UDCHECK_PYTHON, else the maths venv where it exists, else this one
# (no record here needs SymPy, which udcheck.py imports only for embedded and refuted witnesses)
_MATHS = Path.home() / "tools/pyenv-maths/bin/python"
PYTHON = Path(os.environ.get("UDCHECK_PYTHON") or (_MATHS if _MATHS.is_file() else sys.executable))
UDCHECK = HERE / "udcheck.py"
UDCHECK398 = HERE / "udcheck398.py"
VERIFY = UD / "filter" / "verify-witness.py"
UDFILTER = UD / "filter" / "udfilter"
LABELG = "/usr/bin/nauty-labelg"
F398 = json.loads((DATA / "forbidden-398.json").read_text())
T = json.loads((DATA / "tu-gadgets.json").read_text())

failures: list[str] = []
passes = 0


def g6(n: int, edges) -> str:
    es = {tuple(sorted(e)) for e in edges}
    bits = [1 if (i, j) in es else 0 for j in range(1, n) for i in range(j)]
    while len(bits) % 6:
        bits.append(0)
    return chr(n + 63) + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2))
                                 for k in range(0, len(bits), 6))


def canonical(code: str) -> str:
    return subprocess.run([LABELG, "-q"], input=code + "\n", text=True, capture_output=True,
                          check=True).stdout.strip()


def udfilter398(code: str) -> dict:
    p = subprocess.run([str(UDFILTER), "-s", "398", "-f", str(DATA / "forbidden-398.json"),
                        "-t", str(DATA / "tu-gadgets.json")], input=code + "\n", text=True,
                       capture_output=True, check=True)
    return json.loads(p.stdout)


def expect(name: str, ok: bool, detail: str = "") -> None:
    global passes
    if ok:
        passes += 1
        print(f"PASS {name}{': ' + detail if detail else ''}")
    else:
        failures.append(name)
        print(f"FAIL {name}{': ' + detail if detail else ''}")


def check_cli(name: str, checker: Path, records: list[dict], accept: bool, n: int | None = None,
              m: int | None = None, data_dir: Path | None = None, exit_code: int | None = None,
              needle: str | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="st398-") as tmp:
        cert = Path(tmp) / "certs.jsonl"
        cert.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records))
        unknown = [r["g6"] for r in records if r["verdict"] == "unknown"]
        if unknown:
            (Path(tmp) / "UNKNOWN.g6").write_text("".join(c + "\n" for c in unknown))
        size = ["--expect-n", str(n), "--expect-m", str(m)] if n is not None else ["--allow-any-size"]
        cmd = [str(PYTHON), str(checker), *size, str(cert)]
        if data_dir is not None:
            cmd += ["--data-dir", str(data_dir)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = (p.stdout + p.stderr).strip()
        want = exit_code if exit_code is not None else (0 if accept else 1)
        ok = p.returncode == want and (("ACCEPT" in p.stdout) == accept)
        if needle is not None:
            ok = ok and needle in out
        expect(name, ok, f"exit {p.returncode}: {out.splitlines()[0] if out else ''}"[:220])


def check_verify(name: str, record: dict, want: int, *flags: str, script: Path = VERIFY) -> None:
    p = subprocess.run([sys.executable, str(script), *flags, record["g6"], json.dumps(record)],
                       capture_output=True, text=True)
    expect(name, p.returncode == want, f"exit {p.returncode} (want {want}) {p.stderr.strip()[:120]}")


def member_host(index: int) -> str:
    edges = F398[index]
    n = max(max(e) for e in edges) + 1
    return canonical(g6(n, edges))


def main() -> int:
    if not PYTHON.is_file():
        print(f"missing {PYTHON}", file=sys.stderr)
        return 2
    # hosts and their witnesses (from udfilter -s 398; the checker decides independently)
    host = {"A": member_host(74), "B": member_host(397)}
    host["C"] = canonical(g6(5, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3), (3, 4)]))
    d_edges = [(a + 13, b + 13) for a, b in F398[200]] + [(i, i + 1) for i in range(12)] + \
              [(0, 13), (5, 17), (12, 22)]
    host["D"] = canonical(g6(23, d_edges))
    cert = {k: udfilter398(v) for k, v in host.items()}
    want_index = {"A": 74, "B": 397, "C": 0, "D": 200}
    for k in "ABCD":
        c = cert[k]
        expect(f"setup: udfilter -s 398 calls host {k} forbidden with member {want_index[k]}",
               c.get("verdict") == "forbidden" and c["witness"]["index"] == want_index[k],
               json.dumps(c.get("witness"))[:120])
    records = {k: {"g6": cert[k]["g6"], "verdict": "forbidden", "witness": cert[k]["witness"]}
               for k in "ABCD"}
    # a tu record and an unknown record, to show the rest of the kernel is untouched in set 398
    tu_edges = [(a + 3, b + 3) for a, b in T[0]["edges"]] + [(0, 1), (1, 2)]
    tu_code = canonical(g6(11, tu_edges))
    tu_filter = udfilter398(tu_code)
    tu_record = None
    if tu_filter.get("verdict") == "tu":
        w = tu_filter["witness"]
        gadget = T[w["index"]]
        tu_record = {"g6": tu_code, "verdict": "tu",
                     "witness": {"index": w["index"], "map": w["map"],
                                 "pair": [w["map"][gadget["pair"][0]], w["map"][gadget["pair"][1]]]}}
    expect("setup: a tu host", tu_record is not None, json.dumps(tu_filter)[:120])
    unknown_record = {"g6": canonical(g6(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)])),
                      "verdict": "unknown"}

    # positive controls
    for k in "ABCD":
        check_cli(f"accept: udcheck398 host {k} (member {want_index[k]})", UDCHECK398, [records[k]], True)
    if tu_record is not None:
        check_cli("accept: udcheck398 forbidden + tu + unknown records in one file", UDCHECK398,
                  [records["A"], tu_record, unknown_record], True)
    check_cli("accept: udcheck.py (set 74) host C (member 0)", UDCHECK, [records["C"]], True)
    n_d = ord(host["D"][0]) - 63
    check_cli("accept: udcheck398 host D with --expect-n 23", UDCHECK398, [records["D"]], True,
              n=n_d, m=len(d_edges))
    for k in "ABCD":
        check_verify(f"accept: verify-witness -s 398 host {k}", cert[k], 0, "-s", "398")
    check_verify("accept: verify-witness (set 74) host C", cert["C"], 0)
    check_verify("accept: verify-witness --forbidden-set 398 host A", cert["A"], 0, "--forbidden-set", "398")
    if tu_record is not None:
        check_verify("accept: verify-witness -s 398 on a tu witness", tu_filter, 0, "-s", "398")
        check_verify("accept: verify-witness (set 74) on the same tu witness", tu_filter, 0)

    # R1 wrong member
    for wrong in (75, 73, 0, 397):
        bad = json.loads(json.dumps(records["A"]))
        bad["witness"]["index"] = wrong
        check_cli(f"R1 reject: udcheck398 host A (member 74) cited as member {wrong}", UDCHECK398, [bad], False)
        vbad = json.loads(json.dumps(cert["A"]))
        vbad["witness"]["index"] = wrong
        check_verify(f"R1 reject: verify-witness -s 398 host A cited as member {wrong}", vbad, 1, "-s", "398")
    # every other index, in-process, through udcheck398's loader and udcheck.py's verify_certificates
    sys.path.insert(0, str(HERE))
    import importlib.util
    spec = importlib.util.spec_from_file_location("udcheck398_under_test", UDCHECK398)
    front = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(front)
    kernel = front.load_kernel()
    loader = front.make_loader(kernel)
    forbidden, gadgets = loader(DATA)
    accepted_wrong = []
    with tempfile.TemporaryDirectory(prefix="st398-all-") as tmp:
        for index in range(398):
            bad = json.loads(json.dumps(records["A"]))
            bad["witness"]["index"] = index
            path = Path(tmp) / f"c{index}.jsonl"
            path.write_text(json.dumps(bad, separators=(",", ":")) + "\n")
            try:
                kernel.verify_certificates(path, forbidden, gadgets, None, None, LABELG, None, None)
                if index != 74:
                    accepted_wrong.append(index)
            except kernel.CheckError:
                if index == 74:
                    accepted_wrong.append("74 rejected")
    expect("R1 reject: host A cited as each of the 397 other members (in-process)", not accepted_wrong,
           f"wrongly decided: {accepted_wrong[:10]}")

    # R2 non-injective map
    bad = json.loads(json.dumps(records["A"]))
    bad["witness"]["map"][1] = bad["witness"]["map"][0]
    check_cli("R2 reject: udcheck398 non-injective map", UDCHECK398, [bad], False, needle="not injective")
    vbad = json.loads(json.dumps(cert["A"]))
    vbad["witness"]["map"][1] = vbad["witness"]["map"][0]
    check_verify("R2 reject: verify-witness -s 398 non-injective map", vbad, 1, "-s", "398")

    # R3 a set-74 run citing an index >= 74
    for k in "ABD":
        check_cli(f"R3 reject: udcheck.py (set 74) host {k} citing member {want_index[k]}", UDCHECK,
                  [records[k]], False, needle="out of range")
        check_verify(f"R3 reject: verify-witness (set 74) host {k} citing member {want_index[k]}", cert[k], 1)
    check_verify("R3 reject: verify-witness -s 74 host A citing member 74", cert["A"], 1, "-s", "74")

    with tempfile.TemporaryDirectory(prefix="st398-data-") as tmp:
        # R4 tampered 398 file
        d4 = Path(tmp) / "r4" / "data"
        shutil.copytree(DATA, d4)
        with (d4 / "forbidden-398.json").open("ab") as f:
            f.write(b"\n")
        check_cli("R4 reject: udcheck398 with forbidden-398.json plus one byte", UDCHECK398, [records["A"]],
                  False, data_dir=d4, needle="not the pinned forbidden-398.json")
        # R5 the 74 list reordered: the 398 file is still pinned, its prefix no longer matches
        d5 = Path(tmp) / "r5" / "data"
        shutil.copytree(DATA, d5)
        f74 = json.loads((d5 / "forbidden-74.json").read_text())
        f74[0], f74[1] = f74[1], f74[0]
        (d5 / "forbidden-74.json").write_text(json.dumps(f74))
        check_cli("R5 reject: udcheck398 when forbidden-74.json no longer prefixes the 398", UDCHECK398,
                  [records["C"]], False, data_dir=d5, needle="first 74 entries")
        # R6 the kernel changed by one byte
        c6 = Path(tmp) / "r6" / "check"
        c6.mkdir(parents=True)
        shutil.copy2(UDCHECK398, c6 / "udcheck398.py")
        (c6 / "udcheck.py").write_bytes(UDCHECK.read_bytes() + b"\n")
        shutil.copytree(DATA, Path(tmp) / "r6" / "data")
        check_cli("R6 refuse: udcheck398 with udcheck.py changed by one byte", c6 / "udcheck398.py",
                  [records["A"]], False, exit_code=2, needle="not the pinned udcheck.py")
        # R7 verify-witness against a tampered file, and a bad set
        f7 = Path(tmp) / "r7" / "filter"
        f7.mkdir(parents=True)
        shutil.copy2(VERIFY, f7 / "verify-witness.py")
        shutil.copytree(d4, Path(tmp) / "r7" / "data")
        check_verify("R7 refuse: verify-witness -s 398 with forbidden-398.json plus one byte", cert["A"], 2,
                     "-s", "398", script=f7 / "verify-witness.py")
        check_verify("R7 refuse: verify-witness -s 399", cert["A"], 2, "-s", "399")
    print(f"SELFTEST-398 {'PASS' if not failures else 'FAIL'}: {passes} passed, {len(failures)} failed")
    for f in failures:
        print("FAILED:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
