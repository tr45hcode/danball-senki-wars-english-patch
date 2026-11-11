#!/usr/bin/env python3
"""English labels for textures with Japanese text drawn into them.

UI text that isn't in an RMD file is a sprite in a texture atlas: a UAIF
(or IMAG) image plus the UATD (or ATD-) entry with the same id, which lists
the sprite rectangles. This tool redraws such sprites in English.

ATD layout: 0x10 u32 1, 0x14 u32 count, 0x18 float atlas width, height,
then per sprite 28 bytes: float u0, v0, u1, v1 (0..1), float width, height
(pixels), u32 0.

Files, one pair per atlas, named <container>_<image entry index>:
  script/gfx/<name>.tsv   sprite<TAB>ja<TAB>en<TAB>options
  script/gfx/<name>.png   overlay: the English labels alone, atlas-sized,
                          transparent everywhere else

The build (build_patch.py) needs only the TSV and the PNG. For each row
it clears the sprite (or wipes the text off a badge, bg=rows) from the
original texture and draws the overlay's label on top, so the overlay
holds no game art. `render` draws the overlay from the TSV, with the look
(fill gradient, outline or shadow colour) sampled from the Japanese
sprite it replaces.

Row options, space separated (a row with sprite `*` sets defaults):
  font=heavy|bold|cond|plain   typeface (Fira Sans, see FONTS)
  font=pixel   built-in 5 px capitals for the 6 px high labels; two spaces
               in the English split it into a left and a right word
  size=N       cap height in px (default: 9/10 of the Japanese glyphs)
  mode=outline|shadow|none  what surrounds the letters (default: sampled)
  outline=N    outline width in px (default: sampled)
  align=l|c|r  where the text sits in the sprite (default: centred on the
               Japanese ink)
  valign=c     centre the text between the sprite's top and bottom
               (default: on the Japanese glyphs)
  like=N       take the colours from sprite N instead
  fill=RRGGBB[,RRGGBB]  fill colour (top,bottom) instead of the sampled one
  edge=RRGGBB  outline colour instead of the sampled one
  bg=N         start from a copy of sprite N (a blank button) instead of a
               transparent rectangle
  bg=rows      keep the sprite and paint over its text with each row's
               background colour (badges with a plain background); margin=N
               leaves N px at either end alone, thresh=N is how far a
               pixel must be from the background to count as text (60)
  pad=N        keep the text N px away from the sprite's edges
  rect=x,y,w,h use this atlas rectangle instead of the sprite's own
  in=x,y,w,h   replace only this part of the sprite (several rows may each
               take a part of one sprite)
English `A|B` stacks two lines; `~` removes the Japanese and draws nothing.

Usage:
  gfx.py list                         atlases and their sprite counts
  gfx.py sprites <name> <out.png>     numbered sprites, to read the Japanese
  gfx.py template <name>              write an empty TSV for an atlas
  gfx.py render [<name>...]           draw overlays (all TSVs by default)
  gfx.py preview <name> <out.png>     original and patched sprites side by side
  gfx.py copies                       find identical atlases in other containers
                                      and list them in script/gfx/copies.tsv

`render` needs the Fira Sans fonts (SIL Open Font License) installed.
"""
import glob
import os
import struct
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aif  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPK_DIR = os.path.join(ROOT, 'extracted', 'cpk')
GFX_DIR = os.path.join(ROOT, 'script', 'gfx')
IMAGE_TAGS = ('UAIF', 'IMAG')
ATLAS_TAGS = {'UAIF': 'UATD', 'IMAG': 'ATD_'}
FONTS = {'heavy': 'Fira Sans:style=ExtraBold Italic',
         'bold': 'Fira Sans:style=Bold',
         'cond': 'Fira Sans Condensed:style=ExtraBold Italic',
         'condbold': 'Fira Sans Condensed:style=Bold',
         'plain': 'Fira Sans:style=Medium',
         'condplain': 'Fira Sans Condensed:style=Medium'}
NARROWER = {'heavy': 'cond', 'bold': 'condbold', 'plain': 'condplain'}


# ---- atlas data ---------------------------------------------------------

