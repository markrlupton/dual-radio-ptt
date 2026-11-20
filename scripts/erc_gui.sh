#!/bin/bash
# erc_gui.sh dir proj : run KiCad 7's real ERC through eeschema under Xvfb and save the report to dir/proj-erc.rpt
D=$1; P=$2; export DISPLAY=:99
pgrep Xvfb >/dev/null || (Xvfb :99 -screen 0 1600x1000x24 >/dev/null 2>&1 &); sleep 1
pkill -f "eeschema" ; sleep 2; rm -f "$D/$P-erc.rpt"
(eeschema "$D/$P.kicad_sch" >/dev/null 2>&1 &); sleep 18
xdotool mousemove 206 12 click 1; sleep 1.5; xdotool mousemove 283 37 click 1; sleep 3
xdotool mousemove 923 540 click 1; sleep 20
xdotool mousemove 923 491 click 1; sleep 3
xdotool key ctrl+a; xdotool type --delay 20 "$D/$P-erc.rpt"; sleep 1; xdotool key Return; sleep 3
import -window root /tmp/erc/last.png
pkill -f eeschema
ls -la "$D/$P-erc.rpt" 2>/dev/null && grep -E "^\*\*|^ERC" "$D/$P-erc.rpt"
