# Spec 01 — VT100 Study Prep (Research + Python Scripts)

## Goal

Create a `prep/` directory in the build repo containing standalone Python scripts that research and demonstrate the VT100 escape sequences and terminal facilities needed to build a terminal text editor from scratch. These scripts are exploratory — the implementation is driven entirely by web research, not prior knowledge. Every escape sequence and terminal capability used must include a direct reference to its source.

## Ground Rules

**No prior knowledge about VT100/ANSI escape sequences or terminal editing is baked into this spec.** The implementer MUST research every sequence, capability, and pattern via web search and cite the original documentation. Nothing here is assumed known.

## Requirements

1. Create `prep/` in the build repo root with an empty `__init__.py` and a `README.md` that documents what each script does and lists all researched references.

2. Write `prep/clear-screen.py` — a script that researches and demonstrates terminal screen clearing:
   - Research: What escape sequences clear the screen? What's the difference between clearing the whole screen vs clearing from cursor to end?
   - Implement a short demo that shows each clearing method with a visible pause between them
   - The script's header comment MUST cite the exact source(s) used for each sequence (URL, man page section, or spec document)

3. Write `prep/viewport.py` — a script that researches how to discover the terminal's dimensions and cursor position:
   - Research: How does the Device Status Report (`DSR`) sequence work? How do you query cursor position and parse the response? What's the fallback pattern for getting terminal size by moving to an extreme position?
   - Research: What does Python's `shutil.get_terminal_size()` return and how does it work internally?
   - Implement: Report terminal dimensions and demonstrate cursor position query
   - Every sequence and parsing technique MUST include a cited reference

4. Write `prep/cursor-move.py` — a script that researches cursor positioning:
   - Research: What are the absolute positioning (CUP) and relative movement (CUF, CUB, CUU, CUD) escape sequences?
   - Research: What does the `HVP` sequence do differently from `CUP`?
   - Implement: Demo absolute positioning by drawing a simple shape (box or cross) using cursor movement + printable characters
   - Each sequence used MUST have a cited reference in comments

5. Write `prep/colors.py` — a script that researches ANSI color support:
   - Research: What are the SGR parameters for foreground and background colors? What's the difference between 8-color, 16-color, and 256-color modes? How does the `38;5;N` / `48;5;N` extended color sequence work?
   - Implement: Display the 8 standard foreground colors, 8 background colors, and a sample grid of 256-color mode (colors 0–255)
   - Every SGR code used MUST cite the source spec or reference

6. Write `prep/terminal-info.py` — a script that researches how to introspect the terminal:
   - Research: What does `os.isatty()` tell you? How can you test whether the terminal responds to escape sequence queries (e.g., with a timeout)?
   - Research: What does the `TERM` environment variable indicate and what are common values?
   - Implement: Print terminal details — window size, TTY status, TERM value, and a test of escape sequence response detection
   - All research findings MUST include cited references in comments

7. All scripts must handle terminal state management. Research what `stty` raw mode does to the terminal, what state needs to be saved/restored, and implement proper cleanup on exit (use `atexit` or `try/finally`).

8. All scripts must include a `if __name__ == '__main__': main()` entry point.

## Reference Format

In every script, each escape sequence, function, or technique MUST have an inline comment like:

```python
# Reference: https://vt100.net/docs/vt100-ug/chapter3.html#CUP
# Sequence: ESC [ row ; col H — Cursor Position (CUP)
```

A consolidated reference list at the top of each file or in the script's docstring is also acceptable. The `prep/README.md` must include a full bibliography section.

## Acceptance Criteria

- Every script compiles and runs with Python 3 stdlib only (no pip packages)
- Every script includes cited references for all escape sequences used
- `clear-screen.py` visibly demonstrates at least two different clearing sequences with pause between them
- `viewport.py` prints terminal dimensions and demonstrates cursor position query successfully
- `cursor-move.py` draws a visible shape on screen using absolute cursor positioning
- `colors.py` displays a labeled color grid without flickering
- `terminal-info.py` prints terminal details and escape-sequence response test result without crashing
- All scripts exit cleanly with terminal restored to its original state

## Context Limits

The implementer MUST NOT:
- See the original `source/` repo
- See other specs beyond this one
- See `explore/CONTENT_ANGLES.md`
- Use any third-party Python packages
- Assume any escape sequence or terminal behavior is known without researching it

The implementer MUST:
- Use web search to research every VT100/ANSI escape sequence before using it
- Cite the source URL, man page section, or spec document for every sequence and technique
- Include a bibliography in `prep/README.md`
- Create additional research scripts in `prep/` if something interesting comes up during research
