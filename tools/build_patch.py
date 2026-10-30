#!/usr/bin/env python3
"""Build a LayeredFS mod with translated game text.

Usage: build_patch.py [--test-ids] [--ruler] <DA3File_3ds.cpk> <out_dir>

Translations are read from script/en/<container>_<index>_<entry>.tsv
(columns id, ja, en; see make_template.py). Messages without English keep
the original Japanese unless a test option is given:

--test-ids  untranslated messages show their location, e.g. "11812:10"
            (or "01000.98:5" when a container holds several RMD files)
--ruler     with --test-ids: dialogue-like messages (outside the boot-time
            system banks 01000/01500) also get a pixel ruler line and a
            second page, to measure the text box in-game

Output: <out_dir>/00040000000F4000/romfs/DA3File_3ds.cpk
        <out_dir>/text_report.txt  (wrapping/overflow warnings)
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpatch  # noqa: E402
import mron  # noqa: E402
import textfit  # noqa: E402
from cpk import Cpk  # noqa: E402
from rmd import LOCAL_BASE, Rmd, encode_tokens, parse_markup  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_TEXT = '01000_098_000203e8'
SYSTEM_TEXT_10PX = '01000_100_000303e8'
TITLE_ID = '00040000000F4000'
RULER = '1234567890' * 3 + '1234567'   # 11 px per digit at 14 px: visible digits x 11 = px


def load_translations():
    """{file name: {message id: english markup}}"""
    out = {}
    for path in glob.glob(os.path.join(ROOT, 'script', 'en', '*.tsv')):
        name = os.path.basename(path)[:-4]
        rows = {}
        with open(path, encoding='utf-8') as f:
            for n, line in enumerate(f):
                cols = line.rstrip('\n').split('\t')
                if n == 0 and cols[0] == 'id':
                    continue
                if len(cols) >= 3 and cols[-1].strip():
                    rows[int(cols[0])] = cols[-1].strip()
        if rows:
            out[name] = rows
    # 01000_100 is the 10 px copy of the system text, message for message
    if SYSTEM_TEXT in out:
        mirror = out.setdefault(SYSTEM_TEXT_10PX, {})
        for mid, en in out[SYSTEM_TEXT].items():
            mirror.setdefault(mid, en)
    return out


def original_layout(rmd, off, global_widths):
    """(max line width in px, max lines on a page, trailing [p] count)."""
    pages, trailing = [[0]], 0
    n_local = rmd.glyph_count - 297
    for tok in rmd.tokens(off):
        if tok[0] == 'g':
            v = tok[1]
            if v < LOCAL_BASE:
                pages[-1][-1] += global_widths(v)
            elif v - LOCAL_BASE < n_local:
                pages[-1][-1] += rmd.glyph_rect(v - LOCAL_BASE)[1]
            else:   # broken reference (debug file 60016)
                pages[-1][-1] += rmd.cell
            trailing = 0
        elif tok[1] == 0x00:
            pages[-1].append(0)
        elif tok[1] == 0x06:
            pages.append([0])
            trailing += 1
        elif tok[1] == 0x13:
            pages[-1][-1] += textfit.VAR_WIDTH
    pages = [p for p in pages if any(p)] or [[0]]
    return max(max(p) for p in pages), max(len(p) for p in pages), trailing


def message_text(name, label, mid, rmd, off, translations, opts, report):
    cell = rmd.cell if rmd.cell in textfit._PROPORTIONAL else 14

    def gw(v):
        return textfit.char_width(textfit.GLOBAL_CHARS[v - 1], cell) if 1 <= v <= 297 else cell

    width, lines, trailing = original_layout(rmd, off, gw)
    dialogue = lines >= 2 or width >= 200
    en = translations.get(name, {}).get(mid)
    if en is None:
        if '--test-ids' not in opts:
            return None
        if dialogue and '--ruler' in opts and not name.startswith(('01000_', '01500_')):
            en = (f'{label} ruler:[n]{RULER}[p]'
                  f'Page 2 of {label}: the quick brown fox jumps over the lazy dog!')
        else:
            en = label
    en, bad = textfit.normalize(en.rstrip())
    if bad:
        report.append(f'{name}:{mid}: unsupported characters {"".join(sorted(bad))} (dropped)')
        en = ''.join(c for c in en if c not in bad)
    while en.endswith('[p]'):
        en = en[:-3]
    en, warnings = textfit.wrap(en, *textfit.limits(name, width, lines), cell)
    for w in warnings:
        report.append(f'{name}:{mid}: {w}')
    if not dialogue and textfit.measure(en.split('[n]')[0], cell) > max(width, 1) * 1.5 and width:
        report.append(f'{name}:{mid}: UI text {textfit.measure(en, cell)}px vs Japanese {width}px: {en!r}')
    return encode_tokens(parse_markup(en + '[p]' * trailing))


def main():
    opts = {a for a in sys.argv[1:] if a.startswith('--')}
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    cpk_path, out = args
    translations = load_translations()
    print(f'{sum(len(v) for v in translations.values())} translated messages in {len(translations)} files')
    build(cpk_path, out, translations, opts)


def build(cpk_path, out, translations, opts):
    cpk = Cpk(cpk_path)
    replacements, report = {}, []
    for e in cpk.files:
        data = cpk.read(e)
        if data[:8] != mron.MAGIC:
            continue
        entries = mron.parse(data)
        rmd_idx = [i for i, ent in enumerate(entries) if ent['tag'] == 'RMD-']
        payloads = {}
        for i in rmd_idx:
            rmd = Rmd(mron.read_entry(data, entries[i]))
            if not rmd.msg_count:
                continue
            name = f"{e['name']}_{i:03d}_{entries[i]['id']:08x}"
            label = f"{e['name']}.{i}" if len(rmd_idx) > 1 else e['name']
            texts = {}
            for mid, off, _, _ in rmd.messages():
                msg = message_text(name, f'{label}:{mid}', mid, rmd, off, translations, opts, report)
                if msg is not None:
                    texts[mid] = msg
            if texts:
                payloads[i] = rmd.with_texts(texts)
        if e['name'] in ('01000', '01500'):
            payloads.update(fontpatch.patch_container(data))
        if payloads:
            replacements[e['id']] = mron.replace_entries(data, payloads)
    print(f'{len(replacements)} containers rebuilt')

    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'text_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    print(f'{len(report)} warnings -> {os.path.join(out, "text_report.txt")}')

    dst_dir = os.path.join(out, TITLE_ID, 'romfs')
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(cpk_path))
    cpk.write_itoc(dst, replacements)
    print(f'wrote {dst}')


if __name__ == '__main__':
    main()
