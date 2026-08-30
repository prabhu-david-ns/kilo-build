/*
 * tedit — a dependency-free VT100 terminal text/code editor in C.
 *
 * Spec 04 of the kilo build repo. This is the real editor the prep phase
 * (specs 01-03) was studying for: it puts the raw-mode input, escape-sequence
 * parsing, append-buffer rendering, viewport awareness, and per-row display
 * state from prep/ (flow.md, key-classifier.py, input-orchestration.py,
 * clear-screen.py, cursor-move.py, colors.py, viewport.py, terminal-info.py,
 * game-of-life.py) to work in plain C.
 *
 * Build:  make                 (drives gcc -std=c11 -Wall -Wextra)
 * Run:    ./tedit [FILE]       (no FILE starts with an empty buffer)
 *
 * Keys:
 *   type                  insert characters
 *   arrows                move the cursor
 *   Home / End            jump to start / end of line
 *   PageUp / PageDown     scroll a screen at a time
 *   Backspace / Delete    delete characters (merging rows at the edges)
 *   Enter                 split the row
 *   Ctrl-S                save (prompts for a name on a new buffer)
 *   Ctrl-F                find (incremental; Enter jumps, ESC cancels)
 *   Ctrl-Q / Ctrl-C       quit (repeated while the buffer is dirty)
 *
 * Reference format: every escape sequence, syscall and technique below is
 * cited inline (URL, man-page section, or this repo's prep/ material). The
 * full bibliography lives in prep/README.md.
 */

/*** includes ***/

/* Expose POSIX interfaces (strdup(3), getline(3), ftruncate(2),
   sigaction(2)) that strict -std=c11 hides by default. */
#define _POSIX_C_SOURCE 200809L

#include <ctype.h>     /* iscntrl(3), isdigit(3), isspace(3) */
#include <errno.h>     /* errno(3) */
#include <fcntl.h>     /* open(2): O_RDWR, O_CREAT */
#include <signal.h>    /* sigaction(2), SIGWINCH, SIGINT, SIGTERM */
#include <stdarg.h>    /* va_list: vsnprintf(3) */
#include <stdio.h>     /* perror(3), fopen(3), fclose(3), snprintf(3) */
#include <stdlib.h>    /* malloc(3), realloc(3), free(3), exit(3), atexit(3) */
#include <string.h>    /* memcpy(3), memmove(3), memset(3), strlen(3), strstr(3) */
#include <sys/ioctl.h> /* ioctl(2): TIOCGWINSZ */
#include <termios.h>   /* termios(3): tcgetattr, tcsetattr, cfmakeraw */
#include <time.h>      /* time(2), time_t */
#include <unistd.h>    /* read(2), write(2), close(2), STDIN/STDOUT_FILENO */

/*** defines ***/

#define TEDIT_VERSION "0.1.0"
#define TEDIT_TAB_STOP 8
#define TEDIT_QUIT_TIMES 3

/* Ctrl-letter keys arrive as the low 5 bits of the letter (man 7 ascii:
   Ctrl-A = 0x01 ... Ctrl-Z = 0x1A; see prep/flow.md §5.2). */
#define CTRL_KEY(k) ((k) & 0x1f)

/* Synthetic key codes for keys that arrive as multi-byte escape sequences
   (prep/key-classifier.py + prep/flow.md §5.3); chosen above the byte range. */
enum editorKey {
    BACKSPACE = 127, /* DEL: the terminal's erase key sends 0x7F in raw mode */
    ARROW_LEFT = 1000,
    ARROW_RIGHT,
    ARROW_UP,
    ARROW_DOWN,
    DEL_KEY,
    HOME_KEY,
    END_KEY,
    PAGE_UP,
    PAGE_DOWN,
    KEY_RESIZE /* internal: SIGWINCH arrived while waiting for a key */
};

/*** data ***/

/* One file row: canonical bytes (chars) plus a derived display buffer
   (render) with tabs expanded to tab stops and non-printables mapped to a
   caret symbol. "hl" carries the per-display-byte syntax class. Keeping
   chars untouched means real tabs survive a save while render drives the
   screen (prep/viewport.py + spec 04 §5). */
typedef struct erow {
    int idx;            /* row index in the file, zero-based */
    int size;           /* bytes in chars (excl. NUL) */
    int rsize;          /* bytes in render (excl. NUL) */
    char *chars;        /* canonical row content */
    char *render;       /* screen-ready content (tabs expanded) */
    unsigned char *hl;  /* syntax class per render byte */
    int hl_open_comment;/* row ends inside a multi-line comment */
} erow;

/* Syntax-highlight classes. Indexed by display position (render offset),
   per spec 04 §9. */
enum editorHighlight {
    HL_NORMAL = 0,
    HL_NONPRINT,
    HL_COMMENT,   /* // single-line comment */
    HL_MLCOMMENT, /* (block) multi-line comment */
    HL_KEYWORD1,  /* control keywords */
    HL_KEYWORD2,  /* C types */
    HL_STRING,
    HL_NUMBER,
    HL_MATCH      /* current search match overlay */
};

#define HL_HIGHLIGHT_NUMBERS (1 << 0)
#define HL_HIGHLIGHT_STRINGS (1 << 1)

/* Global editor state. */
struct editorConfig {
    int cx, cy;          /* cursor position in file characters */
    int rx;              /* cursor display column (derived from cx) */
    int rowoff;          /* vertical scroll offset (top visible row) */
    int coloff;          /* horizontal scroll offset (left visible col) */
    int screenrows;      /* visible content rows (below status bars) */
    int screencols;      /* visible columns */
    int numrows;         /* total file rows */
    erow *row;           /* dynamic array of rows */
    int dirty;           /* modified since last save */
    char *filename;      /* currently open file, or NULL */
    char statusmsg[80];  /* transient message-bar text */
    time_t statusmsg_time;
    struct termios orig_termios; /* saved attrs, for raw-mode restore */
    struct editorSyntax *syntax; /* current syntax scheme, or NULL */
};

static struct editorConfig E;

