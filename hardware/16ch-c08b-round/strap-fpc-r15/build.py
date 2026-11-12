"""R15（Meta 专利参考对内 18 mm 版）：D17 采集板（V4_FPC1 / V4_FPC3 两颗 Hirose FH34SRJ-34S，34P 0.5）用两片四层表带软板。

KiCad 自带 python3 运行：python3 build.py
- 脚序直接读 D17 KiCad 源板（沿 15k 阵列追到 ADS1298 输入），写 d17-interface.csv。
- 触点、串阻（含两颗 200k）读 R12 板：盒底 2 对（CH1/CH2，对内 16.0 mm，y=42/58）+ 2 辅助（EB1/EB2，y=50）及串阻 R1–R4/R33/R34 原位不动（100% 兼容 R12 8001 全透明外壳）；
  盒外 14 岛（北 2 岛 CH3–CH4 + 南 12 岛 CH5–CH16）触点与串阻向南北各外扩 1.0 mm，对内中心距 16.0 → 18.0 mm（y=41.0/59.0，Ø4.0 端子内侧净距 14.0 mm > Meta sEMG-RD 13.5 mm），
  盒外岛 PCB 宽收窄至 21.2 mm（y=39.4–60.6）、补强宽 20.8 mm（y=39.6–60.4，适配实测 22.04 mm 表带，两侧各留 0.42 mm 余量；同时也兼容 25 mm 表带），腕周节距保持 8.0 mm（16 路跨度 166.8 mm，适配 ≥162 mm 腕围）。
- 尾尖、尾宽、金手指、补强长度同 R7/R12/R14。
- 层：F.Cu 信号 / In1.Cu GND / In2.Cu GND / B.Cu 信号。
- 线宽 0.15；对内中心距 0.30；不同网两线中心距 ≥ 0.47；铜到板边 ≥ 0.305。
- 每一段并行带都比 R12 宽，带内各对按「等分格」排开（格宽 = 带宽 / 对数，对在格中心）；
  格太窄、外侧铜到边会小于 0.315 时，外侧取 0.315，其余等距。每过一个岛剩下的对在岛内（静态区）重新等分。
- 走线全部 0/45/90°；换道用 45° 斜线，相邻两对中心线间距在换道过程中也 ≥ 0.80（规划器逐对推迟起点）。
- P/N 每段（尾→串阻、串阻→触点）等长：南岛/盒底用 B 面腿上的 45° 凸起，北岛用分叉点上下平移（解析求解，不加凸起）。
输出 strap-a/b.kicad_pcb（含填好的 GND 平面）、pro/dru、geometry.json、match.json、d17-interface.csv。
"""
import csv
import hashlib
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

import pcbnew as k

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R12 = HERE
mm = k.ToMM
W = 0.15             # 线宽
HP = 0.15            # 对内半间距（中心距 0.30）
VIA = (0.5, 0.25)    # 过孔外径 / 孔径
TOL = 0.002          # 调长目标（mm），远小于 10 mil = 0.254
YC = 50.0            # 南岛、盒底分叉线
EXT_PAIR_DY = 1.0    # R15：盒外 14 岛（CH3–CH16）触点与串阻相对 R12/R14 各向南北外扩 1.0 mm，对内中心距 16.0 → 18.0 mm（y=41.0/59.0），盒底 CH1/CH2/EB1/EB2 保持 16.0 mm 不动
ISL_Y0 = 39.4        # 盒外电极岛上沿 39.4 mm（总岛宽 21.2 mm < 实测表带 22.04 mm，单边留 0.42 mm）
ISL_Y1 = 60.6        # 盒外电极岛下沿 60.6 mm
STIFF_Y0 = 39.6      # 盒外岛补强上沿 39.6 mm（补强宽 20.8 mm，完全盖住 Ø1.8 触点焊盘 40.1..59.9）
STIFF_Y1 = 60.4      # 盒外岛补强下沿 60.4 mm
EDGE_M = 0.315       # 排线道时外侧铜到板边（规则 0.305，多留 0.01）
PM = EDGE_M + HP + W / 2     # 对中心到板边 0.54
PREQ = 0.82          # 规划换道时相邻两对中心线最小距离（0.30+0.47=0.77，另加 45° 斜接余量）
R_PAD = 0.9 + 0.15 + W / 2 + HP + 0.02     # 规划时对中心线离 Ø1.8 触点中心的最小距离
R_VIA = VIA[0] / 2 + 0.15 + W / 2 + HP + 0.02
MESH = dict(pitch=0.60, hole=0.42, ext=0.55)  # 动态区平面：45° 菱形孔，孔边 0.42、节距 0.60（铜约一半）
STIFF_T_TAIL = 0.10          # 尾端补强：按 FH34SRJ 插接厚 0.30±0.03 减四层板约 0.20 反算（含胶，假设）
STIFF_T_ISL = 0.15           # 岛补强 PI 含胶（同 R11 假设）
FINGER = dict(w=0.30, l=1.5, setback=0.2, pitch=0.5, n=34)   # 同 R7/R12：金手指 0.3×1.5，离尖端 0.2
TAIL_W = 17.5                # (34+1)×0.5，同 R12
STIFF = 2.5                  # 尾端补强长度（自尖端起），同 R7/R12

# 各段带的 y 范围（R12 对应段见 README 宽度表）
B_BAND = (44.88, 52.8)       # B 与 A 并行段（R12 44.88–50.225，5.345）；上沿同 R12，离 A 岛 N 串阻焊盘（44.58）0.30
A_BAND = (53.3, 59.0)        # A 出盒带、A 桥（R12 50.725–56.05，5.325）；与 B 带缝 0.5
B_BR = (43.32, 49.5)         # B 自己的桥（宽 6.18 > R12 5.345；上沿 43.32 使最上一对铜边 43.635 避开外扩后 N 串阻焊盘下沿 43.62，B 片正背面叠焊盘归零）
NORTH = (38.95, 40.85)       # A 北支（R12 39.25–40.85，1.6）
NECK = (44.88, 50.725)       # A 北颈（同 R12）
A_HEAD = [52.55, 53.9, 55.25, 56.6]          # A 的 CH5–8 在盒底里的道（CH2 51.6 之下、盒底 P 触点 58 之上）
A_ISL_MAX = 55.8             # A 岛内道的下限（避开外扩后 y=57.2 的 P 串阻 R9/R11/R13 焊盘上沿 56.38，正背面也不叠焊盘）
# 两片互相给对方辅助触点（Ø1.8 焊盘）开的让位孔：R12 为 Ø2.0（单边只剩 0.10）；R14 放大到 Ø2.2，单边 0.20，触点位置不动
RELIEF_R = 1.1
HOLE_KEEP = RELIEF_R + 0.305 + W / 2 + HP + 0.02     # 对中心线离让位孔圆心的最小距离（外侧铜到孔边 ≥0.325）
# B 头部（盒内，静态区）：上沿离 A 盒底 N 串阻 R2/R4 焊盘（下沿 44.38）0.30；CH16–12 五对在 A 的 EB1 让位孔上方等距，CH11–9 在下方
B_HEAD_TOP = 44.68
_up = [B_HEAD_TOP + PM, YC - HOLE_KEEP]
B_HEAD = [round(_up[0] + (_up[1] - _up[0]) * i / 4, 4) for i in range(5)] + [round(YC + HOLE_KEEP + 0.8 * i, 4) for i in range(3)]
B_HEAD_BOT = round(B_HEAD[-1] + PM, 4)
# 尾部 AGND 过孔：在折弯动态区右界 + 网格外扩 0.55 + 孔半径 + 0.1 之外
TAIL_VIA_DX = MESH['ext'] + VIA[0] / 2 + 0.1

