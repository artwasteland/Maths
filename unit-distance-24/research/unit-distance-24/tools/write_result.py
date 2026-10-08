#!/usr/bin/env python3
"""Generate the u(24) G6 draft from saved evidence, using the standard library.

Installed defaults assume research/unit-distance-24/tools/write_result.py:
    /usr/bin/python3 -B write_result.py --repo REPO [--root FLEET]
        [--evidence DIR] [--original-evidence DIR] [--retained-scan FILE ...]
        [--contract FILE] [--reruns FILE ...] [--g0 FILE] [--g1 FILE]
        [--jobs FILE] [--review FILE ...] [--fleet-audit FILE]
        [--judge-pilot FILE] [--judge-full FILE] [--judge-phaseb FILE]
        [--judge-repro FILE] [--survivor-dir DIR ...] [--survivor-output FILE]
        [--u23-result FILE] [--u22-result FILE] [--forbidden FILE]
        [--gadgets FILE] [--pruning FILE] [--gp11-checker FILE]
        [--gp10-format FILE] [--gp11-format FILE] [--gp10-checker FILE]
        [--fresh-copies FILE]
        [--out FILE] [--values FILE] [--sources FILE]

No network or git calls, no imports from the evidence checkout, and no enumeration
or fleet audit. --root reads only the judge's cost.chosen copies; aggregation is
adapted from u(23)'s aggregate_fleet.aggregate. A missing fleet audit or G0 note
writes an INCOMPLETE draft. Malformed essential input is an input error.

--live-survivor is opt-in. It runs the existing checker script with
--checker-python (default /usr/bin/python3) inside bwrap's read-only filesystem,
with scratch storage inside the output directory. Its external checker needs its
own dependencies; the generator itself does not. Saved output is the default.

Exit: 0 COMPLETE, 3 INCOMPLETE (all outputs written), 2 input error,
1 lint error (no output written). Outputs must be outside the optional fleet.
"""

import argparse
import collections
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
MARK_L, MARK_R = "\x02", "\x03"
PLANS = ("pilot", "full", "phaseb")
ALL_PLANS = PLANS + ("repro",)
REJUDGE_FIELDS = ("verdict", "accepted_slices", "accepted_copies", "missing", "duplicates", "rejected",
                  "g4", "survivors", "resumed_slices", "rerun_disagreements")


class InputError(Exception):
    """Unreadable or structurally malformed evidence."""


class LintError(Exception):
    """The draft contains an unsourced literal or an unconditional claim."""


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def E(value, spec=None):
    if isinstance(value, bool):
        text = "yes" if value else "no"
    elif isinstance(value, int):
        text = format(value, spec or ",")
    elif isinstance(value, float):
        text = format(value, spec) if spec else format(value, ",.3f").rstrip("0").rstrip(".")
    elif value is None:
        text = "not recorded"
    else:
        text = str(value)
    if MARK_L in text or MARK_R in text:
        raise InputError("evidence contains reserved lint markers")
    return MARK_L + text + MARK_R


def strip(text):
    return text.replace(MARK_L, "").replace(MARK_R, "")


STATUS = re.compile(r"\b(?:PASS(?:ED)?|OK|FAIL(?:ED|S)?|ACCEPT(?:ED|S)?|REJECT(?:ED|S)?|"
                    r"CLOSED|UNRESOLVED|COMPLETE|INCOMPLETE|EMPTY|MISMATCH|PARTIAL|"
                    r"UNKNOWN|IDENTICAL|DIFFERENT)\b")
CLAIM = re.compile(r"u\(24\)\s*=\s*\d+")
CONDITION = re.compile(r"\b(?:if|only when|only with|never)\b", re.I)


def lint(marked):
    """Unlike the older lint, even section/gate labels must be sourced values.

    Claims are checked AFTER stripping value markers: putting an unconditional
    claim inside a sourced value does not exempt it. Conditions cannot leak
    across sentence or paragraph boundaries. Numerals include digits in paths.
    """
    problems = []
    if marked.count(MARK_L) != marked.count(MARK_R):
        problems.append("unbalanced value markers")
    fixed = re.sub(re.escape(MARK_L) + r"[^\x02\x03]*" + re.escape(MARK_R), " ", marked)
    for n, line in enumerate(fixed.splitlines(), 1):
        if re.search(r"\d", line):
            problems.append(f"line {n}: numeral in fixed text: {line[:160]}")
        if STATUS.search(line):
            problems.append(f"line {n}: status word in fixed text: {line[:160]}")
        if re.search(r"\b(?:is|are|was|were)\s+(?:now\s+)?(?:complete|closed|green|met)\b", line, re.I):
            problems.append(f"line {n}: state assertion in fixed text")
    text = strip(marked)
    for paragraph in re.split(r"\n\s*(?:>\s*)?\n", text):
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if CLAIM.search(sentence) and not CONDITION.search(sentence):
                problems.append("unconditional claim: " + sentence.strip()[:200])
    return problems


class Values:
    """The provenance ledger. Each value carries file, digest, and location.

    A derived value also names its input value keys and the operation. The
    source registry stores a single digest of the bytes actually read (compressed
    bytes for .gz); it never hashes a file a second time after reading it.
    """

    def __init__(self, repo):
        self.repo = Path(repo).resolve()
        self.sources, self.v, self.raw, self.source_groups = {}, {}, {}, {}
        self.displayed, self.external = set(), set()
        self.rerun_locations = []
        self.sidecar = None

    def read(self, name, path, optional=False, binary=False):
        path = Path(path).resolve()
        file = str(path.relative_to(self.repo)) if path.is_relative_to(self.repo) else str(path)
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            if not optional:
                raise InputError(f"missing input: {path}") from None
            raw = None
        except OSError as error:
            raise InputError(f"cannot read {path}: {error}") from None
        self.sources[name] = {"file": file, "sha256": sha256(raw) if raw is not None else None,
                              "missing": raw is None}
        self.raw[name] = raw
        if raw is None or binary:
            return raw
        try:
            data = gzip.decompress(raw) if path.suffix == ".gz" else raw
            return data.decode("utf-8")
        except (ValueError, OSError, UnicodeError) as error:
            raise InputError(f"cannot decode {path}: {error}") from None

    def json(self, name, path, optional=False):
        text = self.read(name, path, optional)
        if text is None:
            return None
        try:
            return json.loads(text)
        except ValueError as error:
            raise InputError(f"invalid JSON in {path}: {error}") from None

    def put(self, name, value, source, location="whole file"):
        self.v[name] = {"value": value, "sources": [{**self.sources[source], "location": location}]}
        return value

    def derive(self, name, value, inputs, operation):
        refs, seen = [], set()
        for key in inputs:
            for ref in self.v[key]["sources"]:
                identity = canonical(ref)
                if identity not in seen:
                    refs.append(ref)
                    seen.add(identity)
        # A per-level aggregate depends on thousands of files. Intern its source
        # list rather than duplicating it for every displayed cell. A group is
        # only a storage reference: its entries still name each file and digest.
        if len(refs) > 16:
            group = sha256(canonical(refs).encode())
            self.source_groups[group] = refs
            refs = [{"source_group": group}]
        self.v[name] = {"value": value, "sources": refs, "inputs": list(inputs), "derivation": operation}
        return value

    def get(self, name):
        return self.v[name]["value"]

    def field(self, report, *keys):
        name = report + "." + ".".join(map(str, keys))
        if name not in self.v:
            value = self.get(report)
            try:
                for key in keys:
                    value = value[key]
            except (KeyError, TypeError, IndexError):
                raise InputError(f"{report}: missing field {keys}") from None
            if report == "reruns" and keys and isinstance(keys[0], int):
                sid, line = self.rerun_locations[keys[0]]
                self.put(name, value, sid, f"JSONL line {line}, field " + ".".join(map(str, keys[1:])))
            else:
                self.derive(name, value, [report], "JSON field " + ".".join(map(str, keys)))
        return name

    def path(self, source):
        name = "path." + source
        if name not in self.v:
            self.put(name, self.sources[source]["file"], source, "source file identity")
        return name

    def digest(self, source):
        name = "sha256." + source
        if name not in self.v:
            self.put(name, self.sources[source]["sha256"], source, "sha256 of source bytes")
        return name

    def show(self, name, spec=None):
        self.displayed.add(name)
        return E(self.get(name), spec)

    def export(self, decision, sidecar_path):
        """Store displayed values and their derivation inputs, not raw reports.

        External JSON/JSONL inputs retain source references and selectors. A
        reader reloads those hashed files instead of getting redundant copies of
        the whole reports. The detailed fleet provenance is in the gzip sidecar.
        """
        registry = {sid: ref for sid, ref in self.sources.items() if not sid.startswith("tree.")}
        identities = {(r["file"], r["sha256"]): sid for sid, r in registry.items()}

        def compact_refs(refs):
            result = []
            for ref in refs:
                if "source_group" in ref:
                    result.extend(compact_refs(self.source_groups[ref["source_group"]]))
                else:
                    sid = identities.get((ref["file"], ref["sha256"]))
                    if sid is None:
                        raise InputError("unregistered compact provenance: " + ref["file"])
                    item = {"source": sid, "location": ref.get("location", "whole file")}
                    if item not in result:
                        result.append(item)
            return result

        kept, visited, groups, group_ids = {}, set(), {}, {}

        def retain(key):
            if key in visited:
                return
            visited.add(key)
            item = self.v[key]
            record = {k: value for k, value in item.items() if k not in ("value", "sources")}
            refs = compact_refs(item["sources"])
            if len(refs) > 1:
                identity = canonical(refs)
                if identity not in group_ids:
                    group = "g" + str(len(groups))
                    group_ids[identity] = group
                    groups[group] = refs
                record["sources"] = [{"source_group": group_ids[identity]}]
            else:
                record["sources"] = refs
            if key in self.external and key not in self.displayed:
                record["external_input"] = True
            elif key == "tree" and isinstance(item["value"], dict):
                record["value"] = {k: value for k, value in item["value"].items() if k not in ("selected", "root", "all_problems")}
            else:
                record["value"] = item["value"]
            kept[key] = record
            for parent in item.get("inputs", []):
                retain(parent)

        for key in sorted(self.displayed | {"lint"}):
            retain(key)
        return {"schema": "u24-result-values-v2", "generated_utc": self.get("generated_utc"),
                "sources": registry, "source_groups": groups, "v": kept, "decision": decision, "gate_table": self.get("gate_table"),
                "source_sidecar": {"file": sidecar_path, "sha256": sha256(self.sidecar)}}


