# G0 literature recheck at the end of the run (2026-10-06T20:58Z)

Question (CONTRACT.md section 4, G0): does anything published decide u(24) or contradict the inputs (AMP's lower bound
u(24) >= 68; our u(23) = 64 with Schade's lemma giving u(24) <= 69)?

Searches (web, 2026-10-06T20:58Z): "maximum number of unit distances among 24 points in the plane u(24)"; "unit distance graphs
exact values u(n) n up to 30 Alexeev Mixon Parshall 2025 2026"; "arXiv 2412.11914 unit distance 2026 update new
values"; "u(24) OR u(23) unit distance graph 24 vertices 68 edges exact value 2026"; plus the abstract of
arXiv:2609.10791.

Findings:
- Alexeev, Mixon, Parshall, "The Erdos unit distance problem for small point sets", arXiv:2412.11914 (v1 2024-12-16,
  revised 2025-02-12): exact u(n) only for n <= 21; for n = 22..30 bounds only, with u(24) >= 68 the best lower
  bound. Unchanged. https://arxiv.org/abs/2412.11914
- Older tables (e.g. arXiv:2006.06285) give u(24) in [68, 82]; superseded by AMP's upper bounds, no contradiction.
- L. Guth, "Perspectives on the unit distance problem", arXiv:2609.10791 (2026-09-09): a survey; no small-n values.
  https://arxiv.org/abs/2609.10791
- The 2026 AI-assisted disproof of the unit distance conjecture (arXiv:2605.20695 and the discussion at
  gilkalai.wordpress.com, 2026-05-21) concerns the asymptotic exponent, not small n.

Verdict: nothing published decides u(24) or contradicts the inputs. **Dependency to state in the write-up:** the upper
bound u(24) <= 69 uses u(23) = 64, which is this project's own result (research/unit-distance-23/RESULT-u23.md), not yet
published, so u(24) = 68 is conditional on u(23) = 64 being accepted.
