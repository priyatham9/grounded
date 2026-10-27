# grounded

[![docs](https://github.com/priyatham9/grounded/actions/workflows/links.yml/badge.svg)](https://github.com/priyatham9/grounded/actions/workflows/links.yml)
[![site](https://img.shields.io/badge/site-priyatham9.github.io%2Fgrounded-1E40AF)](https://priyatham9.github.io/grounded/)

Landing site for a research programme on grounded reasoning for safety-critical AI in EHS and process industries. It presents the programme's findings and links seven repositories. The programme is in draft status. All 197 references in the paper are checked against a primary or publisher-of-record source, a few page ranges still need confirming, and no external peer review has been conducted.

The site at `docs/index.html` is a static page with no build step and no runtime
dependencies beyond two webfonts. It presents the programme's findings, links the
seven repositories that make it up, and states plainly what has and has not been
established.

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
Application data. The paper's 197 references are checked against primary or
publisher-of-record sources, with a few page ranges still to confirm. No external
peer review has been conducted. The page says so on itself.

## Security

See [SECURITY.md](SECURITY.md) for security policy and how to report vulnerabilities.

## Licence

MIT
