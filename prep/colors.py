#!/usr/bin/env python3
"""
ANSI Color Support Demo

Research and demonstrate VT100/ECMA-48 SGR (Select Graphic Rendition) sequences:
- 8 standard foreground/background colors
- 16-color mode (bright variants)
- 256-color extended mode

References:
- ECMA-48: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
- XTerm SGR: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-SetGraphicsRendition
- ANSI color codes: https://en.wikipedia.org/wiki/ANSI_escape_code
- VT100 User Guide: https://vt100.net/docs/vt100-ug/
"""

import sys
import os
import atexit
import tty
import termios

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

def sgr(*params):
    """Send SGR (Select Graphic Rendition) sequence.
    Reference: ECMA-48 Section 8.3.117 - SGR
    Sequence: CSI param ; param ; ... m"""
    sys.stdout.write(CSI + ";".join(str(p) for p in params) + "m")
    sys.stdout.flush()

def sgr_reset():
    """Reset all attributes to default.
    Reference: ECMA-48 - SGR parameter 0
    Sequence: CSI 0 m"""
    sgr(0)

def set_fg(color):
    """Set foreground color (0-7).
    Reference: ECMA-48 / ANSI standard colors
    Sequence: CSI 30 + color m"""
    sgr(30 + color)

def set_bg(color):
    """Set background color (0-7).
    Reference: ECMA-48 / ANSI standard colors
    Sequence: CSI 40 + color m"""
    sgr(40 + color)

def set_fg_bright(color):
    """Set bright foreground color (0-7).
    Reference: ANSI bright colors (mode 1 + 30+color)
    Sequence: CSI 1 ; 30 + color m"""
    sgr(1, 30 + color)

def set_bg_bright(color):
    """Set bright background color (0-7).
    Sequence: CSI 1 ; 40 + color m"""
    sgr(1, 40 + color)

def set_fg_256(color_index):
    """Set 256-color foreground.
    Reference: XTerm 256-color mode
    Sequence: CSI 38 ; 5 ; N m"""
    sgr(38, 5, color_index)

def set_bg_256(color_index):
    """Set 256-color background.
    Reference: XTerm 256-color mode
    Sequence: CSI 48 ; 5 ; N m"""
    sgr(48, 5, color_index)

def print_colored(text, fg=None, bg=None, bright=False):
    """Print text with specified colors."""
    if fg is not None and bg is not None:
        if bright:
            sgr(1, 30 + fg, 40 + bg)
        else:
            sgr(30 + fg, 40 + bg)
    elif fg is not None:
        if bright:
            sgr(1, 30 + fg)
        else:
            sgr(30 + fg)
    elif bg is not None:
        if bright:
            sgr(1, 40 + bg)
        else:
            sgr(40 + bg)

    sys.stdout.write(text)
    sys.stdout.flush()
    sgr_reset()

def move_cursor(row, col):
    """Move cursor to absolute position.
    Reference: VT100 User Guide Chapter 3 - Cursor Position (CUP)
    Sequence: CSI row ; col H"""
    sys.stdout.write(CSI + f"{row};{col}H")
    sys.stdout.flush()

def clear_screen():
    """Clear entire screen.
    Sequence: CSI 2 J"""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()

def cursor_home():
    """Move cursor to home position.
    Sequence: CSI H"""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()

def demo_8_colors():
    """Demonstrate 8 standard colors."""
    clear_screen()
    cursor_home()

    print("8-Color Mode Demo")
    print("=" * 40)
    print()
    print("Standard foreground colors (30-37):")
    print()

    color_names = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]

    for i, name in enumerate(color_names):
        set_fg(i)
        sys.stdout.write(f"  {name:10} ")
        sys.stdout.flush()
        sgr_reset()
        print(f" (code {30+i})")

    print()
    print("Standard background colors (40-47):")
    print()

    for i, name in enumerate(color_names):
        set_bg(i)
        sys.stdout.write(f"  {name:10} ")
        sys.stdout.flush()
        sgr_reset()
        print(f" (code {40+i})")

