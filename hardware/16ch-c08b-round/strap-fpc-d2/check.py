"""D2 全部检查（KiCad 自带 python3 运行）：python3 check.py
全部从 strap-a/b.kicad_pcb 文件读回（不用 build.py 内存里的数），写 checks.json、pin-map.json、drc-a/b.json、lint-a/b.json、
lengths.csv、widths.csv。任一项不过退出码 1，失败项写进 checks.json 的 fails。
1. 脚序：每片 34 根金手指的网 == 从 D17 源板现推的网；与 R12 金手指逐脚比对。反例：对调两根、整排镜像必须报错。
2. 触点（11-11 晚：CH1/CH2 回胶囊底）：表带 14 路 28 个 F 面 SMD 圆焊盘 Φ6.5、无孔、开窗同大，对内 18.0，每颗 F 面 100k；
   焊盘中心与 TPU 层 D2 孔中心逐个重合（≤ 0.01，北排写死期望 (34, 42)）；
   box_vs_r15（11-11 晚改）：胶囊底 6 个触点中心与 R15 同位（≤ 0.01）且为 F 面 SMD 圆（CH Φ6.5、EB Φ4.5）无孔、开窗 = 焊盘；R1–R4/R33/R34 同值同网仍在 B 面，位置变化只报告；尾部与 R12 相同。
3. KiCad DRC（工程 .kicad_dru，--all-track-errors）0 违规 0 未连，重铺后也 0。反例：P/N 短路、两对中心距 0.40、动态区过孔必须报出；0.47 不报。
4. route_lint 硬项 0。
5. 分段等长：尾侧 CHn_P/N、电极侧 CHn_P_E/N_E 各自差 ≤ 10 mil。
6. 几何：异网中心距 ≥ 0.47、对内 ≥ 0.30、走线/过孔铜到板边 ≥ 0.305、动态区过孔 0、尾部过孔到金手指、PI 补强盖满触点且不盖串阻、
   GND 平面孤铜/碎块/碎孔 0、触点焊盘到板边 ≥ 0.3、过孔不进焊盘。
7. 两片叠放：B 外形让开 A 的串阻、PI 补强片；A 的 Φ4.9 让位孔让开 B 的 EB2 Φ4.5 焊盘（≥ 0.2）。带截面只报告。
8. 修不平（11-11）：strapside_flat —— 16 个岛各自在表带侧（B 面一侧）的最高物（PI 补强片厚度读板上注释、
   叠在下面的另一片按其板厚、B 面元件按 0402 高 0.35 计）彼此差 ≤ 0.01，且表带上 B 面元件 0；
   skinside_res_envelope —— F 面每颗串阻（焊盘 ∪ 本体）外包络外扩 0.3 = TPU 背面浅槽矩形，写进 geometry.json 的 f_res_pockets，
   槽离每个 Φ6.5 焊盘 ≥ 0.25（TPU 孔壁不能被槽打穿）。两道门都在改坏的临时副本上造反例，必须红。
"""
import ast
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew as k

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import _and, area, backside_tracks, band_stats, cross_section, items, material, measure, pset, ptrect, ptseg, stack_gap  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R12 = HERE
R15 = HERE.parent / 'strap-fpc-r15'
D17 = HERE.parent / 'afe-d20/afe-d20-silk.kicad_pcb'
D17_SHA = '87a6863f5c5b5d8de2264e6370b0c6d1670f891305c9b7820c71986956f011cb'
LINT = HERE.parent / 'afe-d20/route_lint.py'
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY = sys.executable
MIL = 0.0254
PIECES = {'a': ('V4_FPC1', 'TAIL_A'), 'b': ('V4_FPC3', 'TAIL_B')}
mm = k.ToMM
report = {'status': '已实现未验收：本机 DRC/几何/脚序/对孔检查结果见各项；未打样、未焊铜片、未插实物、未贴肤'}
fails = []


def gate(name, ok, detail):
    report[name] = dict(ok=bool(ok), **detail) if isinstance(detail, dict) else dict(ok=bool(ok), detail=detail)
    if not ok:
        fails.append(name)


def load_copy(src):
    tmp = Path(tempfile.mkdtemp(prefix='d2chk-'))
    shutil.copy(src, tmp / 'x.kicad_pcb')
    b = k.LoadBoard(str(tmp / 'x.kicad_pcb'))
    shutil.rmtree(tmp)
    return b


boards = {s: k.LoadBoard(str(HERE / f'strap-{s}.kicad_pcb')) for s in PIECES}
r12 = {s: load_copy(R12 / f'strap-{s}.kicad_pcb') for s in PIECES}
report['board_sha256'] = {s: hashlib.sha256((HERE / f'strap-{s}.kicad_pcb').read_bytes()).hexdigest() for s in PIECES}

# ---------- 1. 脚序：从 D17 源板现推 ----------
d17_sha = hashlib.sha256(D17.read_bytes()).hexdigest()
db = load_copy(D17)
pins, bynet = {}, {}
for f in db.GetFootprints():
    for p in f.Pads():
        pins.setdefault(f.GetReference(), {})[p.GetNumber()] = p.GetNetname()
        bynet.setdefault(p.GetNetname(), set()).add((f.GetReference(), p.GetNumber()))
AUX = {'V4_BIAS_DRV1': 'BIAS_DRV1', 'V4_RLD_OUT2': 'BIAS_DRV12', 'V4_WCT': 'WCT', 'V4_WCT2': 'WCT2', 'AGND': 'AGND'}


def d17_expect(ref):
    """V4_FPCx 每脚应接的软板网：AGND/辅助照名；采样网沿 15k 阵列（V4_U3..U10，1↔8…4↔5）到 ADS1298 的 V4_INx[PN](2)。"""
    out = {}
    for n in range(1, 35):
        net = pins[ref][str(n)]
        if net in AUX:
            out[n] = AUX[net]
            continue
        hop = [x for x in bynet[net] if re.fullmatch(r'V4_U(3|4|5|6|7|8|9|10)', x[0])]
        assert len(hop) == 1, (ref, n, net, hop)
        ar, ap = hop[0]
        far = pins[ar][str(9 - int(ap))]
        adc = [x for x in bynet[far] if x[0] in ('V4_U1', 'V4_U2')]
        m = re.fullmatch(r'V4_IN(\d)([PN])(2?)', far)
        assert m and len(adc) == 1, (ref, n, far, adc)
        out[n] = f'CH{int(m[1]) + (8 if m[3] else 0)}_{m[2]}'
    return out


def tail_nets(b, ref):
    f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    return f, {int(p.GetNumber()): p for p in f.Pads()}


def pin_errors(nets, want):
    return [dict(pin=n, board_net=nets.get(n), d17_net=want[n]) for n in range(1, 35) if nets.get(n) != want[n]]


TAIL_EXT = 1.30          # 11-11 胶囊段移到壳外：尾巴加长 1.30，金手指整排沿 −x 平移 1.30（与 R12 比几何时扣掉；tail_vs_r12 核实测平移量）
pin_map = {}
for s, (ref, tref) in PIECES.items():
    want = d17_expect(ref)
    f, pads = tail_nets(boards[s], tref)
    nets = {n: p.GetNetname() for n, p in pads.items()}
    errs = pin_errors(nets, want)
    _, rpads = tail_nets(r12[s], tref)
    r12_diff = [n for n, p in rpads.items() if p.GetNetname() and p.GetNetname() != nets.get(n)]
    geo_diff = [n for n, p in rpads.items() if (round(mm(p.GetPosition().x) - TAIL_EXT, 4), round(mm(p.GetPosition().y), 4), round(mm(p.GetSize(k.F_Cu).x), 3), round(mm(p.GetSize(k.F_Cu).y), 3))
                != (round(mm(pads[n].GetPosition().x), 4), round(mm(pads[n].GetPosition().y), 4), round(mm(pads[n].GetSize(k.F_Cu).x), 3), round(mm(pads[n].GetSize(k.F_Cu).y), 3))
                or p.IsOnLayer(k.F_Cu) != pads[n].IsOnLayer(k.F_Cu)]
    mirrored = {n: nets[35 - n] for n in nets}
    pin_map[s] = dict(connector=ref, d17_sha256=d17_sha, table=[dict(pin=n, board_net=nets[n], d17_net=pins[ref][str(n)], expect=want[n],
                                                                      y=round(mm(pads[n].GetPosition().y), 3)) for n in range(1, 35)])
    gate(f'pins_{s}', not errs and len(pads) == 34 and not r12_diff and not geo_diff and d17_sha == D17_SHA,
         dict(connector=ref, pads=len(pads), errors_vs_d17=errs, d17_sha256_ok=d17_sha == D17_SHA,
              signal_pins_differ_from_r12=r12_diff, finger_geometry_differs_from_r12=geo_diff,
              pin1_y=round(mm(pads[1].GetPosition().y), 3), pin34_y=round(mm(pads[34].GetPosition().y), 3),
              finger_face='F' if all(p.IsOnLayer(k.F_Cu) and not p.IsOnLayer(k.B_Cu) for p in pads.values()) else 'B',
              negative_mirror_errors=len(pin_errors(mirrored, want))))
