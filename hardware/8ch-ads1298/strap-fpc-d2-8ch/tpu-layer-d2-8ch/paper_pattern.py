"""D2-8CH（8通道单片软板版）整体 1:1 装配与裁胶纸样（A4 横版 297 × 210 mm）：
1. 上半幅：1:1 现成表带 + 胶囊底盖（CH1/CH2 Φ6 + EB1/EB2 方形 3×3）+ 北片 TPU（CH3–CH4）+ 南片 TPU（CH5–CH8）+ 较 16ch 裁去的 64 mm 虚线对照；
2. 右下幅：独立 1:1 裁胶/打孔模板（北片 9448A、南片 9448A、胶囊背面 0.20 mm PI 六开窗垫片），可直接垫在纸上裁切；
3. 左下幅：单片四层 FPC 叠层截面放大图（×5）+ 横向 100 mm / 纵向 50 mm 双轴校准尺。
打印选「实际大小 / 100%」，开工前先用卡尺核 100 mm 横尺与 50 mm 纵尺。
"""
from __future__ import annotations
import importlib.util as iu
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
import build as m

HERE = Path(__file__).resolve().parent
def _pick_cjk_font():
    for fp in (
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ):
        if Path(fp).is_file():
            return fm.FontProperties(fname=fp)
    return fm.FontProperties()

FONT = _pick_cjk_font()
W, H = 297.0, 210.0
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

LW = 0.4
GOLD, POCK, TPU_COL = "#f2d38a", "#9a9a9a", "#e4e4e4"
TAPE_COL, PI_COL = "#f7ebc3", "#e6def8"


def t(x: float, y: float, s: str, size: float = 7.0, **kw):
    ax.text(x, y, s, fontproperties=FONT, fontsize=size, **kw)


# ---- A. 上半幅：整体 1:1 装配对位图（皮肤面朝读者，左=北，右=南） ----
YN = 82.0
PX = lambda Y: 16.0 + (YN - Y)
CY = 136.0
PY = lambda X: CY + X

# 表带虚线框（到 Y = -128 以便直观看到 8ch 南片在 -60.1 结束、省掉 64 mm）
ax.add_patch(Rectangle((PX(YN), PY(-m.STRAP_W / 2)), PX(-128) - PX(YN), m.STRAP_W, fc="none", ec="0.60", lw=0.3, ls="--"))
t(PX(-128) + 2.0, PY(m.STRAP_W / 2) - 2.0, "25 mm 表带", 6, color="0.4")

# 16ch 已裁除南段对照虚线框（Y ∈ [-124.1, -60.1]，长 64.0 mm）
ax.add_patch(
    Rectangle(
        (PX(-60.1), PY(-m.LAYER_W / 2)),
        64.0,
        m.LAYER_W,
        fc="none",
        ec="#b85c5c",
        lw=0.35,
        ls=":",
    )
)
t(PX(-92.1), PY(0), "8ch 已裁去 CH9–CH16（缩短 64.0 mm，无空盲孔）", 6, ha="center", va="center", color="#9c3b3b")

# 胶囊底盖（复用 ../../../enclosure-46x40/c08b-shell-r12/capsule-cap-d2/build.py）
_sp = iu.spec_from_file_location("cap_plate", HERE.parents[2] / "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/build.py")
assert _sp and _sp.loader
_cp = iu.module_from_spec(_sp)
_sp.loader.exec_module(_cp)

ax.add_patch(
    FancyBboxPatch(
        (PX(_cp.BODY_HY) + _cp.BODY_R, PY(-_cp.BODY_HX) + _cp.BODY_R),
        2 * _cp.BODY_HY - 2 * _cp.BODY_R,
        2 * _cp.BODY_HX - 2 * _cp.BODY_R,
        boxstyle=f"round,pad={_cp.BODY_R}",
        fc=TPU_COL,
        ec="k",
        lw=LW,
    )
)
for sx in (-1, 1):
    y0 = PY(sx * _cp.BODY_HX) if sx > 0 else PY(-_cp.BODY_HX - _cp.SKIRT_T)
    ax.add_patch(Rectangle((PX(_cp.SKIRT_HY), y0), 2 * _cp.SKIRT_HY, _cp.SKIRT_T, fc="#9a9a9a", ec="k", lw=0.3))
