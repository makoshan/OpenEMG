#!/bin/zsh
# 给 rot_check.py 拉嘉立创封装和符号到 .jlc/<C号>/jlc.pretty、jlc.kicad_sym（不进仓库）。
# easyeda2kicad 要 arm64 环境（mise 的 python3 是 x86）；EasyEDA 会 403 限流，每个料间隔 8 s。
cd "$(dirname "$0")"; D=$PWD/.jlc; mkdir -p $D
[ -x $D/venv/bin/easyeda2kicad ] || { uv venv -q -p 3.12 $D/venv && VIRTUAL_ENV=$D/venv uv pip install -q easyeda2kicad; }
$D/venv/bin/python -c 'import platform; assert platform.machine() == "arm64", platform.machine()' || exit 1
for c in $(/usr/bin/python3 -c "import csv; print(' '.join(sorted({r['LCSC'] for r in csv.DictReader(open('../bom-candidate.csv', encoding='utf-8-sig')) if r['LCSC']})))"); do
  [ -n "$(find $D/$c/jlc.pretty -name '*.kicad_mod' 2>/dev/null)" ] && [ -f $D/$c/jlc.kicad_sym ] && continue
  mkdir -p $D/$c; $D/venv/bin/easyeda2kicad --footprint --symbol --lcsc_id=$c --output $D/$c/jlc --overwrite > $D/$c/pull.log 2>&1
  echo "$c $(find $D/$c/jlc.pretty -name '*.kicad_mod' 2>/dev/null | wc -l | tr -d ' ') 封装 $([ -f $D/$c/jlc.kicad_sym ] && echo 有 || echo 无)符号"; sleep 8
done
