import fs from 'node:fs';
const title = process.argv[2];
if (!title) { console.error('Usage: npm run new-piece "Title" [composer]'); process.exit(1); }
const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const dir = `public/pieces/${slug}`;
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(`${dir}/piece.json`, JSON.stringify({ title, composer: process.argv[3] || "", set: "", tags: [], videos: [] }, null, 2) + '\n');
console.log(`Created ${dir}\nAdd: score.pdf, full.mp3, soprano.mp3, alto.mp3, ... (optional soprano.pdf etc.)\nVideos: list tracks in piece.json, e.g. "videos": ["full", "alto"] (files live in the video bucket)`);
