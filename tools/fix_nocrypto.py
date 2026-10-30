#!/usr/bin/env python3
"""Copy a .3ds whose game partition is decrypted but lacks the NoCrypto flag,
setting NCCH flags[7] bit 2 on partition 0 so emulators don't try to decrypt it.

Usage: fix_nocrypto.py <in.3ds> <out.3ds>
"""
import shutil
import struct
import sys

NO_CRYPTO = 0x04


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, 'rb') as f:
        hdr = f.read(0x200)
        ncch = struct.unpack_from('<I', hdr, 0x120)[0] * 0x200
        f.seek(ncch)
        n = f.read(0x200)
        exefs = struct.unpack_from('<I', n, 0x1A0)[0] * 0x200
        f.seek(ncch + exefs)
        if f.read(5) != b'.code':
            sys.exit('partition 0 ExeFS is not decrypted; refusing to flag it')
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(ncch + 0x18B)
        f.write(b'\0')                       # crypto method: none
        f.seek(ncch + 0x18F)
        f.write(bytes((n[0x18F] | NO_CRYPTO,)))
    print(f'wrote {dst}')


if __name__ == '__main__':
    main()
