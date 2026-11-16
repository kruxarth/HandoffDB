/* HandoffDB page script: the pack browser (#pack) and the install copy buttons. */
(() => {
  const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const list = document.getElementById('pk-list');
  const packEl = document.getElementById('pk-pack');
  const idEl = document.getElementById('pk-id');
  const metaEl = document.getElementById('pk-meta');

  function render(p) {
    const gold = new Set([...(p.gold_src || []), ...(p.gold_tests || [])]);
    packEl.innerHTML = p.pack.split('\n').map(l => {
      if (/^(Source files|Test files|Docs|Earlier issues)/.test(l)) {
        const i = l.indexOf(':');
        return `<span class="s">${esc(l.slice(0, i + 1))}</span>${esc(l.slice(i + 1))}`;
      }
      const m = l.match(/^(\s+)(\S+)(.*)$/);
      if (m) return m[1] + `<span class="${gold.has(m[2]) ? 'hit' : 'p'}">${esc(m[2])}</span>` + `<span class="s">${esc(m[3])}</span>`;
      return `<span class="s">${esc(l)}</span>`;
    }).join('\n');
    idEl.textContent = p.id;
    metaEl.textContent = `${p.tokens} tokens · ${p.both ? 'fix files and test in pack' : 'fix not fully in pack'}`;
  }

  function select(btn, packs) {
    for (const b of list.children) b.setAttribute('aria-selected', String(b === btn));
    render(packs[+btn.dataset.i]);
  }

  if (list) fetch('packs.json').then(r => r.json()).then(packs => {
    list.innerHTML = packs.map((p, i) => `<button class="pk-row" type="button" role="option" aria-selected="${i === 0}" data-i="${i}">
      <span class="pk-row__t">${esc(p.title)}</span><span class="pk-row__id">${esc(p.id.replace('django__', ''))}</span>
      <span class="pk-row__chip${p.both ? '' : ' pk-row__chip--miss'}">${p.both ? 'Fix in pack' : 'Partial'}</span></button>`).join('');
    list.addEventListener('click', e => { const b = e.target.closest('.pk-row'); if (b) select(b, packs); });
    list.addEventListener('keydown', e => {
      if (!['ArrowDown', 'ArrowUp'].includes(e.key)) return;
      const rows = [...list.children], i = rows.indexOf(document.activeElement);
      const n = rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
      if (n) { e.preventDefault(); n.focus(); select(n, packs); }
    });
    render(packs[0]);
  }).catch(() => { packEl.textContent = 'The packs could not be loaded.'; });

  document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', async () => {
    const t = document.getElementById(b.dataset.copy).textContent;
    try { await navigator.clipboard.writeText(t); b.textContent = 'Copied'; } catch { b.textContent = 'Select and copy'; }
    setTimeout(() => { b.textContent = 'Copy'; }, 1600);
  }));
})();
