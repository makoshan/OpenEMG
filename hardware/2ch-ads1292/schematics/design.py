# coding: utf-8
"""ADS1292 双通道六触点验证版电气真源：parts → KiCad 工程（ERC）+ 网表逐脚核对 + BOM。
6 个触点照 C08B 盒底：两排「大—辅—大」，每排两端是一路的正负，中间小点是 RLD；电极焊在 PCB 底面，和板是一体。
主控走 P44e：XIAO 焊在 0.8 mm 转接板上，经 20P 排线接本板 J2（Mako 11-05 定改排线，11-06 定改薄并引出 5V）。
串阻是候选，等 R01 对比。外围按 TI SBAS502C 图 40、图 73 与 ADS1x9xECG-FE 评估板。"""
import csv, json, sys
from pathlib import Path
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import kisch

NAME = 'ads1292-2ch'
M1, K100, K47, K4, R33, R0 = 'C26083', 'C25741', 'C25792', 'C25900', 'C25105', 'C17168'
K10 = 'C25744'   # 0402 10k，基础库（11-12 查）
M1S, K300S, K620S = 'C22935', 'C23024', 'C23219'   # 电极侧第一颗先吃静电，用 0603（75 V）
# P44e J1 逐脚（v12/ads1292-p44e-xiao-adapter-20261106/pin-table.csv）：(P44e 网名, 本板网名)
P44D = {1: ('3V3', '3V3'), 2: ('3V3', '3V3'), 3: ('-', 'NC'), 4: ('DRDY_A', 'ADS_DRDY_N'), 5: ('-', 'NC'), 6: ('MISO', 'ADS_DOUT'),
        7: ('GND', 'GND'), 8: ('GND', 'GND'), 9: ('GND', 'GND'), 10: ('SCLK', 'MCU_SCLK'), 11: ('CS_A', 'ADS_CS_N'), 12: ('START', 'ADS_START'),
        13: ('-', 'NC'), 14: ('-', 'NC'), 15: ('PWDN_N', 'MCU_PWDN'), 16: ('MOSI', 'ADS_DIN'), 17: ('-', 'NC'), 18: ('DRDY_B', 'AVDD_SENSE'),
        19: ('5V', 'XIAO_5V'), 20: ('GND', 'GND')}
# 排线从 J1 南口出，拱过 J2，回折插 J2 南口。折线平行 X 轴，导体 X 不变；两座开口同朝南，J2 在顶面、J1 在背面，所以 J2 第 n 脚对 J1 第 21−n 脚。check_board.py 按两板焊盘坐标核，改走向要重核
J2PINS = {f'{n}:{P44D[21 - n][0]}': P44D[21 - n][1] for n in range(1, 21)} | {'21:SH1': 'GND', '22:SH2': 'GND'}
N100, U1, U10, N47, N15 = 'C1525', 'C52923', 'C19702', 'C1538', 'C23967'
U10S = 'C15525'   # 0402 10µF 6.3V X5R，基础库：手册 §11.1.1.1 每个电源 10µF + 0.1µF（11-11 功能复核）
ESD = 'C43177583'
def R(v, a, b, c, dnp=False, fp='R0402'): return dict(value=v, fp=fp, lcsc=c, dnp=dnp, pins={'1': a, '2': b})
def RS(v, a, b, c, dnp=False): return R(v, a, b, c, dnp, 'R0603')
def C(v, a, b, c, dnp=False, fp='C0402'): return dict(value=v, fp=fp, lcsc=c, dnp=dnp, pins={'1': a, '2': b})
def D(a, dnp=False): return dict(value='ESD501DPYRQ1', fp='X1SON-2_0.6x1', lcsc=ESD, dnp=dnp, pins={'1': a, '2': 'GND'})
def E(v, a, dnp=False, fp='ELECTRODE_PAD'): return dict(value=v, fp=fp, lcsc=None, dnp=dnp, pins={'1': a})
def T(a): return dict(value=a, fp='TP_1.0', lcsc=None, dnp=False, pins={'1': a})

