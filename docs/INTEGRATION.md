# INTEGRATION.md

Wiring the research site (`grounded`) to the personal site (`priyatham9.github.io`)
so the two read as siblings without merging.

Fetched and inspected: `https://priyatham9.github.io/` on 2026-09-06, raw markup and inline
stylesheet, 63,165 bytes, single file, no external CSS. Everything quoted below is copied
from that document or from `repos/grounded/docs/index.html` as committed.

---

## 0. Preconditions. Read this before pasting anything.

Verified against the GitHub API and by HTTP request on 2026-09-06:

| Repository | Visibility | Pages enabled | `https://priyatham9.github.io/<repo>/` |
|---|---|---|---|
| `grounded` | private | no | 404 |
| `ehs-osha-analysis` | private | no | 404 |
| `ehs-ai-grounding-eval` | private | no | 404 |
| `ehs-human-factors-ontology` | private | no | 404 |
| `ehs-risk-sem` | private | no | 404 |
| `ehs-capitals-calculator` | private | no | 404 |
| `ehs-benchmarks` | public | yes | 200 |

Consequences that change what you should paste:

1. **Every research link in section 2 returns 404 today.** The section renders correctly,
   but the destinations do not exist yet. Enable Pages on each repo with source
   `main` branch, `/docs` folder, then re-run the checks in section 6.
2. **Publishing Pages from a private repository is a paid-plan feature on GitHub.**
   The API token available here does not expose the account plan, so confirm this on the
   account before planning around it. If the plan does not allow it, the choices are to
   make the repos public or to serve the research site from a different host.
3. **The GitHub repository links already on the research site also 404 for the public.**
   `docs/index.html` links `https://github.com/priyatham9/ehs-ai-grounding-eval` and five
   siblings from the `.p-links` divs. Those repos are private, so an external reader gets
   a 404, not a permission page. This is a pre-existing problem, not one this patch creates,
   but it becomes visible the moment anyone follows a link in from the personal site.
4. If you want the Research section live before the Pages sites are, use the interim
   variant in section 2.4, which uses the site's own `.report-row.ghost` class and renders
   the rows with no links at all rather than pointing at 404s.

---

## 1. What the personal site actually is

Single-file static page. No build step, no framework, no external stylesheet. One inline
`<style>` block, one inline `<script>` at the end of `<body>`.

### 1.1 CSS custom properties

Defined three times over, on bare `:root`, then under `@media (prefers-color-scheme: dark)`,
then again on `:root[data-theme="light"]` and `:root[data-theme="dark"]`. The token names
are identical to the research site's. Only the accent values differ.

```
--paper --surface --surface-2
--ink --ink-2 --muted
--rule --rule-soft
--accent --accent-2 --accent-ink --accent-wash
--grid-dot --shadow
--font-sans --font-mono --maxw
```

Personal site light accents: `--accent:#0F7A52`, `--accent-2:#0B5C3E`,
`--accent-ink:#FFFFFF`, `--accent-wash:#E3F0E9`.
Personal site dark accents: `--accent:#3FCB88`, `--accent-2:#2AA96C`,
`--accent-ink:#06130C`, `--accent-wash:#10241A`.

The research site uses `#1E40AF` / `#E2E8FB` light and its own dark pair. **The patch below
contains no colour values at all.** It references `--accent` only through existing classes,
so it inherits green on the personal site automatically and needs no dark-mode handling.
Adding a hex value to this patch is the single easiest way to make it look foreign.

The personal site also defines `--maxw: 1180px`, matching the research site, and
`section[id] { scroll-margin-top: 76px; }`, which means a new `id` anchor gets correct
scroll offset with no extra work.

### 1.2 Section ids, in document order

`#architecture`, `#focus`, `#work`, `#reports`, `#experience`, `#wins`, `#education`,
`#contact` (the last is on `<footer class="footer" id="contact">`, not a `<section>`).
There is one unnamed `<section class="hero">` and one unnamed `<section>` holding
`.metrics-grid`.

Six of these carry a numbered rail: `01` Focus, `02` Selected Work, `03` Reports,
`04` Experience, `05` Wins, `06` Education. Every one of them prints
`<span class="rail-of">/ 06</span>`. Adding a seventh numbered section means renumbering.
Section 2.2 gives the exact commands.

