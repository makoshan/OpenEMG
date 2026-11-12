"""ADS1292 / ADS1292R 寄存器表：解码 12 字节寄存器快照、查保留位和禁用编码、解/映射帧状态字。

依据 TI 数据手册 SBAS502C 第 7.5.1.3 节与第 7.6 节（表 13–25）。
特别拦截三类跨芯片移植易错点：
1. 地址差异：0x08 为只读 LOFF_STAT，0x09 为 RESP1，0x0A 为 RESP2，0x0B 为 GPIO（与 ADS1298 不同）；
2. 非 R 版 ADS1292（ID=0x53）：RESP1(0x09) 必须写 0x02，RESP2(0x0A) bit2(RESP_FREQ) 必须写 1（表 24）；
3. CONFIG2(0x02) bit7=1、bit2=0，内部参考为 2.42 V（VREF_4V=0）或 4.033 V（VREF_4V=1，需 AVDD>=4.4 V）。

只读工具：不连设备、不写寄存器。
用法：python ads1292_regs.py --check（只用标准库）
"""
from pathlib import Path
import re
import sys

N_REGS = 0x0C  # 0x00..0x0B
_CH = [('PD', 7, 7), ('GAIN', 6, 4), ('MUX', 3, 0)]

# 地址 → (寄存器名, [(字段名, 高位, 低位)])；未列出的位为固定位或保留位。
REGS = {
    0x00: ('ID', [('DEV_ID', 7, 5), ('CH_ID', 1, 0)]),
    0x01: ('CONFIG1', [('SINGLE_SHOT', 7, 7), ('DR', 2, 0)]),
    0x02: ('CONFIG2', [('PDB_LOFF_COMP', 6, 6), ('PDB_REFBUF', 5, 5), ('VREF_4V', 4, 4),
                       ('CLK_EN', 3, 3), ('INT_TEST', 1, 1), ('TEST_FREQ', 0, 0)]),
    0x03: ('LOFF', [('COMP_TH', 7, 5), ('ILEAD_OFF', 3, 2), ('FLEAD_OFF', 1, 0)]),
    0x04: ('CH1SET', _CH),
    0x05: ('CH2SET', _CH),
    0x06: ('RLD_SENS', [('CHOP', 7, 6), ('PDB_RLD', 5, 5), ('RLD_LOFF_SENS', 4, 4),
                        ('RLD2N', 3, 3), ('RLD2P', 2, 2), ('RLD1N', 1, 1), ('RLD1P', 0, 0)]),
    0x07: ('LOFF_SENS', [('FLIP2', 5, 5), ('FLIP1', 4, 4),
                         ('LOFF2N', 3, 3), ('LOFF2P', 2, 2), ('LOFF1N', 1, 1), ('LOFF1P', 0, 0)]),
    0x08: ('LOFF_STAT', [('CLK_DIV', 6, 6), ('RLD_STAT', 4, 4),
                         ('IN2N_OFF', 3, 3), ('IN2P_OFF', 2, 2), ('IN1N_OFF', 1, 1), ('IN1P_OFF', 0, 0)]),
    0x09: ('RESP1', [('RESP_DEMOD_EN1', 7, 7), ('RESP_MOD_EN', 6, 6), ('RESP_PH', 5, 2), ('RESP_CTRL', 0, 0)]),
    0x0A: ('RESP2', [('CALIB_ON', 7, 7), ('RESP_FREQ', 2, 2), ('RLDREF_INT', 1, 1)]),
    0x0B: ('GPIO', [('GPIOC', 3, 2), ('GPIOD', 1, 0)]),
}

# 可写寄存器的保留位：地址 → (掩码, 必须等于的值)，均依据 SBAS502C「Must be set to」要求。
# 只读寄存器（0x00 ID、0x08 LOFF_STAT）和只读输入位（0x0B GPIO 的 GPIOD[2:1] bit1:0）不查保留掩码。
RESERVED = {
    0x01: (0x78, 0x00),  # CONFIG1 bit6:3 = 0
    0x02: (0x84, 0x80),  # CONFIG2 bit7 = 1，bit2 = 0
    0x03: (0x10, 0x10),  # LOFF bit4 = 1
    0x07: (0xC0, 0x00),  # LOFF_SENS bit7:6 = 0
    0x09: (0x02, 0x02),  # RESP1 bit1 = 1
    0x0A: (0x79, 0x01),  # RESP2 bit6:3 = 0，bit0 = 1
    0x0B: (0xF0, 0x00),  # GPIO bit7:4 = 0
}

