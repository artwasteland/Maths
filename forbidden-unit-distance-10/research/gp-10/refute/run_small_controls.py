#!<repo>/pyenv-gp10/bin/python
"""Bounded required controls, total requested method time below five minutes."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import contextlib
import json
from controls import main, EVIDENCE

jobs=[("gp74","tu",0.5)]
jobs += [("named",method,3) for method in ("tu","tree","null","real")]
jobs += [("amp",method,0.5) for method in ("tu","tree","null","real")]
for suite,method,seconds in jobs:
    sys.argv=["controls.py","--suite",suite,"--method",method,"--seconds",str(seconds)]
    with (EVIDENCE/(suite+"-"+method+".log")).open("w") as log,contextlib.redirect_stdout(log):
        main()
    result=json.loads((EVIDENCE/(suite+"-"+method+".summary.json")).read_text())
    print(json.dumps({k:result[k] for k in ["suite","method","count","refuted","unknown","total_seconds"]}),flush=True)
