#!/usr/bin/env python3
"""Extract ExHeader, ExFS and RomFS from a decrypted .3ds (NCSD) image.

Usage: extract_3ds.py <game.3ds> <out_dir>

Produces:
  out_dir/exheader.bin
  out_dir/exefs/{code.bin,banner.bin,icon.bin,logo.bin}
  out_dir/romfs/...
"""
import os
import struct
import sys

MU = 0x200  # media unit
CHUNK = 1 << 20


def copy_range(src, off, size, dst_path):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    src.seek(off)
    with open(dst_path, 'wb') as dst:
        while size:
            buf = src.read(min(CHUNK, size))
            if not buf:
                raise EOFError(f'unexpected EOF while writing {dst_path}')
            dst.write(buf)
            size -= len(buf)


def extract_exefs(f, base, out):
    f.seek(base)
    hdr = f.read(0x200)
    for i in range(10):
        name, off, size = struct.unpack_from('<8sII', hdr, i * 0x10)
        name = name.rstrip(b'\0').decode('ascii')
        if not size:
            continue
        fname = 'code.bin' if name == '.code' else name + '.bin'
        copy_range(f, base + 0x200 + off, size, os.path.join(out, 'exefs', fname))
        print(f'exefs/{fname}  {size:#x}')


def utf16_name(buf, off, length):
    return buf[off:off + length].decode('utf-16-le')


def extract_romfs(f, base, out):
    f.seek(base)
    ivfc = f.read(0x60)
    if ivfc[:4] != b'IVFC':
        raise ValueError('RomFS has no IVFC header (still encrypted?)')
    master_hash_size = struct.unpack_from('<I', ivfc, 0x08)[0]
    l3_block_log2 = struct.unpack_from('<I', ivfc, 0x4C)[0]
    align = 1 << l3_block_log2
    l3 = base + ((0x60 + master_hash_size + align - 1) & ~(align - 1))

    f.seek(l3)
    h = struct.unpack('<10I', f.read(0x28))
    if h[0] != 0x28:
        raise ValueError(f'bad RomFS level 3 header size {h[0]:#x}')
    dir_meta_off, dir_meta_size = h[3], h[4]
    file_meta_off, file_meta_size = h[7], h[8]
    data_off = l3 + h[9]

    f.seek(l3 + dir_meta_off)
    dirs = f.read(dir_meta_size)
    f.seek(l3 + file_meta_off)
    files = f.read(file_meta_size)

    count = 0
    # stack of (dir_meta_offset, path)
    stack = [(0, os.path.join(out, 'romfs'))]
    while stack:
        doff, path = stack.pop()
        os.makedirs(path, exist_ok=True)
        _, _, child, first_file, _, _ = struct.unpack_from('<6I', dirs, doff)

        foff = first_file
        while foff != 0xFFFFFFFF:
            _, sibling, data, size, _, name_len = struct.unpack_from('<IIQQII', files, foff)
            name = utf16_name(files, foff + 0x20, name_len)
            copy_range(f, data_off + data, size, os.path.join(path, name))
            count += 1
            foff = sibling

        coff = child
        while coff != 0xFFFFFFFF:
            _, sibling, _, _, _, name_len = struct.unpack_from('<6I', dirs, coff)
            stack.append((coff, os.path.join(path, utf16_name(dirs, coff + 0x18, name_len))))
            coff = sibling
    print(f'romfs: {count} files')


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rom, out = sys.argv[1], sys.argv[2]
    with open(rom, 'rb') as f:
        hdr = f.read(0x200)
        if hdr[0x100:0x104] != b'NCSD':
            sys.exit('not an NCSD (.3ds) image')
        ncch = struct.unpack_from('<I', hdr, 0x120)[0] * MU

        f.seek(ncch)
        n = f.read(0x200)
        if n[0x100:0x104] != b'NCCH':
            sys.exit('partition 0 is not NCCH')
        print('product code:', n[0x150:0x160].rstrip(b'\0').decode())

        exh_size = struct.unpack_from('<I', n, 0x180)[0]
        copy_range(f, ncch + 0x200, exh_size, os.path.join(out, 'exheader.bin'))

        exefs_off = struct.unpack_from('<I', n, 0x1A0)[0] * MU
        romfs_off = struct.unpack_from('<I', n, 0x1B0)[0] * MU
        extract_exefs(f, ncch + exefs_off, out)
        extract_romfs(f, ncch + romfs_off, out)


if __name__ == '__main__':
    main()
