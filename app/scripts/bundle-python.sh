#!/bin/bash
# 把独立 Python + 采集服务要的库 + host/ 代码装进 app/build/，打包时整体放进 OpenEMG.app/Contents/Resources。
# 只带采集服务导入链要的库（numpy scipy scikit-learn pyserial；bleak 被 gesture_model、h5py 被 take_file 顶层导入）；torch、matplotlib 这些只在实验脚本里延迟导入，不带。
set -euo pipefail
cd "$(dirname "$0")/.."
PYVER=3.12.12
uv python install "$PYVER" >/dev/null
# 直接取 uv 的独立 CPython 目录；别用 uv python find（会往上层目录找，命中仓里的 .venv，打进去的就只是指回本机的虚拟环境）
SRC="$(uv python dir)/cpython-$PYVER-macos-aarch64-none"
[ ! -f "$SRC/pyvenv.cfg" ] && [ -f "$SRC/lib/python3.12/os.py" ] || { echo "不是独立 CPython：$SRC" >&2; exit 1; }
/bin/rm -rf build/python build/host build/firmware && mkdir -p build
# -L 把软链换成实体文件：打包时 packager 会把相对软链改写成指向本机的绝对路径
command cp -RL "$SRC" build/python
chmod -R u+w build/python
PY=build/python/bin/python3
# 固定核心科学计算库版本，保证打包环境与开发虚拟环境的序列化模型兼容
# scipy 1.16.3：1.15.3 有 8 个 Fortran 模块在 macOS 27 上被 dyld 拒绝加载（__thread_bss 段 offset 非零），采集服务一启动就 ImportError（2026-10-17）
uv pip install --quiet --python "$PY" --break-system-packages numpy==2.2.6 scipy==1.16.3 scikit-learn==1.7.2 pyserial==3.5 bleak==3.0.2 h5py==3.16.0
# 瘦身：标准库测试、头文件、tkinter/idle 都用不到（第三方库的 tests 不删：numpy.testing 运行时要导入 _core/tests）
SP=build/python/lib/python3.12
/bin/rm -rf "$SP"/site-packages/PyObjCTest build/python/include build/python/share "$SP"/test "$SP"/idlelib "$SP"/tkinter "$SP"/turtledemo build/python/lib/tcl* build/python/lib/tk* build/python/lib/itcl* build/python/lib/thread*
# host：只要运行时代码和设备描述，不带研究脚本、检查脚本、网页和数据
mkdir -p build/host
(cd ../host && find . -name '*.py' ! -path './research/*' ! -name 'check_*' ! -path './.venv*' ! -path './v12-captures/*' -print0 | xargs -0 -I{} rsync -R {} ../app/build/host/)
command cp -R ../host/devices build/host/
# emg_web.py 直接从 host/ 读的页面（pages 路由）：单通道 /guide 等；少了打开就是 FileNotFoundError
command cp ../host/emg_*.html ../host/emg_demo.js build/host/
for f in $(grep -o "'emg_[a-z_]*\.\(html\|js\)'" ../host/emg_web.py | tr -d "'" | sort -u); do [ -f "build/host/$f" ] || { echo "打包漏了 host/$f" >&2; exit 1; }; done
# host 按「兄弟目录 firmware/」引用 F01 编解码器与首板自检解码器：build/ 下原样摆好，仅带这两个纯 Python 单文件
mkdir -p build/firmware/offline-f01 build/firmware/c08b-bringup/tools
command cp ../firmware/offline-f01/codec.py build/firmware/offline-f01/codec.py
command cp ../firmware/c08b-bringup/tools/decode_bringup.py build/firmware/c08b-bringup/tools/decode_bringup.py
# 预编译：App 包内不可写，没有 .pyc 时每次启动都现场编译 scipy/sklearn，实测要 55 秒
"$PY" -m compileall -q -j 0 build/python/lib build/host build/firmware >/dev/null
# 自检：脱离仓库目录树模拟 Contents/Resources/{host,firmware} 导入全链路（含缺文件必败反例）
YUANLI_PY="$PY" node check-packaged-resources.mjs
# 自检：标准库必须来自包内（sys.base_prefix 在 build/python 里），不许有指向外面的软链
"$PY" -I -c "import sys, os; p = os.path.realpath(sys.base_prefix); assert p == os.path.realpath('build/python'), p"
[ -z "$(find build -type l)" ] || { echo "build/ 里还有软链" >&2; find build -type l >&2; exit 1; }
# 自检：包内每个原生库都必须能被本机 dyld 加载；系统升级后旧二进制被拒时在打包这一步就失败，不等装好才报采集服务起不来（只验打包这台机器的系统版本）
"$PY" -I - <<'PYEOF'
import ctypes, glob, sys
bad = []
for f in glob.glob('build/python/lib/**/*.so', recursive=True, include_hidden=True) + glob.glob('build/python/lib/**/*.dylib', recursive=True, include_hidden=True):   # include_hidden：wheel 自带的 .dylibs/ 目录（libgfortran、libomp 等）也要查
    if '.dSYM/' in f: continue   # 调试符号（DWARF），不是可加载的库
    try: ctypes.CDLL(f)
    except OSError as e: bad.append(f'{f}: {e}')
if bad: sys.exit('原生库加载失败 %d 个：\n' % len(bad) + '\n'.join(bad[:10]))
PYEOF
echo "python: $(du -sh build/python | cut -f1)  host: $(du -sh build/host | cut -f1)"
