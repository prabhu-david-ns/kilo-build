# VT100 Study Prep

Research scripts for terminal escape sequences and VT100 facilities.

## Scripts

### clear-screen.py
Demonstrates terminal screen clearing escape sequences:
- `CSI 2J` (ED) - Erase in Display (clear entire screen)
- `CSI 0J` (ED) - Erase from cursor to end of screen
- `CSI 1J` (ED) - Erase from start to cursor
- `CSI J` (ED) - Erase from cursor to end (default)

### viewport.py
Reports terminal dimensions and demonstrates cursor position queries:
- Device Status Report (DSR) `CSI 6n` for cursor position
- Fallback using extreme cursor movement to detect boundaries
- `shutil.get_terminal_size()` analysis

### cursor-move.py
Demonstrates cursor positioning escape sequences:
- CUP (Cursor Position) `CSI row ; col H` - absolute positioning
- CUU (Cursor Up) `CSI count A`
- CUD (Cursor Down) `CSI count B`
- CUF (Cursor Forward) `CSI count C`
- CUB (Cursor Back) `CSI count D`
- HVP (Horizontal Vertical Position) `CSI row ; col f`

### colors.py
Demonstrates ANSI color support:
- SGR (Select Graphic Rendition) `CSI ... m`
- 8 standard foreground/background colors
- 16-color mode (bright variants)
- 256-color extended mode (`38;5;N`, `48;5;N`)

### terminal-info.py
Terminal introspection utilities:
- `os.isatty()` for TTY detection
- `TERM` environment variable values
- Escape sequence response detection with timeout

### game-of-life.py
Conway's Game of Life rendered as a real-time terminal animation — the
"put the learnings to use" spec that exercises the same rendering loop a
terminal editor will need:
- Grid stored as a linear array with the row-major index formula
  `i = row * width + col`, with explicit out-of-bounds handling
  (default: toroidal "wrap" boundary so gliders run forever; "clip" also
  implemented, where cells outside the grid read as dead)
  - Wide 40×20 view box (`GRID_COLS = 40`); live cells drawn as `*`
- Coloured frame via SGR (Select Graphic Rendition): bold bright-cyan
  header, bright-yellow border, bold bright-red live cells ("stars"),
  bright-magenta footer — all reset with `CSI 0 m`
- Double-buffered simulation: two grid buffers ping-pong; the next
  generation is written into the back buffer and the references swap
- Double-buffered output: each frame (clear + cursor home + all rows) is
  composed as a single string and written in one `write()`, so the
  terminal never paints a partial frame
- Frame pacing via `time.sleep(FRAME_DELAY)`; exits after a fixed number
  of generations or on Ctrl-C, restoring the terminal (DECTCEM cursor
  visibility, screen)
- Run `python3 prep/game-of-life.py` to watch, or
  `python3 prep/game-of-life.py --check` to self-verify:
  - the seeded glider reproduces shifted by (1,1) every 4 generations
  - edge logic: wrap seam neighbour counting across the torus edges,
    clip semantics (out-of-bounds reads dead / writes ignored), and a
    glider straddling the bottom-right seam that wraps correctly

Escape sequences used:
- `CSI 2 J` / `CSI 3 J` (ED) - clear screen / clear scrollback
- `CSI H` (CUP) - cursor home
- `CSI ? 25 l` / `CSI ? 25 h` (DECTCEM) - hide / show cursor
- `CSI 1 ; 96 m`, `CSI 93 m`, `CSI 92 m`, `CSI 95 m`, `CSI 0 m` (SGR) -
  header / border / live-cell / footer styling and reset

<<<<<<< HEAD
### tedit (spec 04 — the real editor)

`../tedit.c` + `../Makefile` is the payoff spec: a dependency-free VT100
text/code editor in plain C (gcc `-std=c11`, libc/POSIX only, no curses)
that uses everything studied above. Build with `make`, run `./tedit [FILE]`
(or no argument for an empty buffer).

It applies the prep techniques directly:
- raw mode via termios (`prep/flow.md` §3.3, `man 3 termios`) with an
  `atexit` restore
- `read_key()` byte classification + CSI/SS3 escape parsing
  (`prep/key-classifier.py`, `prep/input-orchestration.py`, `prep/flow.md` §5)
- append-buffer frame composition in a single `write()` (`prep/clear-screen.py`,
  `prep/cursor-move.py`, `prep/game-of-life.py`)
- viewport + per-row display model with tab expansion and vertical/horizontal
  scroll (`prep/viewport.py`, `prep/terminal-info.py`)
- SGR colors and reverse-video status bar (`prep/colors.py`)

Keys: type / arrows / Home-End / PageUp-PageDown / Backspace / Delete /
Enter / Ctrl-S save / Ctrl-F find / Ctrl-Q quit (repeated while dirty).

## Spec 05 sources

Spec 05 rebuilt the editor using **only** this prep/ knowledge — zero external
research. Every technique in `tedit.c` is derived from and cited against one of
these files:

- `prep/flow.md` — raw-mode flag set (cfmakeraw list, §3.3), cooked vs raw
  line discipline (§3.2-3.4), VMIN/VTIME blocking reads (§4.2), key
  classification table (§5.1-5.4), keyboard→display pipeline (§4-6, §9) that
  motivates the canonical-bytes vs rendered-columns row model.
- `prep/key-classifier.py` — printable/Ctrl/ESC classification,
  `CSI_SEQUENCES`/`SS3_SEQUENCES` tables, `_read_csi_sequence` ECMA-48
  param/intermediate/final byte parsing.
