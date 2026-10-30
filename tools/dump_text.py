#!/usr/bin/env python3
"""Dump every RMD message to text.

Usage: dump_text.py <extracted/cpk> <out_dir>

Per-file glyphs (kanji etc.) are named from data/glyph_ids.tsv (made by
identify_kanji.py); script/glyph_overrides.tsv (key<TAB>char, hand-checked)
takes precedence.

Writes:
  out_dir/glyphs.tsv          one row per unique per-file glyph bitmap:
                              key, cell, char, status, uses
  out_dir/<container>_<index>_<entry>.tsv
                              one row per message: id, text

Markup in text:
  {漢字|かんじ}   furigana       [n] newline      [p] page break
  [var:N]        variable       [cNN] [x..] other controls
  Glyphs identified from images alone (status 'visual') are wrapped as
  ⟨char⟩; ⟨?⟩ marks a glyph missing from the identification table.
"""
import glob
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ctrtex import decode_l8  # noqa: E402
from rmd import CONTROLS, GLOBAL_CHARS, LOCAL_BASE, Rmd, ruby_reading  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDS = os.path.join(ROOT, 'data', 'glyph_ids.tsv')
OVERRIDES = os.path.join(ROOT, 'script', 'glyph_overrides.tsv')


def load_glyph_names():
    """{key: (char, status)} from the identification table plus overrides."""
    names = {}
    if os.path.exists(IDS):
        with open(IDS, encoding='utf-8') as f:
            next(f)
            for line in f:
                c = line.rstrip('\n').split('\t')
                names[c[0]] = (c[2], c[3])
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding='utf-8') as f:
            for line in f:
                c = line.rstrip('\n').split('\t')
                if len(c) >= 2 and not line.startswith('#'):
                    names[c[0]] = (c[1], 'manual')
    return names


def rmd_pairs(root):
    """Yield (rmd_path, rmdt_path); an RMD's atlas is the adjacent RMDT entry
    with the same id (usually just before it, sometimes just after)."""
    for p in sorted(glob.glob(os.path.join(root, '*', '*_RMD__*.bin'))):
        d, b = os.path.split(p)
        for delta in (-1, 1):
            t = os.path.join(d, '%03d_RMDT_%s' % (int(b[:3]) + delta, b[9:]))
            if os.path.exists(t):
                yield p, t
                break
        else:
            print('no atlas for', p, file=sys.stderr)


def glyph_key(cell, bitmap):
    return '%02d_%s' % (cell, hashlib.md5(bitmap.tobytes()).hexdigest()[:10])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    root, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)

    # pass 1: collect unique glyph bitmaps
    files = []
    glyphs = {}   # key -> [cell, bitmap, uses]
    for p, t in rmd_pairs(root):
        r = Rmd(open(p, 'rb').read())
        atlas = decode_l8(open(t, 'rb').read()[0x1E0:], r.atlas_w, r.atlas_h)
        keys = []
        for k in range(r.glyph_count - 297):
            rect, w = r.glyph_rect(k)
            if not w:
                keys.append(None)
                continue
            bm = atlas.crop(rect)
            key = glyph_key(r.cell, bm)
            glyphs.setdefault(key, [r.cell, bm, 0])[2] += 1
            keys.append(key)
        files.append((p, r, keys))

    # pass 2: name the glyphs
    names = load_glyph_names()
    with open(os.path.join(out, 'glyphs.tsv'), 'w', encoding='utf-8') as f:
        f.write('key\tcell\tchar\tstatus\tuses\n')
        for k in sorted(glyphs, key=lambda k: -glyphs[k][2]):
            ch, status = names.get(k, ('?', 'missing'))
            f.write(f'{k}\t{glyphs[k][0]}\t{ch}\t{status}\t{glyphs[k][2]}\n')

    def local_char(key):
        ch, status = names.get(key, ('?', 'missing'))
        return f'⟨{ch}⟩' if status in ('visual', 'missing') else ch

    # pass 3: dump messages
    for p, r, keys in files:
        container = os.path.basename(os.path.dirname(p))
        name = f'{container}_{os.path.basename(p)[:3]}_{os.path.basename(p)[9:17]}.tsv'
        with open(os.path.join(out, name), 'w', encoding='utf-8') as f:
            for mid, off, _, _ in r.messages():
                parts = []
                for tok in r.tokens(off):
                    if tok[0] == 'g':
                        v = tok[1]
                        if 1 <= v <= len(GLOBAL_CHARS):
                            parts.append(GLOBAL_CHARS[v - 1])
                        elif LOCAL_BASE <= v < LOCAL_BASE + len(keys) and keys[v - LOCAL_BASE]:
                            parts.append(local_char(keys[v - LOCAL_BASE]))
                        else:
                            parts.append(f'[?{v}]')
                        continue
                    _, cid, params = tok
                    if cid == 0x10:
                        parts.append('{')
                        ruby = ruby_reading(params)
                    elif cid == 0x11:
                        parts.append(f'|{ruby}}}')
                    elif cid == 0x00:
                        parts.append('[n]')
                    elif cid == 0x06:
                        parts.append('[p]')
                    elif cid == 0x13:
                        parts.append(f'[var:{params[0]}]')
                    else:
                        parts.append(f'[{CONTROLS[cid][0]}{":" + params.hex() if params else ""}]')
                f.write(f'{mid}\t{"".join(parts)}\n')
    print(f'{len(files)} files dumped', file=sys.stderr)


if __name__ == '__main__':
    main()
