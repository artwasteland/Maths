#!/usr/bin/env python3
"""Red controls for the Mode 398 speed work: broken builds of the NEW source must fail the identity check.

Each mutant is the new enum/udenum.c with one deliberate fault planted by text substitution (each
substitution must apply exactly once), built with the Makefile's flags.  It is run on the red
cells against the REFERENCE (test-398/base398/udenum, the current Mode 398) with the same check
speed398-identity.py uses: exit status, output bytes and all nine counters.  A mutant goes red iff
some cell differs.  The unmutated new binary must be identical on every red cell (the baseline of
the control).

Mutants:
  role-<i>      drop one anchor role: the search pattern i (an orbit class (F, v)) is skipped in
                anchored_images_398, the pattern path
  role-T-<i>    the same in anchored_family_398, the restricted path's T; built with the switch
                forced (RESTRICTED_SWITCH_CANDIDATES=1) so that T answers wherever it may
  rooted-always T searches every pattern only from roots in R, also when |S| <= d - |R| (where an
                image may miss R); switch forced
  one-per-F     over-deduplication: one pattern per forbidden graph instead of one per orbit;
                (a) with the pinned orbit-class guard, which must refuse to run; (b) that guard
                removed (the pinned class-count guard then refuses); (c) both guards removed, so
                that only the identity check can see it
  no-proof      T used from the start without proof that the parent is 398-free (switch forced)
  early-exit    stop after the first embedding even before every S vertex is placed
  tri+1 / sq+1  the triangle / 4-cycle vertex filter one too strict
  pair+1        every pair constraint one common neighbour too strict
  T-size-1      T built with the size bound d-1 (switch forced)
  cf-skip-<i>   contains_forbidden_398 skips forbidden graph i (0 = K4, 74 = the first of the 324, 397)
  class-by-n    the graph classes of the existence cache formed by order alone (non-isomorphic graphs
                share one existence answer); (a) with the pinned class-count guard, which must refuse
                to run; (b) guard removed
  uncovered-count-1  the pattern path's count of uncovered s-sets one too low (it stops one set early
                and starts the direct tests one set early); (a) with the self-check against the
                refreshed list, which must refuse to run on some cell; (b) self-check removed
  direct-test-into-not-onto  the direct test leaves one S position off the target set, so it also
                accepts embeddings whose image is not the target (tracking forced on every order,
                UNCOVERED_MIN_ORDER=1, as in the three below)
  direct-test-drops-single-image  a pattern with exactly one uncovered image adds nothing
  direct-test-stops-at-first-image  the direct test stops at the first image and adds it alone
  direct-test-list-order  an ORDER-only change: two or more uncovered images are added in numeric
                order instead of the search's; same sets, so the outputs must NOT change (the order
                is checked by speed398-family.py, whose red control is this same change)

Red cells: sampled parents of speed.py at levels 12, 16 and 17 (398-free at 12 and 16; all at 17,
where most contain one of the 324), at levels 14 (all) and 18 (398-free), dense cells where the
direct tests of the pattern path find one and several uncovered images, the 743 real level-21
parents (all 48 slices), and "--filter"
over the 398 members themselves grouped by order and size (each member contains itself and, the
list being an antichain, no other member, so a containment test that drops one member lets
exactly that member through).

The WRONG identity checks are shown failing on purpose: a reference output with two children
swapped, and one with its first child replaced by a copy of the second, pass "same count" (and
the first passes "same set") while the byte check fails both.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from speed398lib import (BASE398_SHA256, BASE398_UDENUM, F398_G6, NEW_SOURCE, NEW_UDENUM, SCRATCH, build_variant,
                         compare_runs, g6_lines, g6_order_size, run_udenum, sha256, write_lines)


def mutants() -> list[dict]:
    src_drop = "        if (g->ssize > max_bad_size) continue;\n        if (g->ssize != size) {"
    out = []
    # 208 and 2333 are the roles that add the most sets on the red cells (208 is the last |S| = 2
    # class, 2333 an |S| = 3 class); 0, 209 and 2335 are the first classes of |S| = 2, 3, 4; 3000 is
    # arbitrary.  A role that adds nothing on these inputs cannot be seen missing there: those
    # mutants are informational (must_go_red False), the others must go red.
    for i in (0, 208, 209, 2335, 3000):
        out.append({"name": f"role-{i}", "defines": [], "must_go_red": i in (0, 208, 209),
                    "patches": [(src_drop, src_drop.replace("        if (g->ssize > max_bad_size) continue;",
                                                            f"        if (g->ssize > max_bad_size || i == {i}) continue;"))]})
    fam = "        if (g->ssize > max_bad_size || embeds[cls] < 0) continue;"
    for i in (208, 2333, 209, 2335):
        out.append({"name": f"role-T-{i}", "defines": ["RESTRICTED_SWITCH_CANDIDATES=1"],
                    "must_go_red": i in (208, 2333),
                    "patches": [(fam, fam.replace("embeds[cls] < 0)", f"embeds[cls] < 0 || i == {i})"))]})
    out.append({"name": "rooted-always", "defines": ["RESTRICTED_SWITCH_CANDIDATES=1"],
                "patches": [("        if (g->ssize <= slack) {", "        if (g->ssize <= slack && 0) {")]})
    dedup = ("        if (orbits[p->source][p->deleted] != p->deleted) continue;\n")
    dedup_bad = ("        if (orbits[p->source][p->deleted] != p->deleted) continue;\n"
                 "        if (seen_source[p->source]++) continue;\n")
    decl = "    int i, rooted_count = 0;\n    memset(s, 0, sizeof(*s));"
    decl_bad = "    int i, rooted_count = 0;\n    static int seen_source[MAXF];\n    memset(s, 0, sizeof(*s));"
    guard = "    if (s->pattern_count != SEARCH_398_PATTERNS ||"
    out.append({"name": "one-per-F (guard kept)", "defines": [], "expect_refusal": True,
                "patches": [(dedup, dedup_bad), (decl, decl_bad)]})
    out.append({"name": "one-per-F (orbit guard removed)", "defines": [],
                "patches": [(dedup, dedup_bad), (decl, decl_bad), (guard, "    if (0 &&")]})
    out.append({"name": "one-per-F (both pinned guards removed)", "defines": [],
                "patches": [(dedup, dedup_bad), (decl, decl_bad), (guard, "    if (0 &&"),
                            ("    if (s->class_count != SEARCH_398_GRAPH_CLASSES)",
                             "    if (0 && s->class_count != SEARCH_398_GRAPH_CLASSES)")]})
    out.append({"name": "no-proof", "defines": ["RESTRICTED_SWITCH_CANDIDATES=1"],
                "patches": [("    if (parent_known_free && total >= threshold) {",
                             "    if (total >= threshold) {")]})
    out.append({"name": "early-exit", "defines": [],
                "patches": [("        if (search_images(c, depth + 1, used | (UINT32_C(1) << hv), next_image) &&\n"
                             "            depth >= g->s_complete_depth)\n",
                             "        if (search_images(c, depth + 1, used | (UINT32_C(1) << hv), next_image))\n")]})
    out.append({"name": "tri+1", "defines": [],
                "patches": [("h->triangles_at_least[g->triangles[k]]", "h->triangles_at_least[g->triangles[k] + 1]")]})
    out.append({"name": "sq+1", "defines": [],
                "patches": [("h->squares_at_least[g->squares[k]]", "h->squares_at_least[g->squares[k] + 1]")]})
    out.append({"name": "pair+1", "defines": [],
                "patches": [("        candidates &= c->h->pair[g->cons_type[depth][q]][c->map[g->cons_pos[depth][q]]];",
                             "        candidates &= c->h->pair[g->cons_type[depth][q] % (SG_CN_CAP + 1) == SG_CN_CAP ? "
                             "g->cons_type[depth][q] : g->cons_type[depth][q] + 1][c->map[g->cons_pos[depth][q]]];")]})
    tb = "anchored_family_398(s, host, host_m, max_bad_size, required, anchored);"
    out.append({"name": "T-size-1", "defines": ["RESTRICTED_SWITCH_CANDIDATES=1"],
                "patches": [(tb, tb.replace("max_bad_size, required", "max_bad_size - 1, required"), 2)]})
    cmp_ok = ("    for (k = 0; k < a->n; ++k)\n        if (a->rows[k] != b->rows[k]) return a->rows[k] < b->rows[k] ? -1 : 1;\n"
              "    return 0;\n}")
    cmp_bad = "    (void)k;\n    return 0;\n}"
    cguard = "    if (s->class_count != SEARCH_398_GRAPH_CLASSES)"
    out.append({"name": "class-by-n (guard kept)", "defines": [], "expect_refusal": True,
                "patches": [(cmp_ok, cmp_bad)]})
    out.append({"name": "class-by-n (guard removed)", "defines": [],
                "patches": [(cmp_ok, cmp_bad), (cguard, "    if (0 && s->class_count != SEARCH_398_GRAPH_CLASSES)")]})
    left = "            left = start_uncovered - (family->count - start_count);"
    left_bad = "            left = start_uncovered - (family->count - start_count) - (start_uncovered > 0);"
    ucheck = "                if (listed != left) die("
    out.append({"name": "uncovered-count-1 (self-check kept)", "defines": [], "expect_refusal_somewhere": True,
                "patches": [(left, left_bad)]})
    out.append({"name": "uncovered-count-1 (self-check removed)", "defines": [],
                "patches": [(left, left_bad), (ucheck, "                if (0 && listed != left) die(")]})
    out.append({"name": "direct-test-into-not-onto", "defines": ["UNCOVERED_MIN_ORDER=1"],
                "patches": [("        t.vertex_mask[k] &= target;", "        if (k + 1 < g->ssize) t.vertex_mask[k] &= target;")]})
    out.append({"name": "direct-test-drops-single-image", "defines": ["UNCOVERED_MIN_ORDER=1"],
                "patches": [("                bad_family_add(family, found);\n", "                (void)found;\n")]})
    out.append({"name": "direct-test-stops-at-first-image", "defines": ["UNCOVERED_MIN_ORDER=1"],
                "patches": [("for (u = 0; u < listed && images < 2; ++u) {", "for (u = 0; u < listed && images < 1; ++u) {")]})
    # an ORDER-only change (same sets, other order): the output cannot show it, so here it must
    # stay identical; speed398-family.py's red control shows the family check catching it
    out.append({"name": "direct-test-list-order (order only)", "defines": ["UNCOVERED_MIN_ORDER=1"], "must_go_red": False,
                "expect_identical": True,
                "patches": [("            if (images == 1) {\n                bad_family_add(family, found);\n                continue;\n            }",
                             "            if (images >= 1) {\n                for (u = 0; u < listed; ++u)\n"
                             "                    if (pattern_has_image(s, h, host_m, i, uncovered[u])) bad_family_add(family, uncovered[u]);\n"
                             "                continue;\n            }")]})
    for i in (0, 74, 397):
        out.append({"name": f"cf-skip-{i}", "defines": [],
                    "patches": [("        if (!search_prepare(&c, &s->forbidden[i], m)) continue;",
                                 f"        if (i == {i} || !search_prepare(&c, &s->forbidden[i], m)) continue;")]})
    return out


def build_mutant(mu: dict, work: Path) -> Path:
    src = NEW_SOURCE.read_text()
    for patch in mu["patches"]:
        old, new = patch[0], patch[1]
        want = patch[2] if len(patch) > 2 else 1
        if src.count(old) != want:
            raise SystemExit(f"mutant {mu['name']}: patch applies {src.count(old)} times, expected {want}")
        src = src.replace(old, new)
    tag = "".join(ch if ch.isalnum() else "_" for ch in mu["name"])
    path = work / "src" / f"udenum-{tag}.c"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return build_variant(path, work / "bin" / f"udenum-{tag}", mu["defines"], allow_warnings=True)


def red_cells(a, work: Path) -> list[dict]:
    sw = a.speed_work
    cs = [{"cell": "L12 (13,23) 398-free", "parents": sw / "measure-12-23.free.g6", "n": 13, "m": 23},
          {"cell": "L16 (17,38) 398-free", "parents": sw / "measure-16-38.free.g6", "n": 17, "m": 38},
          {"cell": "L17 (18,42) all", "parents": sw / "measure-17-42.all.g6", "n": 18, "m": 42},
          # dense cells where the pattern path's direct tests find one and several uncovered images
          {"cell": "L14 (15,30) all", "parents": sw / "measure-14-30.all.g6", "n": 15, "m": 30},
          {"cell": "L18 (19,46) 398-free", "parents": sw / "measure-18-46.free.g6", "n": 19, "m": 46}]
    l21 = work / "l21-all.g6"
    write_lines(l21, [g for s in range(48) for g in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
    cs.append({"cell": "L21 (22,61) the 743 real parents", "parents": l21, "n": 22, "m": 61})
    by_nm: dict[tuple[int, int], list[bytes]] = {}
    for g in g6_lines(F398_G6):
        by_nm.setdefault(g6_order_size(g), []).append(g)
    for (n, m), gs in sorted(by_nm.items()):
        f = work / f"members-{n}-{m}.g6"
        write_lines(f, gs)
        cs.append({"cell": f"--filter the members with n={n} m={m}", "parents": f, "n": n, "m": m,
                   "extra": ["--filter"], "filter_group": True})
    return cs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed-work", type=Path, required=True, help="speed.py's work directory (measure files)")
    ap.add_argument("--slices", type=Path, required=True, help="results/u22 of the worker branches (s0of48..)")
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-red")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-red.json")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    if sha256(BASE398_UDENUM) != BASE398_SHA256:
        print("the reference binary is not the pinned Mode 398 binary")
        return 2
    cs = red_cells(a, w)
    refs = {}
    for i, c in enumerate(cs):
        refs[i] = run_udenum(BASE398_UDENUM, c["parents"], c["n"], c["m"], w / "ref" / f"c{i}.g6", extra=c.get("extra", []))
        if refs[i]["returncode"] != 0:
            raise SystemExit(f"reference failed on {c['cell']}: {refs[i]['stderr_tail']}")
    report = {"cells": [c["cell"] for c in cs], "baseline": {}, "mutants": [], "wrong_checks": []}

    # baseline: the unmutated new binary is identical on every red cell
    base_ok = True
    for i, c in enumerate(cs):
        got = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], w / "new" / f"c{i}.g6", extra=c.get("extra", []))
        p = compare_runs(refs[i], got)
        base_ok = base_ok and not p
        report["baseline"][c["cell"]] = p or "identical"
    filter_cells = [i for i, c in enumerate(cs) if c.get("filter_group")]
    members_removed = sum(refs[i]["stats"]["neighbourhoods_bad"] for i in filter_cells)
    print(f"baseline: new binary identical on all {len(cs)} red cells: {base_ok}; the reference --filter "
          f"removes {members_removed} of the 398 members", flush=True)

    all_red = True
    for mu in mutants():
        binary = build_mutant(mu, w)
        diffs = []
        refused = []
        for i, c in enumerate(cs):
            got = run_udenum(binary, c["parents"], c["n"], c["m"], w / "mut" / f"{binary.name}-c{i}.g6",
                             extra=c.get("extra", []))
            p = compare_runs(refs[i], got)
            if p:
                diffs.append({"cell": c["cell"], "problems": p[:4]})
                if got["returncode"] != 0:
                    refused.append(got["stderr_tail"])
        went_red = bool(diffs)
        if mu.get("expect_refusal"):
            went_red = went_red and len(refused) == len(cs)
        if mu.get("expect_refusal_somewhere"):
            went_red = went_red and len(refused) > 0
        must = mu.get("must_go_red", True)
        if must:
            all_red = all_red and went_red
        if mu.get("expect_identical"):
            all_red = all_red and not diffs
        report["mutants"].append({"mutant": mu["name"], "must_go_red": must, "went_red": went_red,
                                  "cells_differing": len(diffs), "differences": diffs, "refusals": refused[:1]})
        first = diffs[0] if diffs else None
        tag = "went red" if went_red else ("DID NOT GO RED" if must else "did not go red (informational)")
        if mu.get("expect_identical"):
            tag = ("identical, as an order-only change must be" if not diffs
                   else "CHANGED THE OUTPUT (an order-only change must not)")
        print(f"RED CONTROL {tag}: {mu['name']}: {len(diffs)} of {len(cs)} cells differ"
              + (f"; e.g. {first['cell']}: {', '.join(first['problems'])}" if first else ""), flush=True)

    # the wrong identity checks, on a reference output with at least two children
    i = next(k for k in refs if not cs[k].get("filter_group") and len(g6_lines(refs[k]["output"])) >= 2)
    ref_lines = g6_lines(refs[i]["output"])
    swapped = [ref_lines[1], ref_lines[0]] + ref_lines[2:]
    replaced = [ref_lines[1]] + ref_lines[1:]
    for name, cand in (("two children swapped", swapped), ("the first child replaced by a copy of the second", replaced)):
        count_check = len(cand) == len(ref_lines)
        set_check = set(cand) == set(ref_lines)
        byte_check = b"".join(x + b"\n" for x in cand) == refs[i]["output"].read_bytes()
        report["wrong_checks"].append({"planted": name, "cell": cs[i]["cell"], "count_check_passes": count_check,
                                       "set_check_passes": set_check, "byte_check_passes": byte_check})
        print(f"WRONG CHECK on {cs[i]['cell']}, {name}: same count {count_check}, same set {set_check}; "
              f"byte check {'passes (BAD)' if byte_check else 'fails (as it must)'}", flush=True)
    wrong_ok = all(not r["byte_check_passes"] and r["count_check_passes"] for r in report["wrong_checks"])
    ok = base_ok and all_red and wrong_ok and members_removed == 398
    report["pass"] = ok
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(report, indent=1) + "\n")
    print("RESULT:", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
