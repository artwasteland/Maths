#!/usr/bin/env python3
"""Gate G6 of research/unit-distance-23/CONTRACT.md: RESULT-u23.md generated from checker and manifest output only.

usage: python write_result.py [--root DIR] [--audit-worktree DIR] [--g5-ref REF] [--outputs DIR]
                              [--aggregate-json FILE [--aggregate-exit N]] [--audit-log FILE [--audit-exit N]]
                              [--top-level-log FILE [--top-level-exit N]] [--level22-log FILE [--level22-exit N]]
                              [--verify-root DIR | --verify-log FILE [--verify-exit N]] [--values FILE] [--out FILE]
       python write_result.py --from-values FILE [--headline-only | --out FILE]
       python write_result.py --self-test [--from-values FILE]

1. Collect. Runs each tool (or reads its saved output: --aggregate-json, --audit-log, --top-level-log, --level22-log)
   and keeps what it ran under --outputs (default results/u23/result-inputs/):
     aggregate_fleet.py --root ROOT --self-check --out aggregate.json   tree, coverage, G4, cost, provenance (it runs
                                                                        top_level_check.py itself)
     top_level_check.py ROOT --self-test                                CONTRACT Section 3, with the tamper control
     level22_control.py ROOT --self-test                                CONTRACT Section 4.3 at level 22: the known
                                                                        configurations survive, with its red controls
     verify_sample.py --verify-root VROOT --root ROOT                   G5's point 6, the human's option 1: the sampled
                                                                        slices re-run with nothing deleted and checked
                                                                        whole (VROOT: verify_sample.py --fetch, before)
     fleet-audit.py --root ROOT                                         verify-chain.py --summary-only over every slice;
                                                                        it lives on branch claude/answering-alexeev-u22-g5,
                                                                        run in --audit-worktree
   It also reads the G5 round-9 read and item 6 of the closure read (git show --g5-ref), CONTRACT.md (the sentences
   the document quotes verbatim), JOBS.md's u23-fleet entry, and the records under results/u23/top-level; and it
   fingerprints the root before and after, since a background collector rewrites it.
2. Extract. Every value the document shows, with its source (an output file and key, or a formula over other
   values), into --values (default results/u23/result-values.json).
3. Decide and render, from the values alone. The headline is COMPLETE only when coverage is complete (all slices,
   none needing a rerun), the audit has no problem and nothing unresolved, the top level is decided (every kept graph
   refuted by a certificate both checkers accept, and accepted by the blind second verifier, which rejects each of
   its tampered copies), every G4 replay passed, the aggregate has no problem and its
   self-check holds, the audit and the aggregate read one snapshot, and the known-graph control finds every required
   graph with its own red controls red (with coverage complete, a control that does not is the state CONTROL FAILED:
   the enumeration lost a graph it must keep, or the control is broken), and every sampled slice passed its re-run
   and check (one that failed is the state VERIFICATION FAILED; one not yet verified keeps the draft INCOMPLETE).
   Otherwise it lists what is not. Even then the
   document is a DRAFT for the human, and it gives u(23) only under the gates' condition.
Then the G6 lint: outside the values, the fixed text holds no numeral but section, gate and function labels, no status
word (PASS, OK, COMPLETE, ...), and every "u(23) = n" sits in a conditional sentence. A lint failure writes nothing.

--from-values FILE re-decides and re-renders from a values file (an edited copy for a what-if); it writes a document
only to an explicit --out. --self-test runs the decision and the lint on in-memory what-ifs (complete; complete with an
unrefuted top-level graph; complete but one slice missing; complete but one known graph missing) and the lint's red
controls.
Exit: 0 written, COMPLETE; 3 written, not complete; 1 lint or self-test failure; 2 an input could not be read.
"""
import argparse, copy, hashlib, json, os, re, shlex, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode = True   # importing fleet_status must not write a __pycache__ into the checkout
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import fleet_status as fs   # noqa: E402  the plan's slice-directory kind
import verify_sample as vsm   # noqa: E402  the sample's and the full re-run's plans, read as the judge reads them

U23 = HERE.parents[1]
REPO = HERE.parents[3]
RESULTS = U23 / "results" / "u23"
ROOT = Path("<scratch>/scratchpad/fleet/results")
AUDIT_WORKTREE = Path("<repo>/.claude/worktrees/agent-a3c9dc31ac1640180")
G5_BRANCH = "claude/answering-alexeev-u22-g5"
AUDIT_TOOL = "research/unit-distance-22/enum/test-rhombus/fleet-audit.py"
VERIFY_CHAIN = "research/unit-distance-22/enum/verify-chain.py"
G5_DIR = "research/unit-distance-23/results/g5-cross-model-2026-09-26"
G5_ROUND9 = f"{G5_DIR}/G5-round9-read-gpt-6-astra.md"
G5_CLOSURE = f"{G5_DIR}/G5-closure-read-gpt-6-astra.md"
CONTRACT = U23 / "CONTRACT.md"
JOBS = REPO / "coordination/cloud-workers/JOBS.md"
# The one numeral of the template that no tool and no CONTRACT sentence supplies: a parameter of the options put to
# the human (Section 6), stated by the supervisor. It is listed in result-values.json with that source.
ENGEL_2157_SHA256 = "06f0d779a598292e6be4e2758097d7e0a1c2364fc348cda7d197751ed2a98aff"   # AMP's five (21,57) graphs
CONSTANTS = {"point6_sample_percent": ("2.5", "the supervisor's statement of the pending options for GPT's point 6 "
                                              "(a parameter of a proposal, not a tool output)"),
             "control22_cell": ("(22,61)", "CONTRACT Section 4.1, the (22,61) tree again (JOBS.md, u23-control22)"),
             "control22_root_k": ("5", "Lemma D4, the (22,61) root minimum degree (run-dag2.py ROOT_K_LEMMAS)"),
             "calib_cell": ("(21,57)", "CONTRACT Section 4.3, the (21,57) calibration (JOBS.md, u23-calib2157)"),
             "calib_root_k": ("3", "Schade's bound at (21,57): 57 - u-bar(20) = 57 - 54"),
             "calib_known": ("five", "engel-21-57.g6: AMP's extremal (21,57) graphs, five of them")}

MARK_L, MARK_R = "\x02", "\x03"   # around every value in the rendered text, for the lint; stripped before writing
OK_REPLAY = ("PASS", "EMPTY")


class InputError(Exception):
    pass


def E(x, spec: str = "") -> str:
    """A value, formatted and marked so the lint can tell it from the fixed text."""
    if isinstance(x, bool):
        s = "yes" if x else "no"
    elif isinstance(x, int):
        s = format(x, spec or ",")
    elif isinstance(x, float):
        s = format(x, spec or ",.1f")
    elif x is None:
        s = "none"
    else:
        s = str(x)
    return MARK_L + s + MARK_R


def strip(text: str) -> str:
    return text.replace(MARK_L, "").replace(MARK_R, "")


def ranges(xs) -> str:
    xs, out = sorted(int(x) for x in xs), []
    for x in xs:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in out)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    p = Path(p).resolve()
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)


def iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def git(*args, cwd: Path = REPO) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise InputError(f"git {' '.join(args)} (in {cwd}): {r.stderr.strip()[:300]}")
    return r.stdout


# ---------------------------------------------------------------------------------------------------------- collect

def run_tool(cmd: list, out: Path, cwd: Path) -> dict:
    t0 = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    out.write_text(r.stdout)
    err = out.with_name(out.name + ".err")
    if r.stderr.strip():
        err.write_text(r.stderr)
    elif err.exists():
        err.unlink()
    return {"command": shlex.join(str(c) for c in cmd), "cwd": rel(cwd), "exit": r.returncode, "stdout": rel(out),
            "started_utc": iso(t0), "seconds": round(time.time() - t0, 1)}


def root_fingerprint(root: Path) -> dict:
    """Every slice copy's run-summary.json, top-level and level-22 keep files and replay summary: path, size, mtime
    (the collector's tar extraction stamps a branch's commit time, so an unchanged branch leaves this unchanged)."""
    h, n = hashlib.sha256(), 0
    for pat in ("run-summary.json", "23-65.keep.g6", "22-60.keep.g6", "replay/summary.json"):
        for p in sorted(root.glob(f"*/research/unit-distance-23/results/u23/{fs.KIND}/s*of*/{pat}")):
            st = p.stat()
            h.update(f"{p.relative_to(root)}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
            n += 1
    return {"files": n, "sha256": h.hexdigest(), "utc": iso(time.time())}


def collect(a) -> dict:
    """Run (or read) every source; return {name: {...provenance, "text" or "json"}}."""
    src = {}
    root = a.root.resolve()
    if not root.is_dir():
        raise InputError(f"no fleet extraction at {root}")
    out = a.outputs.resolve()
    out.mkdir(parents=True, exist_ok=True)
    src["root"] = {"path": str(root), "before": root_fingerprint(root)}
    py = sys.executable
    # aggregate_fleet.py (it runs top_level_check.py itself)
    if a.aggregate_json:
        src["aggregate"] = {"command": "(saved output)", "exit": a.aggregate_exit, "json_path": rel(a.aggregate_json)}
        jpath = a.aggregate_json
    else:
        jpath = out / "aggregate.json"
        src["aggregate"] = run_tool([py, HERE.parent / "aggregate_fleet.py", "--root", root, "--self-check",
                                     "--out", jpath], out / "aggregate.md", REPO)
        src["aggregate"]["json_path"] = rel(jpath)
    try:
        src["aggregate"]["json"] = json.loads(Path(jpath).read_text())
    except (OSError, ValueError) as e:
        raise InputError(f"aggregate record {jpath}: {e}") from None
    src["aggregate"]["sha256"] = sha256(Path(jpath))
    # top_level_check.py --self-test
    if a.top_level_log:
        src["top_level_check"] = {"command": "(saved output)", "exit": a.top_level_exit, "stdout": rel(a.top_level_log)}
        tpath = a.top_level_log
    else:
        tpath = out / "top-level-check.txt"
        src["top_level_check"] = run_tool([py, HERE.parent / "top_level_check.py", root, "--self-test"], tpath, REPO)
    src["top_level_check"]["text"] = Path(tpath).read_text()
    src["top_level_check"]["sha256"] = sha256(Path(tpath))
    # level22_control.py --self-test
    if a.level22_log:
        src["level22_control"] = {"command": "(saved output)", "exit": a.level22_exit, "stdout": rel(a.level22_log)}
        lpath = a.level22_log
    else:
        lpath = out / "level22-control.txt"
        src["level22_control"] = run_tool([py, HERE.parent / "level22_control.py", root, "--self-test"], lpath, REPO)
    src["level22_control"]["text"] = Path(lpath).read_text()
    src["level22_control"]["sha256"] = sha256(Path(lpath))
    # verify_sample.py (the verification workers' branches extracted beforehand, with --fetch)
    if a.verify_log:
        src["verify_sample"] = {"command": "(saved output)", "exit": a.verify_exit, "stdout": rel(a.verify_log)}
        vpath = a.verify_log
    else:
        vpath = out / "verify-sample.txt"
        src["verify_sample"] = run_tool([py, HERE.parent / "verify_sample.py", "--verify-root", a.verify_root.resolve(),
                                         "--root", root], vpath, REPO)
    src["verify_sample"]["text"] = Path(vpath).read_text()
    src["verify_sample"]["sha256"] = sha256(Path(vpath))
    # CONTRACT 4.1 and 4.3's whole-tree controls (target_check.py) and the full re-run (verify_sample.py --all): each
    # optional until its results exist; its saved output, or a run over its root
    engel2157 = REPO / "research/unit-distance-22/sources/engel-dataset/engel-21-57.g6"
    for name, fname, log, lexit, troot, argv in (
            ("control22", "control22-check.txt", a.control22_log, a.control22_exit, a.control22_root,
             ["--target", "22", "61", "--root-k", "5", "--no-ubar", "--expect-empty", "--self-test"]),
            ("calib2157", "calib2157-check.txt", a.calib_log, a.calib_exit, a.calib_root,
             ["--target", "21", "57", "--sub", "calib-21-57", "--root-k", "3", "--known", engel2157, "--self-test"])):
        if log:
            src[name] = {"command": "(saved output)", "exit": lexit, "stdout": rel(log)}
            path = log
        elif troot and Path(troot).is_dir():
            path = out / fname
            src[name] = run_tool([py, HERE.parent / "target_check.py", "--root", Path(troot).resolve(), *argv], path, REPO)
        else:
            src[name] = {"command": f"(not run: no results at {troot})", "exit": None, "text": "", "sha256": None}
            continue
        src[name]["text"] = Path(path).read_text()
        src[name]["sha256"] = sha256(Path(path))
    if a.verify_all_log:
        src["verify_all"] = {"command": "(saved output)", "exit": a.verify_all_exit, "stdout": rel(a.verify_all_log)}
        path = a.verify_all_log
    elif a.verify_all_root and Path(a.verify_all_root).is_dir():
        path = out / "verify-all.txt"
        src["verify_all"] = run_tool([py, HERE.parent / "verify_sample.py", "--all", "--verify-root",
                                      Path(a.verify_all_root).resolve(), "--root", root], path, REPO)
    else:
        path = None
        src["verify_all"] = {"command": f"(not run: no results at {a.verify_all_root})", "exit": None, "text": "",
                             "sha256": None}
    if path:
        src["verify_all"]["text"] = Path(path).read_text()
        src["verify_all"]["sha256"] = sha256(Path(path))
    # the fleet's G4 replays, each in its mode's scope (G5 round 14: the audit does not require a full replay's scope)
    spath = out / "g4-scope.txt"
    src["g4_scope"] = run_tool([py, HERE.parent / "target_check.py", "--root", root, "--target", "23", "65",
                                "--root-k", "5", "--scope-only"], spath, REPO)
    src["g4_scope"]["text"] = spath.read_text()
    src["g4_scope"]["sha256"] = sha256(spath)
    # G5 round 23, finding 2: the copies the scope report must have covered, recomputed here from the credited root
    # (label, target, replay mode, the replay summary's and hashes.json's digests: target_check.copies_lines)
    cl_ = vsm.tc.copies_lines(Path(root), "u23", 23, 65)
    src["g4_scope"]["expected_copies"] = [len(cl_), hashlib.sha256("\n".join(cl_).encode()).hexdigest()]
    # G5 round 24, finding 1: and the root's copies by identity, to be the aggregate's own
    lb_ = sorted(x.split(" ")[0] for x in cl_)
    src["g4_scope"]["root_labels"] = [len(lb_), hashlib.sha256("\n".join(lb_).encode()).hexdigest()]
    # blind_check.py: the blind second verifier over every top-level record, and its tampered copies
    if a.blind_log:
        src["blind_check"] = {"command": "(saved output)", "exit": a.blind_exit, "stdout": rel(a.blind_log)}
        bpath = a.blind_log
    else:
        bpath = out / "blind-check.txt"
        src["blind_check"] = run_tool([py, HERE.parent / "blind_check.py"], bpath, REPO)
    src["blind_check"]["text"] = Path(bpath).read_text()
    src["blind_check"]["sha256"] = sha256(Path(bpath))
    # the fleet audit, on the G5 branch
    wt = a.audit_worktree.resolve()
    if a.audit_log:
        src["audit"] = {"command": "(saved output)", "exit": a.audit_exit, "stdout": rel(a.audit_log)}
        apath = a.audit_log
    else:
        if not (wt / AUDIT_TOOL).is_file():
            raise InputError(f"no {AUDIT_TOOL} in --audit-worktree {wt}")
        apath = out / "fleet-audit.txt"
        src["audit"] = run_tool([py, wt / AUDIT_TOOL, "--root", root], apath, wt)
    src["audit"]["text"] = Path(apath).read_text()
    src["audit"]["sha256"] = sha256(Path(apath))
    if (wt / AUDIT_TOOL).is_file():
        src["audit"].update({"worktree": str(wt), "worktree_head": git("rev-parse", "HEAD", cwd=wt).strip(),
                             "worktree_branch": git("branch", "--show-current", cwd=wt).strip(),
                             "worktree_dirty": git("status", "--porcelain", "--", AUDIT_TOOL, VERIFY_CHAIN,
                                                   cwd=wt).strip(),
                             "fleet_audit_sha256": sha256(wt / AUDIT_TOOL),
                             "verify_chain_sha256": sha256(wt / VERIFY_CHAIN)})
    src["root"]["after"] = root_fingerprint(root)
    if a.aggregate_json or a.audit_log or a.top_level_log or a.level22_log or a.verify_log \
            or a.blind_log:   # saved: another snapshot (the controls' and the full re-run's roots are not the fleet's)
        src["root"].update(before=None, after=None, note="saved outputs: the root was not fingerprinted with them")
    # the G5 record, CONTRACT.md, JOBS.md, the top-level records
    ref = a.g5_ref
    src["g5"] = {"ref": ref, "commit": git("rev-parse", ref).strip(), "round9_path": G5_ROUND9,
                 "closure_path": G5_CLOSURE, "round9": git("show", f"{ref}:{G5_ROUND9}"),
                 "closure": git("show", f"{ref}:{G5_CLOSURE}")}
    # the rounds after the merge live on this branch: the latest one read, as committed at HEAD
    rounds = sorted((int(m.group(1)), q) for q in (REPO / G5_DIR).glob("G5-round*-read-*.md")
                    for m in [re.fullmatch(r"G5-round(\d+)-read-.*\.md", q.name)] if m)
    if rounds and rounds[-1][0] > 9:
        q = rounds[-1][1]
        src["g5_latest"] = {"round": rounds[-1][0], "path": rel(q),
                            "text": git("show", f"HEAD:{rel(q)}") if git("ls-files", rel(q)).strip() else "",
                            "committed": bool(git("ls-files", rel(q)).strip())}
    else:
        src["g5_latest"] = {"round": None, "path": None, "text": "", "committed": False}
    src["contract"] = {"path": rel(CONTRACT), "sha256": sha256(CONTRACT), "text": CONTRACT.read_text()}
    src["jobs"] = {"path": rel(JOBS), "sha256": sha256(JOBS), "text": JOBS.read_text()}
    recs = {}
    for d in sorted((RESULTS / "top-level").glob("s*of*")):
        m = re.fullmatch(r"s(\d+)of(\d+)", d.name)
        if not m:
            continue
        r = {"dir": rel(d)}
        if (d / "CHECK.txt").exists():
            r["check_txt"] = (d / "CHECK.txt").read_text()
        pm = d / "23-65.prune.manifest.json"
        if pm.exists():
            r["prune_manifest"] = json.loads(pm.read_text())
        if (d / "23-65.certs.jsonl").exists():
            r["certs_sha256"] = sha256(d / "23-65.certs.jsonl")
        recs[int(m.group(1))] = r
    src["records"] = recs
    src["repo"] = {"head": git("rev-parse", "HEAD").strip(), "branch": git("branch", "--show-current").strip(),
                   "tools_sha256": {p.name: sha256(p) for p in (HERE, HERE.parent / "aggregate_fleet.py",
                                                                HERE.parent / "top_level_check.py",
                                                                HERE.parent / "level22_control.py",
                                                                HERE.parent / "verify_sample.py",
                                                                HERE.parent / "fleet_status.py")},
                   "tools_dirty": git("status", "--porcelain", "--", str(HERE.parent)).strip()}
    return src


# ---------------------------------------------------------------------------------------------------------- extract

def section(text: str, n: int) -> str:
    m = re.search(rf"^## {n}\. .*$", text, re.M)
    if not m:
        raise InputError(f"CONTRACT.md has no Section {n}")
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start() if nxt else len(text)].strip("\n")


def bullets(body: str) -> list:
    """A section's top-level bullets, each joined to one line ('- ' dropped)."""
    out = []
    for line in body.splitlines():
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif line.startswith("  ") and out:
            out[-1] += " " + line.strip()
    return out


def one_line(s: str) -> str:
    return " ".join(s.split())


def extract_contract(text: str) -> dict:
    s0, s1, s2, s3, s8 = (section(text, n) for n in (0, 1, 2, 3, 8))
    intro = one_line(s0.split("\n- ", 1)[0])
    b0 = bullets(s0)
    need = {"claim_65": "We claim u(23) = 65", "claim_64": "We claim u(23) = 64", "never": "Never"}
    got = {k: next((b for b in b0 if b.startswith(p)), None) for k, p in need.items()}
    bounds = re.search(r"u\(23\) is (\d+) or (\d+)", intro)
    deps = re.search(r"(Section 0's dependencies gain .*?\.)(?=\s+[A-Z])", one_line(s8))
    slicing = re.search(r"\*\*Slicing\*\* at level (\d+)", s2)
    gates = dict(re.findall(r"^\| (G\d) \| (.*) \|$", section(text, 6), re.M))
    missing = [k for k, v in got.items() if not v] + [k for k, v in (("bounds", bounds), ("amendment 2 dependencies",
                                                                       deps), ("slicing level", slicing)) if not v]
    missing += [g for g in (f"G{i}" for i in range(7)) if g not in gates]
    if missing:
        raise InputError(f"CONTRACT.md: cannot find {missing}; the document quotes these verbatim")
    admits = {int(n): [int(lo), int(hi)] for lo, hi, n in re.findall(r"(\d+)\.\.(\d+) at (\d+)", s2)}
    admits.update({int(n): [int(m), int(m)] for m, n in re.findall(r"m = (\d+) only at level (\d+)", s2)})
    amended = re.search(r"\bslic(?:e|es|ing|ed)\b[^.]{0,80}?\blevel (\d+)", one_line(s8), re.I)
    return {**got, "intro": intro, "lower": int(bounds.group(1)), "upper": int(bounds.group(2)),
            "section1": bullets(s1), "section3": one_line(s3), "amend2_deps": deps.group(1),
            "slicing_level": int(slicing.group(1)), "amended_slicing_level": int(amended.group(1)) if amended else None,
            "gates": gates, "reach_admits": admits}


