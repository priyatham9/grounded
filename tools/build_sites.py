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

/* ============ banner: the one navigation strip ============ */
/* One sticky header. Row one: brand, estate links, section links, toggle.
   Row two, inside the same banner: the six projects, wrapping or scrolling. */
.topbar{border-bottom:2px solid var(--rule)}
.topbar-inner{flex-wrap:wrap;align-items:center;row-gap:0;padding:0 30px;justify-content:flex-start}
.brand{padding:12px 16px 12px 0;border-right:2px solid var(--rule-soft);margin-right:6px}
.estate-nav{display:contents}
.estate-nav a,.topnav a{text-decoration:none;padding:12px 10px;font-family:var(--font-mono);font-size:.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);white-space:nowrap;transition:color .15s,background .15s}
.estate-nav a:hover,.topnav a:hover{color:var(--ink);background:var(--surface-2)}
.estate-nav a.nav-external{color:var(--accent)}
.estate-nav a.nav-external::after{content:'\\2197';margin-left:3px;font-size:.85em;opacity:.75}
.estate-nav a.nav-external:hover{background:var(--accent-wash);color:var(--accent-2)}
.estate-nav a.nav-paper{color:var(--accent)}
.topnav{margin-left:auto;padding-left:6px;border-left:2px solid var(--rule-soft);gap:0}
.topnav a.is-active{color:var(--ink);box-shadow:inset 0 -2px 0 var(--accent)}
.toggle{margin-left:8px}
.projects{order:10;flex-basis:100%;display:flex;align-items:center;gap:0;margin:0 -30px;padding:0 30px;border-top:1px solid var(--rule-soft);overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:none}
.projects::-webkit-scrollbar{display:none}
.projects-tag{flex:none;font-family:var(--font-mono);font-size:.5625rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);padding:9px 12px 9px 0;white-space:nowrap}
.projects a{flex:none;padding:9px 11px;font-weight:500;border-left:1px solid var(--rule-soft)}
.projects a:last-child{border-right:1px solid var(--rule-soft)}
.projects a[aria-current="page"]{color:var(--ink);font-weight:700;box-shadow:inset 0 -2px 0 var(--accent)}
@media(max-width:900px){
  .topbar-inner{padding:0 22px}
  .projects,.topnav{margin:0 -22px;padding:0 22px}
  .estate-nav a{order:4}
  .toggle{order:5;margin-left:auto}
  .topnav{order:6;flex-basis:100%;border-left:0;border-top:1px solid var(--rule-soft);overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:none}
  .topnav::-webkit-scrollbar{display:none}
  .topnav a{flex:none;padding:9px 10px}
}
@media(max-width:640px){
  .brand{border-right:0;padding-right:0}
  .estate-nav a{padding:12px 7px;font-size:.625rem}
}
.hero{border-top:2px solid var(--rule)}

/* ============ shared site switcher ============ */
.estate{display:flex;gap:0;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;border-bottom:2px solid var(--rule);background:var(--surface-2)}
.estate a{padding:6px 14px;text-decoration:none;color:var(--muted)}
.estate a[aria-current="true"]{color:var(--accent);font-weight:700;box-shadow:inset 0 -2px 0 var(--accent)}
.estate-sep{width:2px;background:var(--rule-soft)}

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
.section{padding:78px 0;scroll-margin-top:112px}
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
thead th{position:sticky;top:0;z-index:2;text-align:left;padding:11px 14px;background:var(--surface-2);box-shadow:inset 0 -2px 0 var(--rule);font-size:.5625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;white-space:nowrap}
td{padding:9px 14px;box-shadow:inset 0 -1px 0 var(--rule-soft);font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink-2)}
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
<style>{css}{extra}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="#top"><span class="brand-mark"></span> {repo}</a>
    <nav class="estate-nav" aria-label="Research estate">
      <a class="nav-external" href="{personal}/">Priyatham Chimmani</a>
      <a href="{hub}">Grounded</a>
      <a class="nav-paper" href="{hub}paper.html">Paper</a>
      <div class="projects" role="list" aria-label="Projects">
        <span class="projects-tag">Projects</span>
        {crossbar}
      </div>
    </nav>
    <nav class="topnav" aria-label="Sections on this page">{nav}</nav>
    <button class="toggle" id="themeToggle" aria-label="Toggle colour scheme">
      <svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>
      <svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>
    </button>
  </div>
