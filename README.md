# grounded

[![docs](https://github.com/priyatham9/grounded/actions/workflows/links.yml/badge.svg)](https://github.com/priyatham9/grounded/actions/workflows/links.yml)
[![site](https://img.shields.io/badge/site-research%20programme-1E40AF)](https://grounded-chi-five.vercel.app/)

Landing site for a research programme on grounded reasoning for safety-critical AI in EHS and process industries. It presents the programme's findings and links seven repositories. The programme is in draft status. The bundled paper has 197 references; 197 of the 197 were re-checked on 2026-10-28, 2026-10-29 and 2026-10-30: 106 verified, 21 corrected, 4 with a reworded sentence, 55 with metadata matched but the citing sentence not yet read against the source, and 11 unreachable from the sandbox; see the [reference ledger](docs/references-paper.csv). All 45 references in the standalone OSHA paper were verified on 2026-10-27 (each resolves, its metadata matches the publisher record, and the citing sentence matches the source); see the [reference ledger](docs/references-osha.csv). No external peer review has been conducted on either paper.

The site at `docs/index.html` is a static page with no build step and no runtime
dependencies. It presents the programme's findings, links the
seven repositories that make it up, and states plainly what has and has not been
established.

The [investigations page](docs/investigations.html) connects four new audits of
decision-relevant evidence: OSHA record influence, a finite excerpt/scorer
ceiling, simulated contrast-test calibration, and representation loss. These are
different forms of evidence, not a pooled result. With the project repositories
in sibling directories, `python3 tools/build_investigations.py` regenerates its
HTML and SHA-256 source manifest; `--check` verifies them. Page structure lives in
`tools/investigations.template.html`, with static CSS and JavaScript in `docs/`.

The four-page [research brief (PDF)](docs/research-brief.pdf), also available as
[HTML](docs/research-brief.html), presents the findings, practical review steps
and limits in a shareable format. Its [content and build manifest](docs/research-brief-manifest.json)
binds each source artifact by SHA-256 and records the generation time. Rebuild
with `python3 tools/build_research_brief.py`; verify with `--check`. This uses
installed Node/Playwright Chromium, `pdfinfo` and `pdftotext`, with no network or
model calls. `--generated-at` accepts the recorded UTC timestamp to reproduce
the content; PDF metadata may change, so byte-identical PDF regeneration is not
claimed. These are independent working findings, not peer-reviewed results.

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

The landing page uses an editorial research layout: offwhite `#f7f7f2`, ink
`#172824`, emerald `#136c50`, serif display typography and system sans-serif text.
Question-based entry points lead to the seven projects, working papers and an
explicit evidence and limitations section. The responsive layout includes keyboard
focus indicators, a skip link, semantic navigation and reduced-motion support.
No build step, JavaScript or external font downloads are required for the landing page.

## Status

Draft. Empirical figures on the page come from real public OSHA Injury Tracking
Application data. The bundled paper has 197 references; 197 of the 197 were re-checked on 2026-10-28, 2026-10-29 and 2026-10-30: 106 verified, 21 corrected, 4 with a reworded sentence, 55 with metadata matched but the citing sentence not yet read against the source, and 11 unreachable from the sandbox. Results and fixes are in
[docs/references-paper.csv](docs/references-paper.csv). The standalone
OSHA paper's 45 references were verified on 2026-10-27: 45 of 45 resolve and match
their sources, with corrections recorded in
[docs/references-osha.csv](docs/references-osha.csv). No external peer review has been
conducted. The page says so on itself.

## Security

See [SECURITY.md](SECURITY.md) for security policy and how to report vulnerabilities.

## Licence

MIT

## Project interface research

[Current interface references and build specification](docs/PROJECT_DESIGN_RESEARCH.md) compares 14 official product/design-system references, identifies five live-tested interactions, and specifies three different analytical workflows. This is an interface review, not a user study.
