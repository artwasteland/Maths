"""Measured producer policy. A search result is always just a proposed record."""
from common import *
import ast
import subprocess
from dataclasses import dataclass
from exact import graph6


@dataclass(frozen=True)
class Stage:
    name: str
    method: str
    seconds: float
    nodes: int = 0
    check_seconds: float = 60

    def budget(self):
        return dict(vars(self), all_pairs=self.method in ("null", "real", "portfolio"))


CHEAP = [Stage("tu", "tu", 5), Stage("extension", "extension", 3), Stage("rebase", "rebase", 3)]
STANDARD = CHEAP + [Stage("lattice", "lattice18", .5, 20000), Stage("host", "host", 1, 20000),
    Stage("tree", "tree", 1, 1200), Stage("null", "null", 3), Stage("real", "real", 3),
    Stage("msolve", "msolve", 20), Stage("portfolio", "portfolio", 10)]
ESCALATION = [Stage("esc-extension", "extension", 60), Stage("esc-numeric", "numeric", 60),
    Stage("esc-branch", "branch_exact", 30), Stage("esc-msolve", "msolve_long", 120),
    Stage("esc-rebase", "rebase", 60), Stage("esc-saturated", "msolve_sat", 180),
    Stage("esc-saved", "saved_exact", 180, check_seconds=180), Stage("esc-tree", "tree", 60, 100000),
    Stage("esc-targeted", "targeted", 60), Stage("esc-null", "null", 60), Stage("esc-real", "real", 60),
    Stage("esc-pins", "numeric_pin", 120), Stage("esc-components", "targeted_components", 180)]
LATE = [Stage("esc-branch-refute", "branch_refute", 120, check_seconds=120),
        Stage("esc-subfield", "subfield_exact", 180, check_seconds=120)]
# "full" stays the policy frontier wave 1 ran (2026-10-01); the late stages are separate policies so that a worker
# started later in that wave runs the same stages. "late" re-derives the numerical seeds the subfield stage reads
# (a fresh state has no saved numeric files) and then runs the two late stages on a residue that has had "full".
# "long" (2026-10-01, a probe first): on a residue that has had "full", re-derive the numerical seeds, then give the
# stages whose proposals died on checker:Deadline 900-second checks, and the refuters that hit TimeoutExpired ten
# times their escalation budgets. Same methods, longer clocks; a search result is still only a proposal.
LONG = [Stage("esc-numeric", "numeric", 60),
        Stage("long-saturated", "msolve_sat", 600, check_seconds=900),
        Stage("long-saved", "saved_exact", 600, check_seconds=900),
        Stage("long-pins", "numeric_pin", 600, check_seconds=900),
        Stage("long-targeted", "targeted", 600), Stage("long-null", "null", 600), Stage("long-real", "real", 600),
        Stage("long-components", "targeted_components", 900)]
POLICIES = {"cheap": CHEAP, "standard": STANDARD, "full": STANDARD + ESCALATION,
            "late": [Stage("esc-numeric", "numeric", 60)] + LATE, "full-late": STANDARD + ESCALATION + LATE,
            "long": LONG}


