"""Summarise a checked GP-10 run from the checker's own output (never from producer claims).

usage: python result_summary.py CHECKED_DIR RECORDS.jsonl [--json]

Reads CHECKED_DIR/report.json and CHECKED_DIR/minimal.g6 (written by gp10check.py) and the run's records file
(streamed, only to name the certificate type behind each minimal graph). Prints the headline numbers, the minimal
graphs by edge count and by degree data, and the certificate types, as Markdown (or JSON with --json).
"""
import sys, json
from collections import Counter

checked, records_path = sys.argv[1], sys.argv[2]
report = json.load(open(checked + "/report.json"))
minimal = [l.strip() for l in open(checked + "/" + report.get("minimal_file", "minimal.g6")) if l.strip()]
assert len(minimal) == report["minimal_count"], "minimal.g6 disagrees with report.json"


def edges(g6):
    n = ord(g6[0]) - 63
    bits = []
    for ch in g6[1:]:
        v = ord(ch) - 63
        bits += [(v >> (5 - i)) & 1 for i in range(6)]
    out, k = [], 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                out.append((i, j))
            k += 1
    return n, out


want = set(minimal)
cert_type = {}
with open(records_path, "rb") as f:
    for raw in f:
        r = json.loads(raw)
        if r.get("g6") in want:
            c = r.get("cert") or {}
            cert_type[r["g6"]] = c.get("type") or ("R-null" if "cofactors" in c else "?")

by_m, by_mindeg, by_maxdeg, by_degseq = Counter(), Counter(), Counter(), Counter()
for g in minimal:
    n, es = edges(g)
    deg = [0] * n
    for i, j in es:
        deg[i] += 1; deg[j] += 1
    by_m[len(es)] += 1; by_mindeg[min(deg)] += 1; by_maxdeg[max(deg)] += 1
    by_degseq[tuple(sorted(deg, reverse=True))] += 1

out = {"status": report["status"], "profile": report["profile"], "reason": report["reason"],
       "counts": report["counts"], "minimal_count": report["minimal_count"],
       "nonminimal_count": report.get("nonminimal_count"), "direct_rejections": report.get("direct_rejections"),
       "checker_sha256": report["checker_sha256"], "kernel_sha256": report.get("kernel_sha256"),
       "input_sha256": report["input_sha256"], "elapsed_seconds": report.get("elapsed_seconds"),
       "minimal_by_edges": dict(sorted(by_m.items())), "minimal_by_min_degree": dict(sorted(by_mindeg.items())),
       "minimal_by_max_degree": dict(sorted(by_maxdeg.items())),
       "certificate_types": dict(Counter(cert_type.get(g, "not found") for g in minimal)),
       "distinct_degree_sequences": len(by_degseq)}
if "--json" in sys.argv:
    print(json.dumps(out, indent=1))
    sys.exit(0)
print(f"# GP-10 checked run: {out['status']} ({out['profile']}, {out['reason']})\n")
print(f"- graphs: {sum(out['counts'].values())} (embedded {out['counts'].get('embedded')}, refuted {out['counts'].get('refuted')}, unknown {out['counts'].get('unknown')})")
print(f"- certified minimal forbidden: **{out['minimal_count']}** (refuted but not minimal: {out['nonminimal_count']}); direct rejections: {out['direct_rejections']}")
print(f"- checker {out['checker_sha256'][:12]}, kernel {str(out['kernel_sha256'])[:12]}, input {out['input_sha256'][:12]}, {out['elapsed_seconds']:.0f} s\n")
print("| edges | minimal graphs |\n|---:|---:|")
for m, c in out["minimal_by_edges"].items():
    print(f"| {m} | {c} |")
print("\n| min degree | graphs |\n|---:|---:|")
for d, c in out["minimal_by_min_degree"].items():
    print(f"| {d} | {c} |")
print(f"\nMax degree: {out['minimal_by_max_degree']}; distinct degree sequences: {out['distinct_degree_sequences']}")
print(f"\nCertificate types behind the minimal graphs: {out['certificate_types']}")
