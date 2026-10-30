#!/usr/bin/env python3
"""Word list from JMdict (EDRDG, CC BY-SA 4.0).

Download: http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz -> data/jmdict/
load() returns {hiragana reading: set of written forms containing kanji}.
The parsed index is cached next to the download.
"""
import gzip
import os
import pickle
import xml.etree.ElementTree as ET
from collections import defaultdict

from kanjidic import kata_to_hira

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'jmdict', 'JMdict_e.gz')
CACHE = os.path.join(ROOT, 'data', 'jmdict', 'words.pkl')


def _parse(path):
    words = defaultdict(set)
    with gzip.open(path, 'rb') as f:
        for _, el in ET.iterparse(f):
            if el.tag != 'entry':
                continue
            kebs = [k.text for k in el.iter('keb')]
            if kebs:
                for r in el.iter('r_ele'):
                    if r.find('re_nokanji') is not None:
                        continue
                    restr = [x.text for x in r.iter('re_restr')] or kebs
                    reb = kata_to_hira(r.findtext('reb'))
                    words[reb].update(restr)
            el.clear()
    return dict(words)


def load():
    if os.path.exists(CACHE) and os.path.getmtime(CACHE) > os.path.getmtime(PATH):
        with open(CACHE, 'rb') as f:
            return pickle.load(f)
    words = _parse(PATH)
    with open(CACHE, 'wb') as f:
        pickle.dump(words, f)
    return words
