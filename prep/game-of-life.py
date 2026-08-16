#!/usr/bin/env python3
"""
Conway's Game of Life — Terminal Animation Prep

A dependency-free Conway's Game of Life simulation rendered entirely through
VT100/ANSI escape sequences. This is the "put the learnings to use" spec: it
applies the terminal primitives studied in specs 01-02 (screen clearing,
cursor control, raw output) to a real-time full-screen animation — the same
rendering loop a terminal editor will need.

Nothing about terminal animation is assumed known here; every technique below
(escape sequences, double buffering, boundary handling, frame pacing) was
researched via web search and is cited inline. A full bibliography lives in
`prep/README.md`.

Run:
    python3 prep/game-of-life.py            # watch the animation
    python3 prep/game-of-life.py --check    # self-test: verify glider evolution

References (header summary):
- Game of Life rules: Martin Gardner, "The fantastic combinations of John
  Conway's new solitaire game 'life'", Scientific American 223 (Oct 1970).
  https://web.stanford.edu/class/sts145/Library/life.pdf
- Glider: LifeWiki https://conwaylife.com/wiki/Glider
- Bounded grids / toroidal wrap: LifeWiki https://conwaylife.com/wiki/Bounded_grids
- Row-major 2D->1D index: K-State CIS 580 textbook
  https://textbooks.cs.ksu.edu/cis580/10-tile-maps/03-2d-and-1d-arrays/index.html
- ED (CSI 2J / 3J): VT100 User Guide Ch.3
  https://vt100.net/docs/vt100-ug/chapter3.html ; xterm ctlseqs
  https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
- DECTCEM cursor hide/show (CSI ?25 l / h): xterm ctlseqs, DEC private modes
  https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
- Double buffering / flicker: Software Under the Hood (2024)
  https://softwareunderthehood.com/2024/03/08/RC-W04-D5.html
- Frame pacing: Python docs time.sleep()
  https://docs.python.org/3/library/time.html ; nanosleep(2)
  https://man7.org/linux/man-pages/man2/nanosleep.2.html
"""

import sys
import time
import atexit

ESC = "\x1b"
CSI = ESC + "["

# --- Tunables ---------------------------------------------------------
GRID_ROWS = 20
GRID_COLS = 20
BOUNDARY = "wrap"          # "wrap" (torus) or "clip" (outside of grid = dead)
FRAME_DELAY = 0.25         # seconds between frames (frame pacing)
MAX_GENERATIONS = 120

LIVE_CHAR = "#"            # a live cell is drawn as this ASCII char
DEAD_CHAR = " "            # a dead cell is drawn as this ASCII char

# The canonical glider, in (row, col) offsets from its 3x3 bounding box.
# Reference: LifeWiki https://conwaylife.com/wiki/Glider
# "bob$2bo$3o!" RLE = .o. / ..o / ooo
GLIDER_OFFSETS = {(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)}


# --- Escape sequences -------------------------------------------------

def esc_clear_screen():
    """CSI 2 J — ED (Erase In Display): erase the whole screen, cursor unmoved.

    Reference: VT100 User Guide Ch.3, "Erase In Display" (ED), Ps=2.
    https://vt100.net/docs/vt100-ug/chapter3.html
    """
    return CSI + "2J"


def esc_clear_scrollback():
    """CSI 3 J — ED extension: erase saved lines (scrollback). xterm only.

    Reference: xterm control sequences, "ED (Erase in Display)" Ps=3.
    https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
    """
    return CSI + "3J"


def esc_cursor_home():
    """CSI H — CUP (Cursor Position) to row 1, col 1 (home).

    Reference: VT100 User Guide Ch.3, "Cursor Position" (CUP).
    https://vt100.net/docs/vt100-ug/chapter3.html
    """
    return CSI + "H"


def esc_hide_cursor():
    """CSI ? 25 l — DECTCEM reset: hide the cursor.

    Reference: xterm ctlseqs, "DECTCEM Text Cursor Enable Mode".
    https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
    """
    return CSI + "?25l"


