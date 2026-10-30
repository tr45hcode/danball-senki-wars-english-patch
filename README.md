# Danball Senki Wars (3DS, CTR-P-BDNJ) English patch

Status, decisions and next steps: see [progress.md](progress.md).
Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).

## Pipeline

```sh
python3 tools/extract_3ds.py "Danball Senki Wars (Japan)/Danball Senki Wars (Japan) Decrypted.3ds" extracted
python3 tools/unpack_all.py extracted/romfs/DA3File_3ds.cpk extracted/cpk      # ~1 min, 1.8 GB
.venv/bin/python tools/dump_text.py extracted/cpk script/raw                    # ~2.5 min, needs numpy
```

`.venv` is a local virtualenv with `numpy` and `pillow` (`python3 -m venv .venv && .venv/bin/pip install numpy pillow`).

### Translating

```sh
python3 tools/make_template.py 01000_098_000203e8     # creates script/en/01000_098_000203e8.tsv
```

Fill in the `en` column; leave the Japanese column alone. Markup:
- `[n]` forces a line break. Long lines wrap automatically at 308 px, the widest Japanese dialogue line.
- `[var:0]` inserts the player name.
- The closing `[p]` is added automatically.
- `!`, `"`, `[` `]`, `<` `>` and `~` are not in the font's ASCII set. They're swapped for the nearest full-width glyph until custom glyphs are supported.

The system text exists twice, at 14 px (`01000_098`) and 10 px (`01000_100`, same ids). Translate `01000_098` only; the build copies it into the 10 px copy.

`build/mods/text_report.txt` lists overflowing lines and UI strings that are much wider than the Japanese.

- **Style and terms:** `script/glossary.tsv` covers character names, places and LBX terms.
  - Names are romanized Japanese (Hepburn, no macrons), given name first; name tags show given names only.
  - Honorifics are localized.
  - `[x14:0000]` inserts the player's country name.
- **Batches:** `tools/fill_translations.py batch.tsv` merges lines (`file<TAB>id<TAB>english`) into `script/en/` and reports anything that won't fit.
- **Helpers** (`tools/xlate.py`, see its docstring):
  - `show 52600 52601` lists untranslated lines with the furigana collapsed.
  - `check` and `batch out.tsv` read shorthand lines such as `52600:4 English` (or `52600.4:1 Tag` for name tags). `check` wraps them exactly like the build and prints each line's width; `batch` writes a file for `fill_translations.py`.
  - `reuse out.tsv 526` fills speaker tags from `script/speaker_names.tsv` and copies exact repeats of lines already translated. Review the printed repeats: a short reply like "Yes, sir." depends on who is being answered.

  ```sh
  python3 tools/xlate.py show 52610
  python3 tools/xlate.py check < lines.txt      # fix BAD lines, repeat
  python3 tools/xlate.py batch b.tsv < lines.txt && python3 tools/fill_translations.py b.tsv
  ```
- **Digits and other image-only glyphs** (`⟨日⟩`, `⟨Ｑ⟩`): `.venv/bin/python tools/glyphsheet.py out.png 52567` draws them so you can read them. Add the right character to `script/glyph_overrides.tsv` and re-dump. The guesses confuse 3/8/日 and 0/Ｑ.
- **Box sizes:** `tools/layout.py 52508` prints the Japanese width and line count of each message; `layout.py --scan` lists files that may use a one-line box.
- **Story order:** the 525xx containers are the story scenes in play order (52500 is the opening battle, 52502/52504/52506 are name, appearance and country entry, 52511 is the intro narration, 52512 is the opening lyrics). The 525xx scenes carry on past the prologue: 52513, on the ship, follows the lyrics. 539xx are mission events (tutorial pop-ups, map chatter), 11xxx holds character conversations, and 06xxx holds map examine text.

### Building

