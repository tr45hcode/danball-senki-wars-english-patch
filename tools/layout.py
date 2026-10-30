#!/usr/bin/env python3
"""Show how the original Japanese messages are laid out.

Usage: layout.py <container>...    width (px) and line count of each message
       layout.py --scan            files that may use a one-line box

Widths are measured the way the build does (build_patch.original_layout).
The build lets English use at least the Japanese width and line count, so a
three-line Japanese system message may take three lines of English.

--scan lists RMD files whose messages are all single lines with at least one
wider than 308 px, the widest two-line dialogue. Map chatter looks like that
(52508/53900, confirmed in-game), but so does dialogue that relies on the
game wrapping long Japanese lines by itself, so a hit is only a candidate.
Confirmed or suspected one-line files go in textfit.BOXES.
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfit  # noqa: E402
from build_patch import original_layout  # noqa: E402
from rmd import Rmd  # noqa: E402


def layouts(path):
    rmd = Rmd(open(path, 'rb').read())
    cell = rmd.cell if rmd.cell in textfit._PROPORTIONAL else 14

    def gw(v):
        return textfit.char_width(textfit.GLOBAL_CHARS[v - 1], cell) if 1 <= v <= 297 else cell
    return rmd.cell, [(m[0], *original_layout(rmd, m[1], gw)[:2]) for m in rmd.messages()]


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cpk = os.path.join(ROOT, 'extracted', 'cpk')
    if args == ['--scan']:
        for path in sorted(glob.glob(os.path.join(cpk, '*', '*_RMD__*.bin'))):
            try:
                _, msgs = layouts(path)
            except Exception:   # broken debug files
                continue
            if msgs and all(n == 1 for _, _, n in msgs) and max(w for _, w, _ in msgs) > 308:
                print(f'{os.path.relpath(path, cpk)}: {len(msgs)} messages, '
                      f'widest {max(w for _, w, _ in msgs)} px')
        return
    for container in args:
        for path in sorted(glob.glob(os.path.join(cpk, container, '*_RMD__*.bin'))):
            cell, msgs = layouts(path)
            print(f'{os.path.relpath(path, cpk)} (cell {cell}):',
                  ' '.join(f'{mid}:{w}px/{n}' for mid, w, n in msgs))


if __name__ == '__main__':
    main()
