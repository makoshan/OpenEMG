"""C08B 透明光固化（嘉立创 8001 树脂）外壳 R13（四角缺口抱柱版，方案 3）生成器。R13 与 R12 的唯一结构差别：去掉四角 (±19.05, ±15.75) 穿板圆孔柱 + 板间柱 + 螺丝，改为外壳四角抱进两块 PCB 共有的方缺口。以下为 R12 原说明：
C08B 透明光固化（嘉立创 8001 树脂）外壳 R12 生成器（对齐 IMG_3797.MOV 快拆生耳直连方案）。
输出 3 个单实体 STEP 与 STL（不含 AssemblyHelper 包装，可直接上传嘉立创 3D 打印报价）：
- tray.step / tray.stl：底壳（含南北内凹 C 形半圆柱生耳弧槽 + 两侧 Ø1.20 盲孔、底边圆角、采集板支撑柱、主控角托、R14 软板下层通道与北袋、北无铜走廊 2.4G FPC 天线卡肩）
- cover.step / cover.stl：上盖（总厚抬至 10.1 mm、盖内顶面 Z=9.1 mm、四角 R5.8 与顶边 R3.0 大圆角、顶部开关阶梯孔、J300 1代 U.FL 插头透明微凸窗 Z=10.84；2026-11-10 起四个抱柱底面带定位销，插底壳抱柱顶面的孔，用可拆胶粘，见 COVER_PIN）
- switch_plunger.step / switch_plunger.stl：顶杆，往下按时 45° 斜面把 SW300 侧按杆往西推（2026-11-10 重做，参数见 PLUNGER；带盖下防脱翼；同日加两片导向脚，贴开关本体东面定东西向位置）
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

# Panasonic EVQP7A01P（SW300）：侧按轻触开关，按杆朝 +X，往 -X 推 0.2 mm 导通。
# 手册（EVQP7/P3/9P7，2013-09）：Push Travel 0.2 mm，Operating Force 2.2 N，Push Strength 30 N（1 分钟），
# 按杆伸出本体 0.62±0.1、宽 1.7。
# 几个方块是 2026-11-10 在下单版主控 R4U3N 整板 STEP（嘉立创库模型，不是实物）上量的，整机坐标 [x0, x1, y0, y1, z0, z1]：
# 按杆东上角是尖角，在 (3.307, 8.53)。
# 本体东面是一个平面 x=2.657，y 13.424–16.924、z 7.41–8.35；再往上是 45° 倒角，到 z=8.55 收到 x=2.457。
# 金属盖片 z 8.56–8.76：只有按杆正上方一段凸舌伸过本体东面，东沿 x=2.807、y 14.472–15.876；
# 其余位置盖片东沿在 2.457–2.657 之间（y 13.774–14.124、16.224–16.574 两小段到 2.657，别处 2.457）。
# 方块取法：凸舌东沿取 2.82、南北各多 0.05（多算，对「斜面压到凸舌」偏保守）；盖片其余部分和本体倒角段只取到 2.457
# （少算，对「导向脚靠得住本体」偏保守：只认 z≤8.35 那段平面）。上一版把凸舌当成全宽（y 12.824–16.924），和实物不符，已改。
# 旧版只有一个包围盒（x 到 3.38、z 到 8.80），把按杆上方的空当也算成了实体，核不出顶杆推不推得到按杆。
SW_SPEC = {
    "part_number": "Panasonic EVQP7A01P (EVQ-P7 series)",
    "source": "Panasonic EVQP7/P3/9P7 手册（2013-09）+ 主控 R4U3N 整板 STEP 实测（2026-11-10，嘉立创库模型，非实物）",
    "actuator_direction": "+X (pushed toward -X to actuate)",
    "push_travel_mm": 0.20,
    "operating_force_n": 2.2,
    "push_strength_n": 30.0,
    "body_box": [-0.243, 2.657, 12.824, 16.924, 7.41, 8.35],      # 本体，东面是平面的那段高度
    "body_top_box": [-0.243, 2.457, 12.824, 16.924, 8.35, 8.56],  # 本体顶上的倒角段，只取到倒角顶
    "plate_box": [-0.243, 2.457, 13.424, 16.924, 8.56, 8.76],     # 金属盖片（不含凸舌）
    "cover_lip_box": [2.457, 2.82, 14.42, 15.93, 8.56, 8.76],     # 盖片伸在按杆上方的凸舌
    "knob_box": [2.657, 3.307, 14.324, 16.024, 7.43, 8.53],
    "wedge_angle_deg": 45.0,
    "hole_clearance_mm": 0.20,
}

# 顶杆 switch_plunger 的剖面参数（整机坐标，mm）。按杆东上角 x + z = 3.307 + 8.53 = 11.837。
# 2026-11-10 加导向脚（Mako「先加导向」）：顶杆东西向不再靠盖孔 ±0.20 定位。西边两片导向脚贴开关本体东面 x=2.657，
# 东边帽东面贴盖孔东壁 x=4.64，中间标称只有 0.02 的活动量。标称位置比上一版整体东移 0.19：
# 上一版的标称位置（居中）斜面上端正好悬在盖片凸舌上方，往下按先压到凸舌，短按杆推不够。
PLUNGER = {
    # 45° 斜面 x + z = ramp_s。打印后的调节量：按下去空行程太长就调小；静止时就顶着按杆就调大。
    "ramp_s": 12.14,
    "ramp_tip_x": 3.79,  # 斜面下端，再往下是竖直的杆脚西面。按杆碰斜面的位置够不到杆脚
    "foot_z": 8.22,      # 杆脚、导向脚和防脱翼的底面（沿用旧值）。压到主控板面 7.41 为止，行程上限 0.81（竖直下压；歪 2–4° 时约 0.70）
    # 斜面上端，往上是竖直面（落点）。压到底时按杆被推到这个面：导向脚贴本体时它在 x=2.847，帽贴东壁时 2.87，
    # 下端再歪到贴 J300 设计包围盒（x=4.71）时 2.94。盖片凸舌东沿 2.807（方块取 2.82），竖直面最靠西也在它外面 0.04。
    # 调小：能多推一点，离凸舌更近；调大：离凸舌远，最大推量等量减少。比导向脚西面（x[0]）靠东 0.19，这个差是关键尺寸：
    # 小于 0.15（方块口径 0.163）斜面上端就会悬到凸舌上方。
    "land_x": 2.86,
    "relief_z": 9.75,    # 帽西半边的底面，抬高让开开关金属盖片（顶 8.76）
    # 帽顶。按到导通最深要压 0.69（短按杆、没盖上盖时整体东移到贴 J300 的平移姿态，自检拿它当最坏情况），那时帽顶 10.91，还不低于东侧天线鼓包 10.84，手指平着按得到；
    # 压到底（0.81）是 10.79。静止时比鼓包高 0.76、比西侧盖面高 1.50。嫌凸就调小，低于 11.58 自检的帽顶门不过
    # （门留 0.05 给歪斜：不带天线插头歪到 18° 时帽顶中心再矮 0.03，复核算）。
    "top_z": 11.60,
    # 帽和杆的东西范围。x[0] 同时是导向脚西面：离本体东面 0.013。x[1] 是帽和杆的东面：离盖孔东壁 0.01。
    # 顶杆夹在开关本体东面和盖孔东壁之间，标称活动量只有 0.023：上盖相对主控板偏西 0.023 以上就放不进（复核量），
    # 首件偏紧（放不进或按下去发涩）就磨帽东面，不许硬合盖。杆脚东面别往东加：离 J300 接地脚（西沿 4.65）只有 0.02。
    "x": (2.67, 4.63),
    # 首件偏松时用：只把帽东面（盖内顶面以上那段）往东加厚这么多，杆脚东面不动。上盖偏东时活动量变大、东侧推量变小，
    # 磨不回来，只能换厚一档的顶杆（复核建议同批多打 0.05、0.10 两档）。标称件是 0。
    "cap_east_extra": 0.0,
    "y": (13.27, 17.07),  # 比上一版南端长 0.43、北端长 0.61：两片导向脚各厚 0.80（嘉立创「薄处不低于 0.8」）
    "keeper": (5.73, 11.87, 14.00, 9.06),  # 盖下防脱翼：东沿 x、y0、y1、顶 z；西沿和底面跟杆脚齐
    # 导向脚：杆脚南北两头各一片，把斜面槽夹在中间，西面和帽西面齐平（x[0]），从杆脚底一直连到帽底。
    # 这两个数是两片的内侧面：南片 y[0]–14.07，北片 16.27–y[1]，各厚 0.80，离按杆侧面（14.324 / 16.024）各 0.25。设成 None 不出导向脚（只给反例用）。
    "guide_y": (14.07, 16.27),
    # 导向脚底部西侧的 45° 倒角。合盖时顶杆可能偏西最多 0.20（盖孔西侧间隙），倒角把它导到本体东面外侧，不会搁在盖片上。
    # 代价：导向脚直面从 foot_z + 0.25 = 8.47 才开始，下压 0.12 以后才贴上本体平面（顶 8.35）；
    # 按嘉立创模型，在那之前直面先贴盖片南北两小段东沿（也是 2.657），方块口径没算这两段。
    "guide_lead": 0.25,
}
# 盖孔 [x0, x1, y0, y1]：西、南、北各留 0.20（喷油间隙）。东壁 4.64 没动：它是受力时顶杆靠的面，也挡着杆脚不落到 J300 接地脚（x=4.65）上。
PLUNGER_HOLE = (round(PLUNGER["x"][0] - SW_SPEC["hole_clearance_mm"], 4), 4.64,
                round(PLUNGER["y"][0] - SW_SPEC["hole_clearance_mm"], 4), round(PLUNGER["y"][1] + SW_SPEC["hole_clearance_mm"], 4))


def sw300_parts(push=0.0):
    """SW300 参考体，拆成 (不动的本体和盖片, 按杆)。push 是按杆被往西推进去的量。"""
    k = SW_SPEC["knob_box"]
    fixed = box(*SW_SPEC["body_box"]) + box(*SW_SPEC["body_top_box"]) + box(*SW_SPEC["plate_box"]) + box(*SW_SPEC["cover_lip_box"])
    return fixed, box(k[0], k[1] - push, *k[2:])


# ---------------------------------------------------------------------------
# R13 四角缺口抱柱（方案 3）：主控板 R3 与采集板 D19 共用同一组四角方缺口
# 坐标 = 板中心坐标，+Y 向北。缺口：NW/NE/SW 3.0×3.0 mm，SE 3.0×2.6 mm（深度指 Y 向）。
# 抱柱放在缺口里，两条内面各留 POST_GAP 间隙贴着板的缺口直边，锁 X/Y；
# 朝向板内拐角的那条竖棱倒 R1.2：嘉立创铣刀在板的 90° 内拐角会留 R0.8–1.0 的圆角，抱柱棱角 R1.2 > 残留 R1.0，不会顶在圆角死角上。
# ---------------------------------------------------------------------------
BOARD_HX = 21.55              # 两块板外包络半宽 X
BOARD_HY = 18.25              # 两块板外包络半长 Y
NOTCH_X = 18.55               # 缺口内面 |x|（缺口宽 3.00）
CORNERS = {"NW": (-1, +1, 3.0), "NE": (+1, +1, 3.0), "SW": (-1, -1, 3.0), "SE": (+1, -1, 2.6)}
POST_GAP = 0.10               # 抱柱与板缺口直边的单边装配间隙
POST_FILLET_R = 1.20          # 抱柱内棱圆角（避开铣刀残留 R1.0）
MILL_RESIDUAL_R = 1.00        # 嘉立创锣刀在内直角处残留的最大圆角（Ø2.0 铣刀）
LIP_UNDER = 0.80              # 采集板下托台向板内伸出量（托住 D19 底面）
LIP_TOP = 0.50                # 上盖压台向板内伸出量（压住主控板顶面；0.60 会碰到原稿位置的 C61，故取 0.50）
D19_Z = (2.55, 3.35)          # 采集板 D19 底/顶面 Z
MCU_Z = (6.79, 7.41)          # 主控板 R3 底/顶面 Z
UNDER_LIP_Z = (0.95, 2.55)    # 下托台 Z（顶面贴 D19 底面 2.55）
TOP_LIP_Z0 = 7.45             # 上压台底面 Z（主控板顶面 7.41 上留 0.04）
# 上盖对底壳的定位和固定（2026-11-10，Mako「按推荐改」）。之前上盖和底壳在分模面平对平，没有螺丝、卡扣、止口：
# 上盖只靠自己的抱柱卡在主控板缺口上，而主控板在底壳里前后左右没有定位（底壳抱柱只到分模面，够不着主控板）。
# 现在上盖四个抱柱底面各长一根短销，插进底壳抱柱顶面的孔，上盖对底壳才有定位；底壳抱柱顶面下沉一层留给胶，
# 上盖靠可拆胶粘在这四个面上。往上拔只有胶，没有机械限位。螺丝头和卡扣在现有外形里放不下（量过，见证据目录）。
# 合盖顺序（复核指出，第一版销长 1.50 会卡）：上盖抱柱底面离合上还差 0.65 时碰到主控板顶面，要让抱柱先进板缺口、
# 把板带住，销再进孔，所以销只有 0.45 长。销先进孔的话上盖被底壳钉住，只能去挪板，抱柱底面是平的，会压在板角上。
COVER_PIN = {
    # 销的圆心：抱柱里离各面最远的点（东南角缺口浅，位置不同）
    "xy": {"NW": (-20.30, 17.00), "NE": (20.30, 17.00), "SW": (-20.30, -17.00), "SE": (20.20, -17.30)},
    # 对角这两根定位；另外两根的孔放大，只防呆不定位。四根都精配的话，两个件的孔距打印误差（40 mm 上约 0.1）会别住
    "tight": ("NW", "SE"),
    "pin_d": 1.10,          # 上盖销直径
    "pin_len": 0.45,        # 销伸到分模面以下多长。必须比 0.65 短出一截（见上），自检有门
    "pin_tip": 0.10,        # 销头倒角，合盖时导入
    "socket_d": 1.30,       # 定位孔直径，单边 0.10。打印出来偏紧就用 Ø1.3 钻头过一下
    "socket_d_loose": 1.50, # 另两个孔的直径，单边 0.20
    "socket_depth": 0.65,   # 孔深，比销长 0.20，销不会先顶到孔底
    # 底壳抱柱顶面下沉量 = 胶层厚度；上盖仍然坐在一圈壁顶上，胶不垫高上盖。销的直段在胶层以下还吃上孔壁 0.25
    # （0.45 − 头部倒角 0.10 − 胶层 0.10）。孔口不设挡胶的台：试过留一圈 0.25 宽的台，低于「薄处不低于 0.8」，复核指出后去掉了，
    # 点胶时别点在孔边。
    "glue_gap": 0.10,
}
# 撬口：上盖西壁外侧、分模缝处的浅槽 [x0, x1, y0, y1, z0, z1]，拆盖时插撬片。深 0.35，剩壁 0.85
PRY_NOTCH = (-23.00, -22.65, -1.50, 1.50, SPLIT_Z, SPLIT_Z + 0.50)


def notch_outline():
    """两块板共用的板框折线（缺口方角，与 11.7(1).epro 的 POLY e971 同形）。"""
    hx, hy, nx = BOARD_HX, BOARD_HY, NOTCH_X
    return [
        (-nx, hy), (nx, hy), (nx, hy - 3.0), (hx, hy - 3.0), (hx, -(hy - 2.6)), (nx, -(hy - 2.6)),
        (nx, -hy), (-nx, -hy), (-nx, -(hy - 3.0)), (-hx, -(hy - 3.0)), (-hx, hy - 3.0), (-nx, hy - 3.0),
    ]


def _mirror_to_corner(shape, sx, sy):
    if sx < 0:
        shape = b.mirror(shape, about=b.Plane.YZ)
    if sy < 0:
        shape = b.mirror(shape, about=b.Plane.XZ)
    return shape


def corner_post(name, z0, z1, gap=POST_GAP, fillet_r=POST_FILLET_R, lip=0.0, clip=True):
    """四角缺口抱柱（|x|,|y| 象限里建，再镜像到对应角）。lip>0 时做向板内伸出的托台/压台（不倒圆）。
    clip=True：只保留盒内 + 壁里 0.3 mm 的部分，不会凸出外壁。"""
    sx, sy, depth = CORNERS[name]
    ix = NOTCH_X + gap - lip
    iy = (BOARD_HY - depth) + gap - lip
    ox, oy = 21.95, 18.95
    face = b.Pos((ix + ox) / 2, (iy + oy) / 2) * b.Rectangle(ox - ix, oy - iy)
    if lip == 0.0 and fillet_r > 0:
        vs = [v for v in face.vertices() if abs(v.X - ix) < 1e-6 and abs(v.Y - iy) < 1e-6]
        face = b.fillet(vs, fillet_r)
    solid = b.Pos(0, 0, z0) * b.extrude(face, amount=z1 - z0, dir=(0, 0, 1))
    solid = _mirror_to_corner(solid, sx, sy)
    if clip:
        solid = solid & rounded_prism(INNER_W + 0.6, INNER_L + 0.6, z0, z1, INNER_CORNER_R + 0.3)
    return solid


def post_inside_cavity(name, z0, z1):
    """抱柱落在内腔里的那部分（不含 corner_post 伸进壁里的 0.3）"""
    return corner_post(name, z0, z1, clip=False) & rounded_prism(INNER_W, INNER_L, z0, z1, INNER_CORNER_R)


def mill_residual(name, z0, z1, r=MILL_RESIDUAL_R):
    """铣刀在板缺口内拐角残留的圆角材料（板的一部分）：贴在内拐角、边长 r 的方块减去 r 圆。"""
    sx, sy, depth = CORNERS[name]
    y0 = BOARD_HY - depth
    sq = b.Pos(NOTCH_X + r / 2, y0 + r / 2) * b.Rectangle(r, r)
    sq = sq - b.Pos(NOTCH_X + r, y0 + r) * b.Circle(r)
    solid = b.Pos(0, 0, z0) * b.extrude(sq, amount=z1 - z0, dir=(0, 0, 1))
    return _mirror_to_corner(solid, sx, sy)


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
    seam_features=True,
    pin_override=None,
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
    # 南侧内壁局部加厚至 y=-18.40（距 PCB 南边 y=-18.25 留 0.15 mm 净空，确保南生耳内凹弧槽 y=-19.25 内壁实厚 0.85 mm ≥ 0.80 mm）
    s += box(-11.80, 11.80, -18.85, -18.40, 1.40, SPLIT_Z)   # Z 从 1.40 起，避让底槽 Z<=1.22 软板（同 R12 cc1a4fffd）

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

    # R13 四角缺口抱柱（替代 R12 的 (±19.05, ±15.75) Ø4.50 圆孔支撑柱）：
    # - 全高抱柱 Z=0.95..SPLIT_Z 放进两块板共有的四角缺口，两条内面各留 0.10 mm，锁 X/Y；
    # - 采集板下托台 Z=0.95..2.55，向板内伸 0.80 mm，顶面托住 D19 底面 Z=2.55（锁 D19 向下）。
    for cname in CORNERS:
        s += corner_post(cname, UNDER_LIP_Z[0], SPLIT_Z)
        s += corner_post(cname, UNDER_LIP_Z[0], UNDER_LIP_Z[1], lip=LIP_UNDER)
    # SE 缺口只有 2.6 深，两块板在 (21.55, -15.65) 的凸角正好落在内腔 R4.6 圆弧上（零间隙）；
    # 在该点的壁上开 Ø0.60 避空孔（深入壁 0.30，剩壁 ≥0.90），只切 D19 板厚范围 Z=2.55..3.50
    s -= cyl(BOARD_HX, -(BOARD_HY - 2.6), 0.60, UNDER_LIP_Z[1], 3.50)
    if seam_features:
        # 上盖定位销的孔和胶层（见 COVER_PIN）：抱柱顶面下沉 glue_gap，孔从分模面往下 socket_depth。
        # seam_features=False 只给整盒一体件和反例用；pin_override 只给反例用。
        cp = {**COVER_PIN, **(pin_override or {})}
        for cname, (px, py) in cp["xy"].items():
            d = cp["socket_d"] if cname in cp["tight"] else cp["socket_d_loose"]
            s -= corner_post(cname, SPLIT_Z - cp["glue_gap"], SPLIT_Z + 0.02)
            s -= cyl(px, py, d, SPLIT_Z - cp["socket_depth"], SPLIT_Z + 0.02)

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
    seam_features=True,
    pin_override=None,
    pin_corners=None,
):
    """构建上盖 cover（单实体）：
    - 外轮廓 46×40 R5.8，Z=6.60..total_height（默认 10.10 mm）
    - 顶面四周大圆角 R3.0，内腔顶面四周内圆角 R1.8，顶壁基准厚 1.00 mm（内顶面 Z = total_height - 1.00 = 9.10 mm）
    - 针对嘉立创库 3D 中偏高的两颗 SOT-23-6（U12、U17，模型顶 Z=9.10，真实规格书 8.86）设 0.16 mm 浅让位槽（Z=9.26，剩顶壁 0.84 mm ≥ 0.80 mm）
    - J300（U.FL-R-SMT-1，中心 6.21, 15.78）上方设 1代 U.FL 同轴插头微凸透明观察窗（内顶 Z=9.98，外顶 Z=10.84，顶壁厚 0.86 mm ≥ 0.80 mm）与北向同轴引线槽（x: 5.40..7.00, y: 17.00..18.80, Z=7.20..9.68）
    - 顶部 SW300 顶杆孔（范围见 PLUNGER_HOLE：西、南、北与帽留 0.20 mm，兼容 8001 全透明喷油；东壁是顶杆受力时靠的面，标称只留 0.01）
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
        s -= box(3.40, 5.95, 11.72, 14.15, inner_z - 0.20, inner_z + 0.12)  # 防脱翼上方浅槽；东沿随防脱翼东移（原 5.70）
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

    # 顶部 SW300 顶杆孔（Z=8.60..total_height+1.0），范围见 PLUNGER_HOLE：西、南、北离帽 0.20，东壁离帽 0.01
    s -= box(*PLUNGER_HOLE, inner_z - 0.50, total_height + 1.00)

    # 西侧与东南侧无器件边缘压紧凸台（Z=7.58..inner_z，配合四角 M1.4 螺丝+板间柱辅助限位主控板；
    # 四角 (±19.05, ±15.75) 上方留出完整内顶净空 Z=8.88..9.10 mm 容纳 M1.4 螺丝头 Z=7.41..8.21 mm）
    s += box(-21.90, -20.75, -14.20, -10.20, 7.58, inner_z) & domed_prism(
        INNER_W + 0.20, INNER_L + 0.20, SPLIT_Z, inner_z, INNER_CORNER_R, top_inner_r
    )
    s += box(20.75, 21.90, -13.00, -7.50, 7.58, inner_z) & domed_prism(
        INNER_W + 0.20, INNER_L + 0.20, SPLIT_Z, inner_z, INNER_CORNER_R, top_inner_r
    )

    # R13 四角缺口抱柱延续到上盖：Z=SPLIT_Z..盖内顶面，与底壳抱柱同一截面连成整根；
    # 上压台 Z=7.45..盖内顶面，向板内伸 0.60 mm，压住主控板顶面 Z=7.41（锁主控板向上）。
    for cname in CORNERS:
        s += corner_post(cname, SPLIT_Z, inner_z)
        s += corner_post(cname, TOP_LIP_Z0, inner_z, lip=LIP_TOP)
    # 同上：SE 凸角避空，切主控板板厚范围 Z=6.76..7.60
    s -= cyl(BOARD_HX, -(BOARD_HY - 2.6), 0.60, SPLIT_Z - 0.06, 7.60)
    if seam_features:
        # 四根定位销（见 COVER_PIN）：从抱柱底面往下伸 pin_len，头部倒角；再在西壁分模缝处开撬口。
        # pin_override、pin_corners（只出这几个角的销）只给反例用。
        cp = {**COVER_PIN, **(pin_override or {})}
        for cname, (px, py) in cp["xy"].items():
            if pin_corners is not None and cname not in pin_corners:
                continue
            z_tip, t, r = SPLIT_Z - cp["pin_len"], cp["pin_tip"], cp["pin_d"] / 2
            s += cyl(px, py, 2 * r, z_tip + t, SPLIT_Z + 0.30)
            s += b.Pos(px, py, z_tip) * b.Cone(r - t, r, t, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
        s -= box(*PRY_NOTCH)

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


def build_whole_box_onepiece():
    """构建整盒一体打印单实体 whole_box_onepiece（1 solid）：
    将底壳 tray、上盖 cover 与顶面按钮帽融合成 1 个无缝单实体（46.00 × 45.75 × 11.45 mm，高度量到按钮帽顶，天线鼓包顶是 10.69，较旧版 51.60 mm 缩短 5.85 mm），
    用于一次性直接打印整只表盘外观手板，直接扣入南北两端 22.04 mm 快拆表带试戴看整体效果。
    内部与外界通过东侧 USB-C 窗口、南北下层软板槽、底部 6 个电极孔完全贯通，无封闭死腔（兼容 FDM 与光固化）。
    """
    tray = build_tray(seam_features=False)     # 一体件不要销、孔、胶层和撬口：融成一个实体后会变成封闭空腔
    cover = build_cover(seam_features=False)
    seam_ring = rounded_prism(
        BODY_W, BODY_L, SPLIT_Z - 0.16, SPLIT_Z + 0.10, OUTER_CORNER_R
    ) - rounded_prism(
        INNER_W, INNER_L, SPLIT_Z - 0.20, SPLIT_Z + 0.15, INNER_CORNER_R
    )
    seam_ring -= box(20.70, 23.50, -6.50, 6.50, SPLIT_Z - 0.25, SPLIT_Z + 0.20)
    hx0, hx1, hy0, hy1 = PLUNGER_HOLE
    button_cap_solid = box(hx0 - 0.05, hx1 + 0.05, hy0 - 0.05, hy1 + 0.05, 9.00, PLUNGER["top_z"])  # 把盖孔填实
    whole = (tray + cover + seam_ring + button_cap_solid).clean()
    return whole


def build_switch_plunger(**override):
    """顶杆 switch_plunger（单实体）：手指往下按，45° 斜面把 SW300 按杆往西推。
    XZ 剖面沿 Y 拉伸：帽顶 → 东侧直杆 → 杆脚 → 45° 斜面 → 竖直面 → 抬高的帽西底面；南侧再并一片盖下防脱翼。
    杆脚南北两头各并一片导向脚（2026-11-10 加）：西面贴开关本体东面，顶杆往西挪不动，斜面上端到不了盖片凸舌上方。
    旧版（R12、R13 到 2026-11-09）的斜面整个包在帽的方块里，并集后没有斜面，帽底先压到开关盖片，按杆推 0。
    参数见 PLUNGER；override 只给检查脚本做反例和扫公差用。
    """
    p = {**PLUNGER, **override}
    (x0, x1), (y0, y1), s, z_bot = p["x"], p["y"], p["ramp_s"], p["foot_z"]
    assert z_bot < s - p["ramp_tip_x"] < s - p["land_x"] < p["relief_z"] < p["top_z"], "顶杆剖面参数顺序不对"
    assert x0 <= p["land_x"] < p["ramp_tip_x"] < x1, "顶杆剖面 x 顺序不对"

    def prism(pts, ya, yb):  # XZ 剖面从 ya 拉到 yb
        return b.Pos(0, yb, 0) * b.extrude(b.Plane.XZ * b.Polygon(*pts, align=None), amount=yb - ya, dir=(0, -1, 0))

    body = prism([
        (x0, p["top_z"]),
        (x1, p["top_z"]),
        (x1, z_bot),
        (p["ramp_tip_x"], z_bot),
        (p["ramp_tip_x"], s - p["ramp_tip_x"]),
        (p["land_x"], s - p["land_x"]),
        (p["land_x"], p["relief_z"]),
        (x0, p["relief_z"]),
    ], y0, y1)
    if p["guide_y"] is not None:
        (gy0, gy1), lead = p["guide_y"], p["guide_lead"]
        assert y0 < gy0 < gy1 < y1 and x0 + lead < p["ramp_tip_x"] and z_bot + lead < p["relief_z"], "导向脚参数不对"
        foot = [(x0, z_bot + lead), (x0 + lead, z_bot), (p["ramp_tip_x"], z_bot), (p["ramp_tip_x"], p["relief_z"]), (x0, p["relief_z"])]
        body = body + prism(foot, y0, gy0) + prism(foot, gy1, y1)
    if p["cap_east_extra"] > 0:   # 帽东面加厚：从防脱翼浅槽顶（盖内顶面 + 0.12）再高 0.03 起，到帽顶
        body = body + box(x1, x1 + p["cap_east_extra"], y0, y1, COVER_INNER_Z + 0.15, p["top_z"])
    kx1, ky0, ky1, kz1 = p["keeper"]
    return (body + box(p["ramp_tip_x"], kx1, ky0, ky1, z_bot, kz1)).clean()


def build_spring_bar(y_pos):
    """生成配 22.04 mm 表带的 Ø1.80 快拆弹簧棒参考实体（用于装配预览与爆炸图）。"""
    hw = SPRING_BAR_NOM_LEN / 2.0
    barrel = cyl_x(-hw, hw, y_pos, PIN_Z, SPRING_BAR_BARREL_D)
    tips = cyl_x(-(hw + SPRING_BAR_TIP_LEN), hw + SPRING_BAR_TIP_LEN, y_pos, PIN_Z, SPRING_BAR_TIP_D)
    knob = b.Pos(5.00, y_pos - 0.80, PIN_Z + 0.80) * b.Cylinder(0.45, 2.20)
    return (barrel + tips + knob).clean()


def reference_internals():
    """加载两块 PCB、器件包围盒、J400、电池、20P FFC 回折与 R14 软板参考体，供装配预览与干涉核对。"""
    data = json.loads(BOARDS_JSON.read_text())
    out = []

    # 1. 采集板 D19 本体（四角缺口方外形，0.80 mm 厚，Z=2.55..3.35，无安装孔）
    d19_plate = b.Pos(0, 0, D19_Z[0]) * b.extrude(b.Polygon(*notch_outline(), align=None), amount=D19_Z[1] - D19_Z[0], dir=(0, 0, 1))
    out.append(("D17_board", d19_plate))   # 键名沿用 R12，检查脚本按这个名字找

    # 2. 主控板 R3 本体（0.62 mm 厚，Z=6.79..7.41：四角缺口方外形 + 东侧 USB 缺槽 + 中部 20.90×27.40 电池窗；无安装孔）
    mcu_in = json.loads((P / "mcu-input.json").read_text())
    outer_2d = b.Polygon(*notch_outline(), align=None)
    usb_rect = b.Pos((15.80 + 22.00) / 2, 0) * b.Rectangle(22.00 - 15.80, 4.695 * 2)
    usb_slot_2d = b.fillet([v for v in usb_rect.vertices() if abs(v.X - 15.80) < 0.01], 0.7071)
    bat_slot_2d = b.Pos(-2.55, -2.80) * b.Rectangle(20.90, 27.40)
    mcu_face = outer_2d - usb_slot_2d - bat_slot_2d
    mcu_plate = b.Pos(0, 0, MCU_Z[0]) * b.extrude(mcu_face, amount=MCU_Z[1] - MCU_Z[0], dir=(0, 0, 1))
    out.append(("MCU_board", mcu_plate))

    # 3. 电池最大公差包络（302025 标称 Z=5.3..8.3，含 3.3 mm 厚度上限包络 Z=5.15..8.45）
    bat = box(-12.56, 7.46, -15.31, 9.71, 5.15, 8.45)
    out.append(("battery_302025_max", bat))

    # 4. J400 USB-C 母座实体（逐个 Solid 施加刚体变换，避免 OCC Compound 布尔忽略顶层 Location）
    u = mcu_in["usb"]
    off = u["models"][0]["offset"]
    usb_step_path = P / "GT-USB-7014D.step"
    if not usb_step_path.exists():
        usb_step_path = P.parent / "c08b-shell-r12" / "GT-USB-7014D.step"
    usb_raw = b.import_step(usb_step_path)
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
                if ref == "SW300":  # 包围盒把按杆上方的空当算成实体，顶杆斜面要对着真实外形核
                    q = sum(sw300_parts(), b.Part())
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

    # 11. R13 无板间柱、无螺丝：四角抱柱已并入 tray / cover。

    return out


def export_all():
    parts = {
        "tray": build_tray(),
        "cover": build_cover(),
        "switch_plunger": build_switch_plunger(),
        "lug_test_22mm": build_lug_test_coupon(),
        "whole_box_onepiece": build_whole_box_onepiece(),
        "strap_military_green_north": build_military_green_strap_north(),
        "strap_military_green_south": build_military_green_strap_south(),
        "strap_keeper": build_strap_keeper(),
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