```sh
python3 tools/build_patch.py extracted/romfs/DA3File_3ds.cpk build/mods              # translations only
python3 tools/build_patch.py --test-ids extracted/romfs/DA3File_3ds.cpk build/mods   # untranslated → "11812:10" labels
python3 tools/build_patch.py --test-ids --ruler extracted/romfs/DA3File_3ds.cpk build/mods   # + text box ruler
# emulator-friendly ROM copy (partition 0 is decrypted but lacks the NoCrypto flag)
python3 tools/fix_nocrypto.py "Danball Senki Wars (Japan)/Danball Senki Wars (Japan) Decrypted.3ds" "build/Danball Senki Wars (Japan) [nocrypto].3ds"
```

`tools/boot_test.sh` boots the build in a private, windowless Azahar instance (software renderer) and reports whether it crashes. Run it after every build; it catches boot crashes without a manual test.

The output `build/mods/00040000000F4000/romfs/DA3File_3ds.cpk` is a LayeredFS replacement. In Citra or Azahar, right-click the game, choose *Open Mods Location*, and put the `romfs` folder there. On console it goes in `luma/titles/00040000000F4000/romfs/`.

Repacking keeps everything it doesn't change byte-identical. Containers are patched in place (later entries shift by multiples of 0x80). The CPK writer patches ITOC sizes and header totals and reproduces the original exactly when nothing is replaced.

## File formats

| Layer | Format | Tool | Status |
|---|---|---|---|
| `.3ds` | NCSD → NCCH → ExeFS + RomFS | `extract_3ds.py` | read |
| `romfs/DA3File_3ds.cpk` | CRI CPK, ID-only (ITOC), 11,858 files, uncompressed | `cpk.py` | read |
| CPK entries | `MRON3.00` containers of tagged entries | `mron.py` | read |
| MRON payloads | `SLZ` compression, types 0–3 (all 26,092 blobs verified) | `slz.py` | decompress |
| `RMD-` / `RMDT` | pre-rendered text: messages + per-file kanji atlas | `rmd.py` | read |
| `SCE-` | Lua 5.1 bytecode (game scripts) | | not yet |
| `*.l2` | Mobiclip MOFLEX video (FMVs) | | not yet |
| `*.awb`, `ACB-` | CRI ADX2 audio | | not needed |

Format details are in each tool's docstring.

### Text encoding (RMD)

- Global font (`01000/006_RMDT`, `007_RMD`): 297 glyphs, including **proportional half-width ASCII**.
- A glyph token is 2 bytes with bit 7 of the first byte set: `v = (b1 << 7) | (b0 & 0x7F)`.
  - `v` 1–297: global glyph `v-1` (see `GLOBAL_CHARS` in `rmd.py`)
  - `v` ≥ 301: per-file glyph from the paired RMDT atlas (kanji, and symbols such as ！)
- Controls are `b0 b1` with both high bits set. `0x00` is a newline, `0x06` a page break, `0x10`…`0x11` furigana, `0x13` a variable (e.g. player name).
- `00` ends a message. In the original data each message is exactly one page.
- The message table's height is 22 px per furigana line plus 12 px per plain line (14 px font). `with_texts` recomputes it the way the original converter did. The "width" field is a furigana value, 0 without furigana.
- SLZ types 1 and 3 end every block with an end token `00 00` (distance 0), and the game's decoder needs it. Without it, decoding runs past the block and corrupts the heap. This caused both boot-time black screens; see `slz.py`.

### In-game layout (measured)

- Dialogue box: 319 px per line and 2 lines. Beyond 319 px the game breaks mid-word; a third line is drawn below the box.
- Map chatter during missions (52508, 53900): a one-line strip at the bottom of the top screen, so a second line is off-screen. The Japanese reaches 364 px. Files using a box other than the dialogue box are listed in `textfit.BOXES`; for those the listed size is a hard limit. Everything else may use at least the Japanese width and line count.
- No extra letter spacing: advance widths come straight from the font table.
- `!`: the font only has a full-width `！` drawn as a slanted stroke. `fontpatch.py` redraws it as an ASCII-style `!` in all five global font copies (01000 and 01500). The file sizes don't change.