/* Set (async-signal-unsafe but only flipped, never read) by SIGWINCH. */
static volatile sig_atomic_t g_resize = 0;

/*** filetypes ***/

/* A per-language rule table: filename matches, keywords (a trailing '|'
   marks the "type" color), single/multi-line comment delimiters, and
   feature flags. This is the classic lightweight-editor approach — no
   full lexer, just per-row scanning rules. (spec 04 §9) */
const char *C_HL_extensions[] = {".c", ".h", ".cpp", NULL};

const char *C_HL_keywords[] = {
    /* control-flow keywords */
    "switch", "if", "while", "for", "break", "continue", "return", "else",
    "struct", "union", "typedef", "static", "enum", "class", "case",
    /* C types (rendered in the second color) */
    "int|", "long|", "double|", "float|", "char|", "unsigned|", "signed|",
    "void|", NULL
};

struct editorSyntax {
    const char *filetype;
    const char **filematch;
    const char **keywords;
    const char singleline_comment_start[3]; /* NUL-terminated: "//" */
    const char multiline_comment_start[3];  /* NUL-terminated: slash-star */
    const char multiline_comment_end[3];    /* NUL-terminated: star-slash */
    int flags;
};

static struct editorSyntax HLDB[] = {
    {
        "c",
        C_HL_extensions,
        C_HL_keywords,
        "//", "/*", "*/",
        HL_HIGHLIGHT_NUMBERS | HL_HIGHLIGHT_STRINGS
    }
};

#define HLDB_ENTRIES (sizeof(HLDB) / sizeof(HLDB[0]))

/*** prototypes ***/

void editorSetStatusMessage(const char *fmt, ...);
void editorRefreshScreen(void);
char *editorPrompt(char *prompt, void (*callback)(char *, int));
void editorFind(void);
void updateWindowSize(void);

/*** terminal ***/

/* Fatal error path: show the message, then exit. atexit(disableRawMode)
   (registered in enableRawMode) restores the terminal. */
void die(const char *s) {
    write(STDOUT_FILENO, "\x1b[2J", 4); /* ED — erase screen; VT100 UG ch.3 */
    write(STDOUT_FILENO, "\x1b[H", 3);  /* CUP — cursor home; VT100 UG ch.3 */
    perror(s);
    write(STDERR_FILENO, "\r\n", 2);    /* raw mode clears OPOST, no NL->CRNL */
    exit(1);
}

/* Restore the termios saved by enableRawMode. Registered via atexit so the
   terminal is always brought back on exit — normal quit and Ctrl-C both
   funnel through exit(3). */
void disableRawMode(void) {
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &E.orig_termios) == -1)
        die("tcsetattr");
}

/* Enter raw mode. We clear exactly the flags the tty layer needs to stop
   line-buffering, echoing, signal generation and flow control, then read
   bytes one at a time with a blocking read (VMIN=0, VTIME=1 — see man 3
   termios "Raw mode" / cfmakeraw; prep/flow.md §3.3). Clearing ISIG makes
   Ctrl-C arrive as plain byte 0x03 instead of SIGINT. */
void enableRawMode(void) {
    if (tcgetattr(STDIN_FILENO, &E.orig_termios) == -1) die("tcgetattr");
    atexit(disableRawMode);
    struct termios raw = E.orig_termios;
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 0;  /* noncanonical read: return immediately if empty */
    raw.c_cc[VTIME] = 1; /* ...but wait up to 1 decisecond for a byte */
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == -1) die("tcsetattr");
}

/* Read one typed key from a blocking stdin. Printable bytes and control
   bytes pass through; ESC (0x1B) starts a CSI/SS3 escape sequence that is
   decoded into the synthetic editorKey codes. A lone ESC returns as the ESC
   key because VTIME makes the follow-up reads time out after 100ms. The
   sequence table is our own prep research (prep/key-classifier.py,
   prep/flow.md §5.3-5.4) cross-checked against ECMA-48 §5.4. */
int editorReadKey(void) {
    int nread;
    char c;
    while ((nread = read(STDIN_FILENO, &c, 1)) != 1) { /* man 2 read */
        if (nread == -1 && errno != EAGAIN && errno != EINTR) die("read");
        /* While idle the main loop is blocked here; a SIGWINCH that set the
           flag would otherwise wait for the next keypress. Re-query the
           window size and report a sentinel so main redraws immediately. */
        if (g_resize) {
            g_resize = 0;
            updateWindowSize();
            return KEY_RESIZE;
        }
    }
    if (c == '\x1b') {
        char seq[3];
        if (read(STDIN_FILENO, &seq[0], 1) != 1) return '\x1b';
        if (read(STDIN_FILENO, &seq[1], 1) != 1) return '\x1b';
        if (seq[0] == '[') {                 /* CSI: ESC [ ... final */
            if (seq[1] >= '0' && seq[1] <= '9') {
                if (read(STDIN_FILENO, &seq[2], 1) != 1) return '\x1b';
                if (seq[2] == '~') {         /* CSI n ~ keys */
                    switch (seq[1]) {
                        case '1': return HOME_KEY;    /* CSI 1~ */
                        case '3': return DEL_KEY;     /* CSI 3~ */
                        case '4': return END_KEY;     /* CSI 4~ */
                        case '5': return PAGE_UP;     /* CSI 5~ */
                        case '6': return PAGE_DOWN;   /* CSI 6~ */
                        case '7': return HOME_KEY;    /* CSI 7~ */
                        case '8': return END_KEY;     /* CSI 8~ */
                    }
                }
            } else {
                switch (seq[1]) {
                    case 'A': return ARROW_UP;    /* CSI A */
                    case 'B': return ARROW_DOWN;  /* CSI B */
                    case 'C': return ARROW_RIGHT; /* CSI C */
                    case 'D': return ARROW_LEFT;  /* CSI D */
                    case 'H': return HOME_KEY;    /* CSI H */
                    case 'F': return END_KEY;     /* CSI F */
                }
            }
        } else if (seq[0] == 'O') {          /* SS3: ESC O final (vt220) */
            switch (seq[1]) {
                case 'H': return HOME_KEY;   /* ESC O H */
                case 'F': return END_KEY;    /* ESC O F */
            }
        }
        return '\x1b'; /* lone ESC or unrecognized sequence */
    }
    return c;
}

