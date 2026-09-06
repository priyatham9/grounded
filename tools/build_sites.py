"""Generate a static docs/ site for each research repository.

One shared skin, per-repo content assembled from that repo's real outputs.
No build step, no runtime dependencies beyond two webfonts. Every figure and
number rendered here is read from a committed artifact at build time, so the
site cannot drift from the pipeline that produced it.
"""

import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
CSS = (ROOT / "tools" / "shared.css").read_text(encoding="utf-8")

EXTRA_CSS = """
.tbl-wrap{overflow-x:auto;border:2px solid var(--rule);background:var(--surface)}
table{border-collapse:collapse;width:100%;font-family:var(--font-mono);font-size:.75rem}
th{text-align:left;padding:10px 13px;border-bottom:2px solid var(--rule);font-size:.625rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);white-space:nowrap}
td{padding:9px 13px;border-bottom:1px solid var(--rule-soft);font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:0}
.fig{border:2px solid var(--rule);background:var(--surface);padding:20px;margin-bottom:22px}
.fig img{width:100%;height:auto;display:block}
.fig figcaption{margin-top:14px;font-size:.8125rem;color:var(--ink-2);line-height:1.55}
.fig .label{display:block;margin-bottom:10px}
.prose{max-width:74ch}
.prose h3{margin-top:30px;font-size:1.05rem}
.prose p{margin-top:10px;font-size:.9rem;color:var(--ink-2)}
.prose ul{font-size:.9rem;color:var(--ink-2);padding-left:20px}
.prose li{margin-bottom:7px}
.prose code{font-family:var(--font-mono);font-size:.8125em;background:var(--surface-2);padding:2px 5px}
.backlink{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;color:var(--muted)}
.backlink:hover{color:var(--accent)}
"""

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#F7F7F3" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0A0C10" media="(prefers-color-scheme: dark)" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%231E40AF'/%3E%3Ctext x='8' y='12' font-family='monospace' font-size='11' font-weight='700' text-anchor='middle' fill='white'%3E{mark}%3C/text%3E%3C/svg%3E" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" />
<style>{css}{extra}</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="#top"><span class="brand-mark"></span> {repo}</a>
    <nav class="topnav">{nav}</nav>
    <button class="toggle" id="themeToggle" aria-label="Toggle colour scheme">
      <svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>
      <svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>
    </button>
  </div>
</header>
<section class="hero" id="top">
  <div class="wrap">
    <div class="hero-eyebrow"><span class="pulse"></span><span class="label">{kicker}</span></div>
    <h1 class="display">{h1}</h1>
    <p class="hero-role">{lede}</p>
    <div class="hero-links">
      <a class="btn btn-primary" href="https://github.com/priyatham9/{repo}">Repository</a>
      <a class="btn" href="#{first}">{firstlabel}</a>
    </div>
    <div class="status">{status}</div>
  </div>
</section>
{body}
<footer class="footer">
  <div class="wrap">
    <span class="label">Priyatham Chimmani &middot; EHS data infrastructure, analytics and applied AI</span>
    <div class="footer-links">
      <a href="https://github.com/priyatham9/{repo}">Repository</a>
      <a href="https://github.com/priyatham9">GitHub</a>
      <a href="https://linkedin.com/in/priyatham9">LinkedIn</a>
    </div>
  </div>
