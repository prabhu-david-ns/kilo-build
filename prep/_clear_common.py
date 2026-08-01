"""Shared escape-sequence helpers for the clear-screen demos.

Reference: VT100 User Guide Chapter 3 - Erase in Display (ED).
"""

import sys
import time

ESC = "\x1b"
CSI = ESC + "["

PROMPT_PAUSE = 2.0
DEMO_PAUSE = 2.5
INTRO_HOLD = 4.0
PROMPT_HOLD = 3.0
OUTRO_HOLD = 4.0


def clear_entire_screen():
    """CSI 2J - erase the entire visible screen."""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()


def clear_from_cursor_to_end():
    """CSI 0J - erase from the cursor to the end of the screen (default)."""
    sys.stdout.write(CSI + "0J")
    sys.stdout.flush()


def clear_from_start_to_cursor():
    """CSI 1J - erase from the start of the screen to the cursor."""
    sys.stdout.write(CSI + "1J")
    sys.stdout.flush()


def clear_saved_lines():
    """CSI 3J - erase the scrollback buffer (xterm extension)."""
    sys.stdout.write(CSI + "3J")
    sys.stdout.flush()


def move_cursor(row, col):
    """CSI row ; col H - move the cursor to an absolute position."""
    sys.stdout.write(CSI + f"{row};{col}H")
    sys.stdout.flush()


def cursor_home():
    """CSI H - move the cursor to row 1, col 1."""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()


def print_at(row, col, text):
    move_cursor(row, col)
    sys.stdout.write(text)
    sys.stdout.flush()


def pause(seconds):
    time.sleep(seconds)
