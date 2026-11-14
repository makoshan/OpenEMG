#!/usr/bin/env python3
"""双 30 针表带保护软板（配合 16ch-u9-dual30 旗舰版 AFE-30P 双面 1.00mm 广濑 FH34SRJ-30S-0.5SH(50) 座子）：
两片四层柔性板（strap-30p-a / strap-30p-b），承载 32×100 kΩ (0402 C25741) 采样保护串阻 + 2×200 kΩ (0603 C25811) 偏置保护串阻。

叠层（从表带往皮肤）：25 mm 表带 → 本软板（背胶贴表带，F 面焊盘朝皮肤）→ 0.8 TPU 开孔层（孔 Φ6.5）→ Φ6×2.0 镀金铜片回流焊在 F 面焊盘上。
KiCad 自带 python3 运行：python3 -B build.py
- 触点布局与 D2 表带电极层完全同源（复用 hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/build.py）：
  胶囊底 2 路（CH1/CH2 两对 + EB1/EB2 共 6 颗 F 面贴肤焊盘）+ 表带 14 路（北 CH3/CH4，南 CH5–CH16）。
- 双 30P 金手指尾部适配 AFE-30P 正反面 60 mil (1.524 mm) 横向错位：
  - 片 A（插 Top 面 FPC1，广濑 FH34SRJ-30S-0.5SH(50) C324727）：
    30 脚间距 0.50 mm，尾宽 15.50 mm，中心 y = 49.6056 mm（盒 X = -0.3944 mm），yA(p) = 42.3556 + (p - 1) * 0.5；
    1/2 脚（REF1/REF2）与 27 脚（WCT）做孤立裸金手指（不连贴肤铜），29 脚为 BIAS_DRV1，3..25 脚对应 CH1..CH8（P 在小 y、N 在大 y）。
  - 片 B（插 Bottom 面 FPC3，广濑 FH34SRJ-30S-0.5SH(50) C324727）：
    30 脚间距 0.50 mm，尾宽 15.50 mm，中心 y = 48.0816 mm（盒 X = -1.9184 mm），yB(p) = 55.3316 - (p - 1) * 0.5；
    1/2 脚（REF1/REF2）与 27 脚（WCT2）做孤立裸金手指，29 脚为 BIAS_DRV12，25..3 脚对应 CH16..CH9（N 在小 y、P 在大 y）。
- 针脚真源直接从 ../AFE-30P.epro 逐脚经 15 kΩ 排阻（U3..U10）追溯至双 ADS1298（U1/U2）差分输入脚，零硬编码。
"""
import ast
import csv
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path

import pcbnew as k

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TPU = ROOT / 'hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/build.py'
AFE_EPRO = HERE.parent / 'AFE-30P.epro'

mm = k.ToMM
W = 0.15
HP = 0.15
VIA = (0.5, 0.25)
TOL = 0.002
YC = 50.0
EDGE_M = 0.315
PM = EDGE_M + HP + W / 2
PREQ = 0.82
R_VIA = VIA[0] / 2 + 0.15 + W / 2 + HP + 0.02
R_PAD = 0.9 + 0.15 + W / 2 + HP + 0.02
MESH = dict(pitch=0.60, hole=0.42, ext=0.55)
STIFF_T_TAIL = 0.10
STIFF_T_ISL = 0.20
FINGER = dict(w=0.30, l=1.5, setback=0.2, pitch=0.5, n=30)
TAIL_W = 15.50
STIFF = 2.5

YC_TA = 49.6056
YC_TB = 48.0816
TA_Y0, TA_Y1 = round(YC_TA - TAIL_W / 2, 4), round(YC_TA + TAIL_W / 2, 4)   # 41.8556 .. 57.3556
TB_Y0, TB_Y1 = round(YC_TB - TAIL_W / 2, 4), round(YC_TB + TAIL_W / 2, 4)   # 40.3316 .. 55.8316


