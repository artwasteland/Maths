#!/usr/bin/env python3
"""A whole tree at one target, run by the final pipeline over all 1,920 slices: audited, replayed, and its top level.

usage: python target_check.py --root DIR --target N M [--sub SUB] --root-k K [--no-ubar]
                              [--expect-empty | --known FILE] [--fetch PATTERN] [--self-test]

Two uses (CONTRACT Section 4): the (22,61) control at full strength (u23-control22: the top level must keep nothing,
with no u-bar override and root minimum degree 5, Lemma D4) and the (21,57) calibration (u23-calib2157: the top level
must keep every one of Alexeev, Mixon and Parshall's five extremal graphs, engel-21-57.g6, root minimum degree 3).

Each slice's copy lives under ROOT/*/research/unit-distance-23/results/SUB/N-M-L12-tri-pf74/s<i>of1920. Two layers:
  1. The audit: the G5-closed verify-chain.py (the fleet audit's checker, pinned by sha256) run --summary-only over
     every copy, pinned to the target, seed level 10 and 1,920 slices at level 12, with hashes.json and the G4 replays
     required. It checks each copy's required cells, their L4 parents, every count, and each G4 replay's verdict
     rebuilt from its evidence (G5 round 13: a checker of my own missed parents, stage flags and replay scope; this
     one was reviewed through nine rounds and catches them).
  2. What the audit does not pin: the copy's identity in run-config.json and hashes.json, the fleet's pipeline options,
     the root minimum degree and the u-bar table asked for, the G4 replay's tool, enum2, forbidden list, seed and
     sampling policy (the fleet's), the top cell's keep file equal to its hashes.json record, and the G4 replay's
     scope, judged against the audit's own accepted evidence (its summary_audit(), the pinned file imported; G5
     rounds 14 and 15): a full replay recomputes each level-10 seed cell in full, its counts equal to the audited
     cell's; every cell of the mode's levels with audited parents (the slice's copies pooled, and they must agree) has
     a row with exactly those parents, its strata the audited shards, and exactly as many sampled as the pinned replay
     tool's own sample_indices() draws from them; no row names a cell without audited evidence; every count is an
     int; and every copy's prefix (levels <= 12, as hashes.json records it) is one a passing full-mode replay covers
     (G5 round 16). --scope-only runs this part alone over any tree (the (23,65) fleet's G4 gate).
A slice with no copy is MISSING (a MISSING line); a slice any of whose copies fails either layer is FAILING (a PROBLEM
line naming it). Every PROBLEM line is a failure; absence is never a PROBLEM. Then the top level, over the union of the
passing copies' keep files (canonical forms, nauty-labelg): --expect-empty needs it empty; --known needs every graph
of FILE in it (with slices missing, a known graph not yet seen is open, not lost). --fetch PATTERN first fetches
origin's branches claude/answering-alexeev-u22-cloud-u23-PATTERN into refs/u23t/ and extracts each one's results/SUB
tree into ROOT. --self-test shows each requirement can fail, on scratch copies (the evidence is never edited).
Output: a "parameters:" line (what was required), the audit's COVERAGE line, then the last line
TARGET-CHECK OK|FAIL: (N,M): C of 1920 slices complete, G4 PASS P; F failing, M missing; kept at (N,M): K distinct
graph(s)[; known: F of T kept]. Exit 0 only on OK.
"""
import argparse, ast, copy, hashlib, importlib.util, json, math, random, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
import level22_control as lc   # noqa: E402  canonical forms: one notion of "the same graph"

COUNT, LEVEL, SEED_N = 1920, 12, 10
VERIFY_CHAIN = REPO / "research/unit-distance-22/enum/verify-chain.py"
REPLAY_TOOL = REPO / "research/unit-distance-22/enum2/replay-398.py"   # the fleet's G4 replay tool (REPLAY_PINS)
G5_SHA256 = "d253338569dedb41740cdb4774a6a361f6498f036787a52c3f985caca5d6ddd8"   # the G5-closed checker (34f0dcb9ba)
PIPELINE = {"seed_n": SEED_N, "reach": True, "prune": True, "prune_from": 12, "prune_filter_only": True,
            "verify_stages": True,   # G5 round 17: a copy with the stage verifications off passed
            "forbidden_set": 398, "triangles": True, "prune_filter_set": 74}
FLEET_UBAR = {"22": {"builtin": 62, "value": 60}}   # the fleet's override (u(22) = 60), the runbook's default
# the fleet's G4 replay (every (23,65) copy): replay-398.py, enum2.py, forbidden-398.json, the published seed, and the
# sampling policy (G5 round 13: the audit does not pin the policy, a fraction of 0 passed it)
REPLAY_PINS = {"tool_sha256": "2c81ae6541482096ed15cecd7af45e57098ea36941fd6f2634a4124e5b94f785",
               "enum2_sha256": "d967fc9024cda647c01bca95d6d6d9e2b6b0c24539d288c0ee1ee669faffa54e",
               "forbidden_sha256": "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c",
               "seed": "20260926", "forbidden_set": "398", "fraction": 0.001, "min_per_shard": 2, "whole_max": 100,
               "max_per_shard": None}
# the shipped manifests' software (G5 round 17: a changed udenum hash passed): one value per key, measured over every
# copy of the fleet, the (22,61) control and the (21,57) calibration; run-dag2.py is the fleet's or the G5-closed one
# (the controls ran the branch after the G5 merge); the interpreter's path and version are not compared
SOFTWARE = {"udenum": "84adaddfb449a3355c56990cd6d6ac7b564a3ad6d912372b6a3668d72924731a",
            "prune.py": "b4858cabc512f8190308d692ea21bedf37e1f1b927f32c40e714bdd99e47a900",
            "exact_verify.py": "ab55ce77bca0d66f13ba4189ddb16cc0a27fda36838abcf89bb1bda0d8285a7c",
            "udcheck.py": "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de",
            "udcheck398.py": "783d368c34626ad6fe20574d1ecf7a38aea9d2ebb6aef65e9d88785f16262018",
            "udcheck_rhombus.py": "06db27ec337ead0dc18766ddc8dac0cbf7ebc7e9b4d2e30650c4b01016a20222",
            "udembed.py": "75886c6323caa82d15c2a4c14680c0b6ed3b5cc3608abf116934463361decbda",
            "udfilter": "6e0771bb0888e193b7790bdd4b34518d5b35b313fd6a15f330f39f8489fd6dcc",
            "udtriangle": "0ca59908562f56cab4e31edcf22d4459e7bee03586496a69d91ccc3586f7e5cf"}
RUNDAG = {"0c6fb31243ab1e69175be3a5bcbf2c2a270749eeaa1b7d0f2e5f60a47abcd3cd",    # the fleet's
          "78b66addd192f253a3c26c3509d0747d713c392bf2f14f1a1f4220fa3ca05a51"}    # the G5-closed one
VERIFY_CHECK = "udenum --verify-parents: every record canonical and free of the forbidden set"
# G5 round 19, finding 5: the software keys each kind of shipped manifest must record (measured: every manifest of the
# fleet, the control, the calibration, the sample and the full re-run records exactly these)
SOFTWARE_KEYS = {"enum": {"udenum", "run-dag2.py"}, "verify": {"udenum", "run-dag2.py"},
                 "prune": {"prune.py", "udfilter", "udembed.py", "exact_verify.py", "udcheck.py", "python",
                           "udcheck398.py", "udtriangle", "udcheck_rhombus.py"}}
# G5 round 19, finding 3: the red controls a Mode-398 full replay must record, each once (replay-398.py's required list)
RED_IDS = ("R1", "R2", "R3", "R4", "R5a", "R5b")
# the pruning step's data files (the checkout's research/unit-distance-22/data, the same in every copy measured)
PRUNE_DATA = {"forbidden-398.json": "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c",
              "forbidden-74.json": "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
              "tu-gadgets.json": "a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fetch(root: Path, pattern: str, sub: str) -> None:
    out = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/claude/answering-alexeev-u22-cloud-u23-{pattern}"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    for line in filter(None, (x.strip() for x in out)):
        ref = line.split()[1]
        name = ref.split("cloud-u23-", 1)[1]
        subprocess.run(["git", "fetch", "-q", "--no-write-fetch-head", "origin", f"+{ref}:refs/u23t/{name}"], cwd=REPO,
                       check=True)
        dst = root / name
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        arch = subprocess.run(["git", "archive", f"refs/u23t/{name}", f"research/unit-distance-23/results/{sub}"],
                              cwd=REPO, capture_output=True)
        if arch.returncode == 0 and arch.stdout:
            subprocess.run(["tar", "-x", "-C", str(dst)], input=arch.stdout, check=True)


def audit(dirs: list, tn: int, tm: int) -> dict:
    """The G5-closed verify-chain.py --summary-only over these copies: per-slice problems, global problems, the
    COVERAGE line. Its missing-slices line is left out (this tool counts absence itself); an UNRESOLVED line counts
    against the slice it names."""
    if sha(VERIFY_CHAIN) != G5_SHA256:
        raise SystemExit(f"{VERIFY_CHAIN} is not the G5-closed checker (sha256 {sha(VERIFY_CHAIN)})")
    out = {"per_slice": {}, "global": [], "coverage": None}
    if not dirs:
        return out
    r = subprocess.run([sys.executable, str(VERIFY_CHAIN), "--summary-only", "--expect-target", str(tn), str(tm),
                        "--expect-seed", str(SEED_N), "--expect-slices", str(LEVEL), str(COUNT), "--require-hashes",
                        "--require-g4", *map(str, dirs)], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    out["coverage"] = next((x for x in lines if x.startswith("COVERAGE")), None)
    for x in lines:
        if not x.startswith(("PROBLEM: ", "UNRESOLVED: ")):
            continue
        body = x.split(": ", 1)[1]
        if re.match(rf"fleet \({tn},{tm}\) sliced {COUNT} ways at level {LEVEL}: \d+ slices have no summary", body):
            continue
        m = re.match(rf"s(\d+)of{COUNT}: ", body)
        if m:
            out["per_slice"].setdefault(int(m.group(1)), []).append(f"audit: {body}")
        else:
            out["global"].append(f"audit: {body}")
    if out["coverage"] is None:
        out["global"].append(f"audit: no COVERAGE line (exit {r.returncode}): {r.stderr.strip()[-200:]}")
    return out


_VC = None


def vc():
    """The G5-closed verify-chain.py as a module (the same pinned file the audit runs), for its summary_audit()."""
    global _VC
    if _VC is None:
        if sha(VERIFY_CHAIN) != G5_SHA256:
            raise SystemExit(f"{VERIFY_CHAIN} is not the G5-closed checker (sha256 {sha(VERIFY_CHAIN)})")
        spec = importlib.util.spec_from_file_location("verify_chain_g5", VERIFY_CHAIN)
        _VC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_VC)
    return _VC


def audited(d: Path, tn: int, tm: int) -> dict:
    """The audit's own reading of one copy: its accepted parent evidence per cell (the final summary's entry, or the
    one it recovered from history for a resumed cell) and its entries' children. {"error": why} when the audit cannot
    read the copy: the copy then fails here as well as in the audit run (an empty reading would require nothing)."""
    a = argparse.Namespace(pins={"target": [tn, tm], "seed": SEED_N, "slices": [LEVEL, COUNT]}, require={"hashes", "g4"})
    try:
        r = vc().summary_audit(d, a, [], [])
    except Exception as e:   # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
    pe, en = r.get("parent_evidence") or {}, r.get("entries") or {}
    dic = lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, dict) else {})
    return {"parents": {k: e.get("parents") for k, e in pe.items()},
            "shards": {k: ranges_of(e.get("shards")) for k, e in pe.items()},
            # G5 round 24, finding 2: each shard's children, in range order, beside its range
            "shard_children": {k: tuple(s.get("children") if isinstance(s, dict) else None
                                        for s in sorted(e.get("shards") or [], key=lambda s: tuple(s.get("range") or ())
                                                        if isinstance(s, dict) else ()))
                               for k, e in pe.items() if isinstance(e.get("shards"), list)},
            # each cell's parent sources as the audit accepted them: (level, kind) -> records
            "sources": {k: {(tuple(s.get("level") or ()), s.get("kind")): s.get("records")
                            for s in e.get("parent_sources") or [] if isinstance(s, dict)} for k, e in pe.items()},
            # each cell's stage counts: its level file's records, its reach file's, its keep file's
            "counts": {k: (e.get("children"), dic(e.get("reach")).get("kept"),
                           (dic(e.get("prune")).get("counts") or {}).get("kept")) for k, e in en.items()},
            "children": {k: e.get("children") for k, e in en.items()}}


def ranges_of(shards) -> tuple | None:
    """A cell's production shards as sorted (start, end) parent ranges; None when they are not a list of ranges of
    ints (the audit reports that, and checks that they tile the cell's parents)."""
    if not isinstance(shards, list):
        return None
    out = [tuple(s.get("range") or ()) if isinstance(s, dict) else () for s in shards]
    if not out or any(len(r) != 2 or not nat(r[0]) or not nat(r[1]) or r[0] > r[1] for r in out):
        return None
    return tuple(sorted(out))


_SAMPLE = None


def policy_sample():
    """The pinned replay tool's own sample_indices(), compiled alone from its sha256-checked bytes (the module imports
    pynauty, which this check does not need): the sample the fleet's policy draws in each stratum. A row's count is
    required to be exactly its length (G5 round 16's lead: the lower bound it replaces let a row sample less than the
    policy; measured, every row of the fleet, the control and the calibration samples exactly this)."""
    global _SAMPLE
    if _SAMPLE is None:
        if sha(REPLAY_TOOL) != REPLAY_PINS["tool_sha256"]:
            raise SystemExit(f"{REPLAY_TOOL} is not the fleet's replay tool (sha256 {sha(REPLAY_TOOL)})")
        fn = [n for n in ast.parse(REPLAY_TOOL.read_text()).body
              if isinstance(n, ast.FunctionDef) and n.name == "sample_indices"]
        if len(fn) != 1:
            raise SystemExit(f"{REPLAY_TOOL} does not define sample_indices() once")
        ns = {"math": math, "random": random}
        exec(compile(ast.Module(body=fn, type_ignores=[]), str(REPLAY_TOOL), "exec"), ns)
        _SAMPLE = ns["sample_indices"]
    return _SAMPLE


def prefix_of(d: Path) -> str:
    """The digest of the copy's prefix as its hashes.json records it: every *.g6 of levels <= 12 but the slice shares,
    the same files in every slice of a run. Only full-mode replays cover these levels, so a slice-mode copy's prefix
    must be one a passing full-mode copy has (measured: one prefix per run, in every copy of the fleet, the control and
    the calibration)."""
    h = json.loads((d / "hashes.json").read_text()).get("files") or {}
    names = sorted(n for n in h if n.endswith(".g6") and ".slice-" not in n and re.match(r"\d+-\d+[.]", n)
                   and int(n.split("-")[0]) <= LEVEL)
    lines = "".join(f"{n} {h[n].get('sha256') if isinstance(h[n], dict) else None}\n" for n in names)
    return hashlib.sha256(lines.encode()).hexdigest()


SEED_COUNTS = ("records", "enum2_records", "sampled", "only_seed_file", "only_enum2")


def nat(x) -> bool:
    """A count: an int (not a bool, not a float equal to one), at least zero."""
    return type(x) is int and x >= 0


