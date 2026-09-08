// The Word Gazette — client (prototype)
// Loads a puzzle JSON, renders a numbered newspaper grid, and lets you solve it.

const BLOCK = "#";

// ---- small icon set (inline SVG so it inks like everything else) ----
const ICON = {
  // Clean outline cog (Feather "settings").
  gear: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  pause: `<svg viewBox="0 0 24 24" width="14" height="14"><rect x="6" y="5" width="4" height="14" fill="currentColor"/><rect x="14" y="5" width="4" height="14" fill="currentColor"/></svg>`,
  play: `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M7 5l12 7-12 7z"/></svg>`,
  reset: `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12 5V2L7 6l5 4V7a5 5 0 11-5 5H5a7 7 0 107-7z"/></svg>`,
};

const BASE = import.meta.env.BASE_URL;
async function fetchJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Could not load ${path}`);
  return res.json();
}
function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function longDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString("en-US",
    { weekday: "long", year: "numeric", month: "long", day: "numeric" }).toUpperCase();
}

// Assign standard crossword numbers and record where each entry starts.
function numberGrid(grid) {
  const n = grid.length;
  const nums = grid.map((row) => row.map(() => 0));
  const acrossStart = {};
  const downStart = {};
  let counter = 0;
  const isWhite = (r, c) => r >= 0 && c >= 0 && r < n && c < n && grid[r][c] !== BLOCK;
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (!isWhite(r, c)) continue;
      const startsAcross = !isWhite(r, c - 1) && isWhite(r, c + 1);
      const startsDown = !isWhite(r - 1, c) && isWhite(r + 1, c);
      if (startsAcross || startsDown) {
        counter += 1;
        nums[r][c] = counter;
        if (startsAcross) acrossStart[counter] = { r, c };
        if (startsDown) downStart[counter] = { r, c };
      }
    }
  }
  return { nums, acrossStart, downStart };
}

function entryCells(grid, r, c, dir) {
  const n = grid.length;
  const cells = [];
  let rr = r, cc = c;
  while (rr < n && cc < n && grid[rr][cc] !== BLOCK) {
    cells.push({ r: rr, c: cc });
    if (dir === "across") cc += 1; else rr += 1;
  }
  return cells;
}

class Puzzle {
  constructor(data) {
    this.data = data;
    this.grid = data.grid;
    this.size = data.size;
    const { nums, acrossStart, downStart } = numberGrid(this.grid);
    this.nums = nums;
    this.acrossStart = acrossStart;
    this.downStart = downStart;
    this.dir = "across";
    this.active = null;
    this.inputs = {};
    this.cells = {};
    this.clueText = { across: {}, down: {} };
    this.autocheck = false;
    this.solved = false;
    this.wasFull = false;
    this.onSolved = null;      // fired once when fully & correctly filled
    this.onIncomplete = null;  // fired when fully filled but some words are wrong
    this.onChange = null;      // fired whenever the grid state changes (for persistence)
  }

  render() {
    const gridEl = document.getElementById("grid");
    gridEl.style.gridTemplateColumns = `repeat(${this.size}, 1fr)`;
    gridEl.innerHTML = "";
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const cell = document.createElement("div");
        const key = `${r},${c}`;
        if (this.grid[r][c] === BLOCK) {
          cell.className = "cell cell--block";
          gridEl.appendChild(cell);
          continue;
        }
        cell.className = "cell";
        cell.setAttribute("role", "gridcell");
        if (this.nums[r][c]) {
          const num = document.createElement("span");
          num.className = "cell__num";
          num.textContent = this.nums[r][c];
          cell.appendChild(num);
        }
        const input = document.createElement("input");
        // No maxLength: letters are handled in keydown (so retyping overwrites);
        // the input handler keeps only the last char for mobile/IME.
        input.inputMode = "text";
        input.autocomplete = "off";
        input.addEventListener("focus", () => this.setActive(r, c));
        input.addEventListener("mousedown", () => {
          if (this.active && this.active.r === r && this.active.c === c) this.toggleDir();
        });
        input.addEventListener("input", (e) => this.onInput(e, r, c));
        input.addEventListener("keydown", (e) => this.onKey(e, r, c));
        cell.appendChild(input);
        this.inputs[key] = input;
        this.cells[key] = cell;
        gridEl.appendChild(cell);
      }
    }
    this.renderClues();
    const first = this.acrossStart[1] || this.downStart[1];
    if (first) this.focus(first.r, first.c);
  }

  renderClues() {
    const fill = (listId, arr, dir) => {
      const ol = document.getElementById(listId);
      ol.innerHTML = "";
      for (const clue of arr) {
        this.clueText[dir][clue.num] = clue.clue;
        const li = document.createElement("li");
        li.dataset.num = clue.num;
        li.dataset.dir = dir;
        li.innerHTML = `<span class="num">${clue.num}</span><span>${clue.clue}</span>`;
        li.addEventListener("click", () => {
          const start = dir === "across" ? this.acrossStart[clue.num] : this.downStart[clue.num];
          if (!start) return;
          this.dir = dir;
          this.focus(start.r, start.c);
        });
        ol.appendChild(li);
      }
    };
    fill("clues-across", this.data.clues.across, "across");
    fill("clues-down", this.data.clues.down, "down");
  }

  focus(r, c) {
    const el = this.inputs[`${r},${c}`];
    if (el) el.focus();
  }

  toggleDir() {
    this.dir = this.dir === "across" ? "down" : "across";
    if (this.active) this.highlight(this.active.r, this.active.c);
  }

  setActive(r, c) {
    this.active = { r, c };
    this.highlight(r, c);
  }

  currentWordCells(r, c) {
    let rr = r, cc = c;
    const back = this.dir === "across" ? [0, -1] : [-1, 0];
    while (true) {
      const pr = rr + back[0], pc = cc + back[1];
      if (pr < 0 || pc < 0 || this.grid[pr][pc] === BLOCK) break;
      rr = pr; cc = pc;
    }
    return entryCells(this.grid, rr, cc, this.dir);
  }

  highlight(r, c) {
    Object.values(this.cells).forEach((el) =>
      el.classList.remove("cell--active", "cell--inword"));
    document.querySelectorAll(".clues__list li").forEach((li) => li.classList.remove("active"));

    const word = this.currentWordCells(r, c);
    word.forEach(({ r: wr, c: wc }) => this.cells[`${wr},${wc}`].classList.add("cell--inword"));
    this.cells[`${r},${c}`].classList.add("cell--active");

    const start = word[0];
    const startNum = this.nums[start.r][start.c];
    const li = document.querySelector(`.clues__list li[data-num="${startNum}"][data-dir="${this.dir}"]`);
    if (li) { li.classList.add("active"); li.scrollIntoView({ block: "nearest" }); }

    const bar = document.getElementById("cluebar");
    if (bar) {
      const txt = this.clueText[this.dir][startNum] || "";
      bar.innerHTML = `<span class="num">${startNum}</span><span>${txt}</span>`;
    }
  }

  // ---- scopes ----
  allCells() { const a = []; this.eachWhite((r, c) => a.push({ r, c })); return a; }
  scopeCells(scope) {
    if (scope === "letter") return this.active ? [this.active] : [];
    if (scope === "word") return this.active ? this.currentWordCells(this.active.r, this.active.c) : [];
    return this.allCells(); // puzzle
  }

  markCell(r, c) {
    const el = this.inputs[`${r},${c}`], cell = this.cells[`${r},${c}`];
    cell.classList.remove("cell--correct", "cell--wrong");
    if (!el.value) return;
    cell.classList.add(el.value === this.grid[r][c] ? "cell--correct" : "cell--wrong");
  }
  clearMark(r, c) {
    this.cells[`${r},${c}`].classList.remove("cell--correct", "cell--wrong");
  }

  check(scope) {
    for (const { r, c } of this.scopeCells(scope)) this.markCell(r, c);
    this.changed();
  }
  reveal(scope) {
    for (const { r, c } of this.scopeCells(scope)) {
      this.inputs[`${r},${c}`].value = this.grid[r][c];
      this.cells[`${r},${c}`].classList.add("cell--correct");
      this.cells[`${r},${c}`].classList.remove("cell--wrong");
    }
    this.evaluateCompletion();
    this.changed();
  }
  clear(scope) {
    for (const { r, c } of this.scopeCells(scope)) {
      this.inputs[`${r},${c}`].value = "";
      this.clearMark(r, c);
    }
    // Emptying squares un-solves the grid so a fresh solve celebrates again.
    if (!this.allFilled()) { this.solved = false; this.wasFull = false; }
    this.changed();
  }

  setAutocheck(on) {
    this.autocheck = on;
    if (on) this.check("puzzle"); else this.changed();
  }

  allFilled() {
    let full = true;
    this.eachWhite((r, c) => { if (!this.inputs[`${r},${c}`].value) full = false; });
    return full;
  }
  isAllCorrect() {
    let ok = true;
    this.eachWhite((r, c) => { if (this.inputs[`${r},${c}`].value !== this.grid[r][c]) ok = false; });
    return ok;
  }
  incorrectWordCount() {
    let n = 0;
    for (const dir of ["across", "down"]) {
      for (const cl of this.data.clues[dir]) {
        const s = this.startOf(dir, cl.num);
        const cells = entryCells(this.grid, s.r, s.c, dir);
        if (cells.some(({ r, c }) => this.inputs[`${r},${c}`].value !== this.grid[r][c])) n++;
      }
    }
    return n;
  }
  // Called after each fill. Fires onSolved (all correct) or onIncomplete (all
  // filled but some wrong) — the latter only once per time the grid fills up.
  evaluateCompletion() {
    if (this.solved) return;
    if (!this.allFilled()) { this.wasFull = false; return; }
    if (this.isAllCorrect()) {
      this.solved = true;
      this.wasFull = true;
      if (this.onSolved) this.onSolved();
    } else if (!this.wasFull) {
      this.wasFull = true;
      if (this.onIncomplete) this.onIncomplete(this.incorrectWordCount());
    }
  }

  changed() { if (this.onChange) this.onChange(); }

  setLetter(r, c, ch) {
    const el = this.inputs[`${r},${c}`];
    el.value = ch.toUpperCase();
    this.clearMark(r, c);
    if (this.autocheck && el.value) this.markCell(r, c);
  }

  // Fallback for mobile / IME where keydown letters aren't reliable.
  onInput(e, r, c) {
    const v = e.target.value.toUpperCase().replace(/[^A-Z]/g, "");
    e.target.value = v.slice(-1);
    this.clearMark(r, c);
    if (this.autocheck && e.target.value) this.markCell(r, c);
    if (e.target.value) this.advance(r, c, 1);
    this.evaluateCompletion();
    this.changed();
  }

  advance(r, c, step) {
    const word = this.currentWordCells(r, c);
    const idx = word.findIndex((p) => p.r === r && p.c === c);
    const next = word[idx + step];
    if (next) this.focus(next.r, next.c);
  }

  // ---- clue-to-clue navigation (Tab / Shift+Tab / Enter) ----
  entriesFlat() {
    const a = this.data.clues.across.map((c) => ({ dir: "across", num: c.num }));
    const d = this.data.clues.down.map((c) => ({ dir: "down", num: c.num }));
    return a.concat(d);
  }
  startOf(dir, num) { return dir === "across" ? this.acrossStart[num] : this.downStart[num]; }
  currentEntry() {
    if (!this.active) return null;
    const word = this.currentWordCells(this.active.r, this.active.c);
    const s = word[0];
    return { dir: this.dir, num: this.nums[s.r][s.c] };
  }
  gotoEntry(delta) {
    const flat = this.entriesFlat();
    if (!flat.length) return;
    const cur = this.currentEntry();
    let i = cur ? flat.findIndex((e) => e.dir === cur.dir && e.num === cur.num) : -1;
    if (i < 0) i = delta > 0 ? -1 : 0;
    const e = flat[(i + delta + flat.length) % flat.length];
    this.dir = e.dir;
    const start = this.startOf(e.dir, e.num);
    const cells = entryCells(this.grid, start.r, start.c, e.dir);
    const target = cells.find(({ r, c }) => !this.inputs[`${r},${c}`].value) || cells[0];
    this.focus(target.r, target.c);
  }

  onKey(e, r, c) {
    const key = e.key;

    // Letter: overwrite the square and advance (NYT behavior).
    if (/^[a-zA-Z]$/.test(key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      this.setLetter(r, c, key);
      this.advance(r, c, 1);
      this.evaluateCompletion();
      this.changed();
      return;
    }

    if (key === "Backspace") {
      e.preventDefault();
      const el = this.inputs[`${r},${c}`];
      if (el.value) {
        el.value = "";
        this.clearMark(r, c);
        this.advance(r, c, -1);          // clear current, step back
      } else {
        const word = this.currentWordCells(r, c);
        const idx = word.findIndex((p) => p.r === r && p.c === c);
        const prev = word[idx - 1];
        if (prev) {
          this.inputs[`${prev.r},${prev.c}`].value = "";
          this.clearMark(prev.r, prev.c);
          this.focus(prev.r, prev.c);     // step back and clear that one
        }
      }
      this.changed();
      return;
    }

    if (key === "Delete") {
      e.preventDefault();
      this.inputs[`${r},${c}`].value = "";
      this.clearMark(r, c);
      this.changed();
      return;
    }

    if (key === "Tab") { e.preventDefault(); this.gotoEntry(e.shiftKey ? -1 : 1); return; }
    if (key === "Enter") { e.preventDefault(); this.gotoEntry(1); return; }
    if (key === " ") { e.preventDefault(); this.toggleDir(); return; }

    // Arrows: perpendicular arrow switches direction on the same square;
    // a parallel arrow moves one white square in that direction.
    const moves = {
      ArrowRight: [0, 1, "across"], ArrowLeft: [0, -1, "across"],
      ArrowDown: [1, 0, "down"], ArrowUp: [-1, 0, "down"],
    };
    if (moves[key]) {
      e.preventDefault();
      const [dr, dc, dir] = moves[key];
      if (this.dir !== dir) { this.dir = dir; this.highlight(r, c); return; }
      let nr = r + dr, nc = c + dc;
      while (nr >= 0 && nc >= 0 && nr < this.size && nc < this.size) {
        if (this.grid[nr][nc] !== BLOCK) { this.focus(nr, nc); break; }
        nr += dr; nc += dc;
      }
    }
  }

  eachWhite(fn) {
    for (let r = 0; r < this.size; r++)
      for (let c = 0; c < this.size; c++)
        if (this.grid[r][c] !== BLOCK) fn(r, c);
  }

  // ---- persistence ----
  serialize() {
    const entries = {};
    this.eachWhite((r, c) => {
      const v = this.inputs[`${r},${c}`].value;
      if (v) entries[`${r},${c}`] = v;
    });
    return { entries, autocheck: this.autocheck, solved: this.solved };
  }
  restoreEntries(entries) {
    if (!entries) return;
    for (const [key, v] of Object.entries(entries)) {
      if (this.inputs[key]) this.inputs[key].value = v;
    }
    if (this.autocheck) this.check("puzzle");
  }
}

// ============================ Timer ============================
function makeTimer(timeEl, toggleBtn, onChange) {
  let secs = 0, id = null, running = false;
  const fmt = (s) => `${(s / 60) | 0}:${String(s % 60).padStart(2, "0")}`;
  function paint() {
    timeEl.textContent = fmt(secs);
    if (toggleBtn) {
      toggleBtn.innerHTML = running ? ICON.pause : ICON.play;
      toggleBtn.title = running ? "Pause" : "Play";
    }
  }
  const api = {
    get secs() { return secs; },
    get running() { return running; },
    set(s) { secs = s | 0; paint(); },
    start() { if (id) return; running = true; timeEl.classList.remove("done"); id = setInterval(() => { secs++; paint(); onChange && onChange(); }, 1000); paint(); },
    pause() { clearInterval(id); id = null; running = false; paint(); },
    toggle() { running ? this.pause() : this.start(); onChange && onChange(); },
    reset() { this.pause(); secs = 0; timeEl.classList.remove("done"); paint(); onChange && onChange(); },
    done() { this.pause(); timeEl.classList.add("done"); },
  };
  paint();
  return api;
}

// ========================= UI helpers =========================
// Dropdown menus: click to open, click-away / Esc to close.
function wireMenus(onAction, onToggle) {
  const menus = [...document.querySelectorAll(".menu")];
  const closeAll = (except) => menus.forEach((m) => { if (m !== except) m.classList.remove("open"); });
  menus.forEach((menu) => {
    const btn = menu.querySelector(".menu__btn");
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const willOpen = !menu.classList.contains("open");
      closeAll(menu);
      menu.classList.toggle("open", willOpen);
    });
    menu.querySelectorAll(".menu__item").forEach((item) => {
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.remove("open");
        if (item.dataset.toggle) onToggle(item.dataset.toggle);
        else if (item.dataset.act) onAction(item.dataset.act);
      });
    });
  });
  document.addEventListener("click", () => closeAll(null));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAll(null); });
}

// Modal confirm -> Promise<boolean>
function showConfirm(message) {
  return new Promise((resolve) => {
    const ov = document.createElement("div");
    ov.className = "modal";
    ov.innerHTML = `
      <div class="modal__box" role="dialog" aria-modal="true">
        <p class="modal__msg">${message}</p>
        <div class="modal__row">
          <button class="pill modal__cancel">Cancel</button>
          <button class="pill pill--solid modal__ok">Yes, do it</button>
        </div>
      </div>`;
    document.body.appendChild(ov);
    const done = (v) => { ov.remove(); document.removeEventListener("keydown", onKey); resolve(v); };
    const onKey = (e) => { if (e.key === "Escape") done(false); if (e.key === "Enter") done(true); };
    ov.querySelector(".modal__cancel").onclick = () => done(false);
    ov.querySelector(".modal__ok").onclick = () => done(true);
    ov.addEventListener("click", (e) => { if (e.target === ov) done(false); });
    document.addEventListener("keydown", onKey);
    ov.querySelector(".modal__ok").focus();
  });
}

function showInfo(html) {
  const ov = document.createElement("div");
  ov.className = "modal";
  ov.innerHTML = `
    <div class="modal__box" role="dialog" aria-modal="true">
      ${html}
      <div class="modal__row"><button class="pill pill--solid modal__ok">Got it</button></div>
    </div>`;
  document.body.appendChild(ov);
  const close = () => ov.remove();
  ov.querySelector(".modal__ok").onclick = close;
  ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
}

// Result banner (solved / not-quite) with a single call-to-action button.
function showResult({ title, msg, cta }) {
  const ov = document.createElement("div");
  ov.className = "modal";
  ov.innerHTML = `
    <div class="modal__box modal__box--center" role="dialog" aria-modal="true">
      <h3 class="modal__title">${title}</h3>
      <p class="modal__msg">${msg}</p>
      <div class="modal__row modal__row--center"><button class="pill pill--solid modal__ok">${cta}</button></div>
    </div>`;
  document.body.appendChild(ov);
  const close = () => { ov.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape" || e.key === "Enter") close(); };
  ov.querySelector(".modal__ok").onclick = close;
  ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
  document.addEventListener("keydown", onKey);
  ov.querySelector(".modal__ok").focus();
}

// Archive ("Older Issues"): list published issues, newest first; pick to open.
function showArchive(index, currentId, onPick) {
  const rows = index.map((e) => `
    <button class="issue-row${e.id === currentId ? " issue-row--current" : ""}" data-id="${e.id}">
      <span class="issue-row__no">No. ${e.issue}</span>
      <span class="issue-row__date">${longDate(e.date)}</span>
      ${e.id === currentId ? '<span class="issue-row__tag">Today</span>' : ""}
    </button>`).join("");
  const ov = document.createElement("div");
  ov.className = "modal";
  ov.innerHTML = `
    <div class="modal__box modal__box--archive" role="dialog" aria-modal="true">
      <h3 class="modal__title">Older Issues</h3>
      <div class="issue-list">${rows}</div>
      <div class="modal__row modal__row--center"><button class="pill modal__ok">Close</button></div>
    </div>`;
  document.body.appendChild(ov);
  const close = () => ov.remove();
  ov.querySelector(".modal__ok").onclick = close;
  ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
  ov.querySelectorAll(".issue-row").forEach((btn) =>
    btn.addEventListener("click", () => { close(); onPick(btn.dataset.id); }));
}

// Lightweight self-contained confetti burst (no dependency).
function confettiBurst() {
  const canvas = document.createElement("canvas");
  // Explicit CSS size (viewport) with a dpr-scaled backing store so it renders
  // correctly on retina/high-DPI screens.
  canvas.style.cssText =
    "position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:9999";
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.floor(innerWidth * dpr);
  canvas.height = Math.floor(innerHeight * dpr);
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  document.body.appendChild(canvas);

  const colors = ["#f2c94c", "#2a3b74", "#8f2b1f", "#2c5233", "#1a1712", "#d9cfba"];
  const make = (originX) => Array.from({ length: 90 }, () => ({
    x: originX, y: innerHeight + 10,
    vx: (Math.random() - 0.5) * 9,
    vy: -(12 + Math.random() * 9),
    g: 0.28 + Math.random() * 0.1,
    size: 5 + Math.random() * 7,
    rot: Math.random() * Math.PI, vr: (Math.random() - 0.5) * 0.35,
    color: colors[(Math.random() * colors.length) | 0],
    life: 1,
  }));
  // two cannons from the bottom corners
  const parts = make(innerWidth * 0.15).concat(make(innerWidth * 0.85));
  const DURATION = 2600;
  const start = performance.now();
  (function frame(t) {
    const elapsed = t - start;
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const p of parts) {
      p.vy += p.g; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
      if (elapsed > DURATION * 0.55) p.life -= 0.018;
      ctx.save();
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
      ctx.restore();
    }
    if (elapsed < DURATION) requestAnimationFrame(frame);
    else canvas.remove();
  })(start);
}


// Actions that touch the whole puzzle need an "are you sure?" first.
const CONFIRM = {
  "check:puzzle": "Check the whole puzzle?",
  "reveal:puzzle": "Reveal the entire solution? This fills in every answer.",
  "clear:puzzle": "Clear every square? Your progress will be erased.",
  "clear:puzzle+timer": "Clear every square and reset the timer to zero?",
};

// Current issue's live objects; menus/toolbar reference these via S.
const S = { puz: null, timer: null, persist: () => {} };

function updateAutocheckUI() {
  document.querySelectorAll("[data-autocheck-ind]").forEach((el) =>
    el.classList.toggle("on", S.puz && S.puz.autocheck));
}

// Build the page for one issue (fresh grid, clues, timer, saved progress).
function mountIssue(data) {
  if (S.timer) S.timer.pause();

  document.getElementById("puzzle-title").textContent = data.title || "The Daily Crossword";
  document.getElementById("byline").textContent = `Constructed by ${data.author || "The Gazette"}`;
  document.getElementById("issue-no").textContent = `VOL. I . . . No. ${data.issue ?? 1}`;
  document.getElementById("dateline").textContent = data.date ? longDate(data.date) : "";

  const STORE_KEY = `tdc:${data.id || "sample"}`;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(STORE_KEY)); } catch {}

  const puz = new Puzzle(data);
  puz.render();

  const timer = makeTimer(
    document.getElementById("timer"),
    document.getElementById("timer-toggle"),
    () => persist()
  );

  if (saved) {
    puz.autocheck = !!saved.autocheck;
    puz.restoreEntries(saved.entries);
    if (typeof saved.secs === "number") timer.set(saved.secs);
    puz.solved = !!saved.solved;
  }

  function persist() {
    const state = puz.serialize();
    state.secs = timer.secs;
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch {}
  }
  puz.onChange = persist;
  puz.onSolved = () => {
    timer.done();
    persist();
    confettiBurst();
    const t = `${(timer.secs / 60) | 0}:${String(timer.secs % 60).padStart(2, "0")}`;
    showResult({
      title: "Solved!",
      msg: `You finished ${data.title} in ${t}. Nicely done.<br><br>Come back tomorrow for a new midi crossword.`,
      cta: "Hooray",
    });
  };
  puz.onIncomplete = (n) => {
    showResult({
      title: "Not quite…",
      msg: `The grid is full, but ${n === 1 ? "1 word is" : n + " words are"} incorrect.`,
      cta: "Keep trying",
    });
  };

  if (puz.solved) timer.done();
  else timer.start();

  S.puz = puz;
  S.timer = timer;
  S.persist = persist;
  updateAutocheckUI();
  if (puz.autocheck) puz.check("puzzle");
}

async function main() {
  document.getElementById("settings-btn").innerHTML = ICON.gear;
  document.getElementById("timer-reset").innerHTML = ICON.reset;
  document.getElementById("year").textContent = new Date().getFullYear();

  // Pick the newest published issue not in the future.
  let index;
  try {
    index = await fetchJSON("data/index.json");
  } catch (err) {
    document.getElementById("grid").textContent = "Today's puzzle could not be loaded.";
    console.error(err);
    return;
  }
  index.sort((a, b) => (a.date < b.date ? 1 : -1)); // newest first
  const today = todayISO();
  const current = index.find((e) => e.date <= today) || index[0];

  try {
    mountIssue(await fetchJSON(`data/${current.id}.json`));
  } catch (err) {
    document.getElementById("grid").textContent = "Today's puzzle could not be loaded.";
    console.error(err);
    return;
  }

  // Toolbar controls act on whichever issue is currently mounted.
  document.getElementById("timer-toggle").addEventListener("click", () => S.timer.toggle());
  document.getElementById("timer-reset").addEventListener("click", () => S.timer.reset());
  document.getElementById("settings-btn").addEventListener("click", () => {
    showInfo(`<h3 class="modal__title">How to play</h3>
      <p class="modal__msg" style="text-align:left">
        Click a square and type. Click again (or press space) to switch between
        Across and Down. Use <b>Check</b> to test letters, <b>Reveal</b> to give up
        a letter, and <b>Clear</b> to wipe squares. Turn on <b>Autocheck</b> to be
        told immediately when a letter is wrong. Your progress and time are saved
        automatically.</p>`);
  });

  let currentId = current.id;
  document.getElementById("archive-btn").addEventListener("click", () => {
    showArchive(index, currentId, async (id) => {
      try {
        mountIssue(await fetchJSON(`data/${id}.json`));
        currentId = id;
      } catch (err) { console.error(err); }
    });
  });

  wireMenus(
    async (act) => {
      if (CONFIRM[act]) {
        const ok = await showConfirm(CONFIRM[act]);
        if (!ok) return;
      }
      const [op, scope] = act.split(":");
      if (op === "check") S.puz.check(scope);
      else if (op === "reveal") S.puz.reveal(scope);
      else if (op === "clear") {
        if (scope === "puzzle+timer") { S.puz.clear("puzzle"); S.timer.reset(); }
        else S.puz.clear(scope);
        if (!S.puz.solved) S.timer.start();
      }
    },
    (toggle) => {
      if (toggle === "autocheck") {
        S.puz.setAutocheck(!S.puz.autocheck);
        updateAutocheckUI();
        S.persist();
      }
    }
  );
}

main();