### 1.3 Nav markup, exactly as it stands

```html
    <nav class="topnav">
      <a href="#architecture">Architecture</a>
      <a href="#focus">Focus</a>
      <a href="#work">Work</a>
      <a href="#reports">Reports</a>
      <a href="#experience">Experience</a>
      <a href="#wins">Wins</a>
      <a href="#education">Education</a>
      <a href="#contact">Contact</a>
    </nav>
```

`.topnav` is a flat flex row, `gap: 2px`, links styled in IBM Plex Mono at `0.75rem`,
uppercase, `color: var(--muted)`, hover fills with `var(--accent)`. There is **no
scroll-spy and no active-state class** in the page's JavaScript, so adding a nav item is
purely a markup change. `@media (max-width: 900px) { .topnav { display: none; } }` hides
the whole nav on narrow screens, so the new item follows the same rule as every existing
one and needs no responsive work.

### 1.4 The three content components available for reuse

**Focus cards.** `.cards` is a 2-column grid with a single outer `2px` border; children are
`.card` with `.card-ic` (icon box), `<h3>`, `<p>`, and `.chips` / `.chip`. It relies on
`:nth-child(2n)` and `:nth-last-child(-n+2)` to suppress inner borders, so it only looks
right with an even child count.

**Project cards.** `.projects` is a 2-column grid with `gap: 16px`; children are
`<article class="project">` containing `.project-idx` (absolutely positioned code, top
right), `.project-kicker` (accent-outlined label), `<h3>`, `<p>`, `.chips` / `.chip`, and
optionally `<a class="project-live">` with a `.live-dot` and `<span class="arw">`.
Hover translates the card and drops a `6px 6px 0 var(--accent)` hard shadow.

**Report rows.** `.reports` is a bordered container; each child is
`<a class="report-row">`, a 3-column grid `auto 1fr auto` holding, in this order:

```
.report-code   column 1, mono, accent
.report-t      column 2, 1rem, weight 800
.report-st     column 3, bordered accent chip, nowrap, self-centred
.report-d      grid-column: 2 / 4, muted description
.report-open   grid-column: 1 / -1, accent, with a .arw arrow that slides on hover
```

There is also `.report-row.ghost` (`opacity: .55`, status chip demoted to
`var(--rule-soft)` / `var(--muted)`), already defined in the stylesheet and currently
unused. It exists for exactly the case in section 2.4.

`.report-row` hover fills the row with `var(--accent-wash)` and turns `.report-t` accent.
The existing `#reports` section links `RPT-005` with `href="/ehs-benchmarks/"`, a
root-relative path. That is the precedent this patch follows: the research sites live on
the same `priyatham9.github.io` origin, so root-relative paths are correct and survive a
custom-domain change.

**Chosen component: report rows.** The research portfolio is a list of named artifacts with
a code, a status, and a description, which is what `.report-row` was built for. It also
avoids `.cards`' even-count constraint, and it lets the `ehs-benchmarks` supersession note
sit inline. Using it means the patch introduces **no new CSS at all**.

### 1.5 Reveal and animation hooks

`.reveal` starts at `opacity: 0` and gets `.in` added by an `IntersectionObserver` that runs
over `document.querySelectorAll(".reveal")` at load. The new markup carries `.reveal` on the
same two children every other section uses, and is picked up with no JavaScript change.

---

## 2. The Research section, ready to paste

### 2.1 Where it goes

Insert between the end of `#reports` and the start of `#experience`. In the live file that
is here, at the boundary marked below. These are the exact surrounding lines:

```html
    </div>
  </div>
</section>
                       <-- INSERT THE NEW SECTION HERE, with a blank line either side
<section class="section" id="experience">
  <div class="wrap section-grid">
    <div class="section-rail reveal">
      <div class="rail-head"><span class="rail-num">04</span><span class="rail-of">/ 06</span><span class="rail-rule"></span></div>
      <h2 class="display">Experience</h2>
```

The `</section>` above is the close of `<section class="section" id="reports">`. It is the
last `</section>` before the `id="experience"` opening tag, and that pair is unique in the
file.

