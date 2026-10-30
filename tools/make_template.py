#!/usr/bin/env python3
"""Create translation templates from the raw dump.

Usage: make_template.py <name> [<name> ...]
       (name = a script/raw file name without .tsv, e.g. 01000_098_000203e8)

Writes script/en/<name>.tsv with columns: id, ja (reference), en (to fill).
Existing files are never overwritten.

Translation markup:
  [n] new line (optional: long lines are wrapped automatically)
  [var:0] player name (keep it where the Japanese has it)
  The final page break [p] is added automatically; leave it out.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_dir = os.path.join(ROOT, 'script', 'en')
    os.makedirs(out_dir, exist_ok=True)
    for name in sys.argv[1:]:
        src = os.path.join(ROOT, 'script', 'raw', name + '.tsv')
        dst = os.path.join(out_dir, name + '.tsv')
        if os.path.exists(dst):
            print(f'{dst} exists, skipped')
            continue
        with open(src, encoding='utf-8') as f, open(dst, 'w', encoding='utf-8') as o:
            o.write('id\tja\ten\n')
            for line in f:
                mid, ja = line.rstrip('\n').split('\t', 1)
                o.write(f'{mid}\t{ja}\t\n')
        print(f'wrote {dst}')


if __name__ == '__main__':
    main()
