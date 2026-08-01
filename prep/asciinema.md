# Asciinema Conventions

Rules for the terminal-escape-sequence demos and the asciinema recordings
under `prep/ASCIINEMA/`. These were refined over several iterations of
feedback while building the `clear-screen`, `cursor-move`, and other demos.

## File layout

- `prep/` holds the Python sources for all demos (no recording artifacts).
- Recordings (`.cast`, `.gif`, per-demo `-frames/` folders) live in the
  content repo at `content/<repo>/ASCIINEMA/` — not in the build repo.
- `prep/asciinema.md` (this file) documents the conventions.

The recording tools (`record-tmux-shell.sh`, `gif_to_frames.py`) are provided
by the `asciinema-record` skill at `skills/asciinema-record/scripts/` in the
Democrt[AI]{SE} workspace. Copy them into `prep/` when recording from this
repo, or invoke them directly from the skill's scripts directory. Do not
re-vendor them here — the skill is the single source.

Shared helpers live in `prep/_clear_common.py`:

- `clear_entire_screen()` — `CSI 2 J`
- `cursor_home()` — `CSI H`
- `move_cursor(row, col)` — `CSI row ; col H`
- `print_at(row, col, text)` — absolute-positioned print
- `pause(seconds)` — sleep
- Hold constants: `INTRO_HOLD`, `PROMPT_HOLD`, `OUTRO_HOLD`, `DEMO_PAUSE`

