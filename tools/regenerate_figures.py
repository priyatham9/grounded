#!/usr/bin/env python3
"""Regenerate the OSHA paper's figures and numeric tables from committed data.

Standard library only, no network, deterministic. The only numeric source is
Table 3 of docs/paper-osha.html (a verbatim copy of
ehs-osha-analysis/outputs/tables/quality_by_year.csv). Everything this script
can derive from it is rebuilt and compared with what the paper embeds:

  fig-1  (fig02_hours_share_implausible.svg)  bars from Table 3
  fig-3  (fig01_aggregate_trir_by_year.svg)   bars from Table 3
  tbl-1  year-level summary                   columns from Table 3
  tbl-2  denominator failure                  pooled sums from Table 3

Items whose inputs are not committed in this repository are listed in
docs/FIGURES.md and reported as "not regenerable"; nothing is invented for them.

The SVG writer below is a stdlib-only port of the bar/annotate subset of
ehs-osha-analysis/src/ehs_osha/svgplot.py (numpy removed, geometry identical).

Usage:
  python3 tools/regenerate_figures.py            # report, exit 1 on any mismatch
  python3 tools/regenerate_figures.py --out DIR  # also write regenerated SVGs
"""
import argparse
import html
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "docs", "paper-osha.html")
PALETTE = ("#0072B2", "#D55E00")
FONT = "'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

NOT_REGENERABLE = {
    "fig-2": "fig03_hours_per_employee: needs the per-filing hours-per-employee histogram; no per-filing data is committed here",
    "fig-4": "fig04_count_model_fit: needs observed/fitted count distributions for NAICS 238; not committed here",
    "fig-5": "fig05_zero_share_by_size: needs outputs/tables/detectability_by_size_band.csv; not committed here",
    "fig-6": "fig06_percentile_stability: needs per-peer-group P75 TRIR pairs (peer_percentiles_by_year.csv); not committed here",
    "fig-7": "fig08_panel_persistence: needs panel_permutation.csv / panel_transitions.csv; not committed here",
    "tbl-4": "count_model_selection_summary.csv is not committed here; values appear only in the paper",
}


# ------------------------------------------------------------- SVG writer --
def _esc(s):
    return html.escape(str(s), quote=True)


