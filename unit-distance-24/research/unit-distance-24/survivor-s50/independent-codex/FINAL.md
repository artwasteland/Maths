**Yes: I independently confirm that G is not a planar unit-distance graph.** All 12 supplied graphs embed as subgraphs, and all 12 refutation records pass the frozen GP-11 checker.

G has **24 vertices and 69 edges**, with descending degree sequence **six 7s, six 6s, twelve 5s**. My graph6 decoder agrees exactly with NetworkX and the frozen decoder on vertex order and labelled edges for all 13 graphs.

Below, IDs abbreviate `packet-<ID>.record.jsonl`. Each array gives the G-images of H vertices **0 through 10**, using zero-based numbering.

| Record ID | Mapping H → G | Embeds | Checker |
|---|---|---|---|
| 15279f0a55ad52f0 | [19,3,20,8,2,7,16,10,18,1,12] | Yes | ACCEPT |
| 45b8802d634afbe1 | [3,2,13,10,20,1,8,19,22,18,12] | Yes | ACCEPT |
| 59fde588c0e2cb35 | [3,2,20,8,9,19,16,1,10,18,12] | Yes | ACCEPT |
| 603e3f224057a753 | [3,13,2,18,0,22,5,14,15,8,11] | Yes | ACCEPT |
| 60f3da386a6c5278 | [3,1,0,8,10,11,13,2,12,19,18] | Yes | ACCEPT |
| 6ff822fba1454815 | [3,13,22,11,8,5,18,2,4,0,14] | Yes | ACCEPT |
| 7443a07840cf012e | [18,8,14,2,9,3,4,0,13,19,11] | Yes | ACCEPT |
| a5561d906d5f885d | [3,20,8,11,2,13,18,0,4,22,14] | Yes | ACCEPT |
| d06d4b5c19186a03 | [19,8,10,22,13,2,3,7,1,12,18] | Yes | ACCEPT |
| de51b4d793f401e4 | [3,13,23,14,5,0,8,2,22,18,4] | Yes | ACCEPT |
| e38aa6135774612c | [0,2,3,20,22,8,9,18,19,12,13] | Yes | ACCEPT |
| eb71dfb2a5394584 | [19,3,10,6,21,8,2,23,1,18,12] | Yes | ACCEPT |

I wrote an exhaustive backtracking search with necessary degree and edge-support pruning. NetworkX independently agreed on every embedding, and each saved mapping passed separate injectivity and edge checks.

Every original record printed both required ACCEPT messages. The damaged control changed exactly one certificate digit, `cert.sos.c: "1/2" → "1/3"`, and produced:

```text
REJECT record Jo?Q@WgDis_ sos_identity
REJECT run records_rejected
```

I found no flaw in the claim or records. One accepted refuted subgraph suffices; here all 12 qualify. `fixture11` acceptance verifies these individual certificates without establishing a complete B11 census.

The checker hardcodes scratch storage outside this directory, so I used a filesystem bind to keep those writes here while running the unchanged checker. No network or git commands were used; original inputs remained unchanged.

[Full report and mapping links](<repo>/report.md), [search evidence](<repo>/search-results.json), and [checker commands and logs](<repo>/checker-results.json) are saved locally.