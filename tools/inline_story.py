#!/usr/bin/env python3
"""Inline tools/story.css and tools/story.js into single-file HTML pages.

Each page carries marker pairs; everything between a pair is replaced with the
current engine source:

    <style> ... /*STORY_CSS_START*/ /*STORY_CSS_END*/ ... </style>
    <script> /*STORY_JS_START*/ /*STORY_JS_END*/ </script>

Usage:
    python3 tools/inline_story.py page.html [more.html ...]
    python3 tools/inline_story.py --check page.html     # report only, no write

Idempotent: running it twice makes no second change.
"""

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAIRS = [
    # optional: pages that want the base tokens inlined too
    ("shared", "/*SHARED_CSS_START*/", "/*SHARED_CSS_END*/", HERE / "shared.css"),
    ("css", "/*STORY_CSS_START*/", "/*STORY_CSS_END*/", HERE / "story.css"),
    ("js", "/*STORY_JS_START*/", "/*STORY_JS_END*/", HERE / "story.js"),
]


def sanitize(kind: str, src: str) -> str:
    """Keep inlined source from terminating its own host tag."""
    if kind == "js":
        # only a literal </script> ends a script element
        src = src.replace("</script", "<\\/script")
    else:
        src = src.replace("</style", "<\\/style")
    return src


def splice(text: str, start: str, end: str, payload: str) -> tuple[str, str]:
    """Replace the region between start/end markers. Returns (text, status)."""
    i = text.find(start)
    if i < 0:
        return text, "no marker"
    j = text.find(end, i + len(start))
    if j < 0:
        return text, "unterminated marker"
    if text.count(start) > 1 or text.count(end) > 1:
        return text, "duplicate markers"
    body = "\n" + payload.strip("\n") + "\n"
    old = text[i + len(start): j]
    if old == body:
        return text, "unchanged"
    return text[: i + len(start)] + body + text[j:], "updated"


def run(paths, check=False) -> int:
    sources = {}
    for kind, _s, _e, path in PAIRS:
        if not path.exists():
            print(f"error: missing engine file {path}", file=sys.stderr)
            return 2
        sources[kind] = sanitize(kind, path.read_text(encoding="utf-8"))

    failures = 0
    for raw in paths:
        page = pathlib.Path(raw)
        if not page.exists():
            print(f"{page}: error, file not found")
            failures += 1
            continue
        text = original = page.read_text(encoding="utf-8")
        notes = []
        for kind, start, end, _path in PAIRS:
            text, status = splice(text, start, end, sources[kind])
            notes.append(f"{kind} {status}")
            if status in ("unterminated marker", "duplicate markers"):
                failures += 1
        changed = text != original
        if changed and not check:
            page.write_text(text, encoding="utf-8")
        verb = "would change" if (changed and check) else ("changed" if changed else "no change")
        print(f"{page}: {verb} ({', '.join(notes)})")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Inline story.css / story.js into HTML pages.")
    ap.add_argument("pages", nargs="+", help="HTML files to update")
    ap.add_argument("--check", action="store_true", help="report what would change, write nothing")
    args = ap.parse_args()
    return run(args.pages, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
