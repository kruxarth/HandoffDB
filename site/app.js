'use strict';
/* HandoffDB showcase: canvas graph engine + scripted scenes. No dependencies. */
const COL = { cyan:'#22e4ff', lime:'#b8ff2c', orange:'#ff8a1f', mag:'#ff3dcf', yel:'#ffd23f', text:'#eef4ff', dim:'#95a3bb', dim2:'#40527a', bg:'#060a10' };
const KIND = { term:{c:COL.mag,g:'#'}, run:{c:COL.orange,g:'◆'}, file:{c:COL.cyan,g:'▪'}, test:{c:COL.lime,g:'✓'}, doc:{c:COL.yel,g:'¶'} };
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, RM ? Math.min(ms, 300) : ms));
const pick = a => a[Math.floor(Math.random() * a.length)];
const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt = (v, dec=0) => v.toLocaleString('en-US', {minimumFractionDigits:dec, maximumFractionDigits:dec});
const base = p => p.split('/').pop();
const short2 = p => p.split('/').slice(-2).join('/');
function bz(t, a, b, c, d){ const u=1-t; return u*u*u*a + 3*u*u*t*b + 3*u*t*t*c + t*t*t*d; }

/* ---------------------------------------------------------------- graph engine */
class Net {
  constructor(cv, opt={}){
    this.cv = cv; this.ctx = cv.getContext('2d'); this.opt = opt;
    this.nodes = new Map(); this.edges = []; this.pk = []; this.t = 0; this.vis = false; this.last = 0; this.waiters = [];
    this.resize();
    new ResizeObserver(() => this.resize()).observe(cv);
    new IntersectionObserver(es => { this.vis = es[0].isIntersecting; if (this.vis){ this.waiters.forEach(f => f()); this.waiters = []; } }, {threshold:0.05}).observe(cv);
    const loop = ts => { const dt = Math.min(0.2,(ts - this.last) / 1000 || 0); this.last = ts;
      if (this.vis){ this.t += dt; this.step(dt); this.draw(); } requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }
  visible(){ return this.vis ? Promise.resolve() : new Promise(r => this.waiters.push(r)); }
  resize(){
    const r = this.cv.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
    this.W = r.width; this.H = r.height;
    this.cv.width = Math.max(1, Math.round(r.width * d)); this.cv.height = Math.max(1, Math.round(r.height * d));
    this.ctx.setTransform(d, 0, 0, d, 0, 0);
    this.small = this.W < 620; this.fs = this.small ? 9.5 : (this.opt.fs || 11.5); this.wc = {};
  }
  clear(){ this.nodes.clear(); this.edges = []; this.pk.forEach(p => p.res()); this.pk = []; }
  node(id, o){ const n = Object.assign({id, x:.5, y:.5, a:0, ta:1, lit:0, tl:0, ph:Math.random()*6.28, drift:this.opt.drift ?? 2.5, born:this.t}, o); this.nodes.set(id, n); return n; }
  edge(a, b, o={}){ const e = Object.assign({a, b, al:0, ta:1, lit:0, tl:0}, o); this.edges.push(e); return e; }
  label(n){
    let s = (this.small && n.short) ? n.short : n.label;
    const max = this.small ? (this.opt.smax || 17) : (this.opt.max || 42);
    if (s.length > max) s = s.slice(0, max - 1) + '…';
    return KIND[n.kind].g + ' ' + s;
  }
  tw(s){ if (this.wc[s] == null){ this.ctx.font = `500 ${this.fs}px "JetBrains Mono", monospace`; this.wc[s] = this.ctx.measureText(s).width; } return this.wc[s]; }
  pos(n){ return [n.x * this.W + Math.sin(this.t*.7 + n.ph) * n.drift, n.y * this.H + Math.cos(this.t*.6 + n.ph) * n.drift]; }
  side(n, s){ const [x, y] = this.pos(n); return s === 'r' ? [x + this.tw(this.label(n)) + 6, y] : [x - 5, y]; }
  ends(a, b){
    const A = this.nodes.get(a), B = this.nodes.get(b); if (!A || !B) return null;
    const fw = A.x <= B.x;
    return [fw ? this.side(A,'r') : this.side(A,'l'), fw ? this.side(B,'l') : this.side(B,'r')];
  }
  packet(a, b, color=COL.cyan, dur=650){ return new Promise(res => this.pk.push({a, b, color, t:0, dur: RM ? 60 : dur, res, done:false})); }
  step(dt){
    const k = Math.min(1, dt * 6);
    for (const n of this.nodes.values()){ n.a += (n.ta - n.a) * k; n.lit += (n.tl - n.lit) * k; }
    for (const e of this.edges){ e.al += (e.ta - e.al) * k; e.lit += (e.tl - e.lit) * k; }
    this.edges = this.edges.filter(e => !(e.kill && e.al < 0.02));
    for (const [id, n] of this.nodes) if (n.kill && n.a < 0.02) this.nodes.delete(id);
    for (const p of this.pk){ p.t += dt * 1000 / p.dur; if (p.t >= 1 && !p.done){ p.done = true; p.res(); } }
    this.pk = this.pk.filter(p => p.t < 1.3);
  }
  draw(){
    const c = this.ctx, fs = this.fs;
    c.clearRect(0, 0, this.W, this.H);
    if (this.heads){
      c.font = `600 ${fs - 1.5}px "JetBrains Mono", monospace`; c.textBaseline = 'top'; c.fillStyle = COL.dim2; c.globalAlpha = 1;
      for (const h of this.heads) c.fillText(h[1], h[0] * this.W, 8);
    }
    /* edges */
    for (const e of this.edges){
      const en = this.ends(e.a, e.b); if (!en) continue;
      const [[x1,y1],[x2,y2]] = en, dx = (x2 - x1) * .5;
      c.beginPath(); c.moveTo(x1, y1); c.bezierCurveTo(x1 + dx, y1, x2 - dx, y2, x2, y2);
      const lc = e.litc || COL.cyan, lit = e.lit;
      c.globalAlpha = e.al * (0.6 + 0.4 * lit);
      c.strokeStyle = lit > .15 ? lc : (e.color || COL.dim2);
      c.lineWidth = (e.w || 1) + lit * 1.3;
      c.setLineDash(e.dash && lit < .5 ? [3, 4] : []);
      c.shadowColor = lc; c.shadowBlur = lit > .3 ? 10 * lit : 0;
      c.stroke();
      c.shadowBlur = 0; c.setLineDash([]);
      if (e.lbl && e.al > .4 && (lit > .4 || e.showLbl) && !this.small){
        const mx = bz(.5, x1, x1+dx, x2-dx, x2), my = bz(.5, y1, y1, y2, y2);
        c.font = `500 ${fs - 2.5}px "JetBrains Mono", monospace`; c.textBaseline = 'middle';
        const w = c.measureText(e.lbl).width;
        c.globalAlpha = e.al; c.fillStyle = '#04070c'; c.fillRect(mx - w/2 - 3, my - 6, w + 6, 12);
        c.fillStyle = lit > .4 ? lc : COL.dim; c.fillText(e.lbl, mx - w/2, my + .5);
      }
    }
    /* packets */
    for (const p of this.pk){
      const en = this.ends(p.a, p.b); if (!en) continue;
      const [[x1,y1],[x2,y2]] = en, dx = (x2 - x1) * .5;
      for (let i = 6; i >= 0; i--){
        const t = Math.min(1, p.t) - i * 0.035; if (t < 0) continue;
        const x = bz(t, x1, x1+dx, x2-dx, x2), y = bz(t, y1, y1, y2, y2), s = i ? 2.4 : 4.2;
        c.globalAlpha = (1 - i / 7) * (p.t > 1 ? Math.max(0, 1 - (p.t - 1) * 4) : 1);
        c.fillStyle = p.color; c.shadowColor = p.color; c.shadowBlur = i ? 0 : 14;
        c.fillRect(x - s/2, y - s/2, s, s);
      }
      c.shadowBlur = 0;
    }
    /* nodes */
    c.font = `500 ${fs}px "JetBrains Mono", monospace`; c.textBaseline = 'middle';
    for (const n of this.nodes.values()){
      if (n.a < .01) continue;
      const [x, y] = this.pos(n), s = this.label(n), w = this.tw(s), col = n.gold ? COL.lime : KIND[n.kind].c;
      const h = fs * 1.75, bx = x - 4, by = y - h/2;
      const age = this.t - n.born;
      if (age < 1.2 && n.pulse){ c.globalAlpha = (1 - age/1.2) * .8; c.strokeStyle = col; c.lineWidth = 1.5;
        c.strokeRect(bx - age*14, by - age*10, w + 8 + age*28, h + age*20); }
      c.globalAlpha = n.a;
      c.fillStyle = '#060a10'; c.fillRect(bx, by, w + 8, h);
      if (n.lit > .05){ c.globalAlpha = n.a * n.lit * .95; c.fillStyle = col; c.shadowColor = col; c.shadowBlur = 16 * n.lit; c.fillRect(bx, by, w + 8, h); c.shadowBlur = 0; }
      c.globalAlpha = n.a * (0.45 + 0.55 * Math.max(n.lit, n.dimmed ? 0 : .5));
      c.strokeStyle = col; c.lineWidth = 1; c.strokeRect(bx + .5, by + .5, w + 7, h - 1);
      c.globalAlpha = n.a * (n.dimmed ? .45 : 1);
      c.fillStyle = n.lit > .5 ? '#05070b' : col; c.fillText(s, x, y + .5);
      if (n.badge){ c.font = `700 ${fs - 2}px "JetBrains Mono", monospace`; c.fillStyle = COL.lime; c.globalAlpha = n.a;
        c.fillText(n.badge, x, by + h + fs * .6); c.font = `500 ${fs}px "JetBrains Mono", monospace`; }
    }
    c.globalAlpha = 1;
  }
}

/* ---------------------------------------------------------------- count-ups */
function countUp(el){
  const to = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0), suf = el.dataset.suffix || '';
  const t0 = performance.now(), dur = RM ? 1 : 1400;
  const f = now => { const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(to * e, dec) + suf; if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
function onView(el, fn, th=0.25){
  const io = new IntersectionObserver(es => { if (es[0].isIntersecting){ io.disconnect(); document.fonts.ready.then(fn); } }, {threshold: th});
  io.observe(el);
}
$$('[data-count]').forEach(el => onView(el, () => countUp(el), 0.4));

/* ---------------------------------------------------------------- ASCII bars */
function charW(el){ const s = document.createElement('span'); s.textContent = '█'.repeat(20); s.style.visibility = 'hidden'; el.appendChild(s); const w = s.getBoundingClientRect().width / 20; s.remove(); return w || 8; }
function fillBar(el, frac, color, delay=0){
  const n = Math.max(1, Math.floor(el.clientWidth / charW(el) * frac));
  el.style.color = `var(--${color})`; if (color !== 'dim') el.style.textShadow = `0 0 10px var(--${color})`;
  let i = 0; setTimeout(() => { const f = () => { i = Math.min(n, i + Math.max(1, n / 40)); el.textContent = '█'.repeat(Math.round(i)) + (i < n ? '▌' : ''); if (i < n) requestAnimationFrame(f); }; f(); }, RM ? 0 : delay);
}
onView($('#prob-term'), () => {
  const sb = $('#splitbar'), n = Math.floor(sb.clientWidth / charW(sb)), pre = Math.max(2, Math.round(n * .07));
  let i = 0; const f = () => { i = Math.min(n, i + Math.max(1, n / 60));
    const k = Math.round(i); sb.innerHTML = `<span class="pre">${'░'.repeat(Math.min(k, pre))}</span>${'█'.repeat(Math.max(0, k - pre))}`;
    if (i < n) requestAnimationFrame(f); }; f();
  $$('#prob-rows .row').forEach((r, j) => fillBar($('.rb', r), +r.dataset.v / 30, r.dataset.c, 500 + j * 220));
});
onView($('#ret-bars'), () => $$('#ret-bars .bar').forEach((r, j) => fillBar($('.bt', r), +r.dataset.v / 40, r.dataset.c, j * 250)));

/* ---------------------------------------------------------------- learning curve */
(function curve(){
  const svg = $('#curve'), NS = 'http://www.w3.org/2000/svg';
  const L = 42, R = 404, T = 16, B = 206, X = v => L + v / 300 * (R - L), Y = v => B - v / 40 * (B - T);
  const pts = [[0,0],[25,9],[50,14],[100,24],[200,31],[300,34]];
  const mk = (tag, at, txt) => { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); if (txt != null) e.textContent = txt; svg.appendChild(e); return e; };
  const ff = 'JetBrains Mono, monospace';
  for (const v of [0,10,20,30,40]){ mk('line', {x1:L, x2:R, y1:Y(v), y2:Y(v), stroke:'#1d2738'}); mk('text', {x:L-8, y:Y(v)+3.5, 'text-anchor':'end', fill:'#95a3bb', 'font-size':10, 'font-family':ff}, v + '%'); }
  for (const [x] of pts) mk('text', {x:X(x), y:B+18, 'text-anchor':'middle', fill:'#95a3bb', 'font-size':10, 'font-family':ff}, x);
  mk('text', {x:R, y:B+32, 'text-anchor':'end', fill:'#5f6d85', 'font-size':9.5, 'font-family':ff}, 'recorded runs');
  mk('line', {x1:L, x2:R, y1:Y(22), y2:Y(22), stroke:'#95a3bb', 'stroke-dasharray':'4 4'});
  mk('text', {x:L+6, y:Y(22)-6, fill:'#95a3bb', 'font-size':10, 'font-family':ff}, 'best plain table · 22%');
  const d = pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]) + ' ' + Y(p[1])).join(' ');
  const area = mk('path', {d: d + ` L ${X(300)} ${B} L ${X(0)} ${B} Z`, fill:'rgba(184,255,44,.08)', opacity:0});
  const path = mk('path', {d, fill:'none', stroke:'#b8ff2c', 'stroke-width':2.5, 'stroke-linejoin':'round', style:'filter:drop-shadow(0 0 6px rgba(184,255,44,.7))'});
  const len = path.getTotalLength(); path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
  const dots = pts.map(([x, y]) => { const g = mk('g', {opacity:0});
    const c = document.createElementNS(NS, 'circle'); Object.entries({cx:X(x), cy:Y(y), r:4, fill:'#05070b', stroke:'#b8ff2c', 'stroke-width':2}).forEach(([k,v]) => c.setAttribute(k, v)); g.appendChild(c);
    const t = document.createElementNS(NS, 'text'); Object.entries({x:X(x), y:Y(y)-10, 'text-anchor': x === 300 ? 'end' : 'middle', fill:'#eef4ff', 'font-size':11, 'font-weight':700, 'font-family':ff}).forEach(([k,v]) => t.setAttribute(k, v)); t.textContent = y + '%'; g.appendChild(t);
    return g; });
  onView(svg, () => {
    path.style.transition = RM ? 'none' : 'stroke-dashoffset 2.2s cubic-bezier(.4,0,.2,1)'; path.style.strokeDashoffset = 0;
    area.style.transition = 'opacity 1s 1.6s'; area.setAttribute('opacity', 1);
    dots.forEach((g, i) => setTimeout(() => { g.style.transition = 'opacity .3s'; g.setAttribute('opacity', 1); }, RM ? 0 : 200 + i * 380));
  });
})();

