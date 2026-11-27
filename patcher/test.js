// node patcher/test.js <patch.dswp> <original.cpk> [rom.3ds]
// Checks the web patcher's core against the real files.
const fs = require('fs');
const crypto = require('crypto');
const DSW = require('./core.js');

(async () => {
  let ok = true;
  const check = (what, cond) => { console.log((cond ? 'ok   ' : 'FAIL ') + what); ok = ok && cond; };

  for (const n of [0, 1, 55, 56, 63, 64, 65, 119, 120, 1000, 100000]) {
    const data = crypto.randomBytes(n);
    const s = new DSW.Sha256();
    s.update(data.subarray(0, Math.floor(n / 3)));
    s.update(data.subarray(Math.floor(n / 3)));
    check(`sha256 of ${n} bytes`, s.hex() === crypto.createHash('sha256').update(data).digest('hex'));
  }

  const [patchPath, cpkPath, romPath] = process.argv.slice(2);
  const patch = await DSW.parsePatch(new Uint8Array(fs.readFileSync(patchPath)));
  console.log(`patch: ${patch.ops.length} operations, ${patch.lits.length} bytes added`);
  const src = await fs.openAsBlob(cpkPath);
  check('original size', src.size === patch.srcSize);
  let t = Date.now();
  check('original checksum', await DSW.hashBlob(src) === patch.srcHash);
  console.log(`  hashed in ${(Date.now() - t) / 1000}s`);
  const out = DSW.applyPatch(src, patch);
  check('patched size', out.size === patch.dstSize);
  t = Date.now();
  check('patched checksum', await DSW.hashBlob(out) === patch.dstHash);
  console.log(`  hashed in ${(Date.now() - t) / 1000}s`);

  const cpk = await DSW.locateCpk(src);
  check('a CPK is accepted as it is', cpk.size === src.size);

  if (romPath) {
    const rom = await fs.openAsBlob(romPath);
    const found = await DSW.locateCpk(rom);
    check('CPK found in the ROM', found.size === patch.srcSize);
    check('ROM CPK checksum', await DSW.hashBlob(found) === patch.srcHash);
  }
  try {
    await DSW.locateCpk(new Blob([new Uint8Array(1024)]));
    check('garbage is refused', false);
  } catch (e) {
    check('garbage is refused: ' + e.message, !!e.problem);
  }
  process.exit(ok ? 0 : 1);
})();