def replay_scope(c: dict, ev: dict, tn: int) -> list:
    """Why a copy's G4 replay does not have its mode's scope, judged against the audit's accepted evidence (G5 rounds
    14 and 15: a full replay limited to the slice's levels; seed records whose counts were not the seed cells'; a row
    naming a cell but sampling none of it; a resumed cell whose parents were only in the history). The runbook's full
    mode (a worker's first slice) replays every level: levels "", each level-10 seed cell recomputed in full, its
    records equal to the cell's audited children; its slice mode, levels 13 to N. Either way every cell in the mode's
    levels with audited parents (this slice's copies pooled) has a row with exactly those parents, its strata the
    audited shards, and sampled exactly as many as the pinned tool's policy draws from them (G5 round 16's lead); and
    no row names a cell the audit has no evidence for. G5 round 17: every row, stage record and the summary name this
    copy's own run; every parent source the audit accepts for a cell of the mode's levels has its stage record, with
    the audited records, and every stage record's counts are its source cell's audited counts (a reach stage: the
    level file's records in, the reach file's out; a keep stage: the reach file's in, the keep file's out, the
    difference pruned; a slice stage: the keep file's in, re-derived to its share). ev is the audited evidence pooled
    over the slice's copies, and for the prefix (levels <= 12) over every copy of the run with this copy's prefix.
    Measured first: every replay of the (23,65) fleet, the (22,61) control and the (21,57) calibration meets it."""
    slice_parents, slice_shards = ev.get("parents") or {}, ev.get("shards") or {}
    rep, mode, aud = c.get("rep") or {}, c.get("replay_mode"), c.get("audit")
    if not isinstance(aud, dict) or "error" in aud or not isinstance(aud.get("parents"), dict):
        return [f"the audit's own reading of this copy failed ({(aud or {}).get('error') if isinstance(aud, dict) else aud})"]
    if mode not in ("full", "slice"):
        return [f"G4 replay mode {mode!r}"]
    lo, why = (SEED_N + 1 if mode == "full" else LEVEL + 1), []
    if rep.get("levels") != ("" if mode == "full" else f"{LEVEL + 1}-{tn}"):
        why.append(f"a {mode} G4 replay of levels {rep.get('levels')!r}")
    bad_seeds = [s.get("cell") for s in rep.get("seeds") or []
                 if not (s.get("sample_ok") is True and s.get("sample_bad") in ([], None) and s.get("identical") is True
                         # G5 round 24, finding 4: replayable, with no problem recorded
                         and s.get("replayable", True) is True and not s.get("problem"))]
    if bad_seeds:   # G5 round 18: a seed check whose details say it failed, under an identical flag, once passed
        why.append(f"a {mode} G4 replay whose seed checks of {bad_seeds[:3]} did not pass in their details")
    if mode == "full":
        reds = rep.get("red_controls") if isinstance(rep.get("red_controls"), list) else []
        ids = sorted(str(r.get("id")) for r in reds if isinstance(r, dict))
        if ids != sorted(RED_IDS) or len(reds) != len(RED_IDS):
            why.append(f"a full G4 replay whose red controls are {ids}, not each of {list(RED_IDS)} once")
        rows_ = {x.get("cell"): x for x in rep.get("per_cell") or [] if isinstance(x, dict)}
        kids_ = {f"{a}-{b}": v[0] for (a, b), v in (ev.get("counts") or {}).items() if isinstance(v, (list, tuple)) and v}
        unbound = [str(r.get("id")) if isinstance(r, dict) else repr(r) for r in reds if not red_bound(r, rows_, kids_)]
        if unbound:
            why.append(f"a full G4 replay whose red controls {unbound} do not act on its own replayed cells and parents")
        not_red = [str(r.get("id")) if isinstance(r, dict) else repr(r) for r in reds if not red_ok(r)]
        if not_red:
            why.append(f"a full G4 replay whose red controls {not_red} are not red by their own recorded outcome")
        children = (c.get("audit") or {}).get("children") or {}
        full = {s.get("cell"): s for s in rep.get("seeds") or [] if str(s.get("cell", "")).startswith(f"{SEED_N}-")}
        if sorted(full) != sorted(c.get("seeds10") or []):
            why.append(f"a full G4 replay whose level-{SEED_N} seed records are {sorted(full)}, "
                       f"not {sorted(c.get('seeds10') or [])}")
        for cell, s in sorted(full.items()):
            n_ = children.get((SEED_N, int(cell.split("-")[1])))
            if not (s.get("full_check") is True and s.get("full_identical") is True and s.get("identical") is True
                    and nat(n_) and n_ > 0 and all(nat(s.get(k)) for k in SEED_COUNTS)
                    and s["records"] == s["enum2_records"] == n_ and s["only_seed_file"] == s["only_enum2"] == 0
                    and 1 <= s["sampled"] <= n_):
                why.append(f"a full G4 replay whose seed cell {cell} is not recomputed in full over its {n_} audited "
                           f"graphs: records {s.get('records')}, enum2 {s.get('enum2_records')}")
    # the replay's red.json is its summary's red controls, and only a full replay ships one (measured: all 171 full
    # copies of the five bodies of evidence, and none of the 6,365 slice-mode ones)
    rjp = Path(c["dir"]) / "replay" / "red.json" if c.get("dir") else None
    if rjp is not None:
        try:
            rj_ok = (json.loads(rjp.read_text()) == rep.get("red_controls")) if mode == "full" else not rjp.exists()
        except (OSError, ValueError):
            rj_ok = False
        if not rj_ok:
            why.append(f"a {mode} G4 replay whose red.json is not its summary's red controls"
                       if mode == "full" else "a slice-mode G4 replay shipping a red.json")
    run = f"dag-{Path(c['dir']).parent.name}-{Path(c['dir']).name}"
    if [Path(str(x)).name for x in rep.get("run_dirs") or []] != [run]:
        why.append(f"a {mode} G4 replay whose summary names run(s) {rep.get('run_dirs')}, not {run}")
    stray = sorted({Path(str(x.get("run_dir"))).name for x in (rep.get("per_cell") or []) + (rep.get("stages") or [])
                    + [s for s in rep.get("seeds") or [] if isinstance(s, dict) and "run_dir" in s]}   # round 24: seeds
                   - {run})
    if stray:
        why.append(f"a {mode} G4 replay whose rows or stage records name another run: {stray[:3]}")
    # G5 round 22, finding 6: a cell whose every parent was sampled compares every child the audit records for it
    # (measured first: every such row of the five bodies of evidence)
    cn_ = ev.get("counts") or {}
    short = [x.get("cell") for x in rep.get("per_cell") or [] if isinstance(x, dict) and nat(x.get("sampled"))
             and x.get("sampled") == x.get("parents_in_cell") and re.fullmatch(r"\d+-\d+", str(x.get("cell")))
             and (tuple(map(int, str(x["cell"]).split("-"))) in cn_)
             and x.get("production_children") != cn_[tuple(map(int, str(x["cell"]).split("-")))][0]]
    if short:
        why.append(f"a {mode} G4 replay whose fully sampled cells {short[:3]} compare fewer children than the audit records")
    # G5 round 23, finding 5: and no row, sampled in full or not, compares more children than its cell holds
    over = [x.get("cell") for x in rep.get("per_cell") or [] if isinstance(x, dict)
            and re.fullmatch(r"\d+-\d+", str(x.get("cell")))
            and tuple(map(int, str(x["cell"]).split("-"))) in cn_
            and nat(cn_[tuple(map(int, str(x["cell"]).split("-")))][0])
            and not (nat(x.get("production_children")) and nat(x.get("enum2_children"))
                     and x["production_children"] <= cn_[tuple(map(int, str(x["cell"]).split("-")))][0]
                     and x["enum2_children"] <= cn_[tuple(map(int, str(x["cell"]).split("-")))][0])]
    if over:
        why.append(f"a {mode} G4 replay whose cells {over[:3]} compare more children than they hold")
    why += stage_scope(rep.get("stages") or [], ev, lo, tn, mode)
    why += stage_fields(rep.get("stages") or [], ev, c.get("reach_table") or {}, c["slice"], mode)
    rows = {r.get("cell"): r for r in rep.get("per_cell") or []}
    bad = sorted(str(x) for x in rows if not re.fullmatch(r"\d+-\d+", str(x)))
    if bad or len(rows) != len(rep.get("per_cell") or []):
        why.append(f"a {mode} G4 replay whose rows name malformed or repeated cells: {bad[:6]}")
    out = sorted(x for x in rows if x not in bad and not lo <= int(str(x).split("-")[0]) <= tn)
    if out:
        why.append(f"a {mode} G4 replay with rows outside levels {lo} to {tn}: {out[:6]}")
    unknown = sorted(x for x in rows if x not in bad and x not in out
                     and tuple(int(v) for v in str(x).split("-")) not in slice_parents)
    if unknown:
        why.append(f"a {mode} G4 replay with rows for cells the audit has no evidence for: {unknown[:6]}")
    for x, r in rows.items():
        if x not in bad and (r.get("n"), r.get("m")) != tuple(int(v) for v in str(x).split("-")):
            why.append(f"a {mode} G4 replay whose row {x} says n {r.get('n')}, m {r.get('m')}")
    P, draw = REPLAY_PINS, policy_sample()
    samples = {}
    for (n, m), p in sorted(slice_parents.items()):
        if not lo <= n <= tn:
            continue
        r, cell = rows.get(f"{n}-{m}"), f"{n}-{m}"
        if not nat(p):
            why.append(f"audited parents of cell {cell} are not a nonnegative integer: {p!r}")
            continue
        if p == 0:
            continue
        rng = slice_shards.get((n, m))
        if r is None:
            why.append(f"a {mode} G4 replay with no row for cell {cell} ({p} audited parents)")
            continue
        if rng is None or rng[0][0] != 0 or rng[-1][1] != p or any(a[1] != b[0] for a, b in zip(rng, rng[1:])):
            why.append(f"the audited shards of cell {cell} are not ranges tiling its {p} parents: {rng}")
            continue
        drawn = draw(P["seed"], Path(str(r.get("run_dir"))).name, cell, p, P["fraction"], P["min_per_shard"],
                     P["whole_max"], P["max_per_shard"], list(rng))
        want = len(drawn)
        samples[cell] = set(drawn)
        # G5 round 24, finding 2: a shard the policy draws in full contributes all its children to the comparison, so
        # the compared children are at least those of every fully drawn shard (measured first on every row)
        sc = (ev.get("shard_children") or {}).get((n, m))
        if sc is not None and len(sc) == len(rng) and all(nat(x) for x in sc):
            ds = sorted(drawn)
            full_kids = sum(k for (a, b), k in zip(rng, sc)
                            if sum(1 for x in ds if a <= x < b) == b - a)
            if not (nat(r.get("production_children")) and nat(r.get("enum2_children"))
                    and r["production_children"] >= full_kids and r["enum2_children"] >= full_kids):
                why.append(f"a {mode} G4 replay whose row of {cell} compares {r.get('production_children')} children, "
                           f"fewer than the {full_kids} of its fully drawn shards")
        if not (nat(r.get("parents_in_cell")) and r["parents_in_cell"] == p and nat(r.get("sampled"))
                and r["sampled"] == want and r.get("strata") == len(rng) and r.get("stratum") == "shards"):
            why.append(f"a {mode} G4 replay whose row of {cell} has parents {r.get('parents_in_cell')}, sampled "
                       f"{r.get('sampled')} over {r.get('strata')} {r.get('stratum')}, for {p} audited parents in "
                       f"{len(rng)} shards (the policy samples {want})")
    # G5 round 24, finding 3: a red control's parent is one the policy drew in its cell (R3 only when it says so)
    if mode == "full":
        off = [str(r.get("id")) for r in rep.get("red_controls") or [] if isinstance(r, dict)
               and (r.get("id") != "R3" or r.get("from_sample") is True)
               and (r.get("cell") not in samples or r.get("index") not in samples[r.get("cell")])]
        if off:
            why.append(f"a full G4 replay whose red controls {off} act on a parent the policy did not draw")
    return why


def stage_scope(stages: list, ev: dict, lo: int, tn: int, mode: str) -> list:
    """G5 round 17, finding 2: the replay's stage records against the audited evidence. Every parent source (level,
    kind) the audit accepts for a cell of levels lo..tn needs a stage record with its audited records; every stage
    record's counts are its source cell's audited ones, by kind; each is ok, with its kind's status."""
    why = []
    recs = {}
    for s in stages:
        key = (tuple(s.get("level") or ()), s.get("kind"))
        if key in recs:
            why.append(f"a {mode} G4 replay with two stage records of {key}")
        recs[key] = s
    need = {}
    for (n, m), src in (ev.get("sources") or {}).items():
        if lo <= n <= tn:
            for key, r_ in src.items():
                need[key] = r_
    miss = sorted(k for k in need if k not in recs)
    if miss:
        why.append(f"a {mode} G4 replay with no stage record of {len(miss)} audited parent source(s): {miss[:3]}")
    counts = ev.get("counts") or {}
    status = {"reach": "re-derived", "keep": "subsequence of its input", "keep+slice": "re-derived"}
    for key, s in sorted(recs.items(), key=lambda kv: str(kv[0])):
        lvl, kind = key
        ch, rk, pk = counts.get(lvl, (None, None, None))
        ist = s.get("input_stage") or {}
        if kind == "reach":
            ok = nat(ch) and nat(rk) and s.get("input_records") == ch and s.get("records") == rk == s.get("derived_records")
        elif kind == "keep":
            ok = (nat(rk) and nat(pk) and s.get("input_records") == rk and s.get("records") == pk
                  and s.get("pruned") == rk - pk)
        elif kind == "keep+slice":
            ok = (nat(rk) and nat(pk) and s.get("input_records") == pk and ist.get("input_records") == rk
                  and ist.get("records") == pk and ist.get("ok") is True and nat(s.get("records"))
                  and s.get("records") == s.get("derived_records"))
        else:
            ok = False
        ok = ok and s.get("ok") is True and s.get("status") == status.get(kind)
        if key in need:
            ok = ok and s.get("records") == need[key]
        if not ok:
            why.append(f"a {mode} G4 replay whose stage record of {lvl} ({kind}) says in {s.get('input_records')}, out "
                       f"{s.get('records')}, status {s.get('status')!r}, for audited counts (level file, reach, keep) "
                       f"{(ch, rk, pk)}" + (f" and {need[key]} audited parent records" if key in need else ""))
    return why


RUN_NAME = re.compile(r"(dag-\d+-\d+-L\d+-tri-pf74-s\d+of\d+|prefix-\d+-\d+-L\d+-tri-pf74)")


def run_names(x, out=None) -> set:
    """G5 round 21: every run directory a record names anywhere in its values or keys (paths, commands)."""
    out = set() if out is None else out
    if isinstance(x, dict):
        for k, v in x.items():
            run_names(k, out)
            run_names(v, out)
    elif isinstance(x, list):
        for v in x:
            run_names(v, out)
    elif isinstance(x, str):
        out.update(RUN_NAME.findall(x))
    return out


