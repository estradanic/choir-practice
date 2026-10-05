import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

// The scrollbar track is a tile of one grey dot per 2x2 block, built in whole device pixels so it
// stays crisp and evenly spaced whatever the display scaling or browser zoom is.
const dots = () => {
  const dpr = window.devicePixelRatio || 1;
  const d = Math.max(1, Math.round(dpr));
  const c = document.createElement('canvas');
  c.width = c.height = d * 2;
  const g = c.getContext('2d');
  g.fillStyle = '#fff';
  g.fillRect(0, 0, d * 2, d * 2);
  g.fillStyle = '#a9b8d6';
  g.fillRect(0, 0, d, d);
  const st = document.documentElement.style;
  st.setProperty('--wsb-bg', `url(${c.toDataURL()})`);
  st.setProperty('--wsb-sz', `${(d * 2) / dpr}px`);
};
dots();
addEventListener('resize', dots);

let lib;
const load = () => (lib ||= import('pdfjs-dist/legacy/build/pdf.min.mjs').then((m) => { m.GlobalWorkerOptions.workerSrc = workerUrl; return m; }));

const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

// An old-school scrollbar (arrow buttons, dithered track, raised thumb) for a scrolling box, in
// place of the browser's. The horizontal one sits under the box; the vertical one floats over its
// right edge and only appears when the content is taller than the box.
function winScroll(scroller, axis) {
  const v = axis === 'y';
  const el = document.createElement('div');
  el.className = `wsb ${v ? 'wsb-v' : 'wsb-h'}`;
  el.hidden = true;
  el.innerHTML = '<button type="button" class="wsb-a wsb-1" tabindex="-1" aria-label="Scroll back"></button><div class="wsb-t"><div class="wsb-th"></div></div><button type="button" class="wsb-a wsb-2" tabindex="-1" aria-label="Scroll forward"></button>';
  if (v) scroller.parentElement.append(el);
  else {
    // The page reserves this space up front (see .wsb-ph) so nothing shifts when the bar appears.
    const ph = scroller.parentElement.nextElementSibling;
    if (ph?.classList.contains('wsb-ph')) ph.replaceWith(el);
    else scroller.parentElement.after(el);
  }
  const [b1, track, b2] = el.children;
  const thumb = track.firstElementChild;
  const pos = v ? 'scrollTop' : 'scrollLeft';
  const total = () => (v ? scroller.scrollHeight : scroller.scrollWidth);
  const vis = () => (v ? scroller.clientHeight : scroller.clientWidth);
  const room = () => (v ? track.clientHeight : track.clientWidth);
  const len = () => Math.max(16, (room() * vis()) / total());
  const sync = () => {
    const over = total() > vis() + 1;
    el.hidden = !over;
    if (!over) return;
    const l = len();
    thumb.style[v ? 'height' : 'width'] = `${l}px`;
    thumb.style[v ? 'top' : 'left'] = `${(room() - l) * (scroller[pos] / (total() - vis()))}px`;
  };
  scroller.addEventListener('scroll', sync);
  new ResizeObserver(sync).observe(scroller);
  new MutationObserver(sync).observe(scroller, { childList: true, subtree: true, attributes: true, attributeFilter: ['style'] });
  const hold = (btn, dir) => btn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    const step = () => scroller.scrollBy({ [v ? 'top' : 'left']: dir * 48 });
    step();
    let t = setTimeout(() => { t = setInterval(step, 50); }, 350);
    const stop = () => { clearTimeout(t); clearInterval(t); removeEventListener('pointerup', stop); removeEventListener('pointercancel', stop); };
    addEventListener('pointerup', stop);
    addEventListener('pointercancel', stop);
  });
  hold(b1, -1);
  hold(b2, 1);
  track.addEventListener('pointerdown', (e) => {
    if (e.target !== track) return;
    const r = thumb.getBoundingClientRect();
    const before = v ? e.clientY < r.top : e.clientX < r.left;
    scroller.scrollBy({ [v ? 'top' : 'left']: (before ? -1 : 1) * vis() * 0.9, behavior: 'smooth' });
  });
  thumb.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    thumb.setPointerCapture(e.pointerId);
    const start = v ? e.clientY : e.clientX;
    const from = scroller[pos];
    const snap = scroller.style.scrollSnapType;
    scroller.style.scrollSnapType = 'none';
    const move = (m) => { scroller[pos] = from + (((v ? m.clientY : m.clientX) - start) * (total() - vis())) / Math.max(1, room() - len()); };
    const up = () => { thumb.removeEventListener('pointermove', move); thumb.removeEventListener('pointerup', up); scroller.style.scrollSnapType = snap; };
    thumb.addEventListener('pointermove', move);
    thumb.addEventListener('pointerup', up);
  });
  sync();
}

