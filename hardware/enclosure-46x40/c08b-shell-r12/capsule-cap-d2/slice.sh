#!/bin/sh
# 底盖一盘打 2 个（1 个备用），正面朝下、裙边朝上，X2D 0.4，Bambu TPU 95A HF，0.08 高质量。
# 底壳 tray_d2.stl 走嘉立创 8001 光固化（同 R13），不在这里切。用法：sh slice.sh <空的 ASCII 临时目录>。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); W=$1
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
cd "$W"
python3 "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
python3 "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
python3 "$HERE/flatten.py" process "0.08mm High Quality @BBL X2D" proc.json
cp "$HERE/cap_d2.stl" p1.stl; cp "$HERE/cap_d2.stl" p2.stl
rm -rf d; mkdir d
"$BS" --debug 2 --datadir "$PWD/d" --load-settings "$PWD/machine.json;$PWD/proc.json" --load-filaments "$PWD/tpu.json" \
  --orient 0 --arrange 1 --slice 0 --export-3mf plate.3mf --outputdir "$PWD" "$PWD/p1.stl" "$PWD/p2.stl" > slice.log 2>&1
python3 - plate.3mf <<'PY'
import re, sys, zipfile, json
g = zipfile.ZipFile(sys.argv[1]).read("Metadata/plate_1.gcode").decode()[:20000]
print(json.dumps({k: m.group(1).strip() for k, p in (("time", r"total estimated time: ([^;\n]+)"), ("filament_g", r"total filament weight \[g\] : ([\d.]+)")) if (m := re.search(p, g))}, ensure_ascii=False))
PY
cp plate.3mf "$HERE/cap_d2_x2-X2D-TPU95A.3mf"