for ref, (X, Y) in _cp.PADS.items():
    if ref in _cp.BIG:
        ax.add_patch(Circle((PX(Y), PY(X)), _cp.hole_d(ref) / 2, fc="white", ec="k", lw=0.3))
        ax.add_patch(Circle((PX(Y), PY(X)), _cp.BIG_D / 2, fc=GOLD, ec="#854F0B", lw=0.3))
    else:
        hh, dd = _cp.hole_d(ref), _cp.AUX_D
        ax.add_patch(Rectangle((PX(Y) - hh / 2, PY(X) - hh / 2), hh, hh, fc="white", ec="k", lw=0.3))
        ax.add_patch(Rectangle((PX(Y) - dd / 2, PY(X) - dd / 2), dd, dd, fc="#cfe3f7", ec="#854F0B", lw=0.3))
t(
    PX(0),
    PY(-_cp.BODY_HX - _cp.SKIRT_T) - 4.8,
    "胶囊底盖 46×40（复用 cap_d2）：CH1/CH2 Φ6（黄）+ EB1/EB2 方形 3×3（蓝，双 200kΩ 接 BIAS_DRV1，单片直焊免灌锡）",
    5.8,
    ha="center",
)

for Y in (m.NORTH_PIN_Y, m.SOUTH_PIN_Y):
    ax.plot([PX(Y)] * 2, [PY(-12.5), PY(12.5)], color="0.3", lw=0.6)

ring_y = m.NORTH_PIN_Y + m.RING_FROM_NORTH_PIN
ax.add_patch(Rectangle((PX(ring_y + m.RING_HALF), PY(-14)), 2 * m.RING_HALF, 28, fc="#f3c9b8", ec="#b0603a", lw=0.4))
t(PX(ring_y), PY(14) + 2.2, "日字扣环（估 55）", 5.8, ha="center")

# 北片与南片 TPU（1:1 装配位）
CH = {34.0: 3, 42.0: 4, -32.0: 5, -40.0: 6, -48.0: 7, -56.0: 8}
hd = m.hole_d()
for name, ys in (("北片", m.NORTH_YS), ("南片", m.SOUTH_YS)):
    lo, hi = m.span(ys)
    c = m.KEY
    outline = [
        (PX(lo), PY(-m.LAYER_W / 2)),
        (PX(lo), PY(m.LAYER_W / 2)),
        (PX(hi - c), PY(m.LAYER_W / 2)),
        (PX(hi), PY(m.LAYER_W / 2 - c)),
        (PX(hi), PY(-m.LAYER_W / 2)),
    ]
    ax.add_patch(Polygon(outline, closed=True, fc=TPU_COL, ec="k", lw=LW))
    for x0, x1, y0, y1 in m.pockets(ys):
        ax.add_patch(Rectangle((PX(y1), PY(x0)), y1 - y0, x1 - x0, fc=POCK, ec="none"))
    for y in ys:
        for x in (-m.PN / 2, m.PN / 2):
            ax.add_patch(Circle((PX(y), PY(x)), hd / 2, fc="white", ec="k", lw=0.3))
            ax.add_patch(Circle((PX(y), PY(x)), m.DISC_D / 2, fc=GOLD, ec="#854F0B", lw=0.3))
        t(PX(y), PY(-m.LAYER_W / 2) - 4.0, f"CH{CH[y]}", 5.8, ha="center")
    t(PX((lo + hi) / 2), PY(m.LAYER_W / 2) + 2.2, f"{name} {m.LAYER_W}×{hi - lo:.1f}", 6.8, ha="center")
ax.annotate(
    "切角 = 北端 +X（防翻面：浅槽在背面）",
    xy=(PX(46.1 - 0.75), PY(m.LAYER_W / 2 - 0.75)),
    xytext=(PX(58.0), PY(m.LAYER_W / 2 + 8.5)),
    fontproperties=FONT,
    fontsize=5.8,
    ha="center",
    arrowprops=dict(arrowstyle="->", lw=0.35, color="0.3"),
)

