"""C08B 采集板第 2 页：电极接口与 16 路输入保护。
座子脚号由期望网表（叠 PCB 逐脚网名）推出，不写死：D7 起是 FH34SRJ-34S（34 芯 FPC 座），信号脚、BIAS、WCT、地脚都按网名找。
两只电极插座按 2 通道一段拆成多段符号，每段和它的 ESD → 15k 排阻 → 22pF 差分滤波画在同一框里，
连线一路直通；右侧标签接第 1 页 ADS 输入。C08B 两组（插座 1 CH01–08、插座 2 CH09–16）都全贴（16 路）。
D20 起 470pF 对地电容已删（sch.GONE），本页不再画。"""
import json
from sch import *

PAGE_REFS = [r for r in json.loads((SRC / 'page-map.json').read_text())[1]['refs'] if r not in GONE]
NET = {}  # 网名 → 本页 [(位号, 脚号)]
for (r, p), n in EXPECT.items():
    if r in PAGE_REFS: NET.setdefault(n, []).append((r, p))
ARR = [r for r in PAGE_REFS if VAL[r].startswith('15k')]

def other(net, kind):
    """在网 net 上找本页某类器件（'arr' 排阻 / 'esd' / 'cap470' / 'cap1n'）的 (位号, 脚号)。"""
    for r, p in NET[net]:
        if kind == 'arr' and r in ARR: return r, p
        if kind == 'esd' and VAL[r].startswith('ESD'): return r, p
        if kind == 'cap470' and VAL[r] == '470pF': return r, p
        if kind == 'cap1n' and VAL[r] == '22pF': return r, p   # D16：11-05 差分电容换 100 pF；D20 11-09 晚再换 22 pF

