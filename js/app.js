// The Daily Cross — client (prototype)
// Loads a puzzle JSON, renders a numbered newspaper grid, and lets you solve it.

const BLOCK = "#";

async function loadPuzzle() {
  // For the daily build this becomes data/<today>.json; the sample ships for now.
  // BASE_URL keeps the path correct if the site is ever served from a sub-path.
  const base = import.meta.env.BASE_URL;
  const res = await fetch(`${base}data/sample.json`);
  if (!res.ok) throw new Error("Could not load puzzle");
  return res.json();
}

// Assign standard crossword numbers and record where each entry starts.
function numberGrid(grid) {
  const n = grid.length;
  const nums = grid.map((row) => row.map(() => 0));
  const acrossStart = {}; // num -> {r,c}
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

// Collect the cell path for an entry starting at (r,c) in a direction.
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
    this.active = null; // {r,c}
    this.inputs = {};   // "r,c" -> input el
    this.cells = {};    // "r,c" -> cell el
    this.clueText = { across: {}, down: {} }; // num -> clue string
    this.onSolved = null;
    this.solved = false;
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
        input.maxLength = 1;
        input.dataset.r = r;
        input.dataset.c = c;
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
    // Start on 1-Across.
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
    // Walk back to the entry start in the active direction, then forward.
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

    // Sync clue list highlight + the clue bar above the grid.
    const start = word[0];
    const startNum = this.nums[start.r][start.c];
    const li = document.querySelector(`.clues__list li[data-num="${startNum}"][data-dir="${this.dir}"]`);
    if (li) li.classList.add("active");

    const bar = document.getElementById("cluebar");
    if (bar) {
      const txt = this.clueText[this.dir][startNum] || "";
      bar.innerHTML = `<span class="num">${startNum}</span><span>${txt}</span>`;
    }
  }

  checkSolved() {
    if (this.solved) return;
    let done = true;
    this.eachWhite((r, c) => {
      if (this.inputs[`${r},${c}`].value !== this.grid[r][c]) done = false;
    });
    if (done) {
      this.solved = true;
      if (this.onSolved) this.onSolved();
    }
  }

  onInput(e, r, c) {
    const v = e.target.value.toUpperCase().replace(/[^A-Z]/g, "");
    e.target.value = v.slice(-1);
    this.cells[`${r},${c}`].classList.remove("cell--correct", "cell--wrong");
    if (e.target.value) this.advance(r, c, 1);
    this.checkSolved();
  }

  advance(r, c, step) {
    const word = this.currentWordCells(r, c);
    const idx = word.findIndex((p) => p.r === r && p.c === c);
    const next = word[idx + step];
    if (next) this.focus(next.r, next.c);
  }

  onKey(e, r, c) {
    const key = e.key;
    if (key === "Backspace") {
      if (!e.target.value) { e.preventDefault(); this.advance(r, c, -1); }
      this.cells[`${r},${c}`].classList.remove("cell--correct", "cell--wrong");
      return;
    }
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
    if (key === " ") { e.preventDefault(); this.toggleDir(); }
  }

  eachWhite(fn) {
    for (let r = 0; r < this.size; r++)
      for (let c = 0; c < this.size; c++)
        if (this.grid[r][c] !== BLOCK) fn(r, c);
  }

  check() {
    this.eachWhite((r, c) => {
      const el = this.inputs[`${r},${c}`];
      const cell = this.cells[`${r},${c}`];
      cell.classList.remove("cell--correct", "cell--wrong");
      if (!el.value) return;
      cell.classList.add(el.value === this.grid[r][c] ? "cell--correct" : "cell--wrong");
    });
  }

  reveal() {
    this.eachWhite((r, c) => {
      this.inputs[`${r},${c}`].value = this.grid[r][c];
      this.cells[`${r},${c}`].classList.add("cell--correct");
      this.cells[`${r},${c}`].classList.remove("cell--wrong");
    });
    this.checkSolved();
  }

  clear() {
    this.eachWhite((r, c) => {
      this.inputs[`${r},${c}`].value = "";
      this.cells[`${r},${c}`].classList.remove("cell--correct", "cell--wrong");
    });
  }
}

function dateline() {
  const d = new Date();
  const opts = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
  document.getElementById("dateline").textContent = d.toLocaleDateString("en-US", opts);
  document.getElementById("year").textContent = d.getFullYear();
}

// Count-up timer, starts on the solver's first keystroke, stops when solved.
function makeTimer(el) {
  let secs = 0, id = null;
  const fmt = (s) => `${String((s / 60) | 0).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  return {
    start() {
      if (id) return;
      id = setInterval(() => { secs += 1; el.textContent = fmt(secs); }, 1000);
    },
    stop() { clearInterval(id); id = null; },
    done() { this.stop(); el.classList.add("done"); },
  };
}

async function main() {
  dateline();
  try {
    const data = await loadPuzzle();
    document.getElementById("puzzle-title").textContent = data.title || "The Daily Crossword";
    document.getElementById("byline").textContent = `Constructed by ${data.author || "the Machine"}`;
    const puz = new Puzzle(data);
    puz.render();

    const timer = makeTimer(document.getElementById("timer"));
    puz.onSolved = () => timer.done();
    document.getElementById("grid").addEventListener("keydown", () => timer.start(), { once: true });

    document.getElementById("check-btn").addEventListener("click", () => puz.check());
    document.getElementById("reveal-btn").addEventListener("click", () => puz.reveal());
    document.getElementById("clear-btn").addEventListener("click", () => puz.clear());
  } catch (err) {
    document.getElementById("grid").textContent = "Today's puzzle could not be loaded.";
    console.error(err);
  }
}

main();
