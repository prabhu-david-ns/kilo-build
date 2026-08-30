/*
 * tedit — a dependency-free VT100 terminal text/code editor.
 *
 * Rebuilt EXCLUSIVELY from the knowledge captured in prep/ (the build's own
 * specs 01-03 research). Every technique traces back to a prep/ file, cited
 * inline. No external knowledge was used; anything extended beyond prep/ is
 * marked "designed from prep/ primitives".
 */
#define _POSIX_C_SOURCE 200809L  /* strdup, getline under -std=c11 */

#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

/* ------------------------------------------------------------------ */
/* Terminal raw mode                                                   */
/* ------------------------------------------------------------------ */
/*
 * Raw mode: clear ICANON (no line buffering), ECHO (no automatic echo),
 * ISIG (no signal generation from Ctrl-C/Ctrl-Z), IXON/IXOFF (no flow
 * control), OPOST (output passes through unmodified). All derived from the
 * cfmakeraw flag list in prep/flow.md section 3.3 and the cooked-vs-raw
 * discussion in prep/flow.md sections 3.2-3.4.
 */
static struct termios g_orig_termios;
static int g_raw_mode_active = 0;

static void editor_cleanup(void);   /* defined with the render section */

static void termios_restore(void) {
    if (g_raw_mode_active) {
        /* TCSADRAIN: wait for output to drain before restoring — the
         * tcsetattr action constant prep/flow.md section 3.4. */
        tcsetattr(STDIN_FILENO, TCSADRAIN, &g_orig_termios);
        g_raw_mode_active = 0;
    }
}

static void termios_restore_and_exit(int sig) {
    /* Signal paths (SIGINT/SIGTERM) must also restore the terminal.
     * Designed from prep/ primitives: prep/input-orchestration.py and
     * prep/key-classifier.py both restore in a `finally` / atexit path; here
     * we additionally hook external signals so the restore is guaranteed. */
    (void)sig;
    editor_cleanup();
    termios_restore();
    _exit(128 + sig);
}

static int termios_enable_raw(void) {
    /* Save the current attributes, then set raw mode using the exact flag
     * set documented in prep/flow.md section 3.3 (cfmakeraw). */
    if (tcgetattr(STDIN_FILENO, &g_orig_termios) == -1) return -1;
    struct termios raw = g_orig_termios;
    raw.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR |
                     ICRNL | IXON);
    raw.c_oflag &= ~OPOST;
    raw.c_lflag &= ~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
    raw.c_cflag &= ~(CSIZE | PARENB);
    raw.c_cflag |= CS8;
    /* VMIN/VTIME: blocking single-byte reads — prep/flow.md section 4.2. */
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;
    if (tcsetattr(STDIN_FILENO, TCSANOW, &raw) == -1) return -1;
    g_raw_mode_active = 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* Key reading                                                         */
/* ------------------------------------------------------------------ */
/*
 * Key classification derived from prep/key-classifier.py and the input
 * state machine in prep/input-orchestration.py: printable ASCII 0x20-0x7E,
 * control bytes 0x00-0x1F (Ctrl-letter), 0x7F = Backspace, ESC starts a
 * multi-byte CSI (ESC [) or SS3 (ESC O) sequence. ECMA-48 byte classes for
 * CSI parsing (parameter/intermediate/final) come from prep/key-classifier.py
 * `_read_csi_sequence` and prep/input-orchestration.py `is_csi_*`.
 */
enum KeyType {
    KEY_NONE = 0,
    KEY_PRINTABLE,      /* key.ch set */
    KEY_CTRL,           /* key.ch set to the control byte */
    KEY_ENTER,
    KEY_BACKSPACE,      /* DEL 0x7F */
    KEY_ESC,            /* bare ESC */
    KEY_UP, KEY_DOWN, KEY_RIGHT, KEY_LEFT,
    KEY_HOME, KEY_END,
    KEY_PAGE_UP, KEY_PAGE_DOWN,
    KEY_DELETE,
    KEY_UNKNOWN
};

struct Key { enum KeyType type; char ch; };

static int is_csi_param(unsigned char b) { return 0x30 <= b && b <= 0x3F; }
static int is_csi_intermediate(unsigned char b) { return 0x20 <= b && b <= 0x2F; }
static int is_csi_final(unsigned char b) { return 0x40 <= b && b <= 0x7E; }

static char read_byte(void) {
    /* Single-byte blocking read — the whole pipeline is prep/flow.md
     * section 4: terminal -> PTY -> n_tty -> read(). VMIN=1 makes this
     * block until one byte arrives (prep/flow.md section 4.2). */
    char c;
    ssize_t n;
    while ((n = read(STDIN_FILENO, &c, 1)) == -1 && errno == EINTR) {}
    if (n <= 0) return 0;
    return c;
}

static struct Key read_key(void) {
    struct Key key = { KEY_NONE, 0 };
    char c = read_byte();

