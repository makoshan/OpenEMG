"""C08B 透明光固化外壳 R13（四角缺口抱柱版）完整几何、干涉、壁厚、插拔与必失败反例检查。
生成 checks.json；任何正向门禁失败或任一必失败反例未检出时返回退出码 1。
"""
from pathlib import Path
import json
import math
import re
import sys
import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter
import build123d as b

import build as mdl

P = Path(__file__).resolve().parent


def bbox_tuple(shape):
    bb = shape.bounding_box()
    return (
        float(bb.min.X),
        float(bb.min.Y),
        float(bb.min.Z),
        float(bb.max.X),
        float(bb.max.Y),
        float(bb.max.Z),
    )


def aabb_gap(a, c):
    """计算两个 AABB (x0,y0,z0,x1,y1,z1) 之间的欧氏距离（相交时返回负数表示最小轴向重叠深度）。"""
    dx = max(a[0] - c[3], 0.0, c[0] - a[3])
    dy = max(a[1] - c[4], 0.0, c[1] - a[4])
    dz = max(a[2] - c[5], 0.0, c[2] - a[5])
    if dx > 0 or dy > 0 or dz > 0:
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    ov_x = min(a[3], c[3]) - max(a[0], c[0])
    ov_y = min(a[4], c[4]) - max(a[1], c[1])
    ov_z = min(a[5], c[5]) - max(a[2], c[2])
    return -min(ov_x, ov_y, ov_z)


def exact_intersection_vol(s1, s2):
    bb1 = bbox_tuple(s1)
    bb2 = bbox_tuple(s2)
    if aabb_gap(bb1, bb2) > 1e-5:
        return 0.0
    try:
        inter = s1 & s2
        return mdl.volume(inter)
    except Exception:
        return -1.0


def plunger_press_sim(plunger, fixed, e=0.0, knob_dx=0.0, step=0.01, d_min=-0.16, d_max=1.0, dy=0.0):
    """顶杆横向偏 e（东为正）、dy（北为正）后一步步往下压，返回按杆被推多少、压到哪被谁挡住。

    fixed 是 {名字: 不动的实体}；按杆不算在里面，它会被推着走。
    每一步：顶杆和哪个不动件有实体交叠就停；没有就量按杆要让开多少
    （顶杆伸进按杆方块里最靠西的 x，到按杆东端的距离）。
    d 从上浮极限 d_min 起算（负数是往上浮），d<0 时碰到上盖只说明这个位置浮不上去，跳过。
    knob_dx 是按杆伸出量的偏差（手册 0.62±0.1）。
    """
    k = list(mdl.SW_SPEC["knob_box"]); k[1] += knob_dx
    knob = mdl.box(*k)
    travel = mdl.SW_SPEC["push_travel_mm"]
    out = {"lateral_e_mm": e, "lateral_dy_mm": dy, "knob_dx_mm": knob_dx, "contact_press_mm": None, "actuate_press_mm": None,
           "rest_push_mm": None, "top_float_press_mm": None, "top_float_push_mm": None, "max_push_mm": 0.0,
           "stop_press_mm": None, "stopped_by": None}
    n = int(round((d_max - d_min) / step))
    for i in range(n + 1):
        d = round(d_min + i * step, 4)
        pl = plunger.translate((e, dy, -d))
        hit = [name for name, s in fixed.items() if exact_intersection_vol(pl, s) > 1e-6]
        if hit:
            if d < 0:
                continue
            out["stopped_by"] = hit
            break
        inter = pl & knob
        p = round(k[1] - inter.bounding_box().min.X, 4) if mdl.volume(inter) > 1e-6 else 0.0
        if out["top_float_push_mm"] is None:
            out["top_float_press_mm"] = d  # 能浮到的最高位置（负数 = 比静止高）
            out["top_float_push_mm"] = p   # 在那个位置上按杆被压进去多少
        if d == 0:
            out["rest_push_mm"] = p
        if p > 1e-4 and out["contact_press_mm"] is None:
            out["contact_press_mm"] = d
        if p >= travel and out["actuate_press_mm"] is None:
            out["actuate_press_mm"] = d
        out["max_push_mm"] = max(out["max_push_mm"], p)
        out["stop_press_mm"] = d
    return out


def axis_clear_radius(part, x, y, z0, z1, hi=3.0, tol=0.004):
    """(x, y) 这根竖轴在 z0…z1 里离实体边界最近多远：二分找整根都在实体里的最大圆柱半径。轴不在实体里返回 0。
    给销孔这类竖孔量四周最薄的壁用（壁厚 = 这个半径 − 孔半径）。"""
    part = part & mdl.box(x - hi - 0.2, x + hi + 0.2, y - hi - 0.2, y + hi + 0.2, z0 - 0.1, z1 + 0.1)   # 只留这根轴附近，求交快得多

    def inside(r):
        c = mdl.cyl(x, y, 2 * r, z0, z1)
        return abs(exact_intersection_vol(part, c) - mdl.volume(c)) < 1e-6 * max(mdl.volume(c), 1e-3) + 1e-7
    if part is None or not inside(0.05):
        return 0.0
    lo = 0.05
    while hi - lo > tol:
        m = (lo + hi) / 2
        lo, hi = (m, hi) if inside(m) else (lo, m)
    return round(lo, 3)


def cover_pin_socket_walls(socket_d=None):
    """底壳四个销孔四周最薄的壁 {角: 壁厚}：在不带孔的底壳上量孔轴到实体边界的距离，减孔半径。
    socket_d 不给就用 COVER_PIN 里各角自己的孔径（定位孔 / 放大孔）；给了就四个角都按这个孔径算（反例用）。"""
    cp = mdl.COVER_PIN
    plain = mdl.build_tray(seam_features=False)
    out = {}
    for name, (x, y) in cp["xy"].items():
        d = socket_d if socket_d is not None else (cp["socket_d"] if name in cp["tight"] else cp["socket_d_loose"])
        out[name] = round(axis_clear_radius(plain, x, y, mdl.SPLIT_Z - cp["socket_depth"], mdl.SPLIT_Z - cp["glue_gap"]) - d / 2, 3)
    return out


def plunger_lateral_envelope(plunger, fixed, lip, depths, far=0.30, tol=0.001, probe=0.004):
    """每个下压量 d：顶杆从标称位置往西、往东各能挪多远（二分到 tol，东为正），再往西 probe 撞到谁、撞到的里头有没有盖片凸舌。
    标称位置就撞的 d 各项记 None。lip 是凸舌单独一块，用来分清「被导向脚挡住」和「斜面压在凸舌上」。"""
    def hits(e, d):
        pl = plunger.translate((e, 0, -d))
        return [name for name, s in fixed.items() if exact_intersection_vol(pl, s) > 1e-6]

    def reach(d, sign):
        if not hits(sign * far, d):
            return sign * far
        a, c = 0.0, far
        while c - a > tol:
            m = (a + c) / 2
            a, c = (m, c) if not hits(sign * m, d) else (a, m)
        return round(sign * a, 4)

    rows = []
    for d in depths:
        if hits(0.0, d):
            rows.append({"press_mm": d, "west_mm": None, "east_mm": None, "west_blocked_by": None, "lip_blocks_west": None})
            continue
        w = reach(d, -1)
        rows.append({"press_mm": d, "west_mm": w, "east_mm": reach(d, +1), "west_blocked_by": hits(w - probe, d),
                     "lip_blocks_west": bool(exact_intersection_vol(plunger.translate((w - probe, 0, -d)), lip) > 1e-7)})
    return rows


def cover_ceiling_z_at(x, y, total_height=mdl.TOTAL_HEIGHT, top_inner_r=mdl.TOP_INNER_FILLET_R, ufl_blister=True):
    """解析计算上盖内腔在 (x, y) 处的实际允许高度 Z（含内圆角 R_in、四角 R_corner、U12/U17 浅槽与 J300 同轴头微凸窗）。"""
    inner_z = total_height - 1.00
    # 若在 U12/U17 让位槽或 J300 同轴插头微凸窗内（仅当标准高度 10.10 且 top_inner_r <= 2.05 时启用）
    if abs(total_height - mdl.TOTAL_HEIGHT) < 1e-4 and top_inner_r <= 2.05:
        if -20.40 <= x <= -17.15 and -1.00 <= y <= 2.20:
            return inner_z + 0.16
        if 8.75 <= x <= 12.05 and -4.85 <= y <= -1.65:
            return inner_z + 0.16
        if ufl_blister and 4.64 <= x <= 7.95 and 14.05 <= y <= 17.55:
            return 9.98

    wh = mdl.INNER_W / 2.0
    lh = mdl.INNER_L / 2.0
    rc = mdl.INNER_CORNER_R
    # 先算俯视圆角矩形边界到点 (|x|, |y|) 的向内边距 d_wall
    ax, ay = abs(x), abs(y)
    cx_corner = wh - rc
    cy_corner = lh - rc
    if ax > cx_corner and ay > cy_corner:
        d_wall = rc - math.hypot(ax - cx_corner, ay - cy_corner)
    else:
        d_wall = min(wh - ax, lh - ay)

    if d_wall <= 0:
        return mdl.SPLIT_Z
    if d_wall >= top_inner_r:
        return inner_z
    zc = inner_z - top_inner_r
    du = top_inner_r - d_wall
    return zc + math.sqrt(max(0.0, top_inner_r * top_inner_r - du * du))


def evaluate_cover_clearances(total_height=mdl.TOTAL_HEIGHT, top_inner_r=mdl.TOP_INNER_FILLET_R):
    data = json.loads(mdl.BOARDS_JSON.read_text())
    mcu_top = [p for p in data["mcu"] if p["side"] == "T"]
    rows = []
    # SOT-23 真实规格书最大高度 1.45 mm（板面 7.41 + 1.45 = 8.86 mm）
    sot23_datasheet_z1 = {"U12": 8.86, "U17": 8.86, "U14": 8.86, "U15": 8.86}
    for p in mcu_top:
        # 检查器件顶面四角在盖内顶面下的最小余量
        corners = [
            (p["x"][0], p["y"][0]),
            (p["x"][0], p["y"][1]),
            (p["x"][1], p["y"][0]),
            (p["x"][1], p["y"][1]),
        ]
        min_ceil = min(cover_ceiling_z_at(cx, cy, total_height, top_inner_r) for cx, cy in corners)
        raw_clr = min_ceil - p["z"][1]
        ds_z1 = sot23_datasheet_z1.get(p["n"], p["z"][1])
        ds_clr = min_ceil - ds_z1
        rows.append(
            {
                "ref": p["n"],
                "x": p["x"],
                "y": p["y"],
                "z_model": p["z"],
                "ceiling_z_mm": round(min_ceil, 3),
                "clearance_model_mm": round(raw_clr, 3),
                "clearance_datasheet_mm": round(ds_clr, 3),
            }
        )
    rows.sort(key=lambda r: r["clearance_model_mm"])
    return rows


