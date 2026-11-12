# 解析 Bambu G-code，按模型坐标探针列出每个点上方各层的挤出特征（看 0.35 唇边和内袋顶怎么被切）
# 用法：python3 gprobe.py 切片.3mf 南段.stl [北段.stl]。模型外形范围从 STL 读（旧版写死 −138..−19.3，
# 舌片加长到 −214 后南段探针整体偏了 38 mm）；只给一个 STL 时当作南段试样件，只探南段点。
import re, sys, json, zipfile, math, struct
from collections import defaultdict
import numpy as np
gz = zipfile.ZipFile(sys.argv[1]).read("Metadata/plate_1.gcode").decode()
segs = []  # (x0,y0,x1,y1,z,feature,obj,e)
# 盘上只有一个对象时 Bambu 不写对象标记：整盘挤出都算对象 0
LABELED = "; start printing object" in gz
z = 0; feat = None; obj = None if LABELED else 0; x = y = None
for ln in gz.splitlines():
    if ln.startswith("; Z_HEIGHT:"): z = float(ln.split(":")[1])
    elif ln.startswith("; FEATURE:"): feat = ln.split(":", 1)[1].strip()
    elif ln.startswith("; start printing object, unique label id:"): obj = int(ln.rsplit(":", 1)[1])
    elif ln.startswith("; stop printing object") and LABELED: obj = None
    elif ln.startswith("G1") or ln.startswith("G0") or ln.startswith("G2") or ln.startswith("G3"):
        m = dict((k, float(v)) for k, v in re.findall(r"([XYZEIJ])([-\d.]+)", ln.split(";")[0]))
        nx, ny = m.get("X", x), m.get("Y", y)
        if ln[:2] in ("G1", "G2", "G3") and m.get("E", 0) > 0 and x is not None and obj is not None:
            if ln[:2] == "G1":
                segs.append((x, y, nx, ny, z, feat, obj, m["E"]))
            else:   # 圆弧：按圆心 I/J 拆成 ≤0.1 mm 的小段
                cx, cy = x + m.get("I", 0), y + m.get("J", 0); r = math.hypot(x - cx, y - cy)
                a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                sw = ((a0 - a1) if ln[:2] == "G2" else (a1 - a0)) % (2 * math.pi) or 2 * math.pi
                n = max(2, int(r * sw / 0.1) + 1); sg = -1 if ln[:2] == "G2" else 1
                pts = [(cx + r * math.cos(a0 + sg * sw * i / n), cy + r * math.sin(a0 + sg * sw * i / n)) for i in range(n + 1)]
                for (p0, q0), (p1, q1) in zip(pts, pts[1:]):
                    segs.append((p0, q0, p1, q1, z, feat, obj, m["E"] / n))
        x, y = nx, ny
S = np.array([s[:5] for s in segs]); F = [s[5] for s in segs]; O = np.array([s[6] for s in segs])
objs = {}
for o in sorted(set(O)):
    k = O == o
    bb = (S[k][:, [0, 2]].min(), S[k][:, [0, 2]].max(), S[k][:, [1, 3]].min(), S[k][:, [1, 3]].max())
    objs[o] = bb
def stl_xy_bb(p):
    raw = open(p, "rb").read(); n = struct.unpack("<I", raw[80:84])[0]
    v = np.frombuffer(raw[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))["v"].reshape(-1, 3)
    return (float(v[:, 0].min()), float(v[:, 0].max()), float(v[:, 1].min()), float(v[:, 1].max()))


# 南段（或试样件）Y 跨度最长；摆盘不旋转，所以挤出包围盒中心 − 模型包围盒中心 = 平移量
south = max(objs, key=lambda o: objs[o][3] - objs[o][2])
north = ([o for o in objs if o != south] or [None])[0]
model_bb = {south: stl_xy_bb(sys.argv[2])}
if north is not None:
    model_bb[north] = stl_xy_bb(sys.argv[3])
assert all(abs((objs[o][3] - objs[o][2]) - (model_bb[o][3] - model_bb[o][2])) < 1.0 for o in model_bb), "挤出跨度和 STL 对不上（摆盘转了？）"
off = {o: ((objs[o][0] + objs[o][1]) / 2 - (model_bb[o][0] + model_bb[o][1]) / 2,
           (objs[o][2] + objs[o][3]) / 2 - (model_bb[o][2] + model_bb[o][3]) / 2) for o in objs}
