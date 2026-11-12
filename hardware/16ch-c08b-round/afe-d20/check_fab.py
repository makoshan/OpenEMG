"""D20 制造包产物自检。KiCad 自带 Python：python3 -B check_fab.py [包目录名前缀]
D18 包已逐项核过（转角、换焊盘、ESD 等），这里只证明 D20 包 = D18 包 + 已知差异：
  1. zip 平铺、11 层、每个文件 = 源板重导（去时间戳）；板框、PTH = 过孔 + 金属化焊盘、NPTH
  2. BOM = D18 BOM 去掉 C384950（32 颗 470 pF）那一行，16 颗差分电容 C76922（100 pF）那行换成 C76924（22 pF，11-09 晚 Mako 定）；C 号 = 板上字段；位号集合 = 板上要贴的件
  3. CPL = D18 CPL 去掉那 32 行；只有 V4_C54/V4_C92 的 Mid Y 少 0.005，且板上这两颗正好下移 0.005；其余件板上位置、角度、面与 D18 相同
  4. Gerber 铺铜 = 板内填充；thermal（D18 的 16 颗去掉已删的 3 颗）回读；钢网、阻焊逐焊盘
  5. DRC 不重铺、重铺 0 错 0 未连；贴片门通过
阳性对照：每种破坏都必须判不通过。全部通过退出 0。"""
import csv, json, os, re, shutil, subprocess, sys, tempfile, zipfile
import pcbnew as k

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')
META = json.load(open('SOURCE.json'))
BASE = os.path.basename(META['file']).rsplit('.', 1)[0]; SRC = f'source/{BASE}.kicad_pcb'
ZP = next(f for f in os.listdir('.') if f.endswith('.zip') and f.startswith('c08b-afe-'))
D18 = '../fab-d18-20261108'
import gerber_read as G
sys.path.insert(0, os.path.join(HERE, '../../../host'))
import smt_dfm_gate as DFM
DEL = {f'V4_C{n}' for n in (55, *range(57, 72), *range(93, 109))}; assert len(DEL) == 32
NUDGE = {'V4_C54', 'V4_C92'}
# 11-09 晚 Mako 定「现在换 22 pF」：16 颗输入差分电容 100 pF（C76922）→ 22 pF（C76924），改法见 ../d20-22pf-20261109/retag.py
CAP22 = {f'V4_C{n}' for n in (*range(72, 80), *range(109, 117))}; assert len(CAP22) == 16
b = k.LoadBoard(SRC); d18 = k.LoadBoard(f'{D18}/source/afe-d18.kicad_pcb')
fps = {f.GetReference(): f for f in b.GetFootprints()}; f18 = {f.GetReference(): f for f in d18.GetFootprints()}
G.THERMAL = {r: n for r, n in G.THERMAL.items() if r in fps}
fit = {r for r, f in fps.items() if not f.IsDNP() and not f.IsExcludedFromBOM()}
def lcsc(f):
    try: return f.GetFieldText('LCSC')
    except KeyError: return ''   # 安装孔、测试点没有这个字段
want_lc = {r: lcsc(fps[r]) for r in fit}
_ol = k.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(_ol, True); bb = _ol.BBox()
BX0, BY0, BX1, BY1 = k.ToMM(bb.GetX()), k.ToMM(bb.GetY()), k.ToMM(bb.GetRight()), k.ToMM(bb.GetBottom())
n_via = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
pads = [q for f in b.GetFootprints() for q in f.Pads()]
n_pth = sum(1 for q in pads if q.GetAttribute() == k.PAD_ATTRIB_PTH)
n_npth = sum(1 for q in pads if q.GetAttribute() == k.PAD_ATTRIB_NPTH)
WANT_LAYERS = {'Copper,L1,Top', 'Copper,L2,Inr', 'Copper,L3,Inr', 'Copper,L4,Bot', 'SolderMask,Top', 'SolderMask,Bot',
               'Legend,Top', 'Legend,Bot', 'SolderPaste,Top', 'SolderPaste,Bot', 'Profile'}
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
REF = tempfile.mkdtemp()
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', REF + '/', SRC], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th', '-o', REF + '/', SRC], check=True, capture_output=True)
strip = lambda t: '\n'.join(l for l in t.splitlines() if not re.search(r'date', l, re.I))


