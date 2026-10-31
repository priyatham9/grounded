# Figure and table regeneration (docs/paper-osha.html)

`python3 tools/regenerate_figures.py` rebuilds what it can from committed data
and compares it with what the paper embeds. `python3 -m unittest tools.test_figures`
fails if a committed figure or table differs. CI runs both (`claims` workflow).

The only numeric source committed in this repository is Table 3 of the paper, a
verbatim copy of `ehs-osha-analysis/outputs/tables/quality_by_year.csv`.
Its values are rounded (shares to 4-5 decimals, TRIR to 3), so figure
coordinates are compared to within 0.05 px, not byte for byte.

| Item | Status |
|---|---|
| Figure 1 (fig02_hours_share_implausible) | regenerable from Table 3; matches within 0.02 px |
| Figure 3 (fig01_aggregate_trir_by_year) | regenerable from Table 3; matches within 0.04 px |
| Table 1 (year-level summary) | regenerable from Table 3; matches (Ratio column checked to 0.5%, Table 3 carries it rounded) |
| Table 2 (denominator failure) | rows 1-5 regenerable exactly from Table 3; screened TRIR and ratio checked to 1% only (need unrounded flagged hours/cases) |
| Table 3 (plausibility screen by year) | is the source copy; not derived here |
| Figure 2 (fig03_hours_per_employee) | not regenerable: needs per-filing hours-per-employee histogram, not committed here |
| Figure 4 (fig04_count_model_fit) | not regenerable: needs observed/fitted NAICS 238 count distributions, not committed here |
| Figure 5 (fig05_zero_share_by_size) | not regenerable: needs detectability_by_size_band.csv, not committed here |
| Figure 6 (fig06_percentile_stability) | not regenerable: needs peer_percentiles_by_year.csv pairs, not committed here |
| Figure 7 (fig08_panel_persistence) | not regenerable: needs panel_permutation.csv / panel_transitions.csv, not committed here |
| Table 4 (count-model selection) | not regenerable: count_model_selection_summary.csv not committed here |

Figures 2 and 4-7 and Table 4 are produced by `ehs-osha-analysis`
(`src/ehs_osha/pipeline.py`, `svgplot.py`) from its committed outputs. Full
regeneration needs that repository checked out; this repository has no copy of
its CSVs.

`docs/paper.html` (3 figures, 6 tables) was not assessed in this change.
