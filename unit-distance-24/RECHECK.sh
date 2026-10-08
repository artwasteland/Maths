#!/bin/sh
# CHECKER_PYTHON may select an already installed Python 3.12 environment.
set -eu
cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v "${CHECKER_PYTHON:-python3}" >/dev/null 2>&1; then
  echo 'Python interpreter unavailable'
  echo FAIL
  exit 1
fi
exec nice -n 19 "${CHECKER_PYTHON:-python3}" -u -I -B ./recheck.py "$@"