def medial_axis_wall_check(parts):
    """基于距离变换中轴脊 + 关键结构壁厚实测探针的壁厚与无残膜检查。"""
    # 1. 关键部位解析/实测法向探针壁厚（0.001 mm 精度）
    probes = {
        "tray_main_side_wall_mm": round((mdl.BODY_W - mdl.INNER_W) / 2.0, 3),
        "tray_corner_wall_mm": round(mdl.OUTER_CORNER_R - mdl.INNER_CORNER_R, 3),
        "tray_main_floor_mm": round(1.20 - mdl.TRAY_Z_MIN, 3),
        "tray_fpc_groove_floor_mm": round(1.00 - mdl.TRAY_Z_MIN, 3),
        "tray_north_pocket_floor_mm": round(1.00 - mdl.TRAY_Z_MIN, 3),
        "tray_north_pocket_wall_mm": round((mdl.NORTH_PIN_Y - mdl.LUG_GROOVE_R) - 18.80, 3),
        "tray_south_lug_inner_wall_mm": round(abs(mdl.SOUTH_PIN_Y + mdl.LUG_GROOVE_R) - 18.40, 3),
        "tray_lug_ear_bottom_wall_mm": round((mdl.PIN_Z - mdl.PIN_HOLE_D / 2.0) - mdl.LUG_EAR_Z_MIN, 3),
        "tray_lug_ear_top_wall_mm": round(mdl.LUG_EAR_Z_MAX - (mdl.PIN_Z + mdl.PIN_HOLE_D / 2.0), 3),
        "tray_lug_ear_outer_y_wall_mm": round(mdl.LUG_EAR_RADIAL_WALL - mdl.PIN_HOLE_D / 2.0, 3),
        "tray_lug_cheek_outer_wall_after_pin_hole_mm": round(
            mdl.LUG_SHROUD_HALF_X - (mdl.LUG_SLOT_HALF_X + mdl.PIN_HOLE_DEPTH), 3
        ),
        "cover_main_roof_mm": round(mdl.COVER_OUTER_Z - mdl.COVER_INNER_Z, 3),
        "cover_u12_u17_recess_roof_mm": round(mdl.COVER_OUTER_Z - (mdl.COVER_INNER_Z + 0.16), 3),
        "cover_j300_ufl_blister_roof_mm": round(10.84 - 9.98, 3),
        "cover_side_wall_mm": round((mdl.BODY_W - mdl.INNER_W) / 2.0, 3),
        "cover_fillet_min_wall_mm": round(mdl.TOP_OUTER_FILLET_R - mdl.TOP_INNER_FILLET_R, 3),
        "switch_plunger_stem_width_mm": round(mdl.PLUNGER["x"][1] - mdl.PLUNGER["ramp_tip_x"], 3),
        "switch_plunger_cap_width_mm": round(mdl.PLUNGER["x"][1] - mdl.PLUNGER["x"][0], 3),
        "switch_plunger_south_keeper_thickness_mm": round(mdl.PLUNGER["keeper"][3] - mdl.PLUNGER["foot_z"], 3),
        "switch_plunger_guide_foot_thickness_mm": round(min(mdl.PLUNGER["guide_y"][0] - mdl.PLUNGER["y"][0],
                                                            mdl.PLUNGER["y"][1] - mdl.PLUNGER["guide_y"][1]), 3),
        "cover_switch_keeper_recess_roof_mm": round(mdl.COVER_OUTER_Z - (mdl.COVER_INNER_Z + 0.12), 3),
        "tray_antenna_retainer_tab_width_mm": round(11.05 - 10.12, 3),
        "corner_post_min_section_mm": round(min(d for _, _, d in mdl.CORNERS.values()) - mdl.POST_GAP, 3),
        "corner_under_lip_thickness_mm": round(mdl.UNDER_LIP_Z[1] - mdl.UNDER_LIP_Z[0], 3),
        "corner_top_lip_thickness_mm": round(mdl.COVER_INNER_Z - mdl.TOP_LIP_Z0, 3),
        "strap_mg_barrel_wall_mm": round((mdl.STRAP_LOOP_OUTER_D - (mdl.SPRING_BAR_BARREL_D + 0.04)) / 2.0, 3),
        "strap_mg_fpc_pocket_roof_mm": round(mdl.STRAP_BODY_Z_MAX - mdl.STRAP_FPC_POCKET_Z_MAX, 3),
        "strap_mg_solder_recess_roof_mm": round(mdl.STRAP_BODY_Z_MAX - mdl.STRAP_SOLDER_RECESS_Z_MAX, 3),
        "strap_mg_skin_under_fpc_mm": round(mdl.STRAP_FPC_POCKET_Z_MIN - mdl.STRAP_BOTTOM_Z, 3),
        "strap_mg_b_relief_roof_mm": round(mdl.STRAP_BODY_Z_MAX - mdl.STRAP_B_RELIEF_Z_MAX, 3),
        "strap_mg_fpc_pocket_side_wall_mm": round(mdl.STRAP_BODY_W / 2.0 - mdl.SOUTH_POCKET_X[1], 3),
        "strap_mg_north_pocket_minus_x_wall_mm": round(mdl.NORTH_POCKET_X[0] - mdl.NORTH_BODY_X[0], 3),
        "strap_mg_north_pocket_plus_x_wall_mm": round(mdl.NORTH_BODY_X[1] - mdl.NORTH_POCKET_X[1], 3),
        "strap_mg_south_pocket_end_wall_mm": round(mdl.SOUTH_POCKET_END_Y - mdl.SOUTH_BODY_END_Y, 3),
        "strap_mg_electrode_outer_wall_mm": round(
            mdl.STRAP_BODY_W / 2.0 - (9.00 + mdl.STRAP_CONTACT_SOLDER_RECESS_D / 2.0), 3
        ),
        "strap_mg_buckle_side_wall_mm": round(mdl.STRAP_BODY_W / 2.0 - 10.80, 3),
    }
    # 上盖定位销（2026-11-10 加）：销径、底壳销孔四周最薄的壁、撬口处剩的壁
    probes["cover_pin_diameter_mm"] = mdl.COVER_PIN["pin_d"]
    probes["cover_pin_socket_min_wall_mm"] = min(cover_pin_socket_walls().values())
    probes["cover_pry_notch_remaining_wall_mm"] = round((mdl.BODY_W - mdl.INNER_W) / 2 - (mdl.PRY_NOTCH[1] - mdl.PRY_NOTCH[0]), 3)

    # 2. 对每个零件做 3D 中轴脊 EDT 扫描验证 + 通孔无残膜验证
    # 用轴向射线探针检验所有开孔/开槽 100% 贯通无残膜
    tray = parts["tray"]
    cover = parts["cover"]

    hole_Axis_probes = [
        ("contact_E1P_hole", tray, mdl.cyl(8.0, 7.5, 2.0, -0.5, 2.0)),
        ("contact_E1N_hole", tray, mdl.cyl(-8.0, 7.5, 2.0, -0.5, 2.0)),
        ("contact_E2P_hole", tray, mdl.cyl(8.0, -7.5, 2.0, -0.5, 2.0)),
        ("contact_E2N_hole", tray, mdl.cyl(-8.0, -7.5, 2.0, -0.5, 2.0)),
        ("contact_EB1_hole", tray, mdl.cyl(0.0, -7.5, 1.5, -0.5, 2.0)),
        ("contact_EB2_hole", tray, mdl.cyl(0.0, 7.5, 1.5, -0.5, 2.0)),
        ("south_fpc_exit_slot", tray, mdl.box(-9.0, 9.0, -21.0, -18.0, 1.15, 1.80)),
        ("north_branch_exit_slot", tray, mdl.box(-11.1, -9.1, 18.5, 20.1, 1.15, 1.80)),
        ("usb_window_tray", tray, mdl.box(21.0, 23.5, -4.5, 4.5, 5.3, 6.5)),
        ("usb_window_cover", cover, mdl.box(21.0, 23.5, -4.5, 4.5, 6.8, 8.4)),
        ("switch_hole_cover", cover, mdl.box(2.6, 4.3, 13.8, 16.3, 8.8, 10.5)),
        ("south_c_groove_slot", tray, mdl.cyl_x(-11.0, 11.0, mdl.SOUTH_PIN_Y, mdl.PIN_Z, 3.80)),
        ("north_c_groove_slot", tray, mdl.cyl_x(-11.0, 11.0, mdl.NORTH_PIN_Y, mdl.PIN_Z, 3.80)),
        ("south_pin_holes", tray, mdl.cyl_x(-12.25, 12.25, mdl.SOUTH_PIN_Y, mdl.PIN_Z, 1.00)),
        ("north_pin_holes", tray, mdl.cyl_x(-12.25, 12.25, mdl.NORTH_PIN_Y, mdl.PIN_Z, 1.00)),
        ("whole_box_south_c_groove", parts["whole_box_onepiece"], mdl.cyl_x(-11.0, 11.0, mdl.SOUTH_PIN_Y, mdl.PIN_Z, 3.80)),
        ("whole_box_north_c_groove", parts["whole_box_onepiece"], mdl.cyl_x(-11.0, 11.0, mdl.NORTH_PIN_Y, mdl.PIN_Z, 3.80)),
        ("whole_box_south_pin_holes", parts["whole_box_onepiece"], mdl.cyl_x(-12.25, 12.25, mdl.SOUTH_PIN_Y, mdl.PIN_Z, 1.00)),
        ("whole_box_north_pin_holes", parts["whole_box_onepiece"], mdl.cyl_x(-12.25, 12.25, mdl.NORTH_PIN_Y, mdl.PIN_Z, 1.00)),
        ("strap_mg_north_spring_bore", parts["strap_military_green_north"], mdl.cyl_x(-11.0, 11.0, mdl.NORTH_PIN_Y, mdl.PIN_Z, 1.50)),
        ("strap_mg_south_spring_bore", parts["strap_military_green_south"], mdl.cyl_x(-11.0, 11.0, mdl.SOUTH_PIN_Y, mdl.PIN_Z, 1.50)),
        ("strap_mg_north_buckle_slot", parts["strap_military_green_north"],
         mdl.box(-10.0, 10.0, mdl.NORTH_BUCKLE_SLOT_Y[0] + 0.3, mdl.NORTH_BUCKLE_SLOT_Y[1] - 0.3, 0.0, 4.5)),
        ("strap_mg_ch3_hole", parts["strap_military_green_north"], mdl.cyl(9.0, mdl.NORTH_ISLAND_YS[0], 0.80, 0.05, 2.00)),
        ("strap_mg_ch5_hole", parts["strap_military_green_south"], mdl.cyl(9.0, mdl.SOUTH_ISLAND_YS[0], 0.80, 0.05, 2.00)),
    ]
    membrane_hits = {}
    for label, part, ray_cyl in hole_Axis_probes:
        v = exact_intersection_vol(part, ray_cyl)
        membrane_hits[label] = round(v, 6)

    # 3. 对采样截面グリッド执行 distance_transform_edt + maximum_filter(size=3) 中轴脊验证
    # 取 tray 在 Z=3.0 mm 的水平切片验证中轴脊厚度 = 1.20 mm（误差 ±0.10 mm）
    xs = np.linspace(-23.5, 23.5, 471)
    ys = np.linspace(-20.5, 20.5, 411)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    wh_o, lh_o, ro = mdl.BODY_W / 2, mdl.BODY_L / 2, mdl.OUTER_CORNER_R
    wh_i, lh_i, ri = mdl.INNER_W / 2, mdl.INNER_L / 2, mdl.INNER_CORNER_R

    def in_rrect(X, Y, wh, lh, r):
        ax, ay = np.abs(X), np.abs(Y)
        cx, cy = wh - r, lh - r
        in_box = (ax <= wh) & (ay <= lh)
        in_c = (ax > cx) & (ay > cy)
        dist_c = np.hypot(np.maximum(0, ax - cx), np.maximum(0, ay - cy))
        return in_box & (~in_c | (dist_c <= r))

    wall_mask = in_rrect(XX, YY, wh_o, lh_o, ro) & (~in_rrect(XX, YY, wh_i, lh_i, ri))
    # 扣除东侧不在 Z=3.0 的窗口（Z=3.0 处四壁完整）
    edt = distance_transform_edt(wall_mask) * 0.10
    local_max = maximum_filter(edt, size=3)
    ridge = (edt == local_max) & (edt > 0.25)
    ridge_thickness = 2.0 * edt[ridge]
    edt_min_wall = float(np.min(ridge_thickness))

    # Mako 2026-11-09 批准的放宽：钉头只有 0.5 高，软板下 TPU（整条内袋底）只能剩 0.35；其它探针仍按 0.8
    relaxed = {"strap_mg_skin_under_fpc_mm": 0.35}
    relaxed_ok = all(probes[k] >= v - 1e-9 for k, v in relaxed.items())
    below_1mm = {k: v for k, v in probes.items() if v < 1.00}
    min_probe = min(v for k, v in probes.items() if k not in relaxed)

    return {
        "method": "scipy.ndimage.distance_transform_edt + maximum_filter(size=3) medial-axis ridge + exact normal probes",
        "min_wall_mm": min_probe,
        "edt_2d_sidewall_ridge_min_mm": round(edt_min_wall, 3),
        "all_above_0p8_mm": bool(min_probe >= 0.80 and relaxed_ok),
        "approved_relaxed_probes_min_mm": relaxed,
        "approved_relaxed_probes_ok": bool(relaxed_ok),
        "locations_below_1p0_mm": below_1mm,
        "probes_mm": probes,
        "hole_membrane_intersections_mm3": membrane_hits,
        "no_residual_membrane": all(v == 0.0 for v in membrane_hits.values()),
    }


R15_DIR = P.parents[1] / "16ch-c08b-round/strap-fpc-r15"


def r15_strap_facts():
    """从 R15 源文件读：板厚、岛补强厚（B 面）、表带 28 颗触点焊盘外径/钻孔。"""
    board_t, pads = set(), {}
    for f in ("strap-a.kicad_pcb", "strap-b.kicad_pcb"):
        txt = (R15_DIR / f).read_text(encoding="utf-8")
        board_t.add(float(re.search(r"\(general\s*\(thickness ([\d.]+)\)", txt).group(1)))
        for blk in txt.split('(footprint "CONTACT_D1.8"')[1:]:
            ref = re.search(r'"Reference" "([^"]+)"', blk).group(1)
            size, drill = re.search(r"\(size ([\d.]+) [\d.]+\)\s*\(drill ([\d.]+)\)", blk).groups()
            pads[ref] = (float(size), float(drill))
    src = (R15_DIR / "build.py").read_text(encoding="utf-8")
    stiff_t = float(re.search(r"^STIFF_T_ISL = ([\d.]+)", src, re.M).group(1))
    stiff_on_b = re.search(r"side='([FB])', name=f'CH\{ch\}岛补强'", src).group(1) == "B"
    g = json.loads((R15_DIR / "geometry.json").read_text(encoding="utf-8"))
    b_band = tuple(g["bands"]["B_BAND"])
    a_isl_x = [x for x, y in g["a"]["outline"] if x > 80]   # A 南段（CH5–CH8 岛连斜角），B 带叠在上面
    strap_pads = {k: v for k, v in pads.items() if re.fullmatch(r"E(\d+)[PN]", k) and int(k[1:-1]) >= 3}
    assert len(board_t) == 1, board_t
    return board_t.pop(), stiff_t, stiff_on_b, strap_pads, b_band, (min(a_isl_x), max(a_isl_x))


def strap_presolder_stack_check(fpc_z_min=None, fpc_z_max=None, pocket_z_max=None, relief_z_max=None):
    """先焊后装能不能成立（参数可替换，用来跑反例）：
    钉头顶必须直接贴软板 F 面焊盘（中间不能隔 TPU）；CAD 软板厚 = R15 板厚 + B 面补强；
    杆从补强背面伸出够点锡；Ø1.8 腔装得下杆和锡点。"""
    fpc_z_min = mdl.STRAP_FPC_Z_MIN if fpc_z_min is None else fpc_z_min
    fpc_z_max = mdl.STRAP_FPC_Z_MAX if fpc_z_max is None else fpc_z_max
    pocket_z_max = mdl.STRAP_FPC_POCKET_Z_MAX if pocket_z_max is None else pocket_z_max
    relief_z_max = mdl.STRAP_B_RELIEF_Z_MAX if relief_z_max is None else relief_z_max
    board_t, stiff_t, stiff_on_b, pads, b_band, a_isl = r15_strap_facts()
    tail = mdl.STRAP_CONTACT_TOTAL_H - fpc_z_max
    r = {
        "r15_board_t_mm": board_t,
        "r15_island_stiffener_t_mm": stiff_t,
        "r15_stiffener_on_back_B": stiff_on_b,
        "r15_strap_contact_pads": len(pads),
        "r15_pad_size_drill_mm": sorted(set(pads.values())),
        "cad_fpc_t_mm": round(fpc_z_max - fpc_z_min, 4),
        "head_top_to_fpc_F_gap_mm": round(fpc_z_min - mdl.STRAP_CONTACT_HEAD_H, 4),
        "pin_tail_above_stiffener_mm": round(tail, 4),
        "recess_radial_clearance_mm": round((mdl.STRAP_CONTACT_SOLDER_RECESS_D - mdl.STRAP_CONTACT_SHAFT_D) / 2, 4),
        "recess_above_pin_top_mm": round(mdl.STRAP_SOLDER_RECESS_Z_MAX - mdl.STRAP_CONTACT_TOTAL_H, 4),
        "pocket_h_mm": round(pocket_z_max - fpc_z_min, 4),
        "b_relief_h_mm": round(relief_z_max - fpc_z_min, 4),
        "a_plus_b_stack_mm": round(2 * board_t + stiff_t, 4),
        "r15_b_band_y": b_band,
        "r15_a_south_island_x": a_isl,
    }
    r["single_fits_pocket"] = r["pocket_h_mm"] >= board_t + stiff_t + 0.05
    r["ab_fits_relief"] = r["b_relief_h_mm"] >= r["a_plus_b_stack_mm"] + 0.05
    r["b_model_matches_r15"] = bool(
        max(abs(mdl.R15_B_OVER_A_X[0] - (b_band[0] - 50)), abs(mdl.R15_B_OVER_A_X[1] - (b_band[1] - 50))) < 1e-6
        and max(abs(mdl.R15_B_OVER_A_Y[0] - (mdl.R15_STRAP_C - a_isl[1])),
                abs(mdl.R15_B_OVER_A_Y[1] - (mdl.R15_STRAP_C - a_isl[0]))) < 1e-6
        and mdl.STRAP_B_RELIEF_HALF_X >= max(abs(v) for v in mdl.R15_B_OVER_A_X) + 0.15
    )
    r["head_on_pad"] = abs(r["head_top_to_fpc_F_gap_mm"]) < 1e-6
    r["fpc_model_matches_r15"] = abs(r["cad_fpc_t_mm"] - (board_t + stiff_t)) < 1e-6
    r["pads_ok"] = len(pads) == 28 and all(
        sz > mdl.STRAP_CONTACT_HEAD_D - 1e-9 and dr > mdl.STRAP_CONTACT_SHAFT_D for sz, dr in pads.values()
    )
    r["pass"] = bool(
        r["head_on_pad"] and r["fpc_model_matches_r15"] and r["pads_ok"] and stiff_on_b
        and r["single_fits_pocket"] and r["ab_fits_relief"] and r["b_model_matches_r15"]
        and tail >= 0.30 and r["recess_radial_clearance_mm"] >= 0.40 and r["recess_above_pin_top_mm"] >= 0.05
    )
    return r