def path_tokens(x, out=None) -> list:
    """Every absolute path a record names: its string values and keys, and the words of a recorded command."""
    out = [] if out is None else out
    if isinstance(x, dict):
        for k, v in x.items():
            path_tokens(k, out)
            path_tokens(v, out)
    elif isinstance(x, list):
        for v in x:
            path_tokens(v, out)
    elif isinstance(x, str):
        out += [w for w in (x.split() if " " in x else [x]) if len(w) > 1 and w.startswith("/")]   # not "21 / 23"
    return out


def paths_ok(mj: dict, runs: set) -> list:
    """G5 round 22, finding 1: each absolute path the record names, on its own, is a file of an allowed run (the run
    directory a component of it), the checkout's data, check or filter tree, or the interpreter the record itself
    names. A path naming no run at all (a part manifest moved to /tmp) once passed beside a stage file that did.
    Returns the paths that are none of these."""
    py = str((mj.get("software_sha256") or {}).get("python") or "").split()[:1]
    bad = []
    for w in path_tokens(mj):
        parts = Path(w).parts
        in_run = [c for c in parts if RUN_NAME.fullmatch(c)]
        tool = (len(parts) >= 3 and parts[-3] == "unit-distance-22" and parts[-2] in ("data", "check", "filter")) or \
               (len(parts) >= 2 and parts[-2:] == ("unit-distance-22", "data"))
        if not ((len(in_run) == 1 and in_run[0] in runs) or tool or w in py):
            bad.append(w)
    return bad


def at(x, run: str, *tail: str) -> bool:
    """The path is <...>/<run>/<tail...>: the run directory exactly where the file must lie."""
    parts = Path(str(x)).parts
    return len(parts) > len(tail) and parts[-len(tail) - 1:] == (run, *tail)


def red_bound(r, rows: dict, cell_kids: dict | None = None) -> bool:
    """G5 round 21, finding 5: a red control acts on this replay's own data: its cell a replayed cell (for all but R3 one
    with sampled parents, as replay-398.py picks it from the sampled blocks), its index a parent of that cell, and R3's
    dropped member one of the 324 graphs Mode 398 adds to the 74 (indices 74 to 397). Measured first: every red control
    of every full replay of the five bodies of evidence."""
    if not isinstance(r, dict):
        return False
    row = rows.get(r.get("cell"))
    ok = (isinstance(row, dict) and nat(r.get("index")) and nat(row.get("parents_in_cell"))
          and r["index"] < row["parents_in_cell"])
    if r.get("id") == "R4":   # G5 round 22, finding 5: R4 compares parent i with parent i+1, so i+1 must exist
        ok = ok and r["index"] + 1 < row["parents_in_cell"]
        kids = (cell_kids or {}).get(r.get("cell"))   # G5 round 24, finding 3: and its block is within the cell
        ok = ok and (kids is None or (nat(r.get("next_block_size")) and r["next_block_size"] <= kids))
    if r.get("id") == "R3":
        mm = re.fullmatch(r"enum2 without member (\d+) \(one of the 324\) against the production block", str(r.get("control")))
        return ok and bool(mm) and 74 <= int(mm.group(1)) < 398
    return ok and nat(row.get("sampled")) and row["sampled"] > 0


def red_ok(r) -> bool:
    """G5 round 19, finding 3: a red control counts only when its recorded outcome makes it red by the producer's own
    predicate (replay-398.py red_controls): its baseline identical (a nonempty production block), and R1 the mutated
    parent's comparison differing, R2 the dropped record missing, R5a the equal-count check passing where the set
    check fails, R5b the subset check passing where the set check fails, R3 extra children that only the dropped member
    forbids, none lost, its counts adding up; R4 records its outcome only. went_red must say so too (a control whose
    baseline failed once counted red on its flag)."""
    if not isinstance(r, dict) or r.get("baseline_identical") is not True or r.get("went_red") is not True:
        return False
    n = lambda k: r.get(k) if nat(r.get(k)) else None
    rid, blk = r.get("id"), (n("block_size") or 0) > 0
    if rid == "R1":   # G5 round 22, finding 5: and each control's count invariants (round 24: every count a count)
        return (blk and n("only_production") is not None and n("only_enum2") is not None
                and r["only_production"] + r["only_enum2"] > 0 and r["only_production"] <= r["block_size"])
    if rid == "R2":   # one record dropped from an identical block leaves exactly that one on enum2's side
        return blk and n("only_enum2") == 1
    if rid == "R4":   # G5 round 23, finding 6: its next block a real block
        return blk and n("next_block_size") is not None
    if rid == "R5a":
        return blk and r.get("wrong_equal_count_check") == "PASS" and r.get("set_check") == "FAIL"
    if rid == "R5b":
        return blk and r.get("wrong_subset_check") == "PASS" and r.get("set_check") == "FAIL"
    if rid == "R3":
        return (n("missing") == 0 and (n("extra") or 0) >= 1 and r.get("extras_contain_exactly_that_member") is True
                and n("production_children") is not None
                and r.get("enum2_children_without_member") == r["production_children"] + r["extra"])
    return False


def replay_pins(rep: dict) -> list:
    """The G4 replay's recorded tool, data, seed and sampling policy must be the fleet's (REPLAY_PINS); G5 round 18: the
    --scope-only path skipped this, and a replay recording another seed passed it."""
    pins = {k: rep.get(k) for k, v in REPLAY_PINS.items() if rep.get(k) != v and str(rep.get(k)) != str(v)}
    return [f"G4 replay not the fleet's tool, data or sampling policy: {pins}"] if pins else []


def stage_fields(stages: list, ev: dict, reach_table: dict, i: int, mode: str) -> list:
    """G5 round 18, finding 2: each stage record's identity and parameters, not only its counts. Its source is its
    level and kind's own file (a slice stage's, this slice's share); a reach stage's k is the reach table's for its
    cell, and its reach_json_k the same; a keep stage reads that cell's reach file; a slice stage names this slice and
    its input stage is the keep file's, clean; and the cell it was checked for is at the next level, with this stage
    among its audited parent sources. Measured first: every stage record of the fleet, the control and the
    calibration meets it."""
    why = []
    for s in stages:
        lvl = s.get("level")
        if not (isinstance(lvl, list) and len(lvl) == 2 and all(nat(x) for x in lvl)):
            why.append(f"a {mode} G4 replay with a stage record of level {lvl!r}")
            continue
        n, m = lvl
        kind = s.get("kind")
        want = {"reach": f"{n}-{m}.reach.g6", "keep": f"{n}-{m}.keep.g6",
                "keep+slice": f"{n}-{m}.slice-{i}-of-{COUNT}.g6"}.get(kind)
        ok = s.get("source") == want
        if kind == "reach":
            k_tab = (reach_table.get(str(n)) or {}).get(str(m))
            ok = ok and nat(k_tab) and s.get("k") == s.get("reach_json_k") == k_tab
        elif kind == "keep":
            ok = ok and s.get("input") == f"{n}-{m}.reach.g6"
        elif kind == "keep+slice":
            ist = s.get("input_stage") or {}
            ok = (ok and s.get("slice") == [i, COUNT] and ist.get("input") == f"{n}-{m}.reach.g6"
                  and ist.get("status") == "subsequence of its input" and ist.get("ok") is True)
        mm = re.fullmatch(r"(\d+)-(\d+)", str(s.get("for_cell")))
        fc = (int(mm.group(1)), int(mm.group(2))) if mm else None
        ok = ok and fc is not None and fc[0] == n + 1 and ((n, m), kind) in ((ev.get("sources") or {}).get(fc) or {})
        if not ok:
            why.append(f"a {mode} G4 replay whose stage record of ({n},{m}) {kind} says source {s.get('source')!r}, "
                       f"k {s.get('k')}/{s.get('reach_json_k')}, for cell {s.get('for_cell')!r}: not its own file, "
                       "parameters or consumer")
    return why


def seeds10_of(d: Path) -> list:
    """The copy's level-10 seed cells, from its reach.json table (the audit checks that table against its target)."""
    table = json.loads((d / "reach.json").read_text()).get("table") or {}
    return [f"{SEED_N}-{m}" for m in sorted(int(x) for x in table.get(str(SEED_N), []))]


EVIDENCE = ("parents", "shards", "sources", "counts", "shard_children")


def pooled_parents(cs: list, keep=lambda cell: True) -> tuple:
    """The audited evidence of these copies, pooled (a resumed cell's may be in another copy): parents, shards,
    sources and stage counts per cell, for the cells keep() accepts, and the cells whose copies disagree (measured:
    none of the fleet's 35 slices with several copies does)."""
    out, clash = {k: {} for k in EVIDENCE}, []
    for c in cs:
        aud = c.get("audit") if isinstance(c.get("audit"), dict) else {}
        for what in EVIDENCE:
            into = out[what]
            for cell, v in (aud.get(what) or {}).items():
                if not keep(cell):
                    continue
                if cell in into and into[cell] != v:
                    clash.append(f"copies disagree on the audited {what} of cell {cell[0]}-{cell[1]}: {into[cell]} and {v}")
                into.setdefault(cell, v)
    return out, clash


def prefix_pools(all_copies: list) -> tuple:
    """G5 round 17, finding 1: the prefix (levels <= 12) is one set of files per run, and the audit pools its evidence
    over the fleet; so is it pooled here, over every copy with the same prefix digest."""
    groups = {}
    for c in all_copies:
        groups.setdefault(c.get("prefix"), []).append(c)
    pools, clash = {}, []
    for dig, cs in groups.items():
        pools[dig], cl = pooled_parents(cs, keep=lambda cell: cell[0] <= LEVEL)
        clash += [f"prefix {str(dig)[:12]}: {x}" for x in cl]
    return pools, clash


def evidence_for(c: dict, slice_ev: dict, pools: dict) -> dict:
    """A copy's evidence: its slice's pooled, and for the prefix levels, its prefix's pool over the run."""
    pool = pools.get(c.get("prefix")) or {k: {} for k in EVIDENCE}
    return {k: {**{cell: v for cell, v in slice_ev[k].items() if cell[0] > LEVEL}, **pool[k]} for k in EVIDENCE}


def verify_manifests(d: Path, aud: dict, hj: dict, mode: str | None = None) -> list:
    """G5 round 17, finding 4: the production stage verifications the copy ships (verify/<n>-<m>.verify.manifest.json).
    One per run-summary cell from the seed level; each a clean udenum --verify-parents over its cell's stage file (the
    reach file below the prune level, the keep file from it), against the pinned forbidden set, its parts tiling the
    records with nothing written; its records the audited stage count, and the file's sha256 and records those
    hashes.json records where it records them. Measured first: every manifest of the fleet, the control and the
    calibration meets it."""
    why = []
    rs = json.loads((d / "run-summary.json").read_text())
    cells = {(e.get("n"), e.get("m")) for e in rs.get("levels") or [] if isinstance(e, dict)
             and nat(e.get("n")) and e["n"] >= SEED_N}
    vd = d / "verify"
    vms = {}
    for q in (sorted(vd.glob("*.verify.manifest.json")) if vd.is_dir() else []):
        mm = re.fullmatch(r"(\d+)-(\d+)\.verify\.manifest\.json", q.name)
        if mm:
            vms[(int(mm.group(1)), int(mm.group(2)))] = q
    if set(vms) != cells:
        why.append(f"verify manifests for cells {sorted(set(vms) - cells)[:3]} beyond, and none for "
                   f"{sorted(cells - set(vms))[:3]} of, the run-summary cells")
    counts = aud.get("counts") or {}
    for cell, q in sorted(vms.items()):
        vm = json.loads(q.read_text())
        kind = "keep" if cell[0] >= PIPELINE["prune_from"] else "reach"
        ch, rk, pk = counts.get(cell, (None, None, None))
        want = pk if kind == "keep" else rk
        parts = vm.get("parts") if isinstance(vm.get("parts"), list) else []
        rng = [tuple(x.get("range") or ()) if isinstance(x, dict) else () for x in parts]
        tiled = (bool(rng) and all(len(r) == 2 and nat(r[0]) and nat(r[1]) for r in rng) and rng[0][0] == 0
                 and rng[-1][1] == vm.get("records") and all(x[1] == y[0] for x, y in zip(rng, rng[1:])))
        # G5 round 20, finding 1: each part the verification the check names, not another operation: udenum's target
        # the next level's (n+1, m+n), so that no parent can reach it and each is checked and skipped, every parent
        # seen and degree-skipped, nothing processed, generated or rejected, its manifest the run's own for the range
        # (measured first: every verify manifest of the fleet, the control, the calibration, the sample and the re-run)
        st_ok = lambda s, r: (isinstance(s, dict) and s.get("parents_seen") == r[1] - r[0]
                              and s.get("parents_degree_skipped") == r[1] - r[0]
                              and all(s.get(k) == 0 for k in ("parents_processed", "children_written", "bad_sets",
                                                              "neighbourhoods", "neighbourhood_orbit_reps",
                                                              "neighbourhoods_bad", "child_orbit_rejected")))
        stats = tiled and all(st_ok(x.get("udenum_stats"), r)
                              and Path(str(x.get("udenum_manifest"))).parent.name == "_verify"
                              and Path(str(x.get("udenum_manifest"))).name == f"{cell[0]}-{cell[1]}.{r[0]}-{r[1]}.manifest.json"
                              for x, r in zip(parts, rng))
        name = Path(str(vm.get("stage_file"))).name
        h = hj.get(name)
        ok = (vm.get("exit_status") == 0 and vm.get("kind") == "verify" and list(vm.get("level") or []) == list(cell)
              and vm.get("check") == VERIFY_CHECK and vm.get("forbidden_set") == 398
              and vm.get("udenum_target") == [cell[0] + 1, cell[1] + cell[0]]
              and Path(str(vm.get("forbidden_file"))).name == "forbidden-398.json"
              and vm.get("forbidden_sha256") == REPLAY_PINS["forbidden_sha256"] and vm.get("stage_kind") == kind
              and name == f"{cell[0]}-{cell[1]}.{kind}.g6" and nat(want) and nat(vm.get("records"))
              and vm.get("records") == vm.get("parents_seen") == want and stats
              and (h is None or (isinstance(h, dict) and h.get("sha256") == vm.get("stage_sha256")
                                 and h.get("records") == vm.get("records"))))
        # G5 round 21, finding 1: every path it records (its stage file, each part's manifest) in one run: the copy's
        # own, or for a prefix cell of a slice-mode copy the run that computed the prefix (evaluate() and
        # scope_problems() bind that run to a full-mode copy with the same prefix)
        rn = run_names(vm)
        own = f"dag-{d.parent.name}-{d.name}"
        ok = ok and len(rn) == 1 and (rn == {own} or (cell[0] <= LEVEL and mode != "full"))
        # G5 round 22, finding 1: and each path on its own: the stage file directly in that run, each part's manifest
        # in its _verify directory under the range's own name, no path outside it but the checkout's data
        vr = next(iter(rn), None)
        ok = ok and vr is not None and at(vm.get("stage_file"), vr, name) and not paths_ok(vm, {vr}) \
            and all(at(x.get("udenum_manifest"), vr, "_verify", f"{cell[0]}-{cell[1]}.{r[0]}-{r[1]}.manifest.json")
                    for x, r in zip(parts, rng) if isinstance(x, dict))
        if not ok:
            why.append(f"verify/{q.name} is not a clean verification of {name} ({want} audited records): exit "
                       f"{vm.get('exit_status')}, {vm.get('stage_kind')} {vm.get('records')} records, seen "
                       f"{vm.get('parents_seen')}, parts tiled {tiled}")
    return why


