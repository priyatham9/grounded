/* charts.js - inline SVG line and bar charts from inline JSON.
   No dependencies. Colours come from CSS variables so both themes work.
   Usage: <figure class="chart" data-chart='{...}'>, then GCharts.init().
   spec = {type:"line"|"bar", x:[labels], series:[{name, values, tip?}], y:{min,max,ticks,fmt}, aspect}
*/
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var W = 720, PAD = { l: 52, r: 16, t: 14, b: 34 };
  var COL = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)'];

  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function txt(x, y, s, anchor, size, fill) {
    var t = el('text', { x: x, y: y, 'text-anchor': anchor || 'start', 'font-size': size || 11, fill: fill || 'var(--fig-axis)' });
    t.textContent = s; return t;
  }
  function fmtv(v, f) {
    if (f === 'pct') return (v * 100).toFixed(1) + '%';
    if (f === 'int') return Math.round(v).toLocaleString();
    if (typeof f === 'number') return v.toFixed(f);
    return Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
  }
  function niceTicks(lo, hi, n) {
    var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / n)));
    var m = [1, 2, 2.5, 5, 10], best = step;
    for (var i = 0; i < m.length; i++) { if (span / (step * m[i]) <= n) { best = step * m[i]; break; } }
    var a = Math.floor(lo / best) * best, out = [];
    for (var v = a; v <= hi + best * 0.5; v += best) out.push(+v.toFixed(10));
    return out;
  }

  function render(fig) {
    var spec; try { spec = JSON.parse(fig.getAttribute('data-chart')); } catch (e) { return; }
    var H = Math.round(W / (spec.aspect || 2.2));
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': spec.title || 'chart', 'font-family': "'IBM Plex Mono', ui-monospace, Menlo, monospace" });
    el('rect', { x: 0, y: 0, width: W, height: H, fill: 'var(--fig-paper)' }, svg);
    var all = [];
    spec.series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) all.push(v); }); });
    var lo = spec.y && spec.y.min != null ? spec.y.min : Math.min.apply(null, all.concat([0]));
    var hi = spec.y && spec.y.max != null ? spec.y.max : Math.max.apply(null, all);
    if (hi === lo) hi = lo + 1;
    var ticks = (spec.y && spec.y.ticks) || niceTicks(lo, hi, 5);
    lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
    var iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b;
    var ny = function (v) { return PAD.t + ih - (v - lo) / (hi - lo) * ih; };
    var nx = spec.x.length;
    var fmt = spec.y && spec.y.fmt;

    ticks.forEach(function (t) {
      var y = ny(t);
      el('line', { x1: PAD.l, x2: W - PAD.r, y1: y, y2: y, stroke: 'var(--fig-grid)', 'stroke-width': 1 }, svg);
      svg.appendChild(txt(PAD.l - 8, y + 4, fmtv(t, fmt), 'end', 10, 'var(--fig-mute)'));
    });
    el('line', { x1: PAD.l, x2: W - PAD.r, y1: PAD.t + ih, y2: PAD.t + ih, stroke: 'var(--fig-axis)', 'stroke-width': 2 }, svg);
    if (spec.ref != null) {
      el('line', { x1: PAD.l, x2: W - PAD.r, y1: ny(spec.ref), y2: ny(spec.ref), stroke: 'var(--fig-axis)', 'stroke-dasharray': '4 4' }, svg);
      if (spec.refLabel) svg.appendChild(txt(W - PAD.r, ny(spec.ref) - 5, spec.refLabel, 'end', 10, 'var(--fig-mute)'));
    }

    var tip = document.createElement('div'); tip.className = 'chart-tip'; tip.hidden = true;
    function show(node, html) {
      var wrap = fig.querySelector('.chart-body') || fig;
      tip.innerHTML = html; tip.hidden = false;
      var r = node.getBoundingClientRect(), w = wrap.getBoundingClientRect();
      tip.style.left = Math.max(0, Math.min(r.left - w.left + r.width / 2, w.width - tip.offsetWidth)) + 'px';
      tip.style.top = (r.top - w.top - tip.offsetHeight - 8) + 'px';
    }
    function hide() { tip.hidden = true; }
    function attach(node, html) {
      node.setAttribute('tabindex', '0'); node.setAttribute('role', 'img'); node.setAttribute('aria-label', html.replace(/<[^>]+>/g, ' '));
      node.addEventListener('mouseenter', function () { show(node, html); });
      node.addEventListener('focus', function () { show(node, html); });
      node.addEventListener('mouseleave', hide); node.addEventListener('blur', hide);
    }

    if (spec.type === 'bar') {
      var ns = spec.series.length, slot = iw / nx, bw = Math.min(56, slot * 0.7 / ns);
      spec.series.forEach(function (s, si) {
        s.values.forEach(function (v, i) {
          if (v == null) return;
          var x = PAD.l + slot * i + slot / 2 - (bw * ns) / 2 + bw * si;
          var y = ny(Math.max(v, lo)), h = Math.max(1, ny(lo) - y);
          var r = el('rect', { x: x, y: y, width: bw - 2, height: h, fill: COL[si % 4], class: 'chart-bar' }, svg);
          attach(r, '<b>' + spec.x[i] + '</b><br>' + s.name + ': ' + fmtv(v, fmt) + (s.tip && s.tip[i] ? '<br>' + s.tip[i] : ''));
        });
      });
    } else {
      var step = nx > 1 ? iw / (nx - 1) : 0;
      spec.series.forEach(function (s, si) {
        var d = '';
        s.values.forEach(function (v, i) { if (v == null) return; d += (d ? ' L' : 'M') + (PAD.l + step * i).toFixed(1) + ' ' + ny(v).toFixed(1); });
        var ln = el('path', { d: d, fill: 'none', stroke: COL[si % 4], 'stroke-width': 2.5, 'stroke-linejoin': 'round', class: 'chart-line' }, svg);
        drawLine(fig, ln, si);
        s.values.forEach(function (v, i) {
          if (v == null) return;
          var c = el('circle', { cx: PAD.l + step * i, cy: ny(v), r: 4.5, fill: 'var(--fig-paper)', stroke: COL[si % 4], 'stroke-width': 2.5, class: 'chart-pt' }, svg);
          attach(c, '<b>' + spec.x[i] + '</b><br>' + s.name + ': ' + fmtv(v, fmt) + (s.tip && s.tip[i] ? '<br>' + s.tip[i] : ''));
        });
      });
    }
    var every = Math.ceil(nx / 12);
    spec.x.forEach(function (lab, i) {
      if (i % every) return;
      var x = spec.type === 'bar' ? PAD.l + iw / nx * i + iw / nx / 2 : PAD.l + (nx > 1 ? iw / (nx - 1) : 0) * i;
      svg.appendChild(txt(x, H - 10, lab, 'middle', 10, 'var(--fig-mute)'));
    });

    var body = document.createElement('div'); body.className = 'chart-body';
    body.appendChild(svg); body.appendChild(tip);
    var slot2 = fig.querySelector('.chart-slot');
    var prev = fig.querySelector(':scope > .chart-body');
    if (slot2) slot2.replaceWith(body); else if (prev) prev.replaceWith(body); else fig.appendChild(body);
    var oldLg = body.nextElementSibling;
    while (oldLg && oldLg.classList.contains('fig-legend')) { var nx2 = oldLg.nextElementSibling; oldLg.remove(); oldLg = nx2; }
    if (spec.series.length > 1) {
      var lg = document.createElement('div'); lg.className = 'fig-legend';
      spec.series.forEach(function (s, i) { var sp = document.createElement('span'); sp.innerHTML = '<i style="background:' + COL[i % 4] + '"></i>' + s.name; lg.appendChild(sp); });
      body.after(lg);
    }
  }

  // anime-style SVG line draw: each series strokes itself in the first time
  // the figure scrolls into view; theme re-renders and reduced motion land drawn.
  function reducedNow() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
      || document.documentElement.classList.contains('st-reduced') || /[?&]reduced=1\b/.test(location.search);
  }
  function drawLine(fig, path, i) {
    if (fig.__drawn || reducedNow() || !path.getTotalLength) return;
    // with the story engine's GSAP layer on a desktop, the line is scrubbed to scroll
    var G = window.gsap, ST = window.ScrollTrigger;
    if (G && ST && window.matchMedia && matchMedia('(min-width: 900px)').matches) {
      requestAnimationFrame(function () {
        var L = 0; try { L = path.getTotalLength(); } catch (e) { }
        if (!L) return;
        fig.__drawn = 1;
        G.fromTo(path, { strokeDasharray: L + ' ' + L, strokeDashoffset: L },
          { strokeDashoffset: 0, ease: 'none', delay: i * 0.08,
            scrollTrigger: { trigger: fig, start: 'top 80%', end: 'center 45%', scrub: 0.6 } });
      });
      return;
    }
    if (!('IntersectionObserver' in window)) return;
    requestAnimationFrame(function () {
      var len = 0; try { len = path.getTotalLength(); } catch (e) { }
      if (!len) return;
      path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
      var io = new IntersectionObserver(function (es) {
        if (!es[0].isIntersecting) return;
        io.disconnect(); fig.__drawn = 1;
        path.style.transition = 'stroke-dashoffset 1.3s cubic-bezier(.2,.8,.2,1) ' + (i * 160) + 'ms';
        path.style.strokeDashoffset = 0;
        setTimeout(function () { path.style.strokeDasharray = ''; path.style.strokeDashoffset = ''; path.style.transition = ''; }, 1600 + i * 160);
      }, { threshold: 0.25 });
      io.observe(fig);
    });
  }

  window.GCharts = { init: function () { document.querySelectorAll('figure.chart[data-chart]').forEach(render); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', window.GCharts.init); else window.GCharts.init();
  document.addEventListener('rs-themechange', function () { window.GCharts.init(); });
})();

