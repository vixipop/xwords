# tools

`generate_midi.py` — backtracking crossword filler (seed of the daily
generator). Fills a symmetric 7x7 pattern from a common-word list so entries
are easy to clue. Usage:

    # needs a word list at /tmp/common10k.txt (google-10000-english-usa.txt)
    python3 tools/generate_midi.py <seed>

Prints solved grid + numbered entries as JSON. Clues are still written by hand;
wiring an automatic clue source is part of the puzzle-pipeline work.
