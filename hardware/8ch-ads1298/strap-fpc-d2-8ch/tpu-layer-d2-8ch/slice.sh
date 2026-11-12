#!/bin/sh
# D2-8CH 北片 + 南片一盘平放切片，X2D 0.4，Bambu TPU 95A HF，0.16 标准。
# 用法：sh slice.sh <空的 ASCII 临时目录>；生成的含 G-code 3MF 拷回本目录。
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
W=$1
if [ -z "$W" ]; then
  echo "用法: sh slice.sh <空的 ASCII 临时目录>" >&2
  exit 1
fi
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
PY=${PY:-python3}
mkdir -p "$W"
cd "$W"
"$PY" -B "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
"$PY" -B "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
"$PY" -B "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" proc.json
command cp -f "$HERE/layer_d2_8ch_north.stl" "$HERE/layer_d2_8ch_south.stl" .
/bin/rm -rf d
mkdir d
"$BS" --debug 2 --datadir "$PWD/d" --load-settings "$PWD/machine.json;$PWD/proc.json" --load-filaments "$PWD/tpu.json" \
  --orient 0 --arrange 1 --slice 0 --export-3mf layer_8ch.3mf --outputdir "$PWD" \
  "$PWD/layer_d2_8ch_north.stl" "$PWD/layer_d2_8ch_south.stl" > slice.log 2>&1
"$PY" -B - layer_8ch.3mf <<'PY'
import json, re, sys, xml.etree.ElementTree as ET, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    bad_crc = zf.testzip()
    assert bad_crc is None, f"ZIP CRC 错误: {bad_crc}"
    names = set(zf.namelist())
    assert "Metadata/plate_1.gcode" in names, "缺少 Metadata/plate_1.gcode"
    g = zf.read("Metadata/plate_1.gcode").decode("utf-8", errors="replace")
    sinfo = zf.read("Metadata/slice_info.config").decode("utf-8", errors="replace")
hdr = g[:25000]
layers = len(re.findall(r"^; CHANGE_LAYER\b", g, flags=re.M))
root = ET.fromstring(sinfo)
objs = root.findall(".//object")
outside = [o.attrib.get("name", "") for o in objs if o.attrib.get("skipped") == "true"]
assert len(objs) == 2 and not outside, f"排盘对象异常: objs={len(objs)}, outside={outside}"
info = {
    "objects": len(objs),
    "outside_count": len(outside),
    "layers": layers,
}
for k, p in (("time", r"total estimated time: ([^;\n]+)"), ("filament_g", r"total filament weight \[g\] : ([\d.]+)")):
    if m := re.search(p, hdr):
        info[k] = m.group(1).strip()
print(json.dumps(info, ensure_ascii=False))
PY
command cp -f layer_8ch.3mf "$HERE/layer_d2_8ch-X2D-TPU95A.3mf"
