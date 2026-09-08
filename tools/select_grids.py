#!/usr/bin/env python3
"""Generate many 7x7 grids and greedily select a low-overlap set:
distinct 7-letter marquee answers, minimal short-fill repetition, no proper nouns.
Prints the chosen seeds and the union of answers to clue."""
import sys
from generate_midi import generate

# Proper nouns / brands that slip into the common-word 7-letter list.
PROPER = {
    "AMERICA", "ENGLAND", "MYANMAR", "DOUGLAS", "STEPHEN", "KENNETH", "KENNEDY",
    "LEONARD", "BENNETT", "JACKSON", "JOHNSON", "MICHAEL", "ANDREWS", "EDWARDS",
    "SPENCER", "RUSSIAN", "SPANISH", "MYSPACE", "PACIFIC", "ATLANTA", "ONTARIO",
    "ANTHONY", "BRISTOL", "GERMANY", "FLORIDA", "CHELSEA", "ARSENAL", "ORLANDO",
    "VERMONT", "OAKLAND", "PHOENIX", "ESPANOL", "ARIZONA", "ALBERTA", "ROMANCE",
    "TRIBUNE", "SEATTLE", "TORONTO", "GATEWAY", "HOTMAIL", "NETWORK",
    "BARBARA", "SENEGAL", "SWEDISH", "FINNISH", "ESTONIA", "BELGIUM", "AUSTRIA",
    "DENMARK", "NORWICH", "HELSINKI", "CATALAN", "PORTUGAL", "JAMAICA", "ABRAHAM", "ISRAELI", "ITALIAN", "IRELAND", "SCOTTIE",
}
# Awkward fill and anything off-tone for a family puzzle.
AVOID = {"THEREBY", "ONGOING", "STATUTE", "SEGMENT", "TACTICS", "EROTICA",
         "TELECOM", "ADAPTOR", "LEXMARK", "LESBIAN", "PENTIUM", "COMPAQ"}

def answers(p):
    return [e["answer"] for e in p["across"] + p["down"]]

# Generate candidates.
cands = []
for seed in range(1, 121):
    p = generate(seed)
    if not p:
        continue
    ans = answers(p)
    if any(w in PROPER or w in AVOID for w in ans):
        continue
    marquee = [w for w in ans if len(w) == 7]
    cands.append({"seed": seed, "ans": ans, "marquee": marquee})

print(f"{len(cands)} clean candidates", file=sys.stderr)

# Greedy selection: prefer grids whose words (esp. marquee) are least-seen so far.
K = int(sys.argv[1]) if len(sys.argv) > 1 else 12
selected = []
used_marquee = set()
used_words = set()
pool = cands[:]
while pool and len(selected) < K:
    def score(c):
        if any(m in used_marquee for m in c["marquee"]):
            return (10**6, 0)  # never reuse a marquee word
        repeats = sum(1 for w in c["ans"] if w in used_words)
        return (repeats, c["seed"])
    pool.sort(key=score)
    best = pool.pop(0)
    if any(m in used_marquee for m in best["marquee"]):
        break  # remaining all reuse marquee words
    selected.append(best)
    used_marquee.update(best["marquee"])
    used_words.update(best["ans"])

print(f"selected {len(selected)} grids\n")
union = []
seen = set()
for i, c in enumerate(selected, 1):
    print(f"#{i} seed {c['seed']}  marquee={c['marquee']}")
    print("   " + " ".join(c["ans"]))
    for w in c["ans"]:
        if w not in seen:
            seen.add(w); union.append(w)
# repetition report
from collections import Counter
allw = Counter(w for c in selected for w in c["ans"])
reps = {w: n for w, n in allw.items() if n > 1}
print(f"\nseeds = {[c['seed'] for c in selected]}")
print(f"unique words to clue: {len(union)}")
print(f"repeated words ({len(reps)}): {dict(sorted(reps.items(), key=lambda x:-x[1]))}")
