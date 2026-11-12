#!/bin/sh
# 南北两段表带一盘切片（Bambu Studio 02.08.02.61，X2D 0.4，Bambu TPU 95A HF，0.16 标准），只切不打印。
# 只在内袋顶那段高度（床面 Z 0.7..1.3）把桥接角设 180（add_range.py），其余高度自动——run.sh 对照过的推荐做法。
# 用法：sh slice_strap.sh <空的 ASCII 临时目录>；切好的 3MF 拷回外壳目录，核对结果写 strap_slice_check.json。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); W=$1; SHELL_DIR=$HERE/..
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
cd "$W"
python3 "$HERE/flatten.py" machine "Bambu Lab X2D 0.4 nozzle" machine.json
python3 "$HERE/flatten.py" filament "Bambu TPU 95A HF @BBL X2D 0.4 nozzle" tpu.json
python3 "$HERE/flatten.py" process "0.16mm Standard @BBL X2D" p16.json
cp "$SHELL_DIR/strap_military_green_south.stl" south.stl
cp "$SHELL_DIR/strap_military_green_north.stl" north.stl
rm -rf d_s; mkdir d_s
"$BS" --debug 2 --datadir "$PWD/d_s" --load-settings "$PWD/machine.json;$PWD/p16.json" --load-filaments "$PWD/tpu.json" \
  --orient 0 --arrange 1 --slice 0 --export-3mf s16.3mf --outputdir "$PWD" "$PWD/south.stl" "$PWD/north.stl" > s16.log 2>&1
python3 "$HERE/add_range.py" s16.3mf s16lr.in.3mf
rm -rf d_lr; mkdir d_lr
"$BS" --debug 2 --datadir "$PWD/d_lr" --slice 0 --export-3mf s16lr.3mf --outputdir "$PWD" "$PWD/s16lr.in.3mf" > s16lr.log 2>&1
! grep -q "invalid object id" s16lr.log
python3 "$HERE/check_strap_slice.py" "$HERE" s16lr.3mf s16.3mf south.stl > "$HERE/strap_slice_check.json"
cp s16lr.3mf "$SHELL_DIR/strap_military_green-X2D-TPU95A.3mf"
cat "$HERE/strap_slice_check.json"
