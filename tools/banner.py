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
_MOON = ('<svg class="rs-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
         '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>')

HEADER_CSS = r"""<style id="rs-header-css">
.rs-header{
 --rs-paper:var(--paper,#F7F7F3);--rs-surface:var(--surface,#FFFFFF);--rs-surface-2:var(--surface-2,#EFEFE9);
 --rs-ink:var(--ink,#101311);--rs-muted:var(--muted,var(--ink-2,#5E655F));--rs-rule:var(--rule,#101311);
 --rs-rule-soft:var(--rule-soft,#D6D7CE);--rs-accent:var(--accent,#1E40AF);
 --rs-mono:var(--font-mono,"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace);
 --rs-sans:var(--font-sans,"Archivo",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif);
}
:root[data-theme="dark"] .rs-header{
 --rs-paper:var(--paper,#0A0C10);--rs-surface:var(--surface,#12151C);--rs-surface-2:var(--surface-2,#171B24);
 --rs-ink:var(--ink,#EAECF2);--rs-muted:var(--muted,var(--ink-2,#959CAB));--rs-rule:var(--rule,#EAECF2);
 --rs-rule-soft:var(--rule-soft,#2C3240);--rs-accent:var(--accent,#7C9EFF);
}
@media (prefers-color-scheme:dark){:root:not([data-theme]) .rs-header{
 --rs-paper:var(--paper,#0A0C10);--rs-surface:var(--surface,#12151C);--rs-surface-2:var(--surface-2,#171B24);
 --rs-ink:var(--ink,#EAECF2);--rs-muted:var(--muted,var(--ink-2,#959CAB));--rs-rule:var(--rule,#EAECF2);
 --rs-rule-soft:var(--rule-soft,#2C3240);--rs-accent:var(--accent,#7C9EFF);
}}
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
.rs-header .rs-author{display:flex;align-items:center;height:24px;padding:0 0 0 16px;border-left:2px solid var(--rs-rule-soft);font:500 11px/1 var(--rs-mono);letter-spacing:.06em;color:var(--rs-muted);text-decoration:none;white-space:nowrap}
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
.rs-header .rs-n{display:block;font:400 11px/1.2 var(--rs-mono);letter-spacing:.04em;color:var(--rs-muted)}
.rs-header .rs-opt[aria-current="page"] .rs-n::after{content:" \00B7  you are here";color:var(--rs-accent)}
.rs-header .rs-sep{display:block;width:2px;height:24px;margin:0 12px 0 10px;background:var(--rs-rule-soft);flex:none}
.rs-header .rs-btn{display:inline-flex;align-items:center;justify-content:center;flex:none;width:40px;height:40px;margin:0;padding:0;background:var(--rs-paper);color:var(--rs-ink);border:2px solid var(--rs-rule);border-radius:0;cursor:pointer;font:600 11px/1 var(--rs-mono)}
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
.rs-header .rs-sublabel{display:block;flex:none;padding:0 12px 0 0;font:500 11px/1 var(--rs-mono);letter-spacing:.06em;color:var(--rs-muted);white-space:nowrap}
.rs-header .rs-sections{display:flex;align-items:center;position:relative;flex:1 1 auto;min-width:0;height:44px;margin:0;padding:0;overflow-x:auto;scrollbar-width:none}
.rs-header .rs-sections::-webkit-scrollbar{display:none}
.rs-header .rs-sections.rs-fl{-webkit-mask-image:linear-gradient(90deg,transparent,#000 32px);mask-image:linear-gradient(90deg,transparent,#000 32px)}
.rs-header .rs-sections.rs-fr{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent)}
.rs-header .rs-sections.rs-fl.rs-fr{-webkit-mask-image:linear-gradient(90deg,transparent,#000 32px,#000 calc(100% - 32px),transparent);mask-image:linear-gradient(90deg,transparent,#000 32px,#000 calc(100% - 32px),transparent)}
.rs-header .rs-sec{display:flex;align-items:center;flex:none;height:44px;padding:0 10px;font:600 11px/1 var(--rs-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--rs-muted);text-decoration:none;white-space:nowrap}
.rs-header .rs-sec:hover{color:var(--rs-ink)}
.rs-header .rs-sec.rs-active{color:var(--rs-accent);box-shadow:inset 0 -2px 0 var(--rs-accent)}
.rs-header .rs-subbtn{display:none;align-items:center;gap:8px;width:100%;height:44px;margin:0;padding:0;background:transparent;border:0;color:var(--rs-muted);font:500 11px/1 var(--rs-mono);letter-spacing:.06em;cursor:pointer;text-align:left}
.rs-header .rs-subbtn b{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--rs-ink);font-weight:600;text-transform:uppercase}
.rs-header .rs-subbtn[aria-expanded="true"] .rs-caret{transform:rotate(180deg)}
.rs-header .rs-sublist{position:absolute;top:calc(100% + 2px);left:0;right:0;max-height:60vh;overflow-y:auto;margin:0;padding:0;background:var(--rs-surface);border-top:2px solid var(--rs-rule);border-bottom:2px solid var(--rs-rule);box-shadow:0 6px 0 var(--rs-rule)}
.rs-header .rs-sublist .rs-sec{height:auto;min-height:44px;padding:0 16px;border-bottom:1px solid var(--rs-rule-soft)}
.rs-header .rs-sublist .rs-sec.rs-active{box-shadow:inset 4px 0 0 var(--rs-accent)}
.rs-header .rs-progress{display:block;position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--rs-accent);transform:scaleX(0);transform-origin:0 50%;pointer-events:none}
.rs-header .rs-sheet{position:fixed;top:58px;left:0;right:0;bottom:0;overflow-y:auto;margin:0;padding:8px 16px 32px;background:var(--rs-paper);border-top:0;z-index:2}
.rs-header .rs-sheet a{display:flex;align-items:center;min-height:48px;padding:0 4px;border-bottom:1px solid var(--rs-rule-soft);color:var(--rs-ink);text-decoration:none;font:600 13px/1.2 var(--rs-mono);letter-spacing:.06em;text-transform:uppercase}
.rs-header .rs-sheet a[aria-current="page"]{color:var(--rs-accent);box-shadow:inset 4px 0 0 var(--rs-accent);padding-left:14px}
.rs-header .rs-sheet .rs-opt{align-items:flex-start;font:inherit;text-transform:none;letter-spacing:0;padding:8px 4px}
.rs-header .rs-sheet .rs-opt[aria-current="page"]{padding-left:14px}
.rs-header .rs-group{display:block;margin:24px 0 4px;font:500 11px/1 var(--rs-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--rs-muted)}
.rs-header .rs-sheet a.rs-sheet-author{margin-top:24px;border-top:2px solid var(--rs-rule);border-bottom:0;color:var(--rs-muted);text-transform:none;font-weight:500}
html.rs-lock,html.rs-lock body{overflow:hidden}
@media (max-width:1040px){.rs-header .rs-author{display:none}.rs-header .rs-item{padding:0 11px}}
@media (max-width:860px){
 .rs-header .rs-row{padding:0 16px}
 .rs-header.rs-js .rs-nav,.rs-header.rs-js .rs-sep,.rs-header .rs-author{display:none}
 .rs-header.rs-js .rs-burger{display:inline-flex}
 .rs-header .rs-brand{margin-right:auto}
 .rs-header:not(.rs-js) .rs-nav{overflow-x:auto;margin-left:0}
 .rs-header.rs-js .rs-sublabel,.rs-header.rs-js .rs-subrow>.rs-sections{display:none}
 .rs-header.rs-js .rs-subbtn{display:flex}
}
@media (min-width:861px){.rs-header .rs-sheet,.rs-header .rs-sublist{display:none}}
@media (prefers-reduced-motion:reduce){.rs-header *,.rs-header *::before,.rs-header *::after{transition:none!important}}
@media print{.rs-header{display:none!important}}
</style>"""