class Plot:
    W, H = 820, 460
    L, R, T, B = 78, 24, 46, 74

    def __init__(self, title, xlabel, ylabel, subtitle, ymax):
        self.title, self.xlabel, self.ylabel, self.subtitle = title, xlabel, ylabel, subtitle
        self.ymax = ymax
        self.xmax = 1.0
        self.body = []
        self.right, self.bottom = self.W - self.R, self.H - self.B

    def sx(self, x):
        return self.L + x / (self.xmax or 1.0) * (self.right - self.L)

    def sy(self, y):
        return self.bottom - y / self.ymax * (self.bottom - self.T)

    def bars(self, cats, series):
        n_cat, n_ser = len(cats), len(series)
        self.xmax = float(n_cat)
        slot = (self.right - self.L) / n_cat
        bw = slot * 0.8 / n_ser
        for si, (name, vals) in enumerate(series):
            col = PALETTE[si % len(PALETTE)]
            for ci, v in enumerate(vals):
                x0 = self.L + ci * slot + slot * 0.1 + si * bw
                y1, y0 = self.sy(max(v, 0.0)), self.sy(0.0)
                self.body.append(
                    f'<rect x="{x0:.2f}" y="{min(y0, y1):.2f}" width="{bw:.2f}" '
                    f'height="{abs(y0 - y1):.2f}" fill="{col}" />')
            if n_ser > 1:
                # direct label beside the last bar of each series
                lx = self.L + (n_cat - 1) * slot + slot * 0.1 + si * bw + 11
                ly = self.sy(vals[-1]) - 6 - si * 13
                self.body.append(f'<circle cx="{lx:.1f}" cy="{ly - 3.5:.1f}" r="3" fill="{col}" />')
                self.body.append(
                    f'<text x="{lx + 7:.1f}" y="{ly:.1f}" font-size="10" text-anchor="start" '
                    f'fill="#333">{_esc(name)}</text>')
        for ci, cat in enumerate(cats):
            x = self.L + (ci + 0.5) * slot
            rot = -35 if max(len(c) for c in cats) > 5 else 0
            anchor = "end" if rot else "middle"
            self.body.append(
                f'<text x="{x:.1f}" y="{self.bottom + 16:.1f}" font-size="12" '
                f'text-anchor="{anchor}" fill="#333" '
                f'transform="rotate({rot} {x:.1f} {self.bottom + 16:.1f})">{_esc(cat)}</text>')

    def annotate(self, x, y, text, dx, dy):
        px, py = self.sx(x), self.sy(y)
        lx, ly = px + dx, py + dy
        self.body.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4.5" fill="none" stroke="#333" stroke-width="1.3" />')
        self.body.append(
            f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{lx:.2f}" y2="{ly:.2f}" '
            f'stroke="#333" stroke-width="1" stroke-dasharray="2,2" />')
        anchor = "start" if dx >= 0 else "end"
        self.body.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="10.5" font-weight="600" '
            f'text-anchor="{anchor}" fill="#111">{_esc(text)}</text>')

    @staticmethod
    def _ticks(lo, hi, target=6):
        raw = (hi - lo) / target
        mag = 10 ** math.floor(math.log10(raw))
        step = next(mag * m for m in (1, 2, 2.5, 5, 10) if raw <= mag * m)
        v, out = math.ceil(lo / step) * step, []
        while v <= hi + step * 1e-9:
            out.append(round(v, 10))
            v += step
        return out

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" '
               f'font-family="{FONT}" role="img">',
               f'<rect x="0" y="0" width="{self.W}" height="{self.H}" fill="#ffffff" />']
        for t in self._ticks(0.0, self.ymax):
            y = self.sy(t)
            if not (self.T - 1 <= y <= self.bottom + 1):
                continue
            out.append(f'<line x1="{self.L}" y1="{y:.2f}" x2="{self.right}" y2="{y:.2f}" stroke="#e6e6e6" stroke-width="1" />')
            out.append(f'<text x="{self.L - 8}" y="{y + 4:.2f}" font-size="12" text-anchor="end" fill="#444">{_esc(f"{t:g}")}</text>')
        out.append(f'<line x1="{self.L}" y1="{self.T}" x2="{self.L}" y2="{self.bottom}" stroke="#333" stroke-width="1.2" />')
        out.append(f'<line x1="{self.L}" y1="{self.bottom}" x2="{self.right}" y2="{self.bottom}" stroke="#333" stroke-width="1.2" />')
        out += self.body
        out.append(f'<text x="{self.L}" y="24" font-size="15" font-weight="600" fill="#111">{_esc(self.title)}</text>')
        out.append(f'<text x="{self.L}" y="40" font-size="11" fill="#666">{_esc(self.subtitle)}</text>')
        out.append(f'<text x="{(self.L + self.right) / 2:.1f}" y="{self.H - 12}" font-size="12" text-anchor="middle" fill="#333">{_esc(self.xlabel)}</text>')
        mid = (self.T + self.bottom) / 2
        out.append(f'<text x="16" y="{mid:.1f}" font-size="12" text-anchor="middle" fill="#333" transform="rotate(-90 16 {mid:.1f})">{_esc(self.ylabel)}</text>')
        out.append("</svg>")
        return "\n".join(out)


# ------------------------------------------------------------ paper parse --
def _cells(row_html):
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
            for c in re.findall(r"<t[dh]>(.*?)</t[dh]>", row_html, re.S)]


def read_paper(path=PAPER):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def table_rows(page, tid):
    m = re.search(r'<figure class="papertable" id="%s">.*?</figure>' % tid, page, re.S)
    if not m:
        raise SystemExit("table %s missing from paper" % tid)
    return [_cells(r) for r in re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)]


def embedded_svg(page, fid):
    m = re.search(r'<figure class="paperfig" id="%s"><div class="figbody">(<svg.*?</svg>)' % fid, page, re.S)
    if not m:
        raise SystemExit("figure %s missing from paper" % fid)
    return m.group(1)


