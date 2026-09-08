#!/usr/bin/env python3
"""Backtracking crossword filler over a common-word list.
Fills a fixed symmetric 7x7 pattern with everyday words (so every entry
is easy to clue by hand). Emits the solved grid + entry list as JSON.
"""
import json, sys, random
from collections import defaultdict

PATTERN = [
    "...#...",
    "...#...",
    ".......",
    "##...##",
    ".......",
    "...#...",
    "...#...",
]
N = 7
BLOCK = "#"

# --- word lists ---
# Curated clean 3-letter words (no abbreviations / initialisms) for the short slots.
W3 = """ACE ACT ADD AGE AGO AID AIM AIR ALE ALL AND ANT APE APT ARC ARE ARK ARM ART ASH ASK
BAD BAG BAN BAR BAT BAY BED BEE BEG BET BIG BIT BOA BOG BOW BOX BOY BUD BUG BUN BUS BUT BUY
CAB CAN CAP CAR CAT COB COD COG CON COO COP COT COW COY CRY CUB CUE CUP CUT
DAB DAM DAY DEN DEW DIG DIM DIP DOE DOG DOT DRY DUB DUE DUG DYE
EAR EAT EBB EEL EGG EGO ELF ELK ELM END EON ERA EVE EWE EYE
FAD FAN FAR FAT FEE FEW FIB FIG FIN FIR FIT FIX FLY FOE FOG FOR FOX FRY FUN FUR
GAP GAS GEL GEM GET GIG GIN GOD GOO GOT GUM GUN GUT GUY GYM
HAD HAM HAS HAT HAY HEM HEN HER HEW HID HIM HIP HIT HOE HOG HOP HOT HOW HUB HUE HUG HUM HUT
ICE ICY ILK ILL IMP INK INN ION IRE IRK IVY
JAB JAM JAR JAW JAY JET JIG JOB JOG JOT JOY JUG JUT
KEG KEY KID KIN KIT
LAB LAD LAG LAP LAW LAY LED LEG LET LID LIE LIP LIT LOB LOG LOT LOW LUG
MAD MAN MAP MAR MAT MAW MEN MET MID MIX MOB MOD MOM MOP MUD MUG MUM
NAB NAG NAP NET NEW NIB NIL NIP NOD NOR NOT NOW NUB NUN NUT
OAK OAR OAT ODD ODE OFF OFT OHM OIL OLD ONE ORB ORE OUR OUT OVA OWE OWL OWN
PAD PAL PAN PAR PAT PAW PAY PEA PEG PEN PEP PER PET PEW PIE PIG PIN PIT POD POP POT PRY PUB PUG PUN PUP PUT
RAG RAM RAN RAP RAT RAW RAY RED RIB RID RIG RIM RIP ROB ROD ROE ROT ROW RUB RUE RUG RUM RUN RUT RYE
SAD SAG SAP SAT SAW SAY SEA SEE SET SEW SHE SHY SIN SIP SIR SIT SIX SKI SKY SLY SOB SOD SON SOW SOY SPA SPY STY SUB SUE SUM SUN
TAB TAG TAN TAP TAR TAX TEA TEE TEN THE TIC TIE TIN TIP TOE TON TOO TOP TOW TOY TRY TUB TUG TWO
UMP URN USE
VAN VAT VET VIA VIE VOW
WAD WAG WAR WAS WAX WAY WEB WED WEE WET WHO WHY WIG WIN WIT WOE WOK WON WOO WOW WRY
YAK YAM YAP YAW YEA YEN YES YET YEW YOU
ZAP ZED ZEN ZIP ZOO""".split()

W3 = [w for w in W3 if w != "OVA"]          # OVA reads as a plural; drop it
by_len = defaultdict(list)
by_len[3] = sorted(set(W3))

# Full common-word set (for plural detection by stem lookup).
ALLWORDS = set(x.strip().lower() for x in open("/tmp/common10k.txt") if x.strip().isalpha())

def is_plural(w):
    """Heuristic: exclude -s plurals and 3rd-person verb forms (poster s, teaches,
    stories) while keeping real -s words (gas, bus, chaos, address)."""
    wl = w.lower()
    if wl.endswith("ss"):
        return False
    if wl.endswith("ies") and (wl[:-3] + "y") in ALLWORDS:
        return True                         # stories -> story
    if wl.endswith("es") and wl[:-2] in ALLWORDS and len(wl) - 2 >= 3:
        return True                         # glasses -> glass, teaches -> teach
    if wl.endswith("s") and wl[:-1] in ALLWORDS and len(wl) - 1 >= 3:
        return True                         # posters -> poster, writes -> write
    return False

