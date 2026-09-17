#!/usr/bin/env python3
"""Import a community puzzle from Crosshare into The Word Gazette.

Crosshare (https://crosshare.org) is a free, open-source community of crossword
constructors. Every puzzle is owned by ITS constructor, so this tool imports one
SPECIFIC puzzle at a time, by URL or id — it is deliberately NOT a bulk scraper.
Only import puzzles whose constructor is happy to have them republished, and the
constructor's name rides along as the byline.

Crosshare serves a puzzle as an Across-Lite .puz at:
    https://crosshare.org/api/puz/<puzzleId>
and puzzle pages look like:
    https://crosshare.org/crosswords/<puzzleId>/<slug>

Usage:
    python3 import_crosshare.py <crosshare-url-or-id> [--date YYYY-MM-DD]
    python3 import_crosshare.py --file some.puz [--date YYYY-MM-DD]   # local test

The imported issue is written UNREVIEWED, so it lands in the admin queue for you
to check and approve before readers ever see it.
"""
import argparse, json, os, re, sys, urllib.request
from datetime import date, timedelta

import puz

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "public", "data")
PUZ_ENDPOINT = "https://crosshare.org/api/puz/{id}"

def extract_id(s):
    """Accept a full Crosshare URL or a bare puzzle id."""
    s = s.strip()
    m = re.search(r"/crosswords/([A-Za-z0-9]+)", s)
    if m:
        return m.group(1)
    m = re.search(r"/api/puz/([A-Za-z0-9]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", s):
        return s
    raise SystemExit(f"Could not find a Crosshare puzzle id in: {s!r}")

def fetch_puz(pid):
    url = PUZ_ENDPOINT.format(id=pid)
    req = urllib.request.Request(url, headers={"User-Agent": "WordGazette-importer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise SystemExit(f"Crosshare returned HTTP {r.status} for {url}")
        return r.read()

def convert(p, source_url=None):
    """puzpy Puzzle -> Word Gazette issue dict (minus date/issue number)."""
    w, h = p.width, p.height
    if w != h:
        raise SystemExit(f"Puzzle is {w}x{h}; only square grids are supported for now.")
    sol = p.solution
    def ch(i):
        c = sol[i]
        return "#" if c == "." else c.upper()
    grid = [[ch(r * w + c) for c in range(w)] for r in range(h)]

    num = p.clue_numbering()
    def across_answer(e):
        return "".join(sol[e["cell"] + i] for i in range(e["len"])).upper()
    def down_answer(e):
        return "".join(sol[e["cell"] + i * w] for i in range(e["len"])).upper()

    def clean(s):
        return (s or "").strip()

    across = [{"num": e["num"], "clue": clean(e["clue"]), "answer": across_answer(e)}
              for e in num.across]
    down = [{"num": e["num"], "clue": clean(e["clue"]), "answer": down_answer(e)}
            for e in num.down]

    # sanity: every clue present, answers are letters only
    for e in across + down:
        if not e["clue"]:
            raise SystemExit(f"Missing clue for entry {e['num']} ({e['answer']})")
        if not e["answer"].isalpha():
            raise SystemExit(f"Non-letter answer {e['answer']!r} (rebus/shaded squares "
                             "aren't supported yet)")

    issue = {
        "title": clean(p.title) or "Community Crossword",
        "author": clean(p.author) or "A Crosshare constructor",
        "size": w,
        "grid": grid,
        "clues": {"across": across, "down": down},
        "source": "crosshare",
    }
    if source_url:
        issue["sourceUrl"] = source_url
    return issue

def next_date_and_issue():
    idx_path = os.path.join(DATA, "index.json")
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else []
    if index:
        last = max(index, key=lambda e: e["date"])
        d = date.fromisoformat(last["date"]) + timedelta(days=1)
        issue_no = max(e["issue"] for e in index) + 1
    else:
        d = date.today()
        issue_no = 1
    return d.isoformat(), issue_no, index

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="Crosshare URL or puzzle id")
    ap.add_argument("--file", help="Read a local .puz instead of fetching (testing)")
    ap.add_argument("--date", help="Publish date YYYY-MM-DD (default: day after latest)")
    args = ap.parse_args()

    if args.file:
        p = puz.read(args.file)
        source_url = None
    else:
        if not args.source:
            raise SystemExit("Give a Crosshare URL/id, or use --file for a local .puz")
        pid = extract_id(args.source)
        source_url = f"https://crosshare.org/crosswords/{pid}"
        p = puz.load(fetch_puz(pid))

    issue = convert(p, source_url)

    ds, issue_no, index = next_date_and_issue()
    if args.date:
        ds = args.date
    issue["issue"] = issue_no
    issue["id"] = ds
    issue["date"] = ds
    issue["reviewed"] = False

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, f"{ds}.json")
    json.dump(issue, open(out, "w"), indent=1)

    # refresh index (replace any row with the same date, then re-sort newest first)
    index = [e for e in index if e["date"] != ds]
    index.append({"date": ds, "issue": issue_no, "id": ds,
                  "title": issue["title"], "size": issue["size"], "reviewed": False})
    index.sort(key=lambda e: e["date"], reverse=True)
    json.dump(index, open(os.path.join(DATA, "index.json"), "w"), indent=1)

    print(f"Imported '{issue['title']}' by {issue['author']} "
          f"({issue['size']}x{issue['size']}) as {ds} (issue {issue_no}, UNREVIEWED).")

if __name__ == "__main__":
    main()
