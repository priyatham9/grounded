#!/usr/bin/env python3
"""Curate pinned local project findings into the Grounded investigations page.

Run with sibling research checkouts present: python3 tools/build_investigations.py
The deployed page is static and needs none of those repositories at runtime.
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "ehs": ("ehs-osha-analysis", "docs/decision-audit-data.json"),
    "ai": ("ehs-ai-grounding-eval", "results/answerability.json"),
    "sem": ("ehs-risk-sem", "docs/model-audit-data.json"),
    "ontology": (
        "ehs-human-factors-ontology",
        "docs/skos/translation-loss-report.json",
    ),
}


def collect(workspace):
    inputs, provenance = {}, {}
    for key, (repo, relative) in SOURCES.items():
        path = workspace / repo / relative
        raw = path.read_bytes()
        inputs[key] = json.loads(raw)
        provenance[key] = {
            "repository": repo,
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_url": f"https://github.com/priyatham9/{repo}/blob/main/{relative}",
        }
    ehs, ai, sem, ontology = (inputs[key] for key in SOURCES)
    if not sem["simulation_only"] or not sem["main"]["complete"]:
        raise ValueError("SEM main simulation must be complete and labeled")
    sem_rows = [
        row
        for row in sem["main"]["rows"]
        if row["loading"] == 0.75 and row["multiplier"] == 1.0
    ]
    if len(sem_rows) != 4:
        raise ValueError(
            "Expected two contrasts with separate null and alternative rows"
        )
    bm25 = next(row for row in ai["baselines"] if row["adapter"] == "retrieval_bm25")
    return {
        "schema": "grounded-investigations-v1",
        "interpretation": "A research-program synthesis, not a pooled estimate or a universal empirical law.",
        "provenance": provenance,
        "ehs": {
            "evidence_type": "empirical influence audit",
            "headline": ehs["headline"],
            "definitions": ehs["definitions"],
            "limitations": ehs["limitations"],
        },
        "ai": {
            "evidence_type": "exhaustive lexical scorer diagnostic",
            "n": ai["answer_space"]["n_factual"],
            "excerpts": ai["answer_space"]["n_indexed_excerpts"],
            "combinations": ai["answer_space"]["n_combinations_per_format"],
            "attainable": ai["answer_space"]["n_attainable_wrapped"],
            "bare_attainable": ai["answer_space"]["n_attainable_bare"],
            "passes": bm25["n_pass"],
            "recoverable": bm25["n_recoverable_by_reranking"],
            "unreachable": bm25["n_no_excerpt_passes"],
            "pair_ceiling": ai["answer_space"]["pair_ceiling"],
            "limitations": ai["limitations"],
        },
        "sem": {
            "evidence_type": "simulation with known generating model",
            "rows": sem_rows,
            "interpretation": sem["interpretation"],
            "main_replicates_per_stage_cell": sem["main"]["manifest"][
                "reps_per_stage_cell"
            ],
            "main_cells": len(sem["main"]["manifest"]["cells"]),
            "main_stages": len(sem["main"]["manifest"]["stages"]),
        },
        "ontology": {
            "evidence_type": "representation-loss and scoped round-trip audit",
            "counts": ontology["counts"],
            "loss_ledger": ontology["lossLedger"],
            "round_trip": ontology["roundTrip"],
            "interpretation": ontology["interpretation"],
        },
    }


def tokens(data):
    h, ai, ont = data["ehs"]["headline"], data["ai"], data["ontology"]
    selected = {(row["pair"], row["stage"]): row for row in data["sem"]["rows"]}
    null, alternative = (
        selected["positive", "null_validation"],
        selected["positive", "alternative"],
    )
    negative = selected["negative", "null_validation"]
    values = {
        "ehs_before": f"{h['reported_2023_rate']:.4f}",
        "ehs_after": f"{h['reported_2024_rate']:.4f}",
        "ehs_excluded": f"{h['two_filing_exclusion_2023_rate']:.4f}",
        "ehs_change": f"{h['reported_2023_2024_change_pct']:+.2f}%",
        "ehs_sensitive": f"{h['two_filing_exclusion_2023_2024_change_pct']:+.2f}%",
        "ehs_symmetric": f"{h['symmetric_top_two_2023_2024_change_pct']:+.2f}%",
        "ehs_hours_share": f"{100 * h['two_filings_hours_share']:.2f}%",
        "ehs_screens": str(h["threshold_grid_cells_both_pass"]),
        "ai_passes": str(ai["passes"]),
        "ai_recoverable": str(ai["recoverable"]),
        "ai_unreachable": str(ai["unreachable"]),
        "ai_attainable": str(ai["attainable"]),
        "ai_n": str(ai["n"]),
        "ai_combinations": f"{ai['combinations']:,}",
        "ai_excerpts": str(ai["excerpts"]),
        "ai_bare": str(ai["bare_attainable"]),
        "ai_pass_width": f"{100 * ai['passes'] / ai['n']:.8f}",
        "ai_recover_width": f"{100 * ai['recoverable'] / ai['n']:.8f}",
        "ai_fail_width": f"{100 * ai['unreachable'] / ai['n']:.8f}",
        "sem_n": str(null["n"]),
        "sem_reps": str(null["attempts"]),
        "sem_fit": str(null["fit_good_rate_count"]),
        "sem_false": f"{100 * null['observed_naive_rejection_rate']:.1f}%",
        "sem_false_count": str(null["observed_naive_rejection_rate_count"]),
        "sem_cal_false": f"{100 * null['observed_calibrated_rejection_rate']:.1f}%",
        "sem_cal_false_count": str(null["observed_calibrated_rejection_rate_count"]),
        "sem_false_width": f"{400 * null['observed_naive_rejection_rate']:.4f}",
        "sem_cal_width": f"{400 * null['observed_calibrated_rejection_rate']:.4f}",
        "sem_alt": f"{100 * alternative['observed_calibrated_rejection_rate']:.1f}%",
        "sem_alt_low": f"{100 * alternative['calibrated_two_sample_bootstrap_low']:.1f}%",
        "sem_alt_high": f"{100 * alternative['calibrated_two_sample_bootstrap_high']:.1f}%",
        "sem_negative_n": str(negative["n"]),
        "sem_negative_false": f"{100 * negative['observed_naive_rejection_rate']:.1f}%",
        "sem_negative_cal": f"{100 * negative['observed_calibrated_rejection_rate']:.1f}%",
        "sem_negative_false_count": str(
            negative["observed_naive_rejection_rate_count"]
        ),
        "sem_negative_cal_count": str(
            negative["observed_calibrated_rejection_rate_count"]
        ),
        "ont_mappings": str(ont["counts"]["pifAlignments"]),
        "ont_absences": str(ont["counts"]["explicitAbsences"]),
        "ont_gaps": str(ont["counts"]["coverageGapRecords"]),
        "ont_triples": str(ont["round_trip"]["contractTriples"]),
    }
    for prefix, row in (("sem", null), ("sem_negative", negative)):
        for suffix in ("low", "high"):
            values[prefix + "_false_" + suffix] = (
                f"{100 * row['observed_naive_rejection_rate_' + suffix]:.1f}%"
            )
            values[prefix + "_cal_" + suffix] = (
                f"{100 * row['calibrated_two_sample_bootstrap_' + suffix]:.1f}%"
            )
    # Shared rate scale for the two empirical sensitivity comparisons.
    for name, key in (
        ("before", "reported_2023_rate"),
        ("after", "reported_2024_rate"),
        ("excluded", "two_filing_exclusion_2023_rate"),
    ):
        values["ehs_" + name + "_x"] = f"{80 + (h[key] - 3.0) / 1.0 * 430:.3f}"
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = collect(args.workspace)
    html = (ROOT / "tools/investigations.template.html").read_text()
    for key, value in tokens(data).items():
        html = html.replace("{{" + key + "}}", value)
    if "{{" in html:
        raise ValueError("Unexpanded template token")
    outputs = {
        ROOT / "docs/investigations.html": html,
        ROOT / "docs/investigations-data.json": json.dumps(
            data, indent=2, sort_keys=True, allow_nan=False
        )
        + "\n",
    }
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit("Stale investigations artifact: " + str(path))
        else:
            path.write_text(content)
    print("Investigations artifacts " + ("verified" if args.check else "generated"))


if __name__ == "__main__":
    main()
