"""胶囊底盖 D2 的门：孔对 FPC 胶囊段焊盘（读 FPC geometry.json 的 capsule_pads，盒坐标）、铜片（按实物尺寸）穿得过底盖和底壳、
底盖与底壳不干涉、底盖与底壳外底之间留两片 FPC、原触点孔填平、尾巴缝、裙边凸棱落进卡槽、壁厚、凸出。改坏必须红。"""
import json, math, sys
from pathlib import Path
import build123d as b
import build as m

FPC_GEOM = Path(__file__).resolve().parents[3] / "16ch-c08b-round/strap-fpc-d2/geometry.json"


def ins(p, x, y, z):
    return p.is_inside(b.Vector(x, y, z))


def ring(r, n=16):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def vol(a, c):
    try:
        r = a & c
    except Exception:   # 布尔真失败当作干涉（复核 11-11 P2：吞成 0 会把失败当成「不撞」）
        return float("inf")
    return 0.0 if r is None else r.volume   # build123d 求交为空时返回 None，这才是「不撞」


def run(tray=None, cap=None):
    bad, s = [], m.summary()
    tray = tray if tray is not None else m.build_tray_d2()
    cap = cap if cap is not None else m.build_cap()
    z0 = m.face_z0()
    # 1 孔对 FPC 焊盘（独立来源）
    try:
        cp = json.loads(FPC_GEOM.read_text(encoding="utf-8")).get("capsule_pads")
    except FileNotFoundError:
        cp = None
    if not cp:
        bad.append("FPC geometry.json 没有 capsule_pads")
    else:
        items = cp if isinstance(cp, list) else cp.get("pads", [])
        if isinstance(cp, dict) and abs(cp.get("stack_note", {}).get("eb2_disc_base_higher_mm", 0) - m.B_OVER_A) > 1e-6: bad.append('EB2 垫高与 FPC stack_note 不符')
        if len(items) != 6: bad.append(f'FPC capsule_pads {len(items)} ≠ 6')
        for it in items:
            ref = it.get("ref") or it.get("name")
            bx, by = it["box"] if isinstance(it.get("box"), (list, tuple)) else (it["box"]["X"], it["box"]["Y"])
            if ref not in m.PADS: bad.append(f'FPC 焊盘 {ref} 不在孔表'); continue
            px, py = m.PADS[ref]
            pd = it.get("d")
            if pd is not None and m.hole_d(ref) < (m.BIG_D if ref in m.BIG else m.AUX_D) + 0.4 - 1e-9: bad.append(f'{ref} 孔比铜片大不到 0.4')
            need = m.BIG_D if ref in m.BIG else m.AUX_D * 2 ** 0.5   # 方块按对角线：四个角也要落在圆焊盘上
            if pd is not None and pd < need - 1e-9: bad.append(f'{ref} FPC 焊盘 Φ{pd} 盖不住铜片（要 ≥ {need:.2f}）')
            if math.hypot(px - bx, py - by) > 0.01: bad.append(f'{ref} 孔 ({px},{py}) 对 FPC 焊盘 ({bx},{by}) 差 {math.hypot(px - bx, py - by):.3f}')
    # 2 铜片（实物尺寸，从 FPC 面往下）不撞底盖、底壳；孔边一圈有料
    for ref, (x, y) in m.PADS.items():
        d = m.BIG_D if ref in m.BIG else m.AUX_D
        t = m.BIG_T if ref in m.BIG else m.AUX_T
        disc = b.Pos(x, y, m.base_z(ref) - t / 2) * (b.Cylinder(d / 2 + 0.1, t) if ref in m.BIG else b.Box(d + 0.2, d + 0.2, t))
        if vol(disc, cap) > 1e-4: bad.append(f'{ref} 铜片撞底盖')
        if vol(disc, tray) > 1e-4: bad.append(f'{ref} 铜片撞底壳')
        for z in (z0 + 0.05, (z0 + m.FPC_BOT_Z) / 2, m.FPC_BOT_Z - 0.05):
            rr = m.hole_d(ref) / 2 * (1 if ref in m.BIG else 2 ** 0.5) + 0.3   # 方孔取外接圆
            if not all(ins(cap, x + dx, y + dy, z) for dx, dy in ring(rr)): bad.append(f'{ref} 孔边缺料 z={z:.2f}'); break
    # 3 装配（外扣版）：不干涉；底盖顶面与底壳外底之间正好留两片 FPC（从 R13 原底壳实测外底，不自比）；底壳 6 孔已填平；裙边 / 凸棱 / 卡槽
    if vol(cap, tray) > 1e-3: bad.append(f'底盖与底壳干涉 {vol(cap, tray):.4f} mm³')
    r13t = m.r13.build_tray()
    zs = [round(-0.5 + 0.01 * i, 2) for i in range(100)]
    bottom = next((z for z in zs if ins(r13t, 18.0, 0.0, z)), None)   # 底壳外底实测
    if bottom is None or abs((bottom - m.FPC_BOT_Z) - 2 * m.FPC_T) > 0.03: bad.append(f'底盖顶面 {m.FPC_BOT_Z} 到底壳外底实测 {bottom} 不是两片 FPC 厚 {2 * m.FPC_T}')
    for x, y in ((18.0, 0.0), (-18.0, 10.0), (0.0, -16.0), (4.0, 0.0)):
        if not ins(cap, x, y, m.FPC_BOT_Z - 0.05): bad.append(f'底盖正面缺 ({x},{y})')
        if ins(cap, x, y, m.FPC_BOT_Z + 0.05): bad.append(f'底盖高出 FPC 面 ({x},{y})')
    for ref, (x, y) in m.PADS.items():
        if not ins(tray, x, y, 0.5): bad.append(f'底壳 {ref} 原触点孔没填平')
    g0, g1, gd = m.GROOVE
    for sx in (-1, 1):
        for y in (-10.0, 0.0, 10.0):
            if not ins(cap, sx * (m.BODY_HX + m.SKIRT_T / 2), y, 1.0): bad.append(f'裙边缺 x={sx} y={y}')
            if not ins(cap, sx * (m.BODY_HX - m.BEAD / 2), y, (g0 + g1) / 2): bad.append(f'凸棱缺 x={sx} y={y}')
            if ins(tray, sx * (m.BODY_HX - gd / 2), y, (g0 + g1) / 2): bad.append(f'卡槽没开 x={sx} y={y}')
        if ins(cap, sx * (m.BODY_HX + m.SKIRT_T / 2), m.BODY_HY - 1.0, 1.0): bad.append(f'裙边包到圆角/端头 x={sx}')
    ts = m.tail_slot()
    if not ts:
        bad.append('FPC 还没给 tray_tail_slot（尾巴缝）')
    else:
        bx = ts["box"]
        cx, cy = (bx["x0"] + bx["x1"]) / 2, (bx["y0"] + bx["y1"]) / 2
        if ins(tray, cx, cy, 0.5) or ins(tray, bx["x0"] + 0.1, cy, 0.9) or ins(tray, bx["x1"] - 0.1, cy, 0.9): bad.append('底壳尾巴缝没开通')
        if ins(tray, 0.0, ts["north_pocket_y_max_needed"] - 0.02, 2.0): bad.append('北回折槽北壁没退到尾巴需要的位置')
    for r in m.fpc_geom().get("capsule_res_pockets", {}).get("rects", []):   # FPC 背面串阻：底壳外底浅槽要让开（按件顶面实测，不拿槽深自比）
        bx = r["box"]
        if ins(tray, (bx["x0"] + bx["x1"]) / 2, (bx["y0"] + bx["y1"]) / 2, r["part_top_z"] - 0.01): bad.append(f'{r["ref"]} 串阻顶到底壳外底')
        if not ins(tray, (bx["x0"] + bx["x1"]) / 2, (bx["y0"] + bx["y1"]) / 2, 0.95): bad.append(f'{r["ref"]} 串阻槽把底板挖穿')
    # 4 规格门
    pr = s["proud_big"] | s["proud_aux"]   # 11-12 起 6 片同高（REF 挪到 A 片），每片都要等于表带 1.2
    if any(abs(v - 1.2) > 0.05 for v in pr.values()): bad.append(f'凸出 {pr} 不全等于表带 1.2')
    for k, lim in (("hole_gap_min", 0.8), ("tray_wall_at_groove", 0.8), ("face_t", 0.6)):
        if s[k] < lim - 1e-9: bad.append(f'{k} {s[k]} < {lim}')
    if m.SKIRT_T < 0.6 - 1e-9: bad.append(f'裙边 {m.SKIRT_T} < 0.6')
    if not 0.05 - 1e-9 <= m.GROOVE[2] - m.BEAD <= 0.15 + 1e-9: bad.append(f'凸棱比槽浅 {m.GROOVE[2] - m.BEAD:.2f} 不在 0.05–0.15')
    if len(tray.solids()) != 1 or len(cap.solids()) != 1: bad.append('实体数不为 1')
    return bad


