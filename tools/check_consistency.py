#!/usr/bin/env python3
"""Fail if a headline number differs between README, site pages and papers.

Stdlib only, offline. Reads tools/consistency_claims.json. Each claim has a
canonical value, a source (file + regex with one capture group, or a CSV row
count) and the files that repeat it. Every match in every listed file must
equal the canonical value, and each listed pattern must match at least once.
Optional "forbidden" patterns flag stale wording anywhere in given globs.
"""
import csv
import glob
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = Path(__file__).with_name("consistency_claims.json")


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _norm(s, ci):
    return s.lower() if ci else s


def check(registry, root=ROOT):
    """Return a list of problem strings (empty means consistent)."""
    root = Path(root)
    errors = []
    for c in registry["claims"]:
        cid, ci = c["id"], c.get("case_insensitive", False)
        want = _norm(str(c["value"]), ci)
        src = c["source"]
        try:
            text = _read(root, src["file"])
            if src.get("csv_rows"):
                got = [str(max(0, len(list(csv.reader(io.StringIO(text)))) - 1))]
            else:
                got = [m.group(1) for m in re.finditer(src["regex"], text)]
        except OSError as e:
            errors.append(f"{cid}: cannot read source {src['file']}: {e}")
            continue
        if not got:
            errors.append(f"{cid}: source pattern not found in {src['file']}")
        for g in got:
            if _norm(g, ci) != want:
                errors.append(f"{cid}: source {src['file']} says {g!r}, canonical is {c['value']!r}")
        for ap in c["appears_in"]:
            try:
                t = _read(root, ap["file"])
            except OSError as e:
                errors.append(f"{cid}: cannot read {ap['file']}: {e}")
                continue
            found = [m.group(1) for m in re.finditer(ap["regex"], t)]
            if not found:
                errors.append(f"{cid}: {ap['file']} no longer matches /{ap['regex']}/")
            for g in found:
                if _norm(g, ci) != want:
                    errors.append(f"{cid}: {ap['file']} says {g!r}, canonical is {c['value']!r}")
        for fb in c.get("forbidden", []):
            for pat in fb["files"]:
                for p in sorted(glob.glob(str(root / pat))):
                    for m in re.finditer(fb["regex"], Path(p).read_text(encoding="utf-8")):
                        errors.append(f"{cid}: stale wording {m.group(0)!r} in {Path(p).relative_to(root)}")
    return errors


def main(argv=None):
    reg = json.loads(DEFAULT.read_text(encoding="utf-8"))
    errors = check(reg)
    for e in errors:
        print("FAIL", e)
    print(f"{len(reg['claims'])} claims checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
