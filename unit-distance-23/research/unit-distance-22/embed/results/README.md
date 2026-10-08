# Embedder (udembed.py) refutation gap: codex job 3 (2026-09-05 06:15Z to 10:58Z)

Brief: embed/TASK-3.md. Final message: codex-3-last.txt. udembed.py's changes (stderr-only
--trace, the 80-triple L3 cutoff removed, exhaustive exact dependence tests in number-field
arithmetic, triangle-first ordering; global state limit and the checker witness schema
unchanged) reached the branch through the supervisor heartbeat's path-scoped commits
(f2b6087cb and earlier), not through a hand-off.

Independent verification by the coordinator, blind gate `gate-g3.py` on the real survivor cells
(gate-g3-16-19-after-codex-3.txt): n=16 OK (1 survivor, embedded); n=19 OK (5 survivors, 3
embedded, 2 refuted, 0 unknown, checker ACCEPT); GATE G3: PASS on those cells. The gate's
self-test also passes with both mutations red (an extra embedded graph, a corrupted coordinate).

Still open, and only relevant if a (22,61) survivor ever appears (none has, 9 slices in):
n=17 keeps one unknown. The search reaches, in 9 s, an exact forced triangle whose Heron
discriminant is -77, which refutes the embedding mathematically, but the certificate schema
udcheck.py accepts has no move for it (negative-discriminant L3 witnesses are rejected by
design). Codex proposes an `L1c` negative-Heron leaf (embed/REPORT.md, "Proposed
negative-Heron contradiction leaf"): the checker would verify exactly that a*x + b*y + c*z lies
in the row space and that 4|a|^2|b|^2 - (|a|^2 + |b|^2 - |c|^2)^2 < 0. Adding it means changing
the blind checker's contract; it needs its own brief, mutation tests and an independent review
before any certificate uses it. n=18 has 20 unknown of 38 (the default run did not finish in
the job's time).

# Codex job 4 (2026-09-05 12:15Z to 12:28Z): the negative-Heron leaf L1c

Brief: embed/TASK-4.md. Report: codex-4-report.md and codex-4-last.txt. Checker change
(check/udcheck.py, one new `elif kind == "L1c"` branch plus the schema line; check/PROOFS.md
documents it with the soundness argument from AMP's Heron-esque lemma): a leaf that verifies
exactly what a refutation needs: three existing directed edges, three nonzero coefficients in
the node's field, the relation a*x + b*y + c*z in the row space of A, and the discriminant
4|a|^2|b|^2 - (|a|^2 + |b|^2 - |c|^2)^2 strictly negative under the field's selected real
embedding. The edits reached the branch through the supervisor heartbeat's path-scoped commit
6f23cfd0a (12:18Z) before the coordinator's review; the review (this note) approved the diff
as quoted in codex-4-report.md without change.

Coordinator's independent verification (12:33Z): check/selftest.py PASS, 41 checks, 18
positive, 23 mutations rejected (the four new L1c mutations among them: discriminant not
negative, relation outside the row space, zero coefficient, children present); blind gate
`gate-g3.py --n 16 17 19`: n=16 OK, n=17 OK (8 survivors, 7 embedded, 1 refuted, 0 unknown,
checker ACCEPT), n=19 OK (5 survivors, 3 embedded, 2 refuted), GATE G3: PASS; the gate's
self-test PASS with both mutations red. The only cell of gate G3 still open is n=18 (20
unknown of 38 in brief 3's run), being rerun locally with the improved embedder.

# Gate G3 after the calibration runs (2026-09-05 15:00Z)

With the (20,54) and (21,57) calibration keep sets shipped by the calibration workers
(`results/calib/`), the blind gate now covers n = 16, 17, 19, 20, 21: every known extremal graph
embedded and every other survivor refuted with a checker-accepted certificate, none unknown
(`gate-g3-20.txt`, `gate-g3-21.txt`: at n = 21, 19 survivors, 5 embedded, 14 refuted, 11 minutes
on this box). n = 18 is the last open cell, still running with the improved embedder.