def excellon_hits(txt):
    tools, hits, cur = {}, {}, None
    for line in txt.splitlines():
        m = re.match(r'^T(\d+)C([\d.]+)', line)
        if m: tools[m.group(1)] = float(m.group(2)); continue
        m = re.match(r'^T(\d+)$', line)
        if m: cur = m.group(1); continue
        if (re.match(r'^X[-\d.]+Y[-\d.]+', line) or line.startswith('G85')) and cur: hits[cur] = hits.get(cur, 0) + 1
    return tools, hits


def gerber_extent(txt):
    fs = re.search(r'%FSLAX(\d)(\d)Y\d\d\*%', txt); d = int(fs.group(2)); unit = 1.0 if '%MOMM*%' in txt else 25.4
    pts = [(int(m.group(1)) / 10 ** d * unit, int(m.group(2)) / 10 ** d * unit) for m in re.finditer(r'^X(-?\d+)Y(-?\d+)D0[123]\*', txt, re.M)]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def check_zip(zp):
    bad = []; z = zipfile.ZipFile(zp); names = z.namelist()
    if any('/' in n for n in names): bad.append('zip 有子目录')
    if any(not re.search(r'\.(g[a-z0-9]+|drl|gbrjob)$', n) for n in names): bad.append('zip 混入非 Gerber/钻孔文件')
    job = json.loads(z.read(next(n for n in names if n.endswith('.gbrjob'))))
    got = {f['FileFunction'] for f in job['FilesAttributes']}
    if got != WANT_LAYERS: bad.append(f'Gerber 层不对：缺 {WANT_LAYERS - got} 多 {got - WANT_LAYERS}')
    for n in names:
        if os.path.exists(f'{REF}/{n}') and strip(z.read(n).decode(errors='replace')) != strip(open(f'{REF}/{n}', errors='replace').read()):
            bad.append(f'{n} 内容与源板重导不一致')
    if {n for n in names if not n.endswith('.gbrjob')} != {n for n in os.listdir(REF) if not n.endswith(('.gbrjob', '.pdf'))}:
        bad.append('zip 文件清单与源板重导不一致')
    x0, y0, x1, y1 = gerber_extent(z.read(next(n for n in names if 'Edge_Cuts' in n)).decode())
    if abs((x1 - x0) - (BX1 - BX0)) > 0.01 or abs((y1 - y0) - (BY1 - BY0)) > 0.01: bad.append(f'板框 {x1 - x0:.3f}×{y1 - y0:.3f} ≠ 源板')
    t, h = excellon_hits(z.read(next(n for n in names if n.endswith('-PTH.drl'))).decode())
    if sum(h.values()) != n_via + n_pth: bad.append(f'PTH 孔 {sum(h.values())} ≠ 过孔 {n_via} + 金属化焊盘 {n_pth}')
    if min(t.values()) < 0.15 - 1e-6: bad.append(f'最小孔 {min(t.values())}')
    npth_name = [n for n in names if n.endswith('-NPTH.drl')]
    hn = excellon_hits(z.read(npth_name[0]).decode())[1] if npth_name else {}
    if sum(hn.values()) != n_npth: bad.append(f'NPTH 孔 {sum(hn.values())} ≠ {n_npth}')
    return bad, dict(files=len(names), layers=len(got), board=f'{x1 - x0:.2f}×{y1 - y0:.2f}', pth=sum(h.values()), npth=sum(hn.values()), min_drill=min(t.values()))


