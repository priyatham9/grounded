"""One banner for every research page.

Two rows, the whole header sticky. Row one: brand (home), the author's personal
site, then Overview / Projects / Papers, then the theme toggle. Row two, only
where a page has sections: the section links, which existing scroll-spy scripts
keep targeting (id="sectionNav", class "topnav").

apply_banner(html, current_project=None, current_paper=None) replaces whatever
<header>...</header> a page carries and removes the old site-switcher strip, so
generated and hand-built pages end up identical.
"""
import re

PERSONAL = "https://priyatham9.github.io/"
HUB = "https://priyatham9.github.io/grounded/"
PROJECTS = [
    ("ehs-osha-analysis", "OSHA data quality", "2.8M real filings"),
    ("ehs-ai-grounding-eval", "Grounding benchmark", "first baselines"),
    ("ehs-human-factors-ontology", "Human factors ontology", "derivation traces"),
    ("ehs-risk-sem", "SEM for safety risk", "simulation studies"),
    ("ehs-capitals-calculator", "Cost-benefit calculator", "interactive tool"),
    ("ehs-benchmarks", "OSHA benchmarks", "TRIR/DART library"),
]
PAPERS = [
    ("paper.html", "Grounded reasoning for safety-critical AI", "bundled draft"),
    ("paper-osha.html", "The hours denominator", "standalone OSHA paper"),
]

CSS = r"""
/* ---- shared banner ---- */
.gbar{position:sticky;top:0;z-index:70;background:var(--paper);border-bottom:2px solid var(--rule)}
.gbar-row{max-width:var(--maxw,1180px);margin:0 auto;padding:0 24px;display:flex;align-items:stretch;gap:0;min-height:52px}
.gbar-brand{display:flex;align-items:center;gap:10px;padding:0 14px 0 0;font-family:var(--font-mono);font-size:.8125rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--ink);text-decoration:none;border-right:2px solid var(--rule-soft)}
.gbar-mark{width:14px;height:14px;background:var(--accent);flex:none}
.gbar-personal{display:flex;align-items:center;padding:0 14px;font-family:var(--font-mono);font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);text-decoration:none;border-right:2px solid var(--rule-soft)}
.gbar-personal::after{content:'\2197';margin-left:5px;opacity:.7}
.gbar-personal:hover{color:var(--accent);background:var(--surface-2)}
.gbar-primary{display:flex;align-items:stretch;margin-left:auto}
.gbar-primary>a,.gbar-menu>summary{display:flex;align-items:center;padding:0 14px;font-family:var(--font-mono);font-size:.6875rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);text-decoration:none;cursor:pointer;list-style:none;white-space:nowrap;transition:color .15s,background .15s}
.gbar-menu>summary::-webkit-details-marker{display:none}
.gbar-menu>summary::before{content:none!important}
.gbar-menu>summary{margin:0}
.gbar-menu[open]>summary::after{content:'\25B4'}
.gbar-menu>summary::after{content:'\25BE';margin-left:6px;font-size:.8em;opacity:.7}
.gbar-primary>a:hover,.gbar-menu>summary:hover{color:var(--ink);background:var(--surface-2)}
.gbar-primary>a[aria-current="page"],.gbar-menu[data-current="true"]>summary{color:var(--accent);box-shadow:inset 0 -3px 0 var(--accent)}
.gbar-menu{position:relative}
.gbar-menu[open]>summary{background:var(--surface-2);color:var(--ink)}
.gbar-panel{position:absolute;right:0;top:100%;min-width:300px;background:var(--surface);border:2px solid var(--rule);border-top:0;z-index:80;box-shadow:0 12px 30px var(--shadow,rgba(0,0,0,.15))}
.gbar-panel a{display:grid;grid-template-columns:1fr auto;gap:12px;padding:11px 14px;text-decoration:none;color:var(--ink);border-bottom:1px solid var(--rule-soft);font-size:.875rem}
.gbar-panel a:last-child{border-bottom:0}
.gbar-panel a:hover{background:var(--accent-wash)}
.gbar-panel a[aria-current="page"]{color:var(--accent);font-weight:700}
.gbar-panel a small{font-family:var(--font-mono);font-size:.625rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);align-self:center}
.gbar-toggle{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;flex:none;margin:4px 0 4px 12px;background:var(--paper);border:2px solid var(--rule);border-radius:0;color:var(--ink);cursor:pointer}
.gbar-toggle svg{width:15px;height:15px}
.gbar-toggle:hover{background:var(--surface-2)}
.gbar-sections{max-width:var(--maxw,1180px);margin:0 auto;padding:0 24px;display:flex;gap:0;overflow-x:auto;border-top:2px solid var(--rule-soft);scrollbar-width:none}
.gbar-sections::-webkit-scrollbar{display:none}
.gbar-sections a{padding:9px 11px;font-family:var(--font-mono);font-size:.625rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-decoration:none;white-space:nowrap;border-bottom:3px solid transparent}
.gbar-sections a:hover{color:var(--ink)}
.gbar-sections a.active,.gbar-sections a[aria-current="true"]{color:var(--accent);border-bottom-color:var(--accent)}
.gbar-sections .topnav-n{color:var(--accent);margin-right:5px}
html{scroll-padding-top:110px}
[id]{scroll-margin-top:110px}
@media(max-width:760px){
  .gbar-row{padding:0 12px;flex-wrap:wrap}
  .gbar-personal{display:none}
  .gbar-primary>a,.gbar-menu>summary{padding:0 9px;font-size:.625rem}
  .gbar-panel{position:fixed;left:0;right:0;top:auto;min-width:0;border-left:0;border-right:0}
}
@media print{.gbar{display:none}}
"""