def tpu_consts():
    want = ('PITCH', 'NORTH_YS', 'SOUTH_YS', 'STRAP_W', 'LAYER_W', 'PN', 'DISC_D', 'HOLE_CLEAR')
    ns = {}
    for node in ast.parse(TPU.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in want:
            exec(compile(ast.Module([node], []), str(TPU), 'exec'), ns)
    return {n: ns[n] for n in want}


TC = tpu_consts()
assert TC['PN'] == 18.0 and TC['PITCH'] == 8.0 and TC['DISC_D'] == 6.0, TC
to_x = lambda Y: round(58.0 - Y, 6)  # noqa: E731
PN_Y = (round(YC - TC['PN'] / 2, 6), round(YC + TC['PN'] / 2, 6))
ISL_Y0, ISL_Y1 = round(YC - TC['LAYER_W'] / 2, 6), round(YC + TC['LAYER_W'] / 2, 6)
NORTH_CH = (3, 4)
assert tuple(TC['NORTH_YS']) == (34.0, 42.0), ('TPU 层北排应为 (34, 42)', TC['NORTH_YS'])
N_ISL = {ch: to_x(Y) for ch, Y in zip(NORTH_CH, TC['NORTH_YS'])}
S_ISL = {ch: to_x(Y) for ch, Y in zip(range(5, 17), TC['SOUTH_YS'])}
A_ISL = {ch: S_ISL[ch] for ch in range(5, 9)}
B_ISL = {ch: S_ISL[ch] for ch in range(9, 17)}

PAD_D = TC['DISC_D'] + 2 * 0.25
PAD_R = PAD_D / 2
STIFF_D = 7.2
ISL_HW = 3.6
SLIT_C = 55.6
RES = (1.5, 4.3)
RPAD = (0.54, 0.64)
LV = 0.74
E_IN = 0.3

NORTH = (ISL_Y0, 40.85)
ABAND = (50.46, 54.1)
B_BAND = (46.32, 53.2)
FORK_GAP = 0.35 + R_VIA
A_LOW = [54.0, 55.2, 56.4, 57.6]

Z_FLOOR_IN, Z_SHELL_OUT, T_FPC = 1.00, 0.15, 0.203
DZ_TAIL = round((Z_FLOOR_IN + T_FPC / 2) - (Z_SHELL_OUT - T_FPC - T_FPC / 2), 4)
TAIL_EXT = 1.30
assert TAIL_EXT >= DZ_TAIL
BEND_X = 39.96
X_TAIL_VIA = 40.3


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    return dx / L, dy / L


def offset(pts, d):
    out = []
    for i, p in enumerate(pts):
        if i == 0:
            u = unit(pts[0], pts[1]); n = (-u[1], u[0])
        elif i == len(pts) - 1:
            u = unit(pts[-2], pts[-1]); n = (-u[1], u[0])
        else:
            u1, u2 = unit(pts[i - 1], p), unit(p, pts[i + 1])
            n1, n2 = (-u1[1], u1[0]), (-u2[1], u2[0])
            c = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            n = ((n1[0] + n2[0]) / c, (n1[1] + n2[1]) / c)
        out.append((p[0] + d * n[0], p[1] + d * n[1]))
    return out


def clean(pts):
    o = []
    for p in pts:
        p = (round(p[0], 6), round(p[1], 6))
        if o and math.dist(o[-1], p) < 1e-6:
            continue
        if len(o) >= 2:
            a, b = o[-2], o[-1]
            cr = (b[0] - a[0]) * (p[1] - b[1]) - (b[1] - a[1]) * (p[0] - b[0])
            dt = (b[0] - a[0]) * (p[0] - b[0]) + (b[1] - a[1]) * (p[1] - b[1])
            if abs(cr) < 1e-9 and dt > 0:
                o[-1] = p
                continue
        o.append(p)
    return o


def plen(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


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


def segrect(a, b, r):
    x0, y0, x1, y1 = r
    if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in (a, b)):
        return 0.0
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return min(segdist(a, b, c[i], c[(i + 1) % 4]) for i in range(4))


def hairpin(pts, extra, a=0.25):
    (x1, y1), (ex, ey) = pts[0], pts[-1]
    sg = 1 if ey > y1 else -1
    dxs = 1 if ex > x1 else -1
    assert abs(ex - x1) >= 2 * a + 0.1, (pts, a)
    h = (plen(pts) + extra - (abs(ey - y1) + abs(ex - x1) - 4 * a + 2 * a * math.sqrt(2))) / 2
    assert h >= a + 0.1, ('回头弯太矮，用凸起', h)
    top = y1 - sg * h
    return [(x1, y1), (x1, top + sg * a), (x1 + dxs * a, top), (ex - dxs * a, top), (ex, top + sg * a), (ex, ey)], round(h, 4)


def bump(pts, i, e, away, end_margin=0.0):
    a, b = pts[i], pts[i + 1]
    ux, uy = unit(a, b)
    L = math.dist(a, b) - end_margin
    b = (a[0] + ux * L, a[1] + uy * L)
    need = 2 * e + 0.3
    assert L >= need + 0.2, f'段长 {L:.3f} 放不下凸起 {need:.3f}'
    nx, ny = -uy, ux
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if (away[0] - mx) * nx + (away[1] - my) * ny > 0:
        nx, ny = -nx, -ny
    h = e + 0.15
    p1 = (mx - ux * h, my - uy * h)
    p4 = (mx + ux * h, my + uy * h)
    p2 = (p1[0] + (ux + nx) * e, p1[1] + (uy + ny) * e)
    p3 = (p4[0] + (-ux + nx) * e, p4[1] + (-uy + ny) * e)
    return pts[:i + 1] + [p1, p2, p3, p4] + pts[i + 1:], (round(nx, 3), round(ny, 3))


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def circ(x, y, r, n=48):
    return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def lanes(band, n):
    y0, y1 = band
    Wd = y1 - y0
    if n == 0:
        return []
    if n == 1:
        return [round((y0 + y1) / 2, 4)]
    cell = Wd / n
    if cell / 2 >= PM:
        return [round(y0 + cell * (i + 0.5), 4) for i in range(n)]
    p = (Wd - 2 * PM) / (n - 1)
    assert p >= 0.78, (band, n, p)
    return [round(y0 + PM + p * i, 4) for i in range(n)]


def plan(Y, T, x0, obst=(), preq=PREQ, step=0.01):
    n = len(Y)
    gaps = [b - a for a, b in zip(Y, Y[1:])] + [b - a for a, b in zip(T, T[1:])]
    preq = min([preq] + gaps) - 1e-6
    assert preq >= 0.78 - 1e-6, ('道太挤', Y, T)
    d = [round(t - y, 6) for y, t in zip(Y, T)]
    far = x0 + max([abs(v) for v in d] + [0]) + 12

    def segs(i, xs):
        if abs(d[i]) < 1e-9:
            return [((x0, Y[i]), (far, Y[i]))]
        e = (xs + abs(d[i]), T[i])
        return [((x0, Y[i]), (xs, Y[i])), ((xs, Y[i]), e), (e, (far, T[i]))]

    placed = {}

    def ok(i, xs):
        S = [s for s in segs(i, xs) if math.dist(*s) > 1e-9]
        for q in placed.values():
            for s in S:
                for r in q:
                    if math.dist(*r) > 1e-9 and segdist(*s, *r) < preq - 1e-9:
                        return False
        for c, r in obst:
            for s in S:
                if (ptseg(c, *s) if len(c) == 2 else segrect(*s, c)) < r - 1e-9:
                    return False
        return True

    XS = [None] * n
    zeros = [i for i in range(n) if abs(d[i]) < 1e-9]
    ups = sorted((i for i in range(n) if d[i] < -1e-9), key=lambda i: Y[i])
    downs = sorted((i for i in range(n) if d[i] > 1e-9), key=lambda i: -Y[i])
    for i in zeros:
        assert ok(i, x0), ('静止的对碰障碍', i, Y[i])
        XS[i] = x0; placed[i] = segs(i, x0)
    for i in ups + downs:
        xs = x0
        while not ok(i, xs):
            xs = round(xs + step, 4)
            assert xs < x0 + 15, ('换道放不下', Y, T, i)
        XS[i] = xs; placed[i] = segs(i, xs)
    return XS, d


# ---------- 针脚真源：直接读取 ../AFE-30P.epro ----------
AUX_MAP = {
    'AGND': 'AGND',
    'BIAS_DRV1': 'BIAS_DRV1',
    'BIAS_DRV12': 'BIAS_DRV12',
    'REF1': '',
    'REF2': '',
    'WCT': '',
    'WCT2': '',
}


def afe30p_interface():
    raw_bytes = AFE_EPRO.read_bytes()
    with zipfile.ZipFile(AFE_EPRO) as z:
        pcb_name = next(n for n in z.namelist() if n.endswith('.epcb'))
        rows_raw = [json.loads(l) for l in z.read(pcb_name).splitlines() if l.startswith(b'[')]
    rows_raw = rows_raw[max(i for i, r in enumerate(rows_raw) if r[:2] == ['DOCTYPE', 'PCB']):]
    comps = {r[1]: r for r in rows_raw if r[0] == 'COMPONENT'}
    des_of = {r[3]: r[8] for r in rows_raw if r[0] == 'ATTR' and r[3] in comps and r[7] == 'Designator'}
    pins, bynet = {}, {}
    for r in rows_raw:
        if r[0] == 'PAD_NET' and r[1] in des_of and str(r[2]).isdigit():
            d, p, net = des_of[r[1]], int(r[2]), r[3]
            pins.setdefault(d, {})[p] = net
            if net:
                bynet.setdefault(net, []).append((d, p))

    adc_pin_role = {}
    for ch in range(1, 9):
        adc_pin_role[('U1', 17 - 2 * ch)] = (1, ch, 'N')
        adc_pin_role[('U1', 18 - 2 * ch)] = (1, ch, 'P')
        adc_pin_role[('U2', 17 - 2 * ch)] = (2, ch, 'N')
        adc_pin_role[('U2', 18 - 2 * ch)] = (2, ch, 'P')
    net_to_adc = {}
    for (adc, apin), info in adc_pin_role.items():
        anet = pins[adc].get(apin, '')
        if anet:
            net_to_adc[anet] = (adc, apin, *info)

    arrays = {f'U{i}' for i in range(3, 11)}
    out_rows = []
    for con in ('FPC1', 'FPC3'):
        for n in range(1, 31):
            net = pins[con][n]
            row = dict(connector=con, pin=n, afe_net=net, array='', array_in='', array_out='', adc='', adc_pin='', adc_net='', strap_net='')
            if net in AUX_MAP:
                row['strap_net'] = AUX_MAP[net]
            else:
                (ar, ap), = [(d, dp) for d, dp in bynet[net] if d in arrays]
                opp = 9 - ap
                far = pins[ar][opp]
                adc, adp, chip_idx, ch_local, pol = net_to_adc[far]
                ch_global = ch_local + (8 if chip_idx == 2 else 0)
                row.update(array=ar, array_in=str(ap), array_out=str(opp), adc=adc, adc_pin=str(adp), adc_net=far,
                           strap_net=f'CH{ch_global}_{pol}')
            out_rows.append(row)
    return out_rows, hashlib.sha256(raw_bytes).hexdigest()


AFE_ROWS, AFE_SHA = afe30p_interface()
with (HERE / 'afe30p-interface.csv').open('w', newline='', encoding='utf-8') as fh:
    w_ = csv.DictWriter(fh, fieldnames=list(AFE_ROWS[0]), lineterminator='\n'); w_.writeheader(); w_.writerows(AFE_ROWS)
pin_net = {con: {r['pin']: r['strap_net'] for r in AFE_ROWS if r['connector'] == con} for con in ('FPC1', 'FPC3')}
assert sorted(n for c in pin_net.values() for n in c.values() if n.startswith('CH')) == sorted(f'CH{c}_{p}' for c in range(1, 17) for p in 'PN')


def aux_parts():
    return json.loads((HERE / 'capsule-aux-baseline.json').read_text(encoding='utf-8'))


AUXP = aux_parts()


def contact(ref):
    return AUXP[ref]['x'], AUXP[ref]['y']


R_BIG = PAD_R + 0.15 + W / 2 + HP + 0.02
EB_PAD_D = 4.5
EB_DISC = dict(d=3.0, t=2.0, shape='方形 3×3×2（d 为边长）')
EB2_JOINT_DRILL = 0.8
CAP_PAD_D = {'E1N': PAD_D, 'E1P': PAD_D, 'E2N': PAD_D, 'E2P': PAD_D, 'EB1': EB_PAD_D, 'EB2': EB_PAD_D}
CAP_RES = {
    'R2': ('a', (50.5, 39.5), +1), 'R1': ('a', (50.5, 60.5), +1),
    'R4': ('a', (65.5, 39.5), -1), 'R3': ('a', (65.5, 60.5), -1),
    'R33': ('a', (59.4, 58.6), -1), 'R34': ('b', (45.5, 50.0), -1),
}


def pad(num, net, x, y, w, h, circle=False, drill=None):
    return dict(num=num, net=net, x=round(x, 4), y=round(y, 4), w=w, h=h, circle=circle, drill=drill)


def cap_parts():
    out = []
    for ref in ('E1N', 'E1P', 'E2N', 'E2P', 'EB1', 'EB2'):
        d = AUXP[ref]
        (q,) = d['pads']
        out.append(dict(kind='part', piece=d['piece'], ref=ref, x=d['x'], y=d['y'], layer='F.Cu', value='贴肤焊盘',
                        pads=[pad(q['num'], q['net'], d['x'], d['y'], CAP_PAD_D[ref], CAP_PAD_D[ref], circle=True)]))
    for ref, (piece, (cx, cy), side) in CAP_RES.items():
        d = AUXP[ref]
        assert d['layer'] == 'B.Cu' and d['piece'] == piece, ref
        big = d['value'] == '200k'
        hp_, sz = (0.825, (0.95, 1.05)) if big else (0.51, RPAD)
        pads = []
        for q in d['pads']:
            dx = side * hp_ if not q['net'].endswith('_E') else -side * hp_
            pads.append(pad(q['num'], q['net'], cx + dx, cy, *sz))
        out.append(dict(kind='part', piece=piece, ref=ref, x=cx, y=cy, layer='B.Cu', value=d['value'], pads=pads))
    d = AUXP['EB2']
    (q,) = d['pads']
    out.append(dict(kind='part', piece='a', ref='EB2A', x=d['x'], y=d['y'], layer='F.Cu', value='REF 贴肤焊盘（对焊 B 片 EB2）',
                    pads=[pad(q['num'], q['net'], d['x'], d['y'], EB_PAD_D, EB_PAD_D, circle=True, drill=EB2_JOINT_DRILL)]))
    return out


CAP = cap_parts()


def cap_pad(ref, which):
    f = next(f for f in CAP if f['ref'] == ref)
    (q,) = [q for q in f['pads'] if q['net'].endswith('_E') == (which == 'elec')]
    return q['x'], q['y']


def cap_elec(pc, ref, cref):
    ex, ey = cap_pad(ref, 'elec')
    cx, cy = contact(cref)
    s = 1 if ey > cy else -1
    vy = round(ey + s * 1.25, 6)
    assert math.dist((ex, vy), (cx, cy)) >= PAD_R + VIA[0] / 2 + 0.15, (ref, vy)
    yin = round(cy + s * (math.sqrt(PAD_R ** 2 - (ex - cx) ** 2) - E_IN), 4)
    net = next(q['net'] for f in CAP if f['ref'] == ref for q in f['pads'] if q['net'].endswith('_E'))
    pc.tr(net, 'B', [(ex, ey), (ex, vy)], 'elec')
    pc.via(net, (ex, vy))
    pc.tr(net, 'F', [(ex, vy), (ex, yin)], 'elec')


class Piece:
    def __init__(self, name):
        self.name = name
        self.traces = []
        self.vias = []
        self.fps = []
        self.shapes = []
        self.holes = []
        self.cut = []
        self.dyn = []
        self.stiff = []
        self.legs = {}
        self.C = {}
        self.start = {}
        self.lanes = {}

    def tr(self, net, layer, pts, tag=''):
        self.traces.append([net, layer, clean(pts), tag])
        return len(self.traces) - 1

    def via(self, net, p):
        self.vias.append((net, (round(p[0], 6), round(p[1], 6))))

    def advance(self, order, Y, T, x0, obst=()):
        XS, d = plan(Y, T, x0, obst)
        ends = []
        for ch, y, t, xs, dd in zip(order, Y, T, XS, d):
            assert abs(self.C[ch][-1][1] - y) < 1e-6, (self.name, ch, self.C[ch][-1], y)
            if abs(dd) > 1e-9:
                self.C[ch] += [(xs, y), (round(xs + abs(dd), 6), t)]
            ends.append(round(xs + abs(dd), 6))
        return ends


def place_aux(pc):
    for d in CAP:
        if d['piece'] == pc.name:
            pc.fps.append(d)


def refl(cx, pts):
    return [(round(2 * cx - x, 6), round(2 * YC - y, 6)) for x, y in pts]


def contact_block(pc, ch, cx):
    for pol, y in zip('NP', PN_Y):
        pc.fps.append(dict(kind='part', ref=f'E{ch}{pol}', x=cx, y=y, layer='F.Cu', value='贴肤焊盘',
                           pads=[pad('1', f'CH{ch}_{pol}_E', cx, y, PAD_D, PAD_D, circle=True)]))
        pc.stiff.append(dict(circle=(cx, y, STIFF_D / 2), side='B', name=f'E{ch}{pol}补强', thickness=STIFF_T_ISL))
    rn = (cx - RES[0], YC - RES[1])
    rp = (cx + RES[0], YC + RES[1])
    pc.fps.append(dict(kind='part', ref=f'R{2 * ch}', x=rn[0], y=rn[1], layer='F.Cu', value='100k',
                       pads=[pad('1', f'CH{ch}_N', rn[0] + 0.51, rn[1], *RPAD), pad('2', f'CH{ch}_N_E', rn[0] - 0.51, rn[1], *RPAD)]))
    pc.fps.append(dict(kind='part', ref=f'R{2 * ch - 1}', x=rp[0], y=rp[1], layer='F.Cu', value='100k',
                       pads=[pad('1', f'CH{ch}_P', rp[0] - 0.51, rp[1], *RPAD), pad('2', f'CH{ch}_P_E', rp[0] + 0.51, rp[1], *RPAD)]))
    ex, ey = rn[0] - 0.51, rn[1]
    y_in = PN_Y[0] + math.sqrt(PAD_R ** 2 - (ex - cx) ** 2) - E_IN
    nf = [(ex, ey), (ex, round(y_in, 4))]
    pc.tr(f'CH{ch}_N_E', 'F', nf, 'elec')
    pc.tr(f'CH{ch}_P_E', 'F', refl(cx, nf), 'elec')
    return (rn[0] + 0.51, rn[1]), (rp[0] - 0.51, rp[1])


def island_obst(cx):
    out = []
    for sx, y in ((-1, YC - RES[1]), (1, YC + RES[1])):
        for dx in (-0.51, 0.51):
            x = cx + sx * RES[0] + dx
            out.append(((x - RPAD[0] / 2, y - RPAD[1] / 2, x + RPAD[0] / 2, y + RPAD[1] / 2), 0.15 + HP + W / 2 + 0.02))
    out += [((cx - RES[0] + 0.51, YC - RES[1] - LV), R_VIA), ((cx + RES[0] - 0.51, YC + RES[1] + LV), R_VIA)]
    return out


def leg(pc, net, via, pad_xy, up):
    (x, y), (px, py) = via, pad_xy
    dx = abs(x - px)
    ey = py - LV if up else py + LV
    if up:
        yk = ey + dx + 0.4
        assert y >= yk - 1e-9, (net, y, yk)
        pts = [(x, y), (x, yk), (px, ey + 0.4), (px, ey)]
    else:
        yk = ey - dx - 0.4
        assert y <= yk + 1e-9, (net, y, yk)
        pts = [(x, y), (x, yk), (px, ey - 0.4), (px, ey)]
    pc.legs[net] = pc.tr(net, 'B', pts, 'leg')
    pc.via(net, (px, ey))
    pc.tr(net, 'F', [(px, ey), (px, py)], 'leg-stub')


def peel_entry(xv, top_net_is_p, yc):
    up = [(xv - 0.2, yc - HP), (xv, yc - 0.35)]
    dn = [(xv - 0.2, yc + HP), (xv, yc + 0.35), (xv + 0.65, yc + 0.35)]
    return (dn, up) if top_net_is_p else (up, dn)


def pair_traces(pc, ch, layer, center, n_sign, n_end, p_end, tag):
    n_start, p_start = pc.start[ch]
    center = clean(center)
    Nc, Pc = offset(center, n_sign * HP), offset(center, -n_sign * HP)
    assert math.dist(n_start[-1], Nc[0]) < 1e-6 and math.dist(p_start[-1], Pc[0]) < 1e-6, (ch, 'start')
    assert math.dist(n_end[0], Nc[-1]) < 1e-6 and math.dist(p_end[0], Pc[-1]) < 1e-6, (ch, 'end', n_end[0], Nc[-1])
    pc.tr(f'CH{ch}_N', layer, n_start + Nc[1:] + n_end[1:], tag)
    pc.tr(f'CH{ch}_P', layer, p_start + Pc[1:] + p_end[1:], tag)


def fingers(pc, ref, con, tip, face, ypin):
    xc = round(tip + FINGER['setback'] + FINGER['l'] / 2, 4)
    pads = [(str(p), pin_net[con][p], xc, ypin(p)) for p in range(1, FINGER['n'] + 1)]
    ys = [ypin(1), ypin(FINGER['n'])]
    gang = (tip, round(tip + FINGER['setback'] + FINGER['l'] - 0.3, 4), round(min(ys) - FINGER['w'] / 2 - 0.15, 4), round(max(ys) + FINGER['w'] / 2 + 0.15, 4))
    pc.fps.append(dict(ref=ref, kind='finger', face=face, pads=pads, gang=gang))
    pc.gang = gang
    return xc, round(tip + FINGER['setback'] + FINGER['l'], 4)


def conv(pc, con, ypin, xc, xe, ch):
    pp = next(p for p, n in pin_net[con].items() if n == f'CH{ch}_P')
    pn = next(p for p, n in pin_net[con].items() if n == f'CH{ch}_N')
    yp, yn = ypin(pp), ypin(pn)
    assert abs(abs(yp - yn) - 0.5) < 1e-6
    s = 1 if yn < yp else -1
    pc.start[ch] = ([(xc, yn), (xe, yn), (round(xe + 0.1, 6), round(yn + 0.1 * s, 6))],
                    [(xc, yp), (xe, yp), (round(xe + 0.1, 6), round(yp - 0.1 * s, 6))])
    yc = round((yp + yn) / 2, 6)
    pc.C[ch] = [(round(xe + 0.1, 6), yc)]
    return yc


def gnd_tail(pc, con, ypin, xc, xe, xv, via_at=None):
    pins = [p for p in range(1, FINGER['n'] + 1) if pin_net[con][p] == 'AGND']
    runs = []
    for p in pins:
        if runs and p == runs[-1][-1] + 1:
            runs[-1].append(p)
        else:
            runs.append([p])
    for run in runs:
        if len(run) > 1:
            pc.tr('AGND', 'F', [(xe - 0.1, ypin(run[0])), (xe - 0.1, ypin(run[-1]))], 'gnd')
        t = run[len(run) // 2]
        v = (via_at or {}).get(t, (xv, ypin(t)))
        y0 = ypin(t)
        if abs(v[1] - y0) > 1e-6:
            # 135° 标准拐角进入错位过孔，确保 route_lint odd_angle == 0
            dy = v[1] - y0
            xk = round(v[0] - abs(dy), 6)
            assert xk > xe, (con, t, xk, xe, v)
            pc.tr('AGND', 'F', [(xc, y0), (xk, y0), v], 'gnd')
        else:
            pc.tr('AGND', 'F', [(xc, y0), v], 'gnd')
        pc.via('AGND', v)
    return runs


def stitch(pc, pts):
    for p in pts:
        pc.via('AGND', p)


def tail_stiff(pc, x0, x1, y0, y1, side, name):
    pc.stiff.append(dict(rect=(round(x0, 4), round(x1, 4), round(y0, 4), round(y1, 4)), side=side, name=name, thickness=STIFF_T_TAIL))


def islands_outline(pc, cxs):
    cxs = sorted(cxs)
    pc.shapes.append(rect(cxs[0] - ISL_HW, cxs[-1] + ISL_HW, ISL_Y0, ISL_Y1))
    for a, b in zip(cxs, cxs[1:]):
        xb = (a + b) / 2
        hw = (b - a) / 2 - ISL_HW
        pc.cut += [rect(xb - hw, xb + hw, SLIT_C, ISL_Y1 + 1.0), circ(xb, SLIT_C, hw, 64)]
        pc.dyn.append((xb - hw - 0.3, xb + hw + 0.3, ISL_Y0 - 0.3, ISL_Y1 + 0.3, f'{pc.name.upper()}岛间{int(xb)}'))


def hop(pc, ch, xv, yc, layer, top_is_p, n_sign, tag):
    pc.C[ch] += [(round(xv - 0.2, 6), yc)]
    ne, pe = peel_entry(xv, top_is_p, yc)
    pair_traces(pc, ch, layer, pc.C[ch], n_sign, ne, pe, tag)
    up = [(xv, round(yc - 0.35, 6)), (round(xv + 0.2, 6), round(yc - HP, 6)), (round(xv + 0.85, 6), round(yc - HP, 6))]
    lo = [(round(xv + 0.65, 6), round(yc + 0.35, 6)), (round(xv + 0.85, 6), round(yc + HP, 6))]
    n_st, p_st = (lo, up) if top_is_p else (up, lo)
    pc.via(f'CH{ch}_P', p_st[0]); pc.via(f'CH{ch}_N', n_st[0])
    pc.start[ch] = (n_st, p_st)
    pc.C[ch] = [(round(xv + 0.85, 6), yc)]


# =====================================================================
# 片 A：→ AFE-30P FPC1（Top 面，yA(1)=42.3556 .. yA(30)=56.8556）
# =====================================================================
A = Piece('a')
place_aux(A)
TA = round(30.16 - TAIL_EXT, 4)
yA = lambda p: round(42.3556 + (p - 1) * 0.5, 4)  # noqa: E731
xcA, xeA = fingers(A, 'TAIL_A', 'FPC1', TA, 'F', yA)
tail_stiff(A, TA, TA + STIFF, TA_Y0, TA_Y1, 'B', '尾A补强（B面，金手指背面）')
A.dyn.append((round(32.71 - TAIL_EXT, 4), BEND_X, TA_Y0, TA_Y1, 'A尾折弯'))
A.gnd_runs = gnd_tail(A, 'FPC1', yA, xcA, xeA, X_TAIL_VIA, {30: (40.75, 57.00)})
A_TAIL_VIAS = [(p, R_VIA) for n, p in A.vias if n == 'AGND']

# --- BIAS_DRV1（29 脚，y = 56.3556）：F 出尾 → 过孔 (46.8, 58.6) → B 面到 R33 → 过孔 → F 面进 EB1 ---
yb = yA(29)
XB_V, Y_BIAS = 46.8, 58.6
assert cap_pad('R33', 'tail')[1] == Y_BIAS
A.tr('BIAS_DRV1', 'F', [(xcA, yb), (41.2, yb), (round(41.2 + Y_BIAS - yb, 6), Y_BIAS), (XB_V, Y_BIAS)], 'bias')
A.via('BIAS_DRV1', (XB_V, Y_BIAS))
A.tr('BIAS_DRV1', 'B', [(XB_V, Y_BIAS), cap_pad('R33', 'tail')], 'bias')
_ex, _ey = cap_pad('R33', 'elec')
XE_V = 61.6
_cx, _cy = contact('EB1')
assert math.dist((XE_V, _ey), (_cx, _cy)) >= EB_PAD_D / 2 + VIA[0] / 2 + 0.15
A.tr('BIAS_DRV1_E', 'B', [(_ex, _ey), (XE_V, _ey)], 'bias')
A.via('BIAS_DRV1_E', (XE_V, _ey))
A.tr('BIAS_DRV1_E', 'F', [(XE_V, _ey), (XE_V, _cy + 0.5), (XE_V + 0.5, _cy), (_cx - EB_PAD_D / 2 + E_IN, _cy)], 'bias')

# --- 胶囊底 CH1 & CH2 ---
X1H, X1F = 44.6, 57.0
yc1 = conv(A, 'FPC1', yA, xcA, xeA, 1)
hop(A, 1, X1H, yc1, 'F', True, +1, 'box')
A.C[1] += [(50.0, yc1), (round(50.0 + YC - yc1, 6), YC), (X1F - 0.2, YC)]
pair_traces(A, 1, 'B', A.C[1], +1, [(X1F - 0.2, YC + HP), (X1F + 0.45, YC + HP), (X1F + 0.65, YC - 0.05)],
            [(X1F - 0.2, YC - HP), (X1F, YC - 0.35)], 'box')
A.via('CH1_P', (X1F, YC - 0.35))
t1n, t1p = cap_pad('R2', 'tail'), cap_pad('R1', 'tail')
A.legs['CH1_N'] = A.tr('CH1_N', 'B', [(X1F + 0.65, YC - 0.05), (X1F + 0.65, t1n[1] + 0.4), (X1F + 0.25, t1n[1]), t1n], 'leg')
A.legs['CH1_P'] = A.tr('CH1_P', 'F', [(X1F, YC - 0.35), (X1F, t1p[1] + 0.4)], 'leg')
A.via('CH1_P', (X1F, t1p[1] + 0.4))
A.tr('CH1_P', 'B', [(X1F, t1p[1] + 0.4), (X1F - 0.4, t1p[1]), t1p], 'leg-b')

X2D, X2F, Y2_CORR = 55.6, 60.2, 46.50
yc2 = conv(A, 'FPC1', yA, xcA, xeA, 2)
A.C[2] += [(44.6, yc2), (round(44.6 + Y2_CORR - yc2, 6), Y2_CORR), (X2D, Y2_CORR), (round(X2D + YC - Y2_CORR, 6), YC), (X2F - 0.2, YC)]
pair_traces(A, 2, 'F', A.C[2], +1, [(X2F - 0.2, YC + HP), (X2F, YC + 0.35)],
            [(X2F - 0.2, YC - HP), (X2F + 0.45, YC - HP), (X2F + 0.65, YC + 0.05)], 'box')
A.via('CH2_N', (X2F, YC + 0.35))
t2n, t2p = cap_pad('R4', 'tail'), cap_pad('R3', 'tail')
A.legs['CH2_N'] = A.tr('CH2_N', 'B', [(X2F, YC + 0.35), (X2F, t2n[1] + 0.4), (X2F + 0.4, t2n[1]), t2n], 'leg')
A.legs['CH2_P'] = A.tr('CH2_P', 'F', [(X2F + 0.65, YC + 0.05), (X2F + 0.65, t2p[1] + 0.4)], 'leg')
A.via('CH2_P', (X2F + 0.65, t2p[1] + 0.4))
A.tr('CH2_P', 'B', [(X2F + 0.65, t2p[1] + 0.4), (X2F + 1.05, t2p[1]), t2p], 'leg-b')
for r_, c_ in (('R2', 'E1N'), ('R1', 'E1P'), ('R4', 'E2N'), ('R3', 'E2P')):
    cap_elec(A, r_, c_)

# --- 北支 CH3 / CH4 ---
NX = {3: 41.2, 4: 42.4}
NL_ = lanes(NORTH, 2)
NLANE = {4: NL_[0], 3: NL_[1]}
A.lanes['A北支'] = NL_
DN, TURN_A = 0.5, 0.6
north_ys = {}


def north_paths(ch, ys):
    cx = N_ISL[ch]
    yP = yA(next(p for p, n in pin_net['FPC1'].items() if n == f'CH{ch}_P'))
    yN = yA(next(p for p, n in pin_net['FPC1'].items() if n == f'CH{ch}_N'))
    assert abs(yN - yP - 0.5) < 1e-6, ch
    X, L, xd = NX[ch], NLANE[ch], cx + 0.3
    cpair = clean([(X + 0.15, yP - 0.85), (X + 0.15, L + DN), (X + 0.15 - DN, L), (xd + TURN_A, L), (xd, L + TURN_A), (xd, ys)])
    Nc, Pc = offset(cpair, HP), offset(cpair, -HP)
    assert math.dist(Pc[0], (X, yP - 0.85)) < 1e-6 and math.dist(Nc[0], (X + 0.3, yP - 0.85)) < 1e-6
    tn, tp = (cx - RES[0] + 0.51, YC - RES[1]), (cx + RES[0] - 0.51, YC + RES[1])
    yvn, yvp = tn[1] + LV, tp[1] - LV
    n_tail = [(cx + 0.15, ys), (cx - 0.25, ys + 0.4), (tn[0] + 0.4, ys + 0.4), (tn[0], ys), (tn[0], yvn)]
    p_tail = [(cx + 0.45, ys), (cx + 0.45, yvp - 0.4 - (tp[0] - cx - 0.45)), (tp[0], yvp - 0.4), (tp[0], yvp)]
    assert ys > yvn + 0.4 and yvp - 0.4 - (tp[0] - cx - 0.45) > ys, (ch, ys)
    return {f'CH{ch}_P': ([(xcA, yP), (X, yP)], [(X, yP), (X, yP - 0.85)] + Pc[1:] + p_tail[1:], (X, yP)),
            f'CH{ch}_N': ([(xcA, yN), (X + 0.65, yN)], [(X + 0.65, yN), (X + 0.65, yP - 0.5), (X + 0.3, yP - 0.85)] + Nc[1:] + n_tail[1:], (X + 0.65, yN))}


def tot(p3):
    return plen(clean(p3[0])) + plen(clean(p3[1]))


for ch in NORTH_CH:
    ys = YC
    for _ in range(3):
        pp = north_paths(ch, ys)
        d = tot(pp[f'CH{ch}_P']) - tot(pp[f'CH{ch}_N'])
        if abs(d) < 1e-7:
            break
        ys += d / 2
    assert 46.6 <= ys <= 52.5, (ch, ys)
    north_ys[ch] = round(ys, 4)
    tn_, tp_ = contact_block(A, ch, N_ISL[ch])
    for net, (fp, bp, v) in pp.items():
        A.tr(net, 'F', fp, 'north'); A.via(net, v); A.tr(net, 'B', bp, 'north')
        end, pad_ = bp[-1], (tn_ if net.endswith('_N') else tp_)
        A.via(net, end); A.tr(net, 'F', [end, pad_], 'leg-stub')
NORTH_VIAS = [(p, R_VIA) for n, p in A.vias if re.fullmatch(r'CH[34]_[PN]', n)]

# --- 南带 CH5–8 ---
order = [5, 6, 7, 8]
fy = [conv(A, 'FPC1', yA, xcA, xeA, ch) for ch in order]
A.advance(order, fy, A_LOW, 40.2, A_TAIL_VIAS + NORTH_VIAS + [((X1H, round(yc1 - 0.35, 6)), R_VIA), ((X1H + 0.65, round(yc1 + 0.35, 6)), R_VIA), ((XB_V, Y_BIAS), R_VIA)])
A.lanes['A盒底'] = A_LOW
XH0, XH2 = 45.5, 69.6
for ch, y in zip(order, A_LOW):
    assert A.C[ch][-1][0] <= XH0 - 0.2 + 1e-9, (ch, A.C[ch][-1])
    hop(A, ch, XH0, y, 'F', True, +1, 'band')
for ch, y in zip(order, A_LOW):
    hop(A, ch, XH2, y, 'B', True, +1, 'band')
LA = lambda n: lanes(ABAND, n) if n != 1 else [round(ABAND[0] + PM, 4)]  # noqa: E731
A.advance(order, A_LOW, LA(4), XH2 + 1.05, [(contact('EB1'), R_BIG), (contact('E2P'), R_BIG)])
A.lanes['A出盒带'] = LA(4)
rem, cur = list(order), LA(4)
for ch in order:
    cx = A_ISL[ch]
    n = len(rem)
    tn, tp = contact_block(A, ch, cx)
    ends = A.advance(rem, cur, [YC] + LA(n - 1), cx - 3.25, island_obst(cx))
    xv = round(cx - 0.325, 6)
    assert ends[0] <= xv - 0.4, (ch, ends[0], xv)
    A.C[ch] += [(xv - 0.2, YC)]
    ne, pe = peel_entry(xv, True, YC)
    pair_traces(A, ch, 'F', A.C[ch], +1, ne, pe, 'band')
    A.via(f'CH{ch}_P', (xv, YC - 0.35)); A.via(f'CH{ch}_N', (xv + 0.65, YC + 0.35))
    leg(A, f'CH{ch}_P', (xv, YC - 0.35), tp, up=False)
    leg(A, f'CH{ch}_N', (xv + 0.65, YC + 0.35), tn, up=True)
    rem, cur = rem[1:], LA(n - 1)
    if rem:
        A.lanes[f'A岛CH{ch}后'] = cur

# --- A 外形 ---
islands_outline(A, N_ISL.values())
_slit_yc = round((NORTH[1] + TA_Y0) / 2, 4)
_slit_r = round((TA_Y0 - NORTH[1]) / 2, 4)
A.shapes += [
    rect(N_ISL[3] + ISL_HW - 0.1, 39.6, *NORTH),
    rect(TA, 39.6, TA_Y0, TA_Y1),
    [(39.5, ISL_Y0), (75.0, ISL_Y0), (75.0, 63.0), (round(40.0 + (63.0 - TA_Y1), 4), 63.0), (40.0, TA_Y1), (39.5, TA_Y1)],
    rect(74.9, A_ISL[5] - ISL_HW + 0.1, *ABAND),
]
islands_outline(A, A_ISL.values())
A.cut += [rect(39.0, 39.5, NORTH[1], TA_Y0), circ(39.5, _slit_yc, _slit_r, 64)]
A.dyn += [(N_ISL[3] + ISL_HW + 0.6, 38.9, NORTH[0] - 0.3, NORTH[1] + 0.15, 'A北支'),
          (75.5, 86.0, ABAND[0] - 0.3, ABAND[1] + 0.3, 'A带根')]
A.dyn = [(x0, x1, y0, y1, {94: 'A桥1', 102: 'A桥2', 110: 'A桥3'}.get(round((x0 + x1) / 2), n)) for x0, x1, y0, y1, n in A.dyn]
stitch(A, [(46.0, 40.0), (58.9, 38.0), (73.5, 38.5), (47.0, 61.6), (58.0, 61.6), (73.5, 61.6)])

# =====================================================================
# 片 B：→ AFE-30P FPC3（Bottom 面，yB(1)=55.3316 .. yB(30)=40.8316）
# =====================================================================
B = Piece('b')
place_aux(B)
TB = round(32.39 - TAIL_EXT, 4)
yB = lambda p: round(55.3316 - (p - 1) * 0.5, 4)  # noqa: E731
xcB, xeB = fingers(B, 'TAIL_B', 'FPC3', TB, 'F', yB)
tail_stiff(B, TB, TB + STIFF, TB_Y0, TB_Y1, 'B', '尾B补强（B面，金手指背面）')
B.dyn.append((round(34.94 - TAIL_EXT, 4), BEND_X, TB_Y0, TB_Y1, 'B尾折弯'))
B.gnd_runs = gnd_tail(B, 'FPC3', yB, xcB, xeB, X_TAIL_VIA, {30: (40.85, 40.50)})
B_TAIL_VIAS = [(p, R_VIA) for n, p in B.vias if n == 'AGND']

yb = yB(29)   # 41.3316
xbv = 41.80
B.tr('BIAS_DRV12', 'F', [(xcB, yb), (xbv - 0.15, yb), (round(xbv, 6), round(yb + 0.15, 6))], 'bias')
B.via('BIAS_DRV12', (xbv, round(yb + 0.15, 6)))
_tx, _ty = cap_pad('R34', 'tail')
XBV2 = 43.0
B.tr('BIAS_DRV12', 'B', [(xbv, round(yb + 0.15, 6)), (XBV2 - 0.4, round(yb + 0.15, 6)), (XBV2, round(yb + 0.55, 6)),
                         (XBV2, _ty - 0.4), (XBV2 + 0.4, _ty), (_tx, _ty)], 'bias')
_ex, _ey = cap_pad('R34', 'elec')
_cx, _cy = contact('EB2')
XEV2 = 47.5
assert math.dist((XEV2, _ey), (_cx, _cy)) >= EB_PAD_D / 2 + VIA[0] / 2 + 0.15
B.tr('BIAS_DRV12_E', 'B', [(_ex, _ey), (XEV2, _ey)], 'bias')
B.via('BIAS_DRV12_E', (XEV2, _ey))
B.tr('BIAS_DRV12_E', 'F', [(XEV2, _ey), (_cx - EB_PAD_D / 2 + E_IN, _ey)], 'bias')

B_HEAD = [round(YC - R_BIG - 0.82 * i, 4) for i in (3, 2, 1, 0)] + [round(YC + R_BIG + 0.82 * i, 4) for i in range(4)]
B_HEAD_TOP, B_HEAD_BOT = round(B_HEAD[0] - PM, 4), round(B_HEAD[-1] + PM, 4)
order = list(range(16, 8, -1))
fy = [conv(B, 'FPC3', yB, xcB, xeB, ch) for ch in order]
B.advance(order, fy, B_HEAD, BEND_X + 0.1, [(contact('EB2'), R_BIG), ((XEV2, _ey), R_VIA)] + B_TAIL_VIAS)
B.lanes['B头部'] = B_HEAD
_fork9 = round(B_BAND[1] - PM, 4)
LBo = lanes((B_BAND[0], _fork9 - FORK_GAP + PM), 7) + [_fork9]
XC_B = 54.6
B.advance(order, B_HEAD, LBo, XC_B, [(contact('EB2'), R_BIG)])
B.lanes['B并行段'] = LBo
x9 = round(next(p[0] for p in B.C[9] if p[0] >= XC_B) + 0.22, 3)
x16 = round(next(p[0] for p in B.C[16] if p[0] >= XC_B) + 0.22, 3)

YE_B = {}
rem, cur = list(order), LBo
for ch in range(9, 17):
    cx = B_ISL[ch]
    n = len(rem)
    ye = YC if n == 1 else round(max(YC, cur[-2] + FORK_GAP), 4)
    YE_B[ch] = ye
    tn, tp = contact_block(B, ch, cx)
    ends = B.advance(rem, cur, cur[:-1] + [ye], cx - 4.6, island_obst(cx))
    xv = round(cx - 0.325, 6)
    assert ends[-1] <= xv - 0.4, (ch, ends[-1], xv)
    B.C[ch] += [(xv - 0.2, ye)]
    ne, pe = peel_entry(xv, False, ye)
    pair_traces(B, ch, 'F', B.C[ch], -1, ne, pe, 'band')
    B.via(f'CH{ch}_N', (xv, ye - 0.35)); B.via(f'CH{ch}_P', (xv + 0.65, ye + 0.35))
    leg(B, f'CH{ch}_N', (xv, ye - 0.35), tn, up=True)
    leg(B, f'CH{ch}_P', (xv + 0.65, ye + 0.35), tp, up=False)
    rem, cur = rem[:-1], cur[:-1]
    if rem:
        B.lanes[f'B岛CH{ch}后'] = cur

# --- B 外形（弯折线 x=40.0 起从尾宽 [40.3316, 55.8316] 平滑扩开，避开 A 背面 R2/R1/R33） ---
B_HEAD_POLY = [
    (40.0, TB_Y0),
    (40.55, round(TB_Y0 - 0.55, 4)),
    (43.2, round(TB_Y0 - 0.55, 4)),
    (round(43.2 + B_HEAD_TOP - (TB_Y0 - 0.55), 4), B_HEAD_TOP),
    (x16, B_HEAD_TOP),
    (round(x16 + B_BAND[0] - B_HEAD_TOP, 4), B_BAND[0]),
    (75.0, B_BAND[0]),
    (75.0, B_BAND[1]),
    (round(x9 + B_HEAD_BOT - B_BAND[1], 4), B_BAND[1]),
    (x9, B_HEAD_BOT),
    (round(40.0 + B_HEAD_BOT - TB_Y1, 4), B_HEAD_BOT),
    (40.0, TB_Y1),
]
B.shapes += [rect(TB, 40.1, TB_Y0, TB_Y1), B_HEAD_POLY, rect(74.9, B_ISL[9] - ISL_HW + 0.1, *B_BAND)]
islands_outline(B, B_ISL.values())
yb_ = (B_BAND[0] - 0.3, B_BAND[1] + 0.3)
B.dyn += [(75.5, 86.0, *yb_, 'B带根')] + [(x, x + 0.9, *yb_, f'B过A桥{i + 1}') for i, x in enumerate((93.55, 101.55, 109.55, 117.55))]


def seg_len(pc, net):
    return sum(plen(t[2]) for t in pc.traces if t[0] == net)


def tune(pc):
    rows = []
    chs = sorted({int(t[0][2:].split('_')[0]) for t in pc.traces if t[0].startswith('CH')})
    for ch in chs:
        row = dict(ch=ch, bumps=[], method='腿上凸起' if f'CH{ch}_N' in pc.legs else f'北岛分叉高度 ys={north_ys.get(ch)}')
        n, p = f'CH{ch}_N', f'CH{ch}_P'
        d = seg_len(pc, n) - seg_len(pc, p)
        if abs(d) > TOL:
            assert n in pc.legs, (pc.name, ch, d)
            short = p if d > 0 else n
            idx = pc.legs[short]
            pts = pc.traces[idx][2]
            e = abs(d) / (2 * (math.sqrt(2) - 1))
            if e > 1.0 and ch not in (1, 2):
                new, h = hairpin(pts, abs(d))
                pc.traces[idx][2] = clean(new)
                row['hairpin'] = dict(net=short, extra_mm=round(abs(d), 4), height=h, top_y=round(new[2][1], 4))
            else:
                other = pc.traces[pc.legs[n if short == p else p]][2]
                i = max(range(len(pts) - 1), key=lambda j: math.dist(pts[j], pts[j + 1]))
                new, side = bump(pts, i, e, other[0])
                pc.traces[idx][2] = clean(new)
                row['bumps'].append(dict(net=short, at=[round((pts[i][0] + pts[i + 1][0]) / 2, 3), round((pts[i][1] + pts[i + 1][1]) / 2, 3)],
                                         height=round(e, 3), normal=side))
        for suffix, key in (('', 'tail'), ('_E', 'elec')):
            n, p = f'CH{ch}_N{suffix}', f'CH{ch}_P{suffix}'
            row[f'{key}_N_mm'] = round(seg_len(pc, n), 4)
            row[f'{key}_P_mm'] = round(seg_len(pc, p), 4)
            row[f'{key}_diff_mm'] = round(seg_len(pc, p) - seg_len(pc, n), 4)
            row[f'{key}_diff_mil'] = round((seg_len(pc, p) - seg_len(pc, n)) / 0.0254, 2)
        rows.append(row)
    return rows


match = {'a': tune(A), 'b': tune(B)}

LAYER = {'F': 'F.Cu', 'B': 'B.Cu'}
STACKUP = '''(stackup
 (layer "F.SilkS" (type "Top Silk Screen"))
 (layer "F.Paste" (type "Top Solder Paste"))
 (layer "F.Mask" (type "Top Solder Mask") (color "Yellow") (thickness 0.0275) (material "PI coverlay") (epsilon_r 3.4) (loss_tangent 0.004))
 (layer "F.Cu" (type "copper") (thickness 0.012))
 (layer "dielectric 1" (type "core") (thickness 0.025) (material "Polyimide") (epsilon_r 3.4) (loss_tangent 0.004))
 (layer "In1.Cu" (type "copper") (thickness 0.012))
 (layer "dielectric 2" (type "prepreg") (thickness 0.025) (material "PI+adhesive") (epsilon_r 3.4) (loss_tangent 0.004))
 (layer "In2.Cu" (type "copper") (thickness 0.012))
 (layer "dielectric 3" (type "core") (thickness 0.025) (material "Polyimide") (epsilon_r 3.4) (loss_tangent 0.004))
 (layer "B.Cu" (type "copper") (thickness 0.012))
 (layer "B.Mask" (type "Bottom Solder Mask") (color "Yellow") (thickness 0.0275) (material "PI coverlay") (epsilon_r 3.4) (loss_tangent 0.004))
 (layer "B.Paste" (type "Bottom Solder Paste"))
 (layer "B.SilkS" (type "Bottom Silk Screen"))
 (copper_finish "ENIG") (dielectric_constraints no))'''
HEADER = '''(kicad_pcb (version 20240108) (generator "pcbnew") (generator_version "8.0")
(general (thickness 0.203))
(paper "A3")
(layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
 (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
 (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments")
 (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user) (50 "User.1" user "补强-F") (51 "User.2" user "补强-B"))
(setup %s (pad_to_mask_clearance 0) (allow_soldermask_bridges_in_footprints no))
''' % STACKUP


def f6(v):
    return f'{v:.6f}'.rstrip('0').rstrip('.')


def polyset(pts):
    s = k.SHAPE_POLY_SET(); s.NewOutline()
    for x, y in pts:
        s.Append(round(x * 1e6), round(y * 1e6))
    return s


def outlines(s):
    res = []
    for i in range(s.OutlineCount()):
        o = s.Outline(i)
        res.append([(o.CPoint(j).x / 1e6, o.CPoint(j).y / 1e6) for j in range(o.PointCount())])
    return res


def board_outline(pc):
    s = polyset(pc.shapes[0])
    for sh in pc.shapes[1:]:
        s.BooleanAdd(polyset(sh))
    for c in pc.cut:
        s.BooleanSubtract(polyset(c))
    s.Simplify()
    ol = outlines(s)
    assert len(ol) == 1, f'{pc.name} 外形不是单一轮廓：{len(ol)}'
    for i in range(s.OutlineCount()):
        assert s.HoleCount(i) == 0
    return s, ol[0]


def stiff_poly(st):
    if 'circle' in st:
        return polyset(circ(*st['circle'], 96))
    return polyset(rect(*st['rect']))


def poly_rings(s):
    rings = []
    for i in range(s.OutlineCount()):
        for ch in [s.Outline(i)] + [s.Hole(i, j) for j in range(s.HoleCount(i))]:
            rings.append([(ch.CPoint(j).x / 1e6, ch.CPoint(j).y / 1e6) for j in range(ch.PointCount())])
    return rings


def mesh_holes(pc, ol):
    a = MESH['pitch'] / math.sqrt(2)
    d = MESH['hole'] / math.sqrt(2)
    ok = polyset(ol)
    for x, y, r in pc.holes:
        ok.BooleanSubtract(polyset(circ(x, y, r, 64)))
    ok.Inflate(-round(0.305e6), k.CORNER_STRATEGY_ROUND_ALL_CORNERS, 2000)
    avoid = [(p, VIA[0] / 2) for _, p in pc.vias] + [((q['x'], q['y']), q['w'] / 2) for f in pc.fps if f['kind'] == 'part' for q in f['pads'] if q['drill']]
    holes, taken = [], []
    for x0, x1, y0, y1, _ in pc.dyn:
        x0, x1 = x0 - MESH['ext'], x1 + MESH['ext']
        best = []
        for ox in range(6):
            for oy in range(6):
                fx, fy = ox * a / 3, oy * a / 3
                cand = []
                for m in range(math.floor((x0 - fx) / a) - 1, math.ceil((x1 - fx) / a) + 2):
                    for n in range(math.floor((y0 - fy) / a) - 1, math.ceil((y1 - fy) / a) + 2):
                        if (m + n) % 2:
                            continue
                        cx, cy = fx + m * a, fy + n * a
                        if not (x0 + d <= cx <= x1 - d and y0 <= cy <= y1):
                            continue
                        if not ok.Contains(k.VECTOR2I(round(cx * 1e6), round(cy * 1e6))):
                            continue
                        if any(math.dist((cx, cy), p) < d + r + 0.15 for p, r in avoid):
                            continue
                        if any(abs(cx - tx) + abs(cy - ty) < 2 * d + MESH['pitch'] - MESH['hole'] - 1e-6 for tx, ty in taken):
                            continue
                        cand.append((cx, cy))
                if len(cand) > len(best):
                    best = cand
        taken += best
        holes += [[(cx + d, cy), (cx, cy + d), (cx - d, cy), (cx, cy - d)] for cx, cy in best]
    return holes


def emit(pc):
    nets = ['']
    for t in pc.traces:
        nets.append(t[0])
    for v in pc.vias:
        nets.append(v[0])
    for f in pc.fps:
        for pd in f['pads']:
            nets.append(pd['net'] if f['kind'] == 'part' else pd[1])
    order_ = ['']
    for n in nets:
        if n not in order_:
            order_.append(n)
    nid = {n: i for i, n in enumerate(order_)}
    out = [HEADER]
    out += [f'(net {i} "{n}")' for i, n in enumerate(order_)]
    for f in pc.fps:
        ref = f['ref']
        if f['kind'] == 'part':
            x, y = f['x'], f['y']
            pads = ''
            for q in f['pads']:
                at = f'(at {f6(q["x"] - x)} {f6(q["y"] - y)})'
                if q['circle'] and q['drill']:
                    pads += f'(pad "{q["num"]}" thru_hole circle {at} (size {q["w"]} {q["h"]}) (drill {q["drill"]}) (layers "*.Cu" "*.Mask") (remove_unused_layers no) (net {nid[q["net"]]} "{q["net"]}"))'
                elif q['circle']:
                    pads += f'(pad "{q["num"]}" smd circle {at} (size {q["w"]} {q["h"]}) (layers "F.Cu" "F.Paste" "F.Mask") (net {nid[q["net"]]} "{q["net"]}"))'
                else:
                    side = 'B' if f['layer'] == 'B.Cu' else 'F'
                    pads += f'(pad "{q["num"]}" smd rect {at} (size {q["w"]} {q["h"]}) (layers "{side}.Cu" "{side}.Paste" "{side}.Mask") (net {nid[q["net"]]} "{q["net"]}"))'
            if ref.startswith('E'):
                smd = not f['pads'][0]['drill']
                fpn, attr = ('CONTACT_SMD_D6.5', 'smd') if smd else ('CONTACT_D1.8', 'through_hole')
                val = ('贴肤焊盘（焊 Φ6×2.0 镀金铜片）' if f['pads'][0]['w'] > 6 else '贴肤焊盘（焊方形 3×3×2 镀金铜片）') if smd else \
                      ('REF 贴肤焊盘（焊方形 3×3×2，孔内灌锡对焊 B 片 EB2）' if ref == 'EB2A' else '贴肤触点')
                out.append(f'\t(footprint "{fpn}" (layer "F.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1)))) (property "Value" "{val}" (at 0 1.4 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (attr {attr}) {pads})')
            else:
                fpn = 'R0603' if f['value'] == '200k' else 'R0402'
                sd = f['layer'][0]
                mir = ' (justify mirror)' if sd == 'B' else ''
                out.append(f'\t(footprint "{fpn}" (layer "{sd}.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "{sd}.Fab") (effects (font (size 0.4 0.4) (thickness 0.06)){mir})) (property "Value" "{f["value"]}" (at 0 0.9 0) (layer "{sd}.Fab") (hide yes) (effects (font (size 0.4 0.4) (thickness 0.06)){mir})) (attr smd) {pads})')
        else:
            lay = LAYER[f['face']]; m = lay.replace('Cu', 'Mask')
            pads = ''.join(f'(pad "{num}" smd rect (at {f6(x)} {f6(y)}) (size {FINGER["l"]} {FINGER["w"]}) (layers "{lay}" "{m}") (net {nid[net]} "{net}"))' for num, net, x, y in f['pads'])
            fab = 'F.Fab' if f['face'] == 'F' else 'B.Fab'
            gx0, gx1, gy0, gy1 = f['gang']
            gang = f'(fp_rect (start {f6(gx0)} {f6(gy0)}) (end {f6(gx1)} {f6(gy1)}) (stroke (width 0) (type solid)) (fill solid) (layer "{m}"))'
            out.append(f'\t(footprint "FPC30_P0.5_TAIL" (layer "{lay}") (at 0 0) (property "Reference" "{ref}" (at 0 0 0) (layer "{fab}") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (property "Value" "AFE-30P {"FPC1" if ref == "TAIL_A" else "FPC3"}" (at 0 0 0) (layer "{fab}") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (attr smd allow_soldermask_bridges) {gang} {pads})')
    for net, layer, pts, _ in pc.traces:
        for a, b in zip(pts, pts[1:]):
            out.append(f'(segment (start {f6(a[0])} {f6(a[1])}) (end {f6(b[0])} {f6(b[1])}) (width {W}) (layer "{LAYER[layer]}") (net {nid[net]}))')
    for net, (x, y) in pc.vias:
        out.append(f'(via (at {f6(x)} {f6(y)}) (size {VIA[0]}) (drill {VIA[1]}) (layers "F.Cu" "B.Cu") (net {nid[net]}))')
    s, ol = board_outline(pc)
    out.append('(gr_poly (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in ol) + ') (stroke (width 0.05) (type solid)) (fill none) (layer "Edge.Cuts"))')
    for x, y, r in pc.holes:
        out.append(f'(gr_circle (center {f6(x)} {f6(y)}) (end {f6(x + r)} {f6(y)}) (stroke (width 0.05) (type solid)) (fill none) (layer "Edge.Cuts"))')
    for st in pc.stiff:
        lay = 'User.1' if st['side'] == 'F' else 'User.2'
        for o in poly_rings(stiff_poly(st)):
            out.append('(gr_poly (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in o) + f') (stroke (width 0.05) (type solid)) (fill none) (layer "{lay}"))')
        if 'rect' in st:
            x0, x1, y0, y1 = st['rect']
            out.append(f'(gr_text "{st["name"]} PI {st["thickness"]}（含胶，假设）" (at {f6((x0 + x1) / 2)} {f6(y0 - 0.5)} 0) (layer "Cmts.User") (effects (font (size 0.4 0.4) (thickness 0.06))))')
    out.append(f'(gr_text "触点背面 PI 补强 Φ{STIFF_D} 厚 {STIFF_T_ISL}（含胶，假设），每触点一块" (at {f6(min(x for x, _ in ol) + 6)} {f6(ISL_Y1 + 1.0)} 0) (layer "Cmts.User") (effects (font (size 0.5 0.5) (thickness 0.07)) (justify left)))')
    zone_common = '(hatch edge 0.5) (connect_pads yes (clearance 0.2)) (min_thickness 0.15) (filled_areas_thickness no)'
    for layer in ('In1.Cu', 'In2.Cu'):
        out.append(f'(zone (net {nid["AGND"]}) (net_name "AGND") (layer "{layer}") (name "GND") {zone_common} '
                   f'(fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3) (island_removal_mode 0)) (polygon (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in ol) + ')))')
    for i, o in enumerate(mesh_holes(pc, ol)):
        out.append(f'(zone (net 0) (net_name "") (layers "In1.Cu" "In2.Cu") (name "网格孔{i}") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no) '
                   '(keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) (fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) '
                   '(polygon (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in o) + ')))')
    for x0, x1, y0, y1, name in pc.dyn:
        out.append(f'(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (name "动态区禁孔-{name}") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no) '
                   '(keepout (tracks allowed) (vias not_allowed) (pads not_allowed) (copperpour allowed) (footprints allowed)) (fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) '
                   '(polygon (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in rect(x0, x1, y0, y1)) + ')))')
    f = next(f for f in pc.fps if f['kind'] == 'finger')
    p1 = next(p for p in f['pads'] if p[0] == '1')
    txt = f'{"A→AFE-30P FPC1" if pc.name == "a" else "B→AFE-30P FPC3"} pin1 金手指在{f["face"]}面'
    out.append(f'(gr_text "{txt}" (at {f6(p1[2] - 1.2)} {f6(p1[3] + (-1.2 if pc.name == "a" else 1.2))} 0) (layer "Dwgs.User") (effects (font (size 0.6 0.6) (thickness 0.08)) (justify left)))')
    out.append(')')
    return '\n'.join(out), ol


