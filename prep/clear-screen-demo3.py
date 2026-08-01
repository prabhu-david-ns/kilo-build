#!/usr/bin/env python3
"""Demo 3: CSI 1J - Erase from start of screen to cursor.

Reference: VT100 User Guide Chapter 3 - Erase in Display (ED) with param 1.
"""

from _clear_common import (
    DEMO_PAUSE,
    INTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
    clear_from_start_to_cursor,
    cursor_home,
    move_cursor,
    pause,
    print_at,
)


def show_info_frame(lines, hold=INTRO_HOLD):
    """Show an info frame: clear the screen, print lines, hold."""
    clear_entire_screen()
    cursor_home()
    for r, t in enumerate(lines, start=1):
        print_at(r, 1, t.ljust(78))
    pause(hold)


def show_full_screen():
    """Show a full screen with a cursor marker on row 11."""
    clear_entire_screen()
    cursor_home()
    top_rows = [
        (1, "=== Live screen: full content ==="),
        (2, "Top half (rows 1-11) will be CLEARED by CSI 1J."),
        (3, "Row  3: will be cleared."),
        (4, "Row  4: will be cleared."),
        (5, "Row  5: will be cleared."),
        (6, "Row  6: will be cleared."),
        (7, "Row  7: will be cleared."),
        (8, "Row  8: will be cleared."),
        (9, "Row  9: will be cleared."),
        (10, "Row 10: will be cleared."),
    ]
    for r, t in top_rows:
        print_at(r, 1, t.ljust(78))

    print_at(11, 1, "[cursor on row 11] === CSI 1J clears from start of screen to HERE ===".ljust(78))

    bottom_rows = [
        (13, "Row 13: stays visible."),
        (15, "Row 15: stays visible."),
        (17, "Row 17: stays visible."),
        (19, "Row 19: stays visible."),
        (21, "Row 21: stays visible."),
    ]
    for r, t in bottom_rows:
        print_at(r, 1, t.ljust(78))

    move_cursor(11, 1)


def main():
    # 1. Info A: just explain what to expect.
    show_info_frame([
        "CSI 1 J",
        "",
        "Sequence: ESC [ 1 J",
        "Erase from the start of the screen to the cursor.",
        "",
        "Expect (with the cursor on row 11):",
        "  - rows 1-11 disappear",
        "  - rows 12-23 stay",
        "  - the cursor stays at row 11 (CSI 1J does not move it)",
    ])

    # 2. Live screen: show the content with cursor on row 11.
    show_full_screen()
    pause(DEMO_PAUSE)

    # 3. Info B: announce we are sending the sequence now.
    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 1 J",
    ], hold=PROMPT_HOLD)

    # 4. Live screen again: same content, cursor re-placed at row 11.
    show_full_screen()
    pause(PROMPT_HOLD)

    # 5. Send CSI 1J. Top half cleared.
    clear_from_start_to_cursor()
    pause(DEMO_PAUSE)

    # 6. Info C: explain what was shown.
    show_info_frame([
        "After CSI 1J:",
        "",
        "  - top half (rows 1-11) is cleared",
        "  - bottom half (rows 12-23) is preserved",
        "  - the cursor was NOT moved by the erase",
        "    (it stayed at row 11, col 1, as shown in the previous frame)",
        "",
        "CSI 1 J - erase from the start of the screen to the cursor.",
    ])


if __name__ == "__main__":
    main()
