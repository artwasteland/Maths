# The judged u(24) fleet, 2026-10-06

`judge.py` run once per published plan (pilot, full, phase B, repro) on one snapshot of the fleet, taken
2026-10-06T19:40:25Z: every branch `claude/answering-alexeev-u22-cloud-u24-*` and `claude/answering-alexeev-u22-codex-u24-*`
on GitHub (286 branches, `sources.tsv`: branch, fetched commit, advertised commit), each branch's
`research/unit-distance-24/results/u24` extracted into its own directory. Plans and judge at commit 8f2a97fa698 (Liam's
amendment of the full plan); `judge.py` sha256 1fa97e93b0d240d2bb4fdc2325905612cece12293e21db2798d9b5e2c5ac1101; the checker `verify-chain-u24.py` sha256 a231bfc384702231f57fc21461b4c700ec8eed842bceb981076963c79d2cc86a (both unchanged since).

| plan | started (UTC) | finished (UTC) | output |
|---|---|---|---|
| pilot | 2026-10-06T19:40:35Z | 2026-10-06T19:49:26Z | `judge-pilot.json.gz`, `judge-pilot.txt.gz` |
| full | 2026-10-06T19:49:26Z | 2026-10-06T20:37:39Z | `judge-full.json.gz`, `judge-full.txt.gz` |
| phase B | 2026-10-06T20:37:39Z | 2026-10-06T20:45:00Z | `judge-phaseb.json.gz`, `judge-phaseb.txt.gz` |
| repro | 2026-10-06T20:45:00Z | 2026-10-06T20:53:37Z | `judge-repro.json.gz`, `judge-repro.txt.gz` |

Each exited 0 with `JUDGE OK`. To reproduce: fetch each branch of `sources.tsv` at its commit, extract
`research/unit-distance-24/results/u24` from it into `ROOT/<suffix>` (the branch name after `cloud-u24-`, or
`codex-` plus the name after `codex-u24-`), then for each plan:

```
python3 -B research/unit-distance-24/tools/judge.py ROOT --plan coordination/cloud-workers/u24-PLAN-plan.json --out PLAN.json
```

The fleet-wide summary audit over the union of the pilot, full and phase-B plans' accepted copies is
`research/unit-distance-24/tools/fleet_audit.py ROOT --out fleet-audit.json`. Run on the same snapshot
2026-10-06T22:04:00Z to 22:57:45Z: `fleet-audit.json`, `fleet-audit.txt`, verdict OK (pilot 42 slices / 44 copies,
full 1,841 / 1,842, phase B 37 / 37; union 1,923 copies of all 1,920 slices; `COVERAGE (summary only) OK`, status
complete). The wrapper's own rules are red-tested in `tools/test_fleet_audit.py`.