def production_manifests(d: Path, hj: dict, tn: int, tm: int, ev: dict | None = None) -> list:
    """G5 round 18, finding 3: the enumeration and pruning manifests the copy ships (its top levels). Each is a clean
    success bound to the copy's own files. An enumeration manifest has exit 0, the pinned forbidden set, and its
    children file equal to the level file hashes.json records. A pruning manifest has exit 0, no mutation, the run's
    target, filter set 74 and forbidden set 398. Its certificate, keep and UNKNOWN outputs are the files shipped (the
    keep and UNKNOWN files by hashes.json, the certificate file by its own sha256), its input is the reach file
    hashes.json records, and its reach.json and data files are the shipped and pinned ones. The target cell's two
    manifests must be there. Measured first: every shipped manifest of the fleet, the control and the calibration
    meets it."""
    why = []
    # G5 round 21, finding 3: every cell of the top two levels ships both its manifests, and no other cell does (measured:
    # every copy of the five bodies of evidence); deleting a record once removed its checks with it
    rs_cells = {(e.get("n"), e.get("m")) for e in (json.loads((d / "run-summary.json").read_text()).get("levels") or [])
                if isinstance(e, dict) and nat(e.get("n")) and nat(e.get("m")) and e["n"] >= tn - 1}
    for kind in ("manifest", "prune.manifest"):
        have = {tuple(map(int, q.name.split(".")[0].split("-"))) for q in d.glob(f"*.{kind}.json")
                if re.fullmatch(rf"\d+-\d+\.{re.escape(kind)}\.json", q.name)}
        if have != rs_cells or (tn, tm) not in have:
            why.append(f"{kind} files for cells {sorted(have)} are not the top two levels' {sorted(rs_cells)}")
    rj = sha(d / "reach.json") if (d / "reach.json").is_file() else None
    for q in sorted(d.glob("*.manifest.json")):
        mm = re.fullmatch(r"(\d+-\d+)\.(prune\.)?manifest\.json", q.name)
        if not mm:
            why.append(f"{q.name}: not a level's manifest")
            continue
        cell, mj = mm.group(1), json.loads(q.read_text())
        if not mm.group(2):
            ins = {Path(k).name: v for k, v in (mj.get("inputs_sha256") or {}).items()}
            ps = mj.get("parent_sources") if isinstance(mj.get("parent_sources"), list) else [None]
            n_, m_ = map(int, cell.split("-"))
            rtab = (json.loads((d / "reach.json").read_text()).get("table") or {}) if rj else {}
            k_tab = (rtab.get(str(n_)) or {}).get(str(m_))
            # G5 round 19, finding 4: its children counted as the level file hashes.json records, its forbidden set
            # and reach table the pinned and shipped ones, its pruning the run's, every parent source the keep file
            # hashes.json records with its records (a manifest claiming a child beside an empty level file passed)
            lv = [tuple(s.get("level") or ()) if isinstance(s, dict) else () for s in ps]
            ok = (mj.get("exit_status") == 0 and mj.get("forbidden_set") == 398
                  # G5 round 21, finding 2: the sources in order, each once, their total the audited parents, the
                  # parent file this cell's, and every path the record names in this copy's own run
                  and lv == sorted(lv) and len(set(lv)) == len(lv)
                  and (ev is None or sum(s.get("records") or 0 for s in ps if isinstance(s, dict))
                       == (ev.get("parents") or {}).get((n_, m_)))
                  and Path(str(mj.get("parent_file"))).name == f"{cell}.g6"
                  and Path(str(mj.get("parent_file"))).parent.name == "_parents"
                  and all(isinstance(s, dict) and Path(str(s.get("file"))).name
                          == f"{s['level'][0]}-{s['level'][1]}.{s.get('kind')}.g6" for s in ps if isinstance(s, dict)
                          and isinstance(s.get("level"), list) and len(s["level"]) == 2)
                  and run_names(mj) == {f"dag-{d.parent.name}-{d.name}"}
                  # G5 round 22, findings 1 and 3: each path on its own, in its place in the run; and the parent
                  # file's digest the concatenation of its sources, wherever the copy ships them (else all empty)
                  and not paths_ok(mj, {f"dag-{d.parent.name}-{d.name}"})
                  and at(mj.get("parent_file"), f"dag-{d.parent.name}-{d.name}", "_parents", f"{cell}.g6")
                  and all(at(s.get("file"), f"dag-{d.parent.name}-{d.name}", f"{s['level'][0]}-{s['level'][1]}."
                             f"{s.get('kind')}.g6") for s in ps if isinstance(s, dict) and isinstance(s.get("level"), list))
                  and parent_digest_ok(d, mj, hj)
                  and mj.get("children_file_sha256") == (hj.get(f"{cell}.g6") or {}).get("sha256") is not None
                  and nat(mj.get("children_written"))
                  and mj.get("children_written") == (hj.get(f"{cell}.g6") or {}).get("records")
                  and ins.get("forbidden-398.json") == PRUNE_DATA["forbidden-398.json"]
                  and rj is not None and ins.get("reach.json") == rj
                  and mj.get("reach") == {"enabled": True, "k": k_tab, "reach_json_sha256": rj,
                                          "table_level": (mj.get("reach") or {}).get("table_level"),
                                          "table_parent_level": (mj.get("reach") or {}).get("table_parent_level")}
                  and nat(k_tab) and (mj.get("reach") or {}).get("table_level") == rtab.get(str(n_))
                  and (mj.get("reach") or {}).get("table_parent_level") == rtab.get(str(n_ - 1))
                  and mj.get("pruning") == {"enabled": True, "prune_from": LEVEL, "prune_filter_only": True,
                                            "triangles": True, "filter_set": 74}
                  # G5 round 20, finding 2: its parent sources the audited ones, all of them, and its parent range
                  # their records (a source deleted, the range shortened to match, once passed)
                  and (ev is None or {(tuple(s.get("level") or ()), s.get("kind")): s.get("records")
                                      for s in ps if isinstance(s, dict)} == (ev.get("sources") or {}).get((n_, m_)))
                  and mj.get("parent_range") == [0, sum(s.get("records") or 0 for s in ps if isinstance(s, dict))]
                  and mj.get("shard_id") == f"aggregate-{cell}"
                  and bool(ps) and all(isinstance(s, dict) and s.get("kind") == "keep"
                                       and isinstance(s.get("level"), list) and len(s["level"]) == 2
                                       and s["level"][0] == n_ - 1
                                       and s.get("sha256") == (hj.get(f"{s['level'][0]}-{s['level'][1]}.keep.g6")
                                                               or {}).get("sha256") is not None
                                       and s.get("records") == (hj.get(f"{s['level'][0]}-{s['level'][1]}.keep.g6")
                                                                or {}).get("records")
                                       for s in ps))
        else:
            outs = {Path(k).name: v for k, v in (mj.get("outputs_sha256") or {}).items()}
            ins = {Path(k).name: v for k, v in (mj.get("inputs_sha256") or {}).items()}
            certs = d / f"{cell}.certs.jsonl"
            ok = (mj.get("exit_status") == 0 and not any((mj.get("mutation") or {}).values())
                  and mj.get("target") == [tn, tm] and mj.get("filter_set") == 74 and mj.get("forbidden_set") == 398
                  and all(outs.get(f"{cell}.{x}.g6") == (hj.get(f"{cell}.{x}.g6") or {}).get("sha256") is not None
                          for x in ("keep", "UNKNOWN"))
                  and certs.is_file() and outs.get(certs.name) == sha(certs)
                  and ins.get(f"{cell}.reach.g6") == (hj.get(f"{cell}.reach.g6") or {}).get("sha256") is not None
                  and rj is not None and ins.get("reach.json") == rj
                  and all(ins.get(k) == v for k, v in PRUNE_DATA.items())
                  # G5 round 19, finding 4: the checker's own verdict, its counts, and the step's counts agree, and
                  # nothing is recorded as a problem (a REJECT verdict with problems once passed on exit 0)
                  and checker_ok(mj)
                  # G5 round 20, finding 3: and they are the files' and the audit's (one checked graph once passed beside
                  # an empty certificate file)
                  and prune_bound(d, cell, mj, hj, tn, tm, ev)
                  # G5 round 21, finding 4: the checker it records ran on this cell's own files, in this run
                  and checker_command_ok(d, cell, mj)
                  and run_names(mj) == {f"dag-{d.parent.name}-{d.name}"}
                  and not paths_ok(mj, {f"dag-{d.parent.name}-{d.name}"})
                  and at(mj.get("level_file"), f"dag-{d.parent.name}-{d.name}", f"{cell}.reach.g6"))
        if not ok:
            why.append(f"{q.name} is not a clean success bound to the copy's files: exit {mj.get('exit_status')}")
    return why