/* ---------------------------------------------------------------- notes vs pack */
(function accumulation(){
  const acc = [[0,0,0],[10,4696,296],[25,11950,300],[50,24403,302],[100,48725,323],[150,73023,332],[200,97338,330],[250,122374,334],[301,146325,334]];
  const MAX = 146325, r = $('#acc-runs'), nt = $('#acc-notes'), pt = $('#acc-pack'), nb = $('#acc-notes-bar'), pb = $('#acc-pack-bar');
  const run = () => {
    const t0 = performance.now(), dur = RM ? 1 : 5200;
    const f = now => {
      const k = Math.min(1, (now - t0) / dur), runs = k * 301;
      let i = acc.findIndex(a => a[0] >= runs); if (i < 1) i = 1;
      const [r0, n0, p0] = acc[i-1], [r1, n1, p1] = acc[i], u = (runs - r0) / ((r1 - r0) || 1);
      const notes = n0 + (n1 - n0) * u, pack = k === 0 ? 0 : (runs < 10 ? 296 : Math.round(p0 + (p1 - p0) * u));
      r.textContent = Math.round(runs); nt.textContent = fmt(Math.round(notes)); pt.textContent = fmt(pack);
      nb.style.width = (notes / MAX * 100) + '%'; pb.style.width = (pack / MAX * 100) + '%';
      if (k < 1) requestAnimationFrame(f); else setTimeout(run, 4500);
    };
    requestAnimationFrame(f);
  };
  onView($('.acc'), run);
})();

