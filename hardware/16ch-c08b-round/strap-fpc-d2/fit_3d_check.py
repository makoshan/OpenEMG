#!/usr/bin/env python3
"""D2 16 路双片表带软板（strap-a + strap-b 胶囊区叠放）实心三维布尔干涉校验（逐实体刚体变换 + 4 组必交反例对照）。
验证对象：
  - strap-a-3d.step（外层贴底盖：6 颗贴肤铜片 [4×Φ6 + 2×3×3 辅点 EB1/EB2A] + 5 颗背面串阻 R1..R4/R33 + 软板基材）
  - strap-b-3d.step（内层贴底壳外底：背面串阻 R34 + 避开 A 片串阻开窗的软板基材）
  - ../../enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step 与 cap_d2.step
铁律：build123d 导入的 Compound 不做整体平移求交，必须逐个 Solid 独立刚体变换（det(R)=+1）并配必交反例。
"""
from __future__ import annotations
import json
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
STEP_A = HERE / "strap-a-3d.step"
STEP_B = HERE / "strap-b-3d.step"

CAP_DIR = HERE.parents[1] / "enclosure-46x40" / "c08b-shell-r12" / "capsule-cap-d2"
TRAY_STEP = CAP_DIR / "tray_d2.step"
CAP_STEP = CAP_DIR / "cap_d2.step"
OUT_JSON = HERE / "fit-3d.json"

BOX_CAP_TOP_Z = -0.256
FPC_T = 0.203


def transform_solid_to_box(sol: b.Solid, z_f_step: float, dz_extra: float = 0.0, mirror_x: bool = False) -> b.Solid:
    # 绕 (1, -1, 0) 轴旋转 180°：(x, y, z) -> (-y, -x, -z)，det(R) = +1（零镜像），再平移至盒坐标
    rot_axis = b.Axis((0, 0, 0), (1, -1, 0))
    s1 = sol.rotate(rot_axis, 180.0)
    s2 = s1.translate((-50.0, 58.0, (BOX_CAP_TOP_Z + z_f_step) + dz_extra))
    if mirror_x:
        s2 = b.mirror(s2, about=b.Plane.YZ)
    return s2


def intersect_vol(solids_a: list[b.Solid], solids_b: list[b.Solid]) -> float:
    total = 0.0
    for sa in solids_a:
        bba = sa.bounding_box()
        for sb in solids_b:
            bbb = sb.bounding_box()
            if (
                bba.max.X <= bbb.min.X or bbb.max.X <= bba.min.X
                or bba.max.Y <= bbb.min.Y or bbb.max.Y <= bba.min.Y
                or bba.max.Z <= bbb.min.Z or bbb.max.Z <= bba.min.Z
            ):
                continue
            inter = sa & sb
            if inter is not None:
                for s in inter.solids():
                    total += abs(float(s.volume))
    return round(total, 6)


def split_capsule_solids(step_path: Path) -> tuple[b.Solid, list[b.Solid], float]:
    comp = b.import_step(str(step_path))
    board_solid = None
    cap_comps = []
    fcu_z_mins = []
    for s in comp.solids():
        bb = s.bounding_box()
        if bb.size.X > 80.0:
            board_solid = s
        else:
            if bb.min.Z > 0.10:
                fcu_z_mins.append(float(bb.min.Z))
            if 41.0 <= (bb.min.X + bb.max.X) / 2.0 <= 75.0:
                cap_comps.append(s)
    assert board_solid is not None, f"{step_path.name} 未找到裸板基材实体"
    assert fcu_z_mins, f"{step_path.name} 未找到 F 面贴肤器件实体"
    z_f_step = round(min(fcu_z_mins), 6)
    assert abs(z_f_step - 0.161) < 1e-4, f"{step_path.name} F 面贴装基准异常：{z_f_step}"
    return board_solid, cap_comps, z_f_step


