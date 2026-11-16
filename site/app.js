'use strict';
/* HandoffDB showcase. Light theme matching the launch video. No dependencies. */
const COL = { blue:'#0284c7', teal:'#14b8a6', orange:'#f97316', green:'#16a34a', yellow:'#ca8a04', text:'#111827', dim:'#475569', faint:'#8b95a7', gray:'#94a3b8', line:'rgba(15,23,42,0.12)' };
const SOFT = { '#0284c7':'rgba(2,132,199,0.12)', '#14b8a6':'rgba(20,184,166,0.14)', '#f97316':'rgba(249,115,22,0.13)', '#16a34a':'rgba(22,163,74,0.12)', '#ca8a04':'rgba(234,179,8,0.16)' };
const KIND = { term:COL.blue, run:COL.teal, file:COL.orange, test:COL.green, doc:COL.yellow };
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const COARSE = matchMedia('(pointer: coarse)').matches;
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, RM ? Math.min(ms, 300) : ms));
const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt = (v, dec=0) => v.toLocaleString('en-US', {minimumFractionDigits:dec, maximumFractionDigits:dec});
const base = p => p.split('/').pop();
const short2 = p => p.split('/').slice(-2).join('/');
const shuffle = a => a.map(v => [Math.random(), v]).sort((x, y) => x[0] - y[0]).map(v => v[1]);
function bz(t, a, b, c, d){ const u = 1 - t; return u*u*u*a + 3*u*u*t*b + 3*u*t*t*c + t*t*t*d; }
function rrect(c, x, y, w, h, r){ c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }

/* ---------------------------------------------------------------- reveal + count-ups */
function onView(el, fn, th=0.3){
  if (!el) return;
  const io = new IntersectionObserver(es => { if (es[0].isIntersecting){ io.disconnect(); document.fonts.ready.then(fn); } }, {threshold: th});
  io.observe(el);
}
$$('.reveal').forEach(el => onView(el, () => el.classList.add('in'), 0.12));
function countUp(el){
  const to = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0), suf = el.dataset.suffix || '';
  const t0 = performance.now(), dur = RM ? 1 : 1500;
  const f = now => { const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(to * e, dec) + suf; if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
$$('[data-count]').forEach(el => onView(el, () => countUp(el), 0.5));

/* ---------------------------------------------------------------- background graph that follows the cursor */
(function background(){
  const cv = $('#bg'), c = cv.getContext('2d'); const cols = [COL.blue, COL.teal, COL.orange, COL.green];
  let W = 0, H = 0, nodes = [], mouse = {x:-9999, y:-9999, on:false};
  const init = () => {
    const d = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight;
    cv.width = W * d; cv.height = H * d; c.setTransform(d, 0, 0, d, 0, 0);
    const n = Math.min(80, Math.round(W * H / 24000));
    nodes = Array.from({length:n}, () => ({x:Math.random() * W, y:Math.random() * H, vx:(Math.random() - .5) * .16, vy:(Math.random() - .5) * .16, col:cols[Math.floor(Math.random() * 4)], r:2.2 + Math.random() * 1.6, glow:0}));
  };
  const LINK = 140, REACH = 190;
  const draw = () => {
    c.clearRect(0, 0, W, H);
    for (let i = 0; i < nodes.length; i++){
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++){
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy);
        if (d < LINK){ c.globalAlpha = (1 - d / LINK) * (0.10 + 0.25 * Math.max(a.glow, b.glow)); c.strokeStyle = '#334155'; c.lineWidth = 1; c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke(); }
      }
    }
    for (const a of nodes){
      if (mouse.on){ const d = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        if (d < REACH){ c.globalAlpha = (1 - d / REACH) * 0.45; c.strokeStyle = a.col; c.lineWidth = 1.2; c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(mouse.x, mouse.y); c.stroke(); } }
      c.globalAlpha = 0.28 + 0.6 * a.glow; c.fillStyle = '#fff'; c.strokeStyle = a.col; c.lineWidth = 1.6;
      c.beginPath(); c.arc(a.x, a.y, a.r + a.glow * 1.8, 0, 6.283); c.fill(); c.stroke();
    }
    c.globalAlpha = 1;
  };
  const step = () => {
    for (const a of nodes){
      a.x += a.vx; a.y += a.vy;
      if (a.x < -20) a.x = W + 20; if (a.x > W + 20) a.x = -20; if (a.y < -20) a.y = H + 20; if (a.y > H + 20) a.y = -20;
      let g = 0;
      if (mouse.on){ const dx = mouse.x - a.x, dy = mouse.y - a.y, d = Math.hypot(dx, dy);
        if (d < REACH){ g = 1 - d / REACH; a.x += dx * 0.004 * g; a.y += dy * 0.004 * g; } }
      a.glow += (g - a.glow) * 0.08;
    }
  };
  init(); draw();
  addEventListener('resize', () => { init(); draw(); });
  if (RM) return;
  if (!COARSE){
    addEventListener('pointermove', e => { mouse.x = e.clientX; mouse.y = e.clientY; mouse.on = true; }, {passive:true});
    document.addEventListener('pointerleave', () => { mouse.on = false; });
  }
  const loop = () => { if (!document.hidden){ step(); draw(); } requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
})();