/* ---------------------------------------------------------------- load test grid */
(function loadGrid(){
  const host = $('#loadgrid'); const cv = document.createElement('canvas'); cv.style.cssText = 'width:100%;height:118px;display:block';
  host.replaceWith(cv); cv.id = 'loadgrid';
  const ctx = cv.getContext('2d'); const N = 998;
  let shown = 0, startT = 0, raf = 0;
  const geom = () => { const r = cv.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
    cv.width = r.width * d; cv.height = r.height * d; ctx.setTransform(d, 0, 0, d, 0, 0);
    const area = r.width * r.height / N, s = Math.floor(Math.sqrt(area)); return {W:r.width, H:r.height, s:Math.max(3, s), cols:Math.floor(r.width / Math.max(3, s))}; };
  let g = geom(); new ResizeObserver(() => { g = geom(); draw(); }).observe(cv);
  const draw = () => {
    ctx.clearRect(0, 0, g.W, g.H);
    for (let i = 0; i < N; i++){
      const x = (i % g.cols) * g.s, y = Math.floor(i / g.cols) * g.s; if (y > g.H) break;
      const on = i < shown, fresh = on && i > shown - 14;
      ctx.fillStyle = on ? (fresh ? '#eaffb8' : '#b8ff2c') : '#141c2a';
      ctx.globalAlpha = on ? 1 : .9; ctx.fillRect(x, y, g.s - 1, g.s - 1);
    }
    ctx.globalAlpha = 1;
  };
  draw();
  const play = () => { startT = performance.now(); const dur = RM ? 1 : 6000;
    const f = now => { const k = Math.min(1, (now - startT) / dur); shown = Math.round(N * k); draw();
      if (k < 1) raf = requestAnimationFrame(f); else setTimeout(() => { shown = 0; draw(); play(); }, 4000); };
    raf = requestAnimationFrame(f); };
  onView(cv, play);
})();

