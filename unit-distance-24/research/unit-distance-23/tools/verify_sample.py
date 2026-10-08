#!/usr/bin/env python3
"""Gate G5's point 6, option 1 (the human's choice): the sampled slices re-run with nothing deleted and checked whole.

usage: python verify_sample.py [--verify-root DIR] [--root FLEET_ROOT] [--fetch] [--jobs FILE] [--self-test]

The plan is the ## u23-verify entry of coordination/cloud-workers/JOBS.md: the restarted slices, the random sample
(recomputed here from the stated rule, random.Random(SEED).sample(the other slices, ascending, K), which must give the
listed slices), and the table of workers and their slices. Every planned slice needs both of these:
  - its worker's check output, research/unit-distance-23/results/u23/verify/s<i>of1920-<tag>.txt on the worker's
    branch, passing when re-derived here from the output itself (the worker's own verdict line is not trusted): the
    worker's first slice checked whole (exit 0, CHAIN OK, "COVERAGE exhaustive"), a later slice from level 13 (exit 3,
    CHAIN PARTIAL with that as its only reason, no PROBLEM line) with its prefix identical to the first slice's; a
    first slice may instead be checked from level 13 when its output declares "whole check skipped" (a machine too
    small for the whole check), its prefix then shown only by hash, the second requirement's prefix comparison with
    the fleet's copy; every inspected pruned cell's certificates replayed; the checker the pinned G5 one (commit and
    sha256);
  - its worker's copy of the slice's result files identical to the fleet's chosen copy of the same slice
    (aggregate_fleet.py's compare_copies: counts rows, shipped level files, the target's kept graphs), with the same
    prefix hashes, software and input hashes (the interpreter's path and version excepted, and reported: v04 ran on the
    local machine's Python 3.12, the fleet on the cloud's 3.11; every script and binary hash is still compared).
Exit 0 only when every planned slice has both; the last line is VERIFY-SAMPLE OK or VERIFY-SAMPLE FAIL.
--fetch first fetches origin's cloud-u23-v* branches (the sample; with --all the full re-run's cloud-u23-a* branches)
into refs/u23verify/, not writing FETCH_HEAD, and extracts each one's results/u23 tree into --verify-root. --self-test then shows every requirement can fail: a copy's counts changed,
a check's CHAIN line changed, a check output removed, a copy removed, and the sample rule under another seed must each
be caught.
"""
import argparse, copy, hashlib, json, random, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import aggregate_fleet as af   # noqa: E402  read_copy, compare_copies, choose: one notion of "the same copy"
import fleet_status as fs      # noqa: E402
import target_check as tc      # noqa: E402  the pinned audit and the G4 scope rules, the same code the fleet's gate runs

REPO = HERE.parents[3]
JOBS = REPO / "coordination/cloud-workers/JOBS.md"
FLEET_ROOT = Path("<scratch>/scratchpad/fleet/results")
VERIFY_ROOT = Path("<scratch>/scratchpad/fleet/verify-results")
G5_COMMIT = "34f0dcb9ba7c980c9931b1374a8a57a8f762edd0"
G5_SHA256 = "d253338569dedb41740cdb4774a6a361f6498f036787a52c3f985caca5d6ddd8"
LEVEL, COUNT, TARGET, SEED = 12, 1920, (23, 65), 10
# the full re-run's plan: 48 Claude cloud workers a01..a48 (JOBS.md, u23-verify-all-claude); the codex plan before it
# (u23-verify-all-plan.json) was abandoned when codex cloud could not return a slice's results
ALL_PLAN = REPO / "coordination/cloud-workers/u23-verify-all-claude-plan.json"
SAMPLE_OUTPUTS = REPO / "research/unit-distance-23/results/u23/verify-sample-outputs.json"
# the branch commit the first codex wave checked out, before u23-verify.sh recorded its files digest (e29124767c)
PRE_DIGEST_COMMIT = "f197cd586741935115f31329bc8811b0c9154dfd"
# run-dag2.py: the fleet ran FLEET_RUNDAG; the full re-run runs the branch after the G5 merge (32f04c6da), whose
# run-dag2.py is G5_COMMIT's (the resume checks G5 rounds 1-3 asked for; a fresh run does not resume). Only in --all
# mode, only this file, only this pair of hashes.
FLEET_RUNDAG = "0c6fb31243ab1e69175be3a5bcbf2c2a270749eeaa1b7d0f2e5f60a47abcd3cd"
G5_RUNDAG = "78b66addd192f253a3c26c3509d0747d713c392bf2f14f1a1f4220fa3ca05a51"
FROM = LEVEL + 1
# the memory fallback (u23-verify.sh, 2026-09-27): verify-chain-lean.py, the G5 checker with its memory bounded and
# nothing else changed, run on a run directory whose G5 check was killed for memory; its record is s<i>of1920-<tag>.lean.txt
LEAN_SHA256 = "6658191122188546847b7f13d0413be954bb131491556520ccfd90e8660c30e6"


