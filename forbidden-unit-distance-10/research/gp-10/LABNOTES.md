# GP-10 lab notes (supervisor: claude-answering-alexeev-u22)

Chronological, 2026-09-24 (times AEST). What happened, including what went wrong, so the write-up and any
referee can see the path and not only the destination.

## Morning: inputs, contract, builders

- B10 = 33,162 biconnected F9-free 10-vertex graphs out of 9,743,542 (OEIS A002218). GP's printed counts reproduce
  (366, 2,984). An independent C matcher sharing no code with udfilter reproduced B8p, B9p, B10 byte for byte; all
  9,710,380 forbidden witnesses were replayed; the supervisor checked coverage by set equality with the geng
  stream. Gate G0 met.
- CONTRACT.md and PROOFS.md written before any producer existed. Amendment 1 added controls at n = 4..7 so that the
  whole classification up to 9 vertices is re-derived, not assumed.
- The blind checker was built from the contract in a worktree with no producer code. A separate soundness audit
  built 206 invalid certificates or run directories; all were rejected (0 BLOCKER). The first audit brief was
  killed by OpenAI's cyber filter because it said "forge"; reworded as proof-checker soundness testing.
- The checker caught a reversed sentence in the contract (amendment 2).

## Controls

- 7.0 (n = 4..7) and 7.1 (n = 8) PASS. The first 7.1 attempt FAILED (4 of 13 found) because of two driver
  integration bugs (a crashed refuter round, and a schedule that never tried unit-distance subgraphs of forbidden
  maximal graphs); fixed in driver round 2.
- 7.2 (n = 9) PASS after: 13 F9-free 9-vertex graphs embedded through GP's host G118 (image fields of degree 8 and
  16); GP's F(9,14,2), F(9,14,18), F(9,15,27) refuted by R-real sum-of-squares identities following GP's own hand
  arguments; F(9,14,19) needed a 14-row derivation (amendment 5, R-null-dag). So all 74 of GP's graphs are
  re-proved from an empty list, and GP's classification up to 9 vertices is re-derived.
- Found while rebuilding GP's paper exactly: the published picture of F(9,14,2) needs a one-edge correction to match
  the list; the last two rows of GP's H2 coordinate table must be read as offsets from (sqrt 3, 0).

## B10

- The Moebius ladder M10 is refuted three ways (tree, null, real) and its two edge-deletion classes embed: certified
  minimal (runs/M10-minimal). MathWorld attributes "Moebius ladders are not unit-distance" to B. Alexeev (pers.
  comm., 2025-08-09).
- Interim assemblies: 99, then 105 certified minimal forbidden graphs (checker ACCEPT, sample profile, 0 rejections).
- **Supervisor error:** a B10 assembly was launched without a completion watcher; the pipeline idled for some hours
  while Liam slept. Every long job since has a watcher.
- **Triage error found by hand:** the embedder's curve tracer marked 212 graphs "likely forbidden: every sampled
  real configuration collides". The supervisor checked `I??MOwt{G` by hand: it embeds (min pairwise distance 0.378);
  the tracer never tried the second intersection point at one circle step. A branch-enumerating search then found
  separated configurations for 15 of the first 20 "likely forbidden" graphs. Numerical triage is never a verdict;
  this is why.
- **And the converse:** the branch search's own zero-separation graphs are not verdicts either. `I??gpb@~_` looked
  embeddable on paper until the construction was run: a 60-degree hexagon around the hub 9 forces |p7 - p9| = 1
  (an unlisted 7-vertex forcing gadget), so 7, 0, 1 are three common unit neighbours of 8 and 9 (K_{2,3}), and a
  collision is forced. The all-pairs-saturated R-null refutes it in 11 s; earlier sweeps used narrower saturation
  sets.
- **Cloud fan-out (2026-09-24 evening):** refutation workers w1..w8 (runbook `coordination/cloud-workers/gp10-refute.sh`)
  took the zero-separation graphs; the residue that survived them went to Claude analysts in the cloud (a1..a29, brief
  `coordination/cloud-workers/BRIEF-gp10-analyst.md`), who decide each graph by geometric argument and prove it
  with a targeted certificate. Every certificate is re-checked locally by the blind checker before it is used.