# ---------- 几何工具 ----------


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    return dx / L, dy / L


def offset(pts, d):
    """折线等距偏移（尖角斜接）。法向 n=(-uy, ux)：向 +x 走时 +d 在 +y 一侧。"""
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
    """去重、合并共线点。"""
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


def bump(pts, i, e, away, end_margin=0.0):
    """在第 i 段中部插入 45° 梯形凸起，凸出 e，凸向远离点 away 的一侧。增长 0.8284·e。"""
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


# ---------- 带内排道与换道规划 ----------


def lanes(band, n):
    """n 对在带 band=(y0,y1) 里的中心 y：等分格；格太窄时外侧对中心离边 PM，其余等距。"""
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
    assert p >= 0.77, (band, n, p)
    return [round(y0 + PM + p * i, 4) for i in range(n)]


def plan(Y, T, x0, obst=(), preq=PREQ, step=0.01):
    """一组对（自上而下）从道 Y 换到道 T（同序），x0 之前都在 Y 上水平走。
    每对：水平 → 45° 斜线 → 水平。上移的对自上而下、下移的自下而上逐个定起点 xs：
    取 ≥x0 的最小 xs，使本对中心线与已定各对中心线距离 ≥ preq、离障碍圆心 ≥ 半径。返回各对 xs。
    起止道本身相邻间距小于 preq 时（直线段，没有斜接拐角），以起止道的最小间距为准（不低于 0.78）。"""
    n = len(Y)
    gaps = [b - a for a, b in zip(Y, Y[1:])] + [b - a for a, b in zip(T, T[1:])]
    preq = min([preq] + gaps) - 1e-6
    assert preq >= 0.78, ('道太挤', Y, T)
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
                if ptseg(c, *s) < r - 1e-9:
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


# ---------- 针脚真源：直接读 D17 采集板 KiCad 源，沿 15k 阵列追到 ADS1298 输入 ----------
D17_PCB = HERE.parent / 'afe-d20/afe-d20-silk.kicad_pcb'
CONN = {'FPC1': 'V4_FPC1', 'FPC3': 'V4_FPC3'}
AUX = {'V4_BIAS_DRV1': 'BIAS_DRV1', 'V4_RLD_OUT2': 'BIAS_DRV12', 'V4_WCT': 'WCT', 'V4_WCT2': 'WCT2', 'AGND': 'AGND'}


def load_copy(src):
    """拷到临时目录再读，免得 pcbnew 在源目录写 .kicad_prl。"""
    tmp = Path(tempfile.mkdtemp(prefix='r14-'))
    shutil.copy(src, tmp / 'x.kicad_pcb')
    b = k.LoadBoard(str(tmp / 'x.kicad_pcb'))
    shutil.rmtree(tmp)
    return b


def d17_interface():
    b = load_copy(D17_PCB)
    pins, bynet = {}, {}
    for f in b.GetFootprints():
        for p in f.Pads():
            pins.setdefault(f.GetReference(), {})[p.GetNumber()] = p.GetNetname()
            bynet.setdefault(p.GetNetname(), []).append((f.GetReference(), p.GetNumber()))
    opp = {'1': '8', '8': '1', '2': '7', '7': '2', '3': '6', '6': '3', '4': '5', '5': '4'}
    arrays = {f'V4_U{i}' for i in range(3, 11)}
    rows = []
    for con, ref in CONN.items():
        assert len(pins[ref]) >= 34
        for n in range(1, 35):
            net = pins[ref][str(n)]
            row = dict(connector=con, d17_ref=ref, pin=n, d17_net=net, array='', array_in='', array_out='', adc='', adc_pin='', adc_net='')
            if net.startswith('V4_$'):
                (ar, ap), = [x for x in bynet[net] if x[0] in arrays]
                out = pins[ar][opp[ap]]
                (adc, adp), = [x for x in bynet[out] if x[0] in ('V4_U1', 'V4_U2')]
                m = re.fullmatch(r'V4_IN(\d)([PN])(2?)', out)
                row.update(array=ar, array_in=ap, array_out=opp[ap], adc=adc, adc_pin=adp, adc_net=out,
                           strap_net=f'CH{int(m[1]) + (8 if m[3] else 0)}_{m[2]}')
            else:
                row['strap_net'] = AUX[net]
            rows.append(row)
    return rows, hashlib.sha256(D17_PCB.read_bytes()).hexdigest()


D17_ROWS, D17_SHA = d17_interface()
with (HERE / 'd17-interface.csv').open('w', newline='', encoding='utf-8') as fh:
    w_ = csv.DictWriter(fh, fieldnames=list(D17_ROWS[0]), lineterminator='\n'); w_.writeheader(); w_.writerows(D17_ROWS)
pin_net = {con: {r['pin']: r['strap_net'] for r in D17_ROWS if r['connector'] == con} for con in CONN}
assert sorted(n for c in pin_net.values() for n in c.values() if n.startswith('CH')) == sorted(f'CH{c}_{p}' for c in range(1, 17) for p in 'PN')

# ---------- R12 的触点和串阻（照抄） ----------


def r12_parts():
    out = {}
    for s in 'ab':
        b = load_copy(R12 / f'strap-{s}.kicad_pcb')
        for f in b.GetFootprints():
            ref = f.GetReference()
            if ref.startswith('TAIL'):
                continue
            pads = []
            for p in f.Pads():
                bb = p.GetBoundingBox()
                circle = p.GetShape() == k.PAD_SHAPE_CIRCLE
                pads.append(dict(num=p.GetNumber(), net=p.GetNetname(), x=round(mm(p.GetPosition().x), 4), y=round(mm(p.GetPosition().y), 4),
                                 w=round(mm(bb.GetWidth()), 3), h=round(mm(bb.GetHeight()), 3), circle=circle,
                                 drill=round(mm(p.GetDrillSize().x), 3) if circle else None))
            fy = round(mm(f.GetPosition().y), 4)
            is_ext = any(re.match(r'^CH([3-9]|1\d)_', q['net']) for q in pads)
            dy = (-EXT_PAIR_DY if fy < YC else EXT_PAIR_DY) if is_ext else 0.0
            if dy:
                fy = round(fy + dy, 4)
                for q in pads:
                    q['y'] = round(q['y'] + dy, 4)
            out[ref] = dict(piece=s, x=round(mm(f.GetPosition().x), 4), y=fy, layer=f.GetLayerName(),
                            value=f.GetValue(), pads=pads, ext_shifted=bool(is_ext))
    return out


