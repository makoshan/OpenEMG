#!/usr/bin/env python3
"""OpenEMG 16ch 旗舰圆润超薄手表外壳（enclosure-u9-watch）全量三维布尔干涉、动作行程与最小壁厚门禁。

核验范围：
1. 逐个 Solid 独立刚体变换（det(R) = +1，严禁对 build123d Compound 整体平移求交）：
   - AFE-30P 真实贴装整板（306 solids，已剔除 32 颗空贴 DNP 0201 共模电容）
   - MCU-U9 真实 6 层 0.80 mm 满载整板（588 solids，含沉板 USB1 Z=5.396..8.556 与东侧 U1 侧按开关）
   - 双 30P 表带软板胶囊叠层（strap-30p-a + strap-30p-b 基材与铜片/串阻实体）
   - 302025 锂电池、西侧 20P 反序软排线回折环、4 颗板间绝缘支撑柱
   - 4 个单实体外壳零件（tray, cover, side_button, cap_bottom）及总装/爆炸 STEP 语法与 <=25MiB 门禁
2. 名义装配全矩阵 23 对三维布尔干涉体积断言全部严格等于 0.000000 mm³，壳体净高 9.60 mm <= 9.70 mm，
   且 6 颗盒底贴肤镀金电极尖端齐平凸出底盖 1.200 mm。
3. 真实三维布尔探针切片最小壁厚门禁（全部必须 >= 0.80 mm，含南生耳槽 Z=1.15 mm 底部薄壁必败反例）。
4. 6 项必交/必败反例对照（Negative / Positive Collision & Wall Controls）：
   - 反例 1：AFE-30P 底面 FPC3 退回旧版 2.00 mm 高连接器 -> 必撞穿 tray 底板；
   - 反例 2：未倒圆角的旧版 43.10 × 36.666 mm 直角板框 -> 必撞 tray 内腔四角圆角；
   - 反例 3：超长 28.0 mm 电芯包络 -> 必撞穿主控 26.64 × 20.90 mm 原矩形电池窗；
   - 反例 4：东侧按键帽 side_button 向内 (-X) 按入 0.70 mm 触发行程 -> 必推进 MCU-U9 U1 开关按头（> 0.30 mm³）且与上盖孔壁保持 0.000 mm³ 无卡滞；向外 (+X) 拉拽 0.35 mm -> 内侧防脱翼必被上盖内壁锁止（> 0.20 mm³）；
   - 反例 5：EB1 误装 Φ6 圆片必撞 cap_bottom 3.5×3.5 方孔，且软板沿 X 镜像后非对称 R33 必撞 tray 外底；
   - 反例 6：挖去 tray 南壁 Z=1.00..1.40 通底补厚筋退回旧版 -> 南生耳槽 Z=1.15 mm 壁厚探针必测得 0.450 mm (< 0.80 mm) 拦截。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "fit-3d.json"

_spec = importlib.util.spec_from_file_location("u9_watch_build", HERE / "build.py")
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def vol_of(shp: b.Shape | None) -> float:
    if shp is None:
        return 0.0
    return sum(abs(float(s.volume)) for s in shp.solids())


def contained_in_box(bb: b.BoundBox, bounds: tuple[float, float, float, float, float, float]) -> bool:
    x0, x1, y0, y1, z0, z1 = bounds
    return (
        bb.min.X >= x0 and bb.max.X <= x1
        and bb.min.Y >= y0 and bb.max.Y <= y1
        and bb.min.Z >= z0 and bb.max.Z <= z1
    )


def intersect_vol(
    solids_a: list[b.Solid],
    solids_b: list[b.Solid],
    verified_empty_core_for_b: tuple[float, float, float, float, float, float] | None = None,
) -> float:
    """逐对 Solid 精确三维布尔求交。"""
    bbs_b = [sb.bounding_box() for sb in solids_b]
    total = 0.0
    for sa in solids_a:
        bba = sa.bounding_box()
        if verified_empty_core_for_b is not None and contained_in_box(bba, verified_empty_core_for_b):
            continue
        for sb, bbb in zip(solids_b, bbs_b):
            if (
                bba.max.X <= bbb.min.X or bbb.max.X <= bba.min.X
                or bba.max.Y <= bbb.min.Y or bbb.max.Y <= bba.min.Y
                or bba.max.Z <= bbb.min.Z or bbb.max.Z <= bba.min.Z
            ):
                continue
            total += vol_of(sa & sb)
    return round(total, 6)


def probe_wall_thickness(part_sol: b.Solid, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, axis: str) -> float:
    """用真实三维布尔求交测量细探针盒穿过壳体实壁的实际连续壁厚（mm）。"""
    probe = mod.box(x0, x1, y0, y1, z0, z1)
    hit = part_sol & probe
    sols = list(hit.solids())
    if not sols:
        return 0.0
    best = max(sols, key=lambda s: abs(float(s.volume)))
    bb = best.bounding_box()
    return round(float({"X": bb.size.X, "Y": bb.size.Y, "Z": bb.size.Z}[axis]), 4)


def main() -> int:
    # 校验全部 6 份导出 STEP 均可由 OpenCascade 正常解析且单文件体积 <= 24.5 MB
    step_sizes: dict[str, int] = {}
    for sfn in ("tray.step", "cover.step", "side_button.step", "cap_bottom.step", "assembly.step", "exploded.step"):
        sp = HERE / sfn
        assert sp.is_file(), f"缺少 {sfn}"
        sz = sp.stat().st_size
        assert 1_000 <= sz <= 24_500_000, f"{sfn} 体积异常: {sz}"
        comp_chk = b.import_step(str(sp))
        assert len(comp_chk.solids()) >= 1, f"{sfn} 解析实体为空"
        step_sizes[sfn] = sz

    tray = list(b.import_step(str(HERE / "tray.step")).solids())
    cover = list(b.import_step(str(HERE / "cover.step")).solids())
    side_btn = list(b.import_step(str(HERE / "side_button.step")).solids())
    cap_bot = list(b.import_step(str(HERE / "cap_bottom.step")).solids())
    assert len(tray) == 1 and len(cover) == 1 and len(side_btn) == 1 and len(cap_bot) == 1

    shell_body_h = round(float(cover[0].bounding_box().max.Z - tray[0].bounding_box().min.Z), 4)
    assert shell_body_h <= 9.70, f"壳体净高 {shell_body_h} mm 超出 9.70 mm 上限"

    # 先用真实 OCC 布尔严格验证 tray / cover 中央纯空气核与壳体交集恒为 0.0
    tray_core_bounds = (-17.50, 17.50, -14.20, 14.20, 1.02, 6.14)
    cover_core_bounds = (-17.50, 17.50, -14.20, 14.20, 6.22, 8.82)
    tray_core_sol = list(mod.box(*tray_core_bounds).solids())
    cover_core_sol = list(mod.box(*cover_core_bounds).solids())
    assert intersect_vol(tray_core_sol, tray) == 0.0, "tray_core_bounds 侵入了 tray 实体"
    assert intersect_vol(cover_core_sol, cover) == 0.0, "cover_core_bounds 侵入了 cover 实体"

    afe_raw = list(b.import_step(str(mod.AFE_STEP_PATH)).solids())
    mcu_raw = list(b.import_step(str(mod.MCU_STEP_PATH)).solids())
    assert len(afe_raw) == 306, f"afe-30p-3d.step 实体数应为 306（剔除32颗DNP后），实际 {len(afe_raw)}"
    assert len(mcu_raw) == 588, f"mcu-u9-3d.step 实体数应为 588，实际 {len(mcu_raw)}"
    # 断言双板基板均为真实 0.80 mm 叠层
    assert 0.78 <= afe_raw[0].bounding_box().size.Z <= 0.83, f"AFE 基板厚异常: {afe_raw[0].bounding_box().size.Z}"
    assert 0.78 <= mcu_raw[0].bounding_box().size.Z <= 0.83, f"MCU 基板厚异常: {mcu_raw[0].bounding_box().size.Z}"

    afe_solids = [mod.transform_board_solid(s, *mod.AFE_CENTER_XY, mod.AFE_Z_BASE) for s in afe_raw]
    mcu_solids = [mod.transform_board_solid(s, *mod.MCU_CENTER_XY, mod.MCU_Z_BASE) for s in mcu_raw]
    strap_a, strap_b = mod.load_capsule_strap_solids()
    bat = [mod.build_battery_302025()]
    ffc20 = [mod.build_west_ffc20_loop()]
    standoffs = [st for _, st in mod.build_pcb_standoffs()]

    # 核验 6 颗盒底贴肤镀金电极尖端高度与方形辅点尺寸
    tips_z = sorted(round(s.bounding_box().min.Z, 4) for s in strap_a if s.bounding_box().min.Z < -1.5)
    sq_aux = sorted(
        (round(s.bounding_box().size.X, 3), round(s.bounding_box().size.Y, 3), round(s.bounding_box().size.Z, 3))
        for s in strap_a
        if s.bounding_box().min.Z < -1.5 and s.bounding_box().size.X < 4.0
    )

    # 1. 名义全矩阵 23 对三维布尔干涉核验
    nom = {
        "afe_vs_tray": intersect_vol(afe_solids, tray, tray_core_bounds),
        "afe_vs_cover": intersect_vol(afe_solids, cover, cover_core_bounds),
        "afe_vs_battery": intersect_vol(afe_solids, bat),
        "afe_vs_standoffs": intersect_vol(afe_solids, standoffs),
        "afe_vs_ffc20": intersect_vol(afe_solids, ffc20),
        "mcu_vs_tray": intersect_vol(mcu_solids, tray, tray_core_bounds),
        "mcu_vs_cover": intersect_vol(mcu_solids, cover, cover_core_bounds),
        "mcu_vs_side_button": intersect_vol(mcu_solids, side_btn),
        "mcu_vs_battery": intersect_vol(mcu_solids, bat),
        "mcu_vs_standoffs": intersect_vol(mcu_solids, standoffs),
        "mcu_vs_ffc20": intersect_vol(mcu_solids, ffc20),
        "afe_vs_mcu": intersect_vol(afe_solids, mcu_solids),
        "ffc20_vs_tray": intersect_vol(ffc20, tray),
        "ffc20_vs_cover": intersect_vol(ffc20, cover),
        "standoffs_vs_tray": intersect_vol(standoffs, tray),
        "standoffs_vs_cover": intersect_vol(standoffs, cover),
        "battery_vs_cover": intersect_vol(bat, cover, cover_core_bounds),
        "strap_ab_vs_tray": intersect_vol(strap_a + strap_b, tray),
        "strap_ab_vs_cap_bottom": intersect_vol(strap_a + strap_b, cap_bot),
        "strap_a_vs_strap_b": intersect_vol(strap_a, strap_b),
        "tray_vs_cover": intersect_vol(tray, cover),
        "tray_vs_cap_bottom": intersect_vol(tray, cap_bot),
        "cover_vs_side_button": intersect_vol(cover, side_btn),
    }

    # 2. 真实三维布尔最小壁厚探针核验（全部必须 >= 0.80 mm，适配嘉立创 8001 光敏树脂 DFM 红线）
    wall_probes = {
        "tray_floor_center_z": probe_wall_thickness(tray[0], -0.25, 0.25, -0.25, 0.25, 0.0, 2.0, "Z"),
        "tray_south_lug_wall_z1p15": probe_wall_thickness(tray[0], -0.25, 0.25, -20.5, -18.0, 1.10, 1.25, "Y"),
        "tray_south_lug_wall_z3p70": probe_wall_thickness(tray[0], -0.25, 0.25, -20.5, -18.0, 3.60, 3.80, "Y"),
        "tray_north_lug_wall_z3p70": probe_wall_thickness(tray[0], -0.25, 0.25, 18.5, 20.5, 3.60, 3.80, "Y"),
        "tray_west_groove_root_x": probe_wall_thickness(tray[0], -24.0, -21.8, -0.25, 0.25, 1.05, 1.15, "X"),
        "tray_east_below_usb_x": probe_wall_thickness(tray[0], 21.8, 24.0, -0.25, 0.25, 3.00, 3.20, "X"),
        "cover_top_ceiling_center_z": probe_wall_thickness(cover[0], -0.25, 0.25, -0.25, 0.25, 8.50, 10.0, "Z"),
        "cover_blind_boss_top_ne_z": probe_wall_thickness(cover[0], 19.55, 19.75, 16.23, 16.43, 8.50, 10.0, "Z"),
        "cover_btn_flange_east_wall_x": probe_wall_thickness(cover[0], 22.00, 23.80, -13.30, -13.10, 6.45, 6.65, "X"),
    }
    all_walls_ok = all(v >= 0.80 for v in wall_probes.values())

    # 3. 六项必交/必败反例对照
    tall_fpc3_local = list((b.Pos(23.4683, -8.82, -1.00) * b.Box(16.50, 2.85, 2.00)).solids())
    tall_fpc3_box = [mod.transform_board_solid(s, *mod.AFE_CENTER_XY, mod.AFE_Z_BASE) for s in tall_fpc3_local]
    neg1_tall_fpc3_vs_tray = intersect_vol(tall_fpc3_box, tray)

    sharp_board = list(mod.box(-21.55, 21.55, -18.333, 18.333, mod.AFE_Z_BASE, mod.AFE_Z_BASE + 0.80).solids())
    neg2_sharp_board_vs_tray = intersect_vol(sharp_board, tray)

    oversized_bat = list(mod.box(-19.80, 8.20, -4.40, 14.40, 4.80, 7.60).solids())
    neg3_oversized_bat_vs_mcu = intersect_vol(oversized_bat, mcu_solids)

    btn_pressed = [s.translate((-0.70, 0.0, 0.0)) for s in side_btn]
    btn_pulled_out = [s.translate((+0.35, 0.0, 0.0)) for s in side_btn]
    pos4_press_hits_u1_switch = intersect_vol(btn_pressed, mcu_solids)
    pos4_press_vs_cover_clear = intersect_vol(btn_pressed, cover)
    neg4_pullout_captive_stop = intersect_vol(btn_pulled_out, cover)

    wrong_eb1_round = [mod.transform_strap_solid_to_box(s, 0.161, 0.0) for s in (b.Pos(65.5, -50.0, 0.161 + 1.0) * b.Cylinder(3.0, 2.0)).solids()]
    neg5_eb1_round_vs_cap = intersect_vol(wrong_eb1_round, cap_bot)
    strap_a_mirror_x = [b.mirror(s, about=b.Plane.YZ) for s in strap_a]
    neg5_mirror_x_vs_tray = intersect_vol(strap_a_mirror_x, tray)

    # 反例 6：模拟退回旧版未补厚南壁 Z=1.00..1.40 -> 测得壁厚必掉到 0.450 mm (< 0.80 mm)
    old_thin_tray = (tray[0] - mod.box(-12.00, 12.00, -18.80, -18.35, 1.00, 1.40)).solids()[0]
    neg6_unribbed_south_wall_mm = probe_wall_thickness(old_thin_tray, -0.25, 0.25, -20.5, -18.0, 1.10, 1.25, "Y")

    all_nom_zero = all(v == 0.0 for v in nom.values())
    all_ctrls_ok = (
        neg1_tall_fpc3_vs_tray > 5.0
        and neg2_sharp_board_vs_tray > 0.20
        and neg3_oversized_bat_vs_mcu > 2.5
        and pos4_press_hits_u1_switch > 0.30
        and pos4_press_vs_cover_clear == 0.0
        and neg4_pullout_captive_stop > 0.20
        and neg5_eb1_round_vs_cap > 0.50
        and neg5_mirror_x_vs_tray > 0.05
        and 0.40 <= neg6_unribbed_south_wall_mm < 0.50
    )

    report = {
        "board_solid_counts": {"afe_30p": len(afe_solids), "mcu_u9": len(mcu_solids)},
        "shell_body_height_mm": shell_body_h,
        "step_file_sizes_bytes": step_sizes,
        "six_electrode_tip_z_mm": tips_z,
        "aux_square_blocks_size_mm": sq_aux,
        "cap_bottom_outer_z_mm": round(cap_bot[0].bounding_box().min.Z, 4),
        "electrode_protrusion_mm": [round(cap_bot[0].bounding_box().min.Z - z, 4) for z in tips_z],
        "wall_thickness_mm": wall_probes,
        "min_wall_thickness_mm": min(wall_probes.values()),
        "nominal_interference_mm3": nom,
        "controls_mm3": {
            "neg1_old_2mm_fpc3_vs_tray": neg1_tall_fpc3_vs_tray,
            "neg2_old_sharp_afe_outline_vs_tray": neg2_sharp_board_vs_tray,
            "neg3_oversized_28mm_bat_vs_mcu": neg3_oversized_bat_vs_mcu,
            "pos4_button_press_0p70mm_actuates_u1_switch": pos4_press_hits_u1_switch,
            "pos4_button_press_0p70mm_vs_cover_clearance": pos4_press_vs_cover_clear,
            "neg4_button_pullout_0p35mm_captive_stop": neg4_pullout_captive_stop,
            "neg5_eb1_wrong_round_d6_vs_cap_bottom": neg5_eb1_round_vs_cap,
            "neg5_strap_mirror_x_r33_vs_tray": neg5_mirror_x_vs_tray,
            "neg6_old_unribbed_south_wall_z1p15_mm": neg6_unribbed_south_wall_mm,
        },
        "ok": (
            len(tips_z) == 6
            and len(sq_aux) == 2
            and all(abs(z - (-2.256)) < 1e-3 for z in tips_z)
            and shell_body_h <= 9.70
            and all_walls_ok
            and all_nom_zero
            and all_ctrls_ok
        ),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
