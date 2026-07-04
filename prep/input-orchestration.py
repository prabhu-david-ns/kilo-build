#!/usr/bin/env python3
"""
Editor Input Orchestration State Machine

Demonstrates how a terminal editor routes keyboard input through a state machine:
  - NORMAL state: printable chars get echoed, Ctrl-letters trigger actions
  - ESCAPE_SEQUENCE state: accumulate bytes until a complete control sequence
    matches, then dispatch to an action handler.

References:
  - man 3 termios (termios flags, cfmakeraw)
  - man 4 console_codes (Linux console escape sequences)
  - ECMA-48: https://www.ecma-international.org/publications-and-standards/standards/ecma-48/
  - XTerm Control Sequences: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
  - VT100 User Guide: https://vt100.net/docs/vt100-ug/chapter3.html
"""

import sys
import os
import tty
import termios
import atexit

ESC = 0x1B

STATE_NORMAL = 0
STATE_ESC = 1
STATE_CSI = 2
STATE_SS3 = 3

FD = sys.stdin.fileno()
ORIG_ATTRS = None

CSI_ACTIONS = {
    b'[A': ('UP ARROW', 'cursor up'),
    b'[B': ('DOWN ARROW', 'cursor down'),
    b'[C': ('RIGHT ARROW', 'cursor right'),
    b'[D': ('LEFT ARROW', 'cursor left'),
    b'[H': ('HOME', 'cursor to line start'),
    b'[F': ('END', 'cursor to line end'),
    b'[2~': ('INSERT', 'toggle insert/overwrite'),
    b'[3~': ('DELETE', 'delete char at cursor'),
    b'[5~': ('PAGE UP', 'scroll up one page'),
    b'[6~': ('PAGE DOWN', 'scroll down one page'),
    b'[1~': ('HOME', 'cursor to line start'),
    b'[4~': ('END', 'cursor to line end'),
}

SS3_ACTIONS = {
    b'OP': ('F1', 'user defined action F1'),
    b'OQ': ('F2', 'user defined action F2'),
    b'OR': ('F3', 'user defined action F3'),
    b'OS': ('F4', 'user defined action F4'),
}

def save_and_set_raw():
    """Save terminal attributes and set raw mode.
    Reference: man 3 termios, Python tty.setraw"""
    global ORIG_ATTRS
    ORIG_ATTRS = termios.tcgetattr(FD)
    tty.setraw(FD)

def restore():
    """Restore original terminal attributes.
    Reference: man 3 tcsetattr"""
    if ORIG_ATTRS is not None:
        termios.tcsetattr(FD, termios.TCSADRAIN, ORIG_ATTRS)

def ctrl_name(b):
    """Convert control byte to Ctrl-X name.
    Reference: man 7 ascii"""
    if b == 0x00:
        return 'Ctrl-@'
    if b == 0x1F:
        return 'Ctrl-_'
    return 'Ctrl-' + chr(ord('@') ^ b)

def is_csi_param(b):
    """CSI parameter bytes: 0x30-0x3F (digits 0-9, semicolon, etc.)
    Reference: ECMA-48 section 5.4.1"""
    return 0x30 <= b <= 0x3F

def is_csi_intermediate(b):
    """CSI intermediate bytes: 0x20-0x2F
    Reference: ECMA-48 section 5.4.1"""
    return 0x20 <= b <= 0x2F

def is_csi_final(b):
    """CSI final byte: 0x40-0x7E
    Reference: ECMA-48 section 5.4.1"""
    return 0x40 <= b <= 0x7E

