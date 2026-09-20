#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render paper/PAPER.md to repos/grounded/docs/paper.html.

Pure standard library, Python 3.9 compatible. No build step, no dependencies,
no CDN except the Google Fonts stylesheet the rest of the site already loads.

What it handles: ATX headings, paragraphs, bullet and ordered lists, pipe
tables, fenced code blocks, blockquotes (recursively), horizontal rules,
inline code, bold, italic, footnote references and definitions, and the
[citation_key] markers used throughout the manuscript.

Citation markers become superscript links into the References section, and
every reference entry links back to each place it was cited. That is the
whole point of the exercise: a 33,000 word paper with 193 references is not
navigable without it.

Usage:  python3 tools/build_paper.py
"""

import html
import io
import json
import csv
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banner import apply_banner
import re
import sys

# ----------------------------------------------------------------- paths ---

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_MD = os.environ.get("PAPER_SRC") or os.path.join(ROOT, "paper", "PAPER.md")
SRC_JSON = os.path.join(ROOT, "paper", "citations_verified.json")
OUT_HTML = os.environ.get("PAPER_OUT") or os.path.join(
    ROOT, "repos", "grounded", "docs", "paper.html"
)
CITATION_CFF = os.path.join(ROOT, "repos", "grounded", "CITATION.cff")

# Bracketed tokens that look like citation keys but are not. "given" and
# "literature" are literal markers inside the derivation-trace listings.
NOT_CITATIONS = frozenset(["given", "literature", "convention", "no source"])

# Figure and table directives resolve against the committed osha-analysis
# outputs. A missing file is a build failure, never a silent gap.
OSHA_OUT = os.path.join(ROOT, "repos", "ehs-osha-analysis", "outputs")
FIG_DIR = os.path.join(OSHA_OUT, "figures")
TABLE_DIR = os.path.join(OSHA_OUT, "tables")
TABLE_MAX_ROWS = 15
DIRECTIVE_RE = re.compile(r"^!(figure|table)\[([^\]]+)\]\((.*)\)\s*$")

EM_DASH = u"\u2014"

# --------------------------------------------------------------- helpers ---


def die(msg):
    sys.stderr.write("build_paper: %s\n" % msg)
    raise SystemExit(1)


def slug(text):
    s = re.sub(r"<[^>]+>", "", text)
    s = html.unescape(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "section"


URL_RE = re.compile(r"https?://[^\s<>\"']+")


def clean_url(url):
    """Drop trailing punctuation that the prose wrapped around a URL, while
    keeping a closing parenthesis that balances one inside the URL itself,
    as in doi.org/10.1016/S0925-7535(03)00047-X."""
    while url:
        last = url[-1]
        if last in ".,;:!?'\"]":
            url = url[:-1]
            continue
        if last == ")" and url.count(")") > url.count("("):
            url = url[:-1]
            continue
        break
    return url


def autolink(text):
    """Turn bare URLs in already-escaped HTML into links; text must contain
    no anchor elements yet."""
    def one(m):
        raw = m.group(0)
        u = clean_url(raw)
        tail = raw[len(u):]
        return ('<a href="%s" rel="noopener noreferrer" target="_blank">%s</a>%s'
                % (u, u, tail))
    return URL_RE.sub(one, text)


def esc(text):
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


# ---------------------------------------------------------- inline markup ---


class Inline(object):
    """Inline renderer. Holds the citation map and the per-key call counter."""

    def __init__(self, refs):
        self.refs = refs           # key -> reference record
        self.counts = {}           # key -> number of citation sites so far
        self.sites = {}            # key -> list of anchor ids
        self.in_refs = False       # suppress citation linking inside References

    # -- citations ---------------------------------------------------------

    def _cite_site(self, key):
        n = self.counts.get(key, 0) + 1
        self.counts[key] = n
        anchor = "cite-%s-%d" % (key, n)
        self.sites.setdefault(key, []).append(anchor)
        return anchor

    def _citation(self, match):
        raw = match.group(1)
        parts = [p.strip() for p in re.split(r"([;,])", raw)]
        # re.split with a capture group keeps the separators; walk them.
        tokens = [t for t in parts if t not in (";", ",")]
        if not tokens or not all(tokens):
            return match.group(0)
        if not all(re.match(r"^[a-z][a-z0-9_]*$", t) for t in tokens):
            return match.group(0)
        if any(t in NOT_CITATIONS for t in tokens):
            return match.group(0)
        if not any(t in self.refs for t in tokens):
            return match.group(0)

        out = []
        for piece in parts:
            if piece in (";", ","):
                out.append(piece + " ")
                continue
            if piece in self.refs:
                anchor = self._cite_site(piece)
                out.append(
                    '<a id="%s" href="#ref-%s" title="%s">%s</a>'
                    % (anchor, piece, esc(self._short(piece)), piece)
                )
            else:
                out.append(piece)
        return '<sup class="cite">[%s]</sup>' % "".join(out).strip()

    def _short(self, key):
        ref = self.refs[key]["reference"]
        ref = re.sub(r"\s+", " ", ref).strip()
        return ref[:150] + ("..." if len(ref) > 150 else "")

    # -- main --------------------------------------------------------------

    def render(self, text):
        text = re.sub(r"\s+", " ", text).strip()

        # 1. Lift code spans out so nothing else touches them.
        spans = []

        def stash(m):
            spans.append(m.group(2))
            return "\x00%d\x00" % (len(spans) - 1)

        text = re.sub(r"(`+)(.+?)\1", stash, text)

        # 2. Escape, then re-add our own markup.
        text = esc(text)

        # 3. Footnote references, before citation bracket matching.
        text = re.sub(
            r"\[\^(\d+)\]",
            lambda m: '<sup class="fnref" id="fnref-%s">'
            '<a href="#fn-%s">%s</a></sup>' % (m.group(1), m.group(1), m.group(1)),
            text,
        )

        # 4. Citation markers.
        if not self.in_refs:
            text = re.sub(r"\[([^\[\]\n]{1,200})\]", self._citation, text)

        # 5. Emphasis. Bold first so ** is not eaten by the italic pass.
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", text)

        # 6. Put the code spans back.
        def unstash(m):
            return "<code>%s</code>" % esc(spans[int(m.group(1))])

        text = re.sub(r"\x00(\d+)\x00", unstash, text)
        return text


# ----------------------------------------------------------- block parser ---


class Renderer(object):
    def __init__(self, refs):
        self.refs = refs
        self.inline = Inline(refs)
        self.toc = []              # (level, id, text)
        self.ref_entries = []      # (key, html_reference, html_note)
        self.seen_ids = {}
        self.n_figures = 0
        self.n_tables = 0

    def uid(self, base):
        n = self.seen_ids.get(base, 0)
        self.seen_ids[base] = n + 1
        return base if n == 0 else "%s-%d" % (base, n + 1)

    # -- entry point -------------------------------------------------------

    def render(self, lines, depth=0):
        out = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # figure / table directives
            dm = DIRECTIVE_RE.match(stripped)
            if dm:
                kind, rel, caption = dm.groups()
                if kind == "figure":
                    out.append(self.figure(rel, caption))
                else:
                    out.append(self.csv_table(rel, caption))
                i += 1
                continue

            # fenced code
            if stripped.startswith("```"):
                j = i + 1
                buf = []
                while j < n and not lines[j].strip().startswith("```"):
                    buf.append(lines[j])
                    j += 1
                out.append(
                    '<div class="codewrap"><pre><code>%s</code></pre></div>'
                    % esc("\n".join(buf))
                )
                i = j + 1
                continue

            # horizontal rule
            if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
                out.append('<hr class="rule" />')
                i += 1
                continue

            # heading
            m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if m:
                level = len(m.group(1))
                body = self.inline.render(m.group(2))
                hid = self.uid(slug(m.group(2)))
                if level <= 3 and depth == 0:
                    self.toc.append((level, hid, re.sub(r"<[^>]+>", "", body)))
                    if slug(m.group(2)) == "references":
                        self.inline.in_refs = True
                tag = "h%d" % min(level + 1, 6)
                cls = "h-l%d" % level
                out.append(
                    '<%s id="%s" class="%s">%s'
                    '<a class="anchor" href="#%s" aria-label="Link to this section">#</a>'
                    "</%s>" % (tag, hid, cls, body, hid, tag)
                )
                i += 1
                continue

            # table
            if stripped.startswith("|") and i + 1 < n and re.match(
                r"^\|[\s:\-\|]+\|$", lines[i + 1].strip()
            ):
                head = self.split_row(lines[i])
                j = i + 2
                rows = []
                while j < n and lines[j].strip().startswith("|"):
                    rows.append(self.split_row(lines[j]))
                    j += 1
                out.append(self.table(head, rows))
                i = j
                continue

            # blockquote
            if stripped.startswith(">"):
                j = i
                buf = []
                while j < n and (
                    lines[j].strip().startswith(">") or
                    (lines[j].strip() and buf and not lines[j].strip().startswith("#"))
                ):
                    if not lines[j].strip().startswith(">"):
                        break
                    buf.append(re.sub(r"^\s*>\s?", "", lines[j]))
                    j += 1
                out.append(
                    '<blockquote class="bq">%s</blockquote>'
                    % "".join(self.render(buf, depth + 1))
                )
                i = j
                continue

            # footnote definition
            m = re.match(r"^\[\^(\d+)\]:\s*(.*)$", stripped)
            if m:
                num = m.group(1)
                buf = [m.group(2)]
                j = i + 1
                while j < n and lines[j].strip() and not self.is_block_start(lines[j]):
                    buf.append(lines[j].strip())
                    j += 1
                out.append(
                    '<aside class="footnote" id="fn-%s">'
                    '<span class="fn-n">%s</span>'
                    '<span class="fn-body">%s '
                    '<a class="fn-back" href="#fnref-%s">back</a></span></aside>'
                    % (num, num, self.inline.render(" ".join(buf)), num)
                )
                i = j
                continue

            # list
            if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
                block, i = self.collect_list(lines, i)
                out.append(block)
                continue

            # paragraph
            buf = []
            while i < n and lines[i].strip() and not self.is_block_start(lines[i]):
                buf.append(lines[i].strip())
                i += 1
            para = " ".join(buf)
            if self.inline.in_refs and para.startswith("**["):
                out.append(self.reference_entry(para))
            elif self.inline.in_refs and para.startswith("*Verification note.*"):
                out.append(self.verification_note(para))
            else:
                out.append("<p>%s</p>" % self.inline.render(para))
        return out

    # -- pieces ------------------------------------------------------------

    def figure(self, rel, caption):
        path = os.path.join(FIG_DIR, rel)
        if not os.path.isfile(path) or not rel.endswith(".svg"):
            die("figure directive references a missing SVG: %s (looked in %s)" % (rel, FIG_DIR))
        with io.open(path, "r", encoding="utf-8") as fh:
            svg = fh.read()
        svg = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", svg)
        # Drop fixed pixel dimensions so the viewBox drives responsive sizing.
        svg = re.sub(r"<svg\b([^>]*)>", lambda m: "<svg" + re.sub(
            r'\s(width|height)="[^"]*"', "", m.group(1)) + ' role="img">', svg, count=1)
        self.n_figures += 1
        fid = "fig-%d" % self.n_figures
        return (
            '<figure class="paperfig" id="%s"><div class="figbody">%s</div>'
            '<figcaption><span class="figlabel">Figure %d.</span> %s'
            '<a class="cap-anchor" href="#%s" aria-label="Link to this figure">#</a>'
            '<span class="figsrc">Source: ehs-osha-analysis/outputs/figures/%s</span>'
            "</figcaption></figure>"
            % (fid, svg, self.n_figures, self.inline.render(caption), fid, esc(rel))
        )

    def csv_table(self, rel, caption):
        path = os.path.join(TABLE_DIR, rel)
        if not os.path.isfile(path) or not rel.endswith(".csv"):
            die("table directive references a missing CSV: %s (looked in %s)" % (rel, TABLE_DIR))
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            die("table directive references an empty CSV: %s" % rel)
        head, body = rows[0], rows[1:]
        total = len(body)
        body = body[:TABLE_MAX_ROWS]
        self.n_tables += 1
        tid = "tbl-%d" % self.n_tables
        th = "".join("<th>%s</th>" % esc(h) for h in head)
        trs = "".join(
            "<tr>%s</tr>" % "".join("<td>%s</td>" % esc(self.fmt_cell(c)) for c in r)
            for r in body
        )
        note = ""
        if total > TABLE_MAX_ROWS:
            note = " Showing the first %d of %d rows." % (TABLE_MAX_ROWS, total)
        return (
            '<figure class="papertable" id="%s"><figcaption>'
            '<span class="figlabel">Table %d.</span> %s%s'
            '<a class="cap-anchor" href="#%s" aria-label="Link to this table">#</a>'
            '<span class="figsrc">Source: ehs-osha-analysis/outputs/tables/%s</span>'
            '</figcaption><div class="tablewrap"><table><thead><tr>%s</tr></thead>'
            "<tbody>%s</tbody></table></div></figure>"
            % (tid, self.n_tables, self.inline.render(caption), note, tid, esc(rel), th, trs)
        )

    @staticmethod
    def fmt_cell(c):
        """Round floats for display; leave everything else untouched."""
        try:
            v = float(c)
        except ValueError:
            return c
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        if abs(v) >= 1000:
            return "%.1f" % v
        return "%.4g" % v

    @staticmethod
    def is_block_start(line):
        s = line.strip()
        if not s:
            return True
        if DIRECTIVE_RE.match(s):
            return True
        if s.startswith("```") or s.startswith(">") or s.startswith("|"):
            return True
        if re.match(r"^#{1,6}\s", s):
            return True
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            return True
        if re.match(r"^\[\^\d+\]:", s):
            return True
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            return True
        return False

    @staticmethod
    def split_row(line):
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    def table(self, head, rows):
        th = "".join("<th>%s</th>" % self.inline.render(c) for c in head)
        body = []
        for r in rows:
            tds = "".join("<td>%s</td>" % self.inline.render(c) for c in r)
            body.append("<tr>%s</tr>" % tds)
        return (
            '<div class="tablewrap"><table><thead><tr>%s</tr></thead>'
            "<tbody>%s</tbody></table></div>" % (th, "".join(body))
        )

    def collect_list(self, lines, i):
        n = len(lines)
        ordered = bool(re.match(r"^\s*\d+\.\s+", lines[i]))
        base_indent = len(lines[i]) - len(lines[i].lstrip())
        items = []
        cur = None
        while i < n:
            line = lines[i]
            if not line.strip():
                # a blank line ends the list unless the next line continues it
                if i + 1 < n and re.match(r"^\s{%d,}\S" % (base_indent + 1), lines[i + 1]):
                    i += 1
                    continue
                break
            m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
            indent = len(line) - len(line.lstrip())
            if m and indent <= base_indent + 1:
                if cur is not None:
                    items.append(cur)
                cur = [m.group(3)]
                i += 1
                continue
            if cur is not None and (indent > base_indent or not self.is_block_start(line)):
                cur.append(line.strip())
                i += 1
                continue
            break
        if cur is not None:
            items.append(cur)
        tag = "ol" if ordered else "ul"
        body = "".join(
            "<li>%s</li>" % self.inline.render(" ".join(it)) for it in items
        )
        return "<%s class=\"md-list\">%s</%s>" % (tag, body, tag), i

    def reference_entry(self, para):
        m = re.match(r"^\*\*\[([a-z0-9_]+)\]\*\*\s*(.*)$", para)
        if not m:
            return "<p>%s</p>" % self.inline.render(para)
        key, text = m.group(1), m.group(2)
        rec = self.refs.get(key)
        evidence = (rec or {}).get("evidence", "")
        first_url = ""
        um = URL_RE.search(evidence or "")
        if um:
            first_url = clean_url(um.group(0))
        link = ""
        if first_url:
            link = (
                ' <a class="ref-ev" href="%s" rel="noopener noreferrer" '
                'target="_blank">evidence</a>' % html.escape(first_url, quote=True)
            )
        self.ref_entries.append(key)
        return (
            '<div class="ref" id="ref-%s">'
            '<div class="ref-key mono">%s</div>'
            '<div class="ref-body"><span class="ref-text">%s</span>%s'
            '<span class="backrefs" data-key="%s"></span></div>'
            "</div>" % (key, key, autolink(self.inline.render(text)), link, key)
        )

    def verification_note(self, para):
        body = para[len("*Verification note.*"):].strip()
        return (
            '<div class="ref-note"><span class="ref-note-k">Verification note</span>'
            "<span>%s</span></div>" % self.inline.render(body)
        )


# ------------------------------------------------------------------- page ---

CSS = u"""
:root{
 color-scheme:light;
 --paper:#F7F7F3; --surface:#FFFFFF; --surface-2:#EFEFE9;
 --ink:#101311; --ink-2:#3A403C; --muted:#666D68;
 --rule:#101311; --rule-soft:#D6D7CE;
 --accent:#1E40AF; --accent-2:#17307F; --accent-ink:#FFFFFF; --accent-wash:#E2E8FB;
 --warn:#8A5A00; --warn-wash:#FBF0DC;
 --grid-dot:rgba(16,19,17,.10); --shadow:rgba(16,19,17,.08);
 --font-sans:"Archivo",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
 --font-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
 --maxw:1180px;
}
@media (prefers-color-scheme: dark){
 :root:not([data-theme="light"]){
 color-scheme:dark;
 --paper:#0A0C10; --surface:#12151C; --surface-2:#171B24;
 --ink:#EAECF2; --ink-2:#BFC4CF; --muted:#838A99;
 --rule:#EAECF2; --rule-soft:#262B36;
 --accent:#7C9EFF; --accent-2:#5B7FE8; --accent-ink:#06101F; --accent-wash:#151C33;
 --warn:#E3B25F; --warn-wash:#241C0C;
 --grid-dot:rgba(234,236,242,.09); --shadow:rgba(0,0,0,.4);
 }
}
:root[data-theme="dark"]{
 color-scheme:dark;
 --paper:#0A0C10; --surface:#12151C; --surface-2:#171B24;
 --ink:#EAECF2; --ink-2:#BFC4CF; --muted:#838A99;
 --rule:#EAECF2; --rule-soft:#262B36;
 --accent:#7C9EFF; --accent-2:#5B7FE8; --accent-ink:#06101F; --accent-wash:#151C33;
 --warn:#E3B25F; --warn-wash:#241C0C;
 --grid-dot:rgba(234,236,242,.09); --shadow:rgba(0,0,0,.4);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-sans);font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased;overflow-x:hidden}
