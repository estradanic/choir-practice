# Choir Practice

Static Astro site. Add pieces with `/new-score`. Audio and PDFs live in `public/pieces/<slug>/`; videos live in a Cloudflare R2 bucket.

## One-time video hosting setup
1. Cloudflare dashboard → R2 → create a bucket; enable public access (r2.dev URL or a custom domain).
3. R2 → Manage API tokens → create a token with Object Read & Write. Copy values into `.env` (see `.env.example`).
4. Install `rclone`.

## Score import pipeline

Drop a `.mscz` into `scores/` and it is imported automatically.

- A systemd user service (`pipeline/choir-scores.service`) polls `scores/`, moves each file to `scores/in-progress/` and starts one `opencode run -m opencode/big-pickle --auto` session per file, running the `/new-score` skill in pipeline mode (`pipeline/PIPELINE.md`).
- The agent gets fuzzy "candidate" matches against existing pieces and decides. If it is clearly the same piece, its PDF, audio and videos are regenerated and `mediaVersion` in `site.json` is bumped. Otherwise the agent guesses the metadata and emails you one question (set, tags, unusual parts); reply to that email.
- Each job commits and pushes only its own piece folder (`pipeline/gitpush.sh`). Finished scores go to `scores/complete/`, failures to `scores/failed/`; logs are in `scores/logs/`. You get an email either way.
- Heavy steps (export, video render) share a lock, so several scores run one at a time.

Setup: add `MAIL_USER`, `MAIL_BRIDGE_PASSWORD` and `MAIL_TO` to `.env` (Proton Mail Bridge must be running, IMAP 1143 / SMTP 1025; `MAIL_TO` must be a real mailbox, not a SimpleLogin alias), then:

```
cp pipeline/choir-scores.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now choir-scores
```