def main():
    atexit.register(restore)

    try:
        save_and_set_raw()
    except termios.error as e:
        print(f"Error: {e} (not a terminal?)", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(
        "Editor Input Orchestration State Machine\r\n"
        "=============================================\r\n"
        "Type text to see insertion simulation.\r\n"
        "Special keys: arrows, Page Up/Down, Home, End, Delete, Insert, F1-F4\r\n"
        "Ctrl-S = save placeholder, Ctrl-Q = quit\r\n"
        "Ctrl-C = interrupt action\r\n"
        "\r\n"
    )
    sys.stdout.flush()

    state = STATE_NORMAL
    escape_buf = bytearray()
    log_lines = []
    MAX_LOG = 100

    def log_action(msg):
        nonlocal log_lines
        log_lines.append(msg)
        if len(log_lines) > MAX_LOG:
            log_lines = log_lines[-MAX_LOG:]

    try:
        while True:
            data = os.read(FD, 1)
            if not data:
                continue
            b = data[0]

            if state == STATE_NORMAL:
                if 0x20 <= b <= 0x7E:
                    ch = chr(b)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    log_action(f"INSERT '{ch}' at cursor")
                    continue

                if b == ESC:
                    state = STATE_ESC
                    escape_buf = bytearray()
                    escape_buf.append(b)
                    log_action("ESC received → starting escape sequence")
                    continue

                if b == 0x03:
                    log_action("Ctrl-C → INTERRUPT signal (SIGINT)")
                    continue

                if b == 0x11:
                    log_action("Ctrl-Q → QUIT")
                    break

                if b == 0x13:
                    log_action("Ctrl-S → SAVE (placeholder)")
                    continue

                if b == 0x1A:
                    log_action("Ctrl-Z → SUSPEND (SIGTSTP)")
                    continue

                if b == 0x0D:
                    log_action("ENTER → newline")
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    continue

                if b == 0x0A:
                    continue

                if b == 0x7F:
                    log_action("BACKSPACE/DEL → delete char before cursor")
                    continue

                if 0x00 <= b <= 0x1F or b == 0x7F:
                    name = ctrl_name(b) if b != 0x7F else 'DEL'
                    log_action(f"{name} → unknown action (ignored)")
                    continue

                log_action(f"UNKNOWN byte 0x{b:02X} → ignored")
                continue

            elif state == STATE_ESC:
                if b == ord('['):
                    state = STATE_CSI
                    escape_buf.append(b)
                    log_action("ESC [ → CSI sequence started")
                elif b == ord('O'):
                    state = STATE_SS3
                    escape_buf.append(b)
                    log_action("ESC O → SS3 sequence started")
                elif b == ESC:
                    log_action("ESC ESC → two ESC in a row")
                    escape_buf = bytearray()
                    escape_buf.append(b)
                else:
                    log_action(f"ESC {chr(b) if 0x20 <= b <= 0x7E else hex(b)} → unrecognized")
                    state = STATE_NORMAL
                continue

            elif state == STATE_CSI:
                escape_buf.append(b)
                if is_csi_param(b):
                    log_lines.append(f"  CSI param byte: 0x{b:02X} ('{chr(b) if 0x20 <= b <= 0x7E else '?'}')")
                    continue
                if is_csi_intermediate(b):
                    log_lines.append(f"  CSI intermediate byte: 0x{b:02X}")
                    continue
                if is_csi_final(b):
                    seq = bytes(escape_buf)
                    if seq in CSI_ACTIONS:
                        key_name, action = CSI_ACTIONS[seq]
                        log_action(f"CSI {seq[1:].decode()} → {key_name} → {action}")
                    else:
                        log_action(f"CSI sequence: {' '.join(f'{x:02X}' for x in seq)} → unknown dispatch")
                    state = STATE_NORMAL
                    escape_buf = bytearray()
                    continue
                log_action(f"ESC [ ... unexpected byte 0x{b:02X} → reset")
                state = STATE_NORMAL
                escape_buf = bytearray()
                continue

            elif state == STATE_SS3:
                escape_buf.append(b)
                seq = bytes(escape_buf)
                if seq in SS3_ACTIONS:
                    key_name, action = SS3_ACTIONS[seq]
                    log_action(f"SS3 {seq[1:].decode()} → {key_name} → {action}")
                else:
                    log_action(f"SS3 sequence: {' '.join(f'{x:02X}' for x in seq)} → unknown dispatch")
                state = STATE_NORMAL
                escape_buf = bytearray()
                continue

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        restore()

    print()
    print()
    print("=" * 50)
    print("Session Log")
    print("=" * 50)
    for line in log_lines:
        print(line)
    print("=" * 50)

if __name__ == '__main__':
    main()
