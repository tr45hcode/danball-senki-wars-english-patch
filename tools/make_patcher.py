#!/usr/bin/env python3
"""Build the one-file web patcher: patcher/index.template.html with the
patch and patcher/core.js inlined, so the result opens offline by double
click and needs no server.

Usage: make_patcher.py <patch.dswp> <out.html> [--version "v0.2-beta"]
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    args = sys.argv[1:]
    version = 'English patch'
    if '--version' in args:
        i = args.index('--version')
        version = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    patch_path, out_path = args
    read = lambda *p: open(os.path.join(ROOT, 'patcher', *p), encoding='utf-8').read()
    html = read('index.template.html')
    core = read('core.js')
    assert '</script' not in core
    with open(patch_path, 'rb') as f:
        patch = base64.b64encode(f.read()).decode('ascii')
    # the patch goes in last: it is by far the largest piece
    html = html.replace('__VERSION__', version).replace('__CORE__', core).replace('__PATCH__', patch)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'wrote {out_path} ({os.path.getsize(out_path):,} bytes)')


if __name__ == '__main__':
    main()
