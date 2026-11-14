#!/usr/bin/env python3
"""OpenEMG 3D 模型完备性与 CAD 自包含门禁（纯 Python 标准库，含 --selftest 正负双路反例自检）。

校验范围：
1. 核心 3D 资产清单存在且几何格式真实有效：
   - 16 块整板满载 -3d.step（圆孔版与配 R13 无螺丝壳的四角缺口版：2ch / 8ch单面 / 8ch台架 / 8ch双路线软板 / 16ch双面 / 16ch双路线软板 / R4U6与R4U6N主控 / P44e转接板）
   - 3 套 46×40mm 外壳家族（ads1292-shell-r7、c08b-shell-r12、c08b-shell-r13-notch 含 Fusion .f3d 源档）
   - 5 套表带/电极豆套件（tpu-layer-d2、tpu-layer-d2-8ch、capsule-cap-d2、pod-d1、f04-openback-tpu）
   - 关键连接器与模块参考 3D 源（FPC2-fh34.step、GT-USB-7014D.step、XIAO-nRF52840-v15.step）
2. 格式真伪校验（拒绝空文件、截断 STEP、坏三角网格 STL、伪造 GLB 或损坏 .3mf/.f3d 压缩包）。
3. 全仓 .kicad_pcb 的 (model "...") 路径零断链且零本机绝对路径（${KIPRJMOD}/... 必须在仓内真实存在）。
4. 全仓硬件 CAD 脚本（model.py / build.py / check.py）零残留旧内部目录引用，跨目录 Path 引用全部可解析。
"""

from __future__ import annotations

