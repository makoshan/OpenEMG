#!/usr/bin/env python3
"""为 OpenEMG 五大类产品渲染图（成品图、包装图、组装图、表带图、电极图）准备只读三维资产。

严格遵守 mstack / product-render 铁律：
1. 源仓库文件 100% 只读，运行前后逐文件比对 SHA-256，打印 SOURCE_UNCHANGED。
2. KiCad 原生 PCB 经渲染副本导出 .pcb3d（保留 2032 DPI 铜纹、哑光黑阻焊、白丝印、沉金焊盘与 SMART 焊膏）。
3. STEP 几何体按子实体语义拆分导出高精度 STL（在 Blender 中以 global_scale=0.001 原坐标载入并赋真实 PBR 材质）。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import build123d as b

PRODUCT_RENDER = Path(os.environ.get(
    "PRODUCT_RENDER_DIR",
    str(Path.home() / ".local/share/mstack/skills/product-render"),
))
sys.path.insert(0, str(PRODUCT_RENDER))
import pcb_render as pr  # noqa: E402


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def move_solids(shape, dx: float, dy: float, dz: float = 0.0):
    loc = b.Location((dx, dy, dz))
    return [s.moved(loc) for s in shape.solids()]


def export_stl(shape_or_list, out_path: Path, tol: float = 0.025, ang: float = 0.12) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(shape_or_list, list):
        solids = []
        for item in shape_or_list:
            solids.extend(item.solids())
        shape = b.Compound(children=solids)
    else:
        shape = shape_or_list
    b.export_stl(shape, str(out_path), tolerance=tol, angular_tolerance=ang)


def export_pcb3d(src_pcb: Path, out_pcb3d: Path) -> dict:
    work = out_pcb3d.parent / f"_work_{src_pcb.stem}"
    if work.exists():
        shutil.rmtree(work)
    src_stage = work / "src"
    dst_stage = work / "dst"
    src_stage.mkdir(parents=True, exist_ok=True)
    dst_stage.mkdir(parents=True, exist_ok=True)

    # 在临时副本中将 KiCad 库不存在的 TQFP-32_5x5mm 指向官方库同尺寸鸥翼引脚模型 LQFP-32_5x5mm
    raw_txt = src_pcb.read_text(encoding="utf-8")
    qfp_step = pr.MODEL_LIB / "Package_QFP.3dshapes/LQFP-32_5x5mm_P0.5mm.step"
    if qfp_step.exists() and "TQFP-32_5x5mm_P0.5mm.step" in raw_txt:
        raw_txt = raw_txt.replace("TQFP-32_5x5mm_P0.5mm.step", "LQFP-32_5x5mm_P0.5mm.step")
    staged_pcb = src_stage / src_pcb.name
    staged_pcb.write_text(raw_txt, encoding="utf-8")
    for f in src_pcb.parent.iterdir():
        if f.name == src_pcb.name:
            continue
        if f.suffix == ".kicad_pro" or (f.is_dir() and (any(f.glob("**/*.st*p")) or any(f.glob("**/*.wrl")))):
            (shutil.copytree if f.is_dir() else shutil.copy2)(f, src_stage / f.name)

    copy_pcb = pr.styled_copy(staged_pcb, dst_stage, pr.MASK_BLENDER)

    subprocess.run(
        [
            pr.KICAD_PY,
            str(pr.HERE / "pcb3d_export.py"),
            str(pr.CACHE / "pcb2blender"),
            str(copy_pcb),
            str(out_pcb3d),
        ],
        check=True,
    )
    shutil.rmtree(work, ignore_errors=True)
    return {"pcb3d": str(out_pcb3d), "bytes": out_pcb3d.stat().st_size}


def main() -> None:
    repo_hw = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stl_dir = out_dir / "stls"
    pcb_dir = out_dir / "pcb3d"
    stl_dir.mkdir(exist_ok=True)
    pcb_dir.mkdir(exist_ok=True)

    tracked_sources = [
        repo_hw / "2ch-ads1292/board/ads1292-2ch.kicad_pcb",
        repo_hw / "8ch-ads1298/afe-d20-8ch/afe-d20-8ch.kicad_pcb",
        repo_hw / "16ch-c08b-round/afe-d20n/afe-d20n.kicad_pcb",
        repo_hw / "common-mainboard/adapter-p44e-xiao/p44e.kicad_pcb",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-a.kicad_pcb",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-b.kicad_pcb",
        repo_hw / "8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch.kicad_pcb",
        repo_hw / "enclosure-46x40/ads1292-shell-r7/host.step",
        repo_hw / "common-mainboard/mainboard-r4u6n/c08b-mainboard-r4u6n-3d.step",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-a-3d.step",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-b-3d.step",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_north.step",
        repo_hw / "16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_south.step",
        repo_hw / "8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch-3d.step",
        repo_hw / "8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_north.step",
        repo_hw / "8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_south.step",
        repo_hw / "8ch-ads1298/f04-openback-tpu/assembled.step",
        repo_hw / "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step",
        repo_hw / "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2.step",
        repo_hw / "16ch-c08b-round/pod-d1/pod_strip_d1.step",
        repo_hw / "16ch-c08b-round/pod-d1/pod_d1.step",
        repo_hw / "enclosure-46x40/c08b-shell-r13-notch/watch_military_green_strap.glb",
        repo_hw / "enclosure-46x40/c08b-shell-r13-notch/assembly.glb",
    ]
    hashes_before = {str(p): sha256_file(p) for p in tracked_sources}

    manifest = {"repo_hw": str(repo_hw), "pcb3d": {}, "stls": {}}

    # 1. 导出全部 .pcb3d
    pcb_targets = {
        "ads1292_2ch": repo_hw / "2ch-ads1292/board/ads1292-2ch.kicad_pcb",
        "afe_d20_8ch": repo_hw / "8ch-ads1298/afe-d20-8ch/afe-d20-8ch.kicad_pcb",
        "afe_d20n_16ch": repo_hw / "16ch-c08b-round/afe-d20n/afe-d20n.kicad_pcb",
        "p44e": repo_hw / "common-mainboard/adapter-p44e-xiao/p44e.kicad_pcb",
        "strap_a": repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-a.kicad_pcb",
        "strap_b": repo_hw / "16ch-c08b-round/strap-fpc-d2/strap-b.kicad_pcb",
        "strap_d2_8ch": repo_hw / "8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch.kicad_pcb",
    }
    for key, src in pcb_targets.items():
        out_p = pcb_dir / f"{key}.pcb3d"
        print(f"[PCB3D] {key} <- {src.name}")
        manifest["pcb3d"][key] = export_pcb3d(src, out_p)

    # 2. 拆分导出 R7 2ch 整机 STEP 子组件（保留原始整机毫米坐标）
    r7 = b.import_step(str(repo_hw / "enclosure-46x40/ads1292-shell-r7/host.step"))
    r7_contacts = []
    r7_screws = []
    for ch in list(r7.children):
        lbl = ch.label or ""
        if lbl.startswith("metal_contact_"):
            r7_contacts.extend(move_solids(ch, 0, 0, 0))
        elif lbl.startswith("pcb_screw_"):
            r7_screws.extend(move_solids(ch, 0, 0, 0))
        elif lbl in ("shell", "lid", "xiao_official", "battery_LP302025_MAX", "ffc_20P_0p5"):
            export_stl(move_solids(ch, 0, 0, 0), stl_dir / f"r7_{lbl}.stl")
    export_stl(r7_contacts, stl_dir / "r7_contacts_gold.stl")
    export_stl(r7_screws, stl_dir / "r7_screws_steel.stl")

    # 3. 拆分导出 R4U6N 缺口主控 STEP（板体居中归零以便对齐 R13 爆炸图）
    r4 = b.import_step(str(repo_hw / "common-mainboard/mainboard-r4u6n/c08b-mainboard-r4u6n-3d.step"))
    r4_bb = r4.bounding_box()
    r4_cx, r4_cy = (r4_bb.min.X + r4_bb.max.X) / 2.0, (r4_bb.min.Y + r4_bb.max.Y) / 2.0
    r4_pcb, r4_ic, r4_metal, r4_passives = [], [], [], []
    for ch in list(r4.children):
        lbl = (ch.label or "").upper()
        bb = ch.bounding_box()
        moved = move_solids(ch, -r4_cx, -r4_cy, 0)
        if bb.size.X > 38.0 and bb.size.Y > 32.0:
            r4_pcb.extend(moved)
        elif any(k in lbl for k in ("USB", "GT-USB", "U.FL", "UFL", "EVQP", "FH34")):
            r4_metal.extend(moved)
        elif any(k in lbl for k in ("QFN", "SOT", "LGA", "DFN", "SOIC", "U13", "U18")):
            r4_ic.extend(moved)
        else:
            r4_passives.extend(moved)
    if r4_pcb:
        export_stl(r4_pcb, stl_dir / "r4u6n_pcb_black.stl")
    if r4_ic:
        export_stl(r4_ic, stl_dir / "r4u6n_ic_black.stl")
    if r4_metal:
        export_stl(r4_metal, stl_dir / "r4u6n_conn_steel.stl")
    if r4_passives:
        export_stl(r4_passives, stl_dir / "r4u6n_passives_gold.stl")

    # 4. 表带软板上的镀金铜片（平移对齐各自 .pcb3d 原点）
    for key, rel in [
        ("strap_a", "16ch-c08b-round/strap-fpc-d2/strap-a-3d.step"),
        ("strap_b", "16ch-c08b-round/strap-fpc-d2/strap-b-3d.step"),
        ("strap_d2_8ch", "8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch-3d.step"),
    ]:
        shp = b.import_step(str(repo_hw / rel))
        sbb = shp.bounding_box()
        cx, cy = (sbb.min.X + sbb.max.X) / 2.0, (sbb.min.Y + sbb.max.Y) / 2.0
        discs = []
        for ch in list(shp.children):
            lbl = ch.label or ""
            if "disc_" in lbl or "pad_sq_" in lbl:
                discs.extend(move_solids(ch, -cx, -cy, 0))
        if discs:
            export_stl(discs, stl_dir / f"{key}_gold_contacts.stl")

    # 5. TPU 电极定位层、胶囊六孔外扣底盖、Pod D1 电极条/单豆、F04 连续背开口表带
    direct_steps = {
        "tpu_d2_north": "16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_north.step",
        "tpu_d2_south": "16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2_south.step",
        "tpu_8ch_north": "8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_north.step",
        "tpu_8ch_south": "8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch_south.step",
        "tray_d2": "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step",
        "cap_d2": "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2.step",
        "pod_strip_d1": "16ch-c08b-round/pod-d1/pod_strip_d1.step",
        "pod_d1": "16ch-c08b-round/pod-d1/pod_d1.step",
    }
    for key, rel in direct_steps.items():
        shp = b.import_step(str(repo_hw / rel))
        export_stl(shp, stl_dir / f"{key}.stl")

    # 6. F04 9 排连续背开口 TPU 表带拆分（TPU 主体 vs 金属圆电极片）
    f04 = b.import_step(str(repo_hw / "8ch-ads1298/f04-openback-tpu/assembled.step"))
    f04_bb = f04.bounding_box()
    f04_cx, f04_cy = (f04_bb.min.X + f04_bb.max.X) / 2.0, (f04_bb.min.Y + f04_bb.max.Y) / 2.0
    f04_tpu, f04_gold, f04_spring = [], [], []
    for ch in list(f04.children):
        lbl = ch.label or ""
        moved = move_solids(ch, -f04_cx, -f04_cy, 0)
        if "TPU_" in lbl:
            f04_tpu.extend(moved)
        elif "METAL_D9" in lbl:
            f04_gold.extend(moved)
        elif "S7231" in lbl or "stiffener" in lbl:
            f04_spring.extend(moved)
    export_stl(f04_tpu, stl_dir / "f04_tpu_body.stl")
    export_stl(f04_gold, stl_dir / "f04_gold_discs.stl")
    export_stl(f04_spring, stl_dir / "f04_springs.stl")

    # 7. 拷贝只读 GLB 装配模型到资产目录供独立渲染
    glb_dir = out_dir / "glbs"
    glb_dir.mkdir(exist_ok=True)
    for gname in ("watch_military_green_strap.glb", "assembly.glb"):
        shutil.copy2(repo_hw / "enclosure-46x40/c08b-shell-r13-notch" / gname, glb_dir / gname)

    # 8. 硬核对所有源仓库文件字节零改动
    for p in tracked_sources:
        after = sha256_file(p)
        assert after == hashes_before[str(p)], f"源文件被意外修改: {p}"
    manifest["source_files_verified"] = len(tracked_sources)
    (out_dir / "assets_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"SOURCE_UNCHANGED ({len(tracked_sources)} source files verified)")


if __name__ == "__main__":
    main()