/* SIGWINCH arrives when the terminal window is resized (man 7 signal;
   ioctl_tty(2const): "When the window size changes, a SIGWINCH signal is
   sent to the foreground process group" — TLPI demo_SIGWINCH.c
   https://man7.org/code/tty/demo_SIGWINCH.c.html ). We only set a flag and
   let the main loop re-query the size, which is the safe pattern. */
void handleSigWinCh(int sig) {
    (void)sig;
    g_resize = 1;
}

/* SIGINT / SIGTERM cleanup for the case a signal is delivered despite ISIG
   being off (e.g. kill from another terminal). atexit handlers do NOT run
   on signal termination, so restore the tty and show the cursor here. */
void handleSigTerm(int sig) {
    (void)sig;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &E.orig_termios);
    write(STDOUT_FILENO, "\x1b[?25h", 6); /* DECTCEM: show cursor */
    _exit(128 + sig);
}

/* Ask the terminal for the cursor position using a Device Status Report.
   Sequence CSI 6 n, response CSI row ; col R — our own prep research
   (prep/viewport.py, prep/terminal-info.py; VT100 UG ch.3 "DSR"). */
int getCursorPosition(int *rows, int *cols) {
    char buf[32];
    unsigned int i = 0;
    if (write(STDOUT_FILENO, "\x1b[6n", 4) != 4) return -1;
    while (i < sizeof(buf) - 1) {
        if (read(STDIN_FILENO, &buf[i], 1) != 1) break;
        if (buf[i] == 'R') break;
        i++;
    }
    buf[i] = '\0';
    if (buf[0] != '\x1b' || buf[1] != '[') return -1;
    if (sscanf(&buf[2], "%d;%d", rows, cols) != 2) return -1;
    return 0;
}

/* Window size, ioctl first (prep/terminal-info.py documents TIOCGWINSZ;
   man 2 ioctl_tty). If ioctl is unavailable, fall back to parking the
   cursor far off-screen — the terminal clamps it to the last row/col —
   and reading where it actually landed (prep/viewport.py "fallback"). */
int getWindowSize(int *rows, int *cols) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == -1 || ws.ws_col == 0) {
        if (write(STDOUT_FILENO, "\x1b[999C\x1b[999B", 12) != 12) return -1;
        return getCursorPosition(rows, cols);
    } else {
        *cols = ws.ws_col;
        *rows = ws.ws_row;
        return 0;
    }
}

/*** syntax highlighting ***/

/* "Separat or" is the classic lightweight keyword-boundary test: a word is
   only a keyword if preceded by a separator and followed by one. */
int is_separator(int c) {
    return isspace((unsigned char)c) || c == '\0' ||
           strchr(",.()+-/*=~%<>[];", c) != NULL;
}

/* True if the row ends inside an unclosed multi-line comment, i.e. the last
   display byte is HL_MLCOMMENT and it is not the closing "* /" pair. This is
   the state that must be carried across rows for multi-line comments to stay
   highlighted on both rows (spec 04 §9). */
int editorRowHasOpenComment(erow *row) {
    if (row->hl && row->rsize && row->hl[row->rsize - 1] == HL_MLCOMMENT &&
        (row->rsize < 2 ||
         (row->render[row->rsize - 2] != '*' ||
          row->render[row->rsize - 1] != '/')))
        return 1;
    return 0;
}

/* Re-scan one row and set a syntax class per display byte. Runs on every
   row change; the open-comment state read from the previous row is what
   makes block-comment spans stay highlighted across rows, and if the state
   at the end of this row changed we recursively re-highlight the next row.
   (Technique researched via snaptoken/kilo ch.7 and antirez/kilo.) */
void editorUpdateSyntax(erow *row) {
    row->hl = realloc(row->hl, row->rsize);
    memset(row->hl, HL_NORMAL, row->rsize);
    if (E.syntax == NULL) return;

    const char **keywords = E.syntax->keywords;
    const char *scs = E.syntax->singleline_comment_start;
    const char *mcs = E.syntax->multiline_comment_start;
    const char *mce = E.syntax->multiline_comment_end;

    int prev_sep = 1;
    int in_string = 0;
    /* Carry the multi-line comment state from the previous row. */
    int in_comment = (row->idx > 0 &&
                      editorRowHasOpenComment(&E.row[row->idx - 1]));

    int i = 0;
    while (i < row->rsize) {
        char c = row->render[i];
        unsigned char prev_hl = (i > 0) ? row->hl[i - 1] : HL_NORMAL;

        /* Single-line // comment: paint the rest of the row, done. */
        if (scs[0] && !in_string && !in_comment) {
            if (!strncmp(&row->render[i], scs, 2)) {
                memset(&row->hl[i], HL_COMMENT, row->rsize - i);
                break;
            }
        }

        /* Multi-line block comment. */
        if (mcs[0] && mce[0] && !in_string) {
            if (in_comment) {
                row->hl[i] = HL_MLCOMMENT;
                if (!strncmp(&row->render[i], mce, 2)) {
                    memset(&row->hl[i], HL_MLCOMMENT, 2);
                    i += 2;
                    in_comment = 0;
                    prev_sep = 1;
                    continue;
                } else {
                    i++;
                    continue;
                }
            } else if (!strncmp(&row->render[i], mcs, 2)) {
                memset(&row->hl[i], HL_MLCOMMENT, 2);
                i += 2;
                in_comment = 1;
                continue;
            }
        }

        /* "..." and '...' strings, honouring backslash escapes. */
        if (E.syntax->flags & HL_HIGHLIGHT_STRINGS) {
            if (in_string) {
                row->hl[i] = HL_STRING;
                if (c == '\\' && i + 1 < row->rsize) {
                    row->hl[i + 1] = HL_STRING;
                    i += 2;
                    continue;
                }
                if (c == in_string) in_string = 0;
                i++;
                prev_sep = 1;
                continue;
            } else {
                if (c == '"' || c == '\'') {
                    in_string = c;
                    row->hl[i] = HL_STRING;
                    i++;
                    continue;
                }
            }
        }

        /* Numbers: digit runs (and decimal points) after a separator. */
        if (E.syntax->flags & HL_HIGHLIGHT_NUMBERS) {
            if ((isdigit((unsigned char)c) &&
                 (prev_sep || prev_hl == HL_NUMBER)) ||
                (c == '.' && prev_hl == HL_NUMBER)) {
                row->hl[i] = HL_NUMBER;
                i++;
                prev_sep = 0;
                continue;
            }
        }

        /* Keywords, longest-match over the rule table. */
        if (prev_sep) {
            int j;
            for (j = 0; keywords[j]; j++) {
                int klen = strlen(keywords[j]);
                int kw2 = (keywords[j][klen - 1] == '|');
                if (kw2) klen--;
                if (!strncmp(&row->render[i], keywords[j], klen) &&
                    is_separator(row->render[i + klen])) {
                    memset(&row->hl[i],
                           kw2 ? HL_KEYWORD2 : HL_KEYWORD1, klen);
                    i += klen;
                    break;
                }
            }
            if (keywords[j] != NULL) {
                prev_sep = 0;
                continue;
            }
        }

        prev_sep = is_separator(c);
        i++;
    }

    /* Propagate: if the open-comment state at the end of this row changed,
       the next row must be re-scanned (and so on). */
    int changed = (row->hl_open_comment != in_comment);
    row->hl_open_comment = in_comment;
    if (changed && row->idx + 1 < E.numrows)
        editorUpdateSyntax(&E.row[row->idx + 1]);
}

