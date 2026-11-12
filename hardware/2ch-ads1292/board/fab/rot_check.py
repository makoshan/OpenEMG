"""贴片坐标与转角核对（10-21）：KiCad 自带 Python 运行。python3 rot_check.py <板> <嘉立创封装目录> <输出 json>
嘉立创按自己库里的封装贴：CPL 的中心和转角要让「嘉立创封装」摆上去后焊盘和板上焊盘重合。
做法：对每个贴片位号，把板上焊盘换回封装本地坐标（背面件先撤销 y 镜像），和 easyeda2kicad 拉下来的该 C 号封装
按焊盘编号拟合出转角差 φ（0/90/180/270）和中心偏移 s，得到 CPL 应填的中心和角度（背面先撤销 y 镜像）；再把嘉立创封装按算出的值摆回去，
和板上焊盘逐个比，最大残差就是这个位号的核对结果。
约定：KiCad 板内坐标 y 向下、角度为 KiCad 朝向；正面 CPL 角 = r + φ；背面按 kicad-jlcpcb-tools 的约定
CPL 角 = (180 − (r − φ)) mod 360（背面这条无法离线证实，上传后以嘉立创预览为准）。
背面还有一种约定 CPL 角 = r − φ（嘉立创 EDA 导出实测）：两种在 r−φ 为 ±90 时相同，为 0/180 时差 180。本板背面只有 J2（r=−90、φ=0），两种都是 270；别的板要先定。CPL 的 Y = −y（和 kicad-cli pos 一致）。"""
import glob, json, math, os, re, sys
import pcbnew as k

pcb, lib, out = sys.argv[1], sys.argv[2], sys.argv[3]
FILL = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
circ = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
mm = k.ToMM
# 两家焊盘编号不同的料：我们的号 → 嘉立创的号（逗号分隔表示多个）
NUM_MAP = {'C88373': {'1': '2', '2': '1,3'},   # U.FL：我们 1=信号 2=地×2；嘉立创 2=信号 1/3=地
           'C127620': {'1': '1', '3': '2'}}   # 片式天线：我们 1+2（FEED+GND，Walsin 推荐图同一端）合为嘉立创 1=Feeding，我们 3=嘉立创 2
# 我们几个焊盘合起来对应嘉立创一个端子：先按中心合并再拟合（Walsin RFECA3216 推荐焊盘馈电端分 FEED/GND 两块）
MERGE = {'C127620': {'1': ['1', '2']}}
# ADS1292 载板 J2：信号脚 1–20 两家同号同位，只有两个固定脚 21/22 号相反，几何相同
NUM_MAP['C2802370'] = {**{str(i): str(i) for i in range(1, 21)}, '21': '22', '22': '21'}
# 转角已人工核过、残差来自两家焊盘尺寸/间距不同的料（2026-10-21 对照两边焊盘表）
MANUAL_OK = {
    'C43177583': 'ESD501DPYRQ1 X1SON-2：1/2 脚同向（1 脚在 0° 左侧）、中心偏 0，残差来自焊盘中心距 1.0 对 0.7；嘉立创焊盘比器件宽，按中心贴',
    'C2651570': 'TQFP-32：32/32 脚号重合、中心偏 0、φ 270（嘉立创 1 脚起点不同），残差来自两家焊盘行距不同',
    'C2802370': 'FH34SRJ-20S：1–20 脚同号同位，固定脚 21/22 号对调后重合，残差来自固定脚中心 5.75 对 5.80',
    'C2682010': 'SC-70-5：1–3 脚一排转到同侧，行距 1.68 对 2.2 mm',
    'C5832340': '0806 电感无极性，焊盘中心距 1.3 对 1.66 mm',
    'C43698': 'SOT-23-6：脚号与转角一致，焊盘行距不同',
    'C404027': 'SOT-23-5：脚号与转角一致，焊盘行距不同',
    'C408972': 'SOT-23-5（U9 TLV74333，10-24）：5/5 脚号重合、φ 180 与 U15 同，残差 0.195 同 U15，来自焊盘行距不同',
    'C127620': '片式天线 RFECA3216060A1T：嘉立创 2 端子、我们 3 焊盘（Walsin 推荐图），馈电端按 1+2 中心拟合；嘉立创焊盘 1 是否 = Feeding 离线未证实，上传后预览核',
    'C88373': 'U.FL：转角 0°，中心按两个地焊盘对齐，信号焊盘两家差约 0.28 mm，上传后预览核',
    'C5452647': '2016 有源晶振 Y5：4/4 焊盘同象限重合、φ=0°、中心偏移 0，残差 0.141 mm 来自两家焊盘中心距差 0.10 mm',
    'C15127': 'SOT-23 PMOS Q2（AO3401A）：3/3 脚按 G/S/D 名称重合、φ=0°，残差 0.283 mm 来自 SOT-23 跨距差',
    'C2135': 'SOT-23 双肖特基 D2（BAT54C）：3/3 脚按引脚名重合、φ=0°，残差 0.403 mm 来自 SOT-23 跨距差',
    # C08A 10-30：V4 库 0402 电容焊盘中心距 0.84 mm，嘉立创 0402 封装更宽；无极性、中心偏移 0、φ 与同料其它位号一致，残差 0.125 来自中心距差
    'C1525': '0402 100nF（V4 库焊盘）：无极性，中心偏移 0，φ 0/180 与同料一致，残差 0.125 来自焊盘中心距差',
    'C52923': '0402 1uF（V4 库焊盘）：同上',
    'C1524': '0402 1nF（V4 库焊盘）：同上',
}


