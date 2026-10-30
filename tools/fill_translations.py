#!/usr/bin/env python3
"""Merge a batch of translations into script/en/*.tsv and check that they fit.

Usage: fill_translations.py <batch.tsv>

Batch lines: <file name><TAB><message id><TAB><english>   ('#' lines ignored)
  file name as in script/raw, e.g. 52500_002_0000cd14
Templates are created as needed (make_template.py); existing English is
overwritten. Afterwards every line in the batch is wrapped like the build
does and any overflow is reported.
"""
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    batch = defaultdict(dict)
    with open(sys.argv[1], encoding='utf-8') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            name, mid, en = line.rstrip('\n').split('\t', 2)
            batch[name][int(mid)] = en
    for name, rows in batch.items():
        path = os.path.join(ROOT, 'script', 'en', name + '.tsv')
        if not os.path.exists(path):
            subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_template.py'), name],
                           check=True, stdout=subprocess.DEVNULL)
        with open(path, encoding='utf-8') as f:
            lines = f.read().split('\n')
        seen = set()
        for i, line in enumerate(lines):
            cols = line.split('\t')
            if len(cols) == 3 and cols[0].isdigit() and int(cols[0]) in rows:
                cols[2] = rows[int(cols[0])]
                lines[i] = '\t'.join(cols)
                seen.add(int(cols[0]))
        missing = set(rows) - seen
        if missing:
            print(f'{name}: no such message ids {sorted(missing)}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    problems = 0
    for name, rows in batch.items():
        for mid, en in rows.items():
            text, bad = textfit.normalize(en)
            _, warnings = textfit.wrap(text, *textfit.box(name))
            for w in warnings + ([f'unsupported characters {"".join(sorted(bad))}'] if bad else []):
                print(f'{name}:{mid}: {w}')
                problems += 1
    print(f'{sum(len(r) for r in batch.values())} lines merged into {len(batch)} files, {problems} problems')


if __name__ == '__main__':
    main()
