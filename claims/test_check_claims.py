"""Offline tests for the claims registry and checker (no network)."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_claims as cc

REG = json.loads((Path(cc.HERE) / "claims.json").read_text(encoding="utf-8"))
KINDS = {"json_path", "csv_cell", "csv_rows", "regex_count"}


class TestRegistryShape(unittest.TestCase):
    def test_ids_unique(self):
        ids = [c["id"] for c in REG["claims"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_claim_is_fully_specified(self):
        for c in REG["claims"]:
            for k in (
                "statement",
                "appears_in",
                "source",
                "expected",
                "tolerance",
                "verifying_test",
            ):
                self.assertIn(k, c, c["id"])
            self.assertTrue(c["appears_in"], c["id"])
            self.assertIn(c["source"]["kind"], KINDS, c["id"])
            for k in ("repo", "path"):
                self.assertTrue(c["source"][k], c["id"])
            for k in ("repo", "path", "symbol"):
                self.assertTrue(c["verifying_test"][k], c["id"])

    def test_pages_named_exist_and_contain_the_text(self):
        for c in REG["claims"]:
            for a in c["appears_in"]:
                page = (cc.REPO_ROOT / a["path"]).read_text(encoding="utf-8")
                self.assertIn(a["contains"], page, c["id"])

    def test_headline_trir_claim_is_registered(self):
        c = next(c for c in REG["claims"] if c["id"] == "osha-trir-ratio")
        self.assertAlmostEqual(c["expected"], 29.7108)


class TestChecker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "r").mkdir()
        (root / "r" / "t.csv").write_text("label,v\npooled,2.5\n", encoding="utf-8")
        (root / "r" / "t.py").write_text(
            "def test_x():\n    assert 2.5\n", encoding="utf-8"
        )
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def _reg(self, expected):
        claim = {
            "id": "x",
            "statement": "x",
            "appears_in": [{"path": "README.md", "contains": "grounded"}],
            "source": {
                "repo": "r",
                "path": "t.csv",
                "kind": "csv_cell",
                "where": {"label": "pooled"},
                "column": "v",
            },
            "expected": expected,
            "tolerance": 0.01,
            "verifying_test": {
                "repo": "r",
                "path": "t.py",
                "symbol": "test_x",
                "contains": "2.5",
            },
        }
        p = self.root / "reg.json"
        p.write_text(
            json.dumps({"raw_base": "", "ref": "main", "claims": [claim]}),
            encoding="utf-8",
        )
        return p

    def test_passes_when_source_matches(self):
        out = io.StringIO()
        self.assertEqual(cc.run(self._reg(2.5), self.root, out), 0)

    def test_fails_when_source_drifts(self):
        out = io.StringIO()
        self.assertEqual(cc.run(self._reg(3.0), self.root, out), 1)
        self.assertIn("differs from expected", out.getvalue())

    def test_fails_when_test_symbol_removed(self):
        (self.root / "r" / "t.py").write_text("pass\n", encoding="utf-8")
        out = io.StringIO()
        self.assertEqual(cc.run(self._reg(2.5), self.root, out), 1)
        self.assertIn("symbol", out.getvalue())


if __name__ == "__main__":
    unittest.main()