# 7-letter words: common list, alphabetic, no plurals, minus obvious proper nouns.
BLOCK7 = {"BRISTOL", "TRIBUNE", "PACIFIC", "ATLANTA", "ONTARIO", "ANTHONY", "RUSSIAN",
          "MICHAEL", "ANDREWS", "JACKSON", "JOHNSON", "EDWARDS", "DENNIS", "SPENCER"}
for w in (x.strip().upper() for x in open("/tmp/common10k.txt")):
    if (len(w) == 7 and w.isalpha() and w not in BLOCK7
            and not is_plural(w) and w not in by_len[7]):
        by_len[7].append(w)      # keep frequency order (common first)
# also drop plurals that slipped into the 3-letter list (none expected, but be safe)
by_len[3] = [w for w in by_len[3] if not is_plural(w)]
print(f"3-letter: {len(by_len[3])}, 7-letter: {len(by_len[7])}", file=sys.stderr)

# pattern index for fast candidate lookup: (len, pos, char) -> set(words)
index = {}
full = {L: set(ws) for L, ws in by_len.items()}
rank = {w: i for L in by_len for i, w in enumerate(by_len[L])}  # common-first ordering
for L, ws in by_len.items():
    for w in ws:
        for pos, ch in enumerate(w):
            index.setdefault((L, pos, ch), set()).add(w)

# --- build slots from the pattern ---
def cell(r, c): return PATTERN[r][c]
def white(r, c): return 0 <= r < N and 0 <= c < N and cell(r, c) != BLOCK

slots = []  # each: {"cells": [(r,c)...], "dir": "A"/"D"}
for r in range(N):
    for c in range(N):
        if not white(r, c): continue
        if not white(r, c - 1) and white(r, c + 1):
            cells = []
            cc = c
            while white(r, cc): cells.append((r, cc)); cc += 1
            slots.append({"cells": cells, "dir": "A"})
        if not white(r - 1, c) and white(r + 1, c):
            cells = []
            rr = r
            while white(rr, c): cells.append((rr, c)); rr += 1
            slots.append({"cells": cells, "dir": "D"})

# map each cell to the slots crossing it, and each slot to its length
cell_slots = defaultdict(list)
for si, s in enumerate(slots):
    for pos, rc in enumerate(s["cells"]):
        cell_slots[rc].append((si, pos))

grid = {}  # (r,c) -> letter or None (reset per generate())
def reset_grid():
    grid.clear()
    for r in range(N):
        for c in range(N):
            if white(r, c): grid[(r, c)] = None

def candidates(si, used):
    s = slots[si]; L = len(s["cells"])
    pool = None
    for pos, rc in enumerate(s["cells"]):
        ch = grid[rc]
        if ch is None: continue
        cand = index.get((L, pos, ch))
        if cand is None: return []
        pool = cand if pool is None else (pool & cand)
        if not pool: return []
    if pool is None: pool = full[L]
    return pool - used

def solve(unfilled, used):
    if not unfilled: return True
    # MRV: fewest candidates first
    best = min(unfilled, key=lambda si: len(candidates(si, used)))
    cands = sorted(candidates(best, used), key=lambda w: rank[w])
    # small randomization among the most-common candidates for variety
    head = cands[:40]; random.shuffle(head); cands = head + cands[40:]
    rest = [si for si in unfilled if si != best]
    before = {rc: grid[rc] for rc in slots[best]["cells"]}
    for w in cands:
        for pos, rc in enumerate(slots[best]["cells"]): grid[rc] = w[pos]
        used.add(w)
        if solve(rest, used): return True
        used.discard(w)
        for rc in slots[best]["cells"]: grid[rc] = before[rc]
    return False

def generate(seed):
    """Fill the grid for a given seed; return {size, grid, across, down} or None."""
    random.seed(seed)
    reset_grid()
    if not solve(list(range(len(slots))), set()):
        return None
    num = {}
    counter = 0
    across, down = [], []
    for r in range(N):
        for c in range(N):
            if not white(r, c): continue
            sa = not white(r, c - 1) and white(r, c + 1)
            sd = not white(r - 1, c) and white(r + 1, c)
            if sa or sd:
                counter += 1; num[(r, c)] = counter
    for s in slots:
        r, c = s["cells"][0]
        word = "".join(grid[rc] for rc in s["cells"])
        entry = {"num": num[(r, c)], "answer": word}
        (across if s["dir"] == "A" else down).append(entry)
    across.sort(key=lambda e: e["num"]); down.sort(key=lambda e: e["num"])
    rows = [["#" if cell(r, c) == BLOCK else grid[(r, c)] for c in range(N)] for r in range(N)]
    return {"size": N, "grid": rows, "across": across, "down": down}


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = generate(seed)
    if not result:
        print("no fill", file=sys.stderr); sys.exit(1)
    print(json.dumps(result, indent=1))
