#!/usr/bin/env python3
"""Check that pages carry the current tools/tokens.css and do not drift from it.

For each page: (1) the /*TOKENS_CSS_START*/../*TOKENS_CSS_END*/ block equals
tokens.css; (2) any --accent / --paper / --ink set in the page's light :root
equals the tokens.css light value. Exits 1 and lists mismatches.

    python3 tools/check_tokens.py docs/story.html [more.html ...]
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
START, END = "/*TOKENS_CSS_START*/", "/*TOKENS_CSS_END*/"
VARS = ("accent", "paper", "ink")


def light_values(css: str) -> dict:
    """Declarations of every plain top-level `:root{...}` block (light palette; later wins)."""
    out = {}
    text = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    pos = 0
    while pos < len(text):
        o = text.find("{", pos)
        if o < 0:
            break
        sel = text[pos:o].strip().split("}")[-1].strip()
        depth, k = 1, o + 1
        while k < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[k], 0)
            k += 1
        body = text[o + 1:k - 1]
        if sel.startswith("@"):
            pos = k  # skip the whole at-rule
            continue
        if sel == ":root":
            for name, v in re.findall(r"--([\w-]+)\s*:\s*([^;}]+?)\s*(?=;|$)", body):
                out[name] = v.strip()
        pos = k
    return out


def check(page: pathlib.Path, tokens: str) -> list:
    text = page.read_text(encoding="utf-8")
    problems = []
    i, j = text.find(START), text.find(END)
    if i < 0 or j < 0:
        return [f"{page}: no tokens marker block"]
    block = text[i + len(START): j].strip("\n")
    if block != tokens.strip("\n").replace("</style", "<\\/style"):
        problems.append(f"{page}: tokens block differs from tokens.css")
    want = light_values(tokens)
    rest = text[:i] + text[j + len(END):]
    for style in re.findall(r"<style\b[^>]*>(.*?)</style>", rest, re.S):
        for k, v in light_values(style).items():
            if k in VARS and v.upper() != want[k].upper():
                problems.append(f"{page}: --{k} is {v}, tokens.css has {want[k]}")
    return problems


def main(argv) -> int:
    pages = [pathlib.Path(a) for a in argv]
    if not pages:
        print(__doc__)
        return 2
    tokens = (HERE / "tokens.css").read_text(encoding="utf-8")
    problems = []
    for p in pages:
        problems += check(p, tokens)
    for line in problems:
        print(line)
    print(f"{len(pages)} page(s), {len(problems)} mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
