"""R14 板面量测（KiCad 自带 python3）。全部从 kicad_pcb 文件读回，不用 build.py 内存里的数。
check.py 调用 measure() / widths() / stack_gap()；单独运行 `python3 metrics.py 目录` 打印该目录两片板的量测（可量 R12/R13）。"""
import json
import math
import sys
from pathlib import Path

import pcbnew as k

mm = k.ToMM


def ptseg(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.dist(p, (a[0] + t * ax, a[1] + t * ay))


def segdist(a, b, c, d):
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
        return 0.0
    return min(ptseg(a, c, d), ptseg(b, c, d), ptseg(c, a, b), ptseg(d, a, b))


def ptrect(p, r):
    x0, y0, x1, y1 = r
    return math.hypot(max(x0 - p[0], 0, p[0] - x1), max(y0 - p[1], 0, p[1] - y1))


def P(x, y):
    return k.VECTOR2I(round(x * 1e6), round(y * 1e6))


def pset(pts):
    s = k.SHAPE_POLY_SET(); s.NewOutline()
    for x, y in pts:
        s.Append(round(x * 1e6), round(y * 1e6))
    return s


def chain_pts(ch):
    return [(ch.CPoint(i).x / 1e6, ch.CPoint(i).y / 1e6) for i in range(ch.PointCount())]


def area(s):
    return s.Area() / 1e12


def circle_pts(x, y, r, n=96):
    return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _and(a, b):
    s = k.SHAPE_POLY_SET(a); s.BooleanIntersection(b)
    return s


def coupled(n1, n2):
    """同一差分对 CHn_P / CHn_N（电极侧 _E 网不算一对）。"""
    if not (n1.startswith('CH') and n2.startswith('CH')) or n1.endswith('_E') or n2.endswith('_E'):
        return False
    return n1[:-2] == n2[:-2] and {n1[-2:], n2[-2:]} == {'_P', '_N'}


def items(b):
    tr = [(t.GetNetname(), t.GetLayerName(), (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()))
          for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [dict(c=(mm(t.GetPosition().x), mm(t.GetPosition().y)), r=mm(t.GetWidth(k.F_Cu)) / 2, drill=mm(t.GetDrillValue()) / 2, net=t.GetNetname())
            for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    pads = []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append(dict(ref=f.GetReference(), num=p.GetNumber(), net=p.GetNetname(), circle=p.GetShape() == k.PAD_SHAPE_CIRCLE,
                             c=(mm(p.GetPosition().x), mm(p.GetPosition().y)), r=mm(p.GetSize(k.F_Cu).x) / 2,
                             rect=(mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())),
                             F=p.IsOnLayer(k.F_Cu), B=p.IsOnLayer(k.B_Cu)))
    segs, circles, rings, polys = [], [], {'User.1': [], 'User.2': []}, []
    for d in b.GetDrawings():
        if d.GetClass() != 'PCB_SHAPE':
            continue
        L = {k.User_1: 'User.1', k.User_2: 'User.2'}.get(d.GetLayer(), d.GetLayerName())
        if L == 'Edge.Cuts':
            if d.GetShape() == k.SHAPE_T_POLY:
                ring = chain_pts(d.GetPolyShape().Outline(0))
                segs += list(zip(ring, ring[1:] + ring[:1])); polys.append(ring)
            elif d.GetShape() == k.SHAPE_T_CIRCLE:
                circles.append(((mm(d.GetCenter().x), mm(d.GetCenter().y)), mm(d.GetRadius())))
            elif d.GetShape() == k.SHAPE_T_SEGMENT:
                segs.append(((mm(d.GetStart().x), mm(d.GetStart().y)), (mm(d.GetEnd().x), mm(d.GetEnd().y))))
            elif d.GetShape() == k.SHAPE_T_ARC:
                c, r = (mm(d.GetCenter().x), mm(d.GetCenter().y)), mm(d.GetRadius())
                a0, a1 = math.atan2(mm(d.GetStart().y) - c[1], mm(d.GetStart().x) - c[0]), math.radians(d.GetArcAngle().AsDegrees())
                pts = [(c[0] + r * math.cos(a0 + a1 * i / 16), c[1] + r * math.sin(a0 + a1 * i / 16)) for i in range(17)]
                segs += list(zip(pts, pts[1:]))
        elif L in rings and d.GetShape() == k.SHAPE_T_POLY:
            rings[L].append(chain_pts(d.GetPolyShape().Outline(0)))
    dyn = []
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetZoneName().startswith('动态区禁孔'):
            bb = z.GetBoundingBox()
            dyn.append((z.GetZoneName().replace('动态区禁孔-', ''), (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))))
    board = None
    if polys:
        board = pset(polys[0])
        for c, r in circles:
            board.BooleanSubtract(pset(circle_pts(*c, r)))
    return dict(tr=tr, vias=vias, pads=pads, segs=segs, circles=circles, rings=rings, dyn=dyn, board=board, outline=polys[0] if polys else None)


def material(rings):
    """补强层上的闭合线：被别的环包住的是孔/窗，其余是外形。"""
    outer, holes = [], []
    for i, r in enumerate(rings):
        inside = any(j != i and pset(q).Contains(P(*r[0])) for j, q in enumerate(rings))
        (holes if inside else outer).append(r)
    s = k.SHAPE_POLY_SET()
    for r in outer:
        s.BooleanAdd(pset(r))
    for r in holes:
        s.BooleanSubtract(pset(r))
    return s


def track_spacing(tr):
    """同层两条不同网走线的最小中心距（同一差分对除外）与对内最小中心距，带位置。"""
    inter, intra = (9.0, None), (9.0, None)
    bb = [(min(a[0], b_[0]), min(a[1], b_[1]), max(a[0], b_[0]), max(a[1], b_[1])) for _, _, a, b_, _ in tr]
    for i in range(len(tr)):
        n1, l1, a, b_, _ = tr[i]
        for j in range(i + 1, len(tr)):
            n2, l2, c, d, _ = tr[j]
            if l1 != l2 or n1 == n2:
                continue
            if bb[i][0] - bb[j][2] > 2 or bb[j][0] - bb[i][2] > 2 or bb[i][1] - bb[j][3] > 2 or bb[j][1] - bb[i][3] > 2:
                continue
            dd = segdist(a, b_, c, d)
            if coupled(n1, n2):
                if dd < intra[0]:
                    intra = (dd, dict(nets=[n1, n2], layer=l1, at=[round((a[0] + b_[0]) / 2, 3), round((a[1] + b_[1]) / 2, 3)]))
            elif dd < inter[0]:
                inter = (dd, dict(nets=[n1, n2], layer=l1, at=[round((a[0] + b_[0]) / 2, 3), round((a[1] + b_[1]) / 2, 3)]))
    return inter, intra


def cross_section(it, x):
    """x 处外形的竖直截面区间，以及穿过该截面的走线 (y, 网, 层)。"""
    ys = []
    for a, b in it['segs']:
        if (a[0] - x) * (b[0] - x) < 0:
            ys.append(a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0]))
    ys.sort()
    iv = [(round(ys[i], 4), round(ys[i + 1], 4)) for i in range(0, len(ys) - 1, 2)]
    hits = []
    for n, l, a, b, w in it['tr']:
        if (a[0] - x) * (b[0] - x) < 0 or (a[0] == x) != (b[0] == x):
            if a[0] == b[0]:
                continue
            hits.append((round(a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0]), 4), n, l, w))
    return iv, sorted(set(hits))


