# Contributing

Thanks for helping translate **Danball Senki Wars** (3DS) into English. This guide covers getting set up, how translation works here, how to test, and how to send changes.

Background: [README.md](README.md) covers the file formats and tools. [progress.md](progress.md) has the current status, decisions and open questions.

## Ground rules

- **Never commit game files.** That means no ROMs, CPKs, extracted data or built patches. `.gitignore` covers the usual paths. Everyone works from their own legally dumped copy of the game.
- **Follow the glossary** ([`script/glossary.tsv`](script/glossary.tsv)). If a term isn't there, add it in the same pull request.
- **Test before you submit.** Build the patch and play the part you changed (see [Testing](#testing)).

## Setup

You need Python 3.10+, a dump of the Japanese game (CTR-P-BDNJ, title ID `00040000000F4000`) as a decrypted `.3ds`, and Azahar (or Citra) to test.

```sh
python3 -m venv .venv && .venv/bin/pip install numpy pillow

# unpack the game (about 3 GB of output)
python3 tools/extract_3ds.py "path/to/Danball Senki Wars (Japan) Decrypted.3ds" extracted
python3 tools/unpack_all.py extracted/romfs/DA3File_3ds.cpk extracted/cpk

# emulator-friendly ROM copy (partition 0 is decrypted but lacks the NoCrypto flag)
python3 tools/fix_nocrypto.py "path/to/Danball Senki Wars (Japan) Decrypted.3ds" "build/Danball Senki Wars (Japan) [nocrypto].3ds"
```

The Japanese script is already dumped in `script/raw/`, so you don't need to re-dump it to translate. Re-dumping is only needed after fixing a misread glyph (see [Misread characters](#misread-characters)). For that you also need the dictionaries listed in README, *Kanji identification*.

## How the text is organised

Every text file in the game is a `script/raw/<container>_<index>_<id>.tsv` with one `id<TAB>japanese` row per message. Translations go in a file of the same name in `script/en/`, with columns `id`, `ja` (reference only) and `en`. A blank `en` means untranslated.

| Containers | Content |
|---|---|
| 525xx–533xx | Main story scenes, in play order. `_004_` files are speaker name tags |
| 539xx | Mission events: tutorials and map chatter |
| 11xxx | Character conversations (optional, unlock over time) |
| 06xxx | Examine text around the island |
| 13xxx | Character lists, base and operation names, mission briefings |
| 01000_098 | System text: LBX, parts, weapons, Special Functions, menus, messages |
| 01000_095 | Objective hint in the bottom-screen header |

`01000_100` is a 10 px copy of `01000_098`. Don't edit it; the build copies the `01000_098` translations into it.

Coverage per area: `python3 tools/progress.py`.

## Translating

### The quick loop

```sh
python3 tools/xlate.py show 52610 52611        # untranslated lines, furigana collapsed
# write lines like "52610:3 English text" into a file, e.g. lines.txt
python3 tools/xlate.py check < lines.txt       # wraps exactly like the build; fix every BAD line
python3 tools/xlate.py batch b.tsv < lines.txt
python3 tools/fill_translations.py b.tsv       # merges into script/en/
```

Shorthand: `52610:3 Text` targets the dialogue file `52610_002_*`. Use `52610.4:1 Arata` for another RMD index, such as a name tag file, and `01000.98:17852 Text` for system text.

`xlate.py reuse out.tsv 527` fills speaker tags from `script/speaker_names.tsv` and copies exact repeats of lines already translated. Review the repeats it prints before merging: a short reply like "Yes, sir." depends on who is being answered.

### Markup

| Markup | Meaning |
|---|---|
| `[n]` | Line break. Long lines wrap automatically, but explicit breaks often fit better |
| `[var:0]` | Player name (up to 8 characters) |
| `[x14:0000]` | Player's country name (up to 8 characters) |
| `[c:01]…[x2]`, `[c:03]…[x2]` | Narration and colour; keep them where the Japanese has them |

Don't add the final `[p]`; the build does that.

### Space limits

- **Dialogue box:** 319 px per line, 2 lines. Beyond that the game breaks words mid-way or draws off the box. `check` measures in pixels with the real font, so trust it over character counts.
- **Other boxes** are listed in `textfit.BOXES` in `tools/textfit.py`. Examples: map chatter (one line), the objective header (one line, 280 px), and battle lines (one line, 319 px). If you find a new one in game, add it there.
- **Names and labels in the data files** must not be bigger than the largest original of their kind; long names might overflow the game's buffers. Run `python3 tools/sizecheck.py` after changing any names. It must print nothing.

### Characters

The font has only ASCII letters, digits and basic punctuation (plus a redrawn `!`). There are **no accented letters** ("Cafe", not "Café"), no `☆` and no Greek letters. `"`, `[`, `]`, `<`, `>` and `~` are mapped to the nearest full-width glyph. `check` reports anything unsupported.

### Style

- **Names:** romanized Japanese, Hepburn without macrons, long vowels dropped (Hojo, Kojo, Ginjiro). Given name first. Speaker tags show the given name only.
- **Honorifics** become natural English ("Captain", "Ms. Mito"), not -san/-kun.
- **Katakana loanwords** use their English form (Achilles, Dot Phaser).
- **Voices:** Suzune speaks casual Kansai, which becomes a relaxed "gonna/ya" English. Josephine is flamboyant ("darling", "-kins"/"-poo" nicknames). Metazawa ends lines with "-mo". Keep characters consistent with what's already translated.
- Aim for natural English that fits the box, not a literal gloss. When in doubt, read the surrounding scene.

### Misread characters

`⟨字⟩` in the dump marks a kanji identified only from its image, and digits are often wrong: ⟨日⟩ can be 3 or 8, ⟨Ｑ⟩ is usually 0. To check one:

```sh
.venv/bin/python tools/glyphsheet.py /tmp/glyphs.png 52567     # draws the unverified glyphs of a container
```

Add the right character to `script/glyph_overrides.tsv` (`key<TAB>char`) and re-dump with `.venv/bin/python tools/dump_text.py extracted/cpk script/raw`.

## Testing

```sh
python3 tools/build_patch.py --test-ids extracted/romfs/DA3File_3ds.cpk build/mods
tools/boot_test.sh                  # headless Azahar boot check; must say OK
```

- `--test-ids` shows untranslated text as labels like `01000.98:17852` (container.index:id), so screenshots tell you exactly which line to translate next.
- Install the patch as a LayeredFS mod: put `build/mods/00040000000F4000/romfs/` in Azahar's mod folder (right-click the game, *Open Mods Location*). On a 3DS, it goes in `luma/titles/00040000000F4000/romfs/`.
- Load `build/Danball Senki Wars (Japan) [nocrypto].3ds` in Azahar.
- **Don't load emulator save states across builds.** A quicksave from an older build crashes the new one. Use in-game saves.
- `build/mods/text_report.txt` lists overflows and UI strings much wider than the Japanese.

## Sending changes

1. Fork, or create a branch named after the content (e.g. `conversations-117xx`, `ui-lab-menu`).
2. Keep each pull request to one area or chunk of scenes so it can be reviewed.
3. Before opening it, run `xlate.py check` on everything you added (no BAD lines), then `tools/sizecheck.py` (no output) and a build plus `boot_test.sh` (OK).
4. In the description, say what you covered and how you tested it, and attach screenshots of anything in a new kind of box or menu.
5. New names or terms go in `script/glossary.tsv`, new speaker tags in `script/speaker_names.tsv`.

## Where help is needed

See *Next steps* in [progress.md](progress.md). In short:

- **System text and UI** (01000_098): menus, battle messages, capture announcements. Screenshots with labels help a lot.
- **Character conversations** (11xxx) and **examine text** (06xxx), the two biggest untranslated areas.
- **Proofreading** the translated story in game: wording, character voice, anything that doesn't fit.
- **Graphics:** buttons and titles with Japanese drawn into the image (進む, しらべる, screen headers). Not started.
