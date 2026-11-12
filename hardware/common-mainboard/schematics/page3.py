"""C08A 第 5 页：USB、AFE 数字接口与调试。XIAO_* 是旧网名，按网表原样保留。"""
import json
from sch import *

PAGE_REFS = json.loads((SRC / 'page-map.json').read_text())[2]['refs']


def labd(net, x, y):
    """向下的旗形标签（sch.lab 没有 down）。"""
    own('#'); PORTS.append((x, y, net, 'down'))
    NAMED.append((x, y, net)); LABS.append((x, y))
    w = sum(11 if ord(c) > 0x2e80 else 6.6 for c in net) + 14
    pts = [(x, y), (x + w / 2, y + 6), (x + w / 2, y + 22), (x - w / 2, y + 22), (x - w / 2, y + 6)]
    svg.append('<polygon points="' + ' '.join(f'{a},{b}' for a, b in pts) + f'" fill="#eef3ff" stroke="{TXT}" stroke-width="1"/>')
    text(net, x, y + 18, size=11, anchor='middle'); own(None)


def tp(ref, x, y, d):
    """测试点：脚在 (x,y)，沿 d 方向伸出圆焊盘。"""
    pin(ref, '1', x, y)
    dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[d]
    cx, cy = x + dx * 17, y + dy * 17
    line([(x, y), (x + dx * 12, y + dy * 12)])
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    if d == 'left': text(ref, cx - 9, cy + 4, anchor='end')
    elif d == 'up': text(ref, cx + 9, cy + 2)
    else: text(ref, cx + 9, cy + 4)


# ---------------- A USB-C 输入与保护 ----------------
block(30, 60, 600, 560, 'A  USB-C 输入与保护：USBLC6', 'CC 5.1k 下拉声明受电端；USBLC6 压 ESD；33Ω 串阻到主控 USB；R27 为 VBUS 泄放')
ic('J400', 200, 210, 90, 240, [('A4B9', 'VBUS', 'R', 20), ('B4A9', 'VBUS', 'R', 40), ('A6', 'D+', 'R', 70), ('B6', 'D+', 'R', 90),
                              ('A7', 'D-', 'R', 130), ('B7', 'D-', 'R', 150), ('A5', 'CC1', 'L', 70), ('B5', 'CC2', 'L', 130),
                              ('A8', 'SBU1', 'L', 200), ('B8', 'SBU2', 'L', 220),
                              ('A1B12', 'GND', 'B', 10), ('B1A12', 'GND', 'B', 45), ('S', '壳', 'B', 80)], name=' ')
svg.pop(); TEXTS.pop()  # 去掉占位型号；底边有脚，型号写进框内
text('TYPE-C 16P', 245, 395, size=10, color='#333', anchor='middle', weight='bold')
# VBUS：两脚并联，上走 VBUS 干线挂电容和泄放电阻
wire(Pn('J400', 'B4A9'), (330, 250), (330, 150), (540, 150)); wire(Pn('J400', 'A4B9'), (330, 230)); pwr('VBUS', 540, 150)
cap('C42', 380, 190); cap('C54', 430, 190); res('R27', 480, 190, 'v')
gnd(*Pn('C42', '2')); gnd(*Pn('C54', '2')); gnd(*Pn('R27', '2'))
# D+ / D-：两面脚并联 → ESD 抽头 → 33Ω → 主控
res('R204', 490, 280, 'h'); res('R205', 490, 340, 'h')
wire(Pn('J400', 'A6'), Pn('R204', '1')); wire(Pn('J400', 'B6'), (340, 300), (340, 280))
wire(Pn('J400', 'A7'), Pn('R205', '1')); wire(Pn('J400', 'B7'), (350, 360), (350, 340))
lab('MCU_DP', *Pn('R204', '2'), 'right'); lab('MCU_DM', *Pn('R205', '2'), 'right')
ic('U17', 360, 400, 90, 80, [('1', 'IO1', 'T', 15), ('6', 'IO1', 'T', 35), ('3', 'IO2', 'T', 55), ('4', 'IO2', 'T', 75),
                             ('5', 'VBUS', 'R', 20), ('2', 'GND', 'B', 45)], name_dy=52, ref_at=(330, 470))
wire(Pn('U17', '1'), (375, 280)); wire(Pn('U17', '6'), (395, 365), (375, 365))
wire(Pn('U17', '3'), (415, 340)); wire(Pn('U17', '4'), (435, 365), (415, 365))
wire(Pn('U17', '5'), (500, 420)); pwr('VBUS', 500, 420); gnd(*Pn('U17', '2'))
# CC 下拉
res('R206', 100, 320, 'v'); res('R207', 150, 380, 'v')
wire(Pn('J400', 'A5'), Pn('R206', '1')); wire(Pn('J400', 'B5'), Pn('R207', '1'))
gnd(*Pn('R206', '2')); gnd(*Pn('R207', '2'))
nc(*Pn('J400', 'A8')); nc(*Pn('J400', 'B8'))
wire(Pn('J400', 'A1B12'), (210, 490), (280, 490), Pn('J400', 'S')); wire(Pn('J400', 'B1A12'), (245, 490)); gnd(245, 490)

