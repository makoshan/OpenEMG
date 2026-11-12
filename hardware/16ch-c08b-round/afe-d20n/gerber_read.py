"""从 Gerber 文本回读铜皮和开口，不经过 KiCad。check_fab.py、panel/check_panel.py 共用。KiCad Python 运行（要 numpy）。
只处理 KiCad 导出的子集：直线、flash、G36 区域、LPD。遇到圆弧或 LPC 直接报错，不静默漏算。"""
import re, struct, zlib
import numpy as np

# 16 颗设了 thermal 的地焊盘（D16 拆成 GND、AGND），KiCad 在焊盘外 0.02 mm 环上数出的连接数（d15/README 的 2 处 10 颗、3 处 6 颗）
THERMAL = {**{f'V4_C{n}': 2 for n in (33, 34, 81, 82, 84, 119, 120, 55, 71, 108)}, **{f'V4_C{n}': 3 for n in (32, 37, 117, 118, 123, 124)}}
SOLID = 'C901'      # 阳性对照：地焊盘实连铺铜
MIN_RUN = 0.05      # 环上连续铜短于这个长度不算一条连接（采样噪声）


def parse(text):
    assert '%MOMM*%' in text and '%FSLAX46Y46*%' in text and not re.search(r'^G0[23]\*|^%LPC', text, re.M), '不是预期的 KiCad Gerber 子集'
    ap, macros = {}, {}
    for name, body in re.findall(r'%AM(\w+)\*(.*?)%', text, re.S): macros[name] = body
    for n, kind, args in re.findall(r'%ADD(\d+)([A-Za-z]\w*)(?:,([^*]*))?\*%', text):
        v = [float(x) for x in (args or '').split('X') if x]
        if kind == 'C': ap[n] = ('C', v[0], v[0])
        elif kind in ('R', 'O'): ap[n] = (kind, v[0], v[1])
        elif kind == 'RoundRect':
            xs, ys = v[1:9:2], v[2:9:2]; ap[n] = ('R', max(xs) - min(xs) + 2 * v[0], max(ys) - min(ys) + 2 * v[0])
        elif kind == 'RotRect': ap[n] = ('R', v[0], v[1])   # 只有 J_AFE 转 −0.012°，按不转算
        else:   # FreePoly：取多边形外包
            nums = [float(x) for x in re.findall(r'-?\d+\.\d+', macros[kind])]; ap[n] = ('R', 2 * max(map(abs, nums[0::2])), 2 * max(map(abs, nums[1::2])))
    flashes, draws, regions, cur, region, x, y = [], [], [], None, None, 0, 0
    for line in text.splitlines():
        if line == 'G36*': region = []; continue
        if line == 'G37*': regions.append(np.array(region)); region = None; continue
        m = re.fullmatch(r'D(\d+)\*', line)
        if m and int(m[1]) >= 10: cur = m[1]; continue
        m = re.fullmatch(r'(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*', line)
        if not m: continue
        nx = int(m[1]) / 1e6 if m[1] else x; ny = int(m[2]) / 1e6 if m[2] else y; op = m[3]
        if region is not None: region.append((nx, ny))
        elif op == '3': flashes.append((cur, nx, ny))
        elif op == '1': draws.append((ap[cur][1], x, y, nx, ny))
        x, y = nx, ny
    return dict(ap=ap, flashes=flashes, draws=np.array(draws).reshape(-1, 5), regions=regions)


