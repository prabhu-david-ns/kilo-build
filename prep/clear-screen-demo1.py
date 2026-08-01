#!/usr/bin/env python3
"""Demo 1: CSI 2J - Erase the entire screen.

Reference: VT100 User Guide Chapter 3 - Erase in Display (ED).
"""

from _clear_common import (
    DEMO_PAUSE,
    INTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
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


def show_filled_screen():
    """Show the live screen: full content with cursor at row 12, col 30."""
    clear_entire_screen()
    cursor_home()
    rows = [
        (1,  "=== Live screen: full content ==="),
        (3,  "Before clearing, the screen is filled with content."),
        (5,  "Row  5: example content line."),
        (7,  "Row  7: example content line."),
        (9,  "Row  9: example content line."),
        (11, "Row 11: example content line."),
        (13, "Row 13: example content line."),
        (15, "Row 15: example content line."),
        (17, "Row 17: example content line."),
        (19, "Row 19: example content line."),
        (21, "Row 21: example content line."),
    ]
    for r, t in rows:
        print_at(r, 1, t.ljust(78))
    move_cursor(12, 30)


def main():
    # 1. Info A: just explain what to expect. No plan.
    show_info_frame([
        "CSI 2 J",
        "",
        "Sequence: ESC [ 2 J",
        "Erase in Display - clears the ENTIRE visible screen.",
        "",
        "Expect:",
        "  - the entire screen goes blank",
        "  - the cursor stays where it was (CSI 2J does not move it)",
    ])

    # 2. Live screen: show the content.
    show_filled_screen()
    pause(DEMO_PAUSE)

    # 3. Info B: announce we are sending the sequence now.
    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 2 J",
    ], hold=PROMPT_HOLD)

    # 4. Live screen again: same content, cursor re-placed at row 12, col 30.
    show_filled_screen()
    pause(PROMPT_HOLD)

    # 5. Send CSI 2J. Cleared screen.
    clear_entire_screen()
    pause(DEMO_PAUSE)

    # 6. Info C: explain what was shown.
    show_info_frame([
        "After CSI 2J:",
        "",
        "  - the entire visible screen is blank",
        "  - the cursor was NOT moved by the erase",
        "    (it stayed at row 12, col 30, as shown in the previous frame)",
        "",
        "CSI 2 J - clears the entire visible screen.",
        "The cursor position is NOT changed by the erase.",
    ])


if __name__ == "__main__":
    main()
