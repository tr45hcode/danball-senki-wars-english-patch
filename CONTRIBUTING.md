# Contributing

Glad you're here. This covers setting up, how translation works in this repo, testing your changes in an emulator, and sending them in. [README.md](README.md) explains the file formats and tools in more depth, and [progress.md](progress.md) has the current status, the decisions made so far and the open questions.

About 95% of the text is in English now, and v0.1-beta went out as a closed beta on 2026-11-02, so most of the work left is playing the game and fixing what turns up. The other big job is the Japanese drawn into textures, which is partly done. [Where help is needed](#where-help-is-needed) says what that means in practice. You don't need any of the setup below to play the beta and report bugs; the zip on [Releases](https://github.com/tr45hcode/danball-senki-wars-english-patch/releases) has its own install steps.

## Before you start

Never commit game files: no ROMs, no CPKs, no extracted data, no built patches. `.gitignore` already catches the usual paths, but check `git status` before you push anyway. Everyone works from their own dump of the game.

Stick to [`script/glossary.tsv`](script/glossary.tsv) for names and terms, and if you need a term that isn't in there yet, add it in the same pull request. And play what you changed before you send it; the [Testing](#testing) section shows how.

## Setup

You'll need Python 3.10 or newer, a decrypted `.3ds` dump of the Japanese game (CTR-P-BDNJ, title ID `00040000000F4000`), and Azahar or Citra for testing.

```sh
python3 -m venv .venv && .venv/bin/pip install numpy pillow

# unpack the game (about 3 GB of output)
python3 tools/extract_3ds.py "path/to/Danball Senki Wars (Japan) Decrypted.3ds" extracted
python3 tools/unpack_all.py extracted/romfs/DA3File_3ds.cpk extracted/cpk

# emulator-friendly ROM copy (partition 0 is decrypted but lacks the NoCrypto flag)
python3 tools/fix_nocrypto.py "path/to/Danball Senki Wars (Japan) Decrypted.3ds" "build/Danball Senki Wars (Japan) [nocrypto].3ds"
```

The Japanese script is already dumped in `script/raw/`, so translating doesn't require a re-dump. You'd only re-dump after fixing a misread glyph (see [Misread characters](#misread-characters)), and that also needs the two dictionaries from README's *Kanji identification* section.

Redrawing texture labels also needs Fira Sans and Fira Sans Condensed installed (`ttf-fira-sans` on Arch). Building doesn't.

## How the text is laid out

Every text file in the game becomes `script/raw/<container>_<index>_<id>.tsv`, one `id<TAB>japanese` row per message. Translations go in the file with the same name under `script/en/`, which has three columns: `id`, `ja` (just for reference) and `en`. An empty `en` means the line isn't translated yet.

| Containers | What's in them |
|---|---|
| 525xx–533xx | Main story scenes in play order; the `_004_` files are speaker name tags |
| 539xx | Mission events: tutorials and map chatter |
| 11xxx | Character conversations, which unlock as you play |
| 06xxx | Examine text around the island (065xx), Special Function descriptions (06525/06526), the mission map's place tables (06730) |
| 13xxx | Character lists, base and operation names, mission briefings |
| 01000_098 | System text: LBX, parts, weapons, Special Functions, menus, messages |
| 01000_095 | The objective hint in the bottom screen's header bar |
| 01047, 01049 | Partner gift messages, multiplayer room help |
| `script/gfx/` | Not a container: English for the labels drawn into textures, one table per atlas |

Leave `01000_100` alone. It's a 10 px copy of `01000_098`, and the build fills it from your `01000_098` translations.

`python3 tools/progress.py` shows how much of each area is done. The conversations, examine text, LBX data and system text are all past 98%. The story sits at 85% only because it counts debug and placeholder lines along with the 53920–53922 lists, which are skipped on purpose. Of what's still untranslated, the lines that matter are the [fragments](#fragments) the game joins together while you play.

## Translating

### The usual loop

```sh
python3 tools/xlate.py show 52610 52611        # untranslated lines, furigana collapsed
# write lines like "52610:3 English text" into a file, e.g. lines.txt
python3 tools/xlate.py check < lines.txt       # wraps exactly like the build; fix every BAD line
python3 tools/xlate.py batch b.tsv < lines.txt
python3 tools/fill_translations.py b.tsv       # merges into script/en/
```

`52610:3 Text` targets the dialogue file `52610_002_*`. For another RMD index, such as a name tag file, write `52610.4:1 Arata`; for system text, `01000.98:17852 Text`. `show` prints each line under the same key, so you can copy its output and swap the Japanese for English.

`xlate.py reuse out.tsv 527` fills speaker tags from `script/speaker_names.tsv` and copies lines that exactly repeat something already translated. Look over the repeats it prints before you merge them, since a short reply like "Yes, sir." isn't right for every listener.

### Markup

| Markup | Meaning |
|---|---|
| `[n]` | Line break. Long lines wrap on their own, but a hand-placed break often fits better |
| `[var:0]` | The player's name, up to 8 characters |
| `[x14:0000]` | The player's country name, also up to 8 |
| `[c:01]…[x2]`, `[c:03]…[x2]` | Narration and colour; keep them where the Japanese has them |

The build adds the final `[p]`, so don't type it.

### How much fits

The dialogue box takes 319 px per line and two lines. Go past that and the game breaks words mid-way or draws text outside the box. `check` measures with the game's real font, so trust its pixel counts over counting characters.

Some text lives in other boxes with their own limits, listed in `textfit.BOXES` in `tools/textfit.py`. Map chatter gets one line, battle lines one line of 319 px, and the objective header and the Special Function descriptions one line of 280 px each. A single system message with a box of its own goes in `textfit.MESSAGE_BOXES` instead: the examine hint 17922 shows in the bottom screen's header, so it's capped at one 280 px line. If you find another kind of box in game, add it to one of those two tables.

Many of those limits are still guesses waiting on a screenshot. *Open questions* in progress.md lists them, and a contributor who plays far enough to see one of those boxes can settle it.

Names and labels in the data files have one more rule, and so do the speaker tags and the examine labels on the map. They must not end up bigger than the largest original of their kind, in case the game copies them into fixed-size buffers. Run `python3 tools/sizecheck.py` after changing any of them; it should print nothing.

### Fragments

Some system lines aren't whole messages. The game sticks them onto a name or a number while you play: 17320 and 17321 become `[item] x[N] obtained!`, and 17801/17802 become `BA Cards: [N] left`. Put any space the joined text needs inside the fragment itself, as in ` x` and ` obtained!`; the build keeps spaces at either end of a translation.

Nobody has seen most of these in game yet, so their word order is a guess. *Open questions* in progress.md lists the ids. The partner gift fragments (01047.12:152–157, 159–171 and 173–182) are still untranslated labels, waiting on a screenshot that shows how the game puts them together. 01000.98:62001–62029 hold the same pieces and already have a guessed translation.

### The font

It only has ASCII letters, digits, basic punctuation and a redrawn `!`. That means no accented letters (write "Cafe", not "Café"), no `☆` and no Greek. `"`, `[`, `]`, `<`, `>` and `~` get mapped to the closest full-width glyph. `check` tells you about anything it can't draw.

### Style

Names are romanized Japanese in Hepburn without macrons, with long vowels dropped (Hojo, Kojo, Ginjiro) and the given name first; speaker tags use the given name only. Honorifics turn into natural English such as "Captain" or "Ms. Mito" rather than -san or -kun. Katakana loanwords take their English form, so アキレス is Achilles and ドットフェイサー is Dot Phaser.

Characters have voices. Suzune talks in casual Kansai dialect, which comes out as relaxed "gonna, ya" English; Josephine is flamboyant, all "darling" and "-kins"/"-poo" nicknames; Metazawa ends his lines with "-mo". Read some of what's already translated for a character before you write their lines.

Go for natural English that fits the box rather than a literal gloss, and when a line is unclear, read the scene around it.

### Labels in textures

Buttons, screen titles and battle callouts are pictures, not text, so they go through `tools/gfx.py` instead of `xlate.py`. README's *Text drawn into textures* section explains how it works; this is the loop:

```sh
python3 tools/gfx.py sprites 54200_000 /tmp/s.png    # numbered sprites of one atlas
# fill in the en column of script/gfx/54200_000.tsv (gfx.py template makes one)
python3 tools/gfx.py render 54200_000                # prints a warning for every label that doesn't fit
python3 tools/gfx.py preview 54200_000 /tmp/p.png    # check every row against its Japanese
python3 tools/gfx.py copies
```

`grep -l ジオラマ script/gfx/*.tsv` finds the table for a label you saw in game, if someone has already made one; otherwise the contact sheets from `python3 tools/aif.py sheet /tmp/sheets extracted/cpk/<container>` show what each container holds.

Use the same words the system text uses for the same thing, so a button and the message it opens agree: "Special Function", "Sortie", "Squads", "Link Battle", "Secret" for ウラ. Sprites never grow, so a warning from `render` means the English has to get shorter. A short abbreviation ("Wpn", "Vo.") reads better than text squeezed down to five pixels, and the preview shows you which one you've got. Look at the preview at full size too: `bg=rows` sometimes leaves a faint line where the Japanese was, which `thresh=` or `margin=` usually fixes.

### Misread characters

`⟨字⟩` in the dump marks a kanji identified only from its image. Digits are the usual trouble: ⟨日⟩ can be 3 or 8, and ⟨Ｑ⟩ is normally 0. To see what a glyph really is:

```sh
.venv/bin/python tools/glyphsheet.py /tmp/glyphs.png 52567     # draws the unverified glyphs in a container
```

Put the right character in `script/glyph_overrides.tsv` (`key<TAB>char`) and re-dump with `.venv/bin/python tools/dump_text.py extracted/cpk script/raw`.

`script/raw` is one override behind right now. Glyph `14_d92d9cd98d`, shown as ⟨Ω⟩, is really a 9, but the dump predates that fix, so a few reference lines in 06505 and the Special Function descriptions still show ⟨Ω⟩. The English already uses 9.

## Testing

```sh
python3 tools/build_patch.py --test-ids extracted/romfs/DA3File_3ds.cpk build/mods
tools/boot_test.sh                  # headless Azahar boot check; it has to say OK
```

With `--test-ids`, untranslated text shows up in game as a label like `01000.98:17852` (container.index:id), so a screenshot tells you exactly which line to translate next.

To play it, install `build/mods/00040000000F4000/romfs/` as a LayeredFS mod (right-click the game in Azahar, *Open Mods Location*) and load `build/Danball Senki Wars (Japan) [nocrypto].3ds`. On a 3DS the folder goes in `luma/titles/00040000000F4000/romfs/`, though nobody has tried the patch on real hardware yet.

One warning that has already cost us a crash investigation: don't load an emulator save state made with an older build. The game crashes because its memory no longer matches the files, and it looks exactly like a patch bug. Use in-game saves instead.

If something overflows, or a UI string comes out much wider than its Japanese, `build/mods/text_report.txt` will list it.

## Sending changes

Work on a fork or a branch named after what you're doing, like `fragments-item-messages` or `proofread-chapter1`, and keep each pull request to one area or chunk of scenes so someone can review it in one sitting.

Before you open it, `xlate.py check` should show no BAD lines for anything you added, `tools/sizecheck.py` should print nothing, and a fresh build should pass `boot_test.sh`. In the description, say what you covered and how you tested it, with screenshots of any box or menu that hasn't been translated before. For texture labels, attach the `gfx.py preview` image and commit the rendered PNG along with the table. Put new names or terms in `script/glossary.tsv` and new speaker tags in `script/speaker_names.tsv`.

## Where help is needed

*Next steps* in [progress.md](progress.md) has the full list. With the translation nearly done, the job now is finding out how it holds up in game.

**Playtesting.** Our playtests so far covered the prologue and some menus in Azahar, but chapter 1, the character conversations and the map still need a proper run. Flag English that reads badly or sounds wrong for the character, text that runs out of its box, labels that overlap the menu next to them, and any Japanese left on screen. A playtest also settles the box sizes we guessed (see [How much fits](#how-much-fits)), so a screenshot of a map chatter line, a conversation or a Special Function description helps even when nothing looks wrong.

**Bug reports from the beta.** [Open an issue](https://github.com/tr45hcode/danball-senki-wars-english-patch/issues) with the version (v0.1-beta), a screenshot, where you were in the game and what you did just before it, and your emulator and its version, or your 3DS and Luma version.

**Fragment screenshots.** A shot of any message the game builds from pieces, such as an item pickup, a skill being learned or a partner's gift, tells us whether the guessed order is right. Build with `--test-ids` so the untranslated pieces show their labels; see [Fragments](#fragments).

**A real 3DS.** If you have Luma3DS, try the install steps in the release README.txt and tell us whether the game boots and the text shows.

**Graphics.** About 400 labels in 34 atlases are in English, among them 進む, しらべる, the screen titles, the title and system menus, the Lab and the Shop, multiplayer, the mission map and the battle screen. Nobody has seen most of them in game, so a screenshot of any menu helps, especially one where a label looks cut off or squashed. Still in Japanese: the pause menu (54200), Mission Start and the victory and defeat conditions (01002_009), the notices at boot and the save-tampering warnings, the button hint bars, the team tabs and the menu screenshots on the help pages (06520). The squad formation screen is stuck behind a CPK size limit (README, *Things outside the text files*). Nobody has looked at the cutscene videos (MOFLEX) yet.
