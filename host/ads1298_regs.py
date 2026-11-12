"""ADS1298 寄存器表：解码 26 字节寄存器快照、查保留位和禁用编码、解帧状态字。

依据 TI 数据手册 SBAS459K 第 9.6 节（表 16 及各寄存器字段表）。不抄 TI 评估固件 1.1.1 的写入掩码：
它按旧版手册写，会清掉 WCT_CHOP、RLD_LOFF_SENS、WCT_TO_RLD，RESP bit5 写 0
 F4）。

只读工具：不连设备、不写寄存器。计划 S1。
用法：python ads1298_regs.py --check（只用标准库）
"""
import sys

N_REGS = 0x1A  # 0x00..0x19
_CH = [('PD', 7, 7), ('GAIN', 6, 4), ('MUX', 2, 0)]
_BYTE = [('BITS', 7, 0)]

# 地址 → (寄存器名, [(字段名, 高位, 低位)])；没列出的位是固定位或保留位。下面的函数一律经 decode() 取字段。
REGS = {
    0x00: ('ID', [('DEV_ID', 7, 5), ('CH_ID', 2, 0)]),
    0x01: ('CONFIG1', [('HR', 7, 7), ('DAISY_EN', 6, 6), ('CLK_EN', 5, 5), ('DR', 2, 0)]),
    0x02: ('CONFIG2', [('WCT_CHOP', 5, 5), ('INT_TEST', 4, 4), ('TEST_AMP', 2, 2), ('TEST_FREQ', 1, 0)]),
    0x03: ('CONFIG3', [('PD_REFBUF', 7, 7), ('VREF_4V', 5, 5), ('RLD_MEAS', 4, 4), ('RLDREF_INT', 3, 3),
                       ('PD_RLD', 2, 2), ('RLD_LOFF_SENS', 1, 1), ('RLD_STAT', 0, 0)]),
    0x04: ('LOFF', [('COMP_TH', 7, 5), ('VLEAD_OFF_EN', 4, 4), ('ILEAD_OFF', 3, 2), ('FLEAD_OFF', 1, 0)]),
    **{0x05 + i: (f'CH{i + 1}SET', _CH) for i in range(8)},
    0x0D: ('RLD_SENSP', _BYTE), 0x0E: ('RLD_SENSN', _BYTE),
    0x0F: ('LOFF_SENSP', _BYTE), 0x10: ('LOFF_SENSN', _BYTE), 0x11: ('LOFF_FLIP', _BYTE),
    0x12: ('LOFF_STATP', _BYTE), 0x13: ('LOFF_STATN', _BYTE),
    0x14: ('GPIO', [('GPIOD', 7, 4), ('GPIOC', 3, 0)]),
    0x15: ('PACE', [('PACEE', 4, 3), ('PACEO', 2, 1), ('PD_PACE', 0, 0)]),
    0x16: ('RESP', [('RESP_DEMOD_EN1', 7, 7), ('RESP_MOD_EN1', 6, 6), ('RESP_PH', 4, 2), ('RESP_CTRL', 1, 0)]),
    0x17: ('CONFIG4', [('RESP_FREQ', 7, 5), ('SINGLE_SHOT', 3, 3), ('WCT_TO_RLD', 2, 2), ('PD_LOFF_COMP', 1, 1)]),
    0x18: ('WCT1', [('aVF_CH6', 7, 7), ('aVL_CH5', 6, 6), ('aVR_CH7', 5, 5), ('aVR_CH4', 4, 4),
                    ('PD_WCTA', 3, 3), ('WCTA', 2, 0)]),
    0x19: ('WCT2', [('PD_WCTC', 7, 7), ('PD_WCTB', 6, 6), ('WCTB', 5, 3), ('WCTC', 2, 0)]),
}