def R(a, x, y):
    """KiCad 朝向 a 度把本地 (x, y) 转到板上（y 向下，视觉逆时针）。"""
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return x * c + y * s, -x * s + y * c


def easyeda_pads(c):
    fs = glob.glob(f'{lib}/{c}/jlc.pretty/*.kicad_mod')
    if not fs: return None
    t = open(fs[0]).read(); pads = {}
    for m in re.finditer(r'\(pad\s+"?([^"\s]*)"?\s+(smd|thru_hole|np_thru_hole)\s+\S+\s+\(at\s+([-\d.]+)\s+([-\d.]+)', t):
        n, x, y = m.group(1).rstrip("'"), float(m.group(3)), float(m.group(4))   # 同号的第二个焊盘嘉立创写成 1' / 2'
        if n: pads.setdefault(n, []).append((x, y))
    return pads


SYMLIB = os.environ.get('SYMLIB') or os.path.join(os.path.dirname(lib.rstrip('/')), 'eesym')
NORM = {'K': 'K', 'KA': 'K', 'CATHODE': 'K', 'C': 'K', 'A': 'A', 'ANODE': 'A'}
norm = lambda v: NORM.get(str(v).upper(), str(v).upper())


def easyeda_pinnames(c):
    """嘉立创符号的 编号 → 功能名（easyeda2kicad --symbol 拉到 SYMLIB/<C号>/jlc.kicad_sym）。"""
    fs = glob.glob(f'{SYMLIB}/{c}/jlc.kicad_sym')
    if not fs: return None
    t = open(fs[0]).read()
    return {num: norm(name) for name, num in re.findall(r'\(name "([^"]*)".*?\(number "([^"]*)"', t, flags=re.S)}


