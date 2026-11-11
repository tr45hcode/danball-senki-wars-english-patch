#!/usr/bin/env python3
"""AIF textures (the payload of IMAG, IMGR and UAIF entries, Aska3DS engine).

Layout (little-endian, chunk tags stored reversed):
  0x00  'AIF ' chunk, 0xF0 bytes of headers
  0x80    'imgX': 0x90 u32 id, 0x94 char[4] source tag,
          0xA0 u16 pixel format, 0xA8 u16 width, 0xAA u16 height,
          0xAE u16 bits per pixel, 0xB8 u32 row pitch, 0xBC u32 data size
  0xF0  'AMF ' chunk: 'head', 'buff', 'adda' sub-chunks (0xF0 bytes)
  0x1E0 pixel data (imgX + 0x160; two files have no 'aRF ' chunk, which
        puts imgX at 0x10 and the pixels at 0x170), PICA200 native: 8x8 tiles in Morton order, rows
        bottom-up, components byte-swapped (RGBA8 is stored A B G R).

Pixel formats:
  0x03 RGB565     0x06 RGBA4444   0x07 RGBA5551   0x08 RGBA8888
  0x22 A8         0x24 RGB888     0x25 ETC1       0x26 ETC1A4

Usage:
  aif.py info <file.bin>
  aif.py png <file.bin> <out.png>
  aif.py sheet <out_dir> <container dir>...   one contact sheet per container

Needs Pillow. numpy (.venv/bin/python) only makes ETC1 decoding faster.
"""
import os
import struct
import sys

from PIL import Image

try:  # optional: faster ETC1 decoding
    import numpy as np
except ImportError:
    np = None

FORMATS = {0x03: 'RGB565', 0x06: 'RGBA4444', 0x07: 'RGBA5551',
           0x08: 'RGBA8888', 0x22: 'A8', 0x24: 'RGB888', 0x25: 'ETC1',
           0x26: 'ETC1A4'}
BPP = {0x03: 16, 0x06: 16, 0x07: 16, 0x08: 32, 0x22: 8, 0x24: 24,
       0x25: 4, 0x26: 8}


def header(data):
    """Return dict: fmt, name, width, height, bpp, size."""
    if data[:4] != b' FIA':
        raise ValueError('not an AIF texture')
    for o in (0x80, 0x10):
        if data[o:o + 4] == b'Xgmi':
            break
    else:
        raise ValueError('AIF without an imgX chunk')
    fmt, = struct.unpack_from('<H', data, o + 0x20)
    w, h = struct.unpack_from('<HH', data, o + 0x28)
    bpp, = struct.unpack_from('<H', data, o + 0x2E)
    size, = struct.unpack_from('<I', data, o + 0x3C)
    return {'fmt': fmt, 'name': FORMATS.get(fmt, hex(fmt)), 'width': w,
            'height': h, 'bpp': bpp, 'size': size, 'data': o + 0x160}


def _perm(w, h):
    """perm[y * w + x] = position of pixel (x, y), top-down, in the stream."""
    cached = _PERMS.get((w, h))
    if cached:
        return cached
    tile = []
    for i in range(64):
        x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
        y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
        tile.append((x, y))
    perm = [0] * (w * h)
    n = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for x, y in tile:
                perm[(h - 1 - ty - y) * w + tx + x] = n
                n += 1
    inv = [0] * (w * h)
    for i, p in enumerate(perm):
        inv[p] = i
    _PERMS[(w, h)] = (perm, inv)
    return perm, inv