/* ---------------------------------------------------------------- graph engine (cards or rings) */
class Net {
  constructor(cv, opt={}){
    this.cv = cv; this.ctx = cv.getContext('2d'); this.opt = opt; this.mode = opt.mode || 'card';
    this.nodes = new Map(); this.edges = []; this.pk = []; this.t = 0; this.vis = false; this.last = 0; this.waiters = [];
    this.resize();
    new ResizeObserver(() => this.resize()).observe(cv);
    new IntersectionObserver(es => { this.vis = es[0].isIntersecting; if (this.vis){ this.waiters.forEach(f => f()); this.waiters = []; } }, {threshold:0.15}).observe(cv);
    const loop = ts => { const dt = Math.min(0.2, (ts - this.last) / 1000 || 0); this.last = ts;
      if (this.vis){ this.t += dt; this.step(dt); this.draw(); } requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }
  visible(){ return this.vis ? Promise.resolve() : new Promise(r => this.waiters.push(r)); }
  resize(){
    const r = this.cv.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
    this.W = r.width; this.H = r.height;
    this.cv.width = Math.max(1, Math.round(r.width * d)); this.cv.height = Math.max(1, Math.round(r.height * d));
    this.ctx.setTransform(d, 0, 0, d, 0, 0);
    this.small = this.W < 620; this.fs = this.small ? 10 : (this.opt.fs || 12); this.wc = {};
  }
  clear(){ this.nodes.clear(); this.edges = []; this.pk.forEach(p => p.res()); this.pk = []; }
  node(id, o){ const n = Object.assign({id, x:.5, y:.5, a:0, ta:1, lit:0, tl:0, born:this.t}, o); this.nodes.set(id, n); return n; }
  edge(a, b, o={}){ const e = Object.assign({a, b, al:0, ta:1, lit:0, tl:0}, o); this.edges.push(e); return e; }
  label(n){
    let s = (this.small && n.short) ? n.short : n.label;
    const max = this.opt.fit ? Math.max(6, Math.floor((this.W * 0.245 - 36) / (this.fs * 0.61))) : (this.small ? (this.opt.smax || 16) : (this.opt.max || 30));
    return s.length > max ? s.slice(0, max - 1) + '…' : s;
  }
  tw(s){ if (this.wc[s] == null){ this.ctx.font = `500 ${this.fs}px "JetBrains Mono", monospace`; this.wc[s] = this.ctx.measureText(s).width; } return this.wc[s]; }
  box(n){ const w = this.tw(this.label(n)) + 26, h = this.fs * 2.3; return {x:n.x * this.W, y:n.y * this.H - h / 2, w, h}; }
  side(n, s){
    if (this.mode === 'ring'){ const x = n.x * this.W, y = n.y * this.H; return [x + (s === 'r' ? 9 : -9), y]; }
    const b = this.box(n); return [s === 'r' ? b.x + b.w : b.x, b.y + b.h / 2];
  }
  ends(a, b){
    const A = this.nodes.get(a), B = this.nodes.get(b); if (!A || !B) return null;
    const fw = A.x <= B.x;
    return [fw ? this.side(A,'r') : this.side(A,'l'), fw ? this.side(B,'l') : this.side(B,'r')];
  }
  packet(a, b, color=COL.blue, dur=700){ return new Promise(res => this.pk.push({a, b, color, t:0, dur: RM ? 60 : dur, res, done:false})); }
  step(dt){
    const k = Math.min(1, dt * 5);
    for (const n of this.nodes.values()){ n.a += (n.ta - n.a) * k; n.lit += (n.tl - n.lit) * k; }
    for (const e of this.edges){ e.al += (e.ta - e.al) * k; e.lit += (e.tl - e.lit) * k; }
    this.edges = this.edges.filter(e => !(e.kill && e.al < 0.02));
    for (const [id, n] of this.nodes) if (n.kill && n.a < 0.02) this.nodes.delete(id);
    for (const p of this.pk){ p.t += dt * 1000 / p.dur; if (p.t >= 1 && !p.done){ p.done = true; p.res(); } }
    this.pk = this.pk.filter(p => p.t < 1.15);
  }
  draw(){
    const c = this.ctx, fs = this.fs;
    c.clearRect(0, 0, this.W, this.H);
    if (this.heads){
      c.font = `600 ${fs}px Inter, sans-serif`; c.textBaseline = 'top';
      for (const h of this.heads){ c.fillStyle = h[2] || COL.dim; const w = c.measureText(h[1]).width; const hx = this.mode === 'ring' ? Math.min(this.W - w, Math.max(0, h[0] * this.W - w / 2)) : h[0] * this.W; c.fillText(h[1], hx, 6); }
    }
    for (const e of this.edges){
      const en = this.ends(e.a, e.b); if (!en) continue;
      const [[x1,y1],[x2,y2]] = en, dx = (x2 - x1) * .5;
      const col = e.color || COL.gray;
      c.beginPath(); c.moveTo(x1, y1); c.bezierCurveTo(x1 + dx, y1, x2 - dx, y2, x2, y2);
      c.globalAlpha = e.al * ((e.base ?? 0.22) + 0.6 * e.lit); c.strokeStyle = col; c.lineWidth = (e.w || 1.2) + e.lit * 1.2;
      c.setLineDash(e.dash && e.lit < .5 ? [3, 4] : []); c.stroke(); c.setLineDash([]);
      if (e.lbl && !this.small && e.al > .5 && (e.lit > .5 || e.showLbl)){
        const mx = bz(.5, x1, x1 + dx, x2 - dx, x2), my = bz(.5, y1, y1, y2, y2);
        c.font = `500 ${fs - 2.5}px "JetBrains Mono", monospace`; c.textBaseline = 'middle';
        const w = c.measureText(e.lbl).width;
        c.globalAlpha = e.al; c.fillStyle = '#fff'; rrect(c, mx - w/2 - 5, my - 8, w + 10, 16, 8); c.fill();
        c.fillStyle = col; c.fillText(e.lbl, mx - w/2, my + .5);
      }
    }
    for (const p of this.pk){
      const en = this.ends(p.a, p.b); if (!en) continue;
      const [[x1,y1],[x2,y2]] = en, dx = (x2 - x1) * .5, t = Math.min(1, p.t);
      const x = bz(t, x1, x1 + dx, x2 - dx, x2), y = bz(t, y1, y1, y2, y2);
      c.globalAlpha = p.t > 1 ? Math.max(0, 1 - (p.t - 1) * 7) : 1; c.fillStyle = p.color;
      c.beginPath(); c.arc(x, y, 4, 0, 6.283); c.fill();
    }
    for (const n of this.nodes.values()){
      if (n.a < .01) continue;
      const col = n.gold ? COL.blue : KIND[n.kind];
      if (this.mode === 'ring'){
        const x = n.x * this.W, y = n.y * this.H, r = 8 + n.lit * 1.5;
        if (n.lit > .05){ c.globalAlpha = n.a * n.lit * .5; c.fillStyle = SOFT[col]; c.beginPath(); c.arc(x, y, r + 7, 0, 6.283); c.fill(); }
        c.globalAlpha = n.a; c.fillStyle = '#fff'; c.strokeStyle = col; c.lineWidth = 3;
        c.beginPath(); c.arc(x, y, r, 0, 6.283); c.fill(); c.stroke();
        continue;
      }
      const b = this.box(n), s = this.label(n);
      c.globalAlpha = n.a;
      c.shadowColor = 'rgba(15,23,42,0.06)'; c.shadowBlur = 8; c.shadowOffsetY = 2;
      c.fillStyle = '#fff'; rrect(c, b.x, b.y, b.w, b.h, 8); c.fill();
      c.shadowColor = 'transparent'; c.shadowBlur = 0; c.shadowOffsetY = 0;
      if (n.lit > .02){ c.globalAlpha = n.a * Math.min(1, n.lit); c.fillStyle = SOFT[col]; rrect(c, b.x, b.y, b.w, b.h, 8); c.fill(); }
      c.globalAlpha = n.a; c.lineWidth = 1; c.strokeStyle = n.lit > .4 ? col : COL.line; rrect(c, b.x + .5, b.y + .5, b.w - 1, b.h - 1, 8); c.stroke();
      c.fillStyle = col; c.beginPath(); c.arc(b.x + 11, b.y + b.h / 2, 3.2, 0, 6.283); c.fill();
      c.font = `500 ${fs}px "JetBrains Mono", monospace`; c.textBaseline = 'middle'; c.fillStyle = COL.text;
      c.fillText(s, b.x + 20, b.y + b.h / 2 + .5);
      if (n.badge){ c.font = `700 ${fs - 2}px Inter, sans-serif`; c.fillStyle = COL.blue; c.fillText(n.badge, b.x + 2, b.y + b.h + fs * .75); }
    }
    c.globalAlpha = 1;
  }
}

/* ---------------------------------------------------------------- bars */
onView($('#prob'), () => {
  $('#seg-post').style.width = '93%';
  $$('#prob-bars .bar').forEach((r, j) => setTimeout(() => { const i = $('.bt i', r); i.className = 'f-' + r.dataset.c; i.style.width = (+r.dataset.v / +r.dataset.max * 100) + '%'; }, RM ? 0 : 500 + j * 180));
});
onView($('#ret-bars'), () => $$('#ret-bars .bar').forEach((r, j) => setTimeout(() => { const i = $('.bt i', r); i.className = 'f-' + r.dataset.c; i.style.width = (+r.dataset.v / +r.dataset.max * 100) + '%'; }, RM ? 0 : j * 220)));

/* ---------------------------------------------------------------- learning curve */
(function curve(){
  const svg = $('#curve'), NS = 'http://www.w3.org/2000/svg';
  const L = 44, R = 404, T = 22, B = 210, X = v => L + v / 300 * (R - L), Y = v => B - v / 40 * (B - T);
  const pts = [[0,0],[25,9],[50,14],[100,24],[200,31],[300,34]];
  const mk = (tag, at, txt, parent=svg) => { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); if (txt != null) e.textContent = txt; parent.appendChild(e); return e; };
  const mf = 'JetBrains Mono, monospace', sf = 'Inter, sans-serif';
  for (const v of [0,10,20,30,40]){ mk('line', {x1:L, x2:R, y1:Y(v), y2:Y(v), stroke:'rgba(15,23,42,0.08)'}); mk('text', {x:L-8, y:Y(v)+4, 'text-anchor':'end', fill:'#8b95a7', 'font-size':11, 'font-family':mf}, v + '%'); }
  for (const [x] of pts) mk('text', {x:X(x), y:B+18, 'text-anchor':'middle', fill:'#8b95a7', 'font-size':11, 'font-family':mf}, x);
  mk('text', {x:(L+R)/2, y:B+38, 'text-anchor':'middle', fill:'#475569', 'font-size':12, 'font-family':sf}, 'recorded runs');
  mk('line', {x1:L, x2:R, y1:Y(22), y2:Y(22), stroke:'#94a3b8', 'stroke-dasharray':'5 5'});
  mk('text', {x:L+8, y:Y(22)-7, fill:'#8b95a7', 'font-size':11, 'font-family':sf}, 'best plain table · 22%');
  const d = pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]) + ' ' + Y(p[1])).join(' ');
  const area = mk('path', {d: d + ` L ${X(300)} ${B} L ${X(0)} ${B} Z`, fill:'rgba(20,184,166,0.14)', opacity:0});
  const path = mk('path', {d, fill:'none', stroke:'#14b8a6', 'stroke-width':3, 'stroke-linejoin':'round', 'stroke-linecap':'round'});
  const len = path.getTotalLength(); path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
  const dots = pts.map(([x, y], i) => { const g = mk('g', {opacity:0});
    mk('circle', {cx:X(x), cy:Y(y), r:5, fill:'#fff', stroke:'#14b8a6', 'stroke-width':2.5}, null, g);
    if (i) mk('text', {x:X(x), y:Y(y)-12, 'text-anchor': x === 300 ? 'end' : 'middle', fill: x === 300 ? '#0f766e' : '#475569', 'font-size': x === 300 ? 15 : 11.5, 'font-weight':700, 'font-family':sf}, y + '%', g);
    return g; });
  onView(svg, () => {
    path.style.transition = RM ? 'none' : 'stroke-dashoffset 2.2s cubic-bezier(.4,0,.2,1)'; path.style.strokeDashoffset = 0;
    area.style.transition = 'opacity 1s 1.4s'; area.setAttribute('opacity', 1);
    dots.forEach((g, i) => setTimeout(() => { g.style.transition = 'opacity .4s'; g.setAttribute('opacity', 1); }, RM ? 0 : 200 + i * 380));
  });
})();