    if (c >= 0x20 && c <= 0x7E) {
        /* Printable ASCII — prep/key-classifier.py `classify_printable`. */
        key.type = KEY_PRINTABLE;
        key.ch = c;
        return key;
    }
    if (c == 0x1B) {
        /* ESC: either the ESC key or the start of a CSI/SS3 sequence —
         * prep/key-classifier.py `read_escape_sequence`. */
        char c2 = read_byte();
        if (c2 == '[') {
            /* CSI: accumulate param (0x30-0x3F) and intermediate (0x20-0x2F)
             * bytes until a final byte (0x40-0x7E). ECMA-48 state machine as
             * in prep/key-classifier.py `_read_csi_sequence`. */
            char buf[8];
            int len = 0;
            buf[len++] = c2;
            for (;;) {
                char b = read_byte();
                buf[len++] = b;
                if (len >= (int)sizeof(buf)) break;
                if (is_csi_final((unsigned char)b)) break;
                if (is_csi_param((unsigned char)b) ||
                    is_csi_intermediate((unsigned char)b)) continue;
                break; /* unexpected byte — abort the sequence */
            }
            /* Table of recognized CSI sequences — prep/key-classifier.py
             * CSI_SEQUENCES. */
            if (len == 2 && buf[1] == 'A') key.type = KEY_UP;
            else if (len == 2 && buf[1] == 'B') key.type = KEY_DOWN;
            else if (len == 2 && buf[1] == 'C') key.type = KEY_RIGHT;
            else if (len == 2 && buf[1] == 'D') key.type = KEY_LEFT;
            else if (len == 2 && buf[1] == 'H') key.type = KEY_HOME;
            else if (len == 2 && buf[1] == 'F') key.type = KEY_END;
            else if (len == 3 && buf[1] == '1' && buf[2] == '~') key.type = KEY_HOME;
            else if (len == 3 && buf[1] == '4' && buf[2] == '~') key.type = KEY_END;
            else if (len == 3 && buf[1] == '3' && buf[2] == '~') key.type = KEY_DELETE;
            else if (len == 3 && buf[1] == '5' && buf[2] == '~') key.type = KEY_PAGE_UP;
            else if (len == 3 && buf[1] == '6' && buf[2] == '~') key.type = KEY_PAGE_DOWN;
            else key.type = KEY_UNKNOWN;
            return key;
        }
        if (c2 == 'O') {
            /* SS3 sequences (F-keys) — prep/key-classifier.py
             * `_read_ss3_sequence`; not used by the editor, map to unknown. */
            (void)read_byte();
            key.type = KEY_UNKNOWN;
            return key;
        }
        key.type = KEY_ESC;
        return key;
    }
    if (c == 0x0D || c == 0x0A) {
        /* Enter arrives as CR (0x0D) in raw mode — prep/input-orchestration.py
         * handles 0x0D as ENTER and skips the trailing 0x0A. */
        key.type = KEY_ENTER;
        return key;
    }
    if (c == 0x7F) {
        key.type = KEY_BACKSPACE;
        return key;
    }
    if (c >= 0x00 && c <= 0x1F) {
        key.type = KEY_CTRL;
        key.ch = c;
        return key;
    }
    key.type = KEY_UNKNOWN;
    return key;
}

/* ------------------------------------------------------------------ */
/* Append buffer                                                       */
/* ------------------------------------------------------------------ */
/*
 * The whole frame is composed in memory, then written with ONE write().
 * Rationale: building clear + cursor home + all rows + cursor placement as a
 * single string prevents the terminal from painting partial frames.
 * Derived from prep/game-of-life.py `compose_frame` and its cited flicker
 * argument ("prepare the entire content in a single string and then print it
 * all at once ... instead of a partially written one").
 */
typedef struct {
    char *b;
    int len;
} ABuf;

static void ab_append(ABuf *ab, const char *s, int len) {
    char *nb = realloc(ab->b, ab->len + len);
    if (nb == NULL) return;
    memcpy(nb + ab->len, s, len);
    ab->b = nb;
    ab->len += len;
}

static void ab_append_str(ABuf *ab, const char *s) {
    ab_append(ab, s, (int)strlen(s));
}

static void ab_appendf(ABuf *ab, const char *fmt, ...) {
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    int len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (len > (int)sizeof(buf)) len = (int)sizeof(buf);
    ab_append(ab, buf, len);
}

/* ------------------------------------------------------------------ */
/* Escape sequences and SGR styles (every one demonstrated in prep/)   */
/* ------------------------------------------------------------------ */
/* ED erase-in-display / CUP cursor-home / DECTCEM cursor visibility /
 * DECAWM auto-wrap: prep/clear-screen.py, prep/cursor-move.py,
 * prep/game-of-life.py esc_* helpers. SGR palette: prep/colors.py
 * (CSI 30-37m, CSI 40-47m, CSI 1;30-37m, CSI 38;5;Nm, CSI 0m) and the
 * bold-bright style form "1;9xm" used by prep/game-of-life.py. */
#define SEQ_CLEAR   "\x1b[2J"      /* ED clear screen   (prep/clear-screen.py) */
#define SEQ_HOME    "\x1b[H"       /* CUP home          (prep/cursor-move.py) */
#define SEQ_HIDE    "\x1b[?25l"    /* DECTCEM hide      (prep/game-of-life.py) */
#define SEQ_SHOW    "\x1b[?25h"    /* DECTCEM show      (prep/game-of-life.py) */
#define SEQ_WRAP_OFF "\x1b[?7l"    /* DECAWM off        (prep/clear-screen.py) */
#define SEQ_WRAP_ON  "\x1b[?7h"    /* DECAWM on         (prep/clear-screen.py) */

