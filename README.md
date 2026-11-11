# Danball Senki Wars (3DS, CTR-P-BDNJ) English patch

A fan translation of Level-5's Danball Senki Wars, plus the tools that pull the game's text apart and put it back together. We've translated the main story, the character conversations, the map examine text, the menus and the LBX data, about 95% of the game's text. What's left is mostly placeholders and debug lines, plus a few short pieces the game joins together while you play. About 400 labels that the game draws as pictures rather than text (menu titles, buttons, the battle screen's callouts) have English versions too, though some screens still show Japanese. To play it, get the patch from [Releases](https://github.com/tr45hcode/danball-senki-wars-english-patch/releases); the README.txt in the zip explains how to apply it. [progress.md](progress.md) tracks what's done, what we decided and what's next. If you'd like to help, read [CONTRIBUTING.md](CONTRIBUTING.md).

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

`show` lists untranslated lines with the furigana collapsed, keyed the same way the other commands read them, so you can paste its output back with English in place of the Japanese. `check` and `batch` read shorthand like `52600:4 English` (or `52600.4:1 Tag` for a name tag file); `check` wraps each line exactly the way the build will and prints its width in pixels, and `batch` turns the lines into a file `fill_translations.py` can merge. There's also `reuse out.tsv 526`, which fills speaker tags from `script/speaker_names.tsv` and copies exact repeats of lines that are already translated. Read what it copies before merging, because a short reply like "Yes, sir." only fits when the person being answered is someone you'd call sir.

Markup you'll meet:

| Markup | Meaning |
|---|---|
| `[n]` | line break; long lines also wrap on their own at 319 px |
| `[var:0]` | the player's name |
| `[x14:0000]` | the player's country name |
| `[p]` | page break; the build adds the closing one, so leave it out |

The font has no `!`, `"`, `[`, `]`, `<`, `>` or `~` in its ASCII set. `!` got redrawn into the font, and the rest get swapped for the nearest full-width glyph.

The system text exists twice, at 14 px (`01000_098`) and 10 px (`01000_100`) with the same ids. Translate `01000_098` only; the build copies those lines into the 10 px bank.

Some system lines are fragments the game glues to a name or number at runtime (17320 + 17321 make `[item] x[N] obtained!`). The build keeps spaces at either end of a translation, so a fragment carries the spaces it needs. Their order is mostly guessed; [CONTRIBUTING](CONTRIBUTING.md#fragments) has the details.

Names, places and LBX terms are in `script/glossary.tsv`. In short: romanized Japanese names (Hepburn, no macrons, given name first), speaker tags with given names only, and honorifics turned into plain English.

A few tools help with the awkward cases. Image-only glyphs show up as `⟨日⟩` or `⟨Ｑ⟩`, and the digit guesses mix up 3, 8 and 日, or 0 and Ｑ; `.venv/bin/python tools/glyphsheet.py out.png 52567` draws them so you can read the real character, which then goes in `script/glyph_overrides.tsv` before a re-dump. `tools/layout.py 52508` prints the width and line count of each original message, and `layout.py --scan` lists files that might use a one-line box. Run `tools/sizecheck.py` after changing names or labels: it flags any string bigger than the largest original of its kind, and it should print nothing.

Story order: the 525xx containers are the story scenes in play order. 52500 is the opening battle, 52502/52504/52506 are name, appearance and country entry, 52511 is the intro narration and 52512 the opening song; the ship scene in 52513 picks up straight after. Mission events (tutorial pop-ups, map chatter) are in 539xx, character conversations in 11xxx, and things you examine on the map in 06xxx.

## Text drawn into textures

Menu titles, buttons and battle callouts aren't RMD text at all. They're sprites cut out of texture atlases, and `tools/gfx.py` redraws them in English. Each atlas gets a table in `script/gfx/` named after its container and entry index (`13080_005.tsv` is the system menu), with one row per sprite:

```
sprite	ja	en	options
3	タイトルにもどる	Return to Title
86	カメラ	Camera	bg=rows in=4,5,56,13 margin=3
```

```sh
python3 tools/gfx.py list                          # every texture with a sprite list (~180)
python3 tools/gfx.py sprites 13080_005 out.png     # numbered sprites, to read the Japanese
python3 tools/gfx.py template 13080_005            # writes an empty table
python3 tools/gfx.py render 13080_005              # draws script/gfx/13080_005.png
python3 tools/gfx.py preview 13080_005 out.png     # Japanese and English side by side
python3 tools/gfx.py copies                        # finds copies of translated atlases
```

`render` sets each label in Fira Sans and copies its look from the Japanese sprite: the fill colour at the top and bottom of the letters, and whether they have an outline, a drop shadow or neither. When the English is too wide it switches to Fira Sans Condensed, then shrinks the text, and it prints a warning if the label still doesn't fit. Labels only 6 px high get a small built-in pixel font (`font=pixel`), since outlined letters turn to mush at that size. The options column covers the awkward sprites, and `gfx.py`'s docstring lists every option; you'll mostly need `bg=rows`, which wipes the Japanese off a badge or button but keeps the badge, and `in=x,y,w,h`, which replaces one part of a sprite (the battle screen's camera button has a word above its icon and another below it).

The PNG holds the English and nothing else. At build time, `gfx.py` clears each sprite in the original texture, or wipes its text for `bg=rows`, and draws the PNG's label on top, so none of the game's art ends up in the repo. `script/gfx/copies.tsv` lists atlases in other containers that are pixel-for-pixel copies of a translated one, and the build patches those as well; run `copies` again whenever you add a table.

A sprite can't grow, because the game's layout files fix where and how big it's drawn. English that runs much longer than the Japanese has to shrink or abbreviate, which is how 声 on the appearance screen ended up as "Vo.".

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

`build/mods/text_report.txt` lists lines that overflow and UI strings much wider than their Japanese. The build prints how many textures it redrew; it reads the overlay PNGs as they are and doesn't need Fira Sans installed.

Repacking leaves everything it doesn't touch byte-identical. Containers get patched in place (later entries shift by multiples of 0x80), and the CPK writer fixes up ITOC sizes and header totals; with nothing replaced, it reproduces the original file exactly.

The ITOC keeps two size tables: `DataL` holds files under 64 KB with 16-bit sizes, and `DataH` holds the rest with 32-bit ones. When a rebuilt file outgrows 65,535 bytes, `cpk.py` moves its row from the first table to the second and writes both again. Only the squad formation container (13070) needs that so far, since it's 61,520 bytes in the original and 74,320 with its texture redrawn. Each move costs about 4 bytes of the 1,088 that sit free between the ITOC and the file data, so roughly 270 files can move before the writer stops with an error.

## Making a release

Build without test options, then make an xdelta patch against the original CPK:

```sh
python3 tools/build_patch.py extracted/romfs/DA3File_3ds.cpk build/release
mkdir -p build/release/patch
xdelta3 -e -9 -S djw -s extracted/romfs/DA3File_3ds.cpk build/release/00040000000F4000/romfs/DA3File_3ds.cpk build/release/patch/DA3File_3ds.xdelta
xdelta3 -d -c -s extracted/romfs/DA3File_3ds.cpk build/release/patch/DA3File_3ds.xdelta | sha256sum   # must match the built CPK
```

Leave xdelta's source window (`-B`) at its default. Changed files only push the files after them along a little, so the default window still finds every match, while a window as big as the CPK filled all the memory on an 8 GB machine, and systemd-oomd killed the whole terminal. Run `tools/boot_test.sh` on the release CPK before you ship it.

## File formats

| Layer | Format | Tool | Status |
|---|---|---|---|
| `.3ds` | NCSD → NCCH → ExeFS + RomFS | `extract_3ds.py` | read |
| `romfs/DA3File_3ds.cpk` | CRI CPK, ID-only (ITOC), 11,858 files, uncompressed | `cpk.py` | read/write |
| CPK entries | `MRON3.00` containers of tagged entries | `mron.py` | read/write |
| MRON payloads | `SLZ` compression, types 0–3 (all 26,092 blobs verified) | `slz.py` | both ways |
| `RMD-` / `RMDT` | pre-rendered text: messages plus a per-file kanji atlas | `rmd.py` | read/write |
| `IMAG`, `IMGR`, `UAIF` | AIF textures in the 3DS GPU's tiled layout | `aif.py` | read/write |
| `ATD-`, `UATD` | sprite rectangles of a texture atlas | `gfx.py` | read |
| `ULD-` | UI layouts: where each sprite goes on screen | | not yet |
| `SCE-` | Lua 5.1 bytecode (game scripts) | | not yet |
| `*.l2` | Mobiclip MOFLEX video (FMVs) | | not yet |
| `*.awb`, `ACB-` | CRI ADX2 audio | | not needed |

Each tool's docstring has the details.

### Text encoding (RMD)

The global font (`01000/006_RMDT`, `007_RMD`) has 297 glyphs, half-width proportional ASCII among them. A glyph token is two bytes with bit 7 of the first byte set, `v = (b1 << 7) | (b0 & 0x7F)`: values 1–297 point into the global font (`GLOBAL_CHARS` in `rmd.py`), and anything from 301 up is a per-file glyph from the paired RMDT atlas, which is where the kanji and a few symbols like ！ live.

Control codes are `b0 b1` with both high bits set. `0x00` is a newline, `0x06` a page break, `0x10`…`0x11` wraps furigana, and `0x13` inserts a variable such as the player's name. A single `00` ends the message, and in the original data every message is exactly one page.

The message table stores a height of 22 px per furigana line plus 12 px per plain line at 14 px, and `with_texts` recomputes it the same way the original converter did. The "width" field is really a furigana value, 0 when there's none.

SLZ types 1 and 3 end every block with a `00 00` end token (distance 0), and the game's decoder relies on it. Our compressor used to leave it out, so decoding ran past the block and corrupted the heap; both early black screens at boot came from that. `slz.py` explains it.

### Textures (AIF)

An AIF file starts with 0x1E0 bytes of headers. The `imgX` chunk at 0x80 holds the pixel format (+0x20), the width and height (+0x28) and the data size (+0x3C), and the pixels follow straight after in the GPU's own layout: 8×8 tiles in Morton order, rows stored bottom-up, each pixel's channels reversed (RGBA8 is stored A B G R). Two files leave out the `aRF ` chunk, which moves `imgX` to 0x10 and the pixels to 0x170.

The game's textures come in RGBA8, RGBA4444, RGB8, RGB565, RGBA5551, A8, ETC1 and ETC1A4. ETC1 packs 4×4 blocks four to a tile in Z order, and ETC1A4 puts a 64-bit block of 4-bit alpha in front of each colour block. ETC1 is lossy, so `aif.py` re-encodes only the blocks under a changed sprite and leaves every other byte of the texture alone; the uncompressed formats round-trip byte for byte. It doesn't write RGB565 or RGBA5551 yet, since no translated sprite has needed them.

The sprite list sits in a separate entry with the texture's id, `UATD` next to a `UAIF` or `ATD-` next to an `IMAG`. It has the sprite count at 0x14 and the atlas size as two floats at 0x18, then 28 bytes per sprite: u0, v0, u1, v1 as fractions of the atlas, the sprite's width and height in pixels, and a zero.

### In-game layout (measured in Azahar)

The dialogue box holds 319 px per line and two lines. Past 319 px the game breaks words wherever it likes, and a third line lands below the box. Map chatter during missions (52508, 53900) uses a one-line strip at the bottom of the top screen, so a second line ends up off-screen; the Japanese there runs to 364 px. Files with a box other than the dialogue box are listed in `textfit.BOXES` with a hard limit, while everything else may use at least the Japanese width and line count. Single system messages with a box of their own go in `textfit.MESSAGE_BOXES`; the examine hint 17922 sits in the bottom screen's one-line header, so it's capped at 280 px. Several of these sizes (the possible chatter files, the Special Function descriptions) are inferred from the Japanese and still need checking in game.

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

Some Japanese isn't in RMD at all. Textures are partly done (see [Text drawn into textures](#text-drawn-into-textures) and progress.md for what's left), while nobody has started on the FMV subtitles or the banner and icon.