def dark(g, pts):
    """pts (N,2) 里每个点是否有铜。"""
    out = np.zeros(len(pts), bool); px, py = pts[:, 0], pts[:, 1]
    lo, hi = pts.min(0), pts.max(0)
    for poly in g['regions']:
        if poly[:, 0].max() < lo[0] or poly[:, 0].min() > hi[0] or poly[:, 1].max() < lo[1] or poly[:, 1].min() > hi[1]: continue
        x0, y0 = poly.T; x1, y1 = np.roll(poly, -1, 0).T; ins = np.zeros(len(pts), bool)
        # 奇偶规则（KiCad 用切线把洞并进外轮廓）：只留跨过这批点 y 范围、且不在点左边的边
        for i in np.flatnonzero((y0 != y1) & (np.minimum(y0, y1) <= hi[1]) & (np.maximum(y0, y1) >= lo[1]) & (np.maximum(x0, x1) >= lo[0])):
            ins ^= ((y0[i] > py) != (y1[i] > py)) & (px < x0[i] + (py - y0[i]) * (x1[i] - x0[i]) / (y1[i] - y0[i]))
        out |= ins
    for w, x0, y0, x1, y1 in g['draws']:
        if max(x0, x1) + w < lo[0] or min(x0, x1) - w > hi[0] or max(y0, y1) + w < lo[1] or min(y0, y1) - w > hi[1]: continue
        dx, dy = x1 - x0, y1 - y0; t = np.clip(((px - x0) * dx + (py - y0) * dy) / max(dx * dx + dy * dy, 1e-18), 0, 1)
        out |= np.hypot(px - x0 - t * dx, py - y0 - t * dy) <= w / 2
    for n, x, y in g['flashes']:
        k, sx, sy = g['ap'][n]
        if k == 'C': out |= np.hypot(px - x, py - y) <= sx / 2
        else: out |= (abs(px - x) <= sx / 2) & (abs(py - y) <= sy / 2)
    return out


def ring(cx, cy, hx, hy, d, step=0.004):
    """矩形焊盘外 d 处一圈采样点。"""
    a, b = hx + d, hy + d
    n1, n2 = int(2 * a / step), int(2 * b / step)
    xs, ys = np.linspace(-a, a, n1, endpoint=False), np.linspace(-b, b, n2, endpoint=False)
    return np.c_[np.r_[xs, np.full(n2, a), -xs, np.full(n2, -a)] + cx, np.r_[np.full(n1, -b), ys, np.full(n1, b), -ys] + cy]


def runs(mask, step=0.004):
    """环上连续有铜的段数和总覆盖比例。"""
    if mask.all(): return 1, 1.0
    r = np.roll(mask, -int(np.argmin(mask))); e = np.flatnonzero(np.diff(np.r_[0, r.astype(int), 0]))
    return int(sum((b - a) * step >= MIN_RUN for a, b in zip(e[::2], e[1::2]))), float(mask.mean())


def pad_ring(g, pad, d=0.02):
    n, c = runs(dark(g, ring(pad['x'], pad['y'], pad['hx'], pad['hy'], d)))
    return dict(connections=n, coverage=round(c, 3))


def thermal_errors(cu, pads):
    """cu = {'F': parse 结果, 'B': ...}；pads = {位号: 地焊盘}。返回 (问题, 明细)。"""
    bad, rows = [], {}
    for ref, want in {**THERMAL, SOLID: None}.items():
        p = pads[ref]; g = cu[p['side']]; r = pad_ring(g, p); rows[ref] = r
        if want is None:
            if r['coverage'] < 0.85: bad.append(f'{ref} 地焊盘应实连，环上铜只有 {r["coverage"]}')
            continue
        # 缝的中线（间隙 0.25 的一半）上也只能剩辐条和线
        mid = pad_ring(g, p, 0.12); r['mid_gap'] = mid
        if r['connections'] != want: bad.append(f'{ref} 连接数 {r["connections"]} ≠ {want}')
        if r['coverage'] > 0.6 or mid['coverage'] > 0.6: bad.append(f'{ref} 铜把焊盘围住了（{r["coverage"]}/{mid["coverage"]}），thermal 丢失')
    return bad, rows


