#!/usr/bin/env python3
"""CRI CPK archive reader.

Usage:
  cpk.py info <file.cpk>               print header and TOC summary
  cpk.py list <file.cpk>               list files
  cpk.py extract <file.cpk> <out_dir>  extract (and CRILAYLA-decompress) all files
"""
import os
import struct
import sys

# --- @UTF tables -----------------------------------------------------------

UTF_MASK_SEED, UTF_MASK_MUL = 0x655F, 0x4115


def utf_unmask(data):
    out = bytearray(len(data))
    m = UTF_MASK_SEED
    for i, b in enumerate(data):
        out[i] = b ^ (m & 0xFF)
        m = (m * UTF_MASK_MUL) & 0xFFFF
    return bytes(out)


# type code -> (struct fmt, size)
_TYPES = {
    0x0: ('>B', 1), 0x1: ('>b', 1), 0x2: ('>H', 2), 0x3: ('>h', 2),
    0x4: ('>I', 4), 0x5: ('>i', 4), 0x6: ('>Q', 8), 0x7: ('>q', 8),
    0x8: ('>f', 4), 0x9: ('>d', 8),
}
STORAGE_ZERO, STORAGE_CONST, STORAGE_ROW = 0x10, 0x30, 0x50


def parse_utf(buf):
    """Parse an (unmasked) @UTF table. Returns (table_name, columns, rows)."""
    if buf[:4] != b'@UTF':
        buf = utf_unmask(buf)
        if buf[:4] != b'@UTF':
            raise ValueError('not a @UTF table')
    _, rows_off, str_off, data_off, name_off, ncols, row_len, nrows = \
        struct.unpack_from('>IIIIIHHI', buf, 4)
    rows_off += 8
    str_off += 8
    data_off += 8

    def string(off):
        s = str_off + off
        return buf[s:buf.index(b'\0', s)].decode('shift_jis')

    def read_value(typ, pos):
        if typ == 0xA:
            return string(struct.unpack_from('>I', buf, pos)[0]), 4
        if typ == 0xB:
            off, size = struct.unpack_from('>II', buf, pos)
            return buf[data_off + off:data_off + off + size], 8
        fmt, size = _TYPES[typ]
        return struct.unpack_from(fmt, buf, pos)[0], size

    columns = []
    pos = 0x20
    for _ in range(ncols):
        flags = buf[pos]
        name = string(struct.unpack_from('>I', buf, pos + 1)[0])
        pos += 5
        storage, typ = flags & 0xF0, flags & 0x0F
        const = None
        if storage == STORAGE_CONST:
            const, size = read_value(typ, pos)
            pos += size
        columns.append((name, storage, typ, const))

    rows = []
    for r in range(nrows):
        pos = rows_off + r * row_len
        row = {}
        for name, storage, typ, const in columns:
            if storage == STORAGE_ROW:
                row[name], size = read_value(typ, pos)
                pos += size
            elif storage == STORAGE_CONST:
                row[name] = const
            else:
                row[name] = None
        rows.append(row)
    return string(name_off), columns, rows


def utf_locate(buf):
    """Byte positions inside an unmasked @UTF table.

    Returns (rows_off, row_len, data_off, {column: (offset within row, type)})
    for the per-row columns, so fields can be patched in place.
    """
    _, rows_off, str_off, data_off, _, ncols, row_len, _ = \
        struct.unpack_from('>IIIIIHHI', buf, 4)
    cols = {}
    pos, row_pos = 0x20, 0
    for _ in range(ncols):
        flags = buf[pos]
        name_off = struct.unpack_from('>I', buf, pos + 1)[0]
        s = str_off + 8 + name_off
        name = buf[s:buf.index(b'\0', s)].decode('shift_jis')
        pos += 5
        storage, typ = flags & 0xF0, flags & 0x0F
        size = 4 if typ == 0xA else 8 if typ == 0xB else _TYPES[typ][1]
        if storage == STORAGE_CONST:
            pos += size
        elif storage == STORAGE_ROW:
            cols[name] = (row_pos, typ)
            row_pos += size
    return rows_off + 8, row_len, data_off + 8, cols


def utf_set(buf, row, column, value):
    """Overwrite a numeric per-row field of an unmasked @UTF table (bytearray)."""
    rows_off, row_len, _, cols = utf_locate(buf)
    off, typ = cols[column]
    fmt = _TYPES[typ][0]
    struct.pack_into(fmt, buf, rows_off + row * row_len + off, value)


def utf_pack_rows(columns, rows):
    """Pack parse_utf rows back into bytes, one per row."""
    per_row = [(name, typ) for name, storage, typ, _ in columns if storage == STORAGE_ROW]
    fmt = '>' + ''.join(_TYPES[typ][0][1] for _, typ in per_row)
    return [struct.pack(fmt, *(row[name] for name, _ in per_row)) for row in rows]