parts = {
 # 电极是 PCB 底面的一部分。北排 E1 CH1+、E3 RLD、E2 CH1−；南排 E4 CH2+、E6 RLD、E5 CH2−（Mako 11-10 定照 C08B 盒底）
 'E1': E('CH1+', 'E1_CH1P'), 'E2': E('CH1-', 'E2_CH1N'), 'E3': E('RLD', 'E3_RLD', fp='ELECTRODE_PAD_AUX'),
 'E4': E('CH2+', 'E4_CH2P'), 'E5': E('CH2-', 'E5_CH2N'), 'E6': E('RLD', 'E6_RLD', fp='ELECTRODE_PAD_AUX'),
 # 每腿：电极 → 1M → ESD → 1M → ADS。ESD 短路时电极仍隔 1M；第一颗贴着电极放
 'R1': RS('1M', 'E1_CH1P', 'N1P', M1S), 'D1': D('N1P'), 'R2': R('1M', 'N1P', 'IN1P', M1),
 'R3': RS('1M', 'E2_CH1N', 'N1N', M1S), 'D2': D('N1N'), 'R4': R('1M', 'N1N', 'IN1N', M1),
 'R5': RS('1M', 'E4_CH2P', 'N2P', M1S), 'D4': D('N2P'), 'R6': R('1M', 'N2P', 'IN2P', M1),
 'R7': RS('1M', 'E5_CH2N', 'N2N', M1S), 'D5': D('N2N'), 'R8': R('1M', 'N2N', 'IN2N', M1),
  # RLD：RLDOUT → 300k → ESD → 两路各 620k → 两个辅点。两点都贴上时合计 610k，5.5 V 口径 9.0 µA；只贴一点 920k；反馈 1M∥1.5nF（手册图 40）；29 脚经 100k 接 RLDOUT（TI 评估板），CH2 可测 RLD
 'R13': RS('300k', 'RLDOUT', 'NRLD', K300S), 'D3': D('NRLD'), 'R14': RS('620k', 'NRLD', 'E3_RLD', K620S), 'R16': RS('620k', 'NRLD', 'E6_RLD', K620S),
 'R15': R('1M', 'RLDOUT', 'RLDINV', M1), 'C3': C('1.5nF', 'RLDOUT', 'RLDINV', N15), 'R27': R('100k', 'RLDOUT', 'ADS_RLDIN', K100),
 'U1': dict(value='ADS1292IPBSR', fp='Package_QFP:TQFP-32_5x5mm_P0.5mm', lcsc='C2651570', dnp=False, pins={
  '1:PGA1N': 'PGA1N', '2:PGA1P': 'PGA1P', '3:IN1N': 'IN1N', '4:IN1P': 'IN1P', '5:IN2N': 'IN2N', '6:IN2P': 'IN2P',
  '7:PGA2N': 'PGA2N', '8:PGA2P': 'PGA2P', '9:VREFP': 'VREFP', '10:VREFN': 'GND', '11:VCAP1': 'VCAP1', '12:AVDD': 'AVDD',
  '13:AVSS': 'GND', '14:CLKSEL': 'DVDD', '15:PWDN/RESET': 'ADS_RESET_N', '16:START': 'ADS_START', '17:CLK': 'ADS_CLK',
  '18:CS': 'ADS_CS_N', '19:DIN': 'ADS_DIN', '20:SCLK': 'ADS_SCLK', '21:DOUT': 'ADS_DOUT', '22:DRDY': 'ADS_DRDY_N',
  '23:DVDD': 'DVDD', '24:DGND': 'GND', '25:GPIO2': 'ADS_GPIO2', '26:GPIO1': 'ADS_GPIO1', '27:VCAP2': 'VCAP2',
  '28:RLDINV': 'RLDINV', '29:RLDIN/RLDREF': 'ADS_RLDIN', '30:RLDOUT': 'RLDOUT', '31:IN3P': 'AVDD', '32:IN3N': 'AVDD'}),
 'C4': C('4.7nF', 'PGA1P', 'PGA1N', N47), 'C5': C('4.7nF', 'PGA2P', 'PGA2N', N47),
 'C6': C('100nF', 'VREFP', 'GND', N100), 'C7': C('10uF', 'VREFP', 'GND', U10, fp='C0603'),
 'C8': C('1uF', 'VCAP1', 'GND', U1), 'C9': C('1uF', 'VCAP2', 'GND', U1),
 'C10': C('100nF', 'AVDD', 'GND', N100), 'C11': C('10uF', 'AVDD', 'GND', U10S),
 'C12': C('100nF', 'DVDD', 'GND', N100), 'C13': C('10uF', 'DVDD', 'GND', U10S),
 'L1': dict(value='BLM18PG121SN1D', fp='L0603', lcsc='C14709', dnp=False, pins={'1': '3V3', '2': 'DVDD'}),
 # 上电前数字输入要低（手册 10.1）。P44e 已有 PWDN_N、START 10k 下拉，CS_A 10k 上拉（CS 不能再下拉）；这里补其余
 'R18': R('47k', 'ADS_SCLK', 'GND', K47),
 'R19': R('47k', 'ADS_DIN', 'GND', K47), 'R20': R('47k', 'ADS_CLK', 'GND', K47),
 'R21': R('47k', 'ADS_GPIO1', 'GND', K47), 'R22': R('47k', 'ADS_GPIO2', 'GND', K47),
 'R23': R('33R', 'ADS_SCLK', 'MCU_SCLK', R33),
 # 转接板的 RESET_N 是上拉，不能当 ADS 默认低；PWDN/RESET 接 PWDN_N（D4），串 4.7k：Q1 能压过 MCU
 'R31': R('4.7k', 'MCU_PWDN', 'ADS_RESET_N', K4),
 'J2': dict(value='FH34SRJ-20S-0.5SH(50)', fp='FH34SRJ-20S', lcsc='C2802370', dnp=False, pins=J2PINS),
 'C16': C('10uF', '3V3', 'GND', U10, fp='C0603'),
 # AVDD 3.0 V 专用 LDO，常开：切 AVDD 而 DVDD 还在，AVDD−DVDD≈−3.3 V，超手册下限 −2.1 V
 'U3': dict(value='TPS7A2030PDBVR', fp='SOT-23-5', lcsc='C963429', dnp=False, pins={'1:IN': '3V3', '2:GND': 'GND', '3:EN': '3V3', '4:NC': 'NC', '5:OUT': 'AVDD'}),
 'C14': C('1uF', '3V3', 'GND', U1), 'C15': C('1uF', 'AVDD', 'GND', U1),
 # USB 互锁：XIAO 5V 经 P44e J1 19 脚到 J2，插 USB 时 Q1 把 ADS 拉进硬掉电。R32 默认贴；台架要插 USB 读 ADS 时拆掉 R32
 'R32': R('0R', 'XIAO_5V', 'ILK_VBUS', R0),
 'Q1': dict(value='AO3400A', fp='SOT-23', lcsc='C20917', dnp=False, pins={'1:G': 'ILK_VBUS', '2:S': 'GND', '3:D': 'ADS_RESET_N'}),
 # R25 用 10k（Mako 11-12 定，原 100k）：XIAO 的 VBUS 经二极管接内部电源、自带 100k 下拉，电池态二极管漏电会抬高栅极；
 # 100k 时约 13 µA 就到 AO3400A 最小门限 0.65 V，Q1 会把 ADS 压在复位；10k 时要约 70 µA。插 USB 时多耗 0.5 mA
 'R25': R('10k', 'ILK_VBUS', 'GND', K10), 'R26': R('100k', 'AVDD', 'AVDD_SENSE', K100),
 # Mako 11-05 定留 4 个测试点：VREFP、DRDY、SCLK、ILK_VBUS 改量 C7、J2 17 脚、R18、R25 的焊盘
 'TP1': T('AVDD'), 'TP2': T('3V3'), 'TP3': T('GND'), 'TP8': T('ADS_RESET_N'),
}

