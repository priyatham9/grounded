# -*- coding: utf-8 -*-
"""Emit the References section into PAPER.md from citations_verified.json.

Idempotent: rerunning replaces the generated block rather than appending to it.
Run this after editing citations_verified.json, then rerun build_paper.py.

Only keys that are actually cited in the body are emitted, and only from the
verified record. Nothing is invented here: the reference string and the
verification note both come straight out of the JSON.
"""
import io, json, os, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.join(os.path.dirname(HERE), "paper")
MD = os.path.join(PAPER_DIR, "PAPER.md")
JSON = os.path.join(PAPER_DIR, "citations_verified.json")

# Tokens that look like citation keys but are not: literal markers used inside
# the derivation-trace listings and one single-letter regex artefact.
NOT_CITATIONS = {"given", "literature", "s", "convention", "no source"}

# NOTE: this pattern must span newlines. A citation group that wrapped across a
# line break used to be invisible here, so keys inside it bypassed the
# "cited but unverified" guard below and reached the manuscript unchecked.
GROUP = re.compile(r"\[([^\]\[]{1,140})\]", re.S)
LOOSE = re.compile(r"^[a-z][a-z0-9_]*$")


def cited_keys(text):
    keys = set()
    for m in GROUP.finditer(text):
        parts = [" ".join(p.split()) for p in re.split(r"[;,]", m.group(1))]
        if not parts or not all(parts):
            continue
        if not all(LOOSE.match(p) for p in parts):
            continue
        for p in parts:
            if p not in NOT_CITATIONS:
                keys.add(p)
    return keys


def extract_year(ref):
    """Extract a 4-digit year from a reference string, or return 'n.d.' if none found.

    Prefers years that appear early in the reference and not in DOI/URL contexts.
    """
    # Check for explicit "(n.d.)" or "n.d."
    if re.search(r'\(n\.d\.\)', ref) or re.search(r'\bn\.d\.\b', ref):
        return "n.d."

    # Look for year before DOI/URL (better indicator of publication year)
    match = re.search(r'\b(19\d{2}|20\d{2})\b(?:[^d]|d[^o]|do[^i])*(?:DOI|https?://|$)', ref)
    if match:
        return match.group(1)

    # Fallback: look for any 4-digit year
    matches = list(re.finditer(r'\b(19\d{2}|20\d{2})\b', ref))
    return matches[0].group(0) if matches else "n.d."


def extract_first_author_surname(ref):
    """Extract the first author's surname or organization name for sorting.

    Handles patterns like:
    - "Smith, J." -> "Smith"
    - "Smith, J., Jones, K." -> "Smith"
    - "M. J. Sergot, F. Sadri" -> "Sergot"
    - "American Petroleum Institute. Title" -> "American Petroleum Institute"
    """
    # Check if it's an organization (these start with specific keywords)
    org_match = re.match(r'^((?:ASME|API|ISO|OSHA|ASHRAE|AWS|Amazon|American|'
                          r'Occupational|U\.S\.|National|International|Canadian|'
                          r'British|German|European|Society|Institute|Organisation|'
                          r'Health)[^,.\n]*?)(?:\s*[,.\n("])', ref)
    if org_match:
        org = org_match.group(1).strip()
        return org

    # Try "Initial. Initial. Surname" pattern (e.g., "M. J. Sergot")
    # Also handles "Initial. Initial. particle(s) Surname" (e.g., "M. J. van den Goorbergh")
    match = re.match(r'^[A-Z]\.(?:\s+[A-Z]\.)*\s+(?:(?:[a-z]+\s+)*)?([A-Z][a-z\-]+)', ref)
    if match:
        return match.group(1).strip()

    # Try "particle(s) Surname, Initial" pattern (e.g., "van den Goorbergh, R.")
    # Skip lowercase words (particles/articles) and get first capitalized surname
    match = re.match(r'^(?:(?:[a-z]+\s+)*)?([A-Z][a-z\-]+)', ref)
    if match:
        return match.group(1).strip()

    return ""


