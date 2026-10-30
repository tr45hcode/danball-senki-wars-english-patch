#!/usr/bin/env python3
"""RMD message files (output of 'FontConverterDll_1.0.1.5') and their RMDT atlases.

RMD layout (offsets in the header are relative to 0x10):
  0x00  ' DMR', u32 file size, u32 0, u32 file size
  0x10  'FontConverterDll_1.0.1.5'
  0x30  u32 msg_table, text, glyph_table, end, end2, glyph_count,
            tex_size, tex_size2, cell_w, cell_h, cell_size, 0, 1,
            msg_count, tex_size3, hash, atlas_w, atlas_h, 1, 0
  msg_table:   msg_count x {u32 id, u32 text offset, f32 width, f32 height}
  glyph_table: glyph_count x {u8 w, u8 h, u16 0, f32 u0, v0, u1, v1}
               per-file glyphs first; the remaining 297 slots are empty
               placeholders for the global font.

Text is a byte stream:
  00                    end of message
  b0 b1 (b0, b1 & 0x80) control, id = (b0 & 0x7F) | (b1 & 0x7F) << 7
  b0 b1 (b0 & 0x80)     glyph, v = (b1 << 7) | (b0 & 0x7F)
                          1 <= v <= 297  global font glyph v - 1
                          v >= LOCAL_BASE per-file glyph v - LOCAL_BASE
Furigana: ctrl 0x10, reading bytes (hiragana = byte + 0x3040, 0x50 = ん),
          00, base glyphs, ctrl 0x11.
"""
import struct

LOCAL_BASE = 301

# global font (01000/007_RMD) glyph order; index = v - 1
GLOBAL_CHARS = (
    " %&'()*+,-./0123456789:=?"
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'
    '±―”…ⅠⅡⅢⅣⅤ♪　、。「」『』'
    'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ'
    + ''.join(chr(c) for c in range(0x3041, 0x3090)) + 'をん'
    + ''.join(chr(c) for c in range(0x30A1, 0x30F0)) + 'ヲンヴヵヶ'
    + '・ー！（）＜＞？［］～'
)
assert len(GLOBAL_CHARS) == 297, len(GLOBAL_CHARS)

# control id -> (name, fixed parameter byte count)
CONTROLS = {
    0x00: ('n', 0),       # newline
    0x01: ('c', 1),       # style/colour?
    0x02: ('x2', 0),
    0x03: ('x3', 2),
    0x04: ('x4', 0),
    0x06: ('p', 0),       # page break (wait for button)
    0x10: ('ruby', None),
    0x11: ('/ruby', 0),
    0x13: ('var', 1),     # insert variable (player name, ...)
    0x14: ('x14', 2),
}


CHAR_TO_V = {}
for _i, _ch in enumerate(GLOBAL_CHARS):
    CHAR_TO_V.setdefault(_ch, _i + 1)
CONTROL_BY_NAME = {name: cid for cid, (name, _) in CONTROLS.items()}


# Per-message height the converter stores in the message table:
# sum over lines ([n]/[p]-separated, minus the segment after the final [p])
# of (furigana line, plain line) heights. Fitted on the original data:
# 14 px 99.8%, 10 px 99.9%, 11 px 78% of messages.
LINE_HEIGHTS = {14: (22, 12), 11: (20, 10), 10: (19, 9)}


def layout_height(tokens, cell):
    ruby_h, plain_h = LINE_HEIGHTS.get(cell, (cell + 8, cell - 2))
    lines = [False]
    for tok in tokens:
        if tok[0] == 'ctl' and tok[1] == 0x10:
            lines[-1] = True
        elif tok[0] == 'ctl' and tok[1] in (0x00, 0x06):
            lines.append(False)
    lines.pop()
    return float(sum(ruby_h if ruby else plain_h for ruby in lines))


def decode_message(data):
    """Parse standalone encoded message bytes (as made by encode_tokens)."""
    holder = Rmd.__new__(Rmd)
    holder.data, holder.text_base = data, 0
    return list(holder.tokens(0))


def ruby_reading(raw):
    return ''.join('ん' if b == 0x50 else chr(0x3040 + b) for b in raw)


def encode_tokens(tokens):
    """Inverse of Rmd.tokens(): token list -> message bytes including the 00."""
    out = bytearray()
    for tok in tokens:
        if tok[0] == 'g':
            v = tok[1]
            out += bytes((0x80 | (v & 0x7F), v >> 7))
        else:
            _, cid, params = tok
            out += bytes((0x80 | (cid & 0x7F), 0x80 | (cid >> 7)))
            out += params
            if CONTROLS[cid][1] is None:
                out.append(0)
    out.append(0)
    return bytes(out)


