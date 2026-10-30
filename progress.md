# Progress

English patch for **Danball Senki Wars** (3DS, CTR-P-BDNJ, title ID `00040000000F4000`).
Technical details live in [README.md](README.md). This file tracks what's done, what's next, and what we've decided.

_Last updated: 2026-10-30_

## Status at a glance

| Area | State |
|---|---|
| Unpacking the game | ✅ Done. Every layer read and verified (3DS → CPK → MRON → SLZ → text/fonts) |
| Repacking | ✅ Done. Byte-identical when nothing changes, and working in-game |
| Text format | ✅ Decoded: 905 files, 25,193 messages, all parse cleanly |
| Japanese script dump | ✅ Readable. Kanji identification 98.8% on a hand-checked sample |
| English text in-game | ✅ Working: wrapping, `!` glyph, name entry |
| Translation | 🟡 Main story done; LBX data, character lists, battle and gift messages done (55.8% overall) |
| Graphics with baked-in Japanese | ⬜ Not started |
| Cutscene videos (MOFLEX) | ⬜ Not started |
| Distribution (patch packaging) | ⬜ Not started |

## Translation progress

Refresh with `python3 tools/progress.py`.

| Area | Translated | Total | % |
|---|---:|---:|---:|
| Story scenes | 4,560 | 5,360 | 85.1% |
| Character conversations | 0 | 3,180 | 0.0% |
| Map examine text | 0 | 3,676 | 0.0% |
| Character/LBX data | 1,727 | 1,735 | 99.5% |
| System & UI | 4,715 | 5,780 | 81.6% |
| Other | 27 | 34 | 79.4% |
| **All** | **11,029** | **19,765** | **55.8%** |

Story scenes include the speaker name tags (filled from `script/speaker_names.tsv`). The remaining story lines are debug/placeholder text, the 53922 CG list and the 53920/53921 debug lists.

Translated so far:
- **Prologue, 52500–52512:** opening battle, setup screens (name/appearance/country), squad briefing, movement tutorial, patrol, intro narration, opening song lyrics, and all speaker name tags.
- **Prologue map events:** patrol chatter (53900, a copy of 52508) and the item-light tutorial (53902).
- **The ship, 52513–52516:** arrival announcements, meeting Arata, the leg-parts chat (52514 repeats 52513 and adds it), and the talk after the tutorial battle. 52515 (`【01_0160】 チュートリアルバトル…`) is left as a label to see whether players ever see these scene titles.
- **Chapter 1, 52517–52609:** arrival on Kamui Island, the academy, War Time and the ERP briefing, the first mission (Oasis 8), Duck Lodge, Saruta's class, Needs City, Cafe Swallow, the Enka Ruins race and the Port Grande rescue, up to 2nd and 3rd Squads joining. Also the mission tutorials they trigger (53903–53924). Scene titles (`【01_xxxx】`, one-line files) and debug lines (`ゔケノゔ絵`) are skipped.
- **Chapters 2–4, 52700–53340:** the Bandits, Gold Valley scouting, Muraku and the truth about the Second World, the Deathwalz Brothers, the Jenock alliance and the "silent war", Rikuya and the Parasite Keys, the Death Forest and Overload, Seredi and Ezeldarm, the Dot Blastrizer, Rose City, Ayabe's betrayal and the Under Balance, the World Alliance and the Dol Garuda. About 420 story lines remain, in 53341–53388 (the ending), plus the mission-unlock messages in 53901.
- **The ending, 53341–53388,** and the mission-unlock messages (53901). The whole main story is now in English.
- **LBX data (system text 01000.98):** all LBX and part names (1000–4999), weapons (5000–6023), weapon info lines (7000–8045, generated from a term table), chips and their descriptions (14xxx), Special Functions (48xxx, 51xxx), modes and misc parts (53xxx–56xxx), and the character lists (24xxx, 32xxx).
- **13xxx data:** character name lists (13011 in three font sizes, 13017), base names, operation names, mission briefings ("Info") and goals (13260), and the multiplayer menus.
- **Capture announcements (01000.98:10000–10176),** generated from the 13260 place table: "Ownership of X / passes from Y", then "to [x14:0000]. All fighting in the base must stop immediately."
- **Battle messages (01000.98:12000–12510):** the battle log for squads and named characters (Flag, boss, LP/BP recovery, C Gauge, Item Box, enemy Special/Ultimate warnings, LP critical) and the counter menu. One line of at most 308 px, the widest Japanese.
- **Partner gift messages (01047.12:1–151, 158, 172, 183).** The fragments the game joins at runtime (152–157, 159–171, 173–182) are left as labels until a screenshot shows their order.
- **System text:**
  - opening-movie skip prompt (Skip?/Yes/No)
  - name-entry screen (prompt, confirmation, invalid-name error, the online-name notice)
  - country-name entry (prompt, confirmation)
  - appearance/voice screen (prompt, Male/Female, Type 1–10, Play Voice, confirmation)