/* ---------------------------------------------------------------- notes vs pack */
(function accumulation(){
  const acc = [[0,0,0],[10,4696,296],[25,11950,300],[50,24403,302],[100,48725,323],[150,73023,332],[200,97338,330],[250,122374,334],[301,146325,334]];
  const MAX = 146325, r = $('#acc-runs'), nt = $('#acc-notes'), pt = $('#acc-pack'), nb = $('#acc-notes-bar'), pb = $('#acc-pack-bar');
  const run = () => {
    const t0 = performance.now(), dur = RM ? 1 : 5000;
    const f = now => {
      const k = Math.min(1, (now - t0) / dur), runs = k * 301;
      let i = acc.findIndex(a => a[0] >= runs); if (i < 1) i = 1;
      const [r0, n0, p0] = acc[i-1], [r1, n1, p1] = acc[i], u = (runs - r0) / ((r1 - r0) || 1);
      const notes = n0 + (n1 - n0) * u, pack = k === 0 ? 0 : (runs < 10 ? 296 : Math.round(p0 + (p1 - p0) * u));
      r.textContent = Math.round(runs); nt.textContent = fmt(Math.round(notes)); pt.textContent = fmt(pack);
      nb.style.width = (notes / MAX * 100) + '%'; pb.style.width = (pack / MAX * 100) + '%';
      if (k < 1) requestAnimationFrame(f);
    };
    requestAnimationFrame(f);
  };
  onView($('.acc-box'), run, 0.5);
})();

