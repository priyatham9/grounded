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
        self.assertEqual(sorted(ok), ["fig-1", "fig-3", "tbl-1", "tbl-2"])

    def test_detects_changed_figure_number(self):
        page = rf.read_paper()
        t3 = rf.load_table3(page)
        svg = rf.embedded_svg(page, "fig-3")
        self.assertIsNotNone(rf.svg_delta(rf.regen_fig3(t3), svg))
        tampered = svg.replace('height="175.24"', 'height="185.24"')
        self.assertGreater(rf.svg_delta(rf.regen_fig3(t3), tampered), rf.COORD_TOL)

    def test_every_figure_is_accounted_for(self):
        page = rf.read_paper()
        import re
        ids = set(re.findall(r'class="paper(?:fig|table)" id="([^"]+)"', page))
        handled = {"fig-1", "fig-3", "tbl-1", "tbl-2", "tbl-3"} | set(rf.NOT_REGENERABLE)
        self.assertEqual(ids, handled)


if __name__ == "__main__":
    unittest.main()