#define SGR_RESET   "\x1b[0m"      /* reset all (prep/colors.py sgr_reset) */
#define SGR_STATUS  "\x1b[37;44m"  /* white fg / blue bg status bar (prep/colors.py) */
#define SGR_MSG     "\x1b[1;36m"   /* bold bright cyan message bar (prep/game-of-life.py) */
#define SGR_KW      "\x1b[1;31m"   /* bold bright red keywords (prep/game-of-life.py) */
#define SGR_TYPE    "\x1b[33m"     /* yellow types (prep/colors.py) */
#define SGR_NUM     "\x1b[32m"     /* green numbers (prep/colors.py) */
#define SGR_STR     "\x1b[95m"     /* bright magenta strings (prep/game-of-life.py) */
#define SGR_CMT     "\x1b[34m"     /* blue comments (prep/colors.py) */
#define SGR_MATCH   "\x1b[30;43m"  /* black on yellow find match (prep/colors.py) */

/* ------------------------------------------------------------------ */
/* Terminal size query                                                 */
/* ------------------------------------------------------------------ */
/* TIOCGWINSZ ioctl returns struct winsize {ws_row, ws_col, ...} —
 * prep/viewport.py `get_terminal_size_ioctl` / prep/terminal-viewport-combined.py
 * `get_terminal_size_ioctl`. Re-queried at every full refresh so a resize is
 * picked up on the next frame. */
static void editor_query_size(int *rows, int *cols) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == -1 || ws.ws_col == 0) {
        *cols = 80;
        *rows = 24;
    } else {
        *cols = ws.ws_col;
        *rows = ws.ws_row;
    }
}

/* ------------------------------------------------------------------ */
/* Row model                                                           */
/* ------------------------------------------------------------------ */
/*
 * A file row is stored as its CANONICAL bytes only (chars/len) — real tab
 * bytes included — so saving writes back exactly what was read. What gets
 * drawn is a separate, derived render string with tabs expanded to spaces.
 * This separation is motivated by the display pipeline of prep/flow.md
 * (section 5-6: raw bytes in, rendered cells out) and by the render math in
 * prep/clear-screen.py / prep/cursor-move.py (the terminal is a fixed cell
 * grid addressed in display columns, not in file bytes). The expansion is
 * done per-row at render time and never mutates the canonical row.
 */
#define TAB_STOP 8

typedef struct {
    char *chars;    /* canonical bytes of the row (tabs kept as \t) */
    int len;
    int *hl;        /* syntax highlight colour set, per rendered column */
    int hl_len;
} erow;

struct editor {
    erow *row;
    int numrows;
    int cx, cy;         /* cursor: cx = char index in row, cy = row index */
    int rowoff;         /* first row visible on screen */
    int coloff;         /* first display column visible on screen */
    int screenrows;
    int screencols;
    int dirty;
    char *filename;
    char statusmsg[80];
    int quit_confirmed; /* dirty-quit confirmation (see save/quit) */
    /* find state */
    char search[256];
    int search_active;
    int search_len;
    /* syntax */
    int in_comment;     /* multi-line comment state carried between rows */
};

static struct editor E;

static void editor_set_message(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(E.statusmsg, sizeof(E.statusmsg), fmt, ap);
    va_end(ap);
}

/* Row operations ------------------------------------------------------ */

static void erow_free(erow *r) {
    free(r->chars);
    free(r->hl);
    r->chars = NULL;
    r->hl = NULL;
    r->len = r->hl_len = 0;
}

static void erow_insert(erow *r, int at, char c) {
    r->chars = realloc(r->chars, r->len + 2);
    if (at < 0 || at > r->len) at = r->len;
    memmove(r->chars + at + 1, r->chars + at, r->len - at);
    r->chars[at] = c;
    r->len++;
}

static void erow_delete_range(erow *r, int at, int count) {
    if (count < 0) count = 0;
    if (at < 0) at = 0;
    if (at > r->len) return;
    if (count > r->len - at) count = r->len - at;
    memmove(r->chars + at, r->chars + at + count, r->len - at - count);
    r->len -= count;
}

/* Row render: expand tabs to spaces up to the next TAB_STOP boundary.
 * Returns a malloc'd string. Designed from prep/ primitives: the row model
 * separation (flow.md pipeline) + terminal cell-grid math (prep/cursor-move.py). */
static char *erow_render(erow *r, int *out_len) {
    char *dst = malloc(r->len * 8 + 1); /* worst case: every byte a tab */
    int j = 0;
    for (int i = 0; i < r->len; i++) {
        if (r->chars[i] == '\t') {
            int spaces = TAB_STOP - (j % TAB_STOP);
            for (int s = 0; s < spaces; s++) dst[j++] = ' ';
        } else {
            dst[j++] = r->chars[i];
        }
    }
    dst[j] = '\0';
    *out_len = j;
    return dst;
}

/* Display column of char index cx (tab-aware). */
static int erow_rx(erow *r, int cx) {
    int col = 0;
    for (int i = 0; i < cx && i < r->len; i++) {
        if (r->chars[i] == '\t') col += TAB_STOP - (col % TAB_STOP);
        else col++;
    }
    return col;
}