/* ---------------------------------------------------------------- load test grid */
(function loadGrid(){
  const cv = $('#loadgrid'), ctx = cv.getContext('2d'), N = 998;
  let shown = 0, g;
  const geom = () => { const r = cv.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
    cv.width = r.width * d; cv.height = r.height * d; ctx.setTransform(d, 0, 0, d, 0, 0);
    const s = Math.max(3, Math.floor(Math.sqrt(r.width * r.height / N))); return {W:r.width, H:r.height, s, cols:Math.floor(r.width / s)}; };
  const draw = () => {
    ctx.clearRect(0, 0, g.W, g.H);
    for (let i = 0; i < N; i++){
      const x = (i % g.cols) * g.s, y = Math.floor(i / g.cols) * g.s; if (y > g.H) break;
      ctx.fillStyle = i < shown ? '#16a34a' : 'rgba(15,23,42,0.07)';
      rrect(ctx, x, y, g.s - 1.5, g.s - 1.5, Math.min(2, g.s / 3)); ctx.fill();
    }
  };
  g = geom(); draw(); new ResizeObserver(() => { g = geom(); draw(); }).observe(cv);
  onView(cv, () => { const t0 = performance.now(), dur = RM ? 1 : 4000;
    const f = now => { const k = Math.min(1, (now - t0) / dur); shown = Math.round(N * k); draw(); if (k < 1) requestAnimationFrame(f); };
    requestAnimationFrame(f); }, 0.5);
})();