DRU = '''(version 1)
(rule "30P 线宽" (constraint track_width (min 0.15mm)))
(rule "30P 铜间距" (constraint clearance (min 0.15mm)))
(rule "30P 铜到板边 12mil" (constraint edge_clearance (min 0.305mm)))
(rule "30P 金手指到尾尖" (condition "A.Type == 'Pad' && A.memberOfFootprint('TAIL_*')") (constraint edge_clearance (min 0.15mm)))
(rule "30P 过孔外径" (condition "A.Type == 'Via'") (constraint via_diameter (min 0.5mm)))
# 不同网的两条走线（同一差分对 CHn_P/CHn_N 除外）中心距 ≥ 0.47 mm：线宽 0.15 时净距 ≥ 0.32
(rule "30P 不同网走线中心距0.47" (condition "A.Type == 'Track' && B.Type == 'Track' && A.Net != B.Net && !A.isCoupledDiffPair()")
 (constraint clearance (min 0.32mm)))
'''


def project():
    p = json.loads((HERE / 'strap-30p-a.kicad_pro').read_text(encoding='utf-8'))
    r = p['board']['design_settings']['rules']
    r.update(min_clearance=0.15, min_copper_edge_clearance=0.305, min_track_width=0.15, min_via_diameter=0.5,
             min_through_hole_diameter=0.25, min_via_annular_width=0.1, min_hole_clearance=0.2, min_hole_to_hole=0.25)
    p['board']['design_settings']['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': VIA[0], 'drill': VIA[1]}]
    for c in p['net_settings']['classes']:
        c.update(clearance=0.15, track_width=0.15, via_diameter=VIA[0], via_drill=VIA[1])
    return p


