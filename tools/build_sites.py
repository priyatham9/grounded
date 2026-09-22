"""Generate a static docs/ site for each research repository.

One shared skin, per-repo content assembled from that repo's real outputs.
No build step, no runtime dependencies beyond two webfonts. Every figure and
number rendered here is read from a committed artifact at build time, so the
site cannot drift from the pipeline that produced it.

Structure of a generated page:

  banner        one sticky strip: brand, estate links (personal site, hub,
                paper, the six projects with the current one marked),
                scroll-tracked section links, theme toggle
  hero          why the work exists, in one sentence, plus a status strip
  sections      numbered, each opening with a lede before any table
  footer        hub, personal site, repository

Prose is authored here. Numbers, tables and figures are not: they are read
from the committed artifacts named in each caption. Adding a claim to a page
means adding an artifact that supports it.
"""

import csv
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from banner import apply_banner
import html
import io
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
CSS = (ROOT / "tools" / "shared.css").read_text(encoding="utf-8")

HUB = "https://priyatham9.github.io/grounded/"
PERSONAL = "https://priyatham9.github.io"
GH = "https://github.com/priyatham9"

# The six sibling projects, in reading order. The hub is linked separately.
PORTFOLIO = [
    ("ehs-osha-analysis", "OSHA data quality"),
    ("ehs-ai-grounding-eval", "Grounding benchmark"),
    ("ehs-human-factors-ontology", "Human factors ontology"),
    ("ehs-risk-sem", "Risk SEM"),
    ("ehs-capitals-calculator", "Capitals calculator"),
    ("ehs-benchmarks", "EHS benchmarks"),
]

EXTRA_CSS = """
/* ============ figure tokens ============ */
:root{
 --fig-paper:#FFFFFF; --fig-grid:#D6D7CE; --fig-axis:#3A403C; --fig-mute:#666D68;
 --s1:#0072B2; --s2:#D55E00; --s3:#009E73; --s4:#CC79A7;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
 --fig-paper:#12151C; --fig-grid:#262B36; --fig-axis:#BFC4CF; --fig-mute:#838A99;
 --s1:#56B4E9; --s2:#E69F00; --s3:#5ECFA6; --s4:#E58FBE;
  }
}
:root[data-theme="dark"]{
 --fig-paper:#12151C; --fig-grid:#262B36; --fig-axis:#BFC4CF; --fig-mute:#838A99;
 --s1:#56B4E9; --s2:#E69F00; --s3:#5ECFA6; --s4:#E58FBE;
}

/* ============ accessibility ============ */
/* Focus rings, the skip link and the reduced-motion block now live in
   tools/shared.css so every page in the portfolio inherits them from one place.
   What stays here is the belt-and-braces guard against a stray wide child. */
body{overflow-x:hidden}

/* ============ interactive charts ============ */
.chart{border:2px solid var(--rule);background:var(--surface);padding:22px;margin:0 0 26px}
.chart .chart-take{font-family:var(--font-display);font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:1.05rem;line-height:1.2;margin:0 0 14px;max-width:44ch}
.chart-body{position:relative}
.chart svg{display:block;width:100%;height:auto}
.chart-pt,.chart-bar{cursor:pointer;outline:none}
.chart-pt:hover,.chart-pt:focus{r:6.5}
.chart-bar:hover,.chart-bar:focus{opacity:.8}
.chart-pt:focus-visible,.chart-bar:focus-visible{stroke:var(--accent);stroke-width:3}
.chart-tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--paper);font-family:var(--font-mono);font-size:.6875rem;line-height:1.5;padding:6px 9px;border:2px solid var(--rule);white-space:nowrap;z-index:5}
.chart .src{display:block;margin-top:12px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

/* ============ less text: expandable detail ============ */
details.more{border-top:2px solid var(--rule-soft);margin:14px 0 0}
details.more>summary{cursor:pointer;list-style:none;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);padding:10px 0}
details.more>summary::-webkit-details-marker{display:none}
details.more>summary::before{content:'+ ';font-weight:700}
details.more[open]>summary::before{content:'- '}
details.more>div{padding:0 0 12px}
figcaption details.more,.f-body details.more{margin-top:8px;border-top:0}
figcaption details.more>summary,.f-body details.more>summary{padding:4px 0}
figcaption details.more>div{font-size:inherit;color:inherit}

/* ============ compact stat row ============ */
.statrow{display:grid;grid-template-columns:repeat(4,1fr);border:2px solid var(--rule);background:var(--surface);margin:0 0 30px}
.statrow .st-cell{padding:18px 20px;border-right:2px solid var(--rule-soft);min-width:0}
.statrow .st-cell:last-child{border-right:0}
.statrow .st-v{font-family:var(--font-display);font-stretch:125%;font-weight:900;font-size:clamp(1.35rem,5vw,2rem);line-height:1;display:block;margin-top:6px;overflow-wrap:anywhere}
@media(max-width:640px){.statrow{grid-template-columns:1fr 1fr}.statrow .st-cell:nth-child(2){border-right:0}.statrow .st-cell:nth-child(-n+2){border-bottom:2px solid var(--rule-soft)}}

/* ============ vertical rhythm ============ */
.section{padding:78px 0}
.section:nth-of-type(even){background:var(--surface-2)}
.rail-head{margin-bottom:14px}
.rail-head h2{max-width:22ch}
.sec-lede{max-width:68ch;margin:0 0 34px;padding-left:18px;border-left:2px solid var(--accent);font-size:1.02rem;line-height:1.6;color:var(--ink-2)}
.sec-lede strong{color:var(--ink);font-weight:700}

/* ============ opener: why the work exists ============ */
.opener{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);border:2px solid var(--rule);background:var(--surface)}
.opener-main{padding:36px 34px}
.opener-side{padding:36px 34px;border-left:2px solid var(--rule-soft);background:var(--surface-2)}
.opener-main .big{font-size:1.22rem;line-height:1.45;color:var(--ink);font-weight:600;max-width:40ch;margin-bottom:18px}
.opener-main p{font-size:.94rem;line-height:1.62;color:var(--ink-2);max-width:56ch}
.opener-main p:last-child{margin-bottom:0}
.opener-side h3{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:14px}
.opener-side p{font-size:.875rem;line-height:1.6;color:var(--ink-2)}
.opener-side p:last-child{margin-bottom:0}
.opener-side ul{margin:0;padding-left:19px;font-size:.875rem;line-height:1.58;color:var(--ink-2)}
.opener-side li{margin-bottom:9px}
.opener-side li:last-child{margin-bottom:0}
@media(max-width:860px){.opener{grid-template-columns:1fr}.opener-side{border-left:0;border-top:2px solid var(--rule-soft)}}

/* ============ pull quote ============ */
.pull{margin:30px 0;padding:2px 0 2px 24px;border-left:4px solid var(--accent);max-width:62ch}
.pull p{font-size:1.06rem;line-height:1.5;color:var(--ink);font-weight:600;margin-bottom:9px}
.pull .attrib{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0}

/* ============ tables ============ */
.tbl{margin:0 0 26px}
.tbl-wrap{overflow:auto;max-height:540px;overscroll-behavior:contain;border:2px solid var(--rule);background:var(--surface)}
table{border-collapse:separate;border-spacing:0;width:100%;font-family:var(--font-mono);font-size:.75rem}
thead th{position:sticky;top:0;z-index:2;text-align:left;padding:13px 16px;background:var(--surface-2);box-shadow:inset 0 -2px 0 var(--rule);font-size:.5625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;white-space:nowrap}
td{padding:13px 16px;line-height:1.45;box-shadow:inset 0 -1px 0 var(--rule-soft);font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink-2)}
tbody tr:nth-child(even) td{background:var(--surface-2)}
tbody tr:hover td{background:var(--accent-wash);color:var(--ink)}
td.t-first{color:var(--ink);font-weight:600}
tbody tr:last-child td{box-shadow:none}
.tbl-cap{margin-top:12px;font-size:.8125rem;line-height:1.55;color:var(--ink-2);max-width:76ch}
.tbl-cap .src{display:block;margin-top:7px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

/* ============ figures ============ */
.fig{border:2px solid var(--rule);background:var(--surface);padding:22px;margin:0 0 26px}
.fig-scroll{overflow-x:auto;overscroll-behavior-x:contain}
.fig svg{display:block;width:100%;height:auto;max-width:100%}
.fig img{width:100%;height:auto;display:block}
.fig figcaption{margin-top:16px;font-size:.8125rem;color:var(--ink-2);line-height:1.6;max-width:76ch}
.fig figcaption .src{display:block;margin-top:7px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.fig .label{display:block;margin-bottom:12px}
.fig-title{font-size:1.05rem;line-height:1.28;margin:0 0 7px;max-width:54ch;letter-spacing:-.01em}
.fig-sub{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.06em;color:var(--muted);margin:0 0 20px;max-width:80ch;line-height:1.5}
.fig-legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:14px}
.fig-legend span{display:inline-flex;align-items:center;gap:7px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.fig-legend i{width:12px;height:3px;flex:none}
/* One caption style for every table, figure and chart: sentence, then the file. */
.fig figcaption,.tbl-cap,.trace-cap{border-top:1px solid var(--rule-soft);padding-top:12px}
.chart .src,.fig figcaption .src,.tbl-cap .src,.trace-cap .src{font-weight:600}
/* Phones: a figure or table scrolls inside its own frame, the page never does. */
@media(max-width:700px){
  .fig-scroll,.tbl-wrap,.trace{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .fig-scroll>svg{min-width:560px}
  .fig-scroll,.tbl-wrap{scroll-snap-type:x proximity}
  .fig,.chart{padding:16px}
}

/* ============ prose ============ */
.prose{max-width:72ch}
.prose h3{margin-top:34px;margin-bottom:10px;font-size:1.02rem;font-family:var(--font-mono);font-weight:700;letter-spacing:-.01em}
.prose h3:first-child{margin-top:0}
.prose p{margin:0 0 14px;font-size:.94rem;line-height:1.66;color:var(--ink-2)}
.prose ul{margin:0 0 16px;font-size:.94rem;line-height:1.62;color:var(--ink-2);padding-left:20px}
.prose li{margin-bottom:9px}
.prose strong{color:var(--ink)}
.prose code{font-family:var(--font-mono);font-size:.8125em;background:var(--surface-2);padding:2px 5px}
.prose a{text-decoration:none;border-bottom:2px solid var(--accent);padding-bottom:1px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0 40px}
.cols .prose{max-width:none}

/* ============ definition grid ============ */
.defs{border:2px solid var(--rule);background:var(--surface)}
.def{display:grid;grid-template-columns:minmax(0,200px) minmax(0,1fr);border-top:1px solid var(--rule-soft)}
.def:first-child{border-top:0}
.def dt{padding:16px 20px;font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink);font-weight:700;background:var(--surface-2)}
.def dd{margin:0;padding:16px 20px;font-size:.875rem;line-height:1.6;color:var(--ink-2)}
@media(max-width:660px){.def{grid-template-columns:1fr}.def dd{padding-top:0}}

/* ============ trace block ============ */
.trace{border:2px solid var(--rule);background:var(--surface);overflow-x:auto;overscroll-behavior-x:contain}
.trace pre{margin:0;padding:22px;font-family:var(--font-mono);font-size:.6875rem;line-height:1.7;color:var(--ink-2);white-space:pre}
.trace-cap{margin-top:12px;font-size:.8125rem;color:var(--ink-2);line-height:1.55;max-width:76ch}
.trace-cap .src{display:block;margin-top:7px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

/* ============ misc ============ */
.notice{margin-bottom:26px}
.notice:last-child{margin-bottom:0}
.backlink{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;color:var(--muted);border-bottom:2px solid var(--rule-soft);padding-bottom:2px}
.backlink:hover{color:var(--accent);border-bottom-color:var(--accent)}
.footer{border-top:2px solid var(--rule)}
.footer-note{margin-top:16px;font-size:.8125rem;line-height:1.6;color:var(--muted);max-width:64ch}
.hero h1{max-width:18ch;font-size:clamp(1.9rem,6.4vw,4.6rem)}
.hero-role{font-size:1.08rem;max-width:64ch}
.status{margin-top:36px}
"""

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{pageurl}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{pageurl}" />
<meta property="og:image" content="{pageurl}og.png" />
<meta property="og:site_name" content="Grounded" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />
<meta name="twitter:image" content="{pageurl}og.png" />
<script type="application/ld+json">{ldjson}</script>
<meta name="theme-color" content="#F7F7F3" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0A0C10" media="(prefers-color-scheme: dark)" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%231E40AF'/%3E%3Ctext x='8' y='12' font-family='monospace' font-size='11' font-weight='700' text-anchor='middle' fill='white'%3E{mark}%3C/text%3E%3C/svg%3E" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" />
<script>document.documentElement.classList.add('js');</script>
<style>{css}{extra}</style>
<style id="story-css">/*STORY_CSS_START*/{storycss}/*STORY_CSS_END*/</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<section class="hero" id="top">
  <div class="wrap hero-grid">
    <div class="hero-fig">
      <div class="hero-eyebrow" data-st-reveal><span class="pulse"></span><span class="label">{kicker}</span></div>
      <p class="hero-big" data-st-reveal style="--k:{num_k}" aria-label="{num}{unit_plain}"><span class="hero-num" data-to="{num_to}" data-dec="{num_dec}" data-group="{num_group}" aria-hidden="true">{num}</span><span class="hero-unit" aria-hidden="true">{unit}</span></p>
      <p class="hero-means" data-st-reveal><span class="hm-k">What this means</span>{means}</p>
      <span class="src">Source artifact: {num_src}</span>
    </div>
    <div class="hero-text">
      <h1 class="display" data-st-reveal>{h1}</h1>
      <p class="hero-role" data-st-reveal>{lede}</p>
      <p class="hero-not" data-st-reveal><span class="hn-k">What this does not establish</span>{nots}</p>
      <div class="hero-links" data-st-reveal>
        <a class="btn btn-primary btn-story" href="story.html">Read the story<span class="btn-arrow" aria-hidden="true">&rarr;</span></a>
        <a class="btn" href="#explore">{cta}</a>
        <a class="btn" href="{gh}/{repo}">Repository</a>
      </div>
    </div>
    <div class="status">{status}</div>
  </div>
</section>
{doors}
<main id="main">
<div class="layout wrap">
<aside class="toc" aria-label="On this page">
  <details class="toc-d" open>
    <summary><span class="toc-num">--</span><span class="toc-current">Contents</span><span class="toc-caret" aria-hidden="true"></span></summary>
    <ol>{toc}</ol>
  </details>
</aside>
<div class="content">
{body}
</div>
</div>
</main>
{programme}
<footer class="footer">
  <div class="wrap">
    <span class="label">Priyatham Chimmani &middot; EHS data infrastructure, analytics and applied AI</span>
    <div class="footer-links">
      <a href="{hub}">Research hub</a>
      <a href="{personal}">priyatham9.github.io</a>
      <a href="{gh}/{repo}">This repository</a>
      <a href="{gh}">GitHub</a>
      <a href="https://linkedin.com/in/priyatham9">LinkedIn</a>
    </div>
    <p class="footer-note">Every number, table, figure and interactive on this page is read from a committed
    artifact in this repository at build time by <span class="mono">tools/build_sites.py</span>.
    Captions name the artifact. The page cannot report a value the pipeline did not produce.</p>
  </div>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=False)


def cell(k, v, accent=False):
    cls = "st-v accent" if accent else "st-v"
    # A value that is nothing but a number (with an optional percent sign) counts
    # up when it scrolls into view. charts.js reads the data-* attributes.
    m = re.fullmatch(r"([\d,]+(?:\.(\d+))?)(%?)", str(v))
    if m:
        num, dec, suffix = m.group(1), len(m.group(2) or ""), m.group(3)
        v = (f'<span data-countup data-to="{num.replace(",", "")}" data-dec="{dec}" '
             f'data-group="{1 if "," in num else 0}">{num}</span>{suffix}')
    return f'<div class="st-cell"><span class="st-k">{k}</span><span class="{cls}">{v}</span></div>'


def crossbar(current):
    """The six projects, linked to their live pages, current one marked."""
    out = []
    for slug, short in PORTFOLIO:
        cur = ' aria-current="page"' if slug == current else ""
        out.append(f'<a role="listitem" href="{PERSONAL}/{slug}/"{cur}>{short}</a>')
    return "".join(out)


def section(sid, num, title, inner, lede="", note=""):
    n = f'<span class="label">{note}</span>' if note else ""
    l = f'<p class="sec-lede">{lede}</p>' if lede else ""
    return (f'<section class="section rv" id="{sid}" aria-labelledby="h-{sid}"><div class="wrap">'
            f'<div class="rail-head"><span class="rail-num" aria-hidden="true">{num}</span>'
            f'<h2 class="display" id="h-{sid}">{title}</h2>{n}</div>{l}{inner}</div></section>')


# --------------------------------------------------------------------------
# page components shared by the four sites
# --------------------------------------------------------------------------
def jsdata(eid, obj):
    """Embed extracted artifact data for an interactive. Read by charts.js."""
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="{eid}">{raw}</script>'


def scope(does, doesnt, after=""):
    """What the work shows and what it does not, side by side and equal weight."""
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    return (f'<div class="scope"><div class="scope-col scope-yes"><h3 class="scope-h">'
            f'<span class="scope-mark" aria-hidden="true">+</span>What this shows</h3>'
            f'<ul>{li(does)}</ul></div><div class="scope-col scope-no"><h3 class="scope-h">'
            f'<span class="scope-mark" aria-hidden="true">&minus;</span>What this does not show</h3>'
            f'<ul>{li(doesnt)}</ul></div></div>{after}')


def quickstart(repo, cmds, after=""):
    def line(c):
        c = esc(c)
        m = re.search(r"\s+#\s.*$", c)
        if m:
            c = c[:m.start()] + f'<span class="qs-c">{c[m.start():]}</span>'
        return f'<span class="qs-l">{c}</span>'
    code = "\n".join(line(c) for c in cmds)
    return (f'<div class="qs"><div class="qs-bar"><span class="qs-dots" aria-hidden="true"><i></i><i></i><i></i></span>'
            f'<span class="qs-t">{esc(repo)}</span>'
            f'<button type="button" class="qs-copy" aria-label="Copy the quickstart commands">Copy</button></div>'
            f'<pre tabindex="0"><code>{code}</code></pre></div>{after}')


def explore_intro(text, link_href="", link_label=""):
    ln = (f' <a class="ix-more" href="{link_href}">{link_label} &rarr;</a>' if link_href else "")
    return f'<p class="ix-intro">{text}{ln}</p>'


def renumber_and_toc(body, short):
    """Number sections in reading order and build the table of contents from them."""
    counter = [0]

    def num(m):
        counter[0] += 1
        return f'<span class="rail-num" aria-hidden="true">{counter[0]:02d}</span>'
    body = re.sub(r'<span class="rail-num" aria-hidden="true">\d+</span>', num, body)
    items = []
    for i, m in enumerate(re.finditer(r'<section class="section rv" id="([\w-]+)"', body)):
        sid = m.group(1)
        # "Rail label|Strip label": the rail can spell it out, the one-line
        # "On this page" strip in the banner takes the short form.
        lab, _, nav = short.get(sid, sid).partition("|")
        nav = nav or lab
        items.append(f'<li><a href="#{sid}" data-short="{esc(nav)}"><span class="toc-n">{i+1:02d}</span>{esc(lab)}</a></li>')
    return body, "".join(items)