h1,h2,h3,h4,h5,h6{margin:0;line-height:1.1;letter-spacing:-.01em}
p{margin:0 0 1em}
a{color:var(--accent)}
img,svg{max-width:100%}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 30px}
.display{font-stretch:125%;font-weight:900;text-transform:uppercase}
.label{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:600}
.mono{font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.skip{position:absolute;left:-9999px;top:0;z-index:99;background:var(--accent);color:var(--accent-ink);padding:12px 18px;font-family:var(--font-mono);font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;text-decoration:none}
.skip:focus{left:8px;top:8px}

/* five-minute path */
.read5wrap{border-bottom:2px solid var(--rule);padding:0 0 34px}
.read5{border:2px solid var(--accent);background:var(--accent-wash);padding:22px 26px}
.read5 h2{font-family:var(--font-mono);font-size:.8125rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700}
.read5 p{margin:10px 0 0;font-size:.925rem;color:var(--ink-2);max-width:78ch}
.read5 ol{list-style:none;counter-reset:r5;margin:16px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:0;border:2px solid var(--rule);background:var(--surface)}
.read5 li{counter-increment:r5;border-left:2px solid var(--rule-soft);min-width:0}
.read5 li:first-child{border-left:0}
.read5 li a{display:block;height:100%;padding:12px 14px;text-decoration:none;color:var(--ink)}
.read5 li a:hover{background:var(--accent);color:var(--accent-ink)}
.read5 li a::before{content:"0" counter(r5);display:block;font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.16em;color:var(--muted);margin-bottom:4px}
.read5 li a:hover::before{color:var(--accent-ink)}
.read5 .r5-t{display:block;font-family:var(--font-mono);font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.read5 .r5-d{display:block;font-size:.8125rem;margin-top:4px;color:var(--ink-2)}
.read5 li a:hover .r5-d{color:var(--accent-ink)}
@media(max-width:760px){.read5 li{border-left:0;border-top:2px solid var(--rule-soft)}.read5 li:first-child{border-top:0}}

/* previous / next */
.pn{border-top:2px solid var(--rule)}
.pn-inner{max-width:var(--maxw);margin:0 auto;padding:0 30px;display:grid;grid-template-columns:1fr 1fr}
.pn a{display:block;padding:26px 0;text-decoration:none;color:var(--ink);min-width:0}
.pn a+a{text-align:right;border-left:2px solid var(--rule-soft);padding-left:20px}
.pn .pn-k{display:block;font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:700}
.pn .pn-v{display:block;margin-top:6px;font-family:var(--font-mono);font-size:.9rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--accent)}
.pn a:hover .pn-v{text-decoration:underline}
@media(max-width:560px){.pn-inner{grid-template-columns:1fr}.pn a+a{border-left:0;border-top:2px solid var(--rule-soft);padding-left:0;text-align:left}}

/* hero */
.phero{border-bottom:2px solid var(--rule);background-image:radial-gradient(var(--grid-dot) 1px,transparent 1px);background-size:22px 22px;padding:64px 0 52px}
.phero .kicker{display:inline-flex;align-items:center;gap:9px;margin-bottom:22px}
.pulse{width:7px;height:7px;background:var(--accent);flex:none;animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .pulse{animation:none}
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
}
.phero h1{font-size:clamp(1.6rem,4.4vw,3.35rem);max-width:22ch;line-height:1.04;overflow-wrap:break-word}
.phero .byline{margin-top:22px;font-family:var(--font-mono);font-size:.8125rem;letter-spacing:.06em;text-transform:uppercase;font-weight:600;color:var(--ink-2)}
.phero .sub{margin-top:16px;font-size:1.02rem;color:var(--ink-2);max-width:66ch}
.metastrip{display:grid;grid-template-columns:repeat(4,1fr);border:2px solid var(--rule);background:var(--surface);margin-top:32px;max-width:820px}
.ms-cell{padding:13px 16px;border-left:2px solid var(--rule-soft);min-width:0}
.ms-cell:first-child{border-left:0}
.ms-k{font-family:var(--font-mono);font-size:.5625rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:4px}
.ms-v{font-family:var(--font-mono);font-size:1rem;font-weight:700;font-variant-numeric:tabular-nums}
.ms-v.accent{color:var(--accent)}
@media(max-width:760px){.metastrip{grid-template-columns:1fr 1fr}.ms-cell:nth-child(3){border-left:0}.ms-cell:nth-child(n+3){border-top:2px solid var(--rule-soft)}}

/* status banner */
.statuswrap{border-bottom:2px solid var(--rule);padding:34px 0}
.status-note{border:2px solid var(--warn);border-left-width:8px;background:var(--warn-wash);padding:24px 26px}
.status-note h2{font-family:var(--font-mono);font-size:.8125rem;letter-spacing:.12em;text-transform:uppercase;color:var(--warn);font-weight:700}
.status-note p{margin-top:14px;font-size:.925rem;color:var(--ink-2);max-width:78ch}
.status-note ul{margin:14px 0 0;padding-left:20px;font-size:.9rem;color:var(--ink-2);max-width:78ch}
.status-note li{margin-bottom:8px}
.status-note strong{color:var(--ink)}

/* cite panel */
.citewrap{border-bottom:2px solid var(--rule);padding:34px 0}
.cite-panel{border:2px solid var(--rule);background:var(--surface);padding:24px 26px}
.cite-panel h2{font-family:var(--font-mono);font-size:.8125rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink);font-weight:700}
.cite-panel > p{margin-top:10px;font-size:.875rem;color:var(--muted);max-width:78ch}
.cite-blocks{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
.cite-block{border:1px solid var(--rule-soft);background:var(--surface-2);min-width:0}
.cite-block-head{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--rule-soft)}
.cite-fmt{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:var(--muted)}
.copy-btn{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;background:var(--surface);color:var(--accent);border:1px solid var(--accent);padding:5px 10px;cursor:pointer;min-height:28px}
.copy-btn:hover{background:var(--accent);color:var(--paper)}
.copy-btn[data-copied="true"]{background:var(--accent);color:var(--paper)}
.cite-code{margin:0;padding:12px;font-family:var(--font-mono);font-size:.75rem;line-height:1.6;color:var(--ink-2);white-space:pre-wrap;overflow-wrap:anywhere;max-height:220px;overflow-y:auto}
@media(max-width:760px){.cite-blocks{grid-template-columns:1fr}}

