#!/usr/bin/env python3
"""Check the headline-claims registry (claims/claims.json).

For every claim this verifies, in order:
  1. the claim text still appears in the named page of this repo (docs/...);
  2. the value at the claim's source (a committed file in a programme repo,
     fetched from raw.githubusercontent.com) equals the expected value
     within the stated tolerance;
  3. the verifying test named in the registry still exists in its repo and
     still pins the expected value (a text check of the committed test file).

Exit status 1 if any claim fails. Known discrepancies are printed as notes.
Standard library only.

  python3 claims/check_claims.py                  # fetch from GitHub
  python3 claims/check_claims.py --local-root DIR # read DIR/<repo>/<path>
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


class Fetcher:
    def __init__(self, base, ref, local_root=None):
        self.base, self.ref, self.local_root = base, ref, local_root
        self.cache = {}

    def get(self, repo, path):
        key = (repo, path)
        if key in self.cache:
            return self.cache[key]
        if repo == "grounded":
            text = (REPO_ROOT / path).read_text(encoding="utf-8")
        elif self.local_root:
            text = (Path(self.local_root) / repo / path).read_text(encoding="utf-8")
        else:
            url = self.base.format(repo=repo, ref=self.ref, path=path)
            with urllib.request.urlopen(url, timeout=60) as r:
                text = r.read().decode("utf-8")
        self.cache[key] = text
        return text


def json_lookup(obj, key):
    want_len = key.endswith("#len")
    if want_len:
        key = key[: -len("#len")]
    for part in key.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return len(obj) if want_len else obj


def extract(src, fetcher):
    text = fetcher.get(src["repo"], src["path"])
    kind = src["kind"]
    if kind == "json_path":
        return json_lookup(json.loads(text), src["key"])
    if kind == "json_count":
        items = json_lookup(json.loads(text), src["key"])
        return sum(all(i.get(k) == v for k, v in src["where"].items()) for i in items)
    if kind == "regex_count":
        return len(re.findall(src["pattern"], text))
    rows = list(csv.DictReader(io.StringIO(text)))
    if kind == "csv_rows":
        return len(rows)
    if kind == "csv_cell":
        hits = [r for r in rows if all(r.get(k) == v for k, v in src["where"].items())]
        if len(hits) != 1:
            raise ValueError(f"{len(hits)} rows match {src['where']}, expected 1")
        return hits[0][src["column"]]
    raise ValueError(f"unknown source kind {kind}")


def check_claim(c, fetcher):
    errs = []
    for a in c["appears_in"]:
        page = (REPO_ROOT / a["path"]).read_text(encoding="utf-8")
        if a["contains"] not in page:
            errs.append(f"text {a['contains']!r} no longer appears in {a['path']}")
    try:
        got = float(extract(c["source"], fetcher))
        if abs(got - c["expected"]) > c["tolerance"]:
            errs.append(
                f"source value {got} differs from expected {c['expected']} "
                f"(tolerance {c['tolerance']})"
            )
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as e:  # network, missing key, bad shape
        errs.append(
            f"could not read source {c['source']['repo']}/{c['source']['path']}: {e!r}"
        )
    vt = c["verifying_test"]
    try:
        body = fetcher.get(vt["repo"], vt["path"])
        if vt["symbol"] not in body:
            errs.append(
                f"verifying test symbol {vt['symbol']!r} not found in {vt['repo']}/{vt['path']}"
            )
        if vt.get("contains") and vt["contains"] not in body:
            errs.append(
                f"{vt['repo']}/{vt['path']} no longer contains {vt['contains']!r}"
            )
    except (OSError, ValueError) as e:
        errs.append(f"could not read verifying test {vt['repo']}/{vt['path']}: {e!r}")
    return errs


def run(registry_path, local_root=None, out=sys.stdout):
    reg = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    fetcher = Fetcher(reg["raw_base"], reg["ref"], local_root)
    failed = 0
    for c in reg["claims"]:
        errs = check_claim(c, fetcher)
        failed += bool(errs)
        print(f"{'FAIL' if errs else 'ok  '} {c['id']}: {c['statement']}", file=out)
        for e in errs:
            print(f"       - {e}", file=out)
    for d in reg.get("known_discrepancies", []):
        print(
            f"note {d['id']}: {d['where']} says {d['text']!r}; committed: {d['committed_value']}",
            file=out,
        )
    print(
        f"{len(reg['claims']) - failed}/{len(reg['claims'])} claims verified", file=out
    )
    return 1 if failed else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--registry", default=str(HERE / "claims.json"))
    p.add_argument("--local-root", help="directory holding clones named by repo")
    a = p.parse_args(argv)
    return run(a.registry, a.local_root)


if __name__ == "__main__":
    sys.exit(main())
