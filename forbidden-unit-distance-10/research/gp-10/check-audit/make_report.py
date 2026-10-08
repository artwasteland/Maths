#!/usr/bin/env python3
"""Render the human audit report directly from retained observations."""
from collections import Counter
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "ulimit -v 1000000\nexec nice -n 15 env PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python <repo>/pyenv-gp10/bin/python "


def command(script, arguments=""):
    return PREFIX + "research/gp-10/check-audit/" + script + (" " + arguments if arguments else "")


def main():
    bundle = json.loads((HERE / "cases/results.json").read_text())
    results, summary = bundle["cases"], bundle["summary"]
    findings = json.loads((HERE / "findings.json").read_text())
    counts = Counter(f["severity"] for f in findings)
    assert summary["matched"] == summary["total"] and not summary["mismatches"]
    full = [r for r in results if r["kind"] == "run"]
    arithmetic = [r for r in results if r["kind"] == "sturm"]
    run_counts = Counter(r["observed_status"] for r in full)
    helper_counts = Counter(r["observed_status"] for r in arithmetic)
    parent_names = {r["parent"] for r in results if r["parent"]}
    assert all(r["name"] in parent_names for r in results if r["status"] == "ACCEPT")
    env = summary["environment"]
    out = ["# CHECKAUDIT report\n", "## VERDICT\n"]
    out += [f"BLOCKER: {counts['BLOCKER']}. MAJOR: {counts['MAJOR']}. MINOR: {counts['MINOR']}.\n",
            "No invalid full-run fixture was accepted. This is a bounded soundness audit, not a proof that the checker is sound. The required smaller control profiles are missing, so the amended control gate is not fully implemented. The minor findings are sound differences in accepted syntax.\n",
            f"The final audit matched all {summary['total']} expectations: {len(full)} full run checks ({run_counts['ACCEPT']} accepted baselines and {run_counts['REJECT']} rejected mutations), plus {len(arithmetic)} direct Sturm checks ({helper_counts['ACCEPT']} polynomials with no real zero and {helper_counts['REJECT']} red companions). Every accepted baseline has a direct red companion. All {summary['paired_mutations']} mutation links were checked against the retained positive fixture.\n",
            "These counts, findings, environment values and exact outputs come from the commands below and [cases/results.json](cases/results.json), [cases/index.json](cases/index.json), and [findings.json](findings.json). Finding counts are computed from the reviewed finding inventory by the report command.\n",
            "Executed from the repository root, with each block a separate command:\n",
            "```sh\n" + command("build_cases.py") + "\n```\n",
            "```sh\n" + command("audit.py", "--all") + "\n```\n",
            "```sh\n" + command("make_report.py") + "\n```\n",
            f"Observed audit wall time: {summary['elapsed_seconds']:.6f} seconds; maximum resident memory reported by the audit process: {env['max_rss_kib']} KiB; inherited niceness: {env['nice']}; address-space ceiling: {summary['address_space_bytes']} bytes. The suite is a stated deterministic sample of certificates and run directories. No full production classification was attempted, and the suite completed below the common time threshold.\n",
            f"Environment: Python {env['python']} from `{env['executable']}`, SymPy {env['sympy']}, python-flint {env['flint']}, `SYMPY_GROUND_TYPES={env['SYMPY_GROUND_TYPES']}`.\n",
            f"Checker SHA256: `{summary['checker_sha256']}`. Trusted kernel SHA256: `{summary['kernel_sha256']}`. The audit asserted that the checker hash did not change during replay.\n",
            "The original checker is imported through the pre-existing [runner.py](runner.py). The adapter changes only scratch paths and bytecode settings. Each full case calls the original `main(argv)` in the audit process; nauty is its only child. This keeps the workload within the process limit without changing verification branches. All outputs and fixtures are within this module or `/tmp/gp10-checkaudit/`. No git commands were used, and no producer, checker or trusted data files were edited.\n",
            "Process deviation: the initial read of COMMON.md used `nice -n 10 cat research/gp-10/briefs/COMMON.md` without a virtual-memory limit. After reading that rule, commands used `nice -n 15`; the brief and contract reads used `ulimit -v 1500000`, and remaining commands used the stricter `ulimit -v 1000000` required by the contract's machine limit. The contract takes precedence over the common file's looser memory allowance.\n",
            "The fixture builder initially needed a type-sensitive comparison for boolean mutations. Early audit passes also exposed an incorrectly regenerated input for the noncanonical-record test and literal newline escapes in a new TU fixture. These were audit-fixture mistakes, corrected before the final replay. No checker changes were made to obtain passing results.\n"]
    out.append("## TEST CASES\n")
    out += ["Every test input and its observed output is retained under [cases/](cases/). The case index records the positive parent and the mutation path. A record mutation changes exactly its declared JSON field; the run envelope is rebuilt when the graph identity changes. A run mutation changes one input file, such as one JSONL record, a pointer field, a coverage line or a proposed minimal list. Helper mutations change one polynomial coefficient. These scopes are distinguished below instead of treating a whole changed stream as a single scalar field.\n",
            "Every invocation below was actually executed inside the `audit.py --all` command above. `gp10check.main` lines give its exact argument vector. The following fenced output is its captured stdout, including the final run decision; it is not reconstructed from an expected result. For helper cases the output is explicitly an adapter rendering of the helper's return value or rejection exception, not a CLI ACCEPT line. The stored checker report and record logs provide additional structured evidence.\n",
            "To replay one case and its genuine positive parent, use the same command wrapper with `audit.py --case CASE_NAME`. The audit exits successfully only if the expected acceptance or exact rejection reason is observed. Full checker exit codes are recorded separately in results.json.\n",
            "Coverage notes: all frozen forbidden members were targeted by changing the g6 of an accepted distinct rational embedding. These are graph-binding attacks, not evidence that difficult near-solutions were exhausted. The named UDG tree attacks use an accepted same-order K4-with-isolates refutation and change only the record's g6. They must fail at the trusted kernel's comparison with the current graph.\n",
            "A declared-unknown sample may correctly print ACCEPT while its report remains conditional. A missing record, a missing unknown-list entry or a pointer to an unknown graph must reject. A sample profile never establishes production completeness. The smaller-family sample baselines deliberately contain declared unknowns and are not successful classification controls.\n"]
    for i, r in enumerate(results, 1):
        name = r["name"]
        directory = "cases/" + name
        filename = "polynomial.json" if r["kind"] == "sturm" else "records.jsonl"
        out += [f"### {i}. {name}\n",
                f"File: [{directory}/{filename}]({directory}/{filename}). " +
                (f"Run manifest: [run.json]({directory}/run.json). " if r["kind"] == "run" else "") +
                f"Exact saved output: [observed.stdout]({directory}/observed.stdout).\n"]
        if r["parent"]:
            out.append(f"Positive parent: [{r['parent']}](cases/{r['parent']}/). Mutation: `{json.dumps(r['mutation'], sort_keys=True)}`.\n")
        else:
            out.append("Genuine accepted baseline, with a rejected direct companion elsewhere in this section.\n")
        if r["note"]:
            out.append(r["note"] + "\n")
        if r["kind"] == "run":
            operation = "gp10check.main(" + repr(r["in_process_command"][1:]) + ")"
        else:
            operation = r["in_process_command"]
        out.append("Executed in-process command:\n\n```python\n" + operation + "\n```\n")
        out.append("```text\n" + r["stdout"] + ("" if r["stdout"].endswith("\n") else "\n") + "```\n")
    out.append("## CODE REVIEW\n")
    out.append("Reviewed the complete gp10check.py against CONTRACT Sections 3 and 4 and both GP-10 proof documents. Also read the delegated kernel's field construction and complete verify_refutation implementation, plus its local gadget and Heron proofs. Locations below refer to the hashed checker version above.\n")
    for f in findings:
        out += ["### " + f["id"] + ": " + f["title"] + "\n",
                "Locations: `" + f["locations"] + "`.\n", f["requirement"] + "\n", f["explanation"] + "\n",
                "Evidence: " + ", ".join("[" + name + "](cases/" + name + "/observed.stdout)" for name in f["evidence"]) + ".\n",
                "Suggested correction: " + f["recommendation"] + "\n"]
    out += ["### Branch-by-branch assessment\n",
            "| Area and checker locations | Proof obligation and audit result |\n| --- | --- |\n",
            "| Parsing and graph identity, 56-95, 156-217, 743-813 | Strict keys, finite JSON, integer vertices, canonical graph6, correct map length, injection and edge preservation are enforced. Duplicate keys and duplicate records reject. Noncanonical coverage does not merge aliases. Canonicalization trusts the installed nauty implementation. |\n",
            "| E-exact, 303-350 | Strict sign change supplies a root. Edge equations are reduced exactly. Exact collisions reject before interval refinement. Every pair shares the same nested interval, and a rational midpoint root is tested against all pairs. No independent root choice per pair was found. Reducible and repeated-root polynomials are permitted when the proof obligations hold, as the contract allows. |\n",
            "| E-ptr and R-ptr, 487-515, 815-842 | Maps use the correct source-to-target direction. Resolution requires an accepted target with the same required verdict. Missing targets, unknown targets and self-cycles reject. Frozen indices are range checked, checked against the in-force list and bound to the canonical graph. |\n",
            "| R-tree, 496-503; trusted udcheck.py 585-710 | The exact current graph is passed to verify_refutation. The kernel checks root edges, root row space and subsequent move constraints, rather than trusting witness edges. The run fixtures demonstrate rejection of trees transplanted onto the named UDGs, fabricated row spaces, bad leaves, bad fields and invalid collision pairs. Deeper moves were read but not exhaustively mutation tested here. |\n",
            "| R-tu, 516-542 | Each step checks its gadget map against the currently augmented graph, its distinguished pair and nonadjacency. The endpoint must contain the actual frozen forbidden member using stored labels, or an accepted refuted target using canonical labels. The asymmetric label tests distinguish these conventions. Earlier and later steps cannot be swapped to borrow future edges. |\n",
            "| R-null, 353-416 | The checker constructs a frame on an edge and regenerates every generator. No extra pinned vertex or nonedge unit equation can be supplied. The sparse ring has fixed distinct variable names, strict exponent vectors and no duplicate monomials. Expansion checks the identity exactly. Repeated saturation pairs reject; adjacent pairs are allowed because they are redundant, sound equations. |\n",
            "| R-real, 418-442 and 280-300 | The same regenerated identity must equal f. SOS requires a positive constant and positive weights, then separately checks expansion. Sturm checks the named variable, excludes other variables and handles zero and repeated-root polynomials. A saturation variable is valid because its value in a real embedding is real. No sign or complex-versus-real gap was found in these branches. |\n",
            "| Coverage and consistency, 761-883 | All nonhost records must match the frozen input set exactly, with no duplicates or embedded/refuted conflicts. The exact unknown file is mandatory. Requested monotonicity comparisons are actually searched; no automatic nonempty sample is promised or required when none is requested. Records may print ACCEPT before a later coverage failure, but the final run decision rejects. |\n",
            "| Blocks and minimality, 553-569, 885-922 | A nonbiconnected deletion is accepted structurally only after checking block order, forbidden freeness and edge coverage. A forbidden block is not waved through. Biconnected deletions require accepted records. A refuted deletion excludes the parent. Missing deletions, an included nonminimal parent and an omitted minimal graph are rejected. Unknown deletions produce the amended conditional wording and provisional list membership. |\n",
            "| Control gate, 598-603, 661-680, 720-741, 924-963 | Existing control reports must lie within the run tree and are replayed; a supplied ACCEPT flag alone is not enough. The smaller-profile omission is MAJOR-1. Named search provenance and prediction chronology remain external assertions, clearly identified in the report. claim_authorized remains false. |\n",
            "Sound implementation choices that are not additional findings: exact rational interval bounds satisfy the certified interval requirement; a strictly checked rational midpoint root proves the same existence conclusion; the field polynomial need not be irreducible for E-exact; ordered unique saturation pairs and nonempty TU chains restrict the wire format without weakening an accepted proof; omitted cofactors mean zero; dictionary keys cannot silently redefine generators. The amended minimality wording is correct and is not the earlier contract ambiguity.\n",
            "No specific polynomial identity, graph map, proof-tree binding, coverage equality or minimality implication in the exercised paths verified less mathematics than its cited proof requires. This statement is limited by the sampling and trusted components below. The major finding concerns the amended control gate, not a demonstrated invalid geometric verdict.\n"]
    out.append("## UNCERTAIN\n")
    out += ["The full B10 run and the full accepted B8p, B9p, named and regression control trees were not exercised. The missing smaller controls were demonstrated by rejected profile mutations and source review, not by constructing an accepted B10 run that bypasses them. Input-freeze completeness, forbidden-filter witness replay and independent enumeration were outside this module's job.\n",
            "Only the copied C4, triangle and Moser embeddings, the generated elementary embeddings and the retained refutation certificates were verified positively here. Fresh embeddings of Petersen, the pentagonal prism and IISpZATaw were not produced. Their role as UDG targets comes from the supplied brief and contract. The forbidden-member sweep uses simple graph-identity mutations; it is not an exhaustive algebraic attack on each member.\n",
            "The trusted tree kernel's deeper branching moves and all gadget proofs were not re-proved from scratch or exhaustively mutation tested. The direct tree positives mainly close by a rhombus collision. Gadget mutation fixtures primarily exercise the first gadget, although the source review checks the generic path. No CAS producer wrappers were run, so this report says nothing new about msolve or Singular production behavior.\n",
            "Very large polynomials, extreme integer-string sizes beyond the retained rational fixture, long dependency chains, maximum-sized hosts, killed processes, concurrent file replacement, output-path races and disk exhaustion were not stress tested. The suite removes its own stale evidence before each replay; it does not establish all crash-recovery properties of the production checker.\n",
            "The least independently checked assumption is the correctness of the trusted kernel and frozen mathematical data, including the external smaller-graph classification used by block_evidence. A hidden soundness defect would most plausibly lie in a deeper delegated proof-tree move, unusual exact-arithmetic boundary, or run/control interaction that needs a full production tree. Many initial certificates were copied from the checker author's fixture set, so agreement on those baselines is correlated; the new field, graph-binding, label-direction, unknown-pointer, block and arithmetic mutations provide additional but finite independence.\n",
            "Accepted helper return values, accepted declared-unknown samples and the absence of observed false accepts do not authorize a GP-10 classification claim. The startup command deviation is disclosed in VERDICT. All required deliverables for this bounded CHECKAUDIT job are present; the mathematical and production gaps described here remain open.\n"]
    (HERE / "REPORT.md").write_text("\n".join(out))
    print("REPORT " + json.dumps({"BLOCKER": counts["BLOCKER"], "MAJOR": counts["MAJOR"], "MINOR": counts["MINOR"],
                                "cases": summary["total"], "full_runs": len(full), "helper_checks": len(arithmetic),
                                "full_run_accept": run_counts["ACCEPT"], "full_run_reject": run_counts["REJECT"]}, sort_keys=True))


if __name__ == "__main__":
    main()
