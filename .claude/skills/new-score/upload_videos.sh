#!/usr/bin/env bash
# Usage: upload_videos.sh <slug>   (uploads video-out/<slug>/*.mp4 to the R2 bucket)
# Needs rclone and a .env with R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET.
set -euo pipefail
slug="$1"
set -a; source .env; set +a
export RCLONE_CONFIG_R2_TYPE=s3 RCLONE_CONFIG_R2_PROVIDER=Cloudflare \
  RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
  RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
for f in "video-out/$slug"/*.mp4; do
  name=$(basename "$f")
  rclone copyto --ignore-times "$f" "R2:${R2_BUCKET}/$slug/$name" --header-upload "Content-Type: video/mp4" \
    --header-upload "Cache-Control: public, max-age=31536000" \
    --header-upload "Content-Disposition: attachment; filename=\"${slug}-${name}\""
done
