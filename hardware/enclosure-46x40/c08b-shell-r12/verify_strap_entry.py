"""表带入口与软板长度核对（只读验证，不改设计）。

查两件 check.py 没覆盖的事：
1. R15 软板从盒子出来进表带那一段能不能穿过表带入口、整片外形放不放得进内袋。
   check.py 用手写方块代替软板（南段从 Y=-29.8、北段从 32.8 起，宽 ±10.6），
   入口那 1.4 mm 和 R15 真实外形（A 出盒带、北支、CH3 岛外缘）都没进干涉门。
2. 软板长度：盒底触点（E1/E2）和表带触点（E3/E5）在软板上的距离，与外壳/表带里孔位距离差多少。

数据全部读文件：R15 geometry.json 外形 + strap-a/b.kicad_pcb 触点坐标，外壳尺寸 import build.py，
入口剖面用已导出的表带 STL 打竖直射线。
"""
from pathlib import Path
import json
import math
import re
import struct

import numpy as np
import build123d as b

import build as mdl

HERE = Path(__file__).resolve().parent
R15 = HERE.parents[1] / "16ch-c08b-round/strap-fpc-r15"
FPC_T = mdl.R15_FPC_T                     # 0.203，check.py 已读板核对
BOX_FPC_Z = 1.02                          # 盒内软板底面（build.py R14_FPC_box 下表面）
POCKET_Z = mdl.STRAP_FPC_POCKET_Z_MIN     # 0.50：表带内袋底
TRAY_WALL_Y = mdl.BODY_L / 2              # 20.0：软板出盒外壁
# 表带入口实体（build.py step_down）与内袋/中缝开口，从 build.py 读（11-09 对齐 R15 后内袋从根部端面直通）
SOUTH_ENTRY = (mdl.SOUTH_ROOT_Y - 1.40, mdl.SOUTH_ROOT_Y)
NORTH_ENTRY = (mdl.NORTH_ROOT_Y, mdl.NORTH_ROOT_Y + 1.40)
SLOT_HALF_X = 5.00


def r15_contacts():
    out = {}
    for f in ("strap-a.kicad_pcb", "strap-b.kicad_pcb"):
        t = (R15 / f).read_text()
        for fp in re.split(r"\n\t\(footprint ", t)[1:]:
            ref = re.search(r'\(property "Reference" "(E[^"]+)"', fp)
            at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", fp)
            if ref and at:
                out[ref.group(1)] = (float(at.group(1)), float(at.group(2)))
    return out


