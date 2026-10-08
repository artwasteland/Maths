# Control findings

The complete GP forbidden-list coverage control is not green. The named
AMP stalls remain unknown after completed tree searches and bounded
polynomial attempts. They are H_hP`SV, H?dPdLi, HGEAXjw, and H{O_okN.
No B10 production run was started. The report derives coverage and timings
from the saved evidence and does not claim the classification question is
settled.

The tree stalls are completed searches with terminal no-move states,
not state-limit stops. Merely extending the same wall-clock budget cannot
change those fixed points. Stronger algebraic search or a stronger geometric
move is needed for this implementation. Alternate move orders have not been
exhausted, so these observations do not prove that every AMP search fails.
No new move was added or used without an amendment.

The smaller default saturation set missed a real branch with coincident
vertices in a designated regression. An explicit extra nonedge saturation
was selected for a focused R-real run. This is reported as a targeted run,
and is not a hidden per-graph exception in the producer.

The full deliberately wrong-frame prism control now passes. A genuine
exact embedding validates the proper edge frame. Changing only that frame
to a selected cross-layer nonedge, with the saturation list unchanged,
gives a unit-ideal certificate when the guard is deliberately bypassed.
The production verifier rejects it with `frame: not an edge`. The outer
soundness assertion goes red for the expected reason. This is an injected
bug fixture, not an emitted producer false refutation. Details and the
exact embedding mutation check are in `evidence/wrong-frame.json`.

During development, an incorrect Singular ideal-matrix multiplication and
SymPy coercion of flint exponents prevented certificate production. Both
were fixed before the recorded method sweeps. The wrapper now explicitly
sums the lifted products, and polynomial exponents are converted to Python
integers. The CAS negative control and coefficient mutations pass.

No soundness failure was observed in the prescribed bounded embeddable
controls. Timeout and exhausted searches remain unknown. These controls
cannot establish universal soundness or completeness.

The independent checker format document appeared during final review, but
its implementation was absent. New Sturm output was aligned to its string
variable field. Historical records were copied through export_checker.py.
Its nonempty-TU and globally indexed forbidden-list conventions still need
reconciliation with CONTRACT. No independent ACCEPT is claimed.

Final audit aggregation encountered MemoryError under the required cap after
retaining duplicate large certificate objects. The audit now keeps summary
metadata, selects the smallest existing certificate for each graph, and
streams output. Some raw polynomial certificates exceed the checker document
line-size limit. The compact combined sample is checked against that limit;
the raw per-method records remain available as mathematical evidence.

## Round 3 development controls

The first real-DAG f-only mutation test accidentally shared the target list
with the final row polynomial. Deep copying preserved that alias, so the
mutation changed both fields and rejected as a row identity error rather
than the intended final-target error. A JSON round trip now separates the
fields. The corrected one-field mutation rejects with dag_last_real.

An additional rational-spelling positive exposed that python-flint does
not directly parse the permitted spelling +1/01. The local sparse parser
now validates the contract grammar, checks the positive denominator, and
normalizes through exact Fraction before passing the value to FLINT. The
positive and the one-field zero-denominator negative now pass their tests.
These were interoperability and test-fixture issues, not accepted false
refutations. Candidate work proceeds only after the corrected tests pass.

Targeted collision saturation passed a genuine identity control and a
changed-coefficient red checked by the official checker. Its initial
discovery trials on GP indices 16 and 68 remained unknown. The ordinary
all-nonedge saturation controls for those graphs are still available; no
claim that one extra saturation pair suffices is made.
