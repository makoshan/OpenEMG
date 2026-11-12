"""从真实生成的 R12 CAD 实体三角网渲染三张高分辨率预览与剖面图：
1. preview-overview.png：透明外壳整机四视图（等轴测 + 俯视 XY + 侧视 YZ + 正视 XZ）
2. preview-sections.png：三处关键工程剖面（A-A 顶部楔面开关柱塞、B-B USB-C 窗口与顶盖净空、C-C 南北隐藏生耳槽与 R14 软板通道）
3. preview-exploded-lugs.png：五件套单实体与快拆弹簧棒爆炸装配图
"""

from pathlib import Path
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Polygon as MplPolygon, FancyBboxPatch, Circle, Rectangle
import build as mdl

plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

P = Path(__file__).resolve().parent


def tessellate_solid(shape, tol=0.12):
    solids = shape.solids() if hasattr(shape, "solids") and len(shape.solids()) > 1 else [shape]
    all_verts = []
    all_faces = []
    offset = 0
    for s in solids:
        vs, fs = s.tessellate(tol)
        if not vs or not fs:
            continue
        verts = np.array([[float(v.X), float(v.Y), float(v.Z)] for v in vs], dtype=float)
        faces = np.array([[int(i) + offset for i in f] for f in fs], dtype=int)
        all_verts.append(verts)
        all_faces.append(faces)
        offset += len(verts)
    return np.vstack(all_verts), np.vstack(all_faces)


def project_mesh(verts, faces, mode="iso", light_dir=(0.45, -0.55, 0.70)):
    """将 3D 三角网格投影为 2D 多边形集合并按法向计算明暗。"""
    L = np.asarray(light_dir, dtype=float)
    L /= np.linalg.norm(L)

    tris3d = verts[faces]  # (N, 3, 3)
    v1 = tris3d[:, 1] - tris3d[:, 0]
    v2 = tris3d[:, 2] - tris3d[:, 0]
    normals = np.cross(v1, v2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, np.maximum(norms, 1e-12))
    shade = 0.58 + 0.42 * np.clip(normals @ L, -1.0, 1.0)

    if mode == "iso":
        # 东北俯视等轴测投影
        az = np.radians(-38.0)
        el = np.radians(28.0)
        ca, sa = np.cos(az), np.sin(az)
        ce, se = np.cos(el), np.sin(el)
        x = tris3d[:, :, 0]
        y = tris3d[:, :, 1]
        z = tris3d[:, :, 2]
        px = ca * x - sa * y
        py = se * (sa * x + ca * y) + ce * z
        depth = -ce * (sa * x + ca * y) + se * z
    elif mode == "iso_bottom":
        # 仰视等轴测投影（看清底面 6 电极孔、南北 C 形半圆槽、盲孔与软板出口）
        az = np.radians(-35.0)
        el = np.radians(-32.0)
        ca, sa = np.cos(az), np.sin(az)
        ce, se = np.cos(el), np.sin(el)
        x = tris3d[:, :, 0]
        y = tris3d[:, :, 1]
        z = tris3d[:, :, 2]
        px = ca * x - sa * y
        py = se * (sa * x + ca * y) + ce * z
        depth = -ce * (sa * x + ca * y) + se * z
    elif mode == "xy":
        px = tris3d[:, :, 0]
        py = tris3d[:, :, 1]
        depth = tris3d[:, :, 2]
    elif mode == "yz":
        px = tris3d[:, :, 1]
        py = tris3d[:, :, 2]
        depth = tris3d[:, :, 0]
    elif mode == "xz":
        px = tris3d[:, :, 0]
        py = tris3d[:, :, 2]
        depth = -tris3d[:, :, 1]
    else:
        raise ValueError(mode)

    order = np.argsort(depth.mean(axis=1))
    polys2d = np.stack([px[order], py[order]], axis=-1)
    return polys2d, shade[order]


def add_mesh_to_ax(ax, verts, faces, base_rgba, mode="iso", edge_alpha=0.06, lw=0.25):
    polys2d, shade = project_mesh(verts, faces, mode=mode)
    r, g, b_col, alpha = base_rgba
    colors = np.zeros((len(shade), 4), dtype=float)
    colors[:, 0] = np.clip(r * shade, 0, 1)
    colors[:, 1] = np.clip(g * shade, 0, 1)
    colors[:, 2] = np.clip(b_col * shade, 0, 1)
    colors[:, 3] = alpha
    edge_col = (r * 0.45, g * 0.45, b_col * 0.45, edge_alpha) if edge_alpha > 0 else "none"
    coll = PolyCollection(polys2d, facecolors=colors, edgecolors=edge_col, linewidths=lw)
    ax.add_collection(coll)