## Decisions

| Topic | Decision |
|---|---|
| Character names | Romanized Japanese, not the English LBX release names (Ban, Jin, not Van, Justin) |
| Romanization | Hepburn, no macrons, long vowels dropped (Hojo, Kojo, Ginjiro) |
| Name order | Given name first. Speaker tags show given names only |
| Honorifics | Localized into natural English (Haruki → "Captain") |
| Loanwords | English form (アキレス → Achilles, ドットフェイサー → Dot Phaser) |
| Nations | ジェノック → Jenock, ロシウス → Rossius |
| Workflow | Story order, in playtested chunks: translate a chunk, play it in Azahar, fix |
| Unsupported punctuation | `!` redrawn into the font. `"` `[` `]` `<` `>` `~` map to the nearest full-width glyph |

All names and terms are in [`script/glossary.tsv`](script/glossary.tsv).

## Verified in-game (Azahar 2126.2)

- English text renders with the game's own proportional font. There's no extra letter spacing.
- Dialogue box: **319 px per line, 2 lines per message**. Longer lines are broken mid-word by the game, and a third line falls outside the box.
- Map chatter box (52508/53900): **one line**; a second line is drawn off-screen. Japanese lines reach 364 px, which is the limit we wrap to (`textfit.BOXES`).
- The redrawn `!` displays correctly.
- The boot-time black screens came from a missing SLZ end-of-block token in type-1 blocks (fixed in `slz.py`). An earlier theory blaming stale message heights was wrong; heights are still recomputed.
- Boot-time text can grow: a test build growing the system text by 170 KB boots.
- Name entry works with English names.
- Appearance/voice screen: prompt, Male/Female and Type N show in both the appearance and voice boxes.
- `[x14:0000]` prints the country name the player typed on the country-entry screen.
- Test labels (`--test-ids`) show where any untranslated text on screen comes from.

## Open questions

- Can a message have more than one page? The original never uses a mid-message `[p]`. If it works, long lines could spill onto a second page instead of being cut. `--ruler` builds include a test for this, but it hasn't been checked in-game yet.
- Layout of the narration (52511) and opening lyrics (52512) boxes. They're currently wrapped like dialogue; waiting on the playtest.
- `[x14:0100]` (Josephine, 52525) is probably the player's name or a nickname made from it. To be checked in-game.
- One-line boxes: 52541, 52589, 52603, 53904 and 53908 look like mid-mission chatter, so they're kept to one line of at most 319 px (`textfit.BOXES`), which fits either box. Confirm in-game.
- How wide the map chatter box really is. Some Japanese chatter lines are far wider than the screen (53904: 490 px), so the box may scroll. Possible chatter files (all one-line, some over 308 px): 52541, 52589, 52603, 53121, 53125, 53352, 53368, 53904, 53908.

## Known issues

- **Save states:** loading an emulator quicksave made with a different build crashes the game (2026-10-30: invalid-handle fatal error at PC 0x12610C). Use in-game saves across builds. Data strings are still kept within the original sizes as a precaution (`tools/sizecheck.py`).