Placing Research at `04` puts it next to Reports, which is where a reader who just looked at
five interactive reports expects to find the papers. The cost is renumbering three rails.
If you would rather not renumber, the alternative is to append it after `#education` as
`07`, which needs only the `/ 06` to `/ 07` change in 2.2 and no `rail-num` edits, at the
cost of burying it below Education.

### 2.2 Renumber first, then insert

Run these inside the `priyatham9.github.io` working copy, **before** pasting, in this exact
order. macOS `sed` needs the empty `-i ''` argument.

```bash
sed -i '' 's|<span class="rail-num">06</span>|<span class="rail-num">07</span>|' index.html
sed -i '' 's|<span class="rail-num">05</span>|<span class="rail-num">06</span>|' index.html
sed -i '' 's|<span class="rail-num">04</span>|<span class="rail-num">05</span>|' index.html
sed -i '' 's|<span class="rail-of">/ 06</span>|<span class="rail-of">/ 07</span>|g' index.html
```

Highest number first, so no replacement is applied twice. Each of the first three matches
exactly one line: Education, Wins, Experience in that order. The fourth is global and hits
all six. After it, `grep -c 'rail-of">/ 07' index.html` must print `6`; it becomes `7` once
the block below is inserted.

### 2.3 The section, live-link version

Paste verbatim. No colour values, no new classes, no inline styles.

```html
<section class="section" id="research">
  <div class="wrap section-grid">
    <div class="section-rail reveal">
      <div class="rail-head"><span class="rail-num">04</span><span class="rail-of">/ 07</span><span class="rail-rule"></span></div>
      <h2 class="display">Research</h2>
      <p class="rail-note">A separate programme site. Grounded reasoning for safety-critical AI, six repositories, draft stage.</p>
    </div>
    <div class="reports reveal">

      <a class="report-row" href="/grounded/">
        <span class="report-code">RES-000</span>
        <span class="report-t">Grounded Reasoning for Safety-Critical AI</span>
        <span class="report-st">Hub</span>
        <span class="report-d">The programme site. An ontology-based architecture whose conclusions carry derivation traces, an open benchmark for measuring whether an answer is bound to an authoritative source, and the data-quality work underneath both. Findings, the paper in progress, and its stated limits.</span>
        <span class="report-open">Open the research site <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-osha-analysis/">
        <span class="report-code">RES-001</span>
        <span class="report-t">OSHA Injury-Rate Data Quality</span>
        <span class="report-st">Empirical</span>
        <span class="report-d">2,801,064 real OSHA establishment filings, CY2016 to CY2024. 2.07% of filings fail an hours-per-employee plausibility screen, and those filings carry 96.68% of all reported hours. Aggregate TRIR moves from 0.134 unscreened to 3.983 screened. The pooled ratio of 29.7x is not a portable constant: by year it runs from 1.39x in 2018 to 249x in 2019.</span>
        <span class="report-open">Open project <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-ai-grounding-eval/">
        <span class="report-code">RES-002</span>
        <span class="report-t">Grounding Evaluation for Safety-Critical QA</span>
        <span class="report-st">Benchmark</span>
        <span class="report-d">A 68-item benchmark for whether an AI answer to a safety-critical technical question is bound to an authoritative source or generated from parametric memory, scored so that abstention beats confabulation. Apparatus and question corpus only. No baseline results have been run yet.</span>
        <span class="report-open">Open project <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-human-factors-ontology/">
        <span class="report-code">RES-003</span>
        <span class="report-t">Human Factors Ontology</span>
        <span class="report-st">Ontology</span>
        <span class="report-d">Contextual human-error risk factors as machine-readable OWL, with an explicit crosswalk to established Performance Shaping Factor frameworks, and a forward-chaining engine that emits a derivation trace for every conclusion. The factor levels are analyst-assigned, not empirically estimated.</span>
        <span class="report-open">Open project <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-risk-sem/">
        <span class="report-code">RES-004</span>
        <span class="report-t">Structural Equation Modelling for Safety Risk</span>
        <span class="report-st">Simulation</span>
        <span class="report-d">How many observations it takes to recover coefficients, what rare-event outcomes do to calibration, and why hand-set path weights cannot be read causally. Every dataset here is synthetic by design and none of it is a finding about the world.</span>
        <span class="report-open">Open project <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-capitals-calculator/">
        <span class="report-code">RES-005</span>
        <span class="report-t">EHS Capitals Calculator</span>
        <span class="report-st">Tool</span>
        <span class="report-d">Human-capital-inclusive cost-benefit analysis for EHS investment, comparing a traditional accounting against one that counts lost work time, retraining, and productivity loss. Sensitivity analysis and a Monte Carlo mode that treats the inputs as distributions. All arithmetic runs in the browser.</span>
        <span class="report-open">Open the calculator <span class="arw">&rarr;</span></span>
      </a>

      <a class="report-row" href="/ehs-benchmarks/">
        <span class="report-code">RES-006</span>
        <span class="report-t">EHS Benchmarks Library</span>
        <span class="report-st">Published</span>
        <span class="report-d">Listed above as RPT-005, and part of the programme. A tested TypeScript library for TRIR, DART, LTIR and severity rate, with percentile tables built from a narrower panel of filings. Where its figures differ from RES-001, RES-001 is current and supersedes them.</span>
        <span class="report-open">Open report <span class="arw">&rarr;</span></span>
      </a>

    </div>
  </div>
</section>
```