GAIN = {0: 6, 1: 1, 2: 2, 3: 3, 4: 4, 5: 8, 6: 12}  # 111 手册禁止使用（Do not use）
DEV_ID_1292 = 0b010   # ADS1291/1292（无呼吸电路）：ID = 0x53（2 通道）
DEV_ID_1292R = 0b011  # ADS1292R（带呼吸解调/调制）：ID = 0x73（2 通道）


def _snapshot(regs):
    regs = bytes(regs)
    if len(regs) != N_REGS:
        raise ValueError(f'寄存器快照应为 {N_REGS} 字节（0x00–0x0B），实际 {len(regs)}')
    return regs


def decode(regs):
    """12 字节快照 → {寄存器名: {字段名: 值}}，另带原始字节 'raw'。"""
    regs = _snapshot(regs)
    out = {}
    for addr, (name, fields) in REGS.items():
        v = regs[addr]
        out[name] = {'raw': v, **{f: (v >> lo) & ((1 << (hi - lo + 1)) - 1) for f, hi, lo in fields}}
    return out


def check(regs):
    """返回问题列表（空 = 合规）。核查芯片 ID、保留位、禁用编码、RLD/导联脱落互斥与非 R 版呼吸位。"""
    regs = _snapshot(regs)
    d = decode(regs)
    bad = []
    if (regs[0x00] & 0xDF) != 0x53:  # 仅接受 0x53(ADS1292) 或 0x73(ADS1292R)
        bad.append(f'ID=0x{regs[0]:02X}：应为 0x53（ADS1292）或 0x73（ADS1292R）')
    for addr, (mask, want) in RESERVED.items():
        if regs[addr] & mask != want:
            bad.append(f'{REGS[addr][0]}=0x{regs[addr]:02X}：保留位（掩码 0x{mask:02X}）应为 0x{want:02X}')
    if d['CONFIG1']['DR'] == 0b111:
        bad.append('CONFIG1.DR=111：手册写 Do not use')
    if d['LOFF']['FLEAD_OFF'] in (0b10, 0b11):
        bad.append(f"LOFF.FLEAD_OFF={d['LOFF']['FLEAD_OFF']:02b}：手册表 17 写 Do not use（仅支持 00=DC 或 01=AC）")
    for ch in (1, 2):
        cs = d[f'CH{ch}SET']
        if cs['GAIN'] == 0b111:
            bad.append(f'CH{ch}SET.GAIN=111：手册写 Do not use')
        if cs['MUX'] > 0b1001 or (ch == 2 and cs['MUX'] == 0b1001):
            bad.append(f"CH{ch}SET.MUX={cs['MUX']:04b}：手册表 18 未定义或仅限 CH1")
    if d['RLD_SENS']['PDB_RLD'] and d['RLD_SENS']['RLD_LOFF_SENS']:
        bad.append('RLD_SENS 同时开启 PDB_RLD 与 RLD_LOFF_SENS：手册表 19 禁止同时使能')
    if ((regs[0x07] & 0x0F) or d['RLD_SENS']['RLD_LOFF_SENS']) and d['LOFF']['FLEAD_OFF'] == 0 and not d['CONFIG2']['PDB_LOFF_COMP']:
        bad.append('开启了 DC 导联脱落检测但 CONFIG2.PDB_LOFF_COMP=0：比较器掉电')
    if d['ID']['DEV_ID'] != DEV_ID_1292R:
        if regs[0x09] != 0x02:
            bad.append(f'RESP1=0x{regs[0x09]:02X}：非 R 版 ADS1292 无呼吸电路，手册要求整字节写 0x02')
        if d['RESP2']['RESP_FREQ'] != 1:
            bad.append(f'RESP2=0x{regs[0x0A]:02X}：手册表 24 要求非 R 版 ADS1291/1292 的 bit2(RESP_FREQ) 必须写 1')
    return bad


def fs_hz(regs, fclk=512e3):
    """CONFIG1 → 采样率（Hz）。片内振荡器标称 fclk=512 kHz（fMOD=fclk/4=128 kHz，DR=000..110 对应 125..8000 SPS）。"""
    c1 = decode(regs)['CONFIG1']
    if c1['DR'] == 0b111:
        raise ValueError('CONFIG1.DR=111 是禁用保留值')
    return (fclk / 4) / (1 << (10 - c1['DR']))


