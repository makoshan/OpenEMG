"""ADS1292 载板 建板：design.json → 未布线板。KiCad 自带 Python 运行。
板框逐段同 C08A，四孔同 C08A；XIAO 焊 P44e，悬在板上，USB 朝东，20P 排线接 J2；6 个触点照 C08B 盒底，位置在 zones.py。
贴肤规矩（第二版独立复核 P0）：底层只留电极和地；电极周围 1.5 mm 内没有别的网；第一颗电阻贴电极放。"""
import json, math, os, sys
from pathlib import Path
import pcbnew as k
P = Path(__file__).resolve().parent; R = P.parents[2]; sys.path.insert(0, str(P))
FP = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
D = json.loads((P.parent / 'schematics/design.json').read_text())['parts']
OUT = P / 'board.kicad_pcb'
mm = lambda x, y: k.VECTOR2I(k.FromMM(100 + x), k.FromMM(100 - y))   # CAD(x 右, y 上) → KiCad，同 R3
EDGE, VIA_D, VIA_H, CLR = 0.3, 0.45, 0.3, 0.15
from zones import ELECTRODES, ER, HOLES, J2_AT, board_edge
# 位号: (x, y, 转角)；P0 = 信号流第一版
PLACE = {
 'U1': (-8.0, 0.5, 270),   # 输入朝北（E1、E2 之间），数字朝南，RLD 朝东，电源朝西
 'R4': (-6.5, 7.25, 270), 'R2': (-7.5, 7.25, 270), 'R8': (-8.5, 7.25, 270), 'R6': (-9.5, 7.25, 270),
 'C4': (-6.2, 5.2, 0), 'C5': (-9.8, 5.2, 0),
 'R1': (-11.9, 7.5, 180), 'D1': (-12.725, 6.0, 270),   # 电极西边横放，孔落在盘外
 'R5': (-12.2, -7.5, 180), 'D4': (-13.025, -9.0, 270),   # 连 E4 孔一起西移 0.2：DIN 东边是 CS 线和 R20，挪不动（11-10 复核嫌 0.483 余量太小）
 'R3': (5.3, 11.2, 180), 'D2': (3.2, 10.4, 270), 'R7': (8.0, -2.9, 90), 'D5': (8.35, -0.7, 0),   # R7 在 E5 北边、J1 投影外；D5 紧贴 R7 北端出线口（11-12 Mako 取消中区禁布后直穿）
 'R27': (-2.9, 0.75, 180), 'R15': (-1.45, 0.76, 270), 'C3': (-0.45, 0.79, 270), 'R13': (-0.95, 2.45, 0), 'D3': (-0.25, -1.0, 180),
 'C9': (-2.6, -0.7, 0), 'R21': (-2.41, -2.5, 270), 'R22': (-3.37, -2.5, 270),
 'C6': (-13.2, 2.25, 180), 'C7': (-12.9, 3.5, 180), 'C8': (-13.2, 1.25, 180), 'C10': (-13.2, .25, 180), 'C11': (-13.2, -.75, 180),   # 去耦贴着 U1 脚，和脚同行
 'TP1': (-2.1, 7.0, 0), 'R26': (-0.49, 13.2, 0),
 'C12': (-5.36, -3.22, 90), 'C13': (-4.34, -4.18, 270), 'L1': (-1.1125, -4.7, 180),
 'R20': (-10.7, -4.2, 180), 'R23': (-4.6, -7.6, 0), 'R18': (-6.1, -8.7, 270), 'R19': (-5.9, -11.9, 180),
 'U3': (1.4, 15.4, 180), 'C14': (4.45, 15.4, 0), 'C15': (-1.66, 14.45, 180),
 'Q1': (-9.2, -12.4, 0), 'R31': (-6.0, -10.868, 180), 'R25': (-12.3, -11.45, 180),
 'TP2': (-1.1, -8.6, 0), 'TP3': (-3.0, -10.5, 0), 'TP8': (-5.6, -13.8, 0),
 'R14': (3.55, 7.5, 180), 'R16': (3.55, -7.5, 180), 'C16': (2.4, -10.1, 180), 'R32': (18.75, -9.9, 270),   # 两个辅点的 620k 在辅点东边（x 3.55：换层孔 1.85 不压 R14.2/R16.2 焊盘）；R32 在排线区外
}
BOT = ELECTRODES
FID = {'FID1': (-17.0, 13.0, 0), 'FID2': (17.0, 13.0, 0), 'FID3': (-17.0, -13.0, 0)}   # 末位 1 = 底面
LIB_UNUSED = {'R0402': ('Resistor_SMD', 'R_0402_1005Metric'), 'R0603': ('Resistor_SMD', 'R_0603_1608Metric'), 'C0402': ('Capacitor_SMD', 'C_0402_1005Metric'),
       'C0603': ('Capacitor_SMD', 'C_0603_1608Metric'), 'L0603': ('Inductor_SMD', 'L_0603_1608Metric'), 'SOT-23-5': ('Package_TO_SOT_SMD', 'SOT-23-5'),
       'SOT-23': ('Package_TO_SOT_SMD', 'SOT-23'), 'TP_1.0': ('TestPoint', 'TestPoint_Pad_D1.0mm'), 'Package_QFP:TQFP-32_5x5mm_P0.5mm': ('Package_QFP', 'TQFP-32_5x5mm_P0.5mm')}