R12P = r12_parts()


def r12_pad(net):
    """R12 上网名为 net 的串阻焊盘（尾侧或电极侧）中心。"""
    (p,) = [(q['x'], q['y']) for r, d in R12P.items() if r.startswith('R') for q in d['pads'] if q['net'] == net]
    return p


def r12_contact(ref):
    d = R12P[ref]
    return d['x'], d['y']


# ---------- 一片板的容器 ----------


class Piece:
    def __init__(self, name):
        self.name = name
        self.traces = []        # [net, layer, pts, tag]
        self.vias = []          # (net, (x,y))
        self.fps = []
        self.shapes = []
        self.holes = []         # (x,y,r) Edge.Cuts 圆孔
        self.cut = []
        self.dyn = []           # 动态区 (x0,x1,y0,y1,name)
        self.stiff = []
        self.legs = {}          # net -> trace 索引（可加凸起的 B 面腿）
        self.C = {}             # ch -> 对中心线
        self.start = {}         # ch -> (n_start, p_start)
        self.lanes = {}         # 记录：段名 -> 道

    def tr(self, net, layer, pts, tag=''):
        self.traces.append([net, layer, clean(pts), tag])
        return len(self.traces) - 1

    def via(self, net, p):
        self.vias.append((net, (round(p[0], 6), round(p[1], 6))))

    def advance(self, order, Y, T, x0, obst=()):
        """order（自上而下）各对从 Y 换到 T，规划见 plan()。返回各对斜线终点 x。"""
        XS, d = plan(Y, T, x0, obst)
        ends = []
        for ch, y, t, xs, dd in zip(order, Y, T, XS, d):
            assert abs(self.C[ch][-1][1] - y) < 1e-6, (self.name, ch, self.C[ch][-1], y)
            if abs(dd) > 1e-9:
                self.C[ch] += [(xs, y), (round(xs + abs(dd), 6), t)]
            ends.append(round(xs + abs(dd), 6))
        return ends


def place_r12(pc):
    for ref, d in R12P.items():
        if d['piece'] == pc.name:
            pc.fps.append(dict(kind='r12', ref=ref, **d))


def pair_traces(pc, ch, layer, center, n_sign, n_end, p_end, tag):
    """center：对中心线；n_sign：N 的偏移符号。两端：金手指收口（pc.start）与过孔入口。"""
    n_start, p_start = pc.start[ch]
    center = clean(center)
    Nc, Pc = offset(center, n_sign * HP), offset(center, -n_sign * HP)
    assert math.dist(n_start[-1], Nc[0]) < 1e-6 and math.dist(p_start[-1], Pc[0]) < 1e-6, (ch, 'start')
    assert math.dist(n_end[0], Nc[-1]) < 1e-6 and math.dist(p_end[0], Pc[-1]) < 1e-6, (ch, 'end', n_end[0], Nc[-1])
    pc.tr(f'CH{ch}_N', layer, n_start + Nc[1:] + n_end[1:], tag)
    pc.tr(f'CH{ch}_P', layer, p_start + Pc[1:] + p_end[1:], tag)


def legs(pc, ch, xn, yn, xp, yp):
    """B 面腿：过孔→R12 串阻尾侧焊盘；串阻电极侧焊盘→R12 触点（竖直短线）。"""
    cxn, ynt = r12_pad(f'CH{ch}_N')
    cxp, ypt = r12_pad(f'CH{ch}_P')
    assert cxn == cxp
    cx = cxn
    pc.legs[f'CH{ch}_N'] = pc.tr(f'CH{ch}_N', 'B', [(xn, yn), (xn, ynt + abs(xn - cx) + 0.4), (cx, ynt + 0.4), (cx, ynt)], 'leg')
    pc.legs[f'CH{ch}_P'] = pc.tr(f'CH{ch}_P', 'B', [(xp, yp), (xp, ypt - abs(xp - cx) - 0.4), (cx, ypt - 0.4), (cx, ypt)], 'leg')
    for pol in 'NP':
        pc.tr(f'CH{ch}_{pol}_E', 'B', [r12_pad(f'CH{ch}_{pol}_E'), r12_contact(f'E{ch}{pol}')], 'elec')


def island(cx, left, right):
    """电极岛：外沿 cx±2.8（y 39/61，总高 22.0 mm），颈部 cx±3.5 接左右桥（left/right=(y0,y1)）。"""
    return [(cx - 3.5, left[0]), (cx - 2.8, ISL_Y0), (cx + 2.8, ISL_Y0), (cx + 3.5, right[0]),
            (cx + 3.5, right[1]), (cx + 2.8, ISL_Y1), (cx - 2.8, ISL_Y1), (cx - 3.5, left[1])]


def fingers(pc, ref, con, tip, face, ypin):
    """金手指：沿 +x 从 tip+setback 起，长 1.5。返回 (中心 x, 末端 x)。"""
    xc = tip + FINGER['setback'] + FINGER['l'] / 2
    pads = [(str(p), pin_net[con][p], xc, ypin(p)) for p in range(1, FINGER['n'] + 1)]
    ys = [ypin(1), ypin(FINGER['n'])]
    # 整排覆盖膜开窗：尖端到金手指末端前 0.3（末端 0.3 压在覆盖膜下），上下各比金手指多 0.15
    gang = (tip, tip + FINGER['setback'] + FINGER['l'] - 0.3, min(ys) - FINGER['w'] / 2 - 0.15, max(ys) + FINGER['w'] / 2 + 0.15)
    pc.fps.append(dict(ref=ref, kind='finger', face=face, pads=pads, gang=gang))
    pc.gang = gang
    return xc, tip + FINGER['setback'] + FINGER['l']


def conv(pc, con, ypin, xc, xe, ch):
    """金手指出线，对内从 0.5 收到 0.30；对中心线从 (xe+0.1, yc) 起。"""
    pp = next(p for p, n in pin_net[con].items() if n == f'CH{ch}_P')
    pn = next(p for p, n in pin_net[con].items() if n == f'CH{ch}_N')
    yp, yn = ypin(pp), ypin(pn)
    assert abs(abs(yp - yn) - 0.5) < 1e-9
    s = 1 if yn < yp else -1
    pc.start[ch] = ([(xc, yn), (xe, yn), (xe + 0.1, yn + 0.1 * s)], [(xc, yp), (xe, yp), (xe + 0.1, yp - 0.1 * s)])
    yc = (yp + yn) / 2
    pc.C[ch] = [(xe + 0.1, yc)]
    return yc


def gnd_tail(pc, con, ypin, xc, xe, xv, via_at=None):
    """AGND 金手指：相邻几根在金手指末端（覆盖膜下）用竖线并起来，取中间一根直线走出折弯区，
    在折弯区之后的静态区打过孔进 In1/In2（补强区、插入区内不打孔）。"""
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
        pc.tr('AGND', 'F', [(xc, ypin(t)), v], 'gnd')
        pc.via('AGND', v)
    return runs