/* ---------------------------------------------------------------- parity */
(function parity(){
  const el = $('#parity'); el.innerHTML = '<i></i>'.repeat(102);
  const s = $$('i', el);
  onView(el, () => s.forEach((x, i) => setTimeout(() => x.className = 'ok', RM ? 0 : i * 18)), 0.5);
})();

/* ---------------------------------------------------------------- copy buttons */
$$('.copy').forEach(b => b.addEventListener('click', async () => {
  const txt = $('pre', b.parentElement).innerText.split('\n').map(l => l.replace(/\s+#.*$/, '')).filter(l => l.trim() && !l.trim().startsWith('#')).join('\n');
  try { await navigator.clipboard.writeText(txt); b.textContent = 'copied'; } catch { b.textContent = 'select + copy'; }
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
    let i = 0; const t0 = performance.now(), cps = text.length / 3;
    const f = () => { if (token.dead) return res();
      i = Math.min(text.length, Math.max(i + 1, Math.round((performance.now() - t0) / 1000 * cps)));
      pre.innerHTML = hl(text.slice(0, i), gold) + (i < text.length ? '<span class="caret"></span>' : '');
      if (i < text.length) requestAnimationFrame(f); else res(); };
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

/* traversal scene: words -> runs -> files -> tests/docs, as cards */
function buildTraversal(net, P, words, gold=new Set()){
  net.clear();
  const sm = net.small, X = sm ? [.0, .25, .5, .75] : [.0, .245, .49, .735];
  net.heads = [[X[0], sm ? 'task' : 'the new task', COL.blue], [X[1], sm ? 'runs' : 'earlier runs', COL.teal], [X[2], sm ? 'files' : 'files they opened', COL.orange], [X[3], sm ? 'tests' : 'tests and docs', COL.green]];
  const ys = (n, top=.17, bot=.95) => Array.from({length:n}, (_, i) => n === 1 ? (top + bot) / 2 : top + (bot - top) * i / (n - 1));
  const nR = Math.min(P.runs || 5, sm ? 6 : 7);
  words.forEach((w, i) => net.node('w'+i, {kind:'term', label:w.toLowerCase(), short:w.toLowerCase(), x:X[0], y:ys(words.length, .25, .8)[i]}));
  const ry = ys(nR);
  for (let i = 0; i < nR; i++){
    const t = P.earlier[i];
    net.node('r'+i, {kind:'run', label: t || 'run ' + (i + 1), short: t || 'run ' + (i + 1), x:X[1], y:ry[i], ta:0});
    net.edge('w' + (i % words.length), 'r'+i, {ta:0, color:COL.blue});
    if (words.length > 1 && i % 2) net.edge('w' + ((i + 1) % words.length), 'r'+i, {ta:0, color:COL.blue});
  }
  const sy = ys(P.src.length);
  P.src.forEach((f, j) => {
    net.node('s'+j, {kind:'file', label:short2(f.path), short:base(f.path), x:X[2], y:sy[j], ta:0, isGold:gold.has(f.path)});
    for (let m = 0; m < Math.min(f.k, nR, 3); m++){
      const r = (j * 2 + m * 3) % nR, concl = m < f.concl;
      net.edge('r'+r, 's'+j, {ta:0, color: concl ? COL.orange : COL.teal, w: concl ? 1.8 : 1.2, hop:2});
    }
  });
  const td = [...P.test.map(f => ({...f, kind:'test'})), ...P.doc.map(f => ({...f, kind:'doc'}))];
  const ty = ys(td.length);
  td.forEach((f, j) => {
    net.node('t'+j, {kind:f.kind, label:short2(f.path), short:base(f.path), x:X[3], y:ty[j], ta:0, isGold:gold.has(f.path)});
    if (P.src.length) net.edge('s' + (j % P.src.length), 't'+j, {ta:0, color: f.kind === 'test' ? COL.green : COL.yellow, hop:3});
  });
  return {nR, nS:P.src.length, nT:td.length};
}
async function playTraversal(net, info, token, onHop=()=>{}){
  const alive = () => !token.dead;
  onHop(1);
  for (const n of net.nodes.values()) if (n.kind === 'term') n.tl = 1;
  await sleep(500); if (!alive()) return;
  const h1 = net.edges.filter(e => e.a[0] === 'w');
  h1.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h1.map((e, i) => sleep(i * 90).then(() => alive() && net.packet(e.a, e.b, COL.blue, 800))));
  if (!alive()) return;
  for (let i = 0; i < info.nR; i++){ const n = net.nodes.get('r'+i); if (n){ n.ta = 1; n.tl = 1; } }
  for (const n of net.nodes.values()) if (n.kind === 'term') n.tl = 0;
  h1.forEach(e => e.tl = 0);
  await sleep(700); if (!alive()) return;
  onHop(2);
  const h2 = net.edges.filter(e => e.hop === 2);
  h2.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h2.map((e, i) => sleep(i * 60).then(() => alive() && net.packet(e.a, e.b, e.color, 800))));
  if (!alive()) return;
  for (let j = 0; j < info.nS; j++){ const n = net.nodes.get('s'+j); n.ta = 1; n.tl = 1; }
  for (let i = 0; i < info.nR; i++){ const n = net.nodes.get('r'+i); if (n) n.tl = 0; }
  await sleep(700); if (!alive()) return;
  h2.forEach(e => e.tl = 0);
  onHop(3);
  const h3 = net.edges.filter(e => e.hop === 3);
  h3.forEach(e => { e.ta = 1; e.tl = 1; });
  await Promise.all(h3.map((e, i) => sleep(i * 90).then(() => alive() && net.packet(e.a, e.b, e.color, 750))));
  if (!alive()) return;
  for (let j = 0; j < info.nT; j++){ const n = net.nodes.get('t'+j); n.ta = 1; n.tl = 1; }
  await sleep(700); if (!alive()) return;
  h3.forEach(e => e.tl = 0);
  onHop(4);
  for (const n of net.nodes.values()){
    if (n.isGold){ n.gold = true; n.tl = 1; n.badge = '▲ real fix'; }
    else n.tl = 0;
  }
}

/* ---------------------------------------------------------------- hero: calm ring graph, one traversal at a time */
async function heroScene(){
  const net = new Net($('#hero-cv'), {mode:'ring'});
  const hud = $('#hero-hud');
  const X = [.05, .36, .65, .95], cnt = [6, 7, 7, 5], kinds = ['term', 'run', 'file', 'test'];
  const ids = cnt.map((n, c) => Array.from({length:n}, (_, i) => { const id = c + '_' + i;
    net.node(id, {kind:kinds[c], x:X[c] + (Math.random() - .5) * .05, y:.12 + .85 * (i + .5) / n + (Math.random() - .5) * .04}); return id; }));
  const ecol = [COL.blue, COL.teal, COL.orange];
  net.heads = [[X[0], 'words', COL.blue], [X[1], 'runs', COL.teal], [X[2], 'files', COL.orange], [X[3], 'tests', COL.green]];
  for (let c = 0; c < 3; c++) for (const a of ids[c]){
    for (const b of shuffle(ids[c+1]).slice(0, 2)) net.edge(a, b, {color:ecol[c], base:.22});
  }
  const say = (t, col) => { hud.textContent = t; hud.style.color = col || ''; };
  while (true){
    await net.visible();
    say("a new task's words", COL.blue);
    let front = shuffle(ids[0]).slice(0, 2);
    front.forEach(id => net.nodes.get(id).tl = 1);
    await sleep(700);
    const caps = ['earlier runs that worked near it', 'the files they opened', 'the tests they found'];
    for (let c = 0; c < 3; c++){
      say(caps[c], [COL.teal, COL.orange, COL.green][c]);
      const es = net.edges.filter(e => front.includes(e.a)).slice(0, 5);
      es.forEach(e => e.tl = 1);
      await Promise.all(es.map((e, i) => sleep(i * 120).then(() => net.packet(e.a, e.b, e.color, 900))));
      front = [...new Set(es.map(e => e.b))].slice(0, 3);
      front.forEach(id => net.nodes.get(id).tl = 1);
      await sleep(500);
    }
    say('pack ready: about 334 tokens for the next agent', COL.blue);
    await sleep(2200);
    for (const n of net.nodes.values()) n.tl = 0; for (const e of net.edges) e.tl = 0;
    say('');
    await sleep(1400);
  }
}

/* ---------------------------------------------------------------- write scene */
async function writeScene(){
  const net = new Net($('#write-cv'), {max:24, fs:11.5, smax:16});
  const log = $('#write-log');
  const L = [
    ['task', '$ agent run · "Make floatformat template filter independent of USE_L10N…"'],
    ['f0', '› sed -n 1,260p django/template/defaultfilters.py'],
    ['f1', '› sed -n 1,120p tests/template_tests/filter_tests/test_floatformat.py'],
    ['f2', '› sed -n 1670,1760p docs/ref/templates/builtins.txt'],
    ['ans', '✓ answer: the fix belongs in django/template/defaultfilters.py'],
    ['done', 'recorded: 1 run · 3 READ · 1 CONCLUDED · 0 model calls'],
  ];
  const files = [
    {id:'f0', kind:'file', label:'defaultfilters.py', lines:'1-260', y:.18},
    {id:'f1', kind:'test', label:'test_floatformat.py', lines:'1-120', y:.5},
    {id:'f2', kind:'doc', label:'builtins.txt', lines:'1670-1760', y:.82},
  ];
  const typeLine = async (txt, col) => {
    const d = document.createElement('div'); if (col) d.style.color = col; log.appendChild(d);
    if (RM){ d.textContent = txt; return; }
    for (let i = 0; i <= txt.length; i += 2){ d.textContent = txt.slice(0, i); await sleep(14); }
    d.textContent = txt;
  };
  while (true){
    await net.visible();
    net.clear(); log.innerHTML = '';
    for (const [k, txt] of L){
      await typeLine(txt, k === 'ans' ? COL.green : k === 'done' ? COL.teal : k === 'task' ? COL.text : COL.dim);
      if (k === 'task'){
        net.node('run', {kind:'run', label:'HRun', x:.36, y:.5});
        ['floatformat', 'USE_L10N', 'unlocalized'].forEach((t, i) => {
          net.node('t'+i, {kind:'term', label:t, x:0, y:.18 + i * .32});
          net.edge('t'+i, 'run', {color:COL.blue, lbl:'ABOUT', showLbl:i === 1, tl:1});
        });
        await Promise.all([0,1,2].map(i => net.packet('t'+i, 'run', COL.blue, 650)));
        net.edges.forEach(e => e.tl = 0);
      } else if (k[0] === 'f'){
        const f = files.find(x => x.id === k);
        net.node(f.id, {kind:f.kind, label:f.label, x:.62, y:f.y});
        const e = net.edge('run', f.id, {color:COL.teal, lbl:'READ {' + f.lines + '}', showLbl:true, tl:1});
        await net.packet('run', f.id, COL.teal, 650); e.tl = 0;
      } else if (k === 'ans'){
        const e = net.edges.find(x => x.b === 'f0'); e.color = COL.orange; e.w = 2; e.lbl = 'READ + CONCLUDED'; e.tl = 1;
        await net.packet('run', 'f0', COL.orange, 700);
        net.nodes.get('f0').tl = 1;
      }
      await sleep(350);
    }
    await sleep(4000);
  }
}

/* ---------------------------------------------------------------- read scene (15863) */
async function readScene(P15){
  const net = new Net($('#read-cv'), {fit:true, fs:11.5});
  const P = parsePack(P15.pack), gold = new Set([...P15.gold_src, ...P15.gold_tests]);
  const hops = $$('#read-hops span');
  while (true){
    await net.visible();
    const info = buildTraversal(net, P, ['floatformat', 'Decimal', 'precision'], gold);
    await playTraversal(net, info, {}, h => hops.forEach(s => s.classList.toggle('on', +s.dataset.h === h)));
    await sleep(5000);
    hops.forEach(s => s.classList.remove('on'));
  }
}

/* ---------------------------------------------------------------- try it */
function tryIt(PACKS){
  const list = $('#issues'), pre = $('#try-pack'), meta = $('#try-meta'), idEl = $('#try-id'), hud = $('#try-hud');
  const net = new Net($('#try-cv'), {fit:true, fs:11.5});
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
    idEl.textContent = p.id; pre.innerHTML = ''; meta.innerHTML = '<span>building the pack…</span>';
    const info = buildTraversal(net, P, wordsOf(p.title), gold);
    const hopTxt = ['', 'hop 1 of 3 · task → earlier runs', 'hop 2 of 3 · runs → files', 'hop 3 of 3 · files → tests and docs', 'pack ready'];
    await playTraversal(net, info, tk, h => { if (!tk.dead) hud.textContent = hopTxt[h]; });
    if (tk.dead) return;
    await typeInto(pre, p.pack, gold, tk);
    if (tk.dead) return;
    const srcIn = p.gold_src.filter(f => p.pack.includes(f)).length, testIn = p.gold_tests.some(f => p.pack.includes(f));
    meta.innerHTML = `<span>pack <b>${p.tokens}</b> tokens</span>
      <span>real fix files in pack <b class="${srcIn === p.gold_src.length ? 'y' : 'n'}">${srcIn}/${p.gold_src.length}</b></span>
      <span>real test file in pack <b class="${testIn ? 'y' : 'n'}">${testIn ? 'yes' : 'no'}</b></span>
      <span>live agent with this pack <b class="${p.agent_success ? 'y' : 'n'}">${p.agent_success ? 'solved' : 'not solved'}</b></span>`;
  }
  onView($('#try-cv'), () => run(0), 0.3);
}

/* ---------------------------------------------------------------- boot */
heroScene(); writeScene();
fetch('packs.json').then(r => r.json()).then(PACKS => {
  const P15 = PACKS.find(p => p.id === 'django__django-15863');
  const gold15 = new Set([...P15.gold_src, ...P15.gold_tests]);
  const pre = $('#pack-1586'); $('#pk-tok').textContent = P15.tokens + ' tokens';
  pre.innerHTML = hl(P15.pack, gold15);
  onView(pre, () => { pre.innerHTML = ''; typeInto(pre, P15.pack, gold15, {}); }, 0.3);
  readScene(P15); tryIt(PACKS);
}).catch(err => { console.warn('packs.json unavailable', err); });
