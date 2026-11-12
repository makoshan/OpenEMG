"""贴肤几何门：电极盘（大 φ4、辅 φ3）外沿 1.5 mm 内没有电源和逻辑，底层只有电极桩和地，In2 不压电极投影。
KiCad Python：check_skin.py [板文件]；--selftest 往板上塞一个逻辑孔，必须判失败。不符退出 1。"""
import json, math, sys
from pathlib import Path
import pcbnew as k
P = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith('--')]; selftest = '--selftest' in sys.argv
b = k.LoadBoard(args[0] if args else str(P / 'ads1292-2ch.kicad_pcb'))
E = {'E1': 'E1_CH1P', 'E2': 'E2_CH1N', 'E3': 'E3_RLD', 'E4': 'E4_CH2P', 'E5': 'E5_CH2N', 'E6': 'E6_RLD'}
sys.path.insert(0, str(P)); from zones import ER
FREE = set(E.values())                                      # 第一颗电阻之前、没有限流的铜
HIGHZ = {'N1P', 'N1N', 'N2P', 'N2N', 'NRLD'}                # 已隔至少 300 kΩ：桥到电极不增加电流，只按 DRC 间距
xy = lambda p: (k.ToMM(p.x) - 100, 100 - k.ToMM(p.y))
def seg_d(p, a, c):
    (px, py), (ax, ay), (cx, cy) = p, a, c; dx, dy = cx - ax, cy - ay; L = dx * dx + dy * dy
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L)) if L else 0
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
items = []   # (网, 层集合, 到点距离函数)
for t in b.GetTracks():
    n = t.GetNetname()
    if t.Type() == k.PCB_VIA_T:
        c = xy(t.GetPosition()); r = k.ToMM(t.GetWidth(k.F_Cu)) / 2
        items.append((n, {'F.Cu', 'In2.Cu', 'B.Cu'}, 'via', lambda p, c=c, r=r: math.hypot(p[0] - c[0], p[1] - c[1]) - r, c))
    else:
        a, c = xy(t.GetStart()), xy(t.GetEnd()); r = k.ToMM(t.GetWidth()) / 2
        items.append((n, {t.GetLayerName()}, 'track', lambda p, a=a, c=c, r=r: seg_d(p, a, c) - r, a))
for f in b.GetFootprints():
    if f.GetReference() in E: continue
    for q in f.Pads():
        bb = q.GetBoundingBox(); x0, y0 = xy(bb.GetPosition()); w, h = k.ToMM(bb.GetWidth()), k.ToMM(bb.GetHeight()); y0 -= h
        L = {b.GetLayerName(l) for l in q.GetLayerSet().Seq() if b.GetLayerName(l) in ('F.Cu', 'B.Cu')}
        items.append((q.GetNetname(), L, 'pad', lambda p, x0=x0, y0=y0, w=w, h=h: math.hypot(max(x0 - p[0], 0, p[0] - x0 - w), max(y0 - p[1], 0, p[1] - y0 - h)), (x0, y0)))
if selftest:   # 反例：E4 东边 1 mm 放一个 ADS_START 孔
    items.append(('ADS_START', {'F.Cu', 'In2.Cu', 'B.Cu'}, 'via', lambda p: math.hypot(p[0] + 5, p[1] + 7.5) - .225, (-5, -7.5)))
bad, rep = [], {}
for r, n in E.items():
    f = b.FindFootprintByReference(r); c = xy(f.GetPosition()); rep[r] = {'中心': c}
    own = {n}
    for lay, lim, key in (('B.Cu', 1.5, '底层最近非地'), ('In2.Cu', .35, 'In2 最近非本网')):
        d = [(fn(c) - ER[r], net, kind) for net, L, kind, fn, _ in items if lay in L and net not in own and net != 'GND' and net and net not in HIGHZ]
        m = min(d) if d else (99, '', ''); rep[r][key] = (round(m[0], 3), m[1], m[2])
        if m[0] < lim: bad.append(f'{r} {key} {m[0]:.3f} < {lim} {m[1]}')
