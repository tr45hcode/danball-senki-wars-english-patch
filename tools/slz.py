#!/usr/bin/env python3
"""SLZ decompression (Danball Senki Wars / Aska3DS engine).

Header (0x20 bytes, little-endian):
  0x00  'SLZ' + type (0 = stored, 1/2/3 = LZ variants below)
  0x04  u8[4]   unknown (always 00 01 25 00)
  0x08  u32     compressed size (bytes after the header)
  0x0C  u32     decompressed size
  0x10  u32     next chunk offset (0 = last)
  0x14  u32     header size (0x20)
  0x18  u8      1 if the stream is split into 64 KiB blocks
  0x19  u8[7]   unknown

The payload is a sequence of [u16 block_size][block], each block decoding to
at most 0x10000 bytes. block_size 0 means a stored block: the next
min(0x10000, remaining) bytes are copied as-is.

Type 1: byte LZSS. 8-bit flags, LSB first, 1 = literal byte.
        Token b0 b1: dist = (b1 & 0xF) << 8 | b0, len = (b1 >> 4) + 3.
Type 2: type 1 plus RLE when b1 >> 4 == 0xF:
        b1 & 0xF != 0  ->  b0 repeated (b1 & 0xF) + 3 times
        b1 & 0xF == 0  ->  next byte repeated b0 + 19 times (3-byte token)
Type 3: LZSS over 16-bit words. 16-bit flags, LSB first, 1 = literal word.
        Token b0 b1: dist = (b1 & 0xF) << 8 | b0 words, len = (b1 >> 4) + 2 words.

End of block: in types 1 and 3 a token with distance 0 (bytes 00 00) ends the
block. The original compressor always writes it (in a fresh flag byte if the
current one is full), and the game's decoder relies on it: without it,
decoding runs past the block and corrupts the heap. Type 2 has no end token.
"""
import struct
import sys

HEADER_SIZE = 0x20
BLOCK_OUT = 0x10000


class SlzError(ValueError):
    pass


def _lz_bytes(src, p, end, out, limit, rle):
    """Decode one byte-oriented block (types 1 and 2) from src[p:end] into out."""
    while len(out) < limit and p < end:
        flags = src[p]
        p += 1
        for bit in range(8):
            if len(out) >= limit:
                break
            if flags >> bit & 1:
                out.append(src[p])
                p += 1
                continue
            b0, b1 = src[p], src[p + 1]
            p += 2
            if rle and b1 >> 4 == 0xF:
                if b1 & 0xF:
                    out += bytes((b0,)) * ((b1 & 0xF) + 3)
                else:
                    out += bytes((src[p],)) * (b0 + 19)
                    p += 1
                continue
            dist = (b1 & 0xF) << 8 | b0
            length = (b1 >> 4) + 3
            start = len(out) - dist
            if dist == 0 and not rle:
                return                      # end-of-block token
            if dist == 0 or start < 0:
                raise SlzError(f'bad distance {dist} at output {len(out):#x}')
            if dist >= length:
                out += out[start:start + length]
            else:
                for i in range(length):
                    out.append(out[start + i])


def _lz_words(src, p, end, out, limit):
    """Decode one word-oriented block (type 3) from src[p:end] into out."""
    while len(out) < limit and p < end:
        flags = src[p] | src[p + 1] << 8
        p += 2
        for bit in range(16):
            if len(out) >= limit:
                break
            if flags >> bit & 1:
                out += src[p:p + 2]
                p += 2
                continue
            b0, b1 = src[p], src[p + 1]
            p += 2
            dist = ((b1 & 0xF) << 8 | b0) * 2
            length = ((b1 >> 4) + 2) * 2
            start = len(out) - dist
            if dist == 0:
                return                      # end-of-block token
            if start < 0:
                raise SlzError(f'bad distance {dist} at output {len(out):#x}')
            if dist >= length:
                out += out[start:start + length]
            else:
                for i in range(length):
                    out.append(out[start + i])