/* ------------------------------------------------------------------ */
/* File load                                                           */
/* ------------------------------------------------------------------ */
static void editor_open(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (fp == NULL) {
        E.filename = strdup(path);
        return;
    }
    E.filename = strdup(path);
    char *line = NULL;
    size_t cap = 0;
    ssize_t n;
    while ((n = getline(&line, &cap, fp)) != -1) {
        while (n > 0 && (line[n - 1] == '\n' || line[n - 1] == '\r')) n--;
        E.row = realloc(E.row, sizeof(erow) * (E.numrows + 1));
        erow *r = &E.row[E.numrows];
        memset(r, 0, sizeof(*r));
        r->chars = malloc(n + 1);
        memcpy(r->chars, line, n);
        r->chars[n] = '\0';
        r->len = n;
        E.numrows++;
    }
    free(line);
    fclose(fp);
}

/* ------------------------------------------------------------------ */
/* Syntax highlighting                                                 */
/* ------------------------------------------------------------------ */
/*
 * Per-row scanning: each row gets an `hl` array indexed by RENDERED column
 * (the same space the render string lives in), filled by a byte scan of the
 * canonical row. Multi-line block-comment state is carried between rows by
 * `E.in_comment`, set while scanning row N and consumed as the start state
 * of row N+1. Every colour below is an SGR from prep/colors.py /
 * prep/game-of-life.py (see the style #defines above).
 */
enum HL { HL_NONE = 0, HL_KW, HL_TYPE, HL_NUM, HL_STR, HL_CMT, HL_MATCH };

static const char *hl_sgr(enum HL h) {
    switch (h) {
    case HL_KW: return SGR_KW;
    case HL_TYPE: return SGR_TYPE;
    case HL_NUM: return SGR_NUM;
    case HL_STR: return SGR_STR;
    case HL_CMT: return SGR_CMT;
    case HL_MATCH: return SGR_MATCH;
    default: return NULL;
    }
}

static const char *C_KEYWORDS[] = {
    "auto", "break", "case", "const", "continue", "default", "do", "else",
    "enum", "extern", "for", "goto", "if", "inline", "register", "return",
    "sizeof", "static", "struct", "switch", "typedef", "union", "volatile",
    "while", NULL
};

static const char *C_TYPES[] = {
    "bool", "char", "double", "float", "int", "long", "short", "signed",
    "size_t", "ssize_t", "unsigned", "void", "FILE", NULL
};

static int is_sep(char c) {
    return c == ' ' || c == '\t' || c == ';' || c == '(' || c == ')' ||
           c == '{' || c == '}' || c == '[' || c == ']' || c == ',' ||
           c == '+' || c == '-' || c == '*' || c == '/' || c == '=' ||
           c == '<' || c == '>' || c == '&' || c == '|' || c == '!' ||
           c == '~' || c == '%' || c == '^' || c == '"' || c == '\'' ||
           c == ':' || c == '?';
}

static int is_digit(char c) { return c >= '0' && c <= '9'; }
static int is_ident(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}
static int is_alnum(char c) { return is_ident(c) || is_digit(c); }

static int list_contains(const char **list, const char *s, int len) {
    for (int i = 0; list[i] != NULL; i++) {
        if ((int)strlen(list[i]) == len && strncmp(list[i], s, len) == 0)
            return 1;
    }
    return 0;
}

static void editor_find_highlight(const char *needle, int nlen);

/* Recompute the highlight array for every row. Multi-line comments: the
 * `in_comment` flag in the editor survives the loop, so a block comment
 * started on one row colours the following rows until the matching closer
 * (designed from prep/ primitives: the per-row display state model in
 * prep/flow.md §5-6 and the frame row-by-row composition in
 * prep/game-of-life.py). */
static void editor_update_syntax(void) {
    for (int i = 0; i < E.numrows; i++) {
        erow *r = &E.row[i];
        free(r->hl);
        r->hl = NULL;
        r->hl_len = 0;

        char *render = erow_render(r, &r->hl_len);
        r->hl = calloc(r->hl_len ? r->hl_len : 1, sizeof(int));

        int in_comment = E.in_comment;   /* state carried from previous row */
        int in_string = 0;
        int prev_sep = 1;                /* identifier boundary detection */
        int col = 0;                     /* rendered column of byte i */

        for (int i2 = 0; i2 < r->len; i2++) {
            char c = r->chars[i2];
            int w = (c == '\t') ? TAB_STOP - (col % TAB_STOP) : 1;
            int hc = HL_NONE;

            if (in_comment) hc = HL_CMT;
            else if (in_string) hc = HL_STR;

            if (!in_comment) {
                if (in_string) {
                    if (c == '\\') {
                        /* escaped char: colour the pair, skip the next byte */
                        if (i2 + 1 < r->len) {
                            hc = HL_STR;
                            for (int k = 0; k < w; k++) r->hl[col + k] = hc;
                            col += w;
                            i2++;
                            w = 1;
                            for (int k = 0; k < w && col + k < r->hl_len; k++)
                                r->hl[col + k] = HL_STR;
                            col += w;
                            continue;
                        }
                    } else if (c == '"') {
                        in_string = 0;
                    }
                } else if (c == '/' && i2 + 1 < r->len &&
                           r->chars[i2 + 1] == '/') {
                    /* // line comment: colour the rest of the row */
                    hc = HL_CMT;
                    for (int k = 0; k < w; k++) r->hl[col + k] = hc;
                    col += w;
                    while (i2 + 1 < r->len) {
                        i2++;
                        w = (r->chars[i2] == '\t')
                                ? TAB_STOP - (col % TAB_STOP) : 1;
                        for (int k = 0; k < w && col + k < r->hl_len; k++)
                            r->hl[col + k] = HL_CMT;
                        col += w;
                    }
                    break;
                } else if (c == '/' && i2 + 1 < r->len &&
                           r->chars[i2 + 1] == '*') {
                    in_comment = 1;
                    hc = HL_CMT;
                } else if (c == '"') {
                    in_string = 1;
                    hc = HL_STR;
                } else if (is_digit(c)) {
                    hc = HL_NUM;
                    while (i2 + 1 < r->len && is_alnum(r->chars[i2 + 1])) {
                        i2++;
                        w = (r->chars[i2] == '\t')
                                ? TAB_STOP - (col % TAB_STOP) : 1;
                        for (int k = 0; k < w && col + k < r->hl_len; k++)
                            r->hl[col + k] = HL_NUM;
                        col += w;
                    }
                } else if (is_ident(c) && prev_sep) {
                    int start = i2;
                    int end = i2;
                    while (end + 1 < r->len && is_alnum(r->chars[end + 1]))
                        end++;
                    if (list_contains(C_KEYWORDS, r->chars + start,
                                      end - start + 1))
                        hc = HL_KW;
                    else if (list_contains(C_TYPES, r->chars + start,
                                           end - start + 1))
                        hc = HL_TYPE;
                    i2 = end;
                    w = end - start + 1;   /* identifier has no tabs */
                }
            } else {
                if (c == '*' && i2 + 1 < r->len &&
                    r->chars[i2 + 1] == '/') {
                    in_comment = 0;
                    hc = HL_CMT;
                    i2++;
                    w++;
                }
            }

            for (int k = 0; k < w && col + k < r->hl_len; k++)
                r->hl[col + k] = hc;
            col += w;
            prev_sep = is_sep(c);
        }
        E.in_comment = in_comment;   /* carry multi-line comment to next row */
        free(render);
    }
    if (E.search_active)            /* find matches overlay the syntax colours */
        editor_find_highlight(E.search, E.search_len);
}

