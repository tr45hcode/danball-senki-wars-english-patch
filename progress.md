# Progress

English patch for **Danball Senki Wars** (3DS, CTR-P-BDNJ, title ID `00040000000F4000`).
Technical details live in [README.md](README.md). This file tracks what's done, what's next, and what we've decided.

_Last updated: 2026-11-11_

## Status at a glance

| Area | State |
|---|---|
| Unpacking the game | ✅ Done. Every layer read and verified (3DS → CPK → MRON → SLZ → text/fonts) |
| Repacking | ✅ Done. Byte-identical when nothing changes, and working in-game |
| Text format | ✅ Decoded: 905 files, 25,193 messages, all parse cleanly |
| Japanese script dump | ✅ Readable. Kanji identification 98.8% on a hand-checked sample |
| English text in-game | ✅ Working: wrapping, `!` glyph, name entry, 10 px font spacing |
| Translation | 🟡 All text areas done except placeholders and runtime-joined fragments (95.4% overall); playtesting outstanding |
| Graphics with baked-in Japanese | 🟡 409 labels in 34 atlases (39 textures with the copies) redrawn in English. Pause menu, boot notices, hint bars and help screenshots still Japanese |
| Cutscene videos (MOFLEX) | ⬜ Not started |
| Distribution (patch packaging) | 🟡 v0.1-beta closed beta out (xdelta patch against the CPK). Not tested on real hardware |

## Translation progress

Refresh with `python3 tools/progress.py`.

| Area | Translated | Total | % |
|---|---:|---:|---:|
| Story scenes | 4,560 | 5,360 | 85.1% |
| Character conversations | 3,164 | 3,180 | 99.5% |
| Map examine text | 3,635 | 3,676 | 98.9% |
| Character/LBX data | 1,728 | 1,735 | 99.6% |
| System & UI | 5,745 | 5,780 | 99.4% |
| Other | 27 | 34 | 79.4% |
| **All** | **18,859** | **19,765** | **95.4%** |

These counts cover RMD text only. Labels drawn into textures are tracked under *Graphics* in the table above.

Story scenes include the speaker name tags (filled from `script/speaker_names.tsv`). The remaining story lines are debug/placeholder text, the 53922 CG list and the 53920/53921 debug lists.

"Map examine text" counts every 06xxx container: the examine areas (065xx), the Special Function descriptions (06525/06526) and the mission map's place tables (06730). What's left there is 35 `削除` ("deleted") placeholders and 6 developer notes (`01_0280～01_0640/校門前/…`), skipped like the other debug lines.

