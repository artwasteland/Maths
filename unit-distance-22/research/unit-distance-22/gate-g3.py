#!/usr/bin/env python3
"""Gate G3 (CONTRACT Section 7): embed or refute the TU-survivors at n = 16..21.

For each n with a survivors file, run the embedder on every survivor, run the blind checker on
the certificates, and require: every known extremal graph (AMP's 56, sources/amp/anc/graph6.txt)
among the survivors is EMBEDDED, every other survivor is REFUTED with a proof tree, nothing is
unknown, and the checker ACCEPTs. Prints one line per n and a final GATE G3 PASS / FAIL.

Survivor files: --survivors-dir D with D/survivors-<n>-<m>.g6 (from integrate.py) or
D/<n>-<m>.keep.g6 (a run-dag2 keep set, e.g. results/calib/<n>-<m>/); --n restricts.
--self-test runs the 56 known graphs as if they were survivors (all must embed and match) and
then a mutation that must FAIL (one known graph dropped from the known list, so an embedded
survivor is no longer expected): a gate that cannot go red is not a gate.
"""
import argparse, collections, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.environ.get("MATHS_PY", os.path.expanduser("~/tools/pyenv-maths/bin/python"))
if not os.path.exists(PY): PY = sys.executable
U = {16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57}
EXP_TU = {16: 1, 17: 8, 18: 38, 19: 5, 20: 1, 21: 19}
EXP_EMB = {16: 1, 17: 7, 18: 16, 19: 3, 20: 1, 21: 5}

def canon(lines):
    if not lines: return []
    p = subprocess.run(["nauty-labelg", "-q"], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True)
    return p.stdout.split()

def load_known():
    known = collections.defaultdict(set)
    for l in open(os.path.join(HERE, "sources", "amp", "anc", "graph6.txt")):
        l = l.strip()
        if l: known[ord(l[0]) - 63].add(l)
    return {n: set(canon(sorted(v))) for n, v in known.items()}