def vref_v(regs):
    """CONFIG2 → 参考电压（V）。外部参考（PDB_REFBUF=0）时返回 None；内部参考为 2.42 V 或 4.033 V（SBAS502C §7.5）。"""
    c2 = decode(regs)['CONFIG2']
    if not c2['PDB_REFBUF']:
        return None
    return 4.033 if c2['VREF_4V'] else 2.42


def gain(regs, ch):
    """通道 ch（从 1 数，1–2）的 PGA 增益。"""
    if type(ch) is not int or not 1 <= ch <= 2:
        raise ValueError(f'ADS1292 通道号从 1 数，应为 1–2，实际 {ch!r}')
    g = decode(regs)[f'CH{ch}SET']['GAIN']
    if g not in GAIN:
        raise ValueError(f'CH{ch}SET.GAIN={g:03b} 手册禁止使用')
    return GAIN[g]


def full_scale_uv(regs, ch):
    """满幅差分输入峰值（µV）：±VREF/增益。"""
    v = vref_v(regs)
    if v is None:
        raise ValueError('外部参考：快照里没有 VREF 值')
    return v * 1e6 / gain(regs, ch)


def uv_per_count(regs, ch):
    """码值 → 输入端 µV：VREF / (2^23 − 1) / 增益（与 host/v12.py AdcProfile 同一公式）。"""
    return full_scale_uv(regs, ch) / (2 ** 23 - 1)


def decode_ads1292_status(b0, b1, b2):
    """解 ADS1292 原生 24 位状态字（SBAS502C §7.5.1.3）。

    原生位序：1100(23:20) | RLD_STAT(19) | IN2N_OFF(18) | IN2P_OFF(17) | IN1N_OFF(16) | IN1P_OFF(15) | GPIO[2:1](14:13) | 13x0(12:0)。
    返回 (rld_stat, loff_statp, loff_statn, gpio)，其中 loff_statp/n bit0=CH1、bit1=CH2。
    """
    w = (b0 << 16) | (b1 << 8) | b2
    if w >> 20 != 0b1100:
        raise ValueError(f'ADS1292 状态字高 4 位应为 1100，实际 {w >> 20:04b}')
    if w & 0x1FFF:
        raise ValueError(f'ADS1292 状态字低 13 位应全为 0，实际 0x{w & 0x1FFF:04X}（疑似 SPI 移位）')
    rld = (w >> 19) & 1
    statp = (((w >> 17) & 1) << 1) | ((w >> 15) & 1)
    statn = (((w >> 18) & 1) << 1) | ((w >> 16) & 1)
    gpio = (w >> 13) & 0x03
    return rld, statp, statn, gpio


def map_f01_status(b0, b1, b2):
    """将 ADS1292 原生 3 字节状态头映射为统一 V12 F01 24 位状态头（对齐 Ads1292::map_f01_status）。"""
    _, statp, statn, gpio = decode_ads1292_status(b0, b1, b2)
    f01 = 0xC00000 | (statp << 12) | (statn << 4) | gpio
    return bytes(((f01 >> 16) & 0xFF, (f01 >> 8) & 0xFF, f01 & 0xFF))


def _table(**set_):
    regs = bytearray(N_REGS)
    regs[0x00] = 0x53  # ADS1292 ID
    for a, v in set_.items():
        regs[int(a[1:], 16)] = v
    return bytes(regs)


