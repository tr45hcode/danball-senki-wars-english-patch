#!/usr/bin/env python3
"""MRON container (Aska3DS engine).

Header (0x20 bytes):
  0x00  'MRON3.00'
  0x08  u32   entry count (including the trailing SEEK entry)
Entries (0x20 bytes each, from 0x20):
  0x00  char[4]  tag, stored reversed ('GAMI' = IMAG, '-DTA' = ATD-)
  0x04  u32      id
  0x08  u32      size (decompressed size for SLZ entries)
  0x0C  u32      offset from the start of the container
  0x10  u8[16]   zero
The last entry is SEEK, pointing at an empty 'MRON3.00' header at the end.
"""
import struct

import slz

MAGIC = b'MRON3.00'


def parse(data):
    """Return a list of dicts: tag, id, size, offset, compressed."""
    if data[:8] != MAGIC:
        raise ValueError('not an MRON container')
    count = struct.unpack_from('<I', data, 8)[0]
    entries = []
    for i in range(count):
        tag, eid, size, off = struct.unpack_from('<4sIII', data, 0x20 + i * 0x20)
        entries.append({
            'tag': tag[::-1].decode('latin1'),
            'id': eid,
            'size': size,
            'offset': off,
            'compressed': data[off:off + 3] == b'SLZ',
        })
    return entries


def read_entry(data, entry):
    """Return the entry's payload, decompressed if needed."""
    if entry['compressed']:
        return slz.decompress(data, entry['offset'])
    return data[entry['offset']:entry['offset'] + entry['size']]


SHIFT_ALIGN = 0x80  # largest alignment seen between entries


def replace_entries(data, new_payloads):
    """Return a copy of the container with some entries' payloads replaced.

    new_payloads: {entry index: decompressed bytes}. Compressed entries are
    recompressed with the same SLZ type and header template. Everything else
    (padding, unknown tail bytes) is kept; later entries move by multiples of
    SHIFT_ALIGN so their alignment is unchanged.
    """
    entries = parse(data)
    order = sorted(range(len(entries)), key=lambda i: entries[i]['offset'])
    out = bytearray(data)
    shift = 0
    for pos, i in enumerate(order):
        ent = entries[i]
        new_off = ent['offset'] + shift
        struct.pack_into('<I', out, 0x20 + i * 0x20 + 0xC, new_off)
        if i not in new_payloads:
            continue
        payload = new_payloads[i]
        start = ent['offset'] + shift
        end = (entries[order[pos + 1]]['offset'] if pos + 1 < len(order) else len(data)) + shift
        if ent['compressed']:
            template = data[ent['offset']:ent['offset'] + slz.HEADER_SIZE]
            typ = template[3] if template[3] in (0, 1, 2) else 2   # no type 3 encoder
            blob = slz.compress(payload, typ, template)
        else:
            blob = payload
        old_len = end - start
        new_len = old_len
        while new_len < len(blob):
            new_len += SHIFT_ALIGN
        while new_len - SHIFT_ALIGN >= len(blob):
            new_len -= SHIFT_ALIGN
        out[start:end] = blob + bytes(new_len - len(blob))
        struct.pack_into('<I', out, 0x20 + i * 0x20 + 0x8, len(payload))
        shift += new_len - old_len
    return bytes(out)