span = {o: (round(objs[o][1] - objs[o][0], 2), round(objs[o][3] - objs[o][2], 2)) for o in model_bb}
def probe(o, mx, my, r=0.3):
    bx, by = mx + off[o][0], my + off[o][1]
    k = O == o
    P = S[k]; ff = [F[i] for i in np.nonzero(k)[0]]
    a = P[:, 0:2]; bpt = P[:, 2:4]; ab = bpt - a; L2 = (ab ** 2).sum(1) + 1e-12
    t = np.clip(((np.array([bx, by]) - a) * ab).sum(1) / L2, 0, 1)
    d = np.hypot(*(a + ab * t[:, None] - np.array([bx, by])).T)
    hit = defaultdict(set)
    for i in np.nonzero(d < r)[0]: hit[round(P[i, 4], 3)].add(ff[i])
    return {zz: sorted(v) for zz, v in sorted(hit.items()) if zz <= 3.2}
out = {"object_extrusion_span_mm": {k: span[o] for k, o in (("south", south), ("north", north)) if o is not None}, "probes": {}}
pts = {
    "south_lip_X7_Y-69": (south, 7.0, -69.0), "south_lip_X10.2_Y-69": (south, 10.2, -69.0),
    "south_slot_X0_Y-69": (south, 0.0, -69.0), "south_relief_X0_Y-45": (south, 0.0, -45.0),
    "south_contact_X9_Y-65": (south, 9.0, -65.0), "south_entry_A_X7_Y-28.9": (south, 7.0, -28.9),
    "south_root_lip_X7_Y-28.5": (south, 7.0, -28.5), "south_root_lip_X-9.5_Y-28.5": (south, -9.5, -28.5),
    "south_coupon_lip_X7_Y-45": (south, 7.0, -45.0),
    "north_lip_X-7_Y39": (north, -7.0, 39.0), "north_slot_X0_Y39": (north, 0.0, 39.0),
}
for n, (o, mx, my) in pts.items():
    if o is None or not (model_bb[o][2] + 0.3 < my < model_bb[o][3] - 0.3):
        continue   # 试样件没有北段，也不含 Y −69
    out["probes"][n] = probe(o, mx, my)
# 内袋顶第一层：南段 X0 Y-69 上方第一层挤出的特征与该层 Bridge 线段的方向/长度
print(json.dumps(out, ensure_ascii=False, indent=1))
# 内袋顶桥接层：南段在 X0 Y-69 上方第一层的 Bridge 线段方向与长度（离开中缝看整条桥）
o = south
roof_probe = "south_slot_X0_Y-69" if "south_slot_X0_Y-69" in out["probes"] else "south_relief_X0_Y-45"
my_roof = -69.0 if roof_probe.endswith("-69") else -45.0
zr = min(z for z in out["probes"][roof_probe])
k = (O == o) & (np.abs(S[:, 4] - zr) < 1e-6) & np.array([f == "Bridge" for f in F])
P = S[k]
mx0, my0 = P[:, 0] - off[o][0], P[:, 1] - off[o][1]
mx1, my1 = P[:, 2] - off[o][0], P[:, 3] - off[o][1]
L = np.hypot(mx1 - mx0, my1 - my0); ang = np.degrees(np.arctan2(my1 - my0, mx1 - mx0)) % 180
mid = (np.abs((my0 + my1) / 2 - my_roof) < 4)
print(json.dumps({"roof_layer_z_bed": zr, "bridge_segments": int(k.sum()),
    "roof_probe": roof_probe, "bridge_len_near_probe_y": {"max": round(float(L[mid].max()), 2), "median": round(float(np.median(L[mid])), 2)},
    "bridge_angle_deg_hist": np.histogram(ang[mid], bins=[0, 10, 80, 100, 170, 180])[0].tolist(),
    "bridge_x_extent_near_probe_y": [round(float(min(mx0[mid].min(), mx1[mid].min())), 2), round(float(max(mx0[mid].max(), mx1[mid].max())), 2)]}, ensure_ascii=False))
