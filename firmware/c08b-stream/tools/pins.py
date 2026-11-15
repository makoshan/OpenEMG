#!/usr/bin/env python3
"""C08B 流式固件引脚对账与源码安全红线门禁（支持 R4U6 / R4U6N 及双仓目录布局）。

功能：
  1. `python -B tools/pins.py [--check-headers] [<epcb2_or_json>]`：
     直读主控板 `.epcb2` 或 JSON 读回文件，逐脚核对 U18(STM32L432KCU6, 23脚) 与
     U13(nRF52840-QFAA, 15脚)，任何网名偏差或多接未声明信号脚立即非 0 退出；
     `--check-headers` 仅核对磁盘已提交的 `l432/pins.h` 与 `nrf/pins.h` 是否逐字节一致（不改写源码树）。
  2. `python -B tools/pins.py --check-safety [--self-test]`：
     扫描固件源码树，强制拦截 10 条硬件安全红线（并内置 10 项必败变异反例自检）：
       - 默认硬件锁 `MAKO_C08B_AFE_ENABLED` 与 `MAKO_BENCH_MEASURED` 必须为 `0`；
       - `C08B_ADS1292_POR_WAIT_MS` 必须 `>= 1000`（满足 ADS1292 VCAP1=1µF 1s 上电建立）；
       - `C08B_BLE_DEV_NAME` 必须为 `"YUANLI-C08B"`（对齐 `host/devices/c08b-*.json`）；
       - ADS1292 `RESP2(0x0A)` 必须保持 `0x07`（TI SBAS502C 表 24 非 R 版 `bit2=1`）；
       - ADS1298 `CONFIG3` 严禁置 `RLDREF_INT(bit3=0x08)` 或 `VREF_4V(bit5=0x20)`（C08B `Pin 60 RLDREF` 硬连 `AGND`，写 `0xCC` 会短路内部缓冲）；
       - L432 严禁在 `afe_safe_off()` 之外将 `ADS_PWDN` 拉低（复位脉冲仅允许打 `ADS_RESET`，防止放光 `VCAP1`）；
       - 禁止出现 `NRF_CLOCK_LF_SRC_XTAL` / `LFCLKSRC_SRC_Xtal`（`P0.00/XL1=BENCH_EN`、`P0.01/XL2=VBUS_SENSE`）；
       - 禁止将 `OE_N`（P0.17）配置为输出；
       - 禁止将 `BOOT0`（PH3=VBUS_SENSE）配置为输出；
       - 禁止将 `BENCH_EN`（P0.00）置高旁路互锁。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

L432_PKG = {
    'PA0': 6, 'PA1': 7, 'PA2': 8, 'PA3': 9, 'PA4': 10, 'PA5': 11, 'PA6': 12, 'PA7': 13,
    'PB0': 14, 'PB1': 15, 'PA8': 18, 'PA9': 19, 'PA10': 20, 'PA11': 21, 'PA12': 22,
    'PA13': 23, 'PA14': 24, 'PA15': 25, 'PB3': 26, 'PB4': 27, 'PB5': 28, 'PB6': 29, 'PB7': 30,
    'PH3': 31, 'PC14': 2, 'PC15': 3,
}

NRF_PKG = {
    'P0.00': 2, 'P0.01': 3, 'P0.04': 4, 'P0.05': 5, 'P0.07': 6, 'P0.08': 7, 'P1.08': 8, 'P1.09': 9, 'P0.11': 10,
    'P0.12': 11, 'P0.13': 13, 'P0.14': 14, 'P0.17': 15, 'P0.18': 16, 'P0.19': 18, 'P0.20': 19, 'P0.21': 20,
    'P0.22': 21, 'P0.23': 22, 'P0.24': 23, 'P1.00': 24, 'P0.09': 29, 'P0.10': 30, 'P1.15': 38, 'P0.03': 39,
    'P0.02': 40, 'P0.28': 41, 'P0.29': 42, 'P0.30': 43, 'P0.31': 44,
}

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
    ('LINK_RDY',   'PB6',  'LINK_RDY',    'nRF 拉高 = SPIS 接收缓冲已就绪'),
    ('IMU_INT1',   'PB7',  'IMU_INT1',    '本固件只读'),
    ('BOOT0',      'PH3',  'VBUS_SENSE',  'R4U6 起并入 VBUS 分压（68k/100k）：运行态只读不驱动'),
]

NRF = [
    ('BENCH_EN',   'P0.00', 'MCU_BENCH_EN', '台架解互锁（复用 XL1！严禁开外部低频晶振，保持输出低）'),
    ('VBUS_SENSE', 'P0.01', 'VBUS_SENSE',   'VBUS 68k/100k 分压（复用 XL2！只读数字输入）'),
    ('VBAT_SENSE', 'P0.04', 'VBAT_SENSE',   'VBAT/2，SAADC AIN2'),
    ('PWR_HOLD',   'P0.05', 'PWR_HOLD',     '高 = 保持供电'),
    ('LINK_RDY',   'P0.07', 'LINK_RDY',     '拉高 = SPIS 已准备好'),
    ('LINK_MOSI',  'P0.08', 'LINK_MOSI',    'SPIS MOSI'),
    ('LINK_MISO',  'P1.08', 'LINK_MISO',    'SPIS MISO'),
    ('LINK_SCK',   'P1.09', 'LINK_SCK',     'SPIS SCK'),
    ('LINK_CS',    'P0.11', 'LINK_CS',      'SPIS CSN'),
    ('CHRG_N',     'P0.12', 'CHRG_N',       '充电中为低（TP4054 开漏）'),
    ('BUTTON_N',   'P0.14', 'BUTTON_N',     '按下为低，外部上拉 R38'),
    ('OE_N',       'P0.17', 'OE_N',         '低 = AFE 缓冲打开（互锁线，严禁推挽输出！）'),
    ('MCU_RST_N',  'P0.18', 'MCU_RST_N',    'nRF 复位脚'),
    ('LED',        'P0.23', 'MCU_LED',      'D401 阴极，低 = 亮'),
    ('UART_TX',    'P0.24', 'MCU_TX',       'UARTE0 TX，115200，引到 J301.5'),
]


def default_board_path() -> Path:
    candidates = [
        HERE.parents[1] / 'hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6.epcb2',
        HERE.parent / 'mainboard-r4u6-boot0-20261111/C08B-main-R4U6.epcb2',
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[0]


def load_nets(geo: Path) -> dict[tuple[str, int], str]:
    nets: dict[tuple[str, int], str] = {}
    if geo.suffix == '.epcb2':
        des, pads = {}, {}
        for line in geo.read_text(encoding='utf-8').splitlines():
            if '||' not in line:
                continue
            h_s, b_s = line.split('||', 1)
            hj = json.loads(h_s)
            bj = json.loads(b_s.rstrip('|'))
            t = hj.get('type')
            if t == 'ATTR' and bj.get('key') == 'Designator' and bj.get('value') in ('U18', 'U13', 'J_AFE'):
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
        if p['ref'] in ('U18', 'U13', 'J_AFE') and str(p.get('num', '')).isdigit():
            nets[(p['ref'], int(p['num']))] = p.get('net', '')
    return nets


def render_headers(source_label: str = 'C08B-main-R4U6.epcb2') -> tuple[str, str]:
    hdr = f'/* 由 tools/pins.py 从 {source_label} 核对生成，请勿手改。 */\n#pragma once\n'
    l_lines = [hdr]
    for name, port, net, note in L432:
        g, n = port[1], int(port[2:])
        l_lines.append(f'#define {name}_PORT GPIO{g}\n#define {name}_PIN  {n}  /* {port} = {net}：{note} */\n')

    n_lines = [hdr]
    for name, port, net, note in NRF:
        po, pi = int(port[1]), int(port.split('.')[1])
        n_lines.append(f'#define {name}_PIN {po * 32 + pi}u  /* {port} = {net}：{note} */\n')
    return ''.join(l_lines), ''.join(n_lines)


def verify_and_emit(geo: Path, write_headers: bool = True, check_headers: bool = False) -> list[str]:
    nets = load_nets(geo)
    bad: list[str] = []
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
        sig = {
            pin for port, pin in pkg.items()
            if nets.get((ref, pin)) not in (None, '', 'GND', '3V3')
            and not nets.get((ref, pin), '').startswith('$')
        }
        for pin in sorted(sig - used):
            port = [k for k, v in pkg.items() if v == pin][0]
            bad.append(f'{ref} 脚{pin}（{port}）板上接了 {nets[(ref, pin)]!r}，表里没写')
    if bad:
        return bad

    l_txt, n_txt = render_headers('C08B-main-R4U6.epcb2')
    if check_headers:
        lp = HERE / 'l432/pins.h'
        np_ = HERE / 'nrf/pins.h'
        if not lp.is_file() or lp.read_text(encoding='utf-8') != l_txt:
            bad.append('l432/pins.h 与标准核对内容不一致，请重新运行 tools/pins.py')
        if not np_.is_file() or np_.read_text(encoding='utf-8') != n_txt:
            bad.append('nrf/pins.h 与标准核对内容不一致，请重新运行 tools/pins.py')
        return bad

    if write_headers:
        (HERE / 'l432').mkdir(exist_ok=True)
        (HERE / 'l432/pins.h').write_text(l_txt, encoding='utf-8')
        (HERE / 'nrf').mkdir(exist_ok=True)
        (HERE / 'nrf/pins.h').write_text(n_txt, encoding='utf-8')
    return []


# 主控 J_AFE.n <-> 子板 J_AFE/J2.(21-n) 全 20 脚同面排线跨板物理映射真值表
JAFE_CROSS_MAP = [
    (1,  '3V3_AFE',    20, '3V3',        '3V3'),
    (2,  '3V3_AFE',    19, '3V3',        '3V3'),
    (3,  '',           18, 'ADS_CLKSEL', 'NC'),
    (4,  'ADS_DRDY_A', 17, 'ADS_DRDY_A', 'ADS_DRDY_N'),
    (5,  'AFE_GPIO3',  16, 'AFE_GPIO3',  'NC'),
    (6,  'DOUT_B',     15, 'DOUT_B',     'ADS_DOUT'),
    (7,  'GND',        14, 'GND',        'GND'),
    (8,  '',           13, '',           'GND'),
    (9,  'GND',        12, 'GND',        'GND'),
    (10, 'AFE_SCLK',   11, 'SCLK_B',     'MCU_SCLK'),
    (11, 'AFE_CS_A',   10, 'ADS_CS_A',   'ADS_CS_N'),
    (12, 'AFE_START',   9, 'ADS_START',  'ADS_START'),
    (13, '',            8, 'AFE_CLK_IN', 'NC'),
    (14, 'AFE_RESET',   7, 'ADS_RESET',  'NC'),
    (15, 'AFE_PWDN',    6, 'ADS_PWDN',   'MCU_PWDN'),
    (16, 'AFE_DIN',     5, 'DIN_B',      'ADS_DIN'),
    (17, 'AFE_CS_B',    4, 'ADS_CS_B',   'NC'),
    (18, 'AFE_DRDY_B',  3, 'ADS_DRDY_B', 'AVDD_SENSE'),
    (19, '',            2, '',           'XIAO_5V'),
    (20, 'GND',         1, 'GND',        'GND'),
]


def _find_first(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.is_file():
            return p
    return None


def verify_jafe_cross_boards(main_board: Path) -> list[str]:
    bad: list[str] = []
    nets = load_nets(main_board)
    d20_path = _find_first([
        HERE.parents[1] / 'hardware/16ch-c08b-round/schematics-afe/c08b-pcb-pins.json',
        HERE.parent / 'c08b-sch-d20-20261109/c08b-pcb-pins.json',
    ])
    d2ch_path = _find_first([
        HERE.parents[1] / 'hardware/2ch-ads1292/schematics/design.json',
        HERE.parent / 'ads1292-2ch-20261104/design.json',
    ])
    if d20_path is None or d2ch_path is None:
        return ['缺少 D20 c08b-pcb-pins.json 或 2ch design.json，无法执行 J_AFE 20P 跨板对账']

    d20_raw = json.loads(d20_path.read_text(encoding='utf-8'))
    d20_jafe = {
        int(x['pin']): x.get('net', '')
        for x in d20_raw.get('pins', [])
        if x.get('ref') == 'J_AFE' and str(x.get('pin', '')).isdigit()
    }
    d2ch_raw = json.loads(d2ch_path.read_text(encoding='utf-8'))
    j2_pins_raw = d2ch_raw['parts']['J2']['pins']
    d2ch_j2 = {int(k.split(':', 1)[0]): v for k, v in j2_pins_raw.items()}

    for m_pin, exp_main, sub_pin, exp_d20, exp_2ch in JAFE_CROSS_MAP:
        if sub_pin != 21 - m_pin:
            bad.append(f'JAFE_CROSS_MAP 表项 {m_pin}<->{sub_pin} 不满足 21-n')
        got_main = nets.get(('J_AFE', m_pin), '')
        got_d20 = d20_jafe.get(sub_pin, '<MISSING>')
        got_2ch = d2ch_j2.get(sub_pin, '<MISSING>')
        if got_main != exp_main:
            bad.append(f'主控 J_AFE.{m_pin}: 实读 {got_main!r} != 期望 {exp_main!r}')
        if got_d20 != exp_d20:
            bad.append(f'D20 J_AFE.{sub_pin}(对主控.{m_pin}): 实读 {got_d20!r} != 期望 {exp_d20!r}')
        if got_2ch != exp_2ch:
            bad.append(f'2ch J2.{sub_pin}(对主控.{m_pin}): 实读 {got_2ch!r} != 期望 {exp_2ch!r}')

    # 核实 2ch-ads1292 复位链路：J2.6(MCU_PWDN) -> R31 -> ADS_RESET_N -> U1 Pin15(PWDN/RESET)
    r31 = set(d2ch_raw['parts']['R31']['pins'].values())
    u1_p15 = d2ch_raw['parts']['U1']['pins'].get('15:PWDN/RESET')
    if r31 != {'MCU_PWDN', 'ADS_RESET_N'} or u1_p15 != 'ADS_RESET_N':
        bad.append(f'2ch 复位链路异常：R31={r31!r}, U1.15={u1_p15!r}')
    return bad


# 旗舰 6 层双核主控 MCU-U9 FPC1.k (1..20) <-> 超薄双 30P 采集板 AFE-30P FPC2.(21-k) 独立专属映射真值表
# 注意：MCU-U9 FPC1 (1=GND, 19/20=3V3_AFE) 与 R4U6 J_AFE (1/2=3V3_AFE, 20=GND) 首尾电源极性相反，严禁跨代混插！
U9_FPC1_TO_AFE30P_MAP = [
    (1,  'GND',        20, 'GND'),
    (2,  '',           19, 'GND'),
    (3,  'AFE_DRDY_B', 18, 'DRDY2#'),
    (4,  'AFE_CS_B',   17, 'CS#2'),
    (5,  'AFE_DIN',    16, 'DIN'),
    (6,  'AFE_PWDN',   15, 'PWDN#'),
    (7,  'AFE_RESET',  14, 'RESET#'),
    (8,  '',           13, 'CLK'),
    (9,  'AFE_START',  12, 'START'),
    (10, 'AFE_CS_A',   11, 'CS#'),
    (11, 'AFE_SCLK',   10, 'SCLK'),
    (12, 'GND',         9, 'GND'),
    (13, '',            8, 'GND'),
    (14, 'GND',         7, 'GND'),
    (15, 'DOUT_B',      6, 'DOUT'),
    (16, 'AFE_GPIO3',   5, 'GPIO3'),
    (17, 'ADS_DRDY_A',  4, 'DRDY#'),
    (18, '',            3, 'CLKSEL'),
    (19, '3V3_AFE',     2, '+3.3V'),
    (20, '3V3_AFE',     1, '+3.3V'),
]


def _load_epro2_pcb_boards(epro2_path: Path) -> list[dict[tuple[str, int], str]]:
    with zipfile.ZipFile(epro2_path) as zf:
        doc = zf.read(next(n for n in zf.namelist() if n.endswith('.epru'))).decode('utf-8', 'ignore')
    boards: list[tuple[dict[str, str], dict[tuple[str, int], str]]] = []
    active = False
    for line in doc.splitlines():
        if '||' not in line:
            continue
        left, right = line.split('||', 1)
        right = right.removesuffix('|')
        if not right:
            continue
        h = json.loads(left)
        if h['type'] not in ('DOCHEAD', 'ATTR', 'PAD_NET'):
            continue
        v, _ = json.JSONDecoder().raw_decode(right)
        if h['type'] == 'DOCHEAD':
            if v.get('docType') == 'PCB':
                active = True
                boards.append(({}, {}))
            else:
                active = False
        elif active and h['type'] == 'ATTR' and v.get('key') == 'Designator':
            boards[-1][0][v['parentId']] = v.get('value', '')
        elif active and h['type'] == 'PAD_NET':
            _, cid, pin, _ = json.loads(h['id'])
            if str(pin).isdigit():
                boards[-1][1][(cid, int(pin))] = v.get('padNet', '')
    return [
        {(des[cid], pin): net for (cid, pin), net in pads.items() if cid in des}
        for des, pads in boards
    ]


def _load_u9_epro2_nets(epro2_path: Path) -> dict[tuple[str, int], str]:
    boards = _load_epro2_pcb_boards(epro2_path)
    for nets in boards:
        if ('U7', 31) in nets and ('U8', 2) in nets:
            return nets
    return boards[0] if boards else {}


def _load_afe30p_from_epro2(epro2_path: Path) -> dict[tuple[str, int], str] | None:
    for nets in _load_epro2_pcb_boards(epro2_path):
        if ('U1', 39) in nets and ('U2', 39) in nets and ('FPC2', 1) in nets:
            return nets
    return None


def _load_afe30p_epro_nets(epro_path: Path) -> dict[tuple[str, int], str]:
    if epro_path.suffix == '.epro2':
        got = _load_afe30p_from_epro2(epro_path)
        return got if got is not None else {}
    with zipfile.ZipFile(epro_path) as zf:
        epcbs = [n for n in zf.namelist() if n.endswith('.epcb')]
        pcb_name = max(epcbs, key=lambda n: zf.getinfo(n).file_size)
        rows = [json.loads(ln) for ln in zf.read(pcb_name).splitlines() if ln.startswith(b'[')]
    rows = rows[max(i for i, r in enumerate(rows) if r[:2] == ['DOCTYPE', 'PCB']) :]
    refs = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator'}
    return {
        (refs[r[1]], int(r[2])): r[3]
        for r in rows
        if r[0] == 'PAD_NET' and r[1] in refs and str(r[2]).isdigit()
    }


def verify_u9_stream_compat(u9_epro2: Path, afe30p_epro: Path | None = None, selftest: bool = False) -> list[str]:
    bad: list[str] = []
    if not u9_epro2.is_file():
        return [f'缺少 MCU-U9 / 双板工程 ({u9_epro2})']
    u9_nets = _load_u9_epro2_nets(u9_epro2)
    afe_nets = _load_afe30p_from_epro2(u9_epro2)
    if afe_nets is None:
        if afe30p_epro is None or not afe30p_epro.is_file():
            return [f'缺少 AFE-30P 采集板数据 ({afe30p_epro})']
        afe_nets = _load_afe30p_epro_nets(afe30p_epro)

    def _check_pair(u9_d: dict[tuple[str, int], str], afe_d: dict[tuple[str, int], str]) -> list[str]:
        errs: list[str] = []
        used_u7 = {4, 23, 24}
        for pin, exp_dbg in ((4, 'L_NRST'), (23, 'L_SWDIO'), (24, 'L_SWCLK')):
            if u9_d.get(('U7', pin), '') != exp_dbg:
                errs.append(f'MCU-U9 U7 调试脚 {pin}: 实读 {u9_d.get(("U7", pin))!r} != {exp_dbg!r}')
        for name, port, net, _ in L432:
            pin = L432_PKG[port]
            exp_net = 'L_BOOT0' if name == 'BOOT0' else net
            got = u9_d.get(('U7', pin), '')
            if got != exp_net:
                errs.append(f'MCU-U9 U7 {name} ({port}/脚{pin}): 实读 {got!r} != 期望 {exp_net!r}')
            used_u7.add(pin)
        for port, pin in L432_PKG.items():
            if pin not in used_u7 and u9_d.get(('U7', pin), '') not in ('', 'GND', '3V3'):
                errs.append(f'MCU-U9 U7 多接未声明信号脚 {pin}({port})={u9_d[("U7", pin)]!r}')

        used_u8 = set()
        for name, port, net, _ in NRF:
            pin = NRF_PKG[port]
            got = u9_d.get(('U8', pin), '')
            if got != net:
                errs.append(f'MCU-U9 U8 {name} ({port}/脚{pin}): 实读 {got!r} != 期望 {net!r}')
            used_u8.add(pin)
        for port, pin in NRF_PKG.items():
            if pin not in used_u8 and u9_d.get(('U8', pin), '') not in ('', 'GND', '3V3'):
                errs.append(f'MCU-U9 U8 多接未声明信号脚 {pin}({port})={u9_d[("U8", pin)]!r}')

        for m_pin, exp_u9, sub_pin, exp_afe in U9_FPC1_TO_AFE30P_MAP:
            if sub_pin != 21 - m_pin:
                errs.append(f'U9_FPC1_TO_AFE30P_MAP {m_pin}<->{sub_pin} 不满足 21-k')
            got_u9 = u9_d.get(('FPC1', m_pin), '')
            got_afe = afe_d.get(('FPC2', sub_pin), '')
            if got_u9 != exp_u9:
                errs.append(f'MCU-U9 FPC1.{m_pin}: 实读 {got_u9!r} != 期望 {exp_u9!r}')
            if got_afe != exp_afe:
                errs.append(f'AFE-30P FPC2.{sub_pin}(对 FPC1.{m_pin}): 实读 {got_afe!r} != 期望 {exp_afe!r}')
        return errs

    bad.extend(_check_pair(u9_nets, afe_nets))
    if bad:
        return bad

    if selftest:
        # 反例 A：模拟 FPC2.17/18 (CS#2 / DRDY2#) 交叉回退
        bad_swap = dict(afe_nets)
        bad_swap[('FPC2', 17)], bad_swap[('FPC2', 18)] = bad_swap[('FPC2', 18)], bad_swap[('FPC2', 17)]
        if len(_check_pair(u9_nets, bad_swap)) < 2:
            bad.append('U9 selftest 失败：未拦截 AFE-30P FPC2.17/18 交叉')
        # 反例 B：模拟误将 D20 (20=3V3, 1=GND) 跨代混插到 MCU-U9 FPC1 -> 首尾电源/地必反接报红
        fake_d20_as_fpc2 = {('FPC2', sub_p): d20_net for _, _, sub_p, d20_net, _ in JAFE_CROSS_MAP}
        cross_errs = _check_pair(u9_nets, fake_d20_as_fpc2)
        if not (any('FPC2.20' in e for e in cross_errs) and any('FPC2.1(' in e for e in cross_errs)):
            bad.append('U9 selftest 失败：未拦截 MCU-U9 与 D20 跨代 20P 电源反接混插')
    return bad


def strip_c_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    return text


def check_source_safety(root: Path) -> list[str]:
    errors: list[str] = []
    bench_h = strip_c_comments((root / 'common/bench_release.h').read_text(encoding='utf-8'))
    if not re.search(r'#\s*define\s+MAKO_C08B_AFE_ENABLED\s+0\b', bench_h):
        errors.append('bench_release.h 默认硬件锁 MAKO_C08B_AFE_ENABLED 未置 0')
    if not re.search(r'#\s*define\s+MAKO_BENCH_MEASURED\s+0\b', bench_h):
        errors.append('bench_release.h 默认实测门 MAKO_BENCH_MEASURED 未置 0')
    m_por = re.search(r'#\s*define\s+C08B_ADS1292_POR_WAIT_MS\s+(\d+)u?\b', bench_h)
    if not m_por or int(m_por.group(1)) < 1000:
        errors.append('bench_release.h C08B_ADS1292_POR_WAIT_MS 低于 1000 ms（违反 ADS1292 VCAP1=1uF 上电建立要求）')
    m_rst = re.search(r'#\s*define\s+C08B_ADS1292_RESET_LOW_US\s+(\d+)u?\b', bench_h)
    if not m_rst or not (10 <= int(m_rst.group(1)) <= 100):
        errors.append('bench_release.h C08B_ADS1292_RESET_LOW_US 必须介于 10..100 us（>=1 t_MOD 且远低于 4000 us 硬掉电门限）')
    m_settle = re.search(r'#\s*define\s+C08B_ADS1292_RESET_SETTLE_US\s+(\d+)u?\b', bench_h)
    if not m_settle or int(m_settle.group(1)) < 40:
        errors.append('bench_release.h C08B_ADS1292_RESET_SETTLE_US 低于 40 us（违反 >= 18 t_CLK 复位恢复时间）')
    if not re.search(r'#\s*define\s+C08B_BLE_DEV_NAME\s+"YUANLI-C08B"', bench_h):
        errors.append('bench_release.h C08B_BLE_DEV_NAME 未固定为 "YUANLI-C08B"')

    proto_h = strip_c_comments((root / 'common/stream_proto.h').read_text(encoding='utf-8'))
    if not re.search(r'cfg\[\s*0x0A\s*\]\s*=\s*0x07u?\b', proto_h):
        errors.append('stream_proto.h ADS1292 RESP2(0x0A) 未固定为 0x07')

    # 提取 c08b_build_ads1298_regs 函数体，确保 CONFIG3 绝不置 VREF_4V(0x20)、RLD_MEAS(0x10) 或 RLDREF_INT(0x08)，
    # 且 TST1 下 U1/U2 均置 int_test=true（v0.01 17/18 脚独立悬空），无 MUX=0x02(RLD_MEASURE)
    m_fn98 = re.search(r'c08b_build_ads1298_regs\s*\(.*?\n\{(.*?)\n\}', proto_h, flags=re.S)
    if not m_fn98:
        errors.append('stream_proto.h 未找到 c08b_build_ads1298_regs')
    else:
        body98 = m_fn98.group(1)
        if not re.search(r'case\s+C08B_MODE_TST1\s*:[^\n]*\bint_test\s*=\s*true\s*;', body98):
            errors.append('stream_proto.h c08b_build_ads1298_regs 在 C08B_MODE_TST1 下必须置 int_test = true（v0.01 AFE-30P U1/U2 17/18 脚独立悬空）')
        if re.search(r'cfg\s*\[\s*0x0[5-9A-Ca-c]\s*\]\s*=\s*0x02u?\b', body98):
            errors.append('stream_proto.h c08b_build_ads1298_regs 严禁将 ADS1298 通道设为 MUX=0x02 (RLD_MEASURE，v0.01 Pin62 接 +2.5V)')
        cfg3_stmts = re.findall(r'(?:cfg\s*\[\s*0x03\s*\]|\*\s*cfg3_step2)\s*=[^;]+;', body98)
        if len(cfg3_stmts) < 2:
            errors.append('stream_proto.h c08b_build_ads1298_regs 缺少 cfg[0x03] 或 *cfg3_step2 赋值语句')
        for stmt in cfg3_stmts:
            for hx in re.findall(r'0x([0-9A-Fa-f]{2})u?\b', stmt):
                val = int(hx, 16)
                if val == 0x03:
                    continue  # 跳过下标 [0x03]
                if (val & 0x38) != 0:
                    errors.append(
                        f'stream_proto.h c08b_build_ads1298_regs 出现违禁 CONFIG3 值 0x{val:02X}'
                        '（C08B Pin60 RLDREF 硬连 AGND 禁置 RLDREF_INT=0x08，v0.01 Pin62 RLDIN 硬连 +2.5V 禁置 RLD_MEAS=0x10，且禁置 VREF_4V=0x20）'
                    )

    l432_c = strip_c_comments((root / 'l432/main.c').read_text(encoding='utf-8'))
    # SET(ADS_PWDN, 0) 仅允许出现在 afe_safe_off() 与 pulse_ads1292_pwdn_reset() 中各 1 次，
    # 且 pulse_ads1292_pwdn_reset() 调用必须处于 if (g_sess.id_a != 0x92u) 守卫内（严禁对 ADS1298 拉低 PWDN）
    pwdn_zeros = len(re.findall(r'\bSET\s*\(\s*ADS_PWDN\s*,\s*0\s*\)', l432_c))
    if pwdn_zeros != 2:
        errors.append(f'l432/main.c SET(ADS_PWDN, 0) 出现 {pwdn_zeros} 次（仅允许 afe_safe_off 与 pulse_ads1292_pwdn_reset 各 1 次）')
    pulse_calls = len(re.findall(r'\bpulse_ads1292_pwdn_reset\s*\(\s*\)\s*;', l432_c))
    guarded_pulse = re.search(
        r'if\s*\(\s*g_sess\.id_a\s*!=\s*0x92u?\s*\)\s*\{\s*pulse_ads1292_pwdn_reset\s*\(\s*\)\s*;',
        l432_c,
    )
    if pulse_calls != 1 or not guarded_pulse:
        errors.append('l432/main.c pulse_ads1292_pwdn_reset() 必须且仅能在 if (g_sess.id_a != 0x92u) 守卫内调用 1 次')

    all_c = []
    for sub in ('common', 'l432', 'nrf'):
        d = root / sub
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.suffix in ('.c', '.h', '.inc'):
                    all_c.append((f.relative_to(root).as_posix(), strip_c_comments(f.read_text(encoding='utf-8'))))

    for rel, code in all_c:
        if re.search(r'\b(NRF_CLOCK_LF_SRC_XTAL|CLOCK_LFCLKSRC_SRC_Xtal|NRF_CLOCK_LF_SRC_SYNTH)\b', code):
            errors.append(f'{rel}: 严禁使用外部低频晶振 XTAL（C08B 的 P0.00/XL1=BENCH_EN、P0.01/XL2=VBUS_SENSE）')
        if re.search(r'\bgpio_out\s*\(\s*OE_N_PIN\b|\bgpio_set\s*\(\s*OE_N_PIN\b|\bOUT_INIT\s*\(\s*OE_N\b', code):
            errors.append(f'{rel}: 严禁将互锁线 OE_N 配置为输出驱动')
        if re.search(r'\bOUT_INIT\s*\(\s*BOOT0\b|\bSET\s*\(\s*BOOT0\b|pin_mode\s*\(\s*BOOT0_PORT\s*,\s*BOOT0_PIN\s*,\s*M_OUT\b', code):
            errors.append(f'{rel}: 严禁驱动 PH3-BOOT0（接 VBUS_SENSE 分压）')
        if re.search(r'\bgpio_out\s*\(\s*BENCH_EN_PIN\s*,\s*[1-9]|\bgpio_set\s*\(\s*BENCH_EN_PIN\s*,\s*[1-9]', code):
            errors.append(f'{rel}: 严禁在候选固件中拉高 BENCH_EN 旁路硬件互锁')
    return errors


def run_safety_selftest(root: Path) -> None:
    base_err = check_source_safety(root)
    if base_err:
        raise RuntimeError(f'当前源码未过安全红线：{base_err}')

    mutations = [
        ('common/bench_release.h', '#define MAKO_C08B_AFE_ENABLED 0', '#define MAKO_C08B_AFE_ENABLED 1', '偷开 AFE 锁'),
        ('common/bench_release.h', '#define MAKO_BENCH_MEASURED 0', '#define MAKO_BENCH_MEASURED 1', '偷开实测锁'),
        ('common/bench_release.h', '#define C08B_ADS1292_POR_WAIT_MS 1050u', '#define C08B_ADS1292_POR_WAIT_MS 250u', 'ADS1292 POR 等待缩短到 250ms'),
        ('common/bench_release.h', '#define C08B_ADS1292_RESET_LOW_US 20u', '#define C08B_ADS1292_RESET_LOW_US 1000u', 'ADS1292 复位脉宽过长逼近掉电门限'),
        ('common/bench_release.h', '#define C08B_BLE_DEV_NAME "YUANLI-C08B"', '#define C08B_BLE_DEV_NAME "MAKO-C08B-16"', 'BLE 广播名漂移不匹配上位机'),
        ('common/stream_proto.h', 'cfg[0x0A] = 0x07u;', 'cfg[0x0A] = 0x03u;', 'ADS1292 RESP2 漏写 bit2'),
        ('common/stream_proto.h', 'if (cfg3_step2) *cfg3_step2 = 0xC4u;', 'if (cfg3_step2) *cfg3_step2 = 0xCCu;', 'ADS1298 误置 RLDREF_INT=1 顶牛 AGND'),
        ('common/stream_proto.h', 'if (cfg3_step2) *cfg3_step2 = 0xC4u;', 'if (cfg3_step2) *cfg3_step2 = 0xD4u;', 'ADS1298 误置 RLD_MEAS=1 把 v0.01 Pin62(+2.5V) 灌入内部总线'),
        ('common/stream_proto.h', 'case C08B_MODE_TST1: ch_mux = 0x05u; int_test = true; break;', 'case C08B_MODE_TST1: ch_mux = 0x05u; int_test = (chip_idx == 0); break;', 'ADS1298 TST1 误关 U2 INT_TEST 致 v0.01 CH9..16 失波'),
        ('l432/main.c', 'SET(ADS_RESET, 0);', 'SET(ADS_PWDN, 0); SET(ADS_RESET, 0);', '对 ADS1298 复位时误拉低 ADS_PWDN 放光 VCAP1'),
        ('l432/main.c', 'if (g_sess.id_a != 0x92u)', 'if (1)', '去掉 id_a != 0x92u 守卫无条件拉低 ADS_PWDN'),
        ('nrf/main.c', 'NRF_CLOCK_LF_SRC_RC', 'NRF_CLOCK_LF_SRC_XTAL', '误开 XL1/XL2 外部低频晶振'),
        ('nrf/main.c', 'gpio_in(OE_N_PIN', 'gpio_out(OE_N_PIN, 0); gpio_in(OE_N_PIN', '误把 OE_N 设推挽输出'),
        ('nrf/main.c', 'gpio_out(BENCH_EN_PIN, 0)', 'gpio_out(BENCH_EN_PIN, 1)', '误拉高 BENCH_EN 旁路互锁'),
    ]
    with tempfile.TemporaryDirectory(prefix='c08b-safety-') as td:
        tmp = Path(td)
        for sub in ('common', 'l432', 'nrf'):
            src_d = root / sub
            dst_d = tmp / sub
            dst_d.mkdir(parents=True, exist_ok=True)
            for f in src_d.iterdir():
                if f.is_file():
                    (dst_d / f.name).write_text(f.read_text(encoding='utf-8'), encoding='utf-8')
        assert check_source_safety(tmp) == [], '复制目录基线应通过'
        for rel, old, new, label in mutations:
            target = tmp / rel
            orig = target.read_text(encoding='utf-8')
            assert old in orig, f'{rel} 未找到变异锚点 {old!r}'
            target.write_text(orig.replace(old, new, 1), encoding='utf-8')
            got = check_source_safety(tmp)
            target.write_text(orig, encoding='utf-8')
            if not got:
                raise AssertionError(f'必败反例未报红：{label}')
    print(f'源码安全红线检查通过（基线 0 违规 + {len(mutations)}/{len(mutations)} 项变异反例全红）')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('board', nargs='?', help='.epcb2 或板网表 JSON 路径')
    ap.add_argument('--check-headers', action='store_true', help='只核对已提交的 pins.h 与板网表一致，不改写文件')
    ap.add_argument('--check-jafe', action='store_true', help='核对主控 J_AFE.n <-> D20.(21-n) <-> 2ch J2.(21-n) 全 20 脚跨板物理映射')
    ap.add_argument('--check-u9', action='store_true', help='只读核对旗舰 MCU-U9 (U7/U8/FPC1) <-> AFE-30P (FPC2) 与流式固件兼容')
    ap.add_argument('--check-safety', action='store_true', help='执行源码安全红线扫描')
    ap.add_argument('--self-test', action='store_true', help='对源码安全扫描或 U9 跨板映射执行必败反例自检')
    args = ap.parse_args()

    if args.check_u9:
        default_dual = HERE.parents[1] / 'hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2'
        default_u9 = HERE.parents[1] / 'hardware/16ch-u9-dual30/OpenEMG-C08B-Mainboard-Rev0.01.epro2'
        u9_p = Path(args.board) if args.board else (default_dual if default_dual.is_file() else default_u9)
        afe_p = (u9_p.parent / 'AFE-30P.epro') if (u9_p.parent / 'AFE-30P.epro').is_file() else default_dual
        bad = verify_u9_stream_compat(u9_p, afe_p, selftest=args.self_test)
        if bad:
            for b_msg in bad:
                print('MCU-U9 流式固件兼容核对不过：', b_msg, file=sys.stderr)
            return 1
        st_note = ' + 2/2 项反例（FPC2.17/18 交叉 + 跨代 D20 电源反接混插）拦截通过' if args.self_test else ''
        print(f'MCU-U9 流式固件兼容核对通过：U7(23+3脚, PH3=L_BOOT0)、U8(15脚) 与 FPC1.1..20 <-> AFE-30P FPC2.20..1 完全对齐{st_note}')
        return 0

    if args.check_safety:
        if args.self_test:
            run_safety_selftest(HERE)
        else:
            errs = check_source_safety(HERE)
            if errs:
                for e in errs:
                    print('安全红线不过：', e, file=sys.stderr)
                return 1
            print('源码安全红线检查通过（0 违规）')
        return 0

    geo = Path(args.board) if args.board else default_board_path()
    if args.check_jafe:
        bad = verify_jafe_cross_boards(geo)
        if bad:
            for b in bad:
                print('J_AFE 跨板核对不过：', b, file=sys.stderr)
            return 1
        print('J_AFE 20P 跨板映射核对通过（R4U6 J_AFE.1..20 <-> D20.(20..1) <-> 2ch J2.(20..1) 含 R31->Pin15 复位链路）')
        return 0

    bad = verify_and_emit(geo, write_headers=not args.check_headers, check_headers=args.check_headers)
    if bad:
        for b in bad:
            print('引脚核对不过：', b, file=sys.stderr)
        return 1
    mode_tag = '只读核对一致' if args.check_headers else '生成 l432/pins.h、nrf/pins.h'
    print(f'引脚核对通过（{geo.name}）：U18 {len(L432)} 脚、U13 {len(NRF)} 脚（{mode_tag}）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
