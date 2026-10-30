#!/usr/bin/env python3
"""Score a glyph identification table against hand-read ground truth.

Usage: eval_kanji.py <glyph_ids.tsv>
Ground truth: the atlas of 11812/001_RMDT in glyph order, read by eye and
checked against the furigana of the messages that use each glyph.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ctrtex import decode_l8  # noqa: E402
from dump_text import glyph_key  # noqa: E402
from rmd import Rmd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = ('11812', '002_RMD__00002e24', '001_RMDT_00002e24',
         '君俺山野友人事聞優秀今度神威大門統合学園専校父予測可能性広何言少照生研究'
         '者目指高卒業国工科進定未来見届役思用使残念息失礼先輩負開始島自然眠払金足'
         '仲間一現在熟練本当')


def main():
    table = {}
    with open(sys.argv[1], encoding='utf-8') as f:
        next(f)
        for line in f:
            c = line.rstrip('\n').split('\t')
            table[c[0]] = (c[2], c[3])
    cont, rmd_name, tex_name, truth = TRUTH
    base = os.path.join(ROOT, 'extracted', 'cpk', cont)
    r = Rmd(open(os.path.join(base, rmd_name + '.bin'), 'rb').read())
    atlas = decode_l8(open(os.path.join(base, tex_name + '.bin'), 'rb').read()[0x1E0:], r.atlas_w, r.atlas_h)
    ok, wrong = 0, []
    for k, want in enumerate(truth):
        got, status = table[glyph_key(r.cell, atlas.crop(r.glyph_rect(k)[0]))]
        if got == want:
            ok += 1
        else:
            wrong.append(f'{want}->{got}({status})')
    print(f'{ok}/{len(truth)} correct; wrong: {" ".join(wrong)}')


if __name__ == '__main__':
    main()
