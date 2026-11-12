"""从保存后的板、钻孔和 zip 回读；原板铜、元件、钢网、thermal 不能被工艺边改动。KiCad Python 运行：python3 -B check_panel.py"""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
import numpy as np
import pcbnew as k
D = Path(__file__).resolve().parent; sys.path.insert(0, str(D.parent))
import gerber_read as G
BASE_HASH = '7615e0774d70b3a3cec0f72c6338ec9b75ea9a89ac813f5cdd7e58b89b98c633'   # d20-silk
CLI = os.environ.get('KICAD_CLI', 'kicad-cli'); NAME = 'c08b-afe-d20-8ch-panel'; BASE = 'afe-d20-8ch'
src = k.LoadBoard(str(D / f'../source/{BASE}.kicad_pcb')); p = k.LoadBoard(str(D / f'{NAME}.kicad_pcb'))
meta = json.loads((D / 'panel.json').read_text())
G.THERMAL = {r: n for r, n in G.THERMAL.items() if r not in {'V4_C71', 'V4_C119', 'V4_C124', 'V4_C55', 'V4_C117', 'V4_C108', 'V4_C120', 'V4_C118'}}   # D20 删了这 3 颗
MOVED = ['V4_C54', 'J_AFE', 'R801', 'R803', 'R804', 'R805', 'R806', 'R807', 'R808', 'V4_R18']   # D15 以来动过的件


def pads(f):
    return sorted((q.GetNumber(), q.GetPosition().x, q.GetPosition().y, q.GetSize().x, q.GetSize().y, q.GetOrientationDegrees(), q.GetShape(), q.GetLayerSet().FmtHex(), q.GetNetname(), q.GetDrillSize().x, q.GetDrillSize().y, q.GetAttribute(), q.GetRoundRectRadiusRatio(),
                   q.GetLocalZoneConnection(), q.GetLocalThermalSpokeWidthOverride(), q.GetLocalThermalGapOverride(), q.GetThermalSpokeAngleDegrees()) for q in f.Pads())
def footprints(b):
    return {f.GetReference(): (f.GetValue(), f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees(), f.IsFlipped(), pads(f)) for f in b.GetFootprints() if f.GetReference() != 'PANEL'}
def tracks(b):
    return sorted((t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetname(), t.GetWidth() if t.GetClass() != 'PCB_VIA' else t.GetWidth(k.F_Cu), t.GetDrillValue() if t.GetClass() == 'PCB_VIA' else 0) for t in b.GetTracks())
def polygon(ps):
    out = []
    for i in range(ps.OutlineCount()):
        chains = [ps.COutline(i)] + [ps.CHole(i, h) for h in range(ps.HoleCount(i))]
        out.append([[(c.CPoint(j).x, c.CPoint(j).y) for j in range(c.PointCount())] for c in chains])
    return out
def zones(b):
    return sorted((z.GetNetname(), z.GetLayerSet().FmtHex(), str(polygon(z.Outline())), str([(l, polygon(z.GetFilledPolysList(l))) for l in z.GetLayerSet().Seq() if z.HasFilledPolysForLayer(l)])) for z in b.Zones())
assert footprints(src) == footprints(p)
assert tracks(src) == tracks(p)
assert zones(src) == zones(p), '原板铺铜图形变化'
outline = k.SHAPE_POLY_SET(); assert p.GetBoardPolygonOutlines(outline, True) and outline.OutlineCount() == 1
box = outline.BBox(); assert (box.GetWidth(), box.GetHeight()) == (70200000, 70200000)
panel = p.FindFootprintByReference('PANEL'); npth = [q for q in panel.Pads() if q.GetAttribute() == k.PAD_ATTRIB_NPTH]; marks = [q for q in panel.Pads() if q.GetAttribute() == k.PAD_ATTRIB_SMD]
assert len(npth) == 35 and len(marks) == 3
assert sum(q.IsOnLayer(k.F_Cu) for q in marks) == 3 and sum(q.IsOnLayer(k.B_Cu) for q in marks) == 0
assert all(not q.IsOnLayer(k.F_Paste) and not q.IsOnLayer(k.B_Paste) for q in marks)
assert meta['source_sha256'] == BASE_HASH, '拼板不是 D20 派生'
def stale_panel_caught():
    return json.loads((D / '../../fab-d18-20261108/panel/panel.json').read_text())['source_sha256'] != BASE_HASH
assert stale_panel_caught()