import os
import re
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED_3D_ASSETS: tuple[str, ...] = (
    # 16 块满载整板 -3d.step（含圆孔版与配 R13 无螺丝壳的四角缺口版）
    "hardware/common-mainboard/mainboard-r4u6/c08b-mainboard-r4u6-3d.step",
    "hardware/common-mainboard/mainboard-r4u6n/c08b-mainboard-r4u6n-3d.step",
    "hardware/common-mainboard/adapter-p44e-xiao/p44e-3d.step",
    "hardware/2ch-ads1292/board/ads1292-2ch-3d.step",
    "hardware/8ch-ads1298/afe-d20-8ch/afe-d20-8ch-3d.step",
    "hardware/8ch-ads1298/afe-d20n-8ch/afe-d20n-8ch-3d.step",
    "hardware/8ch-ads1298/stacked-d20-8ch/c08b-afe-d20-8ch-single-3d.step",
    "hardware/8ch-ads1298/r01-bench/v12-r01-3d.step",
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch-3d.step",
    "hardware/8ch-ads1298/f04-strap-fpc/fpc-f04-3d.step",
    "hardware/16ch-c08b-round/afe-d20/c08b-afe-d20-3d.step",
    "hardware/16ch-c08b-round/afe-d20n/c08b-afe-d20n-3d.step",
    "hardware/16ch-c08b-round/strap-fpc-d2/strap-a-3d.step",
    "hardware/16ch-c08b-round/strap-fpc-d2/strap-b-3d.step",
    "hardware/16ch-c08b-round/strap-fpc-r15/strap-a-3d.step",
    "hardware/16ch-c08b-round/strap-fpc-r15/strap-b-3d.step",
    # 连接器与模块 3D 参考源
    "hardware/8ch-ads1298/afe-d20-8ch/assembly/models/FPC2-fh34.step",
    "hardware/8ch-ads1298/afe-d20n-8ch/assembly/models/FPC2-fh34.step",
    "hardware/16ch-c08b-round/afe-d20/assembly/models/FPC2-fh34.step",
    "hardware/16ch-c08b-round/afe-d20/panel/assembly/models/FPC2-fh34.step",
    "hardware/16ch-c08b-round/afe-d20n/assembly/models/FPC2-fh34.step",
    "hardware/16ch-c08b-round/afe-d20n/panel/assembly/models/FPC2-fh34.step",
    "hardware/enclosure-46x40/c08b-shell-r12/GT-USB-7014D.step",
    "hardware/enclosure-46x40/ads1292-shell-r7/sources/XIAO-nRF52840-v15.step",
    # 2ch 外壳 R7
    "hardware/enclosure-46x40/ads1292-shell-r7/host.step",
    "hardware/enclosure-46x40/ads1292-shell-r7/shell.step",
    "hardware/enclosure-46x40/ads1292-shell-r7/lid.step",
    "hardware/enclosure-46x40/ads1292-shell-r7/ads1292-r7-shell.stl",
    "hardware/enclosure-46x40/ads1292-shell-r7/ads1292-r7-lid.stl",
    # 8/16ch 外壳 R12（四角螺丝柱版 + 胶囊端帽 D2 + 切片包）
    "hardware/enclosure-46x40/c08b-shell-r12/tray.step",
    "hardware/enclosure-46x40/c08b-shell-r12/tray.stl",
    "hardware/enclosure-46x40/c08b-shell-r12/cover.step",
    "hardware/enclosure-46x40/c08b-shell-r12/cover.stl",
    "hardware/enclosure-46x40/c08b-shell-r12/switch_plunger.step",
    "hardware/enclosure-46x40/c08b-shell-r12/switch_plunger.stl",
    "hardware/enclosure-46x40/c08b-shell-r12/assembly.step",
    "hardware/enclosure-46x40/c08b-shell-r12/assembly.glb",
    "hardware/enclosure-46x40/c08b-shell-r12/exploded.step",
    "hardware/enclosure-46x40/c08b-shell-r12/exploded.glb",
    "hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2.step",
    "hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2.stl",
    "hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step",
    "hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.stl",
    "hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2_x2-X2D-TPU95A.3mf",
    # 8/16ch 外壳 R13（四角缺口无螺丝抱柱版 + Fusion 360 .f3d 源档）
    "hardware/enclosure-46x40/c08b-shell-r13-notch/C08B-R13缺口壳-主控R4U3N-采集D20N-总装与爆炸图.f3d",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/tray.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/tray.stl",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/cover.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/cover.stl",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/switch_plunger.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/switch_plunger.stl",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/assembly.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/assembly.glb",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/exploded.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/exploded.glb",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/watch_military_green_strap.step",
    "hardware/enclosure-46x40/c08b-shell-r13-notch/watch_military_green_strap.glb",
    # 16ch 表带 TPU 开孔层 D2 与独立电极豆 Pod D1
    "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_north.step",
    "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_north.stl",
    "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_south.step",
    "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_south.stl",
    "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2-X2D-TPU95A.3mf",
    "hardware/16ch-c08b-round/pod-d1/pod_d1.step",
    "hardware/16ch-c08b-round/pod-d1/pod_strip_d1.step",
    "hardware/16ch-c08b-round/pod-d1/pod_strip_d1.stl",
    "hardware/16ch-c08b-round/pod-d1/pod_strip_d1-X2D-TPU95A.3mf",
    # 8ch 单片软板专属短版表带 TPU 开孔层 D2-8CH（含 X2D 切片包）
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_north.step",
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_north.stl",
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_south.step",
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_south.stl",
    "hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch-X2D-TPU95A.3mf",
    # 8ch 背开口连续 TPU 表带套件 F04
    "hardware/8ch-ads1298/f04-openback-tpu/assembled.step",
    "hardware/8ch-ads1298/f04-openback-tpu/loading.step",
    "hardware/8ch-ads1298/f04-openback-tpu/liner.step",
    "hardware/8ch-ads1298/f04-openback-tpu/liner-print.stl",
    "hardware/8ch-ads1298/f04-openback-tpu/shell.step",
    "hardware/8ch-ads1298/f04-openback-tpu/shell-print.stl",
    "hardware/8ch-ads1298/f04-openback-tpu/rld-shell.step",
    "hardware/8ch-ads1298/f04-openback-tpu/row.step",
    # 16ch U9 圆角主控 + 超薄双 30 针采集板：整板 3D、双 30P 软板 3D、台架壳 case-30p 与穿戴手表壳 enclosure-u9-watch
    "hardware/16ch-u9-dual30/mcu-u9-3d.step",
    "hardware/16ch-u9-dual30/afe-30p-3d.step",
    "hardware/16ch-u9-dual30/strap-fpc-30p/strap-30p-a-3d.step",
    "hardware/16ch-u9-dual30/strap-fpc-30p/strap-30p-b-3d.step",
    "hardware/16ch-u9-dual30/case-30p/Case.step",
    "hardware/16ch-u9-dual30/case-30p/Lid.step",
    "hardware/16ch-u9-dual30/case-30p/assembly.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/tray.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/tray.stl",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/cover.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/cover.stl",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/side_button.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/side_button.stl",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/cap_bottom.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/cap_bottom.stl",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/assembly.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/assembly.glb",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/exploded.step",
    "hardware/16ch-u9-dual30/enclosure-u9-watch/exploded.glb",
)

