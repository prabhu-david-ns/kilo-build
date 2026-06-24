#!/usr/bin/env python3
"""
Cursor Movement Demo

Research and demonstrate VT100 cursor positioning escape sequences:
- CUP (Cursor Position) for absolute positioning
- CUU/CUD/CUF/CUB for relative movement
- HVP (Horizontal Vertical Position)

References:
- VT100 User Guide: https://vt100.net/docs/vt100-ug/chapter3.html#CUP
- ECMA-48: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
- ANSI escape code: https://en.wikipedia.org/wiki/ANSI_escape_code
"""

import sys
import time
import atexit
import tty
import termios
import os

ESC = "\x1b"
CSI = ESC + "["

ORIGINAL_TTY_STATE = None

def save_tty_state():
    """Save terminal state."""
    fd = sys.stdin.fileno()
    return fd, termios.tcgetattr(fd)

def restore_tty():
    """Restore terminal to original state."""
    global ORIGINAL_TTY_STATE
    if ORIGINAL_TTY_STATE:
        fd, state = ORIGINAL_TTY_STATE
        termios.tcsetattr(fd, termios.TCSADRAIN, state)

def setup_raw_terminal():
    """Configure terminal for raw mode."""
    global ORIGINAL_TTY_STATE
    fd, state = save_tty_state()
    ORIGINAL_TTY_STATE = (fd, state)
    atexit.register(restore_tty)
    tty.setraw(fd)

def clear_screen():
    """Clear entire screen.
    Reference: VT100 User Guide Chapter 3 - Erase in Display (ED)
    Sequence: CSI 2 J"""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()

def cursor_home():
    """Move cursor to home position (1,1).
    Reference: VT100 User Guide Chapter 3 - Cursor Home
    Sequence: CSI H"""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()

def move_cursor(row, col):
    """Move cursor to absolute position using CUP.
    Reference: VT100 User Guide Chapter 3 - Cursor Position (CUP)
    Sequence: CSI row ; col H"""
    sys.stdout.write(CSI + f"{row};{col}H")
    sys.stdout.flush()

def move_hvp(row, col):
    """Move cursor using Horizontal Vertical Position.
    Reference: ECMA-48 - HVP (Horizontal Vertical Position)
    Sequence: CSI row ; col f
    Note: HVP is functionally equivalent to CUP but uses 'f' terminator."""
    sys.stdout.write(CSI + f"{row};{col}f")
    sys.stdout.flush()

def cursor_up(count=1):
    """Move cursor up.
    Reference: VT100 User Guide Chapter 3 - CUU (Cursor Up)
    Sequence: CSI count A"""
    sys.stdout.write(CSI + f"{count}A")
    sys.stdout.flush()

def cursor_down(count=1):
    """Move cursor down.
    Reference: VT100 User Guide Chapter 3 - CUD (Cursor Down)
    Sequence: CSI count B"""
    sys.stdout.write(CSI + f"{count}B")
    sys.stdout.flush()

def cursor_forward(count=1):
    """Move cursor forward (right).
    Reference: VT100 User Guide Chapter 3 - CUF (Cursor Forward)
    Sequence: CSI count C"""
    sys.stdout.write(CSI + f"{count}C")
    sys.stdout.flush()

def cursor_back(count=1):
    """Move cursor back (left).
    Reference: VT100 User Guide Chapter 3 - CUB (Cursor Back)
    Sequence: CSI count D"""
    sys.stdout.write(CSI + f"{count}D")
    sys.stdout.flush()

def print_char(ch):
    """Print a single character without newline."""
    sys.stdout.write(ch)
    sys.stdout.flush()

def draw_box_top(width, start_row, start_col):
    """Draw top border of box using absolute positioning."""
    move_cursor(start_row, start_col)
    print_char('+')
    for _ in range(width - 2):
        print_char('-')
    print_char('+')

def draw_box_bottom(width, start_row, start_col):
    """Draw bottom border of box."""
    move_cursor(start_row, start_col)
    print_char('+')
    for _ in range(width - 2):
        print_char('-')
    print_char('+')

def draw_box_sides(height, width, start_row, start_col):
    """Draw left and right sides of box."""
    for i in range(1, height - 1):
        row = start_row + i
        move_cursor(row, start_col)
        print_char('|')
        move_cursor(row, start_col + width - 1)
        print_char('|')