def band_stats(it, x, yref):
    """x 处、含 yref 的那段外形：宽度、带内走线的最小异网中心距（所有网）、CHn 差分对中心节距（只算 CHn_P/N）、外侧铜到边（所有网）。"""
    iv, hits = cross_section(it, x)
    seg = next((s for s in iv if s[0] <= yref <= s[1]), None)
    if seg is None:
        return None
    hs = [h for h in hits if seg[0] < h[0] < seg[1]]
    out = dict(x=x, y0=seg[0], y1=seg[1], width=round(seg[1] - seg[0], 3), tracks=len(hs))
    for L in ('F.Cu', 'B.Cu'):
        hl = sorted(h for h in hs if h[2] == L)
        if not hl:
            continue
        dmin = min((b[0] - a[0] for a, b in zip(hl, hl[1:]) if not coupled(a[1], b[1]) and a[1] != b[1]), default=None)
        pairs = {}
        for y, n, _, _ in hl:
            if n.startswith('CH') and not n.endswith('_E'):
                pairs.setdefault(n[:-2], []).append(y)
        centers = sorted(sum(v) / len(v) for v in pairs.values() if len(v) == 2)
        pitches = [b - a for a, b in zip(centers, centers[1:])]
        out[L] = dict(tracks=len(hl), pairs=len(centers), min_center_diff_net=None if dmin is None else round(dmin, 3),
                      pair_pitch_min=round(min(pitches), 3) if pitches else None, pair_pitch_max=round(max(pitches), 3) if pitches else None,
                      edge_copper_top=round(hl[0][0] - hl[0][3] / 2 - seg[0], 3), edge_copper_bottom=round(seg[1] - hl[-1][0] - hl[-1][3] / 2, 3))
    return out


