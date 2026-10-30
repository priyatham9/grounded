#!/usr/bin/env bash
# Build submission PDFs of the papers in docs/ with headless Chrome/Chromium.
# Usage: tools/build_papers.sh [outdir]   (default: build/papers)
# Env:   CHROME=/path/to/chrome to override browser detection.
# Fails on any page check problem, missing browser, or empty/unreadable PDF.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-build/papers}"
PAPERS="paper paper-osha"

python3 tools/check_paper_html.py

CHROME="${CHROME:-$(command -v google-chrome chromium chromium-browser 2>/dev/null | head -n1 || true)}"
if [ -z "$CHROME" ]; then
  echo "error: no Chrome/Chromium found (set CHROME=...)" >&2
  exit 2
fi
mkdir -p "$OUT"
for p in $PAPERS; do
  rm -f "$OUT/$p.pdf"
  "$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=20000 --print-to-pdf="$OUT/$p.pdf" \
    "file://$PWD/docs/$p.html" >/dev/null 2>&1 || true
  [ -s "$OUT/$p.pdf" ] || { echo "error: $p.pdf was not produced" >&2; exit 1; }
  head -c 5 "$OUT/$p.pdf" | grep -q '^%PDF-' || { echo "error: $p.pdf is not a PDF" >&2; exit 1; }
  if command -v pdfinfo >/dev/null; then
    pages=$(pdfinfo "$OUT/$p.pdf" | awk '/^Pages:/{print $2}')
    [ "${pages:-0}" -ge 5 ] || { echo "error: $p.pdf has only ${pages:-0} pages" >&2; exit 1; }
    echo "$p.pdf: $pages pages, $(stat -c %s "$OUT/$p.pdf") bytes"
  else
    echo "$p.pdf: $(stat -c %s "$OUT/$p.pdf") bytes (pdfinfo not installed; page count unchecked)"
  fi
done
