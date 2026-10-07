import site from '../../site.json';

// Bump mediaVersion in site.json after re-uploading media (videos, MP3s, PDF).
export const mediaVersion = site.mediaVersion;

// Append ?v=<mediaVersion> to an MP3/PDF URL so a bump busts browsers' year-long cache.
// Idempotent, and always applied to the whole URL: the string that gets fetched is the same
// one mediacache.js uses as its IndexedDB key, which it stamps with window.__cpver, so the
// key and the stored version can't drift apart.
export const withVer = (url) => {
  if (!url || !mediaVersion || /[?&]v=/.test(url)) return url;
  return `${url}${url.includes('?') ? '&' : '?'}v=${mediaVersion}`;
};
