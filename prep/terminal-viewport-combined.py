#!/usr/bin/env python3
"""Combined Terminal Introspection Demo.

Merges terminal-info.py and viewport.py into one demo covering:
- os.isatty() for TTY detection
- TERM environment variable values
- shutil.get_terminal_size() for terminal dimensions
- TIOCGWINSZ ioctl for low-level size query
- DSR (CSI 6n) for cursor position
- Fallback size detection via cursor clamping
- DEC private mode toggles (cursor visible, auto-wrap)

References:
- VT100 User Guide: https://vt100.net/docs/vt100-ug/chapter3.html
- XTerm Control Sequences: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
- Python os.isatty(): https://docs.python.org/3/library/os.html#os.isatty
- terminfo: https://man7.org/linux/man-pages/man5/terminfo.5.html
- Python shutil: https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size
"""

import fcntl
import os
import select
import shutil
import struct
import sys
import termios

from _clear_common import (
    CSI,
    DEMO_PAUSE,
    INTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
    cursor_home,
    move_cursor,
    pause,
    print_at,
)

TERM_VALUES = {
    "vt100": "Classic DEC terminal",
    "vt102": "DEC VT102 with auto-wrap",
    "vt220": "DEC VT220 (8-bit controls)",
    "xterm": "XTerm (most common Linux terminal)",
    "xterm-256color": "XTerm with 256-color support",
    "screen-256color": "Screen with 256-color support",
    "tmux-256color": "Tmux with 256-color support",
    "linux": "Linux console",
}


def show_info_frame(lines, hold=INTRO_HOLD):
    clear_entire_screen()
    cursor_home()
    for r, t in enumerate(lines, start=1):
        print_at(r, 1, t.ljust(78))
    pause(hold)


def query_cursor_position(timeout=2.0):
    """Send DSR (CSI 6n) and return (row, col) or None."""
    fd = sys.stdin.fileno()
    original_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, original_flags | os.O_NONBLOCK)

    sys.stdout.write(CSI + "6n")
    sys.stdout.flush()

    pos = None
    try:
        if select.select([fd], [], [], timeout)[0]:
            response = os.read(fd, 32).decode("ascii", errors="replace")
            if response.startswith(CSI) and response.endswith("R"):
                params = response[2:-1].split(";")
                if len(params) == 2:
                    pos = (int(params[0]), int(params[1]))
    except Exception:
        pass
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, original_flags)
    return pos


def get_terminal_size_ioctl():
    """TIOCGWINSZ ioctl -> (rows, cols) or None."""
    fd = sys.stdin.fileno()
    try:
        winsize = struct.pack("HHHH", 0, 0, 0, 0)
        result = fcntl.ioctl(fd, termios.TIOCGWINSZ, winsize)
        ws_row, ws_col, _, _ = struct.unpack("HHHH", result)
        return (ws_row, ws_col)
    except Exception:
        return None


# ── Section 1: TTY detection ──────────────────────────────────────

def show_tty_detection():
    show_info_frame([
        "TTY detection with os.isatty()",
        "",
        "os.isatty(fd) returns True if the file descriptor",
        "is connected to a terminal device.",
        "",
        "Expect: True / False for stdin, stdout, stderr.",
    ])

    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "=== os.isatty() ===".ljust(78))
    for i, (name, fdno) in enumerate([("stdin", 0), ("stdout", 1), ("stderr", 2)]):
        print_at(3 + i, 1, f"  {name:8}  {os.isatty(fdno)}".ljust(78))
    try:
        ctid = os.ctermid()
        print_at(7, 1, f"  controlling terminal: {ctid}".ljust(78))
    except Exception:
        print_at(7, 1, "  (could not determine controlling terminal)".ljust(78))
    pause(DEMO_PAUSE)


# ── Section 2: TERM variable ──────────────────────────────────────

def show_term_var():
    show_info_frame([
        "TERM environment variable",
        "",
        "The TERM variable names the terminal type and is used",
        "to look up its capabilities in the terminfo database.",
    ])

    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "=== TERM environment variable ===".ljust(78))
    term_value = os.environ.get("TERM", "not set")
    print_at(3, 1, f"  Value: {term_value}".ljust(78))
    desc = TERM_VALUES.get(term_value, "Unknown terminal type")
    print_at(4, 1, f"  {desc}".ljust(78))

    print_at(6, 1, "  Common TERM values:".ljust(78))
    for i, (t, d) in enumerate(list(TERM_VALUES.items())[:5]):
        print_at(7 + i, 1, f"    {t:20} - {d}".ljust(78))
    pause(DEMO_PAUSE)


# ── Section 3: Terminal size (shutil + ioctl) ────────────────────

def show_terminal_size():
    show_info_frame([
        "Terminal size detection",
        "",
        "Two methods:",
        "  - shutil.get_terminal_size()  (Python stdlib)",
        "  - TIOCGWINSZ ioctl            (POSIX, returns struct winsize)",
        "",
        "Expect: columns x lines from both methods.",
    ])

    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "=== Terminal size ===".ljust(78))

    ts = shutil.get_terminal_size()
    print_at(3, 1, f"  shutil.get_terminal_size(): {ts.columns} cols x {ts.lines} lines".ljust(78))

    size = get_terminal_size_ioctl()
    if size:
        rows, cols = size
        print_at(4, 1, f"  TIOCGWINSZ ioctl:           {cols} cols x {rows} lines".ljust(78))
    else:
        print_at(4, 1, "  TIOCGWINSZ ioctl:           (failed)".ljust(78))
    pause(DEMO_PAUSE)