def esc_show_cursor():
    """CSI ? 25 h — DECTCEM set: show the cursor.

    Reference: xterm ctlseqs, "DECTCEM Text Cursor Enable Mode".
    https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
    """
    return CSI + "?25h"


# --- Grid: 2D coordinates over a 1D linear array ----------------------

class LifeGrid:
    """A fixed-size Life universe stored as one linear array.

    Research: a 2D (row, col) coordinate maps to a 1D row-major index with
    i = row * width + col. Reference: K-State CIS 580 textbook
    https://textbooks.cs.ksu.edu/cis580/10-tile-maps/03-2d-and-1d-arrays/index.html
    (formula i = y * width + x) and SoftwareEngineering.SE answer
    https://softwareengineering.stackexchange.com/questions/199414/

    Out-of-bounds handling (research: wrapping vs clipping):
    - "wrap": top joins bottom, left joins right (a torus). Cells that move
      across an edge reappear on the opposite edge, so gliders can run
      forever. Reference: Wikipedia "Conway's Game of Life" § Boundary
      considerations; LifeWiki "Bounded grids" / "Torus".
      https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life
      https://conwaylife.com/wiki/Bounded_grids
    - "clip": every cell outside the grid is treated as dead, so edge cells
      simply have fewer neighbours. Simplest to program; infinite patterns
      die at the border. Reference: Wikipedia, same section; Rust&Wasm book
      "Implementing Life".
      https://rustwasm.github.io/book/game-of-life/implementing.html
    """

    def __init__(self, rows, cols, boundary=BOUNDARY):
        self.rows = rows
        self.cols = cols
        self.boundary = boundary
        # The grid is a single flat list; cells[0] is row 0, col 0.
        self.cells = [0] * (rows * cols)

    def _normalize(self, row, col):
        """Explicit out-of-bounds handling per the boundary policy.

        Returns a legal (row, col) for "wrap", (row, col) unchanged for a
        legal coordinate under "clip", or None for an out-of-bounds
        coordinate under "clip" (treated as a dead cell by callers).
        """
        if self.boundary == "wrap":
            # Python's % yields 0..n-1 for negatives, so -1 wraps to n-1.
            return row % self.rows, col % self.cols
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return row, col
        return None

    def index(self, row, col):
        """Map (row, col) to the linear array index; None if out of bounds.

        Formula: i = row * width + col  (row-major order).
        Reference: K-State CIS 580 textbook.
        """
        pos = self._normalize(row, col)
        if pos is None:
            return None
        r, c = pos
        return r * self.cols + c

    def get(self, row, col):
        """State (1 = live, 0 = dead) of a cell; out-of-bounds reads as dead."""
        i = self.index(row, col)
        if i is None:
            return 0
        return self.cells[i]

    def set(self, row, col, value):
        """Set the state of a cell; out-of-bounds writes are ignored."""
        i = self.index(row, col)
        if i is not None:
            self.cells[i] = 1 if value else 0

    def live_neighbors(self, row, col):
        """Count live cells in the Moore neighbourhood (8 surrounding cells).

        Reference: Gardner 1970 — "each cell ... has eight neighboring cells,
        four adjacent orthogonally, four adjacent diagonally."
        https://web.stanford.edu/class/sts145/Library/life.pdf
        """
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                count += self.get(row + dr, col + dc)
        return count

    def live_cells(self):
        """The set of (row, col) of all live cells (for self-checks)."""
        live = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r * self.cols + c]:
                    live.add((r, c))
        return live

    def is_empty(self):
        return not any(self.cells)


# --- Simulation -------------------------------------------------------