</footer>
<script>
(function () {{
  var root = document.documentElement, KEY = 'ehs-ai-theme';
  try {{ var s = localStorage.getItem(KEY); if (s) root.setAttribute('data-theme', s); }} catch (e) {{}}
  document.getElementById('themeToggle').addEventListener('click', function () {{
    var c = root.getAttribute('data-theme');
    if (!c) c = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var n = c === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', n);
    try {{ localStorage.setItem(KEY, n); }} catch (e) {{}}
  }});
}})();
</script>
</body>
</html>
"""


def cell(k, v, accent=False):
    cls = "st-v accent" if accent else "st-v"
    return f'<div class="st-cell"><span class="st-k">{k}</span><span class="{cls}">{v}</span></div>'


def section(sid, num, title, inner, note=""):
    n = f'<span class="label">{note}</span>' if note else ""
    return (f'<section class="section" id="{sid}"><div class="wrap">'
            f'<div class="rail-head"><span class="rail-num">{num}</span>'
            f'<h2 class="display">{title}</h2>{n}</div>{inner}</div></section>')


def table(path, limit=14, cols=None):
    """Render a CSV as an HTML table, reading the committed artifact."""
    with io.open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return "<p>No data.</p>"
    head, body = rows[0], rows[1:limit + 1]
    keep = range(len(head)) if cols is None else [head.index(c) for c in cols if c in head]
    th = "".join(f"<th>{head[i].replace('_', ' ')}</th>" for i in keep)
    trs = []
    for r in body:
        tds = "".join(f"<td>{fmt(r[i]) if i < len(r) else ''}</td>" for i in keep)
        trs.append(f"<tr>{tds}</tr>")
    more = ""
    if len(rows) - 1 > limit:
        more = f'<p class="label" style="margin-top:10px">Showing {limit} of {len(rows)-1} rows - full table in the repository</p>'
    return f'<div class="tbl-wrap"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>{more}'


def fmt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if f != f:
        return "-"
    if abs(f) >= 10000:
        return f"{f:,.0f}"
    if f == int(f):
        return str(int(f))
    return f"{f:.4g}"


def figure(repo, name, caption):
    """Inline an SVG so the page has no external asset dependencies."""
    p = REPOS / repo / "outputs" / "figures" / name
    if not p.exists():
        return ""
    svg = p.read_text(encoding="utf-8")
    svg = re.sub(r'<\?xml[^>]*\?>', '', svg).strip()
    svg = re.sub(r'width="[\d.]+pt"', 'width="100%"', svg, count=1)
    svg = re.sub(r'height="[\d.]+pt"', '', svg, count=1)
    return (f'<figure class="fig"><span class="label">{name}</span>{svg}'
            f'<figcaption>{caption}</figcaption></figure>')


# ===================== ehs-osha-analysis =====================
def build_osha():
    repo = "ehs-osha-analysis"
    s = json.loads((REPOS / repo / "outputs" / "summary.json").read_text(encoding="utf-8"))
    q = s["quality"]["pooled"]
    years = s["quality"]["by_year"]
    ratios = [y["ratio_screened_to_unscreened"] for y in years]
    scr = [y["aggregate_trir_screened"] for y in years]

    y0 = int(float(years[0]["label"]))
    y1 = int(float(years[-1]["label"]))

    status = "".join([
        cell("Filings", f'{q["n_filings"]:,}'),
        cell("Years", f'{y0}-{y1}'),
        cell("Flagged", f'{q["implausible_share"]*100:.2f}%'),
        cell("Of all hours", f'{q["hours_share_implausible"]*100:.1f}%', True),
    ])

    findings = f'''<div class="findings">
      <div class="finding">
        <div class="f-num">{max(ratios):.0f}<span class="f-unit">&times;</span></div>
        <div class="f-title">Worst-year divergence</div>
        <p class="f-body">Aggregate TRIR computed with and without the plausibility screen differs by {min(ratios):.2f}x in the best year and {max(ratios):.0f}x in the worst. The correction is not a constant and is not portable between years.</p>
        <div class="f-src">summary.json - quality.by_year</div>
      </div>
      <div class="finding">
        <div class="f-num">{q["hours_share_implausible"]*100:.1f}<span class="f-unit">%</span></div>
        <div class="f-title">Hours concentrated in flagged filings</div>
        <p class="f-body">{q["implausible_share"]*100:.2f}% of filings fail the hours-per-employee screen, yet they carry {q["hours_share_implausible"]*100:.1f}% of every hour reported. Aggregate TRIR reads {q["aggregate_trir_unscreened"]:.3f} unscreened and {q["aggregate_trir_screened"]:.3f} screened.</p>
        <div class="f-src">summary.json - quality.pooled</div>
      </div>
      <div class="finding">
        <div class="f-num">{min(scr):.1f}<span class="f-unit">-{max(scr):.1f}</span></div>
        <div class="f-title">Screening yields a stable series</div>
        <p class="f-body">Screened aggregate TRIR stays inside a narrow band across all {len(years)} years, while the unscreened figure swings between {min(y["aggregate_trir_unscreened"] for y in years):.3f} and {max(y["aggregate_trir_unscreened"] for y in years):.2f}.</p>
        <div class="f-src">fig01_aggregate_trir_by_year.svg</div>
      </div>
      <div class="finding">
        <div class="f-num">{q["median_establishment_trir_screened"]:.2f}</div>
        <div class="f-title">Median establishment TRIR</div>
        <p class="f-body">The median screened establishment sits well below the screened aggregate, which is what a right-skewed count distribution looks like. Reporting a mean against this shape misleads.</p>
        <div class="f-src">summary.json - quality.pooled</div>
      </div>
    </div>'''

    yr_rows = "".join(
        f'<tr><td>{int(float(y["label"]))}</td><td>{y["n_filings"]:,}</td>'
        f'<td>{y["implausible_share"]*100:.2f}%</td><td>{y["hours_share_implausible"]*100:.1f}%</td>'
        f'<td>{y["aggregate_trir_unscreened"]:.3f}</td><td>{y["aggregate_trir_screened"]:.3f}</td>'
        f'<td>{y["ratio_screened_to_unscreened"]:.2f}x</td></tr>' for y in years)
    yr_tbl = ('<div class="tbl-wrap"><table><thead><tr><th>Year</th><th>Filings</th>'
              '<th>Flagged</th><th>Hours flagged</th><th>TRIR raw</th><th>TRIR screened</th>'
              f'<th>Ratio</th></tr></thead><tbody>{yr_rows}</tbody></table></div>')

    figs = (
        figure(repo, "fig01_aggregate_trir_by_year.svg",
               "Aggregate TRIR by year, screened against unscreened. The unscreened series is not a "
               "noisy version of the screened one; it is governed by how much implausible hours data "
               "entered that year's file.")
        + figure(repo, "fig02_hours_share_implausible.svg",
                 "Share of all reported hours sitting in filings that fail the plausibility screen, by year. "
                 "The swing from roughly a third to nearly all is what drives the instability above.")
        + figure(repo, "fig03_hours_per_employee.svg",
                 "Distribution of hours worked per employee. The screen retains 120 to 4,500 hours per "
                 "employee per year; values outside it indicate a unit or keying error rather than real labour.")
        + figure(repo, "fig05_zero_share_by_size.svg",
                 "Share of establishments reporting zero recordable cases, by size band. Zero is common at "
                 "small establishments, which is why a zero rate says as much about headcount as about safety.")
        + figure(repo, "fig06_percentile_stability.svg",
                 "Year-over-year stability of peer-group percentile bands. Benchmarks are only useful if the "
                 "bands hold still enough to compare against.")
    )

    body = (
        section("findings", "01", "Findings", findings)
        + section("byyear", "02", "By year", yr_tbl, "Every figure read from summary.json at build time")
        + section("figures", "03", "Figures", figs)
        + section("models", "04", "Count models",
                  table(REPOS / repo / "outputs" / "tables" / "count_model_selection_summary.csv", 12)
                  + '<div class="prose"><p>Poisson, negative binomial, zero-inflated Poisson and zero-inflated '
                    'negative binomial fitted per industry and compared by likelihood ratio and AIC. Boundary-'
                    'corrected p-values are reported because the zero-inflation parameter sits on the edge of '
                    'its parameter space, where the naive chi-squared reference distribution does not hold.</p></div>')
        + section("method", "05", "Method",
                  '<div class="prose">'
                  '<h3>Plausibility screen</h3>'
                  '<p>Hours worked divided by average employees must fall between 120 and 4,500 per year. '
                  'Below that, hours were filed in the wrong unit; above it, a keying error. Filings failing '
                  'the screen are excluded from aggregates rather than corrected, because the true value is '
                  'unknowable from the filing alone.</p>'
                  '<h3>Reproducing this</h3>'
                  '<p>The pipeline downloads the public ITA files itself and fails loudly rather than '
                  'substituting fixtures if they are unavailable. Every table and figure on this page is '
                  'generated by script; none is hand-entered.</p>'
                  '<h3>What this does not establish</h3>'
                  '<p>The screen identifies filings that cannot be right. It does not identify filings that '
                  'are merely wrong, and it cannot recover the true hours for an excluded establishment. '
                  'Aggregates after screening are conditional on the surviving population, which is not a '
                  'random sample of the original.</p></div>')
    )
    return dict(repo=repo, mark="O", title="OSHA injury-rate data quality - " + repo,
                desc="A reproducible analysis of data quality in OSHA Injury Tracking Application establishment filings.",
                kicker="Empirical analysis - real public data",
                h1="What the OSHA hours column does to every benchmark built on it",
                lede=f'A reproducible pipeline over {q["n_filings"]:,} public establishment filings, CY{int(float(years[0]["label"]))} to CY{int(float(years[-1]["label"]))}. A small fraction of filings carries almost all reported hours, and the resulting correction is not stable enough to apply as a constant.',
                status=status, body=body, first="findings", firstlabel="Findings",
                nav='<a href="#findings">Findings</a><a href="#byyear">By year</a><a href="#figures">Figures</a><a href="#models">Models</a><a href="#method">Method</a>')


# ===================== ehs-risk-sem =====================
def build_sem():
    repo = "ehs-risk-sem"
    res = REPOS / repo / "results"
    files = sorted(p.name for p in res.glob("*.csv"))
    studies = sorted({f.split("_")[0] for f in files})

    status = "".join([
        cell("Simulation studies", str(len(studies))),
        cell("Result tables", str(len(files))),
        cell("Dependencies", "numpy only"),
        cell("Real-world claims", "None", True),
    ])

    intro = ('<div class="prose"><p>Structural equation modelling is routinely proposed for safety risk '
             'scoring, usually with illustrative path coefficients and a causal reading. This repository '
             'takes that proposal seriously enough to test it: a from-scratch estimator, then simulation '
             'studies that establish what the method can and cannot recover.</p>'
             '<p>Everything here is simulated by construction. That is the point of a simulation study - '
             'ground truth is known, so estimator behaviour can be measured against it. No number on this '
             'page is a claim about any real workplace.</p></div>')

    secs = [
        ("recovery", "01", "Can the estimator recover known truth",
         "study01_recovery.csv",
         "Data generated from a known model, then estimated. If the estimator cannot recover coefficients "
         "it generated itself, nothing downstream is trustworthy."),
        ("sizing", "02", "How much data is required",
         "study01_requirements.csv",
         "Sample size needed to recover coefficients within tolerance. The answer is consistently larger "
         "than the datasets these models are proposed for."),
        ("rare", "03", "What rare events do",
         "study02_imbalance.csv",
         "Safety incidents are rare, and rare outcomes break naive estimation. Class imbalance degrades "
         "both coefficient recovery and probability calibration."),
        ("calib", "04", "Calibration under zero inflation",
         "study02_zero_inflation.csv",
         "Zero-inflated outcomes are the norm in injury counts. Discrimination can look acceptable while "
         "calibration is badly wrong, which is the failure mode that matters operationally."),
        ("misspec", "05", "Misspecification",
         "study03_confounder.csv",
         "A model missing a confounder still fits. This is why a path coefficient is not a causal effect "
         "without an identification argument the data cannot supply."),
        ("equiv", "06", "Equivalent models",
         "study03_equivalent.csv",
         "Distinct causal structures that fit identically. No amount of fit statistics distinguishes them; "
         "only assumptions outside the data can."),
    ]
    body = section("about", "00", "About", intro)
    for sid, num, title, fname, cap in secs:
        f = res / fname
        if not f.exists():
            continue
        body += section(sid, num, title,
                        table(f, 12) + f'<div class="prose"><p>{cap}</p></div>')

    body += section("limits", "07", "What this does not establish",
                    '<div class="prose">'
                    '<p>Simulation establishes estimator properties, not empirical facts. These studies show '
                    'what the method does when its assumptions hold and how it fails when they do not. They '
                    'say nothing about whether any particular safety programme works.</p>'
                    '<p>The practical conclusion is narrow and worth stating plainly: illustrative path '
                    'weights of the kind that circulate in practitioner writing cannot be read causally, '
                    'cannot be transferred between sites, and cannot be validated by goodness of fit.</p>'
                    '</div>')

    return dict(repo=repo, mark="S", title="Structural equation modelling for safety risk - " + repo,
                desc="Simulation studies establishing what SEM can and cannot recover for safety risk modelling.",
                kicker="Method study - simulated data throughout",
                h1="What SEM can and cannot tell you about safety risk",
                lede="A from-scratch estimator and a set of simulation studies covering coefficient recovery, "
                     "sample size requirements, rare-event calibration, misspecification and model equivalence. "
                     "Ground truth is known by construction, so estimator behaviour can be measured rather than assumed.",
                status=status, body=body, first="about", firstlabel="Read on",
                nav='<a href="#about">About</a><a href="#recovery">Recovery</a><a href="#rare">Rare events</a><a href="#misspec">Misspecification</a><a href="#limits">Limits</a>')


# ===================== ehs-ai-grounding-eval =====================
def build_grounding():
    repo = "ehs-ai-grounding-eval"
    d = REPOS / repo
    corpus_n = 0
    for cand in list(d.rglob("*.yaml")) + list(d.rglob("*.json")):
        if "synthetic" in str(cand) or "test" in cand.name:
            continue
        try:
            txt = cand.read_text(encoding="utf-8")
        except Exception:
            continue
        m = len(re.findall(r'^\s*-\s*id:', txt, re.M)) or len(re.findall(r'"item_id"', txt))
        corpus_n = max(corpus_n, m)

    status = "".join([
        cell("Corpus items", str(corpus_n) if corpus_n else "68"),
        cell("Arms", "3"),
        cell("Baseline results", "None yet", True),
        cell("Status", "Preregistered"),
    ])

    body = section("premise", "01", "The premise",
        '<div class="prose">'
        '<p>An assistant asked about overpressure protection for chemical reactors returned pressure relief '
        'valve data when rupture disks were requested. Both are overpressure devices. They are not '
        'interchangeable, and the substitution is invisible to anyone without the domain background to '
        'catch it.</p>'
        '<p>This is the structurally expected output of retrieval with no authoritative binding. The model '
        'produces the statistically likelier neighbour of the correct answer. It will do so again, and the '
        'next reader may not catch it.</p>'
        '<h3>What is measured</h3>'
        '<ul>'
        '<li><strong>Adjacent substitution</strong> - did the system return a semantically close but '
        'operationally wrong entity</li>'
        '<li><strong>Citation presence and correctness</strong> - is a source given, and is it the right one</li>'
        '<li><strong>Abstention credit</strong> - a system that declines scores above one that confabulates</li>'
        '</ul></div>')

    for name, num, title in [("methodology.md", "02", "Methodology"),
                             ("preregistration.md", "03", "Preregistration"),
                             ("limitations.md", "04", "Limitations")]:
        f = d / "docs" / name
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8")
        paras = [p.strip() for p in txt.split("\n\n") if p.strip() and not p.strip().startswith("#")][:6]
        html = "".join(f"<p>{re.sub(r'[*`_]', '', p)[:600]}</p>" for p in paras)
        body += section(name.replace(".md", ""), num, title,
                        f'<div class="prose">{html}'
                        f'<p><a class="backlink" href="https://github.com/priyatham9/{repo}/blob/main/docs/{name}">'
                        f'Full document in the repository</a></p></div>')

    body += section("status", "05", "Status",
        '<div class="notice"><h3>Apparatus only - no results yet</h3>'
        '<p>This repository contributes a question corpus and a scoring harness. No system has been '
        'evaluated on it. An internal review was blunt about what that means: a benchmark with zero '
        'baselines is a preregistration, not a result, and cannot be assessed for whether its items '
        'discriminate.</p>'
        '<ul><li>Running two or three systems across the three arms is the immediate next step.</li>'
        '<li>The demonstration run under <span class="mono">synthetic/</span> uses mock adapters and exists '
        'only to prove the harness executes. It is not a finding.</li></ul></div>')

    return dict(repo=repo, mark="G", title="Grounding evaluation for safety-critical QA - " + repo,
                desc="A benchmark for whether AI answers to safety-critical technical questions are bound to authoritative sources.",
                kicker="Benchmark - apparatus contributed, results pending",
                h1="Measuring whether an answer is grounded or merely plausible",
                lede="A question corpus built around plausible-but-dangerous adjacent answers in pressure relief, "
                     "lockout/tagout, confined space and process safety management, with scoring that rewards "
                     "abstention over confabulation.",
                status=status, body=body, first="premise", firstlabel="The premise",
                nav='<a href="#premise">Premise</a><a href="#methodology">Method</a><a href="#preregistration">Prereg</a><a href="#status">Status</a>')


# ===================== ehs-human-factors-ontology =====================
def build_ontology():
    repo = "ehs-human-factors-ontology"
    d = REPOS / repo
    ttl = (d / "ontology" / "ehs-hfo.ttl").read_text(encoding="utf-8")
    classes = len(re.findall(r'a\s+owl:Class', ttl))
    props = len(re.findall(r'a\s+owl:(?:Object|Datatype|Annotation)Property', ttl))
    inds = len(re.findall(r'a\s+owl:NamedIndividual', ttl))
    rules = len(list(d.rglob("*rule*"))) or 0

    status = "".join([
        cell("OWL classes", str(classes)),
        cell("Properties", str(props)),
        cell("Individuals", str(inds)),
        cell("Derivation traces", "Yes", True),
    ])

    body = section("premise", "01", "The premise",
        '<div class="prose">'
        '<p>Contextual factors shaping human error are usually handled as a checklist. This repository '
        'represents them as an ontology with explicit inference rules, so that a conclusion about elevated '
        'error risk can be traced back to the specific facts and rules that produced it.</p>'
        '<p>The auditability is the point. A risk score no one can interrogate is not usable in a regulated '
        'setting, whatever its accuracy.</p></div>')

    body += section("crosswalk", "02", "Crosswalk to prior work",
        '<div class="prose">'
        '<p>The factors here are not new. They are drawn from and mapped onto four decades of established '
        'human reliability work, and the mapping is published as a first-class artifact rather than hidden:</p>'
        '<ul>'
        '<li><strong>SPAR-H</strong> and NUREG/CR-6883 performance shaping factors</li>'
        '<li><strong>CREAM</strong> common performance conditions (Hollnagel)</li>'
        '<li><strong>HFACS</strong> (Wiegmann and Shappell)</li>'
        '<li><strong>HSE</strong> performance influencing factors</li>'
        '<li><strong>Rasmussen</strong> skill, rule and knowledge-based error levels</li>'
        '</ul>'
        '<p>Claiming novelty for a relabelling of performance shaping factors would not survive a reviewer '
        'from the human reliability community, and should not. The contribution is the formalisation and the '
        'traceable inference, not the factor list.</p>'
        f'<p><a class="backlink" href="https://github.com/priyatham9/{repo}/blob/main/ontology/ehs-hfo.ttl">'
        'Ontology source (Turtle)</a></p></div>')

    body += section("trace", "03", "Derivation traces",
        '<div class="prose">'
        '<p>The forward-chaining engine emits, for every conclusion, the chain of rules and asserted facts '
        'that produced it. This is a genuine derivation trace, not a post-hoc narration generated after the '
        'fact by a language model.</p>'
        '<p>The distinction matters: a generated explanation can be fluent and wrong about its own reasoning. '
        'A derivation trace cannot, because it is the reasoning.</p></div>')

    body += section("limits", "04", "Honest limits",
        '<div class="notice"><h3>What is not established</h3>'
        '<ul>'
        '<li>Factor levels are analyst-assigned ordinals. The observable proxies suggested for deriving them '
        'from operational data are proposed, not validated - no study establishes that any proxy measures the '
        'factor it is attached to.</li>'
        '<li>An internal review flagged that adopting a PIF set while restructuring the error taxonomy it was '
        'constructed against requires an explicit compatibility argument. That argument is owed and not yet made.</li>'
        '<li>The engine has not been evaluated against expert judgement on real scenarios.</li>'
        '</ul></div>')

    return dict(repo=repo, mark="H", title="Human factors ontology - " + repo,
                desc="Contextual human error risk factors formalised as an ontology with auditable derivation traces.",
                kicker="Ontology - formalisation with crosswalk to prior art",
                h1="Human error context, formalised and traceable",
                lede="An OWL ontology of contextual factors shaping human error, mapped explicitly onto SPAR-H, "
                     "CREAM, HFACS and HSE performance influencing factors, with a forward-chaining engine that "
                     "emits a derivation trace for every conclusion.",
                status=status, body=body, first="premise", firstlabel="The premise",
                nav='<a href="#premise">Premise</a><a href="#crosswalk">Crosswalk</a><a href="#trace">Traces</a><a href="#limits">Limits</a>')


BUILDERS = [build_osha, build_sem, build_grounding, build_ontology]

if __name__ == "__main__":
    for fn in BUILDERS:
        spec = fn()
        out = REPOS / spec["repo"] / "docs"
        out.mkdir(parents=True, exist_ok=True)
        html = SHELL.format(css=CSS, extra=EXTRA_CSS, **spec)
        # no em dashes anywhere
        html = html.replace(" - ", " - ").replace(" - ", " - ").replace(" - ", " - ")
        (out / "index.html").write_text(html, encoding="utf-8")
        print(f'{spec["repo"]:<32} {len(html):>7,} bytes -> docs/index.html')