def parse_atd(data):
    """Return a list of sprite rectangles (x, y, w, h) in pixels."""
    if data[:4] != b' DTA':
        raise ValueError('not an ATD atlas')
    count, = struct.unpack_from('<I', data, 0x14)
    tw, th = struct.unpack_from('<ff', data, 0x18)
    out = []
    for i in range(count):
        u0, v0, u1, v1, w, h = struct.unpack_from('<6f', data, 0x20 + i * 28)
        x0, y0 = round(u0 * tw), round(v0 * th)
        x1, y1 = round(u1 * tw), round(v1 * th)
        out.append((x0, y0, max(x1 - x0, 0), max(y1 - y0, 0)))
    return out


def entry_index(name):
    container, index = name.split('_')
    return container, int(index)


def find_atlas(entries, index):
    """entries: [(tag, id)] of a container in order. Return the index of
    the atlas entry paired with image entry `index`, or None."""
    tag, eid = entries[index]
    want = ATLAS_TAGS.get(tag.replace('-', '_'))
    for i, (t, e) in enumerate(entries):
        if t.replace('-', '_') == want and e == eid:
            return i
    return None


def _dir_entries(container):
    out = []
    for f in sorted(os.listdir(os.path.join(CPK_DIR, container))):
        out.append((f[4:8], int(f[9:17], 16), f))
    return out


def load_atlas(name):
    """Return (image, rects) of an atlas from the extracted files."""
    container, index = entry_index(name)
    ents = _dir_entries(container)
    by_index = {int(f[:3]): (t, e, f) for t, e, f in ents}
    tag, eid, fname = by_index[index]
    img = aif.decode(open(os.path.join(CPK_DIR, container, fname), 'rb').read())
    rects = []
    want = ATLAS_TAGS.get(tag)
    for t, e, f in ents:
        if t == want and e == eid:
            rects = parse_atd(open(os.path.join(CPK_DIR, container, f), 'rb').read())
    return img, rects


# ---- translation tables -------------------------------------------------

def parse_options(text):
    out = {}
    for part in text.split():
        k, _, v = part.partition('=')
        out[k] = v
    return out


def load_table(name):
    """Return (rows, defaults). rows: [(sprite, ja, en, options)]."""
    rows, defaults = [], {}
    with open(os.path.join(GFX_DIR, name + '.tsv'), encoding='utf-8') as f:
        for n, line in enumerate(f):
            cols = line.rstrip('\n').split('\t')
            if not cols[0] or cols[0].startswith('#') or (n == 0 and cols[0] == 'sprite'):
                continue
            cols += [''] * (4 - len(cols))
            if cols[0] == '*':
                defaults = parse_options(cols[3])
                continue
            if cols[2].strip():
                rows.append((int(cols[0]), cols[1], cols[2].strip(),
                             parse_options(cols[3])))
    return rows, defaults


def tables():
    return sorted(os.path.basename(p)[:-4]
                  for p in glob.glob(os.path.join(GFX_DIR, '*.tsv'))
                  if os.path.basename(p) != 'copies.tsv')


def row_rect(rects, sprite, opts):
    if 'rect' in opts:
        return tuple(int(v) for v in opts['rect'].split(','))
    return rects[sprite]


def copies():
    """{atlas name: table name} for atlases that are pixel-for-pixel copies
    of a translated one (script/gfx/copies.tsv, written by `gfx.py copies`)."""
    out = {}
    path = os.path.join(GFX_DIR, 'copies.tsv')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                cols = line.split()
                if len(cols) == 2 and not cols[0].startswith('#'):
                    out[cols[0]] = cols[1]
    return out


def targets():
    """{atlas name: table name} for every atlas the build redraws."""
    out = {n: n for n in tables()}
    out.update({k: v for k, v in copies().items() if v in out})
    return out


def changed_rects(rects, name):
    rows, defaults = load_table(name)
    return [rect for _, _, _, rect, _ in row_parts(rects, rows, defaults)]


def row_parts(rects, rows, defaults):
    """Yield (sprite, en, opts, rect, part) for each row: `rect` is the
    sprite's atlas rectangle, `part` the box inside it that the row
    replaces (all of it unless `in=` says otherwise)."""
    for sprite, _, en, row_opts in rows:
        opts = {**defaults, **row_opts}
        rect = row_rect(rects, sprite, opts)
        w, h = rect[2:]
        ix, iy, iw, ih = (int(v) for v in opts['in'].split(',')) if 'in' in opts else (0, 0, w, h)
        yield sprite, en, opts, rect, (ix, iy, ix + iw, iy + ih)


