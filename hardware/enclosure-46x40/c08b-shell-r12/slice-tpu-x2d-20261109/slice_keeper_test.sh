#!/bin/sh
# 带圈试套件切片（Bambu Studio，X2D 0.4，Bambu TPU 95A HF，0.16 标准），只切不打印。
# 一盘：舌片试样 ×2 + 带圈 5.60（设计）/5.80/6.00 各 1。舌片和带圈都没有内部悬空，不加高度范围修改器。
# 用法：sh slice_keeper_test.sh <空的 ASCII 临时目录>；切好的 3MF 拷回外壳目录。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); W=$1; SHELL_DIR=$HERE/..
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
cd "$W"
python3 "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
python3 "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
python3 "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" p16.json
for f in strap_tongue_test strap_keeper strap_keeper_gauge_h5p8 strap_keeper_gauge_h6p0; do cp "$SHELL_DIR/$f.stl" "$f.stl"; done
cp strap_tongue_test.stl strap_tongue_test_b.stl
rm -rf d_kit; mkdir d_kit
"$BS" --debug 2 --datadir "$PWD/d_kit" --load-settings "$PWD/machine.json;$PWD/p16.json" --load-filaments "$PWD/tpu.json" \
  --orient 0 --arrange 1 --slice 0 --export-3mf kit16.3mf --outputdir "$PWD" \
  "$PWD/strap_tongue_test.stl" "$PWD/strap_tongue_test_b.stl" "$PWD/strap_keeper.stl" \
  "$PWD/strap_keeper_gauge_h5p8.stl" "$PWD/strap_keeper_gauge_h6p0.stl" > kit16.log 2>&1
cp kit16.3mf "$SHELL_DIR/strap_keeper_fit_test-X2D-TPU95A.3mf"
python3 - "$SHELL_DIR" <<'PY'
# 估时耗料 + 剪线缺口有没有真的打出来：舌片件床面 Z≈1.2 那层，外墙中心线在剪线 ±0.8 内要拐进到 |x| 9.7..10.05
# （缺口底 ±10.1 再往里收半个线宽 0.21），左右两侧、每道剪线都要有；对照：没有剪线的 Y −148..−140 段不能有这种点。
import re, sys, zipfile, json
g = zipfile.ZipFile("kit16.3mf").read("Metadata/plate_1.gcode").decode()
head = g[:20000]
est = {k: m.group(1).strip() for k, pat in (("time", r"total estimated time: ([^;\n]+)"), ("filament_g", r"total filament weight \[g\] : ([\d.]+)"))
       if (m := re.search(pat, head))}
objs = {}; cur = None; z = 0.0; x = None
for line in g.splitlines():
    m = re.match(r"; start printing object, unique label id: (\d+)", line)
    if m: cur = m.group(1); continue
    if line.startswith("; stop printing object"): cur = None; continue
    mz = re.match(r"G1 Z([\d.]+)", line)
    if mz: z = float(mz.group(1))
    m = re.match(r"G[123] (?:.*?)X([-\d.]+) Y([-\d.]+)(.*)", line)
    if m:
        if cur and " E" in m.group(3) and x is not None:
            objs.setdefault(cur, []).append((z, float(m.group(1)), float(m.group(2))))
        x = 1
marks = (-157.12, -161.61)     # build.py TRIM_MARKS 160、165；舌片试样 Y −165..−135，中心 −150
tongues = []
for k, pts in objs.items():
    xs = [p[1] for p in pts]; ys = [p[2] for p in pts]
    if abs(max(ys) - min(ys) - 29.58) > 0.3:
        continue
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
    lay = [(p[1] - cx, p[2] - cy - 150.0) for p in pts if abs(p[0] - 1.2) < 0.09]
    band = lambda y0, y1, s: [q for q in lay if 9.7 < s * q[0] < 10.05 and y0 <= q[1] <= y1]
    hit = {f"{mk}_{'+' if s > 0 else '-'}": len(band(mk - 0.8, mk + 0.8, s)) for mk in marks for s in (1, -1)}
    ctrl = len(band(-148.0, -140.0, 1)) + len(band(-148.0, -140.0, -1))
    tongues.append({"obj": k, "notch_pts": hit, "control_pts": ctrl})
ok = len(tongues) == 2 and all(min(t["notch_pts"].values()) > 0 and t["control_pts"] == 0 for t in tongues)
print(json.dumps({"estimate": est, "objects_in_gcode": len(objs), "tongue_notch_check": tongues, "notch_printed": ok}, ensure_ascii=False))
assert ok, "剪线缺口在 G-code 里没打出来，或对照段也有点"
PY
