"""板上逐焊盘网名对 design.json；板框逐段、四孔对 C08A 真板；XIAO 落位和方向。KiCad Python 运行，不符退出 1。
--selftest：把板框改坏 6 种，每种都必须报。"""
import json, re, sys
from collections import Counter
from pathlib import Path
import pcbnew as k
P = Path(__file__).resolve().parent; sys.path.insert(0, str(P))
from zones import ELECTRODES, HOLES, J2_AT
args = [a for a in sys.argv[1:] if not a.startswith('--')]
board = args[0] if args else str(P / 'ads1292-2ch.kicad_pcb')
C08A = P.parents[1] / '16ch-c08b-round/afe-d20/afe-d20-silk.kicad_pcb'
D = json.loads((P.parent / 'schematics/design.json').read_text())['parts']
rd = lambda v: round(float(v) + 0, 2)


def items(t, dx=0., dy=0.):
    """Edge.Cuts 图元 → 可比较的元组。线不分方向；弧带中点，半径和圆心写错都比得出。"""
    out = []
    for m in re.finditer(r'\n\t\((gr_line|gr_arc)\b(.*?)\n\t\)', t, re.S):
        if '"Edge.Cuts"' not in m.group(2): continue
        q = {g: (rd(float(a) + dx), rd(float(c) + dy)) for g, a, c in re.findall(r'\((start|mid|end) (-?[\d.]+) (-?[\d.]+)\)', m.group(2))}
        out.append((m.group(1), tuple(sorted((q['start'], q['end']))), q.get('mid')))
    return out


def rect(r):
    x0, x1, y0, y1 = r; p = [(100 + x0, 100 - y0), (100 + x1, 100 - y0), (100 + x1, 100 - y1), (100 + x0, 100 - y1)]
    return [('gr_line', tuple(sorted(((rd(a[0]), rd(a[1])), (rd(c[0]), rd(c[1]))))), None) for a, c in zip(p, p[1:] + p[:1])]


def edge_bad(t):
    # 11-12 Mako 定拿掉东边 USB 缺口及板内 BAT 窗、电池线孔：C08A 东边换成一条直边，板内不再开窗，其余逐段仍对 C08A
    east = lambda it: it[0] == 'gr_line' and all(x >= 115.5 and 86.3 <= y <= 113.7 for x, y in it[1])
    c08a = [it for it in items(C08A.read_text(), 78.45, 81.75) if not east(it)] + [('gr_line', ((121.55, 86.35), (121.55, 113.65)), None)]
    want = Counter(c08a); got = Counter(items(t)); bad = []
    if want - got: bad.append(f'板框缺 {list((want - got).elements())[:3]}')
    if got - want: bad.append(f'板框多 {list((got - want).elements())[:3]}')
    deg = Counter(p for _, e, _m in items(t) for p in e)
    if any(v != 2 for v in deg.values()): bad.append('板框不闭合')
    return bad


def holes_bad(b):
    t = C08A.read_text(); want = {}
    for r in ('H901', 'H902', 'H903', 'H904'):
        m = re.search(r'\(footprint "[^"]*"(?:(?!\n\t\(footprint).)*?"Reference" "' + r + r'"', t, re.S); a = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)', m.group(0))
        want[r] = (rd(float(a.group(1)) + 78.45), rd(float(a.group(2)) + 81.75))
    hs = [f for f in b.GetFootprints() if re.fullmatch(r'H\d', f.GetReference())]
    got = {(rd(k.ToMM(f.GetPosition().x)), rd(k.ToMM(f.GetPosition().y))) for f in hs}
    drill = {round(k.ToMM(q.GetDrillSize().x), 2) for f in hs for q in f.Pads()}
    return [] if got == set(want.values()) and len(HOLES) == 4 and drill == {1.7} else [f'孔不同 {sorted(got)} {sorted(want.values())} {drill}']