Player names are stored as global-font glyph indices. In `code.bin`, the functions at 0x24D324, 0x24D338 and 0x24D35C convert between glyphs and full-width UTF-16/Shift-JIS through 297-entry tables at 0x5E3862 and 0x5E3610, and the runtime char-to-glyph table sits at 0x654DF0. English names typed on the `A/1` keyboard work in game. The tables swap I and J, which round-trips harmlessly but would show over StreetPass.

## Credits and third-party data

The kanji in the script dump were identified with **KANJIDIC2** and **JMdict**, the property of the [Electronic Dictionary Research and Development Group](https://www.edrdg.org/) (EDRDG), used in conformance with the Group's [licence](https://www.edrdg.org/edrdg/licence.html) (Creative Commons Attribution-ShareAlike 4.0).

Those files are research tools only. The patch contains no dictionary data, so distributing it carries no licence obligations from them. If you share the dictionary files themselves, keep this attribution and the CC BY-SA 4.0 licence with them; that's why `data/jmdict/` and `data/kanjidic/` stay out of the repo and everyone downloads their own copy.

Image matching also uses **Noto Sans CJK JP** (SIL Open Font License), read from your system's font directory and never copied into this project or the patch.

The English in redrawn textures is set in **Fira Sans** and **Fira Sans Condensed** (SIL Open Font License), which `gfx.py render` also reads from your system (on Arch, the `ttf-fira-sans` package). The overlay PNGs and the patch contain text drawn with it, which the licence allows; the font files themselves aren't part of either.