void editorRehighlightAll(void) {
    for (int j = 0; j < E.numrows; j++)
        editorUpdateSyntax(&E.row[j]);
}

/* Map a highlight class to a terminal foreground color via SGR (CSI n m).
   Numbers are ECMA-48 8.3.117 SGR parameters; the 8-color scheme was
   demonstrated in prep/colors.py. */
int editorSyntaxToColor(int hl) {
    switch (hl) {
        case HL_COMMENT:
        case HL_MLCOMMENT: return 36; /* cyan */
        case HL_KEYWORD1:  return 33; /* yellow */
        case HL_KEYWORD2:  return 32; /* green */
        case HL_STRING:    return 35; /* magenta */
        case HL_NUMBER:    return 31; /* red */
        case HL_MATCH:     return 34; /* blue — search match overlay */
        default:           return 37; /* white */
    }
}

/* Pick a syntax scheme by filename extension (strrchr on '.') or by
   substring match (man 3 strrchr, man 3 strstr). */
void editorSelectSyntaxHighlight(void) {
    E.syntax = NULL;
    if (E.filename == NULL) return;
    char *ext = strrchr(E.filename, '.');
    for (unsigned int j = 0; j < HLDB_ENTRIES; j++) {
        struct editorSyntax *s = &HLDB[j];
        unsigned int i = 0;
        while (s->filematch[i]) {
            int is_ext = (s->filematch[i][0] == '.');
            if ((is_ext && ext && !strcmp(ext, s->filematch[i])) ||
                (!is_ext && strstr(E.filename, s->filematch[i]))) {
                E.syntax = s;
                editorRehighlightAll();
                return;
            }
            i++;
        }
    }
}

/*** row operations ***/

/* Rebuild the display buffer from the canonical bytes: tabs expand to the
   next tab stop (TEDIT_TAB_STOP = 8), everything else passes through.
   This is why the saved file keeps its real tabs while the screen shows
   expanded ones (spec 04 §5). */
void editorUpdateRow(erow *row) {
    int tabs = 0;
    for (int j = 0; j < row->size; j++)
        if (row->chars[j] == '\t') tabs++;
    free(row->render);
    row->render = malloc(row->size + tabs * (TEDIT_TAB_STOP - 1) + 1);
    int idx = 0;
    for (int j = 0; j < row->size; j++) {
        if (row->chars[j] == '\t') {
            row->render[idx++] = ' ';
            while (idx % TEDIT_TAB_STOP != 0) row->render[idx++] = ' ';
        } else {
            row->render[idx++] = row->chars[j];
        }
    }
    row->render[idx] = '\0';
    row->rsize = idx;
    editorUpdateSyntax(row);
}

/* Insert a row at index `at`, shifting later rows right. */
void editorInsertRow(int at, char *s, size_t len) {
    if (at < 0 || at > E.numrows) return;
    E.row = realloc(E.row, sizeof(erow) * (E.numrows + 1));
    memmove(&E.row[at + 1], &E.row[at], sizeof(erow) * (E.numrows - at));
    for (int j = at + 1; j <= E.numrows; j++) E.row[j].idx++;
    E.row[at].idx = at;
    E.row[at].size = len;
    E.row[at].chars = malloc(len + 1);
    memcpy(E.row[at].chars, s, len);
    E.row[at].chars[len] = '\0';
    E.row[at].render = NULL;
    E.row[at].hl = NULL;
    E.row[at].hl_open_comment = 0;
    editorUpdateRow(&E.row[at]);
    E.numrows++;
    E.dirty++;
}

/* Free and remove the row at `at`, shifting later rows left. */
void editorDelRow(int at) {
    if (at < 0 || at >= E.numrows) return;
    free(E.row[at].chars);
    free(E.row[at].render);
    free(E.row[at].hl);
    memmove(&E.row[at], &E.row[at + 1],
            sizeof(erow) * (E.numrows - at - 1));
    for (int j = at; j < E.numrows - 1; j++) E.row[j].idx--;
    E.numrows--;
    E.dirty++;
}

/* Insert one character into a row at display-agnostic char offset `at`. */
void editorRowInsertChar(erow *row, int at, int c) {
    if (at < 0 || at > row->size) at = row->size;
    row->chars = realloc(row->chars, row->size + 2);
    memmove(&row->chars[at + 1], &row->chars[at], row->size - at + 1);
    row->size++;
    row->chars[at] = c;
    editorUpdateRow(row);
    E.dirty++;
}

