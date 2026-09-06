#!/usr/bin/env python3
"""Required green and deliberately red certificate checks."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "chiro"))
sys.path.insert(0, str(HERE))
from controls import FANO, PAPPUS  # noqa: E402
from check_realization import check_record  # noqa: E402
from realize import decide  # noqa: E402


def main() -> int:
    real = decide(PAPPUS)
    no_real = decide(FANO)
    green_real = check_record(PAPPUS, real)
    green_no_real = check_record(FANO, no_real)

    mutated_coordinate = copy.deepcopy(real)
    frame_corner = mutated_coordinate["construction"]["frame"][3]
    mutated_coordinate["witness"]["points"][frame_corner][0] = "2"
    red_coordinate = check_record(PAPPUS, mutated_coordinate)

    mutated_ideal = copy.deepcopy(no_real)
    mutated_ideal["witness"]["ideal_blocks"].pop()
    red_ideal = check_record(FANO, mutated_ideal)

    result = {
        "green_real": {"accepted": green_real[0], "detail": green_real[1]},
        "green_no_realization": {"accepted": green_no_real[0], "detail": green_no_real[1]},
        "red_mutated_coordinate": {"accepted": red_coordinate[0], "detail": red_coordinate[1]},
        "red_dropped_ideal_block": {"accepted": red_ideal[0], "detail": red_ideal[1]},
    }
    passed = green_real[0] and green_no_real[0] and not red_coordinate[0] and not red_ideal[0]
    result["passed"] = passed
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
