# Figure and table regeneration (docs/paper-osha.html)

`python3 tools/regenerate_figures.py` rebuilds what it can from committed data
and compares it with what the paper embeds. `python3 -m unittest tools.test_figures`
fails if a committed figure or table differs. CI runs both (`claims` workflow).

Sources: Table 3 of the paper (a verbatim copy of
`ehs-osha-analysis/outputs/tables/quality_by_year.csv`, values rounded, so
figures derived from it are compared to within 0.05 px) and the CSVs vendored
in `data/osha-source/` (byte-for-byte copies from `ehs-osha-analysis` commit
`3ac278e`, provenance in `data/osha-source/README.md` and `SOURCE.json`; these
are full precision, so figures derived from them must match exactly).

9 of the 10 numeric items (Figures 1-7, Tables 1, 2, 4) are regenerable and
match; Table 3 is itself the source copy and Figure 2 is not regenerable.

| Item | Status |
|---|---|
| Figure 1 (fig02_hours_share_implausible) | regenerable from Table 3; matches within 0.02 px |
| Figure 2 (fig03_hours_per_employee) | not regenerable: needs the per-filing hours-per-employee histogram (90 bin counts); no committed CSV in `ehs-osha-analysis` holds it, only the SVG output |
| Figure 3 (fig01_aggregate_trir_by_year) | regenerable from Table 3; matches within 0.04 px |
| Figure 4 (fig04_count_model_fit) | regenerable from `count_model_covariates_fit_detail.csv` and `count_model_covariates.csv`; exact match |
| Figure 5 (fig05_zero_share_by_size) | regenerable from `size_band_effects.csv`; exact match |
| Figure 6 (fig06_percentile_stability) | regenerable from `peer_percentiles_by_year.csv`; exact match (469 matched peer groups) |
| Figure 7 (fig08_panel_persistence) | regenerable from `panel_transitions.csv` and `panel_permutation.csv`; exact match |
| Table 1 (year-level summary) | regenerable from Table 3; matches (Ratio column checked to 0.5%, Table 3 carries it rounded) |
| Table 2 (denominator failure) | rows 1-5 regenerable exactly from Table 3; screened TRIR and ratio checked to 1% only (need unrounded flagged hours/cases) |
| Table 3 (plausibility screen by year) | is the source copy; not derived here |
| Table 4 (count-model selection) | regenerable from `count_model_selection_summary.csv`; exact match |

Figure 2 is produced by `ehs-osha-analysis` (`src/ehs_osha/pipeline.py`) from
the per-filing data, which is not committed there either. The titles,
subtitles and axis labels of Figures 4-7 are fixed text in the script; the
numbers in them (n, permutation count, seed, matched groups) come from the CSVs.
Figures 4 and 7 are rendered in the older sans-serif style with a legend; the
script reproduces that style so the SVG text is identical.

`docs/paper.html` (3 figures, 6 tables) was not assessed in this change.