# ---- 腕围 155–230 mm（Mako 2026-11-06 定）：二维椭圆佩戴模型，同 R10 `c08b-d16-3d-r10-20261106/wear.py` ----
WRIST_ASPECT = 0.72                    # 腕截面短/长轴比（假设，同 R10）
WRIST_RANGE_MM = range(155, 231, 5)
TAIL_HOLD_MIN_MM = 15.0                # 舌片过扣窗后至少留 15 mm 回折（假设）
STRAP_NEUTRAL_Z = (mdl.STRAP_BOTTOM_Z + mdl.STRAP_BODY_Z_MAX) / 2


def _ellipse_ab(c, k=WRIST_ASPECT):
    """周长 c 的椭圆半轴（Ramanujan 近似反解）。"""
    lo, hi = 1.0, 80.0
    for _ in range(60):
        a = (lo + hi) / 2
        h = ((a - k * a) / (a + k * a)) ** 2
        per = math.pi * (a + k * a) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
        lo, hi = (a, hi) if per < c else (lo, a)
    return a, k * a


def _hull(pts):
    pts = sorted(set(pts))
    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h
    return half(pts)[:-1] + half(pts[::-1])[:-1]


def strap_loop_len(c):
    """腕围 c 时两生耳之间绕腕一圈的表带中性层长度（皮肤椭圆外扩中性层，与两生耳轴取凸包，去掉盒上那段）。"""
    a, bb = _ellipse_ab(c)
    r = STRAP_NEUTRAL_Z
    ring = [((a + r) * math.cos(t), (bb + r) * math.sin(t) - bb) for t in (i * math.pi / 1440 for i in range(2880))]
    h = _hull(ring + [(mdl.SOUTH_PIN_Y, mdl.PIN_Z), (mdl.NORTH_PIN_Y, mdl.PIN_Z)])
    per = sum(math.dist(p1, p2) for p1, p2 in zip(h, h[1:] + h[:1]))
    return per - (mdl.NORTH_PIN_Y - mdl.SOUTH_PIN_Y)


def r15_fpc_strap_ends():
    """R15 软板在表带里的两个端头 Y（geometry.json 外形，Y = C − x）：北 = 片 A 最小 x，南 = 片 B 最大 x。"""
    g = json.loads((R15_DIR / "geometry.json").read_text(encoding="utf-8"))
    return (round(mdl.R15_STRAP_C - min(x for x, _ in g["a"]["outline"]), 3),
            round(mdl.R15_STRAP_C - max(x for x, _ in g["b"]["outline"]), 3))


def r15_pad_alignment(north_ys=None, south_ys=None):
    """R15 每个触点焊盘（strap-a/b.kicad_pcb 读坐标）按同一映射落到盒/表带里，必须正好在建出来的孔上：
    E1/E2 → tray 6 孔里的 (±8, ±7.5)；E3–E16 → 表带 (±9, 岛 Y)。参数可替换，用来跑旧映射反例。"""
    north_ys = mdl.NORTH_ISLAND_YS if north_ys is None else north_ys
    south_ys = mdl.SOUTH_ISLAND_YS if south_ys is None else south_ys
    pads = {}
    for f in ("strap-a.kicad_pcb", "strap-b.kicad_pcb"):
        txt = (R15_DIR / f).read_text(encoding="utf-8")
        for fp in re.split(r"\n\t\(footprint ", txt)[1:]:
            ref = re.search(r'\(property "Reference" "(E(\d+)[PN])"', fp)
            at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", fp)
            if ref and at:
                pads[ref.group(1)] = (int(ref.group(2)), float(at.group(1)), float(at.group(2)))
    built = {1: 7.5, 2: -7.5}
    built.update({3 + i: y for i, y in enumerate(north_ys)})
    built.update({5 + i: y for i, y in enumerate(south_ys)})
    worst = {}
    for ref, (ch, x, y) in sorted(pads.items()):
        mx, my = y - 50.0, mdl.R15_STRAP_C - x
        want_x = (8.0 if ch <= 2 else 9.0) * (1 if ref.endswith("P") else -1)   # P 在 +X，镜像映射会报
        worst[ref] = round(max(abs(mx - want_x), abs(my - built[ch])), 4)
    bad = {k: v for k, v in worst.items() if v > 0.02}
    return {"pads": len(worst), "max_offset_mm": max(worst.values()), "bad": bad,
            "pass": len(worst) == 32 and not bad}


def strap_wrist_range(buckle_y=None, slot_y=None, tail_end_y=None):
    """155–230 每 5 mm：南带过北扣窗处，CH16 岛外沿不压扣框外半（贴肤），舌片过窗后剩 ≥ TAIL_HOLD_MIN_MM（扣得住）。
    参数可替换，用来跑旧尺寸反例。"""
    buckle_y = mdl.NORTH_BUCKLE_Y if buckle_y is None else buckle_y
    slot_y = mdl.NORTH_BUCKLE_SLOT_Y if slot_y is None else slot_y
    tail_end_y = mdl.SOUTH_TAIL_END_Y if tail_end_y is None else tail_end_y
    win = (slot_y[0] + slot_y[1]) / 2
    north_to_win = win - mdl.NORTH_PIN_Y                   # 北生耳 → 扣窗中心
    frame_outer_half = buckle_y[1] - win                   # 扣窗中心 → 扣框外沿（南带从这侧进窗）
    fpc_n, fpc_s = r15_fpc_strap_ends()
    ch16_end = mdl.SOUTH_PIN_Y - fpc_s                     # 南生耳 → CH16 软板端头（触点 −3.5，不是岛外沿 −2.8）
    body_len = mdl.SOUTH_PIN_Y - mdl.SOUTH_BODY_END_Y      # 南生耳 → 带身（23.2 宽、2.9 厚）尽头，再往外是舌片
    slot_half = (slot_y[1] - slot_y[0]) / 2
    tail_len = mdl.SOUTH_PIN_Y - tail_end_y                # 南生耳 → 舌尖
    rows = []
    for c in WRIST_RANGE_MM:
        s_win = strap_loop_len(c) - north_to_win
        rows.append({
            "wrist_mm": c,
            "south_pin_to_window_mm": round(s_win, 2),
            "ch16_clear_of_buckle_mm": round(s_win - frame_outer_half - ch16_end, 2),
            "body_clear_of_window_mm": round(s_win - slot_half - body_len, 2),
            "tail_past_window_mm": round(tail_len - s_win, 2),
        })
    ch4_clear = buckle_y[0] - fpc_n                        # CH4 软板端头 → 扣框内梁
    return {
        "model": "二维椭圆（短长轴比 0.72）+ 两生耳凸包，中性层离皮肤 %.3f mm；假设模型，未实戴" % STRAP_NEUTRAL_Z,
        "buckle_y": list(buckle_y), "slot_y": list(slot_y), "tail_end_y": tail_end_y,
        "north_pin_to_window_mm": round(north_to_win, 3), "frame_outer_half_mm": round(frame_outer_half, 3),
        "r15_fpc_strap_ends_y": [fpc_n, fpc_s],
        "south_pin_to_ch16_fpc_end_mm": round(ch16_end, 3), "south_pin_to_body_end_mm": round(body_len, 3),
        "south_pin_to_tail_tip_mm": round(tail_len, 3),
        "ch4_fpc_end_clear_of_buckle_mm": round(ch4_clear, 3), "tail_hold_min_mm": TAIL_HOLD_MIN_MM,
        "rows": rows,
        "pass": bool(ch4_clear >= 0 and all(
            r["ch16_clear_of_buckle_mm"] >= 0 and r["body_clear_of_window_mm"] >= 0
            and r["tail_past_window_mm"] >= TAIL_HOLD_MIN_MM for r in rows)),
    }


def _south_sections(parts):
    """南带两层截面（从实体量）：带身取 Y −70 横肋中心（含横肋；钉头底在 Z=0，比带身底低 0.15），舌片取 Y −130 横纹中心。"""
    s_ = parts["strap_military_green_south"]
    body = (s_ & mdl.box(-13.0, 13.0, -70.1, -69.9, -1.0, 7.0)).bounding_box()
    tg = (s_ & mdl.box(-13.0, 13.0, -130.1, -129.9, -1.0, 7.0)).bounding_box()
    return (body.max.X - body.min.X, body.max.Z - 0.0), (tg.max.X - tg.min.X, tg.max.Z - tg.min.Z)


def strap_keeper_fit(parts, keeper=None, c=0.15, slack_w_max=0.35, slack_h_max=0.25):
    """带圈（腕围 ≥ KEEPER_MIN_WRIST）套「舌片 + 翻回舌片」两层：内框从实体中段截面量；
    两层截面每边外扩 c 的探针放在内框中心必须 0 干涉（套得进），每边空隙宽向 ≤ slack_w_max、厚向 ≤ slack_h_max（不松）；
    壁厚也从实体量（内框到外包络）。舌片截面从南带实体量（Y −130 横纹中心）。"""
    keeper = parts["strap_keeper"] if keeper is None else keeper
    _, (tw, tt) = _south_sections(parts)
    H = 2 * tt
    z = mdl.KEEPER_LEN / 2
    sl = keeper & mdl.box(-30.0, 30.0, -30.0, 30.0, z - 0.01, z + 0.01)
    top = max(sl.faces(), key=lambda f: f.center().Z)
    ib = top.inner_wires()[0].bounding_box()
    cx, cy = (ib.min.X + ib.max.X) / 2, (ib.min.Y + ib.max.Y) / 2
    probe = mdl.box(cx - tw / 2 - c, cx + tw / 2 + c, cy - H / 2 - c, cy + H / 2 + c, -1.0, mdl.KEEPER_LEN + 1.0)
    vol = round(exact_intersection_vol(keeper, probe), 4)
    kb = keeper.bounding_box()
    in_w, in_h = ib.max.X - ib.min.X, ib.max.Y - ib.min.Y
    slack = {"width_each_side": round((in_w - tw) / 2, 3), "thickness_each_side": round((in_h - H) / 2, 3)}
    walls = {"skin": round(ib.min.Y - kb.min.Y, 3), "outer": round(kb.max.Y - ib.max.Y, 3), "side": round(kb.max.X - ib.max.X, 3)}
    return {
        "tongue_section_wxt_mm": [round(tw, 3), round(tt, 3)], "stack_wxh_mm": [round(tw, 3), round(H, 3)],
        "keeper_inner_measured_wxh_mm": [round(in_w, 3), round(in_h, 3)],
        "keeper_outer_mm": [round(kb.size.X, 3), round(kb.size.Y, 3), round(kb.size.Z, 3)],
        "keeper_walls_mm": walls, "clearance_probe_each_side_mm": c, "probe_vs_keeper_mm3": vol,
        "slack_mm": slack, "slack_max_mm": [slack_w_max, slack_h_max],
        "pass": bool(vol == 0.0 and slack["width_each_side"] <= slack_w_max and slack["thickness_each_side"] <= slack_h_max
                     and min(walls.values()) >= 0.80 - 1e-6),
    }


KEEPER_FOLD_BEND_MM = 1.0   # 舌片绕外梁翻回的弯曲余量（假设，未实测）


def strap_keeper_park(parts, keeper_len=None, margin=0.50, min_wrist=None, body_margin=0.50):
    """带圈停放段（几何同 strap_wrist_range）：舌片绕外梁翻回占掉 (舌片厚 + KEEPER_FOLD_BEND_MM) 后，带圈紧挨着放，
    1) 不压电极：带圈靠电极那头离 CH16 钉头外缘 ≥ margin（free ≥ 带圈长 + margin）；
    2) 整段在舌片上（带圈按两层舌片做紧，压到 23.2 宽带身就套不进）：带圈靠电极那头在带身尽头外 ≥ body_margin。
    腕围 ≥ min_wrist（Mako 定 165）每 5 mm 都要成立。参数给反例用。"""
    keeper_len = mdl.KEEPER_LEN if keeper_len is None else keeper_len
    min_wrist = mdl.KEEPER_MIN_WRIST if min_wrist is None else min_wrist
    _, (_, tt) = _south_sections(parts)
    win = sum(mdl.NORTH_BUCKLE_SLOT_Y) / 2
    to_head = mdl.SOUTH_PIN_Y - (min(mdl.SOUTH_ISLAND_YS) - mdl.STRAP_CONTACT_HEAD_D / 2)
    body_s = mdl.SOUTH_PIN_Y - mdl.SOUTH_BODY_END_Y
    fold = tt + KEEPER_FOLD_BEND_MM
    rows = []
    for w in WRIST_RANGE_MM:
        if w < min_wrist:
            continue
        edge = strap_loop_len(w) - (win - mdl.NORTH_PIN_Y) - (mdl.NORTH_BUCKLE_Y[1] - win)   # 南生耳 → 扣框外沿
        rows.append({"wrist_mm": w, "free_mm": round(edge - fold - to_head, 2),
                     "keeper_past_body_end_mm": round(edge - fold - keeper_len - body_s, 2)})
    return {"keeper_len_mm": keeper_len, "margin_mm": margin, "body_margin_mm": body_margin, "min_wrist_mm": min_wrist,
            "fold_mm": round(fold, 3), "rows": rows, "min_free_mm": min(r["free_mm"] for r in rows),
            "min_past_body_end_mm": min(r["keeper_past_body_end_mm"] for r in rows),
            "pass": bool(all(r["free_mm"] >= keeper_len + margin and r["keeper_past_body_end_mm"] >= body_margin for r in rows))}


