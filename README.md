# grounded

[![docs](https://github.com/priyatham9/grounded/actions/workflows/links.yml/badge.svg)](https://github.com/priyatham9/grounded/actions/workflows/links.yml)
[![site](https://img.shields.io/badge/site-priyatham9.github.io%2Fgrounded-1E40AF)](https://priyatham9.github.io/grounded/)

Landing site for a research programme on grounded reasoning for safety-critical AI in EHS and process industries. It presents the programme's findings and links seven repositories. The programme is in draft status. The bundled paper has 197 references; 197 of the 197 were re-checked on 2026-10-28, 2026-10-29 and 2026-10-30: 105 verified, 21 corrected, 4 with a reworded sentence, 56 with metadata matched but the citing sentence not yet read against the source, and 11 unreachable from the sandbox; see the [reference ledger](docs/references-paper.csv). All 45 references in the standalone OSHA paper were verified on 2026-10-27 (each resolves, its metadata matches the publisher record, and the citing sentence matches the source); see the [reference ledger](docs/references-osha.csv). No external peer review has been conducted on either paper.

The site at `docs/index.html` is a static page with no build step and no runtime
dependencies beyond two webfonts. It presents the programme's findings, links the
seven repositories that make it up, and states plainly what has and has not been
established.

The [proposed endeavour page](docs/endeavour.html) sets out a three-year plan built only from the work that exists, with plans labelled as plans and no results claimed.

[REPRODUCE.md](REPRODUCE.md) (page: [docs/reproduce.html](docs/reproduce.html)) gives, for each of the eight research repositories, the commands to run its tests and regenerate its committed outputs from a clean clone, with runtimes, versions and the steps that need raw-data downloads. The weekly [`reproduce` workflow](.github/workflows/reproduce.yml) reruns the test commands and reports a status table; it never runs on pull requests.

The [methods and limitations ledger](docs/methods-ledger.html) ([JSON](docs/methods-ledger.json)) lists, per repository, each statistical or machine-learning method, its assumptions and its stated limitations, each linked to the file and quoting the sentence where the repository says it. `tools/check_ledger.py` and the `ledger` workflow fail if a linked file or quote is missing from the repositories' public GitHub copies.

## At a glance

- Status: draft
- Data: real (OSHA Injury Tracking Application data)
- Quickstart: open `docs/index.html` directly, or serve `docs/` with any static file server
- Licence: MIT

## Why this repo is separate

The work spans seven repositories. Rather than duplicating context in each README,
this one holds the overview and links outward. Cross-links back from the individual
repositories are deliberately not wired up yet - they go in once the site's quality
has been reviewed.

## Design

Matches the design system of priyatham9.github.io: Archivo variable at
`font-stretch: 125%` for display type, IBM Plex Mono for labels and navigation,
2px hard rules with no border radius, radial dot-grid on the hero. The accent
differs - cobalt `#1E40AF` light, `#7C9EFF` dark - so the two read as siblings
rather than copies. Full light/dark support with a persisted manual override.

## Status

Draft. Empirical figures on the page come from real public OSHA Injury Tracking
Application data. The bundled paper has 197 references; 197 of the 197 were re-checked on 2026-10-28, 2026-10-29 and 2026-10-30: 105 verified, 21 corrected, 4 with a reworded sentence, 56 with metadata matched but the citing sentence not yet read against the source, and 11 unreachable from the sandbox. Results and fixes are in
[docs/references-paper.csv](docs/references-paper.csv). The standalone
OSHA paper's 45 references were verified on 2026-10-27: 45 of 45 resolve and match
their sources, with corrections recorded in
[docs/references-osha.csv](docs/references-osha.csv). No external peer review has been
conducted. The page says so on itself.

## Security

See [SECURITY.md](SECURITY.md) for security policy and how to report vulnerabilities.

## Licence

MIT
