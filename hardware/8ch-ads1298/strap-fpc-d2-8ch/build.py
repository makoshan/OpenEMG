"""表带软板 D2-8CH（2026-11-12，配合 C08B 纯单面 8 通道采集板 D20-8CH / D20N-8CH）：单片四层软板直插 V4_FPC1。

叠层（从表带往皮肤）：25 mm 表带 → 本单片软板（背胶贴表带，F 面焊盘朝皮肤）→ 0.8 TPU 开孔层（孔 Φ6.5）→ Φ6×2.0 镀金铜片回流焊在 F 面焊盘上。
KiCad 自带 python3 运行：python3 build.py
- 派生自 hardware/16ch-c08b-round/strap-fpc-d2（commit 92318cfaa），专为 8 通道单芯片（V4_U1 ADS1298）去掉 B 片后的单片软板：
  - 胶囊底（2 路 + 2 辅助）：CH1/CH2 两对 Φ6.5 SMD 焊盘 + EB1/EB2 两个 Φ4.5 实心无孔 SMD 焊盘（方形 3×3×2 铜片）；
  - 消除 16ch A 片上悬空的 EB2A Φ0.8 对焊通孔：EB2 改为实心 F 面 SMD 焊盘，并在本片 B 面原 R34 槽位 (45.5, 50.0) 放置 200k 0603 串阻 R34，
    由 V4_FPC1.33 BIAS_DRV1 经独立 200k 驱动 EB2（与 R33→EB1 对称并联，零悬空贴肤金属、免除两片灌锡对焊工序、复用现有 6 孔底盖与 R34 浅槽）；
  - 北支 2 路：CH3/CH4（板 x 24/16）；
  - 南带 4 路：CH5–CH8（板 x 90/98/106/114，与 D2 TPU 层前 4 岛孔同心）。
输出 strap-d2-8ch.kicad_pcb（含填好的 GND 平面）、pro/dru、geometry.json、match.json、d17-interface.csv。
"""
import ast
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
R12 = ROOT / 'hardware/16ch-c08b-round/strap-fpc-r15'
R15 = ROOT / 'hardware/16ch-c08b-round/strap-fpc-r15'
TPU = ROOT / 'hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/build.py'
mm = k.ToMM
W = 0.15             # 线宽
HP = 0.15            # 对内半间距（中心距 0.30）
VIA = (0.5, 0.25)    # 过孔外径 / 孔径
TOL = 0.002          # 调长目标（mm），远小于 10 mil = 0.254
YC = 50.0
EDGE_M = 0.315       # 排线道时外侧铜到板边（规则 0.305，多留 0.01）
PM = EDGE_M + HP + W / 2     # 对中心到板边 0.54
PREQ = 0.82
R_VIA = VIA[0] / 2 + 0.15 + W / 2 + HP + 0.02      # 规划时对中心线离过孔中心的最小距离 0.645
R_PAD = 0.9 + 0.15 + W / 2 + HP + 0.02             # 同 R15：对中心线离盒底 Ø1.8 触点中心的最小距离
MESH = dict(pitch=0.60, hole=0.42, ext=0.55)
STIFF_T_TAIL = 0.10
STIFF_T_ISL = 0.20       # 触点 PI 补强 0.20（嘉立创 PI 档 0.1/0.15/0.2/0.225/0.25），≈ 叠放的 B 片 0.203：表带侧等高
FINGER = dict(w=0.30, l=1.5, setback=0.2, pitch=0.5, n=34)
TAIL_W = 17.5
STIFF = 2.5


# ---------- TPU 层常量（同源：焊盘中心 = TPU 孔中心） ----------
def tpu_consts():
    """只取 TPU 生成器里的几条常量赋值来算（不 import 它：它要 build123d）。"""
    want = ('PITCH', 'NORTH_YS', 'SOUTH_YS', 'STRAP_W', 'LAYER_W', 'PN', 'DISC_D', 'HOLE_CLEAR')
    ns = {}
    for node in ast.parse(TPU.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in want:
            exec(compile(ast.Module([node], []), str(TPU), 'exec'), ns)
    return {n: ns[n] for n in want}


TC = tpu_consts()
assert TC['PN'] == 18.0 and TC['PITCH'] == 8.0 and TC['DISC_D'] == 6.0, TC
to_x = lambda Y: round(58.0 - Y, 6)          # noqa: E731  表带 Y → 板 x
PN_Y = (round(YC - TC['PN'] / 2, 6), round(YC + TC['PN'] / 2, 6))      # N 41 / P 59
ISL_Y0, ISL_Y1 = round(YC - TC['LAYER_W'] / 2, 6), round(YC + TC['LAYER_W'] / 2, 6)   # 36.9 / 63.1，与 TPU 层同宽
NORTH_CH = (3, 4)                             # NORTH_YS 34/42 依次是 CH3、CH4（11-11 晚：CH1/CH2 回胶囊底）
assert tuple(TC['NORTH_YS']) == (34.0, 42.0), ('TPU 层北排应为 (34, 42)', TC['NORTH_YS'])
N_ISL = {ch: to_x(Y) for ch, Y in zip(NORTH_CH, TC['NORTH_YS'])}          # {3: 24, 4: 16}
S_ISL = {ch: to_x(Y) for ch, Y in zip(range(5, 17), TC['SOUTH_YS'])}      # CH5 90 … CH16 178
A_ISL = {ch: S_ISL[ch] for ch in range(5, 9)}
B_ISL = {ch: S_ISL[ch] for ch in range(9, 17)}

# ---------- 触点与岛 ----------
PAD_D = TC['DISC_D'] + 2 * 0.25        # Φ6.5：铜片 Φ6 四周各 0.25
PAD_R = PAD_D / 2
STIFF_D = 7.2                          # B 面 PI 补强片 Φ7.2（每触点一块）；= 岛宽 2×ISL_HW，不出外形（复核 11-11 P1：Φ7.5 越出岛边 0.15）
ISL_HW = 3.6                           # 岛半宽：焊盘边到岛侧边 0.35（门 ≥ 0.3，DRC 0.305）
SLIT_C = 55.6                          # 岛间下侧开缝的缝底圆心 y（缝宽 0.8，缝顶 55.2）；上侧不开缝，留整条给北支总线 / B 面
RES = (1.5, 4.3)                       # R_N 在 (cx−1.5, 45.7)、R_P 在 (cx+1.5, 54.3)，F 面
RPAD = (0.54, 0.64)                    # 0402 焊盘（同 R12），焊盘中心 ±0.51
LV = 0.74                              # 腿端过孔离串阻中心 0.74（焊盘边 0.32 + 铜距 0.17 + 过孔半径 0.25）
E_IN = 0.3                             # 电极侧短线伸进 Φ6.5 焊盘 0.3

# ---------- 各段带 ----------
NORTH = (ISL_Y0, 40.85)                # 北支：上沿与岛同（36.9），下沿同 R12（40.85，与尾缝 0.4）
ABAND = (50.46, 54.1)                  # A 南带（出盒带、桥、岛内）：对中心 51.0–53.56；上方让开岛中线的过孔对（50.35），下方让开 F 面 R_P 焊盘（53.98）
B_BAND = (46.32, 53.2)                 # B 与 A 并行段（垫在 A 背后）：离 A 的 R_N/R_P 焊盘 0.30、离 A 的 R33 焊盘 0.30
FORK_GAP = 0.35 + R_VIA                # 分叉对中心到上一条继续走的对中心 ≥ 0.995（让开 N 分叉过孔）
A_LOW = [54.0, 55.2, 56.4, 57.6]       # A 片 CH5–8 穿胶囊走 B 面（胶囊底 F 面被 Φ6.5 焊盘和 EB2 让位孔占满）：在孔下沿与 R1/R3 之间，节距 1.2 让开错位过孔
TAIL_VIA_DX = MESH['ext'] + VIA[0] / 2 + 0.1

# ---------- 11-11 晚 Mako 定：胶囊段 FPC 整段放到 R13 底壳外（贴外底 Z 0.15，外扣 0.8 平底盖），两条 34P 尾从底板一道缝穿进壳 ----------
# R13 盒坐标（Z 朝表带）：外面 B 片 Z −0.053…0.15、A 片 −0.256…−0.053；原来盒内 A 1.00…1.203、B 1.203…1.406。
# 尾巴原回折路径不变，只是「离开底面往上拐」那一弯整体下移 ΔZ = 1.256（两片相同），竖直段多 ΔZ → 尾巴加长 ΔZ，取 1.30（余 0.044）。
Z_FLOOR_IN, Z_SHELL_OUT, T_FPC = 1.00, 0.15, 0.203
DZ_TAIL = round((Z_FLOOR_IN + T_FPC / 2) - (Z_SHELL_OUT - T_FPC - T_FPC / 2), 4)       # A：1.1015 − (−0.1545) = 1.256；B 同
TAIL_EXT = 1.30
assert TAIL_EXT >= DZ_TAIL
BEND_X = 39.96                                   # 板 x 39.96 = 盒 Y 18.04（座子北沿）：尾巴从这里离开壳外平面往上拐；以北是弯折区，以南平放
X_TAIL_VIA = 40.3                                # 尾部地过孔挪到弯折线以南（孔边 40.05）

# ---------- 几何工具（同 R15） ----------


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
    """线段到矩形 (x0, y0, x1, y1) 的距离（相交为 0）。"""
    x0, y0, x1, y1 = r
    if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in (a, b)):
        return 0.0
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return min(segdist(a, b, c[i], c[(i + 1) % 4]) for i in range(4))