def load_table3(page):
    rows = table_rows(page, "tbl-3")
    head = rows[0]
    return [dict(zip(head, r)) for r in rows[1:]]


# ----------------------------------------------------------- regeneration --
def regen_fig1(t3):
    """fig02_hours_share_implausible.svg (paper Figure 1)."""
    years = [str(int(r["label"])) for r in t3]
    share = [100.0 * float(r["hours_share_implausible"]) for r in t3]
    cnt = [100.0 * float(r["implausible_share"]) for r in t3]
    p = Plot("A small share of filings carries most of the reported hours",
             "Reporting year", "Percent",
             "Implausible filings hold from a third to nearly all reported hours, year to year.", 105.0)
    p.bars(years, [("% of filings flagged implausible", cnt),
                   ("% of all reported hours held by them", share)])
    return p.svg()


def regen_fig3(t3):
    """fig01_aggregate_trir_by_year.svg (paper Figure 3)."""
    years = [str(int(r["label"])) for r in t3]
    naive = [float(r["aggregate_trir_unscreened"]) for r in t3]
    scr = [float(r["aggregate_trir_screened"]) for r in t3]
    p = Plot("Aggregate TRIR before and after the plausibility screen",
             "Reporting year", "Recordable cases per 200,000 hours",
             "Unscreened TRIR tracks bad hours data, not safety performance.",
             max(max(scr) * 1.15, 1.0))
    p.bars(years, [("unscreened (all filings)", naive), ("screened", scr)])
    for yr, dx in (("2019", -6), ("2024", 6)):
        i = years.index(yr)
        p.annotate(i + 0.3, naive[i], f"{yr} unscreened {naive[i]:.2f}", dx, -20)
        p.annotate(i + 0.7, scr[i], f"{yr} screened {scr[i]:.2f}", dx, -8)
    return p.svg()


def regen_tbl1(t3):
    out = [["Year", "Filings", "Flagged", "Hours in flagged", "TRIR raw", "TRIR screened", "Ratio"]]
    for r in t3:
        out.append([str(int(r["label"])), f'{int(r["n_filings"]):,}',
                    f'{100 * float(r["implausible_share"]):.2f}%',
                    f'{100 * float(r["hours_share_implausible"]):.1f}%',
                    f'{float(r["aggregate_trir_unscreened"]):.3f}',
                    f'{float(r["aggregate_trir_screened"]):.3f}',
                    f'{float(r["ratio_screened_to_unscreened"]):.2f}x'])
    return out


def pooled(t3):
    n = sum(int(r["n_filings"]) for r in t3)
    k = sum(int(r["n_implausible"]) for r in t3)
    h = sum(int(r["hours_total"]) for r in t3)
    c = sum(int(r["cases_total"]) for r in t3)
    fh = sum(int(r["hours_total"]) * float(r["hours_share_implausible"]) for r in t3)
    fc = sum(int(r["cases_total"]) * float(r["cases_share_implausible"]) for r in t3)
    return n, k, h, c, fh, fc


NUM = re.compile(r"-?\d+(?:\.\d+)?")
COORD_TOL = 0.05  # px; Table 3 carries rounded inputs, the CSV it came from does not


def svg_delta(a, b):
    """Max numeric difference between two SVGs with identical non-numeric text,
    or None when the text skeleton differs."""
    if NUM.sub("#", a) != NUM.sub("#", b):
        return None
    pa, pb = NUM.findall(a), NUM.findall(b)
    return max([abs(float(x) - float(y)) for x, y in zip(pa, pb)] or [0.0])


