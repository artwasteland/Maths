# Job A test evidence

These are local build/test records, not publication-gate attestations.
No full B10 or B11 replay is claimed here.

`gp10-regression.txt` records the unchanged GP-10 corpus through the wrapper.
`kernel-selftest.txt` records the unchanged kernel corpus, exact rejection texts,
and restoration of all original positive invocations.
`gp11-selftest.txt` records the new rules and the restored positive evidence.
`gate-integration.txt` exercises the actual B11 dispatch against a fixture freeze.
`small-controls.txt` records the sequential local control verdicts.
`minimality-search.txt` records the untrusted bounded deletion-certificate search.

`control-reports/` contains the actual small-control reports from their initial
local replay. Each report retains that invocation's source hashes and environment.
The wrapper received further receipt/type/path guards and an AMP source pin after
that replay. Legacy mathematical decisions still delegate to the frozen runner.
The final own-rule suite rechecks the new named11 certificates.
The B11 control gate will replay all controls with the final profile.

`build-manifest.json` records the final source and file hashes, interpreter
environment, test commands and outstanding work. Its hash map excludes itself.
It does not attest a commit, a full B10 replay, prediction chronology, G0 or G5.
