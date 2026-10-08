# Independent checker report

## WHAT WORKS

The deliverable consists of udcheck.py, PROOFS.md, selftest.py, and six fixed
JSON-lines fixtures comprising three required certificates and their
one-byte corruptions.

The checker uses the contract's top-level JSON-lines record. The exact inner
witness schema is stated in the udcheck.py module docstring because the
contract does not specify it. By default every record must have 22 vertices
and 61 edges. The --allow-any-size option exists only to run small controls.
The --graphs option requires certificate records to equal a supplied graph6
list in the same order.

Graph6 parsing is independent Python code. The checker verifies order, edge
count, padding, uniqueness, and canonical form with one batched invocation of
/usr/bin/nauty-labelg -q.

Forbidden and TU witnesses are replayed as injective edge-preserving maps.
The TU path additionally checks the gadget index, the exact mapped
distinguished pair, and that this pair is a non-edge of the candidate.

Embedded witnesses use one explicitly isolated real algebraic number field.
Polynomial reduction, addition, multiplication, inversion, exact equality,
Sturm root counting, sign separation, point separation, and squared-distance
checks use fractions.Fraction and code in udcheck.py. SymPy is used only for
its exact irreducibility predicate over the rationals. No floating point
number participates in acceptance.

Refutation nodes carry the current edge set and the full homogeneous complex
matrix A. The checker independently reconstructs the L0 rhombus row space.
It checks exact row-space consequences for L1a, L1b, L2, and L3. An L2 child
must have exactly the one claimed new edge and precisely the old constraints
plus all new rhombus constraints. For L3, the source relation, discriminant,
square root, sign, both ordered Lemma 4 equations, both child row spaces, and
both subtrees are checked. Only L1a and L1b nodes may be leaves.

Unknown records are counted, printed, and required to occur in UNKNOWN.g6 in
exactly the same order.

Manifest checking verifies actual SHA-256 values for parents, children, and
every declared software file. It verifies successful exit status, child
record counts, unique shard IDs, and exact half-open range tiling of every
parent. Plain and zstd-compressed graph lists are both counted. A direct
parent-hash to child-hash link is recognized where one exists.

The exact build check was:

    ~/tools/pyenv-maths/bin/python -m py_compile udcheck.py selftest.py

It produced no output and exited 0.

The full exercised check was:

    PYTHONUNBUFFERED=1 nice -n 10 ~/tools/pyenv-maths/bin/python selftest.py

Its final output line was exactly:

    SELFTEST PASS checks=36 positive=17 rejected_mutations=19

The three required hand-written positive controls produced:

    ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
    ACCEPT certificates records=1 forbidden=0 tu=0 embedded=1 refuted=0 unknown=0 proof_nodes=0
    ACCEPT certificates records=1 forbidden=1 tu=0 embedded=0 refuted=0 unknown=0 proof_nodes=0

These are respectively K4, the Moser spindle, and a planted copy of forbidden
pattern 0. The Moser spindle fixture contains the canonical graph6 string and
coordinates in \(\mathbb Q(\sqrt3+\sqrt{11})\). Its primitive element has
polynomial \(x^4-28x^2+64\) and isolating interval \((5,6)\).

The six TU positive controls each produced:

    ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0

The synthetic L1b, L2, and L3 controls reported respectively 1, 2, and 3
proof nodes. The synthetic default-size control had exactly 22 vertices and
61 edges and produced:

    ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=0 unknown=1 proof_nodes=0

The manifest controls used 2 manifests tiling 1 parent with ranges [0,1) and
[1,2). Both the plain and zstd versions accepted. Their manifest summary was:

    ACCEPT manifests manifests=2 parents=1 chain_roots=1

I also decoded and canonical-checked all 56 AMP ancillary graph6 strings. The
measured class counts were:

    known_graphs= 56 classes= [((0, 0), 1), ((1, 0), 1), ((2, 1), 1), ((3, 3), 1), ((4, 5), 1), ((5, 7), 1), ((6, 9), 4), ((7, 12), 1), ((8, 14), 3), ((9, 18), 1), ((10, 20), 1), ((11, 23), 2), ((12, 27), 1), ((13, 30), 1), ((14, 33), 2), ((15, 37), 1), ((16, 41), 1), ((17, 43), 7), ((18, 46), 16), ((19, 50), 3), ((20, 54), 1), ((21, 57), 5)]

The independent graph6 decoder agreed with NetworkX on 280 deterministic
random labelled graphs. Exact inversion succeeded for all 48 tested nonzero
elements \(a+b\sqrt2\), where \(a,b\) ranged from -3 to 3. Exact sign
separation returned positive for \(\sqrt2\) and negative for \(1-\sqrt2\).

The 74 forbidden JSON records have the contract's exact composition:

    [((4, 6), 1), ((5, 6), 1), ((6, 9), 1), ((7, 10), 1), ((7, 11), 2), ((8, 12), 3), ((8, 13), 10), ((9, 13), 2), ((9, 14), 19), ((9, 15), 34)]

After canonicalizing both representations, all 74 JSON patterns were
isomorphic in position to the 74 lines of forbidden-74.g6.