def esd(ref, x, y, show_val=False):
    """TVS 对地：1 脚（信号）在上接线，2 脚接地，阴极朝信号。"""
    pin(ref, '1', x, y); pin(ref, '2', x, y + 44)
    line([(x, y), (x, y + 14)]); line([(x, y + 30), (x, y + 44)])
    svg.append(f'<polygon points="{x-7},{y+30} {x+7},{y+30} {x},{y+16}" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    line([(x - 9, y + 13), (x - 7, y + 15), (x + 7, y + 15), (x + 9, y + 17)], w=1.8)
    text(ref, x + 8, y + 27, size=10, color=tcol(ref))
    if show_val: text(val(ref), x + 8, y + 39, size=9, color=tcol(ref))
    gnd(x, y + 44)

def vcap(ref, x, y1, y2, top_pin):
    """竖放电容，上脚在 y1、下脚在 y2，只标位号（料值写在列头）。"""
    pin(ref, top_pin, x, y1); pin(ref, '1' if top_pin == '2' else '2', x, y2)
    m = (y1 + y2) // 2
    line([(x, y1), (x, m - 3)]); line([(x, m + 3), (x, y2)])
    line([(x - 9, m - 3), (x + 9, m - 3)], w=2); line([(x - 9, m + 3), (x + 9, m + 3)], w=2)
    text(ref, x + 8, m + 13 if y2 - y1 < 60 else m - 7, size=10, color=tcol(ref))

def rarr(ref, x, rows):
    """4 联排阻：rows=[(y, 输入脚)]，输入脚 k 对应输出脚 9-k。"""
    for y, k in rows:
        pin(ref, k, x - 40, y); pin(ref, str(9 - int(k)), x + 40, y)
        line([(x - 40, y), (x - 15, y)]); line([(x + 15, y), (x + 40, y)])
        svg.append(f'<rect x="{x-15}" y="{y-5}" width="30" height="10" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
        text(k, x - 33, y - 4, size=8, color='#777', anchor='middle'); text(str(9 - int(k)), x + 33, y - 4, size=8, color='#777', anchor='middle')
    ys = [y for y, _ in rows]
    svg.append(f'<rect x="{x-22}" y="{min(ys)-14}" width="44" height="{max(ys)-min(ys)+28}" fill="none" stroke="{SYM}" stroke-width="1" stroke-dasharray="4 3"/>')
    text(ref, x, min(ys) - 20, size=11, color=tcol(ref), anchor='middle', weight='bold')

def channel_name(out_net):
    """V4_IN3P → CH03+，V4_IN3P2 → CH11+（第二颗 ADS 通道号加 8）。"""
    s = out_net[len('V4_IN'):]
    n, pol, two = int(s[0]), s[1], s.endswith('2')
    return f'CH{n + 8 * two:02d}{"+" if pol == "P" else "-"}'

BW, GAP = 395, 13
def conn_pins(conn):
    """插座在期望网表里的全部脚，数字脚按大小排，MP 放最后。"""
    ps = {p for r, p in EXPECT if r == conn}
    return sorted(ps, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, x))

def group(conn, y0, tag, side_title):
    """一只插座的 16 个通道脚（接到排阻的那些，按脚号排），按排阻分 4 框横排。"""
    sig = [p for p in conn_pins(conn) if p.isdigit() and other(EXPECT[(conn, p)], 'arr')]
    assert len(sig) == 16, (conn, sig)
    for k in range(4):
        bx = 30 + k * (BW + GAP)
        part = sig[4 * k:4 * k + 4]
        nets = [EXPECT[(conn, p)] for p in part]
        arr = other(nets[0], 'arr')[0]
        assert all(other(n, 'arr')[0] == arr for n in nets), (conn, part)   # 每框 4 脚同一颗排阻
        outs = [EXPECT[(arr, str(9 - int(other(n, 'arr')[1])))] for n in nets]
        chs = sorted({channel_name(o)[:4] for o in outs})
        block(bx, y0, bx + BW, y0 + 390, f'{tag} {"/".join(chs)} · {side_title}脚 {part[0]}–{part[-1]}',
              'ESD 对地 → 15k 限流 → 22pF 跨接')
        rows = [y0 + 90 + 76 * i for i in range(4)]
        ic(conn, bx + 10, rows[0] - 20, 38, 76 * 3 + 40,
           [(p, channel_name(o), 'R', 20 + 76 * i) for i, (p, o) in enumerate(zip(part, outs))], name=f'段{k + 1}')
        own(None)  # 列头是图纸说明，不属于插座
        for h, x in (('ESD', bx + 95), ('22pF', bx + 250)):
            text(h, x, y0 + 64, size=10, color='#666', anchor='middle')
        rarr(arr, bx + 160, [(y, other(n, 'arr')[1]) for y, n in zip(rows, nets)])
        for y, p, n, o in zip(rows, part, nets, outs):
            wire(Pn(conn, p), Pn(arr, other(n, 'arr')[1]))
            esd(other(n, 'esd')[0], bx + 95, y)
            wire(Pn(arr, str(9 - int(other(n, 'arr')[1]))), (bx + 315, y)); lab(o, bx + 315, y, 'right')
            assert other(o, 'cap470') is None, o   # D20：板上已无对地 470pF
        for i in (0, 2):  # 同一通道的 P/N 两行相邻，22pF 跨在两行之间
            c, p = other(outs[i], 'cap1n'); vcap(c, bx + 250, rows[i], rows[i + 1], p)

def misc(conn, x0, bias, wct, side_title):
    """插座的地、屏蔽、偏置驱动和 WCT 脚：BIAS/WCT 在右边出线，地脚（含固定焊盘 MP）在下沿横排并到一个地符号。"""
    pins = conn_pins(conn)
    pb = next(p for p in pins if EXPECT[(conn, p)] == bias)
    pw = next(p for p in pins if EXPECT[(conn, p)] == wct)
    gp = [p for p in pins if EXPECT[(conn, p)] == 'AGND']
    block(x0, 860, x0 + 800, 1080, f'{side_title}：地 / 屏蔽 / 偏置 / WCT', f'偏置驱动和 WCT 从第 1 页 ADS 引来，过 ESD 后到插座 {pb}、{pw} 脚；其余 {len(gp)} 脚（含固定焊盘 MP）接地')
    bx, by, w = x0 + 30, 950, 20 + 22 * len(gp)
    ic(conn, bx, by, w, 70, [(pb, 'BIAS', 'R', 15), (pw, 'WCT', 'R', 50)] + [(p, '', 'B', 20 + 22 * i) for i, p in enumerate(gp)], name_dy=40)
    r = bx + w + 20
    for p, net, ex in ((pb, bias, 40), (pw, wct, 100)):
        y = Pn(conn, p)[1]
        wire(Pn(conn, p), (r + 170, y)); lab(net, r + 170, y, 'right')
        esd(other(net, 'esd')[0], r + ex, y, show_val=net == wct)   # 偏置那颗的料号字会压到 WCT 线，只在下面一颗标
    wire(*[Pn(conn, p) for p in gp]); gnd(*Pn(conn, gp[-1]))

group('V4_FPC1', 160, 'A组', '插座1 ')

# B组：D2-8CH 表带软板贴肤触点 → 0402/0603 保护串阻 → V4_FPC1 34P 逐针映射框（补齐软板级限流与贴肤极性链路）
block(30, 568, 1649, 842,
      'B组  D2-8CH 表带软板贴肤触点与双级串阻映射（贴肤触点 → 软板 100k/200k → V4_FPC1 34P → 采集板 ESD + 15k + 22pF）',
      '采样腿：软板 R1–R16 (100kΩ 0402) + 采集板 V4_U3–U6 (15kΩ) = 115kΩ/腿；偏置腿：软板 EB1/EB2 各串 R33/R34 (200kΩ 0603) 汇入 33 脚 + V4_R34 (392kΩ) = 单点 592kΩ / 双点并联 492kΩ。')
own(None)
for yy in (632, 660, 688, 716, 744, 772, 800, 828):
    line([(46, yy), (1632, yy)], '#d0d5dd', 1)
for xx in (46, 390, 735, 1080, 1632):
    line([(xx, 632), (xx, 828)], '#d0d5dd', 1)
TABLE_ROWS = [
    ('盒底触点区（胶囊底面 6 触点）', '北短带区（腕带北段 4 触点）', '南长带前段（腕带南段 CH5–CH6）', '南长带后段与偏置/地（CH7–CH8 + BIAS/WCT/AGND）'),
    ('CH1+ : E1P (+8.0,+7.5) → R1 100k → 脚5 → U6.1-8 → IN1P', 'CH3+ : E3P 北1+ → R5 100k → 脚12 → U5.1-8 → IN3P', 'CH5+ : E5P 南1+ → R9 100k → 脚19 → U4.1-8 → IN5P', 'CH7+ : E7P 南3+ → R13 100k → 脚25 → U3.1-8 → IN7P'),
    ('CH1- : E1N (-8.0,+7.5) → R2 100k → 脚6 → U6.2-7 → IN1N', 'CH3- : E3N 北1- → R6 100k → 脚13 → U5.2-7 → IN3N', 'CH5- : E5N 南1- → R10 100k → 脚20 → U4.2-7 → IN5N', 'CH7- : E7N 南3- → R14 100k → 脚26 → U3.2-7 → IN7N'),
    ('CH2+ : E2P (+8.0,-7.5) → R3 100k → 脚9 → U6.3-6 → IN2P', 'CH4+ : E4P 北2+ → R7 100k → 脚15 → U5.3-6 → IN4P', 'CH6+ : E6P 南2+ → R11 100k → 脚22 → U4.3-6 → IN6P', 'CH8+ : E8P 南4+ → R15 100k → 脚28 → U3.3-6 → IN8P'),
    ('CH2- : E2N (-8.0,-7.5) → R4 100k → 脚10 → U6.4-5 → IN2N', 'CH4- : E4N 北2- → R8 100k → 脚16 → U5.4-5 → IN4N', 'CH6- : E6N 南2- → R12 100k → 脚23 → U4.4-5 → IN6N', 'CH8- : E8N 南4- → R16 100k → 脚29 → U3.4-5 → IN8N'),
    ('EB2 辅北 (0,+7.5) → R34 200k ─┐', '北段间距：同对差分中心距 20 mm', '南段间距：CH5–CH8 沿前臂环向排布', 'BIAS : 脚33 ← D910 ESD ← V4_R34 392k ← U1.63 RLDOUT'),
    ('EB1 辅南 (0,-7.5) → R33 200k ─┴→ 汇入脚33 V4_BIAS_DRV1', '盒底每排：大(P)—辅(EB)—大(N)', '软板金手指：插入 V4_FPC1（34P 0.5mm）', 'WCT : 脚32 (软板NC) · AGND : 1-4,7,8,11,14,17,18,21,24,27,30,31,34'),
]
for r_idx, cols in enumerate(TABLE_ROWS):
    yy = 651 + 28 * r_idx
    w_font = 'bold' if r_idx == 0 else 'normal'
    c_font = '#111' if r_idx == 0 else '#2b3a4a'
    for c_idx, txt_val in enumerate(cols):
        xx = (56, 400, 745, 1090)[c_idx]
        text(txt_val, xx, yy, size=10, color=c_font, weight=w_font)

misc('V4_FPC1', 440, 'V4_BIAS_DRV1', 'V4_WCT', '插座1（CH01–08 + BIAS/WCT）')

finish(2, '电极输入', PAGE_REFS, 'C08B 单面 8 通道采集板 电极输入：1 × 34 芯 FPC 座 → ESD → 15k → 22pF → ADS',
       '正面单面贴 A 组（插座 1 V4_FPC1，CH01–08 + BIAS_DRV1/WCT），B 组列出 D2-8CH 软板 100k/200k 串阻与贴肤触点映射；右侧标签接 P1 的 ADS1298（U1）。')
