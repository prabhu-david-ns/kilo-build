#!/usr/bin/env python3
"""Cursor movement: CUU, CUD, CUF, CUB (relative movement).

Reference: VT100 User Guide Chapter 3 - CUU / CUD / CUF / CUB.

Combines the four relative-movement sequences into one demo. For each
direction we show the cursor moving from a known starting position.
"""

import sys

from _clear_common import (
    CSI,
    DEMO_PAUSE,
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


def show_position_screen(row, col, label, hold=DEMO_PAUSE):
    """Show a near-empty screen with the cursor at (row, col) and a label."""
    clear_entire_screen()
    cursor_home()
    print_at(1, 1, f"Cursor at row {row}, col {col} - {label}".ljust(78))
    move_cursor(row, col)
    sys.stdout.flush()
    pause(hold)


def cursor_up(count=1):
    sys.stdout.write(CSI + f"{count}A")
    sys.stdout.flush()


def cursor_down(count=1):
    sys.stdout.write(CSI + f"{count}B")
    sys.stdout.flush()


def cursor_forward(count=1):
    sys.stdout.write(CSI + f"{count}C")
    sys.stdout.flush()


def cursor_back(count=1):
    sys.stdout.write(CSI + f"{count}D")
    sys.stdout.flush()


def demo_cuu():
    show_info_frame([
        "CSI n A   - CUU (Cursor Up)",
        "",
        "Sequence: ESC [ n A  (n defaults to 1)",
        "Moves the cursor up by n rows. The cursor does not wrap.",
        "",
        "Expect:",
        "  - starting at (row 8, col 5), sending CSI 2 A moves the cursor to (row 6, col 5)",
        "  - the column is unchanged (only the row changes)",
    ])

    # Live (before) - first time
    show_position_screen(8, 5, "starting position")

    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 2 A   (CUU 2: move up 2 rows)",
    ], hold=PROMPT_HOLD)

    # Live (before) - re-anchored, second time
    show_position_screen(8, 5, "starting position (re-anchored)")

    # The actual move
    cursor_up(2)

    # Live (after)
    show_position_screen(6, 5, "after CSI 2 A (cursor moved up 2 rows)")


def demo_cud():
    show_info_frame([
        "CSI n B   - CUD (Cursor Down)",
        "",
        "Sequence: ESC [ n B  (n defaults to 1)",
        "Moves the cursor down by n rows. The cursor does not wrap.",
        "",
        "Expect:",
        "  - starting at (row 8, col 5), sending CSI 3 B moves the cursor to (row 11, col 5)",
        "  - the column is unchanged (only the row changes)",
    ])

    show_position_screen(8, 5, "starting position")

    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 3 B   (CUD 3: move down 3 rows)",
    ], hold=PROMPT_HOLD)

    show_position_screen(8, 5, "starting position (re-anchored)")

    cursor_down(3)

    show_position_screen(11, 5, "after CSI 3 B (cursor moved down 3 rows)")


def demo_cuf():
    show_info_frame([
        "CSI n C   - CUF (Cursor Forward / right)",
        "",
        "Sequence: ESC [ n C  (n defaults to 1)",
        "Moves the cursor right by n columns. The cursor does not wrap.",
        "",
        "Expect:",
        "  - starting at (row 8, col 5), sending CSI 4 C moves the cursor to (row 8, col 9)",
        "  - the row is unchanged (only the column changes)",
    ])

    show_position_screen(8, 5, "starting position")

    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 4 C   (CUF 4: move right 4 columns)",
    ], hold=PROMPT_HOLD)

    show_position_screen(8, 5, "starting position (re-anchored)")

    cursor_forward(4)

    show_position_screen(8, 9, "after CSI 4 C (cursor moved right 4 columns)")


def demo_cub():
    show_info_frame([
        "CSI n D   - CUB (Cursor Back / left)",
        "",
        "Sequence: ESC [ n D  (n defaults to 1)",
        "Moves the cursor left by n columns. The cursor does not wrap.",
        "",
        "Expect:",
        "  - starting at (row 8, col 9), sending CSI 2 D moves the cursor to (row 8, col 7)",
        "  - the row is unchanged (only the column changes)",
    ])

    show_position_screen(8, 9, "starting position")

    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 2 D   (CUB 2: move left 2 columns)",
    ], hold=PROMPT_HOLD)

    show_position_screen(8, 9, "starting position (re-anchored)")

    cursor_back(2)

    show_position_screen(8, 7, "after CSI 2 D (cursor moved left 2 columns)")


def main():
    demo_cuu()
    show_info_frame([
        "Sending the next demo now.",
        "",
        "  CSI n B - CUD (Cursor Down)",
    ], hold=PROMPT_HOLD)
    demo_cud()
    show_info_frame([
        "Sending the next demo now.",
        "",
        "  CSI n C - CUF (Cursor Forward)",
    ], hold=PROMPT_HOLD)
    demo_cuf()
    show_info_frame([
        "Sending the next demo now.",
        "",
        "  CSI n D - CUB (Cursor Back)",
    ], hold=PROMPT_HOLD)
    demo_cub()

    show_info_frame([
        "Demo complete.",
        "",
        "Summary of relative-movement sequences:",
        "  CSI n A  - CUU (Cursor Up)",
        "  CSI n B  - CUD (Cursor Down)",
        "  CSI n C  - CUF (Cursor Forward / right)",
        "  CSI n D  - CUB (Cursor Back / left)",
        "",
        "All four move the cursor by n cells (default 1) in their",
        "respective direction. The cursor does not wrap.",
    ], hold=OUTRO_HOLD)


if __name__ == "__main__":
    main()