# 可写寄存器的保留位：地址 → (掩码, 必须等于的值)，都是手册写「Always write」的位。
# 只读寄存器（ID、LOFF_STATP/N）和只读位（CONFIG3 的 RLD_STAT、GPIO 的输入电平 GPIOD）不查。
RESERVED = {
    0x01: (0x18, 0x00),                     # bit4:3 = 0
    0x02: (0xC8, 0x00),                     # bit7:6 = 0（复位值是 1，手册要求写 0），bit3 = 0
    0x03: (0x40, 0x40),                     # bit6 = 1
    **{0x05 + i: (0x08, 0x00) for i in range(8)},  # CHnSET bit3 = 0
    0x15: (0xE0, 0x00),                     # PACE bit7:5 = 0
    0x16: (0x20, 0x20),                     # RESP bit5 = 1（手册原文 Always write 1h；TI 1.1.1 固件写的是 0）
    0x17: (0x11, 0x00),                     # CONFIG4 bit4 = 0，bit0 = 0
}

GAIN = {0: 6, 1: 1, 2: 2, 3: 3, 4: 4, 5: 8, 6: 12}  # 111 手册没定义
DEV_ID_R = 0b110  # ID bit7:5：100 = ADS129x，110 = ADS129xR（带呼吸电路）


def _snapshot(regs):
    regs = bytes(regs)
    if len(regs) != N_REGS:
        raise ValueError(f'寄存器快照应为 {N_REGS} 字节（0x00–0x19），实际 {len(regs)}')
    return regs


def decode(regs):
    """26 字节快照 → {寄存器名: {字段名: 值}}，另带原始字节 'raw'。"""
    regs = _snapshot(regs)
    out = {}
    for addr, (name, fields) in REGS.items():
        v = regs[addr]
        out[name] = {'raw': v, **{f: (v >> lo) & ((1 << (hi - lo + 1)) - 1) for f, hi, lo in fields}}
    return out


def check(regs):
    """返回问题列表（空 = 没问题）。查：ID 是不是 8 通道 ADS129x、保留位、手册写明不许用的编码、导联配置自洽。"""
    regs = _snapshot(regs)
    d = decode(regs)
    bad = []
    if regs[0x00] & 0x1F != 0x12:            # bit4=1、bit3=0、CH_ID=010（8 通道）；与固件 &0x3F==0x12 的低 5 位一致
        bad.append(f'ID=0x{regs[0]:02X}：低 5 位应为 0x12（8 通道 ADS129x），全 0/全 1 多半是 SPI 没读到')
    for addr, (mask, want) in RESERVED.items():
        if regs[addr] & mask != want:
            bad.append(f'{REGS[addr][0]}=0x{regs[addr]:02X}：保留位（掩码 0x{mask:02X}）应为 0x{want:02X}')
    if d['CONFIG1']['DR'] == 0b111:
        bad.append('CONFIG1.DR=111：手册写 Reserved (do not use)')
    if d['CONFIG2']['TEST_FREQ'] == 0b10:
        bad.append('CONFIG2.TEST_FREQ=10：手册写 Not used')
    for i in range(8):
        if d[f'CH{i + 1}SET']['GAIN'] == 0b111:
            bad.append(f'CH{i + 1}SET.GAIN=111：手册没定义')
    flead = d['LOFF']['FLEAD_OFF']
    if flead == 0b10:
        bad.append('LOFF.FLEAD_OFF=10：手册写 Do not use')
    if (regs[0x0F] or regs[0x10]) and flead == 0b00:
        bad.append('LOFF_SENSP/N 有位打开但 FLEAD_OFF=00：手册要求此时设 01 或 11')
    if regs[0x16] & 0xC0 and d['ID']['DEV_ID'] != DEV_ID_R:
        bad.append('RESP bit7:6 非 0：只有 ADS129xR 有呼吸电路，非 R 版手册要求写 0')
    return bad


def fs_hz(regs, fclk=2.048e6):
    """CONFIG1 → 采样率。fclk 是 ADS 主时钟（片内振荡器名义 2.048 MHz，精度见手册电气特性表）。"""
    c1 = decode(regs)['CONFIG1']
    if c1['DR'] == 0b111:
        raise ValueError('CONFIG1.DR=111 是保留值')
    return fclk / (4 if c1['HR'] else 8) / (16 << c1['DR'])  # fMOD = fCLK/4（HR）或 /8（LP），数据率 = fMOD/16/2^DR


