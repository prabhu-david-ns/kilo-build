# Spec 02 — Keyboard Input to Display Flow (Research + Python Scripts)

## Goal

Research and document the full path of a keypress from physical keyboard to on-screen display in a Linux terminal environment, including the OS input subsystem, terminal emulator, TTY discipline, and the C program's stdin read loop. Document findings in `prep/flow.md` with supporting Python scripts.

## Ground Rules

**No prior knowledge about Linux terminal I/O, keyboard input processing, or the kernel tty subsystem is baked into this spec.** The implementer MUST research every subsystem and pathway via web search and cite the original documentation (kernel docs, man pages, specification documents). Nothing here is assumed known.

## Requirements

1. Create `prep/flow.md` — a comprehensive document describing the keyboard-to-display data flow on Fedora Linux with a standard terminal emulator (GNOME Terminal, Konsole, or xterm). Cover:
   - **Physical keyboard → kernel:** How a key press becomes a scancode, how the kernel input subsystem (evdev) processes it, and how it reaches the terminal emulator via the TTY device
   - **Terminal emulator → TTY:** How the terminal emulator reads input, handles the line discipline (cooked vs raw mode), and makes data available via stdin
   - **Line discipline role:** What the kernel's n_tty line discipline does — echo, line buffering, signal generation (SIGINT from Ctrl-C, SIGTSTP from Ctrl-Z), and how `tcsetattr()` modifies these behaviors
   - **C program read path:** What happens when `read(STDIN_FILENO, buf, 1)` is called in a C program — system call, wait queue, blocking vs non-blocking, VMIN/VTIME semantics
   - **Key classification:** How a C editor program must handle different input classes — printable bytes, control characters (Ctrl-letter), escape sequences (arrow keys, Page Up/Down, function keys), and how to decode multi-byte escape sequences from a single-byte `read()` loop
   - **Output path:** From `write(STDOUT_FILENO, ...)` through the kernel TTY discipline to the terminal emulator's display rendering
   - Include a Mermaid sequence diagram or ASCII art flow diagram showing the full path

2. Write `prep/key-classifier.py` — a Python script that demonstrates key classification:
   - Research: What are the different classes of input a terminal editor must handle? How are Ctrl-key combinations encoded? How do terminal emulators send arrow keys and function keys (CSI sequences)?
   - Implement a program that enters raw mode, reads bytes from stdin, and classifies each input into: printable ASCII, Ctrl-letter, escape sequence start (ESC), multi-byte escape sequence (show the raw bytes), or unknown
   - Display the classification and raw hex bytes for each pressed key
   - Print the special key name when it recognizes an arrow key, Page Up/Down, Home, End, Delete, or function key (F1–F4)
   - Exit on 'q' or Ctrl-C
   - Properly restore terminal state on exit

3. Write `prep/input-orchestration.py` — a Python script that simulates an editor's main loop decision tree:
   - Research: How do terminal editors route input? What's the typical decision tree (is this a printable? a control char? the start of an escape sequence?)?
   - Implement a state machine that demonstrates input routing:
     - Normal mode (inserting text): printable chars get echoed, Ctrl-letter triggers actions (exit, save placeholder, etc.)
     - Escape sequence mode: accumulate bytes until a complete CSI sequence matches, then dispatch to an action
   - Print a log of each input and what action was triggered (e.g., "ESC received → starting escape sequence" → "[A received → UP ARROW → cursor up")
   - Exit on Ctrl-Q
   - Properly restore terminal state on exit

4. All scripts must:
   - Use Python 3 stdlib only (no pip packages)
   - Include a `if __name__ == '__main__': main()` entry point
   - Handle terminal raw mode via `termios` module and restore state on exit via `atexit` or `try/finally`
   - Include inline comments citing sources for every escape sequence, termios flag, or kernel mechanism used
   - Exit cleanly with terminal restored

## Reference Format

Every escape sequence, ioctl, termios flag, or kernel mechanism used MUST have an inline comment citing its source:
- Man page sections (e.g., `man 3 tcsetattr`, `man 4 tty`, `man 7 termios`)
- Kernel documentation (e.g., `Documentation/admin-guide/tty/`)
- Specification documents (e.g., vt100.net, ECMA-48)
- URLs to reliable references

The `prep/flow.md` must include a full bibliography section with all sources used.

## Acceptance Criteria

- `prep/flow.md` exists, is well-structured, and covers all the subsystems listed above
- `prep/flow.md` includes a flow diagram (Mermaid or ASCII art)
- `prep/key-classifier.py` runs with Python 3, enters raw mode, properly classifies input, and exits cleanly restoring terminal state
- `prep/input-orchestration.py` runs with Python 3, demonstrates the input routing state machine, prints action logs, and exits cleanly on Ctrl-Q
- All scripts have cited references for escape sequences and termios operations
- `prep/flow.md` has a full bibliography

## Context Limits

The implementer MUST NOT:
- See the original `source/` repo
- See other specs beyond this one
- See `explore/CONTENT_ANGLES.md`
- Use any third-party Python packages
- Assume any terminal behavior or kernel mechanism is known without researching it

The implementer MUST:
- Use web search to research every subsystem before documenting it
- Cite sources for every escape sequence, termios flag, and kernel mechanism
- Include a bibliography in `prep/flow.md`
- Build on existing `prep/` scripts (read them for context, but do not modify them)