geo = {
    'afe30p_source': dict(file=str(AFE_EPRO.relative_to(ROOT)), sha256=AFE_SHA),
    'tpu_layer_source': dict(file=str(TPU.relative_to(ROOT)), sha256=hashlib.sha256(TPU.read_bytes()).hexdigest(), consts=TC),
    'd2': dict(pad_d=PAD_D, stiffener_d=STIFF_D, stiffener_t=STIFF_T_ISL, pair_y=PN_Y, island_y=[ISL_Y0, ISL_Y1], island_half_width=ISL_HW,
               slit=dict(width=round(8.0 - 2 * ISL_HW, 3), from_bottom_to_y=round(SLIT_C - (4.0 - ISL_HW), 3)),
               north_islands=N_ISL, south_islands=S_ISL, resistor_offset=RES, resistor_face='F', leg_via_offset=LV, b_split_y=YE_B),
    'bands': dict(ABAND=ABAND, B_BAND=B_BAND, NORTH=NORTH, B_LANES=LBo),
    'north_split_y': north_ys,
}
geo['capsule_pads'] = dict(
    disc_ch=dict(d=TC['DISC_D'], t=2.0), disc_eb=EB_DISC, mask_opening='= 焊盘',
    eb2_joint=dict(a_ref='EB2A', b_ref='EB2', board=list(contact('EB2')), pad_d=EB_PAD_D, drill=EB2_JOINT_DRILL),
    pads=[dict(ref='EB2' if f['ref'] == 'EB2A' else f['ref'], piece=f['piece'], net=f['pads'][0]['net'], d=f['pads'][0]['w'],
               disc='方形 3×3×2' if f['ref'].startswith('EB') else 'Φ6×2.0', layer='F.Cu', smd=not f['pads'][0]['drill'],
               board=[f['x'], f['y']], box=[round(f['y'] - 50.0, 4), round(58.0 - f['x'], 4)])
          for f in CAP if f['ref'].startswith('E') and not (f['ref'] == 'EB2' and f['piece'] == 'b')],
    resistors=[dict(ref=f['ref'], piece=f['piece'], value=f['value'], layer='B.Cu', board=[f['x'], f['y']])
               for f in CAP if f['ref'].startswith('R')],
)
R_IN = 0.5
Y_ENTRY = round(58 - BEND_X, 4)
YV_B = round(Y_ENTRY + R_IN + T_FPC / 2, 4)
YV_A = round(YV_B + T_FPC, 4)
geo['tray_tail_slot'] = dict(
    note='双 30P 尾（片 A 中心盒 X = -0.3944、片 B 中心盒 X = -1.9184，横向错位 1.524 mm，尾宽各 15.50 mm）穿底壳北侧长槽进入壳内回折插接 FPC1/FPC3。',
    box=dict(x0=round(TB_Y0 - 50.0 - 0.25, 3), x1=round(TA_Y1 - 50.0 + 0.25, 3), y0=round(Y_ENTRY - 0.05, 3), y1=round(YV_A + T_FPC / 2 + 0.05, 3)),
    z_through=[Z_SHELL_OUT, Z_FLOOR_IN], north_pocket_y_max_needed=round(YV_A + T_FPC / 2 + 0.05, 3),
    tail_vertical_centerline_y=dict(a=YV_A, b=YV_B), bend_inner_r_min=R_IN,
    tail_extension_mm=TAIL_EXT, dz_mm=DZ_TAIL, board_x_of_bend_start=round(58 - Y_ENTRY, 3),
)


