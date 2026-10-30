#!/usr/bin/env python3
"""Flag translated data strings that are bigger than any original in their category.

Usage: sizecheck.py        (prints file, id, English bytes, Japanese max bytes, text)

Names and labels may be copied into fixed-size buffers, so an English string
encoded larger than the longest Japanese string of its category could overflow
one. Keep this list empty. Story dialogue is not checked.
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, 'tools')
import textfit, mron
from rmd import Rmd, encode_tokens, parse_markup
from cpk import Cpk
cpk = Cpk('extracted/romfs/DA3File_3ds.cpk')
ent = {e['name']: e for e in cpk.files}
def en_of(f):
    out = {}
    for l in open(f'script/en/{f}.tsv', encoding='utf-8'):
        c = l.rstrip('\n').split('\t')
        if len(c) == 3 and c[0].isdigit() and c[2]: out[int(c[0])] = c[2]
    return out
def enc_len(en):
    return len(encode_tokens(parse_markup(textfit.normalize(en)[0]))) + 1
FILES = {'01000_098_000203e8': [(0, 999), (1000, 4999), (5000, 6999), (7000, 8999), (14000, 14099), (14100, 14199), (24000, 24999), (32000, 32999), (48000, 48999), (51000, 56999)],
         '13011_001_000332d3': [(0, 99999)], '13011_003_000132d3': [(0, 99999)], '13011_005_000232d3': [(0, 99999)],
         '13017_001_100032d9': [(0, 99999)], '13260_001_100033cc': [(0, 999), (10000, 19999)], '13260_003_100133cc': [(0, 99999)]}
for f, cats in FILES.items():
    cont, idx, _ = f.split('_')
    d = cpk.read(ent[cont]); r = Rmd(mron.read_entry(d, mron.parse(d)[int(idx)]))
    ja = {mid: len(encode_tokens(list(r.tokens(off)))) + 1 for mid, off, *_ in r.messages()}
    en = en_of(f)
    for a, b in cats:
        ids = [i for i in ja if a <= i <= b]
        jm = max(ja[i] for i in ids)
        for i in ids:
            if i in en and enc_len(en[i]) > jm:
                print(f'{f}\t{i}\t{enc_len(en[i])}\t{jm}\t{en[i]}')