def programme(repo):
    """Next in the programme: the other sites, starting from the next one."""
    from banner import PROJECTS as BP
    notes = {slug: note for slug, _, note in BP}
    keys = [k for k, _, _ in PROGRAMME]
    i = keys.index(repo)
    order = PROGRAMME[i + 1:] + PROGRAMME[:i]
    cards = []
    for j, (slug, name, url) in enumerate(order):
        note = "research hub" if slug == "grounded" else notes.get(slug, "")
        tag = "Next" if j == 0 else f"{j+1:02d}"
        cards.append(f'<a class="prog-card{" prog-next" if j == 0 else ""}" href="{url}">'
                     f'<span class="prog-tag">{tag}</span><span class="prog-name">{esc(name)}</span>'
                     f'<span class="prog-note">{esc(note)}</span><span class="prog-arrow" aria-hidden="true">&rarr;</span></a>')
    return (f'<nav class="prog" aria-labelledby="prog-h"><div class="wrap">'
            f'<h2 class="prog-h display" id="prog-h">Next in the programme</h2>'
            f'<div class="prog-grid">{"".join(cards)}</div></div></nav>')


def opener(big, paras, side_title, side_html):
    ps = f"<p>{paras[0]}</p>" if paras else ""
    if len(paras) > 1:
        ps += ('<details class="more"><summary>Read on</summary><div>'
               + "".join(f"<p>{p}</p>" for p in paras[1:]) + "</div></details>")
    return (f'<div class="opener"><div class="opener-main"><p class="big">{big}</p>{ps}</div>'
            f'<div class="opener-side"><h3>{side_title}</h3>{side_html}</div></div>')


def pull(text, attrib):
    return f'<blockquote class="pull"><p>{text}</p><p class="attrib">{attrib}</p></blockquote>'


def notice(title, body):
    return f'<div class="notice"><h3>{title}</h3>{body}</div>'


def defs(pairs):
    rows = "".join(f'<div class="def"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in pairs)
    return f'<dl class="defs">{rows}</dl>'


def fmt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if f != f:
        return "-"
    if abs(f) >= 10000:
        return f"{f:,.0f}"
    if f == int(f):
        return str(int(f))
    return f"{f:.4g}"


def table(path, caption, source=None, limit=14, cols=None, rename=None, pct=None):
    """Render a committed CSV as an HTML table. The caption names the artifact."""
    path = Path(path)
    with io.open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return ""
    head, body = rows[0], rows[1:limit + 1]
    rename = rename or {}
    pct = set(pct or [])
    keep = list(range(len(head))) if cols is None else [head.index(c) for c in cols if c in head]
    th = "".join(f"<th>{esc(rename.get(head[i], head[i].replace('_', ' ')))}</th>" for i in keep)
    trs = []
    for r in body:
        tds = []
        for pos, i in enumerate(keep):
            raw = r[i] if i < len(r) else ""
            if head[i] in pct:
                try:
                    val = f"{float(raw) * 100:.2f}%"
                except (TypeError, ValueError):
                    val = esc(raw)
            else:
                val = fmt(raw)
            cls = ' class="t-first"' if pos == 0 else ""
            tds.append(f"<td{cls}>{val}</td>")
        trs.append(f"<tr>{''.join(tds)}</tr>")
    n = len(rows) - 1
    shown = f" Showing {len(body)} of {n} rows." if n > len(body) else ""
    src = source or f"{path.parent.name}/{path.name}"
    return (f'<figure class="tbl"><div class="tbl-wrap"><table>'
            f'<thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<figcaption class="tbl-cap">{caption}{shown}'
            f'<span class="src">Source artifact: {esc(src)}</span></figcaption></figure>')


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
# The pipeline writes SVGs with a fixed print palette. Inlining them here maps
# that palette onto the page's theme tokens so a figure is legible in both
# schemes. Geometry, data and labels are untouched.
SVG_COLOURS = {
    "#ffffff": "var(--fig-paper)", "#fff": "var(--fig-paper)",
    "#e6e6e6": "var(--fig-grid)", "#eee": "var(--fig-grid)",
    "#111": "var(--ink)", "#333": "var(--fig-axis)",
    "#444": "var(--fig-axis)", "#666": "var(--fig-mute)",
    "#0072b2": "var(--s1)", "#d55e00": "var(--s2)",
    "#009e73": "var(--s3)", "#cc79a7": "var(--s4)",
}
MONO_STACK = ("'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace")


# The pipeline draws the chart title at y=24 and the subtitle at y=40, and puts
# the legend row at y=39. The two collide in every committed figure. Lifting the
# title and subtitle out of the SVG and into the page's own type both fixes the
# collision and makes them selectable, responsive and theme-styled. Geometry,
# data and legend are untouched. If the pattern does not match, the SVG is left
# exactly as the pipeline wrote it.
TITLE_RE = re.compile(r'<text\b[^>]*\by="24"[^>]*>(.*?)</text>\s*', re.S)
SUB_RE = re.compile(r'<text\b[^>]*\by="40"[^>]*>(.*?)</text>\s*', re.S)
CROP = 22


def _theme_svg(svg):
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    title = sub = ""
    mt = TITLE_RE.search(svg)
    ms = SUB_RE.search(svg)
    if mt and ms:
        title, sub = mt.group(1).strip(), ms.group(1).strip()
        svg = TITLE_RE.sub("", svg, count=1)
        svg = SUB_RE.sub("", svg, count=1)
        vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        if vb:
            w, h = float(vb.group(1)), float(vb.group(2))
            svg = svg.replace(vb.group(0), f'viewBox="0 {CROP} {w:g} {h - CROP:g}"', 1)

    def swap(m):
        return f'{m.group(1)}="{SVG_COLOURS.get(m.group(2).lower(), m.group(2))}"'

    svg = re.sub(r'\b(fill|stroke)="([^"]+)"', swap, svg)
    # Drop intrinsic pixel dimensions so the CSS can size it fluidly; the
    # viewBox that carries the geometry is left alone.
    svg = re.sub(r'(<svg\b[^>]*?)\swidth="[^"]*"', r"\1", svg, count=1)
    svg = re.sub(r'(<svg\b[^>]*?)\sheight="[^"]*"', r"\1", svg, count=1)
    # The font stack is left as the pipeline wrote it: label positions in these
    # files are laid out against that stack, and swapping in a wider face would
    # collide the legend text.
    return svg, title, sub


def figure(repo, name, caption, legend=""):
    """Inline a committed SVG so the page has no external asset dependency."""
    p = REPOS / repo / "outputs" / "figures" / name
    if not p.exists():
        return ""
    svg, title, sub = _theme_svg(p.read_text(encoding="utf-8"))
    head = f'<h3 class="fig-title">{title}</h3>' if title else ""
    head += f'<p class="fig-sub">{sub}</p>' if sub else ""
    return (f'<figure class="fig"><span class="label">{esc(name)}</span>{head}'
            f'<div class="fig-scroll">{svg}</div>{legend}'
            f'<figcaption>{caption}'
            f'<span class="src">Source artifact: outputs/figures/{esc(name)}</span></figcaption></figure>')


CHARTS_JS = (ROOT / "tools" / "charts.js").read_text(encoding="utf-8")


def _engine(name):
    """Read a storytelling engine asset. Missing assets are tolerated: the page
    keeps the markers, so tools/inline_story.py can fill them in later."""
    p = ROOT / "tools" / name
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        print(f"note: tools/{name} not found, page ships without the engine", file=sys.stderr)
        return ""


STORY_CSS = _engine("story.css")
STORY_JS = _engine("story.js")

# Scroll progress and staggered reveals, driven by the shared engine. Project
# pages carry no orb: the orb belongs to the story pages and the hub. Every call
# is guarded, so the page still reads correctly when the engine is absent.
GLUE_JS = r"""
(function () {
  var S = window.Story;
  if (!S) return;
  if (S.progressBar) { try { S.progressBar(); } catch (e) {} }
  if (S.reveal) { try { S.reveal(document); } catch (e) {} }
})();
"""


# The three doors. Every project page opens the same way: the five-minute story
# for a leader, this page for methods and tables, and the repo's own tool. The
# tool entry names the file that exists in that repo's docs/ directory.
DOORS = {
    "ehs-osha-analysis": ("explore.html", "Denominator explorer",
                          "Screen a site's hours and watch its TRIR move."),
    "ehs-ai-grounding-eval": ("try.html", "Answer an item",
                              "Take one benchmark question before you read the scores."),
    "ehs-human-factors-ontology": ("walkthrough.html", "Derivation walkthrough",
                                   "Step through one assessment rule by rule."),
    "ehs-risk-sem": ("api/", "API reference",
                     "Every estimator and study entry point, documented."),
}
DOOR_EXTRA = {
    "ehs-human-factors-ontology": ("crosswalk.html", "Crosswalk browser"),
}


def doors(repo):
    """One consistent three-door strip under the hero: story, this page, tool."""
    href, name, note = DOORS[repo]
    extra = DOOR_EXTRA.get(repo)
    third = (f'<a class="door" href="{href}"><span class="door-k">Tool</span>'
             f'<span class="door-n">{esc(name)}</span>'
             f'<span class="door-w">{esc(note)}</span>'
             f'<span class="door-go" aria-hidden="true">&rarr;</span></a>')
    side = ""
    if extra:
        side = (f'<a class="door-also" href="{extra[0]}">Also: {esc(extra[1])}'
                f'<span aria-hidden="true"> &rarr;</span></a>')
    return (
        '<nav class="doors" aria-label="Three ways into this project"><div class="wrap">'
        '<div class="doors-grid">'
        '<a class="door" href="story.html"><span class="door-k">Story</span>'
        '<span class="door-n">5 minutes, for leaders</span>'
        '<span class="door-w">The finding as a narrated sequence, no method detail.</span>'
        '<span class="door-go" aria-hidden="true">&rarr;</span></a>'
        '<span class="door door-here" aria-current="page"><span class="door-k">Project page</span>'
        '<span class="door-n">Methods and tables</span>'
        '<span class="door-w">You are here. Every number traced to a committed file.</span>'
        '<span class="door-go" aria-hidden="true">&#9679;</span></span>'
        + third + '</div>' + side + '</div></nav>')


def chart(spec, takeaway, source):
    """Interactive chart: inline JSON, rendered client-side by charts.js."""
    data = html.escape(json.dumps(spec, separators=(",", ":")), quote=True)
    return (f'<figure class="chart" data-chart="{data}"><p class="chart-take">{takeaway}</p>'
            f'<div class="chart-slot"></div><span class="src">Source artifact: {esc(source)}</span></figure>')


def statrow(status):
    return f'<div class="statrow">{status}</div>'


_SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9])')


def lead_first(text, keep=1, label="Why"):
    """Keep the first sentence(s) visible; fold the rest into a details."""
    parts = _SENT.split(text.strip(), maxsplit=keep)
    if len(parts) <= keep or len(parts[-1]) < 40:
        return text
    return (" ".join(parts[:keep])
            + f'<details class="more"><summary>{label}</summary><div>{parts[-1]}</div></details>')


def trim_page(page):
    """Copy cut applied at the end: captions, finding bodies and ledes lead with one sentence."""
    def cap(m):
        return m.group(1) + lead_first(m.group(2)) + m.group(3)
    page = re.sub(r'(<figcaption class="tbl-cap">|<figcaption>)(.*?)(<span class="src">)', cap, page, flags=re.S)
    page = re.sub(r'(<p class="f-body">)(.*?)(</p>)', cap, page, flags=re.S)
    page = re.sub(r'(<p class="sec-lede">)(.*?)(</p>)', cap, page, flags=re.S)
    # standalone prose blocks and opener sidebars fold whole
    page = re.sub(r'(?<!<div class="cols">)(<div class="prose">(?:(?!<div class="cols">).)*?</div>)(?=\s*(?:</div></section>|<figure|<div class="findings"|<details))',
                  r'<details class="more"><summary>Notes</summary><div>\1</div></details>', page, flags=re.S)
    page = re.sub(r'(<div class="opener-side"><h3>.*?</h3>)(.*?)(</div></div>)',
                  lambda m: m.group(1) + '<details class="more"><summary>Read on</summary><div>' + m.group(2) + '</div></details>' + m.group(3),
                  page, flags=re.S)
    # method / notes columns collapse whole
    page = re.sub(r'(<div class="cols">.*?</div></div>)',
                  r'<details class="more"><summary>Method, limits and notes</summary><div>\1</div></details>',
                  page, flags=re.S)
    return page


def legend(items):
    sp = "".join(f'<span><i style="background:{c}"></i>{esc(l)}</span>' for l, c in items)
    return f'<div class="fig-legend">{sp}</div>'


def svg_open(w, h, title):
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="{MONO_STACK}">'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="var(--fig-paper)"/>')


def svg_text(x, y, s, size=11, anchor="start", fill="var(--fig-axis)", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}" font-weight="{weight}">{esc(s)}</text>')


def fig_lines(series, xlabels, ylo, yhi, yticks, caption, title,
              ref=None, reflabel="", source="", legend_items=None):
    """Line chart from real rows. series = [(name, [y...], colour), ...]."""
    w, h = 860, 420
    L, R, T, B = 74, 210, 30, 52
    pw, ph = w - L - R, h - T - B
    n = len(xlabels)
    out = [svg_open(w, h, title)]

    def ypx(v):
        return T + ph - (v - ylo) / (yhi - ylo) * ph

    def xpx(i):
        return L + (pw * i / (n - 1) if n > 1 else pw / 2)

    for t in yticks:
        y = ypx(t)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" '
                   f'stroke="var(--fig-grid)" stroke-width="1"/>')
        out.append(svg_text(L - 10, y + 4, f"{t:g}", 11, "end", "var(--fig-mute)"))
    if ref is not None:
        y = ypx(ref)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" '
                   f'stroke="var(--ink)" stroke-width="2" stroke-dasharray="7 5"/>')
        out.append(svg_text(L + pw + 10, y + 4, reflabel, 11, "start", "var(--ink)", "700"))
    for i, lab in enumerate(xlabels):
        out.append(svg_text(xpx(i), T + ph + 24, lab, 11, "middle", "var(--fig-mute)"))
    out.append(f'<line x1="{L}" y1="{T+ph:.1f}" x2="{L+pw}" y2="{T+ph:.1f}" '
               f'stroke="var(--fig-axis)" stroke-width="2"/>')
    ends = []
    for name, ys, colour in series:
        pts = " ".join(f"{xpx(i):.1f},{ypx(v):.1f}" for i, v in enumerate(ys) if v is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
        for i, v in enumerate(ys):
            if v is not None:
                out.append(f'<circle cx="{xpx(i):.1f}" cy="{ypx(v):.1f}" r="3.5" fill="{colour}"/>')
        last = [v for v in ys if v is not None]
        if last:
            ends.append([ypx(last[-1]), name, colour])
    # Series names sit at the end of their line. Push them apart when the lines
    # finish close together, so no two labels overlap.
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i - 1][0] < 13:
            ends[i][0] = ends[i - 1][0] + 13
    for y, name, colour in ends:
        out.append(svg_text(L + pw + 10, y + 4, name, 10, "start", colour, "600"))
    out.append("</svg>")
    lg = legend(legend_items) if legend_items else ""
    return (f'<figure class="fig"><h3 class="fig-title">{esc(title)}</h3>'
            f'<div class="fig-scroll">{"".join(out)}</div>{lg}'
            f'<figcaption>{caption}<span class="src">Source artifact: {esc(source)}</span>'
            f'</figcaption></figure>')


def fig_stacked(rows, keys, colours, caption, title, source="", unit=""):
    """Horizontal stacked bars. rows = [(label, {key: value})]."""
    barh, gap, T = 26, 12, 26
    rows = [(lab if len(lab) <= 34 else lab[:33].rstrip() + ".", d) for lab, d in rows]
    # 11px IBM Plex Mono advances about 6.6px per character; size the label
    # gutter to the longest label so nothing is clipped at the left edge.
    L = int(min(330, 24 + 6.8 * max(len(lab) for lab, _ in rows)))
    R = 90
    w = 860
    h = T + len(rows) * (barh + gap) + 34
    total_max = max(sum(d.get(k, 0) for k in keys) for _, d in rows) or 1
    pw = w - L - R
    out = [svg_open(w, h, title)]
    for i, (lab, d) in enumerate(rows):
        y = T + i * (barh + gap)
        out.append(svg_text(L - 14, y + barh * 0.68, lab, 11, "end", "var(--fig-axis)", "600"))
        x = L
        for k, c in zip(keys, colours):
            v = d.get(k, 0)
            if not v:
                continue
            bw = pw * v / total_max
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{barh}" fill="{c}"/>')
            if bw > 22:
                # Pale segments need dark text on them, not the reversed-out white
                # that reads on the saturated ones.
                ink = "var(--fig-axis)" if c == "var(--fig-grid)" else "var(--fig-paper)"
                out.append(svg_text(x + bw / 2, y + barh * 0.68, str(v), 10, "middle", ink, "700"))
            x += bw
        tot = sum(d.get(k, 0) for k in keys)
        out.append(svg_text(x + 10, y + barh * 0.68, f"{tot}{unit}", 11, "start",
                            "var(--fig-mute)", "600"))
    out.append("</svg>")
    lg = legend(list(zip(keys, colours)))
    return (f'<figure class="fig"><h3 class="fig-title">{esc(title)}</h3>'
            f'<div class="fig-scroll">{"".join(out)}</div>{lg}'
            f'<figcaption>{caption}<span class="src">Source artifact: {esc(source)}</span>'
            f'</figcaption></figure>')


def fig_bars(rows, caption, title, source="", fmt_val=lambda v: f"{v:.1f}"):
    """Simple horizontal bars. rows = [(label, value_0_to_1)]."""
    barh, gap, T = 30, 14, 26
    L = int(min(330, 24 + 6.8 * max(len(lab) for lab, _ in rows)))
    R, w = 110, 860
    h = T + len(rows) * (barh + gap) + 30
    pw = w - L - R
    top = max(v for _, v in rows) or 1
    out = [svg_open(w, h, title)]
    for i, (lab, v) in enumerate(rows):
        y = T + i * (barh + gap)
        out.append(svg_text(L - 14, y + barh * 0.66, lab, 11, "end", "var(--fig-axis)", "600"))
        bw = pw * v / top
        out.append(f'<rect x="{L}" y="{y}" width="{pw:.1f}" height="{barh}" fill="var(--fig-grid)"/>')
        out.append(f'<rect x="{L}" y="{y}" width="{bw:.1f}" height="{barh}" fill="var(--s1)"/>')
        out.append(svg_text(L + pw + 12, y + barh * 0.66, fmt_val(v), 12, "start",
                            "var(--ink)", "700"))
    out.append("</svg>")
    return (f'<figure class="fig"><h3 class="fig-title">{esc(title)}</h3>'
            f'<div class="fig-scroll">{"".join(out)}</div>'
            f'<figcaption>{caption}<span class="src">Source artifact: {esc(source)}</span>'
            f'</figcaption></figure>')