def plan_from_jobs(text: str) -> dict:
    m = re.search(r"^## u23-verify .*?(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit("JOBS.md has no ## u23-verify entry")
    sec = " ".join(m.group(0).split())
    restarted = re.search(r"The restarted slices \([^)]*\): ([\d ]+)\.", sec)
    rule = re.search(r"random\.Random\((\d+)\)\.sample\(<the other slices, ascending>, (\d+)\)", sec)
    listed = re.search(r"sorted: ([\d ]+)\.", sec)
    table = re.findall(r"\| (v\d\d) \| ([\d ]+) \| \d+ \|", m.group(0))
    if not (restarted and rule and listed and table):
        raise SystemExit("JOBS.md's u23-verify entry: cannot read the restarted slices, the rule, the list or the table")
    workers = {t: [int(x) for x in s.split()] for t, s in table}
    # the sample ran before the files digest existed: exactly its 63 outputs, pinned by sha256, are exempt
    pinned = json.loads(SAMPLE_OUTPUTS.read_text())["outputs"] if SAMPLE_OUTPUTS.exists() else []
    return {"restarted": [int(x) for x in restarted.group(1).split()], "seed": int(rule.group(1)),
            "k": int(rule.group(2)), "random": [int(x) for x in listed.group(1).split()],
            "workers": workers, "pre_digest_sha": sorted(r["sha256"] for r in pinned)}


def plan_from_all(path: Path) -> dict:
    """The u23-verify-all plan: every slice once, task tag -> its slices, the first checked whole. An output is exempt
    from the files digest only by its OWN header: made at PRE_DIGEST_COMMIT, before the digest existed (G5 round 11,
    finding 1: a whole tag was once exempted by any one of its files)."""
    tasks = json.loads(path.read_text())["tasks"]
    return {"all": True, "workers": {t: list(s) for t, s in tasks.items()}, "pre_digest_commit": PRE_DIGEST_COMMIT}


def fetch(root: Path, pattern: str = "v*") -> None:
    out = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/claude/answering-alexeev-u22-cloud-u23-{pattern}"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    for line in filter(None, (x.strip() for x in out)):
        _, ref = line.split()
        name = ref.split("cloud-u23-", 1)[1]
        local = f"refs/u23verify/{name}"
        subprocess.run(["git", "fetch", "-q", "--no-write-fetch-head", "origin", f"+{ref}:{local}"], cwd=REPO,
                       check=True)
        dst = root / name
        dst.mkdir(parents=True, exist_ok=True)
        arch = subprocess.run(["git", "archive", local, "research/unit-distance-23/results/u23"], cwd=REPO,
                              capture_output=True)
        if arch.returncode == 0 and arch.stdout:
            subprocess.run(["tar", "-x", "-C", str(dst)], input=arch.stdout, check=True)


def parse_output(text: str) -> dict:
    """A u23-verify.sh check output: its header and verify-chain's own lines."""
    lines = text.splitlines()
    head = {}
    for pat, key in ((r"^# u23-verify (\w+), slice s(\d+)of(\d+), checked (.*?): verify-chain-(?:g5|lean)\.py (.*?) --expect",
                      "id"),
                     (r"^# u23-verify \w+, slice s\d+of\d+, checked .*?: verify-chain-(g5|lean)\.py ", "cname"),
                     (r"^# run directory: (\S+) \(", "rundir"),
                     (r"^# level files checked \(the runbook's hashes\.json rule\): (\d+) files, sha256 ([0-9a-f]{64})$",
                      "digest"),
                     (r"^# level files checked \(the runbook's hashes\.json rule\): (.*)$", "digest_line"),
                     (r"^# fleet branch HEAD: ([0-9a-f]{40});", "fleet_head"),
                     (r"^# checker: .* at ([0-9a-f]{40}), sha256 ([0-9a-f]{64})$", "checker"),
                     (r"^# started \S+, (\d+) s, exit (\d+)$", "exit"),
                     (r"^# prefix \(levels <= (\d+)\) against s(\d+)of\d+: (.*)$", "prefix"),
                     (r"^# u23-verify verdict: (\S+)$", "verdict")):
        mm = next((re.match(pat, x) for x in lines if re.match(pat, x)), None)
        head[key] = mm.groups() if mm else None
    body = [x for x in lines if not x.startswith("# ")]
    recs = []
    for x in body:
        if x.startswith("{"):
            try:
                recs.append(json.loads(x))
            except ValueError:
                recs.append(None)
    js = recs[0] if recs else None
    o = {"head": head, "json": js, "records": recs, "coverage": next((x for x in body if x.startswith("COVERAGE")), None),
         "chain": next((x for x in reversed(body) if x.startswith("CHAIN ")), None),
         "problems": [x for x in body if x.startswith("PROBLEM")]}
    code = head["exit"][1] if head["exit"] else None
    # died of memory before printing a result (u23-verify.sh's killed_for_memory): the only G5 outcome a lean check
    # may stand in for
    o["killed"] = ((code == "137" or (code == "1" and any("MemoryError" in x for x in body)))
                   and js is None and o["chain"] is None and not o["problems"])
    return o


# G5 round 20, finding 4: a checker record holds exactly these fields (measured: all 1,444 records of the full re-run
# and the sample), each checked below or by judge_output()
RECORD_KEYS = {"run", "target", "seed_n", "levels_inspected", "pruned_cells_inspected", "required_cells", "reach_files",
               "keep_files", "parent_files", "shards", "certs_replayed", "prune_filter_set", "forbidden_set", "rules",
               "verify_manifests", "slice_files", "coverage", "pinned", "slice"}


def record_scope(o: dict | None, ref: dict | None, whole: bool, shards: dict | None = None) -> list:
    """G5 round 19, finding 2: the checker's own record must say it covered what the check claims, counted from the
    slice's own cells (the fleet's copy, to which the re-run's is compared file for file), not from two of its counters
    agreeing: a whole check inspects every required cell (from the seed level), reads its reach file and verify
    manifest, the parent files of every cell above the seed level, and replays every pruned cell (from level 12); a
    check from level 13 does all that for every cell from level 13. Coverage 'exhaustive' or 'partial' to match, the
    required cells always the run's, the level-12 slice files read, and one record, not two. Measured first: every
    check output of the full re-run and the sample (1,271) meets it."""
    if o is None or ref is None:
        return []
    recs = o.get("records") or []
    if len(recs) != 1:
        return [f"its checker printed {len(recs)} records, not one"]
    j = recs[0]
    cells = [cell for cell in ref["counts"] if cell[0] >= SEED]
    R, P, F = len(cells), sum(1 for n, _ in cells if n >= LEVEL), sum(1 for n, _ in cells if n >= FROM)
    par, sl = sum(1 for n, _ in cells if n > SEED), sum(1 for n, _ in cells if n == LEVEL)
    want = ({"coverage": "exhaustive", "levels_inspected": R, "reach_files": R, "verify_manifests": R,
             "parent_files": par, "pruned_cells_inspected": P, "keep_files": P, "certs_replayed": P}
            if whole else
            {"coverage": "partial", "levels_inspected": F, "reach_files": F, "verify_manifests": F,
             "parent_files": F, "pruned_cells_inspected": F, "keep_files": F, "certs_replayed": F})
    want.update(required_cells=R, slice_files=sl, forbidden_set=398, prune_filter_set=74, rules=["triangles"])
    # G5 round 20, finding 4: every shard of every inspected cell with parents (from level 11 for a whole check, 13
    # otherwise), counted from the slice's pooled audited evidence (a resumed copy lists no shards of its own)
    if shards is None:
        return ["no audited shard evidence for the slice, so its checker record's shard count is not checked"]
    want["shards"] = sum(k for (n, _), k in shards.items() if n >= (SEED + 1 if whole else FROM))
    bad = {k: [j.get(k), v] for k, v in want.items() if j.get(k) != v}
    if set(j) != RECORD_KEYS:
        bad["fields"] = [sorted(set(j) ^ RECORD_KEYS), "none beyond or missing"]
    cov = o.get("coverage") or ""
    text_ok = (cov.startswith(f"COVERAGE exhaustive: all {R} required cells of ({TARGET[0]},{TARGET[1]}) from seed "
                              f"level {SEED} present and checked") and f"the certificates of all {P} pruned cells" in cov
               if whole else cov == f"COVERAGE partial: levels below {FROM} not inspected (--from-n {FROM})")
    why = []
    if bad:
        why.append(f"its checker record does not cover what a check {'whole' if whole else f'from level {FROM}'} "
                   f"covers (recorded, required): {bad}")
    if not text_ok:
        why.append(f"its COVERAGE line is not a check {'whole' if whole else f'from level {FROM}'}'s: {cov[:100]!r}")
    return why


def replay_checks(vroot: Path, froot: Path | None = None) -> dict:
    """G5 round 19, finding 1: the re-run's own G4 replays judged as the fleet's and the controls' are, by the same
    code: the G5-closed audit (verify-chain.py --summary-only, pinned) derives each replay's verdict from its details
    (per-cell mismatches, stage records, seed levels, red controls, not the summary's aggregates), and target_check.py's
    scope rules require the pinned sampling policy, the mode's scope against the audited evidence, the red controls'
    recorded outcomes, and every slice-mode prefix covered by a passing full-mode replay.

    The audit pools a slice's copies (as it pools the fleet's reruns with the originals): the fleet's copies of each
    judged slice are audited beside the re-run's, so that a re-run copy resumed without pushed history (the sample's
    v04, run by hand on the desktop, has 61 resumed cells whose parents only its twin records) is checked against the
    parents its files-identical twin records; each replay's verdict is still derived from its own details, and copies
    that disagree are still a problem. The fleet's full-mode copies come in too, as context: a slice-mode twin's prefix
    stage files lie in its fleet worker's first-slice run, which the verify-run binding must find (G5 round 20: without
    them, the twins' prefix manifests read as naming another run). Problems count against the judged slices only.
    {"per_slice": {i: [why]}, "global": [why], "copies": n, "shards": {i: {cell: n}}}."""
    import tempfile
    pat = f"*/research/unit-distance-23/results/u23/{TARGET[0]}-{TARGET[1]}-L{LEVEL}-tri-pf74/s*of{COUNT}"
    dirs = sorted(vroot.glob(pat))
    judged = {int(d.name[1:].split("of")[0]) for d in dirs}
    twins, context = [], []
    for d in (sorted(froot.glob(pat)) if froot else []):
        if int(d.name[1:].split("of")[0]) in judged:
            twins.append(d)
        else:
            try:
                if json.loads((d / "replay" / "fingerprint.json").read_text()).get("mode") == "full":
                    context.append(d)
            except (OSError, ValueError):
                pass
    with tempfile.TemporaryDirectory(prefix="vs-replay-tree-") as tmp:
        for d in dirs + twins + context:   # one tree, <worker>/research/.../s<i>of1920 (re-run a*/v*, fleet f*)
            link = Path(tmp) / d.relative_to(d.parents[6])
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(d.resolve())
        tree = Path(tmp)
        aud = tc.audit(sorted(tree.glob(pat)), *TARGET)
        per = {i: list(ws) for i, ws in aud["per_slice"].items() if i in judged}
        # G5 round 23, finding 1: a copy of a slice the audit found a problem in, context included, covers no prefix
        per_copy, _, glob, shards = tc.scope_problems(tree, "u23", *TARGET,
                                                      failed_slices={i for i, ws in aud["per_slice"].items() if ws})
    for i, label, ws in per_copy:
        if i in judged:
            per.setdefault(i, []).extend(f"its replay ({label}): {w}" for w in ws)
    return {"per_slice": per, "global": aud["global"] + glob, "copies": len(dirs), "twins": len(twins),
            "shards": {i: s for i, s in shards.items() if i in judged}}


def judge_output(o: dict | None, tag: str, i: int, first: int, plan: dict | None = None, kind: str = "g5") -> list:
    """Why this check output does not pass (empty: it passes), re-derived from the output itself. kind "lean": the
    memory-fallback record, by verify-chain-lean.py (pinned by LEAN_SHA256), under every other rule the same."""
    if o is None:
        return ["no check output"]
    h, why = o["head"], []
    if (h["cname"] or (None,))[0] != kind or o.get("file_kind", "g5") != kind:
        why.append(f"it is not a {kind} check output: its header names {h['cname']}, its file {o.get('file_kind')}")
    if not h["id"] or h["id"][0] != tag or int(h["id"][1]) != i or int(h["id"][2]) != COUNT:
        why.append(f"its header names another check: {h['id']}")
    # the checker's own record must be of this slice, target, seed and slicing, run on this slice's directory (G5
    # round 10, finding 2: a genuine check of another slice under this slice's header passed before)
    js0, run = o["json"] or {}, f"dag-{TARGET[0]}-{TARGET[1]}-L{LEVEL}-tri-pf74-s{i}of{COUNT}"
    if js0.get("slice") != [LEVEL, i, COUNT] or js0.get("target") != list(TARGET) or js0.get("seed_n") != SEED \
            or js0.get("pinned") != {"target": list(TARGET), "seed": SEED, "slices": [LEVEL, COUNT]} \
            or Path(str(js0.get("run"))).name != run or not h["rundir"] or Path(h["rundir"][0]).name != run:
        why.append(f"its checker record is not of slice {i}'s run ({run}): slice {js0.get('slice')}, target "
                   f"{js0.get('target')}, seed {js0.get('seed_n')}, pinned {js0.get('pinned')}, run "
                   f"{Path(str(js0.get('run'))).name}, header {h['rundir']}")
    plan = plan or {}
    exempt = (o.get("sha256") in set(plan.get("pre_digest_sha") or ())
              or (bool(plan.get("pre_digest_commit")) and bool(h["fleet_head"])
                  and h["fleet_head"][0] == plan["pre_digest_commit"]))
    if h["digest_line"] and not h["digest"]:
        why.append(f"the digest of the files checked was not computed: {h['digest_line'][0][:120]}")
    elif not h["digest"] and not exempt:
        why.append("no digest of the level files checked (every output of the fixed wrapper has one; only the "
                   "pinned historical outputs are exempt)")
    if h["verdict"] != ("pass",):   # the judge re-derives the verdict, but never overrides the wrapper's own FAIL
        why.append(f"the wrapper's own verdict is not pass: {h['verdict']}")
    if kind == "g5" and h["checker"] != (G5_COMMIT, G5_SHA256):
        why.append(f"its checker is not the pinned G5 one: {h['checker']}")
    if kind == "lean" and (not h["checker"] or h["checker"][1] != LEAN_SHA256):
        why.append(f"its checker is not the pinned memory-bounded one (sha256 {LEAN_SHA256[:16]}): {h['checker']}")
    if o["problems"]:   # G5 round 17, finding 5: a recorded problem fails the output, whichever check it was
        why.append(f"its checker printed {len(o['problems'])} PROBLEM line(s): {o['problems'][0][:120]}")
    code = int(h["exit"][1]) if h["exit"] else None
    skipped = bool(h["id"]) and "whole check skipped" in h["id"][3]   # a declared from-level-13 first slice
    js = o["json"] or {}
    if not (js.get("certs_replayed") == js.get("pruned_cells_inspected") and (js.get("certs_replayed") or 0) > 0):
        why.append(f"certificates replayed {js.get('certs_replayed')} of {js.get('pruned_cells_inspected')} pruned cells")
    if i == first and not skipped:
        cov = o["coverage"] or ""
        if code != 0 or o["chain"] != "CHAIN OK" or not cov.startswith("COVERAGE exhaustive") \
                or f"of ({TARGET[0]},{TARGET[1]}) from seed level {SEED} " not in cov \
                or f"(slice {i} of {COUNT} at level {LEVEL}:" not in cov:
            why.append(f"the whole check did not pass: exit {code}, {o['chain']!r}, {(o['coverage'] or '')[:60]!r}")
    else:
        want = f"CHAIN PARTIAL (levels below {FROM} not inspected (--from-n {FROM}))"
        if code != 3 or o["chain"] != want or o["problems"]:
            why.append(f"the check from level {FROM} did not pass: exit {code}, {o['chain']!r}, "
                       f"{len(o['problems'])} PROBLEM line(s)")
        if i != first and (not h["prefix"] or int(h["prefix"][1]) != first
                           or not re.fullmatch(r"identical, file for file( \(\d+ files\))?", h["prefix"][2])):
            why.append(f"its prefix is not shown identical to s{first}'s: {h['prefix']}")
    return why


def judge_copy(v: dict | None, f: dict | None, allow_g5_rundag: bool = False) -> list:
    if v is None:
        return ["no result copy from the verification worker"]
    if f is None:
        return ["no complete fleet copy to compare with"]
    if allow_g5_rundag:   # the full re-run runs the branch after the G5 merge: run-dag2.py is the G5-closed version
        v = dict(v, software={(s, k, FLEET_RUNDAG if k == "run-dag2.py" and h == G5_RUNDAG else h)
                              for s, k, h in v["software"]})
    why = [f"differs from the fleet's copy ({f['worker']}): {json.dumps(d)[:200]}" for d in af.compare_copies(v, f)]
    # G5 round 18, finding 5: the re-run's own G4 replay must have passed: PASS as the fleet's rule reads its evidence,
    # the runbook's own result PASS, every stage ok, and a full-mode replay's red controls all red (measured: every copy
    # of the fleet, the sample and the full re-run)
    rp = v.get("replay") or {}
    if not (rp.get("verdict") == "PASS" and rp.get("runbook_result") == "PASS" and rp.get("stages_ok") is True
            and (rp.get("red_all") is True if rp.get("mode") == "full" else rp.get("red_all") in (True, None))):
        why.append(f"its own G4 replay did not pass: verdict {rp.get('verdict')}, result {rp.get('runbook_result')}, "
                   f"stages ok {rp.get('stages_ok')}, red controls {rp.get('red_all')} ({rp.get('mode')} mode)")
    for key in ("prefix", "inputs"):
        if v[key] != f[key]:
            why.append(f"its {key} hashes differ from the fleet's copy ({f['worker']})")
    if {x for x in v["software"] if x[1] != "python"} != {x for x in f["software"] if x[1] != "python"}:
        why.append(f"its software hashes differ from the fleet's copy ({f['worker']})")
    if v["ctn"] != f["ctn"]:
        why.append(f"completed through n {v['ctn']}, the fleet's copy {f['ctn']}")
    return why


def collect(vroot: Path, froot: Path, plan: dict) -> tuple:
    outputs, vcopies = {}, {}
    for d in sorted(x for x in vroot.glob("*") if x.is_dir()):
        tag = d.name.split("-")[0]
        for p in sorted(d.glob("research/unit-distance-23/results/u23/verify/s*of1920-*.txt")):
            mm = re.fullmatch(rf"s(\d+)of1920-{tag}(\.lean)?\.txt", p.name)
            if mm:
                o = parse_output(p.read_text())
                o["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                o["file_kind"] = "lean" if mm.group(2) else "g5"
                outputs.setdefault((tag, int(mm.group(1))), []).append(o)
    for c in af.scan(vroot)[0]:
        vcopies.setdefault((c["worker"].split("-")[0], c["slice"]), []).append(c)
    wanted = {i for sl in plan["workers"].values() for i in sl}
    fleet = {}
    for d in sorted(froot.glob(f"*/research/unit-distance-23/results/u23/{fs.KIND}/s*of1920")):
        i = int(d.name[1:].split("of")[0])
        if i in wanted:
            try:
                c = af.read_copy(d, froot)
            except af.Incomplete:
                continue
            if c["ctn"] == c["target"][0]:
                fleet.setdefault(i, []).append(c)
    return outputs, vcopies, {i: af.choose(cs) for i, cs in fleet.items()}


def copy_digest(c: dict) -> tuple:
    """A result copy's level files (its hashes.json) as u23-verify.sh digests the run directory it checked."""
    files = dict(c["prefix"]) | {k: v[0] for k, v in c["upper"].items()}
    lines = "".join(f"{n} {files[n]}\n" for n in sorted(files))
    return str(len(files)), hashlib.sha256(lines.encode()).hexdigest()


def evaluate(plan: dict, outputs: dict, vcopies: dict, fleet: dict, replay: dict | None = None) -> tuple:
    problems, lines = [], []
    if replay is not None:   # G5 round 19, finding 1: problems of no one slice fail the whole report
        problems += [f"the re-run copies' G4 audit: {w}" for w in replay.get("global") or []]
    assigned = [i for sl in plan["workers"].values() for i in sl]
    if plan.get("all"):
        if sorted(assigned) != list(range(COUNT)):
            problems.append(f"the plan's tasks are not every slice 0..{COUNT - 1}, each once")
    else:
        pool = sorted(set(range(COUNT)) - set(plan["restarted"]))
        drawn = sorted(random.Random(plan["seed"]).sample(pool, plan["k"]))
        if drawn != sorted(plan["random"]):
            problems.append(f"the sample rule (seed {plan['seed']}, {plan['k']} of {len(pool)}) does not give the listed "
                            f"random slices")
        if sorted(assigned) != sorted(plan["restarted"] + plan["random"]) or len(set(assigned)) != len(assigned):
            problems.append("the workers' table is not the restarted and random slices, each once")
    results = []
    for tag, sl in sorted(plan["workers"].items()):
        first = sl[0]
        for i in sl:
            outs = outputs.get((tag, i)) or [None]
            g5s = [o for o in outs if o is None or o.get("file_kind", "g5") == "g5"] or [None]
            leans = [o for o in outs if o is not None and o.get("file_kind") == "lean"]
            if leans:   # the memory fallback stands in only for G5 checks that died of memory before a result
                why = [f"G5 check output {k + 1} is not a memory kill (exit "
                       f"{(o['head']['exit'] or (None, None))[1] if o else None}), so no lean check stands in for it"
                       for k, o in enumerate(g5s) if o is None or not o["killed"]]
                why += [f"lean check output {k + 1}: {w}" if len(leans) > 1 else f"lean check: {w}"
                        for k, L in enumerate(leans) for w in judge_output(L, tag, i, first, plan, kind="lean")]
            else:
                why = [f"check output {k + 1}: {w}" if len(g5s) > 1 else w
                       for k, o in enumerate(g5s) for w in judge_output(o, tag, i, first, plan)]
            # G5 round 19, finding 2: every output standing for the slice covers what its check claims
            skip0 = lambda o: bool(o and o["head"]["id"]) and "whole check skipped" in o["head"]["id"][3]
            for k, o in enumerate(leans if leans else g5s):
                why += [f"check output {k + 1}: {w}" if len(leans or g5s) > 1 else w
                        for w in record_scope(o, fleet.get(i), i == first and not skip0(o),
                                              (replay or {}).get("shards", {}).get(i) if replay is not None else None)]
            if replay is not None:
                why += [f"its re-run's G4 replay: {w}" for w in (replay.get("per_slice") or {}).get(i, [])]
            copies = vcopies.get((tag, i)) or [None]
            why += [w for c in copies for w in judge_copy(c, fleet.get(i), allow_g5_rundag=bool(plan.get("all")))]
            for o in outs:   # the directory checked is the one whose files the copy ships (finding 2)
                for c in copies:
                    if o and c and o["head"]["digest"] and tuple(o["head"]["digest"]) != copy_digest(c):
                        why.append(f"the digest of the files checked ({o['head']['digest'][0]} files, "
                                   f"{o['head']['digest'][1][:16]}) is not its copy's ({copy_digest(c)[0]} files, "
                                   f"{copy_digest(c)[1][:16]})")
            o = leans[-1] if leans else g5s[0]
            skip = bool(o and o["head"]["id"]) and "whole check skipped" in o["head"]["id"][3]
            kind = "all" if plan.get("all") else "restarted" if i in plan["restarted"] else "random"
            results.append({"tag": tag, "i": i, "kind": kind, "why": why, "whole": i == first and not skip,
                            "skip": skip, "o": o, "copies": copies, "lean": bool(leans)})
    # a prefix (levels <= 12) is shown sound only by a whole check of it: every slice's prefix, by its copy's hashes,
    # must be the prefix of a slice that passed its whole check (G5 round 10, finding 3: before, every first slice
    # could declare the whole check skipped and the sample still passed, prefixes compared only with each other)
    wholes = {c["prefix"] for r in results if r["whole"] and not r["why"] for c in r["copies"] if c}
    if not wholes and any(not r["why"] for r in results):   # (with no slice passing at all, each slice says why)
        problems.append("no slice passed a whole check, so no prefix is shown sound (G5 round 10, finding 3)")
    for r in results:
        if not r["why"] and any(c["prefix"] not in wholes for c in r["copies"] if c):
            r["why"].append("its prefix (levels <= 12, by its copy's hashes) is not the prefix of any slice that "
                            "passed a whole check")
    ok_slices, whole, lean = 0, 0, 0
    for r in results:
        tag, i, kind, why, o, copies = r["tag"], r["i"], r["kind"], r["why"], r["o"], r["copies"]
        if why:
            problems += [f"s{i} ({tag}, {kind}): {w}" for w in why]
            lines.append(f"s{i} {tag} {kind}: NOT verified")
            continue
        ok_slices += 1
        whole += r["whole"]
        lean += r["lean"]
        py = sorted({x[2] for c in copies for x in c["software"] if x[1] == "python"}
                    - {x[2] for x in fleet[i]["software"] if x[1] == "python"})
        how = ("whole" if r["whole"] else f"from level {FROM}"
               + (" (the worker's first slice, whole check skipped: its prefix by hash)" if r["skip"] else ""))
        lines.append(f"s{i} {tag} {kind}: {how}, {o['chain']}, certificates replayed in {o['json']['certs_replayed']} "
                     f"pruned cells; result files identical to the fleet's copy ({fleet[i]['worker']})"
                     + ("; files checked = copy's (digest)" if o["head"]["digest"] else "")
                     + ("; by verify-chain-lean.py, the G5 check having been killed for memory" if r["lean"] else "")
                     + (f"; interpreter {', '.join(py)} (not compared)" if py else ""))
    return problems, lines, {"planned": len(assigned), "verified": ok_slices, "whole": whole,
                             "workers": len(plan["workers"]), "restarted": len(plan.get("restarted", [])),
                             "random": len(plan.get("random", [])), "seed": plan.get("seed"),
                             "all": bool(plan.get("all")), "prefixes": len(wholes), "lean": lean}


def report(problems, lines, s) -> int:
    for x in lines:
        print(x)
    for p in problems:
        print("PROBLEM:", p)
    if s["all"]:
        print(f"VERIFY-ALL {'OK' if not problems else 'FAIL'}: {s['verified']} of {s['planned']} slices re-run and "
              f"verified ({s['workers']} tasks; {s['whole']} first slices checked whole, the rest from level {FROM} with "
              f"the prefix compared; every prefix the prefix of a whole check"
              + (f"; {s['lean']} by the memory-bounded verify-chain-lean.py after the G5 check was killed for memory"
                 if s.get("lean") else "") + f"), {len(problems)} problem(s)")
    else:
        print(f"VERIFY-SAMPLE {'OK' if not problems else 'FAIL'}: {s['verified']} of {s['planned']} planned slices "
              f"verified ({s['restarted']} restarted, {s['random']} random, seed {s['seed']}; {s['whole']} of "
              f"{s['workers']} workers' first slices checked whole, the rest from level {FROM} with the prefix "
              f"compared), {len(problems)} problem(s)")
    return 0 if not problems else 1


def self_test(plan, outputs, vcopies, fleet, replay=None) -> int:
    judge = globals()["evaluate"]

    def evaluate(p, o, v, f, r=replay):   # noqa: F811  every control judged with the base's replay checks, so that
        return judge(p, o, v, f, r)       # none is caught only for lacking them (a control that could not fail)

    base, _, _ = evaluate(plan, outputs, vcopies, fleet, replay)
    ok_keys = [k for k in sorted(outputs) if k in vcopies and k[1] in fleet
               and not [p for p in base if p.startswith(f"s{k[1]} ({k[0]}")]]
    if not ok_keys:
        print("SELF-TEST cannot run: no planned slice verifies yet")
        return 1
    tag, i = ok_keys[0]
    res = []

    def expect(name, P, must=None):
        new = [p for p in P if p not in base and (must is None or must(p))]
        res.append((name, bool(new)))
        print(f"{'ok  ' if new else 'FAIL'} self-test, {name}: {new[0][:150] if new else 'not caught'}")

    def accepted(name, P, key):   # a positive control: the slice verifies, with no problem of its own
        own = [p for p in P if p not in base and p.startswith(f"s{key[1]} ({key[0]}")]
        res.append((name, not own))
        print(f"{'ok  ' if not own else 'FAIL'} self-test, {name}: {'accepted' if not own else own[0][:150]}")

    vc = copy.deepcopy(vcopies)
    cell = next(iter(vc[(tag, i)][0]["counts"]))
    r = vc[(tag, i)][0]["counts"][cell]   # a stored row: (children, prune count keys, their values)
    vc[(tag, i)][0]["counts"][cell] = ((r[0] or 0) + 1, r[1], r[2])
    expect(f"s{i}'s cell {cell} with one child more in {tag}'s copy", evaluate(plan, outputs, vc, fleet)[0])
    oc = copy.deepcopy(outputs)
    oc[(tag, i)][0]["chain"] = "CHAIN FAIL (1 problems)"
    expect(f"s{i}'s check says CHAIN FAIL", evaluate(plan, oc, vcopies, fleet)[0])
    oc = {k: v for k, v in outputs.items() if k != (tag, i)}
    expect(f"s{i}'s check output removed", evaluate(plan, oc, vcopies, fleet)[0])
    vc = {k: v for k, v in vcopies.items() if k != (tag, i)}
    expect(f"s{i}'s copy removed", evaluate(plan, outputs, vc, fleet)[0])
    vc = copy.deepcopy(vcopies)
    pre = vc[(tag, i)][0]["prefix"]
    vc[(tag, i)][0]["prefix"] = tuple([(pre[0][0], "0" * 64)] + list(pre[1:])) if pre else (("x", "0" * 64),)
    expect(f"s{i}'s copy with one prefix file's hash changed", evaluate(plan, outputs, vc, fleet)[0])
    oc = copy.deepcopy(outputs)
    hid = oc[(tag, i)][0]["head"]["id"]
    if i == plan["workers"][tag][0] and hid:   # a first slice checked from level 13 without declaring the skip
        oc[(tag, i)][0]["head"]["id"] = (hid[0], hid[1], hid[2], f"from level {FROM}", hid[4])
        oc[(tag, i)][0]["chain"] = f"CHAIN PARTIAL (levels below {FROM} not inspected (--from-n {FROM}))"
        expect(f"s{i} (a first slice) checked from level {FROM} without the declared skip",
               evaluate(plan, oc, vcopies, fleet)[0])
    # G5 round 10's findings, each as a red control
    later = next(((tg, j) for tg, j in ok_keys if j != plan["workers"][tg][0]), None)
    other = next(((tg, j) for tg, j in ok_keys if j != i), None)
    if other:   # finding 2: a genuine check of another slice under this slice's header
        oc = copy.deepcopy(outputs)
        sub = copy.deepcopy(outputs[other][0])
        sub["head"]["id"] = oc[(tag, i)][0]["head"]["id"]
        sub["head"]["exit"], sub["chain"], sub["coverage"] = (oc[(tag, i)][0]["head"]["exit"], oc[(tag, i)][0]["chain"],
                                                              oc[(tag, i)][0]["coverage"])
        oc[(tag, i)][0] = sub
        expect(f"s{i}'s output replaced by s{other[1]}'s genuine check under s{i}'s header",
               evaluate(plan, oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # finding 3: every first slice declares its whole check skipped
    for tg, sl in plan["workers"].items():
        for o in oc.get((tg, sl[0])) or []:
            if o and o["head"]["id"]:
                h = o["head"]
                h["id"] = (h["id"][0], h["id"][1], h["id"][2], f"from level {FROM}, whole check skipped "
                           "(U23_VERIFY_WHOLE=0: its prefix is compared by hash with the fleet's)", h["id"][4])
                h["exit"] = (h["exit"][0] if h["exit"] else "0", "3")
                o["chain"] = f"CHAIN PARTIAL (levels below {FROM} not inspected (--from-n {FROM}))"
                o["coverage"], o["problems"] = f"COVERAGE partial: levels below {FROM} not inspected (--from-n {FROM})", []
    expect("every first slice's whole check declared skipped", evaluate(plan, oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # finding 2, the digest: the files checked are not the copy's
    oc[(tag, i)][0]["head"]["digest"] = (copy_digest(vcopies[(tag, i)][0])[0], "0" * 64)
    expect(f"s{i}'s digest of the files checked not its copy's", evaluate(plan, oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # G5 round 13: the control must remove a digest, not only the exemptions
    oc[(tag, i)][0]["head"]["digest"] = None
    oc[(tag, i)][0]["head"]["digest_line"] = None
    expect(f"s{i}'s output without its files digest, no exemption",
           evaluate(dict(plan, pre_digest_sha=[], pre_digest_commit=None), oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # G5 round 11, finding 1: an exempt output altered is exempt no more
    oc[(tag, i)][0]["sha256"] = "0" * 64
    if not plan.get("all"):
        expect(f"s{i}'s output altered (no longer the pinned historical file)", evaluate(plan, oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # a digest line that says the digest could not be computed
    oc[(tag, i)][0]["head"]["digest"] = None
    oc[(tag, i)][0]["head"]["digest_line"] = ("NO RESULT (Traceback ...)",)
    expect(f"s{i}'s digest not computed", evaluate(plan, oc, vcopies, fleet)[0])
    oc = copy.deepcopy(outputs)   # the wrapper's own verdict FAIL
    oc[(tag, i)][0]["head"]["verdict"] = ("FAIL",)
    expect(f"s{i}'s wrapper verdict FAIL", evaluate(plan, oc, vcopies, fleet)[0])
    if later:   # finding 1: a comparison that did not succeed
        oc = copy.deepcopy(outputs)
        pr = oc[later][0]["head"]["prefix"]
        oc[later][0]["head"]["prefix"] = (pr[0], pr[1], "the comparison did not succeed (exit 1): Traceback")
        expect(f"s{later[1]}'s prefix comparison did not succeed", evaluate(plan, oc, vcopies, fleet)[0])
    vc = copy.deepcopy(vcopies)   # G5 round 18, finding 5: the re-run's own G4 replay failed
    vc[(tag, i)][0]["replay"] = dict(vc[(tag, i)][0]["replay"], verdict="MISMATCH", runbook_result="FAIL")
    expect(f"s{i}'s re-run with its own G4 replay failed (MISMATCH, FAIL)", evaluate(plan, outputs, vc, fleet)[0],
           must=lambda p: "its own G4 replay did not pass" in p)
    whole_key = next(((tg, j) for tg, j in ok_keys if j == plan["workers"][tg][0]), None)
    if whole_key:   # G5 round 17, finding 5: a whole check with a recorded problem
        oc = copy.deepcopy(outputs)
        oc[whole_key][0]["problems"] = oc[whole_key][0]["problems"] + ["PROBLEM: a pruned cell did not verify"]
        expect(f"s{whole_key[1]}'s whole check (CHAIN OK) with a PROBLEM line", evaluate(plan, oc, vcopies, fleet)[0],
               must=lambda p: "PROBLEM line(s)" in p)
    # the memory fallback: a lean record stands in only for a G5 check that died of memory before a result
    lk = later or (tag, i)
    g5 = outputs[lk][0]
    killed = copy.deepcopy(g5)
    killed["head"]["exit"] = ((g5["head"]["exit"] or ("0",))[0], "137")
    killed["head"]["verdict"] = ("FAIL",)
    killed.update(json=None, chain=None, coverage=None, problems=[], killed=True)
    lean = copy.deepcopy(g5)
    lean["file_kind"], lean["head"]["cname"] = "lean", ("lean",)
    lean["head"]["checker"] = ((g5["head"]["checker"] or ("0" * 40,))[0], LEAN_SHA256)
    oc = copy.deepcopy(outputs); oc[lk] = [killed, lean]
    accepted(f"s{lk[1]}'s G5 check killed for memory, its lean check passing", evaluate(plan, oc, vcopies, fleet)[0], lk)
    oc = copy.deepcopy(outputs); oc[lk] = [killed, dict(lean, head=dict(lean["head"], checker=(lean["head"]["checker"][0], "0" * 64)))]
    expect(f"s{lk[1]}'s lean check by another checker", evaluate(plan, oc, vcopies, fleet)[0],
           must=lambda p: "not the pinned memory-bounded one" in p)
    oc = copy.deepcopy(outputs); oc[lk] = [dict(killed, problems=["PROBLEM: x"], killed=False), lean]
    expect(f"s{lk[1]}'s lean check beside a G5 check that printed a problem", evaluate(plan, oc, vcopies, fleet)[0],
           must=lambda p: "is not a memory kill" in p)
    oc = copy.deepcopy(outputs); oc[lk] = [killed, dict(lean, head=dict(lean["head"], verdict=("FAIL",)))]
    expect(f"s{lk[1]}'s lean check whose own verdict is FAIL", evaluate(plan, oc, vcopies, fleet)[0],
           must=lambda p: "wrapper's own verdict is not pass" in p)
    oc = copy.deepcopy(outputs); oc[lk] = [killed]
    expect(f"s{lk[1]}'s G5 check killed for memory, no lean check", evaluate(plan, oc, vcopies, fleet)[0])
    # G5 round 19, finding 2: a checker record that says it inspected less than its check claims
    wkey = next(((tg, j) for tg, j in ok_keys if j == plan["workers"][tg][0]), None)
    fkey = next(((tg, j) for tg, j in ok_keys if j != plan["workers"][tg][0]), None)
    if wkey:
        o0 = outputs[wkey][0]
        short = dict(o0["records"][0], coverage="partial", levels_inspected=1, pruned_cells_inspected=1,
                     certs_replayed=1)
        oc = copy.deepcopy(outputs); oc[wkey] = [dict(o0, json=short, records=[short])]
        expect(f"s{wkey[1]}'s whole check whose record says it inspected 1 cell and replayed 1 (G5 round 19, finding 2)",
               evaluate(plan, oc, vcopies, fleet)[0], must=lambda p: "does not cover what a check whole covers" in p)
        for name, change in (("its shards 0", {"shards": 0}), ("forbidden set 74", {"forbidden_set": 74}),
                             ("prune filter set 398 and no rules", {"prune_filter_set": 398, "rules": []})):
            r2 = dict(o0["records"][0], **change)   # G5 round 20, finding 4
            oc = copy.deepcopy(outputs); oc[wkey] = [dict(o0, json=r2, records=[r2])]
            expect(f"s{wkey[1]}'s whole check whose record says {name} (G5 round 20, finding 4)",
                   evaluate(plan, oc, vcopies, fleet)[0], must=lambda p: "does not cover what a check whole covers" in p)
        r3 = dict(o0["records"][0], extra_field=1)
        oc = copy.deepcopy(outputs); oc[wkey] = [dict(o0, json=r3, records=[r3])]
        expect(f"s{wkey[1]}'s checker record with a field it never has", evaluate(plan, oc, vcopies, fleet)[0],
               must=lambda p: "'fields'" in p)
        oc = copy.deepcopy(outputs); oc[wkey] = [dict(o0, records=o0["records"] * 2)]
        expect(f"s{wkey[1]}'s check output with its record printed twice", evaluate(plan, oc, vcopies, fleet)[0],
               must=lambda p: "printed 2 records, not one" in p)
    if fkey:
        o1 = outputs[fkey][0]
        oc = copy.deepcopy(outputs)
        oc[fkey] = [dict(o1, coverage=f"COVERAGE exhaustive: all 83 required cells of ({TARGET[0]},{TARGET[1]})")]
        expect(f"s{fkey[1]}'s check from level {FROM} with an exhaustive COVERAGE line", evaluate(plan, oc, vcopies,
               fleet)[0], must=lambda p: "COVERAGE line is not a check from level" in p)
    # finding 1: the re-run's own replay, judged from its details by the audit and the scope rules, on a scratch copy of
    # a verified slice's copy (its aggregates left as they were)
    import shutil, tempfile
    src = next((c["dir"] for c in vcopies.get((tag, i)) or [] if c), None)
    if src is not None:
        def mutated(change, rel="replay/summary.json"):
            tmp = Path(tempfile.mkdtemp(prefix="vs-replay-"))
            dst = tmp / Path(src).relative_to(Path(src).parents[6])   # <worker>/research/.../s<i>of1920
            shutil.copytree(src, dst)
            sp = dst / (next(q.relative_to(dst) for q in sorted(dst.glob(rel))) if "*" in rel else rel)
            if change:
                j = json.loads(sp.read_text()); change(j); sp.write_text(json.dumps(j))
            try:
                return replay_checks(tmp)["per_slice"].get(i, [])
            finally:
                shutil.rmtree(tmp)
        r0 = mutated(None)
        for name, change, must in (
                ("one per-cell row with a mismatch", lambda j: j["per_cell"][0].__setitem__("mismatches", 1),
                 "evidence gives FAIL"),
                ("a stage record not ok", lambda j: j["stages"][0].__setitem__("ok", False), "evidence gives FAIL"),
                ("its detail records deleted", lambda j: [j.pop(k) for k in ("per_cell", "per_level", "seeds", "stages")],
                 "missing detail records"),
                ("another seed", lambda j: j.__setitem__("seed", str(int(j["seed"]) + 1)), "sampling policy")):
            new = [w for w in mutated(change) if w not in r0]
            ok = any(must in w for w in new)
            res.append((name, ok))
            print(f"{'ok  ' if ok else 'FAIL'} self-test, s{i}'s re-run replay with {name} (G5 round 19, finding 1): "
                  f"{new[0][:150] if new else 'not caught'}")
        # G5 round 20, finding 5: a verify manifest's software map deleted (the re-run's copies' manifests by the
        # controls' rules, not a software inventory pooled across manifests)
        new = [w for w in mutated(lambda j: j.pop("software_sha256"), f"verify/{FROM}-*.verify.manifest.json") if w not in r0]
        ok = any("software keys" in w for w in new)
        res.append(("verify manifest without software pins", ok))
        print(f"{'ok  ' if ok else 'FAIL'} self-test, s{i}'s re-run copy with a verify manifest's software pins deleted "
              f"(G5 round 20, finding 5): {new[0][:150] if new else 'not caught'}")
    # G5 round 23, finding 1: a full-mode copy whose slice failed the audit covers no prefix: two fleet copies of one
    # worker, its first slice (full) and another (slice mode), judged with and without the first slice failed
    fw = {}
    for k, c in fleet.items():
        fw.setdefault(c["worker"], []).append(k)
    pair = next(((w, sorted(ks)) for w, ks in sorted(fw.items()) if len(ks) >= 2), None)
    if pair:
        w, ks = pair
        tmp = Path(tempfile.mkdtemp(prefix="vs-cover-"))
        try:
            for k in ks[:2]:
                src_d = Path(fleet[k]["dir"])
                link = tmp / src_d.relative_to(src_d.parents[6])
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(src_d.resolve())
            modes = {k: json.loads((Path(fleet[k]["dir"]) / "replay" / "fingerprint.json").read_text()).get("mode")
                     for k in ks[:2]}
            fk = next((k for k in ks[:2] if modes[k] == "full"), None)
            sk = next((k for k in ks[:2] if modes[k] == "slice"), None)
            if fk is not None and sk is not None:
                p0 = tc.scope_problems(tmp, "u23", *TARGET)[0]
                p1 = tc.scope_problems(tmp, "u23", *TARGET, failed_slices={fk})[0]
                cov = lambda pc: any(k == sk and any("passing full-mode G4 replay covers" in w_ for w_ in ws)
                                     for k, _, ws in pc)
                ok = not cov(p0) and cov(p1)
                res.append(("failed full-mode copy covering a prefix", ok))
                print(f"{'ok  ' if ok else 'FAIL'} self-test, s{sk}'s prefix covered only by s{fk}, whose slice failed "
                      f"the audit (G5 round 23, finding 1): {'not covered' if ok else 'still covered'}")
        finally:
            shutil.rmtree(tmp)
    expect(f"s{i}'s re-run replay with a problem of its own, as evaluate() receives it",
           evaluate(plan, outputs, vcopies, fleet, dict(replay or {}, per_slice={i: ["x"]}, **{"global": []}))[0],
           must=lambda p: p.startswith(f"s{i} ({tag}") and "its re-run's G4 replay: x" in p)
    if plan.get("all"):
        wk = dict(plan["workers"]); wk.pop(next(iter(wk)))   # a whole task's slices gone (G5 round 12, finding 5)
        expect("a task dropped from the plan", evaluate(dict(plan, workers=wk), outputs, vcopies, fleet)[0])
    else:
        expect("the sample rule under another seed", evaluate(dict(plan, seed=plan["seed"] + 1), outputs, vcopies,
                                                             fleet)[0])
    bad = sum(1 for _, ok in res if not ok)
    print(f"SELF-TEST {'passed' if not bad else 'FAILED'}: {len(res) - bad} of {len(res)} red controls caught")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify-root", type=Path, default=VERIFY_ROOT)
    ap.add_argument("--root", type=Path, default=FLEET_ROOT)
    ap.add_argument("--jobs", type=Path, default=JOBS)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--all", action="store_true", help="judge the full re-run (u23-verify-all-plan.json) in "
                    "--verify-root instead of the sample")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    plan = plan_from_all(ALL_PLAN) if a.all else plan_from_jobs(a.jobs.read_text())
    if a.fetch:
        a.verify_root.mkdir(parents=True, exist_ok=True)
        fetch(a.verify_root, "a*" if a.all else "v*")
    outputs, vcopies, fleet = collect(a.verify_root, a.root, plan)
    replay = replay_checks(a.verify_root, a.root)   # G5 round 19, finding 1 (with the fleet's twins)
    code = 0
    if a.self_test:
        code = self_test(plan, outputs, vcopies, fleet, replay)
    return report(*evaluate(plan, outputs, vcopies, fleet, replay)) or code


if __name__ == "__main__":
    sys.exit(main())