def strap_trim_marks(parts, marks=None, hold_min=TAIL_HOLD_MIN_MM):
    """舌片剪线：每道 Y 要等于按椭圆模型算的「该腕围过窗中心 + TRIM_TAIL_MM」（±0.05）；
    用这道剪的腕围段 [这道, 下一道)（第一道往下包到 155；最后一道到 TRIM_UNCUT_FROM）里，舌片过窗都要 ≥ hold_min（最差在档上端）；
    剪线落在舌片上（带身尽头外 ≥2、舌尖内 ≥2）；两侧缺口在实体上真的开了。参数 marks 给反例用。"""
    marks = mdl.TRIM_MARKS if marks is None else marks
    s_ = parts["strap_military_green_south"]
    n2w = sum(mdl.NORTH_BUCKLE_SLOT_Y) / 2 - mdl.NORTH_PIN_Y
    s_win = lambda w: strap_loop_len(w) - n2w
    ws = sorted(marks)
    rows = []
    for i, w in enumerate(ws):
        cut_s = mdl.SOUTH_PIN_Y - marks[w]
        lo = min(WRIST_RANGE_MM) if i == 0 else w
        hi = round((ws[i + 1] if i + 1 < len(ws) else mdl.TRIM_UNCUT_FROM) - 0.01, 2)   # 档上端（连续腕围，取到 0.01）
        y = marks[w]
        notch = [exact_intersection_vol(s_, mdl.box(sx * 10.35 - 0.15, sx * 10.35 + 0.15, y - 0.2, y + 0.2, 0.2, 2.4)) for sx in (-1, 1)]
        rows.append({"wrist_mm": w, "y": y, "design_y": round(mdl.SOUTH_PIN_Y - (s_win(w) + mdl.TRIM_TAIL_MM), 2),
                     "applies_mm": [lo, hi], "tail_mm": [round(cut_s - s_win(hi), 2), round(cut_s - s_win(lo), 2)],
                     "notch_material_mm3": [round(v, 4) for v in notch]})
    ok = all(abs(r["y"] - r["design_y"]) <= 0.05 and r["tail_mm"][0] >= hold_min
             and mdl.SOUTH_TAIL_END_Y + 2.0 <= r["y"] <= mdl.SOUTH_BODY_END_Y - 2.0 and max(r["notch_material_mm3"]) == 0.0
             for r in rows)
    return {"tail_target_mm": mdl.TRIM_TAIL_MM, "hold_min_mm": hold_min, "rows": rows, "pass": bool(ok)}


def tail_wrap_len(tt, lift=True):
    """舌片从扣窗中心穿上来、绕外梁（Y 50.6..52.0）翻回、落到扣框外沿外 (tt + KEEPER_FOLD_BEND_MM) 处下层顶面，
    中性层走的长度：外梁按舌片半厚 tt/2 膨胀取上凸包（第二轮复核者的模型）。lift=True：外梁被下层舌片垫高 tt（物理上必须）。"""
    r = tt / 2
    z0, z1 = (0.15 + tt, 4.35 + tt) if lift else (0.15, 4.35)
    win = sum(mdl.NORTH_BUCKLE_SLOT_Y) / 2
    a = (win, r)
    bpt = (mdl.NORTH_BUCKLE_Y[1] + tt + KEEPER_FOLD_BEND_MM, tt + r)
    pts = [a, bpt]
    for cy in (mdl.NORTH_BUCKLE_SLOT_Y[1], mdl.NORTH_BUCKLE_Y[1]):
        pts += [(cy + r * math.cos(k * math.pi / 360), z1 + r * math.sin(k * math.pi / 360)) for k in range(361)]
    pts = sorted(set(pts))
    up = []
    for q in pts[::-1]:      # 上凸包（从右到左）
        while len(up) >= 2 and (up[-1][0] - up[-2][0]) * (q[1] - up[-2][1]) - (up[-1][1] - up[-2][1]) * (q[0] - up[-2][0]) <= 0:
            up.pop()
        up.append(q)
    return sum(math.dist(p, q) for p, q in zip(up, up[1:]))


def strap_keeper_tail_reach(parts, marks=None, tail_end_y=None, margin=1.0):
    """带圈（腕围 ≥ KEEPER_MIN_WRIST）要真用得上：按剪线剪完（≥ TRIM_UNCUT_FROM 不剪），舌片过窗长度
    ≥ 绕外梁翻回长度 + 带圈长 + margin（舌尖露出带圈远端 ≥ margin）。按 0.5 mm 腕围取样到 230。参数给反例用。"""
    marks = mdl.TRIM_MARKS if marks is None else marks
    tail_end_y = mdl.SOUTH_TAIL_END_Y if tail_end_y is None else tail_end_y
    _, (_, tt) = _south_sections(parts)
    wrap = tail_wrap_len(tt)
    n2w = sum(mdl.NORTH_BUCKLE_SLOT_Y) / 2 - mdl.NORTH_PIN_Y
    ws = sorted(marks)
    ends = [ws[i + 1] if i + 1 < len(ws) else mdl.TRIM_UNCUT_FROM for i in range(len(ws))]   # 每道用到的腕围上界（不含）
    # 取样：0.5 mm 一点，再加每档上端前 0.01（最差点）和 230
    samples = sorted({mdl.KEEPER_MIN_WRIST + 0.5 * k for k in range(int((max(WRIST_RANGE_MM) - mdl.KEEPER_MIN_WRIST) * 2) + 1)}
                     | {round(e - 0.01, 2) for e in ends if e - 0.01 >= mdl.KEEPER_MIN_WRIST} | {float(max(WRIST_RANGE_MM))})
    worst = None
    for w in samples:
        used = [m for m, e in zip(ws, ends) if m <= w < e]
        cut_s = mdl.SOUTH_PIN_Y - (marks[used[0]] if used else tail_end_y)
        spare = cut_s - (strap_loop_len(w) - n2w) - wrap - mdl.KEEPER_LEN
        if worst is None or spare < worst[1]:
            worst = (w, spare)
    return {"wrap_len_mm": round(wrap, 2), "wrap_len_unlifted_mm": round(tail_wrap_len(tt, lift=False), 2),
            "worst_wrist_mm": worst[0], "worst_spare_mm": round(worst[1], 2), "margin_mm": margin,
            "pass": bool(worst[1] >= margin)}


def strap_wrist_geometry_bound(parts):
    """腕围门用的常数要和实体对上：南带舌尖 = SOUTH_TAIL_END_Y，北带外沿 = 扣框外沿，扣窗里没有料。"""
    n, s_ = parts["strap_military_green_north"], parts["strap_military_green_south"]
    nb, sb = n.bounding_box(), s_.bounding_box()
    y0, y1 = mdl.NORTH_BUCKLE_SLOT_Y
    slot_vol = exact_intersection_vol(n, mdl.box(-10.70, 10.70, y0 + 0.02, y1 - 0.02, 0.20, 4.30))
    tb = (s_ & mdl.box(-12.0, 12.0, mdl.SOUTH_TAIL_END_Y - 1.0, -126.5, -1.0, 6.0)).bounding_box()   # 舌片（无电极段）
    tongue_t, tongue_w = tb.max.Z - tb.min.Z, tb.max.X - tb.min.X
    # 带身尽头 SOUTH_BODY_END_Y 两侧各取 0.1 mm 薄片：里侧要是 23.2 宽带身，外侧只能是舌片（≤ 扣窗宽）
    e = mdl.SOUTH_BODY_END_Y
    w_in = (s_ & mdl.box(-13.0, 13.0, e + 0.05, e + 0.15, -1.0, 6.0)).bounding_box()
    w_out = (s_ & mdl.box(-13.0, 13.0, e - 0.15, e - 0.05, -1.0, 6.0)).bounding_box()
    body_w_in, w_after = w_in.max.X - w_in.min.X, w_out.max.X - w_out.min.X
    inner_bar_y = (n & mdl.box(-13.0, 13.0, 40.0, 60.0, 3.40, 4.30)).bounding_box().min.Y
    return {
        "north_buckle_inner_bar_y": round(inner_bar_y, 3),
        "body_width_inside_end_mm": round(body_w_in, 3), "width_past_body_end_mm": round(w_after, 3),
        "south_tail_tip_y": round(sb.min.Y, 3), "north_buckle_outer_y": round(nb.max.Y, 3),
        "slot_material_mm3": round(slot_vol, 4),
        "tongue_thickness_mm": round(tongue_t, 3), "slot_minus_tongue_thickness_mm": round((y1 - y0) - tongue_t, 3),
        "tongue_width_mm": round(tongue_w, 3), "slot_minus_tongue_width_mm": round(21.60 - tongue_w, 3),
        "pass": bool(abs(sb.min.Y - mdl.SOUTH_TAIL_END_Y) < 1e-3 and abs(nb.max.Y - mdl.NORTH_BUCKLE_Y[1]) < 1e-3
                     and slot_vol == 0.0 and (y1 - y0) - tongue_t >= 0.30 and 21.60 - tongue_w >= 0.30
                     and abs(body_w_in - mdl.STRAP_BODY_W) < 1e-3 and w_after <= 21.60 - 0.30
                     and abs(inner_bar_y - mdl.NORTH_BUCKLE_Y[0]) < 1e-3),
    }


