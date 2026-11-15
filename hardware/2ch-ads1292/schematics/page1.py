"""ADS1292 双通道四电极验证版：一页图。灰字件首版不贴。"""
from sch import *
import sch
sch.DNP8 = set(DNP)           # 不贴件走灰字
sch.val = lambda r: 'FH34 20P' if r == 'J2' else VAL[r] + (' 不贴' if r in DNP else '')

def pad(ref, y):
    ic(ref, 50, y - 18, 60, 36, [('1', '', 'R', 18)], name_dy=22)
    return Pn(ref, '1')

def leg(pad_ref, ra, d, rb, y, out):
    """电极 → 串阻 → ESD → 串阻 → 输出标签，手册未规定方向，1 脚朝电极。"""
    p = pad(pad_ref, y)
    res(ra, 200, y); wire(p, Pn(ra, '1'))
    tvs(d, 270, y + 60); gnd(*Pn(d, '2'))
    res(rb, 340, y); wire(Pn(ra, '2'), (270, y), Pn(rb, '1')); wire((270, y), Pn(d, '1'))
    wire(Pn(rb, '2'), (560, y)); lab(out, 560, y, 'right')

# ---------------- A 电极输入 ----------------
block(30, 60, 660, 1080, 'A  电极与保护：E1–E6 → IN1/IN2、RLD', '照 C08B 盒底两排大—辅—大；每腿 1M → ESD → 1M')
Y = [150, 300, 450, 590, 760, 910]
leg('E1', 'R1', 'D1', 'R2', Y[0], 'IN1P')
leg('E2', 'R3', 'D2', 'R4', Y[1], 'IN1N')
# RLD 从右往左驱动，电极在左：E3、E6 各经 620k 回到 D3 节点 ← R13 ← RLDOUT
p = pad('E3', Y[2]); res('R14', 200, Y[2], 'hr'); wire(p, Pn('R14', '2'))
tvs('D3', 270, Y[2] + 60); gnd(*Pn('D3', '2'))
res('R13', 400, Y[2], 'hr'); wire(Pn('R14', '1'), (270, Y[2]), Pn('R13', '2')); wire((270, Y[2]), Pn('D3', '1')); lab('NRLD', 320, Y[2], 'up')
wire(Pn('R13', '1'), (560, Y[2])); lab('RLDOUT', 560, Y[2], 'right')
p = pad('E6', Y[3]); res('R16', 200, Y[3], 'hr'); wire(p, Pn('R16', '2')); wire(Pn('R16', '1'), (330, Y[3])); lab('NRLD', 330, Y[3], 'right')
leg('E4', 'R5', 'D4', 'R6', Y[4], 'IN2P')
leg('E5', 'R7', 'D5', 'R8', Y[5], 'IN2N')
svg.append(f'<rect x="44" y="1024" width="602" height="48" fill="#f7f9fc" stroke="#b8c4d4" stroke-width="1"/>')
text('元件面(+y北,+x东右)：北排 E1(+)·E3(辅)·E2(-)', 52, 1043, size=9, color='#1d3f9a', weight='bold')
text('南排：E4(CH2+,-8,-7.5)·E6(辅)·E5(CH2-,+8,-7.5)', 340, 1043, size=9, color='#1d3f9a', weight='bold')
text('贴肤翻面(+y北,镜像)：1排左→右 E2(-)·E3·E1(+)', 52, 1063, size=9, color='#a8322d', weight='bold')
text('2排左→右：E5(CH2-)·E6(RLD)·E4(CH2+) [E4恒+]', 340, 1063, size=9, color='#a8322d', weight='bold')

# ---------------- B ADS1292 ----------------
block(680, 60, 1270, 1080, 'B  采集：ADS1292，电极信号 → SPI', '内部振荡器；START 默认低，用命令启动；RLD 参考用内部 AVDD/2')
y0 = 170
ic('U1', 860, y0, 260, 840, [
 ('4', 'IN1P', 'L', 30), ('3', 'IN1N', 'L', 110), ('2', 'PGA1P', 'L', 150), ('1', 'PGA1N', 'L', 230),
 ('6', 'IN2P', 'L', 350), ('5', 'IN2N', 'L', 430), ('8', 'PGA2P', 'L', 470), ('7', 'PGA2N', 'L', 550),
 ('30', 'RLDOUT', 'L', 610), ('28', 'RLDINV', 'L', 690), ('29', 'RLDIN/RLDREF', 'L', 730), ('31', 'IN3P', 'L', 770), ('32', 'IN3N', 'L', 810),
 ('18', 'CS', 'R', 40), ('19', 'DIN', 'R', 80), ('20', 'SCLK', 'R', 120), ('21', 'DOUT', 'R', 160), ('22', 'DRDY', 'R', 200),
 ('15', 'PWDN/RESET', 'R', 240), ('16', 'START', 'R', 280), ('14', 'CLKSEL', 'R', 320), ('17', 'CLK', 'R', 360),
 ('26', 'GPIO1', 'R', 400), ('25', 'GPIO2', 'R', 440), ('9', 'VREFP', 'R', 520), ('11', 'VCAP1', 'R', 640), ('27', 'VCAP2', 'R', 750),
 ('12', 'AVDD', 'T', 70), ('23', 'DVDD', 'T', 190), ('13', 'AVSS', 'B', 70), ('24', 'DGND', 'B', 130), ('10', 'VREFN', 'B', 190)], name_dy=430)
