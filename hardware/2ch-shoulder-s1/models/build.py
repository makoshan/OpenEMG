"""用 FreeCAD 的 Part 模块生成 S1 自绘装配示意模型，单位 mm。局部 -Y 为插口。"""
from pathlib import Path
import FreeCAD as App
import Part

V = App.Vector
OUT = Path(__file__).resolve().parent


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def ph3():
    # 壳体轮廓及触脚位置以板端封装原点为基准，留出朝 -Y 的插口。
    body = box(-4.95, -4.4, 0.05, 9.9, 6, 5.45)
    body = body.cut(box(-4.15, -4.5, 0.65, 8.3, 4.9, 4.05))
    for x in (-4.95, 4.15):
        body = body.fuse(box(x, 1.59, .05, .8, 1.61, 5.45))
    for x in (-2, 0, 2):
        body = body.fuse(box(x-.25, 1.50, 0, .5, 2.70, .25))
        body = body.fuse(box(x-.25, -3.0, 2.45, .5, 3.6, .5))
    for x in (-4.65, 4.05):
        body = body.fuse(box(x, -4.4, 0, .6, 2.9, .15))
    return body


def fh34():
    # 1 脚在 +X，20 触点中心排在 Y=0；插口朝 -Y。
    body = box(-5.70, -3.30, .05, 11.40, 3.80, .95)
    body = body.cut(box(-5.28, -3.35, .20, 10.56, 2.35, .36))
    for i in range(20):
        body = body.fuse(box(4.75-.5*i-.075, -.25, 0, .15, .65, .12))
    for x in (-6, 5.45):
        body = body.fuse(box(x, -2.9, 0, .55, .8, .16))
    return body


def pbs32():
    # TI PBS 机械图：5×5 塑体、7×7 引脚跨度、最大高度 1.20。
    body = box(-2.5, -2.5, .15, 5, 5, 1.05)
    body = body.cut(Part.makeCylinder(.19, .1, V(-1.88, 1.88, 1.14)))
    for side in range(4):
        for i in range(8):
            y = -1.75 + .5*i - .10
            lead = box(2.48, y, .35, .48, .20, .12)
            lead = lead.fuse(box(2.85, y, .04, .12, .20, .43))
            lead = lead.fuse(box(2.85, y, 0, .65, .20, .12))
            lead.rotate(V(0,0,0), V(0,0,1), 90*side)
            body = body.fuse(lead)
    return body


def dpy2():
    body = box(-.5, -.3, .025, 1, .6, .425)
    for x in (-.48, .18):
        body = body.fuse(box(x, -.24, 0, .30, .48, .05))
    return body


if __name__ == "__main__":
    for name, create in (("PH3-side", ph3), ("FH34-20", fh34),
                         ("TI-PBS32", pbs32), ("TI-DPY2", dpy2)):
        shape = create().removeSplitter()
        if not shape.isValid() or len(shape.Solids) != 1:
            raise ValueError(f"{name} 模型实体异常")
        shape.exportStep(str(OUT / (name + ".step")))