def place(f): return (round(k.ToMM(f.GetPosition().x), 4), round(k.ToMM(f.GetPosition().y), 4), round(f.GetOrientationDegrees(), 3), f.IsFlipped())


def board_errors():
    """D20 板上件位 = D18 去掉 32 颗、C54/C92 下移 0.005；孔、板框差异由缺口版自己说明（holes_removed）。"""
    bad = []; gone = set(f18) - set(fps); extra = set(fps) - set(f18)
    allowed_gone = DEL | set(META.get('holes_removed', []))
    if gone != allowed_gone: bad.append(f'删件不符：多删 {sorted(gone - allowed_gone)[:5]} 少删 {sorted(allowed_gone - gone)[:5]}')
    if extra: bad.append(f'多出件 {sorted(extra)[:5]}')
    for r in set(fps) & set(f18):
        a, c = place(fps[r]), place(f18[r])
        if r in NUDGE:
            if (a[0], a[2], a[3]) != (c[0], c[2], c[3]) or abs(a[1] - c[1] - 0.005) > 1e-4: bad.append(f'{r} 不是下移 0.005：{c} → {a}')
        elif a != c: bad.append(f'{r} 位置变了 {c} → {a}')
        if lcsc(fps[r]) != ('C76924' if r in CAP22 else lcsc(f18[r])): bad.append(f'{r} C 号变了')
    return bad


def check_set(bom, cpl):
    bad = []
    rows = lambda p: [(r['Comment'], r['Designator'], r['Footprint'], r['LCSC Part #'], r['Quantity']) for r in csv.DictReader(open(p))]
    want = [('GRM0335C1H220JA01D', x[1], x[2], 'C76924', x[4]) if x[3] == 'C76922' else x
            for x in rows(f'{D18}/jlc_smt_bom.csv') if x[3] != 'C384950']
    if rows(bom) != want: bad.append('BOM ≠ D18 BOM 去掉 C384950 行、C76922 换 C76924')
    seen = {}
    for r in csv.DictReader(open(bom)):
        refs = [x for x in r['Designator'].split(',') if x]
        if int(r['Quantity']) != len(refs): bad.append(f'BOM 数量不符 {r["LCSC Part #"]}')
        for x in refs:
            seen[x] = r['LCSC Part #']
            if want_lc.get(x) != r['LCSC Part #']: bad.append(f'BOM {x} C 号 {r["LCSC Part #"]} ≠ 板上 {want_lc.get(x)}')
    if set(seen) != fit: bad.append(f'BOM 位号差：缺 {sorted(fit - set(seen))[:5]} 多 {sorted(set(seen) - fit)[:5]}')
    if seen.get('V4_R18') != 'C17168': bad.append('V4_R18 不是 0R（C17168）：两个地的唯一连接')
    old = {r['Designator']: r for r in csv.DictReader(open(f'{D18}/jlc_smt_cpl.csv'))}
    crow = list(csv.DictReader(open(cpl))); cs = {r['Designator']: r for r in crow}
    if len(cs) != len(crow): bad.append('CPL 位号重复')
    if set(cs) != fit: bad.append(f'CPL 位号差：缺 {sorted(fit - set(cs))[:5]} 多 {sorted(set(cs) - fit)[:5]}')
    for x, r in cs.items():
        o = old.get(x)
        if o is None: bad.append(f'CPL {x} D18 没有'); continue
        if x in NUDGE:
            o = dict(o, **{'Mid Y': f'{float(o["Mid Y"].rstrip("mm")) - 0.005:.4f}mm'})
        if r != o: bad.append(f'CPL {x} ≠ D18 行{"（应下移 0.005）" if x in NUDGE else ""}：{r} vs {o}')
        mx, my = float(r['Mid X'].rstrip('mm')), -float(r['Mid Y'].rstrip('mm'))
        if not (BX0 <= mx <= BX1 and BY0 <= my <= BY1): bad.append(f'CPL {x} 在板外')
    return bad, dict(bom_parts=len(seen), bom_lines=len(rows(bom)), cpl=len(cs))


