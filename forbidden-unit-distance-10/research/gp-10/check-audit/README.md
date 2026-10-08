# CHECKAUDIT

[REPORT.md](REPORT.md) contains the verdict, every exact checker output, the code review and the remaining uncertainties. [cases/index.json](cases/index.json) describes each fixture and its positive parent. [cases/results.json](cases/results.json) records observed results.

Use the required interpreter, niceness and memory limit. Run each block separately from the repository root:

```sh
ulimit -v 1000000
exec nice -n 15 env SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1 <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/build_cases.py
```

```sh
ulimit -v 1000000
exec nice -n 15 env SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1 <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/audit.py --all
```

```sh
ulimit -v 1000000
exec nice -n 15 env SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1 <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/make_report.py
```

```sh
ulimit -v 1000000
exec nice -n 15 env SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1 <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/verify_deliverables.py
```

Replace `--all` with `--case NAME` to replay one case and its accepted parent. Single-case replay refreshes that case's evidence; rerun the full suite and report generator before publishing an aggregate report after changes.

The harness invokes the original checker in-process, permitting just one external nauty child at a time. The retained runner redirects scratch and bytecode writes without modifying verification logic. Its ordinary CLI can also replay any run fixture directly, using `--output /tmp/gp10-checkaudit/manual` under the same wrapper. Full production runs are outside this audit.
