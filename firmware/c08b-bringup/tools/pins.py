#!/usr/bin/env python3
"""从主控板网表文件（支持嘉立创原生 .epcb2 或 JSON 读回）核对 U18（STM32L432KCU6）和 U13（nRF52840-QFAA）
每只脚的网名，生成两份 pins.h。任何一只脚对不上或板上多接了表里没写的信号脚，退出码非 0。"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# STM32L432KCU6 UFQFN32（DS11451 表 11）：GPIO 名 → 封装脚号（33 是底部散热焊盘）
L432_PKG = {'PA0': 6, 'PA1': 7, 'PA2': 8, 'PA3': 9, 'PA4': 10, 'PA5': 11, 'PA6': 12, 'PA7': 13,
            'PB0': 14, 'PB1': 15, 'PA8': 18, 'PA9': 19, 'PA10': 20, 'PA11': 21, 'PA12': 22,
            'PA13': 23, 'PA14': 24, 'PA15': 25, 'PB3': 26, 'PB4': 27, 'PB5': 28, 'PB6': 29, 'PB7': 30,
            'PH3': 31, 'PC14': 2, 'PC15': 3}

# nRF52840-QFAA QFN48（PS v1.11 §7.1.1）：P口.脚 → 封装脚号（49 是中心焊盘）
NRF_PKG = {'P0.00': 2, 'P0.01': 3, 'P0.04': 4, 'P0.05': 5, 'P0.07': 6, 'P0.08': 7, 'P1.08': 8, 'P1.09': 9, 'P0.11': 10,
           'P0.12': 11, 'P0.13': 13, 'P0.14': 14, 'P0.17': 15, 'P0.18': 16, 'P0.19': 18, 'P0.20': 19, 'P0.21': 20,
           'P0.22': 21, 'P0.23': 22, 'P0.24': 23, 'P1.00': 24, 'P0.09': 29, 'P0.10': 30, 'P1.15': 38, 'P0.03': 39,
           'P0.02': 40, 'P0.28': 41, 'P0.29': 42, 'P0.30': 43, 'P0.31': 44}

# (宏名, 端口, 板上网名, 说明)
L432 = [
    ('ANA_EN',     'PC14', 'ANA_EN',      '高 = 打开 AFE 缓冲（U10 反相出 OE_N）'),
    ('AFE_GPIO3',  'PA0',  'AFE_GPIO3',   'ADS GPIO3，只读'),
    ('ADS_PWDN',   'PA1',  'XIAO_PWDN',   '高 = ADS 工作（2CH 下兼作 ADS1292 PWDN/RESET）'),
    ('DRDY_A',     'PA2',  'XIAO_DRDY',   'U1 DRDY，低有效'),
    ('ADS_START',  'PA3',  'AFE_START',   '同步启动转换'),
    ('DRDY_B',     'PA4',  'AFE_DRDY_B',  '16CH 为 U2 DRDY；2CH 为 AVDD_SENSE（3.0V 监测）'),
    ('SPI1_SCK',   'PA5',  'XIAO_SCLK',   'SPI1 AF5'),
    ('SPI1_MISO',  'PA6',  'XIAO_MISO',   'SPI1 AF5'),
    ('SPI1_MOSI',  'PA7',  'XIAO_MOSI',   'SPI1 AF5'),
    ('CS_A',       'PB0',  'XIAO_CS',     'U1 片选，低有效'),
    ('CS_B',       'PB1',  'MCU_CS_B',    'U2 片选，低有效'),
    ('ADS_RESET',  'PA8',  'XIAO_RESET',  '低脉冲复位（ADS1298）'),
    ('IMU_SCL',    'PA9',  'IMU_SCL',     'I2C1 AF4，外部上拉 R198'),
    ('IMU_SDA',    'PA10', 'IMU_SDA',     'I2C1 AF4，外部上拉 R199'),
    ('USB_DM',     'PA11', 'MCU_DM',      '本固件不用'),
    ('USB_DP',     'PA12', 'MCU_DP',      '本固件不用'),
    ('LINK_CS',    'PA15', 'LINK_CS',     'SPI3 片选（GPIO 控制）'),
    ('LINK_SCK',   'PB3',  'LINK_SCK',    'SPI3 AF6'),
    ('LINK_MISO',  'PB4',  'LINK_MISO',   'SPI3 AF6'),
    ('LINK_MOSI',  'PB5',  'LINK_MOSI',   'SPI3 AF6'),
    ('LINK_RDY',   'PB6',  'LINK_RDY',    'nRF 拉高 = 可以发'),
    ('IMU_INT1',   'PB7',  'IMU_INT1',    '本固件只读'),
    ('BOOT0',      'PH3',  'VBUS_SENSE',  'R4U6 起并入 VBUS 分压（68k/100k）：插 USB 上电进 ROM DFU，运行态只读不驱动'),
]
NRF = [
    ('BENCH_EN',   'P0.00', 'MCU_BENCH_EN', '台架解互锁，本固件保持低'),
    ('VBUS_SENSE', 'P0.01', 'VBUS_SENSE',   'VBUS 68k/100k 分压（0.595×VBUS），数字读'),
    ('VBAT_SENSE', 'P0.04', 'VBAT_SENSE',   'VBAT/2，SAADC AIN2'),
    ('PWR_HOLD',   'P0.05', 'PWR_HOLD',     '高 = 保持供电'),
    ('LINK_RDY',   'P0.07', 'LINK_RDY',     '拉高 = SPIS 已准备好'),
    ('LINK_MOSI',  'P0.08', 'LINK_MOSI',    'SPIS MOSI'),
    ('LINK_MISO',  'P1.08', 'LINK_MISO',    'SPIS MISO'),
    ('LINK_SCK',   'P1.09', 'LINK_SCK',     'SPIS SCK'),
    ('LINK_CS',    'P0.11', 'LINK_CS',      'SPIS CSN'),
    ('CHRG_N',     'P0.12', 'CHRG_N',       '充电中为低（TP4054 开漏）'),
    ('BUTTON_N',   'P0.14', 'BUTTON_N',     '按下为低，外部上拉 R38'),
    ('OE_N',       'P0.17', 'OE_N',         '低 = AFE 缓冲打开（互锁状态）'),
    ('MCU_RST_N',  'P0.18', 'MCU_RST_N',    'nRF 自己的复位脚（UICR PSELRESET=18）'),
    ('LED',        'P0.23', 'MCU_LED',      'D401 阴极，低 = 亮'),
    ('UART_TX',    'P0.24', 'MCU_TX',       'UARTE0 TX，115200，引到 J301.5'),
]


def load_nets(geo: Path):
    nets = {}
    if geo.suffix == '.epcb2':
        des, pads = {}, {}
        for line in geo.read_text(encoding='utf-8').splitlines():
            if '||' not in line:
                continue
            h_s, b_s = line.split('||', 1)
            hj = json.loads(h_s)
            bj = json.loads(b_s.rstrip('|'))
            t = hj.get('type')
            if t == 'ATTR' and bj.get('key') == 'Designator' and bj.get('value') in ('U18', 'U13'):
                des[bj['parentId']] = bj['value']
            elif t == 'PAD_NET':
                arr = json.loads(hj['id'])
                pads[(arr[1], arr[2])] = bj.get('padNet', '')
        for cid, ref in des.items():
            for (c, num), net in pads.items():
                if c == cid and str(num).isdigit():
                    nets[(ref, int(num))] = net
        return nets
    g = json.loads(geo.read_text(encoding='utf-8'))
    for p in g['pads']:
        if p['ref'] in ('U18', 'U13') and p.get('num'):
            nets[(p['ref'], int(p['num']))] = p.get('net', '')
    return nets


def port_c_l432(p):
    return p[1], int(p[2:])


def port_c_nrf(p):
    port, pin = p[1], int(p.split('.')[1])
    return int(port), pin


def main():
    geo = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / 'hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6.epcb2'
    nets = load_nets(geo)
    bad = []
    for ref, table, pkg in (('U18', L432, L432_PKG), ('U13', NRF, NRF_PKG)):
        used = set()
        for name, port, net, _ in table:
            pin = pkg.get(port)
            if pin is None:
                bad.append(f'{ref} {name}: {port} 不在封装表里')
                continue
            got = nets.get((ref, pin))
            if got != net:
                bad.append(f'{ref} {name}: {port}=脚{pin}，板上是 {got!r}，表里写 {net!r}')
            used.add(pin)
        sig = {pin for port, pin in pkg.items()
               if nets.get((ref, pin)) not in (None, '', 'GND', '3V3') and not nets.get((ref, pin), '').startswith('$')}
        for pin in sorted(sig - used):
            bad.append(f'{ref} 脚{pin} 接 {nets[(ref, pin)]}，引脚表里没写')
    if bad:
        print('引脚核对不过：')
        for b in bad:
            print('  ' + b)
        sys.exit(1)
    hdr = '/* 由 tools/pins.py 生成，别手改。核对源：' + geo.name + ' */\n#pragma once\n'
    l = [hdr]
    for name, port, net, note in L432:
        c, n = port_c_l432(port)
        l.append(f'#define {name}_PORT GPIO{c}\n#define {name}_PIN {n}  /* {port} 脚{L432_PKG[port]} {net}：{note} */\n')
    (HERE / 'l432/pins.h').write_text(''.join(l), encoding='utf-8')
    l = [hdr]
    for name, port, net, note in NRF:
        po, n = port_c_nrf(port)
        l.append(f'#define {name}_PIN ({po} * 32 + {n})  /* {port} 脚{NRF_PKG[port]} {net}：{note} */\n')
    (HERE / 'nrf/pins.h').write_text(''.join(l), encoding='utf-8')
    print(f'引脚核对通过：L432 {len(L432)} 脚、nRF {len(NRF)} 脚与 {geo.name} 一致，头文件已生成')


if __name__ == '__main__':
    main()
