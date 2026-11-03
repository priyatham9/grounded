"""Design-token guard: pages carry tokens.css and the engine has no letter-split or from-zero counters."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_tokens

DOCS = HERE.parent / "docs"


class TestTokens(unittest.TestCase):
    def test_pages_match_tokens(self):
        pages = [p for p in sorted(DOCS.glob("*.html")) if check_tokens.START in p.read_text(encoding="utf-8")]
        self.assertTrue(pages, "no docs page carries the tokens block")
        tokens = (HERE / "tokens.css").read_text(encoding="utf-8")
        problems = []
        for p in pages:
            problems += check_tokens.check(p, tokens)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_checker_detects_drift(self):
        import tempfile
        tokens = (HERE / "tokens.css").read_text(encoding="utf-8")
        page = "<style>\n%s\n%s\n%s\n:root{--accent:#ff0000}</style>" % (check_tokens.START, tokens.strip("\n"), check_tokens.END)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.html"
            f.write_text(page, encoding="utf-8")
            self.assertTrue(any("--accent" in m for m in check_tokens.check(f, tokens)))

    def test_engine_has_no_char_split_or_zero_tween(self):
        js = (HERE / "story.js").read_text(encoding="utf-8")
        self.assertNotIn('"words,chars"', js)
        self.assertNotIn('type: "chars"', js)
        self.assertNotIn("rotate: type", js)
        self.assertNotIn("var o = { v: 0 }", js)
        self.assertNotIn("opts.from == null ? 0 : opts.from", js)
        self.assertIsNone(re.search(r"tween\(\s*[^,]*,\s*target\b", js))


if __name__ == "__main__":
    unittest.main()
