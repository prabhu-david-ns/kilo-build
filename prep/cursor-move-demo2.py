#!/usr/bin/env python3
"""Demo 2: CSI row ; col H - CUP (Cursor Position).

Reference: VT100 User Guide Chapter 3 - Cursor Position (CUP).
"""

import sys

from _clear_common import (
    CSI,
    INTRO_HOLD,
    OUTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
    cursor_home,
    move_cursor,
    pause,
    print_at,
)


def show_info_frame(lines, hold=INTRO_HOLD):
    clear_entire_screen()
    cursor_home()
    for r, t in enumerate(lines, start=1):
        print_at(r, 1, t.ljust(78))
    pause(hold)


def main():
    show_info_frame([
        "CSI row ; col H   - CUP (Cursor Position)",
        "",
        "Sequence: ESC [ row ; col H",
        "Moves the cursor to an absolute row and column. Both default to 1.",
        "CSI row ; col f (HVP) is functionally equivalent.",
        "",
        "Expect:",
        "  - a series of CUP moves draws a 7-row x 20-col box at row 5, col 10",
        "  - each side of the box is placed with a separate CUP sequence",
    ])

    # Live (before) - first time
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "Empty screen - ready to draw.".ljust(78))
    pause(PROMPT_HOLD)

    show_info_frame([
        "Sending the sequences now.",
        "",
        "  ESC [ 5 ; 10 H     - move to top-left",
        "  ESC [ 6 ; 10 H ... - draw sides",
        "  ESC [ 11 ; 10 H    - move to bottom-left",
        "  + more CUP moves for borders",
        "",
        "Expect: a 7-row x 20-col box appears at row 5, col 10.",
    ], hold=PROMPT_HOLD)

    # Live (before) - re-anchored
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "Empty screen - ready to draw (re-anchored).".ljust(78))
    pause(PROMPT_HOLD)

    # The actual draw
    height, width = 7, 20
    start_row, start_col = 5, 10

    move_cursor(start_row, start_col)
    sys.stdout.write("+")
    for _ in range(width - 2):
        sys.stdout.write("-")
    sys.stdout.write("+")
    sys.stdout.flush()

    for i in range(1, height - 1):
        move_cursor(start_row + i, start_col)
        sys.stdout.write("|")
        move_cursor(start_row + i, start_col + width - 1)
        sys.stdout.write("|")
    sys.stdout.flush()

    move_cursor(start_row + height - 1, start_col)
    sys.stdout.write("+")
    for _ in range(width - 2):
        sys.stdout.write("-")
    sys.stdout.write("+")
    sys.stdout.flush()

    # Live (after)
    print_at(14, 1, "Box drawn using only CSI row ; col H (CUP).".ljust(78))
    print_at(15, 1, f"Top-left at (row {start_row}, col {start_col}); size {height} x {width}.".ljust(78))
    sys.stdout.flush()
    pause(OUTRO_HOLD)

    show_info_frame([
        "CSI row ; col H - CUP",
        "",
        "  - sets the cursor to an absolute (row, col) position",
        "  - both parameters default to 1 if omitted",
        "  - the HVP form (ESC [ row ; col f) is identical",
        "",
        "Use CUP when you know the target position. Use CUU/CUD/CUF/CUB",
        "when you want to step relative to the current position.",
    ], hold=OUTRO_HOLD)


if __name__ == "__main__":
    main()