Every figure above traces to a committed artifact in `ehs-osha-analysis` and is one of the
verified programme figures. Nothing here is rounded, restated, or newly derived.

### 2.4 Interim version, for use before Pages is enabled

Same section, but the six not-yet-live rows are plain `<div>` elements carrying the
stylesheet's existing `ghost` class. No anchors, so nothing 404s and nothing looks
clickable. Swap each row back to the `<a class="report-row" href="...">` form from 2.3 as
each site goes live. `RES-006` stays a live link throughout, because `ehs-benchmarks` is
already public and returns 200.

```html
      <div class="report-row ghost">
        <span class="report-code">RES-000</span>
        <span class="report-t">Grounded Reasoning for Safety-Critical AI</span>
        <span class="report-st">Not yet public</span>
        <span class="report-d">The programme site. An ontology-based architecture whose conclusions carry derivation traces, an open benchmark for measuring whether an answer is bound to an authoritative source, and the data-quality work underneath both.</span>
      </div>
```

Note the `.report-open` span is dropped from ghost rows. Leaving it in would print an
"Open" affordance on something that opens nothing.

### 2.5 One companion edit worth making

Adding RES-001 puts `2,801,064 filings / 2.07% / 96.68% / 29.7x` a few hundred pixels below
the existing RPT-005 row, which states `1.18 million filings / 1.53% / 87% / 7.6x`. Both
are real, and the second is the earlier narrower panel, but a reader sees two different
answers to the same question on one page. RES-006 above carries the supersession note,
which is the minimum fix. The cleaner fix is to also amend the RPT-005 description in
`#reports` so the disclosure sits at both ends. Replacement text for that
`<span class="report-d">`:

```html
        <span class="report-d">Not synthetic. 1.18&nbsp;million public OSHA establishment filings and 688,367 OIICS-coded injury cases: a percentile calculator against 3,842 real peer groups, search across 228,584 employers resolved by EIN, and the finding that a small fraction of records holds most of the reported hours. Built on a narrower panel than RES-001 below, which supersedes its headline figures.</span>
```

Separately, and unrelated to this patch: the existing `#reports` markup contains em dashes,
both as the literal character in the report titles and as the named HTML entity in the rail
note and the RPT-005 description. The research portfolio's house rule replaces those with a
spaced hyphen. Applying that to the personal site is your call; the replacement text above
already follows it.

---

## 3. The nav item

Existing markup, unchanged, with the one added line marked. `.topnav` needs no CSS change:
it is a flex row with `gap: 2px` that grows.

```html
    <nav class="topnav">
      <a href="#architecture">Architecture</a>
      <a href="#focus">Focus</a>
      <a href="#work">Work</a>
      <a href="#reports">Reports</a>
      <a href="#research">Research</a>          <!-- ADD THIS LINE -->
      <a href="#experience">Experience</a>
      <a href="#wins">Wins</a>
      <a href="#education">Education</a>
      <a href="#contact">Contact</a>
    </nav>
```

