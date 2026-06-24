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

## Bibliography

- VT100 User Guide: https://vt100.net/docs/vt100-ug/
- ECMA-48 Terminal Control Sequences: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
- ANSI escape code (Wikipedia): https://en.wikipedia.org/wiki/ANSI_escape_code
- XTerm Control Sequences: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