def hairpin(pts, extra, a=0.25):
    """B 面腿 [过孔, 竖直, 45°, 竖直, 腿端过孔] 改成「先反向竖直 → 45° 横跨 → 45° 回头 → 竖直到腿端过孔」的回头弯，
    总长正好加 extra。回头弯高 h：L = 2h + |Δy| + |Δx| − 4a + 2a√2（线性，解析求 h）。"""
    (x1, y1), (ex, ey) = pts[0], pts[-1]
    sg = 1 if ey > y1 else -1
    dxs = 1 if ex > x1 else -1
    assert abs(ex - x1) >= 2 * a + 0.1, (pts, a)
    h = (plen(pts) + extra - (abs(ey - y1) + abs(ex - x1) - 4 * a + 2 * a * math.sqrt(2))) / 2
    assert h >= a + 0.1, ('回头弯太矮，用凸起', h)
    top = y1 - sg * h
    return [(x1, y1), (x1, top + sg * a), (x1 + dxs * a, top), (ex - dxs * a, top), (ex, top + sg * a), (ex, ey)], round(h, 4)


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


# ---------- 带内排道与换道规划（同 R15） ----------


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


# ---------- 针脚真源：D17 采集板（同 R15） ----------
D17_PCB = ROOT / 'hardware/16ch-c08b-round/afe-d20/afe-d20-silk.kicad_pcb'
CONN = {'FPC1': 'V4_FPC1', 'FPC3': 'V4_FPC3'}
AUX = {'V4_BIAS_DRV1': 'BIAS_DRV1', 'V4_RLD_OUT2': 'BIAS_DRV12', 'V4_WCT': 'WCT', 'V4_WCT2': 'WCT2', 'AGND': 'AGND'}


def load_copy(src):
    tmp = Path(tempfile.mkdtemp(prefix='d2-'))
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


D20_8CH_PCB = ROOT / 'hardware/8ch-ads1298/afe-d20-8ch/afe-d20-8ch.kicad_pcb'
D20N_8CH_PCB = ROOT / 'hardware/8ch-ads1298/afe-d20n-8ch/afe-d20n-8ch.kicad_pcb'
D17_ROWS_ALL, D17_SHA = d17_interface()
D17_ROWS = [r for r in D17_ROWS_ALL if r['connector'] == 'FPC1']
for _p8 in (D20_8CH_PCB, D20N_8CH_PCB):
    _b8 = load_copy(_p8)
    _f1 = next(f for f in _b8.GetFootprints() if f.GetReference() == 'V4_FPC1')
    _pmap = {int(p.GetNumber()): p.GetNetname() for p in _f1.Pads() if p.GetNumber().isdigit()}
    for _r in D17_ROWS:
        assert _pmap[_r['pin']] == _r['d17_net'], (_p8.name, _r['pin'], _pmap.get(_r['pin']), _r['d17_net'])
with (HERE / 'd17-interface.csv').open('w', newline='', encoding='utf-8') as fh:
    w_ = csv.DictWriter(fh, fieldnames=list(D17_ROWS[0]), lineterminator='\n'); w_.writeheader(); w_.writerows(D17_ROWS)
pin_net = {'FPC1': {r['pin']: r['strap_net'] for r in D17_ROWS}}
assert sorted(n for n in pin_net['FPC1'].values() if n.startswith('CH')) == sorted(f'CH{c}_{p}' for c in range(1, 9) for p in 'PN')

# ---------- 胶囊底触点与串阻（照抄 R15）：A 片 CH1/CH2 两对 + EB1，B 片 EB2 ----------
AUX_REFS = {'a': ('EB1', 'R33', 'E1N', 'E1P', 'E2N', 'E2P', 'R1', 'R2', 'R3', 'R4'), 'b': ('EB2', 'R34')}


