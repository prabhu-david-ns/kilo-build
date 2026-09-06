# Spec 05 — Rebuild the Editor Using Only Our Prep Knowledge

## Goal

Produce the same terminal text/code editor capability as spec 04 — but derived **exclusively** from the knowledge already captured in `prep/` (the build's own specs 01–03 research). This run performs **zero web research**. Every design decision and every escape sequence must trace back to a `prep/` file.

## Ground Rules

**Strict knowledge budget.** The ONLY permitted knowledge sources are:
- The files in `prep/` (scripts, demos, and `flow.md`)
- This spec (for the feature scope) and `.specs/04-terminal-text-editor-c.md` (read it ONLY for the requirement list — the *what* — never for technique; it contains no answers anyway)
- Your own reasoning and prior programming experience

**No external knowledge of any kind:** no web search, no opening URLs, no man pages beyond what a general C programmer already knows, no reading the original `source/` repo, no reading any previous editor implementation, no browsing git history or remote branches. If a technique is not already demonstrated in `prep/`, you must design it yourself from prep/ primitives — and say so honestly in a comment.

**Directory discipline:** work ONLY inside this build directory. Do NOT list or read anything above it (no `..`, no parent repo contents, no explore/ notes). The knowledge budget is `prep/` + `.specs/` + nothing else.

## Workflow (MANDATORY — follow strictly)

**Never plan the whole editor in your head before writing code. Build in small, verified increments.** After the initial `ls`/`README` orientation, do NOT read prep/ files all at once or think for minutes before acting. Instead:

1. Read ONE prep/ file (or one cluster, e.g. the clear-screen demos) immediately before writing the code it informs.
2. Write or extend code. Run `make` (or the build) right away. Fix errors. Move on.
3. Never go more than a few tool calls without a build or a visible terminal check.
4. Use `printf`/`echo`-based terminal checks inside tmux (like the demo scripts do) to verify behavior incrementally; the tmux session must be created before testing raw-mode code, and `tcsetattr`-style errors mean you're testing outside a tty — create the tmux pane FIRST.
5. It is fine to write the whole editor across many file-append/edit steps. The file does not need to appear in one shot.

A run that spends many minutes reading files or generating without building is FAILING this spec even if the final code is right.

## Requirements

1. **Build:** a `Makefile` driving `gcc -std=c11 -Wall -Wextra` producing the binary `tedit`, plus `make clean`. No build-system dependencies. (Build tooling is not knowledge — this is allowed as-is.)
2. **Raw mode:** study `prep/flow.md` (keyboard → display pipeline, raw mode discussion) and the terminal setup found in prep/ demos. Implement raw-mode enable/disable with guaranteed terminal restore on exit. Cite the prep/ file(s) and section(s) you derived this from.
3. **Key reading:** study `prep/key-classifier.py` and `prep/input-orchestration.py`. Implement a key reader that distinguishes printable characters, Ctrl+letter, Enter, Backspace, Delete, arrows, Home/End, PageUp/PageDown, using the escape-sequence parsing approach those files document.
4. **Rendering:** study `prep/clear-screen.py`, `prep/clear-screen-demo*.py`, `prep/cursor-move.py`, `prep/cursor-move-demo*.py`, `prep/colors.py`, and the frame-composition approach in `prep/game-of-life.py`. Implement a frame composer that: hides the cursor while drawing, moves home, draws every visible row, draws a status bar (reverse video or SGR from `prep/colors.py`), draws a message bar, positions the cursor at the edit point, shows the cursor again, and flushes the whole frame in ONE write. Every sequence you emit MUST be one already demonstrated in prep/ — if prep/ doesn't show it, don't use it; design around prep/'s palette.
5. **Viewport:** study `prep/viewport.py`, `prep/terminal-info.py`, and `prep/terminal-viewport-combined.py`. Implement terminal-size query (the ioctl those files use) and row/column math. Re-query the size at each full refresh so resizes are picked up; vertical and horizontal scroll must keep any cursor position reachable.
6. **Row model:** derive from the display pipeline in `prep/flow.md` and the render math in the viewport/clear/cursor files HOW to represent a file row versus what is drawn on screen. Justify your representation in comments citing the prep/ files that motivated it. Tabs must render as expanded spacing yet be saved back as real tab bytes — the expansion must never corrupt saved content.
7. **Editing:** implement insert character at cursor, Backspace (merge with previous row at row start), Delete (merge with next row at row end), Enter (split row), and cursor movement within/across rows. Structure the key classification per `prep/key-classifier.py` and the orchestration per `prep/input-orchestration.py`.
8. **Status bar + message bar:** as in requirement 4 — filename, dirty indicator, line:col, scroll percentage in the status bar; transient messages in the message bar.
9. **Save + quit:** Ctrl-S writes the buffer to the opened file (new-buffer save is optional but nice). Ctrl-Q quits; when the buffer is dirty, quitting must not silently lose work — design a confirmation that uses ONLY primitives already in your frame composer and prep/ (message bar, key loop, status line). Explain your design in a comment citing the prep/ behaviors it builds on.
10. **Syntax highlighting:** use the SGR color mechanisms from `prep/colors.py` to highlight C keywords, types, numbers, strings, and comments. Design the per-row scanning and multi-line comment state yourself — the ONLY constraint is that the terminal mechanisms you emit (colors, attribute codes) come from prep/. State the prep/ source for every SGR sequence.
11. **Find (Ctrl-F):** incremental forward search driven by the key loop, prompt shown in the message bar (per requirement 4), matches highlighted with SGR from `prep/colors.py`, Enter jumps, ESC cancels and restores. Design the state handling yourself from prep/ primitives.
12. **Citations:** every technique MUST carry an inline comment citing the specific `prep/` file (and function/section) it came from. NO external URLs anywhere — no `https://`, no man-page links, no third-party names. The bibliography in `prep/README.md` (a "Spec 05 sources" section) lists ONLY prep/ files, in the format: `prep/<file> — what it contributed`.

## Acceptance Criteria

- `make` builds `tedit` warning-free under `-std=c11 -Wall -Wextra`; `ldd tedit` shows only libc.
- `./tedit FILE` opens the file; `./tedit` starts empty. Raw mode is entered on start and the terminal is FULLY restored on quit (including Ctrl-C paths).
- Typing, arrows, Home/End, PageUp/PageDown, Delete, Backspace, Enter, Ctrl-S, Ctrl-F, Ctrl-Q all function; dirty quit requires confirmation via the message bar (design is yours).
- Tabs display expanded but save as real `\t` bytes. Long lines scroll horizontally without breaking layout; resize adapts on next refresh.
- Status bar shows filename + dirty + line:col + percent; message bar shows transient messages.
- C files highlight (keywords/types/numbers/strings/comments, multi-line comment state across rows).
- Find highlights matches and jumps; ESC cancels cleanly; terminal left clean after quit.
- **Zero external knowledge:** `grep -rE 'https?://' tedit.c` returns nothing; every citation in tedit.c and the new prep/README.md section references only `prep/` files; no function, structure, or comment names an external project, tutorial, or author.
- Runs correctly inside tmux (per `prep/asciinema.md` conventions) — it will be recorded for content.

## Context Limits

The implementer MUST NOT:
- Do ANY web search or open ANY external URL
- See the original `source/` repo, `explore/` notes, or any content-repo parent content
- Read any previous editor implementation or browse git history/remotes for one (there is none in this working tree)
- Use any escape sequence, attribute, or pattern not demonstrated in prep/
- Even list directory contents above this build directory

The implementer MUST:
- Read `prep/` thoroughly FIRST and treat it as the complete knowledge base
- Cite the specific prep/ file (and section/function) for every technique, inline
- Write "designed from prep/ primitives: <reasoning>" comments where you extend beyond what prep/ shows directly
- Extend `prep/README.md` with a "Spec 05 sources" bibliography listing only prep/ files
- If a required feature genuinely cannot be built from prep/ knowledge alone, implement the closest prep/-supported version and document the gap honestly in a comment — do NOT go research it

## Notes

- The point of this run: a derivation that stands entirely on our own build's research — the honest "we built it from what we learned" artifact for the comparison piece.
- You will notice `.specs/04-*.md` in the same directory; read it ONLY for the feature list, then close it. Its research questions are not answers.
- `prep/README.md` may contain a "Spec 04 sources" section listing external references — IGNORE that section entirely; your citations must never reference anything outside this repo's `prep/`.