def background(img, rects, src, opts, rect, part):
    """What a row draws its English on, and the Japanese it removed.

    src is the part of the sprite the row replaces. Returns (base, marked):
    base is transparent, src with its text wiped (bg=rows), or the same
    part of a blank sprite (bg=N); marked is the removed text on a
    transparent image, or None when nothing was removed. Both come from
    the game's pixels, so the build recomputes them instead of storing
    them in the overlay."""
    w, h = rect[2:]
    size = (part[2] - part[0], part[3] - part[1])
    if opts.get('bg') == 'rows':
        return wipe_rows(src, int(opts.get('margin', 0 if 'in' in opts else h // 2)),
                         int(opts.get('thresh', 60)))
    if 'bg' in opts:
        bx, by, bw, bh = rects[int(opts['bg'])]
        base = img.crop((bx, by, bx + w, by + h)).crop(part)
        diff = ImageChops.difference(src.convert('RGB'), base.convert('RGB'))
        ink = diff.convert('L').point(lambda v: 255 if v > 40 else 0)
        marked = Image.new('RGBA', size, (0, 0, 0, 0))
        marked.paste(src, (0, 0), ink)
        return base, marked
    return Image.new('RGBA', size, (0, 0, 0, 0)), None


def apply(img, rects, name):
    """Return `img` with the translated sprites of table `name` redrawn:
    each row's background (see background) with the overlay's English on
    top. Used by the build."""
    rows, defaults = load_table(name)
    labels = Image.open(os.path.join(GFX_DIR, name + '.png')).convert('RGBA')
    if labels.size != img.size:
        raise ValueError(f'{name}.png is {labels.size}, atlas is {img.size}')
    out = img.copy()
    drawn = {}
    for sprite, en, opts, rect, part in row_parts(rects, rows, defaults):
        x, y, w, h = rect
        whole = drawn.get(rect) or img.crop((x, y, x + w, y + h))
        base, _ = background(img, rects, whole.crop(part), opts, rect, part)
        base.alpha_composite(labels.crop((x + part[0], y + part[1],
                                          x + part[2], y + part[3])))
        whole = whole.copy()
        whole.paste(base, part[:2])
        drawn[rect] = whole
        out.paste(whole, (x, y))
    return out


def patch_container(container, data):
    """Return {entry index: new AIF payload} for the atlases of MRON
    container `container` (its CPK name) that have a table. Used by the
    build; needs no fonts."""
    import mron
    todo = {n: t for n, t in targets().items() if n.split('_')[0] == container}
    if not todo:
        return {}
    entries = mron.parse(data)
    ids = [(e['tag'], e['id']) for e in entries]
    out = {}
    for name, table in sorted(todo.items()):
        index = entry_index(name)[1]
        payload = mron.read_entry(data, entries[index])
        atlas = find_atlas(ids, index)
        rects = parse_atd(mron.read_entry(data, entries[atlas])) if atlas is not None else []
        out[index] = aif.encode(payload, apply(aif.decode(payload), rects, table),
                                changed_rects(rects, table))
    return out


def find_copies():
    """Write copies.tsv: every atlas with the same pixels and sprite
    rectangles as a translated one."""
    import hashlib
    sigs = {}
    for container in sorted(os.listdir(CPK_DIR)):
        if not os.path.isdir(os.path.join(CPK_DIR, container)):
            continue
        ents = _dir_entries(container)
        for t, e, f in ents:
            if t not in IMAGE_TAGS:
                continue
            d = open(os.path.join(CPK_DIR, container, f), 'rb').read()
            try:
                hd = aif.header(d)
            except ValueError:
                continue
            atd = b''
            for t2, e2, f2 in ents:
                if t2 == ATLAS_TAGS[t] and e2 == e:
                    atd = open(os.path.join(CPK_DIR, container, f2), 'rb').read()
            sig = hashlib.sha1(d[hd['data']:] + atd).hexdigest()
            sigs.setdefault(sig, []).append(f'{container}_{int(f[:3]):03d}')
    have = set(tables())
    lines = []
    for names in sigs.values():
        src = [n for n in names if n in have]
        if src:
            lines += [f'{n}\t{src[0]}' for n in names if n not in have]
    with open(os.path.join(GFX_DIR, 'copies.tsv'), 'w', encoding='utf-8') as f:
        f.write('# atlas\tidentical to (written by gfx.py copies)\n')
        f.write(''.join(line + '\n' for line in sorted(lines)))
    return lines


# ---- 5 px pixel font ----------------------------------------------------
# For the 6 px high labels (column headers and the like), where an outline
# font turns to mush. Rows top to bottom, '#' = ink.

_PIXEL_ROWS = {
    'A': '.#. #.# ### #.# #.#', 'B': '##. #.# ##. #.# ##.', 'C': '.## #.. #.. #.. .##',
    'D': '##. #.# #.# #.# ##.', 'E': '### #.. ##. #.. ###', 'F': '### #.. ##. #.. #..',
    'G': '.## #.. #.# #.# .##', 'H': '#.# #.# ### #.# #.#', 'I': '# # # # #',
    'J': '..# ..# ..# #.# .#.', 'K': '#.# #.# ##. #.# #.#', 'L': '#.. #.. #.. #.. ###',
    'M': '#...# ##.## #.#.# #...# #...#', 'N': '#..# ##.# #.## #..# #..#',
    'O': '.#. #.# #.# #.# .#.', 'P': '##. #.# ##. #.. #..', 'Q': '.#. #.# #.# ### .##',
    'R': '##. #.# ##. #.# #.#', 'S': '.## #.. .#. ..# ##.', 'T': '### .#. .#. .#. .#.',
    'U': '#.# #.# #.# #.# ###', 'V': '#.# #.# #.# #.# .#.', 'W': '#...# #...# #.#.# ##.## #...#',
    'X': '#.# #.# .#. #.# #.#', 'Y': '#.# #.# .#. .#. .#.', 'Z': '### ..# .#. #.. ###',
    '0': '### #.# #.# #.# ###', '1': '.# ## .# .# .#', '2': '##. ..# .#. #.. ###',
    '3': '##. ..# .#. ..# ##.', '4': '#.# #.# ### ..# ..#', '5': '### #.. ##. ..# ##.',
    '6': '.## #.. ### #.# ###', '7': '### ..# .#. .#. .#.', '8': '### #.# ### #.# ###',
    '9': '### #.# ### ..# ##.', '.': '. . . . #', '/': '..# ..# .#. #.. #..',
    '-': '.. .. ## .. ..', ' ': '. . . . .', ':': '. # . # .', '+': '... .#. ### .#. ...',
}


def pixel_width(text):
    return sum(len(_PIXEL_ROWS[c].split()[0]) + 1 for c in text) - 1


def draw_pixel_label(size, text, look, opts):
    """Draw upper-case `text` in the 5 px pixel font, in the sprite's fill
    colour. Words separated by two spaces are pushed to the ends of the
    Japanese ink (two column headers in one sprite)."""
    w, h = size
    text = text.upper()
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    px = out.load()
    parts = text.split('  ')
    total = pixel_width(text.replace('  ', ' '))
    warn = None if total <= w else f'"{text}" is {total} px in a {w} px sprite'
    y0 = max(0, min(look['core'][0] + (look['core'][1] - look['core'][0] - 5 + 1) // 2, h - 5))
    if len(parts) == 2:
        starts = [look['left'], look['right'] - pixel_width(parts[1])]
    elif opts.get('align') == 'c':
        starts = [(look['left'] + look['right'] - total) // 2]
    else:
        starts = [look['left']]
    edge = look.get('outline') if look['mode'] != 'none' else None
    for part, x in zip(parts, starts):
        x = max(0, min(x, w - pixel_width(part)))
        for c in part:
            glyph = _PIXEL_ROWS[c].split()
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == '#' and 0 <= x + gx < w:
                        px[x + gx, y0 + gy] = look['fill'][0] + (255,)
            x += len(glyph[0]) + 1
    if edge:
        mask = out.getchannel('A').filter(ImageFilter.MaxFilter(3))
        under = Image.new('RGBA', size, edge + (0,))
        under.putalpha(mask)
        under.alpha_composite(out)
        out = under
    return out, warn


# ---- drawing ------------------------------------------------------------

_FONT_FILES = {}


def font_file(key):
    if key not in _FONT_FILES:
        path = subprocess.run(['fc-match', '-f', '%{file}', FONTS[key]],
                              capture_output=True, text=True).stdout
        if 'Fira' not in os.path.basename(path):
            sys.exit(f'font not found: {FONTS[key]} (install Fira Sans)')
        _FONT_FILES[key] = path
    return _FONT_FILES[key]


def font_for_cap(key, cap):
    """Font whose capital letters are `cap` px tall."""
    size = max(4, round(cap / 0.69))
    while True:
        f = ImageFont.truetype(font_file(key), size)
        b = f.getbbox('H')
        if b[3] - b[1] <= cap or size <= 4:
            return f
        size -= 1


def _lum(p):
    return (p[0] * 299 + p[1] * 587 + p[2] * 114) // 1000


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def analyse(sprite):
    """Look of a Japanese text sprite: the band of rows its main glyphs
    occupy (furigana above is left out), the ink's horizontal extent, the
    fill colours top and bottom, and what surrounds the fill: an outline
    (colour, width), a drop shadow (colour, offset) or nothing."""
    w, h = sprite.size
    px = sprite.load()
    rows = [[x for x in range(w) if px[x, y][3] > 128] for y in range(h)]
    counts = [len(r) for r in rows]
    if not any(counts):
        return None
    # bands of consecutive inked rows; the main glyphs are the tallest band
    bands, start = [], None
    for y in range(h + 1):
        ink = y < h and counts[y] > 0
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            bands.append((start, y))
            start = None
    top, bottom = max(bands, key=lambda b: (b[1] - b[0], b[0]))
    # furigana joined to the glyphs by their outlines: cut at the thinnest
    # row of the upper half when the rows above it are much sparser
    if bottom - top >= 14:
        peak = max(counts[top:bottom])
        cut = min(range(top + 2, top + (bottom - top) // 2 + 1),
                  key=lambda y: counts[y], default=None)
        if cut is not None and counts[cut] < peak * 0.35 and \
                max(counts[top:cut]) < peak * 0.75:
            top = cut + 1
    xs = [x for y in range(top, bottom) for x in rows[y]]
    left, right = min(xs), max(xs) + 1

    def mean(ps):
        n = len(ps)
        return tuple(sum(p[i] for p in ps) // n for i in range(3))

    # fill: the bright core of the glyphs
    ink = [(x, y, px[x, y]) for y in range(top, bottom) for x in rows[y]]
    peak = max(_lum(p) for _, _, p in ink)
    core = [(x, y, p) for x, y, p in ink if _lum(p) >= peak * 0.85]
    ys = sorted({y for _, y, _ in core})
    third = max(1, len(ys) // 3)
    fill_top = mean([p for _, y, p in core if y <= ys[third - 1]])
    fill_bottom = mean([p for _, y, p in core if y >= ys[-third]])
    fill = mean([p for _, _, p in core])
    # edge: everything visible that isn't fill-coloured
    edge = [(x, y, px[x, y]) for y in range(max(0, top - 4), min(h, bottom + 4))
            for x in range(w) if px[x, y][3] >= 32 and
            sum(abs(px[x, y][i] - fill[i]) for i in range(3)) > 90]
    look = {'top': top, 'bottom': bottom, 'left': left, 'right': right,
            'fill': (fill_top, fill_bottom), 'mode': 'none',
            'core': (ys[0], ys[-1] + 1)}
    if len(edge) * 8 >= len(core):
        far = sorted(edge, key=lambda e: -sum(abs(e[2][i] - fill[i]) for i in range(3)))
        look['outline'] = mean([p for _, _, p in far[:max(1, len(far) // 2)]])
        alphas = sorted(p[3] for _, _, p in edge)
        look['edge_alpha'] = alphas[len(alphas) * 3 // 4]
        cx0 = min(x for x, _, _ in core)
        cx1 = max(x for x, _, _ in core)
        above = ys[0] - min(y for _, y, _ in edge)
        below = max(y for _, y, _ in edge) - ys[-1]
        before = cx0 - min(x for x, _, _ in edge)
        after = max(x for x, _, _ in edge) - cx1
        if above <= 0 and before <= 0 and below > 0:
            look['mode'] = 'shadow'
            look['offset'] = (max(0, min(3, after)), max(1, min(3, below)))
        else:
            look['mode'] = 'outline'
            look['width'] = 1 if ys[-1] - ys[0] < 10 else 2
    return look


def draw_label(size, text, look, opts):
    """Draw `text` on a transparent image of `size` in the look of the
    Japanese sprite (see analyse). Returns the image and a fit warning."""
    w, h = size
    lines = text.split('|')
    mode = opts.get('mode', look['mode'])
    outline = int(opts.get('outline', look.get('width', 1))) if mode == 'outline' else 0
    dx, dy = look.get('offset', (1, 1)) if mode == 'shadow' else (0, 0)
    pad = int(opts.get('pad', 0))
    pad_l = pad_t = outline + pad
    pad_r, pad_b = outline + dx + pad, outline + dy + pad
    core = look['core'][1] - look['core'][0]
    # a gradient fill leaves only its bright end in `core`: go by the ink
    band = look['bottom'] - look['top'] - 2 * look.get('width', 0) - dy
    if core < band * 0.6:
        core = band
        look = {**look, 'core': (look['top'] + look.get('width', 0),
                                 look['top'] + look.get('width', 0) + band)}
    # Latin capitals look right a little shorter than kana and kanji
    cap = int(opts.get('size', 0)) or max(5, min(round(core * 0.92), h - pad_t - pad_b))
    if len(lines) > 1 and 'size' not in opts:
        cap = max(5, (h - pad_t - pad_b) // len(lines) - 2)
    key = opts.get('font', 'heavy')
    warn = None
    while True:
        font = font_for_cap(key, cap)
        # italic letters lean a little past their advance width
        lean = 'Italic' in FONTS[key]
        widths = [font.getlength(s) + lean for s in lines]
        asc = font.getbbox('H')
        cap_h = asc[3] - asc[1]
        gap = max(2, cap_h // 3)
        block = cap_h * len(lines) + gap * (len(lines) - 1)
        rise = max(0, asc[1] - font.getbbox(lines[0])[1])   # l, d, k above H
        drop = max(0, font.getbbox(lines[-1])[3] - asc[3])  # g, p, y below
        wide = max(widths) + pad_l + pad_r > w
        tall = rise + block + drop + pad_t + pad_b > h
        if not wide and not tall:
            break
        if wide and key in NARROWER:
            key = NARROWER[key]
        elif cap > 5:
            cap -= 1
        else:
            if wide:
                warn = f'"{text}" is {round(max(widths)) + pad_l + pad_r} px in a {w} px sprite'
            break
    if len(lines) > 1 or opts.get('valign') == 'c':
        y0 = (h - block) // 2
    else:
        y0 = look['core'][0] + (core - cap_h + 1) // 2
    # keep ascenders and descenders inside the sprite
    y0 = min(y0, h - pad_b - block - drop)
    y0 = max(y0, pad_t + rise)
    align = opts.get('align', '')
    mask = Image.new('L', size, 0)
    dr = ImageDraw.Draw(mask)
    for i, s in enumerate(lines):
        tw = round(widths[i])
        if align == 'l':
            x = look['left'] + pad_l if len(lines) == 1 else pad_l
            x = min(x, max(pad_l, w - pad_r - tw))
        elif align == 'r':
            x = w - pad_r - tw
        else:
            centre = (look['left'] + look['right'] - dx) / 2
            x = round(centre - tw / 2)
            x = max(pad_l, min(x, w - pad_r - tw))
        dr.text((x, y0 + i * (cap_h + gap) - asc[1]), s, font=font, fill=255)
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    if mode != 'none':
        if mode == 'outline':
            under = mask
            for _ in range(outline):
                under = under.filter(ImageFilter.MaxFilter(3))
            soft = under.filter(ImageFilter.GaussianBlur(0.7))
            under = ImageChops.lighter(under.point(lambda v: v * 235 // 255), soft)
        else:
            under = Image.new('L', size, 0)
            for k in range(1, max(dx, dy) + 1):
                step = ImageChops.offset(mask, min(k, dx), min(k, dy))
                under = ImageChops.lighter(under, step)
        alpha = look.get('edge_alpha', 255)
        out = Image.new('RGBA', size, look['outline'] + (0,))
        out.putalpha(under.point(lambda v: v * alpha // 255))
    # fill: vertical gradient over the text
    ft, fb = look['fill']
    grad = Image.new('RGBA', size)
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        t = min(1.0, max(0.0, (y - y0) / max(1, block - 1)))
        gd.line([(0, y), (w, y)],
                fill=tuple(round(ft[i] + (fb[i] - ft[i]) * t) for i in range(3)) + (255,))
    ink = Image.new('RGBA', size, (0, 0, 0, 0))
    ink.paste(grad, (0, 0), mask)
    out.alpha_composite(ink)
    return out, warn


def wipe_rows(sprite, margin, thresh=60):
    """Remove text drawn on a badge whose background only changes from row
    to row: every pixel that stands out from its row's background colour,
    `margin` px in from either end, becomes that colour. The background of
    a row is sampled at its two ends, so the area must be a little wider
    than the text. Returns the cleaned sprite and the removed text on a
    transparent image."""
    w, h = sprite.size
    base = sprite.copy()
    marked = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    src, dst, mk = sprite.load(), base.load(), marked.load()

    def median(ps):
        return tuple(sorted(p[i] for p in ps)[len(ps) // 2] for i in range(3))

    def dist(p, q):
        return sum(abs(p[i] - q[i]) for i in range(3))

    hits = set()
    med = {}
    for y in range(h):
        row = [src[x, y] for x in range(margin, w - margin) if src[x, y][3] > 16]
        if len(row) < 6:
            continue
        # the row's background: what it looks like at either end, where
        # there is no text
        k = max(3, min(6, len(row) // 8))
        med[y] = median(row[:k] + row[-k:])
        for x in range(margin, w - margin):
            p = src[x, y]
            if p[3] > 16 and dist(p, med[y]) > thresh:
                hits.add((x, y))
    for x, y in hits:
        mk[x, y] = src[x, y]
    # the text's own outline is close to the background colour: take the
    # pixels around each hit as well
    wiped = {(x + i, y + j) for x, y in hits
             for i in (-2, -1, 0, 1, 2) for j in (-2, -1, 0, 1, 2)}
    wiped = {(x, y) for x, y in wiped
             if margin <= x < w - margin and y in med and src[x, y][3] > 16}
    for x, y in wiped:
        # opacity: carried over from the nearest untouched pixels of the row
        # (the background may fade out sideways)
        near = []
        for step in (-1, 1):
            nx = x + step
            while 0 <= nx < w and (nx, y) in wiped:
                nx += step
            if 0 <= nx < w:
                near.append((abs(nx - x), src[nx, y][3]))
        if len(near) == 2:
            (d0, a0), (d1, a1) = near
            alpha = round((a0 * d1 + a1 * d0) / (d0 + d1))
        else:
            alpha = near[0][1] if near else src[x, y][3]
        dst[x, y] = med[y] + (alpha,)
    return base, marked


def render(name):
    """Draw the overlay PNG of table `name`: the English labels alone, on
    a transparent atlas-sized image, so it holds none of the game's art.
    Returns fit warnings."""
    img, rects = load_atlas(name)
    rows, defaults = load_table(name)
    labels = Image.new('RGBA', img.size, (0, 0, 0, 0))
    warnings = []
    drawn = {}      # rectangle -> sprite as redrawn so far (several rows may
                    # each replace one part of the same sprite)
    for sprite, en, opts, rect, part in row_parts(rects, rows, defaults):
        x, y, w, h = rect
        whole = drawn.get(rect) or img.crop((x, y, x + w, y + h))
        src = whole.crop(part)
        base, marked = background(img, rects, src, opts, rect, part)
        look = analyse(marked if marked is not None else src)
        if 'like' in opts:
            lx, ly, lw, lh = rects[int(opts['like'])]
            other = analyse(img.crop((lx, ly, lx + lw, ly + lh)))
            if other and look:
                look = {**other, **{k: look[k] for k in
                                    ('top', 'bottom', 'left', 'right', 'core')}}
            else:
                look = other or look
        if en != '~':       # `~` only removes the Japanese
            if look is None:
                warnings.append(f'{name}:{sprite} has no ink to copy the look from')
                continue
            if 'fill' in opts:
                cols = [_hex(c) for c in opts['fill'].split(',')]
                look = {**look, 'fill': (cols[0], cols[-1])}
            if 'edge' in opts:
                look = {**look, 'outline': _hex(opts['edge'])}
                if look['mode'] == 'none':
                    look.update(mode='outline', width=1)
            size = base.size
            if opts.get('font') == 'pixel':
                label, warn = draw_pixel_label(size, en, look, opts)
            else:
                label, warn = draw_label(size, en, look, opts)
            if warn:
                warnings.append(f'{name}:{sprite} {warn}')
            labels.paste(label, (x + part[0], y + part[1]))
            base.alpha_composite(label)
        whole = whole.copy()
        whole.paste(base, part[:2])
        drawn[rect] = whole
    labels.save(os.path.join(GFX_DIR, name + '.png'), optimize=True)
    return warnings


# ---- views --------------------------------------------------------------

def sprites_sheet(name, out_png, scale=2):
    img, rects = load_atlas(name)
    cells = []
    for i, (x, y, w, h) in enumerate(rects):
        if w < 2 or h < 2:
            continue
        s = img.crop((x, y, x + w, y + h))
        f = scale if max(w, h) * scale <= 500 else 1
        cells.append((i, s.resize((w * f, h * f), Image.NEAREST)))
    width, x, y, rowh, pos = 1040, 0, 0, 0, []
    for i, s in cells:
        cw = max(s.width, 30)
        if x and x + cw > width:
            x, y, rowh = 0, y + rowh + 16, 0
        pos.append((x, y))
        x += cw + 6
        rowh = max(rowh, s.height)
    canvas = Image.new('RGB', (width, y + rowh + 16), (70, 70, 100))
    dr = ImageDraw.Draw(canvas)
    for (i, s), (px, py) in zip(cells, pos):
        canvas.paste(s, (px, py + 12), s)
        dr.text((px, py), str(i), fill=(255, 255, 0))
    canvas.save(out_png)


def preview(name, out_png, scale=2):
    img, rects = load_atlas(name)
    rows, defaults = load_table(name)
    new = apply(img, rects, name)
    cells = []
    for sprite, _, _, opts in rows:
        x, y, w, h = row_rect(rects, sprite, {**defaults, **opts})
        box = (x, y, x + w, y + h)
        cells.append((sprite, img.crop(box).resize((w * scale, h * scale), Image.NEAREST),
                      new.crop(box).resize((w * scale, h * scale), Image.NEAREST)))
    width, x, y, rowh, pos = 1040, 0, 0, 0, []
    for i, a, b in cells:
        cw = a.width * 2 + 4
        if x and x + cw > width:
            x, y, rowh = 0, y + rowh + 16, 0
        pos.append((x, y))
        x += cw + 14
        rowh = max(rowh, a.height)
    canvas = Image.new('RGB', (width, y + rowh + 16), (40, 70, 110))
    dr = ImageDraw.Draw(canvas)
    for (i, a, b), (px, py) in zip(cells, pos):
        canvas.paste(a, (px, py + 12), a)
        canvas.paste(b, (px + a.width + 4, py + 12), b)
        dr.text((px, py), str(i), fill=(255, 255, 0))
    canvas.save(out_png)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]
    if cmd == 'list':
        for container in sorted(os.listdir(CPK_DIR)):
            if not os.path.isdir(os.path.join(CPK_DIR, container)):
                continue
            ents = _dir_entries(container)
            for t, e, f in ents:
                if t not in IMAGE_TAGS:
                    continue
                try:
                    hd = aif.header(open(os.path.join(CPK_DIR, container, f), 'rb').read())
                except ValueError:
                    continue
                for t2, e2, f2 in ents:
                    if t2 == ATLAS_TAGS[t] and e2 == e:
                        rects = parse_atd(open(os.path.join(CPK_DIR, container, f2), 'rb').read())
                        print(f'{container}_{int(f[:3]):03d}', t, (hd['width'], hd['height']),
                              hd['name'], len(rects), 'sprites')
    elif cmd == 'sprites':
        sprites_sheet(args[1], args[2])
    elif cmd == 'template':
        _, rects = load_atlas(args[1])
        os.makedirs(GFX_DIR, exist_ok=True)
        path = os.path.join(GFX_DIR, args[1] + '.tsv')
        if os.path.exists(path):
            sys.exit(f'{path} exists')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('sprite\tja\ten\toptions\n')
            for i, (x, y, w, h) in enumerate(rects):
                if w >= 2 and h >= 2:
                    f.write(f'{i}\t\t\t\n')
    elif cmd == 'render':
        for name in args[1:] or tables():
            for w in render(name):
                print(w)
    elif cmd == 'preview':
        preview(args[1], args[2])
    elif cmd == 'copies':
        print('\n'.join(find_copies()))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