def stitch(pc, pts):
    for p in pts:
        pc.via('AGND', p)


def tail_stiff(pc, x0, x1, y0, y1, side, name):
    pc.stiff.append(dict(rect=(x0, x1, y0, y1), side=side, name=name, thickness=STIFF_T_TAIL, holes=[], windows=[], keep=[]))


def island_stiff(pc, ch, cx):
    """电极岛补强（B 面，非贴肤面）：盖满整个 Ø1.8 触点焊盘，只开端子孔 Ø1.0（= 钻孔）；
    串阻处开窗（焊盘外扩 0.2），窗被触点焊盘外 0.05 的圆截掉，窗不进触点焊盘。"""
    holes, windows, keep = [], [], []
    for pol in 'NP':
        x, y = r12_contact(f'E{ch}{pol}')
        holes.append((x, y, 0.5))
        keep.append((x, y, 0.95))
    for ref, d in R12P.items():
        if ref.startswith('R') and any(q['net'].startswith(f'CH{ch}_') for q in d['pads']):
            x0 = min(q['x'] - q['w'] / 2 for q in d['pads']) - 0.2
            x1 = max(q['x'] + q['w'] / 2 for q in d['pads']) + 0.2
            y0 = min(q['y'] - q['h'] / 2 for q in d['pads']) - 0.2
            y1 = max(q['y'] + q['h'] / 2 for q in d['pads']) + 0.2
            windows.append((round(x0, 3), round(x1, 3), round(y0, 3), round(y1, 3)))
    pc.stiff.append(dict(rect=(cx - 2.4, cx + 2.4, STIFF_Y0, STIFF_Y1), side='B', name=f'CH{ch}岛补强', thickness=STIFF_T_ISL,
                         holes=holes, windows=windows, keep=keep))


def peel_entry(xv, top_net_is_p):
    """对中心线以水平到 (xv-0.2, 50) 结束；上面那根 45° 进 (xv, 49.65)，下面那根进 (xv+0.65, 50.35)。"""
    up = [(xv - 0.2, YC - HP), (xv, YC - 0.35)]
    dn = [(xv - 0.2, YC + HP), (xv, YC + 0.35), (xv + 0.65, YC + 0.35)]
    return (dn, up) if top_net_is_p else (up, dn)        # (n_end, p_end)


# =====================================================================
# 片 A：→ D17 V4_FPC1。金手指在 F 面，pin1 在小 y（尖端朝 -x）；同 R7/R12。
# =====================================================================
A = Piece('a')
place_r12(A)
TA = 30.16
yA = lambda p: 41.75 + (p - 1) * 0.5
xcA, xeA = fingers(A, 'TAIL_A', 'FPC1', TA, 'F', yA)
tail_stiff(A, TA, TA + STIFF, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'B', '尾A补强（B面，金手指背面）')
A.dyn.append((32.71, 38.87, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'A尾折弯'))          # 同 R11
A.gnd_runs = gnd_tail(A, 'FPC1', yA, xcA, xeA, round(38.87 + TAIL_VIA_DX, 3), {34: (40.2, yA(34))})
A_TAIL_VIAS = [(p, R_VIA) for n, p in A.vias if n == 'AGND']
# BIAS_DRV1（33 脚，尾下沿）：F 沿盒底下沿 y=60 到 R12 过孔 (69,60)，B 面到 R33（R12 位置），再到 EB1
yb = yA(33)
A.tr('BIAS_DRV1', 'F', [(xcA, yb), (40.8, yb), (43.05, 60.0), (69.0, 60.0)], 'bias')
A.via('BIAS_DRV1', (69.0, 60.0))
A.tr('BIAS_DRV1', 'B', [(69.0, 60.0), r12_pad('BIAS_DRV1')], 'bias')
A.tr('BIAS_DRV1_E', 'B', [r12_pad('BIAS_DRV1_E'), (69.0, 53.5), r12_contact('EB1')], 'bias')

# --- 盒底 CH1/CH2（尾上部）：CH1 从 B 的 EB2 让位孔上方过、CH2 从下方过，过孔后 B 面到串阻 ---
for ch, path, xv in ((1, [(43.2, 44.0), (47.5, 48.3), (51.7, 48.3), (53.4, 50.0)], 53.9),          # 绕让位孔 Ø2.2：外侧铜到孔边 0.375
                     (2, [(43.2, 46.0), (48.9, 51.7), (59.8, 51.7), (61.5, 50.0)], 62.0)):
    yc = conv(A, 'FPC1', yA, xcA, xeA, ch)
    assert abs(yc - path[0][1]) < 1e-9
    A.C[ch] += path + [(xv - 0.2, YC)]
    ne, pe = peel_entry(xv, True)
    pair_traces(A, ch, 'F', A.C[ch], +1, ne, pe, 'box')
    A.via(f'CH{ch}_P', (xv, YC - 0.35)); A.via(f'CH{ch}_N', (xv + 0.65, YC + 0.35))
    legs(A, ch, xv + 0.65, YC + 0.35, xv, YC - 0.35)

# --- 南带 CH5–8：盒底里走 A_HEAD 道，出盒前换到 A 带等分道，每岛最上一对上到 y=50 打孔，其余在岛内重新等分 ---
A_ISL = {5: 90.0, 6: 98.0, 7: 106.0, 8: 114.0}


def LA(n):
    return [round(A_BAND[0] + PM, 4)] if n == 1 else lanes(A_BAND, n)   # 只剩一对时贴上侧走（无相邻对，省 2.3 mm 爬升）


def isl_lanes_A(m):
    L = LA(m)
    s = max(0.0, L[-1] - A_ISL_MAX)
    return [round(y - s, 4) for y in L]


order = [5, 6, 7, 8]
fy = [conv(A, 'FPC1', yA, xcA, xeA, ch) for ch in order]
A.advance(order, fy, A_HEAD, 40.2, A_TAIL_VIAS)
A.lanes['A盒底'] = A_HEAD
A.advance(order, A_HEAD, LA(4), 68.0, [(r12_contact('E2P'), R_PAD), ((69.0, 60.0), R_VIA)])
A.lanes['A出盒带'] = LA(4)
rem = list(order)
for ch in order:
    cx = A_ISL[ch]
    n = len(rem)
    cont = rem[1:]
    IL = isl_lanes_A(n - 1) if cont else []
    obst = [(r12_contact(f'E{ch}N'), R_PAD), (r12_contact(f'E{ch}P'), R_PAD)]
    ends = A.advance(rem, LA(n), [YC] + IL, cx - 3.25, obst)      # 晚于岛颈角 0.25 起斜，外侧线不擦颈角
    xv = round(max(ends[0] + 0.4, cx + 0.8), 3)
    A.C[ch] += [(xv - 0.2, YC)]
    ne, pe = peel_entry(xv, True)
    pair_traces(A, ch, 'F', A.C[ch], +1, ne, pe, 'band')
    A.via(f'CH{ch}_P', (xv, YC - 0.35)); A.via(f'CH{ch}_N', (xv + 0.65, YC + 0.35))
    legs(A, ch, xv + 0.65, YC + 0.35, xv, YC - 0.35)
    if cont:
        A.lanes[f'A岛CH{ch}内'] = IL
        A.advance(cont, IL, LA(n - 1), cx + 1.35, obst + [((xv, YC - 0.35), R_VIA), ((xv + 0.65, YC + 0.35), R_VIA)])
        A.lanes[f'A桥{ch - 4}'] = LA(n - 1)
    rem = cont

