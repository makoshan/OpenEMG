"""P44e：ADS1292 载板专用转接板。从 P44d 的 ROUTED 板文本改出：板厚 1.6 → 0.8，XIAO 5V 引到 J1 19 脚，J1 14、17 脚断开。
P44d 文件不动。14、17 脚（RESET_N、CS_B）载板不用，断开才腾得出 19 脚的路；D0、D2 的上拉留着。python3 make_p44e.py，之后 kicad-cli 重铺。"""
import hashlib, re, sys, uuid
from pathlib import Path
P = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else (P / 'p44e.kicad_pcb')
raw = SRC.read_bytes(); assert hashlib.sha256(raw).hexdigest().startswith('105c0e63'), '起点不是 P44d 下单版'
t = raw.decode()
t, n = re.subn(r'\n\t\t\(filled_polygon\n.*?\n\t\t\)', '', t, flags=re.S); assert n   # 旧填铜不留，新孔落在里面会被改成 GND
assert t.count('(thickness 1.6)') == 1; t = t.replace('(thickness 1.6)', '(thickness 0.8)')
SEG = re.compile(r'\n\t\(segment\n.*?\n\t\)', re.S)
def ends(s): return {tuple(map(float, re.search(r'\(%s (\S+) (\S+)\)' % k, s).groups())) for k in ('start', 'end')}
def drop(net, a, c):
    global t
    hit = [m[0] for m in SEG.finditer(t) if f'(net "{net}")' in m[0] and ends(m[0]) == {a, c}]
    assert len(hit) == 1, (net, a, c); t = t.replace(hit[0], '')
# J1 17 脚 CS_B、14 脚 RESET_N：从 J1 到 XIAO 那段拿掉，只留 XIAO 脚到上拉电阻
for a, c in (((5.5448, 3.9583), (3.2789, 3.9583)), ((5.8344, 4.2479), (5.5448, 3.9583)), ((14.9817, 4.4412), (14.7884, 4.2479)), ((14.7884, 4.2479), (5.8344, 4.2479)),
             ((14.28, 6.25), (14.9817, 6.25)), ((3.2789, 3.9583), (2.7289, 4.5083)), ((14.9817, 6.25), (14.9817, 4.4412))): drop('CS_B', a, c)
for a, c in (((13.7343, 3.7967), (14.9722, 3.7967)), ((12.9298, 2.9922), (13.7343, 3.7967)), ((4.1735, 2.9922), (12.9298, 2.9922)), ((15.3878, 7.3439), (14.9817, 7.75)),
             ((15.3878, 4.2123), (15.3878, 7.3439)), ((14.9722, 3.7967), (15.3878, 4.2123)), ((14.28, 7.75), (14.9817, 7.75))): drop('RESET_N', a, c)
# 顶层这串地线挡在 5V 焊盘和 19 脚之间，拿掉，13 脚和孔靠顶层铺铜连
for a, c in (((14.2424, 4.1352), (13.23, 5.1476)), ((16.6025, 5.42), (15.3177, 4.1352)), ((15.1123, 4.1352), (14.2424, 4.1352)), ((15.1123, 4.1352), (15.1123, 3.195)), ((15.3177, 4.1352), (15.1123, 4.1352))): drop('GND', a, c)
def pad(ref, num, fn):
    global t
    i = t.index(f'(property "Reference" "{ref}"'); s = t.rfind('\n\t(footprint', 0, i); e = t.find('\n\t(footprint', i); e = len(t) if e < 0 else e
    blk = t[s:e]; m = re.search(r'\n\t\t\(pad "%s" .*?\n\t\t\)' % num, blk, re.S); assert m, (ref, num)
    t = t[:s] + blk.replace(m[0], fn(m[0])) + t[e:]
