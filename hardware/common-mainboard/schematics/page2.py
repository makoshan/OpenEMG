"""L432 + 52840 第 2 页：蓝牙 nRF52840（QFN48）、时钟、射频、IMU、复位/按键/指示灯。L432 在第 5 页。
去耦、DCDC 电感、晶振负载电容、射频匹配都用实线贴着 U13 对应脚画；GPIO 用贴脚标签（R10）。
网名 XIAO_* 是旧方案名，本轮照网表原样保留。"""
import json
from sch import *

PAGE_REFS = json.loads((SRC / 'page-map.json').read_text())[1]['refs']


def rtext(t, x, y, size, color, anchor):
    """竖排文字（逆时针 90°）。anchor=end 时字从 (x,y) 向下排，start 时向上排。"""
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" transform="rotate(-90 {x} {y})">{t}</text>')
    w = len(t) * size * 0.6
    y0, y1 = (y, y + w) if anchor == 'end' else (y - w, y)
    TEXTS.append((x - size * 0.8, y0, x + size * 0.2, y1, t))


def bigic(ref, x0, y0, w, h, pins, name_dy):
    """大芯片：左右脚名横排，上下脚名和球号竖排，避免 18 px 间距下互压。"""
    own(ref)
    svg.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#fffdf4" stroke="{SYM}" stroke-width="1.4"/>')
    for num, nm, side, off in pins:
        if side == 'L': a, b = (x0 - 20, y0 + off), (x0, y0 + off)
        if side == 'R': a, b = (x0 + w + 20, y0 + off), (x0 + w, y0 + off)
        if side == 'T': a, b = (x0 + off, y0 - 20), (x0 + off, y0)
        if side == 'B': a, b = (x0 + off, y0 + h + 20), (x0 + off, y0 + h)
        pin(ref, num, *a); line([a, b])
        if side == 'L':
            text(nm, x0 + 5, y0 + off + 4, size=10, color=SYM); text(num, x0 - 10, y0 + off - 3, size=8, color='#777', anchor='middle')
        elif side == 'R':
            text(nm, x0 + w - 5, y0 + off + 4, size=10, color=SYM, anchor='end'); text(num, x0 + w + 10, y0 + off - 3, size=8, color='#777', anchor='middle')
        elif side == 'T':
            rtext(nm, a[0] + 4, y0 + 5, 10, SYM, 'end'); rtext(num, a[0] - 2, y0 - 2, 8, '#777', 'start')
        else:
            rtext(nm, a[0] + 4, y0 + h - 5, 10, SYM, 'start'); rtext(num, a[0] - 2, y0 + h + 2, 8, '#777', 'end')
    text(ref, x0, y0 - 54, weight='bold')
    text(val(ref), x0 + w / 2, y0 + name_dy, size=12, color='#333', anchor='middle', weight='bold')