def neg(**over):
    saved = {k: getattr(m, k) for k in over}
    try:
        for k, v in over.items(): setattr(m, k, v)
        return run()
    finally:
        for k, v in saved.items(): setattr(m, k, v)


res = {"main": run()}
for k, kw in {"neg_hole_small": dict(HOLE_CLEAR=-0.2), "neg_aux_thin": dict(AUX_T=1.5), "neg_aux_wide": dict(AUX_D=3.4), "neg_aux_tall": dict(AUX_T=2.4), "neg_eb2_raised": dict(BASE_Z={"EB2": m.FPC_BOT_Z + 0.203}),
              "neg_big_thin": dict(BIG_T=1.0), "neg_face_thick": dict(FACE_T=1.6), "neg_pad_shift": dict(PADS={**m.PADS, "E1N": (-8.4, 7.5)}), "neg_eb_swapped": dict(PADS={**m.PADS, "EB1": (0.0, 7.5), "EB2": (0.0, -7.5)}),
              "neg_groove_deep": dict(GROOVE=(0.45, 0.85, 0.6)), "neg_bead_none": dict(BEAD=0.0), "neg_skirt_thin": dict(SKIRT_T=0.3),
              "neg_fpc_gap_one": dict(FPC_BOT_Z=m.TRAY_BOT - m.FPC_T)}.items():
    res[k] = neg(**kw)
_c = m.build_cap()
res["neg_cap_hole_plug"] = run(cap=_c + b.Pos(8, 7.5, m.face_z0() + 0.4) * b.Cylinder(1.0, 0.8))
res["neg_cap_skirt_cut"] = run(cap=_c - m.box(23.0, 24.0, -2, 2, -1, 2))
res["neg_tray_holes_open"] = run(tray=m.r13.build_tray())
ok = not res["main"] and all(res[k] for k in res if k.startswith("neg_"))
res["summary"] = m.summary(); res["pass"] = ok
(Path(__file__).parent / "checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("main", res["main"][:4], "green", [k for k in res if k.startswith("neg_") and not res[k]], "pass", ok)
sys.exit(0 if ok else 1)
