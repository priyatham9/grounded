"""One header for every research page (single source of truth).

Public API
----------
build_header(current, sections, story_href=None)   -> header markup (str)
HEADER_CSS, HEADER_JS, HEAD_THEME_SNIPPET -> full <style>/<script> elements
apply_banner(html, current=None, sections=None, current_project=None,
             current_paper=None, is_hub=False) -> html with the header applied

`current` is one of: 'hub', 'start', 'observatory', 'changelog', a repo name from
PROJECTS (e.g. 'ehs-risk-sem') or a paper filename from PAPERS (e.g. 'paper.html').
The old keywords still work: current_project=<repo>, current_paper=<file>,
is_hub=True.

`sections` is a list of (id, label). None means auto-detect: first from an
existing #sectionNav / .topnav / .gbar-sections nav, then from <section id> + <h2>
(needs at least 2). Pass [] to force no section row.

apply_banner is idempotent. On every run it removes:
  * every <header> whose class contains gbar, topbar or rs-header
  * old site-switcher strips: <div class="estate">...</div>
  * <style id="rs-header-css">, <script id="rs-header-js">, <script id="rs-theme-init">
  * the old "/* ---- shared banner ---- */ ... @media print{.gbar{display:none}}" CSS block
  * inside every other <style>: any selector that contains `.gbar` or `.estate`
    (a rule is dropped when all of its selectors match, otherwise only the
    matching selectors are removed from the list; @media/@supports blocks left
    empty are dropped). Nothing else in page CSS is touched.
  * the old banner.JS <script> (under 1200 chars, has .gbar-menu and getElementById('gbar'),
    no themeToggle); larger page scripts that mention .gbar-menu are left for the page owner
It then injects the theme snippet + CSS before </head>, the header right after
<body>, and the JS before </body>.

Theme-toggle contract
---------------------
The header owns the only theme toggle: <button id="rs-theme">. It sets
data-theme="light|dark" on <html>, reads localStorage "pc-theme" first (shared
with the personal site on the same origin), falls back to "ehs-ai-theme", and
writes both keys. With nothing stored it follows prefers-color-scheme (no
data-theme attribute). After a toggle it dispatches
document 'rs-themechange' with detail {theme}. Pages must delete:
  * any button #themeToggle / .toggle / .gbar-toggle and its click handler
    (scripts using getElementById('themeToggle') or KEY='ehs-ai-theme')
  * their own inline <head> theme pre-paint script (HEAD_THEME_SNIPPET replaces it)
  * their own section scroll-spy / progress-bar scripts that target
    #sectionNav, .topnav, #progress or #gbarNow (the header does scroll-spy and
    reading progress itself)
  * .icon-sun/.icon-moon display rules that exist only for the old toggle.
"""
import html as _html
import re
import sys

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
PRIMARY = [("hub", "Overview", HUB), ("start", "Start here", HUB + "start.html"),
           ("observatory", "Observatory", HUB + "observatory.html")]

_E = _html.escape

HEAD_THEME_SNIPPET = (
    '<script id="rs-theme-init">try{var t=localStorage.getItem("pc-theme")||'
    'localStorage.getItem("ehs-ai-theme");if(t==="light"||t==="dark")'
    'document.documentElement.setAttribute("data-theme",t);}catch(e){}</script>')

_SUN = ('<svg class="rs-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
        '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>')
_FIND = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
         '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>')
_MOON = ('<svg class="rs-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
         '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>')

