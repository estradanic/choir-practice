#!/usr/bin/env bash
# Usage: gitpush.sh <slug> "<message>" [--bump]
# Commits only public/pieces/<slug> (and site.json when bumping mediaVersion), serialized across jobs.
set -euo pipefail
cd "$(dirname "$0")/.."
slug=$1; msg=$2; bump=${3:-}
exec 9>/tmp/choir-git.lock; flock 9
git pull -q --rebase --autostash
paths=("public/pieces/$slug")
if [ "$bump" = --bump ]; then
  node -e 'const f="site.json",j=JSON.parse(require("fs").readFileSync(f));j.mediaVersion++;require("fs").writeFileSync(f,JSON.stringify(j,null,2)+"\n")'
  paths+=(site.json)
fi
git add -- "${paths[@]}"
git commit -qm "$msg" -- "${paths[@]}"
git push -q
git log --oneline -1
