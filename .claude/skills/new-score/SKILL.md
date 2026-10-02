---
name: new-score
description: Add a new score to the choir practice site from a MuseScore .mscz file. Exports PDF + full/per-part MP3s via the MuseScore CLI, creates the piece folder, sets set/tags, builds and uploads videos. Use for /new-score.
---

# /new-score

Input: path to an `.mscz` file (ask if not given). Keep it token-cheap: run the commands, don't read the generated files.

## Steps

1. **Ask (one question call)**: title, composer, set name (optional, plus position in the set), tags (offer existing ones: `grep -h '"tags"' public/pieces/*/piece.json`).
2. **Create the piece**: `npm run new-piece "<Title>" "<Composer>"` → `public/pieces/<slug>/`.
3. **Export**: `python3 .claude/skills/new-score/export.py "<file.mscz>" public/pieces/<slug>`
   - Produces `score.pdf`, `full.mp3`, and one `<part>.mp3` per part (only that part audible). Takes ~30s per 4-part piece.
   - No part PDFs by design: everyone uses the same full score PDF.
   - Uses `mscore4portable` on PATH (override with `--mscore PATH`).
4. **Edit `piece.json`**: set `title`, `composer`, `set`, `setOrder`, `tags`. Pieces sharing an identical `set` string are grouped on the home page.
5. **Videos**: ask for the MuseScore-exported `.mp4` (video export is GUI-only; skip this step if none). Then:
   - `python3 .claude/skills/new-score/part_videos.py "<video.mp4>" public/pieces/<slug> video-out/<slug>` → `full.mp4` + `<part>.mp4` (auto-measures the ~2.98s intro offset; ~5s, video not re-encoded).
   - `.claude/skills/new-score/upload_videos.sh <slug>` → uploads to the Cloudflare R2 bucket (needs rclone + `.env`, see `.env.example`; if missing, tell the user to follow README setup).
   - In `piece.json` set `"videos": ["full", "soprano", ...]` (the tracks uploaded). URLs are derived as `<site.json videoBase>/<slug>/<track>.mp4`.
6. **Verify**: `npm run build`; confirm it passes.
7. **Offer to commit and push** (`git add public/pieces/<slug>`; message "Add <title>"). The GitHub Action deploys it.

## Notes
- File naming rules: `score.pdf`, `full.mp3`, `<part>.mp3`. Parts are auto-detected from filenames; any names (e.g. `baritone`) work.
- If an export errors, check that the AppImage runs: `mscore4portable --version`.
- Per-part audio: a temp copy of the score has `<play>0</play>` set on every note outside the target part, then it is exported. (Soloing via `audiosettings.json` was tried first but leaked the soprano into the first ~20s of every part.) The original .mscz is never modified.