def demo_16_colors():
    """Demonstrate 16-color mode (with bold/bright)."""
    clear_screen()
    cursor_home()

    print("16-Color Mode Demo (with bold/bright)")
    print("=" * 40)
    print()
    print("Normal (30-37) vs Bright (1;30-37):")
    print()

    color_names = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]

    for i, name in enumerate(color_names):
        set_fg(i)
        sys.stdout.write(f"  Normal {name:10}")
        sys.stdout.flush()
        sgr_reset()
        sys.stdout.write("  ")
        set_fg_bright(i)
        sys.stdout.write(f"Bright {name:10}")
        sys.stdout.flush()
        sgr_reset()
        print()

def demo_256_colors():
    """Demonstrate 256-color extended mode."""
    clear_screen()
    cursor_home()

    print("256-Color Mode Demo")
    print("=" * 40)
    print()
    print("Extended colors using CSI 38;5;Nm (foreground) and CSI 48;5;Nm (background)")
    print()

    print("Colors 0-15 (standard + bright):")
    print()
    for i in range(16):
        set_fg_256(i)
        sys.stdout.write(f"{i:3}")
        sys.stdout.flush()
        sgr_reset()
        if i == 7:
            sys.stdout.write(" ")
        if i == 15:
            sys.stdout.write(" ")
    print()
    print()

    print("Color cube (16-231): 6x6x6 = 216 colors in R,G,B pattern")
    print("Format: R*36 + G*6 + B + 16")
    print()
    row = 0
    for r in range(6):
        for g in range(6):
            for b in range(6):
                color_idx = r * 36 + g * 6 + b + 16
                set_fg_256(color_idx)
                sys.stdout.write(f"{color_idx:3}")
                sys.stdout.flush()
                sgr_reset()
            sys.stdout.write("  ")
        print()
        row += 1
        if row >= 6:
            print()
            row = 0

    print()
    print("Grayscale (232-255): 24 shades of gray")
    print()
    for i in range(232, 256):
        set_fg_256(i)
        sys.stdout.write(f"{i:3}")
        sys.stdout.flush()
        sgr_reset()
        if i == 243:
            print()
    print()

def demo_color_grid():
    """Display a color grid with labels."""
    clear_screen()
    cursor_home()

    print("Color Grid with Backgrounds")
    print("=" * 40)
    print()
    print("Row bg=0   Row bg=1   Row bg=2   Row bg=3")
    print("Black  Red   Green  Yellow Blue   Magenta Cyan   White")
    print()

    for fg in range(8):
        color_names = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]
        for bg in range(4):
            set_fg(fg)
            set_bg(bg)
            sys.stdout.write(f"{color_names[fg][:4]} ")
            sys.stdout.flush()
        sgr_reset()
        sys.stdout.write("  ")
        for bg in range(4, 8):
            set_fg(fg)
            set_bg(bg)
            sys.stdout.write(f"{color_names[fg][:4]} ")
            sys.stdout.flush()
        sgr_reset()
        print()

def main():
    global ORIGINAL_TTY_STATE

    ORIGINAL_TTY_STATE = save_tty_state()
    setup_raw_terminal()

    try:
        demo_8_colors()

        print()
        print("Press Enter for 16-color demo...")
        sys.stdin.readline()

        demo_16_colors()

        print()
        print("Press Enter for 256-color demo...")
        sys.stdin.readline()

        demo_256_colors()

        print()
        print("Press Enter for color grid...")
        sys.stdin.readline()

        demo_color_grid()

        clear_screen()
        cursor_home()
        print("ANSI Color Demo complete!")
        print()
        print("Summary of SGR sequences demonstrated:")
        print("  CSI 30-37 m      — Set foreground (8 colors)")
        print("  CSI 40-47 m      — Set background (8 colors)")
        print("  CSI 1 ; 30-37 m  — Set bright foreground")
        print("  CSI 1 ; 40-47 m  — Set bright background")
        print("  CSI 38 ; 5 ; N m — Set 256-color foreground")
        print("  CSI 48 ; 5 ; N m — Set 256-color background")
        print("  CSI 0 m          — Reset all attributes")

    except Exception as e:
        restore_tty()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
