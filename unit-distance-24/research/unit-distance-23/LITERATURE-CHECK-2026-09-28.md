# G0, the literature recheck: is u(23) still open? (2026-09-28 and 29)

CONTRACT Section 6 gives gate G0 a literature recheck "that u(23) is still open", for the human to redo before anything
is public. Liam asked the u(23) session to do it ("there's honestly not much point me doing the literature check lol
... this may as well be alchemy class to me"), so this is the session's record of it, for him to accept. It is needed
before anything public; the private note to Boris Alexeev does not depend on it, and Boris, a co-author of the paper
that holds the record, is the reader best placed to know of any other work.

## What was checked, and what it says

- **OEIS A186705** (the maximum number of unit distances among n points): its data ends at a(21) = 57. Its edit
  history's latest edits are from May 2026 (#95 to #100: links to the 2026 papers on the asymptotic problem, a
  discussion of a(27)); none adds a(22) or a(23). https://oeis.org/A186705, https://oeis.org/history?seq=A186705
- **Alexeev, Mixon and Parshall, arXiv:2412.11914**: still at v2 (2025-02-12). Exact values for n <= 21, bounds for
  22 <= n <= 30, and u(23) >= 64 from known configurations. https://arxiv.org/abs/2412.11914
- **Boris Alexeev's arXiv listing**: nothing on unit distances since 2412.11914; his 2025-2026 papers are on other
  subjects (the newest, 2609.21914, on flag varieties). https://arxiv.org/a/alexeev_b_1.html
- **The 2026 unit-distance literature** is about the asymptotic problem, not exact small values: the disproof of
  Erdős's conjecture (arXiv:2605.20695, "Remarks on the disproof of the unit distance conjecture"), Sawin's explicit
  lower bound (arXiv:2605.20579), optimized lower-bound certificates (arXiv:2606.03419), and k-planar unit distance
  graphs (Gehér, Pálvölgyi, Simon and Tóth, arXiv:2603.19848, 2026-03-20, bounds on u_k(n), nothing for n = 22 or 23).
- **Web searches** for exact values of u(22) and u(23), the maximum edges of a 23-vertex unit-distance graph, and
  follow-ups to AMP (2026-09-28, 2026-09-29) found nothing beyond the above.

## Conclusion

As of 2026-09-29, no published source gives u(22) or u(23) exactly. Our u(22) = 60 (`research/unit-distance-22/RESULT-u22.md`)
was reported privately to Alexeev, Mixon and Parshall on 2026-09-06 and is not yet public. Redo this check on the day
anything goes public.