## Dump format (`script/raw`)

- `<container>_<index>_<entry>.tsv`: one `id<TAB>text` row per message.
- Markup: `{漢字|かんじ}` furigana, `[n]` newline, `[p]` page break, `[var:N]` variable.
- `⟨字⟩` is a kanji identified from its image alone (about 5% of kanji uses), so treat it with suspicion.
- `glyphs.tsv` lists every unique per-file glyph bitmap with its character, status and use count.

### Kanji identification

Kanji exist only as bitmaps in per-file atlases. `identify_kanji.py` names each unique bitmap; it needs `.venv` and the dictionaries in `data/`:
- `data/kanjidic/kanjidic2.xml.gz`: https://www.edrdg.org/kanjidic/kanjidic2.xml.gz
- `data/jmdict/JMdict_e.gz`: http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz

Both are EDRDG, CC BY-SA 4.0; attribute them if redistributed.

```sh
.venv/bin/python tools/identify_kanji.py extracted/cpk data/glyph_ids.tsv   # ~30 s
.venv/bin/python tools/eval_kanji.py data/glyph_ids.tsv                     # 80/81 on the hand-checked atlas
python3 tools/dump_text.py extracted/cpk script/raw
```

Evidence, strongest first:
1. Furigana compounds that are JMdict words (熟練/じゅくれん), including okurigana (逃|に + げる → 逃げる).
2. 10/11 px message files copied from their identical 14 px twins.
3. Furigana that matches KANJIDIC readings.
4. Image similarity to Noto Sans CJK.

Each bitmap gets one character per font size. Hand corrections go in `script/glyph_overrides.tsv` (`key<TAB>char`), which wins over everything.

## Status / next steps

1. **Kanji identification**: 98.8% on the hand-checked sample, and 95% of kanji uses are backed by readings, dictionary words or alignment. Remaining: image-only glyphs (`⟨⟩` in the dump) and true homophones (態勢/体勢), to be fixed by hand in `script/glyph_overrides.tsv`.
2. **Reinsertion: working in-game** (Azahar, 2026-10-29). The skip prompt and the first scene (`52501`) are translated, wrapping works, and `!` renders.
   - Open: whether a mid-message `[p]` gives a second page (`--ruler` tests it).
   - RMD text can grow. A build growing the boot-time system text by 170 KB boots fine (`tools/boot_test.sh`).
3. **Name entry**: the prompts (01000.98 messages 17608, 17609, 17611, 17633) are translated.
   - The game stores names as global-font glyph indices.
   - `code.bin` 0x24D324/0x24D338/0x24D35C convert glyph ↔ full-width UTF-16/Shift-JIS through 297-entry tables at 0x5E3862/0x5E3610. Full-width input maps back to the proportional ASCII glyphs.
   - The runtime char → glyph table is at 0x654DF0.
   - Still to confirm in-game: the `A/1` keyboard types readable English names.
4. Text that isn't in RMD: textures with baked-in Japanese (`IMAG`, `IMGR`, UI layouts, e.g. the 進む button and the 名前入力 title), FMV subtitles, the banner and icon.

## Credits and third-party data

The kanji in the script dump were identified with these dictionaries:

- **KANJIDIC2** and **JMdict**, the property of the [Electronic Dictionary Research and Development Group](https://www.edrdg.org/) (EDRDG), used in conformance with the Group's [licence](https://www.edrdg.org/edrdg/licence.html) (Creative Commons Attribution-ShareAlike 4.0).

These files are research tools only. The patch contains no dictionary data, so distributing the patch carries no licence obligations from them. If you share the dictionary files themselves (anything in `data/`), keep this attribution and the CC BY-SA 4.0 licence with them. The simplest approach is to leave `data/` out of any public repository and let collaborators download the files from the links in [Kanji identification](#kanji-identification).

Image matching also uses **Noto Sans CJK JP** (SIL Open Font License), read from the system font directory. It isn't copied into this project or the patch.