Nine items at `0.75rem` mono with `7px 11px` padding still fit inside `--maxw: 1180px`
alongside `.brand` and the theme `.toggle`, and the whole nav is `display: none` below
900px anyway. Check the 900px to 1180px band during verification; that is where a ninth
item would first crowd.

An alternative worth considering: a link straight out to the research site in the nav,
`<a href="/grounded/">Research</a>` rather than the in-page anchor. It sends people
to the real site in one click, but it breaks the pattern that every other nav item is an
in-page anchor, and it skips the framing the section provides. The in-page anchor is the
recommendation.

---

## 4. The reverse direction

### 4.1 What already links back

Exactly one link, in `repos/grounded/docs/index.html`, in the footer:

```html
    <div class="footer-links">
      <a href="https://priyatham9.github.io">Personal site</a>
      <a href="https://github.com/priyatham9">GitHub</a>
      <a href="https://linkedin.com/in/priyatham9">LinkedIn</a>
    </div>
```

The hub also links out to `https://priyatham9.github.io/ehs-benchmarks` from the
`ehs-benchmarks` project card's `.p-links` div. That is the whole of it.

### 4.2 What is missing

The five generated per-repo sites link back to nothing. Their footers come from the template
in `tools/build_sites.py` and contain only Repository, GitHub, and LinkedIn. A reader who
lands on `ehs-osha-analysis` from a search result or a shared link has no path to the hub
that frames it, and no path to the personal site. Given that the hub's own status section
says these repositories are one bundled programme, that is the wrong first impression.

`ehs-capitals-calculator/docs/index.html` is not generated by `build_sites.py`. It has a
different head, no `robots` meta, and a different footer, so it needs a hand edit rather
than a regeneration.

### 4.3 Reciprocal links worth adding

Listed in descending order of value. All are outside the file this document owns, so they
are proposals, not applied changes.

1. **Hub link in every generated per-repo footer.** One line in the footer template in
   `tools/build_sites.py`, ahead of the Repository link, then regenerate all five sites:

   ```html
         <a href="https://priyatham9.github.io/grounded/">Research hub</a>
   ```

   Add `Personal site` on the same line if you want full symmetry with the hub footer.

2. **Site links on the hub's project cards.** Each card currently has only a Repository
   link. Once Pages is on, add a sibling link inside the existing `.p-links` div, using the
   same root-relative form the personal site already uses for `/ehs-benchmarks/`:

   ```html
         <div class="p-links"><a href="https://github.com/priyatham9/ehs-osha-analysis">Repository</a><a href="/ehs-osha-analysis/">Site</a></div>
   ```

   Note that root-relative works because the hub is served from the same origin. It will
   need revisiting if the research site ever moves to its own domain.

3. **A `Personal site` entry in the hub's `.topnav`**, mirroring the `Research` entry being
   added to the personal site's nav. Currently the return path exists only in the footer, so
   it is invisible until a reader scrolls the whole page.

   ```html
       <nav class="topnav">
         <a href="#findings">Findings</a>
         <a href="#work">Work</a>
         <a href="#paper">Paper</a>
         <a href="#status">Status</a>
         <a href="https://priyatham9.github.io">Personal site</a>
       </nav>
   ```

4. **The same footer treatment for `ehs-capitals-calculator`**, applied by hand.

5. Leave the two brand marks and accents as they are. The shared skin plus the different
   accent is what makes them read as siblings rather than as one site with a colour bug. Do
   not add the cobalt accent to the personal site, and do not add green to the research
   site.

---

## 5. Canonical URLs, and the noindex question

### 5.1 Current state, verified

| Page | robots meta | canonical | Indexable |
|---|---|---|---|
| `priyatham9.github.io/` | `noindex, nofollow` | none | no |
| research hub `docs/index.html` | `noindex, nofollow` | none | no |
| four generated repo sites | `noindex, nofollow` | none | no |
| `ehs-capitals-calculator/docs` | **none** | none | yes, once Pages is on |
| `priyatham9.github.io/ehs-benchmarks/` | **none** | none | **yes, and live now** |
| `priyatham9.github.io/robots.txt` | 404, no file | n/a | n/a |

No page in either site carries a `rel="canonical"`. The personal site sets
`og:url` to `https://priyatham9.github.io/`, which is an Open Graph hint for social cards
and is not read as a canonical signal by search engines.