def aux_parts():
    out = {}
    for s, refs in AUX_REFS.items():
        b = load_copy(R15 / f'strap-{s}.kicad_pcb')
        for f in b.GetFootprints():
            ref = f.GetReference()
            if ref not in refs:
                continue
            pads = []
            for p in f.Pads():
                bb = p.GetBoundingBox()
                circle = p.GetShape() == k.PAD_SHAPE_CIRCLE
                pads.append(dict(num=p.GetNumber(), net=p.GetNetname(), x=round(mm(p.GetPosition().x), 4), y=round(mm(p.GetPosition().y), 4),
                                 w=round(mm(bb.GetWidth()), 3), h=round(mm(bb.GetHeight()), 3), circle=circle,
                                 drill=round(mm(p.GetDrillSize().x), 3) if circle else None))
            out[ref] = dict(piece=s, ref=ref, x=round(mm(f.GetPosition().x), 4), y=round(mm(f.GetPosition().y), 4), layer=f.GetLayerName(),
                            value=f.GetValue(), pads=pads)
    assert set(out) == {r for v in AUX_REFS.values() for r in v}
    return out


AUXP = aux_parts()


def contact(ref):
    """胶囊底触点中心：照 R15 原位（11-11 Mako：位置不变）。"""
    return AUXP[ref]['x'], AUXP[ref]['y']


# ---------- 胶囊底 D2（11-11 Mako 定：胶囊底扣单独底片，6 个触点改 F 面 Φ6.5 SMD 焊盘焊 Φ6×2.0 镀金铜片） ----------
# 触点中心、串阻值与网照 R15；串阻留 B 面（胶囊里面），但原位（43.6/56.2，Ø1.8 端子旁）挡住 B 片绕 EB2 的走线和 A 片穿胶囊的 B 面带，
# 挪到触点外侧（y 39.5 / 60.5，B 片外形之外）；R33 挪到两列之间 y 58.6；R34 挪到 EB2 左侧。电极侧：串阻 → B 面短线 → 焊盘圆外的过孔
# （过孔铜离 Φ6.5 焊盘 ≥ 0.15，不做盘中孔）→ F 面短线进焊盘 0.3。
R_BIG = PAD_R + 0.15 + W / 2 + HP + 0.02          # 对中心线离 Φ6.5 焊盘中心的最小距离 3.645
EB_PAD_D = 4.5                                    # EB1/EB2（BIAS/REF）焊盘 Φ4.5：盖得住方形 3×3 铜片的对角线 4.24
EB_DISC = dict(d=3.0, t=2.0, shape='方形 3×3×2（d 为边长）')   # 11-12：Φ4×2 买不到，购物车定方形 3×3×2
CAP_PAD_D = {'E1N': PAD_D, 'E1P': PAD_D, 'E2N': PAD_D, 'E2P': PAD_D, 'EB1': EB_PAD_D, 'EB2': EB_PAD_D}
CAP_RES = {   # 参考号: (片, 中心, 尾侧焊盘在 +x 侧 = +1 / −x 侧 = −1)
    'R2': ('a', (50.5, 39.5), +1), 'R1': ('a', (50.5, 60.5), +1),
    'R4': ('a', (65.5, 39.5), -1), 'R3': ('a', (65.5, 60.5), -1),
    'R33': ('a', (59.4, 58.6), -1), 'R34': ('a', (45.5, 50.0), -1),
}


def cap_parts():
    out = []
    for ref in ('E1N', 'E1P', 'E2N', 'E2P', 'EB1', 'EB2'):
        d = AUXP[ref]
        (q,) = d['pads']
        net = 'BIAS_DRV1_EB2_E' if ref == 'EB2' else q['net']
        out.append(dict(kind='part', piece='a', ref=ref, x=d['x'], y=d['y'], layer='F.Cu', value='贴肤焊盘',
                        pads=[pad(q['num'], net, d['x'], d['y'], CAP_PAD_D[ref], CAP_PAD_D[ref], circle=True)]))
    for ref, (piece, (cx, cy), side) in CAP_RES.items():
        d = AUXP[ref]
        assert d['layer'] == 'B.Cu', ref
        big = d['value'] == '200k'
        hp_, sz = (0.825, (0.95, 1.05)) if big else (0.51, RPAD)
        pads = []
        for q in d['pads']:
            is_elec = q['net'].endswith('_E')
            dx = side * hp_ if not is_elec else -side * hp_
            net = ('BIAS_DRV1_EB2_E' if is_elec else 'BIAS_DRV1') if ref == 'R34' else q['net']
            pads.append(pad(q['num'], net, cx + dx, cy, *sz))
        out.append(dict(kind='part', piece='a', ref=ref, x=cx, y=cy, layer='B.Cu', value=d['value'], pads=pads))
    return out


def cap_pad(ref, which):
    f = next(f for f in CAP if f['ref'] == ref)
    (q,) = [q for q in f['pads'] if q['net'].endswith('_E') == (which == 'elec')]
    return q['x'], q['y']


def cap_elec(pc, ref, cref):
    """0402 串阻电极侧 → B 面竖直短线 → 焊盘圆外过孔 → F 面竖直短线伸进 Φ6.5 焊盘 0.3（离触点中心远的一侧打孔）。"""
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


# ---------- 一片板的容器 ----------


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


def pad(num, net, x, y, w, h, circle=False, drill=None):
    return dict(num=num, net=net, x=round(x, 4), y=round(y, 4), w=w, h=h, circle=circle, drill=drill)


CAP = cap_parts()


def place_aux(pc):
    for d in CAP:
        if d['piece'] == pc.name:
            pc.fps.append(d)


def refl(cx, pts):
    """关于岛中心 (cx, 50) 点对称。"""
    return [(round(2 * cx - x, 6), round(2 * YC - y, 6)) for x, y in pts]


def contact_block(pc, ch, cx):
    """一路两触点：F 面 Φ6.5 SMD 焊盘（无孔）、B 面 Φ7.2 PI 补强、F 面 0402 串阻、电极侧 F 面短线。
    串阻电极侧焊盘 → 竖直短线（沿焊盘长轴）→ 伸进 Φ6.5 焊盘 0.3，不打孔。N 侧和 P 侧关于 (cx, 50) 点对称，电极侧两段等长。
    返回两颗串阻尾侧焊盘中心 (N, P)。"""
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
    y_in = PN_Y[0] + math.sqrt(PAD_R ** 2 - (ex - cx) ** 2) - E_IN     # 焊盘圆在 x = ex 处的下沿再往里 0.3
    nf = [(ex, ey), (ex, round(y_in, 4))]
    pc.tr(f'CH{ch}_N_E', 'F', nf, 'elec')
    pc.tr(f'CH{ch}_P_E', 'F', refl(cx, nf), 'elec')
    return (rn[0] + 0.51, rn[1]), (rp[0] - 0.51, rp[1])