_PERMS = {}
_HI = bytes((i >> 4) * 17 for i in range(256))
_LO = bytes((i & 15) * 17 for i in range(256))
_Q4 = bytes((i + 8) // 17 for i in range(256))


def _take(plane, order):
    return bytes(map(plane.__getitem__, order))


# ---- ETC1 ---------------------------------------------------------------

_MOD = [[2, 8], [5, 17], [9, 29], [13, 42], [18, 60], [24, 80],
        [33, 106], [47, 183]]


def _etc1_decode(blocks):
    """blocks: (N,) uint64 (as stored, little-endian) -> (N, 4, 4, 3) uint8,
    indexed [block, y, x]."""
    b = blocks.astype(np.uint64)
    hi = (b >> np.uint64(32)).astype(np.int64)
    lo = (b & np.uint64(0xFFFFFFFF)).astype(np.int64)
    diff = (hi >> 1) & 1
    flip = hi & 1
    t1 = (hi >> 5) & 7
    t2 = (hi >> 2) & 7
    base = np.empty((len(b), 2, 3), dtype=np.int32)
    for c, sh in enumerate((24, 16, 8)):
        v = (hi >> sh) & 0xFF
        a5 = v >> 3
        d3 = v & 7
        d3 = np.where(d3 > 3, d3 - 8, d3)
        b5 = a5 + d3
        c1d = (a5 << 3) | (a5 >> 2)
        c2d = (b5 << 3) | (b5 >> 2)
        a4 = v >> 4
        b4 = v & 15
        base[:, 0, c] = np.where(diff == 1, c1d, a4 * 17)
        base[:, 1, c] = np.where(diff == 1, c2d, b4 * 17)
    out = np.empty((len(b), 4, 4, 3), dtype=np.uint8)
    for x in range(4):
        for y in range(4):
            k = x * 4 + y
            msb = (lo >> (k + 16)) & 1
            lsb = (lo >> k) & 1
            sub = np.where(flip == 1, y >= 2, x >= 2).astype(np.int64)
            tbl = np.where(sub == 1, t2, t1)
            mod = np.array(_MOD)[tbl, lsb] * np.where(msb == 1, -1, 1)
            col = base[np.arange(len(b)), sub] + mod[:, None]
            out[:, y, x] = np.clip(col, 0, 255)
    return out


def _etc_layout(w, h):
    """Block order of the stream: 8x8 tiles row-major, 2x2 blocks in each
    tile in Z order. Returns (by, bx) block coordinates per stream block."""
    ty, tx = np.mgrid[0:h // 8, 0:w // 8]
    by = (ty.reshape(-1, 1) * 2 + np.array([0, 0, 1, 1])).reshape(-1)
    bx = (tx.reshape(-1, 1) * 2 + np.array([0, 1, 0, 1])).reshape(-1)
    return by, bx


def _decode_etc(raw, w, h, alpha):
    if np is None:
        return _decode_etc_py(raw, w, h, alpha)
    n = (w // 4) * (h // 4)
    step = 16 if alpha else 8
    buf = np.frombuffer(raw[:n * step], dtype='<u8').reshape(n, -1)
    rgb = _etc1_decode(buf[:, -1])
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 3] = 255
    by, bx = _etc_layout(w, h)
    view = out.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4)
    view[by, bx, :, :, :3] = rgb
    if alpha:
        a = buf[:, 0]
        al = np.empty((n, 4, 4), dtype=np.uint8)
        for x in range(4):
            for y in range(4):
                sh = np.uint64((x * 4 + y) * 4)
                al[:, y, x] = ((a >> sh) & np.uint64(15)).astype(np.uint8) * 17
        view[by, bx, :, :, 3] = al
    return Image.fromarray(out[::-1], 'RGBA')


# Pure-Python ETC1, one block at a time. The build uses it to rewrite only
# the blocks under a redrawn sprite, so the rest of a texture stays as it is.

def _block_pos(w, h):
    """Stream order of the 4x4 blocks: [(bx, by)], by counted from the
    bottom as stored."""
    out = []
    for ty in range(0, h // 4, 2):
        for tx in range(0, w // 4, 2):
            out += [(tx, ty), (tx + 1, ty), (tx, ty + 1), (tx + 1, ty + 1)]
    return out


def _etc_bases(hi):
    diff = (hi >> 1) & 1
    bases = ([], [])
    for sh in (24, 16, 8):
        v = (hi >> sh) & 0xFF
        if diff:
            a = v >> 3
            d = v & 7
            b = a + (d - 8 if d > 3 else d)
            bases[0].append((a << 3) | (a >> 2))
            bases[1].append(((b << 3) | (b >> 2)) & 0xFF)
        else:
            bases[0].append((v >> 4) * 17)
            bases[1].append((v & 15) * 17)
    return bases


def etc1_block_decode(block):
    """block: 64-bit int (the stored little-endian u64). Returns 16 RGB
    tuples indexed [y * 4 + x], y from the top of the stored (flipped)
    image."""
    hi, lo = block >> 32, block & 0xFFFFFFFF
    flip = hi & 1
    tables = ((hi >> 5) & 7, (hi >> 2) & 7)
    bases = _etc_bases(hi)
    out = [None] * 16
    for x in range(4):
        for y in range(4):
            k = x * 4 + y
            sub = (y >= 2) if flip else (x >= 2)
            mod = _MOD[tables[sub]][(lo >> k) & 1]
            if (lo >> (k + 16)) & 1:
                mod = -mod
            out[y * 4 + x] = tuple(min(255, max(0, c + mod)) for c in bases[sub])
    return out


def etc1_block_encode(px):
    """px: 16 RGB tuples [y * 4 + x]. Returns the 64-bit block with the
    lowest squared error over both flips and both colour modes."""
    best = None
    for flip in (0, 1):
        if flip:
            subs = [[(x, y) for y in (0, 1) for x in range(4)],
                    [(x, y) for y in (2, 3) for x in range(4)]]
        else:
            subs = [[(x, y) for x in (0, 1) for y in range(4)],
                    [(x, y) for x in (2, 3) for y in range(4)]]
        avg = [[sum(px[y * 4 + x][c] for x, y in sub) / 8 for c in range(3)]
               for sub in subs]
        # individual: 4 bits per channel; differential: 5 bits + 3-bit delta
        q4 = [[min(15, int(a / 17 + 0.5)) for a in av] for av in avg]
        q5a = [min(31, int(a * 31 / 255 + 0.5)) for a in avg[0]]
        q5b = [min(31, int(a * 31 / 255 + 0.5)) for a in avg[1]]
        dlt = [max(-4, min(3, b - a)) for a, b in zip(q5a, q5b)]
        q5b = [a + d for a, d in zip(q5a, dlt)]
        modes = [(0, q4, [[q * 17 for q in q4[0]], [q * 17 for q in q4[1]]]),
                 (1, (q5a, dlt), [[(q << 3) | (q >> 2) for q in q5a],
                                  [(q << 3) | (q >> 2) for q in q5b]])]
        for diff, q, bases in modes:
            total, tabs, sels = 0, [], []
            for sub, base in zip(subs, bases):
                pick = None
                for t in range(8):
                    small, large = _MOD[t]
                    cols = [tuple(min(255, max(0, c + m)) for c in base)
                            for m in (small, large, -small, -large)]
                    err, sel = 0, []
                    for x, y in sub:
                        p = px[y * 4 + x]
                        e = [(p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 +
                             (p[2] - c[2]) ** 2 for c in cols]
                        m = min(e)
                        err += m
                        sel.append(e.index(m))
                    if pick is None or err < pick[0]:
                        pick = (err, t, sel)
                total += pick[0]
                tabs.append(pick[1])
                sels.append(dict(zip(sub, pick[2])))
            if best is None or total < best[0]:
                best = (total, flip, diff, q, tabs, sels)
    _, flip, diff, q, tabs, sels = best
    hi = (tabs[0] << 5) | (tabs[1] << 2) | (diff << 1) | flip
    for c, sh in enumerate((24, 16, 8)):
        if diff:
            hi |= ((q[0][c] << 3) | (q[1][c] & 7)) << sh
        else:
            hi |= ((q[0][c] << 4) | q[1][c]) << sh
    lo = 0
    for sel in sels:
        for (x, y), s in sel.items():
            k = x * 4 + y
            lo |= (s & 1) << k          # 0/1: small/large
            lo |= (s >> 1) << (k + 16)  # 2/3: negative
    return (hi << 32) | lo


def _decode_etc_py(raw, w, h, alpha):
    step = 16 if alpha else 8
    out = Image.new('RGBA', (w, h))
    px = out.load()
    for i, (bx, by) in enumerate(_block_pos(w, h)):
        o = i * step
        cols = etc1_block_decode(int.from_bytes(raw[o + step - 8:o + step], 'little'))
        al = int.from_bytes(raw[o:o + 8], 'little') if alpha else None
        for x in range(4):
            for y in range(4):
                a = ((al >> ((x * 4 + y) * 4)) & 15) * 17 if alpha else 255
                px[bx * 4 + x, h - 1 - (by * 4 + y)] = cols[y * 4 + x] + (a,)
    return out


def _encode_etc(data, hd, img, rects):
    """Rewrite the blocks of an ETC1/ETC1A4 texture under `rects`
    (x, y, w, h, top-down) with the pixels of `img`."""
    w, h, alpha = hd['width'], hd['height'], hd['fmt'] == 0x26
    step = 16 if alpha else 8
    index = {pos: i for i, pos in enumerate(_block_pos(w, h))}
    blocks = set()
    for x, y, rw, rh in rects:
        for by in range((h - y - rh) // 4, (h - y - 1) // 4 + 1):
            for bx in range(x // 4, (x + rw - 1) // 4 + 1):
                blocks.add((bx, by))
    out = bytearray(data)
    px = img.convert('RGBA').load()
    for bx, by in sorted(blocks):
        o = hd['data'] + index[(bx, by)] * step
        cols, al = [None] * 16, 0
        for x in range(4):
            for y in range(4):
                p = px[bx * 4 + x, h - 1 - (by * 4 + y)]
                cols[y * 4 + x] = p[:3]
                al |= ((p[3] + 8) // 17) << ((x * 4 + y) * 4)
        if alpha:
            out[o:o + 8] = al.to_bytes(8, 'little')
        out[o + step - 8:o + step] = etc1_block_encode(cols).to_bytes(8, 'little')
    return bytes(out)


# ---- public -------------------------------------------------------------

def decode(data):
    """Return a PIL RGBA image."""
    hd = header(data)
    fmt, w, h = hd['fmt'], hd['width'], hd['height']
    raw = data[hd['data']:hd['data'] + w * h * BPP[fmt] // 8]
    if fmt in (0x25, 0x26):
        return _decode_etc(raw, w, h, fmt == 0x26)
    perm, _ = _perm(w, h)
    full = b'\xff' * (w * h)
    if fmt == 0x08:      # stored A B G R
        planes = [raw[3::4], raw[2::4], raw[1::4], raw[0::4]]
    elif fmt == 0x24:    # stored B G R
        planes = [raw[2::3], raw[1::3], raw[0::3], full]
    elif fmt == 0x22:
        planes = [full, full, full, raw]
    elif fmt == 0x06:    # u16 LE, nibbles R G B A from the top
        lo, hi = raw[0::2], raw[1::2]
        planes = [hi.translate(_HI), hi.translate(_LO),
                  lo.translate(_HI), lo.translate(_LO)]
    elif fmt in (0x03, 0x07):
        v = struct.unpack(f'<{w * h}H', raw)
        if fmt == 0x07:
            planes = [bytes((x >> 11) * 255 // 31 for x in v),
                      bytes(((x >> 6) & 31) * 255 // 31 for x in v),
                      bytes(((x >> 1) & 31) * 255 // 31 for x in v),
                      bytes((x & 1) * 255 for x in v)]
        else:
            planes = [bytes((x >> 11) * 255 // 31 for x in v),
                      bytes(((x >> 5) & 63) * 255 // 63 for x in v),
                      bytes((x & 31) * 255 // 31 for x in v), full]
    else:
        raise ValueError(f'unknown pixel format {fmt:#x}')
    return Image.merge('RGBA', [Image.frombytes('L', (w, h), _take(p, perm))
                                for p in planes])


def encode(data, img, rects=None):
    """Return a copy of the AIF `data` with its pixels replaced by `img`
    (same size and format, so the entry never changes size). ETC1 textures
    are lossy, so there only the 4x4 blocks under `rects` (x, y, w, h) are
    rewritten; RGB565 and RGBA5551 aren't written at all."""
    hd = header(data)
    fmt, w, h = hd['fmt'], hd['width'], hd['height']
    if img.size != (w, h):
        raise ValueError(f'image is {img.size}, texture is {(w, h)}')
    if fmt in (0x25, 0x26):
        return _encode_etc(data, hd, img, rects or [])
    _, inv = _perm(w, h)
    r, g, b, a = (_take(p.tobytes(), inv) for p in img.convert('RGBA').split())
    if fmt == 0x08:
        raw = bytearray(w * h * 4)
        raw[0::4], raw[1::4], raw[2::4], raw[3::4] = a, b, g, r
    elif fmt == 0x24:
        raw = bytearray(w * h * 3)
        raw[0::3], raw[1::3], raw[2::3] = b, g, r
    elif fmt == 0x22:
        raw = a
    elif fmt == 0x06:
        r, g, b, a = (p.translate(_Q4) for p in (r, g, b, a))
        raw = bytearray(w * h * 2)
        raw[0::2] = bytes((x << 4) | y for x, y in zip(b, a))
        raw[1::2] = bytes((x << 4) | y for x, y in zip(r, g))
    else:
        raise ValueError(f'cannot write pixel format {FORMATS.get(fmt, fmt)}')
    o = hd['data']
    return data[:o] + bytes(raw) + data[o + len(raw):]


def sheet(paths, out_png, bg=(64, 64, 96)):
    """Draw every texture in `paths` on one labelled contact sheet."""
    from PIL import ImageDraw
    tiles = []
    for p in paths:
        try:
            d = open(p, 'rb').read()
            im = decode(d)
            tiles.append((os.path.basename(p)[:8] + ' ' + header(d)['name'], im))
        except Exception as e:  # noqa: BLE001
            print(f'{p}: {e}', file=sys.stderr)
    if not tiles:
        return False
    width = 1040
    x = y = rowh = 0
    pos = []
    for label, im in tiles:
        if x and x + im.width > width:
            x, y, rowh = 0, y + rowh + 14, 0
        pos.append((x, y))
        x += im.width + 4
        rowh = max(rowh, im.height)
    canvas = Image.new('RGB', (max(width, max(im.width for _, im in tiles)),
                               y + rowh + 14), bg)
    dr = ImageDraw.Draw(canvas)
    for (label, im), (px, py) in zip(tiles, pos):
        canvas.paste(im, (px, py + 12), im)
        dr.text((px, py), label, fill=(255, 255, 0))
    canvas.save(out_png)
    return True


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'info':
        print(header(open(sys.argv[2], 'rb').read()))
    elif cmd == 'png':
        decode(open(sys.argv[2], 'rb').read()).save(sys.argv[3])
    elif cmd == 'sheet':
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        for d in sys.argv[3:]:
            files = sorted(os.path.join(d, f) for f in os.listdir(d)
                           if f[4:8] in ('IMAG', 'IMGR', 'UAIF'))
            if files and sheet(files, os.path.join(
                    out, os.path.basename(d.rstrip('/')) + '.png')):
                print(d, len(files))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