# 标题与说明
t(16, 201, "C08B 表带电极层 D2-8CH（8通道单片软板版）· 整体 1:1 装配与裁胶纸样（皮肤面朝你）", 10.5)
t(
    16,
    194.5,
    f"黄 = Φ{m.DISC_D}×{m.DISC_T} 镀金铜片（紧贴凸出 {m.DISC_T - m.LAYER_T:.1f} / 垫 9448A 凸出 {m.DISC_T - m.TAPE_9448A_T - m.LAYER_T:.1f}）；"
    f"白圈 = TPU 孔 Φ{hd}；深灰 = TPU 背面 0402 串阻槽（共 12 处）；同路距 {m.PN:.0f}，路距 {m.PITCH:.0f}",
    6.6,
)
t(16, 188.5, "适用：主控 R4U6/R4U6N + 单面采集板 D20-8CH/D20N-8CH + 单片软板 strap-d2-8ch + 胶囊壳 tray_d2/cap_d2", 6.6)


# ---- B. 右下幅：独立 1:1 裁胶与 PI 垫片开窗模板（直接贴在纸样上裁切） ----
def draw_tape_diecut(origin_px: float, center_py: float, ys: tuple[float, ...], title_str: str):
    lo, hi = m.span(ys)
    c = m.KEY
    # 以 hi 为左端（与上方装配图同向：左=北，上=+X，皮肤面朝读者）
    tx = lambda Y: origin_px + (hi - Y)
    ty = lambda X: center_py + X
    outline = [
        (tx(lo), ty(-m.LAYER_W / 2)),
        (tx(lo), ty(m.LAYER_W / 2)),
        (tx(hi - c), ty(m.LAYER_W / 2)),
        (tx(hi), ty(m.LAYER_W / 2 - c)),
        (tx(hi), ty(-m.LAYER_W / 2)),
    ]
    ax.add_patch(Polygon(outline, closed=True, fc=TAPE_COL, ec="#7a5d1a", lw=0.4))
    for x0, x1, y0, y1 in m.pockets(ys):
        ax.add_patch(Rectangle((tx(y1), ty(x0)), y1 - y0, x1 - x0, fc="white", ec="#7a5d1a", lw=0.25))
    for y in ys:
        for x in (-m.PN / 2, m.PN / 2):
            ax.add_patch(Circle((tx(y), ty(x)), hd / 2, fc="white", ec="#7a5d1a", lw=0.3))
    t(origin_px + (hi - lo) / 2, ty(m.LAYER_W / 2) + 2.0, title_str, 6.2, ha="center")


t(142, 87, "1:1 裁切模板（皮肤面朝你，白孔/白窗全镂空）：", 7.0)
draw_tape_diecut(142.0, 66.0, m.NORTH_YS, "① 北片 9448A 双面胶 16.2×26.2")
draw_tape_diecut(172.0, 66.0, m.SOUTH_YS, "② 南片 9448A 双面胶 32.2×26.2")

# ③ 胶囊段背面 0.20 mm PI 垫片 1:1 模板（从 strap-d2-8ch/geometry.json 读取真实多边形与 6 窗，皮肤面视角 X_strap = 50 - by, Y_strap = 58 - bx）
geo_fpc = json.loads(m.FPC_GEOM.read_text(encoding="utf-8"))
sp_pi = next(st for st in geo_fpc["a"]["stiffeners"] if "poly" in st)
pi_ox, pi_cy = 222.0, 66.0
pi_ymax = max(58.0 - pt[0] for pt in sp_pi["poly"])  # 17.6
px_pi = lambda bx: pi_ox + (pi_ymax - (58.0 - bx))
py_pi = lambda by: pi_cy + (50.0 - by)
pi_pts = [(px_pi(pt[0]), py_pi(pt[1])) for pt in sp_pi["poly"]]
ax.add_patch(Polygon(pi_pts, closed=True, fc=PI_COL, ec="#4c3b8a", lw=0.4))
for hx0, hx1, hy0, hy1 in sp_pi["holes"]:
    wx0, wx1 = sorted((px_pi(hx0), px_pi(hx1)))
    wy0, wy1 = sorted((py_pi(hy0), py_pi(hy1)))
    ax.add_patch(Rectangle((wx0, wy0), wx1 - wx0, wy1 - wy0, fc="white", ec="#4c3b8a", lw=0.3))