- **Supervisor error (input corruption):** six graph6 strings in the second residue list lost a backslash in a
  shell step (`\` is a graph6 data character; `read` without `-r` eats it), giving 42-bit strings that are not
  10-vertex graphs. Found by checking every input file against B10.g6 by string membership. Each truncated string
  had exactly one preimage in B10; the files were repaired in place and a17 took the six real graphs. Analyst a3
  found and repaired its own corrupted line independently.
- **Supervisor error (coverage):** a coverage check (r3 unknowns, minus everything decided since, with refutations
  propagated to supergraphs and embeddings to subgraphs) found 41 frontier graphs in no analyst's list: w6's 26
  unknowns (w6 finished after the residue lists were cut) and 15 left undecided by earlier rounds but never queued.
  All 41 went to a18..a26; the 13 unknowns just above the frontier went to a27..a29 at the same time. The check is
  now run before every fan-out, not after.
- **The assembly outgrew the desktop.** r4 died of MemoryError after validating all 4,098 seeds: the driver holds
  every certificate in memory (172 MB of JSON then; its peak on a cloud worker later reached 8.5 GB at 4,138 seeds
  and 13.2 GB at 4,216). Assembly and checking moved to cloud workers (`gp10-assemble.sh`, `gp10-final.sh`). The
  checker itself streams (170 MB peak on 33,162 records).
- **A silent drop, found by a coverage check.** `ItP?OGrBw` stayed unknown in asm1 although a refutation existed:
  its only certificate was 9.98 MB, and the driver's seed loader skips lines over the checker's 8 MiB record limit
  without counting a rejection (4,139 records in, 4,138 selected). An analyst (a30) re-certified it in 1.6 MB; the
  gather step now skips and counts oversized records.
- **Tooling errors of the supervisor's own:** five watchers fetching in one worktree raced on `FETCH_HEAD` (a
  probe printed zeros from another analyst's branch; fixed with per-tag refs); a Monitor piped through `grep`
  (here a ugrep wrapper that buffers until exit) delivered nothing mid-stream.
- **Interim assemblies, checker-accepted over all 33,162 graphs, 0 rejections:** asm1 229 certified minimal (105
  unknown); asm2 296 (30 unknown; one of them conditional).
- **The analysts.** 35 cloud Claude sessions and two local workflows decided the residue by geometric argument;
  every refutation they claimed was re-checked locally by the blind checker before use (none rejected). The last
  five graphs each had three independent analysts; every graph decided by more than one analyst got the same
  verdict from each (20 such graphs, 0 disagreements). Six residue graphs embed: four drawn numerically by cloud
  analysts and made exact in rounds 10-13 (I?CtQZOwW, IMi@GoFOw, Ir?A[WiDW, IOCqGvHZ_), two drawn by the local
  workflow and already embedded by earlier rounds; the rest are forbidden.
- **Lean assembler.** `tools/lean_assemble.py` does the driver's no-producer assembly without holding certificates
  (15 s, 343 MB). Validated against asm2: 0 verdict differences in 33,162 records, identical UNKNOWN list (1,183
  pointer records name a different neighbour, since propagation order differs). On asm3's seed bundle: 32,653
  embedded, 509 refuted, 0 unknown. The B10 gate runs on it (fin2) and on the driver's own asm3 (fin1): two
  independent assemblies, one checker.
- **asm3 was killed for memory, as feared:** the driver on asm3's 4,203 seeds reached 13.96 GB and exited 137
  (SIGKILL) on the 15 GB cloud worker. The lean assembly of the same bundle (lean3) had already been built and sent
  to the gate (fin2) in parallel, so nothing waited on it. fin1 (the gate on a driver-built asm3) cannot run on these
  workers; the lean assembler's equivalence to the driver rests on the asm2 comparison (0 verdict differences in
  33,162 records).
- **A wrong prediction, recorded:** the fin0 dry run (B10 profile on asm2, 30 unknown) was expected to REJECT; it
  printed `ACCEPT run verified`. The B10 profile accepts a partial run whose unknowns are listed exactly and marks it
  `conditional: true`. So "ACCEPT" is not G3: G3 is ACCEPT with `counts.unknown == 0`, `conditional == false` and an
  empty `conditional_minimal`, read from the report, not from the final line. fin0 re-verified all eight controls and
  took 52 minutes on a cloud worker.
- **G5 closed:** Arturo (Kimi k3) returned task 0018: checker sound, 0 BLOCKER, 0 MAJOR, 5 MINOR; every finding is
  answered in `G5-RESPONSE.md` (amendment 6 is wording only; the checker stays frozen at `d717816b…`).
- **Round 9 exactification:** 9 of the 10 cloud-numeric seeds exactified (checker ACCEPT); 8 of the 9 had already
  been embedded by round 7 before the cloud workers received them (redundant work, no harm). The tenth, `IGE@[pSwW`
  (numeric separation 0.0022), did not exactify and remains with the analysts.

## Deviation to report

- CONTRACT 7.5 asked for PREDICTIONS.md before the B10 run. Interim B10 assemblies were run before a supervisor-level
  PREDICTIONS.md existed (the embedder wrote its own pilot predictions). The final report must say so rather than
  write predictions after the fact.

## Result (2026-09-25, ~03:00 AEST)

- **G3 closed.** fin2 (B10 profile, checker `d717816b…`, on the lean assembly lean3): `ACCEPT`, reason `verified`,
  33,162 graphs = 32,653 embedded + 509 refuted + 0 unknown, not conditional, 0 direct rejections, all eight controls
  re-verified inside the run, 3,156 s on a cloud worker. **324 minimal forbidden graphs on 10 vertices** (185 refuted
  but not minimal); with GP's 74, 398 up to 10 vertices.
- **An independent agreement:** before fin2 reported, the supervisor computed the expected L10 from lean3's verdicts
  and the poset (refuted graphs whose every biconnected one-edge deletion embeds): 324 graphs. The checker's
  `L10.g6` is exactly that set.
- **G6:** `RESULT.md` generated by `tools/write_result.py` from `runs/B10-final-2026-09-25/` alone (the writer
  refuses while any unknown or conditional remains; red-tested on fin0).
- G4 (a second, differently-typed certificate per L10 member; a count, not required) is running on 18 cloud workers.
- **The deposit bundle re-checks from nothing (2026-09-25 ~04:30 AEST).** `tools/build_bundle.sh` assembles 169 files
  (49 MB, no personal name or machine path in any file or archive header; the verification files asserted
  byte-identical to the certified run's). `RECHECK.sh` printed `RECHECK PASS: 324 … identical to L10.g6` four times:
  from clean copies of the bundle before and after the publishable-only pass on the desktop (Python 3.12), and on two
  fresh cloud machines following only the README (rc1, rc2; Python 3.11, fresh venv from requirements.txt, apt nauty).
  The Zenodo metadata is staged in `deposit/.zenodo.json`; no draft exists yet (publishing is the human's).

## Checking harder (2026-09-25, ~05:45 to 08:00 AEST)

The human asked whether the result could be checked harder. Everything in `RESULT.md` passed through one checker, so
each check here avoids it in a different way; `INDEPENDENT-CHECKS.md` (generated from `runs/independent-checks-2026-09-25/`
and `runs/G4-second-certificates-2026-09-25/`) has the numbers.

- **Independent audit** (`tools/independent_audit.py`: networkx, pynauty, mpmath; nothing from `check/`, `drive/` or
  the producers): PASS, 0 alarms, identical on two runs. 33,162 distinct classes; the minimality recount by nauty
  lookups gives 324 = L10 (185 refuted non-minimal, 0 biconnected deletions missing from B10); 3,879 exact embeddings
  re-evaluated at 120 digits, worst edge residue 6.2e-99, falling to 6.7e-219 at 240 digits (true zeros); smallest
  point gap 0.0024; 28,959 pointers, 0 broken chains; the up-set of L10 in B10 is exactly the 509 refuted graphs; VF2
  (no canonical forms), the 100 densest embedded graphs against all of L10: 10,595 pairs, 0 containments.
- **Red on purpose** (`tools/independent_audit_redteam.py`): 10 of 10 mutation checks red with the named alarm (a
  coordinate moved by 1e-40, a pointer map swapped, an L10 member or a non-minimal graph relabelled embedded, L10 short
  by one or long by one, a relabelled duplicate in B10), and the 240-digit control passes.
- **Numeric embedding attack** (`tools/embed_redteam.py`, numpy only): 0 of 324 members embed (16,384 LM starts each;
  a candidate counts only if 50-digit refinement drives the residue below 1e-35 with no two points closer than 1e-6).
  The same rule found embeddings for all 324 member-minus-an-edge controls (each within 2,048 starts) and all 324
  look-alikes (same edge count, 319 with the same degree sequence; each within 4,096 starts). 1,182 near-miss
  candidates on 52 members; each of the 152 recorded refined gaps is below 4e-11 (two points colliding).
- **G4, final count:** 194 of 324 members have a checker-accepted refutation of a different type (g14 and g17 landed;
  g18's retry stayed idle and was not re-fired). `tools/g4_count.py` reproduces the saved run byte for byte.
- **A second verifier, written blind** (`blind-verifier/`, `REPORT.md` there): a Claude agent (the checker was built by
  codex) in a directory holding only the written spec and the 324 records. 324 of 324 ACCEPT (tree 103, real-dag 97,
  null-dag 65, real 24, null 22, tu 13), 0 REJECT, 0 UNSUPPORTED; its 207 negative controls all rejected and 7 attack
  certificates stopped at the intended check. The supervisor re-ran it (identical verdicts), added five mutations it
  never saw (all rejected), and ran it over the 74 GP certificates from the empty-list controls: 74 of 74 ACCEPT, every
  TU certificate among them citing only a strictly smaller forbidden graph, so the premise its TU acceptances lean on
  is closed by the same second implementation, inductively.
- **Boris's question about "exactly four"** (the u(22) letter) answered in
  `research/unit-distance-22/REPLY-DRAFT-2026-09-25-four-graphs.md` for the human to send; the u(22) write-up's
  "a single edge count from level 16" was wrong (34..41 there; single only at 21) and is corrected in `RESULT-u22.md`.

- **Every polynomial identity without FLINT** (`tools/modp_identities.py`, written after the blind verifier named
  python-flint as the one arithmetic dependency both verifiers share): the 2,071 identities of the 208 polynomial
  certificates among the 324 (every cofactor sum, derivation row and SOS decomposition), and the 24 of the 7 among
  the GP 74, hold at three random points modulo 2^61-1 and three modulo 2^127-1, in plain Python integers; 8 of 8 red
  controls fail as required.

Supervisor errors on the way:

- **A lax filter.** The first numeric search counted any float candidate with residue below 1e-10 and gap above 1e-4
  as an embedding; its first "hit" slid into a collision under 50-digit refinement. The same rule would have inflated
  the controls' success rate too, so refinement now decides members and controls alike.
- **The self-match trap, twice.** `pkill -f` killed its own shell (exit 144), the second time through the bracket
  trick, because the filename also appeared elsewhere in the same command line; it took both Monitor watchers with it.
  Kill patterns are now anchored on the interpreter path.
- **A silent hang.** Control M7 waited for a relabelled graph6 string that could never differ: networkx writes graph6
  in node insertion order, so `relabel_nodes` (and `to_graph6_bytes(nodes=...)`, which goes through `subgraph()`)
  wrote the original string back. Seen only because the driver stayed alive with no output; the graph is now built
  explicitly and the loop is capped.
- **An unbudgeted spot check.** VF2 over 1,000 hosts would have taken about three hours (15 s per dense host); cut to
  100 and made its own stage, since the up-set equality is the complete check.

## Boris's reply: two OEIS sequences and a corollary (2026-09-25, ~13:00 AEST)

- Boris noted that the result extends OEIS A308349 (minimal forbidden graphs on n vertices: 0,0,0,1,1,1,3,13,55) and
  probably A059103 (connected unit-distance graphs: 1,1,2,5,13,51,222,1313,9639). A308349(10) = 324 directly.
- **A059103(10) = 91,658**, by `tools/count_connected_udg.sh` (a connected graph is unit-distance iff its blocks are,
  so a(n) = connected F(n-1)-free graphs minus the Bn run's refuted graphs). It reproduces every known term for
  n = 4..9 two ways; at n = 10 two matchers sharing no code agree on the 92,167 F9-free connected graphs, and a direct
  count with all 398 as patterns gives 91,658 again. Run in `runs/A059103-connected-udg-2026-09-25/`; the script run
  end to end reproduces the list's sha256. OEIS submissions are the human's.
- **Corollary of u(22) = 60** (AMP's Schade lemma, chained): u(23) <= 65, so u(23) is 64 or 65; AMP's Theorem 1(b)
  upper bounds for n = 23..30 (66, 72, 78, 84, 90, 96, 103, 110, which are exactly Schade's chain from their
  u-bar(23) = 66) drop to 65, 70, 76, 82, 88, 94, 100, 107.
