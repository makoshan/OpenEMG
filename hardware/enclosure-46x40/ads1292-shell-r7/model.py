"""R7 结构候选：完整载板（外形同 C08A）+ XIAO 焊 P44e 悬在板上 + 20P 排线 + 四孔立柱 + 东边 USB 开口。盒子比 R5 加厚。
载板外形、孔、窗从真实 .kicad_pcb 读，P44e 尺寸和背面件读板文件，XIAO 用官方 STEP，电池沿用 R5。名义几何，不含公差、焊锡、掰板毛刺。
uv run --no-project --python 3.12 --with build123d python model.py"""
import json, math, re, tempfile, zipfile
from pathlib import Path
import build123d as b
R = Path(__file__).resolve().parent
PCB = R.parents[1] / '2ch-ads1292/board/ads1292-2ch.kicad_pcb'
XIAO_STEP = R / 'sources/XIAO-nRF52840-v15.step'
Z0, TH = 2.3, .8                                # 板底、板厚
JH, PT, XH = 1.0, .8, 4.46                      # FH34 高、P44e 厚、XIAO 含 USB 高
ZP = Z0 + TH + JH; ZX = ZP + PT                 # P44e 底、XIAO 底
LID = ZX + XH + .5                              # 盖内面：XIAO 顶到盖留 0.5，同 R5 的门
DZ = LID - 8.9                                  # 比 R5 加高多少
P44 = R.parents[1] / 'common-mainboard/adapter-p44e-xiao/p44e.kicad_pcb'
CAV = (43.6, 37.6, 2.8)
ELECTRODES = {'E1': (-8, 7.5), 'E2': (8, 7.5), 'E3': (0, 7.5), 'E4': (-8, -7.5), 'E5': (8, -7.5), 'E6': (0, -7.5)}   # 照 C08B 盒底两排大—辅—大
ED = {'E1': 6, 'E2': 6, 'E3': 3, 'E4': 6, 'E5': 6, 'E6': 3}   # 11-11 Mako 定：大点 Φ6×2.0、辅点方形 3×3×2 镀金铜片（ED 对方块是 y 向边长；Φ4×2.0 买不到，Φ3×1.5 够不着腕，6×2.5 方条压 E6 旁信号孔）
EX = {'E3': 3.0, 'E6': 3.0}   # 方块沿 x 的边长
EH = {'E1': 2.0, 'E2': 2.0, 'E3': 2.0, 'E4': 2.0, 'E5': 2.0, 'E6': 2.0}   # 触点厚，平片；焊锡层未计
shape = lambda n, x, y, z, grow, h: box(x, y, z, EX[n] + grow, ED[n] + grow, h) if n in EX else cyl(x, y, z, ED[n] + grow, h)   # 触点本体（grow 0）和壳孔（grow 0.4）
T0 = Z0 - max(EH.values())   # 大点贴肤面（触点平面）的高度；壳和腕都从这里起算，板以上不动
YIN = min(7.5 - ED[n] / 2 for n in ED if EH[n] == max(EH.values()))   # 现在六片都参与取最小，大点 Φ6 决定（4.5）；只适用于平片：硬圆腕在平片上先碰内侧边；改回圆顶要改成 7.5
box = lambda x, y, z, w, l, h: b.Pos(x, y, z) * b.Box(w, l, h, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
cyl = lambda x, y, z, d, h: b.Pos(x, y, z) * b.Cylinder(d / 2, h, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
t = PCB.read_text(); c = lambda s: (float(s[0]) - 100, 100 - float(s[1]))


def loops():
    """Edge.Cuts 接成闭环，圆弧按三点离散。最大的环是外框，其余是板内孔。"""
    segs = []
    for m in re.finditer(r'\n\t\((gr_line|gr_arc)\n(.*?)\n\t\)', t, re.S):
        if '"Edge.Cuts"' not in m.group(2): continue
        q = {k: c(v) for k, *v in re.findall(r'\((start|mid|end) (-?[\d.]+) (-?[\d.]+)\)', m.group(2))}
        pts = [q['start'], q['end']]
        if 'mid' in q:
            (ax, ay), (bx, by), (cx, cy) = q['start'], q['mid'], q['end']
            d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
            uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
            r = math.hypot(ax - ux, ay - uy); a0, a1, a2 = (math.atan2(y - uy, x - ux) for x, y in (q['start'], q['mid'], q['end']))
            w = lambda v: (v - a0) % (2 * math.pi)
            sw = w(a2) if w(a1) < w(a2) else w(a2) - 2 * math.pi
            pts = [(ux + r * math.cos(a0 + sw * i / 16), uy + r * math.sin(a0 + sw * i / 16)) for i in range(17)]
        segs.append(pts)
    out = []
    while segs:
        loop = segs.pop(0)
        while math.dist(loop[0], loop[-1]) > .01:
            for i, s in enumerate(segs):
                if math.dist(s[0], loop[-1]) < .01: loop += s[1:]; segs.pop(i); break
                if math.dist(s[-1], loop[-1]) < .01: loop += s[-2::-1]; segs.pop(i); break
            else: raise SystemExit('板框不闭合')
        out.append(loop[:-1])
    return sorted(out, key=lambda l: -(max(p[0] for p in l) - min(p[0] for p in l)))


def holes():
    out = {}
    for m in re.finditer(r'\n\t\(footprint "ads:HOLE_1P7"(.*?)\n\t\)', t, re.S):
        r = re.search(r'\(property "Reference" "(H\d)"', m.group(1)).group(1); a = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)', m.group(1))
        out[r] = c(a.groups())
    return out


L = loops(); H = holes(); assert len(L) == 1 and len(H) == 4, (len(L), H)
prism = lambda p, z, h: b.Pos(0, 0, z) * b.extrude(b.make_face(b.Polyline(*p, close=True)), amount=h)
board = prism(L[0], Z0, TH)
for p in L[1:]: board -= prism(p, Z0 - .1, TH + .2)
for x, y in H.values(): board -= cyl(x, y, Z0 - .1, 1.7, TH + .2)
parts = {'board_ADS1292_REAL_OUTLINE': board}
# 电极：平片焊在板底焊盘上（载板已取消 BAT 窗与线孔，六片 100% 落在实心板底；E4 片下有 GND 孔垫 Kapton；辅点方块 3×3 盖住 Φ3 盘）
for n, (x, y) in ELECTRODES.items():
    parts[f'metal_contact_{n}_ASSUMED'] = shape(n, x, y, Z0 - EH[n], 0, EH[n])
    sup = shape(n, x, y, Z0, 0, .1); assert abs(sum(s.volume for s in (sup & board).solids()) - sup.volume) < 1e-3, f'{n} 悬空越出实心板底'
# 电池和托架：比 R4 西移 0.4，给 XIAO 西端让位
BX = -10.8
parts['battery_LP302025_MAX'] = box(BX, 0, 4.9, 20.5, 27, 3.3)
parts['battery_insulation_adhesive_ASSUMED'] = box(BX, 0, 4.8, 20.5, 27, .1)
tray = box(BX, 0, 4.5, 21.7, 28.4, .3)
for y in (-14.8, 14.8): tray += box(-9, y, 3.1, 3, 1.2, 1.7) + box(-9, y / abs(y) * 14.2, 4.5, 3, 1.2, .3)
parts['battery_tray_INSULATING_ASSUMED'] = tray
# P44e：17.78×21×0.8，俯视转到 USB 朝东。载板 x = 21.5 − P44e y，y = 8.89 − P44e x（BAT 槽和载板窗重合，核过）
q = P44.read_text(); bx = lambda px, py: (21.5 - py, 8.89 - px)
p44 = box(11, 0, ZP, 21, 17.78, PT) - box(12.25, 4.44, ZP - .1, 3.7, 3.1, PT + .2)
parts['p44e_real_size'] = p44
back = None
for r, w, l in (('R1', 1, .5), ('R2', 1, .5), ('R3', 1, .5), ('R4', 1, .5), ('R5', 1, .5), ('C1', 1.6, .8)):
    m_ = re.findall(r'\n\t\(footprint.*?\n\t\t\(at ([-\d.]+) ([-\d.]+)[^\n]*\n(?:(?!\n\t\(footprint).)*?\(property "Reference" "%s"' % r, q, re.S)[0]
    x, y = bx(float(m_[0]), float(m_[1])); s = box(x, y, ZP - .55, l, w, .55); back = s if back is None else back + s
parts['p44e_back_parts_ENVELOPE'] = back
# J1：P44e 背面；J2：载板顶面。本体按封装 Fab 层
parts['J1_FH34_on_P44e'] = box(12, -6.79, Z0 + TH, 11.4, 3.8, JH)
j2 = re.search(r'\(footprint "p44:Hirose_FH34SRJ-20S-0.5SH".*?\(at (-?[\d.]+) (-?[\d.]+)', t, re.S); jx, jy = c(j2.groups())   # 落位读板
parts['J2_FH34_on_carrier'] = box(jx, jy - 1.4, Z0 + TH, 11.4, 3.8, JH)
# 泡棉：分置 P44e 槽东西两侧托住北半边，让开 x = 9.2..15.0 的电池线北出走廊，1 mm 双面胶，假设
parts['foam_1mm_ASSUMED'] = box(17.8, 7.4, Z0 + TH, 5.6, 2.4, JH) + box(7.4, 7.4, Z0 + TH, 3.6, 2.4, JH)
# XIAO：官方 STEP，USB 朝东，底贴 P44e 面
m = b.import_step(XIAO_STEP).rotate(b.Axis.X, 90)
ux, uy = .45, 8.9   # 同直焊版中心，USB 开口位置同 C08A（载板缺口 11-12 已拿掉）
bb = m.bounding_box(); m = m.translate((ux + 21.05 + 1.52 - bb.max.X, uy - 8.9 - (bb.min.Y + bb.max.Y) / 2, ZX - bb.min.Z))   # PCB 东端 + USB 外伸 1.52（官方 STEP）
parts['xiao_official'] = m
# 排线：J1 南口出，上拱，过 J2 上方，南边下落回折，从南口进 J2。折线平行 X，导体 X 不变。按聚硕 JS05A-20P-020-3-4（C22434842）：长 20、补强 4、宽 10.5
FFC = [(-8.72, 3.6), (-10.1, 3.6), (-10.6, 4.4), (-11.3, 6.7), (-12.1, 7.2), (-15.3, 7.2), (-16.1, 6.7), (-16.75, 4.5), (-16.65, 3.9), (-16.1, 3.6), (jy - 3.35, 3.6)]   # 前 1.4 mm 是补强段，直
def strip(pts, w):
    up, dn = [], []
    for i, (y, z) in enumerate(pts):
        a_, e_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]; dy, dz = e_[0] - a_[0], e_[1] - a_[1]; L_ = math.hypot(dy, dz); ny, nz = -dz / L_ * w / 2, dy / L_ * w / 2
        up.append((y + ny, z + nz)); dn.append((y - ny, z - nz))
    return up + dn[::-1]
