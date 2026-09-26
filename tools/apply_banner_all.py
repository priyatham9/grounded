"""Re-apply the shared header (tools/banner.py) to every research page, then rebuild
the programme search index (tools/build_search.py).

    python3 tools/apply_banner_all.py                  # all pages under <root>/repos
    python3 tools/apply_banner_all.py --repos DIR      # a mirror of repos/
    python3 tools/apply_banner_all.py --dry-run        # report what would change

Each page keeps what its header already says: which item is current, whether it
links to a story, and its "On this page" strip (section links whose target id is
gone from the page are dropped). apply_banner is idempotent, so running this twice
changes nothing the second time. Pages without the shared header (ehs-benchmarks,
which has its own masthead) are left alone and listed.
"""
import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banner  # noqa: E402
import build_search  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROJECT_SLUGS = {s for s, _, _ in banner.PROJECTS}
HUB_PAGES = {"index.html": "hub", "start.html": "start", "observatory.html": "observatory",
             "changelog.html": "changelog", "paper.html": "paper.html", "paper-osha.html": "paper-osha.html"}
SKIP_REPOS = {"ehs-osha-benchmark-api", "priyathamchimmani", "priyatham9.github.io", "priyatham9", "brag"}


def settings(repo, path, page):
    """current=, story_href= and sections= for one page."""
    if repo == "grounded":
        current = HUB_PAGES.get(path.name, "hub")
    else:
        current = repo
    story = None
    if repo in PROJECT_SLUGS and (path.parent / "story.html").exists():
        story = "story.html"   # on the story page itself the header marks it as the current page
    # the strip the page already carries is the page owner's choice (a builder may have passed
    # explicit sections, or none); keep it, minus links whose target no longer exists
    m = re.search(r'<header class="rs-header"[^>]*>(.*?)</header>', page, re.S)
    if m:
        nav = re.search(r'<nav class="rs-sections"[^>]*>(.*?)</nav>', m.group(1), re.S)
        secs = [(html.unescape(i), banner._text(lab)) for i, lab in
                re.findall(r'<a class="rs-sec" href="#([^"]+)">(.*?)</a>', nav.group(1), re.S)] if nav else []
        body = page[:m.start()] + page[m.end():]
    else:
        secs, body = banner._detect_sections(page), page
    secs = [(i, lab) for i, lab in secs if f'id="{html.escape(i)}"' in body]
    return current, story, secs


def main(argv=None):
    ap = argparse.ArgumentParser(description="Re-apply the shared header and rebuild the search index.")
    ap.add_argument("--repos", default=str(ROOT / "repos"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated path substrings, e.g. grounded/,story.html")
    a = ap.parse_args(argv)
    repos = Path(a.repos)
    only = [x for x in a.only.split(",") if x]
    changed, same, skipped = [], 0, []
    for d in sorted(p for p in repos.iterdir() if p.is_dir() and p.name not in SKIP_REPOS):
        for f in sorted((d / "docs").glob("*.html")) if (d / "docs").is_dir() else []:
            rel = f"{d.name}/{f.name}"
            if only and not any(x in rel for x in only):
                continue
            page = f.read_text(encoding="utf-8")
            if 'class="rs-header"' not in page:
                skipped.append(rel)
                continue
            current, story, secs = settings(d.name, f, page)
            out = banner.apply_banner(page, current=current, sections=secs, story_href=story)
            if out == page:
                same += 1
                continue
            changed.append(f"{rel}  current={current} story={story or '-'} sections={len(secs)}")
            if not a.dry_run:
                f.write_text(out, encoding="utf-8")
    print(("would update" if a.dry_run else "updated") + f" {len(changed)} page(s), {same} already current")
    for c in changed:
        print("  " + c)
    if skipped:
        print("no shared header (left alone): " + ", ".join(skipped))
    if not a.dry_run:
        build_search.main(["--repos", str(repos)])


if __name__ == "__main__":
    main()