def section(text, n):
    match = re.search(rf"^## {n}\. [^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        raise InputError(f"contract section {n} not found")
    return match[1].strip()


def bullets(text):
    return [m[0].rstrip() for m in re.finditer(r"^- .*?(?=^- |\Z)", text, re.M | re.S)]


def match_value(v, name, text, pattern, source, group=1, cast=str):
    match = re.search(pattern, text, re.M)
    if not match:
        raise InputError(f"cannot extract {name} from {v.sources[source]['file']}")
    return v.put(name, cast(match[group]), source, "regex: " + pattern)


def graph6(graph):
    """Decode the graph6 format locally; no networkx or checkout imports."""
    graph = graph.removeprefix(">>graph6<<")
    values = [ord(c) - 63 for c in graph]
    if not values or any(x < 0 or x > 63 for x in values):
        raise ValueError("invalid graph6 characters")
    if values[0] != 63:
        n, offset = values[0], 1
    elif len(values) >= 4 and values[1] != 63:
        n, offset = (values[1] << 12) + (values[2] << 6) + values[3], 4
    elif len(values) >= 8:
        n, offset = 0, 8
        for x in values[2:8]:
            n = (n << 6) + x
    else:
        raise ValueError("truncated graph6 header")
    if n > 4096:
        raise ValueError("graph6 too large for this write-up")
    required = n * (n - 1) // 2
    if len(values) - offset != (required + 5) // 6:
        raise ValueError("graph6 data length mismatch")
    edges, bit = set(), 0
    for j in range(1, n):
        for i in range(j):
            if values[offset + bit // 6] & (1 << (5 - bit % 6)):
                edges.add((i, j))
            bit += 1
    return n, edges


def live_survivor(a, bundle, v, sid):
    """Never fall back to an unisolated external checker invocation."""
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise InputError("--live-survivor requires bwrap for read-only checker isolation")
    output_dir = a.out.resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="survivor-check-", dir=output_dir) as tmp:
        scratch = Path(tmp)
        script = bundle / "check_survivor.py"
        command = [bwrap, "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/",
                   "--bind", str(scratch), str(scratch), "--tmpfs", "/tmp",
                   "--dir", "/tmp/gp10-check", "--bind", str(scratch), "/tmp/gp10-check",
                   "--", str(a.checker_python), "-B", str(script), str(bundle)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=1800,
                                env={**os.environ, "TMPDIR": str(scratch), "PYTHONDONTWRITEBYTECODE": "1"})
    log = output_dir / f"{sid}.live.out"
    log.write_text(f"# live command {canonical(command)} (exit {result.returncode})\n" + result.stdout + result.stderr)
    return log


def collect_g1_basis(v, text):
    """Summarize the closure record's stated basis, without rerunning reviews."""
    text = text or ""

    def take(pattern, number=False):
        match = re.search(pattern, text)
        return int(match[1].replace(",", "")) if match and number else match[1] if match else None

    basis = {"rounds": [int(n) for n in re.findall(r"\*\*Round (\d+)\.\*\*", text)],
             "verification_verdict": take(r"verifier's\s+verdict is (CLOSED|NOT CLOSED)"),
             "families": take(r"(\d+) field families:", True),
             "bound": take(r"(\d+) bound to a measurement", True),
             "historical": take(r"(\d+) historical claims about deleted files", True),
             "provenance": take(r"and (\d+) provenance fields", True),
             "sampled_bound": take(r"(\d+) randomly sampled bound fields", True),
             "sampling_caveat": "sampling is not exhaustive" in text,
             "scan_copies": take(r"all ([\d,]+) judged copies", True),
             "scan_files": take(r"That is ([\d,]+) files", True),
             "scan_stage_files": take(r"of which ([\d,]+) level files are bound to stage manifests", True),
             "scan_problems": take(r"with (\d+) problems", True),
             "rejudge_plans": take(r"All (\w+) plans give JUDGE OK"),
             "rejudge_verdict": take(r"All \w+ plans give (JUDGE OK)"),
             "fleet_verdict": take(r"and the fleet audit is (OK)"),
             "historical_limit": "They rest on the worker's checker" in text}
    v.put("g1.basis", basis, "g1", "What closes it: targeted verification rounds, field enumeration, retained scan, re-judge and limits")
    required = ("families", "bound", "historical", "provenance", "verification_verdict", "scan_copies",
                "scan_files", "scan_problems", "rejudge_plans", "rejudge_verdict", "fleet_verdict")
    if basis["rounds"] and all(basis[k] is not None for k in required):
        summary = ("Targeted verification rounds " + ", ".join(map(str, basis["rounds"])) +
                   f" end with verifier verdict {basis['verification_verdict']}; "
                   f"{basis['families']:,} field families: {basis['bound']:,} measured or derived, "
                   f"{basis['historical']:,} historical, {basis['provenance']:,} provenance; "
                   f"independent retained scan: {basis['scan_copies']:,} copies, {basis['scan_files']:,} files, "
                   f"{basis['scan_problems']:,} problems; {basis['rejudge_plans']}-plan re-judge "
                   f"{basis['rejudge_verdict']}, fleet audit {basis['fleet_verdict']}.")
        if basis["sampled_bound"] is not None:
            summary += f" The final verification sampled {basis['sampled_bound']:,} bound fields."
        if basis["sampling_caveat"]:
            summary += " Sampling is not exhaustive."
    else:
        summary = "No detailed verification basis is supplied by this closure input."
    v.derive("g1.basis_summary", summary, ["g1.basis"], "summarize only basis fields extracted from the closure note; retain the sampling limit")


def collect(a):
    v = Values(a.repo)
    contract = v.read("contract", a.contract)
    for n in (0, 1, 2, 3, 4):
        v.put(f"contract.section{n}", section(contract, n), "contract", f"section {n}, verbatim")
    gates = bullets(v.get("contract.section4"))
    names = [re.search(r"\*\*(G\d+)\*\*", b)[1] for b in gates]
    if names != [f"G{i}" for i in range(7)]:
        raise InputError("contract must list G0 through G6, in order")
    v.put("contract.gates", gates, "contract", "section 4 gate bullets, verbatim")
    v.put("contract.gate_names", names, "contract", "section 4 gate names")
    match_value(v, "claim.n", contract, r"u\((\d+)\) >=", "contract", cast=int)
    match_value(v, "claim.lower", contract, r"u\(\d+\) >= (\d+)", "contract", cast=int)
    match_value(v, "claim.top", contract, r"gives u\(\d+\) <= (\d+)", "contract", cast=int)
    match_value(v, "plan.count", v.get("contract.section2"), r"count ([\d,]+)", "contract",
                cast=lambda s: int(s.replace(",", "")))
    match_value(v, "plan.level", v.get("contract.section2"), r"slice\s+level (\d+)", "contract", cast=int)
    u23 = v.read("u23", a.u23_result)
    u22 = v.read("u22", a.u22_result)
    for n in range(1, 9):
        match_value(v, f"section.{n}", u23, rf"^## ({n})\.", "u23")
    match_value(v, "dependency.u23", u23, r"u\(23\) = (64)\b", "u23", cast=int)
    match_value(v, "dependency.u22", u22, r"u\(22\) = (\d+)\b", "u22", cast=int)
    deps = u23.split("Where each lives:\n", 1)
    if len(deps) != 2:
        raise InputError("u23 dependency list missing")
    entries = bullets(deps[1].split("\n## ", 1)[0])
    for key, needle in (("amp", "AMP's values"), ("forbidden", "minimal forbidden graphs"),
                        ("gadgets", "TU gadgets"), ("lemmas", "Lemma R and Lemma T")):
        found = [b for b in entries if needle in b]
        if len(found) != 1:
            raise InputError(f"u23 dependency {key} missing or ambiguous")
        v.put("dependency." + key, found[0], "u23", "dependency list, verbatim")
    v.read("forbidden", a.forbidden, binary=True)
    v.read("gadgets", a.gadgets, binary=True)
    v.read("pruning", a.pruning)
    v.read("gp10_format", a.gp10_format)
    v.read("gp11_format", a.gp11_format)
    v.read("gp10_checker", a.gp10_checker, binary=True)
    v.read("gp11_checker", a.gp11_checker, binary=True)
    order = re.search(rb"^GP(\d+) = HERE\.parent$", v.raw["gp11_checker"], re.M)
    if not order:
        raise InputError("frozen checker source does not identify its graph order")
    v.put("gp.order", int(order[1]), "gp11_checker", "graph order in the GP variable declaration")
    v.derive("gp.name", "GP-" + order[1].decode(), ["gp.order"], "graph-order label")
    v.derive("gp.order_word", {11: "eleven"}.get(int(order[1]), order[1].decode()), ["gp.order"], "spell graph order for prose")
    match_value(v, "replay.receipt_label", contract, r"(G4 replay)", "contract")
    match_value(v, "replay.fraction", contract, r"fraction\*\* \((0\.\d+)\)", "contract", cast=float)
    v.derive("replay.percent", 100 * v.get("replay.fraction"), ["replay.fraction"], "convert the contract's replay fraction to a percentage")
    v.read("judge_readme", a.evidence / "README.md")
    original_readme = v.read("original_readme", a.original_evidence / "README.md")
    date = re.search(r"\d{4}-\d{2}-\d{2}", original_readme)
    v.put("rejudge.original_date", date[0] if date else None, "original_readme", "date in original report README heading")
    label = re.search(r"r\d+$", a.evidence.name)
    v.put("rejudge.label", label[0] if label else "selected", "judge_readme", "selected evidence directory identity")
    tsv = v.read("fleet_sources", a.evidence / "sources.tsv")
    v.read("original_fleet_sources", a.original_evidence / "sources.tsv")
    v.derive("rejudge.same_snapshot", v.raw["fleet_sources"] == v.raw["original_fleet_sources"],
             [v.digest("fleet_sources"), v.digest("original_fleet_sources")], "exact equality of original and final branch/commit TSV bytes")
    v.put("fleet.branches", len([line for line in tsv.splitlines() if line.strip()]), "fleet_sources", "nonempty rows")
    for plan in ALL_PLANS:
        sid = "judge_" + plan
        report = v.json(sid, getattr(a, "judge_" + plan))
        if not isinstance(report, dict):
            raise InputError(f"{sid} is not a JSON object")
        v.put(sid, report, sid)
        v.external.add(sid)
        # Hash the saved rendering too, but take decisions from JSON, not its labels.
        v.read(sid + "_text", a.evidence / f"judge-{plan}.txt.gz")
        original = "original_judge_" + plan
        v.put(original, v.json(original, a.original_evidence / f"judge-{plan}.json.gz", optional=True), original)
        v.external.add(original)
    v.derive("rejudge.key_fields", list(REJUDGE_FIELDS), ["judge_" + p for p in ALL_PLANS],
             "judgment keys selected from report JSON names, matching the final README's identical-field list")
    scans = []
    for index, path in enumerate(a.retained_scan):
        sid = f"retained_scan.{index}"
        text = v.read(sid, path, optional=True)
        lines = (text or "").splitlines()
        summary = next(((n, line) for n, line in enumerate(lines, 1) if line.startswith("RETAINED SCAN ")), None)
        coverage = next(((n, line) for n, line in enumerate(lines, 1) if line.startswith("# coverage ")), None)
        v.put(sid + ".summary", summary[1] if summary else None, sid,
              f"summary line {summary[0]}" if summary else "summary line absent")
        v.put(sid + ".coverage", coverage[1] if coverage else None, sid,
              f"coverage line {coverage[0]}" if coverage else "coverage line absent")
        scans.append(sid)
    v.derive("retained_scan.reports", scans, [s + ".summary" for s in scans], "selected retained-scan reports")
    audit = v.json("fleet_audit", a.fleet_audit, optional=True)
    v.put("fleet_audit", audit, "fleet_audit")
    v.external.add("fleet_audit")
    rows, row_inputs, rerun_paths = [], [], []
    rerun_files = a.reruns if a.reruns is not None else sorted((a.repo / "research/unit-distance-24/evidence").glob("rerun-resumed-*.jsonl"))
    for index, path in enumerate(rerun_files):
        sid = f"reruns.file{index}"
        text = v.read(sid, path, optional=True)
        file_rows = []
        try:
            for line, raw in enumerate((text or "").splitlines(), 1):
                if raw.strip():
                    file_rows.append(json.loads(raw))
                    v.rerun_locations.append((sid, line))
        except ValueError as error:
            raise InputError(f"invalid rerun JSONL in {path}: {error}") from None
        v.put(sid, file_rows, sid, "JSONL rows")
        v.external.add(sid)
        row_inputs.append(sid)
        rerun_paths.append(v.sources[sid]["file"])
        rows.extend(file_rows)
    v.derive("reruns", rows, row_inputs or ["contract.section3"], "concatenate all supplied or discovered rerun-resumed-*.jsonl files in path order")
    v.external.add("reruns")
    v.derive("reruns.files", rerun_paths, row_inputs or ["contract.section3"], "rerun input file identities; an empty list records no saved comparisons")
    fresh = v.json("fresh_copies", a.fresh_copies, optional=True)
    v.put("fresh_copies", fresh, "fresh_copies")
    v.external.add("fresh_copies")
    tags = fresh.get("tags", {}) if isinstance(fresh, dict) else {}
    bound, unbound = {}, []
    for row in rows:
        if not isinstance(row, dict):
            continue
        tag, index = row.get("fresh_tag"), str(row.get("slice"))
        address = tags.get(tag, {})
        receipt = address.get("slices", {}).get(index)
        if not isinstance(receipt, dict):
            unbound.append({"tag": tag, "slice": row.get("slice")})
            continue
        entry = bound.setdefault(tag, {"branch": address.get("branch"), "commit": address.get("commit"), "slices": {}})
        entry["slices"][index] = receipt
    v.derive("fresh.bindings", {"tags": bound, "unbound": unbound}, ["fresh_copies", "reruns"],
             "bind every comparison's fresh tag/slice to its manifest branch, commit, receipt path, receipt digest and structure digest")
    v.derive("fresh.tags", sorted(bound), ["fresh.bindings"], "fresh tags whose comparison receipts have a manifest entry")
    g0 = v.read("g0", a.g0, optional=True)
    v.put("g0.exists", g0 is not None, "g0", "file presence")
    verdict = re.search(r"^Verdict: (.*?)(?= \*\*Dependency|$)", g0 or "", re.M)
    v.put("g0.verdict", verdict[1] if verdict else "no verdict extracted", "g0", "Verdict line")
    g1 = v.read("g1", a.g1, optional=True)
    first_verdict = re.search(r"^G1 verdict: (CLOSED|NOT CLOSED)\b", g1 or "", re.M)
    v.put("g1.exists", g1 is not None, "g1", "file presence")
    v.put("g1.verdict", first_verdict[1] if first_verdict else None, "g1", "first line matching ^G1 verdict: (CLOSED|NOT CLOSED)")
    collect_g1_basis(v, g1)
    jobs = v.read("jobs", a.jobs)
    pilot = re.search(r"^## u24-pilot\b.*?(?=^## |\Z)", jobs, re.M | re.S)
    v.put("pilot.jobs", pilot[0].strip() if pilot else "", "jobs", "u24-pilot section")
    v.external.add("pilot.jobs")
    needle = "**time-slice supervisor landed; every resumed u24 slice is treated as suspect.**"
    start = jobs.find(needle)
    if start < 0:
        raise InputError("JOBS.md time-slice policy paragraph missing")
    stop = jobs.find("\n10:55Z:", start)
    if stop < 0:
        raise InputError("JOBS.md time-slice policy boundary missing")
    policy = jobs[start:stop]
    policy_start = policy.find("Policy:")
    policy_stop = policy.find("\nJudge (")
    if policy_start < 0 or policy_stop < 0:
        raise InputError("JOBS.md resume policy sentences missing")
    v.put("resume.policy", policy[policy_start:policy_stop], "jobs", "10:40Z paragraph, Policy sentences, verbatim")
    v.put("resume.mechanisms", policy[:policy_start].rstrip(), "jobs", "10:40Z paragraph, supervisor mechanisms, verbatim")
    v.put("resume.policy_location", f"{v.sources['jobs']['file']}:{jobs[:start + policy_start].count(chr(10)) + 1} (the 10:40Z paragraph)",
          "jobs", "source line of Policy sentences")
    review_ids = []
    for index, path in enumerate(a.review):
        sid = "review." + str(index)
        text = v.read(sid, path)
        v.put(sid, text, sid)
        v.external.add(sid)
        review_ids.append(sid)
    v.derive("reviews.files", [v.sources[s]["file"] for s in review_ids], review_ids, "review source identities")
    # Fix reports claiming findings are addressed are not a reviewer closure.
    closure = [line for s in review_ids for line in v.get(s).splitlines()
               if re.search(r"\bG1\s*:\s*CLOSED\b|\b(?:final review|reviews?)\s*:\s*CLOSED\b", line, re.I)]
    v.derive("reviews.closure", closure, review_ids, "explicit G1/final-review closure lines; addressed is insufficient")
    note = a.repo / "research/unit-distance-24/SURVIVOR-s50-2026-10-06.md"
    v.read("survivor_note", note)
    bundles = []
    for index, bundle in enumerate(a.survivor_dir):
        sid = "survivor." + str(index)
        mapping = v.json(sid + ".mapping", bundle / "mapping.json", optional=True)
        v.put(sid + ".mapping", mapping, sid + ".mapping")
        v.read(sid + ".script", bundle / "check_survivor.py", optional=True)
        log = (a.survivor_output if a.survivor_output and index == 0 else bundle / "check_survivor.out")
        if a.live_survivor:
            log = live_survivor(a, bundle, v, sid)
        output = v.read(sid + ".output", log, optional=True)
        v.put(sid + ".output", output, sid + ".output")
        problems, inputs = [], [sid + ".mapping", sid + ".output"]
        raw = None
        if not isinstance(mapping, dict):
            problems.append("refutation mapping is absent")
        else:
            record_name = mapping.get("record")
            if not isinstance(record_name, str) or Path(record_name).name != record_name:
                problems.append("refutation record path is invalid")
            else:
                raw = v.read(sid + ".record", bundle / record_name, optional=True, binary=True)
                v.put(sid + ".record_hash", sha256(raw) if raw is not None else None, sid + ".record", "sha256")
                inputs.append(sid + ".record_hash")
                if raw is None or sha256(raw) != mapping.get("record_sha256"):
                    problems.append("refutation record is absent or its hash differs")
            try:
                sn, se = graph6(mapping["survivor"])
                pn, pe = graph6(mapping["pattern"])
                image = {int(k): x for k, x in mapping["pattern_to_survivor"].items()}
                if ((sn, len(se)) != (v.get("claim.n"), v.get("claim.top")) or
                        set(image) != set(range(pn)) or len(set(image.values())) != pn or
                        any(type(x) is not int or not 0 <= x < sn for x in image.values()) or
                        any(tuple(sorted((image[x], image[y]))) not in se for x, y in pe)):
                    problems.append("subgraph mapping does not validate")
                v.derive(sid + ".pattern_size", [pn, len(pe)], [sid + ".mapping"], "decode graph6 and count edges")
                record = json.loads(raw) if raw is not None else {}
                cert = record.get("cert") or {}
                if isinstance(cert, dict):
                    sos = cert.get("sos")
                    v.put(sid + ".certificate", {"type": cert.get("type"),
                          "rows": len(cert["rows"]) if isinstance(cert.get("rows"), list) else None,
                          "sos": isinstance(sos, dict),
                          "squares": len(sos.get("squares", [])) if isinstance(sos, dict) else None},
                          sid + ".record", "cert.type, length of cert.rows, cert.sos and length of cert.sos.squares")
                if record.get("g6") != mapping["pattern"] or record.get("verdict") != "refuted":
                    problems.append("record does not refute the mapped pattern")
                expected = (f'SURVIVOR REFUTATION OK: {mapping["survivor"]} contains {mapping["pattern"]} '
                            '(refuted, frozen checker ACCEPT)')
                lines = (output or "").splitlines()
                header = lines[0] if lines else ""
                if (expected not in lines or f'ACCEPT record {mapping["pattern"]} verified' not in lines or
                        "ACCEPT run verified" not in lines or not re.search(r"\(exit 0\)", header) or
                        any(re.search(r"\b(?:FAIL|REJECT)\b", line) for line in lines)):
                    problems.append("saved check lacks an exact graph-bound success and exit-zero record")
            except (ValueError, KeyError, TypeError, AttributeError):
                problems.append("malformed graph, mapping or record")
        blind = v.json(sid + ".blind", bundle / "independent-codex/checker-results.json", optional=True)
        v.put(sid + ".blind", blind, sid + ".blind")
        v.external.add(sid + ".blind")
        search = v.json(sid + ".search", bundle / "independent-codex/search-results.json", optional=True)
        v.put(sid + ".search", search, sid + ".search")
        v.external.add(sid + ".search")
        v.read(sid + ".blind_note", bundle / "independent-codex/FINAL.md", optional=True)
        v.read(sid + ".subgraph_log", bundle / "survivor-subgraph.log", optional=True)
        if isinstance(blind, dict):
            originals = [r for r in blind.get("records", []) if not r.get("damaged")]
            red = [r for r in blind.get("records", []) if r.get("damaged")]
            v.derive(sid + ".blind_counts", {"originals": len(originals),
                     "accepted": sum(r.get("status") == "ACCEPT" and r.get("exit_code") == 0 for r in originals),
                     "damaged": len(red), "rejected": sum(r.get("status") == "REJECT" and r.get("exit_code") != 0 for r in red)},
                     [sid + ".blind"], "count original and damaged checker results separately")
            found = search.get("records", []) if isinstance(search, dict) else []
            v.derive(sid + ".blind_search", {"patterns": len(found),
                     "embedded": sum(r.get("embeds") is True and r.get("mapping_independently_verified") is True for r in found),
                     "orders": sorted({r.get("vertices") for r in found if isinstance(r.get("vertices"), int)})},
                     [sid + ".search"], "count independently verified subgraph embeddings and their vertex orders")
            if blind.get("checker_sha256") != v.sources["gp11_checker"]["sha256"]:
                problems.append("current frozen checker differs from the independent check's hash")
            inputs.append(sid + ".blind")
        else:
            problems.append("independent checker's frozen-checker hash is absent")
        v.derive(sid + ".problems", problems, inputs + ["claim.n", "claim.top"],
                 "hash, record identity, injective edge mapping, exact saved check lines, checker hash binding")
        bundles.append(sid)
    v.derive("survivor.bundles", bundles, [s + ".mapping" for s in bundles], "supplied bundles")
    v.read("generator", HERE, binary=True)
    v.put("generated_utc", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
          "generator", "generation metadata, not a mathematical evidence value")
    v.put("generator.destination", "research/unit-distance-24/tools/write_result.py", "generator", "installed location")
    v.read("generator_tests", HERE.with_name("test_write_result.py"), binary=True)
    for name in ("judge.py", "fleet_audit.py", "test_fleet_audit.py", "rerun_compare.py"):
        v.read("tool." + name, a.repo / "research/unit-distance-24/tools" / name, binary=True)
    for index, bundle in enumerate(a.survivor_dir):
        for name in ("blind_check.py", "run_certificates.py"):
            v.read(f"survivor.{index}." + name, bundle / "independent-codex" / name, optional=True, binary=True)
    if a.root:
        aggregate(v, a.root)
    else:
        v.derive("tree", None, ["judge_" + p for p in PLANS], "--root not supplied: saved judge reports have no per-level aggregate")
    return v


def aggregate(v, root):
    """Adapt u23's per-cell Counter aggregation, retaining every chosen source.

    Read counts and summaries in sequence, never manifests/certificates. Check
    identities and the summary's independent count representation, required cells,
    kept+pruned=input, pruned by kind, and the target's measured aggregate. Missing
    copies yield an omitted table and a G6 failure, not a partial table presented
    as a whole fleet. Digests pin the actual bytes read from the optional snapshot.
    """
    root = root.resolve()
    cells, expected, inputs, selected, errors = {}, None, [], [], []
    level = v.get("plan.level")
    for plan in PLANS:
        report = v.get("judge_" + plan)
        for i in report["accepted_slices"]:
            key = str(i)
            row = report.get("cost", {}).get("chosen", {}).get(key)
            if not isinstance(row, dict) or row.get("accepted") is not True:
                errors.append(f"{plan} slice {i}: no accepted cost.chosen selection")
                continue
            source = row.get("source", "")
            receipt = (root / source).resolve()
            if not source or not receipt.is_relative_to(root) or receipt.parent.name != "check":
                errors.append(f"{plan} slice {i}: invalid source path")
                continue
            results = receipt.parent.parent
            candidates = sorted(results.glob(f"*/s{i}of{v.get('plan.count')}/counts.json"))
            if len(candidates) != 1 or not candidates[0].resolve().is_relative_to(root):
                errors.append(f"{plan} slice {i}: cannot identify one counted counts.json")
                continue
            path = candidates[0]
            sid = f"tree.{plan}.{i}"
            try:
                counts = v.json(sid, path)
                summary = v.json(sid + ".summary", path.parent / "run-summary.json")
                # Detailed per-copy provenance goes to the deterministic gzip
                # sidecar. It must not become thousands of value records.
                v.raw.pop(sid, None)
                v.raw.pop(sid + ".summary", None)
                if (summary.get("slice") != [level, i, v.get("plan.count")] or
                        summary.get("target") != [v.get("claim.n"), v.get("claim.top")] or
                        summary.get("completed_through_n") != v.get("claim.n")):
                    raise ValueError("counted summary identity differs")
                summaries = {(r["n"], r["m"]): (r.get("children"), (r.get("prune") or {}).get("counts"))
                             for r in summary["levels"] if r["n"] > level}
                per_copy = {}
                for n, m, children, pc in counts:
                    if n <= level:
                        continue
                    if (n, m) in per_copy:
                        raise ValueError("duplicate cell")
                    if (type(children) is not int or children < 0 or not isinstance(pc, dict) or
                            any(type(x) is not int or x < 0 for x in pc.values())):
                        raise ValueError("invalid cell counts")
                    if summaries.get((n, m)) != (children, pc):
                        raise ValueError("counts disagree with summary")
                    kinds = [k for k in pc if re.fullmatch(r"tu|refuted|forbidden|[a-z0-9]+_(?:tu|refuted)", k)]
                    if (pc["kept"] + pc["pruned"] != pc["input"] or pc["input"] > children or
                            sum(pc[k] for k in kinds) != pc["pruned"]):
                        raise ValueError("prune accounting differs")
                    per_copy[n, m] = {"children": children, **pc}
                if set(per_copy) != set(summaries):
                    raise ValueError("summary/count cell sets differ")
                if expected is None:
                    expected = set(per_copy)
                if set(per_copy) != expected:
                    raise ValueError("required cells differ between chosen copies")
                for cell, c in per_copy.items():
                    cells.setdefault(cell, collections.Counter()).update(c)
                selected.append({"plan": plan, "slice": i, "source": source, "counts": v.sources[sid],
                                 "summary": v.sources[sid + ".summary"]})
            except (InputError, KeyError, TypeError, ValueError) as error:
                errors.append(f"{plan} slice {i}: {error}")
    n, m = v.get("claim.n"), v.get("claim.top")
    if len(selected) != v.get("plan.count") or len({r['slice'] for r in selected}) != v.get("plan.count"):
        errors.append("counted copies do not cover exactly the contracted fleet")
    top = cells.get((n, m), {})
    target_children = sum(v.get("judge_" + p)["summary"]["record"]["fleets"][0]["target_cell"]["children"] for p in PLANS)
    target_kept = sum(v.get("judge_" + p)["summary"]["record"]["fleets"][0]["target_cell"]["kept"] for p in PLANS)
    if top.get("children") != target_children or top.get("kept") != target_kept:
        errors.append("aggregate target differs from the saved judge's target measurements")
    levels = []
    for n in sorted({c[0] for c in cells}):
        row = collections.Counter()
        ms = sorted(m for nn, m in cells if nn == n)
        for m in ms:
            row.update(cells[n, m])
        levels.append({"level": n, "window": str(ms[0]) if len(ms) == 1 else f"{ms[0]}..{ms[-1]}",
                       "cells": len(ms), **dict(row),
                       "pruned_percent": 100 * row["pruned"] / row["input"] if row["input"] else 0.0})
    listed_errors = errors[:8] + ([f"{len(errors) - 8} additional aggregation problems; full list in the compressed source manifest"] if len(errors) > 8 else [])
    v.derive("tree", {"root": str(root), "counted_copies": len(selected), "selected": selected,
                      "levels": levels if not errors else [], "problems": listed_errors,
                      "problems_count": len(errors), "all_problems": errors},
             ["judge_" + p for p in PLANS], "sum counts by cell then level above slice level; cross-check summaries and prune identities; raw copy sources are in the gzip sidecar")


def pack_sources(v, destination, values_path):
    """Pin every selected counts file once, in a deterministic gzip artifact."""
    tree = v.get("tree")
    obj = {"schema": "u24-result-sources-v1", "root": tree["root"] if tree else None,
           "counted_copies": tree["counted_copies"] if tree else 0,
           "selected": tree["selected"] if tree else [],
           "problems": tree.get("all_problems", []) if tree else [],
           "sources": {key: ref for key, ref in v.sources.items() if key.startswith("tree.")}}
    v.sidecar = gzip.compress((canonical(obj) + "\n").encode("utf-8"), mtime=0)
    file = os.path.relpath(destination.resolve(), values_path.resolve().parent)
    v.sources["tree_sources"] = {"file": file, "sha256": sha256(v.sidecar),
                                 "missing": False, "artifact": True}
    v.put("tree.source_digest", sha256(v.sidecar), "tree_sources", "sha256 of compressed sidecar bytes")
    v.put("tree.source_file", file, "tree_sources", "path relative to the values file")
    item = v.v["tree"]
    v.derive("tree", item["value"], item["inputs"] + ["tree.source_digest"], item["derivation"])


def rerun_is_fresh(row):
    return (row.get("fresh_from_scratch") is True and type(row.get("fresh_recovered_cells")) is int
            and row["fresh_recovered_cells"] == 0)


def rerun_is_accepted(row):
    return (isinstance(row, dict) and row.get("verdict") == "IDENTICAL" and row.get("fresh_verdict_pass") is True
            and rerun_is_fresh(row) and isinstance(row.get("files"), dict)
            and set(row["files"]) == {"counts.json", "hashes.json", "reach.json", "run-config.json", "known.json without run"}
            and all(x is True for x in row["files"].values()))


def resumed_twins(v, reports):
    """Name each resumed accepted receipt, and bind a comparison to its copy.

    A duplicate's counted twin can cover it only through the judge's explicit
    duplicate-copy agreement. Structural recovery is included even when the
    timing record has no positive resumed-cell count (the phase-B slice does).
    Only accepted comparisons with an explicitly fresh copy count. A reproduction
    twin's chosen copy must have a recorded zero resumed-cell count. Missing twins
    are reported; they do not veto the headline.
    """
    twins = []
    for p in PLANS:
        report = reports[p]
        for i in report.get("resumed_slices", []):
            accepted = [r for r in report.get("cost", {}).get("rows", {}).get(str(i), []) if r.get("accepted") is True]
            resumed = [r for r in accepted if r.get("resumed_cells", 0) > 0] or accepted
            chosen = report.get("cost", {}).get("chosen", {}).get(str(i), {}).get("source")
            for row in resumed:
                source = row["source"]
                tag_match = re.search(r"-([^/]+)\.txt$", source)
                tag = tag_match[1] if tag_match else ""
                matches = [(k, r) for k, r in enumerate(v.get("reruns")) if isinstance(r, dict)
                           and r.get("slice") == i and r.get("kept_tag") == tag]
                relation = "direct comparison"
                if source != chosen:
                    chosen_match = re.search(r"-([^/]+)\.txt$", chosen or "")
                    same = source in report.get("duplicates", {}).get(str(i), []) and chosen in report.get("duplicates", {}).get(str(i), [])
                    if same and report.get("verdict") == "OK" and chosen_match:
                        matches = [(k, r) for k, r in enumerate(v.get("reruns")) if isinstance(r, dict)
                                   and r.get("slice") == i and r.get("kept_tag") == chosen_match[1]]
                        relation = "via the counted copy and the judge's duplicate-copy agreement"
                    else:
                        matches = []
                comparisons, rejected = [], []
                for k, r in matches:
                    sid, line = v.rerun_locations[k]
                    text = f"{r.get('fresh_tag')} ({r.get('verdict')}); {v.sources[sid]['file']}:{line}; {relation}"
                    if rerun_is_accepted(r):
                        comparisons.append(text)
                    elif not rerun_is_fresh(r):
                        recovered = r.get("fresh_recovered_cells")
                        why = (f"twin itself resumed ({recovered} recovered cells)"
                               if type(recovered) is int and recovered > 0 else "freshness not established")
                        rejected.append(text + "; " + why)
                    else:
                        rejected.append(text + "; comparison did not pass")
                repro = reports["repro"]
                candidate = repro.get("cost", {}).get("chosen", {}).get(str(i), {})
                duplicates = repro.get("duplicates", {}).get(str(i), [])
                if (not comparisons and i in repro.get("accepted_slices", []) and source in duplicates
                        and repro.get("verdict") == "OK" and candidate.get("accepted") is True
                        and candidate.get("source") != source and candidate.get("source") in duplicates):
                    text = f"reproduction comparison: {candidate['source']}; judge verdict {repro.get('verdict')}"
                    recovered = candidate.get("resumed_cells")
                    if type(recovered) is int and recovered == 0:
                        comparisons.append(text)
                    else:
                        why = (f"twin itself resumed ({recovered} recovered cells)"
                               if type(recovered) is int and recovered > 0 else "freshness not recorded")
                        rejected.append(text + "; " + why)
                text = "; ".join(comparisons) if comparisons else "; ".join(rejected + ["no from-scratch twin is recorded"])
                twins.append({"plan": report["provenance"]["plan"]["job"], "slice": i, "source": source,
                              "mechanism": "legacy same-container relaunch" if p == "full" else "tree-kill time-slice supervisor",
                              "twin": text,
                              "missing": not comparisons})
    keys = ["judge_" + p for p in ALL_PLANS] + ["reruns", "resume.policy", "resume.mechanisms"]
    v.derive("resume.twins", twins, keys, "match resumed receipts to accepted reruns with fresh_from_scratch true and no recovered cells, or chosen reproduction copies with zero resumed cells; duplicate comparisons bind other copies")
    v.derive("resume.missing", [r for r in twins if r["missing"]], ["resume.twins"], "list resumed accepted copies without a recorded from-scratch twin; this is not a gate predicate")


def decide(v):
    """Every headline item is a separate predicate, with its gate and sources."""
    checks = []

    def check(name, gate, ok, detail, keys):
        key = "check." + name
        obj = {"name": name, "gate": gate, "ok": bool(ok), "status": "met" if ok else "not met", "detail": detail}
        v.derive(key, obj, keys, "evidence predicate: " + name)
        checks.append(obj)

    reports = {p: v.get("judge_" + p) for p in ALL_PLANS}
    comparisons = []
    for p in ALL_PLANS:
        original = v.get("original_judge_" + p)
        changed = [key for key in v.get("rejudge.key_fields") if not isinstance(original, dict)
                   or key not in original or key not in reports[p] or original[key] != reports[p][key]]
        comparisons.append({"plan": p, "matching": not changed, "different_fields": changed})
    v.derive("rejudge.comparisons", comparisons,
             ["rejudge.key_fields"] + ["original_judge_" + p for p in ALL_PLANS] + ["judge_" + p for p in ALL_PLANS],
             "compare every documented key field, requiring presence and exact equality in each original/final report pair")
    rejudge_ok = v.get("rejudge.same_snapshot") and all(row["matching"] for row in comparisons)
    check("rejudge-equality", "G3", rejudge_ok,
          f"same snapshot sources {v.get('rejudge.same_snapshot')}; original/final key-field differences " +
          str({row["plan"]: row["different_fields"] for row in comparisons if not row["matching"]}),
          ["rejudge.comparisons", "rejudge.same_snapshot"])
    reasons = collections.Counter(r.get("why", "reason absent from record")
                                  for r in reports["full"]["provenance"]["plan"].get("rerun", []))
    reason_rows = [{"why": why, "requests": number} for why, number in sorted(reasons.items())]
    v.derive("history.reasons", reason_rows, ["judge_full"],
             "count each distinct verbatim why string in the published full plan")
    grouped = {}
    for row in reason_rows:
        clause = re.split(r" \(|;", row["why"], maxsplit=1)[0]
        group = grouped.setdefault(clause, {"requests": 0, "leads": []})
        group["requests"] += row["requests"]
        group["leads"].extend(int(lead) for lead in re.findall(r"\blead ([+-]?\d+) s\b", row["why"]))
    group_rows = []
    for clause, group in sorted(grouped.items()):
        low = min(group["leads"]) if group["leads"] else None
        high = max(group["leads"]) if group["leads"] else None
        group_rows.append({"why": clause, "requests": group["requests"],
                           "lead_seconds_min": low, "lead_seconds_max": high,
                           "lead_seconds_range": f"{low}..{high}" if low is not None else None})
    v.derive("history.reason_groups", group_rows, ["history.reasons"],
             "group by the leading clause before the first ' (' or ';'; sum exact-reason counts; min/max signed lead N s values wherever present")
    total = v.derive("history.grouped_requests", sum(row["requests"] for row in group_rows),
                     ["history.reason_groups"], "sum requested pairs across leading-clause groups")
    requested = reports["full"].get("rerun_count")
    check("rerun-reason-accounting", "G3", type(requested) is int and total == requested,
          f"rerun reason groups total {total}; judge requested pairs {requested}",
          ["history.grouped_requests", v.field("judge_full", "rerun_count")])
    count, level = v.get("plan.count"), v.get("plan.level")
    for p in PLANS:
        j = reports[p]
        ok = (j.get("schema") == "u24-fleet-judge-v1" and j.get("verdict") == "OK" and j.get("exit") == 0
              and j.get("missing") == [] and j.get("problems") == [] and j.get("pending") == []
              and j.get("g4") == {"PASS": j.get("accepted_copies")} and bool(j.get("prefix_files"))
              and (j.get("summary") or {}).get("problems") == [] and (j.get("summary") or {}).get("unresolved") == []
              and j.get("provenance", {}).get("checker_sha256") == reports["pilot"].get("provenance", {}).get("checker_sha256")
              and j.get("provenance", {}).get("plan", {}).get("count") == count
              and j.get("provenance", {}).get("plan", {}).get("slice_level") == level
              and j.get("provenance", {}).get("plan", {}).get("target") == [v.get("claim.n"), v.get("claim.top")])
        check("plan-" + p, "G3", ok, f"{p} verdict {j.get('verdict')}, exit {j.get('exit')}",
              ["judge_" + p, "judge_pilot", "plan.count", "plan.level", "claim.n", "claim.top"])
    accepted = [i for p in PLANS for i in reports[p].get("accepted_slices", [])]
    coverage = (all(type(i) is int for i in accepted) and sorted(accepted) == list(range(count))
                and all(sorted(reports[p].get("accepted_slices", [])) == sorted(reports[p].get("planned", [])) for p in PLANS))
    check("partition", "G3", coverage, f"{len(accepted)} accepted slice entries; expected the partition of range({count})",
          ["judge_" + p for p in PLANS] + ["plan.count"])
    audit = v.get("fleet_audit")
    audit_ok = False
    if isinstance(audit, dict):
        summary = audit.get("audit") or {}
        record = summary.get("record") or {}
        fleets = record.get("fleets") or []
        audited_plans = audit.get("plans") or {}
        names = {"pilot": "pilot", "full": "full", "phaseb": "phaseB"}
        audit_ok = (audit.get("schema") == "u24-fleet-audit-v1" and audit.get("verdict") == "OK" and audit.get("exit") == 0
                    and audit.get("problems") == [] and summary.get("status") == "complete"
                    and summary.get("problems") == [] and summary.get("unresolved") == [] and summary.get("missing_slices") == 0
                    and audit.get("union_slices") == count and record.get("problems") == 0 and record.get("unresolved") == 0
                    and audit.get("union_copies") == sum(reports[p].get("accepted_copies", 0) for p in PLANS)
                    and record.get("audited") == audit.get("union_copies") and record.get("runs") == audit.get("union_copies")
                     and len(fleets) == 1 and fleets[0].get("slice_indices") == count and fleets[0].get("missing_slices") == 0
                     and bool(fleets[0].get("slice_partition"))
                     and all(isinstance(row, dict) and type(row.get("sum")) is int
                             and row.get("sum") == row.get("stage_file") and row.get("slices_recording") == count
                             for row in fleets[0]["slice_partition"].values())
                    and audit.get("checker_sha256") == reports['pilot'].get('provenance', {}).get('checker_sha256')
                    and all(audited_plans.get(names[p], {}).get("accepted_slices") == reports[p].get("accepted_slices")
                            and audited_plans.get(names[p], {}).get("verdict") == "OK"
                            and audited_plans.get(names[p], {}).get("exit") == 0 for p in PLANS)
                    and any(line.startswith("COVERAGE (summary only) OK:") for line in audit.get("coverage_lines", [])))
    check("fleet-audit", "G3", audit_ok,
          "G3's fleet-wide audit has not run: no saved fleet-audit.json" if audit is None else
          f"fleet-wide verdict {audit.get('verdict')}, status {(audit.get('audit') or {}).get('status')}" if isinstance(audit, dict)
          else "fleet-wide audit is not a JSON object",
          ["fleet_audit"] + ["judge_" + p for p in PLANS] + ["plan.count"])
    known = [reports[p].get("known") or {} for p in PLANS]
    totals = [k.get("total") for k in known]
    actual = [k.get("predicted_for_accepted") for k in known]
    known_ok = (all(type(x) is int for x in totals + actual) and len(set(totals)) == 1
                and sum(actual) == totals[0] and all(k.get("predicted_for_plan") == k.get("predicted_for_accepted")
                and (k.get("fleet") or {}).get("result") == "OK" and (k.get("fleet") or {}).get("problems") == [] for k in known))
    check("known-control", "G4", known_ok, f"accepted predictions {actual}; required fleet totals {totals}", ["judge_" + p for p in PLANS])
    repro = reports["repro"]
    repro_ok = (repro.get("verdict") == "OK" and repro.get("exit") == 0 and repro.get("missing") == []
                and repro.get("problems") == [] and repro.get("pending") == [] and repro.get("rerun_disagreements") == []
                and repro.get("g4") == {"PASS": repro.get("accepted_copies")}
                and repro.get("accepted_slices") == repro.get("planned"))
    check("reproduction", "G5", repro_ok, f"repro verdict {repro.get('verdict')}, exit {repro.get('exit')}", ["judge_repro"])
    rows = v.get("reruns")
    row_slices = [r.get("slice") for r in rows if isinstance(r, dict)]
    reruns_ok = (len(row_slices) == len(rows) and all(type(i) is int for i in row_slices)
                 and all(rerun_is_accepted(r) for r in rows))
    check("resumed-reruns", "G3", reruns_ok,
          f"saved resumed-slice comparisons {[(r.get('slice'), r.get('verdict')) for r in rows if isinstance(r, dict)]}; "
          "every saved row must be IDENTICAL with passing file comparisons, fresh_from_scratch true and zero fresh recovered cells; "
          f"invalid rows {[r.get('slice') for r in rows if isinstance(r, dict) and not rerun_is_accepted(r)]}",
          ["reruns"])
    resumed_twins(v, reports)
    survivors = {}
    for p in ALL_PLANS:
        for row in reports[p].get("survivors", []):
            graph = row.get("graph6")
            survivors.setdefault(graph, set()).update(row.get("slices", []))
    v.derive("survivor.graphs", [{"graph6": g, "slices": sorted(ss)} for g, ss in sorted(survivors.items(), key=lambda x: str(x[0]))],
             ["judge_" + p for p in ALL_PLANS], "union of survivor graph identities, including nonaccepted observations; deduplicate across plans")
    bundles = v.get("survivor.bundles")
    refuted, problems = set(), []
    for sid in bundles:
        mapping = v.get(sid + ".mapping") or {}
        if not v.get(sid + ".problems"):
            refuted.add(mapping.get("survivor"))
        else:
            problems.extend(v.get(sid + ".problems"))
    missing = [g for g in survivors if not g or g not in refuted]
    measured_kept = sum((reports[p].get("summary", {}).get("record") or {}).get("fleets", [{}])[0]
                        .get("target_cell", {}).get("kept", 0) for p in PLANS)
    credited_survivors = {row.get("graph6") for p in PLANS for row in reports[p].get("survivors", [])
                         if any(c.get("accepted") and not c.get("validation") for c in row.get("copies", []))}
    if measured_kept != len(credited_survivors):
        problems.append(f"target kept measurement {measured_kept} differs from {len(credited_survivors)} credited survivor identities")
    check("survivor-refutations", "G3", not missing and not problems,
          f"unrefuted survivors {missing}; bundle problems {problems}",
          ["survivor.graphs"] + [s + ".problems" for s in bundles] + ["judge_" + p for p in PLANS])
    check("literature", "G0", v.get("g0.exists"), "record exists" if v.get("g0.exists") else "G0 literature note is absent", ["g0.exists"])
    closure = v.get("g1.verdict")
    detail = (f"closure record {v.sources['g1']['file']}: first G1 verdict {closure}" if closure else
              f"G1 closure record {'is absent' if not v.get('g1.exists') else 'has no matching verdict line'}: {v.sources['g1']['file']}; not re-derived by this generator")
    if closure:
        detail += "; basis reported by the closure note: " + v.get("g1.basis_summary")
    check("review-closure", "G1", v.get("g1.exists") and closure == "CLOSED", detail,
          ["g1.exists", "g1.verdict", "g1.basis_summary", "reviews.files"])
    pilot = reports["pilot"]
    pilot_ok = (pilot.get("verdict") == "OK" and pilot.get("exit") == 0 and bool(v.get("pilot.jobs"))
                and sorted(pilot.get("accepted_slices", [])) == sorted(pilot.get("planned", [])))
    check("pilot", "G2", pilot_ok,
          f"pilot verdict {pilot.get('verdict')}; {len(pilot.get('accepted_slices', []))} accepted of {len(pilot.get('planned', []))} planned; u24-pilot section {'exists' if v.get('pilot.jobs') else 'is absent'} in {v.sources['jobs']['file']}",
          ["judge_pilot", "pilot.jobs"])
    tree = v.get("tree")
    check("aggregation", "G6", tree is None or not tree["problems"],
          "per-level table omitted: --root not supplied" if tree is None else f"aggregation problems {tree['problems']}", ["tree"])
    failing = [c for c in checks if not c["ok"]]
    decision = {"headline": "INCOMPLETE" if failing else "COMPLETE", "checks": checks,
                "failing_items": [c["name"] for c in failing], "failing_gates": sorted({c["gate"] for c in failing})}
    v.derive("decision", decision, ["check." + c["name"] for c in checks], "COMPLETE iff every headline predicate holds")
    gate_rows = []
    for gate in v.get("contract.gate_names"):
        cs = [c for c in checks if c["gate"] == gate]
        if gate == "G1":
            status = "met" if cs and all(c["ok"] for c in cs) else "not met"
            detail = "; ".join(c["detail"] for c in cs)
        elif gate == "G6":
            status = "met" if not any(not c['ok'] for c in cs) else "not met"
            detail = "generated from the hashed inputs; fixed-text and conditional-claim lint checked before writing"
        else:
            status = "met" if cs and all(c["ok"] for c in cs) else "not met"
            detail = "; ".join(c["detail"] for c in cs if not c["ok"]) or "; ".join(c["name"] for c in cs)
        gate_rows.append({"gate": gate, "status": status, "detail": detail})
    v.derive("gate_table", gate_rows, ["decision", "contract.gate_names"],
             "every G0..G6 gate must be met; G1 uses the first verdict in its explicit closure record; G2 requires all pilot slices and its JOBS section; G6 subject to lint")
    return decision


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|",
            *["| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in row) + " |" for row in rows]]


def quote(marked):
    return "\n".join("> " + line for line in marked.splitlines())


def render(v, decision):
    S = v.show

    def field(report, *keys, spec=None):
        return S(v.field(report, *keys), spec)

    def derived(key, value, inputs, operation, spec=None):
        v.derive(key, value, inputs, operation)
        return S(key, spec)

    def path(source):
        return "`" + S(v.path(source)) + "`"

    def heading(n, title):
        return [f"## {S('section.' + str(n))}. {title}", ""]

    n = S("claim.n", "d")
    cell = "(" + n + "," + S("claim.top", "d") + ")"
    conditional = f"If the gates of Section {S('section.6')} are all green, u({n}) = {S('claim.lower')}."
    out = [f"# u({n}): the {cell} enumeration (draft for the human)", "",
           "Generated " + S("generated_utc") + " by `" + S("generator.destination") + "`.", "",
           "Every displayed number and status is extracted from the hashed evidence or derived from it. "
           "The generation time is metadata. The accompanying `result-values.json` records each value, its source "
            "file and digest, and every derivation. The counted-copy source manifest is `" + S("tree.source_file") +
            "`, SHA digest `" + S("tree.source_digest") + "`. This draft is for human review.", "",
           "**Headline: " + field("decision", "headline") + ".** " + conditional, ""]
    if decision["failing_items"]:
        out += ["Items that prevent the headline from closing:", ""]
        for c in decision["checks"]:
            if not c["ok"]:
                out.append("- **" + field("check." + c["name"], "gate") + "**: " + field("check." + c["name"], "detail") + ".")
        out.append("")
    out += heading(1, "Statement and dependencies")
    out += ["A TU gadget is a totally unfaithful graph: a distinguished non-edge has unit length in every "
            "unit-distance embedding. At an induced ancestor this forces an extra edge at the target; the "
            "proved upper bound rules out that target. See " + path("pruning") + ".", "",
            "The receipt label `" + S("replay.receipt_label") + "` means the independent augmentation replay, "
            "which samples " + S("replay.percent", ".1f") + "% of the augmentation work. Replay, sampling and "
            "replay verdict references in the quoted historical material use that receipt meaning. Gate " +
            field("contract.gate_names", 4) + " means the known-graph control: eligible graphs from known point "
            "configurations must be generated once and must never be pruned. The two checks have different scopes.", "",
            "The contract's claim and dependencies, verbatim:", "", quote(S("contract.section0")), "",
            conditional + " The claim depends on the inputs below.", "",
            "Both preceding results are this programme's own results, neither yet independently published: " + path("u23") + "; " +
            path("u22") + ". Their values used by the contract are respectively " +
            S("dependency.u23") + " and " + S("dependency.u22") + ".", "",
            "The following dependencies are quoted from the preceding result:", ""]
    out += [quote(S("dependency." + key)) for key in ("amp", "forbidden", "gadgets", "lemmas")]
    out += ["", "The forbidden-graph file read here is " + path("forbidden") + ", SHA digest `" + S(v.digest("forbidden")) + "`. "
            "The TU gadget file is " + path("gadgets") + ", SHA digest `" + S(v.digest("gadgets")) + "`.", "",
            "For the survivor, the dependency is the individual refutation record and the frozen checker, " + path("gp11_checker") +
            ", SHA digest `" + S(v.digest("gp11_checker")) + "`. The survivor argument requires neither the " +
            S("gp.name") + " classification (the census of minimal non-unit-distance graphs on " + S("gp.order_word") +
            " vertices) nor its full final census check. The certificate establishes a refuted subgraph; "
            "a unit-distance embedding of the survivor would restrict to an embedding of that subgraph.", ""]
    out += heading(2, "What the candidate graph would have to be")
    out += ["The reach table records the ancestor vertex-and-edge cells and minimum-degree bounds that can "
            "still lead to the target, using the known extremal values u(j).", "",
            "The contract's structural requirements, verbatim:", "", quote(S("contract.section1")), ""]
    out += heading(3, "The enumeration")
    out += ["Canonical augmentation by minimum-degree deletion gives each candidate a unique construction "
            "path from its canonical parent. Record-hash slicing at the slice level partitions that tree. "
            "The reach table bounds every ancestor cell that can lead to the target using the known u(j). "
            "Forbidden-subgraph exclusions, certificate refutations and the rules justified by Lemmas R and T "
            "apply hereditarily, because every subgraph of a unit-distance graph is unit-distance. A TU gadget "
            "in an induced ancestor forces an extra unit distance on a non-edge of the target, contradicting "
            "its proved upper bound, so that rule also excludes descendants soundly. Details are in " +
            path("pruning") + " and " + path("u23") + ".", "",
            "The contract's enumeration parameters, verbatim:", "", quote(S("contract.section2")), "",
            "The contract's standard, including the limits of reproduction, verbatim:", "", quote(S("contract.section3")), "",
            "Reproduction is by sample, not of every slice. The in-process checks before deletion and the "
            "independent replay are the contract's standard. Re-running the same program establishes reproducibility; "
            "it does not establish the program's correctness.", "",
            "The pilot deployment record is " + path("jobs") + ", entry `" + field("judge_pilot", "provenance", "plan", "job") + "`. The judged snapshot has " +
            S("fleet.branches") + " branch/commit rows in " + path("fleet_sources") + "; " + path("original_readme") +
            " records the snapshot procedure and frozen checker, and " + path("judge_readme") +
            " records the final re-judge and receipt audit. The generator reads those saved reports.", ""]
    out += heading(4, "What the run produced")
    out += ["The filter-only prune applies the sound forbidden-subgraph, gadget and structural filters and "
            "keeps every graph they leave undecided. Surviving that filter does not certify a unit-distance embedding.", ""]
    rows = []
    for p in ALL_PLANS:
        report = "judge_" + p
        j = v.get(report)
        job = v.field(report, "provenance", "plan", "job")
        planned = derived(report + ".planned_count", len(j["planned"]), [report], "length of planned slices")
        accepted = derived(report + ".accepted_count", len(j["accepted_slices"]), [report], "length of accepted_slices")
        duplicate = derived(report + ".duplicate_count", len(j["duplicates"]), [report], "number of slice keys with duplicate accepted copies")
        rows.append([S(job), field(report, "verdict"), field(report, "exit"), planned, accepted,
                     field(report, "accepted_copies"), duplicate, field(report, "prefix_files"),
                     derived(report + ".g4_text", "; ".join(f"{status} {number:,}" for status, number in j["g4"].items()),
                             [report], "format each replay status followed by its copy count")])
    out += table(["plan", "verdict", "exit", "planned slices", "accepted slices", "accepted copies", "duplicate slices", "prefix files", "independent augmentation replay"], rows)
    out += ["", "The coverage partition uses the coverage plans only; the reproduction copies add no new slices. "
            "Duplicate and validation copies do not multiply the count. The partition check and each headline "
            "predicate are recorded in the values file.", ""]
    tree = v.get("tree")
    out += ["### The tree above the slice level", ""]
    if tree is None:
        out += ["The per-level table is omitted because `--root` was not supplied. The saved judge reports "
                "do not contain a whole-fleet per-level aggregate.", ""]
    elif tree["problems"]:
        out += ["The per-level table is omitted because the optional snapshot did not validate: " +
                field("tree", "problems") + ".", ""]
    else:
        out += ["Over " + field("tree", "counted_copies") + " counted copies, using each coverage plan's "
                "`cost.chosen` source. Counts are summed by cell and level, and checked against each chosen "
                "summary and the prune accounting identities. The snapshot path and every selected file hash "
                "are in the compressed source manifest named above.", ""]
        rows = []
        for i, row in enumerate(tree["levels"]):
            vals = []
            for k in ("level", "window", "cells", "children", "kept", "pruned", "tu", "tri_tu", "tri_refuted", "refuted", "pruned_percent"):
                if k not in row:
                    row[k] = 0
                vals.append(field("tree", "levels", i, k, spec=".1f" if k == "pruned_percent" else None))
            rows.append(vals)
        out += table(["level", "window", "cells", "children", "kept", "pruned", "tu", "tri_tu", "tri_refuted", "refuted", "% pruned"], rows)
        out += ["", "Kept at the target means kept by the filter-only prune. The survivor record below decides "
                "those graphs. This aggregation reads retained counts and summaries; it does not replay "
                "certificates or prove enumeration completeness independently.", ""]
    out += ["### The survivor and its refutation", ""]
    graphs = v.get("survivor.graphs")
    out += ["Distinct survivor identities across the judge reports: " +
            derived("survivor.count", len(graphs), ["survivor.graphs"], "deduplicated survivor identities") + ". " + path("survivor_note") +
            " is the narrative note; the final judge reports decide coverage here.", ""]
    for i, graph in enumerate(graphs):
        out += ["- Slice(s) " + field("survivor.graphs", i, "slices") + ": ``" + field("survivor.graphs", i, "graph6") + "``."]
    out.append("")
    for sid in v.get("survivor.bundles"):
        mapping = v.get(sid + ".mapping")
        out += ["Bundle " + path(sid + ".mapping") + "; check output " + path(sid + ".output") + ".", ""]
        if isinstance(mapping, dict) and sid + ".pattern_size" in v.v:
            out += ["Pattern ``" + field(sid + ".mapping", "pattern") + "`` has " + field(sid + ".pattern_size", 0) +
                    " vertices and " + field(sid + ".pattern_size", 1) + " edges. Packet `" + field(sid + ".mapping", "gp11_packet") +
                    "`; record " + path(sid + ".record") + ", SHA digest `" + S(v.digest(sid + ".record")) + "`. "
                    "The generator checks injectivity and every pattern edge against the survivor, and checks "
                    "the record's graph identity and hash. It reads the saved frozen-checker acceptance below.", ""]
            if sid + ".certificate" in v.v:
                cert = v.get(sid + ".certificate")
                if cert["type"] == "real-dag" and cert["sos"]:
                    out += ["Its `" + field(sid + ".certificate", "type") + "` certificate uses " +
                            field(sid + ".certificate", "rows") + " exact rational polynomial identities to derive "
                            "a polynomial equal to a positive constant plus " + field(sid + ".certificate", "squares") +
                            " positively weighted squares, which cannot vanish at a real embedding; see " + path("gp10_format") +
                            ", inherited by " + path("gp11_format") + ", and " + path("gp10_checker") +
                            " (`regenerate`, `algebra_dag` and `real_no_zero`).", ""]
                else:
                    out += ["The record declares certificate type `" + field(sid + ".certificate", "type") +
                            "`; consult " + path("gp10_format") + " and " + path("gp11_format") +
                            " for that type's mathematical format. This generator does not replay the certificate.", ""]
        output = v.get(sid + ".output")
        if output:
            out += ["```text", S(sid + ".output").rstrip(), "```", ""]
        if sid + ".blind_counts" in v.v:
            counts = sid + ".blind_counts"
            search = sid + ".blind_search"
            out += ["The blind search, " + path(sid + ".search") + ", found " + field(search, "embedded") + " " + S("gp.name") +
                    "-refuted graphs on " + S("gp.order_word") + " vertices embedded in the survivor, out of " +
                    field(search, "patterns") + " supplied records; any one suffices. The blind second check, " +
                    path(sid + ".blind_note") + " and " + path(sid + ".blind") + ", reports that the frozen checker accepts " +
                    field(counts, "accepted") + " of " + field(counts, "originals") + " original records, and rejects " +
                    field(counts, "rejected") + " of " + field(counts, "damaged") + " damaged records. "
                    "It used the same frozen checker. The independent work was the subgraph search and the "
                    "mapping checks, rather than another certificate-checker implementation.", ""]
    out += ["### Coverage, histories and cost", ""]
    rows = []
    for p in PLANS:
        report = "judge_" + p
        rows.append([field(report, "provenance", "plan", "job"), field(report, "summary", "status"),
                     field(report, "summary", "missing_slices"), field(report, "resumed_copies"),
                     field(report, "resumed_slices"), field(report, "validation_count"), field(report, "validation_copies")])
    out += table(["plan", "per-plan summary", "slices outside plan", "resumed accepted copies", "resumed slices", "validation requested", "validation accepted"], rows)
    out += ["", "Each per-plan summary intentionally lacks the other plans' slices. Its per-slice status "
            "does not substitute for the fleet-wide summary audit. A summary-only audit reads structural "
            "records and counts; it cannot re-prove the certificate-to-keep relation after intermediate "
            "files have been deleted. That relation rests on the worker's in-process checks before deletion.", ""]
    if not isinstance(v.get("fleet_audit"), dict):
        out += [field("check.fleet-audit", "detail") + ".", ""]
    else:
        out += ["Fleet-wide report " + path("fleet_audit") + ": verdict " + field("fleet_audit", "verdict") +
                ", status " + field("fleet_audit", "audit", "status") + ", exit " + field("fleet_audit", "exit") + ".", ""]
        if v.get("fleet_audit").get("coverage_lines"):
            out += ["```text", derived("audit.coverage_text", "\n".join(v.get("fleet_audit")["coverage_lines"]), ["fleet_audit"], "coverage_lines joined verbatim"), "```", ""]
    full = v.get("judge_full")
    out += ["The judge records " + field("judge_full", "rerun_count") + " requested rerun slice/tag pairs and " +
            field("judge_full", "rerun_copies") + " retired rerun copies. These are histories, distinct from "
            "the fresh comparisons below. Superseded and validation decisions are retained in each JSON report.", ""]
    out += ["Rerun requests grouped by the reason's leading clause, before its first parenthesis or semicolon:", ""]
    out += table(["reason leading clause", "requested slice/tag pairs", "lead seconds range"],
                 [[field("history.reason_groups", i, key) for key in ("why", "requests", "lead_seconds_range")]
                  for i in range(len(v.get("history.reason_groups")))])
    out += ["", "The full verbatim reason list and each reason's count are retained in `result-values.json` under `history.reasons`.", "",
            "The grouped counts sum to " + S("history.grouped_requests") + "; the judge's requested pairs are " +
            field("judge_full", "rerun_count") + ". Their equality is a headline predicate.", ""]
    for i, row in enumerate(full["rerun_disagreements"]):
        number = row["slice"]
        why = [r["why"] for r in full["provenance"]["plan"].get("rerun", []) if r.get("slice") == number]
        chosen = full.get("cost", {}).get("chosen", {}).get(str(number), {}).get("source")
        differences = "\n".join(row["differences"])
        legacy = any("legacy" in text.lower() and "resum" in text.lower() for text in why)
        cells = row.get("cells") or row.get("differing_cells")
        has_cells = cells is not None or bool(re.search(r"\bcell\b|\(\s*\d+\s*,\s*\d+\s*\)", differences))
        explanation = ("The earlier copy was resumed under the legacy supervisor and disagrees on counts with the from-scratch rerun. "
                       if legacy and "counts" in differences else "The judge records a retired-copy disagreement. ")
        explanation += ("The disagreement record names cells: " + canonical(cells) + ". " if cells is not None else
                        "The cell details appear in the quoted differences. " if has_cells else
                        "The disagreement record does not name the differing cells. ")
        explanation += ("The counted copy is the rerun. " if chosen == row.get("new_copy") else
                        "The counted-copy selection does not identify this rerun. ")
        if legacy:
            explanation += "This is why every legacy-resumed copy was rerun before judging."
        out += ["At slice " + field("judge_full", "rerun_disagreements", i, "slice") + ", the earlier copy is `" +
                field("judge_full", "rerun_disagreements", i, "old_copy") + "` and the rerun is `" +
                field("judge_full", "rerun_disagreements", i, "new_copy") + "`. " +
                derived("history.explanation." + str(i), explanation, ["judge_full", "resume.policy"],
                        "match disagreement to plan reason and cost.chosen; identify cell details only if the disagreement record names them"), "",
                "The judge's differences, verbatim:", "", quote(field("judge_full", "rerun_disagreements", i, "differences")), "",
                "The plan's reason:", "", quote(derived("history.why." + str(i), "\n".join(why), ["judge_full"],
                    "rerun why strings at the disagreement slice, verbatim")), ""]
    rows = []
    for p in PLANS:
        report = "judge_" + p
        rows.append([field(report, "provenance", "plan", "job"), *[field(report, "cost", "observed", k) for k in
                     ("step_seconds", "run_dag2_seconds", "g4_seconds", "check_seconds", "control_seconds", "evidence_seconds")]])
    out += table(["plan", "step seconds", "run clock seconds", "replay seconds", "check seconds", "control seconds", "evidence seconds"], rows)
    out += ["", "These are the judge's observed sums over its selected copies. They are not an elapsed "
            "fleet duration or a total including failed attempts. The rule is:", "", quote(field("judge_pilot", "cost", "rule")), "",
            "The judge's cost limits:", "", *[quote(field("judge_pilot", "cost", "notes", i)) for i in range(len(v.get("judge_pilot")["cost"]["notes"]))], ""]
    out += heading(5, "Cross-checks that were actually run")
    out += ["### Independently measured retained files", "",
            "The independent scans measured retained level files against their recorded hashes and manifests. "
            "The saved summaries and coverage of enumeration stage manifests follow. This generator reads "
            "the reports; it does not rerun the scans.", ""]
    for sid in v.get("retained_scan.reports"):
        out += ["Saved scan " + path(sid) + ":", "", "```text", S(sid + ".summary")]
        if v.get(sid + ".coverage") is not None:
            out += [S(sid + ".coverage")]
        out += ["```", ""]
    audit = v.get("fleet_audit")
    fleets = ((audit.get("audit") or {}).get("record") or {}).get("fleets", []) if isinstance(audit, dict) else []
    if fleets and isinstance(fleets[0].get("slice_partition"), dict):
        shares = fleets[0]["slice_partition"]
        v.derive("fleet.share_cells", sorted(shares, key=int), ["fleet_audit"], "slice-level edge cells in the complete fleet audit")
        out += ["The fleet audit's slice-share sums and unsliced stage totals:", ""]
        rows = [[field("fleet.share_cells", i), field("fleet_audit", "audit", "record", "fleets", 0, "slice_partition", key, "sum"),
                 field("fleet_audit", "audit", "record", "fleets", 0, "slice_partition", key, "stage_file")]
                for i, key in enumerate(v.get("fleet.share_cells"))]
        out += table(["slice-level edge cell", "slice-share sum", "unsliced stage total"], rows) + [""]
    rows = []
    for p in PLANS:
        report = "judge_" + p
        rows.append([field(report, "provenance", "plan", "job"), field(report, "known", "predicted_for_plan"),
                     field(report, "known", "predicted_for_accepted"), field(report, "known", "total"), field(report, "known", "fleet", "result")])
    out += table(["plan", "plan prediction", "accepted prediction", "fleet total", "per-plan control"], rows)
    out += ["", "The accepted predictions sum explicitly, in pilot, full, phase B order: " +
            " + ".join(field("judge_" + p, "known", "predicted_for_accepted") for p in PLANS) + " = " +
            derived("known.sum", sum(v.get("judge_" + p)["known"]["predicted_for_accepted"] for p in PLANS),
                    ["judge_" + p for p in PLANS], "sum accepted known predictions in pilot, full, phase B order") +
            "; the fleet total is " + field("judge_pilot", "known", "total") + ". " +
            derived("known.conclusion", "Every eligible known configuration lies in the slice predicted for it and was found there, unpruned."
                    if v.get("check.known-control")["ok"] else "The saved known-graph control does not establish completion of the union.",
                    ["check.known-control"], "conclusion only when every plan's known control and the fleet sum pass"), "",
            "The known-graph headline predicate requires each accepted prediction to equal its plan prediction, "
            "and the coverage plans' accepted predictions to sum to the common fleet total. Individual "
            "per-plan controls cover subsets; their completion flags do not certify the union by themselves.", "",
            "The reproduction sample has " + field("judge_repro", "accepted_count") + " accepted slices and " +
            field("judge_repro", "accepted_copies") + " accepted copies. The published draw is:", "",
            quote(field("judge_repro", "provenance", "plan", "random_draw")), "",
            "Chosen heavy slices: " + field("judge_repro", "provenance", "plan", "chosen", "heavy") + ". "
            "The judge compares accepted production and reproduction copies. Reproduction is by sample, "
            "not of every slice.", "",
            "### Resumed copies and their from-scratch twins", "",
            "The legacy supervisor relaunched workers in the same container. It could leave simultaneous writers "
            "and reuse an interrupted partial line. The tree-kill time-slice supervisor kills the process tree, "
            "quarantines partial files, and resumes valid checkpoints. The full plan's resumed copies use the "
            "legacy mechanism; the pilot and phase B resumed copies use the tree-kill mechanism. The source "
            "describes the holes and their repair:", "", quote(S("resume.mechanisms")), "",
            "The policy sentences, verbatim, at `" + S("resume.policy_location") + "`:", "", quote(S("resume.policy")), "",
            "A rerun counts as a twin only when its saved row explicitly says it ran from scratch and "
            "reports no fresh recovered cells. A reproduction comparison counts only when the chosen "
            "copy's resumed-cell count is recorded as zero. A resumed candidate is shown below and does not count.", "",
            "Every resumed accepted copy and its comparison:", ""]
    out += table(["plan", "slice", "accepted copy", "resume mechanism", "from-scratch twin"],
                 [[field("resume.twins", i, key) for key in ("plan", "slice", "source", "mechanism", "twin")]
                  for i in range(len(v.get("resume.twins")))])
    missing = v.get("resume.missing")
    out += ["", "Resumed accepted copies with no recorded from-scratch twin:", ""]
    if missing:
        for i, row in enumerate(missing):
            out += ["- " + field("resume.missing", i, "plan") + ", slice " + field("resume.missing", i, "slice") +
                    ": `" + field("resume.missing", i, "source") + "`."]
    else:
        out += [derived("resume.missing_text", "None: every resumed accepted copy has a recorded twin.",
                        ["resume.missing"], "empty missing-twin list")]
    out += ["", "A missing twin is listed here and does not fail a gate. Every saved rerun row must show "
            "identical file comparisons, a passing fresh receipt and explicit from-scratch freshness. "
            "Fresh comparisons are read from:", ""]
    for index in range(len(v.get("reruns.files"))):
        out += ["- " + field("reruns.files", index) + "."]
    out.append("")
    rows = []
    for i, row in enumerate(v.get("reruns")):
        if isinstance(row, dict):
            freshness = []
            for key in ("kept_recovered_cells", "fresh_recovered_cells", "fresh_from_scratch"):
                name = f"reruns.{i}.{key}"
                if key not in row:
                    sid, line = v.rerun_locations[i]
                    v.put(name, None, sid, f"JSONL line {line}, field {key} absent")
                freshness.append(S(v.field("reruns", i, key)) if key in row else S(name))
            rows.append([field("reruns", i, "slice"), field("reruns", i, "kept_tag"), field("reruns", i, "fresh_tag"),
                         field("reruns", i, "verdict"), field("reruns", i, "cells"), field("reruns", i, "hashed_files"), *freshness])
    out += table(["slice", "counted tag", "fresh tag", "verdict", "cells", "hashed files", "kept recovered cells",
                  "fresh recovered cells", "fresh from scratch"], rows)
    out += ["", "These comparisons cover every cell's `counts.json`, the retained-file hashes, `reach.json`, "
            "`run-config.json`, and the known-graph record with its machine-local `run` field removed. "
            "They require the fresh receipt's passing verdict and zero recovered cells in its structure. Deleted intermediate files cannot be compared "
            "byte for byte. Structure and inventory records are excluded because their retained-file lists "
            "differ by runbook version. The comparison procedure is described in `tools/rerun_compare.py`.", ""]
    out += heading(6, "Gates")
    out += ["The contract's gate requirements, verbatim:", "", quote(S("contract.section4")), ""]
    rows = [[field("gate_table", i, k) for k in ("gate", "status", "detail")] for i in range(len(v.get("gate_table")))]
    out += table(["gate", "status here", "evidence or remaining item"], rows)
    out += ["", "The literature verdict recorded in " + path("g0") + ": " + S("g0.verdict") + " "
            "This generator reads the literature note; it does not repeat its searches.", "",
            "The closure input is " + path("g1") + "; its first matching verdict is " + S("g1.verdict") +
            ". The basis stated by that file is:", "", S("g1.basis_summary"), "",
            "The generator reads the closure record and does not repeat its targeted verification. "
            "Historical (deleted-content) fields rest on the worker's check before deletion. The saved audit "
            "cannot re-measure deleted files; the field enumeration states those limits row by row. "
            "Without an explicit final closure record, closure is not re-derived by this generator. "
            "The historical review files are:", ""]
    out += ["- " + field("reviews.files", i) + "." for i in range(len(v.get("reviews.files")))]
    out.append("")
    out += heading(7, "What is claimed, and what is not")
    out += [conditional + " This condition includes the mathematical and software dependencies stated "
            "above, including our own preceding results and the review gate. The generated headline "
            "summarizes the saved evidence predicates; it does not independently discharge those dependencies.", "",
            "The individual survivor certificate does not establish a complete classification of graphs "
            "of its order. The summary audit does not reconstruct deleted intermediate certificate files. "
            "Enumeration correctness continues to depend on the reviewed augmentation and pruning "
            "programs, their checkers, the common canonical-labelling software, and the stated mathematical lemmas.", ""]
    out += heading(8, "How to check it")
    out += ["The " + S("rejudge.original_date") + " reports in " + path("original_readme") +
            " are the original judge of this snapshot. The " + S("rejudge.label") + " reports in " + path("judge_readme") +
            " are the re-judge with the final receipt audit. " +
            derived("rejudge.conclusion", "They use the same branch/commit snapshot and are identical in every key field."
                    if v.get("check.rejudge-equality")["ok"] else
                    "The saved reports do not establish the same snapshot and equality of every key field.",
                    ["check.rejudge-equality"], "state key-field identity only when every report pair and the snapshot sources agree"), "",
            "The compared JSON keys are " + S("rejudge.key_fields") + "; equality is a headline predicate. "
            "Read both READMEs for the snapshot's branch commits, audit history and judge commands. "
            "Read the contract, the source JSON reports and the saved survivor check. Recompute the file "
            "digests listed in `result-values.json` and its compressed source manifest. These commands "
            "are reproduction instructions; this generator reads saved reports and does not run the judge "
            "or the enumeration. Use a disposable repository checkout and writable output directories.", "",
            "Build ROOT from " + path("fleet_sources") + " by the procedure in " + path("original_readme") + ": fetch each recorded "
            "commit and extract its result directory under the branch suffix. This command template assumes "
            "ROOT is an empty directory whose absolute path the caller supplies:", "", "```sh",
            derived("command.snapshot", '\n'.join([
                'mkdir -p "$ROOT"',
                'while IFS="$(printf \'\\t\')" read -r branch fetched advertised; do',
                '  git fetch origin "$fetched"',
                '  case "$branch" in',
                '    *cloud-u24-*) suffix=${branch##*cloud-u24-} ;;',
                '    *codex-u24-*) suffix=codex-${branch##*codex-u24-} ;;',
                '    *) exit 1 ;;',
                '  esac',
                '  mkdir -p "$ROOT/$suffix"',
                '  git archive "$fetched" research/unit-distance-24/results/u24 | tar -x -C "$ROOT/$suffix"',
                'done < ' + v.sources["fleet_sources"]["file"]]),
                [v.path("fleet_sources"), v.path("original_readme")], "shell template of original README extraction procedure; uses exact fetched commits"),
            "```", "", "Judge each published plan, then audit the union and run the audit's mutation tests:", "", "```sh"]
    for p in ALL_PLANS:
        report = "judge_" + p
        job = v.get(report)["provenance"]["plan"]["job"]
        out += [derived("command.judge." + p, 'nice -n 15 /usr/bin/python3 -B ' +
                        v.sources["tool.judge.py"]["file"] + ' "$ROOT" --plan coordination/cloud-workers/' +
                        job + '-plan.json --out judge-' + p + '.json',
                        [v.path("tool.judge.py"), v.field(report, "provenance", "plan", "job"), v.path("judge_readme")],
                        "judge invocation for the published plan; output outside ROOT")]
    for name, suffix in (("fleet_audit.py", ' "$ROOT" --out fleet-audit.json'), ("test_fleet_audit.py", " -v")):
        prefix = "nice -n 15 /usr/bin/python3 -B " if name == "fleet_audit.py" else "nice -n 15 timeout 1800 /usr/bin/python3 -B "
        out += [derived("command." + name, prefix + v.sources["tool." + name]["file"] + suffix,
                        [v.path("tool." + name)], "saved tool's command-line interface")]
    out += ["```", "", "Fresh-copy source addresses are in " + path("fresh_copies") + ", SHA digest `" +
            S(v.digest("fresh_copies")) + "`. The values file binds each comparison's tag and slice to the "
            "manifest's branch, commit, receipt path, receipt digest and structure digest:", ""]
    out += table(["fresh tag", "branch", "commit"],
                 [[field("fresh.tags", i), field("fresh.bindings", "tags", tag, "branch"),
                   field("fresh.bindings", "tags", tag, "commit")] for i, tag in enumerate(v.get("fresh.tags"))])
    if v.get("fresh.bindings")["unbound"]:
        out += ["", "Comparison addresses absent from the saved manifest: " + field("fresh.bindings", "unbound") + "."]
    out += ["", "Extract the immutable fresh commits in a disposable checkout, then verify their saved receipt "
            "and structure digests. The template sets the FRESH tag variables used by the comparisons:", "", "```sh"]
    extract = '\n'.join([
        'export FRESH_WORK="$PWD/fresh-copies"',
        'mkdir -p "$FRESH_WORK"',
        'nice -n 15 timeout 1800 /usr/bin/python3 -B - <<\'PY\' > "$FRESH_WORK/sources.tsv"',
        'import json', 'from pathlib import Path',
        'manifest = json.loads(Path(' + repr(v.sources["fresh_copies"]["file"]) + ').read_text())',
        'for tag, address in sorted(manifest["tags"].items()):',
        '    print(tag, address["branch"], address["commit"], sep="\\t")',
        'PY',
        'while IFS=$\'\\t\' read -r fresh_tag fresh_branch fresh_commit; do',
        '  git fetch origin "$fresh_branch"',
        '  mkdir -p "$FRESH_WORK/$fresh_tag"',
        '  git archive "$fresh_commit" research/unit-distance-24/results/u24 | tar -x -C "$FRESH_WORK/$fresh_tag"',
        '  export "FRESH_${fresh_tag}_ROOT=$FRESH_WORK/$fresh_tag/research/unit-distance-24/results/u24"',
        'done < "$FRESH_WORK/sources.tsv"',
        'nice -n 15 timeout 1800 /usr/bin/python3 -B - <<\'PY\'',
        'import hashlib, json, os', 'from pathlib import Path',
        'manifest = json.loads(Path(' + repr(v.sources["fresh_copies"]["file"]) + ').read_text())',
        'for tag, address in manifest["tags"].items():',
        '    base = Path(os.environ["FRESH_WORK"]) / tag',
        '    for record in address["slices"].values():',
        '        receipt = base / record["receipt"]',
        '        assert hashlib.sha256(receipt.read_bytes()).hexdigest() == record["receipt_sha256"]',
        '        structure = receipt.with_suffix(".structure.json")',
        '        assert hashlib.sha256(structure.read_bytes()).hexdigest() == record["structure_sha256"]',
        'PY'])
    out += [derived("command.fresh_extract", extract, ["fresh.bindings", v.path("fresh_copies"), "generator.destination"],
                    "extract exact manifest commits and verify every fresh receipt and structure digest; never executed by this generator"),
            "```", "", "Compare every saved rerun row and run its mutation control. Each FRESH tag variable "
            "below names that rerun's extracted result directory, as distinct from the whole snapshot ROOT. "
            "Use the source addresses above:", "", "```sh"]
    for i, row in enumerate(v.get("reruns")):
        if not isinstance(row, dict) or not all(k in row for k in ("slice", "kept_tag", "fresh_tag")):
            continue
        sources = [r["source"] for p in PLANS for r in v.get("judge_" + p).get("cost", {}).get("rows", {}).get(str(row["slice"]), [])
                   if r.get("accepted") is True and r["source"].endswith("-" + row["kept_tag"] + ".txt")]
        kept = ('"$ROOT/' + str(Path(sorted(sources)[0]).parent.parent) + '"') if sources else '"$KEPT_ROOT"'
        call = f'{row["slice"]} {kept} {row["kept_tag"]}'
        base = "nice -n 15 timeout 1800 /usr/bin/python3 -B " + v.sources["tool.rerun_compare.py"]["file"]
        commands = base + " " + call + ' "${FRESH_' + row["fresh_tag"] + '_ROOT}" ' + row["fresh_tag"] + "\n" + base + " --self-test " + call
        out += [derived("command.rerun." + str(i), commands,
                        [v.field("reruns", i), v.path("tool.rerun_compare.py")] + ["judge_" + p for p in PLANS],
                        "compare and self-test each JSONL row; locate kept root by accepted receipt and kept tag; fresh roots supplied by caller")]
    if not v.get("reruns"):
        out += [derived("command.rerun.empty", "No saved rerun rows supply comparison commands.", ["reruns"], "empty row list")]
    out += ["```", "", "Check the survivor with the frozen checker's Python environment, named CHECKER_PYTHON:", "", "```sh"]
    for sid in v.get("survivor.bundles"):
        out += [derived("command.survivor." + sid, 'nice -n 15 timeout 1800 "$CHECKER_PYTHON" -B ' + v.sources[sid + ".script"]["file"],
                        [v.path(sid + ".script")], "external survivor checker invocation; dependencies from its frozen environment")]
    out += ["```", "", "For the blind check, copy the complete supplied bundle named in its report into "
            "BLIND_WORK, including the supplied records and survivor graph file. Its scripts resolve inputs beside themselves "
            "and write outputs there. Use its Python environment with NetworkX; the certificate script uses "
            "the frozen checker environment and filesystem isolation recorded in the bundle:", "", "```sh"]
    for sid in v.get("survivor.bundles"):
        for name in ("blind_check.py", "run_certificates.py"):
            out += [derived("command.blind." + sid + "." + name, 'nice -n 15 timeout 1800 "$CHECKER_PYTHON" -B "$BLIND_WORK/' + name + '"',
                            [v.path(sid + "." + name), v.path(sid + ".blind_note")],
                            "run copied blind script with its inputs in a writable complete bundle; script's paths/environment must match its recorded originals")]
    out += ["```", "", "Generate the write-up and run its evidence-mutation suite. The last test regenerates "
            "from the untouched real inputs and compares the document, compact values and deterministic "
            "source sidecar with the first generation, apart from the generation timestamp:", "", "```sh",
            derived("command.generate", 'nice -n 15 timeout 1800 /usr/bin/python3 -B ' + v.get("generator.destination") + ' --repo . --root "$ROOT"',
                    ["generator.destination"], "installed generator invocation; ROOT supplied by caller"),
            derived("command.generator_tests", 'U24_TEST_REPO="$PWD" U24_TEST_ROOT="$ROOT" nice -n 15 timeout 1800 /usr/bin/python3 -B ' +
                    str(Path(v.get("generator.destination")).with_name("test_write_result.py")) + " -v",
                    ["generator.destination", v.path("generator_tests")], "installed unittest invocation with real repo and snapshot"), "```", "",
            "The default reads the saved survivor output. `--live-survivor --checker-python PYTHON` "
            "runs the existing checker script in a read-only filesystem with writable scratch under the "
            "output directory. Use the frozen checker's Python environment for that external command.", ""]
    return "\n".join(out).rstrip() + "\n"


def options(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", type=Path, default=REPO)
    p.add_argument("--root", type=Path)
    for flag in ("evidence", "original-evidence", "contract", "g0", "g1", "jobs", "fleet-audit", "u23-result", "u22-result", "forbidden",
                 "gadgets", "pruning", "gp11-checker", "gp10-checker", "gp10-format", "gp11-format", "fresh-copies",
                 "survivor-output", "out", "values", "sources"):
        p.add_argument("--" + flag, type=Path)
    p.add_argument("--reruns", type=Path, action="append", nargs="+",
                   help="one or more JSONL files; repeatable; default: discover every rerun-resumed-*.jsonl")
    p.add_argument("--retained-scan", type=Path, action="append", nargs="+",
                   help="saved retained-scan text files; repeatable; default: both final retained scans")
    for plan in ALL_PLANS:
        p.add_argument("--judge-" + plan, type=Path)
    p.add_argument("--review", type=Path, action="append")
    p.add_argument("--survivor-dir", type=Path, action="append")
    p.add_argument("--live-survivor", action="store_true")
    p.add_argument("--checker-python", type=Path, default=Path("/usr/bin/python3"))
    a = p.parse_args(argv)
    a.repo = a.repo.resolve()
    u = a.repo / "research/unit-distance-24"
    a.evidence = a.evidence or u / "evidence/judge-final-2026-10-07-r2"
    a.original_evidence = a.original_evidence or u / "evidence/judge-final-2026-10-06"
    a.retained_scan = ([path for group in a.retained_scan for path in group] if a.retained_scan else
                       [u / "evidence/retained-scan-2026-10-07.txt", u / "evidence/retained-scan-2026-10-07b.txt"])
    defaults = {"contract": u / "CONTRACT.md",
                "g0": u / "G0-literature-2026-10-06.md", "g1": u / "G1-verification-2026-10-07.md",
                "jobs": a.repo / "coordination/cloud-workers/JOBS.md",
                "fleet_audit": a.evidence / "fleet-audit.json", "u23_result": a.repo / "research/unit-distance-23/RESULT-u23.md",
                "u22_result": a.repo / "research/unit-distance-22/RESULT-u22.md",
                "forbidden": a.repo / "research/unit-distance-22/data/forbidden-398.json",
                "gadgets": a.repo / "research/unit-distance-22/data/tu-gadgets.json",
                "pruning": a.repo / "research/unit-distance-22/enum/PRUNING.md",
                "gp10_checker": a.repo / "research/gp-10/check/gp10check.py",
                "gp10_format": a.repo / "research/gp-10/check/FORMAT.md",
                "gp11_format": a.repo / "research/gp-11/check/FORMAT.md",
                "fresh_copies": u / "evidence/fresh-copies-2026-10-07.json",
                "gp11_checker": a.repo / "research/gp-11/check/gp11check.py", "out": u / "RESULT-u24.md",
                "values": u / "result-values.json"}
    for name, default in defaults.items():
        if getattr(a, name) is None:
            setattr(a, name, default)
    a.sources = a.sources or a.values.parent / "result-sources.json.gz"
    a.reruns = sorted({path.resolve() for group in a.reruns for path in group}) if a.reruns else None
    for plan in ALL_PLANS:
        if getattr(a, "judge_" + plan) is None:
            setattr(a, "judge_" + plan, a.evidence / f"judge-{plan}.json.gz")
    if a.review is None:
        a.review = sorted(u.glob("REPORT-review*-2026-10-01.md")) + sorted(u.glob("REPORT-rereview-fixes-2026-10-01.md"))
    if a.survivor_dir is None:
        a.survivor_dir = [u / "survivor-s50"]
    return a


def generate(a, write=True):
    """Return (markdown, values, decision); output files are written after lint."""
    destinations = [a.out.resolve(), a.values.resolve(), a.sources.resolve()]
    if len(set(destinations)) != len(destinations):
        raise InputError("markdown, values and source-sidecar destinations must differ")
    if a.root and any(p.is_relative_to(a.root.resolve()) for p in destinations):
        raise InputError("outputs must be outside the read-only fleet snapshot")
    v = collect(a)
    # Prevent accidental replacement of any input, including optional absent ones.
    input_paths = {(v.repo / s['file']).resolve() for s in v.sources.values()}
    if any(p in input_paths for p in destinations):
        raise InputError("an output destination is also an input")
    pack_sources(v, a.sources, a.values)
    decision = decide(v)
    marked = render(v, decision)
    problems = lint(marked)
    if problems:
        raise LintError("\n".join(problems))
    v.derive("lint", {"status": "OK", "fixed_text_numerals": 0, "unconditional_claims": 0},
             ["decision", "generator.destination"], "lint final marked document before writing any output")
    doc = strip(marked)
    values = v.export(decision, v.get("tree.source_file"))
    payload = json.dumps(values, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) >= 300_000:
        raise InputError("values exceed the compact evidence ledger size limit")
    if write:
        for path in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
        # No output is opened before all input parsing, decision and lint pass.
        a.sources.write_bytes(v.sidecar)
        a.values.write_text(payload, encoding="utf-8")
        a.out.write_text(doc, encoding="utf-8")
    return doc, values, decision


def main(argv=None):
    try:
        a = options(argv)
        _, _, decision = generate(a)
    except LintError as error:
        print("LINT ERROR: " + str(error), file=sys.stderr)
        return 1
    except (InputError, OSError, subprocess.SubprocessError) as error:
        print("INPUT ERROR: " + str(error), file=sys.stderr)
        return 2
    print("Headline: " + decision["headline"])
    for check in decision["checks"]:
        if not check["ok"]:
            print(check["gate"] + ": " + check["detail"])
    print(f"Written: {a.out}; {a.values}; {a.sources}")
    return 0 if decision["headline"] == "COMPLETE" else 3


if __name__ == "__main__":
    sys.exit(main())