HEADER_CSS = r"""<style id="rs-header-css">
.rs-header,.rs-k{
 --rs-paper:var(--paper,#F7F7F3);--rs-surface:var(--surface,#FFFFFF);--rs-surface-2:var(--surface-2,#EFEFE9);
 --rs-ink:var(--ink,#101311);--rs-muted:var(--muted,var(--ink-2,#5E655F));--rs-rule:var(--rule,#101311);
 --rs-rule-soft:var(--rule-soft,#D6D7CE);--rs-accent:var(--accent,#1E40AF);
 --rs-mono:var(--font-mono,"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace);
 --rs-sans:var(--font-sans,"Archivo",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif);
}
:root[data-theme="dark"] .rs-header,:root[data-theme="dark"] .rs-k{
 --rs-paper:var(--paper,#0A0C10);--rs-surface:var(--surface,#12151C);--rs-surface-2:var(--surface-2,#171B24);
 --rs-ink:var(--ink,#EAECF2);--rs-muted:var(--muted,var(--ink-2,#959CAB));--rs-rule:var(--rule,#EAECF2);
 --rs-rule-soft:var(--rule-soft,#2C3240);--rs-accent:var(--accent,#7C9EFF);
}
@media (prefers-color-scheme:dark){:root:not([data-theme]) .rs-header,:root:not([data-theme]) .rs-k{
 --rs-paper:var(--paper,#0A0C10);--rs-surface:var(--surface,#12151C);--rs-surface-2:var(--surface-2,#171B24);
 --rs-ink:var(--ink,#EAECF2);--rs-muted:var(--muted,var(--ink-2,#959CAB));--rs-rule:var(--rule,#EAECF2);
 --rs-rule-soft:var(--rule-soft,#2C3240);--rs-accent:var(--accent,#7C9EFF);
}}
:root{--rs-header-h:58px}
html{scroll-padding-top:calc(var(--rs-header-h) + 12px)}
a.skip,a.skip-link{min-height:44px;box-sizing:border-box}
/* isolation: neutralise page element rules (header{}, nav a{}, button{} ...) */
.rs-header :where(a,button,nav,div,span,summary,details,b,i){all:revert;box-sizing:border-box}
.rs-header [hidden]{display:none!important}
.rs-header svg{display:block;width:18px;height:18px;fill:none;stroke:currentColor}
.rs-header{all:revert;display:block;position:sticky;top:0;z-index:1000;margin:0;padding:0;width:auto;max-width:none;float:none;transform:none;
 box-sizing:border-box;background:var(--rs-paper);color:var(--rs-ink);border:0;box-shadow:none;font:400 14px/1.3 var(--rs-sans);text-align:left}
.rs-header .rs-bar{border-bottom:2px solid var(--rs-rule);background:var(--rs-paper)}
.rs-header .rs-row{display:flex;align-items:center;max-width:1180px;height:56px;margin:0 auto;padding:0 24px}
.rs-header .rs-brand{display:flex;align-items:center;gap:10px;height:56px;padding:0 16px 0 0;font:700 13px/1 var(--rs-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--rs-ink);text-decoration:none;white-space:nowrap}
.rs-header .rs-mark{display:block;width:14px;height:14px;background:var(--rs-accent);flex:none}
.rs-header .rs-author{display:flex;align-items:center;height:44px;padding:0 0 0 16px;background:linear-gradient(var(--rs-rule-soft),var(--rs-rule-soft)) 0 50%/2px 24px no-repeat;font:500 12px/1 var(--rs-mono);letter-spacing:.06em;color:var(--rs-muted);text-decoration:none;white-space:nowrap;margin-right:8px}
.rs-header .rs-author:hover{color:var(--rs-accent)}
.rs-header .rs-nav{display:flex;align-items:center;height:56px;margin:0 0 0 auto;padding:0}
.rs-header .rs-menu{display:flex;align-items:center;position:relative;height:56px;margin:0;padding:0}
.rs-header .rs-item{display:flex;align-items:center;gap:6px;height:56px;margin:0;padding:0 14px;font:600 12px/1 var(--rs-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--rs-muted);text-decoration:none;white-space:nowrap;cursor:pointer;list-style:none;background:transparent;border:0}
.rs-header .rs-item::-webkit-details-marker{display:none}
.rs-header .rs-item::marker{content:""}
.rs-header .rs-item:hover,.rs-header .rs-menu[open]>.rs-item{background:var(--rs-surface-2);color:var(--rs-ink)}
.rs-header .rs-item[aria-current="page"],.rs-header .rs-menu[data-current]>.rs-item{color:var(--rs-ink);box-shadow:inset 0 -3px 0 var(--rs-accent)}
.rs-header .rs-story{color:var(--rs-accent);font-weight:700;box-shadow:inset 0 -3px 0 var(--rs-accent)}
.rs-header .rs-story::before{content:"";display:block;width:7px;height:7px;background:var(--rs-accent);flex:none}
.rs-header .rs-story:hover{background:var(--rs-accent);color:var(--rs-paper)}
.rs-header .rs-story:hover::before{background:var(--rs-paper)}
.rs-header .rs-caret{display:block;width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid currentColor;transition:transform .15s}
.rs-header .rs-menu[open] .rs-caret{transform:rotate(180deg)}
.rs-header .rs-panel{display:block;position:absolute;top:calc(100% + 2px);right:0;width:340px;max-width:calc(100vw - 32px);margin:0;padding:0;background:var(--rs-surface);border:2px solid var(--rs-rule);box-shadow:6px 6px 0 var(--rs-rule);z-index:1}
.rs-header .rs-opt{display:flex;flex-direction:column;justify-content:center;gap:4px;min-height:44px;padding:9px 14px;border-bottom:1px solid var(--rs-rule-soft);color:var(--rs-ink);text-decoration:none}
.rs-header .rs-opt:last-child{border-bottom:0}
.rs-header .rs-opt:hover{background:var(--rs-surface-2)}
.rs-header .rs-opt[aria-current="page"]{box-shadow:inset 4px 0 0 var(--rs-accent);background:var(--rs-surface-2)}
.rs-header .rs-t{display:block;font:500 14px/1.25 var(--rs-sans);color:var(--rs-ink)}
.rs-header .rs-n{display:block;font:400 12px/1.25 var(--rs-mono);letter-spacing:.04em;color:var(--rs-muted)}
.rs-header .rs-opt[aria-current="page"] .rs-n::after{content:" \00B7  you are here";color:var(--rs-accent)}
.rs-header .rs-sep{display:block;width:2px;height:24px;margin:0 12px 0 10px;background:var(--rs-rule-soft);flex:none}
.rs-header .rs-btn{display:inline-flex;align-items:center;justify-content:center;flex:none;width:44px;height:44px;margin:0;padding:0;background:var(--rs-paper);color:var(--rs-ink);border:2px solid var(--rs-rule);border-radius:0;cursor:pointer;font:600 12px/1 var(--rs-mono);touch-action:manipulation}
.rs-header .rs-find{margin-right:8px;gap:8px}
.rs-header .rs-find span{display:none}
.rs-header:not(.rs-js) .rs-find{display:none}
.rs-header .rs-btn:hover{background:var(--rs-surface-2)}
.rs-header .rs-moon{display:none}
:root[data-theme="dark"] .rs-header .rs-sun{display:none}
:root[data-theme="dark"] .rs-header .rs-moon{display:block}
@media (prefers-color-scheme:dark){:root:not([data-theme]) .rs-header .rs-sun{display:none}:root:not([data-theme]) .rs-header .rs-moon{display:block}}
.rs-header .rs-burger{display:none;width:44px;height:44px;margin-left:8px}
.rs-header .rs-burger i{display:block;position:relative;width:18px;height:2px;background:currentColor;transition:background .15s}
.rs-header .rs-burger i::before,.rs-header .rs-burger i::after{content:"";position:absolute;left:0;width:18px;height:2px;background:currentColor;transition:transform .15s}
.rs-header .rs-burger i::before{top:-6px}.rs-header .rs-burger i::after{top:6px}
.rs-header .rs-burger[aria-expanded="true"] i{background:transparent}
.rs-header .rs-burger[aria-expanded="true"] i::before{transform:translateY(6px) rotate(45deg)}
.rs-header .rs-burger[aria-expanded="true"] i::after{transform:translateY(-6px) rotate(-45deg)}
.rs-header :focus-visible{outline:2px solid var(--rs-accent);outline-offset:-2px}
/* row 2 */
.rs-header .rs-sub{position:relative;border-bottom:2px solid var(--rs-rule-soft);background:var(--rs-paper)}
.rs-header .rs-subrow{height:44px}
.rs-header .rs-sublabel{display:block;flex:none;padding:0 12px 0 0;font:500 12px/1 var(--rs-mono);letter-spacing:.06em;color:var(--rs-muted);white-space:nowrap}
.rs-header .rs-sections{display:flex;align-items:center;position:relative;flex:1 1 auto;min-width:0;height:44px;margin:0;padding:0;overflow-x:auto;scrollbar-width:none}
.rs-header .rs-sections::-webkit-scrollbar{display:none}
.rs-header .rs-sections.rs-fl{-webkit-mask-image:linear-gradient(90deg,transparent,#000 32px);mask-image:linear-gradient(90deg,transparent,#000 32px)}
.rs-header .rs-sections.rs-fr{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent)}
.rs-header .rs-sections.rs-fl.rs-fr{-webkit-mask-image:linear-gradient(90deg,transparent,#000 32px,#000 calc(100% - 32px),transparent);mask-image:linear-gradient(90deg,transparent,#000 32px,#000 calc(100% - 32px),transparent)}
.rs-header .rs-sec{display:flex;align-items:center;flex:none;height:44px;padding:0 10px;font:600 12px/1 var(--rs-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--rs-muted);text-decoration:none;white-space:nowrap}
.rs-header .rs-sec:hover{color:var(--rs-ink)}
.rs-header .rs-sec.rs-active{color:var(--rs-accent);box-shadow:inset 0 -2px 0 var(--rs-accent)}
.rs-header .rs-subbtn{display:none;align-items:center;gap:8px;width:100%;height:44px;margin:0;padding:0;background:transparent;border:0;color:var(--rs-muted);font:500 12px/1 var(--rs-mono);letter-spacing:.06em;cursor:pointer;text-align:left}
.rs-header .rs-subbtn b{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--rs-ink);font-weight:600;text-transform:uppercase}
.rs-header .rs-subbtn[aria-expanded="true"] .rs-caret{transform:rotate(180deg)}
.rs-header .rs-sublist{position:absolute;top:calc(100% + 2px);left:0;right:0;max-height:60vh;overflow-y:auto;margin:0;padding:0;background:var(--rs-surface);border-top:2px solid var(--rs-rule);border-bottom:2px solid var(--rs-rule);box-shadow:0 6px 0 var(--rs-rule)}
.rs-header .rs-sublist .rs-sec{height:auto;min-height:44px;padding:0 16px;border-bottom:1px solid var(--rs-rule-soft)}
.rs-header .rs-sublist .rs-sec.rs-active{box-shadow:inset 4px 0 0 var(--rs-accent)}
.rs-header .rs-progress{display:block;position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--rs-accent);transform:scaleX(0);transform-origin:0 50%;pointer-events:none}
.rs-header .rs-sheet{position:fixed;top:58px;overscroll-behavior:contain;left:0;right:0;bottom:0;overflow-y:auto;margin:0;padding:8px 16px 32px;background:var(--rs-paper);border-top:0;z-index:2}
.rs-header .rs-sheet a{display:flex;align-items:center;min-height:48px;padding:0 4px;border-bottom:1px solid var(--rs-rule-soft);color:var(--rs-ink);text-decoration:none;font:600 13px/1.2 var(--rs-mono);letter-spacing:.06em;text-transform:uppercase}
.rs-header .rs-sheet a[aria-current="page"]{color:var(--rs-accent);box-shadow:inset 4px 0 0 var(--rs-accent);padding-left:14px}
.rs-header .rs-sheet .rs-opt{align-items:flex-start;font:inherit;text-transform:none;letter-spacing:0;padding:8px 4px}
.rs-header .rs-sheet .rs-opt[aria-current="page"]{padding-left:14px}
.rs-header .rs-group{display:block;margin:24px 0 4px;font:500 12px/1 var(--rs-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--rs-muted)}
.rs-header .rs-sheet a.rs-sheet-author{margin-top:24px;border-top:2px solid var(--rs-rule);border-bottom:0;color:var(--rs-muted);text-transform:none;font-weight:500}
html.rs-lock,html.rs-lock body{overflow:hidden}
@media (max-width:1279.98px){.rs-header .rs-author{display:none}}
@media (max-width:1100px){.rs-header .rs-item{padding:0 10px}}
@media (min-width:1280px){.rs-header .rs-find{width:auto;padding:0 12px}.rs-header .rs-find span{display:block}.rs-header .rs-item{padding:0 12px}}
@media (max-width:959.98px){
 .rs-header .rs-row{padding:0 16px}
 .rs-header.rs-js .rs-nav,.rs-header.rs-js .rs-sep,.rs-header .rs-author{display:none}
 .rs-header.rs-js .rs-burger{display:inline-flex}
 .rs-header .rs-brand{margin-right:auto}
 .rs-header:not(.rs-js) .rs-nav{overflow-x:auto;margin-left:0}
 .rs-header.rs-js .rs-sublabel,.rs-header.rs-js .rs-subrow>.rs-sections{display:none}
 .rs-header.rs-js .rs-subbtn{display:flex}
}
@media (min-width:960px){.rs-header .rs-sheet,.rs-header .rs-sublist{display:none}}
/* programme search dialog (built by rs-header-js on first open) */
.rs-k,.rs-k :where(div,span,a,button,input,p,mark,kbd,b,svg){all:revert;box-sizing:border-box}
.rs-k{width:min(640px,100vw - 32px);max-width:none;max-height:min(76vh,680px);margin:10vh auto auto;padding:0;overflow:hidden;background:var(--rs-surface);color:var(--rs-ink);border:2px solid var(--rs-rule);box-shadow:8px 8px 0 var(--rs-rule);font:400 15px/1.4 var(--rs-sans)}
.rs-k[open]{display:flex;flex-direction:column}
.rs-k::backdrop{background:#0a0c108c}
.rs-k svg{flex:none;width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2}
.rs-k-top{display:flex;align-items:center;gap:10px;padding:0 8px 0 16px;border-bottom:2px solid var(--rs-rule);color:var(--rs-muted)}
.rs-k-top:focus-within{box-shadow:inset 0 -2px var(--rs-accent)}
.rs-k input{flex:1;min-width:0;height:56px;border:0;outline:0;background:none;color:var(--rs-ink);font:500 17px var(--rs-sans);appearance:none}
.rs-k input::placeholder{color:var(--rs-muted)}
.rs-k-x{min-width:44px;height:44px;padding:0 10px;background:none;color:var(--rs-muted);border:1px solid var(--rs-rule-soft);font:600 12px var(--rs-mono);text-transform:uppercase;cursor:pointer}
#rs-k-list{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding-bottom:8px}
#rs-k-list:empty{display:none}
.rs-k-g{padding:14px 16px 6px;font:600 12px var(--rs-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--rs-muted)}
.rs-k [role=option]{display:block;padding:9px 16px 9px 13px;border-left:3px solid transparent;color:var(--rs-ink);text-decoration:none}
.rs-k [role=option]:hover,.rs-k [aria-selected=true]{background:var(--rs-surface-2);border-color:var(--rs-accent)}
.rs-k-t{display:block;font-weight:500}
.rs-k-c{display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:13px;color:var(--rs-muted)}
.rs-k-c b{margin-right:6px;color:var(--rs-ink)}
.rs-k mark{background:none;color:inherit;font-weight:700;text-decoration:underline 2px var(--rs-accent);text-underline-offset:2px}
.rs-k-e{margin:0;padding:20px 16px;color:var(--rs-muted)}
.rs-k-f{margin:0;padding:10px 16px;border-top:1px solid var(--rs-rule-soft);font:500 12px var(--rs-mono);color:var(--rs-muted);word-spacing:6px}
.rs-k-f kbd{margin:0 4px 0 0;padding:2px 5px;border:1px solid var(--rs-rule-soft);font:inherit;word-spacing:0}
.rs-k-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.rs-k :focus-visible{outline:2px solid var(--rs-accent);outline-offset:-2px}
@media (max-width:640px){.rs-k{width:100%;height:100%;max-height:100%;margin:0;border:0;box-shadow:none}.rs-k-f{display:none}}
@media (prefers-reduced-motion:reduce){.rs-header *,.rs-header *::before,.rs-header *::after{transition:none!important}}
@media print{.rs-header,.rs-k{display:none!important}}
</style>"""