# --- 北支 CH3/CH4（尾中部）：F 直出到阶梯过孔换 B → 上行左转进北支（B 面）→ 北岛 B 面分叉 ---
BUSX = 41.6
NOFF = round((NORTH[1] - NORTH[0]) / 2 - PM, 4)                # 两对中心离北支中线 ±NOFF（外侧铜到边 0.315）
LANE = {'CH4_N': NOFF + HP, 'CH4_P': NOFF - HP, 'CH3_N': -(NOFF - HP), 'CH3_P': -(NOFF + HP)}   # 上行时相对总线中心的 x 偏移
VX = {'CH3_N': BUSX + LANE['CH3_N'], 'CH4_P': BUSX + LANE['CH4_P']}
VX['CH3_P'] = VX['CH3_N'] - 0.6
VX['CH4_N'] = VX['CH4_P'] + 0.6
YNB = (NORTH[0] + NORTH[1]) / 2
BUS = [(BUSX, 46.2), (BUSX, 41.3), (BUSX - (41.3 - YNB), YNB)]                 # 北支总线中心线（B 面）
A.lanes['A北支'] = [round(YNB - NOFF, 4), round(YNB + NOFF, 4)]


def north(ch, dlt):
    """返回 CH3/CH4 两条腿（尚未落板）；dlt：分叉线相对 y=50 的下移量（调等长用）。"""
    out = {}
    jog = {}
    for pol in 'NP':
        net = f'CH{ch}_{pol}'
        y0 = yA(next(p for p, n in pin_net['FPC1'].items() if n == net))
        lx = BUSX + LANE[net]
        jog[net] = ([(xcA, y0), (VX[net], y0)], [(VX[net], y0), (VX[net], 46.75), (lx, 46.75 - abs(lx - VX[net])), (lx, 46.2)])
    cpair = offset(BUS + [(27.9 if ch == 3 else 22.9, YNB)], NOFF if ch == 4 else -NOFF)
    ys = YC + dlt
    if ch == 3:
        cpair += [(26.9, cpair[-1][1] + 1.0), (26.9, ys - 0.9), (26.0, ys), (25.8, ys)]
    else:
        # 过北颈时对中心在 y=50（颈下沿 50.725），进 CH4 岛后再平移 dlt
        cpair += [(21.9, cpair[-1][1] + 1.0), (21.9, 49.1), (21.0, YC)]
        cpair += [(19.3, YC), (19.3 - abs(dlt), ys), (17.8, ys)] if abs(dlt) > 0.05 else [(17.8, YC)]
    cpair = clean(cpair)
    cx = r12_pad(f'CH{ch}_N')[0]
    Nc, Pc = offset(cpair, HP), offset(cpair, -HP)
    dx = cpair[-1][0] - cx
    for pol, cl, sgn in (('N', Nc, -1), ('P', Pc, 1)):
        net = f'CH{ch}_{pol}'
        assert math.dist(jog[net][1][-1], cl[0]) < 1e-6, (net, jog[net][1][-1], cl[0])
        ye = cl[-1][1]
        if pol == 'N':
            end = [(cx, ye - dx), r12_pad(net)]
        else:
            px, py = r12_pad(net)                    # R12：P 串阻横放，从左边沿元件轴进焊盘
            end = [(cx, ye + dx), (cx, py - 0.1), (cx + 0.1, py), (px, py)]
        out[net] = (jog[net][0], jog[net][1] + cl[1:] + end)
    return out


def north_len(legs_, pol):
    f, b = legs_[pol]
    return plen(clean(f)) + plen(clean(b))


north_dlt = {}
for ch in (4, 3):
    dlt = 0.0
    for _ in range(3):                       # 长度差对 dlt 线性（N 长 +dlt、P 长 −dlt），迭代两次即收敛
        lg = north(ch, dlt)
        diff = north_len(lg, f'CH{ch}_P') - north_len(lg, f'CH{ch}_N')
        if abs(diff) < 1e-6:
            break
        dlt += diff / 2
    north_dlt[ch] = round(dlt, 4)
    for net, (fpts, bpts) in lg.items():
        A.tr(net, 'F', fpts, 'north')
        A.via(net, fpts[-1])
        A.tr(net, 'B', bpts, 'north')
    for pol in 'NP':
        e = f'CH{ch}_{pol}_E'
        if pol == 'N':
            A.tr(e, 'B', [r12_pad(e), r12_contact(f'E{ch}N')], 'elec')
        else:                                    # R12：P 电极侧 竖 0.8 → 45° → 竖到触点
            ex, ey = r12_pad(e)
            cxp, cyp = r12_contact(f'E{ch}P')
            A.tr(e, 'B', [(ex, ey), (ex, ey + 0.8), (cxp, ey + 0.8 + (ex - cxp)), (cxp, cyp)], 'elec')

# --- A 外形 ---
A.shapes += [
    [(12.5, 44.88), (13.2, ISL_Y0), (18.8, ISL_Y0), (19.5, 44.88), (19.5, 50.725), (18.8, ISL_Y1), (13.2, ISL_Y1), (12.5, 50.225)],   # CH4 岛（外扩至 39/61）
    rect(19.4, 20.6, *NECK),
    [(20.5, 44.88), (21.2, NORTH[0]), (27.5, NORTH[0]), (28.8, NORTH[1]), (27.5, 50.225), (26.8, ISL_Y1), (21.2, ISL_Y1), (20.5, 50.725)],  # CH3 岛（下沿外扩至 61）
    rect(27.0, 39.6, *NORTH),                                         # 北支（下沿同 R12 40.85，上沿外扩 0.3）
    rect(TA, 39.6, 50 - TAIL_W / 2, 50 + TAIL_W / 2),                 # 尾
    [(39.5, NORTH[0]), (41.5, NORTH[0]), (43.75, 37.0), (75.0, 37.0), (75.0, 63.0), (43.75, 63.0), (39.5, 58.75)],   # 盒底头部（同 R11/R12）
    rect(74.9, 86.6, *A_BAND),                                        # 出盒带
]
for ch, cx in sorted(A_ISL.items()):
    A.shapes.append(island(cx, A_BAND, A_BAND))
    if ch != 8:
        A.shapes.append(rect(cx + 3.4, cx + 4.6, *A_BAND))
