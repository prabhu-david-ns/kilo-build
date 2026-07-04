#!/usr/bin/env python3
"""
Terminal Key Classifier

Demonstrates classification of keyboard input in a terminal editor context.
Reads bytes from stdin in raw mode and classifies each input into:
  - Printable ASCII
  - Ctrl-letter
  - Escape sequence start (ESC)
  - Multi-byte escape sequence (arrow keys, function keys, etc.)
  - Unknown

References:
  - man 3 termios (termios flags, cfmakeraw, VMIN/VTIME)
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

CSI_SEQUENCES = {
    b'[A': 'Up arrow',
    b'[B': 'Down arrow',
    b'[C': 'Right arrow',
    b'[D': 'Left arrow',
    b'[H': 'Home',
    b'[F': 'End',
    b'[2~': 'Insert',
    b'[3~': 'Delete',
    b'[5~': 'Page Up',
    b'[6~': 'Page Down',
    b'[7~': 'Home',
    b'[8~': 'End',
    b'[1~': 'Home',
    b'[4~': 'End',
}

SS3_SEQUENCES = {
    b'OP': 'F1',
    b'OQ': 'F2',
    b'OR': 'F3',
    b'OS': 'F4',
}

FD = sys.stdin.fileno()
ORIG_ATTRS = None

def save_and_set_raw():
    """Save terminal attributes and set raw mode using the termios module.
    Reference: man 3 termios, Python tty module source (tty.setraw)"""
    global ORIG_ATTRS
    ORIG_ATTRS = termios.tcgetattr(FD)
    tty.setraw(FD)

def restore():
    """Restore original terminal attributes.
    Reference: man 3 tcsetattr"""
    if ORIG_ATTRS is not None:
        termios.tcsetattr(FD, termios.TCSADRAIN, ORIG_ATTRS)

def classify_printable(b):
    """Check if byte is a printable ASCII character (0x20-0x7E).
    Reference: man 7 ascii"""
    return 0x20 <= b <= 0x7E

def classify_ctrl(b):
    """Check if byte is a Ctrl-letter code (0x00-0x1F, except 0x1B which is ESC).
    Ctrl-A = 0x01, Ctrl-B = 0x02, ..., Ctrl-Z = 0x1A
    Ctrl-[ = 0x1B (ESC), Ctrl-\ = 0x1C, Ctrl-] = 0x1D, Ctrl-^ = 0x1E, Ctrl-_ = 0x1F
    Ctrl-@ (null) = 0x00, Ctrl-? (DEL) = 0x7F
    Reference: man 7 ascii"""
    return (0x00 <= b <= 0x1F and b != 0x1B)

def ctrl_to_name(b):
    """Convert a control byte to its Ctrl-X name."""
    if b == 0x00:
        return 'Ctrl-@'
    if b == 0x1F:
        return 'Ctrl-_'
    return 'Ctrl-' + chr(ord('@') ^ b)

def read_escape_sequence():
    """Read bytes after an initial ESC (0x1B) to identify a complete escape sequence.
    Follows ECMA-48 state machine rules for control sequence parsing.

    1. Check for CSI (ESC [) or SS3 (ESC O) sequences
    2. Accumulate parameter bytes (0x30-0x3F) and intermediate bytes (0x20-0x2F)
    3. Final byte (0x40-0x7E) terminates the sequence

    Reference: ECMA-48 section 5.4, XTerm Control Sequences"""
    buf = os.read(FD, 1)
    if not buf:
        return b'', ESCAPE_NONE

    seq = buf
    cp1252_final_allowed = [0x80, 0x90, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F]
    cp1252_intermediate_allowed = list(range(0x80, 0xA0))
    cp1252_param_allowed = list(range(0x80, 0xA0))

    if seq == b'[':
        return _read_csi_sequence()
    elif seq == b'O':
        return _read_ss3_sequence()
    else:
        return seq, ESCAPE_UNKNOWN

ESCAPE_NONE = 0
ESCAPE_CSI = 1
ESCAPE_SS3 = 2
ESCAPE_UNKNOWN = 3

def _read_csi_sequence():
    """Read a CSI sequence: ESC [ params... intermediate... final_byte
    Parameter bytes: 0x30-0x3F (digits, semicolon, etc.)
    Intermediate bytes: 0x20-0x2F
    Final byte: 0x40-0x7E
    Reference: ECMA-48 section 5.4.1"""
    buf = b'['
    while True:
        byte_data = os.read(FD, 1)
        if not byte_data:
            break
        b = byte_data[0]
        buf += byte_data
        if 0x40 <= b <= 0x7E:
            break
        elif 0x20 <= b <= 0x2F:
            continue
        elif 0x30 <= b <= 0x3F:
            continue
        elif 0x80 <= b <= 0x9F:
            buf = buf[:-1]
            buf += bytes([b & 0x7F])
            if 0x40 <= (b & 0x7F) <= 0x7E:
                break
            elif 0x20 <= (b & 0x7F) <= 0x2F:
                continue
            elif 0x30 <= (b & 0x7F) <= 0x3F:
                continue
            else:
                buf = b'\x1b' + buf
                buf += byte_data
                break
        else:
            break
    if buf in CSI_SEQUENCES:
        return buf, ESCAPE_CSI
    return buf, ESCAPE_CSI

def _read_ss3_sequence():
    """Read an SS3 sequence: ESC O final_byte
    Typically used for F1-F4 and application keypad keys.
    Reference: XTerm Control Sequences, VT220"""
    buf = b'O'
    byte_data = os.read(FD, 1)
    if byte_data:
        buf += byte_data
    if buf in SS3_SEQUENCES:
        return buf, ESCAPE_SS3
    return buf, ESCAPE_SS3

def classify_and_display(buf, seq_type, raw_bytes):
    """Display the classification of received input."""
    hex_str = ' '.join(f'{b:02X}' for b in raw_bytes)

    if seq_type == ESCAPE_CSI:
        name = CSI_SEQUENCES.get(buf, 'unknown CSI')
        print(f"  Multi-byte escape: {name}  |  raw: {hex_str}")
    elif seq_type == ESCAPE_SS3:
        name = SS3_SEQUENCES.get(buf, 'unknown SS3')
        print(f"  Multi-byte escape: {name}  |  raw: {hex_str}")
    elif seq_type == ESCAPE_UNKNOWN:
        print(f"  Escape prefix + unknown: {hex_str}")
    else:
        print(f"  Unknown: {hex_str}")

def main():
    atexit.register(restore)

    try:
        save_and_set_raw()
    except termios.error as e:
        print(f"Error setting raw mode (not a terminal?): {e}", file=sys.stderr)
        sys.exit(1)

    print("Key Classifier Demo")
    print("=" * 50)
    print("Press keys to see their classification.")
    print("Press 'q' or Ctrl-C to exit.")
    print()

    try:
        while True:
            data = os.read(FD, 1)
            if not data:
                continue

            b = data[0]
            raw_bytes = data

            if classify_printable(b):
                ch = chr(b)
                print(f"  Printable ASCII: '{ch}'  |  hex: {b:02X}")
                if ch == 'q':
                    print()
                    print("'q' pressed — exiting.")
                    break

            elif classify_ctrl(b):
                name = ctrl_to_name(b)
                print(f"  Ctrl character: {name:<8}  |  hex: {b:02X}")
                if b == 0x03:
                    print("  (Ctrl-C — interrupt)")
                    break

            elif b == 0x1B:
                seq, stype = read_escape_sequence()
                if seq:
                    raw = b'\x1b' + seq
                    classify_and_display(seq, stype, raw)
                else:
                    print(f"  Escape (ESC) key  |  hex: 1B")

            elif b == 0x7F:
                print(f"  Delete (DEL)      |  hex: 7F")

            else:
                print(f"  Unknown byte       |  hex: {b:02X}")

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        restore()

if __name__ == '__main__':
    main()
