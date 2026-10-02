import fs from 'node:fs';
const [title, composer = '', set = ''] = process.argv.slice(2);
if (!title) { console.error('Usage: npm run new-piece "Title" [composer] [set]'); process.exit(1); }
const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
// Slug convention: title-composer-set, skipping any empty parts.
const slug = [slugify(title), slugify(composer), slugify(set)].filter(Boolean).join('-');
const dir = `public/pieces/${slug}`;
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(`${dir}/piece.json`, JSON.stringify({ title, composer, set, tags: [], videos: [] }, null, 2) + '\n');
console.log(`Created ${dir}\nAdd: score.pdf, full.mp3, soprano.mp3, alto.mp3, ...\nVideos: list tracks in piece.json, e.g. "videos": ["full", "alto"] (files live in the video bucket)`);
