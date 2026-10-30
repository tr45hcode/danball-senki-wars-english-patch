#!/usr/bin/env python3
"""Identify bitmap glyphs by matching against a reference font (Noto Sans CJK JP).

Glyphs are compared inside their fixed cell (no stretching), upsampled and
blurred, allowing small shifts. Candidates are the JIS X 0208 repertoire,
with a small prior favouring JIS level 1 kanji.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = '/usr/share/fonts/noto-cjk/NotoSansCJK-{}.ttc'
UP = 3          # upsampling factor before comparison
SHIFT = 1       # max shift in source pixels


def jis_repertoire():
    """All JIS X 0208 characters, and the subset that is level 1 kanji."""
    chars, level1 = [], set()
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xEB)):
        for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try:
                ch = bytes([lead, trail]).decode('shift_jis')
            except UnicodeDecodeError:
                continue
            chars.append(ch)
            if 0x889F <= (lead << 8 | trail) <= 0x9872:
                level1.add(ch)
    return chars, level1


def _prep(img, cell):
    img = img.convert('L').resize((cell * UP, cell * UP), Image.BILINEAR)
    return np.asarray(img.filter(ImageFilter.GaussianBlur(UP * 0.6)), np.float32)


def _unit(a):
    a = a - a.mean()
    n = np.linalg.norm(a)
    return a / n if n else a


def render(ch, cell, font):
    img = Image.new('L', (cell, cell))
    ImageDraw.Draw(img).text((cell / 2, cell / 2), ch, font=font, fill=255, anchor='mm')
    return img


def build_reference(cell, weight='Bold'):
    chars, level1 = jis_repertoire()
    font = ImageFont.truetype(FONT.format(weight), cell, index=0)
    keep, vecs = [], []
    for ch in chars:
        if not ch.strip() or font.getmask(ch).getbbox() is None:
            continue
        keep.append(ch)
        vecs.append(_unit(_prep(render(ch, cell, font), cell)).ravel())
    prior = np.array([0.02 if c in level1 else 0.0 for c in keep], np.float32)
    return keep, np.stack(vecs), prior


def match(bitmaps, cell, ref, top=3):
    chars, mat, prior = ref
    out = []
    size = cell * UP
    for bm in bitmaps:
        a = _prep(bm, cell)
        best = None
        for dy in range(-SHIFT * UP, SHIFT * UP + 1, UP):
            for dx in range(-SHIFT * UP, SHIFT * UP + 1, UP):
                v = _unit(np.roll(np.roll(a, dy, 0), dx, 1)).ravel()
                s = mat @ v
                best = s if best is None else np.maximum(best, s)
        best = best + prior
        idx = np.argsort(-best)[:top]
        out.append(([chars[i] for i in idx], [float(best[i]) for i in idx]))
    return out