def layer_text(zp, tail):
    z = zipfile.ZipFile(zp); return z.read(next(n for n in z.namelist() if n.endswith(tail))).decode()


def copper_errors(zp):
    g = {n: G.parse(layer_text(zp, t)) for n, t in (('F', 'F_Cu.gtl'), ('I1', 'In1_Cu.g1'), ('I2', 'In2_Cu.g2'), ('B', 'B_Cu.gbl'))}
    bad = [x for n, ly in (('F', k.F_Cu), ('I1', k.In1_Cu), ('I2', k.In2_Cu), ('B', k.B_Cu)) for x in G.fill_errors(g[n], G.board_fill(k, b, ly))]
    th, rows = G.thermal_errors(g, G.gnd_pads(k, b))
    return bad + th, rows


def open_layers(zp):
    bad, n = [], {}
    for tail, ly in (('F_Paste.gtp', k.F_Paste), ('B_Paste.gbp', k.B_Paste), ('F_Mask.gts', k.F_Mask), ('B_Mask.gbs', k.B_Mask)):
        e, c = G.open_errors(k, b, G.parse(layer_text(zp, tail)), ly); bad += e; n[tail] = c
    return bad, n


def drc(out, refill):
    d = tempfile.mkdtemp(); [shutil.copy(f'source/{BASE}.{e}', d) for e in ('kicad_pcb', 'kicad_pro', 'kicad_dru')]; shutil.copy('source/fp-lib-table', d)
    os.symlink(os.path.abspath('../d15/C08A.pretty'), f'{d}/C08A.pretty')   # 都在副本上跑，源板不动
    subprocess.run([CLI, 'pcb', 'drc', *(['--refill-zones'] if refill else []), '--severity-all', '--format', 'json', '-o', os.path.abspath(out), f'{d}/{BASE}.kicad_pcb'], check=True, capture_output=True)
    shutil.rmtree(d)
    # 只排除两类「板上封装 vs 库」提示，警告也算（丝印压开窗是警告级）：库没加载时报 lib_footprint_issues；
    # 加载 d15/C08A.pretty 时报 lib_footprint_mismatch——D20 重画了 80 个 courtyard、加了 5 个 1 脚点，焊盘与库逐个相同（11-09 复核 libcmp）
    LIB = {'lib_footprint_issues', 'lib_footprint_mismatch'}
    j = json.load(open(out)); v = [x for x in j['violations'] if x['type'] not in LIB]
    n = dict(violations=len(v), unconnected_items=len(j['unconnected_items']), lib_notes=len(j['violations']) - len(v))
    return ([f'{out} {n}'] if n['violations'] or n['unconnected_items'] else []), n


bad, info = check_zip(ZP)
bad += board_errors()
e, info['smt'] = check_set('jlc_smt_bom.csv', 'jlc_smt_cpl.csv'); bad += e
nth = sum(q.GetLocalZoneConnection() == k.ZONE_CONNECTION_THERMAL for q in pads)
if nth != len(G.THERMAL): bad.append(f'板上 thermal {nth} 颗 ≠ 名单 {len(G.THERMAL)}')
e, thermal = copper_errors(ZP); bad += e
e, info['opens'] = open_layers(ZP); bad += e
for out, rf in (('drc.json', False), ('drc-refill.json', True)):
    e, info[out] = drc(out, rf); bad += e
e, info['smt_dfm'] = DFM.errors(SRC, 'jlc_smt_cpl.csv', 'jlc_smt_bom.csv'); bad += ['贴片门：' + x for x in e]
info['thermal'] = len(G.THERMAL)
print('自检', '通过' if not bad else '不通过', json.dumps(info, ensure_ascii=False))
for x in bad[:30]: print('  ', x)