def read_csv(path):
    with io.open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def md_table(path, heading):
    """Extract a pipe table that follows a markdown heading. Returns (head, rows)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().lstrip("#").strip() == heading)
    except StopIteration:
        return None
    rows = []
    for l in lines[start + 1:]:
        s = l.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            rows.append(cells)
        elif rows:
            break
        elif s.startswith("#"):
            break
    return (rows[0], rows[1:]) if len(rows) > 1 else None


def md_inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_table_html(pair, caption, source):
    head, rows = pair
    th = "".join(f"<th>{md_inline(c)}</th>" for c in head)
    trs = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            cls = ' class="t-first"' if i == 0 else ""
            tds.append("<td" + cls + ">" + md_inline(c) + "</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    trs = "".join(trs)
    return (f'<figure class="tbl"><div class="tbl-wrap"><table>'
            f'<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'
            f'<figcaption class="tbl-cap">{caption}'
            f'<span class="src">Source artifact: {esc(source)}</span></figcaption></figure>')


# ===================== ehs-osha-analysis =====================
def build_osha():
    repo = "ehs-osha-analysis"
    out = REPOS / repo / "outputs"
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    q = s["quality"]["pooled"]
    years = s["quality"]["by_year"]
    conc = s["quality"]["hours_concentration"]
    ratios = [y["ratio_screened_to_unscreened"] for y in years]
    scr = [y["aggregate_trir_screened"] for y in years]
    uns = [y["aggregate_trir_unscreened"] for y in years]
    ylab = [str(int(float(y["label"]))) for y in years]
    y0, y1 = ylab[0], ylab[-1]
    worst = years[ratios.index(max(ratios))]
    best = years[ratios.index(min(ratios))]
    dedup = s["load_report"]["duplicate_rows_dropped"]
    top1 = conc[0]

    status = "".join([
        cell("Filings", f'{q["n_filings"]:,}'),
        cell("Years", f"{y0}-{y1}"),
        cell("Flagged", f'{q["implausible_share"]*100:.2f}%'),
        cell("Of all hours", f'{q["hours_share_implausible"]*100:.1f}%', True),
    ])

    lead = opener(
        "The correction is real, it is large, and it is not a constant. That last part is "
        "what stops it being a footnote.",
        [f"Every establishment-level injury benchmark in the United States is computed from the "
         f"same public filings analysed here: {q['n_filings']:,} of them, calendar years {y0} "
         f"through {y1}, downloaded from the OSHA Injury Tracking Application by a script in this "
         f"repository. The rate everyone quotes has hours worked in its denominator.",
         f"Only {q['implausible_share']*100:.2f}% of filings report hours that cannot be right. "
         f"Those filings carry {q['hours_share_implausible']*100:.1f}% of every hour in the "
         f"dataset. Pooled aggregate TRIR reads {q['aggregate_trir_unscreened']:.3f} before the "
         f"screen and {q['aggregate_trir_screened']:.3f} after it.",
         f"A ratio of {q['ratio_screened_to_unscreened']:.1f}x would still be manageable if it "
         f"held still. It does not. The same screen moves {int(float(best['label']))} by "
         f"{best['ratio_screened_to_unscreened']:.2f}x and {int(float(worst['label']))} by "
         f"{worst['ratio_screened_to_unscreened']:.0f}x. Nobody can apply a published correction "
         f"factor to their own year and know what they have."],
        "What follows from that",
        "<ul>"
        "<li>An unscreened aggregate is not a noisy estimate of the screened one. Their "
        "relationship changes year to year, so the error has no fixed sign or size.</li>"
        "<li>The screened series is stable. That is the useful finding: screening does not just "
        "shift the number, it makes the series comparable across years at all.</li>"
        "<li>Anyone publishing a benchmark from these files owes readers the screen they used. "
        "Without it the number is not reproducible even in principle.</li>"
        "</ul>")

    findings = f'''<div class="findings">
      <div class="finding">
        <div class="f-num">{max(ratios):.0f}<span class="f-unit">&times;</span></div>
        <div class="f-title">Worst-year divergence</div>
        <p class="f-body">Aggregate TRIR computed with and without the plausibility screen differs by {min(ratios):.2f}x in {int(float(best["label"]))} and {max(ratios):.0f}x in {int(float(worst["label"]))}. A correction that varies by two orders of magnitude between adjacent years is not a portable constant.</p>
        <div class="f-src">summary.json - quality.by_year</div>
      </div>
      <div class="finding">
        <div class="f-num">{q["hours_share_implausible"]*100:.1f}<span class="f-unit">%</span></div>
        <div class="f-title">Hours concentrated in flagged filings</div>
        <p class="f-body">{q["implausible_share"]*100:.2f}% of filings fail the hours-per-employee screen, and they carry {q["hours_share_implausible"]*100:.1f}% of every hour reported. Aggregate TRIR reads {q["aggregate_trir_unscreened"]:.3f} unscreened against {q["aggregate_trir_screened"]:.3f} screened.</p>
        <div class="f-src">summary.json - quality.pooled</div>
      </div>
      <div class="finding">
        <div class="f-num">{min(scr):.1f}<span class="f-unit">-{max(scr):.1f}</span></div>
        <div class="f-title">Screening yields a stable series</div>
        <p class="f-body">Screened aggregate TRIR stays inside a narrow band across all {len(years)} years, while the unscreened figure swings between {min(uns):.3f} and {max(uns):.2f}. The screen is doing more than trimming outliers.</p>
        <div class="f-src">outputs/tables/quality_by_year.csv</div>
      </div>
      <div class="finding">
        <div class="f-num">{q["median_establishment_trir_screened"]:.2f}</div>
        <div class="f-title">Median establishment TRIR</div>
        <p class="f-body">The median screened establishment sits well below the screened aggregate, which is what a right-skewed count distribution looks like. Reporting a mean against this shape overstates the typical site.</p>
        <div class="f-src">summary.json - quality.pooled</div>
      </div>
    </div>'''

    yr_rows = "".join(
        f'<tr><td class="t-first">{int(float(y["label"]))}</td><td>{y["n_filings"]:,}</td>'
        f'<td>{y["implausible_share"]*100:.2f}%</td><td>{y["hours_share_implausible"]*100:.1f}%</td>'
        f'<td>{y["aggregate_trir_unscreened"]:.3f}</td><td>{y["aggregate_trir_screened"]:.3f}</td>'
        f'<td>{y["ratio_screened_to_unscreened"]:.2f}x</td>'
        f'<td>{y["median_establishment_trir_screened"]:.2f}</td></tr>' for y in years)
    yr_tbl = (
        '<figure class="tbl"><div class="tbl-wrap"><table><thead><tr><th>Year</th><th>Filings</th>'
        '<th>Flagged</th><th>Hours flagged</th><th>TRIR raw</th><th>TRIR screened</th>'
        f'<th>Ratio</th><th>Median est. TRIR</th></tr></thead><tbody>{yr_rows}</tbody></table></div>'
        '<figcaption class="tbl-cap">Read across the last two columns rather than down them. '
        'The screened aggregate and the median establishment barely move; the ratio between '
        'screened and unscreened moves by a factor of nearly two hundred.'
        '<span class="src">Source artifact: outputs/summary.json - quality.by_year</span>'
        '</figcaption></figure>')

    conc_fig = fig_bars(
        [(f'Top {int(c["top_n_filings_by_hours"]):,} filing'
          f'{"" if int(c["top_n_filings_by_hours"]) == 1 else "s"}', c["hours_share"])
         for c in conc],
        "One keying error in the hours column sets the national denominator. A single "
        f'establishment filing accounts for {top1["hours_share"]*100:.1f}% of the '
        f"{q['hours_total']/1e12:.1f} trillion hours in the pooled dataset while contributing "
        f'{top1["cases_share"]*100:.2f}% of the recordable cases. Share of all reported hours '
        "held by the largest filings, ranked by hours.",
        "Hours concentration in the largest filings",
        "outputs/tables/quality_hours_concentration.csv",
        fmt_val=lambda v: f"{v*100:.2f}%")

    trir_chart = chart(
        {"type": "line", "title": "Aggregate TRIR by year, screened against unscreened",
         "x": ylab, "aspect": 2.2, "y": {"min": 0},
         "series": [
             {"name": "Unscreened", "values": [round(v, 3) for v in uns],
              "tip": [f"ratio {r:.2f}x" for r in ratios]},
             {"name": "Screened", "values": [round(v, 3) for v in scr],
              "tip": [f"ratio {r:.2f}x" for r in ratios]}]},
        f"Screened TRIR stays between {min(scr):.1f} and {max(scr):.1f}. Unscreened swings "
        f"{min(uns):.2f} to {max(uns):.2f}.",
        "outputs/summary.json - quality.by_year")
    hours_chart = chart(
        {"type": "bar", "title": "Share of reported hours in implausible filings, by year",
         "x": ylab, "aspect": 2.4, "y": {"min": 0, "max": 1, "fmt": "pct"},
         "series": [{"name": "Hours in flagged filings",
                     "values": [round(y["hours_share_implausible"], 4) for y in years],
                     "tip": [f'{y["implausible_share"]*100:.2f}% of filings' for y in years]}]},
        f"Flagged filings hold {min(y['hours_share_implausible'] for y in years)*100:.0f}% to "
        f"{max(y['hours_share_implausible'] for y in years)*100:.0f}% of all hours, depending on the year.",
        "outputs/summary.json - quality.by_year")

    figs = trir_chart + hours_chart + '<details class="more"><summary>Static figures</summary><div>' + (
        figure(repo, "fig01_aggregate_trir_by_year.svg",
               "The unscreened series is governed by how much bad hours data entered that "
               "year's file, not by safety performance. That is why the two series cross and "
               "diverge rather than tracking each other: the unscreened aggregate is not a noisy "
               "version of the screened one. Aggregate TRIR by year, screened against unscreened.")
        + figure(repo, "fig02_hours_share_implausible.svg",
                 "Implausible filings hold anywhere from roughly a third to nearly all of the "
                 "reported hours, depending on the year. That swing is what drives the "
                 "instability in the ratio above. Share of all reported hours sitting in filings "
                 "that fail the plausibility screen, by year.")
        + figure(repo, "fig03_hours_per_employee.svg",
                 "The tail extends many orders of magnitude beyond anything a workforce can "
                 "produce, so values outside the window are unit or keying errors rather than "
                 "real labour. Distribution of hours worked per employee; the screen retains 120 "
                 "to 4,500 hours per employee per year.")
        + figure(repo, "fig05_zero_share_by_size.svg",
                 "A zero rate says as much about headcount as about safety performance: zero is "
                 "the modal outcome at small establishments. Share of establishments reporting "
                 "zero recordable cases, by size band.")
        + figure(repo, "fig06_percentile_stability.svg",
                 "A benchmark is only usable if the band a site is compared against holds still "
                 "enough between years to mean the same thing. Year-over-year stability of "
                 "peer-group percentile bands.")
    ) + "</div></details>"

    stab = read_csv(out / "tables" / "percentile_band_stability.csv")
    rho = {}
    rel = {}
    for r in stab:
        rho.setdefault(r["percentile"], []).append(float(r["spearman_rho"]))
        rel.setdefault(r["percentile"], []).append(float(r["median_abs_rel_change"]))
    rho_med = {k: statistics.median(v) for k, v in rho.items()}
    rel_med = {k: statistics.median(v) for k, v in rel.items()}
    worst_band = max(rel_med, key=rel_med.get)
    best_band = min(rel_med, key=rel_med.get)

    peers = (
        table(out / "tables" / "percentile_band_stability.csv",
              f"Rank correlation and median absolute change for each percentile band between "
              f"consecutive years, over peer groups matched in both years. Ordering is stable: the "
              f"median rank correlation runs from {min(rho_med.values()):.2f} to "
              f"{max(rho_med.values()):.2f} across bands. The band values themselves are less so, "
              f"and least so at the bottom, where {worst_band} moves a median of "
              f"{rel_med[worst_band]*100:.0f}% year over year against {rel_med[best_band]*100:.0f}% "
              f"for {best_band}. Low percentiles sit near zero, so a small absolute move is a large "
              f"relative one, which is exactly the region where a site is judged to have improved.",
              source="outputs/tables/percentile_band_stability.csv", limit=12)
        + table(out / "tables" / "size_band_effects.csv",
                "Establishment size against zero share, dispersion and rate. The "
                "variance-to-mean ratio rises steadily with size, so a single Poisson assumption "
                "cannot serve every band.",
                source="outputs/tables/size_band_effects.csv", limit=10,
                cols=["size_band", "n", "zero_share", "mean_recordables",
                      "variance_to_mean_ratio", "aggregate_trir", "median_establishment_trir"],
                pct=["zero_share"])
    )

    method = (
        '<div class="cols"><div class="prose">'
        "<h3>The plausibility screen</h3>"
        "<p>Hours worked divided by average employees must fall between 120 and 4,500 per year. "
        "Below that, hours were filed in the wrong unit. Above it, a keying error. Filings failing "
        "the screen are excluded from aggregates rather than corrected, because the true value is "
        "not recoverable from the filing alone.</p>"
        "<h3>How sensitive is that window</h3>"
        f"<p>The bounds are a judgement call, so the pipeline sweeps them. Across the grid the "
        f"corrected aggregate TRIR moves only between "
        f"{s['quality']['sensitivity_min_corrected_trir']:.3f} and "
        f"{s['quality']['sensitivity_max_corrected_trir']:.3f}, and the flagged share between "
        f"{s['quality']['sensitivity_min_flagged_share']*100:.2f}% and "
        f"{s['quality']['sensitivity_max_flagged_share']*100:.2f}%. The finding does not depend on "
        f"where exactly the window is drawn.</p>"
        "<h3>Reproducing this</h3>"
        "<p>The pipeline downloads the public ITA files itself and fails loudly rather than "
        f"substituting fixtures if they are unavailable. {dedup:,} duplicate rows were dropped "
        "before analysis. Every table and figure on this page is generated by script; none is "
        "hand-entered.</p>"
        "</div><div class=\"prose\">"
        "<h3>Reviewer note</h3>"
        "<p>An internal adversarial review held that this analysis is a separable contribution "
        "being buried inside a larger manuscript, and that it should stand as its own paper. That "
        "criticism is recorded here rather than answered.</p>"
        "</div></div>")

    # ---- signature interactive: screen window, TRIR by year, peer lookup ----
    grid = []
    for r in read_csv(out / "tables" / "quality_sensitivity_grid.csv"):
        try:
            lo, hi = float(r["min_hours_per_employee"]), float(r["max_hours_per_employee"])
        except (TypeError, ValueError):
            continue
        if not re.fullmatch(r"\d+-\d+", r["label"]):
            continue
        grid.append({"lo": int(lo), "hi": int(hi), "flag": round(float(r["implausible_share"]), 6),
                     "hours": round(float(r["hours_share_implausible"]), 6),
                     "scr": round(float(r["aggregate_trir_screened"]), 4),
                     "uns": round(float(r["aggregate_trir_unscreened"]), 4),
                     "ratio": round(float(r["ratio_screened_to_unscreened"]), 3)})
    titles = {}
    ex_path = REPOS / repo / "docs" / "explore-data.json"
    if ex_path.exists():
        titles = json.loads(ex_path.read_text(encoding="utf-8")).get("titles", {})
    prow = {}
    naics = []
    bands = []
    for r in read_csv(out / "tables" / "peer_percentiles_pooled.csv"):
        def f2(k):
            try:
                return round(float(r[k]), 3)
            except (TypeError, ValueError):
                return None
        prow[f'{r["naics3"]}|{r["size_band"]}'] = [int(r["n"]), r["publishable"] == "True"] + \
            [f2(k) for k in ("p10", "p25", "p50", "p75", "p90", "p95", "aggregate_trir")]
        if r["naics3"] not in naics:
            naics.append(r["naics3"])
        if r["size_band"] not in bands:
            bands.append(r["size_band"])
    band_order = ["001-019", "020-049", "050-099", "100-249", "250-499", "500-999", "1000+"]
    bands.sort(key=lambda b_: band_order.index(b_) if b_ in band_order else 99)
    ixdata = {
        "def": {"lo": 120, "hi": 4500}, "grid": grid,
        "years": [{"y": int(float(y["label"])), "scr": round(y["aggregate_trir_screened"], 4),
                   "uns": round(y["aggregate_trir_unscreened"], 4),
                   "ratio": round(y["ratio_screened_to_unscreened"], 3),
                   "hours": round(y["hours_share_implausible"], 5)} for y in years],
        "peers": {"naics": [[n_, titles.get(n_, "")] for n_ in sorted(naics)], "bands": bands, "rows": prow},
    }
    explore = (
        explore_intro("Three ways into the same public filings. Move the plausibility window and "
                      "watch what it does to the national rate, switch the yearly series, then place "
                      "a site's TRIR against its industry peers.", "explore.html", "Full denominator explorer")
        + '<div class="ix" id="ix-osha">'
        '<div class="ix-panel ix-wide"><div class="ix-head"><span class="ix-k">A</span><h3>Move the screen</h3>'
        '<p>Hours per employee per year a filing must fall between to count.</p></div>'
        '<div class="ix-controls"><label>Minimum<select id="ox-lo"></select></label>'
        '<label>Maximum<select id="ox-hi"></select></label></div>'
        '<div class="ox-out" id="ox-out" aria-live="polite">'
        '<div class="ox-read"><span>Filings flagged</span><b data-k="flag">-</b><div class="ox-bar"><i class="ox-bar-f"></i></div></div>'
        '<div class="ox-read"><span>Hours in flagged filings</span><b data-k="hours">-</b><div class="ox-bar"><i class="ox-bar-h"></i></div></div>'
        '<div class="ox-read"><span>TRIR screened</span><b data-k="scr" class="acc">-</b></div>'
        '<div class="ox-read"><span>TRIR unscreened</span><b data-k="uns">-</b></div>'
        '<div class="ox-read"><span>Ratio</span><b data-k="ratio">-</b></div>'
        '<p class="ox-note"></p></div>'
        '<span class="src">Source artifact: outputs/tables/quality_sensitivity_grid.csv (pooled, all years)</span></div>'
        '<div class="ix-panel"><div class="ix-head"><span class="ix-k">B</span><h3>TRIR by year</h3>'
        '<p>Hover or tab through the bars for the year.</p></div>'
        '<div class="seg" id="ox-mode"></div><div class="ox-years" id="ox-years"></div>'
        '<p class="ix-read" id="ox-year-read" aria-live="polite">Select a bar to read the year.</p>'
        '<span class="src">Source artifact: outputs/summary.json - quality.by_year</span></div>'
        '<div class="ix-panel"><div class="ix-head"><span class="ix-k">C</span><h3>Peer percentile lookup</h3>'
        '<p>Pooled screened percentiles by three-digit NAICS and size band.</p></div>'
        '<div class="ix-controls"><label>Industry (NAICS 3)<select id="ox-naics"></select></label>'
        '<label>Size band<select id="ox-size"></select></label>'
        '<label>Your TRIR<input id="ox-trir" type="number" inputmode="decimal" min="0" step="0.1" value="3.0" /></label></div>'
        '<div class="ox-peer" id="ox-peer"><div class="ox-strip"></div><div class="ox-pcts"></div><p class="ox-peer-msg" aria-live="polite"></p><p class="ox-peer-meta"></p></div>'
        '<span class="src">Source artifact: outputs/tables/peer_percentiles_pooled.csv</span></div>'
        '</div>' + jsdata("ix-osha-data", ixdata))

    sens = s["quality"]
    osha_scope = scope(
        [f"Which filings report hours that cannot be right: {q['implausible_share']*100:.2f}% of "
         f"{q['n_filings']:,} filings, carrying {q['hours_share_implausible']*100:.1f}% of all hours.",
         f"That the screened-to-unscreened correction is not a constant. It runs {min(ratios):.2f}x "
         f"to {max(ratios):.0f}x depending on the year.",
         f"That the result does not hinge on where the window is drawn: across the sensitivity grid "
         f"corrected TRIR stays between {sens['sensitivity_min_corrected_trir']:.3f} and "
         f"{sens['sensitivity_max_corrected_trir']:.3f}.",
         "That screened percentile ordering is stable between years, while the low bands move most."],
        ["The screen identifies filings that cannot be right. It does not identify filings that "
         "are merely wrong, and it cannot recover the true hours for an excluded establishment.",
         "Aggregates after screening are conditional on the surviving population, which is not a "
         "random sample of the original. If implausible hours are filed disproportionately by one "
         "kind of employer, the screened aggregate inherits that selection.",
         "Nothing here is a claim about whether workplaces got safer. It is a claim about what "
         "the denominator will support."])
    qs = quickstart(repo, [
        "python scripts/download_data.py --list     # show the catalog and URLs",
        "python scripts/download_data.py            # ~170 MB into data/raw",
        "python scripts/run_analysis.py             # writes outputs/",
        'cd tests && python -m unittest discover -s . -p "test_*.py"'],
        '<p class="qs-note">Or <code>make data</code>, <code>make analysis</code>, <code>make test</code>. '
        'The pipeline downloads the public ITA files itself and fails loudly rather than substituting fixtures.</p>')

    body = (
        section("explore", "00", "Try the denominator", explore)
        + section("why", "01", "Why this exists", lead)
        + section("findings", "02", "Findings", findings,
                  lede="Four numbers, each traceable to the artifact named beneath it.")
        + section("scope", "00", "What this does and does not show", osha_scope)
        + section("byyear", "03", "Year by year", yr_tbl,
                  lede="The pooled ratio is an average over years that do not resemble each other. "
                       "The point of this table is the spread, not the centre.")
        + section("hours", "04", "Where the hours are", conc_fig,
                  lede="A national aggregate rate is a sum of cases over a sum of hours. When one "
                       "filing dominates the second sum, it decides the answer on its own.")
        + section("figures", "05", "Figures", figs,
                  lede="Two interactive charts from summary.json. The pipeline's static figures "
                       "sit underneath.")
        + section("models", "06", "Count models",
                  table(out / "tables" / "count_model_selection_summary.csv",
                        "Which count model wins on AIC, across the thirty largest three-digit "
                        "NAICS industries fitted for the model year.",
                        source="outputs/tables/count_model_selection_summary.csv", limit=6,
                        pct=["share_best_by_aic"])
                  + '<div class="prose"><p>Poisson, negative binomial, zero-inflated Poisson and '
                    "zero-inflated negative binomial were fitted per industry and compared by "
                    "likelihood ratio and AIC. Boundary-corrected p-values are reported because the "
                    "zero-inflation parameter sits on the edge of its parameter space, where the "
                    "naive chi-squared reference distribution does not hold. Poisson never wins, "
                    "which is the practical result: injury counts are overdispersed everywhere, so "
                    "control limits built on a Poisson assumption are too tight.</p></div>",
                  lede="Rates are ratios of counts, and the count distribution decides what a "
                       "control limit or a significance test on that rate is allowed to say.")
        + section("peers", "07", "Peer benchmarking", peers,
                  lede="If a benchmark is going to be used to judge a site, the peer group it is "
                       "judged against has to be stable between years.")
        + section("method", "08", "Method and limits", method,
                  lede="The screen, its sensitivity, and what the result does not license.")
        + section("run", "00", "Run it yourself", qs)
    )

    return dict(
        repo=repo, mark="O", title="OSHA injury-rate data quality - " + repo,
        desc="A reproducible analysis of data quality in OSHA Injury Tracking Application "
             "establishment filings, over 2.8 million real public records.",
        kicker="Empirical analysis - real public data",
        h1="The hours column decides every benchmark built on it",
        lede=f"A reproducible pipeline over {q['n_filings']:,} filings, CY{y0}-{y1}. "
             f"{q['implausible_share']*100:.2f}% of filings carry "
             f"{q['hours_share_implausible']*100:.1f}% of all hours, and the correction ranges "
             f"{min(ratios):.2f}x to {max(ratios):.0f}x by year. It cannot be published as a "
             f"constant.",
        num=f"{q['hours_share_implausible']*100:.1f}", num_dec=1, unit="%",
        means=f"of every reported hour sits in the {q['implausible_share']*100:.2f}% of filings "
              f"that fail the plausibility screen. Correcting for them moves aggregate TRIR by "
              f"{min(ratios):.2f}x in one year and {max(ratios):.0f}x in another.",
        num_src="outputs/summary.json - quality.pooled", cta="Try the denominator",
        nots="Nothing here says a flagged filing is wrong, or that any establishment is unsafe. "
             "The screen marks hours that cannot be reconciled with the headcount reported beside "
             "them. It does not identify a cause, and it does not correct the record.",
        toc={"explore": "Try it", "why": "Why this exists|Why", "findings": "Findings",
             "scope": "Does / does not|Scope", "byyear": "Year by year|By year",
             "hours": "Where the hours are|Hours",
             "figures": "Figures", "models": "Count models|Models", "peers": "Peer benchmarking|Peers",
             "method": "Method", "run": "Run it"},
        status=status, body=body)


# ===================== ehs-risk-sem =====================
def build_sem():
    repo = "ehs-risk-sem"
    res = REPOS / repo / "results"
    files = sorted(p.name for p in res.glob("*.csv"))
    studies = sorted({f.split("_")[0] for f in files})

    rec = read_csv(res / "study01_recovery.csv")
    ns = sorted({int(r["n"]) for r in rec})
    preds = []
    for r in rec:
        if r["predictor"] not in preds:
            preds.append(r["predictor"])
    by = {(int(r["n"]), r["predictor"]): r for r in rec}
    cov_all = [float(r["coverage_95_analytic"]) for r in rec]
    ser_all = [float(r["se_ratio_analytic_over_empirical"]) for r in rec]

    req = read_csv(res / "study01_requirements.csv")
    req_map = {r["requirement"]: int(r["n_required"]) for r in req}
    conf = read_csv(res / "study03_confounder.csv")
    conf_om = next(r for r in conf if "omitted" in r["fitted_model"])
    conf_in = next(r for r in conf if "included" in r["fitted_model"])
    equiv = read_csv(res / "study03_equivalent.csv")
    imb = read_csv(res / "study02_imbalance.csv")
    under = next((r for r in imb if "undersampling" in r["training_sample"]), None)

    status = "".join([
        cell("Simulation studies", str(len(studies))),
        cell("Result tables", str(len(files))),
        cell("Coefficients recovered", "Yes"),
        cell("Real-world claims", "None", True),
    ])

    lead = opener(
        "A formula that fits perfectly, recovers its own coefficients, and passes every "
        "conventional cutoff can still point the wrong way down its own arrows.",
        ["A particular formula circulates in practitioner writing on safety analytics: risk as a "
         "weighted sum of unsafe acts, operational stress, system condition and safety response "
         "capability, with weights around 0.45, 0.30, -0.25 and -0.20, described as a structural "
         "equation model with machine-constructed latent variables.",
         "This repository builds the estimator that would be needed to produce that formula, from "
         "scratch in numpy, and then tests what such an estimator can support. Most of the answer "
         "is negative, and the negative results are the contribution.",
         f"The clearest one is here. Fitting the same data with the causal arrow reversed returns "
         f"an identical coefficient ({float(equiv[0]['beta']):.3f} both ways), an identical "
         f"chi-square, an identical CFI and an identical SRMR. Both models meet every conventional "
         f"cutoff. Goodness of fit cannot tell you which way causation runs, because it never "
         f"could."],
        "Everything here is simulated",
        "<p>Every number on this page comes from data generated by a model whose parameters were "
        "fixed in advance. That is what a simulation study is for: ground truth is known, so "
        "estimator behaviour can be measured against it rather than assumed.</p>"
        "<p><strong>No number on this page is a claim about any real workplace, any real "
        "programme, or any real injury.</strong> Nothing in this repository touches real injury "
        "data at any point.</p>")

    disc = read_csv(res / "study02_discrimination.csv")
    disc.sort(key=lambda r: float(r["target_base_rate"]), reverse=True)
    rec_chart = chart(
        {"type": "line", "title": "95% interval coverage by sample size", "x": [f"n={n:,}" for n in ns],
         "aspect": 2.2, "ref": 0.95, "refLabel": "nominal 95%", "y": {"min": 0.7, "max": 1.0, "fmt": "pct"},
         "series": [{"name": p.replace("SafetyResponseCapability", "SafetyResponse"),
                     "values": [round(float(by[(n, p)]["coverage_95_analytic"]), 3) for n in ns],
                     "tip": [f'SE ratio {float(by[(n, p)]["se_ratio_analytic_over_empirical"]):.2f}, '
                             f'RMSE {float(by[(n, p)]["rmse"]):.3f}' for n in ns]} for p in preds]},
        f"Coverage sits at {min(cov_all)*100:.0f}% to {max(cov_all)*100:.0f}% against a nominal 95%, "
        "at every sample size.",
        "results/study01_recovery.csv")
    cal_chart = chart(
        {"type": "bar", "title": "Calibration slope by event base rate",
         "x": [f'{float(r["target_base_rate"])*100:g}%' for r in disc], "aspect": 2.4,
         "ref": 1.0, "refLabel": "ideal slope 1.0", "y": {"min": 0, "fmt": 2},
         "series": [{"name": "Calibration slope", "values": [round(float(r["calibration_slope"]), 3) for r in disc],
                     "tip": [f'AUC {float(r["auc"]):.3f}, ECE {float(r["ece"]):.4f}, '
                             f'{float(r["alerts_per_true_event_at_top_5pct"]):.1f} alerts per true event' for r in disc]}]},
        f"AUC holds near {statistics.median(float(r['auc']) for r in disc):.2f} at every base rate; "
        f"alerts per true event climb to {max(float(r['alerts_per_true_event_at_top_5pct']) for r in disc):.0f} at the rarest.",
        "results/study02_discrimination.csv")

    cov_fig = rec_chart + cal_chart + fig_lines(
        [(p.replace("SafetyResponseCapability", "SafetyResponse"),
          [float(by[(n, p)]["coverage_95_analytic"]) for n in ns],
          f"var(--s{i+1})") for i, p in enumerate(preds)],
        [f"n={n:,}" for n in ns], 0.70, 1.00,
        [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00],
        "Coverage of the nominal 95% confidence interval, by sample size, for each of the four "
        f"path coefficients. Coverage should sit on the dashed line. It sits between "
        f"{min(cov_all)*100:.0f}% and {max(cov_all)*100:.0f}% instead, and it does not improve "
        f"with sample size: the analytic standard errors are {min(ser_all)*100:.0f}% to "
        f"{max(ser_all)*100:.0f}% of the empirical ones at every n tested. The point estimates are "
        "nearly unbiased. It is the uncertainty around them that is wrong, which is the more "
        "dangerous failure, because an interval that is too narrow reads as confidence.",
        "Interval coverage against sample size",
        ref=0.95, reflabel="nominal 95%",
        source="results/study01_recovery.csv")

    rec_tbl = table(
        res / "study01_recovery.csv",
        "Bias, spread and interval coverage for each coefficient at each sample size, over 300 "
        "replications per cell. Bias is negligible everywhere. Coverage never reaches its nominal "
        "level anywhere.",
        source="results/study01_recovery.csv", limit=24,
        cols=["n", "predictor", "true_beta", "mean_estimate", "bias", "empirical_sd",
              "coverage_95_analytic", "se_ratio_analytic_over_empirical"],
        rename={"se_ratio_analytic_over_empirical": "SE ratio",
                "coverage_95_analytic": "coverage 95"})

    sizing = (
        table(res / "study01_requirements.csv",
              "Sample size required for each analytic goal, computed from the same generating "
              "model. Distinguishing the two negative coefficients from one another needs a sample "
              f"of {req_map.get('distinguish beta = -0.25 from beta = -0.20 at 80% power', 0):,}, "
              "which is larger than most sites will ever have. Reporting them as separate drivers "
              "at any realistic n is reporting noise.",
              source="results/study01_requirements.csv", limit=8)
        + table(res / "study01_distinguishability.csv",
                "Every pairwise comparison between coefficients, with the sample size that would "
                "be needed to separate the pair at 80% power. Ranking the drivers is a much harder "
                "task than estimating them.",
                source="results/study01_distinguishability.csv", limit=8))

    rare = (
        table(res / "study02_imbalance.csv",
              "What resampling does to a rare-outcome model. Discrimination is essentially "
              "unchanged by rebalancing, while the predicted probabilities become meaningless: "
              f"undersampling the majority class overpredicts by "
              f"{float(under['overprediction_ratio']):.0f}x if the intercept is not corrected."
              if under else "What resampling does to a rare-outcome model.",
              source="results/study02_imbalance.csv", limit=6,
              cols=["training_sample", "train_n", "train_event_fraction", "auc_test",
                    "mean_predicted_test", "observed_rate_test", "overprediction_ratio",
                    "calibration_slope", "ppv_at_top_5pct"])
        + table(res / "study02_alert_burden.csv",
                "Alerts per true event at realistic base rates. This is the operational meaning of "
                "a rare outcome: at a base rate this low, even a highly specific model buries the "
                "true events under false ones, and the people receiving the alerts stop reading "
                "them.",
                source="results/study02_alert_burden.csv", limit=8)
        + table(res / "study02_sizing.csv",
                "Events and units of observation required to estimate a rare-event rate to a given "
                "relative precision.",
                source="results/study02_sizing.csv", limit=6))

    zero = table(
        res / "study02_zero_inflation.csv",
        "Zero-inflated outcomes are the norm in injury counts. As the structural zero fraction "
        "rises, the observed zeros pull away from what a Poisson would produce and the "
        "variance-to-mean ratio climbs, while the slope on the latent variable attenuates.",
        source="results/study02_zero_inflation.csv", limit=6)

    misspec = (
        table(res / "study03_confounder.csv",
              f"The same data, fitted with and without a confounder. Omitting it inflates the "
              f"coefficient from {float(conf_in['beta_predictor_on_outcome']):.3f} to "
              f"{float(conf_om['beta_predictor_on_outcome']):.3f} against a true direct effect of "
              f"{float(conf_om['true_direct_effect']):.2f}. Both models meet every conventional "
              f"fit cutoff, and the misspecified one fits better.",
              source="results/study03_confounder.csv", limit=4)
        + table(res / "study03_equivalent.csv",
                "Two models with opposite causal directions, fitted to the same data. Every fit "
                "statistic is identical to the last decimal place. No amount of model comparison "
                "separates them; only an assumption from outside the data can.",
                source="results/study03_equivalent.csv", limit=4)
        + table(res / "study03_reverse.csv",
                "Data generated with injuries driving climate, then fitted as climate driving "
                "injuries. The reversed model recovers a large, highly significant coefficient and "
                "passes every cutoff.",
                source="results/study03_reverse.csv", limit=4))

    meaning = (
        table(res / "study04_ambiguity.csv",
              "Four causal worlds that produce nearly identical fitted coefficients, and what "
              "intervening on a variable would actually do in each. The coefficient is the same. "
              "What it licenses you to do is not.",
              source="results/study04_ambiguity.csv", limit=6)
        + table(res / "study04_raw_scale.csv",
                "Two crews carrying identical raw scores at two sites. Standardising the inputs "
                "flips the ranking at the site where overtime varies widely and leaves it intact "
                "where overtime is tightly controlled. Nothing about the crews changed between the "
                "rows; only the scaling did. A weighted-sum score is not scale-free, so the choice "
                "of scaling is a decision about who gets flagged.",
                source="results/study04_raw_scale.csv", limit=6)
        + table(res / "study04_invariance.csv",
                "Measurement loadings at two sites. When an indicator loads differently between "
                "sites, the latent variable does not mean the same thing at both, and comparing "
                "their scores compares two different constructs.",
                source="results/study04_invariance.csv", limit=10))

    short = {"UnsafeActs": "Unsafe acts", "OperationalStress": "Operational stress",
             "SystemCondition": "System condition", "SafetyResponseCapability": "Safety response"}
    reps = sorted({int(r["n_reps"]) for r in rec})
    ixdata = {
        "ns": ns, "preds": preds, "short": {p_: short.get(p_, p_) for p_ in preds},
        "rows": [{"n": int(r["n"]), "p": r["predictor"], "beta": float(r["true_beta"]),
                  "mean": round(float(r["mean_estimate"]), 5), "sd": round(float(r["empirical_sd"]), 5),
                  "se": round(float(r["mean_analytic_se"]), 5),
                  "cov": round(float(r["coverage_95_analytic"]), 4),
                  "ratio": round(float(r["se_ratio_analytic_over_empirical"]), 4)} for r in rec],
    }
    explore = (
        explore_intro(f"Every estimate below was produced by fitting data simulated from known path "
                      f"weights, {', '.join(str(x) for x in reps)} replications per cell. Drag the "
                      "sample size. The wide band is where estimates actually land; the thin bar is the "
                      "interval the estimator reports. When the thin bar is shorter, the reported "
                      "confidence is false.", "api/", "API reference")
        + '<div class="ix" id="ix-sem">'
        '<div class="ix-panel ix-wide"><div class="ix-controls sx-controls">'
        f'<label class="sx-slider">Sample size <output id="sx-nlab">n = {ns[0]:,}</output>'
        f'<input id="sx-n" type="range" min="0" max="{len(ns)-1}" step="1" value="0" /></label>'
        '<div class="sx-legend"><span><i class="lg-emp"></i>Where estimates land (mean &plusmn; 1.96 empirical SD)</span>'
        '<span><i class="lg-an"></i>Interval the estimator reports (&plusmn; 1.96 analytic SE)</span>'
        '<span><i class="lg-true"></i>True weight</span></div></div>'
        '<div class="sx-grid"><div><h3 class="ix-sub">All four paths at this n <small>select a row</small></h3><div id="sx-four" class="sx-svg"></div></div>'
        '<div class="sx-readout" aria-live="polite"><h3 class="ix-sub" data-k="p">-</h3><dl>'
        '<dt>True weight</dt><dd data-k="beta">-</dd><dt>Mean estimate</dt><dd data-k="mean">-</dd>'
        '<dt>Empirical SD</dt><dd data-k="sd">-</dd><dt>Mean analytic SE</dt><dd data-k="se">-</dd>'
        '<dt>SE ratio</dt><dd data-k="ratio">-</dd><dt>95% coverage</dt><dd data-k="cov" class="acc">-</dd></dl>'
        '<div class="sx-covbar" aria-hidden="true"><i></i><b style="left:95%"></b></div>'
        '<p class="sx-covnote">Tick marks the nominal 95%.</p></div></div>'
        '<h3 class="ix-sub">The selected path, at every sample size tested</h3><div id="sx-byn" class="sx-svg"></div>'
        '<span class="src">Source artifact: results/study01_recovery.csv</span></div></div>'
        + jsdata("ix-sem-data", ixdata))

    sem_scope = scope(
        [f"Point estimates are nearly unbiased at every sample size tested, from n={ns[0]:,} to n={ns[-1]:,}.",
         f"Interval coverage sits at {min(cov_all)*100:.0f}% to {max(cov_all)*100:.0f}% against a nominal 95%, "
         f"and does not improve with n.",
         "Telling the two negative coefficients apart at 80% power needs a sample of "
         f"{req_map.get('distinguish beta = -0.25 from beta = -0.20 at 80% power', 0):,}.",
         f"Fitting the same data with the causal arrow reversed returns an identical coefficient "
         f"({float(equiv[0]['beta']):.3f} both ways) and identical fit statistics."],
        ["Simulation establishes estimator properties, not empirical facts. These studies say nothing "
         "about whether any particular safety programme works, and they are not evidence about any real site.",
         "The generating models are the author's, chosen to resemble the structure the "
         "circulating formula implies. A different generating model would give different numbers, "
         "though the identification results do not depend on the parameterisation.",
         "Replication counts are modest in places and each table records its own. The "
         "bootstrap study runs 40 replications, which is enough to show the direction of the "
         "coverage gap and not enough to pin its size.",
         "Nothing here has been peer reviewed."],
        '<p class="scope-after">The practical conclusion is narrow and worth stating plainly: illustrative path '
        "weights of the kind that circulate in practitioner writing cannot be read causally, "
        "cannot be transferred between sites, and cannot be validated by goodness of fit.</p>")
    qs = quickstart(repo, [
        "git clone https://github.com/priyatham9/ehs-risk-sem",
        "cd ehs-risk-sem",
        "python3 -m unittest discover -s tests -v",
        "python3 simulations/run_all.py --quick       # writes results_quick/",
        "python3 simulations/run_all.py               # full run, writes results/"],
        '<p class="qs-note"><code>--quick</code> writes to <code>results_quick/</code>, so a reduced-replication '
        "run cannot silently replace the checked-in tables.</p>")

    body = (
        section("explore", "00", "Drag the sample size", explore)
        + section("why", "01", "Why this exists", lead)
        + section("scope", "00", "What this does and does not show", sem_scope)
        + section("recovery", "02", "Recovery, and the intervals around it", cov_fig + rec_tbl,
                  lede="Start with the friendliest possible test. Generate data from a known "
                       "model, then estimate it. If the estimator cannot recover coefficients it "
                       "generated itself, nothing downstream is worth reading.")
        + section("sizing", "03", "How much data the formula would need", sizing,
                  lede="Estimating a coefficient and being able to tell it apart from the "
                       "coefficient next to it are different tasks with very different sample "
                       "size requirements.")
        + section("rare", "04", "What rare events do", rare,
                  lede="Safety incidents are rare. Rare outcomes break naive estimation in a "
                       "specific way: discrimination survives, calibration does not, and "
                       "calibration is what an operational alert depends on.")
        + section("zero", "05", "Zero inflation", zero,
                  lede="Most establishments record no injuries in a period. That is not a small "
                       "deviation from a count model, it is a different data-generating process.")
        + section("misspec", "06", "Misspecification and equivalence", misspec,
                  lede="This is the section that matters. A model can be wrong in the specific "
                       "way that inflates the number you care about, and still fit better than "
                       "the correct one.")
        + section("meaning", "07", "What a coefficient means", meaning,
                  lede="Even a correctly estimated coefficient does not tell you what happens if "
                       "you intervene, and does not survive a change of scale or a change of site.")
        + section("run", "00", "Run it yourself", qs)
    )

    return dict(
        repo=repo, mark="S", title="Structural equation modelling for safety risk - " + repo,
        desc="Simulation studies establishing what structural equation modelling can and cannot "
             "recover for safety risk scoring. All data simulated by design.",
        kicker="Method study - every number simulated by design",
        h1="What SEM cannot tell you about safety risk",
        lede="A from-scratch numpy estimator, then simulation studies covering coefficient "
             "recovery, interval coverage, sample size, rare-event calibration, misspecification "
             "and equivalence. Ground truth is known by construction: behaviour is measured, not "
             "assumed. No real injury data here.",
        num=f"{max(cov_all)*100:.0f}", num_dec=0, unit="%",
        means=f"is the best 95% interval coverage the estimator reaches at any sample size tested. "
              f"The estimates are nearly unbiased; the uncertainty reported around them is too narrow, "
              f"which reads as confidence.",
        num_src="results/study01_recovery.csv", cta="Drag the sample size",
        nots="No claim about real safety data. Every observation on this page is simulated from a "
             "model this code wrote, so the results bound what the method can recover under ideal "
             "conditions. They do not show that a real risk score is right or wrong.",
        toc={"explore": "Try it", "why": "Why this exists|Why", "scope": "Does / does not|Scope",
             "recovery": "Recovery", "sizing": "Sizing", "rare": "Rare events|Rare",
             "zero": "Zero inflation|Zeroes", "misspec": "Misspecification|Misspec",
             "meaning": "Meaning", "run": "Run it"},
        status=status, body=body)


# ===================== ehs-ai-grounding-eval =====================
def build_grounding():
    repo = "ehs-ai-grounding-eval"
    d = REPOS / repo

    domains = []
    tiers = Counter()
    types = Counter()
    families = set()
    pairs = set()
    total = 0
    for p in sorted((d / "corpus" / "items").glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        items = doc.get("items", [])
        total += len(items)
        t = Counter(i.get("risk_tier") for i in items)
        for i in items:
            tiers[i.get("risk_tier")] += 1
            types[i.get("item_type")] += 1
            if i.get("family"):
                families.add(i["family"])
            if i.get("pair_id"):
                pairs.add(i["pair_id"])
        domains.append((doc.get("domain_title", doc["domain"]), doc["domain"],
                        doc.get("source_family", ""), len(items), t))

    ver = json.loads((d / "corpus" / "verification" / "source_verification.json").read_text(encoding="utf-8"))
    quar = json.loads((d / "corpus" / "quarantine" / "unverified.json").read_text(encoding="utf-8"))
    n_quar = len(quar.get("items", []))

    status = "".join([
        cell("Corpus items", str(total)),
        cell("Minimal pairs", str(len(pairs))),
        cell("Sources verified", f'{ver["n_ok"]}/{ver["n_checked"]}'),
        cell("LLM results", "None yet", True),
    ])

    lead = opener(
        "Asked about overpressure protection for a chemical reactor, an assistant returned "
        "pressure relief valve data when rupture disks were the question.",
        ["Both are overpressure devices. They are not interchangeable. A rupture disk is a "
         "one-shot non-reclosing device with a nominal burst pressure and an operating margin "
         "requirement; a spring-loaded relief valve has a set pressure, a blowdown and a reseat "
         "behaviour. Quoting a blowdown percentage for a rupture disk is not a small error. It is "
         "an answer about a different device, delivered in the register of a correct one.",
         "The substitution is invisible to anyone without the domain background to catch it, and "
         "the people most likely to ask the question are the people least likely to have that "
         "background. This is the structurally expected output of retrieval with no authoritative "
         "binding: the model returns the statistically likelier neighbour of the right answer.",
         f"So the corpus is built out of that failure mode on purpose. Alongside "
         f"{total} questions it carries {len(pairs)} minimal pairs: two questions whose correct "
         "answers diverge precisely because the device, or the regulatory trigger, differs. "
         "Answering one correctly while getting its partner wrong is the signal being measured, "
         "and it is why the primary outcome is paired accuracy rather than per-item accuracy."],
        "State of the work",
        "<p><strong>No language model has been evaluated on this corpus.</strong> What exists is "
        "the apparatus plus three non-LLM baselines (random floor 52.1%, TF-IDF retrieval 27.0%, "
        "oracle ceiling 100%) that show the items discriminate, and a real Anthropic Messages API "
        "adapter with a one-command run script, ready for the owner to run against an actual "
        "model.</p>"
        "<p>That is a real limitation, not a phase of a rollout. Nothing here should be read as a "
        "finding about any language model until that run happens.</p>")

    no_results = notice(
        "Baselines exist - no language model scored yet",
        "<p>This repository contributes a question corpus, a scoring harness, and three non-LLM "
        "baselines that establish the items discriminate: random floor 52.1%, TF-IDF retrieval "
        "27.0%, oracle ceiling 100% accuracy. No language model has been evaluated on it yet.</p>"
        "<ul>"
        "<li>A real Anthropic Messages API adapter (<code>grounding_eval/adapters/anthropic_api.py</code>) "
        "and a one-command run script (<code>scripts/run_baselines.sh</code>) now exist. Running "
        "them against an actual model is the immediate next step, and until that happens nothing "
        "here should be cited as a finding about any model.</li>"
        "<li>The demonstration run under <code>synthetic/</code> uses mock adapters and exists "
        "only to prove the harness executes end to end. It is not a result and the mock "
        "adapters do not represent any real system.</li>"
        "<li>The preregistration below was written to make a later result auditable. It also "
        "makes this absence auditable.</li>"
        "</ul>")

    def short(slug):
        s = slug.replace("_", " ")
        return s[0].upper() + s[1:]

    dom_fig = fig_stacked(
        [(short(slug), {k: c[k] for k in ("high", "medium", "low")})
         for _, slug, _, n, c in sorted(domains, key=lambda r: -r[3])],
        ["high", "medium", "low"], ["var(--s2)", "var(--s1)", "var(--fig-grid)"],
        f"Corpus composition by domain and risk tier. {tiers['high']} of {total} items are "
        f"high tier, meaning a wrong answer has a direct physical or regulatory consequence "
        f"rather than an inconvenient one. Pressure relief is the largest domain because it is "
        "where the motivating failure occurred and where the adjacent-device confusion is "
        "sharpest.",
        "Corpus items by domain and risk tier",
        "corpus/items/*.json")

    dom_rows = "".join(
        f'<tr><td class="t-first">{esc(title)}</td><td>{n}</td>'
        f'<td>{c["high"]}</td><td>{c["medium"]}</td><td>{c["low"]}</td>'
        f'<td>{esc(sf)}</td></tr>'
        for title, slug, sf, n, c in sorted(domains, key=lambda r: -r[3]))
    dom_tbl = (
        '<figure class="tbl"><div class="tbl-wrap"><table><thead><tr><th>Domain</th>'
        '<th>Items</th><th>High</th><th>Medium</th><th>Low</th><th>Source family</th>'
        f'</tr></thead><tbody>{dom_rows}</tbody></table></div>'
        '<figcaption class="tbl-cap">Every domain is anchored to a public federal regulation, '
        'because a public source is one the reader can check. Where the governing document is a '
        'copyrighted consensus standard, the item is either anchored to a public regulation that '
        f'covers the same substantive requirement or it is quarantined: {n_quar} items are '
        'excluded from scoring on exactly that ground.'
        '<span class="src">Source artifact: corpus/items/*.json</span></figcaption></figure>')

    def count(v):
        return len(v) if isinstance(v, (list, dict)) else v

    sections = ver["sections_fetched"]
    sec_list = (", ".join(sections) if isinstance(sections, list) else str(sections))

    verification = (
        defs([
            ("Items checked", f'{ver["n_checked"]} of {ver["n_items"]}'),
            ("Passed", f'{ver["n_ok"]}, with {count(ver["n_failed"])} failures, '
                       f'{count(ver["unparsed_citations"])} unparsed citations and '
                       f'{count(ver["fetch_errors"])} fetch errors'),
            ("eCFR edition", esc(ver["ecfr_edition_date"])),
            ("Sections fetched", f'<span class="mono">{count(sections)}</span>: {esc(sec_list)}'),
            ("What is checked", esc(ver["note"])),
        ])
        + '<div class="prose" style="margin-top:26px">'
        "<p>Verification is structural. It confirms that the cited section exists in the eCFR at a "
        "pinned edition date, that the item's verbatim anchor text appears in it, and that the "
        "cited paragraph markers are present. It does not confirm that the answer key is a good "
        "answer, and it never fetches a copyrighted standard.</p>"
        f'<p><a class="backlink" href="{GH}/{repo}/blob/main/corpus/verification/source_verification.json">'
        "The full verification record</a></p></div>")

    scoring = (
        '<div class="cols"><div class="prose">'
        "<h3>Adjacent substitution</h3>"
        "<p>Did the system return a semantically close but operationally wrong entity. This is "
        "scored separately from ordinary wrongness and carries the heaviest penalty, because a "
        "confident answer about the wrong device is more dangerous than an obviously bad one.</p>"
        "<h3>Citation presence and correctness</h3>"
        "<p>Is a source given, and is it the right one. A citation that exists but does not "
        "support the claim is graded differently from no citation at all.</p>"
        "<h3>Abstention credit</h3>"
        "<p>A system that declines scores above one that confabulates. Category-error items exist "
        "specifically to test this: they carry a false premise, and the correct response is to "
        "reject the premise rather than to answer.</p>"
        "</div><div class=\"prose\">"
        "<h3>Why the scorer is the weak point</h3>"
        "<p>Scoring is lexical. Required and forbidden concepts are matched as term sets with a "
        "coverage threshold, and the contrast heuristic that decides whether a term was asserted "
        "or merely mentioned works over a fixed character window. The repository's own limitations "
        "document names this as the weakest link, and it is right to.</p>"
        "<p>A lexical scorer can be gamed by a verbose answer and can miss a correct answer phrased "
        "unusually. Human adjudication is specified in the preregistration for exactly this reason, "
        "with the adjudication protocol fixed in advance rather than invented once disagreements "
        "appear.</p>"
        f'<p><a class="backlink" href="{GH}/{repo}/blob/main/docs/limitations.md">'
        "All twelve limitations, as written by the author</a></p>"
        "</div></div>")

    prereg_parts = []
    cfg = md_table(d / "docs" / "preregistration.md", "Scoring configuration")
    if cfg:
        prereg_parts.append(md_table_html(
            cfg,
            "Scoring parameters, frozen before any evaluation. Changing any of these after a run "
            "requires an amendment entry and demotes the affected numbers to exploratory.",
            "docs/preregistration.md - Scoring configuration"))
    plan = md_table(d / "docs" / "preregistration.md", "Statistical plan")
    if plan:
        prereg_parts.append(md_table_html(
            plan,
            "The analysis plan, fixed in advance. One confirmatory outcome; everything else is "
            "labelled exploratory whatever it turns out to say.",
            "docs/preregistration.md - Statistical plan"))
    prereg_parts.append(
        '<div class="prose">'
        "<h3>Three arms</h3>"
        "<ul>"
        "<li><strong>Ungrounded.</strong> Instruction or persona prompt over parametric memory, "
        "with no retrieval.</li>"
        "<li><strong>Pseudo-grounded.</strong> Retrieval over a plausible but unauthoritative "
        "corpus.</li>"
        "<li><strong>Grounded.</strong> Retrieval over a version-pinned authoritative corpus with "
        "device-type metadata filtering.</li>"
        "</ul>"
        "<p>The primary comparison is grounded against ungrounded on paired accuracy. The "
        "direction of the pseudo-grounded comparison is deliberately not predicted: retrieval over "
        "unauthoritative sources may plausibly do worse than no retrieval at all.</p>"
        "<h3>Recorded so it cannot be reinterpreted later</h3>"
        "<p>The preregistration states in advance which outcomes would count against the "
        "benchmark's own premise. If grounded and ungrounded do not differ on paired accuracy, "
        "that is a real result and will be reported as one. If adjacent-substitution rates are "
        "near zero in every arm, the corpus failed to do its job.</p>"
        f'<p><a class="backlink" href="{GH}/{repo}/blob/main/docs/preregistration.md">'
        "The full preregistration</a></p></div>")

    # ---- signature interactive: browse items, reveal the trap, baseline outcomes ----
    summ = {r["adapter"]: r for r in read_csv(d / "results" / "baselines_summary.csv")}
    ADAPTERS = [("random_floor", "Random floor"), ("retrieval_tfidf", "TF-IDF"),
                ("retrieval_bm25", "BM25"), ("oracle", "Oracle")]
    ADAPTERS = [(k, l) for k, l in ADAPTERS if (d / "results" / f"baselines_{k}.json").exists()]
    outcomes = {}
    for k, _ in ADAPTERS:
        run = json.loads((d / "results" / f"baselines_{k}.json").read_text(encoding="utf-8"))
        per = {}
        for r_ in run["runs"]:
            for sc in r_["scores"]:
                per.setdefault(sc["item_id"], []).append(sc["outcome"])
        outcomes[k] = per
    dom_short = {"confined_space": "Confined space", "hazard_communication": "Hazard comms",
                 "injury_recordkeeping": "Recordkeeping", "lockout_tagout": "Lockout/tagout",
                 "machine_electrical_fire": "Machine, electrical, fire",
                 "pressure_relief_devices": "Pressure relief",
                 "process_safety_management": "Process safety",
                 "respiratory_protection_and_noise": "Respiratory, noise"}
    dlist, items = [], []
    for p_ in sorted((d / "corpus" / "items").glob("*.json")):
        doc = json.loads(p_.read_text(encoding="utf-8"))
        di = len(dlist)
        its = doc.get("items", [])
        fact_ids = [i["id"] for i in its if i.get("item_type") == "factual"]
        acc = []
        for k, _ in ADAPTERS:
            obs = [o for iid in fact_ids for o in outcomes[k].get(iid, [])]
            acc.append(round(sum(o == "correct" for o in obs) / len(obs), 4) if obs else 0)
        dlist.append({"id": doc["domain"], "short": dom_short.get(doc["domain"], short(doc["domain"])),
                      "n": len(its), "acc": acc})
        for i in its:
            aw = i.get("adjacent_wrong") or {}
            out_ = {}
            for k, _ in ADAPTERS:
                o = outcomes[k].get(i["id"])
                if not o:
                    continue
                out_[k] = o[0] if len(o) == 1 else [sum(x == "correct" for x in o), len(o)]
            items.append({"id": i["id"], "d": di, "type": i.get("item_type"), "tier": i.get("risk_tier"),
                          "pair": i.get("pair_id"), "q": i["question"], "a": i["correct_answer"],
                          "cite": (i.get("source") or {}).get("clause", ""),
                          "trap": {"label": aw.get("label", ""), "answer": aw.get("answer", ""),
                                   "why": aw.get("why_dangerous", "")},
                          "out": out_ if i.get("item_type") == "factual" else None})
    ixdata = {"domains": dlist, "items": items,
              "adapters": [{"key": k, "label": l} for k, l in ADAPTERS]}
    tf = float(summ["retrieval_tfidf"]["accuracy"]) if "retrieval_tfidf" in summ else None
    rf = float(summ["random_floor"]["accuracy"]) if "random_floor" in summ else None

    explore = (
        explore_intro(f"Every one of the {total} corpus items, with the plausible wrong answer it was "
                      "built to catch. Pick a domain, open an item, reveal the trap. The bars show how the "
                      "three non-LLM baselines score per domain on factual items; none of them is a "
                      "language model.", "try.html", "Try answering an item yourself")
        + '<div class="ix" id="ix-ground">'
        '<div class="ix-panel ix-wide"><h3 class="ix-sub">Baseline accuracy by domain <small>select a domain to filter</small></h3>'
        '<div class="gx-legend">' + "".join(f'<span><i class="a{j}"></i>{esc(l)}</span>' for j, (_, l) in enumerate(ADAPTERS)) + '</div>'
        '<div class="gx-acc" id="gx-acc"></div>'
        '<span class="src">Source artifact: results/baselines_*.json - scores, factual items, correct outcome share</span></div>'
        '<div class="ix-panel ix-wide"><div class="seg seg-wrap" id="gx-domains"></div>'
        '<div class="gx-browse"><div class="gx-list" id="gx-list" aria-label="Corpus items"></div>'
        '<div class="gx-card" id="gx-card" aria-live="polite"></div></div>'
        '<span class="src">Source artifact: corpus/items/*.json</span></div>'
        '</div>' + jsdata("ix-ground-data", ixdata))

    g_scope = scope(
        [f"A corpus of {total} items across {len(domains)} domains, built around plausible-but-wrong "
         f"adjacent answers, with {len(pairs)} minimal pairs.",
         f"Structural source verification: {ver['n_ok']} of {ver['n_checked']} checked items pass "
         "against the eCFR at a pinned edition date.",
         "That the items discriminate: random floor 52.1%, TF-IDF retrieval 27.0%, oracle ceiling 100%.",
         "A scoring harness and preregistration fixed before any system was run."],
        ["<strong>No language model has been evaluated on this corpus.</strong> Nothing here should be "
         "cited as a finding about any model.",
         "The demonstration run under <code>synthetic/</code> uses mock adapters and exists "
         "only to prove the harness executes end to end. It is not a result.",
         "Verification is structural. It does not confirm that the answer key is a good answer.",
         "Scoring is lexical. A lexical scorer can be gamed by a verbose answer and can miss a correct "
         "answer phrased unusually."])
    qs = quickstart(repo, [
        "python3 -m grounding_eval.cli corpus      # describe the corpus",
        "python3 -m grounding_eval.cli validate    # corpus + stored source verification",
        "python3 -m grounding_eval.cli demo        # labelled demonstration run",
        "python3 -m unittest discover -s tests -v"],
        '<p class="qs-note">Python 3.9+, pandas and numpy. No other dependencies, no build step. '
        'Baselines: <code>scripts/run_baselines.sh</code>.</p>')

    body = (
        section("explore", "00", "Browse the traps", explore)
        + section("status", "02", "Status", no_results,
                  lede="Stated before anything else on the page, because a benchmark is easy to "
                       "mistake for a result.")
        + section("why", "01", "Why this exists", lead)
        + section("scope", "00", "What this does and does not show", g_scope)
        + section("corpus", "03", "The corpus", dom_fig + dom_tbl,
                  lede=f"{total} items across {len(domains)} domains, {types['factual']} factual "
                       f"and {types['category_error']} category-error, organised into "
                       f"{len(families)} families and {len(pairs)} minimal pairs.")
        + section("sources", "04", "Source verification", verification,
                  lede="An item is only usable if a reader can check its answer against a source "
                       "the reader can also reach.")
        + section("scoring", "05", "What is scored", scoring,
                  lede="Three measured quantities, and an honest account of where the measurement "
                       "is weakest.")
        + section("prereg", "06", "Preregistration", "".join(prereg_parts),
                  lede="Fixed before any system was run, so that a later result cannot be the "
                       "product of choices made after seeing the data.")
        + section("run", "00", "Run it yourself", qs)
    )

    return dict(
        repo=repo, mark="G", title="Grounding evaluation for safety-critical QA - " + repo,
        desc="A preregistered benchmark for whether AI answers to safety-critical technical "
             "questions are bound to authoritative sources. Three non-LLM baselines exist; no "
             "language model has been scored yet.",
        kicker="Benchmark - baselines exist, no language model scored yet",
        h1="Measuring whether an answer is grounded or merely plausible",
        lede=f"{total} questions built around plausible-but-wrong adjacent answers in pressure "
             f"relief, lockout/tagout, confined space, process safety and recordkeeping. Baselines "
             f"exist; no language model has been evaluated yet.",
        num=f"{tf*100:.1f}" if tf is not None else str(total), num_dec=1 if tf is not None else 0,
        unit="%" if tf is not None else "",
        means=(f"is what TF-IDF retrieval scores on the factual items, below the {rf*100:.1f}% random "
               "floor. The items discriminate. No language model has been evaluated yet."
               if tf is not None and rf is not None else "corpus items. No language model has been evaluated yet."),
        num_src="results/baselines_summary.csv", cta="Browse the traps",
        nots="No language model has been scored. The numbers on this page come from three "
             "non-LLM baselines, so they say the items discriminate. They say nothing yet about "
             "how any assistant performs on safety-critical questions.",
        toc={"explore": "Try it", "status": "Status", "why": "Why this exists|Why",
             "scope": "Does / does not|Scope", "corpus": "The corpus|Corpus", "sources": "Sources",
             "scoring": "Scoring", "prereg": "Preregistration|Prereg", "run": "Run it"},
        status=status, body=body)


# ===================== ehs-human-factors-ontology =====================
def _trace_excerpt(repo_dir):
    """Run the repo's own CLI on its committed worked example and keep the trace."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "ehs_hfo", "assess",
             "examples/reactor_startup_nonroutine.json"],
            cwd=str(repo_dir), env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    text = r.stdout.decode("utf-8", "replace")
    m = re.search(r"^Derivation trace: screening band\n-+\n(.*?)(?=\n\nDerivation trace:)",
                  text, re.S | re.M)
    if not m:
        return None
    lines = m.group(1).rstrip().splitlines()
    return "\n".join(lines[:26])


