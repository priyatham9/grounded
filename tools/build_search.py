"""Build the programme-wide search index read by the shared header's search.

Crawls repos/*/docs/*.html (every research page, the two papers included) and
writes a compact JSON file to repos/grounded/docs/search-index.json. The header
(tools/banner.py) fetches it lazily the first time a reader opens search.

Format (kept small on purpose):
  {"v": 1,
   "p": [[repo, file, title, group, context, description], ...],  # one row per page
   "i": [[page_index, anchor, label, group, snippet], ...]} # headings and terms
group: 0 Pages, 1 Findings, 2 Papers, 3 Tools, 4 Terms.
file is "" for index.html so both the live URL (/<repo>/) and the local one
(/<repo>/docs/) resolve without a filename.

Usage: python3 tools/build_search.py [--repos DIR]   (default: <root>/repos)
"""
import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banner import PROJECTS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Pages that are local-only or not research pages.
SKIP_REPOS = {"ehs-osha-benchmark-api", "priyatham9.github.io", "priyatham9", "brag"}
TOOLS = {("ehs-capitals-calculator", "index.html"), ("ehs-osha-analysis", "explore.html"),
         ("ehs-ai-grounding-eval", "try.html"), ("ehs-human-factors-ontology", "crosswalk.html"),
         ("ehs-human-factors-ontology", "walkthrough.html"), ("ehs-benchmarks", "index.html"),
         ("grounded", "observatory.html")}
PAPERS = {("grounded", "paper.html"), ("grounded", "paper-osha.html")}
NAMES = dict((s, n) for s, n, _ in PROJECTS)
NAMES["grounded"] = "Grounded hub"
KIND = {"index.html": "Project page", "story.html": "Story", "explore.html": "Explorer",
        "try.html": "Try it", "crosswalk.html": "Crosswalk", "walkthrough.html": "Walk-through",
        "observatory.html": "Observatory", "start.html": "Start here", "changelog.html": "Changelog",
        "paper.html": "Paper", "paper-osha.html": "Paper"}
# Page order in the empty-query list: hub first, then the programme's reading order.
ORDER = ["grounded"] + [s for s, _, _ in PROJECTS]
FILE_ORDER = ["index.html", "start.html", "story.html", "observatory.html", "paper.html",
              "paper-osha.html", "explore.html", "try.html", "crosswalk.html", "walkthrough.html",
              "changelog.html"]

SKIP_TAGS = {"script", "style", "svg", "noscript", "template", "nav", "footer", "dialog",
             "button", "figure", "table", "select", "textarea", "form"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
        "track", "wbr"}
HEAD = {"h1", "h2", "h3", "h4"}
BAD_ANCHORS = {"top", "main", "content"}


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def cut(s, n):
    s = clean(s)
    if len(s) <= n:
        return s
    s = s[:n].rsplit(" ", 1)[0].rstrip(",;:.")
    return s + "…"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []        # [tag, skip, section_id]
        self.title = ""
        self.h1 = ""
        self.desc = ""
        self.items = []        # [anchor, label, kind, snippet]
        self.cap = None        # [kind, tag, id, section_id, buf]
        self.snip_for = None   # item awaiting its first paragraph
        self.pbuf = None
        self.in_title = False
        self.title_done = False
        self.used_sections = set()
        self.dt = None
        self.text = {}         # section id -> visible text (for glossary deep links)

    def skipping(self):
        return any(f[1] for f in self.stack)

    def section_id(self):
        for f in reversed(self.stack):
            if f[2]:
                return f[2]
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        skip = (tag in SKIP_TAGS or "rs-header" in cls or "sr-only" in cls or "visually-hidden" in cls
                or a.get("aria-hidden") == "true" or "hidden" in a or tag == "header" and "rs-" in cls
                or tag == "aside")
        sid = a.get("id") if tag in ("section", "article") and a.get("id") not in BAD_ANCHORS else None
        if tag == "meta" and a.get("name") == "description" and not self.desc:
            self.desc = clean(a.get("content") or "")
        if tag == "title" and not self.title_done:
            self.in_title = True
        if tag in VOID:
            return
        self.stack.append([tag, skip, sid])
        if self.skipping():
            return
        if tag in HEAD:
            self.cap = ["h", tag, a.get("id"), self.section_id(), []]
        elif tag == "dt":
            self.cap = ["dt", tag, a.get("id"), self.section_id(), []]
        elif tag == "dd" and self.dt is not None:
            self.cap = ["dd", tag, None, None, []]
        elif tag == "p" and self.snip_for is not None and self.cap is None:
            self.pbuf = []

    def handle_endtag(self, tag):
        if tag == "title" and self.in_title:
            self.in_title = False
            self.title_done = True
        if tag in VOID:
            return
        # pop to the matching tag (tolerates unclosed <p>/<li>)
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break
        else:
            return
        c = self.cap
        if c and c[1] == tag:
            self.cap = None
            text = re.sub(r"\s*[#\u00b6]$", "", clean("".join(c[4])))
            if not text:
                return
            if c[0] == "h":
                if tag == "h1":
                    self.h1 = self.h1 or text
                    return
                sec = c[3]
                anchor = None
                if sec and sec not in self.used_sections:
                    anchor = sec
                    self.used_sections.add(sec)
                elif c[2]:
                    anchor = c[2]
                if not anchor or anchor in BAD_ANCHORS:
                    self.snip_for = None
                    return
                it = [anchor, text, "h", ""]
                self.items.append(it)
                self.snip_for = it
            elif c[0] == "dt":
                anchor = c[2] or c[3]
                self.dt = [anchor, text, "t", ""] if anchor else None
                if self.dt:
                    self.items.append(self.dt)
            elif c[0] == "dd" and self.dt is not None:
                if len(text) < 12:   # a live output or a bare value, not a definition
                    self.items.remove(self.dt)
                else:
                    self.dt[3] = cut(text, 110)
                self.dt = None
            return
        if tag == "p" and self.pbuf is not None:
            text = clean("".join(self.pbuf))
            self.pbuf = None
            if self.snip_for is not None and len(text) > 24:
                self.snip_for[3] = cut(text, 110)
                self.snip_for = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        if self.skipping():
            return
        sid = self.section_id() or ""
        self.text[sid] = self.text.get(sid, "") + data
        if self.cap is not None:
            self.cap[4].append(data)
        elif self.pbuf is not None:
            self.pbuf.append(data)


