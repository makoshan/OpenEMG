#!/bin/sh
# 表带 TPU 切片验证（Bambu Studio 02.08.02.61，X2D 0.4，Bambu TPU 95A HF），只切不打印。
# 用法：sh run.sh <空的 ASCII 临时目录>；结果写 results.json 到本目录。不在仓库里跑时用 REPO=仓库根 指定取旧版 STL 的仓库。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); W=$1; SHELL_DIR=$HERE/..
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
cd "$W"
python3 "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
python3 "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
python3 "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" p16.json
python3 "$HERE/flatten.py" process "0.08mm High Quality @BBL X2D" p08.json
python3 "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" p16a180.json 'bridge_angle="180"'
cp "$SHELL_DIR/strap_military_green_south.stl" south.stl
cp "$SHELL_DIR/strap_military_green_north.stl" north.stl
cp "$SHELL_DIR/strap_test_coupon_ch5_ch9.stl" coupon.stl
run() { tag=$1; proc=$2; shift 2; rm -rf "d_$tag"; mkdir "d_$tag"
  "$BS" --debug 2 --datadir "$PWD/d_$tag" --load-settings "$PWD/machine.json;$PWD/$proc" --load-filaments "$PWD/tpu.json" \
    --orient 0 --arrange 1 --slice 0 --export-3mf "$tag.3mf" --outputdir "$PWD" "$@" > "$tag.log" 2>&1; }
run new16 p16.json "$PWD/south.stl" "$PWD/north.stl"
run new08 p08.json "$PWD/south.stl" "$PWD/north.stl"
run new16a180 p16a180.json "$PWD/south.stl" "$PWD/north.stl"
# 推荐做法：只在内袋顶那段高度设 180（全局 180 会把生耳下那层桥也改成横跨 21 mm、两头悬空）
python3 "$HERE/add_range.py" new16.3mf new16lr.in.3mf
rm -rf d_new16lr; mkdir d_new16lr
"$BS" --debug 2 --datadir "$PWD/d_new16lr" --slice 0 --export-3mf new16lr.3mf --outputdir "$PWD" "$PWD/new16lr.in.3mf" > new16lr.log 2>&1
! grep -q "invalid object id" new16lr.log
# CH5–CH9 试样件：同样只在内袋顶设 180，切好的 3MF 拷回外壳目录，可直接发打印机
run coupon16 p16.json "$PWD/coupon.stl"
python3 "$HERE/add_range.py" coupon16.3mf coupon16lr.in.3mf 1
rm -rf d_coupon16lr; mkdir d_coupon16lr
"$BS" --debug 2 --datadir "$PWD/d_coupon16lr" --slice 0 --export-3mf coupon16lr.3mf --outputdir "$PWD" "$PWD/coupon16lr.in.3mf" > coupon16lr.log 2>&1
! grep -q "invalid object id" coupon16lr.log
cp coupon16lr.3mf "$SHELL_DIR/strap_test_coupon_ch5_ch9-X2D-TPU95A.3mf"
python3 - "$HERE" <<'PY'
import json, subprocess, sys
here = sys.argv[1]; res = {}
for t in ("new16", "new08", "new16a180", "new16lr", "coupon16", "coupon16lr"):
    b = json.loads(subprocess.check_output(["python3", f"{here}/bridges.py", f"{t}.3mf"]))
    res[t] = {"object_xy_span_mm": b["object_xy_span_mm"], "bridges": b["south_bridge_layers"], "north_bridges": b["north_bridge_layers"]}
    stls = {"new16": ["south.stl", "north.stl"], "new08": ["south.stl", "north.stl"], "coupon16lr": ["coupon.stl"]}.get(t)
    if stls:
        txt = subprocess.check_output(["python3", f"{here}/gprobe.py", f"{t}.3mf", *stls]).decode()
        res[t]["probes"] = json.loads(txt[:txt.rfind('{"roof_layer')])["probes"]
        res[t]["roof"] = json.loads(txt[txt.rfind('{"roof_layer'):])
    if t == "coupon16lr":   # 打印时间和耗料（G-code 头里 Bambu 写的估算）
        import re, zipfile
        g = zipfile.ZipFile(f"{t}.3mf").read("Metadata/plate_1.gcode").decode()[:20000]
        res[t]["estimate"] = {k: m.group(1).strip() for k, pat in (("time", r"total estimated time: ([^;\n]+)"),
                              ("filament_g", r"total filament weight \[g\] : ([\d.]+)")) if (m := re.search(pat, g))}
# 高度范围修改器写错对象编号时 Bambu 不报错、只是静默不生效：直接看床面 1.0 那层（0.16 层高下的内袋顶）必须横跨。
# 不能取「桥最多那层」：试样件桥最多的是 1.16（B 带让位顶），不加修改器也横跨，断言会恒过（复核查出）。
def roof_across(t, k):
    return res[t][k]["1.0"]["frac_along_X"] > 0.9
for t, k in (("new16lr", "bridges"), ("new16lr", "north_bridges"), ("coupon16lr", "bridges")):
    assert roof_across(t, k), ("高度范围修改器没生效", t, k, res[t][k]["1.0"])
# 对照：不加修改器的南段和试样件，同一判据必须不过（北段不加修改器本来就横跨，不算对照）
for t in ("new16", "coupon16"):
    assert not roof_across(t, "bridges"), ("断言判不出没加修改器", t, res[t]["bridges"]["1.0"])
open(f"{here}/results.json", "w").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
PY
