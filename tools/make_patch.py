#!/usr/bin/env python3
"""Make and apply the English patch file (.dswp).

The release is one small file that turns the player's own DA3File_3ds.cpk
into the patched one. It holds no copy of the game: unchanged stretches
are references into the player's file, and only the bytes that differ
(new text, redrawn textures, the rewritten ITOC) are stored, deflated.

Usage:
  make_patch.py make  <original.cpk> <patched.cpk> <out.dswp>
  make_patch.py apply <patch.dswp> <original.cpk> <out.cpk>
  make_patch.py info  <patch.dswp>

File layout (all integers little-endian):
  8   magic 'DSWPAT01'
  8   size of the original CPK        32  its SHA-256
  8   size of the patched CPK         32  its SHA-256
  4   size of the payload once inflated
  ..  payload, raw-deflated: varint op count, then per op a varint kind
      (0 copy: varint source offset, varint length; 1 add: varint length),
      then every added byte in order.

The web patcher (patcher/core.js) reads the same format.
"""
import hashlib
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import Cpk  # noqa: E402

MAGIC = b'DSWPAT01'
BLOCK = 128          # entries inside a container only ever move by multiples of this
CHUNK = 1 << 22


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def read_varint(buf, pos):
    n = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n, pos
        shift += 7


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(CHUNK)
            if not buf:
                return h.hexdigest()
            h.update(buf)


class Ops:
    """Copy and add operations, with neighbours merged."""

    def __init__(self):
        self.ops = []       # ['c', src_off, length] or ['a', bytearray]

    def copy(self, off, length):
        if not length:
            return
        last = self.ops[-1] if self.ops else None
        if last and last[0] == 'c' and last[1] + last[2] == off:
            last[2] += length
        else:
            self.ops.append(['c', off, length])

    def add(self, data):
        if not data:
            return
        last = self.ops[-1] if self.ops else None
        if last and last[0] == 'a':
            last[1] += data
        else:
            self.ops.append(['a', bytearray(data)])


def common_length(a, b):
    """How many leading bytes a and b share."""
    n = min(len(a), len(b))
    pos = 0
    while pos < n:
        step = min(4096, n - pos)
        if a[pos:pos + step] == b[pos:pos + step]:
            pos += step
            continue
        for i in range(step):
            if a[pos + i] != b[pos + i]:
                return pos + i
    return n


def diff(ops, src, src_base, dst):
    """Add the operations that turn `src` (which starts at src_base in the
    original CPK) into `dst`: blocks of dst that sit in src at a multiple of
    BLOCK become copies, everything else is added."""
    index = {}
    for off in range(0, len(src) - BLOCK + 1, BLOCK):
        index.setdefault(hash(src[off:off + BLOCK]), off)
    pos = lit = 0
    n = len(dst)
    while pos + BLOCK <= n:
        off = index.get(hash(dst[pos:pos + BLOCK]))
        if off is None or src[off:off + BLOCK] != dst[pos:pos + BLOCK]:
            pos += BLOCK
            continue
        length = BLOCK + common_length(src[off + BLOCK:], dst[pos + BLOCK:])
        ops.add(dst[lit:pos])
        ops.copy(src_base + off, length)
        pos += length
        lit = pos
        pos += -pos % BLOCK     # back onto the grid the entries sit on
    ops.add(dst[lit:])


