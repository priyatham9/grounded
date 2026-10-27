# Programme metric dictionary

One canonical definition per metric used across the programme repositories, with its
29 CFR 1904 source and a test that the TypeScript (`ehs-benchmarks`) and Python
(`ehs-osha-analysis`) implementations agree. The machine-readable source of truth is
[`dictionary.json`](dictionary.json); this page is its readable form.

Independent work; not affiliated with OSHA or any employer.

## Basis and aggregation

- Basis: every rate is per 200,000 hours worked (100 full-time employees x 40 h/week x 50 weeks).
  This constant and the rate formulas come from OSHA guidance on calculating incidence rates for
  Forms 300/300A, not from the text of 29 CFR 1904
  ([OSHA guidance, copy hosted by NJ Dept. of Labor](https://www.nj.gov/labor/safetyandhealth/assets/PDFs/Survey/form300.pdf)).
- Aggregation: ratio of sums (total cases over total hours), never a mean of establishment rates.
  This is a programme convention (`ehs_osha.metrics` docstring), not a regulatory requirement.
- Denominator: total hours worked by all employees covered by the OSHA 300 Log,
  29 CFR 1904.32(b)(2)(ii); supervised non-payroll workers are covered by the log under
  29 CFR 1904.31(a), 1904.31(b)(2) and 1904.31(b)(4). `ehs-benchmarks` exposes this as
  `contractorBasis` (`employee-only` default, or `combined`).
- Undefined rate: when hours <= 0 the rate is not computable. TypeScript returns `null`,
  Python returns `NaN`; neither is ever reported as 0.

## Metrics

| id | Formula | Form 300A columns | 29 CFR 1904 source |
|---|---|---|---|
| trir | 200000 * (G + H + I + J) / hours | G deaths, H days-away cases, I job transfer or restriction cases, J other recordable cases | 29 CFR 1904.7(a); 29 CFR 1904.7(b)(2); 29 CFR 1904.7(b)(3); 29 CFR 1904.7(b)(4); 29 CFR 1904.32(b)(2)(ii) |
| dart | 200000 * (H + I) / hours | H, I | 29 CFR 1904.7(b)(3); 29 CFR 1904.7(b)(4); 29 CFR 1904.32(b)(2)(ii) |
| ltir | 200000 * H / hours | H | 29 CFR 1904.7(b)(3); 29 CFR 1904.32(b)(2)(ii) |
| severity | 200000 * (K + L) / hours | K total days away, L total days of job transfer or restriction | 29 CFR 1904.7(b)(3)(i); 29 CFR 1904.7(b)(3)(ii); 29 CFR 1904.7(b)(3)(vii); 29 CFR 1904.7(b)(4); 29 CFR 1904.32(b)(2)(ii) |
| fatality | 200000 * G / hours | G | 29 CFR 1904.7(b)(2); 29 CFR 1904.32(b)(2)(ii) |

What the cited paragraphs say (read on law.cornell.edu's copy of the eCFR, 2026-10-27):

- 1904.7(a): an injury or illness is recordable if it results in death, days away from work,
  restricted work or transfer to another job, medical treatment beyond first aid, or loss of consciousness
  (or is a significant diagnosed injury or illness).
- 1904.7(b)(2): death is recorded with a check mark in the death space of the 300 Log.
- 1904.7(b)(3): days-away cases are checked in the days-away space with the number of calendar days away;
  (i) counting begins the day after the injury or illness onset; (ii) enter the days recommended by the
  health care professional; (vii) the employer may cap total days away at 180.
- 1904.7(b)(4): restricted work or job transfer cases (without death or days away) are recorded in the
  job transfer or restriction space with the number of restricted or transferred days.
- 1904.32(b)(2)(ii): the annual summary shows the annual average number of employees and the total hours
  worked by all employees covered by the OSHA 300 Log.

Notes: LTIR is days-away cases only (some industry usage includes restricted cases, which is DART).
`fatality` exists only in TypeScript; Python includes deaths in TRIR and has no separate rate.
Severity per case is bounded when the 180-day cap is used.

## Agreement test

Files in this directory:

- `vector_inputs.json`: six hand-written input vectors (typical, fatality, single case on 10,000 h,
  zero cases, fractional hours, zero hours).
- `generate_vectors.py`: runs the real implementations on those inputs and writes `vectors.json`,
  recording the git commit of each repo (`ehs-benchmarks` 0026fd27, `ehs-osha-analysis` fb3ce46 at generation).
  Run it from the repo root with
  `python3 metrics/generate_vectors.py --osha-analysis ../ehs-osha-analysis --benchmarks ../ehs-benchmarks`
  (needs pandas, numpy and Node >= 22.6; the TypeScript is executed with `--experimental-strip-types`,
  no npm install).
- `agreement_test.py` and `agreement_test.mjs`: run in CI (`.github/workflows/metrics.yml`) with only the
  standard library. They assert that the two implementations agree to 1e-9 relative on every vector,
  that an independent implementation of the dictionary formulas reproduces both, that zero hours is null
  not 0, and that the dictionary is complete and cited.

CI does not recompute the vectors (the other repos are not dependencies of this site); when either
implementation changes, rerun the generator and commit the new `vectors.json`. A drift between the
implementations, or between either and the dictionary, shows up as a failing diff on regeneration.