Translated so far:
- **Prologue, 52500–52512:** opening battle, setup screens (name/appearance/country), squad briefing, movement tutorial, patrol, intro narration, opening song lyrics, and all speaker name tags.
- **Prologue map events:** patrol chatter (53900, a copy of 52508) and the item-light tutorial (53902).
- **The ship, 52513–52516:** arrival announcements, meeting Arata, the leg-parts chat (52514 repeats 52513 and adds it), and the talk after the tutorial battle. 52515 (`【01_0160】 チュートリアルバトル…`) is left as a label to see whether players ever see these scene titles.
- **Chapter 1, 52517–52609:** arrival on Kamui Island, the academy, War Time and the ERP briefing, the first mission (Oasis 8), Duck Lodge, Saruta's class, Needs City, Cafe Swallow, the Enka Ruins race and the Port Grande rescue, up to 2nd and 3rd Squads joining. Also the mission tutorials they trigger (53903–53924). Scene titles (`【01_xxxx】`, one-line files) and debug lines (`ゔケノゔ絵`) are skipped.
- **Chapters 2–4, 52700–53340:** the Bandits, Gold Valley scouting, Muraku and the truth about the Second World, the Deathwalz Brothers, the Jenock alliance and the "silent war", Rikuya and the Parasite Keys, the Death Forest and Overload, Seredi and Ezeldarm, the Dot Blastrizer, Rose City, Ayabe's betrayal and the Under Balance, the World Alliance and the Dol Garuda.
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
- **The rest of the system text (01000.98), 2026-10-31:** menus, customize and parts screens, battle orders, sort options, the shop, Lab and chip perks (6xxxx, 177xx), save/SD/StreetPass messages, multiplayer rooms and rules, formation, reward and rank-up messages, battle items and their descriptions, stage and area names (13xxx), and the remaining list names. Lines matching an already translated Japanese line elsewhere were copied (108). Left: 17534 (`位`, a rank suffix with no good English), 17348 (a lone image glyph), debug lines (8, 17993, 60016).
- **Map examine text (065xx), 2026-11-01:** all 16 areas (school gate, classroom, schoolyard, cafeteria, Infirmary, Command Room, Shopping District, Cafe Swallow, Duck Lodge outside/lobby/rec room, the player's room in both versions, ferry, Kamui Port, LBX Mound). The 007/008 files are the name tags: object labels (kept within the widest Japanese tag, 168 px) and speakers (given names, generated from the 13011 list like the story tags). The 004/005 files hold the examine descriptions, item pickups (50000+), visitor lines in your room (06511/06515.9), the map chatter (2000+, mostly the squad between story scenes), the morning greetings (10020+, copies of each character's 11xxx line 90) and copies of the scout messages.
- **Special Function descriptions (06525.5 and 06526.3, 33300–33519):** one line each, capped at 280 px in `textfit.BOXES` (the Japanese never exceeds it). 33300+k describes the Special Function named at 01000.98:48020+k, though the pairing drifts after about 33458. The second copy is filled from the first by id.
- **Mission map (06730.24/.26):** both are copies of the 13260 place table and are filled from it by id; 13260:10052 is now "Jenock Base Drill".
- **Multiplayer room help (01049.10).**
- **Texture labels, 2026-11-10:** 409 sprites in 34 atlases (`script/gfx/`). The title and system menus, save/load, the appearance and voice screen, the screen titles (Enter Name, Enter Country, Squads, Link Menu), sort and hint labels, the Lab and the Shop, Customize, the Special Function swap screen, the multiplayer lobby and rooms, the mission map (Day, War Time Cost, Defense, Reward, Terrain), the island map menu and its place names, the battle screen's bottom menu (Switch LBX, Lock-On List, All-Out Attack, Close) and the status callouts (OVERHEAT, JAMMING, FINAL BREAK CHANCE!). Five more atlases are byte-identical copies in other containers (`script/gfx/copies.tsv`) and get the same English.
- **Character conversations (11700–11922), 2026-11-01:** all 135 scoutable characters (topic chats 10–3x, the "what do you need?" opener 40, gift thanks 50, being let go 60, leaving 70, joining 80, the morning meet-up 90) and their scout/part-ways messages (60000–60006, generated with each full name from the 13011 list); the commanders (Dordkins, Ms. Higurashi, Ms. Mito, Jordan, Croskey, Portman, Iceman, Todoroki, Nomi), Ayabe, Metazawa, Instructor Saruta and the Saruta School (11911:1000–2000), Tome, the Cafe Swallow master, teachers, guards and World Saver soldiers. Only the 16 `未使用` placeholder lines are left. New names and terms are in the glossary.

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
| Release format | xdelta patch against the player's own `DA3File_3ds.cpk`, which the game picks up through LayeredFS. The release ships no game data |
| Texture labels | Fira Sans, falling back to Fira Sans Condensed and then a smaller size when space is short. Colours, outline and shadow come from the Japanese sprite. 6 px labels use a built-in pixel font. Terms match the system text ("Sortie", "Squads", "Secret" for ウラ) |
| Game art in the repo | None. The overlay PNGs hold only our English; the build wipes or clears the Japanese in the player's own textures |

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
- Redrawn textures load: the boot notice's "Next" prompt shows in English (headless Azahar screenshot, 2026-11-10), and a build with all 39 redrawn textures passes `boot_test.sh`.

## Open questions

