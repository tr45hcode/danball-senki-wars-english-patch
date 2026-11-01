#!/usr/bin/env python3
"""Patch the global fonts (RMD/RMDT pairs with 297 glyphs and no messages,
in containers 01000 and 01500).

The font has no ASCII '!', and its full-width '！' (glyph 288) is drawn as a
slanted stroke that reads as '/'. It is redrawn as a narrow '!' built from
the font's own 'l' stem and '.' dot, and its advance width is narrowed.

The 10 px font (01500) draws its ASCII glyphs centred in the 10 px cell, but
the game draws every cell from the pen position and then advances by the
glyph's proportional width. Narrow letters land 3-4 px right of their slot,
on top of the next letter ("Inui" reads "hui"); the Japanese text never used
half-width letters at 10 px, so it never showed. Those glyphs are moved left
to sit inside their advance, like the 14 and 11 px fonts already do.
Only pixels and one width byte change, so every file keeps its size.
"""
import mron
from ctrtex import decode_l8, encode_l8
from rmd import GLOBAL_CHARS, Rmd

EXCLAIM = GLOBAL_CHARS.index('！')
EXCLAIM_ADVANCE = {14: 4, 11: 4, 10: 3}
PROPORTIONAL = 78        # glyphs 0-77 (ASCII, ±) have their own advance widths
CENTRED_CELLS = (10,)    # fonts whose proportional glyphs are drawn centred
TEX_HEADER = 0x1E0


def _ink(img, rect):
    """{(x, y): value} of the ink pixels in a cell (relative coordinates)."""
    x0, y0, x1, y1 = rect
    px = img.load()
    bg = px[x0, y0]
    return {(x - x0, y - y0): px[x, y]
            for y in range(y0, y1) for x in range(x0, x1) if px[x, y] != bg}, bg


def redraw_exclaim(rmd, img):
    stem, _ = _ink(img, rmd.glyph_rect(GLOBAL_CHARS.index('l'))[0])
    dot, _ = _ink(img, rmd.glyph_rect(GLOBAL_CHARS.index('.'))[0])
    rect = rmd.glyph_rect(EXCLAIM)[0]
    x0, y0, x1, y1 = rect
    _, bg = _ink(img, rect)
    px = img.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = bg
    stem_x = min(x for x, _ in stem)
    dot_top = min(y for _, y in dot)
    dot_x0 = min(x for x, _ in dot)
    for (x, y), v in stem.items():
        if y <= dot_top - 3:
            px[x0 + x, y0 + y] = v
    for (x, y), v in dot.items():
        px[x0 + stem_x + (x - dot_x0), y0 + y] = v


def left_align(rmd, img):
    """Move each proportional glyph left so its ink is centred in its advance
    width (rounding right) instead of in the cell. Never moves a glyph right.
    The extent is measured on clearly inked pixels: some cells carry a faint
    stray pixel (241 on a 240 background) that would otherwise pin them."""
    px = img.load()
    for i in range(PROPORTIONAL):
        rect, adv = rmd.glyph_rect(i)
        ink, bg = _ink(img, rect)
        solid = [x for (x, _), v in ink.items() if abs(v - bg) >= 8]
        if not solid:
            continue
        left, right = min(solid), max(solid)
        shift = left - max(0, (adv - (right - left + 1) + 1) // 2)
        if shift <= 0:
            continue
        x0, y0, x1, y1 = rect
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[x, y] = bg
        for (x, y), v in ink.items():
            if x >= shift:
                px[x0 + x - shift, y0 + y] = v


def _global_fonts(data):
    """Yield (rmd index, Rmd, rmdt index) for each global font in a container."""
    entries = mron.parse(data)
    for i, ent in enumerate(entries):
        if ent['tag'] != 'RMD-':
            continue
        rmd = Rmd(mron.read_entry(data, ent))
        if rmd.msg_count or rmd.glyph_count != 297 or rmd.cell not in EXCLAIM_ADVANCE:
            continue
        tex_i = next(j for j in (i - 1, i + 1)
                     if 0 <= j < len(entries) and entries[j]['tag'] == 'RMDT'
                     and entries[j]['id'] == ent['id'])
        yield i, rmd, tex_i


def patch_container(data):
    """Return {entry index: new payload} for the global fonts in a container."""
    entries = mron.parse(data)
    out = {}
    for i, rmd, tex_i in _global_fonts(data):
        rmd_bytes = rmd.data
        tex = mron.read_entry(data, entries[tex_i])
        img = decode_l8(tex[TEX_HEADER:], rmd.atlas_w, rmd.atlas_h)
        if rmd.cell in CENTRED_CELLS:
            left_align(rmd, img)        # before the '!' copies the 'l' stem
        redraw_exclaim(rmd, img)
        out[tex_i] = tex[:TEX_HEADER] + encode_l8(img)
        new_rmd = bytearray(rmd_bytes)
        new_rmd[rmd.glyph_table + EXCLAIM * 0x14] = EXCLAIM_ADVANCE[rmd.cell]
        out[i] = bytes(new_rmd)
    return out


def glyph_preview(data, path):
    """Save an enlarged preview of '!' next to 'l' and '.' for each font."""
    from PIL import Image
    entries = mron.parse(data)
    tiles = []
    for _, rmd, tex_i in _global_fonts(data):
        img = decode_l8(mron.read_entry(data, entries[tex_i])[TEX_HEADER:], rmd.atlas_w, rmd.atlas_h)
        for ch in 'l.！':
            tiles.append(img.crop(rmd.glyph_rect(GLOBAL_CHARS.index(ch))[0]).resize((rmd.cell * 6, rmd.cell * 6), Image.NEAREST))
    sheet = Image.new('L', (sum(t.width + 6 for t in tiles), max(t.height for t in tiles)), 60)
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + 6
    sheet.save(path)
