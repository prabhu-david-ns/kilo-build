#!/usr/bin/env python3
"""Demo 4: CSI 3J - Erase the saved lines (scrollback buffer).

Reference: xterm control sequences - extended ED with param 3.
"""

import sys

from _clear_common import (
    DEMO_PAUSE,
    INTRO_HOLD,
    PROMPT_HOLD,
    clear_entire_screen,
    clear_saved_lines,
    cursor_home,
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


def show_live_screen():
    """Show the visible screen with a note that scrollback has content above it.

    The actual scrollback lines are emitted before this function runs so they
    are scrolled off the top of the 24-row visible screen.
    """
    clear_entire_screen()
    cursor_home()
    rows = [
        (3,  "Visible screen content (row 3)."),
        (5,  "Visible screen content (row 5)."),
        (7,  "Visible screen content (row 7)."),
        (9,  "There are 40 lines in the scrollback above the visible screen."),
        (10, "Use Shift+PgUp to see them in the scrollback buffer."),
    ]
    for r, t in rows:
        print_at(r, 1, t.ljust(78))


def main():
    # Pre-fill scrollback: emit 40 lines so they scroll off the top.
    for i in range(40):
        sys.stdout.write(f"scrollback line {i + 1:>3}  (in the buffer above the visible screen)\n")
    sys.stdout.flush()

    # 1. Info A: just explain what to expect.
    show_info_frame([
        "CSI 3 J",
        "",
        "Sequence: ESC [ 3 J",
        "Erase the saved lines (scrollback buffer). xterm extension.",
        "The visible screen is NOT changed by CSI 3J.",
        "",
        "Expect:",
        "  - the 40 lines in the scrollback are cleared",
        "  - the visible screen is unchanged",
    ])

    # 2. Live screen: visible content with scrollback present.
    show_live_screen()
    pause(DEMO_PAUSE)

    # 3. Info B: announce we are sending the sequence now.
    show_info_frame([
        "Sending the sequence now.",
        "",
        "  ESC [ 3 J",
    ], hold=PROMPT_HOLD)

    # 4. Live screen again: re-draw the visible content.
    show_live_screen()
    pause(PROMPT_HOLD)

    # 5. Send CSI 3J.
    clear_saved_lines()
    pause(DEMO_PAUSE)

    # 6. Info C: explain what was shown.
    show_info_frame([
        "After CSI 3J:",
        "",
        "  - the 40 lines that were in the scrollback are GONE",
        "  - the visible screen (above) is UNCHANGED",
        "  - try Shift+PgUp: the buffer is now empty",
        "",
        "Note: CSI 3J is an xterm extension. Not all terminals support it.",
    ])


if __name__ == "__main__":
    main()