# ── Section 4: DSR query ──────────────────────────────────────────

def show_dsr_query():
    show_info_frame([
        "DSR - Device Status Report (CSI 6 n)",
        "",
        "Send:     CSI 6 n",
        "Reply:    CSI row ; col R",
        "",
        "Expect: a response showing the cursor position.",
    ])

    move_cursor(12, 30)
    pos = query_cursor_position()

    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "=== DSR query result ===".ljust(78))
    if pos:
        row, col = pos
        print_at(3, 1, f"  Cursor at: row {row}, col {col}".ljust(78))
        print_at(4, 1, "  (cursor was placed at row 12, col 30 before query)".ljust(78))
    else:
        print_at(3, 1, "  No response within 2 second timeout".ljust(78))
    pause(DEMO_PAUSE)


# ── Section 5: Fallback via cursor clamping ───────────────────────

def show_fallback_size():
    show_info_frame([
        "Fallback size via cursor clamping",
        "",
        "Move cursor far beyond screen (row 9999, col 9999).",
        "The terminal clamps to the max valid position.",
        "",
        "Expect: a row/col close to the actual terminal size.",
    ])

    original = query_cursor_position()
    move_cursor(9999, 9999)
    clamped = query_cursor_position()
    if original:
        move_cursor(original[0], original[1])

    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "=== Cursor-clamp fallback ===".ljust(78))
    if clamped:
        row, col = clamped
        print_at(3, 1, f"  Clamped to:   row {row}, col {col}".ljust(78))
        print_at(4, 1, f"  Implied size: {col} cols x {row} lines".ljust(78))
    else:
        print_at(3, 1, "  (query did not return a position)".ljust(78))
    pause(DEMO_PAUSE)


# ── Section 6: DEC private mode toggles ───────────────────────────

def show_dec_toggles():
    show_info_frame([
        "DEC private mode toggles",
        "",
        "  CSI ? 25 h/l   - DECTCEM (cursor visible on/off)",
        "  CSI ? 7  h/l   - DECAWM  (auto-wrap on/off)",
    ])

    for label_on, label_off, seq_on, seq_off, prompt in [
        ("cursor show", "cursor hide", "?25h", "?25l", "Cursor visible"),
        ("auto-wrap on", "auto-wrap off", "?7h", "?7l", "Auto-wrap enabled"),
    ]:
        clear_entire_screen()
        cursor_home()
        print_at(1, 1, "=== DEC private mode ===".ljust(78))
        print_at(3, 1, f"  Sending CSI {seq_off}  ({label_off}) ...".ljust(78))
        sys.stdout.write(CSI + seq_off)
        sys.stdout.flush()
        pause(PROMPT_HOLD)

        clear_entire_screen()
        cursor_home()
        print_at(1, 1, "=== DEC private mode ===".ljust(78))
        print_at(3, 1, f"  Sent: {label_off}  (CSI {seq_off})".ljust(78))
        pause(PROMPT_HOLD)

        clear_entire_screen()
        cursor_home()
        print_at(1, 1, "=== DEC private mode ===".ljust(78))
        print_at(3, 1, f"  Sending CSI {seq_on}  ({label_on}) ...".ljust(78))
        sys.stdout.write(CSI + seq_on)
        sys.stdout.flush()
        pause(PROMPT_HOLD)

        clear_entire_screen()
        cursor_home()
        print_at(1, 1, "=== DEC private mode ===".ljust(78))
        print_at(3, 1, f"  Restored: {label_on}  (CSI {seq_on})".ljust(78))
        pause(DEMO_PAUSE)


# ── Main ───────────────────────────────────────────────────────────

def main():
    show_tty_detection()
    show_info_frame(["Next: TERM environment variable."], hold=PROMPT_HOLD)
    show_term_var()

    show_info_frame(["Next: Terminal size (shutil + TIOCGWINSZ)."], hold=PROMPT_HOLD)
    show_terminal_size()

    show_info_frame(["Next: DSR cursor position query."], hold=PROMPT_HOLD)
    show_dsr_query()

    show_info_frame(["Next: Fallback size via cursor clamping."], hold=PROMPT_HOLD)
    show_fallback_size()

    show_info_frame(["Next: DEC private mode toggles."], hold=PROMPT_HOLD)
    show_dec_toggles()

    show_info_frame([
        "Demo complete.",
        "",
        "Facilities demonstrated:",
        "  os.isatty()                  - TTY detection",
        "  os.environ.get('TERM')       - Terminal type",
        "  shutil.get_terminal_size()   - High-level size query",
        "  TIOCGWINSZ ioctl             - Low-level size query",
        "  DSR (CSI 6 n)                - Cursor position report",
        "  Cursor clamping to (9999,9999) - Fallback size detection",
        "  CSI ? 25 h/l                 - Cursor visibility toggle",
        "  CSI ? 7  h/l                 - Auto-wrap toggle",
    ], hold=INTRO_HOLD)


if __name__ == "__main__":
    main()
