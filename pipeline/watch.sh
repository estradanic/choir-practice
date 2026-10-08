#!/usr/bin/env bash
# Polls scores/ for new .mscz files (also handles leftovers from before a shutdown), one background job each.
cd "$(dirname "$0")/.."
mkdir -p scores/in-progress scores/logs
size() { stat -c %s "$1"; }
start() { # $1 = path already in in-progress
  nohup pipeline/job.sh "$1" >/dev/null 2>&1 &
}
# Resume jobs interrupted by a shutdown.
for f in scores/in-progress/*.mscz; do [ -e "$f" ] && start "$f"; done
n=0
while sleep 5; do
  n=$((n+1)); [ $((n % 6)) = 1 ] && timeout 60 python3 pipeline/mailwatch.py 2>>scores/logs/mailwatch.log
  for f in scores/*.mscz; do
    [ -e "$f" ] || continue
    s1=$(size "$f"); sleep 3; [ -e "$f" ] && [ "$s1" = "$(size "$f")" ] || continue
    mv "$f" scores/in-progress/ && start "scores/in-progress/$(basename "$f")"
  done
done
