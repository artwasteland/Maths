#!<repo>/pyenv-gp10/bin/python
"""Copy historical local records into a checker sample using its published Sturm field."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse
import copy
import hashlib
import json
from pathlib import Path
from gp10refute import configure,verify,timed
configure()
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("input",type=Path)
p.add_argument("--out-dir",type=Path,required=True)
a=p.parse_args()
records=[json.loads(s) for s in a.input.read_text().splitlines()]
changed=0
for record in records:
    cert=record["cert"]
    if cert.get("type")=="real" and isinstance(cert.get("sturm"),dict):
        name=cert["sturm"]["variable"]
        cert["sturm"]=name[0]+"_"+name[1:]
        changed+=1
    if cert.get("type")=="tu":
        raise ValueError("TU list-index and endpoint policy needs explicit run reconciliation")
    if record["verdict"]=="refuted":
        with timed(30):verify(record["g6"],cert,[],{})
codes=sorted(r["g6"] for r in records)
assert len(codes)==len(set(codes))
a.out_dir.mkdir(parents=True,exist_ok=True)
input_path=a.out_dir/"input.g6"
input_path.write_text("\n".join(codes)+"\n")
(a.out_dir/"records.jsonl").write_text("\n".join(json.dumps(r,sort_keys=True) for r in records)+"\n")
unknown=sorted(r["g6"] for r in records if r["verdict"]=="unknown")
(a.out_dir/"UNKNOWN.g6").write_text("\n".join(unknown)+("\n" if unknown else ""))
manifest={"profile":"sample","input":"input.g6","input_sha256":hashlib.sha256(input_path.read_bytes()).hexdigest(),
          "records":["records.jsonl"],"unknown":"UNKNOWN.g6","forbidden_limit":0}
(a.out_dir/"run.json").write_text(json.dumps(manifest,indent=2)+"\n")
result={"records":len(records),"converted_sturm":changed,"unknown":len(unknown),"local_replay":"PASS",
        "independent_checker_run":False,"argv":sys.argv}
(a.out_dir/"export.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