- Can a message have more than one page? The original never uses a mid-message `[p]`. If it works, long lines could spill onto a second page instead of being cut. `--ruler` builds include a test for this, but it hasn't been checked in-game yet.
- Layout of the narration (52511) and opening lyrics (52512) boxes. They're currently wrapped like dialogue; waiting on the playtest.
- `[x14:0100]` (Josephine, 52525) is probably the player's name or a nickname made from it. To be checked in-game.
- One-line boxes: 52541, 52589, 52603, 53904 and 53908 look like mid-mission chatter, so they're kept to one line of at most 319 px (`textfit.BOXES`), which fits either box. Confirm in-game.
- How wide the map chatter box really is. Some Japanese chatter lines are far wider than the screen (53904: 490 px), so the box may scroll. Possible chatter files (all one-line, some over 308 px): 52541, 52589, 52603, 53121, 53125, 53352, 53368, 53904, 53908.
- **Fragment order (guessed, check in-game).** The game joins these to a name or number at runtime, so they carry their own spaces (the build now keeps spaces at either end of a translation): 17176, 17190, 17320/17321 (`[item] x[N] obtained!`), 17327/17328 (`[char] learned [skill]!`), 17330/17331, 17349–17352, 17358/17359, 17454, 17498, 17581, 17594–17606, 17644/17645, 17653/17654, 17675/17676, 17801/17802 (`BA Cards: [N] left`), 17872/17873, 60055–60057, 61606, 62001–62029. 62001–62029 are the same fragments as 01047.12:152–182, which stay as labels.
- **Day counter (top screen, 17900 + 1791x).** "Day" plus "(Mon)" ran off the right edge of the screen (Japanese 52 px, about 57 px fit, English needed 74). It's now `1・Mon`: 17900 is `・` and the weekdays have no brackets. 17901 "After School" (99 px vs 42) is probably in the same corner; no screenshot of it yet.
- UI labels much wider than their kanji (stat labels, sort options, tabs, stage and area names) were shortened where it was cheap (RNG, WT, Attr., bare sort keys). Whatever still overlaps will show in the next playtest.
- **Map tags and Special Function descriptions:** the examine labels (Clock Tower, Vending Machine…) are assumed to show in the speaker name box. The descriptions are assumed to be a 280 px one-line field. Check both in-game.
- **Texture labels:** apart from the boot screen's "Next", every redrawn label has been checked only in `gfx.py preview`. Narrow sprites forced abbreviations that may read badly on screen: "Vo." (声), "Recov." (受身), "Wpn A / Left", "COMMAND" (司令室 in the mission map's 5 px font).
- **Which スキップ is the cutscene hint?** Three skip sprites now say "Skip" (01100_003, 01085_003, 01047_007). Nobody has checked that one of them is the START スキップ hint in cutscenes.
- **Conversation boxes (11xxx)** are assumed to be the normal dialogue box (319 px x 2 lines) and were fitted to it. The NPC files (119xx) use a wider font, so their lines run shorter. Confirm in-game, along with the scout prompt `[x14:0200]` (assumed to be the SC price: "Scout for [x14:0200] SC?").

## Known issues

- **Save states:** loading an emulator quicksave made with a different build crashes the game (2026-10-30: invalid-handle fatal error at PC 0x12610C). Use in-game saves across builds. Data strings are still kept within the original sizes as a precaution (`tools/sizecheck.py`).
- About 5% of kanji uses in the dump are identified from the image alone (`⟨字⟩`). True homophones (態勢/体勢) and some names can be wrong. Fixes go in `script/glossary.tsv` (names) or `script/glyph_overrides.tsv` (glyphs).
- Some text drawn into textures is still Japanese: what's probably the battle pause menu (54200: あきらめる, ゲーム スピード, 普通/早い/遅い), Mission Start and the victory and defeat conditions (01002_009), the notice at boot (01100_004) and the two save-tampering warnings (01100_013, 13141), the button hint bars (せんたく, けってい, …), the team tabs (A–F チーム), the Spectating badge and the menu screenshots on the help pages (06520).
- The squad formation screen (13070) can't be redrawn: the container is 61,520 bytes, and with the new texture it outgrows the 16-bit size field of the CPK's `DataL` table. Its table is parked in `script/gfx/13070_004.tsv.disabled`.
- Some `bg=rows` badges keep a faint line where the Japanese was (the Player tag in battle, the Defense tab on the mission map).
- The player-name tables in `code.bin` have I/J swapped. It's harmless because it round-trips, but names sent over StreetPass would show it.
- Debug file `60016` references glyphs it doesn't contain. It's ignored.

## Next steps

1. **Playtest chapter 1** (prologue through 52609). Fix wording and overflow, confirm the one-line boxes and `[x14:0000]`/`[x14:0100]`.
2. **Check the new UI text in-game:** the fragment order and the day counter (Open questions), anything wider than its slot, and the redrawn texture labels (cut off, squashed, leftover Japanese).
3. **Playtest the character conversations and the map:** box size, voices, the scout/part-ways prompts, examine labels in the name box, and the Special Function description line.
4. **Remaining text:** only placeholders, debug lines and the runtime-joined fragments (see Open questions) are left. Fill the fragments once screenshots show their order.
5. **Graphics:** finish the textures listed under Known issues, and teach `cpk.py` to move a file that outgrows `DataL` into `DataH` so 13070 can be redrawn. After that, the IMAG pictures outside the UI atlases (47xxx, 48xxx, 54xxx), which nobody has looked through yet.
6. **Real hardware:** test v0.1-beta on a 3DS, either through Luma3DS LayeredFS (the steps in the release README, untested) or with a patched CIA.

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

