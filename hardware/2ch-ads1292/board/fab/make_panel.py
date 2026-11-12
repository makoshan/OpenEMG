"""ADS1292 载板完整板：单板工艺边拼板（2026-11-04，照 v12/c08a-tidy-v3-20261031/panel-20261031 同法）。
KiCad 自带 Python 运行：python3 -B make_panel.py
为什么：标准型贴片要求出货 ≥7×7 cm、有工艺边和 MARK；板比 7×7 cm 小，要加工艺边和 MARK，所以做进自己的 Gerber，按「客户资料出货」下单。
为什么一拼一：ESD501DPYRQ1 贴片库只有 19 颗，每块 5 颗，最多 3 块；一拼一才能只贴 3 块。
做法：源板按 blob 取，原地不动，贴片坐标不变。四边各 2 处连接筋（11-12 东边 USB 缺口拿掉，东边成一条直边）；壳内余量东西 0.25、南北 0.55，掰板后连接筋要磨平。
电极手焊，去掉这些焊盘的锡膏开窗，避免钢网在空焊盘上印锡；铜和阻焊不动。"""
import hashlib, json, os, shutil, subprocess, zipfile
import pcbnew as k

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
BLOB, SHA = '05b6710dc606bd9d3527c021fc97eb67994e40da', None   # hardware/2ch-ads1292/board/ads1292-2ch.kicad_pcb（完整板，C08B 式 6 触点：两排大—辅—大，XIAO 经 P44e 和 20P 排线）
PRO = 'hardware/2ch-ads1292/board/ads1292-2ch.kicad_pro'
NAME = 'ads1292-2ch-panel'; ZP = f'{NAME}-gerber-20261104.zip'
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')
GIT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
MM = k.FromMM; mm = k.ToMM
V = lambda x, y: k.VECTOR2I(MM(x), MM(y))

shutil.rmtree('source', ignore_errors=True); os.makedirs('source')
body = subprocess.run(['git', 'cat-file', 'blob', BLOB], cwd=GIT, capture_output=True, check=True).stdout
open('source/ads1292-2ch.kicad_pcb', 'wb').write(body); SHA = hashlib.sha256(body).hexdigest()
shutil.copy(os.path.join(GIT, PRO), 'source/ads1292-2ch.kicad_pro')

# KiCad 坐标 y 向下：板 x 78.45–121.55、y 81.75–118.25（同 C08A 43.1×36.5）；四角 R4.6
L, T, Rr, B, GAP = 78.45, 81.75, 121.55, 118.25, 2.0
X0, X1, Y0, Y1 = 64.9, 135.1, 64.9, 135.1      # 拼后 70.2×70.2
TABS = {'W': [(92, 96), (104, 108)], 'N': [(88, 92), (108, 112)], 'S': [(88, 92), (108, 112)], 'E': [(88, 92), (108, 112)]}
EDGES = {'W': ((L, 86.35), (L, 113.65)), 'N': ((83.05, T), (116.95, T)), 'S': ((83.05, B), (116.95, B)), 'E': ((Rr, 86.35), (Rr, 113.65))}
BITE_D, BITE_P, BITE_OUT = 0.5, 0.75, 0.3      # 邮票孔圆心在板边外 0.3：铜退边 0.3，孔不吃进板内
NO_PASTE = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6']