def check_p44d(pins):
    """J2 对 P44e 的 pin-table（独立来源）逐脚核：page1 的标签由本文件生成，几何比对查不出这里接错。"""
    want = {'3V3': '3V3', 'GND': 'GND', 'DRDY_A': 'ADS_DRDY_N', 'MISO': 'ADS_DOUT', 'SCLK': 'MCU_SCLK', 'CS_A': 'ADS_CS_N', 'START': 'ADS_START',
            'PWDN_N': 'MCU_PWDN', 'MOSI': 'ADS_DIN', 'DRDY_B': 'AVDD_SENSE', '5V': 'XIAO_5V', '': 'NC'}
    t = {int(r['adapter_pin']): r['adapter_net'] for r in csv.DictReader(open(P.parents[1] / 'common-mainboard/adapter-p44e-xiao/pin-table.csv'))}
    bad = [k for k, net in pins.items() if int(k.split(':')[0]) <= 20 and want[t[21 - int(k.split(':')[0])]] != net]
    print('J2 对 P44e pin-table：' + ('通过' if not bad else f'不符 {bad}'))
    return not bad


# 封装写真实库名，板上和原理图才对得上；安装孔也进真源
FPID = {'R0402': 'Resistor_SMD:R_0402_1005Metric', 'R0603': 'Resistor_SMD:R_0603_1608Metric', 'C0402': 'Capacitor_SMD:C_0402_1005Metric',
        'C0603': 'Capacitor_SMD:C_0603_1608Metric', 'L0603': 'Inductor_SMD:L_0603_1608Metric', 'X1SON-2_0.6x1': 'Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm',
        'ELECTRODE_PAD': 'ads:ELECTRODE_PAD', 'ELECTRODE_PAD_AUX': 'ads:ELECTRODE_PAD_AUX', 'FH34SRJ-20S': 'p44:Hirose_FH34SRJ-20S-0.5SH', 'TP_1.0': 'TestPoint:TestPoint_Pad_D1.0mm', 'SOT-23-5': 'Package_TO_SOT_SMD:SOT-23-5', 'SOT-23': 'Package_TO_SOT_SMD:SOT-23'}