def glossary():
    """The plain-language glossary the story engine annotates pages with (tools/story.js)."""
    src = (ROOT / "tools" / "story.js").read_text(encoding="utf-8")
    m = re.search(r"var glossary = \{(.*?)\n\s*\};", src, re.S)
    alt = re.search(r"var GLOSS_ALT = \{(.*?)\n\s*\};", src, re.S)
    terms = re.findall(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', m.group(1)) if m else []
    forms = {}
    if alt:
        for k, v in re.findall(r'"([^"]+)":\s*\[([^\]]*)\]', alt.group(1)):
            forms[k] = re.findall(r'"([^"]+)"', v)
    return [(k, d, forms.get(k, [k])) for k, d in terms]


def page_title(raw, repo):
    t = clean(raw)
    for suf in (" - Priyatham Chimmani", " | Grounded", " - Grounded", " - " + repo, " - EHS Benchmarks"):
        if t.endswith(suf) and len(t) > len(suf) + 3:
            t = t[: -len(suf)]
    return t.strip(" -|")


def build(repos):
    pages, items = [], []
    found = []
    for d in sorted(p for p in repos.iterdir() if p.is_dir()):
        if d.name in SKIP_REPOS or not (d / "docs").is_dir():
            continue
        for f in sorted((d / "docs").glob("*.html")):
            found.append((d.name, f))
    found.sort(key=lambda x: (ORDER.index(x[0]) if x[0] in ORDER else 99,
                              FILE_ORDER.index(x[1].name) if x[1].name in FILE_ORDER else 50, x[1].name))
    parsed = []
    for repo, f in found:
        p = Page()
        p.feed(f.read_text(encoding="utf-8", errors="replace"))
        key = (repo, f.name)
        group = 2 if key in PAPERS else 3 if key in TOOLS else 0
        title = page_title(p.title or p.h1 or f.stem, repo)
        ctx = NAMES.get(repo, repo) + " · " + KIND.get(f.name, f.stem.replace("-", " ").title())
        pi = len(pages)
        pages.append([repo, "" if f.name == "index.html" else f.name, title, group, ctx, cut(p.desc, 140)])
        seen = {title.lower()}
        for anchor, label, kind, snip in p.items:
            k = label.lower()
            if k in seen or len(label) < 3:
                continue
            seen.add(k)
            g = 4 if kind == "t" else 2 if key in PAPERS else 1
            items.append([pi, anchor, cut(label, 120), g, snip])
        parsed.append((pi, f.name, p.text))
    # Glossary terms deep-link to the first section that uses them, stories first.
    rank = {"story.html": 0, "index.html": 1}
    parsed.sort(key=lambda x: (rank.get(x[1], 2), x[0]))
    have = {i[2].lower() for i in items if i[3] == 4}
    for term, definition, forms in glossary():
        if term.lower() in have:
            continue
        pat = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(x) for x in forms) + r")(?![\w-])",
                         0 if term.isupper() or term[:1].isupper() else re.I)
        # the page that uses the term most is its home; link to the first section there using it
        best = None
        # project pages first: the hub and the papers mention every term once in passing
        for pi, _, text in sorted(parsed, key=lambda x: pages[x[0]][0] == "grounded"):
            if best and pages[pi][0] == "grounded":
                break
            n = sum(len(pat.findall(t)) for t in text.values())
            first = next((sid for sid, t in text.items() if sid and pat.search(t)), None)
            if n and first and (best is None or n > best[0]):
                best = (n, pi, first)
        if best:
            items.append([best[1], best[2], term, 4, cut(definition, 140)])
    return {"v": 1, "p": pages, "i": items}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repos", default=str(ROOT / "repos"))
    a = ap.parse_args(argv)
    repos = Path(a.repos)
    idx = build(repos)
    out = repos / "grounded" / "docs" / "search-index.json"
    raw = json.dumps(idx, ensure_ascii=False, separators=(",", ":"))
    out.write_text(raw + "\n", encoding="utf-8")
    print(f"search index: {len(idx['p'])} pages, {len(idx['i'])} entries, {len(raw.encode()):,} bytes -> {out}")


if __name__ == "__main__":
    main()
