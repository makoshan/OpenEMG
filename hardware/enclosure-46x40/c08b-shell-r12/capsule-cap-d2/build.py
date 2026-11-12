"""C08B 胶囊底盖 D2 外扣版（2026-11-11 Mako：「第一个盖子是扣在表盘之外的」→「可以」）。
胶囊段 FPC 不进 R13 底壳，整段贴在底壳外底下面；外面扣一个平底盖（和表带 TPU 开孔层同构，0.8 厚），两条长边裙边包住底壳侧面扣进卡槽，两端敞开过表带。
铜片焊在 FPC 焊盘上从底盖孔穿出：CH1 / CH2 Φ6 × 2.0（同表带），BIAS / REF 方形 3 × 3 × 2.0（11-11 购物车定：Φ4 × 2 买不到，叠焊的 4×2×0.8 已删）。
坐标沿用 R13 壳（不改换算）：X 横跨（46 宽，同一路 P/N 沿 X），Y 沿表带（北 +），Z 朝表带（Z = 0 是旧触点尖端）。
叠层：底壳外底 Z 0.15 → B 片（若在此处）→ A 片 → 底盖顶面 Z −0.256（A 片 F 面压在底盖上）→ 底盖底面 Z −1.056。
底壳：R13 原有 6 个触点孔填平；两条长边外壁开卡槽；北端开一道尾巴缝（位置读 FPC geometry.json 的 tray_tail_slot）。
标「假设」的等实物量了改常量，重跑 build.py → check.py → slice.sh。"""
from pathlib import Path
import json
import build123d as b
import importlib.util

HERE = Path(__file__).resolve().parent
R13_DIR = HERE.parents[1] / "c08b-shell-r13-notch"
_spec = importlib.util.spec_from_file_location("r13_shell", R13_DIR / "build.py")   # 本文件也叫 build.py，按路径加载防撞名
r13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r13)

# ---- 触点（以 FPC 的 geometry.json capsule_pads 为准，check.py 会对一遍） ----
BIG = {"E1N": (-8.0, 7.5), "E1P": (8.0, 7.5), "E2N": (-8.0, -7.5), "E2P": (8.0, -7.5)}
AUX = {"EB1": (0.0, -7.5), "EB2": (0.0, 7.5)}   # 以 FPC capsule_pads 为准（都在 A 片 F 面；EB2 经金属化孔对焊 B 片）
PADS = {**BIG, **AUX}
BIG_D, BIG_T = 6.0, 2.0
AUX_D, AUX_T = 3.0, 2.0               # 方形 3×3×2：AUX_D 是边长（孔、碰撞都按方块算）
HOLE_CLEAR = 0.5                       # 孔 = 铜片 + 0.5（先焊铜片再扣盖）
FPC_T = 0.203                          # 四层 FPC 板厚
FPC_BOT_Z = r13.TRAY_Z_MIN - 2 * FPC_T  # A 片 F 面 = 底盖顶面 Z −0.256（底壳外底下面留 A + B 两片的厚度）
TRAY_BOT = r13.TRAY_Z_MIN              # 底壳外底 Z 0.15
B_OVER_A = 0.0                         # 11-12 Mako「REF 挪到 A 片」：EB2 贴肤焊盘改在 A 片（金属化孔对焊 B 片），6 片同高（FPC geometry.json stack_note）
BASE_Z = {"EB2": FPC_BOT_Z + B_OVER_A}

# ---- 底盖 ----
FACE_T = 0.80                          # 底盖正面厚（同表带 TPU 层）
BODY_HX, BODY_HY, BODY_R = r13.BODY_W / 2, r13.BODY_L / 2, r13.OUTER_CORNER_R
SKIRT_T = 0.80                         # 裙边厚
SKIRT_TOP = 1.30                       # 裙边顶 Z
SKIRT_HY = BODY_HY - BODY_R - 0.3      # 裙边只在长边直段（|y| ≤ 13.9），圆角和两端不包
GROOVE = (0.45, 0.85, 0.30)            # 底壳外壁卡槽 Z0、Z1、深
BEAD = 0.25                            # 裙边内凸棱（比槽浅 0.05）
MIN_WALL = 0.80


def face_z0():
    return FPC_BOT_Z - FACE_T


FPC_GEOM = HERE.parents[2] / "16ch-c08b-round/strap-fpc-d2/geometry.json"