HEADER_JS = r"""<script id="rs-header-js">
(function(){
 var h=document.getElementById('rs-header');if(!h)return;
 var root=document.documentElement,doc=document;h.classList.add('rs-js');
 var mq=window.matchMedia?matchMedia('(prefers-color-scheme: dark)'):{matches:false};
 /* theme */
 var tb=doc.getElementById('rs-theme');
 function cur(){var t=root.getAttribute('data-theme');return t==='dark'||t==='light'?t:(mq.matches?'dark':'light');}
 /* a toggle button keeps one name ("Dark theme") and reports its state with aria-pressed;
    the tooltip says the action. A changing name on a pressed toggle reads as a contradiction. */
 function sync(){var d=cur()==='dark';tb.setAttribute('aria-pressed',d?'true':'false');tb.setAttribute('aria-label','Dark theme');tb.title=d?'Switch to light theme':'Switch to dark theme';}
 if(tb){tb.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';root.setAttribute('data-theme',n);
  try{localStorage.setItem('pc-theme',n);localStorage.setItem('ehs-ai-theme',n);}catch(e){}
  sync();try{doc.dispatchEvent(new CustomEvent('rs-themechange',{detail:{theme:n}}));}catch(e){}});
  sync();if(mq.addEventListener)mq.addEventListener('change',sync);
  /* other code (the story engine's theme API, a page script) may set data-theme too */
  if(window.MutationObserver)new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-theme']});}
 /* dropdowns */
 var menus=[].slice.call(h.querySelectorAll('.rs-menu'));
 function closeMenus(except){menus.forEach(function(m){if(m!==except&&m.open)m.open=false;});}
 menus.forEach(function(m){var s=m.querySelector('summary');s.setAttribute('aria-expanded','false');
  s.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();m.open=!m.open;}
   else if(e.key==='ArrowDown'){e.preventDefault();m.open=true;m.querySelector('a').focus();}});
  /* arrows move through an open menu; tabbing out closes it */
  m.addEventListener('keydown',function(e){var a=doc.activeElement,k=e.key,n=k==='ArrowDown'?'nextElementSibling':k==='ArrowUp'?'previousElementSibling':0;
   if(n&&a.parentNode.className==='rs-panel'&&a[n]){e.preventDefault();a[n].focus();}});
  m.addEventListener('focusout',function(e){if(!m.contains(e.relatedTarget))m.open=false;});
  m.addEventListener('toggle',function(){s.setAttribute('aria-expanded',m.open?'true':'false');if(m.open)closeMenus(m);});});
 /* the story link marks itself when it is this page */
 var sa=h.querySelector('a.rs-story');if(sa&&sa.href.split('#')[0]===location.href.split('#')[0])sa.setAttribute('aria-current','page');
 /* mobile sheet */
 var mb=doc.getElementById('rs-menu-btn'),sheet=doc.getElementById('rs-sheet');
 function focusables(){return [mb].concat([].slice.call(sheet.querySelectorAll('a[href]')));}
 function setSheet(open){if(!sheet)return;sheet.hidden=!open;mb.setAttribute('aria-expanded',open?'true':'false');
  mb.setAttribute('aria-label',open?'Close menu':'Open menu');root.classList.toggle('rs-lock',open);
  if(open){var f=sheet.querySelector('a[href]');if(f)f.focus();}}
 if(mb&&sheet){mb.addEventListener('click',function(){setSheet(sheet.hidden);});
  sheet.addEventListener('click',function(e){if(e.target.closest('a'))setSheet(false);});
  window.addEventListener('resize',function(){if(!sheet.hidden&&innerWidth>959)setSheet(false);});}
 /* sections */
 var sb=doc.getElementById('rs-subbtn'),sl=doc.getElementById('rs-sublist'),nav=doc.getElementById('rs-sections');
 function setSub(open){if(!sb)return;sl.hidden=!open;sb.setAttribute('aria-expanded',open?'true':'false');}
 if(sb){sb.addEventListener('click',function(){setSub(sl.hidden);});sl.addEventListener('click',function(e){if(e.target.closest('a'))setSub(false);});}
 doc.addEventListener('click',function(e){var t=e.target;if(!t.closest)return;
  if(!t.closest('.rs-menu'))closeMenus();if(sb&&!sl.hidden&&!t.closest('.rs-sub'))setSub(false);});
 doc.addEventListener('keydown',function(e){
  if(e.key==='Escape'){var o=menus.filter(function(m){return m.open;})[0];
   if(o){o.open=false;o.querySelector('summary').focus();return;}
   if(sheet&&!sheet.hidden){setSheet(false);mb.focus();return;}
   if(sb&&!sl.hidden){setSub(false);sb.focus();}return;}
  if(e.key==='Tab'&&sheet&&!sheet.hidden){var f=focusables(),i=f.indexOf(doc.activeElement);
   e.preventDefault();var n=f.length;f[i<0?0:(i+(e.shiftKey?n-1:1))%n].focus();}});
 var links=nav?[].slice.call(nav.querySelectorAll('a.rs-sec')):[],items=[];
 links.forEach(function(a){var el=doc.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));if(el)items.push({a:a,el:el,id:el.id});});
 var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches,active=null;
 function off(){return h.offsetHeight;}
 function fades(){if(!nav)return;var m=nav.scrollWidth-nav.clientWidth;nav.classList.toggle('rs-fl',nav.scrollLeft>2);nav.classList.toggle('rs-fr',m>2&&nav.scrollLeft<m-2);}
 function spy(){if(!items.length)return;var y=off()+24,pick=null;
  items.forEach(function(it){if(it.el.getBoundingClientRect().top<=y)pick=it;});
  if(!pick)pick=items[0];if(innerHeight+scrollY>=doc.documentElement.scrollHeight-2)pick=items[items.length-1];
  if(pick===active)return;active=pick;
  [].slice.call(h.querySelectorAll('a.rs-sec')).forEach(function(a){var on=a.getAttribute('href')==='#'+pick.id;a.classList.toggle('rs-active',on);if(on)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');});
  var now=doc.getElementById('rs-now');if(now)now.textContent=pick.a.textContent;
  if(nav.scrollWidth>nav.clientWidth){var l=pick.a.offsetLeft-(nav.clientWidth-pick.a.offsetWidth)/2;
   try{nav.scrollTo({left:l,behavior:reduce?'auto':'smooth'});}catch(e){nav.scrollLeft=l;}}}
 var bar=h.querySelector('.rs-progress'),ticking=false;
 function frame(){ticking=false;var max=doc.documentElement.scrollHeight-innerHeight;
  if(bar)bar.style.transform='scaleX('+(max>0?Math.min(1,Math.max(0,scrollY/max)):0)+')';spy();}
 function onScroll(){if(!ticking){ticking=true;requestAnimationFrame(frame);}}
 function pad(){root.style.setProperty('--rs-header-h',off()+'px');root.style.scrollPaddingTop=(off()+12)+'px';fades();}
 if(items.length&&'IntersectionObserver' in window){var io=new IntersectionObserver(onScroll,{rootMargin:'-'+off()+'px 0px -50% 0px'});items.forEach(function(it){io.observe(it.el);});}
 if(nav)nav.addEventListener('scroll',fades,{passive:true});
 addEventListener('scroll',onScroll,{passive:true});addEventListener('resize',function(){pad();onScroll();});
 pad();frame();
 /* programme search: / or Ctrl/Cmd+K; the index is fetched on first use */
 var fb=doc.getElementById('rs-find');if(!fb)return;
 var L=/^\/[^\/]+\/docs\//.test(location.pathname),G=['Pages','Findings','Papers','Tools','Terms'],RK='rs-search-recent',dl,inp,lst,msg,st,data,all,view=[],sel=0,back,moved,
 U=(r,f,a)=>'/'+r+'/'+(L?'docs/':'')+f+(a?'#'+a:''),
 esc=x=>String(x).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';'),
 rec=()=>{try{return JSON.parse(localStorage.getItem(RK))||[]}catch(e){return []}},
 load=()=>{data=data||fetch(U('grounded','search-index.json')).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{
  all=j.p.map(p=>({l:p[2],g:p[3],c:p[4],s:p[5],u:U(p[0],p[1])})).concat(j.i.map(i=>{var p=j.p[i[0]];return{l:i[2],g:i[3],c:p[4],s:i[4],u:U(p[0],p[1],i[1])}}));
  all.forEach(t=>{t.k=t.l.toLowerCase();t.x=(t.c+' '+(t.s||'')).toLowerCase()});dl&&dl.open&&render()},()=>{data=0;dl&&dl.open&&render(1)})},
 hl=(x,ws)=>{var l=x.toLowerCase(),m=[],o='',p=0;ws.forEach(w=>{for(var i=l.indexOf(w);i>-1;i=l.indexOf(w,i+w.length))m.push([i,i+w.length])});
  m.sort((a,b)=>a[0]-b[0]).forEach(r=>{if(r[0]>=p){o+=esc(x.slice(p,r[0]))+'<mark>'+esc(x.slice(r[0],r[1]))+'</mark>';p=r[1]}});return o+esc(x.slice(p))},
 mark=()=>{var os=lst.querySelectorAll('[role=option]'),c=os[sel];os.forEach((o,i)=>o.setAttribute('aria-selected',i==sel));
  c?(inp.setAttribute('aria-activedescendant',c.id),c.scrollIntoView({block:'nearest'})):inp.removeAttribute('aria-activedescendant')},
 render=err=>{var raw=inp.value.trim(),q=raw.toLowerCase(),ws=q.split(/\s+/).filter(Boolean),gs=[],h='',r,b;view=[];
  if(!q){r=rec();r.length&&gs.push(['Recent',r]);all&&gs.push(['All pages',all.filter(t=>t.u.indexOf('#')<0)])}
  else if(all){b=G.map(()=>[]);
   all.forEach(t=>{var s=0;for(var w of ws){var j=t.k.indexOf(w);if(j<0){if(t.x.indexOf(w)<0)return;s++}else s+=j&&/[a-z0-9]/.test(t.k[j-1])?3:6}
    t.sc=s+(t.k.indexOf(q)?0:5)-t.l.length/300;b[t.g].push(t)});
   b.forEach((a,g)=>a.length&&gs.push([G[g],a.sort((x,y)=>y.sc-x.sc).slice(0,g==1?8:5)]));gs.sort((x,y)=>y[1][0].sc-x[1][0].sc)}
  gs.forEach((g,n)=>{h+='<div role="group" aria-labelledby="rs-kg'+n+'"><div class="rs-k-g" id="rs-kg'+n+'">'+g[0]+'</div>';
   g[1].forEach(t=>{h+='<a role="option" tabindex="-1" id="rs-ko'+view.length+'" href="'+esc(t.u)+'"><span class="rs-k-t">'+hl(t.l,ws)+'</span><span class="rs-k-c"><b>'+esc(t.c)+'</b>'+hl(t.s||'',ws)+'</span></a>';view.push(t)});h+='</div>'});
  lst.innerHTML=h;sel=0;mark();inp.setAttribute('aria-expanded',!!view.length);
  msg.innerHTML=err?'Search is unavailable. Use the Projects and Papers menus.':all?q&&!view.length?'No match for “'+esc(raw)+'”. Try TRIR, hours, grounding or payback.':'':'Loading…';
  msg.hidden=!msg.innerHTML;st.textContent=q&&all?view.length+' results':''},
 shut=()=>{moved=0;dl.open&&dl.close()},
 go=(t,tab)=>{if(!t)return;var r=rec().filter(x=>x.u!=t.u),a=doc.createElement('a'),e;r.unshift({l:t.l,c:t.c,s:t.s,u:t.u});
  try{localStorage.setItem(RK,JSON.stringify(r.slice(0,6)))}catch(x){}
  if(tab)return open(t.u,'_blank','noopener');
  a.href=t.u;e=a.hash&&doc.getElementById(decodeURIComponent(a.hash.slice(1)));moved=1;dl.close();
  if(e&&a.pathname.replace(/index\.html$/,'')==location.pathname.replace(/index\.html$/,'')){location.hash==a.hash?e.scrollIntoView():location.hash=a.hash;e.hasAttribute('tabindex')||e.setAttribute('tabindex','-1');e.focus({preventScroll:true})}
  else location.href=t.u},
 build=()=>{dl=doc.createElement('dialog');dl.className='rs-k';dl.setAttribute('aria-label','Search the research');
  dl.innerHTML='<div class="rs-k-top">'+fb.querySelector('svg').outerHTML+'<input type="text" role="combobox" aria-label="Search the research" aria-expanded="false" aria-controls="rs-k-list" aria-autocomplete="list" aria-describedby="rs-k-help" placeholder="Search findings, papers, tools, terms" autocomplete="off" spellcheck="false" enterkeyhint="go"><button type="button" class="rs-k-x">Close</button></div><div id="rs-k-list" role="listbox" aria-label="Results"></div><p class="rs-k-e"></p><p class="rs-k-f" id="rs-k-help"><kbd>↑↓</kbd>move <kbd>Enter</kbd>open <kbd>Esc</kbd>close</p><p class="rs-k-sr" role="status"></p>';
  doc.body.append(dl);[inp,lst,msg,st]=['input','#rs-k-list','.rs-k-e','.rs-k-sr'].map(s=>dl.querySelector(s));
  inp.oninput=()=>render();
  inp.onkeydown=e=>{var k=e.key,n=view.length;
   if(k=='ArrowDown'||k=='ArrowUp'){e.preventDefault();if(n){sel=(sel+(k[5]=='D'?1:n-1))%n;mark()}}
   else if(k=='Enter'){e.preventDefault();go(view[sel],e.metaKey||e.ctrlKey)}
   else if(k=='Escape'){e.preventDefault();inp.value?(inp.value='',render()):shut()}};
  lst.onclick=e=>{var o=e.target.closest('[role=option]');if(o){e.preventDefault();go(view[o.id.slice(5)],e.metaKey||e.ctrlKey||e.shiftKey)}};
  dl.onclick=e=>{if(e.target==dl||e.target.className=='rs-k-x')shut()};
  dl.onclose=()=>{moved||back&&back.focus&&back.focus()}},
 show=()=>{dl||build();if(!dl.open){back=doc.activeElement;moved=0;inp.value='';load();render();dl.showModal();inp.focus()}};
 fb.onclick=show;
 doc.addEventListener('keydown',e=>{var t=e.target||{},k=e.key||'';if(root.classList.contains('st-presenting')||e.altKey)return;
  if(k.toLowerCase()=='k'&&(e.metaKey||e.ctrlKey)){e.preventDefault();dl&&dl.open?shut():show()}
  else if(k=='/'&&!e.metaKey&&!e.ctrlKey&&!/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)&&!t.isContentEditable&&!doc.querySelector('dialog[open]')){e.preventDefault();show()}});
})();
</script>"""


