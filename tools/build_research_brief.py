#!/usr/bin/env python3
"""Build a four-page, linked research brief from local research artifacts.

Requires the sibling project checkouts, installed Node/Playwright Chromium,
pdfinfo and pdftotext. No network or model calls. --check verifies the current
inputs, content, HTML/PDF hashes and print checks without rewriting anything.
Content is reproducible with --generated-at; PDF metadata need not be identical.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "ehs": ("ehs-osha-analysis", "docs/decision-audit-data.json"),
    "ai": ("ehs-ai-grounding-eval", "results/answerability.json"),
    "sem": ("ehs-risk-sem", "docs/model-audit-data.json"),
    "ontology": (
        "ehs-human-factors-ontology",
        "docs/skos/translation-loss-report.json",
    ),
}
AUDITS = {
    "ehs": "https://ehs-osha-analysis.vercel.app/decision-audit.html",
    "ai": "https://ehs-ai-grounding-eval.vercel.app/evidence-audit.html",
    "sem": "https://ehs-risk-sem.vercel.app/model-audit.html",
    "ontology": "https://ehs-human-factors-ontology.vercel.app/translation-audit.html",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_content(workspace):
    raw, sources = {}, {}
    for key, (repo, relative) in FILES.items():
        path = workspace / repo / relative
        raw[key] = json.loads(path.read_text())
        sources[key] = {
            "repository": repo,
            "path": relative,
            "sha256": digest(path),
            "url": f"https://github.com/priyatham9/{repo}/blob/main/{relative}",
        }
    ehs = raw["ehs"]
    candidates = [
        row
        for row in ehs["influence_audit"]["review_candidates"]
        if row["year_before"] == 2023 and row["year_after"] == 2024
    ]
    candidate = max(candidates, key=lambda row: row["hours"])
    fragility = next(
        row
        for row in ehs["influence_audit"]["decision_fragility"]
        if row["year_before"] == 2023
    )
    ai = raw["ai"]
    bm25 = next(row for row in ai["baselines"] if row["adapter"] == "retrieval_bm25")
    counterexample = next(
        row
        for row in ai["score_validity_examples"]
        if row["question_id"] == "hc-005" and row["excerpt_id"] == "hn-001"
    )
    if not counterexample["diagnostics"]["passes"]:
        raise ValueError("Selected lexical counterexample no longer passes")
    sem = raw["sem"]
    if not sem["simulation_only"] or not sem["main"]["complete"]:
        raise ValueError("The primary simulation must be complete and labeled")
    rows = {
        row["stage"]: row
        for row in sem["main"]["rows"]
        if row["pair"] == "positive" and row["loading"] == 0.75 and row["n"] == 770
    }
    if set(rows) != {"null_validation", "alternative"}:
        raise ValueError("Missing independently evaluated simulation stages")
    ontology = raw["ontology"]
    return {
        "sources": sources,
        "ehs": {
            "candidate": candidate,
            "fragility": fragility,
            "n_comparisons": len(ehs["influence_audit"]["decision_fragility"]),
            "other_comparisons_without_single_reversal": sum(
                row["n_single_filing_reversals"] == 0
                for row in ehs["influence_audit"]["decision_fragility"]
            ),
            "definition": ehs["definitions"]["population"],
            "rule": ehs["influence_audit"]["rule"],
        },
        "ai": {
            "n": ai["answer_space"]["n_factual"],
            "n_excerpts": ai["answer_space"]["n_indexed_excerpts"],
            "n_combinations": ai["answer_space"]["n_combinations_per_format"],
            "attainable": ai["answer_space"]["n_attainable_wrapped"],
            "own_passes": ai["answer_space"]["n_own_wrapped_pass"],
            "bare_attainable": ai["answer_space"]["n_attainable_bare"],
            "passes": bm25["n_pass"],
            "recoverable": bm25["n_recoverable_by_reranking"],
            "unreachable": bm25["n_no_excerpt_passes"],
            "pairs": bm25["pairs"],
            "pair_ceiling": ai["answer_space"]["pair_ceiling"],
            "counterexample": counterexample,
            "counterexample_question": next(
                row["question"]
                for row in ai["answer_space"]["items"]
                if row["item_id"] == "hc-005"
            ),
            "counterexample_anchor": next(
                row["anchor_text"]
                for row in ai["excerpts"]
                if row["item_id"] == "hn-001"
            ),
        },
        "sem": {
            "rows": rows,
            "scope": sem["interpretation"]["scope"],
            "calibrated_interpretation": sem["interpretation"]["calibrated"],
            "reps_per_stage_cell": sem["main"]["manifest"]["reps_per_stage_cell"],
        },
        "ontology": {
            "counts": ontology["counts"],
            "ledger": ontology["lossLedger"],
            "round_trip": ontology["roundTrip"],
            "source": ontology["source"],
        },
    }


CSS = """
@page{size:A4;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;color:#18362b;background:#dde3d9;font-family:'Liberation Sans',Arial,sans-serif}body{font-size:9.4pt;line-height:1.43;-webkit-print-color-adjust:exact;print-color-adjust:exact}.sheet{width:210mm;height:297mm;padding:14mm 17mm 12mm;background:#fbfcf7;margin:8mm auto;display:flex;flex-direction:column;break-after:page;page-break-after:always;position:relative}.sheet:last-child{break-after:auto;page-break-after:auto}.masthead{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #a9bba9;padding-bottom:3mm;font-size:7.4pt;letter-spacing:.13em;text-transform:uppercase}.brand{font-family:'Liberation Serif',Georgia,serif;font-size:19pt;letter-spacing:-.03em;text-transform:none;font-weight:bold}.masthead span:last-child{font-size:7pt;color:#526659}.program-title{font-family:'Liberation Serif',Georgia,serif;font-size:29pt;font-weight:normal;line-height:1.03;letter-spacing:-.035em;margin:6mm 0 2.5mm}.byline{font-size:7.8pt;color:#4b6253;margin:0 0 3mm}.intro{font-size:8.8pt;margin:0 0 5mm;max-width:166mm;color:#435d4c}.running-title{font-size:8.8pt;color:#4a6152;margin:4mm 0 4mm}.eyebrow{font-size:7.3pt;letter-spacing:.12em;text-transform:uppercase;font-weight:bold;color:#426450;margin:0 0 2mm}.finding-title{font-family:'Liberation Serif',Georgia,serif;font-size:28pt;line-height:1.05;font-weight:normal;letter-spacing:-.025em;margin:0 0 4mm;max-width:168mm}.first .finding-title{font-size:22pt}.finding{font-size:11.1pt;line-height:1.42;margin:0 0 4mm}.first .finding{font-size:10pt}.evidence{background:#e9efdf;border-top:2px solid #2c694c;padding:3mm 5mm;margin:1mm 0 3mm}.evidence h3{font-size:9.2pt;font-weight:bold;margin:0 0 1mm}.caption{font-size:7.6pt;color:#4e6354;margin:0 0 3mm}.evidence svg{display:block;width:100%;height:auto}.axis{stroke:#aebea8;stroke-width:1}.grid{stroke:#c7d2bf;stroke-width:1}.svg-label{font-family:'Liberation Sans',Arial,sans-serif;font-size:13px;fill:#304e3c}.svg-value{font-family:'Liberation Sans',Arial,sans-serif;font-weight:bold;font-size:15px;fill:#183d2b}.svg-note{font-family:'Liberation Sans',Arial,sans-serif;font-size:11px;fill:#526b56}table{width:100%;border-collapse:collapse;font-size:8.1pt;margin:1mm 0 2mm}caption{text-align:left;color:#4c6352;font-size:7.5pt;margin-bottom:2mm}th,td{text-align:left;border-bottom:1px solid #bdcbb7;padding:1.6mm 2mm;vertical-align:top}th:first-child,td:first-child{padding-left:0}thead th{font-size:7pt;text-transform:uppercase;letter-spacing:.03em;color:#47614e;border-top:1px solid #bdcbb7}tbody th{font-weight:normal}small{font-size:7pt;color:#4d6352}p{margin:0 0 3mm}h3{font-size:10.3pt;margin:0 0 2mm}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:7mm;margin:3mm 0 4mm}.two-col p{font-size:9.3pt;line-height:1.45;margin:0}.limit{border-left:2px solid #aa8350;padding:2mm 0 2mm 4mm;font-size:8.5pt;color:#4b5d4d;margin:0 0 4mm}.limit strong{color:#334d3a}.witness{border:1px solid #b7c8b0;padding:3mm 5mm;margin:1mm 0 3mm;background:#f5f7ee}.witness h3{font-size:9.2pt}.witness p{font-size:8.7pt;margin:0 0 2mm}.witness p:last-child{margin:0}.mono{font-family:'Liberation Mono',monospace;font-size:8pt}a{color:#175a3c;text-decoration:underline;text-underline-offset:2px}.source{margin-top:auto;padding-top:3mm;border-top:1px solid #a9bba9;font-size:7.3pt;line-height:1.45}.source-top{display:flex;justify-content:space-between;gap:8mm;margin-bottom:2mm}.source-top a{font-weight:bold;font-size:8.4pt}.source .hash{font-family:'Liberation Mono',monospace;font-size:6.6pt}.foot{display:flex;justify-content:space-between;margin-top:3mm;font-size:6.9pt;color:#546957}.retained{background:#d7e6cf}.lost{background:#eedecd}.closing{background:#204c37;color:#fff;padding:4mm 5mm;margin:0 0 4mm;font-size:9pt}.closing strong{display:block;margin-bottom:1.5mm}.closing span{color:#e2eddd}.first .evidence{padding:3mm 5mm;margin-bottom:2mm}.first table{font-size:7.8pt}.first .two-col{margin:1mm 0 2mm;gap:6mm}.first .two-col p{font-size:8.8pt}.first .limit{font-size:8.1pt;margin-bottom:2mm}.screen-note{max-width:176mm;margin:6mm auto;font-size:12px;color:#294e39}.screen-note a{margin-right:18px}@media print{body{background:#fff}.sheet{margin:0}.screen-note{display:none}a{color:inherit}}@media screen and (max-width:820px){.sheet{width:100%;height:auto;min-height:297mm;margin:0 auto 8mm;padding:10mm 7mm}.screen-note{margin:5mm 7mm}.program-title{font-size:27pt}.finding-title{font-size:25pt}.source{margin-top:6mm}}"""


def pct(value, digits=1, signed=False):
    return format(100 * value, ("+" if signed else "") + "." + str(digits) + "f") + "%"


def e(text):
    return html.escape(str(text))


def footer(key, page, content, timestamp):
    source = content["sources"][key]
    return f'''<div class="source"><div class="source-top"><a href="{AUDITS[key]}">Explore the interactive audit →</a><a href="{source["url"]}">Inspect the source artifact →</a></div>
      <div>Artifact: <span class="hash">{e(source["repository"] + "/" + source["path"])}</span><br>SHA-256: <span class="hash">{source["sha256"]}</span></div>
      <div class="foot"><span>Priyatham Chimmani · Independent research<br>Working findings · Not peer reviewed</span><span>Generated {e(timestamp)}<br>{page} / 4 · <a href="https://grounded-chi-five.vercel.app/research-brief-manifest.json">Content &amp; build manifest</a></span></div></div>'''


def header(page, first=False):
    return f"""<section class="sheet{" first" if first else ""}" aria-label="Research brief page {page}"><header class="masthead"><span class="brand">Grounded</span><span>Research brief / {page:02d}</span></header>"""


def trend_svg(before, after):
    # Shared zero and scale: -5 to +20 percentage points of relative rate change.
    def x(value):
        return 238 + (value + 5) / 25 * 335

    zero = x(0)
    rows = []
    for label, value, y, color in (
        ("Screened population", before, 29, "#94533d"),
        ("Without one review candidate", after, 69, "#296849"),
    ):
        left, right = sorted((zero, x(value)))
        rows.append(
            f'<text x="0" y="{y + 5}" class="svg-label">{label}</text><rect x="{left:.2f}" y="{y - 10}" width="{right - left:.2f}" height="20" fill="{color}"/><text x="620" y="{y + 5}" text-anchor="end" class="svg-value">{value:+.2f}%</text>'
        )
    return f'''<svg viewBox="0 0 625 103" role="img" aria-label="Change in rate: {before:+.2f}% originally, {after:+.2f}% after one-record sensitivity"><line x1="{zero}" x2="{zero}" y1="9" y2="82" class="axis"/>{"".join(rows)}<text x="{zero}" y="100" text-anchor="middle" class="svg-note">0%</text><text x="573" y="100" text-anchor="middle" class="svg-note">+20%</text></svg>'''


def partition_svg(ai):
    x = 0
    pieces = []
    for key, color, ink in (
        ("passes", "#286849", "white"),
        ("recoverable", "#cbab5d", "#203823"),
        ("unreachable", "#c9d4bf", "#203823"),
    ):
        width = ai[key] / ai["n"] * 625
        pieces.append(
            f'<rect x="{x:.5f}" y="3" width="{width:.5f}" height="48" fill="{color}"/><text x="{x + width / 2:.5f}" y="34" text-anchor="middle" font-family="Liberation Serif,serif" font-size="26" fill="{ink}">{ai[key]}</text>'
        )
        x += width
    return (
        '<svg viewBox="0 0 625 58" role="img" aria-label="BM25 outcome partition: current passes, recoverable misses, no passing excerpt">'
        + "".join(pieces)
        + "</svg>"
    )


def rejection_svg(null):
    rows = []
    for label, key, y, color in (
        ("Naïve test", "observed_naive_rejection_rate", 29, "#94533d"),
        (
            "Null-calibrated diagnostic",
            "observed_calibrated_rejection_rate",
            72,
            "#296849",
        ),
    ):
        width = null[key] / 0.25 * 335
        rows.append(
            f'<text x="0" y="{y + 5}" class="svg-label">{label}</text><rect x="238" y="{y - 10}" width="335" height="20" fill="#d5dfca"/><rect x="238" y="{y - 10}" width="{width:.3f}" height="20" fill="{color}"/><text x="620" y="{y + 5}" text-anchor="end" class="svg-value">{pct(null[key])}</text>'
        )
    return (
        '<svg viewBox="0 0 625 108" role="img" aria-label="False positive rates on independent null simulations">'
        + "".join(rows)
        + '<line x1="305" x2="305" y1="5" y2="88" stroke="#597153" stroke-dasharray="3 3"/><text x="305" y="105" text-anchor="middle" class="svg-note">5% nominal</text><text x="573" y="105" text-anchor="middle" class="svg-note">25%</text></svg>'
    )


def render(content, timestamp):
    date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%d %B %Y")
    c, frag = content["ehs"]["candidate"], content["ehs"]["fragility"]
    first = (
        header(1, True)
        + f"""
      <h1 class="program-title">Audit the measurement<br>before optimizing the decision.</h1>
      <p class="byline">Priyatham Chimmani · Independent research · {e(date)}</p>
      <p class="intro">Four investigations examine what a reassuring check leaves out. Empirical records, an exhaustive scorer diagnostic, controlled simulation and a representation test provide different evidence. They are not pooled into a universal failure rate.</p>
      <p class="eyebrow">01 / Empirical influence audit · OSHA administrative filings</p>
      <h2 class="finding-title">One screened record can reverse a trend.</h2>
      <p class="finding">The default-screened 2023–24 injury-rate change is <strong>{c["original_change_pct"]:+.2f}%</strong>. Omitting one influential 2023 filing changes it to <strong>{c["review_change_pct"]:+.2f}%</strong>. This is a review sensitivity, not a corrected estimate.</p>
      <figure class="evidence"><h3>Direction depends on the influential denominator</h3><p class="caption">Same 2024 endpoint; one 2023 filing omitted only in the sensitivity.</p>{trend_svg(c["original_change_pct"], c["review_change_pct"])}</figure>
      <table><caption>TRIR = 200,000 × recordable cases / reported hours. Rates rounded to four decimals.</caption><thead><tr><th>Scenario</th><th>2023 rate</th><th>2024 rate</th><th>Change</th></tr></thead><tbody><tr><th>Default-screened population</th><td>{c["original_rate_before"]:.4f}</td><td>{c["original_rate_after"]:.4f}</td><td>{c["original_change_pct"]:+.2f}%</td></tr><tr><th>Without filing {c["filing_id"]}</th><td>{c["review_rate_before"]:.4f}</td><td>{c["review_rate_after"]:.4f}</td><td>{c["review_change_pct"]:+.2f}%</td></tr></tbody></table>
      <p class="caption">All {frag["n_filings_tested"]:,} individual deletions across both years were tested; {frag["n_single_filing_reversals"]} reverses the sign. The other {content["ehs"]["other_comparisons_without_single_reversal"]} adjacent-year comparisons have no single-deletion reversal. The candidate reports {c["hours"] / 1e9:.2f} billion hours and {c["cases"]} cases.</p>
      <div class="two-col"><div><h3>What the check misses</h3><p>Scaling hours and employees together preserves hours per employee while changing the injury rate. Internal ratio consistency cannot establish absolute-scale validity.</p></div><div><h3>Practical review step</h3><p>Apply the same leave-one-out influence rule to both years. Inspect flagged source records and retain them pending review; do not automatically delete them.</p></div></div>
      <p class="limit"><strong>Limits.</strong> Retrospective analysis of administrative filings, not a probability sample or causal study. Influence does not identify an erroneous field or recover its true value. The rule was not historically preregistered.</p>
      {footer("ehs", 1, content, timestamp)}</section>"""
    )
    ai = content["ai"]
    second = (
        header(2)
        + f"""
      <p class="running-title">Audit the measurement before optimizing the decision.</p>
      <p class="eyebrow">02 / Exhaustive scorer diagnostic · No language model evaluated</p>
      <h2 class="finding-title">Audit the answer space<br>before changing the retriever.</h2>
      <p class="finding">Testing every indexed excerpt against every factual question—<strong>{ai["n_combinations"]:,} combinations</strong>—finds any scorer-passing response for only <strong>{ai["attainable"]}/{ai["n"]} questions</strong>. BM25 already passes {ai["passes"]}.</p>
      <figure class="evidence"><h3>Decomposing BM25’s {ai["n"]} factual outcomes</h3>{partition_svg(ai)}<p class="caption">{ai["passes"]} current passes · {ai["recoverable"]} misses with a passing excerpt available · {ai["unreachable"]} with no passing indexed excerpt.</p></figure>
      <table><caption>Same {ai["n_excerpts"]} indexed excerpts and unchanged lexical rubric; factual questions only.</caption><thead><tr><th>Selection / response format</th><th>Scorer passes</th><th>What it tests</th></tr></thead><tbody><tr><th>BM25 top-ranked excerpt</th><td>{ai["passes"]} / {ai["n"]}</td><td>Current retrieval baseline</td></tr><tr><th>Question’s designated source</th><td>{ai["own_passes"]} / {ai["n"]}</td><td>Source-selection intervention</td></tr><tr><th>Any wrapped indexed excerpt</th><td>{ai["attainable"]} / {ai["n"]}</td><td>Exhaustive fixed-format ceiling</td></tr><tr><th>Any bare indexed excerpt</th><td>{ai["bare_attainable"]} / {ai["n"]}</td><td>Format sensitivity without metadata</td></tr></tbody></table>
      <div class="witness"><h3>A pass worth disputing: the number has the wrong referent</h3><p><strong>Question:</strong> {e(ai["counterexample_question"])}</p><p><strong>Unrelated source excerpt:</strong> “{e(ai["counterexample_anchor"])}”</p><p>The numeric-only key accepts this unrelated noise-exposure excerpt. A lexical pass is not semantic validation; this is not a language-model response.</p></div>
      <div class="two-col"><div><h3>What the score mixes</h3><p>Score differences mix retrieval, the response format and lexical matching. None isolates system capability.</p></div><div><h3>Practical review step</h3><p>Measure what the available evidence can make the scorer accept, then audit accepted answers for meaning before attributing a score gap to system capability.</p></div></div>
      <p class="limit"><strong>Limits.</strong> The ceiling is conditional on this corpus, format and rubric; it does not bound semantic answerability or synthesis. No language model was evaluated. Metadata can supply legitimate answer content.</p>
      {footer("ai", 2, content, timestamp)}</section>"""
    )
    null, alt = (
        content["sem"]["rows"]["null_validation"],
        content["sem"]["rows"]["alternative"],
    )
    method_rows = []
    for label, prefix in (
        ("Naïve analytic test", "observed_naive"),
        ("Null-calibrated diagnostic", "observed_calibrated"),
        ("Oracle: latent scores observed", "oracle"),
    ):
        method_rows.append(
            f"<tr><th>{label}</th><td>{int(null[prefix + '_rejection_rate_count'])}/{null['attempts']} ({pct(null[prefix + '_rejection_rate'])})</td><td>{int(alt[prefix + '_rejection_rate_count'])}/{alt['attempts']} ({pct(alt[prefix + '_rejection_rate'])})</td></tr>"
        )
    third = (
        header(3)
        + f"""
      <p class="running-title">Audit the measurement before optimizing the decision.</p>
      <p class="eyebrow">03 / Controlled simulation · Known generating model</p>
      <h2 class="finding-title">Good model fit does not<br>calibrate a contrast test.</h2>
      <p class="finding">At N={null["n"]} and loading {null["loading"]:.2f}, <strong>{null["fit_good_rate_count"]}/{null["attempts"]} null simulations pass the fit criteria</strong>. The repository’s two-step estimator with its naïve analytic standard error still rejects a true null in <strong>{pct(null["observed_naive_rejection_rate"])}</strong> of simulations.</p>
      <figure class="evidence"><h3>False positives on independent null simulations</h3><p class="caption">Shared 0–25% scale. Nominal significance level: 5%.</p>{rejection_svg(null)}</figure>
      <table><caption>Independent sets of {null["attempts"]:,} surveys per stage. Alternative contrast Δ={alt["true_difference"]:.2f}.</caption><thead><tr><th>Procedure</th><th>Null rejection (Δ=0)</th><th>Alternative rejection</th></tr></thead><tbody>{"".join(method_rows)}</tbody></table>
      <p class="caption">The naïve null rate has pointwise 95% Wilson interval {pct(null["observed_naive_rejection_rate_low"])}–{pct(null["observed_naive_rejection_rate_high"])}. The calibrated alternative rate has 95% two-sample Monte Carlo interval {pct(alt["calibrated_two_sample_bootstrap_low"])}–{pct(alt["calibrated_two_sample_bootstrap_high"])}, including cutoff uncertainty. High alternative rejection is not useful power evidence before false positives are checked.</p>
      <div class="two-col"><div><h3>What the fit check misses</h3><p>The naïve uncertainty calculation treats estimated latent correlations as fixed. Fit criteria—CFI ≥ .95, RMSEA ≤ .06, SRMR ≤ .08—test a different property from contrast-test calibration.</p></div><div><h3>Practical review step</h3><p>Evaluate the contrast procedure on separate null and alternative samples. Keep measurement estimation in the uncertainty calculation; do not use fit alone to justify effect rankings.</p></div></div>
      <p class="limit"><strong>Limits.</strong> Five normal latent variables, four correlated predictors (ρ=.35), three indicators per factor and independent errors; no missingness or workplace observations. Error rates are estimator-specific. The null-calibrated cutoff knows the data-generating process and is a diagnostic, not a real-data remedy. Only the completed primary experiment is summarized here.</p>
      {footer("sem", 3, content, timestamp)}</section>"""
    )
    ontology = content["ontology"]
    ledger = {row["feature"]: row for row in ontology["ledger"]}
    names = [
        "PIF mapping expressions",
        "Original alignment resource identities",
        "Explicit no-counterpart assertions",
        "Explicit external coverage-gap records",
    ]
    ledger_rows = "".join(
        f'<tr><th>{e(name)}</th><td>{ledger[name]["source"]}</td><td class="'
        + ("retained" if ledger[name]["source"] == ledger[name]["skos"] else "lost")
        + f'">{ledger[name]["skos"]}</td><td>{ledger[name]["sidecar"]}</td></tr>'
        for name in names
    )
    count, trip = ontology["counts"], ontology["round_trip"]
    fourth = (
        header(4)
        + f"""
      <p class="running-title">Audit the measurement before optimizing the decision.</p>
      <p class="eyebrow">04 / Representation-loss audit · Author-proposed crosswalk</p>
      <h2 class="finding-title">A complete mapping count<br>can miss explicit absences.</h2>
      <p class="finding">The standard SKOS export retains <strong>{count["uniquePifSkosMappings"]}/{count["pifAlignments"]} PIF mapping expressions</strong>, but omits all <strong>{count["explicitAbsences"]} explicit no-counterpart assertions</strong> and all <strong>{count["coverageGapRecords"]} coverage-gap records</strong>.</p>
      <figure class="evidence"><h3>Preservation depends on what is counted</h3><table><caption>These overlapping feature counts are not additive; dimension mappings are separate.</caption><thead><tr><th>Recorded feature</th><th>Source</th><th>SKOS</th><th>With sidecar</th></tr></thead><tbody>{ledger_rows}</tbody></table></figure>
      <div class="witness"><h3>Two source states, one identical export</h3><p class="mono">WorkplaceVisibility → noCounterpartIn → SPAR-H</p><p>The source can assert no counterpart or say nothing. Deleting this absence changes the source but leaves its standard SKOS export byte-identical.</p></div>
      <div class="two-col"><div><h3>What a scoped repair proves</h3><p>A separate RDF sidecar recovers {trip["recoveredTriples"]}/{trip["contractTriples"]} source triples in the declared crosswalk-record contract: {trip["missing"]} missing and {trip["added"]} added. The standard SKOS graph remains unchanged.</p></div><div><h3>Practical review step</h3><p>Declare which assertions, explicit absences and provenance must survive an interchange. Test their reconstruction; do not use edge counts as the fidelity criterion.</p></div></div>
      <p class="limit"><strong>Limits.</strong> A lossless scoped round trip does not reconstruct the entire ontology or validate the proposed alignments. It establishes no new taxonomy, causal relationship or prediction of injury risk.</p>
      <div class="closing"><strong>A common review discipline, not a pooled empirical claim.</strong><span>Name the quantity. Challenge what the summary cannot test. Trace the evidence. Record what remains unknown.</span></div>
      {footer("ontology", 4, content, timestamp)}</section>"""
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="author" content="Priyatham Chimmani"><meta name="description" content="Four reproducible working findings on measurement and decision review."><title>Audit the measurement before optimizing the decision — Priyatham Chimmani</title><style>{CSS}</style></head><body><nav class="screen-note" aria-label="Brief navigation"><a href="research-brief.pdf" download>Download four-page PDF</a><a href="investigations.html">Explore the interactive investigations</a><a href="research-brief-manifest.json">Content &amp; build manifest</a></nav><main>{first}{second}{third}{fourth}</main></body></html>"""


NODE_RENDER = r"""
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1000,height:1200}});
 await page.goto('file://'+process.argv[1]);await page.emulateMedia({media:'print'});
 await page.evaluate(()=>document.fonts.ready);
 const sheets=await page.locator('.sheet').evaluateAll(nodes=>nodes.map((node,i)=>{
   const rect=node.getBoundingClientRect(),footer=node.querySelector('.source').getBoundingClientRect();
   return {page:i+1,overflow:node.scrollHeight-node.clientHeight,widthOverflow:node.scrollWidth-node.clientWidth,
           footerBottom:footer.bottom-rect.top,pageHeight:rect.height};
 }));
 if(sheets.length!==4||sheets.some(x=>x.overflow>1||x.widthOverflow>1||x.footerBottom>x.pageHeight-20))
   throw new Error('Print layout overflow: '+JSON.stringify(sheets));
 await page.pdf({path:process.argv[2],printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,tagged:true});
 console.log(JSON.stringify({browser:await browser.version(),layout:sheets}));await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