(HERE / 'pin-map.json').write_text(json.dumps(pin_map, ensure_ascii=False, indent=1))

# 反例④：对调两根金手指的网存盘，再从文件读回做同样的检查
neg_pin = {}
for s, (ref, tref), (p1, p2) in (('a', PIECES['a'], (19, 20)), ('b', PIECES['b'], (6, 7))):
    tmp = Path(tempfile.mkdtemp(prefix='d2neg-'))
    b = k.LoadBoard(str(HERE / f'strap-{s}.kicad_pcb'))
    _, pads = tail_nets(b, tref)
    n1, n2 = pads[p1].GetNet(), pads[p2].GetNet()
    pads[p1].SetNet(n2); pads[p2].SetNet(n1)
    k.SaveBoard(str(tmp / 'swap.kicad_pcb'), b)
    _, sp = tail_nets(k.LoadBoard(str(tmp / 'swap.kicad_pcb')), tref)
    shutil.rmtree(tmp)
    e = pin_errors({n: p.GetNetname() for n, p in sp.items()}, d17_expect(ref))
    neg_pin[f'{s}_swap_{p1}_{p2}'] = dict(errors=len(e), pins=[x['pin'] for x in e])
gate('pin_order_negative', all(v['errors'] == 2 for v in neg_pin.values()) and all(report[f'pins_{s}']['negative_mirror_errors'] > 0 for s in PIECES), neg_pin)

# ---------- 2. 触点、串阻（D2 新布置）、盒底辅助件与 R15 逐个相同、尾部与 R12 ----------
TPU = HERE / 'tpu-layer-d2/build.py'