def vref_v(regs):
    """CONFIG3 → 参考电压。外部参考（PD_REFBUF=0）时快照里没有电压值，返回 None，不猜。"""
    c3 = decode(regs)['CONFIG3']
    if not c3['PD_REFBUF']:
        return None
    return 4.0 if c3['VREF_4V'] else 2.4


def gain(regs, ch):
    """通道 ch（从 1 数，1–8）的 PGA 增益。"""
    if type(ch) is not int or not 1 <= ch <= 8:
        raise ValueError(f'通道号从 1 数，应为 1–8，实际 {ch!r}')
    g = decode(regs)[f'CH{ch}SET']['GAIN']
    if g not in GAIN:
        raise ValueError(f'CH{ch}SET.GAIN={g:03b} 手册没定义')
    return GAIN[g]


def full_scale_uv(regs, ch):
    """满幅正弦的峰值，折算到输入端（µV）：±VREF/增益。只认每路 24 位的档位。"""
    c1 = decode(regs)['CONFIG1']
    if c1['HR'] and c1['DR'] == 0:
        raise ValueError('HR 模式 DR=000（32 kSPS）每路只有 16 位（手册 9.4.1.3），本工具按 24 位换算，不支持')
    v = vref_v(regs)
    if v is None:
        raise ValueError('外部参考：快照里没有 VREF 值')
    return v * 1e6 / gain(regs, ch)


def uv_per_count(regs, ch):
    """码值 → 输入端 µV：VREF / (2^23 − 1) / 增益（与 host/v12.py AdcProfile 同一公式）。"""
    return full_scale_uv(regs, ch) / (2 ** 23 - 1)


def decode_ads_status(b0, b1, b2):
    """帧头 3 字节状态字 → (LOFF_STATP, LOFF_STATN, GPIO 高 4 位)。

    布局（手册 9.4.1.3.1）：1100 + LOFF_STATP[7:0] + LOFF_STATN[7:0] + GPIO[7:4]。
    LOFF_STATP/N 的位 n-1 = 1 表示 INnP/INnN 电极脱落。
    名字故意不叫 decode_status：host/v12_status.py 已有同名函数（解 F05 状态特征）。
    """
    w = (b0 << 16) | (b1 << 8) | b2
    if w >> 20 != 0b1100:
        raise ValueError(f'状态字高 4 位应为 1100，实际 {w >> 20:04b}（全零读或错位）')
    return (w >> 12) & 0xFF, (w >> 4) & 0xFF, w & 0x0F


def _table(**set_):
    regs = bytearray(N_REGS)
    regs[0x00] = 0x92                       # ADS1298 的 ID
    for a, v in set_.items():
        regs[int(a[1:], 16)] = v
    return bytes(regs)


