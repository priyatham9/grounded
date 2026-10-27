#!/usr/bin/env python3
"""Check the methods and limitations ledger (docs/methods-ledger.json).

Every assumption and caveat in the ledger names a file in one of the
programme's repositories and quotes the sentence in that file which states it.
This checker fetches each file from the repository's public GitHub copy
(raw.githubusercontent.com) and verifies, for every row:

  1. the method file exists;
  2. every assumption and caveat file exists;
  3. the quoted text appears in that file (whitespace-normalised, so a quote
     may span a line break but not be reworded).

Exit status 1 if anything fails. Standard library only.

  python3 tools/check_ledger.py                  # fetch from GitHub
  python3 tools/check_ledger.py --local-root DIR # read DIR/<repo>/<path>
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER = REPO_ROOT / "docs" / "methods-ledger.json"


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


class Fetcher:
    def __init__(self, ledger, local_root=None):
        self.base = ledger["raw_base"]
        self.refs = ledger["refs"]
        self.local_root = local_root
        self.cache = {}

    def get(self, repo, path):
        """Return the file text, or None if the file does not exist."""
        key = (repo, path)
        if key in self.cache:
            return self.cache[key]
        text = None
        if self.local_root:
            p = Path(self.local_root) / repo / path
            if p.is_file():
                text = p.read_text(encoding="utf-8")
        else:
            url = self.base.format(repo=repo, ref=self.refs[repo], path=path)
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    text = r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
        self.cache[key] = text
        return text


def iter_links(ledger):
    """Yield (row_id, repo, kind, path, quote or None) for every link."""
    for row in ledger["rows"]:
        yield row["id"], row["repo"], "method", row["method_path"], None
        for kind in ("assumptions", "caveats"):
            for item in row[kind]:
                yield row["id"], row["repo"], kind, item["path"], item["quote"]


def check(ledger, fetcher):
    """Return a list of failure strings (empty when everything holds)."""
    failures = []
    for row_id, repo, kind, path, quote in iter_links(ledger):
        text = fetcher.get(repo, path)
        if text is None:
            failures.append(f"{row_id}: {kind}: {repo}/{path} does not exist")
        elif quote is not None and norm(quote) not in norm(text):
            failures.append(f"{row_id}: {kind}: quote not found in {repo}/{path}: {quote[:70]!r}")
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--local-root", help="read DIR/<repo>/<path> instead of fetching")
    args = ap.parse_args(argv)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    fetcher = Fetcher(ledger, args.local_root)
    failures = check(ledger, fetcher)
    links = sum(1 for _ in iter_links(ledger))
    for f in failures:
        print("FAIL", f)
    print(f"{len(ledger['rows'])} rows, {links} links, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