/* Overlay find-match highlighting on top of the syntax colours. Searches the
 * canonical bytes; a match's rendered columns get HL_MATCH. */
static void editor_find_highlight(const char *needle, int nlen) {
    if (nlen <= 0) return;
    for (int i = 0; i < E.numrows; i++) {
        erow *r = &E.row[i];
        for (int pos = 0; pos + nlen <= r->len; pos++) {
            if (strncmp(r->chars + pos, needle, nlen) != 0) continue;
            int startcol = erow_rx(r, pos);
            int endcol = erow_rx(r, pos + nlen);
            for (int c = startcol; c < endcol && c < r->hl_len; c++)
                r->hl[c] = HL_MATCH;
            pos += nlen - 1;
        }
    }
}

/* ------------------------------------------------------------------ */
/* Viewport scrolling                                                  */
/* ------------------------------------------------------------------ */
/* Vertical and horizontal scroll keep the cursor on screen; the math is
 * derived from prep/viewport.py / prep/terminal-viewport-combined.py
 * (cursor/row-clamping to the terminal cell grid) — any cursor position is
 * reachable because the offsets move with the cursor. */
static void editor_scroll(void) {
    if (E.cy < E.rowoff) E.rowoff = E.cy;
    if (E.cy >= E.rowoff + E.screenrows) E.rowoff = E.cy - E.screenrows + 1;
    int rx = erow_rx(&E.row[E.cy], E.cx);
    if (rx < E.coloff) E.coloff = rx;
    if (rx >= E.coloff + E.screencols) E.coloff = rx - E.screencols + 1;
    if (E.coloff < 0) E.coloff = 0;
}

/* ------------------------------------------------------------------ */
/* Frame composition + refresh                                         */
/* ------------------------------------------------------------------ */
static void editor_draw_rows(ABuf *ab) {
    for (int y = 0; y < E.screenrows; y++) {
        int filerow = y + E.rowoff;
        if (filerow >= E.numrows) {
            ab_append_str(ab, "~");
            for (int c = 1; c < E.screencols; c++) ab_append_str(ab, " ");
        } else {
            erow *r = &E.row[filerow];
            int rlen;
            char *render = erow_render(r, &rlen);
            enum HL last_hl = HL_NONE;
            int drawn = 0;
            for (int c = E.coloff; c < E.coloff + E.screencols; c++) {
                if (c >= rlen) break;
                enum HL h = (c < r->hl_len) ? (enum HL)r->hl[c] : HL_NONE;
                if (h != last_hl) {
                    const char *sg = hl_sgr(h);
                    if (sg) ab_append_str(ab, sg);
                    else ab_append_str(ab, SGR_RESET);
                    last_hl = h;
                }
                ab_append(ab, &render[c], 1);
                drawn++;
            }
            if (last_hl != HL_NONE) ab_append_str(ab, SGR_RESET);
            for (int c = drawn; c < E.screencols; c++) ab_append_str(ab, " ");
            free(render);
        }
        /* Raw mode cleared OPOST, so plain \n would not return the column;
         * emit \r\n explicitly — the pattern used by
         * prep/input-orchestration.py under raw mode. */
        ab_append_str(ab, "\r\n");
    }
}

