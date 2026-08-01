#!/usr/bin/env python3
"""Demo 2: CSI 0J - Erase from cursor to end of screen (default).

Reference: VT100 User Guide Chapter 3 - Erase in Display (ED) with param 0.
"""

from _clear_common import (
    DEMO_PAUSE,
    INTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
    clear_from_cursor_to_end,
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
        (1,  "=== Live screen: full content ==="),
        (3,  "Top half (rows 1-10) is preserved by CSI 0J."),
        (5,  "Row  5: stays visible."),
        (7,  "Row  7: stays visible."),
        (9,  "Row  9: stays visible."),
    ]
    for r, t in top_rows:
        print_at(r, 1, t.ljust(78))

    print_at(11, 1, "[cursor on row 11] === CSI 0J clears from HERE downward ===".ljust(78))

    bottom_rows = [
        (13, "Row 13: will be CLEARED by CSI 0J"),
        (15, "Row 15: will be CLEARED by CSI 0J"),
        (17, "Row 17: will be CLEARED by CSI 0J"),
        (19, "Row 19: will be CLEARED by CSI 0J"),
        (21, "Row 21: will be CLEARED by CSI 0J"),
    ]
    for r, t in bottom_rows:
        print_at(r, 1, t.ljust(78))

    move_cursor(11, 1)


def main():
    # 1. Info A: just explain what to expect.
    show_info_frame([
        "CSI 0 J",
        "",
        "Sequence: ESC [ 0 J   (the 0 is the default, so ESC [ J works too)",
        "Erase from the cursor position to the end of the screen.",
        "",
        "Expect (with the cursor on row 11):",
        "  - rows 11-23 disappear",
        "  - rows 1-10 stay",
        "  - the cursor stays at row 11 (CSI 0J does not move it)",
    ])

    # 2. Live screen: show the content with cursor on row 11.
    show_full_screen()
    pause(DEMO_PAUSE)

    # 3. Info B: announce we are sending the sequence now.
    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 0 J",
    ], hold=PROMPT_HOLD)

    # 4. Live screen again: same content, cursor re-placed at row 11.
    show_full_screen()
    pause(PROMPT_HOLD)

    # 5. Send CSI 0J. Bottom half cleared.
    clear_from_cursor_to_end()
    pause(DEMO_PAUSE)

    # 6. Info C: explain what was shown.
    show_info_frame([
        "After CSI 0J:",
        "",
        "  - top half (rows 1-10) is preserved",
        "  - bottom half (rows 11-23) is cleared",
        "  - the cursor was NOT moved by the erase",
        "    (it stayed at row 11, col 1, as shown in the previous frame)",
        "",
        "CSI 0 J - erase from the cursor to the end of the screen.",
    ])


if __name__ == "__main__":
    main()
