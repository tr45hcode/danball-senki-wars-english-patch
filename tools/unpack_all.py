#!/usr/bin/env python3
"""Unpack every file in the game CPK, expanding MRON containers.

Usage: unpack_all.py <DA3File_3ds.cpk> <out_dir> [jobs]

Layout:
  out_dir/<cpk id>.<ext>                         non-MRON files (afs2, seek, l2)
  out_dir/<cpk id>/<index>_<TAG>_<entry id>.bin  decompressed MRON entries
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mron  # noqa: E402
from cpk import Cpk  # noqa: E402

EXT = {b'AFS2': 'awb', b'Seek': 'seek', b'L2\xaa\xab': 'l2'}


def unpack(args):
    cpk_path, out, chunk = args
    cpk = Cpk(cpk_path)
    for e in chunk:
        data = cpk.read(e)
        if data[:8] != mron.MAGIC:
            ext = EXT.get(data[:4], 'bin')
            with open(os.path.join(out, f"{e['name']}.{ext}"), 'wb') as f:
                f.write(data)
            continue
        d = os.path.join(out, e['name'])
        os.makedirs(d, exist_ok=True)
        for i, ent in enumerate(mron.parse(data)):
            if ent['tag'] == 'SEEK':
                continue
            tag = ent['tag'].replace('-', '_')
            with open(os.path.join(d, f"{i:03d}_{tag}_{ent['id']:08x}.bin"), 'wb') as f:
                f.write(mron.read_entry(data, ent))
    return len(chunk)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cpk_path, out = sys.argv[1], sys.argv[2]
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
    os.makedirs(out, exist_ok=True)
    files = Cpk(cpk_path).files
    n = 128
    chunks = [(cpk_path, out, files[i::n]) for i in range(n)]
    done = 0
    with ProcessPoolExecutor(jobs) as ex:
        for count in ex.map(unpack, chunks):
            done += count
            print(f'{done}/{len(files)}', end='\r', flush=True)
    print()


if __name__ == '__main__':
    main()