# 底层除地和电极桩外不能有线
longest = 0
for t in b.GetTracks():
    if t.Type() != k.PCB_VIA_T and t.GetLayerName() == 'B.Cu' and t.GetNetname() != 'GND' and t.GetNetname() not in FREE:
        L = k.ToMM(t.GetLength()); longest = max(longest, L)
        bad.append(f'底层有信号线 {t.GetNetname()} {L:.2f}')
rep['底层信号线最长'] = round(longest, 2)
# 第一颗电阻前的铜：总长和到电源、逻辑的最近距离（各层都算）
free = {}
for t in b.GetTracks():
    n = t.GetNetname()
    if n in FREE and t.Type() != k.PCB_VIA_T: free[n] = free.get(n, 0) + k.ToMM(t.GetLength())
rep['无限流铜长度'] = {n: round(v, 2) for n, v in free.items()}
# 长度门：这段铜没有限流，不许悄悄变长。E2 的 7.0 是共用负端时分两路留下的，现在只到 R3，没收紧
for n, lim in {'E1_CH1P': 2.5, 'E2_CH1N': 7.0, 'E3_RLD': 2.0, 'E4_CH2P': 3.2, 'E5_CH2N': 2.0, 'E6_RLD': 2.0}.items():   # 前四个同 4e8501c76，新增两个按最严的 2.0
    if free.get(n, 0) + (20 if selftest and n == 'E2_CH1N' else 0) > lim: bad.append(f'{n} 无限流铜 {free.get(n, 0):.2f} > {lim}')
# 无限流铜到电源、逻辑的最近距离：线、孔、焊盘都按胶囊算，各层都查。门槛 0.45（内层和壳内干侧；皮肤一侧已按 1.5 卡）
caps = []
for t in b.GetTracks():
    if t.Type() == k.PCB_VIA_T:
        c = xy(t.GetPosition()); caps.append((t.GetNetname(), {'F.Cu', 'In2.Cu', 'B.Cu'}, c, c, k.ToMM(t.GetWidth(k.F_Cu)) / 2))
    else: caps.append((t.GetNetname(), {t.GetLayerName()}, xy(t.GetStart()), xy(t.GetEnd()), k.ToMM(t.GetWidth()) / 2))
for f in b.GetFootprints():
    if f.GetReference() in E: continue
    for q in f.Pads():
        bb = q.GetBoundingBox(); x0, y0 = xy(bb.GetPosition()); w, h = k.ToMM(bb.GetWidth()), k.ToMM(bb.GetHeight()); cx, cy = x0 + w / 2, y0 - h / 2; r = min(w, h) / 2; e = max(w, h) / 2 - r
        a_, c_ = ((cx - e, cy), (cx + e, cy)) if w >= h else ((cx, cy - e), (cx, cy + e))
        caps.append((q.GetNetname(), {b.GetLayerName(l) for l in q.GetLayerSet().Seq() if b.GetLayerName(l) in ('F.Cu', 'B.Cu')}, a_, c_, r))
if selftest: caps.append(('3V3', {'F.Cu', 'In2.Cu', 'B.Cu'}, (-10.4, 8.05), (-10.4, 8.05), .225))   # 反例：E1 孔旁放 3V3 孔，全层门必须报
near = {}
for n, L, a, c, r in caps:
    if n not in FREE: continue
    for m_, L2, a2, c2, r2 in caps:
        if m_ in FREE or m_ in HIGHZ or m_ == 'GND' or not m_ or m_.startswith('unconnected') or not (L & L2): continue
        d = min(seg_d(a, a2, c2), seg_d(c, a2, c2), seg_d(a2, a, c), seg_d(c2, a, c)) - r - r2
        if d < near.get(n, (99,))[0]: near[n] = (round(d, 3), m_, sorted(L & L2)[0])
rep['无限流铜最近电源逻辑'] = near
for n, (d, m_, l) in near.items():
    if d < .45: bad.append(f'{n} 到 {m_} {d} < 0.45（{l}）')
out = P / ('skin-selftest.json' if selftest else 'skin.json'); out.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
for r in E: print(r, rep[r])
print(rep['无限流铜长度'], '底层桩', longest)
print(rep['无限流铜最近电源逻辑'])
print('贴肤几何门：', '通过' if not bad else bad); sys.exit(1 if bad else 0)
