#!/usr/bin/env python3
"""Recompute docs/status.json from the public GitHub repositories.

Standard library only (plus the git CLI). Each repository is cloned over HTTPS
with `git clone --depth 1` into a temporary directory; nothing from a clone is
executed.

COUNTING METHOD (static, not a test run). A test is counted as one function or
method whose name starts with `test`, defined (at module level or inside any
class) in a file named `test_*.py` or `*_test.py`, found by parsing the file
with `ast`. Consequences, stated so the numbers are not over-read:
  * tests that skip at run time (for example real-data tests when data/raw is
    empty) ARE counted; the count is the number of test functions, not the
    number that passed;
  * a parametrised test or one using subTest counts once;
  * this can differ from the "Ran N tests" line of a unittest run.
Because nothing is run, the file does not assert that the suites pass; it
records the field `tests.method` per repository to say so.

Other fields: last commit date/sha and latest release tag come from git;
`headline` for ehs-osha-analysis is read from outputs/summary.json. The
`benchmark` and `ontology` blocks need the repos' own code to be run, so they
are carried forward unchanged from the committed file (listed under
`carried_forward`). The grounded entry omits commit fields on purpose: a
snapshot committed to grounded would otherwise always differ from grounded's
own HEAD.

  python3 tools/refresh_status.py          # rewrite docs/status.json
  python3 tools/refresh_status.py --check  # exit 1 if the committed snapshot is
                                           # older than 14 days or its counts, tags
                                           # or headline figures differ
"""
import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "status.json"
OWNER = "priyatham9"
REPO_NAMES = [
    "ehs-osha-analysis",
    "ehs-ai-grounding-eval",
    "ehs-human-factors-ontology",
    "ehs-risk-sem",
    "ehs-capitals-calculator",
    "grounded",
]
MAX_AGE_DAYS = 14
METHOD = ("static count of test*/async test* functions in test_*.py and *_test.py "
          "files (ast); includes tests that skip at run time; not a test run")
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}
CARRIED = ("benchmark", "ontology")


def git(args, cwd=None):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def count_tests(repo_dir):
    n = 0
    for f in sorted(repo_dir.rglob("*.py")):
        rel = f.relative_to(repo_dir)
        if SKIP_DIRS & set(rel.parts):
            continue
        if not (f.name.startswith("test_") or f.name.endswith("_test.py")):
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(rel))
        n += sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and x.name.startswith("test") for x in ast.walk(tree))
    return n


def latest_tag(url):
    out = git(["ls-remote", "--tags", "--refs", url])
    tags = [l.split("refs/tags/", 1)[1] for l in out.splitlines() if "refs/tags/" in l]
    key = lambda t: [int(x) for x in re.findall(r"\d+", t)]
    return max(tags, key=key) if tags else None


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


def build(previous):
    status = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "test_count_method": METHOD, "repos": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for name in REPO_NAMES:
            url = f"https://github.com/{OWNER}/{name}.git"
            dest = Path(tmp) / name
            git(["clone", "--quiet", "--depth", "1", url, str(dest)])
            entry = {"release_tag": latest_tag(url),
                     "tests": {"count": count_tests(dest), "method": "static"}}
            if name != "grounded":
                date, sha = git(["log", "-1", "--format=%ad,%h", "--date=short"], dest).split(",")
                entry["last_commit_date"], entry["last_commit_sha"] = date, sha
            if name == "ehs-osha-analysis":
                entry["headline"] = osha_headline(dest)
            prev = previous.get("repos", {}).get(name, {})
            for k in CARRIED:
                if k in prev:
                    entry[k] = prev[k]
            status["repos"][name] = entry
    status["carried_forward"] = list(CARRIED)
    status["total_tests"] = sum(r["tests"]["count"] for r in status["repos"].values())
    status["last_commit_date"] = max(r["last_commit_date"] for r in status["repos"].values()
                                     if "last_commit_date" in r)
    return status


def load_previous():
    try:
        return json.loads(OUT.read_text())
    except (OSError, ValueError):
        return {}


def check():
    committed = load_previous()
    problems = []
    try:
        age = (datetime.now(timezone.utc)
               - datetime.strptime(committed["generated_utc"], "%Y-%m-%dT%H:%M:%SZ")
               .replace(tzinfo=timezone.utc)).days
        if age > MAX_AGE_DAYS:
            problems.append(f"snapshot is {age} days old (limit {MAX_AGE_DAYS})")
    except (KeyError, ValueError):
        problems.append("snapshot has no valid generated_utc")
    fresh = build(committed)
    # Commit date/sha are informational and move with every upstream push; the
    # check compares counts, tags and headline figures.
    for d in (committed, fresh):
        d.pop("generated_utc", None)
        d.pop("last_commit_date", None)
        for r in d.get("repos", {}).values():
            r.pop("last_commit_date", None)
            r.pop("last_commit_sha", None)
    if committed != fresh:
        for name in REPO_NAMES:
            a, b = committed.get("repos", {}).get(name), fresh["repos"][name]
            if a != b:
                problems.append(f"{name}: committed {json.dumps(a, sort_keys=True)} "
                                f"!= recomputed {json.dumps(b, sort_keys=True)}")
        if not problems or committed.get("total_tests") != fresh["total_tests"]:
            problems.append(f"total_tests committed {committed.get('total_tests')} "
                            f"!= recomputed {fresh['total_tests']}")
    for p in problems:
        print("STALE:", p, file=sys.stderr)
    if problems:
        print("Run `python3 tools/refresh_status.py`, update quoted counts, and commit.",
              file=sys.stderr)
        return 1
    print("docs/status.json is current")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    status = build(load_previous())
    OUT.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}: total_tests={status['total_tests']}")
    for n, r in status["repos"].items():
        print(f"  {n}: {r['tests']['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
