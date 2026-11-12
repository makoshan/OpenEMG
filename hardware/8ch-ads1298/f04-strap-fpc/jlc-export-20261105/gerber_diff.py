"""嘉立创导出的 Gerber 和下单包 Gerber 比几何：两边并成多边形，按板框中心对齐，算异或面积。
用法：uvx --with gerbonara --with shapely python gerber_diff.py <下单包目录> <嘉立创 gerber 目录> <输出.json>"""
import json, math, sys
from pathlib import Path
from gerbonara import GerberFile
from gerbonara.graphic_primitives import ArcPoly, Circle, Line, Rectangle
from gerbonara.utils import MM
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

def shape(p):
    if isinstance(p, Line):
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, 4)
    if isinstance(p, Circle):
        return Point(p.x, p.y).buffer(p.r, 8)
    if isinstance(p, Rectangle):
        return affinity.rotate(box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2), p.rotation, origin=(p.x, p.y), use_radians=True)
    if isinstance(p, ArcPoly):
        pts = list(p.outline)
        return Polygon(pts).buffer(0) if len(pts) >= 3 else None
    return None

def load(f):
    dark, skip = [], 0
    g = GerberFile.open(f)
    for o in g.objects:
        for p in o.to_primitives(unit=MM):
            s = shape(p)
            if s is None:
                skip += 1
            elif getattr(p, 'polarity_dark', True):
                dark.append(s)
    return unary_union(dark), skip

src, eda = Path(sys.argv[1]), Path(sys.argv[2])
so, _ = load(src / 'fpc-f04-Edge_Cuts.gm1'); eo, _ = load(eda / 'Gerber_BoardOutlineLayer.GKO')
sb, eb = so.bounds, eo.bounds
dx, dy = (sb[0] + sb[2] - eb[0] - eb[2]) / 2, (sb[1] + sb[3] - eb[1] - eb[3]) / 2
res = {'板框': {'源尺寸': [round(sb[2] - sb[0], 3), round(sb[3] - sb[1], 3)], '嘉立创尺寸': [round(eb[2] - eb[0], 3), round(eb[3] - eb[1], 3)]}}
for name, a, b in [('铜', 'fpc-f04-F_Cu.gtl', 'Gerber_TopLayer.GTL'), ('覆盖膜开窗', 'fpc-f04-F_Mask.gts', 'Gerber_TopSolderMaskLayer.GTS'),
                   ('钢网', 'fpc-f04-F_Paste.gtp', 'Gerber_TopPasteMaskLayer.GTP'), ('丝印', 'fpc-f04-F_Silkscreen.gto', 'Gerber_TopSilkscreenLayer.GTO'),
                   ('板框线', 'fpc-f04-Edge_Cuts.gm1', 'Gerber_BoardOutlineLayer.GKO')]:
    A, sa = load(src / a); B, sk = load(eda / b)
    B = affinity.translate(B, dx, dy)
    x = A.symmetric_difference(B)
    res[name] = dict(源面积=round(A.area, 4), 嘉立创面积=round(B.area, 4), 异或面积=round(x.area, 4), 异或占比=round(x.area / max(A.area, 1e-9), 5),
                     厚于0p02mm的差异面积=round(x.buffer(-0.01).area, 4), 跳过图元=[sa, sk])
Path(sys.argv[3]).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