def tpu_consts():
    want = ('PITCH', 'NORTH_YS', 'SOUTH_YS', 'LAYER_W', 'PN', 'DISC_D', 'HOLE_CLEAR')
    ns = {}
    for node in ast.parse(TPU.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in want:
            exec(compile(ast.Module([node], []), str(TPU), 'exec'), ns)
    return {n: ns[n] for n in want}


TC = tpu_consts()
NORTH_YS_EXPECT = (34.0, 42.0)          # 11-11 晚 Mako 定：北片只剩 CH3/CH4（表带 Y 34/42）；写死，不跟 TPU 文件走，TPU 文件不符另报
BOX_CH = (1, 2)                          # 胶囊底两路（11-11 起 F 面 Φ6.5 SMD 焊盘 + B 面串阻，box_vs_r15 管）
contacts, topo, counts = {}, [], {}
for s in PIECES:
    fps = list(boards[s].GetFootprints())
    counts[s] = dict(contacts=0, resistors=sum(1 for f in fps if f.GetReference().startswith('R')))
    for f in fps:
        m = re.fullmatch(r'E(\d+)([NP])', f.GetReference())
        if not m or int(m[1]) in BOX_CH:
            continue
        counts[s]['contacts'] += 1
        (p,) = list(f.Pads())
        contacts[f.GetReference()] = dict(piece=s, ch=int(m[1]), pol=m[2], x=round(mm(p.GetPosition().x), 4), y=round(mm(p.GetPosition().y), 4),
                                          d=round(mm(p.GetSize(k.F_Cu).x), 4), circle=p.GetShape() == k.PAD_SHAPE_CIRCLE,
                                          smd=p.GetAttribute() == k.PAD_ATTRIB_SMD, drill=round(mm(p.GetDrillSize().x), 4),
                                          layers=sorted(boards[s].GetLayerName(L) for L in p.GetLayerSet().Seq()),
                                          mask_margin=round(mm(p.GetLocalSolderMaskMargin() or 0), 4), net=p.GetNetname())
    chs = sorted({int(p.GetNetname()[2:].split('_')[0]) for f in fps for p in f.Pads() if p.GetNetname().startswith('CH')})
    for ch in chs:
        for pol in 'NP':
            t, e = f'CH{ch}_{pol}', f'CH{ch}_{pol}_E'
            rs = [f for f in fps if {p.GetNetname() for p in f.Pads()} == {t, e}]
            es = [f for f in fps if f.GetReference() == f'E{ch}{pol}' and [p.GetNetname() for p in f.Pads()] == [e]]
            if len(rs) != 1 or len(es) != 1 or rs[0].GetValue() != '100k' or rs[0].GetLayerName() != ('B.Cu' if ch in BOX_CH else 'F.Cu'):
                topo.append(dict(net=t, resistors=len(rs), contacts=len(es)))
bad_pad = {r: c for r, c in contacts.items() if not (c['circle'] and c['smd'] and c['d'] == 6.5 and c['drill'] == 0
                                                    and c['layers'] == ['F.Cu', 'F.Mask', 'F.Paste'] and c['mask_margin'] == 0)}
STRAP_CH = range(3, 17)
pair_sp = {ch: round(contacts[f'E{ch}P']['y'] - contacts[f'E{ch}N']['y'], 4) for ch in STRAP_CH}
xs = {ch: contacts[f'E{ch}N']['x'] for ch in STRAP_CH}
pcb_mask_margin = round(mm(boards['a'].GetDesignSettings().m_SolderMaskExpansion), 4)
gate('contacts_d2', len(contacts) == 28 and not bad_pad and not topo and all(v == 18.0 for v in pair_sp.values())
     and all(contacts[f'E{ch}N']['y'] == 41.0 for ch in STRAP_CH) and pcb_mask_margin == 0
     and counts['a']['resistors'] + counts['b']['resistors'] == 34,
     dict(strap_contacts=len(contacts), counts=counts, pad='表带 28 个：F 面 SMD 圆 Φ6.5、无孔、F.Cu/F.Mask/F.Paste、阻焊开窗 = 焊盘（本地 0、全板 pad_to_mask 0）',
          bad_pads=bad_pad, topology_errors=topo, pair_spacing_mm=pair_sp, contact_x=xs, board_mask_margin=pcb_mask_margin))

# 每个触点焊盘中心 ↔ TPU 层 D2 孔中心（表带 X = y − 50，Y = 58 − x）
holes = [(sx * TC['PN'] / 2, Y) for Y in NORTH_YS_EXPECT + tuple(TC['SOUTH_YS']) for sx in (-1, 1)]
tpu_north_ok = tuple(TC['NORTH_YS']) == NORTH_YS_EXPECT
pairs, used = [], set()
for ref, c in sorted(contacts.items()):
    X, Y = 50.0 - c['y'], 58.0 - c['x']   # TPU 层坐标 Z 朝皮肤（R13 壳 Z 朝表带），所以 X = 50 − 板 y（右手系，行列式 +1；复核 11-11 P0：X = y − 50 是镜像）
    i, h = min(enumerate(holes), key=lambda t: math.dist(t[1], (X, Y)))
    used.add(i)
    pairs.append(dict(ref=ref, strap_xy=[round(X, 4), round(Y, 4)], hole=[h[0], h[1]], err_mm=round(math.dist(h, (X, Y)), 5)))
worst_al = max(p['err_mm'] for p in pairs)
hole_d = TC['DISC_D'] + TC['HOLE_CLEAR']
gate('tpu_hole_alignment', len(pairs) == 28 and len(used) == len(holes) == 28 and worst_al <= 0.01 and len(TC['SOUTH_YS']) == 12,
     dict(tpu_build=str(TPU.relative_to(ROOT)), tpu_sha256=hashlib.sha256(TPU.read_bytes()).hexdigest(), holes=len(holes), matched=len(used),
          north_ys_expected=list(NORTH_YS_EXPECT), north_ys_in_tpu_file=list(TC['NORTH_YS']), tpu_file_north_matches=tpu_north_ok,
          worst_err_mm=worst_al, tpu_hole_d=hole_d, pad_d=6.5, disc_d=TC['DISC_D'],
          note='焊盘 Φ6.5 = 铜片 Φ6 + 2×0.25；TPU 孔 Φ6.5（铜片 + 0.5 套装余量），两者同径同心', table=pairs))

# 胶囊底（11-11 Mako：底片开 6 孔、铜片同表带）：6 个触点中心与 R15 同位（≤ 0.01），且是 F 面 SMD 圆 Φ6.5、无孔、开窗 = 焊盘；
# 串阻 R1–R4/R33/R34 与 R15 同值、同网（逐焊盘的网集合）、仍在 B 面；位置可变，报告变化量
r15 = {s: load_copy(R15 / f'strap-{s}.kicad_pcb') for s in PIECES}
BOX_CONTACTS = {'a': ('E1N', 'E1P', 'E2N', 'E2P', 'EB1'), 'b': ('EB2',)}
BOX_RES = {'a': ('R1', 'R2', 'R3', 'R4', 'R33'), 'b': ('R34',)}
BOX_D = {'E1N': 6.5, 'E1P': 6.5, 'E2N': 6.5, 'E2P': 6.5, 'EB1': 4.5, 'EB2': 4.5}   # 11-11：EB1/EB2 用 Φ4 铜片，焊盘 Φ4.5


def fpd(b):
    return {f.GetReference(): f for f in b.GetFootprints()}


def box_cmp(bd):
    bad, moved, rows = [], {}, []
    for s in PIECES:
        here, old = fpd(bd[s]), fpd(r15[s])
        for ref in BOX_CONTACTS[s]:
            f, o = here.get(ref), old[ref]
            if f is None or len(list(f.Pads())) != 1:
                bad.append(f'{ref} 缺'); continue
            (p,), (q,) = list(f.Pads()), list(o.Pads())
            err = math.dist((mm(p.GetPosition().x), mm(p.GetPosition().y)), (mm(q.GetPosition().x), mm(q.GetPosition().y)))
            lay = sorted(bd[s].GetLayerName(L) for L in p.GetLayerSet().Seq())
            ok = (err <= 0.01 and p.GetNetname() == q.GetNetname() and p.GetShape() == k.PAD_SHAPE_CIRCLE and p.GetAttribute() == k.PAD_ATTRIB_SMD
                  and round(mm(p.GetSize(k.F_Cu).x), 4) == BOX_D[ref] and round(mm(p.GetSize(k.F_Cu).y), 4) == BOX_D[ref] and mm(p.GetDrillSize().x) == 0
                  and lay == ['F.Cu', 'F.Mask', 'F.Paste'] and (p.GetLocalSolderMaskMargin() or 0) == 0)
            rows.append(dict(piece=s, ref=ref, net=p.GetNetname(), board=[round(mm(p.GetPosition().x), 4), round(mm(p.GetPosition().y), 4)],
                             err_vs_r15_mm=round(err, 5), d=round(mm(p.GetSize(k.F_Cu).x), 4), drill=round(mm(p.GetDrillSize().x), 4), layers=lay))
            if not ok:
                bad.append(ref)
        for ref in BOX_RES[s]:
            f, o = here.get(ref), old[ref]
            if f is None:
                bad.append(f'{ref} 缺'); continue
            nets = sorted(p.GetNetname() for p in f.Pads()); nets_r15 = sorted(p.GetNetname() for p in o.Pads())
            if f.GetValue() != o.GetValue() or nets != nets_r15 or f.GetLayerName() != 'B.Cu' or len(nets) != 2:
                bad.append(ref)
            moved[ref] = dict(value=f.GetValue(), nets=nets, layer=f.GetLayerName(), at=[round(mm(f.GetPosition().x), 4), round(mm(f.GetPosition().y), 4)],
                              r15_at=[round(mm(o.GetPosition().x), 4), round(mm(o.GetPosition().y), 4)],
                              moved_mm=round(math.dist((mm(f.GetPosition().x), mm(f.GetPosition().y)), (mm(o.GetPosition().x), mm(o.GetPosition().y))), 4))
    return dict(same=not bad and len(rows) == 6 and len(moved) == 6, bad=bad, contacts=rows, resistors=moved)


box = box_cmp(boards)


def _bx_move_e1n(b):
    f = next(f for f in b.GetFootprints() if f.GetReference() == 'E1N')
    f.SetPosition(k.VECTOR2I(f.GetPosition().x + k.FromMM(0.05), f.GetPosition().y))


def _bx_value_r33(b):
    next(f for f in b.GetFootprints() if f.GetReference() == 'R33').SetValue('100k')


def _bx_net_r4(b):
    p = next(p for f in b.GetFootprints() if f.GetReference() == 'R4' for p in f.Pads() if p.GetNetname() == 'CH2_N')
    p.SetNet(b.FindNet('CH1_N'))


def _bx_eb1_drill(b):
    p = next(iter(next(f for f in b.GetFootprints() if f.GetReference() == 'EB1').Pads()))
    p.SetSize(k.VECTOR2I(k.FromMM(1.8), k.FromMM(1.8)))


def _bx_edit(s, fn):
    tmp = Path(tempfile.mkdtemp(prefix='d2box-'))
    b = k.LoadBoard(str(HERE / f'strap-{s}.kicad_pcb'))
    fn(b)
    k.SaveBoard(str(tmp / 'x.kicad_pcb'), b)
    nb = k.LoadBoard(str(tmp / 'x.kicad_pcb'))
    shutil.rmtree(tmp)
    return nb


neg_box = {}
for name, fn in (('E1N 右移 0.05', _bx_move_e1n), ('R33 值改 100k', _bx_value_r33), ('R4 尾侧网改 CH1_N', _bx_net_r4), ('EB1 焊盘改 Φ1.8', _bx_eb1_drill)):
    neg_box[name] = not box_cmp({'a': _bx_edit('a', fn), 'b': boards['b']})['same']
gate('box_vs_r15', box['same'] and all(neg_box.values()),
     dict(box, negatives_red=neg_box,
          note='胶囊底 6 个触点（CH1/CH2 两对 + EB1/EB2）中心与 R15 同位（≤ 0.01），F 面 SMD 圆、无孔、开窗 = 焊盘，直径 CH1/CH2 Φ6.5、EB1/EB2 Φ4.5；'
               '串阻 R1–R4（100k）、R33/R34（200k）与 R15 同值同网、仍在 B 面，位置可变（resistors.moved_mm 报告变化量）'))

tail_cmp = {}
for s, (ref, tref) in PIECES.items():
    ia, ir = items(boards[s]), items(r12[s])
    fa = [p for p in ia['pads'] if p['ref'] == tref]
    tip = round(min(p['rect'][0] for p in fa) - 0.2, 3)
    wa = next(s_ for s_ in cross_section(ia, tip + 1.0)[0] if s_[0] < 50 < s_[1])
    tip_r = round(min(p['rect'][0] for p in ir['pads'] if p['ref'] == tref) - 0.2, 3)
    wr = next(s_ for s_ in cross_section(ir, tip_r + 1.0)[0] if s_[0] < 50 < s_[1])
    ring = [r for r in ia['rings']['User.2'] if abs(min(x for x, _ in r) - tip) < 1e-3]
    st_len = round(max(x for x, _ in ring[0]) - min(x for x, _ in ring[0]), 3) if ring else None
    tail_cmp[s] = dict(tip_x=tip, width_d2=round(wa[1] - wa[0], 3), width_r12=round(wr[1] - wr[0], 3), stiffener_len=st_len,
                       stiffener_side='B（金手指背面）' if ring else None)
for s_, (ref_, tref_) in PIECES.items():
    _r = [p for p in items(r12[s_])['pads'] if p['ref'] == tref_]
    tail_cmp[s_]['tip_x_r12'] = round(min(p['rect'][0] for p in _r) - 0.2, 3)
    tail_cmp[s_]['extension_mm'] = round(tail_cmp[s_]['tip_x_r12'] - tail_cmp[s_]['tip_x'], 3)
gate('tail_vs_r12', all(v['width_d2'] == v['width_r12'] == 17.5 and v['stiffener_len'] == 2.5 and v['extension_mm'] == TAIL_EXT for v in tail_cmp.values())
     and all(not report[f'pins_{s}']['finger_geometry_differs_from_r12'] for s in PIECES), tail_cmp)

# ---------- 3. DRC ----------


def drc(board_path, out, refill=False):
    subprocess.run([KC, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors', *(['--refill-zones'] if refill else []), '-o', str(out), str(board_path)],
                   check=True, capture_output=True)
    return json.loads(Path(out).read_text())


for s in PIECES:
    d = drc(HERE / f'strap-{s}.kicad_pcb', HERE / f'drc-{s}.json')
    tmp = Path(tempfile.mkdtemp(prefix='d2drc-'))
    rf = drc(HERE / f'strap-{s}.kicad_pcb', tmp / 'refill.json', refill=True)         # 不存盘，只验证重铺后也干净
    shutil.rmtree(tmp)
    gate(f'drc_{s}', not d['violations'] and not d['unconnected_items'] and not rf['violations'] and not rf['unconnected_items'],
         dict(violations=len(d['violations']), unconnected=len(d['unconnected_items']), kicad=d.get('kicad_version'), rules=f'strap-{s}.kicad_dru',
              after_refill_zones=dict(violations=len(rf['violations']), unconnected=len(rf['unconnected_items']))))


def negative(s, edit):
    tmp = Path(tempfile.mkdtemp(prefix='d2neg-'))
    for ext in ('kicad_pro', 'kicad_dru'):
        shutil.copy(HERE / f'strap-{s}.{ext}', tmp / f'strap-{s}.{ext}')
    b = k.LoadBoard(str(HERE / f'strap-{s}.kicad_pcb'))
    edit(b)
    k.SaveBoard(str(tmp / f'strap-{s}.kicad_pcb'), b)
    d = drc(tmp / f'strap-{s}.kicad_pcb', tmp / 'drc.json')
    shutil.rmtree(tmp)
    return sorted({v['type'] + (' :' + re.search(r"'([^']+)'", v['description'])[1] if "'" in v['description'] else '') for v in d['violations']})


def add_track(b, net, pts, layer=k.F_Cu):
    for a, z in zip(pts, pts[1:]):
        t = k.PCB_TRACK(b)
        t.SetStart(k.VECTOR2I(k.FromMM(a[0]), k.FromMM(a[1]))); t.SetEnd(k.VECTOR2I(k.FromMM(z[0]), k.FromMM(z[1])))
        t.SetWidth(k.FromMM(0.15)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)


def add_via(b, net, p):
    v = k.PCB_VIA(b)
    v.SetPosition(k.VECTOR2I(k.FromMM(p[0]), k.FromMM(p[1]))); v.SetWidth(k.FromMM(0.5)); v.SetDrill(k.FromMM(0.25))
    v.SetLayerPair(k.F_Cu, k.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)


def lane_y(s, x, net):
    return next(h[0] for h in cross_section(items(boards[s]), x)[1] if h[1] == net and h[2] == 'F.Cu')


negs = {}
# ① 短路：A 出盒带 x=80 处 CH5_N 加一段竖线压到 CH5_P
yp, yn = lane_y('a', 80.0, 'CH5_P'), lane_y('a', 80.0, 'CH5_N')
negs['short_CH5_N_to_CH5_P'] = negative('a', lambda b: add_track(b, 'CH5_N', [(80.0, yn), (80.0, yp)]))
# ② 3W：B 并行段 x 80–82，CH13_P 向下凸一个 45° 梯形，凸起段离 CH12_N 中心距 0.40（净距 0.25：≥0.15 通用、<0.32 3W）
y13, y12 = lane_y('b', 80.0, 'CH13_P'), lane_y('b', 80.0, 'CH12_N')


def jog(c):
    yj = y12 - c
    e = yj - y13
    return lambda b: add_track(b, 'CH13_P', [(80.0, y13), (80.0 + e, yj), (82.0 - e, yj), (82.0, y13)])


negs['center_0.40_CH13_P_vs_CH12_N'] = negative('b', jog(0.40))
negs['positive_center_0.47_same_place'] = negative('b', jog(0.47))
# ③ 动态区过孔：A 桥 1（x 93.55–94.45）两道之间放一个 AGND 过孔
ys = sorted(h[0] for h in cross_section(items(boards['a']), 94.0)[1] if h[2] == 'F.Cu')
gap = max(zip(ys, ys[1:]), key=lambda t: t[1] - t[0])
negs['via_in_dynamic_A_bridge1'] = negative('a', lambda b: add_via(b, 'AGND', (94.0, round((gap[0] + gap[1]) / 2, 3))))
neg_ok = (bool({'shorting_items', 'tracks_crossing'} & {x.split(' ')[0] for x in negs['short_CH5_N_to_CH5_P']})
          and any('中心距0.47' in x for x in negs['center_0.40_CH13_P_vs_CH12_N'])
          and not any('中心距0.47' in x for x in negs['positive_center_0.47_same_place'])
          and any(x.startswith('items_not_allowed') for x in negs['via_in_dynamic_A_bridge1']))
gate('drc_negative_controls', neg_ok, negs)

# ---------- 4. route_lint ----------
hard = ('odd_angle', 'sharp', 'tee_acute', 'width_jump', 'dangling', 'pad_exit')
for s in PIECES:
    subprocess.run([KPY, str(LINT), str(HERE / f'strap-{s}.kicad_pcb'), str(HERE / f'lint-{s}.json')], capture_output=True)
    L = json.loads((HERE / f'lint-{s}.json').read_text())['summary']
    gate(f'route_lint_{s}', sum(L[h] for h in hard) == 0, dict(hard=sum(L[h] for h in hard), hard_items={h: L[h] for h in hard},
                                                            report_only={x: L[x] for x in ('pad_exit_side', 'tee_90', 'pad_exit_rotated')}))

# ---------- 5. 分段等长（读回 KiCad 走线长度） ----------
rows = []
for s, b in boards.items():
    L = {}
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_TRACK':
            L[t.GetNetname()] = L.get(t.GetNetname(), 0) + mm(t.GetLength())
    for ch in sorted({int(n[2:].split('_')[0]) for n in L if n.startswith('CH')}):
        for seg, suf in (('尾→串阻', ''), ('串阻→触点', '_E')):
            p, n = L[f'CH{ch}_P{suf}'], L[f'CH{ch}_N{suf}']
            rows.append(dict(piece=s.upper(), ch=ch, segment=seg, P_mm=round(p, 4), N_mm=round(n, 4), diff_mm=round(p - n, 4), diff_mil=round((p - n) / MIL, 3)))
with (HERE / 'lengths.csv').open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
worst = max(rows, key=lambda r: abs(r['diff_mil']))
gate('length_match', abs(worst['diff_mil']) <= 10 and len(rows) == 32,
     dict(segments=len(rows), worst_diff_mil=worst['diff_mil'], worst_at=f"{worst['piece']} CH{worst['ch']} {worst['segment']}",
          nonzero=[f"{r['piece']} CH{r['ch']} {r['segment']} {r['diff_mil']} mil" for r in rows if abs(r['diff_mil']) > 0.01], limit_mil=10, table='lengths.csv'))

# ---------- 6. 几何（metrics.py，全部从 kicad_pcb 读） ----------
for s, b in boards.items():
    m = measure(b)
    g = m['geometry']
    gate(f'geometry_{s}', g['min_center_between_different_nets_mm'] >= 0.47 - 1e-4 and g['min_center_within_pair_mm'] >= 0.30 - 1e-4
         and g['min_track_copper_to_outline_mm'] >= 0.305 - 1e-4 and (g['min_track_copper_to_hole_edge_mm'] or 9) >= 0.305 - 1e-4
         and g['min_via_copper_to_outline_mm'] >= 0.305 - 1e-4 and g['vias_in_dynamic_zones'] == 0 and g['track_widths'] == [0.15], g)
    report[f'res_pad_to_contact_{s}_report_only'] = dict(min_gap_mm=min(w['gap_mm'] for w in m['res_pad_to_contact']),
                                                         note='表带串阻与触点同在 F 面（TPU 槽由 skinside_res_envelope 管）；胶囊底 R1–R4 在 B 面、投影落在同路 Φ6.5 焊盘圆内（异面，负值 = 投影重叠，不相连）；只报告')
    t = m['tail']
    gate(f'tail_vias_{s}', t['via_copper_to_finger_copper_mm'] >= 0.3 and t['via_hole_edge_to_finger_pad_mm'] >= 0.2, t)
    st = m['stiffener']
    isl = st['layers'].get('User.2', {})
    n_isl = sum(1 for f in b.GetFootprints() if re.fullmatch(r'E(\d+)[NP]', f.GetReference()) and int(f.GetReference()[1:-1]) not in BOX_CH)
    gate(f'stiffener_{s}', st['fingers_backed_on_opposite_face'] and isl.get('island_contacts_backed') == n_isl
         and isl.get('min_contact_coverage') == 1.0 and isl.get('res_pads_covered') == 0,
         dict(island_contacts=n_isl, note='每个 Φ6.5 触点背面一块 Φ7.2 PI，整圆 100% 盖住；串阻焊盘（F 面）投影被盖 0', **st))
    # 复核 11-11：PI 补强圆片不能出岛外形（读板上 User.2 补强形状的包围盒，对岛外形 x 范围）
    _bad, _n = [], 0
    for d in b.GetDrawings():
        if d.GetLayer() != k.User_2:   # 层名被改成「补强-B」，按层号认
            continue
        _n += 1
        bb = d.GetBoundingBox()
        cx_ = (bb.GetLeft() + bb.GetRight()) / 2e6
        w_ = (bb.GetRight() - bb.GetLeft() - d.GetWidth()) / 1e6   # 包围盒含轮廓线宽，扣掉才是补强片本身
        if w_ > 5 and w_ < 9 and abs(w_ - (bb.GetBottom() - bb.GetTop() - d.GetWidth()) / 1e6) < 0.05:   # 只看圆片（尾端补强是长条）
            if w_ / 2 > 3.6 + 1e-6:
                _bad.append((round(cx_, 3), round(w_, 3)))
    gate(f'stiffener_inside_island_{s}', _n == n_isl + 1 and not _bad, dict(stiffener_shapes=_n, expect=n_isl + 1, oversize=_bad[:5], island_half_width=3.6))
    me = m['mesh']
    gate(f'gnd_planes_{s}', all(v['orphan_pieces'] == 0 and v['pieces_under_0p5mm2'] == 0 and v['voids_narrower_than_0p15'] == 0
                                and 0.40 <= v['min_copper_vs_copperable'] and v['max_copper_vs_copperable'] <= 0.62 for v in me.values()), me)
    # 触点焊盘到板边 ≥ 0.3；过孔不进焊盘（不做盘中孔）：过孔铜到任何焊盘铜 ≥ 0.15（同网也算）
    it = items(b)
    cps = [p for p in it['pads'] if p['circle'] and p['r'] > 2]          # 触点焊盘 Φ6.5 / 胶囊底 EB Φ4.5
    edge = min(min(ptseg(p['c'], a, z) for a, z in it['segs']) - p['r'] for p in cps)
    vip = min(((math.dist(v['c'], p['c']) - p['r'] - v['r'], v, p) for v in it['vias'] for p in cps), key=lambda t: t[0])
    vip_r = min(((ptrect(v['c'], p['rect']) - v['r'], v, p) for v in it['vias'] for p in it['pads'] if not p['circle']), key=lambda t: t[0])
    gate(f'pad_edge_and_no_via_in_pad_{s}', edge >= 0.3 - 1e-4 and vip[0] >= 0.15 and vip_r[0] >= 0.15,
         dict(contact_pad_to_outline_min_mm=round(edge, 4), via_to_contact_pad_min_mm=round(vip[0], 4),
              nearest=dict(via=[round(x, 3) for x in vip[1]['c']], pad=f"{vip[2]['ref']}"),
              via_to_rect_pad_min_mm=round(vip_r[0], 4), nearest_rect=f"{vip_r[2]['ref']}.{vip_r[2]['num']}"))

# ---------- 7. 带截面（只报告）与两片叠放 ----------
SEC = {
    'a': [('尾（插接尾，A 折弯区）', 35.0, 50.0), ('A 北支', 33.0, 39.0), ('A 北岛间 CH4|CH3', 20.1, 39.0), ('A 出盒带（带根）', 80.0, 53.0),
          ('A 桥1（CH5|CH6）', 94.1, 53.0), ('A 桥2', 102.1, 53.0), ('A 桥3', 110.1, 53.0)],
    'b': [('尾（插接尾，B 折弯区）', 36.5, 50.0), ('B 盒内头部', 60.0, 48.0), ('B 带根（垫在 A 背后）', 80.0, 48.0), ('B 过 A 桥1', 94.0, 48.0),
          ('B 过 A 桥2', 102.0, 48.0), ('B 过 A 桥3', 110.0, 48.0), ('B 过 A 桥4', 118.0, 48.0)]
         + [(f'B 桥{i}', 126.1 + 8 * (i - 1), 47.0) for i in range(1, 8)],
}
wrows = []
itd = {s: items(boards[s]) for s in PIECES}
for s, secs in SEC.items():
    for name, x, yref in secs:
        a_ = band_stats(itd[s], x, yref)
        assert a_ is not None, (s, name, x, yref, cross_section(itd[s], x)[0])
        lay = [a_[L] for L in ('F.Cu', 'B.Cu') if L in a_]
        wrows.append(dict(piece=s.upper(), segment=name, x=x, y=f"{a_['y0']}–{a_['y1']}", width=a_['width'],
                          pairs=sum(v['pairs'] for v in lay), min_center_diff_net=min((v['min_center_diff_net'] for v in lay if v['min_center_diff_net']), default=None),
                          pair_pitch='–'.join(sorted({str(v['pair_pitch_min']) for v in lay if v['pair_pitch_min']} | {str(v['pair_pitch_max']) for v in lay if v['pair_pitch_max']})),
                          edge_copper=f"{min((v['edge_copper_top'] for v in lay), default='')}/{min((v['edge_copper_bottom'] for v in lay), default='')}"))
with (HERE / 'widths.csv').open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(wrows[0]), lineterminator='\n'); w.writeheader(); w.writerows(wrows)
report['bands_report_only'] = dict(note='R15 的「逐段 ≥ R12、同槽 A+B 并排总宽 > R12」门不再适用（D2 里 B 在 A 背后叠放，不并排）。'
                                        '截面只报告，间距/铜到边由 geometry 门和 DRC 管', table='widths.csv', sections=wrows)
# 叠放：A 的 F 面贴肤，B 垫在 A 的 B 面后面。B 外形要让开 A 的 PI 补强片，A 的 EB1 端子从 B 的让位孔穿过；A 串阻已搬到 F 面，「B 外形 vs A 的串阻焊盘」只按投影保留；
# B 的 EB2 从 A 的让位孔穿过。
is_res = lambda p: p['ref'].startswith('R')                                  # noqa: E731


def stiff_gap(b_top, b_under):
    """b_top 的外形到 b_under 的 B 面 PI 补强圆片的带符号间隙（正 = 圆片完全在 b_top 外）。"""
    top = items(b_top)
    ol = k.SHAPE_POLY_SET(); b_top.GetBoardPolygonOutlines(ol, False)
    poly = k.SHAPE_POLY_SET(); poly.AddOutline(ol.Outline(0))
    rows = []
    for ring in items(b_under)['rings']['User.2']:
        xs_, ys_ = [x for x, _ in ring], [y for _, y in ring]
        c = ((max(xs_) + min(xs_)) / 2, (max(ys_) + min(ys_)) / 2)
        r = (max(xs_) - min(xs_)) / 2
        if abs((max(ys_) - min(ys_)) / 2 - r) > 0.01:
            continue                                                         # 只看圆片（尾补强是矩形，在盒内另一层）
        d = min(ptseg(c, a, z) for a, z in top['segs']) - r
        rows.append(dict(at=[round(c[0], 3), round(c[1], 3)], gap_mm=round(-(r + d) if poly.Contains(k.VECTOR2I(round(c[0] * 1e6), round(c[1] * 1e6))) else d, 4)))
    rows.sort(key=lambda t: t['gap_mm'])
    return dict(min_gap_mm=rows[0]['gap_mm'], nearest=rows[:3], discs=len(rows))


stack = {'B 外形 vs A 的串阻焊盘（A 的 B 面胶囊串阻 + F 面表带串阻投影）': stack_gap(boards['b'], boards['a'], {'k': is_res})['k'],
         'B 外形 vs A 的 PI 补强圆片': stiff_gap(boards['b'], boards['a'])}
gate('stack_clearance', all(v['min_gap_mm'] >= 0.2 - 1e-4 for v in stack.values()),
     dict(note='带符号间隙：正 = 对方材料不压在该件上；门限 0.2', **stack))


# 11-12 Mako「REF 挪到 A 片」：A 片 EB2A = 金属化孔焊盘（F 面贴肤焊铜片、B 面对焊 B 片 EB2）。读两块板实物：同心、同径、同网、孔金属化、两面开窗，A 片在此没有板边孔。
def eb2_joint(ba, bb):
    fa, fb = fpd(ba).get('EB2A'), fpd(bb).get('EB2')
    if fa is None or fb is None:
        return dict(ok=False, why='缺 EB2A 或 EB2')
    (pa,), (pb,) = list(fa.Pads()), list(fb.Pads())
    ca, cb = (mm(pa.GetPosition().x), mm(pa.GetPosition().y)), (mm(pb.GetPosition().x), mm(pb.GetPosition().y))
    lay = {ba.GetLayerName(L) for L in pa.GetLayerSet().Seq()}
    edge_near = [round(mm(d.GetCenter().x), 3) for d in ba.GetDrawings() if d.GetLayer() == k.Edge_Cuts and d.GetShape() == k.SHAPE_T_CIRCLE
                 and math.dist((mm(d.GetCenter().x), mm(d.GetCenter().y)), ca) < 3]
    r = dict(off_mm=round(math.dist(ca, cb), 4), da=round(mm(pa.GetSize(k.F_Cu).x), 4), db=round(mm(pb.GetSize(k.F_Cu).x), 4),
             drill=round(mm(pa.GetDrillSize().x), 4), pth=pa.GetAttribute() == k.PAD_ATTRIB_PTH, net_a=pa.GetNetname(), net_b=pb.GetNetname(),
             layers=sorted(lay), a_edge_holes_near=edge_near)
    r['ok'] = (r['off_mm'] <= 0.01 and r['da'] == r['db'] == 4.5 and 0.6 <= r['drill'] <= 1.0 and r['pth'] and r['net_a'] == r['net_b'] == 'BIAS_DRV12_E'
               and {'F.Cu', 'B.Cu', 'F.Mask', 'B.Mask'} <= lay and not edge_near)
    return r


def _j_move(b):
    f = fpd(b)['EB2A']; f.SetPosition(k.VECTOR2I(f.GetPosition().x + k.FromMM(0.05), f.GetPosition().y))


def _j_net(b):
    next(iter(fpd(b)['EB2A'].Pads())).SetNet(b.FindNet('AGND'))


jt = eb2_joint(boards['a'], boards['b'])
def _jb_move(b):
    f = fpd(b)['EB2']; f.SetPosition(k.VECTOR2I(f.GetPosition().x, f.GetPosition().y + k.FromMM(0.05)))


def _j_drill(b):
    p = next(iter(fpd(b)['EB2A'].Pads())); p.SetDrillSize(k.VECTOR2I(k.FromMM(1.2), k.FromMM(1.2)))


neg_jt = {n: not eb2_joint(_bx_edit('a', fn), boards['b'])['ok'] for n, fn in (('EB2A 右移 0.05', _j_move), ('EB2A 网改 AGND', _j_net), ('EB2A 孔 1.2', _j_drill))}
neg_jt['B 片 EB2 下移 0.05'] = not eb2_joint(boards['a'], _bx_edit('b', _jb_move))['ok']
gate('eb2_joint', jt['ok'] and all(neg_jt.values()), dict({kk: v for kk, v in jt.items() if kk != 'ok'}, joint_ok=jt['ok'], negatives_red=neg_jt,
     note='A 片 EB2A 与 B 片 EB2 同心（≤ 0.01）、同 Φ4.5、同网 BIAS_DRV12_E；A 片是金属化孔 0.6–1.0、两面开窗；A 片此处无板边孔（原 Φ4.9 让位孔已撤）'))
report['backside_tracks_report_only'] = {s: backside_tracks(boards[s]) for s in PIECES}

# ---------- 8. 修不平：表带侧等高、皮肤侧串阻槽 ----------
H0402 = 0.35            # 0402 贴装高度（假设，含焊锡）
BODY0402 = (1.0, 0.5)   # 0402 本体（假设）：长 × 宽，沿两焊盘连线方向
POCKET_M = 0.3          # 槽壁余量：TPU 槽四周比串阻外包络多 0.3
KEEP_PAD = 0.25         # 槽离 Φ6.5 焊盘边 ≥ 0.25（TPU 孔 Φ6.5 的壁不能被槽打穿）


def pi_thickness(b):
    """触点 PI 补强厚度：读板上 Cmts.User 注释「触点背面 PI 补强 Φx 厚 t」。"""
    ts = [float(m[1]) for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT'
          for m in [re.search(r'触点背面 PI 补强 Φ[\d.]+ 厚 ([\d.]+)', d.GetText())] if m]
    assert len(ts) == 1, ts
    return ts[0]


def island_rects(b):
    """每个岛：由一路两个触点焊盘定位，x = 焊盘中心 ± 补强圆片半径（= 岛半宽），y = 外形上下沿。"""
    it = items(b)
    ys = [y for _, y in it['outline']]
    discs = [r for r in it['rings']['User.2'] if abs((max(x for x, _ in r) - min(x for x, _ in r)) - (max(y for _, y in r) - min(y for _, y in r))) < 0.01]
    hw = max((max(x for x, _ in r) - min(x for x, _ in r)) / 2 for r in discs)
    out = {}
    for f in b.GetFootprints():
        m = re.fullmatch(r'E(\d+)N', f.GetReference())
        if m and int(m[1]) not in BOX_CH:
            cx = mm(f.GetPosition().x)
            out[int(m[1])] = (cx - hw, min(ys), cx + hw, max(ys))
    return out, hw


def strapside(bd):
    """bd = {'a': board, 'b': board}。返回每岛表带侧最高物与 B 面元件。"""
    th = {s: mm(b.GetDesignSettings().GetBoardThickness()) for s, b in bd.items()}
    it = {s: items(b) for s, b in bd.items()}
    rows, comps, box_b = [], [], []
    for s, b in bd.items():
        other = 'b' if s == 'a' else 'a'
        t_pi = pi_thickness(b)
        stiff = material(it[s]['rings']['User.2'])
        isl, _ = island_rects(b)
        for ch, (x0, y0, x1, y1) in sorted(isl.items()):
            r = pset([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            parts = []
            if area(_and(stiff, r)) > 1e-3:
                parts.append(dict(what=f'PI 补强（{s.upper()} 片 B 面）', h=t_pi))
            ov = area(_and(it[other]['board'], r))
            if ov > 1e-3:
                parts.append(dict(what=f'叠在下面的 {other.upper()} 片（板厚）', h=round(th[other], 4), overlap_mm2=round(ov, 2)))
            for f in b.GetFootprints():
                if f.GetLayer() == k.B_Cu and any(ptrect((mm(p.GetPosition().x), mm(p.GetPosition().y)), (x0, y0, x1, y1)) == 0 for p in f.Pads()):
                    parts.append(dict(what=f'B 面元件 {f.GetReference()}', h=H0402))
                    comps.append(f'{s.upper()}:{f.GetReference()}')
            rows.append(dict(piece=s.upper(), ch=ch, x=[round(x0, 3), round(x1, 3)], top_mm=max((p_['h'] for p_ in parts), default=0.0), items=parts))
        for f in b.GetFootprints():                       # 表带段（x ≥ 75，出胶囊）上的 B 面元件也算违规；胶囊底的 R33/R34 只报告
            if f.GetLayer() == k.B_Cu:
                x = mm(f.GetPosition().x)
                if x >= 75.0:
                    if f'{s.upper()}:{f.GetReference()}' not in comps:
                        comps.append(f'{s.upper()}:{f.GetReference()}')
                else:
                    box_b.append(f'{s.upper()}:{f.GetReference()} ({x:.2f}, {mm(f.GetPosition().y):.2f}) 胶囊底，不在表带上')
    tops = [r_['top_mm'] for r_ in rows]
    return dict(islands=len(rows), top_min_mm=min(tops), top_max_mm=max(tops), spread_mm=round(max(tops) - min(tops), 4),
                strapside_components=comps, box_b_side_parts_report_only=box_b, board_thickness_mm=th, table=rows)


def flat_ok(r):
    return r['islands'] == 14 and not r['strapside_components'] and r['spread_mm'] <= 0.01 and r['top_min_mm'] > 0


def res_pockets(bd):
    """F 面 100k 串阻：外包络 = 焊盘外框 ∪ 本体（0402 1.0×0.5，假设），外扩 POCKET_M = 槽矩形；核槽到每个 Φ6.5 焊盘 ≥ KEEP_PAD。"""
    out, worst = [], (9.0, None)
    for s, b in bd.items():
        contacts_ = [(f.GetReference(), (mm(f.GetPosition().x), mm(f.GetPosition().y)), mm(next(iter(f.Pads())).GetSize(k.F_Cu).x) / 2)
                     for f in b.GetFootprints() if re.fullmatch(r'E\d+[NP]', f.GetReference())]
        for f in b.GetFootprints():
            if not (f.GetReference().startswith('R') and f.GetValue() == '100k' and f.GetLayer() == k.F_Cu):
                continue
            pads = list(f.Pads())
            bbs = [p.GetBoundingBox() for p in pads]
            x0, y0 = min(mm(q.GetLeft()) for q in bbs), min(mm(q.GetTop()) for q in bbs)
            x1, y1 = max(mm(q.GetRight()) for q in bbs), max(mm(q.GetBottom()) for q in bbs)
            cx, cy = mm(f.GetPosition().x), mm(f.GetPosition().y)
            horiz = abs(pads[0].GetPosition().x - pads[1].GetPosition().x) >= abs(pads[0].GetPosition().y - pads[1].GetPosition().y)
            bl, bw = BODY0402 if horiz else BODY0402[::-1]
            x0, y0, x1, y1 = min(x0, cx - bl / 2), min(y0, cy - bw / 2), max(x1, cx + bl / 2), max(y1, cy + bw / 2)
            pk = (round(x0 - POCKET_M, 4), round(y0 - POCKET_M, 4), round(x1 + POCKET_M, 4), round(y1 + POCKET_M, 4))
            gaps = sorted((round(ptrect(c, pk) - r, 4), ref) for ref, c, r in contacts_)
            ch = int(re.match(r'CH(\d+)', pads[0].GetNetname())[1])
            row = dict(piece=s.upper(), ref=f.GetReference(), ch=ch, net=pads[0].GetNetname().replace('_E', ''),
                       envelope=[round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)], pocket_board=list(pk),
                       pocket_size=[round(pk[2] - pk[0], 4), round(pk[3] - pk[1], 4)],
                       pocket_strap=dict(X=[round(50 - pk[3], 4), round(50 - pk[1], 4)], Y=[round(58 - pk[2], 4), round(58 - pk[0], 4)]),   # 同上：X = 50 − 板 y
                       gap_to_contact_pad_mm=gaps[0][0], nearest_contact=gaps[0][1])
            out.append(row)
            if gaps[0][0] < worst[0]:
                worst = (gaps[0][0], f"{s.upper()}:{f.GetReference()}→{gaps[0][1]}")
    return out, worst


def pockets_ok(rows, worst):
    return len(rows) == 28 and worst[0] >= KEEP_PAD - 1e-9


def edited(s, fn):
    """改坏的临时副本：读板 → fn(board) → 存盘 → 从文件重读。"""
    tmp = Path(tempfile.mkdtemp(prefix='d2flat-'))
    b = k.LoadBoard(str(HERE / f'strap-{s}.kicad_pcb'))
    fn(b)
    k.SaveBoard(str(tmp / 'x.kicad_pcb'), b)
    nb = k.LoadBoard(str(tmp / 'x.kicad_pcb'))
    shutil.rmtree(tmp)
    return nb


def fp(b, ref):
    return next(f for f in b.GetFootprints() if f.GetReference() == ref)


def set_pi(t):
    def go(b):
        for d in b.GetDrawings():
            if d.GetClass() == 'PCB_TEXT' and '触点背面 PI 补强' in d.GetText():
                d.SetText(re.sub(r'厚 [\d.]+', f'厚 {t}', d.GetText()))
    return go


def move_ref(ref, dy):
    def go(b):
        f = fp(b, ref)
        f.SetPosition(k.VECTOR2I(f.GetPosition().x, f.GetPosition().y + k.FromMM(dy)))
    return go


flat = strapside(boards)
neg_flat = {
    'R10（A CH5 R_N）翻到 B 面': strapside({'a': edited('a', lambda b: fp(b, 'R10').SetLayerAndFlip(k.B_Cu)), 'b': boards['b']}),
    'A 片触点 PI 改回 0.15': strapside({'a': edited('a', set_pi(0.15)), 'b': boards['b']}),
}
neg_flat_red = {n: not flat_ok(v) for n, v in neg_flat.items()}
gate('strapside_flat', flat_ok(flat) and all(neg_flat_red.values()),
     dict(note='表带侧（B 面一侧）每岛最高物：PI 补强厚度读板上注释、叠在下面的另一片取其板厚、B 面元件按 0402 高 0.35；只算表带 14 岛（胶囊底 CH1/CH2 不在表带上），差 ≤ 0.01，表带上 B 面元件 0',
          **{k_: v for k_, v in flat.items() if k_ != 'table'},
          per_island=[f"{r_['piece']} CH{r_['ch']}: {r_['top_mm']}（{'、'.join(p_['what'] + ' ' + str(p_['h']) for p_ in r_['items'])}）" for r_ in flat['table']],
          negatives={n: dict(red=neg_flat_red[n], spread_mm=v['spread_mm'], top_max_mm=v['top_max_mm'], strapside_components=v['strapside_components'])
                     for n, v in neg_flat.items()}))

pk_rows, pk_worst = res_pockets(boards)
neg_pk = {}
for name, s, fn in (('R10 往焊盘挪 0.8', 'a', move_ref('R10', -0.8)), ('R17 往焊盘挪 0.8', 'b', move_ref('R17', 0.8))):
    bd = dict(boards); bd[s] = edited(s, fn)
    r_, w_ = res_pockets(bd)
    neg_pk[name] = dict(red=not pockets_ok(r_, w_), worst_gap_mm=w_[0], at=w_[1])
gate('skinside_res_envelope', pockets_ok(pk_rows, pk_worst) and all(v['red'] for v in neg_pk.values()),
     dict(note=f'每颗 F 面 100k：焊盘外框 ∪ 0402 本体 {BODY0402[0]}×{BODY0402[1]}（假设）外扩 {POCKET_M} = TPU 背面浅槽；槽离 Φ6.5 焊盘 ≥ {KEEP_PAD}；'
               '只含表带 28 颗（胶囊底 R1–R4 在 B 面，不进 TPU 槽）；矩形写进 geometry.json 的 f_res_pockets（板坐标 + 表带坐标 X = 50 − 板 y、Y = 58 − 板 x）',
          pockets=len(pk_rows), worst_gap_to_contact_pad_mm=pk_worst[0], worst_at=pk_worst[1],
          sizes=sorted({tuple(r_['pocket_size']) for r_ in pk_rows}), negatives=neg_pk))
geo_path = HERE / 'geometry.json'
geo = json.loads(geo_path.read_text())
geo['f_res_pockets'] = dict(note=f'TPU 层背面浅槽（每颗串阻一个矩形，含焊盘 + 本体，四周余量 {POCKET_M}）；槽深 ≥ {H0402} + 余量（0402 高 0.35 为假设）；'
                                 f'由 check.py 从 strap-a/b.kicad_pcb 读出；槽离 Φ6.5 焊盘 ≥ {KEEP_PAD}',
                            margin_mm=POCKET_M, part_height_mm=H0402, keep_from_pad_mm=KEEP_PAD, rects=pk_rows)
geo_path.write_text(json.dumps(geo, ensure_ascii=False, indent=1))

# ---------- 9. 胶囊在壳外（11-11 晚 Mako 定）：壳内只剩两条尾 ----------
# 胶囊段整段在 R13 底壳外（贴外底 Z 0.15），只有两条 34P 尾从 geometry.json 的 tray_tail_slot 穿底板进壳。核：
# ① 每片外形在「尾巴拐上去的线」板 x 39.96（盒 Y 18.04）以北的部分拆成连通块，带金手指的那块（尾）在拐弯线处的 y 范围必须落在缝的 x 范围里，
#    其余块（A 北支）留在壳外；② 尾的竖直段（盒 Y = 竖直中线 ± 板厚/2，Z 0.65 到对应座子）对 D17 底面件包围盒（boards-real-frame.json）
#    间隙 ≥ 0.05，B 尾插进 V4_FPC3 本身除外；③ 胶囊范围（板 x 39.96–76.8）里的 FPC 都在壳外，底面件下方没有 FPC（Z ≤ 0.15 < 底板顶 1.00）。
FRAME = HERE.parents[1] / 'enclosure-46x40/c08b-shell-r13-notch/boards-real-frame.json'
GEO = json.loads((HERE / 'geometry.json').read_text())
SLOT = GEO['tray_tail_slot']
BEND_X = SLOT['board_x_of_bend_start']
BH_GAP = 0.05
Z_TOP = {'a': (3.33 + 4.58) / 2, 'b': (1.32 + 2.57) / 2}         # 尾巴插进座子的高度：座子包围盒中线（假设）


def _rp(x0, y0, x1, y1):
    s_ = k.SHAPE_POLY_SET(); s_.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        s_.Append(round(x * 1e6), round(y * 1e6))
    return s_


def tail_check(polys, fingers_xy):
    out, ok = {}, True
    for s_, P in polys.items():
        north = _and(P, _rp(0, 0, BEND_X, 100)); north.Simplify()
        comps = []
        for i in range(north.OutlineCount()):
            ring = [(north.Outline(i).CPoint(j).x / 1e6, north.Outline(i).CPoint(j).y / 1e6) for j in range(north.Outline(i).PointCount())]
            one_ = k.SHAPE_POLY_SET(); one_.AddOutline(north.Outline(i))
            is_tail = one_.Contains(k.VECTOR2I(round(fingers_xy[s_][0] * 1e6), round(fingers_xy[s_][1] * 1e6)))
            at_bend = [y for x, y in ring if abs(x - BEND_X) < 1e-3]
            comps.append(dict(tail=is_tail, y_at_bend=[round(min(at_bend), 3), round(max(at_bend), 3)] if at_bend else None,
                              box_x_at_bend=[round(min(at_bend) - 50, 3), round(max(at_bend) - 50, 3)] if at_bend else None))
        tails = [c for c in comps if c['tail']]
        good = (len(tails) == 1 and tails[0]['box_x_at_bend'] is not None
                and SLOT['box']['x0'] <= tails[0]['box_x_at_bend'][0] and tails[0]['box_x_at_bend'][1] <= SLOT['box']['x1'])
        ok &= good
        out[s_] = dict(ok=good, components=comps)
    return ok, out


def tail_vs_parts():
    parts = [q for q in json.loads(FRAME.read_text())['afe'] if q['side'] == 'B']
    rows = []
    for s_ in PIECES:
        yc = SLOT['tail_vertical_centerline_y'][s_]
        env = dict(x=(SLOT['box']['x0'] + 0.2, SLOT['box']['x1'] - 0.2), y=(yc - 0.1015, yc + 0.1015), z=(0.6485, Z_TOP[s_]))
        for q in parts:
            if s_ == 'b' and q['n'] == 'V4_FPC3':
                continue
            d = [max(q[a_][0] - env[a_][1], env[a_][0] - q[a_][1], 0) for a_ in ('x', 'y', 'z')]
            rows.append(dict(tail=s_.upper(), part=q['n'], gap=round(math.sqrt(sum(v * v for v in d)), 3)))
    rows.sort(key=lambda r_: r_['gap'])
    return rows


polys = {}
for s_, b in boards.items():
    ol = k.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol, False); polys[s_] = ol
fxy = {s_: next((p['c'] for p in items(boards[s_])['pads'] if p['ref'] == PIECES[s_][1]), None) for s_ in PIECES}
t_ok, t_info = tail_check(polys, fxy)
tp_rows = tail_vs_parts()
# 反例：A 北支和尾之间的 0.4 缝补上（北支被拉进缝）、B 尾加宽到 y 60（超出缝）
_bridge = {'a': _rp(38.5, 40.0, BEND_X, 42.0)}
neg_t = {}
for name, s_, add in (('A 北支与尾之间缝补上', 'a', _rp(37.0, 40.5, BEND_X + 0.5, 41.6)), ('B 尾加宽到 y 60.0', 'b', _rp(33.0, 58.0, BEND_X + 0.5, 60.0))):
    pp = dict(polys); q_ = k.SHAPE_POLY_SET(polys[s_]); q_.BooleanAdd(add); q_.Simplify(); pp[s_] = q_
    neg_t[name] = not tail_check(pp, fxy)[0]
in_cap = {s_: round(_and(polys[s_], _rp(BEND_X, 0, 76.8, 100)).Area() / 1e12, 2) for s_ in PIECES}
gate('box_height', t_ok and tp_rows[0]['gap'] >= BH_GAP and all(neg_t.values()),
     dict(note='胶囊段在 R13 底壳外（Z ≤ 0.15，底板顶 1.00 以下），D17 底面件（最低 U2 Z 1.24）下方不再有 FPC；壳内只剩两条尾，经 tray_tail_slot 穿底板；'
               '尾竖直段对底面件 ≥ 0.05（B 尾插 V4_FPC3 本身不算）；尾巴插座高度取座子包围盒中线（假设）',
          tray_tail_slot=SLOT['box'], tails=t_info, tail_vs_bottom_parts_min=tp_rows[:4], capsule_area_outside_shell_mm2=in_cap,
          negatives_red=neg_t))

after = {s: hashlib.sha256((HERE / f'strap-{s}.kicad_pcb').read_bytes()).hexdigest() for s in PIECES}
gate('boards_unchanged_by_check', after == report['board_sha256'], dict(note='检查全程只读两块板（反例都在临时副本上做）'))
for prl in HERE.glob('*.kicad_prl'):                           # pcbnew 读板顺手写的本机界面状态，不入库
    prl.unlink()
report['fails'] = fails
(HERE / 'checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k_: v.get('ok') if isinstance(v, dict) and 'ok' in v else v for k_, v in report.items() if k_ != 'board_sha256'}, ensure_ascii=False))
sys.exit(1 if fails else 0)
