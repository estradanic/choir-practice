import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.min.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

async function init(root) {
  const scroller = root.querySelector('.pages');
  const label = root.querySelector('.pg');
  const bar = root.querySelector('.bar');
  const doc = await pdfjs.getDocument({ url: root.dataset.src }).promise;
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

  const scaleFor = (p) => {
    const h = scroller.clientHeight - 16;
    const w = scroller.clientWidth - 16;
    return Math.min(h / p.vp.height, w / p.vp.width) * ZOOMS[zi];
  };

  const size = () => {
    pages.forEach((p) => {
      const s = scaleFor(p);
      p.wrap.style.width = `${p.vp.width * s}px`;
      p.wrap.style.height = `${p.vp.height * s}px`;
    });
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
    if (p.key === key) p.wrap.replaceChildren(c);
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
