"""C08B 表带电极层 D2（2026-11-11 Mako：「TPU 直接贴到表带上方，不需包裹成品表带；一层表带，一层 FPC，一层 TPU，TPU 开口，贴镀金铜片」）。
叠层（从表带往皮肤）：现成 25 mm 表带 → FPC（背胶贴表带，焊盘朝皮肤，焊盘背面 PI 补强）→ TPU 层（本件，开孔）→ 镀金铜片（焊在 FPC 焊盘上，穿过 TPU 孔贴皮肤）。
TPU 只是一层带孔的软垫：盖住 FPC 不碰皮肤，铜片卡在孔里顺便定位 FPC。导电只走 铜片 → 焊锡 → FPC。
现成表带短段有日字扣环（不剪，Mako 11-11），一条连续的层会压在扣环上，所以分北、南两片：北片在胶囊和扣环之间，南片在胶囊另一侧。
表带上 14 路：北 2 路（CH3 / CH4）、南 12 路（CH5–CH16），节距 8；CH1 / CH2 和 BIAS / REF 在胶囊底（11-11 Mako「改回原来方案，触点在表盘底部」）。位置沿用 D1 全长贴片（R12 椭圆模型，腕围 182 下南条末端约到扣环附近）。
坐标：Y 沿表带（R12/R13 盒坐标，北 +），X 沿前臂（表带宽度方向，中心 0），Z 从 TPU 贴 FPC 那面（0）往皮肤（正）。平放打印。
标「假设」的等实物量了改常量，重跑 build.py → check.py → slice.sh。"""
from pathlib import Path
import json
import build123d as b

HERE = Path(__file__).resolve().parent

# ---- 布局（Y = 每路中心，沿表带） ----
PITCH = 8.0
NORTH_YS = (34.0, 42.0)                                  # CH3、CH4（R15 同位）
SOUTH_YS = tuple(-32.0 - PITCH * k for k in range(12))    # −32 … −120
NORTH_PIN_Y, SOUTH_PIN_Y = 21.65, -21.20                  # R12/R13 生耳轴
LOOP_R = 1.90                                             # 带端包弹簧棒的圆筒半径（Ø3.80）
LUG_GAP = 3.00                                            # 层离带端圆筒至少 3
RING_FROM_NORTH_PIN = 55.0                                # **假设**：不剪短段时日字扣环中心离北生耳约 55–60（取近的，偏保守），没实量
RING_HALF = 1.5
STRAP_W = 25.0         # 表带宽（Mako 11-10 量）
LAYER_W = 26.2         # TPU 层宽：比表带每边多 0.6，给 Φ6.5 孔留 0.85 壁
PN = 18.0              # 同一路 P/N 中心距（25 宽表带放 Φ6；20 会出带边，用 R15 的 18）
END_L = 1.1            # 两端各留（从铜片外沿算；孔 Φ6.5 时端壁 0.85）

# ---- 铜片（五金渠道 标准五金供应商「圆形Φ6*厚2镀金1u」，10 个一包） ----
DISC_D = 6.0
DISC_T = 2.0
HOLE_CLEAR = 0.50      # 孔 = 铜片径 + 0.5：先焊铜片再套 TPU，28 个孔要同时套进（复核 11-11 P1，0.3 太紧）

# ---- TPU 层 ----
LAYER_T = 0.80         # 层厚 → 铜片凸出 DISC_T − LAYER_T = 1.2
MIN_WALL = 0.80
FPC_T = 0.11           # 嘉立创单面 FPC 成品厚
PI_T = 0.20           # 焊盘背面 PI 补强（在 FPC 和表带之间，不影响本件；11-11 改 0.20 与叠放 B 片带等高）
# FPC 皮肤面的 0402 串阻要藏进本层背面浅槽（11-11「修不平」）：槽位从 FPC 的 geometry.json 读（同一个 v12 目录下），不在这里抄数
FPC_GEOM = HERE.parent / "geometry.json"
RES_H = 0.35           # 0402 高（假设）
POCKET_D = 0.45        # 槽深 = 串阻高 + 0.1；槽顶剩 LAYER_T − POCKET_D = 0.35（两层 0.16）
KEY = 1.5              # 方向键：北端 +X 角切 1.5 的 45° 角，贴的时候认方向（槽不对称，装反了电阻会顶 TPU）