/* ---------------------------------------------------------------- parity */
(function parity(){
  const el = $('#parity'); el.innerHTML = Array.from({length:102}, () => '<span>■</span>').join('');
  const s = $$('span', el);
  onView(el, () => s.forEach((x, i) => setTimeout(() => x.className = 'ok', RM ? 0 : i * 22)));
})();

/* ---------------------------------------------------------------- copy buttons */
$$('.copy').forEach(b => b.addEventListener('click', async () => {
  const txt = $('pre', b.parentElement).innerText.split('\n').map(l => l.replace(/\s+#.*$/, '')).filter(l => l.trim() && !l.trim().startsWith('#')).join('\n');
  try { await navigator.clipboard.writeText(txt); b.textContent = 'copied ✓'; } catch { b.textContent = 'select + copy'; }
  setTimeout(() => b.textContent = 'copy', 1600);
}));

/* ---------------------------------------------------------------- packs */
function parsePack(text){
  const P = {runs:0, src:[], test:[], doc:[], earlier:[]}; let sec = null;
  for (const l of text.split('\n')){
    const m0 = l.match(/^Handoff from (\d+) earlier/); if (m0){ P.runs = +m0[1]; continue; }
    if (/^Source files:/.test(l)){ sec = 'src'; continue; }
    if (/^Test files/.test(l)){ sec = 'test'; continue; }
    if (/^Docs/.test(l)){ sec = 'doc'; continue; }
    if (/^Earlier issues:/.test(l)){ P.earlier = l.slice(15).split(' | ').map(s => s.trim()).filter(Boolean); sec = null; continue; }
    const m = l.match(/^\s+(\S+)\s+opened by (\d+) earlier runs?(?: \(lines ([^)]*)\))?(?:; (\d+) concluded)?/);
    if (m && sec) P[sec].push({path:m[1], k:+m[2], lines:(m[3] || '').split(',')[0].trim(), concl:+(m[4] || 0)});
  }
  return P;
}
function hl(text, gold){
  let sec = '';
  return text.split('\n').map(l => {
    if (/^Source files:/.test(l)){ sec = 'src'; return `<span class="h-sec">${esc(l)}</span>`; }
    if (/^Test files/.test(l)){ sec = 'test'; return `<span class="h-sec">${esc(l)}</span>`; }
    if (/^Docs/.test(l)){ sec = 'doc'; return `<span class="h-sec">${esc(l)}</span>`; }
    if (/^Earlier issues:/.test(l)) return `<span class="h-sec">Earlier issues:</span><span class="h-dim">${esc(l.slice(15))}</span>`;
    if (/^Handoff from/.test(l)) return `<span class="h-dim">${esc(l)}</span>`;
    const m = l.match(/^(\s+)(\S+)(.*)$/);
    if (m && sec){ const cls = gold.has(m[2]) ? 'hit' : ({src:'h-path', test:'h-test', doc:'h-doc'})[sec]; return m[1] + `<span class="${cls}">${esc(m[2])}</span>` + esc(m[3]); }
    return esc(l);
  }).join('\n');
}
function typeInto(pre, text, gold, token){
  return new Promise(res => {
    if (RM){ pre.innerHTML = hl(text, gold); return res(); }
    let i = 0; const t0 = performance.now(), cps = text.length / 2.8;
    const f = () => { if (token.dead) return res();
      i = Math.min(text.length, Math.max(i + 1, Math.round((performance.now() - t0) / 1000 * cps))); pre.innerHTML = hl(text.slice(0, i), gold) + (i < text.length ? '<span class="caret"></span>' : '');
      pre.scrollTop = pre.scrollHeight;
      if (i < text.length) requestAnimationFrame(f); else { pre.scrollTop = 0; res(); } };
    f();
  });
}
const STOP = new Set('should when with from that this does doesn cannot into allow have been than them they were which while after before about raised raises cause causes using used make still more less only also some even other isn wasn aren work works django'.split(' '));
function wordsOf(title){
  const raw = (title.match(/[A-Za-z_][A-Za-z0-9_.]*[A-Za-z0-9_]/g) || []).map(w => w.replace(/\.$/, ''));
  const seen = new Set(), out = [];
  const score = w => (/[_.]|[a-z][A-Z]|^[A-Z][a-z]+[A-Z]/.test(w) ? 3 : 0) + (/^[A-Z]/.test(w) ? 1 : 0) + w.length / 10;
  for (const w of raw.filter(w => w.length >= 4 && !STOP.has(w.toLowerCase())).sort((a, b) => score(b) - score(a))){
    const k = w.toLowerCase(); if (seen.has(k)) continue; seen.add(k); out.push(w); if (out.length >= 4) break;
  }
  return out.length ? out : ['task'];
}

/* traversal scene: words -> runs -> files -> tests/docs */
function buildTraversal(net, P, words, gold=new Set()){
  net.clear();
  const sm = net.small, X = sm ? [.02, .26, .47, .73] : [.02, .24, .45, .72];
  net.heads = sm ? null : [[X[0], 'HTerm'], [X[1], 'HRun'], [X[2], 'HFile · source'], [X[3], 'HFile · tests, docs']];
  const ys = (n, top=.14, bot=.94) => Array.from({length:n}, (_, i) => n === 1 ? (top + bot) / 2 : top + (bot - top) * i / (n - 1));
  const nR = Math.min(P.runs || 5, sm ? 7 : 9);
  words.forEach((w, i) => net.node('w'+i, {kind:'term', label:'word:' + w.toLowerCase(), short:w.toLowerCase(), x:X[0], y:ys(words.length, .25, .8)[i], ta:1}));
  const ry = ys(nR);
  for (let i = 0; i < nR; i++){
    const t = P.earlier[i];
    net.node('r'+i, {kind:'run', label: t ? 'run · ' + t.slice(0, 15) + '…' : 'run ' + (i + 1), short: 'run ' + (i + 1), x:X[1], y:ry[i], ta:0, pulse:true});
    net.edge('w' + (i % words.length), 'r'+i, {ta:0, dash:true, color:'#4a2a45', litc:COL.mag, lbl:'ABOUT'});
    if (words.length > 1 && i % 2) net.edge('w' + ((i + 1) % words.length), 'r'+i, {ta:0, dash:true, color:'#4a2a45', litc:COL.mag});
  }
  const sy = ys(P.src.length, .14, .9);
  P.src.forEach((f, j) => {
    net.node('s'+j, {kind:'file', label:short2(f.path), short:base(f.path), x:X[2], y:sy[j], ta:0, pulse:true, path:f.path, gold:false, isGold:gold.has(f.path)});
    for (let m = 0; m < Math.min(f.k, nR, 3); m++){
      const r = (j * 2 + m * 3) % nR, concl = m < f.concl;
      net.edge('r'+r, 's'+j, {ta:0, color: concl ? '#5a3410' : COL.dim2, litc: concl ? COL.orange : COL.cyan, w: concl ? 1.6 : 1, lbl: concl ? 'CONCLUDED' : (f.lines ? 'READ ' + f.lines : 'READ'), hop:2});
    }
  });
  const td = [...P.test.map(f => ({...f, kind:'test'})), ...P.doc.map(f => ({...f, kind:'doc'}))];
  const ty = ys(td.length, .12, .92);
  td.forEach((f, j) => {
    net.node('t'+j, {kind:f.kind, label:short2(f.path), short:base(f.path), x:X[3], y:ty[j], ta:0, pulse:true, path:f.path, isGold:gold.has(f.path)});
    const src = j % Math.max(1, P.src.length);
    if (P.src.length) net.edge('s'+src, 't'+j, {ta:0, dash:true, color:COL.dim2, litc: f.kind === 'test' ? COL.lime : COL.yel, hop:3});
  });
  return {nR, nS:P.src.length, nT:td.length};
}
async function playTraversal(net, info, token, onHop=()=>{}){
  const E = net.edges, alive = () => !token.dead;
  onHop(1);
  for (const n of net.nodes.values()) if (n.kind === 'term') n.tl = 1;
  await sleep(350); if (!alive()) return;
  const h1 = E.filter(e => e.a[0] === 'w');
  h1.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h1.map((e, i) => sleep(i * 60).then(() => alive() && net.packet(e.a, e.b, COL.mag, 600))));
  if (!alive()) return;
  for (let i = 0; i < info.nR; i++){ const n = net.nodes.get('r'+i); if (n){ n.ta = 1; n.tl = 1; n.born = net.t; } }
  for (const n of net.nodes.values()) if (n.kind === 'term') n.tl = .25;
  h1.forEach(e => e.tl = .15);
  await sleep(450); if (!alive()) return;
  onHop(2);
  const h2 = E.filter(e => e.hop === 2);
  h2.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h2.map((e, i) => sleep(i * 45).then(() => alive() && net.packet(e.a, e.b, e.litc, 650))));
  if (!alive()) return;
  for (let j = 0; j < info.nS; j++){ const n = net.nodes.get('s'+j); n.ta = 1; n.tl = 1; n.born = net.t; }
  for (let i = 0; i < info.nR; i++){ const n = net.nodes.get('r'+i); if (n) n.tl = .2; }
  await sleep(450); if (!alive()) return;
  h2.forEach(e => e.tl = .12);
  onHop(3);
  const h3 = E.filter(e => e.hop === 3);
  h3.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h3.map((e, i) => sleep(i * 70).then(() => alive() && net.packet(e.a, e.b, e.litc, 600))));
  if (!alive()) return;
  for (let j = 0; j < info.nT; j++){ const n = net.nodes.get('t'+j); n.ta = 1; n.tl = 1; n.born = net.t; }
  await sleep(600); if (!alive()) return;
  h3.forEach(e => e.tl = .12);
  onHop(4);
  for (const n of net.nodes.values()){
    if (n.isGold){ n.gold = true; n.tl = 1; n.badge = '▲ real fix'; }
    else if (n.kind !== 'run' && n.kind !== 'term') n.tl = 0;
  }
}