STALE_LEGACY_DIRS_RE = re.compile(
    r"(?:"
    r"ads1292-2ch-20261104|"
    r"ads1292-structure-r4-20261104|"
    r"ads1292-p44e-xiao-adapter-20261106|"
    r"c08b-clear-shell-r12-20261107|"
    r"c08b-clear-shell-r13-notch-20261108|"
    r"c08b-d17-fpc34-4l-r15-meta18-20261108|"
    r"c08b-d17-fpc34-r12-20261107|"
    r"c08b-strap-fpc-d2-20261111|"
    r"c08b-strap-fpc-d2-8ch-20261112|"
    r"c08b-strap-layer-d2-20261111|"
    r"c08b-strap-layer-d2-8ch-20261112|"
    r"c08b-capsule-plate-d2-20261111|"
    r"mainboard-r4u6-boot0-20261111|"
    r"c08b-afe-relayout-20261102|"
    r"fpc-f04-budget|"
    r"f04-row-fixed|"
    r"comfort-e23-low-spring|"
    r"manufacturing-r01"
    r")"
)

KICAD_MODEL_RE = re.compile(r'\(model\s+"([^"]+)"')
PATH_JOIN_RE = re.compile(
    r'\b(?:HERE|R|P|S)\s*(?:\.parents\[(\d+)\]|((?:\.parent)+))?\s*/\s*["\']([^"\']+)["\']'
)


def validate_3d_file(p: Path, rel: str, errors: list[str]) -> None:
    ext = p.suffix.lower()
    try:
        size = p.stat().st_size
    except OSError as exc:
        errors.append(f"无法读取 3D 文件属性 ({rel}): {exc}")
        return
    if size == 0:
        errors.append(f"3D 文件为空 ({rel})")
        return

    if ext in {".step", ".stp"}:
        head = p.read_bytes()[:4096]
        with p.open("rb") as fh:
            if size > 8192:
                fh.seek(size - 8192)
            tail = fh.read()
            fh.seek(0)
            sample = fh.read(min(size, 512 * 1024))
        if b"ISO-10303-21;" not in head:
            errors.append(f"STEP 缺少 ISO-10303-21 头部 ({rel})")
        if b"END-ISO-10303-21;" not in tail:
            errors.append(f"STEP 缺少 END-ISO-10303-21 尾部，疑似截断 ({rel})")
        if b"ADVANCED_BREP_SHAPE_REPRESENTATION" not in sample and b"MANIFOLD_SOLID_BREP" not in sample and b"SHELL_BASED_SURFACE_MODEL" not in sample:
            # 某些大 STEP 实体定义在后半段，若前 512KB 未命中再扫全文
            full = p.read_bytes()
            if b"ADVANCED_BREP_SHAPE_REPRESENTATION" not in full and b"MANIFOLD_SOLID_BREP" not in full and b"SHELL_BASED_SURFACE_MODEL" not in full:
                errors.append(f"STEP 未包含任何三维实体拓扑定义 ({rel})")

    elif ext == ".stl":
        raw = p.read_bytes()
        if raw[:5].lower() == b"solid" and b"facet normal" in raw[:4096]:
            if b"endsolid" not in raw[-1024:]:
                errors.append(f"ASCII STL 缺少 endsolid 结尾 ({rel})")
        else:
            if size < 84:
                errors.append(f"二进制 STL 小于 84 字节头部 ({rel})")
                return
            (tri_count,) = struct.unpack("<I", raw[80:84])
            expected = 84 + 50 * tri_count
            if tri_count < 4 or expected != size:
                errors.append(f"二进制 STL 三角面数与文件长度不匹配 (tris={tri_count}, expected={expected}, actual={size}): {rel}")

    elif ext == ".glb":
        with p.open("rb") as fh:
            hdr = fh.read(12)
        if len(hdr) < 12:
            errors.append(f"GLB 小于 12 字节头部 ({rel})")
            return
        magic, version, total_len = struct.unpack("<4sII", hdr)
        if magic != b"glTF" or version != 2 or total_len != size:
            errors.append(f"GLB 头部校验失败 (magic={magic!r}, v={version}, len={total_len} vs {size}): {rel}")

    elif ext in {".3mf", ".f3d"}:
        try:
            with zipfile.ZipFile(p, "r") as zf:
                names = zf.namelist()
                if not names:
                    errors.append(f"归档容器为空 ({rel})")
        except zipfile.BadZipFile as exc:
            errors.append(f"3D 归档容器损坏 ({rel}): {exc}")


