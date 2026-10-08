"""Run udtriangle on graph6 files and write udcheck-format certificate files for the cross-check."""
import json, subprocess, sys
from pathlib import Path
UDT = "<repo>/research/unit-distance-22/filter/udtriangle"
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
for src in sys.argv[2:]:
    lines = [l for l in Path(src).read_bytes().split(b"\n") if l]
    p = subprocess.run([UDT], input=b"".join(l + b"\n" for l in lines), capture_output=True, check=True)
    verd = [json.loads(x) for x in p.stdout.split(b"\n") if x]
    assert len(verd) == len(lines)
    stem = Path(src).stem
    certs, tri_only, unknown = [], [], []
    for g, v in zip(lines, verd):
        code = g.decode()
        if v["verdict"] == "pass":
            certs.append({"g6": code, "verdict": "unknown"}); unknown.append(code)
        else:
            rec = {"g6": code, "verdict": v["verdict"], "witness": v["witness"]}
            certs.append(rec); tri_only.append(rec)
    (out / f"{stem}.certs.jsonl").write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in certs))
    (out / f"{stem}.tri.jsonl").write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in tri_only))
    (out / f"{stem}.g6").write_bytes(b"".join(l + b"\n" for l in lines))
    (out / f"{stem}.UNKNOWN.g6").write_text("".join(c + "\n" for c in unknown))
    print(stem, "graphs", len(lines), "certificates", len(tri_only), "pass", len(unknown), p.stderr.decode().strip().splitlines()[-1][:160], flush=True)
