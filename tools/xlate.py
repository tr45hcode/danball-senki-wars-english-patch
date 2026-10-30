#!/usr/bin/env python3
"""Helpers for translating in batches (run from anywhere).

Usage:
  xlate.py show <prefix>...            untranslated lines of matching script/raw files
  xlate.py reuse <out.tsv> <prefix>... batch of speaker tags and exact repeats
  xlate.py batch <out.tsv>   < lines   shorthand lines -> fill_translations.py batch
  xlate.py check             < lines   wrap shorthand lines like the build does

A prefix is the start of a script/raw file name: 52517, 525, 5390...

show: collapses furigana to the kanji ({漢字|かんじ} -> 漢字), or to the
reading when the kanji is an image-only guess (⟨字⟩). Speaker name tags (story
scenes' 004 files) and debug lines are left out.

reuse: speaker tags (004 files) come from script/speaker_names.tsv, keyed
by reading (see that file); unknown tags are listed so they can be added.
Dialogue lines whose Japanese exactly matches an already translated line
are copied. Short replies can depend on who is spoken to ("Yes, sir."), so
the copied dialogue is printed for review before merging.

Shorthand lines, one per message ('#' lines ignored):
  52517:7 English text          file 52517_002_*  (the dialogue RMD)
  52517.4:1 Arata               file 52517_004_*  (another RMD index)

check: prints OK/BAD and the width of each wrapped line, using the same
limits as the build (box size from textfit.BOXES, or more if the Japanese
was wider or had more lines).
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfit  # noqa: E402

RAW = os.path.join(ROOT, 'script', 'raw')
EN = os.path.join(ROOT, 'script', 'en')
NAMES = os.path.join(ROOT, 'script', 'speaker_names.tsv')
DEBUG = ('ゔケノゔ絵',)


def rows(path):
    """{id: [columns after id]} of a raw or en tsv."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f):
            c = line.rstrip('\n').split('\t')
            if n == 0 and c[0] == 'id':
                continue
            if len(c) >= 2 and c[0].isdigit():
                out[int(c[0])] = c[1:]
    return out


def english(name):
    return {k: v[1] for k, v in rows(os.path.join(EN, name + '.tsv')).items()
            if len(v) > 1 and v[1].strip()}


def is_tags(name):
    """Speaker name tags: RMD index 004 of a story scene (52xxx/53xxx)."""
    return name.split('_')[1] == '004' and name.startswith(('52', '53'))


def raw_files(prefixes):
    for p in prefixes:
        yield from sorted(glob.glob(os.path.join(RAW, f'{p}*_*_*.tsv')))


def reading(text):
    """Tag text keyed by its reading, so misread kanji still match."""
    text = re.sub(r'\{([^|}]*)\|([^}]*)\}', r'\2', text)
    return text.replace('[p]', '').replace('⟨', '').replace('⟩', '').strip()


def compact(text):
    text = re.sub(r'\{([^|}]*)\|([^}]*)\}',
                  lambda m: m.group(2) if '⟨' in m.group(1) else m.group(1), text)
    return text.replace('[p]', '')


def resolve(ref):
    """'52517:7' / '52517.4:1' -> (file name, message id)."""
    cont, mid = ref.split(':')
    idx = 2
    if '.' in cont:
        cont, idx = cont.split('.')
    found = glob.glob(os.path.join(RAW, f'{cont}_{int(idx):03d}_*.tsv'))
    if len(found) != 1:
        sys.exit(f'{ref}: no single script/raw file for it')
    return os.path.basename(found[0])[:-4], int(mid)


def shorthand(stream):
    for line in stream.read().split('\n'):
        if line.strip() and not line.startswith('#'):
            ref, en = line.split(' ', 1)
            yield ref, en.strip()


