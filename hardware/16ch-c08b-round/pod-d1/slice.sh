#!/bin/sh
# 整条 16 节一个件，平放（皮肤面朝下），X2D 0.4，Bambu TPU 95A HF，0.16 标准。
# 用法：sh slice.sh <空的 ASCII 临时目录>；3MF 拷回本目录。flatten.py 取自 R12 slice-tpu-x2d-20261109。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); W=$1
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
cd "$W"
python3 "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
python3 "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
python3 "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" proc.json
cp "$HERE/pod_strip_d1.stl" strip.stl
rm -rf d; mkdir d
"$BS" --debug 2 --datadir "$PWD/d" --load-settings "$PWD/machine.json;$PWD/proc.json" --load-filaments "$PWD/tpu.json" \
  --orient 0 --arrange 1 --slice 0 --export-3mf strip.3mf --outputdir "$PWD" "$PWD/strip.stl" > slice.log 2>&1
python3 - strip.3mf <<'PY'
import re, sys, zipfile, json
g = zipfile.ZipFile(sys.argv[1]).read("Metadata/plate_1.gcode").decode()[:20000]
print(json.dumps({k: m.group(1).strip() for k, p in (("time", r"total estimated time: ([^;\n]+)"), ("filament_g", r"total filament weight \[g\] : ([\d.]+)")) if (m := re.search(p, g))}, ensure_ascii=False))
PY
cp strip.3mf "$HERE/pod_strip_d1-X2D-TPU95A.3mf"
