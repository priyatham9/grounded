# Project interface research and implementation specification

Research date: 2026-11-16. Scope: the EHS, AI evidence, SEM, ontology, local CSV, CRM, finance and data-contract projects. The personal homepage is outside this scope.

The strongest direction is an **auditable decision workbench**: show a bounded claim, let the reader change or inspect its basis, and preserve enough state to reproduce the resulting judgment. The current projects have substantive calculations and evidence. Their next design improvements should reduce the distance between an action and its consequence, rather than add dashboard decoration.

This is a comparative interface review conducted after the current prototypes were built, not a preregistered user study. It establishes observable patterns and proposed acceptance criteria; it does not establish that users prefer these designs or complete tasks faster.

## Five references to examine first, ranked

Evidence labels: **L** = public interface loaded and the named interaction was exercised; **V** = official documentation and its product screenshots were visually inspected, but the product interaction was not executed; **D** = official documentation read, with execution unverified. A live documentation page is not a live product test.

### 1. Carbon — selection becomes an explicit work state · L

[Current batch-action demo](https://react.carbondesignsystem.com/iframe.html?id=components-datatable-batch-actions--default&viewMode=story) · [Current table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)

Observed: selecting two of six rows displayed “2 items selected” and a blue action toolbar; Cancel cleared all six checkboxes. The inspected Storybook identified `@carbon/react@1.120.0`; the guidance page displayed an update date of September 30, 2026. These are observed page identifiers, not a claim about every deployed Carbon application.

Apply to the local CSV review: keep the selected-record count and joint-exclusion consequence beside the table where selection happens. “Review selected” must preserve the distinction between the viewing filter and the exclusion set. Adopt explicit cancel/reset behavior. Do not borrow Delete: excluding a record here is a reversible analytical scenario, not a source-data mutation.

### 2. LangSmith — compare the same example under two conditions · V

[Experiment comparison workflow](https://docs.langchain.com/langsmith/compare-experiment-results)

Observed in official screenshots: aligned experiment columns, highlighted output differences and a details panel. The documentation describes choosing a source experiment, filtering regressions, compact/full/diff views, and opening an example to compare details or traces. No authenticated LangSmith experiment was accessed.

Apply to the AI audit: show the same question with Own and Bare responses together when inspecting metadata sensitivity. Keep their scorer gates aligned, and identify precisely which response wrapper changed. This is a more relevant pattern than a chat transcript. The source describes red/green improvement conventions; our audit should use textual pass/fail labels because a lexical pass is not necessarily a better answer.

### 3. Cloudscape — comparison without abandoning the collection · L

[Live comparison demo](https://cloudscape.design/examples/react/split-panel-comparison.html) · [Split-view guidance](https://cloudscape.design/patterns/resource-management/view/split-view/)

Observed: selecting two instance rows changed the collection count to 2/50 and opened a comparison area with both IDs as column headers and aligned attributes beneath them. The list remained available. This is an official design-system demonstration; its own notice says it may differ from current AWS service interfaces.

Apply to finance: compare a frozen custom policy with the current edited policy in a compact, aligned summary, while keeping assumptions accessible. Apply to data contracts: retain the consumer list while inspecting one dependency path. Avoid opening a modal for every row or requiring users to remember values from a previous screen.

### 4. Grafana Play — a displayed result has an inspectable data basis · L

[Public sandbox](https://play.grafana.org/) · [Observed home dashboard](https://play.grafana.org/d/to6j8mh/grafana-play-home)

Observed: the contributor panel menu exposed Inspect; its Data view opened a panel with Data, Stats, Query and JSON tabs, a formatted-data option, a data table and Download CSV. The inspected data view showed underlying rows whose fields differed from the visible contributor summary. We did not validate the dashboard’s aggregation or download its data.

Apply to EHS and SEM: provide a direct path from a visible result to its exact input counts, selected condition and source artifact. Inspecting underlying rows is a distinct action from exporting the displayed summary. Do not import the entire monitoring shell, alert terminology or real-time refresh behavior into static research artifacts.

### 5. DataHub — impact is a scoped dependency question · V

[Lineage impact analysis](https://docs.datahub.com/docs/act-on-metadata/impact-analysis)

The official workflow shows upstream/downstream selection, dependency depth, entity filters and CSV export. Its documented limitations include an export cap and possible UI/export differences involving cached ghost entities. The documentation and an embedded workflow screenshot were inspected; no DataHub tenant was accessed.

Apply to the contract workbench: distinguish the dependency-closed recheck set from consumers whose outputs actually changed. Keep a selected consumer’s path and checks next to its before/after result. Export scope must match the declared review scope; do not silently turn a visible subset into a different export population. Dependency reachability does not certify input truth.

## Nine further references, each tied to a task

| # | Reference and access | Observable or documented interaction | Application and boundary |
|---|---|---|---|
| 6 | [OpenMetadata column lineage](https://docs.open-metadata.org/v2.0.x/how-to-guides/data-lineage/column) · V | The current `latest` URL redirected to v2.0.x. A screenshot exposes columns within a selected table; docs describe column expansion and manual lineage editing. | Ontology and contracts: inspect the exact assertion or field, not merely an object-to-object edge. A recorded link needs origin and meaning. We did not execute lineage edits. |
| 7 | [PostHog breakdowns](https://posthog.com/docs/product-analytics/trends/breakdowns) · D | Docs describe adding a property/cohort breakdown, multiple series, numeric bins and an explicit control to load more than the initial 25 categorical values. | CRM/EHS: expose subgroup counts before aggregate interpretation. A breakdown does not itself standardize populations; CRM must retain the separate common-mix calculation. Make truncation visible. |
| 8 | [Hex input parameters](https://learn.hex.tech/docs/explore-data/cells/input-cells/input-cells-introduction) · D | Docs distinguish input label from variable name, connect inputs to downstream calculations and describe URL parameters for published apps. | SEM/finance/CRM: every control must identify what it changes and update all dependent outputs coherently. Pinning a scenario must freeze all its assumptions. We did not run a Hex app or verify its sharing behavior. |
| 9 | [PatternFly table demos](https://www.patternfly.org/components/table/react-demos/) · D, rendering limited | The page lists selection, filtering, responsive sorting, column management, pagination and distinct empty/loading/error examples. The current page identified release 6.7.0, but embedded table bodies did not render in this browser session. | CSV/contract ledgers: distinguish no matching rows from no data and failed loading. Use explicit pagination scope and accessible table structure. Do not claim its demo interactions were tested. |
| 10 | [Datasette Lite, public fixture](https://lite.datasette.io/?url=https://latest.datasette.io/fixtures.db) · L | Loaded a SQLite fixture in the browser, opened the 15-row `facetable` table, inspected suggested facets, filters, SQL and export entry points. The loader exposes stages rather than a blank screen. | CSV: show parsing/validation progress and preserve a route from summary to rows. The fixture was downloaded from a public URL; no private file was uploaded and no blanket network-privacy claim was tested. |
| 11 | [DuckDB Web Shell](https://shell.duckdb.org/) · L | Executed a grouped query on a two-year inline fixture; the typed result table returned rates 2.0 and 2.4. Import, Datasets and Share controls were visible but not exercised. | EHS/CSV: make the numerator, denominator and formula inspectable. Keep SQL as an optional reproducibility aid, not the operator’s required interface. Browser execution alone is not evidence that a site makes no network requests. |
| 12 | [OpenRefine facets](https://openrefine.org/docs/manual/facets) · D | Docs describe include/exclude facets, matching-versus-total row counts, combining facets and the effect of active facets on exports. They also name operations that ignore facets. | CSV/EHS: viewing filters and analytical exclusions require separate state and labels. An export must say whether it contains all accepted rows, the visible subset or the review scenario. No local OpenRefine session was launched. |
| 13 | [Foundry Workshop Object Table](https://www.palantir.com/docs/foundry/workshop/widgets-object-table) · D | Docs describe object selection, derived columns, selection-triggered events and inline writeback. These capabilities were read, not executed in Foundry. | Contract/operations lab: selected objects should drive a specific inspector or review action. Our local review has no writeback and must not imitate an operational approval that changes production systems. |
| 14 | [Metabase drill-through](https://www.metabase.com/docs/latest/questions/visualizations/drill-through) · V | Official screenshots show contextual drill-through menus. Docs describe opening underlying records or a new filtered question without modifying the original question. | EHS/AI: selecting a consequential aggregate should reveal the exact members contributing to it. Keep the original baseline visible and make the new scope explicit. No Metabase query was executed. |

These are 14 interface references across 14 products/design systems. The fifth-ranked reference is useful despite documentation-only access; ranking reflects task relevance, not the strength of our access.

## Access record and exclusions

Five public interfaces had an executed interaction: Carbon, Cloudscape, Grafana, Datasette and DuckDB. Documentation-only observations are labeled above. No product account, private tenant, sign-in, paid feature or externally submitted form was used.

An Observable Inputs notebook loaded its shell but did not expose usable inputs during the session; a guessed Framework documentation route returned 404. It is excluded from the 14 references. PatternFly’s documentation remained useful, but its missing embedded demos reduce our evidence level. Initial Grafana and Datasette loads displayed startup states; longer waits yielded functional interfaces. This is an access limitation, not a product performance benchmark.

The review workspace retains URL/status logs, text captures, scripts and screenshots under `/workspace/release-artifacts/design-research-current/`. Useful evidence files include `carbon-flow.json`, `carbon-selected.png`, `cloudscape-focused.json`, `cloudscape-comparison.png`, `grafana-finalflow.json`, `grafana-inspect-data.png`, `datasette-finalflow.json`, `datasette-table.png`, `duckdb-flow.json`, `duckdb-query.png`, `langsmith-diff.png` and `access-log.json`. Earlier project screenshots are under `/workspace/release-artifacts/deep-research/`. These local artifacts are review evidence, not assets bundled into the public site. Reference imagery remains owned by its respective publisher; this spec links to it rather than republishing it.

## Project critique at the initial review

This table records the review baseline. The CSV, AI and finance/CRM changes requested here have since been implemented; the implementation record below supersedes those specific outstanding requests.

| Project | What now supports a real task | Remaining interaction weakness or constraint |
|---|---|---|
| EHS investigation | Exact filing evidence, denominator decomposition and multiple sensitivity checks support a consequential challenge to an aggregate trend. | Preserve a visible baseline and the selected exclusion rule while moving between decomposition and evidence. Never label the exclusion result “corrected.” The conclusion is sensitivity to reported exposure. |
| Local CSV audit | Actual local input, strict parsing, per-record influence and joint exclusion scenarios are a usable analytical tool. | The result sits far above a 25-row selection table. Add an in-context scenario strip so a selection’s joint consequence is visible where the user acts. Existing excluded-only filtering should remain. |
| AI evidence audit | The 63-question ledger and exact scoring contract allow users to inspect why ranking or metadata matters. | Separate tabs make Own/Bare differences a memory exercise. Add an optional paired response view with aligned scorer gates. Keep single-response reading available on narrow screens. |
| SEM workbench | Null and alternative results sit together; discrete conditions, Monte Carlo uncertainty and the separate Fisher benchmark are explicit. | Preserve the current condition in long-page navigation. Do not add arbitrary continuous sliders between unrun conditions. Label sign-order error separately from failure to reject equality. |
| Ontology translation audit | Source → SKOS → sidecar makes a missing assertion concrete; exact triples and a scoped round-trip proof are inspectable. | This three-stage comparison is more useful than a decorative global graph. Add direct links to selected factor/framework state if it becomes a review handoff; never imply recovered assertions are validated mappings. |
| CRM decision model | Two constructed cases isolate mix reversal and unresolved outcomes; bounds and equality semantics are explicit. | While editing counts/mix, keep the current conclusion visible. A comparison across changed cohort counts cannot be attributed solely to the mix slider. Avoid presenting finite-cohort bounds as sampling confidence intervals. |
| Finance decision model | Dated cash flows, recurring commercial costs, feasibility, a constructed comparator and break-even analysis answer an actual policy question. | The calculation is separated from editable inputs by substantial vertical distance. Add a compact result summary and freeze a custom scenario for comparison; disclose changes to shared business context. Constructed alternatives must remain distinguishable from user-pinned policies. |
| Contract change review | Real JSON import/editing, typed bindings, before/after consumer evaluation, dependency paths and a local approval gate are substantive. | Preserve explicit pending/evaluated/blocked states. The selected consumer’s shortest path is an explanation, not the complete set of upstream causes. Do not equate a successful recheck with an unchanged value or semantic truth. |

The current local contract workbench was also exercised: the constructed cohort-mismatch change produced two critical failures and disabled local approval. This verifies that example’s UI gate, not the correctness of arbitrary user contracts.

## Three genuinely different workflow directions

### A. Evidence investigation: claim → exceptions → source → review

Choose for EHS, local CSV and the AI evidence ledger. The main entity is an evidence record. The question is “Which records or scoring conditions support this result?” Users narrow a collection and inspect a selected member without losing their scope.

```text
Claim + evidence class + scope + source snapshot
Baseline result  |  current review result  |  what changed
-------------------------------------------------------
Filter/counts   | ranked evidence ledger | selected record
               | selected IDs           | source + checks
               |                        | exact contribution
-------------------------------------------------------
Review selection / joint effect / reset / export scope
```

Workflow: load or select a pinned artifact → see numerator/denominator → inspect an influential filing or failed question → change one declared review condition → compare against the baseline → export the evidence and limitation. Selecting a chart segment filters the ledger; it must not silently modify analysis exclusions.

The AI variant uses paired evidence responses instead of the CSV exclusion checkbox. EHS’s explanatory narrative can precede this workbench, but a direct “inspect evidence” route should bypass the introduction for returning reviewers.

### B. Paired decision laboratory: assumptions → two outcomes → reversal boundary

Choose for finance, CRM and SEM. The main entity is a complete scenario or experimental condition. The question is “What changes the decision when the assumptions change?” It requires a visible comparison, not merely another set of cards.

```text
Context and evidence class       [choose case] [reset]
------------------------------------------------------
Editable assumptions | Current       | Pinned/reference
explicit units       | result        | result
                     | feasibility   | feasibility
                     | basis         | frozen basis
------------------------------------------------------
Changed assumptions + aligned comparison + boundary
Export both full scenarios and calculation version
```

Workflow: start from a named constructed case or completed SEM condition → inspect its full assumptions → pin a baseline where appropriate → edit one assumption → see both outcomes and all changed inputs → inspect a break-even threshold or measured design map → export.

SEM remains a lookup into completed experiments, not a browser simulation or power calculator for an actual workplace. Its reference is an experimental method/condition, not a user-invented estimate. Finance can compute arbitrary valid scenarios; its pinned comparator must preserve revenue, costs, horizon, rate and constraints as well as policy days. CRM must say when cohort composition or censoring changed, rather than attributing every difference to standardization.

### C. Contract review: proposed change → affected consumers → gate

Choose for the data-contract workbench and ontology translation audit. The main entity is a transformation between two representations. The question is “What information or validity is lost, and which consumer requires a review?”

```text
Baseline snapshot → proposal/export       evaluation state
---------------------------------------------------------
Changed fields | consumer before/after | selected basis
and contracts  | recheck / changed /   | dependency path
               | invalid / unaffected | exact assertions
---------------------------------------------------------
Blocking checks | scoped guarantee | local review + bundle
```

Workflow: load two snapshots or select a source assertion → display exact changes → compute affected consumers or lost information → inspect a path/assertion → repair or document the limitation → export a reproducible bundle. Ontology uses three representations (source, projection, sidecar recovery), not an operational approval gate. A full graph is secondary: a path plus a table is often sufficient to explain this task.

## Buildable specification

### State and data contract

Use a single state model per workbench: `source`, `scope`, `selection`, `scenario`, `evaluation`, `review`. Selection for inspection, filters for visibility and records excluded from a scenario must be different fields. A derived result must retain the complete input state that produced it.

| State | Required visible behavior |
|---|---|
| No source | Explain accepted format and provide a clearly labeled constructed example. Do not show invented success metrics. |
| Loading/parsing | Name the stage. Disable dependent actions. Keep input identity visible where available. |
| Evaluated | Show scope, evidence class, units and source identity alongside results. |
| Edited but unevaluated | Clear or visibly invalidate prior results and local approval. Disable result export until reevaluated. |
| Invalid input | Identify the field/row or contract failure. Missing is not zero; invalid is not a failed outcome with a valid denominator. |
| Valid but empty | Explain whether filters, screens or exclusions removed all usable records. No-exposure rate is undefined. |
| Filtered | Show matching/total counts. Preserve selection deliberately and expose selected-but-hidden records. |
| Pinned comparison | Freeze complete inputs and provenance, label the snapshot, show changed assumptions and offer replace/clear. Never recompute the pinned result using only some current inputs. |
| Artifact failure | Hide derived numbers and disable dependent controls; static hero values must not masquerade as loaded findings. |

For local files, keep processing and review state in memory; reload clears them. Exported files may contain supplied identifiers and values. A source digest identifies bytes or canonical content according to an explicitly named hashing scope; it does not certify provenance or correctness. Do not place private records or entire imported JSON in shareable URLs.

### Three implementation priorities

1. **CSV consequence at the point of selection.** Add a compact strip above the ledger showing `N excluded`, screened trend, joint review trend, and absolute rate difference where a percentage is undefined. Include “Review selected” and reset. Keep the individual leave-one-out column labeled as removal from the baseline; joint removal is a separate calculation. On desktop the strip may stick within the ledger area. On mobile it must wrap and leave the first checkbox/record column identifiable. Acceptance: select rows on page 2, filter to selected, reset, and verify both count and joint result without returning to the page top.
2. **AI paired response inspection.** Provide a compare control for two supported response modes on the same question. Show response identity, exact supplied text and concept/numeric/forbidden gates side by side, with explicit metadata boundaries. A comparison must use the same scorer and selected question; the unrelated-number counterexample needs its actual excerpt ID. Acceptance: all three metadata-sensitive questions reveal the wrapped/bare difference without changing question or retaining a stale response; single view, paired view, deep link and export agree.
3. **Finance/CRM results while editing.** Add a compact result region adjacent to, or persistently visible with, assumption inputs. Finance may pin the complete current custom scenario; compare it with later edits and list changed context as well as policy fields. Reset restores the named starting case and clears the pin. Keep the existing constructed-alternative comparison separately labeled. Acceptance: pin → change revenue, rate and policy → pinned inputs/result remain identical; export contains both full scenarios; clear/reset removes the pin. CRM should use the same visibility principle, and add pinning only when its cohort/mix comparison can be explained unambiguously.

### Implementation record · 2026-11-16

All three priorities now have working implementations. This records engineering acceptance checks, not measured usability improvement.

| Priority | Implemented behavior | Verification and remaining boundary |
|---|---|---|
| CSV consequence at selection | A sticky review strip shows the excluded count and screened versus joint review trend. “Review selected” changes the viewing filter; reset clears exclusions, returns to all rows and resets pagination. The checkbox column remains identifiable during horizontal scrolling. | Independently exercised the constructed 25-row case: excluding the influential record changes +585.71% to −25.00%; selected-only view retains that record; reset restores the analytical baseline, full view and disabled selection action. The initially retained selected-only filter was fixed and the complete flow passed again. No page overflow at 1440, 390 or 320 px. This verifies state consistency, not that an exclusion is substantively justified. |
| AI paired inspection | A fifth Compare view aligns exact responses for own wrapped versus own bare, or BM25 versus own wrapped. Each side repeats question/source identity, outcome and the three scoring gates. Deep links and exports preserve both responses. | Independently exercised `cs-004`, `prd-006` and `psm-007`: identical excerpt bodies, wrapped pass versus bare failure, exact scored text in exported JSON, and ranking comparison restored after reload. This makes format sensitivity inspectable; it does not establish semantic correctness. |
| Finance/CRM while editing | Both tools retain a compact current conclusion beside editing. Finance can freeze, replace and clear a complete custom scenario, compare it with the edited scenario, and list changed business context, policy and constraints. The constructed comparator remains separate. CRM retains its finite-cohort conclusion without adding an ambiguous cross-cohort pin. | Finance tests cover immutable snapshots, policy-only versus context changes, invalid-input recovery, replacement, all six starting cases, reset and exact dual-scenario export. CRM checks cover both cases, ties, invalid inputs and reset. All 22 relevant model tests pass; desktop/mobile browser checks and WCAG scans found no reported violations. These checks do not substitute for reader comprehension tests. |

Review scripts and captured evidence are in `/workspace/release-artifacts/deep-research/`: `check_paired_interfaces.py`, `paired-interface-independent-check.json`, `check_pinned_finance.py`, `pin-browser-check.json` and `decision-accessibility-final.json`. The finance implementation is in `personal/labs/finance/decision.*` plus `decision-comparison.mjs`; CRM is in `personal/labs/crm/decision.*`. No personal homepage changes were part of this work.

The CSV owner subsequently added saved-review restoration with exact source-byte hash matching and recomputed results. Its separate model review reports rejection of 14 invalid cases and checks BOM/CRLF source-byte preservation; these are owner/model-review results, distinct from the independent interaction checks above. Restoration does not make a source digest a certificate of data truth.

A subsequent finance evidence audit adds a separate empirical workflow at `personal/labs/finance/filings.html`: select an original annual filing and account scope → inspect component differences → inspect raw signed facts and exact periods → review scope evidence → export a pinned evidence bundle. Its Microsoft and Costco cases use public reports, while the policy laboratory remains explicitly hypothetical. Independent annual-table checks reproduce all 30 selected facts and 10 account-year bridges. Costco's $2m net residual must be read alongside $108m of absolute component differences and the conditional rounding bound; aggregate agreement is not component agreement.

The later CRM investigation at `personal/labs/crm/campaign.html` adds real UCI Bank Marketing records while retaining the constructed cohort tool separately. Its protocol was frozen before evaluation: inspect a chronological holdout → compare fixed models with/without post-call duration → inspect the same row → export evidence. Independent verification reproduces all 13,216 scores, metrics and 1,000 paired block-sensitivity comparisons. This quantifies a timing hazard already documented by the dataset, not a new leakage discovery. The interface discloses the 5.24% training versus 24.02% holdout subscription rate, assumed profile/history timing, absent client IDs and lack of causal allocation evidence.

This empirical audit is now the project hub's primary CRM destination, **“Would you know this before the call?”** / **“Inspect the campaign evidence.”** The constructed cohort model and original conversion workspace remain separate secondary links. Its implemented flow provides aligned average precision/Brier/log-loss results, retrospective top-decile counts, fixed-bin calibration, a source-row browser ordered by score difference or source position, an explicitly revealed outcome, and a review export containing both scores, the frozen protocol and artifact hash. Primary users are revenue-operations analysts and ML reviewers checking information timing. The ranked later batch is not an online contact policy; no interface action contacts a customer or estimates incremental campaign value.

### Layout and interaction details

At a 1440 px desktop viewport, use approximately 1200–1360 px of content width. Evidence investigation can allocate roughly 35–45% to the ledger and the remainder to the inspector; contract review can use a 260–320 px change rail. These are initial build constraints, not evidence of an optimal layout. Maintain a readable 60–80 character line length for source prose rather than expanding it across the entire workbench.

Use 36–44 px table rows for scanning on desktop, expanding as needed for wrapped explanations. Interactive controls need adequately spaced touch targets; never achieve density by making the checkbox the only tiny click target. Sticky summary regions must not obscure keyboard focus or table captions. At narrow widths, stack assumptions, outcome and inspector; preserve column relationships through labeled blocks or a deliberate horizontal table region. Avoid whole-page horizontal overflow.

Use semantic tables for comparisons, buttons for actions, links for navigation, and native labels for inputs. Selection, invalidity and uncertainty need text in addition to color. Announce concise result changes through a status region; do not reread an entire source excerpt after every toggle. Preserve focus after row selection and restore it when closing detail views. Keep long raw JSON/triples in disclosures with copy/export access.

Charts require units, scope and an accessible numeric basis. Shared scales support valid comparisons; uncertainty bars need their actual interpretation. Empty or missing values must not be drawn at zero. Prefer a selected dependency path to a dense, unexplained network. Do not add motion that makes a before/after comparison harder to inspect.

### Review artifacts and acceptance tasks

Every review export should include the artifact/model version, evidence class, source identity, selected scope, complete scenario inputs, result values before display rounding and relevant limitations. Paired comparisons include both scenarios. Keep viewing filters distinct from analytical exclusions in the export. Research data and local user files have different privacy and provenance boundaries.

| Task to verify | Success criterion |
|---|---|
| EHS: challenge the aggregate trend | Reviewer can identify the exact influential filings, their exposure share and the changed trend, then explain why this is sensitivity rather than corrected truth. |
| CSV: inspect then exclude | Reviewer can distinguish a row’s individual baseline influence from the joint exclusion result, inspect remaining counts and export the actual scenario. |
| AI: explain a metadata-sensitive pass | Reviewer can point to changed supplied text and its scorer gate, without equating a lexical pass with semantic correctness. |
| SEM: test an inference claim | Reviewer can read null false positives and alternative rejection together, find the selected sample size/loading, and distinguish simulation, information benchmark and actual-data advice. |
| Ontology: explain an empty cell | Reviewer can distinguish explicit absence, unrecorded comparison and external coverage gap, then inspect what each export preserves. |
| CRM evidence: audit decision-time information | Reviewer can compare the same later rows under both feature sets, identify duration as post-call information, inspect calibration and the base-rate shift, and explain why ranking gain is not a causal allocation benefit. |
| CRM cohort tool: challenge a raw conversion winner | Reviewer can find subgroup denominators, common mix and unresolved-outcome bounds, and identify when the finite-cohort conclusion is a tie or indeterminate. |
| Finance: compare policies | Reviewer can explain why more cash release can coexist with lower modeled value, compare a frozen scenario, and name the assumptions that changed. |
| Contract: reject an invalid proposal | Reviewer can follow a changed binding to an invalid consumer, see approval blocked, repair the proposal and observe that editing clears prior approval. |

These tasks should be tested with real readers before claiming usability gains. Record completion, wrong interpretations and recovery from mistakes; do not substitute a screenshot or an accessibility scan for comprehension testing. Existing mathematical, source-reconciliation and browser checks remain necessary because a usable presentation can still make an incorrect analytical claim.

## Product brief and prototype handoff

The users and jobs below are **design assumptions**, not interview findings. The shared job is to turn a disputed summary into a reproducible review. Success means a reader can identify the relevant evidence, distinguish it from assumptions, and explain what remains undecided.

| Product | Assumed primary user | Job to be done |
|---|---|---|
| EHS investigation / local CSV | Safety analyst reviewing an annual comparison | Identify influential exposure records and explain the sensitivity before interpreting safety performance. |
| AI evidence audit | Retrieval/evaluation engineer | Separate available-answer limitations from retrieval misses and inspect scorer-accepted counterexamples. |
| SEM workbench | Quantitative researcher planning an inference | Compare false positives and alternative rejection under completed conditions before trusting sample-size claims. |
| Ontology translation | Knowledge engineer exporting a crosswalk | Specify which assertions must survive and inspect an actual loss/recovery example. |
| CRM | Revenue-operations analyst / ML reviewer | Audit pre-call information timing on real records; separately test whether entered cohort outcomes identify a common-mix ranking. |
| Finance filings / policy lab | Finance analyst | Audit a selected statement comparison; separately compare supplied policy economics without treating them as estimated effects. |
| Data contracts | Analytics engineer reviewing a proposed change | Find affected consumers, inspect failed contracts and record a bounded local review. |

### Screen-by-screen journey

“Screen” means a distinct task state; these may be sections or panels on one route. Preserve the source and scope across transitions.

| Screen / products | Information needed | Primary action and next state | Adapted reference |
|---|---|---|---|
| 1. Start / all | Evidence class, intended question, available source or constructed case | Open a pinned investigation or load local input → scoped result | Datasette’s visible loading stages |
| 2. Scope / CSV, filings, SEM | Years/accounts, valid input counts or completed experimental condition | Apply explicit scope → baseline and available comparisons | Hex’s labeled inputs and downstream dependencies |
| 3. Exceptions / EHS, AI | Matching/total count, influence or scorer outcome, active filters | Select a record/question → exact basis; filter alone changes no scenario | Carbon’s explicit selection state |
| 4. Evidence / EHS, AI, filings, CRM timing | Source identity, periods, supplied text or paired record scores | Inspect raw basis, paired response or available information → supported interpretation | Grafana Inspect Data; LangSmith aligned examples |
| 5. Scenario / CRM, finance, CSV | Complete assumptions, current/reference result, changed inputs | Edit or exclude → recomputed result; pin only a complete scenario | Cloudscape’s collection-preserving comparison |
| 6. Transformation / ontology, contracts | Before/after assertions, failed checks and declared dependency paths | Inspect loss or affected consumer → scoped repair/review | OpenMetadata column detail; DataHub impact scope |
| 7. Judgment / all | Finding, limitation, unresolved verification and review note | Record a conclusion → export preview; local approval only for contracts | Foundry Object Table’s selection-driven actions, without writeback |
| 8. Handoff / all | Export contents, source/model version, complete selected basis | Download review; restore where implemented using the original source | OpenRefine’s explicit export/filter relationship |

### Three visual systems, not three skins

These are build specifications for future iterations; they do not assert that every current page uses these tokens. Reference evidence levels remain those recorded above. Check actual contrast and focus visibility after implementation.

**A — Evidence investigation, recommended primary direction.** Use a warm document surface `#F7F7F2`, white evidence panels, ink `#172824`, secondary text `#52635C`, teal actions `#136C50`, amber review flags `#795200` and red failures `#A12622`. Set Georgia titles at 48/52 px, system-sans body at 16/24, table text at 14/20 and monospace identifiers at 12/18. Use 8 px spacing increments, 24 px panel padding, a 32 px main gutter and 44 px table rows. Give the ledger about 40% of desktop width and the evidence inspector 60%; stack below 900 px. Charts use shared axes and direct labels, with exact values in the adjacent table. Adapt **Carbon** selection/count/reset, **Grafana** inspectable underlying data and **LangSmith** aligned same-question comparisons. Tradeoff: evidence takes more space than a summary dashboard; returning users need direct inspector links.

**B — Paired decision laboratory.** Use `#F3F6F8` canvas, white controls, `#162D3D` text, blue current scenario `#215B7B` and purple reference `#6B4C9A`; reserve amber for infeasibility rather than “worse.” Use system sans throughout: titles 36/42, body 16/24, tabular results 28/32 and labels 13/18. Use a 4 px spacing base, 24 px cards and a 16 px comparison gap. At desktop allocate 320 px to assumptions and two aligned result columns to current/reference; mobile repeats scenario labels in stacked blocks. Tables align units and decimal precision; sensitivity charts show the current point and conditional boundary, with no interpolation between unrun SEM conditions. Adapt **Cloudscape** retained comparison, **Hex** explicit parameter dependencies and **PostHog** visible subgroup breakdowns. Tradeoff: symmetry can imply comparability; changed context and distinct SEM estimands must remain prominent.

**C — Contract review.** Use white canvas, pale slate `#EEF2F6` change rail, `#182B3A` text, `#285E8E` inspection links, green `#166534` valid checks and red `#A12622` blocking checks. Use system-sans titles 30/36, body 15/23 and monospace code 13/20; do not render explanatory prose as code. Use 8 px spacing, 16 px cell padding, 40 px minimum rows and 280 px desktop change rail. The central before/after table leads to a 360 px inspector; collapse to ordered sections below 1000 px. Prefer a short dependency path to a global network; preserve full values in disclosures. Adapt **DataHub** direction/depth scope, **OpenMetadata** field-level inspection and **Foundry Object Table** selection-driven detail. Tradeoff: excellent for an engineering review, but unfamiliar users need plain-language check explanations and a constructed starter.

### AI placement and explicit trust states

The current AI project evaluates deterministic excerpt returns and lexical rules. It has no generated assistant, tool-calling agent or corrective AI action. The following compares **future assistant concepts**, not shipped capabilities or observed behavior in the references.

| Placement | Appropriate job | Benefit / principal risk | Recommendation |
|---|---|---|---|
| Inline beside a result | Explain one named calculation or check | Keeps evidence close; a short answer can hide necessary qualifications | Use for bounded explanations with a source link and “Inspect calculation.” |
| Sidebar attached to selection | Investigate one record, question or contract | Preserves work context; selection changes can silently stale the answer | Preferred future assistant placement for direction A, if selected scope is explicit and changes invalidate prior conclusions. |
| Dedicated workspace | Compare many sources or draft a review | Room for an evidence plan; separates the answer from the original task | Reserve for a future cross-source investigation requiring an explicit source set and return link. Do not replace the current benchmark ledger with chat. |

Every future response would show its scope—selected IDs, period and filters—plus source snapshot/retrieval date separately from generation time. During loading, show the actual stage and disable dependent actions. Partial text is labeled provisional; do not present a final conclusion or enable an action from an unfinished response. Insufficient evidence must name the missing input and offer source inspection, not invent an answer or imply a search found nothing unless that search completed.

Correction is an explicit “Report incorrect interpretation” action with editable note and source reference. It must not rewrite source data; any feedback retention or transmission requires a disclosed workflow. Proposed actions show exact changed fields, affected scope and a before/after preview, then require deliberate user application and fresh deterministic checks. A suggestion cannot mark a contract approved. If selection or source freshness changes, mark the response stale and require regeneration. These are requirements for a future implementation, not promises of model reliability.

### Prototype first, then test comprehension

Choose **A** as the portfolio’s primary investigation pattern; use B and C where the task requires a scenario or transformation. Prototype CSV Start → Exceptions → Review first, then AI paired evidence. These flows test the largest risk: confusing a viewing selection or sensitivity with a corrected truth.

The first CSV screen should say **“What holds your trend together?”**, show **“Local CSV”** and **“Constructed example”** as separate entry paths, label required fields `year`, `employees`, `hours`, `cases`, and offer **“Choose CSV”** and **“Try constructed case.”** After parsing, show **“Screened baseline”**, **“Review scenario”**, **“Records excluded”**, units and the active years. Keep **“Review selected”**, **“Reset exclusions”** and **“Export review”** unambiguous.

Illustrative end-to-end task, using the existing **constructed** fixture: an analyst loads the 25-row case. The screened change is +585.71%. They inspect `example-scale-review`, which passes the ratio screen, then exclude it only in a review scenario; the displayed change becomes −25.00%. “Review selected” shows that one row without altering the analytical scope. They write “Verify units and reporting scope; retain the original pending review,” export both basis and exclusions, then reset. This demonstrates sensitivity and state consistency; it is not a finding about an actual employer or a recommended deletion.

### Copy-ready build prompt

```text
Build the next iteration of the existing local CSV evidence workbench using
direction A in PROJECT_DESIGN_RESEARCH.md. Preserve the tested analytical model,
source-byte hashing, restoration checks and explicit sensitivity limitations.
Do not modify the personal homepage or add generated AI responses.

Use a 1280px maximum content width, 32px desktop gutters and 20px mobile gutters.
Apply the specified warm-paper, ink and teal tokens. Start with a plain task
heading, local-input privacy statement, required-column guide and separate
Choose CSV / Try constructed case buttons. Show parsing, invalid-file and
empty-result states; never display a success metric before valid data exists.

After loading, keep source name, selected years and screen bounds visible.
Show screened baseline and review scenario with cases, hours, rate and absolute
difference; mark undefined percentage changes explicitly. Put a ranked ledger
beside a selected-record inspector on desktop and stack them on mobile.
Keep a compact joint-consequence strip beside selection: excluded count,
baseline/review trend, Review selected and Reset exclusions. Viewing filters
must not alter the exclusion set. Distinguish baseline leave-one-out influence
from the combined scenario. Reset returns to all rows and the first page.

Provide accessible table headings, visible focus, text status labels and a
deliberate horizontal table region without page overflow. Keep current scope
and selected identifiers visible in the inspector. Export complete inputs,
source identity, model version, exclusions, results and the review note;
explain what is included before download. Retain the original file unchanged.

Verify the existing constructed reversal, multiple exclusions, filtered hidden
selections, reset, invalid input, zero exposure, zero baseline, export/restore
and source mismatch. Test keyboard flow and 320/390/1440px layouts. Ask a reader
to explain why the review result is not a corrected estimate; record mistakes
before claiming a usability gain. Reuse the current modules, not a parallel
unverified calculation path.
```