def utf_with_rows(buf, rows):
    """Copy of an unmasked @UTF table with its rows replaced (packed bytes).

    Only for tables of numeric columns with no data region, such as the
    ITOC's DataL and DataH. The table is padded to 8 bytes, as CRI's are.
    """
    _, rows_off, str_off, data_off, name_off, ncols, row_len, _ = \
        struct.unpack_from('>IIIIIHHI', buf, 4)
    if data_off + 8 != len(buf) or any(len(r) != row_len for r in rows):
        raise ValueError('table has a data region or the rows do not fit it')
    strings = bytes(buf[str_off + 8:data_off + 8]).rstrip(b'\0') + b'\0'
    out = bytearray(buf[:rows_off + 8]) + b''.join(rows) + strings
    out += b'\0' * (-len(out) % 8)
    struct.pack_into('>IIIIIHHI', out, 4, len(out) - 8, rows_off,
                     rows_off + row_len * len(rows), len(out) - 8,
                     name_off, ncols, row_len, len(rows))
    return out


def read_chunk(f, off, magic):
    """Read a CPK chunk ('CPK ', 'TOC ', ...) and return its parsed @UTF table."""
    f.seek(off)
    hdr = f.read(0x10)
    if hdr[:4] != magic:
        raise ValueError(f'expected {magic!r} at {off:#x}, got {hdr[:4]!r}')
    size = struct.unpack_from('<Q', hdr, 8)[0]
    return parse_utf(f.read(size))


# --- CRILAYLA ---------------------------------------------------------------

def crilayla_decompress(src):
    if src[:8] != b'CRILAYLA':
        raise ValueError('not CRILAYLA')
    uncomp_size, hdr_off = struct.unpack_from('<II', src, 8)
    prefix = src[0x10 + hdr_off:0x10 + hdr_off + 0x100]
    out = bytearray(uncomp_size)

    bits = int.from_bytes(src[0x10:0x10 + hdr_off], 'little')
    nbits = hdr_off * 8

    def take(n):
        nonlocal nbits
        nbits -= n
        return (bits >> nbits) & ((1 << n) - 1)

    # Bits are consumed from the end of the stream, most significant first.
    pos = uncomp_size - 1
    while pos >= 0:
        if take(1):
            back = take(13) + 3
            length = 3
            for lvl_bits in (2, 3, 5, 8):
                v = take(lvl_bits)
                length += v
                if v != (1 << lvl_bits) - 1:
                    break
            else:
                while True:
                    v = take(8)
                    length += v
                    if v != 0xFF:
                        break
            for _ in range(length):
                out[pos] = out[pos + back]
                pos -= 1
        else:
            out[pos] = take(8)
            pos -= 1
    return prefix + bytes(out)


# --- archive ----------------------------------------------------------------