def fpc_geom():
    try:
        return json.loads(FPC_GEOM.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def tail_slot():
    """FPC 尾巴穿底壳的缝（盒坐标 box{x0,x1,y0,y1}），没有就返回 None。"""
    return fpc_geom().get("tray_tail_slot")


def hole_d(ref):
    return (BIG_D if ref in BIG else AUX_D) + HOLE_CLEAR


def disc_t(ref):
    return BIG_T if ref in BIG else AUX_T


def base_z(ref):
    return BASE_Z.get(ref, FPC_BOT_Z)


def tip_z(ref):
    return base_z(ref) - disc_t(ref)


def rrect(hx, hy, z0, z1, r):
    return b.Pos(0, 0, z0) * b.extrude(b.RectangleRounded(2 * hx, 2 * hy, r), amount=z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    return b.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * b.Box(x1 - x0, y1 - y0, z1 - z0)


def build_tray_d2():
    t = r13.build_tray()
    for (x, y) in list(BIG.values()) + list(AUX.values()):   # 填平 R13 原 6 个触点孔（含沉台），到 FPC 槽底 Z 1.00
        t += b.Pos(x, y, (TRAY_BOT + 1.0) / 2) * b.Cylinder(5.4 / 2, 1.0 - TRAY_BOT)
    g0, g1, gd = GROOVE
    for sx in (-1, 1):   # 两条长边外壁卡槽
        x0, x1 = sorted((sx * (BODY_HX + 0.1), sx * (BODY_HX - gd)))
        t -= box(x0, x1, -SKIRT_HY - 0.5, SKIRT_HY + 0.5, g0, g1)
    g = fpc_geom()
    ts = g.get("tray_tail_slot")
    if ts:   # 尾巴缝：穿底板（FPC 给的盒坐标），北回折槽北壁退到尾巴需要的位置
        bx = ts["box"]
        t -= box(bx["x0"], bx["x1"], bx["y0"], bx["y1"], TRAY_BOT - 0.1, ts["z_through"][1] + 0.01)
        t -= box(-9.60, 9.60, 18.70, ts["north_pocket_y_max_needed"] + 0.05, 1.00, 4.10)   # R13 回折槽 x ±9.6、Z 1.00–4.10
    for r in g.get("capsule_res_pockets", {}).get("rects", []):   # FPC 背面串阻：底壳外底挖浅槽
        bx = r["box"]
        t -= box(bx["x0"], bx["x1"], bx["y0"], bx["y1"], TRAY_BOT - 0.1, r["pocket_z"][1])
    return t.clean()


def build_cap():
    z0 = face_z0()
    s = rrect(BODY_HX, BODY_HY, z0, FPC_BOT_Z, BODY_R)                     # 平底盖正面，和胶囊底一样大
    g0, g1, gd = GROOVE
    for sx in (-1, 1):
        x0, x1 = sorted((sx * BODY_HX, sx * (BODY_HX + SKIRT_T)))
        s += box(x0, x1, -SKIRT_HY, SKIRT_HY, z0, SKIRT_TOP)               # 裙边：从底盖往上包到底壳侧面
        bx0, bx1 = sorted((sx * BODY_HX + sx * 0.01, sx * (BODY_HX - BEAD)))
        s += box(bx0, bx1, -SKIRT_HY, SKIRT_HY, g0 + 0.05, g1 - 0.05)       # 内凸棱
    for ref, (x, y) in PADS.items():
        h = FPC_BOT_Z - z0 + 0.2
        s -= b.Pos(x, y, (z0 + FPC_BOT_Z) / 2) * (b.Cylinder(hole_d(ref) / 2, h) if ref in BIG else b.Box(hole_d(ref), hole_d(ref), h))   # 辅点方孔
    return s.clean()


def summary():
    z0 = face_z0()
    big = {k: round(z0 - tip_z(k), 3) for k in BIG}
    aux = {k: round(z0 - tip_z(k), 3) for k in AUX}
    hole_gap = min(abs(PADS[a][0] - PADS[c][0]) - (hole_d(a) + hole_d(c)) / 2
                   for a in PADS for c in PADS if a != c and PADS[a][1] == PADS[c][1])
    low = min(tip_z(k) for k in PADS)
    return {"face_z0": round(z0, 3), "proud_big": big, "proud_aux": aux, "lowest_z": round(low, 3),
            "total_height_new": round(r13.TOTAL_HEIGHT - low, 3), "total_height_r13": r13.TOTAL_HEIGHT,
            "width_with_skirt": round(2 * (BODY_HX + SKIRT_T), 3), "hole_gap_min": round(hole_gap, 3),
            "fpc_gap": round(TRAY_BOT - FPC_BOT_Z, 3),
            "tray_floor_min_at_res": round(1.0 - max([r["pocket_z"][1] for r in fpc_geom().get("capsule_res_pockets", {}).get("rects", [])] or [TRAY_BOT]), 3),
            "tray_wall_at_groove": round((r13.BODY_W - r13.INNER_W) / 2 - GROOVE[2], 3), "face_t": FACE_T}


if __name__ == "__main__":
    tray, cap = build_tray_d2(), build_cap()
    for name, part in (("tray_d2", tray), ("cap_d2", cap)):
        b.export_step(part, str(HERE / f"{name}.step"))
        b.export_stl(part, str(HERE / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
    out = summary() | {k: {"volume": round(p.volume, 1), "solids": len(p.solids()), "valid": p.is_valid,
                           "bbox": [round(v, 3) for v in (p.bounding_box().size.X, p.bounding_box().size.Y, p.bounding_box().size.Z)]}
                       for k, p in (("tray", tray), ("cap", cap))}
    (HERE / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
