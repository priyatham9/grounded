# Vendored source CSVs for docs/paper-osha.html

Byte-for-byte copies of committed files from `priyatham9/ehs-osha-analysis`,
taken from commit `3ac278e19a1076fe50936a83484fed7be99855d2` (main at the time
of copying), path `outputs/tables/<name>`. Nothing was edited, filtered or
recomputed. `SOURCE.json` records, per file, the source path, the git blob SHA
at that commit and the commit that last changed it; `tools/test_figures.py`
recomputes each blob SHA and fails if a file here has been altered.

| File | Used for |
|---|---|
| `size_band_effects.csv` | Figure 5 |
| `count_model_covariates_fit_detail.csv`, `count_model_covariates.csv` | Figure 4 (observed/fitted counts and n for NAICS 238) |
| `peer_percentiles_by_year.csv` | Figure 6 |
| `panel_transitions.csv`, `panel_permutation.csv` | Figure 7 |
| `count_model_selection_summary.csv` | Table 4 |

To refresh: copy the files from a newer `ehs-osha-analysis` commit, update
`SOURCE.json`, and run `python3 tools/regenerate_figures.py`. A mismatch with
the paper means the paper or the source data changed and needs a decision; do
not edit the paper numbers to fit.
