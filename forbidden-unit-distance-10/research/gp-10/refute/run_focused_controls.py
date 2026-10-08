#!<repo>/pyenv-gp10/bin/python
"""Specified follow-up samples, aggregate requested method time below five minutes."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
from controls import main
jobs=[
 ["--suite","gp74","--method","tree","--seconds","40","--indices","59,67,69","--tag=-deep"],
 ["--suite","gp74","--method","real","--seconds","15","--indices","4,9,10,18","--tag=-focused"],
 ["--suite","gp74","--method","real","--seconds","20","--indices","17","--extra-sat","3","7","--tag=-extra"],
 ["--suite","amp","--method","real","--seconds","0.5","--tag=-final","--progress-every","20"],
 ["--suite","gp74","--method","real","--seconds","10","--indices","22,38,39,66","--all-sat","--tag=-stalls"],
]
for arguments in jobs:
    sys.argv=["controls.py",*arguments]
    main()
