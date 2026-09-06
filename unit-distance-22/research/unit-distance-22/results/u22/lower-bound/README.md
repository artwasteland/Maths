# The lower bound u(22) >= 60, as this project's own certificate

`config-22-60.certificate.jsonl` is one line of `embed/udembed.py` output on the first graph of
`sources/engel-dataset/engel-22-60.g6` (Engel's 35 known 22-point configurations with 60 unit
distances, the family AMP draw): verdict `embedded`, coordinates in Q(sqrt 3, sqrt 11) given as
polynomials in the generator x = sqrt 11 + sqrt 3 (minimal polynomial x^4 - 28 x^2 + 64, root in
[5, 6]). `check/udcheck.py --expect-m 60` accepts it (and all 25 of the 35 that the embedder
finished within the coordinator's time budget, `engel-22-60.embedded.jsonl`: records 25,
embedded 25). `config-22-60.json` is the same configuration evaluated to floats for the page,
with the 60 edges; numerically the 60 edges are unit, no other pair is (231 pairs), and the
closest two points are 0.2918 apart.