/* figure / table caption anchors */
.cap-anchor{margin-left:.45em;text-decoration:none;color:var(--rule-soft);font-family:var(--font-mono);font-weight:400;font-size:.85em}
.paperfig figcaption:hover .cap-anchor,.papertable figcaption:hover .cap-anchor{color:var(--accent)}
.paperfig:target,.papertable:target{outline:2px solid var(--accent);outline-offset:6px}

/* layout */
.layout{max-width:var(--maxw);margin:0 auto;padding:0 30px;display:grid;grid-template-columns:264px minmax(0,1fr);gap:0;align-items:start}
.toc-rail{position:sticky;top:calc(var(--hdr-h,56px) + 24px);max-height:calc(100vh - var(--hdr-h,56px) - 48px);overflow-y:auto;padding:34px 26px 40px 0;border-right:2px solid var(--rule-soft);scrollbar-width:thin}
.toc-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.toc-title{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);font-weight:700}
.toc-toggle{display:none;background:var(--surface);border:2px solid var(--rule);color:var(--ink);cursor:pointer;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;padding:7px 11px}
.toc-list{list-style:none;margin:16px 0 0;padding:0}
.toc-list li{margin:0}
.toc-list a{display:block;text-decoration:none;font-family:var(--font-mono);font-size:.72rem;line-height:1.4;color:var(--muted);padding:5px 0 5px 10px;border-left:2px solid transparent}
.toc-list a:hover{color:var(--ink)}
.toc-list a[aria-current="true"]{color:var(--accent);border-left-color:var(--accent);font-weight:600}
.toc-list .lvl-1 a{color:var(--ink-2);font-weight:700;margin-top:10px;text-transform:uppercase;letter-spacing:.06em;font-size:.6875rem;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.toc-min{flex:none;font-weight:400;font-size:.5625rem;letter-spacing:.1em;color:var(--muted);text-transform:uppercase}
.toc-list .lvl-3 a{padding-left:22px;font-size:.6875rem;opacity:.86}

/* article */
.doc{padding:40px 0 80px 40px;min-width:0;position:relative}
.doc > *{max-width:68ch}
.doc p,.doc li{font-size:1.0125rem;line-height:1.78;color:var(--ink-2);overflow-wrap:break-word}
.doc strong{color:var(--ink)}
.doc .h-l1{font-size:clamp(1.5rem,3.4vw,2.15rem);margin:76px 0 22px;padding-top:26px;border-top:2px solid var(--rule);font-stretch:125%;font-weight:900;text-transform:uppercase;color:var(--ink)}
.doc .h-l2{font-size:clamp(1.16rem,2.2vw,1.42rem);margin:52px 0 16px;font-weight:800;color:var(--ink)}
.doc .h-l3{font-size:1.02rem;margin:38px 0 12px;font-family:var(--font-mono);font-weight:700;letter-spacing:-.01em;color:var(--ink)}
.doc > :first-child{margin-top:0}
.anchor{margin-left:.5em;text-decoration:none;color:var(--rule-soft);font-family:var(--font-mono);font-weight:400;font-size:.7em;opacity:0}
h2:hover .anchor,h3:hover .anchor,h4:hover .anchor{opacity:1}
.rule{border:0;border-top:2px solid var(--rule-soft);margin:44px 0;max-width:68ch}
.md-list{margin:0 0 1.3em;padding-left:22px}
.md-list li{margin-bottom:.65em}
.doc code{font-family:var(--font-mono);font-size:.86em;background:var(--surface-2);padding:.1em .34em;border:1px solid var(--rule-soft);color:var(--ink)}
.codewrap{max-width:100%;overflow-x:auto;border:2px solid var(--rule-soft);background:var(--surface);margin:0 0 1.5em}
.codewrap pre{margin:0;padding:18px 20px;width:max-content;min-width:100%}
.codewrap code{font-family:var(--font-mono);font-size:.8125rem;line-height:1.7;background:none;border:0;padding:0;white-space:pre;color:var(--ink-2)}
.bq{margin:0 0 1.5em;padding:18px 22px;border-left:4px solid var(--accent);background:var(--surface-2);max-width:68ch}
.bq > :last-child{margin-bottom:0}
.bq p{font-size:.97rem}
.paperfig,.papertable{margin:0 0 2em;padding:0;max-width:100%}
.figbody{border:2px solid var(--rule);background:#fff;padding:10px;overflow-x:auto}
.figbody svg{display:block;width:100%;height:auto;max-width:820px;margin:0 auto}
:root[data-theme="dark"] .figbody{background:#fff;filter:invert(1) hue-rotate(180deg)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .figbody{background:#fff;filter:invert(1) hue-rotate(180deg)}}
.paperfig figcaption,.papertable figcaption{font-size:.9rem;line-height:1.55;color:var(--ink-2);margin:.7em 0 0;max-width:68ch}
.papertable figcaption{margin:0 0 .7em}
.figlabel{font-family:var(--font-mono);font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;font-weight:700;color:var(--ink);margin-right:.5em}
.figsrc{display:block;font-family:var(--font-mono);font-size:.7rem;color:var(--muted);margin-top:.3em;opacity:.8}
.papertable .tablewrap{margin:0}
.tablewrap{max-width:100%;overflow-x:auto;border:2px solid var(--rule);background:var(--surface);margin:0 0 1.7em}
.tablewrap table{border-collapse:collapse;width:100%;min-width:640px}
.tablewrap th,.tablewrap td{text-align:left;vertical-align:top;padding:11px 14px;border-bottom:1px solid var(--rule-soft);border-right:1px solid var(--rule-soft);font-size:.8125rem;line-height:1.55;color:var(--ink-2)}
.tablewrap th{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink);font-weight:700;border-bottom:2px solid var(--rule);background:var(--surface-2)}
.tablewrap tr:last-child td{border-bottom:0}
.tablewrap th:last-child,.tablewrap td:last-child{border-right:0}

/* citations */
sup.cite{font-family:var(--font-mono);font-size:.62em;line-height:0;letter-spacing:.01em;vertical-align:super}
sup.cite a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent;white-space:nowrap}
sup.cite a:hover{border-bottom-color:var(--accent)}
sup.fnref{font-family:var(--font-mono);font-size:.66em}
sup.fnref a{text-decoration:none;cursor:pointer}
.footnote{display:flex;gap:12px;max-width:68ch;margin:0 0 1.5em;padding:14px 16px;border-left:2px solid var(--rule-soft);background:var(--surface-2)}
.fn-n{font-family:var(--font-mono);font-size:.6875rem;font-weight:700;color:var(--accent);flex:none;padding-top:.15em}
.fn-body{font-size:.875rem;line-height:1.66;color:var(--ink-2)}
.fn-back{font-family:var(--font-mono);font-size:.625rem;text-transform:uppercase;letter-spacing:.1em;text-decoration:none;margin-left:6px}
/* sidenotes: on wide screens, footnotes move into the doc's own right
   margin (JS positions them level with their reference mark). On narrow
   screens they stay inline but collapsed, toggled open by the marker. */
@media(min-width:1280px){
 .footnote.sidenote{position:absolute;left:calc(68ch + 30px);width:210px;max-width:210px;margin:0;padding:10px 12px;font-size:.8rem;display:block}
 .footnote.sidenote .fn-n{display:inline;margin-right:6px}
 .footnote.sidenote .fn-body{font-size:.8rem;line-height:1.6}
 .footnote.sidenote .fn-back{display:none}
}
.footnote.fn-collapsed{display:none}
.footnote.fn-collapsed.fn-open{display:flex}

/* references */
.ref{display:grid;grid-template-columns:170px minmax(0,1fr);gap:0 18px;max-width:68ch;padding:16px 0 4px;border-top:1px solid var(--rule-soft)}
.ref:target{background:var(--accent-wash);border-top-color:var(--accent)}
.ref-key{font-size:.72rem;font-weight:700;color:var(--accent);word-break:break-word;padding-top:.18em}
.ref-body{font-size:.9rem;line-height:1.66;color:var(--ink-2);min-width:0;overflow-wrap:anywhere;word-break:break-word}
.ref-ev{font-family:var(--font-mono);font-size:.625rem;text-transform:uppercase;letter-spacing:.1em;text-decoration:none;margin-left:8px;border-bottom:1px solid var(--accent)}
.backrefs{display:inline}
.backrefs a{font-family:var(--font-mono);font-size:.625rem;text-decoration:none;margin-left:5px;color:var(--muted);border-bottom:1px solid var(--rule-soft)}
.backrefs a:hover{color:var(--accent);border-bottom-color:var(--accent)}
.backrefs .brlabel{font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-left:10px}
.ref-note{display:block;max-width:68ch;margin:0 0 6px;padding:10px 14px 10px 188px;font-size:.8125rem;line-height:1.6;color:var(--muted);overflow-wrap:anywhere}
.ref-note-k{display:block;font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:4px}

/* footer */
.footer{border-top:2px solid var(--rule);padding:48px 0 64px;background:var(--surface-2)}
.footer p{font-size:.875rem;color:var(--muted);max-width:68ch}
.footer-links{display:flex;flex-wrap:wrap;gap:18px;margin-top:16px}
.footer-links a{font-family:var(--font-mono);font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;text-decoration:none;color:var(--muted)}
.footer-links a:hover{color:var(--accent)}

/* narrow */
@media (max-width:1024px){
 .layout{grid-template-columns:minmax(0,1fr);padding:0 20px}
 .toc-rail{position:static;max-height:none;overflow:visible;border-right:0;border-bottom:2px solid var(--rule);padding:20px 0}
 .toc-toggle{display:inline-block}
 .toc-rail[data-collapsed="true"] .toc-list{display:none}
 .toc-list{max-height:52vh;overflow-y:auto}
 .doc{padding:34px 0 64px;overflow-wrap:anywhere}
 .doc svg{max-width:100%;height:auto}
 .tablewrap table{display:table}
 .wrap{padding:0 20px}
   .ref{grid-template-columns:minmax(0,1fr);gap:4px}
 .ref-note{padding-left:14px}
}
@media (max-width:560px){
 .phero{padding:44px 0 38px}
 .doc .h-l1{margin-top:52px}
}

/* print */
@media print{
 :root{--paper:#fff;--surface:#fff;--surface-2:#fff;--ink:#000;--ink-2:#111;--muted:#444;--rule:#000;--rule-soft:#bbb;--accent:#000;--accent-wash:#fff;--warn:#000;--warn-wash:#fff;--grid-dot:transparent}
 .toc-rail,.anchor,.footer-links,.skip,.ref-ev,.backrefs,.pn,.read5wrap{display:none !important}
 body{font-size:10.5pt;line-height:1.5;background:#fff;color:#000}
 .layout{display:block;max-width:none;padding:0}
 .doc{padding:0;max-width:none}
 .doc > *{max-width:none}
 .phero{border-bottom:1pt solid #000;padding:0 0 12pt;background:none}
 .metastrip{max-width:none}
 .doc .h-l1{page-break-before:always;page-break-after:avoid;border-top:1pt solid #000}
 .doc > .h-l1:first-child{page-break-before:avoid;border-top:0}
 .doc .h-l2,.doc .h-l3{page-break-after:avoid}
 .ref,.footnote,.bq,.tablewrap,.codewrap{page-break-inside:avoid}
 .tablewrap table{min-width:0}
 sup.cite{font-size:.7em}
 a{color:#000;text-decoration:none}
 @page{margin:18mm 16mm}
}
"""

PAPER_SECTIONS = [("read5", "Summary"), ("abstract", "Abstract"), ("cite-this", "Cite"), ("references", "References")]

JS = u"""
/* back-links on each reference, built from the citation anchors in the body */
(function(){
  var holders=document.querySelectorAll('.backrefs');
  Array.prototype.forEach.call(holders,function(h){
    var key=h.getAttribute('data-key');
    var sites=document.querySelectorAll('sup.cite a[href="#ref-'+key+'"]');
    if(!sites.length)return;
    var lab=document.createElement('span');
    lab.className='brlabel';lab.textContent='cited at';
    h.appendChild(lab);
    Array.prototype.forEach.call(sites,function(a,i){
      var b=document.createElement('a');
      b.href='#'+a.id;b.textContent=String(i+1);
      b.setAttribute('aria-label','Back to citation '+(i+1)+' of '+key);
      h.appendChild(b);
    });
  });
})();

/* keep the contents rail under the shared site header, whatever height it has */
(function(){
  var hd=document.getElementById('rs-header');
  if(!hd)return;
  function sync(){document.documentElement.style.setProperty('--hdr-h',hd.offsetHeight+'px');}
  sync();
  if('ResizeObserver' in window)new ResizeObserver(sync).observe(hd);else window.addEventListener('resize',sync);
})();

/* collapse the contents rail on narrow screens */
(function(){
  var rail=document.getElementById('tocRail'),btn=document.getElementById('tocToggle');
  if(!rail||!btn)return;
  var mq=window.matchMedia('(max-width:1024px)');
  function sync(){
    if(mq.matches){rail.setAttribute('data-collapsed','true');btn.setAttribute('aria-expanded','false');btn.textContent='Contents';}
    else{rail.removeAttribute('data-collapsed');btn.setAttribute('aria-expanded','true');}
  }
  btn.addEventListener('click',function(){
    var closed=rail.getAttribute('data-collapsed')==='true';
    if(closed){rail.removeAttribute('data-collapsed');btn.setAttribute('aria-expanded','true');btn.textContent='Hide';}
    else{rail.setAttribute('data-collapsed','true');btn.setAttribute('aria-expanded','false');btn.textContent='Contents';}
  });
  if(mq.addEventListener)mq.addEventListener('change',sync);else if(mq.addListener)mq.addListener(sync);
  window.addEventListener('resize',sync);
  sync();
})();

/* highlight the section being read: the last heading above the read line */
(function(){
  var links=Array.prototype.slice.call(document.querySelectorAll('.toc-list a'));
  var rail=document.getElementById('tocRail');
  var items=[];
  links.forEach(function(a){
    var el=document.getElementById(a.getAttribute('href').slice(1));
    if(el)items.push({a:a,el:el,top:0});
  });
  if(!items.length)return;
  var current=null,raf=false;
  function measure(){
    var y=window.pageYOffset||document.documentElement.scrollTop;
    items.forEach(function(it){it.top=it.el.getBoundingClientRect().top+y;});
  }
  function paint(){
    raf=false;
    var line=(window.pageYOffset||document.documentElement.scrollTop)+150;
    var best=items[0];
    for(var i=0;i<items.length;i++){ if(items[i].top<=line)best=items[i]; else break; }
    if(best===current)return;
    if(current)current.a.removeAttribute('aria-current');
    current=best;
    current.a.setAttribute('aria-current','true');
    if(rail&&!rail.hasAttribute('data-collapsed')&&rail.scrollHeight>rail.clientHeight+4){
      var want=current.a.offsetTop-rail.clientHeight/2;
      rail.scrollTop=want>0?want:0;
    }
  }
  function schedule(){if(!raf){raf=true;requestAnimationFrame(paint);}}
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',function(){measure();schedule();});
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(function(){measure();schedule();});
  measure();paint();
})();

/* footnotes: true sidenotes on wide screens (positioned level with their
   in-text marker), collapsed inline toggles on narrow screens */
(function(){
  var refs=Array.prototype.slice.call(document.querySelectorAll('sup.fnref a'));
  if(!refs.length)return;
  var pairs=[];
  refs.forEach(function(a){
    var id=(a.getAttribute('href')||'').replace('#fn-','');
    var note=document.getElementById('fn-'+id);
    if(note)pairs.push({marker:a,note:note});
  });
  if(!pairs.length)return;
  var doc=document.getElementById('doc');
  var mq=window.matchMedia('(min-width:1280px)');
  function positionWide(){
    var docTop=doc.getBoundingClientRect().top+window.pageYOffset;
    pairs.forEach(function(p){
      var y=p.marker.getBoundingClientRect().top+window.pageYOffset-docTop;
      p.note.style.top=Math.max(0,y-4)+'px';
    });
  }
  function sync(){
    if(mq.matches){
      pairs.forEach(function(p){
        p.note.classList.add('sidenote');
        p.note.classList.remove('fn-collapsed','fn-open');
      });
      positionWide();
    }else{
      pairs.forEach(function(p){
        p.note.classList.remove('sidenote');
        p.note.style.top='';
        p.note.classList.add('fn-collapsed');
      });
    }
  }
  pairs.forEach(function(p){
    p.marker.addEventListener('click',function(ev){
      if(mq.matches)return;
      ev.preventDefault();
      var open=p.note.classList.toggle('fn-open');
      p.marker.setAttribute('aria-expanded',open?'true':'false');
      if(open)p.note.scrollIntoView({block:'nearest'});
    });
    p.marker.setAttribute('aria-expanded','false');
  });
  var raf=false;
  function schedule(){if(!raf){raf=true;requestAnimationFrame(function(){raf=false;if(mq.matches)positionWide();});}}
  window.addEventListener('resize',function(){sync();});
  window.addEventListener('scroll',schedule,{passive:true});
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(sync);
  sync();
})();

/* copy-to-clipboard for the Cite this panel */
(function(){
  var btns=document.querySelectorAll('.copy-btn[data-copy-target]');
  if(!btns.length)return;
  Array.prototype.forEach.call(btns,function(btn){
    btn.addEventListener('click',function(){
      var target=document.getElementById(btn.getAttribute('data-copy-target'));
      if(!target)return;
      var text=target.textContent;
      var done=function(){
        var prev=btn.textContent;
        btn.textContent='Copied';
        btn.setAttribute('data-copied','true');
        setTimeout(function(){btn.textContent=prev;btn.removeAttribute('data-copied');},1600);
      };
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(done,done);
      }else{
        try{
          var ta=document.createElement('textarea');
          ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
          document.body.appendChild(ta);ta.focus();ta.select();
          document.execCommand('copy');document.body.removeChild(ta);
        }catch(e){}
        done();
      }
    });
  });
})();
"""

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'"
    "%3E%3Crect width='16' height='16' fill='%231E40AF'/%3E%3Ctext x='8' y='12' "
    "font-family='monospace' font-size='11' font-weight='700' text-anchor='middle' "
    "fill='white'%3EP%3C/text%3E%3C/svg%3E"
)


WORDS_PER_MIN = 230


def section_minutes(lines):
    """Estimated reading time per top-level section, keyed by heading slug.
    Counts words from each '# ' heading to the next one."""
    counts = {}
    key = None
    for l in lines:
        m = re.match(r"^# (\S.*)$", l)
        if m:
            key = slug(m.group(1))
            counts.setdefault(key, 0)
            continue
        if key is not None and not l.startswith("<!--"):
            counts[key] += len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", l))
    return dict((k, max(1, int(round(v / float(WORDS_PER_MIN)))))
                for k, v in counts.items())


def build_toc(entries, minutes):
    out = ['<ul class="toc-list">']
    for level, hid, text in entries:
        extra = ""
        if level == 1 and hid in minutes and hid != "references":
            extra = ('<span class="toc-min" aria-label="about %d minutes">%d min</span>'
                     % (minutes[hid], minutes[hid]))
        out.append(
            '<li class="lvl-%d"><a href="#%s">%s%s</a></li>' % (level, hid, text, extra)
        )
    out.append("</ul>")
    return "".join(out)


# Five-minute path per source document
READ5_MAP = {
    "PAPER.md": [
        ("abstract", "Abstract", "The whole argument in one page."),
        ("1-3-contributions", "Contributions", "The four artifacts and what each one claims."),
        ("6-data-foundations", "The data-quality result", "The one empirical result: 2,801,064 OSHA establishment filings and the exposure denominator under every rate-based metric."),
        ("7-discussion-and-limitations", "Limitations", "What this draft does not show, in the authors' own words."),
    ],
    "OSHA_PAPER.md": [
        ("abstract", "Abstract", "The problem: OSHA rate metrics depend on a denominator that does not exist in the data."),
        ("2-data-and-reproducibility", "Data and reproducibility", "The dataset: 2,801,064 OSHA establishment filings with reproducible analysis."),
        ("5-the-denominator-failure", "The denominator failure", "The main finding: the hours denominator does not replicate across standard benchmarks."),
        ("11-why-the-hours-fail-implausible-reporting-is-a-property-of-establishments-not-of-filings", "Why hours fail", "The persistence: implausible reporting is a property of establishments, not noise in filings."),
        ("limitations", "Limitations", "What this analysis does not show, in the authors' own words."),
    ],
}


def read5_box(toc):
    src_basename = os.path.basename(SRC_MD)
    READ5 = READ5_MAP.get(src_basename, READ5_MAP["PAPER.md"])
    if os.environ.get("PAPER_READ5"):
        import json as _json
        READ5 = [tuple(x) for x in _json.loads(os.environ["PAPER_READ5"])]
    ids = set(hid for _, hid, _ in toc)
    missing = [hid for hid, _, _ in READ5 if hid not in ids]
    if missing:
        die("five-minute path points at headings that do not exist: %s" % ", ".join(missing))
    items = "".join(
        '<li><a href="#%s"><span class="r5-t">%s</span><span class="r5-d">%s</span></a></li>'
        % (hid, esc(t), esc(d)) for hid, t, d in READ5
    )
    return u'''<section class="read5wrap" id="read5"><div class="wrap">
<div class="read5">
<h2>Read this in 5 minutes</h2>
<p>The full manuscript is a long read. These four stops give the finding, the claims,
the one empirical result, and the caveats. Each section heading in the contents rail
carries its own estimated reading time.</p>
<ol>%s</ol>
</div>
</div></section>''' % items


def load_citation_cff():
    """Minimal, dependency-free reader for the handful of flat fields this
    page needs from CITATION.cff. Not a general YAML parser."""
    if not os.path.isfile(CITATION_CFF):
        return None
    text = io.open(CITATION_CFF, encoding="utf-8").read()

    def field(key):
        m = re.search(r'^%s:\s*"?([^"\n]+)"?\s*$' % re.escape(key), text, re.M)
        return m.group(1).strip() if m else ""

    given = re.search(r"^\s*-?\s*given-names:\s*(.+)$", text, re.M)
    family = re.search(r"^\s*-?\s*family-names:\s*(.+)$", text, re.M)
    return {
        "given": given.group(1).strip() if given else "",
        "family": family.group(1).strip() if family else "",
        "url": field("url"),
        "date": field("date-released"),
    }


def cite_panel(full_title, out_basename):
    """A 'Cite this' panel: BibTeX and APA built from CITATION.cff plus the
    manuscript title, each with a copy button. Skipped silently if the CFF
    file is missing so a build never fails on it."""
    cff = load_citation_cff()
    if not cff or not cff["family"]:
        return ""
    year = (cff["date"] or "2026")[:4]
    given, family = cff["given"], cff["family"]
    page_url = "https://priyatham9.github.io/grounded/" + out_basename
    bib_key = (slug(full_title).split("-")[0] or "grounded") + year
    initial = (given[:1] + ".") if given else ""

    bibtex = (
        "@misc{%s,\n"
        "  author       = {%s, %s},\n"
        "  title        = {%s},\n"
        "  year         = {%s},\n"
        "  howpublished = {\\url{%s}},\n"
        "  note         = {Working draft, not peer reviewed}\n"
        "}"
    ) % (bib_key, family, given, full_title, year, page_url)

    apa = "%s, %s (%s). %s. Working draft, not peer reviewed. %s" % (
        family, initial, year, full_title, page_url
    )

    return u"""<section class="citewrap" id="cite-this"><div class="wrap">
<div class="cite-panel">
<h2>Cite this</h2>
<p>A working draft, not peer reviewed. Cite the manuscript itself, not a
finished result.</p>
<div class="cite-blocks">
<div class="cite-block">
<div class="cite-block-head"><span class="cite-fmt">BibTeX</span>
<button type="button" class="copy-btn" data-copy-target="cite-bibtex">Copy</button></div>
<pre class="cite-code" id="cite-bibtex">%s</pre>
</div>
<div class="cite-block">
<div class="cite-block-head"><span class="cite-fmt">APA</span>
<button type="button" class="copy-btn" data-copy-target="cite-apa">Copy</button></div>
<pre class="cite-code" id="cite-apa">%s</pre>
</div>
</div>
</div>
</div></section>""" % (esc(bibtex), esc(apa))


def status_banner(n_refs, n_notes, n_words):
    return u"""<section class="statuswrap"><div class="wrap">
<div class="status-note">
<h2>Read this first: what this document is and is not</h2>
<p>This is a <strong>working draft</strong>. It has not been submitted to any venue,
it has not been peer reviewed, and nothing in it should be read as a validated
result about any deployed system.</p>
<ul>
<li><strong>The benchmark has no baseline results.</strong> Section 5 describes a
preregistered apparatus of 68 clause-anchored items. The harness has been exercised
only against a mock adapter with a synthetic response profile. No model has been
evaluated. Any number attributed to it would be wrong.</li>
<li><strong>Four of five internal adversarial reviewers would reject this manuscript
as structured</strong> - mainly for bundling four separable contributions into one
paper, and for presenting an evaluation benchmark with no baselines. The
formal-methods reviewer did not reject. That review is reported here rather than
buried.</li>
<li><strong>The ontology's factor levels are analyst-assigned.</strong> The 90
crosswalk alignments are one coder's unadjudicated judgement, with no inter-rater
reliability figure. The screening bands are ordinal labels produced by rules marked
as convention, never validated against injury or incident outcomes.</li>
<li><strong>The simulation studies are synthetic by design.</strong> They demonstrate
properties of an estimator. They are not findings about workplace safety.</li>
<li><strong>The OSHA reanalysis is the one empirical result here.</strong> It runs on
2,801,064 real establishment filings and its numbers are reproducible from the
committed pipeline. The correction factor it reports is explicitly not a portable
constant.</li>
<li><strong>Citations.</strong> All %d citation keys used in the text resolve to a
reference below, each checked against a primary or publisher-of-record source, with
the evidence URL recorded in the repository. %d entries carry a verification note
saying what that check found, including the ones where a page range still needs
confirming against printed proceedings.</li>
</ul>
</div>
</div></section>""" % (n_refs, n_notes)


def build():
    if not os.path.exists(SRC_MD):
        die("cannot find %s" % SRC_MD)
    if not os.path.exists(SRC_JSON):
        die("cannot find %s" % SRC_JSON)

    md = io.open(SRC_MD, encoding="utf-8").read()
    refs = json.load(io.open(SRC_JSON, encoding="utf-8"))

    if EM_DASH in md:
        die("PAPER.md still contains em dashes; fix the source, not the output")

    lines = md.split("\n")

    # Front matter: short title, byline, the draft blockquote, then the full
    # title as the second H1. Everything after that H1 is the body.
    h1s = [i for i, l in enumerate(lines) if re.match(r"^# \S", l)]
    if len(h1s) < 2:
        die("expected two leading H1 lines in PAPER.md")
    full_title = lines[h1s[1]][2:].strip()
    byline = ""
    for l in lines[h1s[0] + 1:h1s[1]]:
        if l.strip() and not l.strip().startswith(">"):
            byline = l.strip()
            break
    body_lines = lines[h1s[1] + 1:]

    r = Renderer(refs)
    blocks = r.render(body_lines)
    article = "\n".join(blocks)

    # Word count is the manuscript only. The References section, with its
    # verification notes, is a large apparatus and would inflate the figure.
    manuscript = md.split("<!-- BEGIN GENERATED REFERENCES -->")[0]
    n_words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", manuscript))
    n_refs = len(r.ref_entries)
    n_notes = article.count('class="ref-note"')

    if n_refs == 0:
        die("no reference entries were rendered; is the References section present?")

    dangling = sorted(set(r.inline.counts) - set(r.ref_entries))
    if dangling:
        die("cited keys with no reference entry: %s" % ", ".join(dangling))

    subtitle = (
        "A working draft. Four artifacts: a structural account of semantically "
        "adjacent substitution, an auditable human-factors ontology, a preregistered "
        "grounding benchmark, and a population-scale reanalysis of the exposure "
        "denominator underlying every rate-based safety metric."
    )

    page = u"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>%(title_short)s - Paper - Priyatham Chimmani</title>
<meta name="description" content="Working draft. %(desc)s" />
<link rel="canonical" href="%(pageurl)s" />
<meta property="og:title" content="%(title_short)s - Paper - Priyatham Chimmani" />
<meta property="og:description" content="Working draft. %(desc)s" />
<meta property="og:type" content="article" />
<meta property="og:url" content="%(pageurl)s" />
<meta property="og:image" content="%(ogimage)s" />
<meta property="og:site_name" content="Grounded" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title_short)s - Paper - Priyatham Chimmani" />
<meta name="twitter:description" content="Working draft. %(desc)s" />
<meta name="twitter:image" content="%(ogimage)s" />
<script type="application/ld+json">%(ldjson)s</script>
<meta name="theme-color" content="#F7F7F3" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0A0C10" media="(prefers-color-scheme: dark)" />
<link rel="icon" href="%(favicon)s" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" />
<style>%(css)s</style>
</head>
<body id="top">

<a class="skip" href="#doc">Skip to the paper</a>


<section class="phero"><div class="wrap">
  <div class="kicker"><span class="pulse"></span><span class="label">Draft manuscript - not submitted</span></div>
  <h1 class="display">%(title_full)s</h1>
  <div class="byline">%(byline)s</div>
  <p class="sub">%(subtitle)s</p>
  <div class="metastrip">
    <div class="ms-cell"><span class="ms-k">Manuscript</span><span class="ms-v">%(words)s</span></div>
    <div class="ms-cell"><span class="ms-k">References</span><span class="ms-v accent">%(nrefs)d</span></div>
    <div class="ms-cell"><span class="ms-k">Benchmark results</span><span class="ms-v">None</span></div>
    <div class="ms-cell"><span class="ms-k">Peer review</span><span class="ms-v">None</span></div>
  </div>
</div></section>

%(status)s

%(cite)s

%(read5)s

<main class="layout">
  <aside class="toc-rail" id="tocRail" aria-label="Table of contents">
    <div class="toc-head">
      <span class="toc-title">Contents</span>
      <button class="toc-toggle" id="tocToggle" aria-expanded="true">Contents</button>
    </div>
    %(toc)s
  </aside>

  <article class="doc" id="doc">
%(article)s
  </article>
</main>

<nav class="pn" aria-label="Previous and next">
  <div class="pn-inner">
    <a href="index.html"><span class="pn-k">&larr; Previous</span><span class="pn-v">Research hub</span></a>
    <a href="https://priyatham9.github.io/ehs-osha-analysis/"><span class="pn-k">Next &rarr;</span><span class="pn-v">OSHA data quality &#x2197;</span></a>
  </div>
</nav>

<footer class="footer"><div class="wrap">
  <p>Generated from <code>paper/PAPER.md</code> by <code>tools/build_paper.py</code>.
  Edit the Markdown and rerun the script; do not edit this file by hand.
  Every reference below was checked against a primary or publisher-of-record source,
  and the evidence URL for each check lives in <code>paper/citations_verified.json</code>.</p>
  <div class="footer-links">
    <a href="https://priyatham9.github.io/">Priyatham Chimmani</a>
    <a href="index.html">Research hub</a>
    <a href="#top">Back to top</a>
    <a href="#references">References</a>
  </div>
</div></footer>

<script>%(js)s</script>
</body>
</html>
""" % {
        "title_short": os.environ.get("PAPER_TITLE_SHORT") or "Grounded Reasoning for Safety-Critical AI",
        "pageurl": "https://priyatham9.github.io/grounded/" + os.path.basename(OUT_HTML),
        "ogimage": "https://priyatham9.github.io/grounded/" + (
            "og-paper-osha.png" if os.path.basename(OUT_HTML) == "paper-osha.html" else "og-paper.png"),
        "ldjson": json.dumps({
            "@context": "https://schema.org",
            "@type": "ScholarlyArticle",
            "headline": os.environ.get("PAPER_TITLE_SHORT") or "Grounded Reasoning for Safety-Critical AI",
            "description": subtitle if os.path.basename(OUT_HTML) != "paper-osha.html" else
                "A standalone paper on the OSHA hours-denominator result: data quality in OSHA "
                "Injury Tracking Application establishment filings and its effect on rate-based "
                "safety benchmarks.",
            "author": {
                "@type": "Person",
                "name": "Priyatham Chimmani",
                "url": "https://priyatham9.github.io/",
                "sameAs": ["https://github.com/priyatham9", "https://linkedin.com/in/priyatham9"],
            },
            "datePublished": "2026-09",
            "isPartOf": "https://priyatham9.github.io/grounded/",
            "about": subtitle if os.path.basename(OUT_HTML) != "paper-osha.html" else
                "OSHA injury-rate data quality and the exposure-hours denominator",
        }, ensure_ascii=False),
        "title_full": esc(full_title),
        "desc": esc(subtitle),
        "subtitle": esc(subtitle),
        "byline": esc(byline),
        "favicon": FAVICON,
        "css": CSS,
        "js": JS,
        "toc": build_toc(r.toc, section_minutes(body_lines)),
        "read5": read5_box(r.toc),
        "article": article,
        "status": status_banner(n_refs, n_notes, n_words),
        "cite": cite_panel(full_title, os.path.basename(OUT_HTML)),
        "words": "{:,}".format(n_words) + " words",
        "nrefs": n_refs,
    }

    if EM_DASH in page or ("&" + "mdash;") in page:
        die("generated page contains an em dash")

    # Cheap guards against the two ways this file can silently corrupt itself:
    # script text leaking into the stylesheet, and unbalanced braces truncating
    # the rest of the CSS.
    if "(function(" in CSS or "addEventListener" in CSS:
        die("script text leaked into the stylesheet")
    if CSS.count("{") != CSS.count("}"):
        die("stylesheet braces are unbalanced (%d open, %d close)"
            % (CSS.count("{"), CSS.count("}")))
    if "position:sticky" not in page:
        die("stylesheet lost its sticky rules")

    outdir = os.path.dirname(OUT_HTML)
    if not os.path.isdir(outdir):
        die("output directory does not exist: %s" % outdir)
    page = apply_banner(page, current_paper=os.path.basename(OUT_HTML),
                        sections=PAPER_SECTIONS)
    io.open(OUT_HTML, "w", encoding="utf-8").write(page)

    print("wrote %s" % OUT_HTML)
    print("  %s words, %d references, %d verification notes, %d TOC entries"
          % ("{:,}".format(n_words), n_refs, n_notes, len(r.toc)))
    print("  %d citation sites across %d distinct keys"
          % (sum(r.inline.counts.values()), len(r.inline.counts)))
    print("  em dashes in output: 0")


if __name__ == "__main__":
    build()
