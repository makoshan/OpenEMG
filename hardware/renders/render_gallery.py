"""OpenEMG 五大类产品影棚光追渲染器（基于 mstack product-render Cycles 管线）。

输出 5 组 × 2 视角（top 正交俯视 + iso 85mm 透视斜视）= 10 张 2400×1350 PNG：
  1. openemg-finished-{top,iso}-dark.png          —— 成品图（16ch 整表正反双姿态 + 2ch R7 一体盒正反双姿态）
  2. openemg-kit-packaging-{top,iso}-dark.png     —— 包装图（模块化开源复刻套件精装 EVA 防静电收纳示意）
  3. openemg-assembly-exploded-{top,iso}-dark.png —— 组装图（16ch R13 / 8ch D20-8CH / 2ch R7 三档叠板立体爆炸图）
  4. openemg-strap-system-{top,iso}-dark.png      —— 表带图（16ch D2 双片软板 + 8ch 单片软板 + TPU 定位层 + F04 连续表带）
  5. openemg-electrodes-{top,iso}-dark.png        —— 电极图（板底直焊六触点 + 胶囊外扣六孔底盖 + Pod D1 穿带式双极干电极微距）

每张图内置三重硬门禁：
  - 同一场景独立展品 XY 水平投影净间距断言（assert_no_xy_overlap），零穿模零重叠；
  - 100% 几何包围盒角点落在取景安全框内（in_frame(0.01)），否则立即报错退出；
  - 高光过曝像素占比 clipped <= 1.0%，否则立即报错退出。
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# 支持脱离 Blender 直接以系统 Python 启动批处理（每个场景独立 Blender 进程，杜绝节点组累加污染）
if "bpy" not in sys.modules and "--worker" not in sys.argv:
    ap_top = argparse.ArgumentParser()
    ap_top.add_argument("--blender", type=str, default=shutil.which("blender") or "/opt/homebrew/bin/blender")
    ap_top.add_argument("--assets", type=Path, required=True)
    ap_top.add_argument("--out", type=Path, required=True)
    ap_top.add_argument("--samples", type=int, default=128)
    ap_top.add_argument("--scale", type=int, default=100)
    ap_top.add_argument("--expo", type=float, default=1.0)
    ap_top.add_argument("--only", type=str, default="")
    top_args = ap_top.parse_args()
    top_args.out.mkdir(parents=True, exist_ok=True)
    all_keys = ["finished", "packaging", "assembly", "strap", "electrodes"]
    sel = [s.strip() for s in top_args.only.split(",") if s.strip()] or all_keys
    report_path = top_args.out / "render_report.json"
    existing = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    for k in sel:
        part_json = top_args.out / f"_report_{k}.json"
        cmd = [
            top_args.blender,
            "-b",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(Path(__file__).resolve()),
            "--",
            "--worker",
            "--assets",
            str(top_args.assets.resolve()),
            "--out",
            str(top_args.out.resolve()),
            "--samples",
            str(top_args.samples),
            "--scale",
            str(top_args.scale),
            "--expo",
            str(top_args.expo),
            "--only",
            k,
            "--report-part",
            str(part_json),
        ]
        print(f"=== [BATCH] Scene '{k}' ===")
        subprocess.run(cmd, check=True)
        existing[k] = json.loads(part_json.read_text(encoding="utf-8"))[k]
        part_json.unlink(missing_ok=True)
    merged_report = {k: existing[k] for k in all_keys if k in existing}
    for k, v in existing.items():
        if k not in merged_report:
            merged_report[k] = v
    report_path.write_text(
        json.dumps(merged_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("BATCH_ALL_SCENES_OK", list(merged_report.keys()))
    sys.exit(0)

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--worker", action="store_true")
ap.add_argument("--assets", type=Path, required=True, help="prepare_assets.py 生成的资产目录")
ap.add_argument("--out", type=Path, required=True, help="渲染 PNG 输出目录")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--expo", type=float, default=1.0)
ap.add_argument("--only", type=str, default="", help="仅渲染指定场景名")
ap.add_argument("--report-part", type=Path, default=None)
args = ap.parse_args(argv)
args.out.mkdir(parents=True, exist_ok=True)

CACHE = Path(os.environ.get("PRODUCT_RENDER_CACHE", Path.home() / ".cache/product-render"))
sys.path[:0] = [str(CACHE / "deps"), str(CACHE / "pcb2blender")]

import bpy  # noqa: E402
import numpy as np  # noqa: E402
import pcb2blender_importer  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

pcb2blender_importer.register()


def srgb_hex_to_lin(hex_str: str):
    rgb = [int(hex_str[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)


GOLD_LIN = srgb_hex_to_lin("c8964a")
IC_COLOR = (0.012, 0.012, 0.013)
IC_PAT = re.compile(r"QFN|DFN|QFP|LQFP|TQFP|SOIC|SSOP|TSSOP|MSOP|SON\b|SOT-|SOD-|BGA|LGA|CSP|^RHL|^RGE|^RSW|^L_0", re.I)


def reset_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)


def make_pbr(
    name: str,
    rgb,
    rough: float,
    metal: float = 0.0,
    spec: float = 0.5,
    alpha: float = 1.0,
    coat: float = 0.0,
    coat_rough: float = 0.08,
):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if alpha < 1.0 and "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if coat > 0.0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
    return m


def make_clear_shell(name: str, rgb=(0.12, 0.18, 0.26), fac: float = 0.16, rough: float = 0.06):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.85
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.94, 0.97, 1.0, 1.0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = fac
    out = nt.nodes["Material Output"]
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def build_palette():
    return {
        "gold": make_pbr("M_GoldSatin", GOLD_LIN, rough=0.28, metal=1.0),
        "champagne": make_pbr("M_Champagne", (0.55, 0.38, 0.15), rough=0.25, metal=0.94),
        # 对齐 c08b-overall-iso-dark.png 高透工程水晶壳：84% 无偏折直线透射 + 16% 镜面高光，一眼看清内部电池与黑金电路板
        "resin": make_clear_shell("M_Resin8001", (0.14, 0.22, 0.32), fac=0.16, rough=0.06),
        "plunger": make_clear_shell("M_Plunger", (0.22, 0.34, 0.48), fac=0.30, rough=0.08),
        "pcb_black": make_pbr("M_PCBBlack", (0.012, 0.015, 0.020), rough=0.36, metal=0.06, spec=0.35),
        "ic_black": make_pbr("M_ICBlack", (0.010, 0.010, 0.012), rough=0.45, metal=0.0, spec=0.25),
        "steel": make_pbr("M_Steel", (0.58, 0.60, 0.64), rough=0.24, metal=0.95),
        "fpc": make_pbr("M_FPCPolyimide", (0.36, 0.13, 0.018), rough=0.36, metal=0.04, spec=0.4),
        "olive_strap": make_pbr("M_OliveStrap", (0.036, 0.066, 0.030), rough=0.75, metal=0.0, spec=0.18),
        "tpu_dark": make_pbr("M_TPUDark", (0.022, 0.025, 0.032), rough=0.62, metal=0.0, spec=0.22),
        "battery": make_pbr("M_BatteryBlue", (0.035, 0.18, 0.52), rough=0.34, metal=0.10, spec=0.45),
        "eva_foam": make_pbr("M_EVAFoam", (0.016, 0.018, 0.023), rough=0.88, metal=0.0, spec=0.08),
        "box_black": make_pbr("M_BoxCard", (0.010, 0.011, 0.015), rough=0.72, metal=0.0, spec=0.18),
    }


def assign_mat(obj, mat):
    if obj.type != "MESH":
        return
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def smooth_shade(objs):
    for o in objs:
        if o.type == "MESH" and o.data:
            for p in o.data.polygons:
                p.use_smooth = True


def crisp_boolean_normals(obj):
    """布尔挖槽后将水平面与正交直壁设为平面着色，彻底消除大面 N-gon 对角阴影拉丝，同时保留倒角圆弧面平滑过渡。"""
    if obj.type != "MESH" or not obj.data:
        return
    for p in obj.data.polygons:
        nx, ny, nz = abs(p.normal.x), abs(p.normal.y), abs(p.normal.z)
        if nz > 0.999 or nx > 0.999 or ny > 0.999:
            p.use_smooth = False
        else:
            p.use_smooth = True


def parent_group(name: str, objs, loc=(0.0, 0.0, 0.0), rot_deg=(0.0, 0.0, 0.0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    obj_set = set(objs)
    for o in objs:
        if o.parent not in obj_set:
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = mw
    root.rotation_euler = Euler(tuple(math.radians(a) for a in rot_deg), "XYZ")
    root.location = Vector(loc)
    bpy.context.view_layer.update()
    return root


def bbox_objs(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    assert pts, "空网格集合"
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def place_center_xy_z0(root, objs, target_cx: float, target_cy: float, z_target: float = 0.0):
    lo, hi = bbox_objs(objs)
    root.location.x += target_cx - (lo.x + hi.x) / 2.0
    root.location.y += target_cy - (lo.y + hi.y) / 2.0
    root.location.z += z_target - lo.z
    bpy.context.view_layer.update()


def place_on_z0(root, objs, z_target: float = 0.0):
    lo, _ = bbox_objs(objs)
    root.location.z += z_target - lo.z
    bpy.context.view_layer.update()


def shift_world_z_lo(mesh_objs: list, target_lo_z: float):
    """沿世界 +Z 轴将一组网格整体平移至最低点 = target_lo_z（兼容含局部 X=+90° 旋转的 GLTF 子网格）。"""
    lo, _ = bbox_objs(mesh_objs)
    dz = target_lo_z - lo.z
    obj_set = set(mesh_objs)
    top_movers = []
    for o in mesh_objs:
        cur = o.parent
        has_anc = False
        while cur is not None:
            if cur in obj_set:
                has_anc = True
                break
            cur = cur.parent
        if not has_anc:
            top_movers.append(o)
    for o in top_movers:
        mw = o.matrix_world.copy()
        mw.translation.z += dz
        o.matrix_world = mw
    bpy.context.view_layer.update()
    new_lo, _ = bbox_objs(mesh_objs)
    assert abs(new_lo.z - target_lo_z) < 2e-4, f"Z 定向偏移误差过大: {new_lo.z} vs {target_lo_z}"


def assert_z_stack_order(tower_name: str, layers: list[tuple[str, list]], min_z_gap: float = 0.002):
    """断言爆炸塔自下而上每一层严格递增且层间留有净空，杜绝层序颠倒或穿模。"""
    spans = []
    for lbl, objs in layers:
        lo, hi = bbox_objs(objs)
        spans.append((lbl, lo.z, hi.z))
    for i in range(len(spans) - 1):
        n1, lo1, hi1 = spans[i]
        n2, lo2, hi2 = spans[i + 1]
        gap = lo2 - hi1
        assert gap >= min_z_gap, (
            f"{tower_name} 爆炸层序穿模或倒置 ({gap*1000:.2f}mm < {min_z_gap*1000:.2f}mm): "
            f"L{i+1}:{n1}[{lo1*1000:.2f}..{hi1*1000:.2f}mm] -> L{i+2}:{n2}[{lo2*1000:.2f}..{hi2*1000:.2f}mm]"
        )


def assert_no_xy_overlap(named_groups: list[tuple[str, list]], min_gap: float = 0.004):
    boxes = []
    for label, objs in named_groups:
        lo, hi = bbox_objs(objs)
        boxes.append((label, lo, hi))
    for i in range(len(boxes)):
        n1, lo1, hi1 = boxes[i]
        for j in range(i + 1, len(boxes)):
            n2, lo2, hi2 = boxes[j]
            dx = max(0.0, max(lo1.x - hi2.x, lo2.x - hi1.x))
            dy = max(0.0, max(lo1.y - hi2.y, lo2.y - hi1.y))
            gap = math.hypot(dx, dy)
            assert gap >= min_gap, (
                f"XY 包围盒碰撞或过近 ({gap*1000:.1f}mm < {min_gap*1000:.1f}mm): "
                f"{n1} [{lo1.x*1000:.1f}..{hi1.x*1000:.1f}, {lo1.y*1000:.1f}..{hi1.y*1000:.1f}] vs "
                f"{n2} [{lo2.x*1000:.1f}..{hi2.x*1000:.1f}, {lo2.y*1000:.1f}..{hi2.y*1000:.1f}]"
            )


def import_pcb3d_group(name: str, pcb3d_path: Path, dpi: float = 2032.0):
    before = set(bpy.data.objects)
    r = bpy.ops.pcb2blender.import_pcb3d(filepath=str(pcb3d_path), add_solder_joints="SMART", texture_dpi=dpi)
    assert r == {"FINISHED"}, (pcb3d_path, r)
    new_objs = [o for o in bpy.data.objects if o not in before]
    retint_pcb2blender(new_objs)
    root = parent_group(name, new_objs)
    return root, new_objs


def import_stl_obj(name: str, stl_path: Path, mat, scale: float = 0.001):
    before = set(bpy.data.objects)
    r = bpy.ops.wm.stl_import(filepath=str(stl_path), global_scale=scale)
    assert r == {"FINISHED"}, (stl_path, r)
    new_objs = [o for o in bpy.data.objects if o not in before]
    for o in new_objs:
        o.name = name
        assign_mat(o, mat)
    smooth_shade(new_objs)
    return new_objs


def import_glb_styled(name: str, glb_path: Path, pal: dict):
    before = set(bpy.data.objects)
    r = bpy.ops.import_scene.gltf(filepath=str(glb_path))
    assert r == {"FINISHED"}, (glb_path, r)
    new_objs = [o for o in bpy.data.objects if o not in before]
    for o in new_objs:
        if o.type != "MESH":
            continue
        nm = o.name.lower()
        if any(k in nm for k in ("tray", "cover")):
            assign_mat(o, pal["resin"])
        elif "plunger" in nm:
            assign_mat(o, pal["plunger"])
        elif any(k in nm for k in ("spring_bar", "usb", "j400", "ufl", "sw300")):
            assign_mat(o, pal["steel"])
        elif "battery" in nm:
            assign_mat(o, pal["battery"])
        elif "contact_" in nm or "electrodes" in nm:
            assign_mat(o, pal["gold"])
        elif "strap_military" in nm or "woven_strap" in nm:
            assign_mat(o, pal["olive_strap"])
        elif "islands" in nm:
            # R15 四层电极软板表面为黑色阻焊覆盖膜，衬托 28 颗镀金圆电极
            assign_mat(o, pal["pcb_black"])
        elif "fpc" in nm or "ffc" in nm:
            assign_mat(o, pal["fpc"])
        elif "board" in nm:
            assign_mat(o, pal["pcb_black"])
        elif any(k in nm for k in ("mcu_u", "mcu_d")):
            assign_mat(o, pal["ic_black"])
    smooth_shade(new_objs)
    root = parent_group(name, new_objs)
    return root, new_objs


def upgrade_capsule_internals(prefix: str, glb_root, glb_objs: list, pal: dict, stls: Path, pcb3d: Path):
    """将整机 GLB 内的简化素模电路板替换为满载器件的 R4U6N 与 D20N 真板模型（在局部原坐标对齐后再随 glb_root 变换）。"""
    drop = []
    for o in glb_objs:
        nm = o.name
        if nm in ("D17_board", "MCU_board") or nm.startswith("MCU_") or re.fullmatch(r"(?:Mesh_)?\d+", nm):
            drop.append(o)
    for o in drop:
        glb_objs.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)

    afe_root, afe_objs = import_pcb3d_group(f"{prefix}_AFE16", pcb3d / "afe_d20n_16ch.pcb3d", dpi=1524.0)
    afe_root.parent = glb_root
    afe_root.location = Vector((0.0, 0.0, 0.00295))

    r4_parts = (
        import_stl_obj(f"{prefix}_R4PCB", stls / "r4u6n_pcb_black.stl", pal["pcb_black"])
        + import_stl_obj(f"{prefix}_R4IC", stls / "r4u6n_ic_black.stl", pal["ic_black"])
        + import_stl_obj(f"{prefix}_R4Conn", stls / "r4u6n_conn_steel.stl", pal["steel"])
        + import_stl_obj(f"{prefix}_R4Pas", stls / "r4u6n_passives_gold.stl", pal["gold"])
    )
    r4_grp = parent_group(f"{prefix}_R4Grp", r4_parts, loc=(0.0, 0.0, 0.0068))
    r4_grp.parent = glb_root
    bpy.context.view_layer.update()
    glb_objs.extend(afe_objs + r4_parts)


def retint_pcb2blender(target_objs):
    # 对齐 product-render/studio.py：把所有焊盘表面处理统一改为 CUSTOM #c8964a 缎面沉金，芯片外壳改近黑哑光
    for tree in [m.node_tree for m in bpy.data.materials if m.node_tree] + list(bpy.data.node_groups):
        for node in tree.nodes:
            if "SurfaceFinish" in node.bl_idname and hasattr(node, "surface_finish"):
                node.surface_finish = "CUSTOM"
                node.inputs["Color"].default_value = (*GOLD_LIN, 1.0)
                node.inputs["Roughness"].default_value = 0.28

    for m in bpy.data.materials:
        for node in (m.node_tree.nodes if m.node_tree else []):
            if "Mat4cad" not in node.bl_idname or getattr(node, "mat_base", "") != "PLASTIC":
                continue
            c = node.inputs["Color"].default_value
            if max(c[:3]) < 0.3 and max(c[:3]) - min(c[:3]) < 0.05:
                node.inputs["Color"].default_value = (*IC_COLOR, 1.0)
                try:
                    node.mat_variant = "MATTE"
                except TypeError:
                    pass

    for o in target_objs:
        if o.type != "MESH" or o.name.startswith("SOLDER") or not IC_PAT.search(o.name) or not o.material_slots:
            continue
        mw, area = o.matrix_world, {}
        nrm = mw.to_3x3()
        tops = [(p, (mw @ p.center).z) for p in o.data.polygons if (nrm @ p.normal).normalized().z > 0.9]
        if not tops:
            continue
        zmax = max(z for _, z in tops)
        for p, z in tops:
            if z > zmax - 0.05e-3:
                area[p.material_index] = area.get(p.material_index, 0.0) + p.area
        slot = o.material_slots[max(area, key=area.get)]
        if slot.material and slot.material.node_tree:
            m = slot.material.copy()
            slot.material = m
            for node in m.node_tree.nodes:
                if "Mat4cad" in node.bl_idname:
                    node.mat_base, node.mat_variant = "PLASTIC", "MATTE"
                    node.inputs["Color"].default_value = (*IC_COLOR, 1.0)


def make_bevel_box(name: str, size_xyz, loc_xyz, bevel_w: float, mat, segments: int = 12):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc_xyz)
    o = bpy.context.object
    o.name = name
    o.scale = size_xyz
    bpy.ops.object.transform_apply(scale=True)
    bev = o.modifiers.new("bevel", "BEVEL")
    bev.width = bevel_w
    bev.segments = segments
    bev.affect = "EDGES"
    bpy.ops.object.modifier_apply(modifier="bevel")
    assign_mat(o, mat)
    smooth_shade([o])
    return o


def make_cylinder(name: str, radius: float, depth: float, loc_xyz, mat, vertices: int = 64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc_xyz)
    o = bpy.context.object
    o.name = name
    bev = o.modifiers.new("bevel", "BEVEL")
    bev.width = min(radius, depth) * 0.08
    bev.segments = 4
    bpy.ops.object.modifier_apply(modifier="bevel")
    assign_mat(o, mat)
    smooth_shade([o])
    return o


def make_text_mesh(name: str, body: str, size: float, extrude: float, loc_xyz, mat):
    curve = bpy.data.curves.new(type="FONT", name=f"{name}_curve")
    curve.body = body
    curve.size = size
    curve.extrude = extrude
    curve.bevel_depth = 0.0
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    for fp in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ):
        if Path(fp).exists():
            curve.font = bpy.data.fonts.load(fp)
            break
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = loc_xyz
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    mesh_obj = bpy.context.object
    assign_mat(mesh_obj, mat)
    return mesh_obj


def setup_studio_and_shoot(scene_name: str, content_objs, iso_dir=(-0.45, -0.80, 0.75), tray_pad_xy=(0.24, 0.22)):
    sc = bpy.context.scene
    lo, hi = bbox_objs(content_objs)
    size = hi - lo
    center = (hi + lo) / 2.0
    L = max(size.x, size.y)

    # 世界光：相机看到纯黑，反射/漫射看到中冷灰（对齐 product-render/studio.py）
    world = bpy.data.worlds.new(f"w_{scene_name}")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bgnode = nt.nodes["Background"]
    bgnode.inputs["Color"].default_value = (0.50, 0.52, 0.56, 1.0)
    bgnode.inputs["Strength"].default_value = 0.62 * args.expo
    black = nt.nodes.new("ShaderNodeBackground")
    black.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bgnode.outputs["Background"], mix.inputs[1])
    nt.links.new(black.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], nt.nodes["World Output"].inputs["Surface"])

    # 深蓝灰圆角托盘
    tray_thk = max(0.003, 0.003 * L / 0.08)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(center.x, center.y, lo.z - tray_thk * 0.52),
    )
    tray = bpy.context.object
    tray.name = "StudioTray"
    tray.scale = (size.x + L * tray_pad_xy[0], size.y + L * tray_pad_xy[1], tray_thk)
    bpy.ops.object.transform_apply(scale=True)
    bev = tray.modifiers.new("bevel", "BEVEL")
    bev.width = min(tray.dimensions.x, tray.dimensions.y) * 0.06
    bev.segments = 16
    bev.affect = "EDGES"
    tray_mat = make_pbr("M_StudioTray", (0.007, 0.009, 0.014), rough=0.80, spec=0.10)
    assign_mat(tray, tray_mat)
    frame_objs = list(content_objs) + [tray]

    def add_area_light(lname: str, loc: Vector, lsize: float, irradiance: float):
        ld = bpy.data.lights.new(lname, "AREA")
        ld.size = lsize
        ld.energy = irradiance * math.pi * (loc - center).length ** 2
        lo_obj = bpy.data.objects.new(lname, ld)
        lo_obj.location = loc
        lo_obj.rotation_euler = (center - loc).to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(lo_obj)

    H = L * 3.8
    E = args.expo
    add_area_light("key", center + Vector((-0.58 * H, 0.55 * H, H)), L * 3.0, 2.45 * E)
    add_area_light("side", center + Vector((-H, -0.32 * H, 0.46 * H)), L * 1.25, 1.05 * E)
    add_area_light("rim", center + Vector((0.82 * H, 0.80 * H, 0.52 * H)), L * 0.85, 0.35 * E)

    sc.render.engine = "CYCLES"
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 12
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.glossy_bounces = 8
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as exc:
        print("GPU_FALLBACK", exc)

    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Base Contrast"
    sc.view_settings.exposure = 1.2
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1350
    sc.render.resolution_percentage = args.scale
    sc.render.image_settings.file_format = "PNG"

    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    cam_d.clip_start, cam_d.clip_end = L * 0.005, L * 250.0

    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in frame_objs if o.type == "MESH" for c in o.bound_box]

    def in_frame(margin: float) -> bool:
        bpy.context.view_layer.update()
        return all(
            margin <= v.x <= 1.0 - margin and margin <= v.y <= 1.0 - margin and v.z > 0
            for v in (world_to_camera_view(sc, cam, p) for p in corners)
        )

    results = []
    for view in ("top", "iso"):
        if view == "top":
            cam_d.type = "ORTHO"
            cam.rotation_euler = (0.0, 0.0, 0.0)
            flo = Vector([min(p[i] for p in corners) for i in range(3)])
            fhi = Vector([max(p[i] for p in corners) for i in range(3)])
            cam.location = ((flo.x + fhi.x) / 2.0, (flo.y + fhi.y) / 2.0, fhi.z + H)
            aspect = sc.render.resolution_x / sc.render.resolution_y
            cam_d.ortho_scale = max(fhi.x - flo.x, (fhi.y - flo.y) * aspect) * 1.14
        else:
            cam_d.type = "PERSP"
            cam_d.lens = 85.0
            dirv = Vector(iso_dir).normalized()
            cam.rotation_euler = (-dirv).to_track_quat("-Z", "Y").to_euler()
            d = L * 22.0
            cam.location = center + dirv * d
            assert in_frame(0.055), f"{scene_name}: 斜视最远处仍出画"
            while True:
                cam.location = center + dirv * (d * 0.96)
                if not in_frame(0.055):
                    cam.location = center + dirv * d
                    break
                d *= 0.96
        if not in_frame(0.01):
            sys.exit(f"{scene_name}-{view}: 模型出画")
        out_png = args.out / f"{scene_name}-{view}-dark.png"
        sc.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)

        img = bpy.data.images.load(str(out_png))
        px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
        img.pixels.foreach_get(px)
        rgb = px.reshape(-1, 4)[:, :3]
        clipped = float((rgb.min(axis=1) >= 0.995).mean())
        mean_val = float(rgb.mean())
        bpy.data.images.remove(img)
        print(f"RENDERED {out_png.name} clipped={clipped:.4f} mean={mean_val:.3f}")
        if clipped > 0.01:
            sys.exit(f"{scene_name}-{view}: 过曝 {clipped:.2%} (>1%)")
        results.append({"file": out_png.name, "clipped": round(clipped, 5), "mean": round(mean_val, 4)})
    return results


def build_r7_unit(name: str, pal: dict, stls: Path, pcb3d: Path, flip_bottom: bool = False):
    objs = []
    pcb_root, pcb_objs = import_pcb3d_group(f"{name}_pcb", pcb3d / "ads1292_2ch.pcb3d", dpi=1524.0)
    pcb_root.location = Vector((0.0, 0.0, 0.0027))
    objs.extend(pcb_objs)

    p44_root, p44_objs = import_pcb3d_group(f"{name}_p44e", pcb3d / "p44e.pcb3d", dpi=1524.0)
    p44_root.rotation_euler = Euler((0.0, 0.0, math.radians(90.0)), "XYZ")
    p44_root.location = Vector((0.011, 0.0, 0.0045))
    objs.extend(p44_objs)

    objs.extend(import_stl_obj(f"{name}_contacts", stls / "r7_contacts_gold.stl", pal["gold"]))
    objs.extend(import_stl_obj(f"{name}_screws", stls / "r7_screws_steel.stl", pal["steel"]))
    objs.extend(import_stl_obj(f"{name}_xiao", stls / "r7_xiao_official.stl", pal["steel"]))
    objs.extend(import_stl_obj(f"{name}_bat", stls / "r7_battery_LP302025_MAX.stl", pal["battery"]))
    objs.extend(import_stl_obj(f"{name}_ffc", stls / "r7_ffc_20P_0p5.stl", pal["fpc"]))
    objs.extend(import_stl_obj(f"{name}_shell", stls / "r7_shell.stl", pal["resin"]))
    objs.extend(import_stl_obj(f"{name}_lid", stls / "r7_lid.stl", pal["resin"]))

    bpy.context.view_layer.update()
    unit_root = parent_group(name, [pcb_root, p44_root] + [o for o in objs if o.parent is None])
    if flip_bottom:
        unit_root.rotation_euler = Euler((math.radians(180.0), 0.0, 0.0), "XYZ")
        bpy.context.view_layer.update()
    return unit_root, objs


# ==============================================================================
# 1. 成品图：openemg-finished
# ==============================================================================
def scene_finished():
    reset_scene()
    pal = build_palette()
    glbs = args.assets / "glbs"
    stls = args.assets / "stls"
    pcb3d = args.assets / "pcb3d"
    all_objs = []

    # 上排左：16ch C08B R13 整表正面朝上（绕 Z 转 -90°：胶囊在 X=+0.045，长表带水平朝左 -X，短表带只到 +0.097）
    w_top_root, w_top_objs = import_glb_styled("Watch16_Top", glbs / "watch_military_green_strap.glb", pal)
    upgrade_capsule_internals("W16Top", w_top_root, w_top_objs, pal, stls, pcb3d)
    w_top_root.rotation_euler = Euler((0.0, 0.0, math.radians(-90.0)), "XYZ")
    w_top_root.location = Vector((0.045, 0.036, 0.0))
    place_on_z0(w_top_root, w_top_objs, 0.0)
    all_objs.extend(w_top_objs)

    # 下排左：16ch C08B R13 整表翻转贴肤面朝上（长表带同样水平朝左 -X，与上排平行对称，展示 6+28=34 颗镀金干电极）
    w_bot_root, w_bot_objs = import_glb_styled("Watch16_Bottom", glbs / "watch_military_green_strap.glb", pal)
    w_bot_root.rotation_euler = Euler((math.radians(180.0), 0.0, math.radians(90.0)), "XYZ")
    w_bot_root.location = Vector((0.045, -0.036, 0.0))
    place_on_z0(w_bot_root, w_bot_objs, 0.0)
    all_objs.extend(w_bot_objs)

    # 右侧上：2ch ADS1292 R7 成品盒正面朝上（X=+0.145，与短表带留足 25 mm 净间距，水晶壳透视 XIAO + P44e + 黑金载板）
    r7_top_root, r7_top_objs = build_r7_unit("R7_Top", pal, stls, pcb3d, flip_bottom=False)
    r7_top_root.location = Vector((0.145, 0.036, 0.0))
    place_on_z0(r7_top_root, r7_top_objs, 0.0)
    all_objs.extend(r7_top_objs)

    # 右侧下：2ch ADS1292 R7 成品盒背面朝上（展示壳底贴腕圆弧槽与六颗「大—辅—大」镀金干电极）
    r7_bot_root, r7_bot_objs = build_r7_unit("R7_Bottom", pal, stls, pcb3d, flip_bottom=True)
    r7_bot_root.location = Vector((0.145, -0.036, 0.0))
    place_on_z0(r7_bot_root, r7_bot_objs, 0.0)
    all_objs.extend(r7_bot_objs)

    assert_no_xy_overlap(
        [
            ("Watch16_Top", w_top_objs),
            ("Watch16_Bottom", w_bot_objs),
            ("R7_Top", r7_top_objs),
            ("R7_Bottom", r7_bot_objs),
        ],
        min_gap=0.015,
    )
    return setup_studio_and_shoot("openemg-finished", all_objs, iso_dir=(-0.38, -0.82, 0.72), tray_pad_xy=(0.16, 0.24))


# ==============================================================================
# 2. 包装图：openemg-kit-packaging（开源复刻套件精装 EVA 防静电收纳示意）
# ==============================================================================
def scene_packaging():
    reset_scene()
    pal = build_palette()
    glbs = args.assets / "glbs"
    stls = args.assets / "stls"
    pcb3d = args.assets / "pcb3d"
    all_objs = []

    box_cx, box_cy = 0.104, 0.0
    box_w, box_h, box_z = 0.196, 0.136, 0.018
    wall = 0.0035
    outer_box = make_bevel_box("KitOuterBox", (box_w, box_h, box_z), (box_cx, box_cy, box_z / 2.0), 0.004, pal["box_black"])
    inner_cut = make_bevel_box(
        "KitInnerCut",
        (box_w - 2 * wall, box_h - 2 * wall, box_z),
        (box_cx, box_cy, box_z / 2.0 + 0.003),
        0.003,
        pal["box_black"],
    )
    mod = outer_box.modifiers.new("hollow", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = inner_cut
    bpy.context.view_layer.objects.active = outer_box
    bpy.ops.object.modifier_apply(modifier="hollow")
    bpy.data.objects.remove(inner_cut, do_unlink=True)
    crisp_boolean_normals(outer_box)
    all_objs.append(outer_box)

    foam_z = 0.0145
    foam = make_bevel_box(
        "KitEVAFoam",
        (box_w - 2 * wall - 0.0006, box_h - 2 * wall - 0.0006, foam_z),
        (box_cx, box_cy, 0.003 + foam_z / 2.0),
        0.0025,
        pal["eva_foam"],
    )

    pockets = [
        ("p_capsule", -0.056, 0.036, 0.048, 0.042, 0.0095),
        ("p_afe8", 0.004, 0.036, 0.045, 0.0385, 0.0045),
        ("p_afe2", 0.060, 0.036, 0.045, 0.0385, 0.0045),
        ("p_fpc8", -0.025, -0.006, 0.108, 0.028, 0.0040),
        ("p_p44e", 0.058, -0.006, 0.024, 0.020, 0.0045),
        ("p_podstrip", 0.000, -0.041, 0.146, 0.032, 0.0055),
    ]
    cutters = []
    for pname, dx, dy, pw, ph, pd in pockets:
        c = make_bevel_box(
            pname,
            (pw, ph, pd + 0.006),
            (box_cx + dx, box_cy + dy, 0.003 + foam_z - pd + (pd + 0.006) / 2.0),
            0.003,
            pal["eva_foam"],
            segments=6,
        )
        cutters.append(c)
        bm = foam.modifiers.new(pname, "BOOLEAN")
        bm.operation = "DIFFERENCE"
        bm.object = c
        bpy.context.view_layer.objects.active = foam
        bpy.ops.object.modifier_apply(modifier=pname)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    crisp_boolean_normals(foam)
    all_objs.append(foam)
    foam_top = 0.003 + foam_z

    # 槽 1：C08B 整机胶囊头（升级为满载真板 + 水晶半透壳，移除悬空编织表带环使槽位利落）
    cap_root, cap_objs = import_glb_styled("Kit_Capsule", glbs / "assembly.glb", pal)
    loops = [o for o in cap_objs if "woven_strap_loop" in o.name]
    for o in loops:
        cap_objs.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)
    upgrade_capsule_internals("KitCap", cap_root, cap_objs, pal, stls, pcb3d)
    cap_root.location = Vector((box_cx - 0.056, box_cy + 0.036, 0.0))
    place_on_z0(cap_root, cap_objs, foam_top - 0.0075)
    all_objs.extend(cap_objs)

    # 槽 2：8ch D20-8CH 纯单面采集板 (.pcb3d)
    b8_root, b8_objs = import_pcb3d_group("Kit_AFE8", pcb3d / "afe_d20_8ch.pcb3d", dpi=1524.0)
    b8_root.location = Vector((box_cx + 0.004, box_cy + 0.036, 0.0))
    place_on_z0(b8_root, b8_objs, foam_top - 0.0012)
    all_objs.extend(b8_objs)

    # 槽 3：2ch ADS1292 六触点采集板 (.pcb3d，统一沉金焊盘)
    b2_root, b2_objs = import_pcb3d_group("Kit_AFE2", pcb3d / "ads1292_2ch.pcb3d", dpi=1524.0)
    b2_root.location = Vector((box_cx + 0.060, box_cy + 0.036, 0.0))
    place_on_z0(b2_root, b2_objs, foam_top - 0.0012)
    all_objs.extend(b2_objs)

    # 槽 4：D2-8CH 34P 柔性表带软板 (.pcb3d + 18 颗镀金铜片)
    s8_root, s8_objs = import_pcb3d_group("Kit_Strap8", pcb3d / "strap_d2_8ch.pcb3d", dpi=1524.0)
    s8_discs = import_stl_obj("Kit_Strap8Discs", stls / "strap_d2_8ch_gold_contacts.stl", pal["gold"])
    for d in s8_discs:
        d.parent = s8_root
    s8_root.location = Vector((box_cx - 0.025, box_cy - 0.006, foam_top - 0.0010))
    all_objs.extend(s8_objs + s8_discs)

    # 槽 5：P44e 转接板
    p4_root, p4_objs = import_pcb3d_group("Kit_P44e", pcb3d / "p44e.pcb3d", dpi=1524.0)
    p4_root.rotation_euler = Euler((0.0, 0.0, math.radians(90.0)), "XYZ")
    p4_root.location = Vector((box_cx + 0.058, box_cy - 0.006, 0.0))
    place_on_z0(p4_root, p4_objs, foam_top - 0.0012)
    all_objs.extend(p4_objs)

    # 槽 6：Pod D1 16节一体 TPU 电极条 + 32 颗 Φ6.5mm 镀金圆电极
    pod_objs = import_stl_obj("Kit_PodStrip", stls / "pod_strip_d1.stl", pal["tpu_dark"])
    pod_discs = []
    for idx in range(16):
        px = (-7.5 + idx) * 0.008875
        for py in (-0.010, 0.010):
            pod_discs.append(make_cylinder(f"Kit_PodDisc_{idx}_{py}", 0.00325, 0.001, (px, py, 0.0056), pal["gold"], vertices=36))
    parent_group("Kit_PodGrp", pod_objs + pod_discs, loc=(box_cx, box_cy - 0.041, foam_top - 0.0040))
    all_objs.extend(pod_objs + pod_discs)

    # 左侧：精装哑光炭黑盒盖（留出 12 mm 独立间隙，锐利矢量金属字体）
    lid_cx, lid_cy = -0.106, 0.0
    lid_w, lid_h, lid_z = 0.198, 0.138, 0.011
    lid_box = make_bevel_box("KitLidBox", (lid_w, lid_h, lid_z), (lid_cx, lid_cy, lid_z / 2.0), 0.004, pal["box_black"])
    rim_outer = make_bevel_box(
        "KitLidRimO", (lid_w - 0.018, lid_h - 0.018, 0.0005), (lid_cx, lid_cy, lid_z + 0.0001), 0.002, pal["champagne"], segments=6
    )
    rim_inner = make_bevel_box(
        "KitLidRimI", (lid_w - 0.0205, lid_h - 0.0205, 0.002), (lid_cx, lid_cy, lid_z + 0.0001), 0.0018, pal["champagne"], segments=6
    )
    rmod = rim_outer.modifiers.new("rcut", "BOOLEAN")
    rmod.operation = "DIFFERENCE"
    rmod.object = rim_inner
    bpy.context.view_layer.objects.active = rim_outer
    bpy.ops.object.modifier_apply(modifier="rcut")
    bpy.data.objects.remove(rim_inner, do_unlink=True)
    crisp_boolean_normals(rim_outer)

    t1 = make_text_mesh("TxtTitle", "OpenEMG", 0.021, 0.00045, (lid_cx, lid_cy + 0.018, lid_z), pal["champagne"])
    t2 = make_text_mesh("TxtSub", "2 / 8 / 16-CH  MODULAR  sEMG  KIT", 0.0076, 0.00035, (lid_cx, lid_cy - 0.007, lid_z), pal["gold"])
    t3 = make_text_mesh("TxtLic", "46x40 mm STACK  |  CERN-OHL-S-2.0 & MIT", 0.0058, 0.00030, (lid_cx, lid_cy - 0.031, lid_z), pal["steel"])
    lid_objs = [lid_box, rim_outer, t1, t2, t3]
    all_objs.extend(lid_objs)

    assert_no_xy_overlap([("Lid", lid_objs), ("TrayBox", [outer_box])], min_gap=0.010)
    return setup_studio_and_shoot("openemg-kit-packaging", all_objs, iso_dir=(-0.40, -0.84, 0.78), tray_pad_xy=(0.14, 0.20))


# ==============================================================================
# 3. 组装图：openemg-assembly-exploded（16ch / 8ch / 2ch 三档叠板分层爆炸图）
# ==============================================================================
def scene_assembly():
    reset_scene()
    pal = build_palette()
    glbs = args.assets / "glbs"
    stls = args.assets / "stls"
    pcb3d = args.assets / "pcb3d"
    all_objs = []

    # 左塔 (X = -0.072 m)：从合拢真源 assembly.glb 提取 7 层物理零件，沿世界 +Z 轴自下而上逐层分离爆炸
    lx = -0.072
    ex_root, ex_objs = import_glb_styled("Exploded16_R13", glbs / "assembly.glb", pal)
    drop_list = []
    for o in ex_objs:
        nm = o.name
        if nm in ("D17_board", "MCU_board") or nm.startswith("MCU_") or re.fullmatch(r"(?:Mesh_)?\d+", nm):
            drop_list.append(o)
    for o in drop_list:
        ex_objs.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)

    ex_root.location = Vector((lx, 0.0, 0.0))
    bpy.context.view_layer.update()

    ex16_contacts = [o for o in ex_objs if o.name.startswith("contact_")]
    ex16_tray = [
        o
        for o in ex_objs
        if o.name in ("tray", "north_spring_bar", "south_spring_bar", "north_woven_strap_loop", "south_woven_strap_loop")
        or o.name.startswith("R14_FPC_")
    ]
    ex16_bat = [o for o in ex_objs if o.name in ("battery_302025_max", "J_AFE_FFC20_loop")]
    ex16_cov = [o for o in ex_objs if o.name in ("cover", "FPC_ANT_2G4")]
    ex16_plg = [o for o in ex_objs if o.name == "switch_plunger"]
    accounted = set(ex16_contacts + ex16_tray + ex16_bat + ex16_cov + ex16_plg)
    leftover = [o.name for o in ex_objs if o.type == "MESH" and o not in accounted]
    assert not leftover, f"R13 assembly.glb 存在未归类网格: {leftover}"

    afe16_root, afe16_objs = import_pcb3d_group("Ex16_AFED20N", pcb3d / "afe_d20n_16ch.pcb3d", dpi=1524.0)
    afe16_root.location = Vector((lx, 0.0, 0.0))
    r4_parts = (
        import_stl_obj("Ex16_R4PCB", stls / "r4u6n_pcb_black.stl", pal["pcb_black"])
        + import_stl_obj("Ex16_R4IC", stls / "r4u6n_ic_black.stl", pal["ic_black"])
        + import_stl_obj("Ex16_R4Conn", stls / "r4u6n_conn_steel.stl", pal["steel"])
        + import_stl_obj("Ex16_R4Pas", stls / "r4u6n_passives_gold.stl", pal["gold"])
    )
    r4_16_grp = parent_group("Ex16_R4Grp", r4_parts, loc=(lx, 0.0, 0.0))

    shift_world_z_lo(ex16_contacts, 0.0005)
    shift_world_z_lo(ex16_tray, 0.0070)
    shift_world_z_lo([afe16_root] + afe16_objs, 0.0205)
    shift_world_z_lo(ex16_bat, 0.0290)
    shift_world_z_lo([r4_16_grp] + r4_parts, 0.0395)
    shift_world_z_lo(ex16_cov, 0.0485)
    shift_world_z_lo(ex16_plg, 0.0595)

    assert_z_stack_order(
        "Tower16_R13",
        [
            ("Contacts6", ex16_contacts),
            ("Tray_R13", ex16_tray),
            ("AFE_D20N_16ch", afe16_objs),
            ("Battery_FFC20", ex16_bat),
            ("Mainboard_R4U6N", r4_parts),
            ("Cover_ANT", ex16_cov),
            ("Plunger", ex16_plg),
        ],
        min_z_gap=0.0025,
    )
    tower16 = ex_objs + afe16_objs + r4_parts
    all_objs.extend(tower16)

    # 中塔 (X = 0.000 m)：8ch 纯单面采集板 D20-8CH + 外扣六孔底盖 Capsule Cap D2 分层爆炸
    cap_d2 = import_stl_obj("Ex8_CapD2", stls / "cap_d2.stl", pal["tpu_dark"])
    cap8_grp = parent_group("Ex8_CapG", cap_d2, loc=(0.0, 0.0, 0.0))
    c6 = []
    for cx_m, cy_m in ((-0.008, 0.0075), (0.008, 0.0075), (-0.008, -0.0075), (0.008, -0.0075)):
        c6.append(make_cylinder(f"Ex8_E_{cx_m}_{cy_m}", 0.003, 0.002, (cx_m, cy_m, 0.0), pal["gold"], vertices=40))
    for cy_m in (-0.0075, 0.0075):
        c6.append(make_bevel_box(f"Ex8_EB_{cy_m}", (0.003, 0.003, 0.002), (0.0, cy_m, 0.0), 0.0003, pal["gold"], segments=4))
    tray_d2 = import_stl_obj("Ex8_TrayD2", stls / "tray_d2.stl", pal["resin"])
    tray8_grp = parent_group("Ex8_TrayG", tray_d2, loc=(0.0, 0.0, 0.0))
    afe8_root, afe8_objs = import_pcb3d_group("Ex8_AFE8", pcb3d / "afe_d20_8ch.pcb3d", dpi=1524.0)
    afe8_root.location = Vector((0.0, 0.0, 0.0))
    bat8 = make_bevel_box("Ex8_Bat", (0.025, 0.020, 0.003), (-0.002, -0.002, 0.0), 0.0006, pal["battery"], segments=6)
    r4_8 = (
        import_stl_obj("Ex8_R4PCB", stls / "r4u6n_pcb_black.stl", pal["pcb_black"])
        + import_stl_obj("Ex8_R4IC", stls / "r4u6n_ic_black.stl", pal["ic_black"])
        + import_stl_obj("Ex8_R4Conn", stls / "r4u6n_conn_steel.stl", pal["steel"])
        + import_stl_obj("Ex8_R4Pas", stls / "r4u6n_passives_gold.stl", pal["gold"])
    )
    r4_8_grp = parent_group("Ex8_R4G", r4_8, loc=(0.0, 0.0, 0.0))
    cov8 = import_stl_obj("Ex8_Lid", stls / "r7_lid.stl", pal["resin"])
    cov8_grp = parent_group("Ex8_CovG", cov8, loc=(0.0, 0.0, 0.0))

    shift_world_z_lo([cap8_grp] + cap_d2, 0.0005)
    shift_world_z_lo(c6, 0.0065)
    shift_world_z_lo([tray8_grp] + tray_d2, 0.0125)
    shift_world_z_lo([afe8_root] + afe8_objs, 0.0235)
    shift_world_z_lo([bat8], 0.0315)
    shift_world_z_lo([r4_8_grp] + r4_8, 0.0405)
    shift_world_z_lo([cov8_grp] + cov8, 0.0505)

    assert_z_stack_order(
        "Tower8_D20_8CH",
        [
            ("CapsuleCap_D2", cap_d2),
            ("Contacts6", c6),
            ("Tray_D2", tray_d2),
            ("AFE_D20_8CH", afe8_objs),
            ("Battery_302025", [bat8]),
            ("Mainboard_R4U6N", r4_8),
            ("Lid", cov8),
        ],
        min_z_gap=0.0025,
    )
    tower8 = cap_d2 + c6 + tray_d2 + afe8_objs + [bat8] + r4_8 + cov8
    all_objs.extend(tower8)

    # 右塔 (X = +0.072 m)：2ch ADS1292 + P44e + Seeed XIAO nRF52840 入门版 R7 竖向分层爆炸
    rx = 0.072
    r2_contacts = import_stl_obj("Ex2_Contacts", stls / "r7_contacts_gold.stl", pal["gold"])
    r2_con_grp = parent_group("Ex2_ConG", r2_contacts, loc=(rx, 0.0, 0.0))
    r2_shell = import_stl_obj("Ex2_Shell", stls / "r7_shell.stl", pal["resin"])
    r2_sh_grp = parent_group("Ex2_ShG", r2_shell, loc=(rx, 0.0, 0.0))
    r2_pcb_root, r2_pcb_objs = import_pcb3d_group("Ex2_PCB", pcb3d / "ads1292_2ch.pcb3d", dpi=1524.0)
    r2_pcb_root.location = Vector((rx, 0.0, 0.0))
    r2_bat = import_stl_obj("Ex2_Bat", stls / "r7_battery_LP302025_MAX.stl", pal["battery"])
    r2_ffc = import_stl_obj("Ex2_FFC", stls / "r7_ffc_20P_0p5.stl", pal["fpc"])
    r2_mid_grp = parent_group("Ex2_MidG", r2_bat + r2_ffc, loc=(rx, 0.0, 0.0))
    r2_p44_root, r2_p44_objs = import_pcb3d_group("Ex2_P44e", pcb3d / "p44e.pcb3d", dpi=1524.0)
    r2_p44_root.rotation_euler = Euler((0.0, 0.0, math.radians(90.0)), "XYZ")
    r2_p44_root.location = Vector((rx + 0.011, 0.0, 0.0))
    r2_xiao = import_stl_obj("Ex2_XIAO", stls / "r7_xiao_official.stl", pal["steel"])
    r2_xiao_grp = parent_group("Ex2_XiaoG", r2_xiao, loc=(rx, 0.0, 0.0))
    r2_lid = import_stl_obj("Ex2_Lid", stls / "r7_lid.stl", pal["resin"])
    r2_lid_grp = parent_group("Ex2_LidG", r2_lid, loc=(rx, 0.0, 0.0))

    shift_world_z_lo([r2_con_grp] + r2_contacts, 0.0005)
    shift_world_z_lo([r2_sh_grp] + r2_shell, 0.0065)
    shift_world_z_lo([r2_pcb_root] + r2_pcb_objs, 0.0195)
    shift_world_z_lo([r2_mid_grp] + r2_bat + r2_ffc, 0.0275)
    shift_world_z_lo([r2_p44_root] + r2_p44_objs, 0.0365)
    shift_world_z_lo([r2_xiao_grp] + r2_xiao, 0.0435)
    shift_world_z_lo([r2_lid_grp] + r2_lid, 0.0525)

    assert_z_stack_order(
        "Tower2_R7",
        [
            ("Contacts6", r2_contacts),
            ("Shell_R7", r2_shell),
            ("ADS1292_2ch", r2_pcb_objs),
            ("Battery_FFC20", r2_bat + r2_ffc),
            ("Adapter_P44e", r2_p44_objs),
            ("Seeed_XIAO", r2_xiao),
            ("Lid_R7", r2_lid),
        ],
        min_z_gap=0.0025,
    )
    tower2 = r2_contacts + r2_shell + r2_pcb_objs + r2_bat + r2_ffc + r2_p44_objs + r2_xiao + r2_lid
    all_objs.extend(tower2)

    assert_no_xy_overlap([("Tower16", tower16), ("Tower8", tower8), ("Tower2", tower2)], min_gap=0.020)
    return setup_studio_and_shoot("openemg-assembly-exploded", all_objs, iso_dir=(-0.46, -0.82, 0.64), tray_pad_xy=(0.22, 0.34))


# ==============================================================================
# 4. 表带图：openemg-strap-system（16ch D2 双片软板 + 8ch 单片软板 + TPU 层 + F04 连续表带）
# ==============================================================================
def scene_strap():
    reset_scene()
    pal = build_palette()
    stls = args.assets / "stls"
    pcb3d = args.assets / "pcb3d"
    all_objs = []
    groups_check = []

    # 第 1 行 (Y = +0.044 m)：左 16ch D2 软板 A 片 (105mm) | 中 16ch 南段 TPU (96mm) | 右 16ch 北段 TPU (16mm)
    sa_root, sa_objs = import_pcb3d_group("Strap16_A", pcb3d / "strap_a.pcb3d", dpi=1524.0)
    sa_discs = import_stl_obj("Strap16_ADiscs", stls / "strap_a_gold_contacts.stl", pal["gold"])
    for d in sa_discs:
        d.parent = sa_root
    place_center_xy_z0(sa_root, sa_objs + sa_discs, -0.102, 0.044, 0.0004)
    all_objs.extend(sa_objs + sa_discs)
    groups_check.append(("Strap16_A", sa_objs + sa_discs))

    tpu16_s = import_stl_obj("TPU16_South", stls / "tpu_d2_south.stl", pal["tpu_dark"])
    t16s_grp = parent_group("TPU16_SGrp", tpu16_s, rot_deg=(0.0, 0.0, -90.0))
    place_center_xy_z0(t16s_grp, tpu16_s, 0.016, 0.044, 0.0)
    all_objs.extend(tpu16_s)
    groups_check.append(("TPU16_South", tpu16_s))

    tpu16_n = import_stl_obj("TPU16_North", stls / "tpu_d2_north.stl", pal["tpu_dark"])
    t16n_grp = parent_group("TPU16_NGrp", tpu16_n, rot_deg=(0.0, 0.0, -90.0))
    place_center_xy_z0(t16n_grp, tpu16_n, 0.086, 0.044, 0.0)
    all_objs.extend(tpu16_n)
    groups_check.append(("TPU16_North", tpu16_n))

    # 第 2 行 (Y = +0.005 m)：左 16ch D2 软板 B 片 (150mm) | 中 8ch 南段短版 TPU (32mm) | 右 8ch 北段 TPU (16mm)
    sb_root, sb_objs = import_pcb3d_group("Strap16_B", pcb3d / "strap_b.pcb3d", dpi=1524.0)
    sb_discs = import_stl_obj("Strap16_BDiscs", stls / "strap_b_gold_contacts.stl", pal["gold"])
    for d in sb_discs:
        d.parent = sb_root
    place_center_xy_z0(sb_root, sb_objs + sb_discs, -0.079, 0.005, 0.0004)
    all_objs.extend(sb_objs + sb_discs)
    groups_check.append(("Strap16_B", sb_objs + sb_discs))

    tpu8_s = import_stl_obj("TPU8_South", stls / "tpu_8ch_south.stl", pal["tpu_dark"])
    t8s_grp = parent_group("TPU8_SGrp", tpu8_s, rot_deg=(0.0, 0.0, -90.0))
    place_center_xy_z0(t8s_grp, tpu8_s, 0.030, 0.005, 0.0)
    all_objs.extend(tpu8_s)
    groups_check.append(("TPU8_South", tpu8_s))

    tpu8_n = import_stl_obj("TPU8_North", stls / "tpu_8ch_north.stl", pal["tpu_dark"])
    t8n_grp = parent_group("TPU8_NGrp", tpu8_n, rot_deg=(0.0, 0.0, -90.0))
    place_center_xy_z0(t8n_grp, tpu8_n, 0.068, 0.005, 0.0)
    all_objs.extend(tpu8_n)
    groups_check.append(("TPU8_North", tpu8_n))

    # 第 3 行 (Y = -0.034 m)：左 8ch 单片软板 D2-8CH (105mm) | 右 F04 9排军绿背开口连续表带 (172mm)
    s8_root, s8_objs = import_pcb3d_group("Strap8_Single", pcb3d / "strap_d2_8ch.pcb3d", dpi=1524.0)
    s8_discs = import_stl_obj("Strap8_Discs", stls / "strap_d2_8ch_gold_contacts.stl", pal["gold"])
    for d in s8_discs:
        d.parent = s8_root
    place_center_xy_z0(s8_root, s8_objs + s8_discs, -0.102, -0.034, 0.0004)
    all_objs.extend(s8_objs + s8_discs)
    groups_check.append(("Strap8_Single", s8_objs + s8_discs))

    f04_parts = (
        import_stl_obj("F04_TPU", stls / "f04_tpu_body.stl", pal["olive_strap"])
        + import_stl_obj("F04_Gold", stls / "f04_gold_discs.stl", pal["gold"])
        + import_stl_obj("F04_Spring", stls / "f04_springs.stl", pal["fpc"])
    )
    f04_grp = parent_group("F04_Grp", f04_parts)
    place_center_xy_z0(f04_grp, f04_parts, 0.066, -0.034, 0.0)
    all_objs.extend(f04_parts)
    groups_check.append(("F04_Strap", f04_parts))

    assert_no_xy_overlap(groups_check, min_gap=0.008)
    return setup_studio_and_shoot("openemg-strap-system", all_objs, iso_dir=(-0.40, -0.82, 0.74), tray_pad_xy=(0.15, 0.24))


# ==============================================================================
# 5. 电极图：openemg-electrodes（贴肤镀金干电极微距特写）
# ==============================================================================
def scene_electrodes():
    reset_scene()
    pal = build_palette()
    stls = args.assets / "stls"
    pcb3d = args.assets / "pcb3d"
    all_objs = []
    groups_check = []

    # 左区 (X = -0.062 m, Y = +0.015 m)：2ch-ads1292 板底直焊六触点「大—辅—大」微距（底面朝上，保留高清丝印与沉金盘）
    b2_root, b2_objs = import_pcb3d_group("Elec_2chPCB", pcb3d / "ads1292_2ch.pcb3d", dpi=2032.0)
    b2_root.location = Vector((0.0, 0.0, 0.0027))
    b2_contacts = import_stl_obj("Elec_2chContacts", stls / "r7_contacts_gold.stl", pal["gold"])
    b2_grp = parent_group("Elec_2chGrp", [b2_root] + b2_contacts, loc=(-0.062, 0.015, 0.0), rot_deg=(180.0, 0.0, 0.0))
    place_on_z0(b2_grp, b2_objs + b2_contacts, 0.0)
    all_objs.extend(b2_objs + b2_contacts)
    groups_check.append(("Elec_2ch", b2_objs + b2_contacts))

    # 中区 (X = -0.003 m, Y = +0.015 m)：C08B 胶囊外扣六孔底盖 Capsule Cap D2 + 6 颗穿孔齐平镀金干电极
    tray_d2 = import_stl_obj("Elec_TrayD2", stls / "tray_d2.stl", pal["resin"])
    cap_d2 = import_stl_obj("Elec_CapD2", stls / "cap_d2.stl", pal["tpu_dark"])
    cap_contacts = []
    for cx_m, cy_m in ((-0.008, 0.0075), (0.008, 0.0075), (-0.008, -0.0075), (0.008, -0.0075)):
        cap_contacts.append(make_cylinder(f"Elec_CapC_{cx_m}_{cy_m}", 0.003, 0.002, (cx_m, cy_m, -0.00125), pal["gold"], vertices=48))
    for cy_m in (-0.0075, 0.0075):
        cap_contacts.append(
            make_bevel_box(f"Elec_CapSq_{cy_m}", (0.003, 0.003, 0.002), (0.0, cy_m, -0.00125), 0.0003, pal["gold"], segments=6)
        )
    cap_grp = parent_group("Elec_CapGrp", tray_d2 + cap_d2 + cap_contacts, loc=(-0.003, 0.015, 0.0), rot_deg=(180.0, 0.0, 0.0))
    place_on_z0(cap_grp, tray_d2 + cap_d2 + cap_contacts, 0.0)
    all_objs.extend(tray_d2 + cap_d2 + cap_contacts)
    groups_check.append(("Elec_CapD2", tray_d2 + cap_d2 + cap_contacts))

    # 右区 (X = +0.048 & +0.070 m, Y = +0.015 m)：单节 Pod D1 双极干电极豆组装态 vs 分解悬停态
    pod1 = import_stl_obj("Elec_PodAssy", stls / "pod_d1.stl", pal["tpu_dark"])
    p1_d1 = make_cylinder("Elec_PodAssyD1", 0.00325, 0.001, (0.0, -0.010, 0.0061), pal["gold"], vertices=48)
    p1_d2 = make_cylinder("Elec_PodAssyD2", 0.00325, 0.001, (0.0, 0.010, 0.0061), pal["gold"], vertices=48)
    pod1_grp = parent_group("Elec_Pod1G", pod1 + [p1_d1, p1_d2], loc=(0.048, 0.015, 0.0))
    place_on_z0(pod1_grp, pod1 + [p1_d1, p1_d2], 0.0)
    all_objs.extend(pod1 + [p1_d1, p1_d2])
    groups_check.append(("Pod1_Assy", pod1 + [p1_d1, p1_d2]))

    pod2 = import_stl_obj("Elec_PodExpBase", stls / "pod_d1.stl", pal["tpu_dark"])
    foam1 = make_cylinder("Elec_Foam1", 0.0030, 0.002, (0.0, -0.010, 0.0105), pal["eva_foam"], vertices=40)
    foam2 = make_cylinder("Elec_Foam2", 0.0030, 0.002, (0.0, 0.010, 0.0105), pal["eva_foam"], vertices=40)
    disc1 = make_cylinder("Elec_Disc1", 0.00325, 0.001, (0.0, -0.010, 0.0160), pal["gold"], vertices=48)
    disc2 = make_cylinder("Elec_Disc2", 0.00325, 0.001, (0.0, 0.010, 0.0160), pal["gold"], vertices=48)
    pod2_grp = parent_group("Elec_Pod2G", pod2 + [foam1, foam2, disc1, disc2], loc=(0.070, 0.015, 0.0))
    place_on_z0(pod2_grp, pod2, 0.0)
    all_objs.extend(pod2 + [foam1, foam2, disc1, disc2])
    groups_check.append(("Pod2_Exp", pod2 + [foam1, foam2, disc1, disc2]))

    # 前排横贯 (Y = -0.032 m)：穿在 25 mm 军绿战术织带上的 16 节一体连接 TPU 电极豆条 Pod D1（32 颗 Φ6.5mm 镀金电极阵列）
    strip = import_stl_obj("Elec_PodStrip", stls / "pod_strip_d1.stl", pal["tpu_dark"])
    webbing = make_bevel_box("Elec_Webbing25", (0.168, 0.025, 0.0016), (0.0, 0.0, 0.0023), 0.0005, pal["olive_strap"], segments=4)
    s_discs = []
    for idx in range(16):
        px = (-7.5 + idx) * 0.008875
        for py in (-0.010, 0.010):
            s_discs.append(make_cylinder(f"Elec_SDisc_{idx}_{py}", 0.00325, 0.001, (px, py, 0.0061), pal["gold"], vertices=40))
    strip_grp = parent_group("Elec_StripGrp", strip + [webbing] + s_discs, loc=(0.003, -0.032, 0.0))
    place_on_z0(strip_grp, strip + [webbing] + s_discs, 0.0)
    all_objs.extend(strip + [webbing] + s_discs)
    groups_check.append(("PodStrip16", strip + [webbing] + s_discs))

    assert_no_xy_overlap(groups_check, min_gap=0.008)
    return setup_studio_and_shoot("openemg-electrodes", all_objs, iso_dir=(-0.42, -0.84, 0.68), tray_pad_xy=(0.20, 0.26))


SCENES = [
    ("finished", scene_finished),
    ("packaging", scene_packaging),
    ("assembly", scene_assembly),
    ("strap", scene_strap),
    ("electrodes", scene_electrodes),
]

selected = {s.strip() for s in args.only.split(",") if s.strip()}
report = {}
for key, fn in SCENES:
    if selected and key not in selected:
        continue
    print(f"========== RENDERING SCENE: {key} ==========")
    report[key] = fn()

out_json = args.report_part if args.report_part else (args.out / "render_report.json")
out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("WORKER_SCENES_OK", list(report.keys()))
