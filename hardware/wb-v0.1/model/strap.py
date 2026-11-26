# /// script
# dependencies = ["build123d==0.13.0"]
# ///
"""生成 WB v0.1.1 表带打印件。尺寸单位为 mm，Z=0 为软板一侧。"""
import argparse
from pathlib import Path

import build123d as b


def hole(diameter, start_z, end_z, y):
    return b.Pos(0, y, (start_z + end_z) / 2) * b.Cylinder(diameter / 2, end_z - start_z)


def wristband():
    thickness = 2.10
    block = b.extrude(b.RectangleRounded(7, 26, 1.75), amount=thickness)
    for y in (-10, 0, 10):
        block = block.cut(hole(2.20, -.01, thickness + .01, y),
                          hole(4.00, 1.50, thickness + .01, y))
    for y in (-5, 5):
        block = block.cut(hole(2.40, -.01, thickness + .01, y))
    # 薄片延伸至黑块的圆角切点，覆盖相邻两块之间全宽 26 mm 的缝。
    web = b.extrude(b.Rectangle(6.5, 26), amount=.40)
    sections = [b.Pos(10*i, 0, 0)*block for i in range(8)]
    webs = [b.Pos(5+10*i, 0, 0)*web for i in range(7)]
    strip = sections[0].fuse(*sections[1:], *webs).clean()
    assert strip.is_valid and len(strip.solids()) == 1
    body = strip.solids()[0]
    body.label, body.color = 'TPU_linked_strip', b.Color('#4C5864')
    return body


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    shape = wristband()
    b.export_step(shape, out/'strap.step')
    b.export_stl(shape, out/'strap.stl', tolerance=.015, angular_tolerance=.10)