# ---------------- C 调试接口与测试点 ----------------
block(30, 580, 600, 1080, 'C  调试接口与测试点：SWD + UART 焊盘', '烧录/调试走 SWD；TX 出串口日志；RST 接主控复位')
ic('J301', 150, 690, 70, 130, [('2', '3V3', 'L', 30), ('1', 'GND', 'L', 100), ('3', 'SWDIO', 'R', 20), ('4', 'SWDCLK', 'R', 50),
                              ('5', 'TX', 'R', 80), ('6', 'RST', 'R', 110)], name='调试焊盘')
wire(Pn('J301', '2'), (90, 720)); pwr('3V3', 90, 720); gnd(*Pn('J301', '1'))
for num, net in [('3', 'MCU_SWDIO'), ('4', 'MCU_SWDCLK'), ('5', 'MCU_TX'), ('6', 'MCU_RST_N')]:
    x, y = Pn('J301', num); wire((x, y), (300, y)); lab(net, 300, y, 'right')
tp('TP703', 480, 900, 'right'); wire((400, 900), Pn('TP703', '1')); lab(EXPECT[('TP703', '1')], 400, 900, 'left')
tp('TP705', 480, 960, 'up'); wire(Pn('TP705', '1'), (480, 990)); gnd(480, 990)
text('TP703 测第二颗 ADS 的 DRDY（AFE_DRDY_B）', 60, 1040, color='#555')

# ---------------- B 主控 → ADS 控制与 SPI 缓冲 ----------------
block(620, 60, 1240, 1080, 'B  AFE 控制与 SPI 缓冲：SN74AXC8T245，主控 → J_AFE', '两侧都接 3V3，当可关断缓冲用：DIR1 接 3V3 → A 到 B；OE_N 高时隔离 ADS')
ic('U2', 870, 180, 130, 640, [('1', 'VCCA', 'T', 15), ('2', 'DIR1', 'T', 45), ('23', 'VCCB', 'T', 85), ('24', 'VCCB', 'T', 115),
                             ('22', 'OE', 'B', 15), ('11', 'DIR2', 'B', 45), ('12', 'GND', 'B', 70), ('13', 'GND', 'B', 95), ('25', 'EP', 'B', 115)]
   + [(n, nm, 'L', 40 + 80 * i) for i, (n, nm) in enumerate([('3', 'A1'), ('6', 'A4'), ('7', 'A5'), ('8', 'A6'), ('4', 'A2'), ('5', 'A3'), ('9', 'A7'), ('10', 'A8')])]
   + [(n, nm, 'R', 40 + 80 * i) for i, (n, nm) in enumerate([('21', 'B1'), ('18', 'B4'), ('17', 'B5'), ('16', 'B6'), ('20', 'B2'), ('19', 'B3'), ('15', 'B7'), ('14', 'B8')])],
   name_dy=330)
wire(Pn('U2', '1'), (885, 140), (985, 140), Pn('U2', '24')); wire(Pn('U2', '2'), (915, 140)); wire(Pn('U2', '23'), (955, 140)); pwr('3V3', 935, 140)


def pull(r, x, y, up):
    """信号线 (x,y) 处分支出上/下拉电阻：1 脚接信号，2 脚接 3V3 或地。"""
    yy = y - 30 if up else y + 30
    res(r, x + 40, yy, 'h'); wire((x, y), (x, yy))
    (lambda p: pwr('3V3', *p))(Pn(r, '2')) if up else gnd(*Pn(r, '2'))


# A 侧：主控来的信号，旗形标签在左；上拉排在前两行，避免上下拉电阻挤在同一高度
def term(n, x_end, side):
    """U2 一只信号脚：网名取 BA 板；空网打叉，GND 直接接地，其余拉到 x_end 放旗形标签。"""
    x, y = Pn('U2', n); net = EXPECT[('U2', n)]
    if not net: nc(x, y); return x, y, net
    if net == 'GND': gnd(x - 20 if side == 'left' else x + 20, y); wire((x, y), (x - 20 if side == 'left' else x + 20, y)); return x, y, net
    wire((x_end, y), (x, y)) if side == 'left' else wire((x, y), (x_end, y)); lab(net, x_end, y, side); return x, y, net


