"""ADS1292 拼板制造包自检（2026-11-04）。KiCad 自带 Python 运行：python3 -B check_fab.py
不信生成脚本，从产物回读，和源板、design.json、rotation.json 独立比：
  1. zip 平铺，11 层 + 2 份钻孔 + job，每个文件和拼板重导一致（去日期）
  2. 拼板对源板：铜、阻焊、钻孔的每条指令都还在；多出来的全在板外工艺边或邮票孔；锡膏只少 E1–E6
  3. 锡膏开窗数 = 贴片件的焊盘数，底面 0；PTH = 过孔；NPTH = 安装孔 4 + 邮票孔 + 定位孔 4
  4. BOM/CPL 位号、C 号、面别、坐标、转角和真源一致
阳性对照：几种破坏都必须判不通过。全部通过退出 0。"""
import collections, csv, json, os, re, shutil, subprocess, sys, tempfile, zipfile
import pcbnew as k

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
CLI = os.environ.get('KICAD_CLI', 'kicad-cli'); SRC = 'source/ads1292-2ch.kicad_pcb'; PAN = 'ads1292-2ch-panel.kicad_pcb'
P = json.load(open('panel.json')); ZP = P['zip']
D = json.load(open('../design.json'))['parts']; rot = json.load(open('rotation.json'))
want = {r for r, p in D.items() if p.get('lcsc') and not p.get('dnp')}
b = k.LoadBoard(SRC); side = {f.GetReference(): 'Bottom' if f.IsFlipped() else 'Top' for f in b.GetFootprints()}
LAY = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
BOARD = (78.45, 81.75, 121.55, 118.25)   # KiCad 坐标，Gerber 里 y 取反


def export(pcb):
    d = tempfile.mkdtemp()
    subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAY, '--subtract-soldermask', '-o', d + '/', pcb], check=True, capture_output=True)
    subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th', '-o', d + '/', pcb], check=True, capture_output=True)
    return d


def ops(txt):
    """Gerber 拆成 (光圈定义, x, y, D 码) 计数，光圈编号换成定义，两次导出才可比。"""
    ap, cur, out, x, y, reg = {}, None, collections.Counter(), 0, 0, False
    macro = ''
    for ln in txt.splitlines():
        if ln.startswith('%AM'): macro = ln
        m = re.match(r'%ADD(\d+)(.*)\*%', ln)
        if m: ap[m.group(1)] = m.group(2); continue
        if ln.startswith('G36'): reg = True
        if ln.startswith('G37'): reg = False
        m = re.match(r'^D(\d+)\*$', ln)
        if m and int(m.group(1)) >= 10: cur = ap.get(m.group(1)); continue
        m = re.match(r'^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+J-?\d+)?D0([123])\*', ln)
        if m:
            x = int(m.group(1)) if m.group(1) else x; y = int(m.group(2)) if m.group(2) else y
            out[('region' if reg else cur, x, y, m.group(3))] += 1
    return out


def inside(x, y):
    X, Y = x / 1e6, -y / 1e6
    return BOARD[0] <= X <= BOARD[2] and BOARD[1] <= Y <= BOARD[3]


def drill(txt):
    tools, cur, out = {}, None, collections.Counter()
    for ln in txt.splitlines():
        m = re.match(r'^T(\d+)C([\d.]+)', ln)
        if m: tools[m.group(1)] = float(m.group(2)); continue
        m = re.match(r'^T(\d+)$', ln)
        if m: cur = m.group(1); continue
        m = re.match(r'^X(-?[\d.]+)Y(-?[\d.]+)', ln)
        if m and cur: out[(tools[cur], float(m.group(1)), float(m.group(2)))] += 1
    return out


def check_zip(zp):
    bad = []; z = zipfile.ZipFile(zp); names = z.namelist()
    if any('/' in n for n in names): bad.append('zip 有子目录')
    if any(not re.search(r'\.(g[a-z0-9]+|drl|gbrjob)$', n) for n in names): bad.append('zip 混入非 Gerber/钻孔文件')
    strip = lambda t: '\n'.join(l for l in t.splitlines() if not re.search(r'date|CreationDate', l, re.I))
    ref = export(PAN)
    if {n for n in names} != set(os.listdir(ref)): bad.append(f'文件清单不一致 {set(names) ^ set(os.listdir(ref))}')
    for n in names:
        if os.path.exists(f'{ref}/{n}') and strip(z.read(n).decode(errors='replace')) != strip(open(f'{ref}/{n}', errors='replace').read()): bad.append(f'{n} 与拼板重导不一致')
    s = export(SRC); info = {}
    pname = lambda suf: next(n for n in names if n.endswith(suf))
    sname = lambda suf: next(n for n in os.listdir(s) if n.endswith(suf))
    for suf in ('F_Cu.gtl', 'In1_Cu.g1', 'In2_Cu.g2', 'B_Cu.gbl', 'F_Mask.gts', 'B_Mask.gbs'):
        a = ops(open(f'{s}/{sname(suf)}').read()); c = ops(z.read(pname(suf)).decode())
        lost = a - c; extra = [q for q in (c - a) if inside(q[1], q[2])]
        if lost: bad.append(f'{suf} 少了 {sum(lost.values())} 条')
        if extra: bad.append(f'{suf} 板内多 {len(extra)} 条')
        info[suf] = dict(src=sum(a.values()), panel=sum(c.values()))
    pads = {'F_Paste.gtp': sum(1 for f in b.GetFootprints() if f.GetReference() in want for q in f.Pads() if q.IsOnLayer(k.F_Paste)), 'B_Paste.gbp': 0}
    for suf, n in pads.items():
        c = ops(z.read(pname(suf)).decode()); a = ops(open(f'{s}/{sname(suf)}').read())
        got = sum(v for q, v in c.items() if q[3] == '3')
        if got != n: bad.append(f'{suf} 开窗 {got} ≠ {n}')
        if c - a: bad.append(f'{suf} 比源板多开窗')
        info[suf] = dict(src=sum(v for q, v in a.items() if q[3] == '3'), panel=got)
    pth = drill(z.read(pname('-PTH.drl')).decode()); npth = drill(z.read(pname('-NPTH.drl')).decode())
    vias = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
    if sum(pth.values()) != vias: bad.append(f'PTH {sum(pth.values())} ≠ 过孔 {vias}')
    if drill(open(f'{s}/{sname("-PTH.drl")}').read()) != pth: bad.append('PTH 与源板不同')
    if sum(npth.values()) != 4 + P['bites'] + P['tooling']: bad.append(f'NPTH {sum(npth.values())}')
    if len(names) != 14: bad.append(f'文件数 {len(names)}')
    info.update(pth=sum(pth.values()), npth=sum(npth.values()), files=len(names))
    return bad, info


