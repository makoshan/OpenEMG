"""AFE D20N（四角缺口）一拼一工艺边候选；保持原板坐标，单独导出，不覆盖单板包。几何沿用 D15/D17。"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
import pcbnew as k

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
BASE = 'afe-d20n-8ch'; SRC = f'../source/{BASE}.kicad_pcb'
NAME = 'c08b-afe-d20n-8ch-panel'; ZP = f'{NAME}-gerber.zip'
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')
assert hashlib.sha256(open(SRC,'rb').read()).hexdigest()=='1d5dd19ae77378b8bb4e1ebcf8e4ea27b224799f766247868c5bf966470d44e3', '源板更新，须重核连接筋'
MM = k.FromMM; mm = k.ToMM
V = lambda x, y: k.VECTOR2I(MM(x), MM(y))

# AFE为圆角矩形；连接筋避开北侧两FPC及东侧J_AFE，坐标由独立只读调查选择。
L, T, Rr, B, GAP = 0.0, 0.0, 43.1, 36.5, 2.0
X0, X1, Y0, Y1 = -13.55, 56.65, -16.85, 53.35
TABS = {'W': [(10,14),(24,28)], 'N': [(5.5,8.5),(34.5,37.5)], 'S': [(10,14),(22,26)], 'E': [(6,10)]}
EDGES = {'W': ((0,3),(0,33.5)), 'N': ((3,0),(40.1,0)), 'S': ((3,36.5),(40.1,36.5)), 'E': ((43.1,3),(43.1,33.9))}   # 方缺口板的四条直边
BITE_D, BITE_P, BITE_OUT = 0.5, 0.75, 0.3


def build(with_tabs=True):
    b = k.LoadBoard(SRC)
    hit = {}
    for d in b.GetDrawings():
        if d.GetLayer() != k.Edge_Cuts or d.GetShape() != k.SHAPE_T_SEGMENT: continue
        s, e = sorted([(round(mm(d.GetStart().x), 3), round(mm(d.GetStart().y), 3)), (round(mm(d.GetEnd().x), 3), round(mm(d.GetEnd().y), 3))])
        for side, seg in EDGES.items():
            if (s, e) == tuple(sorted(tuple(round(v, 3) for v in p) for p in seg)): hit[side] = d
    assert set(hit) == set(EDGES), ('没找全直板边', hit.keys())
    for d in hit.values(): b.Remove(d)

    def line(a, c):
        s = k.PCB_SHAPE(b, k.SHAPE_T_SEGMENT); s.SetLayer(k.Edge_Cuts); s.SetWidth(MM(0.05)); s.SetStart(V(*a)); s.SetEnd(V(*c)); b.Add(s)

    def split(lo, hi, cuts):   # 区间 [lo,hi] 去掉连接筋后的各段
        out, p = [], lo
        for a, c in (sorted(cuts) if with_tabs else []):
            out.append((p, a)); p = c
        return out + [(p, hi)]

    for a,c in split(3,33.5,TABS['W']): line((L,a),(L,c))
    for a,c in split(3,40.1,TABS['N']): line((a,T),(c,T))
    for a,c in split(3,40.1,TABS['S']): line((a,B),(c,B))
    for a,c in split(3,33.9,TABS['E']): line((Rr,a),(Rr,c))
    # 工艺边内框，在连接筋处断开
    for a, c in split(T - GAP, B + GAP, TABS['W']): line((L - GAP, a), (L - GAP, c))
    for a, c in split(L - GAP, Rr + GAP, TABS['N']): line((a, T - GAP), (c, T - GAP))
    for a, c in split(L - GAP, Rr + GAP, TABS['S']): line((a, B + GAP), (c, B + GAP))
    for a, c in split(T - GAP, B + GAP, TABS['E']): line((Rr + GAP, a), (Rr + GAP, c))
    if with_tabs:   # 连接筋两侧边
        for a, c in TABS['W']: line((L - GAP, a), (L, a)); line((L - GAP, c), (L, c))
        for a, c in TABS['N']: line((a, T - GAP), (a, T)); line((c, T - GAP), (c, T))
        for a, c in TABS['S']: line((a, B), (a, B + GAP)); line((c, B), (c, B + GAP))
        for a, c in TABS['E']: line((Rr, a), (Rr + GAP, a)); line((Rr, c), (Rr + GAP, c))
    for a, c in [((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))]: line(a, c)
    return b


def add_parts(b):
    fp = k.FOOTPRINT(b); fp.SetReference('PANEL'); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    fp.SetFPID(k.LIB_ID('panel', 'rails')); fp.SetAttributes(k.FP_EXCLUDE_FROM_BOM | k.FP_EXCLUDE_FROM_POS_FILES | k.FP_BOARD_ONLY); b.Add(fp)
    n = [0]

    def npth(x, y, d):
        p = k.PAD(fp); p.SetAttribute(k.PAD_ATTRIB_NPTH); p.SetShape(k.PAD_SHAPE_CIRCLE)
        p.SetSize(V(d, d)); p.SetDrillSize(V(d, d)); p.SetLayerSet(k.PAD.UnplatedHoleMask()); p.SetPosition(V(x, y)); p.SetNumber(''); fp.Add(p)

    def fid(x, y, back):   # MARK：1 mm 铜点，2 mm 开窗
        p = k.PAD(fp); p.SetAttribute(k.PAD_ATTRIB_SMD); p.SetShape(k.PAD_SHAPE_CIRCLE); p.SetSize(V(1, 1))
        ls = k.LSET(); ls.AddLayer(k.B_Cu if back else k.F_Cu); ls.AddLayer(k.B_Mask if back else k.F_Mask)
        p.SetLayerSet(ls); p.SetLocalSolderMaskMargin(MM(0.5)); p.SetPosition(V(x, y)); n[0] += 1; p.SetNumber(f'M{n[0]}'); fp.Add(p)
        # MARK 周围要留空，courtyard 是真实范围；有了它 DRC 不报 missing_courtyard，规则不用动
        c = k.PCB_SHAPE(fp, k.SHAPE_T_CIRCLE); c.SetLayer(k.B_CrtYd if back else k.F_CrtYd); c.SetWidth(MM(0.05)); c.SetCenter(V(x, y)); c.SetEnd(V(x + 1.25, y)); fp.Add(c)

    def row(a, c):   # 孔排在筋中间，两端余量相等
        n = int((c - a - 0.8) / BITE_P) + 1; s = a + (c - a - (n - 1) * BITE_P) / 2
        return [s + i * BITE_P for i in range(n)]

    bites = []
    for a, c in TABS['W']: bites += [(L - BITE_OUT, v) for v in row(a, c)]
    for a, c in TABS['N']: bites += [(v, T - BITE_OUT) for v in row(a, c)]
    for a, c in TABS['S']: bites += [(v, B + BITE_OUT) for v in row(a, c)]
    for a, c in TABS['E']: bites += [(Rr + BITE_OUT, v) for v in row(a, c)]
    for x, y in bites: npth(x, y, BITE_D)
    tooling = [(X0 + 3.5, Y0 + 3.5), (X1 - 3.5, Y0 + 3.5), (X0 + 3.5, Y1 - 3.5), (X1 - 3.5, Y1 - 3.5)]
    for x, y in tooling: npth(x, y, 1.152)
    marks = [(X0 + 8, Y0 + 7.5), (X1 - 9, Y0 + 7.5), (X0 + 8, Y1 - 7.5)]   # 三点不对称，防反放
    for x, y in marks: fid(x, y, False)   # 单面贴，只放正面 MARK，背面保持 0 开窗
    t = k.PCB_TEXT(b); t.SetText('JLCJLCJLCJLC'); t.SetLayer(k.F_SilkS); t.SetPosition(V(23, Y1 - 7.5))
    t.SetTextSize(V(1, 1)); t.SetTextThickness(MM(0.15)); b.Add(t)
    return dict(bites=len(bites), tooling=len(tooling), marks_per_side=len(marks))


def outlines(b):
    ps = k.SHAPE_POLY_SET(); ok = b.GetBoardPolygonOutlines(ps, True)
    return ok, ps.OutlineCount(), [ps.HoleCount(i) for i in range(ps.OutlineCount())]


# 反例：不加连接筋时，板和工艺边是两块
neg = build(with_tabs=False); n_ok, n_cnt, _ = outlines(neg)
assert n_ok and n_cnt == 2, ('反例应是两块分离外形', n_ok, n_cnt)

b = build(); parts = add_parts(b); stripped = []
ok, cnt, holes = outlines(b)
assert ok and cnt == 1, ('拼板外形不是一整块', ok, cnt)
outline_poly = k.SHAPE_POLY_SET(); assert b.GetBoardPolygonOutlines(outline_poly, True)
bb = outline_poly.BBox()  # 量板框中心线；图形包围盒会把0.05mm笔画也算进板尺寸
size = (round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2))
assert size[0] >= 70 and size[1] >= 70, ('拼后小于 7×7 cm', size)

# 原板内容逐项不变：器件位置/角度/面、走线、过孔、铺铜
src = k.LoadBoard(SRC)
key_fp = lambda bd: sorted((f.GetReference(), f.GetPosition().x, f.GetPosition().y, round(f.GetOrientationDegrees(), 3), f.IsFlipped()) for f in bd.GetFootprints() if f.GetReference() != 'PANEL')
key_tr = lambda bd: sorted((t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetname()) for t in bd.GetTracks())
key_zn = lambda bd: sorted((z.GetNetname(), z.GetLayerSet().FmtHex(), sum(z.GetFilledPolysList(l).Area() for l in z.GetLayerSet().Seq() if z.HasFilledPolysForLayer(l))) for z in bd.Zones())
assert key_fp(src) == key_fp(b) and key_tr(src) == key_tr(b) and key_zn(src) == key_zn(b), '原板内容被改动'

shutil.copy(f'../source/{BASE}.kicad_pro', f'{NAME}.kicad_pro'); shutil.copy(f'../source/{BASE}.kicad_dru', f'{NAME}.kicad_dru')
b.Save(f'{NAME}.kicad_pcb')
os.makedirs('panel.pretty',exist_ok=True)
k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(os.path.abspath('panel.pretty'),b.FindFootprintByReference('PANEL'))
from pathlib import Path
Path('fp-lib-table').write_text('(fp_lib_table (lib (name "C08A")(type "KiCad")(uri "${KIPRJMOD}/../../d15/C08A.pretty")(options "")(descr "")) (lib (name "panel")(type "KiCad")(uri "${KIPRJMOD}/panel.pretty")(options "")(descr "")))')

shutil.rmtree('gerber', ignore_errors=True); os.makedirs('gerber')
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', 'gerber/', f'{NAME}.kicad_pcb'], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th', '-o', 'gerber/', f'{NAME}.kicad_pcb'], check=True, capture_output=True)
with zipfile.ZipFile(ZP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir('gerber')): z.write(f'gerber/{f}', f)   # 平铺

json.dump(dict(source_sha256=hashlib.sha256(open(SRC, 'rb').read()).hexdigest(), panel_mm=size, outline=dict(pieces=cnt, holes=holes, negative_without_tabs=n_cnt), tabs=TABS, **parts,
               no_paste=stripped, zip=ZP, zip_sha256=hashlib.sha256(open(ZP, 'rb').read()).hexdigest(),
               kicad=subprocess.run([CLI, 'version'], capture_output=True, text=True).stdout.strip()), open('panel.json', 'w'), ensure_ascii=False, indent=1)
# 两口径 DRC；重铺只在副本上跑
for out, extra in (('drc.json', []), ('drc-refill.json', ['--refill-zones'])):
    src = f'{NAME}.kicad_pcb'
    if extra:
        d = tempfile.mkdtemp()
        for e in ('kicad_pcb', 'kicad_pro', 'kicad_dru'): shutil.copy(f'{NAME}.{e}', d)
        Path(f'{d}/fp-lib-table').write_text(Path('fp-lib-table').read_text().replace('${KIPRJMOD}/../../d15/C08A.pretty', os.path.abspath('../../d15/C08A.pretty')).replace('${KIPRJMOD}/panel.pretty', os.path.abspath('panel.pretty')))
        src = f'{d}/{NAME}.kicad_pcb'
    subprocess.run([CLI, 'pcb', 'drc', *extra, '--severity-all', '--format', 'json', '-o', os.path.abspath(out), src], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'svg', '--layers', 'F.Cu,F.Mask,F.Silkscreen,Edge.Cuts', '--mode-single', '--fit-page-to-board', '--exclude-drawing-sheet', '-o', 'panel-top.svg', f'{NAME}.kicad_pcb'], check=True, capture_output=True)
print('拼板', size, '外形', cnt, '块', holes, '洞 | 邮票孔', parts['bites'], '| 去锡膏', len(stripped))