def ind(ref, x, y, o='h'):
    def body(x, y, v):
        line([(x - 40, y), (x - 20, y)]); line([(x + 20, y), (x + 40, y)])
        svg.append(f'<path d="M{x-20},{y} a5,5 0 0 1 10,0 a5,5 0 0 1 10,0 a5,5 0 0 1 10,0 a5,5 0 0 1 10,0" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    two_pin(ref, x, y, o, body)


def xtal_body(x, y):
    line([(x - 40, y), (x - 12, y)]); line([(x + 12, y), (x + 40, y)])
    line([(x - 12, y - 10), (x - 12, y + 10)], w=2); line([(x + 12, y - 10), (x + 12, y + 10)], w=2)
    svg.append(f'<rect x="{x-7}" y="{y-12}" width="14" height="24" fill="none" stroke="{SYM}" stroke-width="1.4"/>')


def xtal2(ref, x, y):
    two_pin(ref, x, y, 'h', lambda x, y, v: xtal_body(x, y))


def xtal4(ref, x, y):
    """四脚晶振：1、3 为振荡脚，2、4 为外壳地，在下方合一接地；位号料值写在上方。"""
    pin(ref, '1', x - 40, y); pin(ref, '3', x + 40, y); pin(ref, '2', x - 8, y + 24); pin(ref, '4', x + 8, y + 24)
    xtal_body(x, y)
    line([(x - 8, y + 12), (x - 8, y + 24)]); line([(x + 8, y + 12), (x + 8, y + 24)])
    text(VAL[ref], x, y - 16, anchor='middle'); text(ref, x, y - 30, anchor='middle')


def coax(ref, x, y):
    """U.FL 座：1 芯线在左，2 外壳在下。"""
    pin(ref, '1', x - 20, y); pin(ref, '2', x, y + 20)
    svg.append(f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{SYM}" stroke-width="1.4"/><circle cx="{x}" cy="{y}" r="3" fill="{SYM}"/>')
    line([(x - 20, y), (x - 3, y)]); line([(x, y + 11), (x, y + 20)])
    text(ref, x, y - 32, anchor='middle'); text(VAL[ref], x, y - 18, anchor='middle')


def switch(ref, x, y):
    """轻触按键，竖放：1 在上、2 在下。"""
    pin(ref, '1', x, y - 30); pin(ref, '2', x, y + 30)
    line([(x, y - 30), (x, y - 12)]); line([(x, y + 12), (x, y + 30)])
    svg.append(f'<circle cx="{x}" cy="{y-12}" r="2.5" fill="none" stroke="{SYM}"/><circle cx="{x}" cy="{y+12}" r="2.5" fill="none" stroke="{SYM}"/>')
    line([(x - 2, y + 10), (x - 12, y - 12)]); line([(x - 18, y - 2), (x - 10, y - 2)])
    text(ref, x + 12, y - 3); text(VAL[ref], x + 12, y + 11)


# ---------------- A nRF52840 蓝牙 ----------------
block(30, 60, 1200, 1080, 'A  蓝牙：nRF52840（QFN48），SPI 从机接 L432，兼管电源、按键和电量',
      '去耦、DCDC、晶振、射频匹配贴脚实线；GPIO 贴脚标签分三组；LINK_* 接第 5 页 L432')
X0, Y0, WU, HU = 560, 180, 480, 710
# 脚号 → 端口名（官方 QFN48 脚表）。29、30、38–44 是低频脚（信号不超过 10 kHz），这版一个都不用
PORT = {'2': 'P0.00', '3': 'P0.01', '4': 'P0.04/AIN2', '5': 'P0.05/AIN3', '6': 'P0.07', '7': 'P0.08', '8': 'P1.08', '9': 'P1.09', '10': 'P0.11', '11': 'P0.12',
        '13': 'P0.13', '14': 'P0.14', '15': 'P0.17', '16': 'P0.18/RESET', '18': 'P0.19', '19': 'P0.20', '20': 'P0.21', '21': 'P0.22', '22': 'P0.23', '23': 'P0.24', '24': 'P1.00',
        '26': 'SWDIO', '27': 'SWDCLK', '28': 'NC', '29': 'P0.09/NFC1', '30': 'P0.10/NFC2', '38': 'P1.15', '39': 'P0.03/AIN1', '40': 'P0.02/AIN0',
        '41': 'P0.28/AIN4', '42': 'P0.29/AIN5', '43': 'P0.30/AIN6', '44': 'P0.31/AIN7'}
def _grp(n):
    if n.startswith('LINK_') or n in ('L_BOOT0_CTL', 'L_NRST'): return 0
    if n in ('PWR_HOLD', 'CHRG_N', 'VBAT_SENSE', 'VBUS_SENSE', 'BUTTON_N', 'MCU_LED', 'MCU_BENCH_EN', 'OE_N'): return 1
    return 2
_used = sorted(((_grp(EXPECT[('U13', b)]), EXPECT[('U13', b)], b) for b in PORT if EXPECT.get(('U13', b))))
gpio, GRP_ROW = [], {}
for g in range(3):
    rows = [(b, PORT[b], n) for gg, n, b in _used if gg == g]
    if not rows: continue
    if gpio: gpio.append(None)
    GRP_ROW[g] = len(gpio); gpio += rows
top_nc = [(b, PORT[b]) for b in PORT if not EXPECT.get(('U13', b))]
vdd = [('12', 'VDD'), ('17', 'VDD'), ('25', 'VDD'), ('37', 'VDD'), ('48', 'VDD')]
left = [('47', 'DCC', 280), ('46', 'DEC4', 330), ('1', 'DEC1', 450), ('33', 'DEC6', 510), ('34', 'DEC3', 570)]
bottom = [('35', 'XC1', 190), ('36', 'XC2', 270),
          ('32', 'VSS_PA', 290), ('45', 'VSS', 310), ('49', 'VSS_PAD', 330), ('31', 'ANT', 360)]
pins = [(b, n, 'L', o) for b, n, o in left] + [(b, n, 'B', o) for b, n, o in bottom]
pins += [(b, n, 'T', 20 + 18 * i) for i, (b, n) in enumerate(vdd)] + [(b, n, 'T', 112 + 18 * i) for i, (b, n) in enumerate(top_nc)]
assert 112 + 18 * (len(top_nc) - 1) <= WU - 10, '顶排放不下空脚'
off = 20
for g in gpio:
    if g: pins.append((g[0], g[1], 'R', off))
    off += 26
bigic('U13', X0, Y0, WU, HU, pins, name_dy=HU / 2)
for g in gpio:
    if g: lab(g[2], *Pn('U13', g[0]), 'right')
for b, _ in top_nc: nc(*Pn('U13', b))
for g, t in enumerate(('到 L432', '电源/按键', '调试')):
    if g in GRP_ROW: text(t, X0 + WU + 130, Y0 + 20 + 26 * GRP_ROW[g] + 4, size=10, color='#555')

# 3V3 供电：5 个 VDD 脚并到上方母线，母线左侧挂去耦
for b, _ in vdd: wire(Pn('U13', b), (Pn('U13', b)[0], 145))
wire((70, 145), (Pn('U13', '48')[0], 145)); pwr('3V3', 70, 145)
for ref, x in zip(['C26', 'C28', 'C30', 'C44', 'C52', 'C53', 'C51', 'C61', 'C63', 'C64', 'C65'], range(100, 560, 42)):
    cap(ref, x, 185); gnd(*Pn(ref, '2'))

# DCDC 和 DEC 去耦（左侧）
for b, ref in [('1', 'C47'), ('34', 'C48')]:
    y = Pn('U13', b)[1]
    cap(ref, 460, y, 'hr'); wire(Pn('U13', b), Pn(ref, '1')); gnd(*Pn(ref, '2'))
ind('L3', 460, 460, 'hr'); ind('L5', 360, 460, 'hr')
wire(Pn('U13', '47'), Pn('L3', '1')); wire(Pn('L3', '2'), Pn('L5', '1'))
wire(Pn('L5', '2'), (300, 460), (300, 510))
cap('C45', 240, 510, 'hr')
wire(Pn('U13', '46'), (300, 510), Pn('C45', '1'))
gnd(*Pn('C45', '2'))
# DEC6（33）必须接 DEC4（46），C46 47 nF 挂在这条线上
wire(Pn('U13', '33'), (300, 690), (300, 510))
cap('C46', 240, 690, 'hr'); wire((300, 690), Pn('C46', '1')); gnd(*Pn('C46', '2'))
text('DCDC：DCC → L3 10µH → L5 15nH → DEC4', 60, 420, color='#555')
text('33 脚 DEC6 接 46 脚 DEC4（官方必连）', 60, 650, color='#555')

# 时钟（下方）：只留 32 MHz；32.768 kHz 官方标 Optional，本板不贴，用内部 RC
xtal4('Y3', 790, 930)
wire(Pn('U13', '35'), Pn('Y3', '1')); wire(Pn('U13', '36'), Pn('Y3', '3'))
wire(Pn('Y3', '2'), (782, 962), (798, 962), Pn('Y3', '4')); gnd(790, 962)
cap('C55', 750, 990); cap('C56', 830, 990)
wire(Pn('Y3', '1'), Pn('C55', '1')); wire(Pn('Y3', '3'), Pn('C56', '1')); gnd(*Pn('C55', '2')); gnd(*Pn('C56', '2'))
text('时钟：32 MHz（射频）；低频时钟用内部 RC，无 32.768 kHz 晶振', 60, 1060, color='#555')
# 地
wire(Pn('U13', '32'), (850, 920), (890, 920), Pn('U13', '49')); wire(Pn('U13', '45'), (870, 920)); gnd(870, 920)
# 射频：官方 QFAA 四件：C59 并、L4 串、C66 并、L6 串
wire(Pn('U13', '31'), (920, 940)); ind('L4', 960, 940, 'h')
wire((920, 940), Pn('L4', '1')); cap('C59', 920, 980); gnd(*Pn('C59', '2'))
ind('L6', 1060, 940, 'h')
wire(Pn('L4', '2'), (1010, 940), Pn('L6', '1')); cap('C66', 1010, 980); gnd(*Pn('C66', '2'))
coax('J300', 1130, 940)
wire(Pn('L6', '2'), Pn('J300', '1')); gnd(*Pn('J300', '2'))
text('射频匹配：官方四件 1.0pF/4.7nH/1.2pF/2.2nH（2m 内可改贴片天线免 J300）', 620, 1060, color='#555')

# ---------------- D IMU ----------------
block(1220, 60, 1650, 560, 'D  姿态：LSM6DS3TR-C，I²C → L432', 'CS 接 3V3 选 I²C；SA0 接地，地址 0x6A；SCL/SDA 4.7k 上拉')
ic('U16', 1400, 300, 120, 180, [('13', 'SCL', 'T', 30), ('14', 'SDA', 'T', 60),
                                ('8', 'VDD', 'L', 30), ('5', 'VDDIO', 'L', 55), ('12', 'CS', 'L', 80), ('1', 'SA0', 'L', 120), ('2', 'SDx', 'L', 140), ('3', 'SCx', 'L', 160),
                                ('4', 'INT1', 'R', 30), ('9', 'INT2', 'R', 70), ('10', 'NC', 'R', 95), ('11', 'NC', 'R', 120),
                                ('6', 'GND', 'B', 40), ('7', 'GND', 'B', 80)], name_dy=108)
SIDE['R198'] = 1; res('R198', 1430, 210, 'vr'); res('R199', 1460, 225, 'vr')
wire(Pn('U16', '13'), Pn('R198', '1'), (1300, 250)); lab('IMU_SCL', 1300, 250, 'left')
wire(Pn('U16', '14'), Pn('R199', '1'), (1560, 265)); lab('IMU_SDA', 1560, 265, 'right')
pwr('3V3', *Pn('R198', '2')); pwr('3V3', *Pn('R199', '2'))
wire((1350, 330), (1350, 380)); wire((1350, 330), Pn('U16', '8')); wire((1350, 355), Pn('U16', '5')); wire((1350, 380), Pn('U16', '12')); pwr('3V3', 1350, 330)
wire(Pn('U16', '1'), (1350, 420), (1350, 460)); wire(Pn('U16', '2'), (1350, 440)); wire(Pn('U16', '3'), (1350, 460)); gnd(1350, 460)
wire(Pn('U16', '4'), (1560, 330)); lab('IMU_INT1', 1560, 330, 'right')
for n in ('9', '10', '11'): nc(*Pn('U16', n))
wire(Pn('U16', '6'), (1440, 515), (1480, 515), Pn('U16', '7')); gnd(1460, 515)

# ---------------- E 复位 / 按键 / 指示灯 ----------------
block(1220, 580, 1650, 1080, 'E  复位、按键、指示灯', '复位 10k + 100nF；SW300 给第 3 页开机电路；BUTTON_N 读键；LED 低电平亮')
res('R203', 1300, 700, 'v'); pwr('3V3', *Pn('R203', '1'))
cap('C62', 1360, 780); wire(Pn('R203', '2'), Pn('C62', '1'), (1420, 740)); lab('MCU_RST_N', 1420, 740, 'right'); gnd(*Pn('C62', '2'))
res('R38', 1300, 900, 'vr'); pwr('3V3', *Pn('R38', '2'))
wire(Pn('R38', '1'), (1340, 940)); lab('BUTTON_N', 1340, 940, 'right')
switch('SW300', 1470, 910); lab('SW_N', *Pn('SW300', '1'), 'up'); gnd(*Pn('SW300', '2'))
res('R208', 1320, 1040, 'h'); pwr('3V3', *Pn('R208', '1'))
diode('D401', 1420, 1040, 'right', '2', '1', led=True)
wire(Pn('R208', '2'), Pn('D401', '2')); wire(Pn('D401', '1'), (1480, 1040)); lab('MCU_LED', 1480, 1040, 'right')

finish(2, '蓝牙', PAGE_REFS, 'C08B 主控板 L432 + 52840：nRF52840 + 时钟 + 射频 + IMU；采样主控 L432 见第 5 页',
       '主控电源/时钟/射频外围实线贴脚；GPIO 用贴脚标签分三组。')