/* ---------------------------------------------------------------- hero scene */
async function heroScene(PACKS){
  const net = new Net($('#hero-cv'), {max:24, drift:3});
  const hud = $('#hero-hud'), runsEl = $('#hero-runs'), packsEl = $('#hero-packs');
  const srcs = [...new Set(PACKS.flatMap(p => parsePack(p.pack).src.map(f => f.path)))];
  const tests = [...new Set(PACKS.flatMap(p => parsePack(p.pack).test.map(f => f.path)))];
  const ranges = PACKS.flatMap(p => parsePack(p.pack).src.map(f => f.lines)).filter(Boolean);
  const terms = ['word:floatformat','sym:Decimal','word:constraint','sym:refresh_from_db','word:sqlite','sym:ValidationError','word:migrate','sym:DecimalField'];
  const shuffle = a => a.map(v => [Math.random(), v]).sort((x, y) => x[0] - y[0]).map(v => v[1]);
  const sm = net.W < 620, X = sm ? [.02, .3, .5, .75] : [.03, .3, .5, .79];
  const NT = sm ? 6 : 7, NF = sm ? 6 : 8, NX = 4, NRUN = sm ? 5 : 6;
  const ys = (n, top, bot) => Array.from({length:n}, (_, i) => top + (bot - top) * (i + .5) / n);
  terms.slice(0, NT).forEach((t, i) => net.node('T'+i, {kind:'term', label:t, short:t.split(':')[1], x:X[0], y:ys(NT, .03, .97)[i]}));
  shuffle(srcs).slice(0, NF).forEach((f, i) => net.node('F'+i, {kind:'file', label:short2(f), short:base(f), x:X[2], y:ys(NF, .03, .97)[i]}));
  shuffle(tests).slice(0, NX).forEach((f, i) => net.node('X'+i, {kind:'test', label:base(f), short:base(f), x:X[3], y:ys(NX, .1, .9)[i]}));
  const slotY = ys(NRUN, .06, .94), slots = Array(NRUN).fill(null);
  let seq = 0x3a0, runs = 0, packs = 0, oldest = 0;
  const rnd = n => Math.floor(Math.random() * n);
  function addRun(slot, instant){
    const id = 'R' + (++seq);
    net.node(id, {kind:'run', label:'HRun ' + seq.toString(16), short:'run ' + seq.toString(16), x:X[1], y:slotY[slot], a: instant ? 1 : 0, pulse:!instant, born:net.t});
    const ts = shuffle([...Array(NT).keys()]).slice(0, 2), fs = shuffle([...Array(NF).keys()]).slice(0, 2 + rnd(2)), tx = rnd(NX);
    const es = [];
    ts.forEach(t => es.push(net.edge('T'+t, id, {dash:true, color:'#4a2a45', litc:COL.mag, lbl:'ABOUT', al: instant ? 1 : 0})));
    fs.forEach((f, k) => es.push(net.edge(id, 'F'+f, {color: k === 0 ? '#5a3410' : COL.dim2, w: k === 0 ? 1.6 : 1, litc: k === 0 ? COL.orange : COL.cyan, lbl: k === 0 ? 'CONCLUDED' : 'READ {' + pick(ranges) + '}', al: instant ? 1 : 0})));
    es.push(net.edge(id, 'X'+tx, {color:COL.dim2, litc:COL.lime, lbl:'READ', al: instant ? 1 : 0}));
    slots[slot] = id; return {id, es};
  }
  for (let s = 0; s < NRUN; s++){ addRun(s, true); runs++; }
  runsEl.textContent = runs;
  const clearLit = () => { for (const n of net.nodes.values()) n.tl = 0; for (const e of net.edges) e.tl = 0; };
  while (true){
    await net.visible();
    /* write */
    const slot = oldest; oldest = (oldest + 1) % NRUN;
    hud.innerHTML = '<span style="color:var(--orange)">● write</span> retire oldest run';
    const old = slots[slot];
    if (old){ const on = net.nodes.get(old); on.ta = 0; on.kill = true; net.edges.forEach(e => { if (e.a === old || e.b === old){ e.ta = 0; e.kill = true; } }); }
    await sleep(650);
    hud.innerHTML = '<span style="color:var(--orange)">● write</span> run finished → nodes · 0 model calls';
    const {id, es} = addRun(slot, false);
    es.forEach(e => e.al = 0);
    await sleep(250);
    for (const e of es){ e.tl = 1; await net.packet(e.a, e.b, e.litc, 420); e.tl = .0; }
    runs++; runsEl.textContent = runs;
    await sleep(700);
    /* read */
    const about = es.filter(e => e.a[0] === 'T');
    const qTerms = new Set(about.map(e => e.a)); qTerms.add('T' + rnd(NT));
    hud.innerHTML = '<span style="color:var(--cyan)">● read</span> new task → entities';
    qTerms.forEach(t => net.nodes.get(t).tl = 1);
    await sleep(500);
    hud.innerHTML = '<span style="color:var(--cyan)">● read</span> hop 1/3 · algo.MSpaths ABOUT';
    const h1 = net.edges.filter(e => qTerms.has(e.a) && e.ta === 1);
    h1.forEach(e => e.tl = 1);
    await Promise.all(h1.map((e, i) => sleep(i * 70).then(() => net.packet(e.a, e.b, COL.mag, 600))));
    const hitRuns = new Set(h1.map(e => e.b)); hitRuns.forEach(r => { const n = net.nodes.get(r); if (n) n.tl = 1; });
    await sleep(350);
    hud.innerHTML = '<span style="color:var(--cyan)">● read</span> hop 2/3 · runs → READ, CONCLUDED';
    const h2 = net.edges.filter(e => hitRuns.has(e.a) && e.ta === 1);
    h2.forEach(e => e.tl = 1);
    await Promise.all(h2.map((e, i) => sleep(i * 50).then(() => net.packet(e.a, e.b, e.litc, 600))));
    h2.forEach(e => { const n = net.nodes.get(e.b); if (n) n.tl = 1; });
    await sleep(350);
    hud.innerHTML = '<span style="color:var(--cyan)">● read</span> hop 3/3 · files → their tests';
    const litF = h2.map(e => e.b).filter(b => b[0] === 'F');
    const tmp = litF.slice(0, 3).map(f => net.edge(f, 'X' + rnd(NX), {dash:true, color:COL.dim2, litc:COL.lime, tl:1}));
    await Promise.all(tmp.map((e, i) => sleep(i * 80).then(() => net.packet(e.a, e.b, COL.lime, 550))));
    tmp.forEach(e => { const n = net.nodes.get(e.b); if (n) n.tl = 1; });
    packs++; packsEl.textContent = packs;
    hud.innerHTML = '<span style="color:var(--lime)">● pack ready</span> → next agent';
    await sleep(1700);
    clearLit(); tmp.forEach(e => { e.ta = 0; e.kill = true; });
    hud.innerHTML = '<span class="c-dim">idle</span>';
    await sleep(700);
  }
}

