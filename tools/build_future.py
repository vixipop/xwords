#!/usr/bin/env python3
"""Regenerate the UPCOMING issues with clean grids (few 3-letter words) and the
crosswordese-demoting word ranker, while FREEZING everything already public.

Issues dated on/before FREEZE_THROUGH are kept exactly as they are (someone may
be mid-solve). Everything after is rebuilt from a rotating bank of clean grids,
forbidding every answer used in the trailing NO_REPEAT_WINDOW issues so no word
recurs within a month.

Run with `--dry` to just report which answers still need clues.
"""
import json, os, sys
from datetime import date, timedelta
from generate_midi import generate
from cluebank import CLUES

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "public", "data")

FREEZE_THROUGH = date(2026, 9, 10)   # issues on/before this are untouchable
FUTURE_COUNT = 7                     # how many upcoming issues to (re)build
NO_REPEAT_WINDOW = 30
AUTHOR = "The Gazette"

def title_for(d):
    return f"The {d.strftime('%A')} Crossword"

# Clean rotating grid bank: every layout here has <=6 three-letter words
# (versus 13-18 in the grids we're replacing). A shape recurs only every few
# days and always with different words, so the paper still feels varied.
BANK = [
    "##.....|#......|#......|...#...|......#|......#|.....##",
    "....###|......#|.......|...#...|.......|#......|###....",
    "###....|#......|.......|...#...|.......|......#|....###",
    "##...##|......#|.......|...#...|.......|#......|##...##",
    "##...##|#......|.......|...#...|.......|......#|##...##",
    "##....#|#.....#|.......|...#...|.......|#.....#|#....##",
    "#....##|#.....#|.......|...#...|.......|#.....#|##....#",
]
BANK = [row.split("|") for row in BANK]

def answers_of(clues):
    return set(e["answer"] for e in clues["across"] + clues["down"])

def load_frozen():
    """Return frozen issues (date<=FREEZE_THROUGH) as dicts, oldest first."""
    frozen = []
    for fn in sorted(os.listdir(DATA)):
        if not (fn.endswith(".json") and fn[0].isdigit()):
            continue
        j = json.load(open(os.path.join(DATA, fn)))
        d = date.fromisoformat(j["date"])
        if d <= FREEZE_THROUGH:
            frozen.append(j)
    frozen.sort(key=lambda j: j["date"])
    return frozen

def fill_issue(pat, forbid):
    """Seed-search until this grid fills without any forbidden answer."""
    for seed in range(1, 4000):
        p = generate(seed, pat, budget=60000, forbid=forbid)
        if p:
            return seed, p
    return None, None

def main():
    dry = "--dry" in sys.argv
    frozen = load_frozen()
    # answer history in publish order, so the no-repeat window can look back
    recent = [answers_of(j["clues"]) for j in frozen]

    start = FREEZE_THROUGH + timedelta(days=1)
    future = []
    missing = set()
    for i in range(FUTURE_COUNT):
        d = start + timedelta(days=i)
        pat = BANK[i % len(BANK)]
        forbid = set().union(*recent[-NO_REPEAT_WINDOW:]) if recent else set()
        seed, p = fill_issue(pat, forbid)
        if not p:
            raise SystemExit(f"{d}: could not fill grid {i % len(BANK)} "
                             f"with {len(forbid)} forbidden")
        ans = answers_of(p)
        recent.append(ans)
        for w in ans:
            if w not in CLUES:
                missing.add(w)
        future.append((d, seed, i % len(BANK), p))
        print(f"  {d} grid#{i%len(BANK)} seed={seed} "
              f"3-letter={sum(len(w)==3 for w in ans)} forbid={len(forbid)}",
              file=sys.stderr)

    if missing:
        print(f"\nMISSING {len(missing)} clues:", file=sys.stderr)
        print(" ".join(sorted(missing)))
        if dry:
            return
        raise SystemExit("write the missing clues into cluebank.py, then rerun")
    if dry:
        print("all clued.")
        return

    # hard check: no answer repeats within the window across frozen+future
    allrecent = recent
    for i in range(len(allrecent)):
        for j in range(max(0, i - NO_REPEAT_WINDOW + 1), i):
            clash = allrecent[i] & allrecent[j]
            if clash:
                raise SystemExit(f"repeat within window: {clash}")

    # write frozen (unchanged) + future, rebuild index
    index = []
    for j in frozen:
        index.append({"date": j["date"], "issue": j["issue"], "id": j["id"],
                      "title": j.get("title") or title_for(date.fromisoformat(j["date"])),
                      "size": j["size"], "reviewed": j.get("reviewed", True)})
    base_issue = max((j["issue"] for j in frozen), default=0)
    for k, (d, seed, gi, p) in enumerate(future):
        ds = d.isoformat()
        issue_no = base_issue + k + 1
        title = title_for(d)
        def clue_list(entries):
            return [{"num": e["num"], "clue": CLUES[e["answer"]], "answer": e["answer"]}
                    for e in entries]
        obj = {"issue": issue_no, "title": title, "author": AUTHOR,
               "size": p["size"], "grid": p["grid"],
               "clues": {"across": clue_list(p["across"]), "down": clue_list(p["down"])},
               "id": ds, "date": ds, "reviewed": False}
        json.dump(obj, open(os.path.join(DATA, f"{ds}.json"), "w"), indent=1)
        index.append({"date": ds, "issue": issue_no, "id": ds, "title": title,
                      "size": p["size"], "reviewed": False})

    index.sort(key=lambda x: x["date"], reverse=True)
    json.dump(index, open(os.path.join(DATA, "index.json"), "w"), indent=1)
    json.dump([], open(os.path.join(DATA, "queue.json"), "w"))
    print(f"wrote {len(future)} future issues; froze {len(frozen)}.", file=sys.stderr)

if __name__ == "__main__":
    main()
