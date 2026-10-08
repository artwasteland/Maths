**Round-8 finding: CLOSED.** At `0f64a5a72c`, `research/unit-distance-22/enum/verify-chain.py:1028–1034` rejects non-integer and boolean counts before sampling bounds or bindings. The additional guards at **326–332** and **893–898** prevent malformed cell identities and parent levels from entering coverage calculations.

Independent in-memory tests rejected all **22 adversarial cases**, including float/bool oversampling, zero-parent sampling, malformed target entries, and malformed parent levels recovered through history. Untouched, duplicate-copy and valid resumed-copy controls produced no additional errors.

**No new SERIOUS or FATAL findings** in the reviewed changes and interactions. The supplied fleet log correctly remains FAIL for missing slices and unresolved evidence.

Minor issues: none reported.

**G5: CLOSED**
