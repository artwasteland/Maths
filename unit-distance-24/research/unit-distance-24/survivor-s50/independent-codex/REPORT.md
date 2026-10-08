Independent blind check: G is refuted by all 12 supplied records.

G has 24 vertices and 69 edges. Its descending degree sequence is six 7s, six 6s, and twelve 5s. In graph6 vertex order, vertices 0–11 have degree 5, 12–17 degree 6, and 18–23 degree 7.

The independent decoder uses the triangular graph6 bit index v(v−1)/2+u. For G and every record, its exact labelled edge set and vertex order agree with NetworkX and frozen udcheck.py. All record graphs have 11 vertices and 18 edges.

The custom exhaustive backtracking search in [blind_check.py](blind_check.py) considers every injective map with necessary degree and required-edge support pruning. It imposes no nonedge constraints. NetworkX VF2 monomorphism independently agrees for every record. Each saved mapping was reread and verified independently using NetworkX edge tests and an injectivity test. All 12 searches returned a witness.

Arrays below list G-images of H vertices 0 through 10. Record IDs abbreviate packet-<ID>.record.jsonl. Every original record printed both `ACCEPT record <g6> verified` and `ACCEPT run verified`, returned exit code 0, and recorded one refuted graph with no unknowns.

| Record ID | Map H → G | Embeds | Checker |
|---|---|---|---|
| [15279f0a55ad52f0](mappings/packet-15279f0a55ad52f0.record.jsonl.json) | [19,3,20,8,2,7,16,10,18,1,12] | Yes | ACCEPT |
| [45b8802d634afbe1](mappings/packet-45b8802d634afbe1.record.jsonl.json) | [3,2,13,10,20,1,8,19,22,18,12] | Yes | ACCEPT |
| [59fde588c0e2cb35](mappings/packet-59fde588c0e2cb35.record.jsonl.json) | [3,2,20,8,9,19,16,1,10,18,12] | Yes | ACCEPT |
| [603e3f224057a753](mappings/packet-603e3f224057a753.record.jsonl.json) | [3,13,2,18,0,22,5,14,15,8,11] | Yes | ACCEPT |
| [60f3da386a6c5278](mappings/packet-60f3da386a6c5278.record.jsonl.json) | [3,1,0,8,10,11,13,2,12,19,18] | Yes | ACCEPT |
| [6ff822fba1454815](mappings/packet-6ff822fba1454815.record.jsonl.json) | [3,13,22,11,8,5,18,2,4,0,14] | Yes | ACCEPT |
| [7443a07840cf012e](mappings/packet-7443a07840cf012e.record.jsonl.json) | [18,8,14,2,9,3,4,0,13,19,11] | Yes | ACCEPT |
| [a5561d906d5f885d](mappings/packet-a5561d906d5f885d.record.jsonl.json) | [3,20,8,11,2,13,18,0,4,22,14] | Yes | ACCEPT |
| [d06d4b5c19186a03](mappings/packet-d06d4b5c19186a03.record.jsonl.json) | [19,8,10,22,13,2,3,7,1,12,18] | Yes | ACCEPT |
| [de51b4d793f401e4](mappings/packet-de51b4d793f401e4.record.jsonl.json) | [3,13,23,14,5,0,8,2,22,18,4] | Yes | ACCEPT |
| [e38aa6135774612c](mappings/packet-e38aa6135774612c.record.jsonl.json) | [0,2,3,20,22,8,9,18,19,12,13] | Yes | ACCEPT |
| [eb71dfb2a5394584](mappings/packet-eb71dfb2a5394584.record.jsonl.json) | [19,3,10,6,21,8,2,23,1,18,12] | Yes | ACCEPT |

The damaged control changes exactly one byte of packet-45b8802d634afbe1.record.jsonl: `cert.sos.c = "1/2"` becomes `"1/3"`. The checker returned exit code 1 and printed `REJECT record Jo?Q@WgDis_ sos_identity` and `REJECT run records_rejected`. Original record bytes were retained.

The checker was invoked with the requested Python -B CLI and exact fixture11 manifest in a separate temporary directory per record, retained under checker-runs for review. Every directory contains input.g6, empty UNKNOWN.g6, unchanged records.jsonl (except the deliberately damaged control), run.json, stdout.log, stderr.log, and checked/report.json. Input SHA-256 values were computed from graph6 bytes including the newline.

The unmodified checker hardcodes /tmp/gp10-check for scratch files. Bubblewrap provided read-only /, writable workspace, private /tmp, and a bind from workspace/checker-scratch to /tmp/gp10-check. Thus no host files outside this workspace were changed. The verifier command following the filesystem wrapper was exactly the requested command; no verification logic was patched. No network or git commands were used. All runs used nice -n 15 timeout 1800.

Ten certificates are real-dag; packets 6ff822fba1454815 and 7443a07840cf012e use real certificates. All 12 use SOS witnesses. The frozen verifier regenerates framed unit-distance equations and selected noncollision saturation equations, checks the supplied algebraic identities over exact rational polynomials, and checks that the final polynomial is a strictly positive constant plus positive weighted squares. An injective planar unit-distance embedding would satisfy these equations, forcing that positive polynomial to zero: a contradiction. Saturating selected pairs suffices because every injective embedding satisfies those selected noncollision constraints.

One accepted refuted subgraph suffices by restriction of an embedding; all 12 are available here. I independently confirm the stated non-unit-distance conclusion using the frozen checker as requested. I found no problem with the supplied records or subgraph implication. The fixture11 profile has fixture-only scope and does not establish a complete B11 census; no census claim is needed for these individual certificates.

All original input bytes and checker source hashes were unchanged before/after. Full mappings, graph6 codes, search counts, hashes, commands, logs, and reports are retained in [search-results.json](search-results.json) and [checker-results.json](checker-results.json).

Reproduce search:

```sh
nice -n 15 timeout 1800 <repo>/pyenv-gp10/bin/python -B blind_check.py
```

Reproduce checker runs:

```sh
nice -n 15 timeout 1800 <repo>/pyenv-gp10/bin/python -B run_certificates.py
```
