# Pipeline mode for /new-score

Unattended: the user is not at the keyboard. Never use the question tool. Never wait for input.

- Guess first: `python3 pipeline/inspect.py "<file>"` prints title, composer, part names and `existing` (slug of a piece with the same title, composer and part count, or null).
- **existing != null** -> follow "Regenerating an existing piece". No questions, keep piece.json metadata, bump mediaVersion.
- **existing == null** -> new piece. Ask ONCE by email with `python3 pipeline/ask.py "<job id>" "<question>"`; it blocks until the user replies and prints the reply. Include your guesses (title, composer) and ask for: set name + position (or none), tags (list existing ones, say "none" is fine), and non-standard parts. The reply is final; don't re-ask. If the reply is unclear, ask one short follow-up.
- Run heavy steps (export.py, slow_audio.py, render_video.py) under `flock /tmp/choir-heavy.lock <command>`. Use long timeouts.
- Commit with `pipeline/gitpush.sh <slug> "Add <title>"` (new) or `pipeline/gitpush.sh <slug> "Update media for <title>" --bump` (update). Never use plain git add/commit/push; other work is in progress in the tree.
- Don't move the score file; the pipeline does that. Exit non-zero (fail loudly) if anything fails.
