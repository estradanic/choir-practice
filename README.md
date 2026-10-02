# Choir Practice

Static Astro site. Add pieces with `/new-score`. Audio and PDFs live in `public/pieces/<slug>/`; videos live in a Cloudflare R2 bucket.

## One-time video hosting setup
1. Cloudflare dashboard → R2 → create a bucket; enable public access (r2.dev URL or a custom domain).
3. R2 → Manage API tokens → create a token with Object Read & Write. Copy values into `.env` (see `.env.example`).
4. Install `rclone`.
