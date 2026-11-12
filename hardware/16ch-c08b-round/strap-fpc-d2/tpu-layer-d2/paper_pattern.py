"""D2 表带电极层整体 1:1 纸样（A4 横版）：表带 + 胶囊 + 北/南两片 TPU（孔、铜片、串阻槽、方向切角）+ 通道号 + 扣环估位 + 叠层截面（放大）+ 校准尺。
尺寸全从 build.py 读；打印选「实际大小 / 100%」，先量 100 mm 校准线。"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Circle, Polygon
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
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
LW = 0.4
GOLD, POCK, TPU = "#f2d38a", "#9a9a9a", "#e4e4e4"


def t(x, y, s, size=7, **kw):
    ax.text(x, y, s, fontproperties=FONT, fontsize=size, **kw)


# 表带坐标 (X 横跨带宽, Y 沿带长，北 +) → 纸面：北在左
YN = 82.0
PX = lambda Y: 16.0 + (YN - Y)
CY = 128.0
PY = lambda X: CY + X

# 表带
ax.add_patch(Rectangle((PX(YN), PY(-m.STRAP_W / 2)), PX(-128) - PX(YN), m.STRAP_W, fc="none", ec="0.55", lw=0.3, ls="--"))
t(PX(-128) + 1.5, PY(m.STRAP_W / 2) - 2, "表带 25", 6, color="0.4")
# 胶囊与生耳
# 胶囊底盖（../../../enclosure-46x40/c08b-shell-r12/capsule-cap-d2/build.py：正面和胶囊底同大，两条长边裙边，6 孔「大—小—大」）
import importlib.util as _iu
_sp = _iu.spec_from_file_location("cap_plate", HERE.parents[2] / "enclosure-46x40/c08b-shell-r12/capsule-cap-d2/build.py")
_cp = _iu.module_from_spec(_sp); _sp.loader.exec_module(_cp)
from matplotlib.patches import FancyBboxPatch
ax.add_patch(FancyBboxPatch((PX(_cp.BODY_HY) + _cp.BODY_R, PY(-_cp.BODY_HX) + _cp.BODY_R), 2 * _cp.BODY_HY - 2 * _cp.BODY_R,
                            2 * _cp.BODY_HX - 2 * _cp.BODY_R, boxstyle=f"round,pad={_cp.BODY_R}", fc=TPU, ec="k", lw=LW))
for sx in (-1, 1):   # 裙边（长边直段）
    y0 = PY(sx * _cp.BODY_HX) if sx > 0 else PY(-_cp.BODY_HX - _cp.SKIRT_T)
    ax.add_patch(Rectangle((PX(_cp.SKIRT_HY), y0), 2 * _cp.SKIRT_HY, _cp.SKIRT_T, fc="#9a9a9a", ec="k", lw=0.3))
for ref, (X, Y) in _cp.PADS.items():   # 孔位对称，表带 / 盒两套坐标在这里不分镜像
    big = ref in _cp.BIG
    if big:
        ax.add_patch(Circle((PX(Y), PY(X)), _cp.hole_d(ref) / 2, fc="white", ec="k", lw=0.3))
        ax.add_patch(Circle((PX(Y), PY(X)), _cp.BIG_D / 2, fc=GOLD, ec="#854F0B", lw=0.3))
    else:   # 辅点方形 3×3×2，方孔
        hh, dd = _cp.hole_d(ref), _cp.AUX_D
        ax.add_patch(Rectangle((PX(Y) - hh / 2, PY(X) - hh / 2), hh, hh, fc="white", ec="k", lw=0.3))
        ax.add_patch(Rectangle((PX(Y) - dd / 2, PY(X) - dd / 2), dd, dd, fc="#cfe3f7", ec="#854F0B", lw=0.3))
t(PX(0), PY(-_cp.BODY_HX - _cp.SKIRT_T) - 4.5, "胶囊底盖 46 × 40（两条长边裙边扣住，两端过表带）：CH1 / CH2 Φ6（黄）+ BIAS / REF 方 3×3（蓝），两排「大—小—大」", 6, ha="center")
for Y in (m.NORTH_PIN_Y, m.SOUTH_PIN_Y):
    ax.plot([PX(Y)] * 2, [PY(-12.5), PY(12.5)], color="0.3", lw=0.6)
# 日字扣环（估）
ring = m.NORTH_PIN_Y + m.RING_FROM_NORTH_PIN
ax.add_patch(Rectangle((PX(ring + m.RING_HALF), PY(-14)), 2 * m.RING_HALF, 28, fc="#f3c9b8", ec="#b0603a", lw=0.4))
t(PX(ring) , PY(14) + 2, "日字扣环（估 55）", 6, ha="center")

# 两片 TPU
CH = {34.0: 3, 42.0: 4}
CH.update({-32.0 - 8.0 * k: 5 + k for k in range(12)})
hd = m.hole_d()
for name, ys in (("北片", m.NORTH_YS), ("南片", m.SOUTH_YS)):
    lo, hi = m.span(ys)
    c = m.KEY
    outline = [(PX(lo), PY(-m.LAYER_W / 2)), (PX(lo), PY(m.LAYER_W / 2)), (PX(hi - c), PY(m.LAYER_W / 2)),
               (PX(hi), PY(m.LAYER_W / 2 - c)), (PX(hi), PY(-m.LAYER_W / 2))]
    ax.add_patch(Polygon(outline, closed=True, fc=TPU, ec="k", lw=LW))
    for x0, x1, y0, y1 in m.pockets(ys):
        ax.add_patch(Rectangle((PX(y1), PY(x0)), y1 - y0, x1 - x0, fc=POCK, ec="none"))
    for y in ys:
        for x in (-m.PN / 2, m.PN / 2):
            ax.add_patch(Circle((PX(y), PY(x)), hd / 2, fc="white", ec="k", lw=0.3))
            ax.add_patch(Circle((PX(y), PY(x)), m.DISC_D / 2, fc=GOLD, ec="#854F0B", lw=0.3))
        t(PX(y), PY(-m.LAYER_W / 2) - 4, f"CH{CH[y]}", 6, ha="center")
    t(PX((lo + hi) / 2), PY(m.LAYER_W / 2) + 2, f"{name} {m.LAYER_W} × {hi - lo:.1f}", 7, ha="center")
t(PX(m.NORTH_YS[-1]) - 9, PY(m.LAYER_W / 2) + 7, "切角 = 北端 +X（防翻面）", 6)

# 标题与图例
t(16, 200, "C08B 表带电极层 D2 · 整体 1:1 纸样（皮肤面朝你）", 11)
t(16, 193, f"黄 = Φ{m.DISC_D}×{m.DISC_T} 镀金铜片（凸出 {m.DISC_T - m.LAYER_T:.1f}）；白圈 = TPU 孔 Φ{hd}；灰块 = TPU 背面串阻槽；浅灰 = TPU {m.LAYER_T} 层；同一路两片相距 {m.PN:.0f}，相邻两路 {m.PITCH:.0f}", 7)
t(16, 187, "左 = 北（短段，日字扣环一侧），右 = 南（长段）；FPC 在 TPU 下面、外形与 TPU 同宽（26.2）", 7)

# 叠层截面（放大 ×5，一路）
k = 5.0
sx, sy = 30.0, 52.0
layers = [("表带（约 1.6，假设）", 1.6, "#5f5e5a"), ("PI 补强 0.20 / 叠放带 0.203", 0.20, "#7F77DD"), ("FPC 0.20（四层）", 0.20, "#185FA5"),
          ("9448A 0.1（开孔、开槽窗）", 0.10, "#d9c27a"), (f"TPU 层 {m.LAYER_T}", m.LAYER_T, "#b4b2a9")]
z = 0.0
W_ = 26.2 * 1.6
for i, (nm, th, col) in enumerate(layers):
    ax.add_patch(Rectangle((sx, sy - (z + th) * k), W_, th * k, fc=col, ec="k", lw=0.2))
    ly = sy - 1.5 - i * 5.0                       # 标签等距排开，引线指到该层中间
    ax.plot([sx + W_, sx + W_ + 6], [sy - (z + th / 2) * k, ly + 1.0], color="0.4", lw=0.25)
    t(sx + W_ + 7, ly, nm, 6)
    z += th
for xx in (sx + 0.18 * W_, sx + 0.82 * W_):   # 铜片穿过 TPU
    ax.add_patch(Rectangle((xx - 3 * 1.6 / 2 * 1.0, sy - (z - m.LAYER_T - 0.1) * k - m.DISC_T * k), 3 * 1.6, m.DISC_T * k, fc=GOLD, ec="#854F0B", lw=0.3))
ax.add_patch(Rectangle((sx + 0.42 * W_, sy - (z - m.LAYER_T) * k - 0.35 * k), 2.0, 0.35 * k, fc="#333", ec="none"))
t(sx + 0.42 * W_ - 6, sy - (z + 0.5) * k - 9, "黑块 = 串阻（皮肤面，藏在 TPU 槽里）", 5.5)
t(sx, sy + 4, "叠层截面（厚度 ×5，宽度示意，不是 1:1）：皮肤在下", 7)
t(sx, sy - (z + 1.2) * k - 14, "电流：皮肤 → 铜片 → 焊锡 → FPC 焊盘 → 串阻 → FPC 走线 → 胶囊插座 → 采集板", 6)

# 校准尺
by = 12.0
ax.plot([180, 280], [by, by], lw=0.6, color="k")
for i in range(11):
    ax.plot([180 + 10 * i] * 2, [by, by + (2.5 if i % 5 else 4)], lw=0.4, color="k")
t(180, by - 5, "校准：应量得 100 mm（打印选「实际大小 / 100%」）", 6.5)

for ext in ("pdf", "png"):
    fig.savefig(HERE / f"paper_pattern_d2_1to1_A4.{ext}", dpi=200 if ext == "png" else None)
print("ok")
