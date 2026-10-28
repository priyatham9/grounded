"""Checks docs/references-paper.csv against docs/paper.html and the README."""
import csv
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {"verified", "corrected", "unreachable", "unsupported-claim", "metadata-only", "unchecked"}


class ReferencesLedger(unittest.TestCase):
    def setUp(self):
        with open(ROOT / "docs" / "references-paper.csv", encoding="utf-8", newline="") as f:
            self.rows = list(csv.DictReader(f))

    def test_keys_match_paper(self):
        html = (ROOT / "docs" / "paper.html").read_text(encoding="utf-8")
        i = html.index('<h2 id="references"')
        keys = re.findall(r'<div class="ref" id="ref-([^"]+)"', html[i:])
        self.assertEqual(sorted(keys), sorted(r["key"] for r in self.rows))

    def test_status_values(self):
        for r in self.rows:
            self.assertIn(r["status"], STATUSES, r["key"])

    def test_checked_rows_have_a_source(self):
        for r in self.rows:
            if r["status"] != "unchecked":
                self.assertTrue(r["checked_via"].strip(), r["key"])

    def test_readme_counts(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        n = lambda s: sum(1 for r in self.rows if r["status"] == s)
        self.assertIn("%d of the %d were re-checked" % (len(self.rows) - n("unchecked"), len(self.rows)), readme)
        self.assertIn("%d verified, %d corrected, %d with a reworded sentence" % (n("verified"), n("corrected"), n("unsupported-claim")), readme)


if __name__ == "__main__":
    unittest.main()