/* Append a byte range to a row (used to merge the next row on Delete). */
void editorRowAppendString(erow *row, char *s, size_t len) {
    row->chars = realloc(row->chars, row->size + len + 1);
    memcpy(&row->chars[row->size], s, len);
    row->size += len;
    row->chars[row->size] = '\0';
    editorUpdateRow(row);
    E.dirty++;
}

/* Delete the char at `at` inside a row. */
void editorRowDelChar(erow *row, int at) {
    if (at < 0 || at >= row->size) return;
    memmove(&row->chars[at], &row->chars[at + 1], row->size - at);
    row->size--;
    editorUpdateRow(row);
    E.dirty++;
}

/* Convert a char offset to its display column (tabs count as up-to-stop
   columns) — this is the cursor math the display needs. */
int editorRowCxToRx(erow *row, int cx) {
    int rx = 0;
    for (int j = 0; j < cx; j++) {
        if (row->chars[j] == '\t')
            rx += (TEDIT_TAB_STOP - 1) - (rx % TEDIT_TAB_STOP);
        rx++;
    }
    return rx;
}

/* Inverse of editorRowCxToRx: find the char offset for a display column. */
int editorRowRxToCx(erow *row, int rx) {
    int cur_rx = 0;
    int cx;
    for (cx = 0; cx < row->size; cx++) {
        if (row->chars[cx] == '\t')
            cur_rx += (TEDIT_TAB_STOP - 1) - (cur_rx % TEDIT_TAB_STOP);
        cur_rx++;
        if (cur_rx > rx) return cx;
    }
    return cx;
}

/*** editor operations ***/

/* Insert a character at the cursor, growing the row list if needed. */
void editorInsertChar(int c) {
    if (E.cy == E.numrows) editorInsertRow(E.numrows, "", 0);
    editorRowInsertChar(&E.row[E.cy], E.cx, c);
    E.cx++;
}

/* Enter: split the current row at the cursor into two rows. */
void editorInsertNewline(void) {
    if (E.cx == 0) {
        editorInsertRow(E.cy, "", 0);
    } else {
        erow *row = &E.row[E.cy];
        editorInsertRow(E.cy + 1, &row->chars[E.cx], row->size - E.cx);
        row = &E.row[E.cy];
        row->size = E.cx;
        row->chars[row->size] = '\0';
        editorUpdateRow(row);
    }
    E.cy++;
    E.cx = 0;
}

/* Backspace at column 0 merges the current row into the previous one. */
void editorDelChar(void) {
    if (E.cy == E.numrows) return;
    if (E.cx == 0 && E.cy == 0) return;
    erow *row = &E.row[E.cy];
    if (E.cx > 0) {
        editorRowDelChar(row, E.cx - 1);
        E.cx--;
    } else {
        E.cx = E.row[E.cy - 1].size;
        editorRowAppendString(&E.row[E.cy - 1], row->chars, row->size);
        editorDelRow(E.cy);
        E.cy--;
    }
}

/* Move the cursor, clamping into the current row. */
void editorMoveCursor(int key) {
    erow *row = (E.cy >= E.numrows) ? NULL : &E.row[E.cy];
    switch (key) {
        case ARROW_LEFT:
            if (E.cx != 0) E.cx--;
            else if (E.cy > 0) {
                E.cy--;
                E.cx = E.row[E.cy].size;
            }
            break;
        case ARROW_RIGHT:
            if (row && E.cx < row->size) E.cx++;
            else if (row && E.cx == row->size) {
                E.cy++;
                E.cx = 0;
            }
            break;
        case ARROW_UP:
            if (E.cy != 0) E.cy--;
            break;
        case ARROW_DOWN:
            if (E.cy < E.numrows) E.cy++;
            break;
    }
    row = (E.cy >= E.numrows) ? NULL : &E.row[E.cy];
    int rowlen = row ? row->size : 0;
    if (E.cx > rowlen) E.cx = rowlen;
}

/*** file i/o ***/

/* Serialize the whole buffer as rows joined by '\n' — the exact bytes we
   save. The row 'chars' (with real tabs) are written verbatim. */
char *editorRowsToString(int *buflen) {
    int totlen = 0;
    for (int j = 0; j < E.numrows; j++) totlen += E.row[j].size + 1;
    *buflen = totlen;
    char *buf = malloc(totlen ? (size_t)totlen : 1);
    char *p = buf;
    for (int j = 0; j < E.numrows; j++) {
        memcpy(p, E.row[j].chars, E.row[j].size);
        p += E.row[j].size;
        *p = '\n';
        p++;
    }
    return buf;
}

/* Open a file: read it line by line into the row model. getline(3) grows
   the line buffer for us (POSIX, libc only). */
void editorOpen(char *filename) {
    free(E.filename);
    E.filename = strdup(filename);
    editorSelectSyntaxHighlight();
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        /* A path that doesn't exist yet (ENOENT) starts an empty buffer
           that Ctrl-S can create; any other open error is fatal. */
        if (errno != ENOENT) die("fopen");
        return;
    }
    char *line = NULL;
    size_t linecap = 0;
    ssize_t linelen;
    while ((linelen = getline(&line, &linecap, fp)) != -1) {
        while (linelen > 0 && (line[linelen - 1] == '\n' ||
                               line[linelen - 1] == '\r'))
            linelen--;
        editorInsertRow(E.numrows, line, (size_t)linelen);
    }
    free(line);
    fclose(fp);
    E.dirty = 0;
}

/* Save: ftruncate + a single write(2) — truncating first makes a failed
   write leave a clean shorter file rather than a corrupt one (the pattern
   antirez/kilo documents). If there is no filename yet, ask for one. */
