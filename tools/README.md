# tools — puzzle pipeline

Curated-queue model: pre-build a batch of issues, publish one per day.

- `generate_midi.py` — backtracking filler for the symmetric 7x7 grid. Excludes
  plurals and (via a blocklist) proper nouns. `generate(seed)` returns a grid;
  CLI prints one. Needs a word list at `/tmp/common10k.txt`
  (google-10000-english-usa.txt).
- `select_grids.py` — generates many grids and greedily picks a low-overlap set
  (distinct 7-letter marquee answers, minimal short-fill repeats, no proper
  nouns). Prints chosen seeds + the union of answers to clue.
- `cluebank.py` — `CLUES`: one clue per answer word. Add entries when new grids
  introduce new words.
- `build_issues.py` — assembles the selected grids + clue bank into issues and
  writes `public/data/`: dated issue files, `index.json` (published manifest),
  and `queue.json` (upcoming issues). Re-run to regenerate the whole batch.
- `publish_daily.mjs` — run daily by `.github/workflows/daily.yml`: moves the
  next queued issue to today's date, updates `index.json`, commits. Idempotent.

## Refill the queue
Edit `SEEDS` in `build_issues.py` (use `select_grids.py` to find fresh
low-overlap seeds), add any missing clues to `cluebank.py`, then either re-run
`build_issues.py` (rebuilds everything) or append new puzzle objects to
`public/data/queue.json` by hand.
