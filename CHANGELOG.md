# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog and this project uses semantic versioning.

## [Unreleased]

### Changed
- `docs/status.json` refreshed from the public repositories (was a 2026-09-26 snapshot). Counts are now a static count of test functions (`tools/refresh_status.py`, ast over `test_*.py` in a depth-1 clone), not a test run: they include tests that skip at run time, so OSHA reads 249 against 178 "Ran" before. The grounded entry now counts its own 14 claims-checker tests. The observatory tile is relabelled "Test functions" (it no longer claims "all passing"), and the story, OSHA paper and `claims/claims.json` quote the new counts.

### Added
- `tools/refresh_status.py` and `.github/workflows/status.yml`: weekly check (no PR is opened) that fails when the committed snapshot is over 14 days old or its counts, tags or headline figures differ from a fresh recount.

### Fixed
- `docs/story.html`: OSHA test count 175 corrected to 178 (docs/status.json) and "31 of 80 mappings" reworded to "31 of 80 cells" (20 factors x four frameworks, `docs/crosswalk-data.json` in the ontology repo; the 96-row CSV is a different unit). Both are now asserted claims in `claims/claims.json`, which gains a `json_count` source kind; the known-discrepancies list is empty.

### Added
- Headline-claims registry (`claims/claims.json`): 20 claims from the site and both papers, each with where it is stated, the committed source file and key in the owning repo, and the verifying test; `claims/check_claims.py` fetches those files from raw.githubusercontent.com and a weekly and per-PR `claims` workflow fails if any claim stops matching. Two stale site statements (175 tests, 31 of 80 mappings) are recorded as known discrepancies
- Programme metric dictionary (`metrics/`): TRIR, DART, LTIR, severity and fatality rate with 29 CFR 1904 sources, plus a cross-implementation agreement test (TypeScript vs Python reference vectors) run in CI
- Hub: story-arc labels on each chapter, a scroll-drawn narrative thread on wide screens, word-mask heading reveals, constellation line draw, and a closing "so what" section with three questions for a VP of EHS

### Fixed
- OSHA paper: all 45 references verified on 2026-10-27 and recorded in `docs/references-osha.csv`; corrected Steiger (1979) issue, Kuhn et al. (2023) venue label, the ITA users guide date and the OSHA ITA page title; added missing issue, page and DOI details; reworded eight sentences to match what their sources say
- Changelog regenerated through 2026-09-20 with linkable day anchors; RSS feed now uses RFC 822 dates, an atom:self link, and anchors that resolve
- Broken PANEL.md link on the hub; horizontal overflow on start.html at phone width; changelog added to the sitemap

## [0.1.0] - 2026-09-09

### Added
- Landing site for research programme on grounded reasoning for safety-critical AI in EHS and process industries
- Static HTML page presenting programme findings and linking to six supporting repositories
- Design system matching priyatham9.github.io with cobalt accent colour and light/dark theme support
- Empirical figures from public OSHA Injury Tracking Application data, with draft status and incomplete reference verification clearly stated