def box_poly(ring):
    return [[round(y - 50.0, 4), round(58.0 - x, 4)] for x, y in ring]


_sa, _ = board_outline(A); _sb, _ = board_outline(B)
_st = k.SHAPE_POLY_SET(_sa); _st.BooleanIntersection(_sb); _st.BooleanIntersection(polyset(rect(BEND_X, 76.8, 0, 100))); _st.Simplify()
geo['capsule_stack'] = dict(polygons_box=[box_poly(o) for o in outlines(_st)], area_mm2=round(_st.Area() / 1e12, 2))
_BODY = {'200k': (1.6, 0.8), '100k': (1.0, 0.5)}
_pk = []
for f in CAP:
    if not f['ref'].startswith('R'):
        continue
    xs = [q['x'] - q['w'] / 2 for q in f['pads']] + [q['x'] + q['w'] / 2 for q in f['pads']]
    ys = [q['y'] - q['h'] / 2 for q in f['pads']] + [q['y'] + q['h'] / 2 for q in f['pads']]
    bl, bw = _BODY[f['value']]
    x0, x1 = min(xs + [f['x'] - bl / 2]) - 0.3, max(xs + [f['x'] + bl / 2]) + 0.3
    y0, y1 = min(ys + [f['y'] - bw / 2]) - 0.3, max(ys + [f['y'] + bw / 2]) + 0.3
    h = 0.45 if f['value'] == '200k' else 0.35
    base = Z_SHELL_OUT - T_FPC if f['piece'] == 'a' else Z_SHELL_OUT
    _pk.append(dict(ref=f['ref'], piece=f['piece'], value=f['value'], board=[round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
                    box=dict(x0=round(y0 - 50, 3), x1=round(y1 - 50, 3), y0=round(58 - x1, 3), y1=round(58 - x0, 3)),
                    part_top_z=round(base + h, 3), pocket_z=[Z_SHELL_OUT, round(base + h + 0.05, 3)]))
geo['capsule_res_pockets'] = dict(rects=_pk)

for pc in (A, B):
    txt, ol = emit(pc)
    path = HERE / f'strap-30p-{pc.name}.kicad_pcb'
    path.write_text(txt, encoding='utf-8')
    b = k.LoadBoard(str(path))
    k.ZONE_FILLER(b).Fill(b.Zones())
    k.SaveBoard(str(path), b)
    proj = project()
    proj['meta']['filename'] = f'strap-30p-{pc.name}.kicad_pro'
    (HERE / f'strap-30p-{pc.name}.kicad_pro').write_text(json.dumps(proj, indent=2, ensure_ascii=False), encoding='utf-8')
    (HERE / f'strap-30p-{pc.name}.kicad_dru').write_text(DRU, encoding='utf-8')
    fing = next(f for f in pc.fps if f['kind'] == 'finger')
    geo[pc.name] = dict(outline=[[round(x, 4), round(y, 4)] for x, y in ol], holes=pc.holes,
                        dynamic_zones=[dict(name=n, x=[x0, x1], y=[y0, y1]) for x0, x1, y0, y1, n in pc.dyn],
                        stiffeners=[dict(name=st['name'], side=st['side'], thickness_mm=st['thickness'], material='PI+胶（假设）',
                                         **({'circle': st['circle']} if 'circle' in st else {'rect': st['rect']})) for st in pc.stiff],
                        gang_opening=getattr(pc, 'gang', None), mesh=MESH, lanes=pc.lanes,
                        tail=dict(tip_x=TA if pc.name == 'a' else TB, width=TAIL_W, finger_face=fing['face'],
                                  pin1_y=next(p[3] for p in fing['pads'] if p[0] == '1'),
                                  pin30_y=next(p[3] for p in fing['pads'] if p[0] == '30'),
                                  finger=FINGER, stiffener_len=STIFF),
                        traces=[dict(net=n, layer=LAYER[l], pts=[[round(x, 5), round(y, 5)] for x, y in p], tag=t) for n, l, p, t in pc.traces],
                        vias=[dict(net=n, at=list(p)) for n, p in pc.vias])
(HERE / 'geometry.json').write_text(json.dumps(geo, ensure_ascii=False, indent=1), encoding='utf-8')
(HERE / 'match.json').write_text(json.dumps(match, ensure_ascii=False, indent=1), encoding='utf-8')
for prl in HERE.glob('*.kicad_prl'):
    prl.unlink()
worst = max(abs(r[k_]) for side in match.values() for r in side for k_ in ('tail_diff_mm', 'elec_diff_mm'))
print(f'strap-fpc-30p 已生成：A {len(A.traces)} 线 {len(A.vias)} 孔；B {len(B.traces)} 线 {len(B.vias)} 孔；分段 P/N 最大差 {worst:.4f} mm（{worst / 0.0254:.2f} mil）；北岛分叉 {north_ys}')