def draw_box(height, width, start_row, start_col):
    """Draw a box at specified position using absolute cursor positioning."""
    draw_box_top(width, start_row, start_col)
    draw_box_bottom(height, start_row + height - 1, start_col)
    draw_box_sides(height, width, start_row, start_col)

def draw_cross(center_row, center_col, size):
    """Draw a cross/plus sign at center using relative movement."""
    move_cursor(center_row, center_col)

    cursor_up(size // 2)
    print_char('+')
    for _ in range(size // 2):
        cursor_back(1)
        cursor_up(1)
        print_char('+')
    cursor_down(size // 2)
    cursor_forward(1)

    cursor_down(size // 2)
    print_char('+')
    for _ in range(size // 2):
        cursor_back(1)
        cursor_down(1)
        print_char('+')
    cursor_up(size // 2)
    cursor_forward(1)

    cursor_forward(size // 2)
    print_char('+')
    for _ in range(size // 2):
        cursor_down(1)
        cursor_forward(1)
        print_char('+')
    cursor_up(size // 2)
    cursor_back(1)

    cursor_back(size // 2)
    print_char('+')
    for _ in range(size // 2):
        cursor_up(1)
        cursor_back(1)
        print_char('+')

def demo_relative_movement():
    """Demonstrate relative cursor movement sequences."""
    clear_screen()
    cursor_home()

    print("Demo 1: Relative Cursor Movement (CUU, CUD, CUF, CUB)")
    print("=" * 50)
    print()
    print("Starting at column 5, row 8...")
    print()

    start_row, start_col = 8, 5
    move_cursor(start_row, start_col)

    print("Sequence: CUU 2 (Cursor Up 2)")
    cursor_up(2)
    print(">>> Cursor moved up 2 lines")
    time.sleep(1)

    print("Sequence: CUD 3 (Cursor Down 3)")
    cursor_down(3)
    print(">>> Cursor moved down 3 lines")
    time.sleep(1)

    print("Sequence: CUF 4 (Cursor Forward 4)")
    cursor_forward(4)
    print(">>> Cursor moved right 4 columns")
    time.sleep(1)

    print("Sequence: CUB 2 (Cursor Back 2)")
    cursor_back(2)
    print(">>> Cursor moved left 2 columns")
    time.sleep(1)

    print()
    print("Final position: row 9, col 7")

def demo_absolute_positioning():
    """Demonstrate absolute cursor positioning (CUP vs HVP)."""
    clear_screen()
    cursor_home()

    print("Demo 2: Absolute Cursor Positioning (CUP vs HVP)")
    print("=" * 50)
    print()
    print("CUP (Cursor Position): CSI row ; col H")
    print("HVP (Horizontal Vertical Position): CSI row ; col f")
    print()
    print("Both are functionally equivalent - drawing shapes below:")
    print()

    draw_box(7, 20, 5, 10)

    print()
    print()
    print("Box drawn at row 5, col 10 using CUP (CSI row ; col H)")

def demo_cross_shape():
    """Draw a cross/plus sign using relative movement."""
    clear_screen()
    cursor_home()

    print("Demo 3: Cross Shape via Relative Movement")
    print("=" * 50)
    print()
    print("Drawing a cross at center of screen using CUU, CUD, CUF, CUB...")
    print()

    center_row, center_col = 12, 40
    draw_cross(center_row, center_col, 7)

    print()
    print()
    print("Cross drawn using relative movements from center")

def main():
    global ORIGINAL_TTY_STATE

    ORIGINAL_TTY_STATE = save_tty_state()
    setup_raw_terminal()

    try:
        demo_relative_movement()

        print()
        print("Press Enter to continue...")
        sys.stdin.readline()

        demo_absolute_positioning()

        print()
        print("Press Enter to continue...")
        sys.stdin.readline()

        demo_cross_shape()

        clear_screen()
        cursor_home()
        print("Cursor movement demo complete!")
        print()
        print("Summary of sequences demonstrated:")
        print("  CSI row ; col H    — CUP (Cursor Position)")
        print("  CSI row ; col f    — HVP (Horizontal Vertical Position)")
        print("  CSI count A        — CUU (Cursor Up)")
        print("  CSI count B        — CUD (Cursor Down)")
        print("  CSI count C        — CUF (Cursor Forward)")
        print("  CSI count D        — CUB (Cursor Back)")

    except Exception as e:
        restore_tty()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