void editorSave(void) {
    if (E.filename == NULL) {
        char *name = editorPrompt("Save as: %s", NULL);
        if (name == NULL) {
            editorSetStatusMessage("Save aborted");
            return;
        }
        E.filename = name;
        editorSelectSyntaxHighlight();
    }
    int len;
    char *buf = editorRowsToString(&len);
    int fd = open(E.filename, O_RDWR | O_CREAT, 0644); /* man 2 open */
    if (fd != -1) {
        if (ftruncate(fd, len) != -1) { /* man 2 ftruncate */
            if (write(fd, buf, (size_t)len) == len) {
                close(fd);
                free(buf);
                E.dirty = 0;
                editorSetStatusMessage("%d bytes written to disk", len);
                return;
            }
        }
        close(fd);
    }
    free(buf);
    editorSetStatusMessage("Can't save! I/O error: %s", strerror(errno));
}

/*** find ***/

/* Overlay HL_MATCH on every occurrence of the query in the render buffer,
   giving incremental match highlighting across all rows while finding.
   (Search-match highlighting researched via snaptoken/kilo ch.9.) */
void editorHighlightMatches(const char *query) {
    size_t qlen = strlen(query);
    if (qlen == 0) return;
    for (int j = 0; j < E.numrows; j++) {
        erow *row = &E.row[j];
        char *match = row->render;
        while ((match = strstr(match, query)) != NULL) {
            memset(&row->hl[match - row->render], HL_MATCH, qlen);
            match += qlen;
        }
    }
}

/* Called after every keystroke while the search prompt is open: printable
   keys re-run the incremental search forward from the cursor, arrow keys
   step between matches, Enter/ESC end the session. */
void editorFindCallback(char *query, int key) {
    static int last_match = -1;
    static int direction = 1;

    if (key == '\r' || key == '\x1b') { /* Enter/ESC: finish */
        last_match = -1;
        direction = 1;
        return;
    } else if (key == ARROW_RIGHT || key == ARROW_DOWN) {
        direction = 1;
    } else if (key == ARROW_LEFT || key == ARROW_UP) {
        direction = -1;
    } else { /* printable: fresh incremental search */
        last_match = -1;
        direction = 1;
    }

    if (query[0] == '\0') { /* nothing to search for yet */
        last_match = -1;
        editorRehighlightAll();
        return;
    }

    if (last_match == -1) {
        /* First pass after a query change: search forward from the cursor
           row, wrapping around the file. */
        int current = E.cy;
        for (int i = 0; i < E.numrows; i++) {
            erow *row = &E.row[current];
            char *match = strstr(row->render, query);
            if (match) {
                last_match = current;
                E.cy = current;
                E.cx = editorRowRxToCx(row, match - row->render);
                E.rowoff = E.numrows; /* force scroll to the match */
                editorRehighlightAll();
                editorHighlightMatches(query);
                return;
            }
            current = (current + 1) % E.numrows;
        }
        return;
    }

    /* Arrow navigation: walk rows in `direction` to the next match. */
    int current = last_match;
    for (int i = 0; i < E.numrows; i++) {
        current += direction;
        if (current == -1) current = E.numrows - 1;
        else if (current == E.numrows) current = 0;
        erow *row = &E.row[current];
        char *match = strstr(row->render, query);
        if (match) {
            last_match = current;
            E.cy = current;
            E.cx = editorRowRxToCx(row, match - row->render);
            E.rowoff = E.numrows;
            break;
        }
    }
}

/* Ctrl-F: open a prompt; forward search from the cursor with live match
   highlighting. Enter keeps the cursor at the match; ESC returns to where
   we started. The highlight overlay is cleared on exit. */
void editorFind(void) {
    int saved_cx = E.cx, saved_cy = E.cy;
    int saved_coloff = E.coloff, saved_rowoff = E.rowoff;
    char *query = editorPrompt("Search: %s (ESC to cancel)",
                               editorFindCallback);
    if (query) {
        free(query);
    } else {
        E.cx = saved_cx;
        E.cy = saved_cy;
        E.coloff = saved_coloff;
        E.rowoff = saved_rowoff;
    }
    editorRehighlightAll(); /* drop the HL_MATCH overlay */
}

/*** append buffer ***/

/* The append buffer is the flicker fix: instead of write()ing dozens of
   small escape sequences and characters, we compose the entire frame in
   memory and flush it with a single write(). Rationale researched via the
   game-of-life prep (prep/game-of-life.py "compose_frame"),
   https://softwareunderthehood.com/2024/03/08/RC-W04-D5.html and
   https://stackoverflow.com/questions/71452837/. */
struct abuf {
    char *b;
    int len;
};

#define ABUF_INIT {NULL, 0}

void abAppend(struct abuf *ab, const char *s, int len) {
    char *new = realloc(ab->b, (size_t)(ab->len + len));
    if (new == NULL) return;
    memcpy(&new[ab->len], s, (size_t)len);
    ab->b = new;
    ab->len += len;
}

void abFree(struct abuf *ab) {
    free(ab->b);
}

/*** output ***/

/* Vertical + horizontal scroll. rx (display cursor column) is computed from
   cx; the viewport then pans so the cursor is always visible. (spec 04 §5;
   the viewport math was studied in prep/viewport.py.) */
void editorScroll(void) {
    E.rx = 0;
    if (E.cy < E.numrows) E.rx = editorRowCxToRx(&E.row[E.cy], E.cx);
    if (E.cy < E.rowoff) E.rowoff = E.cy;
    if (E.cy >= E.rowoff + E.screenrows) E.rowoff = E.cy - E.screenrows + 1;
    if (E.rx < E.coloff) E.coloff = E.rx;
    if (E.rx >= E.coloff + E.screencols) E.coloff = E.rx - E.screencols + 1;
}

/* Draw every visible content row into the append buffer. Rows outside the
   file show "~"; a syntax-colored slice of each row (from coloff for
   screencols columns) is appended with SGR color switches per byte. Each
   row ends with CSI K (EL, erase to end of line) so a shorter row never
   leaves stale characters behind (ECMA-48; prep/clear-screen.py). */
