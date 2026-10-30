#!/usr/bin/env python3
"""Pre-build gate for the paper pages (docs/paper.html, docs/paper-osha.html).

Stdlib only. Fails (exit 1) on: duplicate ids, in-page links (#x) with no
target, citation links that do not point at a reference entry, local
img/link/script files that are missing, and leftover unresolved markers
([cite_key], TODO, ??). It never edits a page.
"""
import os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS = ["docs/paper.html", "docs/paper-osha.html"]
MARKER = re.compile(r"\[[a-z][a-z_]*\d{4}[a-z0-9_]*\]|\bTODO\b|\?\?|\bCITATION NEEDED\b", re.I)


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.dups, self.hrefs, self.files = set(), set(), [], []
        self.refs, self.cites, self.text, self.skip = set(), [], [], 0
        self.in_a = 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "a":
            self.in_a += 1
        i = a.get("id")
        if i:
            (self.dups if i in self.ids else self.ids).add(i)
            if i.startswith("ref-"):
                self.refs.add(i)
        h = a.get("href")
        if h and h.startswith("#") and len(h) > 1:
            self.hrefs.append(h[1:])
            if h.startswith("#ref-"):
                self.cites.append(h[1:])
        for k in ("src", "href"):
            v = a.get(k)
            if v and tag in ("img", "script", "link", "source") and not re.match(r"(https?:|data:|//|#|mailto:)", v):
                self.files.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag == "a" and self.in_a:
            self.in_a -= 1

    def handle_data(self, d):
        if not self.skip:
            # a resolved citation renders as [<a>key</a>]: ignore linked text
            self.text.append("" if self.in_a else d)


def main():
    bad = 0
    for rel in PAPERS:
        path = os.path.join(ROOT, rel)
        p = P()
        p.feed(open(path, encoding="utf-8").read())
        errs = []
        errs += ["duplicate id: " + i for i in sorted(p.dups)]
        errs += ["dangling #link: " + h for h in sorted(set(p.hrefs) - p.ids)]
        errs += ["citation to missing reference: " + c for c in sorted(set(p.cites) - p.refs)]
        for f in p.files:
            if not os.path.exists(os.path.join(os.path.dirname(path), f.split("?")[0])):
                errs.append("missing file: " + f)
        text = "".join(p.text)
        errs += ["unresolved marker: " + m.group(0) for m in MARKER.finditer(text)]
        print("%s: %d ids, %d references, %d citation links, %d problem(s)"
              % (rel, len(p.ids), len(p.refs), len(p.cites), len(errs)))
        for e in errs[:50]:
            print("  " + e)
        bad += len(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