def limits(name, mid):
    """(px per line, lines, cell) the build will wrap this message to."""
    box_width, box_lines = textfit.box(name)
    cont, idx, eid = name.split('_')
    path = os.path.join(ROOT, 'extracted', 'cpk', cont, f'{idx}_RMD__{eid}.bin')
    if not os.path.exists(path):
        return box_width, box_lines, 14
    from build_patch import original_layout
    from rmd import Rmd
    rmd = Rmd(open(path, 'rb').read())
    cell = rmd.cell if rmd.cell in textfit._PROPORTIONAL else 14
    offsets = {m[0]: m[1] for m in rmd.messages()}
    if mid not in offsets:
        return box_width, box_lines, cell

    def gw(v):
        return textfit.char_width(textfit.GLOBAL_CHARS[v - 1], cell) if 1 <= v <= 297 else cell
    width, lines, _ = original_layout(rmd, offsets[mid], gw)
    return (*textfit.limits(name, width, lines), cell)


def show(prefixes):
    for path in raw_files(prefixes):
        name = os.path.basename(path)[:-4]
        if is_tags(name):
            continue
        done = english(name)
        for mid, cols in rows(path).items():
            if mid not in done and not any(d in cols[0] for d in DEBUG):
                print(f'{name[:5]}:{mid}\t{compact(cols[0])}')


def reuse(out, prefixes):
    names = {}
    if os.path.exists(NAMES):
        with open(NAMES, encoding='utf-8') as f:
            for line in f:
                if '\t' in line and not line.startswith('#'):
                    key, en = line.rstrip('\n').split('\t')
                    names[key] = en
    memory = {}
    for path in glob.glob(os.path.join(EN, '*.tsv')):
        name = os.path.basename(path)[:-4]
        if is_tags(name):
            continue
        raw = rows(os.path.join(RAW, name + '.tsv'))
        for mid, en in english(name).items():
            if mid in raw:
                memory.setdefault(raw[mid][0], en)
    batch, unknown = [], {}
    for path in raw_files(prefixes):
        name = os.path.basename(path)[:-4]
        done = english(name)
        tags = is_tags(name)
        for mid, cols in rows(path).items():
            if mid in done:
                continue
            if tags:
                key = reading(cols[0])
                if key in names:
                    batch.append((name, mid, names[key]))
                else:
                    unknown.setdefault(key, []).append(f'{name[:5]}.4:{mid}')
            elif cols[0] in memory:
                batch.append((name, mid, memory[cols[0]]))
                print(f'repeat  {name[:5]}:{mid}\t{memory[cols[0]]}')
    with open(out, 'w', encoding='utf-8') as f:
        for row in batch:
            f.write('%s\t%d\t%s\n' % row)
    for key, where in unknown.items():
        print(f'unknown tag  {key}\t{" ".join(where[:4])}')
    print(f'{len(batch)} lines -> {out}')


def batch(out):
    lines = [(*resolve(ref), en) for ref, en in shorthand(sys.stdin)]
    with open(out, 'w', encoding='utf-8') as f:
        for row in lines:
            f.write('%s\t%d\t%s\n' % row)
    print(f'{len(lines)} lines -> {out}')


def check():
    for ref, en in shorthand(sys.stdin):
        name, mid = resolve(ref)
        width, lines, cell = limits(name, mid)
        text, bad = textfit.normalize(en)
        wrapped, warnings = textfit.wrap(text, width, lines, cell)
        widths = ' | '.join(str(textfit.measure(s, cell)) for s in wrapped.split('[n]'))
        flag = 'BAD' if warnings or bad else 'OK '
        extra = f'  (unsupported: {"".join(sorted(bad))})' if bad else ''
        print(f'{flag} {widths}  [{width}px x{lines}]  {ref} {en}{extra}')


def main():
    args = sys.argv[1:]
    if args[:1] == ['show'] and len(args) > 1:
        show(args[1:])
    elif args[:1] == ['reuse'] and len(args) > 2:
        reuse(args[1], args[2:])
    elif args[:1] == ['batch'] and len(args) == 2:
        batch(args[1])
    elif args == ['check']:
        check()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