async function init(root) {
  const scroller = root.querySelector('.pages');
  const label = root.querySelector('.pg');
  const bar = root.querySelector('.bar');
  const ld = root.querySelector('.loading');
  const lt = ld.querySelector('.lt');
  const fill = ld.querySelector('i');
  const setPct = (p) => {
    p = Math.max(0, Math.min(100, Math.round(p)));
    lt.textContent = `Loading score… ${p}%`;
    ld.setAttribute('aria-valuenow', p);
    const room = fill.parentElement.clientWidth - 4;
    fill.style.width = `${Math.floor((room * p) / 100 / 12) * 12}px`;
  };
  setPct(0);
  const pdfjs = await load();
  setPct(20);
  const task = pdfjs.getDocument({ url: root.dataset.src });
  task.onProgress = ({ loaded, total }) => { if (total) setPct(20 + (loaded / total) * 70); };
  const doc = await task.promise;
  setPct(95);
  let zi = 2;
  let cur = 0;
  const pages = [];

  for (let n = 1; n <= doc.numPages; n++) {
    const page = await doc.getPage(n);
    const wrap = document.createElement('div');
    wrap.className = 'pdfpage';
    scroller.append(wrap);
    pages.push({ page, wrap, vp: page.getViewport({ scale: 1 }), key: '' });
  }

  const first = pages[0].vp;
  if (!window.__paSet) {
    window.__paSet = true;
    document.documentElement.style.setProperty('--pa', first.width / first.height);
    dispatchEvent(new Event('refit'));
  }

  // On phones the box shrinks to the pages instead of leaving grey space around them, and keeps that height when zooming; desktop and
  // fullscreen keep the height the layout gives them.
  const fixedH = () => !document.documentElement.classList.contains('desk') && !document.fullscreenElement;

  const scaleFor = (p) => {
    const h = (fixedH() ? innerHeight * 0.75 : scroller.clientHeight) - 16;
    const w = scroller.clientWidth - 16;
    return Math.min(h / p.vp.height, w / p.vp.width) * ZOOMS[zi];
  };

  const size = () => {
    pages.forEach((p) => {
      const s = scaleFor(p);
      p.wrap.style.width = `${p.vp.width * s}px`;
      p.wrap.style.height = `${p.vp.height * s}px`;
    });
    scroller.style.height = fixedH()
      ? `${Math.min(innerHeight * 0.75, Math.max(...pages.map((p) => p.vp.height * (scaleFor(p) / ZOOMS[zi]))))}px`
      : '';
  };

  const draw = async (p) => {
    const s = scaleFor(p);
    const key = `${s.toFixed(3)}@${devicePixelRatio}`;
    if (p.key === key) return;
    p.key = key;
    const vp = p.page.getViewport({ scale: s * devicePixelRatio });
    const c = document.createElement('canvas');
    c.width = Math.floor(vp.width);
    c.height = Math.floor(vp.height);
    await p.page.render({ canvasContext: c.getContext('2d'), viewport: vp, canvas: c }).promise;
    if (p.key === key) { p.wrap.replaceChildren(c); ld.classList.add('done'); }
  };

  const left = (i) => pages[i].wrap.offsetLeft - 8;
  let lock = 0;
  const prev = bar.querySelector('[data-act=prev]');
  const next = bar.querySelector('[data-act=next]');
  const zout = bar.querySelector('[data-act=out]');
  const zin = bar.querySelector('[data-act=in]');
  const mark = () => {
    prev.disabled = cur <= 0;
    next.disabled = cur >= pages.length - 1;
    zout.disabled = zi <= 0;
    zin.disabled = zi >= ZOOMS.length - 1;
  };

  const update = () => {
    const r = scroller.getBoundingClientRect();
    pages.forEach((p) => {
      const b = p.wrap.getBoundingClientRect();
      if (b.right > r.left - r.width && b.left < r.right + r.width) draw(p);
    });
    if (Date.now() > lock) {
      const sl = scroller.scrollLeft;
      const atEnd = sl >= scroller.scrollWidth - scroller.clientWidth - 2;
      let best = pages.length - 1;
      if (!atEnd) {
        let bestD = Infinity;
        pages.forEach((_, i) => {
          const d = Math.abs(left(i) - sl);
          if (d < bestD) { bestD = d; best = i; }
        });
      }
      cur = best;
    }
    label.textContent = `Page ${cur + 1} / ${pages.length}`;
    mark();
  };

  const go = (i) => {
    cur = Math.max(0, Math.min(pages.length - 1, i));
    lock = Date.now() + 600;
    scroller.scrollTo({ left: left(cur), behavior: 'smooth' });
    label.textContent = `Page ${cur + 1} / ${pages.length}`;
    mark();
    setTimeout(update, 650);
  };

  const zoom = (d) => {
    const n = d === 0 ? 2 : Math.max(0, Math.min(ZOOMS.length - 1, zi + d));
    if (n === zi) return;
    const keep = cur;
    zi = n;
    size();
    pages.forEach((p) => { p.key = ''; });
    scroller.scrollLeft = left(keep);
    update();
  };

  let raf = 0;
  scroller.addEventListener('scroll', () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(update);
  });
  scroller.addEventListener('wheel', (e) => {
    if (zi === 2 && Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      e.preventDefault();
      scroller.scrollLeft += e.deltaY;
    }
  }, { passive: false });
  scroller.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' && zi === 2) { e.preventDefault(); go(cur + 1); }
    if (e.key === 'ArrowLeft' && zi === 2) { e.preventDefault(); go(cur - 1); }
  });
  bar.addEventListener('click', (e) => {
    const a = e.target.closest('[data-act]')?.dataset.act;
    if (a === 'prev') go(cur - 1);
    if (a === 'next') go(cur + 1);
    if (a === 'out') zoom(-1);
    if (a === 'in') zoom(1);
    if (a === 'fit') zoom(0);
    if (a === 'fs') {
      if (document.fullscreenElement) document.exitFullscreen();
      else root.requestFullscreen?.().catch(() => {});
    }
  });
  winScroll(scroller, 'x');
  winScroll(scroller, 'y');
  new ResizeObserver(() => { if (!scroller.clientHeight) return; size(); pages.forEach((p) => { p.key = ''; }); update(); }).observe(scroller);
  size();
  update();
}

// Start loading each PDF once its panel is first shown.
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    io.unobserve(e.target);
    init(e.target).catch((err) => { console.error(err); e.target.classList.add("failed"); });
  });
});
document.querySelectorAll('.pdfview').forEach((el) => io.observe(el));
