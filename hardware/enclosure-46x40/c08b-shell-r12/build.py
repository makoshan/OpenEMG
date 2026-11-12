"""C08B 透明光固化（嘉立创 8001 树脂）外壳 R12 生成器（对齐 IMG_3797.MOV 快拆生耳直连方案）。
输出 3 个单实体 STEP 与 STL（不含 AssemblyHelper 包装，可直接上传嘉立创 3D 打印报价）：
- tray.step / tray.stl：底壳（含南北内凹 C 形半圆柱生耳弧槽 + 两侧 Ø1.20 盲孔、底边圆角、采集板支撑柱、主控角托、R14 软板下层通道与北袋、北无铜走廊 2.4G FPC 天线卡肩）
- cover.step / cover.stl：上盖（总厚抬至 10.1 mm、盖内顶面 Z=9.1 mm、四角 R5.8 与顶边 R3.0 大圆角、顶部开关阶梯孔、J300 1代 U.FL 插头透明微凸窗 Z=10.84）
- switch_plunger.step / switch_plunger.stl：顶部 45° 楔面开关按压柱塞（防脱台阶 + 推动 SW300 侧按杆）
（已按 IMG_3797.MOV 去掉 south_lug_end / north_lug_end 两个多余树脂端块：26 mm 编织表带回折圆筒内直接穿 Ø1.8×26 mm 快拆弹簧棒，一步卡入底壳半圆弧槽两侧盲孔。）
另导出 assembly.step / assembly.glb 与 exploded.step / exploded.glb 仅供预览与对齐核查。
"""
from pathlib import Path
import json
import math
import copy
import build123d as b

P = Path(__file__).resolve().parent
BOARDS_JSON = P / "boards-real-frame.json"

# ---------------------------------------------------------------------------
# 具名几何常量（单位 mm，R11/R12 整机坐标系：Z=0 为底部电极触点尖端最低点）
# ---------------------------------------------------------------------------
TOTAL_HEIGHT = 10.10          # 整机总厚（含底部触点 Z=0..10.10；R11 为 9.70）
TRAY_Z_MIN = 0.15             # 底壳外底面 Z（触点尖端在 Z=0.00，露出 0.15 mm）
SPLIT_Z = 6.76                # 底壳与上盖分模面 Z（齐平托住主控板底面 Z=6.79，留 0.03 mm 装配余量）
COVER_INNER_Z = 9.10          # 上盖内顶面基准 Z（由 R11 的 8.70 抬高 0.40 mm）
COVER_OUTER_Z = 10.10         # 上盖外顶面 Z（顶壁厚 1.00 mm）

# 主体俯视与圆角参数
BODY_W = 46.00                # 主体宽 X (-23.0 .. +23.0)
BODY_L = 40.00                # 主体长 Y (-20.0 .. +20.0)
OUTER_CORNER_R = 5.80         # 俯视四角大圆角（R11 为 R3.0）
INNER_W = 43.60               # 内腔宽 X (-21.8 .. +21.8)
INNER_L = 37.60               # 内腔长 Y (-18.8 .. +18.8)
INNER_CORNER_R = 4.60         # 内腔四角圆角（匹配 D17 板角 R4.6，壁厚 1.20 mm）
TOP_OUTER_FILLET_R = 3.00     # 上盖顶面四周外圆角 R3.0
TOP_INNER_FILLET_R = 1.80     # 上盖内腔顶面四周内圆角 R1.8（保证圆角处壁厚 ≥1.00 mm 且不碰器件）
BOT_OUTER_FILLET_R = 0.90     # 底壳底面外周圆角 R0.9

# 隐藏生耳槽与快拆弹簧棒参数（对齐 IMG_3797/3799/3800.MOV 实测：表带连接处宽 22.04 mm，织带端头回折圆筒 Ø3.80 直接穿 Ø1.80 快拆弹簧棒；
# 针对 IMG_3799/3800.MOV 反馈“凸出来的耳堵太长撑起表壳导致底部悬空”，将中段 22.30 mm 顶部遮檐完全退平至盒壁 y=±20.00，
# 仅保留两侧 2.20 mm 宽低剖面小耳（Z=2.00..5.40，底面悬空高出盒底 1.85 mm 不顶手腕），南/北耳凸出由 4.80/6.80 mm 大幅缩减至 2.65/3.10 mm）
STRAP_MEASURED_W = 22.04      # Mako 实测表带连接处宽度 22.04 mm（22 mm 标称快拆表带）
SPRING_BAR_NOM_LEN = 22.04    # 快拆弹簧棒与织带圆筒实测宽度（x: -11.02..+11.02 mm）
SPRING_BAR_BARREL_D = 1.80    # 弹簧棒主杆直径
SPRING_BAR_TIP_D = 0.80       # 弹簧棒两端伸缩销头直径
SPRING_BAR_TIP_LEN = 0.90     # 单侧销头伸出长度（总展长 23.84 mm，单边弹入盲孔 0.77 mm）
STRAP_LOOP_OUTER_D = 3.80     # 编织表带回折圆筒外径（Ø1.80 弹簧棒 + 1.00 mm 织带双层包覆，半径 R=1.90 mm）
LUG_GROOVE_R = 1.95           # 底壳内凹半圆柱弧槽半径（D=3.90 mm，与 Ø3.80 织带圆筒留 0.10 mm 间隙，中段顶部敞开无凸出遮檐）
LUG_SLOT_HALF_X = 11.15       # 生耳槽半宽（总宽 22.30 mm，配实测 22.04 mm 表带连接端，单侧留 0.13 mm 间隙兼容 3D 打印与喷油）
LUG_SHROUD_HALF_X = 13.35     # 两侧生耳小耳外半宽（由 16.00 收窄至 13.35 mm，总宽 26.70 mm，单侧耳厚 2.20 mm）
PIN_HOLE_D = 1.20             # 护耳内侧盲孔直径（配合 Ø0.80 销头，按 8001 全透明喷清漆预留 0.40 mm 直径余量）
PIN_HOLE_DEPTH = 1.20         # 护耳盲孔深度（|x| = 11.15..12.35，距外侧 x=13.35 留实心壁厚 1.00 mm ≥ 0.80 mm）
SOUTH_PIN_Y = -21.20          # 南端弹簧棒轴线 Y（由 -22.50 内收 1.30 mm，仅出盒壁 1.20 mm；南小耳外端 y=-22.65，仅凸出 2.65 mm）
NORTH_PIN_Y = 21.65           # 北端弹簧棒轴线 Y（由 +24.50 内收 2.85 mm，仅出盒壁 1.65 mm；北小耳外端 y=+23.10，仅凸出 3.10 mm）
LUG_EAR_RADIAL_WALL = 1.45    # 弹簧棒轴心到小耳外端距离（销孔半径 0.60 + 0.85 mm 实壁 = 1.45 mm）
SOUTH_LUG_OUTER_Y = SOUTH_PIN_Y - LUG_EAR_RADIAL_WALL  # -22.65 mm（较旧版 -24.80 缩短 2.15 mm / -44.8%）
NORTH_LUG_OUTER_Y = NORTH_PIN_Y + LUG_EAR_RADIAL_WALL  # +23.10 mm（较旧版 +26.80 缩短 3.70 mm / -54.4%）
LUG_EAR_Z_MIN = 2.00          # 凸出小耳底面 Z（高出底壳底面 Z=0.15 达 1.85 mm、高出触点 Z=0.00 达 2.00 mm，彻底消除撑起手腕悬空）
LUG_EAR_Z_MAX = 5.40          # 凸出小耳顶面 Z（销孔上下各留 1.10 mm ≥ 0.80 mm 实壁，低于上盖顶 4.70 mm 不顶回折魔术贴）
PIN_Z = 3.70                  # 南北弹簧棒轴线 Z（织带圆筒 Z=1.80..5.60，与下层 Z<=1.38 软板留 ≥0.42 mm 垂直净空）

# 内置北侧无铜走廊 2.4 GHz FPC 贴片天线与 J300 1代 U.FL 同轴插头参数
# 主控板与 D17 板北边均截止于 y=18.25 mm，盒内北壁在 y=18.80 mm，y=18.25..18.80 (Z=4.25..8.80) 为完全无铜走廊。
# 标准 2.4 GHz FPC 贴片天线 20.0 × 4.2 × 0.20 mm 竖贴于北内壁 y=18.80（天线占 x: -10.0..+10.0, y: 18.42..18.62, Z: 4.45..8.65），
# 由 Ø0.81 mm 同轴线经北引线槽接至 J300（U.FL-R-SMT-1，中心 6.21, 15.78，插头扣合顶面 Z = 7.41 + 2.40 = 9.81 mm）。
ANTENNA_SPEC = {
    "type": "Internal 2.4 GHz FPC dipole/monopole patch antenna in North copper-free corridor + J300 1st-gen U.FL (IPEX1) mated plug",
    "j300_part": "Hirose U.FL-R-SMT-1(10) on MCU top (x=6.21, y=15.78, z=7.42..8.69)",
    "ufl_mated_plug_z_top_mm": 9.81,
    "cover_ufl_recess_inner_z_mm": 9.98,
    "cover_ufl_blister_outer_z_mm": 10.84,
    "cover_ufl_roof_wall_mm": 0.86,
    "fpc_antenna_size_mm": [20.0, 4.2, 0.20],
    "fpc_antenna_corridor_bbox": {
        "x": [-10.0, 10.0],
        "y": [18.42, 18.62],
        "z": [4.45, 8.65],
    },
    "distance_to_battery_mm": 8.71,
    "outside_pcb_copper": True,
}

# Panasonic EVQP7A01P（SW300）规格参数（来源：Panasonic EVQ-P7 系列规格书）
# 本体 3.5×2.9×1.4 mm，侧按行程 nominal 0.30 mm / max 0.50 mm，动作力 1.6 N / 2.2 N。
# 在 11.7 主控板上封装包围盒 x: -0.21..3.38, y: 12.81..17.55, z: 7.41..8.80，按动面朝 +X。
SW_SPEC = {
    "part_number": "Panasonic EVQP7A01P (EVQ-P7 series)",
    "source": "Panasonic EVQ-P7 Side-operational SMD Light Touch Switch Datasheet + 11.7 PCB 3D bbox",
    "actuator_direction": "+X (pushed toward -X to actuate)",
    "actuator_rest_x": 3.38,
    "nominal_travel_mm": 0.30,
    "full_stroke_mm": 0.50,
    "plunger_vertical_stroke_mm": 0.80,
    "wedge_angle_deg": 45.0,
    "horizontal_push_mm": 0.64,
    "hole_clearance_mm": 0.20,
}