# 阳性对照
tmp = tempfile.mkdtemp(); B, C = 'jlc_smt_bom.csv', 'jlc_smt_cpl.csv'
crows = list(csv.reader(open(C)))
def mut(fn, name):
    p = f'{tmp}/{name}.csv'; rr = [list(x) for x in crows]; fn(rr)
    with open(p, 'w', newline='') as fh: csv.writer(fh, lineterminator='\n').writerows(rr)
    return p
def edit(ref, col, f):
    def g(rr):
        for x in rr:
            if x[0] == ref: x[col] = f(x[col])
    return g
def zipmut(name, keep, fix):
    p = f'{tmp}/{name}.zip'
    with zipfile.ZipFile(ZP) as zi, zipfile.ZipFile(p, 'w') as zo:
        for n in zi.namelist():
            if keep(n): zo.writestr(n, fix(n, zi.read(n)))
    return p
b_lc = f'{tmp}/b.csv'; open(b_lc, 'w').write(open(B).read().replace('C17168', 'C25744', 1))
b100 = f'{tmp}/b100.csv'; open(b100, 'w').write(open(B).read().replace('GRM0335C1H220JA01D', 'GRM0335C1H101JA01D').replace('C76924', 'C76922'))
ctrl = {
    'CPL 删一行': check_set(B, mut(lambda rr: rr.pop(5), 'del'))[0],
    'CPL C54 留 D18 坐标': check_set(B, mut(edit('V4_C54', 2, lambda v: f'{float(v.rstrip("mm")) + .005:.4f}mm'), 'c54'))[0],
    'CPL 转 J_AFE 90°': check_set(B, mut(edit('J_AFE', 4, lambda v: f'{(float(v) + 90) % 360:.1f}'), 'turn'))[0],
    'CPL U2 换面': check_set(B, mut(edit('V4_U2', 3, lambda v: 'Top' if v == 'Bottom' else 'Bottom'), 'side'))[0],
    'BOM 改 R18 C 号': check_set(b_lc, C)[0],
    'BOM 用 D18 文件': check_set(f'{D18}/{B}', C)[0],
    'BOM 差分电容还是 100 pF': check_set(b100, C)[0],
    'CPL 用 D18 文件': check_set(B, f'{D18}/{C}')[0],
    'In2 内容清空': check_zip(zipmut('noin2', lambda n: True, lambda n, d: b'\n'.join(l for l in d.split(b'\n') if not l.startswith(b'X')) if 'In2_Cu' in n else d))[0],
    'Gerber 少 In1': check_zip(zipmut('dropin1', lambda n: 'In1_Cu' not in n, lambda n, d: d))[0],
    'In1 换成 D18 的': check_zip(zipmut('mix', lambda n: True, lambda n, d: open(f'{D18}/gerber/afe-d18-In1_Cu.g1', 'rb').read() if 'In1_Cu' in n else d))[0],
    '丝印换成 D18 的': check_zip(zipmut('silk', lambda n: True, lambda n, d: open(f'{D18}/gerber/afe-d18-F_Silkscreen.gto', 'rb').read() if 'F_Silkscreen' in n else d))[0],
}
fps_save = dict(fps); fps['V4_C54'] = f18['V4_C54']   # 板上 C54 退回 D18 位置
ctrl['板上 C54 没下移'] = board_errors(); fps.clear(); fps.update(fps_save)
fps['V4_C55'] = f18['V4_C55']; ctrl['板上留着一颗 470 pF'] = board_errors(); fps.clear(); fps.update(fps_save)
fps['V4_C72'] = f18['V4_C72']; ctrl['板上 C72 还是 100 pF'] = board_errors(); fps.clear(); fps.update(fps_save)
miss = [n for n, v in ctrl.items() if not v]
print('阳性对照', f'{len(ctrl) - len(miss)}/{len(ctrl)} 判红', ('漏判 ' + str(miss)) if miss else '')
shutil.rmtree(tmp); shutil.rmtree(REF)
sys.exit(1 if bad or miss else 0)