Two of those rows are almost certainly unintentional. `ehs-capitals-calculator` is the only
research page with no `robots` tag, which looks like a template divergence rather than a
decision. And `ehs-benchmarks` is public, live, indexable today, and carries the older
narrower-panel figures that the hub itself describes as superseded. Whatever you decide
below, those two should become deliberate rather than accidental.

### 5.2 The conflict, stated plainly

`noindex` keeps a page out of search results. `nofollow` additionally tells crawlers not to
follow the page's outbound links or pass any signal through them, which means that once the
Research section is added, the links to the research site will themselves be nofollowed. The
two sites are currently private in the practical sense: reachable only by someone who
already has the URL.

That is a real benefit. The manuscript is a draft. The benchmark has apparatus and a
question corpus and no baseline results. The internal adversarial review found that four of
five reviewers would reject the current manuscript, principally for bundling separable
contributions and for presenting a benchmark with no baselines. Indexing that now means the
draft is what gets found, quoted, and screenshotted, by people who will not read the status
caveats sitting three sections below.

It is also the direct opposite of the point. A research portfolio exists to be found, read,
linked, and cited. Independent citations, invitations to review, media mentions, and
speaking invitations all begin with someone locating the work without being handed the URL.
A page that returns nothing in a search cannot accumulate any of that, and a body of
evidence that depends on external recognition cannot be built from links you send yourself.
Two years of `noindex` is two years of no external record.

These goals are in direct conflict and cannot both be fully satisfied. What can be traded is
scope and timing.

### 5.3 The options

**Option A. Keep `noindex, nofollow` everywhere.** Share by direct link only. Costs
discoverability entirely, for as long as it stands. Nothing accrues in the meantime, and
lifting it later means starting the clock from zero on indexing, backlinks, and any external
record. Add the missing `robots` tag to `ehs-capitals-calculator` and decide explicitly what
to do about `ehs-benchmarks`, which is currently indexable.

**Option B. Lift it on the hub only.** Remove `noindex, nofollow` from
`grounded/docs/index.html`, add
`<link rel="canonical" href="https://priyatham9.github.io/grounded/" />` to its head,
and leave the per-repo sites and the personal site as they are. One citable, stable entry
point exists; the draft detail underneath stays out of the index. The hub's own status
section already states the limits honestly, so the page that gets found is also the page
that discloses. The cost is that the hub's outbound links to per-repo sites lead to
noindexed pages, which is fine for readers and slightly odd for crawlers.

**Option C. Publish the whole programme.** Remove `noindex` everywhere, add a self-referential
`rel="canonical"` to every page, add a `robots.txt` at the origin, and treat the current
figures and caveats as the public record. Maximum discoverability, and the version of the
work that exists today becomes the version the world has. If you take this one, the
supersession note in section 2.5 stops being tidiness and becomes necessary, because the
older `ehs-benchmarks` figures and the current ones would both be indexed and both citable.

A fourth axis, orthogonal to all three: the personal site's own `noindex, nofollow` is a
separate decision from the research site's. You can publish the research programme and keep
the personal site private, or the reverse. They are different documents with different
audiences, and nothing requires them to match.

**Not deciding is itself Option A**, running by default for as long as it takes to decide.

### 5.4 Canonical mechanics, whichever way you go

- Canonicalise on the trailing-slash form, `https://priyatham9.github.io/grounded/`.
  GitHub Pages serves both with and without the slash; picking one and stating it prevents
  the pair being treated as two URLs.
- Each page's canonical should point at itself, not at the hub. Pointing a per-repo site at
  the hub tells search engines the per-repo page is a duplicate, which is wrong and would
  suppress it.
- Internal links between pages on the same origin should stay root-relative
  (`/ehs-osha-analysis/`), matching the existing `/ehs-benchmarks/` link. Absolute URLs are
  only needed in the canonical tag itself and in cross-origin links.
- If the research site ever moves to its own domain, the canonical tags and every
  root-relative link in section 4.3 need revisiting together. That is an argument for
  deciding the domain question before, not after.

---

## 6. Verification checklist

Run after applying sections 2 and 3 to the `priyatham9.github.io` working copy.

**Markup and numbering**