def check_kicad_pcb_models(pcb: Path, root: Path, errors: list[str]) -> None:
    rel_pcb = pcb.relative_to(root)
    txt = pcb.read_text("utf-8", errors="replace")
    pcb_dir = pcb.parent
    for m in KICAD_MODEL_RE.finditer(txt):
        mpath = m.group(1).strip()
        if mpath.startswith(("/Users/", "/home/", "/tmp/", "/private/", "C:\\", "D:\\")):
            errors.append(f"PCB 含本机绝对 3D 模型路径 ({mpath}): {rel_pcb}")
            continue
        if mpath.startswith("${KICAD"):
            # KiCad 官方标准库变量，跨平台合法
            continue
        if mpath.startswith("${KIPRJMOD}/"):
            sub = mpath[len("${KIPRJMOD}/"):]
            target = (pcb_dir / sub).resolve()
        else:
            target = (pcb_dir / mpath).resolve()
        if not target.is_file() or target.stat().st_size == 0:
            errors.append(f"PCB 本地 3D 模型路径断链 ({mpath} -> 缺失): {rel_pcb}")


def check_cad_py_self_contained(py_file: Path, root: Path, errors: list[str]) -> None:
    rel_py = py_file.relative_to(root)
    txt = py_file.read_text("utf-8", errors="replace")
    # 去注释行后检查是否残留旧目录路径字面量
    code_lines = [ln.split("#", 1)[0] for ln in txt.splitlines()]
    code_only = "\n".join(code_lines)
    m_old = STALE_LEGACY_DIRS_RE.search(code_only)
    if m_old:
        errors.append(f"CAD/硬件脚本残留旧仓目录引用 ({m_old.group(0)!r}): {rel_py}")

    # 检查形如 R.parent / "foo" 或 HERE.parents[1] / "bar" 的跨目录引用（仅检查含上跳 parent/parents 的静态输入路径）
    py_dir = py_file.parent
    for pm in PATH_JOIN_RE.finditer(code_only):
        idx_s, dots, target_rel = pm.group(1), pm.group(2), pm.group(3)
        if idx_s is None and not dots:
            continue
        up = (int(idx_s) + 1) if idx_s is not None else dots.count(".parent")
        base = py_dir
        for _ in range(up):
            base = base.parent
        cand = (base / target_rel).resolve()
        if not cand.exists():
            errors.append(f"脚本跨目录引用目标不存在 ({pm.group(0).strip()} -> {cand}): {rel_py}")


