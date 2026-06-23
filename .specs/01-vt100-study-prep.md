# Spec 01 — VT100 Study Prep (Python Scripts)

## Goal

Create a `prep/` directory in the build repo containing standalone Python scripts that study the VT100 escape sequences and terminal facilities needed to build a terminal text editor. These scripts are exploratory — they help us understand the primitives before writing C code.

## Requirements

1. Create `prep/` in the build repo root with an empty `__init__.py` and a `README.md` briefly documenting what each script does.
2. Write `prep/clear-screen.py` — a script that demonstrates:
   - Clearing the entire screen (`\x1b[2J`)
   - Moving cursor to home position (`\x1b[H`)
   - Clearing from cursor to end of screen (`\x1b[J`)
   - Each operation pauses briefly (`time.sleep(0.5)`) so the effect is visible
3. Write `prep/viewport.py` — a script that:
   - Queries terminal cursor position via `\x1b[6n` and reads the response
   - Gets terminal window size via `shutil.get_terminal_size()` (Python stdlib)
   - Prints formatted terminal dimensions (rows × cols)
   - Attempts the Kilo-style cursor query fallback: moves cursor to bottom-right via `\x1b[999C\x1b[999B`, queries with `\x1b[6n`, restores cursor
4. Write `prep/cursor-move.py` — a script that demonstrates:
   - Moving to specific row/col via `\x1b[row;colH`
   - Relative cursor movement: up (`\x1b[A`), down (`\x1b[B`), forward (`\x1b[C`), back (`\x1b[D`)
   - Drawing a simple shape (e.g., a box or cross) using cursor positioning + printable characters
5. Write `prep/colors.py` — a script that displays:
   - All 8 standard ANSI foreground colors on a dark background
   - All 8 standard ANSI background colors
   - A sample of 256-color mode (`\x1b[38;5;Nm`) showing colors 0–255 in a grid
   - Each color labeled with its numeric code
6. Write `prep/terminal-info.py` — a single script that prints a summary of the current terminal's capabilities including:
   - Window size (rows, cols)
   - Whether stdin is a TTY (`os.isatty(0)`)
   - Whether stdout is a TTY (`os.isatty(1)`)
   - TERM environment variable value
   - Whether `\x1b[6n` cursor position query responds correctly (detected via timeout)
7. All scripts must handle terminal restoration: save `stty` state before raw mode and restore on exit (use `atexit` or `try/finally`).
8. All scripts must include a `if __name__ == '__main__': main()` entry point.

## Acceptance Criteria

- Running `python3 prep/clear-screen.py` clears the screen, moves cursor home, and pauses between each operation.
- Running `python3 prep/viewport.py` prints terminal dimensions and successfully queries cursor position via escape sequence.
- Running `python3 prep/cursor-move.py` draws a visible shape on screen using cursor positioning.
- Running `python3 prep/colors.py` displays a labeled color grid without flickering.
- Running `python3 prep/terminal-info.py` prints terminal details without crashing.
- All scripts exit cleanly with terminal restored to its original state.

## Context Limits

The implementer MUST NOT:
- See the original `source/` repo (antirez/kilo)
- See other specs beyond this one
- See `explore/CONTENT_ANGLES.md`

The implementer MAY:
- Use Python stdlib only (no third-party packages)
- Use POSIX `stty` command as reference
- Reference VT100/ANSI escape sequence documentation (man page, Wikipedia, etc.)
- Create new scripts in `prep/` as needed beyond the listed ones
