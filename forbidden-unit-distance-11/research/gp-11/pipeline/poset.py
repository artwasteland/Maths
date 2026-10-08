"""Read-only, memory-mapped deletion order with both adjacency directions."""
from common import *
import fcntl
import subprocess
import numpy as np

ROW = np.dtype([("parent", "<u4"), ("child", "<u4"), ("map", "u1", (11,))])
FILES = ("relations.bin", "down.u32", "up.u32", "reverse.u32", "edges.u8", "tu.so")


def build(directory, guard):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (directory / "index.json").exists():
            return Poset(directory)
        if digest(B11) != B11_SHA:
            raise ValueError("frozen_B11_hash")
        guard.check()
        started = time.monotonic()
        filt = ROOT / "research/unit-distance-22/filter"
        subprocess.run(["cc", "-O3", "-Wall", "-Wextra", str(HERE / "poset.c"),
                        "-lnauty", "-o", str(directory / "poset-build")], check=True)
        subprocess.run(["cc", "-O3", "-Wall", "-Wextra", "-fPIC", "-shared", "-I", str(filt),
                        str(HERE / "tu.c"), str(filt / "udfilter.c"), "-o", str(directory / "tu.so")], check=True)
        subprocess.run([str(directory / "poset-build"), str(B11), str(directory / "relations.bin")], check=True)
        guard.check()
        rows = np.memmap(directory / "relations.bin", dtype=ROW, mode="r")
        if len(rows) != 4721083:
            raise ValueError("relation_count")
        for field, name in (("parent", "down.u32"), ("child", "up.u32")):
            counts = np.bincount(rows[field], minlength=448708)
            offsets = np.concatenate(([0], np.cumsum(counts))).astype("<u4")
            offsets.tofile(directory / name)
        # Stable sorting fixes the order when a child has several parents.
        np.argsort(rows["child"], kind="stable").astype("<u4").tofile(directory / "reverse.u32")
        np.array([sum((c-63).bit_count() for c in code[1:])
                  for code in B11.read_bytes().splitlines()], dtype="u1").tofile(directory / "edges.u8")
        paths = [HERE / "poset.c", HERE / "tu.c", filt / "udfilter.c", filt / "udfilter.h"]
        receipt = {"population_sha256": B11_SHA, "vertices": 448708, "relations": len(rows),
                   "format": "little-endian parent:u32,child:u32,child_to_parent:11*u8",
                   "sources": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                   "files": {name: digest(directory / name) for name in FILES},
                   "seconds": time.monotonic()-started, "minimum_available_kib": guard.minimum_kib}
        write_json(directory / "index.json", receipt)
    return Poset(directory)


class Poset:
    def __init__(self, directory):
        self.directory = Path(directory)
        receipt = json.loads((self.directory / "index.json").read_text())
        if receipt["population_sha256"] != B11_SHA or digest(B11) != B11_SHA:
            raise ValueError("frozen_B11_hash")
        for name, expected in receipt["files"].items():
            if digest(self.directory / name) != expected:
                raise ValueError("index_artifact_hash:" + name)
        for name, expected in receipt["sources"].items():
            if digest(ROOT / name) != expected:
                raise ValueError("index_source_hash:" + name)
        self.codes = B11.read_text().splitlines()
        self.ids = {code: i for i, code in enumerate(self.codes)}
        self.rows = np.memmap(self.directory / "relations.bin", dtype=ROW, mode="r")
        self.down = np.memmap(self.directory / "down.u32", dtype="<u4", mode="r")
        self.up = np.memmap(self.directory / "up.u32", dtype="<u4", mode="r")
        self.reverse = np.memmap(self.directory / "reverse.u32", dtype="<u4", mode="r")
        self.edges = np.memmap(self.directory / "edges.u8", dtype="u1", mode="r")

    def neighbours(self, gid, verdict):
        if verdict == "embedded":
            for i in range(int(self.down[gid]), int(self.down[gid+1])):
                row = self.rows[i]
                yield int(row["child"]), row["map"].tolist()
        else:
            for i in self.reverse[self.up[gid]:self.up[gid+1]]:
                row = self.rows[i]
                yield int(row["parent"]), row["map"].tolist()


def validate(poset, codes):
    # Different graph operations reproduce complete neighbour sets, not only counts.
    from graph6 import decode_graph6, iter_edges, remove_edge, canonicalize
    count = 0
    for code in codes:
        gid = poset.ids[code]
        n, mask = decode_graph6(code)
        expected = {poset.ids[c.g6] for a, b in iter_edges(n, mask)
                    if (c := canonicalize(n, remove_edge(n, mask, a, b))).g6 in poset.ids}
        actual = list(poset.neighbours(gid, "embedded"))
        if expected != {child for child, _ in actual}:
            raise ValueError("poset_neighbour_set")
        parent_edges = set(iter_edges(n, mask))
        for child, mapping in actual:
            cn, cm = decode_graph6(poset.codes[child])
            if sorted(mapping) != list(range(11)) or any(tuple(sorted((mapping[a], mapping[b]))) not in parent_edges
                                                       for a, b in iter_edges(cn, cm)):
                raise ValueError("poset_edge_map")
            if not any(parent == gid and reverse == mapping for parent, reverse in poset.neighbours(child, "refuted")):
                raise ValueError("poset_reverse")
            count += 1
    return {"parents": len(codes), "relations": count, "status": "PASS"}