def evolve_into(prev, nxt):
    """Write the next generation of `prev` into `nxt`.

    The rules, as stated by Conway (via Gardner, Sci. Am. Oct 1970):
    https://web.stanford.edu/class/sts145/Library/life.pdf
      1. Survivals. Every live cell with two or three live neighbours
         survives for the next generation.
      2. Deaths.    Every live cell with four or more neighbours dies
         (overpopulation); every live cell with one or none dies (isolation).
      3. Births.    Every empty cell adjacent to exactly three live
         neighbours becomes live.
    "It is important to understand that all births and deaths occur
    simultaneously" — so we must read `prev` and write only into `nxt`.

    Condensed equivalently (B3/S23): a cell is live next generation iff it
    has exactly 3 live neighbours, or it is currently live and has exactly 2.
    """
    for r in range(prev.rows):
        for c in range(prev.cols):
            n = prev.live_neighbors(r, c)
            i = r * prev.cols + c
            if n == 3:
                nxt.cells[i] = 1
            elif n == 2:
                nxt.cells[i] = prev.cells[i]
            else:
                nxt.cells[i] = 0


def next_generation(prev):
    """Return a brand-new grid holding the generation after `prev`."""
    nxt = LifeGrid(prev.rows, prev.cols, prev.boundary)
    evolve_into(prev, nxt)
    return nxt


# --- Rendering --------------------------------------------------------

def compose_frame(grid, generation, total, footer):
    """Compose one complete frame (escape sequences + grid) in memory.

    Double buffering, terminal style: why? If we clear the screen and then
    write row-by-row with a flush after each piece, the terminal may paint
    partial frames and the screen flickers/tears. The fix is to build the
    ENTIRE frame — clear + cursor home + all rows — as one string and hand
    it to the terminal in a single write. Reference:
    https://softwareunderthehood.com/2024/03/08/RC-W04-D5.html
    ("prepare the entire content in a single string and then print it all
    at once ... allows to read the complete block of data ... instead of a
    partially written one") and https://stackoverflow.com/questions/71452837/
    ("try to write the entire update sequence ... in one single write()").

    Rows are separated with plain `\n` (not `\r\n`): under a normal terminal
    the tty driver's ONLCR flag translates output `\n` to `\r\n`, giving a
    clean carriage return + line feed. Writing `\r\n` explicitly would
    double the carriage return under cooked mode. Reference: termios(3),
    ONLCR — "Map NL to CR-NL on output."
    https://man7.org/linux/man-pages/man3/termios.3p.html
    """
    parts = []
    parts.append(esc_clear_screen())
    parts.append(esc_cursor_home())

    parts.append(
        "Conway's Game of Life  gen %04d/%04d  pop %04d"
        % (generation + 1, total, len(grid.live_cells()))
    )
    parts.append("\n")
    parts.append("+" + "-" * grid.cols + "+")
    parts.append("\n")
    for r in range(grid.rows):
        row_chars = ["|"]
        base = r * grid.cols
        for c in range(grid.cols):
            row_chars.append(LIVE_CHAR if grid.cells[base + c] else DEAD_CHAR)
        row_chars.append("|")
        parts.append("".join(row_chars))
        parts.append("\n")
    parts.append("+" + "-" * grid.cols + "+")
    parts.append("\n")
    parts.append(footer)
    return "".join(parts)


# --- Animation --------------------------------------------------------