def _raises(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def _selfcheck():
    # 阳性：C08D V4 的 EXR1、ch_mask=0xFF，RLD 打开后的整表（v12/c08d-v4-firmware-20261101/src/ads1298.cpp:34-51）
    v4 = bytearray(_table(r01=0x84, r03=0xE4, r14=0x0F, r16=0x20, r0D=0xFF, r0E=0xFF))
    assert check(v4) == [], check(v4)
    # 阳性：R01 dual 的 SHT1（CHnSET=0x01、CONFIG3=0xE0），未用通道 0x81
    r01 = bytearray(_table(r01=0x84, r03=0xE0, r14=0x0F, r16=0x20))
    r01[0x05:0x0D] = bytes([0x01] + [0x81] * 7)
    assert check(r01) == [], check(r01)
    # TI 评估固件 1.1.1 上电表（dc_conf.h）：只有 RESP bit5 违反现行手册
    ti = _table(r01=0x86, r02=0x10, r03=0xDC, r04=0x03, r0F=0xFF, r10=0x02, r14=0x00, r16=0x00,
                r17=0x02, r18=0x0A, r19=0xE3, **{f'r{0x05 + i:02X}': 0x01 for i in range(8)})
    bad = check(ti)
    assert len(bad) == 1 and bad[0].startswith('RESP=0x00'), bad

    def one(addr, val, key, base=v4):
        t = bytearray(base); t[addr] = val
        b = check(t)
        assert len(b) == 1 and key in b[0], (hex(addr), hex(val), b)
    # 反例：每条规则、每个保留位单独触发一次
    for idv in (0x00, 0xFF, 0x93, 0x82):   # 全 0、全 1、CH_ID=011、bit4=0
        one(0x00, idv, 'ID')
    one(0x01, 0x8C, 'CONFIG1')              # bit3
    one(0x01, 0x94, 'CONFIG1')              # bit4
    one(0x01, 0x87, 'DR=111')
    one(0x02, 0x40, 'CONFIG2')              # 复位值就是 0x40，但手册要求 bit7:6 写 0h
    one(0x02, 0x80, 'CONFIG2')              # bit7
    one(0x02, 0x08, 'CONFIG2')              # bit3
    one(0x02, 0x12, 'TEST_FREQ=10')
    one(0x03, 0xA4, 'CONFIG3')              # bit6 = 0
    one(0x05, 0x08, 'CH1SET=0x08')
    one(0x0C, 0x08, 'CH8SET=0x08')
    one(0x05, 0x70, 'GAIN=111')
    one(0x04, 0x02, 'FLEAD_OFF=10')
    one(0x0F, 0x01, 'FLEAD_OFF=00')
    one(0x10, 0x01, 'FLEAD_OFF=00')         # 只开 N 端也算
    one(0x15, 0x20, 'PACE')
    one(0x16, 0x00, 'RESP=0x00')
    one(0x16, 0xA0, 'RESP bit7:6')
    one(0x16, 0x60, 'RESP bit7:6')          # bit6 单独
    one(0x17, 0x10, 'CONFIG4')
    one(0x17, 0x01, 'CONFIG4')
    # ADS1298R（ID 0xD2）的呼吸位是合法的
    r = bytearray(v4); r[0x00] = 0xD2; r[0x16] = 0xE0
    assert check(r) == [], check(r)
    # 只读位不查：RLD_STAT、GPIO 输入电平、LOFF_STATP/N 怎么变都不报
    for addr, val in ((0x03, 0xE5), (0x14, 0xFF), (0x12, 0xFF), (0x13, 0x5A)):
        t = bytearray(v4); t[addr] = val
        assert check(t) == [], (hex(addr), check(t))
    # 合法的导联配置：直流（LOFF=0x03）和交流（LOFF=0x01，FLEAD=01）都不报
    for loff in (0x03, 0x01):
        lof = bytearray(v4); lof[0x04] = loff; lof[0x0F] = lof[0x10] = 0x01; lof[0x17] = 0x02
        assert check(lof) == [], (hex(loff), check(lof))
    # decode 字段表逐个核
    d = decode(_table(r03=0xE4, r04=0x03, r05=0x65, r14=0xA5, r15=0x1F, r16=0x2E, r17=0x0A, r18=0x5A, r19=0xE3))
    assert d['ID'] == {'raw': 0x92, 'DEV_ID': 4, 'CH_ID': 2}
    assert d['CONFIG3'] == {'raw': 0xE4, 'PD_REFBUF': 1, 'VREF_4V': 1, 'RLD_MEAS': 0, 'RLDREF_INT': 0,
                            'PD_RLD': 1, 'RLD_LOFF_SENS': 0, 'RLD_STAT': 0}
    assert d['LOFF'] == {'raw': 0x03, 'COMP_TH': 0, 'VLEAD_OFF_EN': 0, 'ILEAD_OFF': 0, 'FLEAD_OFF': 3}
    assert d['CH1SET'] == {'raw': 0x65, 'PD': 0, 'GAIN': 6, 'MUX': 5}
    assert d['GPIO'] == {'raw': 0xA5, 'GPIOD': 0xA, 'GPIOC': 5}
    assert d['PACE'] == {'raw': 0x1F, 'PACEE': 3, 'PACEO': 3, 'PD_PACE': 1}
    assert d['RESP'] == {'raw': 0x2E, 'RESP_DEMOD_EN1': 0, 'RESP_MOD_EN1': 0, 'RESP_PH': 3, 'RESP_CTRL': 2}
    assert d['CONFIG4'] == {'raw': 0x0A, 'RESP_FREQ': 0, 'SINGLE_SHOT': 1, 'WCT_TO_RLD': 0, 'PD_LOFF_COMP': 1}
    assert d['WCT1'] == {'raw': 0x5A, 'aVF_CH6': 0, 'aVL_CH5': 1, 'aVR_CH7': 0, 'aVR_CH4': 1, 'PD_WCTA': 1, 'WCTA': 2}
    assert d['WCT2'] == {'raw': 0xE3, 'PD_WCTC': 1, 'PD_WCTB': 1, 'WCTB': 4, 'WCTC': 3}
    assert _raises(check, bytes(25))
    # 采样率、参考、增益、换算
    assert fs_hz(v4) == 2000 and fs_hz(_table(r01=0x83, r03=0xE0)) == 4000 and fs_hz(ti) == 500
    assert fs_hz(_table(r01=0x80, r03=0xE0)) == 32000 and fs_hz(_table(r01=0x06, r03=0xE0)) == 250  # LP 模式
    assert _raises(fs_hz, _table(r01=0x87))
    assert vref_v(v4) == 4.0 and vref_v(_table(r03=0xC0)) == 2.4 and vref_v(_table(r03=0x40)) is None
    assert gain(v4, 1) == 6 and gain(_table(r05=0x10, r03=0xE0), 1) == 1 and gain(_table(r0C=0x60), 8) == 12
    for ch in (0, 9, -1, 1.0, True):
        assert _raises(gain, v4, ch), ch
    assert _raises(gain, _table(r05=0x70), 1)
    assert abs(uv_per_count(v4, 1) - 4e6 / (6 * (2 ** 23 - 1))) < 1e-15   # 与 host/v12.py:44 同式
    assert full_scale_uv(v4, 1) == 4e6 / 6 and abs(full_scale_uv(_table(r03=0xC0), 1) - 2.4e6 / 6) < 1e-6
    assert _raises(full_scale_uv, _table(r01=0x80, r03=0xE0), 1)   # 32 kSPS 每路 16 位
    assert full_scale_uv(_table(r01=0x00, r03=0xE0), 1) == 4e6 / 6  # LP 16 kSPS 仍是 24 位
    assert _raises(uv_per_count, _table(r03=0x40), 1)                # 外部参考
    # 状态字：位置逐个核（手册 1100 + STATP + STATN + GPIO[7:4]）
    assert decode_ads_status(0xC0, 0x00, 0x00) == (0, 0, 0)
    assert decode_ads_status(0xC0, 0x10, 0x00) == (0x01, 0, 0)       # IN1P 脱落
    assert decode_ads_status(0xC8, 0x00, 0x00) == (0x80, 0, 0)       # IN8P 脱落
    assert decode_ads_status(0xC0, 0x00, 0x10) == (0, 0x01, 0)       # IN1N 脱落
    assert decode_ads_status(0xC0, 0x08, 0x00) == (0, 0x80, 0)       # IN8N 脱落
    assert decode_ads_status(0xC0, 0x00, 0x0F) == (0, 0, 0x0F)       # GPIO
    for b0 in (0x00, 0x80, 0xD0, 0xFF):
        assert _raises(decode_ads_status, b0, 0, 0), hex(b0)
    print('ads1298_regs --check: OK')


if __name__ == '__main__':
    if sys.argv[1:] != ['--check']:
        print(__doc__); sys.exit(2)
    _selfcheck()
