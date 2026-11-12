# 统计南段表带（Y 跨度最长的对象）和北段（另一个对象）每个含 Bridge 的层：沿 Y / 沿 X 的挤出占比、最长直线段
import re, sys, zipfile, json, math
import numpy as np
from collections import defaultdict
gz = zipfile.ZipFile(sys.argv[1]).read("Metadata/plate_1.gcode").decode()
# 盘上只有一个对象时 Bambu 不写对象标记：整盘挤出都算对象 0
LABELED = "; start printing object" in gz
z = 0; feat = None; obj = None if LABELED else 0; x = y = None
seg = defaultdict(list); ext_by_obj = defaultdict(list)
for ln in gz.splitlines():
    if ln.startswith("; Z_HEIGHT:"): z = float(ln.split(":")[1])
    elif ln.startswith("; FEATURE:"): feat = ln.split(":", 1)[1].strip()
    elif ln.startswith("; start printing object, unique label id:"): obj = int(ln.rsplit(":", 1)[1])
    elif ln.startswith("; stop printing object") and LABELED: obj = None
    elif ln[:2] in ("G1", "G0", "G2", "G3"):
        m = dict((k, float(v)) for k, v in re.findall(r"([XYZEIJ])([-\d.]+)", ln.split(";")[0]))
        nx, ny = m.get("X", x), m.get("Y", y)
        if ln[:2] in ("G1", "G2", "G3") and m.get("E", 0) > 0 and x is not None and obj is not None:
            L = math.hypot(nx - x, ny - y)
            if ln[:2] in ("G2", "G3"):   # 圆弧：长度按弧长算（复核指出旧版漏了 G2/G3），方向按弦
                cx, cy = x + m.get("I", 0), y + m.get("J", 0)
                a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                sw = (a0 - a1) if ln[:2] == "G2" else (a1 - a0)
                sw = sw % (2 * math.pi) or 2 * math.pi
                L = math.hypot(x - cx, y - cy) * sw
            ext_by_obj[obj].append((x, y, nx, ny))
            if feat == "Bridge": seg[(obj, z)].append((x, y, nx, ny, L))
        x, y = nx, ny
span = {o: np.ptp(np.array(v)[:, [1, 3]]) for o, v in ext_by_obj.items()}
xspan = {o: np.ptp(np.array(v)[:, [0, 2]]) for o, v in ext_by_obj.items()}
south = max(span, key=span.get)
north = min(span, key=span.get) if len(span) > 1 else None   # 单对象（试样件）没有北段


def layers(obj):
    out = {}
    for (o, zz), s in sorted(seg.items(), key=lambda kv: kv[0][1]):
        if o != obj: continue
        a = np.array(s); dx = a[:, 2] - a[:, 0]; dy = a[:, 3] - a[:, 1]
        L = a[:, 4]; ang = np.degrees(np.arctan2(dy, dx)) % 180
        if L.sum() < 50: continue   # 只看大面积桥（内袋顶），忽略孔边小桥
        alongY = L[(ang > 80) & (ang < 100)].sum() / L.sum()
        alongX = L[(ang < 10) | (ang > 170)].sum() / L.sum()
        out[zz] = {"bridge_len_mm": round(float(L.sum()), 1), "frac_along_Y": round(float(alongY), 3),
                   "frac_along_X": round(float(alongX), 3), "longest_single_move_mm": round(float(L.max()), 2)}
    return out


# 摆盘不旋转时两条表带都是 Y 长 X 短（南 ~118.7 × 23.2、北 ~35.9 × 23.6）；打出来核对，转了就别信沿 X/Y 的结论
print(json.dumps({"file": sys.argv[1], "object_xy_span_mm": {str(o): [round(float(xspan[o]), 1), round(float(span[o]), 1)] for o in span},
                  "south_bridge_layers": layers(south), "north_bridge_layers": layers(north) if north is not None else {}}, ensure_ascii=False))
