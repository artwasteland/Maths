#!<repo>/pyenv-gp10/bin/python
"""Replay saved certificates, audit coverage and generate the honest module report."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
import networkx as nx
from graphs import MODULE,ROOT,UD,decode,canonical,patterns
from gp10refute import configure,verify,timed

configure()
start=time.monotonic()
E=MODULE/"evidence"
F=MODULE/"fixtures"
summary_paths=sorted(E.glob("*.summary.json"))
summaries={p.name.removesuffix(".summary.json"):json.loads(p.read_text()) for p in summary_paths}
gp=(F/"gp74.g6").read_text().splitlines()
prep=json.loads((E/"preparation.json").read_text())
assert canonical(gp)==gp
assert len(set(gp))==len(gp)
for code,edges in zip(gp,json.loads((UD/"data/forbidden-74.json").read_text())):
    assert nx.is_isomorphic(nx.from_graph6_bytes(code.encode()),nx.Graph(edges))
for name,expected in prep["input_sha256"].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
vendor=(MODULE/"VENDOR.md").read_text()
assert hashlib.sha256((UD/"embed/udembed.py").read_bytes()).hexdigest() in vendor
for p in MODULE.glob("*.py"):
    compile(p.read_text(),str(p),"exec")
for p in MODULE.rglob("*"):
    if p.is_file() and p.suffix in (".py",".md"):
        assert chr(0x2014) not in p.read_text(),p
assert not list(E.glob("*SOUNDNESS-FAILURE*"))

all_records={}
checked=Counter()
method_codes={method:set() for method in ["tu","tree","null","real"]}
proofs={}
proof_sizes={}
oversized_records=[]
null_constant_real=0
for name,summary in summaries.items():
    path=E/(name+".jsonl")
    with path.open() as raw:
        raw_sizes=[len(line.encode()) for line in raw]
    records=[json.loads(line) for line in path.read_text().splitlines()]
    assert len(records)==summary["count"]==len(summary["rows"]),name
    assert len({r["g6"] for r in records})==len(records),name
    assert Counter(r["verdict"] for r in records)==Counter({k:v for k,v in
        [("refuted",summary["refuted"]),("unknown",summary["unknown"])] if v}),name
    for rec,row,raw_size in zip(records,summary["rows"],raw_sizes):
        assert rec["g6"]==row["g6"] and rec["verdict"]==row["verdict"]
        if rec["verdict"]=="refuted":
            with timed(30):
                verify(rec["g6"],rec["cert"],[],{})
            checked[rec["cert"]["type"]]+=1
            if summary["suite"]=="gp74":
                method_codes[summary["method"]].add(rec["g6"])
                size=len(json.dumps(rec,sort_keys=True).encode())
                if raw_size>8*1024*1024:
                    oversized_records.append({"run":name,"g6":rec["g6"],"raw_bytes":raw_size})
                if size<proof_sizes.get(rec["g6"],float("inf")):
                    proofs[rec["g6"]]=(rec,name)
                    proof_sizes[rec["g6"]]=size
        else:
            assert rec["verdict"]=="unknown" and isinstance(rec["cert"]["reason"],str)
            assert isinstance(rec["cert"]["budget"],dict)
    all_records[name]=[{"g6":r["g6"],"verdict":r["verdict"]} for r in records]
    print(json.dumps({"replayed":name,"refuted":summary["refuted"]}),flush=True)

for suite in ["amp","b9"]:
    for method in method_codes:
        rows=all_records[suite+"-"+method]
        expected=(F/(suite+".g6")).read_text().splitlines()
        assert [r["g6"] for r in rows]==expected
        assert all(r["verdict"]=="unknown" for r in rows)
named=json.loads((F/"named.json").read_text())
for method in method_codes:
    records={r["g6"]:r for r in all_records["named-"+method]}
    for name in ["prism","petersen","spindle"]:
        assert records[named[name]]["verdict"]=="unknown"
    if method in ("tree","null","real"):
        for name in ["K4","K23","mobius10"]:
            assert records[named[name]]["verdict"]=="refuted"

cli_path=E/"cli-gp74.jsonl"
cli=[json.loads(line) for line in cli_path.read_text().splitlines()]
assert [r["g6"] for r in cli]==gp
cli_unknown=[r["g6"] for r in cli if r["verdict"]=="unknown"]
assert (E/"cli-gp74.UNKNOWN.g6").read_text().splitlines()==cli_unknown
assert hashlib.sha256(cli_path.read_bytes()).hexdigest()==json.loads((E/"cli-before-resume.json").read_text())["sha256"]
assert len((E/"cli-gp74.jsonl.timings.jsonl").read_text().splitlines())==len(gp)
for rec in cli:
    if rec["verdict"]=="refuted":
        with timed(30):verify(rec["g6"],rec["cert"],[],{})
        size=len(json.dumps(rec,sort_keys=True).encode())
        if size<proof_sizes.get(rec["g6"],float("inf")):
            proofs[rec["g6"]]=(rec,"cli-gp74")
            proof_sizes[rec["g6"]]=size
current=[json.loads(line) for line in (E/"cli-current-real.jsonl").read_text().splitlines()]
assert len(current)==1 and current[0]["verdict"]=="refuted"
assert isinstance(current[0]["cert"]["sturm"],str) and "_" in current[0]["cert"]["sturm"]
verify(current[0]["g6"],current[0]["cert"],[],{})
known=json.loads((F/"positive-tree.json").read_text())
verify(known["g6"],known["cert"],[],{})
tu=[json.loads(s) for s in (E/"cli-tu.jsonl").read_text().splitlines()]
assert len(tu)==1 and tu[0]["verdict"]=="refuted" and tu[0]["cert"]["steps"]
verify(tu[0]["g6"],tu[0]["cert"],[],{known["g6"]:known})
assert (E/"cli-tu.UNKNOWN.g6").read_text()==""

combined=[]
for code in gp:
    if code in proofs:
        combined.append(proofs[code][0])
    else:
        runs=[{"name":name,"seconds_per_graph":s["seconds_per_graph"],"max_states":s["max_states"],
               "all_sat":s.get("all_sat",False),"extra_sat":s.get("extra_sat",[])}
              for name,s in summaries.items() if s["suite"]=="gp74" and any(row["g6"]==code for row in s["rows"])]
        combined.append({"g6":code,"verdict":"unknown","cert":{"reason":"no certificate in measured control runs",
                         "budget":{"runs":runs}}})
with (E/"GP74.combined.jsonl").open("w") as out:
    for record in combined:out.write(json.dumps(record,sort_keys=True)+"\n")
unknown=[r["g6"] for r in combined if r["verdict"]=="unknown"]
(E/"GP74.UNKNOWN.g6").write_text("\n".join(unknown)+("\n" if unknown else ""))
with (E/"GP74.refuted.jsonl").open("w") as out:
    for record in combined:
        if record["verdict"]=="refuted":out.write(json.dumps(record,sort_keys=True)+"\n")
import runpy
saved_argv=sys.argv
try:
    sys.argv=[str(MODULE/"export_checker.py"),str(E/"GP74.combined.jsonl"),"--out-dir",str(E/"checker-sample")]
    runpy.run_path(str(MODULE/"export_checker.py"),run_name="__main__")
finally:
    sys.argv=saved_argv
export=json.loads((E/"checker-sample/export.json").read_text())
export_count=0;export_max_bytes=0;export_unknown=[]
with (E/"checker-sample/records.jsonl").open() as source:
    for line in source:
        export_count+=1;export_max_bytes=max(export_max_bytes,len(line.encode()))
        record=json.loads(line)
        if "sturm" in record["cert"]:assert isinstance(record["cert"]["sturm"],str)
        if record["verdict"]=="unknown":export_unknown.append(record["g6"])
assert export_count==len(gp) and export["local_replay"]=="PASS"
assert export_max_bytes<=8*1024*1024
assert (E/"checker-sample/input.g6").read_text().splitlines()==sorted(gp)
assert (E/"checker-sample/UNKNOWN.g6").read_text().splitlines()==sorted(export_unknown)
for i in [4,9,10,17,18]:
    assert gp[i] in method_codes["real"]
wrong_frame=json.loads((E/"wrong-frame.json").read_text())
assert wrong_frame["status"]=="PASS" and wrong_frame["unsafe_identity_equals_one"]
assert not wrong_frame["false_refutation_emitted_by_producer"]
selftest=json.loads((E/"selftest.json").read_text())
assert selftest["status"]=="PASS"
audit={"status":"PASS_LOCAL_REPLAY", "gp_total":len(gp),"gp_refuted":len(proofs),"gp_unknown":len(unknown),
       "gp_unknown_indices":[gp.index(c) for c in unknown],"combined_certificate_types":dict(Counter(r["cert"]["type"] for r in combined if r["verdict"]=="refuted")),"per_method_union":{k:len(v) for k,v in method_codes.items()},
       "replayed_method_certificates":dict(checked),"soundness_inputs_per_method":len(all_records["amp-tu"])+len(all_records["b9-tu"])+3,
       "false_refutations":0,"wrong_frame_control":wrong_frame,"cli_records":len(cli),"cli_verdicts":dict(Counter(r["verdict"] for r in cli)),
       "cli_unknown_exact":True,"resume_bytes_unchanged":True,"known_cli_accepted":True,"current_sturm_cli_accepted":True,
       "export_records":export_count,"export_max_record_bytes":export_max_bytes,"oversized_method_records":oversized_records,
       "tree_source_unchanged":True,"input_hashes_unchanged":True,
       "independent_gp10_format_exists":(ROOT/"research/gp-10/check/FORMAT.md").exists(),
       "independent_gp10_checker_exists":(ROOT/"research/gp-10/check/gp10check.py").exists(),
       "seconds":time.monotonic()-start,"argv":sys.argv,
       "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(MODULE.glob("*.py"))}}
(E/"final-audit.json").write_text(json.dumps(audit,indent=2)+"\n")

lines=["# C-REFUTER report", "", 
 f"Implemented the requested producer and all four certificate methods. The saved control runs refute {len(proofs)} of {len(gp)} GP graphs and leave {len(unknown)} unknown ({len(unknown)/len(gp):.1%}). The all-GP coverage control is therefore NOT satisfied. No GP-10 classification claim is made, and no B10 production run was started.","",
 "The deliverables are `gp10refute.py`, `graphs.py`, `amp_core.py`, `algebra.py`, `FORMAT.md`, `PROOFS.md`, `VENDOR.md`, the control and audit scripts, and the saved fixtures and evidence. `PROOFS.md` documents identities used to accelerate allowed certificates. No new move or certificate type was added; no contract amendment is proposed.","",
 "The polynomial checker format was absent when implementation began and appeared during final review. New output now matches its string Sturm field and underscore variable names. `export_checker.py` prepares copies for checker review and can translate the historical object-form Sturm field without changing any coefficients. The checker implementation itself was still absent. Local replay is not independent GP-10 checker acceptance. Its documented nonempty-TU restriction and F9-global forbidden indices still need reconciliation with the contract semantics used here.","",
 "## Implementation and resource rules","",
 "TU repeatedly adds justified gadget pairs and requires a checked terminal forbidden or previously refuted subgraph. A bare gadget match never refutes. The optional known file is validated, its dependencies must be acyclic, and self endpoints are rejected. An empty list with no known endpoints necessarily yields no TU refutations.","",
 "The AMP core is vendored with provenance and its original source hash. It sets `SYMPY_GROUND_TYPES=python`, uses `DomainMatrix.to_list()`, visits both L3 children after an unknown, and removes the coordinate catalog and all tikz dependencies. Its seed is derived from the canonical graph's SHA256. Every emitted tree was checked by the original `udcheck.verify_refutation` kernel.","",
 "Singular receives only expanded polynomials and must return exact marker lines. The wrapper also checks its lifted sum before export. Python-flint expands every final identity in the regenerated edge-frame and saturation system. Rhombus helper cofactors are substituted out, so none of their equations become unproved generators. R-real searches individual basis members for a zero-free univariate polynomial or a positive rational quadratic sum of squares. It prefers targets in coordinate variables over inverse variables. This is a limited search, not a complete real-algebraic solver.","",
 "Outputs are canonical, flushed and fsynced per record. Resume binds the input, list, known file, options, and core source hashes. It replays completed refutations, repairs a torn last line, rebuilds UNKNOWN exactly, and converts a journalled interrupted graph to unknown on resume. TU/tree workers and Singular failures become unknown attempts. A main-process native crash still requires restarting with the same arguments.","",
 f"The contract's stricter memory rule was used instead of COMMON's larger allowance. The measured address-space limit was {selftest['environment']['RLIMIT_AS'][0]} bytes, with niceness {selftest['environment']['nice']}. Commands after the initial required-file read used `ulimit -v 976562` and `nice -n 15`. The first read used `nice -n 10` before the detailed common rules had been read. Each numerical command used the frozen Python; each search architecture has at most the parent and one child. No git command, installation, oversight task, or original unit-distance module edit was performed.","",
 f"Measured environment from `selftest.py`: SymPy {selftest['environment']['sympy']}, python-flint {selftest['environment']['flint']}, SYMPY_GROUND_TYPES={selftest['environment']['SYMPY_GROUND_TYPES']}.","",
 "## Coverage and timing","",
 "Initial sweeps on the complete GP list used an empty forbidden list and no known endpoints. Refutation counts overlap between methods. Times are measured wall seconds, including local certificate checks. All totals and rates below are generated by `audit_report.py` from the saved summaries.","",
 "| Method | Refuted | Unknown | Unknown rate | Seconds per graph | Total seconds |",
 "|---|---:|---:|---:|---:|---:|"]
for method in method_codes:
    s=summaries["gp74-"+method]
    lines.append(f"| {method} | {s['refuted']} | {s['unknown']} | {s['unknown']/s['count']:.1%} | {s['seconds_per_graph']:g} | {s['total_seconds']:.3f} |")
lines += ["", "Focused retries are stated samples. They do not imply the same budget was used on the entire list.","",
          "| Saved run | Sample size | Refuted in sample | Seconds per graph | Total seconds |",
          "|---|---:|---:|---:|---:|"]
for name,s in summaries.items():
    if s["suite"]=="gp74" and name not in {"gp74-"+m for m in method_codes}:
        lines.append(f"| {name} | {s['count']} | {s['refuted']} | {s['seconds_per_graph']:g} | {s['total_seconds']:.3f} |")
lines += ["", "The cumulative per-method GP coverage across those runs is "+", ".join(f"{m}: {len(c)}/{len(gp)}" for m,c in method_codes.items())+". R-real includes positive-constant identities where R-null also applies.","",
 "All designated real-only regressions, JSON indices 4, 9, 10, 17, 18, have R-real records. Index 17 used the explicit extra saturation pair `[3,7]` in canonical labels, as recorded in `gp74-real-extra.summary.json`. This was a targeted mathematical choice, not a producer lookup keyed to that graph. Other focused cases used the default four-cycle-diagonal saturation set.","",
 f"`GP74.combined.jsonl` contains exactly {len(gp)} records, choosing the smallest existing verified record when one was found. `GP74.UNKNOWN.g6` lists its {len(unknown)} unresolved graphs exactly. This union uses different budgets and is not a single default-budget producer run.","",
 "The remaining stalls are:",""]
retry=summaries["gp74-tree-retry"]
for c in unknown:
    i=gp.index(c);row=next(r for r in retry["rows"] if r["g6"]==c);d=row["detail"]
    lines.append(f"- Index {i}, original g6 ``{prep['gp_original'][i]}``, canonical g6 ``{c}``: {d.get('states')} tree states, moves {d.get('moves')}, stops {d.get('stops')}, {d['seconds']:.3f} seconds within a {d['limit']:g}-second allocation.")
lines += ["", "These are completed no-move leaves, not state-limit exhaustion. More time alone does not change this implementation's fixed points. A stronger move, a different search strategy, or stronger polynomial search is needed. I have not proved that every alternative AMP move order fails. The all-saturation null and real samples did not resolve them. `LABNOTES.md` records why the coverage gate remains open.","",
 "## Controls and CLI validation","",
 "K4, K2,3 and the Moebius ladder were each refuted by tree, null and real methods with the empty list. TU had no terminal endpoint in that test and returned unknown. The pentagonal prism, Petersen graph and Moser spindle returned unknown under each method. The refuter does not emit embedding certificates.","",
 "| Soundness sample | Inputs | Method | Refuted | Budget per graph | Total seconds |",
 "|---|---:|---|---:|---:|---:|"]
for suite in ["amp","b9"]:
    for method in method_codes:
        s=summaries[suite+"-"+method]
        lines.append(f"| {suite} | {s['count']} | {method} | {s['refuted']} | {s['seconds_per_graph']:g} | {s['total_seconds']:.3f} |")
a=json.loads((E/"sample-audit.json").read_text())
lines += ["",f"There were no false refutations on the {audit['soundness_inputs_per_method']} prescribed embeddable inputs per method. All these verdicts were unknown; this does not certify their embeddings. TU soundness runs used the full forbidden list as a possible terminal, so the test could detect a bad inference. GP coverage runs used the empty list.","",
 f"The B9 sample took the first F9-free graphs in SHA256 order. Selection scanned {prep['b9_candidates_scanned']} candidates. A separate NetworkX monomorphism audit checked all {a['count']} selected graphs, making {a['comparisons']} eligible comparisons in {a['seconds']:.3f} seconds. It shares no subgraph-matching implementation with the producer.","",
 f"`selftest.py` passed {selftest['count']} recorded checks. Genuine tree, null, real-Sturm, real-SOS, and TU certificates pass before one-field mutations are rejected for their asserted reason. The controls cover coefficient changes, extra equations, nonedge frames, invalid TU endpoints, bare gadgets, nonpositive SOS constants, wrong Sturm variables, CAS no answers, L3's second child, exceptions, child crashes, timeouts, resume mismatch and recovery, and pointer cycles.","",
 "The full pentagonal prism red demonstration passes in `wrong_frame_control.py`. An exact real-field embedding validates the correct frame and all pair distances. Only the frame field is changed, from `[0,1]` to nonedge `[0,5]` in canonical labels, with the saturation list unchanged. Deliberately bypassing the guard gives a Singular lift whose expansion is exactly one for the wrongly framed prism. The production verifier rejects that false certificate with `frame: not an edge`, and the outer soundness assertion goes red for the expected reason. A one-coordinate mutation of the genuine embedding also fails with a collision reason. The fixture coordinates are not claimed as a general-search named embedding control.","",
 f"The actual default CLI run used a {json.loads((E/'cli-gp74.jsonl.meta.json').read_text())['seconds']:g}-second graph budget and produced {len(cli)} records: "+", ".join(f"{n} {v}" for v,n in sorted(Counter(r['verdict'] for r in cli).items()))+f". Its unknown rate was {len(cli_unknown)/len(cli):.1%}. The UNKNOWN file was exact. Re-running the same command resumed every record without changing output bytes or duplicating timing rows. A separate CLI run with `--refuted` emitted a TU chain to a validated known tree record.","",
 f"Final local replay checked {sum(checked.values())} method-run refutation records, plus CLI outputs, with no rejection. The original AMP source and frozen control input hashes still match the values recorded when read. All module Python files compile without writing bytecode.","",
 f"The checker-ready sample is in `evidence/checker-sample/`, with a sample manifest and sorted input and unknown lists. Its chosen certificate types are {audit['combined_certificate_types']}. A separate `evidence/checker-real-sample/` exercises the current string-form Sturm certificate. The historical larger polynomial records remain in their original evidence files. It is prepared for independent replay and has not received independent ACCEPT. Historical source-bound CLI outputs cannot be resumed under the final formatter revision; use a new output path. The original resume checks were completed before that revision.","",
 f"The initial final-audit aggregation hit the address-space cap while holding duplicate large evidence objects. It was changed to retain compact summaries, select the smallest available certificate per graph, and stream combined output. The final checker sample has a maximum record size of {export_max_bytes} bytes. There are {len(oversized_records)} larger per-method records exceeding the checker document\'s line ceiling; they remain in the raw evidence and are not the selected combined proofs.","",
 "## Commands actually run","",
 "All paths below are relative to the repository root. Each invocation used this prefix:","",
 "```sh","ulimit -v 976562","exec nice -n 15 <repo>/pyenv-gp10/bin/python -B SCRIPT_AND_ARGUMENTS","```","",
 "Substitute each following line for `SCRIPT_AND_ARGUMENTS`. Existing sweep evidence is intentionally not overwritten; use a new `--tag` when repeating an individual sweep. The small and focused runner files contain the exact subrun argument lists.","","```text",
 "research/gp-10/refute/controls.py --prepare",
 "research/gp-10/refute/audit_sample.py",
 "research/gp-10/refute/controls.py --suite gp74 --method tree --seconds 3",
 "research/gp-10/refute/controls.py --suite gp74 --method null --seconds 3",
 "research/gp-10/refute/controls.py --suite gp74 --method real --seconds 3",
 "research/gp-10/refute/controls.py --suite gp74 --method tree --seconds 12 --indices 16,17,18,22,38,39,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,73 --tag=-retry",
 "research/gp-10/refute/controls.py --suite gp74 --method null --seconds 10 --indices 16,22,38,39,59,66,67,68,69 --all-sat --tag=-all-sat",
 "research/gp-10/refute/run_small_controls.py",
 "research/gp-10/refute/controls.py --suite b9 --method tu --seconds 0.4",
 "research/gp-10/refute/controls.py --suite b9 --method tree --seconds 0.4 --progress-every 50",
 "research/gp-10/refute/controls.py --suite b9 --method null --seconds 0.4 --progress-every 50",
 "research/gp-10/refute/controls.py --suite b9 --method real --seconds 0.4 --progress-every 50",
 "research/gp-10/refute/run_focused_controls.py",
 "research/gp-10/refute/selftest.py",
 "research/gp-10/refute/wrong_frame_control.py",
 "research/gp-10/refute/gp10refute.py research/gp-10/refute/fixtures/gp74.g6 --out research/gp-10/refute/evidence/cli-gp74.jsonl --unknown research/gp-10/refute/evidence/cli-gp74.UNKNOWN.g6 --time-limit 3 --forbidden research/gp-10/refute/fixtures/empty.json",
 "research/gp-10/refute/gp10refute.py research/gp-10/refute/fixtures/tu-known.g6 --out research/gp-10/refute/evidence/cli-tu.jsonl --unknown research/gp-10/refute/evidence/cli-tu.UNKNOWN.g6 --time-limit 2 --forbidden research/gp-10/refute/fixtures/empty.json --refuted research/gp-10/refute/fixtures/positive-tree.json --methods tu",
 "research/gp-10/refute/export_checker.py research/gp-10/refute/evidence/GP74.combined.jsonl --out-dir research/gp-10/refute/evidence/checker-sample",
 "research/gp-10/refute/gp10refute.py research/gp-10/refute/fixtures/real-current.g6 --out research/gp-10/refute/evidence/cli-current-real.jsonl --unknown research/gp-10/refute/evidence/cli-current-real.UNKNOWN.g6 --time-limit 3 --forbidden research/gp-10/refute/fixtures/empty.json --methods real",
 "research/gp-10/refute/export_checker.py research/gp-10/refute/evidence/cli-current-real.jsonl --out-dir research/gp-10/refute/evidence/checker-real-sample",
 "research/gp-10/refute/audit_report.py","```","",
 "The main GP CLI command was executed again to exercise resume. The final audit writes `evidence/final-audit.json`, the combined GP records, and this report. Detailed graph timings, reasons, budgets, and applicable source hashes are in the per-run summary files.","",
 "## UNCERTAIN","",
 "- The named unresolved graphs still prevent the required complete GP coverage control. No full B10 run, full B8/B9 pipeline control, minimality derivation, or GP-10 gate acceptance was exercised.",
 "- The independent GP-10 checker code was not present. Its format document has been matched for polynomial records, but empty TU chains and arbitrary shorter forbidden-list indexing still need reconciliation. Generator reconstruction and variable ordering are the most likely places for an integration bug. The local polynomial verifier shares its system builder with the producer, although it expands identities independently of Singular.",
 "- The finite soundness budgets often timed out. They cannot exclude bugs appearing after deeper searches, larger algebraic fields, or larger certificates. Some raw polynomial records exceed the documented checker line-size limit and need smaller certificates or a reviewed checker budget change. The saturated real search is incomplete and does not synthesize general sums of squares or prove general real infeasibility.",
 "- Alternative L3 move orders were not exhausted. The fixed-point observations justify rejecting a simple time-only remedy for this implementation, not a theorem that all searches in the existing calculus must fail.",
 "- A real main-process SIGKILL and a deliberate producer memory-exhaustion allocation were not induced. The audit aggregation did encounter and recover from a real address-space MemoryError. Journal recovery was simulated, and a child process exit was exercised. Python signals can be delayed inside native arithmetic. A main-process native crash requires resume to recover the pending graph.",
 "- Search seeds and enumeration are deterministic. Wall-clock deadlines can change near-limit outcomes under load, and timing fields prevent byte-identical unknown records across fresh runs. Completed resume output was byte-identical.",
 "- The deliberately unsafe nonedge-frame identity is retained only as a red fixture. It must not be mixed into production record streams. Production tests reject it, and its exact positive embedding was verified separately.",
 "- Earlier sweeps precede the final R-real target-order improvement and journal/extra-saturation options. The saved measurements are observations of those actual runs. Focused real checks, the final AMP real sweep and the B9 real sweep exercised the final mathematical implementation. Self-tests, historical-record conversion, and a new real CLI run exercised the final Sturm formatter. Historical records remain locally readable."]
(MODULE/"REPORT.md").write_text("\n".join(lines)+"\n")
print(json.dumps({k:v for k,v in audit.items() if k!="source_sha256"},indent=2))
