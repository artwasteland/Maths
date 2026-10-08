#!/usr/bin/env python3
"""Materialise the retained GP-10 evidence in a new scratch run tree; never run a heavy check.

No higher-order answers enter the certificates or forbidden list in force.
Historical reports are present solely to meet the replay prerequisite; they are rechecked.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

GP10 = Path(__file__).resolve().parents[2] / "gp-10"


def prepare(output):  # B11 harness addition.
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with tarfile.open(GP10 / "cloud/final/tree-public.tar.gz") as archive:
        # Accept only regular files/directories confined below tree/.
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] != "tree" or not (member.isfile() or member.isdir()):
                raise ValueError("unexpected control archive member: " + member.name)
        archive.extractall(output, filter="data")
    tree = output / "tree"
    with gzip.open(GP10 / "cloud/lean3/records.jsonl.gz", "rb") as source, (tree / "records.jsonl").open("wb") as target:
        shutil.copyfileobj(source, target)
    expected = (GP10 / "cloud/lean3/records.sha256").read_text().split()[0]
    digest = hashlib.file_digest((tree / "records.jsonl").open("rb"), "sha256").hexdigest()
    if digest != expected:
        raise ValueError("B10 record digest mismatch")
    (tree / "UNKNOWN.g6").write_text("")
    for path in [tree / "run.json", *sorted((tree / "controls").glob("*/run.json"))]:
        manifest = json.loads(path.read_text())
        name = Path(manifest["input"]).name
        frozen = GP10 / "data" / name
        manifest["input"] = str(frozen if frozen.exists() else path.parent / name)
        path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PREPARED {tree}")
    print(f"B10 records sha256={digest}")
    return tree


def main():  # B11 harness addition.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    main()
