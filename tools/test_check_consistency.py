"""Runs the headline-number consistency check against the repo (offline)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_consistency as cc


class TestConsistency(unittest.TestCase):
    def test_repo_is_consistent(self):
        reg = json.loads(cc.DEFAULT.read_text(encoding="utf-8"))
        self.assertEqual(cc.check(reg), [])

    def test_detects_mismatch(self):
        reg = {"claims": [{"id": "x", "value": "1", "source": {"file": "README.md", "regex": "(Landing)"},
                           "appears_in": []}]}
        self.assertTrue(cc.check(reg))


if __name__ == "__main__":
    unittest.main()
