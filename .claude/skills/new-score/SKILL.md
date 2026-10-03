---
name: new-score
description: Add a new score to the choir practice site from a MuseScore .mscz file. Exports PDF + full/per-part MP3s via the MuseScore CLI, creates the piece folder, sets set/tags, builds and uploads videos. Use for /new-score.
user-invocable: true
---

# /new-score

Input: path to an `.mscz` file (ask if not given). Keep it token-cheap: run the commands, don't read the generated files.

## Steps

1. **Ask (one question call)**: title, composer, set name (optional, plus position in the set), tags, and **anything non-standard about the parts** — anything that is not standard SATB.
   - **Always ask about tags, every time — never skip it.** Do not infer them from the title, composer or set, and do not copy them from a sibling piece in the same set (a Gloria is a Mass, but confirm rather than assume). Offer the existing tags to pick from:
     `python3 -c "import json,glob;print(sorted({t for f in glob.glob('public/pieces/*/piece.json') for t in json.load(open(f)).get('tags',[])}))"`
     (A plain `grep -h '"tags"'` only matches the opening `"tags": [` line and never shows the values — that's why the tags list must be read properly.) Reuse an existing tag when it fits; confirm any new tag name instead of inventing one.
   - Offer options like Descant, extra Soprano/Alto splits, Baritone, Bass II, doubling, a piano/organ part, or "standard SATB, nothing unusual".
   - Compare with the score: `export.py` prints the parts it found. A part the user mentions but the export doesn't produce means the score is set up unusually — see Notes.
   - Never rely on this alone: check the produced `<part>.mp3` names against what the user said and ask if they disagree.
2. **Create the piece**: `npm run new-piece "<Title>" "<Composer>" "<Set>"` → `public/pieces/<slug>/`. Slug is always `title-composer-set` (empty parts omitted).
3. **Export**: `python3 .claude/skills/new-score/export.py "<file.mscz>" public/pieces/<slug>`
   - Produces `score.pdf`, `full.mp3`, and one `<part>.mp3` per part (only that part audible). Takes ~30s per part.
   - No part PDFs by design: everyone uses the same full score PDF.
   - Uses `mscore4portable` on PATH (override with `--mscore PATH`).
   - Also writes `"parts": [...]` into `piece.json`: the parts in score staff order. Don't hand-edit it; re-run the export instead. The site lists tracks in that order, so no other file records voice order.
   - Then `python3 .claude/skills/new-score/slow_audio.py public/pieces/<slug>` → pre-rendered 0.75× and 0.875× copies (pitch preserved, ffmpeg `rubberband`) in `speeds/<speed>/`. The site's speed buttons swap to these (browser time-stretching sounds bad); ~2.5× the MP3 size, a minute or so. Re-run with `--force` if MP3s are re-exported.
4. **Edit `piece.json`**: set `title`, `composer`, `set`, `setOrder`, `tags`. Pieces sharing an identical `set` string are grouped on the home page.
5. **Videos**: ask for the MuseScore-exported `.mp4` (video export is GUI-only; skip this step if none). Then:
   - `python3 .claude/skills/new-score/part_videos.py "<video.mp4>" public/pieces/<slug> video-out/<slug>` → `full.mp4` + `<part>.mp4` (auto-measures the ~2.98s title-screen intro and cuts it; re-encodes, ~1 min).
   - `.claude/skills/new-score/upload_videos.sh <slug>` → uploads to the Cloudflare R2 bucket (needs rclone + `.env`, see `.env.example`; if missing, tell the user to follow README setup). The script passes `--s3-no-check-bucket`; without it every upload dies with `CreateBucket … 403 AccessDenied`, because R2 forbids bucket creation to a token scoped to that bucket.
   - In `piece.json` set `"videos": ["full", "soprano", ...]` (the tracks uploaded). URLs are derived as `<site.json videoBase>/<slug>/<track>.mp4`. Only list tracks that actually uploaded, otherwise the tabs 404.
   - Uploaded videos are cached by browsers for a year. If you **re-upload** videos for an existing piece, bump `videoVersion` in `site.json` so everyone's browser fetches the new files.
6. **Verify**: `npm run build`; confirm it passes.
7. **Offer to commit and push** (`git add public/pieces/<slug>`; message "Add <title>"). Include any supporting changes made along the way (e.g. `.gitignore`, `scripts/new-piece.mjs`, `src/lib/pieces.js`, this skill). The GitHub Action deploys it.

## Notes
- File naming rules: `score.pdf`, `full.mp3`, `<part>.mp3`. Parts are auto-detected from filenames; any names (e.g. `baritone`) work.
- Voice order on the page is the score's staff order, read from `parts` in `piece.json` (written by `export.py`). `src/lib/pieces.js` only falls back to `soprano, alto, tenor, baritone, bass` for pieces exported before that existed, so don't add non-standard voices to that list.
- Watch for parts whose `trackName` is duplicated or stale, e.g. a Descant copied from the Soprano and only the *instrument* renamed, leaving both parts called "Soprano". `export.py` disambiguates by preferring the instrument's `longName` when it is unique (so it exports `descant.mp3`), falling back to a numeric suffix (`soprano2`). If a part still looks wrong, inspect `trackName` vs `longName` per `Part` in the `.mscx`.
- If an export errors, check that the AppImage runs: `mscore4portable --version`.
- Per-part audio: a temp copy of the score has `<play>0</play>` set on every note outside the target part, then it is exported. (Soloing via `audiosettings.json` was tried first but leaked the soprano into the first ~20s of every part.) The original .mscz is never modified.