HEADER_JS = r"""<script id="rs-header-js">
(function(){
 var h=document.getElementById('rs-header');if(!h)return;
 var root=document.documentElement,doc=document;h.classList.add('rs-js');
 var mq=window.matchMedia?matchMedia('(prefers-color-scheme: dark)'):{matches:false};
 /* theme */
 var tb=doc.getElementById('rs-theme');
 function cur(){var t=root.getAttribute('data-theme');return t==='dark'||t==='light'?t:(mq.matches?'dark':'light');}
 function sync(){var d=cur()==='dark';tb.setAttribute('aria-pressed',d?'true':'false');tb.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme');}
 if(tb){tb.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';root.setAttribute('data-theme',n);
  try{localStorage.setItem('pc-theme',n);localStorage.setItem('ehs-ai-theme',n);}catch(e){}
  sync();try{doc.dispatchEvent(new CustomEvent('rs-themechange',{detail:{theme:n}}));}catch(e){}});
  sync();if(mq.addEventListener)mq.addEventListener('change',sync);}
 /* dropdowns */
 var menus=[].slice.call(h.querySelectorAll('.rs-menu'));
 function closeMenus(except){menus.forEach(function(m){if(m!==except&&m.open)m.open=false;});}
 menus.forEach(function(m){var s=m.querySelector('summary');s.setAttribute('aria-expanded','false');
  s.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();m.open=!m.open;}});
  m.addEventListener('toggle',function(){s.setAttribute('aria-expanded',m.open?'true':'false');if(m.open)closeMenus(m);});});
 /* mobile sheet */
 var mb=doc.getElementById('rs-menu-btn'),sheet=doc.getElementById('rs-sheet');
 function focusables(){return [mb].concat([].slice.call(sheet.querySelectorAll('a[href]')));}
 function setSheet(open){if(!sheet)return;sheet.hidden=!open;mb.setAttribute('aria-expanded',open?'true':'false');
  mb.setAttribute('aria-label',open?'Close menu':'Open menu');root.classList.toggle('rs-lock',open);
  if(open){var f=sheet.querySelector('a[href]');if(f)f.focus();}}
 if(mb&&sheet){mb.addEventListener('click',function(){setSheet(sheet.hidden);});
  sheet.addEventListener('click',function(e){if(e.target.closest('a'))setSheet(false);});
  window.addEventListener('resize',function(){if(!sheet.hidden&&innerWidth>860)setSheet(false);});}
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
 function pad(){root.style.scrollPaddingTop=(off()+12)+'px';fades();}
 if(items.length&&'IntersectionObserver' in window){var io=new IntersectionObserver(onScroll,{rootMargin:'-'+off()+'px 0px -50% 0px'});items.forEach(function(it){io.observe(it.el);});}
 if(nav)nav.addEventListener('scroll',fades,{passive:true});
 addEventListener('scroll',onScroll,{passive:true});addEventListener('resize',function(){pad();onScroll();});
 pad();frame();
})();
</script>"""


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
        '<button class="rs-btn" id="rs-theme" type="button" aria-label="Toggle colour theme">%s%s</button>'
        '<button class="rs-btn rs-burger" id="rs-menu-btn" type="button" aria-expanded="false" aria-controls="rs-sheet" aria-label="Open menu"><i></i></button>'
        '</div></div>' % (HUB, ' aria-label="Grounded research hub"', PERSONAL, prim,
                          menu("Projects", proj, proj_cur), menu("Papers", paps, pap_cur), story, _SUN, _MOON))
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
