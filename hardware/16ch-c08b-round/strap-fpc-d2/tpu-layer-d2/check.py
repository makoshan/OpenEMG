"""D2 开孔层的门：每个孔用铜片实物径探（不拿 hole_d 自比）、孔间/孔边/端头实心、单实体、包围盒、离带端圆筒和扣环、规格门。改坏必须红。"""
import json, math, sys
from pathlib import Path
import build123d as b
import build as m


def ins(p, x, y, z):
    return p.is_inside(b.Vector(x, y, z))


def ring(r, n=16):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# Mako 11-11 定的规格（改设计要两边一起改，防参数被悄悄改掉还判绿）
EXPECT = {"PN": 18.0, "PITCH": 8.0, "DISC_D": 6.0, "DISC_T": 2.0, "NORTH_YS": (34.0, 42.0),
          "SOUTH_YS": tuple(-32.0 - 8.0 * k for k in range(12))}


def grid(p, ys, P=m, step=0.5):
    """整片网格扫：铜片投影（径 + 0.1）内必须全空；孔外（孔径 + 0.1 以外）必须全实。抓针孔、沉孔、锥孔、凹坑、槽、多孔。"""
    bad, lo, hi = [], *P.span(ys)
    holes = [(x, y) for y in ys for x in (-P.PN / 2, P.PN / 2)]
    pk = P.pockets(ys)
    nx, ny = int(P.LAYER_W / step), int((hi - lo) / step)
    for i in range(1, nx):
        x = -P.LAYER_W / 2 + i * step
        for j in range(1, ny):
            y = lo + j * step
            d = min(math.hypot(x - hx, y - hy) for hx, hy in holes)
            if x > P.LAYER_W / 2 - P.KEY - 0.3 and y > hi - P.KEY - 0.3:   # 方向切角区另核
                continue
            inq = [q for q in pk if q[0] - 0.1 < x < q[1] + 0.1 and q[2] - 0.1 < y < q[3] + 0.1]
            if inq:   # 串阻槽：槽内底部要空（深度按串阻高 + 0.05 核，不拿槽深自比），槽顶要实
                if not (q_in := [q for q in inq if q[0] + 0.1 < x < q[1] - 0.1 and q[2] + 0.1 < y < q[3] - 0.1]):
                    continue
                if any(ins(p, x, y, z) for z in (0.05, P.RES_H + 0.05)): bad.append(f'串阻槽不够深/有料 ({x:.1f},{y:.1f})'); return bad
                if not ins(p, x, y, P.LAYER_T - 0.05): bad.append(f'串阻槽打穿 ({x:.1f},{y:.1f})'); return bad
                continue
            if d < P.DISC_D / 2 + 0.1:
                if any(ins(p, x, y, z) for z in (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)): bad.append(f'铜片位置有料 ({x:.1f},{y:.1f})'); return bad
            elif d > P.hole_d() / 2 + 0.1:
                if not all(ins(p, x, y, z) for z in (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)): bad.append(f'该实的地方空了 ({x:.1f},{y:.1f})'); return bad
    return bad


def probe(p, ys, P=m):
    bad = grid(p, ys, P)
    zs = (0.05, P.LAYER_T / 2, P.LAYER_T - 0.05)
    for y in ys:
        for x in (-P.PN / 2, P.PN / 2):
            for z in zs:   # 铜片放得进：铜片径 + 0.1 一圈全空
                if any(ins(p, x + dx, y + dy, z) for dx, dy in ring(P.DISC_D / 2 + 0.1)): bad.append(f'孔装不下 Φ{P.DISC_D} 铜片 ({x},{y}) z={z}'); break
            if any(ins(p, x + dx, y + dy, P.LAYER_T / 2) for dx, dy in [(0, 0)] + ring(1.5, 8)): bad.append(f'孔中间有料 ({x},{y})')
            if not all(ins(p, x + dx, y + dy, P.LAYER_T / 2) for dx, dy in ring(P.DISC_D / 2 + 0.6)): bad.append(f'孔太大或孔边缺料 ({x},{y})')
        if not ins(p, 0, y, P.LAYER_T / 2): bad.append(f'两孔之间缺料 y={y}')
    for ya, yb in zip(sorted(ys), sorted(ys)[1:]):   # 相邻两路之间实心
        for x in (-P.PN / 2, 0, P.PN / 2):
            if not ins(p, x, (ya + yb) / 2, P.LAYER_T / 2): bad.append(f'路间缺料 x={x} y={(ya + yb) / 2}')
    lo, hi = P.span(ys)
    for x in (-P.LAYER_W / 2 + 0.2, P.LAYER_W / 2 - 0.2):
        for y in (lo + 0.2, hi - 0.2, (lo + hi) / 2):
            if x > 0 and y > hi - 1.0:   # 北端 +X 是方向切角
                if ins(p, x, y, P.LAYER_T / 2): bad.append('北端 +X 没有方向切角')
                continue
            if not ins(p, x, y, P.LAYER_T / 2): bad.append(f'边缘缺料 ({x},{y:.1f})')
    if len(p.solids()) != 1: bad.append(f'实体数 {len(p.solids())}')
    bb = p.bounding_box()
    want = (P.LAYER_W, hi - lo, P.LAYER_T)
    if any(abs(g - w) > 0.01 for g, w in zip((bb.size.X, bb.size.Y, bb.size.Z), want)): bad.append(f'包围盒 {[round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)]} ≠ {want}')
    return bad