- About 5% of kanji uses in the dump are identified from the image alone (`⟨字⟩`). True homophones (態勢/体勢) and some names can be wrong. Fixes go in `script/glossary.tsv` (names) or `script/glyph_overrides.tsv` (glyphs).
- Text drawn into images is still Japanese, e.g. the 進む button, the screen titles (名前入力, 容姿・声の選択, 所属国名の入力) and the 性別/容姿/声/決定 buttons, and the START スキップ hint in cutscenes.
- The player-name tables in `code.bin` have I/J swapped. It's harmless because it round-trips, but names sent over StreetPass would show it.
- Debug file `60016` references glyphs it doesn't contain. It's ignored.

## Next steps

1. **Playtest chapter 1** (prologue through 52609). Fix wording and overflow, confirm the one-line boxes and `[x14:0000]`/`[x14:0100]`.
2. **Translate the UI text the playtest shows,** using the labels (Arata's leg-part choices, menus, Lab, Formation).
3. **Next text:** the rest of the system/UI text (01000.98: menus, battle messages, ownership announcements), then the character conversations (11xxx) and map examine text (06xxx).
4. **Graphics:** find and translate textures with baked-in Japanese (buttons, titles, menus).
5. **Packaging:** decide on the release format, either a LayeredFS folder or a patch file against the CPK. Check it on real hardware (Luma3DS).

## Future work

### Save editor (PKHeX-style)

An editor for money, LBX, parts, weapons, chips and scouted players looks feasible. This is outside the translation; give it its own folder or repo.

What a first look at a save showed (2026-10-30):

- One file per slot: `sv1.bin` / `sv2.bin`, 103,400 bytes, in Azahar's `sdmc/Nintendo 3DS/<id0>/<id1>/title/00040000/000f4000/data/00000001/`. On a real 3DS, back it up with Checkpoint or JKSM.
- It doesn't look encrypted or compressed: 64% zero bytes, plain little-endian integers, and 4 KB blocks of at most ~4.9 bits/byte of entropy.
- No CRC32 or byte-sum of the file sits in the first 0x100 bytes. A checksum could still be elsewhere; test by loading a hand-edited save.
- The player name ("T") and the country (ハーネス) don't appear as global-font glyph indices, RMD tokens, UTF-16 or Shift-JIS. Find out how strings are stored first.

Plan:

1. Map fields by diffing saves that differ by one action (buy one item, spend money, gain a level, build an LBX).
2. Check for a checksum by editing a byte and loading the save in game.
3. Show names instead of IDs. The English tables for LBX, parts, weapons, chips and Special Functions already exist in `script/en/01000_098_000203e8.tsv`.
4. Build a small editor (Python or a web page) that reads and writes `sv1.bin` and fixes any checksum.

## Log

### 2026-10-29
- Extracted the ROM. Cracked CPK (ID-only), MRON containers, and SLZ compression (4 variants, all 26,092 blobs verified).
- Found the text system: pre-rendered RMD message files plus per-file kanji atlases, a 297-glyph global font, and furigana.
- Built the script dump. Kanji identification uses furigana together with KANJIDIC2/JMdict (EDRDG) and image matching.
- Built the repacker: SLZ compressor, MRON/CPK rebuild, RMD encoder with text-region growth.
- First in-game test in Azahar: labels rendered. A black screen was wrongly blamed on stale message heights (see below).
- Measured the dialogue box. Added word wrapping and redrew `!` in all global fonts.
- Translated the opening scene, the skip prompt and the name-entry screen. All verified in-game.
- Set style decisions and the glossary. Translated the full prologue (52500–52512); its playtest is pending.
- Translated the appearance/voice screen. That build black-screened at boot.
- Added `tools/boot_test.sh` (headless Azahar) and bisected locally. The crash depended on the combination of lines, not any single one.
- Root cause: SLZ types 1/3 end each block with a `00 00` token. Our compressor omitted it, so the game decoded past the end of the system text and corrupted the heap. Fixed. The current build and a deliberately grown system text both boot.

### 2026-10-30
- Playtest up to the first patrol event: appearance and voice boxes fine, `[x14:0000]` confirmed as the country name.
- Nation spellings settled: Jenock, Rossius.
- Translated the country-name prompts (01000.98:17607, 17612) and the patrol map events (53900, 53902). Reworded the briefing's ID check (52507:30) to "ID confirmed, [var:0]. Assigned to [x14:0000]." so 8-letter names still fit two lines.
- Second playtest: the patrol chatter (52508/53900) shows in a one-line box, so wrapped lines lost their second half. Added `textfit.BOXES` (per-file box size) and shortened those lines to one line each.
- The story goes on at 52513 (the ship), not 53xxx.
- Translated the ship scenes 52513–52516. The ⟨Ｑ⟩ glyph in the dump is a full-width ０ (1⟨Ｑ⟩⟨Ｑ⟩⟨Ｑ⟩人 = 1,000 people).
- Translated chapter 1 (52517–52609) plus its mission tutorials: 1,805 lines, 9.1% (6.2% without name tags).
- Rendered the image-only digit glyphs and added them to `script/glyph_overrides.tsv` (new file): 0, 3, 4, 5, 6, 7, 8, 9, ＋, and a few kanji and brackets. Re-dumped `script/raw`. Notable fixes: ⟨日⟩ is sometimes 3 and sometimes 8 (Oasis 8, 3 blocks), and Arata's Wild Frame line is a triple jump.
- Exact repeats are reused across files (52539/53906 = 52538, 53916 = 52540, 52557 = 52556, 52591 = 52590).
- Moved the batch helpers into the project: `tools/xlate.py` (show/check/batch/reuse), `tools/glyphsheet.py`, `tools/layout.py`, and the tag list `script/speaker_names.tsv`. Sizes listed in `textfit.BOXES` are now a hard limit in the build. Before, a one-line box could still widen to the Japanese width (490 px in 52603).
- Translated chapters 2–4 (52700–53340), about 2,300 lines, using `tools/xlate.py`. Overall 20.9% (16.0% without name tags). The build is clean and boots.
- `script/speaker_names.tsv` now covers the main and recurring cast. 53920 (expression list) and 53921 (name list) are debug data and are skipped.
- Translated the ending (53341–53388) and 53901: the main story is complete.
- LBX data: weapon info lines generated from a term table (types, attributes, resistances); LBX/part names and weapons translated as base names with derived variants (Ｃ, Ⅱ, 改, color letters); chips generated from patterns; Special Functions by hand. Character lists romanized from furigana (Hepburn, given name first, long vowels dropped) plus hand-written Western names. 13260 base/operation names generated from a place table.
- `build_patch.py` now mirrors the 01000_098 translations into the 10 px copy (01000_100). Battle-chatter files 53121, 53125, 53352 and 53368 are capped at one 319 px line.
- More glyph overrides (system-text digits, α/β, 13260 kanji) and a fresh dump. Overall 50.3%.
- Crash investigation (see Known issues): shortened 160 data strings to fit the original size limits (Industrial Zone → Works, Volcanic Zone → Volcano, "Battle X!" → "VS X!", "Machine Gun" → "MG", shorter titles). Added `tools/sizecheck.py`.
- From the latest screenshots: battle speaker names (01000.98:11–273), the tutorial battle (51015), bottom-screen objective hints (01000_095, one line of up to 280 px, in `textfit.BOXES`), save-screen day labels (01540), area titles and save/load messages (01000.98:17840–17953). 52.7% overall.
- Capture announcements (01000.98:10000–10176) generated from the 13260 place table; battle log and counter menu (12xxx), with 超必殺ファンクション as "Ultimate" to keep one line; partner gift messages (01047). The gift lines carry no speaker, so each keeps the voice its Japanese implies (Kansai, posh, katakana accent). 55.8% overall. Build boots.