def load(fp):
    lib, name = fp.split(':')
    d = {'Package_SON': P / 'libs/Package_SON.pretty', 'p44': P / 'libs/p44.pretty', 'ads': P / 'libs/ads.pretty'}.get(lib, FP / f'{lib}.pretty')
    f = k.FootprintLoad(str(d), name); f.SetFPID(k.LIB_ID(lib, name)); return f

b = k.BOARD(); b.SetCopperLayerCount(4)
nets = {}
def net(n):
    if n not in nets: nets[n] = k.NETINFO_ITEM(b, n); b.Add(nets[n])
    return nets[n]
def edge(pts):
    for a, c in zip(pts, pts[1:]):
        s = k.PCB_SHAPE(b); s.SetShape(k.SHAPE_T_SEGMENT); s.SetLayer(k.Edge_Cuts); s.SetWidth(k.FromMM(0.1)); s.SetStart(mm(*a)); s.SetEnd(mm(*c)); b.Add(s)
def arc(c, st, en, mid):
    s = k.PCB_SHAPE(b); s.SetShape(k.SHAPE_T_ARC); s.SetLayer(k.Edge_Cuts); s.SetWidth(k.FromMM(0.1)); s.SetArcGeometry(mm(*st), mm(*mid), mm(*en)); b.Add(s)
board_edge(edge, lambda st, en, mid: arc(None, st, en, mid))   # 外包络同 C08A，见 zones.py

def assign(f, ref):
    want = {key.split(':')[0]: n for key, n in D[ref]['pins'].items()}
    for p in f.Pads():
        n = want.get(p.GetNumber())
        if n and n != 'NC': p.SetNet(net(n))