def _compact(src, css=False):
    """Drop comments that start a line and the indentation. Deterministic and ASI-safe:
    JS keeps its line breaks; CSS joins lines. The readable source above stays the reference."""
    src = re.sub(r"(?m)^[ \t]*/\*.*?\*/[ \t]*\n", "", src, flags=re.S)
    if not css:  # anonymous functions here never use this/arguments, so arrows are equivalent
        src = re.sub(r"\bfunction\(([\w,]*)\)\{", r"(\1)=>{", src)
    lines = [ln.strip() for ln in src.split("\n")]
    return ("" if css else "\n").join(ln for ln in lines if ln)


HEADER_CSS = _compact(HEADER_CSS, css=True)
HEADER_JS = _compact(HEADER_JS)


def _current_from(current, current_project, current_paper, is_hub):
    if current:
        return current
    if current_project:
        return current_project
    if current_paper:
        return current_paper
    return "hub" if is_hub else None


def build_header(current=None, sections=None, story_href=None):
    """Return the header markup. sections: list of (id, label) or None/[].

    story_href, when given, adds one marked link in the primary row that takes
    the reader to that page's narrative walkthrough.
    """
    sections = list(sections or [])
    proj_cur = any(current == s for s, _, _ in PROJECTS)
    pap_cur = any(current == f for f, _, _ in PAPERS)

    def aria(flag):
        return ' aria-current="page"' if flag else ""

    def opts(rows, href):
        return "".join('<a class="rs-opt" href="%s"%s><span class="rs-t">%s</span><span class="rs-n">%s</span></a>'
                       % (href(k), aria(k == current), _E(t), _E(n)) for k, t, n in rows)
    proj = opts(PROJECTS, lambda s: "https://priyatham9.github.io/%s/" % s)
    paps = opts(PAPERS, lambda f: HUB + f)
    prim = "".join('<a class="rs-item" href="%s"%s>%s</a>' % (u, aria(k == current), l) for k, l, u in PRIMARY)
    story = ('<a class="rs-item rs-story" href="%s">Read the story</a>' % _E(story_href, quote=True)) if story_href else ""
    caret = '<span class="rs-caret" aria-hidden="true"></span>'

    def menu(label, body, cur):
        return ('<details class="rs-menu"%s><summary class="rs-item" aria-haspopup="true">%s%s</summary>'
                '<div class="rs-panel">%s</div></details>' % (' data-current="true"' if cur else "", label, caret, body))

    row1 = (
        '<div class="rs-bar"><div class="rs-row">'
        '<a class="rs-brand" href="%s"%s><span class="rs-mark" aria-hidden="true"></span>Grounded</a>'
        '<a class="rs-author" href="%s">Priyatham Chimmani&nbsp;&#8599;</a>'
        '<nav class="rs-nav" aria-label="Research site">%s%s%s%s</nav>'
        '<span class="rs-sep" aria-hidden="true"></span>'
        '<button class="rs-btn rs-find" id="rs-find" type="button" aria-haspopup="dialog" aria-keyshortcuts="Control+K Meta+K /" '
        'aria-label="Search the research" title="Search (/ or Ctrl+K)">%s<span>Search</span></button>'
        '<button class="rs-btn" id="rs-theme" type="button" aria-label="Dark theme" aria-pressed="false" title="Switch colour theme">%s%s</button>'
        '<button class="rs-btn rs-burger" id="rs-menu-btn" type="button" aria-expanded="false" aria-controls="rs-sheet" aria-label="Open menu"><i></i></button>'
        '</div></div>' % (HUB, ' aria-label="Grounded research hub"', PERSONAL, prim,
                          menu("Projects", proj, proj_cur), menu("Papers", paps, pap_cur), story, _FIND, _SUN, _MOON))
    sheet = ('<div class="rs-sheet" id="rs-sheet" hidden>%s%s'
             '<span class="rs-group">Projects</span>%s<span class="rs-group">Papers</span>%s'
             '<a class="rs-sheet-author" href="%s">Priyatham Chimmani&nbsp;&#8599;</a></div>'
             % (prim, story, proj, paps, PERSONAL))
    row2 = ""
    if sections:
        secs = "".join('<a class="rs-sec" href="#%s">%s</a>' % (_E(i, quote=True), _E(l)) for i, l in sections)
        row2 = ('<div class="rs-sub"><div class="rs-row rs-subrow">'
                '<span class="rs-sublabel">On this page</span>'
                '<nav class="rs-sections" id="rs-sections" aria-label="On this page">%s</nav>'
                '<button class="rs-subbtn" id="rs-subbtn" type="button" aria-expanded="false" aria-controls="rs-sublist">'
                'On this page:<b id="rs-now">%s</b>%s</button></div>'
                '<nav class="rs-sublist" id="rs-sublist" aria-label="On this page (list)" hidden>%s</nav></div>'
                % (secs, _E(sections[0][1]), caret, secs))
    return ('<header class="rs-header" id="rs-header">%s%s%s<span class="rs-progress" aria-hidden="true"></span></header>'
            % (row1, row2, sheet))