/* ---------------------------------------------------------------- write scene */
async function writeScene(){
  const net = new Net($('#write-cv'), {max:26, drift:1.5, fs:11});
  const log = $('#write-log');
  const L = [
    ['task', '$ agent run · "Make floatformat template filter independent of USE_L10N…"'],
    ['f0', '▸ sed -n 1,260p django/template/defaultfilters.py'],
    ['f1', '▸ sed -n 1,120p tests/template_tests/filter_tests/test_floatformat.py'],
    ['f2', '▸ sed -n 1670,1760p docs/ref/templates/builtins.txt'],
    ['ans', '✓ answer: the fix belongs in django/template/defaultfilters.py'],
    ['done', '── recorded · 1 HRun · 3 READ · 1 CONCLUDED · 0 model calls'],
  ];
  const files = [
    {id:'f0', kind:'file', label:'template/defaultfilters.py', short:'defaultfilters.py', lines:'1-260', y:.2},
    {id:'f1', kind:'test', label:'test_floatformat.py', short:'test_floatformat', lines:'1-120', y:.5},
    {id:'f2', kind:'doc', label:'templates/builtins.txt', short:'builtins.txt', lines:'1670-1760', y:.8},
  ];
  const typeLine = async (txt, cls) => {
    const span = document.createElement('div'); if (cls) span.style.color = cls; log.appendChild(span);
    for (let i = 0; i <= txt.length; i += RM ? txt.length : 2){ span.textContent = txt.slice(0, i); await sleep(12); }
    span.textContent = txt;
  };
  while (true){
    await net.visible();
    net.clear(); log.innerHTML = '';
    for (const [k, txt] of L){
      await typeLine(txt, k === 'ans' ? COL.lime : k === 'done' ? COL.orange : k === 'task' ? COL.text : null);
      if (k === 'task'){
        net.node('run', {kind:'run', label:'HRun · floatformat', short:'HRun', x:.34, y:.5, pulse:true});
        ['word:floatformat', 'sym:USE_L10N', 'word:unlocalized'].forEach((t, i) => {
          net.node('t'+i, {kind:'term', label:t, short:t.split(':')[1], x:.02, y:.2 + i * .3});
          net.edge('t'+i, 'run', {dash:true, color:'#4a2a45', litc:COL.mag, lbl:'ABOUT', showLbl:i === 1});
        });
        await sleep(200);
        await Promise.all([0,1,2].map(i => net.packet('t'+i, 'run', COL.mag, 500)));
      } else if (k[0] === 'f'){
        const f = files.find(x => x.id === k);
        net.node(f.id, {kind:f.kind, label:f.label, short:f.short, x:.6, y:f.y, pulse:true});
        const e = net.edge('run', f.id, {color:COL.dim2, litc: f.kind === 'test' ? COL.lime : f.kind === 'doc' ? COL.yel : COL.cyan, lbl:'READ {' + f.lines + '}', showLbl:true, tl:1});
        await net.packet('run', f.id, e.litc, 520); e.tl = .3;
      } else if (k === 'ans'){
        const e = net.edge('run', 'f0', {color:'#5a3410', litc:COL.orange, w:2, tl:1});
        net.edges.find(x => x.b === 'f0' && x.lbl).lbl = 'READ {1-260} + CONCLUDED';
        await net.packet('run', 'f0', COL.orange, 600);
        net.nodes.get('f0').tl = 1;
      }
      await sleep(260);
    }
    await sleep(3200);
  }
}