SIDE['R15'] = SIDE['C6'] = 1
yy = lambda o: y0 + o
lab('IN1P', 735, yy(30), 'left'); lab('IN1N', 735, yy(110), 'left')
wire(Pn('U1', '4'), (735, yy(30))); wire(Pn('U1', '3'), (735, yy(110)))
cap('C4', 800, yy(190)); wire(Pn('U1', '2'), Pn('C4', '1')); wire(Pn('U1', '1'), Pn('C4', '2'))
lab('IN2P', 735, yy(350), 'left'); lab('IN2N', 735, yy(430), 'left')
wire(Pn('U1', '6'), (735, yy(350))); wire(Pn('U1', '5'), (735, yy(430)))
cap('C5', 800, yy(510)); wire(Pn('U1', '8'), Pn('C5', '1')); wire(Pn('U1', '7'), Pn('C5', '2'))
cap('C3', 800, yy(650)); res('R15', 760, yy(650), 'v')
res('R27', 712, yy(680), 'v'); lab('RLDOUT', 712, yy(610), 'up')
wire(Pn('U1', '30'), Pn('C3', '1'), Pn('R15', '1'), (712, yy(610)), Pn('R27', '1')); wire(Pn('U1', '28'), Pn('C3', '2'), Pn('R15', '2'))
wire(Pn('R27', '2'), (712, yy(730)), Pn('U1', '29'))
wire(Pn('U1', '31'), (820, yy(770)), (820, yy(850))); wire(Pn('U1', '32'), (820, yy(810)))
pwr('AVDD', 820, yy(850), up=False)
for n, net in (('18', 'ADS_CS_N'), ('19', 'ADS_DIN'), ('20', 'ADS_SCLK'), ('21', 'ADS_DOUT'), ('22', 'ADS_DRDY_N'), ('15', 'ADS_RESET_N'), ('16', 'ADS_START'), ('17', 'ADS_CLK'), ('26', 'ADS_GPIO1'), ('25', 'ADS_GPIO2')):
    x, y = Pn('U1', n); wire((x, y), (1160, y)); lab(net, 1160, y, 'right')
x, y = Pn('U1', '14'); wire((x, y), (1170, y)); pwr('DVDD', 1170, y)
x, y = Pn('U1', '9'); cap('C6', 1180, y + 40); cap('C7', 1230, y + 40)
wire((x, y), Pn('C6', '1'), Pn('C7', '1')); gnd(*Pn('C6', '2')); gnd(*Pn('C7', '2')); lab('VREFP', 1205, y, 'up')
x, y = Pn('U1', '11'); cap('C8', 1180, y + 40); wire((x, y), Pn('C8', '1')); gnd(*Pn('C8', '2'))
x, y = Pn('U1', '27'); cap('C9', 1230, y + 40); wire((x, y), Pn('C9', '1')); gnd(*Pn('C9', '2'))
pwr('AVDD', *Pn('U1', '12')); pwr('DVDD', *Pn('U1', '23'))
for n in ('13', '24', '10'): gnd(*Pn('U1', n))

# ---------------- C 主控接口 ----------------
block(1280, 60, 1650, 590, 'C  主控接口：J2 → 20P 排线 → P44e', 'XIAO 焊在 P44e；电池线焊 XIAO 背面，不经本板')
PIN = [k for k in __import__('sch')._D['J2']['pins'] if int(k.split(':')[0]) <= 20]
sig = [(k.split(':')[0], k.split(':')[1], 'L', 34 + i * 21) for i, k in enumerate(PIN)]
ic('J2', 1490, 112, 110, 460, sig + [('21', 'SH1', 'R', 60), ('22', 'SH2', 'R', 400)], name_dy=240, ref_at=(1560, 136))
for k in PIN:
    n = k.split(':')[0]; net = EXPECT[('J2', n)]; x, y = Pn('J2', n)
    if net: lab(net, x, y, 'left')
    else: nc(x, y)
gnd(*Pn('J2', '21')); gnd(*Pn('J2', '22'))
text('J2 脚 n', 1296, 500, color='#555'); text('= P44e J1', 1296, 516, color='#555'); text('脚 21−n', 1296, 532, color='#555')