pad('U1', '14', lambda b: b.replace('\n\t\t\t(solder_mask_margin', '\n\t\t\t(net "5V")\n\t\t\t(solder_mask_margin', 1))
pad('J1', '19', lambda b: b.replace('\n\t\t\t(thermal_bridge_angle', '\n\t\t\t(net "5V")\n\t\t\t(thermal_bridge_angle', 1))
for n_ in ('14', '17'): pad('J1', n_, lambda b: re.sub(r'\n\t\t\t\(net "[^"]*"\)', '', b))
# 5V：J1 19 脚东出到孔，顶层 45° 进 XIAO 5V 盘
new = []; uid = lambda: uuid.uuid5(uuid.NAMESPACE_URL, f'p44e/{len(new)}')
def seg(a, c, layer): new.append(f'\n\t(segment\n\t\t(start {a[0]} {a[1]})\n\t\t(end {c[0]} {c[1]})\n\t\t(width 0.25)\n\t\t(layer "{layer}")\n\t\t(net "5V")\n\t\t(uuid "{uid()}")\n\t)')
V = (15.15, 4.4)
for a, c in (((14.28, 5.25), (15.0, 5.25)), ((15.0, 5.25), (15.15, 5.1)), ((15.15, 5.1), V)): seg(a, c, 'B.Cu')
seg(V, (16.6025, 2.9475), 'F.Cu'); seg((16.6025, 2.9475), (16.6025, 2.88), 'F.Cu')
# 13 脚的地改走孔南边，接回西边的地孔
for a, c in (((16.6025, 5.42), (13.5025, 5.42)), ((13.5025, 5.42), (13.23, 5.1476))): seg(a, c, 'F.Cu'); new[-1] = new[-1].replace('(net "5V")', '(net "GND")').replace('(width 0.25)', '(width 0.2)')
# 清理 P44d 遗留的 6 处 90° 拐角、1 处 45° 锐角分叉、14 处焊盘 45° 斜出线及 MOSI 1.7 µm 残段，使 route_lint 硬项全 0
def ends_u(s): return frozenset(tuple(map(float, re.search(r'\(%s (\S+) (\S+)\)' % k, s).groups())) for k in ('start', 'end'))
def layer_of(s): return re.search(r'\(layer "([^"]+)"\)', s).group(1)
def net_of(s): return re.search(r'\(net "([^"]+)"\)', s).group(1)
drop_set = {
    ('DRDY_A', 'B.Cu', frozenset([(14.28, 12.75), (14.9817, 12.75)])),
    ('DRDY_A', 'B.Cu', frozenset([(14.9817, 12.75), (14.9817, 14.5879)])),
    ('3V3', 'B.Cu', frozenset([(14.28, 14.25), (13.5783, 14.25)])),
    ('3V3', 'B.Cu', frozenset([(13.5783, 13.8877), (13.5783, 14.25)])),
    ('3V3', 'B.Cu', frozenset([(4.51, 12.3), (6.425, 12.3)])),
    ('3V3', 'B.Cu', frozenset([(6.425, 12.3), (7.225, 11.5)])),
    ('3V3', 'B.Cu', frozenset([(6.9149, 6.8845), (6.9149, 11.1899)])),
    ('3V3', 'B.Cu', frozenset([(6.9149, 11.1899), (7.225, 11.5)])),
    ('3V3', 'B.Cu', frozenset([(7.225, 11.5), (8.0458, 12.3208)])),
    ('3V3', 'B.Cu', frozenset([(8.0458, 12.3208), (12.4446, 12.3208)])),
    ('GND', 'B.Cu', frozenset([(14.28, 11.25), (13.5783, 11.25)])),
    ('GND', 'B.Cu', frozenset([(13.5783, 10.8877), (13.5783, 11.25)])),
    ('GND', 'B.Cu', frozenset([(13.716, 10.75), (13.5783, 10.8877)])),
    ('GND', 'B.Cu', frozenset([(13.716, 10.75), (13.5783, 10.75)])),
    ('GND', 'B.Cu', frozenset([(13.9292, 10.75), (13.716, 10.75)])),
    ('GND', 'B.Cu', frozenset([(14.28, 10.75), (13.9292, 10.75)])),
    ('GND', 'B.Cu', frozenset([(14.28, 10.25), (13.5783, 10.25)])),
    ('GND', 'B.Cu', frozenset([(13.5783, 10.5334), (13.5783, 10.25)])),
    ('GND', 'B.Cu', frozenset([(14.28, 4.75), (13.5783, 4.75)])),
    ('GND', 'B.Cu', frozenset([(13.5783, 4.75), (13.5783, 4.7993)])),
    ('GND', 'B.Cu', frozenset([(13.5783, 4.7993), (13.23, 5.1476)])),
    ('GND', 'B.Cu', frozenset([(9.3873, 10.8877), (8.775, 11.5)])),
    ('GND', 'B.Cu', frozenset([(9.3873, 10.5334), (9.3873, 10.8877)])),
    ('GND', 'B.Cu', frozenset([(8.51, 8.0), (9.3873, 8.8773)])),
    ('GND', 'B.Cu', frozenset([(9.3873, 8.8773), (9.3873, 10.5334)])),
    ('GND', 'B.Cu', frozenset([(8.51, 5.0), (8.6576, 5.1476)])),
    ('GND', 'B.Cu', frozenset([(8.6576, 5.1476), (13.23, 5.1476)])),
    ('GND', 'B.Cu', frozenset([(16.78, 3.75), (16.5292, 3.75)])),
    ('GND', 'B.Cu', frozenset([(16.5292, 3.75), (16.0783, 3.75)])),
    ('GND', 'B.Cu', frozenset([(16.5292, 3.75), (16.78, 4.0008)])),
    ('GND', 'B.Cu', frozenset([(16.78, 4.0008), (16.78, 15.25)])),
    ('RESET_N', 'B.Cu', frozenset([(3.49, 15.0), (1.6813, 13.1913)])),
    ('RESET_N', 'B.Cu', frozenset([(1.6813, 13.1913), (1.6813, 4.7005)])),
    ('START', 'B.Cu', frozenset([(7.49, 8.0), (7.6298, 8.1398)])),
    ('START', 'B.Cu', frozenset([(7.6298, 8.1398), (7.6298, 8.8828)])),
    ('PWDN_N', 'B.Cu', frozenset([(7.49, 5.0), (9.8282, 7.3382)])),
    ('PWDN_N', 'B.Cu', frozenset([(9.8282, 7.3382), (9.8282, 7.4398)])),
    ('CS_A', 'B.Cu', frozenset([(4.1147, 4.3753), (3.49, 5.0)])),
    ('CS_A', 'B.Cu', frozenset([(5.0201, 4.3753), (4.1147, 4.3753)])),
    ('MOSI', 'B.Cu', frozenset([(13.2722, 6.75), (13.271, 6.7512)])),
    ('MOSI', 'B.Cu', frozenset([(13.5783, 6.75), (13.2722, 6.75)])),
    ('MOSI', 'B.Cu', frozenset([(14.28, 6.75), (13.5783, 6.75)])),
    ('MOSI', 'F.Cu', frozenset([(13.271, 7.1685), (13.271, 6.7512)])),
}
to_drop = [m[0] for m in SEG.finditer(t) if (net_of(m[0]), layer_of(m[0]), ends_u(m[0])) in drop_set]
assert len(to_drop) == len(drop_set), (len(to_drop), len(drop_set))
for s in to_drop: t = t.replace(s, '', 1)
assert '(at 13.271 6.7512)' in t; t = t.replace('(at 13.271 6.7512)', '(at 13.271 6.75)', 1)
def chain(net, layer, pts, w=0.2):
    for a, c in zip(pts, pts[1:]):
        new.append(f'\n\t(segment\n\t\t(start {a[0]} {a[1]})\n\t\t(end {c[0]} {c[1]})\n\t\t(width {w})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uid()}")\n\t)')