def decompress(data, offset=0):
    """Decompress an SLZ stream (following any chained chunks)."""
    result = bytearray()
    while True:
        if data[offset:offset + 3] != b'SLZ':
            raise SlzError(f'no SLZ header at {offset:#x}')
        typ = data[offset + 3]
        csize, dsize, nxt, hsize = struct.unpack_from('<IIII', data, offset + 8)
        p = offset + hsize
        end = p + csize
        if typ == 0:
            result += data[p:p + dsize]
        else:
            out = bytearray()
            while p < end and len(out) < dsize:
                bsize = struct.unpack_from('<H', data, p)[0]
                p += 2
                limit = min(dsize, len(out) + BLOCK_OUT)
                if bsize == 0:
                    # stored block: compressed form would not fit in a u16
                    bsize = limit - len(out)
                    out += data[p:p + bsize]
                elif typ == 3:
                    _lz_words(data, p, p + bsize, out, limit)
                elif typ in (1, 2):
                    _lz_bytes(data, p, p + bsize, out, limit, rle=typ == 2)
                else:
                    raise SlzError(f'unknown SLZ type {typ}')
                p += bsize
            if len(out) < dsize:
                raise SlzError(f'short output {len(out):#x} < {dsize:#x}')
            result += out[:dsize]
        if not nxt:
            return bytes(result)
        offset += nxt


def _compress_block(src, rle):
    """LZSS-compress one block (types 1/2); matches stay inside the block."""
    max_len = 17 if rle else 18   # type 2 reserves length nibble 0xF for RLE
    out = bytearray()
    chains = {}
    flags_pos = None
    bit = 8
    i = 0
    n = len(src)

    def emit(is_literal, payload):
        nonlocal flags_pos, bit
        if bit == 8:
            flags_pos = len(out)
            out.append(0)
            bit = 0
        if is_literal:
            out[flags_pos] |= 1 << bit
        out.extend(payload)
        bit += 1

    def insert(pos):
        if pos + 3 <= n:
            chains.setdefault(src[pos:pos + 3], []).append(pos)

    while i < n:
        # RLE run
        if rle:
            run = 1
            while i + run < n and src[i + run] == src[i] and run < 274:
                run += 1
            if run >= 4:
                if run <= 18:
                    emit(False, (src[i], 0xF0 | (run - 3)))
                else:
                    emit(False, (run - 19, 0xF0, src[i]))
                for k in range(run):
                    insert(i + k)
                i += run
                continue
        # LZ match
        best_len, best_dist = 0, 0
        for cand in reversed(chains.get(src[i:i + 3], ())[-48:]):
            dist = i - cand
            if dist > 0xFFF:
                break
            length = 3
            while length < max_len and i + length < n and src[cand + length] == src[i + length]:
                length += 1
            if length > best_len:
                best_len, best_dist = length, dist
                if length == max_len:
                    break
        if best_len >= 3:
            emit(False, (best_dist & 0xFF, (best_len - 3) << 4 | best_dist >> 8))
            for k in range(best_len):
                insert(i + k)
            i += best_len
        else:
            emit(True, (src[i],))
            insert(i)
            i += 1
    if not rle:
        emit(False, (0, 0))   # type 1 end-of-block token (the game stops on it)
    return bytes(out)


def compress(data, typ=2, template=None):
    """Compress to an SLZ stream. template: an original SLZ header (0x20 bytes)
    whose unknown fields are copied; otherwise the common single-chunk values."""
    hdr = bytearray(template[:HEADER_SIZE] if template else
                    b'SLZ\x02\x00\x01\x25\x00' + bytes(16) + b'\x00\x40\x01\x00' + bytes(4))
    hdr[3] = typ
    if typ == 0:
        payload = bytes(data)
    elif typ in (1, 2):
        payload = bytearray()
        for start in range(0, len(data), BLOCK_OUT):
            block = _compress_block(data[start:start + BLOCK_OUT], rle=typ == 2)
            if len(block) > 0xFFFF:
                payload += b'\0\0' + data[start:start + BLOCK_OUT]
            else:
                payload += struct.pack('<H', len(block)) + block
    else:
        raise ValueError(f'cannot compress SLZ type {typ}')
    struct.pack_into('<IIII', hdr, 8, len(payload), len(data), 0, HEADER_SIZE)
    return bytes(hdr) + bytes(payload)


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: slz.py <in.slz> <out.bin>')
    with open(sys.argv[1], 'rb') as f:
        data = f.read()
    with open(sys.argv[2], 'wb') as f:
        f.write(decompress(data))


if __name__ == '__main__':
    main()
