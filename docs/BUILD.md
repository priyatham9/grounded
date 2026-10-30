# Building the papers

The papers are generated HTML pages: `docs/paper.html` and `docs/paper-osha.html`. They are the committed source for submission; the PDFs are built from them.

## Build

    tools/build_papers.sh [outdir]      # default build/papers

Needs Python 3 and Chrome or Chromium (`CHROME=/path` overrides detection); `pdfinfo` (poppler-utils) is used for a page-count check when present. The script prints each page to PDF with the page's own `@media print` rules and does not modify the pages.

## What fails the build

`tools/check_paper_html.py` runs first and exits non-zero on duplicate ids, `#links` with no target, citation links that do not resolve to a reference entry, missing local image/script/stylesheet files, and leftover `[cite_key]`, `TODO` or `??` markers. The build then fails if a PDF is missing, not a PDF, or under 5 pages.

## CI

`.github/workflows/papers.yml` runs the script on changes to the paper pages or build tools and uploads `papers-pdf` (both PDFs) as a workflow artifact. No accounts or tokens are needed.

## Limits

This checks internal citation and link integrity, not that a reference is correct. Venue-specific templates (for example a journal LaTeX class) are not produced; the PDF is a print rendering of the page.