def island_obst(cx):
    """F 面带换道要让开的东西：四个串阻焊盘（矩形，对中心离焊盘边 ≥ 0.395）和两个腿端过孔。"""
    out = []
    for sx, y in ((-1, YC - RES[1]), (1, YC + RES[1])):
        for dx in (-0.51, 0.51):
            x = cx + sx * RES[0] + dx
            out.append(((x - RPAD[0] / 2, y - RPAD[1] / 2, x + RPAD[0] / 2, y + RPAD[1] / 2), 0.15 + HP + W / 2 + 0.02))
    out += [((cx - RES[0] + 0.51, YC - RES[1] - LV), R_VIA), ((cx + RES[0] - 0.51, YC + RES[1] + LV), R_VIA)]
    return out


def leg(pc, net, via, pad_xy, up):
    """B 面腿：过孔 → 竖直 → 45° → 竖直到腿端过孔 → F 面竖直短线进串阻尾侧焊盘（沿焊盘长轴）。
    腿端过孔放在串阻外侧（N 在串阻上方、P 在下方，离焊盘铜 0.17），点对称；带在两颗串阻之间走，不挡过孔。"""
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
    """对中心线水平到 (xv-0.2, yc) 结束；上面那根 45° 进 (xv, yc-0.35)，下面那根进 (xv+0.65, yc+0.35)。"""
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
    xc = tip + FINGER['setback'] + FINGER['l'] / 2
    pads = [(str(p), pin_net[con][p], xc, ypin(p)) for p in range(1, FINGER['n'] + 1)]
    ys = [ypin(1), ypin(FINGER['n'])]
    gang = (tip, tip + FINGER['setback'] + FINGER['l'] - 0.3, min(ys) - FINGER['w'] / 2 - 0.15, max(ys) + FINGER['w'] / 2 + 0.15)
    pc.fps.append(dict(ref=ref, kind='finger', face=face, pads=pads, gang=gang))
    pc.gang = gang
    return xc, tip + FINGER['setback'] + FINGER['l']


def conv(pc, con, ypin, xc, xe, ch):
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
    pc.stiff.append(dict(rect=(x0, x1, y0, y1), side=side, name=name, thickness=STIFF_T_TAIL))


def islands_outline(pc, cxs):
    """一排岛：整块 (min−3.6 … max+3.6) × (36.9 … 63.1)，相邻岛之间从下沿开 0.8 宽缝到 y 55.2（缝底半圆）。"""
    cxs = sorted(cxs)
    pc.shapes.append(rect(cxs[0] - ISL_HW, cxs[-1] + ISL_HW, ISL_Y0, ISL_Y1))
    for a, b in zip(cxs, cxs[1:]):
        xb = (a + b) / 2
        hw = (b - a) / 2 - ISL_HW
        pc.cut += [rect(xb - hw, xb + hw, SLIT_C, ISL_Y1 + 1.0), circ(xb, SLIT_C, hw, 64)]
        pc.dyn.append((xb - hw - 0.3, xb + hw + 0.3, ISL_Y0 - 0.3, ISL_Y1 + 0.3, f'{pc.name.upper()}岛间{int(xb)}'))


# =====================================================================
# 片 A：→ D17 V4_FPC1。金手指在 F 面，pin1 在小 y（尖端朝 -x）；同 R7/R12。
# =====================================================================
A = Piece('a')
place_aux(A)
TA = round(30.16 - TAIL_EXT, 4)                    # 11-11 胶囊段移到壳外：尾巴加长 TAIL_EXT（金手指整排随尖端前移）
yA = lambda p: 41.75 + (p - 1) * 0.5        # noqa: E731
xcA, xeA = fingers(A, 'TAIL_A', 'FPC1', TA, 'F', yA)
tail_stiff(A, TA, TA + STIFF, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'B', '尾A补强（B面，金手指背面）')
A.dyn.append((round(32.71 - TAIL_EXT, 4), BEND_X, 50 - TAIL_W / 2, 50 + TAIL_W / 2, 'A尾折弯'))
A.gnd_runs = gnd_tail(A, 'FPC1', yA, xcA, xeA, X_TAIL_VIA, {34: (40.6, yA(34))})
A_TAIL_VIAS = [(p, R_VIA) for n, p in A.vias if n == 'AGND']
def hop(pc, ch, xv, yc, layer, top_is_p, n_sign, tag):
    """一对水平走线（沿 +x）在 xv 处换层：到达端同 peel_entry（上 → (xv, yc−0.35)，下 → (xv+0.65, yc+0.35)），
    出发端镜像（上 (xv+0.2, yc−0.15)、下 (xv+0.85, yc+0.15)），两线到达 + 出发各多 0.65，换一次层 P/N 等长。"""
    pc.C[ch] += [(round(xv - 0.2, 6), yc)]
    ne, pe = peel_entry(xv, top_is_p, yc)
    pair_traces(pc, ch, layer, pc.C[ch], n_sign, ne, pe, tag)
    up = [(xv, round(yc - 0.35, 6)), (round(xv + 0.2, 6), round(yc - HP, 6)), (round(xv + 0.85, 6), round(yc - HP, 6))]
    lo = [(round(xv + 0.65, 6), round(yc + 0.35, 6)), (round(xv + 0.85, 6), round(yc + HP, 6))]
    n_st, p_st = (lo, up) if top_is_p else (up, lo)
    pc.via(f'CH{ch}_P', p_st[0]); pc.via(f'CH{ch}_N', n_st[0])
    pc.start[ch] = (n_st, p_st)
    pc.C[ch] = [(round(xv + 0.85, 6), yc)]


