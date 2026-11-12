"""KiCad Python：把载板顶面焊盘、器件位号、板框导成 JSON（设计坐标 mm：x = kx−100，y = 100−ky），给 make_paper.py 画纸样。"""
import json, sys
from pathlib import Path
import pcbnew as k
R = Path(__file__).resolve().parent
b = k.LoadBoard(str(R.parents[2] / '2ch-ads1292/board/ads1292-2ch.kicad_pcb'))
xy = lambda x, y: (round(k.ToMM(x) - 100, 3), round(100 - k.ToMM(y), 3))
def polys(ps):
    return [[xy(o.CPoint(j).x, o.CPoint(j).y) for j in range(o.PointCount())] for o in (ps.Outline(i) for i in range(ps.OutlineCount()))]
out = {'pads': [], 'refs': [], 'edge': []}
for f in b.GetFootprints():
    p = f.GetPosition(); out['refs'].append({'ref': f.GetReference(), 'at': xy(p.x, p.y), 'back': f.IsFlipped()})
    for q in f.Pads():
        for side, L in (('F', k.F_Cu), ('B', k.B_Cu)):
            if q.IsOnLayer(L):
                ps = k.SHAPE_POLY_SET(); q.TransformShapeToPolygon(ps, L, 0, 5000, k.ERROR_INSIDE)
                out['pads'].append({'ref': f.GetReference(), 'side': side, 'net': q.GetNetname(), 'polys': polys(ps)})
ps = k.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps, False)
out['edge'] = polys(ps) + [[xy(ps.Hole(i, h).CPoint(j).x, ps.Hole(i, h).CPoint(j).y) for j in range(ps.Hole(i, h).PointCount())] for i in range(ps.OutlineCount()) for h in range(ps.HoleCount(i))]
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else R / 'board.json', 'w'))
print('焊盘', len(out['pads']), '件', len(out['refs']), '板框环', len(out['edge']))