def render_overview(meshes):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    draw_order = [
        ("contacts", (0.85, 0.65, 0.18, 0.95)),
        ("r14_fpc", (0.88, 0.43, 0.12, 0.90)),
        ("d17_board", (0.08, 0.42, 0.24, 0.92)),
        ("pcb_standoffs", (0.86, 0.68, 0.20, 0.96)),
        ("ffc20", (0.92, 0.76, 0.22, 0.90)),
        ("battery", (0.38, 0.56, 0.78, 0.88)),
        ("mcu_board", (0.10, 0.28, 0.48, 0.90)),
        ("m14_screws", (0.76, 0.80, 0.85, 0.98)),
        ("usb_j400", (0.72, 0.75, 0.78, 0.95)),
        ("sw300", (0.22, 0.24, 0.28, 0.95)),
        ("ufl_plug", (0.85, 0.68, 0.12, 0.96)),
        ("fpc_ant", (0.90, 0.25, 0.55, 0.94)),
        ("d401_led", (0.15, 0.88, 0.35, 0.98)),
        ("spring_bars", (0.78, 0.80, 0.84, 0.95)),
        ("south_woven_strap_loop", (0.29, 0.35, 0.18, 0.86)),
        ("north_woven_strap_loop", (0.29, 0.35, 0.18, 0.86)),
        ("tray", (0.74, 0.88, 0.96, 0.42)),
        ("cover", (0.82, 0.93, 0.99, 0.36)),
        ("switch_plunger", (0.16, 0.62, 0.90, 0.88)),
    ]

    views = [
        (axes[0, 0], "iso", "A. 8001 全透明整机等轴测透视图（内置北走廊 2.4G FPC 天线）", (-34, 34), (-22, 26)),
        (axes[0, 1], "xy", "B. 俯视图 XY（顶孔开关 + J300 同轴头微凸窗 + 北无铜走廊天线）", (-26, 26), (-31, 33)),
        (axes[1, 0], "yz", "C. 侧视图 YZ（主体高 10.1 mm，J300 微凸包 10.84 mm）", (-31, 33), (-1.5, 12.0)),
        (axes[1, 1], "xz", "D. 正视图 XZ（东侧 USB-C 窗口 + 底部 6 电极触点）", (-26, 26), (-1.5, 12.0)),
    ]

    for ax, mode, title, xlim, ylim in views:
        ax.set_facecolor("#FFFFFF")
        for key, rgba in draw_order:
            if key in meshes:
                v, f = meshes[key]
                add_mesh_to_ax(ax, v, f, rgba, mode=mode, edge_alpha=0.08 if "lug" in key or key in ("tray", "cover") else 0.04)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.grid(True, linestyle="--", alpha=0.25, color="#94A3B8")
        ax.set_title(title, fontsize=12, fontweight="bold", color="#0F172A", pad=8)

    # 俯视图关键尺寸标注
    ax_xy = axes[0, 1]
    ax_xy.annotate(
        "顶孔楔面柱塞 switch_plunger\n(推动侧按 SW300 朝 -X)",
        xy=(3.5, 15.1),
        xytext=(-22.0, 24.5),
        fontsize=8.5,
        fontweight="bold",
        color="#0369A1",
        arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#E0F2FE", ec="#0284C7", lw=0.8),
    )
    ax_xy.annotate(
        "北无铜走廊 2.4G FPC 天线 (20×4.2mm)\n+ J300 1代 U.FL 插头微凸包",
        xy=(6.2, 16.5),
        xytext=(5.5, 24.5),
        fontsize=8.2,
        fontweight="bold",
        color="#BE185D",
        arrowprops=dict(arrowstyle="->", color="#BE185D", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#FCE7F3", ec="#DB2777", lw=0.8),
    )
    ax_xy.annotate(
        "指示灯 D401 (10.0, 9.7)\n透过 8001 全透明上盖直接可见",
        xy=(10.0, 9.7),
        xytext=(9.0, 2.0),
        fontsize=8.0,
        fontweight="bold",
        color="#15803D",
        arrowprops=dict(arrowstyle="->", color="#15803D", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#DCFCE7", ec="#16A34A", lw=0.8),
    )
    ax_xy.annotate(
        "南隐藏生耳槽 (22.30mm 槽宽配 22.04mm 表带)\nR14 软板 A+B (14.12mm) 常插出盒",
        xy=(0.0, -22.5),
        xytext=(-21.0, -29.8),
        fontsize=8.5,
        fontweight="bold",
        color="#B45309",
        arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#FEF3C7", ec="#D97706", lw=0.8),
    )

    # 侧视图高度标注
    ax_yz = axes[1, 0]
    ax_yz.axhline(0.0, color="#B45309", ls=":", lw=1.0)
    ax_yz.axhline(10.10, color="#0369A1", ls=":", lw=1.0)
    ax_yz.annotate(
        "主体高 10.10 mm（J300 透明微凸窗 Z=10.84 mm）\n8001 全透明喷油余量已预留",
        xy=(-14.0, 10.10),
        xytext=(-30.0, 8.20),
        fontsize=8.2,
        fontweight="bold",
        color="#0369A1",
        arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.0),
        bbox=dict(boxstyle="round,pad=0.22", fc="#E0F2FE", ec="#0284C7", lw=0.7),
    )

    fig.suptitle(
        "OpenEMG V12 · C08B 透明光固化外壳 R12（嘉立创 8001 全透明 + 对齐 IMG_3797.MOV 快拆生耳直连 · 3 单实体）",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = P / "preview-overview.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_sections():
    """绘制三处精确工程剖面图（直接按 R12 真实坐标绘制剖面几何与间隙标注）。"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.2), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    # --- 剖面 A-A：Y = 15.10 mm（XZ 剖面，穿过 SW300、顶部 45° 楔面开关柱塞与 J300 U.FL 同轴插头微凸窗） ---
    ax = axes[0]
    ax.set_facecolor("#FFFFFF")
    ax.set_title("剖面 A-A (Y=15.1 mm)：顶孔楔面柱塞 + J300 1代 U.FL 同轴插头微凸窗", fontsize=10.5, fontweight="bold")
    # 主控板 Z=6.79..7.41
    ax.add_patch(Rectangle((-1.0, 6.79), 10.0, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.0, label="主控 PCB (Z=6.79..7.41)"))
    # SW300 本体与按杆 (x: -0.21..3.38, z: 7.41..8.80)
    ax.add_patch(Rectangle((-0.21, 7.41), 3.19, 1.39, fc="#475569", ec="#1E293B", lw=1.0, label="SW300 开关体"))
    ax.add_patch(Rectangle((2.98, 7.65), 0.40, 0.95, fc="#F59E0B", ec="#B45309", lw=1.2, label="SW300 侧按杆 (x=3.38→2.74)"))
    # J300 U.FL 座 (x: 4.71..7.71, z: 7.42..8.69) 与 1代 U.FL 同轴插头 (z: 7.42..9.81)
    ax.add_patch(Rectangle((4.71, 7.42), 3.00, 1.27, fc="#94A3B8", ec="#334155", lw=1.0, label="J300 U.FL 母座 (Z=7.42..8.69)"))
    ax.add_patch(Rectangle((4.86, 8.69), 2.85, 1.12, fc="#FBBF24", ec="#B45309", lw=1.1, alpha=0.85, label="J300 1代 U.FL 插头 (顶 Z=9.81)"))
    # 上盖 cover 顶壁剖面 (左段 Z=9.10..10.10，孔 x=2.30..4.64，右段含 J300 透明微凸包 Z=9.98..10.84)
    ax.add_patch(Rectangle((-1.0, 9.10), 3.30, 1.00, fc="#BAE6FD", ec="#0284C7", lw=1.2, alpha=0.75, label="8001 全透明上盖 cover"))
    cover_right_xz = [
        (4.64, 9.98), (7.95, 9.98), (7.95, 9.10), (9.00, 9.10),
        (9.00, 10.10), (8.60, 10.10), (8.25, 10.84), (4.64, 10.84)
    ]
    ax.add_patch(MplPolygon(cover_right_xz, closed=True, fc="#BAE6FD", ec="#0284C7", lw=1.2, alpha=0.75))
    # 开关柱塞静止位截面
    plunger_xz = [
        (2.50, 10.40),
        (4.44, 10.40),
        (4.44, 8.22),
        (3.54, 8.22),
        (3.54, 8.90),
        (2.84, 8.90),
        (2.50, 9.24),
    ]
    ax.add_patch(MplPolygon(plunger_xz, closed=True, fc="#0284C7", ec="#0369A1", lw=1.3, alpha=0.78, label="柱塞 switch_plunger (静止位)"))
    # 柱塞下压 -0.80 mm 虚线轮廓
    plunger_down_xz = [(x, z - 0.80) for x, z in plunger_xz]
    ax.add_patch(MplPolygon(plunger_down_xz, closed=True, fc="none", ec="#DC2626", lw=1.4, ls="--", label="下压 ΔZ=-0.80mm 极限位"))
    # 南侧防脱翼投影虚线框 (x: 3.54..5.54, z: 8.22..9.06)
    ax.add_patch(Rectangle((3.54, 8.22), 2.00, 0.84, fc="#38BDF8", ec="#0369A1", lw=1.0, ls=":", alpha=0.35, label="南/东侧防脱翼 (y=12.3..14.0)"))
    ax.annotate("下压 0.80 mm\n45° 楔面推按杆 -X 0.64 mm\n(> 0.50 mm 满行程)", xy=(3.05, 8.35), xytext=(-0.8, 9.35),
                fontsize=7.8, fontweight="bold", color="#DC2626", arrowprops=dict(arrowstyle="->", color="#DC2626"))
    ax.annotate("J300 同轴头微凸窗\n(内顶 9.98, 顶壁 0.86mm)", xy=(6.3, 10.0), xytext=(5.1, 10.95),
                fontsize=7.8, fontweight="bold", color="#B45309", arrowprops=dict(arrowstyle="->", color="#B45309"))
    ax.set_xlim(-1.0, 8.8)
    ax.set_ylim(6.4, 11.45)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Z (mm)")
    ax.grid(True, ls="--", alpha=0.3)
    ax.legend(loc="lower left", fontsize=6.8, framealpha=0.9)

    # --- 剖面 B-B：东侧 USB-C 窗口与 U12/U17 顶盖间隙 (XZ 剖面) ---
    ax2 = axes[1]
    ax2.set_facecolor("#FFFFFF")
    ax2.set_title("剖面 B-B (东侧 XZ)：J400 USB-C 窗口 + 顶盖加高至 10.1 mm 净空", fontsize=11, fontweight="bold")
    # D17 板与主控板
    ax2.add_patch(Rectangle((8.0, 2.55), 12.6, 0.80, fc="#15803D", ec="#14532D", lw=1.0, label="D17 采集板 (Z=2.55..3.35)"))
    ax2.add_patch(Rectangle((8.0, 6.79), 13.55, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.0, label="主控板 (Z=6.79..7.41)"))
    # U17 SOT-23-6 (x: 8.94..11.86, 规格书 z=8.86, 嘉立创3D z=9.10)
    ax2.add_patch(Rectangle((8.94, 7.41), 2.92, 1.45, fc="#334155", ec="#0F172A", lw=1.0, label="U17 实测规格书高 (Z=8.86, 余0.40mm)"))
    ax2.add_patch(Rectangle((8.94, 8.86), 2.92, 0.24, fc="none", ec="#F59E0B", lw=1.1, ls="--", label="U17 嘉立创库3D虚高 (Z=9.10, 余0.16mm)"))
    # J400 母座 (x: 15.15..22.35, z: 5.30..8.47)
    ax2.add_patch(Rectangle((15.15, 5.30), 7.20, 3.17, fc="#94A3B8", ec="#334155", lw=1.1, label="J400 USB-C 母座 (Z=5.30..8.47)"))
    # USB-C 插头舌片 + 护套包络
    ax2.add_patch(Rectangle((16.50, 5.585), 6.50, 2.60, fc="#38BDF8", ec="#0284C7", lw=1.0, ls="--", alpha=0.35, label="USB-C 插头舌片与外护套"))
    ax2.add_patch(Rectangle((22.35, 5.05), 3.50, 3.60, fc="#38BDF8", ec="#0284C7", lw=1.0, ls="--", alpha=0.35))
    # 底壳与上盖东侧墙剖面
    ax2.add_patch(Rectangle((8.0, 0.15), 15.0, 1.05, fc="#7DD3FC", ec="#0369A1", lw=1.0, alpha=0.65, label="底壳 tray (底厚 0.85..1.05 mm)"))
    ax2.add_patch(Rectangle((21.80, 0.15), 1.20, 4.95, fc="#7DD3FC", ec="#0369A1", lw=1.0, alpha=0.65))
    # 上盖顶壁（含 U17 0.16mm 浅槽 Z=9.26..10.10）
    cover_roof_pts = [
        (8.0, 9.10), (8.75, 9.10), (8.75, 9.26), (12.05, 9.26), (12.05, 9.10),
        (20.80, 9.10), (20.80, 8.68), (22.30, 8.68), (22.30, 8.80), (23.00, 8.80),
        (23.00, 10.10), (8.0, 10.10)
    ]
    ax2.add_patch(MplPolygon(cover_roof_pts, closed=True, fc="#BAE6FD", ec="#0284C7", lw=1.2, alpha=0.75, label="上盖 cover (顶壁 0.84..1.00 mm)"))
    ax2.set_xlim(8.0, 26.2)
    ax2.set_ylim(-0.3, 10.8)
    ax2.set_aspect("equal")
    ax2.set_xlabel("X (mm)")
    ax2.set_ylabel("Z (mm)")
    ax2.grid(True, ls="--", alpha=0.3)
    ax2.legend(loc="lower left", fontsize=7.0, framealpha=0.9)

    # --- 剖面 C-C：北端短生耳内凹弧槽、快拆弹簧棒织带圆筒、内置北走廊 2.4G FPC 天线与 R14/R15 软板通道 (YZ 剖面) ---
    ax3 = axes[2]
    ax3.set_facecolor("#FFFFFF")
    ax3.set_title("剖面 C-C (北端 YZ)：短耳堵防悬空版 (北耳仅凸 3.10mm, 底抬高至 Z=2.0)", fontsize=10.2, fontweight="bold")
    # 底壳北袋底板与内凹生耳墙（中段无顶棚，两侧小耳 Z=2.00..5.40 伸至 y=23.10）
    ax3.add_patch(Rectangle((14.0, 0.15), 5.70, 0.85, fc="#7DD3FC", ec="#0369A1", lw=1.0, alpha=0.7, label="底壳北底板 (y<=19.70, 厚 0.85 mm ≥ 0.80)"))
    ax3.add_patch(Rectangle((18.80, 1.00), 0.90, 5.60, fc="#7DD3FC", ec="#0369A1", lw=1.1, alpha=0.78, label="北内凹弧槽内墙 (y=18.80..19.70, 厚 0.90 mm)"))
    # 两侧短生耳凸耳外轮廓投影虚线 (|x|=11.15..13.35, y=19.70..23.10, Z=2.00..5.40)
    ax3.add_patch(Rectangle((19.70, 2.00), 3.40, 3.40, fc="#BAE6FD", ec="#0284C7", lw=1.2, ls="--", alpha=0.45, label="两侧短生耳小耳 (y<=23.10 仅凸3.1mm, 底Z=2.0防顶腕)"))
    ax3.add_patch(Rectangle((14.0, 6.60), 6.00, 3.50, fc="#BAE6FD", ec="#0284C7", lw=1.0, alpha=0.6, label="8001 全透明上盖 cover (北壁 y=20.00 无凸檐)"))
    # D17 板与主控板（北边均截止于 y=18.25）
    ax3.add_patch(Rectangle((14.0, 2.55), 4.25, 0.80, fc="#15803D", ec="#14532D", lw=1.0, label="D18 采集板 (北边 y=18.25)"))
    ax3.add_patch(Rectangle((14.0, 6.79), 4.25, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.0, label="主控板 R2 (北边 y=18.25)"))
    ax3.add_patch(Rectangle((16.10, 3.35), 1.94, 1.05, fc="#64748B", ec="#1E293B", lw=0.9, label="V4_FPC1/3 34P 座子 (y<=18.04)"))
    ax3.add_patch(Rectangle((16.10, 1.32), 1.94, 1.23, fc="#64748B", ec="#1E293B", lw=0.9))
    # 内置北侧无铜走廊 2.4 GHz FPC 天线 (y=18.42..18.62, Z=4.45..8.65)
    ax3.add_patch(Rectangle((18.35, 4.45), 0.35, 4.20, fc="#EC4899", ec="#9D174D", lw=1.3, label="2.4G FPC 天线 (20×4.2mm 贴北壁 y=18.8)"))
    # R14/R15 双片软板 180° 回折弧 + 下层北支出口
    ax3.add_patch(Rectangle((16.57, 1.02), 2.18, 2.88, fc="#F97316", ec="#C2410C", lw=1.1, alpha=0.55, label="R15 软板尾回折区 (y=16.57..18.75)"))
    ax3.add_patch(MplPolygon([(18.5, 1.02), (23.6, 1.20), (28.0, 1.85), (28.0, 2.05), (23.6, 1.38), (18.5, 1.18)],
                            closed=True, fc="#FB923C", ec="#C2410C", lw=1.1, label="下层 R15 北支软板 (Z=1.02..1.38)"))
    # 上层编织表带回折圆筒 (外径 Ø3.80 绕 y=21.65, z=3.70)
    theta_s = np.linspace(np.pi / 2, 3 * np.pi / 2, 48)
    s_oy = 21.65 + 1.90 * np.cos(theta_s)
    s_oz = 3.70 + 1.90 * np.sin(theta_s)
    s_iy = 21.65 + 0.92 * np.cos(theta_s[::-1])
    s_iz = 3.70 + 0.92 * np.sin(theta_s[::-1])
    strap_yz = (
        [(26.85, 5.60), (21.65, 5.60)]
        + list(zip(s_oy, s_oz))
        + [(21.65, 1.80), (26.85, 1.80), (26.85, 2.78), (21.65, 2.78)]
        + list(zip(s_iy, s_iz))
        + [(21.65, 4.62), (26.85, 4.62)]
    )
    ax3.add_patch(MplPolygon(strap_yz, closed=True, fc="#475569", ec="#0F172A", lw=1.2, alpha=0.82, label="22.04mm 编织带回折圆筒 (绕 Y=21.65, 无顶棚阻挡)"))
    # 快拆弹簧棒 Ø1.80 (中心 y=21.65, z=3.70)
    ax3.add_patch(Circle((21.65, 3.70), 0.90, fc="#E2E8F0", ec="#334155", lw=1.3, label="Ø1.80 快拆弹簧棒 (内移至 Y=21.65, Z=3.70)"))
    ax3.set_xlim(14.0, 28.5)
    ax3.set_ylim(-0.3, 11.45)
    ax3.set_aspect("equal")
    ax3.set_xlabel("Y (mm)")
    ax3.set_ylabel("Z (mm)")
    ax3.grid(True, ls="--", alpha=0.3)
    ax3.legend(loc="upper right", fontsize=6.3, framealpha=0.9)

    fig.suptitle(
        "OpenEMG V12 · C08B 8001 全透明外壳 R12 关键工程剖面核对（0 干涉 · 全壁厚 ≥ 0.84 mm）",
        fontsize=13.5,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = P / "preview-sections.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_exploded():
    """渲染三件套单实体 + 快拆弹簧棒与编织带回折圆筒爆炸装配图。"""
    tray = mdl.build_tray()
    cover = mdl.build_cover().translate((0, 0, 11.0))
    plunger = mdl.build_switch_plunger().translate((0, 0, 16.5))
    south_strap = mdl.build_woven_strap_loop(mdl.SOUTH_PIN_Y, is_north=False).translate((0, -9.0, 0))
    north_strap = mdl.build_woven_strap_loop(mdl.NORTH_PIN_Y, is_north=True).translate((0, 9.0, 0))
    sb_south = mdl.build_spring_bar(mdl.SOUTH_PIN_Y).translate((0, -9.0, 0))
    sb_north = mdl.build_spring_bar(mdl.NORTH_PIN_Y).translate((0, 9.0, 0))

    items = [
        ("底壳 tray (1 solid)", tray, (0.60, 0.82, 0.95, 0.68)),
        ("南快拆弹簧棒", sb_south, (0.75, 0.78, 0.82, 0.95)),
        ("北快拆弹簧棒", sb_north, (0.75, 0.78, 0.82, 0.95)),
        ("南编织表带回折圆筒 (非打印件)", south_strap, (0.34, 0.38, 0.44, 0.78)),
        ("北编织表带回折圆筒 (非打印件)", north_strap, (0.34, 0.38, 0.44, 0.78)),
        ("透明上盖 cover (1 solid)", cover, (0.76, 0.90, 0.98, 0.58)),
        ("楔面开关柱塞 switch_plunger (1 solid)", plunger, (0.12, 0.56, 0.88, 0.92)),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    for ax, mode, title, xlim, ylim in [
        (ax1, "iso", "A. R12 三件打印单实体 + 织带穿快拆弹簧棒 等轴测爆炸图", (-38, 38), (-32, 32)),
        (ax2, "yz", "B. R12 侧向 YZ 爆炸装配关系图（对齐 IMG_3797.MOV，无树脂端块）", (-42, 44), (-2, 29)),
    ]:
        ax.set_facecolor("#FFFFFF")
        for name, shape, rgba in items:
            v, f = tessellate_solid(shape, tol=0.14)
            add_mesh_to_ax(ax, v, f, rgba, mode=mode, edge_alpha=0.12, lw=0.3)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.grid(True, ls="--", alpha=0.25)
        ax.set_title(title, fontsize=12, fontweight="bold", color="#0F172A")

    ax2.annotate("3. 开关柱塞 switch_plunger (打印件 #3)\n   从盖下装入防脱槽，顶帽伸出盖孔", xy=(15.0, 25.5), xytext=(-38.0, 25.0),
                 fontsize=8.5, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1"))
    ax2.annotate("2. 透明上盖 cover (打印件 #2)\n   四角 R5.8 + 顶边大圆角 R3.0 + D401 透光", xy=(0.0, 19.5), xytext=(-38.0, 18.5),
                 fontsize=8.5, fontweight="bold", color="#0284C7", arrowprops=dict(arrowstyle="->", color="#0284C7"))
    ax2.annotate("1. 底壳 tray (打印件 #1)\n   南北内凹 C 形半圆槽 + Ø1.20 盲孔 + 下层软板槽", xy=(0.0, 3.5), xytext=(-38.0, 10.5),
                 fontsize=8.5, fontweight="bold", color="#0F172A", arrowprops=dict(arrowstyle="->", color="#0F172A"))
    ax2.annotate("南 22.04mm 编织带回折圆筒 + Ø1.8 快拆弹簧棒\n(直接卡入底壳南 22.30mm C形半圆槽盲孔，无树脂端块)", xy=(-31.5, 3.7), xytext=(-39.5, 2.2),
                 fontsize=8.3, fontweight="bold", color="#334155", arrowprops=dict(arrowstyle="->", color="#334155"))
    ax2.annotate("北 22.04mm 编织带回折圆筒 + Ø1.8 快拆弹簧棒\n(上层卡入盲孔，下层 R14 北支软板无干涉穿出)", xy=(33.5, 3.7), xytext=(6.0, 11.5),
                 fontsize=8.3, fontweight="bold", color="#334155", arrowprops=dict(arrowstyle="->", color="#334155"))

    fig.suptitle(
        "OpenEMG V12 · C08B 透明外壳 R12 嘉立创 3D 打印三件单实体 + 快拆织带分解图",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = P / "preview-exploded-lugs.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_whole_box_and_strap():
    """渲染整盒一体打印效果 + 22.04 mm 表带如何连接的四宫格总装说明图（preview-whole-box-strap.png）。"""
    whole = mdl.build_whole_box_onepiece()
    coupon = mdl.build_lug_test_coupon()
    south_strap = mdl.build_woven_strap_loop(mdl.SOUTH_PIN_Y, is_north=False)
    north_strap = mdl.build_woven_strap_loop(mdl.NORTH_PIN_Y, is_north=True)
    sb_south = mdl.build_spring_bar(mdl.SOUTH_PIN_Y)
    sb_north = mdl.build_spring_bar(mdl.NORTH_PIN_Y)

    v_whole, f_whole = tessellate_solid(whole, tol=0.13)
    v_coupon, f_coupon = tessellate_solid(coupon.translate((36.0, 12.0, 0.0)), tol=0.12)
    v_ss, f_ss = tessellate_solid(south_strap, tol=0.14)
    v_ns, f_ns = tessellate_solid(north_strap, tol=0.14)
    v_sbs, f_sbs = tessellate_solid(sb_south, tol=0.12)
    v_sbn, f_sbn = tessellate_solid(sb_north, tol=0.12)

    fig, axes = plt.subplots(2, 2, figsize=(16.5, 12.2), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    # Panel A: 整盒一体打印单实体 whole_box_onepiece 俯视等轴测 + 旁附 lug_test_22mm 快印测试件
    axA = axes[0, 0]
    axA.set_facecolor("#FFFFFF")
    add_mesh_to_ax(axA, v_sbs, f_sbs, (0.78, 0.80, 0.85, 0.95), mode="iso", edge_alpha=0.10)
    add_mesh_to_ax(axA, v_sbn, f_sbn, (0.78, 0.80, 0.85, 0.95), mode="iso", edge_alpha=0.10)
    add_mesh_to_ax(axA, v_ss, f_ss, (0.32, 0.36, 0.42, 0.72), mode="iso", edge_alpha=0.08)
    add_mesh_to_ax(axA, v_ns, f_ns, (0.32, 0.36, 0.42, 0.72), mode="iso", edge_alpha=0.08)
    add_mesh_to_ax(axA, v_whole, f_whole, (0.64, 0.85, 0.96, 0.72), mode="iso", edge_alpha=0.12, lw=0.28)
    add_mesh_to_ax(axA, v_coupon, f_coupon, (0.20, 0.72, 0.54, 0.82), mode="iso", edge_alpha=0.15, lw=0.30)
    axA.annotate(
        "① 整盒一体打印件 whole_box_onepiece.stl\n(1 solid, 46.0×45.75×10.69mm, 4850 mm³)\n短耳堵防悬空版：总长由51.6缩至45.75mm(-5.85mm)",
        xy=(-4.0, 6.0),
        xytext=(-37.0, 17.5),
        fontsize=8.5,
        fontweight="bold",
        color="#0369A1",
        arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="#E0F2FE", ec="#0284C7", lw=0.9),
    )
    axA.annotate(
        "② 局部快印件 lug_test_22mm.stl\n(28.4×6.15×6.61mm, 273 mm³)\n12分钟快测 22.04mm 表带短耳连接",
        xy=(22.0, 11.0),
        xytext=(10.0, 20.5),
        fontsize=8.3,
        fontweight="bold",
        color="#047857",
        arrowprops=dict(arrowstyle="->", color="#047857", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="#D1FAE5", ec="#059669", lw=0.9),
    )
    axA.set_xlim(-39, 43)
    axA.set_ylim(-23, 28)
    axA.set_aspect("equal")
    axA.grid(True, ls="--", alpha=0.25)
    axA.set_title("A. 整盒一体打印单实体 (whole_box_onepiece) + 局部快印测试件 (lug_test_22mm)", fontsize=11.5, fontweight="bold")

    # Panel B: 整盒一体打印单实体 仰视底面等轴测（展示南北短耳 + 盲孔 + 底部 6 电极孔 + 软板出口）
    axB = axes[0, 1]
    axB.set_facecolor("#FFFFFF")
    add_mesh_to_ax(axB, v_whole, f_whole, (0.64, 0.85, 0.96, 0.82), mode="iso_bottom", edge_alpha=0.14, lw=0.28)
    axB.annotate(
        "南北敞口内凹生耳槽 (宽 22.30mm, R=1.95mm, 无顶棚)\n+ 两侧 2.20mm 短耳 Ø1.20×1.20mm 盲孔 (底抬高至Z=2.0mm)",
        xy=(-8.0, 12.5),
        xytext=(-34.0, 20.0),
        fontsize=8.5,
        fontweight="bold",
        color="#B45309",
        arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="#FEF3C7", ec="#D97706", lw=0.9),
    )
    axB.annotate(
        "盒底 6 电极沉孔 + 东侧 USB-C 窗口\n(内部与外界完全贯通，无封闭死腔，光固化/FDM 均可直印)",
        xy=(0.0, -2.0),
        xytext=(-32.0, -21.5),
        fontsize=8.3,
        fontweight="bold",
        color="#0F172A",
        arrowprops=dict(arrowstyle="->", color="#0F172A", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="#F1F5F9", ec="#475569", lw=0.9),
    )
    axB.set_xlim(-36, 36)
    axB.set_ylim(-24, 26)
    axB.set_aspect("equal")
    axB.grid(True, ls="--", alpha=0.25)
    axB.set_title("B. 整盒底面仰视图（南北短耳 2.65/3.10mm + 中间零外凸敞口槽 + 下层软板通道）", fontsize=11.5, fontweight="bold")

    # Panel C: 如何跟 22.04 mm 表带连接（俯视 XY 装配三步法详解）
    axC = axes[1, 0]
    axC.set_facecolor("#FFFFFF")
    # 画表壳南端护耳与 22.30 mm 敞口内凹槽俯视截面
    axC.add_patch(Rectangle((-23.0, -20.00), 46.0, 6.80, fc="#BAE6FD", ec="#0284C7", lw=1.2, label="表壳南壁 (宽 46.0 mm, y=-20.00)"))
    # 左右紧凑短耳 x=-13.35..-11.15, y=-22.65..-19.25
    axC.add_patch(Rectangle((-13.35, -22.65), 2.20, 3.40, fc="#7DD3FC", ec="#0369A1", lw=1.3, label="左右短耳 (厚 2.20mm, 仅凸出盒壁 2.65mm)"))
    axC.add_patch(Rectangle((11.15, -22.65), 2.20, 3.40, fc="#7DD3FC", ec="#0369A1", lw=1.3))
    # 内凹弧槽虚线 (y=-20.00..-19.25)
    axC.add_patch(Rectangle((-11.15, -20.00), 22.30, 0.75, fc="#FFFFFF", ec="#0284C7", lw=1.0, ls="--", alpha=0.90, label="嵌入盒壁 0.75mm 内凹弧槽 (中段无顶棚)"))
    # 左右盲孔 x=-12.35..-11.15, x=11.15..12.35, y=-21.20±0.60
    axC.add_patch(Rectangle((-12.35, -21.80), 1.20, 1.20, fc="#FEF08A", ec="#CA8A04", lw=1.3, label="两侧 Ø1.20×1.20mm 盲孔 (外侧剩壁 1.00mm≥0.80)"))
    axC.add_patch(Rectangle((11.15, -21.80), 1.20, 1.20, fc="#FEF08A", ec="#CA8A04", lw=1.3))
    # 22.04 mm 编织表带回折圆筒 x=-11.02..+11.02, y=-26.40..-19.30
    axC.add_patch(Rectangle((-11.02, -26.40), 22.04, 7.10, fc="#475569", ec="#0F172A", lw=1.3, alpha=0.82, label="实测 22.04mm 表带圆筒 (单边余量 0.13mm)"))
    # 快拆弹簧棒管身 Ø1.80 (x=-11.02..+11.02, y=-22.10..-20.30) + 左右伸缩销头 (x=-11.92..+11.92) + 快拆拨杆
    axC.add_patch(Rectangle((-11.02, -22.10), 22.04, 1.80, fc="#E2E8F0", ec="#334155", lw=1.2, label="Ø1.80 快拆生耳弹簧棒 (Y=-21.20)"))
    axC.add_patch(Rectangle((-11.92, -21.60), 0.90, 0.80, fc="#F59E0B", ec="#B45309", lw=1.2))
    axC.add_patch(Rectangle((11.02, -21.60), 0.90, 0.80, fc="#F59E0B", ec="#B45309", lw=1.2))
    axC.add_patch(Circle((4.50, -23.00), 0.75, fc="#F59E0B", ec="#B45309", lw=1.2))

    axC.annotate("第 1 步：把快拆弹簧棒穿进\n22.04mm 表带端头圆筒套管", xy=(0.0, -24.5), xytext=(-22.0, -31.8),
                 fontsize=8.2, fontweight="bold", color="#0F172A", arrowprops=dict(arrowstyle="->", color="#0F172A", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#F1F5F9", ec="#64748B"))
    axC.annotate("第 2 步：左销头先插入左短耳盲孔\n(x = -11.15..-12.35 mm)", xy=(-11.75, -21.2), xytext=(-22.5, -17.5),
                 fontsize=8.2, fontweight="bold", color="#B45309", arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#FEF3C7", ec="#D97706"))
    axC.annotate("第 3 步：拨动快拆拨杆推入内凹槽松手，\n右销头弹入右短耳盲孔（中段无顶棚不顶表带）", xy=(11.5, -21.2), xytext=(1.5, -31.8),
                 fontsize=8.2, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#E0F2FE", ec="#0284C7"))

    axC.set_xlim(-24.0, 24.0)
    axC.set_ylim(-33.5, -12.5)
    axC.set_aspect("equal")
    axC.set_xlabel("X (mm) — 槽宽 22.30 mm 配 22.04 mm 表带（两侧短耳仅宽 2.20 mm）")
    axC.set_ylabel("Y (mm)")
    axC.grid(True, ls="--", alpha=0.3)
    axC.legend(loc="upper right", fontsize=6.8, framealpha=0.92)
    axC.set_title("C. 短耳堵版如何跟 22.04 mm 表带连接（俯视三步快拆卡入图）", fontsize=11.5, fontweight="bold")

    # Panel D: 侧视 YZ 剖面（展示短耳防悬空 + 上层快拆表带圆筒 vs 下层软板通道的分层关系）
    axD = axes[1, 1]
    axD.set_facecolor("#FFFFFF")
    axD.add_patch(Rectangle((15.0, 0.15), 4.70, 0.85, fc="#7DD3FC", ec="#0369A1", lw=1.0, alpha=0.75, label="盒底板 (y<=19.70, Z=0.15..1.00, 厚 0.85 mm)"))
    axD.add_patch(Rectangle((18.80, 1.00), 0.90, 9.10, fc="#7DD3FC", ec="#0369A1", lw=1.2, alpha=0.78, label="盒北壁内凹弧槽 (y=18.80..19.70, 中段无顶棚)"))
    axD.add_patch(Rectangle((19.70, 2.00), 3.40, 3.40, fc="#BAE6FD", ec="#0284C7", lw=1.2, ls="--", alpha=0.55, label="两侧短生耳小耳 (y<=23.10 仅凸3.1mm, Z=2.0..5.4)"))
    # 下层软板通道
    axD.add_patch(MplPolygon([(18.5, 1.02), (23.6, 1.20), (28.0, 1.85), (28.0, 2.05), (23.6, 1.38), (18.5, 1.18)],
                             closed=True, fc="#FB923C", ec="#C2410C", lw=1.2, label="下层：R14/R15 软板通道 (Z=1.02..1.38mm)"))
    # 上层表带圆筒 (绕 Y=21.65, Z=3.70)
    theta_s = np.linspace(np.pi / 2, 3 * np.pi / 2, 48)
    s_oy = 21.65 + 1.90 * np.cos(theta_s)
    s_oz = 3.70 + 1.90 * np.sin(theta_s)
    s_iy = 21.65 + 0.92 * np.cos(theta_s[::-1])
    s_iz = 3.70 + 0.92 * np.sin(theta_s[::-1])
    strap_yz = (
        [(28.0, 5.60), (21.65, 5.60)]
        + list(zip(s_oy, s_oz))
        + [(21.65, 1.80), (28.0, 1.80), (28.0, 2.78), (21.65, 2.78)]
        + list(zip(s_iy, s_iz))
        + [(21.65, 4.62), (28.0, 4.62)]
    )
    axD.add_patch(MplPolygon(strap_yz, closed=True, fc="#475569", ec="#0F172A", lw=1.2, alpha=0.85, label="上层：22.04mm 编织带圆筒 (绕 Y=21.65, Z=1.80..5.60)"))
    axD.add_patch(Circle((21.65, 3.70), 0.90, fc="#E2E8F0", ec="#334155", lw=1.3, label="Ø1.80 快拆生耳轴心 (Y=21.65, Z=3.70)"))
    axD.annotate("小耳底面抬高至 Z=2.00mm (距触点 2.0mm)\n中段无顶棚，彻底消除撑起表壳悬空", xy=(22.0, 2.0), xytext=(15.1, 8.2),
                 fontsize=8.2, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#E0F2FE", ec="#0284C7"))
    axD.annotate("下层软板平顺穿出 (Z=1.02..1.38)\n与表带圆筒底面留 0.42mm 垂直净空", xy=(22.0, 1.35), xytext=(20.5, -1.2),
                 fontsize=8.2, fontweight="bold", color="#C2410C", arrowprops=dict(arrowstyle="->", color="#C2410C", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#FFEDD5", ec="#EA580C"))
    axD.set_xlim(14.8, 28.8)
    axD.set_ylim(-1.8, 11.2)
    axD.set_aspect("equal")
    axD.set_xlabel("Y (mm)")
    axD.set_ylabel("Z (mm)")
    axD.grid(True, ls="--", alpha=0.3)
    axD.legend(loc="upper right", fontsize=7.0, framealpha=0.92)
    axD.set_title("D. 侧面剖视核对（上层快拆生耳连表带 + 下层出软板，0 干涉）", fontsize=11.5, fontweight="bold")

    fig.suptitle(
        "OpenEMG V12 · C08B 整盒一体打印效果 (whole_box_onepiece) 与 22.04 mm 表带连接核对",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = P / "preview-whole-box-strap.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")



def render_pcb_standoffs():
    """渲染两块 PCB 四角同位 M1.4 螺丝 + 板间塑料柱/铜柱锁紧方案四宫格详解图（preview-pcb-standoffs.png）。"""
    refs = dict(mdl.reference_internals())
    tray = mdl.build_tray()
    d18 = refs["D17_board"].translate((0, 0, 4.0))
    pillars = (
        refs["pcb_standoff_NW"]
        + refs["pcb_standoff_SW"]
        + refs["pcb_standoff_SE"]
    ).translate((0, 0, 8.0))
    pillar_ne = refs["pcb_standoff_NE"].translate((0, 0, 8.0))
    mcu = refs["MCU_board"].translate((0, 0, 12.5))
    top_screws = (
        refs["m14_screw_top_NW"]
        + refs["m14_screw_top_NE"]
        + refs["m14_screw_top_SW"]
        + refs["m14_screw_top_SE"]
    ).translate((0, 0, 16.5))
    bot_screws = (
        refs["m14_screw_bot_NW"]
        + refs["m14_screw_bot_NE"]
        + refs["m14_screw_bot_SW"]
        + refs["m14_screw_bot_SE"]
    ).translate((0, 0, 1.2))

    fig, axes = plt.subplots(2, 2, figsize=(16.8, 12.4), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    # Panel A: 双 PCB + 四角板间柱 + 上下 M1.4 螺丝 + 底壳沉台 3D 爆炸图
    axA = axes[0, 0]
    axA.set_facecolor("#FFFFFF")
    for shape, rgba in [
        (tray, (0.68, 0.86, 0.96, 0.55)),
        (bot_screws, (0.72, 0.76, 0.82, 0.96)),
        (d18, (0.08, 0.44, 0.25, 0.90)),
        (pillars, (0.85, 0.66, 0.16, 0.98)),
        (pillar_ne, (0.94, 0.94, 0.86, 0.98)),
        (mcu, (0.10, 0.30, 0.52, 0.90)),
        (top_screws, (0.72, 0.76, 0.82, 0.98)),
    ]:
        v, f = tessellate_solid(shape, tol=0.14)
        add_mesh_to_ax(axA, v, f, rgba, mode="iso", edge_alpha=0.10, lw=0.28)

    axA.annotate(
        "④ 顶面 4 颗 M1.4×2.5 螺丝 (Z=7.41..8.21)\n(NE 角用尼龙螺丝头 Ø2.4mm 避让 C53)",
        xy=(-10.0, 23.0),
        xytext=(-35.0, 26.5),
        fontsize=8.3,
        fontweight="bold",
        color="#0F172A",
        arrowprops=dict(arrowstyle="->", color="#0F172A", lw=1.1),
        bbox=dict(boxstyle="round,pad=0.25", fc="#F1F5F9", ec="#475569"),
    )
    axA.annotate(
        "③ 主控板 R2 (厚 0.62mm, Z=6.79..7.41)\n四角同位 (±19.05, ±15.75) Ø1.70 NPTH 孔",
        xy=(12.0, 17.5),
        xytext=(6.0, 25.5),
        fontsize=8.3,
        fontweight="bold",
        color="#1E3A8A",
        arrowprops=dict(arrowstyle="->", color="#1E3A8A", lw=1.1),
        bbox=dict(boxstyle="round,pad=0.25", fc="#DBEAFE", ec="#2563EB"),
    )
    axA.annotate(
        "② 板间 4 颗支柱 (高 3.44mm, Z=3.35..6.79)\n• NW/SW/SE：Ø2.50 塑料柱/黄铜柱 (M1.4×3.5)\n• NE 角：Ø2.6→Ø2.0 阶梯绝缘塑料柱 (避让 R209)",
        xy=(-12.0, 11.5),
        xytext=(-36.0, 13.5),
        fontsize=8.2,
        fontweight="bold",
        color="#B45309",
        arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.1),
        bbox=dict(boxstyle="round,pad=0.25", fc="#FEF3C7", ec="#D97706"),
    )
    axA.annotate(
        "① 采集板 D18 (厚 0.80mm, Z=2.55..3.35)\n+ 下方 4 颗 M1.4 螺丝落入底壳 Ø2.80 沉头定位台",
        xy=(10.0, 4.0),
        xytext=(2.0, -19.5),
        fontsize=8.2,
        fontweight="bold",
        color="#065F46",
        arrowprops=dict(arrowstyle="->", color="#065F46", lw=1.1),
        bbox=dict(boxstyle="round,pad=0.25", fc="#D1FAE5", ec="#059669"),
    )
    axA.set_xlim(-37, 37)
    axA.set_ylim(-22, 31)
    axA.set_aspect("equal")
    axA.grid(True, ls="--", alpha=0.25)
    axA.set_title("A. 双 PCB + 板间塑料柱/铜柱 (3.44mm) + M1.4 螺丝 3D 爆炸分解图", fontsize=11.5, fontweight="bold")

    # Panel B: NW / SW / SE 标准角（支持 M1.4×3.5 塑料柱/铜柱对锁 或 M1.4×6 长螺丝一穿到底）工程剖面
    axB = axes[0, 1]
    axB.set_facecolor("#FFFFFF")
    # 底壳底板 Z=0.15..1.20 + Ø4.50 支撑台 Z=0.95..2.55（扣 Ø2.80 沉孔 Z=1.65..2.55 与 Ø1.25 导孔 Z=1.00..1.65）
    tray_boss_poly = [
        (-3.2, 0.15), (3.2, 0.15), (3.2, 1.20), (2.25, 1.20), (2.25, 2.55),
        (1.40, 2.55), (1.40, 1.65), (0.625, 1.65), (0.625, 1.00),
        (-0.625, 1.00), (-0.625, 1.65), (-1.40, 1.65), (-1.40, 2.55),
        (-2.25, 2.55), (-2.25, 1.20), (-3.2, 1.20)
    ]
    axB.add_patch(MplPolygon(tray_boss_poly, closed=True, fc="#BAE6FD", ec="#0284C7", lw=1.3, label="底壳 Ø4.50 支撑台 (Z=0.95..2.55, 底壁实厚 0.85mm)"))
    # D18 采集板 Z=2.55..3.35 (Ø1.70 孔)
    axB.add_patch(Rectangle((-3.2, 2.55), 2.35, 0.80, fc="#15803D", ec="#052E16", lw=1.1, label="采集板 D18 (0.80mm, Z=2.55..3.35, Ø1.70孔)"))
    axB.add_patch(Rectangle((0.85, 2.55), 2.35, 0.80, fc="#15803D", ec="#052E16", lw=1.1))
    # 板间柱 Z=3.35..6.79 (OD Ø2.50, ID Ø1.45)
    axB.add_patch(Rectangle((-1.25, 3.35), 0.525, 3.44, fc="#F59E0B", ec="#B45309", lw=1.2, label="板间塑料柱/铜柱 (OD Ø2.50, H=3.44mm, M1.4×3.5)"))
    axB.add_patch(Rectangle((0.725, 3.35), 0.525, 3.44, fc="#F59E0B", ec="#B45309", lw=1.2))
    # 主控板 R2 Z=6.79..7.41 (Ø1.70 孔)
    axB.add_patch(Rectangle((-3.2, 6.79), 2.35, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.1, label="主控板 R2 (0.62mm, Z=6.79..7.41, Ø1.70孔)"))
    axB.add_patch(Rectangle((0.85, 6.79), 2.35, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.1))
    # 上方 M1.4×2.5 螺丝 (头 Ø2.50 Z=7.41..8.21, 杆 Z=5.20..7.41)
    top_screw_poly = [(-1.25, 8.21), (1.25, 8.21), (1.25, 7.41), (0.70, 7.41), (0.70, 5.20), (-0.70, 5.20), (-0.70, 7.41), (-1.25, 7.41)]
    axB.add_patch(MplPolygon(top_screw_poly, closed=True, fc="#CBD5E1", ec="#334155", lw=1.2, label="上下对锁 M1.4×2.5 螺丝 (头 Ø2.50×0.80mm)"))
    # 下方 M1.4×2.5 螺丝 (头 Ø2.50 Z=1.75..2.55, 杆 Z=2.55..4.95)
    bot_screw_poly = [(-1.25, 1.75), (1.25, 1.75), (1.25, 2.55), (0.70, 2.55), (0.70, 4.95), (-0.70, 4.95), (-0.70, 2.55), (-1.25, 2.55)]
    axB.add_patch(MplPolygon(bot_screw_poly, closed=True, fc="#CBD5E1", ec="#334155", lw=1.2))
    # 上盖内顶面 Z=8.88..9.10
    axB.add_patch(Rectangle((-3.2, 8.95), 6.4, 1.00, fc="#BAE6FD", ec="#0284C7", lw=1.1, alpha=0.70, label="透明上盖 cover (内顶余量 0.67mm)"))

    axB.annotate("顶螺帽与上盖净空 0.67 mm\n(Z=8.21 vs 盖内顶 Z=8.88)", xy=(-1.15, 8.35), xytext=(-5.05, 7.85),
                 fontsize=7.6, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#E0F2FE", ec="#0284C7"))
    axB.annotate("板间净高 3.44 mm (Z=3.35..6.79)\n配 M1.4×3.5mm 塑料柱/黄铜柱", xy=(1.28, 5.05), xytext=(2.05, 4.70),
                 fontsize=7.6, fontweight="bold", color="#B45309", arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#FEF3C7", ec="#D97706"))
    axB.annotate("底壳 Ø2.80 沉孔容底螺帽\n下设 Ø1.25 孔兼容 M1.4×6", xy=(-1.35, 2.05), xytext=(-5.05, 4.30),
                 fontsize=7.6, fontweight="bold", color="#0F172A", arrowprops=dict(arrowstyle="->", color="#0F172A", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#F1F5F9", ec="#475569"))
    axB.set_xlim(-5.25, 5.25)
    axB.set_ylim(-0.2, 10.6)
    axB.set_aspect("equal")
    axB.set_xlabel("径向 r (mm) — 孔心 (0, 0)")
    axB.set_ylabel("高度 Z (mm)")
    axB.grid(True, ls="--", alpha=0.3)
    axB.legend(loc="upper right", fontsize=6.6, framealpha=0.92)
    axB.set_title("B. NW / SW / SE 标准角锁紧剖面（双通 M1.4×3.5 柱对锁 & 长螺丝一穿到底双兼容）", fontsize=11.0, fontweight="bold")

    # Panel C: NE 东北角 (+19.05, +15.75) 阶梯绝缘塑料柱避让主控底面 R209 与顶面 C53 剖面
    axC = axes[1, 0]
    axC.set_facecolor("#FFFFFF")
    axC.add_patch(MplPolygon(tray_boss_poly, closed=True, fc="#BAE6FD", ec="#0284C7", lw=1.2))
    axC.add_patch(Rectangle((-3.2, 2.55), 2.35, 0.80, fc="#15803D", ec="#052E16", lw=1.1))
    axC.add_patch(Rectangle((0.85, 2.55), 2.35, 0.80, fc="#15803D", ec="#052E16", lw=1.1))
    # NE 阶梯绝缘柱 (下段 Z=3.35..5.95 OD Ø2.60 即 r=1.30; 上段 Z=5.95..6.79 OD Ø2.00 即 r=1.00)
    ne_left = [(-1.30, 3.35), (-0.725, 3.35), (-0.725, 6.79), (-1.00, 6.79), (-1.00, 5.95), (-1.30, 5.95)]
    ne_right = [(0.725, 3.35), (1.30, 3.35), (1.30, 5.95), (1.00, 5.95), (1.00, 6.79), (0.725, 6.79)]
    axC.add_patch(MplPolygon(ne_left, closed=True, fc="#FEF08A", ec="#CA8A04", lw=1.3, label="NE 阶梯绝缘塑料柱 pcb_standoff_ne (下Ø2.6→上Ø2.0)"))
    axC.add_patch(MplPolygon(ne_right, closed=True, fc="#FEF08A", ec="#CA8A04", lw=1.3))
    axC.add_patch(Rectangle((-3.2, 6.79), 2.35, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.1))
    axC.add_patch(Rectangle((0.85, 6.79), 2.35, 0.62, fc="#1E3A8A", ec="#0F172A", lw=1.1))
    # 主控板底面 R209 (0402 VBUS, 位于孔西侧 dx = -1.77..-1.25 mm, 焊盘/本体最近 r=1.02..1.25 mm, Z=6.28..6.79)
    axC.add_patch(Rectangle((-1.77, 6.28), 0.52, 0.51, fc="#EF4444", ec="#991B1B", lw=1.3, label="主控底面 R209 (VBUS, 距孔心 1.02..1.25mm, Z=6.28..6.79)"))
    # 主控板顶面 C53 (3V3, 焊盘距孔心 1.352mm, 3D体 1.487mm, Z=7.41..7.94)
    axC.add_patch(Rectangle((-1.90, 7.41), 0.52, 0.53, fc="#F97316", ec="#9A3412", lw=1.2, label="主控顶面 C53.1 (3V3, 距孔心 1.352mm, Z=7.41..7.94)"))
    # NE 顶面尼龙 M1.4 螺丝 (头径 Ø2.40 即 r=1.20 < 1.352mm)
    ne_top_screw = [(-1.20, 8.21), (1.20, 8.21), (1.20, 7.41), (0.70, 7.41), (0.70, 5.20), (-0.70, 5.20), (-0.70, 7.41), (-1.20, 7.41)]
    axC.add_patch(MplPolygon(ne_top_screw, closed=True, fc="#E2E8F0", ec="#475569", lw=1.2, label="NE 尼龙 M1.4 螺丝 (头径 Ø2.40 < C53 1.352×2)"))
    axC.add_patch(MplPolygon(bot_screw_poly, closed=True, fc="#CBD5E1", ec="#334155", lw=1.2))
    axC.add_patch(Rectangle((-3.2, 8.95), 6.4, 1.00, fc="#BAE6FD", ec="#0284C7", lw=1.1, alpha=0.70))

    axC.annotate("上段缩颈至 Ø2.00mm (r=1.00)\n避开 R209 (r=1.02) 且绝缘 VBUS", xy=(-1.05, 6.45), xytext=(-5.05, 4.45),
                 fontsize=7.6, fontweight="bold", color="#991B1B", arrowprops=dict(arrowstyle="->", color="#991B1B", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#FEE2E2", ec="#DC2626"))
    axC.annotate("尼龙螺帽 Ø2.40 (r=1.20)\n避开顶面 C53.1 (r=1.352)", xy=(-1.22, 7.75), xytext=(-5.05, 7.85),
                 fontsize=7.6, fontweight="bold", color="#9A3412", arrowprops=dict(arrowstyle="->", color="#9A3412", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#FFEDD5", ec="#EA580C"))
    axC.set_xlim(-5.25, 5.25)
    axC.set_ylim(-0.2, 10.6)
    axC.set_aspect("equal")
    axC.set_xlabel("X 方向相对 NE 孔心 (19.05, 15.75) 偏移 dx (mm)")
    axC.set_ylabel("高度 Z (mm)")
    axC.grid(True, ls="--", alpha=0.3)
    axC.legend(loc="upper right", fontsize=6.5, framealpha=0.92)
    axC.set_title("C. NE 东北角 (+19.05, +15.75) 阶梯绝缘塑料柱避让 R209 / C53 放大剖面", fontsize=11.0, fontweight="bold")

    # Panel D: 四角俯视位置与选型对照面板
    axD = axes[1, 1]
    axD.set_facecolor("#FFFFFF")
    axD.add_patch(Rectangle((-21.55, -18.25), 43.10, 36.50, fc="#E2E8F0", ec="#334155", lw=1.5, alpha=0.45, label="双板外框 (43.10 × 36.50 mm, R4.6)"))
    axD.add_patch(Rectangle((-13.00, -16.50), 20.90, 27.40, fc="#DBEAFE", ec="#2563EB", lw=1.2, ls="--", alpha=0.55, label="中部 302025 电池穿板窗 (20.9×27.4mm)"))
    axD.add_patch(Rectangle((8.32, -13.67), 12.04, 3.84, fc="#FEF3C7", ec="#D97706", lw=1.2, label="同位 J_AFE 20P 座 (y=-13.67..-9.83)"))
    axD.add_patch(Rectangle((9.09, -14.48), 10.50, 1.48, fc="#FDE68A", ec="#B45309", lw=1.1, ls=":", label="20P FFC 回折弧 (y=-14.48..-13.00)"))

    corners_info = [
        ("NW (-19.05, +15.75)", -19.05, 15.75, 2.062, "#15803D", "标准 Ø2.5×3.5 塑料/铜柱\n+ M1.4 螺丝 (净空 r=2.06mm)"),
        ("NE (+19.05, +15.75)", 19.05, 15.75, 1.251, "#DC2626", "必用阶梯绝缘塑料柱 (Ø2.6→Ø2.0)\n+ 尼龙 M1.4 螺丝 (避让 R209/VBUS)"),
        ("SW (-19.05, -15.75)", -19.05, -15.75, 3.797, "#15803D", "标准 Ø2.5×3.5 塑料/铜柱\n+ M1.4 螺丝 (净空 r=3.80mm)"),
        ("SE (+19.05, -15.75)", 19.05, -15.75, 2.043, "#15803D", "标准 Ø2.5×3.5 塑料/铜柱\n+ M1.4 螺丝 (距 FFC 弧 0.02+mm)"),
    ]
    for label, hx, hy, r_clear, col, desc in corners_info:
        axD.add_patch(Circle((hx, hy), r_clear, fc="none", ec=col, lw=1.1, ls="--"))
        axD.add_patch(Circle((hx, hy), 1.25, fc=col, ec="#0F172A", lw=1.2, alpha=0.75))
        axD.add_patch(Circle((hx, hy), 0.70, fc="#FFFFFF", ec="#0F172A", lw=0.9))
        tx = hx + (3.2 if hx < 0 else -17.5)
        ty = hy + (-4.2 if hy > 0 else 1.8)
        axD.annotate(f"{label}\n{desc}", xy=(hx, hy), xytext=(tx, ty),
                     fontsize=7.6, fontweight="bold", color=col,
                     arrowprops=dict(arrowstyle="->", color=col, lw=1.1),
                     bbox=dict(boxstyle="round,pad=0.22", fc="#FFFFFF", ec=col, lw=0.9))

    axD.set_xlim(-25.5, 25.5)
    axD.set_ylim(-22.0, 22.0)
    axD.set_aspect("equal")
    axD.set_xlabel("X (mm)")
    axD.set_ylabel("Y (mm)")
    axD.grid(True, ls="--", alpha=0.3)
    axD.legend(loc="center", fontsize=6.8, framealpha=0.92)
    axD.set_title("D. 四角同位安装孔 (±19.05, ±15.75) 俯视净空圆与支柱选型图", fontsize=11.0, fontweight="bold")

    fig.suptitle(
        "OpenEMG V12 · C08B 两块 PCB（D18 采集板 + 主控板 R2）四角 M1.4 螺丝 + 板间塑料柱/铜柱固定方案",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = P / "preview-pcb-standoffs.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_military_green_strap(meshes):
    """渲染 C08B R12 + R15 军绿色战术表带（14 节电极岛 + 28 颗盒外镀金电极 + 18mm Meta 间距）四宫格设计图（preview-military-green-strap.png）。"""
    strap_north = mdl.build_military_green_strap_north()
    strap_south = mdl.build_military_green_strap_south()
    strap_elecs, strap_fpc = mdl.build_strap_electrodes_and_fpc()

    v_sn, f_sn = tessellate_solid(strap_north, 0.16)
    v_ss, f_ss = tessellate_solid(strap_south, 0.18)
    v_se, f_se = tessellate_solid(strap_elecs, 0.14)
    v_sf, f_sf = tessellate_solid(strap_fpc, 0.18)

    fig, axes = plt.subplots(2, 2, figsize=(17.2, 12.8), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    # 军绿主色（RAL 6003 Olive Drab / Pantone 19-0516 TCX #4B5320）
    mg_rgba = (0.29, 0.35, 0.18, 0.95)
    mg_dark_rgba = (0.21, 0.26, 0.13, 0.96)

    # Panel A: 军绿色战术表带 + 8001 全透明表壳 3D 俯视等轴测全景图 + 右上角 170mm 环腕佩戴缩略图
    axA = axes[0, 0]
    axA.set_facecolor("#FFFFFF")
    full_draw_order = [
        (v_se, f_se, (0.86, 0.68, 0.18, 0.98)),
        (v_sf, f_sf, (0.88, 0.45, 0.12, 0.92)),
        (meshes["contacts"][0], meshes["contacts"][1], (0.86, 0.68, 0.18, 0.98)),
        (meshes["r14_fpc"][0], meshes["r14_fpc"][1], (0.88, 0.45, 0.12, 0.92)),
        (v_ss, f_ss, mg_rgba),
        (v_sn, f_sn, mg_rgba),
        (meshes["spring_bars"][0], meshes["spring_bars"][1], (0.78, 0.80, 0.84, 0.96)),
        (meshes["d17_board"][0], meshes["d17_board"][1], (0.08, 0.42, 0.24, 0.92)),
        (meshes["pcb_standoffs"][0], meshes["pcb_standoffs"][1], (0.86, 0.68, 0.20, 0.96)),
        (meshes["battery"][0], meshes["battery"][1], (0.38, 0.56, 0.78, 0.88)),
        (meshes["mcu_board"][0], meshes["mcu_board"][1], (0.10, 0.28, 0.48, 0.90)),
        (meshes["m14_screws"][0], meshes["m14_screws"][1], (0.76, 0.80, 0.85, 0.98)),
        (meshes["usb_j400"][0], meshes["usb_j400"][1], (0.72, 0.75, 0.78, 0.95)),
        (meshes["ufl_plug"][0], meshes["ufl_plug"][1], (0.85, 0.68, 0.12, 0.96)),
        (meshes["fpc_ant"][0], meshes["fpc_ant"][1], (0.90, 0.25, 0.55, 0.94)),
        (meshes["tray"][0], meshes["tray"][1], (0.74, 0.88, 0.96, 0.44)),
        (meshes["cover"][0], meshes["cover"][1], (0.82, 0.93, 0.99, 0.38)),
        (meshes["switch_plunger"][0], meshes["switch_plunger"][1], (0.16, 0.62, 0.90, 0.90)),
    ]
    for v, f, rgba in full_draw_order:
        add_mesh_to_ax(axA, v, f, rgba, mode="iso", edge_alpha=0.07, lw=0.22)

    axA.annotate(
        "北段军绿短带 + 一体战术日字扣环\n(strap_military_green_north, 内嵌 CH3–CH4 两岛)",
        xy=(24.0, 22.0),
        xytext=(-88.0, 34.0),
        fontsize=8.2,
        fontweight="bold",
        color="#2E381D",
        arrowprops=dict(arrowstyle="->", color="#2E381D", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#ECFCCB", ec="#4D7C0F"),
    )
    axA.annotate(
        "8001 全透明表壳 R12 + 22.04mm 快拆生耳头\n(内透蓝绿双 PCB、4 颗铜柱与 2.4G 天线)",
        xy=(0.0, 6.0),
        xytext=(-88.0, 12.0),
        fontsize=8.2,
        fontweight="bold",
        color="#0369A1",
        arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#E0F2FE", ec="#0284C7"),
    )
    axA.annotate(
        "南段军绿 12 节传感长带 + 防滑横纹穿扣尾舌\n(strap_military_green_south, CH5–CH16 节距 8.0mm)",
        xy=(-42.0, -28.0),
        xytext=(-88.0, -58.0),
        fontsize=8.0,
        fontweight="bold",
        color="#2E381D",
        arrowprops=dict(arrowstyle="->", color="#2E381D", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.25", fc="#ECFCCB", ec="#4D7C0F"),
    )
    axA.set_xlim(-92, 92)
    axA.set_ylim(-64, 48)
    axA.set_aspect("equal")
    axA.grid(True, ls="--", alpha=0.25)
    axA.set_title("A. 军绿色战术表带 (RAL 6003 #4B5320) + 8001 全透明表壳 3D 全景等轴测图", fontsize=11.5, fontweight="bold")

    # 在 Panel A 右下角空白处绘制 170mm 腕围环腕佩戴示意小窗（不遮挡东北侧北段表带）
    ax_inset = axA.inset_axes([0.61, 0.04, 0.37, 0.46])
    ax_inset.set_facecolor("#F8FAFC")
    theta = np.linspace(0, 2 * np.pi, 160)
    rx, ry = 28.5, 22.0
    # 手腕截面与外圈军绿表带环
    ax_inset.fill(rx * np.cos(theta), ry * np.sin(theta), fc="#FDE68A", ec="#D97706", lw=1.0, alpha=0.35)
    ax_inset.plot((rx + 2.2) * np.cos(theta), (ry + 2.2) * np.sin(theta), color="#4B5320", lw=6.5, solid_capstyle="round")
    # 顶部透明表壳
    ax_inset.add_patch(FancyBboxPatch((-18.0, ry - 1.0), 36.0, 8.2, boxstyle="round,pad=0.3,rounding_size=2.0",
                                      fc="#BAE6FD", ec="#0284C7", lw=1.3, alpha=0.88))
    # 环周 16 路镀金电极点
    for ang_deg in np.linspace(-210, 45, 16):
        rad = np.radians(ang_deg)
        ax_inset.add_patch(Circle(((rx + 0.5) * np.cos(rad), (ry + 0.5) * np.sin(rad)), 1.35, fc="#EAB308", ec="#713F12", lw=0.7))
    # 侧边北日字扣环
    ax_inset.add_patch(Rectangle((-rx - 4.8, 3.0), 3.6, 8.5, fc="#2E381D", ec="#0F172A", lw=1.1))
    ax_inset.text(0, 0, "155–230 mm 环腕佩戴\n16路电极贴合周向肌群", ha="center", va="center", fontsize=6.8, fontweight="bold", color="#1E293B")
    ax_inset.set_xlim(-38, 38)
    ax_inset.set_ylim(-29, 34)
    ax_inset.set_aspect("equal")
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.set_title("环腕佩戴截面 (155–230mm，模型)", fontsize=7.5, fontweight="bold", color="#2E381D", pad=2)

    # Panel B: 贴肤底面翻转朝上 3D 等轴测图（34 颗镀金电极：盒底 6 颗 16mm + 军绿表带 28 颗 18mm Meta 间距）
    axB = axes[0, 1]
    axB.set_facecolor("#FFFFFF")

    def flip_upside_down(v, f):
        vf = v.copy()
        vf[:, 1] = -vf[:, 1]
        vf[:, 2] = 10.5 - vf[:, 2]
        ff = f[:, [0, 2, 1]]
        return vf, ff

    bottom_draw_order = [
        (meshes["cover"][0], meshes["cover"][1], (0.82, 0.93, 0.99, 0.30)),
        (meshes["mcu_board"][0], meshes["mcu_board"][1], (0.10, 0.28, 0.48, 0.65)),
        (meshes["d17_board"][0], meshes["d17_board"][1], (0.08, 0.42, 0.24, 0.70)),
        (meshes["tray"][0], meshes["tray"][1], (0.74, 0.88, 0.96, 0.52)),
        (v_ss, f_ss, mg_dark_rgba),
        (v_sn, f_sn, mg_dark_rgba),
        (v_sf, f_sf, (0.92, 0.48, 0.12, 0.96)),
        (meshes["r14_fpc"][0], meshes["r14_fpc"][1], (0.92, 0.48, 0.12, 0.96)),
        (meshes["contacts"][0], meshes["contacts"][1], (0.95, 0.78, 0.12, 1.0)),
        (v_se, f_se, (0.95, 0.78, 0.12, 1.0)),
    ]
    for v, f, rgba in bottom_draw_order:
        vf, ff = flip_upside_down(v, f)
        add_mesh_to_ax(axB, vf, ff, rgba, mode="iso", edge_alpha=0.08, lw=0.22)

    axB.annotate(
        "盒底 6 颗镀金电极 (CH1–CH2 + EB1/EB2)\n保持 16.0mm 对内间距，100% 兼容 R12 底壳",
        xy=(0.0, 10.0),
        xytext=(-88.0, 26.0),
        fontsize=8.1,
        fontweight="bold",
        color="#B45309",
        arrowprops=dict(arrowstyle="->", color="#B45309", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.24", fc="#FEF3C7", ec="#D97706"),
    )
    axB.annotate(
        "南段 12 节电极岛 (CH5–CH16, 共 24 颗 Φ1.5×Φ0.8×2 黄铜触点)\n• 对内间距 18.0 mm (x = ±9.00 mm，对齐 Meta 专利)\n• 钉头贴软板 F 面焊盘、背面补强孔口点锡（先焊后装）",
        xy=(42.0, 26.0),
        xytext=(-2.0, -48.0),
        fontsize=7.9,
        fontweight="bold",
        color="#2E381D",
        arrowprops=dict(arrowstyle="->", color="#2E381D", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.24", fc="#ECFCCB", ec="#4D7C0F"),
    )
    axB.annotate(
        "北段 2 节电极岛 (CH3–CH4, 4 颗 Φ1.5×Φ0.8×2 黄铜触点)\n+ 北端一体日字穿带环扣 (内窗 21.6×3.0mm)",
        xy=(-26.0, -14.0),
        xytext=(-88.0, -44.0),
        fontsize=7.9,
        fontweight="bold",
        color="#1E293B",
        arrowprops=dict(arrowstyle="->", color="#1E293B", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.24", fc="#F1F5F9", ec="#475569"),
    )
    axB.set_xlim(-92, 92)
    axB.set_ylim(-56, 62)
    axB.set_aspect("equal")
    axB.grid(True, ls="--", alpha=0.25)
    axB.set_title("B. 贴肤底面翻转 3D 图：34 颗电极阵列（盒底 6 颗 16mm + 表带 28 颗 Φ1.5×Φ0.8×2mm 黄铜触点 18mm）", fontsize=11.2, fontweight="bold")

    # Panel C: 横向剖面 A-A (Y=SOUTH_ISLAND_YS[0]=-32.0 mm，穿过南段第 1 岛 CH5)：军绿表带内袋 + 21.20mm R15 软板 + Φ1.5×Φ0.8×2.0mm 黄铜阶梯触点
    axC = axes[1, 0]
    axC.set_facecolor("#FFFFFF")
    # 先焊后装叠层（全部取 build.py 常量）：钉头顶贴软板 F 面焊盘，软板下 TPU 0.35（整条内袋底，Mako 批准放宽）
    zb, zp0, zp1 = mdl.STRAP_BOTTOM_Z, mdl.STRAP_FPC_POCKET_Z_MIN, mdl.STRAP_FPC_POCKET_Z_MAX
    zf0, zf1, zr1, zt = mdl.STRAP_FPC_Z_MIN, mdl.STRAP_FPC_Z_MAX, mdl.STRAP_SOLDER_RECESS_Z_MAX, mdl.STRAP_BODY_Z_MAX
    zfc = zf0 + mdl.R15_FPC_T
    hw, rh, rr, rs = mdl.STRAP_BODY_W / 2, mdl.STRAP_CONTACT_HEAD_CBORE_D / 2, mdl.STRAP_CONTACT_SOLDER_RECESS_D / 2, mdl.STRAP_CONTACT_SHAFT_D / 2
    axC.add_patch(Rectangle((-hw, zp1), 2 * hw, zt - zp1, fc="#4B5320", ec="#1A2E05", lw=1.3,
                            label=f"军绿表带上层 (宽 {2 * hw:.2f}mm, 锡点腔顶壁 {zt - zr1:.2f}mm)"))
    axC.add_patch(Rectangle((-10.80, zt), 21.60, 0.30, fc="#3F471B", ec="#1A2E05", lw=1.1, label="战术防滑横肋 (高 0.30mm, 节距 4.0mm)"))
    for sign in (-1, 1):
        axC.add_patch(Rectangle((min(sign * 10.70, sign * hw), zb), hw - 10.70, zp1 - zb, fc="#4B5320", ec="#1A2E05", lw=1.2))
        for a, b2 in ((5.00, 9.00 - rh), (9.00 + rh, 10.70)):   # 软板下 0.35 TPU，中间让出 Ø1.66 头孔
            axC.add_patch(Rectangle((min(sign * a, sign * b2), zb), b2 - a, zp0 - zb, fc="#6B7A2E", ec="#1A2E05", lw=1.0,
                                    label=f"软板下 TPU {zp0 - zb:.2f}mm (整条内袋底, Mako 11-09 批准放宽)" if (sign < 0 and a == 5.00) else None))
        axC.add_patch(Rectangle((sign * 9.00 - rr, zp1), 2 * rr, zr1 - zp1, fc="#FFFFFF", ec="#1A2E05", lw=0.9))
    axC.add_patch(Rectangle((-10.60, zf0), 21.20, zfc - zf0, fc="#F97316", ec="#9A3412", lw=1.2,
                            label=f"R15 四层软板 (F 面朝皮肤, 厚 {mdl.R15_FPC_T}mm, Ø1.0 孔 + Ø1.8 焊盘)"))
    bx0, bx1 = mdl.R15_B_OVER_A_X
    axC.add_patch(Rectangle((-mdl.STRAP_B_RELIEF_HALF_X, zp1), 2 * mdl.STRAP_B_RELIEF_HALF_X, mdl.STRAP_B_RELIEF_Z_MAX - zp1, fc="#FFFFFF", ec="#1A2E05", lw=0.9))
    axC.add_patch(Rectangle((bx0, zf1), bx1 - bx0, mdl.R15_FPC_T, fc="#FDBA74", ec="#9A3412", lw=1.0, hatch="//",
                            label=f"R15 B 片走线带压在 A 南岛上 (内袋顶局部抬到 {mdl.STRAP_B_RELIEF_Z_MAX:.2f})"))
    axC.add_patch(Rectangle((-10.40, zfc), 20.80, zf1 - zfc, fc="#FBBF24", ec="#B45309", lw=1.0,
                            label=f"B 面 PI 补强 (厚 {mdl.R15_ISLAND_STIFF_T}mm, 盖住背面焊盘环, 只开 Ø1.0 孔)"))
    for ex in (-9.00, 9.00):
        solder_poly = [(ex - 0.50, zf1), (ex + 0.50, zf1), (ex + rs, zf1 + 0.30), (ex - rs, zf1 + 0.30)]
        axC.add_patch(MplPolygon(solder_poly, closed=True, fc="#94A3B8", ec="#475569", lw=0.9,
                                 label="背面补强孔口点锡 → 吸进孔壁到 F 面焊盘" if ex < 0 else None))
        h = mdl.STRAP_CONTACT_HEAD_H
        elec_poly = [(ex - 0.75, 0.00), (ex + 0.75, 0.00), (ex + 0.75, h), (ex + rs, h), (ex + rs, mdl.STRAP_CONTACT_TOTAL_H),
                     (ex - rs, mdl.STRAP_CONTACT_TOTAL_H), (ex - rs, h), (ex - 0.75, h)]
        axC.add_patch(MplPolygon(elec_poly, closed=True, fc="#EAB308", ec="#713F12", lw=1.3,
                                 label="Φ1.5×Φ0.8×2.0mm 黄铜触点 (钉头顶贴软板 F 面焊盘)" if ex < 0 else None))

    axC.annotate("", xy=(-9.00, -0.45), xytext=(9.00, -0.45), arrowprops=dict(arrowstyle="<->", color="#B45309", lw=1.5))
    axC.text(0.0, -0.68, "对内中心距 18.00 mm（Φ1.5 钉头内侧净距 16.50 mm）",
             ha="center", va="top", fontsize=8.0, fontweight="bold", color="#B45309")
    axC.annotate(f"先焊后装\n① 钉头贴软板 F 面焊盘，杆穿 Ø1.0 孔\n② 背面补强孔口点锡（杆伸出 {mdl.STRAP_CONTACT_TOTAL_H - zf1:.2f}mm，可剪短）\n③ 28 颗测通后整条塞进表带",
                 xy=(9.00, zf1 + 0.20), xytext=(3.40, 3.55),
                 fontsize=7.2, fontweight="bold", color="#713F12", arrowprops=dict(arrowstyle="->", color="#713F12", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#FEF3C7", ec="#D97706"))
    axC.annotate(f"中部 10.0mm 装入窗口\n(焊好的软板组件从这里塞进内袋 Z={zp0:.2f}..{zp1:.2f})", xy=(-3.0, 0.55), xytext=(-13.80, 3.55),
                 fontsize=7.2, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#E0F2FE", ec="#0284C7"))

    axC.set_xlim(-14.2, 14.2)
    axC.set_ylim(-1.35, 8.30)
    axC.set_aspect("equal")
    axC.set_xlabel("X (mm) — 表带体宽 23.20 mm（生耳连接头宽 22.04 mm）")
    axC.set_ylabel("Z (mm)")
    axC.grid(True, ls="--", alpha=0.3)
    axC.legend(loc="upper center", bbox_to_anchor=(0.5, 0.99), ncol=2, fontsize=6.4, framealpha=0.92)
    axC.set_title(f"C. 横向剖面 A-A (Y={mdl.SOUTH_ISLAND_YS[0]:g}mm)：先焊后装，钉头贴 R15 软板焊盘、背面补强孔口点锡", fontsize=10.8, fontweight="bold")

    # Panel D: 纵向剖面 B-B (南端生耳连接处至 CH5–CH6 电极岛) + 双制造路线对比
    axD = axes[1, 1]
    axD.set_facecolor("#FFFFFF")
    # 表壳南端底板、内凹生耳槽与两侧短耳 (Y=-22.65..-17.0, Z=0.15..6.60)
    axD.add_patch(Rectangle((-19.25, 0.15), 2.25, 0.85, fc="#BAE6FD", ec="#0284C7", lw=1.1, label="8001 全透明底壳 tray (底板 y>=-19.25, Z=0.15..1.00)"))
    axD.add_patch(Rectangle((-19.25, 1.40), 0.85, 5.20, fc="#7DD3FC", ec="#0284C7", lw=1.2, alpha=0.80, label="南内凹弧槽内墙 (y=-19.25..-18.40, 厚 0.85mm)"))
    axD.add_patch(Rectangle((-22.65, 2.00), 3.40, 3.40, fc="#BAE6FD", ec="#0284C7", lw=1.2, ls="--", alpha=0.45, label="两侧短生耳小耳 (y>=-22.65 仅凸2.65mm, Z=2.0..5.4)"))
    # Ø1.80 快拆弹簧棒 (Y=-21.20, Z=3.70)
    axD.add_patch(Circle((-21.20, 3.70), 0.90, fc="#E2E8F0", ec="#334155", lw=1.3, label="Ø1.80×22mm 快拆生耳弹簧棒 (内移至 Y=-21.20, Z=3.70)"))
    # 军绿表带生耳圆筒套管 (Y=-21.20, R=1.90) + 桥接段 (Y=-28.40..-21.20, Z=2.25..5.60) + 下沉台阶 + 带身 (Y=-46.0..-28.2, Z=0.15..2.90)
    strap_long_yz = [
        (-45.50, 2.90), (-29.60, 2.90), (-29.60, 5.60), (-19.30, 5.60),
        (-19.30, 1.80), (-23.10, 1.80), (-23.10, 2.25), (-28.20, 2.25),
        (-28.20, mdl.STRAP_FPC_POCKET_Z_MAX), (-45.50, mdl.STRAP_FPC_POCKET_Z_MAX)
    ]
    axD.add_patch(MplPolygon(strap_long_yz, closed=True, fc="#4B5320", ec="#1A2E05", lw=1.2, alpha=0.92, label="军绿表带生耳头 (22.04mm) + 桥接段 + 带身 (宽23.20mm)"))
    # 软板下 TPU (Z=0.15..0.50，整条内袋底，Mako 批准放宽到 0.35)
    axD.add_patch(Rectangle((-45.50, mdl.STRAP_BOTTOM_Z), mdl.SOUTH_ROOT_Y + 45.50, mdl.STRAP_FPC_POCKET_Z_MIN - mdl.STRAP_BOTTOM_Z, fc="#6B7A2E", ec="#1A2E05", lw=1.0, alpha=0.85))
    axD.add_patch(Circle((-21.20, 3.70), 0.92, fc="#FFFFFF", ec="#1A2E05", lw=1.0))
    axD.add_patch(Circle((-21.20, 3.70), 0.90, fc="#E2E8F0", ec="#334155", lw=1.2))
    # 下层 R15 软板从盒底 Z=1.02..1.32 穿出，下到表带内袋压在钉头顶（Z=0.50..0.853 含补强）
    # 出线槽外沿 SOUTH_FPC_EXIT_Y 起直线下坡，到表带根部 SOUTH_ROOT_Y 落到内袋底（build.py ramp）
    zt_box = mdl.FPC_BOX_Z + mdl.R15_FPC_T
    r15_path_yz = [
        (-17.00, mdl.FPC_BOX_Z), (mdl.SOUTH_FPC_EXIT_Y, mdl.FPC_BOX_Z), (mdl.SOUTH_ROOT_Y, mdl.STRAP_FPC_Z_MIN), (-45.50, mdl.STRAP_FPC_Z_MIN),
        (-45.50, mdl.STRAP_FPC_Z_MAX), (mdl.SOUTH_ISLAND_YS[0] + 2.8, mdl.STRAP_FPC_Z_MAX),
        (mdl.SOUTH_ROOT_Y, mdl.STRAP_FPC_Z_MIN + mdl.R15_FPC_T), (mdl.SOUTH_FPC_EXIT_Y, zt_box), (-17.00, zt_box)
    ]
    axD.add_patch(MplPolygon(r15_path_yz, closed=True, fc="#F97316", ec="#9A3412", lw=1.2, label="R15 软板 (盒出口 Z=1.02 下坡 → 根部进内袋压在钉头顶, 岛上含 B 面补强)"))
    for ey, lbl in [(y, f"CH{5 + i} ({y:g}mm)") for i, y in enumerate(mdl.SOUTH_ISLAND_YS[:2])]:
        axD.add_patch(Rectangle((ey - 0.90, mdl.STRAP_FPC_POCKET_Z_MAX), 1.80, mdl.STRAP_SOLDER_RECESS_Z_MAX - mdl.STRAP_FPC_POCKET_Z_MAX, fc="#FFFFFF", ec="#1A2E05", lw=0.8))
        axD.add_patch(Rectangle((ey - 0.75, 0.00), 1.50, mdl.STRAP_CONTACT_HEAD_H, fc="#EAB308", ec="#713F12", lw=1.2))
        axD.add_patch(Rectangle((ey - 0.40, mdl.STRAP_CONTACT_HEAD_H), 0.80, mdl.STRAP_CONTACT_SHAFT_H, fc="#EAB308", ec="#713F12", lw=1.1))
        axD.text(ey, -0.65, lbl, ha="center", va="top", fontsize=7.6, fontweight="bold", color="#713F12")

    axD.annotate("上层：22.04mm 军绿生耳圆筒\n卡入 22.30mm 敞口槽 (单边余 0.13mm, 无顶棚)", xy=(-21.2, 5.5), xytext=(-31.5, 7.2),
                 fontsize=7.5, fontweight="bold", color="#2E381D", arrowprops=dict(arrowstyle="->", color="#2E381D", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#ECFCCB", ec="#4D7C0F"))
    axD.annotate("Φ1.5×Φ0.8×2.0mm 黄铜触点\n(先焊在软板上，再整条塞进表带)", xy=(mdl.SOUTH_ISLAND_YS[0], 1.85), xytext=(-45.4, 5.2),
                 fontsize=7.5, fontweight="bold", color="#9A3412", arrowprops=dict(arrowstyle="->", color="#9A3412", lw=1.1),
                 bbox=dict(boxstyle="round,pad=0.22", fc="#FFEDD5", ec="#EA580C"))

    # 双制造路线说明卡片
    spec_text = (
        "【表带触点规格（Φ1.5*Φ0.8*2 mm 黄铜）与双制造路线】\n"
        "• 黄铜触点（28 颗，CH3–CH16）：头 Φ1.50×0.50 + 杆 Φ0.80×1.50 mm；钉头贴 R15 软板 F 面焊盘，背面补强孔口点锡，先焊后装\n"
        "• 路线 1（纺织快拆版）：22.04mm 军绿尼龙快拆带 + 底面 TPU 定位条，28 颗 Φ1.5×Φ0.8×2 黄铜钉先焊在 R15 软板上再装\n"
        "• 路线 2（3D直印版）：军绿 TPU 95A 打印 strap_military_green_north/south.stl (宽 23.20mm，Ø1.66 头孔 + Ø1.80 杆/锡点腔，软板下 TPU 0.35mm)"
    )
    axD.text(-45.5, 12.8, spec_text, fontsize=6.9, fontweight="bold", color="#0F172A", va="top",
             bbox=dict(boxstyle="round,pad=0.28", fc="#F8FAFC", ec="#4D7C0F", lw=1.1))

    axD.set_xlim(-46.2, -16.5)
    axD.set_ylim(-1.7, 13.4)
    axD.set_aspect("equal")
    axD.set_xlabel("Y (mm) — 南端生耳轴 Y=-21.20 mm，电极岛节距 8.00 mm")
    axD.set_ylabel("Z (mm)")
    axD.grid(True, ls="--", alpha=0.3)
    axD.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=6.5, framealpha=0.92)  # 放到图外，别挡出盒下坡段
    axD.set_title("D. 纵向剖面 B-B (南短生耳至 CH5–CH6) 与双制造路线规格", fontsize=11.0, fontweight="bold")

    fig.suptitle(
        "OpenEMG V12 · C08B 军绿色战术表带设计方案（适配短耳堵防悬空版 8001 全透明壳 + R15 18mm Meta 间距 34P 四层软板）",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = P / "preview-military-green-strap.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_short_lug_comparison():
    """渲染 STE A-F 六分区对照图：IMG_3799/3800.MOV 旧版长耳堵悬空问题 vs 新版短耳堵防悬空改型（preview-short-lugs-3799-3800.png）。"""
    whole = mdl.build_whole_box_onepiece()
    v_w, f_w = tessellate_solid(whole, 0.13)
    refs = dict(mdl.reference_internals())
    v_ss, f_ss = tessellate_solid(refs["south_woven_strap_loop"], 0.13)
    v_ns, f_ns = tessellate_solid(refs["north_woven_strap_loop"], 0.13)
    v_sb, f_sb = tessellate_solid(mdl.build_spring_bar(mdl.SOUTH_PIN_Y) + mdl.build_spring_bar(mdl.NORTH_PIN_Y), 0.12)

    fig, axes = plt.subplots(2, 2, figsize=(16.8, 12.2), dpi=180)
    fig.patch.set_facecolor("#F8FAFC")

    # Panel A: 旧版 (IMG_3799/3800.MOV) 环腕悬空机理 vs 新版短耳堵贴腕对比 (YZ 截面)
    axA = axes[0, 0]
    axA.set_facecolor("#FFFFFF")
    # 画手腕背侧弧面 (中心 y=0, z=-34, R=34.0 => 顶点 (0,0) 刚好贴底部电极 Z=0.0)
    yw = np.linspace(-28, 28, 200)
    zw_skin = -34.0 + np.sqrt(np.maximum(0.0, 34.0**2 - yw**2))
    axA.fill_between(yw, -7.0, zw_skin, color="#FDE68A", alpha=0.42, label="手腕背侧弧面 (腕宽 ~44 mm)")
    axA.plot(yw, zw_skin, color="#D97706", lw=2.0)

    # 上半部分/红色虚线：旧版长护耳 (Y=-24.80..+26.80, 总长 51.60 mm, 底面 Z=1.35 + 全宽顶棚 Z=6.76) 撑起表带导致悬空
    axA.add_patch(Rectangle((-24.80, 1.35), 4.80, 5.41, fc="none", ec="#DC2626", lw=1.8, ls="--", label="[旧] 旧版长护耳 (南-24.8/北+26.8, 总长51.6mm, 顶棚+低底面撑起悬空)"))
    axA.add_patch(Rectangle((20.00, 1.35), 6.80, 5.41, fc="none", ec="#DC2626", lw=1.8, ls="--"))
    axA.plot([20.0, 26.8, 28.5], [6.76, 6.76, 2.0], color="#DC2626", lw=1.8, ls=":", label="[旧] 旧版魔术贴回折被 26.8mm 顶棚向外顶开")

    # 实心蓝绿：新版表壳 (主体 Y=-20..+20, Z=0.15..10.10; 两侧短小耳 Y=-22.65..+23.10, Z=2.00..5.40, 中段 0 外凸)
    axA.add_patch(Rectangle((-20.00, 0.15), 40.00, 9.95, fc="#BAE6FD", ec="#0284C7", lw=1.5, alpha=0.80, label="[新] 新版表壳主体 (40.0mm, 中间表带槽 0.0mm 外凸)"))
    axA.add_patch(Rectangle((-22.65, 2.00), 2.65, 3.40, fc="#38BDF8", ec="#0369A1", lw=1.4, alpha=0.88, label="[新] 新版两侧短耳 (南凸2.65/北凸3.10mm, 底抬高至Z=2.0mm)"))
    axA.add_patch(Rectangle((20.00, 2.00), 3.10, 3.40, fc="#38BDF8", ec="#0369A1", lw=1.4, alpha=0.88))
    # 底部 6 电极 (y=±7.5, Z=0.00..0.85) 稳贴手腕
    for ey in (-7.5, 7.5):
        axA.add_patch(Rectangle((ey - 2.0, 0.00), 4.0, 0.75, fc="#EAB308", ec="#713F12", lw=1.2))
    # 新版生耳与表带自然下垂贴腕
    axA.add_patch(Circle((-21.20, 3.70), 1.90, fc="#475569", ec="#0F172A", lw=1.2, alpha=0.85, label="[新] 表带圆筒内移至 Y=-21.2/+21.65，直接顺手腕下折"))
    axA.add_patch(Circle((21.65, 3.70), 1.90, fc="#475569", ec="#0F172A", lw=1.2, alpha=0.85))
    axA.plot([21.65, 24.5, 26.8], [3.70, 0.5, -2.5], color="#15803D", lw=2.4)
    axA.plot([-21.20, -24.0, -26.5], [3.70, 0.5, -2.5], color="#15803D", lw=2.4)

    axA.annotate("旧版北耳凸出 6.80mm + 顶棚\n(IMG_3799/3800：把表带往外撑开，表底悬空)", xy=(25.5, 5.5), xytext=(6.5, 11.2),
                 fontsize=8.0, fontweight="bold", color="#DC2626", arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.24", fc="#FEE2E2", ec="#DC2626"))
    axA.annotate("新版北短耳仅凸 3.10mm (-54.4%)\n中段无顶棚 + 底面抬高至 Z=2.0mm 不顶手腕", xy=(21.65, 2.2), xytext=(-26.5, 11.2),
                 fontsize=8.0, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.24", fc="#E0F2FE", ec="#0284C7"))
    axA.set_xlim(-28.5, 29.5)
    axA.set_ylim(-5.5, 14.8)
    axA.set_aspect("equal")
    axA.set_xlabel("Y (mm) — 沿手腕前后方向")
    axA.set_ylabel("Z (mm)")
    axA.grid(True, ls="--", alpha=0.3)
    axA.legend(loc="lower center", fontsize=6.6, ncol=2, framealpha=0.92)
    axA.set_title("A. 为什么旧版耳堵会撑起手腕悬空 vs 新版短耳堵贴腕剖面对比", fontsize=11.2, fontweight="bold")

    # Panel B: 俯视 XY 外轮廓叠加对比（旧版 32.0×51.6mm 大护耳罩 vs 新版 26.7×45.75mm 两侧紧凑短耳）
    axB = axes[0, 1]
    axB.set_facecolor("#FFFFFF")
    # 主体 46x40
    axB.add_patch(Rectangle((-23.0, -20.0), 46.0, 40.0, fc="#E0F2FE", ec="#0284C7", lw=1.5, alpha=0.65, label="表壳主体 (46.0 × 40.0 mm 保持不变)"))
    # 旧版护耳红虚线框 (x=-16..16, y=-24.8..26.8)
    axB.add_patch(Rectangle((-16.0, 20.0), 32.0, 6.80, fc="#FEE2E2", ec="#DC2626", lw=1.6, ls="--", alpha=0.45, label="[旧] 旧版全宽护耳罩 (32.0mm宽, 北+6.80/南-4.80mm, 满封顶棚)"))
    axB.add_patch(Rectangle((-16.0, -24.80), 32.0, 4.80, fc="#FEE2E2", ec="#DC2626", lw=1.6, ls="--", alpha=0.45))
    # 新版两侧短耳实心框 (|x|=11.15..13.35, y=20.0..23.10 & -22.65..-20.0)
    for sx in (-13.35, 11.15):
        axB.add_patch(Rectangle((sx, 19.70), 2.20, 3.40, fc="#0284C7", ec="#0F172A", lw=1.3, label="[新] 新版紧凑短耳 (单边宽2.20mm, 北+3.10/南-2.65mm)" if sx < 0 else None))
        axB.add_patch(Rectangle((sx, -22.65), 2.20, 3.40, fc="#0284C7", ec="#0F172A", lw=1.3))
    # 新版生耳轴线
    axB.plot([-12.35, 12.35], [21.65, 21.65], color="#15803D", lw=2.2, label="[新] 新版生耳轴线 (北 Y=+21.65 / 南 Y=-21.20)")
    axB.plot([-12.35, 12.35], [-21.20, -21.20], color="#15803D", lw=2.2)
    axB.plot([-12.55, 12.55], [24.50, 24.50], color="#DC2626", lw=1.4, ls=":", label="[旧] 旧版生耳轴线 (北 Y=+24.50 / 南 Y=-22.50)")
    axB.plot([-12.55, 12.55], [-22.50, -22.50], color="#DC2626", lw=1.4, ls=":")

    axB.annotate("北端缩短 3.70 mm (-54.4%)\n且中间 22.30mm 槽顶棚完全取消 (外凸 0.0mm)", xy=(0.0, 21.65), xytext=(-21.5, 28.0),
                 fontsize=8.1, fontweight="bold", color="#0369A1", arrowprops=dict(arrowstyle="->", color="#0369A1", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.24", fc="#E0F2FE", ec="#0284C7"))
    axB.annotate("南端缩短 2.15 mm (-44.8%)\n护耳外宽由 32.0mm 收窄至 26.7mm (-5.3mm)", xy=(0.0, -21.20), xytext=(-21.5, -31.5),
                 fontsize=8.1, fontweight="bold", color="#047857", arrowprops=dict(arrowstyle="->", color="#047857", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.24", fc="#D1FAE5", ec="#059669"))
    axB.set_xlim(-26.0, 26.0)
    axB.set_ylim(-34.0, 33.5)
    axB.set_aspect("equal")
    axB.set_xlabel("X (mm)")
    axB.set_ylabel("Y (mm)")
    axB.grid(True, ls="--", alpha=0.3)
    axB.legend(loc="center", fontsize=7.0, framealpha=0.94)
    axB.set_title("B. 俯视 XY 外轮廓对比：总长由 51.60 mm 缩至 45.75 mm（缩短 5.85 mm）", fontsize=11.2, fontweight="bold")

    # Panel C: 新版短耳堵 3D 等轴测渲染图 (whole_box_onepiece + 22.04mm 快拆表带头)
    axC = axes[1, 0]
    axC.set_facecolor("#FFFFFF")
    add_mesh_to_ax(axC, v_sb, f_sb, (0.78, 0.80, 0.85, 0.96), mode="iso", edge_alpha=0.10)
    add_mesh_to_ax(axC, v_ss, f_ss, (0.29, 0.35, 0.18, 0.82), mode="iso", edge_alpha=0.09)
    add_mesh_to_ax(axC, v_ns, f_ns, (0.29, 0.35, 0.18, 0.82), mode="iso", edge_alpha=0.09)
    add_mesh_to_ax(axC, v_w, f_w, (0.64, 0.85, 0.96, 0.76), mode="iso", edge_alpha=0.13, lw=0.28)
    axC.set_xlim(-35, 35)
    axC.set_ylim(-23, 25)
    axC.set_aspect("equal")
    axC.grid(True, ls="--", alpha=0.25)
    axC.set_title("C. 新版短耳堵整盒单实体 (whole_box_onepiece.stl, 46.0×45.75×10.69mm) 俯视 3D 图", fontsize=11.2, fontweight="bold")

    # Panel D: 新版仰视底面 3D 图 + 关键尺寸对照卡片
    axD = axes[1, 1]
    axD.set_facecolor("#FFFFFF")
    add_mesh_to_ax(axD, v_w, f_w, (0.64, 0.85, 0.96, 0.84), mode="iso_bottom", edge_alpha=0.14, lw=0.28)
    table_txt = (
        "【修改前后核心尺寸对照 (对齐 IMG_3799 / IMG_3800.MOV)】\n"
        "• 整盒 Y 向总长：51.60 mm → 45.75 mm（缩短 5.85 mm）\n"
        "• 北端耳堵外凸：+6.80 mm → +3.10 mm（缩短 3.70 mm / -54.4%）\n"
        "• 南端耳堵外凸：+4.80 mm → +2.65 mm（缩短 2.15 mm / -44.8%）\n"
        "• 中段 22.30mm 表带槽顶棚外凸：6.80/4.80 mm → 0.00 mm（完全敞口不顶表带）\n"
        "• 耳堵外包总宽：32.00 mm (单边4.85) → 26.70 mm (单边2.20mm, 减窄 55%)\n"
        "• 耳堵底面高度：Z=0.15..1.35 mm → 抬高至 Z=2.00 mm（高出盒底触点 2.0mm）\n"
        "• 最小壁厚与干涉：全壁厚 ≥ 0.80 mm（盲孔外墙 1.00mm），269器件 0 干涉"
    )
    axD.text(-34.5, -8.5, table_txt, fontsize=7.6, fontweight="bold", color="#0F172A", va="top",
             bbox=dict(boxstyle="round,pad=0.32", fc="#F8FAFC", ec="#0284C7", lw=1.2))
    axD.set_xlim(-36, 36)
    axD.set_ylim(-26, 25)
    axD.set_aspect("equal")
    axD.grid(True, ls="--", alpha=0.25)
    axD.set_title("D. 新版仰视底面 3D 图与防悬空尺寸核对表", fontsize=11.2, fontweight="bold")

    fig.suptitle(
        "OpenEMG V12 · 针对 IMG_3799.MOV / IMG_3800.MOV 表壳凸出耳堵缩短防悬空改型总览",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = P / "preview-short-lugs-3799-3800.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def render_strap_trim_and_keeper():
    """舌片剪线 + 带圈：A 舌片俯视（贴肤面朝下看，剪线缺口按腕围标），B 带圈截面套「带身 + 舌片」两层。"""
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.25, 1]})
    # A：南带尾段俯视（X 横、Y 竖），带身到 −124.7，之后是 21.2 宽舌片；每道剪线两侧缺口 0.6 × 0.5
    y_top, y_tip, be = -110.0, mdl.SOUTH_TAIL_END_Y, mdl.SOUTH_BODY_END_Y
    axA.add_patch(Rectangle((-mdl.STRAP_BODY_W / 2, be), mdl.STRAP_BODY_W, y_top - be, fc="#4B5320", ec="#1A2E05", lw=1.0))
    axA.add_patch(Rectangle((-10.60, y_tip), 21.20, be + 0.6 - y_tip, fc="#8A9A5B", ec="#1A2E05", lw=1.0))
    for ex in mdl.EXT_ELECTRODE_XS:
        axA.add_patch(Circle((ex, min(mdl.SOUTH_ISLAND_YS)), 0.75, fc="#EAB308", ec="#713F12", lw=0.8))
    axA.text(0, min(mdl.SOUTH_ISLAND_YS), "CH16", ha="center", va="center", fontsize=8, color="white")
    for w, ym in sorted(mdl.TRIM_MARKS.items()):
        for sx in (-1, 1):
            x0 = 10.60 - mdl.TRIM_NOTCH_DEPTH if sx > 0 else -10.60
            axA.add_patch(Rectangle((x0, ym - mdl.TRIM_NOTCH_LEN / 2), mdl.TRIM_NOTCH_DEPTH, mdl.TRIM_NOTCH_LEN, fc="white", ec="#7C2D12", lw=0.8))
        axA.plot([-10.1, 10.1], [ym, ym], ls="--", lw=0.8, color="#7C2D12")
        axA.text(12.2, ym, f"{w} mm" + ("（155 也用）" if w == min(mdl.TRIM_MARKS) else ""), va="center", fontsize=8, color="#7C2D12")
    axA.text(-12.2, (be + y_top) / 2, "带身", ha="right", va="center", fontsize=9)
    axA.text(-12.2, (be + y_tip) / 2, f"舌片（宽 21.2）", ha="right", va="center", fontsize=9)
    axA.set_xlim(-24, 42); axA.set_ylim(y_tip - 3, y_top); axA.set_aspect("equal"); axA.grid(alpha=0.2)
    axA.set_xlabel("X (mm)"); axA.set_ylabel("Y (mm，南带沿长)")
    axA.set_title(f"A. 舌片剪线（5 mm 一档）：用不大于自己腕围的那道剪，过窗留约 20–{mdl.TRIM_TAIL_MM:g} mm（220 以上不剪）", fontsize=10.5, fontweight="bold")
    # B：带圈截面（打印时沿带长朝上）与两层叠放
    W, H, wall, sw = mdl.KEEPER_IN_W, mdl.KEEPER_IN_H, mdl.KEEPER_WALL, mdl.KEEPER_SKIN_WALL
    axB.add_patch(FancyBboxPatch((-W / 2 - wall, -H / 2 - sw), W + 2 * wall, H + wall + sw,
                                 boxstyle=f"round,pad=0,rounding_size={mdl.KEEPER_IN_R + sw}", fc="#2E381D", ec="#111", lw=1.2,
                                 label=f"带圈 壁 {wall:.2f}（贴肤侧 {sw:.2f}）、沿带长 {mdl.KEEPER_LEN:.1f}"))
    axB.text(0, -H / 2 - sw - 0.25, f"↓ 贴肤侧：只放在扣框和 CH16 钉头之间的无电极段（腕围 ≥{mdl.KEEPER_MIN_WRIST}）", ha="center", va="top", fontsize=8.5, color="#7C2D12")
    axB.add_patch(FancyBboxPatch((-W / 2, -H / 2), W, H, boxstyle=f"round,pad=0,rounding_size={mdl.KEEPER_IN_R}", fc="white", ec="#111", lw=1.0))
    y0 = -2.60
    axB.add_patch(Rectangle((-10.60, y0), 21.20, 2.60, fc="#6B7A2E", ec="#1A2E05", lw=1.0, label="下层：过窗前的舌片 21.20 × 2.60（含横纹）"))
    axB.add_patch(Rectangle((-10.60, 0.0), 21.20, 2.60, fc="#8A9A5B", ec="#1A2E05", lw=1.0, label="上层：翻回的舌片 21.20 × 2.60"))
    axB.annotate("", xy=(-W / 2, H / 2 + wall + 0.35), xytext=(W / 2, H / 2 + wall + 0.35), arrowprops=dict(arrowstyle="<->", lw=1.0))
    axB.text(0, H / 2 + wall + 0.55, f"内框 {W:.2f} × {H:.2f}（宽向每边空 0.30、厚向 0.20）", ha="center", va="bottom", fontsize=9)
    axB.set_xlim(-15, 15); axB.set_ylim(-6.5, 9.5); axB.set_aspect("equal"); axB.grid(alpha=0.25)
    axB.set_xlabel("X 带宽 (mm)"); axB.set_ylabel("叠层厚度 (mm)")
    axB.legend(loc="upper left", fontsize=7.5, ncol=1, framealpha=0.92)
    axB.set_title(f"B. 带圈截面：腕围 ≥{mdl.KEEPER_MIN_WRIST} 套两层舌片（紧配）", fontsize=10.5, fontweight="bold")
    fig.suptitle(f"C08B 军绿表带：舌片按腕围剪短（过窗留约 {mdl.TRIM_TAIL_MM:g} mm），带圈放在扣框旁无电极段（模型，未打印）", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_path = P / "preview-strap-trim-keeper.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved {out_path.name}")


def main():
    parts = {
        "tray": mdl.build_tray(),
        "cover": mdl.build_cover(),
        "switch_plunger": mdl.build_switch_plunger(),
    }
    refs = dict(mdl.reference_internals())
    data = json.loads(mdl.BOARDS_JSON.read_text())
    sw = next(p for p in data["mcu"] if p["n"] == "SW300")
    d401 = next(p for p in data["mcu"] if p["n"] == "D401")

    meshes = {
        "tray": tessellate_solid(parts["tray"], 0.14),
        "cover": tessellate_solid(parts["cover"], 0.14),
        "switch_plunger": tessellate_solid(parts["switch_plunger"], 0.10),
        "south_woven_strap_loop": tessellate_solid(refs["south_woven_strap_loop"], 0.14),
        "north_woven_strap_loop": tessellate_solid(refs["north_woven_strap_loop"], 0.14),
        "d17_board": tessellate_solid(refs["D17_board"], 0.16),
        "pcb_standoffs": tessellate_solid(
            refs["pcb_standoff_NW"]
            + refs["pcb_standoff_NE"]
            + refs["pcb_standoff_SW"]
            + refs["pcb_standoff_SE"],
            0.10,
        ),
        "mcu_board": tessellate_solid(refs["MCU_board"], 0.16),
        "m14_screws": tessellate_solid(
            refs["m14_screw_top_NW"]
            + refs["m14_screw_top_NE"]
            + refs["m14_screw_top_SW"]
            + refs["m14_screw_top_SE"]
            + refs["m14_screw_bot_NW"]
            + refs["m14_screw_bot_NE"]
            + refs["m14_screw_bot_SW"]
            + refs["m14_screw_bot_SE"],
            0.10,
        ),
        "battery": tessellate_solid(refs["battery_302025_max"], 0.20),
        "usb_j400": tessellate_solid(refs["MCU_USB_J400"], 0.16),
        "ffc20": tessellate_solid(refs["J_AFE_FFC20_loop"], 0.16),
        "r14_fpc": tessellate_solid(
            refs["R14_FPC_box"]
            + refs["R14_FPC_south_AB"]
            + refs["R14_FPC_north_tails"]
            + refs["R14_FPC_north_branch"],
            0.18,
        ),
        "contacts": tessellate_solid(
            refs["contact_-8_-7"]
            + refs["contact_8_-7"]
            + refs["contact_-8_7"]
            + refs["contact_8_7"]
            + refs["contact_0_-7"]
            + refs["contact_0_7"],
            0.14,
        ),
        "spring_bars": tessellate_solid(
            mdl.build_spring_bar(mdl.SOUTH_PIN_Y) + mdl.build_spring_bar(mdl.NORTH_PIN_Y),
            0.14,
        ),
        "sw300": tessellate_solid(mdl.box(*sw["x"], *sw["y"], *sw["z"]), 0.12),
        "ufl_plug": tessellate_solid(refs["MCU_J300_UFL_plug"], 0.10),
        "fpc_ant": tessellate_solid(refs["FPC_ANT_2G4"], 0.12),
        "d401_led": tessellate_solid(mdl.box(*d401["x"], *d401["y"], *d401["z"]), 0.10),
    }

    render_overview(meshes)
    render_sections()
    render_exploded()
    render_whole_box_and_strap()
    render_pcb_standoffs()
    render_military_green_strap(meshes)
    render_short_lug_comparison()
    render_strap_trim_and_keeper()


if __name__ == "__main__":
    main()