- [ ] `grep -c 'rail-of">/ 07' index.html` prints `7`. No occurrence of `/ 06` remains.
- [ ] Rail numbers read `01` through `07` in document order, with no gaps or repeats:
      `grep -o 'rail-num">[0-9][0-9]' index.html`
- [ ] `grep -c 'id="research"' index.html` prints `1`.
- [ ] The nav has nine `<a>` children and `#research` sits between `#reports` and
      `#experience`.
- [ ] The page has one `<section class="section" id="research">` and its `</section>`
      closes before `<section class="section" id="experience">`. Confirm by opening the file
      in a browser and checking the Elements panel shows them as siblings, not nested.

**House rules**

- [ ] No em dash anywhere in the added block, neither the literal character nor the named
      HTML entity for it. Check with
      `grep -n $'\u2014' index.html` and `grep -in 'mdash' index.html`; neither should return
      a line from the pasted block.
- [ ] No hex colour, no `style=` attribute, and no new class name in the added block.
      `grep -n '1E40AF\|7C9EFF\|#[0-9A-Fa-f]\{6\}' ` over the pasted lines returns nothing.
- [ ] Every figure in the Research section matches the programme's verified set exactly:
      `2,801,064`, `2.07%`, `96.68%`, `0.134`, `3.983`, `29.7x`, `1.39x`, `249x`, `68`.
      No rounding, no restatement.
- [ ] The benchmark is described as having no baseline results. The ontology's factor levels
      are described as analyst-assigned. The SEM work is described as synthetic.

**Rendering**

- [ ] Light theme: the Research section's `.report-code`, `.report-st` border, and
      `.report-open` are green `#0F7A52`, identical to the Reports section directly above.
      Nothing cobalt appears.
- [ ] Dark theme, via the `#themeToggle` button: the same elements are `#3FCB88`. Toggle
      both directions and reload to confirm the `pc-theme` localStorage value persists.
- [ ] System dark with no stored preference: colours still correct, since the personal site
      defines its dark tokens in both the media query and the `[data-theme]` block.
- [ ] Row hover fills with `--accent-wash` and the `&rarr;` in `.report-open` slides right.
- [ ] The section fades in on scroll. If it stays invisible, the `.reveal` class is missing
      from `.section-rail` or from the `.reports` wrapper.

**Responsive**

- [ ] No horizontal body scroll at 320px, 375px, 768px, 900px, 940px, 1180px, and 1440px.
      940px and 900px are the two breakpoints in play: `.section-grid` collapses to one
      column at 940px, `.topnav` disappears at 900px.
- [ ] In the 900px to 1180px band the nine-item nav sits on one line without wrapping into
      the brand or the theme toggle.
- [ ] Long `.report-t` values do not overflow their column at 320px.

**Links**

- [ ] Clicking `Research` in the nav scrolls to the section with the heading clear of the
      sticky topbar. `section[id] { scroll-margin-top: 76px; }` handles this; if the heading
      is hidden behind the bar, the `id` is on the wrong element.
- [ ] Every `href` in the section resolves. Run against the deployed site, not locally:

      ```bash
      for p in grounded ehs-osha-analysis ehs-ai-grounding-eval \
               ehs-human-factors-ontology ehs-risk-sem ehs-capitals-calculator \
               ehs-benchmarks; do
        printf '%-30s %s\n' "$p" \
          "$(curl -s -o /dev/null -w '%{http_code}' https://priyatham9.github.io/$p/)"
      done
      ```

      All seven must return 200. Any 404 means Pages is not enabled on that repo, and that
      row should revert to the ghost form in section 2.4 until it is.
- [ ] From the research hub, the footer `Personal site` link returns to
      `https://priyatham9.github.io/` and the new Research section is visible from there.
      The round trip should work in both directions with no dead end.
- [ ] If any reciprocal link from section 4.3 was added, its destination returns 200 too.

**Consistency**

- [ ] RPT-005 and RES-001 do not present conflicting OSHA figures without the supersession
      note from section 2.5 appearing on at least one of them.
- [ ] The `robots` meta on the personal site is whatever section 5 decided, deliberately,
      and the same decision has been applied to `ehs-capitals-calculator` and
      `ehs-benchmarks`, which are the two current outliers.
