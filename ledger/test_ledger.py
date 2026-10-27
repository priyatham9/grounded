"""Tests for the methods and limitations ledger.

Offline tests check the shape of docs/methods-ledger.json, that the checker
catches missing files and reworded quotes, and that docs/methods-ledger.html
is in sync. TestPublicGitHub fetches every linked file from the sibling
repositories' public GitHub copies and is the test that all linked paths exist
there; set LEDGER_OFFLINE=1 to skip it.
"""

import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_ledger as bl
import check_ledger as cl

LEDGER = json.loads(cl.LEDGER.read_text(encoding="utf-8"))
REPOS = {
    "ehs-ai-grounding-eval",
    "ehs-benchmarks",
    "ehs-capitals-calculator",
    "ehs-chemical-peers",
    "ehs-human-factors-ontology",
    "ehs-osha-analysis",
    "ehs-risk-sem",
}
# Items the ledger was asked to cover; each must appear as a quote or text.
REQUIRED = {
    "same-coder limitation": ("ehs-human-factors-ontology", "No second coder reviewed them."),
    "Q3/Q4 uninformative intervals": ("ehs-osha-analysis", "Q3 and Q4 have very wide intervals"),
    "calibration only for tfidf": ("ehs-ai-grounding-eval", "not computed for BM25, BM25+ or RRF"),
    "quarantined items": ("ehs-ai-grounding-eval", "could not be verified"),
    "WBGT omitted": ("ehs-capitals-calculator", "WBGT triggers"),
}


class FakeFetcher:
    def __init__(self, files):
        self.files = files

    def get(self, repo, path):
        return self.files.get((repo, path))


class TestShape(unittest.TestCase):
    def test_row_ids_unique(self):
        ids = [r["id"] for r in LEDGER["rows"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_repo_in_refs_and_covered(self):
        self.assertEqual(set(LEDGER["refs"]), REPOS)
        self.assertEqual({r["repo"] for r in LEDGER["rows"]}, REPOS)

    def test_every_row_is_fully_linked(self):
        for row in LEDGER["rows"]:
            for k in ("id", "repo", "method", "method_path", "assumptions", "caveats"):
                self.assertTrue(row.get(k), (row.get("id"), k))
            for kind in ("assumptions", "caveats"):
                for item in row[kind]:
                    for k in ("text", "path", "quote"):
                        self.assertTrue(item.get(k), (row["id"], kind, k))
                    self.assertFalse(item["path"].startswith(("/", "http")), item["path"])

    def test_requested_caveats_present(self):
        for name, (repo, needle) in REQUIRED.items():
            hits = [
                it
                for r in LEDGER["rows"]
                if r["repo"] == repo
                for it in r["assumptions"] + r["caveats"]
                if needle in it["quote"]
            ]
            self.assertTrue(hits, name)


class TestCheckerLogic(unittest.TestCase):
    def setUp(self):
        self.ledger = {
            "rows": [
                {
                    "id": "r1",
                    "repo": "a",
                    "method_path": "M.md",
                    "assumptions": [],
                    "caveats": [{"text": "t", "path": "C.md", "quote": "two words"}],
                }
            ]
        }

    def test_passes_and_ignores_line_breaks(self):
        f = FakeFetcher({("a", "M.md"): "x", ("a", "C.md"): "has two\nwords here"})
        self.assertEqual(cl.check(self.ledger, f), [])

    def test_missing_file_fails(self):
        f = FakeFetcher({("a", "C.md"): "two words"})
        self.assertTrue(any("does not exist" in m for m in cl.check(self.ledger, f)))

    def test_reworded_quote_fails(self):
        f = FakeFetcher({("a", "M.md"): "x", ("a", "C.md"): "two  other words"})
        self.assertTrue(any("quote not found" in m for m in cl.check(self.ledger, f)))


class TestHtmlInSync(unittest.TestCase):
    def test_page_main_matches_json(self):
        page = bl.PAGE.read_text(encoding="utf-8")
        self.assertEqual(bl.committed_main(page), bl.render_main(LEDGER))

    def test_every_blob_link_is_on_the_page(self):
        page = bl.PAGE.read_text(encoding="utf-8")
        for row in LEDGER["rows"]:
            self.assertIn(bl.blob(LEDGER, row["repo"], row["method_path"]), page)


class TestPublicGitHub(unittest.TestCase):
    """Every linked path exists in the public repositories, and says what we quote."""

    @unittest.skipIf(os.environ.get("LEDGER_OFFLINE") == "1", "LEDGER_OFFLINE=1")
    def test_all_links_resolve_on_github(self):
        fetcher = cl.Fetcher(LEDGER, os.environ.get("LEDGER_LOCAL_ROOT"))
        try:
            failures = cl.check(LEDGER, fetcher)
        except (urllib.error.URLError, OSError) as e:
            self.skipTest(f"GitHub unreachable: {e}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