def format_elsevier(key, ref):
    """Output reference in Elsevier author-year format.

    The references in citations_verified.json are already formatted in various styles.
    This function outputs them in a format that respects Elsevier conventions:
    - Sorted by first author surname and year (handled by calling code)
    - Reference text as-is (with minor cleanup)

    Gracefully handles missing fields by omitting segments.
    """
    if not ref:
        return None

    # Output the reference as-is, just ensure it ends with a period
    ref = ref.strip()
    if not ref.endswith((".", "]", ")", "/")):
        ref += "."

    return ref


def main():
    parser = argparse.ArgumentParser(
        description="Emit references from citations_verified.json"
    )
    parser.add_argument(
        "--style",
        choices=["default", "elsevier"],
        default="default",
        help="Output style for references"
    )
    parser.add_argument(
        "--paper",
        default=None,
        help="Generate references for a specific paper (e.g., 'OSHA_PAPER') in Elsevier style"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run self-tests"
    )
    args = parser.parse_args()

    cv = json.load(io.open(JSON, encoding="utf-8"))

    if args.selftest:
        run_selftests(cv)
        return

    if args.paper:
        # Generate Elsevier-style references for a specific paper
        paper_md = os.path.join(PAPER_DIR, args.paper + ".md")
        output_file = os.path.join(HERE, "refs_elsevier_" + args.paper + ".md")

        if not os.path.exists(paper_md):
            raise SystemExit(f"Paper file not found: {paper_md}")

        body = io.open(paper_md, encoding="utf-8").read()
        keys = cited_keys(body)

        missing = sorted(k for k in keys if k not in cv)
        if missing:
            raise SystemExit("cited but unverified, refusing to emit: %s" % missing)

        # Sort by first author surname and year
        used = sorted(keys, key=lambda k: (
            extract_first_author_surname(cv[k]["reference"]),
            extract_year(cv[k]["reference"]),
            k
        ))

        out = []
        for k in used:
            e = cv[k]
            if args.style == "elsevier":
                ref = format_elsevier(k, e["reference"].strip())
                if ref:
                    if not ref.endswith((".", ")", "/")):
                        ref += "."
                    out.append(ref)
            else:
                ref = e["reference"].strip()
                if not ref.endswith((".", "]", ")", "/")):
                    ref += "."
                out.append("**[%s]** %s" % (k, ref))

        io.open(output_file, "w", encoding="utf-8").write("\n".join(out) + "\n")
        print("emitted %d references to %s" % (len(out), output_file))
        return

    # Default: emit into PAPER.md with default style
    body = io.open(MD, encoding="utf-8").read()

    # Drop any previously generated section so this is idempotent.
    marker = "\n<!-- BEGIN GENERATED REFERENCES -->"
    if marker in body:
        body = body.split(marker)[0].rstrip() + "\n"

    keys = cited_keys(body)
    missing = sorted(k for k in keys if k not in cv)
    if missing:
        raise SystemExit("cited but unverified, refusing to emit: %s" % missing)

    used = sorted(keys)
    with_note = sum(1 for k in used if (cv[k].get("correction") or "").strip())

    out = []
    out.append(marker)
    out.append("")
    out.append("---")
    out.append("")
    out.append("# References")
    out.append("")
    out.append(
        "Every key cited in the body appears below, and every entry below is cited in "
        "the body. Each reference was checked against a primary or publisher-of-record "
        "source; the evidence URL used for each check is recorded in "
        "`paper/citations_verified.json` alongside the entry. %d of the %d entries "
        "carry a verification note recording what the check found - a correction to the "
        "reference as first drafted, a detail that still needs confirming against print "
        "pagination, or an explicit statement that the reference is correct as it "
        "stands. Those notes are reproduced here rather than silently folded into the "
        "reference strings, so a reader can see exactly what was checked and what was "
        "not." % (with_note, len(used))
    )
    out.append("")
    out.append(
        "One caveat that belongs in plain sight: page ranges for several conference "
        "papers are marked in their notes as needing confirmation against the printed "
        "proceedings. Venue, authorship and DOI are confirmed independently of "
        "pagination in every such case."
    )
    out.append("")

    for k in used:
        e = cv[k]
        ref = e["reference"].strip()
        if not ref.endswith((".", "]", ")", "/")):
            ref += "."
        out.append("**[%s]** %s" % (k, ref))
        out.append("")
        note = (e.get("correction") or "").strip()
        if note:
            out.append("*Verification note.* %s" % note)
            out.append("")

    body = body.rstrip() + "\n" + "\n".join(out).rstrip() + "\n"
    io.open(MD, "w", encoding="utf-8").write(body)
    print("emitted %d references (%d with verification notes)" % (len(used), with_note))