def make(orig_path, new_path, out_path):
    src, dst = Cpk(orig_path), Cpk(new_path)
    src_files = {e['id']: e for e in src.files}
    ops = Ops()
    fsrc, fdst = open(orig_path, 'rb'), open(new_path, 'rb')

    first = min(e['offset'] for e in dst.files)
    fsrc.seek(0)
    fdst.seek(0)
    diff(ops, fsrc.read(min(e['offset'] for e in src.files)), 0, fdst.read(first))
    end = first
    changed = 0
    for e in sorted(dst.files, key=lambda e: e['offset']):
        if e['offset'] > end:
            fdst.seek(end)
            ops.add(fdst.read(e['offset'] - end))
        s = src_files.get(e['id'])
        fdst.seek(e['offset'])
        new = fdst.read(e['size'])
        if s is not None:
            fsrc.seek(s['offset'])
            old = fsrc.read(s['size'])
            if old == new:
                ops.copy(s['offset'], s['size'])
            else:
                changed += 1
                diff(ops, old, s['offset'], new)
        else:
            changed += 1
            ops.add(new)
        end = e['offset'] + e['size']
    fdst.seek(end)
    ops.add(fdst.read())

    body = bytearray(varint(len(ops.ops)))
    lits = bytearray()
    for op in ops.ops:
        if op[0] == 'c':
            body += varint(0) + varint(op[1]) + varint(op[2])
        else:
            body += varint(1) + varint(len(op[1]))
            lits += op[1]
    payload = bytes(body + lits)
    z = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = z.compress(payload) + z.flush()
    with open(out_path, 'wb') as f:
        f.write(MAGIC)
        f.write(struct.pack('<Q', os.path.getsize(orig_path)))
        f.write(bytes.fromhex(sha256_file(orig_path)))
        f.write(struct.pack('<Q', os.path.getsize(new_path)))
        f.write(bytes.fromhex(sha256_file(new_path)))
        f.write(struct.pack('<I', len(payload)))
        f.write(packed)
    print(f'{changed} files changed, {len(ops.ops)} operations, {len(lits):,} bytes added, '
          f'patch {os.path.getsize(out_path):,} bytes')


def parse(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:8] != MAGIC:
        raise ValueError('not a .dswp patch')
    src_size, = struct.unpack_from('<Q', data, 8)
    src_hash = data[16:48].hex()
    dst_size, = struct.unpack_from('<Q', data, 48)
    dst_hash = data[56:88].hex()
    raw_len, = struct.unpack_from('<I', data, 88)
    payload = zlib.decompress(data[92:], -15)
    if len(payload) != raw_len:
        raise ValueError('patch is damaged')
    count, pos = read_varint(payload, 0)
    ops = []
    for _ in range(count):
        kind, pos = read_varint(payload, pos)
        if kind == 0:
            off, pos = read_varint(payload, pos)
            length, pos = read_varint(payload, pos)
            ops.append((0, off, length))
        else:
            length, pos = read_varint(payload, pos)
            ops.append((1, 0, length))
    return {'src_size': src_size, 'src_hash': src_hash, 'dst_size': dst_size,
            'dst_hash': dst_hash, 'ops': ops, 'lits': payload[pos:]}


def apply(patch_path, orig_path, out_path):
    p = parse(patch_path)
    if os.path.getsize(orig_path) != p['src_size']:
        sys.exit('this is not the right file: the size differs')
    if sha256_file(orig_path) != p['src_hash']:
        sys.exit('this is not the right file: the checksum differs')
    h = hashlib.sha256()
    lit = 0
    with open(orig_path, 'rb') as src, open(out_path, 'wb') as out:
        for kind, off, length in p['ops']:
            if kind == 0:
                src.seek(off)
                left = length
                while left:
                    buf = src.read(min(left, CHUNK))
                    out.write(buf)
                    h.update(buf)
                    left -= len(buf)
            else:
                buf = p['lits'][lit:lit + length]
                lit += length
                out.write(buf)
                h.update(buf)
    if h.hexdigest() != p['dst_hash']:
        os.remove(out_path)
        sys.exit('the result does not match: the patch or the input is damaged')
    print(f'wrote {out_path} ({p["dst_size"]:,} bytes, checksum ok)')


def main():
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == 'make':
        make(*args[1:])
    elif len(args) == 4 and args[0] == 'apply':
        apply(*args[1:])
    elif len(args) == 2 and args[0] == 'info':
        p = parse(args[1])
        print(f"original {p['src_size']:,} bytes sha256 {p['src_hash']}")
        print(f"patched  {p['dst_size']:,} bytes sha256 {p['dst_hash']}")
        print(f"{len(p['ops'])} operations, {len(p['lits']):,} bytes added")
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