t(pi_ox + 16.9, pi_cy + 14.2, "③ 胶囊背 0.20 PI 垫片（6窗避串阻）", 6.2, ha="center")
t(
    142,
    46.5,
    "注：③ 由嘉立创贴装压合出厂自带；若手工改制垫片，按上方皮肤面同向（左=北，上=+X）冲切 6 个串阻窗（含非对称 R33）。",
    5.6,
    color="0.3",
)


# ---- C. 左下幅：单片四层 FPC 叠层截面放大图（×5） ----
k = 5.0
sx, sy = 18.0, 76.0
layers = [
    ("25 mm 表带（约 1.6，假设）", 1.60, "#5f5e5a"),
    ("Φ7.2 圆形 PI 补强 0.20（12 处）", 0.20, "#7F77DD"),
    ("单片四层 FPC 0.203", 0.203, "#185FA5"),
    ("3M 9448A 0.10（开孔+开槽窗）", 0.10, "#d9c27a"),
    (f"TPU 电极层 {m.LAYER_T:.2f}", m.LAYER_T, "#b4b2a9"),
]
z = 0.0
W_sec = 38.0
for i, (nm, th, col) in enumerate(layers):
    ax.add_patch(Rectangle((sx, sy - (z + th) * k), W_sec, th * k, fc=col, ec="k", lw=0.2))
    ly = sy - 1.5 - i * 4.8
    ax.plot([sx + W_sec, sx + W_sec + 5.5], [sy - (z + th / 2) * k, ly + 1.0], color="0.4", lw=0.25)
    t(sx + W_sec + 6.5, ly, nm, 5.8)
    z += th
for xx in (sx + 0.18 * W_sec, sx + 0.82 * W_sec):
    ax.add_patch(
        Rectangle(
            (xx - 2.3, sy - (z - m.LAYER_T - 0.10) * k - m.DISC_T * k),
            4.6,
            m.DISC_T * k,
            fc=GOLD,
            ec="#854F0B",
            lw=0.3,
        )
    )
ax.add_patch(Rectangle((sx + 0.42 * W_sec, sy - (z - m.LAYER_T) * k - 0.35 * k), 2.0, 0.35 * k, fc="#333", ec="none"))
t(sx, sy + 3.5, "表带段叠层截面（厚度 ×5 示意，皮肤朝下）：", 6.8)
t(sx, sy - (z + 1.2) * k - 8.5, "黑块 = F.Cu 0402 串阻（100 kΩ，藏进 TPU 0.45 深浅槽，净空 0.20 mm）", 5.6)
t(sx, sy - (z + 1.2) * k - 13.5, "链路：皮肤 → Φ6 镀金铜片 → 焊锡 → FPC 焊盘 → 100kΩ → V4_FPC1 → D20-8CH(U1)", 5.6)


# ---- D. 双轴 1:1 校准尺（横 100 mm + 纵 50 mm） ----
bx0, by0 = 150.0, 14.0
ax.plot([bx0, bx0 + 100.0], [by0, by0], lw=0.6, color="k")
for i in range(11):
    ax.plot([bx0 + 10 * i] * 2, [by0, by0 + (2.2 if i % 5 else 3.8)], lw=0.4, color="k")
t(bx0, by0 - 4.8, "横向校准尺：应精确量得 100.0 mm（打印选「实际大小 / 100%」）", 6.2)

vx0, vy0 = 287.0, 14.0
ax.plot([vx0, vx0], [vy0, vy0 + 50.0], lw=0.6, color="k")
for i in range(6):
    ax.plot([vx0 - (2.2 if i % 5 else 3.8), vx0], [vy0 + 10 * i] * 2, lw=0.4, color="k")
t(vx0 - 4.5, vy0 + 25.0, "纵向 50 mm", 5.8, rotation=90, ha="center", va="center")

for ext in ("pdf", "png"):
    fig.savefig(HERE / f"paper_pattern_d2_8ch_1to1_A4.{ext}", dpi=200 if ext == "png" else None)
print("ok")
