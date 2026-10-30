#!/usr/bin/env python3
"""Render the unverified per-file glyphs of some containers to one PNG.

Usage: .venv/bin/python tools/glyphsheet.py <out.png> <container>...
       e.g. glyphsheet.py /tmp/g.png 52522 52525

Draws every glyph the dump shows as ⟨字⟩ (identified from the image alone,
or not at all), enlarged, numbered in the order of the printed list
(index, key, guessed char, container). Look at the sheet, then put the right
character in script/glyph_overrides.tsv (key<TAB>char) and re-run
dump_text.py. Full-width digits are the usual suspects: the guesses mix up
3/8/日 and 0/Ｑ.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

from ctrtex import decode_l8  # noqa: E402
from dump_text import glyph_key, load_glyph_names, rmd_pairs  # noqa: E402
from rmd import Rmd  # noqa: E402

SCALE, CELL, PER_ROW = 6, 110, 10


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, containers = sys.argv[1], set(sys.argv[2:])
    names = load_glyph_names()
    found = {}
    for p, t in rmd_pairs(os.path.join(ROOT, 'extracted', 'cpk')):
        container = os.path.basename(os.path.dirname(p))
        if container not in containers:
            continue
        r = Rmd(open(p, 'rb').read())
        atlas = decode_l8(open(t, 'rb').read()[0x1E0:], r.atlas_w, r.atlas_h)
        for k in range(r.glyph_count - 297):
            rect, w = r.glyph_rect(k)
            if not w:
                continue
            bm = atlas.crop(rect)
            key = glyph_key(r.cell, bm)
            ch, status = names.get(key, ('?', 'missing'))
            if status in ('visual', 'missing') and key not in found:
                found[key] = (bm, ch, container)
    if not found:
        print('no unverified glyphs')
        return
    rows = (len(found) + PER_ROW - 1) // PER_ROW
    sheet = Image.new('L', (min(len(found), PER_ROW) * CELL + 10, rows * 140 + 10), 255)
    draw = ImageDraw.Draw(sheet)
    for i, (key, (bm, ch, container)) in enumerate(found.items()):
        x, y = 10 + i % PER_ROW * CELL, 10 + i // PER_ROW * 140
        sheet.paste(bm.resize((bm.width * SCALE, bm.height * SCALE), Image.NEAREST), (x, y))
        draw.text((x, y + 100), f'{i}:{container}', fill=0)
        print(i, key, ch, container)
    sheet.save(out)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