/* ---------------------------------------------------------------- read scene (15863) */
async function readScene(P15){
  const net = new Net($('#read-cv'), {max:26, drift:1.5, fs:10.5, smax:14});
  const P = parsePack(P15.pack), gold = new Set([...P15.gold_src, ...P15.gold_tests]);
  const words = ['floatformat', 'Decimal', 'precision'];
  const hops = $$('#read-hops span');
  while (true){
    await net.visible();
    const token = {};
    const info = buildTraversal(net, P, words, gold);
    await playTraversal(net, info, token, h => hops.forEach(s => s.classList.toggle('on', +s.dataset.h === h)));
    await sleep(3600);
    hops.forEach(s => s.classList.remove('on'));
  }
}

/* ---------------------------------------------------------------- try it */
function tryIt(PACKS){
  const list = $('#issues'), pre = $('#try-pack'), meta = $('#try-meta'), idEl = $('#try-id'), hud = $('#try-hud');
  const net = new Net($('#try-cv'), {max:34, drift:1.5, smax:15});
  let token = {dead:true};
  PACKS.forEach((p, i) => {
    const b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'option');
    b.innerHTML = `<span class="ires ${p.both ? 'y' : 'n'}">${p.both ? 'held fix' : 'missed'}</span><span class="iid">#${p.id.split('-').pop()}</span>${esc(p.title)}`;
    b.addEventListener('click', () => run(i));
    list.appendChild(b);
  });
  async function run(i){
    token.dead = true; token = {dead:false}; const tk = token;
    $$('button', list).forEach((b, j) => b.setAttribute('aria-selected', j === i));
    const p = PACKS[i], P = parsePack(p.pack), gold = new Set([...p.gold_src, ...p.gold_tests]);
    idEl.textContent = p.id; pre.innerHTML = ''; meta.innerHTML = `<span>building pack…</span>`;
    const info = buildTraversal(net, P, wordsOf(p.title), gold);
    const hopTxt = ['', 'hop 1/3 · task → earlier runs', 'hop 2/3 · runs → files', 'hop 3/3 · files → tests, docs', 'pack ready'];
    await playTraversal(net, info, tk, h => { if (!tk.dead) hud.innerHTML = `<span style="color:${h === 4 ? 'var(--lime)' : 'var(--cyan)'}">●</span> ${hopTxt[h]}`; });
    if (tk.dead) return;
    await typeInto(pre, p.pack, gold, tk);
    if (tk.dead) return;
    const srcIn = p.gold_src.filter(f => p.pack.includes(f)).length, testIn = p.gold_tests.some(f => p.pack.includes(f));
    meta.innerHTML = `<span>pack <b>${p.tokens}</b> tokens</span>
      <span>real fix files in pack <b class="${srcIn === p.gold_src.length ? 'y' : 'n'}">${srcIn}/${p.gold_src.length}</b></span>
      <span>real test file in pack <b class="${testIn ? 'y' : 'n'}">${testIn ? 'yes' : 'no'}</b></span>
      <span>live agent with this pack <b class="${p.agent_success ? 'y' : 'n'}">${p.agent_success ? 'solved' : 'not solved'}</b></span>`;
  }
  onView($('#try'), () => run(0), 0.15);
}

/* ---------------------------------------------------------------- boot */
fetch('packs.json').then(r => r.json()).then(PACKS => {
  const P15 = PACKS.find(p => p.id === 'django__django-15863');
  const gold15 = new Set([...P15.gold_src, ...P15.gold_tests]);
  const pre = $('#pack-1586'); $('#pk-tok').textContent = P15.tokens + ' tokens';
  pre.innerHTML = hl(P15.pack, gold15);
  onView(pre, () => { pre.innerHTML = ''; typeInto(pre, P15.pack, gold15, {}); }, 0.2);
  heroScene(PACKS); writeScene(); readScene(P15); tryIt(PACKS);
}).catch(err => { console.warn('packs.json unavailable', err); });