def run(out_dir=None):
    page = read_paper()
    t3 = load_table3(page)
    problems, notes, ok = [], [], []

    # Figures: same SVG skeleton and every number within COORD_TOL px.
    for fid, fn in (("fig-1", regen_fig1), ("fig-3", regen_fig3)):
        regen, committed = fn(t3), embedded_svg(page, fid)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, fid + ".svg"), "w", encoding="utf-8") as fh:
                fh.write(regen + "\n")
        delta = svg_delta(regen, committed)
        if delta is not None and delta <= COORD_TOL:
            ok.append(fid)
            if delta:
                notes.append("%s matches within %.2f px (max coordinate delta %.2f; rounded Table 3 inputs)" % (fid, COORD_TOL, delta))
        else:
            problems.append(fid)
            a, b = regen.splitlines(), committed.splitlines()
            diff = [i + 1 for i in range(max(len(a), len(b)))
                    if (a[i] if i < len(a) else None) != (b[i] if i < len(b) else None)]
            notes.append("%s differs on %d of %d lines (first: line %s)\n  regenerated: %s\n  committed:   %s" % (
                fid, len(diff), len(b), diff[0],
                a[diff[0] - 1] if diff[0] <= len(a) else "<none>",
                b[diff[0] - 1] if diff[0] <= len(b) else "<none>"))

    # Table 1: every column rebuilt from Table 3 must match exactly, except
    # Ratio, which Table 3 only carries rounded; compared to 0.5 percent.
    t1_got, t1_want = regen_tbl1(t3), table_rows(page, "tbl-1")
    t1_bad = []
    for g, w in zip(t1_got, t1_want):
        for j, (a, b) in enumerate(zip(g, w)):
            if j == 6 and g is not t1_got[0]:
                if abs(float(a[:-1]) - float(b[:-1])) > 0.005 * float(a[:-1]):
                    t1_bad.append((g[0], a, b))
            elif a != b:
                t1_bad.append((g[0], a, b))
    if len(t1_got) != len(t1_want):
        t1_bad.append(("rows", len(t1_got), len(t1_want)))
    if t1_bad:
        problems.append("tbl-1")
        notes.append("tbl-1 mismatches (row, regenerated, committed): %s" % t1_bad)
    else:
        ok.append("tbl-1")

    # Table 2: pooled values. Filings, flagged, hours share, cases share and
    # unscreened TRIR follow from Table 3 exactly. Screened TRIR and the
    # ratio need unrounded flagged hours/cases, which Table 3 only carries as
    # 4-decimal shares, so they are checked to 1 percent, not regenerated.
    n, k, h, c, fh, fc = pooled(t3)
    t2 = {r[0]: r[1] for r in table_rows(page, "tbl-2") if len(r) == 2}
    exact = {
        "Filings after deduplication": f"{n:,}",
        "Flagged implausible": f"{k:,} ({100 * k / n:.2f}%)",
        "Share of all reported hours they hold": f"{100 * fh / h:.2f}%",
        "Share of all reported cases they hold": f"{100 * fc / c:.2f}%",
        "Aggregate TRIR, unscreened": f"{c * 2e5 / h:.3f}",
    }
    t2_bad = [(k_, v, t2.get(k_)) for k_, v in exact.items() if t2.get(k_) != v]
    scr = (c - fc) * 2e5 / (h - fh)
    if abs(scr - float(t2["Aggregate TRIR, screened"])) > 0.01 * scr:
        t2_bad.append(("screened TRIR (1% tolerance)", round(scr, 3), t2["Aggregate TRIR, screened"]))
    ratio = scr / (c * 2e5 / h)
    if abs(ratio - float(t2["Ratio"].rstrip("×"))) > 0.01 * ratio:
        t2_bad.append(("ratio (1% tolerance)", round(ratio, 2), t2["Ratio"]))
    if t2_bad:
        problems.append("tbl-2")
        notes.append("tbl-2 mismatches (item, regenerated, committed): %s" % t2_bad)
    else:
        ok.append("tbl-2")
    return ok, problems, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="directory to write regenerated SVGs into")
    args = ap.parse_args(argv)
    ok, problems, notes = run(args.out)
    for x in ok:
        print("match           %s" % x)
    for x in problems:
        print("MISMATCH        %s" % x)
    for fid, why in NOT_REGENERABLE.items():
        print("not regenerable %s: %s" % (fid, why))
    for n in notes:
        print(n)
    total = len(ok) + len(problems) + len(NOT_REGENERABLE)
    print("%d of %d items regenerable (%d match, %d mismatch)" % (
        len(ok) + len(problems), total, len(ok), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