void editorDrawRows(struct abuf *ab) {
    for (int y = 0; y < E.screenrows; y++) {
        int filerow = y + E.rowoff;
        if (filerow >= E.numrows) {
            if (E.numrows == 0 && y == E.screenrows / 3) {
                char welcome[80];
                int welcomelen = snprintf(welcome, sizeof(welcome),
                    "tedit editor -- version %s", TEDIT_VERSION);
                if (welcomelen > E.screencols) welcomelen = E.screencols;
                int padding = (E.screencols - welcomelen) / 2;
                if (padding) { abAppend(ab, "~", 1); padding--; }
                while (padding--) abAppend(ab, " ", 1);
                abAppend(ab, welcome, welcomelen);
            } else {
                abAppend(ab, "~", 1);
            }
        } else {
            int len = E.row[filerow].rsize - E.coloff;
            if (len < 0) len = 0;
            if (len > E.screencols) len = E.screencols;
            char *c = &E.row[filerow].render[E.coloff];
            unsigned char *hl = &E.row[filerow].hl[E.coloff];
            int current_color = -1;
            for (int j = 0; j < len; j++) {
                unsigned char uc = (unsigned char)c[j];
                if (iscntrl(uc)) {
                    /* Show control chars as ^X in reverse video (SGR 7m). */
                    char sym = (uc <= 26) ? '@' + uc : '?';
                    abAppend(ab, "\x1b[7m", 4);
                    abAppend(ab, &sym, 1);
                    abAppend(ab, "\x1b[m", 3);
                    if (current_color != -1) {
                        char buf[16];
                        int clen = snprintf(buf, sizeof(buf), "\x1b[%dm",
                                            current_color);
                        abAppend(ab, buf, clen);
                    }
                } else if (hl[j] == HL_NORMAL) {
                    if (current_color != -1) {
                        abAppend(ab, "\x1b[39m", 5); /* default fg */
                        current_color = -1;
                    }
                    abAppend(ab, &c[j], 1);
                } else {
                    int color = editorSyntaxToColor(hl[j]);
                    if (color != current_color) {
                        current_color = color;
                        char buf[16];
                        int clen = snprintf(buf, sizeof(buf), "\x1b[%dm",
                                            color);
                        abAppend(ab, buf, clen);
                    }
                    abAppend(ab, &c[j], 1);
                }
            }
            abAppend(ab, "\x1b[39m", 5); /* restore default foreground */
        }
        abAppend(ab, "\x1b[K", 3);  /* EL: erase to end of line */
        abAppend(ab, "\r\n", 2);    /* raw mode clears OPOST: explicit CR */
    }
}

/* Status bar in reverse video (SGR 7m). Left: filename, dirty flag, line
   count. Right, right-aligned: cursor line:col and scroll percentage.
   (spec 04 §7; reverse video researched in prep/colors.py.) */
void editorDrawStatusBar(struct abuf *ab) {
    abAppend(ab, "\x1b[7m", 4); /* SGR reverse video */
    char status[80], rstatus[80];
    int len = snprintf(status, sizeof(status), " %.20s %s %d lines",
                       E.filename ? E.filename : "[No Name]",
                       E.dirty ? "(modified)" : "", E.numrows);
    int rx = (E.cy < E.numrows) ? editorRowCxToRx(&E.row[E.cy], E.cx) + 1 : 1;
    int percent = 0;
    if (E.numrows > E.screenrows)
        percent = (E.rowoff * 100) / (E.numrows - E.screenrows);
    int rlen = snprintf(rstatus, sizeof(rstatus), "%d:%d %d%%",
                        E.cy + 1, rx, percent);
    if (len > E.screencols) len = E.screencols;
    abAppend(ab, status, len);
    while (len < E.screencols) {
        if (E.screencols - len == rlen) {
            abAppend(ab, rstatus, rlen);
            break;
        } else {
            abAppend(ab, " ", 1);
            len++;
        }
    }
    abAppend(ab, "\x1b[m", 3); /* SGR reset */
    abAppend(ab, "\r\n", 2);
}

/* Message bar: transient text that fades after 5 seconds (spec 04 §7). */
void editorDrawMessageBar(struct abuf *ab) {
    abAppend(ab, "\x1b[K", 3);
    int msglen = strlen(E.statusmsg);
    if (msglen > E.screencols) msglen = E.screencols;
    if (msglen && time(NULL) - E.statusmsg_time < 5)
        abAppend(ab, E.statusmsg, msglen);
}

/* Compose and flush one full frame: hide cursor, home, draw rows + status
   + message bars, place the cursor at the edit position, show cursor —
   all as one write(). The frame pattern follows prep/clear-screen.py,
   prep/cursor-move.py and prep/game-of-life.py. */
void editorRefreshScreen(void) {
    editorScroll();
    struct abuf ab = ABUF_INIT;
    abAppend(&ab, "\x1b[?25l", 6); /* DECTCEM reset: hide cursor */
    abAppend(&ab, "\x1b[H", 3);    /* CUP: cursor home */
    editorDrawRows(&ab);
    editorDrawStatusBar(&ab);
    editorDrawMessageBar(&ab);
    char buf[32];
    snprintf(buf, sizeof(buf), "\x1b[%d;%dH",
             (E.cy - E.rowoff) + 1, (E.rx - E.coloff) + 1);
    abAppend(&ab, buf, (int)strlen(buf)); /* CUP: to the edit position */
    abAppend(&ab, "\x1b[?25h", 6); /* DECTCEM set: show cursor */
    write(STDOUT_FILENO, ab.b, (size_t)ab.len); /* single flush */
    abFree(&ab);
}

/*** input ***/

/* Set the transient message shown in the message bar. */
void editorSetStatusMessage(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(E.statusmsg, sizeof(E.statusmsg), fmt, ap);
    va_end(ap);
    E.statusmsg_time = time(NULL);
}

/* Inline prompt in the message bar: used by find and by save-as. Each
   keystroke redraws, and the optional callback (editorFindCallback) is
   invoked so the search can react incrementally. ESC returns NULL (cancel);
   Enter returns a freshly allocated string. */