def prune_bound(d: Path, cell: str, mj: dict, hj: dict, tn: int, tm: int, ev: dict | None) -> bool:
    """G5 round 20, finding 3: a pruning manifest's counts are its artifacts' and the audit's: its input the reach file's
    records, its kept the keep file's, its unknown the UNKNOWN file's (hashes.json), its certificate file one record per
    graph checked, by verdict the verified counts; its triangle prover's statistics the step's triangle counts, nothing
    failed, lifted wrongly or hit internally; the filter's survivors its input less its TU, the triangles' survivors
    those less the triangles' TU and refuted, the embedder's survivors the triangles'; its level and level file its
    cell's; the TU rule's bound the run's target; and (with the audit's evidence) its input and kept the audited stage
    counts. Measured first: every pruning manifest of the fleet, the control, the calibration, the sample and the
    re-run (14,002)."""
    cn, vc_, ts = mj.get("counts") or {}, mj.get("verified_counts") or {}, mj.get("triangles_stats") or {}
    n_, m_ = map(int, cell.split("-"))
    rec = lambda name: (hj.get(name) or {}).get("records")
    try:
        certs = [json.loads(x) for x in (d / f"{cell}.certs.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return False
    by = {}
    for r in certs:
        by[r.get("verdict") if isinstance(r, dict) else None] = by.get(r.get("verdict") if isinstance(r, dict) else None, 0) + 1
    au = (ev.get("counts") or {}).get((n_, m_)) if ev is not None else None
    return (cn.get("input") == rec(f"{cell}.reach.g6") and cn.get("kept") == rec(f"{cell}.keep.g6")
            and cn.get("unknown") == rec(f"{cell}.UNKNOWN.g6")
            and len(certs) == vc_.get("records") and set(by) <= {"tu", "refuted", "unknown", "embedded"}
            and all(by.get(k, 0) == vc_.get(k) for k in ("tu", "refuted", "unknown", "embedded"))
            and ts.get("graphs") == cn.get("survivors") and ts.get("pass") == cn.get("tri_survivors")
            and ts.get("tu") == cn.get("tri_tu") and ts.get("refuted") == cn.get("tri_refuted")
            and all(ts.get(k) == 0 for k in ("verify_fail", "lift_fail", "internal"))
            and cn.get("survivors") == (cn.get("input") or 0) - (cn.get("tu") or 0)
            and cn.get("tri_survivors") == (cn.get("survivors") or 0) - (cn.get("tri_tu") or 0) - (cn.get("tri_refuted") or 0)
            and (mj.get("embedder") or {}).get("survivors") == cn.get("tri_survivors")
            and mj.get("level") == [n_, m_] and Path(str(mj.get("level_file"))).name == f"{cell}.reach.g6"
            and (mj.get("tu_rule_bound") or {}).get("n") == tn
            and (mj.get("tu_rule_bound") or {}).get("proved_upper_bound") == tm
            and (ev is None or (au is not None and au[1] == cn.get("input") and au[2] == cn.get("kept"))))


def parent_digest_ok(d: Path, mj: dict, hj: dict) -> bool:
    """G5 round 22, finding 3: an enumeration manifest's parent-file digest is the concatenation of its sources: computed
    from the shipped source files when the copy ships them all, the empty file's when every source is empty; when a
    nonempty source is not shipped, the digest is bound by the full-directory check of a complete run (the full re-run
    for (23,65)), not here."""
    ps = [s for s in mj.get("parent_sources") or [] if isinstance(s, dict)]
    pf = str(mj.get("parent_file"))
    got = (mj.get("inputs_sha256") or {}).get(pf)
    if all(s.get("records") == 0 for s in ps):
        return got == hashlib.sha256(b"").hexdigest()
    files = [d / Path(str(s.get("file"))).name for s in ps]
    if not all(f.is_file() for f in files):
        # G5 round 23, finding 4: one nonempty source among empty ones is their concatenation, whatever is shipped
        full = [s for s in ps if s.get("records") != 0]
        if len(full) == 1 and all(s.get("sha256") == hashlib.sha256(b"").hexdigest() for s in ps if s is not full[0]):
            return got == full[0].get("sha256")
        return True
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return got == h.hexdigest()


def checker_command_ok(d: Path, cell: str, mj: dict) -> bool:
    """G5 round 21, finding 4: the certificate checker's recorded command is the rhombus checker the manifest names, run
    on this cell (--expect-n, --expect-m), on this run's reach, UNKNOWN and certificate files and its own work
    directory, with the forbidden set 398 and the checkout's data (measured: every pruning manifest)."""
    import shlex
    tc_ = mj.get("triangles_checker") or {}
    try:
        argv = shlex.split(str(tc_.get("command") or ""))
    except ValueError:
        return False
    run = f"dag-{d.parent.name}-{d.name}"
    n_, m_ = cell.split("-")
    py = str((mj.get("software_sha256") or {}).get("python") or "").split()
    # G5 round 22, finding 4: the program run is the interpreter the manifest records, running the checker it names
    if len(argv) < 5 or argv[:3] != ["nice", "-n", "10"] or not py or argv[3] != py[0] or argv[4] != tc_.get("path") \
            or Path(argv[4]).name != "udcheck_rhombus.py" or tc_.get("from_environment") is not False:
        return False
    opts, pos, k = {}, [], 5
    while k < len(argv):
        if argv[k].startswith("--") and k + 1 < len(argv):
            opts[argv[k]] = argv[k + 1]
            k += 2
        else:
            pos.append(argv[k])
            k += 1
    in_run = lambda x, name, parent=None: (Path(x).name == name and
                                           (Path(x).parent.name == run if parent is None else
                                            Path(x).parent.name == parent and Path(x).parent.parent.parent.name == run))
    return (set(opts) == {"--expect-n", "--expect-m", "--graphs", "--unknown-file", "--data-dir", "--forbidden-set",
                          "--work-dir"}
            and opts["--expect-n"] == n_ and opts["--expect-m"] == m_ and opts["--forbidden-set"] == "398"
            and in_run(opts["--graphs"], f"{cell}.reach.g6") and in_run(opts["--unknown-file"], f"{cell}.UNKNOWN.g6")
            and Path(opts["--data-dir"]).name == "data" and Path(opts["--data-dir"]).parent.name == "unit-distance-22"
            and Path(opts["--work-dir"]).name == "check-work" and Path(opts["--work-dir"]).parent.name == cell
            and Path(opts["--work-dir"]).parent.parent.name == "_prune"
            and Path(opts["--work-dir"]).parent.parent.parent.name == run
            and len(pos) == 1 and in_run(pos[0], f"{cell}.certs.jsonl"))


def checker_ok(mj: dict) -> bool:
    """A pruning manifest's certificate check, read from its own fields: the checker's line says ACCEPT, its counts are
    the verified counts, the verified counts are the step's counts, no problem is recorded, no triangle proof passed
    silently, and the embedder was skipped as the filter-only prune requires (G5 round 19, finding 4)."""
    line, vc_, cn = str(mj.get("checker") or ""), mj.get("verified_counts") or {}, mj.get("counts") or {}
    if not line.startswith("ACCEPT certificates ") or not isinstance(vc_, dict) or not isinstance(cn, dict):
        return False
    said = dict(x.split("=", 1) for x in line.split()[2:] if "=" in x)
    keys = ("input", "tu", "tri_tu", "refuted", "tri_refuted", "embedded", "unknown", "kept", "pruned")
    if not all(nat(cn.get(k)) for k in keys) or not all(nat(vc_.get(k)) for k in
                                                         ("records", "tu", "tri_tu", "refuted", "tri_refuted",
                                                          "embedded", "unknown", "kept")):
        return False
    # measured on every pruning manifest (14,002): the certificate file's TU and refuted records are the filter's and
    # the triangle prover's together; the rest are the step's own counts
    want = {"records": cn["input"], "tu": cn["tu"] + cn["tri_tu"], "refuted": cn["refuted"] + cn["tri_refuted"],
            "embedded": cn["embedded"], "unknown": cn["unknown"], "kept": cn["kept"], "tri_tu": cn["tri_tu"],
            "tri_refuted": cn["tri_refuted"]}
    return (all(vc_.get(k) == v for k, v in want.items()) and cn["pruned"] == cn["input"] - cn["kept"]
            and all(said.get(k) == str(vc_.get(k)) for k in ("records", "tu", "embedded", "refuted", "unknown",
                                                              "tri_tu", "tri_refuted"))
            and mj.get("problems") == [] and mj.get("triangles_silent_passes") == 0 and cn.get("tri_silent_passes") == 0
            and mj.get("embedder", {}).get("skipped") is True and mj.get("embedder", {}).get("filter_only") is True)


def verify_runs(d: Path) -> dict:
    """{cell: the name of the run directory its verify manifest's stage file lies in}, for G5 round 18's finding 4
    (evaluate() binds each to this copy's run, or for the prefix levels to a full-mode copy's run with this prefix)."""
    out = {}
    for q in (sorted((d / "verify").glob("*.verify.manifest.json")) if (d / "verify").is_dir() else []):
        mm = re.fullmatch(r"(\d+)-(\d+)\.verify\.manifest\.json", q.name)
        if mm:
            out[(int(mm.group(1)), int(mm.group(2)))] = Path(str(json.loads(q.read_text()).get("stage_file"))).parent.name
    return out


def software(d: Path) -> list:
    """G5 round 17, finding 4: every software hash the shipped manifests record is the pinned one (SOFTWARE; run-dag2.py
    the fleet's or the G5-closed one); the interpreter is not compared, and no other key may appear."""
    why = []
    for q in sorted(d.glob("*.manifest.json")) + sorted((d / "verify").glob("*.json") if (d / "verify").is_dir() else []):
        sw = json.loads(q.read_text()).get("software_sha256")
        kind = "verify" if q.parent.name == "verify" else "prune" if q.name.endswith(".prune.manifest.json") else "enum"
        # G5 round 19, finding 5: an absent map or key was once an empty collection, so a deleted pin passed
        if not isinstance(sw, dict) or set(sw) != SOFTWARE_KEYS[kind]:
            why.append(f"{q.relative_to(d)}: software keys {sorted(sw) if isinstance(sw, dict) else sw!r}, not the "
                       f"{kind} manifest's {sorted(SOFTWARE_KEYS[kind])}")
            continue
        if not (isinstance(sw.get("python", ""), str) and (kind != "prune" or sw["python"])):
            why.append(f"{q.relative_to(d)}: no interpreter recorded")
        for k, v in sw.items():
            if k == "python":
                continue
            if not (v == SOFTWARE.get(k) or (k == "run-dag2.py" and v in RUNDAG)):
                why.append(f"{q.relative_to(d)}: software {k} sha256 {str(v)[:16]} is not the pinned one")
    return why


def read_copy(d: Path, tn: int, tm: int, root_k: int, no_ubar: bool) -> dict:
    """What the audit does not pin, for one copy; "why" lists each requirement it fails."""
    i = int(re.fullmatch(rf"s(\d+)of{COUNT}", d.name).group(1))
    c = {"slice": i, "dir": str(d), "why": [], "keep": None, "replay_mode": None}
    if not (d / "run-summary.json").is_file():   # G5 round 14: a copy the audit never saw cannot count
        c["why"] = ["no run-summary.json, so the audit did not see this copy"]
        return c
    try:
        cfg = json.loads((d / "run-config.json").read_text())
        hj = json.loads((d / "hashes.json").read_text())
        rep = json.loads((d / "replay" / "summary.json").read_text())
        c["replay_mode"] = json.loads((d / "replay" / "fingerprint.json").read_text()).get("mode")
        c["rep"], c["seeds10"], c["audit"] = rep, seeds10_of(d), audited(d, tn, tm)
        c["prefix"] = prefix_of(d)
        c["reach_table"] = json.loads((d / "reach.json").read_text()).get("table") or {}
    except (OSError, ValueError) as e:
        c["why"] = [f"unreadable ({type(e).__name__}: {e})"]
        return c
    why, want = [], [LEVEL, i, COUNT]
    if list(cfg.get("target") or []) != [tn, tm] or list(cfg.get("slice") or []) != want:
        why.append(f"run-config.json names target {cfg.get('target')} slice {cfg.get('slice')}")
    if list(hj.get("slice") or []) != want:
        why.append(f"hashes.json names slice {hj.get('slice')}")
    bad = {k: cfg.get(k) for k, v in PIPELINE.items() if cfg.get(k) != v}
    if bad:
        why.append(f"run-config differs from the fleet's pipeline: {bad}")
    if cfg.get("reach_root_k") != root_k:
        why.append(f"root minimum degree {cfg.get('reach_root_k')}, not {root_k}")
    ov = cfg.get("ubar_override") or {}
    if (ov if no_ubar else (ov and ov != FLEET_UBAR)):
        why.append(f"u-bar override {ov}")
    why += replay_pins(rep)
    try:   # G5 round 17, finding 4: the production verifications and software the copy ships
        why += verify_manifests(d, c["audit"] if isinstance(c.get("audit"), dict) else {}, hj.get("files") or {},
                                c.get("replay_mode"))
        why += software(d)
        why += production_manifests(d, hj.get("files") or {}, tn, tm,
                                    c["audit"] if isinstance(c.get("audit"), dict) and "error" not in c["audit"] else None)
        c["verify_runs"] = verify_runs(d)
    except (OSError, ValueError, AttributeError, TypeError) as e:
        why.append(f"its verify manifests or software could not be read ({type(e).__name__}: {e})")
    kf = d / f"{tn}-{tm}.keep.g6"
    h = (hj.get("files") or {}).get(kf.name)
    if not kf.exists():
        why.append(f"no {kf.name}")
    elif not h or h.get("sha256") != sha(kf) or h.get("records") != sum(1 for x in kf.read_text().splitlines() if x):
        why.append(f"{kf.name} is not the file hashes.json records ({h})")
    else:
        c["keep"] = [x.strip() for x in kf.read_text().splitlines() if x.strip()]
    c["why"] = why
    return c


def collect(root: Path, sub: str, tn: int, tm: int, root_k: int, no_ubar: bool) -> tuple:
    copies, dirs = {}, []
    for d in sorted(root.glob(f"*/research/unit-distance-23/results/{sub}/{tn}-{tm}-L{LEVEL}-tri-pf74/s*of{COUNT}")):
        if d.is_dir():
            c = read_copy(d, tn, tm, root_k, no_ubar)
            copies.setdefault(c["slice"], []).append(c)
            if (d / "run-summary.json").is_file():
                dirs.append(d)
    return copies, audit(dirs, tn, tm)


def evaluate(copies: dict, aud: dict, tn: int, tm: int, known: list | None, expect_empty: bool, labelg: str) -> tuple:
    # the copies are never changed here: a rule that depends on other slices (the prefix) must not leave one
    # evaluation's verdicts in the evidence the next evaluation reads (a self-test state once leaked that way)
    problems, missing, chosen, failing, whys, local = [], [], {}, [], {}, {}
    problems += aud["global"]
    pools, pclash = prefix_pools([c for cs in copies.values() for c in cs])
    problems += pclash
    for i in range(COUNT):
        cs = copies.get(i) or []
        if not cs:
            missing.append(i)
            continue
        why = list(aud["per_slice"].get(i, []))
        slice_ev, clash = pooled_parents(cs)
        why += clash
        for c in cs:   # each copy's G4 replay against the audited evidence (G5 rounds 14 to 17)
            local[id(c)] = list(c["why"]) or replay_scope(c, evidence_for(c, slice_ev, pools), tn)
        whys[i] = why
    # the prefix (levels <= 12, the same files in every slice) is replayed by full-mode copies only: each copy's must
    # be the prefix of a full-mode copy that passes (G5 round 16's lead)
    covered = {c.get("prefix") for i in whys for c in copies[i] if c.get("replay_mode") == "full" and not local[id(c)]}
    prefixes = {c.get("prefix") for i in whys for c in copies[i] if c.get("prefix")}
    if len(prefixes) > 1:
        problems.append(f"the copies record {len(prefixes)} different prefixes (levels <= {LEVEL}); a run has one")
    # G5 round 18, finding 4: each verify manifest's stage file lies in this copy's run; a prefix level's may lie in
    # the run of a full-mode copy with this copy's prefix (the prefix is computed once per worker and hard-linked)
    full_runs = {f"dag-{Path(c['dir']).parent.name}-{Path(c['dir']).name}": c.get("prefix")
                 for i in whys for c in copies[i] if c.get("replay_mode") == "full"}
    for i in whys:
        for c in copies[i]:
            run = f"dag-{Path(c['dir']).parent.name}-{Path(c['dir']).name}"
            stray = sorted(cell for cell, rdir in (c.get("verify_runs") or {}).items()
                           if not (rdir == run or (cell[0] <= LEVEL and full_runs.get(rdir) == c.get("prefix"))))
            if stray:   # every second-pass rule adds its reason (none hides another's: G5 round 18's control shift)
                local[id(c)] = local[id(c)] + [f"verify manifests of {stray[:3]} name a stage file outside this run "
                                               "(and, for the prefix, outside every full-mode run with this prefix)"]
    for i, why in whys.items():
        cs = copies[i]
        for c in cs:
            if c.get("prefix") not in covered:
                local[id(c)] = local[id(c)] + [f"its prefix (levels <= {LEVEL}, {str(c.get('prefix'))[:16]}) is not "
                                               "one a passing full-mode G4 replay covers"]
        # every copy must pass, not one of them (measured: no slice of the fleet or the control has a failing copy
        # beside a passing one), and all must keep the same graphs
        good = [c for c in cs if not local[id(c)]]
        why += [w for c in cs for w in local[id(c)]]
        if len({tuple(x["keep"]) for x in good}) > 1:
            why.append("its copies keep different graphs")
        if why:
            failing.append(i)
            problems += [f"s{i}: {w}" for w in why]
        else:
            chosen[i] = good[0]
    if not missing and not (aud.get("coverage") or "").startswith("COVERAGE (summary only) OK"):
        problems.append(f"every slice is in, and the audit does not say OK: {aud.get('coverage')!r}")
    if chosen and not any(c.get("replay_mode") == "full" for c in chosen.values()):
        problems.append("no counted copy has a full-mode G4 replay, so no replay here showed its red controls red")
    union = sorted({g for c in chosen.values() for g in c["keep"]})
    forms = set(lc.canonical(union, labelg)) if union else set()
    found = []
    if expect_empty and forms:
        problems.append(f"the top level keeps {len(forms)} graph(s) at ({tn},{tm}); the control needs none")
    if known is not None:
        kforms = lc.canonical(known, labelg)
        found = [k for k, f in enumerate(kforms) if f in forms]
        lost = [k for k in range(len(known)) if k not in found]
        if lost and not missing:   # with slices missing, a known graph not yet seen is open, not lost
            problems.append(f"known graph(s) {lost} of {len(known)} not kept at ({tn},{tm})")
    s = {"complete": len(chosen), "pass": len(chosen), "failing": len(failing), "missing": len(missing),
         "missing_list": missing, "kept": len(forms), "known": len(known) if known is not None else None,
         "found": len(found), "found_list": found}
    return problems, s


def report(problems, s, tn, tm, aud) -> int:
    print(f"AUDIT: {aud.get('coverage') or 'no copies audited'}")
    for p in problems[:300]:
        print("PROBLEM:", p)
    if len(problems) > 300:
        print(f"PROBLEM: ... and {len(problems) - 300} more")
    if s["missing_list"]:
        m = s["missing_list"]
        print(f"MISSING: {len(m)} slice(s) with no copy: {m[:40]}{' ...' if len(m) > 40 else ''}")
    known = f"; known: {s['found']} of {s['known']} kept" if s["known"] is not None else ""
    ok = not problems and not s["missing"]
    print(f"TARGET-CHECK {'OK' if ok else 'FAIL'}: ({tn},{tm}): {s['complete']} of {COUNT} slices complete, "
          f"G4 PASS {s['pass']}; {s['failing']} failing, {s['missing']} missing; kept at ({tn},{tm}): {s['kept']} "
          f"distinct graph(s){known}")
    return 0 if ok else 1


def self_test(copies, aud, a, known, labelg) -> int:
    tn, tm = a.target
    run = lambda cp, au=aud, kn=known: evaluate(cp, au, tn, tm, kn, a.expect_empty, labelg)
    base, bs = run(copies)
    res = []

    def expect(name, out, must=None):
        """A red control is caught when it adds a problem (or a missing slice); with must, only by a problem that must
        accepts: the rule the control is aimed at, not another one that happens to fire in the same state."""
        P, s = out
        new = [p for p in P if p not in base and (must is None or must(p))]
        caught = bool(new) or (must is None and s["missing"] > bs["missing"])
        res.append(caught)
        why = new[0] if new else f"{s['missing']} missing, was {bs['missing']}" if caught else "not caught"
        print(f"{'ok  ' if caught else 'FAIL'} self-test, {name}: {why[:150]}")

    i = next((k for k in sorted(copies) if copies[k] and not copies[k][0]["why"] and k not in aud["per_slice"]), None)
    if i is None:
        print("SELF-TEST cannot run: no complete slice yet")
        return 1
    d = Path(copies[i][0]["dir"])

    def reread(mutate, name, must=None, j=None):   # a scratch copy of a real slice copy, one file edited, re-read
        k = i if j is None else j
        dk = d if j is None else Path(copies[j][0]["dir"])
        cp, au = copy.deepcopy(copies), copy.deepcopy(aud)
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp) / "scratch" / dk.relative_to(dk.parents[5])   # the same results path under a scratch worker
            shutil.copytree(dk, td)
            mutate(td)
            cp[k] = [read_copy(td, tn, tm, a.root_k, a.no_ubar)]
            au["per_slice"][k] = audit([td], tn, tm)["per_slice"].get(k, [])
        expect(name, run(cp, au), must)

    def edit(rel, f):
        def m(td):
            p = td / rel
            j = json.loads(p.read_text())
            f(j)
            p.write_text(json.dumps(j))
        return m

    def cell(j, n, m):
        return next(x for x in j["levels"] if x.get("n") == n and x.get("m") == m)

    lvl = lambda j: next(x for x in j["levels"] if (x.get("n") or 0) > LEVEL and x.get("parents"))
    expect(f"s{i} removed", run({k: v for k, v in copies.items() if k != i}))
    reread(edit("run-config.json", lambda j: j.__setitem__("slice", [LEVEL, (i + 1) % COUNT, COUNT])),
           f"s{i}'s run-config naming another slice", must=lambda p: "run-config.json names target" in p)
    reread(edit("run-config.json", lambda j: j.__setitem__("prune_filter_set", 398)),
           f"s{i} run with another prune filter set", must=lambda p: "differs from the fleet's pipeline" in p)
    reread(edit("run-config.json", lambda j: j.__setitem__("reach_root_k", a.root_k + 1)),
           f"s{i} run with another root minimum degree", must=lambda p: "root minimum degree" in p)
    reread(edit("run-summary.json", lambda j: lvl(j).update(parents=0, parent_edge_counts=[], parent_sources=[])),
           f"s{i}'s first slice cell with its parents emptied (G5 round 13)",
           must=lambda p: "no copy of the slice records its parents" in p)
    reread(edit("run-summary.json", lambda j: lvl(j).__setitem__("children", -1)), f"s{i}'s cell with children -1",
           must=lambda p: "not nonnegative integers" in p)
    reread(edit("replay/summary.json", lambda j: j["stages"][0].__setitem__("ok", False)),
           f"s{i}'s G4 replay with a failed stage under an OK aggregate", must=lambda p: "stages_ok" in p)
    reread(edit("replay/summary.json", lambda j: j.update(fraction=0, min_per_shard=1, whole_max=0, max_per_shard=1)),
           f"s{i}'s G4 replay with another sampling policy", must=lambda p: "sampling policy" in p)
    reread(edit("replay/summary.json", lambda j: j["per_cell"][0].__setitem__("mismatches", 1)),
           f"s{i}'s G4 replay with one cell mismatching", must=lambda p: "mismatching_parents" in p)
    reread(edit("run-summary.json", lambda j: cell(j, tn, tm).setdefault("prune", {}).setdefault("counts", {})
                .__setitem__("kept", 1)), f"s{i}'s top prune count saying a graph was kept, beside its keep file",
           must=lambda p: "prune counts" in p)
    reread(lambda td: (td / "run-summary.json").unlink(), f"s{i}'s copy without run-summary.json (G5 round 14)",
           must=lambda p: "no run-summary.json" in p)
    if copies[i][0].get("replay_mode") == "full":
        def shrink(j):   # round 14's reproduction: the prefix rows, prefix stages and seeds gone, the totals rebalanced
            j["levels"] = f"{LEVEL + 1}-{tn}"
            j["seeds"] = [s for s in j["seeds"] if s.get("cell") == "1-0"]
            j["per_cell"] = [c for c in j["per_cell"] if c["n"] > LEVEL]
            j["per_level"] = [x for x in j.get("per_level") or [] if x.get("n", 0) > LEVEL]
            j["stages"] = [s for s in j.get("stages") or [] if (s.get("level") or [0])[0] >= LEVEL]
            j["stages_checked"] = len(j["stages"])
            for k, tot in (("sampled", "sampled_parents"), ("processed", "processed_parents"),
                           ("production_children", "production_children_compared"),
                           ("enum2_children", "enum2_children_compared")):
                j[tot] = sum(c.get(k) or 0 for c in j["per_cell"])
        def shrink_all(td):   # G5 round 17, finding 7: the fingerprint's totals reconciled with the shortened summary
            edit("replay/summary.json", shrink)(td)
            sp, fpp = td / "replay" / "summary.json", td / "replay" / "fingerprint.json"
            j, fp = json.loads(sp.read_text()), json.loads(fpp.read_text())
            for k in ("sampled_parents", "production_children_compared", "mismatching_parents", "stages_checked"):
                if k in fp and k in j:
                    fp[k] = str(j[k]) if isinstance(fp[k], str) else j[k]
            fpp.write_text(json.dumps(fp))
        reread(shrink_all, f"s{i}'s full replay limited to the slice's levels, its totals and fingerprint reconciled "
                           "(G5 rounds 14 and 17)", must=lambda p: "a full G4 replay of levels" in p)
        strip = ("full_check", "full_identical", "enum2_records", "only_seed_file", "only_enum2", "full_seconds")
        reread(edit("replay/summary.json", lambda j: [s.pop(k, None) for s in j["seeds"] for k in strip]),
               f"s{i}'s full replay with the seeds' full checks deleted (G5 round 14)",
               must=lambda p: "is not recomputed in full" in p)
    if copies[i][0].get("replay_mode") == "full":   # G5 round 15's reproductions, the replay totals rebalanced
        def rebalance(td):
            sp, fpp = td / "replay" / "summary.json", td / "replay" / "fingerprint.json"
            j, fp = json.loads(sp.read_text()), json.loads(fpp.read_text())
            for x in j.get("per_level") or []:
                rows = [r for r in j["per_cell"] if r.get("n") == x.get("n")]
                for k, k2 in (("cells", None), ("parents", "parents_in_cell"), ("sampled", "sampled"),
                              ("processed", "processed"), ("production_children", "production_children"),
                              ("enum2_children", "enum2_children"), ("mismatches", "mismatches")):
                    x[k] = len(rows) if k2 is None else sum(r.get(k2) or 0 for r in rows)
            for k, tot in (("sampled", "sampled_parents"), ("processed", "processed_parents"),
                           ("production_children", "production_children_compared"),
                           ("enum2_children", "enum2_children_compared")):
                j[tot] = sum(r.get(k) or 0 for r in j["per_cell"])
            for k in ("sampled_parents", "production_children_compared", "mismatching_parents"):
                if k in fp and k in j:
                    fp[k] = j[k]
            sp.write_text(json.dumps(j)); fpp.write_text(json.dumps(fp))

        def seed_zero(td):
            edit("replay/summary.json", lambda j: next(s for s in j["seeds"] if s["cell"].startswith(f"{SEED_N}-"))
                 .update(records=0, enum2_records=0, sampled=0))(td)
        reread(seed_zero, f"s{i}'s first level-{SEED_N} seed record claiming a full check of no graphs (G5 round 15)",
               must=lambda p: "is not recomputed in full" in p)

        def unsampled(td):
            def f(j):
                r = next(r for r in j["per_cell"] if (r.get("parents_in_cell") or 0) > 100)
                r.update(sampled=0, processed=0, production_children=0, enum2_children=0, mismatches=0)
            edit("replay/summary.json", f)(td)
            rebalance(td)
        reread(unsampled, f"s{i}'s replay row of a large cell sampling none of it, totals rebalanced (G5 round 15)",
               must=lambda p: "the policy samples" in p)

        def resumed_elsewhere(td):
            s = json.loads((td / "run-summary.json").read_text())
            e = next(x for x in s["levels"] if (x.get("n") or 0) == SEED_N + 1 and (x.get("parents") or 0) > 100)
            cell = f"{e['n']}-{e['m']}"
            (td / "history").mkdir(exist_ok=True)
            (td / "history" / "0000000.json").write_text(json.dumps(s))
            (td / "history" / "INDEX.json").write_text(json.dumps({"commits": ["0000000"]}))
            for k in ("parents", "parent_edge_counts", "parent_sources", "shards"):
                e.pop(k, None)
            e["resumed"] = True
            (td / "run-summary.json").write_text(json.dumps(s))
            edit("replay/summary.json", lambda j: j.__setitem__("per_cell", [r for r in j["per_cell"]
                                                                                if r.get("cell") != cell]))(td)
            rebalance(td)
        reread(resumed_elsewhere, f"s{i}'s cell resumed, its parents only in the history, its replay row removed "
                                  "(G5 round 15)", must=lambda p: "no row for cell" in p)
    # the domains and agreements this layer requires, each broken in memory (G5 round 15: "validate its count domains")
    c0 = copies[i][0]

    def mem(f, name, must=None, j=None):
        cp = copy.deepcopy(copies)
        f(cp[i if j is None else j])
        expect(name, run(cp), must)

    def row(cs, pred):
        return next(r for r in cs[0]["rep"]["per_cell"] if pred(r))

    mem(lambda cs: cs[0].__setitem__("audit", {"error": "RuntimeError: simulated"}),
        f"s{i}'s own audit reading failing in-process", must=lambda p: "the audit's own reading of this copy failed" in p)
    mem(lambda cs: row(cs, lambda r: r.get("parents_in_cell") == 1).__setitem__("sampled", True),
        f"s{i}'s replay row of a one-parent cell sampling True (a bool, not a count)", must=lambda p: "sampled True" in p)
    mem(lambda cs: row(cs, lambda r: (r.get("parents_in_cell") or 0) > 1).update(
        sampled=row(cs, lambda r: (r.get("parents_in_cell") or 0) > 1)["parents_in_cell"] + 1),
        f"s{i}'s replay row sampling more parents than its cell has", must=lambda p: "the policy samples" in p)
    mem(lambda cs: cs[0]["rep"]["per_cell"].append({"cell": "x-1", "n": None}),
        f"s{i}'s replay with a row naming a malformed cell", must=lambda p: "malformed or repeated" in p)
    k_in = next(k for k, v in sorted(c0["audit"]["parents"].items()) if v and v > 0 and k[0] > LEVEL)
    mem(lambda cs: cs[0]["audit"]["parents"].__setitem__(k_in, float(c0["audit"]["parents"][k_in])),
        f"s{i}'s audited parents of cell {k_in[0]}-{k_in[1]} a float", must=lambda p: "not a nonnegative integer" in p)

    def second(f):
        def g(cs):
            c2 = copy.deepcopy(cs[0])
            f(c2)
            cs.append(c2)
        return g
    k_out = next((k for k, v in sorted(c0["audit"]["parents"].items()) if k[0] <= LEVEL and v), k_in)
    mem(second(lambda c2: c2["audit"]["parents"].__setitem__(k_out, c0["audit"]["parents"][k_out] + 1)),
        f"a second copy of s{i} disagreeing on the audited parents of cell {k_out[0]}-{k_out[1]}",
        must=lambda p: "disagree on the audited parents" in p)
    mem(second(lambda c2: c2["rep"].__setitem__("levels", "bogus")),
        f"a second copy of s{i} failing its replay scope beside a passing copy",
        must=lambda p: "G4 replay of levels 'bogus'" in p)

    # G5 round 16's leads, each aimed at its own rule's line: the exact sample, the strata, the rows the audit has no
    # evidence for, the audited shards, and the prefix a full-mode replay covers
    draw, P = policy_sample(), REPLAY_PINS

    def policy(r):
        return len(draw(P["seed"], Path(str(r.get("run_dir"))).name, r["cell"], r["parents_in_cell"], P["fraction"],
                        P["min_per_shard"], P["whole_max"], P["max_per_shard"],
                        list(c0["audit"]["shards"][(r["n"], r["m"])])))
    old_bound = lambda p: max(1, p if p <= P["whole_max"] else math.ceil(P["fraction"] * p))
    under = next((r for r in c0["rep"]["per_cell"] if r.get("parents_in_cell") and (r["n"], r["m"]) in
                  c0["audit"]["shards"] and policy(r) - 1 >= old_bound(r["parents_in_cell"])), None)
    if under is None:   # the control could not show the exact rule is stronger than the bound it replaced
        res.append(False)
        print(f"FAIL self-test, a row sampling less than the policy: s{i} has no row the old lower bound would pass")
    else:
        mem(lambda cs: row(cs, lambda r: r["cell"] == under["cell"]).__setitem__("sampled", policy(under) - 1),
            f"s{i}'s replay row of {under['cell']} sampling {policy(under) - 1}, one fewer than the policy's "
            f"{policy(under)} (the lower bound it replaced, {old_bound(under['parents_in_cell'])}, passed it)",
            must=lambda p: "the policy samples" in p)
    r0 = next(r for r in c0["rep"]["per_cell"] if r.get("parents_in_cell"))
    lo0 = SEED_N + 1 if c0.get("replay_mode") == "full" else LEVEL + 1
    mem(lambda cs: row(cs, lambda r: r["cell"] == r0["cell"]).__setitem__("strata", r0["strata"] + 1),
        f"s{i}'s replay row of {r0['cell']} claiming {r0['strata'] + 1} strata for its {r0['strata']} shards",
        must=lambda p: "the policy samples" in p)
    mem(lambda cs: cs[0]["rep"]["per_cell"].append(dict(r0, cell=f"{lo0}-99", n=lo0, m=99)),
        f"s{i}'s replay with a row for cell {lo0}-99, which the audit has no evidence for",
        must=lambda p: "no evidence" in p)
    mem(lambda cs: row(cs, lambda r: r["cell"] == r0["cell"]).__setitem__("n", r0["n"] + 1),
        f"s{i}'s replay row {r0['cell']} saying n {r0['n'] + 1}", must=lambda p: "says n" in p)
    mem(lambda cs: cs[0]["audit"]["shards"].__setitem__((r0["n"], r0["m"]), ((0, r0["parents_in_cell"] - 1),)),
        f"s{i}'s audited shards of {r0['cell']} stopping one parent short", must=lambda p: "not ranges tiling" in p)
    j = next((k for k in sorted(copies) if k != i and copies[k] and copies[k][0].get("replay_mode") == "slice"
              and not copies[k][0]["why"]), None)
    if j is None:
        res.append(False)
        print("FAIL self-test, a slice-mode copy recording another prefix: no passing slice-mode copy to change")
    else:
        mem(lambda cs: cs[0].__setitem__("prefix", "0" * 64), f"s{j}'s slice-mode copy recording another prefix",
            must=lambda p: p.startswith(f"s{j}: its prefix"), j=j)
    # G5 round 17, each aimed at its own rule's line
    other = f"dag-{Path(c0['dir']).parent.name}-s{(i + 1) % COUNT}of{COUNT}"
    mem(lambda cs: row(cs, lambda r: r["cell"] == r0["cell"]).__setitem__("run_dir", "/x/" + other),
        f"s{i}'s replay row of {r0['cell']} naming the run of s{(i + 1) % COUNT}",
        must=lambda p: "name another run" in p)
    mem(lambda cs: cs[0]["rep"].__setitem__("run_dirs", ["/x/" + other]),
        f"s{i}'s replay summary naming the run of s{(i + 1) % COUNT}", must=lambda p: "whose summary names run" in p)
    lo_i = SEED_N + 1 if c0.get("replay_mode") == "full" else LEVEL + 1
    need = sorted({key for cell, src in c0["audit"]["sources"].items() if lo_i <= cell[0] <= tn for key in src},
                  key=str)
    k_st = need[0]
    mem(lambda cs: cs[0]["rep"].__setitem__("stages", [s for s in cs[0]["rep"]["stages"]
                                                       if (tuple(s["level"]), s["kind"]) != k_st]),
        f"s{i}'s replay without the stage record of {k_st}", must=lambda p: "no stage record of" in p)

    def zeroed(cs):
        s = next(s for s in cs[0]["rep"]["stages"] if (tuple(s["level"]), s["kind"]) == k_st)
        s.update({k: 0 for k in ("input_records", "records", "derived_records", "pruned") if k in s})
    mem(zeroed, f"s{i}'s stage record of {k_st} with its counts zeroed", must=lambda p: "stage record of" in p)
    vfirst = sorted((Path(c0["dir"]) / "verify").glob("*.verify.manifest.json"))[0].name
    reread(edit(f"verify/{vfirst}", lambda j: j.__setitem__("exit_status", 1)),
           f"s{i}'s verify/{vfirst} with exit status 1", must=lambda p: "is not a clean verification" in p)
    reread(edit("run-config.json", lambda j: j.__setitem__("verify_stages", False)),
           f"s{i} run with the stage verifications off", must=lambda p: "differs from the fleet's pipeline" in p)
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j["software_sha256"].__setitem__("udenum", "0" * 64)),
           f"s{i}'s top manifest naming another udenum", must=lambda p: "software udenum" in p)
    if c0.get("replay_mode") == "full" and j is not None:   # finding 1: the prefix evidence moved, its rows removed
        def moved(cp):
            src, dst = cp[i][0], cp[j][0]
            cells = [cell for cell, v in src["audit"]["parents"].items() if SEED_N < cell[0] <= LEVEL and v]
            for what in EVIDENCE:
                for cell in cells:
                    if cell in src["audit"][what]:
                        dst["audit"][what][cell] = src["audit"][what].pop(cell)
            src["rep"]["per_cell"] = [r for r in src["rep"]["per_cell"] if (r["n"], r["m"]) not in set(cells)]
            return cells
        cp = copy.deepcopy(copies)
        cells_moved = moved(cp)
        expect(f"s{i}'s {len(cells_moved)} prefix cells' evidence moved to s{j}'s copy, their rows removed from its full "
               "replay (G5 round 17, finding 1)", run(cp), must=lambda p: p.startswith(f"s{i}: ") and "no row for cell" in p)
    # G5 round 18, each aimed at its own rule's line
    if c0["rep"].get("seeds"):
        mem(lambda cs: cs[0]["rep"]["seeds"][0].update(sample_ok=False, sample_bad=["x"]),
            f"s{i}'s first seed check failed in its details (identical still true)",
            must=lambda p: "did not pass in their details" in p)
    st_reach = next((s for s in c0["rep"]["stages"] if s.get("kind") == "reach"), None)
    st_any = st_reach or c0["rep"]["stages"][0]
    if st_reach:
        mem(lambda cs: next(s for s in cs[0]["rep"]["stages"] if s.get("kind") == "reach").__setitem__("k", 99),
            f"s{i}'s reach stage of {st_reach['level']} with k 99", must=lambda p: "parameters or consumer" in p)
    mem(lambda cs: next(s for s in cs[0]["rep"]["stages"] if s.get("level") == st_any["level"]
                        and s.get("kind") == st_any["kind"]).__setitem__("source", "99-99.reach.g6"),
        f"s{i}'s stage of {st_any['level']} naming the source 99-99.reach.g6", must=lambda p: "parameters or consumer" in p)
    reread(edit(f"{tn}-{tm}.prune.manifest.json", lambda j: j.__setitem__("exit_status", 1)),
           f"s{i}'s top pruning manifest with exit status 1", must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j.__setitem__("exit_status", 1)),
           f"s{i}'s top enumeration manifest with exit status 1", must=lambda p: "is not a clean success bound" in p)
    vmid = next((q.name for q in sorted((Path(c0["dir"]) / "verify").glob("*.verify.manifest.json"))
                 if int(q.name.split("-")[0]) > LEVEL), None)
    if vmid:
        def moved_stage(j):
            sf = Path(j["stage_file"])
            j["stage_file"] = str(sf.parent.parent / (sf.parent.name.rsplit("-s", 1)[0] + f"-s{(i + 1) % COUNT}of{COUNT}")
                                  / sf.name)
        reread(edit(f"verify/{vmid}", moved_stage), f"s{i}'s verify/{vmid} naming the stage file of another slice's run",
               must=lambda p: "name a stage file outside this run" in p)
    # G5 round 19, each the reviewer's own reproduction, aimed at its rule's line
    jf = next((k for k, cs in sorted(copies.items()) if cs and cs[0].get("replay_mode") == "full"
               and (cs[0].get("rep") or {}).get("red_controls")), None)
    if jf is not None:
        mem(lambda cs: cs[0]["rep"]["red_controls"][0].update(baseline_identical=False),
            f"s{jf}'s red control {copies[jf][0]['rep']['red_controls'][0].get('id')} with its baseline not identical, "
            "went_red still true (finding 3)", must=lambda p: "not red by their own recorded outcome" in p, j=jf)
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R3").update(
            extras_contain_exactly_that_member=False), f"s{jf}'s red control R3 whose extras are not the dropped member's",
            must=lambda p: "not red by their own recorded outcome" in p, j=jf)
        mem(lambda cs: cs[0]["rep"]["red_controls"].pop(), f"s{jf}'s full replay with one red control missing",
            must=lambda p: "not each of" in p, j=jf)
    if c0.get("replay_mode") == "full" and (Path(c0["dir"]) / "replay" / "red.json").is_file():
        reread(edit("replay/red.json", lambda j: j[0].__setitem__("went_red", False)),
               f"s{i}'s red.json disagreeing with its summary's red controls", must=lambda p: "red.json is not" in p)
    fb = lambda j: next(k for k in j["inputs_sha256"] if k.endswith("/forbidden-398.json"))
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j["inputs_sha256"].__setitem__(fb(j), "0" * 64)),
           f"s{i}'s top enumeration manifest with its forbidden set's digest zeroed (finding 4)",
           must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j.__setitem__("children_written", j["children_written"] + 1)),
           f"s{i}'s top enumeration manifest counting a child its level file does not have (finding 4)",
           must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.prune.manifest.json",
                lambda j: j.update(checker=j["checker"].replace("ACCEPT", "REJECT", 1), problems=["a certificate"])),
           f"s{i}'s top pruning manifest whose checker says REJECT, with a problem (finding 4)",
           must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.prune.manifest.json",
                lambda j: j["verified_counts"].__setitem__("tu", j["verified_counts"]["tu"] + 1)),
           f"s{i}'s top pruning manifest whose verified counts are not its counts", must=lambda p: "is not a clean "
           "success bound" in p)
    vm13 = next((q.name for q in sorted((Path(c0["dir"]) / "verify").glob(f"{LEVEL + 1}-*.verify.manifest.json"))), None)
    if vm13:
        reread(edit(f"verify/{vm13}", lambda j: j.pop("software_sha256")),
               f"s{i}'s verify/{vm13} with its software pins deleted (finding 5)", must=lambda p: "software keys" in p)
        # G5 round 20, each the reviewer's own reproduction
        reread(edit(f"verify/{vm13}", lambda j: j.__setitem__("udenum_target", [j["level"][0] + 1, j["level"][1] + 26])),
               f"s{i}'s verify/{vm13} naming another udenum target, an operation that verifies nothing (finding 1)",
               must=lambda p: "is not a clean verification" in p)
    two = next((q.name for q in sorted(Path(c0["dir"]).glob("*.manifest.json")) if not q.name.endswith(".prune.manifest.json")
                and len(json.loads(q.read_text()).get("parent_sources") or []) >= 2), None)
    if two:
        def drop_source(j):
            j["parent_sources"] = j["parent_sources"][:-1]
            j["parent_range"] = [0, sum(s["records"] for s in j["parent_sources"])]
        reread(edit(two, drop_source), f"s{i}'s {two} with a parent source deleted and its range shortened to match "
               "(finding 2)", must=lambda p: "is not a clean success bound" in p)

    def one_graph(j):   # an ACCEPT claiming one checked and pruned graph, internally consistent, beside empty files
        j["counts"].update(input=j["counts"]["input"] + 1, tu=j["counts"]["tu"] + 1, pruned=j["counts"]["pruned"] + 1)
        j["verified_counts"].update(records=j["verified_counts"]["records"] + 1, tu=j["verified_counts"]["tu"] + 1)
        said = dict(x.split("=", 1) for x in j["checker"].split()[2:] if "=" in x)
        j["checker"] = j["checker"].replace(f"records={said['records']}", f"records={j['verified_counts']['records']}",
                                            1).replace(f" tu={said['tu']}", f" tu={j['verified_counts']['tu']}", 1)
    reread(edit(f"{tn}-{tm}.prune.manifest.json", one_graph),
           f"s{i}'s top pruning manifest claiming one more graph checked and pruned than its files hold (finding 3)",
           must=lambda p: "is not a clean success bound" in p)
    # G5 round 21, each the reviewer's own reproduction
    other = f"s{(i + 1) % COUNT}of{COUNT}"
    if vm13:
        reread(edit(f"verify/{vm13}", lambda j: [x.__setitem__("udenum_manifest", x["udenum_manifest"].replace(
            f"s{i}of{COUNT}/", f"{other}/")) for x in j["parts"]]),
               f"s{i}'s verify/{vm13} whose parts cite another slice's verification manifests (finding 1)",
               must=lambda p: "is not a clean verification" in p)
    if two:
        reread(edit(two, lambda j: (j["parent_sources"].append(dict(j["parent_sources"][0])),
                                    j.__setitem__("parent_range", [0, sum(s["records"] for s in j["parent_sources"])]))),
               f"s{i}'s {two} with a parent source listed twice (finding 2)", must=lambda p: "is not a clean success" in p)
        reread(edit(two, lambda j: j.__setitem__("parent_file", j["parent_file"].replace(f"s{i}of{COUNT}/", f"{other}/"))),
               f"s{i}'s {two} whose parent file is another slice's (finding 2)", must=lambda p: "is not a clean success" in p)
    below = [q.name for q in Path(c0["dir"]).glob(f"{tn - 1}-*.manifest.json")]
    if below:
        reread(lambda td: [(td / name).unlink() for name in below],
               f"s{i} without its level-{tn - 1} manifests {sorted(below)} (finding 3)",
               must=lambda p: "are not the top two levels'" in p)
    reread(edit(f"{tn}-{tm}.prune.manifest.json", lambda j: j["triangles_checker"].__setitem__(
        "command", j["triangles_checker"]["command"].replace(f"s{i}of{COUNT}/", f"{other}/"))),
           f"s{i}'s top pruning manifest whose checker ran on another slice's files (finding 4)",
           must=lambda p: "is not a clean success bound" in p)
    if jf is not None:
        mem(lambda cs: [r.update(cell="99-999", index=-1) for r in cs[0]["rep"]["red_controls"]],
            f"s{jf}'s red controls on cell 99-999, index -1 (finding 5)",
            must=lambda p: "do not act on its own replayed cells" in p, j=jf)
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R3").__setitem__(
            "control", "enum2 without member 0 (one of the 324) against the production block"),
            f"s{jf}'s R3 dropping member 0, one of the 74 (finding 5)",
            must=lambda p: "do not act on its own replayed cells" in p, j=jf)
    # G5 round 22, each the reviewer's own reproduction
    if vm13:
        reread(edit(f"verify/{vm13}", lambda j: [x.__setitem__("udenum_manifest", "/tmp/unrelated/_verify/"
                                                               + Path(x["udenum_manifest"]).name) for x in j["parts"]]),
               f"s{i}'s verify/{vm13} whose parts' manifests lie outside every run (finding 1)",
               must=lambda p: "is not a clean verification" in p)
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j.__setitem__("parent_file", "/tmp/unrelated/_parents/"
                                                                   + Path(j["parent_file"]).name)),
           f"s{i}'s top enumeration manifest whose parent file lies outside every run (finding 1)",
           must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.manifest.json", lambda j: j["inputs_sha256"].__setitem__(j["parent_file"], "0" * 64)),
           f"s{i}'s top enumeration manifest with another parent-file digest (finding 3)",
           must=lambda p: "is not a clean success bound" in p)
    reread(edit(f"{tn}-{tm}.prune.manifest.json", lambda j: j["triangles_checker"].__setitem__(
        "command", j["triangles_checker"]["command"].replace(j["software_sha256"]["python"].split()[0], "/bin/true", 1))),
           f"s{i}'s top pruning manifest whose checker command runs /bin/true (finding 4)",
           must=lambda p: "is not a clean success bound" in p)
    if jf is not None:
        def r4_last(cs):
            rows = {x["cell"]: x for x in cs[0]["rep"]["per_cell"]}
            r = next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R4")
            r["index"] = rows[r["cell"]]["parents_in_cell"] - 1
        mem(r4_last, f"s{jf}'s R4 on its cell's last parent, with no parent after it (finding 5)",
            must=lambda p: "do not act on its own replayed cells" in p, j=jf)
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R2").__setitem__("only_enum2", 102),
            f"s{jf}'s R2 dropping one record and finding 102 (finding 5)",
            must=lambda p: "not red by their own recorded outcome" in p, j=jf)
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R4").__setitem__(
            "next_block_size", -1), f"s{jf}'s R4 with a next block of -1 records (G5 round 23, finding 6)",
            must=lambda p: "not red by their own recorded outcome" in p, j=jf)
        cnj = (copies[jf][0].get("audit") or {}).get("counts") or {}
        part = next((x for x in copies[jf][0]["rep"]["per_cell"] if x.get("sampled", 0) < x.get("parents_in_cell", 0)
                     and tuple(map(int, str(x["cell"]).split("-"))) in cnj), None)
        if part:
            over_n = cnj[tuple(map(int, str(part["cell"]).split("-")))][0] + 1
            mem(lambda cs: next(x for x in cs[0]["rep"]["per_cell"] if x["cell"] == part["cell"]).update(
                production_children=over_n, enum2_children=over_n),
                f"s{jf}'s partly sampled cell {part['cell']} comparing {over_n} children, more than it holds (finding 5)",
                must=lambda p: "compare more children than they hold" in p, j=jf)
        # G5 round 24, each the reviewer's own reproduction
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R1").__setitem__("only_enum2", -1),
            f"s{jf}'s R1 with only_enum2 -1 (G5 round 24, finding 3)",
            must=lambda p: "not red by their own recorded outcome" in p, j=jf)
        mem(lambda cs: next(r for r in cs[0]["rep"]["red_controls"] if r.get("id") == "R4").__setitem__(
            "next_block_size", 10 ** 9), f"s{jf}'s R4 whose next block holds more children than its cell",
            must=lambda p: "do not act on its own replayed cells" in p, j=jf)
        mem(lambda cs: [r.__setitem__("index", 0) for r in cs[0]["rep"]["red_controls"] if r.get("id") != "R3"],
            f"s{jf}'s sampled red controls on parent 0, which the policy did not draw",
            must=lambda p: "act on a parent the policy did not draw" in p, j=jf)
        if copies[jf][0]["rep"].get("seeds"):
            mem(lambda cs: cs[0]["rep"]["seeds"][0].update(replayable=False,
                                                            problem="seed file missing or not matching its manifest"),
                f"s{jf}'s seed check that says it could not be replayed (finding 4)",
                must=lambda p: "did not pass in their details" in p, j=jf)
            if "run_dir" in copies[jf][0]["rep"]["seeds"][0]:
                mem(lambda cs: [s.__setitem__("run_dir", "/tmp/dag-23-65-L12-tri-pf74-s1of1920")
                                for s in cs[0]["rep"]["seeds"]],
                    f"s{jf}'s seed records naming another run", must=lambda p: "name another run" in p, j=jf)
        # finding 2: a partly sampled cell comparing fewer children than its fully drawn shards hold. The case needs a
        # cell sampled in part with a shard drawn in full, so it is sought in every complete copy, not only the first
        # full-mode one (in both controls that one has no such cell, and the control once skipped itself silently)
        shard_row = None
        for js, cs_ in sorted(copies.items()):
            if not cs_ or cs_[0]["why"] or js in aud["per_slice"] or "rep" not in cs_[0]:
                continue
            evj = cs_[0].get("audit") or {}
            for x in cs_[0]["rep"].get("per_cell") or []:
                cell_t = tuple(map(int, str(x["cell"]).split("-")))
                rng_ = (evj.get("shards") or {}).get(cell_t)
                kids_ = (evj.get("shard_children") or {}).get(cell_t)
                if rng_ and kids_ and x.get("sampled", 0) < x.get("parents_in_cell", 0):
                    P_ = REPLAY_PINS
                    drawn_ = policy_sample()(P_["seed"], Path(str(x["run_dir"])).name, x["cell"], x["parents_in_cell"],
                                             P_["fraction"], P_["min_per_shard"], P_["whole_max"], P_["max_per_shard"],
                                             list(rng_))
                    fk = sum(k for (a_, b_), k in zip(rng_, kids_) if sum(1 for y in drawn_ if a_ <= y < b_) == b_ - a_)
                    if fk > 0:
                        shard_row = (js, x["cell"], fk)
                        break
            if shard_row:
                break
        if shard_row:
            js_, cell_, fk_ = shard_row
            mem(lambda cs: next(x for x in cs[0]["rep"]["per_cell"] if x["cell"] == cell_).update(
                production_children=fk_ - 1, enum2_children=fk_ - 1),
                f"s{js_}'s cell {cell_} comparing {fk_ - 1} children, fewer than its fully drawn shards' {fk_} "
                f"(finding 2)", must=lambda p: "fewer than the" in p, j=js_)
        else:   # never a silent skip: with no such cell in any copy the rule's premise never holds, so it has nothing to
                # check in this data; said on its own line and not counted (measured on the (21,57) calibration, whose
                # partly sampled cells are almost all one shard: 5 multi-shard of 2,719 in 400 copies, none with a shard
                # drawn in full that has children; the (22,61) control has one, s27's cell 16-34, and catches it)
            print("n/a  self-test, finding 2's control: no complete copy has a partly sampled cell with a shard drawn in "
                  "full, so the lower bound has nothing to check in this data (not counted)")
        full_row = next((x for x in copies[jf][0]["rep"]["per_cell"] if x.get("sampled") == x.get("parents_in_cell")
                         and (x.get("production_children") or 0) > 0), None)
        if full_row:
            mem(lambda cs: next(x for x in cs[0]["rep"]["per_cell"] if x["cell"] == full_row["cell"]).update(
                production_children=0, enum2_children=0),
                f"s{jf}'s fully sampled cell {full_row['cell']} comparing no children (finding 6)",
                must=lambda p: "compare fewer children than the audit records" in p, j=jf)
    # G5 round 23, finding 4: a parent digest with one nonempty source among empty ones, none of them shipped
    def one_full(j):
        for q in sorted(Path(copies[j][0]["dir"]).glob("*.manifest.json")):
            if q.name.endswith(".prune.manifest.json"):
                continue
            ps = json.loads(q.read_text()).get("parent_sources") or []
            if (len([s for s in ps if s.get("records")]) == 1 and len(ps) >= 2
                    and not all((Path(copies[j][0]["dir"]) / Path(s["file"]).name).is_file() for s in ps)):
                return q.name
        return None
    j1 = next(((j, n) for j in sorted(copies) if copies[j] and (n := one_full(j))), None)
    if j1:
        reread(lambda td: (lambda q: q.write_text(json.dumps(dict(json.loads(q.read_text()), inputs_sha256={
            **json.loads(q.read_text())["inputs_sha256"], json.loads(q.read_text())["parent_file"]: "0" * 64}))))(
            td / j1[1]), f"s{j1[0]}'s {j1[1]} whose parent digest is not its one nonempty source's (finding 4)",
            must=lambda p: "is not a clean success bound" in p, j=j1[0])
    if a.expect_empty:
        cp = copy.deepcopy(copies); cp[i][0]["keep"] = [KNOWN_ANY]
        expect(f"s{i} keeping a graph", run(cp), must=lambda p: "the control needs none" in p)
    if known:   # every slice in (the others stand in as copies of s<i>), and a known graph that IS kept, dropped
        j = next(iter(bs["found_list"]), None)
        if j is None:   # dropping a graph nobody keeps changes nothing, so the control could not fail
            res.append(False)
            print("FAIL self-test, a kept known graph kept nowhere: no known graph is kept yet, so it cannot be aimed")
        else:
            drop = set(lc.canonical(known[j:j + 1], labelg))
            full = {k: copy.deepcopy(copies.get(k) or [dict(copies[i][0], slice=k)]) for k in range(COUNT)}
            for cs in full.values():
                for c in cs:
                    c["keep"] = [g for g in (c["keep"] or []) if lc.canonical([g], labelg)[0] not in drop]
            # the audit's coverage as a complete run's would read, so the only rule left to catch this is the known
            # one (with the real partial coverage, "every slice is in, and the audit does not say OK" caught it)
            ok_aud = dict(aud, coverage="COVERAGE (summary only) OK (the self-test's stand-in for a complete run)")
            lost = lambda p: json.loads(p.split("known graph(s) ", 1)[1].split(" of ", 1)[0])
            expect(f"known graph {j} (kept) dropped from every keep, every slice in", run(full, ok_aud),
                   must=lambda p: p.startswith("known graph(s) [") and j in lost(p))
    after, as_ = run(copies)   # the red controls must have left the real evidence exactly as they found it
    if (after, as_) != (base, bs):
        res.append(False)
        print(f"FAIL self-test: the red controls changed the evaluation of the real evidence ({bs['failing']} failing "
              f"before, {as_['failing']} after)")
    bad = res.count(False)
    print(f"SELF-TEST {'passed' if not bad else 'FAILED'}: {len(res) - bad} of {len(res)} red controls caught")
    return 1 if bad else 0


