# The Daily Cross

A free, ad-free daily crossword with a newspaper aesthetic. Because the
crossword shouldn't be behind a paywall.

## Status: prototype

A working front-end shell is in place:

- **Newspaper masthead + layout** — off-white newsprint, hairline rules, a
  blackletter nameplate, clues in columns.
- **Interactive grid** — click / arrow-key navigation, active-word highlight,
  clue ↔ grid sync, Check / Reveal / Clear.
- **Data-driven** — puzzles are plain JSON (`data/*.json`); the app just renders.
- A hand-verified **sample mini** ships in `data/sample.json`.

## Typography (the "fonts fit to print")

The NYT print system, and the free stand-ins used here until we license or
self-host alternatives:

| Role            | NYT print font | Free stand-in (current) |
| --------------- | -------------- | ----------------------- |
| Masthead        | (custom black-letter nameplate) | UnifrakturCook |
| Headlines       | NYT Cheltenham | Playfair Display |
| Body            | NYT Imperial (print) / Georgia (digital) | Georgia |
| Captions / fine print | NYT Franklin | Libre Franklin |
| Solver's pencil (cell input) | — | Caveat (handwritten) |

## Run it

```
python3 -m http.server 8099
# open http://localhost:8099
```

Pure static HTML/CSS/JS — no build step, deploys anywhere (GitHub Pages, Netlify, etc.).

## Roadmap

- [ ] Daily puzzle **generator** (grid layout + backtracking fill over a
      word+clue database) → writes `data/<YYYY-MM-DD>.json`.
- [ ] Load today's puzzle by date; archive of past days.
- [ ] Solve-state persistence (localStorage) + completion timer.
- [ ] Self-host fonts (`assets/fonts/`) so it works offline / without Google Fonts.
- [ ] Paper texture + print stylesheet ("print your crossword").