class Cpk:
    DATAL_MAX = 0xFFFF   # largest file size the ITOC's DataL table can hold

    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        _, _, rows = read_chunk(self.f, 0, b'CPK ')
        self.header = rows[0]
        self.files = []
        toc_off = self.header.get('TocOffset')
        if toc_off:
            _, _, toc = read_chunk(self.f, toc_off, b'TOC ')
            content_off = self.header.get('ContentOffset') or toc_off
            base = min(toc_off, content_off)
            for row in toc:
                d = row.get('DirName') or ''
                name = f"{d}/{row['FileName']}" if d else row['FileName']
                self.files.append({
                    'name': name,
                    'offset': base + row['FileOffset'],
                    'size': row['FileSize'],
                    'extract_size': row['ExtractSize'],
                    'id': row.get('ID'),
                })
        elif self.header.get('ItocOffset'):
            self._read_itoc()

    def _read_itoc(self):
        """ID-only archive: files are stored in ID order from ContentOffset, each aligned."""
        _, _, rows = read_chunk(self.f, self.header['ItocOffset'], b'ITOC')
        entries = {}
        for key in ('DataL', 'DataH'):
            blob = rows[0].get(key)
            if blob:
                for row in parse_utf(blob)[2]:
                    entries[row['ID']] = (row['FileSize'], row['ExtractSize'])
        align = self.header.get('Align') or 1
        off = self.header['ContentOffset']
        for fid in sorted(entries):
            size, extract_size = entries[fid]
            self.files.append({
                'name': f'{fid:05d}',
                'offset': off,
                'size': size,
                'extract_size': extract_size,
                'id': fid,
            })
            off = (off + size + align - 1) // align * align

    def read(self, entry):
        self.f.seek(entry['offset'])
        data = self.f.read(entry['size'])
        if data[:8] == b'CRILAYLA':
            data = crilayla_decompress(data)
        return data

    def _chunk_table(self, off):
        """Return (chunk header, unmasked table bytearray, was_masked)."""
        self.f.seek(off)
        hdr = self.f.read(0x10)
        raw = self.f.read(struct.unpack_from('<Q', hdr, 8)[0])
        masked = raw[:4] != b'@UTF'
        return hdr, bytearray(utf_unmask(raw) if masked else raw), masked

    def write_itoc(self, dst, replacements):
        """Write a copy of this ID-only archive with some files replaced.

        replacements: {file id: bytes}. Stored uncompressed; offsets of later
        files shift, so the ITOC sizes and header totals are written again.
        """
        if self.header.get('TocOffset') or not self.header.get('ItocOffset'):
            raise NotImplementedError('only ITOC (ID-only) archives are supported')
        align = self.header['Align']
        content_off = self.header['ContentOffset']
        sizes = {e['id']: e['size'] for e in self.files}
        for fid, data in replacements.items():
            sizes[fid] = len(data)

        # ITOC: new FileSize/ExtractSize in the nested DataL/DataH tables.
        # DataL stores sizes in 16 bits, so a file that outgrows it moves
        # to DataH and both tables are written again.
        itoc_off = self.header['ItocOffset']
        itoc_hdr, itoc, itoc_masked = self._chunk_table(itoc_off)
        rows_off, _, data_off, cols = utf_locate(itoc)
        tables = {}
        for key in ('DataL', 'DataH'):
            boff, bsize = struct.unpack_from('>II', itoc, rows_off + cols[key][0])
            blob = bytes(itoc[data_off + boff:data_off + boff + bsize])
            _, columns, rows = parse_utf(blob)
            for row in rows:
                if row['ID'] in replacements:
                    row['FileSize'] = row['ExtractSize'] = sizes[row['ID']]
            tables[key] = (blob, columns, rows)
        low, high = tables['DataL'][2], tables['DataH'][2]
        grown = [r for r in low if r['FileSize'] > self.DATAL_MAX]
        if grown:
            ids = {r['ID'] for r in grown}
            low[:] = [r for r in low if r['ID'] not in ids]
            high[:] = sorted(high + grown, key=lambda r: r['ID'])
        packed = [utf_with_rows(blob, utf_pack_rows(columns, rows))
                  for blob, columns, rows in (tables['DataL'], tables['DataH'])]
        old_len = len(itoc)
        itoc = itoc[:data_off] + packed[0] + packed[1]
        struct.pack_into('>I', itoc, 4, len(itoc) - 8)
        utf_set(itoc, 0, 'FilesL', len(low))
        utf_set(itoc, 0, 'FilesH', len(high))
        struct.pack_into('>II', itoc, rows_off + cols['DataL'][0], 0, len(packed[0]))
        struct.pack_into('>II', itoc, rows_off + cols['DataH'][0],
                         len(packed[0]), len(packed[1]))
        if itoc_off + 0x10 + len(itoc) > content_off:
            raise ValueError(f'ITOC grew past the file data ({len(grown)} files '
                             'moved to DataH)')

        # header totals
        hdr_hdr, header, hdr_masked = self._chunk_table(0)
        total = sum(sizes.values())
        pos = content_off
        ids = sorted(sizes)
        for fid in ids[:-1]:
            pos = (pos + sizes[fid] + align - 1) // align * align
        end = pos + sizes[ids[-1]]
        utf_set(header, 0, 'ContentSize', (end - content_off + align - 1) // align * align)
        utf_set(header, 0, 'EnabledPackedSize', total)
        utf_set(header, 0, 'EnabledDataSize', total)
        utf_set(header, 0, 'ItocSize', 0x10 + len(itoc))

        def remask(t, masked):
            return utf_unmask(bytes(t)) if masked else bytes(t)

        self.f.seek(0)
        prefix = bytearray(self.f.read(content_off))
        prefix[0x10:0x10 + len(header)] = remask(header, hdr_masked)
        struct.pack_into('<Q', prefix, itoc_off + 8, len(itoc))
        end = itoc_off + 0x10 + max(old_len, len(itoc))
        prefix[itoc_off + 0x10:end] = remask(itoc, itoc_masked).ljust(end - itoc_off - 0x10, b'\0')

        by_id = {e['id']: e for e in self.files}
        with open(dst, 'wb') as out:
            out.write(prefix)
            for n, fid in enumerate(ids):
                if fid in replacements:
                    out.write(replacements[fid])
                else:
                    self.f.seek(by_id[fid]['offset'])
                    remaining = by_id[fid]['size']
                    while remaining:
                        buf = self.f.read(min(remaining, 1 << 22))
                        out.write(buf)
                        remaining -= len(buf)
                if n != len(ids) - 1:
                    out.write(b'\0' * (-out.tell() % align))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    cpk = Cpk(path)
    if cmd == 'info':
        for k, v in cpk.header.items():
            if v is not None:
                print(f'{k:20} {v:#x}' if isinstance(v, int) else f'{k:20} {v!r}')
        print('files:', len(cpk.files))
        print('compressed:', sum(e['size'] != e['extract_size'] for e in cpk.files))
    elif cmd == 'list':
        for e in cpk.files:
            print(f"{e['offset']:#012x} {e['size']:>10} {e['extract_size']:>10}  {e['name']}")
    elif cmd == 'extract':
        out = sys.argv[3]
        for i, e in enumerate(cpk.files):
            dst = os.path.join(out, e['name'])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as o:
                o.write(cpk.read(e))
            if i % 500 == 0:
                print(f'{i}/{len(cpk.files)} {e["name"]}', flush=True)
        print('done')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