# a graph for the empty control's red control: any graph will do; Engel et al.'s first (22,60) configuration
KNOWN_ANY = (REPO / "research/unit-distance-22/sources/engel-dataset/engel-22-60.g6").read_text().split()[0]


def copies_lines(root: Path, sub: str, tn: int, tm: int) -> list:
    """G5 rounds 22-23: the copies a scope check covers, by identity and evidence: per copy its worker/slice label, its
    target, its replay mode and the SHA-256 of its replay summary and its hashes.json. write_result.py recomputes this
    from the root it credits, so an equal report must have read the same evidence (labels alone once matched a
    control's copies relabelled as the fleet's)."""
    out = []
    for d in sorted(root.glob(f"*/research/unit-distance-23/results/{sub}/{tn}-{tm}-L{LEVEL}-tri-pf74/s*of{COUNT}")):
        try:
            mode = json.loads((d / "replay" / "fingerprint.json").read_text()).get("mode")
            rs, hs = sha(d / "replay" / "summary.json"), sha(d / "hashes.json")
        except (OSError, ValueError):
            mode, rs, hs = None, None, None
        out.append(f"{Path(d).relative_to(root).parts[0]}/{d.name} ({tn},{tm}) {mode} {rs} {hs}")
    return sorted(out)


def scope_problems(root: Path, sub: str, tn: int, tm: int, failed_slices=frozenset()) -> tuple:
    """Every copy's G4 replay under root judged against its slice's audited evidence (the fleet's G4 gate; G5 round 19,
    finding 1: the full re-run's copies too): the pinned sampling policy, its mode's scope, its red controls, and a
    slice-mode copy's prefix covered by a passing full-mode copy. G5 round 20, finding 5: and every copy's shipped
    manifests by the controls' rules (the verify manifests, the software pins of each manifest, the enumeration and
    pruning manifests against the files and the slice's pooled audited evidence, each verify manifest's stage file in its
    own run or its prefix's), so that neither the fleet's copies nor the full re-run's rest on a software inventory
    pooled across manifests. Returns ([(slice, label, [why])], counts per mode, global problems, {slice: {cell: shards}}
    from the pooled evidence, for the checker records' shard counts)."""
    n = {"full": [0, 0], "slice": [0, 0]}
    glob, by = [], {}
    for d in sorted(root.glob(f"*/research/unit-distance-23/results/{sub}/{tn}-{tm}-L{LEVEL}-tri-pf74/s*of{COUNT}")):
        c = {"dir": d, "slice": int(re.fullmatch(rf"s(\d+)of{COUNT}", d.name).group(1))}
        try:
            c["rep"] = json.loads((d / "replay" / "summary.json").read_text())
            c["replay_mode"] = json.loads((d / "replay" / "fingerprint.json").read_text()).get("mode")
            c["seeds10"], c["audit"], c["prefix"] = seeds10_of(d), audited(d, tn, tm), prefix_of(d)
            c["reach_table"] = json.loads((d / "reach.json").read_text()).get("table") or {}
        except (OSError, ValueError) as e:
            c["error"] = f"unreadable ({type(e).__name__}: {e})"
        by.setdefault(c["slice"], []).append(c)
    pools, pclash = prefix_pools([c for cs in by.values() for c in cs])
    glob += pclash
    shards = {}
    for i, cs in sorted(by.items()):
        slice_ev, clash = pooled_parents(cs)
        glob += [f"s{i}: {w}" for w in clash]
        for c in cs:
            if "error" in c:
                c["why"] = [c["error"]]
                continue
            ev = evidence_for(c, slice_ev, pools)
            c["why"] = replay_pins(c["rep"]) + replay_scope(c, ev, tn)
            shards[i] = {cell: len(r) for cell, r in (ev.get("shards") or {}).items() if r is not None}
            d = c["dir"]
            try:   # the manifests, by the controls' rules, against the pooled evidence
                hj = json.loads((d / "hashes.json").read_text()).get("files") or {}
                c["why"] += [f"manifests: {w}" for w in verify_manifests(d, ev, hj, c.get("replay_mode")) + software(d)
                             + production_manifests(d, hj, tn, tm, ev)]
                c["verify_runs"] = verify_runs(d)
            except (OSError, ValueError, AttributeError, TypeError) as e:
                c["why"].append(f"manifests: unreadable ({type(e).__name__}: {e})")
    # each verify manifest's stage file lies in the copy's own run, or for the prefix in a full-mode run with its prefix
    full_runs = {f"dag-{Path(c['dir']).parent.name}-{Path(c['dir']).name}": c.get("prefix")
                 for cs in by.values() for c in cs if c.get("replay_mode") == "full"}
    for cs in by.values():
        for c in cs:
            run = f"dag-{Path(c['dir']).parent.name}-{Path(c['dir']).name}"
            stray = sorted(cell for cell, rdir in (c.get("verify_runs") or {}).items()
                           if not (rdir == run or (cell[0] <= LEVEL and full_runs.get(rdir) == c.get("prefix"))))
            if stray:
                c["why"] = (c.get("why") or []) + [f"manifests: verify manifests of {stray[:3]} name a stage file outside "
                                                   "this run (and, for the prefix, outside every full-mode run with it)"]
    # a slice-mode copy's prefix is covered only by a passing full-mode copy's replay (as in evaluate()); G5 round 23,
    # finding 1: passing the audit too (failed_slices: the slices the audit found a problem in)
    covered = {c.get("prefix") for i, cs in by.items() for c in cs
               if c.get("replay_mode") == "full" and not c["why"] and i not in failed_slices}
    prefixes = {c.get("prefix") for cs in by.values() for c in cs if c.get("prefix")}
    if len(prefixes) > 1:
        glob.append(f"the copies record {len(prefixes)} different prefixes (levels <= {LEVEL}); a run has one")
    out = []
    for i, cs in sorted(by.items()):
        for c in cs:
            why = c["why"] or ([] if c.get("prefix") in covered else
                               [f"its prefix (levels <= {LEVEL}, {str(c.get('prefix'))[:16]}) is not one a "
                                "passing full-mode G4 replay covers"])
            mode = c.get("replay_mode")
            if mode in n:
                n[mode][0] += 1
                n[mode][1] += not why
            out.append((i, f"{Path(c['dir']).relative_to(root).parts[0]}/{Path(c['dir']).name}", why))
    return out, n, glob, shards


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--target", type=int, nargs=2, required=True)
    ap.add_argument("--sub", default="u23")
    ap.add_argument("--root-k", type=int, required=True)
    ap.add_argument("--no-ubar", action="store_true")
    ap.add_argument("--expect-empty", action="store_true")
    ap.add_argument("--known", type=Path)
    ap.add_argument("--fetch")
    ap.add_argument("--labelg", default=shutil.which("nauty-labelg") or shutil.which("labelg") or "nauty-labelg")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--scope-only", action="store_true", help="only each copy's G4 replay scope (for the fleet)")
    a = ap.parse_args()
    tn, tm = a.target
    if a.scope_only:   # each copy's G4 replay against its slice's audited evidence (the fleet's G4 gate)
        per_copy, n, glob, _ = scope_problems(a.root, a.sub, tn, tm)
        bad = glob + [f"{label}: {w}" for _, label, ws in per_copy for w in ws]
        for b in bad[:100]:
            print("PROBLEM:", b)
        ok = not bad and n["full"][0] > 0
        # G5 round 21-22: the copies covered, by identity, for write_result to bind to the aggregate's
        lines_ = copies_lines(a.root, a.sub, tn, tm)
        print(f"G4-SCOPE COPIES ({tn},{tm}): {len(lines_)} copies, sha256 "
              f"{hashlib.sha256(chr(10).join(lines_).encode()).hexdigest()}")
        print(f"G4-SCOPE {'OK' if ok else 'FAIL'}: {n['full'][1]} of {n['full'][0]} full-mode replays and "
              f"{n['slice'][1]} of {n['slice'][0]} slice-mode replays in their mode's scope; {len(bad)} problem(s)")
        return 0 if ok else 1
    if a.fetch:
        a.root.mkdir(parents=True, exist_ok=True)
        fetch(a.root, a.fetch, a.sub)
    known = [x.strip() for x in a.known.read_text().splitlines() if x.strip()] if a.known else None
    print(f"parameters: target ({tn},{tm}), root minimum degree {a.root_k}, u-bar override "
          f"{'refused' if a.no_ubar else 'the fleet 22=60 only'}, top level "
          f"{'empty' if a.expect_empty else 'holding the known graphs' if known else 'unchecked'}, known "
          + (f"{a.known.name} sha256 {sha(a.known)} ({len(known)} graphs)" if known is not None else "none")
          + f"; checker target_check.py sha256 {sha(HERE)}; audit verify-chain.py sha256 {sha(VERIFY_CHAIN)}")
    copies, aud = collect(a.root, a.sub, tn, tm, a.root_k, a.no_ubar)
    code = self_test(copies, aud, a, known, a.labelg) if a.self_test else 0
    problems, s = evaluate(copies, aud, tn, tm, known, a.expect_empty, a.labelg)
    return report(problems, s, tn, tm, aud) or code


if __name__ == "__main__":
    sys.exit(main())