/* ======================================================================
   site.js - page behaviour for the generated project sites.
   Count-up hero, scroll reveals, sticky table of contents,
   copy buttons, and one signature interactive per site. Every interactive
   reads a JSON block embedded at build time from committed repo artifacts.
   ====================================================================== */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  // The system setting, or the story engine's own hook (?reduced=1), which marks
  // the document element so a reviewer can force the reduced path on any machine.
  var reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
    || document.documentElement.classList.contains('st-reduced')
    || /[?&]reduced=1\b/.test(location.search);
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null) continue;
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c != null) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }
  function s(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) { if (k === 'text') n.textContent = attrs[k]; else n.setAttribute(k, attrs[k]); }
    if (parent) parent.appendChild(n);
    return n;
  }
  function data(id) { var el = document.getElementById(id); if (!el) return null; try { return JSON.parse(el.textContent); } catch (e) { return null; } }
  function pct(v, d) { return (v * 100).toFixed(d == null ? 1 : d) + '%'; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

  /* ---------- count-up ---------- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-to')), dec = +(el.getAttribute('data-dec') || 0);
    var grouped = el.getAttribute('data-group') === '1';
    function fmt(v) { var t = v.toFixed(dec); if (grouped) t = t.replace(/\B(?=(\d{3})+(?!\d))/g, ','); return t; }
    if (reduce || !('requestAnimationFrame' in window)) { el.textContent = fmt(target); return; }
    var t0 = null, dur = 1400;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur); k = 1 - Math.pow(1 - k, 4);
      el.textContent = fmt(target * k);
      if (k < 1) requestAnimationFrame(step); else el.textContent = fmt(target);
    }
    el.textContent = fmt(0);
    requestAnimationFrame(step);
    setTimeout(function () { el.textContent = fmt(target); }, dur + 600);
  }

  /* ---------- count-up for figures further down the page ---------- */
  function countOnView() {
    var els = $$('[data-countup][data-to]');
    if (!els.length) return;
    if (reduce || !('IntersectionObserver' in window)) { els.forEach(countUp); return; }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); countUp(e.target); } });
    }, { threshold: 0.4 });
    els.forEach(function (e) { io.observe(e); });
  }

  /* ---------- reveals ---------- */
  function reveals() {
    var els = $$('.rv');
    if (reduce || !('IntersectionObserver' in window)) { els.forEach(function (e) { e.classList.add('in'); }); return; }
    els = els.filter(function (e) { if (e.getBoundingClientRect().top < window.innerHeight) { e.classList.add('in'); return false; } return true; });
    var io = new IntersectionObserver(function (es) {
      // GSAP-style batch stagger: items entering in the same frame cascade 70ms apart
      var k = 0;
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var t = e.target; t.style.transitionDelay = (Math.min(k++, 6) * 70) + 'ms';
        t.classList.add('in'); io.unobserve(t);
        setTimeout(function () { t.style.transitionDelay = ''; }, 1400);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.02 });
    els.forEach(function (e) { io.observe(e); });
  }

  /* ---------- TOC (reading progress lives in the site header) ---------- */
  function toc() {
    var links = $$('.toc a[href^="#"]');
    if (!links.length) return;
    var secs = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    var cur = $('.toc-current'), num = $('.toc-num'), det = $('.toc-d');
    var wide = window.innerWidth >= 1024;
    if (det) {
      det.open = wide;
      det.querySelector('summary').addEventListener('click', function (e) { if (wide) e.preventDefault(); });
    }
    window.addEventListener('resize', function () { var w = window.innerWidth >= 1024; if (w !== wide) { wide = w; det.open = w; } });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && det && !wide && det.open) { det.open = false; det.querySelector('summary').focus(); } });
    var ticking = false;
    function paint() {
      ticking = false;
      var line = window.innerHeight * 0.3, active = -1;
      secs.forEach(function (sec, i) { if (sec && sec.getBoundingClientRect().top <= line) active = i; });
      links.forEach(function (a, i) {
        var on = i === active;
        a.classList.toggle('is-on', on);
        if (on) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
      });
      if (cur) cur.textContent = active >= 0 ? links[active].getAttribute('data-short') : 'Contents';
      if (num) num.textContent = active >= 0 ? (active + 1 < 10 ? '0' : '') + (active + 1) + '/' + (links.length < 10 ? '0' : '') + links.length : '--/' + (links.length < 10 ? '0' : '') + links.length;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(paint); } }, { passive: true });
    window.addEventListener('resize', paint);
    links.forEach(function (a) { a.addEventListener('click', function () { var d = a.closest('details'); if (d && window.innerWidth < 1024) d.open = false; }); });
    paint();
  }

  /* ---------- copy ---------- */
  function copyButtons() {
    $$('.qs-copy').forEach(function (b) {
      b.addEventListener('click', function () {
        var code = b.closest('.qs').querySelector('code').textContent;
        function done(ok) { b.textContent = ok ? 'Copied' : 'Select and copy'; setTimeout(function () { b.textContent = 'Copy'; }, 1800); }
        function fallback() {
          try {
            var ta = h('textarea', { 'aria-hidden': 'true' }); ta.value = code; ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta); ta.select(); var ok = document.execCommand('copy'); document.body.removeChild(ta); done(ok);
          } catch (e) { done(false); }
        }
        try {
          if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(code).then(function () { done(true); }, fallback);
          else fallback();
        } catch (e) { fallback(); }
      });
    });
  }

  /* ---------- shared: segmented buttons ---------- */
  function seg(container, options, current, onPick, label) {
    clear(container);
    container.setAttribute('role', 'group');
    if (label) container.setAttribute('aria-label', label);
    options.forEach(function (o) {
      var b = h('button', { type: 'button', class: 'seg-b', 'aria-pressed': String(o.value === current), text: o.label });
      b.addEventListener('click', function () {
        $$('.seg-b', container).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true'); onPick(o.value);
      });
      container.appendChild(b);
    });
  }

  /* =================== OSHA =================== */
  function osha(root) {
    var D = data('ix-osha-data'); if (!D) return;
    // A. screening window
    var selLo = $('#ox-lo', root), selHi = $('#ox-hi', root), out = $('#ox-out', root);
    var los = [], his = [];
    D.grid.forEach(function (g) { if (los.indexOf(g.lo) < 0) los.push(g.lo); if (his.indexOf(g.hi) < 0) his.push(g.hi); });
    los.sort(function (a, b) { return a - b; }); his.sort(function (a, b) { return a - b; });
    los.forEach(function (v) { selLo.appendChild(h('option', { value: v, text: v.toLocaleString() + ' h' })); });
    his.forEach(function (v) { selHi.appendChild(h('option', { value: v, text: v.toLocaleString() + ' h' })); });
    selLo.value = D.def.lo; selHi.value = D.def.hi;
    function paintGrid() {
      var lo = +selLo.value, hi = +selHi.value, g = null;
      D.grid.forEach(function (r) { if (r.lo === lo && r.hi === hi) g = r; });
      if (!g) return;
      $('[data-k=flag]', out).textContent = pct(g.flag, 2);
      $('[data-k=hours]', out).textContent = pct(g.hours, 1);
      $('[data-k=scr]', out).textContent = g.scr.toFixed(3);
      $('[data-k=uns]', out).textContent = g.uns.toFixed(3);
      $('[data-k=ratio]', out).textContent = g.ratio.toFixed(1) + 'x';
      $('.ox-bar-f', out).style.width = pct(g.flag, 3);
      $('.ox-bar-h', out).style.width = pct(g.hours, 3);
      var isDef = lo === D.def.lo && hi === D.def.hi;
      $('.ox-note', out).textContent = isDef ? 'This is the window the pipeline uses.' : 'The pipeline uses ' + D.def.lo + ' to ' + D.def.hi.toLocaleString() + ' hours per employee.';
    }
    selLo.addEventListener('change', paintGrid); selHi.addEventListener('change', paintGrid); paintGrid();

    // B. TRIR by year
    var mode = 'both', svgBox = $('#ox-years', root), readout = $('#ox-year-read', root);
    function paintYears() {
      clear(svgBox);
      var W = 640, H = 260, L = 44, R = 10, T = 16, B = 30, iw = W - L - R, ih = H - T - B;
      var svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Aggregate TRIR by year, ' + mode });
      var vals = [];
      D.years.forEach(function (y) { if (mode !== 'uns') vals.push(y.scr); if (mode !== 'scr') vals.push(y.uns); });
      var top = Math.ceil(Math.max.apply(null, vals));
      for (var t = 0; t <= top; t++) {
        var yy = T + ih - t / top * ih;
        s('line', { x1: L, x2: W - R, y1: yy, y2: yy, stroke: 'var(--fig-grid)' }, svg);
        s('text', { x: L - 8, y: yy + 4, 'text-anchor': 'end', 'font-size': 11, fill: 'var(--fig-mute)', text: t }, svg);
      }
      var slot = iw / D.years.length, series = mode === 'both' ? ['uns', 'scr'] : [mode];
      var bw = Math.min(34, slot * 0.72 / series.length);
      D.years.forEach(function (y, i) {
        series.forEach(function (k, si) {
          var v = y[k], x = L + slot * i + slot / 2 - bw * series.length / 2 + bw * si, top2 = T + ih - v / top * ih;
          var r = s('rect', { x: x, y: top2, width: bw - 2, height: Math.max(1, T + ih - top2), fill: k === 'scr' ? 'var(--accent)' : 'var(--s2)', class: 'ox-yr', tabindex: 0, role: 'img',
            'aria-label': y.y + ' ' + (k === 'scr' ? 'screened' : 'unscreened') + ' TRIR ' + v.toFixed(3) }, svg);
          function show() {
            readout.textContent = y.y + ': screened ' + y.scr.toFixed(3) + ', unscreened ' + y.uns.toFixed(3) + ', ratio ' + y.ratio.toFixed(2) + 'x, ' + pct(y.hours, 1) + ' of hours in flagged filings';
          }
          r.addEventListener('mouseenter', show); r.addEventListener('focus', show);
        });
        s('text', { x: L + slot * i + slot / 2, y: H - 9, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--fig-mute)', text: y.y }, svg);
      });
      s('line', { x1: L, x2: W - R, y1: T + ih, y2: T + ih, stroke: 'var(--fig-axis)', 'stroke-width': 2 }, svg);
      svgBox.appendChild(svg);
    }
    seg($('#ox-mode', root), [{ value: 'both', label: 'Both' }, { value: 'scr', label: 'Screened' }, { value: 'uns', label: 'Unscreened' }], mode,
      function (v) { mode = v; paintYears(); }, 'Series shown');
    paintYears();

    // C. peer lookup
    var selN = $('#ox-naics', root), selS = $('#ox-size', root), inp = $('#ox-trir', root), pr = $('#ox-peer', root);
    D.peers.naics.forEach(function (n) { selN.appendChild(h('option', { value: n[0], text: n[0] + (n[1] ? ' ' + n[1] : '') })); });
    D.peers.bands.forEach(function (b) { selS.appendChild(h('option', { value: b, text: b + ' employees' })); });
    selN.value = D.peers.naics.some(function (n) { return n[0] === '325'; }) ? '325' : D.peers.naics[0][0];
    selS.value = '100-249';
    var KEYS = ['p10', 'p25', 'p50', 'p75', 'p90', 'p95'];
    function paintPeer() {
      var row = D.peers.rows[selN.value + '|' + selS.value];
      var box = $('.ox-strip', pr), msg = $('.ox-peer-msg', pr), meta = $('.ox-peer-meta', pr);
      clear(box);
      if (!row) { clear($('.ox-pcts', pr)); msg.textContent = 'No filings for this industry and size band in the pooled table.'; meta.textContent = ''; return; }
      var n = row[0], pub = row[1], ps = row.slice(2, 8), agg = row[8];
      meta.textContent = 'n = ' + n.toLocaleString() + ' establishments' + (pub ? '' : ' - below the publishable threshold, read with care') + (agg != null ? ' - aggregate TRIR ' + agg.toFixed(2) : '');
      var mx = Math.max(ps[5], +inp.value || 0) * 1.1 || 1;
      var row2 = $('.ox-pcts', pr); clear(row2);
      KEYS.forEach(function (k, i) {
        box.appendChild(h('div', { class: 'ox-tick', style: 'left:' + (ps[i] / mx * 100).toFixed(2) + '%' }));
        row2.appendChild(h('div', null, [h('span', { text: k.toUpperCase() }), h('b', { text: ps[i].toFixed(2) })]));
      });
      var you = +inp.value;
      if (inp.value !== '' && you >= 0) {
        box.appendChild(h('div', { class: 'ox-you', style: 'left:' + (you / mx * 100).toFixed(2) + '%' }, [h('span', { text: 'You' })]));
        var band = 'below the 10th percentile';
        for (var i = KEYS.length - 1; i >= 0; i--) { if (you >= ps[i]) { band = i === KEYS.length - 1 ? 'at or above the 95th percentile' : 'between ' + KEYS[i].toUpperCase() + ' and ' + KEYS[i + 1].toUpperCase(); break; } }
        if (you === 0 && ps[0] === 0) band = 'at the 10th percentile, where zero-case establishments sit';
        msg.textContent = 'A TRIR of ' + you.toFixed(2) + ' falls ' + band + ' for this peer group.';
      } else msg.textContent = 'Enter a TRIR to place it against the peer bands.';
    }
    [selN, selS].forEach(function (e) { e.addEventListener('change', paintPeer); });
    inp.addEventListener('input', paintPeer);
    paintPeer();
  }

  /* =================== RISK SEM =================== */
  function sem(root) {
    var D = data('ix-sem-data'); if (!D) return;
    var pred = D.preds[0], ni = 0, slider = $('#sx-n', root), nlab = $('#sx-nlab', root);
    slider.max = D.ns.length - 1; slider.value = 0;
    function row(n, p) { var r = null; D.rows.forEach(function (x) { if (x.n === n && x.p === p) r = x; }); return r; }
    function axis(svg, W, L, R, lo, hi, y) {
      for (var v = lo; v <= hi + 1e-9; v += 0.25) {
        var x = L + (v - lo) / (hi - lo) * (W - L - R);
        s('line', { x1: x, x2: x, y1: 8, y2: y, stroke: Math.abs(v) < 1e-9 ? 'var(--fig-axis)' : 'var(--fig-grid)' }, svg);
        s('text', { x: x, y: y + 16, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--fig-mute)', text: v.toFixed(2) }, svg);
      }
    }
    function paint() {
      var n = D.ns[ni];
      nlab.textContent = 'n = ' + n.toLocaleString();
      slider.setAttribute('aria-valuetext', 'n = ' + n);
      // all four at this n
      var box = $('#sx-four', root); clear(box);
      var W = 640, L = 150, R = 16, lo = -0.75, hi = 1.0, rowH = 46, H = D.preds.length * rowH + 30;
      var svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Estimate spread for four coefficients at n = ' + n });
      axis(svg, W, L, R, lo, hi, H - 22);
      function X(v) { return L + (v - lo) / (hi - lo) * (W - L - R); }
      D.preds.forEach(function (p, i) {
        var r = row(n, p), y = 22 + i * rowH, on = p === pred;
        var g = s('g', { class: 'sx-row' + (on ? ' on' : ''), tabindex: 0, role: 'button', 'aria-pressed': String(on), 'aria-label': p + ': select' }, svg);
        s('text', { x: L - 12, y: y + 5, 'text-anchor': 'end', 'font-size': 12, 'font-weight': on ? 700 : 500, fill: on ? 'var(--ink)' : 'var(--fig-axis)', text: D.short[p] }, g);
        s('rect', { x: X(r.mean - 1.96 * r.sd), y: y - 9, width: X(r.mean + 1.96 * r.sd) - X(r.mean - 1.96 * r.sd), height: 18, fill: 'var(--s2)', opacity: on ? 0.35 : 0.18 }, g);
        s('rect', { x: X(r.mean - 1.96 * r.se), y: y - 3, width: X(r.mean + 1.96 * r.se) - X(r.mean - 1.96 * r.se), height: 6, fill: 'var(--accent)' }, g);
        s('line', { x1: X(r.beta), x2: X(r.beta), y1: y - 14, y2: y + 14, stroke: 'var(--ink)', 'stroke-width': 2, 'stroke-dasharray': '3 2' }, g);
        s('circle', { cx: X(r.mean), cy: y, r: 4, fill: 'var(--ink)' }, g);
        function pick() { pred = p; paint(); }
        g.addEventListener('click', pick);
        g.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); var nx = $('.sx-row.on', box); if (nx) nx.focus(); } });
      });
      box.appendChild(svg);
      // readouts
      var r = row(n, pred);
      $('[data-k=p]', root).textContent = D.short[pred];
      $('[data-k=beta]', root).textContent = r.beta.toFixed(2);
      $('[data-k=mean]', root).textContent = r.mean.toFixed(3);
      $('[data-k=sd]', root).textContent = r.sd.toFixed(3);
      $('[data-k=se]', root).textContent = r.se.toFixed(3);
      $('[data-k=cov]', root).textContent = pct(r.cov, 1);
      $('[data-k=ratio]', root).textContent = r.ratio.toFixed(2);
      $('.sx-covbar i', root).style.width = pct(r.cov, 2);
      // spread vs n for the selected predictor
      var box2 = $('#sx-byn', root); clear(box2);
      var W2 = 640, L2 = 70, R2 = 16, H2 = D.ns.length * 30 + 30, lo2 = r.beta - 0.35, hi2 = r.beta + 0.35;
      var svg2 = s('svg', { viewBox: '0 0 ' + W2 + ' ' + H2, role: 'img', 'aria-label': 'Spread of ' + pred + ' estimates by sample size' });
      function X2(v) { return L2 + (v - lo2) / (hi2 - lo2) * (W2 - L2 - R2); }
      [-0.3, -0.15, 0, 0.15, 0.3].forEach(function (d) {
        var x = X2(r.beta + d);
        s('line', { x1: x, x2: x, y1: 6, y2: H2 - 22, stroke: d === 0 ? 'var(--ink)' : 'var(--fig-grid)', 'stroke-dasharray': d === 0 ? '3 2' : '' }, svg2);
        s('text', { x: x, y: H2 - 6, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--fig-mute)', text: (r.beta + d).toFixed(2) }, svg2);
      });
      D.ns.forEach(function (nn, i) {
        var q = row(nn, pred), y = 18 + i * 30, on = i === ni;
        s('text', { x: L2 - 10, y: y + 4, 'text-anchor': 'end', 'font-size': 11, 'font-weight': on ? 700 : 400, fill: on ? 'var(--ink)' : 'var(--fig-mute)', text: nn.toLocaleString() }, svg2);
        s('rect', { x: X2(q.mean - 1.96 * q.sd), y: y - 7, width: X2(q.mean + 1.96 * q.sd) - X2(q.mean - 1.96 * q.sd), height: 14, fill: 'var(--s2)', opacity: on ? 0.45 : 0.2 }, svg2);
        s('rect', { x: X2(q.mean - 1.96 * q.se), y: y - 2, width: X2(q.mean + 1.96 * q.se) - X2(q.mean - 1.96 * q.se), height: 4, fill: 'var(--accent)' }, svg2);
      });
      box2.appendChild(svg2);
    }
    slider.addEventListener('input', function () { ni = +slider.value; paint(); });
    paint();
  }

  /* =================== GROUNDING =================== */
  function ground(root) {
    var D = data('ix-ground-data'); if (!D) return;
    var dom = 'all', cur = null;
    var list = $('#gx-list', root), card = $('#gx-card', root), chips = $('#gx-domains', root), grid = $('#gx-acc', root);
    // per-domain accuracy small multiples
    D.domains.forEach(function (d, di) {
      var cell = h('button', { type: 'button', class: 'gx-dom', 'aria-pressed': 'false', 'data-d': di });
      cell.appendChild(h('span', { class: 'gx-dom-t', text: d.short }));
      D.adapters.forEach(function (a, ai) {
        var v = d.acc[ai];
        cell.appendChild(h('span', { class: 'gx-accrow' }, [
          h('small', { text: a.label }),
          h('span', { class: 'gx-track' }, [h('i', { class: 'a' + ai, style: 'width:' + (v * 100).toFixed(1) + '%' })]),
          h('b', { text: pct(v, 0) })]));
      });
      cell.addEventListener('click', function () { setDom(dom === di ? 'all' : di); });
      grid.appendChild(cell);
    });
    function setDom(v) {
      dom = v;
      $$('.gx-dom', grid).forEach(function (b) { b.setAttribute('aria-pressed', String(+b.getAttribute('data-d') === v)); });
      $$('.seg-b', chips).forEach(function (b, i) { b.setAttribute('aria-pressed', String((i === 0 && v === 'all') || i - 1 === v)); });
      paintList();
    }
    seg(chips, [{ value: 'all', label: 'All ' + D.items.length }].concat(D.domains.map(function (d, i) { return { value: i, label: d.short + ' ' + d.n }; })), 'all', setDom, 'Filter by domain');
    var OUT = { correct: 'correct', adjacent_substitution: 'adjacent substitution', other_incorrect: 'incorrect', abstained: 'abstained', unscorable: 'unscorable' };
    function paintList() {
      clear(list);
      var shown = D.items.filter(function (it) { return dom === 'all' || it.d === dom; });
      shown.forEach(function (it) {
        var b = h('button', { type: 'button', class: 'gx-item', 'aria-pressed': String(cur === it) }, [
          h('span', { class: 'gx-id', text: it.id }),
          h('span', { class: 'gx-tier t-' + it.tier, text: it.tier }),
          h('span', { class: 'gx-q', text: it.q })]);
        b.addEventListener('click', function () { cur = it; $$('.gx-item', list).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); }); b.setAttribute('aria-pressed', 'true'); paintCard(); });
        list.appendChild(b);
      });
      if (!cur || shown.indexOf(cur) < 0) { cur = shown[0]; if (list.firstChild) list.firstChild.setAttribute('aria-pressed', 'true'); paintCard(); }
    }
    function paintCard() {
      clear(card); if (!cur) return;
      var it = cur;
      card.appendChild(h('div', { class: 'gx-meta' }, [
        h('span', { class: 'label', text: it.id + ' - ' + D.domains[it.d].short + ' - ' + (it.type === 'factual' ? 'factual' : 'category error') + (it.pair ? ' - pair ' + it.pair : '') })]));
      card.appendChild(h('p', { class: 'gx-question', text: it.q }));
      card.appendChild(h('div', { class: 'gx-block ok' }, [h('span', { class: 'label', text: 'Answer key' }), h('p', { text: it.a }), it.cite ? h('span', { class: 'src', text: it.cite }) : null]));
      var trap = h('div', { class: 'gx-block trap', id: 'gx-trap', hidden: '' }, [
        h('span', { class: 'label', text: 'The trap: ' + it.trap.label }), h('p', { text: it.trap.answer }),
        it.trap.why ? h('p', { class: 'gx-why', text: 'Why it is dangerous: ' + it.trap.why }) : null]);
      var btn = h('button', { type: 'button', class: 'btn gx-reveal', 'aria-expanded': 'false', 'aria-controls': 'gx-trap', text: 'Reveal the plausible wrong answer' });
      btn.addEventListener('click', function () {
        var open = trap.hidden; trap.hidden = !open; btn.setAttribute('aria-expanded', String(open));
        btn.textContent = open ? 'Hide the wrong answer' : 'Reveal the plausible wrong answer';
      });
      card.appendChild(btn); card.appendChild(trap);
      if (it.out) {
        var row = h('div', { class: 'gx-outs' }, [h('span', { class: 'label', text: 'Baseline outcomes on this item' })]);
        D.adapters.forEach(function (a) {
          var o = it.out[a.key]; if (o == null) return;
          var txt = typeof o === 'string' ? OUT[o] || o : o[0] + ' of ' + o[1] + ' repeats correct';
          var good = typeof o === 'string' ? o === 'correct' : o[0] === o[1];
          row.appendChild(h('span', { class: 'gx-out' + (good ? ' good' : '') }, [h('b', { text: a.label }), ' ' + txt]));
        });
        card.appendChild(row);
      }
    }
    paintList();
  }

  /* =================== ONTOLOGY =================== */
  function onto(root) {
    var D = data('ix-onto-data'); if (!D) return;
    var di = 0, fcur = D.dims[0].factors[0].curie, base = 'example', lvl = null;
    var tabs = $('#hx-tabs', root), fbox = $('#hx-factors', root), xbox = $('#hx-xw', root);
    function factor(c) { var f = null; D.dims.forEach(function (d) { d.factors.forEach(function (x) { if (x.curie === c) f = x; }); }); return f; }
    // context tabs
    D.dims.forEach(function (d, i) {
      var t = h('button', { type: 'button', role: 'tab', class: 'hx-tab', id: 'hx-tab-' + i, 'aria-selected': String(i === di), 'aria-controls': 'hx-factors', tabindex: i === di ? '0' : '-1' },
        [h('span', { text: d.label }), h('small', { text: d.factors.length + ' factors' })]);
      t.addEventListener('click', function () { selectDim(i, true); });
      t.addEventListener('keydown', function (e) {
        var k = e.key, j = null;
        if (k === 'ArrowRight' || k === 'ArrowDown') j = (i + 1) % D.dims.length;
        if (k === 'ArrowLeft' || k === 'ArrowUp') j = (i - 1 + D.dims.length) % D.dims.length;
        if (j !== null) { e.preventDefault(); selectDim(j, true); $('#hx-tab-' + j).focus(); }
      });
      tabs.appendChild(t);
    });
    function selectDim(i, pickFirst) {
      di = i;
      $$('.hx-tab', tabs).forEach(function (t, k) { t.setAttribute('aria-selected', String(k === i)); t.setAttribute('tabindex', k === i ? '0' : '-1'); });
      fbox.setAttribute('aria-labelledby', 'hx-tab-' + i);
      if (pickFirst) fcur = D.dims[i].factors[0].curie;
      paintFactors();
    }
    function paintFactors() {
      clear(fbox);
      D.dims[di].factors.forEach(function (f) {
        var al = f.xw.filter(function (r) { return r.s !== 'none'; }).length;
        var b = h('button', { type: 'button', class: 'hx-f', 'aria-pressed': String(f.curie === fcur) }, [h('span', { text: f.label }), h('small', { text: al + ' aligned / ' + (f.xw.length - al) + ' absent' })]);
        b.addEventListener('click', function () { fcur = f.curie; paintFactors(); syncDemo(); });
        fbox.appendChild(b);
      });
      paintXw();
    }
    function paintXw() {
      clear(xbox);
      var f = factor(fcur);
      xbox.appendChild(h('div', { class: 'hx-xw-head' }, [h('span', { class: 'label', text: 'IDHEAS-G source wording' }), h('p', { text: f.verbatim })]));
      D.frameworks.forEach(function (fw) {
        var rows = f.xw.filter(function (r) { return r.fw === fw; });
        var col = h('div', { class: 'hx-fw' }, [h('span', { class: 'hx-fw-name', text: fw })]);
        if (!rows.length) col.appendChild(h('p', { class: 'hx-empty', text: 'No row in the crosswalk.' }));
        rows.forEach(function (r) {
          col.appendChild(h('div', { class: 'hx-m s-' + r.s }, [
            h('span', { class: 'hx-strength', text: r.s === 'none' ? 'asserted absence' : r.s }),
            h('b', { text: r.s === 'none' ? 'No counterpart' : r.ext }),
            r.note ? h('p', { text: r.note }) : null,
            r.cite ? h('span', { class: 'src', text: r.cite }) : null]));
        });
        xbox.appendChild(col);
      });
    }
    // rule-engine demo
    var selF = $('#hx-dfactor', root), lvBox = $('#hx-dlevel', root), res = $('#hx-dres', root);
    D.dims.forEach(function (d) {
      var og = h('optgroup', { label: d.label });
      d.factors.forEach(function (f) { og.appendChild(h('option', { value: f.curie, text: f.label })); });
      selF.appendChild(og);
    });
    function syncDemo() { selF.value = fcur; lvl = null; paintDemo(); }
    selF.addEventListener('change', function () { fcur = selF.value; lvl = null; var f = factor(fcur); D.dims.forEach(function (d, i) { if (d.factors.indexOf(f) >= 0) di = i; }); selectDim(di, false); paintDemo(); });
    seg($('#hx-dbase', root), [{ value: 'example', label: 'Worked example' }, { value: 'nominal', label: 'All nominal' }], base,
      function (v) { base = v; lvl = null; paintDemo(); }, 'Starting scenario');
    function paintDemo() {
      var B = D.demo.bases[base];
      var given = B.levels[fcur];
      if (lvl === null) lvl = given;
      seg(lvBox, D.demo.levels.map(function (l) { return { value: l[0], label: l[1] + (l[0] === given ? ' (as given)' : '') }; }), lvl,
        function (v) { lvl = v; paintRes(); }, 'Level for this factor');
      paintRes();
    }
    function paintRes() {
      var B = D.demo.bases[base], given = B.levels[fcur];
      var r = D.demo.results[lvl === given ? B.result : D.demo.runs[base + '|' + fcur + '|' + lvl]];
      clear(res);
      var meter = h('ol', { class: 'hx-meter', 'aria-label': 'Screening band' });
      D.demo.bands.forEach(function (b) { meter.appendChild(h('li', { class: b === r.band ? 'on' : '', 'aria-current': b === r.band ? 'true' : null, text: b })); });
      res.appendChild(meter);
      res.appendChild(h('dl', { class: 'hx-facts' }, [
        h('dt', { text: 'Distinct rules fired' }), h('dd', { text: String(r.fired) }),
        h('dt', { text: 'Functions challenged' }), h('dd', { text: r.funcs.length ? r.funcs.join(', ') : 'none' }),
        h('dt', { text: 'Aggravated error modes' }), h('dd', { text: r.agg.length ? r.agg.join(', ') : 'none' }),
        h('dt', { text: 'Coverage' }), h('dd', { text: r.cov })]));
      res.appendChild(h('pre', { class: 'hx-trace', tabindex: '0', 'aria-label': 'Band derivation trace' }, [h('code', { text: r.trace.join('\n') })]));
    }
    selectDim(0, false); syncDemo();
  }

  /* ---------- header height: sticky TOC sits under the shared header ---------- */
  function headerHeight() {
    var hd = document.getElementById('rs-header');
    if (!hd) return;
    function set() { document.documentElement.style.setProperty('--hdr-h', hd.offsetHeight + 'px'); }
    set();
    if ('ResizeObserver' in window) new ResizeObserver(set).observe(hd); else window.addEventListener('resize', set);
  }

  function init() {
    document.documentElement.classList.add('js');
    headerHeight();
    $$('.hero-num[data-to]').forEach(countUp);
    countOnView();
    reveals(); toc(); copyButtons();
    var o = $('#ix-osha'); if (o) osha(o);
    var m = $('#ix-sem'); if (m) sem(m);
    var g = $('#ix-ground'); if (g) ground(g);
    var t = $('#ix-onto'); if (t) onto(t);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
