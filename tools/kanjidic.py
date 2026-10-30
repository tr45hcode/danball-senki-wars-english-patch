#!/usr/bin/env python3
"""Kanji readings from KANJIDIC2 (EDRDG, CC BY-SA 4.0).

Download: https://www.edrdg.org/kanjidic/kanjidic2.xml.gz -> data/kanjidic/
load() returns {kanji: (readings, name_readings, frequency rank or None)}.
readings: on'yomi (converted to hiragana), kun'yomi stems and full forms
(okurigana marker removed). name_readings: nanori not already in readings.
"""
import gzip
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'kanjidic', 'kanjidic2.xml.gz')


def kata_to_hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def load(path=PATH):
    out = {}
    with gzip.open(path, 'rb') as f:
        for _, el in ET.iterparse(f):
            if el.tag != 'character':
                continue
            lit = el.findtext('literal')
            readings, names = set(), set()
            for r in el.iter('reading'):
                kind, text = r.get('r_type'), (r.text or '').replace('-', '')
                if kind == 'ja_on':
                    readings.add(kata_to_hira(text))
                elif kind == 'ja_kun':
                    stem, _, okuri = text.partition('.')
                    readings.add(stem)
                    if okuri:
                        readings.add(stem + okuri)
            for n in el.iter('nanori'):
                names.add(n.text or '')
            freq = el.findtext('misc/freq')
            readings.discard('')
            names.discard('')
            out[lit] = (readings, names - readings, int(freq) if freq else None)
            el.clear()
    return out