def pockets(ys):
    """这一片范围内的串阻槽（表带坐标矩形 [X0, X1, Y0, Y1]）。"""
    lo, hi = span(ys)
    g = json.loads(FPC_GEOM.read_text(encoding="utf-8"))["f_res_pockets"]["rects"]
    out = [(r["pocket_strap"]["X"][0], r["pocket_strap"]["X"][1], r["pocket_strap"]["Y"][0], r["pocket_strap"]["Y"][1]) for r in g]
    return [q for q in out if lo < (q[2] + q[3]) / 2 < hi]


def hole_d():
    return DISC_D + HOLE_CLEAR


def span(ys):
    return min(ys) - DISC_D / 2 - END_L, max(ys) + DISC_D / 2 + END_L


def build_piece(ys):
    lo, hi = span(ys)
    s = b.Pos(0, (lo + hi) / 2, LAYER_T / 2) * b.Box(LAYER_W, hi - lo, LAYER_T)
    for y in ys:
        for x in (-PN / 2, PN / 2):
            s -= b.Pos(x, y, LAYER_T / 2) * b.Cylinder(hole_d() / 2, LAYER_T + 0.2)
    for x0, x1, y0, y1 in pockets(ys):   # 背面（Z=0，贴 FPC 那面）浅槽
        s -= b.Pos((x0 + x1) / 2, (y0 + y1) / 2, POCKET_D / 2 - 0.05) * b.Box(x1 - x0, y1 - y0, POCKET_D + 0.1)
    if KEY > 0:   # 北端 +X 角切角
        s -= b.Pos(LAYER_W / 2, hi, LAYER_T / 2) * b.Rot(0, 0, 45) * b.Box(KEY * 1.4142, KEY * 1.4142, LAYER_T + 0.2)
    return s.clean()


def gaps():
    n_lo, n_hi = span(NORTH_YS)
    s_lo, s_hi = span(SOUTH_YS)
    return {"north_to_loop": round(n_lo - (NORTH_PIN_Y + LOOP_R), 3),
            "north_to_ring": round((NORTH_PIN_Y + RING_FROM_NORTH_PIN - RING_HALF) - n_hi, 3),
            "south_to_loop": round((SOUTH_PIN_Y - LOOP_R) - s_hi, 3),
            "north_y": [n_lo, n_hi], "south_y": [s_lo, s_hi]}


def summary():
    hd = hole_d()
    return {"pitch": PITCH, "channels": len(NORTH_YS) + len(SOUTH_YS), "hole_d": hd, "disc_proud": round(DISC_T - LAYER_T, 3),
            "wall_to_edge": round(LAYER_W / 2 - PN / 2 - hd / 2, 3), "wall_between_ch": round(PITCH - hd, 3),
            "wall_to_end": round(END_L + DISC_D / 2 - hd / 2, 3), "disc_inside_strap": round(STRAP_W / 2 - PN / 2 - DISC_D / 2, 3),
            "stack_t": round(FPC_T + LAYER_T, 3), "pocket_floor": round(LAYER_T - POCKET_D, 3),
            "pockets": {"north": len(pockets(NORTH_YS)), "south": len(pockets(SOUTH_YS))}} | gaps()


if __name__ == "__main__":
    out = summary()
    for name, ys in (("north", NORTH_YS), ("south", SOUTH_YS)):
        p = build_piece(ys)
        bb = p.bounding_box()
        b.export_step(p, str(HERE / f"layer_d2_{name}.step"))
        b.export_stl(b.Pos(-bb.min.X, -bb.min.Y, 0) * p, str(HERE / f"layer_d2_{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        out[name] = {"bbox": [round(v, 3) for v in (bb.size.X, bb.size.Y, bb.size.Z)], "volume_mm3": round(p.volume, 1),
                     "solids": len(p.solids()), "valid": p.is_valid}
    (HERE / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
