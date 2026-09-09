#!/usr/bin/env python3
"""Backtracking crossword filler over a common-word list.
Fills a fixed symmetric 7x7 pattern with everyday words (so every entry
is easy to clue by hand). Emits the solved grid + entry list as JSON.
"""
import json, sys, random
from collections import defaultdict

N = 7
BLOCK = "#"

# A bank of distinct, hand-checked 7x7 midi patterns (180-degree symmetric,
# every white cell crosses an Across AND a Down word of length >= 3, one
# connected white region). validate_pattern() below enforces those rules, and
# build_issues.py gives each issue a different pattern so no two grids share a
# black-square layout. PATTERNS[0] is the original grid.
PATTERNS = [
    ["...#...",
     "...#...",
     ".......",
     "##...##",
     ".......",
     "...#...",
     "...#..."],

    ["....#..",
     "....#..",
     ".......",
     "#.....#",
     ".......",
     "..#....",
     "..#...."],

    ["..#....",
     "..#....",
     ".......",
     "...#...",
     ".......",
     "....#..",
     "....#.."],

    ["...#...",
     ".......",
     ".......",
     "##...##",
     ".......",
     ".......",
     "...#..."],

    ["....#..",
     "..#..#.",
     ".......",
     "#.....#",
     ".......",
     ".#..#..",
     "..#...."],

    ["#..#...",
     "....#..",
     ".......",
     "..#.#..",
     ".......",
     "..#....",
     "...#..#"],

    ["...#...",
     "...#...",
     ".......",
     ".......",
     ".......",
     "...#...",
     "...#..."],

    ["..#....",
     "..#..#.",
     ".......",
     "...#...",
     ".......",
     ".#..#..",
     "....#.."],
]
PATTERN = PATTERNS[0]     # default / backward-compatible

# Pattern currently being solved (set by generate()); cell()/white() read it.
_PAT = PATTERN

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

import os
HERE = os.path.dirname(os.path.abspath(__file__))

# A real English dictionary (all lowercase) for plural / stem detection.
DICT = set(w.strip().lower() for w in open(os.path.join(HERE, "words_alpha.txt"))
           if w.strip().isalpha())
ALLWORDS = DICT

