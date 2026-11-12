"""C08A 第 1 页：两颗 ADS1298 采集核心。12 颗 ADS 去耦（V4_C31–C36 正面 U1、V4_C117–C122 背面 U2）从原第 3 页移来贴芯片画。
两颗 ADS 画法相同，用 ads() 按偏移复用；64 脚按 R10：输入/数字口用贴脚标签，电源、参考、VCAP、RLD/WCT 回路用实线。"""
import json
from sch import *

DECAP = ['V4_C31', 'V4_C32', 'V4_C33', 'V4_C34', 'V4_C35', 'V4_C36']
PAGE_REFS = [r for r in json.loads((SRC / 'page-map.json').read_text())[0]['refs'] + DECAP if r not in GONE]

# ADS1298 PAG 脚位：左=模拟输入与测试脚，右=数字口与地，上=电源与 RLD/WCT，下=负电源/参考/VCAP/NC
INPUTS = [(str(16 - i), ('IN%d%s' % (i // 2 + 1, 'P' if i % 2 == 0 else 'N'))) for i in range(16)]
SIGNALS = [('34', 'DIN'), ('40', 'SCLK'), ('39', 'CS'), ('43', 'DOUT'), ('47', 'DRDY'), ('38', 'START'), ('36', 'RESET'),
           ('35', 'PWDN'), ('37', 'CLK'), ('45', 'GPIO3'), ('52', 'CLKSEL')]
GNDS = [('41', 'DAISY_IN'), ('42', 'GPIO1'), ('44', 'GPIO2'), ('46', 'GPIO4'), ('31', 'RESV1'), ('33', 'DGND'), ('49', 'DGND'),
        ('51', 'DGND'), ('60', 'RLDREF'), ('62', 'RLDIN')]
AVDD, AVSS, DVDD = ['19', '21', '22', '54', '56', '59'], ['20', '23', '25', '32', '53', '57', '58'], ['48', '50']

def capq(ref, x, y, o):
    """竖向电容，标注三行（位号/料值/8路不贴），给底排 66 间距用；连接与 sch.cap 相同。"""
    a, b = (x, y - 40), (x, y + 40)
    if o == 'vr': a, b = b, a
    pin(ref, '1', *a); pin(ref, '2', *b)
    line([(x, y - 40), (x, y - 4)]); line([(x, y + 4), (x, y + 40)])
    line([(x - 12, y - 4), (x + 12, y - 4)], w=2); line([(x - 12, y + 4), (x + 12, y + 4)], w=2)
    v, c = val(ref).split(' 8路不贴')[0], tcol(ref)
    text(ref, x + 12, y - 3, color=c); text(v, x + 12, y + 11, color=c)
    if ref in DNP8: text('8路不贴', x + 12, y + 25, color=c)

def tp(ref, x, y):
    """测试点：圆在右，脚朝左。"""
    pin(ref, '1', x - 20, y); line([(x - 20, y), (x - 6, y)])
    svg.append(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    text(ref, x + 10, y + 4)

def ads(dx, u, c, title, note):
    """c：本颗外围件位号表。dx：整框横向偏移。"""
    x0, y0, w, h = 200 + dx, 290, 480, 430
    block(30 + dx, 60, 830 + dx, 910, title, note)
    pins = [(n, nm, 'L', 20 + 20 * i) for i, (n, nm) in enumerate(INPUTS)] + [('17', 'TESTP', 'L', 350), ('18', 'TESTN', 'L', 370)]
    pins += [(n, nm, 'R', 60 + 20 * i) for i, (n, nm) in enumerate(SIGNALS)] + [(n, nm, 'R', 285 + 13 * i) for i, (n, nm) in enumerate(GNDS)]
    pins += [(n, '', 'T', 50 + 20 * i) for i, n in enumerate(DVDD)] + [(n, '', 'T', 110 + 20 * i) for i, n in enumerate(AVDD)]
    pins += [('61', 'RLDINV', 'T', 250), ('63', 'RLDOUT', 'T', 330), ('64', 'WCT', 'T', 460)]
    pins += [(n, '', 'B', 12 + 12 * i) for i, n in enumerate(AVSS)] + [('27', '', 'B', 100), ('29', '', 'B', 115)]
    pins += [('24', 'VREFP', 'B', 130), ('26', 'VCAP4', 'B', 262), ('28', 'VCAP1', 'B', 328), ('30', 'VCAP2', 'B', 394), ('55', 'VCAP3', 'B', 460)]
    ic(u, x0, y0, w, h, pins)
    text('DVDD', x0 + 60, y0 + 30, size=10, color=SYM, anchor='middle')
    text('AVDD ×6', x0 + 160, y0 + 30, size=10, color=SYM, anchor='middle')
    text('AVSS ×7（含 VREFN）', x0 + 60, y0 + h - 22, size=10, color=SYM, anchor='middle')
    # 输入、测试脚、数字口：贴脚标签
    for n, _ in INPUTS + [('17', ''), ('18', '')]: lab(EXPECT[(u, n)], *Pn(u, n), 'left')
    for n, _ in SIGNALS[:-1]: lab(EXPECT[(u, n)], *Pn(u, n), 'right')
    # 数字地一排用竖线并到一个地符号
    # D16 分地：RLDREF、RLDIN 接 AGND，其余接 GND（RESV1、DAISY_IN、未用 GPIO 都要逻辑低）
    px, py = Pn(u, '51'); wire(Pn(u, GNDS[0][0]), Pn(u, '51'), (px + 30, py)); dgnd(px + 30, py, 'right')
    wire(Pn(u, '60'), Pn(u, '62')); gnd(*Pn(u, '62'))
    nc(*Pn(u, '27')); nc(*Pn(u, '29'))
    # DVDD → 3V3 去耦（1µF + 100nF）
    wire(Pn(u, DVDD[0]), Pn(u, DVDD[1])); wire(Pn(u, DVDD[0]), (x0 + 50, 150), (60 + dx, 150))
    cap(c['d3a'], 60 + dx, 190, 'vr'); cap(c['d3b'], 122 + dx, 190, 'vr'); dgnd(*Pn(c['d3a'], '1'), 'right'); dgnd(*Pn(c['d3b'], '1'), 'right')
    pwr('3V3', 180 + dx, 150)
    # AVDD → +2.5V 去耦
    wire(Pn(u, AVDD[0]), Pn(u, AVDD[-1])); wire(Pn(u, AVDD[0]), (x0 + 110, 150), (386 + dx, 150))
    cap(c['d25a'], 326 + dx, 190, 'vr'); cap(c['d25b'], 386 + dx, 190, 'vr'); gnd(*Pn(c['d25a'], '1')); gnd(*Pn(c['d25b'], '1'))
    pwr('V4_+2.5V', 356 + dx, 150)
    # RLD：RLDOUT 经 392k∥10nF 回 RLDINV，再经 392k 出偏置驱动
    res(c['rf'], 490 + dx, 220, 'h'); cap(c['cf'], 490 + dx, 160, 'h')
    wire(Pn(u, '61'), Pn(c['rf'], '1'), Pn(c['cf'], '1')); wire(Pn(u, '63'), Pn(c['rf'], '2'), Pn(c['cf'], '2'))
    res(c['rb'], 600 + dx, 160, 'h'); wire(Pn(c['cf'], '2'), Pn(c['rb'], '1')); lab(EXPECT[(c['rb'], '2')], *Pn(c['rb'], '2'), 'right')
    # WCT：100pF 到地，10k 引到电极座
    wire(Pn(u, '64'), (x0 + 460, 232), (690 + dx, 232))   # 上移 8，地符号不压 34 脚脚号
    cap(c['cw'], 690 + dx, 272, 'v'); gnd(*Pn(c['cw'], '2'))
    res(c['rw'], 730 + dx, 232, 'h'); lab(EXPECT[(c['rw'], '2')], *Pn(c['rw'], '2'), 'right')
    # 负电源母线：AVSS 直下，VREFP/VCAP 电容挂在母线上
    bus = 870
    for n in AVSS: wire(Pn(u, n), (Pn(u, n)[0], bus))
    capq(c['vr1'], x0 + 130, 830, 'vr'); capq(c['vr2'], x0 + 196, 830, 'v')
    wire(Pn(u, '24'), Pn(c['vr1'], '2')); wire((x0 + 130, 765), (x0 + 196, 765), Pn(c['vr2'], '1'))
    for n, k in (('26', 'vc4'), ('28', 'vc1'), ('30', 'vc2')):
        capq(c[k], Pn(u, n)[0], 830, 'vr'); wire(Pn(u, n), Pn(c[k], '2'))
    capq(c['vc3a'], x0 + 460, 830, 'vr'); capq(c['vc3b'], x0 + 526, 830, 'v')
    wire(Pn(u, '55'), Pn(c['vc3a'], '2')); wire((x0 + 460, 765), (x0 + 526, 765), Pn(c['vc3b'], '1'))
    # ±2.5V 跨接去耦挂在母线左端
    SIDE[c['dpm_a']] = 1  # 左边那颗标注放左侧，免得压到右侧母线
    cap(c['dpm_a'], 100 + dx, 830, 'vr'); cap(c['dpm_b'], 150 + dx, 830, 'vr')
    wire(Pn(c['dpm_a'], '2'), Pn(c['dpm_b'], '2')); pwr('V4_+2.5V', 125 + dx, Pn(c['dpm_a'], '2')[1])
    wire((64 + dx, bus), (x0 + 526, bus)); pwr('V4_-2.5V', 64 + dx, bus, up=False)
    text('VREFP / VCAP 电容都接 -2.5V', x0 + 200, 897, color='#555')

DX1 = 410
U1 = dict(d3a='V4_C31', d3b='V4_C32', d25a='V4_C33', d25b='V4_C34', dpm_a='V4_C35', dpm_b='V4_C36', rf='V4_R24', cf='V4_C47', rb='V4_R34',
          cw='V4_C123', rw='V4_R35', vr1='V4_C45', vr2='V4_C46', vc4='V4_C44', vc1='V4_C54', vc2='V4_C43', vc3a='V4_C48', vc3b='V4_C49')
ads(DX1, 'V4_U1', U1, 'A  ADS1298 采集核心（U1，正面单面贴）：电极 CH1–8 → SPI', '±2.5V 双电源；RLD 偏置经 392k∥10nF 反馈、392k 出 V4_BIAS_DRV1；WCT 100pF 滤波后引到电极座')
# CLKSEL 下拉
lab('ADS_CLKSEL', 740 + DX1, Pn('V4_U1', '52')[1], 'right'); wire(Pn('V4_U1', '52'), (740 + DX1, Pn('V4_U1', '52')[1]))
res('V4_R17', 720 + DX1, Pn('V4_U1', '52')[1] + 40, 'vr'); dgnd(*Pn('V4_R17', '1'), 'right')

# ---------------- B 时钟与测试点 ----------------
block(30, 925, 1650, 1080, 'B  AFE 时钟与测试点：2.048MHz 有源晶振 → AFE_CLK_IN', '晶振供 U1，AFE_CLK_IN 也引到 J_AFE（主控未用）；TP901/TP902 引出 TESTP/TESTN 测点；V4_R18 0R 是数字地 GND 和模拟地 AGND 的唯一连接；未标名地符号都是 AGND。')
ic('V4_X1', 260, 1000, 110, 50, [('4', 'VDD', 'L', 15), ('1', 'EN', 'L', 40), ('3', 'OUT', 'R', 15), ('2', 'GND', 'B', 55)])
wire(Pn('V4_X1', '4'), (200, 1015), (200, 1040), Pn('V4_X1', '1')); pwr('3V3', 200, 1015)
cap('V4_C37', 140, 1040, 'h'); wire(Pn('V4_C37', '2'), (200, 1040)); dgnd(*Pn('V4_C37', '1')); dgnd(*Pn('V4_X1', '2'))
lab('AFE_CLK_IN', *Pn('V4_X1', '3'), 'right')
for i, r in enumerate(['TP902', 'TP901']):
    x, y = 760, 1005 + 40 * i
    tp(r, x, y); lab(EXPECT[(r, '1')], *Pn(r, '1'), 'left')
res('V4_R18', 1300, 1010, 'h'); dgnd(*Pn('V4_R18', '1')); gnd(*Pn('V4_R18', '2'), label='AGND', side='right')

finish(1, '单 ADS1298 采集', PAGE_REFS, 'C08B 单面 8 通道采集板：8 路电极 → 正面 ADS1298（U1）→ SPI 经 J_AFE',
       '正面单面贴 8 路（背面无器件，整面阻焊铜皮贴锂电池）；输入来自第 2 页保护，±2.5V 来自第 3 页，SPI/DRDY/CS 经 J_AFE 去主控板。')