def _raises(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def _check_repo_firmware_tables():
    """若同仓存在 c08b-bringup 固件源码，直接提取 CFG1292_TEST 实表核查，防固件与主机规则漂移。"""
    here = Path(__file__).resolve().parent.parent
    candidates = (
        here / 'firmware/c08b-bringup/l432/main.c',
        here / 'v12/c08b-bringup-fw-20261109/l432/main.c',
    )
    for path in candidates:
        if not path.exists():
            continue
        m = re.search(r'CFG1292_TEST\[0x0C\]\s*=\s*\{([^}]+)\}', path.read_text(encoding='utf-8'))
        assert m, f'未在 {path} 找到 CFG1292_TEST'
        regs = bytearray(N_REGS)
        regs[0x00] = 0x53
        for addr_s, val_s in re.findall(r'\[(0x[0-9A-Fa-f]+)\]\s*=\s*(0x[0-9A-Fa-f]+)', m.group(1)):
            regs[int(addr_s, 16)] = int(val_s, 16)
        assert check(regs) == [], f'{path} CFG1292_TEST 违反手册：{check(regs)}'


def _selfcheck():
    import ads1298_regs

    # 阳性：xiao-ads1292-2ch 的五种工作模式（TST1 / SHT1 / EXT1 / EXR1 / RLD1，2 kSPS 与 4 kSPS）
    exr1_2k = _table(r01=0x04, r02=0xA0, r03=0x10, r04=0x00, r05=0x00, r06=0x23, r07=0x00, r09=0x02, r0A=0x07, r0B=0x0C)
    tst1_4k = _table(r01=0x05, r02=0xA3, r03=0x10, r04=0x05, r05=0x05, r06=0x00, r07=0x00, r09=0x02, r0A=0x07, r0B=0x0C)
    sht1_2k = _table(r01=0x04, r02=0xA0, r03=0x10, r04=0x01, r05=0x01, r06=0x00, r07=0x00, r09=0x02, r0A=0x07, r0B=0x0C)
    rld1_2k = _table(r01=0x04, r02=0xA0, r03=0x10, r04=0x00, r05=0x02, r06=0x23, r07=0x00, r09=0x02, r0A=0x07, r0B=0x0C)
    for cfg in (exr1_2k, tst1_4k, sht1_2k, rld1_2k):
        assert check(cfg) == [], check(cfg)
    _check_repo_firmware_tables()

    def one(addr, val, key, base=exr1_2k):
        t = bytearray(base)
        t[addr] = val
        b = check(t)
        assert len(b) == 1 and key in b[0], (hex(addr), hex(val), b)

    # 反例：逐条规则、逐个保留位单独触发（含历史真实缺陷 RESP2=0x03）
    for idv in (0x00, 0xFF, 0x51, 0x71, 0x92, 0x52, 0x43):  # 全0、全1、ADS1291、ADS1298、CH_ID错、bit4=0
        one(0x00, idv, 'ID')
    one(0x01, 0x0C, 'CONFIG1')          # bit3=1
    one(0x01, 0x44, 'CONFIG1')          # bit6=1
    one(0x01, 0x07, 'DR=111')
    one(0x02, 0x20, 'CONFIG2')          # bit7=0
    one(0x02, 0xA4, 'CONFIG2')          # bit2=1
    one(0x03, 0x00, 'LOFF=0x00')        # bit4=0
    one(0x03, 0x12, 'FLEAD_OFF=10')
    one(0x03, 0x13, 'FLEAD_OFF=11')
    one(0x04, 0x70, 'CH1SET.GAIN=111')
    one(0x05, 0x70, 'CH2SET.GAIN=111')
    one(0x04, 0x0A, 'CH1SET.MUX=1010')
    one(0x05, 0x09, 'CH2SET.MUX=1001')  # IN3P/IN3N 路由仅 CH1 支持
    rld_conflict = bytearray(exr1_2k); rld_conflict[0x02] = 0xE0  # 先开比较器，单独测 PDB_RLD 与 RLD_LOFF_SENS 互斥
    one(0x06, 0x30, '禁止同时使能', base=rld_conflict)
    one(0x07, 0x40, 'LOFF_SENS')        # bit6=1
    one(0x07, 0x01, 'PDB_LOFF_COMP=0')  # DC 脱落开了电流源但没开比较器
    one(0x06, 0x10, 'PDB_LOFF_COMP=0')  # RLD_LOFF_SENS 单独开但没开比较器也抓
    r_base = bytearray(exr1_2k); r_base[0x00] = 0x73
    one(0x09, 0x00, '保留位', base=r_base)   # 复位值是 0x00，单独测 bit1=1 保留位
    one(0x09, 0xC2, 'RESP1=0xC2')            # 非 R 版开了呼吸解调/调制位
    one(0x09, 0x03, 'RESP1=0x03')            # 非 R 版开了 RESP_CTRL bit0
    one(0x0A, 0x03, 'RESP2=0x03')       # 历史真实缺陷：c08b-bringup 曾漏写 bit2(RESP_FREQ=1)
    one(0x0A, 0x06, 'RESP2=0x06')       # bit0=0 保留位违规
    one(0x0A, 0x0F, 'RESP2=0x0F')       # bit3=1 保留位违规
    one(0x0B, 0x1C, 'GPIO=0x1C')        # bit4=1 保留位违规

    # ADS1292R（ID=0x73）允许开呼吸位与 RESP_FREQ=0（32 kHz）
    r_ver = bytearray(exr1_2k); r_ver[0x00] = 0x73; r_ver[0x04] = 0x09; r_ver[0x09] = 0xC2; r_ver[0x0A] = 0x03
    assert check(r_ver) == [], check(r_ver)
    # 只读寄存器与只读输入位（LOFF_STAT 0x08、GPIO 低 2 位 GPIOD）怎么变都不误报
    for addr, val in ((0x08, 0x5F), (0x0B, 0x0F), (0x0B, 0x03)):
        t = bytearray(exr1_2k); t[addr] = val
        assert check(t) == [], (hex(addr), hex(val), check(t))
    # 合法的导联脱落配置：DC（开 PDB_LOFF_COMP）与 AC（FLEAD_OFF=01）均合规
    dc_loff = bytearray(exr1_2k); dc_loff[0x02] = 0xE0; dc_loff[0x07] = 0x0F
    ac_loff = bytearray(exr1_2k); ac_loff[0x03] = 0x11; ac_loff[0x07] = 0x0F
    assert check(dc_loff) == [] and check(ac_loff) == []

    # 字段解码逐项核对
    d = decode(_table(r01=0x85, r02=0xF9, r03=0xFD, r04=0x65, r06=0xEB, r07=0x3A, r08=0x55, r09=0xDE, r0A=0x87, r0B=0x0A))
    assert d['ID'] == {'raw': 0x53, 'DEV_ID': 2, 'CH_ID': 3}
    assert d['CONFIG1'] == {'raw': 0x85, 'SINGLE_SHOT': 1, 'DR': 5}
    assert d['CONFIG2'] == {'raw': 0xF9, 'PDB_LOFF_COMP': 1, 'PDB_REFBUF': 1, 'VREF_4V': 1, 'CLK_EN': 1, 'INT_TEST': 0, 'TEST_FREQ': 1}
    assert d['CH1SET'] == {'raw': 0x65, 'PD': 0, 'GAIN': 6, 'MUX': 5}
    assert d['RLD_SENS'] == {'raw': 0xEB, 'CHOP': 3, 'PDB_RLD': 1, 'RLD_LOFF_SENS': 0, 'RLD2N': 1, 'RLD2P': 0, 'RLD1N': 1, 'RLD1P': 1}
    assert d['RESP2'] == {'raw': 0x87, 'CALIB_ON': 1, 'RESP_FREQ': 1, 'RLDREF_INT': 1}
    assert d['GPIO'] == {'raw': 0x0A, 'GPIOC': 2, 'GPIOD': 2}
    assert _raises(check, bytes(11)) and _raises(check, bytes(26))

    # 采样率、基准、增益与 µV 系数
    assert [fs_hz(_table(r01=dr)) for dr in range(7)] == [125, 250, 500, 1000, 2000, 4000, 8000]
    assert _raises(fs_hz, _table(r01=0x07))
    assert vref_v(exr1_2k) == 2.42 and vref_v(_table(r02=0xB0)) == 4.033 and vref_v(_table(r02=0x80)) is None
    assert gain(exr1_2k, 1) == 6 and gain(_table(r05=0x60), 2) == 12
    for ch in (0, 3, -1, 1.0, True):
        assert _raises(gain, exr1_2k, ch), ch
    assert _raises(gain, _table(r04=0x70), 1)
    assert abs(uv_per_count(exr1_2k, 1) - 2.42e6 / (6 * (2 ** 23 - 1))) < 1e-15
    assert round((2 ** 23 - 1) * uv_per_count(exr1_2k, 1)) == 403333
    assert _raises(uv_per_count, _table(r02=0x80), 1)

    # 状态字解码与 F01 映射遍历全部 128 种合法位组合，逐一与 ads1298_regs.decode_ads_status 互逆核对
    for bits in range(128):
        w = 0xC00000 | (bits << 13)
        b0, b1, b2 = (w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF
        rld, sp, sn, gp = decode_ads1292_status(b0, b1, b2)
        assert rld == ((bits >> 6) & 1) and gp == (bits & 0x03)
        mapped = map_f01_status(b0, b1, b2)
        assert ads1298_regs.decode_ads_status(*mapped) == (sp, sn, gp)
    for bad_w in (0x000000, 0x800000, 0xD00000, 0xC00001, 0xC01000):
        assert _raises(decode_ads1292_status, (bad_w >> 16) & 0xFF, (bad_w >> 8) & 0xFF, bad_w & 0xFF)
    print('ads1292_regs --check: OK')


if __name__ == '__main__':
    if sys.argv[1:] != ['--check']:
        print(__doc__)
        sys.exit(2)
    _selfcheck()