def box(x0, x1, y0, y1, z0, z1):
    return b.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * b.Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def cyl(x, y, d, z0, z1):
    return b.Pos(x, y, (z0 + z1) / 2) * b.Cylinder(d / 2, z1 - z0)


def cyl_x(x0, x1, y, z, d):
    return b.Pos((x0 + x1) / 2, y, z) * b.Cylinder(
        d / 2, x1 - x0, rotation=(0, 90, 0)
    )


def rounded_prism(w, l, z0, z1, r):
    return b.Pos(0, 0, z0) * b.extrude(b.RectangleRounded(w, l, r), amount=z1 - z0)


def domed_prism(w, l, z0, z1, r_xy, r_top):
    """生成带顶面四周大圆角（r_top）与俯视四角大圆角（r_xy）的平滑单实体，无相切布尔缝。"""
    s = rounded_prism(w, l, z0, z1, r_xy)
    r_eff = min(float(r_top), max(0.20, float(z1 - z0) - 0.15))
    top_edges = [
        e for e in s.edges() if abs(e.bounding_box().min.Z - z1) < 1e-4 and abs(e.bounding_box().max.Z - z1) < 1e-4
    ]
    return b.fillet(top_edges, r_eff)


def bottom_filleted_prism(w, l, z0, z1, r_xy, r_bot):
    """生成带底面四周圆角（r_bot）与俯视四角大圆角（r_xy）的平滑单实体。"""
    s = rounded_prism(w, l, z0, z1, r_xy)
    bot_edges = [
        e for e in s.edges() if abs(e.bounding_box().min.Z - z0) < 1e-4 and abs(e.bounding_box().max.Z - z0) < 1e-4
    ]
    return b.fillet(bot_edges, r_bot)


def volume(s):
    return sum(abs(q.volume) for q in s.solids()) if s else 0.0


def build_tray(
    pin_hole_depth=PIN_HOLE_DEPTH,
    outer_r=OUTER_CORNER_R,
):
    """构建底壳 tray（单实体，对齐 IMG_3799.MOV / IMG_3800.MOV 短耳堵防悬空版）：
    - 主体外框 46×40 R5.8，Z=0.15..6.60，底边 R0.9 圆角
    - 两侧紧凑短生耳凸耳（|x|: 11.15..13.35 单边宽 2.20 mm，南 y: -22.65..-20.00 仅伸出 2.65 mm，北 y: 20.00..23.10 仅伸出 3.10 mm，
      Z=2.00..5.40 距腕面抬高 2.00 mm 防顶手腕悬空；中间 22.30 mm 表带槽取消顶棚，Y 向外凸 0.00 mm）
    - 北端 R14/R15 双片 34P 软板 180° 回折槽（x: ±9.60，y: 17.80..18.80，Z=1.00..4.10）
    - 南端 R14/R15 双片软板出盒槽（x: -9.60..+9.60，覆盖 -5.12..+9.00 共 14.12 mm 宽并留余量）
    - 六个底部电极触点沉孔 + 四个 D18/R2 同位安装孔支撑定位台
    """
    main_outer = bottom_filleted_prism(
        BODY_W, BODY_L, TRAY_Z_MIN, SPLIT_Z, outer_r, BOT_OUTER_FILLET_R
    )

    # 南北紧凑短生耳外体（仅在两侧 |x|<=13.35 伸出至 y=-22.65 / +23.10，Z=2.00..5.40，与主体搭接熔合为 1 个干净实体）
    south_shroud = b.Pos(0, (SOUTH_LUG_OUTER_Y - 17.65) / 2.0, LUG_EAR_Z_MIN) * b.extrude(
        b.RectangleRounded(2 * LUG_SHROUD_HALF_X, -17.65 - SOUTH_LUG_OUTER_Y, 0.75),
        amount=LUG_EAR_Z_MAX - LUG_EAR_Z_MIN,
    )
    north_shroud = b.Pos(0, (NORTH_LUG_OUTER_Y + 17.60) / 2.0, LUG_EAR_Z_MIN) * b.extrude(
        b.RectangleRounded(2 * LUG_SHROUD_HALF_X, NORTH_LUG_OUTER_Y - 17.60, 0.75),
        amount=LUG_EAR_Z_MAX - LUG_EAR_Z_MIN,
    )

    outer = (main_outer + south_shroud + north_shroud).clean()

    # 主内腔（Z=1.20..6.65，壁厚 1.20 mm；底板厚 Z=0.15..1.20 = 1.05 mm）
    inner_cav = rounded_prism(INNER_W, INNER_L, 1.20, SPLIT_Z + 0.10, INNER_CORNER_R)

    # 盒底 R14 软板静态通道（x: -13.3..13.3, y: -18.8..18.8, 底面 Z=1.00，底板实厚 1.00-0.15 = 0.85 mm ≥ 0.80 mm）
    fpc_floor_groove = box(-13.30, 13.30, -18.80, 18.80, 1.00, 1.25)

    # 北侧 R14/R15 软板尾回折底槽（x: -9.60..9.60, y: 17.80..18.80, Z=1.00..4.10，与主内腔北壁 y=18.80 齐平，
    # 距北生耳弧槽内壁 y=19.70 留实心北墙 0.90 mm ≥ 0.80 mm）
    north_pocket = box(-9.60, 9.60, 17.80, 18.80, 1.00, 4.10)

    # 北支软板出口槽（R14/R15 片 A 北支 x: -11.05..-9.15，槽开 x: -11.15..-8.60, y: 18.50..20.20, Z=1.00..2.15，与左生耳内壁 x=-11.15 齐平）
    north_branch_slot = box(-LUG_SLOT_HALF_X, -8.60, 18.50, 20.20, 1.00, 2.15)

    # 南端 R14 双片出盒槽（R14 A+B 占 x: -5.12..+9.00，开对称宽槽 x: -9.60..+9.60, y: -20.50..-18.00, Z=1.00..2.20）
    south_fpc_slot = box(-9.60, 9.60, -20.50, -18.00, 1.00, 2.20)

    # 南北内凹生耳弧槽与敞口表带槽（对齐 IMG_3799.MOV / IMG_3800.MOV：
    # 圆心在 (SOUTH_PIN_Y=-21.20 / NORTH_PIN_Y=+21.65, PIN_Z=3.70)，半径 R=1.95 mm，
    # 内侧弧壁 Y=-19.25 / +19.70 嵌入盒体端面内侧，中间 22.30 mm 槽在 |y|>20.00 全高敞开无顶棚，表带可贴腕直接回折）
    south_lug_slot = (
        cyl_x(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, SOUTH_PIN_Y, PIN_Z, 2 * LUG_GROOVE_R)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, -25.00, SOUTH_PIN_Y + LUG_GROOVE_R, -0.10, PIN_Z)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, -25.00, -20.00, PIN_Z, SPLIT_Z + 0.20)
    )
    north_lug_slot = (
        cyl_x(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, NORTH_PIN_Y, PIN_Z, 2 * LUG_GROOVE_R)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, NORTH_PIN_Y - LUG_GROOVE_R, 25.00, -0.10, PIN_Z)
        + box(-LUG_SLOT_HALF_X, LUG_SLOT_HALF_X, 20.00, 25.00, PIN_Z, SPLIT_Z + 0.20)
    )

    # 快拆弹簧棒销孔（两侧短耳内壁盲孔 Ø1.20 mm，深 1.20 mm，外侧留壁 1.00 mm ≥ 0.80 mm）
    south_pin_holes = cyl_x(
        -LUG_SLOT_HALF_X - pin_hole_depth,
        LUG_SLOT_HALF_X + pin_hole_depth,
        SOUTH_PIN_Y,
        PIN_Z,
        PIN_HOLE_D,
    )
    north_pin_holes = cyl_x(
        -LUG_SLOT_HALF_X - pin_hole_depth,
        LUG_SLOT_HALF_X + pin_hole_depth,
        NORTH_PIN_Y,
        PIN_Z,
        PIN_HOLE_D,
    )

    # 东侧 USB-C 窗口下半部（Z=5.10..6.65, y=-5.97..5.97, x=21.40..23.20）+ 外侧插头护套沉台（x=22.30..23.20, y=-6.40..6.40, z=4.90..6.65）
    usb_cut = box(21.40, 23.20, -5.97, 5.97, 5.10, SPLIT_Z + 0.10) + box(
        22.30, 23.20, -6.40, 6.40, 4.90, SPLIT_Z + 0.10
    )

    s = outer - inner_cav - fpc_floor_groove
    # 南侧内壁局部加厚至 y=-18.40（Z=1.40..SPLIT_Z 避让底槽 Z<=1.22 软板，距 PCB 南边 y=-18.25 留 0.15 mm 净空，确保南生耳内凹弧槽 y=-19.25 内壁实厚 0.85 mm ≥ 0.80 mm）
    s += box(-11.80, 11.80, -18.85, -18.40, 1.40, SPLIT_Z)

    s = (
        s
        - north_pocket
        - north_branch_slot
        - south_fpc_slot
        - south_lug_slot
        - north_lug_slot
        - south_pin_holes
        - north_pin_holes
        - usb_cut
    )

    # 采集板 D18 与主控板 R2 四角同位 (±19.05, ±15.75) 安装孔支撑沉台：
    # - 外径 Ø4.50 mm 支撑柱（Z=0.95..2.55），顶面环形台阶（Ø2.80..4.50 mm, Z=2.55）直接托住 D18 采集板底面；
    # - 上段 Ø2.80 mm 沉头孔（Z=1.65..2.60，深 0.90 mm，壁厚 (4.50-2.80)/2 = 0.85 mm ≥ 0.80 mm）：
    #   容纳双板对锁时下方 M1.4×2.5 螺丝头（Ø2.50×0.80 mm, Z=1.75..2.55），兼作双板模块落盒四向定位沉孔；
    # - 下段 Ø1.25 mm 同轴 M1.4 自攻底孔（Z=1.00..1.65，孔底留实心底壁 1.00-0.15 = 0.85 mm ≥ 0.80 mm 盲孔防汗）：
    #   支持改用 M1.4×6 mm 长螺丝从主控板顶面一穿到底直接锁入底壳。
    d18_holes = [
        (-19.05, 15.75),
        (19.05, 15.75),
        (-19.05, -15.75),
        (19.05, -15.75),
    ]
    for hx, hy in d18_holes:
        s += cyl(hx, hy, 4.50, 0.95, 2.55)
        s -= cyl(hx, hy, 2.80, 1.65, 2.60) + cyl(hx, hy, 1.25, 1.00, 1.70)

    # 西侧与东侧无器件边缘托台（Z=3.55..SPLIT_Z，齐平托住主控板 R2 底面 Z=6.79，避让四角安装柱）
    s += box(-21.90, -20.70, -13.00, 13.00, 3.55, SPLIT_Z)
    s += box(20.70, 21.90, -13.00, -7.20, 3.55, SPLIT_Z)

    # 北侧无铜走廊 2.4 GHz FPC 贴片天线两端限位卡肩（天线 20.0×4.2×0.20 mm 贴于北壁 y=18.80, x=-10.0..+10.0, Z=4.45..8.65）
    # 在 x = ±[10.12..11.05], y = 18.28..18.90, Z = 4.25..SPLIT_Z 设左右限位肩，不侵入 PCB y<=18.25
    s += box(-11.05, -10.12, 18.28, 18.90, 4.25, SPLIT_Z)
    s += box(10.12, 11.05, 18.28, 18.90, 4.25, SPLIT_Z)

    # 减去六个底部触点孔（放在加柱之后以确保孔道完全贯通无残膜）
    for x in (-8.0, 8.0):
        for y in (-7.5, 7.5):
            s -= cyl(x, y, 4.10, 0.05, 1.30) + cyl(x, y, 5.20, 0.70, 1.30)
    for y in (-7.5, 7.5):
        s -= cyl(0.0, y, 3.10, 0.05, 1.30) + cyl(0.0, y, 4.20, 0.70, 1.30)

    return s.clean()