chain('DRDY_A', 'B.Cu', [(14.28, 12.75), (14.7817, 12.75), (14.9817, 12.95), (14.9817, 14.5879)])
chain('3V3', 'B.Cu', [(14.28, 14.25), (13.7783, 14.25), (13.5783, 14.05), (13.5783, 13.8877)])
chain('3V3', 'B.Cu', [(6.9149, 6.8845), (6.9149, 10.69), (7.225, 11.0001), (7.225, 11.5), (7.225, 12.3)])
chain('3V3', 'B.Cu', [(4.51, 12.3), (7.225, 12.3), (8.025, 12.3), (8.0458, 12.3208), (12.4446, 12.3208)])
chain('GND', 'B.Cu', [(14.28, 11.25), (13.7783, 11.25), (13.5783, 11.05), (13.5783, 10.75)])
chain('GND', 'B.Cu', [(14.28, 10.75), (13.5783, 10.75)])
chain('GND', 'B.Cu', [(14.28, 10.25), (13.716, 10.25), (13.5783, 10.3877), (13.5783, 10.5334)])
chain('GND', 'B.Cu', [(14.28, 4.75), (13.6276, 4.75), (13.23, 5.1476)])
chain('GND', 'B.Cu', [(8.775, 11.5), (8.775, 10.95), (9.1916, 10.5334), (9.3873, 10.5334)])
chain('GND', 'B.Cu', [(8.51, 8.0), (8.51, 8.35), (9.3873, 9.2273), (9.3873, 10.5334)])
chain('GND', 'B.Cu', [(8.51, 5.0), (8.85, 5.0), (8.9976, 5.1476), (13.23, 5.1476)])
chain('GND', 'B.Cu', [(16.78, 3.75), (16.25, 3.75), (16.0783, 3.75)])
chain('GND', 'B.Cu', [(16.25, 3.75), (16.25, 4.28), (16.78, 4.81), (16.78, 15.25)])
chain('RESET_N', 'B.Cu', [(3.49, 15.0), (3.49, 14.65), (1.6813, 12.8413), (1.6813, 4.7005)])
chain('START', 'B.Cu', [(7.49, 8.0), (7.49, 8.35), (7.6298, 8.4898), (7.6298, 8.8828)])
chain('PWDN_N', 'B.Cu', [(7.49, 5.0), (7.49, 5.35), (9.4782, 7.3382), (9.8282, 7.3382), (9.8282, 7.4398)])
chain('CS_A', 'B.Cu', [(3.49, 5.0), (3.49, 4.65), (3.7647, 4.3753), (5.0201, 4.3753)])
chain('MOSI', 'F.Cu', [(13.271, 7.1685), (13.271, 6.75)])
chain('MOSI', 'B.Cu', [(14.28, 6.75), (13.271, 6.75)])
new.append(f'\n\t(via\n\t\t(at {V[0]} {V[1]})\n\t\t(size 0.6)\n\t\t(drill 0.3)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "5V")\n\t\t(uuid "{uid()}")\n\t)')
new.append(f'\n\t(gr_text "P44e ADS1292 ONLY"\n\t\t(at 8.89 19.9 0)\n\t\t(layer "B.SilkS")\n\t\t(uuid "{uid()}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.8 0.8)\n\t\t\t\t(thickness 0.13)\n\t\t\t)\n\t\t\t(justify mirror)\n\t\t)\n\t)')
i = t.index('\n\t(via\n'); t = t[:i] + ''.join(new) + t[i:]
(P / 'p44e.kicad_pcb').write_text(t); print('改完，新增', len(new))