parts['ffc_20P_0p5'] = b.extrude(b.Plane.YZ.offset(6.75) * b.make_face(b.Polyline(*strip(FFC, .2), close=True)), amount=10.5)
ffc_free = sum(math.dist(p, q_) for p, q_ in zip(FFC, FFC[1:]))
# 板上件包络：U3 1.45、Q1 约 1.25、U1 1.2 是最高的，Q1 到托架底 0.15 未入模型
parts['R14_ENVELOPE'] = box(3.55, 7.5, 3.1, 1.6, .8, .55); parts['R16_ENVELOPE'] = box(3.55, -7.5, 3.1, 1.6, .8, .55); parts['R7_ENVELOPE'] = box(8.0, -2.9, 3.1, .8, 1.6, .55); parts['D5_ENVELOPE'] = box(8.35, -0.7, 3.1, 1.0, .6, .4)   # P44e 投影下的 0603 与 D5 X1SON-2
parts['C16_ENVELOPE'] = box(2.4, -10.1, 3.1, 1.6, .8, .9)   # 10 µF 0603 按 0.9 高
parts['U1_ENVELOPE'] = box(-8, .5, 3.1, 7, 7, 1.2); parts['U3_ENVELOPE'] = box(1.4, 15.4, 3.1, 1.75, 3.05, 1.45) + box(1.4, 15.4, 3.1, 3.0, 2.2, .6)   # SOT-23-5 本体最高 1.45，脚低
# 电池线（11-12 Mako 定）：焊 XIAO 背面 BAT+/BAT− → 穿 P44e 槽 → 沿两板间 1.0 mm 无件空隙北出 P44e 边与盖北筋下沿（z 4.2）→ 上升走北侧上层走廊进电池北端。板底贴肤侧 0 走线；线径 0.4 是假设
def wire(name, pts, d=.4):
    q = None
    for A, B in zip(pts, pts[1:]):
        mid = [(a + e) / 2 for a, e in zip(A, B)]; dims = [max(abs(a - e), d) for a, e in zip(A, B)]
        s = box(mid[0], mid[1], mid[2] - dims[2] / 2, *dims); q = s if q is None else q + s
    parts[name] = q