def is_plural(w):
    """Heuristic: exclude -s plurals and 3rd-person verb forms (posters, teaches,
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

# The answer pool comes from a SCORED crossword word list (WORD;score, 0-100).
# Only well-scored, common entries make good daily answers, so keep score >=
# SCORE_MIN and rank by score (best first) so the filler prefers the nicest
# words and reaches for weaker ones only to complete a grid.
SCORE_MIN = 60
SCORE = {}
for line in open(os.path.join(HERE, "xwordlist.dict")):
    line = line.strip()
    if ";" not in line:
        continue
    w, s = line.rsplit(";", 1)
    w = w.upper()
    if not w.isalpha() or not s.isdigit():
        continue
    s = int(s)
    if s > SCORE.get(w, -1):
        SCORE[w] = s

# Proper nouns to keep out of a plain family crossword: countries, US states,
# and common first names (a few slip into the dictionary as lowercase words).
COUNTRIES = """AFGHANISTAN ALBANIA ALGERIA ANGOLA ARGENTINA ARMENIA AUSTRIA
AUSTRALIA AZERBAIJAN BAHRAIN BANGLADESH BELARUS BELGIUM BOLIVIA BOTSWANA BRAZIL
BULGARIA CAMBODIA CAMEROON CANADA CHILE CHINA COLOMBIA CONGO CROATIA CUBA CYPRUS
DENMARK ECUADOR EGYPT ENGLAND ERITREA ESTONIA ETHIOPIA FINLAND FRANCE GABON
GEORGIA GERMANY GHANA GREECE GUINEA GUYANA HAITI HONDURAS HUNGARY ICELAND INDIA
INDONESIA IRAN IRAQ IRELAND ISRAEL ITALY JAMAICA JAPAN JORDAN KENYA KOREA KOSOVO
KUWAIT LAOS LATVIA LEBANON LIBERIA LIBYA LITHUANIA LUXEMBOURG MADAGASCAR MALAWI
MALAYSIA MALI MALTA MEXICO MOLDOVA MONGOLIA MOROCCO MOZAMBIQUE MYANMAR NAMIBIA
NEPAL NICARAGUA NIGER NIGERIA NORWAY OMAN PAKISTAN PANAMA PARAGUAY PERU POLAND
PORTUGAL QATAR ROMANIA RUSSIA RWANDA SENEGAL SERBIA SINGAPORE SLOVAKIA SLOVENIA
SOMALIA SPAIN SUDAN SWEDEN SWITZERLAND SYRIA TAIWAN TANZANIA THAILAND TOGO
TUNISIA TURKEY UGANDA UKRAINE URUGUAY UZBEKISTAN VENEZUELA VIETNAM YEMEN ZAMBIA
ZIMBABWE SCOTLAND WALES""".split()
STATES = """ALABAMA ALASKA ARIZONA ARKANSAS CALIFORNIA COLORADO CONNECTICUT
DELAWARE FLORIDA GEORGIA HAWAII IDAHO ILLINOIS INDIANA IOWA KANSAS KENTUCKY
LOUISIANA MAINE MARYLAND MASSACHUSETTS MICHIGAN MINNESOTA MISSISSIPPI MISSOURI
MONTANA NEBRASKA NEVADA OHIO OKLAHOMA OREGON PENNSYLVANIA TENNESSEE TEXAS UTAH
VERMONT VIRGINIA WASHINGTON WISCONSIN WYOMING""".split()
try:
    NAMES = [n.strip().upper() for n in open(os.path.join(HERE, "firstnames.txt"))
             if n.strip().isalpha()]
except OSError:
    NAMES = []
PROPER_BLOCK = set(COUNTRIES) | set(STATES) | set(NAMES)

by_len = defaultdict(list)
by_len[3] = [w for w in sorted(set(W3)) if not is_plural(w)]  # curated clean 3s

def acceptable(w):
    """A real dictionary word, decently scored, not a plural or a proper noun."""
    return (w.lower() in DICT and w not in PROPER_BLOCK and not is_plural(w))

POOL_CAP = 8000
for L in (4, 5, 6, 7):
    words = [w for w, s in SCORE.items()
             if len(w) == L and s >= SCORE_MIN and acceptable(w)]
    words.sort(key=lambda w: (-SCORE[w], w))   # best score first, then A-Z
    by_len[L] = words[:POOL_CAP]

print(f"lengths: " + ", ".join(f"{L}:{len(by_len[L])}" for L in sorted(by_len)),
      file=sys.stderr)

# pattern index for fast candidate lookup: (len, pos, char) -> set(words)
index = {}
full = {L: set(ws) for L, ws in by_len.items()}
rank = {w: i for L in by_len for i, w in enumerate(by_len[L])}  # common-first ordering
for L, ws in by_len.items():
    for w in ws:
        for pos, ch in enumerate(w):
            index.setdefault((L, pos, ch), set()).add(w)

# --- build slots from the current pattern (_PAT) ---
def cell(r, c): return _PAT[r][c]
def white(r, c): return 0 <= r < N and 0 <= c < N and cell(r, c) != BLOCK

slots = []        # each: {"cells": [(r,c)...], "dir": "A"/"D"}
cell_slots = defaultdict(list)

def build_slots():
    """(Re)build slot/cell tables from the current pattern _PAT."""
    global slots, cell_slots
    slots = []
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
    cell_slots = defaultdict(list)
    for si, s in enumerate(slots):
        for pos, rc in enumerate(s["cells"]):
            cell_slots[rc].append((si, pos))
    # for forward checking: which slots cross each slot
    global slot_cross
    slot_cross = []
    for si, s in enumerate(slots):
        cross = set()
        for rc in s["cells"]:
            for (si2, _pos) in cell_slots[rc]:
                if si2 != si:
                    cross.add(si2)
        slot_cross.append(cross)

slot_cross = []

def validate_pattern(pat):
    """True if pat is a legal midi: 180-degree symmetric, every white cell in
    an Across AND Down word of length >= 3, single connected white region."""
    global _PAT
    if len(pat) != N or any(len(row) != N for row in pat):
        return False
    # rotational symmetry
    for r in range(N):
        for c in range(N):
            if (pat[r][c] == BLOCK) != (pat[N-1-r][N-1-c] == BLOCK):
                return False
    prev = _PAT
    _PAT = pat
    try:
        whites = [(r, c) for r in range(N) for c in range(N) if white(r, c)]
        if not whites:
            return False
        # every white cell must be crossed by an across and a down run of len>=3
        def run_len(r, c, dr, dc):
            n = 1
            rr, cc = r + dr, c + dc
            while white(rr, cc): n += 1; rr += dr; cc += dc
            rr, cc = r - dr, c - dc
            while white(rr, cc): n += 1; rr -= dr; cc -= dc
            return n
        for (r, c) in whites:
            if run_len(r, c, 0, 1) < 3 or run_len(r, c, 1, 0) < 3:
                return False
        # connectivity (flood fill)
        seen = {whites[0]}
        stack = [whites[0]]
        while stack:
            r, c = stack.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if white(nr, nc) and (nr, nc) not in seen:
                    seen.add((nr, nc)); stack.append((nr, nc))
        return len(seen) == len(whites)
    finally:
        _PAT = prev

grid = {}  # (r,c) -> letter or None (reset per generate())
def reset_grid():
    grid.clear()
    for r in range(N):
        for c in range(N):
            if white(r, c): grid[(r, c)] = None

build_slots()   # initialise for the default pattern

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

_budget = [0]        # remaining backtracking steps (set per generate())

def solve(unfilled, used):
    if not unfilled: return True
    _budget[0] -= 1
    if _budget[0] < 0: raise TimeoutError
    unfilled_set = set(unfilled)
    # MRV: pick the most-constrained slot (fewest candidates)
    best = min(unfilled, key=lambda si: len(candidates(si, used)))
    cands = sorted(candidates(best, used), key=lambda w: rank[w])
    # small randomization among the most-common candidates for variety
    head = cands[:40]; random.shuffle(head); cands = head + cands[40:]
    rest = [si for si in unfilled if si != best]
    neighbours = [si for si in slot_cross[best] if si in unfilled_set]
    before = {rc: grid[rc] for rc in slots[best]["cells"]}
    for w in cands:
        for pos, rc in enumerate(slots[best]["cells"]): grid[rc] = w[pos]
        used.add(w)
        # forward check: every crossing slot must still have a candidate
        if all(candidates(si2, used) for si2 in neighbours):
            if solve(rest, used): return True
        used.discard(w)
        for rc in slots[best]["cells"]: grid[rc] = before[rc]
    return False

def generate(seed, pattern=None, budget=200000):
    """Fill the grid for a given seed and pattern; return
    {size, grid, across, down} or None. pattern defaults to PATTERNS[0].
    budget caps backtracking steps so unfillable patterns bail fast."""
    global _PAT
    _PAT = pattern if pattern is not None else PATTERN
    build_slots()
    random.seed(seed)
    reset_grid()
    _budget[0] = budget
    try:
        if not solve(list(range(len(slots))), set()):
            return None
    except TimeoutError:
        return None       # gave up — treat as unfillable for this seed
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
