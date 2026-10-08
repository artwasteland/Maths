# B10, interim assembly of 2026-09-24 (NOT the result)

A `sample`-profile checker run over all 33,162 graphs of B10 with F9 in force and minimality derivation, assembled
from every certificate accepted so far (seeds validated by the official checker first). The blind checker's
verdict: `ACCEPT run verified`, 0 rejected certificates; embedded 32,519, refuted 285, unknown 358 (third assembly, ~20:30 AEST; the second had 31,919 / 247 / 996 and 105 minimal).

`L10-established-so-far.g6` holds the 122 graphs the checker derived as minimal forbidden with NO unknown
dependency: each is refuted by an accepted certificate and each of its one-edge deletions is embedded (or not
biconnected). Each of these is a minimal forbidden unit-distance graph on 10 vertices (PROOFS.md, L-min). The
Moebius ladder `Is?@WxcU?` is among them.

What this does NOT say: that the list is complete. 996 graphs are undecided (`UNKNOWN.g6`); 702 of them are
minimal among the undecided, and each of those is either another minimal forbidden graph or an undrawn
unit-distance graph. The contract's full claim needs UNKNOWN empty, the B10 profile with every control replay,
and gate G5.