def build(with_tabs=True):
    b = k.LoadBoard('source/ads1292-2ch.kicad_pcb')
    hit = {}
    for d in b.GetDrawings():
        if d.GetLayer() != k.Edge_Cuts or d.GetShape() != k.SHAPE_T_SEGMENT: continue
        s, e = sorted([(round(mm(d.GetStart().x), 3), round(mm(d.GetStart().y), 3)), (round(mm(d.GetEnd().x), 3), round(mm(d.GetEnd().y), 3))])
        for side, seg in EDGES.items():
            if (s, e) == (tuple(round(v, 3) for v in seg[0]), tuple(round(v, 3) for v in seg[1])): hit[side] = d
    assert set(hit) == set(EDGES), ('没找全四条直板边', hit.keys())
    for d in hit.values(): b.Remove(d)

    def line(a, c):
        s = k.PCB_SHAPE(b, k.SHAPE_T_SEGMENT); s.SetLayer(k.Edge_Cuts); s.SetWidth(MM(0.05)); s.SetStart(V(*a)); s.SetEnd(V(*c)); b.Add(s)

    def split(lo, hi, cuts):   # 区间 [lo,hi] 去掉连接筋后的各段
        out, p = [], lo
        for a, c in (sorted(cuts) if with_tabs else []):
            out.append((p, a)); p = c
        return out + [(p, hi)]

    for a, c in split(86.35, 113.65, TABS['W']): line((L, a), (L, c))
    for a, c in split(83.05, 116.95, TABS['N']): line((a, T), (c, T))
    for a, c in split(83.05, 116.95, TABS['S']): line((a, B), (c, B))
    for a, c in split(86.35, 113.65, TABS['E']): line((Rr, a), (Rr, c))
    # 工艺边内框 x 76.45–123.55、y 79.75–120.25，同样在连接筋处断开
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

    bites = []
    for a, c in TABS['W']: bites += [(L - BITE_OUT, a + 0.4 + i * BITE_P) for i in range(int((c - a - 0.8) / BITE_P) + 1)]
    for a, c in TABS['N']: bites += [(a + 0.4 + i * BITE_P, T - BITE_OUT) for i in range(int((c - a - 0.8) / BITE_P) + 1)]
    for a, c in TABS['S']: bites += [(a + 0.4 + i * BITE_P, B + BITE_OUT) for i in range(int((c - a - 0.8) / BITE_P) + 1)]
    for a, c in TABS['E']: bites += [(Rr + BITE_OUT, a + 0.4 + i * BITE_P) for i in range(int((c - a - 0.8) / BITE_P) + 1)]
    for x, y in bites: npth(x, y, BITE_D)
    tooling = [(X0 + 3.5, Y0 + 3.5), (X1 - 3.5, Y0 + 3.5), (X0 + 3.5, Y1 - 3.5), (X1 - 3.5, Y1 - 3.5)]
    for x, y in tooling: npth(x, y, 1.152)
    marks = [(X0 + 8, Y0 + 7.5), (X1 - 9, Y0 + 7.5), (X0 + 8, Y1 - 7.5)]   # 三点不对称，防反放
    for x, y in marks: fid(x, y, False)   # 只贴顶面，底面不放
    t = k.PCB_TEXT(b); t.SetText('JLCJLCJLCJLC'); t.SetLayer(k.F_SilkS); t.SetPosition(V(100, Y1 - 7.5))
    t.SetTextSize(V(1, 1)); t.SetTextThickness(MM(0.15)); b.Add(t)
    return dict(bites=len(bites), tooling=len(tooling), marks_per_side=len(marks))


def strip_paste(b):
    out = []
    for r in NO_PASTE:
        f = b.FindFootprintByReference(r)
        for p in f.Pads():
            ls = p.GetLayerSet(); ls.RemoveLayer(k.B_Paste if f.IsFlipped() else k.F_Paste); p.SetLayerSet(ls); out.append(f'{r}.{p.GetNumber()}')
    return out


def outlines(b):
    ps = k.SHAPE_POLY_SET(); ok = b.GetBoardPolygonOutlines(ps, True)
    return ok, ps.OutlineCount(), [ps.HoleCount(i) for i in range(ps.OutlineCount())]


# 反例：不加连接筋时，板和工艺边是两块
neg = build(with_tabs=False); n_ok, n_cnt, _ = outlines(neg)
assert n_ok and n_cnt == 2, ('反例应是两块分离外形', n_ok, n_cnt)

b = build(); parts = add_parts(b); stripped = strip_paste(b)
ok, cnt, holes = outlines(b)
assert ok and cnt == 1, ('拼板外形不是一整块', ok, cnt)
bb = b.GetBoardEdgesBoundingBox()
size = (round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2))
assert size[0] >= 70 and size[1] >= 70, ('拼后小于 7×7 cm', size)

# 原板内容逐项不变：器件位置/角度/面、走线、过孔、铺铜
src = k.LoadBoard('source/ads1292-2ch.kicad_pcb')
key_fp = lambda bd: sorted((f.GetReference(), f.GetPosition().x, f.GetPosition().y, round(f.GetOrientationDegrees(), 3), f.IsFlipped()) for f in bd.GetFootprints() if f.GetReference() != 'PANEL')
key_tr = lambda bd: sorted((t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetname()) for t in bd.GetTracks())
key_zn = lambda bd: sorted((z.GetNetname(), z.GetLayerSet().FmtHex(), sum(z.GetFilledPolysList(l).Area() for l in z.GetLayerSet().Seq() if z.HasFilledPolysForLayer(l))) for z in bd.Zones())
assert key_fp(src) == key_fp(b) and key_tr(src) == key_tr(b) and key_zn(src) == key_zn(b), '原板内容被改动'

shutil.copy('source/ads1292-2ch.kicad_pro', f'{NAME}.kicad_pro')
b.Save(f'{NAME}.kicad_pcb')

shutil.rmtree('gerber', ignore_errors=True); os.makedirs('gerber')
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', 'gerber/', f'{NAME}.kicad_pcb'], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th', '-o', 'gerber/', f'{NAME}.kicad_pcb'], check=True, capture_output=True)
with zipfile.ZipFile(ZP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir('gerber')): z.write(f'gerber/{f}', f)   # 平铺

json.dump(dict(source=dict(blob=BLOB, sha256=SHA), panel_mm=size, outline=dict(pieces=cnt, holes=holes, negative_without_tabs=n_cnt), tabs=TABS, **parts,
               no_paste=stripped, zip=ZP, zip_sha256=hashlib.sha256(open(ZP, 'rb').read()).hexdigest(),
               kicad=subprocess.run([CLI, 'version'], capture_output=True, text=True).stdout.strip()),
          open('panel.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(json.load(open('panel.json')), ensure_ascii=False))
