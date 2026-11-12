"""L432 + 52840 第 5 页：采样主控 STM32L432KCU6。读两颗 ADS、IMU，走 USB，经 SPI3 把数据交给 nRF52840。"""
import json
from sch import *

PAGE_REFS = json.loads((SRC / 'page-map.json').read_text())[4]['refs']
block(30, 60, 1180, 1080, 'A  采样主控：STM32L432KCU6，SPI1 → AFE，SPI3 → nRF52840，USB 全速',
      'USB 用内部 HSI48 + CRS，不要晶振；VDDUSB 片内连 VDD；PC14/PC15 只接低速脚')
L = [('11', 'PA5 SPI1_SCK', 40), ('12', 'PA6 SPI1_MISO', 70), ('13', 'PA7 SPI1_MOSI', 100), ('14', 'PB0', 130), ('15', 'PB1', 160),
     ('8', 'PA2 EXTI2', 200), ('10', 'PA4 EXTI4', 230), ('9', 'PA3', 270), ('7', 'PA1', 300), ('18', 'PA8', 330), ('6', 'PA0', 360),
     ('3', 'PC15', 410), ('2', 'PC14', 440)]
R = [('25', 'PA15 SPI3_NSS', 40), ('26', 'PB3 SPI3_SCK', 70), ('27', 'PB4 SPI3_MISO', 100), ('28', 'PB5 SPI3_MOSI', 130), ('29', 'PB6 EXTI6', 160),
     ('19', 'PA9 I2C1_SCL', 210), ('20', 'PA10 I2C1_SDA', 240), ('30', 'PB7 EXTI7', 270),
     ('22', 'PA12 USB_DP', 320), ('21', 'PA11 USB_DM', 350),
     ('23', 'PA13 SWDIO', 400), ('24', 'PA14 SWCLK', 430), ('4', 'NRST', 460), ('31', 'PH3 BOOT0', 490)]
T = [('1', 'VDD', 40), ('17', 'VDD', 80), ('5', 'VDDA', 160)]
B = [('16', 'VSS', 60), ('32', 'VSS', 110), ('33', 'VSS_PAD', 160)]
X0, Y0, WU, HU = 430, 300, 280, 540
ic('U18', X0, Y0, WU, HU, [(n, m, 'L', o) for n, m, o in L] + [(n, m, 'R', o) for n, m, o in R] + [(n, m, 'T', o) for n, m, o in T] + [(n, m, 'B', o) for n, m, o in B], name_dy=HU - 30)
for n, _, _ in L:
    if EXPECT[('U18', n)]: lab(EXPECT[('U18', n)], *Pn('U18', n), 'left')
    else: nc(*Pn('U18', n))
for n, _, _ in R[:10]: lab(EXPECT[('U18', n)], *Pn('U18', n), 'right')
for t, y in (('AFE SPI、片选', 60), ('DRDY', 215), ('AFE 控制', 285), ('AFE 电源使能', 425)): text(t, 150, Y0 + y, size=10, color='#555')
for t, y in (('到 nRF52840', 100), ('IMU', 240), ('USB', 335)): text(t, 900, Y0 + y, size=10, color='#555')
# 供电：VDD/VDDA 并到 3V3 母线，每脚 100 nF，VDDA 再加 1 µF
for n, _, _ in T: wire(Pn('U18', n), (Pn('U18', n)[0], 145))
wire((180, 145), (Pn('U18', '5')[0], 145)); pwr('3V3', 180, 145)
for ref, x in zip(['C72', 'C73'], (290, 350)):
    cap(ref, x, 185); gnd(*Pn(ref, '2'))
text('C72 贴 VDD；C73 贴 VDDA；VDD 脚 1 经孔接 C51', 470, 130, color='#555')
# 地
y = Pn('U18', '16')[1] + 30
wire(Pn('U18', '16'), (Pn('U18', '16')[0], y), (Pn('U18', '33')[0], y), Pn('U18', '33')); wire(Pn('U18', '32'), (Pn('U18', '32')[0], y)); gnd(Pn('U18', '32')[0], y)
# 调试焊盘 J302：只有 SWD 两脚，3V3 和 GND 从 J301 取；复位、BOOT0 就地接件
ic('J302', 950, 700, 90, 80, [('2', 'SWDIO', 'L', 20), ('1', 'SWCLK', 'L', 50)], name_dy=72, ref_at=(950, 690))
wire(Pn('U18', '23'), (800, Pn('U18', '23')[1]), (800, Pn('J302', '2')[1]), Pn('J302', '2'))
wire(Pn('U18', '24'), (820, Pn('U18', '24')[1]), (820, Pn('J302', '1')[1]), Pn('J302', '1'))
cap('C75', 840, 900); wire(Pn('U18', '4'), (840, Pn('U18', '4')[1]), Pn('C75', '1')); gnd(*Pn('C75', '2'))
res('R211', 880, 900, 'v'); wire(Pn('U18', '31'), (880, Pn('U18', '31')[1]), Pn('R211', '1')); gnd(*Pn('R211', '2'))
wire((880, Pn('U18', '31')[1]), (935, Pn('U18', '31')[1])); lab('VBUS_SENSE', 935, Pn('U18', '31')[1], 'right')
text('BOOT0 接 VBUS_SENSE（插 USB 上电进 DFU）；R211 预留不贴', 740, 1000, color='#555')
# VBUS 分压给 nRF52840 判 USB 插入
block(1200, 60, 1650, 460, 'B  USB 插入检测与 DFU 引导：VBUS 分压 → VBUS_SENSE', 'L432 的 IO 已用满，所以由 nRF52840 读，再经链路告诉 L432')
res('R209', 1320, 200, 'v'); pwr('VBUS', *Pn('R209', '1'))
res('R210', 1320, 320, 'v'); wire(Pn('R209', '2'), Pn('R210', '1')); gnd(*Pn('R210', '2'))
wire((1320, 260), (1420, 260)); lab('VBUS_SENSE', 1420, 260, 'right')
finish(5, '采样主控', PAGE_REFS, 'C08B 主控板 L432 + 52840：STM32L432KCU6 采样 + USB；与 nRF52840 走 SPI3 + LINK_RDY', 'SPI1 读两颗 ADS1298，I2C1 读 IMU，SPI3 + LINK_RDY 与 nRF52840 通信。')
