"""Fails if a committed figure or numeric table in docs/paper-osha.html differs
from what tools/regenerate_figures.py rebuilds from the committed Table 3."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regenerate_figures as rf


class TestFigures(unittest.TestCase):
    def test_committed_figures_match_regenerated(self):
        ok, problems, notes = rf.run()
        self.assertEqual(problems, [], "\n".join(notes))
        self.assertEqual(sorted(ok), ["fig-1", "fig-3", "fig-4", "fig-5", "fig-6", "fig-7", "tbl-1", "tbl-2", "tbl-4"])

    def test_detects_changed_figure_number(self):
        page = rf.read_paper()
        t3 = rf.load_table3(page)
        svg = rf.embedded_svg(page, "fig-3")
        self.assertIsNotNone(rf.svg_delta(rf.regen_fig3(t3), svg))
        tampered = svg.replace('height="175.24"', 'height="185.24"')
        self.assertGreater(rf.svg_delta(rf.regen_fig3(t3), tampered), rf.COORD_TOL)

    def test_csv_figures_are_exact_and_detect_change(self):
        page = rf.read_paper()
        for fid, fn in (("fig-4", rf.regen_fig4), ("fig-5", rf.regen_fig5),
                        ("fig-6", rf.regen_fig6), ("fig-7", rf.regen_fig7)):
            self.assertEqual(rf.svg_delta(fn(), rf.embedded_svg(page, fid)), 0.0, fid)
        svg = rf.embedded_svg(page, "fig-5")
        tampered = svg.replace('height="255.37"', 'height="256.37"')
        self.assertNotEqual(tampered, svg)
        self.assertGreater(rf.svg_delta(rf.regen_fig5(), tampered), 0.0)

    def test_vendored_csvs_match_recorded_checksums(self):
        import hashlib, json
        meta = json.loads((Path(rf.SRC) / "SOURCE.json").read_text())
        for name, want in meta["files"].items():
            blob = (Path(rf.SRC) / name).read_bytes()
            git_sha = hashlib.sha1(b"blob %d\0" % len(blob) + blob).hexdigest()
            self.assertEqual(git_sha, want["git_blob_sha"], name)

    def test_every_figure_is_accounted_for(self):
        page = rf.read_paper()
        import re
        ids = set(re.findall(r'class="paper(?:fig|table)" id="([^"]+)"', page))
        ok, problems, _ = rf.run()
        handled = set(ok) | set(problems) | {"tbl-3"} | set(rf.NOT_REGENERABLE)
        self.assertEqual(ids, handled)


if __name__ == "__main__":
    unittest.main()