for ref, p in D.items():
    f = load(p['fp']); f.SetReference(ref); f.SetValue(p['value']); b.Add(f)
    if ref[0] == 'H':
        f.SetPosition(mm(*HOLES[int(ref[1]) - 1])); continue
    if ref in FID:
        x, y, back = FID[ref]
        if back: f.Flip(f.GetPosition(), k.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetPosition(mm(x, y)); continue
    if ref == 'J2':
        f.SetPosition(mm(*J2_AT))
    elif ref in BOT:
        f.Flip(f.GetPosition(), k.FLIP_DIRECTION_LEFT_RIGHT); f.SetPosition(mm(*BOT[ref]))
    else:
        x, y, a = PLACE[ref]; f.SetPosition(mm(x, y)); f.SetOrientationDegrees(a)
    assign(f, ref)
    f.Value().SetVisible(False)
    f.Reference().SetTextSize(k.VECTOR2I(k.FromMM(.5), k.FromMM(.5))); f.Reference().SetTextThickness(k.FromMM(.08))
# 接口门：J2 第 21−n 脚和 P44e J1 第 n 脚同 x，开口朝南（固定脚在南），排线才对得上
pd = {p.GetNumber(): p.GetPosition() for p in b.FindFootprintByReference('J2').Pads()}
assert abs(k.ToMM(pd['20'].x) - 107.25) < .01 and abs(k.ToMM(pd['1'].x) - 116.75) < .01 and pd['21'].y > pd['1'].y, 'J2 脚序或开口错'

# GND 扇出：贴片盘外就近打 0.45/0.3 孔，1.9 不会自己下到平面
gnd = net('GND'); allp = [(p, f) for f in b.GetFootprints() for p in f.Pads()]
vias = []
def clear(px, py):
    if not (-20.9 < px < 20.9 and -17.6 < py < 17.6): return False
    if px > 15 and abs(py) < 5.1: return False
    if abs(px + 9) < 1.9 and abs(abs(py) - 14.8) < 1.0: return False   # 托架支脚区：R4 的专用无件区
    for e, (ex, ey) in ELECTRODES.items():   # 地孔不进电极盘，离盘边留 0.5
        if math.hypot(px - ex, py - ey) < ER[e] + VIA_D / 2 + .5: return False
    for hx, hy in HOLES:
        if math.hypot(px - hx, py - hy) < 1.5: return False
    for p, f in allp:
        c = p.GetPosition(); cx, cy = k.ToMM(c.x) - 100, 100 - k.ToMM(c.y); bb = p.GetBoundingBox()
        hw, hh = k.ToMM(bb.GetWidth()) / 2, k.ToMM(bb.GetHeight()) / 2
        if abs(px - cx) < hw + VIA_D / 2 + CLR and abs(py - cy) < hh + VIA_D / 2 + CLR: return False
    return all(math.hypot(px - vx, py - vy) >= VIA_D + CLR for vx, vy in vias)
fan = 0
cad = lambda p: (k.ToMM(p.GetPosition().x) - 100, 100 - k.ToMM(p.GetPosition().y))
def track(n, layer, pts, w=.2):
    for a_, c_ in zip(pts, pts[1:]):
        t = k.PCB_TRACK(b); t.SetStart(mm(*a_)); t.SetEnd(mm(*c_)); t.SetWidth(k.FromMM(w)); t.SetLayer(layer); t.SetNet(net(n)); t.SetLocked(True); b.Add(t)
def via(n, x, y):
    v = k.PCB_VIA(b); v.SetPosition(mm(x, y)); v.SetDrill(k.FromMM(VIA_H)); v.SetWidth(k.FromMM(VIA_D)); v.SetNet(net(n)); v.SetLocked(True); b.Add(v); vias.append((x, y))
F, B = k.F_Cu, k.B_Cu
pad = lambda r, n: cad({q.GetNumber(): q for q in b.FindFootprintByReference(r).Pads()}[n])
# 电极：盘 → 底层短桩 → 孔 → 顶层第一颗电阻。这段铜没有限流，所以写死、最短
I2 = k.In2_Cu
# 大点：盘边直出 0.4 到孔，孔落在盘外，翻顶层进第一颗电阻；辅点同样直出
track('E1_CH1P', B, [(-9.98, 7.5), (-10.4, 7.5)]); via('E1_CH1P', -10.4, 7.5); track('E1_CH1P', F, [(-10.4, 7.5), pad('R1', '1')])
track('E4_CH2P', B, [(-9.98, -7.5), (-10.7, -7.5)]); via('E4_CH2P', -10.7, -7.5); track('E4_CH2P', F, [(-10.7, -7.5), pad('R5', '1')])   # 孔离 DIN 竖线约 0.68
track('E2_CH1N', B, [(6.9, 7.6), (6.9, 10.1)]); via('E2_CH1N', 6.9, 10.1); x3, y3 = pad('R3', '1'); track('E2_CH1N', F, [(6.9, 10.1), (6.9, y3), (x3, y3)])
track('E5_CH2N', B, [(8, -5.52), (8, -4.9)]); via('E5_CH2N', 8, -4.9); track('E5_CH2N', F, [(8, -4.9), pad('R7', '1')])   # J1 投影下只走线和孔
track('E3_RLD', B, [(1.48, 7.5), (1.85, 7.5)], .15); via('E3_RLD', 1.85, 7.5); track('E3_RLD', F, [(1.85, 7.5), pad('R14', '2')], .15)
track('E6_RLD', B, [(1.48, -7.5), (1.85, -7.5)], .15); via('E6_RLD', 1.85, -7.5); track('E6_RLD', F, [(1.85, -7.5), pad('R16', '2')], .15)
# 高阻线（第一颗电阻之后）写死：走内层最短路，夹在 In1 和底层地之间。两路 N 线从 E2 平行到 U1，P 线就近
# E1 压在输入电阻组下面：三根 N 线的孔排在 y 11.25，离 E1 盘边 1.5 以上（11-10 看图：原来贴着隔离圈，汗液进腔会让两路串），顶层竖线进电阻。N1P 全走顶层，从孔北边 y 12.0 绕进来
VY = 11.25
x, y = pad('R3', '2'); track('N1N', F, [(x, y), (2.7, y)], .15); track('N1N', F, [(pad('D2', '1')[0], y), pad('D2', '1')], .15); via('N1N', 2.7, y)
track('N1N', I2, [(2.7, y), (2.2, y - .5), (-5.95, y - .5), (-6.5, VY)], .15); via('N1N', -6.5, VY); track('N1N', F, [(-6.5, VY), pad('R4', '1')], .15)
x, y = pad('R7', '2'); xd, yd = pad('D5', '1'); track('N2N', F, [(x, y), (xd, yd), (xd, -.2), (7.2, .6), (2.2, .6)], .15); via('N2N', 2.2, .6)
track('N2N', I2, [(2.2, .6), (-3.5, 6.3), (-3.5, 8.3), (-5.3, 10.1), (-7.8, 10.1), (-8.5, 10.8), (-8.5, VY)], .15); via('N2N', -8.5, VY); track('N2N', F, [(-8.5, VY), pad('R8', '1')], .15)
x, y = pad('R1', '2'); x2, y2 = pad('R2', '1'); track('N1P', F, [(x, y), (x, 11.55), (x + .45, 12.0), (x2 - .45, 12.0), (x2, 11.55), (x2, y2)], .15); track('N1P', F, [(x, y), pad('D1', '1')], .15)
x, y = pad('R5', '2'); track('N2P', F, [(x, y), (x, -3.6)], .15); track('N2P', F, [(x, y), pad('D4', '1')], .15); via('N2P', x, -3.6)
T = 11.945   # 等长对齐：N2N 取消中区禁布后直穿（28.04 mm），N2P 去掉北端高耸 U 形绕线与接头短段（28.03 mm），两根对地电容对齐（11-12 Mako 定）
xn = x + .2   # 内层竖段比孔东错 0.2：R5 西移后竖线会贴上 D1 的地孔
track('N2P', I2, [(x, -3.6), (xn, -3.4), (xn, T), (xn + .3, T + .3), (xn + .63, T + .3), (xn + 1.625, VY), (-9.5, VY)], .15); via('N2P', -9.5, VY); track('N2P', F, [(-9.5, VY), pad('R6', '1')], .15)
# D1、D4 的地孔放西边，躲开 N2P 内层竖线
for d in ('D1', 'D4'): x, y = pad(d, '2'); track('GND', F, [(x, y), (x - .725, y)]); via('GND', x - .725, y); fan += 1
# 地：U3 地脚外侧被 3V3 挡住，从肚子下打孔；U1 的地也从封装肚子下打孔，外面留给去耦和信号
track('GND', F, [pad('U3', '2'), (1.2, 15.4)]); via('GND', 1.2, 15.4); fan += 1
for n, vx, vy in (('10', -9.6, 1.75), ('13', -9.6, .25)): track('GND', F, [pad('U1', n), (vx, vy)]); via('GND', vx, vy); fan += 1
x, y = pad('U1', '24'); track('GND', F, [(x, y), (x, -1.35), (-6.0, -1.1), (-6.0, -.85)]); via('GND', -6.0, -.85); fan += 1
# C9、R21、R22 的地端并成一根下孔（E3 原来在这里，搬走后没再改）
a2, c2 = pad('R22', '2'), pad('C9', '2'); track('GND', F, [a2, (-1.8, a2[1])]); track('GND', F, [c2, (-1.95, c2[1]), (-1.8, c2[1] - .15), (-1.8, a2[1])]); via('GND', -1.8, a2[1]); fan += 1
x, y = pad('C12', '2'); track('GND', F, [(x, y), (-5.0, y), (-4.7, -2.44)]); via('GND', -4.7, -2.44); fan += 1
x, y = pad('C13', '2'); track('GND', F, [(x, y), (-3.7, y)]); via('GND', -3.7, y); fan += 1
# jp(n)：J2 上对应 P44e J1 第 n 脚的焊盘
jp = lambda n: pad('J2', str(21 - n))
# 3V3：J1 1、2 脚从 J2 肚子下并到一个孔进内层。一路西行到 L1，一路在 x=3.9 从 C16 过孔直上 U3（11-12 Mako 定：取消中区禁布后去掉东边绕线）
(xa, ya), (xb, yb) = jp(1), jp(2); xv, yv = (xa + xb) / 2, -12.05; yt3 = -11.8
track('3V3', F, [(xa, ya), (xa, -11.9), (7.4, yv), (xv, yv)], .25); track('3V3', F, [(xb, yb), (xb, -11.9), (7.6, yv), (xv, yv)], .25); via('3V3', xv, yv); track('3V3', I2, [(xv, yv), (7.25, yt3)], .25)
x1, y1 = pad('L1', '1'); x1 = round(x1, 3); via('3V3', x1, -3.7); track('3V3', F, [(x1, -3.7), (x1, y1)], .25)   # 孔在 L1 北边，离 E6 盘边 1.5 以上
track('3V3', I2, [(7.25, yt3), (3.9, yt3), (-1.7, yt3), (-2.2, yt3 + .5), (-2.2, -4.1), (-1.8, -3.7), (x1, -3.7)], .25)   # 内层干线从 E6 西边绕过
xt2, yt2 = pad('TP2', '1'); track('3V3', F, [(x1, y1), (x1, -7.825), (xt2, yt2)], .25)
via('3V3', 3.9, -10.1); track('3V3', F, [(3.9, -10.1), pad('C16', '1')], .25); track('3V3', I2, [(3.9, yt3), (3.9, -10.1), (3.9, 13.8), (3.5, 14.2)], .25); via('3V3', 3.5, 14.2)
x1, y1 = pad('U3', '1'); x3, y3 = pad('U3', '3'); xc, yc = pad('C14', '1')
track('3V3', F, [(3.5, 14.2), (3.5, y1), (3.5, yc), (3.5, 16.05), (3.2, y3), (x3, y3)], .25); track('3V3', F, [(3.5, y1), (x1, y1)], .25); track('3V3', F, [(3.5, yc), (xc, yc)], .25)
x, y = pad('C11', '2'); track('GND', F, [(x, y), (x, y - .1), (x - .45, y - .55)]); via('GND', x - .45, y - .55); fan += 1
x, y = pad('R19', '2'); track('GND', F, [(x, y), (x - .75, y)]); via('GND', x - .75, y); fan += 1
x, y = pad('R18', '2'); track('GND', F, [(x, y), (x + .55, y)]); via('GND', x + .55, y); fan += 1   # 西边是 CS、DIN，东边是 RESET 内层线
# 电源：AVDD 从 U3 到 31/32 脚，内层绕到 12 脚；DVDD 在 U1 肚子下把 14、23 脚连起来
for n in ('31', '32'): track('AVDD', F, [pad('U1', n), (-3.95, pad('U1', n)[1])], .25)
track('AVDD', F, [(-3.95, pad('U1', '31')[1]), (-3.95, 4.0)], .25); via('AVDD', -3.95, 4.0); via('AVDD', -10.1, .75)
track('AVDD', I2, [(-10.1, .75), (-10.1, 2.75), (-9.65, 3.2), (-4.75, 3.2), (-3.95, 4.0)], .25)
x5, y5 = pad('U3', '5'); track('AVDD', F, [(-3.95, 4.0), (-1.0, 4.0), (-1.0, y5)], .25); track('AVDD', F, [pad('C15', '1'), (x5, y5)], .25)
xa, ya = pad('C10', '1'); x, y = pad('U1', '12'); track('AVDD', F, [(x, y), (-12.0, y), (-12.5, ya), (xa, ya)], .25); track('AVDD', F, [(x, y), (-10.1, .75)], .25)
track('AVDD', F, [(pad('C11', '1')[0], ya), pad('C11', '1')], .25); track('AVDD', F, [(-1.0, 7.0), pad('TP1', '1')], .25)
track('DVDD', F, [pad('U1', '14'), (-8.4, -.25), (-6.75, -1.9), pad('U1', '23')], .25)
x, y = pad('U1', '23'); track('DVDD', F, [(x, y), (x, -3.55), (x + .15, -3.7), (-2.1, -3.7), (-1.9, -3.9), (-1.9, -4.7), pad('L1', '2')], .25)
# 参考和 VCAP：沿焊盘长轴出、一折到电容
x, y = pad('U1', '9'); x7, y7 = pad('C7', '1'); track('VREFP', F, [(x, y), pad('C6', '1')]); track('VREFP', F, [(x7, y), (x7, y7)])
track('VCAP1', F, [pad('U1', '11'), pad('C8', '1')])
x, y = pad('U1', '27'); track('VCAP2', F, [(x, y), (-3.9, y), (-3.45, y - .45), pad('C9', '1')])
x, y = pad('U1', '26'); track('ADS_GPIO1', F, [(x, y), (-3.85, y), (-3.3, y - .55), (-2.75, y - .55), (-2.41, -1.64), pad('R21', '1')], .15)
x, y = pad('U1', '25'); track('ADS_GPIO2', F, [(x, y), (-3.76, y), (-3.37, -1.64), pad('R22', '1')], .15)
# RLD：三脚相邻，RLDOUT 上抬、RLDINV 下压，给 R27 让出位置
x, y = pad('U1', '30'); ry = y + .15; x15, y1 = pad('R15', '1'); track('RLDOUT', F, [(x, y), (-3.9, y), (-3.75, ry), (pad('R27', '1')[0], ry), (-1.95, ry), (-1.95 + ry - y1, y1), (x15, y1), pad('C3', '1')], .15)
track('RLDOUT', F, [(pad('R27', '1')[0], ry), pad('R27', '1')], .15); x13, y13 = pad('R13', '1'); track('RLDOUT', F, [(x13, y13), (x13, 1.95), (x15, 1.625), (x15, y1)], .15)
x, y = pad('U1', '28'); track('RLDINV', F, [(x, y), (-3.9, y), (-3.75, y - .15), (-2.1, y - .15), (-1.95, y), (-.95, y), (-.89, y + .06), pad('C3', '2')], .15)
track('ADS_RLDIN', F, [pad('U1', '29'), pad('R27', '2')], .15)
# NRLD 全走顶层，从 R13 南北两头出：取消中区禁布后，北路 45° 斜穿进 R14（E3），南路过 D3 后 45° 斜穿进 R16（E6）
x, y = pad('R13', '2'); x1, y1 = pad('R14', '1'); track('NRLD', F, [(x, y), (x, 3.0), (3.375, 6.5), (x1 - .3, 6.5), (x1, 6.8), (x1, y1)], .15)
xd, yd = pad('D3', '1'); x6, y6 = pad('R16', '1'); track('NRLD', F, [(x, y), (x, y - .55), (xd, y - .55 - (xd - x)), (xd, yd), (xd, -3.225), (3.475, -6.6), (x6 - .3, -6.6), (x6, -6.9), (x6, y6)], .15)
# 数字线写死：西半边沿用 4e8501c76 布通的路，东半边进 J2。J2 北边进 DOUT、SCLK、CS，南边进 PWDN、DIN，START、DRDY 走内层从肚子下上来
x, y = pad('U1', '16'); track('ADS_START', F, [(x, y), (-9.6, y)], .15); via('ADS_START', -9.6, y)
x12, y12 = jp(12); track('ADS_START', I2, [(-9.6, y), (-6.85, y), (-4.6, -3.5), (-4.2, -3.9), (-4.2, -12.95), (-3.8, -13.35), (x12 - 1.3, -13.35), (x12, -12.05)], .15); via('ADS_START', x12, -12.05); track('ADS_START', F, [(x12, -12.05), (x12, y12)], .15)
x, y = pad('U1', '22'); track('ADS_DRDY_N', F, [(x, y), (x, -3.518), (x + 2.232, -5.75), (-2.9, -5.75)], .15); via('ADS_DRDY_N', -2.9, -5.75)
x4, y4 = jp(4); track('ADS_DRDY_N', I2, [(-2.9, -5.75), (-2.9, -12.0), (-2.4, -12.5), (x4 - .45, -12.5), (x4, -12.05)], .15); via('ADS_DRDY_N', x4, -12.05); track('ADS_DRDY_N', F, [(x4, -12.05), (x4, y4)], .15)
x, y = pad('U1', '21'); track('ADS_DOUT', F, [(x, y), (x, -3.478), (-4.535, -6.693), (-3.5, -6.693)], .15); via('ADS_DOUT', -3.5, -6.693)
track('ADS_DOUT', I2, [(-3.5, -6.693), (-3.5, -11.65)], .15); via('ADS_DOUT', -3.5, -11.65)
x6, y6 = jp(6); track('ADS_DOUT', F, [(-3.5, -11.65), (-3.15, -11.3), (5.35, -11.3), (6.4, -10.25), (x6 - .5, -10.25), (x6, -10.75), (x6, y6)], .15)
x10, y10 = jp(10); track('MCU_SCLK', F, [pad('R23', '2'), (-3.75, -7.6), (-.55, -10.8), (4.645, -10.8), (5.745, -9.7), (x10 - .7, -9.7), (x10, -10.4), (x10, y10)], .15)
x, y = pad('U1', '18'); x11, y11 = jp(11); track('ADS_CS_N', F, [(x, round(y, 3)), (x, -8.15), (-8.7, -8.7), (-5.403, -8.7), (-4.6, -7.897), (-4.6, -7.298), (-4.31, -7.008), (-3.825, -7.008), (-1.433, -9.4), (x11 - .7, -9.4), (x11, -10.1), (x11, y11)], .15)
x15, y15 = jp(15); track('MCU_PWDN', F, [pad('R31', '1'), (-5.0, -10.868), (-3.581, -12.287), (4.131, -12.287), (4.344, -12.5), (x15 - .35, -12.5), (x15, -12.15), (x15, y15)], .15)
x, y = pad('U1', '19'); x16, y16 = jp(16); xr, yr = pad('R19', '1')
track('ADS_DIN', F, [(x, y), (x, -1.825), (-8.875, -1.7), (-9.944, -1.7), (-10.7, -2.456), (-10.7, -4.534), (-9.717, -5.517), (-9.717, -8.425), (-8.024, -10.118), (-6.448, -10.118), (-6.036, -10.53), (-6.036, -11.134), (-5.765, -11.405), (-5.465, -11.405), (xr, -11.48), (xr, yr), (xr, -12.32), (-4.857, -12.853), (x16 - .3, -12.853), (x16, -12.553), (x16, y16)], .15)
x18, y18 = jp(18); xs, ys = pad('R26', '2'); track('AVDD_SENSE', F, [(xs, ys), (6.25, ys), (9.95, 9.5), (9.95, -4.7), (x18, -10.5), (x18, y18)], .15)   # 从 E2/E5 东侧 x=9.95 45° 斜下进 J2
x, y = pad('U1', '15'); track('ADS_RESET_N', F, [(x, y), (-10.1, y)], .15); via('ADS_RESET_N', -10.1, y)
track('ADS_RESET_N', I2, [(-10.1, y), (-10.6, y - .5), (-10.6, y - .8), (-10.15, y - 1.25), (-7.4, y - 1.25), (-4.95, y - 3.7), (-4.95, -9.9), (-5.918, -10.868), (-6.68, -10.868), (-7.1, -11.29)], .15); via('ADS_RESET_N', -7.1, -11.29); track('ADS_RESET_N', F, [(-7.1, -11.29), (-7.1, -11.168), (-6.8, -10.868), pad('R31', '2')], .15)   # 孔离 E4 盘边 1.5 以上
xq3, yq3 = pad('Q1', '3'); track('ADS_RESET_N', F, [(xq3, yq3), (xq3, -12.0), (-7.5525, -11.29), (-7.1, -11.29)], .15); track('ADS_RESET_N', F, [(xq3, yq3), (-7.425, yq3), (-6.025, -13.8), pad('TP8', '1')], .15)
x, y = pad('Q1', '1'); xr, _ = pad('R25', '1'); track('ILK_VBUS', F, [(x, y), (xr, y)], .15); yq = y
x, y = pad('R32', '2'); track('ILK_VBUS', F, [(-11.2, yq), (-11.2, -14.4), (-10.0, -15.6), (16.6, -15.6), (17.2, -15.0), (17.2, y - .35), (17.55, y), (x, y)], .15)   # 从 J2 1 脚和固定脚之间穿过
x19, y19 = jp(19); x, y = pad('R32', '1'); track('XIAO_5V', F, [(x19, y19), (x19, y - .36), (x19 + .36, y), (x, y)], .25)
# J2 地：J1 7、8、9 脚并到一个孔；J1 20 脚和两个固定脚各一孔
xg, yg = jp(8); track('GND', F, [(xg, yg), (xg, -10.2)]); via('GND', xg, -10.2); fan += 1
for n in (7, 9): x, y = jp(n); track('GND', F, [(x, y), (x, -10.7), (xg, -10.2)])
x, y = jp(20); track('GND', F, [(x, y), (x, -10.2)]); via('GND', x, -10.2); fan += 1
x, y = pad('J2', '21'); track('GND', F, [(x, y), (x + .8, y)]); via('GND', x + .8, y); fan += 1
x, y = pad('J2', '22'); track('GND', F, [(x, y), (x - .8, y)]); via('GND', x - .8, y); fan += 1
SKIP = {('J2', '14'), ('J2', '13'), ('J2', '12'), ('J2', '1'), ('J2', '21'), ('J2', '22'), ('R22', '2'), ('R21', '2'), ('C9', '2'), ('U1', '10'), ('U1', '13'), ('U1', '24'), ('C13', '2'), ('C12', '2'), ('C11', '2'), ('R19', '2'), ('U3', '2'), ('D1', '2'), ('D4', '2'), ('R18', '2'), ('TP3', '1')}   # TP3 在内层四根线正上方，没地方打孔，靠顶层地铜连
for p, f in allp:
    if p.GetNetname() != 'GND' or (f.GetReference(), p.GetNumber()) in SKIP: continue
    c = p.GetPosition(); cx, cy = k.ToMM(c.x) - 100, 100 - k.ToMM(c.y)
    fc = f.GetPosition(); ox, oy = cx - (k.ToMM(fc.x) - 100), cy - (100 - k.ToMM(fc.y))
    # 沿焊盘长轴出线：QFP 脚取外法线，两脚件取本体轴线
    if abs(ox) >= abs(oy): base = 0 if ox > 0 else math.pi
    else: base = math.pi / 2 if oy > 0 else -math.pi / 2
    if not (ox or oy): base = 0
    best = None
    order = (0,) if f.GetReference() == 'U1' else (0, 45, -45, 90, -90, 135, -135, 180)
    for dist in (0.65, 0.8, 0.95, 1.1, 1.3, 1.5, 1.8, 2.1, 2.4):
        for da in order:
            a = base + math.radians(da); x, y = round(cx + dist * math.cos(a), 3), round(cy + dist * math.sin(a), 3)
            if clear(x, y): best = (x, y); break
        if best: break
    assert best, f'GND 扇出无位 {f.GetReference()}.{p.GetNumber()}'
    x, y = best; vias.append(best); fan += 1
    v = k.PCB_VIA(b); v.SetPosition(mm(x, y)); v.SetDrill(k.FromMM(VIA_H)); v.SetWidth(k.FromMM(VIA_D)); v.SetNet(gnd); v.SetLocked(True); b.Add(v)
    t = k.PCB_TRACK(b); t.SetStart(c); t.SetEnd(mm(x, y)); t.SetWidth(k.FromMM(.2)); t.SetLayer(k.F_Cu if p.IsOnLayer(k.F_Cu) else k.B_Cu); t.SetNet(gnd); t.SetLocked(True); b.Add(t)

# 出线短桩：实测净效果为负（桩尖处多出尖角），默认关；STUBS=1 才开
import os
STUBS = os.environ.get('STUBS') == '1'
vs = list(vias); stub = 0; skip = []
for p, f in (allp if STUBS else []):
    ref, n = f.GetReference(), p.GetNetname()
    if not n or n == 'GND' or ref[0] in 'ET' or ref[:2] == 'TP': continue
    c = p.GetPosition(); cx, cy = k.ToMM(c.x) - 100, 100 - k.ToMM(c.y); fc = f.GetPosition()
    ox, oy = cx - (k.ToMM(fc.x) - 100), cy - (100 - k.ToMM(fc.y)); bb = p.GetBoundingBox()
    hw, hh = k.ToMM(bb.GetWidth()) / 2, k.ToMM(bb.GetHeight()) / 2
    if abs(ox) >= abs(oy): dx, dy = (1 if ox > 0 else -1), 0
    else: dx, dy = 0, (1 if oy > 0 else -1)
    L = (hw if dx else hh) + .3; tx, ty = round((cx + dx * L) / .01) * .01, round((cy + dy * L) / .01) * .01
    lay = k.F_Cu if p.IsOnLayer(k.F_Cu) else k.B_Cu; ok = True
    for q, g in allp:
        if q.GetNetname() == n or not q.IsOnLayer(lay): continue
        qc = q.GetPosition(); qx, qy = k.ToMM(qc.x) - 100, 100 - k.ToMM(qc.y); qb = q.GetBoundingBox()
        if abs(tx - qx) < k.ToMM(qb.GetWidth()) / 2 + .25 and abs(ty - qy) < k.ToMM(qb.GetHeight()) / 2 + .25: ok = False; break
    if ok and any(math.hypot(tx - vx, ty - vy) < VIA_D / 2 + .25 for vx, vy in vs): ok = False
    if not ok: skip.append(f'{ref}.{p.GetNumber()}'); continue
    t = k.PCB_TRACK(b); t.SetStart(c); t.SetEnd(mm(tx, ty)); t.SetWidth(k.FromMM(.25 if n in ('AVDD', '3V3', 'DVDD') else .15)); t.SetLayer(lay); t.SetNet(p.GetNet()); t.SetLocked(True); b.Add(t); stub += 1
print('短桩', stub, '跳过', skip)

from zones import outline
z = k.ZONE(b); z.SetLayer(k.In1_Cu); z.SetNet(gnd); o = z.Outline(); o.NewOutline()
for x, y in outline: o.Append(mm(x, y))
z.SetLocalClearance(k.FromMM(.2)); z.SetMinThickness(k.FromMM(.2)); z.SetPadConnection(k.ZONE_CONNECTION_FULL); b.Add(z)
b.GetDesignSettings().SetBoardThickness(k.FromMM(.8))
b.BuildConnectivity(); k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(OUT), b)
# 4 层 0.8 mm 叠层：写进板文件，下单板厚才不会按默认 1.6 走。介质厚度是假设，下单时按嘉立创实际叠层核
t = OUT.read_text(encoding='utf-8'); assert '(stackup' not in t
lay = lambda n, ty, th=None, extra='': f'\t\t\t(layer "{n}"\n\t\t\t\t(type "{ty}")\n' + (f'\t\t\t\t(thickness {th})\n' if th else '') + extra + '\t\t\t)\n'
di = lambda i, ty: f'\t\t\t(layer "dielectric {i}"\n\t\t\t\t(type "{ty}")\n\t\t\t\t(thickness {.1 if ty == "prepreg" else .4996})\n\t\t\t\t(material "FR4")\n\t\t\t\t(epsilon_r 4.5)\n\t\t\t\t(loss_tangent 0.02)\n\t\t\t)\n'
st = '\t\t(stackup\n' + lay('F.SilkS', 'Top Silk Screen') + lay('F.Paste', 'Top Solder Paste') + lay('F.Mask', 'Top Solder Mask', .01) + lay('F.Cu', 'copper', .035) + di(1, 'prepreg') + lay('In1.Cu', 'copper', .0152) + di(2, 'core') + lay('In2.Cu', 'copper', .0152) + di(3, 'prepreg') + lay('B.Cu', 'copper', .035) + lay('B.Mask', 'Bottom Solder Mask', .01) + lay('B.Paste', 'Bottom Solder Paste') + lay('B.SilkS', 'Bottom Silk Screen') + '\t\t\t(copper_finish "ENIG")\n\t\t\t(dielectric_constraints no)\n\t\t)\n'
assert t.count('\t(setup\n') == 1; OUT.write_text(t.replace('\t(setup\n', '\t(setup\n' + st), encoding='utf-8')
print('器件', len(D), 'GND 扇出孔', fan)
