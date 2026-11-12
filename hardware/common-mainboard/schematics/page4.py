"""C08B 主控板第 4 页：AFE 板间座 J800（C08A 没有，按 BA 板网表新画）。
缓冲 U2 的 B 侧经 33Ω 串阻成 AFE_* 网，座子侧上/下拉定默认电平；3V3 经 0.47Ω 成 3V3_AFE 给采集板。"""
import json
from sch import *

PAGE_REFS = json.loads((SRC / 'page-map.json').read_text())[3]['refs']

# ---------------- A 缓冲输出串阻 ----------------
block(30, 60, 820, 560, 'A  缓冲输出串阻：33Ω × 6，U2 B 侧 → AFE_*', '串阻压过冲；左侧网来自第 3 页 U2，右侧网到 C 框 J_AFE')
for i, r in enumerate(['R810', 'R813', 'R811', 'R812', 'R814', 'R815']):
    y = 150 + 66 * i
    res(r, 400, y, 'h')
    a, b = Pn(r, '1'), Pn(r, '2')
    wire((220, y), a); lab(EXPECT[(r, '1')], 220, y, 'left')
    wire(b, (580, y)); lab(EXPECT[(r, '2')], 580, y, 'right')

# ---------------- B 默认电平 ----------------
block(30, 580, 820, 1080, 'B  板间信号默认电平：上拉 47k × 2、下拉 47k × 5、DOUT_B 下拉 100k', '两片选默认高（不选中）；复位、掉电、START、SCLK、DIN 默认低；上拉接 3V3_AFE')
for i, r in enumerate(['R820', 'R821', 'R822', 'R823', 'R824', 'R825', 'R826', 'R827']):
    y = 665 + 56 * i
    res(r, 400, y, 'h')
    wire((220, y), Pn(r, '1')); lab(EXPECT[(r, '1')], 220, y, 'left')
    x2, _ = Pn(r, '2')
    if EXPECT[(r, '2')] == 'GND':
        wire(Pn(r, '2'), (x2 + 40, y)); gnd(x2 + 40, y)
    else:
        wire(Pn(r, '2'), (x2 + 40, y)); pwr(EXPECT[(r, '2')], x2 + 40, y)

# ---------------- C 板间座 J_AFE ----------------
block(840, 60, 1650, 1080, 'C  AFE 板间座 J_AFE：FH34SRJ-20S 0.5 mm，FPC 到采集板', '1、2 脚 3V3_AFE；21、22 为固定脚接地；3、8、13、19 脚本板不用（CLKSEL/CLK 由采集板本地处理）')
X0, Y0 = 1330, 160
order = [str(i) for i in range(1, 21)]
pins = [(n, '', 'L', 22 + 34 * i) for i, n in enumerate(order)] + [('21', '', 'B', 40), ('22', '', 'B', 100)]
ic('J_AFE', X0, Y0, 140, 22 + 34 * 19 + 40, pins, name=' ')
svg.pop(); TEXTS.pop()
text('FH34SRJ-20S', X0 + 70, Y0 + 360, size=11, color='#333', anchor='middle', weight='bold')
for n in order:
    x, y = Pn('J_AFE', n); net = EXPECT[('J_AFE', n)]
    text(n, x + 26, y + 4, size=10, color='#555')
    if net == 'GND':
        wire((x, y), (x - 40, y)); gnd(x - 40, y)
    elif not net:
        nc(x, y)   # 本板不用：CLKSEL/CLK 采集板本地处理，DAISY_IN/CS4 两边都空
    elif net == '3V3_AFE':
        continue
    else:
        wire((x, y), (1150, y)); lab(net, 1150, y, 'left')
# 1、2 脚并联接 3V3_AFE
x1, y1 = Pn('J_AFE', '1'); x2, y2 = Pn('J_AFE', '2')
wire((x1, y1), (x1 - 40, y1), (x1 - 40, y2), (x2, y2)); wire((x1 - 40, y1), (x1 - 40, y1 - 30)); pwr('3V3_AFE', x1 - 40, y1 - 30)
for n in ('21', '22'):
    gnd(*Pn('J_AFE', n))

# 3V3_AFE 供电：3V3 → R801 0.47Ω → 3V3_AFE，就近两颗去耦
res('R801', 940, 975, 'h'); pwr('3V3', *Pn('R801', '1'))
wire(Pn('R801', '2'), (1220, 975)); pwr('3V3_AFE', 1220, 975)
cap('C801', 1030, 1015); cap('C802', 1140, 1015)
wire((1030, 975), Pn('C801', '1')); wire((1140, 975), Pn('C802', '1'))
gnd(*Pn('C801', '2')); gnd(*Pn('C802', '2'))

finish(4, 'AFE 板间接口', PAGE_REFS, 'C08B 主控板 AFE 板间座：U2 缓冲 → 33Ω 串阻 → J_AFE → FPC → 采集板',
       '框 A 串阻、框 B 默认电平、框 C 座子与 3V3_AFE 供电；与第 2、3 页只用旗形标签相连。')