def build_cover(
    total_height=TOTAL_HEIGHT,
    top_outer_r=TOP_OUTER_FILLET_R,
    top_inner_r=TOP_INNER_FILLET_R,
    outer_r=OUTER_CORNER_R,
    ufl_blister=True,
):
    """构建上盖 cover（单实体）：
    - 外轮廓 46×40 R5.8，Z=6.60..total_height（默认 10.10 mm）
    - 顶面四周大圆角 R3.0，内腔顶面四周内圆角 R1.8，顶壁基准厚 1.00 mm（内顶面 Z = total_height - 1.00 = 9.10 mm）
    - 针对嘉立创库 3D 中偏高的两颗 SOT-23-6（U12、U17，模型顶 Z=9.10，真实规格书 8.86）设 0.16 mm 浅让位槽（Z=9.26，剩顶壁 0.84 mm ≥ 0.80 mm）
    - J300（U.FL-R-SMT-1，中心 6.21, 15.78）上方设 1代 U.FL 同轴插头微凸透明观察窗（内顶 Z=9.98，外顶 Z=10.84，顶壁厚 0.86 mm ≥ 0.80 mm）与北向同轴引线槽（x: 5.40..7.00, y: 17.00..18.80, Z=7.20..9.68）
    - 顶部 SW300 阶梯防脱按压孔（孔壁与柱塞留 0.20 mm 间隙，兼容 8001 全透明喷油）
    - 指示灯 D401（x=9.6..10.45, y=8.9..10.56）上方保持全透明平整无遮挡筋
    - 四角主控角缺口定位压柱（Z=6.60..9.10，压住主控板四角并对齐底壳）
    """
    inner_z = total_height - 1.00
    outer = domed_prism(BODY_W, BODY_L, SPLIT_Z, total_height, outer_r, top_outer_r)
    if ufl_blister and abs(total_height - TOTAL_HEIGHT) < 1e-4:
        # J300 1代 U.FL 同轴插头顶面流线型透明微凸包（x: 3.80..8.60, y: 13.30..18.40, Z: 8.60..10.84，顶边圆角 R0.70）
        blister_raw = b.Pos(6.20, 15.85, 8.60) * b.extrude(
            b.RectangleRounded(4.80, 5.10, 1.30), amount=2.24
        )
        b_edges = [
            e
            for e in blister_raw.edges()
            if abs(e.bounding_box().min.Z - 10.84) < 1e-4
            and abs(e.bounding_box().max.Z - 10.84) < 1e-4
        ]
        blister = b.fillet(b_edges, 0.70) & rounded_prism(
            BODY_W, BODY_L, SPLIT_Z, 11.50, outer_r
        )
        outer = (outer + blister).clean()

    inner = domed_prism(
        INNER_W, INNER_L, SPLIT_Z - 0.20, inner_z, INNER_CORNER_R, top_inner_r
    )
    s = outer - inner

    # 当 total_height 为标准 10.10 且 top_inner_r <= 2.0 时，为 U12、U17、开关防脱翼、J300 同轴插头与北走廊天线预留内槽（剩顶壁 ≥ 0.84 mm）
    if abs(total_height - TOTAL_HEIGHT) < 1e-4 and top_inner_r <= 2.05:
        s -= box(-20.40, -17.15, -1.00, 2.20, inner_z - 0.20, inner_z + 0.16)
        s -= box(8.75, 12.05, -4.85, -1.65, inner_z - 0.20, inner_z + 0.16)
        s -= box(3.40, 5.70, 12.15, 14.15, inner_z - 0.20, inner_z + 0.12)
        if ufl_blister:
            # J300 1代 U.FL 同轴插头让位腔（x: 4.64..7.95 与开关孔东壁 x=4.64 直接台阶相连，消除薄隔墙；内顶 Z=9.98，顶壁厚 10.84-9.98 = 0.86 mm ≥ 0.80 mm）
            # 底面从 Z=7.20 起切，清除北内圆角 R1.8 侵入区
            s -= box(4.64, 7.95, 14.05, 17.55, 7.20, 9.98)
            # J300 向北引出 Ø0.81 mm 同轴线至北侧无铜走廊 FPC 天线的走线槽（x: 5.40..7.00, y: 17.00..18.80, Z=7.20..9.68）
            s -= box(5.40, 7.00, 17.00, 18.80, 7.20, 9.68)
            # 北侧无铜走廊 2.4 GHz FPC 贴片天线（x: -10.0..+10.0, y: 18.42..18.62, Z: 4.45..8.65）顶部内圆角让位槽（剩北上角斜壁厚 ≥ 1.15 mm）
            s -= box(-10.20, 10.20, 18.30, 18.80, SPLIT_Z - 0.10, 8.80)

    # 东侧 USB-C 窗口上半部（Z=6.55..8.68, y=-5.97..5.97, x=20.80..23.20 清除顶内圆角与 J400 顶面边角）+ 外侧插头护套沉台
    s -= box(20.80, 23.20, -5.97, 5.97, SPLIT_Z - 0.10, 8.68)
    s -= box(22.30, 23.20, -6.40, 6.40, SPLIT_Z - 0.10, 8.80)

    # 顶部 SW300 阶梯孔：
    # 上层通孔（Z=8.60..total_height+1.0）：x in [2.30, 4.64], y in [13.50, 16.66]（配柱塞帽 x in [2.50, 4.44], y in [13.70, 16.46]，四周间隙 0.20 mm）
    s -= box(2.30, 4.64, 13.50, 16.66, inner_z - 0.50, total_height + 1.00)

    # 西侧与东南侧无器件边缘压紧凸台（Z=7.58..inner_z，配合四角 M1.4 螺丝+板间柱辅助限位主控板；
    # 四角 (±19.05, ±15.75) 上方留出完整内顶净空 Z=8.88..9.10 mm 容纳 M1.4 螺丝头 Z=7.41..8.21 mm）
    s += box(-21.90, -20.75, -14.20, -10.20, 7.58, inner_z) & domed_prism(
        INNER_W + 0.20, INNER_L + 0.20, SPLIT_Z, inner_z, INNER_CORNER_R, top_inner_r
    )
    s += box(20.75, 21.90, -13.00, -7.50, 7.58, inner_z) & domed_prism(
        INNER_W + 0.20, INNER_L + 0.20, SPLIT_Z, inner_z, INNER_CORNER_R, top_inner_r
    )

    return s.clean()


def build_woven_strap_loop(y_pos, is_north=False):
    """构建对齐 IMG_3797.MOV 的 22.04 mm 编织表带回折圆筒套管参考体（非 3D 打印件，用于装配预览与零干涉验证）：
    - 圆筒套管：绕 (y_pos, PIN_Z=3.70)，外径 Ø3.80 mm（R=1.90 mm，Z=1.80..5.60），内孔 Ø1.84 mm 包裹快拆弹簧棒，实测宽 22.04 mm（x: -11.02..+11.02）
    - 背部快拆拨珠开槽：x in [3.50, 6.50] 留拨杆滑槽
    - 向外延伸段：贴合手腕方向引出 5.2 mm 编织带头段（Z=2.25..5.60），完全位于下层 R14/R15 软板（Z<=1.38）上方
    """
    hw = STRAP_MEASURED_W / 2.0
    outer_cyl = cyl_x(-hw, hw, y_pos, PIN_Z, STRAP_LOOP_OUTER_D)
    inner_bore = cyl_x(-hw - 0.20, hw + 0.20, y_pos, PIN_Z, SPRING_BAR_BARREL_D + 0.04)
    if is_north:
        tail = box(-hw, hw, y_pos, y_pos + 5.20, 2.25, PIN_Z + STRAP_LOOP_OUTER_D / 2)
        qr_window = box(3.50, 6.50, y_pos - 2.00, y_pos + 0.50, PIN_Z, PIN_Z + 2.10)
    else:
        tail = box(-hw, hw, y_pos - 5.20, y_pos, 2.25, PIN_Z + STRAP_LOOP_OUTER_D / 2)
        qr_window = box(3.50, 6.50, y_pos - 0.50, y_pos + 2.00, PIN_Z, PIN_Z + 2.10)
    return ((outer_cyl + tail) - inner_bore - qr_window).clean()