def spec(P=m):
    bad, s = [], P.summary()
    for k, v in EXPECT.items():
        if getattr(P, k) != v: bad.append(f'{k} = {getattr(P, k)} 不是 Mako 定的 {v}')
    if not 0.8 - 1e-9 <= s["disc_proud"] <= 2.0 + 1e-9: bad.append(f'铜片凸出 {s["disc_proud"]} 不在 0.8–2.0')
    for k in ("wall_to_edge", "wall_to_end"):
        if s[k] < P.MIN_WALL - 1e-9: bad.append(f'{k} {s[k]} < {P.MIN_WALL}')
    if s["wall_between_ch"] < 1.0 - 1e-9: bad.append(f'路间壁 {s["wall_between_ch"]} < 1.0')
    if s["disc_inside_strap"] < 0 - 1e-9: bad.append(f'铜片出表带边 {s["disc_inside_strap"]}')
    if P.LAYER_T < 0.6 - 1e-9: bad.append(f'层厚 {P.LAYER_T} < 0.6')
    if P.HOLE_CLEAR < 0.2 - 1e-9: bad.append(f'孔余量 {P.HOLE_CLEAR} < 0.2')
    if s["channels"] != 14: bad.append(f'表带路数 {s["channels"]} ≠ 14（CH1/CH2 在胶囊底）')
    if s["pockets"]["north"] + s["pockets"]["south"] != 28: bad.append(f'串阻槽 {s["pockets"]} 不是 28 个')
    if s["pocket_floor"] < 0.3 - 1e-9: bad.append(f'槽顶只剩 {s["pocket_floor"]} < 0.3（两层）')
    if P.POCKET_D < P.RES_H + 0.05 - 1e-9: bad.append(f'槽深 {P.POCKET_D} < 串阻高 {P.RES_H} + 0.05')
    for ys in (P.NORTH_YS, P.SOUTH_YS):   # 槽离铜片孔壁 ≥ MIN_WALL
        for x0, x1, y0, y1 in P.pockets(ys):
            for y in ys:
                for hx in (-P.PN / 2, P.PN / 2):
                    dx = max(x0 - hx, 0, hx - x1); dy = max(y0 - y, 0, y - y1)
                    if math.hypot(dx, dy) - P.hole_d() / 2 < P.MIN_WALL - 1e-9: bad.append(f'槽离孔 {math.hypot(dx, dy) - P.hole_d() / 2:.2f} < {P.MIN_WALL}')
    if s["north_to_loop"] < P.LUG_GAP - 1e-9: bad.append(f'北片离带端圆筒 {s["north_to_loop"]} < {P.LUG_GAP}')
    if s["south_to_loop"] < P.LUG_GAP - 1e-9: bad.append(f'南片离带端圆筒 {s["south_to_loop"]} < {P.LUG_GAP}')
    if s["north_to_ring"] < 3.0 - 1e-9: bad.append(f'北片离扣环 {s["north_to_ring"]} < 3')
    return bad


def run(**over):
    saved = {k: getattr(m, k) for k in over}
    try:
        for k, v in over.items(): setattr(m, k, v)
        bad = spec()
        for ys in (m.NORTH_YS, m.SOUTH_YS):
            try:
                bad += probe(m.build_piece(ys), ys)
            except Exception as e:
                bad.append(f'建模失败 {type(e).__name__}')
        return bad
    finally:
        for k, v in saved.items(): setattr(m, k, v)