static void editor_draw_status_bar(ABuf *ab) {
    ab_append_str(ab, SGR_STATUS);
    char left[64];
    int percent = E.numrows ? (E.rowoff + E.screenrows) * 100 / E.numrows : 100;
    if (percent > 100) percent = 100;
    int l = snprintf(left, sizeof(left), "%s | %s | %d:%d",
                     E.filename ? E.filename : "[no name]",
                     E.dirty ? "modified" : "saved",
                     E.cy + 1, E.cx + 1);
    if (l > E.screencols) l = E.screencols;
    ab_append(ab, left, l);
    int used = l;
    int pr = snprintf(NULL, 0, "%d%%", percent);
    int right = E.screencols - pr;
    for (int c = used; c < right && c < E.screencols; c++)
        ab_append_str(ab, " ");
    char pbuf[16];
    int pl = snprintf(pbuf, sizeof(pbuf), "%d%%", percent);
    ab_append(ab, pbuf, pl);
    ab_append_str(ab, SGR_RESET);
    ab_append_str(ab, "\r\n");
}

static void editor_draw_message_bar(ABuf *ab) {
    ab_append_str(ab, SGR_MSG);
    char msg[E.screencols + 1];
    int n;
    if (E.search_active) {
        n = snprintf(msg, sizeof(msg), "Search: %s", E.search);
    } else if (E.statusmsg[0] != '\0') {
        n = snprintf(msg, sizeof(msg), "%s", E.statusmsg);
    } else {
        n = snprintf(msg, sizeof(msg),
                     "Ctrl-S save | Ctrl-F find | Ctrl-Q quit");
    }
    if (n < 0) n = 0;
    for (int c = n; c < E.screencols; c++) {
        if (c >= (int)sizeof(msg) - 1) break;
        msg[c] = ' ';
    }
    int m = n < E.screencols ? E.screencols : n;
    if (m > (int)sizeof(msg) - 1) m = sizeof(msg) - 1;
    ab_append(ab, msg, m);
    ab_append_str(ab, SGR_RESET);
    /* NO trailing \r\n on the last row: the frame fills the whole terminal
     * height, so a final line feed would push the cursor onto a scrollback
     * line and the terminal would scroll the entire frame up by one,
     * dropping the first row. The frame ends with an explicit CUP to the
     * edit point instead (designed from prep/cursor-move.py absolute
     * positioning). */
}

static void editor_refresh(void) {
    editor_query_size(&E.screenrows, &E.screencols);
    E.screenrows -= 2;                 /* status bar + message bar */
    if (E.screenrows < 1) E.screenrows = 1;
    editor_scroll();
    editor_update_syntax();            /* keep highlights/find in sync with edits */

    ABuf ab = { 0 };
    ab_append_str(&ab, SEQ_HIDE);      /* hide cursor while drawing (prep/game-of-life.py) */
    ab_append_str(&ab, SEQ_CLEAR);     /* ED clear screen (prep/clear-screen.py) */
    ab_append_str(&ab, SEQ_HOME);      /* CUP home (prep/cursor-move.py) */
    editor_draw_rows(&ab);
    editor_draw_status_bar(&ab);
    editor_draw_message_bar(&ab);
    int rx = erow_rx(&E.row[E.cy], E.cx);
    ab_appendf(&ab, "\x1b[%d;%dH", E.cy - E.rowoff + 1, rx - E.coloff + 1);
    ab_append_str(&ab, SEQ_SHOW);      /* show cursor (prep/game-of-life.py) */
    write(STDOUT_FILENO, ab.b, ab.len);
    free(ab.b);
}

/* Restore the terminal visuals on exit: show the cursor, re-enable
 * auto-wrap, clear the screen. Mirrors prep/game-of-life.py `cleanup` (which
 * re-shows the cursor on exit so the shell prompt is not left invisible). */
static void editor_cleanup(void) {
    write(STDOUT_FILENO, SEQ_SHOW, sizeof(SEQ_SHOW) - 1);
    write(STDOUT_FILENO, SEQ_WRAP_ON, sizeof(SEQ_WRAP_ON) - 1);
    write(STDOUT_FILENO, SEQ_CLEAR, sizeof(SEQ_CLEAR) - 1);
    write(STDOUT_FILENO, SEQ_HOME, sizeof(SEQ_HOME) - 1);
}

/* ------------------------------------------------------------------ */
/* Cursor movement and editing operations                              */
/* ------------------------------------------------------------------ */
static void editor_move_cursor(enum KeyType key) {
    if (E.cy >= E.numrows) {
        if (key == KEY_DOWN || key == KEY_PAGE_DOWN) return;
    }
    erow *r = (E.cy >= 0 && E.cy < E.numrows) ? &E.row[E.cy] : NULL;
    switch (key) {
    case KEY_LEFT:
        if (E.cx > 0) E.cx--;
        else if (E.cy > 0) { E.cy--; E.cx = E.row[E.cy].len; }
        break;
    case KEY_RIGHT:
        if (r && E.cx < r->len) E.cx++;
        else if (r && E.cy < E.numrows - 1) { E.cy++; E.cx = 0; }
        break;
    case KEY_UP:
        if (E.cy > 0) E.cy--;
        break;
    case KEY_DOWN:
        if (E.cy < E.numrows - 1) E.cy++;
        break;
    case KEY_HOME:
        E.cx = 0;
        break;
    case KEY_END:
        if (r) E.cx = r->len;
        break;
    case KEY_PAGE_UP:
        for (int n = E.screenrows; n > 0 && E.cy > 0; n--) E.cy--;
        break;
    case KEY_PAGE_DOWN:
        for (int n = E.screenrows; n > 0 && E.cy < E.numrows - 1; n--)
            E.cy++;
        break;
    default:
        return;
    }
    if (E.cy < E.numrows && E.cx > E.row[E.cy].len) E.cx = E.row[E.cy].len;
}