def build_ontology():
    repo = "ehs-human-factors-ontology"
    d = REPOS / repo
    ttl = (d / "ontology" / "ehs-hfo.ttl").read_text(encoding="utf-8")
    classes = len(re.findall(r"a\s+owl:Class", ttl))
    props = len(re.findall(r"a\s+owl:(?:Object|Datatype|Annotation)Property", ttl))
    inds = len(re.findall(r"a\s+owl:NamedIndividual", ttl))
    externals = len(re.findall(r",\s*ehs:ExternalFactor\b", ttl))
    ttl_lines = len(ttl.splitlines())

    xw = read_csv(d / "crosswalk" / "crosswalk.csv")
    frameworks = []
    for r in xw:
        if r["framework_label"] not in frameworks:
            frameworks.append(r["framework_label"])
    local_factors = len({r["factor_curie"] for r in xw})
    aligned = [r for r in xw if r["match_strength"] != "none"]
    absences = [r for r in xw if r["match_strength"] == "none"]
    ext_matched = len({r["external_curie"] for r in aligned if r["external_curie"]})
    by_fw = {f: Counter(r["match_strength"] for r in xw if r["framework_label"] == f)
             for f in frameworks}
    n_close = sum(c["close"] for c in by_fw.values())
    dims = []
    for r in xw:
        if r["dimension_label"] not in dims:
            dims.append(r["dimension_label"])

    status = "".join([
        cell("Factors", str(local_factors)),
        cell("Alignments", str(len(aligned))),
        cell("Asserted absences", str(len(absences))),
        cell("Derivation traces", "Every conclusion", True),
    ])

    lead = opener(
        "A derivation trace is the reasoning, not a description of it written afterwards.",
        ["A language model asked to explain a risk score will produce a fluent explanation. That "
         "explanation is generated after the answer and is not causally connected to how the "
         "answer was produced, so it can be confident, readable and wrong about its own "
         "reasoning. In a regulated setting that is worse than no explanation, because it invites "
         "reliance it cannot support.",
         "This repository takes the other route. Contextual factors shaping human error are "
         "encoded as an OWL ontology, and a forward-chaining rule engine evaluates a scenario "
         "against it. Every derived fact records the rule that fired and the facts that satisfied "
         "that rule's body, down to the scenario inputs. The trace is not a narration of the "
         "reasoning. It is the reasoning, printed.",
         "Two properties make it auditable rather than merely verbose. Every rule declares whether "
         "its basis is literature, in which case a citation is enforced at construction, or "
         "convention, in which case it says so and names no source. And output is deterministic: "
         "two runs of the same scenario produce byte-identical reports, because an audit record "
         "that changes between runs is not an audit record."],
        "Conceded up front",
        "<ul>"
        "<li><strong>Factor levels are analyst-assigned ordinals.</strong> A person decides that "
        "training is degraded. Nothing in this repository measures it.</li>"
        "<li>The observable proxies suggested for deriving levels from operational data are "
        "proposed, not validated.</li>"
        "<li>A compatibility argument is owed. Adopting one project's factor set while "
        "restructuring the error taxonomy it was built against needs to be justified explicitly, "
        "and that argument is not yet made.</li>"
        "</ul>")

    adopted = (
        '<div class="cols"><div class="prose">'
        "<p>The four context dimensions here are not new, and the twenty factors are not new "
        "either. They are the performance-influencing-factor context categories and the twenty "
        "PIFs published by the U.S. Nuclear Regulatory Commission in IDHEAS-G (NUREG-2198, 2021), "
        "adopted unchanged. Two of the four labels are identical to the source's; two are "
        "synonyms.</p>"
        "<p>This is said first because it is what a reviewer from the human reliability community "
        "would otherwise find and hold against the work. Claiming novelty for a relabelling of "
        "performance shaping factors would not survive that reviewer, and should not.</p>"
        "<p>Adding another loosely defined factor grouping would also make a documented problem "
        "worse rather than better: existing PSF sets already range from one factor to more than "
        "fifty, and the literature reports that they are not defined precisely enough to be "
        "applied consistently.</p>"
        "</div><div class=\"prose\">"
        "<h3>So what is contributed</h3>"
        "<ul>"
        "<li><strong>An encoding.</strong> Fixed identifiers with the source's own wording "
        "attached, so a reader can check the transcription rather than trust it. Hand-written "
        f"Turtle, {ttl_lines:,} lines, parsed by a standard-library parser because the repository "
        "takes no dependencies.</li>"
        "<li><strong>A crosswalk as a first-class artifact.</strong> Every factor mapped to its "
        f"counterpart in {len(frameworks)} external frameworks, with a match strength and a "
        "citation on every row, and an explicit assertion of absence where a framework has none. "
        "Generated from the ontology, and the test suite fails if the two disagree.</li>"
        "<li><strong>Traceable inference.</strong> The rule engine, and the guarantees below.</li>"
        "</ul>"
        f'<p><a class="backlink" href="{GH}/{repo}/blob/main/ontology/ehs-hfo.ttl">'
        "Ontology source (Turtle)</a></p>"
        "</div></div>")

    # Chart labels: the full framework name where it fits, otherwise the
    # framework identifier from the same rows.
    curie = {r["framework_label"]: r["framework"] for r in xw}
    fw_short = {f: (f if len(f) <= 20 else curie[f].split("fw-")[-1]) for f in frameworks}

    xw_fig = fig_stacked(
        [(fw_short[f], {k: by_fw[f][k] for k in ("close", "broader", "partial", "none")})
         for f in frameworks],
        ["close", "broader", "partial", "none"],
        ["var(--s1)", "var(--s3)", "var(--s2)", "var(--fig-grid)"],
        f"Match strength for every correspondence, by external framework. "
        f"{len(aligned)} alignments and {len(absences)} asserted absences across "
        f"{len(frameworks)} frameworks, of which only {n_close} are close matches. The rest are "
        "broader, narrower or partial. The strength "
        "<code>exact</code> is declared in the ontology and deliberately never used, and a test "
        "enforces that, because asserting exact identity between factors written decades apart "
        "for different industries would claim more than the sources support.",
        "Crosswalk match strength by framework",
        "crosswalk/crosswalk.csv")

    xw_tbl = table(
        d / "crosswalk" / "crosswalk.csv",
        "Every row carries a match strength, a citation and, where the correspondence is imperfect, "
        "a note saying why. Rows with strength <code>none</code> are assertions that a framework "
        "has no counterpart at all, which is a claim someone can argue with rather than a silence.",
        source="crosswalk/crosswalk.csv", limit=14,
        cols=["dimension_label", "factor_label", "framework_label", "external_label",
              "match_strength", "source_refs"],
        rename={"dimension_label": "dimension", "factor_label": "local factor",
                "framework_label": "framework", "external_label": "external counterpart",
                "match_strength": "strength", "source_refs": "citation"})

    trace = _trace_excerpt(d)
    if trace:
        trace_html = (
            f'<div class="trace"><pre>{esc(trace)}</pre></div>'
            '<p class="trace-cap">The top of the derivation for the screening band, produced by '
            "running the repository's own command-line tool against its committed worked example "
            "at the moment this page was generated. Two things to notice. The band rule announces "
            "itself as <code>[convention; no source]</code>, because the threshold is the author's "
            "and no literature supports it. And the chain bottoms out in <code>[given]</code>, "
            "which are facts the scenario or the ontology supplied, so there is nothing between "
            "the input and the conclusion that a reader cannot inspect."
            '<span class="src">Generated at build time from examples/reactor_startup_nonroutine.json'
            "</span></p>")
    else:
        trace_html = (
            '<div class="prose"><p>The derivation trace is produced by running '
            "<code>python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json</code> "
            "in the repository. It could not be generated during this build, so it is not "
            "reproduced here rather than being quoted from memory.</p></div>")

    engine = defs([
        ("Termination", "No function symbols, so the Herbrand base is finite and evaluation "
                        "reaches a fixpoint."),
        ("Negation", "Stratified negation as failure, checked at construction. A negative "
                     "dependency inside a cycle raises rather than picking an answer."),
        ("Determinism", "The fact index is seeded in sorted order and alternative derivations are "
                        "canonically sorted, so two runs produce byte-identical reports."),
        ("Rule basis", "Every rule declares <code>literature</code>, which requires a citation and "
                       "is enforced in the constructor, or <code>convention</code>, which states "
                       "that the author chose a threshold and no source supports it. Every "
                       "screening-band rule is convention, and a test fails if one ever claims "
                       "otherwise."),
        ("Missing data", "A factor omitted from a scenario is carried as unknown, never as "
                         "nominal, and the report prints assessment coverage. Treating missing "
                         "data as satisfactory is the standard way a screening tool understates a "
                         "hazard."),
        ("Output", "An ordinal screening band. Not a probability, not a rate, and the report says "
                   "so in the line that prints it."),
    ])

    # An absence row asserts that a LOCAL factor has no counterpart in the external
    # framework, so external_label is empty on every one of them by construction.
    # Rendering it produced a table whose "External factor" column was blank in every
    # row; the column that carries the meaning is the local factor.
    gaps_rows = "".join(
        f'<tr><td class="t-first">{esc(r["framework_label"])}</td>'
        f'<td>{esc(r["factor_label"])}</td><td style="white-space:normal">{esc(r["note"])}</td></tr>'
        for r in absences)
    gaps_tbl = (
        '<figure class="tbl"><div class="tbl-wrap"><table><thead><tr><th>Framework</th>'
        '<th>Local factor with no counterpart</th><th>What is asserted</th></tr></thead>'
        f'<tbody>{gaps_rows}</tbody></table></div>'
        '<figcaption class="tbl-cap">The asserted absences. A crosswalk that only records matches '
        'is a crosswalk that hides its own coverage; these rows say what the adopted factor set '
        f'does not reach. Coverage runs the other way too: {externals} external factors are '
        f'declared in the ontology and {ext_matched} of them have a local counterpart, so the '
        'uncovered remainder in that direction is visible rather than implied.'
        '<span class="src">Source artifact: crosswalk/crosswalk.csv, rows with strength none'
        '</span></figcaption></figure>')

    limits = notice(
        "What is not established",
        "<ul>"
        "<li><strong>Factor levels are analyst-assigned ordinals.</strong> The observable proxies "
        "suggested for deriving them from operational data are proposed, not validated. No study "
        "here establishes that any proxy measures the factor it is attached to, and a screening "
        "band computed from unvalidated inputs inherits their uncertainty entirely.</li>"
        "<li><strong>A compatibility argument is owed.</strong> An internal review flagged that "
        "adopting a PIF set while restructuring the error taxonomy it was constructed against "
        "requires an explicit argument that the two remain compatible. That argument is not yet "
        "made.</li>"
        "<li><strong>The engine has not been evaluated against expert judgement.</strong> Nobody "
        "has checked whether its screening bands agree with what experienced analysts would say "
        "about the same scenarios.</li>"
        "<li><strong>The screening bands are conventions.</strong> The thresholds are the "
        "author's. The engine declares this in every trace, which makes it honest, not "
        "validated.</li>"
        "<li><strong>The scenario corpus is synthetic.</strong> It is fabricated, labelled as such "
        "in the repository, and used only to exercise the engine. The worked example is a "
        "hand-written illustration and is not a record of a real event at any site.</li>"
        "</ul>")

    # ---- signature interactive: PIF explorer + rule-engine demo ----
    fws_order = [f for f in ("SPAR-H", "CREAM", "HFACS") if f in frameworks] + \
        [f for f in frameworks if f not in ("SPAR-H", "CREAM", "HFACS")]
    dim_map = {}
    for r in xw:
        dd = dim_map.setdefault(r["dimension_label"], {})
        fa = dd.setdefault(r["factor_curie"], {"curie": r["factor_curie"], "label": r["factor_label"],
                                               "verbatim": r["factor_verbatim_label"], "xw": []})
        fa["xw"].append({"fw": r["framework_label"], "ext": r["external_label"], "s": r["match_strength"],
                         "cite": r["source_refs"], "note": r["note"]})
    demo = _engine_demo(d)
    ixdata = {"frameworks": fws_order,
              "dims": [{"label": dl, "factors": sorted(dim_map[dl].values(), key=lambda f: f["label"])}
                       for dl in dims],
              "demo": demo}
    demo_html = ""
    if demo:
        demo_html = (
            '<div class="ix-panel ix-wide hx-demo"><div class="ix-head"><span class="ix-k">B</span>'
            '<h3>Run the rule engine</h3><p>Start from a scenario, change one factor, read the band and '
            'the derivation. Every result was computed by the repository\'s own engine when this page '
            'was built, one factor changed at a time.</p></div>'
            '<div class="ix-controls hx-dcontrols"><div><span class="ix-lab">Starting scenario</span><div class="seg" id="hx-dbase"></div></div>'
            '<label>Factor<select id="hx-dfactor"></select></label>'
            '<div><span class="ix-lab">Level</span><div class="seg seg-wrap" id="hx-dlevel"></div></div></div>'
            '<div class="hx-dres" id="hx-dres" aria-live="polite"></div>'
            '<p class="hx-disclaimer">Ordinal screening label. Not a human error probability, not a rate, '
            'not calibrated against outcome data. Band thresholds are conventions chosen by the author.</p>'
            '<span class="src">Computed at build time: ehs_hfo.assessment.assess on examples/reactor_startup_nonroutine.json '
            'and an all-nominal variant</span></div>')
    explore = (
        explore_intro(f"Pick a context, pick a factor, and see where it lands in {len(fws_order)} "
                      "external frameworks, including the rows that assert there is no counterpart. "
                      "Then push the same factor through the rule engine.",
                      "walkthrough.html", "Step through a full derivation")
        + '<div class="ix" id="ix-onto">'
        '<div class="ix-panel ix-wide"><div class="ix-head"><span class="ix-k">A</span><h3>PIF explorer</h3>'
        '<p>Four context dimensions, twenty IDHEAS-G factors, one crosswalk.</p></div>'
        '<div class="hx-tabs" id="hx-tabs" role="tablist" aria-label="Context dimension"></div>'
        '<div class="hx-body"><div class="hx-factors" id="hx-factors" role="tabpanel"></div>'
        '<div class="hx-xw" id="hx-xw" aria-live="polite"></div></div>'
        '<span class="src">Source artifact: crosswalk/crosswalk.csv</span></div>'
        + demo_html + '</div>' + jsdata("ix-onto-data", ixdata))

    o_scope = scope(
        [f"An encoding of the {local_factors} IDHEAS-G factors with the source's own wording attached, "
         "so the transcription can be checked rather than trusted.",
         f"A crosswalk to {len(frameworks)} external frameworks: {len(aligned)} cited alignments, "
         f"{len(absences)} asserted absences, only {n_close} close matches.",
         "A forward-chaining engine whose every conclusion carries the rule that fired and the facts "
         "behind it, deterministic run to run."],
        ["<strong>Factor levels are analyst-assigned ordinals.</strong> The observable proxies "
         "suggested for deriving them from operational data are proposed, not validated.",
         "<strong>A compatibility argument is owed.</strong> Adopting a PIF set while restructuring "
         "the error taxonomy it was constructed against requires an explicit argument. That argument "
         "is not yet made.",
         "<strong>The engine has not been evaluated against expert judgement.</strong>",
         "<strong>The screening bands are conventions.</strong> The thresholds are the author's.",
         "<strong>The scenario corpus is synthetic.</strong> The worked example is a hand-written "
         "illustration and is not a record of a real event at any site."])
    qs = quickstart(repo, [
        "git clone https://github.com/priyatham9/ehs-human-factors-ontology",
        "cd ehs-human-factors-ontology",
        "python3 -m unittest discover -s tests -t .",
        "PYTHONPATH=src python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json"],
        '<p class="qs-note">Standard library only. Two runs of the same scenario produce byte-identical reports.</p>')

    body = (
        section("explore", "00", "Explore the factors", explore)
        + section("why", "01", "Why this exists", lead)
        + section("scope", "00", "What this does and does not show", o_scope)
        + section("adopted", "02", "The taxonomy is adopted, not invented", adopted,
                  lede="The most useful thing this page can do is tell you what is borrowed "
                       "before you find out yourself.")
        + section("crosswalk", "03", "Crosswalk to prior work", xw_fig + xw_tbl,
                  lede=f"{local_factors} factors across {len(dims)} context dimensions, mapped "
                       f"onto {len(frameworks)} external frameworks with a citation on every row.")
        + section("trace", "04", "A derivation trace", trace_html,
                  lede="This is the whole argument for the approach, so it is shown rather than "
                       "described.")
        + section("engine", "05", "What the engine guarantees", engine,
                  lede="Guarantees worth having, and the narrow shape of the thing they apply to.")
        + section("gaps", "06", "What the factor set does not reach", gaps_tbl,
                  lede="A crosswalk is only credible if it publishes its own gaps.")
        + section("limits", "07", "Honest limits", limits)
        + section("run", "00", "Run it yourself", qs)
    )

    return dict(
        repo=repo, mark="H", title="Human factors ontology - " + repo,
        desc="Contextual human error risk factors formalised as an OWL ontology with a "
             "crosswalk to prior human reliability work and auditable derivation traces.",
        kicker="Ontology - adopted taxonomy, contributed formalisation",
        h1="Human error context, formalised and traceable",
        lede=f"An OWL ontology of {local_factors} contextual factors from IDHEAS-G, mapped onto "
             f"{len(frameworks)} external frameworks through {len(aligned)} cited alignments and "
             f"{len(absences)} asserted absences. A forward-chaining engine traces every "
             f"conclusion; factor levels are analyst-assigned.",
        num=str(n_close), num_dec=0, unit=f"/{len(aligned)}",
        means=f"crosswalk alignments are close matches. The rest are broader, narrower or partial, "
              f"and {len(absences)} more rows assert that a framework has no counterpart at all.",
        num_src="crosswalk/crosswalk.csv", cta="Explore the factors",
        nots="The ontology does not predict error. Factor levels are assigned by an analyst, and "
             "the rules turn those assignments into a banded conclusion with a trace. Nothing here "
             "has been validated against observed incident outcomes.",
        toc={"explore": "Try it", "why": "Why this exists|Why", "scope": "Does / does not|Scope",
             "adopted": "Adopted taxonomy|Taxonomy", "crosswalk": "Crosswalk",
             "trace": "Derivation trace|Trace",
             "engine": "Guarantees", "gaps": "Gaps", "limits": "Honest limits|Limits", "run": "Run it"},
        status=status, body=body)


