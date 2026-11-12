"""核对南北表带切片：①内袋顶横跨（加修改器的过、不加的对照不过）②南段每道剪线缺口真的打出来、没剪线的段没有 ③估时耗料。
剪线判据同 slice_keeper_test.sh：床面 Z≈1.2 那层，剪线 ±0.8 内外墙要拐进到 |x−中线| 9.7..10.05，左右两侧都要有。"""
import json, re, struct, subprocess, sys, zipfile
here, lr, plain, south_stl = sys.argv[1:5]
sys.path.insert(0, here)
src = open(f'{here}/../build.py', encoding='utf-8').read()
marks = [float(v) for v in re.findall(r'-\d+\.\d+', re.search(r'TRIM_MARKS = \{(.*?)\}', src, re.S).group(1))]
def stl_bbox(p):
    b = open(p, 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
    xs, ys, zs = [], [], []
    for i in range(n):
        v = struct.unpack('<12f', b[84 + 50 * i: 84 + 50 * i + 48])[3:]
        xs += v[0::3]; ys += v[1::3]; zs += v[2::3]
    return min(xs), max(xs), min(ys), max(ys), min(zs)
def bridges(f):
    return json.loads(subprocess.check_output(['python3', f'{here}/bridges.py', f]))
def across(b, k):
    return b[k]['1.0']['frac_along_X'] > 0.9
B, P = bridges(lr), bridges(plain)
res = {'roof_across': {'south': across(B, 'south_bridge_layers'), 'north': across(B, 'north_bridge_layers')},
       'control_plain_south_not_across': not across(P, 'south_bridge_layers')}
g = zipfile.ZipFile(lr).read('Metadata/plate_1.gcode').decode()
head = g[:20000]
res['estimate'] = {k: m.group(1).strip() for k, pat in (('time', r'total estimated time: ([^;\n]+)'), ('filament_g', r'total filament weight \[g\] : ([\d.]+)')) if (m := re.search(pat, head))}
objs, cur, z = {}, None, 0.0
for line in g.splitlines():
    m = re.match(r'; start printing object, unique label id: (\d+)', line)
    if m: cur = m.group(1); continue
    if line.startswith('; stop printing object'): cur = None; continue
    mz = re.match(r'G1 Z([\d.]+)', line)
    if mz: z = float(mz.group(1))
    m = re.match(r'G[123] (?:.*?)X([-\d.]+) Y([-\d.]+)(.*)', line)
    if m and cur and ' E' in m.group(3):
        objs.setdefault(cur, []).append((z, float(m.group(1)), float(m.group(2))))
span = {k: max(y for _, _, y in v) - min(y for _, _, y in v) for k, v in objs.items()}
sk = max(span, key=span.get)          # 南段是最长的那个对象
pts = objs[sk]
x0, x1, y0, y1, zmin = stl_bbox(south_stl)
px0, px1 = min(x for _, x, _ in pts), max(x for _, x, _ in pts)
py0, py1 = min(y for _, _, y in pts), max(y for _, _, y in pts)
ox, oy = (px0 + px1) / 2 - (x0 + x1) / 2, (py0 + py1) / 2 - (y0 + y1) / 2   # 模型 → 床面平移（--orient 0 不转）
layers = sorted({zz for zz, _, _ in pts}); zl = min(layers, key=lambda v: abs(v - 1.2))
lay = [(x - ox, y - oy) for zz, x, y in pts if zz == zl]
def notch(ylo, yhi):
    side = {s: any(9.7 <= s * x <= 10.05 and ylo <= y <= yhi for x, y in lay) for s in (1, -1)}
    return side[1] and side[-1]
res['south_label'] = sk; res['probe_layer_z'] = zl
res['notches'] = {f'{m:.2f}': notch(m - 0.8, m + 0.8) for m in marks}
res['control_band_-148_-140_has_notch'] = any(9.7 <= abs(x) <= 10.05 and -148 <= y <= -140 for x, y in lay)
ok = all(res['roof_across'].values()) and res['control_plain_south_not_across'] and all(res['notches'].values()) and not res['control_band_-148_-140_has_notch'] and len(marks) == 12
res['pass'] = ok
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if ok else 1)