n_via = sum(1 for t in src.GetTracks() if t.GetClass() == 'PCB_VIA'); n_np = sum(1 for f in src.GetFootprints() for q in f.Pads() if q.GetAttribute() == k.PAD_ATTRIB_NPTH)
def holes(text): return len(re.findall(r'^X[-\d.]+Y[-\d.]+', text, re.M))
z = zipfile.ZipFile(D / f'{NAME}-gerber.zip'); names = z.namelist(); assert len(names) == 14 and all('/' not in n for n in names)
job = json.loads(z.read(next(n for n in names if n.endswith('gbrjob')))); assert len(job['FilesAttributes']) == 11
pth = z.read(f'{NAME}-PTH.drl').decode(); np_ = z.read(f'{NAME}-NPTH.drl').decode()
assert holes(pth) == n_via and holes(np_) == n_np + 35
broken = re.sub(r'^X[-\d.]+Y[-\d.]+\n', '', np_, count=1, flags=re.M); assert holes(broken) != n_np + 35
assert meta['outline']['negative_without_tabs'] == 2

# 回读：铺铜 = 板内填充，四层都比；thermal、钢网、阻焊同单板
txt = lambda tail: z.read(f'{NAME}-{tail}').decode()
g = {n: G.parse(txt(f)) for n, f in (('F', 'F_Cu.gtl'), ('I1', 'In1_Cu.g1'), ('I2', 'In2_Cu.g2'), ('B', 'B_Cu.gbl'))}
for n, ly in (('F', k.F_Cu), ('I1', k.In1_Cu), ('I2', k.In2_Cu), ('B', k.B_Cu)):
    e = G.fill_errors(g[n], G.board_fill(k, p, ly)); assert not e, (n, e)
gp = G.gnd_pads(k, p); e, thermal = G.thermal_errors(g, gp); assert not e, e
order = [*G.THERMAL, G.SOLID]; G.png(str(D / 'thermal-readback.png'), [(r, g[gp[r]['side']], gp[r]) for r in order])
opens = {}
for tail, ly in (('F_Paste.gtp', k.F_Paste), ('B_Paste.gbp', k.B_Paste), ('F_Mask.gts', k.F_Mask), ('B_Mask.gbs', k.B_Mask)):
    e, opens[tail] = G.open_errors(k, p, G.parse(txt(tail)), ly); assert not e, (tail, e[:3])

# 邮票孔孔边到四层铜的最小净距，从 Gerber 量
def clear(x, y, r):
    t = np.arange(-1.2, 1.2, .01); xx, yy = np.meshgrid(t + x, t + y); pts = np.c_[xx.ravel(), yy.ravel()]; d = np.hypot(pts[:, 0] - x, pts[:, 1] - y)
    return min((d[G.dark(gi, pts)].min(initial=9) - r) for gi in g.values())
bite = [q for q in npth if abs(k.ToMM(q.GetDrillSize().x) - .5) < 1e-6]; assert len(bite) == 31
gaps = [clear(k.ToMM(q.GetPosition().x), -k.ToMM(q.GetPosition().y), .25) for q in bite]; assert min(gaps) >= .3, ('邮票孔离铜太近', min(gaps))

# 筋和动过的件：外包到筋矩形的最小距离
tabs = meta['tabs']; R = [(-2, a, 0, c) for a, c in tabs['W']] + [(a, -2, c, 0) for a, c in tabs['N']] + [(a, 36.5, c, 38.5) for a, c in tabs['S']] + [(43.1, a, 45.1, c) for a, c in tabs['E']]
def dist(bb, r):
    x0, y0, x1, y1 = k.ToMM(bb.GetLeft()), k.ToMM(bb.GetTop()), k.ToMM(bb.GetRight()), k.ToMM(bb.GetBottom())
    return float(np.hypot(max(r[0] - x1, x0 - r[2], 0), max(r[1] - y1, y0 - r[3], 0)))
near = min(dist(p.FindFootprintByReference(r).GetBoundingBox(), t) for r in MOVED for t in R); assert near > 1, near

# 反例：撤掉 thermal 属性重铺，拼板回读必须红；并证明查的是 Gerber，不是板子属性
tmp = tempfile.mkdtemp(); lost = f'{tmp}/{NAME}.kicad_pcb'; text, n = re.subn(r'\(zone_connect 1\)\s*', '', (D / f'{NAME}.kicad_pcb').read_text()); assert n == len(G.THERMAL)
open(lost, 'w').write(text); [shutil.copy(D / f'{NAME}.{e}', tmp) for e in ('kicad_pro', 'kicad_dru')]
lb = k.LoadBoard(lost); k.ZONE_FILLER(lb).Fill(lb.Zones()); lb.Save(lost)
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu', '-o', tmp + '/', lost], check=True, capture_output=True)
lc = {s: G.parse(open(f'{tmp}/{NAME}-{f}').read()) for s, f in (('F', 'F_Cu.gtl'), ('B', 'B_Cu.gbl'))}
lost_bad = G.thermal_errors(lc, gp)[0]; assert lost_bad, '丢 thermal 的反例没红'
assert G.fill_errors(lc['F'], G.board_fill(k, p, k.F_Cu)), '重铺的反例没红'
shutil.rmtree(tmp)