STRAP_BODY_W = 23.20
# R15 平展坐标 → 盒/表带坐标：X = y_R15 − 50，Y = R15_STRAP_C − x_R15（F 面朝皮肤，转 90°，不镜像）。
# 盒底 E1/E2（x 50.5/65.5）落在 tray 孔 Y ±7.5，所以 C = 58；表带同一个 C，平放时软板不长不短（Mako 2026-11-09 定对齐 R15）。
# 旧 R12 表带南用 57、北用 59，平放各差 1 mm，先焊的铆钉落不进头孔。check.py 逐个焊盘核这组 Y。
R15_DIR = P.parents[1] / "16ch-c08b-round/strap-fpc-r15"
R15_STRAP_C = 58.0
NORTH_ISLAND_YS = (R15_STRAP_C - 24.0, R15_STRAP_C - 16.0)                         # CH3 x24、CH4 x16 → 34、42
SOUTH_ISLAND_YS = tuple(R15_STRAP_C - 90.0 - 8.00 * k for k in range(12))          # CH5 x90 … CH16 x178 → −32 … −120
EXT_ELECTRODE_XS = (-9.00, 9.00)
# 表带根部：北段从 29.40 起（R15 北支 X −11.05..−9.15 和 CH3 岛斜角 29.2 起进内袋），南段仍从 −28.20 起。
# 内袋整宽从根部端面直通（旧版只开 ±5 中缝，A 出盒带 X 3.3..9.0 和北支被挡）。
NORTH_ROOT_Y = 29.40
SOUTH_ROOT_Y = -28.20
# 北段内袋 −X 侧到 −11.15：CH3 岛和北支外沿在 −11.05（R15 north_split_shift），间隙 0.10 和南段 ±10.70 对 ±10.60 相同。
# 带身 −X 侧外扩到 −11.95，侧壁保持 0.80（壁厚门）；+X 侧不变。
NORTH_POCKET_X = (-11.15, 10.70)
NORTH_BODY_X = (-11.95, STRAP_BODY_W / 2.0)
SOUTH_POCKET_X = (-10.70, 10.70)
NORTH_POCKET_END_Y = 45.90      # CH4 端头 45.50（触点 +3.5）+ 0.40
SOUTH_POCKET_END_Y = -123.90    # CH16 端头 −123.50 − 0.40
SOUTH_BODY_END_Y = -124.70      # 端墙 0.80（壁厚门）；再往外是 21.2 宽舌片
# 软板出盒到表带口的下坡段：盒内软板底 Z 1.02，表带内袋底 0.50；起点是 tray 出线槽外沿
FPC_BOX_Z = 1.02
NORTH_BRANCH_EXIT_Y = 20.20
SOUTH_FPC_EXIT_Y = -20.50

# 表带黄铜阶梯铆钉触点规格：Φ1.5 * Φ0.8 * 2 mm（材质：黄铜，头径 Φ1.50×厚 0.50 mm + 杆径 Φ0.80×长 1.50 mm，总长 2.00 mm）
STRAP_CONTACT_HEAD_D = 1.50
STRAP_CONTACT_HEAD_H = 0.50
STRAP_CONTACT_SHAFT_D = 0.80
STRAP_CONTACT_SHAFT_H = 1.50
STRAP_CONTACT_TOTAL_H = 2.00
STRAP_CONTACT_HEAD_CBORE_D = 1.66
STRAP_CONTACT_SOLDER_RECESS_D = 1.80
STRAP_BOTTOM_Z = 0.15             # 表带贴肤底面（钉头底 Z=0，露出 0.15）
# 先焊后装（Mako 2026-11-09 定）：钉头贴 R15 软板 F 面（贴肤面）Ø1.8 焊盘，杆穿 Ø1.0 孔和 B 面 PI 补强孔，
# 在背面补强孔口点锡、吸进孔壁；28 颗焊完测通，再整条软板塞进表带。
# 原因：R15 B 面补强盖满焊盘环（背面没有可焊铜环），旧版焊点又封在表带实心层下面，装好后烙铁够不到。
R15_FPC_T = 0.203                 # R15 strap-a/b.kicad_pcb 板厚（check.py 读板核对）
R15_ISLAND_STIFF_T = 0.15         # R15 build.py STIFF_T_ISL：岛补强 PI 含胶，在 B 面（check.py 读脚本核对）
STRAP_FPC_Z_MIN = STRAP_CONTACT_HEAD_H                         # 0.50：软板 F 面直接压在钉头顶上
STRAP_FPC_Z_MAX = STRAP_FPC_Z_MIN + R15_FPC_T + R15_ISLAND_STIFF_T  # 0.853：含 B 面补强
STRAP_FPC_POCKET_Z_MIN = STRAP_FPC_Z_MIN
STRAP_FPC_POCKET_Z_MAX = 0.95     # 软板+补强 0.353，上方留 0.097
# 软板下 TPU = 0.50 − 0.15 = 0.35 mm（整条内袋底）：钉头只有 0.5 高，低于 0.8 壁厚门，Mako 2026-11-09 批准放宽；
# 阈值写死在 check.py，不从这里读。
# R15 B 片走线带（geometry.json B_BAND y 44.88..52.80）压在 A 片南岛 CH5–CH8（x 87.2..116.8）的补强上，
# 那里叠层 0.203 + 0.15 + 0.203 = 0.556，比内袋 0.45 厚。A 南段外形 x 86.5..117.5（含岛斜角），
# 按 Y = 58 − x 在 Y −59.5..−28.5；B 带 X −5.12..2.80。
R15_B_OVER_A_X = (44.88 - 50.0, 52.80 - 50.0)
R15_B_OVER_A_Y = (R15_STRAP_C - 117.5, R15_STRAP_C - 86.5)
STRAP_B_RELIEF_HALF_X = 5.32      # 内袋顶局部让位按 ±5.32 对称开（B 带 ±0.2，左右翻了也盖得住；触点在 ±9 不受影响）
STRAP_B_RELIEF_Z_MAX = 1.15       # A+补强+B 顶到 1.056，留 0.094；顶上剩 1.75
STRAP_SOLDER_RECESS_Z_MAX = 2.08  # 杆顶 Z=2.00（未剪脚）+ 0.08；背面锡点也在这个 Ø1.8 腔里
STRAP_BODY_Z_MAX = 2.90
# 腕围 155–230 mm（Mako 2026-11-06 定）：扣框紧贴 CH4 岛，小腕 CH16 不压扣框；舌片加长，230 也扣得住。
# check.py 的 strap_wrist_range 按椭圆佩戴模型逐 5 mm 核（假设模型，未实戴）。
NORTH_BUCKLE_Y = (46.20, 52.00)       # 日字扣外框：内梁 46.20..47.60、外梁 50.60..52.00（旧 47.00..55.60）
NORTH_BUCKLE_SLOT_Y = (47.60, 50.60)  # 穿带窗 3.0（旧 4.0）；舌片连横纹厚 2.60，留 0.40
SOUTH_TAIL_END_Y = -217.00            # 舌尖（旧 -138.00 腕围 >169 够不到扣；−214 时 230 腕围翻回后穿不满带圈，再加 3 mm）
# 舌片剪线（Mako 2026-11-09 定「剪短舌片」）：小腕围时舌片过窗后多出很多（155 时 86 mm），翻回会压在电极段外侧甩着。
# 舌片两侧边各开一个 0.6 × 0.5 缺口，剪在一对缺口之间。按腕围 W 那道剪，舌片过扣窗中心还剩 TRIM_TAIL_MM；
# 腕围在两道之间时用不大于自己腕围的那道（5 mm 一档，剩约 20–25 mm；155 用 160 那道，剩约 29）；220 以上不剪。
# 10 mm 一档时每档上端只剩约 15.5，舌片绕外梁翻回（约 14.6，check.py tail_wrap_len）后穿不满 3 mm 带圈，所以改 5 mm。
# Y 位置是 check.py 椭圆腕围模型（假设，未实戴）算出来的，check.py strap_trim_marks / strap_keeper_tail_reach 逐道核对。
TRIM_TAIL_MM = 25.0
TRIM_MARKS = {160: -157.12, 165: -161.61, 170: -166.13, 175: -170.69, 180: -175.28, 185: -179.89,
              190: -184.53, 195: -189.19, 200: -193.87, 205: -198.57, 210: -203.29, 215: -208.03}
TRIM_UNCUT_FROM = 220                 # 这个腕围起不剪（最后一道 215 用到 219.99）
TRIM_NOTCH_LEN = 0.60                 # 沿带长
TRIM_NOTCH_DEPTH = 0.50               # 从带边（±10.60）切进去；舌片两侧横纹只到 ±9.20，不碰


def r15_outline_face(sheet, x_rng, y_rng):
    """R15 片 A/B 真实外形（geometry.json）映射到表带坐标，裁到矩形 x_rng × y_rng。"""
    pts = json.loads((R15_DIR / "geometry.json").read_text())[sheet]["outline"]
    face = b.Polygon(*[(y - 50.0, R15_STRAP_C - x) for x, y in pts], align=None)
    return face & b.Pos((x_rng[0] + x_rng[1]) / 2, (y_rng[0] + y_rng[1]) / 2) * b.Rectangle(
        x_rng[1] - x_rng[0], y_rng[1] - y_rng[0]
    )


def slab(face, z0, z1):
    return b.Pos(0, 0, z0) * b.extrude(face, amount=z1 - z0)


def ramp(face, y_from, y_to, z_end=STRAP_FPC_Z_MIN):
    """出盒段：平面外形在 y_from 处底面 Z=FPC_BOX_Z，绕 X 轴转成直线下坡，到 y_to 处底面落到 z_end 上方一点。"""
    L, dz = abs(y_to - y_from), FPC_BOX_Z - z_end
    ang = math.degrees(math.atan2(dz, L)) * (1 if y_to < y_from else -1)
    s = b.extrude(face, amount=R15_FPC_T)
    return b.Pos(0, 0, FPC_BOX_Z) * s.rotate(b.Axis((0, y_from, 0), (1, 0, 0)), ang)


def strap_contact_cut(ex, ey):
    """每颗触点在表带上挖的孔：底面 Ø1.66 头孔（钉头穿出）+ 软板上方 Ø1.8 杆/锡点腔（不通顶）。"""
    return cyl(ex, ey, STRAP_CONTACT_HEAD_CBORE_D, 0.05, STRAP_CONTACT_HEAD_H) + cyl(
        ex, ey, STRAP_CONTACT_SOLDER_RECESS_D, STRAP_FPC_POCKET_Z_MIN, STRAP_SOLDER_RECESS_Z_MAX
    )


