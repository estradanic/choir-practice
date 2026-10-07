#!/usr/bin/env bash
# Usage: job.sh <file.mscz in scores/in-progress>. Runs one opencode session; moves file to complete/ or failed/.
cd "$(dirname "$0")/.."
f=$1; name=$(basename "$f" .mscz)
mkdir -p scores/complete scores/failed scores/logs
log=scores/logs/$name.log
prompt="Pipeline job, unattended. Run the /new-score skill in PIPELINE MODE on $PWD/$f (read pipeline/PIPELINE.md first). Piece id for messages: $name. ${JOB_NOTE:-}"
if timeout 2d opencode run -m opencode/big-pickle --auto "$prompt" >"$log" 2>&1; then
  mv "$f" scores/complete/; python3 pipeline/ask.py "$name" "Done: $name was imported and pushed." --notify
else
  mv "$f" scores/failed/; python3 pipeline/ask.py "$name" "FAILED: $name. See scores/logs/$name.log" --notify
fi
