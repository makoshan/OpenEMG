"""ADS1292 载板贴片文件（2026-11-04）。KiCad 自带 Python 运行：python3 -B make_smt.py
先跑 make_panel.py（取源板）和 rot_check.py（rotation.json）。贴哪些件、C 号只看 ../design.json：有 C 号且不是 DNP。
板在拼板里原地不动，CPL 和拼板 Gerber 同一坐标系。Footprint 列写嘉立创封装名，Comment 写库里真实型号。
产物：jlc_smt_bom.csv、jlc_smt_cpl.csv、bom-detail.csv、orientation.csv、polarity-top.svg。"""
import glob
import csv, json, os, re, subprocess
import pcbnew as k
from rotation_source import verify_source

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
SRC = 'source/ads1292-2ch.kicad_pcb'; CLI = os.environ.get('KICAD_CLI', 'kicad-cli')
verify_source(SRC, 'rotation.json')
D = json.load(open('../design.json'))['parts']; rot = json.load(open('rotation.json'))
SD = sorted(glob.glob('stock-*.jsonl'))[-1][6:14]   # 最新一份库存的日期，写进明细表头
stock = {r['key']: r for f in sorted(glob.glob('stock-*.jsonl')) for r in map(json.loads, open(f)) if r.get('lcsc')}   # 按日期顺序读，后查的盖前面的
b = k.LoadBoard(SRC); fps = {f.GetReference(): f for f in b.GetFootprints()}
order = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))
smt = sorted((r for r, p in D.items() if p.get('lcsc') and not p.get('dnp')), key=order)

cpl = {}
for r in smt:
    v = rot[r]; cpl[r] = [r, f"{v['cpl_x']:.4f}mm", f"{v['cpl_y']:.4f}mm", v['side'], f"{round(v['cpl_rot'], 1) % 360:.1f}"]
with open('jlc_smt_cpl.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation']); w.writerows(cpl[r] for r in smt)

groups = {}
for r in smt: groups.setdefault(D[r]['lcsc'], []).append(r)
with open('jlc_smt_bom.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Quantity'])
    for lc, refs in sorted(groups.items(), key=lambda x: -len(x[1])):
        w.writerow([stock[lc]['mpn'], ','.join(refs), stock[lc]['package'], lc, len(refs)])
with open('bom-detail.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['LCSC Part #', '型号', '每板', '3 块', '库别', f'库存({SD[:4]}-{SD[4:6]}-{SD[6:]})', '最小贴装', '损耗', '单价(USD,1+)', '位号'])
    for lc, refs in sorted(groups.items(), key=lambda x: (str(stock[x[0]]['lib']), -len(x[1]))):
        s = stock[lc]; w.writerow([lc, s['mpn'], len(refs), len(refs) * 3, s['lib'], s['stock'], s['least'], s['loss'], s['price1'], ','.join(refs)])

# 方向表：多脚件 1 脚；ESD501 有方向，1 脚 = 信号、2 脚 = GND
ori = []
for r in smt:
    f = fps[r]; pn = {q.GetNumber(): q for q in f.Pads()}
    if not re.match(r'[UQDJ]\d', r): continue
    q = pn['1']; kind = '1 脚 = 信号（2 脚 = GND）' if r[0] == 'D' else '1 脚'
    ori.append([r, D[r]['value'], cpl[r][3], kind, f'{k.ToMM(q.GetPosition().x):.3f}', f'{-k.ToMM(q.GetPosition().y):.3f}', f'{f.GetOrientationDegrees():.0f}', cpl[r][4], rot[r]['status']])
with open('orientation.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['位号', '型号', '面', '标记', '标记焊盘X(mm)', '标记焊盘Y(mm)', 'KiCad角度', 'CPL角度', '转角核对']); w.writerows(ori)

# 极性图：板框 + 焊盘 + 位号，1 脚红点。给嘉立创「传极性图」用，背面按从背面看（左右镜像）
ol = k.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol, True); bb = ol.BBox()
X0, Y0, W, H = k.ToMM(bb.GetX()) - 2, k.ToMM(bb.GetY()) - 2, k.ToMM(bb.GetWidth()) + 4, k.ToMM(bb.GetHeight()) + 4
poly = ol.Outline(0); pts = [(k.ToMM(poly.CPoint(i).x), k.ToMM(poly.CPoint(i).y)) for i in range(poly.PointCount())]
for side in ('Top',):   # 底面没有贴片件
    mx = (lambda x: X0 + W - (x - X0)) if side == 'Bottom' else (lambda x: x)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X0} {Y0} {W} {H}" width="{W * 30:.0f}" height="{H * 30:.0f}"><rect x="{X0}" y="{Y0}" width="{W}" height="{H}" fill="#fff"/>',
         '<polygon fill="#eef3ee" stroke="#000" stroke-width=".08" points="' + ' '.join(f'{mx(x):.3f},{y:.3f}' for x, y in pts) + '"/>']
    for r in smt:
        f = fps[r]
        if cpl[r][3] != side: continue
        for q in f.Pads():
            x, y = k.ToMM(q.GetPosition().x), k.ToMM(q.GetPosition().y); bx = q.GetBoundingBox()
            w_, h_ = k.ToMM(bx.GetWidth()), k.ToMM(bx.GetHeight())
            s.append(f'<rect x="{mx(x) - w_ / 2:.3f}" y="{y - h_ / 2:.3f}" width="{w_:.3f}" height="{h_:.3f}" fill="#999"/>')
        x, y = k.ToMM(f.GetPosition().x), k.ToMM(f.GetPosition().y)
        s.append(f'<text x="{mx(x):.3f}" y="{y - .9:.3f}" font-size=".62" font-family="Arial" text-anchor="middle" stroke="#fff" stroke-width=".14" paint-order="stroke">{r}</text>')
    for o in ori:
        if o[2] != side: continue
        x, y = float(o[4]), -float(o[5])
        s.append(f'<circle cx="{mx(x):.3f}" cy="{y:.3f}" r=".3" fill="#d00"/>')
    t = '顶面，红点 = 1 脚；D1–D5 的 1 脚 = 信号'
    s.append(f'<text x="{X0 + 1}" y="{Y0 + H - .6}" font-size=".9" font-family="PingFang SC,Arial">{t}</text></svg>')
    open(f'polarity-{side.lower()}.svg', 'w').write('\n'.join(s))
print('贴片', len(smt), '| 顶', sum(cpl[r][3] == 'Top' for r in smt), '底', sum(cpl[r][3] == 'Bottom' for r in smt), '| 料种', len(groups), '| 未核转角', [r for r in smt if not str(rot[r]['status']).startswith('ok')])