`gif_to_frames.py` (from the skill's scripts dir) is the CLI tool that dumps
every frame of a `.gif` into a numbered PNG folder.

## Commands

### Install / versions

    asciinema --version
    agg --version
    which asciinema agg python3

### Recording (asciinema)

    asciinema rec --headless --window-size 80x24 --return -q \
      -c "python3 -u clear-screen-demo1.py" --overwrite \
      ASCIINEMA/clear-screen-demo1.cast

Key flags:
- `--headless` — runs the child in a NullTty; no interference with the
  current terminal. Auto-enabled when no TTY is available (CI, piped shells).
- `--window-size 80x24` — sets the PTY size. Use the same size for every
  demo in the same batch for consistent frames.
- `--return` — propagate the child's exit code (non-zero = cast is invalid).
- `-q` — suppress asciinema's own "session started / Press ctrl+d" banner
  so the cast is clean.
- `-c "python3 -u clear-screen-demo1.py"` — the command to record.
  `python3 -u` (unbuffered) ensures output is captured in real time.
- `--overwrite` — allows re-recording without prompting.

Full help:

    asciinema rec --help

### Rendering (agg)

    agg --font-size 14 --theme asciinema --speed 0.5 --last-frame-duration 3 \
      ASCIINEMA/clear-screen-demo1.cast ASCIINEMA/clear-screen-demo1.gif

Key flags:
- `--font-size 14` — readable at 80x24.
- `--theme asciinema` — the default dark background theme.
- `--speed 0.5` — half-speed playback gives the viewer time to read each
  state.
- `--last-frame-duration 3` — holds the final frame for 3 seconds so the
  closing info frame settles.

Full help:

    agg --help

### Frame dump

    python3 ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/gif_to_frames.py ASCIINEMA/clear-screen-demo1.gif ASCIINEMA/clear-screen-demo1-frames

Output: `clear-screen-demo1-frames/frame-00.png` ... `frame-N.png`

### Inspecting a cast file

    head -c 400 ASCIINEMA/clear-screen-demo1.cast | cat -A

Or with Python (decode every event):

    python3 -c "
    import json
    lines = open('ASCIINEMA/clear-screen-demo1.cast').read().splitlines()
    evs = [json.loads(l) for l in lines[1:] if l.strip()]
    for i, e in enumerate(evs):
        short = e[2].replace('\r\n','\\\\n').replace('\x1b[','<ESC[')[:80]
        print(f'[{i:2}] +{e[0]:.2f}s  {short}')
    "

### Inspecting a GIF

    file clear-screen.gif
    python3 -c "from PIL import Image; im=Image.open('clear-screen.gif'); print(f'frames={im.n_frames} size={im.size}')"

### Smoke-testing a demo script (no TTY required)

    timeout 60 python3 -u clear-screen-demo1.py </dev/null >/dev/null 2>&1
    echo "exit=$?"

### Replaying a cast event stream onto a grid (debug)

    python3 - <<'EOF'
    import json
    lines = open('ASCIINEMA/clear-screen-demo3.cast').read().splitlines()
    evs = [json.loads(l) for l in lines[1:] if l.strip()]
    grid = [[' '] * 80 for _ in range(24)]
    r, c = 0, 0
    for i, e in enumerate(evs):
        if i < 6: continue  # skip info frames
        t, code, data = e
        j = 0
        while j < len(data):
            ch = data[j]
            if ch == '\x1b' and j+1 < len(data) and data[j+1] == '[':
                k = j + 2; p = ''
                while k < len(data) and data[k] not in 'ABCDEFGHJKSTfmnsulh':
                    p += data[k]; k += 1
                cmd = data[k]; k += 1
                nums = [int(x) if x else 1 for x in p.split(';')] if p else [1]
                if cmd == 'H':
                    r = (nums[0]-1) if len(nums) > 0 else 0
                    c = (nums[1]-1) if len(nums) > 1 else 0
                elif cmd == 'A': r = max(0, r - nums[0])
                elif cmd == 'B': r = min(23, r + nums[0])
                elif cmd == 'C': c = min(79, c + nums[0])
                elif cmd == 'D': c = max(0, c - nums[0])
                j = k
            elif ch in '\r\n': j += 1
            else:
                if 0 <= r < 24 and 0 <= c < 80:
                    grid[r][c] = ch
                c += 1; j += 1
    for ri in range(5, 20):
        line = ''.join(grid[ri][30:55]).rstrip()
        if line: print(f'row {ri:2}: "{line}"')
    EOF

### Full pipeline (record + render + dump)

    for n in 1 2 3 4; do
      rm -f "ASCIINEMA/clear-screen-demo$n.cast" "ASCIINEMA/clear-screen-demo$n.gif"
      rm -rf "ASCIINEMA/clear-screen-demo${n}-frames"
      asciinema rec --headless --window-size 80x24 --return -q \
        -c "python3 -u clear-screen-demo$n.py" --overwrite \
        "ASCIINEMA/clear-screen-demo$n.cast" >/dev/null 2>&1
      agg --font-size 14 --theme asciinema --speed 0.5 --last-frame-duration 3 \
        "ASCIINEMA/clear-screen-demo$n.cast" "ASCIINEMA/clear-screen-demo$n.gif" 2>&1 | tail -1
      python3 ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/gif_to_frames.py "ASCIINEMA/clear-screen-demo$n.gif" "ASCIINEMA/clear-screen-demo${n}-frames"
    done

### Re-recording all demos in batch

    for n in 1 2 3; do
      timeout 90 python3 "cursor-move-demo$n.py" </dev/null >/dev/null 2>&1
      asciinema rec --headless --window-size 80x24 --return -q \
        -c "python3 -u cursor-move-demo$n.py" --overwrite \
        "ASCIINEMA/cursor-move-demo$n.cast" >/dev/null 2>&1
      agg --font-size 14 --theme asciinema --speed 0.5 --last-frame-duration 3 \
        "ASCIINEMA/cursor-move-demo$n.cast" "ASCIINEMA/cursor-move-demo$n.gif" 2>&1 | tail -1
      python3 ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/gif_to_frames.py "ASCIINEMA/cursor-move-demo$n.gif" "ASCIINEMA/cursor-move-demo${n}-frames"
    done

## Tmux-based recording (interactive tools + shell prompt)

Use `record-tmux-shell.sh` (from the skill's scripts dir) for recording
interactive tools where you want the shell prompt visible in the GIF. tmux
provides the PTY; asciinema records the attachment.

### How it works

1. A dummy tmux session keeps the server alive.
2. An interactive `bash` shell starts (prompt appears).
3. Commands from a file are typed via `tmux send-keys` in the
   background, WHILE asciinema records — the interaction is captured
   live.
4. The shell prompt returns after each command (or after the tool exits).

### Usage

    ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/record-tmux-shell.sh <commands_file> [output.cast] [cols] [rows] [timeout]

    # Interactive tool:
    echo -e "python3 -u key-classifier.py\na\nb\nC-a\nC-b\nUp\nDown\nLeft\nRight\nq" \
      > /tmp/kc.txt
    ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/record-tmux-shell.sh /tmp/kc.txt ASCIINEMA/key-classifier.cast 80 24 30

    # Simple bash commands:
    echo -e "date\nls -la\npwd" > /tmp/cmds.txt
    ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/record-tmux-shell.sh /tmp/cmds.txt ASCIINEMA/shell-demo.cast 80 24 20

### Commands file format

One command or keystroke per line. Blank lines and `#` comments ignored.

- **Shell commands** (multi-character lines): Enter is appended
  automatically. The command runs and the prompt returns.
- **Keystrokes** (single characters, `C-x`, `Up`, `Down`, etc.):
  No Enter appended. The classifier reads them byte-by-byte in
  cbreak mode.

Keystroke names follow tmux's `send-keys` conventions:
`C-a`, `C-b`, `Up`, `Down`, `Left`, `Right`, `F1`–`F4`, `Escape`,
`Home`, `End`, `PageUp`, `PageDown`, `Insert`, `Delete`.

### What the GIF shows

For key-classifier:

1. Shell prompt appears (e.g., `openclaw@git:... >>`)
2. `python3 -u key-classifier.py` is typed and executed
3. Classifier header appears
4. Each keystroke classified in real-time:
   - `a` → "Printable ASCII: 'a' | hex: 61"
   - `C-a` → "Ctrl character: Ctrl-A | hex: 01"
   - `Up` → "Multi-byte escape: Up arrow | raw: 1B 5B 41"
5. `q` → "'q' pressed — exiting."
6. Shell prompt returns, tmux session ends

### Rendering and frame dump

    agg --font-size 14 --theme asciinema --speed 0.5 --last-frame-duration 3 \
      ASCIINEMA/key-classifier.cast ASCIINEMA/key-classifier.gif

    python3 ~/CONTENT_TOP/Democrt_AI_SE/skills/asciinema-record/scripts/gif_to_frames.py ASCIINEMA/key-classifier.gif ASCIINEMA/key-classifier-frames

## Per-demo structure

Each demo script follows the same skeleton:

```python
def show_info_frame(lines, hold=INTRO_HOLD):
    clear_entire_screen()
    cursor_home()
    for r, t in enumerate(lines, start=1):
        print_at(r, 1, t.ljust(78))
    pause(hold)
```

Every demo's `main()` chains together info frames, live screens, and
sequences using `show_info_frame`, `show_position_screen` (or equivalent),
the actual escape-sequence call, and the post-state live screen.

## The 6-step pattern

For each escape sequence being demonstrated, the demo follows this exact
frame order:

1. **Info A** — title + escape sequence + what to expect. NO "Plan" steps.
2. **Live (before, first time)** — the screen state before the sequence.
3. **Info B** — "Sending the sequence now." with the raw sequence shown.
4. **Live (before, re-anchored)** — the screen state again, to anchor the
   cursor position right before the action. The cursor is freshly placed
   at the exact starting point.
5. **The actual sequence** — the escape sequence runs, then `pause()`.
6. **Live (after)** — the new screen state, with the cursor block visible
   at the new position.

Between sequences within a single demo file, a short info frame announces
the next section ("Sending the next demo now..."). At the very end, a
final info frame summarizes what was demonstrated.

```
[Info A] [Live before 1] [Info B] [Live before 2] [Action] [Live after]
                  \                                                  /
                   same content twice (re-anchor) + actual sequence
```

The re-anchor step (Live before 2) is what makes the action visible in the
recording: by drawing the starting state cleanly twice, the GIF's frame
collapsing never produces a confusing "the cursor teleported" frame.

## Information-frame rules

- **Use "Expect:" not "Plan:"** in the first info frame. Plan is
  implementation steps ("1. Show... 2. Send..."). Expect is what the
  viewer should see ("starting at (8,5), sending CSI 2 A moves the cursor
  to (6,5)").
- **No empty on-screen text** during the live frames. The only text on a
  live frame is a single one-line label like `Cursor at row 8, col 5 - starting position`.
  No "Step 1: ...", no "Trace:", no on-screen sequence labels.
- **The cursor block is the demo.** For cursor-move demos, every live frame
  shows the cursor at a specific position. The label is for context, not
  as a substitute for the visible cursor.
- **No text overlay after the action.** Once the live (after) frame is
  drawn, the next frame is always a clean info frame. Never put explanatory
  text on the same screen as the action result (it fights with the cursor
  and the action's visual evidence).
- **`ljust(78)` on every print.** Prevents row collisions when a previous
  print is longer than the current one.
- **Padded writes when overwriting.** When a sequence writes to a row that
  might already contain text, pad with trailing spaces so any leftover from
  a previous shorter write is overwritten cleanly.

## Live-frame rules

- **For position demos** (cursor-move): use `show_position_screen(row, col, label)`
  that prints a one-line label and places the cursor at the exact position
  with `move_cursor(row, col)`.
- **For content demos** (clear-screen): the screen is mostly empty plus
  the demonstrated content; no on-screen prompts or step labels.
- **For draw demos** (cursor-move-demo2 box, cursor-move-demo3 line):
  the draw happens once, then `OUTRO_HOLD` keeps the result on screen
  before transitioning to the closing info frame.
- **For build-up demos** (cursor-move-demo3 line): each `+` is its own
  frame, with the cursor block visibly advancing. After the last cell
  is drawn, no text is overlaid - the next frame is the closing info.

## Sequence-sending rules (Info B)

- Keep the sequence on its own line. Format: `  ESC [ n A   (description)`.
- Show the **escape form** (the `ESC [ ...` representation) not the
  Python function name. The viewer should be able to copy the sequence
  by hand.
- For multi-step sequences (e.g. drawing a box), enumerate them:
  ```
    ESC [ 5 ; 10 H     - move to top-left
    ESC [ 6 ; 10 H ... - draw sides
  ```
- Include the **expectation** in the same info frame, as a one-line
  `Expect:` footer if it's short.

## Sequence-action rules

- **No `stty raw` or `tty.setraw`.** These break Enter handling in asciinema
  (raw mode disables CR-to-LF translation) and are not needed - the demos
  write to stdout only and never read stdin.
- **No `sys.stdin.readline()`.** Replace with `time.sleep()` or `pause()`.
- **For relative-move demos**, after drawing the starting state, **place
  the cursor explicitly with `move_cursor`** before sending the sequence.
  This anchors the cursor and prevents the prompt-writing logic from
  accidentally moving it.
- **For draw demos (line, box)**, write each cell deliberately. If
  writing a single character advances the cursor, account for that
  (either use CUP for the next cell, or `cursor_back` after the write
  to restore the column).
- **For cross-shaped draws with relative moves**, drawing each arm on
  a separate row/column requires accounting for the write-advance.
  The simplest robust approach: write a whole arm as a string of `+`s,
  or just draw a horizontal/vertical line where the natural advance
  is the desired direction.

## Recording rules

- **Use `--headless --window-size 80x24 --return -q`** for asciinema. The
  recording captures a real PTY-backed session so the cursor block and
  escape sequences render correctly.
- **Use `--speed 0.5 --last-frame-duration 3`** for agg. Half-speed gives
  the viewer time to read each state; the 3-second last-frame hold lets the
  final state settle.
- **Use `INTRO_HOLD = 4.0` and `OUTRO_HOLD = 4.0`** so the first and
  last info frames stay on screen long enough to read. `PROMPT_HOLD = 3.0`
  for the in-between "sending now" frames. `DEMO_PAUSE = 2.5` for live
  states.
- **Use `python3 -u` (unbuffered)** when invoking the demo from asciinema
  so output is captured in real time.
- **Use `--overwrite`** to allow re-recording.
- **`-q` is critical** — without it, asciinema's "Recording to ... Press
  <ctrl+d> to stop" banner leaks into the cast, which is visible in the
  recording and confuses the info frames.

## Frame-collision rules

- **Don't `clear_entire_screen()` mid-demo unless you mean it.** A clear
  between sections is fine, but inside a section it wipes the previous
  live state and confuses the viewer.
- **Don't put two `print_at` calls on the same row** unless the second
  is a deliberate overwrite. The script's `ljust(78)` padding handles
  this when the second string is at least as long as the first.
- **Don't use `print()` (which appends `\n`) to add labels to a live
  frame** - the newline moves the cursor to a new row and may collide
  with the demonstrated content. Use `print_at(row, col, ...)` instead.
- **CUP/CUU/CUD/CUF/CUB calls inside demo functions can shift the cursor**
  in unexpected ways. After every draw or move, the next live frame
  should explicitly call `move_cursor` (or `print_at`) to re-anchor.

## Per-demo artifact naming

- `demo.cast` (in `ASCIINEMA/`) - the asciinema v3 cast file
- `demo.gif` (in `ASCIINEMA/`) - the rendered GIF
- `demo-frames/frame-NN.png` (in `ASCIINEMA/`) - individual frames
  for inspection

Names: `clear-screen-demoN.{cast,gif,frames}`, `cursor-move-demoN.{cast,gif,frames}`,
`key-classifier.{cast,gif,frames}`, `shell-demo.{cast,gif,frames}`, and
similar for any future demo.

## Files in prep/

- The Python demo sources (`clear-screen-demo*.py`, `cursor-move-demo*.py`,
  `key-classifier.py`, `terminal-viewport-combined.py`, `_clear_common.py`).
- `asciinema.md` — this conventions doc.

The recording tools are NOT vendored here. They live in the
`asciinema-record` skill at `skills/asciinema-record/scripts/`
(`record-tmux-shell.sh`, `gif_to_frames.py`). Copy them into `prep/`
when recording.

## What's not here

These demos do NOT have an asciinema recording:

- `prep/input-orchestration.py` - interactive diagnostic. Could be
  recorded with `record-tmux-shell.sh` if needed.
