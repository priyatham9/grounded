#!/usr/bin/env python3
"""Collect a programme status feed by running each repo's test suite and
reading its committed artifacts. Writes repos/grounded/docs/status.json.

Standard library only. Python 3.9. Run from the Research root:
    python3 tools/build_status.py
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
OUT = REPOS / "grounded" / "docs" / "status.json"

REPO_NAMES = [
    "ehs-osha-analysis",
    "ehs-ai-grounding-eval",
    "ehs-human-factors-ontology",
    "ehs-risk-sem",
    "ehs-capitals-calculator",
    "grounded",
]


def run(cmd, cwd, timeout=600):
    p = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True,
                        text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def parse_unittest_summary(text):
    """Return (ran, ok) from combined stdout+stderr of a unittest run."""
    m = re.search(r"Ran (\d+) tests?", text)
    ran = int(m.group(1)) if m else None
    ok = bool(re.search(r"^OK", text, re.MULTILINE))
    return ran, ok


def git_info(repo_dir):
    _, out, _ = run("git log -1 --format='%ad,%h' --date=short", repo_dir)
    date, sha = (out.strip().split(",") + [None, None])[:2]
    rc, tag_out, _ = run("git describe --tags --abbrev=0", repo_dir)
    tag = tag_out.strip() if rc == 0 and tag_out.strip() else None
    return date or None, sha or None, tag


def tests_osha(repo_dir):
    data_present = any((repo_dir / "data" / "raw").glob("*.zip"))
    rc, out, err = run("make test", repo_dir, timeout=600)
    ran, ok = parse_unittest_summary(out + err)
    path = "make test (data/raw populated, real-data tests ran)" if data_present \
        else "make test (data/raw empty, real-data tests skipped)"
    return {"count": ran, "ok": ok, "path": path}


def tests_generic(repo_dir, discover_args, path_label):
    rc, out, err = run(f"python3 -m unittest discover {discover_args}", repo_dir, timeout=300)
    ran, ok = parse_unittest_summary(out + err)
    return {"count": ran, "ok": ok, "path": path_label}


def osha_headline(repo_dir):
    f = repo_dir / "outputs" / "summary.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    pooled = d.get("metrics", {}).get("pooled", {})
    return {
        "trir_screened": pooled.get("trir_screened"),
        "dart_screened": pooled.get("dart_screened"),
        "ltir_screened": pooled.get("ltir_screened"),
        "n_filings": pooled.get("n_filings"),
        "implausible_share": d.get("quality", {}).get("pooled", {}).get("implausible_share"),
    }


def benchmark_summary(repo_dir):
    rc, out, _ = run("python3 -m grounding_eval.cli corpus", repo_dir)
    m = re.search(r"items\s+(\d+)", out)
    item_count = int(m.group(1)) if m else None
    results_md = repo_dir / "docs" / "results.md"
    rows = []
    if results_md.exists():
        for line in results_md.read_text().splitlines():
            if line.startswith("|") and not line.startswith("|---") and "adapter" not in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 4:
                    rows.append({"adapter": cells[0], "arm": cells[1], "accuracy": cells[3]})
    return {"item_count": item_count, "baseline_rows": rows}


def ontology_counts(repo_dir):
    rc, out, err = run(
        "PYTHONPATH=src python3 -c \"from ehs_hfo.ontology import Ontology; "
        "o = Ontology.load('ontology/ehs-hfo.ttl'); "
        "print(len(o.factors)); print(len(o.alignments))\"",
        repo_dir,
    )
    lines = [l for l in out.strip().splitlines() if l.strip().isdigit()]
    if len(lines) >= 2:
        return {"factor_count": int(lines[0]), "alignment_count": int(lines[1])}
    return {"factor_count": None, "alignment_count": None}


def main():
    status = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "repos": {}}

    for name in REPO_NAMES:
        repo_dir = REPOS / name
        date, sha, tag = git_info(repo_dir)
        entry = {"last_commit_date": date, "last_commit_sha": sha, "release_tag": tag}

        if name == "ehs-osha-analysis":
            entry["tests"] = tests_osha(repo_dir)
            entry["headline"] = osha_headline(repo_dir)
        elif name == "ehs-ai-grounding-eval":
            entry["tests"] = tests_generic(repo_dir, "-s tests -t .",
                                            "python3 -m unittest discover -s tests -t .")
            entry["benchmark"] = benchmark_summary(repo_dir)
        elif name == "ehs-human-factors-ontology":
            entry["tests"] = tests_generic(repo_dir, "-s tests -t .",
                                            "python3 -m unittest discover -s tests -t .")
            entry["ontology"] = ontology_counts(repo_dir)
        elif name == "ehs-risk-sem":
            entry["tests"] = tests_generic(repo_dir, "-s tests",
                                            "python3 -m unittest discover -s tests")
        elif name == "ehs-capitals-calculator":
            entry["tests"] = tests_generic(repo_dir, "-s tests",
                                            "python3 -m unittest discover -s tests")
        elif name == "grounded":
            entry["tests"] = {"count": 0, "ok": True, "path": "no tests in this repo"}

        status["repos"][name] = entry

    total_tests = sum(
        (r["tests"]["count"] or 0) for r in status["repos"].values() if r.get("tests")
    )
    status["total_tests"] = total_tests
    status["last_commit_date"] = max(
        (r["last_commit_date"] for r in status["repos"].values() if r["last_commit_date"]),
        default=None,
    )

    missing = []
    for name, r in status["repos"].items():
        t = r.get("tests")
        if not t or t.get("count") is None:
            missing.append(f"{name}: test count")
        if r.get("last_commit_date") is None:
            missing.append(f"{name}: last_commit_date")
        if r.get("last_commit_sha") is None:
            missing.append(f"{name}: last_commit_sha")
    if name == "ehs-osha-analysis" and (not status["repos"]["ehs-osha-analysis"].get("headline")):
        missing.append("ehs-osha-analysis: headline")
    if not status["repos"]["ehs-ai-grounding-eval"]["benchmark"].get("item_count"):
        missing.append("ehs-ai-grounding-eval: benchmark item_count")
    if status["repos"]["ehs-human-factors-ontology"]["ontology"].get("factor_count") is None:
        missing.append("ehs-human-factors-ontology: factor_count")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")

    if missing:
        print("MISSING COUNTS:", ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
