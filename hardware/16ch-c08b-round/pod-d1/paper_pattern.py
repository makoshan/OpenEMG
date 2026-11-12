"""电极小节整条 1:1 纸样（A4 横版）：皮肤面俯视（16 节、32 个铜片、桥、凹槽）+ 胶囊占位 + 一节截面 + 校准尺。
尺寸全从 build.py 常量读，改了常量重跑本脚本。打印时选「实际大小 / 100%」，先量 100 mm 校准线。"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Circle, Polygon
import build as m

HERE = Path(__file__).parent
FONT = fm.FontProperties(fname="/System/Library/Fonts/Hiragino Sans GB.ttc")   # 简体字形（PingFang.ttc 默认港版）
W, H = 297.0, 210.0
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
LW = 0.4


def t(x, y, s, size=7, **kw):
    ax.text(x, y, s, fontproperties=FONT, fontsize=size, **kw)


# ---- 皮肤面俯视：X 沿表带（纸横向），Y 沿前臂（纸纵向） ----
z0, z1, z2 = m.heights()
xs = m.pod_xs()
L = (m.N_PODS - 1) * m.pitch() + m.POD_W
ox, oy = 18.0 + m.CAPSULE_L, 125.0            # 整条左端 x、中线 y
cx = ox - m.pod_xs()[0] + m.POD_W / 2        # 整条中心
hl, hw = m.POD_L / 2, m.POD_W / 2
pd = m.FOAM_D + m.POCKET_CLEAR
ax.add_patch(Rectangle((ox - m.CAPSULE_L, oy - 23), m.CAPSULE_L, 46, fill=False, lw=LW, ls="--"))
t(ox - m.CAPSULE_L / 2, oy, f"胶囊\n{m.CAPSULE_L:.0f} × 46", 7, ha="center", va="center")
for i, x in enumerate(xs):
    X = cx + x
    ax.add_patch(Rectangle((X - hw, oy - hl), m.POD_W, m.POD_L, fill=False, lw=LW))
    for y in (-m.E_PITCH / 2, m.E_PITCH / 2):
        ax.add_patch(Circle((X, oy + y), m.E_D / 2, fill=True, fc="#f2d38a", ec="k", lw=LW))   # 铜片
        ax.add_patch(Circle((X, oy + y), pd / 2, fill=False, lw=0.25, ls=":"))                  # 凹槽
    t(X, oy - hl - 3.5, str(i + 1), 6, ha="center")
for xa, xb in zip(xs, xs[1:]):
    for sg in (-1, 1):
        y0, y1 = sorted((sg * m.BRIDGE_Y0, sg * hl))
        ax.add_patch(Rectangle((cx + xa + hw, oy + y0), xb - xa - m.POD_W, y1 - y0, fc="0.6", ec="none"))
# 表带外沿（虚线，25 宽）
for sg in (-1, 1):
    ax.plot([ox - m.CAPSULE_L - 5, ox + L + 5], [oy + sg * m.STRAP_W / 2] * 2, lw=0.25, ls="--", color="0.4")
t(ox + L + 6, oy + m.STRAP_W / 2, "表带边（25）", 6, va="center")
# 尺寸标注
ax.annotate("", (ox, oy + hl + 4), (ox + L, oy + hl + 4), arrowprops=dict(arrowstyle="<->", lw=LW))
t(ox + L / 2, oy + hl + 5.5, f"整条 {L:.1f}（节距 {m.pitch():.3f}，节宽 {m.POD_W}）；加胶囊 {L + m.CAPSULE_L:.1f} ≈ 腕围 {m.WRIST_MAKO:.0f}", 7, ha="center")
X1 = cx + xs[0]
ax.annotate("", (X1 + hw + 6, oy - m.E_PITCH / 2), (X1 + hw + 6, oy + m.E_PITCH / 2), arrowprops=dict(arrowstyle="<->", lw=LW))
t(X1 + hw + 7, oy, f"P/N {m.E_PITCH:.0f}", 6, va="center")
t(18, 196, "C08B 电极小节 D1 整条 · 1:1 纸样（皮肤面朝你）", 11)
t(18, 189, f"黄圆 = Φ{m.E_D} × {m.DISC_T} 镀金铜片；虚线圆 = 泡棉凹槽 Φ{pd:.1f}；灰块 = 节间桥；节号 1–16 从胶囊一侧数", 7)

# ---- 截面（沿前臂，一节） ----
sx, sy = 30.0, 45.0
sec = [(-hl, 0), (hl, 0), (hl, z2), (m.ch_half() - m.LIP_OVER, z2), (m.ch_half() - m.LIP_OVER, z1), (m.ch_half(), z1 - m.LIP_OVER),
       (m.ch_half(), z0), (-m.ch_half(), z0), (-m.ch_half(), z1 - m.LIP_OVER), (-(m.ch_half() - m.LIP_OVER), z1),
       (-(m.ch_half() - m.LIP_OVER), z2), (-hl, z2)]
ax.add_patch(Polygon([(sx + hl + y, sy + z) for y, z in sec], closed=True, fc="0.88", ec="k", lw=LW))
for y in (-m.E_PITCH / 2, m.E_PITCH / 2):   # 凹槽、泡棉、FPC、铜片（截面）
    ax.add_patch(Rectangle((sx + hl + y - pd / 2, sy), pd, m.POCKET_D, fc="white", ec="k", lw=0.25))
    ax.add_patch(Rectangle((sx + hl + y - m.FOAM_D / 2, sy - m.PAD_PROUD), m.FOAM_D, m.FOAM_T, fc="#cde6c4", ec="k", lw=0.25))
    ax.add_patch(Rectangle((sx + hl + y - m.E_D / 2, sy - m.PAD_PROUD - m.FPC_T - m.DISC_T), m.E_D, m.DISC_T, fc="#f2d38a", ec="k", lw=0.25))
ax.add_patch(Rectangle((sx + hl - m.STRAP_W / 2, sy + z0), m.STRAP_W, m.STRAP_T, fc="none", ec="0.3", lw=0.3, ls="--"))
t(sx, sy + z2 + 9, f"一节截面（沿前臂）· 高 {z2:.1f}，表带 {m.STRAP_W:.0f}×{m.STRAP_T}（假设）在槽里，铜片凸出 {m.summary()['contact_proud']:.2f}", 7)
FPC_C = "#3b5bdb"   # FPC 用蓝色粗线画，导电的只有它和铜片


def fpc_path(y0, z0_, k):
    """FPC 中心线：平时贴在 TPU 皮肤面（z=0），到凹槽处被泡棉顶出 PAD_PROUD。k 是放大倍数。"""
    pts = [(-hl, 0.0)]
    for ye in (-m.E_PITCH / 2, m.E_PITCH / 2):
        a, b_ = ye - pd / 2 - m.MOUTH_CHAMFER, ye + pd / 2 + m.MOUTH_CHAMFER
        pts += [(a, 0.0), (ye - m.FOAM_D / 2, -m.PAD_PROUD), (ye + m.FOAM_D / 2, -m.PAD_PROUD), (b_, 0.0)]
    pts.append((hl, 0.0))
    return [(y0 + k * (y + hl), z0_ + k * (z - m.FPC_T / 2)) for y, z in pts]


xs_, zs_ = zip(*fpc_path(sx, sy, 1.0))
ax.plot(xs_, zs_, color=FPC_C, lw=0.9)
t(sx + m.POD_L + 10, sy - 4, "绿 = 泡棉 Φ6×2（不导电）\n蓝 = FPC（导电，走线到胶囊）\n黄 = 镀金铜片（导电，焊在 FPC 焊盘上）\n灰 = TPU（不导电）\n虚线 = 表带", 6)

# ---- 放大 ×4：一个电极 ----
K = 4.0
dx, dy = 175.0, 58.0          # 放大图左下角
ye = m.E_PITCH / 2            # 取 y=+10 那个电极，左右各看 6 mm
yl, yr = ye - 6.0, ye + 6.0
def P(y, z):
    return (dx + K * (y - yl), dy + K * z)
tpu = [P(yl, 0), P(ye - pd / 2 - m.MOUTH_CHAMFER, 0), P(ye - pd / 2, m.MOUTH_CHAMFER), P(ye - pd / 2, m.POCKET_D),
       P(ye + pd / 2, m.POCKET_D), P(ye + pd / 2, m.MOUTH_CHAMFER), P(ye + pd / 2 + m.MOUTH_CHAMFER, 0), P(yr, 0),
       P(yr, m.BASE_T), P(yl, m.BASE_T)]
ax.add_patch(Polygon(tpu, closed=True, fc="0.88", ec="k", lw=LW))
ax.add_patch(Polygon([P(ye - m.FOAM_D / 2, -m.PAD_PROUD), P(ye + m.FOAM_D / 2, -m.PAD_PROUD), P(ye + m.FOAM_D / 2, m.FOAM_T - m.PAD_PROUD),
                      P(ye - m.FOAM_D / 2, m.FOAM_T - m.PAD_PROUD)], closed=True, fc="#cde6c4", ec="k", lw=0.3))
zf = -m.PAD_PROUD - m.FPC_T
fp = [(yl, 0.0), (ye - pd / 2 - m.MOUTH_CHAMFER, 0.0), (ye - m.FOAM_D / 2, -m.PAD_PROUD), (ye + m.FOAM_D / 2, -m.PAD_PROUD),
      (ye + pd / 2 + m.MOUTH_CHAMFER, 0.0), (yr, 0.0)]
ax.plot(*zip(*[P(y, z - m.FPC_T / 2) for y, z in fp]), color=FPC_C, lw=K * m.FPC_T * 72 / 25.4)
ax.add_patch(Polygon([P(ye - m.E_D / 2, zf - m.DISC_T), P(ye + m.E_D / 2, zf - m.DISC_T), P(ye + m.E_D / 2, zf), P(ye - m.E_D / 2, zf)],
                     closed=True, fc="#f2d38a", ec="k", lw=0.3))
ax.plot(*zip(P(ye - m.E_D / 2 + 0.3, zf), P(ye + m.E_D / 2 - 0.3, zf)), color="0.45", lw=1.0)   # 焊锡层（示意）
ax.plot([dx - 4, dx + K * 12 + 4], [dy + K * (zf - m.DISC_T)] * 2, color="#c0705a", lw=0.6, ls="--")
lab = [("TPU 小节（不导电）", ye + 4.5, 1.6), ("泡棉 Φ6×2（不导电，当弹簧）", ye + 1.5, 0.9), ("FPC 焊盘 + 走线（导电）", ye + 5.0, -0.05),
       ("焊锡（导电）", ye + 2.0, zf), ("镀金铜片（导电，贴皮肤）", ye + 1.0, zf - 0.6), ("皮肤", ye - 5.5, zf - m.DISC_T - 0.25)]
for s_, y, z in lab:
    x0, z0p = P(y, z)
    ax.annotate(s_, (x0, z0p), (dx + K * 12 + 8, z0p + 0.0), fontproperties=FONT, fontsize=6, va="center",
                arrowprops=dict(arrowstyle="-", lw=0.3, color="0.3"))
t(dx, dy + K * m.BASE_T + 6, "放大 ×4：一个电极（不是 1:1）", 7)
t(dx, dy + K * (zf - m.DISC_T) - 6, "电流：皮肤 → 铜片 → 焊锡 → FPC 焊盘 → FPC 走线 → 胶囊插座 → 采集板", 6)

# ---- 校准尺 ----
by = 14.0
ax.plot([18, 118], [by, by], lw=0.6, color="k")
for k in range(11):
    ax.plot([18 + 10 * k] * 2, [by, by + (2.5 if k % 5 else 4)], lw=0.4, color="k")
t(18, by - 5, "校准：这条线应量得 100 mm（打印选「实际大小 / 100%」）", 7)
ax.add_patch(Rectangle((140, 9), 10, 10, fill=False, lw=0.5)); t(152, 12, "10 × 10 mm", 6)
t(200, 9, "剪下整条外框，绕手腕一圈，看铜片落点与胶囊接口", 7)

for ext in ("pdf", "png"):
    fig.savefig(HERE / f"paper_pattern_1to1_A4.{ext}", dpi=200 if ext == "png" else None)
print("ok", round(L, 3))
