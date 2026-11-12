"""F04 8通道腕带单排几何原语（自包含整理自 E14..E23，消除历史迭代目录链）。"""
from __future__ import annotations
import copy
import math
from functools import lru_cache
from build123d import Align, Box, Color, Compound, Cylinder, Plane, Polygon, Pos, Rot, Sphere, Vertex, extrude

TRAVEL = 0.22
BOARD_T = 0.106
SPRING_H = 1.20
SPRING_Z = 1.256
HEAD_Z = 2.456
GUIDE_Z = 1.10
GUIDE_BOTTOM_LIP = 2.756
GUIDE_TOP = 3.356
BODY = 3.706
DISC_D, DISC_T, POCKET_D, APERTURE_D, LIP_T, BOSS_D = 9.0, 1.2, 9.4, 8.0, 0.4, 11.0
DISC_FRONT = HEAD_Z + DISC_T


def box(w: float, l: float, h: float, x: float = 0.0, y: float = 0.0, z: float = 0.0):
    return Pos(x, y, z) * Box(w, l, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def cyl(d: float, h: float, y: float = 0.0, z: float = 0.0, x: float = 0.0):
    return Pos(x, y, z) * Cylinder(d / 2.0, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def circle(x: float, y: float, d: float, r_unused: float, h: float, z: float = 1.0):
    return Pos(x, y, z) * Cylinder(d / 2.0, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def plate(w: float, l: float, h: float, z: float = 0.0):
    return box(w, l, h, 0.0, 0.0, z)


def named(s, label: str, rgb: tuple[float, float, float]):
    s.label = label
    s.color = Color(*rgb)
    return s


def overlap(a, b) -> float:
    q = a.intersect(b)
    if not q:
        return 0.0
    return q.volume if hasattr(q, "volume") else sum(x.volume for x in q)


def clear(parts: list) -> None:
    for i, a in enumerate(parts):
        assert a.is_valid
        aa = a.bounding_box()
        for b in parts[i + 1:]:
            bb = b.bounding_box()
            if any(getattr(aa.max, k) <= getattr(bb.min, k) + 1e-8 or getattr(bb.max, k) <= getattr(aa.min, k) + 1e-8 for k in "XYZ"):
                continue
            assert overlap(a, b) < 1e-6, (a.label, b.label, overlap(a, b))


def pose(i: int, angle: float):
    pitch = 19.6
    if angle == 0:
        return Pos(98 + i * pitch, 0, 0)
    t = math.radians(angle) * i
    r = pitch / math.radians(angle)
    return Pos(98 + r * math.sin(t), 0, -0.75 + r * (1 - math.cos(t))) * Rot(0, -i * angle, 0) * Pos(0, 0, 0.75)


def bridge(i: int, angle: float, y: float, w: float, z: float, h: float, label: str, color: tuple[float, float, float]):
    p0 = Pos(-98, 0, 0) * pose(i, angle)
    p1 = Pos(-98, 0, 0) * pose(i + 1, angle)
    pts = [(p * Vertex(x, 0, v)).center() for p, x, v in [(p0, 7.8, z), (p1, -7.8, z), (p1, -7.8, z + h), (p0, 7.8, z + h)]]
    f = Pos(0, y + w, 0) * (Plane.XZ * Polygon(*[(v.X, v.Z) for v in pts], align=None))
    return named(extrude(f, amount=w, dir=(0, -1, 0)), label, color)


def head(stroke: float = 0.0):
    return disc(0.0, stroke)


def passage(shape):
    for x in (-6.5, 6.5):
        shape -= box(6, 8, 0.8, x=x, z=0.85)
    return shape


@lru_cache(None)
def fixed(rld: bool = False):
    frame = passage(plate(15.6, 28, 3.006) - plate(12.4, 25.4, 6, 0.6))
    support = plate(12, 25, 0.4, 0.6)
    for y in ([-6.5] if rld else [-6.5, 6.5]):
        for x in (-3.9, 3.9):
            support += circle(x, y, 1.0, 0.5, HEAD_Z - TRAVEL - 1.0)
    guide = plate(12, 25, 2.256, 1.1) - plate(10.8, 23.8, 1.656, 1.1)
    for y in ([-6.5] if rld else [-6.5, 6.5]):
        guide -= cyl(POCKET_D, 0.64, y, 2.736)
        cap = cyl(BOSS_D, DISC_FRONT + LIP_T - GUIDE_TOP, y, GUIDE_TOP)
        cap -= cyl(POCKET_D, DISC_FRONT - (GUIDE_TOP - 0.01), y, GUIDE_TOP - 0.01)
        cap -= cyl(APERTURE_D, LIP_T + 0.04, y, DISC_FRONT)
        guide += cap
    guide = passage(guide)
    glue = passage(plate(12, 25, 0.1, 1.0) - plate(10.8, 23.8, 0.12, 0.99))
    return [
        named(frame, "TPU carrier28 floor0.6", (0.09, 0.11, 0.12)),
        named(support, "PETG support OUTSIDE FPC stops", (0.36, 0.43, 0.44)),
        named(guide, "PETG guide discD9 pocket9.4 aperture8" + (" RLD" if rld else ""), (0.17, 0.2, 0.22)),
        named(plate(6, 23, 0.106, 1.05), "FPC island6x23 no slots", (0.62, 0.39, 0.12)),
        named(plate(6, 23, 0.05, 1.0), "ADHESIVE island0.05 assumed", (0.24, 0.56, 0.66)),
        named(glue, "ADHESIVE guide0.1 assumed", (0.24, 0.56, 0.66)),
        named(plate(15.6, 28, 0.15, -0.15), "ADHESIVE textile0.15 assumed", (0.24, 0.56, 0.66)),
    ]


def disc(y: float, stroke: float = 0.0):
    return named(cyl(DISC_D, DISC_T, y, HEAD_Z - stroke), "METAL D9x1.2 disc 304 STOCK", (0.75, 0.61, 0.3))