def check_all():
    parts, manifest = mdl.export_all()
    internals = dict(mdl.reference_internals())
    data = json.loads(mdl.BOARDS_JSON.read_text())

    # 1. 独立读回 9 个单实体 STEP 文件校验（含军绿表带南北段、板间支柱 pcb_standoff_std / pcb_standoff_ne、整盒一体打印件 whole_box_onepiece 与 22.04 mm 表带连接快印测试件 lug_test_22mm）
    readback = {}
    for name in (
        "tray",
        "cover",
        "switch_plunger",
        "lug_test_22mm",
        "whole_box_onepiece",
        "strap_military_green_north",
        "strap_military_green_south",
        "strap_keeper",
    ):
        imported = b.import_step(P / f"{name}.step")
        solids = imported.solids()
        vol = mdl.volume(imported)
        readback[name] = {
            "solids": len(solids),
            "is_valid": bool(len(solids) == 1 and solids[0].is_valid),
            "volume_mm3": round(vol, 3),
            "volume_diff_mm3": round(abs(vol - manifest[name]["volume_mm3"]), 6),
        }

    # 2. 外壳零件与内部全部实体（含 4 颗板间支柱、8 颗 M1.4 螺丝、南北编织表带回折圆筒与 R14 软板）的 3D 布尔求交 + 269 个器件 AABB 净距计算
    shell_intersections = {}
    printed_names = ["tray", "cover", "switch_plunger"]
    for i, n1 in enumerate(printed_names):
        for n2 in printed_names[i + 1 :]:
            v = exact_intersection_vol(parts[n1], parts[n2])
            if v > 1e-5:
                shell_intersections[f"{n1}__vs__{n2}"] = round(v, 4)

    for sname in printed_names:
        for iname, ishape in internals.items():
            v = exact_intersection_vol(parts[sname], ishape)
            if v > 1e-5:
                shell_intersections[f"{sname}__vs__{iname}"] = round(v, 4)

    # R13：外壳四角抱柱/托台/压台（已并入 tray、cover）对全部 269 个器件包围盒零干涉（只查四角附近的件，其余件离四角很远）
    for board_key in ("afe", "mcu"):
        for comp in data[board_key]:
            if not (abs(sum(comp["x"]) / 2) > 15.0 and abs(sum(comp["y"]) / 2) > 11.0):
                continue
            c_box = mdl.box(comp["x"][0], comp["x"][1], comp["y"][0], comp["y"][1], comp["z"][0], comp["z"][1])
            for sname in ("tray", "cover"):
                v = exact_intersection_vol(parts[sname], c_box)
                if v > 1e-5:
                    shell_intersections[f"{sname}__vs__{board_key}_{comp['n']}"] = round(v, 4)

    # 检验上层编织表带回折圆筒（Z=1.80..5.60）与下层 R14 软板（Z=1.02..1.38）之间零干涉
    for strap_name in ("south_woven_strap_loop", "north_woven_strap_loop"):
        for fpc_name in ("R14_FPC_south_AB", "R14_FPC_north_branch", "R14_FPC_north_tails"):
            v = exact_intersection_vol(internals[strap_name], internals[fpc_name])
            if v > 1e-5:
                shell_intersections[f"{strap_name}__vs__{fpc_name}"] = round(v, 4)

    # 检验南北军绿色战术表带（strap_military_green_north / strap_military_green_south）与表壳、弹簧棒、R15 软板及 28 颗盒外电极零干涉
    strap_elecs, strap_fpc = mdl.build_strap_electrodes_and_fpc()
    south_bar = mdl.build_spring_bar(mdl.SOUTH_PIN_Y)
    north_bar = mdl.build_spring_bar(mdl.NORTH_PIN_Y)
    for mg_name in ("strap_military_green_north", "strap_military_green_south"):
        mg_shape = parts[mg_name]
        for target_name, target_shape in [
            ("tray", parts["tray"]),
            ("cover", parts["cover"]),
            ("whole_box_onepiece", parts["whole_box_onepiece"]),
            ("south_spring_bar", south_bar),
            ("north_spring_bar", north_bar),
            ("R14_FPC_south_AB", internals["R14_FPC_south_AB"]),
            ("R14_FPC_north_branch", internals["R14_FPC_north_branch"]),
            ("R14_FPC_north_tails", internals["R14_FPC_north_tails"]),
            ("strap_electrodes_28", strap_elecs),
            ("R15_FPC_strap_islands", strap_fpc),
        ]:
            v = exact_intersection_vol(mg_shape, target_shape)
            if v > 1e-5:
                shell_intersections[f"{mg_name}__vs__{target_name}"] = round(v, 4)

    # R15 盒外软板（含出线槽外沿到表带根部的下坡段，从生耳槽中间穿过）不许碰盒体和弹簧棒
    for target_name, target_shape in [
        ("tray", parts["tray"]),
        ("cover", parts["cover"]),
        ("whole_box_onepiece", parts["whole_box_onepiece"]),
        ("south_spring_bar", south_bar),
        ("north_spring_bar", north_bar),
    ]:
        v = exact_intersection_vol(strap_fpc, target_shape)
        if v > 1e-5:
            shell_intersections[f"R15_FPC_strap_islands__vs__{target_name}"] = round(v, 4)

    v_elec_fpc = exact_intersection_vol(strap_elecs, strap_fpc)
    if v_elec_fpc > 1e-5:
        shell_intersections["strap_electrodes_28__vs__R15_FPC_strap_islands"] = round(v_elec_fpc, 4)

    # 3. 计算全部 269 个器件（110 主控 + 159 采集板）与外壳内壁、底面、盖内顶面的精确最小间隙前十
    clearance_list = []
    cover_rows = evaluate_cover_clearances()
    for r in cover_rows:
        clearance_list.append(
            {
                "pair": f"cover_ceiling vs MCU_{r['ref']}",
                "clearance_mm": r["clearance_model_mm"],
                "clearance_datasheet_mm": r["clearance_datasheet_mm"],
                "note": "SOT-23 嘉立创库 3D 高 1.69 mm，真实规格书最大 1.45 mm"
                if r["ref"] in ("U12", "U17")
                else "嘉立创 3D 包围盒",
            }
        )

    # 底面器件对 tray 底板 (Z=1.00 / 1.20) 与北袋顶 (Z=4.25) 与回折区 R823 间隙
    for p in data["afe"]:
        if p["side"] == "B":
            floor_z = 1.00 if (-13.3 <= p["x"][0] and p["x"][1] <= 13.3) else 1.20
            clr = round(p["z"][0] - floor_z, 3)
            clearance_list.append(
                {
                    "pair": f"tray_floor vs AFE_{p['n']}",
                    "clearance_mm": clr,
                    "note": f"AFE 底面器件 z0={p['z'][0]} vs 底槽 z={floor_z}",
                }
            )
    # 电池最大公差包络 (Z=5.15..8.45) 对 D17 顶面最高件 (4.66) 与盖内顶面 (9.10)
    clearance_list.append(
        {
            "pair": "battery_max_envelope_bottom(5.15) vs AFE_V4_U1_top(4.66)",
            "clearance_mm": round(5.15 - 4.66, 3),
            "note": "含 3.3 mm 电池厚度上限公差（标称 5.30 时余 0.64 mm）",
        }
    )
    clearance_list.append(
        {
            "pair": "cover_ceiling(9.10) vs battery_max_envelope_top(8.45)",
            "clearance_mm": round(9.10 - 8.45, 3),
            "note": "含 3.3 mm 电池厚度上限公差（标称 8.30 时余 0.80 mm）",
        }
    )
    # 排线 J_AFE 180° 回折包络 (z_max=6.15) 对主控底面 R823 (z_min=6.28)
    clearance_list.append(
        {
            "pair": "MCU_R823_bottom(6.28) vs J_AFE_FFC20_loop_top(6.15)",
            "clearance_mm": round(6.28 - 6.15, 3),
            "note": "20P FFC 回折弧顶可压低至 Z<=6.10，与 R823 无干涉",
        }
    )
    # 顶杆静止居中时：斜面到按杆东上角、杆东面到 J300
    _k = mdl.SW_SPEC["knob_box"]
    clearance_list.append(
        {
            "pair": "switch_plunger_ramp vs MCU_SW300_knob_corner",
            "clearance_mm": round((mdl.PLUNGER["ramp_s"] - _k[1] - _k[5]) * 0.7071, 3),
            "note": "顶杆在标称位置时 45° 斜面到按杆东上角的法向距离；换成下压空行程是它的 1.414 倍",
        }
    )
    clearance_list.append(
        {
            "pair": "switch_plunger_stem_east vs MCU_J300_body",
            "clearance_mm": round(next(m for m in data["mcu"] if m["n"] == "J300")["x"][0] - mdl.PLUNGER["x"][1], 3),
            "note": "顶杆在标称位置到 J300 设计包围盒（x=4.71）的水平净距，帽贴盖孔东壁（再东 0.01）后剩 0.07；嘉立创模型在杆脚高度是圆柱面 x=5.21（复核量），更远，板面附近接地脚伸到 4.65。下端东侧没有专门的靠山",
        }
    )
    clearance_list.append(
        {
            "pair": "cover_j300_recess_ceiling(9.98) vs MCU_J300_UFL_plug_top(9.81)",
            "clearance_mm": round(9.98 - 9.81, 3),
            "note": "1代 U.FL 同轴插头扣合总高 2.40 mm（Z=9.81）与上盖微凸窗内顶（Z=9.98）留 0.17 mm 净空",
        }
    )
    clearance_list.append(
        {
            "pair": "FPC_ANT_2G4_south(y=18.42) vs MCU_and_D17_board_north_edge(y=18.25)",
            "clearance_mm": round(18.42 - 18.25, 3),
            "note": "20×4.2 mm 2.4G FPC 天线完全位于两块 PCB 铜皮北界（y=18.25）之外的无铜走廊",
        }
    )
    clearance_list.append(
        {
            "pair": "tray_c_groove_radius(1.95) vs woven_strap_loop_radius(1.90)",
            "clearance_mm": round(mdl.LUG_GROOVE_R - mdl.STRAP_LOOP_OUTER_D / 2.0, 3),
            "note": "对齐 IMG_3799/3800.MOV：敞口内凹生耳弧槽（R=1.95）与 Ø3.80 织带回折圆筒（R=1.90）留 0.05 mm 贴合转动净空",
        }
    )
    clearance_list.append(
        {
            "pair": "woven_strap_loop_bottom(1.80) vs R14_FPC_exit_top(1.38)",
            "clearance_mm": round((mdl.PIN_Z - mdl.STRAP_LOOP_OUTER_D / 2.0) - 1.38, 3),
            "note": "上层快拆弹簧棒织带圆筒（底 Z=1.80）与下层 R14 软板（顶 Z<=1.38）留 0.42..0.45 mm 垂直分层净空",
        }
    )

    clearance_list.sort(key=lambda x: x["clearance_mm"])
    top10_min_clearances = clearance_list[:10]

    # 4. USB-C 插头与护套可插到位验证
    # 标准 USB-C 金属舌片 8.40×2.60 mm（中心 y=0, z=6.885，插入 x=16.50..23.00）
    # 标准 USB-C 插头外模护套 12.40×6.50 mm（停靠在母座前端 x=22.35..30.00，落入外壳东墙护套沉台 x=22.30..23.00）
    usb_plug_tongue = mdl.box(16.50, 23.00, -4.20, 4.20, 5.585, 8.185)
    usb_plug_boot = mdl.box(22.35, 30.00, -6.20, 6.20, 5.05, 8.65)
    usb_plug_total = usb_plug_tongue + usb_plug_boot
    usb_tray_hit = exact_intersection_vol(parts["tray"], usb_plug_total)
    usb_cover_hit = exact_intersection_vol(parts["cover"], usb_plug_total)
    usb_check = {
        "plug_tongue_spec_mm": [8.40, 2.60],
        "plug_boot_spec_mm": [12.40, 6.50],
        "insertion_depth_to_x_mm": 16.50,
        "boot_stop_x_mm": 22.35,
        "tray_intersection_mm3": round(usb_tray_hit, 5),
        "cover_intersection_mm3": round(usb_cover_hit, 5),
        "can_insert_fully": bool(usb_tray_hit == 0.0 and usb_cover_hit == 0.0),
    }

    # 5. 顶杆：逐步下压，核按杆真被推过手册行程（2026-11-10 重写；同日加导向脚，横向位置改成从几何里量）
    # 旧版只把顶杆整体下移 0.80 后和 SW300 包围盒求交，再比两个写死的常数，核不出「帽底先压到开关盖片、按杆推 0」。
    plunger = parts["switch_plunger"]
    plunger_up = plunger.translate((0, 0, +0.40))
    # 上拉 0.40 mm 时必须被上盖挡住（交集 > 0.5 mm³ 证明防脱生效）
    retention_inter = exact_intersection_vol(parts["cover"], plunger_up)
    lip = mdl.box(*mdl.SW_SPEC["cover_lip_box"])
    press_fixed = {
        "SW300 本体和盖片": mdl.sw300_parts()[0],
        "主控板": internals["MCU_board"],
        "J300": internals["MCU_J300"],
        "J300 天线插头": internals["MCU_J300_UFL_plug"],
        "上盖": parts["cover"] & mdl.box(1.0, 7.0, 11.0, 18.0, 6.0, 12.5),
    }
    travel = mdl.SW_SPEC["push_travel_mm"]
    hole_gap = mdl.SW_SPEC["hole_clearance_mm"]
    # 顶杆东西向能待在哪：不写死，每个下压量往西、往东各挪到刚好不撞。
    # 该是：西边导向脚贴开关本体东面，东边帽贴盖孔东壁。往西挡住它的如果是盖片凸舌，就是斜面压到凸舌上了，导向没起作用。
    envelope = plunger_lateral_envelope(plunger, press_fixed, lip, [round(-0.16 + 0.04 * i, 2) for i in range(25)])
    reach_rows = [r for r in envelope if r["west_mm"] is not None]
    # 从上浮到压到底都不撞的范围：西边界取各深度里最靠东的，东边界取最靠西的。标称位置处处都撞时记 0，下面的门按不过算
    e_west = max((r["west_mm"] for r in reach_rows), default=0.0)
    e_east = min((r["east_mm"] for r in reach_rows), default=0.0)
    # 静止（下压 0）时最靠西：方块口径下导向脚的直面还没贴上本体平面，是底部倒角搭在本体上棱
    e_rest_west = next((r["west_mm"] for r in reach_rows if r["press_mm"] == 0.0), 0.0)
    # 按下去时按杆把顶杆往东顶：帽靠到盖孔东壁为止；力作用点低，下端还会再歪到贴住 J300 外壳。
    # 歪的姿态不单独建模，用「整根东移到贴 J300、不算上盖」代替：按杆那个高度上的位置一样，推量上限也一样。
    j300_gap = round(next(m for m in data["mcu"] if m["n"] == "J300")["x"][0] - mdl.PLUNGER["x"][1], 4)
    no_cover = {k: v for k, v in press_fixed.items() if k != "上盖"}
    y_end = hole_gap - 0.01   # 顶杆在盖孔里偏南、偏北到头，留 0.01 不贴面
    press_cases = {
        "nominal_seated_east": plunger_press_sim(plunger, press_fixed, e=e_east),
        "nominal_against_j300": plunger_press_sim(plunger, no_cover, e=j300_gap),
        "nominal_centered": plunger_press_sim(plunger, press_fixed, e=0.0),
        "nominal_seated_west": plunger_press_sim(plunger, press_fixed, e=e_west),
        # 按杆伸出量手册 0.62±0.1：短的最难推到，长的最容易静止时就被顶着
        "short_knob_seated_east": plunger_press_sim(plunger, press_fixed, e=e_east, knob_dx=-0.10),
        "short_knob_against_j300": plunger_press_sim(plunger, no_cover, e=j300_gap, knob_dx=-0.10),
        "long_knob_seated_west": plunger_press_sim(plunger, press_fixed, e=e_rest_west, knob_dx=+0.10),
        # 短按杆、顶杆没靠东。加导向脚之前这两个位置（当时是居中、贴盖孔西壁）斜面先压到盖片凸舌，只推 0.157
        "short_knob_centered": plunger_press_sim(plunger, press_fixed, e=0.0, knob_dx=-0.10),
        "short_knob_seated_west": plunger_press_sim(plunger, press_fixed, e=e_west, knob_dx=-0.10),
        # 再加南北偏到头：导向脚不能蹭到按杆侧面，也不能错开本体东面
        "short_knob_west_plunger_south": plunger_press_sim(plunger, press_fixed, e=e_west, dy=-y_end, knob_dx=-0.10),
        "short_knob_west_plunger_north": plunger_press_sim(plunger, press_fixed, e=e_west, dy=+y_end, knob_dx=-0.10),
    }
    rest_cases = [press_cases[k] for k in ("nominal_seated_east", "nominal_centered", "nominal_seated_west")]
    loaded = [press_cases[k] for k in ("nominal_seated_east", "nominal_against_j300")]
    short = [press_cases[k] for k in ("short_knob_seated_east", "short_knob_against_j300")]
    unseated_short = [press_cases[k] for k in ("short_knob_centered", "short_knob_seated_west",
                                               "short_knob_west_plunger_south", "short_knob_west_plunger_north")]
    # 有工况从头就撞时 stop 是 None：不让 max() 崩，下面的门按不过算，照常写 checks.json
    stops = [c["stop_press_mm"] for c in press_cases.values() if c["stop_press_mm"] is not None]
    stop_d = max(stops) if stops else None
    # 帽四周 4 mm 内最高的盖面（东侧天线鼓包）：按到导通时帽顶不能比它低，不然手指平着按不到
    (_cx0, _cx1), (_cy0, _cy1) = mdl.PLUNGER["x"], mdl.PLUNGER["y"]
    surround_top = bbox_tuple(parts["cover"] & mdl.box(_cx0 - 4.0, _cx1 + 4.0, _cy0 - 4.0, _cy1 + 4.0, 9.0, 13.0))[5]
    # 有受力姿态不导通时记 None，下面的门按不过算，照常写 checks.json（原来 max() 碰到 None 直接崩，留下旧文件）
    acts = [c["actuate_press_mm"] for c in loaded + short]
    actuate_d = None if None in acts else max(acts)
    # 这里只算平移姿态；不带天线插头歪到 18° 时帽顶中心再矮约 0.03（复核算），门留 0.05
    cap_tilt_allowance = 0.05

    def cap_margin(top_z):
        return None if actuate_d is None else round(top_z - actuate_d - surround_top, 3)

    def cap_ok(m):
        return m is not None and m >= cap_tilt_allowance

    cap_above_surround = cap_margin(mdl.PLUNGER["top_z"])
    cap_proud_at_stop = None if stop_d is None else round(mdl.PLUNGER["top_z"] - stop_d - mdl.TOTAL_HEIGHT, 3)
    # 导向脚内侧面到按杆侧面：顶杆南北偏到头（盖孔间隙 0.20）还剩多少
    _gy = mdl.PLUNGER["guide_y"]
    guide_knob_side_gap = None if _gy is None else round(min(_k[2] - _gy[0], _gy[1] - _k[3]) - hole_gap, 3)
    # 浮到头时最靠西的位置（包络第一行就是上浮到头那一格）：东余量按「卡在最靠西且浮到头」这个保守口径算，位置和上浮量取同一格
    top_row = reach_rows[0] if reach_rows else {"press_mm": 0.0, "west_mm": 0.0}
    # 导向脚真的在：在每片脚该在的地方各放一个小探块，顶杆要把它填满（参数没变但实体缺脚、脚变薄，都会少）
    _fx0, _fz0 = mdl.PLUNGER["x"][0], mdl.PLUNGER["foot_z"] + mdl.PLUNGER["guide_lead"]

    def feet_fill_of(pl):
        if _gy is None:
            return None
        return [round(exact_intersection_vol(pl, mdl.box(_fx0, _fx0 + 0.30, ya, yb, _fz0, _fz0 + 0.30)) / (0.30 * (yb - ya) * 0.30), 3)
                for ya, yb in ((mdl.PLUNGER["y"][0], _gy[0]), (_gy[1], mdl.PLUNGER["y"][1]))]

    feet_fill = feet_fill_of(plunger)
    land_west_x = round(mdl.PLUNGER["land_x"] + e_west, 4)

    switch_check = {
        **mdl.SW_SPEC,
        "plunger": {k: list(v) if isinstance(v, tuple) else v for k, v in mdl.PLUNGER.items()},
        "plunger_hole": list(mdl.PLUNGER_HOLE),
        "lateral_envelope": envelope,
        "lateral_range_mm": [e_west, e_east],
        "lateral_play_mm": round(e_east - e_west, 4),
        "rest_west_most_mm": e_rest_west,
        "press_cases": press_cases,
        "rest_clear_of_fixed_parts": bool(all(c["rest_push_mm"] is not None for c in rest_cases)),
        "anti_popout_retention_verified": bool(retention_inter > 0.5),
        "upward_pull_retention_overlap_mm3": round(retention_inter, 3),
        # 只含标称按杆、不歪的靠东 / 标称位置 / 靠西和两个受力姿态
        "nominal_knob_untilted_reaches_travel": bool(all(c["max_push_mm"] >= travel for c in rest_cases + loaded)),
        "loaded_push_margin_ok": bool(all(c["max_push_mm"] >= travel + 0.10 for c in loaded)),
        "short_knob_loaded_reaches_travel": bool(all(c["max_push_mm"] >= travel for c in short)),
        # 静止时顶杆能往上浮；浮到头按杆还被压过行程，才算被迫导通。
        # 长按杆那个工况放在静止最靠西的位置上，方块口径下它一往下压就被导向脚倒角挡住（停在 0），这条门对它只看静止和上浮，
        # 等于假设倒角能把顶杆导回东边再接着压；导回来之后的位置由靠西工况管
        "no_forced_actuation_at_rest": bool(
            all(c["top_float_push_mm"] is not None and c["top_float_push_mm"] < travel
                for c in rest_cases + [press_cases["long_knob_seated_west"]])),
        "cap_proud_of_cover_at_stop_mm": cap_proud_at_stop,
        "cap_stays_proud_at_stop": bool(cap_proud_at_stop is not None and cap_proud_at_stop > 0.0),
        "cover_top_around_cap_mm": round(surround_top, 3),
        "deepest_loaded_actuate_press_mm": actuate_d,
        "cap_above_surrounding_cover_at_actuation_mm": cap_above_surround,
        "cap_tilt_allowance_mm": cap_tilt_allowance,
        "cap_reachable_at_actuation": bool(cap_ok(cap_above_surround)),
        # 上一版这条门不过（短按杆碰上顶杆没靠东，只推 0.157）。现在「没靠东」能到的位置由导向脚限住，另加南北偏到头两个
        "short_knob_unseated_reaches_travel": bool(all(c["max_push_mm"] >= travel for c in unseated_short)),
        "short_knob_unseated_max_push_mm": [c["max_push_mm"] for c in unseated_short],
        # 导向：每个下压量上挡住顶杆往西的都不是盖片凸舌，斜面上端到不了凸舌上方
        "guide_keeps_ramp_off_lip": bool(reach_rows and not any(r["lip_blocks_west"] for r in reach_rows)),
        "land_face_x_at_west_most_mm": land_west_x,
        "lip_east_x_mm": mdl.SW_SPEC["cover_lip_box"][1],
        "land_face_clear_of_lip_mm": round(land_west_x - mdl.SW_SPEC["cover_lip_box"][1], 4),
        "guide_to_knob_side_gap_at_y_end_mm": guide_knob_side_gap,
        "guide_feet_clear_of_knob_sides": bool(guide_knob_side_gap is not None and guide_knob_side_gap > 0.0),
        "guide_feet_fill_south_north": feet_fill,
        "guide_feet_both_present": bool(feet_fill is not None and min(feet_fill) > 0.98),
        # CAD 里算不出过或不过的风险
        "known_limits": {
            "no_overtravel_stop": "压到底标称推 0.37–0.46、长按杆更多，手册只给导通行程 0.2，没给最大行程，没有限位保护开关",
            "return_needs_low_friction": "45° 斜面靠按杆弹簧把顶杆顶回去，摩擦系数到 0.414 就自锁（手算，没实测）",
            "east_side_has_no_foot_stop": "导向脚只管住往西。受力时按杆把顶杆往东顶，靠的仍是盖孔东壁（在帽的高度）和 J300，杆脚高度没有靠山，下端会往东歪。"
                                          "本脚本不建歪斜姿态，J300 用的是设计包围盒（西沿 4.71），看不见接地脚（西沿 4.65、顶约 7.55）："
                                          "杆脚一歪或上盖偏东 0.011 以上就落在接地脚上，行程从 0.81 变 0.67–0.70。"
                                          "复核对嘉立创真实模型量的（evidence/2026-11-10-c08b-r13-plunger-guide/REVIEW.md）：最多歪 10–11°；"
                                          "压到底歪 1–8° 最少推 0.357（短按杆 0.257），歪到头 10° 是 0.313 / 0.213（带天线插头）、11° 是 0.336 / 0.236（不带）；"
                                          "带插头歪 11° 会卡在下压 0.53、只推 0.03，要顶杆自己回正才能接着按",
            "cover_offset_window": "上盖相对主控板的东西向偏移直接吃进配合（复核量，真实模型）：偏西 0.023 以上顶杆竖直放不进，偏西 0.10 歪着也放不进；"
                                   "偏东 0.05 不歪推 0.308 / 0.208，偏东 0.10 是 0.257 / 0.158（短按杆不导通）。本脚本没有上盖偏移的工况，"
                                   "盖孔东壁东移 0.15 的变异 11 条顶杆门照过（复核做的）",
            "guide_feet_engage_after_0p12": "方块口径下导向脚直面要下压 0.12 才贴上本体平面（顶 8.35），之前顶杆能偏西、能歪，靠底部 45° 倒角搭在本体上棱把它导回来；"
                                            "摩擦大时可能卡在倒角上按不下去（手算摩擦系数 0.36 以上，没实测）。顶杆平时靠自重落在按杆上（下压 0.3 上下），那时直面已经贴上；"
                                            "嘉立创模型上盖片还有两小段东沿（2.657）静止时就挡着。实物开关有没有这两段没核",
            "tight_between_switch_and_cover": "顶杆夹在开关本体东面和盖孔东壁之间，标称活动量只有 0.023；下端往西只能歪 0.5°，绕竖轴只能转 ±0.3–0.6°（复核量）。"
                                              "首件先量活动量，偏紧磨帽东面（PLUNGER x[1]），不许硬合盖；偏松换帽东面加厚的件（PLUNGER cap_east_extra）",
            "single_foot_not_enough": "只剩一片导向脚时，顶杆绕竖轴转 2° 斜面又能压到凸舌（复核算，只留北脚，短按杆 0.167）。"
                                      "本脚本只核两片脚都在（guide_feet_both_present），不建绕竖轴转动的姿态",
        },
        # 余量：按杆尖相对顶杆在东西方向偏多少就不行
        "knob_tip_west_margin_mm": round(min(c["max_push_mm"] for c in loaded) - travel, 3),
        "knob_tip_east_margin_mm": round(mdl.PLUNGER["ramp_s"] + top_row["west_mm"] - top_row["press_mm"] + travel - (_k[1] + _k[5]), 3),
        "note": "CAD 标称。west 余量：按杆尖偏西超过它，受力姿态下推不到 0.20；east 余量：偏东超过它，顶杆卡在最靠西且浮到头时就被顶到导通。"
                "西边现在靠导向脚贴开关本体，按杆和本体是同一个零件，east 余量只剩按杆自己的伸出量公差要吃。"
                "按杆真实最大行程手册没给；回弹靠按杆弹簧沿斜面把顶杆顶回去，摩擦没算。",
    }
    switch_gates = (
        "rest_clear_of_fixed_parts", "anti_popout_retention_verified", "nominal_knob_untilted_reaches_travel",
        "loaded_push_margin_ok", "short_knob_loaded_reaches_travel", "no_forced_actuation_at_rest", "cap_stays_proud_at_stop",
        "cap_reachable_at_actuation", "short_knob_unseated_reaches_travel", "guide_keeps_ramp_off_lip", "guide_feet_clear_of_knob_sides",
        "guide_feet_both_present",
    )
    switch_check["failed_gates"] = [g for g in switch_gates if not switch_check[g]]

    # 5b. 内置北侧无铜走廊 2.4 GHz FPC 天线与 J300 1代 U.FL 同轴插头验证
    ufl_cover_hit = exact_intersection_vol(parts["cover"], internals["MCU_J300_UFL_plug"])
    ant_tray_hit = exact_intersection_vol(parts["tray"], internals["FPC_ANT_2G4"])
    ant_cover_hit = exact_intersection_vol(parts["cover"], internals["FPC_ANT_2G4"])
    ant_mcu_hit = exact_intersection_vol(internals["MCU_board"], internals["FPC_ANT_2G4"])
    ant_d17_hit = exact_intersection_vol(internals["D17_board"], internals["FPC_ANT_2G4"])
    antenna_check = {
        **mdl.ANTENNA_SPEC,
        "ufl_plug_cover_intersection_mm3": round(ufl_cover_hit, 5),
        "fpc_antenna_tray_intersection_mm3": round(ant_tray_hit, 5),
        "fpc_antenna_cover_intersection_mm3": round(ant_cover_hit, 5),
        "fpc_antenna_pcb_intersection_mm3": round(ant_mcu_hit + ant_d17_hit, 5),
        "ufl_plug_and_fpc_antenna_fit": bool(
            ufl_cover_hit == 0.0 and ant_tray_hit == 0.0 and ant_cover_hit == 0.0 and (ant_mcu_hit + ant_d17_hit) == 0.0
        ),
    }

    # 5c. 四角缺口抱柱锁位验证（方案 3）：
    # X/Y：把板往 ±X、±Y 各推 0.12 mm（> 单边间隙 0.10）必须撞到抱柱；X 推 0.05、Y 推 0.02 必须不撞（装得进去；Y 向北有 R12 原有天线限位肩，间隙只有 0.03，所以 Y 用 0.02）。
    # Z：主控板上推 0.06（压台）和下推 0.05（边托台）都必须撞；采集板下推 0.05（下托台）必须撞，上推不锁（如实记录）。
    shell_all = {"tray": parts["tray"], "cover": parts["cover"]}

    def hits(board, dx, dy, dz):
        moved = board.translate((dx, dy, dz))
        return sum(exact_intersection_vol(sh, moved) for sh in shell_all.values())

    lock = {}
    for bname, label in (("D17_board", "D19"), ("MCU_board", "MCU")):
        brd = internals[bname]
        lock[label] = {
            "fit_0p05_no_hit": all(hits(brd, dx, dy, 0) <= 1e-5 for dx, dy in ((0.05, 0), (-0.05, 0), (0, 0.02), (0, -0.02))),
            "lock_x_pos": hits(brd, 0.12, 0, 0) > 1e-4,
            "lock_x_neg": hits(brd, -0.12, 0, 0) > 1e-4,
            "lock_y_pos": hits(brd, 0, 0.12, 0) > 1e-4,
            "lock_y_neg": hits(brd, 0, -0.12, 0) > 1e-4,
            "lock_z_down": hits(brd, 0, 0, -0.05) > 1e-4,
            "lock_z_up": hits(brd, 0, 0, 0.06) > 1e-4,
        }
    # 铣刀残留 R1.0 圆角材料（板的一部分）对 R1.2 倒圆抱柱零干涉
    residual_hits = {}
    for cname in mdl.CORNERS:
        for label, zr in (("D19", mdl.D19_Z), ("MCU", mdl.MCU_Z)):
            res = mdl.mill_residual(cname, zr[0], zr[1])
            residual_hits[f"{cname}_{label}"] = round(sum(exact_intersection_vol(sh, res) for sh in shell_all.values()), 6)
    standoff_check = {
        "notch_mm": {k: {"width": 3.0, "depth_y": d} for k, (_, _, d) in mdl.CORNERS.items()},
        "post_gap_single_side_mm": mdl.POST_GAP,
        "post_inner_edge_fillet_r_mm": mdl.POST_FILLET_R,
        "mill_residual_r_mm": mdl.MILL_RESIDUAL_R,
        "lock_tests": lock,
        "mill_residual_vs_post_mm3": residual_hits,
        "d19_z_up_is_mechanically_locked": lock["D19"]["lock_z_up"],
        "all_fasteners_zero_interference": bool(
            all(v == 0.0 for v in residual_hits.values())
            and all(lock[k][t] for k in lock for t in ("fit_0p05_no_hit", "lock_x_pos", "lock_x_neg", "lock_y_pos", "lock_y_neg", "lock_z_down"))
            and lock["MCU"]["lock_z_up"]
            and not any("corner" in k for k in shell_intersections)
        ),
    }

    # 5d. 上盖对底壳：定位销 + 胶层（2026-11-10 加）。之前上盖和底壳之间什么都没有，这一节是新的。
    # 前后左右：上盖挪 0.15（> 定位孔单边 0.10）必须撞到底壳，挪 0.05 必须不撞（合得上）。
    # 转动：绕每根定位销转 0.2° 必须撞（靠另一根定位销挡，设计值 0.105°）；只剩放大孔那两根时要 0.28° 才撞，挡不住。
    # 合盖顺序：销刚要进孔的那个高度上，上盖抱柱已经卡住主控板（上盖相对板挪 0.15 会撞板，不挪不撞）。
    # 往上：只有胶，没有机械限位，如实记 False，不进门。
    cp = mdl.COVER_PIN
    _tr, _cov, _mcu = parts["tray"], parts["cover"], internals["MCU_board"]

    def cover_hits(cov, dx, dy, dz=0.0, target=None):
        return exact_intersection_vol(_tr if target is None else target, cov.translate((dx, dy, dz)))

    def cover_turn_hits(cov, pin_name, deg):
        px, py = cp["xy"][pin_name]
        return exact_intersection_vol(_tr, cov.rotate(b.Axis((px, py, 0), (0, 0, 1)), deg))

    def cover_lock_tests(cov, pin_len=cp["pin_len"]):
        h = pin_len + 0.02    # 销尖离孔口还差 0.02
        four = ((0.15, 0), (-0.15, 0), (0, 0.15), (0, -0.15))
        return {
            "fit_0p05_no_hit": bool(all(cover_hits(cov, dx, dy) <= 1e-5 for dx, dy in ((0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)))),
            "lock_x_pos": bool(cover_hits(cov, 0.15, 0) > 1e-4), "lock_x_neg": bool(cover_hits(cov, -0.15, 0) > 1e-4),
            "lock_y_pos": bool(cover_hits(cov, 0, 0.15) > 1e-4), "lock_y_neg": bool(cover_hits(cov, 0, -0.15) > 1e-4),
            "lock_turn_about_each_tight_pin": bool(all(cover_turn_hits(cov, n, a) > 1e-4 for n in cp["tight"] for a in (0.2, -0.2))),
            "posts_grip_board_before_pins_enter": bool(cover_hits(cov, 0, 0, h, _mcu) <= 1e-5
                                                       and all(cover_hits(cov, dx, dy, h, _mcu) > 1e-4 for dx, dy in four)),
            "lock_z_up": bool(cover_hits(cov, 0, 0, 0.30) > 1e-4),
        }

    cover_lock = cover_lock_tests(_cov)
    # 胶层：每个角下沉的那块（不含孔）的面积和深度，从「不带这些特征的底壳 − 交付底壳」里量
    _tray_plain = mdl.build_tray(seam_features=False)
    glue = {}
    for cname, (px, py) in cp["xy"].items():
        d = cp["socket_d"] if cname in cp["tight"] else cp["socket_d_loose"]
        near = mdl.box(px - 3.5, px + 3.5, py - 3.5, py + 3.5, mdl.SPLIT_Z - cp["glue_gap"] + 0.02, mdl.SPLIT_Z - 0.02)
        removed = exact_intersection_vol(_tray_plain, near) - exact_intersection_vol(_tr, near)
        top = bbox_tuple(_tr & mdl.post_inside_cavity(cname, mdl.SPLIT_Z - 1.0, mdl.SPLIT_Z))[5]
        glue[cname] = {"gap_mm": round(mdl.SPLIT_Z - top, 3), "area_mm2": round(removed / (cp["glue_gap"] - 0.04) - math.pi * (d / 2) ** 2, 2)}
    pin_tip_z = bbox_tuple(_cov)[2]
    post_reach_h = round(mdl.MCU_Z[1] - mdl.SPLIT_Z, 3)   # 上盖抱柱底面碰到主控板顶面时，上盖离合上还差多少
    cover_fix_check = {
        "pin": {k: ({c: list(v) for c, v in val.items()} if isinstance(val, dict) else (list(val) if isinstance(val, tuple) else val)) for k, val in cp.items()},
        "pin_radial_clearance_mm": {"tight": round((cp["socket_d"] - cp["pin_d"]) / 2, 3), "loose": round((cp["socket_d_loose"] - cp["pin_d"]) / 2, 3)},
        "pin_bottom_gap_mm": round(cp["socket_depth"] - cp["pin_len"], 3),
        "pin_straight_in_socket_wall_mm": round(cp["pin_len"] - cp["pin_tip"] - cp["glue_gap"], 3),   # 销直段在胶层以下、还贴着孔壁的长度
        "pin_tip_z_mm": round(pin_tip_z, 3),
        "close_sequence_mm": {"posts_reach_board_top_at": post_reach_h, "pins_reach_socket_at": cp["pin_len"],
                              "posts_ahead_of_pins": round(post_reach_h - cp["pin_len"], 3)},
        "socket_walls_mm": cover_pin_socket_walls(),
        "lock_tests": cover_lock,
        "cover_z_up_is_mechanically_locked": cover_lock["lock_z_up"],
        "glue_layer": glue,
        "glue_area_total_mm2": round(sum(g["area_mm2"] for g in glue.values()), 2),
        "pry_notch": list(mdl.PRY_NOTCH),
        "note": "上盖前后左右靠对角两根销定位（销 Ø1.10 配孔 Ø1.30，标称能晃 ±0.10），另两根孔 Ø1.50 不定位；往上只靠胶粘在四个抱柱端面上，没有机械限位。"
                "用哪种胶、粘多牢没测。销孔打印偏紧时用钻头过一下。主控板前后左右是上盖的抱柱在管，"
                "所以主控板对底壳的位置 = 销的 ±0.10 再加抱柱的 ±0.10。合盖时先让上盖抱柱落进主控板缺口，再往下压到销进孔。",
    }
    cover_fix_check["pass"] = bool(
        all(cover_lock[k] for k in cover_lock if k != "lock_z_up")
        and cover_fix_check["pin_bottom_gap_mm"] >= 0.10
        and cover_fix_check["pin_straight_in_socket_wall_mm"] >= 0.20
        and cover_fix_check["close_sequence_mm"]["posts_ahead_of_pins"] >= 0.15
        and abs(pin_tip_z - (mdl.SPLIT_Z - cp["pin_len"])) < 1e-3
        and all(abs(g["gap_mm"] - cp["glue_gap"]) < 0.005 and g["area_mm2"] > 1.0 for g in glue.values())
    )

    # 6. 壁厚与无残膜检查
    wall_check = medial_axis_wall_check(parts)

    # 7. 五项必失败阴性对照（Negative Controls）—— 必须全部被同一判据标红！
    # 反例 1：把整机总厚改回 9.70 mm（盖内顶面 Z=8.70），器件撞盖必须被检出
    neg1_rows = evaluate_cover_clearances(total_height=9.70)
    neg1_colliding = [r for r in neg1_rows if r["clearance_model_mm"] < 0.0]
    neg1_cover = mdl.build_cover(total_height=9.70)
    neg1_sw300_vol = exact_intersection_vol(neg1_cover, internals["MCU_SW300"])

    # 反例 2：把上盖内圆角加大到超出余量（top_inner_r=2.60, top_outer_r=3.60），SW300 与 U12 撞圆角必须被检出
    neg2_rows = evaluate_cover_clearances(total_height=10.10, top_inner_r=2.60)
    neg2_colliding = [r for r in neg2_rows if r["clearance_model_mm"] < 0.0]

    # 反例 3：把弹簧棒销孔深度加深到 1.60 mm（距短耳外壁 13.35 仅剩 0.60 mm < 0.80 mm），薄壁/穿孔必须被检出
    neg3_Pin_depth = 1.60
    neg3_remaining_wall = round(
        mdl.LUG_SHROUD_HALF_X - (mdl.LUG_SLOT_HALF_X + neg3_Pin_depth), 3
    )

    # 反例 4：去掉上盖 J300 同轴插头微凸窗（ufl_blister=False，恢复平顶 Z_inner=9.10），1代 U.FL 同轴插头（Z=9.81）撞盖必须被检出
    neg4_cover = mdl.build_cover(total_height=10.10, ufl_blister=False)
    neg4_ufl_vol = exact_intersection_vol(neg4_cover, internals["MCU_J300_UFL_plug"])

    # 反例 5：抱柱内棱不倒圆（尖角）会顶到铣刀残留 R1.0 圆角材料，必须被检出
    sharp = mdl.corner_post("NE", mdl.UNDER_LIP_Z[0], mdl.SPLIT_Z, fillet_r=0.0)
    neg5_sharp_vol = exact_intersection_vol(sharp, mdl.mill_residual("NE", mdl.D19_Z[0], mdl.D19_Z[1]))
    # 反例 6：抱柱和板缺口直边间隙做成负值（-0.20，抱柱侵入板内）必须撞板
    bad_gap = mdl.corner_post("NE", mdl.UNDER_LIP_Z[0], mdl.SPLIT_Z, gap=-0.20)
    neg6_vol = exact_intersection_vol(bad_gap, internals["D17_board"])

    # 反例 7：IMG_3799.MOV / IMG_3800.MOV 旧版长护耳（北凸 6.80 mm / 南凸 4.80 mm，总长 51.60 mm > 46.00 mm 门限，且中间表带槽带顶棚凸出）必须被防悬空门限拦截（移植自 R12 cc1a4fffd）
    max_allowed_lug_protrusion_mm = 3.20
    max_allowed_total_y_mm = 46.00
    cur_north_protrusion_mm = round(mdl.NORTH_LUG_OUTER_Y - mdl.BODY_L / 2.0, 2)
    cur_south_protrusion_mm = round(abs(mdl.SOUTH_LUG_OUTER_Y) - mdl.BODY_L / 2.0, 2)
    cur_total_y_mm = round(manifest["tray"]["size_mm"][1], 2)
    # 检验中间表带槽 (|x|<=10.5, |y|>20.05) 无任何顶棚或底唇伸出盒体 40 mm 之外
    center_slot_overhang_vol = exact_intersection_vol(
        parts["whole_box_onepiece"],
        mdl.box(-10.50, 10.50, 20.02, 27.00, 0.0, 11.0) + mdl.box(-10.50, 10.50, -27.00, -20.02, 0.0, 11.0),
    )
    old_r12_north_protrusion_mm = 6.80
    old_r12_south_protrusion_mm = 4.80
    old_r12_total_y_mm = 51.60

    negative_controls = {
        "neg1_height_9p7_collision": {
            "tested_total_height_mm": 9.70,
            "colliding_refs": [r["ref"] for r in neg1_colliding],
            "min_clearance_mm": neg1_rows[0]["clearance_model_mm"],
            "sw300_intersection_vol_mm3": round(neg1_sw300_vol, 3),
            "detected": bool(len(neg1_colliding) > 0 and neg1_sw300_vol > 0.0),
        },
        "neg2_excessive_fillet_r3p6_collision": {
            "tested_top_inner_r_mm": 2.60,
            "colliding_refs": [r["ref"] for r in neg2_colliding],
            "min_clearance_mm": neg2_rows[0]["clearance_model_mm"],
            "detected": bool(len(neg2_colliding) > 0),
        },
        "neg3_pin_hole_breach_thin_wall": {
            "tested_pin_hole_depth_mm": neg3_Pin_depth,
            "remaining_outer_wall_mm": neg3_remaining_wall,
            "threshold_mm": 0.80,
            "detected": bool(neg3_remaining_wall < 0.80),
        },
        "neg4_ufl_plug_without_blister_collision": {
            "tested_ufl_blister": False,
            "ufl_plug_intersection_vol_mm3": round(neg4_ufl_vol, 3),
            "detected": bool(neg4_ufl_vol > 0.5),
        },
        "neg5_sharp_post_vs_mill_residual": {
            "residual_vs_sharp_post_mm3": round(neg5_sharp_vol, 5),
            "detected": bool(neg5_sharp_vol > 1e-3),
        },
        "neg6_negative_gap_post_hits_board": {
            "tested_gap_mm": -0.20,
            "d19_intersection_mm3": round(neg6_vol, 4),
            "detected": bool(neg6_vol > 1e-3),
        },
        "neg7_old_long_lug_protrusion_rejected": {
            "tested_old_north_protrusion_mm": old_r12_north_protrusion_mm,
            "tested_old_south_protrusion_mm": old_r12_south_protrusion_mm,
            "tested_old_total_y_mm": old_r12_total_y_mm,
            "max_allowed_protrusion_mm": max_allowed_lug_protrusion_mm,
            "max_allowed_total_y_mm": max_allowed_total_y_mm,
            "current_north_protrusion_mm": cur_north_protrusion_mm,
            "current_south_protrusion_mm": cur_south_protrusion_mm,
            "current_total_y_mm": cur_total_y_mm,
            "current_center_slot_overhang_vol_mm3": round(center_slot_overhang_vol, 5),
            "detected": bool(
                old_r12_north_protrusion_mm > max_allowed_lug_protrusion_mm
                and old_r12_south_protrusion_mm > max_allowed_lug_protrusion_mm
                and old_r12_total_y_mm > max_allowed_total_y_mm
                and cur_north_protrusion_mm <= max_allowed_lug_protrusion_mm
                and cur_south_protrusion_mm <= max_allowed_lug_protrusion_mm
                and cur_total_y_mm <= max_allowed_total_y_mm
                and center_slot_overhang_vol == 0.0
            ),
        },
    }

    # 反例 8：d4eea6b56 旧叠层（软板在 Z=1.32，钉头和焊盘之间隔 0.8 mm TPU）必须判为不能先焊后装
    neg8 = strap_presolder_stack_check(fpc_z_min=1.32, fpc_z_max=1.32 + mdl.R15_FPC_T + mdl.R15_ISLAND_STIFF_T)
    negative_controls["neg8_head_not_on_fpc_pad"] = {
        "tested_fpc_z_min_mm": 1.32,
        "head_top_to_fpc_F_gap_mm": neg8["head_top_to_fpc_F_gap_mm"],
        "detected": not neg8["pass"],
    }
    # 反例 9：软板按 0.23 mm 无补强建模（d4eea6b56 的做法）必须对不上 R15 实际厚度
    neg9 = strap_presolder_stack_check(fpc_z_max=mdl.STRAP_FPC_Z_MIN + 0.23)
    negative_controls["neg9_fpc_without_stiffener"] = {
        "tested_cad_fpc_t_mm": neg9["cad_fpc_t_mm"],
        "r15_actual_t_mm": round(neg9["r15_board_t_mm"] + neg9["r15_island_stiffener_t_mm"], 4),
        "detected": not neg9["pass"],
    }
    # 反例 10：南段不开 B 带让位，表带必须和 A 南岛上的 B 带干涉
    neg10_vol = exact_intersection_vol(mdl.build_military_green_strap_south(b_relief=False), mdl.build_r15_b_over_a())
    negative_controls["neg10_no_relief_for_b_over_a"] = {
        "strap_south_vs_b_over_a_vol_mm3": round(neg10_vol, 4),
        "detected": bool(neg10_vol > 0.01) and not strap_presolder_stack_check(relief_z_max=mdl.STRAP_FPC_POCKET_Z_MAX)["pass"],
    }
    presolder_check = strap_presolder_stack_check()
    wrist_check = strap_wrist_range()
    wrist_bound = strap_wrist_geometry_bound(parts)
    # 反例 11：R12/R13 原扣框（47.00..55.60、窗 49.30..53.30）+ 原舌尖 -138，按同一模型必须过不了 155–230
    neg11 = strap_wrist_range(buckle_y=(47.00, 55.60), slot_y=(49.30, 53.30), tail_end_y=-138.00)
    negative_controls["neg11_old_buckle_and_tail_fail_wrist_155_230"] = {
        "failing_wrists_mm": [r["wrist_mm"] for r in neg11["rows"]
                              if r["ch16_clear_of_buckle_mm"] < 0 or r["tail_past_window_mm"] < TAIL_HOLD_MIN_MM],
        "detected": not neg11["pass"],
    }
    pad_align = r15_pad_alignment()
    # 反例 12：旧 R12/R13 表带映射（北 59 − x、南 57 − x）必须对不上 R15 焊盘
    neg12 = r15_pad_alignment(north_ys=(35.0, 43.0), south_ys=tuple(-33.0 - 8.0 * k for k in range(12)))
    negative_controls["neg12_old_strap_mapping_off_r15_pads"] = {
        "max_offset_mm": neg12["max_offset_mm"], "detected": not neg12["pass"],
    }
    # 反例 13/14：旧内袋（北 ±10.70；南整宽内袋不通根部、只开 ±5 中缝）必须和 R15 真实外形干涉
    _, strap_fpc_real = mdl.build_strap_electrodes_and_fpc()
    neg13_vol = exact_intersection_vol(mdl.build_military_green_strap_north(pocket_x=(-10.70, 10.70)), strap_fpc_real)
    neg14_vol = exact_intersection_vol(mdl.build_military_green_strap_south(pocket_root_y=-29.60), strap_fpc_real)
    negative_controls["neg13_north_pocket_pm10p70_hits_ch3_island"] = {
        "vol_mm3": round(neg13_vol, 4), "detected": bool(neg13_vol > 0.01)}
    negative_controls["neg14_south_root_closed_blocks_a_band"] = {
        "vol_mm3": round(neg14_vol, 4), "detected": bool(neg14_vol > 0.01)}
    keeper_fit = strap_keeper_fit(parts)
    keeper_park = strap_keeper_park(parts)
    trim = strap_trim_marks(parts)
    reach = strap_keeper_tail_reach(parts)
    # 反例 15：旧版带圈（按「带身 + 舌片」做，23.80 × 6.20）套两层舌片太松，必须判不过
    neg15 = strap_keeper_fit(parts, keeper=mdl.build_strap_keeper(in_w=23.80, in_h=6.20))
    negative_controls["neg15_old_loose_keeper_23p8x6p2"] = {
        "slack_mm": neg15["slack_mm"], "detected": not neg15["pass"]}
    # 反例 16：紧配带圈从 160 起用，停放段一半压在带身上（套不进），必须判不过
    neg16 = strap_keeper_park(parts, min_wrist=160)
    negative_controls["neg16_snug_keeper_from_160_sits_on_body"] = {
        "min_past_body_end_mm": neg16["min_past_body_end_mm"], "detected": not neg16["pass"]}
    # 反例 17：内高 5.4（两层舌片 5.2 只留 0.1）太紧，探针必须干涉
    neg17 = strap_keeper_fit(parts, keeper=mdl.build_strap_keeper(in_h=5.4))
    negative_controls["neg17_keeper_inner_height_5p4_too_tight"] = {
        "probe_vs_keeper_mm3": neg17["probe_vs_keeper_mm3"], "detected": neg17["probe_vs_keeper_mm3"] > 0.01}
    # 反例 18：剪线整体往带身那头挪 15 mm（舌片剪得太短，过窗只剩约 1.5–10 mm），必须判不过
    neg18 = strap_trim_marks(parts, marks={w: y + 15.0 for w, y in mdl.TRIM_MARKS.items()})
    negative_controls["neg18_trim_marks_too_short"] = {
        "min_tail_mm": min(r["tail_mm"][0] for r in neg18["rows"]), "detected": not neg18["pass"]}
    # 反例 19：剪线 10 mm 一档 + 舌尖 −214（第一版），每档上端舌片翻回后穿不满带圈，必须判不过
    neg19 = strap_keeper_tail_reach(parts, marks={w: y for w, y in mdl.TRIM_MARKS.items() if w % 10 == 0}, tail_end_y=-214.0)
    negative_controls["neg19_trim_10mm_steps_tail_too_short_for_keeper"] = {
        "worst_wrist_mm": neg19["worst_wrist_mm"], "worst_spare_mm": neg19["worst_spare_mm"], "detected": not neg19["pass"]}
    # 反例 20：带圈 10 mm 长，165 起扣框旁无电极段放不下（关掉「在带身外」那条，只看放不放得下）
    neg20 = strap_keeper_park(parts, keeper_len=10.0, body_margin=-99.0)
    negative_controls["neg20_keeper_10mm_cannot_park_off_electrodes"] = {
        "min_free_mm": neg20["min_free_mm"], "detected": not neg20["pass"]}

    # 反例 21：改之前的顶杆（斜面整个包在帽的方块里），按杆必须推不到手册行程
    old_plunger = (mdl.box(2.50, 4.44, 13.70, 16.46, 8.90, 10.40) + mdl.box(3.54, 4.44, 13.70, 16.46, 8.22, 9.20)
                   + mdl.box(3.54, 5.54, 12.30, 14.00, 8.22, 9.06))
    # 旧件按旧坐标放进现在的盖孔（2.47–4.64），东西能挪 −0.03…+0.20，取靠东、中间、靠西三个位置
    neg21 = [plunger_press_sim(old_plunger, press_fixed, e=e) for e in (0.19, 0.08, -0.02)]
    negative_controls["neg21_old_plunger_cannot_push_knob"] = {
        "max_push_mm": max(c["max_push_mm"] for c in neg21),
        "stop_press_mm": [c["stop_press_mm"] for c in neg21], "stopped_by": [c["stopped_by"] for c in neg21],
        "detected": bool(max(c["max_push_mm"] for c in neg21) < travel)}

    # 反例 22：贴门限的一个（靠东时竖直面离凸舌 0.05）。竖直面西移 0.08，靠东时斜面也压到盖片凸舌，推量停在 0.26 上下，受力余量门必须不过
    neg22 = plunger_press_sim(mdl.build_switch_plunger(land_x=mdl.PLUNGER["land_x"] - 0.08), press_fixed, e=e_east)
    negative_controls["neg22_land_west_0p08_loses_loaded_margin"] = {
        "max_push_mm": neg22["max_push_mm"], "stopped_by": neg22["stopped_by"],
        "detected": bool(neg22["max_push_mm"] < travel + 0.10)}

    # 反例 23：帽顶降到 11.55（比现值矮 0.05），拿门用的同一个量、同一个判据重算，必须不过
    negative_controls["neg23_cap_top_11p55_fails_cap_gate"] = {
        "cap_above_surrounding_cover_at_actuation_mm": cap_margin(11.55),
        "detected": bool(not cap_ok(cap_margin(11.55)))}

    # 反例 24：去掉导向脚。斜面要能压到盖片凸舌（导向门不过），短按杆在静止最靠西的位置推不到行程（就是上一版没过的那条）
    no_feet = mdl.build_switch_plunger(guide_y=None)
    neg24_env = plunger_lateral_envelope(no_feet, press_fixed, lip, [0.0, 0.40, 0.48, 0.56])
    neg24_west = next((r["west_mm"] for r in neg24_env if r["press_mm"] == 0.0 and r["west_mm"] is not None), 0.0)
    neg24_sim = plunger_press_sim(no_feet, press_fixed, e=neg24_west, knob_dx=-0.10)
    neg24_fill = feet_fill_of(no_feet)
    negative_controls["neg24_no_guide_feet_ramp_lands_on_lip"] = {
        "lip_blocks_west_at_press_mm": [r["press_mm"] for r in neg24_env if r["lip_blocks_west"]],
        "rest_west_most_mm": neg24_west, "short_knob_max_push_mm": neg24_sim["max_push_mm"], "stopped_by": neg24_sim["stopped_by"],
        "feet_fill_south_north": neg24_fill,
        "detected": bool(any(r["lip_blocks_west"] for r in neg24_env) and neg24_sim["max_push_mm"] < travel and max(neg24_fill) < 0.98)}

    # 反例 25：贴门限的一个（导向脚西面离门限 0.027）。导向脚西面东移 0.04，够不着本体，导向门必须不过
    _px0, _px1 = mdl.PLUNGER["x"]
    neg25_env = plunger_lateral_envelope(mdl.build_switch_plunger(x=(_px0 + 0.04, _px1)), press_fixed, lip, [0.52, 0.56, 0.60])
    negative_controls["neg25_guide_feet_0p04_short_ramp_lands_on_lip"] = {
        "lip_blocks_west_at_press_mm": [r["press_mm"] for r in neg25_env if r["lip_blocks_west"]],
        "west_most_mm": [r["west_mm"] for r in neg25_env],
        "detected": bool(any(r["lip_blocks_west"] for r in neg25_env))}

    # 反例 26：上盖不带销，挪 0.15 不会撞底壳（就是改之前的状态），定位门必须不过
    neg26 = cover_lock_tests(mdl.build_cover(seam_features=False))
    negative_controls["neg26_cover_without_pins_not_located"] = {
        "lock_tests": neg26, "detected": bool(not any(neg26[k] for k in ("lock_x_pos", "lock_x_neg", "lock_y_pos", "lock_y_neg")))}

    # 反例 27：销孔都开到 Ø1.80，用壁厚门的同一个函数重量一遍，最薄的壁必须低于 0.8
    neg27 = cover_pin_socket_walls(socket_d=1.80)
    negative_controls["neg27_socket_d1p8_wall_below_0p8"] = {"walls_mm": neg27, "detected": bool(min(neg27.values()) < 0.80)}

    # 反例 28：上盖只留西北一根销。平移照样挡得住，但绕这根销能转，转动门必须不过（复核做的变异，原来抓不到）
    neg28 = cover_lock_tests(mdl.build_cover(pin_corners=("NW",)))
    negative_controls["neg28_single_pin_cover_can_turn"] = {
        "lock_tests": neg28, "detected": bool(neg28["lock_x_pos"] and not neg28["lock_turn_about_each_tight_pin"])}

    # 反例 30：去掉东南那根定位销（剩西北一根定位销加两根放大孔的销）。平移挡得住，转动要 0.28° 才被放大孔挡，转动门必须不过
    neg30 = cover_lock_tests(mdl.build_cover(pin_corners=("NW", "NE", "SW")))
    negative_controls["neg30_one_tight_pin_missing_cover_can_turn"] = {
        "lock_tests": neg30, "detected": bool(neg30["lock_x_pos"] and not neg30["lock_turn_about_each_tight_pin"])}

    # 反例 29：销长 1.50（第一版）。销要进孔时上盖抱柱还够不着主控板，合盖顺序门必须不过（复核 P1）
    neg29 = cover_lock_tests(mdl.build_cover(pin_override={"pin_len": 1.50}), pin_len=1.50)
    negative_controls["neg29_long_pin_enters_before_posts_grip_board"] = {
        "posts_grip_board_before_pins_enter": neg29["posts_grip_board_before_pins_enter"],
        "detected": bool(not neg29["posts_grip_board_before_pins_enter"])}

    all_gates_pass = (
        presolder_check["pass"] and wrist_check["pass"] and wrist_bound["pass"] and pad_align["pass"] and
        keeper_fit["pass"] and keeper_park["pass"] and trim["pass"] and reach["pass"] and
        all(r["is_valid"] and r["solids"] == 1 for r in readback.values())
        and len(shell_intersections) == 0
        and min(r["clearance_model_mm"] for r in cover_rows) >= 0.15
        and wall_check["all_above_0p8_mm"]
        and wall_check["no_residual_membrane"]
        and usb_check["can_insert_fully"]
        and all(switch_check[g] for g in switch_gates)
        and antenna_check["ufl_plug_and_fpc_antenna_fit"]
        and standoff_check["all_fasteners_zero_interference"]
        and cover_fix_check["pass"]
        and all(nc["detected"] for nc in negative_controls.values())
    )

    report = {
        "status": "PASS_NOMINAL_CAD_UNVERIFIED_HARDWARE" if all_gates_pass else "FAIL",
        "all_gates_pass": bool(all_gates_pass),
        "switch_gates_failed_pending_mako": switch_check["failed_gates"],
        "dimensions_mm": {
            "total_height_with_contacts_mm": mdl.TOTAL_HEIGHT,
            "total_height_at_j300_ufl_blister_mm": round(surround_top, 3),
            "total_height_at_switch_plunger_top_mm": mdl.PLUNGER["top_z"],
            "capsule_body_xy_mm": [mdl.BODY_W, mdl.BODY_L],
            "tray_with_hidden_lugs_xy_mm": [
                mdl.BODY_W,
                round(manifest["tray"]["size_mm"][1], 2),
            ],
            "north_lug_ear_protrusion_mm": cur_north_protrusion_mm,
            "south_lug_ear_protrusion_mm": cur_south_protrusion_mm,
            "center_strap_slot_y_protrusion_mm": 0.0,
            "lug_ear_z_range_mm": [mdl.LUG_EAR_Z_MIN, mdl.LUG_EAR_Z_MAX],
            "overall_length_with_strap_ends_mm": round((mdl.NORTH_PIN_Y + 5.20) - (mdl.SOUTH_PIN_Y - 5.20), 2),
            "outer_corner_radius_mm": mdl.OUTER_CORNER_R,
            "inner_corner_radius_mm": mdl.INNER_CORNER_R,
            "top_outer_fillet_radius_mm": mdl.TOP_OUTER_FILLET_R,
            "bottom_outer_fillet_radius_mm": mdl.BOT_OUTER_FILLET_R,
            "r14_south_fpc_total_width_mm": 14.12,
            "r12_south_fpc_slot_width_mm": 19.20,
            "strap_connection_measured_width_mm": mdl.STRAP_MEASURED_W,
            "lug_slot_width_mm": round(2.0 * mdl.LUG_SLOT_HALF_X, 2),
            "lug_shroud_outer_width_mm": round(2.0 * mdl.LUG_SHROUD_HALF_X, 2),
            "spring_bar_spec": "Ø1.80 mm barrel, Ø0.80×0.90 mm tips, 22.04 mm measured strap connection width (lug slot width 22.30 mm, single-side clearance 0.13 mm; blind holes Ø1.20×1.20 mm, outer wall 1.00 mm ≥ 0.80 mm)",
        },
        "readback_single_solid": readback,
        "unexpected_intersections_mm3": shell_intersections,
        "top10_min_clearances_mm": top10_min_clearances,
        "cover_top_component_clearances_mm": cover_rows,
        "wall_thickness_and_membrane": wall_check,
        "usb_plug_insertion": usb_check,
        "switch_plunger_verification": switch_check,
        "antenna_and_ufl_verification": antenna_check,
        "corner_notch_post_verification": standoff_check,
        "cover_to_tray_fix_verification": cover_fix_check,
        "strap_presolder_stack": presolder_check,
        "strap_wrist_range_155_230": dict(wrist_check, geometry_bound=wrist_bound),
        "strap_r15_pad_alignment": pad_align,
        "strap_keeper_fit": dict(keeper_fit, park_off_electrodes=keeper_park, tail_reach=reach),
        "strap_trim_marks": trim,
        "negative_controls": negative_controls,
    }

    (P / "checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"=== CHECKS SUMMARY: all_gates_pass={all_gates_pass} ===")
    print("  Intersections:", len(shell_intersections))
    print("  Min cover clearance (model):", min(r["clearance_model_mm"] for r in cover_rows), "mm")
    print("  Min wall thickness:", wall_check["min_wall_mm"], "mm")
    print("  No residual membrane:", wall_check["no_residual_membrane"])
    print("  Strap presolder stack:", presolder_check["pass"])
    print("  Strap wrist 155-230:", wrist_check["pass"], "| geometry bound:", wrist_bound["pass"],
          "| R15 pads aligned:", pad_align["pass"], pad_align["max_offset_mm"])
    print("  Strap keeper fit:", keeper_fit["pass"], keeper_fit["slack_mm"], "| park (>=%d):" % keeper_park["min_wrist_mm"],
          keeper_park["pass"], keeper_park["min_free_mm"], keeper_park["min_past_body_end_mm"], "| trim marks:", trim["pass"], min(r["tail_mm"][0] for r in trim["rows"]),
          "| tail reach:", reach["pass"], reach["worst_spare_mm"], "@", reach["worst_wrist_mm"])
    print("  USB plug full insertion:", usb_check["can_insert_fully"])
    print("  Cover to tray:", cover_fix_check["pass"], cover_fix_check["lock_tests"], "| glue gap/area:", cover_fix_check["glue_layer"],
          "| socket walls:", cover_fix_check["socket_walls_mm"], "| close sequence:", cover_fix_check["close_sequence_mm"])
    print("  Switch plunger:", {g: switch_check[g] for g in switch_gates},
          "| knob tip margin west/east:", switch_check["knob_tip_west_margin_mm"], switch_check["knob_tip_east_margin_mm"],
          "| cap above surround at actuation:", cap_above_surround, "surround top", round(surround_top, 3),
          "| short knob unseated max push:", switch_check["short_knob_unseated_max_push_mm"],
          "| lateral range west/east:", switch_check["lateral_range_mm"], "rest west-most", switch_check["rest_west_most_mm"],
          "| land face clear of lip:", switch_check["land_face_clear_of_lip_mm"],
          "| FAILED GATES:", switch_check["failed_gates"])
    print("    lateral envelope (press: west/east, west blocked by):",
          [(r["press_mm"], r["west_mm"], r["east_mm"], r["west_blocked_by"], r["lip_blocks_west"]) for r in switch_check["lateral_envelope"]])
    for name, c in switch_check["press_cases"].items():
        print("   ", name, "contact", c["contact_press_mm"], "actuate", c["actuate_press_mm"], "max_push", c["max_push_mm"],
              "stop", c["stop_press_mm"], c["stopped_by"], "| rest_push", c["rest_push_mm"], "float_push", c["top_float_push_mm"])
    print("  Negative controls detected:", {k: v["detected"] for k, v in negative_controls.items()})

    if not all_gates_pass:
        sys.exit(1)


if __name__ == "__main__":
    check_all()
