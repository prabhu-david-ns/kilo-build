# Spec 03 — Terminal Animation Prep: Game of Life in Python

## Goal

Build a Conway's Game of Life animation in dependency-free Python that renders entirely through VT100 escape sequences (no curses, no third-party libraries). This applies the terminal primitives studied in specs 01–02 (screen clearing, cursor control, raw output) to a real-time full-screen animation — the same rendering loop a terminal editor will need.

## Ground Rules

**No prior knowledge about terminal animation is baked into this spec.** The implementer MUST research every escape sequence, buffering pattern, and pacing technique via web search and cite the original documentation. Nothing here is assumed known — screen clearing, cursor movement, and double-buffering must all be re-derived and cited.

## Requirements

1. Write `prep/game-of-life.py` — a Conway's Game of Life simulation on a terminal grid:
   - Research: What are the exact rules of Conway's Game of Life? (birth/survival/death conditions)
   - Research: How do terminal programs clear the screen and reposition the cursor between frames? What escape sequences do they use, and what are the differences between the erase modes?
   - Implement a fixed-size grid (e.g. 20×20) rendered as live/dead cells, with a visible animated simulation (e.g. a glider pattern) that evolves frame by frame.
2. Grid data structure:
   - Research: How do you map 2D (row, col) coordinates to a 1D linear array? How do terminal games handle coordinates that go out of bounds (edge wrapping vs clipping)? What are the tradeoffs?
   - Implement the grid as a linear array with an index mapping function, and handle out-of-bounds coordinates explicitly.
3. Double-buffered rendering:
   - Research: Why do terminal animations flicker when writing directly? What is double-buffering, and how does it apply to a terminal (as opposed to a GPU)?
   - Implement the simulation with two alternating state buffers, and render the screen by composing the full frame before writing it.
4. Frame pacing:
   - Research: How do terminal animations control frame rate without a graphics loop? What functions do C/Python use to sleep between frames?
   - Implement a steady frame delay so the animation is watchable.
5. Reference Format:
   - Every escape sequence, algorithm, and technique MUST have an inline comment citing its source (URL, man page section, or spec document).
   - Create/update `prep/README.md` (or a bibliography section) listing all sources used for this spec.

## Acceptance Criteria

- `python3 prep/game-of-life.py` runs in a terminal and shows a live, evolving Game of Life animation.
- The screen is cleared/redrawn per frame via escape sequences — no external terminal control library is used.
- The simulation is correct: cells follow the standard Game of Life rules (verify a known pattern like a glider evolves as expected).
- No flicker from partial writes: each frame is composed in memory before being written out.
- The script's header and each escape sequence have source citations.
- The simulation exits cleanly (Ctrl-C or a defined end condition) and restores the terminal state (cursor visibility, screen) if it changed anything.

## Context Limits

The implementer MUST NOT:
- See the original `source/` repo
- See other specs beyond this one
- See `explore/CONTENT_ANGLES.md`
- Use any third-party package (curses, blessed, rich, etc.) — stdlib only
- Assume any behavior is known without researching it

The implementer MUST:
- Use web search to research every technique (escape sequences, double buffering, grid wrapping, frame pacing) before using it
- Cite source URL, man page section, or spec document for every technique
- Create a bibliography of all sources in `prep/README.md`
- Follow the existing `prep/asciinema.md` conventions for demo pacing (pause-based pacing — no `tty.setraw` + `readline` hangs, which break under tmux)

## Notes

- This is the "put the learnings to use" spec: it exercises screen clearing (2J/3J/H), cursor control, and full-frame writes — the same primitives the editor will need. Keep the implementation focused and readable.
