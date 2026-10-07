# Pipeline mode for /new-score

Unattended: the user is not at the keyboard. Never use the question tool. Never wait for input.

- Guess first: `python3 pipeline/inspect.py "<file>"` prints title, composer, part names and fuzzy `candidates` (existing pieces that look similar, with similarity scores and whether the part count matches). It does not decide anything; you do.
- **Update** (a candidate is clearly the same piece: near-identical title and composer, same part count, or the piece was clearly just re-edited) -> follow "Regenerating an existing piece": keep piece.json metadata, bump mediaVersion via gitpush. No questions needed if the title and composer are the same apart from case, accents or punctuation.
- **Update with changes**: if it is the same piece but the score's title, composer or part list differs meaningfully from the existing record (e.g. a corrected title, a renamed or added part), ask ONCE by email whether to update the existing piece and whether to change the metadata (show old vs new). Don't change metadata without that answer.
- **Unsure** between update and new (e.g. same title but different composer, or different part count): ask ONCE by email, naming the candidate slug.
- **New piece** (no plausible candidate) -> ask ONCE by email with `python3 pipeline/ask.py "<job id>" "<question>"`; it blocks until the user replies and prints the reply. Include your guesses (title, composer) and ask for: set name + position (or none), tags (list existing ones, "none" is fine), and non-standard parts. The reply is final; don't re-ask. If the reply is unclear, ask one short follow-up.
- Run heavy steps (export.py, slow_audio.py, render_video.py) under `flock /tmp/choir-heavy.lock <command>`. Use long timeouts.
- Commit with `pipeline/gitpush.sh <slug> "Add <title>"` (new) or `pipeline/gitpush.sh <slug> "Update media for <title>" --bump` (update). Never use plain git add/commit/push; other work is in progress in the tree.
- Don't move the score file; the pipeline does that. Exit non-zero (fail loudly) if anything fails.
- NEVER edit `site.json` yourself (ignore the manual mediaVersion bump in the skill): `gitpush.sh --bump` does it, under the lock, so parallel jobs don't clash.
