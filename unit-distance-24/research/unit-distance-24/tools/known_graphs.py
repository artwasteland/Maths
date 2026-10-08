#!/usr/bin/env python3
"""Faithful Engel graphs as a streaming control of the (24,69) enumeration.

slice RUN --out FILE records zero-based indices into each pinned Engel file.
fleet FILE... [--complete] checks the union and uniqueness across slices.
--self-test plants faults, asserts their rule's exact text, and rechecks clean evidence.

An eligible graph at (n,m), of minimum degree d >= k(n,m), has a canonical
parent at (n-1,m-d). L4 admits this degree (d <= floor(2m/n)), assigns the
parent k <= max(0,d-1), and deletion leaves minimum degree >= max(0,d-1).
The maximum with zero also covers deletion of an isolated vertex.
The parent's edges obey u-bar because it is an induced unit-distance graph.
Induction reaches the exhaustive seeds through the unique level-12 ancestor.
Faithfulness is inherited by induced subgraphs, so neither a forbidden nor
a forced-extra-unit-edge certificate can prune these graphs or their ancestors.
This is membership in the search tree, not a claim of extension to (24,69).

Only the small Engel sets and their matched indices live in memory.
No graph library, canonicalisation subprocess, or production checker is used.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile

DATA = Path(__file__).resolve().parents[2] / "unit-distance-22/sources/engel-dataset"
SCHEMA = "u24-known-graphs-v1"
PINS = {
    # Reviewed dataset, never learned from a receipt.
    'engel-16-35.g6': '3a57f3ce6647983d4ade7b51bfdbb557fb5aef73e8d3a76741a560e1d80562a4',
    'engel-16-36.g6': '227aa5f0d051c443a7c493c93b7c67b7d679361aab287109214facdd0a079c5b',
    'engel-16-37.g6': '9bdf80c8c87d73f80774291484c7b501c98b3784c3fdfdab9dd95a549bd01a5b',
    'engel-16-38.g6': '43e86929bca3f1f8c4d88186c0447da1731e26d3bf6540c9fb19c5ae2326161f',
    'engel-16-39.g6': '820b5ba811530629082d0cafd5693ff4e059c810c182bb85e9a075e519d24aad',
    'engel-16-40.g6': 'eebd764b8a3d49128fdfe6dc571d51cb9836058a5ec51ac76a6c9a732da1ee19',
    'engel-16-41.g6': 'd46961deb17048d30b957dc94d10059f43771e36dad4565ec0f297e86e6c0979',
    'engel-17-39.g6': '529be5a1a8ded6326c8fe99f2124e6bb3abcac24cb068bb79cf7c981dd0a5747',
    'engel-17-40.g6': 'b4fd35dc03348f034b30110ea459242288929ffc84337bdb9a3d0a76547dfc4b',
    'engel-17-41.g6': '1c0b09fa3ab12526c40c2292eb2bbb19d00a9ee5fa67aeba51cbc3094019f638',
    'engel-17-42.g6': '359527739e04bd9cac09b0bac1e82c3823e5e22e97a09393ab83e0514e111d2c',
    'engel-17-43.g6': 'c847b40fe601d5a0f0437e854ac4b383a6b7445d2c10c7ba7c64e7621d03d29b',
    'engel-18-42.g6': '131b3b159a34aa7710c4ed83a474f249f5cdac7be65f9836916c503e065e5ed0',
    'engel-18-43.g6': '70d0459763e57a9a6553876893054e13ceacb37db1b56a1ffe19dee18ec45de5',
    'engel-18-44.g6': '8ff551d64c07f52e666cbc36e6d3b664f4772093be2a862de69d4a5ce01108d0',
    'engel-18-45.g6': '2b21bf5473bea55557ef6abf4f0cab36278ff98d8a45a2841f29eb74a478a7eb',
    'engel-18-46.g6': '3247dfba24336ffd72531bbdf711b088a662e8f3d45853dcab623c56439607f5',
    'engel-19-46.g6': 'c651d54e3d216e88afc6f83f1b01ab16c4dbb87f81013cab9917eff529a93cb7',
    'engel-19-47.g6': '52be94439b075cdc986a1f775292f3333949a6a2ce0f21b21aebb846b954f46e',
    'engel-19-48.g6': 'd82261912c25903bb4d14c689f4b7d7942ce771f905c355c0b1c8d7f6fd5b304',
    'engel-19-49.g6': '681785405ad628e6a7a842a899b49c731b64b0cd3653d3298b5079427302b275',
    'engel-19-50.g6': '811cf3a614a3c7d50ac88ee432eb9b3132986b8fb93d2d2e09d8fee0a7a02fdf',
    'engel-20-51.g6': '95b0df340b827db0bd9338c3c90ffe5c1c6cb874e85a715ad645ce516c44f81d',
    'engel-20-52.g6': '20a6506b920064792ca6bfd1040ba5c3ce6a0e3f037a44eb1b9b577c9be6a778',
    'engel-20-53.g6': '2175ee3c2f23d81fcc010bdf38078c83e918e85ce6839d486eddf35dc3217694',
    'engel-20-54.g6': '08e9a8a16cea095057468c9d9dce1b92c1ec03298a896451c93a6077c7827a31',
    'engel-21-56.g6': '530da401c836d1aece525f63a45a9cf1c33dfd6b4e7e22827ba5fa5c74782013',
    'engel-21-57.g6': '06f0d779a598292e6be4e2758097d7e0a1c2364fc348cda7d197751ed2a98aff',
    'engel-22-60.g6': 'c85de7632fbf2513e96405295a0afdd4c67ce25de1d8ba56474c1ed8514c01e6',
}
UBAR = [0, 0, 1, 3, 5, 7, 9, 12, 14, 18, 20, 23, 27, 30, 33, 37, 41, 43,
        46, 50, 54, 57, 60, 64, 72]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def production_table() -> dict:
    table = {24: {69: 5}}
    for n in range(23, 9, -1):
        level = {}
        for cm, k in table[n + 1].items():
            for d in range(k, min(n, 2 * cm // (n + 1)) + 1):
                m = cm - d
                if 0 <= m <= UBAR[n]:
                    level[m] = min(level.get(m, d), max(0, d - 1))
        table[n] = level
    return {str(n): {str(m): k for m, k in sorted(level.items())}
            for n, level in sorted(table.items())}


def production_reach(reach: dict) -> None:
    expected = {"target": [24, 69], "seed_n": 10, "root_k": 5, "table": production_table()}
    recorded = {key: reach.get(key) for key in expected}
    if json.dumps(recorded, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("CONFIG: not the production (24,69) reach table with seed 10 and root k 5")


def records(path: Path):
    with path.open("rb") as stream:
        for i, raw in enumerate(stream):
            if not raw.endswith(b"\n"):
                raise ValueError(f"FILE {path.name}: missing final newline at record {i}")
            code = raw[:-1]
            if not code or not code.isascii():
                raise ValueError(f"FILE {path.name}: empty or non-ASCII record {i}")
            yield code


def graph_stats(code: bytes) -> tuple[int, int, int]:
    n = code[0] - 63
    bits = n * (n - 1) // 2
    if not 0 <= n <= 62 or len(code) != 1 + (bits + 5) // 6 or any(c < 63 or c > 126 for c in code):
        raise ValueError("DATASET: invalid graph6 record")
    degrees, offset = [0] * n, 0
    for j in range(1, n):
        for i in range(j):
            if (code[1 + offset // 6] - 63) & (1 << (5 - offset % 6)):
                degrees[i] += 1
                degrees[j] += 1
            offset += 1
    return n, sum(degrees) // 2, min(degrees, default=0)


def catalogue() -> dict:
    table, cells = production_table(), {}
    if {p.name for p in DATA.glob("engel-*.g6")} != set(PINS):
        raise ValueError("DATASET: Engel file names differ from the pinned set")
    for name, pin in sorted(PINS.items()):
        path = DATA / name
        if digest(path) != pin:
            raise ValueError(f"DATASET {name}: sha256 differs from pin")
        _, ns, ms = path.stem.split("-")
        n, m = int(ns), int(ms)
        if ms not in table.get(ns, {}):
            continue
        k = table[ns][ms]
        codes, eligible = {}, set()
        for index, code in enumerate(records(path)):
            gn, gm, d = graph_stats(code)
            if (gn, gm) != (n, m) or code in codes:
                raise ValueError(f"DATASET {name}: wrong cell or duplicate at index {index}")
            codes[code] = index
            if d >= k:
                eligible.add(index)
        cells[f"{n}-{m}"] = {"k": k, "dataset": {"file": name, "sha256": pin, "records": len(codes)},
                              "eligible": len(eligible), "codes": codes, "eligible_indices": eligible}
    return cells


def metadata(cell: dict) -> dict:
    return {key: cell[key] for key in ("k", "dataset", "eligible")}


def soundness(name: str, found: dict, eligible: set) -> list[str]:
    problems = []
    lost = sorted((found["full"] & eligible) - found["reach"])
    if lost:
        problems.append(f"REACH {name}: eligible Engel indices in full but not reach: {lost}")
    lost = sorted(found["reach"] - found["keep"])
    if lost:
        problems.append(f"PRUNED {name}: Engel indices in reach but not keep: {lost}")
    return problems


def slice_control(run: Path, cells: dict) -> dict:
    config = json.loads((run / "run-config.json").read_text())
    reach = json.loads((run / "reach.json").read_text())
    s = config.get("slice")
    production_reach(reach)
    if config.get("target") != [24, 69] or config.get("seed_n") != 10:
        raise ValueError("CONFIG: not the production (24,69) reach table with seed 10 and root k 5")
    if (not isinstance(s, list) or len(s) != 3 or s[0] != 12 or s[2] != 1920
            or type(s[1]) is not int or not 0 <= s[1] < 1920):
        raise ValueError("CONFIG: not a slice of 1920 at level 12")
    out = {"schema": SCHEMA, "target": [24, 69], "slice": s, "run": str(run.resolve()),
           "reach_sha256": digest(run / "reach.json"),
           "run_config_sha256": digest(run / "run-config.json"), "cells": {}, "problems": []}
    for name, cell in cells.items():
        row, found = {**metadata(cell), "files": {}}, {}
        for stage, suffix in (("full", ".g6"), ("reach", ".reach.g6"), ("keep", ".keep.g6")):
            path, hits, count = run / (name + suffix), set(), 0
            if path.is_file():
                for code in records(path):
                    count += 1
                    index = cell["codes"].get(code)
                    if index is not None:
                        hits.add(index)
                row["files"][stage] = {"name": path.name, "records": count, "indices": sorted(hits)}
            else:
                row["files"][stage] = None
                out["problems"].append(f"FILE {path.name}: required production stage file is missing")
            found[stage] = hits
        out["cells"][name] = row
        out["problems"].extend(soundness(name, found, cell["eligible_indices"]))
    out["result"] = "FAIL" if out["problems"] else "OK"
    return out


def receipt_sets(receipt: dict, cells: dict) -> dict:
    if receipt.get("schema") != SCHEMA or receipt.get("target") != [24, 69]:
        raise ValueError("RECEIPT: wrong schema or target")
    s = receipt.get("slice")
    if (not isinstance(s, list) or len(s) != 3 or s[0] != 12 or s[2] != 1920
            or type(s[1]) is not int or not 0 <= s[1] < 1920):
        raise ValueError("RECEIPT: invalid slice")
    if set(receipt["cells"]) != set(cells):
        raise ValueError("RECEIPT: cell set differs from the production catalogue")
    sets = {}
    for name, cell in cells.items():
        row = receipt["cells"][name]
        if metadata(row) != metadata(cell):
            raise ValueError(f"RECEIPT {name}: dataset pin, count or eligibility differs")
        found = {}
        for stage, suffix in (("full", ".g6"), ("reach", ".reach.g6"), ("keep", ".keep.g6")):
            f = row["files"][stage]
            if f is None:
                raise ValueError(f"RECEIPT {name}: required {stage} file record is missing")
            indices = f["indices"]
            if (f["name"] != name + suffix or type(f["records"]) is not int or f["records"] < len(indices)
                    or any(type(i) is not int or not 0 <= i < cell["dataset"]["records"] for i in indices)
                    or indices != sorted(set(indices))):
                raise ValueError(f"RECEIPT {name}: invalid {stage} indices or file")
            found[stage] = set(indices)
        sets[name] = found
    return sets


def fleet_control(receipts: list[dict], cells: dict, complete: bool = False) -> dict:
    problems, seen, union = [], {}, {name: {} for name in cells}
    for receipt in receipts:
        try:
            sets = receipt_sets(receipt, cells)
            index = receipt["slice"][1]
            if index in seen:
                problems.append(f"DUPLICATE SLICE: {index}")
                continue
            seen[index] = receipt
            if receipt.get("result") != "OK" or receipt.get("problems") != []:
                problems.append(f"RECEIPT slice {index}: slice control did not pass")
            for name, found in sets.items():
                eligible = cells[name]["eligible_indices"]
                problems.extend(soundness(name, found, eligible))
                for i in sorted(found["keep"] & eligible):
                    if i in union[name]:
                        problems.append(f"PARTITION {name}: eligible Engel index {i} kept in slices {union[name][i]} and {index}")
                    else:
                        union[name][i] = index
        except (KeyError, TypeError, ValueError) as error:
            problems.append(str(error))
    if not receipts:
        problems.append("RECEIPT: no slices supplied")
    if complete:
        if set(seen) != set(range(1920)):
            problems.append(f"COMPLETE: {len(seen)} of 1920 slices present")
        for name, cell in cells.items():
            missing = sorted(cell["eligible_indices"] - union[name].keys())
            if missing:
                problems.append(f"MISSING {name}: {len(missing)} eligible Engel forms not kept (first indices {missing[:12]})")
    return {"schema": SCHEMA, "mode": "fleet", "complete": complete, "slices": len(seen),
            "cells": {name: {"eligible": cell["eligible"], "found": len(union[name])} for name, cell in cells.items()},
            "problems": problems, "result": "FAIL" if problems else "OK"}


def verdict(out: dict) -> str:
    if out["result"] == "FAIL":
        return f"KNOWN-GRAPHS FAIL: {len(out['problems'])} problem(s)"
    if out.get("mode") == "fleet":
        found = sum(c["found"] for c in out["cells"].values())
        total = sum(c["eligible"] for c in out["cells"].values())
        scope = "complete" if out["complete"] else "coverage only; missing forms not judged"
        return f"KNOWN-GRAPHS OK: {out['slices']}/1920 slices, {found}/{total} eligible forms kept ({scope})"
    matches = sum(len(c["files"]["keep"]["indices"]) for c in out["cells"].values() if c["files"]["keep"])
    return f"KNOWN-GRAPHS OK: slice {out['slice'][1]} of 1920, {len(out['cells'])} cells, {matches} Engel forms kept"


def self_test(cells: dict) -> None:
    name, cell = next((n, c) for n, c in cells.items() if c["eligible_indices"])
    index = min(cell["eligible_indices"])
    code = next(code for code, i in cell["codes"].items() if i == index)
    with tempfile.TemporaryDirectory(prefix="u24-known-red-") as tmp:
        run = Path(tmp)
        (run / "reach.json").write_text(json.dumps({"target": [24, 69], "seed_n": 10,
                                                  "root_k": 5, "table": production_table()}))
        (run / "run-config.json").write_text(json.dumps({"target": [24, 69], "seed_n": 10, "slice": [12, 0, 1920]}))
        for cell_name in cells:
            for suffix in (".g6", ".reach.g6", ".keep.g6"):
                (run / (cell_name + suffix)).touch()
        for suffix in (".g6", ".reach.g6", ".keep.g6"):
            (run / (name + suffix)).write_bytes(code + b"\n")
        clean = slice_control(run, cells)
        assert clean["result"] == "OK"
        for stage, rule, detail in (("reach", "REACH", "eligible Engel indices in full but not reach"),
                                    ("keep", "PRUNED", "Engel indices in reach but not keep")):
            path = run / f"{name}.{stage}.g6"
            original = path.read_bytes()
            try:
                path.write_bytes(b"")
                red = slice_control(run, cells)
                text = f"{rule} {name}: {detail}: [{index}]"
                assert red["result"] == "FAIL" and red["problems"] == [text], red
                print("SELF-TEST red: FAIL:", text)
            finally:
                path.write_bytes(original)
            assert slice_control(run, cells) == clean
        base = fleet_control([clean], cells)
        assert base["result"] == "OK"
        other = copy.deepcopy(clean)
        other["slice"][1] = 1
        badpin = copy.deepcopy(clean)
        badpin["cells"][name]["dataset"]["sha256"] = "0" * 64
        cases = [([clean, other], False, f"PARTITION {name}: eligible Engel index {index} kept in slices 0 and 1"),
                 ([clean, clean], False, "DUPLICATE SLICE: 0"),
                 ([badpin], False, f"RECEIPT {name}: dataset pin, count or eligibility differs"),
                 ([clean], True, "COMPLETE: 1 of 1920 slices present")]
        # All slice identities are present; a missing form must fail its own rule.
        empty = copy.deepcopy(clean)
        for row in empty["cells"].values():
            for f in row["files"].values():
                f.update(records=0, indices=[])
        full = []
        for i in range(1920):
            r = dict(empty, slice=[12, i, 1920])
            full.append(r)
        complete_positive = copy.deepcopy(empty)
        for cell_name, c in cells.items():
            indices = sorted(c["eligible_indices"])
            complete_positive["cells"][cell_name]["files"] = {
                stage: {"name": cell_name + suffix, "records": len(indices), "indices": indices}
                for stage, suffix in (("full", ".g6"), ("reach", ".reach.g6"), ("keep", ".keep.g6"))}
        positive_fleet = [complete_positive, *full[1:]]
        complete_base = fleet_control(positive_fleet, cells, True)
        assert complete_base["result"] == "OK"
        cases.append((full, True, f"MISSING {name}: {cell['eligible']} eligible Engel forms not kept (first indices {sorted(cell['eligible_indices'])[:12]})"))
        for receipts, complete, text in cases:
            red = fleet_control(receipts, cells, complete)
            assert red["result"] == "FAIL" and text in red["problems"], red
            print("SELF-TEST red: FAIL:", text)
            assert fleet_control([clean], cells) == base
            assert slice_control(run, cells) == clean
        assert fleet_control(positive_fleet, cells, True) == complete_base
        print("SELF-TEST green: complete synthetic fleet covers every eligible form exactly once")
    print("KNOWN-GRAPHS SELF-TEST OK: 7 rule-specific red controls; clean evidence restored after each")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="mode")
    sp = sub.add_parser("slice")
    sp.add_argument("run", type=Path)
    sp.add_argument("--out", type=Path, required=True)
    fp = sub.add_parser("fleet")
    fp.add_argument("receipts", type=Path, nargs="+")
    fp.add_argument("--complete", action="store_true")
    fp.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = None
    try:
        cells = catalogue()
        if a.self_test:
            self_test(cells)
            return 0
        if a.mode == "slice":
            out = slice_control(a.run, cells)
            for name, row in out["cells"].items():
                print(f"{name}: " + ", ".join(f"{stage} {f['records']} records" if f else f"{stage} MISSING"
                                             for stage, f in row["files"].items()))
        elif a.mode == "fleet":
            out = fleet_control([json.loads(p.read_text()) for p in a.receipts], cells, a.complete)
            for name, row in out["cells"].items():
                print(f"{name}: eligible {row['eligible']} / found {row['found']}")
        else:
            ap.error("choose slice, fleet or --self-test")
    except (OSError, ValueError, KeyError, TypeError) as error:
        out = {"schema": SCHEMA, "result": "FAIL", "problems": [str(error)]}
    if getattr(a, "out", None):
        a.out.write_text(json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n")
    for problem in out["problems"]:
        print("FAIL:", problem)
    print(verdict(out))
    return 0 if out["result"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