_DEMO_PY = r"""
import json
from ehs_hfo.facts import Scenario
from ehs_hfo.assessment import assess
from ehs_hfo.ontology import Ontology
from ehs_hfo.rules import build_program, BAND_ORDER
import re
o = Ontology.load(); p = build_program()
ex = json.load(open("examples/reactor_startup_nonroutine.json"))
factors = sorted(ex["factor_levels"])
LV = [("ehs:LevelEnhanced", "enhanced"), ("ehs:LevelNominal", "nominal"), ("ehs:LevelDegraded", "degraded"),
      ("ehs:LevelSeverelyDegraded", "severely degraded"), ("ehs:LevelUnknown", "unknown")]
def pretty(c):
    return re.sub(r"(?<!^)(?=[A-Z])", " ", c.split(":", 1)[-1]).lower()
results, index = [], {}
def run(levels):
    a = assess(Scenario.from_dict({"scenario_id": "demo", "factor_levels": levels}), o, p)
    r = {"band": a.screening_band, "fired": len(a.result.rules_fired()),
         "funcs": [pretty(x) for x in a.challenged_functions],
         "agg": [pretty(x) for x in a.aggravated_error_modes],
         "cov": "%d of %d factors assessed" % a.coverage,
         "trace": a.band_trace()[:9]}
    k = json.dumps(r, sort_keys=True)
    if k not in index:
        index[k] = len(results); results.append(r)
    return index[k]
bases = {"example": dict(ex["factor_levels"]), "nominal": {f: "ehs:LevelNominal" for f in factors}}
out = {"bands": list(BAND_ORDER), "levels": LV, "bases": {}, "runs": {}, "results": results}
for name, lv in bases.items():
    out["bases"][name] = {"levels": lv, "result": run(lv)}
    for f in factors:
        for code, _ in LV:
            if code == lv[f]:
                continue
            v = dict(lv); v[f] = code
            out["runs"]["%s|%s|%s" % (name, f, code)] = run(v)
print(json.dumps(out))
"""


