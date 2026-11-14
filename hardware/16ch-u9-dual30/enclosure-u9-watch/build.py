#!/usr/bin/env python3
"""OpenEMG 16ch 旗舰双板（MCU-U9 + AFE-30P + 双 30P 表带软板）圆润手表外壳生成器。

设计特征：
1. 适配升级 1.00 mm 超薄双面接触 30P 连接器（C324727）与 0.80 mm 四层圆角板框后的 AFE-30P，
   以及扩窗版 6 层圆角双核主控 MCU-U9（含 27.40 × 20.90 mm 电池镂空窗）。
2. 俯视 46.80 × 40.00 mm（四角 R3.80 圆角），上盖顶面 R2.40 大圆角，底壳底面 R0.70 圆角；
   壳体净高 Z = 0.15 .. 10.55 mm（10.40 mm），较 2.00 mm 高连接器方案减薄逾 2.0 mm。
3. 隐藏式四角反锁结构：底壳外底四角（|X| >= 19.65 mm，完全避开中间 |X| <= 11.12 mm 软板区）设沉头孔，
   4 颗 M1.4 螺丝自下而上穿过双板 Ø2.00 mm 安装孔与板间绝缘柱，盲锁入上盖四角下压柱，上盖顶面与四周零外露螺丝孔；
   外扣六孔贴肤底盖 cap_bottom 扣合后将底面四角螺丝孔一并遮蔽。
4. 东侧（+X）集成圆角 Type-C 插口（含插头护套沉台）与防脱侧按按键帽 side_button（对齐 MCU-U9 U1 侧按开关，
   静止间隙 0.198 mm，向内按压 0.70 mm 即可推动开关按头 0.502 mm 满行程）。
5. 北侧（+Y）严格按 ../strap-fpc-30p/geometry.json 开双 30P 软板穿底槽与壳内回折袋；
   南北两端继承低剖面 22.30 mm 快拆弹簧棒生耳槽（配标准 22 mm 快拆表带，底部抬高防悬空）。

导出产物：
- 单实体可打印件（各 1 solid）：tray.{step,stl}, cover.{step,stl}, side_button.{step,stl}, cap_bottom.{step,stl}
- 整机满载预览与爆炸图（含双板全部 926 个真实 3D 器件实体）：assembly.{step,glb}, exploded.{step,glb}
- 结构尺寸与体积清单：manifest.json
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
STRAP_GEOM_PATH = HERE.parent / "strap-fpc-30p" / "geometry.json"
AFE_STEP_PATH = HERE.parent / "afe-30p-3d.step"
MCU_STEP_PATH = HERE.parent / "mcu-u9-3d.step"
STRAP_A_STEP_PATH = HERE.parent / "strap-fpc-30p" / "strap-30p-a-3d.step"
STRAP_B_STEP_PATH = HERE.parent / "strap-fpc-30p" / "strap-30p-b-3d.step"

# ---------------------------------------------------------------------------
# 1. 整表坐标系常量（单位 mm；X 东西横跨 46.8，Y 南北沿表带 40.0，Z 向上朝表盘顶）
# ---------------------------------------------------------------------------
TRAY_Z_MIN = 0.15            # 底壳外底基准 Z
FLOOR_Z_TOP = 1.00           # 底壳内腔底面 Z（底板实厚 0.85 mm >= 0.80 mm）
AFE_Z_BASE = 2.45            # AFE-30P 板底 Z（板顶 3.2504；背面 U2 最低 Z=1.150，背面 FPC3 最低 Z=1.450）
SPLIT_Z_TRAY = 6.16          # 底壳上沿 Z
SPLIT_Z_COVER = 6.20         # 上盖下沿 Z（留 0.04 mm 装配分模间隙，布尔零干涉）
MCU_Z_BASE = 6.20            # MCU-U9 板底 Z（板顶 7.8176；背面器件最低 Z=5.000；正面最高器件 Z=9.468）
COVER_INNER_Z = 9.65         # 上盖内顶面 Z（距最高器件 9.468 留 0.182 mm 净空）
COVER_OUTER_Z = 10.55        # 上盖外顶面 Z（顶壁实厚 0.90 mm >= 0.80 mm；壳体净高 10.40 mm）

BODY_W = 46.80               # 外宽 X: [-23.40 .. +23.40]
BODY_L = 40.00               # 外长 Y: [-20.00 .. +20.00]
OUTER_CORNER_R = 3.80        # 俯视四角圆角 R3.80
INNER_W = 44.40              # 内腔宽 X: [-22.20 .. +22.20]（直壁厚 1.20 mm，距 43.10 板边留 0.65 mm）
INNER_L = 37.60              # 内腔长 Y: [-18.80 .. +18.80]（直壁厚 1.20 mm，距 36.50 板边留 0.55 mm）
INNER_CORNER_R = 2.20        # 内腔四角圆角 R2.20（包络 R1.80 圆角板框）
TOP_OUTER_FILLET_R = 2.40    # 上盖顶面四周外圆角 R2.40
TOP_INNER_FILLET_R = 1.10    # 上盖内腔顶面四周内圆角 R1.10
BOT_OUTER_FILLET_R = 0.70    # 底壳底边四周外圆角 R0.70

# 双板局部坐标 -> 整表坐标系刚体变换基准（绕 Z 旋转 180° + 平移，det(R) = +1）
AFE_CENTER_XY = (21.5500, 4.7498)
MCU_CENTER_XY = (21.3030, -18.3490)

# 双板真实 4 颗 Ø2.00 mm 安装孔中心（取 AFE-30P 与 MCU-U9 实测同心均值，最大双板偏差 <= 0.037 mm）
MOUNT_HOLES: dict[str, tuple[float, float]] = {
    "NE": (+19.6557, +16.3297),
    "SE": (+19.6485, -16.4516),
    "NW": (-20.0990, +16.3297),
    "SW": (-20.1025, -16.3918),
}

# 南北 22 mm 快拆表带生耳几何参数
LUG_SLOT_HALF_X = 11.15      # 22.30 mm 表带槽宽（适配实测 22.04 mm 快拆表带）
LUG_SHROUD_HALF_X = 13.35    # 两侧短耳外半宽（单侧耳宽 2.20 mm）
LUG_GROOVE_R = 1.95          # 织带回折圆筒弧槽半径
PIN_HOLE_D = 1.20            # 弹簧棒盲孔直径
PIN_HOLE_DEPTH = 1.20        # 弹簧棒盲孔深（外侧留实壁 1.00 mm）
SOUTH_PIN_Y = -21.20         # 南弹簧棒轴心 Y（小耳外端 -22.65）
NORTH_PIN_Y = +21.80         # 北弹簧棒轴心 Y（弧槽内缘 +19.85，距北回折袋 +19.00 留 0.85 mm 实壁）
LUG_EAR_RADIAL_WALL = 1.45
SOUTH_LUG_OUTER_Y = SOUTH_PIN_Y - LUG_EAR_RADIAL_WALL
NORTH_LUG_OUTER_Y = NORTH_PIN_Y + LUG_EAR_RADIAL_WALL
LUG_EAR_Z_MIN = 2.00         # 小耳底面抬高至 Z=2.00 防顶手腕
LUG_EAR_Z_MAX = 5.40
PIN_Z = 3.70

# 外扣六孔贴肤底盖 cap_bottom 与胶囊电极参数（1:1 匹配 strap-fpc-30p/geometry.json）
FPC_T = 0.203
FPC_BOT_Z = TRAY_Z_MIN - 2 * FPC_T   # -0.256 mm（A 片贴肤面与底盖内顶面齐平）
CAP_FACE_T = 0.80
CAP_Z_MIN = FPC_BOT_Z - CAP_FACE_T   # -1.056 mm（6 颗 2.0 mm 厚电极铜片尖端在 -2.256 mm，凸出 1.200 mm）
CAP_SKIRT_CLEAR = 0.04               # 裙边与底壳外壁滑配间隙
CAP_SKIRT_T = 0.80
CAP_SKIRT_HY = 14.80                 # 仅包两侧长边直段
CAP_SKIRT_TOP_Z = 1.45
TRAY_GROOVE = (0.88, 1.32, 0.32)     # 底壳外壁卡槽 (z0, z1, depth)，避开底边 R0.70 圆角
CAP_BEAD_Z = (0.94, 1.26)            # 裙边卡棱 Z 范围（上下各留 0.06 mm 间隙）
CAP_BEAD_TIP_X = BODY_W / 2.0 - 0.24 # 伸入卡槽至 |X|=23.16（咬合量 0.24 mm，距槽底 23.08 留 0.08 mm）

BIG_PADS = {"E1N": (-8.0, 7.5), "E1P": (8.0, 7.5), "E2N": (-8.0, -7.5), "E2P": (8.0, -7.5)}
AUX_PADS = {"EB1": (0.0, -7.5), "EB2": (0.0, 7.5)}
HOLE_CLEAR = 0.50


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> b.Part:
    return b.Pos((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0) * b.Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def cyl(x: float, y: float, d: float, z0: float, z1: float) -> b.Part:
    return b.Pos(x, y, (z0 + z1) / 2.0) * b.Cylinder(d / 2.0, z1 - z0)


def cyl_x(x0: float, x1: float, y: float, z: float, d: float) -> b.Part:
    return b.Pos((x0 + x1) / 2.0, y, z) * b.Cylinder(
        d / 2.0, x1 - x0, rotation=(0, 90, 0)
    )


def rounded_prism(w: float, l: float, z0: float, z1: float, r: float) -> b.Part:
    return b.Pos(0, 0, z0) * b.extrude(b.RectangleRounded(w, l, r), amount=z1 - z0)


def domed_prism(w: float, l: float, z0: float, z1: float, r_xy: float, r_top: float) -> b.Part:
    s = rounded_prism(w, l, z0, z1, r_xy)
    r_eff = min(float(r_top), max(0.20, float(z1 - z0) - 0.15))
    top_edges = [
        e
        for e in s.edges()
        if abs(e.bounding_box().min.Z - z1) < 1e-4 and abs(e.bounding_box().max.Z - z1) < 1e-4
    ]
    return b.fillet(top_edges, r_eff)


def bottom_filleted_prism(w: float, l: float, z0: float, z1: float, r_xy: float, r_bot: float) -> b.Part:
    s = rounded_prism(w, l, z0, z1, r_xy)
    bot_edges = [
        e
        for e in s.edges()
        if abs(e.bounding_box().min.Z - z0) < 1e-4 and abs(e.bounding_box().max.Z - z0) < 1e-4
    ]
    return b.fillet(bot_edges, r_bot)


def fpc_geom() -> dict:
    return json.loads(STRAP_GEOM_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 2. 四个单实体可打印结构件生成函数
# ---------------------------------------------------------------------------
def build_tray() -> b.Part:
    """构建圆润底壳 tray（1 solid）。"""
    g = fpc_geom()
    main_outer = bottom_filleted_prism(
        BODY_W, BODY_L, TRAY_Z_MIN, SPLIT_Z_TRAY, OUTER_CORNER_R, BOT_OUTER_FILLET_R
    )
    south_shroud = b.Pos(0, (SOUTH_LUG_OUTER_Y - 17.65) / 2.0, LUG_EAR_Z_MIN) * b.extrude(
        b.RectangleRounded(2 * LUG_SHROUD_HALF_X, -17.65 - SOUTH_LUG_OUTER_Y, 0.75),
        amount=LUG_EAR_Z_MAX - LUG_EAR_Z_MIN,
    )
    north_shroud = b.Pos(0, (NORTH_LUG_OUTER_Y + 17.60) / 2.0, LUG_EAR_Z_MIN) * b.extrude(
        b.RectangleRounded(2 * LUG_SHROUD_HALF_X, NORTH_LUG_OUTER_Y - 17.60, 0.75),
        amount=LUG_EAR_Z_MAX - LUG_EAR_Z_MIN,
    )
    outer = (main_outer + south_shroud + north_shroud).clean()

    inner_cav = rounded_prism(INNER_W, INNER_L, FLOOR_Z_TOP, SPLIT_Z_TRAY + 0.10, INNER_CORNER_R)
    s = outer - inner_cav

    # 南壁内侧局部补厚至 y=-18.40（Z=1.40..SPLIT_Z_TRAY，距 PCB 南边 -18.25 留 0.15 mm 净空，保南生耳弧槽 -19.25 实壁 0.85 mm）
    s += box(-12.00, 12.00, -18.85, -18.40, 1.40, SPLIT_Z_TRAY)

    # 南北生耳半圆柱弧槽、敞口槽与两侧 Ø1.20 盲孔
    south_lug_slot = (
        cyl_x(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, SOUTH_PIN_Y, PIN_Z, 2 * LUG_GROOVE_R)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, -25.00, SOUTH_PIN_Y + LUG_GROOVE_R, -0.10, PIN_Z)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, -25.00, -20.00, PIN_Z, SPLIT_Z_TRAY + 0.20)
    )
    north_lug_slot = (
        cyl_x(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, NORTH_PIN_Y, PIN_Z, 2 * LUG_GROOVE_R)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, NORTH_PIN_Y - LUG_GROOVE_R, 25.00, -0.10, PIN_Z)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, 20.00, 25.00, PIN_Z, SPLIT_Z_TRAY + 0.20)
    )
    south_pin_holes = cyl_x(
        -LUG_SLOT_HALF_X - PIN_HOLE_DEPTH,
        LUG_SLOT_HALF_X + PIN_HOLE_DEPTH,
        SOUTH_PIN_Y,
        PIN_Z,
        PIN_HOLE_D,
    )
    north_pin_holes = cyl_x(
        -LUG_SLOT_HALF_X - PIN_HOLE_DEPTH,
        LUG_SLOT_HALF_X + PIN_HOLE_DEPTH,
        NORTH_PIN_Y,
        PIN_Z,
        PIN_HOLE_D,
    )

    # 北侧双 30P 表带软板穿底长槽与壳内回折袋（严格对齐 strap-fpc-30p/geometry.json）
    ts = g["tray_tail_slot"]
    bx = ts["box"]
    tail_through_slot = box(bx["x0"], bx["x1"], bx["y0"], bx["y1"], TRAY_Z_MIN - 0.10, FLOOR_Z_TOP + 0.05)
    north_fold_pocket = box(-10.60, 8.40, 15.00, ts["north_pocket_y_max_needed"] + 0.004, FLOOR_Z_TOP, 4.55)

    # 东侧 Type-C 插头护套下沿浅沉台（外侧 x=22.55..23.55, y=-6.40..+6.30, z=5.55..SPLIT_Z_TRAY+0.10，内留 0.35mm+1.20mm 实壁）
    usb_overmold_lower = box(22.55, 23.60, -6.40, 6.30, 5.55, SPLIT_Z_TRAY + 0.10)

    # 两侧长边外壁卡槽（配外扣六孔底盖 cap_bottom）
    g0, g1, gd = TRAY_GROOVE
    hx = BODY_W / 2.0
    side_grooves = box(-hx - 0.10, -hx + gd, -15.30, 15.30, g0, g1) + box(
        hx - gd, hx + 0.10, -15.30, 15.30, g0, g1
    )

    s = (
        s
        - south_lug_slot
        - north_lug_slot
        - south_pin_holes
        - north_pin_holes
        - tail_through_slot
        - north_fold_pocket
        - usb_overmold_lower
        - side_grooves
    )

    # 外底面 6 处背贴串阻浅避让坑（直接读取 strap-fpc-30p/geometry.json capsule_res_pockets）
    for r in g["capsule_res_pockets"]["rects"]:
        rb = r["box"]
        s -= box(rb["x0"], rb["x1"], rb["y0"], rb["y1"], TRAY_Z_MIN - 0.10, float(r["pocket_z"][1]))

    # 四角真实孔位支撑台（Ø3.40 mm, Z=0.95..2.43）+ 穿过 AFE-30P Ø2.00 孔的短定位套（Ø1.72 mm, Z=2.43..3.18）
    # 外底四角（|X| >= 19.65 mm，完全在胶囊软板 |X|<=11.12 mm 外侧）设 Ø2.80 沉头孔（Z=0.15..1.05）+ Ø1.55 穿钉通孔
    for hx_p, hy_p in MOUNT_HOLES.values():
        s += cyl(hx_p, hy_p, 3.40, 0.95, AFE_Z_BASE - 0.02)
        s += cyl(hx_p, hy_p, 1.72, AFE_Z_BASE - 0.02, AFE_Z_BASE + 0.73)
        # 裁齐在内腔轮廓之内避免刺破外圆角
    s = (s & (rounded_prism(BODY_W + 6.0, BODY_L + 10.0, -2.0, SPLIT_Z_TRAY + 0.5, 1.0)))
    for hx_p, hy_p in MOUNT_HOLES.values():
        s -= cyl(hx_p, hy_p, 2.80, TRAY_Z_MIN - 0.10, 1.05)
        s -= cyl(hx_p, hy_p, 1.55, 1.00, AFE_Z_BASE + 0.85)

    return s.clean()


def build_cover() -> b.Part:
    """构建圆润上盖 cover（1 solid，顶面与四周零外露螺丝孔）。"""
    outer = domed_prism(
        BODY_W, BODY_L, SPLIT_Z_COVER, COVER_OUTER_Z, OUTER_CORNER_R, TOP_OUTER_FILLET_R
    )
    inner = domed_prism(
        INNER_W, INNER_L, SPLIT_Z_COVER - 0.20, COVER_INNER_Z, INNER_CORNER_R, TOP_INNER_FILLET_R
    )
    s = outer - inner

    # 四角下压定位柱（Ø3.20 mm, Z=7.84..9.75 熔入上盖顶壁）+ 向下短定位销（Ø1.68 mm, Z=7.00..7.84 插入 MCU-U9 Ø2.00 孔）
    # 内部预留 Ø1.25 mm 自攻盲孔（Z=6.90..9.55，上盖顶壁保留 1.00 mm 完整无孔外观）
    inner_clip = domed_prism(
        INNER_W + 0.40, INNER_L + 0.40, SPLIT_Z_COVER, COVER_OUTER_Z - 0.30, INNER_CORNER_R, TOP_INNER_FILLET_R
    )
    bosses = None
    for hx_p, hy_p in MOUNT_HOLES.values():
        post = cyl(hx_p, hy_p, 3.20, 7.84, COVER_INNER_Z + 0.35) + cyl(hx_p, hy_p, 1.68, 7.00, 7.84)
        bosses = post if bosses is None else (bosses + post)
    if bosses is not None:
        s = (s + (bosses & inner_clip)).clean()
    for hx_p, hy_p in MOUNT_HOLES.values():
        s -= cyl(hx_p, hy_p, 1.25, 6.95, 9.55)

    # 东侧（+X）USB Type-C 窗口（MCU-U9 USB1 包络 X=[15.07..22.27], Y=[-5.786..+5.664], Z=[6.218..9.379]）
    # 内贯通口：X=[20.60..23.60], Y=[-5.98..+5.86], Z=[6.10..9.58]；外侧插头塑胶护套沉台：X=[22.55..23.60], Y=[-6.40..+6.30], Z=[6.10..9.95]
    usb_aperture = box(20.60, 23.60, -5.98, 5.86, SPLIT_Z_COVER - 0.15, 9.58) + box(
        22.55, 23.60, -6.40, 6.30, SPLIT_Z_COVER - 0.15, 9.95
    )

    # 东侧（+X）侧按开关按键孔与内侧防脱翼活动腔（对齐 MCU-U9 U1 开关：壳体 X=[18.042..20.392], 按头 X=[20.392..21.542], Y=[-12.01..-10.21], Z=[8.168..9.068]）
    # 外穿孔：X=[22.40..23.80], Y=[-12.91..-9.31] (宽 3.60), Z=[7.52..9.62] (高 2.10)
    # 内侧防脱活动腔：X=[20.50..22.55]（东侧留实壁 23.40-22.55 = 0.85 mm >= 0.80 mm）, Y=[-13.70..-8.52], Z=[7.12..9.65]
    btn_aperture = box(22.40, 23.80, -12.91, -9.31, 7.52, 9.62) + box(
        20.50, 22.55, -13.70, -8.52, 7.12, 9.65
    )

    s = (s - usb_aperture - btn_aperture).clean()
    return s


def build_side_button() -> b.Part:
    """构建东侧防脱侧按按键帽 side_button（1 solid）。
    - 外露圆角键帽：X=[21.74..23.85]（凸出东壁 0.45 mm），Y=[-12.71..-9.51]（宽 3.20 mm，距盖孔单边留 0.20 mm 间隙），
      Z=[7.72..9.42]（高 1.70 mm，距盖孔上下留 0.20 mm 间隙）
    - 内侧防脱卡翼：X=[21.74..22.34]（厚 0.60 mm），Y=[-13.45..-8.77]（南北各外扩 0.74 mm 锁在盖孔内），Z=[7.32..9.42]
    - 行程核验：静止内端面 X=21.74（距 U1 按头 X=21.542 留 0.198 mm 间隙，防脱翼东面 X=22.34 距活动腔东壁 22.55 留 0.21 mm）；
      向 -X 按入 0.70 mm 时内端面达 X=21.04，将 U1 按头推进 0.502 mm（满行程），且距开关壳体 X=20.392 仍留 0.648 mm 余量。
    """
    cap = box(21.74, 23.85, -12.71, -9.51, 7.72, 9.42)
    outer_edges = [
        e for e in cap.edges() if abs(e.bounding_box().min.X - 23.85) < 1e-4 and abs(e.bounding_box().max.X - 23.85) < 1e-4
    ]
    cap = b.fillet(outer_edges, 0.35)
    flange = box(21.74, 22.34, -13.45, -8.77, 7.32, 9.42)
    return (cap + flange).clean()


def build_cap_bottom() -> b.Part:
    """构建外扣六孔贴肤底盖 cap_bottom（1 solid，TPU 95A 或韧性树脂）。
    - 底板：46.80 × 40.00 R3.80，Z=[-1.056 .. -0.256]（厚 0.80 mm）
    - 两侧长边弹性裙边：|X|=[23.44 .. 24.24]（与底壳外壁 23.40 留 0.04 mm 滑配间隙），Y=[-14.80 .. +14.80]，Z=[-1.056 .. +1.45]
    - 内凸卡棱：Z=[0.94 .. 1.26]，伸至 |X|=23.16（扣入底壳 Z=[0.88..1.32] 卡槽 0.24 mm，与槽底 23.08 留 0.08 mm 间隙）
    - 电极开孔：4 × Φ6.50 mm 圆孔（CH1/CH2）+ 2 × 3.50 × 3.50 mm 方孔（BIAS/REF 辅点）
    """
    hx = BODY_W / 2.0
    hy = BODY_L / 2.0
    s = rounded_prism(BODY_W + 2 * CAP_SKIRT_CLEAR, BODY_L, CAP_Z_MIN, FPC_BOT_Z, OUTER_CORNER_R)
    for sx in (-1.0, 1.0):
        x_in = sx * (hx + CAP_SKIRT_CLEAR)
        x_out = sx * (hx + CAP_SKIRT_CLEAR + CAP_SKIRT_T)
        x0, x1 = sorted((x_in, x_out))
        s += box(x0, x1, -CAP_SKIRT_HY, CAP_SKIRT_HY, CAP_Z_MIN, CAP_SKIRT_TOP_Z)
        bx0, bx1 = sorted((sx * CAP_BEAD_TIP_X, sx * (hx + CAP_SKIRT_CLEAR + 0.05)))
        s += box(bx0, bx1, -CAP_SKIRT_HY, CAP_SKIRT_HY, CAP_BEAD_Z[0], CAP_BEAD_Z[1])

    h_cut = FPC_BOT_Z - CAP_Z_MIN + 0.30
    zc = (CAP_Z_MIN + FPC_BOT_Z) / 2.0
    for x, y in BIG_PADS.values():
        s -= b.Pos(x, y, zc) * b.Cylinder((6.0 + HOLE_CLEAR) / 2.0, h_cut)
    for x, y in AUX_PADS.values():
        side = 3.0 + HOLE_CLEAR
        s -= b.Pos(x, y, zc) * b.Box(side, side, h_cut)
    return s.clean()


# ---------------------------------------------------------------------------
# 3. 刚体变换（det(R)=+1，逐个 Solid 独立变换）与内部装配件构建
# ---------------------------------------------------------------------------
def transform_board_solid(sol: b.Solid, cx: float, cy: float, z_base: float) -> b.Solid:
    """绕 Z 轴旋转 180° 并平移至整表坐标系：x_box = cx - x, y_box = cy - y, z_box = z_base + z（det(R)=+1）。"""
    return sol.rotate(b.Axis.Z, 180.0).translate((cx, cy, z_base))


def transform_strap_solid_to_box(sol: b.Solid, z_f_step: float = 0.161, dz_extra: float = 0.0) -> b.Solid:
    """将 strap-30p-a/b 的 Solid 经绕 (1,-1,0) 轴 180° 纯旋转（det(R)=+1）变换至整表盒底坐标系。"""
    rot_axis = b.Axis((0, 0, 0), (1, -1, 0))
    return sol.rotate(rot_axis, 180.0).translate((-50.0, 58.0, (FPC_BOT_Z + z_f_step) + dz_extra))


def build_battery_302025() -> b.Solid:
    """构建穿在 MCU-U9 27.40 × 20.90 mm 电池镂空窗内的 302025 锂电池参考实体（1 solid）。
    电芯体 25.20 × 19.60 × 2.80 mm + 东侧极耳保护板包络（总展长 26.40 mm，西北角避开孔位加强阶梯），
    Z = [4.80 .. 7.60] mm（高于 AFE-30P 顶面 U1 Z=4.5505 留 0.25 mm 缓冲间隙，低于 MCU-U9 顶面 Z=7.818）。
    """
    cell = box(-19.15, 6.05, -4.40, 14.40, 4.80, 7.60)
    pcm = box(-17.65, 7.25, -4.40, 15.20, 4.80, 7.60)
    return (cell + pcm).clean().solids()[0]


def build_pcb_standoffs() -> list[tuple[str, b.Solid]]:
    """构建双板之间的 4 颗 Ø3.00 mm 绝缘尼龙支撑柱（Z = 3.27 .. 6.18 mm，内孔 Ø1.55 mm）。"""
    out = []
    for name, (hx_p, hy_p) in MOUNT_HOLES.items():
        st = (cyl(hx_p, hy_p, 3.00, AFE_Z_BASE + 0.82, MCU_Z_BASE - 0.02) - cyl(hx_p, hy_p, 1.55, AFE_Z_BASE + 0.75, MCU_Z_BASE + 0.05)).clean()
        out.append((f"standoff_{name}", st.solids()[0]))
    return out


def build_west_ffc20_loop() -> b.Solid:
    """构建西侧（-X）连接 AFE-30P FPC2 与 MCU-U9 FPC1 的 20P 0.5mm 反序软排线 U 形回折参考体。"""
    # 插口在 X = -15.90, Y = [-16.65 .. -6.15]（宽 10.50 mm），向西（-X）伸至 X = -20.80 U 形回折（Z = 3.75 .. 5.75）
    outer = cyl_y_arch(-20.80, -15.95, -16.65, -6.15, 3.70, 5.80, t=0.18)
    return outer


def cyl_y_arch(x_west: float, x_east: float, y0: float, y1: float, z0: float, z1: float, t: float = 0.18) -> b.Solid:
    zc = (z0 + z1) / 2.0
    r_out = (z1 - z0) / 2.0
    x_arc_c = x_west + r_out
    straight_top = box(x_arc_c, x_east, y0, y1, z1 - t, z1)
    straight_bot = box(x_arc_c, x_east, y0, y1, z0, z0 + t)
    semi_out = b.Pos(x_arc_c, (y0 + y1) / 2.0, zc) * b.Cylinder(r_out, y1 - y0, rotation=(90, 0, 0))
    semi_in = b.Pos(x_arc_c, (y0 + y1) / 2.0, zc) * b.Cylinder(r_out - t, y1 - y0 + 0.2, rotation=(90, 0, 0))
    bend = (semi_out - semi_in) & box(x_west - 0.5, x_arc_c + 0.02, y0 - 0.2, y1 + 0.2, z0 - 0.2, z1 + 0.2)
    return (straight_top + straight_bot + bend).clean().solids()[0]


def build_spring_bar(y_pos: float) -> b.Solid:
    hw = 22.04 / 2.0
    barrel = cyl_x(-hw, hw, y_pos, PIN_Z, 1.80)
    tips = cyl_x(-(hw + 0.90), hw + 0.90, y_pos, PIN_Z, 0.80)
    return (barrel + tips).clean().solids()[0]


def load_capsule_strap_solids() -> tuple[list[b.Solid], list[b.Solid]]:
    """加载 strap-30p-a-3d.step 与 strap-30p-b-3d.step 的胶囊区实体并逐个刚体变换至盒底坐标系。"""
    out_a, out_b = [], []
    cap_clip = b.Pos((40.2 + 74.8) / 2.0, -50.0, 0.05) * b.Box(74.8 - 40.2, 30.0, 0.50)
    for step_p, dz, bucket in ((STRAP_A_STEP_PATH, 0.0, out_a), (STRAP_B_STEP_PATH, +FPC_T, out_b)):
        comp = b.import_step(str(step_p))
        for s in comp.solids():
            bb = s.bounding_box()
            if bb.size.X > 80.0:
                for cs in (s & cap_clip).solids():
                    bucket.append(transform_strap_solid_to_box(cs, 0.161, dz))
            elif 41.0 <= (bb.min.X + bb.max.X) / 2.0 <= 75.0:
                bucket.append(transform_strap_solid_to_box(s, 0.161, dz))
    return out_a, out_b


def export_all() -> dict:
    parts = {
        "tray": build_tray(),
        "cover": build_cover(),
        "side_button": build_side_button(),
        "cap_bottom": build_cap_bottom(),
    }

    manifest: dict[str, dict] = {
        "frame": "OpenEMG watch frame (X East+, Y North+, Z Top+; mm)",
        "board_stack_z": {
            "cap_bottom_z": [round(CAP_Z_MIN, 3), round(FPC_BOT_Z, 3)],
            "electrode_tips_z": round(FPC_BOT_Z - 2.0, 3),
            "tray_z": [round(TRAY_Z_MIN, 3), round(SPLIT_Z_TRAY, 3)],
            "afe_30p_substrate_z": [round(AFE_Z_BASE, 3), round(AFE_Z_BASE + 0.8004, 4)],
            "battery_302025_z": [4.80, 7.60],
            "mcu_u9_substrate_z": [round(MCU_Z_BASE, 3), round(MCU_Z_BASE + 1.6176, 4)],
            "cover_z": [round(SPLIT_Z_COVER, 3), round(COVER_OUTER_Z, 3)],
            "shell_body_height_mm": round(COVER_OUTER_Z - TRAY_Z_MIN, 3),
            "overall_height_with_electrodes_mm": round(COVER_OUTER_Z - (FPC_BOT_Z - 2.0), 3),
        },
        "parts": {},
    }

    for name, part in parts.items():
        solids = list(part.solids())
        assert len(solids) == 1, f"{name} 必须为单实体，当前 solids={len(solids)}"
        s1 = solids[0]
        assert s1.is_valid, f"{name} 几何拓扑无效"
        step_p = HERE / f"{name}.step"
        stl_p = HERE / f"{name}.stl"
        b.export_step(s1, str(step_p))
        b.export_stl(s1, str(stl_p), tolerance=0.01, angular_tolerance=0.1)
        bb = s1.bounding_box()
        manifest["parts"][name] = {
            "step": step_p.name,
            "stl": stl_p.name,
            "solid_count": 1,
            "is_valid": True,
            "volume_mm3": round(float(abs(s1.volume)), 3),
            "bbox_min": [round(float(v), 3) for v in (bb.min.X, bb.min.Y, bb.min.Z)],
            "bbox_max": [round(float(v), 3) for v in (bb.max.X, bb.max.Y, bb.max.Z)],
            "size_mm": [round(float(v), 3) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
        }
        print(
            f"[OK] {name:14s} solids=1 vol={abs(s1.volume):8.2f} mm³ size={[round(float(v), 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)]}",
            flush=True,
        )

    def simplify_board_for_preview(raw_solids: list[b.Solid], cx: float, cy: float, z_base: float) -> list[b.Solid]:
        """总装预览轻量化（全量精细布尔干涉由 fit_3d_check.py 直接读取 mcu-u9-3d.step / afe-30p-3d.step 原件执行）：
        基板（>35mm）与干净几何器件（<=50 面）原样保留，立创云端高面数阻容圆角模型按精确 1:1 三维包围盒呈现，跳过 <0.05mm 丝印贴片。
        """
        out_sols: list[b.Solid] = []
        for s in raw_solids:
            ts = transform_board_solid(s, cx, cy, z_base)
            bb = ts.bounding_box()
            if bb.size.Z < 0.05 and bb.size.X < 0.8 and bb.size.Y < 0.8:
                continue
            if bb.size.X > 35.0 or len(ts.faces()) <= 50:
                out_sols.append(ts)
            else:
                out_sols.append(box(bb.min.X, bb.max.X, bb.min.Y, bb.max.Y, bb.min.Z, bb.max.Z).solids()[0])
        return out_sols

    # 加载双板与双 30P 胶囊叠层构建预览总装（全量 338+588 原件布尔求交在 fit_3d_check.py 中独立校验）
    afe_raw = list(b.import_step(str(AFE_STEP_PATH)).solids())
    mcu_raw = list(b.import_step(str(MCU_STEP_PATH)).solids())
    afe_box_solids = simplify_board_for_preview(afe_raw, *AFE_CENTER_XY, AFE_Z_BASE)
    mcu_box_solids = simplify_board_for_preview(mcu_raw, *MCU_CENTER_XY, MCU_Z_BASE)
    strap_a_solids, strap_b_solids = load_capsule_strap_solids()

    afe_comp = b.Compound(children=afe_box_solids)
    mcu_comp = b.Compound(children=mcu_box_solids)
    strap_a_comp = b.Compound(children=strap_a_solids)
    strap_b_comp = b.Compound(children=strap_b_solids)
    bat_solid = build_battery_302025()
    ffc20_solid = build_west_ffc20_loop()
    south_bar = build_spring_bar(SOUTH_PIN_Y)
    north_bar = build_spring_bar(NORTH_PIN_Y)

    assy_items: list[tuple[str, b.Shape, tuple[float, float, float, float]]] = [
        ("tray", parts["tray"].solids()[0], (0.78, 0.86, 0.92, 0.55)),
        ("cover", parts["cover"].solids()[0], (0.82, 0.90, 0.96, 0.45)),
        ("side_button", parts["side_button"].solids()[0], (0.20, 0.65, 0.95, 0.92)),
        ("cap_bottom", parts["cap_bottom"].solids()[0], (0.22, 0.24, 0.27, 0.88)),
        ("AFE_30P_full_338", afe_comp, (0.12, 0.46, 0.26, 1.0)),
        ("MCU_U9_full_588", mcu_comp, (0.14, 0.34, 0.56, 1.0)),
        ("battery_302025", bat_solid, (0.38, 0.58, 0.78, 1.0)),
        ("west_ffc20_reverse_loop", ffc20_solid, (0.88, 0.52, 0.14, 1.0)),
        ("strap_30p_a_capsule", strap_a_comp, (0.85, 0.68, 0.20, 1.0)),
        ("strap_30p_b_capsule", strap_b_comp, (0.80, 0.42, 0.12, 1.0)),
        ("south_spring_bar", south_bar, (0.75, 0.77, 0.80, 1.0)),
        ("north_spring_bar", north_bar, (0.75, 0.77, 0.80, 1.0)),
    ]
    for st_name, st_sol in build_pcb_standoffs():
        assy_items.append((st_name, st_sol, (0.92, 0.92, 0.88, 1.0)))

    def save_scene(stem: str, items: list[tuple[str, b.Shape, tuple[float, float, float, float]]]) -> None:
        children = []
        for label, shp, rgba in items:
            c = copy.copy(shp)
            c.label = label
            c.color = b.Color(*rgba)
            children.append(c)
        scene = b.Compound(children=children)
        b.export_step(scene, str(HERE / f"{stem}.step"))
        b.export_gltf(scene, str(HERE / f"{stem}.glb"), binary=True, linear_deflection=0.02, angular_deflection=0.2)
        print(f"[OK] Exported {stem}.step & {stem}.glb (groups={len(children)})", flush=True)

    save_scene("assembly", assy_items)

    exploded_offsets = {
        "cover": (0.0, 0.0, 18.0),
        "side_button": (8.0, 0.0, 18.0),
        "MCU_U9_full_588": (0.0, 0.0, 10.0),
        "battery_302025": (0.0, 0.0, 5.5),
        "west_ffc20_reverse_loop": (-7.0, 0.0, 4.5),
        "standoff_NE": (0.0, 0.0, 4.0),
        "standoff_SE": (0.0, 0.0, 4.0),
        "standoff_NW": (0.0, 0.0, 4.0),
        "standoff_SW": (0.0, 0.0, 4.0),
        "AFE_30P_full_338": (0.0, 0.0, 0.0),
        "tray": (0.0, 0.0, -7.0),
        "strap_30p_b_capsule": (0.0, 0.0, -13.0),
        "strap_30p_a_capsule": (0.0, 0.0, -16.5),
        "cap_bottom": (0.0, 0.0, -21.0),
        "south_spring_bar": (0.0, -9.0, -7.0),
        "north_spring_bar": (0.0, 9.0, -7.0),
    }

    def shift_shape(shp: b.Shape, delta: tuple[float, float, float]) -> b.Shape:
        if delta == (0.0, 0.0, 0.0):
            return shp
        if isinstance(shp, b.Compound):
            return b.Compound(children=[s.translate(delta) for s in shp.solids()])
        return shp.translate(delta)

    exploded_items = [
        (lbl, shift_shape(shp, exploded_offsets.get(lbl, (0.0, 0.0, 0.0))), rgba)
        for lbl, shp, rgba in assy_items
    ]
    save_scene("exploded", exploded_items)

    manifest["embedded_board_solids"] = {
        "afe_30p": len(afe_box_solids),
        "mcu_u9": len(mcu_box_solids),
        "strap_30p_a_capsule": len(strap_a_solids),
        "strap_30p_b_capsule": len(strap_b_solids),
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    export_all()
