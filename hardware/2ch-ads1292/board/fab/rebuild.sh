#!/bin/zsh
# 板改完后重出整包：绑新 blob → 拼板 → 电路表 → 转角核对 → BOM/CPL → 自检 → 拼板 DRC → 图。任一步不过就停。
# 用法：zsh rebuild.sh "这次板改了什么"。board/final.sh 每跑一次板的 uuid 都变，所以板定稿后要再跑这个。
set -e; cd "$(dirname "$0")"; [ -n "$1" ] || { echo '用法：rebuild.sh "改了什么"'; exit 1; }
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
B=$(git hash-object -w ../board/ads1292-2ch.kicad_pcb); sed -i '' "s/^BLOB, SHA = '[0-9a-f]*'/BLOB, SHA = '$B'/" make_panel.py
$KPY -B make_panel.py > panel.log 2>&1 || { tail -3 panel.log; exit 1; }
/usr/bin/python3 circ_from_design.py
[ -n "$(find .jlc -name '*.kicad_mod' 2>/dev/null | head -1)" ] || zsh pull_jlc.sh
SYMLIB=$PWD/.jlc $KPY -B rot_check.py source/ads1292-2ch.kicad_pcb $PWD/.jlc rotation.json fill.json circ.json > rot.log 2>&1 || { tail -3 rot.log; exit 1; }
/usr/bin/python3 - "$B" "$1" <<'P'
import hashlib, json, sys
rot = json.load(open('rotation.json')); bad = sorted(r for r, v in rot.items() if v['status'] not in ('ok', 'ok-人工核'))
assert not bad, f'转角没核过，不绑定：{bad}'
h = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
json.dump(dict(pcb='hardware/2ch-ads1292/board/ads1292-2ch.kicad_pcb', blob=sys.argv[1], pcb_sha256=h('source/ads1292-2ch.kicad_pcb'),
               rotation_sha256=h('rotation.json'), change=sys.argv[2]), open('rotation.source.json', 'w'), ensure_ascii=False, indent=1)
print('转角', len(rot), '件全过，绑定', sys.argv[1][:8])
P
$KPY -B make_smt.py 2>&1 | grep '^贴片'
$KPY -B check_fab.py > fab.log 2>&1 || { tail -4 fab.log; exit 1; }; tail -1 fab.log
kicad-cli pcb drc --severity-all --format json -o drc.json ads1292-2ch-panel.kicad_pcb > /dev/null 2>&1
/usr/bin/python3 -c "
import json; d = json.load(open('drc.json')); e = [v for v in d['violations'] if v['severity'] == 'error']
print('拼板 DRC 错误', len(e), '未连', len(d['unconnected_items'])); raise SystemExit(1 if e or d['unconnected_items'] else 0)"
kicad-cli pcb render --side top --width 1568 --height 1568 -o panel-top.png ads1292-2ch-panel.kicad_pcb > /dev/null 2>&1
kicad-cli pcb render --side bottom --width 1568 --height 1568 -o board-bottom.png source/ads1292-2ch.kicad_pcb > /dev/null 2>&1
# 极性图：magick 自带的 SVG 渲染会把字画坏，用无头 Chrome 截
/bin/rm -f polarity-top.png; "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --user-data-dir=$(mktemp -d) --window-size=1413,1215 --screenshot=$PWD/polarity-top.png "file://$PWD/polarity-top.svg" > /dev/null 2>&1
[ -s polarity-top.png ] && echo "图已重出" || { echo "极性图没出来"; exit 1; }
/bin/rm -f panel.log rot.log fab.log