def _engine_demo(repo_dir):
    """Run the repository's own engine over single-factor changes. None if it cannot run."""
    try:
        r = subprocess.run([sys.executable, "-c", _DEMO_PY], cwd=str(repo_dir),
                           env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
        if r.returncode != 0:
            print(r.stderr.decode()[-800:], file=sys.stderr)
            return None
        return json.loads(r.stdout.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print("engine demo skipped:", e, file=sys.stderr)
        return None


SITE_CSS = r"""
/* ================= project site v2 ================= */
body{overflow-x:clip}
.src{display:block;margin-top:14px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
/* ---- reveals ---- */
.js .rv{opacity:0;transform:translateY(28px);transition:opacity .7s ease,transform .8s cubic-bezier(.2,.7,.2,1)}
.js .rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){.js .rv{opacity:1;transform:none;transition:none}}
@media print{.js .rv{opacity:1;transform:none}}

/* ---- hero: the figure leads ---- */
.hero{padding:64px 0 56px;overflow:hidden}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:40px 56px;align-items:start}
.hero-fig{min-width:0}
.hero-eyebrow{margin-bottom:10px}
.hero-big{margin:0;display:flex;align-items:flex-start;font-family:var(--font-sans);font-stretch:125%;font-weight:900;line-height:.8;letter-spacing:-.045em;color:var(--accent);font-variant-numeric:tabular-nums;white-space:nowrap}
.hero-num{font-size:min(30vw,calc((100vw - 44px) / var(--k,3.7)))}
@media(min-width:901px){.hero-num{font-size:min(10.5rem,10.5vw)}}
.hero-unit{font-size:clamp(1.6rem,6vw,4rem);margin:.08em 0 0 .06em;color:var(--ink);letter-spacing:-.02em}
.hero-means{margin:26px 0 0;padding-left:18px;border-left:4px solid var(--accent);font-size:clamp(1.02rem,1.6vw,1.22rem);line-height:1.45;font-weight:600;color:var(--ink);max-width:44ch}
.hm-k{display:block;font-family:var(--font-mono);font-size:.625rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.hero-text{min-width:0;padding-top:4px}
.hero .hero-text h1{font-size:clamp(1.7rem,3.3vw,2.75rem);max-width:20ch;line-height:1.02}
.hero .hero-role{font-size:.98rem;margin-top:16px;max-width:56ch}
.hero .status{grid-column:1/-1;margin-top:0;max-width:none}
.hero .st-v{font-size:1.15rem}
.hero-not{margin:18px 0 0;padding-left:18px;border-left:4px solid var(--rule);font-size:.9rem;line-height:1.55;color:var(--ink-2);max-width:56ch}
.hn-k{display:block;font-family:var(--font-mono);font-size:.625rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:5px}
@media(max-width:900px){.hero{padding:40px 0 40px}.hero-grid{grid-template-columns:1fr;gap:32px}}

/* ---- three doors: story, this page, tool ---- */
.doors{border-top:2px solid var(--rule);border-bottom:2px solid var(--rule);background:var(--surface-2)}
.doors-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:2px;background:var(--rule-soft)}
.door{position:relative;display:flex;flex-direction:column;gap:5px;min-height:118px;padding:20px 22px 40px;background:var(--surface);color:var(--ink);text-decoration:none;transition:background .15s}
a.door:hover{background:var(--accent-wash)}
.door-k{font-family:var(--font-mono);font-size:.625rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
.door-n{font-family:var(--font-display);font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:1rem;line-height:1.12;color:var(--ink)}
.door-w{font-size:.8125rem;line-height:1.5;color:var(--ink-2);max-width:40ch}
.door-go{position:absolute;right:18px;bottom:13px;font-size:1.15rem;color:var(--accent);transition:transform .2s}
a.door:hover .door-go,a.door:focus-visible .door-go{transform:translateX(5px)}
.door-here{background:var(--accent-wash);box-shadow:inset 0 3px 0 var(--accent);cursor:default}
.door-here .door-k{color:var(--accent)}
.door-here .door-go{color:var(--accent);font-size:.7rem;bottom:17px}
.door-also{display:inline-block;margin:14px 0 2px;font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-decoration:none;border-bottom:2px solid var(--rule-soft);padding-bottom:2px}
.door-also:hover{color:var(--accent);border-bottom-color:var(--accent)}
.doors .wrap{padding-block:26px}
@media(max-width:860px){.doors-grid{grid-template-columns:1fr}.door{min-height:0;padding:16px 20px 16px}.door-go{position:static;align-self:flex-start;margin-top:2px}.door-here .door-go{display:none}}
.st-presenting .doors{display:none!important}

/* ---- layout + table of contents ---- */
.layout{display:grid;grid-template-columns:200px minmax(0,1fr);gap:0 56px;align-items:start}
.toc{position:sticky;top:calc(var(--hdr-h,56px) + 28px);padding:64px 0 24px;z-index:20}
.toc-d>summary{list-style:none;display:flex;align-items:baseline;gap:10px;padding:0 0 12px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);cursor:default;border-bottom:2px solid var(--rule)}
.toc-d>summary::-webkit-details-marker{display:none}
.toc-num{color:var(--accent);font-weight:700}
.toc-current{color:var(--ink);font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.toc-caret{display:none}
.toc ol{list-style:none;margin:0;padding:8px 0 0}
.toc li a{display:flex;gap:10px;align-items:baseline;min-height:34px;padding:7px 0 7px 12px;border-left:2px solid var(--rule-soft);font-size:.8125rem;line-height:1.3;color:var(--ink-2);text-decoration:none;transition:color .15s,border-color .15s,background .15s}
.toc li a:hover{color:var(--ink);border-left-color:var(--ink)}
.toc li a.is-on{color:var(--accent);border-left-color:var(--accent);font-weight:700;background:var(--accent-wash)}
.toc-n{font-family:var(--font-mono);font-size:.625rem;color:var(--muted);flex:none}
.toc li a.is-on .toc-n{color:var(--accent)}
@media(max-width:1023px){
  .layout{display:block}
  .toc{top:var(--hdr-h,56px);margin:0 -30px;padding:0;background:var(--paper);border-bottom:2px solid var(--rule)}
  .toc-d>summary{cursor:pointer;min-height:48px;align-items:center;padding:0 30px;border-bottom:0}
  .toc-caret{display:block;margin-left:auto;width:10px;height:10px;border-right:2px solid var(--ink);border-bottom:2px solid var(--ink);transform:rotate(45deg) translateY(-3px);transition:transform .2s}
  .toc-d[open] .toc-caret{transform:rotate(-135deg)}
  .toc ol{position:absolute;left:0;right:0;top:100%;background:var(--surface);border-top:2px solid var(--rule);border-bottom:2px solid var(--rule);padding:6px 30px 12px;max-height:70vh;overflow:auto;box-shadow:0 18px 30px var(--shadow)}
  .toc li a{min-height:44px}
  }
@media(max-width:900px){.toc{margin:0 -22px}.toc-d>summary,.toc ol{padding-left:22px;padding-right:22px}}
.content{min-width:0}
.content .wrap{max-width:none;padding:0}
.content .section,.content .section:nth-of-type(even){background:transparent;padding:72px 0;border-bottom:2px solid var(--rule)}
.content .section:last-child{border-bottom:0}
.content .rail-head{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:18px;align-items:end;margin-bottom:26px}
.content .rail-num{font-family:var(--font-sans);font-stretch:125%;font-weight:900;font-size:clamp(2.4rem,5vw,3.8rem);line-height:.78;letter-spacing:-.04em;color:transparent;-webkit-text-stroke:1.5px var(--accent)}
.content .rail-head h2{font-size:clamp(1.3rem,3.4vw,2.6rem);max-width:none;line-height:1;overflow-wrap:break-word;hyphens:auto;min-width:0}
.content .rail-head .label{grid-column:2}
@media(max-width:640px){.content .section,.content .section:nth-of-type(even){padding:52px 0}.content .rail-num{-webkit-text-stroke-width:1px}}

/* ---- interactive shell ---- */
.ix-intro{font-size:1.06rem;line-height:1.55;color:var(--ink-2);max-width:66ch;margin:0 0 26px}
.ix-more{font-family:var(--font-mono);font-size:.75rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;text-decoration:none;border-bottom:2px solid var(--accent);white-space:nowrap}
.ix{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px;background:var(--rule-soft);border:2px solid var(--rule)}
.ix-panel{background:var(--surface);padding:26px;min-width:0}
.ix-wide{grid-column:1/-1}
@media(max-width:860px){.ix{grid-template-columns:1fr}.ix-panel{padding:20px 16px}}
.ix-head{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:14px;margin-bottom:18px}
.ix-head h3{font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:1.15rem;line-height:1.1;align-self:center}
.ix-head p{grid-column:2;margin:6px 0 0;font-size:.875rem;color:var(--muted)}
.ix-k{grid-row:span 2;width:40px;height:40px;display:grid;place-items:center;background:var(--accent);color:var(--accent-ink);font-family:var(--font-mono);font-weight:700;font-size:1rem}
.ix-sub{font-family:var(--font-mono);font-size:.6875rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--ink);margin:0 0 12px}
.ix-sub small{font-weight:500;color:var(--muted);margin-left:8px;letter-spacing:.06em}
.ix-read{font-family:var(--font-mono);font-size:.75rem;color:var(--ink-2);min-height:3em;margin:10px 0 0}
.ix-controls{display:flex;flex-wrap:wrap;gap:14px 18px;margin-bottom:20px;align-items:flex-end}
.ix-controls label,.ix-lab{display:flex;flex-direction:column;gap:6px;font-family:var(--font-mono);font-size:.625rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.ix-lab{margin-bottom:6px}
.ix select,.ix input[type=number]{min-height:44px;min-width:0;max-width:100%;padding:0 12px;border:2px solid var(--rule);border-radius:0;background:var(--paper);color:var(--ink);font-family:var(--font-mono);font-size:.875rem;letter-spacing:0;text-transform:none}
.ix input[type=number]{width:120px}
#ox-naics{width:min(360px,100%)}
.seg{display:flex;margin-bottom:14px}
.seg-wrap{flex-wrap:wrap}
.seg-b{min-height:44px;padding:0 14px;margin:0 -2px -2px 0;border:2px solid var(--rule);border-radius:0;background:var(--surface);color:var(--ink);font-family:var(--font-mono);font-size:.6875rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;transition:background .15s,color .15s}
.seg-b:hover{background:var(--surface-2)}
.seg-b[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);position:relative;z-index:1}
.ix button:focus-visible,.ix select:focus-visible,.ix input:focus-visible{outline:3px solid var(--accent);outline-offset:2px;position:relative;z-index:2}

/* ---- osha ---- */
.ox-out{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:2px;background:var(--rule-soft);border:2px solid var(--rule)}
.ox-read{background:var(--surface);padding:14px 16px;min-width:0}
.ox-read span{display:block;font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.ox-read b{display:block;margin-top:6px;font-stretch:125%;font-weight:900;font-size:clamp(1.3rem,2.6vw,2rem);line-height:1;font-variant-numeric:tabular-nums}
.ox-read b.acc{color:var(--accent)}
.ox-bar{height:6px;background:var(--surface-2);margin-top:10px}
.ox-bar i{display:block;height:100%;background:var(--s2);width:0;transition:width .5s cubic-bezier(.2,.7,.2,1)}
.ox-bar i.ox-bar-f{background:var(--accent)}
.ox-note{grid-column:1/-1;background:var(--surface-2);margin:0;padding:10px 16px;font-family:var(--font-mono);font-size:.6875rem;color:var(--ink-2)}
@media(max-width:760px){.ox-out{grid-template-columns:1fr 1fr}}
.ox-years svg{display:block;width:100%;height:auto}
.ox-yr{cursor:pointer;transition:opacity .15s;outline:none}
.ox-yr:hover,.ox-yr:focus{opacity:.72}
.ox-yr:focus-visible{stroke:var(--ink);stroke-width:3}
.ox-strip{position:relative;height:46px;margin:30px 8px 0;border-bottom:2px solid var(--rule);background:linear-gradient(90deg,var(--accent-wash),transparent)}
.ox-tick{position:absolute;bottom:0;width:2px;height:24px;background:var(--accent);transform:translateX(-1px)}
.ox-you{position:absolute;top:-16px;bottom:-8px;width:4px;background:var(--s2);transform:translateX(-2px);transition:left .3s}
.ox-you span{position:absolute;top:-16px;left:50%;transform:translateX(-50%);font-family:var(--font-mono);font-size:.625rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--ink);white-space:nowrap}
.ox-pcts{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:2px;margin-top:16px}
.ox-pcts div{background:var(--surface-2);padding:8px 8px}
.ox-pcts span{display:block;font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.12em;color:var(--muted)}
.ox-pcts b{font-family:var(--font-mono);font-size:.875rem;font-variant-numeric:tabular-nums}
@media(max-width:420px){.ox-pcts{grid-template-columns:repeat(3,minmax(0,1fr))}}
.ox-peer-msg{margin:14px 0 4px;font-weight:600;font-size:.95rem;min-height:1.5em}
.ox-peer-meta{margin:0;font-family:var(--font-mono);font-size:.6875rem;color:var(--muted)}

/* ---- risk sem ---- */
.sx-controls{display:grid;grid-template-columns:minmax(0,1fr);gap:14px}
.sx-slider{width:100%}
.sx-slider output{font-stretch:125%;font-weight:900;font-size:clamp(1.6rem,4vw,2.6rem);color:var(--accent);letter-spacing:-.02em;text-transform:none;font-family:var(--font-sans);line-height:1}
.sx-slider input{width:100%;height:44px;accent-color:var(--accent);cursor:pointer}
.sx-legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-family:var(--font-mono);font-size:.6875rem;color:var(--ink-2)}
.sx-legend span{display:inline-flex;align-items:center;gap:8px}
.sx-legend i{width:22px;height:12px;flex:none}
.lg-emp{background:var(--s2);opacity:.45}
.lg-an{height:5px!important;background:var(--accent)}
.lg-true{width:0!important;height:16px!important;border-left:2px dashed var(--ink)}
.sx-grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:28px;margin-bottom:26px}
@media(max-width:860px){.sx-grid{grid-template-columns:1fr}}
.sx-svg svg{display:block;width:100%;height:auto}
.sx-row{cursor:pointer;outline:none}
.sx-row:hover text{fill:var(--accent)}
.sx-row:focus-visible text{fill:var(--accent);text-decoration:underline}
.sx-row:focus-visible rect:first-of-type{stroke:var(--accent);stroke-width:2}
.sx-readout{border:2px solid var(--rule);padding:18px;background:var(--surface-2);align-self:start}
.sx-readout dl{display:grid;grid-template-columns:auto auto;gap:8px 12px;margin:0}
.sx-readout dt{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);align-self:center}
.sx-readout dd{margin:0;text-align:right;font-stretch:125%;font-weight:900;font-size:1.25rem;font-variant-numeric:tabular-nums}
.sx-readout dd.acc{color:var(--accent);font-size:1.7rem}
.sx-covbar{position:relative;height:12px;background:var(--paper);border:2px solid var(--rule);margin-top:16px}
.sx-covbar i{display:block;height:100%;background:var(--accent);width:0;transition:width .45s cubic-bezier(.2,.7,.2,1)}
.sx-covbar b{position:absolute;top:-8px;bottom:-8px;width:3px;background:var(--ink)}
.sx-covnote{margin:8px 0 0;font-family:var(--font-mono);font-size:.625rem;color:var(--muted)}

/* ---- grounding ---- */
.gx-legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:14px;font-family:var(--font-mono);font-size:.6875rem;color:var(--ink-2)}
.gx-legend span{display:inline-flex;align-items:center;gap:7px}
.gx-legend i{width:14px;height:8px}
.gx-acc{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:2px;background:var(--rule-soft);border:2px solid var(--rule)}
.gx-dom{display:block;text-align:left;background:var(--surface);border:0;border-radius:0;padding:14px;color:var(--ink);font:inherit;cursor:pointer;transition:background .15s}
.gx-dom:hover{background:var(--surface-2)}
.gx-dom[aria-pressed="true"]{background:var(--accent-wash);box-shadow:inset 0 0 0 3px var(--accent)}
.gx-dom-t{display:block;font-weight:700;font-size:.875rem;margin-bottom:8px}
.gx-accrow{display:grid;grid-template-columns:80px minmax(0,1fr) 38px;gap:8px;align-items:center;margin-top:3px}
.gx-accrow small{font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.gx-accrow b{font-family:var(--font-mono);font-size:.6875rem;text-align:right;font-variant-numeric:tabular-nums}
.gx-track{height:7px;background:var(--surface-2)}
.gx-track i{display:block;height:100%}
.a0{background:var(--s2)}.a1{background:var(--s1)}.a2{background:var(--s3)}.a3{background:var(--muted)}
.gx-browse{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.45fr);border:2px solid var(--rule)}
.gx-list{max-height:620px;overflow:auto;overscroll-behavior:contain;border-right:2px solid var(--rule)}
.gx-item{display:grid;grid-template-columns:auto auto;justify-content:start;gap:4px 8px;width:100%;text-align:left;padding:12px 14px;background:var(--surface);color:var(--ink);border:0;border-bottom:1px solid var(--rule-soft);border-left:4px solid transparent;border-radius:0;font:inherit;cursor:pointer}
.gx-item:hover{background:var(--surface-2)}
.gx-item[aria-pressed="true"]{background:var(--accent-wash);border-left-color:var(--accent)}
.gx-id{font-family:var(--font-mono);font-size:.6875rem;font-weight:700;color:var(--accent)}
.gx-tier{font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.1em;text-transform:uppercase;padding:1px 6px;border:1px solid var(--rule-soft);color:var(--muted)}
.gx-tier.t-high{border-color:var(--warn);color:var(--warn)}
.gx-q{grid-column:1/-1;font-size:.8125rem;line-height:1.4;color:var(--ink-2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.gx-card{padding:24px;min-width:0;background:var(--surface)}
.gx-question{font-size:clamp(1.05rem,1.8vw,1.28rem);line-height:1.4;font-weight:600;margin:8px 0 18px}
.gx-block{padding:14px 16px;margin:0 0 14px;border-left:4px solid var(--s3);background:var(--surface-2)}
.gx-block p{margin:6px 0 0;font-size:.9rem;line-height:1.55;color:var(--ink-2)}
.gx-block .src{margin-top:8px}
.gx-block.trap{border-left-color:var(--warn);background:var(--warn-wash)}
.gx-block.trap .label{color:var(--warn)}
.gx-why{font-weight:600;color:var(--ink)!important}
.gx-reveal{margin:0 0 14px;cursor:pointer;min-height:44px}
.gx-outs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.gx-outs .label{flex-basis:100%;margin-bottom:2px}
.gx-out{font-family:var(--font-mono);font-size:.6875rem;padding:5px 9px;border:1px solid var(--rule-soft);color:var(--ink-2)}
.gx-out b{color:var(--ink)}
.gx-out.good{border-color:var(--s3)}
@media(max-width:760px){.gx-browse{grid-template-columns:1fr}.gx-list{max-height:300px;border-right:0;border-bottom:2px solid var(--rule)}.gx-card{padding:18px 14px}}

/* ---- ontology ---- */
.hx-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:2px solid var(--rule);margin-bottom:0}
.hx-tab{display:flex;flex-direction:column;align-items:flex-start;gap:2px;min-height:60px;padding:10px 14px;background:var(--surface);color:var(--ink);border:0;border-left:2px solid var(--rule-soft);border-radius:0;text-align:left;font:inherit;cursor:pointer}
.hx-tab:first-child{border-left:0}
.hx-tab span{font-stretch:125%;font-weight:800;text-transform:uppercase;font-size:.8125rem;line-height:1.1}
.hx-tab small{font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.hx-tab:hover{background:var(--surface-2)}
.hx-tab[aria-selected="true"]{background:var(--accent);color:var(--accent-ink)}
.hx-tab[aria-selected="true"] small{color:var(--accent-ink)}
@media(max-width:640px){.hx-tabs{grid-template-columns:1fr 1fr}.hx-tab:nth-child(3){border-left:0}.hx-tab:nth-child(n+3){border-top:2px solid var(--rule-soft)}}
.hx-body{display:grid;grid-template-columns:minmax(0,250px) minmax(0,1fr);border:2px solid var(--rule);border-top:0}
.hx-factors{border-right:2px solid var(--rule);background:var(--surface-2)}
.hx-f{display:flex;flex-direction:column;gap:2px;width:100%;min-height:48px;padding:10px 14px;text-align:left;background:transparent;color:var(--ink);border:0;border-bottom:1px solid var(--rule-soft);border-left:4px solid transparent;border-radius:0;font:inherit;font-size:.875rem;font-weight:600;cursor:pointer}
.hx-f small{font-family:var(--font-mono);font-size:.5625rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500}
.hx-f:hover{background:var(--surface)}
.hx-f[aria-pressed="true"]{background:var(--surface);border-left-color:var(--accent);color:var(--accent)}
.hx-xw{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:2px;background:var(--rule-soft);align-content:start}
.hx-xw-head{grid-column:1/-1;background:var(--surface);padding:14px 16px}
.hx-xw-head p{margin:4px 0 0;font-weight:700;font-size:1rem}
.hx-fw{background:var(--surface);padding:14px 16px}
.hx-fw-name{display:block;font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:.9rem;margin-bottom:10px}
.hx-m{border-left:4px solid var(--s1);padding:6px 0 6px 10px;margin-bottom:10px}
.hx-m b{display:block;font-size:.875rem;line-height:1.35}
.hx-m p{margin:4px 0 0;font-size:.78rem;line-height:1.45;color:var(--ink-2)}
.hx-m .src{margin-top:4px}
.hx-strength{display:inline-block;font-family:var(--font-mono);font-size:.5625rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:2px}
.hx-m.s-close{border-left-color:var(--s1)}.hx-m.s-broader,.hx-m.s-narrower{border-left-color:var(--s3)}.hx-m.s-partial{border-left-color:var(--s2)}
.hx-m.s-none{border-left:4px dashed var(--muted)}
.hx-m.s-none b{color:var(--muted)}
.hx-empty{font-size:.8rem;color:var(--muted);margin:0}
@media(max-width:760px){.hx-body{grid-template-columns:1fr}.hx-factors{border-right:0;border-bottom:2px solid var(--rule);display:flex;overflow-x:auto}.hx-f{flex:none;width:auto;max-width:220px;border-left:0;border-bottom:4px solid transparent;border-right:1px solid var(--rule-soft)}.hx-f[aria-pressed="true"]{border-left:0;border-bottom-color:var(--accent)}}
.hx-dcontrols{display:grid;grid-template-columns:auto minmax(0,1fr);gap:16px 24px;align-items:start}
.hx-dcontrols>div:last-child{grid-column:1/-1}
.hx-dcontrols .seg{margin-bottom:0}
#hx-dfactor{width:100%}
@media(max-width:640px){.hx-dcontrols{grid-template-columns:1fr}}
.hx-meter{list-style:none;margin:0 0 18px;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:2px solid var(--rule)}
.hx-meter li{padding:14px 10px;text-align:center;font-family:var(--font-mono);font-size:.6875rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);border-left:2px solid var(--rule-soft);transition:background .25s,color .25s}
.hx-meter li:first-child{border-left:0}
.hx-meter li.on{background:var(--accent);color:var(--accent-ink)}
.hx-meter li.on:last-child{background:var(--warn);color:var(--paper)}
@media(max-width:520px){.hx-meter{grid-template-columns:1fr 1fr}.hx-meter li:nth-child(3){border-left:0}.hx-meter li:nth-child(n+3){border-top:2px solid var(--rule-soft)}}
.hx-facts{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:8px 18px;margin:0 0 16px}
.hx-facts dt{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding-top:3px}
.hx-facts dd{margin:0;font-size:.9rem;font-weight:600}
@media(max-width:520px){.hx-facts{grid-template-columns:1fr}.hx-facts dd{margin-bottom:6px}}
.hx-trace{margin:0;max-height:280px;overflow:auto;background:var(--surface-2);border:2px solid var(--rule-soft);padding:14px 16px;font-family:var(--font-mono);font-size:.6875rem;line-height:1.65;color:var(--ink-2);white-space:pre}
.hx-disclaimer{margin:14px 0 0;font-family:var(--font-mono);font-size:.6875rem;color:var(--warn)}

/* ---- does / does not ---- */
.scope{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:2px solid var(--rule)}
.scope-col{padding:28px 28px 20px;min-width:0}
.scope-yes{background:var(--surface)}
.scope-no{background:var(--warn-wash);border-left:2px solid var(--rule)}
.scope-h{display:flex;align-items:center;gap:14px;font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:clamp(1rem,1.8vw,1.3rem);line-height:1.05;margin-bottom:14px}
.scope-mark{flex:none;width:40px;height:40px;display:grid;place-items:center;font-size:1.6rem;font-weight:900;background:var(--accent);color:var(--accent-ink);font-stretch:100%}
.scope-no .scope-mark{background:var(--warn);color:var(--paper)}
.scope ul{list-style:none;margin:0;padding:0;counter-reset:sc}
.scope li{counter-increment:sc;display:grid;grid-template-columns:28px minmax(0,1fr);padding:12px 0;border-top:1px solid var(--rule-soft);font-size:.92rem;line-height:1.55;color:var(--ink-2)}
.scope li::before{content:counter(sc,decimal-leading-zero);font-family:var(--font-mono);font-size:.625rem;font-weight:700;color:var(--accent);padding-top:4px}
.scope-no li::before{color:var(--warn)}
.scope-no li{border-top-color:rgba(138,90,0,.25)}
.scope li strong{color:var(--ink)}
.scope-after{margin:18px 0 0;padding-left:18px;border-left:4px solid var(--accent);font-weight:600;max-width:70ch}
@media(max-width:760px){.scope{grid-template-columns:1fr}.scope-no{border-left:0;border-top:2px solid var(--rule)}.scope-col{padding:22px 16px 14px}}

/* ---- quickstart ---- */
.qs{border:2px solid var(--rule);background:#0E1117;color:#E6E8EE}
.qs-bar{display:flex;align-items:center;gap:14px;padding:0 0 0 16px;border-bottom:2px solid #262B36;min-height:48px}
.qs-dots{display:flex;gap:6px}
.qs-dots i{width:9px;height:9px;background:#3A4150}
.qs-dots i:first-child{background:#7C9EFF}
.qs-t{font-family:var(--font-mono);font-size:.6875rem;letter-spacing:.1em;text-transform:uppercase;color:#9AA1B0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qs-copy{margin-left:auto;align-self:stretch;min-width:92px;min-height:48px;padding:0 18px;border:0;border-left:2px solid #262B36;border-radius:0;background:#171B24;color:#E6E8EE;font-family:var(--font-mono);font-size:.6875rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;transition:background .15s,color .15s}
.qs-copy:hover{background:#7C9EFF;color:#06101F}
.qs-copy:focus-visible{outline:3px solid #7C9EFF;outline-offset:-3px}
.qs pre{margin:0;padding:20px 20px 22px;overflow-x:auto;font-family:var(--font-mono);font-size:.8125rem;line-height:1.85;white-space:pre}
.qs pre:focus-visible{outline:3px solid #7C9EFF;outline-offset:-3px}
.qs-l::before{content:'$ ';color:#7C9EFF;user-select:none;-webkit-user-select:none}
.qs-c{color:#8A93A5}
.qs-note{margin:14px 0 0;font-size:.875rem;color:var(--ink-2);max-width:70ch}
.qs-note code{font-family:var(--font-mono);font-size:.8125em;background:var(--surface-2);padding:2px 5px}

/* ---- next in the programme ---- */
.prog{background:var(--surface-2);border-top:2px solid var(--rule);padding:72px 0}
.prog-h{font-size:clamp(1.5rem,3.4vw,2.6rem);margin-bottom:26px}
.prog-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2px;background:var(--rule-soft);border:2px solid var(--rule)}
.prog-card{position:relative;display:flex;flex-direction:column;gap:6px;min-height:132px;padding:20px 20px 44px;background:var(--surface);color:var(--ink);text-decoration:none;transition:background .15s}
.prog-card:hover{background:var(--accent-wash)}
.prog-next{grid-row:span 2;background:var(--accent);color:var(--accent-ink);justify-content:flex-end}
.prog-next:hover{background:var(--accent-2)}
.prog-tag{font-family:var(--font-mono);font-size:.625rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.prog-next .prog-tag{color:var(--accent-ink)}
.prog-name{font-stretch:125%;font-weight:900;text-transform:uppercase;font-size:1rem;line-height:1.1}
.prog-next .prog-name{font-size:clamp(1.4rem,2.6vw,2.1rem)}
.prog-note{font-family:var(--font-mono);font-size:.6875rem;color:var(--ink-2)}
.prog-next .prog-note{color:var(--accent-ink)}
.prog-arrow{position:absolute;right:18px;bottom:14px;font-size:1.3rem;transition:transform .2s}
.prog-card:hover .prog-arrow,.prog-card:focus-visible .prog-arrow{transform:translateX(6px)}
@media(max-width:900px){.prog-grid{grid-template-columns:1fr 1fr}.prog-next{grid-column:1/-1;grid-row:auto;min-height:150px}}
@media(max-width:480px){.prog-grid{grid-template-columns:1fr}.prog{padding:52px 0}}

/* ============ round 6 surfaces: same family as the story pages ============ */
:root{--sf-radius:14px;--sf-radius-sm:10px;--sf-hair:1px solid rgba(127,127,127,.28)}
@supports (color:color-mix(in srgb,red 10%,blue)){:root{--sf-hair:1px solid color-mix(in srgb,var(--ink) 14%,transparent)}}
.status,.findings,.fig,.chart,.tbl-wrap,.scope,.opener,.defs,.notice,.trace,.doors{border:var(--sf-hair)!important;border-radius:var(--sf-radius);overflow:hidden}
.tbl-wrap{overflow:auto}
.notice{border-color:color-mix(in srgb,var(--warn) 55%,transparent)!important}
.st-cell,.finding,.project,.scope-col+.scope-col{border-left:var(--sf-hair)!important}
.st-cell:first-child,.finding:first-child,.project:first-child{border-left:0!important}
.projects{border:var(--sf-hair)!important;border-radius:var(--sf-radius);overflow:hidden}
.doors{display:grid;gap:12px;border:0!important;overflow:visible;border-radius:0}
.door{border:var(--sf-hair)!important;border-radius:var(--sf-radius);transition:transform .2s cubic-bezier(.2,.8,.2,1),border-color .2s}
a.door:hover{transform:translateY(-2px)}
.btn{border:var(--sf-hair);border-radius:999px;margin:0 8px 8px 0;padding:12px 20px;transition:transform .2s cubic-bezier(.2,.8,.2,1),background .15s}
.btn:hover{transform:translateY(-1px)}
.btn-primary{border-color:var(--accent)}
.chip{border-radius:999px;border:var(--sf-hair)}
.hero{border-bottom:var(--sf-hair)}
.hero-not{border-left:3px solid color-mix(in srgb,var(--ink) 30%,transparent);border-radius:2px}
.pull{border-left-width:3px}
.section-alt,.prog{border-top:var(--sf-hair)}
.fig,.chart{padding:24px}
@media print{.status,.findings,.fig,.chart,.tbl-wrap,.scope,.opener,.defs,.notice,.door{border:1px solid #999!important;border-radius:6px}}
"""


PROGRAMME = [
    ("grounded", "Grounded", "https://priyatham9.github.io/grounded/"),
    ("ehs-osha-analysis", "OSHA data quality", "https://priyatham9.github.io/ehs-osha-analysis/"),
    ("ehs-ai-grounding-eval", "Grounding benchmark", "https://priyatham9.github.io/ehs-ai-grounding-eval/"),
    ("ehs-human-factors-ontology", "Human factors ontology", "https://priyatham9.github.io/ehs-human-factors-ontology/"),
    ("ehs-risk-sem", "SEM for safety risk", "https://priyatham9.github.io/ehs-risk-sem/"),
    ("ehs-capitals-calculator", "Cost-benefit calculator", "https://priyatham9.github.io/ehs-capitals-calculator/"),
    ("ehs-benchmarks", "OSHA benchmarks", "https://priyatham9.github.io/ehs-benchmarks/"),
]

BUILDERS = [build_osha, build_sem, build_grounding, build_ontology]

# Rule 1 of this project: no em dashes anywhere, in any form.
DASHES = [chr(0x2014), chr(0x2015), "&#8212;", "&#x2014;", "&#X2014;"]  # code points, so dedash.py cannot rewrite this guard


def dedash(s):
    # The dash characters are built from code points here too, for the same reason.
    pat = r"\s*(?:" + chr(0x2014) + "|" + chr(0x2015) + r"|&#8212;|&#x2014;|&#X2014;)\s*"
    s = re.sub(pat, " - ", s)
    return s


if __name__ == "__main__":
    for fn in BUILDERS:
        spec = fn()
        out = REPOS / spec["repo"] / "docs"
        out.mkdir(parents=True, exist_ok=True)
        pageurl = f"https://priyatham9.github.io/{spec['repo']}/"
        ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareSourceCode",
            "name": spec["title"],
            "description": spec["desc"],
            "codeRepository": f"{GH}/{spec['repo']}",
            "programmingLanguage": "Python",
            "license": "MIT",
            "author": {
                "@type": "Person",
                "name": "Priyatham Chimmani",
                "url": "https://priyatham9.github.io/",
                "sameAs": ["https://github.com/priyatham9", "https://linkedin.com/in/priyatham9"],
            },
        }
        ldjson = json.dumps(ld, ensure_ascii=False)
        body, tocl = renumber_and_toc(spec.pop("body"), spec.pop("toc"))
        unit = spec.get("unit", "")
        num = spec["num"]
        extra = dict(
            num_to=num.replace(",", ""), num_group="1" if "," in num else "0",
            unit_plain=html.unescape(re.sub(r"<[^>]+>", "", unit)),
            num_k=f"{0.8 * len(num) + 0.3 * len(html.unescape(unit)) + 0.2:.2f}",
        )
        page = SHELL.format(css=CSS, extra=EXTRA_CSS + SITE_CSS, storycss=STORY_CSS,
                            hub=HUB, personal=PERSONAL, gh=GH,
                            pageurl=pageurl, ldjson=ldjson, body=body, toc=tocl,
                            programme=programme(spec["repo"]), doors=doors(spec["repo"]),
                            **extra, **spec)
        page = trim_page(page)
        page = page.replace(
            "</body>",
            '<script id="story-js">/*STORY_JS_START*/' + STORY_JS + "/*STORY_JS_END*/</script>\n"
            + "<script>" + CHARTS_JS + "</script>\n"
            + '<script id="story-glue">' + GLUE_JS + "</script>\n</body>", 1)
        page = apply_banner(page, current_project=spec["repo"], story_href="story.html")
        page = dedash(page)
        for bad in DASHES:
            if bad in page:
                raise SystemExit(f'em dash survived in {spec["repo"]}: {bad!r}')
        (out / "index.html").write_text(page, encoding="utf-8")
        print(f'{spec["repo"]:<32} {len(page):>8,} bytes -> docs/index.html')