</header>
<div class="estate" aria-label="Site switcher"><a href="https://priyatham9.github.io/" data-site="personal">Priyatham Chimmani</a><span class="estate-sep"></span><a href="https://priyatham9.github.io/grounded/" data-site="research" aria-current="true">Grounded research</a></div>
<section class="hero" id="top">
  <div class="wrap">
    <div class="hero-eyebrow"><span class="pulse"></span><span class="label">{kicker}</span></div>
    <h1 class="display">{h1}</h1>
    <p class="hero-role">{lede}</p>
    <div class="hero-links">
      <a class="btn btn-primary" href="{gh}/{repo}">Repository</a>
      <a class="btn" href="#{first}">{firstlabel}</a>
      <a class="btn" href="{hub}">All projects</a>
    </div>
    <div class="status">{status}</div>
  </div>
</section>
<main id="main">
{body}
</main>
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
    <p class="footer-note">Every number, table and figure on this page is read from a committed
    artifact in this repository at build time by <span class="mono">tools/build_sites.py</span>.
    Captions name the artifact. The page cannot report a value the pipeline did not produce.</p>
  </div>
</footer>
<script>
(function () {{
  var root = document.documentElement, KEY = 'ehs-ai-theme';
  try {{ var s = localStorage.getItem(KEY); if (s) root.setAttribute('data-theme', s); }} catch (e) {{}}
  var btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', function () {{
    var c = root.getAttribute('data-theme');
    if (!c) c = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var n = c === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', n);
    try {{ localStorage.setItem(KEY, n); }} catch (e) {{}}
  }});
}})();
(function () {{
  var links = Array.prototype.slice.call(document.querySelectorAll('.topnav a[href^="#"]'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var map = {{}}, ratio = {{}};
  links.forEach(function (a) {{
    var el = document.getElementById(a.getAttribute('href').slice(1));
    if (el) {{ map[el.id] = a; ratio[el.id] = 0; }}
  }});
  var ids = Object.keys(map);
  if (!ids.length) return;
  function paint() {{
    var best = null, bestv = 0;
    ids.forEach(function (id) {{ if (ratio[id] > bestv) {{ bestv = ratio[id]; best = id; }} }});
    links.forEach(function (a) {{ a.classList.remove('is-active'); a.removeAttribute('aria-current'); }});
    if (best) {{ map[best].classList.add('is-active'); map[best].setAttribute('aria-current', 'true'); }}
  }}
  var obs = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{ ratio[e.target.id] = e.isIntersecting ? e.intersectionRatio : 0; }});
    paint();
  }}, {{ rootMargin: '-116px 0px -50% 0px', threshold: [0, 0.05, 0.2, 0.5, 0.9] }});
  ids.forEach(function (id) {{ obs.observe(document.getElementById(id)); }});
}})();
(function () {{
  /* Hero status numbers count up once when scrolled into view. Skipped under
     reduced motion and where IntersectionObserver is missing: the final value
     is already in the markup, so nothing is lost. */
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (!('IntersectionObserver' in window)) return;
  var cells = Array.prototype.slice.call(document.querySelectorAll('.status .st-v'));
  var re = /^(\d[\d,]*)(\.\d+)?(%?)$/;
  cells.forEach(function (el) {{
    var m = re.exec(el.textContent.trim());
    if (!m) return;
    var target = parseFloat(m[1].replace(/,/g, '') + (m[2] || ''));
    var dec = m[2] ? m[2].length - 1 : 0, suffix = m[3], grouped = m[1].indexOf(',') !== -1;
    var done = false;
    function fmt(v) {{
      var t = v.toFixed(dec);
      if (grouped) {{ var parts = t.split('.'); parts[0] = parts[0].replace(/\B(?=(\d{{3}})+(?!\d))/g, ','); t = parts.join('.'); }}
      return t + suffix;
    }}
    var obs = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{
        if (!e.isIntersecting || done) return;
        done = true; obs.disconnect();
        var t0 = null, dur = 900;
        function step(ts) {{
          if (t0 === null) t0 = ts;
          var k = Math.min(1, (ts - t0) / dur); k = 1 - Math.pow(1 - k, 3);
          el.textContent = fmt(target * k);
          if (k < 1) requestAnimationFrame(step); else el.textContent = fmt(target);
        }}
        requestAnimationFrame(step);
      }});
    }}, {{ threshold: 0.4 }});
    obs.observe(el);
  }});
}})();
</script>
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
    return (f'<section class="section" id="{sid}"><div class="wrap">'
            f'<div class="rail-head"><span class="rail-num">{num}</span>'
            f'<h2 class="display">{title}</h2>{n}</div>{l}{inner}</div></section>')


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
    return (f'<figure class="fig"><div class="fig-scroll">{"".join(out)}</div>{lg}'
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
    return (f'<figure class="fig"><div class="fig-scroll">{"".join(out)}</div>{lg}'
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
    return (f'<figure class="fig"><div class="fig-scroll">{"".join(out)}</div>'
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
        "<h3>What this does not establish</h3>"
        "<p>The screen identifies filings that cannot be right. It does not identify filings that "
        "are merely wrong, and it cannot recover the true hours for an excluded establishment.</p>"
        "<p>Aggregates after screening are conditional on the surviving population, which is not a "
        "random sample of the original. If implausible hours are filed disproportionately by one "
        "kind of employer, the screened aggregate inherits that selection.</p>"
        "<p>Nothing here is a claim about whether workplaces got safer. It is a claim about what "
        "the denominator will support.</p>"
        "<h3>Reviewer note</h3>"
        "<p>An internal adversarial review held that this analysis is a separable contribution "
        "being buried inside a larger manuscript, and that it should stand as its own paper. That "
        "criticism is recorded here rather than answered.</p>"
        "</div></div>")

    body = (
        section("why", "01", "Why this exists", lead)
        + section("findings", "02", "Findings", findings,
                  lede="Four numbers, each traceable to the artifact named beneath it.")
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
    )

    return dict(
        repo=repo, mark="O", title="OSHA injury-rate data quality - " + repo,
        desc="A reproducible analysis of data quality in OSHA Injury Tracking Application "
             "establishment filings, over 2.8 million real public records.",
        kicker="Empirical analysis - real public data",
        h1="The hours column decides every benchmark built on it",
        lede=f"A reproducible pipeline over {q['n_filings']:,} public establishment filings, "
             f"CY{y0} to CY{y1}. {q['implausible_share']*100:.2f}% of filings carry "
             f"{q['hours_share_implausible']*100:.1f}% of all reported hours, and the correction "
             f"that follows ranges from {min(ratios):.2f}x to {max(ratios):.0f}x depending on the "
             f"year. It cannot be published as a constant.",
        status=status, body=body, first="why", firstlabel="Why this exists",
        nav='<a href="#why">Why</a><a href="#findings">Findings</a>'
            '<a href="#byyear">By year</a><a href="#hours">Hours</a>'
            '<a href="#figures">Figures</a><a href="#models">Models</a>'
            '<a href="#peers">Peers</a><a href="#method">Method</a>')


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

    limits = notice(
        "What this does not establish",
        '<p>Simulation establishes estimator properties, not empirical facts. These studies show '
        "what the method does when its assumptions hold and how it fails when they do not. They "
        "say nothing about whether any particular safety programme works, and they are not "
        "evidence about any real site.</p>"
        "<ul>"
        "<li>The generating models are the author's, chosen to resemble the structure the "
        "circulating formula implies. A different generating model would give different numbers, "
        "though the identification results do not depend on the parameterisation.</li>"
        "<li>Replication counts are modest in places and each table records its own. The "
        "bootstrap study runs 40 replications, which is enough to show the direction of the "
        "coverage gap and not enough to pin its size.</li>"
        "<li>Nothing here has been peer reviewed.</li>"
        "</ul>"
        "<p>The practical conclusion is narrow and worth stating plainly: illustrative path "
        "weights of the kind that circulate in practitioner writing cannot be read causally, "
        "cannot be transferred between sites, and cannot be validated by goodness of fit.</p>")

    body = (
        section("why", "01", "Why this exists", lead)
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
        + section("limits", "08", "Limits", limits)
    )

    return dict(
        repo=repo, mark="S", title="Structural equation modelling for safety risk - " + repo,
        desc="Simulation studies establishing what structural equation modelling can and cannot "
             "recover for safety risk scoring. All data simulated by design.",
        kicker="Method study - every number simulated by design",
        h1="What SEM cannot tell you about safety risk",
        lede="A from-scratch estimator in numpy, then simulation studies covering coefficient "
             "recovery, interval coverage, sample size, rare-event calibration, misspecification "
             "and model equivalence. Ground truth is known by construction, so estimator behaviour "
             "is measured rather than assumed. Nothing here analyses real injury data.",
        status=status, body=body, first="why", firstlabel="Why this exists",
        nav='<a href="#why">Why</a><a href="#recovery">Recovery</a>'
            '<a href="#sizing">Sizing</a><a href="#rare">Rare events</a>'
            '<a href="#zero">Zero inflation</a><a href="#misspec">Misspecification</a>'
            '<a href="#meaning">Meaning</a><a href="#limits">Limits</a>')


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
        "<p><strong>No system has been evaluated on this corpus.</strong> What exists is the "
        "apparatus: a question corpus, a scoring harness, a source verification tool, and a "
        "preregistered analysis plan frozen before any run.</p>"
        "<p>That is a real limitation, not a phase of a rollout. Without baselines nobody can tell "
        "whether these items discriminate between systems at all.</p>")

    no_results = notice(
        "Apparatus and preregistration - no results",
        "<p>This repository contributes a question corpus and a scoring harness. No system has "
        "been evaluated on it. An internal adversarial review was blunt about what that means: a "
        "benchmark with zero baselines is a preregistration, not a result, and it cannot be "
        "assessed for whether its items discriminate.</p>"
        "<ul>"
        "<li>Running two or three systems across the three arms is the immediate next step, and "
        "until that happens nothing here should be cited as a finding about any model.</li>"
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

    body = (
        section("why", "01", "Why this exists", lead)
        + section("status", "02", "Status", no_results,
                  lede="Stated before anything else on the page, because a benchmark is easy to "
                       "mistake for a result.")
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
    )

    return dict(
        repo=repo, mark="G", title="Grounding evaluation for safety-critical QA - " + repo,
        desc="A preregistered benchmark for whether AI answers to safety-critical technical "
             "questions are bound to authoritative sources. Apparatus only, no baseline results.",
        kicker="Benchmark - apparatus and preregistration, no results yet",
        h1="Measuring whether an answer is grounded or merely plausible",
        lede=f"{total} questions built around plausible-but-wrong adjacent answers in pressure "
             f"relief, lockout/tagout, confined space, process safety and recordkeeping, with "
             f"scoring that rewards abstention over confabulation. Every source is verified "
             f"against a pinned eCFR edition. No system has been evaluated yet: this is apparatus "
             f"and a frozen analysis plan, not a finding.",
        status=status, body=body, first="why", firstlabel="Why this exists",
        nav='<a href="#why">Why</a><a href="#status">Status</a>'
            '<a href="#corpus">Corpus</a><a href="#sources">Sources</a>'
            '<a href="#scoring">Scoring</a><a href="#prereg">Prereg</a>')


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

    body = (
        section("why", "01", "Why this exists", lead)
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
    )

    return dict(
        repo=repo, mark="H", title="Human factors ontology - " + repo,
        desc="Contextual human error risk factors formalised as an OWL ontology with a "
             "crosswalk to prior human reliability work and auditable derivation traces.",
        kicker="Ontology - adopted taxonomy, contributed formalisation",
        h1="Human error context, formalised and traceable",
        lede=f"An OWL ontology of {local_factors} contextual factors shaping human error, adopted "
             f"from IDHEAS-G and mapped explicitly onto {len(frameworks)} external frameworks "
             f"through {len(aligned)} cited alignments and {len(absences)} asserted absences, with "
             f"a forward-chaining engine that emits a real derivation trace for every conclusion. "
             f"Factor levels are analyst-assigned, and the page says so throughout.",
        status=status, body=body, first="why", firstlabel="Why this exists",
        nav='<a href="#why">Why</a><a href="#adopted">Adopted</a>'
            '<a href="#crosswalk">Crosswalk</a><a href="#trace">Trace</a>'
            '<a href="#engine">Engine</a><a href="#gaps">Gaps</a>'
            '<a href="#limits">Limits</a>')


PROGRAMME = [
    ("grounded", "Grounded", "https://priyatham9.github.io/grounded/"),
    ("ehs-osha-analysis", "OSHA data quality", "https://priyatham9.github.io/ehs-osha-analysis/"),
    ("ehs-ai-grounding-eval", "Grounding benchmark", "https://priyatham9.github.io/ehs-ai-grounding-eval/"),
    ("ehs-human-factors-ontology", "Human factors ontology", "https://priyatham9.github.io/ehs-human-factors-ontology/"),
    ("ehs-risk-sem", "SEM for safety risk", "https://priyatham9.github.io/ehs-risk-sem/"),
    ("ehs-capitals-calculator", "Cost-benefit calculator", "https://priyatham9.github.io/ehs-capitals-calculator/"),
    ("ehs-benchmarks", "OSHA benchmarks", "https://priyatham9.github.io/ehs-benchmarks/"),
]

PREVNEXT_CSS = """
.pn{display:grid;grid-template-columns:1fr 1fr;border:2px solid var(--rule);background:var(--surface);margin:0 auto;max-width:var(--maxw)}
.pn a{padding:22px 26px;text-decoration:none;color:var(--ink);display:flex;flex-direction:column;gap:6px;transition:background .15s}
.pn a:hover{background:var(--accent-wash)}
.pn a+a{border-left:2px solid var(--rule-soft);text-align:right;align-items:flex-end}
.pn .label{color:var(--accent)}
.pn .pn-t{font-family:var(--font-mono);font-weight:700;font-size:.95rem}
.pn-wrap{padding:0 30px 48px}
@media(max-width:640px){.pn{grid-template-columns:1fr}.pn a+a{border-left:0;border-top:2px solid var(--rule-soft);text-align:left;align-items:flex-start}}
"""

def prevnext(repo):
    keys = [k for k,_,_ in PROGRAMME]
    i = keys.index(repo)
    pv = PROGRAMME[(i - 1) % len(PROGRAMME)]
    nx = PROGRAMME[(i + 1) % len(PROGRAMME)]
    return (f'<div class="pn-wrap"><nav class="pn" aria-label="Programme navigation">'
            f'<a href="{pv[2]}"><span class="label">Previous</span><span class="pn-t">&larr; {pv[1]}</span></a>'
            f'<a href="{nx[2]}"><span class="label">Next</span><span class="pn-t">{nx[1]} &rarr;</span></a>'
            f'</nav></div>')

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
        page = SHELL.format(css=CSS, extra=EXTRA_CSS, hub=HUB, personal=PERSONAL, gh=GH,
                            crossbar=crossbar(spec["repo"]), pageurl=pageurl, ldjson=ldjson, **spec)
        page = page.replace("</style>", PREVNEXT_CSS + "</style>", 1)
        if spec["repo"] in ("ehs-ai-grounding-eval", "ehs-human-factors-ontology"):
            page = page.replace('<main id="main">\n', '<main id="main">\n<div class="wrap" style="padding-top:40px">'
                                + statrow(spec["status"]) + '</div>', 1)
        page = trim_page(page)
        page = page.replace("</body>", "<script>" + CHARTS_JS + "</script>\n</body>", 1)
        page = page.replace('<footer class="footer">', prevnext(spec["repo"]) + '<footer class="footer">', 1)
        page = apply_banner(page, current_project=spec["repo"])
        page = dedash(page)
        for bad in DASHES:
            if bad in page:
                raise SystemExit(f'em dash survived in {spec["repo"]}: {bad!r}')
        (out / "index.html").write_text(page, encoding="utf-8")
        print(f'{spec["repo"]:<32} {len(page):>8,} bytes -> docs/index.html')