def res_fit(P=m):
    """独立核落槽（复核 11-11 P0）：不用 f_res_pockets 里算好的表带坐标，自己把 FPC 串阻外框（板坐标 envelope）
    按 TPU 层右手系换算 X = 50 − 板 y、Y = 58 − 板 x、Z = −板 z（行列式 +1）放进 TPU 实体，四角和中心在 z=0.2 都必须是空的（落进槽）。"""
    M = ((0, -1, 0), (-1, 0, 0), (0, 0, -1))
    det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
           + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    bad = [] if det == 1 else [f'换算行列式 {det} ≠ +1（镜像）']
    rects = json.loads(P.FPC_GEOM.read_text(encoding="utf-8"))["f_res_pockets"]["rects"]
    pieces = {"north": (P.NORTH_YS, P.build_piece(P.NORTH_YS)), "south": (P.SOUTH_YS, P.build_piece(P.SOUTH_YS))}
    for r in rects:
        x0, y0, x1, y1 = r["envelope"]
        pts = [((x0 + x1) / 2, (y0 + y1) / 2)] + [(x, y) for x in (x0 + 0.05, x1 - 0.05) for y in (y0 + 0.05, y1 - 0.05)]
        T = [(50.0 - y, 58.0 - x) for x, y in pts]
        Yc = T[0][1]
        name = "north" if Yc > 0 else "south"
        ys, part = pieces[name]
        if any(ins(part, X, Y, 0.2) for X, Y in T): bad.append(f'{r["ref"]} 串阻按右手系换算后没落进槽')
    return bad


res = {"main": run(), "res_fit": res_fit()}
neg = {
 "neg_hole_tight": dict(HOLE_CLEAR=-0.2), "neg_layer_thick": dict(LAYER_T=1.6), "neg_layer_thin": dict(LAYER_T=0.4),
 "neg_pn_20": dict(PN=20.0), "neg_narrow": dict(LAYER_W=24.0), "neg_pitch_6": dict(PITCH=6.0),
 "neg_north_5": dict(NORTH_YS=tuple(34.0 + 8 * k for k in range(5))), "neg_end_0": dict(END_L=0.0),
 "neg_south_close": dict(SOUTH_YS=tuple(-26.0 - 8 * k for k in range(12))), "neg_disc_big": dict(DISC_D=8.0),
 "neg_pocket_shallow": dict(POCKET_D=0.3), "neg_pocket_through": dict(POCKET_D=0.85),
 "neg_pn_14": dict(PN=14.0), "neg_disc_t_24": dict(DISC_T=2.4), "neg_north_shift": dict(NORTH_YS=(42.0, 50.0)),
 "neg_split_3_11": dict(NORTH_YS=(34.0, 42.0, 50.0), SOUTH_YS=tuple(-32.0 - 8 * k for k in range(11))),
}
for k, kw in neg.items(): res[k] = run(**kw)
_n = m.build_piece(m.NORTH_YS)
geo = {  # 参数都对、几何局部坏
 "neg_hole_missing": _n + b.Pos(9, 42, m.LAYER_T / 2) * b.Cylinder(3.3, m.LAYER_T),
 "neg_web_cut": _n - b.Pos(0, 38, m.LAYER_T / 2) * b.Box(30, 0.6, 2),
 "neg_chip": _n + b.Pos(0, 80, 0.4) * b.Box(1, 1, 0.8),
 "neg_pinhole_web": _n - b.Pos(0, 38, m.LAYER_T / 2) * b.Cylinder(1.0, 2),
 "neg_counterbore": _n - b.Pos(9, 42, m.LAYER_T - 0.15) * b.Cylinder(3.8, 0.4),
 "neg_dimple": _n - b.Pos(-5, 38, m.LAYER_T) * b.Sphere(0.6),
 "neg_edge_notch": _n - b.Pos(13.1, 38, m.LAYER_T / 2) * b.Box(1.0, 2.0, 2),
 "neg_extra_hole": _n - b.Pos(-5, 30, m.LAYER_T / 2) * b.Cylinder(0.5, 2),
 "neg_pocket_filled": _n + (lambda q: b.Pos((q[0] + q[1]) / 2, (q[2] + q[3]) / 2, 0.2) * b.Box(1.0, 1.5, 0.4))(m.pockets(m.NORTH_YS)[0]),   # 从实际槽表取位置，不写死坐标
 "neg_hole_shifted": (_n + b.Pos(9, 34, m.LAYER_T / 2) * b.Cylinder(3.3, m.LAYER_T)) - b.Pos(9.8, 34, m.LAYER_T / 2) * b.Cylinder(3.15, m.LAYER_T + 0.2),
}
for k, g in geo.items(): res[k] = probe(g, m.NORTH_YS)
_pk = m.pockets   # 反例：槽 X 镜像（按旧的 X = 板 y − 50），res_fit 必须红
m.pockets = lambda ys: [(-q[1], -q[0], q[2], q[3]) for q in _pk(ys)]
try: res["neg_pocket_mirror"] = res_fit()
finally: m.pockets = _pk
ok = not res["main"] and not res["res_fit"] and all(res[k] for k in res if k.startswith("neg_"))
res["summary"] = m.summary(); res["pass"] = ok
(Path(__file__).parent / "checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("main", res["main"][:3], "green", [k for k in res if k.startswith("neg_") and not res[k]], "pass", ok)
sys.exit(0 if ok else 1)
