# AMP refutation core

Source: `research/unit-distance-22/embed/udembed.py`.
Source SHA256: `75886c6323caa82d15c2a4c14680c0b6ed3b5cc3608abf116934463361decbda`.

`amp_core.py` copies the graph, exact linear algebra, proof serialization,
and reduction routines. Embedding search, coordinate catalog, and CLI are
omitted. Consequently `sources/amp/tikz.tex` is not needed or opened.

Changes: explicitly select SymPy's Python ground types before importing it;
use DomainMatrix.to_list(); visit both L3 children when a child is unknown;
handle an edgeless graph in find_l3; disable coordinate search. The caller
seeds random.Random from SHA256 of canonical graph6, supplies a finite state
budget, isolates the core in a bounded child, and verifies the serialized
witness using the original udcheck.verify_refutation before accepting it.

No new proof-tree move is introduced. Original source files are read only.
