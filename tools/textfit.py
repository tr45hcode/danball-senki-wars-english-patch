#!/usr/bin/env python3
"""Measure and word-wrap English markup for the game's global fonts.

Advance widths come from the global font tables (01000/007_RMD etc.): the
first 78 glyphs (ASCII, ±) are proportional, everything after is one cell
wide. Measured in-game: no extra letter spacing.

Dialogue box: 319 px per line (measured in-game; the game hard-wraps mid-word
beyond that) and 2 lines (a third line is drawn below the box). For
comparison, Japanese dialogue never exceeds 308 px (22 full-width chars).
"""
from rmd import GLOBAL_CHARS

_PROPORTIONAL = {
    14: [6, 13, 12, 4, 5, 5, 9, 14, 4, 8, 4, 6, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11,
         4, 9, 11, 12, 12, 11, 12, 10, 10, 12, 12, 3, 10, 11, 9, 14, 12, 12, 11, 12, 11,
         12, 11, 12, 12, 14, 12, 12, 9, 7, 10, 10, 9, 9, 10, 6, 10, 9, 3, 3, 9, 3, 14, 9,
         10, 10, 10, 7, 9, 6, 9, 9, 13, 9, 9, 9],
    11: [5, 10, 10, 3, 4, 4, 7, 11, 3, 7, 3, 5, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 3, 7, 8, 9,
         9, 8, 9, 8, 7, 9, 9, 3, 8, 8, 7, 11, 9, 10, 8, 10, 9, 9, 9, 9, 9, 11, 9, 9, 7, 6,
         8, 8, 7, 7, 8, 5, 8, 7, 3, 3, 7, 3, 11, 7, 8, 8, 8, 5, 7, 5, 7, 7, 11, 7, 7, 7],
    10: [4, 9, 9, 3, 4, 4, 7, 10, 3, 6, 3, 4, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 3, 7, 8, 8, 9,
         8, 9, 7, 7, 9, 8, 2, 7, 8, 7, 10, 8, 9, 8, 9, 8, 8, 8, 8, 8, 10, 8, 8, 7, 5, 7, 7,
         6, 7, 7, 4, 7, 7, 2, 2, 6, 2, 10, 7, 7, 7, 7, 5, 7, 4, 7, 7, 10, 7, 7, 6],
}

# Global glyphs redrawn by fontpatch.py, with their new advance widths
OVERRIDE_WIDTHS = {'！': {14: 4, 11: 4, 10: 3}}   # now a narrow ASCII-style '!'

# ASCII the global font lacks -> closest glyph it has
SUBSTITUTIONS = {
    '!': '！', '"': '”', '[': '［', ']': '］', '<': '＜', '>': '＞', '~': '～',
    ';': ',', '—': '―', '–': '-', '’': "'", '‘': "'", '“': '”',
}

DIALOGUE_WIDTH = 319   # measured in-game: 29 digits (319 px) fit, 30 (330 px) wrap
DIALOGUE_LINES = 2
VAR_WIDTH = 60  # estimate for an inserted player/country name

# Files shown in a box other than the dialogue box: name -> (px per line, lines).
# Map chatter during missions is a one-line strip at the bottom of the top
# screen; a second line falls off-screen (seen in-game on 52508/53900). Its
# Japanese reaches 364 px on one line, so at least that much fits.
BOXES = {
    '52508_002_0000cd1c': (364, 1),
    '53900_002_0000d28c': (364, 1),
    # Probably chatter too (one-line, mid-mission) but unconfirmed: kept within
    # both boxes until seen in-game.
    '52541_002_0000cd3d': (319, 1),
    '53908_002_0000d294': (319, 1),
    '52589_002_0000cd6d': (319, 1),
    '52603_002_0000cd7b': (319, 1),
    '53904_002_0000d290': (319, 1),
    # Objective hint in the bottom screen's header bar (one line; Japanese max 280 px)
    '01000_095_001003e8': (280, 1),
    '53121_002_0000cf81': (319, 1),
    '53125_002_0000cf85': (319, 1),
    '53352_002_0000d068': (319, 1),
    '53368_002_0000d078': (319, 1),
    # Special Function descriptions (33300-33519, two copies): one line each,
    # Japanese max 280 px. Kept within that until seen in-game.
    '06525_005_0000197d': (280, 1),
    '06526_003_0000197e': (280, 1),
}


