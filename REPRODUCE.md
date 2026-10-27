# Reproduce everything

How a reviewer, officer or reader checks the evidence behind this programme from a clean clone. It covers the eight research repositories the hub links to. Every command below was run by hand in a fresh `git clone --depth 1` of the repository's default branch on 2026-10-27. Where a step could not be run, the entry says so and says why. Nothing here is copied from a README without being run.

The same test commands run every week in the [`reproduce` workflow](.github/workflows/reproduce.yml) (also manual). It has no pull-request trigger, so it never blocks a change to this repository. The page version of this document is [docs/reproduce.html](docs/reproduce.html).

## Environment used

| Item | Value |
|---|---|
| OS | Linux x86_64, 4 cores |
| Python | 3.12.3 (a virtual environment per run). The repositories state a floor of 3.9 and run 3.9 and 3.12 in their own CI; 3.9 was not available here and was not run |
| Python packages, run A | latest at the time: numpy 2.5.4, pandas 3.1.0 (what the repositories' own CI installs, unpinned) |
| Python packages, run B | numpy 2.0.2, pandas 2.3.3 (the versions the repositories state they were developed against) |
| Node | 22.22.0 with npm 10.9.4 (the `ehs-benchmarks` CI uses Node 20) |
| Network | No access to osha.gov (HTTP 403 from the proxy). Raw-data downloads were attempted and failed; see "What needs raw data" |

Every test command passed in both run A and run B. Times below are from run A, wall clock, on a clean clone.

## Quick path

```bash
git clone --depth 1 https://github.com/priyatham9/<repo>.git && cd <repo>
python3 -m venv .venv && . .venv/bin/activate && python -m pip install numpy pandas   # not needed for ehs-chemical-peers or grounding-eval-action
# then the repository's test command from the table below
```

| Repository | Test command (from the repo root) | Result | Time |
|---|---|---|---|
| ehs-osha-analysis | `PYTHONPATH=src python -m unittest discover -s tests` | 279 tests, OK, 18 skipped (the real-data tests skip without `data/raw`) | 31 to 35 s |
| ehs-chemical-peers | `python -m unittest discover -s tests -p "test_*.py"` | 79 tests, OK, 6 skipped (real-data tests) | 9 s |
| ehs-ai-grounding-eval | `python -m unittest discover -s tests` | 182 tests, OK | 14 s |
| ehs-human-factors-ontology | `PYTHONPATH=src python -m unittest discover -s tests -t .` | 215 tests, OK | 2 s |
| ehs-risk-sem | `python -m unittest discover -s tests` | 126 tests, OK | 20 s |
| ehs-capitals-calculator | `PYTHONPATH=src python -m unittest discover -s tests` | 191 tests, OK | 0.4 s |
| ehs-benchmarks | `npm ci && npm test` | 137 tests (vitest), passed | 2 s with a warm npm cache |
| grounding-eval-action | `git clone --depth 1 https://github.com/priyatham9/ehs-ai-grounding-eval.git /tmp/corpus` then `PYTHONPATH=/tmp/corpus:$PWD/runner python -m unittest discover -s tests` | 38 tests, OK | 2 s |

The skipped tests are skipped, not passed: they compare a rebuild from raw data with the committed outputs, so a clean offline clone does not exercise them.

## Per repository

### ehs-osha-analysis

Python, numpy, pandas. 2.8 million OSHA Form 300A filings (2016 to 2024); committed outputs are `outputs/summary.json`, the tables in `outputs/tables/` and the 6 figures in `outputs/figures/`.

Verified offline from a clean clone:

```bash
make test PYTHON=python                                   # 279 tests, 18 skipped, ~32 s
PYTHONPATH=src python -m unittest discover -s tests -p "test_pipeline_on_fixture.py"   # 10 tests on the synthetic fixture, 2.6 s
python scripts/generate_ontology_client.py --check        # "ontology client is up to date", 0.3 s
make ontology PYTHON=python                               # builds build/ontology/ontology.sqlite and .json on the synthetic fixture, 1.2 s
make health PYTHON=python                                 # lineage ok, 260/260 expectations pass, rewrites docs/LINEAGE.md and docs/DATA_HEALTH.md with no change to the committed copies, 0.4 s
ruff check .                                              # All checks passed (ruff 0.17.3)
```

Not run, needs raw data: `make data` then `make analysis` (`PYTHONPATH=src python3 scripts/run_analysis.py`) regenerates `outputs/` and `summary.json`. The repository's `REPRODUCIBILITY.md` records 93.4 s for the pipeline and 165 s for the full test suite on the author's macOS machine, plus SHA-256 digests of all nine input files, so a regenerated file can be checked against the digest. Its headline check values, for example pooled aggregate TRIR (screened) 3.983078949653959 over 2,801,064 filings, are in `outputs/summary.json` under `quality.pooled`. `make data` failed here at the first file with a proxy 403.

One step in that repository's README does not work from a standalone clone: `python3 ../../tools/build_sites.py` assumes the author's multi-repository working layout.

### ehs-chemical-peers

Standard library only (Python 3.9+). OSHA injury logs, EPA Risk Management Program accident histories and OSHA severe injury reports joined for NAICS 325 plants; committed outputs are `outputs/summary.json`, `docs/data/*.json` and the tables in `docs/paper.md`.

Verified offline from a clean clone:

```bash
make test PYTHON=python                                   # 79 tests, 6 skipped, ~9 s
python scripts/paper_tables.py                            # "wrote 9 tables to docs/paper.md"; git diff shows no change
python scripts/build_compare.py                           # "48 groups, 358 tested pairs"; git diff shows no change
make ontology PYTHON=python                               # exports build/ontology from the committed data, 1.8 s
ruff check .                                              # All checks passed
```

The two regeneration commands rebuild committed files and leave `git diff -- docs` empty, which is what the workflow checks.

Not reproduced offline:

- `make data` downloads 14 files, about 300 MB: ten from osha.gov and four (`facilities.csv`, `submissions.csv`, `accidents.csv`, `naics-codes.csv`) from the Data Liberation Project's `epa-rmp-spreadsheets` repository on raw.githubusercontent.com. It failed here at the first osha.gov file. It writes `data/raw/manifest.json` with SHA-256 digests.
- `make build` (about 11 s on the author's laptop once the data exists) failed here with `FileNotFoundError` for `data/raw/submissions.csv`, as expected without the download.
- `make pages` failed: `scripts/build_story.py` expects the author's multi-repository layout (`tools/inline_story.py` two directories up). It also left `docs/story.html` modified, so run `git checkout docs` after trying it.

`REPRODUCIBILITY.md` states the source files change each spring, so a rebuild against newer files will change the numbers; `docs/data/meta.json` records which file digests a build used.

### ehs-ai-grounding-eval

Python, numpy, pandas. 68 items sourced from 29, 40 and 46 CFR. Committed outputs are in `results/` (baseline run files, `baselines_table.md`, `baselines_summary.csv`, `baselines_breakdown.*`).

Verified offline from a clean clone:

```bash
python -m unittest discover -s tests                      # 182 tests, OK, ~14 s
python -m grounding_eval.cli corpus                       # describe the corpus
python -m grounding_eval.cli validate                     # corpus and stored source verification
python -m grounding_eval.cli demo                         # labelled mock demonstration, 1.5 s for the three commands
python -m grounding_eval.run_baselines                    # six non-LLM baselines, 3.8 s
python tools/verify_sources.py --offline                  # "offline recheck: OK" against the committed eCFR report, 0.1 s
python tools/corpus_stats.py                              # per-domain counts
ruff check .                                              # All checks passed
```

`run_baselines` rewrote the six `results/baselines_*.json` run files. `baselines_table.md`, `baselines_summary.csv` and the breakdown files came out unchanged. In the run files the only differences are timing fields, platform and Python version, the run start time, and last-digit floating-point noise in one retriever's similarity values (for example 0.4428798088881202 against 0.4428798088881201). The scored results are the same.

Not run: `python tools/verify_sources.py` without `--offline` re-fetches the cited text from the eCFR and needs network; `scripts/run_baselines.sh` calls the Anthropic API and refuses to run without `ANTHROPIC_API_KEY`. No language model has been evaluated in this repository's committed results.

### ehs-human-factors-ontology

Python, numpy, pandas for the tests. Committed outputs: `crosswalk/crosswalk.md` and `.csv`, `synthetic/scenarios`, `incidents/suggester_eval.md`, `incidents/csb_coding.md`, the methods-note statistics and `docs/suggester.html`.

Verified offline from a clean clone, all with an unchanged working tree afterwards:

```bash
PYTHONPATH=src python -m unittest discover -s tests -t .  # 215 tests, OK, ~2 s
python tools/build_crosswalk.py --check                   # "crosswalk is up to date"
python synthetic/generate_scenarios.py --check            # "synthetic corpus is reproducible (48 scenarios)"
PYTHONPATH=src python tools/methods_note_stats.py --check # exit 0
python tools/build_crosswalk.py                           # regenerate in place, no diff
python synthetic/generate_scenarios.py                    # regenerate in place, no diff (seed 20260904)
PYTHONPATH=src python tools/evaluate_suggester.py --write
PYTHONPATH=src python tools/methods_note_stats.py --write
PYTHONPATH=src python tools/build_csb_coding.py --write
PYTHONPATH=src python tools/build_suggester_page.py --write   # each ~0.1 s, no diff
PYTHONPATH=src python -m ehs_hfo assess examples/reactor_startup_nonroutine.json
ruff check .                                              # All checks passed
```

No raw data is needed. The inputs are hand-coded and cited in the repository.

### ehs-risk-sem

Python, numpy, pandas. Simulation studies on synthetic data only; committed outputs are the 21 tables in `results/`.

Verified from a clean clone:

```bash
python -m unittest discover -s tests                      # 126 tests, OK, ~20 s
python simulations/run_all.py --quick                     # 10 s, writes results_quick/ (git-ignored), does not touch results/
python simulations/run_all.py                             # full rerun, 351 s here (the README says about 11.5 minutes), rewrites results/
```

The full rerun does not give byte-identical files. With the same seeds and a newer numpy and pandas, 13 of the 21 tables changed. Numeric differences are at floating-point round-off: the largest absolute difference was 1.1e-11 and the largest relative difference 7.4e-14, and no non-numeric cell changed. Compare with a tolerance, not with `git diff`. Restore the committed tables with `git checkout results`.

Side effect to know about: running the test suite rewrites 14 files under `docs/api/` (the API-docs test regenerates them without the site header). Run `git checkout docs` afterwards to get a clean tree.

`python simulations/run_all.py` uses no downloaded data. `synthetic/generate_synthetic_datasets.py` regenerates the three labelled synthetic datasets.

### ehs-capitals-calculator

Python 3.9+, numpy only for the Monte Carlo module. There are no committed generated outputs; the published figures from the cited worked example are pinned by tests.

```bash
PYTHONPATH=src python -m unittest discover -s tests       # 191 tests, OK, 0.4 s
python src/cli.py example                                 # the published comparison, instant
python src/cli.py montecarlo --samples 100000             # fixed default seed, 0.2 s
ruff check .                                              # All checks passed
```

No raw data is needed. The Monte Carlo spreads are labelled illustrative placeholders in the tool's own output.

### ehs-benchmarks

TypeScript, Node. Committed outputs are the benchmark tables under `docs/data/`, built from OSHA's establishment-level filings for 2023 to 2025.

Verified from a clean clone:

```bash
npm ci && npm test                                        # 137 tests passed, ~2 s with a warm cache
npm run build                                             # tsc, 0.5 s
```

The repository's README says 106 tests; the run shows 137, so that line is out of date.

Not run, needs raw data: `node scripts/build-benchmarks.mjs <rawDataDir>` regenerates `docs/data/`. The raw files (about 700 MB per the README, from OSHA's establishment-specific data page) are not committed and are expected at the paths named at the top of the script: `sum2023/ITA 300A Summary Data 2023 through 12-31-2024_v2.csv`, `sum2024/ITA_300A_Summary_Data_2024_through_12-31-2025_v2.csv`, `ita2025.csv` and `case2024/ITA_Case_Detail_Data_2024_through_12-31-2025.csv`. osha.gov was unreachable here.

### grounding-eval-action

A composite GitHub Action that runs the grounding benchmark against an HTTP endpoint.

```bash
git clone --depth 1 https://github.com/priyatham9/ehs-ai-grounding-eval.git /tmp/corpus
PYTHONPATH=/tmp/corpus:$PWD/runner python -m unittest discover -s tests   # 38 tests, OK, ~2 s
PYTHONPATH=/tmp/corpus python runner/run.py --endpoint-url http://127.0.0.1:1/unused --mode dry-run --results-dir results --badge
```

The dry run makes no network calls and wrote `results/run.json` (68 requests, `is_mock_demonstration` false), `results/summary.md` and `badge/grounding.svg`, all untracked. Live mode needs an endpoint you control; the repository's own `self-test` workflow exercises it against a local mock endpoint in CI, which was not rerun here.

## What needs raw data downloads

These cannot be completed offline and were not run in the environment used for this page. In each case the committed outputs, the tests that do run, and the digests recorded by the repository are what a reviewer can check without the download.

| Step | Source | Size stated by the repository |
|---|---|---|
| `ehs-osha-analysis`: `make data`, then `make analysis` | nine OSHA Injury Tracking Application summary zips, osha.gov/itadata | about 170 MB (nine files, 169 MB by the digests table) |
| `ehs-chemical-peers`: `make data`, then `make build` | ten osha.gov files and four EPA RMP extracts from the Data Liberation Project on GitHub | about 300 MB |
| `ehs-benchmarks`: `node scripts/build-benchmarks.mjs` | OSHA establishment-specific injury and illness data | about 700 MB |
| `ehs-ai-grounding-eval`: `tools/verify_sources.py` (online) | eCFR | small; needs network |
| `ehs-ai-grounding-eval`: `scripts/run_baselines.sh` | Anthropic API | billed API calls; needs a key |

The workflow therefore runs the test suites and the offline "is the committed output current" checks, and says so in its run summary. It does not download these files.

## Using the workflow

Run it from the Actions tab (`reproduce`, "Run workflow") or wait for the weekly schedule (Mondays 07:37 UTC). Each repository is one matrix row. The run page ends with a table of repository, commit, test result, output-check result and verdict. A red row means that repository's default branch no longer passes its documented commands from a clean clone; it does not affect pull requests here.

The workflow installs the latest numpy and pandas, as the repositories' own CI does. If a row fails after a dependency release, run B above (numpy 2.0.2, pandas 2.3.3) is the reference environment.