def load_stl(p):
    raw = p.read_bytes()
    n = struct.unpack("<I", raw[80:84])[0]
    a = np.frombuffer(raw[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return a["v"].reshape(-1, 3, 3).astype(float)


def z_hits(T, x, y):
    """竖直射线 (x, y) 与三角面的全部交点 Z（Möller–Trumbore）。"""
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0, 0, 1.0])
    o = np.array([x, y, -10.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    ok = np.abs(a) > 1e-12
    f = np.where(ok, 1 / np.where(ok, a, 1), 0)
    s = o - v0
    u = f * (s * h).sum(1)
    q = np.cross(s, e1)
    w = f * (q @ d)
    t = f * (e2 * q).sum(1)
    m = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)
    return sorted(set(np.round(t[m] - 10, 4)))


def free_gap(T, x, y, zlo, zhi):
    """(x, y) 处 Z∈[zlo, zhi] 内最大的空隙高度（射线交点成对为实体段）。"""
    # 射线落在竖直侧壁/棱上会得到奇数个交点：挪开 0.1 µm 级避开退化
    hs = z_hits(T, x + 1.3e-4, y + 1.7e-4)
    assert len(hs) % 2 == 0, (x, y, hs)
    pts = [zlo]
    for z0, z1 in zip(hs[::2], hs[1::2]):
        if z1 <= zlo or z0 >= zhi:
            continue
        pts += [max(z0, zlo), min(z1, zhi)]
    pts.append(zhi)
    return max(pts[i + 1] - pts[i] for i in range(0, len(pts), 2))


def rect(x0, x1, y0, y1):
    return b.Pos((x0 + x1) / 2, (y0 + y1) / 2) * b.Rectangle(x1 - x0, y1 - y0)


def area(f):
    return sum(q.area for q in f.faces()) if f else 0.0


def outside_opening(outline, c, y_lo, y_hi, entry, pocket_end, pocket_x):
    """R15 外形映射到表带坐标（X = y − 50，Y = c − x），裁到表带 Y 段，减去内袋+中缝开口，剩下的就是压进 TPU 的部分。
    内袋和中缝都从根部端面外 0.1 起（build.py fpc_pocket）。"""
    face = b.Polygon(*[(p[1] - 50.0, c - p[0]) for p in outline], align=None)
    clip = face & rect(-30, 30, y_lo, y_hi)
    if entry[0] < 0:
        root = entry[1] + 0.10
        opening = rect(pocket_x[0], pocket_x[1], pocket_end, root) + rect(-SLOT_HALF_X, SLOT_HALF_X, pocket_end, root)
    else:
        root = entry[0] - 0.10
        opening = rect(pocket_x[0], pocket_x[1], root, pocket_end) + rect(-SLOT_HALF_X, SLOT_HALF_X, root, pocket_end)
    rest = clip - opening
    # 分开统计：入口段（step_down 那 1.4 mm）和内袋段（侧壁 + 末端墙）
    entry_area = area(rest & rect(-30, 30, entry[0], entry[1])) if rest else 0.0
    wall_area = area(rest) - entry_area
    pieces = []
    for q in (rest.faces() if rest else []):
        bb = q.bounding_box()
        if q.area > 1e-4:
            pieces.append({"area_mm2": round(q.area, 4),
                           "x": [round(bb.min.X, 3), round(bb.max.X, 3)],
                           "y": [round(bb.min.Y, 3), round(bb.max.Y, 3)]})
    return round(area(rest), 4), round(entry_area, 4), round(wall_area, 4), pieces


def main():
    g = json.loads((R15 / "geometry.json").read_text())
    bands = g["bands"]
    E = r15_contacts()
    X = lambda yr: yr - 50.0              # 表带/盒 X = y_R15 − 50：盒底 6 触点落在 tray 6 孔上；不镜像的依据是 F 面朝皮肤（变换行列式 +1）和北支出口槽只开在 −X 侧（独立复核核过）

    # ---- 1. 长度：盒内映射 vs 表带映射 ----
    # 盒底触点在 build.py 里是 (±8, ±7.5)；E1 在北 (+7.5)、E2 在南 (−7.5)
    c_box_e1 = 7.5 + E["E1P"][0]
    c_box_e2 = -7.5 + E["E2P"][0]
    c_south = mdl.SOUTH_ISLAND_YS[0] + E["E5P"][0]
    c_north = mdl.NORTH_ISLAND_YS[0] + E["E3P"][0]
    # 平放时软板最省长度的走法：盒内 Z=1.02 平走到盒外壁，再直线降到入口处内袋底 0.50。
    # 下降多走的那点路程要加到差值上（软板不能拉长）。
    def extra(dy):
        return math.hypot(dy, BOX_FPC_Z - POCKET_Z) - dy
    south_short = (c_box_e2 - c_south) + extra(-TRAY_WALL_Y - SOUTH_ENTRY[1])
    north_short = (c_north - c_box_e1) + extra(NORTH_ENTRY[0] - TRAY_WALL_Y)
    length = {
        "mapping_box_c_from_E1P_E2P": [c_box_e1, c_box_e2],
        "mapping_strap_south_c_from_E5P": c_south,
        "mapping_strap_north_c_from_E3P": c_north,
        "south_fpc_short_flat_mm": round(south_short, 3),
        "north_fpc_short_flat_mm": round(north_short, 3),
        "head_hole_radial_clearance_mm": round((mdl.STRAP_CONTACT_HEAD_CBORE_D - mdl.STRAP_CONTACT_HEAD_D) / 2, 3),
    }

    # 生耳处表带朝皮肤下弯多少度能吃掉差值（估算：软板在盒外壁 Z=1.02 处固定，
    # 表带绕弹簧棒 (PIN_Y, PIN_Z) 刚体转动，入口点到盒壁的直线距离缩短量 = 差值）
    def bend_needed(pin_y, entry_y, short, sign):
        wall = (sign * TRAY_WALL_Y, BOX_FPC_Z)
        p = (entry_y, POCKET_Z)
        v = (p[0] - pin_y, p[1] - mdl.PIN_Z)
        d0 = math.dist(wall, p)
        for k in range(0, 901):
            # 远端朝皮肤一侧（−Z）转：南端在 (Y,Z) 平面逆时针、北端顺时针
            phi = math.radians(k / 10) * (-sign)
            c, s = math.cos(phi), math.sin(phi)
            q = (pin_y + v[0] * c - v[1] * s, mdl.PIN_Z + v[0] * s + v[1] * c)
            if d0 - math.dist(wall, q) >= short:
                return round(k / 10, 1)
        return None

    length["south_bend_deg_to_absorb_est"] = bend_needed(mdl.SOUTH_PIN_Y, SOUTH_ENTRY[0], south_short, -1)
    length["north_bend_deg_to_absorb_est"] = bend_needed(mdl.NORTH_PIN_Y, NORTH_ENTRY[1], north_short, +1)

    # ---- 2. 入口剖面：射线逐点找能过 0.203 软板的空隙（Z 0.15 表带底面..2.25 生耳桥底）----
    Ts = load_stl(HERE / "strap_military_green_south.stl")
    Tn = load_stl(HERE / "strap_military_green_north.stl")
    segs = {
        "south_A_band": (X(bands["A_BAND"][0]), X(bands["A_BAND"][1]), Ts, SOUTH_ENTRY),
        "south_B_band": (X(bands["B_BAND"][0]), X(bands["B_BAND"][1]), Ts, SOUTH_ENTRY),
        "north_branch": (X(bands["NORTH"][0]), X(bands["NORTH"][1]), Tn, NORTH_ENTRY),
    }
    profile = {}
    for name, (x0, x1, T, (ya, yb)) in segs.items():
        blocked = []
        xs = np.round(np.arange(x0, x1 + 1e-9, 0.05), 3)
        for x in xs:
            gmin = min(free_gap(T, float(x), float(y), mdl.STRAP_BOTTOM_Z, 2.25) for y in np.arange(ya + 0.05, yb - 0.05 + 1e-9, 0.1))
            if gmin < FPC_T:
                blocked.append(float(x))
        profile[name] = {
            "x_range": [round(x0, 3), round(x1, 3)],
            "samples": len(xs),
            "blocked_samples": len(blocked),
            "blocked_x": [blocked[0], blocked[-1]] if blocked else None,
        }
    # 阳性对照：中缝中心 X=0 必须能过；阴性对照：内袋外 X=11.2 必须过不去
    ctrl_open = min(free_gap(Ts, 0.0, y, mdl.STRAP_BOTTOM_Z, 2.25) for y in np.arange(-29.55, -28.25, 0.1))
    ctrl_wall = min(free_gap(Ts, 11.2, y, mdl.STRAP_BOTTOM_Z, 2.25) for y in np.arange(-29.55, -28.25, 0.1))
    # 北段阴性对照：内袋 −X 侧外（−11.5，侧壁 −11.95..−11.15 里）必须过不去
    ctrl_wall_n = min(free_gap(Tn, -11.5, y, mdl.STRAP_BOTTOM_Z, 2.25)
                      for y in np.arange(NORTH_ENTRY[0] + 0.05, NORTH_ENTRY[1] - 0.05 + 1e-9, 0.1))

    # ---- 3. R15 真实外形 vs 内袋+中缝开口（二维，表带坐标）----
    a_out, b_out = g["a"]["outline"], g["b"]["outline"]
    south_lo, north_hi = -126.0, 48.0
    overlap = {
        "south_A": outside_opening(a_out, c_south, south_lo, SOUTH_ENTRY[1], SOUTH_ENTRY, mdl.SOUTH_POCKET_END_Y, mdl.SOUTH_POCKET_X),
        "south_B": outside_opening(b_out, c_south, south_lo, SOUTH_ENTRY[1], SOUTH_ENTRY, mdl.SOUTH_POCKET_END_Y, mdl.SOUTH_POCKET_X),
        "north_A": outside_opening(a_out, c_north, NORTH_ENTRY[0], north_hi, NORTH_ENTRY, mdl.NORTH_POCKET_END_Y, mdl.NORTH_POCKET_X),
    }
    overlap = {k: {"area_outside_opening_mm2": v[0], "in_entry_mm2": v[1], "in_pocket_walls_mm2": v[2], "pieces": v[3]}
               for k, v in overlap.items()}
    # 自检：把开口放大到 ±11.6 全宽、入口全开，剩余应为 0（证明数字来自开口尺寸，不是映射错位）
    wide = {}
    for k, (outl, c, lo, hi) in {"south_A": (a_out, c_south, south_lo, SOUTH_ENTRY[1]),
                                 "south_B": (b_out, c_south, south_lo, SOUTH_ENTRY[1]),
                                 "north_A": (a_out, c_north, NORTH_ENTRY[0], north_hi)}.items():
        face = b.Polygon(*[(p[1] - 50.0, c - p[0]) for p in outl], align=None) & rect(-30, 30, lo, hi)
        wide[k] = round(area(face - rect(-12.0, 12.0, lo - 1, hi + 1)), 4)

    res = {
        "fpc_length": length,
        "entry_ray_profile": profile,
        "entry_ray_controls": {"slot_center_x0_min_gap_mm": round(ctrl_open, 3), "outside_pocket_x11p2_min_gap_mm": round(ctrl_wall, 3),
                               "north_outside_pocket_xm11p5_min_gap_mm": round(ctrl_wall_n, 3)},
        "r15_outline_vs_strap_opening": overlap,
        "control_full_width_opening_residual_mm2": wide,
        "verdict": {
            "south_entry_blocks_A_band": profile["south_A_band"]["blocked_samples"] > 0,
            "south_entry_blocks_B_band": profile["south_B_band"]["blocked_samples"] > 0,
            "north_entry_blocks_branch": profile["north_branch"]["blocked_samples"] > 0,
            "fpc_into_pocket_walls": {k: v["in_pocket_walls_mm2"] > 0 for k, v in overlap.items()},
            "flat_fpc_short_exceeds_head_clearance": min(south_short, north_short) > length["head_hole_radial_clearance_mm"],
            "controls_ok": ctrl_open >= FPC_T and ctrl_wall < FPC_T and ctrl_wall_n < FPC_T and all(v == 0 for v in wide.values()),
        },
    }
    (HERE / "verify-strap-entry.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
