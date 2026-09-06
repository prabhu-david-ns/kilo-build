# Democrt[AI]{SE} — Kilo Series Index

Canonical index of the published Kilo series pieces. Every post in the series links back here;
this is the continuity anchor (created retroactively 2026-09-06 — earlier posts predate the index).

**Series:** We are building Kilo as part of the **Democrt[AI]{SE}** series — reliving the joy of
building classic software with a modest LLM. Build repo: https://github.com/prabhu-david-ns/kilo-build

**How to read this table:** each row = one LinkedIn piece (video + lead-in post).
`LinkedIn URL` is filled in by **Prabhu after posting** (HTA cannot see LinkedIn).
Code links point into this repo (public).

| # | Piece | Posted | Code / files | LinkedIn URL |
|---|-------|--------|--------------|--------------|
| L0 | Series Introduction | 2026-08-08 | [repo root](https://github.com/prabhu-david-ns/kilo-build) | _fill after posting_ |
| L1 | Terminals 101 (foundations) | 2026-08-08 | [prep/terminal-info.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/terminal-info.py) | _fill after posting_ |
| L2 | Meet Kilo | 2026-08-08 | [repo root](https://github.com/prabhu-david-ns/kilo-build) | _fill after posting_ |
| L3 | Raw Mode deep dive | 2026-08-22 | [repo root](https://github.com/prabhu-david-ns/kilo-build) | _fill after posting_ |
| V4 | Clear the Screen (CSI 2J/0J/1J/3J) | 2026-08-17 | [prep/clear-screen.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/clear-screen.py) + [demos 1-4](https://github.com/prabhu-david-ns/kilo-build/tree/main/prep) | _fill after posting_ |
| V5 | Move the Cursor (CUU/CUD/CUF/CUB, CUP) | 2026-08-22 | [prep/cursor-move.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/cursor-move.py) + [demos 1-3](https://github.com/prabhu-david-ns/kilo-build/tree/main/prep) | _fill after posting_ |
| V6 | 256 Colors (SGR) | 2026-08-24..30 | [prep/colors.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/colors.py) | _fill after posting_ |
| V7 | A Keypress's Journey (physical key → read()) | 2026-08-24..30 | [prep/key-classifier.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/key-classifier.py) · [prep/input-orchestration.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/input-orchestration.py) | _fill after posting_ |
| V8 | Bytes to Pixels (write() → render) | 2026-08-24..30 | [prep/terminal-viewport-combined.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/terminal-viewport-combined.py) | _fill after posting_ |
| G | Your Terminal Is a Game Console (Game of Life) | 2026-08-24..30 | [prep/game-of-life.py](https://github.com/prabhu-david-ns/kilo-build/blob/main/prep/game-of-life.py) | _fill after posting_ |
| 10 | tedit code walkthrough | ✅ published (date ← Prabhu) | [.specs/04-terminal-text-editor-c.md](https://github.com/prabhu-david-ns/kilo-build/blob/main/.specs/04-terminal-text-editor-c.md) | _fill after posting_ |
| 11 | how close we got (build/run vs original) | ✅ published (date ← Prabhu) | [.specs/05](https://github.com/prabhu-david-ns/kilo-build/tree/main/.specs) | _fill after posting_ |
| 12 | Kilo series close (map + all 12 posts) | ✍️ drafted — review ([kilo-content PR #14](https://github.com/prabhu-david-ns/kilo-content/pull/14)) | [repo root](https://github.com/prabhu-david-ns/kilo-build) | _fill after posting_ |

**Close-out (2026-09-06):** all 12 pieces published (per Prabhu); kilo-build merged: spec 04/05, impl 04 (tedit) + impl 05 (byte-identical to 04 — one canonical `tedit.c` kept, provenance in PRs #10/#12), POSTS-INDEX. Series formally closes with piece 12.

**Maintenance rule (going forward):** every new Democrt[AI]{SE} series keeps a `POSTS-INDEX.md`
in its public build repo. HTA creates the row in the drafts PR; Prabhu fills the `LinkedIn URL`
column after each manual post. New posts reference the previous piece by name + `<<prev-url>>`
marker, and carry GitHub file links for everything they discuss.