# Single messages of the system text (01000_098, and its 10 px copy 01000_100)
# shown in a box of their own: message id -> (px per line, lines).
SYSTEM_TEXT_FILES = ('01000_098_000203e8', '01000_100_000303e8')
MESSAGE_BOXES = {
    # Map examine hint, in the bottom screen's header bar like 01000_095.
    # Wrapped onto two lines, only the second line showed.
    17922: (280, 1),
}


def box(name, mid=None):
    """(px per line, lines) of the box a file's messages are shown in."""
    if name in SYSTEM_TEXT_FILES and mid in MESSAGE_BOXES:
        return MESSAGE_BOXES[mid]
    return BOXES.get(name, (DIALOGUE_WIDTH, DIALOGUE_LINES))


def limits(name, width, lines, mid=None):
    """Wrap limits for a message whose Japanese was width px x lines. A box
    listed in BOXES or MESSAGE_BOXES is used as is; otherwise the dialogue
    box, widened to fit the Japanese (system messages can have three lines)."""
    if name in BOXES or (name in SYSTEM_TEXT_FILES and mid in MESSAGE_BOXES):
        return box(name, mid)
    return max(DIALOGUE_WIDTH, width), max(DIALOGUE_LINES, lines)


def char_width(ch, cell=14):
    ch = SUBSTITUTIONS.get(ch, ch)
    if ch in OVERRIDE_WIDTHS:
        return OVERRIDE_WIDTHS[ch][cell]
    if ch not in GLOBAL_CHARS:
        return cell
    i = GLOBAL_CHARS.index(ch)
    widths = _PROPORTIONAL[cell]
    return widths[i] if i < len(widths) else cell


def normalize(text):
    """Apply substitutions outside [tags]; returns (text, unsupported chars)."""
    out, bad = [], set()
    for kind, s in _split_markup(text):
        if kind == 'c':
            out.append(s)
            continue
        s = ''.join(SUBSTITUTIONS.get(c, c) for c in s)
        bad.update(c for c in s if c not in GLOBAL_CHARS)
        out.append(s)
    return ''.join(out), bad


def _split_markup(text):
    """Split into ('t', str) text runs and ('c', '[...]') control tags."""
    parts, i, start = [], 0, 0
    while i < len(text):
        if text[i] == '[':
            if i > start:
                parts.append(('t', text[start:i]))
            end = text.index(']', i) + 1
            parts.append(('c', text[i:end]))
            i = start = end
        else:
            i += 1
    if start < len(text):
        parts.append(('t', text[start:]))
    return parts


def measure(segment, cell=14):
    """Width in pixels of a single line of markup (no [n]/[p])."""
    w = 0
    for kind, s in _split_markup(segment):
        if kind == 'c':
            # [var:N] player name, [x14:..] country name: both user-entered text
            w += VAR_WIDTH if s.startswith(('[var', '[x14')) else 0
        else:
            w += sum(char_width(c, cell) for c in s)
    return w


def wrap(text, max_width=DIALOGUE_WIDTH, max_lines=DIALOGUE_LINES, cell=14):
    """Greedy word wrap. Explicit [n] and [p] are kept; long lines are broken
    at spaces. Returns (markup, list of warnings)."""
    warnings = []
    pages_out = []
    trailing_p = text.endswith('[p]')
    body = text[:-3] if trailing_p else text
    for page in body.split('[p]'):
        lines_out = []
        for hard_line in page.split('[n]'):
            # leading spaces stay on the first word (fragments joined to a name)
            lead = len(hard_line) - len(hard_line.lstrip(' '))
            words = hard_line[lead:].split(' ')
            words[0] = hard_line[:lead] + words[0]
            line = ''
            for word in words:
                cand = f'{line} {word}' if line else word
                if line and measure(cand, cell) > max_width:
                    lines_out.append(line)
                    line = word
                else:
                    line = cand
            lines_out.append(line)
        for ln in lines_out:
            w = measure(ln, cell)
            if w > max_width:
                warnings.append(f'line is {w}px (max {max_width}): {ln!r}')
        if len(lines_out) > max_lines:
            warnings.append(f'{len(lines_out)} lines on one page (max {max_lines})')
        pages_out.append('[n]'.join(lines_out))
    return '[p]'.join(pages_out) + ('[p]' if trailing_p else ''), warnings
