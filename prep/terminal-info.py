#!/usr/bin/env python3
"""
Terminal Information and Introspection Demo

Research and demonstrate:
- os.isatty() for TTY detection
- TERM environment variable values
- Escape sequence response detection

References:
- Python os.isatty(): https://docs.python.org/3/library/os.html#os.isatty
- TERM variable: https://man7.org/linux/man-pages/man5/terminfo.5.html
- Terminal capabilities: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
"""

import sys
import os
import shutil
import select
import fcntl
import struct
import termios
import tty
import atexit

ESC = "\x1b"
CSI = ESC + "["

ORIGINAL_TTY_STATE = None

TERM_VALUES = {
    "vt100": "Classic DEC terminal",
    "vt102": "DEC VT102 with auto-wrap",
    "vt220": "DEC VT220 (8-bit controls)",
    "xterm": "XTerm (most common Linux terminal)",
    "xterm-16color": "XTerm with 16-color support",
    "xterm-256color": "XTerm with 256-color support",
    "xterm-kitty": "Kitty terminal emulator",
    "screen": "GNU Screen (terminal multiplexer)",
    "screen-256color": "Screen with 256-color support",
    "tmux": "Tmux terminal multiplexer",
    "tmux-256color": "Tmux with 256-color support",
    "linux": "Linux console",
    "ansi": "Generic ANSI terminal",
}

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

def isatty_info():
    """Get information about TTY status using os.isatty().
    Reference: Python os module - os.isatty()
    https://docs.python.org/3/library/os.html#os.isatty

    Returns True if the file descriptor is connected to a TTY.
    """
    stdin_is_tty = os.isatty(sys.stdin.fileno())
    stdout_is_tty = os.isatty(sys.stdout.fileno())
    stderr_is_tty = os.isatty(sys.stderr.fileno())

    print("TTY Status (os.isatty):")
    print("-" * 40)
    print(f"  stdin:  {stdin_is_tty}")
    print(f"  stdout: {stdout_is_tty}")
    print(f"  stderr: {stderr_is_tty}")
    print()

    if stdin_is_tty:
        try:
            ctid = os.ctermid()
            print(f"  Controlling terminal: {ctid}")
        except Exception:
            print("  Could not determine controlling terminal")
    print()

def term_info():
    """Display TERM environment variable information.
    Reference: Linux terminfo man page (man 5 terminfo)
    https://man7.org/linux/man-pages/man5/terminfo.5.html

    The TERM variable typically contains the terminal type name
    which corresponds to a terminfo entry describing the
    terminal's capabilities.
    """
    term_value = os.environ.get("TERM", "not set")

    print("TERM Environment Variable:")
    print("-" * 40)
    print(f"  Value: {term_value}")
    print()

    if term_value in TERM_VALUES:
        print(f"  Known terminal: {TERM_VALUES[term_value]}")
    elif term_value.startswith("xterm"):
        print("  XTerm variant detected")
    elif term_value.startswith("screen"):
        print("  GNU Screen variant detected")
    elif term_value.startswith("tmux"):
        print("  Tmux variant detected")
    else:
        print("  Unknown terminal type")

    print()
    print("  Common TERM values:")
    for term, desc in list(TERM_VALUES.items())[:6]:
        print(f"    {term:20} — {desc}")
    print()

def get_terminal_size():
    """Get terminal window size using multiple methods."""
    print("Terminal Size:")
    print("-" * 40)

    ts = shutil.get_terminal_size()
    print(f"  shutil.get_terminal_size(): {ts.columns} cols x {ts.lines} lines")

    fd = sys.stdin.fileno()
    try:
        winsize = struct.pack('HHHH', 0, 0, 0, 0)
        result = fcntl.ioctl(fd, termios.TIOCGWINSZ, winsize)
        rows, cols, xpixels, ypixels = struct.unpack('HHHH', result)
        print(f"  TIOCGWINSZ ioctl:       {cols} cols x {rows} lines")
        if xpixels and ypixels:
            print(f"  Pixel size:             {xpixels} x {ypixels}")
    except Exception:
        print("  TIOCGWINSZ ioctl:       (failed)")

    print()

def query_device_status():
    """Send Device Status Report and check for response.
    Reference: VT100 User Guide - Device Status Report (DSR)
    https://vt100.net/docs/vt100-ug/chapter3.html#DSR

    Sequence: CSI 6 n — Report Cursor Position
    Response: CSI row ; col R

    This tests if the terminal responds to escape sequence queries.
    """
    print("Escape Sequence Response Test:")
    print("-" * 40)

    fd = sys.stdin.fileno()

    original_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, original_flags | os.O_NONBLOCK)

    sys.stdout.write(CSI + "6n")
    sys.stdout.flush()

    try:
        if select.select([fd], [], [], 2.0)[0]:
            response = os.read(fd, 32).decode('ascii', errors='replace')
            if response.startswith(CSI) and response.endswith('R'):
                print(f"  Response received: {repr(response)}")
                print("  Terminal responds to DSR queries: YES")
            else:
                print(f"  Unexpected response: {repr(response)}")
                print("  Terminal responds: UNCERTAIN")
        else:
            print("  No response within 2 second timeout")
            print("  Terminal may not respond to DSR queries")
            print("  (Some terminals/console modes disable this)")
    except Exception as e:
        print(f"  Error: {e}")
        print("  Escape sequence response: UNKNOWN")
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, original_flags)

    print()

def test_terminal_capabilities():
    """Test various terminal capabilities."""
    print("Terminal Capability Tests:")
    print("-" * 40)

    capabilities = [
        ("Auto-wrap (DECAWM)", CSI + "?7h", CSI + "?7l"),
        ("Cursor visible (DECTCEM)", CSI + "?25h", CSI + "?25l"),
    ]

    for name, enable_seq, disable_seq in capabilities:
        sys.stdout.write(disable_seq)
        sys.stdout.flush()
        print(f"  {name}: DISABLED (sent {enable_seq})")
        sys.stdin.readline()
        sys.stdout.write(enable_seq)
        sys.stdout.flush()
        print(f"  {name}: ENABLED")
        print()

def main():
    clear_screen()
    cursor_home()

    print("Terminal Information and Introspection")
    print("=" * 40)
    print()

    isatty_info()
    term_info()
    get_terminal_size()

    setup_raw_terminal()
    query_device_status()

    print("Press Enter to see capability test...")
    print("(WARNING: Will temporarily disable cursor visibility)")
    sys.stdin.readline()

    test_terminal_capabilities()

    clear_screen()
    cursor_home()
    print("Terminal Info Demo complete!")
    print()
    print("Key functions demonstrated:")
    print("  os.isatty()           — Check if fd is connected to TTY")
    print("  os.environ['TERM']    — Terminal type identifier")
    print("  shutil.get_terminal_size() — Terminal dimensions")
    print("  TIOCGWINSZ ioctl      — Low-level window size query")
    print("  DSR (CSI 6n)          — Device Status Report query")

def clear_screen():
    """Clear entire screen."""
    sys.stdout.write(CSI + "2J")
    sys.stdout.flush()

def cursor_home():
    """Move cursor to home position."""
    sys.stdout.write(CSI + "H")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