# --- BIAS_DRV1（33 脚）：F 出尾 → 过孔 (46.9, 58.6) → B 面沿 y 58.6 到 R33（两列之间）→ 过孔 → F 面竖直上行进 EB1 左侧 ---
yb = yA(33)
XB_V, Y_BIAS = 46.8, 58.6
assert cap_pad('R33', 'tail')[1] == Y_BIAS
A.tr('BIAS_DRV1', 'F', [(xcA, yb), (40.8, yb), (round(40.8 + Y_BIAS - yb, 6), Y_BIAS), (XB_V, Y_BIAS)], 'bias')
A.via('BIAS_DRV1', (XB_V, Y_BIAS))
A.tr('BIAS_DRV1', 'B', [(XB_V, Y_BIAS), cap_pad('R33', 'tail')], 'bias')
_ex, _ey = cap_pad('R33', 'elec')
XE_V = 61.6
_cx, _cy = contact('EB1')
assert math.dist((XE_V, _ey), (_cx, _cy)) >= EB_PAD_D / 2 + VIA[0] / 2 + 0.15
A.tr('BIAS_DRV1_E', 'B', [(_ex, _ey), (XE_V, _ey)], 'bias')
A.via('BIAS_DRV1_E', (XE_V, _ey))
A.tr('BIAS_DRV1_E', 'F', [(XE_V, _ey), (XE_V, _cy + 0.5), (XE_V + 0.5, _cy), (_cx - EB_PAD_D / 2 + E_IN, _cy)], 'bias')
# --- R34（200k，B 面 (45.5, 50.0)）→ 独立限流驱动 EB2（实心 F 面 Φ4.5 SMD 焊盘，零悬空金属、免对焊） ---
_r34_tx, _r34_ty = cap_pad('R34', 'tail')
A.tr('BIAS_DRV1', 'B', [(XB_V, Y_BIAS), (round(_r34_tx + 0.4, 6), Y_BIAS), (_r34_tx, round(Y_BIAS - 0.4, 6)), (_r34_tx, _r34_ty)], 'bias')
_r34_ex, _r34_ey = cap_pad('R34', 'elec')
_eb2_cx, _eb2_cy = contact('EB2')
XEV2 = 47.5
assert math.dist((XEV2, _r34_ey), (_eb2_cx, _eb2_cy)) >= EB_PAD_D / 2 + VIA[0] / 2 + 0.15
A.tr('BIAS_DRV1_EB2_E', 'B', [(_r34_ex, _r34_ey), (XEV2, _r34_ey)], 'bias')
A.via('BIAS_DRV1_EB2_E', (XEV2, _r34_ey))
A.tr('BIAS_DRV1_EB2_E', 'F', [(XEV2, _r34_ey), (_eb2_cx - EB_PAD_D / 2 + E_IN, _eb2_cy)], 'bias')

# --- 胶囊底 CH1：F 出尾 → 过孔换 B（胶囊 F 面在 C1 列被 E1N 焊盘挡住）→ B 面 y 44 过 E1N 背后 → 45° 下到 y 50 →
#     在两列之间 x 57 分叉：P 打孔到 F 竖直下行（跨过 B 面的 CH5–8 带和 BIAS）→ 过孔 → B 面到 R1；N 留 B 面竖直上行到 R2 ---
X1H, X1F = 44.6, 57.0
yc = conv(A, 'FPC1', yA, xcA, xeA, 1)
hop(A, 1, X1H, yc, 'F', True, +1, 'box')
A.C[1] += [(50.6, yc), (50.6 + YC - yc, YC), (X1F - 0.2, YC)]
pair_traces(A, 1, 'B', A.C[1], +1, [(X1F - 0.2, YC + HP), (X1F + 0.45, YC + HP), (X1F + 0.65, YC - 0.05)],
            [(X1F - 0.2, YC - HP), (X1F, YC - 0.35)], 'box')
A.via('CH1_P', (X1F, YC - 0.35))
t1n, t1p = cap_pad('R2', 'tail'), cap_pad('R1', 'tail')
A.legs['CH1_N'] = A.tr('CH1_N', 'B', [(X1F + 0.65, YC - 0.05), (X1F + 0.65, t1n[1] + 0.4), (X1F + 0.25, t1n[1]), t1n], 'leg')
A.legs['CH1_P'] = A.tr('CH1_P', 'F', [(X1F, YC - 0.35), (X1F, t1p[1] + 0.4)], 'leg')
A.via('CH1_P', (X1F, t1p[1] + 0.4))
A.tr('CH1_P', 'B', [(X1F, t1p[1] + 0.4), (X1F - 0.4, t1p[1]), t1p], 'leg-b')
# --- 胶囊底 CH2：F 面 y 46 从 E1N 与 EB2 让位孔之间穿过 C1 列 → 45° 下到 y 50 → x 60.2 分叉：N 打孔到 B 竖直上行到 R4；P 留 F 竖直下行 → 过孔 → B 面到 R3 ---
X2D, X2F = 54.5, 60.2
yc = conv(A, 'FPC1', yA, xcA, xeA, 2)
A.C[2] += [(X2D, yc), (X2D + YC - yc, YC), (X2F - 0.2, YC)]
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

# --- 北支 CH3/CH4：F 面直出到阶梯过孔（P 在 X、N 在 X+0.65）→ B 面成对上行 → 45° 左拐进北支总线 → 各岛 45° 下拐 → 岛中部分叉 ---
NX = {3: 41.2, 4: 42.4}                            # 越靠右的对，在总线里越靠上（上 → 下：CH4、CH3）
NL_ = lanes(NORTH, 2)
NLANE = {4: NL_[0], 3: NL_[1]}
A.lanes['A北支'] = NL_
DN, TURN_A = 0.5, 0.6
north_ys = {}


def north_paths(ch, ys):
    cx = N_ISL[ch]
    yP = yA(next(p for p, n in pin_net['FPC1'].items() if n == f'CH{ch}_P'))
    yN = yA(next(p for p, n in pin_net['FPC1'].items() if n == f'CH{ch}_N'))
    assert abs(yN - yP - 0.5) < 1e-9, ch               # P 在上
    X, L, xd = NX[ch], NLANE[ch], cx + 0.3
    cpair = clean([(X + 0.15, yP - 0.85), (X + 0.15, L + DN), (X + 0.15 - DN, L), (xd + TURN_A, L), (xd, L + TURN_A), (xd, ys)])
    Nc, Pc = offset(cpair, HP), offset(cpair, -HP)     # 上行时 N 在右；左行时 N 在上；下行时 N 在左
    assert math.dist(Pc[0], (X, yP - 0.85)) < 1e-6 and math.dist(Nc[0], (X + 0.3, yP - 0.85)) < 1e-6
    tn, tp = (cx - RES[0] + 0.51, YC - RES[1]), (cx + RES[0] - 0.51, YC + RES[1])
    assert abs(Nc[-1][0] - (cx + 0.15)) < 1e-6 and abs(Pc[-1][0] - (cx + 0.45)) < 1e-6
    # N 掉头：45° 左下 → 水平 → 45° 左上 → 直上进 R_N 尾侧焊盘；P：直下 → 45° → 直下进 R_P 尾侧焊盘
    # 两腿都止于腿端过孔（N 在 R_N 尾侧焊盘下方、P 在 R_P 尾侧焊盘上方，离焊盘中心 LV），再由 F 面短线进 F 面串阻
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
    for _ in range(3):                                  # P 长 = c − ys，N 长 = c' + ys：线性，一步即准
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