# ---------------------------------------------------------------- page surgery

def _text(fragment):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def _detect_sections(page):
    # A page that ships its own table of contents names each section twice: a
    # spelled-out label for the rail and a short one for this single-line strip.
    # A page with its own contents rail (<aside class="toc">) gets no second strip:
    # two stacked section navs read as a duplicated breadcrumb and eat phone height.
    if re.search(r'<aside\b[^>]*class="[^"]*\btoc\b', page):
        return []
    short = re.findall(r'<a\b[^>]*href="#([^"]+)"[^>]*\bdata-short="([^"]*)"', page)
    if short:
        out = []
        for href, label in short:
            label = _html.unescape(label).strip()
            if label and (href, label) not in out:
                out.append((_html.unescape(href), label))
        if out:
            return out
    m = (re.search(r'<nav\b[^>]*\bid="(?:sectionNav|rs-sections)"[^>]*>(.*?)</nav>', page, re.S)
         or re.search(r'<nav\b[^>]*class="[^"]*\b(?:topnav|gbar-sections)\b[^"]*"[^>]*>(.*?)</nav>', page, re.S))
    if m:
        out = []
        for href, inner in re.findall(r'<a\b[^>]*href="#([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
            inner = re.sub(r'<span[^>]*class="[^"]*topnav-n[^"]*"[^>]*>.*?</span>', "", inner, flags=re.S)
            label = _text(inner)
            if label and (href, label) not in out:
                out.append((_html.unescape(href), label))
        if out:
            return out
    out = []
    for sid, body in re.findall(r'<section\b[^>]*\bid="([^"]+)"[^>]*>(.*?)(?=<section\b|</main>|</body>)', page, re.S):
        h2 = re.search(r"<h2\b[^>]*>(.*?)</h2>", body, re.S)
        if h2 and _text(h2.group(1)):
            out.append((sid, _text(h2.group(1))))
    return out if len(out) >= 2 else []


_OLD_SEL = re.compile(r"\.gbar|\.estate\b")


def _split_top(s, ch):
    parts, depth, buf, q = [], 0, "", None
    for c in s:
        if q:
            buf += c
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == ch and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += c
    parts.append(buf)
    return parts


def _strip_old_css(css):
    """Remove selectors containing .gbar / .estate; keep everything else verbatim."""
    out, i, n = [], 0, len(css)
    while i < n:
        j, q = i, None
        stop = None
        while j < n:
            c = css[j]
            if q:
                if c == "\\":
                    j += 2
                    continue
                if c == q:
                    q = None
            elif css.startswith("/*", j):
                k = css.find("*/", j + 2)
                j = n if k < 0 else k + 2
                continue
            elif c in "\"'":
                q = c
            elif c in "{;}":
                stop = c
                break
            j += 1
        if stop is None:
            out.append(css[i:])
            break
        if stop in ";}":
            out.append(css[i:j + 1])
            i = j + 1
            continue
        depth, k, q = 1, j + 1, None
        while k < n and depth:
            c = css[k]
            if q:
                if c == "\\":
                    k += 2
                    continue
                if c == q:
                    q = None
            elif css.startswith("/*", k):
                e = css.find("*/", k + 2)
                k = n if e < 0 else e + 2
                continue
            elif c in "\"'":
                q = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        prelude, body = css[i:j], css[j + 1:k - 1]
        bare = re.sub(r"/\*.*?\*/", "", prelude, flags=re.S).strip()
        if bare.startswith("@media") or bare.startswith("@supports"):
            inner = _strip_old_css(body)
            if re.sub(r"/\*.*?\*/", "", inner, flags=re.S).strip():
                out.append(prelude + "{" + inner + "}")
        elif bare.startswith("@"):
            out.append(css[i:k])
        else:
            sels = [s for s in _split_top(bare, ",") if s.strip()]
            keep = [s for s in sels if not _OLD_SEL.search(s)]
            if len(keep) == len(sels):
                out.append(css[i:k])
            elif keep:
                lead = prelude[:len(prelude) - len(prelude.lstrip())]
                out.append(lead + ",".join(s.strip() for s in keep) + "{" + body + "}")
        i = k
    return "".join(out)


def apply_banner(html, current=None, sections=None, current_project=None,
                 current_paper=None, is_hub=False, story_href=None):
    current = _current_from(current, current_project, current_paper, is_hub)
    if sections is None:
        sections = _detect_sections(html)
    # 1. remove previous header generations and injected assets
    html = re.sub(r'\s*<header\b[^>]*class="[^"]*\b(?:gbar|topbar|rs-header)\b[^"]*"[^>]*>.*?</header>', "", html, flags=re.S)
    html = re.sub(r'\s*<div class="estate"[^>]*>.*?</div>', "", html, flags=re.S)
    html = re.sub(r'<(style|script) id="(?:rs-header-css|rs-header-js|rs-theme-init)">.*?</\1>', "", html, flags=re.S)
    html = re.sub(r"/\* ---- shared banner ---- \*/.*?@media print\{\.gbar\{display:none\}\}\n?", "", html, flags=re.S)
    # only the exact old banner.JS block (short, gbar-menu + getElementById('gbar')); page scripts are never removed
    html = re.sub(r"\s*<script>(?:(?!</script>).){0,1200}</script>",
                  lambda m: "" if ("querySelectorAll('.gbar-menu')" in m.group(0) and "getElementById('gbar')" in m.group(0)
                                   and "themeToggle" not in m.group(0)) else m.group(0), html, flags=re.S)
    html = re.sub(r"(<style\b[^>]*>)(.*?)(</style>)",
                  lambda m: m.group(1) + _strip_old_css(m.group(2)) + m.group(3), html, flags=re.S)
    # 2. inject
    head_bits = HEAD_THEME_SNIPPET + HEADER_CSS
    if "</head>" in html:
        html = html.replace("</head>", head_bits + "</head>", 1)
    else:
        mh = re.search(r"<head\b[^>]*>", html) or re.search(r"<html\b[^>]*>", html)
        html = (html[:mh.end()] + head_bits + html[mh.end():]) if mh else head_bits + html
    header = build_header(current, sections, story_href=story_href)
    # keep a leading skip link ("<a class=\"skip\" ...>") as the first focusable element
    mb = re.search(r"<body\b[^>]*>(?:\s*<a\b[^>]*class=\"[^\"]*\bskip(?:-link)?\b[^\"]*\"[^>]*>.*?</a>)?", html, re.S)
    if not mb:
        # no <body> tag: never put the header before <html>/<head>. Insert it where the
        # implied body starts: after </head>, else after <html ...>, else after the doctype.
        mb = (re.search(r"</head\s*>", html, re.I) or re.search(r"<html\b[^>]*>", html, re.I)
              or re.search(r"<!doctype[^>]*>", html, re.I))
    html = (html[:mb.end()] + header + html[mb.end():]) if mb else header + html
    idx = html.rfind("</body>")
    html = (html[:idx] + HEADER_JS + html[idx:]) if idx >= 0 else html + HEADER_JS
    return html