- `prep/input-orchestration.py` — NORMAL/ESC/CSI/SS3 input state machine,
  raw-mode `\r\n` output pattern, Ctrl-S/Ctrl-Q/Ctrl-F action routing that the
  editor's key processor mirrors.
- `prep/clear-screen.py` — ED clear-screen `CSI 2J`, CUP `CSI H`, DECAWM
  auto-wrap toggles `CSI ?7l` / `CSI ?7h`.
- `prep/cursor-move.py` — CUP absolute positioning `CSI row;col H` used for
  per-frame cursor placement and the no-trailing-newline frame design.
- `prep/colors.py` — SGR palette: `CSI 30-37m`, `CSI 40-47m`, `CSI 1;30-37m`,
  `CSI 38;5;Nm`, `CSI 0m`; source of every colour the editor emits
  (keywords, types, numbers, strings, comments, matches, status/message bars).
- `prep/game-of-life.py` — single-write frame composition (`compose_frame`),
  DECTCEM cursor hide/show `CSI ?25l` / `CSI ?25h`, bold-bright `1;9xm` style
  form, `cleanup()` restore-on-exit pattern.
- `prep/viewport.py` — TIOCGWINSZ ioctl size query, DSR `CSI 6n` cursor report
  and cursor-clamp fallback that motivate the viewport/scroll math.
- `prep/terminal-info.py` — `os.isatty()` tty detection (the editor refuses to
  run when stdin is not a terminal), DEC private-mode toggles.
- `prep/terminal-viewport-combined.py` — consolidated TIOCGWINSZ query and
  `CSI ?25h/l` / `CSI ?7h/l` private-mode toggles used at startup/exit.

No external URLs, man-page links, or third-party project names appear in
`tedit.c`; the only sources cited are the files above. Techniques extended
beyond what prep/ shows directly (for example the per-row `hl` syntax-array,
multi-line comment state carry, the dirty-quit confirmation, and the
incremental find state) are marked in `tedit.c` as "designed from prep/
primitives" and justified against the prep/ behaviours they build on.
>>>>>>> origin/main

## Bibliography

- VT100 User Guide: https://vt100.net/docs/vt100-ug/
- ECMA-48 Terminal Control Sequences: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
- ANSI escape code (Wikipedia): https://en.wikipedia.org/wiki/ANSI_escape_code
- XTerm Control Sequences: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
- Conway's Game of Life (Wikipedia): https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life
- Martin Gardner, "The fantastic combinations of John Conway's new solitaire
  game 'life'", Scientific American 223 (October 1970): 120-123:
  https://web.stanford.edu/class/sts145/Library/life.pdf
- Glider (LifeWiki): https://conwaylife.com/wiki/Glider
- Glider (Wikipedia): https://en.wikipedia.org/wiki/Glider_(Conway%27s_Life)
- Bounded grids (LifeWiki): https://conwaylife.com/wiki/Bounded_grids
- Torus (LifeWiki): https://conwaylife.com/wiki/Torus
- Golly Help — Bounded Grids: https://golly.sourceforge.io/Help/bounded.html
- Implementing Life (Rust and WebAssembly book): https://rustwasm.github.io/book/game-of-life/implementing.html
- 2D to 1D array indexing (K-State CIS 580): https://textbooks.cs.ksu.edu/cis580/10-tile-maps/03-2d-and-1d-arrays/index.html
- "Two techniques to remove flickering when printing on the terminal" —
  Software Under the Hood (2024): https://softwareunderthehood.com/2024/03/08/RC-W04-D5.html
- How to reduce flicker in terminal re-drawing (Stack Overflow):
  https://stackoverflow.com/questions/71452837/how-to-reduce-flicker-in-terminal-re-drawing
- Python docs — time.sleep(): https://docs.python.org/3/library/time.html#time.sleep
- nanosleep(2) (Linux man page): https://man7.org/linux/man-pages/man2/nanosleep.2.html
- termios(3p) — ONLCR flag (Linux man page): https://man7.org/linux/man-pages/man3/termios.3p.html

## Spec 04 sources (tedit.c)

- termios(3) — tcgetattr/tcsetattr/cfmakeraw, ICANON, ISIG, ECHO, IXON,
  VMIN/VTIME: https://man7.org/linux/man-pages/man3/termios.3.html
- read(2): https://man7.org/linux/man-pages/man2/read.2.html
- write(2): https://man7.org/linux/man-pages/man2/write.2.html
- open(2) / close(2): https://man7.org/linux/man-pages/man2/open.2.html
- ftruncate(2): https://man7.org/linux/man-pages/man2/ftruncate.2.html
- getline(3): https://man7.org/linux/man-pages/man3/getline.3.html
- ioctl_tty(2const) — TIOCGWINSZ window size:
  https://man7.org/linux/man-pages/man2/tiocgwinsz.2const.html
- signal(7) — SIGWINCH, sigaction(2):
  https://man7.org/linux/man-pages/man7/signal.7.html
- TLPI demo_SIGWINCH.c — resize handling pattern:
  https://man7.org/code/tty/demo_SIGWINCH.c.html
- atexit(3): https://man7.org/linux/man-pages/man3/atexit.3.html
- strstr(3): https://man7.org/linux/man-pages/man3/strstr.3.html
- Build Your Own Text Editor (snaptoken/kilo) — raw mode, read_key, escape
  parsing, append buffer, per-row syntax highlighting, quit confirmation,
  incremental search: https://viewsourcecode.org/snaptoken/kilo/
- antirez/kilo — row model, tab expansion, multi-line comment state,
  search match highlighting: https://github.com/antirez/kilo
