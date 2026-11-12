"""把一页的几何导出成嘉立创原生工程要的数据（page{N}-native.json），由 build_eprj3.js 写成 .eprj3。
单位：1 px = 0.01 inch（嘉立创原生单位）；eprj3 本地文件 Y 轴朝上，图纸坐标取 H - y。
器件：归属于该位号的图元做成它自己的符号（脚尖即 PIN），位号/料值文字变成可见的 Designator/Name 属性；
电源、地、旗形标签换成原生电源符号和网络端口；其余图元（框、标题栏、打叉、说明文字）放在图纸上。"""
import json, math, re
import sch

H = sch.H  # 图纸高；嘉立创图框从 (0,0) 往上长，图纸 y 换成 H - y

ATTR = re.compile(r'(\w[\w-]*)="([^"]*)"')


def attrs(e):
    return dict(ATTR.findall(e.split('>', 1)[0]))


def color(c):
    return None if c in (None, 'none', sch.SYM) else c


def style(a, closed=False):
    fill = a.get('fill', 'none')
    return dict(strokeColor=color(a.get('stroke')), strokeStyle='DASH' if a.get('stroke-dasharray') else 'SOLID',
                strokeWidth=None, fillColor=None if fill == 'none' else fill, fillStyle='NONE' if fill == 'none' else 'SOLID')


def arcs(d, ox, oy):
    """解析 path 的 M/m、A/a、Z：每段圆弧给出 起点/弧上中点/终点；Z 给一条闭合直线。"""
    toks = re.findall(r'[MmAaZzLl]|-?[\d.]+', d)
    out, i, cur, start = [], 0, None, None
    while i < len(toks):
        c = toks[i]; i += 1
        if c in 'Mm':
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            cur = (x, y) if c == 'M' or cur is None else (cur[0] + x, cur[1] + y); start = cur
        elif c in 'Ll':
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            nxt = (x, y) if c == 'L' else (cur[0] + x, cur[1] + y)
            out.append(('LINE', cur, nxt)); cur = nxt
        elif c in 'Aa':
            r, _, _, large, sweep, x, y = (float(t) for t in toks[i:i + 7]); i += 7
            end = (x, y) if c == 'A' else (cur[0] + x, cur[1] + y)
            m = ((cur[0] + end[0]) / 2, (cur[1] + end[1]) / 2)
            dx, dy = end[0] - cur[0], end[1] - cur[1]; L = math.hypot(dx, dy)
            n = (dy / L, -dx / L) if sweep == 1 else (-dy / L, dx / L)  # 屏幕坐标下弧鼓出的一侧
            h = math.sqrt(max(r * r - (L / 2) ** 2, 0))
            out.append(('ARC', cur, (m[0] + n[0] * (r - h), m[1] + n[1] * (r - h)), end)); cur = end
        elif c in 'Zz':
            out.append(('LINE', cur, start)); cur = start
    return out


def shape(e, ox, oy):
    """svg 元素 → 原生图元列表 [(类型, 字段)]，坐标相对 (ox, oy)，Y 朝上。"""
    P = lambda x, y: (round(float(x) - ox, 3), round(oy - float(y), 3))
    a, tag = attrs(e), e[1:].split(' ', 1)[0]
    if tag in ('polyline', 'polygon'):
        pts = [P(*p.split(',')) for p in a['points'].split()]
        if tag == 'polygon': pts.append(pts[0])
        flat = [v for p in pts for v in p]
        return [('POLY', dict(style(a), dots=flat, points=[dict(x=x, y=y) for x, y in pts], closed=tag == 'polygon'))]
    if tag == 'rect':
        if 'stroke' not in a: return []  # 整页底色，嘉立创图纸自带背景
        x, y, w, h = (float(a.get(k, 0)) for k in ('x', 'y', 'width', 'height'))
        (x1, y1), (x2, y2) = P(x, y), P(x + w, y + h)
        return [('RECT', dict(style(a), dotX1=x1, dotY1=y1, dotX2=x2, dotY2=y2, radiusX=0, radiusY=0, rotation=0))]
    if tag == 'circle':
        cx, cy = P(a['cx'], a['cy'])
        return [('CIRCLE', dict(style(a), centerX=cx, centerY=cy, radius=float(a['r'])))]
    if tag == 'path':
        out = []
        for k, *pts in arcs(a['d'], ox, oy):
            q = [P(*p) for p in pts]
            if k == 'LINE': out.append(('POLY', dict(style(a), dots=[*q[0], *q[1]], points=[dict(x=x, y=y) for x, y in q], closed=False)))
            else: out.append(('ARC', dict(style(a), startX=q[0][0], startY=q[0][1], referX=q[1][0], referY=q[1][1], endX=q[2][0], endY=q[2][1])))
        return out
    if tag == 'text':
        x, y = P(a['x'], a['y'])
        al = {'start': 'LEFT', 'middle': 'CENTER', 'end': 'RIGHT'}[a.get('text-anchor', 'start')]
        return [('TEXT', dict(x=x, y=y, rotation=90 if 'rotate(-90' in a.get('transform', '') else 0,
                              value=re.search(r'>(.*)</text>', e).group(1), color=a.get('fill'), fillColor=None, fontFamily=None,
                              fontSize=float(a.get('font-size', 11)), fontWeight=a.get('font-weight') == 'bold',
                              italic=False, underline=False, strikeout=False, align=al + '_BOTTOM'))]
    raise ValueError(('未支持的 svg 元素', e[:80]))


