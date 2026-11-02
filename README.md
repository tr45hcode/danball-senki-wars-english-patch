# Danball Senki Wars (3DS, CTR-P-BDNJ) English patch

A fan translation of Level-5's Danball Senki Wars, plus the tools that pull the game's text apart and put it back together. The main story, the character conversations, the map examine text, the menus and the LBX data are translated, which is about 95% of the game's text. What's left is placeholders, debug lines and a few short pieces the game joins together while you play. To play it, get the patch from [Releases](https://github.com/tr45hcode/danball-senki-wars-english-patch/releases); the README.txt in the zip explains how to apply it. [progress.md](progress.md) tracks what's done, what we decided and what's next. If you'd like to help, read [CONTRIBUTING.md](CONTRIBUTING.md).

No game files live in this repo. You need your own dump of the Japanese cartridge.

## Getting the text out

```sh
python3 tools/extract_3ds.py "Danball Senki Wars (Japan)/Danball Senki Wars (Japan) Decrypted.3ds" extracted
python3 tools/unpack_all.py extracted/romfs/DA3File_3ds.cpk extracted/cpk      # ~1 min, 1.8 GB
.venv/bin/python tools/dump_text.py extracted/cpk script/raw                    # ~2.5 min, needs numpy
```

`.venv` is a plain virtualenv with numpy and pillow: `python3 -m venv .venv && .venv/bin/pip install numpy pillow`. You only have to re-dump after correcting a misread glyph, since `script/raw/` is already committed.

## Translating

Each message lives in a `script/en/<file>.tsv` row: you fill in the `en` column and leave the Japanese reference column alone. `python3 tools/make_template.py 01000_098_000203e8` creates an empty file if one doesn't exist yet, though `fill_translations.py` does that for you too.

Most of the work goes through `tools/xlate.py`:

```sh
python3 tools/xlate.py show 52610
python3 tools/xlate.py check < lines.txt      # fix BAD lines, repeat
python3 tools/xlate.py batch b.tsv < lines.txt && python3 tools/fill_translations.py b.tsv
```

`show` lists untranslated lines with the furigana collapsed. `check` and `batch` read shorthand like `52600:4 English` (or `52600.4:1 Tag` for a name tag file); `check` wraps each line exactly the way the build will and prints its width in pixels, and `batch` turns the lines into a file `fill_translations.py` can merge. There's also `reuse out.tsv 526`, which fills speaker tags from `script/speaker_names.tsv` and copies exact repeats of lines that are already translated. Read what it copies before merging, because a short reply like "Yes, sir." only fits when the person being answered is someone you'd call sir.

Markup you'll meet:

| Markup | Meaning |
|---|---|
| `[n]` | line break; long lines also wrap on their own at 319 px |
| `[var:0]` | the player's name |
| `[x14:0000]` | the player's country name |
| `[p]` | page break; the build adds the closing one, so leave it out |

The font has no `!`, `"`, `[`, `]`, `<`, `>` or `~` in its ASCII set. `!` got redrawn into the font, and the rest get swapped for the nearest full-width glyph.

The system text exists twice, at 14 px (`01000_098`) and 10 px (`01000_100`) with the same ids. Translate `01000_098` only; the build copies those lines into the 10 px bank.

Names, places and LBX terms are in `script/glossary.tsv`. In short: romanized Japanese names (Hepburn, no macrons, given name first), speaker tags with given names only, and honorifics turned into plain English.

A few tools help with the awkward cases. Image-only glyphs show up as `⟨日⟩` or `⟨Ｑ⟩`, and the digit guesses mix up 3, 8 and 日, or 0 and Ｑ; `.venv/bin/python tools/glyphsheet.py out.png 52567` draws them so you can read the real character, which then goes in `script/glyph_overrides.tsv` before a re-dump. `tools/layout.py 52508` prints the width and line count of each original message, and `layout.py --scan` lists files that might use a one-line box. Run `tools/sizecheck.py` after changing names or labels: it flags any string bigger than the largest original of its kind, and it should print nothing.

Story order: the 525xx containers are the story scenes in play order. 52500 is the opening battle, 52502/52504/52506 are name, appearance and country entry, 52511 is the intro narration and 52512 the opening song; the ship scene in 52513 picks up straight after. Mission events (tutorial pop-ups, map chatter) are in 539xx, character conversations in 11xxx, and things you examine on the map in 06xxx.

## Building

```sh
python3 tools/build_patch.py extracted/romfs/DA3File_3ds.cpk build/mods              # translations only
python3 tools/build_patch.py --test-ids extracted/romfs/DA3File_3ds.cpk build/mods   # untranslated text shows as "11812:10" labels
python3 tools/build_patch.py --test-ids --ruler extracted/romfs/DA3File_3ds.cpk build/mods   # adds a text box ruler
# emulator-friendly ROM copy: partition 0 is decrypted but lacks the NoCrypto flag
python3 tools/fix_nocrypto.py "Danball Senki Wars (Japan)/Danball Senki Wars (Japan) Decrypted.3ds" "build/Danball Senki Wars (Japan) [nocrypto].3ds"
```

After every build, run `tools/boot_test.sh`. It boots the patched game in a private, windowless Azahar (software renderer) for 30 seconds and tells you whether it crashed. It was written to bisect the two early boot-time black screens, and it can't see anything past the first half minute.

The output, `build/mods/00040000000F4000/romfs/DA3File_3ds.cpk`, is a LayeredFS replacement. In Azahar or Citra, right-click the game, pick *Open Mods Location*, and drop the `romfs` folder there; on a 3DS with Luma it goes in `luma/titles/00040000000F4000/romfs/`. Don't load an emulator save state made with a different build, because the game crashes when its memory doesn't match the files. In-game saves are fine.

`build/mods/text_report.txt` lists lines that overflow and UI strings much wider than their Japanese.

Repacking leaves everything it doesn't touch byte-identical. Containers get patched in place (later entries shift by multiples of 0x80), and the CPK writer fixes up ITOC sizes and header totals; with nothing replaced, it reproduces the original file exactly.

## Making a release

Build without test options, then make an xdelta patch against the original CPK:

```sh
python3 tools/build_patch.py extracted/romfs/DA3File_3ds.cpk build/release
mkdir -p build/release/patch
xdelta3 -e -9 -S djw -s extracted/romfs/DA3File_3ds.cpk build/release/00040000000F4000/romfs/DA3File_3ds.cpk build/release/patch/DA3File_3ds.xdelta
xdelta3 -d -c -s extracted/romfs/DA3File_3ds.cpk build/release/patch/DA3File_3ds.xdelta | sha256sum   # must match the built CPK
```

Leave xdelta's source window (`-B`) at its default. Changed files only push the files after them along a little, so the default window still finds every match. A window as big as the CPK used up all the memory on an 8 GB machine. Run `tools/boot_test.sh` on the release CPK before you ship it.

## File formats

| Layer | Format | Tool | Status |
|---|---|---|---|
| `.3ds` | NCSD → NCCH → ExeFS + RomFS | `extract_3ds.py` | read |
| `romfs/DA3File_3ds.cpk` | CRI CPK, ID-only (ITOC), 11,858 files, uncompressed | `cpk.py` | read/write |
| CPK entries | `MRON3.00` containers of tagged entries | `mron.py` | read/write |
| MRON payloads | `SLZ` compression, types 0–3 (all 26,092 blobs verified) | `slz.py` | both ways |
| `RMD-` / `RMDT` | pre-rendered text: messages plus a per-file kanji atlas | `rmd.py` | read/write |
| `SCE-` | Lua 5.1 bytecode (game scripts) | | not yet |
| `*.l2` | Mobiclip MOFLEX video (FMVs) | | not yet |
| `*.awb`, `ACB-` | CRI ADX2 audio | | not needed |

Each tool's docstring has the details.

### Text encoding (RMD)

The global font (`01000/006_RMDT`, `007_RMD`) has 297 glyphs, half-width proportional ASCII among them. A glyph token is two bytes with bit 7 of the first byte set, `v = (b1 << 7) | (b0 & 0x7F)`: values 1–297 point into the global font (`GLOBAL_CHARS` in `rmd.py`), and anything from 301 up is a per-file glyph from the paired RMDT atlas, which is where the kanji and a few symbols like ！ live.

Control codes are `b0 b1` with both high bits set. `0x00` is a newline, `0x06` a page break, `0x10`…`0x11` wraps furigana, and `0x13` inserts a variable such as the player's name. A single `00` ends the message, and in the original data every message is exactly one page.

The message table stores a height of 22 px per furigana line plus 12 px per plain line at 14 px, and `with_texts` recomputes it the same way the original converter did. The "width" field is really a furigana value, 0 when there's none.

SLZ types 1 and 3 end every block with a `00 00` end token (distance 0), and the game's decoder relies on it. Our compressor used to leave it out, so decoding ran past the block and corrupted the heap; both early black screens at boot came from that. `slz.py` explains it.

### In-game layout (measured in Azahar)

The dialogue box holds 319 px per line and two lines. Past 319 px the game breaks words wherever it likes, and a third line lands below the box. Map chatter during missions (52508, 53900) uses a one-line strip at the bottom of the top screen, so a second line ends up off-screen; the Japanese there runs to 364 px. Files with a box other than the dialogue box are listed in `textfit.BOXES` with a hard limit, while everything else may use at least the Japanese width and line count.

There's no extra letter spacing; advance widths come straight from the font table. The original font only had a full-width `！`, drawn as a slanted stroke, so `fontpatch.py` redraws it as an ASCII-style `!` in all five global font copies (01000 and 01500) without changing any file size.

## Dump format (`script/raw`)

Files are named `<container>_<index>_<entry>.tsv`, one `id<TAB>text` row per message. Furigana shows as `{漢字|かんじ}`, and `[n]`, `[p]` and `[var:N]` mean newline, page break and variable. Treat `⟨字⟩` with suspicion: that kanji was identified from its image alone, which happens for about 5% of kanji uses. `glyphs.tsv` lists every unique per-file glyph bitmap with its character, status and how often it's used.

### Kanji identification

The game stores kanji only as bitmaps in per-file atlases, so `identify_kanji.py` has to name each unique bitmap. It needs `.venv` and two dictionaries in `data/`:

- `data/kanjidic/kanjidic2.xml.gz` from https://www.edrdg.org/kanjidic/kanjidic2.xml.gz
- `data/jmdict/JMdict_e.gz` from http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz

Both come from the EDRDG under CC BY-SA 4.0, so attribute them if you redistribute them.

```sh
.venv/bin/python tools/identify_kanji.py extracted/cpk data/glyph_ids.tsv   # ~30 s
.venv/bin/python tools/eval_kanji.py data/glyph_ids.tsv                     # 80/81 on the hand-checked atlas
python3 tools/dump_text.py extracted/cpk script/raw
```

The evidence it weighs, strongest first: furigana compounds that are JMdict words (熟練/じゅくれん, okurigana included, so 逃|に + げる gives 逃げる); 10/11 px message files copied from their identical 14 px twins; furigana matching KANJIDIC readings; and, last, how much the bitmap looks like the Noto Sans CJK glyph. Each bitmap gets one character per font size. Hand corrections in `script/glyph_overrides.tsv` (`key<TAB>char`) beat everything else.

It scores 98.8% on the hand-checked sample. What's left wrong is mostly image-only glyphs and true homophones like 態勢/体勢.

## Things outside the text files

Some Japanese isn't in RMD at all: textures with text drawn into them (`IMAG`, `IMGR`, UI layouts such as the 進む and しらべる buttons and the screen titles), FMV subtitles, and the banner and icon. None of that is started.

Player names are stored as global-font glyph indices. In `code.bin`, the functions at 0x24D324, 0x24D338 and 0x24D35C convert between glyphs and full-width UTF-16/Shift-JIS through 297-entry tables at 0x5E3862 and 0x5E3610, and the runtime char-to-glyph table sits at 0x654DF0. English names typed on the `A/1` keyboard work in game. The tables swap I and J, which round-trips harmlessly but would show over StreetPass.

## Credits and third-party data

The kanji in the script dump were identified with **KANJIDIC2** and **JMdict**, the property of the [Electronic Dictionary Research and Development Group](https://www.edrdg.org/) (EDRDG), used in conformance with the Group's [licence](https://www.edrdg.org/edrdg/licence.html) (Creative Commons Attribution-ShareAlike 4.0).

Those files are research tools only. The patch contains no dictionary data, so distributing it carries no licence obligations from them. If you share the dictionary files themselves, keep this attribution and the CC BY-SA 4.0 licence with them; that's why `data/jmdict/` and `data/kanjidic/` stay out of the repo and everyone downloads their own copy.

Image matching also uses **Noto Sans CJK JP** (SIL Open Font License), read from your system's font directory and never copied into this project or the patch.
