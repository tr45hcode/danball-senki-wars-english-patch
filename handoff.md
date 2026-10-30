# Handoff for 2026-10-30

Where we stopped, and what to do first tomorrow. Background: [progress.md](progress.md) (status, decisions, log) and [README.md](README.md) (formats, tools).

## State at end of day

- **Installed build:** prologue (52500–52512), skip prompt, name entry and appearance screen translated, built with `--test-ids` (untranslated text shows `container.index:id` labels). It's linked into Azahar's mods folder.
- **Boot crash fixed:** our SLZ compressor was missing the `00 00` end-of-block token. The fixed build passes `tools/boot_test.sh`, but **you haven't confirmed it in the GUI yet**.
- **Translation:** 164 / 19,765 messages (0.8%).

## First thing tomorrow

1. Boot `build/Danball Senki Wars (Japan) [nocrypto].3ds` in Azahar and check:
   - The appearance screen shows "Choose your appearance.", Male/Female, Type 1–10. Check the numbers count up in order (they were reconstructed from glyph shapes).
   - What the **voice** box shows. If it's a label, note the ID.
   - Play the rest of the prologue: the country-name screen, the briefing/tutorial (52507), the patrol (52508–52510), the narration (52511) and the opening lyrics (52512).
2. Note for each screen:
   - wording that reads badly or is out of character
   - overflow or cut-off text, especially the narration and lyrics, which may use different boxes from dialogue
   - every `01000.98:xxxxx`-style label (untranslated UI the prologue uses)
   - whether `[x14:0000]` really shows the country name (52507 lines 30 and 40)

## Then

1. Fix whatever the playtest turns up, and translate the labelled UI lines from `01000_098_000203e8`.
2. Continue the story: the 53xxx scenes in order. Find which come right after the prologue by playing on with the `--test-ids` build and noting labels.
3. Decide the two provisional nation spellings, **Genock** and **Rossius**, and update `script/glossary.tsv`.

## How to work

```sh
# translate: write a batch file (file<TAB>id<TAB>english), merge and check fit
python3 tools/fill_translations.py batch.tsv

# build (test labels on) + automatic boot check before any GUI playtest
python3 tools/build_patch.py --test-ids extracted/romfs/DA3File_3ds.cpk build/mods
tools/boot_test.sh                 # must say OK; CRASH = don't hand the build out

python3 tools/progress.py          # refresh the table in progress.md
```

Rules of thumb:
- Dialogue: 319 px per line, 2 lines per message. The wrapper handles it; overflow goes to `build/mods/text_report.txt`.
- Follow `script/glossary.tsv`.
  - Names: romanized, given name first, no macrons.
  - Honorifics: localized.
- Keep control tags from the Japanese: `[var:0]` (player name), `[x14:0000]` (country), `[c:01]…[x2]` (narration).
- Readings for names come from the furigana (`{漢字|かな}`), not the kanji. A few kanji in the dump are still wrong.
- Before playtesting, always run `tools/boot_test.sh`.

## Open questions (not blocking)

- Can a message have a second page (mid-message `[p]`)? `--ruler` builds test it; it isn't checked in-game yet.
- Layout of the narration (52511) and lyrics (52512) boxes.
- `A/1` name keyboard: works, but the code.bin name tables have I/J swapped. Harmless unless names go over StreetPass.

## Gotchas

- Use the `[nocrypto]` ROM copy, not the original (the NoCrypto flag is missing).
- Azahar ignores SIGTERM when crash-looping: use `timeout -s KILL`, and don't `pkill -f` with a pattern that appears in your own command line.
- Kanji tools need the venv: `.venv/bin/python tools/identify_kanji.py …`.
- `build/` contains 1–2 GB outputs; `build/azahar-headless/` is the private test instance used by `boot_test.sh`.
