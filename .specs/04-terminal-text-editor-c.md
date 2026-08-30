# Spec 04 — A Terminal Text Editor in C

## Goal

Build a dependency-free terminal text/code editor in C (VT100-only, no curses, no ncurses, no third-party libraries) that puts the specs 01–03 prep learnings to work: raw mode input, escape-sequence parsing, append-buffer rendering, viewport awareness, and per-row display state. This is the real editor — the thing the whole prep phase was studying for.

## Ground Rules

**No prior knowledge about terminal editors is baked into this spec.** The prep material in `prep/` (flow.md, key-classifier.py, input-orchestration.py, clear-screen.py, cursor-move.py, colors.py, viewport.py, terminal-info.py) is OUR OWN prior research from specs 01–03 — the implementer MUST read and use it as the primary reference, and MUST re-verify and cite every technique in the output. Anything not covered by prep/ (termios details, editor loop patterns, file I/O conventions) MUST be researched via web search and cited. Nothing is assumed known.

## Requirements

1. **Project skeleton + build with gcc:**
   - Create a `Makefile` in the repo root driving `gcc` (`-std=c11 -Wall -Wextra`, debug-friendly). `make` builds the editor binary (`tedit`), `make clean` removes artifacts.
   - No build-system dependencies (no cabin, no cmake, no meson). No third-party libraries — link only against libc/POSIX.
2. **Raw mode:**
   - Research: What is terminal "raw mode"? Which termios flags disable canonical mode, echo, signals, and flow control? What is the difference between raw and cbreak?
   - Implement raw-mode enable/disable using the termios interface, with guaranteed restore on exit (atexit or equivalent). Cite the man page.
3. **Key reading:**
   - Research: How do interactive terminal programs read keys from a blocking stdin? How are escape sequences for arrow keys, Home/End/PageUp/PageDown/Delete encoded, and how do you disambiguate them from plain ESC?
   - Use `prep/key-classifier.py` and `prep/input-orchestration.py` as prior art. Implement a `read_key()` that returns typed keys: printable chars, Ctrl+letter (Ctrl-Q quit, Ctrl-S save, Ctrl-F find), Enter, Backspace, Delete, arrows, Home/End, PageUp/PageDown.
4. **Screen rendering with an append buffer:**
   - Research: Why do terminal programs flicker when writing many small writes? What is the append-buffer pattern (compose the whole frame in memory, flush once)?
   - Use `prep/clear-screen.py` + `prep/cursor-move.py` prior art. Implement a frame composer that: hides the cursor, moves home, draws every visible row, draws a status bar (reverse video), draws a message bar, restores cursor to the edit position, and flushes with a single `write()`. Reuse the pattern from `prep/colors.py` for SGR (e.g. reverse video, status colors).
5. **Viewport + row model:**
   - Research: How do terminal editors keep a file's canonical content separate from what's displayed (tab expansion, long-line wrapping/horizontal scroll)? How do they query terminal size (ioctl) and handle resize (SIGWINCH)?
   - Use `prep/viewport.py` + `prep/terminal-info.py` prior art. Implement a row model where each file row keeps its canonical bytes and a derived display buffer (tabs expanded to the next tab stop; display columns tracked for cursor math). Implement vertical scroll and horizontal scroll so any row content and any cursor position are reachable.
   - File loading from `argv[1]` (or empty buffer), with per-row insertion/append. Preserve real tabs in the saved file — display expansion must NOT corrupt saved content.
6. **Editing operations:**
   - Insert character at cursor, Backspace (merge with previous row), Delete (merge with next row), Enter (split row), cursor movement within and across rows, and per-row updates after edits.
7. **Status bar + message bar:**
   - Status bar shows: file name, dirty indicator, line:col of cursor, scroll percentage (or equivalent). Message bar shows transient messages (e.g. "saved", "search: ...").
8. **Save + quit safeguard:**
   - Ctrl-S writes the buffer to the file. Ctrl-Q quits; when the buffer is dirty, require a repeat-quit confirmation shown in the message bar.
   - Research: how do minimal terminal editors handle "unsaved changes" without modal dialogs?
9. **Syntax highlighting (C):**
   - Research: how do lightweight editors highlight code without a full lexer — per-row scanning for keywords, numbers, strings, comments? How do multi-line comments carry state between rows?
   - Implement `hl` state per row (indexed by display position), highlight C keywords/numbers/strings/comments, with multi-line comment state propagated across rows. Refinements (search match highlight) must match the search feature below.
10. **Find (Ctrl-F):**
    - Research: how do minimal editors implement a search prompt inline in the message bar, and match highlighting?
    - Implement forward search from the cursor with incremental match highlight, Enter to jump, ESC to cancel.
11. **Reference Format:**
    - Every escape sequence, syscall, and technique MUST have an inline comment citing its source (URL, man page section, or spec document).
    - Extend `prep/README.md` bibliography with all new sources used by this spec.

## Acceptance Criteria

- `make` builds `tedit` with gcc cleanly (no warnings under `-Wall -Wextra`). `ldd tedit` shows only libc (no ncurses).
- `./tedit FILE` opens an existing file, `./tedit` starts with an empty buffer.
- Raw mode is entered on start and the terminal is fully restored on exit (normal quit AND Ctrl-C at any point).
- All listed keys work: typing, arrows, Home/End, PageUp/PageDown, Delete, Backspace, Enter, Ctrl-S save, Ctrl-F find, Ctrl-Q quit (dirty buffer requires repeated Ctrl-Q with a visible message).
- Tabs display expanded but are saved as real tabs. Long lines scroll horizontally without breaking layout.
- Status bar shows filename + dirty flag + line:col; message bar shows transient messages.
- C files get syntax highlighting; multi-line comments spanning rows stay highlighted on both rows.
- Find highlights matches and jumps; ESC cancels cleanly.
- Terminal is left clean after quit (no leftover escape output, cursor visible).
- Runs correctly inside tmux (per `prep/asciinema.md` conventions) — it will be recorded for content.
- The editor is genuinely dependency-free: no external packages, no curses, no third-party includes.

## Context Limits

The implementer MUST NOT:
- See the original `source/` repo
- See other specs beyond this one
- See `explore/CONTENT_ANGLES.md`
- Use any third-party package or curses/ncurses
- Assume any behavior is known without researching it
- Name the editor after any existing public editor project

The implementer MUST:
- Read `prep/` first (it is our own research — flow.md, key-classifier.py, input-orchestration.py, clear-screen.py, cursor-move.py, colors.py, viewport.py, terminal-info.py, asciinema.md)
- Use web search to research every technique not covered by prep/ (termios raw mode, append-buffer rationales, ioctl sizing, per-row syntax highlighting, search state) and cite the source
- Cite source URL, man page section, or spec document for every technique inline
- Extend the `prep/README.md` bibliography
- Keep the whole editor in idiomatic plain C, scoped to stay as small as reasonably possible

## Notes

- This is the payoff spec: everything studied in specs 01–03 (VT100 sequences, keyboard→display flow, viewport math) becomes a real editor. Where prep/ already answers a question, use it — but still verify and cite.
- Keep the editor single-file unless the file grows unwieldy; readability beats ceremony.
- The editor will be recorded under tmux for content, so treat the tmux environment as the recorded truth (see `prep/asciinema.md`).