def on_seg(p, a, b):
    return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]))


def export(page, name, refs, find):
    comps, sheet, odd = {}, [], []
    pins = {}
    for (r, n), xy in sch.PINS.items(): pins.setdefault(r, {})[n] = xy
    box = {r: (min(x for x, _ in v.values()), min(y for _, y in v.values()), max(x for x, _ in v.values()), max(y for _, y in v.values())) for r, v in pins.items()}
    for owner, e in sch.ELEM:
        if owner in ('#', '~'): continue  # 电源/地/标签/导线/打叉自身的画法：原生里换成原生符号或导线，绝不重复导出为图纸装饰线
        if owner is None or owner not in pins:
            if e.startswith('<circle') and 'r="3.2"' in e: continue  # 连接点由嘉立创自己画
            sheet += shape(e, 0, H); continue
        comps.setdefault(owner, []).append(e)
    out = {'page': page, 'name': name, 'components': [], 'sheet': sheet, 'wires': [], 'power': [], 'ports': []}
    for r in sorted(refs):
        ox, oy = pins[r][min(pins[r])]  # 原点取某个脚尖，保证在格点上
        bx = box[r]
        c = {'ref': r, 'value': sch.VAL[r], 'x': ox, 'y': H - oy, 'dnp': r in sch.DNP, 'dnp8': r in sch.DNP8,
             'pins': [{'num': n, 'x': x - ox, 'y': oy - y} for n, (x, y) in sorted(pins[r].items())],
             'graphics': [], 'designator': None, 'name': None}
        for e in comps.get(r, []):
            for typ, body in shape(e, ox, oy):
                # 归属核对：图元离自己的脚包络太远，多半归错了
                pts = [(body.get('x'), body.get('y'))] if typ == 'TEXT' else []
                if typ == 'TEXT':
                    ax, ay = body['x'] + ox, oy - body['y']
                    if not (bx[0] - 90 <= ax <= bx[2] + 90 and bx[1] - 90 <= ay <= bx[3] + 90): odd.append(f'{r}:{body["value"]}')
                    if body['value'] == r and c['designator'] is None: c['designator'] = body; continue
                    if body['value'] in (sch.val(r), sch.VAL[r]) and c['name'] is None: c['name'] = body; continue
                c['graphics'].append({'type': typ, 'body': body})
        out['components'].append(c)
    # 导线：按连通组合并，组里有标签/电源名就给网名
    groups = {}
    # 嘉立创只认「线端碰脚尖/线端」：线中途经过的脚尖、线端、电源/标签点都要在那里把线断开
    nodes = set(sch.PINS.values()) | {(x, y) for x, y, _ in sch.NAMED} | {p for s in sch.SEGS for p in s}
    pin_net = {xy: sch.EXPECT[k] for k, xy in sch.PINS.items() if sch.EXPECT.get(k)}
    gnet = {}
    for xy, n in pin_net.items(): gnet.setdefault(find(xy), n)
    for x, y, n in sch.NAMED: gnet.setdefault(find((x, y)), n)
    wires = {}
    def seg(g, a, b): wires.setdefault(g, []).append([a[0], H - a[1], b[0], H - b[1]])
    for i, (a, b) in enumerate(sch.SEGS):
        g = find(('s', i))
        k = 0 if a[1] == b[1] else 1
        cut = sorted({p for p in nodes if on_seg(p, a, b)} | {a, b}, key=lambda p: p[k])
        for p, q in zip(cut, cut[1:]): seg(g, p, q)
    # 电源/地：SVG 里竖线（地 8、电源 14）是导线，原生电源符号放在竖线末端
    power = []
    for x, y, n, up in sch.PWRS:
        end = (x, y - 14) if up else (x, y + 14) if n not in ('GND', 'AGND') else (x, y + 8)
        seg(find((x, y)), (x, y), end)
        power.append({'x': end[0], 'y': H - end[1], 'net': n, 'up': up})
    # 旗形标签：沿旗子方向引 10 的短线，原生端口放在线端
    ports = []
    for x, y, n, d in sch.PORTS:
        dx, dy = {'right': (10, 0), 'left': (-10, 0), 'up': (0, -10), 'down': (0, 10)}[d]
        seg(find((x, y)), (x, y), (x + dx, y + dy))
        ports.append({'x': x + dx, 'y': H - y - dy, 'net': n, 'dir': d})
    out['wires'] = [{'net': gnet.get(g), 'segs': s} for g, s in wires.items()]
    out['power'], out['ports'] = power, ports
    (sch.P / f'page{page}-native.json').write_text(json.dumps(out, ensure_ascii=False))
    return odd
