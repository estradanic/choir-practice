// Media (audio, video, PDF) kept in IndexedDB so return visits skip the download. Entries carry
// the site's videoVersion; when it changes, everything stored under an older one is dropped.
const ver = String(window.__cpver ?? '');
let dbp;
const db = () => (dbp ||= new Promise((res) => {
  try {
    const r = indexedDB.open('cp-media', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('m');
    r.onsuccess = () => {
      const d = r.result;
      const st = d.transaction('m', 'readwrite').objectStore('m');
      st.openCursor().onsuccess = (e) => {
        const c = e.target.result;
        if (!c) return;
        if (c.value.ver !== ver) c.delete();
        c.continue();
      };
      res(d);
    };
    r.onerror = () => res(null);
  } catch { res(null); }
}));
const req = (r) => new Promise((res) => { r.onsuccess = () => res(r.result); r.onerror = () => res(null); });

export const getCached = async (url) => {
  const d = await db();
  if (!d) return null;
  const v = await req(d.transaction('m').objectStore('m').get(url));
  return v && v.ver === ver ? v.blob : null;
};

export const putCached = async (url, blob) => {
  const d = await db();
  if (!d) return;
  try { d.transaction('m', 'readwrite').objectStore('m').put({ ver, blob }, url); } catch {}
};

// Bytes of a file: from the store if it's there, otherwise downloaded and stored.
export const fetchBytes = async (url) => {
  const b = await getCached(url);
  if (b) return b.arrayBuffer();
  const r = await fetch(url);
  if (!r.ok) throw new Error(r.status);
  const blob = await r.blob();
  putCached(url, blob);
  return blob.arrayBuffer();
};

// Play stored videos from memory; store the rest in the background once the page is busy with nothing else.
export const cacheVideos = async () => {
  const vids = [...document.querySelectorAll('video[src]')];
  await Promise.all(vids.map(async (v) => {
    const url = v.getAttribute('src');
    const b = await getCached(url);
    if (b) v.src = URL.createObjectURL(b);
  }));
  setTimeout(async () => {
    for (const v of vids) {
      const url = v.dataset.orig || (v.src.startsWith('blob:') ? null : v.getAttribute('src'));
      if (!url || (await getCached(url))) continue;
      try {
        const r = await fetch(url);
        if (r.ok) await putCached(url, await r.blob());
      } catch {}
    }
  }, 8000);
};
