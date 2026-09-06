# Draft email to Alexeev, Mixon and Parshall (for Liam to send, or not)

Revised 2026-09-06 00:55Z, after the run finished. The 2026-09-05 draft (a letter of intent,
written before the fleet ran) is in git history; this one is a letter of result. Every number
below is what the repository records as of this revision; the page and the write-up are
linked rather than restated. Liam's plan: this goes after u(22) is final (it is), on the same
day as the stratum, with AMP credited in every document (they are).

To: Boris Alexeev, Dustin Mixon, Hans Parshall
Subject: u(22) = 60, by an enumeration built on your method, with checkable certificates

Dear Boris Alexeev, Dustin Mixon and Hans Parshall,

I run a small independent research project called the Artificial Wasteland
(artwaste.land), in which AI systems (Anthropic's Claude, with some OpenAI models) carry out
computational mathematics under my direction, with every result published with a checkable
certificate. The code and computation described below are the work of those systems; I am
the human responsible for both and for this message. I read replies myself and pass them to
the systems doing the work; nothing you write back will be published or quoted without your
say-so. I am not a mathematician by training; if something below is wrong, it is worth
telling me plainly.

Working from "The Erdős unit distance problem for small point sets" (arXiv:2412.11914), we
have determined u(22) = 60: no unit-distance graph on 22 vertices has 61 edges. The method
is yours, reimplemented, with two additions, and I would rather you heard it from us, with
the files, before it goes anywhere else.

What was done, in your terms:

- The F-free enumeration of your Section 2, by canonical augmentation deleting a minimum-
  degree vertex (our choice; the paper does not specify one), pruned at every level from 12
  vertices on by your five totally unfaithful gadgets plus a sixth, each proved in the
  repository, and restricted at every level to the edge counts that can still reach (22,61)
  given u(n) for n <= 21 and a minimum-degree lemma.
- The lemma: combining your Theorem 1(a) and 1(c), a 22-vertex 61-edge unit-distance graph
  has minimum degree exactly 5, because all 18,689 non-isomorphic degree-4 extensions of
  your five extremal 21-vertex graphs contain a forbidden subgraph (checked three ways).
- The run: level 13 was cut into 48 slices by hashing, and fourteen 4-core cloud machines
  grew the slices to 22 vertices, about 165 machine-hours in all. The tree peaks at 15
  vertices with 341,340,490 children generated across the slices and collapses from 16,
  where the reach window admits a single edge count.
- The top level: across all 48 slices, exactly four F-free graphs with 22 vertices and 61
  edges were generated (two in each of two slices). Each contains your gadget with a
  triangle and two rhombi with its forced pair non-adjacent, so none is the unit-distance
  graph of any point set given your u(22) <= 61; and separately, an exact-arithmetic
  reimplementation of the refutation side of your Section 4 solver refutes all four
  algebraically. An independently written blind checker accepts both certificate sets.

What was checked against your paper: the unpruned enumeration reproduces your Table 1 F-free
column at n = 16, 17, 18, 19 and 20 (1, 15, 84, 17, 7) with your embeddable graphs present,
and the gadget-filtered pipeline reproduces the after-filter column at n = 16 to 21 (1, 8,
38, 5, 1, 19), including your five graphs at 21; the n = 21 unpruned count (your 149) was
still being recomputed when I wrote this, after an out-of-memory restart. An independent
Python enumerator replays 92 of 92 sampled shards of the early levels identically; all
fourteen machines produced byte-identical files for the shared levels. The lower bound is
your configuration, drawn on the page from an exact embedding in Q(sqrt 3, sqrt 11) that the
checker verified.

What we did not do: anything at 23 or beyond; a re-enumeration of your two 62-edge graphs
(your u(22) <= 61 is used as your theorem); and the general problem, where we have of course
read the May 2026 developments.

Everything is public under an open licence: the write-up
(research/unit-distance-22/RESULT-u22.md in the repository at github.com/artwasteland),
the four candidate graphs with both certificate files, every slice's manifests with hashes,
the enumerator, the gadget proofs, the checker, and the page at
artwaste.land/strata/the-sixty-first-distance/. If you would look at any of it, or tell us
where a working geometer would want more, we would be grateful; and if you would rather it
were cited or framed differently, say so and it will be. We intend to propose a(22) = 60 for
OEIS A186705 after a mathematician has read the certificate, and to deposit the files with
a DOI; both can wait for your reply if you would like them to.

With thanks for a paper that made this possible,

Liam [surname]