A.cut = [circ(39.5, 41.35, 0.5, 64)]          # 北支与尾之间 0.4 缝的缝底圆（同 R11）
A.holes.append((50.5, 50.0, RELIEF_R))         # 给片 B 的 EB2 让位（R12 Ø2.0，R14/R15 Ø2.2）
yd = (A_BAND[0] - 0.3, A_BAND[1] + 0.3)
A.dyn += [(28.9, 39.5, NORTH[0] - 0.3, NORTH[1] + 0.25, 'A北支'), (19.55, 20.45, 44.5, 51.0, 'A北颈'),
          (75.5, 86.0, *yd, 'A带根'), (93.55, 94.45, *yd, 'A桥1'), (101.55, 102.45, *yd, 'A桥2'), (109.55, 110.45, *yd, 'A桥3')]
for ch, cx in [(3, 24.0), (4, 16.0)] + sorted(A_ISL.items()):
    island_stiff(A, ch, cx)
stitch(A, [(cx + dx, 41.3 - EXT_PAIR_DY) for cx in A_ISL.values() for dx in (-2.0, 2.0)] + [(cx + dx, 58.7 + EXT_PAIR_DY) for cx in A_ISL.values() for dx in (-2.0, 2.0)] +
       [(14.0, 41.3 - EXT_PAIR_DY), (18.0, 41.3 - EXT_PAIR_DY), (14.0, 58.7 + EXT_PAIR_DY), (18.0, 58.7 + EXT_PAIR_DY), (22.2, 58.7 + EXT_PAIR_DY), (26.0, 58.7 + EXT_PAIR_DY),
        (46.0, 40.0), (58.0, 39.5), (73.5, 38.5), (47.0, 61.6), (58.0, 61.6), (73.5, 61.6)])

# =====================================================================
# 片 B：→ D17 V4_FPC3。金手指在 F 面，pin1 在大 y（尖端朝 -x）；同 R7/R12。
# =====================================================================
B = Piece('b')
place_r12(B)
TB = 32.39
yB = lambda p: 58.25 - (p - 1) * 0.5
xcB, xeB = fingers(B, 'TAIL_B', 'FPC3', TB, 'F', yB)
tail_stiff(B, TB, TB + STIFF, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'B', '尾B补强（B面，金手指背面）')
B.dyn.append((34.94, 38.34, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'B尾折弯'))           # 同 R11
B.gnd_runs = gnd_tail(B, 'FPC3', yB, xcB, xeB, round(38.34 + TAIL_VIA_DX, 3))
B_TAIL_VIAS = [(p, R_VIA) for n, p in B.vias if n == 'AGND']
# BIAS_DRV12（V4_RLD_OUT2，34 脚，尾上沿）：F 出折弯区后过孔到 B 面，沿 B 头部上沿到 R34（R12 位置），再到 EB2
yb = yB(34)
xbv = 40.2                                      # 过孔在尾部 AGND 过孔列（x 39.24）右边，孔间净距 ≥0.5
B.tr('BIAS_DRV12', 'F', [(xcB, yb), (xbv - 0.15, yb), (xbv, yb + 0.15)], 'bias')
B.via('BIAS_DRV12', (xbv, yb + 0.15))
r34x, r34y = r12_pad('BIAS_DRV12')
yt = B_HEAD_TOP + 0.4                           # B 面沿头部上沿走，铜到边 0.325
B.tr('BIAS_DRV12', 'B', [(xbv, yb + 0.15), (44.0, yb + 0.15), (44.0 + yt - yb - 0.15, yt), (55.2, yt), (55.6, yt + 0.4), (55.6, r34y - 0.4), (55.2, r34y), (r34x, r34y)], 'bias')
B.tr('BIAS_DRV12_E', 'B', [r12_pad('BIAS_DRV12_E'), r12_contact('EB2')], 'bias')

B_ISL = {ch: 122.0 + (ch - 9) * 8 for ch in range(9, 17)}
order = list(range(16, 8, -1))                                   # 自上而下 CH16…CH9
fy = [conv(B, 'FPC3', yB, xcB, xeB, ch) for ch in order]
B.advance(order, fy, B_HEAD, 39.4, [(r12_contact('EB2'), R_PAD)] + B_TAIL_VIAS)
B.lanes['B头部'] = B_HEAD
LBo = lanes(B_BAND, 8)
ends = B.advance(order, B_HEAD, LBo, 63.9, [((65.5, 50.0), HOLE_KEEP)])
B.lanes['B并行段'] = LBo
# 头部下沿/上沿的 45° 斜边跟着 CH9/CH16 的斜线走，起点比对中心线拐点晚 0.22（外侧线斜接拐点仍离边 ≥0.315）
x9 = round(next(p[0] for p in B.C[9] if p[0] > 63.9) + 0.22, 3)
x16 = round(next(p[0] for p in B.C[16] if p[0] > 63.9) + 0.22, 3)
R33 = R12P['R33']
r33_x0 = min(q['x'] - q['w'] / 2 for q in R33['pads']) - 0.2
r33_y0 = min(q['y'] - q['h'] / 2 for q in R33['pads']) - 0.2
assert x9 + (B_HEAD_BOT - B_BAND[1]) <= r33_x0, ('B 头部下沿压到 A 的 R33 窗', x9, r33_x0)


def LB(n):
    return lanes(B_BR, n)


rem = list(order)
for i, ch in enumerate(range(9, 17)):
    cx = B_ISL[ch]
    n = len(rem)
    Y = LBo if i == 0 else LB(n)
    T = LB(n - 1) + [YC]
    obst = [(r12_contact(f'E{ch}N'), R_PAD), (r12_contact(f'E{ch}P'), R_PAD)]
    ends = B.advance(rem, Y, T, cx - 3.25, obst)
    xv = round(max(ends[-1] + 0.4, cx - 1.6), 3)
    B.C[ch] += [(xv - 0.2, YC)]
    ne, pe = peel_entry(xv, False)
    pair_traces(B, ch, 'F', B.C[ch], -1, ne, pe, 'band')
    B.via(f'CH{ch}_N', (xv, YC - 0.35)); B.via(f'CH{ch}_P', (xv + 0.65, YC + 0.35))
    legs(B, ch, xv, YC - 0.35, xv + 0.65, YC + 0.35)
    rem = rem[:-1]
    if rem:
        B.lanes[f'B桥{ch - 8}'] = LB(n - 1)

# --- B 外形 ---
B_HEAD_POLY = [(41.2, 41.25), (44.0, 41.25), (44.0 + B_HEAD_TOP - 41.25, B_HEAD_TOP), (x16, B_HEAD_TOP), (x16 + B_BAND[0] - B_HEAD_TOP, B_BAND[0]), (75.0, B_BAND[0]),
               (75.0, B_BAND[1]), (x9 + B_HEAD_BOT - B_BAND[1], B_BAND[1]), (x9, B_HEAD_BOT), (44.0 + 58.75 - B_HEAD_BOT, B_HEAD_BOT), (44.0, 58.75), (41.2, 58.75)]
B.shapes += [rect(TB, 41.3, 50 - TAIL_W / 2, 50 + TAIL_W / 2), B_HEAD_POLY, rect(74.9, 118.6, *B_BAND)]
for ch, cx in sorted(B_ISL.items()):
    B.shapes.append(island(cx, B_BAND if ch == 9 else B_BR, B_BR if ch != 16 else (45.0, 55.0)))
    if ch != 16:
        B.shapes.append(rect(cx + 3.4, cx + 4.6, *B_BR))