WM = Z0 + TH + JH / 2   # P44e（底 4.1）与载板无件面（顶 3.1）夹层中线 z = 3.6，上下各留 0.3
for i, (px, wy, ex) in enumerate(((11.26, 15.6, -14.0), (13.17, 16.3, -15.0))):
    wire(f'battery_wire_{i}', [(px, 4.45, ZX - .05), (px, 4.45, WM), (px, 10.3, WM), (px, 12.0, 6.3), (px, wy, 6.3), (ex, wy, 6.3), (ex, 13.5, 6.3)])
for i, (x, y) in enumerate(H.values()):
    parts[f'pcb_screw_M1p6_ASSUMED_{i}'] = cyl(x, y, 1.0 + T0, 1.6, 2.1 - T0) + cyl(x, y, 3.1, 2.8, .6)
# 壳：外形同 R4；立柱到 C08A 孔位；USB 开口移到东墙
shell = (b.Pos(0, 0, .6 + T0) * b.extrude(b.RectangleRounded(46, 40, 4), amount=LID - .6 - T0)) - (b.Pos(0, 0, 1.2 + T0) * b.extrude(b.RectangleRounded(*CAV), amount=LID - 1.1 - T0))   # 壳沿平到盖内面，盖坐上去厚度才算数
for n, (x, y) in ELECTRODES.items(): shell -= shape(n, x, y, .5 + T0, .4, .8)   # 孔比触点大 0.4，孔位同 C08B
# 壳底中线做凹（11-10 Mako 定）：六个触点都在 |y| = 7.5，平壳底下硬腕先碰壳底中线、触点悬空。
# 按最小腕围 WMIN 的圆腕过两排触点尖，再让开 GAP，沿 x 整条挖掉；腕越粗弧越平，都落在槽里。槽顶以上内侧按 FLOOR 加厚
WMIN, GAP, FLOOR = 155, .1, .5
RW = WMIN / 2 / math.pi; WTOP = RW - math.sqrt(RW ** 2 - YIN ** 2) + GAP           # 槽顶（y = 0）离触点平面的高度；Φ6 平片时只有约 0.5，低于壳外凸 0.6，槽实际挖不到壳
along_x = lambda r, zc: b.Pos(0, 0, zc + T0) * b.Rot(0, 90, 0) * b.Cylinder(r, 60)
shell -= along_x(RW, WTOP - RW)
# 加厚段是两圆柱之间的环，只取腔内那段：从腔底平面起算会把槽顶 1.2 以上那段填回去（11-10 复核抓到，155 腕只让开 0.032）
KEEL = WTOP + FLOOR > 1.2   # 槽顶加厚后高过壳腔底才要加厚段
if KEEL:
    keel = (along_x(RW + FLOOR, WTOP - RW) - along_x(RW, WTOP - RW)) & (b.Pos(0, 0, 1.2 + T0) * b.extrude(b.RectangleRounded(*CAV[:2], 2.8), amount=WTOP + FLOOR - 1.2 + .01))
    for n, (x, y) in ELECTRODES.items(): keel -= shape(n, x, y, .5 + T0, .4, 3)
    shell += keel
