#!/usr/bin/env python3
"""Validate the completed VM outputs and write a compact JSON summary.

Adapted from GP-10 write_independent_checks.py's refusal to report unfinished
or failed work. All counts are read from artifacts, never typed result counts.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from independent_core import digest, lines, loads, require, write_json


def summarize(root):
    root = Path(root)
    read = lambda p: loads((root / p).read_bytes())
    audit, red = read("audit/report.json"), read("redteam/redteam.json")
    modp, embed = read("modp.json"), read("embed.json")
    require(audit["status"] == "PASS" and audit["scope"] == "B11" and audit["derived_list_valid"]
            and set(audit["stages"]) >= set("1234") and not audit["alarms"],
            "summary_audit", "full independent audit did not pass every stage")
    require(audit.get("equals_comparison_counts") and audit["minimality"].get("equals_comparison_L11"),
            "summary_comparison", "checker count/list comparisons are missing or failed")
    require(red["status"] == "PASS" and red["green_before"] == red["green_after"] == "PASS"
            and red["all_controls_behaved"] and len(red["controls"]) >= 8,
            "summary_redteam", "paired audit red controls did not all behave")
    require(modp["status"] == "PASS" and modp["all_red"] and modp["controls_status"] == "PASS"
            and modp["shard"] == "0/1" and not modp["failures"]
            and modp["selected_records"] == modp["scanned_records"] == audit["input"]["records"]
            and modp["consumed_sha256"] == audit["input"]["records_sha256"],
            "summary_modp", "full identity coverage or red controls are missing")
    require(embed["status"] == "NO_COUNTEREXAMPLE_FOUND" and embed["shard"] == "0/1"
            and embed["controls_all_found"] and not embed["member_hits"],
            "summary_embed", "numerical members/controls did not finish successfully")
    require(embed["input_hashes"]["records"] == audit["input"]["records_sha256"]
            and embed["input_hashes"]["B11"] == audit["input"]["B11_sha256"]
            and embed["input_hashes"]["L11"] == digest(root / "audit/L11.g6"),
            "summary_embed_inputs", "numerical search used different input bytes")
    statuses = {}
    with (root / "audit/verdicts.tsv").open() as f:
        require(f.readline() == "g6\tverdict\ttype\n", "summary_statuses", "wrong status stream header")
        for line in f:
            g, verdict, typ = line.rstrip("\n").split("\t")
            require(g not in statuses, "summary_statuses", "duplicate status graph")
            statuses[g] = verdict
    refuted = {g for g, verdict in statuses.items() if verdict == "refuted"}
    checked = []
    for _, raw in lines(root / "modp.jsonl"):
        row = loads(raw)
        require(row["status"] == "PASS", "summary_identities", "identity detail contains a failure")
        checked.append(row["g6"])
    require(len(checked) == len(set(checked)) and set(checked) == refuted,
            "summary_identities", "identity details do not cover every refuted record exactly once")
    minimal = [raw[:-1].decode("ascii") for _, raw in lines(root / "audit/L11.g6")]
    searched = [row["g6"] for row in embed["rows"]]
    require(len(searched) == len(set(searched)) and set(searched) == set(minimal)
            and len(minimal) == audit["minimality"]["L11"],
            "summary_search", "numeric search does not cover every independent L11 member exactly once")
    artifacts = ["audit/report.json", "audit/L11.g6", "audit/minimality.jsonl", "audit/verdicts.tsv",
                 "redteam/redteam.json", "modp.json", "modp.jsonl", "embed.json", "embed.jsonl"]
    rep = {"status": "PASS", "scope": "independent checks 1,2,3,6 after B11 result",
           "counts": audit["input"]["counts"], "L11": len(minimal),
           "refuted_records_with_identity_coverage": len(checked), "identities_per_point": modp["identities_per_point"],
           "audit_red_controls": len(red["controls"]), "modp_red_controls": len(modp["red_controls"]),
           "numerical_controls_minus_edge": embed["controls_minus_edge_found"],
           "numerical_controls_embedded_B11": embed["controls_embedded_B11_found"],
           "predictions": audit.get("predictions"), "source_hashes": {"audit": audit["source_hashes"],
               "modp": modp["source_hashes"], "embed": embed["source_hashes"]},
           "artifacts": {name: digest(root / name) for name in artifacts},
           "classification_authorized": False, "numerical_search_is_not_a_proof": True}
    write_json(root / "summary.json", rep)
    print(json.dumps({k: rep[k] for k in ("status", "counts", "L11", "identities_per_point")}), flush=True)
    return rep


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("rundir")
    a = p.parse_args()
    try:
        summarize(a.rundir)
    except (ValueError, OSError, KeyError) as exc:
        print(f"REFUSE SUMMARY: {exc}", file=sys.stderr)
        sys.exit(1)