def build_military_green_strap_north(pocket_x=NORTH_POCKET_X, root_y=NORTH_ROOT_Y):
    """构建军绿色表带北段短带 + 一体战术日字扣环 strap_military_green_north（单实体，可直接 TPU 95A 3D 打印）：
    - 生耳连接头：宽 22.04 mm（x: -11.02..+11.02），外径 Ø3.80 mm 圆筒套管（中心 Y=+21.65, Z=3.70），内孔 Ø1.84 mm 穿快拆生耳 + 背部快拆拨杆窗
    - 桥接过渡段：Y=21.65..29.60 保持 Z=2.25..5.60，下面是 R15 北支出盒下坡段（Z 1.02→0.50）
    - 北段 2 节电极岛带身（CH3 Y=+34.0, CH4 Y=+42.0，Y = 58 − x_R15）：X −11.95..+11.60（−X 侧为 CH3 岛/北支外扩 0.35），
      底面 R15 软板内袋 X −11.15..+10.70（Z=0.50..0.95，从根部 29.40 端面直通）与 x=±9.00 mm Φ1.5×Φ0.8×2.0 mm 黄铜触点孔
      （底面 Ø1.66 头孔 + 软板上方 Ø1.80 杆/锡点腔 Z..2.08；软板下 TPU 0.35 mm，Mako 批准放宽）
    - 北端一体日字环扣（Y=46.20..52.00, Z=0.15..4.35，紧贴 CH4 岛）：内穿带窗 21.60 × 3.00 mm，供南段长带舌片穿入回折固定
    参数 pocket_x / root_y 只给 check.py 跑反例用。
    """
    hw_head = STRAP_MEASURED_W / 2.0
    bx0, bx1 = NORTH_BODY_X
    outer_cyl = cyl_x(-hw_head, hw_head, NORTH_PIN_Y, PIN_Z, STRAP_LOOP_OUTER_D)
    bridge = box(-hw_head, hw_head, NORTH_PIN_Y, root_y + 0.20, 2.25, PIN_Z + STRAP_LOOP_OUTER_D / 2)
    step_down = box(bx0, bx1, root_y, root_y + 1.40, 0.15, PIN_Z + STRAP_LOOP_OUTER_D / 2)
    body = box(bx0, bx1, root_y, NORTH_BUCKLE_Y[0] + 0.20, STRAP_BOTTOM_Z, STRAP_BODY_Z_MAX)
    buckle_outer = box(bx0, bx1, NORTH_BUCKLE_Y[0], NORTH_BUCKLE_Y[1], 0.15, 4.35)

    s = outer_cyl + bridge + step_down + body + buckle_outer
    for yr in (33.0, 35.5, 38.0, 40.5, 43.0, 45.5):
        s += box(-10.80, 10.80, yr - 0.55, yr + 0.55, STRAP_BODY_Z_MAX, STRAP_BODY_Z_MAX + 0.30)

    inner_bore = cyl_x(-hw_head - 0.25, hw_head + 0.25, NORTH_PIN_Y, PIN_Z, SPRING_BAR_BARREL_D + 0.04)
    qr_window = box(3.50, 6.50, NORTH_PIN_Y - 2.00, NORTH_PIN_Y + 2.00, PIN_Z - 0.50, PIN_Z + 2.10)
    buckle_slot = box(-10.80, 10.80, NORTH_BUCKLE_SLOT_Y[0], NORTH_BUCKLE_SLOT_Y[1], -0.50, 5.00)
    fpc_pocket = box(pocket_x[0], pocket_x[1], root_y - 0.10, NORTH_POCKET_END_Y,
                     STRAP_FPC_POCKET_Z_MIN, STRAP_FPC_POCKET_Z_MAX) + box(
        -5.00, 5.00, root_y - 0.10, NORTH_POCKET_END_Y, 0.05, STRAP_FPC_POCKET_Z_MAX
    )

    s = s - inner_bore - qr_window - buckle_slot - fpc_pocket
    for ey in NORTH_ISLAND_YS:
        for ex in EXT_ELECTRODE_XS:
            s -= strap_contact_cut(ex, ey)
    return s.clean()


def strap_b_relief():
    """南段内袋顶在 A 南岛 CH5–CH8 上方的局部让位（装 R15 B 片走线带）。"""
    return box(-STRAP_B_RELIEF_HALF_X, STRAP_B_RELIEF_HALF_X, R15_B_OVER_A_Y[0] - 0.5, R15_B_OVER_A_Y[1] + 0.5,
               STRAP_FPC_POCKET_Z_MIN, STRAP_B_RELIEF_Z_MAX)


def build_r15_b_over_a():
    """R15 B 片走线带压在 A 南岛补强上的那一段（参考体，供干涉门用）。"""
    return box(R15_B_OVER_A_X[0], R15_B_OVER_A_X[1], R15_B_OVER_A_Y[0], R15_B_OVER_A_Y[1],
               STRAP_FPC_Z_MAX, STRAP_FPC_Z_MAX + R15_FPC_T)