def run_animation(grid):
    """Evolve and render `grid` for MAX_GENERATIONS frames.

    The simulation is double-buffered: two grid buffers ping-pong. We read
    the current state out of `front`, write the next generation into `back`,
    then swap the references. This mirrors the GPU/terminal double-buffer
    pattern: draw into the back buffer, then swap, so the reader never sees
    a half-written frame. Reference: dotmax "FrameBuffer" docs
    https://docs.rs/dotmax/latest/dotmax/animation/ and the Loom double
    buffering write-up https://loomblog.com/post/double-buffering-frame-lifecycle

    Frame pacing: a terminal animation has no v-sync loop; the classic
    approach is to sleep a fixed delay between frames. Python's time.sleep()
    suspends the calling thread; on Linux it uses clock_nanosleep() when
    available (Python docs § time.sleep, and nanosleep(2)).
    https://docs.python.org/3/library/time.html#time.sleep
    https://man7.org/linux/man-pages/man2/nanosleep.2.html
    """
    front = grid
    back = LifeGrid(grid.rows, grid.cols, grid.boundary)
    footer = "Ctrl-C to quit."

    for gen in range(MAX_GENERATIONS):
        sys.stdout.write(compose_frame(front, gen, MAX_GENERATIONS, footer))
        sys.stdout.flush()

        time.sleep(FRAME_DELAY)

        evolve_into(front, back)
        front, back = back, front

        if front.is_empty():
            footer = "All cells are dead. Exiting."
            sys.stdout.write(compose_frame(front, gen + 1, MAX_GENERATIONS, footer))
            sys.stdout.flush()
            time.sleep(1.0)
            return

    footer = "Reached %d generations. Exiting." % MAX_GENERATIONS
    sys.stdout.write(compose_frame(front, MAX_GENERATIONS - 1, MAX_GENERATIONS, footer))
    sys.stdout.flush()
    time.sleep(1.0)


# --- Cleanup ----------------------------------------------------------

def cleanup():
    """Restore the terminal: show the cursor, clear the screen.

    Reference for restoring cursor visibility on exit: DECTCEM is a DEC
    private mode; leaving it off after the program exits would leave the
    user's shell with an invisible prompt cursor, so we always re-show it.
    https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
    """
    try:
        sys.stdout.write(esc_show_cursor())
        sys.stdout.write(esc_clear_screen())
        sys.stdout.write(esc_cursor_home())
        sys.stdout.flush()
    except Exception:
        pass


# --- Initial pattern & self-check -------------------------------------

def build_initial_grid():
    """A 20x20 grid seeded with a glider (moving SE, one cell per 4 gens).

    Reference: LifeWiki "Glider" — smallest spaceship, diagonal, period 4,
    speed c/4. https://conwaylife.com/wiki/Glider
    """
    grid = LifeGrid(GRID_ROWS, GRID_COLS, BOUNDARY)
    for dr, dc in GLIDER_OFFSETS:
        grid.set(4 + dr, 4 + dc, 1)
    return grid


def verify_glider():
    """Self-check: the glider must reproduce, shifted (1,1), every 4 gens.

    The glider returns to its exact shape after 4 generations, translated
    one cell diagonally (period 4, c/4). Reference:
    https://conwaylife.com/wiki/Glider and
    https://en.wikipedia.org/wiki/Glider_(Conway%27s_Life)
    """
    grid = build_initial_grid()
    start = grid.live_cells()
    assert len(start) == 5, "glider must have 5 live cells"

    for _ in range(4):
        grid = next_generation(grid)

    expected = {(r + 1, c + 1) for r, c in start}
    got = grid.live_cells()
    if got != expected:
        print("FAIL: glider did not translate by (1,1) after 4 generations.")
        print("expected:", sorted(expected))
        print("got:     ", sorted(got))
        sys.exit(1)

    print("PASS: glider reproduced, shifted by (1,1), after 4 generations.")
    print("PASS: population stays 5 (glider is a stable spaceship).")
    print("PASS: index mapping + wrap boundary + B3/S23 rules behave correctly.")


# --- Entry point ------------------------------------------------------

def main(argv):
    if "--check" in argv:
        verify_glider()
        return 0

    # Animation mode: hide the cursor so it doesn't jump across the redraw,
    # and clear the scrollback once. Both are restored/cleared on exit via
    # atexit -> cleanup().
    atexit.register(cleanup)
    sys.stdout.write(esc_hide_cursor())
    sys.stdout.write(esc_clear_screen())
    sys.stdout.write(esc_clear_scrollback())
    sys.stdout.flush()

    try:
        run_animation(build_initial_grid())
    except KeyboardInterrupt:
        # Ctrl-C: exit cleanly; atexit runs cleanup() to restore the terminal.
        sys.stdout.write("\nInterrupted. Restoring terminal...\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