if '--selftest' in sys.argv:
    t = open(board, encoding='utf8').read()
    arc = re.search(r'\n\t\(gr_arc\n.*?\n\t\)', t, re.S).group(0); line = re.search(r'\n\t\(gr_line\n.*?\n\t\)', t, re.S).group(0)
    mid = re.search(r'\(mid (\S+) (\S+)\)', arc)
    cases = {'圆弧中点改错': t.replace(arc, arc.replace(mid.group(0), f'(mid {float(mid.group(1)) + .5} {mid.group(2)})')),
             '圆角改直线': t.replace(arc, arc.replace('(gr_arc', '(gr_line').replace(mid.group(0) + '\n', '')),
             '删一段': t.replace(line, ''),
             '多一段': t.replace(line, line + line.replace('"Edge.Cuts"', '"Edge.Cuts"').replace(re.search(r'\(uuid "[^"]+"\)', line).group(0), '(uuid "00000000-0000-0000-0000-000000000001")').replace(re.search(r'\(start (\S+)', line).group(1), '90')),
             '线段端点偏 0.2': t.replace(line, re.sub(r'\(start (\S+) (\S+)\)', lambda m: f'(start {float(m.group(1)) + .2} {m.group(2)})', line, 1)),
             '板内残留窗': t.replace(line, line + '\n\t(gr_line\n\t\t(start 110.35 97.1)\n\t\t(end 114.05 97.1)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "00000000-0000-0000-0000-000000000002")\n\t)')}
    assert not edge_bad(t), edge_bad(t)
    miss = [n for n, c in cases.items() if c == t or not edge_bad(c)]
    print('板框反例：', '都报了' if not miss else f'漏报 {miss}'); sys.exit(1 if miss else 0)

b = k.LoadBoard(board); bad = edge_bad(open(board, encoding='utf8').read()) + holes_bad(b); n = 0
for ref, p in D.items():
    f = b.FindFootprintByReference(ref)
    if f is None: bad.append(f'缺 {ref}'); continue
    got = {q.GetNumber(): q.GetNetname() for q in f.Pads()}
    for key, net in p['pins'].items():
        num = key.split(':')[0]; n += 1
        g_ = got.get(num, '')
        if ('' if g_.startswith('unconnected-') else g_) != ('' if net == 'NC' else net): bad.append(f'{ref}.{num} 板 {got.get(num)!r} 真源 {net}')
extra = [f.GetReference() for f in b.GetFootprints() if f.GetReference() not in D]
if extra: bad.append(f'板上多件 {extra}')
u = b.FindFootprintByReference('J2'); pd = {q.GetNumber(): q.GetPosition() for q in u.Pads()}
if (round(k.ToMM(u.GetPosition().x) - 100, 3), round(100 - k.ToMM(u.GetPosition().y), 3)) != J2_AT or round(u.GetOrientationDegrees()) % 360 != 0 or u.IsFlipped(): bad.append('J2 落位或转角不对')
# 排线直通：J2 第 21−n 脚和 P44e J1 第 n 脚同 x。P44e 俯视转到 USB 朝东：载板 x = 21.5 − P44e y（BAT 槽核过）
j1 = {q.GetNumber(): q.GetPosition() for q in k.LoadBoard(str(P.parents[1] / 'common-mainboard/adapter-p44e-xiao/p44e.kicad_pcb')).FindFootprintByReference('J1').Pads()}
off = [n for n in range(1, 21) if abs(k.ToMM(pd[str(21 - n)].x) - 100 - (21.5 - k.ToMM(j1[str(n)].y))) > .02]
if off: bad.append(f'J2 和 J1 不同 x {off}')
# J1 投影和排线通过的区域不放贴片件：J1 压在板面，排线贴着板面出入
# J1 壳体四周再留 0.3：P44e 落位偏 0.1 加焊点爬锡，焊盘贴着壳体会把 P44e 垫歪（11-10 R7.1 只隔 0.065 才查出来）
for x0, x1, y0, y1, m in ((5.8, 18.2, -8.69, -4.49, .3), (6.3, 17.7, -18.25, -8.69, 0)):
    for f in b.GetFootprints():
        if f.IsFlipped() or f.GetReference() == 'J2': continue
        for q in f.Pads():
            bb = q.GetBoundingBox(); qx0, qx1 = k.ToMM(bb.GetLeft()) - 100, k.ToMM(bb.GetRight()) - 100; qy0, qy1 = 100 - k.ToMM(bb.GetBottom()), 100 - k.ToMM(bb.GetTop())
            if qx1 > x0 - m and qx0 < x1 + m and qy1 > y0 - m and qy0 < y1 + m: bad.append(f'{f.GetReference()}.{q.GetNumber()} 压在 J1 或排线区（含余量 {m}）')
for r, (x, y) in ELECTRODES.items():
    f = b.FindFootprintByReference(r); c = (round(k.ToMM(f.GetPosition().x) - 100, 3), round(100 - k.ToMM(f.GetPosition().y), 3))
    if c != (x, y) or not f.IsFlipped(): bad.append(f'{r} 不对 {c}')
if k.ToMM(b.GetDesignSettings().GetBoardThickness()) != .8: bad.append('板厚不是 0.8')
print(f'核 {n} 脚：', '通过' if not bad else bad[:10]); sys.exit(1 if bad else 0)