/* Insert a new (empty) row at index `at`. */
static void editor_insert_row(int at) {
    E.row = realloc(E.row, sizeof(erow) * (E.numrows + 1));
    memmove(&E.row[at + 1], &E.row[at], sizeof(erow) * (E.numrows - at));
    memset(&E.row[at], 0, sizeof(erow));
    E.numrows++;
}

static void editor_insert_char(char c) {
    if (E.cy == E.numrows) editor_insert_row(E.numrows);
    erow_insert(&E.row[E.cy], E.cx, c);
    E.cx++;
    E.dirty = 1;
    E.statusmsg[0] = '\0';
}

static void editor_insert_newline(void) {
    if (E.cx == 0) {
        editor_insert_row(E.cy);
    } else {
        erow *r = &E.row[E.cy];
        char *tail = malloc(r->len - E.cx + 1);
        memcpy(tail, r->chars + E.cx, r->len - E.cx);
        tail[r->len - E.cx] = '\0';
        int tail_len = r->len - E.cx;
        editor_insert_row(E.cy + 1);   /* reallocs the row array */
        erow *nr = &E.row[E.cy + 1];   /* re-fetch after the realloc */
        nr->chars = tail;
        nr->len = tail_len;
        r = &E.row[E.cy];
        r->len = E.cx;
        r->chars[r->len] = '\0';
    }
    E.cy++;
    E.cx = 0;
    E.dirty = 1;
    E.statusmsg[0] = '\0';
}

static void editor_backspace(void) {
    if (E.cy >= E.numrows) return;
    if (E.cx > 0) {
        erow_delete_range(&E.row[E.cy], E.cx - 1, 1);
        E.cx--;
    } else if (E.cy > 0) {
        /* merge current row into the previous one */
        erow *prev = &E.row[E.cy - 1];
        erow *cur = &E.row[E.cy];
        int prevlen = prev->len;
        prev->chars = realloc(prev->chars, prevlen + cur->len + 1);
        memcpy(prev->chars + prevlen, cur->chars, cur->len);
        prev->chars[prevlen + cur->len] = '\0';
        prev->len = prevlen + cur->len;
        erow_free(cur);
        memmove(&E.row[E.cy], &E.row[E.cy + 1],
                sizeof(erow) * (E.numrows - E.cy - 1));
        E.numrows--;
        E.cy--;
        E.cx = prevlen;
    }
    E.dirty = 1;
    E.statusmsg[0] = '\0';
}

static void editor_delete(void) {
    if (E.cy >= E.numrows) return;
    erow *r = &E.row[E.cy];
    if (E.cx < r->len) {
        erow_delete_range(r, E.cx, 1);
    } else if (E.cy < E.numrows - 1) {
        /* merge next row into the current one */
        erow *next = &E.row[E.cy + 1];
        r->chars = realloc(r->chars, r->len + next->len + 1);
        memcpy(r->chars + r->len, next->chars, next->len);
        r->chars[r->len + next->len] = '\0';
        r->len += next->len;
        erow_free(next);
        memmove(&E.row[E.cy + 1], &E.row[E.cy + 2],
                sizeof(erow) * (E.numrows - E.cy - 2));
        E.numrows--;
    }
    E.dirty = 1;
    E.statusmsg[0] = '\0';
}

/* ------------------------------------------------------------------ */
/* Save + quit                                                         */
/* ------------------------------------------------------------------ */
/*
 * Dirty-quit design (built only from prep/ primitives): the message bar and
 * the key loop already form the editor's only UI channel (prep/input-
 * orchestration.py routes Ctrl-letters to actions and prints status lines).
 * So a dirty Ctrl-Q does not quit: it sets the message "Unsaved changes;
 * Ctrl-Q again to discard and quit" (shown in the message bar via
 * prep/colors.py SGR) and arms `quit_confirmed`. A second Ctrl-Q within that
 * state quits. Any other key disarms it. This reuses the message-bar +
 * key-loop pair from prep/ — no new UI primitive is introduced.
 */
static void editor_save(void) {
    if (E.filename == NULL) {
        editor_set_message("No file name — cannot save");
        return;
    }
    FILE *fp = fopen(E.filename, "wb");
    if (fp == NULL) {
        editor_set_message("Cannot save: %s", strerror(errno));
        return;
    }
    for (int i = 0; i < E.numrows; i++) {
        fwrite(E.row[i].chars, 1, E.row[i].len, fp);
        fputc('\n', fp);   /* rows store content without the newline */
    }
    fclose(fp);
    E.dirty = 0;
    editor_set_message("Saved: %s (%d lines)", E.filename, E.numrows);
}