Every substantive positive control was made to fail through the same
command-line path:

| control | deliberate break | exact red condition |
|---|---|---|
| K4 L1a | fixture pair byte 1 changed to 0 | invalid distinct vertices |
| default size | ran K4 without --allow-any-size | expected 22 vertices, got 4 |
| L0 | changed first root matrix coefficient from 1 to 2 | root row space inconsistent |
| Moser spindle | fixture coordinate byte in 1/2 changed to 1/3 | edge (0,1) not squared distance 1 |
| point injection | replaced point 6 by point 0 | points 0 and 6 collide |
| forbidden injection | fixture final map byte 3 changed to 2 | map not injective |
| forbidden edges | claimed K4 inside the five-edge diamond | mapped pattern edge absent |
| L1b | changed omega from 0 to 1 | L1b omega has unit modulus |
| L2 | changed omega from 1 to 0 | claimed ratio not a row-space consequence |
| L2 child | deleted one child edge | child graph inconsistent with parent move |
| L3 algebra | changed \(d=\sqrt3\) to \(d=1\) | d does not square to discriminant |
| L3 branch | changed one matrix coefficient in child 1 | branch row space inconsistent |
| TU pair | replaced one reported pair endpoint | not the mapped distinguished pair |
| graph6 canonicality | supplied valid gadget in noncanonical labelling | labelg result differed |
| unknown list | changed C~ to C? in UNKNOWN.g6 | unknown list differed |
| graph list | replaced expected 22-vertex line by C~ | graph list differed |
| manifest tiling | changed second range from [1,2) to [0,1) | overlap at record 1 |
| manifest input hash | changed one hex byte | parent file hash mismatch |
| TU written proof | changed first rhombus coefficient from -1 to 1 | gadget 0 identity false |

The fixed corrupt fixtures are retained so the three one-byte failures do not
depend on runtime fixture generation.

## WHAT DOES NOT

No real (22,61) enumeration list, production certificate file, or production
manifest directory was present in this module. I therefore did not and
cannot claim that all (22,61) candidates have been checked.

The manifest format in Contract Section 2 cannot by itself prove a complete
chain from geng seeds to a final frozen file. In particular, it has no record
type for concatenating shard outputs, canonical sorting, isomorphism
deduplication, or freezing that result as the next parent. It also does not
identify which unhashed-parent roots are authorized geng seeds or which
terminal file is the required 22-61.g6. udcheck.py verifies every fact that
the stated fields can establish and reports the number of unlinked hash
roots. It does not pretend those roots prove seed provenance.

The checker does not accept towers of number fields or free-form symbolic
expressions. A producer must express all exact values in one real primitive
field using the documented polynomial basis. This is a deliberate small
trusted format, but producers using a different unstated schema will need a
converter.

## UNCERTAIN

Production scale is unexercised. The largest certificate test here has 22
vertices, but only one record and no large proof tree. Exact row reduction is
cubic in the small vertex dimension but is repeated at proof nodes. Runtime
and memory on the eventual full certificate set remain a work item.

No proof tree produced by the independent embedder was available. The tested
trees are hand-built L1a, L1b, L2, and L3 examples. Integration against the
producer's serialization is still required.

The manifest checker treats equal software basenames as the same logical
software item for cross-manifest consistency. This is sensible for the
expected flat tool set, but the contract should define software identities so
that two unrelated files with the same basename are not ambiguous.

The checker requires each L3 coefficient \(a,b,c\) to be nonzero. This avoids
degenerate, non-progressing case splits. AMP states that the coefficient
triple is a nonzero vector, which is weaker. A production proof that uses a
zero individual coefficient will be rejected until the contract resolves
this distinction.

## PROPOSED CONTRACT AMENDMENTS

1. Specify the exact inner JSON schema for embedded and refuted witnesses.
   State coefficient order, rational encoding, interval endpoint convention,
   complex encoding, graph state encoding, child order, and whether matrices
   are compared literally or by row space. The schema in udcheck.py is a
   concrete proposal.

2. Add signed merge manifests. A merge record should name every ordered shard
   input and hash, the exact concatenation order, canonicalization and
   deduplication software hashes, the output path and hash, input and output
   record counts, and duplicate count. Add explicit seed records and one
   explicit target record. Without these, Section 6.2(a) is not mechanically
   provable.

3. State whether a hash of a zstd path covers compressed bytes or decompressed
   content. This checker hashes stored bytes and counts decompressed records.
   Recording both hashes would be better.

4. Pin the nauty version and canonicalization options. With installed nauty
   2.8.8 and default labelg -q, only 1 of the 74 literal lines in
   data/forbidden-74.g6 is already canonical, although all 74 become
   position-wise identical to the JSON patterns after both sides pass through
   labelg. Either canonicalize that data file or explicitly exempt it as a
   historical labelled reference.

5. Clarify whether L3 requires all of \(a,b,c\) to be nonzero, and specify how
   a negative discriminant is certified. The present checker requires three
   nonzero coefficients, exact \(d^2=D\), and \(D\geq0\) at the isolated real
   root.
