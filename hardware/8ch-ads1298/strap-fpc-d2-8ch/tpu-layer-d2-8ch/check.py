"""D2-8CH 表带电极层全套门禁：
1. 0.5 mm 步进三层网格全扫 + 12 孔环探 + 孔间/路间/端头壁厚 + 防翻面切角 + 单实体包围盒；
2. 独立解析源板 strap-d2-8ch.kicad_pcb（不信 geometry.json 缓存），按右手系验证 12 颗 F.Cu 串阻落槽与 12 颗铜片同心；
3. 导入满载 3D 实心装配体 strap-d2-8ch-3d.step（逐实体刚体旋转变换，严禁 Compound 整体搬移），在垫 0.10 mm 9448A 与 0.00 mm 压平贴死两种工况下验证实心三维布尔干涉 = 0.0 mm³；
4. 33 项必败反例（17 项参数越界、10 项局部针孔/沉孔/凹坑、槽镜像、5 项三维实心反例：X 镜像、左右/南北翻面、孔偏移、漏挖槽）必须全部报红。
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import sys
from pathlib import Path
import build123d as b
import build as m

HERE = Path(__file__).resolve().parent
STEP_FPC_3D = m.FPC_DIR / "strap-d2-8ch-3d.step"
Z_F_STEP = 0.161   # strap-d2-8ch-3d.step 中 F.Cu 表面 Z 坐标

EXPECT = {
    "PN": 18.0,
    "PITCH": 8.0,
    "DISC_D": 6.0,
    "DISC_T": 2.0,
    "NORTH_YS": (34.0, 42.0),
    "SOUTH_YS": (-32.0, -40.0, -48.0, -56.0),
}


def ins(p, x: float, y: float, z: float) -> bool:
    return p.is_inside(b.Vector(x, y, z))


def ring(r: float, n: int = 16) -> list[tuple[float, float]]:
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def grid(p, ys: tuple[float, ...], P=m, step: float = 0.5) -> list[str]:
    bad: list[str] = []
    lo, hi = P.span(ys)
    holes = [(x, y) for y in ys for x in (-P.PN / 2, P.PN / 2)]
    pk = P.pockets(ys)
    nx, ny = int(P.LAYER_W / step), int((hi - lo) / step)
    for i in range(1, nx):
        x = -P.LAYER_W / 2 + i * step
        for j in range(1, ny):
            y = lo + j * step
            d = min(math.hypot(x - hx, y - hy) for hx, hy in holes)
            if x > P.LAYER_W / 2 - P.KEY - 0.3 and y > hi - P.KEY - 0.3:
                continue
            inq = [q for q in pk if q[0] - 0.1 < x < q[1] + 0.1 and q[2] - 0.1 < y < q[3] + 0.1]
            if inq:
                if not [q for q in inq if q[0] + 0.1 < x < q[1] - 0.1 and q[2] + 0.1 < y < q[3] - 0.1]:
                    continue
                if any(ins(p, x, y, z) for z in (0.05, P.RES_H + 0.05)):
                    bad.append(f"串阻槽不够深/有料 ({x:.1f},{y:.1f})")
                    return bad
                if not ins(p, x, y, P.LAYER_T - 0.05):
                    bad.append(f"串阻槽打穿 ({x:.1f},{y:.1f})")
                    return bad
                continue
            if d < P.DISC_D / 2 + 0.1:
                if any(ins(p, x, y, z) for z in (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)):
                    bad.append(f"铜片位置有料 ({x:.1f},{y:.1f})")
                    return bad
            elif d > P.hole_d() / 2 + 0.1:
                if not all(ins(p, x, y, z) for z in (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)):
                    bad.append(f"该实的地方空了 ({x:.1f},{y:.1f})")
                    return bad
    return bad


def probe(p, ys: tuple[float, ...], P=m) -> list[str]:
    bad = grid(p, ys, P)
    zs = (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)
    for y in ys:
        for x in (-P.PN / 2, P.PN / 2):
            for z in zs:
                if any(ins(p, x + dx, y + dy, z) for dx, dy in ring(P.DISC_D / 2 + 0.1)):
                    bad.append(f"孔装不下 Φ{P.DISC_D} 铜片 ({x},{y}) z={z}")
                    break
            if any(ins(p, x + dx, y + dy, P.LAYER_T / 2) for dx, dy in [(0, 0)] + ring(1.5, 8)):
                bad.append(f"孔中间有料 ({x},{y})")
            if not all(ins(p, x + dx, y + dy, P.LAYER_T / 2) for dx, dy in ring(P.DISC_D / 2 + 0.6)):
                bad.append(f"孔太大或孔边缺料 ({x},{y})")
        if not ins(p, 0, y, P.LAYER_T / 2):
            bad.append(f"两孔之间缺料 y={y}")
    for ya, yb in zip(sorted(ys), sorted(ys)[1:]):
        for x in (-P.PN / 2, 0, P.PN / 2):
            if not ins(p, x, (ya + yb) / 2, P.LAYER_T / 2):
                bad.append(f"路间缺料 x={x} y={(ya + yb) / 2}")
    lo, hi = P.span(ys)
    for x in (-P.LAYER_W / 2 + 0.2, P.LAYER_W / 2 - 0.2):
        for y in (lo + 0.2, hi - 0.2, (lo + hi) / 2):
            if x > 0 and y > hi - 1.0:
                if ins(p, x, y, P.LAYER_T / 2):
                    bad.append("北端 +X 没有方向切角")
                continue
            if not ins(p, x, y, P.LAYER_T / 2):
                bad.append(f"边缘缺料 ({x},{y:.1f})")
    if len(p.solids()) != 1:
        bad.append(f"实体数 {len(p.solids())}")
    bb = p.bounding_box()
    want = (P.LAYER_W, hi - lo, P.LAYER_T)
    if any(abs(g - w) > 0.01 for g, w in zip((bb.size.X, bb.size.Y, bb.size.Z), want)):
        bad.append(f"包围盒 {[round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)]} ≠ {want}")
    return bad


def spec(P=m) -> list[str]:
    bad: list[str] = []
    s = P.summary()
    for k, v in EXPECT.items():
        if getattr(P, k) != v:
            bad.append(f"{k} = {getattr(P, k)} ≠ 规定值 {v}")
    if not 0.8 - 1e-9 <= s["disc_proud_flush_mm"] <= 2.0 + 1e-9:
        bad.append(f"铜片凸出 {s['disc_proud_flush_mm']} 不在 0.8–2.0")
    for k in ("wall_to_edge", "wall_to_end"):
        if s[k] < P.MIN_WALL - 1e-9:
            bad.append(f"{k} {s[k]} < {P.MIN_WALL}")
    if s["wall_between_ch"] < 1.0 - 1e-9:
        bad.append(f"路间壁 {s['wall_between_ch']} < 1.0")
    if s["disc_inside_strap"] < 0 - 1e-9:
        bad.append(f"铜片出表带边 {s['disc_inside_strap']}")
    if P.LAYER_T < 0.6 - 1e-9:
        bad.append(f"层厚 {P.LAYER_T} < 0.6")
    if P.HOLE_CLEAR < 0.2 - 1e-9:
        bad.append(f"孔余量 {P.HOLE_CLEAR} < 0.2")
    if s["strap_channels"] != 6 or s["total_system_channels"] != 8:
        bad.append(f"8ch 版表带路数应为 6（总路数 8），实际 {s['strap_channels']}/{s['total_system_channels']}")
    if s["pockets"]["north"] != 4 or s["pockets"]["south"] != 8:
        bad.append(f"8ch 串阻槽应为北 4 + 南 8 = 12 个，实际 {s['pockets']}")
    if s["pocket_floor"] < 0.3 - 1e-9:
        bad.append(f"槽顶只剩 {s['pocket_floor']} < 0.3（两层）")
    if P.POCKET_D < P.RES_H + 0.05 - 1e-9:
        bad.append(f"槽深 {P.POCKET_D} < 串阻高 {P.RES_H} + 0.05")
    for ys in (P.NORTH_YS, P.SOUTH_YS):
        for x0, x1, y0, y1 in P.pockets(ys):
            for y in ys:
                for hx in (-P.PN / 2, P.PN / 2):
                    dx = max(x0 - hx, 0, hx - x1)
                    dy = max(y0 - y, 0, y - y1)
                    if math.hypot(dx, dy) - P.hole_d() / 2 < P.MIN_WALL - 1e-9:
                        bad.append(f"槽离孔 {math.hypot(dx, dy) - P.hole_d() / 2:.2f} < {P.MIN_WALL}")
    if s["north_to_loop"] < P.LUG_GAP - 1e-9:
        bad.append(f"北片离带端圆筒 {s['north_to_loop']} < {P.LUG_GAP}")
    if s["south_to_loop"] < P.LUG_GAP - 1e-9:
        bad.append(f"南片离带端圆筒 {s['south_to_loop']} < {P.LUG_GAP}")
    if s["north_to_ring"] < 3.0 - 1e-9:
        bad.append(f"北片离扣环 {s['north_to_ring']} < 3")
    return bad


def run(**over) -> list[str]:
    saved = {k: getattr(m, k) for k in over}
    try:
        for k, v in over.items():
            setattr(m, k, v)
        bad = spec()
        for ys in (m.NORTH_YS, m.SOUTH_YS):
            try:
                bad += probe(m.build_piece(ys), ys)
            except Exception as e:
                bad.append(f"建模失败 {type(e).__name__}")
        return bad
    finally:
        for k, v in saved.items():
            setattr(m, k, v)


def parse_pcb_footprints(pcb_path: Path) -> tuple[list[dict], list[dict]]:
    """直接解析 strap-d2-8ch.kicad_pcb 提取 F.Cu 上的 R5–R16 串阻与表带段 E3–E8 电极焊盘。"""
    raw = pcb_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.PINNED_FPC_SHA256
    txt = raw.decode("utf-8")
    res_list: list[dict] = []
    elec_list: list[dict] = []
    i = 0
    n = len(txt)
    while i < n:
        idx = txt.find("\t(footprint ", i)
        if idx == -1:
            break
        depth = 0
        j = idx
        in_str = False
        while j < n:
            ch = txt[j]
            if ch == '"' and txt[j - 1] != "\\":
                in_str = not in_str
            elif not in_str:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
            j += 1
        blk = txt[idx:j]
        i = j
        m_fp = re.match(r'\t\(footprint\s+"([^"]+)"', blk)
        m_layer = re.search(r'\(layer\s+"([^"]+)"\)', blk)
        m_at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", blk)
        m_ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', blk)
        if not (m_fp and m_layer and m_at and m_ref):
            continue
        fpid, layer, ref = m_fp.group(1), m_layer.group(1), m_ref.group(1)
        bx, by = float(m_at.group(1)), float(m_at.group(2))
        rot = float(m_at.group(3) or 0.0) % 180.0
        if layer == "F.Cu" and fpid == "R0402":
            # 0402 焊盘+器件包络（含焊膏外沿 1.56 × 0.64 mm）
            hx, hy = (0.32, 0.78) if abs(rot - 90.0) < 1e-3 else (0.78, 0.32)
            res_list.append({"ref": ref, "bx": bx, "by": by, "envelope": (bx - hx, by - hy, bx + hx, by + hy)})
        elif layer == "F.Cu" and re.match(r"^E[3-8][PN]$", ref):
            elec_list.append({"ref": ref, "bx": bx, "by": by})
    return res_list, elec_list


def res_fit_pcb(P=m) -> list[str]:
    """独立从源板 .kicad_pcb 验证右手系换算（行列式 +1）：12 颗 F.Cu 串阻全部落槽 + 12 颗表带电极同心。"""
    M = ((0, -1, 0), (-1, 0, 0), (0, 0, -1))
    det = (
        M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
        - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
        + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
    )
    bad = [] if det == 1 else [f"换算行列式 {det} ≠ +1（镜像）"]
    res_list, elec_list = parse_pcb_footprints(P.FPC_PCB)
    if len(res_list) != 12:
        bad.append(f"源板 F.Cu R0402 数量 {len(res_list)} ≠ 12")
    if len(elec_list) != 12:
        bad.append(f"源板表带电极 E3–E8 数量 {len(elec_list)} ≠ 12")
    pieces = {"north": P.build_piece(P.NORTH_YS), "south": P.build_piece(P.SOUTH_YS)}
    holes = {(round(x, 3), round(y, 3)) for ys in (P.NORTH_YS, P.SOUTH_YS) for y in ys for x in (-P.PN / 2, P.PN / 2)}
    for e in elec_list:
        X, Y = round(50.0 - e["by"], 3), round(58.0 - e["bx"], 3)
        if (X, Y) not in holes:
            bad.append(f"{e['ref']} 换算坐标 ({X},{Y}) 未对准任何 TPU 孔")
    for r in res_list:
        x0, y0, x1, y1 = r["envelope"]
        pts = [((x0 + x1) / 2, (y0 + y1) / 2)] + [(x, y) for x in (x0, x1) for y in (y0, y1)]
        T = [(50.0 - y, 58.0 - x) for x, y in pts]
        part = pieces["north" if T[0][1] > 0 else "south"]
        for z in (0.05, 0.20, P.RES_H):
            if any(ins(part, X, Y, z) for X, Y in T):
                bad.append(f"{r['ref']} 在 z={z} 撞上 TPU 实体（未落进浅槽）")
                break
    return bad


def intersect_vol(solids_a: list[b.Solid], solids_b: list[b.Solid]) -> float:
    total = 0.0
    for sa in solids_a:
        bba = sa.bounding_box()
        for sb in solids_b:
            bbb = sb.bounding_box()
            if (
                bba.max.X <= bbb.min.X
                or bba.min.X >= bbb.max.X
                or bba.max.Y <= bbb.min.Y
                or bba.min.Y >= bbb.max.Y
                or bba.max.Z <= bbb.min.Z
                or bba.min.Z >= bbb.max.Z
            ):
                continue
            inter = sa & sb
            if inter is not None:
                for s in inter.solids():
                    total += abs(float(s.volume))
    return round(total, 6)


def transform_fpc_solid_to_strap(sol: b.Solid, gap_mm: float = 0.10, mirror_x: bool = False) -> b.Solid:
    """将 KiCad STEP 实体 (xs=bx, ys=-by, zs) 逐个做刚体旋转变换到表带 TPU 坐标系：
    绕 Z 轴转 -90°：(xs, ys, zs) -> (ys, -xs, zs)，再平移 (+50, +58, -Z_F_STEP - gap_mm)。
    线性矩阵 [[0, 1, 0], [-1, 0, 0], [0, 0, 1]] 行列式 = +1（纯旋转零镜像）。
    """
    s1 = sol.rotate(b.Axis.Z, -90.0)
    s2 = s1.translate((50.0, 58.0, -Z_F_STEP - gap_mm))
    if mirror_x:
        s2 = b.mirror(s2, about=b.Plane.YZ)
    return s2


def solid_3d_fit() -> dict:
    """导入 strap-d2-8ch-3d.step 实心 3D 装配体，与北/南 TPU STEP 做真实三维布尔干涉与 5 项必交反例验证。"""
    fpc_comp = b.import_step(str(STEP_FPC_3D))
    north_solids = list(b.import_step(str(HERE / "layer_d2_8ch_north.step")).solids())
    south_solids = list(b.import_step(str(HERE / "layer_d2_8ch_south.step")).solids())
    tpu_solids = north_solids + south_solids
    assert len(north_solids) == 1 and len(south_solids) == 1

    strap_comp_step: list[b.Solid] = []
    board_step: b.Solid | None = None
    for s in fpc_comp.solids():
        bb = s.bounding_box()
        xc = (bb.min.X + bb.max.X) / 2.0
        if bb.size.X > 80.0:
            board_step = s
        elif xc < 35.0 or xc > 80.0:
            strap_comp_step.append(s)

    assert board_step is not None
    assert len(strap_comp_step) == 24, f"表带段应有 24 颗器件实体（12 铜片 + 12 串阻），实际 {len(strap_comp_step)}"

    # 裁剪北段 [11.9, 28.1] 与南段 [85.9, 118.1] 软板基材参与三维布尔检查
    clip_n = b.Pos(20.0, -50.0, 0.05) * b.Box(16.2, 30.0, 0.5)
    clip_s = b.Pos(102.0, -50.0, 0.05) * b.Box(32.2, 30.0, 0.5)
    board_clips = list((board_step & clip_n).solids()) + list((board_step & clip_s).solids())
    assert len(board_clips) >= 2

    all_step = strap_comp_step + board_clips
    solids_gap010 = [transform_fpc_solid_to_strap(s, gap_mm=0.10) for s in all_step]
    solids_flush = [transform_fpc_solid_to_strap(s, gap_mm=0.00) for s in all_step]

    v_gap010 = intersect_vol(solids_gap010, tpu_solids)
    v_flush = intersect_vol(solids_flush, tpu_solids)

    disc_tops_010 = sorted(round(s.bounding_box().max.Z, 4) for s in solids_gap010 if s.bounding_box().max.Z > 1.5)
    disc_tops_flush = sorted(round(s.bounding_box().max.Z, 4) for s in solids_flush if s.bounding_box().max.Z > 1.5)

    # 平面内转 180°（保持浅槽朝 FPC）：因串阻偏移 (±1.5, ∓4.3) 绕岛中心 C2 中心对称，平面 180° 旋转同样 0 干涉
    n_lo, n_hi = m.span(m.NORTH_YS)
    s_lo, s_hi = m.span(m.SOUTH_YS)
    tpu_rot180 = [
        ns.translate((0, -(n_lo + n_hi) / 2, 0)).rotate(b.Axis.Z, 180.0).translate((0, (n_lo + n_hi) / 2, 0))
        for ns in north_solids
    ] + [
        ss.translate((0, -(s_lo + s_hi) / 2, 0)).rotate(b.Axis.Z, 180.0).translate((0, (s_lo + s_hi) / 2, 0))
        for ss in south_solids
    ]
    v_rot180_c2 = intersect_vol(solids_gap010, tpu_rot180)

    # 5 组三维实心必败反例（全部必须产生 > 0.5 mm³ 真实布尔干涉）
    # 1) X 镜像（套用盒底 X = by - 50 错式）：12 颗非对称串阻全部撞进 TPU 实心区
    v_neg_mirror_x = intersect_vol([transform_fpc_solid_to_strap(s, gap_mm=0.10, mirror_x=True) for s in strap_comp_step], tpu_solids)
    # 2) 左右翻面安装（绕各片自身纵向 Y 中轴翻 180°，孔仍对齐，但浅槽朝皮肤、平底压死 12 颗串阻）
    tpu_flip_y = [
        ns.rotate(b.Axis((0, (n_lo + n_hi) / 2, m.LAYER_T / 2), (0, 1, 0)), 180.0)
        for ns in north_solids
    ] + [
        ss.rotate(b.Axis((0, (s_lo + s_hi) / 2, m.LAYER_T / 2), (0, 1, 0)), 180.0)
        for ss in south_solids
    ]
    v_neg_flip_over_y = intersect_vol(solids_gap010, tpu_flip_y)
    # 3) 南北翻面安装（绕各片自身横向 X 中轴翻 180°，孔仍对齐，但浅槽朝皮肤、平底压死 12 颗串阻）
    tpu_flip_x = [
        ns.rotate(b.Axis((0, (n_lo + n_hi) / 2, m.LAYER_T / 2), (1, 0, 0)), 180.0)
        for ns in north_solids
    ] + [
        ss.rotate(b.Axis((0, (s_lo + s_hi) / 2, m.LAYER_T / 2), (1, 0, 0)), 180.0)
        for ss in south_solids
    ]
    v_neg_flip_over_x = intersect_vol(solids_gap010, tpu_flip_x)
    # 4) TPU 横向偏移 0.40 mm（超过单边 0.25 mm 孔余量，铜片撞孔壁）
    tpu_shift_x = [ts.translate((0.40, 0, 0)) for ts in tpu_solids]
    v_neg_shift_x = intersect_vol(solids_gap010, tpu_shift_x)
    # 5) 漏挖背面串阻槽
    saved_pk = m.pockets
    m.pockets = lambda ys: []
    try:
        tpu_no_pk = list(m.build_piece(m.NORTH_YS).solids()) + list(m.build_piece(m.SOUTH_YS).solids())
    finally:
        m.pockets = saved_pk
    v_neg_no_pockets = intersect_vol(solids_gap010, tpu_no_pk)

    ok_3d = (
        len(disc_tops_010) == 12
        and all(abs(z - 1.90) < 1e-3 for z in disc_tops_010)
        and all(abs(z - 2.00) < 1e-3 for z in disc_tops_flush)
        and v_gap010 == 0.0
        and v_flush == 0.0
        and v_rot180_c2 == 0.0
        and v_neg_mirror_x > 0.5
        and v_neg_flip_over_y > 0.5
        and v_neg_flip_over_x > 0.5
        and v_neg_shift_x > 0.5
        and v_neg_no_pockets > 0.5
    )
    return {
        "strap_component_solids": len(strap_comp_step),
        "twelve_disc_proud_with_9448a_mm": [round(z - m.LAYER_T, 4) for z in disc_tops_010],
        "twelve_disc_proud_flush_mm": [round(z - m.LAYER_T, 4) for z in disc_tops_flush],
        "nominal_interference_mm3": {
            "with_9448a_0p10mm": v_gap010,
            "pressed_flush_0p00mm": v_flush,
            "in_plane_rot180_c2_symmetric": v_rot180_c2,
        },
        "negative_controls_interference_mm3": {
            "mirror_x_r13_formula": v_neg_mirror_x,
            "flip_over_about_y_axis": v_neg_flip_over_y,
            "flip_over_about_x_axis": v_neg_flip_over_x,
            "shift_x_0p40mm": v_neg_shift_x,
            "missing_resistor_pockets": v_neg_no_pockets,
        },
        "ok": ok_3d,
    }


res: dict = {"main": run(), "res_fit_pcb": res_fit_pcb(), "solid_3d_fit": solid_3d_fit()}
neg = {
    "neg_hole_tight": dict(HOLE_CLEAR=-0.2),
    "neg_layer_thick": dict(LAYER_T=1.6),
    "neg_layer_thin": dict(LAYER_T=0.4),
    "neg_pn_20": dict(PN=20.0),
    "neg_narrow": dict(LAYER_W=24.0),
    "neg_pitch_6": dict(PITCH=6.0),
    "neg_north_5": dict(NORTH_YS=tuple(34.0 + 8 * k for k in range(5))),
    "neg_end_0": dict(END_L=0.0),
    "neg_south_close": dict(SOUTH_YS=tuple(-26.0 - 8 * k for k in range(4))),
    "neg_16ch_south_ys": dict(SOUTH_YS=tuple(-32.0 - 8 * k for k in range(12))),
    "neg_disc_big": dict(DISC_D=8.0),
    "neg_pocket_shallow": dict(POCKET_D=0.3),
    "neg_pocket_through": dict(POCKET_D=0.85),
    "neg_pn_14": dict(PN=14.0),
    "neg_disc_t_24": dict(DISC_T=2.4),
    "neg_north_shift": dict(NORTH_YS=(42.0, 50.0)),
    "neg_split_3_3": dict(NORTH_YS=(34.0, 42.0, 50.0), SOUTH_YS=(-32.0, -40.0, -48.0)),
}
for k, kw in neg.items():
    res[k] = run(**kw)

_n = m.build_piece(m.NORTH_YS)
geo = {
    "neg_hole_missing": _n + b.Pos(9, 42, m.LAYER_T / 2) * b.Cylinder(3.3, m.LAYER_T),
    "neg_web_cut": _n - b.Pos(0, 38, m.LAYER_T / 2) * b.Box(30, 0.6, 2),
    "neg_chip": _n + b.Pos(0, 80, 0.4) * b.Box(1, 1, 0.8),
    "neg_pinhole_web": _n - b.Pos(0, 38, m.LAYER_T / 2) * b.Cylinder(1.0, 2),
    "neg_counterbore": _n - b.Pos(9, 42, m.LAYER_T - 0.15) * b.Cylinder(3.8, 0.4),
    "neg_dimple": _n - b.Pos(-5, 38, m.LAYER_T) * b.Sphere(0.6),
    "neg_edge_notch": _n - b.Pos(13.1, 38, m.LAYER_T / 2) * b.Box(1.0, 2.0, 2),
    "neg_extra_hole": _n - b.Pos(-5, 30, m.LAYER_T / 2) * b.Cylinder(0.5, 2),
    "neg_pocket_filled": _n + (lambda q: b.Pos((q[0] + q[1]) / 2, (q[2] + q[3]) / 2, 0.2) * b.Box(1.0, 1.5, 0.4))(m.pockets(m.NORTH_YS)[0]),
    "neg_hole_shifted": (_n + b.Pos(9, 34, m.LAYER_T / 2) * b.Cylinder(3.3, m.LAYER_T))
    - b.Pos(9.8, 34, m.LAYER_T / 2) * b.Cylinder(3.15, m.LAYER_T + 0.2),
}
for k, g in geo.items():
    res[k] = probe(g, m.NORTH_YS)

_pk = m.pockets
m.pockets = lambda ys: [(-q[1], -q[0], q[2], q[3]) for q in _pk(ys)]
try:
    res["neg_pocket_mirror"] = res_fit_pcb()
finally:
    m.pockets = _pk

neg_failed = [k for k in res if k.startswith("neg_") and not res[k]]
ok = (
    not res["main"]
    and not res["res_fit_pcb"]
    and res["solid_3d_fit"]["ok"]
    and not neg_failed
)
res["summary"] = m.summary()
res["pass"] = ok
(HERE / "checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "main_errors": res["main"],
            "res_fit_pcb_errors": res["res_fit_pcb"],
            "solid_3d_fit_ok": res["solid_3d_fit"]["ok"],
            "nominal_3d_mm3": res["solid_3d_fit"]["nominal_interference_mm3"],
            "neg_untriggered": neg_failed,
            "pass": ok,
        },
        ensure_ascii=False,
    )
)
sys.exit(0 if ok else 1)