# --- 南带 CH5–8：F 出尾 → C1 列左侧换 B（A_LOW 道，EB2 让位孔下沿与 R1/R3 之间）→ C2 列右侧换回 F → 出盒带等分道 → 每岛最上一对升到 y 50 进过孔对 ---
order = [5, 6, 7, 8]
fy = [conv(A, 'FPC1', yA, xcA, xeA, ch) for ch in order]
A.advance(order, fy, A_LOW, 40.2, A_TAIL_VIAS + NORTH_VIAS + [((X1H, YC - 6.35), R_VIA), ((X1H + 0.65, YC - 5.65), R_VIA), ((XB_V, Y_BIAS), R_VIA)])
A.lanes['A盒底'] = A_LOW
XH0, XH2 = 45.5, 69.6                  # CH5–8 两次换层的过孔列：C1 列左侧（F → B）、C2 列右侧（B → F）
for ch, y in zip(order, A_LOW):
    assert A.C[ch][-1][0] <= XH0 - 0.2 + 1e-9, (ch, A.C[ch][-1])
    hop(A, ch, XH0, y, 'F', True, +1, 'band')
for ch, y in zip(order, A_LOW):
    hop(A, ch, XH2, y, 'B', True, +1, 'band')
LA = lambda n: lanes(ABAND, n) if n != 1 else [round(ABAND[0] + PM, 4)]     # noqa: E731  只剩一对时贴上侧（靠近过孔对）
A.advance(order, A_LOW, LA(4), XH2 + 1.05, [(contact('EB1'), R_BIG), (contact('E2P'), R_BIG)])
A.lanes['A出盒带'] = LA(4)
rem, cur = list(order), LA(4)
for ch in order:
    cx = A_ISL[ch]
    n = len(rem)
    tn, tp = contact_block(A, ch, cx)
    ends = A.advance(rem, cur, [YC] + LA(n - 1), cx - 3.25, island_obst(cx))
    xv = round(cx - 0.325, 6)                       # 过孔对以岛中心对称：两条腿等长
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
A.shapes += [
    rect(N_ISL[3] + ISL_HW - 0.1, 39.6, *NORTH),                       # 北支
    rect(TA, 39.6, 50 - TAIL_W / 2, 50 + TAIL_W / 2),                   # 尾
    [(39.5, ISL_Y0), (75.0, ISL_Y0), (75.0, 63.0), (44.25, 63.0), (40.0, 58.75), (39.5, 58.75)],   # 胶囊头部（上沿 36.9，同北支上沿）；下角斜边起点 39.5 → 40.0，弯折线 39.96 处只剩尾宽
    rect(74.9, A_ISL[5] - ISL_HW + 0.1, *ABAND),                        # 出盒带
]
islands_outline(A, A_ISL.values())
A.cut.append(circ(39.5, 41.35, 0.5, 64))      # 北支与尾之间 0.4 缝的缝底圆（同 R11）
# 11-12：原 Φ4.9 让位孔（B 片 EB2 铜片从 A 的孔穿出）换成 EB2A 对焊焊盘，见 cap_parts
A.dyn += [(N_ISL[3] + ISL_HW + 0.6, 38.9, NORTH[0] - 0.3, NORTH[1] + 0.15, 'A北支'),
          (75.5, 86.0, ABAND[0] - 0.3, ABAND[1] + 0.3, 'A带根')]
# 动态区重命名：南岛之间的叫 A桥1–3（DRC 反例与 R15 同名）
A.dyn = [(x0, x1, y0, y1, {94: 'A桥1', 102: 'A桥2', 110: 'A桥3'}.get(round((x0 + x1) / 2), n)) for x0, x1, y0, y1, n in A.dyn]
stitch(A, [(46.0, 40.0), (58.9, 38.0), (73.5, 38.5), (47.0, 61.6), (58.0, 61.6), (73.5, 61.6)])

# =====================================================================
# 分段等长：南岛 B 面腿上加 45° 凸起；北岛已解出分叉高度
# =====================================================================


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
            if e > 1.0 and ch not in (1, 2):                # 凸起放不下（B 岛前三岛分叉下移造成 P 腿短 1.6–4.4 mm）：B 面回头弯；胶囊底 CH1/CH2 照 R15 用凸起
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


match = {'a': tune(A)}

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
    if 'circle' in st:
        return polyset(circ(*st['circle'], 96))
    if 'poly' in st:
        s = polyset(st['poly'])
        for h in st.get('holes', ()):
            s.BooleanSubtract(polyset(rect(*h)))
        s.Simplify()
        return s
    return polyset(rect(*st['rect']))


def poly_rings(s):
    rings = []
    for i in range(s.OutlineCount()):
        for ch in [s.Outline(i)] + [s.Hole(i, j) for j in range(s.HoleCount(i))]:
            rings.append([(ch.CPoint(j).x / 1e6, ch.CPoint(j).y / 1e6) for j in range(ch.PointCount())])
    return rings


def mesh_holes(pc, ol):
    """动态区里的 45° 菱形禁铺孔（同 R15）；避开过孔和带孔触点。"""
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
                out.append(f'(footprint "{fpn}" (layer "F.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1)))) (property "Value" "{val}" (at 0 1.4 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1)))) (attr {attr}) {pads})')
            else:
                fpn = 'R0603' if f['value'] == '200k' else 'R0402'
                sd = f['layer'][0]
                mir = ' (justify mirror)' if sd == 'B' else ''
                out.append(f'(footprint "{fpn}" (layer "{sd}.Cu") (at {f6(x)} {f6(y)}) (property "Reference" "{ref}" (at 0 0 0) (layer "{sd}.Fab") (effects (font (size 0.4 0.4) (thickness 0.06)){mir})) (property "Value" "{f["value"]}" (at 0 0.9 0) (layer "{sd}.Fab") (hide yes) (effects (font (size 0.4 0.4) (thickness 0.06)){mir})) (attr smd) {pads})')
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
        lay = 'User.1' if st['side'] == 'F' else 'User.2'
        for o in poly_rings(stiff_poly(st)):
            out.append('(gr_poly (pts ' + ' '.join(f'(xy {f6(x)} {f6(y)})' for x, y in o) + f') (stroke (width 0.05) (type solid)) (fill none) (layer "{lay}"))')
        if 'rect' in st:
            x0, x1, y0, y1 = st['rect']
            out.append(f'(gr_text "{st["name"]} PI {st["thickness"]}（含胶，假设）" (at {f6((x0 + x1) / 2)} {f6(y0 - 0.5)} 0) (layer "Cmts.User") (effects (font (size 0.4 0.4) (thickness 0.06))))')
        elif 'poly' in st:
            xs_p = [p[0] for p in st['poly']]
            ys_p = [p[1] for p in st['poly']]
            out.append(f'(gr_text "{st["name"]} PI {st["thickness"]}（含胶，假设）" (at {f6((min(xs_p) + max(xs_p)) / 2)} {f6(min(ys_p) - 0.6)} 0) (layer "Cmts.User") (effects (font (size 0.4 0.4) (thickness 0.06))))')
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
    txt = f'D2-8CH→D20-8CH V4_FPC1 pin1 金手指在{f["face"]}面'
    out.append(f'(gr_text "{txt}" (at {f6(p1[2] - 1.2)} {f6(p1[3] + (-1.2 if pc.name == "a" else 1.2))} 0) (layer "Dwgs.User") (effects (font (size 0.6 0.6) (thickness 0.08)) (justify left)))')
    out.append(')')
    return '\n'.join(out), ol


