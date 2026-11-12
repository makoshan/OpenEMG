"""从已冻结的 V12 快照派生离体候选；不改原设计，不自动放行制造或人体连接。"""
from pathlib import Path
import copy
import hashlib
import json

P = Path(__file__).resolve().parent


def candidate():
    baseline = P / 'baseline-design.json'
    pin = json.loads((P / 'baseline.json').read_text())
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == pin['sha256'], '原设计快照改变'
    d = copy.deepcopy(json.loads(baseline.read_text()))
    parts = {x['ref']: x for x in d['parts']}
    # PWDN 不再跟随 PG 爬升：由独立 GPIO 经现有空闲转换通道驱动，两侧默认下拉。
    del parts['U11']
    parts['U2']['pins']['8'] = 'XIAO_PWDN'
    parts['U2']['pins']['16'] = 'ADS_PWDN'
    parts['J1']['pins'].update({'15': 'XIAO_PWDN', '16': 'OE_N'})
    d['pinnames']['J1_XIAO'].update({'15': 'D4_PWDN', '16': 'D5_NOT_READY'})
    parts['J1']['value'] = 'XIAO_16P'
    parts['J1']['note'] = '原14脚保持；15=D4/PWDN，16=D5/OE_N状态，D5仅输入且不启用内部上下拉。'
    parts['J1']['mpn'] = 'TST-108-01-L-D'
    parts['J2']['mpn'] = 'B2B-PH-K-S'
    parts['J3']['mpn'] = '43045-2012'
    parts['J3']['pins'].update({'18': None, '19': None, '20': None})
    d['pinnames']['J3_ELEC'].update({'18': 'NC', '19': 'NC', '20': 'NC'})
    parts['J3']['note'] = 'Micro-Fit20针，1–17保留原逻辑；18–20不接。仅离体调试板，未确认实际线束。'
    # 施密特输入允许 PG 慢边沿；门限按 TI SCES802 的完整电压范围核算。
    parts['U10'].update(value='SN74AUP1T14DCKR', lcsc='', sym='SN74AUP1T14',
                       note='PG由DVDD上拉；3V3供电，施密特输入；设计温度限定−40…85°C。')
    d['pinnames']['SN74AUP1T14'] = {'1': 'NC', '2': 'A', '3': 'GND', '4': 'Y', '5': 'VCC'}
    # 候选不使用 RLDIN 回读/MUX 路径，按 ADS 未使用模拟输入脚的要求接 AVDD。
    parts['U1']['pins']['62'] = 'AVDD'
    parts['U1']['note'] = 'RLDIN未用接AVDD；固件必须禁止RLD_MEAS及CHnSET的RLDIN路由。'

    def add(ref, value, pins, sym='RES', sheet='IF', note='', lcsc='', fp=None):
        assert ref not in parts
        parts[ref] = dict(ref=ref, value=value, pins=pins, sym=sym, sheet=sheet,
                          block='R01', note=note, lcsc=lcsc, fp=fp)

    add('R39', '10k', {'1': 'XIAO_PWDN', '2': 'GND'}, lcsc='C25744', fp='R0402')
    add('R40', '10k', {'1': 'ADS_PWDN', '2': 'GND'}, sheet='ADS', lcsc='C25744', fp='R0402')
    # 监控器独立由电池供电，在主控3V3掉电时关掉模拟电源；RC串阻限制RESET放电电流。
    add('U12', 'TPS3808G33DBVR', {'1': 'U7_EN', '2': 'GND', '3': 'VBAT',
        '4': None, '5': '3V3', '6': 'VBAT'}, sym='TPS3808G33', sheet='POWER',
        note='CT悬空，12–28ms释放延时；RESET不加独立上拉，避免MCU复位时自行开AFE。')
    d['pinnames']['TPS3808G33'] = {'1': '~{RESET}', '2': 'GND', '3': '~{MR}',
                                  '4': 'CT', '5': 'SENSE', '6': 'VDD'}
    parts['C31'].update(pins={'1': 'VBAT', '2': 'GND'}, sheet='POWER', block='R01',
                        note='U12电池供电去耦，复用被删除U11的100nF位号。')
    parts['C24']['pins']['1'] = 'EN_RC'
    add('R41', '4.7k', {'1': 'U7_EN', '2': 'EN_RC'}, sheet='POWER', lcsc='C25900', fp='R0402',
        note='1%；C24最坏放电加ANA_EN电流<1mA，使TPS3808的VOL保证条件适用。')
    # KiCad 二极管封装编号是 1=K、2=A，转换候选符号脚号而不偷偷交换焊盘网。
    parts['D1']['pins'] = {'1': 'AVDD', '2': 'DVDD'}
    d['pinnames']['B5819WS'] = {'1': 'K', '2': 'A'}
    parts['D1']['note'] = 'R+O B5819WS，SOD-323；原图逻辑1=A/2=K，本候选物理1=K/2=A。'
    for i, net in enumerate(['AVDD', 'DVDD', 'PG', 'OE_N', 'ADS_PWDN', 'ADS_RESET',
                              'ADS_CLKSEL', 'VCAP1', 'U7_EN', 'GND'], 1):
        add(f'TP{i}', net, {'1': net}, sym='TESTPOINT', sheet='POWER', fp='TESTPOINT',
            note='仅离体示波/逻辑分析探测；探头电容对VCAP1的影响须记录。')
    bindings = json.loads((P / 'footprints.json').read_text())
    for part in parts.values():
        binding = bindings.get(part['ref']) or bindings.get(part['fp'])
        assert binding, f"未定义封装：{part['ref']}"
        part['footprint'] = binding['footprint']
        part['footprint_source'] = binding['source']
        part['dnp'] = False
        part['source_ref'] = part['ref']
    # KiCad 要求位号以数字结尾；保留旧位号用于追溯，制造源使用规范编号。
    aliases = {}
    for ch in range(1,9):
        for li, leg in enumerate('PN'):
            for ri, letter in enumerate('ABCDEF'):
                old = f'R{ch}{leg}{letter}'
                new = f'R{101+(ch-1)*12+li*6+ri}'
                parts[old]['ref'] = new
                aliases[old] = new
    d.update(revision='V12-R01', status='OFF_BODY_CANDIDATE_NOT_RELEASED',
             manufacturing_ready=False, human_test_ready=False,
             default_variant='S', q_variant='仅离体噪声对照',
             operating_temperature_C=[-40, 85],
             source_sha256=pin['sha256'], parts=list(parts.values()), reference_aliases=aliases,
             open_gates=[ '实际供电/掉电波形', '真实接口与电池确认',
                         '工厂工艺/物料与独立制造包复核', '人体路径安全复核', '真实信号/无线/装配验收'])
    return d


if __name__ == '__main__':
    d = candidate()
    (P / 'design.json').write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
    print(f"V12-R01：{len(d['parts'])}件；仅离体候选，未放行制造/佩戴")