def widths(b, spec):
    """spec: {段名: (x, yref)} → 各段截面统计。"""
    it = items(b)
    return {name: band_stats(it, x, y) for name, (x, y) in spec.items()}


def _rect_segs(r):
    x0, y0, x1, y1 = r
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return list(zip(c, c[1:] + c[:1]))


def pad_gap(top, p):
    """另一片（top 的 items）的材料（外形多边形减 Edge.Cuts 圆孔）到焊盘 p 的带符号间隙：
    正 = 焊盘完全落在空处（板外或孔里），值为焊盘边到最近材料边；负 = 焊盘压在材料上，值为压入深度（近似）。圆孔解析计算。"""
    c = p['c']
    r_eff = p['r'] if p['circle'] else math.hypot((p['rect'][2] - p['rect'][0]) / 2, (p['rect'][3] - p['rect'][1]) / 2)
    corners = None if p['circle'] else [(p['rect'][0], p['rect'][1]), (p['rect'][2], p['rect'][1]), (p['rect'][2], p['rect'][3]), (p['rect'][0], p['rect'][3])]

    def to_seg(a, b):
        if p['circle']:
            return ptseg(c, a, b) - p['r']
        if ptrect(a, p['rect']) == 0 or ptrect(b, p['rect']) == 0:
            return 0.0
        return min(segdist(a, b, *e) for e in _rect_segs(p['rect']))

    outline = top['segs']
    d_out = min(to_seg(a, b) for a, b in outline)
    hole = next(((hc, hr) for hc, hr in top['circles'] if math.dist(c, hc) < hr), None)
    in_poly = top['poly'].Contains(P(*c))
    if hole is not None:                                            # 焊盘中心在孔里
        hc, hr = hole
        far = math.dist(c, hc) + p['r'] if p['circle'] else max(math.dist(q, hc) for q in corners)
        return round(hr - far, 4), '孔'
    if not in_poly:                                                 # 焊盘中心在板外
        return round(d_out, 4), '板外'
    d_bound = min([ptseg(c, a, b) for a, b in outline] + [abs(math.dist(c, hc) - hr) for hc, hr in top['circles']])
    return round(-(r_eff + d_bound), 4), '压在材料上'


def stack_gap(b_top, b_under, kinds):
    """b_top 叠在 b_under 上：b_top 的材料到 b_under 指定焊盘的带符号间隙（见 pad_gap），逐焊盘给出，取最小。"""
    top = items(b_top)
    ol = k.SHAPE_POLY_SET()
    b_top.GetBoardPolygonOutlines(ol, False)                         # 外形线（多边形或线段/圆弧）拼成的外轮廓，R12 也能用
    top['poly'] = k.SHAPE_POLY_SET(); top['poly'].AddOutline(ol.Outline(0))
    under = items(b_under)
    res = {}
    for kind, sel in kinds.items():
        rows = []
        for p in under['pads']:
            if sel(p):
                g, where = pad_gap(top, p)
                rows.append(dict(pad=f"{p['ref']}.{p['num']}", net=p['net'], gap_mm=g, where=where))
        rows.sort(key=lambda r: r['gap_mm'])
        res[kind] = dict(min_gap_mm=rows[0]['gap_mm'], at=rows[0]['pad'], nearest=rows[:4], pads=len(rows))
    return res


def backside_tracks(b):
    """B 面贴片焊盘（串阻）的正背面（F.Cu）有没有走线经过：返回 (焊盘, 走线网) 对。"""
    it = items(b)
    hits = []
    for p in it['pads']:
        if p['circle'] or not p['B'] or p['F']:
            continue
        nets = sorted({n for n, L, a, b_, w in it['tr'] if L == 'F.Cu' and (ptrect(a, p['rect']) == 0 or ptrect(b_, p['rect']) == 0
                                                                          or min(segdist(a, b_, *e) for e in _rect_segs(p['rect'])) < w / 2)})
        hits += [dict(pad=f"{p['ref']}.{p['num']}", f_cu_net=n) for n in nets]
    pads = sorted({h['pad'] for h in hits}, key=lambda s: (int(s[1:].split('.')[0]), s))
    return dict(pad_net_pairs=len(hits), pads=len(pads), resistors=sorted({p.split('.')[0] for p in pads}, key=lambda s: int(s[1:])), list=hits)