"""


def verify_pdf(path):
    info = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True
    ).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE).group(1))
    if pages != 4:
        raise ValueError(f"Expected four pages, got {pages}")
    text = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    extracted = [page for page in text.split("\f") if page.strip()]
    if len(extracted) != 4 or any(
        "Priyatham Chimmani" not in page for page in extracted
    ):
        raise ValueError("Missing selectable text or per-page attribution")
    links = subprocess.run(
        ["pdfinfo", "-url", str(path)], check=True, capture_output=True, text=True
    ).stdout
    if any(url not in links for url in AUDITS.values()):
        raise ValueError("Missing interactive audit PDF link")
    bbox = subprocess.run(
        ["pdftotext", "-bbox", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    root = ET.fromstring(bbox)
    violations = []
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    word_counts = []
    for index, page in enumerate(root.findall(".//x:page", ns), 1):
        width, height = float(page.attrib["width"]), float(page.attrib["height"])
        words = page.findall(".//x:word", ns)
        word_counts.append(len(words))
        for word in words:
            if (
                float(word.attrib["xMin"]) < 25
                or float(word.attrib["xMax"]) > width - 25
                or float(word.attrib["yMin"]) < 20
                or float(word.attrib["yMax"]) > height - 20
            ):
                violations.append((index, word.text))
    if violations:
        raise ValueError("Text crosses safe print margins: " + repr(violations[:8]))
    if len(word_counts) != 4 or min(word_counts) < 150:
        raise ValueError("Unexpectedly empty page")
    return {
        "pages": pages,
        "selectable_text": True,
        "audit_links": len(AUDITS),
        "words_per_page": word_counts,
        "safe_margin_violations": len(violations),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    parser.add_argument(
        "--generated-at", help="ISO-8601 UTC timestamp for reproducible content"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    html_path, pdf_path, manifest_path = [
        ROOT / "docs" / name
        for name in (
            "research-brief.html",
            "research-brief.pdf",
            "research-brief-manifest.json",
        )
    ]
    content = load_content(args.workspace)
    if args.check:
        manifest = json.loads(manifest_path.read_text())
        if (
            content != manifest["content"]
            or digest(Path(__file__)) != manifest["generator_sha256"]
        ):
            raise SystemExit(
                "Research brief source inputs or generator changed; regenerate after inputs settle"
            )
        expected_html = render(content, manifest["generated_at"])
        if html_path.read_text() != expected_html:
            raise SystemExit("Research brief HTML is stale")
        if (
            digest(html_path) != manifest["html_sha256"]
            or digest(pdf_path) != manifest["pdf_sha256"]
        ):
            raise SystemExit("Research brief output hash mismatch")
        verification = verify_pdf(pdf_path)
        if verification != manifest["verification"]:
            raise SystemExit("Research brief PDF checks changed")
        print(
            "Research brief inputs, outputs, four-page text layout and links verified"
        )
        return
    timestamp = args.generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    if (
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        .utcoffset()
        .total_seconds()
        != 0
    ):
        raise ValueError("Generation timestamp must be UTC")
    html_path.write_text(render(content, timestamp))
    result = subprocess.run(
        ["node", "-e", NODE_RENDER, str(html_path), str(pdf_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(result.stderr.strip())
    rendering = json.loads(result.stdout)
    verification = verify_pdf(pdf_path)
    manifest = {
        "schema": "grounded-research-brief-v1",
        "generated_at": timestamp,
        "generator_sha256": digest(Path(__file__)),
        "content": content,
        "rendering": {"engine": "Playwright / Chromium", **rendering},
        "verification": verification,
        "html_sha256": digest(html_path),
        "pdf_sha256": digest(pdf_path),
        "reproducibility": "Selected source values and HTML content are reproducible with the recorded timestamp. PDF generation metadata may change; PDF byte identity across renders is not claimed.",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(
        f"Research brief generated: {verification['pages']} pages, {pdf_path.stat().st_size:,} bytes"
    )


if __name__ == "__main__":
    main()
