"""C08B 采集板 第 4 页：J_AFE 板对板接口。FH34SRJ-20S 把采集板的 SPI/控制/时钟（接 P1 两颗 ADS）、
3V3（来自主控板）、GND 引到主控板。座子是 derive 加的、不在 C08A 真源，本页把它的脚→网补进 EXPECT 再逐脚比对。"""
import json
from sch import *

JAFE = {'1': 'GND', '2': '', '3': 'ADS_DRDY_B', '4': 'ADS_CS_B', '5': 'DIN_B', '6': 'ADS_PWDN',
        '7': 'ADS_RESET', '8': 'AFE_CLK_IN', '9': 'ADS_START', '10': 'ADS_CS_A', '11': 'SCLK_B',
        '12': 'GND', '13': '', '14': 'GND', '15': 'DOUT_B', '16': 'AFE_GPIO3', '17': 'ADS_DRDY_A',
        '18': 'ADS_CLKSEL', '19': '3V3', '20': '3V3', '21': 'GND', '22': 'GND'}
EXPECT.update({('J_AFE', p): n for p, n in JAFE.items()})
VAL['J_AFE'] = 'FH34SRJ-20S-0.5SH'
PULLS = [('R801', 'ADS_CS_A', 1), ('R802', 'ADS_CS_B', 1), ('R803', 'ADS_RESET', 0), ('R804', 'ADS_PWDN', 0),
         ('R805', 'ADS_START', 0), ('R806', 'SCLK_B', 0), ('R807', 'DIN_B', 0), ('R808', 'AFE_GPIO3', 0)]
PAGE_REFS = ['J_AFE'] + [r for r, _, _ in PULLS]

block(30, 60, 1100, 1080, 'A  J_AFE 板对板接口：FH34SRJ-20S（0.5 mm 20 芯）→ 主控板',
      'SPI/控制/时钟接 P1 两颗 ADS；19/20 脚 3V3 由主控板供入（去 P3）；1/12/14/21/22 脚 GND；2/13 脚空。对插主控板同位 J_AFE，含义逐脚对上。')

x0, y0, w, h = 760, 200, 160, 640
left = [str(i) for i in range(1, 12)]        # 1–11 左
right = [str(i) for i in range(12, 23)]      # 12–22 右
pins = [(n, JAFE[n] or 'NC', 'L', 20 + 40 * i) for i, n in enumerate(left)]
pins += [(n, JAFE[n] or 'NC', 'R', 20 + 40 * i) for i, n in enumerate(right)]
ic('J_AFE', x0, y0, w, h, pins, name='FH34SRJ-20S')

for num, net in JAFE.items():
    x, y = Pn('J_AFE', num)
    d = 'left' if num in left else 'right'
    if net == '':
        nc(x, y)
    elif net == 'GND':
        dgnd(x, y, d)   # 标名放外侧，不压座子方框
    elif net == '3V3':
        lab('3V3', x, y, d)   # 脚距小，电源旗会压到上一行，用和信号一样的端口
    else:
        lab(net, x, y, d)

# B 框：主控板没插或上电前，片选默认拉高（不选中 ADS），其余控制/时钟/数据线默认拉低。原 C08A 第 5 页 R801–R808，C08B 去主控页时漏画（复核 P1）
block(1130, 60, 1650, 1080, 'B  J_AFE 信号上下拉：R801–R808',
      '主控板未接时：CS 拉高（不选中），RESET/PWDN/START/SCLK/DIN/GPIO3 拉低；10 kΩ。')
for i, (r, net, up) in enumerate(PULLS):
    y = 170 + 105 * i
    lab(net, 1250, y, 'left'); wire((1250, y), (1360, y))
    res(r, 1400, y, 'h'); wire(Pn(r, '2'), (1480, y))
    pwr('3V3', 1480, y) if up else dgnd(1480, y)

finish(4, 'J_AFE 接口', PAGE_REFS, 'C08B 采集板 J_AFE：20 芯板对板座，SPI/控制/时钟接 ADS、3V3 自主控板、多脚 GND',
       '信号脚旗标接 P1 的两颗 ADS（同名网）；3V3 来自主控板经本座供入 P3；对插主控板 J_AFE 同位含义一致。')