B.holes.append((65.5, 50.0, RELIEF_R))         # 给片 A 的 EB1 让位（R12 Ø2.0，R14 Ø2.2）
yb_ = (B_BAND[0] - 0.3, B_BAND[1] + 0.3)
B.dyn += [(75.5, 86.0, *yb_, 'B带根')] + [(x, x + 0.9, *yb_, f'B过A桥{i + 1}') for i, x in enumerate((93.55, 101.55, 109.55, 117.55))] + \
         [(cx + 3.55, cx + 4.45, B_BR[0] - 0.3, B_BR[1] + 0.3, f'B桥{ch - 8}') for ch, cx in sorted(B_ISL.items()) if ch != 16]
for ch, cx in sorted(B_ISL.items()):
    island_stiff(B, ch, cx)
stitch(B, [(cx + dx, y) for cx in B_ISL.values() for dx in (-2.0, 2.0) for y in (41.3 - EXT_PAIR_DY, 58.7 + EXT_PAIR_DY)] + [(57.5, 50.0), (61.5, 50.0)])

# =====================================================================
# 分段等长（南岛、盒底：B 面腿上加 45° 凸起；北岛已在 north() 里解出）
# =====================================================================


def seg_len(pc, net):
    return sum(plen(t[2]) for t in pc.traces if t[0] == net)


def tune(pc):
    rows = []
    chs = sorted({int(t[0][2:].split('_')[0]) for t in pc.traces if t[0].startswith('CH')})
    for ch in chs:
        row = dict(ch=ch, bumps=[], method='凸起' if f'CH{ch}_N' in pc.legs else f'北岛分叉线下移 {north_dlt.get(ch, 0):+.4f} mm')
        n, p = f'CH{ch}_N', f'CH{ch}_P'
        d = seg_len(pc, n) - seg_len(pc, p)
        if abs(d) > TOL:
            assert n in pc.legs, (pc.name, ch, d)
            short = p if d > 0 else n
            idx = pc.legs[short]
            pts = pc.traces[idx][2]
            e = abs(d) / (2 * (math.sqrt(2) - 1))
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

# =====================================================================
# 输出 KiCad
# =====================================================================
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
    x0, x1, y0, y1 = st['rect']
    s = polyset(rect(x0, x1, y0, y1))
    for wx0, wx1, wy0, wy1 in st['windows']:
        s.BooleanSubtract(polyset(rect(wx0, wx1, wy0, wy1)))
    for x, y, r in st['keep']:                      # 触点焊盘外 0.05 以内保留补强
        disc = polyset(circ(x, y, r, 96))
        disc.BooleanIntersection(polyset(rect(x0, x1, y0, y1)))
        s.BooleanAdd(disc)
    for x, y, r in st['holes']:
        s.BooleanSubtract(polyset(circ(x, y, r, 64)))
    s.Simplify()
    return s


def poly_rings(s):
    rings = []
    for i in range(s.OutlineCount()):
        for ch in [s.Outline(i)] + [s.Hole(i, j) for j in range(s.HoleCount(i))]:
            rings.append([(ch.CPoint(j).x / 1e6, ch.CPoint(j).y / 1e6) for j in range(ch.PointCount())])
    return rings


def mesh_holes(pc, ol):
    """动态区（禁孔矩形沿 x 各外扩 0.55）里的 45° 菱形禁铺孔，孔边 0.42、节距 0.60（网格线 0.18）。
    孔心须在铜区（板内缩 0.305）内；离过孔/触点焊盘 ≥0.15。每个区按孔数最多选格点相位。"""
    a = MESH['pitch'] / math.sqrt(2)
    d = MESH['hole'] / math.sqrt(2)                 # 半对角线
    ok = polyset(ol)
    for x, y, r in pc.holes:
        ok.BooleanSubtract(polyset(circ(x, y, r, 64)))
    ok.Inflate(-round(0.305e6), k.CORNER_STRATEGY_ROUND_ALL_CORNERS, 2000)
    avoid = [(p, VIA[0] / 2) for _, p in pc.vias] + [((f['x'], f['y']), 0.9) for f in pc.fps if f['kind'] == 'r12' and f['ref'].startswith('E')]
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
            nets.append(pd['net'] if f['kind'] == 'r12' else pd[1])
    order_ = ['']
    for n in nets:
        if n not in order_:
            order_.append(n)
    nid = {n: i for i, n in enumerate(order_)}
    out = [HEADER]
    out += [f'(net {i} "{n}")' for i, n in enumerate(order_)]
    for f in pc.fps:
        ref = f['ref']
        if f['kind'] == 'r12':
            x, y = f['x'], f['y']
            pads = ''
            for q in f['pads']:
                at = f'(at {f6(q["x"] - x)} {f6(q["y"] - y)})'
                if q['circle']:
                    pads += f'(pad "{q["num"]}" thru_hole circle {at} (size {q["w"]} {q["h"]}) (drill {q["drill"]}) (layers "*.Cu" "*.Mask") (remove_unused_layers no) (net {nid[q["net"]]} "{q["net"]}"))'
                else:
                    side = 'B' if f['layer'] == 'B.Cu' else 'F'
                    pads += f'(pad "{q["num"]}" smd rect {at} (size {q["w"]} {q["h"]}) (layers "{side}.Cu" "{side}.Paste" "{side}.Mask") (net {nid[q["net"]]} "{q["net"]}"))'
            if ref.startswith('E'):
                out.append(f'(footprint "CONTACT_D1.8" (layer "F.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1)))) (property "Value" "贴肤触点" (at 0 1.4 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (attr through_hole) {pads})')
            else:
                fpn = 'R0603' if f['value'] == '200k' else 'R0402'
                out.append(f'(footprint "{fpn}" (layer "B.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "B.Fab") (effects (font (size 0.4 0.4) (thickness 0.06)) (justify mirror))) (property "Value" "{f["value"]}" (at 0 0.9 0) (layer "B.Fab") (hide yes) (effects (font (size 0.4 0.4) (thickness 0.06)) (justify mirror))) (attr smd) {pads})')
        else:
            lay = LAYER[f['face']]; m = lay.replace('Cu', 'Mask')
            pads = ''.join(f'(pad "{num}" smd rect (at {f6(x)} {f6(y)}) (size {FINGER["l"]} {FINGER["w"]}) (layers "{lay}" "{m}") (net {nid[net]} "{net}"))' for num, net, x, y in f['pads'])
            fab = 'F.Fab' if f['face'] == 'F' else 'B.Fab'
            gx0, gx1, gy0, gy1 = f['gang']
            gang = f'(fp_rect (start {f6(gx0)} {f6(gy0)}) (end {f6(gx1)} {f6(gy1)}) (stroke (width 0) (type solid)) (fill solid) (layer "{m}"))'
            out.append(f'(footprint "FPC34_P0.5_TAIL" (layer "{lay}") (at 0 0) (property "Reference" "{ref}" (at 0 0 0) (layer "{fab}") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (property "Value" "D17 {"V4_FPC1" if ref == "TAIL_A" else "V4_FPC3"}" (at 0 0 0) (layer "{fab}") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (attr smd allow_soldermask_bridges) {gang} {pads})')
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
        poly = stiff_poly(st)
        lay = 'User.1' if st['side'] == 'F' else 'User.2'
        for o in poly_rings(poly):
            out.append('(gr_poly (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in o) + f') (stroke (width 0.05) (type solid)) (fill none) (layer "{lay}"))')
        x0, x1, y0, y1 = st['rect']
        out.append(f'(gr_text "{st["name"]} PI {st["thickness"]}（含胶，假设）" (at {f6((x0 + x1) / 2)} {f6(y0 - 0.5)} 0) (layer "Cmts.User") (effects (font (size 0.4 0.4) (thickness 0.06))))')
    # GND 平面：整板一块实铺；动态区内用禁铺菱形孔做成 45° 网格
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
    txt = f'{"A→D17 V4_FPC1" if pc.name == "a" else "B→D17 V4_FPC3"} pin1 金手指在{f["face"]}面'
    out.append(f'(gr_text "{txt}" (at {f6(p1[2] - 1.2)} {f6(p1[3] + (-1.2 if pc.name == "a" else 1.2))} 0) (layer "Dwgs.User") (effects (font (size 0.6 0.6) (thickness 0.08)) (justify left)))')
    out.append(')')
    return '\n'.join(out), ol