char *editorPrompt(char *prompt, void (*callback)(char *, int)) {
    size_t bufsize = 128;
    char *buf = malloc(bufsize);
    size_t buflen = 0;
    buf[0] = '\0';
    while (1) {
        editorSetStatusMessage(prompt, buf);
        editorRefreshScreen();
        int c = editorReadKey();
        if (c == DEL_KEY || c == CTRL_KEY('h') || c == BACKSPACE) {
            if (buflen != 0) buf[--buflen] = '\0';
        } else if (c == '\x1b') {
            editorSetStatusMessage("");
            if (callback) callback(buf, c);
            free(buf);
            return NULL;
        } else if (c == '\r') {
            if (buflen != 0) {
                editorSetStatusMessage("");
                if (callback) callback(buf, c);
                return buf;
            }
        } else if (!iscntrl(c) && c < 128) {
            if (buflen == bufsize - 1) {
                bufsize *= 2;
                char *nb = realloc(buf, bufsize);
                if (!nb) continue;
                buf = nb;
            }
            buf[buflen++] = c;
            buf[buflen] = '\0';
        }
        if (callback) callback(buf, c);
    }
}

/* Leave the terminal clean: show the cursor, clear the screen, home, then
   exit — atexit(disableRawMode) restores termios. */
void editorExit(void) {
    write(STDOUT_FILENO, "\x1b[?25h", 6); /* DECTCEM: show cursor */
    write(STDOUT_FILENO, "\x1b[2J", 4);   /* ED: erase screen */
    write(STDOUT_FILENO, "\x1b[H", 3);    /* CUP: cursor home */
    exit(0);
}

/* Route one keypress. The quit safeguard follows the researched minimal
   pattern: while the buffer is dirty, Ctrl-Q must be pressed a few times,
   with the count shown in the message bar (spec 04 §8; snaptoken/kilo ch.5
   "Quit confirmation", antirez/kilo). Ctrl-C is treated the same way so the
   terminal is always restored on exit. */
void editorProcessKey(int c) {
    static int quit_times = TEDIT_QUIT_TIMES;
    switch (c) {
        case '\r':
        case '\n':
            editorInsertNewline();
            break;
        case CTRL_KEY('q'):
        case CTRL_KEY('c'):
            if (E.dirty && quit_times > 0) {
                editorSetStatusMessage("WARNING!!! File has unsaved changes. "
                    "Press Ctrl-%c %d more times to quit.",
                    c == CTRL_KEY('q') ? 'Q' : 'C', quit_times);
                quit_times--;
                return;
            }
            editorExit();
            break;
        case CTRL_KEY('s'):
            editorSave();
            break;
        case CTRL_KEY('f'):
            editorFind();
            break;
        case HOME_KEY:
            E.cx = 0;
            break;
        case END_KEY:
            if (E.cy < E.numrows) E.cx = E.row[E.cy].size;
            break;
        case BACKSPACE:
        case CTRL_KEY('h'):
        case DEL_KEY:
            if (c == DEL_KEY) editorMoveCursor(ARROW_RIGHT);
            editorDelChar();
            break;
        case PAGE_UP:
        case PAGE_DOWN:
            if (c == PAGE_UP) {
                E.cy = E.rowoff;
            } else if (c == PAGE_DOWN) {
                E.cy = E.rowoff + E.screenrows - 1;
                if (E.cy > E.numrows) E.cy = E.numrows;
            }
            {
                int times = E.screenrows;
                while (times--)
                    editorMoveCursor(c == PAGE_UP ? ARROW_UP : ARROW_DOWN);
            }
            break;
        case ARROW_UP:
        case ARROW_DOWN:
        case ARROW_LEFT:
        case ARROW_RIGHT:
            editorMoveCursor(c);
            break;
        case CTRL_KEY('l'):
        case '\x1b':
            break; /* redraw / lone ESC: nothing to do */
        default:
            /* Insert printable chars and real tabs (0x09). Tabs are stored
               as-is in chars and expanded only in render, so they survive a
               save. NUL (0x00) would truncate a row, so it is excluded. */
            if (c > 0 && (c >= 32 || c == '\t')) editorInsertChar(c);
            break;
    }
    quit_times = TEDIT_QUIT_TIMES; /* any other key resets the countdown */
}

/*** init ***/

/* Query the window size (ioctl; prep/terminal-info.py) and install the
   signal handlers. screenrows has the status and message bars subtracted. */
void updateWindowSize(void) {
    if (getWindowSize(&E.screenrows, &E.screencols) == -1)
        die("getWindowSize");
    E.screenrows -= 2;
    if (E.screenrows < 1) E.screenrows = 1;
    if (E.screencols < 1) E.screencols = 1;
}

void initEditor(void) {
    E.cx = 0; E.cy = 0; E.rx = 0;
    E.rowoff = 0; E.coloff = 0;
    E.numrows = 0; E.row = NULL;
    E.dirty = 0; E.filename = NULL;
    E.statusmsg[0] = '\0'; E.statusmsg_time = 0;
    E.syntax = NULL;
    updateWindowSize();

    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_flags = SA_RESTART; /* keep read(2) running through SIGWINCH */
    sigemptyset(&sa.sa_mask);
    sa.sa_handler = handleSigWinCh;
    if (sigaction(SIGWINCH, &sa, NULL) == -1) die("sigaction");
    sa.sa_handler = handleSigTerm;
    if (sigaction(SIGINT, &sa, NULL) == -1) die("sigaction");
    if (sigaction(SIGTERM, &sa, NULL) == -1) die("sigaction");
}

int main(int argc, char *argv[]) {
    if (argc > 2) {
        fprintf(stderr, "Usage: tedit [FILE]\r\n");
        return 1;
    }
    enableRawMode();  /* before initEditor so the DSR fallback can read */
    initEditor();
    if (argc >= 2) editorOpen(argv[1]);
    editorSetStatusMessage("HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find");
    while (1) {
        editorRefreshScreen();
        int c = editorReadKey();
        if (c == KEY_RESIZE) continue; /* size already re-queried; redraw */
        editorProcessKey(c);
    }
    return 0;
}