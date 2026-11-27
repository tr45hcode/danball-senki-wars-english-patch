// Core of the web patcher: no DOM here, so Node can test it too.
//
//   DSW.locateCpk(blob)        find DA3File_3ds.cpk in a game dump (or accept the CPK itself)
//   DSW.parsePatch(bytes)      read a .dswp patch (see tools/make_patch.py)
//   DSW.hashBlob(blob, cb)     SHA-256 of a Blob, in slices
//   DSW.applyPatch(src, patch) -> Blob made of slices of `src` and the patch's own bytes,
//                              so a 1.1 GB file never has to sit in memory
var DSW = (function () {
  'use strict';

  var K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ]);

  function Sha256() {
    this.h = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                              0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    this.w = new Uint32Array(64);
    this.tail = new Uint8Array(64);
    this.tailLen = 0;
    this.total = 0;
  }

  Sha256.prototype.block = function (d, o) {
    var h = this.h, w = this.w, i;
    for (i = 0; i < 16; i++, o += 4) {
      w[i] = (d[o] << 24) | (d[o + 1] << 16) | (d[o + 2] << 8) | d[o + 3];
    }
    for (i = 16; i < 64; i++) {
      var x = w[i - 15], y = w[i - 2];
      var s0 = ((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3);
      var s1 = ((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
    }
    var a = h[0], b = h[1], c = h[2], dd = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (i = 0; i < 64; i++) {
      var S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      var t1 = (hh + S1 + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
      var S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      var t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      hh = g; g = f; f = e; e = (dd + t1) | 0;
      dd = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += dd; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
  };

  Sha256.prototype.update = function (data) {
    var pos = 0, n = data.length;
    this.total += n;
    if (this.tailLen) {
      var take = Math.min(64 - this.tailLen, n);
      this.tail.set(data.subarray(0, take), this.tailLen);
      this.tailLen += take;
      pos = take;
      if (this.tailLen < 64) return;
      this.block(this.tail, 0);
      this.tailLen = 0;
    }
    for (; pos + 64 <= n; pos += 64) this.block(data, pos);
    if (pos < n) {
      this.tail.set(data.subarray(pos), 0);
      this.tailLen = n - pos;
    }
  };

  Sha256.prototype.hex = function () {
    var bits = this.total * 8, pad = new Uint8Array(((this.tailLen < 56 ? 56 : 120) - this.tailLen) + 8);
    pad[0] = 0x80;
    var hi = Math.floor(bits / 4294967296), lo = bits >>> 0, n = pad.length;
    pad[n - 8] = hi >>> 24; pad[n - 7] = hi >>> 16; pad[n - 6] = hi >>> 8; pad[n - 5] = hi;
    pad[n - 4] = lo >>> 24; pad[n - 3] = lo >>> 16; pad[n - 2] = lo >>> 8; pad[n - 1] = lo;
    var total = this.total;
    this.update(pad);
    this.total = total;
    var out = '';
    for (var i = 0; i < 8; i++) out += ('00000000' + (this.h[i] >>> 0).toString(16)).slice(-8);
    return out;
  };

  var SLICE = 8 * 1024 * 1024;

  async function readBytes(blob, off, len) {
    return new Uint8Array(await blob.slice(off, off + len).arrayBuffer());
  }

  // SHA-256 of a whole Blob, read in slices; progress(done, total) is optional
  async function hashBlob(blob, progress) {
    var sha = new Sha256();
    for (var off = 0; off < blob.size; off += SLICE) {
      sha.update(await readBytes(blob, off, SLICE));
      if (progress) progress(Math.min(off + SLICE, blob.size), blob.size);
    }
    return sha.hex();
  }

  // ---- the patch ----

  function u32(d, o) { return (d[o] | (d[o + 1] << 8) | (d[o + 2] << 16) | (d[o + 3] << 24)) >>> 0; }
  function u64(d, o) { return u32(d, o) + u32(d, o + 4) * 4294967296; }
  function ascii(d, o, n) { return String.fromCharCode.apply(null, d.subarray(o, o + n)); }
  function hex(d, o, n) {
    var s = '';
    for (var i = 0; i < n; i++) s += ('0' + d[o + i].toString(16)).slice(-2);
    return s;
  }

  async function inflateRaw(bytes) {
    var stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  async function parsePatch(bytes) {
    if (ascii(bytes, 0, 8) !== 'DSWPAT01') throw new Error('This is not a patch file.');
    var info = {
      srcSize: u64(bytes, 8), srcHash: hex(bytes, 16, 32),
      dstSize: u64(bytes, 48), dstHash: hex(bytes, 56, 32)
    };
    var rawLen = u32(bytes, 88);
    var body = await inflateRaw(bytes.subarray(92));
    if (body.length !== rawLen) throw new Error('The patch is damaged.');
    var pos = 0;
    function varint() {
      var n = 0, mul = 1, b;
      do {
        b = body[pos++];
        n += (b & 0x7f) * mul;
        mul *= 128;
      } while (b & 0x80);
      return n;
    }
    var count = varint(), ops = [];
    for (var i = 0; i < count; i++) {
      var kind = varint();
      if (kind === 0) {
        var off = varint();
        ops.push({ copy: true, off: off, len: varint() });
      } else {
        ops.push({ copy: false, len: varint() });
      }
    }
    info.ops = ops;
    info.lits = body.subarray(pos);
    return info;
  }

  // Blob of the patched file: slices of the player's file and slices of the patch's own bytes
  function applyPatch(src, patch) {
    var parts = [], lit = 0, size = 0;
    patch.ops.forEach(function (op) {
      if (op.copy) {
        parts.push(src.slice(op.off, op.off + op.len));
      } else {
        parts.push(patch.lits.slice(lit, lit + op.len));
        lit += op.len;
      }
      size += op.len;
    });
    if (size !== patch.dstSize) throw new Error('The patch is damaged.');
    return new Blob(parts, { type: 'application/octet-stream' });
  }

  // ---- finding the CPK in a game dump ----

  var CPK_NAME = 'DA3File_3ds.cpk';

  function Problem(message) { var e = new Error(message); e.problem = true; return e; }

  var ENCRYPTED = 'This game file is encrypted. Use a decrypted dump (for Azahar or Citra that is ' +
    'the usual kind), or extract DA3File_3ds.cpk from your game with GodMode9 and choose that.';

  function utf16(d, o, n) {
    var s = '';
    for (var i = 0; i < n; i += 2) s += String.fromCharCode(d[o + i] | (d[o + i + 1] << 8));
    return s;
  }

  async function cpkFromNcch(blob, base) {
    var ncch = await readBytes(blob, base, 0x200);
    if (ascii(ncch, 0x100, 4) !== 'NCCH') throw Problem(ENCRYPTED);
    var romfs = base + u32(ncch, 0x1B0) * 0x200;
    var ivfc = await readBytes(blob, romfs, 0x60);
    if (ascii(ivfc, 0, 4) !== 'IVFC') throw Problem(ENCRYPTED);
    var align = Math.pow(2, u32(ivfc, 0x4C));
    var l3 = romfs + Math.ceil((0x60 + u32(ivfc, 8)) / align) * align;
    var hd = await readBytes(blob, l3, 0x28), h = [];
    for (var i = 0; i < 10; i++) h.push(u32(hd, i * 4));
    if (h[0] !== 0x28) throw Problem('This does not look like a 3DS game file.');
    var dirs = await readBytes(blob, l3 + h[3], h[4]);
    var files = await readBytes(blob, l3 + h[7], h[8]);
    var stack = [0];
    while (stack.length) {
      var doff = stack.pop();
      var foff = u32(dirs, doff + 12);
      while (foff !== 0xFFFFFFFF) {
        var nameLen = u32(files, foff + 28);
        if (utf16(files, foff + 0x20, nameLen) === CPK_NAME) {
          var at = l3 + h[9] + u64(files, foff + 8);
          return blob.slice(at, at + u64(files, foff + 16));
        }
        foff = u32(files, foff + 4);
      }
      var coff = u32(dirs, doff + 8);
      while (coff !== 0xFFFFFFFF) {
        stack.push(coff);
        coff = u32(dirs, coff + 4);
      }
    }
    throw Problem('This is a 3DS game, but not Danball Senki Wars: ' + CPK_NAME + ' is not in it.');
  }

  // Accepts the CPK itself, a decrypted .3ds/.cci (NCSD), a .cxi (NCCH) or a decrypted .cia
  async function locateCpk(blob) {
    var head = await readBytes(blob, 0, 0x200);
    if (ascii(head, 0, 4) === 'CPK ') return blob;
    if (ascii(head, 0x100, 4) === 'NCSD') return cpkFromNcch(blob, u32(head, 0x120) * 0x200);
    if (ascii(head, 0x100, 4) === 'NCCH') return cpkFromNcch(blob, 0);
    if (u32(head, 0) === 0x2020) {
      var up = function (n) { return Math.ceil(n / 64) * 64; };
      var at = up(0x2020) + up(u32(head, 8)) + up(u32(head, 12)) + up(u32(head, 16)) + up(u32(head, 20));
      return cpkFromNcch(blob, at);
    }
    throw Problem('This is not a 3DS game file. Choose a .3ds, .cci, .cxi or .cia, or ' + CPK_NAME + '.');
  }

  return {
    Sha256: Sha256, hashBlob: hashBlob, parsePatch: parsePatch, applyPatch: applyPatch,
    locateCpk: locateCpk, readBytes: readBytes, CPK_NAME: CPK_NAME, SLICE: SLICE
  };
})();

if (typeof module !== 'undefined') module.exports = DSW;