# zip 必须等于拼板重导：丝印、板框、走线、MARK 被改都要红（复核破坏 4 处本来查不到）；只忽略时间戳和注释行
assert hashlib.sha256((D / f'{NAME}-gerber.zip').read_bytes()).hexdigest() == meta['zip_sha256'], 'zip 和 panel.json 记录不符'
tmp = tempfile.mkdtemp(); re_dir = tmp + '/g/'; os.makedirs(re_dir); PCB = str(D / f'{NAME}.kicad_pcb')
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts', '--subtract-soldermask', '-o', re_dir, PCB], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th', '-o', re_dir, PCB], check=True, capture_output=True)
def norm(s):
    return [l for l in s.splitlines() if not l.startswith(('G04', '%TF.CreationDate', '; ', '%TF.ProjectId', '%TF.GenerationSoftware'))]
def zip_diff(read):
    return [n for n in names if not n.endswith('gbrjob') and norm(read(n)) != norm(open(re_dir + n, errors='replace').read())]
rd = lambda n: z.read(n).decode(errors='replace')
assert not zip_diff(rd), ('zip 和拼板重导不同', zip_diff(rd))
silk = f'{NAME}-F_Silkscreen.gto'
assert silk in zip_diff(lambda n: rd(n).replace('D03*', 'D02*', 1) if n == silk else rd(n)), '改丝印的反例没红'
edge = f'{NAME}-Edge_Cuts.gm1'
assert edge in zip_diff(lambda n: '\n'.join(rd(n).splitlines()[:-40]) if n == edge else rd(n)), '删板框的反例没红'
cu = f'{NAME}-F_Cu.gtl'
assert cu in zip_diff(lambda n: '\n'.join(l for i, l in enumerate(rd(n).splitlines()) if i % 500) if n == cu else rd(n)), '删走线的反例没红'
shutil.rmtree(tmp)

# DRC 现场重跑，不读存档（11-09 复核：加一条横穿走线的铜线、更新 zip 哈希后，读存档的门照样通过）
for name, extra in (('drc.json', []), ('drc-refill.json', ['--refill-zones'])):
    tmpd = tempfile.mkdtemp()
    for e in ('kicad_pcb', 'kicad_pro', 'kicad_dru'): shutil.copy(D / f'{NAME}.{e}', tmpd)
    (Path(tmpd) / 'fp-lib-table').write_text((D / 'fp-lib-table').read_text().replace('${KIPRJMOD}/../../d15/C08A.pretty', str((D / '../../d15/C08A.pretty').resolve())).replace('${KIPRJMOD}/panel.pretty', str((D / 'panel.pretty').resolve())))
    subprocess.run([CLI, 'pcb', 'drc', *extra, '--severity-all', '--format', 'json', '-o', str(D / name), f'{tmpd}/{NAME}.kicad_pcb'], check=True, capture_output=True)
    shutil.rmtree(tmpd)
    j = json.loads((D / name).read_text())
    v = [x for x in j['violations'] if x['type'] not in ('lib_footprint_issues', 'lib_footprint_mismatch')]   # 板上封装 vs 库的提示，理由见 ../check_fab.py
    assert not j['unconnected_items'] and not v and not j['schematic_parity'], (name, v[:2])
r = dict(board_sha256=hashlib.sha256((D / f'{NAME}.kicad_pcb').read_bytes()).hexdigest(), source_sha256=BASE_HASH, original_footprints_pads_tracks_zones_equal=True, panel_mm=[70.2, 70.2], connected_pieces=1, negative_without_tabs_pieces=2, pth=n_via, npth=n_np + 35, marks_per_side=3,
         missing_drill_control_caught=True, gerber_fill_equal_board=True, thermal=dict(order=order, pads=thermal), thermal_lost_control=lost_bad[:2], stale_d18_panel_control=True, openings=opens,
         mouse_bite_edge_to_copper_min_mm=round(min(gaps), 3), moved_parts_to_tab_min_mm=round(near, 2), drc_errors=0, drc_warnings_except_lib_table=0, drc_unconnected=0)
(D / 'check-result.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n')
print({x: v for x, v in r.items() if x != 'thermal'})
