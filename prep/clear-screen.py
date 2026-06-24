#!/usr/bin/env python3
"""
Terminal Screen Clearing Demo

Research and demonstrate VT100/ECMA-48 screen clearing escape sequences.

References:
- VT100 User Guide: https://vt100.net/docs/vt100-ug/chapter3.html#ED
- ECMA-48: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
- ANSI escape code: https://en.wikipedia.org/wiki/ANSI_escape_code
"""

import sys
import time
import os
import atexit

ESC = "\x1b"
CSI = ESC + "["

ORIGINAL_STTY = None

def save_tty_state():
    """Save terminal state using stty."""
    import subprocess
    try:
        result = subprocess.run(["stty", "-g"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return None

def restore_tty():
    """Restore terminal to original state."""
    if ORIGINAL_STTY:
        import subprocess
        try:
            subprocess.run(["stty", ORIGINAL_STTY], capture_output=True)
        except Exception:
            pass

def setup_raw_terminal():
    """Configure terminal to raw mode for escape sequence handling."""
    import subprocess
    subprocess.run(["stty", "raw", "-echo"], capture_output=True)

def clear_entire_screen():
    """Clear the entire screen using CSI 2J.
    Reference: VT100 User Guide Chapter 3 - Erase in Display (ED)
    Sequence: CSI 2 J — Erase all of the display."""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()

def clear_from_cursor_to_end():
    """Clear from cursor to end of screen using CSI 0J (default).
    Reference: VT100 User Guide Chapter 3 - ED with param 0
    Sequence: CSI 0 J — Erase from cursor to end of display."""
    sys.stdout.write(CSI + "0J")
    sys.stdout.flush()

def clear_from_start_to_cursor():
    """Clear from start of screen to cursor using CSI 1J.
    Reference: VT100 User Guide Chapter 3 - ED with param 1
    Sequence: CSI 1 J — Erase from start of display to cursor."""
    sys.stdout.write(CSI + "1J")
    sys.stdout.flush()

def clear_saved_lines():
    """Clear saved lines (scrollback buffer) using CSI 3J.
    Reference: XTerm control sequences - extended ED
    Sequence: CSI 3 J — Erase saved lines (xterm extension)."""
    sys.stdout.write(CSI + "3J")
    sys.stdout.flush()

def move_cursor(row, col):
    """Move cursor to absolute position.
    Reference: VT100 User Guide Chapter 3 - Cursor Position (CUP)
    Sequence: CSI row ; col H"""
    sys.stdout.write(CSI + f"{row};{col}H")
    sys.stdout.flush()

def cursor_home():
    """Move cursor to home position (1,1).
    Reference: VT100 User Guide Chapter 3 - Cursor Home
    Sequence: CSI H (equivalent to CSI 1;1H)"""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()

def disable_auto_wrap():
    """Disable auto-wrap mode.
    Reference: VT100 User Guide - Auto Wrap
    Sequence: CSI ? 7 l — Reset Auto Wrap (RM/r)"""
    sys.stdout.write(CSI + "?7l")
    sys.stdout.flush()

def enable_auto_wrap():
    """Enable auto-wrap mode.
    Sequence: CSI ? 7 h — Set Auto Wrap (SM/s)"""
    sys.stdout.write(CSI + "?7h")
    sys.stdout.flush()

def print_at(row, col, text):
    """Print text at absolute cursor position."""
    move_cursor(row, col)
    sys.stdout.write(text)
    sys.stdout.flush()

def draw_demo_content():
    """Draw some visible content to demonstrate clearing."""
    content = [
        (3, 5, "=== Screen Clearing Demo ==="),
        (5, 5, "This content will be cleared."),
        (7, 5, "Line A"),
        (8, 5, "Line B"),
        (9, 5, "Line C"),
        (11, 5, "Current line: Line D"),
    ]
    for row, col, text in content:
        print_at(row, col, text)

def demo_clear_entire_screen():
    """Demo 1: Clear entire screen (CSI 2J)."""
    cursor_home()
    draw_demo_content()
    time.sleep(1.5)

    print_at(14, 5, ">>> DEMO 1: Clearing entire screen (CSI 2J)...")
    time.sleep(1)
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "Screen cleared! Only this text remains.")
    time.sleep(1.5)

def demo_clear_from_cursor_to_end():
    """Demo 2: Clear from cursor to end of screen (CSI 0J)."""
    cursor_home()
    draw_demo_content()
    print_at(11, 5, "Current line: Line D"),
    time.sleep(1.5)

    print_at(14, 5, ">>> DEMO 2: Clear from cursor to end (CSI 0J)...")
    time.sleep(1)
    clear_from_cursor_to_end()
    time.sleep(1.5)

def demo_clear_from_start_to_cursor():
    """Demo 3: Clear from start to cursor (CSI 1J)."""
    cursor_home()
    draw_demo_content()
    time.sleep(1.5)

    print_at(14, 5, ">>> DEMO 3: Clear from start to cursor (CSI 1J)...")
    time.sleep(1)
    clear_from_start_to_cursor()
    time.sleep(1.5)

def demo_clear_saved_lines():
    """Demo 4: Clear saved lines / scrollback (CSI 3J)."""
    cursor_home()
    sys.stdout.write("Scrollback buffer cleared (if supported by terminal).\n")
    sys.stdout.write("This is a xterm extension - may not work on all terminals.\n")
    sys.stdout.flush()
    time.sleep(1.5)

    print_at(14, 5, ">>> DEMO 4: Clear saved lines (CSI 3J)...")
    time.sleep(1)
    clear_saved_lines()
    time.sleep(1.5)

def main():
    global ORIGINAL_STTY

    ORIGINAL_STTY = save_tty_state()
    atexit.register(restore_tty)

    try:
        setup_raw_terminal()

        clear_entire_screen()
        cursor_home()

        print("Terminal Screen Clearing Demonstration")
        print("=" * 40)
        print()
        print("This script demonstrates various screen clearing")
        print("escape sequences defined in VT100/ECMA-48.")
        print()
        print("Press Enter to start demos...")
        sys.stdout.flush()
        sys.stdin.readline()

        demo_clear_entire_screen()
        print()
        print("Press Enter for next demo...")
        sys.stdout.flush()
        sys.stdin.readline()

        demo_clear_from_cursor_to_end()
        print()
        print("Press Enter for next demo...")
        sys.stdout.flush()
        sys.stdin.readline()

        demo_clear_from_start_to_cursor()
        print()
        print("Press Enter for next demo...")
        sys.stdout.flush()
        sys.stdin.readline()

        demo_clear_saved_lines()

        clear_entire_screen()
        cursor_home()
        print("Demo complete!")
        print()
        print("Summary of sequences demonstrated:")
        print("  CSI 2 J  — Erase in Display (clear entire screen)")
        print("  CSI 0 J  — Erase from cursor to end (default)")
        print("  CSI 1 J  — Erase from start to cursor")
        print("  CSI 3 J  — Erase saved lines (xterm extension)")

    except Exception as e:
        restore_tty()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