static int editor_quit(void) {
    if (E.dirty && !E.quit_confirmed) {
        E.quit_confirmed = 1;
        editor_set_message("Unsaved changes — press Ctrl-Q again to discard and quit");
        return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ */
/* Find (Ctrl-F)                                                       */
/* ------------------------------------------------------------------ */
/* Incremental forward search driven by the key loop: printable chars append
 * to the query (re-highlighted every keystroke), Backspace edits it, Enter
 * jumps the cursor to the next match from the current position, ESC cancels
 * and restores. State handling built from prep/ primitives (message-bar
 * prompt + SGR match colour + the input state machine of
 * prep/input-orchestration.py). */
static void editor_find_cancel(void) {
    E.search_active = 0;
    /* Keep any message set by editor_find_next ("Match N:M") visible — the
     * message bar is the feedback channel, per prep/input-orchestration.py. */
}

static void editor_find_next(void) {
    int nlen = E.search_len;
    if (nlen == 0) return;
    for (int i = E.cy; i < E.numrows; i++) {
        erow *r = &E.row[i];
        int start = (i == E.cy) ? E.cx : 0;
        for (int pos = start; pos + nlen <= r->len; pos++) {
            if (strncmp(r->chars + pos, E.search, nlen) == 0) {
                E.cy = i;
                E.cx = pos;
                editor_set_message("Match %d:%d", i + 1, pos + 1);
                return;
            }
        }
    }
    /* wrap around to the top of the file */
    for (int i = 0; i <= E.cy; i++) {
        erow *r = &E.row[i];
        for (int pos = 0; pos + nlen <= r->len; pos++) {
            if (i == E.cy && pos >= E.cx) break;
            if (strncmp(r->chars + pos, E.search, nlen) == 0) {
                E.cy = i;
                E.cx = pos;
                editor_set_message("Match %d:%d (wrapped)", i + 1, pos + 1);
                return;
            }
        }
    }
    editor_set_message("No match: %s", E.search);
}

/* ------------------------------------------------------------------ */
/* Key processing                                                      */
/* ------------------------------------------------------------------ */
static void editor_process_key(struct Key k) {
    if (E.search_active) {
        if (k.type == KEY_CTRL && k.ch == 0x06) { /* Ctrl-F: next match */
            editor_find_next();
        } else if (k.type == KEY_ENTER) {
            editor_find_next();
            editor_find_cancel();
        } else if (k.type == KEY_ESC) {
            editor_find_cancel();
        } else if (k.type == KEY_BACKSPACE) {
            if (E.search_len > 0) E.search[--E.search_len] = '\0';
        } else if (k.type == KEY_PRINTABLE) {
            if (E.search_len < (int)sizeof(E.search) - 1)
                E.search[E.search_len++] = k.ch;
            E.search[E.search_len] = '\0';
        }
        return;
    }

    switch (k.type) {
    case KEY_PRINTABLE:
        editor_insert_char(k.ch);
        break;
    case KEY_ENTER:
        editor_insert_newline();
        break;
    case KEY_BACKSPACE:
        editor_backspace();
        break;
    case KEY_DELETE:
        editor_delete();
        break;
    case KEY_UP: case KEY_DOWN: case KEY_LEFT: case KEY_RIGHT:
    case KEY_HOME: case KEY_END: case KEY_PAGE_UP: case KEY_PAGE_DOWN:
        editor_move_cursor(k.type);
        break;
    case KEY_CTRL:
        if (k.ch == 0x09) {          /* Tab: insert a real tab byte — it renders
                                        expanded (prep/flow.md pipeline row model)
                                        and saves as a real \t */
            editor_insert_char('\t');
        } else if (k.ch == 0x11) {   /* Ctrl-Q: quit */
            if (editor_quit()) exit(0);
        } else if (k.ch == 0x13) {   /* Ctrl-S: save */
            editor_save();
            E.quit_confirmed = 0;
        } else if (k.ch == 0x06) {   /* Ctrl-F: find */
            E.search_active = 1;
            E.search_len = 0;
            E.search[0] = '\0';
        } else if (k.ch == 0x03) {   /* Ctrl-C: treated as quit */
            if (editor_quit()) exit(0);
        }
        break;
    default:
        break;
    }
    if (k.type != KEY_CTRL || (k.ch != 0x11 && k.ch != 0x13 && k.ch != 0x06))
        E.quit_confirmed = 0;
}

static void editor_init(const char *path) {
    memset(&E, 0, sizeof(E));
    if (path != NULL) editor_open(path);
    editor_update_syntax();
    E.screenrows = 24;
    E.screencols = 80;
    editor_query_size(&E.screenrows, &E.screencols);
    E.screenrows -= 2;
}

int main(int argc, char **argv) {
    atexit(termios_restore);
    atexit(editor_cleanup);
    signal(SIGINT, termios_restore_and_exit);
    signal(SIGTERM, termios_restore_and_exit);

    if (!isatty(STDIN_FILENO)) {
        fprintf(stderr, "tedit: stdin is not a terminal\n");
        return 1;
    }
    if (termios_enable_raw() == -1) {
        fprintf(stderr, "tedit: raw mode failed: %s\n", strerror(errno));
        return 1;
    }
    /* Disable auto-wrap once so drawing a full-width row cannot wrap into
     * the next line; re-enabled on exit. (prep/clear-screen.py
     * disable_auto_wrap / terminal-viewport-combined.py DEC toggles.) */
    write(STDOUT_FILENO, SEQ_WRAP_OFF, sizeof(SEQ_WRAP_OFF) - 1);

    editor_init(argc > 1 ? argv[1] : NULL);
    if (argc > 1 && E.filename != NULL)
        editor_set_message("\"%s\"  %d lines", E.filename, E.numrows);

    for (;;) {
        editor_refresh();
        struct Key k = read_key();
        editor_process_key(k);
    }
    return 0;
}