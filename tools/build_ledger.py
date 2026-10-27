#!/usr/bin/env python3
"""Render docs/methods-ledger.html from docs/methods-ledger.json.

The JSON is the source of truth. The page's <main> element is generated here;
the page shell (head, site header, search dialog, footer scripts) is reused
from the existing page, or from docs/reproduce.html on the first build, so the
page keeps the same header as the rest of the site.

  python3 tools/build_ledger.py          # write docs/methods-ledger.html
  python3 tools/build_ledger.py --check  # fail if the committed <main> is stale
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "methods-ledger.json"
PAGE = ROOT / "docs" / "methods-ledger.html"
SHELL_FALLBACK = ROOT / "docs" / "reproduce.html"

URL = "https://priyatham9.github.io/grounded/methods-ledger.html"
TITLE = "Methods and limitations ledger - Grounded"
DESC = (
    "Per repository, each statistical or machine-learning method used, its assumptions "
    "and known limitations, each linked to the file where the repository states it."
)
CSS = """<style id="ledger-css">
.led{display:grid;gap:14px}
.led .card h3{margin:6px 0 4px}
.led .m{color:var(--ink-2);font-size:15.5px;margin:0 0 10px}
.led h4{font:600 12px/1.4 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.led ul{margin:0;padding-left:1.1em}
.led li{margin-bottom:10px;color:var(--ink-2);font-size:15.5px}
.led q{display:block;margin-top:2px;color:var(--muted);font-size:14px;quotes:none;overflow-wrap:anywhere}
.led li a,.led .m a{color:var(--accent);font:600 13px/1.4 var(--font-mono);overflow-wrap:anywhere}
.led .toc{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0 0 20px}
.led .toc a{color:var(--accent);font:600 13px/1.4 var(--font-mono);text-decoration:none;min-height:44px;display:inline-flex;align-items:center}
</style>"""


def blob(ledger, repo, path):
    return ledger["blob_base"].format(repo=repo, ref=ledger["refs"][repo], path=path)


def link(ledger, repo, path):
    return f'<a href="{html.escape(blob(ledger, repo, path))}">{html.escape(repo)}/{html.escape(path)}</a>'


def render_item(ledger, repo, item):
    return (
        f"<li>{html.escape(item['text'])} {link(ledger, repo, item['path'])}"
        f"<q>{html.escape(item['quote'])}</q></li>"
    )


def render_main(ledger):
    repos = []
    for row in ledger["rows"]:
        if row["repo"] not in repos:
            repos.append(row["repo"])
    n_items = sum(len(r["assumptions"]) + len(r["caveats"]) for r in ledger["rows"])
    out = [
        '<main id="main">',
        ' <div class="wrap intro">',
        '  <span class="label">Grounded &middot; rigour</span>',
        "  <h1>Methods and limitations ledger.</h1>",
        (
            f"  <p>{len(ledger['rows'])} methods across {len(repos)} repositories and {n_items} "
            "stated assumptions and limitations. Each line links to the file in the owning "
            "repository where it is stated and quotes the sentence. Nothing here is new analysis: "
            "the ledger restates what each repository already says about itself, and "
            "<code>tools/check_ledger.py</code> fails if a linked file or a quoted sentence is missing "
            "from the repository's public GitHub copy.</p>"
        ),
        '  <div class="btns">',
        '   <a class="btn primary" href="methods-ledger.json">Machine-readable JSON</a>',
        '   <a class="btn" href="https://github.com/priyatham9/grounded/blob/main/tools/check_ledger.py">Checker</a>',
        "  </div>",
        " </div>",
        ' <section><div class="wrap led">',
        '  <nav class="toc" aria-label="Repositories">'
        + "".join(f'<a href="#{html.escape(r)}">{html.escape(r)}</a>' for r in repos)
        + "</nav>",
    ]
    for repo in repos:
        out.append(f'  <h2 id="{html.escape(repo)}">{html.escape(repo)}</h2>')
        for row in (r for r in ledger["rows"] if r["repo"] == repo):
            out.append(f'  <div class="card" id="{html.escape(row["id"])}">')
            out.append(f"   <h3>{html.escape(row['id'])}</h3>")
            out.append(
                f'   <p class="m">{html.escape(row["method"])} Method described in '
                f"{link(ledger, repo, row['method_path'])}.</p>"
            )
            for label, key in (("Assumptions", "assumptions"), ("Limitations and caveats", "caveats")):
                out.append(f"   <h4>{label}</h4>")
                out.append("   <ul>")
                out.extend("    " + render_item(ledger, repo, it) for it in row[key])
                out.append("   </ul>")
            out.append("  </div>")
    out += [" </div></section>", "</main>"]
    return "\n".join(out)


def splice(shell, main):
    shell = re.sub(r'<style id="ledger-css">.*?</style>', "", shell, flags=re.DOTALL)
    shell = shell.replace("</head>", CSS + "</head>", 1)
    shell = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", shell, count=1, flags=re.DOTALL)
    for pat, val in (
        (r'(<meta name="description" content=")[^"]*', DESC),
        (r'(<meta property="og:title" content=")[^"]*', TITLE),
        (r'(<meta property="og:description" content=")[^"]*', DESC),
        (r'(<meta property="og:url" content=")[^"]*', URL),
        (r'(<link rel="canonical" href=")[^"]*', URL),
    ):
        shell = re.sub(pat, lambda m, val=val: m.group(1) + html.escape(val, quote=True), shell, count=1)
    return re.sub(r'<main id="main">.*?</main>', lambda m: main, shell, count=1, flags=re.DOTALL)


def committed_main(text):
    m = re.search(r'<main id="main">.*?</main>', text, flags=re.DOTALL)
    return m.group(0) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    want = render_main(ledger)
    if args.check:
        have = committed_main(PAGE.read_text(encoding="utf-8")) if PAGE.exists() else None
        if have != want:
            print("docs/methods-ledger.html is stale: run python3 tools/build_ledger.py")
            return 1
        print("docs/methods-ledger.html matches docs/methods-ledger.json")
        return 0
    shell_path = PAGE if PAGE.exists() else SHELL_FALLBACK
    PAGE.write_text(splice(shell_path.read_text(encoding="utf-8"), want), encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