for p in parts.values(): p['fp'] = FPID.get(p['fp'], p['fp'])
for i in (1, 2, 3, 4): parts[f'H{i}'] = dict(value='HOLE', fp='ads:HOLE_1P7', lcsc=None, dnp=False, pins={})
# MARK：顶面三点；底面没有贴片件，不放
for i in range(1, 4): parts[f'FID{i}'] = dict(value='MARK', fp='Fiducial:Fiducial_1mm_Mask2mm', lcsc=None, dnp=False, pins={})

if __name__ == '__main__':
    kisch.write(P, NAME, parts, {'sources': {'ADS1292': 'TI SBAS502C 2020-04 图 40、图 73、10.1', 'EVM': 'TI SLAU384A 第 51 页'}}, cols=20, row_pitch=96.52, paper='A0')
    ok = kisch.check(P / 'design.json', P / f'{NAME}.net.xml') and check_p44d(parts['J2']['pins'])
    # 原理图上写明 DNP 和不进 BOM，板子的标志才对得上；kisch 只出默认值
    import re
    sp = P / f'{NAME}.kicad_sch'; t = sp.read_text(encoding='utf-8'); out = []; n = 0
    for blk in re.split(r'(?=\(symbol \(lib_id )', t):
        m = re.search(r'\(property "Reference" "([A-Z]+\d+)"', blk)
        if m and m.group(1) in parts:
            r = m.group(1)
            if parts[r].get('dnp'): blk, c = re.subn(r'\(dnp no\)', '(dnp yes)', blk, count=1); n += c
            if r[0] in 'HF' or r[:2] == 'TP': blk, c = re.subn(r'\(in_bom yes\)', '(in_bom no)', blk, count=1); n += c
        out.append(blk)
    sp.write_text(''.join(out), encoding='utf-8'); print('原理图标志', n)
    with open(P / 'bom-candidate.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['位号', '值', '封装', 'LCSC', '首版'])
        for r, p in parts.items(): w.writerow([r, p['value'], p['fp'], p.get('lcsc') or '', '不贴' if p['dnp'] else '贴'])
    fit = [r for r, p in parts.items() if not p['dnp']]
    print('器件', len(parts), '首版贴', len(fit), '不贴', len(parts) - len(fit), '料种', len({p['lcsc'] for p in parts.values() if p['lcsc']}))
    sys.exit(0 if ok else 1)
