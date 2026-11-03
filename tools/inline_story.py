#!/usr/bin/env python3
"""Inline tools/story.css and tools/story.js into single-file HTML pages.

Each page carries marker pairs; everything between a pair is replaced with the
current engine source:

    <style> ... /*STORY_CSS_START*/ /*STORY_CSS_END*/ ... </style>
    <script> /*STORY_JS_START*/ /*STORY_JS_END*/ </script>

Usage:
    python3 tools/inline_story.py page.html [more.html ...]
    python3 tools/inline_story.py --check page.html     # report only, no write
    python3 tools/inline_story.py --add-tokens page.html  # also insert the tokens marker
                                                          # pair at the start of the first <style>

The tokens block (/*TOKENS_CSS_START*/ /*TOKENS_CSS_END*/) holds tools/tokens.css.
Page-level :root values that come later in the same page still win.

Idempotent: running it twice makes no second change.
"""

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAIRS = [
    # the one design-token layer (palette, scales, a11y rules); goes first in the page's CSS
    ("tokens", "/*TOKENS_CSS_START*/", "/*TOKENS_CSS_END*/", HERE / "tokens.css"),
    # optional: pages that want the base tokens inlined too
    ("shared", "/*SHARED_CSS_START*/", "/*SHARED_CSS_END*/", HERE / "shared.css"),
    ("css", "/*STORY_CSS_START*/", "/*STORY_CSS_END*/", HERE / "story.css"),
    ("js", "/*STORY_JS_START*/", "/*STORY_JS_END*/", HERE / "story.js"),
]


# Motion layer (story.js section 9): GSAP core + plugins from cdnjs, pinned.
# All four are free since GSAP 3.13. They load before the engine script.
GSAP_VERSION = "3.15.0"
GSAP_TAGS = "".join(
    f'<script id="gsap-{n.lower().replace(".min.js", "")}" src="https://cdnjs.cloudflare.com/ajax/libs/gsap/{GSAP_VERSION}/{n}"></script>\n'
    for n in ("gsap.min.js", "ScrollTrigger.min.js", "SplitText.min.js", "Flip.min.js")
)


def ensure_gsap(text: str) -> tuple[str, str]:
    """Put the GSAP tags right before the script that holds the engine (idempotent)."""
    import re
    j = text.find("/*STORY_JS_START*/")
    if j < 0:
        return text, "no engine"
    i = text.rfind("<script", 0, j)
    if 'id="gsap-gsap"' in text:
        # keep the pinned version current
        new = re.sub(r'(<script id="gsap-[^"]+" src="[^"]*/gsap/)[\d.]+/', r"\g<1>" + GSAP_VERSION + "/", text)
        return new, "gsap ok" if new == text else "gsap version"
    return text[:i] + GSAP_TAGS + text[i:], "gsap added"


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


TOKENS_EMPTY = "/*TOKENS_CSS_START*/\n/*TOKENS_CSS_END*/\n"


def ensure_tokens_marker(text: str) -> tuple[str, str]:
    """Insert an empty tokens marker pair at the start of the first <style> element."""
    import re
    if "/*TOKENS_CSS_START*/" in text:
        return text, "marker present"
    m = re.search(r"<style\b[^>]*>", text)
    if not m:
        return text, "no <style>"
    return text[: m.end()] + "\n" + TOKENS_EMPTY + text[m.end():], "marker added"


def run(paths, check=False, add_tokens=False) -> int:
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
        if add_tokens:
            text, tm = ensure_tokens_marker(text)
            notes.append(tm)
        for kind, start, end, _path in PAIRS:
            text, status = splice(text, start, end, sources[kind])
            notes.append(f"{kind} {status}")
            if status in ("unterminated marker", "duplicate markers"):
                failures += 1
        text, gs = ensure_gsap(text)
        notes.append(gs)
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
    ap.add_argument("--add-tokens", action="store_true",
                    help="insert the tokens marker pair at the start of the first <style> if missing")
    args = ap.parse_args()
    return run(args.pages, check=args.check, add_tokens=args.add_tokens)


if __name__ == "__main__":
    sys.exit(main())