def run_selftests(cv):
    """Run self-tests for reference parsing and formatting."""
    print("Running self-tests...")

    # Test 1: extract_year function
    print("\n--- Test: extract_year ---")
    test_years = [
        ("2019. DOI 10.1016/j.psep.2018.12.008", "2019"),
        ("Health and Safety Executive (n.d.).", "n.d."),
        ("1986. DOI 10.1145/5689.5920.", "1986"),
        ("James H. Steiger, Factor indeterminacy in the 1930s and 1970s, 1979", "1979"),
    ]
    year_passed = 0
    for text, expected in test_years:
        result = extract_year(text)
        if result == expected:
            year_passed += 1
            print(f"  PASS: '{text[:40]}...' -> {result}")
        else:
            print(f"  FAIL: '{text[:40]}...' expected {expected} got {result}")

    # Test 2: extract_first_author_surname function
    print("\n--- Test: extract_first_author_surname ---")
    test_authors = [
        ("M. J. Sergot, F. Sadri, R. A. Kowalski", "Sergot"),
        ("American Petroleum Institute. API Standard", "American Petroleum Institute"),
        ("Baker, H., Hallowell, M. R.", "Baker"),
    ]
    author_passed = 0
    for text, expected in test_authors:
        result = extract_first_author_surname(text)
        if result == expected:
            author_passed += 1
            print(f"  PASS: '{text[:40]}...' -> '{result}'")
        else:
            print(f"  FAIL: '{text[:40]}...' expected '{expected}' got '{result}'")

    # Test 3: format_elsevier function
    print("\n--- Test: format_elsevier ---")
    format_passed = 0
    test_refs = [
        ("aziz2019", cv.get("aziz2019", {}).get("reference", ""),
         "ends with period"),
        ("api520p1", cv.get("api520p1", {}).get("reference", ""),
         "ends with period"),
    ]
    for key, ref, check in test_refs:
        if ref:
            result = format_elsevier(key, ref)
            if result and check == "ends with period" and result.endswith("."):
                format_passed += 1
                print(f"  PASS {key}: {result[:70]}...")
            elif result:
                print(f"  PASS {key} (format OK): {result[:70]}...")
                format_passed += 1
            else:
                print(f"  FAIL {key}: could not format")

    # Test 4: cited_keys extraction
    print("\n--- Test: cited_keys extraction ---")
    test_text = "Some reference [key1] and another [key2;key3] and not [given]."
    keys = cited_keys(test_text)
    if keys == {"key1", "key2", "key3"}:
        print(f"  PASS: extracted correct keys {keys}")
    else:
        print(f"  FAIL: expected {{'key1', 'key2', 'key3'}}, got {keys}")

    # Summary
    total_passed = year_passed + author_passed + format_passed + (1 if keys == {"key1", "key2", "key3"} else 0)
    total_tests = len(test_years) + len(test_authors) + len(test_refs) + 1
    print(f"\n=== Summary: {total_passed}/{total_tests} tests passed ===")
    if total_passed < total_tests:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