b = k.LoadBoard(pcb)
res = {}
for f in b.GetFootprints():
    ref = f.GetReference()
    p = circ.get(ref, {})
    lc = FILL.get(ref, {}).get('lcsc') or p.get('lcsc')
    if not lc or p.get('dnp'): continue
    ep = easyeda_pads(lc)
    r = f.GetOrientationDegrees(); bot = f.IsFlipped(); P0 = (mm(f.GetPosition().x), mm(f.GetPosition().y))
    loc = {}
    for q in f.Pads():
        bx, by = mm(q.GetPosition().x) - P0[0], mm(q.GetPosition().y) - P0[1]
        lx, ly = R(-r, bx, by)
        if bot: ly = -ly   # 撤销背面镜像：KiCad 翻面是 y 镜像（取反 x 会让 φ 多出 180，11-04 复核抓到 J2 贴反）
        if q.GetNumber(): loc.setdefault(q.GetNumber(), []).append((lx, ly))
    row = dict(ref=ref, lcsc=lc, side='Bottom' if bot else 'Top', kicad_x=round(P0[0], 4), kicad_y=round(-P0[1], 4), kicad_rot=r)
    if not ep:
        row.update(status='无嘉立创封装·极性未核' if ref.startswith(('D', 'LED', 'ESD', 'Q')) else '无嘉立创封装', cpl_x=row['kicad_x'], cpl_y=row['kicad_y'], cpl_rot=((180 - r) % 360) if bot else r % 360)
        res[ref] = row; continue
    # 3 脚以下的半导体（二极管、LED、ESD、MOS）按引脚功能名配对：两家编号可能相反（D1 B5819WS 嘉立创 1=A 2=K，我们 1=K），
    # 按编号配会贴反（10-21 独立复核抓到）。名字取我们 circuit.json 的 pin_names 和嘉立创符号的引脚名。
    polar = ref.startswith(('D', 'LED', 'ESD', 'Q')) and len(loc) <= 3
    sym = easyeda_pinnames(lc) if polar else None
    ours = {n: norm(v) for n, v in (p.get('pin_names') or {}).items()}
    if polar and sym and ours:
        byname = {v: n for n, v in sym.items()}
        if all(ours.get(n) in byname for n in loc):
            ep = {n: ep.get(byname[ours[n]], []) for n in loc}
            row['pin_map'] = {n: byname[ours[n]] for n in loc}
    if lc in MERGE:
        for n, parts in MERGE[lc].items():
            loc[n] = [v for q in parts for v in loc.pop(q, [])]
            loc[n] = [(sum(v[0] for v in loc[n]) / len(loc[n]), sum(v[1] for v in loc[n]) / len(loc[n]))]
    if lc in NUM_MAP and not polar:   # 换成嘉立创的编号
        ep = {n: [p for e in NUM_MAP[lc][n].split(',') for p in ep.get(e, [])] for n in NUM_MAP[lc]}
    if polar and 'pin_map' not in row:
        row.update(status='极性未核', cpl_x=row['kicad_x'], cpl_y=row['kicad_y'], cpl_rot=((180 - r) % 360) if bot else r % 360,
                   note='拿不到嘉立创符号引脚名，方向须在预览人工核')
        res[ref] = row; continue
    common = [n for n in loc if n in ep]
    best = None
    for phi in (0, 90, 180, 270):
        # 本地：k_i ≈ Rφ·e_i + s（按编号；同号多焊盘取均值）
        pairs = []
        for n in common:
            kx = sum(v[0] for v in loc[n]) / len(loc[n]); ky = sum(v[1] for v in loc[n]) / len(loc[n])
            ex = sum(v[0] for v in ep[n]) / len(ep[n]); ey = sum(v[1] for v in ep[n]) / len(ep[n])
            pairs.append(((kx, ky), R(phi, ex, ey)))
        if not pairs: continue
        sx = sum(a[0] - c[0] for a, c in pairs) / len(pairs); sy = sum(a[1] - c[1] for a, c in pairs) / len(pairs)
        err = max(math.hypot(a[0] - c[0] - sx, a[1] - c[1] - sy) for a, c in pairs)
        if best is None or err < best[0]: best = (err, phi, sx, sy)
    if best is None:
        row.update(status='焊盘编号对不上', common=0, cpl_x=row['kicad_x'], cpl_y=row['kicad_y'], cpl_rot=((180 - r) % 360) if bot else r % 360)
        res[ref] = row; continue
    err, phi, sx, sy = best
    my = -sy if bot else sy
    dx, dy = R(r, sx, my)
    P = (P0[0] + dx, P0[1] + dy)
    eff = (r + phi) % 360 if not bot else (r - phi) % 360          # 嘉立创封装在板上的实际视觉转角
    cpl_rot = eff if not bot else (180 - eff) % 360
    # 自检：把嘉立创封装按 (P, eff, 镜像) 摆回去，和板上焊盘逐个比
    worst = 0.0
    for n in common:
        for (ex, ey) in ep[n]:
            ly = -ey if bot else ey
            qx, qy = R(eff, ex, ly)
            bx, by = P[0] + qx, P[1] + qy
            group = MERGE.get(lc, {}).get(n, [n])   # 合并过的端子按板上那几个焊盘的中心比
            qs = [q for q in f.Pads() if q.GetNumber() in group]
            if len(group) > 1:
                cx, cy = sum(mm(q.GetPosition().x) for q in qs) / len(qs), sum(mm(q.GetPosition().y) for q in qs) / len(qs)
                d = math.hypot(cx - bx, cy - by)
            else:
                d = min(math.hypot(mm(q.GetPosition().x) - bx, mm(q.GetPosition().y) - by) for q in qs)
            worst = max(worst, d)
    row.update(status='ok' if worst < 0.1 else ('ok-人工核' if lc in MANUAL_OK and worst < 0.42 else '残差大'), note=MANUAL_OK.get(lc, ''), common=len(common), npads=len(loc), phi=phi, s=[round(sx, 4), round(sy, 4)],
               cpl_x=round(P[0], 4), cpl_y=round(-P[1], 4), cpl_rot=round(cpl_rot, 3), fit_err=round(err, 4), place_err=round(worst, 4))
    res[ref] = row
for v in res.values():   # 库里拉不到封装的阻容：无极性，0° 约定已由拉到的 0402/0603 同类件证实（φ 全 0）
    if v['status'] == '无嘉立创封装' and v['ref'][0] in 'RCL': v['status'] = 'ok-无极性两端件'
json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
st = {}
for v in res.values(): st[v['status']] = st.get(v['status'], 0) + 1
print('位号', len(res), st)
for v in res.values():
    if v['status'] != 'ok' or v.get('phi') or abs(v.get('s', [0, 0])[0]) > 0.01 or abs(v.get('s', [0, 0])[1]) > 0.01:
        print(' ', v['ref'], v['lcsc'], v['side'], v['status'], 'φ', v.get('phi'), 's', v.get('s'), '残差', v.get('place_err'), '编号重合', v.get('common'), '/', v.get('npads'))