def build_military_green_strap_south(b_relief=True, pocket_root_y=SOUTH_ROOT_Y + 0.10):
    """构建军绿色表带南段 12 节电极长带 strap_military_green_south（单实体，可直接 TPU 95A 3D 打印）：
    - 生耳连接头：宽 22.04 mm（x: -11.02..+11.02），外径 Ø3.80 mm 圆筒套管（中心 Y=-21.20, Z=3.70），内孔 Ø1.84 mm 穿快拆生耳 + 背部快拆拨杆窗
    - 桥接过渡段：Y=-28.40..-21.20 保持 Z=2.25..5.60，下面是 R15 南出盒 A、B 带下坡段（Z 1.02→0.50）
    - 南段 12 节电极岛带身（CH5..CH16，Y=-32.0..-120.0，节距 8.0 mm，Y = 58 − x_R15）：外宽 23.20 mm，
      底面 R15 软板内袋 X ±10.70（Z=0.50..0.95，从根部 −28.20 端面直通，A 出盒带和 B 带都进得去）与 24 个 Φ1.5×Φ0.8×2.0 mm 黄铜触点孔（x=±9.00 mm；先焊后装）
    - 尾端穿扣调节舌片（Y=-217.0..-124.7，宽 21.20 mm，腕围 155–230 都扣得住）：带战术防滑横纹，穿入北端日字扣环（21.60 × 3.00 mm 窗）回折固定
    参数 pocket_root_y 只给 check.py 跑反例用（旧版 −29.60：整宽内袋不通根部）。
    """
    hw_head = STRAP_MEASURED_W / 2.0
    hw_body = STRAP_BODY_W / 2.0
    outer_cyl = cyl_x(-hw_head, hw_head, SOUTH_PIN_Y, PIN_Z, STRAP_LOOP_OUTER_D)
    bridge = box(-hw_head, hw_head, SOUTH_ROOT_Y - 0.20, SOUTH_PIN_Y, 2.25, PIN_Z + STRAP_LOOP_OUTER_D / 2)
    step_down = box(-hw_body, hw_body, SOUTH_ROOT_Y - 1.40, SOUTH_ROOT_Y, 0.15, PIN_Z + STRAP_LOOP_OUTER_D / 2)
    body = box(-hw_body, hw_body, SOUTH_BODY_END_Y, SOUTH_ROOT_Y, STRAP_BOTTOM_Z, STRAP_BODY_Z_MAX)
    tail_tip = box(-10.60, 10.60, SOUTH_TAIL_END_Y, SOUTH_BODY_END_Y + 0.60, 0.15, 2.45)

    s = outer_cyl + bridge + step_down + body + tail_tip
    for k in range(24):
        yr = -30.00 - 4.00 * k
        s += box(-10.80, 10.80, yr - 0.65, yr + 0.65, STRAP_BODY_Z_MAX, STRAP_BODY_Z_MAX + 0.30)
    for yr in [-127.0 - 3.0 * k for k in range(int((-127.0 - SOUTH_TAIL_END_Y - 1.5) // 3.0) + 1)]:
        s += box(-9.20, 9.20, yr - 0.55, yr + 0.55, 2.45, 2.75)

    inner_bore = cyl_x(-hw_head - 0.25, hw_head + 0.25, SOUTH_PIN_Y, PIN_Z, SPRING_BAR_BARREL_D + 0.04)
    qr_window = box(3.50, 6.50, SOUTH_PIN_Y - 2.00, SOUTH_PIN_Y + 2.00, PIN_Z - 0.50, PIN_Z + 2.10)
    fpc_pocket = box(SOUTH_POCKET_X[0], SOUTH_POCKET_X[1], SOUTH_POCKET_END_Y, pocket_root_y,
                     STRAP_FPC_POCKET_Z_MIN, STRAP_FPC_POCKET_Z_MAX) + box(
        -5.00, 5.00, SOUTH_POCKET_END_Y, SOUTH_ROOT_Y + 0.10, 0.05, STRAP_FPC_POCKET_Z_MAX
    )

    s = s - inner_bore - qr_window - fpc_pocket
    for ym in TRIM_MARKS.values():
        for sx in (-1, 1):
            x_in, x_out = sx * (10.60 - TRIM_NOTCH_DEPTH), sx * 10.90
            s -= box(min(x_in, x_out), max(x_in, x_out), ym - TRIM_NOTCH_LEN / 2, ym + TRIM_NOTCH_LEN / 2, -1.0, 4.0)
    if b_relief:
        s -= strap_b_relief()
    for ey in SOUTH_ISLAND_YS:
        for ex in EXT_ELECTRODE_XS:
            s -= strap_contact_cut(ex, ey)
    return s.clean()


def build_r15_strap_fpc():
    """R15 软板盒外部分的真实外形参考体（geometry.json，Y = 58 − x）：
    - 北：片 A 从北支出口槽外沿 20.20 起（只取北支 X<−8.9，两尾在盒内回折不算）下坡到根部 29.40，再平放进内袋到 CH4 端头 45.50
    - 南：片 A、B 从出线槽外沿 −20.50 下坡到根部 −28.20，再平放；B 从根部到 A 尽头（−59.5）叠在 A 上一层，再往南与 A 同层
    平放段统一按软板 + B 面补强 Z 0.50..0.853 算（保守）；下坡段只有软板 0.203。"""
    zf, zb = STRAP_FPC_Z_MIN, STRAP_FPC_Z_MAX
    big = (-30.0, 30.0)
    north = ramp(r15_outline_face("a", (-30.0, -8.90), (NORTH_BRANCH_EXIT_Y, 28.0)), NORTH_BRANCH_EXIT_Y, NORTH_ROOT_Y)
    north += ramp(r15_outline_face("a", big, (28.0, NORTH_ROOT_Y)), NORTH_BRANCH_EXIT_Y, NORTH_ROOT_Y)
    north += slab(r15_outline_face("a", big, (NORTH_ROOT_Y, 60.0)), zf, zb)
    south = ramp(r15_outline_face("a", big, (SOUTH_ROOT_Y, SOUTH_FPC_EXIT_Y)), SOUTH_FPC_EXIT_Y, SOUTH_ROOT_Y)
    # B 按保守走法：出盒后只降到 A+补强顶面 0.853，进根部就骑在 A 上（实物会在 −28.5 前后才爬上去）
    south += ramp(r15_outline_face("b", big, (SOUTH_ROOT_Y, SOUTH_FPC_EXIT_Y)), SOUTH_FPC_EXIT_Y, SOUTH_ROOT_Y, zb)
    south += slab(r15_outline_face("a", big, (-200.0, SOUTH_ROOT_Y)), zf, zb)
    ya0, ya1 = R15_B_OVER_A_Y
    south += slab(r15_outline_face("b", big, (ya0, SOUTH_ROOT_Y)), zb, zb + R15_FPC_T)  # 根部起叠在 A 上
    south += slab(r15_outline_face("b", big, (-200.0, ya0)), zf, zb)                   # A 尽头以南
    return north, south


def build_strap_electrodes_and_fpc():
    """构建表带内嵌的 R15 软板（真实外形，见 build_r15_strap_fpc；28 个 Ø1.00 mm PTH 孔）与 28 颗 Φ1.5×Φ0.8×2.0 mm 黄铜触点（CH3..CH16，x=±9.00 mm；钉头顶贴软板 F 面焊盘，杆从背面伸出 1.147 mm 未剪脚）参考体。"""
    electrodes = []
    fpc_holes = []
    for ey in NORTH_ISLAND_YS + SOUTH_ISLAND_YS:
        for ex in EXT_ELECTRODE_XS:
            c = cyl(ex, ey, STRAP_CONTACT_HEAD_D, 0.0, STRAP_CONTACT_HEAD_H) + cyl(
                ex, ey, STRAP_CONTACT_SHAFT_D, STRAP_CONTACT_HEAD_H, STRAP_CONTACT_TOTAL_H
            )
            electrodes.append(c)
            fpc_holes.append(cyl(ex, ey, 1.00, STRAP_FPC_Z_MIN - 0.05, STRAP_FPC_Z_MAX + 0.05))
    elec_comp = electrodes[0]
    for c in electrodes[1:]:
        elec_comp = elec_comp + c
    holes_comp = fpc_holes[0]
    for h in fpc_holes[1:]:
        holes_comp = holes_comp + h
    r15_strap_north, r15_strap_south = build_r15_strap_fpc()
    r15_strap_total = (r15_strap_north + r15_strap_south) - holes_comp
    return elec_comp.clean(), r15_strap_total.clean()


def build_lug_test_coupon():
    """构建用于快速 3D 打印试装 22.04 mm 快拆表带的局部测试样件 lug_test_22mm（单实体）：
    - 仅截取表壳南端结合部（x: -14.20..+14.20 宽 28.40 mm，y: -22.65..-16.50 长 6.15 mm，Z: 0.15..6.60 高 6.45 mm），省料 80%、12 分钟可打出
    - 完整保留 22.30 mm 槽宽（配 22.04 mm 实测表带连接头，单边留 0.13 mm 余量）、R1.95 内凹弧槽、两侧 Ø1.20×1.20 mm 盲孔及下层软板出线槽
    """
    return (build_tray() & box(-14.20, 14.20, -23.50, -16.50, 0.0, 7.00)).clean()


STRAP_COUPON_Y = (-70.00, SOUTH_ROOT_Y)   # CH5–CH9 五节 + 根部


def build_strap_test_coupon():
    """南段表带 CH5–CH9 打印试样 strap_test_coupon_ch5_ch9（单实体，TPU 95A，长约 42 mm）：
    从带身根部（Y −28.2，含根部 1.4 mm 台阶和延到根部的 0.35 唇边自由边）切到 CH9 岛后（Y −70.0）。
    CH5–CH8 段内袋中间有 B 带让位（顶 1.15），内袋顶只有两条 5.4 mm 窄桥；−60 往后（CH9 起）才是整宽 21 mm 横跨桥，
    所以一定要切到 CH9 之后，才试得到最没把握的那种桥。
    打出来量：CH5→CH9 同侧孔心距（名义 32.00）、左右孔心距（名义 18.00）、0.35 唇边成不成形、内袋顶有没有塌到唇边。
    """
    return (build_military_green_strap_south() & box(-15.0, 15.0, STRAP_COUPON_Y[0], STRAP_COUPON_Y[1], -1.0, 10.0)).clean()


# 带圈（活动，TPU 95A）：舌片按剪线剪短后，过窗翻回的那段用它套住。贴肤那面的框会把钉头顶离皮肤，所以只放在
# 扣框外沿和 CH16 钉头之间那段没有电极的带上；舌片绕外梁翻回还要占掉一段（舌片厚 + 约 1 mm 弯曲，假设），
# 155 时这段放不下。Mako 2026-11-09 定：带圈按「舌片 + 翻回舌片」两层做紧，只在腕围 ≥ KEEPER_MIN_WRIST 用。
# 165 起带圈停的那段整段在带身尽头（−124.7）以外，上下两层都是舌片（21.2 宽、连横纹 2.6 厚）；160 时一半压在 23.2 宽带身上，套不进。
# check.py strap_keeper_park 逐腕围核停放段（无电极、整段在舌片上），strap_keeper_fit 从实体量内框核套得进又不松。
KEEPER_MIN_WRIST = 165
KEEPER_IN_W = 21.20 + 0.60            # 21.80：舌片两侧各 0.30
KEEPER_IN_H = 2.60 * 2 + 0.40         # 5.60：两层舌片上下各 0.20（旧版按「带身 + 舌片」做 23.80 × 6.20，套两层舌片宽空 2.6、厚空 1.0）
KEEPER_WALL = 1.20                    # 外侧和两侧
KEEPER_SKIN_WALL = 0.80               # 贴肤一侧（−Y）
KEEPER_LEN = 3.00                     # 沿带长；打印时这个方向朝上（Z），框截面没有悬空
KEEPER_IN_R = 0.25                    # 内角小圆角：舌片方角要进得去


def build_strap_keeper(in_w=KEEPER_IN_W, in_h=KEEPER_IN_H):
    """带圈 strap_keeper（单实体）：X = 带宽方向、Y = 叠层厚度方向（−Y 贴肤）、Z = 沿带长，原点在内框中心底面。参数只给反例用。"""
    oh = in_h + KEEPER_WALL + KEEPER_SKIN_WALL
    outer = b.Pos(0, (KEEPER_WALL - KEEPER_SKIN_WALL) / 2) * b.extrude(
        b.RectangleRounded(in_w + 2 * KEEPER_WALL, oh, KEEPER_IN_R + KEEPER_SKIN_WALL), amount=KEEPER_LEN)
    inner = b.Pos(0, 0, -0.5) * b.extrude(b.RectangleRounded(in_w, in_h, KEEPER_IN_R), amount=KEEPER_LEN + 1.0)
    return (outer - inner).clean()


# 带圈试套件：先单打这一盘试松紧，再定带圈内高。舌片试样取南带 Y −165..−135（含 165、160 两道剪线缺口和横纹），
# 打两件，一件翻面叠在另一件上，模拟「过窗前的舌片 + 翻回的舌片」两层（横纹面对面）。
# 带圈三档内高：5.60 设计值（不打点）、5.80（顶面两点）、6.00（三点）；宽都按设计 21.80。FDM 内框偏小，挑刚好推得进、不自己滑的那档。
STRAP_TONGUE_TEST_Y = (-165.00, -135.00)
KEEPER_GAUGE_DOTS = {5.80: 2, 6.00: 3}


def build_strap_tongue_test():
    """舌片试样 strap_tongue_test（单实体，和南带同一几何、同一摆放）。"""
    return (build_military_green_strap_south() & box(-13.0, 13.0, STRAP_TONGUE_TEST_Y[0], STRAP_TONGUE_TEST_Y[1], -1.0, 7.0)).clean()


def build_strap_keeper_gauge(in_h):
    """试套用带圈：只改内高，顶面外侧壁上打 Ø0.8 × 0.4 小坑做记号（点数见 KEEPER_GAUGE_DOTS）。"""
    k = build_strap_keeper(in_h=in_h)
    n = KEEPER_GAUGE_DOTS[in_h]
    yc = in_h / 2 + KEEPER_WALL / 2
    for i in range(n):
        k -= cyl((i - (n - 1) / 2) * 2.0, yc, 0.80, KEEPER_LEN - 0.40, KEEPER_LEN + 0.10)
    return k.clean()


def build_whole_box_onepiece():
    """构建整盒一体打印单实体 whole_box_onepiece（1 solid）：
    将底壳 tray、上盖 cover 与顶面按钮帽融合成 1 个无缝单实体（46.00 × 45.75 × 10.69 mm，较旧版 51.60 mm 缩短 5.85 mm），
    用于一次性直接打印整只表盘外观手板，直接扣入南北两端 22.04 mm 快拆表带试戴看整体效果。
    内部与外界通过东侧 USB-C 窗口、南北下层软板槽、底部 6 个电极孔完全贯通，无封闭死腔（兼容 FDM 与光固化）。
    """
    tray = build_tray()
    cover = build_cover()
    seam_ring = rounded_prism(
        BODY_W, BODY_L, SPLIT_Z - 0.16, SPLIT_Z + 0.10, OUTER_CORNER_R
    ) - rounded_prism(
        INNER_W, INNER_L, SPLIT_Z - 0.20, SPLIT_Z + 0.15, INNER_CORNER_R
    )
    seam_ring -= box(20.70, 23.50, -6.50, 6.50, SPLIT_Z - 0.25, SPLIT_Z + 0.20)
    button_cap_solid = box(2.25, 4.69, 13.45, 16.71, 9.00, 10.40)
    whole = (tray + cover + seam_ring + button_cap_solid).clean()
    return whole


def build_switch_plunger():
    """构建顶部 45° 楔面开关柱塞 switch_plunger（单实体）：
    - 顶帽：x in [2.50, 4.44] (1.94 mm), y in [13.70, 16.46] (2.76 mm), Z in [8.96, 10.40]（高出盖顶 0.30 mm 方便盲按，与盖孔四周留 0.20 mm 间隙）
    - 防脱台阶：西侧向 -X 伸出至 x=1.50（x in [1.50, 4.44], y in [13.70, 16.46], Z in [8.96, 9.80] — 位于上盖内顶面 Z=9.10 下方被挡住防脱，Wait: SW300 顶面在 Z=8.80，内顶面在 Z=9.10，若在南侧 y in [12.30, 13.50] 留防脱翼 Z=8.10..8.95，那里既无 SW300 也无 J300，防脱翼厚度可达 0.85 mm！）
    - 下方 45° 楔面推杆：静止位位于 x in [3.54, 4.54]（与 SW300 x=3.38 留 0.16 mm 间隙，与 J300 x=4.71 留 0.17 mm 间隙），并在 J300 南侧无器件区（y in [12.30, 14.00], x in [3.54, 5.60]）加厚脊柱（厚 2.06 mm）及防脱卡台！
    """
    # 1. 穿孔主柱（x: 2.50..4.44, y: 13.70..16.46, z: 8.90..10.40，厚 1.94×2.76×1.50 mm）
    cap = box(2.50, 4.44, 13.70, 16.46, 8.90, 10.40)

    # 2. 45° 楔面工作头与盖下防脱翼：
    # - 穿孔段下方竖杆 stem（x: 3.54..4.44, y: 13.70..16.46, z: 8.22..9.20）：静止位全部位于 x>=3.54（与 SW300 x<=3.38 留 0.16 mm 净空），
    #   下压 0.80 mm 到底时底面停在 Z=7.42（高于主控板顶面 Z=7.41，以主控板面作过压硬限位）
    # - 南侧与东侧盖下防脱翼 south_keeper（x: 3.54..5.54, y: 12.30..14.00, z: 8.22..9.06，厚 0.84 mm ≥ 0.80 mm）：
    #   位于 SW300（x<=3.38）东侧、J300（y>=14.22）南侧的无器件空档，顶面 Z=9.06 与上盖防脱槽顶 Z=9.22 留 0.16 mm 垂向间隙，向南与向东双重卡在上盖孔外防止柱塞向上脱出！
    stem = box(3.54, 4.44, 13.70, 16.46, 8.22, 9.20)
    south_keeper = box(3.54, 5.54, 12.30, 14.00, 8.22, 9.06)

    # 3. 45° 楔面（z=8.90..9.60, x=2.50..3.54）：静止时高于 SW300 顶面（z=8.80，留 0.10 mm 垂向间隙 + 0.16 mm 水平间隙），
    # 下压 Δz=0.80 mm 时 45° 斜面下行进入 z=8.10..8.80，将 SW300 按杆从 x=3.38 推至 x=2.74（水平行程 0.64 mm > 0.50 mm）！
    upper_wedge_pts = [
        (2.50, 9.60),
        (3.54, 9.60),
        (3.54, 8.90),
        (2.84, 8.90),
    ]
    upper_wedge = b.Pos(0, 16.46, 0) * b.extrude(
        b.Plane.XZ * b.Polygon(*upper_wedge_pts, align=None), amount=2.76, dir=(0, -1, 0)
    )

    plunger = (cap + stem + south_keeper + upper_wedge).clean()
    return plunger


def build_spring_bar(y_pos):
    """生成配 22.04 mm 表带的 Ø1.80 快拆弹簧棒参考实体（用于装配预览与爆炸图）。"""
    hw = SPRING_BAR_NOM_LEN / 2.0
    barrel = cyl_x(-hw, hw, y_pos, PIN_Z, SPRING_BAR_BARREL_D)
    tips = cyl_x(-(hw + SPRING_BAR_TIP_LEN), hw + SPRING_BAR_TIP_LEN, y_pos, PIN_Z, SPRING_BAR_TIP_D)
    knob = b.Pos(5.00, y_pos - 0.80, PIN_Z + 0.80) * b.Cylinder(0.45, 2.20)
    return (barrel + tips + knob).clean()


def build_pcb_standoff_std(hx=0.0, hy=0.0):
    """构建 NW / SW / SE 三处标准板间支柱（单实体，高 3.44 mm，位于采集板 D18 顶面 Z=3.35 与主控板 R2 底面 Z=6.79 之间）：
    - 外径 OD = Ø2.50 mm（对齐市售 M1.4×Ø2.5×3.5 mm 圆柱尼龙柱/黄铜柱，孔心距最近铜 ≥ 2.043 mm，且在 SE 角留出 y>-14.50 的 20P FFC 回折空间）
    - 内孔 ID = Ø1.45 mm（适配 M1.4 螺丝）
    """
    return (cyl(hx, hy, 2.50, 3.35, 6.79) - cyl(hx, hy, 1.45, 3.30, 6.85)).clean()


def build_pcb_standoff_ne(hx=19.05, hy=15.75):
    """构建 NE 东北角 (19.05, 15.75) 阶梯防短路绝缘塑料柱（单实体，高 3.44 mm，Z=3.35..6.79）：
    - 下段基座（Z=3.35..5.95，贴 D18 顶面 Ø4.095 净空区）：外径 OD = Ø2.60 mm
    - 上段缩颈（Z=5.95..6.79，贴主控板 R2 底面）：外径缩至 OD = Ø2.00 mm（半径 1.00 mm < R209 距孔心 1.02..1.25 mm 与 C73 距孔心 1.59 mm），
      彻底避让主控板底面 0402 电阻 R209(VBUS) 并对底层 VBUS 走线（距孔心 1.033 mm）保持绝缘！
    - 内孔 ID = Ø1.45 mm（配尼龙 M1.4 螺丝）
    """
    outer = cyl(hx, hy, 2.60, 3.35, 5.95) + cyl(hx, hy, 2.00, 5.95, 6.79)
    return (outer - cyl(hx, hy, 1.45, 3.30, 6.85)).clean()


def build_m14_screw(hx, hy, is_top=True, head_d=2.50):
    """构建 M1.4×2.5 盘头锁紧螺丝参考体（头径 Ø2.50 mm / NE 尼龙头 Ø2.40 mm，头厚 0.80 mm，螺杆 Ø1.40 mm）：
    - 顶面螺丝（is_top=True）：螺帽位于主控板 R2 顶面 Z=7.41..8.21，螺杆向下穿主控板旋入板间柱上段 Z=5.20..7.41
    - 底面螺丝（is_top=False）：螺帽位于采集板 D18 底面下方 Z=1.75..2.55（落入底壳 Ø2.80 沉头定位孔），螺杆向上穿采集板旋入板间柱下段 Z=2.55..4.95
    """
    if is_top:
        return (cyl(hx, hy, head_d, 7.41, 8.21) + cyl(hx, hy, 1.40, 5.20, 7.41)).clean()
    return (cyl(hx, hy, head_d, 1.75, 2.55) + cyl(hx, hy, 1.40, 2.55, 4.95)).clean()


def reference_internals():
    """加载两块 PCB、器件包围盒、J400、电池、20P FFC 回折与 R14 软板参考体，供装配预览与干涉核对。"""
    data = json.loads(BOARDS_JSON.read_text())
    out = []

    # 1. D18 采集板本体（四角同位 (±19.05, ±15.75) Ø1.70 安装孔）
    d17_edges = [
        b.Edge.make_line((*d["start"], 0), (*d["end"], 0))
        if d["kind"] == "line"
        else b.Edge.make_three_point_arc((*d["start"], 0), (*d["mid"], 0), (*d["end"], 0))
        for d in json.loads((P / "d16-outline.json").read_text())
    ]
    d17_plate = b.Pos(0, 0, 2.55) * b.extrude(
        b.Face(b.Wire.combine(d17_edges)[0]), amount=0.80, dir=(0, 0, 1)
    )
    for hx, hy in [(-19.05, 15.75), (19.05, 15.75), (-19.05, -15.75), (19.05, -15.75)]:
        d17_plate -= cyl(hx, hy, 1.70, 2.50, 3.40)
    out.append(("D17_board", d17_plate))

    # 2. 主控板 R2 本体（0.62 mm 厚，Z=6.79..7.41：四角 R4.6 圆角 + 中部 20.90×27.40 电池窗开槽 + 四角 (±19.05, ±15.75) Ø1.70 开孔）
    mcu_in = json.loads((P / "mcu-input.json").read_text())
    outer_2d = b.fillet(b.Rectangle(43.10, 36.50).vertices(), 4.60)
    usb_rect = b.Pos((15.80 + 22.00) / 2, 0) * b.Rectangle(22.00 - 15.80, 4.695 * 2)
    usb_slot_2d = b.fillet([v for v in usb_rect.vertices() if abs(v.X - 15.80) < 0.01], 0.7071)
    bat_slot_2d = b.Pos(-2.55, -2.80) * b.Rectangle(20.90, 27.40)
    mcu_face = outer_2d - usb_slot_2d - bat_slot_2d
    for hx, hy in [(-19.05, 15.75), (19.05, 15.75), (-19.05, -15.75), (19.05, -15.75)]:
        mcu_face -= b.Pos(hx, hy) * b.Circle(1.70 / 2)
    mcu_plate = b.Pos(0, 0, 6.79) * b.extrude(mcu_face, amount=0.62, dir=(0, 0, 1))
    out.append(("MCU_board", mcu_plate))

    # 3. 电池最大公差包络（302025 标称 Z=5.3..8.3，含 3.3 mm 厚度上限包络 Z=5.15..8.45）
    bat = box(-12.56, 7.46, -15.31, 9.71, 5.15, 8.45)
    out.append(("battery_302025_max", bat))

    # 4. J400 USB-C 母座实体（逐个 Solid 施加刚体变换，避免 OCC Compound 布尔忽略顶层 Location）
    u = mcu_in["usb"]
    off = u["models"][0]["offset"]
    usb_raw = b.import_step(P / "GT-USB-7014D.step")
    usb = b.Compound(
        children=[
            s.translate(tuple(off)).rotate(b.Axis.Z, u["angle"]).translate((*u["xy"], 7.40))
            for s in usb_raw.solids()
        ]
    )
    out.append(("MCU_USB_J400", usb))

    # 5. 20P FFC U 形回折区包络（对齐 D18 与主控板 R2 北移后的同位 J_AFE y=-13.67..-9.83：
    # 20P 0.5mm 间距排线实宽 10.50 mm 居中于 x=14.34 即 x: 9.09..19.59, y: -14.48..-13.00, z: 3.40..6.15，
    # 与 SE 角 (19.05, -15.75) Ø2.50 支柱北缘 y=-14.50 及主控底面 R821..R826 零干涉）
    ffc_loop = box(9.09, 19.59, -14.48, -13.00, 3.40, 6.15)
    out.append(("J_AFE_FFC20_loop", ffc_loop))

    # 6. R14/R15 软板关键段包络（盒内段、南出盒 A+B 14.12 mm 段、北侧双尾回折段 y=16.57..18.75、北支段）
    r14_box = box(-13.00, 13.00, -18.50, 18.50, 1.02, 1.22)
    # 出盒以后（南 Y<−20.50、北 Y>20.20）的软板按 R15 真实外形下坡进表带，在 build_r15_strap_fpc 里，这里只到出线槽外沿
    r14_south = box(-5.12, 9.00, SOUTH_FPC_EXIT_Y, -17.00, 1.02, 1.35)
    r14_north_tails = box(-8.77, 8.77, 16.57, 18.75, 1.02, 3.92)
    r14_north_branch = box(-11.05, -9.15, 18.50, NORTH_BRANCH_EXIT_Y, 1.02, 1.38)
    out.extend(
        [
            ("R14_FPC_box", r14_box),
            ("R14_FPC_south_AB", r14_south),
            ("R14_FPC_north_tails", r14_north_tails),
            ("R14_FPC_north_branch", r14_north_branch),
        ]
    )

    # 7. 六颗底部电极触点
    for x in (-8.0, 8.0):
        for y in (-7.5, 7.5):
            c = cyl(x, y, 4.0, 0.0, 0.70) + cyl(x, y, 5.0, 0.70, 0.85) + cyl(x, y, 1.0, 0.85, 1.01)
            out.append((f"contact_{int(x)}_{int(y)}", c))
    for y in (-7.5, 7.5):
        c = cyl(0.0, y, 3.0, 0.0, 0.70) + cyl(0.0, y, 4.0, 0.70, 0.85) + cyl(0.0, y, 1.0, 0.85, 1.01)
        out.append((f"contact_0_{int(y)}", c))

    # 8. 关键顶面器件实体（SW300, J300, D401, U12, U17）
    for ref in ("SW300", "J300", "D401", "U12", "U17", "U14", "U15"):
        for m in data["mcu"]:
            if m["n"] == ref:
                q = box(m["x"][0], m["x"][1], m["y"][0], m["y"][1], m["z"][0], m["z"][1])
                out.append((f"MCU_{ref}", q))
                break

    # 9. J300 1代 U.FL 同轴插头（x=6.21, y=15.78, Z=7.42..9.81 + 向北引出同轴尾管 y=15.78..18.42, Z=8.45..9.35）
    # 与北侧无铜走廊内置 2.4 GHz FPC 贴片天线（20.0 × 4.2 × 0.20 mm，贴于 y=18.42..18.62, x=-10.0..+10.0, Z=4.45..8.65）
    ufl_plug = cyl(6.21, 15.78, 2.70, 7.42, 9.81) + box(5.70, 6.72, 15.78, 18.42, 8.45, 9.35)
    fpc_ant = box(-10.00, 10.00, 18.42, 18.62, 4.45, 8.65)
    out.append(("MCU_J300_UFL_plug", ufl_plug))
    out.append(("FPC_ANT_2G4", fpc_ant))

    # 10. 对齐 IMG_3797.MOV 的南北编织表带回折圆筒套管（Ø3.80 mm 包裹 Ø1.80 mm 快拆弹簧棒）
    out.append(("south_woven_strap_loop", build_woven_strap_loop(SOUTH_PIN_Y, is_north=False)))
    out.append(("north_woven_strap_loop", build_woven_strap_loop(NORTH_PIN_Y, is_north=True)))

    # 11. 两块 PCB 之间的 4 颗同轴板间支柱（塑料柱/铜柱 Z=3.35..6.79）与上下 8 颗 M1.4 锁紧螺丝
    standoff_coords = [
        ("NW", -19.05, 15.75, False),
        ("NE", 19.05, 15.75, True),
        ("SW", -19.05, -15.75, False),
        ("SE", 19.05, -15.75, False),
    ]
    for cname, hx, hy, is_ne in standoff_coords:
        pillar = build_pcb_standoff_ne(hx, hy) if is_ne else build_pcb_standoff_std(hx, hy)
        top_screw = build_m14_screw(hx, hy, is_top=True, head_d=(2.40 if is_ne else 2.50))
        bot_screw = build_m14_screw(hx, hy, is_top=False, head_d=2.50)
        out.append((f"pcb_standoff_{cname}", pillar))
        out.append((f"m14_screw_top_{cname}", top_screw))
        out.append((f"m14_screw_bot_{cname}", bot_screw))

    return out


def export_all():
    parts = {
        "tray": build_tray(),
        "cover": build_cover(),
        "switch_plunger": build_switch_plunger(),
        "pcb_standoff_std": build_pcb_standoff_std(0.0, 0.0),
        "pcb_standoff_ne": build_pcb_standoff_ne(0.0, 0.0),
        "lug_test_22mm": build_lug_test_coupon(),
        "strap_test_coupon_ch5_ch9": build_strap_test_coupon(),
        "strap_keeper": build_strap_keeper(),
        "strap_tongue_test": build_strap_tongue_test(),
        "strap_keeper_gauge_h5p8": build_strap_keeper_gauge(5.80),
        "strap_keeper_gauge_h6p0": build_strap_keeper_gauge(6.00),
        "whole_box_onepiece": build_whole_box_onepiece(),
        "strap_military_green_north": build_military_green_strap_north(),
        "strap_military_green_south": build_military_green_strap_south(),
    }

    manifest = {}
    for name, solid in parts.items():
        solids = solid.solids()
        assert len(solids) == 1, f"{name} 必须为单实体，当前 solids={len(solids)}"
        s1 = solids[0]
        assert s1.is_valid, f"{name} 实体无效"
        step_path = P / f"{name}.step"
        stl_path = P / f"{name}.stl"
        b.export_step(s1, step_path)
        b.export_stl(s1, stl_path)
        bb = s1.bounding_box()
        manifest[name] = {
            "step": step_path.name,
            "stl": stl_path.name,
            "is_valid": bool(s1.is_valid),
            "solid_count": len(solids),
            "volume_mm3": round(float(s1.volume), 3),
            "bbox_min": [round(float(v), 3) for v in bb.min],
            "bbox_max": [round(float(v), 3) for v in bb.max],
            "size_mm": [round(float(v), 3) for v in bb.size],
        }
        print(
            f"[OK] {name:26s} solids={len(solids)} valid={s1.is_valid} vol={s1.volume:8.2f} mm³ size={ [round(v,2) for v in bb.size] }",
            flush=True,
        )

    # 导出整机装配体与爆炸图（仅供预览与 Fusion 查看，不用于 3D 打印下单）
    internals = reference_internals()
    south_bar = build_spring_bar(SOUTH_PIN_Y)
    north_bar = build_spring_bar(NORTH_PIN_Y)

    assy_items = [
        ("tray", parts["tray"], (0.78, 0.86, 0.92, 0.55)),
        ("cover", parts["cover"], (0.82, 0.90, 0.96, 0.45)),
        ("switch_plunger", parts["switch_plunger"], (0.20, 0.65, 0.95, 0.90)),
        ("south_spring_bar", south_bar, (0.75, 0.77, 0.80, 1.0)),
        ("north_spring_bar", north_bar, (0.75, 0.77, 0.80, 1.0)),
    ]
    for n, q in internals:
        col = (0.10, 0.45, 0.25, 1.0) if "board" in n else (0.35, 0.40, 0.45, 1.0)
        if "FPC" in n:
            col = (0.85, 0.45, 0.10, 1.0)
        elif "battery" in n:
            col = (0.35, 0.55, 0.75, 1.0)
        elif "contact" in n:
            col = (0.85, 0.68, 0.20, 1.0)
        elif "woven_strap_loop" in n:
            col = (0.29, 0.35, 0.18, 0.90)
        elif "pcb_standoff_NE" in n:
            col = (0.92, 0.92, 0.88, 1.0)
        elif "pcb_standoff_" in n:
            col = (0.82, 0.65, 0.22, 1.0)
        elif "m14_screw_" in n:
            col = (0.72, 0.75, 0.78, 1.0)
        assy_items.append((n, q, col))

    def save_compound(filename, item_list):
        children = []
        for n, q, col in item_list:
            c = copy.copy(q)
            c.label = n
            c.color = b.Color(*col)
            children.append(c)
        comp = b.Compound(children=children)
        b.export_step(comp, P / f"{filename}.step")
        b.export_gltf(comp, P / f"{filename}.glb", binary=True)

    save_compound("assembly", assy_items)

    # 导出含完整南北军绿色战术表带（14 节电极岛 + 28 颗盒外镀金电极 + R15 软板）的全机总装模型
    strap_elecs, strap_fpc = build_strap_electrodes_and_fpc()
    full_strap_items = [
        it for it in assy_items if "woven_strap_loop" not in it[0]
    ] + [
        ("strap_military_green_north", parts["strap_military_green_north"], (0.29, 0.35, 0.18, 0.96)),
        ("strap_military_green_south", parts["strap_military_green_south"], (0.29, 0.35, 0.18, 0.96)),
        ("strap_electrodes_28", strap_elecs, (0.85, 0.68, 0.20, 1.0)),
        ("R15_FPC_strap_islands", strap_fpc, (0.85, 0.45, 0.10, 1.0)),
    ]
    save_compound("watch_military_green_strap", full_strap_items)

    # 爆炸视图：上盖 +Z 14 mm，柱塞 +Z 22 mm，顶面四颗 M1.4 螺丝 +Z 8 mm，南北编织带圆筒与快拆弹簧棒 ±Y 9 mm
    exploded_offsets = {
        "cover": (0, 0, 14.0),
        "switch_plunger": (0, 0, 22.0),
        "m14_screw_top_NW": (0, 0, 8.0),
        "m14_screw_top_NE": (0, 0, 8.0),
        "m14_screw_top_SW": (0, 0, 8.0),
        "m14_screw_top_SE": (0, 0, 8.0),
        "south_woven_strap_loop": (0, -9.0, 0),
        "south_spring_bar": (0, -9.0, 0),
        "north_woven_strap_loop": (0, 9.0, 0),
        "north_spring_bar": (0, 9.0, 0),
    }
    exploded_items = [
        (n, q.translate(exploded_offsets.get(n, (0, 0, 0))), col)
        for n, q, col in assy_items
    ]
    save_compound("exploded", exploded_items)

    (P / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return parts, manifest


if __name__ == "__main__":
    export_all()
