#!/usr/bin/env python3
"""Guards: every guard of both forbidden sets fires, and set 74 fails exactly as before.

udenum and udfilter each get:
  - the accepted inputs (set 74 with forbidden-74.json, set 398 with forbidden-398.json);
  - set 398 given the 74 file, or the 398 file plus one trailing byte: refused by the sha256 pin;
  - set 74 given the 398 file, a bad set number: refused;
  - malformed files in set 74 (73 graphs, 81 graphs, a duplicate edge, an order-10 graph, the 398
    file, unbalanced brackets): the NEW binary's exit status and message must equal the OLD
    binary's, i.e. set 74 rejects every input where and as it did before;
  - test builds whose sha256 pin is moved (with -D) to a mutated 398 file, so that the guards
    BEHIND the pin are reached and shown to fire one at a time: 397 graphs; 398 graphs but a
    9-vertex member in place of a 10-vertex one (3,874 patterns); one edge added to a member (size
    distribution); an 11-vertex member (udenum: bad edge, udfilter: order above 10).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from t398lib import (F398, F74, HERE, NEW_UDENUM, NEW_UDFILTER, OLD_UDENUM, OLD_UDFILTER, SCRATCH, TU, UD,
                     sha256)

ENUM_FLAGS = ["-O3", "-DNDEBUG", "-std=c17", "-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Wconversion",
              "-Wno-old-style-declaration", "-I/usr/include/x86_64-linux-gnu/nauty", "-I/usr/include/nauty"]


def udenum_stats(binary: Path, forbidden: Path, extra=()) -> tuple[int, str]:
    p = subprocess.run(["nice", "-n", "10", str(binary), "--forbidden", str(forbidden), "--pattern-stats", *extra],
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def udfilter_load(binary: Path, forbidden: Path, extra=()) -> tuple[int, str]:
    p = subprocess.run(["nice", "-n", "10", str(binary), "-f", str(forbidden), "-t", str(TU), *extra],
                       input="C~\n", capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=SCRATCH / "guards")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "guards.json")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    rows = []

    def expect(name, got: tuple[int, str], ok_exit: bool, needle: str):
        good = (got[0] == 0) == ok_exit and needle in got[1]
        rows.append({"case": name, "exit": got[0], "output": got[1][:300], "as_required": good})
        print(f"{'ok ' if good else 'BAD'} {name}: exit {got[0]}: {got[1][:160]}")

    l74 = json.loads(F74.read_text())
    l398 = json.loads(F398.read_text())
    files = {}

    def mk(name, value, raw=None):
        p = w / name
        p.write_bytes(raw if raw is not None else json.dumps(value).encode())
        files[name] = p
        return p

    trailing = mk("398-plus-newline.json", None, F398.read_bytes() + b"\n")
    m73 = mk("73.json", l74[:73])
    m81 = mk("81.json", l74 + l74[:7])
    dup = mk("dup-edge.json", [l74[0] + [l74[0][0]]] + l74[1:])
    ord10 = mk("order-10-in-74.json", l74[:73] + [l398[74]])
    unbal = mk("unbalanced.json", None, F74.read_bytes()[:-1])
    m397 = mk("397.json", l398[:397])
    nine = mk("398-with-a-9-vertex-member.json", l398[:397] + [l74[73]])
    plus_edge_member = [list(e) for e in l398[250]]
    present = {frozenset(e) for e in plus_edge_member}
    plus_edge_member.append(next([x, y] for x in range(10) for y in range(x + 1, 10) if frozenset((x, y)) not in present))
    plus = mk("398-with-an-edge-added.json", l398[:250] + [plus_edge_member] + l398[251:])
    eleven = mk("398-with-an-11-vertex-member.json", l398[:397] + [l398[397] + [[9, 10], [8, 10]]])

    # accepted inputs
    expect("udenum set 74, forbidden-74.json", udenum_stats(NEW_UDENUM, F74), True, '"patterns":635')
    expect("udenum set 398, forbidden-398.json", udenum_stats(NEW_UDENUM, F398, ["--forbidden-set", "398"]), True,
           '"patterns":3875')
    expect("udfilter set 74, forbidden-74.json", udfilter_load(NEW_UDFILTER, F74), True, '"forbidden"')
    expect("udfilter set 398, forbidden-398.json", udfilter_load(NEW_UDFILTER, F398, ["-s", "398"]), True, '"forbidden"')
    # the pin
    expect("udenum set 398 given forbidden-74.json", udenum_stats(NEW_UDENUM, F74, ["--forbidden-set", "398"]), False,
           "is not the pinned")
    expect("udenum set 398 given forbidden-398.json plus a newline", udenum_stats(NEW_UDENUM, trailing,
           ["--forbidden-set", "398"]), False, "is not the pinned")
    expect("udfilter set 398 given forbidden-74.json", udfilter_load(NEW_UDFILTER, F74, ["-s", "398"]), False,
           "is not the pinned")
    expect("udfilter set 398 given forbidden-398.json plus a newline", udfilter_load(NEW_UDFILTER, trailing, ["-s", "398"]),
           False, "is not the pinned")
    expect("udenum --forbidden-set 75", udenum_stats(NEW_UDENUM, F74, ["--forbidden-set", "75"]), False, "must be 74 or 398")
    expect("udfilter -s 75", udfilter_load(NEW_UDFILTER, F74, ["-s", "75"]), False, "usage")

    # set 74 on malformed inputs: new == old, exit and message
    for name, path in (("the 398 file", F398), ("73 graphs", m73), ("81 graphs", m81), ("a duplicate edge", dup),
                       ("an order-10 member", ord10), ("unbalanced brackets", unbal)):
        for prog, new, old, run in (("udenum", NEW_UDENUM, OLD_UDENUM, udenum_stats),
                                    ("udfilter", NEW_UDFILTER, OLD_UDFILTER, udfilter_load)):
            n, o = run(new, path), run(old, path)
            same = n == o
            rows.append({"case": f"{prog} set 74 on {name}: new vs old", "new": n, "old": o, "as_required": same})
            print(f"{'ok ' if same else 'BAD'} {prog} set 74 on {name}: new exit {n[0]} '{n[1][:90]}' | "
                  f"old exit {o[0]} '{o[1][:90]}'")

    # test builds pinned to each mutated file, reaching the guards behind the pin
    for label, path, enum_needle, filt_needle in (
            ("397 graphs", m397, "does not contain 398 graphs", "does not contain 398 patterns"),
            ("a 9-vertex member in place of a 10-vertex one", nine, "does not yield 3875 deletion patterns", None),
            ("one edge added to member 250", plus, "size distribution does not match", None),
            ("an 11-vertex member", eleven, "bad forbidden edge", "order above 10")):
        pin = sha256(path)
        eb = w / f"udenum-pin-{pin[:12]}"
        subprocess.run(["nice", "-n", "10", "cc", *ENUM_FLAGS, f"-DFORBIDDEN_398_SHA256=\"{pin}\"",
                        str(UD / "enum" / "udenum.c"), "-o", str(eb), "-lnauty"], check=True)
        expect(f"udenum test build pinned to [{label}]", udenum_stats(eb, path, ["--forbidden-set", "398"]), False,
               enum_needle)
        if filt_needle:
            fb = w / f"udfilter-pin-{pin[:12]}"
            subprocess.run(["nice", "-n", "10", "cc", "-std=c17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                            f"-DUDF_FORBIDDEN_398_SHA256=\"{pin}\"", "-o", str(fb),
                            str(UD / "filter" / "udfilter.c"), str(UD / "filter" / "udfilter-cli.c")], check=True)
            expect(f"udfilter test build pinned to [{label}]", udfilter_load(fb, path, ["-s", "398"]), False, filt_needle)
        else:
            # udfilter has no pattern or distribution guard: the pinned file loads (398 graphs, orders <= 10)
            fb = w / f"udfilter-pin-{pin[:12]}"
            subprocess.run(["nice", "-n", "10", "cc", "-std=c17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                            f"-DUDF_FORBIDDEN_398_SHA256=\"{pin}\"", "-o", str(fb),
                            str(UD / "filter" / "udfilter.c"), str(UD / "filter" / "udfilter-cli.c")], check=True)
            expect(f"udfilter test build pinned to [{label}] (loads: only the pin guards content)",
                   udfilter_load(fb, path, ["-s", "398"]), True, '"forbidden"')

    ok = all(r["as_required"] for r in rows)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps({"rows": rows, "pass": ok}, indent=1) + "\n")
    print(f"{sum(r['as_required'] for r in rows)} of {len(rows)} cases as required")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
