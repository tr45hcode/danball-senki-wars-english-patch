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
#
# On Windows (Git Bash) it copies the Azahar install (AZAHAR_DIR, default
# C:\Program Files\Azahar) into build/azahar-headless/app once and runs it in
# portable mode, which keeps config, saves and log in app/user. The log there
# goes quiet after the save-data check at 2-4 s, patched or not, so "reached"
# reads lower than on Linux. QPA=windows shows the window instead.
P=$(cd "$(dirname "$0")/.." && pwd)
S=$P/build/azahar-headless
ROM="$P/build/Danball Senki Wars (Japan) [nocrypto].3ds"
CPK=${1:-$P/build/mods/00040000000F4000/romfs/DA3File_3ds.cpk}
SECS=${2:-30}
case $(uname -s) in
MINGW* | MSYS* | CYGWIN*)
    if [ ! -f "$S/app/azahar.exe" ]; then
        mkdir -p "$S/app/user"
        cp -r "${AZAHAR_DIR:-/c/Program Files/Azahar}"/. "$S/app/"
    fi
    C=$S/app/user/config
    D=$S/app/user
    MINE=$(cygpath -u "$APPDATA")/Azahar/config/qt-config.ini
    AZAHAR=$S/app/azahar.exe
    ROM=$(cygpath -w "$ROM")
    PY=python
    LINK='ln -f'   # a hard link: Git Bash's ln -s copies the 1 GB file instead
    ;;
*)
    C=$S/config/azahar-emu
    D=$S/data/azahar-emu
    MINE=~/.config/azahar-emu/qt-config.ini
    AZAHAR=azahar
    PY=python3
    LINK='ln -sfn'
    ;;
esac
M=$D/load/mods/00040000000F4000/romfs

if [ ! -f "$C/qt-config.ini" ]; then
    mkdir -p "$C"
    if [ -f "$MINE" ]; then
        cp "$MINE" "$C/"
    else
        : > "$C/qt-config.ini"
    fi
    # software renderer, no audio, unlimited speed, no exit confirmation
    $PY -I - "$C/qt-config.ini" <<'EOF'
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
rm -f "$M/DA3File_3ds.cpk"
if [ "$CPK" != none ]; then $LINK "$(realpath "$CPK")" "$M/DA3File_3ds.cpk"; fi
L=$D/log/azahar_log.txt
rm -f "$L"
XDG_CONFIG_HOME=$S/config XDG_DATA_HOME=$S/data QT_QPA_PLATFORM=${QPA:-offscreen} \
    timeout -s KILL "$SECS" "$AZAHAR" "$ROM" >/dev/null 2>&1

mod=$(grep -c 'LayeredFS replacement' "$L" 2>/dev/null)
if [ ! -f "$L" ] || grep -q 'Failed to obtain loader' "$L"; then
    echo "NO BOOT: the game didn't load (see $L)"
    exit 2
fi
if grep -q 'unmapped' "$L" 2>/dev/null; then
    echo "CRASH at $(grep -m1 unmapped "$L" | cut -c2-12)s game time (mod loaded: ${mod:-0})"
    exit 1
fi
echo "OK: no crash in ${SECS}s (reached $(tail -1 "$L" | cut -c2-12)s game time, mod loaded: ${mod:-0})"
