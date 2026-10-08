# GP-10 exact-embedding index

## Files and interface

`index.py` reads the frozen `research/gp-10/cloud/lean3/records.jsonl.gz`
stream and checks that every indexed key occurs in `research/gp-10/data/B10.g6`.
It retains the small record graph in memory.  For an E-ptr it follows the
source-to-target maps to an E-exact terminal, composes those maps in that
direction, and selects the terminal coordinates in the source graph's own
canonical labelling.  Its returned value is always an ordinary `exact`
certificate; no pointer remains.

The Python interface is:

```python
from index import EmbeddingIndex

index = EmbeddingIndex()
cert = index.resolve(canonical_graph6)  # direct E-exact certificate
record = index.record(canonical_graph6) # complete embedded record
for record in index.stream():           # canonical graph6 byte order
    ...
```

The corresponding command-line operations are:

```sh
python research/gp-11/embed/index.py lookup 'I???XjI{O'
python research/gp-11/embed/index.py stream > /tmp/gp10-resolved.jsonl
python research/gp-11/embed/index.py stats
python research/gp-11/embed/test_index.py
```

No generated index is needed or committed.  Loading and resolving directly
from the 45 MiB gzip source keeps a single source of truth and takes seconds.
If a materialized compact stream is useful on a worker, the `stream` command
above rebuilds it deterministically; compress it with
`gzip -n /tmp/gp10-resolved.jsonl` if desired.

## Complete resolution

On 2026-09-30 in the supplied container, `index.py stats` produced:

```json
{"pointer_chain_lengths":{"0":3879,"1":7816,"2":9569,"3":7270,"4":3285,"5":781,"6":52,"7":1},"resolved":32653,"seconds":16.506161335}
```

Thus all **32,653 / 32,653** embedded graphs resolve.  The distribution sums
to 32,653, includes the expected 3,879 direct records and 28,774 pointers, and
has maximum pointer-chain length 7.  The all-record regression also asserted
that every result has ten points and is direct E-exact.

## Frozen-checker sample and red controls

`test_index.py` samples **1,000** distinct embedded canonical graph6 strings
using `random.Random(20261001).sample(sorted_codes, 1000)`.  Each resolved
certificate is passed to the unmodified frozen checker's `decode` and
`exact_embedding` functions.  This is precisely the sample profile's exact
certificate verification path, called directly so this lean container does
not need the checker's unrelated `python-flint`, NetworkX, and nauty
dependencies.  All 1,000 were accepted.  The entire test output was:

```text
test_all_resolve (__main__.IndexTests.test_all_resolve) ... ok
test_red_controls_and_unchanged_evidence (__main__.IndexTests.test_red_controls_and_unchanged_evidence) ... ok
test_seeded_sample_with_frozen_exact_checker (__main__.IndexTests.test_seeded_sample_with_frozen_exact_checker) ... ok

----------------------------------------------------------------------
Ran 3 tests in 119.273s

OK
```

The red-control test asserts the frozen checker's reason field, not just that
some exception occurred:

| control | exact rejection reason |
| --- | --- |
| a genuine E-ptr map changed to repeat one target vertex | `map_not_injective` |
| one coordinate's constant coefficient increased by one (still valid JSON and a valid rational) | `edge_equation` |
| the inverse of a genuine pointer permutation used in place of the source-to-target composition | `edge_equation` |

After each mutation, the original resolved E-exact evidence is submitted again
unchanged and accepted.  In particular, the coordinate control reaches the
edge-equation arithmetic: it cannot pass merely by retaining JSON parsing while
removing coordinate verification.

The environment's package mirrors returned HTTP 403 while attempting to
install optional full-run dependencies, so this run did not invoke the
checker's CLI framing/profile layer.  The tested routines are nevertheless
loaded from `research/gp-10/check/gp10check.py` itself, which remains untouched;
only modules unused by exact and map verification are stubbed at import time.