for x, y in H.values(): shell += cyl(x, y, 1.2 + T0, 3.2, 1.1 - T0); shell -= cyl(x, y, .9 + T0, 1.3, 1.5 - T0)   # M1.6 自攻底孔 φ1.3，假设
shell -= box(22.4, 0, ZX - .1, 4, 10.6, LID - ZX + .1)   # 开口跟 XIAO 抬高，上沿由盖封住
parts['shell'] = shell
lid = b.Pos(0, 0, LID) * b.extrude(b.RectangleRounded(46, 40, 4), amount=.8)
lip = (b.Pos(0, 0, LID - .5) * b.extrude(b.RectangleRounded(43.2, 37.2, 2.6), amount=.5)) - (b.Pos(0, 0, LID - .6) * b.extrude(b.RectangleRounded(42, 36, 2), amount=.7))
lip -= box(21.6, 0, LID - .6, 2, 11, .7)   # USB 上方让开
# P44e 限位：盖上伸下三根筋，西边接 USB 插入力，南北防横移。东边靠东墙。FH34 不能受拉推，力要走筋不走排线
RB = LID - 4.85                                                  # 西筋下沿高过托架 4.8
rib = box(-.05, 0, 4.85, .9, 10, RB) + box(3.2, -9.3, 4.2, 4, .6, LID - 4.2) + box(11, 9.3, 4.2, 10, .6, LID - 4.2)
parts['lid'] = lid + lip + rib
for n, q in parts.items(): q.label = n
b.export_step(b.Compound(children=list(parts.values())), R / 'host.step')

