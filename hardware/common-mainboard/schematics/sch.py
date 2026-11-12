"""C08A 原理图画法库（样张 S1 定稿的画法）：按功能分框、框内连线、标签只做框间接口。
电气真源是 c08a-native-complete-20261028/expected-pins.json（冻结PCB ae043e31，已核与已下单整理版 v3 同网）；
每页 pageN.py 画完调用 finish()：用连线几何重建网表，与真源逐脚比对，不一致就退出非零。
画法约定：器件脚坐标一律用 Pn() 取，不手算；连线只走横竖；跨框信号用 lab()，电源用 pwr()/gnd()；空网脚用 nc()。"""
import json, sys
from collections import defaultdict
from pathlib import Path

P = Path(__file__).resolve().parent
# C08B 主控板 thru3：期望网表、料值、DNP 全部取自板子（pcb_pins.py 导出 ba-pcb-pins.json），不再叠 C08A 真源。
# 画法沿用 C08A 样张 S1（第 3/4/5 页改成本板第 1/2/3 页）。悬空脚为空网，必须打叉。
SRC = P
_BA = json.loads((P / 'ba-pcb-pins.json').read_text())
EXPECT = {(p['ref'], p['pin']): p['net'] for p in _BA['pins']}
DNP8 = set()
VAL = {r: c['value'] for r, c in _BA['comps'].items()}
DNP = {r for r, c in _BA['comps'].items() if c['dnp']}
GRAY = '#9a9a9a'

W, H = 1680, 1188  # A3 横向，4 px/mm
SYM, WIRE, TXT, FRAME = '#a8322d', '#1f8a3a', '#1d3f9a', '#4a4a4a'
OWN = [None]  # 当前图元归属：位号；'#' 表示电源/地/标签自身的画法（原生工程里换成原生符号）；None 表示图纸
ELEM = []      # (归属, svg 元素)，导出嘉立创原生工程用

class Rec(list):
    """svg 列表：每次追加同时记下归属。"""
    def append(self, e): ELEM.append((OWN[0], e)); super().append(e)
    def insert(self, i, e): ELEM.insert(i, (None, e)); super().insert(i, e)

def own(r): OWN[0] = r

svg, PINS, NAMED, NCS, SEGS, TEXTS = Rec(), {}, [], [], [], []
PWRS, PORTS = [], []  # (x, y, 网名, 朝上?) / (x, y, 网名, 方向)

def text(t, x, y, size=11, color=TXT, anchor='start', weight='normal'):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{t}</text>')
    w = sum(size if ord(c) > 0x2e80 else size * 0.6 for c in t)
    x0 = x - w if anchor == 'end' else x - w / 2 if anchor == 'middle' else x
    TEXTS.append((x0, y - size * 0.8, x0 + w, y + size * 0.2, t))

def line(pts, color=SYM, w=1.4, dash=None):
    d = ' '.join(f'{x},{y}' for x, y in pts)
    svg.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>')

def pin(ref, num, x, y):
    OWN[0] = ref
    PINS[(ref, num)] = (x, y)

SIDE = {}  # 竖向器件标注放左侧的位号

def label_of(ref, x, y, vertical):
    v, c = val(ref), tcol(ref)
    if vertical:
        dx, an = (-12, 'end') if ref in SIDE else (12, 'start')
        text(ref, x + dx, y - 3, anchor=an, color=c); text(v, x + dx, y + 11, anchor=an, color=c)
    else:
        text(ref, x, y - 14, anchor='middle', color=c); text(v, x, y + 24, anchor='middle', color=c)

def val(ref):
    """料值；DNP 和 8 路版不贴都写在料值后面。"""
    v = VAL[ref] + (' DNP' if ref in DNP and 'DNP' not in VAL[ref] else '')
    return v + ' 8路不贴' if ref in DNP8 else v

def tcol(ref): return GRAY if ref in DNP8 else TXT

def two_pin(ref, x, y, o, body):
    """o: h/hr/v/vr，r 表示 1 脚在右/下。返回 1、2 脚坐标。"""
    a, b = ((x - 40, y), (x + 40, y)) if o[0] == 'h' else ((x, y - 40), (x, y + 40))
    if o.endswith('r'): a, b = b, a
    pin(ref, '1', *a); pin(ref, '2', *b)
    vert = o[0] == 'v'
    body(x, y, vert)
    label_of(ref, x, y, vert)