def main() -> int:
    board_a, comps_a, z_f_a = split_capsule_solids(STEP_A)
    board_b, comps_b, z_f_b = split_capsule_solids(STEP_B)
    tray_solids = list(b.import_step(str(TRAY_STEP)).solids())
    cap_solids = list(b.import_step(str(CAP_STEP)).solids())
    assert len(tray_solids) >= 1 and len(cap_solids) >= 1
    assert len(comps_a) == 11, f"strap-a 胶囊区应有 11 颗器件实体（6 铜片 + 5 串阻），实际 {len(comps_a)}"
    assert len(comps_b) == 1, f"strap-b 胶囊区应有 1 颗器件实体（R34），实际 {len(comps_b)}"

    # 裁剪胶囊平坦区软板基材 bx ∈ [40.2, 74.8]（x < 40.0 为入壳动态弯折区）
    cap_clip = b.Pos((40.2 + 74.8) / 2, -50.0, 0.05) * b.Box(74.8 - 40.2, 30.0, 0.5)
    board_a_cap = list((board_a & cap_clip).solids())
    board_b_cap = list((board_b & cap_clip).solids())
    assert len(board_a_cap) >= 1 and len(board_b_cap) >= 1

    # A 片在底盖内侧（dz=0），B 片叠在 A 片背面与底壳外底之间（dz=+FPC_T=+0.203 mm）
    a_box = [transform_solid_to_box(s, z_f_a, dz_extra=0.0) for s in (comps_a + board_a_cap)]
    b_box = [transform_solid_to_box(s, z_f_b, dz_extra=+FPC_T) for s in (comps_b + board_b_cap)]
    all_nom = a_box + b_box

    a_comp_box = [transform_solid_to_box(s, z_f_a, dz_extra=0.0) for s in comps_a]
    b_comp_box = [transform_solid_to_box(s, z_f_b, dz_extra=+FPC_T) for s in comps_b]
    tips_z = sorted(round(s.bounding_box().min.Z, 4) for s in a_comp_box if s.bounding_box().min.Z < -1.5)
    sq_aux_sizes = sorted(
        (round(s.bounding_box().size.X, 3), round(s.bounding_box().size.Y, 3), round(s.bounding_box().size.Z, 3))
        for s in a_comp_box
        if s.bounding_box().min.Z < -1.5 and s.bounding_box().size.X < 4.0
    )

    v_vs_tray = intersect_vol(all_nom, tray_solids)
    v_vs_cap = intersect_vol(all_nom, cap_solids)
    v_a_vs_b = intersect_vol(a_box, b_box)

    # 反例 1：EB1 误挂 Φ6.0×2.0 圆铜片（复现旧 STEP 缺陷）-> 必撞 cap_d2 3.5×3.5 方孔
    wrong_eb1_step = b.Pos(65.5, -50.0, z_f_a + 1.0) * b.Cylinder(3.0, 2.0)
    v_wrong_eb1_d6 = intersect_vol([transform_solid_to_box(wrong_eb1_step, z_f_a, 0.0)], cap_solids)

    # 反例 2：B 片 EB2 正面误挂 3×3×2 铜块 -> 必顶穿叠在前面的 A 片基材
    wrong_eb2_on_b = b.Pos(50.5, -50.0, z_f_b + 1.0) * b.Box(3.0, 3.0, 2.0)
    v_wrong_eb2_b_vs_a = intersect_vol([transform_solid_to_box(wrong_eb2_on_b, z_f_b, +FPC_T)], a_box)

    # 反例 3：沿 X 镜像 -> 非对称 R33 (X=+8.6 -> -8.6) 必撞底壳外底实心面
    a_mirror_x = [transform_solid_to_box(s, z_f_a, 0.0, mirror_x=True) for s in comps_a]
    v_mirror_x = intersect_vol(a_mirror_x, tray_solids)

    # 反例 4：B 片往底壳方向多抬 +0.20 mm -> R34 必撞穿 tray_d2 浅坑底
    b_shifted_up = [transform_solid_to_box(s, z_f_b, dz_extra=+FPC_T + 0.20) for s in comps_b]
    v_b_up_vs_tray = intersect_vol(b_shifted_up, tray_solids)

    report = {
        "capsule_component_solids": {"strap_a": len(comps_a), "strap_b": len(comps_b)},
        "six_electrode_tip_z_mm": tips_z,
        "aux_square_blocks_size_mm": sq_aux_sizes,
        "cap_outer_bottom_z_mm": round(min(cs.bounding_box().min.Z for cs in cap_solids), 4),
        "protrusion_mm": [round(-1.056 - z, 4) for z in tips_z],
        "nominal_interference_mm3": {
            "ab_vs_tray_d2": v_vs_tray,
            "ab_vs_cap_d2": v_vs_cap,
            "strap_a_vs_strap_b": v_a_vs_b,
        },
        "negative_controls_interference_mm3": {
            "eb1_wrong_round_d6_vs_cap_d2": v_wrong_eb1_d6,
            "eb2_block_on_b_vs_strap_a": v_wrong_eb2_b_vs_a,
            "mirror_x_asymmetric_r33_vs_tray_d2": v_mirror_x,
            "strap_b_shift_up_0p20mm_vs_tray_d2": v_b_up_vs_tray,
        },
        "ok": (
            len(tips_z) == 6
            and len(sq_aux_sizes) == 2
            and all(abs(z - (-2.256)) < 1e-3 for z in tips_z)
            and v_vs_tray == 0.0
            and v_vs_cap == 0.0
            and v_a_vs_b == 0.0
            and v_wrong_eb1_d6 > 0.05
            and v_wrong_eb2_b_vs_a > 0.05
            and v_mirror_x > 0.05
            and v_b_up_vs_tray > 0.05
        ),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