def png(path, tiles, cols=6, px=160, span=1.6):
    """把各焊盘周围 span mm 的回读铜画成一张 PNG；黄 = 铜，灰 = 空。tiles = [(名字, Gerber, 焊盘)]。只用标准库 + numpy。"""
    rows = -(-len(tiles) // cols); pic = np.full((rows * (px + 6), cols * (px + 6), 3), 255, np.uint8)
    for i, (_, g, p) in enumerate(tiles):
        t = np.linspace(-span / 2, span / 2, px); xx, yy = np.meshgrid(t + p['x'], p['y'] - t)
        m = dark(g, np.c_[xx.ravel(), yy.ravel()]).reshape(px, px)
        tile = np.where(m[..., None], np.array([214, 158, 46], np.uint8), np.array([40, 40, 48], np.uint8))
        r, c = divmod(i, cols); pic[r * (px + 6):r * (px + 6) + px, c * (px + 6):c * (px + 6) + px] = tile
    raw = b''.join(b'\0' + row.tobytes() for row in pic)
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', pic.shape[1], pic.shape[0], 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def fill_errors(g, board_polys):
    """Gerber 的 G36 区域和板内保存的填充比，多重集相等才算没有重铺。board_polys：该层全部填充多边形的顶点列表（nm 整数）。"""
    key = lambda pts: tuple(sorted(set((round(x * 1e6), round(y * 1e6)) for x, y in pts)))
    a = sorted(key(p) for p in g['regions']); b = sorted(key(p) for p in board_polys)
    return [] if a == b else [f'铺铜区域 {len(a)} 块与板内填充 {len(b)} 块不同，差 {len(set(a) ^ set(b))}']


def size_of(g, n):
    return tuple(sorted(g['ap'][n][1:]))


def gnd_pads(k, board):
    """{位号: 焊盘}：设了 thermal 的 GND 焊盘，加上阳性对照 C901。坐标已转成 Gerber 的 y 向上。"""
    out = {}
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() in ('GND', 'AGND') and (p.GetLocalZoneConnection() == k.ZONE_CONNECTION_THERMAL or f.GetReference() == SOLID):
                sx, sy = k.ToMM(p.GetSize().x), k.ToMM(p.GetSize().y)
                if abs(f.GetOrientationDegrees() % 180 - 90) < 1: sx, sy = sy, sx
                out[f.GetReference()] = dict(x=k.ToMM(p.GetPosition().x), y=-k.ToMM(p.GetPosition().y), hx=sx / 2, hy=sy / 2, side='B' if f.IsFlipped() else 'F', pad=p.GetNumber())
    return out


def board_fill(k, board, layer):
    """该层板内保存的全部填充多边形，转成 Gerber 坐标。KiCad 存的是切线合并后的单链。"""
    polys = []
    for z in board.Zones():
        if z.IsOnLayer(layer) and z.HasFilledPolysForLayer(layer):
            ps = z.GetFilledPolysList(layer)
            for i in range(ps.OutlineCount()):
                c = ps.COutline(i); polys.append([(c.CPoint(j).x / 1e6, -c.CPoint(j).y / 1e6) for j in range(c.PointCount())])
    return polys


def open_errors(k, board, g, layer):
    """钢网或阻焊层：板上每个焊盘都要有一个同位置、同尺寸的 flash，且不能多出别的。"""
    bad, want = [], 0; used = set(); pos = {}
    for i, (n, x, y) in enumerate(g['flashes']): pos.setdefault((round(x, 2), round(y, 2)), []).append(i)
    for f in board.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(layer): continue
            want += 1; x, y = k.ToMM(p.GetPosition().x), -k.ToMM(p.GetPosition().y); m = 2 * k.ToMM(p.GetSolderMaskExpansion(layer)) if layer in (k.F_Mask, k.B_Mask) else 0
            near = [i for dx in (-.01, 0, .01) for dy in (-.01, 0, .01) for i in pos.get((round(x + dx, 2), round(y + dy, 2)), []) if abs(g['flashes'][i][1] - x) < .002 and abs(g['flashes'][i][2] - y) < .002]
            if not near: bad.append(f'{f.GetReference()}.{p.GetNumber()} 没有开口'); continue
            used.add(near[0])
            if p.GetShape() == k.PAD_SHAPE_CUSTOM: continue
            size = sorted((k.ToMM(p.GetSize().x) + m, k.ToMM(p.GetSize().y) + m)); got = size_of(g, g['flashes'][near[0]][0])
            if abs(size[0] - got[0]) > .002 or abs(size[1] - got[1]) > .002: bad.append(f'{f.GetReference()}.{p.GetNumber()} 开口 {got} ≠ 焊盘 {size}')
    if len(g['flashes']) != want: bad.append(f'开口 {len(g["flashes"])} 个 ≠ 焊盘 {want} 个')
    return bad, want