def res(ref, x, y, o='h'):
    def body(x, y, v):
        if v:
            line([(x, y - 40), (x, y - 18)]); line([(x, y + 18), (x, y + 40)])
            svg.append(f'<rect x="{x-7}" y="{y-18}" width="14" height="36" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
        else:
            line([(x - 40, y), (x - 18, y)]); line([(x + 18, y), (x + 40, y)])
            svg.append(f'<rect x="{x-18}" y="{y-7}" width="36" height="14" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    two_pin(ref, x, y, o, body)

def cap(ref, x, y, o='v'):
    def body(x, y, v):
        if v:
            line([(x, y - 40), (x, y - 4)]); line([(x, y + 4), (x, y + 40)])
            line([(x - 12, y - 4), (x + 12, y - 4)], w=2); line([(x - 12, y + 4), (x + 12, y + 4)], w=2)
        else:
            line([(x - 40, y), (x - 4, y)]); line([(x + 4, y), (x + 40, y)])
            line([(x - 4, y - 12), (x - 4, y + 12)], w=2); line([(x + 4, y - 12), (x + 4, y + 12)], w=2)
    two_pin(ref, x, y, o, body)

def jumper(ref, x, y):
    def body(x, y, v):
        line([(x, y - 40), (x, y - 8)]); line([(x, y + 8), (x, y + 40)])
        svg.append(f'<path d="M{x-8},{y-8} A8,8 0 0 1 {x+8},{y-8} Z M{x-8},{y+8} A8,8 0 0 0 {x+8},{y+8} Z" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    two_pin(ref, x, y, 'v', body)

def diode(ref, x, y, flow, a, k, led=False):
    """flow：电流方向 right/left/up/down；a、k 为阳极、阴极脚号。"""
    d = {'right': (1, 0), 'left': (-1, 0), 'down': (0, 1), 'up': (0, -1)}[flow]
    pa, pk = (x - 40 * d[0], y - 40 * d[1]), (x + 40 * d[0], y + 40 * d[1])
    pin(ref, a, *pa); pin(ref, k, *pk)
    n = (-d[1], d[0])
    t0, t1 = (x - 10 * d[0], y - 10 * d[1]), (x + 10 * d[0], y + 10 * d[1])
    line([pa, t0]); line([t1, pk])
    tri = [(t0[0] + 10 * n[0], t0[1] + 10 * n[1]), (t0[0] - 10 * n[0], t0[1] - 10 * n[1]), t1]
    svg.append('<polygon points="' + ' '.join(f'{p[0]},{p[1]}' for p in tri) + f'" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    line([(t1[0] + 10 * n[0], t1[1] + 10 * n[1]), (t1[0] - 10 * n[0], t1[1] - 10 * n[1])], w=2)
    if led:
        for s in (0, 7):
            bx, by = x + 6 + s, y - 14
            line([(bx, by), (bx + 8, by - 8)], w=1); line([(bx + 8, by - 8), (bx + 3, by - 7)], w=1)
    vert = flow in ('up', 'down')
    label_of(ref, x, y, vert)

def bat54c(ref, x, y):
    """共阴双二极管，阳极在右（A1 上、A2 下），阴极在左。"""
    pin(ref, '1', x + 40, y - 20); pin(ref, '2', x + 40, y + 20); pin(ref, '3', x - 40, y)
    for yy in (y - 20, y + 20):
        line([(x + 40, yy), (x + 12, yy)])
        svg.append(f'<polygon points="{x+12},{yy-8} {x+12},{yy+8} {x-4},{yy}" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
        line([(x - 4, yy - 8), (x - 4, yy + 8)], w=2); line([(x - 4, yy), (x - 14, yy)])
    line([(x - 14, y - 20), (x - 14, y + 20)]); line([(x - 14, y), (x - 40, y)])
    text(ref, x - 8, y - 34, color=tcol(ref)); text(val(ref), x - 8, y + 44, color=tcol(ref))

def mos(ref, x, y, ch):
    """G 在左；N 管 D 上 S 下，P 管 S 上 D 下。AO3400A/AO3401A：1=G 2=S 3=D。"""
    top, bot = ('3', '2') if ch == 'N' else ('2', '3')
    pin(ref, '1', x - 40, y); pin(ref, top, x, y - 40); pin(ref, bot, x, y + 40)
    line([(x - 40, y), (x - 14, y)]); line([(x - 14, y - 14), (x - 14, y + 14)], w=2)
    line([(x - 8, y - 18), (x - 8, y + 18)], w=2)
    line([(x - 8, y - 12), (x, y - 12), (x, y - 40)]); line([(x - 8, y + 12), (x, y + 12), (x, y + 40)])
    ay = y + 12 if ch == 'N' else y - 12
    tip, tail = ((x - 8, ay), (x, ay)) if ch == 'N' else ((x, ay), (x - 8, ay))
    svg.append(f'<polygon points="{tip[0]},{tip[1]} {tip[0]+(5 if ch=="N" else -5)},{tip[1]-4} {tip[0]+(5 if ch=="N" else -5)},{tip[1]+4}" fill="{SYM}"/>')
    text(ref, x + 10, y - 4, color=tcol(ref)); text(val(ref), x + 10, y + 10, color=tcol(ref))

def ic(ref, x0, y0, w, h, pins, name=None, name_dy=None, ref_at=None):
    own(ref)
    """pins: (脚号, 脚名, 边 L/R/T/B, 偏移)。脚伸出 20。"""
    svg.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#fffdf4" stroke="{SYM}" stroke-width="1.4"/>')
    for num, nm, side, off in pins:
        if side == 'L': a, b, tx, an = (x0 - 20, y0 + off), (x0, y0 + off), (x0 + 5, y0 + off + 4), 'start'
        if side == 'R': a, b, tx, an = (x0 + w + 20, y0 + off), (x0 + w, y0 + off), (x0 + w - 5, y0 + off + 4), 'end'
        if side == 'T': a, b, tx, an = (x0 + off, y0 - 20), (x0 + off, y0), (x0 + off, y0 + 14), 'middle'
        if side == 'B': a, b, tx, an = (x0 + off, y0 + h + 20), (x0 + off, y0 + h), (x0 + off, y0 + h - 6), 'middle'
        pin(ref, num, *a); line([a, b])
        text(nm, *tx, size=10, color=SYM, anchor=an)
        nx, ny = ((a[0] + b[0]) / 2, a[1] - 3) if side in 'LR' else (a[0] + 3, (a[1] + b[1]) / 2 + 3)
        text(num, nx, ny, size=8, color='#777', anchor='middle' if side in 'LR' else 'start')
    rx, ry = ref_at or (x0, y0 - 8 if not any(s == 'T' for _, _, s, _ in pins) else y0 - 24)
    text(ref, rx, ry, weight='bold', color=tcol(ref))
    if name: text(name, x0 + w, y0 + h + 14, anchor='end')
    else: text(val(ref), x0 + w / 2, y0 + (name_dy or h / 2 + 4), size=10, color=GRAY if ref in DNP8 else '#333', anchor='middle', weight='bold')

def pwr(net, x, y, up=True):
    s = -1 if up else 1
    own('#'); PWRS.append((x, y, net, up))
    NAMED.append((x, y, net))
    line([(x, y), (x, y + 14 * s)], WIRE); line([(x - 10, y + 14 * s), (x + 10, y + 14 * s)], SYM, 2)
    text(net, x, y + (s * 20 if up else 32), size=11, color=SYM, anchor='middle', weight='bold'); own(None)

def gnd(x, y):
    own('#'); PWRS.append((x, y, 'GND', False))
    NAMED.append((x, y, 'GND'))
    line([(x, y), (x, y + 8)], WIRE)
    for i, half in enumerate((10, 6, 2)): line([(x - half, y + 8 + i * 3), (x + half, y + 8 + i * 3)], SYM, 1.6)
    own(None)

LABS = []

def lab(net, x, y, d):
    """框间接口：旗形标签，d 为旗子伸出方向。"""
    own('#'); PORTS.append((x, y, net, d))
    NAMED.append((x, y, net)); LABS.append((x, y))
    w = sum(11 if ord(c) > 0x2e80 else 7.5 for c in net) + 14
    if d == 'right': pts = [(x, y), (x + 8, y - 8), (x + w, y - 8), (x + w, y + 8), (x + 8, y + 8)]; tx, an = x + 10, 'start'
    if d == 'left': pts = [(x, y), (x - 8, y - 8), (x - w, y - 8), (x - w, y + 8), (x - 8, y + 8)]; tx, an = x - 10, 'end'
    if d == 'up':
        pts = [(x, y), (x + w / 2, y - 6), (x + w / 2, y - 22), (x - w / 2, y - 22), (x - w / 2, y - 6)]; tx, an = x, 'middle'
        svg.append('<polygon points="' + ' '.join(f'{a},{b}' for a, b in pts) + f'" fill="#eef3ff" stroke="{TXT}" stroke-width="1"/>')
        text(net, tx, y - 10, size=11, anchor=an); own(None); return
    svg.append('<polygon points="' + ' '.join(f'{a},{b}' for a, b in pts) + f'" fill="#eef3ff" stroke="{TXT}" stroke-width="1"/>')
    text(net, tx, y + 4, size=11, anchor=an); own(None)

def nc(x, y):
    own('~')
    NCS.append((x, y)); line([(x - 5, y - 5), (x + 5, y + 5)], '#2050c0', 1.4); line([(x - 5, y + 5), (x + 5, y - 5)], '#2050c0', 1.4)
    own(None)

def Pn(ref, num): return PINS[(ref, num)]

def wire(*pts):
    own('~')
    for a, b in zip(pts, pts[1:]):
        assert a[0] == b[0] or a[1] == b[1], ('斜线', a, b)
        SEGS.append((a, b))
    line(pts, WIRE, 1.6)
    own(None)

def block(x0, y0, x1, y1, title, note):
    own(None)
    svg.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="none" stroke="{FRAME}" stroke-width="1.6"/>')
    text(title, x0 + 12, y0 + 26, size=19, color='#111', weight='bold')
    text(note, x0 + 12, y0 + 48, size=11, color='#555')


def finish(page, name, refs, title, subtitle):
    """page 页号；refs 本页应画的全部位号；title/subtitle 写在左下大标题。"""
    refs = set(refs)
    own(None)
    svg.insert(0, f'<rect x="10" y="10" width="{W-20}" height="{H-20}" fill="none" stroke="#333" stroke-width="2"/>')
    svg.insert(0, f'<rect width="{W}" height="{H}" fill="#fffdf6"/>')
    text(title, 40, 1125, size=22, color='#111', weight='bold')
    text(subtitle, 40, 1155, size=12, color='#555')
    x0, y0 = 1180, 1094
    svg.append(f'<rect x="{x0}" y="{y0}" width="470" height="84" fill="none" stroke="#333" stroke-width="1.4"/>')
    for yy in (y0 + 28, y0 + 56): line([(x0, yy), (x0 + 470, yy)], '#333', 1)
    line([(x0 + 80, y0), (x0 + 80, y0 + 84)], '#333', 1); line([(x0 + 300, y0), (x0 + 300, y0 + 84)], '#333', 1); line([(x0 + 370, y0), (x0 + 370, y0 + 84)], '#333', 1)
    for i, (k, v, k2, v2) in enumerate([('图名', 'C08B 主控板 · ' + name, '版本', '参考版'), ('图页', f'{page} / 5', '日期', '2026-11-08'), ('网表', '与主控板 PCB 逐脚一致', '尺寸', 'A3')]):
        yy = y0 + 19 + 28 * i
        text(k, x0 + 10, yy, size=12, color='#333'); text(v, x0 + 90, yy, size=12, color='#111')
        text(k2, x0 + 310, yy, size=12, color='#333'); text(v2, x0 + 380, yy, size=12, color='#111')

    # ---------------- 用几何重建网表并与真源逐脚比对 ----------------
    def on_seg(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]))

    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b): parent[find(a)] = find(b)
    nodes = set(PINS.values()) | {(x, y) for x, y, _ in NAMED} | set(NCS) | {p for s in SEGS for p in s}
    for i, (a, b) in enumerate(SEGS):
        for p in nodes:
            if on_seg(p, a, b): union(('s', i), p)
    names = defaultdict(set)
    for x, y, n in NAMED: names[find((x, y))].add(n)
    err = []
    drawn = {r for r, _ in PINS}
    miss = [k for k in EXPECT if k[0] in refs and k not in PINS]
    extra = [k for k in PINS if k not in EXPECT or k[0] not in refs]
    if miss: err.append(f'漏画脚 {miss}')
    if extra: err.append(f'多出脚 {extra}')
    grp_nets = defaultdict(set)
    for k, xy in PINS.items():
        if k in EXPECT: grp_nets[find(xy)].add(EXPECT[k])
    for g, ns in grp_nets.items():
        if len(ns) > 1: err.append(f'短接 {sorted(ns)}')
        if len(names[g]) > 1: err.append(f'一组多名 {sorted(names[g])}')
        if names[g] and names[g] != ns: err.append(f'标签与网不符 {sorted(names[g])} vs {sorted(ns)}')
    net_groups = defaultdict(set)
    for k, xy in PINS.items():
        if k in EXPECT: net_groups[EXPECT[k]].add(find(xy))
    for n, gs in net_groups.items():
        if n == '':
            for k, xy in PINS.items():
                if EXPECT.get(k) == '' and (xy not in NCS or len([1 for kk, p in PINS.items() if find(p) == find(xy)]) > 1): err.append(f'空网脚未打叉或被连上 {k}')
        elif len(gs) > 1 and any(not names[g] for g in gs): err.append(f'断开 {n}：{len(gs)} 段且有段无标签')
    for x, y, n in NAMED:
        if find((x, y)) not in grp_nets: err.append(f'悬空标签 {n}@{x},{y}')
    # 文字互压（估算外框）
    ov = [(a[4], b[4]) for i, a in enumerate(TEXTS) for b in TEXTS[i + 1:] if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]]
    # 字压线：文字外框（四边各收 1）与导线相交
    def hits(t, a, b):
        x0, y0, x1, y1 = t[0] + 1, t[1] + 1, t[2] - 1, t[3] - 1
        if a[1] == b[1]: return y0 < a[1] < y1 and min(a[0], b[0]) < x1 and max(a[0], b[0]) > x0
        return x0 < a[0] < x1 and min(a[1], b[1]) < y1 and max(a[1], b[1]) > y0
    ow = sorted({t[4] for t in TEXTS for a, b in SEGS if hits(t, a, b)})
    # 连接点：某点上导线臂数 + 是否有脚/标签 ≥ 3 就画实心点（T 接、脚尖压在线中间）
    pts = set(PINS.values()) | {(x, y) for x, y, _ in NAMED} | {p for s in SEGS for p in s}
    endpoints = set(PINS.values()) | {(x, y) for x, y, _ in NAMED}
    for p in pts:
        deg = sum(1 if p in (a, b) else 2 for a, b in SEGS if on_seg(p, a, b)) + (p in endpoints)
        if deg >= 3: svg.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="3.2" fill="{WIRE}"/>')
    lab_groups = {find(p) for p in LABS}
    only_label = sum(1 for k, xy in PINS.items() if find(xy) in lab_groups and sum(1 for p in PINS.values() if find(p) == find(xy)) == 1)
    report = {'页': page, '元件': len(drawn), '脚': len(PINS), '连线段': len(SEGS), '标签与电源符号': len(NAMED),
              '只靠标签的脚': only_label, '只靠标签占比': round(only_label / len(PINS), 3), '文字互压': ov, '字压线': ow, '错误': err}
    # 跨页核对用：每个连通组的脚和名字，由 check_all.py 汇总
    groups = defaultdict(lambda: {'脚': [], '名': []})
    for k, xy in PINS.items(): groups[find(xy)]['脚'].append(f'{k[0]}.{k[1]}')
    for g in groups: groups[g]['名'] = sorted(names[g])
    (P / f'page{page}-groups.json').write_text(json.dumps(list(groups.values()), ensure_ascii=False))
    (P / f'page{page}-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (P / f'page{page}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="PingFang SC, Helvetica, sans-serif">' + ''.join(svg) + '</svg>')
    from native_export import export
    report['归属可疑'] = export(page, name, refs, find)
    (P / f'page{page}-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(1 if err else 0)