def res_web(it):
    """每个串阻焊盘到最近触点焊盘的边距（覆盖膜桥）；负值 = 焊盘与触点焊盘铜相连。"""
    contacts = [p for p in it['pads'] if p['circle'] and p['r'] > 0.8]
    web = []
    for r in (p for p in it['pads'] if p['ref'].startswith('R')):
        c = min(contacts, key=lambda c: ptrect(c['c'], r['rect']) - c['r'])
        web.append(dict(pad=f"{r['ref']}.{r['num']}", contact=c['ref'], gap_mm=round(ptrect(c['c'], r['rect']) - c['r'], 3)))
    return sorted(web, key=lambda w: w['gap_mm'])


def measure(b):
    it = items(b)
    tr = it['tr']
    (inter, inter_at), (intra, intra_at) = track_spacing(tr)
    edge = min(segdist(a, b_, e0, e1) - w / 2 for _, _, a, b_, w in tr for e0, e1 in it['segs'])
    hole = min((ptseg(c, a, b_) - r - w / 2 for _, _, a, b_, w in tr for c, r in it['circles']), default=None)
    via_edge = min(min(ptseg(v['c'], e0, e1) for e0, e1 in it['segs']) - v['r'] for v in it['vias'])
    dyn_vias = [dict(at=[round(v['c'][0], 3), round(v['c'][1], 3)], zone=n) for v in it['vias'] for n, (x0, y0, x1, y1) in it['dyn']
                if x0 - v['r'] <= v['c'][0] <= x1 + v['r'] and y0 - v['r'] <= v['c'][1] <= y1 + v['r']]
    geom = dict(min_center_between_different_nets_mm=round(inter, 4), at=inter_at,
                min_center_within_pair_mm=round(intra, 4), within_pair_at=intra_at,
                min_track_copper_to_outline_mm=round(edge, 4), min_track_copper_to_hole_edge_mm=None if hole is None else round(hole, 4),
                min_via_copper_to_outline_mm=round(via_edge, 4), vias=len(it['vias']), vias_in_dynamic_zones=len(dyn_vias), dyn_via_list=dyn_vias,
                track_widths=sorted({round(w, 3) for *_, w in tr}))
    web = res_web(it)
    res_pads = [p for p in it['pads'] if p['ref'].startswith('R')]
    contacts = [p for p in it['pads'] if p['circle'] and p['r'] > 0.8]
    # 尾部过孔到金手指：铜到铜、孔边到焊盘边
    fingers = [p for p in it['pads'] if p['ref'].startswith('TAIL')]
    vf = min(((ptrect(v['c'], f['rect']) - v['r'], ptrect(v['c'], f['rect']) - v['drill'], v, f) for v in it['vias'] for f in fingers), key=lambda t: t[0])
    tail = dict(finger_face='F' if all(f['F'] and not f['B'] for f in fingers) else 'B',
                via_copper_to_finger_copper_mm=round(vf[0], 3), via_hole_edge_to_finger_pad_mm=round(vf[1], 3),
                nearest=dict(via=[round(vf[2]['c'][0], 3), round(vf[2]['c'][1], 3)], via_net=vf[2]['net'], finger=f"{vf[3]['ref']}.{vf[3]['num']}"),
                finger_end_x=round(max(f['rect'][2] for f in fingers), 3))
    # 补强：岛触点被盖住的比例（Ø1.0 端子孔外到 Ø1.8 焊盘边的环），串阻焊盘有没有被盖
    st = {}
    for L, rings in it['rings'].items():
        if not rings:
            continue
        m = material(rings)
        cov = []
        for c in contacts:
            ann = pset(circle_pts(*c['c'], c['r']))
            ann.BooleanSubtract(pset(circle_pts(*c['c'], 0.5 + 1e-3)))
            a_c = area(_and(m, ann))
            if a_c > 1e-6:
                cov.append(dict(contact=c['ref'], covered=round(a_c / area(ann), 4)))
        res_cov = sum(1 for r in res_pads if area(_and(m, pset([(r['rect'][0], r['rect'][1]), (r['rect'][2], r['rect'][1]), (r['rect'][2], r['rect'][3]), (r['rect'][0], r['rect'][3])]))) > 1e-6)
        st[L] = dict(pieces=m.OutlineCount(), area_mm2=round(area(m), 2), island_contacts_backed=len(cov),
                     min_contact_coverage=min((c['covered'] for c in cov), default=None), res_pads_covered=res_cov)
    mb = material(it['rings']['User.2' if tail['finger_face'] == 'F' else 'User.1'])
    fingers_backed = all(mb.Contains(P(*f['c'])) for f in fingers)
    # 内层 GND：孤铜、碎块、碎孔、动态区实铜比例
    cu = {}
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for L in (k.In1_Cu, k.In2_Cu):
            if z.IsOnLayer(L):
                cu.setdefault(b.GetLayerName(L), k.SHAPE_POLY_SET()).BooleanAdd(z.GetFilledPolysList(L))
    able = k.SHAPE_POLY_SET(it['board'])
    able.Inflate(-round(0.305e6), k.CORNER_STRATEGY_ROUND_ALL_CORNERS, 2000)
    gnd_pts = [v['c'] for v in it['vias'] if v['net'] == 'AGND'] + [p['c'] for p in it['pads'] if p['net'] == 'AGND']
    mesh = {}
    for L, c in cu.items():
        c = k.SHAPE_POLY_SET(c); c.Simplify()
        pieces, orphans, small_pieces = c.OutlineCount(), [], []
        for i in range(c.OutlineCount()):
            ol = k.SHAPE_POLY_SET(); ol.AddOutline(c.Outline(i))
            for j in range(c.HoleCount(i)):
                ol.AddHole(c.Hole(i, j))
            a_ = abs(c.Outline(i).Area()) / 1e12
            if not any(ol.Contains(P(*q)) for q in gnd_pts):
                orphans.append(dict(at=list(chain_pts(c.Outline(i))[0]), area=round(a_, 4)))
            if a_ < 0.5:
                small_pieces.append(dict(at=list(chain_pts(c.Outline(i))[0]), area=round(a_, 4)))
        nh, voids_min, small = 0, 9.0, []
        for i in range(c.OutlineCount()):
            for j in range(c.HoleCount(i)):
                h = c.Hole(i, j)
                a_, per = abs(h.Area()) / 1e12, h.Length() / 1e6
                wdt = 4 * a_ / per if per else 0
                nh += 1
                voids_min = min(voids_min, wdt)
                if wdt < 0.15:
                    small.append([round(h.CPoint(0).x / 1e6, 3), round(h.CPoint(0).y / 1e6, 3), round(wdt, 4)])
        regs = []
        for name, (x0, y0, x1, y1) in it['dyn']:
            r = _and(it['board'], pset([(x0 - 0.55, y0), (x1 + 0.55, y0), (x1 + 0.55, y1), (x0 - 0.55, y1)]))
            ra = _and(able, r)
            cr = _and(c, r)
            regs.append(dict(zone=name, copper_vs_board=round(area(cr) / area(r), 3), copper_vs_copperable=round(area(cr) / area(ra), 3)))
        mesh[L] = dict(copper_pieces=pieces, orphan_pieces=len(orphans), orphan_list=orphans[:5], pieces_under_0p5mm2=len(small_pieces),
                       regions=regs, max_copper_vs_copperable=max(x['copper_vs_copperable'] for x in regs),
                       min_copper_vs_copperable=min(x['copper_vs_copperable'] for x in regs),
                       mean_copper_vs_copperable=round(sum(x['copper_vs_copperable'] for x in regs) / len(regs), 3),
                       holes_in_copper=nh, min_void_width_4A_over_P=round(voids_min, 4), voids_narrower_than_0p15=len(small), narrow_voids_at=small[:10])
    return dict(geometry=geom, res_pad_to_contact=web, tail=tail,
                stiffener=dict(layers=st, fingers_backed_on_opposite_face=fingers_backed), mesh=mesh)


if __name__ == '__main__':
    d = Path(sys.argv[1])
    print(json.dumps({s: measure(k.LoadBoard(str(d / f'strap-{s}.kicad_pcb'))) for s in 'ab'}, ensure_ascii=False, indent=1, default=str))
