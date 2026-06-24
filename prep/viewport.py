#!/usr/bin/env python3
"""
Terminal Viewport and Cursor Position Demo

Research and demonstrate:
- Device Status Report (DSR) for cursor position queries
- Fallback method for detecting terminal size via cursor clamping
- Python's shutil.get_terminal_size() behavior

References:
- VT100 User Guide: https://vt100.net/docs/vt100-ug/chapter3.html#DSR
- XTerm DSR: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-DeviceStatus
- Python shutil: https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size
"""

import sys
import os
import shutil
import termios
import fcntl
import struct
import atexit
import select
import tty

ESC = "\x1b"
CSI = ESC + "["

ORIGINAL_TTY_STATE = None

def save_tty_state():
    """Save terminal file descriptor and settings."""
    fd = sys.stdin.fileno()
    return fd, termios.tcgetattr(fd)

def restore_tty():
    """Restore terminal to original state."""
    global ORIGINAL_TTY_STATE
    if ORIGINAL_TTY_STATE:
        fd, state = ORIGINAL_TTY_STATE
        termios.tcsetattr(fd, termios.TCSADRAIN, state)

def setup_raw_terminal():
    """Configure terminal for raw mode with non-blocking read."""
    global ORIGINAL_TTY_STATE
    fd, state = save_tty_state()
    ORIGINAL_TTY_STATE = (fd, state)
    atexit.register(restore_tty)

    tty.setraw(fd)
    original_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, original_flags | os.O_NONBLOCK)

def move_cursor(row, col):
    """Move cursor to absolute position.
    Reference: VT100 User Guide Chapter 3 - Cursor Position (CUP)
    Sequence: CSI row ; col H"""
    sys.stdout.write(CSI + f"{row};{col}H")
    sys.stdout.flush()

def cursor_home():
    """Move cursor to home position (1,1).
    Reference: VT100 User Guide Chapter 3 - Cursor Home
    Sequence: CSI H"""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()

def clear_screen():
    """Clear entire screen.
    Reference: VT100 User Guide Chapter 3 - Erase in Display (ED)
    Sequence: CSI 2 J"""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()

def query_cursor_position():
    """Send Device Status Report to query cursor position.
    Reference: VT100 User Guide Chapter 3 - Device Status Report (DSR)
    Sequence: CSI 6 n — Report Cursor Position
    Response format: CSI row ; col R

    Returns:
        tuple: (row, col) if successful, None otherwise
    """
    fd = sys.stdin.fileno()

    sys.stdout.write(CSI + "6n")
    sys.stdout.flush()

    try:
        if select.select([fd], [], [], 2.0)[0]:
            response = os.read(fd, 32).decode('ascii')

            if response.startswith(CSI) and response.endswith('R'):
                params = response[2:-1].split(';')
                if len(params) == 2:
                    row, col = int(params[0]), int(params[1])
                    return (row, col)
    except Exception:
        pass

    return None

def get_terminal_size_fallback():
    """Detect terminal size by moving cursor to extremes.
    Reference: technique from various terminal emulators

    This method:
    1. Saves current cursor position
    2. Moves cursor far to the bottom-right (beyond terminal bounds)
    3. Queries the actual position (terminal clamps to max)
    4. Restores cursor position

    The terminal will clamp cursor to max valid position,
    giving us the terminal dimensions.
    """
    fd = sys.stdin.fileno()

    original_pos = query_cursor_position()

    move_cursor(9999, 9999)
    max_pos = query_cursor_position()

    if original_pos:
        move_cursor(original_pos[0], original_pos[1])
    else:
        cursor_home()

    if max_pos:
        return max_pos
    return None

def get_terminal_size_ioctl():
    """Get terminal size using TIOCGWINSZ ioctl.
    Reference: ioctl(2) man page - TIOCGWINSZ

    TIOCGWINSZ returns struct winsize {ushort ws_row, ws_col, ws_xpixel, ws_ypixel}
    """
    fd = sys.stdin.fileno()
    try:
        winsize = struct.pack('HHHH', 0, 0, 0, 0)
        result = fcntl.ioctl(fd, termios.TIOCGWINSZ, winsize)
        ws_row, ws_col, ws_xpixel, ws_ypixel = struct.unpack('HHHH', result)
        return (ws_row, ws_col)
    except Exception:
        return None

def main():
    clear_screen()
    cursor_home()

    print("Terminal Viewport and Cursor Position Demo")
    print("=" * 45)
    print()

    print("1. Using shutil.get_terminal_size():")
    print("-" * 40)
    ts = shutil.get_terminal_size()
    print(f"   Columns: {ts.columns}")
    print(f"   Lines: {ts.lines}")
    print(f"   Type: {type(ts).__name__}")
    print()

    print("2. Using TIOCGWINSZ ioctl directly:")
    print("-" * 40)
    size_ioctl = get_terminal_size_ioctl()
    if size_ioctl:
        print(f"   Rows: {size_ioctl[0]}, Cols: {size_ioctl[1]}")
    else:
        print("   Could not get size via ioctl")
    print()

    print("3. Querying cursor position with DSR (CSI 6n):")
    print("-" * 40)
    print("   Reference: VT100 User Guide - Device Status Report")
    print("   Sequence sent: CSI 6 n")
    print("   Expected response: CSI row ; col R")
    print()

    setup_raw_terminal()
    cursor_home()

    pos = query_cursor_position()
    if pos:
        print(f"   Current cursor position: row={pos[0]}, col={pos[1]}")
    else:
        print("   Could not get cursor position (timeout or error)")
    print()

    print("4. Fallback size detection via cursor clamping:")
    print("-" * 40)
    print("   Moving cursor to extreme position (9999, 9999)...")
    print("   The terminal clamps to max valid position.")

    move_cursor(9999, 9999)
    clamped_pos = query_cursor_position()

    if clamped_pos:
        print(f"   Terminal clamped to: row={clamped_pos[0]}, col={clamped_pos[1]}")
        print(f"   Implied terminal size: {clamped_pos[1]} columns x {clamped_pos[0]} lines")
    else:
        print("   Fallback method also failed")

    cursor_home()
    print()
    print("Demo complete!")

if __name__ == "__main__":
    main()