def check_repo(root: Path, require_manifest: bool = True) -> list[str]:
    errors: list[str] = []
    if require_manifest:
        for rel_str in REQUIRED_3D_ASSETS:
            fp = root / rel_str
            if not fp.is_file():
                errors.append(f"缺失核心开源 3D 资产: {rel_str}")

    hw_root = root / "hardware"
    if not hw_root.exists():
        return errors

    for dirpath, dirnames, filenames in os.walk(hw_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules"}]
        dp = Path(dirpath)
        for fn in sorted(filenames):
            p = dp / fn
            rel = str(p.relative_to(root))
            ext = p.suffix.lower()
            if ext in {".step", ".stp", ".stl", ".glb", ".3mf", ".f3d"}:
                validate_3d_file(p, rel, errors)
            elif ext == ".kicad_pcb":
                check_kicad_pcb_models(p, root, errors)
            elif ext == ".py":
                check_cad_py_self_contained(p, root, errors)

    return errors


VALID_MINI_STEP = (
    "ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n"
    "#10=MANIFOLD_SOLID_BREP('Body',#11);\n"
    "ENDSEC;\nEND-ISO-10303-21;\n"
)


def run_selftest() -> int:
    """正负双路自检：干净最小仓通过 + 4 类必失败反例全部命中。"""
    with tempfile.TemporaryDirectory(prefix="openemg-3d-gate-test-") as td:
        root = Path(td)
        hw = root / "hardware/demo"
        hw.mkdir(parents=True)
        good_step = hw / "part.step"
        good_step.write_text(VALID_MINI_STEP, encoding="utf-8")
        good_pcb = hw / "demo.kicad_pcb"
        good_pcb.write_text('(kicad_pcb (footprint "U1" (model "${KIPRJMOD}/part.step")))\n', encoding="utf-8")
        good_py = hw / "build.py"
        good_py.write_text('from pathlib import Path\nP = Path(__file__).resolve().parent\nx = P.parent / "demo"\n', encoding="utf-8")

        base_errs = check_repo(root, require_manifest=False)
        if base_errs:
            print(f"SELFTEST FAIL: 干净最小基线不应报错: {base_errs}", file=sys.stderr)
            return 1

        # 反例 1：开启完整清单检查时缺失核心 -3d.step 必红
        miss_errs = check_repo(root, require_manifest=True)
        if not any("缺失核心开源 3D 资产" in e for e in miss_errs):
            print(f"SELFTEST FAIL: 反例 1 未捕获核心 3D 资产缺失: {miss_errs}", file=sys.stderr)
            return 1

        # 反例 2：截断假 STEP + 损坏二进制 STL 必红
        bad_step = hw / "truncated.step"
        bad_step.write_text("ISO-10303-21;\nHEADER;\n", encoding="utf-8")
        bad_stl = hw / "corrupt.stl"
        bad_stl.write_bytes(b"\x00" * 80 + struct.pack("<I", 10) + b"\x00" * 50)  # 声明 10 面但只有 1 面数据
        fmt_errs = check_repo(root, require_manifest=False)
        bad_step.unlink()
        bad_stl.unlink()
        if not (any("缺少 END-ISO-10303-21 尾部" in e for e in fmt_errs) and any("二进制 STL 三角面数与文件长度不匹配" in e for e in fmt_errs)):
            print(f"SELFTEST FAIL: 反例 2 未捕获截断 STEP 或坏 STL: {fmt_errs}", file=sys.stderr)
            return 1

        # 反例 3：.kicad_pcb 含断链 ${KIPRJMOD}/missing.step 必红
        good_pcb.write_text('(kicad_pcb (footprint "J1" (model "${KIPRJMOD}/missing.step")))\n', encoding="utf-8")
        pcb_errs = check_repo(root, require_manifest=False)
        good_pcb.write_text('(kicad_pcb (footprint "U1" (model "${KIPRJMOD}/part.step")))\n', encoding="utf-8")
        if not any("PCB 本地 3D 模型路径断链" in e for e in pcb_errs):
            print(f"SELFTEST FAIL: 反例 3 未捕获 PCB 3D 路径断链: {pcb_errs}", file=sys.stderr)
            return 1

        # 反例 4：CAD 脚本跨目录引用不存在目录必红
        good_py.write_text('from pathlib import Path\nP = Path(__file__).resolve().parent\nx = P.parent / "nonexistent-sibling"\n', encoding="utf-8")
        py_errs = check_repo(root, require_manifest=False)
        good_py.write_text('from pathlib import Path\nP = Path(__file__).resolve().parent\nx = P.parent / "demo"\n', encoding="utf-8")
        if not any("脚本跨目录引用目标不存在" in e for e in py_errs):
            print(f"SELFTEST FAIL: 反例 4 未捕获 CAD 脚本断链目录: {py_errs}", file=sys.stderr)
            return 1

    print("check_3d_completeness selftest: 4/4 必失败反例全部拦截，干净基线通过")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return run_selftest()
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errs = check_repo(target, require_manifest=True)
    if errs:
        print(f"3D 完备性与 CAD 自包含门禁失败（共 {len(errs)} 项）：", file=sys.stderr)
        for e in errs[:50]:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"3D 完备性与 CAD 自包含门禁通过：{target}（{len(REQUIRED_3D_ASSETS)} 项核心 3D 资产齐备，PCB/CAD 0 断链）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