DRU = '''(version 1)
(rule "D2 线宽" (constraint track_width (min 0.15mm)))
(rule "D2 铜间距" (constraint clearance (min 0.15mm)))
(rule "D2 铜到板边 12mil" (constraint edge_clearance (min 0.305mm)))
(rule "D2 金手指到尾尖（同 R7/R12，金手指离尖端 0.2）" (condition "A.Type == 'Pad' && A.memberOfFootprint('TAIL_*')") (constraint edge_clearance (min 0.15mm)))
(rule "D2 过孔外径" (condition "A.Type == 'Via'") (constraint via_diameter (min 0.5mm)))
# 不同网的两条走线（同一差分对 CHn_P/CHn_N 除外）中心距 ≥ 0.47 mm（> 18 mil）：线宽 0.15 时净距 ≥ 0.32
(rule "D2 不同网走线中心距0.47" (condition "A.Type == 'Track' && B.Type == 'Track' && A.Net != B.Net && !A.isCoupledDiffPair()")
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
       'd20_8ch_sources': dict(round=dict(file=str(D20_8CH_PCB.relative_to(ROOT)), sha256=hashlib.sha256(D20_8CH_PCB.read_bytes()).hexdigest()),
                               notch=dict(file=str(D20N_8CH_PCB.relative_to(ROOT)), sha256=hashlib.sha256(D20N_8CH_PCB.read_bytes()).hexdigest())),
       'tpu_layer_source': dict(file=str(TPU.relative_to(ROOT)), sha256=hashlib.sha256(TPU.read_bytes()).hexdigest(), consts=TC),
       'd2_8ch': dict(single_piece=True, channels=8, pad_d=PAD_D, stiffener_d=STIFF_D, stiffener_t=STIFF_T_ISL, pair_y=PN_Y,
                      island_y=[ISL_Y0, ISL_Y1], island_half_width=ISL_HW,
                      slit=dict(width=round(8.0 - 2 * ISL_HW, 3), from_bottom_to_y=round(SLIT_C - (4.0 - ISL_HW), 3)),
                      north_islands=N_ISL, south_islands=A_ISL, resistor_offset=RES, resistor_face='F', leg_via_offset=LV),
       'bands': dict(ABAND=ABAND, NORTH=NORTH),
       'north_split_y': north_ys}
geo['capsule_pads'] = dict(
    note='胶囊底 6 个触点（8ch 单片版）：6 个贴肤焊盘全部是本片 F 面（皮肤侧）无孔实心 SMD 圆焊盘，开窗 = 焊盘。'
         'CH1/CH2 焊盘 Φ6.5 焊 Φ6×2.0；EB1/EB2 焊盘 Φ4.5 焊方形 3×3×2。'
         'EB1 经 R33（200k）接 BIAS_DRV1，EB2 经 R34（200k，复用原 B.Cu (45.5, 50.0) 槽位）独立接 BIAS_DRV1：无悬空贴肤金属、无需两片灌锡对焊。',
    disc_ch=dict(d=TC['DISC_D'], t=2.0), disc_eb=EB_DISC, mask_opening='= 焊盘（每个焊盘见 pads[].d）',
    eb2_mode=dict(ref='EB2', board=list(contact('EB2')), pad_d=EB_PAD_D, drill=None, series_resistor='R34 (200k to BIAS_DRV1)',
                  assembly='单片直接回流焊 6 颗铜片，无 A/B 对焊工序'),
    stack_note=dict(eb2_disc_base_higher_mm=0.0, reason='单片软板，6 个贴肤焊盘都在同一 F 面，铜片底面天然同高',
                    tip_from_a_f_face_mm=dict(CH=2.0, EB1=2.0, EB2=2.0)),
    pads=[dict(ref=f['ref'], piece='a', net=f['pads'][0]['net'], d=f['pads'][0]['w'],
               disc='方形 3×3×2' if f['ref'].startswith('EB') else 'Φ6×2.0', layer='F.Cu', smd=not f['pads'][0]['drill'],
               board=[f['x'], f['y']], box=[round(f['y'] - 50.0, 4), round(58.0 - f['x'], 4)])
          for f in CAP if f['ref'].startswith('E')],
    resistors=[dict(ref=f['ref'], piece='a', value=f['value'], layer='B.Cu', board=[f['x'], f['y']],
                    r15_board=[AUXP[f['ref']]['x'], AUXP[f['ref']]['y']],
                    moved_mm=round(math.dist((f['x'], f['y']), (AUXP[f['ref']]['x'], AUXP[f['ref']]['y'])), 4))
               for f in CAP if f['ref'].startswith('R')])
R_IN = 0.5
Y_ENTRY = round(58 - BEND_X, 4)
YV_B = round(Y_ENTRY + R_IN + T_FPC / 2, 4)
YV_A = round(YV_B + T_FPC, 4)
TAIL_HW = TAIL_W / 2
geo['tray_tail_slot'] = dict(
    note='8ch 单片只有一条 34P 尾（TAIL_A → V4_FPC1），完全兼容现有 R13 底壳穿壳缝（比双片少一层 0.203 尾巴厚度）。',
    box=dict(x0=round(-TAIL_HW - 0.2, 3), x1=round(TAIL_HW + 0.2, 3), y0=round(Y_ENTRY - 0.05, 3), y1=round(YV_A + T_FPC / 2 + 0.05, 3)),
    z_through=[Z_SHELL_OUT, Z_FLOOR_IN], north_pocket_y_max_needed=round(YV_A + T_FPC / 2 + 0.05, 3),
    tail_vertical_centerline_y=dict(a=YV_A), bend_inner_r_min=R_IN,
    tail_extension_mm=TAIL_EXT, dz_mm=DZ_TAIL,
    board_x_of_bend_start=round(58 - Y_ENTRY, 3))
_BODY = {'200k': (1.6, 0.8), '100k': (1.0, 0.5)}
# 现成 16ch 外扣底盖 cap_d2 顶面在 Z = -0.256、底壳 tray_d2 外底在 Z = +0.150（夹层总高 0.406 mm）。
# 单片 D2-8CH 板厚 0.203 mm，在胶囊段背面（User.2）贴一块 0.20 mm PI 补强垫片（6 个矩形窗让开 B 面 R1–R4/R33/R34）：
# 垫片顶住底壳 Z = +0.150，把 FPC 背面锁在 Z <= -0.050（标称贴底盖时 -0.053），使 R1–R4(0.35)/R33(0.45)/R34(0.45) 顶面
# 位于 +0.300/+0.400/+0.400（标称 +0.297/+0.397/+0.397），全部低于现成 tray_d2 浅槽顶 0.347/0.447/0.650，零改模复用现成外壳。
CAP_STIFF_POLY = [(41.5, 37.3), (74.5, 37.3), (74.5, 62.6), (44.45, 62.6), (41.5, 59.65)]
CAP_STIFF_HOLES = []
_TRAY_D2_POCKET_Z = {'R1': 0.347, 'R2': 0.347, 'R3': 0.347, 'R4': 0.347, 'R33': 0.447, 'R34': 0.650}
_pk = []
for f in CAP:
    if not f['ref'].startswith('R'):
        continue
    xs = [q['x'] - q['w'] / 2 for q in f['pads']] + [q['x'] + q['w'] / 2 for q in f['pads']]
    ys = [q['y'] - q['h'] / 2 for q in f['pads']] + [q['y'] + q['h'] / 2 for q in f['pads']]
    bl, bw = _BODY[f['value']]
    x0, x1 = round(min(xs + [f['x'] - bl / 2]) - 0.3, 3), round(max(xs + [f['x'] + bl / 2]) + 0.3, 3)
    y0, y1 = round(min(ys + [f['y'] - bw / 2]) - 0.3, 3), round(max(ys + [f['y'] + bw / 2]) + 0.3, 3)
    CAP_STIFF_HOLES.append((x0, x1, y0, y1))
    h = 0.45 if f['value'] == '200k' else 0.35
    base_nom = round(Z_SHELL_OUT - 2 * T_FPC + T_FPC, 4)        # -0.053
    base_pressed = round(Z_SHELL_OUT - STIFF_T_ISL, 4)          # -0.050（0.20 mm PI 垫片顶住 Z=0.150 时的最严极限）
    tray_z = _TRAY_D2_POCKET_Z[f['ref']]
    _pk.append(dict(ref=f['ref'], piece='a', value=f['value'], board=[x0, y0, x1, y1],
                    box=dict(x0=round(y0 - 50, 3), x1=round(y1 - 50, 3), y0=round(58 - x1, 3), y1=round(58 - x0, 3)),
                    part_top_z_nominal=round(base_nom + h, 3),
                    part_top_z=round(base_pressed + h, 3),
                    existing_tray_d2_pocket_z=tray_z,
                    clearance_to_tray_d2_mm=round(tray_z - (base_pressed + h), 3),
                    pocket_z=[Z_SHELL_OUT, tray_z]))
A.stiff.append(dict(poly=CAP_STIFF_POLY, holes=CAP_STIFF_HOLES, side='B',
                    name='胶囊背面垫片补强（6窗避让B面串阻，垫平0.406夹层）', thickness=STIFF_T_ISL))
geo['capsule_res_pockets'] = dict(
    note='胶囊段背面贴 0.20 mm PI 垫片补强（6 窗让开 R1–R4/R33/R34）顶住底壳外底 Z=0.150，把单片 FPC 背面锁在 Z<=-0.050（标称 -0.053），'
         '使 6 颗背面串阻顶面（0.300/0.400）全部低于现成 16ch tray_d2 浅槽顶（0.347/0.447/0.650），最小净余量 0.047 mm，零改模直接复用现成外壳。',
    capsule_spacer_pi_mm=STIFF_T_ISL, fpc_back_z_nominal=-0.053, fpc_back_z_pressed_max=-0.050, rects=_pk)

STEM = 'strap-d2-8ch'
txt, ol = emit(A)
path = HERE / f'{STEM}.kicad_pcb'
path.write_text(txt, encoding='utf-8')
b = k.LoadBoard(str(path))
k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(path), b)
proj = project()
proj['meta']['filename'] = f'{STEM}.kicad_pro'
(HERE / f'{STEM}.kicad_pro').write_text(json.dumps(proj, indent=2, ensure_ascii=False))
(HERE / f'{STEM}.kicad_dru').write_text(DRU, encoding='utf-8')
fing = next(f for f in A.fps if f['kind'] == 'finger')
geo['a'] = dict(outline=[[round(x, 4), round(y, 4)] for x, y in ol], holes=A.holes,
                dynamic_zones=[dict(name=n, x=[x0, x1], y=[y0, y1]) for x0, x1, y0, y1, n in A.dyn],
                stiffeners=[dict(name=st['name'], side=st['side'], thickness_mm=st['thickness'], material='PI+胶（假设）',
                                 **({'circle': st['circle']} if 'circle' in st else
                                    ({'poly': st['poly'], 'holes': st['holes']} if 'poly' in st else {'rect': st['rect']})))
                            for st in A.stiff],
                gang_opening=getattr(A, 'gang', None), mesh=MESH, lanes=A.lanes,
                tail=dict(tip_x=TA, width=TAIL_W, finger_face=fing['face'],
                          pin1_y=next(p[3] for p in fing['pads'] if p[0] == '1'),
                          pin34_y=next(p[3] for p in fing['pads'] if p[0] == '34'),
                          finger=FINGER, stiffener_len=STIFF),
                traces=[dict(net=n, layer=LAYER[l], pts=[[round(x, 5), round(y, 5)] for x, y in p], tag=t) for n, l, p, t in A.traces],
                vias=[dict(net=n, at=list(p)) for n, p in A.vias])
(HERE / 'geometry.json').write_text(json.dumps(geo, ensure_ascii=False, indent=1))
(HERE / 'match.json').write_text(json.dumps(match, ensure_ascii=False, indent=1))
for prl in HERE.glob('*.kicad_prl'):
    prl.unlink()
worst = max(abs(r[k_]) for side in match.values() for r in side for k_ in ('tail_diff_mm', 'elec_diff_mm'))
print(f'D2-8CH 已生成：{len(A.traces)} 线 {len(A.vias)} 孔；分段 P/N 最大差 {worst:.4f} mm（{worst / 0.0254:.2f} mil）；北岛分叉 {north_ys}')