def parse_tlc(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    verdict = next((x for x in reversed(lines) if x.startswith("TOP-LEVEL")), None)
    m = re.match(r"TOP-LEVEL (\S+): (\d+) slice\(s\) with kept graphs, (\d+) cop\(ies\), (\d+) problem\(s\)",
                 verdict or "")
    acc = [re.match(r"s(\d+): (\d+) kept graph\(s\) in (\d+) cop(?:y|ies); (\S+): (.*)$", x) for x in lines]
    acc = [{"slice": int(x.group(1)), "graphs": int(x.group(2)), "copies": int(x.group(3)), "checker": x.group(4),
            "line": x.group(5)} for x in acc if x]
    return {"lines": lines, "verdict": verdict, "word": m.group(1) if m else None,
            "slices": int(m.group(2)) if m else None, "copies": int(m.group(3)) if m else None,
            "problem_count": int(m.group(4)) if m else None, "accept": acc,
            "tamper_rejected": sum(1 for x in lines if re.match(r"s\d+: self-test: \S+ rejects a tampered", x)),
            "tamper_no_reason": sum(1 for x in lines if re.fullmatch(r"s\d+: self-test: \S+ rejects a tampered "
                                                                     r"certificate:\s*", x)),
            "tamper_accepted": sum(1 for x in lines if "accepted a tampered certificate" in x),
            "problems": [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]}


def parse_l22(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]

    def first(rx):
        return next((m for m in (re.match(rx, x) for x in lines) if m), None)

    verdict = next((x for x in reversed(lines) if x.startswith("LEVEL-22 CONTROL")), None)
    m = re.match(r"LEVEL-22 CONTROL (\S+): (\d+) of (\d+) required graphs found$", verdict or "")
    head = first(r"Engel \((\d+),(\d+)\) graphs: (\d+); required \(minimum degree >= (\d+)\): (\d+); kept \(\d+,\d+\) "
                 r"graphs in the fleet: (\d+) distinct, from (\d+) slice copies$")
    rows = [re.match(r"\s+Engel\s+(\d+) \(min degree (\d+)\): (?:found in (.+)|MISSING)$", x) for x in lines]
    rows = [{"index": int(r.group(1)), "min_degree": int(r.group(2)),
             "slices": r.group(3).split(", ") if r.group(3) else []} for r in rows if r]
    efile = first(r"Engel file: (\S+) sha256 ([0-9a-f]{64})$")
    other = first(r"kept \(\d+,\d+\) graphs that are not Engel's: (\d+) ")
    dup = first(r"kept \(\d+,\d+\) graphs in more than one slice: (\d+)$")
    removed = first(r"self-test: with Engel graph (\d+)'s form removed from the union, missing = \[([\d, ]*)\]$")
    flipped = first(r"self-test: Engel graph \d+ with the pair \(\d+,\d+\) flipped is (not found|FOUND \(wrong\))$")
    twice = first(r"self-test: Engel graph \d+ also placed in a second slice is (reported|NOT reported)$")
    num = lambda mm, i: int(mm.group(i)) if mm else None
    return {"lines": lines, "verdict": verdict, "word": m.group(1) if m else None, "found": num(m, 2),
            "required": num(m, 3), "cell": [num(head, 1), num(head, 2)] if head else None, "engel": num(head, 3),
            "min_degree": num(head, 4), "required_head": num(head, 5), "kept_distinct": num(head, 6),
            "copies": num(head, 7), "rows": rows, "engel_file": efile.group(1) if efile else None,
            "engel_sha256": efile.group(2) if efile else None, "not_engel": num(other, 1), "dup": num(dup, 1),
            "selftest_removed": num(removed, 1),
            "selftest_missing": [int(i) for i in removed.group(2).split(",") if i.strip()] if removed else None,
            "selftest_flipped_found": (flipped.group(1) != "not found") if flipped else None,
            "selftest_dup_reported": (twice.group(1) == "reported") if twice else None,
            "problems": [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]}


VS_MISSING = ("no check output", "no result copy from the verification worker")


def parse_vs(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    verdict = next((x for x in reversed(lines) if x.startswith("VERIFY-SAMPLE")), None)
    m = re.match(r"VERIFY-SAMPLE (\S+): (\d+) of (\d+) planned slices verified \((\d+) restarted, (\d+) random, seed "
                 r"(\d+); (\d+) of (\d+) workers' first slices checked whole, the rest from level (\d+) with the prefix "
                 r"compared\), (\d+) problem\(s\)$", verdict or "")
    rows = [re.match(r"s(\d+) (v\d\d) (restarted|random): (NOT verified|(?:whole|from level \d+)\b.*)$", x) for x in lines]
    rows = [r for r in rows if r]
    ok = [(int(r.group(1)), r.group(2), r.group(3)) for r in rows if r.group(4) != "NOT verified"]
    notv = [(int(r.group(1)), r.group(2), r.group(3)) for r in rows if r.group(4) == "NOT verified"]
    probs = [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]
    # a problem is a failure unless it only says a check output or a copy is missing (not yet verified, not refuted)
    failed = [x for x in probs if not x.endswith(VS_MISSING)]
    missing_only = sorted({i for i, _, _ in notv} - {int(mm.group(1)) for x in failed
                                                     for mm in [re.match(r"s(\d+) ", x)] if mm})
    g = (lambda i: int(m.group(i))) if m else (lambda i: None)
    return {"lines": lines, "verdict": verdict, "word": m.group(1) if m else None, "verified": g(2), "planned": g(3),
            "restarted": g(4), "random": g(5), "seed": g(6), "whole": g(7), "workers": g(8), "from_level": g(9),
            "problem_count": g(10),
            "verified_restarted": sorted(i for i, _, k in ok if k == "restarted"),
            "verified_random": sorted(i for i, _, k in ok if k == "random"),
            "not_verified": sorted(i for i, _, _ in notv), "missing_only": missing_only,
            "not_verified_workers": sorted({w for _, w, _ in notv}), "failed_problems": failed}


# G5 round 20, finding 6: what a verified row must say, in full. Every (23,65) slice has the same cells (levels 10 to 23,
# pruned from 12), so a whole check replays the certificates of 69 pruned cells and a check from level 13 those of 61
# (measured: every row of the sample and the full re-run); verify_sample.record_scope() derives them from the cells.
ROW_CERTS = {"whole": 69, "from": 61}
ROW_OK = re.compile(r"(whole|from level (\d+)( \(the worker's first slice, whole check skipped: its prefix by hash\))?), "
                    r"(CHAIN OK|CHAIN PARTIAL \(levels below (\d+) not inspected \(--from-n (\d+)\)\)), certificates "
                    r"replayed in (\d+) pruned cells; result files identical to the fleet's copy \((f\d+-[0-9a-z]+)\)(.*)")
ROW_SUFFIX = (re.compile(r"files checked = copy's \(digest\)"),
              re.compile(r"by verify-chain-lean\.py, the G5 check having been killed for memory"),
              re.compile(r"interpreter \S+ \S+ \(not compared\)"))


def row_ok(text: str, digest: bool) -> tuple:
    """(kind, lean, skip) of a verified row that says all a verified row must say, else None: a whole check with CHAIN
    OK, or a check from level 13 with its CHAIN PARTIAL, each with its certificate count; the fleet's copy it matched;
    and only the known notes after it, the files digest among them where the plan requires one (the full re-run)."""
    m = ROW_OK.fullmatch(text)
    if not m or (m.group(9) and not m.group(9).startswith("; ")):
        return None
    kind = "whole" if m.group(1) == "whole" else "from"
    parts = m.group(9)[2:].split("; ") if m.group(9) else []
    if not all(any(r.fullmatch(x) for r in ROW_SUFFIX) for x in parts):
        return None
    if digest and not any(ROW_SUFFIX[0].fullmatch(x) for x in parts):
        return None
    if int(m.group(7)) != ROW_CERTS[kind]:
        return None
    if kind == "whole" and m.group(4) != "CHAIN OK":
        return None
    if kind == "from" and not (m.group(2) == m.group(5) == m.group(6) == "13" and m.group(4).startswith("CHAIN PARTIAL")):
        return None
    return kind, any(ROW_SUFFIX[1].fullmatch(x) for x in parts), bool(m.group(3))


def account(lines: list, plan: dict, sample: bool, chosen: dict | None = None) -> dict:
    """G5 round 19, findings 6 and 7: a judge's per-slice rows and PROBLEM lines against its plan. The rows must be
    every planned slice exactly once, each with its planned worker (and in the sample its kind), and no other row; a
    row marked whole must be a worker's first slice; every PROBLEM line must be about a slice whose row says NOT
    verified; and such a slice is explained, i.e. only not yet verified, when it has at least one PROBLEM line and
    every one says its check output or copy is missing. Totals alone once let a footer with no rows, or 63 copies of
    one row, count as 63 verified slices, and a FAIL with no explanation read as open."""
    want = {i: (t, ("restarted" if i in plan.get("restarted", []) else "random") if sample else "all")
            for t, sl in plan["workers"].items() for i in sl}
    firsts = {sl[0] for sl in plan["workers"].values() if sl}
    row = re.compile(r"s(\d+) ([av]\d\d) (restarted|random|all): (NOT verified|whole\b.*|from level \d+\b.*)")
    prob = re.compile(r"PROBLEM: s(\d+) \(([av]\d\d), (restarted|random|all)\): (.*)")
    rows, dup, bad_ok, lean_rows, skips, wrong_copy, first_not_whole = {}, set(), [], 0, [], [], []
    for x in lines:
        m = row.fullmatch(x)
        if m:
            i = int(m.group(1))
            if i in rows:
                dup.add(i)
            rows[i] = (m.group(2), m.group(3), "not" if m.group(4) == "NOT verified"
                       else "whole" if m.group(4).startswith("whole") else "from")
            if m.group(4) != "NOT verified":   # G5 round 20, finding 6: the whole row read, not its first word
                ro = row_ok(m.group(4), digest=not sample)
                fm = ROW_OK.fullmatch(m.group(4))
                if ro is None:
                    bad_ok.append(i)
                else:
                    lean_rows += ro[1]
                    if ro[2]:
                        skips.append(i)
                    # G5 round 21, finding 7: the fleet copy it matched is the aggregate's chosen copy of the slice
                    if chosen is not None and fm and chosen.get(i) != fm.group(8):
                        wrong_copy.append(i)
                    # and a worker's first slice is checked whole or declares its whole check skipped
                    if i in firsts and ro[0] == "from" and not ro[2]:
                        first_not_whole.append(i)
    probs, stray = {}, []
    for x in lines:
        if not x.startswith("PROBLEM: "):
            continue
        m = prob.fullmatch(x)
        i = int(m.group(1)) if m else None
        if m and rows.get(i, ("", "", ""))[2] == "not" and rows[i][:2] == (m.group(2), m.group(3)):
            probs.setdefault(i, []).append(m.group(4))
        else:
            stray.append(x[:200])
    notv = sorted(i for i, r in rows.items() if r[2] == "not")
    return {"exact": not dup and set(rows) == set(want) and all(rows[i][:2] == want[i] for i in rows),
            "dup": sorted(dup), "absent": len(set(want) - set(rows)), "extra": len(set(rows) - set(want)),
            "wrong": sorted(i for i in rows if i in want and rows[i][:2] != want[i])[:20],
            "ok_rows": sum(1 for r in rows.values() if r[2] != "not"), "not_rows": len(notv),
            "whole_rows": sum(1 for r in rows.values() if r[2] == "whole"),
            "whole_wrong": sorted(i for i, r in rows.items() if r[2] == "whole" and i not in firsts),
            "bad_ok": sorted(bad_ok)[:20], "bad_ok_count": len(bad_ok), "lean_rows": lean_rows,
            "skip_rows": len(skips), "skip_wrong": sorted(i for i in skips if i not in firsts),
            "wrong_copy": sorted(wrong_copy)[:20], "first_not_whole": sorted(first_not_whole)[:20],
            "planned_workers": len(plan["workers"]), "plan_seed": plan.get("seed"),
            "plan_restarted": len(plan.get("restarted") or []), "plan_random": len(plan.get("random") or []),
            "stray": stray[:20], "stray_count": len(stray),
            "unexplained": [i for i in notv if not probs.get(i) or not all(x.endswith(VS_MISSING) for x in probs[i])]}


def parse_target(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    verdict = next((x for x in reversed(lines) if x.startswith("TARGET-CHECK")), None)
    m = re.match(r"TARGET-CHECK (\S+): \((\d+),(\d+)\): (\d+) of (\d+) slices complete, G4 PASS (\d+); (\d+) "
                 r"failing, (\d+) missing; kept at \((\d+),(\d+)\): (\d+) distinct graph\(s\)"
                 r"(?:; known: (\d+) of (\d+) kept)?$", verdict or "")
    st = next((x for x in lines if x.startswith("SELF-TEST")), None)
    pm = next((x for x in lines if x.startswith("parameters: ")), None)
    ms = next((re.match(r"MISSING: (\d+) slice\(s\) with no copy", x) for x in lines if x.startswith("MISSING: ")), None)
    au = next((x for x in lines if x.startswith("AUDIT: ")), None)
    g = (lambda i: int(m.group(i)) if m and m.group(i) is not None else None)
    # G5 round 22, finding 8: the kept count's own cell must be the footer's, and the self-test line must say every
    # control was caught (its prefix alone once passed "0 of 63")
    ok_kept_cell = bool(m) and (m.group(9), m.group(10)) == (m.group(2), m.group(3))
    stm = re.fullmatch(r"SELF-TEST passed: (\d+) of (\d+) red controls caught", st or "")
    return {"lines": [x for x in lines if not x.startswith("PROBLEM: ")][-14:], "verdict": verdict,
            "word": m.group(1) if m else None, "cell": [g(2), g(3)] if m and ok_kept_cell else None,
            "complete": g(4), "slices": g(5),
            "g4_pass": g(6), "failing": g(7), "missing": g(8), "kept": g(11), "found": g(12), "known": g(13),
            "parameters": pm[len("parameters: "):] if pm else None, "audit": au[len("AUDIT: "):] if au else None,
            "selftest": st,
            "selftest_ok": bool(stm) and stm.group(1) == stm.group(2) and int(stm.group(1)) > 0,
            # G5 round 19, finding 7: the MISSING line's own count (a FAIL is open only when absence explains it)
            "missing_listed": int(ms.group(1)) if ms else 0,
            "problems": [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]}


def parse_verify_all(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    verdict = next((x for x in reversed(lines) if x.startswith("VERIFY-ALL")), None)
    m = re.match(r"VERIFY-ALL (\S+): (\d+) of (\d+) slices re-run and verified \((\d+) tasks; (\d+) first slices "
                 r"checked whole", verdict or "")
    probs = [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]
    g = (lambda i: int(m.group(i))) if m else (lambda i: None)
    pc = re.search(r"\), (\d+) problem\(s\)$", verdict or "")
    ln = re.search(r"; (\d+) by the memory-bounded verify-chain-lean\.py", verdict or "")
    return {"lines": lines, "verdict": verdict, "word": m.group(1) if m else None, "verified": g(2), "planned": g(3),
            "tasks": g(4), "whole": g(5), "failed_problems": [x for x in probs if not x.endswith(VS_MISSING)],
            "missing": sum(1 for x in probs if x.endswith(VS_MISSING)),
            "problems_count": int(pc.group(1)) if pc else None, "problem_lines": len(probs),
            "lean": int(ln.group(1)) if ln else 0,
            "not_verified": sum(1 for x in lines if re.fullmatch(r"s\d+ \S+ \S+: NOT verified", x))}


def parse_blind(text: str) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    verdict = next((x for x in reversed(lines) if x.startswith("BLIND-CHECK")), None)
    m = re.match(r"BLIND-CHECK (\S+): (\d+) of (\d+) top-level certificates accepted by the blind verifier "
                 r"\(verify_tree\.py sha256 ([0-9a-f]+)\); (\d+) of (\d+) tampered inputs rejected$", verdict or "")
    g = (lambda i: int(m.group(i))) if m else (lambda i: None)
    acc = [re.match(r"s(\d+)of\d+/\S+\.g6 graph \d+ (\S+) certs ([0-9a-f]{64}): ACCEPT \(exit 0\)$", x) for x in lines]
    return {"lines": lines, "verdict": verdict, "word": m.group(1) if m else None, "accepted": g(2), "total": g(3),
            "accepted_graphs": sorted([int(x.group(1)), x.group(2), x.group(3)] for x in acc if x),
            "verifier_sha256": m.group(4) if m else None, "rejected": g(5), "tried": g(6),
            "problems": [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]}


def parse_audit(text: str) -> dict:
    lines = text.splitlines()
    report = None
    for x in lines:
        if x.startswith("{"):
            try:
                report = json.loads(x)
                break
            except ValueError:
                pass
    unresolved = [x[len("UNRESOLVED: "):] for x in lines if x.startswith("UNRESOLVED: ")]
    problems = [x[len("PROBLEM: "):] for x in lines if x.startswith("PROBLEM: ")]
    cov = next((x for x in lines if x.startswith("COVERAGE")), None)
    chain = next((x for x in lines if x.startswith("CHAIN ")), None)
    word = re.match(r"COVERAGE \(summary only\) (\S+)", cov or "")
    word = word.group(1).rstrip(":") if word else None
    slices = set()
    for u in unresolved:
        for pat in (r"^\S+/s(\d+)of\d+: ", r"^slice (\d+): "):
            mm = re.match(pat, u)
            if mm:
                slices.add(int(mm.group(1)))
        mm = re.match(r"^fleet \(\d+,\d+\): slices \[([\d, ]+)\]", u)
        if mm:
            slices.update(int(s) for s in mm.group(1).split(","))
    fleet = ((report or {}).get("fleets") or [None])[0] or {}
    return {"header": lines[0] if lines and "slice result directories" in lines[0] else None, "report": report,
            "fleet": fleet, "unresolved_lines": unresolved, "problem_lines": problems, "coverage_line": cov,
            "chain_line": chain, "word": word, "unresolved_slices": sorted(slices),
            "exit_expected": {"FAIL": 1, "UNRESOLVED": 4, "OK": 3}.get(word)}


def extract(src: dict) -> dict:
    x = {}

    def put(key, value, frm):
        x[key] = {"value": value, "from": frm}

    A = src["aggregate"]["json"]
    AJ = "aggregate.json: "
    P, cov, tree, top, rep, cost, prov = (A[k] for k in ("plan", "coverage", "tree", "top_level", "replays", "cost",
                                                          "provenance"))
    C, L, W = P["slices"], P["slice_level"], P["workers"]
    tn, tm = P["target"]
    for k in ("kind", "slices", "workers", "slice_level", "target"):
        put(f"plan.{k}", P[k], AJ + f"plan.{k}")
    put("plan.slices_per_worker", C // W, "plan.slices // plan.workers")
    put("agg.generated_utc", A["generated_utc"], AJ + "generated_utc")
    put("agg.root", A["root"], AJ + "root")
    put("agg.final", A["final"], AJ + "final")
    put("agg.problems", A["problems"], AJ + "problems")
    put("agg.exit", src["aggregate"].get("exit"), "the aggregate_fleet.py run's exit status")
    put("agg.self_check", [{"check": c["check"], "ok": c["ok"], "what": c["what"]} for c in (A["self_check"] or [])]
        if A.get("self_check") is not None else None, AJ + "self_check")
    ro = prov["run_options"]
    rs, rc = ro["run_summary"], ro["run_config"]
    put("run.seed_n", rs["seed_n"], AJ + "provenance.run_options.run_summary.seed_n")
    put("run.root_k", rs["reach"]["root_k"], AJ + "provenance.run_options.run_summary.reach.root_k")
    put("run.reach_levels", {int(k): v for k, v in rs["reach"]["levels"].items()},
        AJ + "provenance.run_options.run_summary.reach.levels")
    put("run.prune_from", rs["prune"]["prune_from"], AJ + "provenance.run_options.run_summary.prune.prune_from")
    put("run.prune_filter_only", rs["prune"]["prune_filter_only"], AJ + "...run_summary.prune.prune_filter_only")
    put("run.forbidden_set", rs["forbidden_set"], AJ + "provenance.run_options.run_summary.forbidden_set")
    put("run.prune_filter_set", rs.get("prune_filter_set"), AJ + "provenance.run_options.run_summary.prune_filter_set")
    put("run.triangles", rs.get("triangles"), AJ + "provenance.run_options.run_summary.triangles")
    put("run.verify_stages", rs.get("verify_stages"), AJ + "provenance.run_options.run_summary.verify_stages")
    ub = (rs.get("ubar_override") or {}).get("22") or {}
    put("run.ubar22", ub.get("value"), AJ + "provenance.run_options.run_summary.ubar_override.22.value")
    put("run.ubar22_builtin", ub.get("builtin"), AJ + "provenance.run_options.run_summary.ubar_override.22.builtin")
    put("run.prune_tries", rc.get("prune_tries"), AJ + "provenance.run_options.run_config.prune_tries")
    # coverage
    put("cov.complete", cov["complete"], AJ + "coverage.complete")
    put("cov.missing", cov["missing"], AJ + "coverage.missing")
    put("cov.missing_slices", cov["missing_slices"], AJ + "coverage.missing_slices")
    put("cov.missing_ranges", ranges(cov["missing_slices"]), "ranges of coverage.missing_slices")
    put("cov.missing_by_owner", cov["missing_by_plan_owner"], AJ + "coverage.missing_by_plan_owner")
    put("cov.every_copy_resumed", cov["every_copy_resumed"], AJ + "coverage.every_copy_resumed")
    put("cov.copies_read", cov["copies_read"], AJ + "coverage.copies_read")
    put("cov.copies_skipped", len(cov["copies_skipped"]), "len(" + AJ + "coverage.copies_skipped)")
    put("cov.copies_misfiled", len(cov["copies_misfiled"]), "len(" + AJ + "coverage.copies_misfiled)")
    put("cov.copies_unfinished", len(cov["copies_unfinished"]), "len(" + AJ + "coverage.copies_unfinished)")
    put("cov.several", len(cov["several_copies"]), "len(" + AJ + "coverage.several_copies)")
    put("cov.several_agree", cov["several_copies_agree"], AJ + "coverage.several_copies_agree")
    done = set(range(C)) - set(cov["missing_slices"])
    put("cov.first_complete", min(done) if done else None, "min of the slices not in coverage.missing_slices")
    reruns = sorted(int(i) for i, s in A["slices"].items() if s.get("chosen") and s.get("resumed_cells") == 0
                    and any(c["resumed_cells"] for c in s["copies"]))
    put("cov.rerun_slices", reruns, AJ + "slices[i]: a copy with resumed_cells > 0, the chosen copy with none")
    put("cov.rerun_workers", prov["copies_outside_plan_owner"], AJ + "provenance.copies_outside_plan_owner")
    put("cov.refired_tags", len(prov["worker_tags_with_several_dirs"]),
        "len(" + AJ + "provenance.worker_tags_with_several_dirs)")
    put("cov.worker_dirs", len(prov["workers"]), "len(" + AJ + "provenance.workers)")
    put("cov.worker_dirs_with_copies", prov["worker_dirs_with_copies"], AJ + "provenance.worker_dirs_with_copies")
    # the tree
    reach = x["run.reach_levels"]["value"]
    by_n = {}
    for c in tree["cells"]:
        by_n.setdefault(c["n"], []).append(c["m"])
    rows = []
    for e in tree["levels"]:
        n, w = e["n"], reach.get(e["n"]) or []
        rows.append({"n": n, "window": (f"{min(w)}..{max(w)}" if len(w) > 1 else str(w[0])) if w else "",
                     "cells_are_window": sorted(by_n.get(n, [])) == sorted(w), "cells": e["cells"],
                     "children": e["children"], "kept": e["kept"], "pruned": e["pruned"],
                     "by_kind": e["pruned_by_kind"],
                     "pct_pruned": round(100 * e["pruned"] / e["children"], 1) if e["children"] else None})
    put("tree.kinds", tree["kinds"], AJ + "tree.kinds")
    put("tree.levels", rows, AJ + "tree.levels (window: run.reach_levels; pct_pruned = 100 * pruned / children)")
    other = [k for k in tree["count_keys"] if k not in tree["kinds"] and k not in ("kept", "pruned")]
    put("tree.other_totals", {k: sum(e["counts"].get(k, 0) for e in tree["levels"]) for k in other},
        AJ + "tree.levels[].counts summed, the keys that are not prune verdicts")
    put("tree.reach_dropped", sum(e["reach_dropped"] or 0 for e in tree["levels"]),
        AJ + "tree.levels[].reach_dropped summed")
    # the top level
    for k in ("children", "kept", "pruned", "slices_with_children", "records", "kept_without_record", "records_dir"):
        put(f"top.{k}", top[k], AJ + f"top_level.{k}")
    put("top.slices_kept", {int(k): v for k, v in top["slices_kept"].items()}, AJ + "top_level.slices_kept")
    put("top.kept_graphs", {int(k): v for k, v in top["kept_graphs"].items()}, AJ + "top_level.kept_graphs")
    t0 = top.get("top_level_check") or {}
    put("tlc_agg.verdict", t0.get("verdict"), AJ + "top_level.top_level_check.verdict")
    put("tlc_agg.exit", t0.get("exit") if t0.get("ran") else None, AJ + "top_level.top_level_check.exit")
    T = parse_tlc(src["top_level_check"]["text"])
    TS = "top-level-check.txt: "
    for k in ("lines", "verdict", "word", "slices", "copies", "problem_count", "accept", "tamper_rejected",
              "tamper_no_reason", "tamper_accepted", "problems"):
        put(f"tlc.{k}", T[k], TS + {"lines": "every line", "verdict": "the TOP-LEVEL line",
                                    "accept": "the per-checker lines", "tamper_rejected": "count of self-test rejects",
                                    "tamper_no_reason": "count of self-test rejects with nothing after the colon",
                                    "tamper_accepted": "count of self-test accepts",
                                    "problems": "PROBLEM lines"}.get(k, f"the TOP-LEVEL line's {k}"))
    put("tlc.exit", src["top_level_check"].get("exit"), "the top_level_check.py run's exit status")
    Q = parse_l22(src["level22_control"]["text"])
    QS = "level22-control.txt: "
    for k, frm in (("lines", "every line"), ("verdict", "the LEVEL-22 CONTROL line"),
                   ("word", "the LEVEL-22 CONTROL line's verdict"), ("found", "the LEVEL-22 CONTROL line's found"),
                   ("required", "the LEVEL-22 CONTROL line's required"), ("cell", "the Engel line's cell"),
                   ("engel", "the Engel line's graph count"), ("min_degree", "the Engel line's minimum degree"),
                   ("required_head", "the Engel line's required count"),
                   ("kept_distinct", "the Engel line's distinct kept graphs"),
                   ("copies", "the Engel line's slice copies"), ("rows", "the per-graph lines"),
                   ("engel_file", "the Engel file line's path"), ("engel_sha256", "the Engel file line's sha256"),
                   ("not_engel", "the not-Engel's line"), ("dup", "the more-than-one-slice line"),
                   ("selftest_removed", "the self-test's removal line: the graph removed"),
                   ("selftest_missing", "the self-test's removal line: what it then reports missing"),
                   ("selftest_flipped_found", "the self-test's flipped-edge line (found: true)"),
                   ("selftest_dup_reported", "the self-test's second-slice line (reported: true)"),
                   ("problems", "PROBLEM lines")):
        put(f"l22.{k}", Q[k], QS + frm)
    put("l22.exit", src["level22_control"].get("exit"), "the level22_control.py run's exit status")
    Z = parse_vs(src["verify_sample"]["text"])
    ZS = "verify-sample.txt: "
    for k, frm in (("verdict", "the VERIFY-SAMPLE line"), ("word", "the VERIFY-SAMPLE line's verdict"),
                   ("verified", "the VERIFY-SAMPLE line: slices verified"), ("planned", "the VERIFY-SAMPLE line: planned"),
                   ("restarted", "the VERIFY-SAMPLE line: restarted slices planned"),
                   ("random", "the VERIFY-SAMPLE line: random slices planned"), ("seed", "the VERIFY-SAMPLE line: seed"),
                   ("whole", "the VERIFY-SAMPLE line: first slices checked whole"),
                   ("workers", "the VERIFY-SAMPLE line: workers"), ("from_level", "the VERIFY-SAMPLE line: level"),
                   ("problem_count", "the VERIFY-SAMPLE line: problems"),
                   ("verified_restarted", "the per-slice lines: restarted slices verified"),
                   ("verified_random", "the per-slice lines: random slices verified"),
                   ("not_verified", "the per-slice lines: slices not verified"),
                   ("missing_only", "slices not verified whose only problems are a missing check output or copy"),
                   ("not_verified_workers", "the per-slice lines: the workers of the slices not verified"),
                   ("failed_problems", "PROBLEM lines other than a missing check output or copy")):
        put(f"vs.{k}", Z[k], ZS + frm)
    put("vs.exit", src["verify_sample"].get("exit"), "the verify_sample.py run's exit status")
    chosen = {int(i): s.get("chosen") for i, s in (A.get("slices") or {}).items()}
    put("vs.accounted", account(Z["lines"], vsm.plan_from_jobs(vsm.JOBS.read_text()), True, chosen),
        ZS + "the per-slice rows and PROBLEM lines against the sample's plan (JOBS.md, as verify_sample.py reads it)")
    for name, key in (("control22", "c22"), ("calib2157", "cal")):
        T = parse_target(src[name]["text"])
        for k, frm in (("verdict", "the TARGET-CHECK line"), ("word", "the TARGET-CHECK line's verdict"),
                       ("cell", "the TARGET-CHECK line's cell"), ("complete", "the TARGET-CHECK line: complete slices"),
                       ("slices", "the TARGET-CHECK line: slices"), ("g4_pass", "the TARGET-CHECK line: G4 PASS"),
                       ("failing", "the TARGET-CHECK line: slices failing"),
                       ("missing", "the TARGET-CHECK line: slices missing"),
                       ("parameters", "the parameters line: what the check required"),
                       ("audit", "the AUDIT line: verify-chain.py --summary-only's COVERAGE line"),
                       ("kept", "the TARGET-CHECK line: distinct graphs kept"),
                       ("found", "the TARGET-CHECK line: known graphs kept"), ("known", "the TARGET-CHECK line: known"),
                       ("selftest", "the SELF-TEST line"), ("selftest_ok", "the SELF-TEST line says passed"),
                       ("problems", "PROBLEM lines"), ("lines", "the last lines"),
                       ("missing_listed", "the MISSING line's count")):
            put(f"{key}.{k}", T[k], f"{name}: " + frm)
        put(f"{key}.exit", src[name].get("exit"), f"the target_check.py run's exit status ({name})")
    sv = next((x for x in reversed(src["g4_scope"]["text"].splitlines()) if x.startswith("G4-SCOPE")), None)
    put("g4.scope_verdict", sv, "g4-scope.txt: the G4-SCOPE line")
    # G5 round 22, finding 7: the copies the scope check covered, by identity, against the aggregate's copies
    cl = next((re.fullmatch(r"G4-SCOPE COPIES \(23,65\): (\d+) copies, sha256 ([0-9a-f]{64})", x)
               for x in src["g4_scope"]["text"].splitlines() if x.startswith("G4-SCOPE COPIES ")), None)
    put("g4.scope_copies", [int(cl.group(1)), cl.group(2)] if cl else None,
        "g4-scope.txt: the G4-SCOPE COPIES line, for (23,65)")
    put("g4.agg_copies", src["g4_scope"].get("expected_copies"),
        "the credited root's copies, recomputed (target_check.copies_lines: label, target, mode, evidence digests)")
    put("g4.root_labels", src["g4_scope"].get("root_labels"), "the credited root's copies, by worker and slice")
    labels = sorted(f"{cp.get('worker')}/s{i}of1920" for i, s in (A.get("slices") or {}).items() for cp in s.get("copies") or [])
    put("g4.agg_labels", [len(labels), hashlib.sha256("\n".join(labels).encode()).hexdigest()],
        AJ + "slices.*.copies: the aggregate's own copies, by worker and slice")
    put("g4.scope_exit", src["g4_scope"].get("exit"), "the target_check.py --scope-only run's exit status")
    X = parse_verify_all(src["verify_all"]["text"])
    for k, frm in (("verdict", "the VERIFY-ALL line"), ("word", "the VERIFY-ALL line's verdict"),
                   ("verified", "the VERIFY-ALL line: slices verified"), ("planned", "the VERIFY-ALL line: planned"),
                   ("tasks", "the VERIFY-ALL line: tasks"), ("whole", "the VERIFY-ALL line: first slices checked whole"),
                   ("failed_problems", "PROBLEM lines other than a missing output or copy"),
                   ("missing", "PROBLEM lines of a missing output or copy"),
                   ("problems_count", "the VERIFY-ALL line: its problem count"),
                   ("problem_lines", "the number of PROBLEM lines"),
                   ("lean", "the VERIFY-ALL line: slices checked by verify-chain-lean.py after a G5 memory kill"),
                   ("not_verified", "the per-slice lines that say NOT verified")):
        put(f"va.{k}", X[k], "verify-all.txt: " + frm)
    plan_file = REPO / "coordination/cloud-workers/u23-verify-all-claude-plan.json"
    put("va.expected_tasks", len(json.loads(plan_file.read_text()).get("tasks") or {}) if plan_file.is_file() else None,
        "coordination/cloud-workers/u23-verify-all-claude-plan.json: its workers")
    put("va.exit", src["verify_all"].get("exit"), "the verify_sample.py --all run's exit status")
    put("va.accounted", account(X["lines"], vsm.plan_from_all(vsm.ALL_PLAN), False,
                                {int(i): s.get("chosen") for i, s in (A.get("slices") or {}).items()}),
        "verify-all.txt: the per-slice rows and PROBLEM lines against the plan (u23-verify-all-claude-plan.json)")
    Y = parse_blind(src["blind_check"]["text"])
    YS = "blind-check.txt: "
    for k, frm in (("lines", "every line"), ("verdict", "the BLIND-CHECK line"),
                   ("word", "the BLIND-CHECK line's verdict"), ("accepted", "the BLIND-CHECK line: accepted"),
                   ("total", "the BLIND-CHECK line: certificates"), ("verifier_sha256", "the BLIND-CHECK line: sha256"),
                   ("rejected", "the BLIND-CHECK line: tampered inputs rejected"),
                   ("tried", "the BLIND-CHECK line: tampered inputs tried"), ("problems", "PROBLEM lines"),
                   ("accepted_graphs", "the per-graph ACCEPT lines: slice and graph6")):
        put(f"blind.{k}", Y[k], YS + frm)
    put("blind.exit", src["blind_check"].get("exit"), "the blind_check.py run's exit status")
    red, rcounts = {}, {}
    for i, r in src["records"].items():
        mm = re.search(r"^REJECT: .*$", r.get("check_txt", ""), re.M)
        if mm:
            red[i] = mm.group(0)
        if r.get("prune_manifest"):
            rcounts[i] = {"counts": r["prune_manifest"].get("counts"), "checker": r["prune_manifest"].get("checker")}
    put("rec.red_control", red, "results/u23/top-level/s<i>of<C>/CHECK.txt: the REJECT line of its red control")
    put("rec.prune", rcounts, "results/u23/top-level/s<i>of<C>/23-65.prune.manifest.json: counts, checker")
    put("top.records_certs_sha256", {str(i): r.get("certs_sha256") for i, r in src["records"].items()},
        "results/u23/top-level/s<i>of<C>/23-65.certs.jsonl: sha256 (the file the checkers replay)")
    # G4
    for k in ("verdicts", "modes", "full_mode_red_all", "totals", "not_pass_or_empty",
              "other_copies_not_pass_or_empty"):
        put(f"g4.{k}", rep[k], AJ + f"replays.{k}")
    put("g4.runbook_differs", len(rep["runbook_verdict_differs"]), "len(" + AJ + "replays.runbook_verdict_differs)")
    # cost
    for k, path in (("slices_timed", "slices_timed"), ("excluded", "len slices_excluded_resumed"),
                    ("seconds", "seconds_total"), ("hours", "hours_total"), ("median", "per_slice.median"),
                    ("p90", "per_slice.p90"), ("max", "per_slice.max"), ("heaviest", "heaviest"),
                    ("run_dag2_s", "runbook_clocks.run_dag2_wall_seconds"),
                    ("replay_s", "runbook_clocks.replay_wall_seconds"), ("clock_copies", "runbook_clocks.copies"),
                    ("partial", "len cells_with_a_resumed_step_the_rule_times")):
        val = cost
        for part in path.removeprefix("len ").split("."):
            val = val[part]
        put(f"cost.{k}", len(val) if path.startswith("len ") else val, AJ + "cost." + path)
    # provenance
    put("prov.prefix_files", prov["prefix"]["files"], AJ + "provenance.prefix.files")
    put("prov.prefix_copies", prov["prefix"]["copies"], AJ + "provenance.prefix.copies")
    put("prov.prefix_agree", prov["prefix"]["agree"], AJ + "provenance.prefix.agree")
    tools = {}
    for k, val in prov["software"].items():
        tools.setdefault(k.split(": ", 1)[1], set()).update(val["values"])
    put("prov.software", {n: sorted(h[:8] if re.fullmatch("[0-9a-f]{64}", h) else h for h in s)
                          for n, s in sorted(tools.items())}, AJ + "provenance.software (first 8 hex digits)")
    data = {}
    for k, val in prov["inputs"].items():
        data.setdefault(k.split(": ", 1)[1], set()).update(val["values"])
    put("prov.inputs", {n: sorted(s) for n, s in sorted(data.items())}, AJ + "provenance.inputs")
    put("prov.software_all_same", prov["software_all_same"], AJ + "provenance.software_all_same")
    put("prov.run_options_identical", prov["run_options_identical"], AJ + "provenance.run_options_identical")
    put("prov.verify_manifests", prov["verify_manifests_read"], AJ + "provenance.verify_manifests_read")
    # the audit
    U = parse_audit(src["audit"]["text"])
    AU = "fleet-audit.txt: "
    rp, fl = U["report"] or {}, U["fleet"]
    put("audit.header", U["header"], AU + "line 1")
    for k in ("runs", "audited", "pinned", "required", "problems", "unresolved"):
        put(f"audit.{k}", rp.get(k), AU + f"report.{k}")
    for k in ("summaries", "slice_indices", "missing_slices", "prefix_files_hashed", "prefix_files_identical_in",
              "g4_results", "slice_partition", "prefix_cells", "prefix_cells_with_parents_recorded",
              "cells_recovered_from_history", "target_cell", "slice_count", "slice_level", "target"):
        put(f"audit.{k}", fl.get(k), AU + f"report.fleets[0].{k}")
    for k in ("unresolved_lines", "problem_lines", "coverage_line", "chain_line", "word", "unresolved_slices",
              "exit_expected"):
        put(f"audit.{k}", U[k], AU + {"unresolved_lines": "UNRESOLVED lines", "problem_lines": "PROBLEM lines",
                                      "coverage_line": "the COVERAGE line", "chain_line": "the CHAIN line",
                                      "word": "the COVERAGE line's verdict", "exit_expected":
                                      "the exit status verify-chain.py gives that verdict",
                                      "unresolved_slices": "the slices the UNRESOLVED lines name"}[k])
    put("audit.exit", src["audit"].get("exit"), "the fleet-audit.py run's exit status (none: a saved output)")
    for k in ("worktree_head", "worktree_branch", "worktree_dirty", "fleet_audit_sha256", "verify_chain_sha256"):
        put(f"audit.{k}", src["audit"].get(k), f"the audit worktree ({k})")
    # snapshot
    rb, ra = src["root"]["before"], src["root"]["after"]
    put("snap.before", rb, "the fleet root's fingerprint before the tools ran")
    put("snap.after", ra, "the fleet root's fingerprint after the tools ran")
    # G5, CONTRACT, JOBS
    g5 = src["g5"]
    last = [ln.strip() for ln in g5["round9"].splitlines() if ln.strip()]
    put("g5.verdict", last[-1].strip("*").strip() if last else None, f"{G5_ROUND9}: its last line")
    put("g5.commit", g5["commit"], f"git rev-parse {g5['ref']}")
    put("g5.ref", g5["ref"], "--g5-ref")
    gl = src["g5_latest"]
    lv = re.findall(r"^G5 round (\d+): (CLOSED|OPEN \(\d+ findings?\))$", gl["text"], re.M)
    put("g5.latest_round", gl["round"], f"the highest G5-roundN-read file in {G5_DIR}")
    put("g5.latest_path", gl["path"], "that file")
    put("g5.latest_verdict", f"G5 round {lv[-1][0]}: {lv[-1][1]}" if lv and int(lv[-1][0]) == gl["round"] else None,
        "that file, as committed at HEAD: its final verdict line")
    put("g5.latest_answered", bool(re.search(r"^## Response", gl["text"], re.M)),
        "that file: a Response section answers its findings in writing")
    item6 = re.search(r"^6\. \*\*(.+?)\*\*", g5["closure"], re.M)
    put("g5.item6", item6.group(1) if item6 else None, f"{G5_CLOSURE}: item 6's title")
    K = extract_contract(src["contract"]["text"])
    for k, val in K.items():
        put(f"contract.{k}", val, f"{rel(CONTRACT)}: " + {"intro": "Section 0, first paragraph",
                                                          "claim_64": "Section 0, bullet", "claim_65":
                                                          "Section 0, bullet", "never": "Section 0, bullet",
                                                          "lower": "Section 0: u(23) is <lower> or <upper>",
                                                          "upper": "Section 0: u(23) is <lower> or <upper>",
                                                          "section1": "Section 1, bullets", "section3": "Section 3",
                                                          "amend2_deps": "Section 8, amendment 2",
                                                          "slicing_level": "Section 2, Slicing bullet",
                                                          "amended_slicing_level": "Section 8: a slicing level an "
                                                                                   "amendment sets (none: no such)",
                                                          "gates": "Section 6, the gates table",
                                                          "reach_admits": "Section 2, Reach table bullet"}[k])
    cap = re.search(r"cloud cap is about (\d+) concurrent sandboxes", src["jobs"]["text"])
    put("jobs.cap", int(cap.group(1)) if cap else None, f"{rel(JOBS)}, u23-fleet: 'the cloud cap is about N'")
    consts = {k: {"value": v, "from": f} for k, (v, f) in CONSTANTS.items()}
    sources = {}
    for name in ("aggregate", "top_level_check", "blind_check", "level22_control", "verify_sample", "audit",
                 "control22", "calib2157", "verify_all", "g4_scope"):
        s = {k: val for k, val in src[name].items() if k not in ("json", "text")}
        sources[name] = s
    sources["g5"] = {k: g5[k] for k in ("ref", "commit", "round9_path", "closure_path")}
    sources["contract"] = {k: src["contract"][k] for k in ("path", "sha256")}
    sources["jobs"] = {k: src["jobs"][k] for k in ("path", "sha256")}
    sources["records"] = {i: r["dir"] for i, r in src["records"].items()}
    sources["root"] = src["root"]
    sources["repo"] = src["repo"]
    return {"about": {"tool": rel(HERE), "tool_sha256": sha256(HERE), "generated_utc": iso(time.time()),
                      "note": "every value of RESULT-u23.md, with its source; decision, lint: this generator's "
                              "outputs, recomputed from the values on every render"},
            "sources": sources, "constants": consts, "v": x}


# ----------------------------------------------------------------------------------------------------------- decide

def rows_note(A: dict) -> str:
    """What a judge's per-slice rows fail to account for (account()), for a check's detail; empty when nothing."""
    out = []
    if A and not A.get("exact"):
        out.append(f"the per-slice rows are not the plan's slices, each once: {E(A.get('absent'))} absent, "
                   f"{E(A.get('extra'))} extra, repeated {E(ranges(A.get('dup') or []) or 'none')}, with another "
                   f"worker or kind {E(ranges(A.get('wrong') or []) or 'none')}")
    if A and A.get("whole_wrong"):
        out.append(f"rows marked whole that are no worker's first slice: {E(ranges(A['whole_wrong']))}")
    if A and A.get("stray_count"):
        out.append(f"{E(A['stray_count'])} PROBLEM line(s) not about a slice that is NOT verified")
    if A and A.get("bad_ok_count"):
        out.append(f"{E(A['bad_ok_count'])} verified row(s) that do not say what a verified row must: "
                   f"{E(ranges(A.get('bad_ok') or []))}")
    if A and A.get("skip_wrong"):
        out.append(f"rows declaring a skipped whole check that are no worker's first slice: {E(ranges(A['skip_wrong']))}")
    if A and A.get("wrong_copy"):
        out.append(f"rows naming a fleet copy other than the aggregate's chosen one: {E(ranges(A['wrong_copy']))}")
    if A and A.get("first_not_whole"):
        out.append(f"workers' first slices neither checked whole nor declared skipped: {E(ranges(A['first_not_whole']))}")
    if A and A.get("unexplained"):
        out.append(f"not verified, and not explained by a missing check output or copy: {E(ranges(A['unexplained']))}")
    return "".join(f"; {x}" for x in out)


def decide(V: dict) -> dict:
    """The headline and the open items, from the values alone (a stored decision is never read)."""
    g = lambda k: V["v"][k]["value"]
    C, (tn, tm) = g("plan.slices"), g("plan.target")
    cell = E(f"({tn},{tm})")
    checks = []

    def check(name, ok, status, detail, gate=False):
        # gate=True: evidence for a gate of Section 6, not open for the enumeration's state when not yet ok
        checks.append({"name": name, "ok": bool(ok), "status": status, "detail": detail, "gate": bool(gate)})

    # coverage
    miss, resumed = g("cov.missing_slices"), g("cov.every_copy_resumed")
    ok = g("cov.complete") == C and not miss and not resumed
    d = f"{E(g('cov.complete'))} of {E(C)} slices have a complete copy"
    if miss:
        own = ", ".join(f"{w} {k}" for w, k in sorted(g("cov.missing_by_owner").items(), key=lambda t: (-t[1], t[0])))
        d += f"; missing {E(len(miss))}: {E(ranges(miss))} (by plan owner: {E(own)})"
    if resumed:
        d += f"; every copy has resumed cells, so a fresh rerun is needed: {E(ranges(resumed))}"
    check("coverage", ok, E("complete" if ok else "incomplete"), d)
    # the audit
    word, exp, ex = g("audit.word"), g("audit.exit_expected"), g("audit.exit")
    probs, unres = g("audit.problem_lines"), g("audit.unresolved_lines")
    pinned = g("audit.pinned") or {}
    ok = (word == "OK" and g("audit.problems") == 0 and g("audit.unresolved") == 0 and not probs and not unres
          and g("audit.missing_slices") == 0 and g("audit.slice_indices") == C and ex in (None, exp)
          and pinned.get("target") == [tn, tm] and pinned.get("slices") == [g("plan.slice_level"), C]
          and pinned.get("seed") == g("run.seed_n") and not g("audit.worktree_dirty"))
    if g("audit.coverage_line") is None:
        d = "the audit output has no COVERAGE line (it did not finish, or it is not the audit's output)"
    else:
        d = (f"`{E(g('audit.coverage_line'))}`, `{E(g('audit.chain_line'))}` (exit {E(ex)}); summaries "
             f"{E(g('audit.runs'))}, slice indices {E(g('audit.slice_indices'))}, missing {E(g('audit.missing_slices'))}")
        if probs:
            d += "; problems: " + "; ".join(f"`{E(p)}`" for p in probs)
        if unres:
            d += (f"; {E(len(unres))} unresolved lines naming slices {E(ranges(g('audit.unresolved_slices')) or 'none')}"
                  f" (the lines are in the audit output)")
        if ex is not None and exp is not None and ex != exp:
            d += f"; its exit status {E(ex)} is not the {E(exp)} its verdict gives"
        if g("audit.worktree_dirty"):
            d += f"; the audit's tools differ from their branch: `{E(g('audit.worktree_dirty'))}`"
    check("audit", ok, E(word or "unreadable"), d)
    # the top level
    tv, av = g("tlc.verdict") or "", g("tlc_agg.verdict") or ""
    kept, nokeep = g("top.slices_kept"), g("top.kept_without_record")
    ok = (tv.startswith("TOP-LEVEL OK") and g("tlc.exit") in (0, None) and av.startswith("TOP-LEVEL OK")
          and g("tlc_agg.exit") == 0 and not nokeep and not g("tlc.problems") and g("tlc.tamper_accepted") == 0
          and g("tlc.slices") == len(kept)
          and (not kept or g("tlc.tamper_rejected") == 2 * len(kept))
          and sum(a["graphs"] for a in g("tlc.accept")) == 2 * g("top.kept"))
    d = (f"kept at {cell} by the filter-only prune: {E(g('top.kept'))} graph(s) in slice(s) "
         f"{E(ranges(kept) or 'none')}; `{E(tv or 'no TOP-LEVEL line')}`")
    if nokeep:
        d += f"; kept with no top-level record: slice(s) {E(ranges(nokeep))}"
    if g("tlc.problems"):
        d += "; " + "; ".join(f"`{E(p)}`" for p in g("tlc.problems"))
    if av != tv:
        d += f"; inside aggregate_fleet.py: `{E(av or 'not run')}`"
    check("top level", ok, E("decided" if ok else "not decided"), d)
    # the blind second verifier: every kept top-level graph's certificate accepted, every tampered copy rejected
    # the graphs it accepted must be exactly the graphs the fleet kept at the top (G5 round 11: a count-only check let
    # a report on another graph through)
    certs = g("top.records_certs_sha256") or {}
    kept_set = sorted([int(s), x, certs.get(str(s))] for s, gs in (g("top.kept_graphs") or {}).items() for x in gs)
    ok = (g("blind.word") == "OK" and g("blind.exit") == 0 and not g("blind.problems")
          and g("blind.accepted") == g("blind.total") == g("top.kept") and bool(g("blind.tried"))
          and g("blind.rejected") == g("blind.tried") and g("blind.accepted_graphs") == kept_set)
    d = (f"`blind-verifier/verify_tree.py`, written from the format and the mathematics alone: "
         f"`{E(g('blind.verdict') or 'no BLIND-CHECK line')}`")
    if g("blind.problems"):
        d += "; " + "; ".join(f"`{E(x)}`" for x in g("blind.problems")[:6])
    if g("blind.total") != g("top.kept"):
        d += f"; it saw {E(g('blind.total'))} certificate(s), the top level keeps {E(g('top.kept'))} graph(s)"
    if g("blind.accepted_graphs") != kept_set:
        d += ("; the graphs it accepted, with their certificate files, are not the graphs the fleet kept at the top "
          "with their records' certificate files")
    check("blind verifier", ok, E("accepts" if ok else "does not accept"), d)
    # G4
    verd = g("g4.verdicts")
    # G5 round 21, finding 6: the scope report covers every copy the audit and the aggregate read, all in scope (an OK
    # line over one copy once met the gate beside 1,955)
    sm = re.fullmatch(r"G4-SCOPE OK: (\d+) of (\d+) full-mode replays and (\d+) of (\d+) slice-mode replays in their "
                      r"mode's scope; (\d+) problem\(s\)", g("g4.scope_verdict") or "")
    # and the root's copies are the aggregate's: the same labels, counted from both
    root_labels_ok = (bool(g("g4.agg_labels")) and g("g4.root_labels") == g("g4.agg_labels")
                      and bool(g("g4.agg_copies")) and g("g4.agg_copies")[0] == g("g4.agg_labels")[0])
    scope_counts_ok = bool(sm) and sm.group(1) == sm.group(2) and sm.group(3) == sm.group(4) and sm.group(5) == "0" \
        and int(sm.group(2)) >= 1 and int(sm.group(2)) + int(sm.group(4)) == g("cov.copies_read") == g("audit.runs")
    ok = (not g("g4.not_pass_or_empty") and not g("g4.other_copies_not_pass_or_empty")
          and sum(verd.get(k, 0) for k in OK_REPLAY) == g("cov.complete") == sum(verd.values())
          and set(g("audit.g4_results") or {}) <= set(OK_REPLAY)
          and sum((g("audit.g4_results") or {}).values()) == g("audit.runs")
          and (g("g4.scope_verdict") or "").startswith("G4-SCOPE OK") and g("g4.scope_exit") == 0
          and scope_counts_ok and g("g4.scope_copies") is not None and g("g4.scope_copies") == g("g4.agg_copies")
          and root_labels_ok)
    d = (f"verdicts over the chosen copies {E(', '.join(f'{k} {v:,}' for k, v in sorted(verd.items())))}; the audit's "
         f"G4 results {E(', '.join(f'{k} {v:,}' for k, v in sorted((g('audit.g4_results') or {}).items())) or 'none')}")
    d += f"; every replay in its mode's scope: `{E(g('g4.scope_verdict') or 'not run')}`"
    if g("g4.not_pass_or_empty") or g("g4.other_copies_not_pass_or_empty"):
        d += (f"; not passed: {E(json.dumps(g('g4.not_pass_or_empty')))}, other copies "
              f"{E(json.dumps(g('g4.other_copies_not_pass_or_empty')))}")
    check("G4", ok, E(" ".join(sorted(verd)) or "none"), d)
    # the aggregate's own problems and self-check (a top_level_check.py problem belongs to the top-level item)
    own = [p for p in g("agg.problems") if not p.startswith("top_level_check.py:")]
    sc = g("agg.self_check")
    bad = [c["check"] for c in sc or [] if not c["ok"]]
    covered = g("cov.complete") == C and not miss and not resumed
    ok = not own and sc is not None and not bad and g("agg.final") == (covered and not g("agg.problems"))
    d = (f"problems {E(len(g('agg.problems')))}" + ("".join(f"; `{E(p)}`" for p in own)) + "; self-check "
         + (E("not run") if sc is None else f"{E(len(sc) - len(bad))} of {E(len(sc))} identities hold"
            + (f", broken: {E(', '.join(bad))}" if bad else "")) + f"; final flag {E(g('agg.final'))}")
    check("aggregate", ok, E("clean" if ok else "not clean"), d)
    # one snapshot
    tc = g("audit.target_cell") or {}
    taken = g("snap.before") is not None and g("snap.after") is not None
    same_fp = not taken or g("snap.before")["sha256"] == g("snap.after")["sha256"]
    audit_root = (re.search(r" under (\S+)$", g("audit.header") or "") or [None, None])[1]
    ok = (same_fp and audit_root == g("agg.root") and g("audit.runs") == g("cov.copies_read")
          and g("audit.missing_slices") == len(miss)
          and tc.get("children") == g("top.children") and tc.get("kept") == g("top.kept")
          and tc.get("slices_with_children") == g("top.slices_with_children"))
    d = (f"root: the audit's is the aggregate's: {E(audit_root == g('agg.root'))}; "
         f"slice copies: the audit {E(g('audit.runs'))}, the aggregate {E(g('cov.copies_read'))}; missing: the audit "
         f"{E(g('audit.missing_slices'))}, the aggregate {E(len(miss))}; the target cell's children and kept: the "
         f"audit {E(tc.get('children'))} and {E(tc.get('kept'))}, the aggregate {E(g('top.children'))} and "
         f"{E(g('top.kept'))}; the root's fingerprint while the tools ran: "
         + E(("unchanged" if same_fp else "changed") if taken else "not taken (saved outputs)"))
    check("snapshot", ok, E("one snapshot" if ok else "different snapshots: re-run"), d)
    # CONTRACT Section 4.3 at level 22: every required known graph kept, in one slice, and the control's red controls red
    rq, fd, qrows, qv = g("l22.required"), g("l22.found"), g("l22.rows") or [], g("l22.verdict") or ""
    lost = [r["index"] for r in qrows if not r["slices"]]
    red_ok = (g("l22.selftest_removed") is not None and g("l22.selftest_missing") == [g("l22.selftest_removed")]
              and g("l22.selftest_flipped_found") is False and g("l22.selftest_dup_reported") is True)
    ok = (qv.startswith("LEVEL-22 CONTROL OK") and g("l22.exit") in (0, None) and not g("l22.problems") and bool(rq)
          and fd == rq == g("l22.required_head") == len(qrows) and not lost and g("l22.dup") == 0 and red_ok)
    qc = g("l22.cell") or [None, None]
    d = (f"of the {E(g('l22.engel'))} known {E(f'({qc[0]},{qc[1]})')} configurations, the {E(rq)} with minimum degree "
         f"at least {E(g('l22.min_degree'))} kept at level {E(qc[0])}: {E(fd)}; `{E(qv or 'no LEVEL-22 CONTROL line')}`")
    if lost:
        d += f"; not kept: Engel {E(', '.join(str(i) for i in lost))}"
    if g("l22.dup"):
        d += f"; kept graphs in more than one slice {E(g('l22.dup'))}"
    if g("l22.problems"):
        d += "; " + "; ".join(f"`{E(p)}`" for p in g("l22.problems"))
    if not red_ok:
        d += "; its self-test did not show that each of its checks can fail"
    check("known graphs", ok, E("kept" if ok else "not shown kept"), d)
    # G5's point 6, option 1: EVERY planned slice verified, the judge's own verdict OK and its exit 0 (G5 round 10,
    # finding 4: a sample with 62 of 63 slices missing once read as COMPLETE, missing being "not yet", not "failed").
    # A slice with only its output or copy missing makes the draft INCOMPLETE; one that disagrees, VERIFICATION FAILED.
    fp, nv, mo = g("vs.failed_problems") or [], g("vs.not_verified") or [], g("vs.missing_only") or []
    # the per-slice lines must add up to the verdict's own count (a line the parser cannot read must not vanish)
    counted = len(g("vs.verified_restarted") or []) + len(g("vs.verified_random") or [])
    # G5 round 19, finding 6: the rows must be the plan's slices, each once (63 copies of one row once counted 63)
    B = g("vs.accounted") or {}
    vs_rows = (B.get("exact") is True and not B.get("stray_count") and not B.get("whole_wrong")
               and not B.get("bad_ok_count") and not B.get("skip_wrong")
               and not B.get("wrong_copy") and not B.get("first_not_whole"))   # G5 round 21, finding 7
    # G5 round 20, finding 6: its scope too, as the rows show it: every worker's first slice checked whole or declared
    # skipped (its prefix by hash), at least one checked whole, and the footer's count the rows' (a sample whose whole
    # checks were all turned into checks from level 13, under a footer of 0 of 10, once met the gate)
    vs_scope = ((B.get("whole_rows") or 0) >= 1 and B.get("whole_rows") == g("vs.whole")
                and (B.get("whole_rows") or 0) + (B.get("skip_rows") or 0) == g("vs.workers")
                and g("vs.workers") == B.get("planned_workers")   # the footer's workers are the plan's
                # G5 round 23, finding 7: and its seed and counts, restarted and random, the plan's
                and g("vs.seed") == B.get("plan_seed") and g("vs.restarted") == B.get("plan_restarted")
                and g("vs.random") == B.get("plan_random")
                and g("vs.from_level") == vsm.FROM)   # G5 round 24, finding 5: the level the rows were checked from
    ok = (g("vs.word") == "OK" and g("vs.exit") == 0 and not fp and not nv and bool(g("vs.planned"))
          and counted == g("vs.verified") == g("vs.planned") and not g("vs.problem_count")
          and vs_rows and vs_scope and B.get("ok_rows") == g("vs.planned") and B.get("not_rows") == 0)
    # and finding 7: a report that does not account for its slices, or a slice not verified that no missing evidence
    # explains, is a failure, never "not yet"
    vs_bad = bool(fp) or (g("vs.verdict") is not None and (not vs_rows or bool(B.get("unexplained"))
                                                           or (g("vs.word") == "OK" and not vs_scope)
                                                           # finding 7: a FAIL no row explains
                                                           or (g("vs.word") == "FAIL" and not B.get("not_rows"))))
    d = (f"{E(g('vs.verified'))} of {E(g('vs.planned'))} sampled slices re-run with nothing deleted and checked, their "
         f"result files identical to the fleet's; `{E(g('vs.verdict') or 'no VERIFY-SAMPLE line')}`")
    if mo:
        d += f"; not yet verified (no check output or copy, nothing failed): {E(ranges(mo))}"
    if fp:
        d += "; failed: " + "; ".join(f"`{E(x)}`" for x in fp[:6]) + (f" and {E(len(fp) - 6)} more" if len(fp) > 6 else "")
    if counted != g("vs.verified") or counted + len(nv) != g("vs.planned"):
        d += (f"; the per-slice lines count {E(counted)} verified and {E(len(nv))} not, against the verdict's "
              f"{E(g('vs.verified'))} of {E(g('vs.planned'))}")
    d += rows_note(B)
    check("certification sample", ok, E("all verified" if ok else "a failure" if vs_bad
                                        else "not all verified" if g("vs.verdict") else "not run"), d)

    # CONTRACT 4.1 and 4.3 as whole trees, and the full re-run: gate evidence. Not yet run or not yet complete, they
    # leave the gates open, not the enumeration; a real failure (every slice in and the top level wrong, or a slice
    # re-run that disagrees) is the state CONTROL FAILED or VERIFICATION FAILED
    # each piece of evidence must be for the contract's requirement, as its parameters line states it (G5 round 12:
    # a degree-6 control and a four-graph calibration once passed as the required ones), and a recorded failure is
    # never "open" (only absence is): a failing slice, a graph kept, a known graph lost, a broken checker
    want22 = (f"target {CONSTANTS['control22_cell'][0]}, root minimum degree {CONSTANTS['control22_root_k'][0]}, "
              "u-bar override refused, top level empty, known none; ")
    ran22 = g("c22.exit") is not None   # the tool ran (G5 round 14: an interrupted run, no verdict line, once read open)
    # G5 round 21, finding 7: the footer's own cell and denominator are the contract's (a footer naming another target
    # or 9,999 slices under the right parameters once met the gate)
    # G5 round 24, finding 5: a report's MISSING line is its own footer's count, and its checker the committed one
    tc_sha = sha256(HERE.parent / "target_check.py")   # the checker these reports must name: the committed one
    footer = lambda key, cell: (g(f"{key}.cell") is not None and f"({g(f'{key}.cell')[0]},{g(f'{key}.cell')[1]})" == cell
                                and g(f"{key}.slices") == C and g(f"{key}.missing_listed") == g(f"{key}.missing")
                                and bool(tc_sha) and f"checker target_check.py sha256 {tc_sha}" in (g(f"{key}.parameters") or ""))
    ok22 = (g("c22.word") == "OK" and g("c22.exit") == 0 and g("c22.complete") == g("c22.g4_pass") == C
            and footer("c22", CONSTANTS["control22_cell"][0])
            and (g("c22.audit") or "").startswith("COVERAGE (summary only) OK")
            and g("c22.failing") == 0 and g("c22.missing") == 0 and g("c22.kept") == 0 and bool(g("c22.selftest_ok"))
            and not g("c22.problems") and (g("c22.parameters") or "").startswith(want22))
    # every PROBLEM line of target_check.py is a failure (absence has its own MISSING line): G5 round 13, a global
    # problem beside otherwise complete counts once read as open
    # G5 round 19, finding 7: a FAIL is open only when absence explains all of it (nothing failing, the slices missing
    # listed as missing, every other slice complete with its G4 PASS); a FAIL with nothing failing and nothing missing
    # once read as open
    pending = lambda key: (g(f"{key}.word") == "FAIL" and g(f"{key}.failing") == 0 and (g(f"{key}.missing") or 0) > 0
                           and g(f"{key}.missing_listed") == g(f"{key}.missing") and g(f"{key}.slices") == C
                           and g(f"{key}.complete") == g(f"{key}.g4_pass")
                           and (g(f"{key}.complete") or 0) + g(f"{key}.missing") == C)
    bad22 = bool(g("c22.problems")) or (ran22 and (g("c22.verdict") is None or (g("c22.failing") or 0) > 0
                                                   or (g("c22.word") is not None and not footer("c22",
                                                                                              CONSTANTS["control22_cell"][0]))
                                                   or (g("c22.word") == "FAIL" and not pending("c22"))
                                                   or g("c22.word") not in ("OK", "FAIL")   # G5 round 18, finding 6
                                                   or (g("c22.word") == "OK") != (g("c22.exit") == 0)
                                                   or (g("c22.kept") or 0) > 0 or not g("c22.selftest_ok")
                                                   or not (g("c22.parameters") or "").startswith(want22)
                                                   or (g("c22.missing") == 0 and not (g("c22.audit") or "")
                                                       .startswith("COVERAGE (summary only) OK"))))
    k = lambda name: E(CONSTANTS[name][0])
    d = (f"the whole {k('control22_cell')} tree, with no u-bar override at its level below and root minimum degree "
         f"{k('control22_root_k')} (Lemma D4), must keep nothing at its top: "
         f"`{E(g('c22.verdict') or 'not run yet')}`" + (f"; `{E(g('c22.selftest'))}`" if g("c22.selftest") else ""))
    if ran22 and not ok22:
        d += (f"; {E(g('c22.failing'))} slice(s) failing, {E(g('c22.missing'))} missing, as required: "
              f"`{E(g('c22.parameters') or 'no parameters line')}`")
    check("tree control", ok22, E("empty" if ok22 else "fails" if bad22 else "open"), d, gate=not bad22)
    wantcal = (f"target {CONSTANTS['calib_cell'][0]}, root minimum degree {CONSTANTS['calib_root_k'][0]}, u-bar override "
               f"the fleet 22=60 only, top level holding the known graphs, known engel-21-57.g6 sha256 {ENGEL_2157_SHA256} "
               "(5 graphs); ")
    rancal = g("cal.exit") is not None
    okcal = (g("cal.word") == "OK" and g("cal.exit") == 0 and g("cal.complete") == g("cal.g4_pass") == C
             and footer("cal", CONSTANTS["calib_cell"][0])
             and (g("cal.kept") or 0) >= (g("cal.found") or 0)   # G5 round 23, finding 7
             and g("cal.failing") == 0 and g("cal.missing") == 0 and g("cal.known") == 5 and g("cal.found") == 5
             and (g("cal.audit") or "").startswith("COVERAGE (summary only) OK")
             and bool(g("cal.selftest_ok")) and not g("cal.problems") and (g("cal.parameters") or "").startswith(wantcal))
    badcal = bool(g("cal.problems")) or (rancal and (g("cal.verdict") is None or (g("cal.failing") or 0) > 0
                                                     or (g("cal.word") is not None and not footer("cal",
                                                                                                CONSTANTS["calib_cell"][0]))
                                                     # G5 round 23, finding 7: no more known graphs found than kept
                                                     or (g("cal.kept") is not None and g("cal.found") is not None
                                                         and g("cal.kept") < g("cal.found"))
                                                     or (g("cal.word") == "FAIL" and not pending("cal"))
                                                     or g("cal.word") not in ("OK", "FAIL")   # G5 round 18, finding 6
                                                     or (g("cal.word") == "OK") != (g("cal.exit") == 0)
                                                     or not g("cal.selftest_ok")
                                                     or not (g("cal.parameters") or "").startswith(wantcal)
                                                     or (g("cal.missing") == 0 and (g("cal.found") or 0) < 5)
                                                     or (g("cal.missing") == 0 and not (g("cal.audit") or "")
                                                         .startswith("COVERAGE (summary only) OK"))))
    d = (f"the whole {k('calib_cell')} tree, root minimum degree {k('calib_root_k')} (Schade's bound), must keep all "
         f"{k('calib_known')} of AMP's extremal graphs: `{E(g('cal.verdict') or 'not run yet')}`"
         + (f"; `{E(g('cal.selftest'))}`" if g("cal.selftest") else ""))
    if rancal and not okcal:
        d += (f"; {E(g('cal.failing'))} slice(s) failing, {E(g('cal.missing'))} missing, as required: "
              f"`{E(g('cal.parameters') or 'no parameters line')}`")
    check("calibration", okcal, E("all kept" if okcal else "fails" if badcal else "open"), d, gate=not badcal)
    # G5 round 19, findings 6 and 7: the rows must be the plan's 1,920 slices, each once with its worker, the whole
    # ones exactly the workers' first slices; and a FAIL is open only when missing evidence explains every slice not
    # verified (a footer with no rows once met the gate; a NOT verified row with no explanation once read as open)
    A = g("va.accounted") or {}
    # G5 round 20, finding 6: every verified row read in full (its check, CHAIN verdict, certificate count, files digest
    # and notes), no row declaring a skipped whole check, and the lean rows the footer's lean count
    va_rows = (A.get("exact") is True and not A.get("stray_count") and not A.get("whole_wrong")
               and not A.get("bad_ok_count") and not A.get("skip_rows") and A.get("lean_rows") == (g("va.lean") or 0)
               and not A.get("wrong_copy") and not A.get("first_not_whole"))   # G5 round 21, finding 7
    okva = (g("va.word") == "OK" and g("va.exit") == 0 and g("va.verified") == g("va.planned") == C
            and g("va.tasks") == g("va.expected_tasks") and g("va.whole") == g("va.tasks")
            and g("va.problems_count") == 0 and not g("va.problem_lines") and not g("va.not_verified")
            and not g("va.failed_problems") and not g("va.missing")
            and va_rows and A.get("ok_rows") == C and A.get("not_rows") == 0
            and A.get("whole_rows") == g("va.expected_tasks"))
    # a recorded failure, whatever the verdict line says; and a judge that ran but did not report completely and
    # consistently (G5 round 17, finding 6: a judge that crashed before printing anything once read as open, and an OK
    # line with a problem and no whole check as met)
    ranva = g("va.exit") is not None
    badva = bool(g("va.failed_problems")) or (ranva and (
        g("va.verdict") is None or g("va.problems_count") is None
        or g("va.problems_count") != g("va.problem_lines")
        or (g("va.word") == "OK") != (g("va.exit") == 0)
        or (g("va.word") == "OK" and (g("va.problems_count") != 0 or g("va.whole") != g("va.tasks")))
        # G5 round 18, finding 6: an unparsed verdict, and an OK that contradicts the report's own lines or plan
        or g("va.word") not in ("OK", "FAIL")
        or (g("va.word") == "OK" and (bool(g("va.not_verified")) or g("va.tasks") != g("va.expected_tasks")
                                      or g("va.verified") != C or g("va.planned") != C))
        or not va_rows or bool(A.get("unexplained")) or A.get("ok_rows") != g("va.verified")
        or (A.get("ok_rows") or 0) + (A.get("not_rows") or 0) != C
        # G5 round 20, finding 7: a FAIL is open only with a slice not verified, and missing evidence explaining each
        # (a FAIL of 1,920 verified rows and no problem once read as open)
        or (g("va.word") == "FAIL" and not A.get("not_rows"))))
    d = (f"every slice re-run with nothing deleted and checked (`u23-verify-all-claude`, Claude cloud): "
         f"`{E(g('va.verdict') or 'not run yet')}`")
    if badva:
        d += "; failed: " + "; ".join(f"`{E(x)}`" for x in g("va.failed_problems")[:4])
        d += rows_note(A)
    check("full re-run", okva, E("all verified" if okva else "a failure" if badva else "open"), d, gate=not badva)

    failing = [c for c in checks if not c["ok"] and not c.get("gate")]
    if not failing:
        state = "COMPLETE"
    elif all(c["name"] in ("top level", "blind verifier") for c in failing):
        state = "TOP LEVEL NOT DECIDED"
    elif vs_bad or any(c["name"] == "full re-run" for c in failing):
        state = "VERIFICATION FAILED"
    elif checks[0]["ok"] and any(c["name"] in ("known graphs", "tree control", "calibration") for c in failing):
        state = "CONTROL FAILED"
    else:
        state = "INCOMPLETE"
    k = g("top.kept")
    if state == "COMPLETE":
        top = (f"the {E(k)} graph(s) the fleet's filter-only prune kept at {cell} each carry a refutation that both "
               f"checkers accept (`{E(tv)}`) and a blind second verifier accepts (`{E(g('blind.verdict'))}`)" if k
               else f"the fleet's filter-only prune kept no graph at {cell} (`{E(tv)}`)")
        headline = (f"The enumeration {NO_GRAPH.format(cell=cell)}. All {E(C)} of {E(C)} slices have a complete copy; "
                    f"the coverage audit says `{E(g('audit.coverage_line'))}`; {top}; the G4 replays give "
                    f"{E(', '.join(f'{a} {b:,}' for a, b in sorted(verd.items())))}. If the gates of Section 6 are "
                    f"all green, u(23) = {E(g('contract.lower'))}.")
    elif state == "VERIFICATION FAILED":
        vc = next((c for c in failing if c["name"] == "full re-run"), None) \
            or next(c for c in checks if c["name"] == "certification sample")
        headline = (f"A re-run slice {E('did not verify')} ({vc['name']}): {vc['detail']}. Its re-run with nothing deleted, or the full "
                    "check of its run directory, disagrees with the fleet; this draft states nothing about u(23). "
                    "Open: " + "; ".join(f"{c['name']} ({c['status']})" for c in failing) + ".")
    elif state == "CONTROL FAILED":
        kg = next(c for c in failing if c["name"] in ("known graphs", "tree control", "calibration"))
        headline = (f"A control of CONTRACT Section 4 does not hold ({kg['name']}): {kg['detail']}. "
                    "A configuration the enumeration must keep is missing, or the control is broken; this draft states "
                    "nothing about u(23). Open: " + "; ".join(f"{c['name']} ({c['status']})" for c in failing) + ".")
    elif state == "TOP LEVEL NOT DECIDED":
        headline = (f"The top level is {E('not decided')}: "
                    + "; ".join(f"{c['name']}: {c['detail']}" for c in failing)
                    + ". CONTRACT Section 3 asks for an exact embedding or an accepted refutation of every such graph; "
                    "this draft states nothing about u(23).")
    else:
        headline = (f"The enumeration is {E(state)}: this draft states nothing about u(23). Open: "
                    + "; ".join(f"{c['name']} ({c['status']})" for c in failing) + ".")
    return {"state": state, "headline": headline, "checks": checks, "failing": [c["name"] for c in failing]}


# ----------------------------------------------------------------------------------------------------------- render

def table(head: list, rows: list, align: list) -> list:
    return ["| " + " | ".join(head) + " |", "|" + "|".join("---:" if a == "r" else "---" for a in align) + "|",
            *["| " + " | ".join(r) + " |" for r in rows]]


def render(V: dict, D: dict, lint_note: str | None = None) -> str:
    g = lambda k: V["v"][k]["value"]
    C, L, W = g("plan.slices"), g("plan.slice_level"), g("plan.workers")
    tn, tm = g("plan.target")
    cell = E(f"({tn},{tm})")
    state = D["state"]
    ck = {c["name"]: c for c in D["checks"]}
    sw = g("prov.software")
    h8 = lambda name: E("/".join(sw.get(name, ["?"])))
    inputs = g("prov.inputs")
    fb = inputs.get("forbidden-398.json") or ["?"]
    tu = inputs.get("tu-gadgets.json") or ["?"]
    kept = g("top.slices_kept")
    o = [f"# u(23): the {cell} enumeration (DRAFT for the human)", "",
         f"**A DRAFT for the human, not a result.** Generated {E(V['about']['generated_utc'])} by "
         "`research/unit-distance-23/tools/write_result.py`, for gate G6 (the write-up generated from checker and "
         "manifest output only). Every number and status word below is read from a file: the outputs of the tools in "
         "Section 8, the records they rest on (the top-level records, the G5 reads, `JOBS.md`), and `CONTRACT.md`, "
         "whose sentences are quoted verbatim. The one exception is a parameter of the options put to the human "
         "in Section 6 (the sample's size), which is the supervisor's. `results/u23/result-values.json` names each value's source. "
         "Writing to Alexeev, Mixon and Parshall, and any OEIS, arXiv or Zenodo publication, are the human's "
         "(CONTRACT Section 7).", "",
         f"**Headline: {E(state)}.** {D['headline']}", ""]
    if D["failing"]:
        o += ["What is open:"] + [f"- **{c['name']}** ({c['status']}): {c['detail']}." for c in D["checks"]
                                  if not c["ok"]] + [""]
    elif any(not c["ok"] for c in D["checks"]):
        o += ["Still open, for the gates of Section 6 (not for the enumeration's state):"] + [
            f"- **{c['name']}** ({c['status']}): {c['detail']}." for c in D["checks"] if not c["ok"]] + [""]
    # 1
    o += ["## 1. Statement and dependencies", "", "CONTRACT Section 0, verbatim:", "",
          f"> {E(g('contract.intro'))}", ""]
    if state == "COMPLETE":
        o += [f"**Statement (DRAFT, for the human).** The enumeration of Section 3 {NO_GRAPH.format(cell=cell)}. "
              f"If the gates of Section 6 are all green, u(23) = {E(g('contract.lower'))}. The CONTRACT's own "
              "sentence on when that claim is allowed (Section 0):", "", f"> {E(g('contract.claim_64'))}", ""]
    else:
        o += [f"**No statement.** The enumeration's state is {E(state)} (the headline lists what is open), so this "
              "draft states nothing about u(23). The CONTRACT's rule (Section 0):", "",
              f"> {E(g('contract.claim_64'))}", ""]
    o += ["The dependencies, CONTRACT Section 0 and amendment 2, verbatim:", "", f"> {E(g('contract.never'))}", ">",
          f"> {E(g('contract.amend2_deps'))}", "", "Where each lives:",
          f"- u(22) = {E(g('run.ubar22'))}: `research/unit-distance-22/RESULT-u22.md`; every slice ran with u-bar(22) = "
          f"{E(g('run.ubar22'))} in place of AMP's {E(g('run.ubar22_builtin'))}, its justification recorded in the "
          "run options;",
          "- AMP's values of u(n): Alexeev, Mixon and Parshall, `arXiv:2412.11914`, Theorem 1 (with Schade's lemma, "
          "which gives the upper bound above);",
          f"- the {E(g('run.forbidden_set'))} minimal forbidden graphs: Globus and Parshall's list and GP-10's "
          "ten-vertex list (`research/gp-10/RESULT.md`), as `research/unit-distance-22/data/forbidden-398.json`, "
          f"sha256 `{E(' / '.join(fb))}` in every slice copy's manifests and G4 replays;",
          "- the six TU gadgets: `research/unit-distance-22/check/PROOFS.md` (`tu-gadgets.json`, sha256 "
          f"`{E(' / '.join(tu))}` in every prune manifest);",
          "- Lemma R and Lemma T: `research/unit-distance-23/RHOMBUS-SPEC.md` Sections 1 and 4, "
          "`research/unit-distance-22/enum/PRUNING.md` Section 5; their certificates are checked by "
          "`check/udcheck_rhombus.py` and `check/tri_verify.py`, which hand every other record to the hash-pinned "
          "`check/udcheck.py` or `check/udcheck398.py`.", ""]
    # 2
    o += [f"## 2. What a {cell} unit-distance graph would have to be", "", "CONTRACT Section 1, verbatim:", ""]
    o += [f"> - {E(b)}" for b in g("contract.section1")]
    o += ["", "And, by amendment 2, hereditarily like the gadgets: no 4-cycle rows (Lemma R) or triangle "
          "orientations (Lemma T) of the graph, or of any induced subgraph, force a collision or a unit distance on a "
          "non-edge (`RHOMBUS-SPEC.md`, `PRUNING.md` Section 5).", ""]
    # 3
    o += ["## 3. The enumeration", "",
          f"Method (CONTRACT Section 2 and amendments 1 to 3). The run options below are the same in every slice copy "
          f"(identical: {E(g('prov.run_options_identical'))}).",
          f"- `research/unit-distance-22/enum/udenum` in Mode {E(g('run.forbidden_set'))} (the fast binary of "
          f"amendment 3, `{h8('udenum')}` in every copy): canonical augmentation by minimum-degree deletion, from "
          f"the seeds at level {E(g('run.seed_n'))} to level {E(tn)}.",
          f"- The reach table from {cell} with root k = {E(g('run.root_k'))} and u-bar(22) = {E(g('run.ubar22'))}: "
          "the windows in Section 4.1.",
          f"- Hereditary pruning from level {E(g('run.prune_from'))}: `udfilter` (the six gadgets, its containment "
          f"re-check on set {E(g('run.prune_filter_set'))}) and `udtriangle` (Lemmas R and T). Every graph gets "
          "one certificate line; the prune step replays the whole certificate file with `check/udcheck_rhombus.py` "
          "and re-reads its outputs (`prune.py`'s `verify_outputs`: the keep file is exactly the kept records, kept "
          f"plus pruned the input); every stage file is re-checked against all {E(g('run.forbidden_set'))} (stage "
          f"verification: {E(g('run.verify_stages'))}).",
          f"- The prune is filter-only (filter-only: {E(g('run.prune_filter_only'))}; embedder tries "
          f"{E(g('run.prune_tries'))}): a graph that survives every rule is kept, and at the top level CONTRACT "
          "Section 3 decides it (Section 4.2).",
          f"- Level {E(L)} is split into {E(C)} slices by record hash. Each worker regenerates the prefix, levels "
          f"{E(g('run.seed_n'))} to {E(L)}, itself (Section 5 compares the copies), and runs its slices to level "
          f"{E(tn)}.", ""]
    amended = g("contract.amended_slicing_level")
    if g("contract.slicing_level") != L and amended != L:
        o += [f"The CONTRACT and the run disagree on one parameter: CONTRACT Section 2 says slicing at level "
              f"{E(g('contract.slicing_level'))}, the run options say level {E(L)}, and the slicing level an amendment "
              f"in CONTRACT Section 8 sets is {E(amended)}. An amendment is owed.", ""]
    rw = g("cov.rerun_workers")
    o += [f"The fleet (`coordination/cloud-workers/JOBS.md`, entry `u23-fleet`): {E(W)} planned workers of "
          f"{E(g('plan.slices_per_worker'))} interleaved slices each, run as cloud sessions in waves"
          + (f", since the cloud cap was about {E(g('jobs.cap'))} concurrent sandboxes" if g("jobs.cap") else "")
          + f". Tags re-fired after a lost or stuck session started fresh sandboxes and re-ran slices already pushed "
          f"({E(g('cov.refired_tags'))} tags with several result directories). A container restart makes the runbook "
          "resume from its own files, and a resumed cell's summary keeps neither its parents nor its share, so the "
          f"summary audit cannot bind it (JOBS.md): {E(len(g('cov.rerun_slices')))} slices "
          f"({E(ranges(g('cov.rerun_slices')) or 'none')}) have such a copy and a fresh one, and the fresh copy is "
          "the one counted; the rerun workers, outside the plan's owners, made "
          + E(", ".join(f"{w} {k}" for w, k in sorted(rw.items())) or "none") + " of the copies. Slices whose every "
          f"copy has resumed cells: {E(ranges(g('cov.every_copy_resumed')) or 'none')}. {E(g('cov.several'))} slices "
          "hold several complete copies (Section 5).", ""]
    # 4
    lv = g("tree.levels")
    scope = (f"all {E(C)} slices" if g("cov.complete") == C else
             f"the {E(g('cov.complete'))} of {E(C)} slices with a complete copy (partial)")
    kinds = g("tree.kinds")
    rows = []
    for e in lv:
        rows.append([E(e["n"], "d"), E(e["window"]), E(e["cells"]), E(e["children"]), E(e["kept"]), E(e["pruned"]),
                     *[E(e["by_kind"].get(k, 0)) for k in kinds],
                     E(e["pct_pruned"], ".1f") if e["pct_pruned"] is not None else E("-")])
    ot = g("tree.other_totals")
    o += ["## 4. What the run produced", "", f"### 4.1 The tree above level {E(L)}", "",
          f"Over {scope}, one copy each (`aggregate_fleet.py`):", "",
          *table(["level", "window m (reach table)", "cells", "children", "kept", "pruned", *[E(k) for k in kinds],
                  "% pruned"], rows, ["l", "l"] + ["r"] * (5 + len(kinds))), "",
          "The other count keys, summed over these cells: " + ", ".join(f"{E(k)} {E(v)}" for k, v in ot.items())
          + f". Children minus prune input (the reach filter's drops): {E(g('tree.reach_dropped'))}. At level "
          f"{E(tn)}, kept means kept by the filter-only prune; Section 4.2 decides those graphs.", ""]
    if not all(e["cells_are_window"] for e in lv):
        o += [f"Levels whose cells are not the reach window: {E(', '.join(str(e['n']) for e in lv if not e['cells_are_window']))}.", ""]
    o += [f"### 4.2 The top level {cell} and its certificate", "",
          f"Over {scope}: children at {cell} {E(g('top.children'))}; kept by the filter-only prune "
          f"{E(g('top.kept'))}, in slice(s) {E(ranges(kept) or 'none')}.", ""]
    for i in sorted(kept):
        gl = g("top.kept_graphs").get(i) or []
        rec = g("rec.prune").get(i) or g("rec.prune").get(str(i))
        red = g("rec.red_control").get(i) or g("rec.red_control").get(str(i))
        o.append(f"- Slice {E(i, 'd')}: " + ", ".join(f"`{E(x)}`" for x in gl) + ". "
                 + (f"Its record `{E(g('top.records_dir'))}/s{E(i, 'd')}of{E(C, 'd')}/` (graph, certificate, prune "
                    f"manifest, CHECK.txt): the full prune with the embedder on gives "
                    f"`{E(json.dumps(rec['counts']))}` and `{E(rec['checker'])}`"
                    + (f"; its red control (a proof-tree entry changed): `{E(red)}`" if red else "") + "."
                    if rec else "It has no record."))
    o += ["", "CONTRACT Section 3, verbatim:", "", f"> {E(g('contract.section3'))}", "",
          f"`top_level_check.py` with its self-test, which replays each record with both checkers and a tampered "
          f"copy of each certificate (exit {E(g('tlc.exit'))}):", "", "```", *[E(x) for x in g("tlc.lines")], "```", "",
          f"`blind_check.py`: the blind second verifier (`research/unit-distance-23/blind-verifier/`, its "
          f"README says how it was made: from the format and the mathematics alone, sharing no code with "
          f"`check/udcheck.py`, which `check/udcheck398.py` executes) on each record, and seven tampered copies of each "
          f"certificate made afresh (exit {E(g('blind.exit'))}):", "", "```", *[E(x) for x in g("blind.lines")],
          "```", "",
          f"Graphs kept with no record: {E(ranges(g('top.kept_without_record')) or 'none')}."
          + (f" The self-test's rejection lines with no reason: {E(g('tlc.tamper_no_reason'))} of "
             f"{E(g('tlc.tamper_rejected'))}. It counts any nonzero exit of a checker as a rejection and shows the "
             "checker's standard output, while the checkers write `REJECT` on standard error; the reason for the "
             "record's own red control is the one quoted above." if g("tlc.tamper_no_reason") else ""), ""]
    part = g("audit.slice_partition") or {}
    prows = [[E(f"({L},{pm})"), E(p.get("stage_file")), E(p.get("sum")), E(p.get("slices_recording")),
              E(ranges(p.get("present_slices_without_a_share") or []) or "none")]
             for pm, p in sorted(part.items(), key=lambda t: int(t[0]))]
    o += ["### 4.3 Coverage and reruns", "",
          f"- Slices with a complete copy: {E(g('cov.complete'))} of {E(C)}"
          + (f"; missing {E(len(g('cov.missing_slices')))}: {E(g('cov.missing_ranges'))}" if g("cov.missing_slices")
             else "") + f". Copies read {E(g('cov.copies_read'))} from {E(g('cov.worker_dirs_with_copies'))} worker "
          f"directories; skipped as incomplete {E(g('cov.copies_skipped'))}, misfiled {E(g('cov.copies_misfiled'))}, "
          f"unfinished {E(g('cov.copies_unfinished'))}.",
          f"- The coverage audit (`verify-chain.py --summary-only`, pinned to target "
          f"{E(tuple((g('audit.pinned') or {}).get('target') or ()))}, seed level "
          f"{E((g('audit.pinned') or {}).get('seed'))} and slices {E(tuple((g('audit.pinned') or {}).get('slices') or ()))}"
          f" (level, count), requiring {E(', '.join(g('audit.required') or []) or 'nothing')}; branch "
          f"`{E(g('audit.worktree_branch') or G5_BRANCH)}` at `{E((g('audit.worktree_head') or '?')[:10])}`): "
          f"{E(g('audit.header'))}. Summaries {E(g('audit.summaries'))}, slice indices {E(g('audit.slice_indices'))}, "
          f"missing {E(g('audit.missing_slices'))}; prefix cells {E(g('audit.prefix_cells'))}, with their parents "
          f"recorded {E(g('audit.prefix_cells_with_parents_recorded'))}; cells recovered from pushed history "
          f"{E(g('audit.cells_recovered_from_history'))}; problems {E(g('audit.problems'))}, unresolved "
          f"{E(g('audit.unresolved'))}. Its verdict: `{E(g('audit.coverage_line'))}`, `{E(g('audit.chain_line'))}`"
          f" (exit {E(g('audit.exit'))}). A summary-only audit never says more than that: it reads no level, keep, "
          "parent or certificate file.",
          "- The slices partition every level-" + E(L) + " parent cell: each slice records its share, and the audit "
          "requires the shares to add up to the stage file once every slice is present.", "",
          *table(["parent cell", "records in the stage file", "sum of the recorded shares", "slices recording",
                  "slices present without a share"], prows, ["l", "r", "r", "r", "l"]), ""]
    heavy = ", ".join(f"s{h['slice']} {h['seconds']:,.1f} s ({h['worker']})" for h in g("cost.heaviest"))
    o += ["### 4.4 Cost", "",
          f"By `fleet_status.py`'s rule (step timings of the cells above level {E(L)}; a resumed cell's time is "
          f"unknown, so a slice with one is not timed): {E(g('cost.slices_timed'))} slices timed, "
          f"{E(g('cost.excluded'))} excluded, **{E(g('cost.seconds'))} s** ({E(g('cost.hours'), ',.2f')} h). Per "
          f"slice: median {E(g('cost.median'))} s, p90 {E(g('cost.p90'))} s, max {E(g('cost.max'))} s; the heaviest "
          f"{E(heavy)}. The runbook's own clocks over {E(g('cost.clock_copies'))} copies: `run-dag2.py` "
          f"{E(g('cost.run_dag2_s'))} s, the G4 replay {E(g('cost.replay_s'))} s.", ""]
    # 5
    t = g("g4.totals")
    qc = g("l22.cell") or [None, None]
    qcell = E(f"({qc[0]},{qc[1]})")
    sc = g("agg.self_check")
    adm = g("contract.reach_admits")
    reach = g("run.reach_levels")
    adm_rows = [(n, lohi, [min(reach.get(n) or [0]), max(reach.get(n) or [0])]) for n, lohi in sorted(adm.items())]
    o += ["## 5. Cross-checks that were actually run", "",
          f"- **G4, the independent replay** (`enum2/replay-398.py` with `enum2.py`, sharing no code with `udenum` but "
          f"using the same nauty release for canonical labelling and automorphism orbits, so a defect there would reach "
          f"both; "
          f"`{h8('replay-398.py')}` and `{h8('enum2.py')}` in every copy): verdicts "
          f"{E(', '.join(f'{k} {v:,}' for k, v in sorted(g('g4.verdicts').items())))} over the chosen copies; modes "
          f"{E(', '.join(f'{k} {v:,}' for k, v in sorted(g('g4.modes').items(), key=str)))}; full-mode replays with "
          f"every red control red {E(g('g4.full_mode_red_all'))}. Parents sampled {E(t['sampled_parents'])}, "
          f"processed {E(t['processed_parents'])}; production children compared "
          f"{E(t['production_children_compared'])}; mismatching parents {E(t['mismatching_parents'])}; stage files "
          f"re-derived {E(t['stages_checked'])}. The audit derives each replay's verdict again from its evidence and "
          f"binds its rows to the summaries: {E(', '.join(f'{k} {v:,}' for k, v in sorted((g('audit.g4_results') or {}).items())) or 'none')}.",
          f"- **The prefix is the same on every worker**: {E(g('prov.prefix_files'))} files of levels up to "
          f"{E(L)} (`hashes.json`) with identical sha256 in all {E(g('prov.prefix_copies'))} copies: "
          f"{E(g('prov.prefix_agree'))}; the audit: {E(g('audit.prefix_files_hashed'))} prefix files hashed, identical "
          f"in {E(g('audit.prefix_files_identical_in'))} summaries. Every worker computed the prefix itself.",
          f"- **Duplicate copies agree**: {E(g('cov.several'))} slices hold several complete copies; their counts "
          f"rows, shipped level files and kept graphs are identical: {E(g('cov.several_agree'))}.",
          f"- **The top-level certificates**: each record replayed by `check/udcheck.py` and `check/udcheck398.py` "
          f"({E(len(g('tlc.accept')))} checker lines above), each tampered copy not accepted "
          f"({E(g('tlc.tamper_rejected'))} of {E(2 * len(kept))}; accepted {E(g('tlc.tamper_accepted'))}). The "
          f"two are one implementation (`check/udcheck398.py` executes `check/udcheck.py`'s pinned bytes), so a "
          f"blind second verifier, written from the format and the mathematics alone (`blind_check.py`, "
          f"{ck['blind verifier']['status']}), accepts {E(g('blind.accepted'))} of {E(g('blind.total'))} and rejects "
          f"{E(g('blind.rejected'))} of {E(g('blind.tried'))} tampered inputs.",
          f"- **Known graphs survive** (CONTRACT Section 4.3 at level {E(qc[0])}; `level22_control.py`, "
          f"{ck['known graphs']['status']}): of Engel et al.'s {E(g('l22.engel'))} known {qcell} configurations "
          f"(`{E(g('l22.engel_file'))}`, sha256 `{E((g('l22.engel_sha256') or '?')[:16])}`), each the unit-distance "
          f"graph of its own points, the {E(g('l22.required'))} with minimum degree at least "
          f"{E(g('l22.min_degree'))} must be kept at level {E(qc[0])}; kept: {E(g('l22.found'))}, "
          + ", ".join(f"Engel {E(r['index'], 'd')} in {E(', '.join(r['slices']) or 'none')}" for r in g("l22.rows")
                      or []) + f". The fleet's keep files at level {E(qc[0])} hold {E(g('l22.kept_distinct'))} "
          f"distinct {qcell} graphs over {E(g('l22.copies'))} slice copies, {E(g('l22.not_engel'))} of them not "
          f"Engel's (the filter-only prune keeps what it cannot decide), and {E(g('l22.dup'))} of them in more than "
          f"one slice. Its self-test: with Engel {E(g('l22.selftest_removed'))}'s form removed it reports missing "
          f"{E(g('l22.selftest_missing'))}; an edge-flipped Engel graph found: {E(g('l22.selftest_flipped_found'))}; "
          f"a graph placed in a second slice reported: {E(g('l22.selftest_dup_reported'))}. `{E(g('l22.verdict'))}` "
          f"(exit {E(g('l22.exit'))}).",
          f"- **The certification sample** (G5's point 6, the human's choice; `verify_sample.py`, "
          f"{ck['certification sample']['status']}): {E(g('vs.verified'))} of {E(g('vs.planned'))} sampled slices "
          "re-run with nothing deleted, each run directory checked in full by the G5-closed `verify-chain.py --check` "
          f"({E(g('vs.whole'))} checked whole from the seed level, the rest from level {E(g('vs.from_level'))} with the "
          "prefix compared), and each re-run's result files identical to the fleet's copy of the slice; the random "
          f"part drawn by a published seed ({E(g('vs.seed'), 'd')}), which the tool re-draws. Section 6 has the "
          "details.",
          f"- **The full re-run** (beyond point 6's sample; `u23-verify-all-claude` on Claude cloud, judged by "
          f"`verify_sample.py --all`, {ck['full re-run']['status']}): every one of the {E(C)} slices re-run with "
          "nothing deleted and checked the same way, each check bound to its slice's copy (the checker's own record "
          "and a digest of the files checked), every prefix the prefix of a whole check: "
          f"`{E(g('va.verdict') or 'not run yet')}`.",
          f"- **The tree control at full strength** (CONTRACT Section 4.1; `u23-control22`, judged by "
          f"`target_check.py`, {ck['tree control']['status']}): the whole {E(CONSTANTS['control22_cell'][0])} tree "
          "through the final pipeline, with no u-bar override below it and root minimum degree "
          f"{E(CONSTANTS['control22_root_k'][0])} (Lemma D4), must keep nothing at its top, consistently with the "
          f"u(22) result: `{E(g('c22.verdict') or 'not run yet')}`.",
          f"- **The calibration** (CONTRACT Section 4.3; `u23-calib2157`, judged by `target_check.py`, "
          f"{ck['calibration']['status']}): the whole {E(CONSTANTS['calib_cell'][0])} tree through the final pipeline, "
          f"root minimum degree {E(CONSTANTS['calib_root_k'][0])} (Schade's bound), must keep all "
          f"{E(CONSTANTS['calib_known'][0])} of Alexeev, Mixon and Parshall's extremal graphs (`engel-21-57.g6`): "
          f"`{E(g('cal.verdict') or 'not run yet')}`.",
          "- **The aggregate's self-check**, each identity recomputed by a second path: "
          + (E("not run") if sc is None else f"{E(sum(1 for c in sc if c['ok']))} of {E(len(sc))} hold ("
             + ", ".join(f"{E(c['check'])} {E('holds' if c['ok'] else 'BROKEN')}" for c in sc) + ")")
          + "; its red control, `--perturb`, is in Section 8 (this generator does not run it).",
          "- **One software and data hash each in every copy**: "
          f"{E(g('prov.software_all_same'))} (" + ", ".join(f"{E(n)} `{E('/'.join(h))}`" for n, h in sw.items())
          + f"; {E(g('prov.verify_manifests'))} verify manifests read).",
          "- **The reach windows against CONTRACT Section 2**: "
          + ", ".join(f"level {E(n, 'd')}: the CONTRACT {E(f'{lo}..{hi}')}, the run {E(f'{a}..{b}')}"
                      for n, (lo, hi), (a, b) in adm_rows) + ".",
          f"- **G5, the cross-model soundness read**: `{E(g('g5.verdict'))}`, the round-9 read "
          f"`{E(G5_ROUND9)}` on branch `{E(G5_BRANCH)}` (`{E(g('g5.commit')[:10])}`)"
          + (f"; the latest read since, `{E(g('g5.latest_verdict') or 'no verdict line')}` "
             f"(`{E(g('g5.latest_path'))}`)" if g("g5.latest_round") is not None else "") + ".", ""]
    # 6
    gates = g("contract.gates")
    st = {"G0": "not re-derived by this generator. Inputs: one software and data hash each in every copy: "
                f"{E(g('prov.software_all_same'))} (Section 5). The literature: the last record is "
                "`research/unit-distance-23/LITERATURE-CHECK-2026-09-28.md`, made by the session at the human's "
                "request; to be redone on the day anything is public.",
          "G1": "not re-derived by this generator: `research/unit-distance-22/enum/REPORT-398.md` and "
                "`REPORT-398-SPEED.md`.",
          "G2": (E("met") if ck["known graphs"]["ok"] and ck["tree control"]["ok"]
                 and ck["calibration"]["ok"] else E("open"))
                + f": re-derived here (Section 5): CONTRACT Section 4.3 at level {E(qc[0])}, "
                  f"{ck['known graphs']['status']}; Section 4.1, the whole {E(CONSTANTS['control22_cell'][0])} tree, "
                  f"{ck['tree control']['status']}; Section 4.3's {E(CONSTANTS['calib_cell'][0])} calibration, "
                  f"{ck['calibration']['status']}. Sections 4.2 and 4.4: "
                  "`research/unit-distance-22/enum/REPORT-398.md` and G4 below; the earlier pilot and control records "
                  "are in `LABNOTES.md` and `JOBS.md` (`u23-pilot`, `u23-control`, `u23-pilot2`, `u23-pilot3`).",
          "G3": (E("met") if ck["coverage"]["ok"] and ck["audit"]["ok"] and ck["top level"]["ok"] and
                 ck["blind verifier"]["ok"] and ck["snapshot"]["ok"] else E("open"))
                + f": coverage {ck['coverage']['status']}, the audit {ck['audit']['status']}, the top level "
                  f"{ck['top level']['status']}, the blind verifier {ck['blind verifier']['status']}, "
                  f"{ck['snapshot']['status']}.",
          "G4": (E("met") if ck["G4"]["ok"] and ck["coverage"]["ok"] else E("open")) + f": {ck['G4']['detail']}"
                + ("" if ck["coverage"]["ok"] else f"; the slices still missing have no replay yet") + ".",
          "G5": (E("met") if (g("g5.latest_round") is None and g("g5.verdict") == "G5: CLOSED")
                 or (g("g5.latest_verdict") or "").endswith(": CLOSED") else E("open"))
                + f": `{E(g('g5.verdict'))}` (`{E(G5_ROUND9)}`, branch `{E(G5_BRANCH)}`, `{E(g('g5.commit')[:10])}`)"
                + (f"; since the fleet, `{E(g('g5.latest_verdict') or 'no verdict line')}` (`{E(g('g5.latest_path'))}`"
                   + (", answered in writing" if g("g5.latest_answered") else ", not yet answered")
                   + ("" if (g("g5.latest_verdict") or "").endswith(": CLOSED") else "; the next read pending") + ")"
                   if g("g5.latest_round") is not None else "") + "; "
                f"point 6 by the human's choice, the certification sample: {ck['certification sample']['status']}, "
                f"{E(g('vs.verified'))} of {E(g('vs.planned'))} slices verified (below); beyond it, the full re-run of "
                f"every slice: {ck['full re-run']['status']}, {E(g('va.verified') or 0)} of {E(C)} verified.",
          "G6": (E("met") + " by this generator: " + lint_note) if lint_note else E("pending the lint")}
    o += ["## 6. Gates", "", *table(["gate", "requirement (CONTRACT Section 6)", "status here"],
                                    [[k, E(gates[k]), st[k]] for k in sorted(gates)], ["l", "l", "l"]), "",
          "GPT's point 6 (item 6 of "
          f"`{E(G5_CLOSURE)}`: \"{E(g('g5.item6'))}\"): once intermediate files are deleted, no summary-level audit "
          "can re-prove the certificate-to-keep-file relation, so correctness rests on the workers' in-process "
          "checks, `prune.py`'s `verify_outputs` at production and the G4 replay. Of the three options put to the "
          "human (a re-run of the restarted slices plus a "
          f"~{E(V['constants']['point6_sample_percent']['value'])}% random sample with nothing deleted, each run "
          "directory checked by the full `verify-chain.py --check`; keeping the files until an on-worker full audit; "
          "a full second run) the human chose the first (`JOBS.md`, entry `u23-verify`). Its result, "
          f"`verify_sample.py`: `{E(g('vs.verdict') or 'not run')}`. Verified: the restarted slices "
          f"{E(ranges(g('vs.verified_restarted') or []) or 'none')} ({E(len(g('vs.verified_restarted') or []))} of "
          f"{E(g('vs.restarted'))}), and {E(len(g('vs.verified_random') or []))} of the {E(g('vs.random'))} random "
          f"ones (seed {E(g('vs.seed'), 'd')}): each re-run by the fleet's unchanged runbook with nothing deleted, "
          f"its run directory checked by the G5-closed `verify-chain.py --check` ({E(g('vs.whole'))} of "
          f"{E(g('vs.workers'))} workers' first slices whole; every other slice from level {E(g('vs.from_level'))}, its "
          "prefix compared byte for byte with its worker's first slice, or, for a first slice checked from that level "
          "on a machine too small for the whole check, by hash with the fleet's copies), every inspected "
          "pruned cell's certificates replayed, and its result files identical to the fleet's copy."
          + (f" Not verified, nothing having failed: {E(ranges(g('vs.missing_only')))} (the workers "
             f"{E(', '.join(g('vs.not_verified_workers') or []))}: refused by the cloud's permission classifier, or "
             "still running; `JOBS.md`, entry `u23-verify`). Whether that sample is enough is the human's call."
             if g("vs.missing_only") else ""), ""]
    # 7
    if state == "COMPLETE":
        o += ["## 7. What is claimed, and what is not", "",
              f"- Claimed, as a DRAFT for the human: the enumeration of Section 3 {NO_GRAPH.format(cell=cell)} "
              "(Sections 4 and 5).",
              f"- If the gates of Section 6 are all green, u(23) = {E(g('contract.lower'))}; the CONTRACT allows that "
              "claim only as Section 1 quotes.",
              f"- Not claimed: u(23) = {E(g('contract.lower'))} as an established result. G0 and G1 are not "
              f"re-derived here; G2's whole-tree controls are {ck['tree control']['status']} and "
              f"{ck['calibration']['status']}, the full re-run is {ck['full re-run']['status']}"
              + ("." if ck["full re-run"]["ok"] else
                 "; and whether the certification sample of Section 6 suffices, while the full re-run is open, is "
                 "the human's decision."), ]
    else:
        o += ["## 7. What is claimed, and what is not", "",
              f"- Claimed: nothing about u(23). The enumeration's state is {E(state)}; the headline lists what is "
              "open.",
              f"- What the outputs show so far, and no more: over {scope}, the fleet's filter-only prune kept "
              f"{E(g('top.kept'))} graph(s) at {cell}, and `top_level_check.py` says `{E(g('tlc.verdict'))}`.",
              f"- Not claimed: anything about the slices not yet counted, or about a {cell} graph in them."]
    o += ["- Not claimed: that the summary audit re-proves the certificate-to-keep relation of the deleted "
          "intermediate files (it reads no level, keep, parent or certificate file); that relation rests on the "
          f"workers' in-process checks, and the certification sample re-proved it on {E(g('vs.verified'))} of the "
          f"{E(C)} slices (Section 6)"
          + (f", the full re-run on {E(g('va.verified'))} of them (Section 5)." if ck["full re-run"]["ok"] else "."),
          f"- Not claimed: anything about u(n) for n > {E(tn)}.",
          "- Rests on: the dependencies in Section 1.", ""]
    # 8
    s = V["sources"]
    fc = g("cov.first_complete")
    o += ["## 8. How to check it", "",
          "ROOT is the extraction of every fleet worker's pushed results, VROOT the verification workers'; G5DIR a "
          "checkout of branch "
          f"`{E(G5_BRANCH)}`, where the audit ran (merged into this branch once the fleet and the certification "
          "sample were done, so a checkout of this branch serves as well).", "", "```",
          "python3 research/unit-distance-23/tools/fleet_status.py --fetch --workdir ROOT",
          "python3 research/unit-distance-23/tools/aggregate_fleet.py --root ROOT --self-check --out aggregate.json",
          f"python3 research/unit-distance-23/tools/aggregate_fleet.py --root ROOT --self-check --perturb {E(fc, 'd')}"
          "   # must fail",
          "python3 research/unit-distance-23/tools/top_level_check.py ROOT --self-test",
          "python3 research/unit-distance-23/tools/level22_control.py ROOT --self-test",
          "python3 research/unit-distance-23/tools/verify_sample.py --fetch --verify-root VROOT --root ROOT --self-test",
          f"git worktree add G5DIR origin/{E(G5_BRANCH)}",
          f"python3 G5DIR/{E(AUDIT_TOOL)} --root ROOT",
          "python3 research/unit-distance-23/tools/write_result.py --root ROOT --audit-worktree G5DIR",
          "python3 research/unit-distance-23/tools/write_result.py --self-test", "```", "",
          "What this draft ran (the outputs' sha256 are in `result-values.json`, under `sources`):", ""]
    for name, label in (("aggregate", "aggregate"), ("top_level_check", "top level"),
                        ("blind_check", "blind verifier"), ("level22_control", "known graphs"),
                        ("verify_sample", "certification sample"), ("audit", "coverage audit")):
        o.append(f"- {label}: `{E(s[name].get('command'))}` in `{E(s[name].get('cwd', '-'))}` (exit "
                 f"{E(s[name].get('exit'))}; output sha256 `{E(s[name].get('sha256', '?')[:16])}`)")
    o += ["", f"The fleet root's fingerprint before and after: `{E(g('snap.before')['sha256'][:16])}` and "
          f"`{E(g('snap.after')['sha256'][:16])}` over {E(g('snap.after')['files'])} files."
          if g("snap.before") and g("snap.after") else "", ""]
    return "\n".join(o)


# ------------------------------------------------------------------------------------------------------------- lint

LABELS = re.compile(r"\b(?:Sections?|amendments?|rounds?|items?|points?|Theorem|Lemmas?)\s+\d+(?:\.\d+)*"
                    r"(?:(?:\s*,\s*|\s+(?:and|to|or)\s+)\d+(?:\.\d+)*)*|\bu(?:-bar)?\(\d+\)|\barXiv:\d{4}\.\d{4,5}"
                    r"|^#+\s+\d+(?:\.\d+)*\.?", re.M)
NUMERAL = re.compile(r"(?<![\w\-./\\])\d[\d,]*(?:\.\d+)?(?![\w\-]|\.\d)")
STATUS = re.compile(r"\b(?:PASS(?:ED)?|OK|FAIL(?:ED|S)?|ACCEPT(?:ED|S)?|REJECT(?:ED|S)?|CLOSED|UNRESOLVED|COMPLETE|"
                    r"INCOMPLETE|EMPTY|MISMATCH|PARTIAL)\b")
ASSERTS = re.compile(r"\b(?:is|are|was|were)\s+(?:now\s+)?(?:complete|incomplete|closed|decided|green|met)\b", re.I)
CLAIM = re.compile(r"u\(23\)\s*=\s*\d+")
CONDITION = re.compile(r"\b(?:if|only when|only with|never|not claimed|then)\b", re.I)
NO_GRAPH = "finds no {cell} unit-distance graph"   # the statement only a COMPLETE headline may carry


def lint(marked: str) -> list:
    """G6: the fixed text (everything outside the marked values) holds no numeral but labels, no status word and no
    assertion of a gate's state; every u(23) = n, values included, sits in a sentence with a condition."""
    fixed = re.sub(re.escape(MARK_L) + ".*?" + re.escape(MARK_R), " ", marked, flags=re.S)
    out = []
    for i, line in enumerate(LABELS.sub(" ", fixed).splitlines(), 1):
        for m in NUMERAL.finditer(line):
            out.append(f"line {i}: numeral {m.group(0)!r} in the fixed text: {line.strip()[:120]}")
    prose = re.sub(r"```.*?```", " ", fixed, flags=re.S)
    prose = re.sub(r"`[^`\n]*`", " ", prose)
    for i, line in enumerate(prose.splitlines(), 1):
        for rx, what in ((STATUS, "status word"), (ASSERTS, "assertion of a state")):
            for m in rx.finditer(line):
                out.append(f"line {i}: {what} {m.group(0)!r} in the fixed text: {line.strip()[:120]}")
    text = strip(marked)
    for m in CLAIM.finditer(text):   # the sentence around it: from the last ". " or line break to the next
        a = max(text.rfind(". ", 0, m.start()), text.rfind("\n", 0, m.start()))
        b = min([p for p in (text.find(". ", m.end()), text.find("\n", m.end())) if p >= 0] or [len(text)])
        if not CONDITION.search(text[a + 1: b]):
            out.append(f"{m.group(0)!r} outside a condition: {text[a + 1: b].strip()[:160]}")
    return out


def lint_note(marked: str) -> str:
    return (f"the lint sees no numeral, status word or state assertion in the fixed text around the "
            f"{E(marked.count(MARK_L))} values, and each of the {E(len(CLAIM.findall(strip(marked))))} occurrences of "
            "u(23) = n sits in a conditional sentence")


INT_KEYED = ("top.slices_kept", "top.kept_graphs", "rec.red_control", "rec.prune", "run.reach_levels",
             "contract.reach_admits")


def load_values(p: Path) -> dict:
    """A values file as extract() made it (JSON turns the integer keys of some maps into strings)."""
    V = json.loads(p.read_text())
    for k in INT_KEYED:
        if isinstance(V["v"].get(k, {}).get("value"), dict):
            V["v"][k]["value"] = {int(i): val for i, val in V["v"][k]["value"].items()}
    return V


def build(V: dict) -> tuple:
    D = decide(V)
    first = render(V, D, None)
    problems = lint(first)
    if problems:
        return D, None, problems
    doc = render(V, D, lint_note(first))
    return D, doc, lint(doc)


# -------------------------------------------------------------------------------------------------------- what-ifs

def what_if(V: dict, kind: str) -> dict:
    """An edited copy of the values, for the self-test: 'complete' (the fleet finished as it should), 'unrefuted'
    (complete, and one more slice kept a top-level graph with no record), 'one-missing' (complete but one slice),
    'control-missing' (complete, but the known-graph control finds one required graph not kept), 'sample-failed'
    (complete, but one sampled slice's re-run differs from the fleet's copy), 'sample-partial' (complete, some sampled
    slices not verified and none failed: INCOMPLETE), 'sample-miscounted' (a per-slice line the parser cannot read),
    'sample-mostly-missing' (G5 round 10's reproduction: 1 of 63 verified, the rest missing), 'sample-no-exit' (an OK
    verdict line without its run's exit status), 'blind-rejects' (the blind second verifier rejects the top level),
    'controls-open' (the whole-tree controls and the full re-run not run: the gates open, the state unchanged),
    'control22-keeps' and 'calib-loses' (a whole-tree control fails with every slice in), 'rerun-fails' (a slice of
    the full re-run disagrees), 'rerun-partial' (the full re-run under way)."""
    W = copy.deepcopy(V)
    x = W["v"]
    s = lambda k, val: x[k].__setitem__("value", val)
    g = lambda k: x[k]["value"]
    C = g("plan.slices")
    if kind in ("complete", "unrefuted", "one-missing", "control-missing", "sample-failed", "sample-partial",
                "sample-miscounted", "sample-mostly-missing", "sample-no-exit", "blind-rejects", "blind-other-graph",
                "blind-other-certs",
                "controls-open",
                "control22-keeps", "calib-loses", "rerun-fails", "rerun-partial", "controls-running",
                "control22-degree6", "calib-four-known", "control22-slice-failing", "control22-selftest-broken",
                "rerun-ok-with-problem", "control22-global-problem", "control22-interrupted",
                "control22-audit-contradiction", "g4-scope-fail", "rerun-judge-crashed", "rerun-ok-inconsistent",
                "rerun-ok-not-verified", "rerun-ok-zero-tasks", "rerun-malformed", "control22-malformed",
                "control22-ok-exit1", "rerun-ok-no-rows", "sample-duplicated-rows", "rerun-fail-unexplained",
                "control22-fail-unexplained", "calib-fail-unexplained", "sample-chain-fail-row", "sample-no-whole",
                "rerun-fail-all-rows-ok", "g4-scope-one-copy", "control22-other-target", "sample-other-copy",
                "sample-one-worker", "g4-scope-other-copies", "sample-other-seed", "calib-kept-below-found",
                "g4-scope-other-root", "control22-missing-line", "control22-other-checker", "sample-other-level"):
        s("cov.complete", C); s("cov.missing", 0); s("cov.missing_slices", []); s("cov.missing_ranges", "")
        s("cov.missing_by_owner", {}); s("cov.every_copy_resumed", []); s("agg.final", True)
        s("agg.problems", []); s("g4.verdicts", {"PASS": C}); s("g4.not_pass_or_empty", {})
        s("g4.other_copies_not_pass_or_empty", [])
        s("audit.slice_indices", C); s("audit.missing_slices", 0); s("audit.problems", 0); s("audit.unresolved", 0)
        s("audit.problem_lines", []); s("audit.unresolved_lines", []); s("audit.unresolved_slices", [])
        s("audit.word", "OK"); s("audit.exit", 3); s("audit.exit_expected", 3); s("audit.runs", g("cov.copies_read"))
        s("audit.g4_results", {"PASS": g("cov.copies_read")})
        s("audit.coverage_line", "COVERAGE (summary only) OK: every run's required cells are listed and recorded with "
                                 "the parents L4 allows, every count is consistent, and every fleet's slices are all "
                                 "present with their shares")
        s("audit.chain_line", "CHAIN PARTIAL (summary only: no level, keep, parent or certificate file was read)")
        s("snap.after", g("snap.before"))
        rows = [dict(r, slices=r["slices"] or [f"s{i}of{C}"]) for i, r in enumerate(g("l22.rows"))]
        s("l22.rows", rows); s("l22.found", len(rows)); s("l22.required", len(rows)); s("l22.required_head", len(rows))
        s("l22.verdict", f"LEVEL-22 CONTROL OK: {len(rows)} of {len(rows)} required graphs found"); s("l22.word", "OK")
        s("l22.problems", []); s("l22.exit", 0); s("l22.dup", 0)
        pl = g("vs.planned") or 63
        s("vs.verdict", f"VERIFY-SAMPLE OK: {pl} of {pl} planned slices verified"); s("vs.word", "OK")
        tcs = sha256(HERE.parent / "target_check.py")
        params = {"c22": "target (22,61), root minimum degree 5, u-bar override refused, top level empty, known none; "
                         f"checker target_check.py sha256 {tcs}",
                  "cal": "target (21,57), root minimum degree 3, u-bar override the fleet 22=60 only, top level holding "
                         f"the known graphs, known engel-21-57.g6 sha256 {ENGEL_2157_SHA256} (5 graphs); checker "
                         f"target_check.py sha256 {tcs}"}
        for key, cell, extra in (("c22", "(22,61)", ""), ("cal", "(21,57)", "; known: 5 of 5 kept")):
            s(f"{key}.parameters", params[key]); s(f"{key}.failing", 0); s(f"{key}.missing", 0)
            s(f"{key}.word", "OK"); s(f"{key}.exit", 0); s(f"{key}.complete", C); s(f"{key}.g4_pass", C)
            s(f"{key}.kept", 0 if key == "c22" else 7); s(f"{key}.selftest_ok", True); s(f"{key}.problems", [])
            s(f"{key}.selftest", "SELF-TEST passed: 5 of 5 red controls caught")
            s(f"{key}.known", None if key == "c22" else 5); s(f"{key}.found", None if key == "c22" else 5)
            s(f"{key}.verdict", f"TARGET-CHECK OK: {cell}: {C} of {C} slices complete, G4 PASS {C}; 0 failing, 0 "
                                f"missing; kept at {cell}: {0 if key == 'c22' else 7} distinct graph(s){extra}")
        s("c22.audit", "COVERAGE (summary only) OK: every run's required cells are listed"); s("cal.audit", g("c22.audit"))
        s("g4.scope_verdict", "G4-SCOPE OK: 101 of 101 full-mode replays and 1854 of 1854 slice-mode replays in their "
                              "mode's scope; 0 problem(s)"); s("g4.scope_exit", 0)
        s("va.word", "OK"); s("va.exit", 0); s("va.verified", C); s("va.planned", C); s("va.failed_problems", [])
        s("va.missing", 0); s("va.tasks", 48); s("va.whole", 48); s("va.problems_count", 0); s("va.problem_lines", 0)
        s("va.lean", 0); s("va.not_verified", 0); s("va.expected_tasks", 48)
        full = lambda n, whole, skip: {"exact": True, "dup": [], "absent": 0, "extra": 0, "wrong": [], "ok_rows": n,
                                       "not_rows": 0, "whole_rows": whole, "whole_wrong": [], "stray": [],
                                       "stray_count": 0, "unexplained": [], "bad_ok": [], "bad_ok_count": 0,
                                       "lean_rows": 0, "skip_rows": skip, "skip_wrong": [], "wrong_copy": [],
                                       "first_not_whole": [], "planned_workers": 48 if whole == 48 else 10}
        s("va.accounted", full(C, 48, 0)); s("vs.accounted", full(pl, 9, 1)); s("vs.whole", 9); s("vs.workers", 10)
        s("c22.cell", [22, 61]); s("cal.cell", [21, 57]); s("g4.scope_copies", g("g4.agg_copies"))
        s("g4.root_labels", g("g4.agg_labels")); s("vs.from_level", 13)
        s("vs.accounted", dict(g("vs.accounted"), plan_seed=g("vs.seed"), plan_restarted=g("vs.restarted"),
                               plan_random=g("vs.random")))
        s("c22.missing_listed", 0); s("cal.missing_listed", 0); s("c22.slices", C); s("cal.slices", C)
        s("va.verdict", f"VERIFY-ALL OK: {C} of {C} slices re-run and verified (48 tasks; 48 first slices checked "
                        "whole, the rest from level 13 with the prefix compared; every prefix the prefix of a whole "
                        "check), 0 problem(s)")
        kt = g("top.kept")
        s("blind.word", "OK"); s("blind.exit", 0); s("blind.problems", []); s("blind.accepted", kt)
        s("blind.total", kt); s("blind.tried", 7 * kt); s("blind.rejected", 7 * kt)
        s("blind.verdict", f"BLIND-CHECK OK: {kt} of {kt} top-level certificates accepted by the blind verifier")
        s("blind.accepted_graphs", sorted([int(sl), x, (g("top.records_certs_sha256") or {}).get(str(sl))]
                                          for sl, gs in g("top.kept_graphs").items() for x in gs))
        s("vs.verified", pl); s("vs.planned", pl); s("vs.problem_count", 0); s("vs.failed_problems", [])
        s("vs.not_verified", []); s("vs.missing_only", []); s("vs.not_verified_workers", []); s("vs.exit", 0)
        s("vs.verified_restarted", list(range(g("vs.restarted") or 15)))
        s("vs.verified_random", list(range(100, 100 + (g("vs.random") or 48))))
    if kind == "sample-failed":
        s("vs.failed_problems", ["s14 (v02, random): differs from the fleet's copy (f15): a cell with one child more"])
        s("vs.not_verified", [14]); s("vs.verified", (g("vs.planned") or 63) - 1); s("vs.word", "FAIL")
        s("vs.verified_random", g("vs.verified_random")[1:])   # the lines agree with the verdict
        s("vs.verdict", "VERIFY-SAMPLE FAIL: one slice not verified"); s("vs.exit", 1); s("vs.problem_count", 1)
        s("vs.accounted", dict(g("vs.accounted"), ok_rows=(g("vs.planned") or 63) - 1, not_rows=1, unexplained=[14]))
    if kind == "sample-partial":
        s("vs.not_verified", [113, 586, 606]); s("vs.missing_only", [113, 586, 606]); s("vs.not_verified_workers", ["v04"])
        s("vs.verified_restarted", g("vs.verified_restarted")[1:]); s("vs.verified_random", g("vs.verified_random")[2:])
        s("vs.verified", (g("vs.planned") or 63) - 3); s("vs.word", "FAIL"); s("vs.exit", 1); s("vs.problem_count", 6)
        s("vs.verdict", "VERIFY-SAMPLE FAIL: three slices have no check output or copy")
        s("vs.accounted", dict(g("vs.accounted"), ok_rows=(g("vs.planned") or 63) - 3, not_rows=3))
    if kind == "control-missing":
        rows = [dict(r) for r in g("l22.rows")]
        rows[-1]["slices"] = []
        s("l22.rows", rows); s("l22.found", len(rows) - 1)
        s("l22.verdict", f"LEVEL-22 CONTROL FAIL: {len(rows) - 1} of {len(rows)} required graphs found")
        s("l22.word", "FAIL"); s("l22.exit", 1)
        s("l22.problems", [f"Engel graph {rows[-1]['index']} (minimum degree {rows[-1]['min_degree']}) is missing "
                           "from level 22"])
    if kind == "sample-miscounted":   # one per-slice line the parser could not read, while the verdict says all
        s("vs.verified_random", g("vs.verified_random")[1:])
        s("vs.accounted", dict(g("vs.accounted"), exact=False, absent=1, ok_rows=(g("vs.planned") or 63) - 1))
    if kind == "sample-mostly-missing":   # G5 round 10's reproduction: only v01's s276 available, the judge FAIL 1/63
        pl = g("vs.planned") or 63
        miss = list(range(200, 200 + pl - 1))
        s("vs.not_verified", miss); s("vs.missing_only", miss); s("vs.not_verified_workers", ["v02", "v03"])
        s("vs.verified_restarted", []); s("vs.verified_random", [276]); s("vs.verified", 1); s("vs.word", "FAIL")
        s("vs.exit", 1); s("vs.problem_count", 2 * (pl - 1))
        s("vs.verdict", f"VERIFY-SAMPLE FAIL: 1 of {pl} planned slices verified")
        s("vs.accounted", dict(g("vs.accounted"), ok_rows=1, not_rows=pl - 1, whole_rows=1))
    if kind == "sample-no-exit":   # an OK verdict line from a run whose exit status is unknown or not 0
        s("vs.exit", None)
    if kind == "controls-open":   # the whole-tree controls and the full re-run not run yet
        for key in ("c22", "cal"):
            for k in ("word", "exit", "complete", "g4_pass", "kept", "known", "found", "verdict", "selftest",
                      "failing", "missing", "parameters"):
                s(f"{key}.{k}", None)
            s(f"{key}.selftest_ok", False)
    if kind == "controls-running":   # under way: slices missing, none failing, nothing kept (no PROBLEM line)
        s("c22.word", "FAIL"); s("c22.exit", 1); s("c22.complete", 1448); s("c22.g4_pass", 1448); s("c22.missing", 472)
        s("c22.problems", [])
        s("c22.verdict", f"TARGET-CHECK FAIL: (22,61): 1448 of {C} slices complete, G4 PASS 1448; 0 failing, 472 "
                         "missing; kept at (22,61): 0 distinct graph(s)")
        s("c22.missing_listed", 472)
    if kind == "control22-degree6":   # G5 round 12: a passing control run with another root minimum degree
        s("c22.parameters", g("c22.parameters").replace("root minimum degree 5", "root minimum degree 6"))
    if kind == "calib-four-known":   # G5 round 12: a calibration checked against four known graphs, 4 of 4 kept
        s("cal.known", 4); s("cal.found", 4)
        s("cal.parameters", g("cal.parameters").replace("(5 graphs)", "(4 graphs)").replace(ENGEL_2157_SHA256, "0" * 64))
    if kind == "control22-slice-failing":   # G5 round 12: one slice's G4 replay FAILED, the rest complete
        s("c22.word", "FAIL"); s("c22.exit", 1); s("c22.complete", C - 1); s("c22.g4_pass", C - 1); s("c22.failing", 1)
        s("c22.problems", ["s7 (k08): FAILING, its G4 replay FAILED"])
    if kind == "control22-global-problem":   # G5 round 13: complete counts beside a global problem line
        s("c22.word", "FAIL"); s("c22.exit", 1)
        s("c22.problems", ["no counted copy has a full-mode G4 replay, so no replay here showed its red controls red"])
    if kind == "control22-interrupted":   # G5 round 14: a problem recorded, the run cut off before its verdict line
        s("c22.verdict", None); s("c22.word", None); s("c22.exit", 1)
        s("c22.problems", ["s7: audit: s7of1920: G4 replay says 'PASS' but its evidence gives FAIL: stage files that do "
                           "not re-derive"])
    if kind == "control22-audit-contradiction":   # G5 round 14: complete counts, the audit's own line not OK
        s("c22.audit", "COVERAGE (summary only) FAIL (1 problems, 0 unresolved)")
    if kind == "g4-scope-fail":   # a fleet replay outside its mode's scope
        s("g4.scope_verdict", "G4-SCOPE FAIL: 100 of 101 full-mode replays and 1854 of 1854 slice-mode replays in their "
                              "mode's scope; 1 problem(s)"); s("g4.scope_exit", 1)
    if kind == "control22-selftest-broken":   # the checker's own red controls did not all go red
        s("c22.selftest_ok", False); s("c22.selftest", "SELF-TEST FAILED: 9 of 10 red controls caught")
    if kind == "rerun-ok-with-problem":   # G5 round 12: an OK verdict line beside a recorded failure
        s("va.failed_problems", ["s7 (c101, all): differs from the fleet's copy (f08): a cell with one child more"])
        s("va.word", None); s("va.exit", None); s("va.verified", None); s("va.planned", None); s("va.verdict", None)
        s("va.accounted", dict(g("va.accounted"), ok_rows=C - 1, not_rows=1, unexplained=[7]))
    if kind == "control22-keeps":   # every (22,61) slice in, and one graph kept at the top: u(22) = 60 contradicted
        s("c22.word", "FAIL"); s("c22.exit", 1); s("c22.kept", 1)
        s("c22.verdict", f"TARGET-CHECK FAIL: (22,61): {C} of {C} slices complete, G4 PASS {C}; 0 failing, 0 missing; "
                         "kept at (22,61): 1 distinct graph(s)")
    if kind == "calib-loses":   # every (21,57) slice in, and one of AMP's graphs not kept
        s("cal.word", "FAIL"); s("cal.exit", 1); s("cal.found", 4)
        s("cal.verdict", f"TARGET-CHECK FAIL: (21,57): {C} of {C} slices complete, G4 PASS {C}; 0 failing, 0 missing; "
                         "kept at (21,57): 6 distinct graph(s); known: 4 of 5 kept")
    if kind == "rerun-fails":   # one slice's full re-run disagrees with the fleet
        s("va.word", "FAIL"); s("va.exit", 1); s("va.verified", C - 1)
        s("va.failed_problems", ["s7 (c101, all): differs from the fleet's copy (f08): a cell with one child more"])
        s("va.problems_count", 1); s("va.problem_lines", 1)
        s("va.verdict", f"VERIFY-ALL FAIL: {C - 1} of {C} slices re-run and verified (48 tasks; 48 first slices "
                        "checked whole), 1 problem(s)")
        s("va.accounted", dict(g("va.accounted"), ok_rows=C - 1, not_rows=1, unexplained=[7]))
    if kind == "rerun-partial":   # the full re-run under way: some slices not yet back, none failed
        s("va.word", "FAIL"); s("va.exit", 1); s("va.verified", 100); s("va.missing", 2 * (C - 100))
        s("va.whole", 20); s("va.problems_count", 2 * (C - 100)); s("va.problem_lines", 2 * (C - 100))
        s("va.verdict", f"VERIFY-ALL FAIL: 100 of {C} slices re-run and verified (48 tasks; 20 first slices checked "
                        f"whole), {2 * (C - 100)} problem(s)")
        s("va.accounted", dict(g("va.accounted"), ok_rows=100, not_rows=C - 100, whole_rows=20))
    if kind == "rerun-judge-crashed":   # G5 round 17, finding 6: the judge ran and printed nothing
        s("va.word", None); s("va.exit", 1); s("va.verified", None); s("va.planned", None); s("va.verdict", None)
        s("va.problems_count", None); s("va.problem_lines", 0); s("va.whole", None); s("va.tasks", None)
        s("va.accounted", dict(g("va.accounted"), exact=False, absent=C, ok_rows=0, whole_rows=0))
    if kind == "rerun-ok-not-verified":   # G5 round 18: an OK total beside a slice line that says NOT verified
        s("va.not_verified", 1)
        s("va.accounted", dict(g("va.accounted"), ok_rows=C - 1, not_rows=1, unexplained=[955]))
    if kind == "g4-scope-other-root":   # G5 round 24, finding 1: a root of the right size but other copies
        s("g4.root_labels", [g("g4.agg_labels")[0], "0" * 64])
    if kind == "control22-missing-line":   # finding 5: an OK control report with a MISSING line of 1
        s("c22.missing_listed", 1)
    if kind == "control22-other-checker":   # finding 5: an OK control report naming another checker
        s("c22.parameters", g("c22.parameters").rsplit("sha256 ", 1)[0] + "sha256 " + "0" * 64)
    if kind == "sample-other-level":   # finding 5: the footer checked from level 14, the rows from 13
        s("vs.from_level", 14)
    if kind == "sample-other-seed":   # G5 round 23, finding 7: the footer's seed not the plan's
        s("vs.seed", 0)
    if kind == "calib-kept-below-found":   # finding 7: kept 0 distinct graphs, yet 5 of 5 known found
        s("cal.kept", 0)
    if kind == "g4-scope-other-copies":   # G5 round 22, finding 7: 1,955 scope copies, not the aggregate's
        s("g4.scope_copies", [g("g4.agg_copies")[0], "0" * 64])
    if kind == "g4-scope-one-copy":   # G5 round 21, finding 6: an OK scope report over one copy
        s("g4.scope_verdict", "G4-SCOPE OK: 1 of 1 full-mode replays and 0 of 0 slice-mode replays in their mode's "
                              "scope; 0 problem(s)")
    if kind == "control22-other-target":   # finding 7: the control's footer naming another target, 9,999 slices
        s("c22.cell", [21, 57]); s("c22.slices", 9999)
    if kind == "sample-other-copy":   # finding 7: a row naming a fleet copy that is not the aggregate's chosen one
        s("vs.accounted", dict(g("vs.accounted"), wrong_copy=[276]))
    if kind == "sample-one-worker":   # finding 7: one whole row, the other first slices plain, a footer of 1 of 1
        s("vs.accounted", dict(g("vs.accounted"), whole_rows=1, skip_rows=0, first_not_whole=[14]))
        s("vs.whole", 1); s("vs.workers", 1)
    if kind == "sample-chain-fail-row":   # G5 round 20, finding 6: a row saying CHAIN FAIL, counted verified before
        s("vs.accounted", dict(g("vs.accounted"), bad_ok=[276], bad_ok_count=1))
    if kind == "sample-no-whole":   # every whole check turned into one from level 13, under a footer of 0 of 10
        s("vs.accounted", dict(g("vs.accounted"), whole_rows=0)); s("vs.whole", 0)
    if kind == "rerun-fail-all-rows-ok":   # finding 7: a FAIL footer of 1920 of 1920, every row verified, no problem
        s("va.word", "FAIL"); s("va.exit", 1)
        s("va.verdict", f"VERIFY-ALL FAIL: {C} of {C} slices re-run and verified (48 tasks; 48 first slices checked "
                        "whole), 0 problem(s)")
    if kind == "rerun-ok-no-rows":   # G5 round 19, finding 6: a valid OK footer and no slice rows at all
        s("va.accounted", dict(g("va.accounted"), exact=False, absent=C, ok_rows=0, whole_rows=0))
    if kind == "sample-duplicated-rows":   # finding 6: 63 copies of one success row under the real footer
        s("vs.accounted", dict(g("vs.accounted"), exact=False, dup=[276], absent=(g("vs.planned") or 63) - 1,
                               ok_rows=1, whole_rows=0))
    if kind == "rerun-fail-unexplained":   # finding 7: a NOT verified row, no PROBLEM line, a FAIL footer of 1919
        s("va.word", "FAIL"); s("va.exit", 1); s("va.verified", C - 1); s("va.not_verified", 1)
        s("va.verdict", f"VERIFY-ALL FAIL: {C - 1} of {C} slices re-run and verified (48 tasks; 48 first slices checked "
                        "whole), 0 problem(s)")
        s("va.accounted", dict(g("va.accounted"), ok_rows=C - 1, not_rows=1, unexplained=[955]))
    if kind in ("control22-fail-unexplained", "calib-fail-unexplained"):   # finding 7: FAIL, 1919 complete, 0 missing
        key, cell = ("c22", "(22,61)") if kind.startswith("control22") else ("cal", "(21,57)")
        s(f"{key}.word", "FAIL"); s(f"{key}.exit", 1); s(f"{key}.complete", C - 1); s(f"{key}.g4_pass", C - 1)
        s(f"{key}.verdict", f"TARGET-CHECK FAIL: {cell}: {C - 1} of {C} slices complete, G4 PASS {C - 1}; 0 failing, "
                            f"0 missing; kept at {cell}: 0 distinct graph(s)")
    if kind == "rerun-ok-zero-tasks":   # an OK claiming zero tasks and zero whole checks
        s("va.tasks", 0); s("va.whole", 0)
        s("va.verdict", f"VERIFY-ALL OK: {C} of {C} slices re-run and verified (0 tasks; 0 first slices checked whole), "
                        "0 problem(s)")
    if kind == "rerun-malformed":   # a verdict the parser cannot read, exit 1, no PROBLEM line
        s("va.word", None); s("va.exit", 1); s("va.verified", None); s("va.planned", None); s("va.tasks", None)
        s("va.whole", None); s("va.verdict", "VERIFY-ALL OKAY: garbled), 0 problem(s)")
    if kind == "control22-malformed":   # a control verdict the parser cannot read
        s("c22.word", None); s("c22.exit", 1)
    if kind == "control22-ok-exit1":   # an OK control verdict with exit 1
        s("c22.exit", 1)
    if kind == "rerun-ok-inconsistent":   # an OK line with one problem and no whole check, exit 0, no PROBLEM line
        s("va.whole", 0); s("va.problems_count", 1)
        s("va.verdict", f"VERIFY-ALL OK: {C} of {C} slices re-run and verified (48 tasks; 0 first slices checked "
                        "whole), 1 problem(s)")
    if kind == "blind-other-graph":   # G5 round 11: an OK blind report, on a graph the fleet did not keep
        s("blind.accepted_graphs", [[50, "V" + "?" * 43, (g("top.records_certs_sha256") or {}).get("50")]])
    if kind == "blind-other-certs":   # the kept graph, with a certificate file other than its record's
        s("blind.accepted_graphs", [[int(sl), x, "0" * 64] for sl, gs in g("top.kept_graphs").items() for x in gs])
    if kind == "blind-rejects":   # the blind second verifier does not accept the top-level certificate
        s("blind.word", "FAIL"); s("blind.exit", 1); s("blind.accepted", 0)
        s("blind.problems", ["s50of1920/23-65.g6 graph 0: the blind verifier did not accept: REJECT root.A (exit 1)"])
        s("blind.verdict", "BLIND-CHECK FAIL: 0 of 1 top-level certificates accepted by the blind verifier")
    if kind == "unrefuted":
        new = next(i for i in range(C) if i not in g("top.slices_kept"))
        sk = dict(g("top.slices_kept")); sk[new] = 1; s("top.slices_kept", sk)
        kg = dict(g("top.kept_graphs")); kg[new] = ["(a graph with no record)"]; s("top.kept_graphs", kg)
        s("top.kept", g("top.kept") + 1); s("top.children", g("top.children") + 1)
        s("top.slices_with_children", sorted(set(g("top.slices_with_children")) | {new}))
        s("top.kept_without_record", [new])
        fail = f"TOP-LEVEL FAIL: {len(sk)} slice(s) with kept graphs, {len(sk)} cop(ies), 1 problem(s)"
        s("tlc.verdict", fail); s("tlc.word", "FAIL"); s("tlc.slices", len(sk)); s("tlc.exit", 1)
        s("tlc.problems", [f"s{new}: 1 kept graph(s) and no top-level record"])
        s("tlc_agg.verdict", fail); s("tlc_agg.exit", 1)
        s("agg.problems", [f"top_level_check.py: {fail} (exit 1)"]); s("agg.final", False)
        tc = dict(g("audit.target_cell")); tc.update(children=g("top.children"), kept=g("top.kept"),
                                                     slices_with_children=g("top.slices_with_children"))
        s("audit.target_cell", tc)
    if kind == "one-missing":
        s("cov.complete", C - 1); s("cov.missing", 1); s("cov.missing_slices", [C - 1])
        s("cov.missing_ranges", str(C - 1)); s("cov.missing_by_owner", {"f96": 1}); s("agg.final", False)
        s("g4.verdicts", {"PASS": C - 1}); s("audit.slice_indices", C - 1); s("audit.missing_slices", 1)
        s("audit.problems", 1); s("audit.word", "FAIL"); s("audit.exit", 1); s("audit.exit_expected", 1)
        s("audit.problem_lines", [f"fleet sliced {C} ways: 1 slices have no summary ([{C - 1}])"])
        s("audit.coverage_line", "COVERAGE (summary only) FAIL (1 problems, 0 unresolved)")
        s("audit.chain_line", "CHAIN FAIL (1 problems)")
    return W


def self_test(V: dict) -> int:
    res = []

    def expect(name, cond, detail=""):
        res.append((name, bool(cond), detail))

    # G5 round 19: the parsers themselves, on the saved reports (the what-ifs below set their results directly, so
    # these are what fail if account() or the MISSING count reads a report wrongly)
    I = RESULTS / "result-inputs"
    if (I / "verify-all.txt").is_file() and (I / "verify-sample.txt").is_file():
        pa, ps = vsm.plan_from_all(vsm.ALL_PLAN), vsm.plan_from_jobs(vsm.JOBS.read_text())
        va_lines = parse_verify_all((I / "verify-all.txt").read_text())["lines"]
        vs_lines = parse_vs((I / "verify-sample.txt").read_text())["lines"]
        rowx = re.compile(r"s(\d+) ([av]\d\d) (?:restarted|random|all): ")
        a0, s0 = account(va_lines, pa, False), account(vs_lines, ps, True)
        expect("account: the saved full re-run report's rows are exactly the plan's", a0["exact"] and not a0["stray_count"]
               and a0["ok_rows"] + a0["not_rows"] == len(sum(pa["workers"].values(), [])), str(a0)[:200])
        expect("account: the saved sample's rows are exactly its plan's, all verified", s0["exact"]
               and not s0["stray_count"] and not s0["not_rows"] and s0["ok_rows"] == len(sum(ps["workers"].values(), []))
               and not s0["bad_ok_count"] and s0["whole_rows"] + s0["skip_rows"] == len(ps["workers"]), str(s0)[:200])
        expect("account: every verified row of the saved full re-run report says what a verified row must",
               not a0["bad_ok_count"] and not a0["skip_rows"], str(a0)[:200])
        a1 = account([x for x in va_lines if not rowx.match(x) and not x.startswith("PROBLEM: ")], pa, False)
        expect("account: a footer with no rows is not the plan's rows (G5 round 19, finding 6)",
               not a1["exact"] and a1["ok_rows"] == 0 and a1["absent"] == len(sum(pa["workers"].values(), [])))
        r276 = next((x for x in vs_lines if x.startswith("s276 v01 random: ")), None)
        a2 = account([x for x in vs_lines if not rowx.match(x)] + [r276] * 63, ps, True) if r276 else {}
        expect("account: 63 copies of one sample row are not the plan's rows (finding 6)",
               r276 and not a2["exact"] and a2["dup"] == [276] and a2["ok_rows"] == 1)
        ok_row = next(x for x in va_lines if rowx.match(x) and "NOT verified" not in x)
        i, tag = int(rowx.match(ok_row).group(1)), rowx.match(ok_row).group(2)
        a3 = account([f"s{i} {tag} all: NOT verified" if x == ok_row else x for x in va_lines], pa, False)
        expect("account: a NOT verified row with no PROBLEM line is unexplained (finding 7)", i in a3["unexplained"])
        a4 = account(va_lines + [f"PROBLEM: s{i} ({tag}, all): no check output"], pa, False)
        expect("account: a PROBLEM line about a verified slice is stray", a4["stray_count"] == a0["stray_count"] + 1)
        a5 = account([x.replace(f" {tag} all: ", " a99 all: ", 1) if x == ok_row else x for x in va_lines], pa, False)
        expect("account: a row under another worker is not the plan's rows", not a5["exact"] and i in a5["wrong"])
        later = next(x for x in va_lines if rowx.match(x) and x.split(": ", 1)[1].startswith("from level"))
        a6 = account([x.replace(": from level", ": whole, from level", 1) if x == later else x for x in va_lines], pa,
                     False)
        expect("account: a row marked whole that is no worker's first slice", bool(a6["whole_wrong"]))
        # G5 round 20, finding 6: a row's whole text, not its first word
        wr276 = next((x for x in vs_lines if x.startswith("s276 v01 random: whole, CHAIN OK")), None)
        a7 = account([x.replace("whole, CHAIN OK, certificates replayed in 69", "whole, CHAIN FAIL (1 problems), "
                                "certificates replayed in 0") if x == wr276 else x for x in vs_lines], ps, True)
        expect("account: a whole row saying CHAIN FAIL and 0 certificates is not a verified row (G5 round 20)",
               wr276 is not None and 276 in a7["bad_ok"])
        a8 = account([x.replace(": whole, CHAIN OK, certificates replayed in 69", ": from level 13, CHAIN PARTIAL (levels "
                                "below 13 not inspected (--from-n 13)), certificates replayed in 61") for x in vs_lines],
                     ps, True)
        expect("account: every whole row turned into a check from level 13 leaves no whole row", a8["whole_rows"] == 0
               and s0["whole_rows"] >= 1)
        chosen0 = {int(k): v.get("chosen") for k, v in (json.loads((I / "aggregate.json").read_text()).get("slices")
                                                        or {}).items()} if (I / "aggregate.json").is_file() else {}
        s1 = account(vs_lines, ps, True, chosen0)
        expect("account: every saved sample row names the aggregate's chosen copy (G5 round 21)",
               chosen0 and not s1["wrong_copy"] and not s1["first_not_whole"], str(s1)[:200])
        a10 = account([x.replace(f"({chosen0.get(276)})", "(f99999-absent)") if wr276 and x == wr276 else x
                       for x in vs_lines], ps, True, chosen0)
        expect("account: a row naming a fleet copy that is not the chosen one", 276 in a10["wrong_copy"])
        f14 = next((x for x in vs_lines if x.startswith("s14 ") and ": whole, CHAIN OK" in x), None)
        a11 = account([x.replace(": whole, CHAIN OK, certificates replayed in 69", ": from level 13, CHAIN PARTIAL (levels "
                                 "below 13 not inspected (--from-n 13)), certificates replayed in 61") if x == f14 else x
                       for x in vs_lines], ps, True, chosen0)
        expect("account: a worker's first slice turned into a plain check from level 13",
               f14 is not None and 14 in a11["first_not_whole"])
        dg = next(x for x in va_lines if x.endswith("; files checked = copy's (digest)"))
        a9 = account([x[:-len("; files checked = copy's (digest)")] if x == dg else x for x in va_lines], pa, False)
        expect("account: a full re-run row without its files digest is not a verified row",
               int(rowx.match(dg).group(1)) in a9["bad_ok"])
    if (I / "control22-check.txt").is_file():   # G5 round 22, finding 8: the parser on the saved control report
        cr = (I / "control22-check.txt").read_text()
        C0 = parse_target(cr)
        C1 = parse_target(re.sub(r"SELF-TEST passed: (\d+) of", "SELF-TEST passed: 0 of", cr))
        C2 = parse_target(cr.replace("kept at (22,61)", "kept at (21,57)"))
        expect("parse_target: the saved control report reads its self-test passed and its own cell",
               C0["selftest_ok"] and C0["cell"] == [22, 61], str((C0["selftest"], C0["cell"])))
        expect("parse_target: a self-test of 0 of N is not passed (G5 round 22)", not C1["selftest_ok"])
        expect("parse_target: a kept count for another target leaves no cell", C2["cell"] is None)
    if (I / "calib2157-check.txt").is_file():
        ct = (I / "calib2157-check.txt").read_text()
        T0 = parse_target(ct)
        T1 = parse_target("\n".join(x for x in ct.splitlines() if not x.startswith("MISSING: ")))
        expect("parse_target: the MISSING line's count, and none without it (finding 7)",
               T0["missing_listed"] == T0["missing"] and T1["missing_listed"] == 0,
               f"{T0['missing_listed']} / {T0['missing']} / {T1['missing_listed']}")

    for kind, want in (("complete", "COMPLETE"), ("unrefuted", "TOP LEVEL NOT DECIDED"), ("one-missing", "INCOMPLETE"),
                       ("control-missing", "CONTROL FAILED"), ("sample-failed", "VERIFICATION FAILED"),
                       # G5 round 19: a row the parser cannot read under an OK verdict is a report that does not
                       # account for its slices, a failure (it was INCOMPLETE, kept from COMPLETE only)
                       ("sample-partial", "INCOMPLETE"), ("sample-miscounted", "VERIFICATION FAILED"),
                       ("sample-mostly-missing", "INCOMPLETE"), ("sample-no-exit", "INCOMPLETE"),
                       ("blind-rejects", "TOP LEVEL NOT DECIDED"), ("blind-other-graph", "TOP LEVEL NOT DECIDED"),
                       ("blind-other-certs", "TOP LEVEL NOT DECIDED"),
                       ("controls-open", "COMPLETE"),
                       ("control22-keeps", "CONTROL FAILED"), ("calib-loses", "CONTROL FAILED"),
                       ("rerun-fails", "VERIFICATION FAILED"), ("rerun-partial", "COMPLETE"),
                       ("controls-running", "COMPLETE"), ("control22-degree6", "CONTROL FAILED"),
                       ("calib-four-known", "CONTROL FAILED"), ("control22-slice-failing", "CONTROL FAILED"),
                       ("control22-selftest-broken", "CONTROL FAILED"), ("rerun-ok-with-problem", "VERIFICATION FAILED"),
                       ("control22-global-problem", "CONTROL FAILED"), ("control22-interrupted", "CONTROL FAILED"),
                       ("control22-audit-contradiction", "CONTROL FAILED"), ("g4-scope-fail", "INCOMPLETE"),
                       ("rerun-judge-crashed", "VERIFICATION FAILED"), ("rerun-ok-inconsistent", "VERIFICATION FAILED"),
                       ("rerun-ok-not-verified", "VERIFICATION FAILED"), ("rerun-ok-zero-tasks", "VERIFICATION FAILED"),
                       ("rerun-malformed", "VERIFICATION FAILED"), ("control22-malformed", "CONTROL FAILED"),
                       ("control22-ok-exit1", "CONTROL FAILED"), ("rerun-ok-no-rows", "VERIFICATION FAILED"),
                       ("sample-duplicated-rows", "VERIFICATION FAILED"),
                       ("rerun-fail-unexplained", "VERIFICATION FAILED"),
                       ("control22-fail-unexplained", "CONTROL FAILED"), ("calib-fail-unexplained", "CONTROL FAILED"),
                       ("sample-chain-fail-row", "VERIFICATION FAILED"), ("sample-no-whole", "VERIFICATION FAILED"),
                       ("rerun-fail-all-rows-ok", "VERIFICATION FAILED"), ("g4-scope-one-copy", "INCOMPLETE"),
                       ("control22-other-target", "CONTROL FAILED"), ("sample-other-copy", "VERIFICATION FAILED"),
                       ("sample-one-worker", "VERIFICATION FAILED"), ("g4-scope-other-copies", "INCOMPLETE"),
                       ("sample-other-seed", "VERIFICATION FAILED"), ("calib-kept-below-found", "CONTROL FAILED"),
                       ("g4-scope-other-root", "INCOMPLETE"), ("control22-missing-line", "CONTROL FAILED"),
                       ("control22-other-checker", "CONTROL FAILED"), ("sample-other-level", "VERIFICATION FAILED")):
        W = what_if(V, kind)
        D, doc, problems = build(W)
        text = strip(doc or "")
        expect(f"{kind}: state {want}", D["state"] == want, f"got {D['state']}, failing {D['failing']}")
        expect(f"{kind}: the lint is clean", doc is not None and not problems, "; ".join(problems[:3]))
        tn, tm = W["v"]["plan.target"]["value"]
        if want == "COMPLETE":
            expect(f"{kind}: the no-graph statement present", NO_GRAPH.format(cell=f"({tn},{tm})") in text)
        else:
            expect(f"{kind}: no 'finds no' anywhere", "finds no" not in text)
        if kind == "sample-partial":
            expect("sample-partial: the slices not verified are named", "113, 586, 606" in text)
        if kind in ("controls-open", "rerun-partial"):
            expect(f"{kind}: the open gate evidence is listed", "Still open, for the gates of Section 6" in text)
            expect(f"{kind}: its gate shows it open", ("| open: re-derived here" in text) if kind == "controls-open"
                   else ("the full re-run of every slice: open" in text))
        if kind in ("control22-keeps", "calib-loses"):
            expect(f"{kind}: the headline names the control", ("tree control" if kind == "control22-keeps"
                                                              else "calibration") in strip(D["headline"]))
        if kind == "rerun-fails":
            expect("rerun-fails: the headline names the full re-run", "full re-run" in strip(D["headline"]))
        if kind == "sample-failed":
            expect("sample-failed: the headline names the failure", "differs from the fleet's copy" in strip(D["headline"]))
        if kind == "sample-miscounted":
            expect("sample-miscounted: the miscount is named",
                   any("per-slice lines count" in strip(c["detail"]) for c in D["checks"]))
        expect(f"{kind}: the first lines say DRAFT", "DRAFT" in "\n".join(text.splitlines()[:3]))
        if kind == "unrefuted":
            expect("unrefuted: the top-level item names the slice",
                   any(c["name"] == "top level" and not c["ok"] for c in D["checks"]) and
                   str(W["v"]["top.kept_without_record"]["value"][0]) in strip(D["headline"]))
        if kind == "one-missing":
            expect("one-missing: the missing slice is listed", str(V["v"]["plan.slices"]["value"] - 1)
                   in strip(D["headline"] + " ".join(c["detail"] for c in D["checks"])))
        if kind == "control-missing":
            lost = W["v"]["l22.rows"]["value"][-1]["index"]
            expect("control-missing: the headline names the graph not kept", f"not kept: Engel {lost}"
                   in strip(D["headline"]))
    D, doc, problems = build(V)
    expect(f"as given: state {D['state']}, lint clean", doc is not None and not problems, "; ".join(problems[:3]))
    marked = render(what_if(V, "complete"), decide(what_if(V, "complete")), "x")
    for what, extra in (("a typed numeral", "\nThe fleet ran 1,234 slices.\n"),
                        ("a typed status word", "\nEvery replay PASS.\n"),
                        ("a state asserted in fixed text", "\nThe enumeration is complete.\n"),
                        ("an unconditional claim", "\nHence u(23) = 64.\n")):
        expect(f"lint red control, {what}: flagged", lint(marked + extra), "the lint passed it")
    for name, ok, detail in res:
        print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"  ({detail})" if detail and not ok else ""))
    bad = sum(1 for _, ok, _ in res if not ok)
    print(f"SELF-TEST {'passed' if not bad else 'FAILED'}: {len(res) - bad} of {len(res)} expectations")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------------------- main

def headline_text(D: dict) -> str:
    lines = [f"STATE: {D['state']}", f"HEADLINE: {strip(D['headline'])}"]
    lines += [f"  {'ok  ' if c['ok'] else 'OPEN'} {c['name']} ({strip(c['status'])}): {strip(c['detail'])}"
              for c in D["checks"]]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT, help="the fleet's extracted results (read-only)")
    ap.add_argument("--audit-worktree", type=Path, default=AUDIT_WORKTREE,
                    help=f"a checkout of {G5_BRANCH}, where the fleet audit lives")
    ap.add_argument("--g5-ref", default=f"origin/{G5_BRANCH}", help="the ref the G5 record is read from")
    ap.add_argument("--outputs", type=Path, default=RESULTS / "result-inputs", help="where the tools' outputs go")
    ap.add_argument("--aggregate-json", type=Path, help="read this aggregate_fleet.py --out record, do not run it")
    ap.add_argument("--aggregate-exit", type=int)
    ap.add_argument("--audit-log", type=Path, help="read this fleet-audit.py output, do not run it")
    ap.add_argument("--audit-exit", type=int)
    ap.add_argument("--top-level-log", type=Path, help="read this top_level_check.py --self-test output")
    ap.add_argument("--top-level-exit", type=int)
    ap.add_argument("--level22-log", type=Path, help="read this level22_control.py --self-test output")
    ap.add_argument("--level22-exit", type=int)
    ap.add_argument("--verify-root", type=Path,
                    default=Path("<scratch>/scratchpad/fleet/verify-results"),
                    help="the verification workers' extracted results (verify_sample.py --fetch)")
    ap.add_argument("--verify-log", type=Path, help="read this verify_sample.py output, do not run it")
    ap.add_argument("--verify-exit", type=int)
    ap.add_argument("--control22-root", type=Path, default=Path("<scratch>/scratchpad/control22"),
                    help="the (22,61) control's extracted results (target_check.py --fetch 'k*')")
    ap.add_argument("--control22-log", type=Path, help="read this target_check.py output for the control")
    ap.add_argument("--control22-exit", type=int)
    ap.add_argument("--calib-root", type=Path, default=Path("<scratch>/scratchpad/calib-local<repo>/"),
                    help="the (21,57) calibration's unpacked codex task results")
    ap.add_argument("--calib-log", type=Path, help="read this target_check.py output for the calibration")
    ap.add_argument("--calib-exit", type=int)
    ap.add_argument("--verify-all-root", type=Path, default=Path("<scratch>/scratchpad/verify-all-claude"),
                    help="the full re-run's unpacked codex task results")
    ap.add_argument("--verify-all-log", type=Path, help="read this verify_sample.py --all output")
    ap.add_argument("--verify-all-exit", type=int)
    ap.add_argument("--blind-log", type=Path, help="read this blind_check.py output, do not run it")
    ap.add_argument("--blind-exit", type=int)
    ap.add_argument("--values", type=Path, default=RESULTS / "result-values.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--from-values", type=Path, help="decide and render from this values file only")
    ap.add_argument("--headline-only", action="store_true", help="with --from-values: print the decision only")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    try:
        if a.from_values or a.self_test:
            V = load_values(a.from_values or a.values)
            if a.self_test:
                return self_test(V)
            D, doc, problems = build(V)
            print(headline_text(D))
            if problems:
                print("LINT FAILED:\n  " + "\n  ".join(problems), file=sys.stderr)
                return 1
            if a.out and not a.headline_only:
                a.out.write_text(strip(doc))
                print(f"WROTE {a.out}")
            return 0 if D["state"] == "COMPLETE" else 3
        V = extract(collect(a))
    except InputError as e:
        print(f"write_result.py: {e}", file=sys.stderr)
        return 2
    D, doc, problems = build(V)
    if problems:
        print(headline_text(D))
        print("LINT FAILED, nothing written:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    V["decision"] = {"state": D["state"], "headline": strip(D["headline"]), "failing": D["failing"],
                     "checks": [{k: strip(c[k]) if isinstance(c[k], str) else c[k] for k in c} for c in D["checks"]]}
    V["lint"] = strip(lint_note(render(V, D, None)))
    out = a.out or U23 / "RESULT-u23.md"
    a.values.parent.mkdir(parents=True, exist_ok=True)
    a.values.write_text(json.dumps(V, indent=1, default=str) + "\n")
    out.write_text(strip(doc))
    print(headline_text(D))
    print(f"WROTE {rel(out)} and {rel(a.values)}")
    return 0 if D["state"] == "COMPLETE" else 3


if __name__ == "__main__":
    sys.exit(main())