DRU = '''(version 1)
(rule "R14 线宽" (constraint track_width (min 0.15mm)))
(rule "R14 铜间距" (constraint clearance (min 0.15mm)))
(rule "R14 铜到板边 12mil" (constraint edge_clearance (min 0.305mm)))
(rule "R14 金手指到尾尖（同 R7/R12，金手指离尖端 0.2）" (condition "A.Type == 'Pad' && A.memberOfFootprint('TAIL_*')") (constraint edge_clearance (min 0.15mm)))
(rule "R14 过孔外径" (condition "A.Type == 'Via'") (constraint via_diameter (min 0.5mm)))
# 不同网的两条走线（同一差分对 CHn_P/CHn_N 除外）中心距 ≥ 0.47 mm（> 18 mil）：线宽 0.15 时净距 ≥ 0.32
(rule "R14 不同网走线中心距0.47" (condition "A.Type == 'Track' && B.Type == 'Track' && A.Net != B.Net && !A.isCoupledDiffPair()")
 (constraint clearance (min 0.32mm)))
'''


def project():
    p = json.loads((R12 / 'strap-a.kicad_pro').read_text())
    r = p['board']['design_settings']['rules']
    r.update(min_clearance=0.15, min_copper_edge_clearance=0.305, min_track_width=0.15, min_via_diameter=0.5,
             min_through_hole_diameter=0.25, min_via_annular_width=0.1, min_hole_clearance=0.2, min_hole_to_hole=0.25)
    p['board']['design_settings']['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': VIA[0], 'drill': VIA[1]}]
    for c in p['net_settings']['classes']:
        c.update(clearance=0.15, track_width=0.15, via_diameter=VIA[0], via_drill=VIA[1])
    return p


geo = {'d17_source': dict(file=str(D17_PCB.relative_to(ROOT)), sha256=D17_SHA),
       'meta_spacing_r15': dict(box_bottom_pair_spacing_mm=16.0, external_island_pair_spacing_mm=round(16.0 + 2 * EXT_PAIR_DY, 3),
                                external_pair_dy_mm=EXT_PAIR_DY, external_contact_y_mm=[round(42.0 - EXT_PAIR_DY, 3), round(58.0 + EXT_PAIR_DY, 3)],
                                circumferential_pitch_mm=8.0, island_pcb_height_mm=round(ISL_Y1 - ISL_Y0, 3),
                                island_stiffener_height_mm=round(STIFF_Y1 - STIFF_Y0, 3)),
       'bands': dict(A_BAND=A_BAND, B_BAND=B_BAND, B_BR=B_BR, NORTH=NORTH, NECK=NECK, gap_A_B=round(A_BAND[0] - B_BAND[1], 3)),
       'north_split_shift': north_dlt}
for pc in (A, B):
    txt, ol = emit(pc)
    path = HERE / f'strap-{pc.name}.kicad_pcb'
    path.write_text(txt, encoding='utf-8')
    b = k.LoadBoard(str(path))
    k.ZONE_FILLER(b).Fill(b.Zones())
    k.SaveBoard(str(path), b)
    proj = project()
    proj['meta']['filename'] = f'strap-{pc.name}.kicad_pro'
    (HERE / f'strap-{pc.name}.kicad_pro').write_text(json.dumps(proj, indent=2, ensure_ascii=False))
    (HERE / f'strap-{pc.name}.kicad_dru').write_text(DRU, encoding='utf-8')
    fing = next(f for f in pc.fps if f['kind'] == 'finger')
    geo[pc.name] = dict(outline=[[round(x, 4), round(y, 4)] for x, y in ol], holes=pc.holes,
                        dynamic_zones=[dict(name=n, x=[x0, x1], y=[y0, y1]) for x0, x1, y0, y1, n in pc.dyn],
                        stiffeners=[dict(name=st['name'], side=st['side'], layer='User.1' if st['side'] == 'F' else 'User.2', thickness_mm=st['thickness'],
                                         material='PI+胶（假设）', rect=st['rect'], holes=st['holes'], windows=st['windows']) for st in pc.stiff],
                        gang_opening=getattr(pc, 'gang', None), mesh=MESH, lanes=pc.lanes,
                        tail=dict(tip_x=TA if pc.name == 'a' else TB, width=TAIL_W, finger_face=fing['face'],
                                  pin1_y=next(p[3] for p in fing['pads'] if p[0] == '1'),
                                  pin34_y=next(p[3] for p in fing['pads'] if p[0] == '34'),
                                  finger=FINGER, stiffener_len=STIFF),
                        traces=[dict(net=n, layer=LAYER[l], pts=[[round(x, 5), round(y, 5)] for x, y in p], tag=t) for n, l, p, t in pc.traces],
                        vias=[dict(net=n, at=list(p)) for n, p in pc.vias])
(HERE / 'geometry.json').write_text(json.dumps(geo, ensure_ascii=False, indent=1))
(HERE / 'match.json').write_text(json.dumps(match, ensure_ascii=False, indent=1))
for prl in HERE.glob('*.kicad_prl'):
    prl.unlink()
worst = max(abs(r[k_]) for side in match.values() for r in side for k_ in ('tail_diff_mm', 'elec_diff_mm'))
print(f'R15 已生成：A {len(A.traces)} 线 {len(A.vias)} 孔；B {len(B.traces)} 线 {len(B.vias)} 孔；分段 P/N 最大差 {worst:.4f} mm（{worst / 0.0254:.2f} mil）')
