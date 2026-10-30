#!/bin/bash
# Boot the game headlessly in a private Azahar instance and report whether it
# crashes. The user's own Azahar config, saves and log are not touched.
#
# Usage: tools/boot_test.sh [cpk | none] [seconds]
#   cpk      DA3File_3ds.cpk to load as a LayeredFS mod
#            (default: build/mods/00040000000F4000/romfs/DA3File_3ds.cpk)
#   none     boot the unmodified game
#   seconds  wall-clock time to run (default 30; ~10 s of game time with the
#            software renderer, enough to get past boot-time loading)
#
# A crash shows up in the log as a flood of "unmapped Read32" errors (the
# signature of heap corruption seen so far). Needs: azahar, the nocrypto ROM.
P=$(cd "$(dirname "$0")/.." && pwd)
S=$P/build/azahar-headless
ROM="$P/build/Danball Senki Wars (Japan) [nocrypto].3ds"
CPK=${1:-$P/build/mods/00040000000F4000/romfs/DA3File_3ds.cpk}
SECS=${2:-30}
M=$S/data/azahar-emu/load/mods/00040000000F4000/romfs

if [ ! -f "$S/config/azahar-emu/qt-config.ini" ]; then
    mkdir -p "$S/config/azahar-emu"
    if [ -f ~/.config/azahar-emu/qt-config.ini ]; then
        cp ~/.config/azahar-emu/qt-config.ini "$S/config/azahar-emu/"
    else
        : > "$S/config/azahar-emu/qt-config.ini"
    fi
    # software renderer, no audio, unlimited speed, no exit confirmation
    python3 -I - "$S/config/azahar-emu/qt-config.ini" <<'EOF'
import re, sys
p = sys.argv[1]
s = open(p).read()
for k, v in (('graphics_api', '0'), ('output_type', '1'), ('frame_limit', '0'),
             ('confirmClose', 'false'), ('use_vsync', 'false')):
    if re.search(rf'^{k}=', s, re.M):
        s = re.sub(rf'^{k}=.*$', f'{k}={v}', s, flags=re.M)
        s = re.sub(rf'^{k}\\default=.*$', f'{k}\\\\default=false', s, flags=re.M)
open(p, 'w').write(s)
EOF
fi

mkdir -p "$M"
if [ "$CPK" = none ]; then rm -f "$M/DA3File_3ds.cpk"; else ln -sfn "$(realpath "$CPK")" "$M/DA3File_3ds.cpk"; fi
L=$S/data/azahar-emu/log/azahar_log.txt
rm -f "$L"
XDG_CONFIG_HOME=$S/config XDG_DATA_HOME=$S/data QT_QPA_PLATFORM=offscreen \
    timeout -s KILL "$SECS" azahar "$ROM" >/dev/null 2>&1

mod=$(grep -c 'LayeredFS replacement' "$L" 2>/dev/null)
if grep -q 'unmapped' "$L" 2>/dev/null; then
    echo "CRASH at $(grep -m1 unmapped "$L" | cut -c2-12)s game time (mod loaded: ${mod:-0})"
    exit 1
fi
echo "OK: no crash in ${SECS}s (reached $(tail -1 "$L" | cut -c2-12)s game time, mod loaded: ${mod:-0})"
