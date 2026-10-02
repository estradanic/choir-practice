import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('public/pieces');
const videoBase = JSON.parse(fs.readFileSync('site.json', 'utf8')).videoBase.replace(/\/$/, '');
const order = ['soprano', 'alto', 'tenor', 'baritone', 'bass'];
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export function getPieces() {
  if (!fs.existsSync(root)) return [];
  return fs
    .readdirSync(root, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => {
      const dir = path.join(root, d.name);
      const meta = JSON.parse(fs.readFileSync(path.join(dir, 'piece.json'), 'utf8'));
      const files = fs.readdirSync(dir);
      const videos = new Set(meta.videos || []);
      const has = (f) => files.includes(f);
      const names = new Set(
        files
          .filter((f) => /\.(mp3|pdf)$/.test(f))
          .map((f) => f.replace(/\.(mp3|pdf)$/, ''))
          .filter((n) => n !== 'full' && n !== 'score')
      );
      videos.forEach((n) => n !== 'full' && names.add(n));
      const vid = (n) => (videos.has(n) ? `${videoBase}/${d.name}/${n}.mp4` : null);
      const rank = (n) => (order.includes(n) ? order.indexOf(n) : 99);
      const parts = [...names]
        .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
        .map((n) => ({
          key: n,
          label: cap(n),
          audio: has(`${n}.mp3`) ? `${n}.mp3` : null,
          pdf: has('score.pdf') ? 'score.pdf' : null,
          video: vid(n),
        }));
      const full = {
        key: 'full',
        label: 'Full choir',
        audio: has('full.mp3') ? 'full.mp3' : null,
        pdf: has('score.pdf') ? 'score.pdf' : null,
        video: vid('full'),
      };
      return { slug: d.name, title: meta.title, composer: meta.composer || '', set: meta.set || '', setOrder: meta.setOrder ?? 0, tags: meta.tags || [], tracks: [full, ...parts] };
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}
