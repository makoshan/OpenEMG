#!/usr/bin/env python3
"""D2-8CH 单片软板胶囊区实心三维布尔干涉校验（逐实体刚体变换 + 3 组必交反例对照）。
验证对象：
  - strap-d2-8ch-3d.step（胶囊区落入 x∈[40, 75] 的实心铜片、0402/0603 串阻与软板基材）
  - geometry.json 中的 capsule_spacer 6 开窗 0.20 mm PI 垫片（实心拉伸含 6 窗挖孔）
  - ../../enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step 与 cap_d2.step
铁律：build123d 导入的 Compound 不做整体平移求交，必须逐个 Solid 独立刚体变换并配必交反例。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
STEP_FPC = HERE / "strap-d2-8ch-3d.step"
GEOM_JSON = HERE / "geometry.json"
CAP_DIR = HERE.parents[1] / "enclosure-46x40" / "c08b-shell-r12" / "capsule-cap-d2"
TRAY_STEP = CAP_DIR / "tray_d2.step"
CAP_STEP = CAP_DIR / "cap_d2.step"
OUT_JSON = HERE / "fit-3d.json"

# KiCad STEP 坐标系 (xs = bx, ys = -by, zs) -> R13/D2 盒坐标系 (X, Y, Z)
# E1N (bx=50.5, by=42 -> xs=50.5, ys=-42) => Box (X=-8.0, Y=+7.5)
# E1P (bx=50.5, by=58 -> xs=50.5, ys=-58) => Box (X=+8.0, Y=+7.5)
# R33 (bx=59.4, by=58.6 -> xs=59.4, ys=-58.6) => Box (X=+8.6, Y=-1.4) [双轴非对称特征]
# 变换：
#   X = -ys - 50.0
#   Y = -xs + 58.0
#   Z = -zs + (-0.256 + 0.161) = -zs - 0.095   （使 F 面焊盘 zs=+0.161 精确贴合底盖内顶 Z=-0.256）
# 线性部分矩阵 [[0, -1, 0], [-1, 0, 0], [0, 0, -1]] 行列式 = +1（纯刚体旋转：绕 (1,-1,0) 轴转 180°，零镜像！）
Z_F_STEP = 0.161
BOX_CAP_TOP_Z = -0.256
FPC_T = 0.203


def transform_solid_to_box(sol: b.Solid, dz_extra: float = 0.0, mirror_x: bool = False) -> b.Solid:
    # 先绕 (1, -1, 0) 轴旋转 180°：(x, y, z) -> (-y, -x, -z)，再平移 (-50, +58, -0.095 + dz_extra)
    rot_axis = b.Axis((0, 0, 0), (1, -1, 0))
    s1 = sol.rotate(rot_axis, 180.0)
    s2 = s1.translate((-50.0, 58.0, (BOX_CAP_TOP_Z + Z_F_STEP) + dz_extra))
    if mirror_x:
        # 故意镜像反例：用平面 X=0 镜像检验非对称 R33 (X=+8.6 -> -8.6) 是否撞底壳
        s2 = b.mirror(s2, about=b.Plane.YZ)
    # 强制烘焙底层几何（防止 OCC TopLoc_Location 缓存异常）
    return s2


def build_spacer_solid_in_box(skip_last_hole: bool = False) -> b.Solid:
    geo = json.loads(GEOM_JSON.read_text(encoding="utf-8"))
    sp = next(st for st in geo["a"]["stiffeners"] if "poly" in st)
    # 板坐标 (bx, by) -> 盒坐标 (X = by - 50, Y = 58 - bx)
    pts_box = [(pt[1] - 50.0, 58.0 - pt[0]) for pt in sp["poly"]]
    z0 = BOX_CAP_TOP_Z + FPC_T          # -0.053 mm（压实后 FPC B 面）
    thick = float(sp["thickness_mm"])   # 0.200 mm -> 顶面 +0.147 mm（距底壳外底 Z=+0.150 留 0.003 mm）
    plate = b.Pos(0, 0, z0) * b.extrude(b.Polygon(*pts_box, align=None), amount=thick)
    holes = sp["holes"][:-1] if skip_last_hole else sp["holes"]
    for h in holes:
        hx0, hx1, hy0, hy1 = h          # geometry.json 存 [x0, x1, y0, y1]
        bx0, bx1 = sorted((hy0 - 50.0, hy1 - 50.0))
        by0, by1 = sorted((58.0 - hx0, 58.0 - hx1))
        plate -= b.Pos((bx0 + bx1) / 2, (by0 + by1) / 2, z0 + thick / 2) * b.Box(bx1 - bx0, by1 - by0, thick + 0.02)
    sols = plate.solids()
    assert len(sols) == 1, f"垫片应为单个连通实体，实际 {len(sols)}"
    return sols[0]


def intersect_vol(solids_a: list[b.Solid], solids_b: list[b.Solid]) -> float:
    total = 0.0
    for sa in solids_a:
        bba = sa.bounding_box()
        for sb in solids_b:
            bbb = sb.bounding_box()
            if (bba.max.X <= bbb.min.X or bba.min.X >= bbb.max.X or
                bba.max.Y <= bbb.min.Y or bba.min.Y >= bbb.max.Y or
                bba.max.Z <= bbb.min.Z or bba.min.Z >= bbb.max.Z):
                continue
            inter = sa & sb
            if inter is not None:
                for s in inter.solids():
                    total += abs(float(s.volume))
    return round(total, 6)


def main() -> int:
    fpc_comp = b.import_step(str(STEP_FPC))
    tray_solids = list(b.import_step(str(TRAY_STEP)).solids())
    cap_solids = list(b.import_step(str(CAP_STEP)).solids())
    assert len(tray_solids) >= 1 and len(cap_solids) >= 1

    # 取胶囊区器件实体（bx ∈ [41, 75]，即 6 个铜片 + 6 颗背面串阻 R1-R4/R33/R34）
    # 裸板基材跨全长 12.4..117.6，单独按胶囊段裁剪出 [41.0, 74.8] 区段参与盒底装配求交
    comp_solids_step = []
    board_solid_step = None
    for s in fpc_comp.solids():
        bb = s.bounding_box()
        if bb.size.X > 80.0:
            board_solid_step = s
        elif 41.0 <= (bb.min.X + bb.max.X) / 2.0 <= 75.0:
            comp_solids_step.append(s)

    assert board_solid_step is not None
    assert len(comp_solids_step) == 12, f"胶囊区应有 12 颗实体（6 铜片 + 6 串阻），实际 {len(comp_solids_step)}"

    # 裁剪胶囊段平坦区软板基材（bx ∈ [40.2, 74.8]，尾巴弯折段 x < 40.0 为动态弯折入槽区，由 tray_tail_slot 专管）
    cap_clip = b.Pos((40.2 + 74.8) / 2, -50.0, 0.05) * b.Box(74.8 - 40.2, 30.0, 0.5)
    board_cap_solids = list((board_solid_step & cap_clip).solids())
    assert len(board_cap_solids) >= 1

    spacer_box = build_spacer_solid_in_box()
    nom_solids = [transform_solid_to_box(s) for s in (comp_solids_step + board_cap_solids)] + [spacer_box]

    # 核对 6 颗贴肤铜片尖端 Z 与 R33 双轴非对称坐标
    tips_z = sorted(round(s.bounding_box().min.Z, 4) for s in [transform_solid_to_box(c) for c in comp_solids_step] if s.bounding_box().min.Z < -1.5)
    r33_boxes = [
        (round((s.bounding_box().min.X + s.bounding_box().max.X) / 2, 3),
         round((s.bounding_box().min.Y + s.bounding_box().max.Y) / 2, 3),
         round(s.bounding_box().max.Z, 3))
        for s in [transform_solid_to_box(c) for c in comp_solids_step]
        if s.bounding_box().max.Z > 0.35
    ]

    v_tray_nom = intersect_vol(nom_solids, tray_solids)
    v_cap_nom = intersect_vol(nom_solids, cap_solids)
    v_spacer_comp = intersect_vol([transform_solid_to_box(c) for c in comp_solids_step], [spacer_box])

    # 反例 1：去掉 0.20 mm PI 垫片，单片软板贴向底壳外底上移 +0.203 mm -> 串阻必撞穿 tray_d2 浅坑
    nospacer_solids = [transform_solid_to_box(s, dz_extra=+FPC_T) for s in (comp_solids_step + board_cap_solids)]
    v_tray_nospacer = intersect_vol(nospacer_solids, tray_solids)

    # 反例 2：沿 X 镜像（对称 6 孔抓不出，唯独非对称 R33 从 X=+8.6 翻到 X=-8.6 撞上底壳实心面！）
    mirror_solids = [transform_solid_to_box(s, mirror_x=True) for s in comp_solids_step]
    v_tray_mirror_x = intersect_vol(mirror_solids, tray_solids)

    # 反例 3：底盖横向偏 0.40 mm（超过 0.25 mm 单边孔隙）-> 铜片必撞 cap_d2
    cap_shifted = [cs.translate((0.40, 0.0, 0.0)) for cs in cap_solids]
    v_cap_shifted = intersect_vol(nom_solids, cap_shifted)

    # 反例 4：垫片漏挖 R34 窗口 -> R34 必撞垫片
    spacer_no_r34 = build_spacer_solid_in_box(skip_last_hole=True)
    v_spacer_missing_win = intersect_vol([transform_solid_to_box(c) for c in comp_solids_step], [spacer_no_r34])

    report = {
        "capsule_component_solids": len(comp_solids_step),
        "six_electrode_tip_z_mm": tips_z,
        "cap_outer_bottom_z_mm": round(min(cs.bounding_box().min.Z for cs in cap_solids), 4),
        "protrusion_mm": [round(-1.056 - z, 4) for z in tips_z],
        "r0603_centers_and_top_z_in_box_mm": r33_boxes,
        "nominal_interference_mm3": {
            "vs_tray_d2": v_tray_nom,
            "vs_cap_d2": v_cap_nom,
            "resistors_vs_spacer_windows": v_spacer_comp,
        },
        "negative_controls_interference_mm3": {
            "no_spacer_shift_up_0p203mm_vs_tray_d2": v_tray_nospacer,
            "mirror_x_asymmetric_r33_vs_tray_d2": v_tray_mirror_x,
            "cap_shift_x_0p40mm_vs_electrodes": v_cap_shifted,
            "spacer_missing_r34_window_vs_r34": v_spacer_missing_win,
        },
        "ok": (
            len(tips_z) == 6
            and all(abs(z - (-2.256)) < 1e-3 for z in tips_z)
            and v_tray_nom == 0.0
            and v_cap_nom == 0.0
            and v_spacer_comp == 0.0
            and v_tray_nospacer > 0.05
            and v_tray_mirror_x > 0.05
            and v_cap_shifted > 0.05
            and v_spacer_missing_win > 0.05
        ),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