# ---- 检查 ----
def vol(a, e):
    A, E = a.bounding_box(), e.bounding_box()
    if any(min(getattr(A.max, k), getattr(E.max, k)) - max(getattr(A.min, k), getattr(E.min, k)) < 1e-6 for k in 'XYZ'): return 0.
    return sum(sum(x.volume for x in (u & v).solids()) if (u & v) else 0 for u in a.solids() for v in e.solids())
names = list(parts); hits = []; intent = []
OK = lambda a, e: ('screw' in a and e == 'shell') or ('screw' in e and a == 'shell')
for i, a in enumerate(names):
    for e in names[i + 1:]:
        v = vol(parts[a], parts[e])
        if v > 1e-4: (intent if OK(a, e) else hits).append([a, e, round(v, 4)])
xs = [p[0] for p in L[0]]; ys = [p[1] for p in L[0]]; xb = parts['xiao_official'].bounding_box()
gap = {'板到东西壁': round(CAV[0] / 2 - max(max(xs), -min(xs)), 3), '板到南北壁': round(CAV[1] / 2 - max(max(ys), -min(ys)), 3),
       'XIAO 顶': round(xb.max.Z, 3), 'XIAO 顶到盖': round(LID - xb.max.Z, 3), 'XIAO 到托架': round(parts['xiao_official'].distance_to(tray), 3),
       'XIAO 到电池': round(parts['xiao_official'].distance_to(parts['battery_LP302025_MAX']), 3), 'USB 前沿': round(xb.max.X, 3), '壳外面 x': 23.0,
       'U3 到托架': round(parts['U3_ENVELOPE'].distance_to(tray), 3), 'U1 顶到托架底': round(4.5 - (Z0 + TH + 1.2), 3), '电池顶到盖唇': round(LID - .5 - 8.2, 3), '盖内面': round(LID, 3), '盒总厚': round(LID + .8 - T0, 3), '排线露出段': round(ffc_free, 2), '排线总长估': round(ffc_free + 2 * 2.6, 2), '排线顶到盖': round(LID - 7.3, 3), 'P44e 西到筋': round(.5 - .4, 3), 'P44e 南北到筋': round(9.0 - 8.89, 3), 'P44e 东到墙': round(21.8 - 21.5, 3)}