### 2026-10-31
- Playtest screenshots (build/issues): names in some screens were garbled ("Kagetora hui", "S iren", "PohtBlank", "Guilbthe Cutter"). Cause: the 10 px global font (01500/004) draws its ASCII glyphs centred in the 10 px cell, while the game draws each cell from the pen and advances by the proportional width, so narrow letters landed on the next one. `fontpatch.py` now moves those glyphs left inside their advance. Checked by rendering the screenshot strings with the font from the built CPK; not yet seen in-game.
- "Examine anything that catches your eye." (01000.98:17922) shows in the bottom screen's one-line header, so its second line was all that showed. It's now "Examine anything of interest." and capped at 280 px x 1 line via the new per-message `textfit.MESSAGE_BOXES`.
- Day counter on the top screen ran off the edge; now `1・Mon` (see Open questions).
- The build keeps spaces at either end of a translation, for fragments the game joins to a name or number.
- Translated the rest of the system/UI text (01000.98, about 1,000 lines), the mission map's place tables (06730, from 13260) and the multiplayer room help (01049). Six Special Function names the dump had garbled were read from their katakana readings, which were shifted by 0x10 (Infinity Drive, Omega Explosion, Mega Railgun, Gao Cannon, Super Gao Cannon, Number Novem). Overall 66.9%. Build boots.

### 2026-11-01
- Translated the character conversations (11xxx): 2,235 lines of chat for 135 scoutable characters and 23 NPC files, plus 945 generated scout/part-ways messages. Voices follow the earlier choices (katakana-accented players in simple broken English, Metazawa's "-mo", posh and Kansai speakers as before). Overall 82.9%. `xlate.py check` clean, `sizecheck.py` clean, build boots.
- `fill_translations.py` now checks lines with the same limits as the build and `xlate.py check` (it used to assume the bare dialogue box and flagged 4-line system prompts that the build accepts).
- Fitting notes: about 70 characters is the practical limit for a two-line message. Hand-placed `[n]` usually costs a third line, so let the build wrap. `"` maps to a 14 px full-width glyph, and some files use a wider font, so trust `check` over character counts.
- Translated the map examine text (065xx, about 2,600 lines) and the Special Function descriptions (440 lines, two copies). Speaker tags and labels go through `sizecheck.py` now (all 16 tag files are listed there). Glyph 14_d92d9cd98d (shown as ⟨Ω⟩) is a 9, so Suzune's record is "97 fights, 97 losses" and one Special Function fires 9 special rounds. It's in `script/glyph_overrides.tsv`; `script/raw` hasn't been re-dumped yet. Overall 95.4%. Build boots.
- `xlate.py show` now keys lines by RMD index (06500.7:1000) when the file isn't the 002 dialogue file, so its output can be pasted back as shorthand.

### 2026-11-02
- Released **v0.1-beta** (closed beta) as a GitHub pre-release: a 657 KB xdelta patch against `DA3File_3ds.cpk` plus a README.txt with install steps, checksums, known issues and what to put in a bug report. A fresh build from `ce8bdf6` matches the release CPK byte for byte and passes `boot_test.sh`, and the patch rebuilds that CPK exactly. The first encode used a CPK-sized source window (`-B`) and filled RAM and swap in about 12 seconds, so systemd-oomd killed the whole terminal; the default window is enough (README, *Making a release*).
- CONTRIBUTING caught up with the beta. *Where help is needed* now asks for playtests, bug reports, fragment screenshots, a real 3DS and textures instead of the conversations and examine text, which are done. It also gained a *Fragments* section and the newer boxes (`textfit.MESSAGE_BOXES`, the Special Function line).

### 2026-11-10
- Started on the Japanese drawn into textures. The UI art lives in `UAIF` textures with a `UATD` sprite list (and `IMAG` + `ATD-` in a few places). `tools/aif.py` reads and writes the texture format, including ETC1, where it re-encodes only the 4×4 blocks under a changed sprite. Every UI texture in a format it writes round-trips byte for byte.
- `tools/gfx.py` redraws sprites from a table per atlas (`script/gfx/`). It samples the look of the Japanese label, wipes text off badges and buttons (`bg=rows`), can replace part of a sprite (`in=`), and has a 5 px pixel font for the smallest column headers. `build_patch.py` applies the tables. The overlays hold only our English; the build recomputes everything else from the player's CPK, and the output was byte-identical before and after that change.
- Translated 409 sprites in 34 atlases; with 5 identical copies, a build redraws 39 textures and passes `boot_test.sh`. A headless Azahar screenshot shows the English "Next" on the boot notice.
- 13070 (squad formation) broke the build: the container grows past the CPK's 16-bit `DataL` size limit. Its table is disabled until `cpk.py` can move the file.