class Producers:
    def __init__(self, store, tu):
        self.store = store
        self.tu = tu
        self.work = store.directory / "scratch"

    def warm(self, stage):
        # Charge one-time imports/library preparation to the job, not its first graph.
        method = stage.method
        if method == "tu":
            return
        if method in ("branch_refute", "subfield_exact"):
            # The bounded worker imports its own native algebra libraries.
            return
        if method in ("extension", "rebase"):
            from extension import index
            index()
        elif method.startswith("lattice"):
            import lattice
        elif method == "host":
            from hosts import database
            database()
        elif method in ("tree", "null", "real", "portfolio", "targeted", "targeted_components"):
            import gp10refute
            import amp_core
            import algebra
        else:
            import generic_exact
            import portfolio
            import numeric_branch
        redirect(self.work)
        if method in ("msolve", "msolve_long", "msolve_sat", "saved_exact", "numeric_pin", "targeted_components"):
            import msolve_exact
            msolve_exact.prepare_binary()
            if not (self.work / "msolve_seed.so").exists():
                subprocess.run(["cc", "-O2", "-fPIC", "-c", str(GP / "embed/msolve_seed.c"),
                                "-o", str(self.work / "msolve_seed.o")], check=True)
                subprocess.run(["ld", "-shared", str(self.work / "msolve_seed.o"), "-ldl",
                                "-o", str(self.work / "msolve_seed.so")], check=True)

    def propose(self, code, stage):
        if stage.method == "tu":
            return self.tu.propose(code, self.store)
        cap = stage.seconds
        key = hashlib.sha256(code.encode()).hexdigest()[:16]
        directory = self.work / (stage.name + "-cases") / key
        directory.mkdir(parents=True, exist_ok=True)
        closure = self.tu.closure(code)
        search_code = code
        if stage.method in ("tree", "null", "real", "portfolio", "msolve_sat", "saved_exact", "numeric_pin", "targeted", "targeted_components"):
            search_code = closure["g6"]
        n, edges = graph6(search_code)
        seed = int.from_bytes(hashlib.sha256(search_code.encode()).digest(), "big")
        cert = None
        detail = {}
        started = time.monotonic()
        try:
            with timer(cap):
                if stage.method in ("extension", "rebase"):
                    from extension import search
                    cert, detail = search(code, cap, directory, self.store.ck, stage.method == "rebase")
                elif stage.method.startswith("lattice"):
                    from lattice import search
                    cert, detail = search(n, edges, seed, stage.method, stage.nodes)
                elif stage.method == "host":
                    from hosts import search
                    cert, detail = search(n, edges, seed, stage.nodes)
                elif stage.method == "tree":
                    from gp10refute import tree_search
                    cert, detail = tree_search(search_code, stage.nodes)
                elif stage.method in ("null", "real", "portfolio"):
                    from algebra import algebra_search
                    cert, detail = algebra_search(search_code, stage.method, max(.01, cap-.2), all_pairs=True, dag="auto")
                elif stage.method == "msolve":
                    from rigid_system import generic_rank
                    from generic_exact import msolve_stage
                    rank, rank_detail = generic_rank(code)
                    cert, detail = msolve_stage(code, directory, 2*n-3-rank, max(.01, cap-.2), 2, 2)
                    detail["rank"] = rank_detail
                elif stage.method == "numeric":
                    from numeric_branch import search
                    cert, detail = search(code, max(.01, cap-.1), self.work / "numeric" / key)
                elif stage.method == "branch_refute":
                    from branch_refute import search
                    cert, detail = search(code, max(.01, cap-.2), directory)
                elif stage.method == "subfield_exact":
                    from subfield_exact import search
                    cert, detail = search(code, max(.01, cap-.2), directory, work=self.work)
                else:
                    from portfolio import run
                    saved = self.work / "numeric" / key / "numeric.json"
                    evidence = json.loads(saved.read_text()) if saved.exists() else None
                    if evidence and code != search_code and stage.method in ("msolve_sat", "numeric_pin"):
                        evidence = dict(evidence)
                        mapping = closure["old_to_new"]
                        evidence["collision_pairs"] = {str(tuple(sorted(mapping[v] for v in ast.literal_eval(pair)))): count
                                                       for pair, count in evidence["collision_pairs"].items()}
                        if evidence.get("coords"):
                            evidence["coords"] = [evidence["coords"][mapping.index(v)] for v in range(n)]
                    cert, detail = run(stage.method, search_code, cap-.2, directory, self.work, evidence, code, closure)
        except Deadline:
            detail.update(reason="wall_budget")
            cert = None
        except Exception as exc:
            detail.update(reason="producer_error:" + type(exc).__name__, error=str(exc)[-1000:])
            cert = None
        detail.update(search_g6=search_code, search_seconds=time.monotonic()-started)
        if cert is None:
            return unknown(code, str(detail.get("reason", "no_certificate")), stage.budget()), detail
        verdict = "embedded" if cert["type"] == "exact" else "refuted"
        if code != search_code:
            if verdict == "embedded":
                cert = {"type": "exact", "field": cert["field"],
                        "coords": [cert["coords"][v] for v in closure["old_to_new"]]}
            else:
                with timer(stage.check_seconds):
                    self.store.accept({"g6": search_code, "verdict": verdict, "cert": cert}, stage.name + ":endpoint")
                cert = {"type": "tu", "steps": closure["steps"], "end": {
                    "refuted": search_code, "map": [closure["old_to_new"].index(v) for v in range(n)]}}
        return {"g6": code, "verdict": verdict, "cert": cert}, detail


def run(store, tu, policy):
    producers = Producers(store, tu)
    for stage in POLICIES[policy]:
        tu.drain(store)
        if store.db.execute("SELECT 1 FROM completed WHERE stage=?", (stage.name,)).fetchone():
            continue
        order = store.order(stage.name, "up" if stage.method in ("tu", "tree", "null", "real") else "down")
        if order:
            producers.warm(stage)
        start = time.monotonic()
        print(compact({"event": "stage_start", "stage": stage.name, "eligible": len(order), "counts": store.counts()}), flush=True)
        attempted = 0
        for gid in order:
            code = store.poset.codes[gid]
            if store.has(code):
                continue
            store.guard.check()
            token = store.lease(gid, stage.name, stage.seconds + 2*stage.check_seconds + 60)
            began = time.monotonic()
            try:
                record, detail = producers.propose(code, stage)
                with timer(stage.check_seconds):
                    store.finish(gid, stage.name, token, record, stage.budget(), time.monotonic()-began, detail)
            except (store.ck.Rejection, Deadline, ValueError) as exc:
                if isinstance(exc, store.ck.Rejection) and exc.reason == "embedded_refuted_conflict":
                    raise
                reason = "checker:" + (exc.reason if isinstance(exc, store.ck.Rejection) else type(exc).__name__)
                detail = {"checker_error": type(exc).__name__+":"+str(exc), "reason": reason}
                record = unknown(code, reason, stage.budget())
                store.finish(gid, stage.name, token, record, stage.budget(), time.monotonic()-began, detail)
            if record["verdict"] != "unknown":
                store.propagate(code)
                tu.drain(store)
            # Keep diagnostics for saved-output retries, never as decision evidence.
            with (producers.work / (stage.name + "-stats.jsonl")).open("a") as stream:
                stream.write(compact({"g6": code, "meta": detail}) + "\n")
            attempted += 1
            if attempted % 100 == 0 or time.monotonic()-start > 30:
                print(compact({"event": "progress", "stage": stage.name, "attempted": attempted,
                               "counts": store.counts(), "minimum_available_kib": store.guard.minimum_kib}), flush=True)
                start = time.monotonic()
            from graph6 import _canonicalize_cached
            _canonicalize_cached.cache_clear()
        store.coverage()
        store.db.execute("INSERT INTO completed VALUES (?)", (stage.name,))
        store.db.commit()
        print(compact({"event": "stage_complete", "stage": stage.name, "attempted": attempted, "counts": store.counts()}), flush=True)