JS = r"""
<script>
(function(){
  var menus=[].slice.call(document.querySelectorAll('.gbar-menu'));
  menus.forEach(function(m){m.addEventListener('toggle',function(){if(m.open)menus.forEach(function(o){if(o!==m)o.open=false;});});});
  document.addEventListener('click',function(e){if(!e.target.closest('.gbar-menu'))menus.forEach(function(o){o.open=false;});});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')menus.forEach(function(o){o.open=false;});});
  var bar=document.getElementById('gbar');
  function h(){document.documentElement.style.setProperty('--topbar-h',Math.round(bar.getBoundingClientRect().height)+'px');}
  h();window.addEventListener('resize',h);
})();
</script>
"""

TOGGLE = ('<button class="gbar-toggle toggle" id="themeToggle" aria-label="Toggle colour scheme">'
          '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>'
          '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg></button>')


def _sections_from(old_header):
    """Lift the page's own section links out of whatever header it had."""
    m = (re.search(r'<nav[^>]*id="sectionNav"[^>]*>(.*?)</nav>', old_header, re.S)
         or re.search(r'<nav[^>]*aria-label="(?:Sections[^"]*|On this page)"[^>]*>(.*?)</nav>', old_header, re.S)
         or re.search(r'<nav[^>]*class="[^"]*(?:topnav|bnav-sections)[^"]*"[^>]*>(.*?)</nav>', old_header, re.S))
    if not m:
        return ""
    links = re.findall(r'<a\s[^>]*href="#[^"]*"[^>]*>.*?</a>', m.group(1), re.S)
    return "".join(links)


def build(current_project=None, current_paper=None, sections_html="", is_hub=False):
    proj = "".join(
        '<a href="https://priyatham9.github.io/%s/"%s>%s<small>%s</small></a>'
        % (slug, ' aria-current="page"' if slug == current_project else "", name, note)
        for slug, name, note in PROJECTS)
    paps = "".join(
        '<a href="%s%s"%s>%s<small>%s</small></a>'
        % (HUB, f, ' aria-current="page"' if f == current_paper else "", name, note)
        for f, name, note in PAPERS)
    sec = ('<nav class="gbar-sections topnav" id="sectionNav" aria-label="On this page">%s</nav>' % sections_html) if sections_html else ""
    return (
        '<header class="gbar topbar" id="gbar">'
        '<div class="gbar-row">'
        '<a class="gbar-brand" href="%s"><span class="gbar-mark"></span>Grounded</a>'
        '<a class="gbar-personal" href="%s">Priyatham Chimmani</a>'
        '<nav class="gbar-primary" aria-label="Research site">'
        '<a href="%s"%s>Overview</a>'
        '<details class="gbar-menu"%s><summary>Projects</summary><div class="gbar-panel">%s</div></details>'
        '<details class="gbar-menu"%s><summary>Papers</summary><div class="gbar-panel">%s</div></details>'
        '</nav>%s</div>%s</header>'
        % (HUB, PERSONAL, HUB, ' aria-current="page"' if is_hub else "",
           ' data-current="true"' if current_project else "", proj,
           ' data-current="true"' if current_paper else "", paps,
           TOGGLE, sec))


def apply_banner(html, current_project=None, current_paper=None, is_hub=False):
    m = re.search(r'<header\b.*?</header>', html, re.S)
    old = m.group(0) if m else ""
    new = build(current_project, current_paper, _sections_from(old), is_hub)
    html = html[:m.start()] + new + html[m.end():] if m else html.replace("<body>", "<body>" + new, 1)
    html = re.sub(r'\s*<div class="estate"[^>]*>.*?</div>', "", html, count=1, flags=re.S)
    html = re.sub(r"/\* ---- shared banner ---- \*/.*?@media print\{\.gbar\{display:none\}\}\n?", "", html, count=1, flags=re.S)
    html = html.replace("</style>", CSS + "</style>", 1)
    if "getElementById('gbar')" not in html:
        html = html.replace("</body>", JS + "</body>", 1)
    return html