def check_set(bom, cpl):
    bad = []; seen = {}
    for r in csv.DictReader(open(bom)):
        refs = r['Designator'].split(',')
        if int(r['Quantity']) != len(refs): bad.append(f'BOM 数量 {r["LCSC Part #"]}')
        for x in refs:
            seen[x] = r['LCSC Part #']
            if D.get(x, {}).get('lcsc') != r['LCSC Part #']: bad.append(f'BOM {x} C 号 {r["LCSC Part #"]}')
    if set(seen) != want: bad.append(f'BOM 位号差 {sorted(set(seen) ^ want)}')
    rows = list(csv.DictReader(open(cpl))); cs = {r['Designator']: r for r in rows}
    if len(cs) != len(rows): bad.append('CPL 重复')
    if set(cs) != want: bad.append(f'CPL 位号差 {sorted(set(cs) ^ want)}')
    for x, r in cs.items():
        if x not in rot: continue
        q = rot[x]
        if r['Layer'] != side[x]: bad.append(f'CPL {x} 面别')
        X, Y = float(r['Mid X'].rstrip('m')), float(r['Mid Y'].rstrip('m'))
        if abs(X - q['cpl_x']) > .001 or abs(Y - q['cpl_y']) > .001: bad.append(f'CPL {x} 坐标')
        if not (BOARD[0] <= X <= BOARD[2] and BOARD[1] <= -Y <= BOARD[3]): bad.append(f'CPL {x} 在板外')
        if abs((float(r['Rotation']) - q['cpl_rot'] + 180) % 360 - 180) > .06: bad.append(f'CPL {x} 转角')
    return bad, dict(parts=len(seen), kinds=len(set(seen.values())))


bad1, i1 = check_zip(ZP); bad2, i2 = check_set('jlc_smt_bom.csv', 'jlc_smt_cpl.csv')
print(json.dumps(dict(zip=i1, set=i2), ensure_ascii=False)); print('问题：', bad1 + bad2 or '无')

# 阳性对照
T = tempfile.mkdtemp(); neg = []
def mut(fn, src, sub):
    t = open(src).read(); assert sub[0] in t, sub; p = f'{T}/{fn}'; open(p, 'w').write(t.replace(sub[0], sub[1], 1)); return p
BC, CC = 'jlc_smt_bom.csv', 'jlc_smt_cpl.csv'
first = list(csv.DictReader(open(CC)))[0]
neg.append(('BOM 换 C 号', check_set(mut('a.csv', BC, ('C2651570', 'C2651571')), CC)[0]))
neg.append(('CPL 删一行', check_set(BC, mut('b.csv', CC, (','.join(first.values()) + '\n', '')))[0]))
neg.append(('CPL 改面', check_set(BC, mut('c.csv', CC, (',Top,', ',Bottom,')))[0]))
u1 = next(r for r in csv.DictReader(open(CC)) if r['Designator'] == 'U1')
neg.append(('CPL 转 90', check_set(BC, mut('d.csv', CC, (f"U1,{u1['Mid X']},{u1['Mid Y']},Top,{u1['Rotation']}", f"U1,{u1['Mid X']},{u1['Mid Y']},Top,{(float(u1['Rotation']) + 90) % 360:.1f}")))[0]))
zb = f'{T}/z.zip'
with zipfile.ZipFile(ZP) as z, zipfile.ZipFile(zb, 'w') as o:
    for n in z.namelist():
        d = z.read(n)
        if n.endswith('F_Paste.gtp'):   # 多开一个窗
            d = d.replace(b'M02*', b'X100000000Y-100000000D03*\nM02*')
        if n.endswith('In2_Cu.g2'):     # 删最后一条画线
            t = d.decode().splitlines(); idx = max(i for i, l in enumerate(t) if re.search(r'D0[12]\*$', l)); del t[idx]; d = '\n'.join(t).encode()
        o.writestr(n, d)
neg.append(('Gerber 被改', check_zip(zb)[0]))
ok = all(v for _, v in neg)
print('阳性对照：', [(n, bool(v)) for n, v in neg])
shutil.rmtree(T, ignore_errors=True)
print('制造包自检：', '通过' if not (bad1 or bad2) and ok else '不通过'); sys.exit(0 if not (bad1 or bad2) and ok else 1)
