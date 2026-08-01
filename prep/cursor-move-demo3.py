#!/usr/bin/env python3
"""Demo 3: drawing a horizontal line, one cell at a time, with CUF.

Reference: VT100 User Guide Chapter 3 - CUF (Cursor Forward).
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


def cursor_forward(count=1):
    """CSI count C - CUF (Cursor Forward / right)"""
    sys.stdout.write(CSI + f"{count}C")
    sys.stdout.flush()


def main():
    show_info_frame([
        "Drawing a horizontal line with CUF (Cursor Forward)",
        "",
        "Sequence: ESC [ n C",
        "Moves the cursor right by n columns (default 1).",
        "",
        "Combining CUF with a character write, the cursor advances rightward",
        "and the character appears in the new cell. In this demo we draw",
        "the line one cell at a time so the construction is visible.",
        "",
        "Expect:",
        "  - a horizontal line of 10 '+'s is drawn at row 12, columns 30-39",
        "  - one cell appears per frame, with the cursor visibly advancing right",
    ])

    # Live (before) - first time
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "Empty screen - ready to draw.".ljust(78))
    pause(PROMPT_HOLD)

    show_info_frame([
        "Sending the sequences now.",
        "",
        "  ESC [ 12 ; 30 H    - one CUP to the start point",
        "  10x (ESC [ 1 C, write '+')   - one cell per step",
        "",
        "Expect: a horizontal line of 10 '+'s built cell by cell.",
    ], hold=PROMPT_HOLD)

    # Live (before) - re-anchored
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, "Empty screen - ready to draw (re-anchored).".ljust(78))
    pause(PROMPT_HOLD)

    # The actual draw: one cell per frame.
    # Place the cursor at the start, then for each cell: CUF(1) + write('+').
    # The natural advance of the write + the explicit CUF gives 1 cell per
    # step, with the cursor at the end of the line after the last write.
    start_row, start_col, length = 12, 30, 10
    move_cursor(start_row, start_col)
    sys.stdout.flush()
    pause(PROMPT_HOLD)  # one frame per cell

    for _ in range(length):
        cursor_forward(1)
        sys.stdout.write("+")
        sys.stdout.flush()
        pause(PROMPT_HOLD)
    # Cursor is now at (row 12, col 40). Do NOT add any text - go to info frame.

    # Live (after) - just the line, no text overlay
    pause(OUTRO_HOLD)

    show_info_frame([
        "After drawing:",
        "",
        f"  - line starts at (row {start_row}, col {start_col}) and ends at (row {start_row}, col {start_col + length - 1})",
        "  - 10 cells, each placed with CUF(1) + write '+'",
        f"  - cursor is now at (row {start_row}, col {start_col + length}) - at the end of the line",
        "",
        "CUF is useful when the target is described by an offset from",
        "the current position rather than absolute coordinates.",
    ], hold=OUTRO_HOLD)


if __name__ == "__main__":
    main()