# ---------------- D 模拟电源与互锁 ----------------
block(1280, 600, 1650, 1080, 'D  模拟电源与 USB 互锁', 'TPS7A2030 常开；插 USB 时 Q1 把 ADS 拉进硬掉电')
ic('U3', 1440, 660, 130, 90, [('1', 'IN', 'L', 25), ('3', 'EN', 'L', 65), ('5', 'OUT', 'R', 25), ('4', 'NC', 'R', 65), ('2', 'GND', 'B', 65)], name_dy=62, ref_at=(1495, 678))
SIDE['C14'] = 1
cap('C14', 1340, 725); wire(Pn('C14', '1'), Pn('U3', '1')); pwr('3V3', 1370, 685); gnd(*Pn('C14', '2'))
wire(Pn('U3', '3'), (1400, 725), (1400, 685)); nc(*Pn('U3', '4')); gnd(*Pn('U3', '2'))
cap('C15', 1610, 725); wire(Pn('U3', '5'), Pn('C15', '1')); pwr('AVDD', 1600, 685); gnd(*Pn('C15', '2'))
res('R31', 1405, 835, 'h'); lab('MCU_PWDN', *Pn('R31', '1'), 'left')
mos('Q1', 1480, 950, 'N'); wire(Pn('R31', '2'), (1480, 835), Pn('Q1', '3')); lab('ADS_RESET_N', 1480, 835, 'right'); gnd(*Pn('Q1', '2'))
res('R25', 1400, 990, 'v'); gnd(*Pn('R25', '2'))
res('R32', 1345, 905, 'v'); lab('XIAO_5V', *Pn('R32', '1'), 'up')
wire(Pn('R32', '2'), (1345, 950), Pn('R25', '1'), Pn('Q1', '1'))
res('R26', 1590, 950, 'v'); pwr('AVDD', *Pn('R26', '1')); wire(Pn('R26', '2'), (1590, 1040)); lab('AVDD_SENSE', 1590, 1040, 'left')
text('台架要插 USB 读 ADS：拆 R32', 1296, 1062, color='#555')

# ---------------- E 默认电平 ----------------
block(30, 1100, 660, 1400, 'E  默认电平与 SCLK 串阻', '手册 10.1：电源稳定前数字输入要低；P44e 已管 PWDN、START、CS')
for i, (r, net) in enumerate((('R18', 'ADS_SCLK'), ('R19', 'ADS_DIN'), ('R20', 'ADS_CLK'), ('R21', 'ADS_GPIO1'), ('R22', 'ADS_GPIO2'))):
    x = 76 + i * 84
    res(r, x, 1236, 'v'); lab(net, *Pn(r, '1'), 'up'); gnd(*Pn(r, '2'))
res('R23', 200, 1345, 'h'); lab('ADS_SCLK', *Pn('R23', '1'), 'left'); lab('MCU_SCLK', *Pn('R23', '2'), 'right')

# ---------------- F 去耦与电池 ----------------
block(680, 1100, 1270, 1400, 'F  去耦', 'AVDD、DVDD 去耦贴着 U1 12、23 脚放；DVDD 过磁珠；C16 接 3V3 干线')
for x, r, net in ((730, 'C10', 'AVDD'), (800, 'C11', 'AVDD')):
    cap(r, x, 1270); pwr(net, *Pn(r, '1')); gnd(*Pn(r, '2'))
res('L1', 930, 1230, 'h'); pwr('3V3', *Pn('L1', '1'))
cap('C12', 1010, 1270); cap('C13', 1080, 1270); gnd(*Pn('C12', '2')); gnd(*Pn('C13', '2'))
cap('C16', 1190, 1270); pwr('3V3', *Pn('C16', '1')); gnd(*Pn('C16', '2'))
wire(Pn('L1', '2'), Pn('C12', '1'), Pn('C13', '1')); pwr('DVDD', 1045, 1230)
text('AVDD 脚 12', 736, 1350, color='#555'); text('DVDD 脚 23', 1010, 1350, color='#555'); text('3V3 入口', 1160, 1350, color='#555')

# ---------------- G 测试点 ----------------
block(1280, 1100, 1650, 1400, 'G  测试点', '电源、地和 ADS 复位线')
def tp(ref, x, y, net, d):
    pin(ref, '1', x, y); own(ref)
    svg.append(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="{SYM}" stroke-width="1.4"/>')
    if d == 'g': gnd(x, y + 6); wire((x, y), (x, y + 6))
    else: lab(net, x, y, d)
    own(ref); text(ref, x + 12 if d == 'left' else x - 12, y - 12, size=10, color=TXT, anchor='start' if d == 'left' else 'end')
for i, (r, net) in enumerate((('TP1', 'AVDD'), ('TP2', '3V3'))): tp(r, 1400, 1190 + i * 50, net, 'left')
tp('TP8', 1500, 1190, 'ADS_RESET_N', 'right')
tp('TP3', 1520, 1240, 'GND', 'g')

finish(1, '全图', list(VAL), 'ADS1292 双通道验证版', '串阻是候选，等 R01 对比；未打样、未上电、未贴肤')
