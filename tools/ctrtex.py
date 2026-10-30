#!/usr/bin/env python3
"""3DS texture helpers (Morton-tiled 8x8 tiles, origin bottom-left)."""
from PIL import Image


def _morton(i):
    x = y = 0
    for b in range(3):
        x |= ((i >> (2 * b)) & 1) << b
        y |= ((i >> (2 * b + 1)) & 1) << b
    return x, y


_MORTON = [_morton(i) for i in range(64)]


def decode_l8(data, w, h):
    """Decode an 8bpp single-channel tiled texture to a PIL 'L' image."""
    img = Image.new('L', (w, h))
    px = img.load()
    i = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for x, y in _MORTON:
                px[tx + x, ty + y] = data[i]
                i += 1
    return img.transpose(Image.FLIP_TOP_BOTTOM)


def encode_l8(img):
    """Inverse of decode_l8."""
    img = img.convert('L').transpose(Image.FLIP_TOP_BOTTOM)
    w, h = img.size
    px = img.load()
    out = bytearray(w * h)
    i = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for x, y in _MORTON:
                out[i] = px[tx + x, ty + y]
                i += 1
    return bytes(out)
