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
ANCHOR = date(2026, 9, 10)  # date of the newest seeded (published) issue
SEED_PUBLISHED = 5          # how many to pre-publish (rest go to the queue)
# No answer may repeat within a month. Issues publish one per day, so that is a
# sliding window of this many consecutive issues (published + queued in order).
NO_REPEAT_WINDOW = 30

DATA = os.path.join(os.path.dirname(__file__), "..", "public", "data")

def answers_of(p):
    return set(e["answer"] for e in p["across"] + p["down"])

def build_puzzle(grid, issue, forbid):
    # GRIDS records the seed that fills each layout given the earlier issues'
    # words, so one deterministic generate() reproduces it — no search needed.
    p = generate(grid["seed"], grid["pat"], budget=60000, forbid=forbid)
    if not p:
        raise SystemExit(f"issue {issue}: seed {grid['seed']} failed to fill "
                         f"with {len(forbid)} words forbidden")
    def clue_list(entries):
        out = []
        for e in entries:
            w = e["answer"]
            if w not in CLUES:
                raise SystemExit(f"missing clue for {w} (issue {issue})")
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
    # Build in publish order, forbidding every answer used in the previous
    # NO_REPEAT_WINDOW issues, so no word recurs inside a month.
    puzzles = []
    recent = []                       # word-sets, one per built issue, in order
    for i, g in enumerate(GRIDS):
        forbid = set().union(*recent[-NO_REPEAT_WINDOW:]) if recent else set()
        pz = build_puzzle(g, i + 1, forbid)
        puzzles.append(pz)
        recent.append(answers_of(pz["clues"]))
        print(f"  built issue {i+1}: {len(recent[-1])} answers, "
              f"{len(forbid)} forbidden", file=sys.stderr)

    # hard check: no answer repeats within the window
    for i in range(len(puzzles)):
        cur = recent[i]
        for j in range(max(0, i - NO_REPEAT_WINDOW + 1), i):
            clash = cur & recent[j]
            if clash:
                raise SystemExit(f"repeat within window: issues {j+1}&{i+1} share {clash}")

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