def run_gate(n, survivors, known_n, tries, max_states, workdir, tag):
    """Return (ok, summary line, details dict)."""
    surv = canon(survivors)
    dups = len(surv) - len(set(surv))
    g6 = os.path.join(workdir, f"{tag}-{n}.g6"); open(g6, "w").write("".join(s + "\n" for s in surv))
    certs = os.path.join(workdir, f"{tag}-{n}.jsonl"); unk = os.path.join(workdir, f"{tag}-{n}.UNKNOWN.g6")
    with open(certs, "w") as out:
        r = subprocess.run([PY, "-u", os.path.join(HERE, "embed", "udembed.py"), g6, "--tries", str(tries),
                            "--max-states", str(max_states), "--unknown-file", unk], stdout=out, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        return False, f"n={n}: embedder exited {r.returncode}: {r.stderr.strip()[:200]}", {}
    recs = [json.loads(l) for l in open(certs) if l.strip()]
    hist = collections.Counter(rec["verdict"] for rec in recs)
    embedded = {rec["g6"] for rec in recs if rec["verdict"] == "embedded"}
    refuted = {rec["g6"] for rec in recs if rec["verdict"] == "refuted"}
    unknown = {rec["g6"] for rec in recs if rec["verdict"] == "unknown"}
    chk = subprocess.run([PY, os.path.join(HERE, "check", "udcheck.py"), "--allow-any-size", "--graphs", g6,
                          "--unknown-file", unk, certs], capture_output=True, text=True)
    accept = chk.returncode == 0 and any(l.startswith("ACCEPT") for l in chk.stdout.splitlines())
    known_here = known_n & set(surv)
    extra_embedded = embedded - known_n          # a survivor embedded that AMP did not list: new extremal graph or a bug
    missing_embedded = known_here - embedded     # a known extremal graph we failed to embed
    wrong_refuted = refuted & known_n            # a known UD graph "refuted": the proof tree is unsound
    ok = (accept and not extra_embedded and not missing_embedded and not wrong_refuted and not unknown
          and dups == 0 and len(recs) == len(surv))
    line = (f"n={n} m={U.get(n,'?')}: survivors={len(surv)} (expect {EXP_TU.get(n,'?')}), embedded={len(embedded)} "
            f"(expect {EXP_EMB.get(n,'?')}), refuted={len(refuted)}, unknown={len(unknown)}, dups={dups}, "
            f"known-among-survivors={len(known_here)}/{len(known_n)}, extra-embedded={len(extra_embedded)}, "
            f"missing-embedded={len(missing_embedded)}, known-refuted={len(wrong_refuted)}, "
            f"checker={'ACCEPT' if accept else 'REJECT: ' + (chk.stdout + chk.stderr).strip().splitlines()[-1][:120] if (chk.stdout + chk.stderr).strip() else 'REJECT'}")
    return ok, line, {"embedded": sorted(embedded), "refuted": sorted(refuted), "unknown": sorted(unknown),
                      "extra_embedded": sorted(extra_embedded), "missing_embedded": sorted(missing_embedded),
                      "certs": certs, "hist": dict(hist)}

def find_survivors(d, n):
    for name in (f"survivors-{n}-{U[n]}.g6", f"{n}-{U[n]}.keep.g6", os.path.join(f"{n}-{U[n]}", f"{n}-{U[n]}.keep.g6")):
        p = os.path.join(d, name)
        if os.path.exists(p): return [l.strip() for l in open(p) if l.strip()]
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--survivors-dir", default=HERE)
    ap.add_argument("--n", type=int, nargs="*")
    ap.add_argument("--tries", type=int, default=24)
    ap.add_argument("--max-states", type=int, default=400)
    ap.add_argument("--workdir", default=os.path.join(HERE, "gate-g3-work"))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report", help="write a JSON report here")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)
    known = load_known()
    report = {"python": PY, "tries": a.tries, "max_states": a.max_states, "cells": {}}
    if a.self_test:
        ok_all = True
        for n in sorted(known):
            ok, line, det = run_gate(n, sorted(known[n]), known[n], a.tries, a.max_states, a.workdir, "selftest")
            print(("OK   " if ok else "FAIL ") + line); ok_all &= ok
        # mutation that must FAIL: forget one known graph at n=17 (an embedded survivor is then "extra")
        n = 17; dropped = sorted(known[n])[0]
        ok, line, det = run_gate(n, sorted(known[n]), known[n] - {dropped}, a.tries, a.max_states, a.workdir, "mutation")
        print(("FAIL (as required) " if not ok else "BUG: mutation passed ") + line)
        ok_all &= (not ok) and det.get("extra_embedded") == [dropped]
        # mutation that must FAIL: a corrupted certificate byte must be rejected by the checker
        certs = os.path.join(a.workdir, "selftest-16.jsonl"); txt = open(certs).read()
        bad = txt.replace('"embedded"', '"embedded"', 1).replace("coordinates", "coordinates", 1)
        i = txt.find('"coordinates":[[[')
        bad = txt[: i + 17] + ('"7/2"' if txt[i + 17:].startswith('"') else "7") + txt[i + 17 + (txt[i + 17:].find(",") if True else 0):] if i >= 0 else txt
        badf = os.path.join(a.workdir, "mutation-16.jsonl"); open(badf, "w").write(bad)
        g6 = os.path.join(a.workdir, "selftest-16.g6")
        chk = subprocess.run([PY, os.path.join(HERE, "check", "udcheck.py"), "--allow-any-size", "--graphs", g6,
                              "--unknown-file", os.path.join(a.workdir, "selftest-16.UNKNOWN.g6"), badf], capture_output=True, text=True)
        rejected = chk.returncode != 0 or not any(l.startswith("ACCEPT") for l in chk.stdout.splitlines())
        print(("FAIL (as required) " if rejected else "BUG: corrupted certificate accepted ") + "corrupted coordinate in the n=16 certificate: " + ((chk.stdout + chk.stderr).strip().splitlines() or ["?"])[-1][:120])
        ok_all &= rejected
        print("SELF-TEST", "PASS" if ok_all else "FAIL"); sys.exit(0 if ok_all else 1)
    ok_all = True; any_cell = False
    for n in (a.n or sorted(U)):
        surv = find_survivors(a.survivors_dir, n)
        if surv is None:
            print(f"n={n}: no survivors file under {a.survivors_dir}"); ok_all = False; continue
        any_cell = True
        ok, line, det = run_gate(n, surv, known.get(n, set()), a.tries, a.max_states, a.workdir, "gate")
        print(("OK   " if ok else "FAIL ") + line); ok_all &= ok
        report["cells"][n] = {"ok": ok, "line": line, **{k: v for k, v in det.items() if k != "certs"}, "certs": det.get("certs")}
    if a.report: json.dump(report, open(a.report, "w"), indent=1)
    print("GATE G3:", "PASS" if (ok_all and any_cell) else "FAIL"); sys.exit(0 if (ok_all and any_cell) else 1)

if __name__ == "__main__":
    main()