for n, r, up in [('3', 'R34', 1), ('6', 'R42', 1), ('7', None, 0), ('8', None, 0), ('4', 'R35', 0), ('5', 'R36', 0), ('9', 'R37', 0), ('10', 'R39', 0)]:
    x, y, net = term(n, 720, 'left')
    if r: pull(r, 745, y, up)
# B 侧：到两颗 ADS 的信号，旗形标签在右
for n in ('21', '18', '17', '16', '20', '19', '15', '14'):  # B 侧：本板不上下拉，经第 4 页 33Ω 串阻到 J800
    term(n, 1150, 'right')
wire(Pn('U2', '11'), (915, 860), (985, 860)); wire(Pn('U2', '12'), (940, 860)); wire(Pn('U2', '13'), (965, 860)); wire(Pn('U2', '25'), (985, 860)); gnd(950, 860)
wire(Pn('U2', '22'), (885, 880), (820, 880)); lab('OE_N', 820, 880, 'left')
cap('C39', 1060, 940); cap('C40', 1120, 940); wire(Pn('C39', '1'), Pn('C40', '1')); pwr('3V3', 1090, 900)
gnd(*Pn('C39', '2')); gnd(*Pn('C40', '2'))
text('U2 电源去耦', 1050, 1030, color='#555')

# ---------------- D 回读缓冲与 OE 门 ----------------
block(1260, 60, 1650, 1080, 'D  回读缓冲与 OE 门：U3 / U10', 'U7_EN 经 U10 反相出 OE_N；U3 把 DRDY/DOUT 送回主控')
ic('U10', 1400, 170, 140, 60, [('2', 'A', 'L', 20), ('1', 'NC', 'L', 45), ('4', 'Y', 'R', 20), ('5', 'VCC', 'T', 40), ('3', 'GND', 'B', 40)], name_dy=36)
wire((1340, 190), Pn('U10', '2')); lab(EXPECT[('U10', '2')], 1340, 190, 'left'); nc(*Pn('U10', '1'))
pwr('3V3', *Pn('U10', '5')); gnd(*Pn('U10', '3'))
wire(Pn('U10', '4'), (1590, 190)); lab('OE_N', 1590, 190, 'right')
ic('U3', 1380, 480, 160, 120, [('4', 'B1', 'T', 40), ('5', 'B2', 'T', 120), ('9', 'A1', 'B', 40), ('8', 'A2', 'B', 120),
                             ('7', 'VCCA', 'L', 20), ('6', 'VCCB', 'L', 45), ('2', 'OE', 'L', 70),
                             ('1', 'DIR1', 'R', 20), ('3', 'GND', 'R', 45), ('10', 'DIR2', 'R', 70)], name_dy=98)
wire((1575, 190), (1575, 300), (1320, 300), (1320, 550), Pn('U3', '2'))
wire(Pn('U3', '7'), (1340, 500), (1340, 525), Pn('U3', '6')); pwr('3V3', 1340, 500)
wire(Pn('U3', '1'), (1580, 500), (1580, 550), Pn('U3', '10')); wire(Pn('U3', '3'), (1580, 525)); gnd(1580, 550)
wire(Pn('U3', '4'), (1420, 420)); lab('ADS_DRDY_A', 1420, 420, 'up'); tp('TP701', 1420, 435, 'left')
wire(Pn('U3', '5'), (1500, 420)); lab('DOUT_B', 1500, 420, 'up')
wire(Pn('U3', '9'), (1420, 720)); labd('XIAO_DRDY', 1420, 720)
wire(Pn('U3', '8'), (1500, 720)); labd('XIAO_MISO', 1500, 720)
res('R701', 1380, 640, 'hr'); gnd(*Pn('R701', '2'))
res('R702', 1540, 640, 'h'); gnd(*Pn('R702', '2'))
tp('TP702', 1420, 685, 'left'); tp('TP704', 1500, 685, 'right')
own(None); text('DIR 接地 → B 到 A（ADS → 主控）', 1290, 800, color='#555')
cap('C27', 1500, 990); cap('C29', 1560, 990); wire(Pn('C27', '1'), Pn('C29', '1')); pwr('3V3', 1530, 950)
gnd(*Pn('C27', '2')); gnd(*Pn('C29', '2'))
text('U3/U10 去耦', 1480, 1066, color='#555')

finish(3, 'USB 与板间接口', PAGE_REFS, 'C08B 主控板 USB、AFE 板间接口与调试：USB-C → 主控；主控 SPI/控制 → 缓冲 → J_AFE → 采集板',
       '框 A 是 USB 入口，B/D 是主控与 ADS 之间的缓冲（OE_N 统一关断），C 是调试焊盘；框间只用旗形标签连接。')
