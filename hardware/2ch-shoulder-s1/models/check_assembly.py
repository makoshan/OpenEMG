"""用 FreeCAD 重新读入导出的 STEP，检查器件数量、几何干涉和两只肩线插口。"""
from itertools import combinations
from pathlib import Path
import re

import FreeCAD as App
import Import

ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "shoulder-s1.step"


def check():
    doc = App.newDocument("ShoulderVerification")
    Import.insert(str(STEP), doc.Name)
    root, = [obj for obj in doc.Objects if obj.Label == "shoulder-s1 1"]
    items = root.Group
    # 工程的实装清单来自原理图的实例，孔、测试点和板上光学标记没有实体。
    sch = (ROOT / "shoulder-s1.kicad_sch").read_text()
    instances = re.findall(r'\(symbol \(lib_id "BTAI1:([A-Z]+\d+)"(.*?)(?=\(symbol \(lib_id |\Z)', sch, re.S)
    expected = {ref for ref, record in instances
                if ref.startswith(("J", "U", "R", "C", "D", "Q", "L")) and "(dnp no)" in record}
    names = re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\(\s*'[^']*',\s*'([A-Z]+\d+)'", STEP.read_text())
    if sorted(names) != sorted(expected) or len(items) != len(expected) + 1:
        raise ValueError("STEP 实例集合与原理图实装位号不符")
    shapes = [(item.Label, item.Shape) for item in items]
    for name, shape in shapes:
        if not shape.Solids or not shape.isValid():
            raise ValueError(f"无效实体 {name}")
    for (a, s), (b, t) in combinations(shapes, 2):
        if s.BoundBox.intersect(t.BoundBox) and s.common(t).Volume > 1e-5:
            raise ValueError(f"装配实体相交 {a} / {b}")
    ports = sorted((s for n, s in shapes if n.startswith("PH3-side")),
                   key=lambda s: s.BoundBox.Center.x)
    if len(ports) != 2:
        raise ValueError("应有两只肩线座")
    # 用全局坐标检查朝板边一侧为插腔、朝板内一侧为后壁，能检出 180° 装反。
    for shape, mouth_x, back_x, y in zip(ports, (-20.1, 20.4), (-14.7, 15), (8.6, -6)):
        mm = lambda x: App.Vector(x, y, -1.5)
        if shape.isInside(mm(mouth_x), 1e-5, True) or not shape.isInside(mm(back_x), 1e-5, True):
            raise ValueError("JST 插口或后壁方向错误")
    print(f"{len(names)} 个实装位号 + 1 块板；实体有效、两两实体相交 0；左右插腔朝外。")
    App.closeDocument(doc.Name)


if __name__ == "__main__":
    check()