def parse_markup(text):
    """Markup -> tokens. Supports global-font characters, [n], [p], [var:N]."""
    tokens = []
    i = 0
    while i < len(text):
        if text[i] == '[':
            end = text.index(']', i)
            name, _, arg = text[i + 1:end].partition(':')
            cid = CONTROL_BY_NAME[name]
            params = bytes.fromhex(arg) if CONTROLS[cid][1] and name != 'var' else \
                bytes((int(arg),)) if name == 'var' else b''
            tokens.append(('ctl', cid, params))
            i = end + 1
            continue
        if text[i] not in CHAR_TO_V:
            raise ValueError(f'{text[i]!r} is not in the global font')
        tokens.append(('g', CHAR_TO_V[text[i]]))
        i += 1
    return tokens


class Rmd:
    def __init__(self, data):
        if data[:4] != b' DMR':
            raise ValueError('not an RMD file')
        self.data = data
        f = struct.unpack_from('<20I', data, 0x30)
        self.fields = f
        self.msg_table = f[0] + 0x10
        self.text_base = f[1] + 0x10
        self.glyph_table = f[2] + 0x10
        self.glyph_count = f[5]
        self.cell = f[8]
        self.msg_count = f[13]
        self.atlas_w, self.atlas_h = f[16], f[17]

    def with_texts(self, texts):
        """Return new RMD bytes with message text replaced.

        texts: {message id: encoded bytes (from encode_tokens)}; messages not
        listed keep their original bytes. Replaced messages get their table
        width/height recomputed the way the converter does (width is a
        furigana value, 0 without furigana). If the text outgrows its region,
        the region grows in 0x80 steps and the glyph table moves (all offsets
        and both size fields are updated).
        """
        if not self.msg_count:
            return self.data
        d = bytearray(self.data)
        region = self.glyph_table - self.text_base
        blob = bytearray()
        msgs = list(enumerate(self.messages()))
        # keep the original storage order (not always table order)
        for n, (mid, off, _, _) in sorted(msgs, key=lambda m: m[1][1]):
            if mid in texts:
                msg = texts[mid]
                height = layout_height(decode_message(msg), self.cell)
                struct.pack_into('<ff', d, self.msg_table + n * 16 + 8, 0.0, height)
            else:
                list(self.tokens(off))
                msg = self.data[self.text_base + off:self.text_base + self.last_end]
            struct.pack_into('<I', d, self.msg_table + n * 16 + 4, len(blob))
            blob += msg
        new_region = region
        while new_region < len(blob):
            new_region += 0x80
        delta = new_region - region
        d[self.text_base:self.glyph_table] = blob + bytes(new_region - len(blob))
        if delta:
            for field in (2, 3, 4):              # glyph table, end, end
                struct.pack_into('<I', d, 0x30 + field * 4, self.fields[field] + delta)
            struct.pack_into('<I', d, 0x04, len(d))
            struct.pack_into('<I', d, 0x0C, len(d))
        return bytes(d)

    def messages(self):
        for i in range(self.msg_count):
            mid, off, w, h = struct.unpack_from('<IIff', self.data, self.msg_table + i * 16)
            yield mid, off, w, h

    def glyph_rect(self, index):
        """Pixel rect (x0, y0, x1, y1) and advance width of a per-file glyph."""
        o = self.glyph_table + index * 0x14
        w = self.data[o]
        u0, v0, u1, v1 = struct.unpack_from('<4f', self.data, o + 4)
        W, H = self.atlas_w, self.atlas_h
        return (round(u0 * W), round(v0 * H), round(u1 * W), round(v1 * H)), w

    def tokens(self, off):
        """Yield ('g', v) glyphs and ('ctl', id, params) controls; stops at 00."""
        d = self.data
        i = self.text_base + off
        while True:
            b0 = d[i]
            if b0 == 0:
                self.last_end = i + 1 - self.text_base
                return
            if not b0 & 0x80:
                raise ValueError(f'stray byte {b0:#x} at {i:#x}')
            b1 = d[i + 1]
            i += 2
            if not b1 & 0x80:
                yield ('g', (b1 << 7) | (b0 & 0x7F))
                continue
            cid = (b0 & 0x7F) | (b1 & 0x7F) << 7
            if cid not in CONTROLS:
                raise ValueError(f'unknown control {cid:#x} at {i - 2:#x}')
            n = CONTROLS[cid][1]
            if n is None:
                end = d.index(0, i)
                params = d[i:end]
                i = end + 1
            else:
                params = d[i:i + n]
                i += n
            yield ('ctl', cid, params)
