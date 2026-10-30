#!/usr/bin/env python3
"""Print translation coverage as a Markdown table (for PROGRESS.md).

Usage: progress.py

Counts messages in script/raw and those with English in script/en, grouped
by container range. The 10 px duplicate of the system text (01000_100) is
excluded: it repeats 01000_098 message for message.
"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUPS = [
    ('Story scenes', lambda c: 52000 <= c < 54000),
    ('Character conversations', lambda c: 11000 <= c < 12000),
    ('Map examine text', lambda c: 6000 <= c < 7000),
    ('Character/LBX data', lambda c: 13000 <= c < 14000),
    ('System & UI', lambda c: c < 2000),
    ('Other', lambda c: True),
]
SKIP = {'01000_100_000303e8'}


def translated(name):
    path = os.path.join(ROOT, 'script', 'en', name + '.tsv')
    done = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                cols = line.rstrip('\n').split('\t')
                if len(cols) >= 3 and cols[0].isdigit() and cols[-1].strip():
                    done.add(int(cols[0]))
    return done


def main():
    totals = {g: [0, 0] for g, _ in GROUPS}
    for path in sorted(glob.glob(os.path.join(ROOT, 'script', 'raw', '*_*.tsv'))):
        name = os.path.basename(path)[:-4]
        if name in SKIP:
            continue
        cont = int(name[:5])
        group = next(g for g, test in GROUPS if test(cont))
        with open(path, encoding='utf-8') as f:
            ids = {int(line.split('\t', 1)[0]) for line in f if line.strip()}
        totals[group][0] += len(ids)
        totals[group][1] += len(ids & translated(name))
    print('| Area | Translated | Total | % |')
    print('|---|---:|---:|---:|')
    all_t = all_d = 0
    for g, (t, d) in totals.items():
        if t:
            print(f'| {g} | {d:,} | {t:,} | {100 * d / t:.1f}% |')
            all_t += t
            all_d += d
    print(f'| **All** | **{all_d:,}** | **{all_t:,}** | **{100 * all_d / all_t:.1f}%** |')


if __name__ == '__main__':
    main()
