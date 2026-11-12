# 表带南北入口：R15 软板真实外形 vs 表带开口（俯视，表带坐标），压进 TPU 的部分标红
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
import build123d as b
from matplotlib import font_manager
for f in ("PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"):
    if any(f == x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
shell = Path(sys.argv[1]); r15 = shell.parents[1] / "16ch-c08b-round/strap-fpc-r15"
sys.path.insert(0, str(shell)); import build as mdl   # 11-09 起开口尺寸从 build.py 读
from verify_strap_entry import r15_contacts
E = r15_contacts()
g = json.loads((r15 / "geometry.json").read_text())
# 用 build123d 2D 面做布尔（CAD 环境没有 shapely）；box(x0,y0,x1,y1) 与 shapely 同参序
def box(x0, y0, x1, y1):
    x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1)
    return b.Pos((x0 + x1) / 2, (y0 + y1) / 2) * b.Rectangle(x1 - x0, y1 - y0)
def mapped(outline, c): return b.Polygon(*[(p[1] - 50.0, c - p[0]) for p in outline], align=None)
def polys(f):
    # 按边界弧长均匀取点（vertices() 不保证沿边界顺序，会画出假斜线）
    out = []
    for q in (f.faces() if f else []):
        w = q.outer_wire()
        out.append([(v.X, v.Y) for v in w.positions([i / 1500 for i in range(1501)])])
    return out
def area(f): return sum(q.area for q in f.faces()) if f else 0.0
C = mdl.R15_STRAP_C
cases = [
    (f"南入口（南段表带，Y = {C:g} − x）", [g["a"]["outline"], g["b"]["outline"]], C,
     (mdl.SOUTH_ROOT_Y - 1.40, mdl.SOUTH_ROOT_Y), -1, (-36, -19.5), [mdl.SOUTH_ISLAND_YS[0]]),
    (f"北入口（北段表带，Y = {C:g} − x）", [g["a"]["outline"]], C,
     (mdl.NORTH_ROOT_Y, mdl.NORTH_ROOT_Y + 1.40), +1, (27.9, 47.5), list(mdl.NORTH_ISLAND_YS)),  # 27.9 以下是盒内回折的两尾，不画
]
fig, axs = plt.subplots(1, 2, figsize=(13, 7.2))
for ax, (title, outs, c, entry, sgn, ylim, hole_ys) in zip(axs, cases):
    # 表带实体（TPU，软板高度处）：开口 = 内袋 + 中缝 ±5，都从根部端面直通（build.py fpc_pocket）
    if sgn < 0:
        y_far, px = mdl.SOUTH_POCKET_END_Y, mdl.SOUTH_POCKET_X
        strap = box(-11.6, mdl.SOUTH_BODY_END_Y, 11.6, entry[1])
        opening = box(px[0], y_far, px[1], entry[1] + 0.1) + box(-5, y_far, 5, entry[1] + 0.1)
    else:
        y_far, px = mdl.NORTH_POCKET_END_Y, mdl.NORTH_POCKET_X
        strap = box(mdl.NORTH_BODY_X[0], entry[0], mdl.NORTH_BODY_X[1], mdl.NORTH_BUCKLE_Y[1])
        opening = box(px[0], entry[0] - 0.1, px[1], y_far) + box(-5, entry[0] - 0.1, 5, y_far)
    solid = strap - opening
    for pts in polys(solid):
        ax.add_patch(MPoly(pts, fc="#9aa66b", ec="#556b2f", lw=0.8, alpha=0.55))
    ax.axhspan(*entry, color="#556b2f", alpha=0.15)
    ax.text(-11.4, (entry[0] + entry[1]) / 2, "入口实体 step_down", va="center", fontsize=8, color="#33401a")
    fpc = None
    for o in outs:
        p = mapped(o, c); fpc = p if fpc is None else fpc + p
    fpc = fpc & box(-30, ylim[0], 30, ylim[1])
    for pts in polys(fpc):
        ax.add_patch(MPoly(pts, fc="#f2a65a", ec="#c0641a", lw=0.8, alpha=0.45))
    bad = fpc & solid
    for pts in polys(bad):
        ax.add_patch(MPoly(pts, fc="#d62728", ec="#8b0000", lw=0.8, alpha=0.85))
    # 表带头孔（实线）vs 钉头按盒内映射 C − x 落点（虚线，读 R15 焊盘；对齐后两圈同心）
    pads = [(E[k][1] - 50.0, C - E[k][0]) for k in ("E3P", "E3N", "E4P", "E4N", "E5P", "E5N")]
    for hy in hole_ys:
        for hx in (-9, 9):
            ax.add_patch(Circle((hx, hy), 0.83, fc="none", ec="k", lw=1.0))
    for px_, py_ in pads:
        if ylim[0] < py_ < ylim[1]:
            ax.add_patch(Circle((px_, py_), 0.75, fc="none", ec="#1f77b4", lw=1.0, ls="--"))
    ax.set_xlim(-14, 14); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.grid(alpha=0.25)
    ax.set_title(f"{title}\n压进 TPU：{area(bad):.2f} mm²", fontsize=11)
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
fig.legend(handles=[Patch(fc="#9aa66b", alpha=0.55, label="表带 TPU 实体（软板高度处）"),
                    Patch(fc="#f2a65a", alpha=0.45, label="R15 软板真实外形（A+B）"),
                    Patch(fc="#d62728", alpha=0.85, label="软板压进 TPU（过不去）"),
                    Line2D([], [], color="k", lw=1, label="表带头孔 Ø1.66"),
                    Line2D([], [], color="#1f77b4", lw=1, ls="--", label="钉头平放落点（R15 E3/E4/E5 焊盘，盒内同一映射）")],
           loc="lower center", ncol=3, fontsize=9, frameon=False)
fig.suptitle("图 1  C08B 表带入口：R15 软板外形 vs 表带开口（俯视，表带坐标；2026-11-09 对齐 R15 后）", fontsize=12)
fig.tight_layout(rect=(0, 0.11, 1, 0.95))
fig.savefig(sys.argv[2], dpi=150)
print("saved", sys.argv[2], "south/north bad area printed in titles")