wc = min((round(parts[f'battery_wire_{i}'].distance_to(parts[f'metal_contact_{n}_ASSUMED']), 3), f'线 {i} 对 {n}') for i in (0, 1) for n in ELECTRODES)   # 电池线全在板上方，与板底触点隔整块载板
gap['电池线到触点最近'] = wc
gap['电池线到载板顶'] = round(min(parts[f'battery_wire_{i}'].distance_to(board) for i in (0, 1)), 3)
gap['电池线到P44e'] = round(min(parts[f'battery_wire_{i}'].distance_to(p44) for i in (0, 1)), 3)
gap['电池线到盖'] = round(min(parts[f'battery_wire_{i}'].distance_to(parts['lid']) for i in (0, 1)), 3)
gap['电池线到板上件最近'] = min((round(parts[f'battery_wire_{i}'].distance_to(parts[k]), 3), f'线 {i} 对 {k}') for i in (0, 1) for k in ('U3_ENVELOPE', 'R14_ENVELOPE', 'foam_1mm_ASSUMED', 'battery_tray_INSULATING_ASSUMED'))
# 腕型：155、190、230 腕围的圆腕过六个触点尖，不能碰壳；平壳底同样摆 190 必撞（反例）
wrist = lambda C: (lambda r: along_x(r, (r - math.sqrt(r * r - YIN ** 2)) - r))(C / 2 / math.pi)   # 圆腕压在大片内侧边上
gap['腕型碰壳'] = {C: round(vol(wrist(C), shell), 4) for C in (155, 190, 230)}
gap['腕到壳最近'] = {C: round(wrist(C).distance_to(shell), 3) for C in (155, 190, 230)}   # 实测；平片时由壳外凸量决定，不再约等于 GAP
neg_140 = vol(wrist(155).translate((0, 0, gap['腕到壳最近'][155] + .05)), shell)   # 反例：触点再矮一点（比余量多 0.05），腕必碰壳
gap['壳底槽顶高（设计）'] = round(WTOP, 3); gap['加厚段'] = KEEL
if KEEL: gap['电池线离加厚段'] = round(parts['battery_wire_0'].distance_to(keel), 3)
gap['辅点离腕（硬腕）'] = {C: round(min(wrist(C).distance_to(parts[f'metal_contact_{n}_ASSUMED']) for n in ('E3', 'E6')), 3) for C in (155, 190, 230)}
gap['大点凸出壳外'] = round(shell.bounding_box().min.Z - min(parts[f'metal_contact_{n}_ASSUMED'].bounding_box().min.Z for n in ED if n not in EX), 3)
pinch_wire = box(11.26, 7.4, WM - .55, 1.1, 4.0, 1.1)   # 反例：夹层处线径粗到 1.1 必同时被载板和 P44e 夹住
neg_pinch = min(vol(pinch_wire, board), vol(pinch_wire, p44))
flat = (b.Pos(0, 0, .6 + T0 - .3) * b.extrude(b.RectangleRounded(46, 40, 4), amount=1))
neg_wrist = vol(wrist(155), flat)   # 反例：壳外凸只剩 0.3 时 155 腕必碰平壳
big = prism([(-22, -19), (22, -19), (22, 19), (-22, 19)], Z0, TH); neg = vol(big, shell)     # 反例：44×38 必撞壳
up = vol(parts['xiao_official'].translate((0, 0, 1.4)), parts['lid'])                         # 反例：XIAO 抬 1.4 必撞盖
old = vol(parts['xiao_official'], parts['lid'].translate((0, 0, -DZ)))                           # 反例：盖留在 R5 高度必撞 XIAO
rep = dict(hits=hits, intent=intent, gaps=gap, negative_wire_pinched=round(neg_pinch, 4), negative_flat_shell0p3_wrist155=round(neg_wrist, 3), negative_wrist155_up=round(neg_140, 3), negative_44x38_shell=round(neg, 2), negative_xiao_up_lid=round(up, 2), negative_r5_lid=round(old, 2), size=[round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)])
(R / 'checks.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1)); print(json.dumps(rep, ensure_ascii=False))
assert not hits and neg_pinch > 0 and neg > 0 and up > 0 and old > 0 and neg_wrist > 0 and neg_140 > 0 and not any(gap['腕型碰壳'].values()) and gap['腕到壳最近'][155] >= GAP - .005 and gap['电池线到载板顶'] >= .25 and gap['电池线到P44e'] >= .25 and gap['电池线到盖'] >= .2 and gap['大点凸出壳外'] >= .5
assert gap['板到东西壁'] >= .2 and gap['板到南北壁'] >= .2 and gap['XIAO 顶到盖'] >= .5 and gap['XIAO 到托架'] >= .2 and gap['USB 前沿'] <= 23.05

sh_out = parts['shell'].solids()[0] if len(parts['shell'].solids()) == 1 else b.Compound(children=list(parts['shell'].solids()))
ld_out = parts['lid'].solids()[0] if len(parts['lid'].solids()) == 1 else b.Compound(children=list(parts['lid'].solids()))
b.export_step(sh_out, R / 'shell.step')
b.export_step(ld_out, R / 'lid.step')
b.export_stl(sh_out, R / 'ads1292-r7-shell.stl', tolerance=.01, angular_tolerance=.1)
b.export_stl(ld_out, R / 'ads1292-r7-lid.stl', tolerance=.01, angular_tolerance=.1)
print('R7 名义几何：通过')
