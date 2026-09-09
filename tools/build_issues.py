#!/usr/bin/env python3
"""Assemble curated issues from the selected grids + clue bank.

Writes:
  public/data/<date>.json   one file per published issue
  public/data/index.json    manifest of published issues (newest first)
  public/data/queue.json    remaining pre-built issues, published one/day by cron
"""
import json, os, sys
from datetime import date, timedelta
from generate_midi import generate
from cluebank import CLUES
from grids import GRIDS          # each: {"pat": [...7 rows...], "seed": int}

TITLE = "The Daily 7"
AUTHOR = "The Gazette"
ANCHOR = date(2026, 9, 9)   # date of the newest seeded (published) issue
SEED_PUBLISHED = 4          # how many to pre-publish (rest go to the queue)

DATA = os.path.join(os.path.dirname(__file__), "..", "public", "data")

def build_puzzle(grid, issue):
    p = generate(grid["seed"], grid["pat"])
    if not p:
        raise SystemExit(f"grid {issue} (seed {grid['seed']}) failed to fill")
    def clue_list(entries):
        out = []
        for e in entries:
            w = e["answer"]
            if w not in CLUES:
                raise SystemExit(f"missing clue for {w} (seed {seed})")
            out.append({"num": e["num"], "clue": CLUES[w], "answer": w})
        return out
    return {
        "issue": issue,
        "title": TITLE,
        "author": AUTHOR,
        "size": p["size"],
        "grid": p["grid"],
        "clues": {"across": clue_list(p["across"]), "down": clue_list(p["down"])},
    }

def main():
    os.makedirs(DATA, exist_ok=True)
    puzzles = [build_puzzle(g, i + 1) for i, g in enumerate(GRIDS)]

    # sanity: no repeated clue text within the whole set
    seen = {}
    for pz in puzzles:
        for e in pz["clues"]["across"] + pz["clues"]["down"]:
            seen.setdefault(e["clue"], set()).add(e["answer"])
    dupe_clues = {c: ws for c, ws in seen.items() if len(ws) > 1}
    if dupe_clues:
        print("WARNING: clue text reused for different answers:", dupe_clues, file=sys.stderr)

    # publish the first SEED_PUBLISHED issues on consecutive dates ending at ANCHOR
    index = []
    for offset, pz in enumerate(puzzles[:SEED_PUBLISHED]):
        d = ANCHOR - timedelta(days=(SEED_PUBLISHED - 1 - offset))
        ds = d.isoformat()
        issue = dict(pz, id=ds, date=ds)
        with open(os.path.join(DATA, f"{ds}.json"), "w") as f:
            json.dump(issue, f, indent=1)
        index.append({"date": ds, "issue": pz["issue"], "id": ds,
                      "title": pz["title"], "size": pz["size"]})
    index.sort(key=lambda x: x["date"], reverse=True)
    with open(os.path.join(DATA, "index.json"), "w") as f:
        json.dump(index, f, indent=1)

    # the rest wait in the queue (no date yet); cron assigns dates one per day
    queue = puzzles[SEED_PUBLISHED:]
    with open(os.path.join(DATA, "queue.json"), "w") as f:
        json.dump(queue, f, indent=1)

    print(f"published {len(index)} issues, {len(queue)} queued")
    print("published dates:", [e["date"] for e in index])

if __name__ == "__main__":
    main()
