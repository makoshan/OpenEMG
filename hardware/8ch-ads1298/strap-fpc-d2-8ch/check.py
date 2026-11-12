"""D2-8CH 单片 8 通道表带软板全部检查（KiCad 自带 python3 运行）：python3 check.py
全部从 strap-d2-8ch.kicad_pcb 文件读回（不用 build.py 内存里的数），写 checks.json、pin-map.json、drc.json、lint.json、
lengths.csv、widths.csv。任一项不过退出码 1，失败项写进 checks.json 的 fails。
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
from metrics import _and, area, backside_tracks, band_stats, cross_section, items, material, measure, pset, ptrect, ptseg  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STEM = 'strap-d2-8ch'
PCB_PATH = HERE / f'{STEM}.kicad_pcb'
R12 = ROOT / 'hardware/16ch-c08b-round/strap-fpc-r15'
R15 = ROOT / 'hardware/16ch-c08b-round/strap-fpc-r15'
D17 = ROOT / 'hardware/16ch-c08b-round/afe-d20/afe-d20-silk.kicad_pcb'
D17_SHA = '313238267216c032e11496a289c3cb21d70863daff151d648592985a3cdcb878'
D20_8CH = ROOT / 'hardware/8ch-ads1298/afe-d20-8ch/afe-d20-8ch.kicad_pcb'
D20N_8CH = ROOT / 'hardware/8ch-ads1298/afe-d20n-8ch/afe-d20n-8ch.kicad_pcb'
LINT = ROOT / 'hardware/16ch-c08b-round/afe-d20/route_lint.py'
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY = sys.executable
MIL = 0.0254
mm = k.ToMM
report = {'status': '已实现未验收：本机 DRC/几何/脚序/对孔/双辅助串阻检查见各项；未打样、未焊铜片、未插实物、未贴肤'}
fails = []


def gate(name, ok, detail):
    report[name] = {**detail, 'ok': bool(ok)} if isinstance(detail, dict) else dict(ok=bool(ok), detail=detail)
    if not ok:
        fails.append(name)


def load_copy(src):
    tmp = Path(tempfile.mkdtemp(prefix='d28chk-'))
    shutil.copy(src, tmp / 'x.kicad_pcb')
    b = k.LoadBoard(str(tmp / 'x.kicad_pcb'))
    shutil.rmtree(tmp)
    return b


board = k.LoadBoard(str(PCB_PATH))
r12_a = load_copy(R12 / 'strap-a.kicad_pcb')
report['board_sha256'] = hashlib.sha256(PCB_PATH.read_bytes()).hexdigest()

# ---------- 1. 脚序：同时从 D17 源板与 D20-8CH / D20N-8CH 源板现推 ----------
d17_sha = hashlib.sha256(D17.read_bytes()).hexdigest()
AUX = {'V4_BIAS_DRV1': 'BIAS_DRV1', 'V4_RLD_OUT2': 'BIAS_DRV12', 'V4_WCT': 'WCT', 'V4_WCT2': 'WCT2', 'AGND': 'AGND'}


def afe_expect(afe_pcb, ref='V4_FPC1'):
    db = load_copy(afe_pcb)
    pins, bynet = {}, {}
    for f in db.GetFootprints():
        for p in f.Pads():
            pins.setdefault(f.GetReference(), {})[p.GetNumber()] = p.GetNetname()
            bynet.setdefault(p.GetNetname(), set()).add((f.GetReference(), p.GetNumber()))
    out = {}
    for n in range(1, 35):
        net = pins[ref][str(n)]
        if net in AUX:
            out[n] = AUX[net]
            continue
        hop = [x for x in bynet[net] if re.fullmatch(r'V4_U(3|4|5|6)', x[0])]
        assert len(hop) == 1, (afe_pcb.name, ref, n, net, hop)
        ar, ap = hop[0]
        far = pins[ar][str(9 - int(ap))]
        adc = [x for x in bynet[far] if x[0] == 'V4_U1']
        m = re.fullmatch(r'V4_IN(\d)([PN])', far)
        assert m and len(adc) == 1, (afe_pcb.name, ref, n, far, adc)
        out[n] = f'CH{int(m[1])}_{m[2]}'
    return out, pins[ref]


def tail_nets(b, ref='TAIL_A'):
    f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    return f, {int(p.GetNumber()): p for p in f.Pads()}


def pin_errors(nets, want):
    return [dict(pin=n, board_net=nets.get(n), expect_net=want[n]) for n in range(1, 35) if nets.get(n) != want[n]]


TAIL_EXT = 1.30
want_d17, raw_d17 = afe_expect(D17)
want_8ch, raw_8ch = afe_expect(D20_8CH)
want_8chn, raw_8chn = afe_expect(D20N_8CH)
_, pads = tail_nets(board)
nets = {n: p.GetNetname() for n, p in pads.items()}
errs_d17 = pin_errors(nets, want_d17)
errs_8ch = pin_errors(nets, want_8ch)
errs_8chn = pin_errors(nets, want_8chn)
_, rpads = tail_nets(r12_a)
r12_diff = [n for n, p in rpads.items() if p.GetNetname() and p.GetNetname() != nets.get(n)]
geo_diff = [n for n, p in rpads.items() if (round(mm(p.GetPosition().x) - TAIL_EXT, 4), round(mm(p.GetPosition().y), 4), round(mm(p.GetSize(k.F_Cu).x), 3), round(mm(p.GetSize(k.F_Cu).y), 3))
            != (round(mm(pads[n].GetPosition().x), 4), round(mm(pads[n].GetPosition().y), 4), round(mm(pads[n].GetSize(k.F_Cu).x), 3), round(mm(pads[n].GetSize(k.F_Cu).y), 3))
            or p.IsOnLayer(k.F_Cu) != pads[n].IsOnLayer(k.F_Cu)]
mirrored = {n: nets[35 - n] for n in nets}
pin_map = dict(connector='V4_FPC1', d17_sha256=d17_sha,
               d20_8ch_sha256=hashlib.sha256(D20_8CH.read_bytes()).hexdigest(),
               d20n_8ch_sha256=hashlib.sha256(D20N_8CH.read_bytes()).hexdigest(),
               table=[dict(pin=n, board_net=nets[n], d17_net=raw_d17[str(n)], d20_8ch_net=raw_8ch[str(n)], expect=want_8ch[n],
                           y=round(mm(pads[n].GetPosition().y), 3)) for n in range(1, 35)])
(HERE / 'pin-map.json').write_text(json.dumps(pin_map, ensure_ascii=False, indent=1))
gate('pins_8ch', not errs_d17 and not errs_8ch and not errs_8chn and len(pads) == 34 and not r12_diff and not geo_diff and d17_sha == D17_SHA,
     dict(connector='V4_FPC1', pads=len(pads), errors_vs_d17=errs_d17, errors_vs_d20_8ch=errs_8ch, errors_vs_d20n_8ch=errs_8chn,
          d17_sha256_ok=d17_sha == D17_SHA, signal_pins_differ_from_r12=r12_diff, finger_geometry_differs_from_r12=geo_diff,
          pin1_y=round(mm(pads[1].GetPosition().y), 3), pin34_y=round(mm(pads[34].GetPosition().y), 3),
          finger_face='F' if all(p.IsOnLayer(k.F_Cu) and not p.IsOnLayer(k.B_Cu) for p in pads.values()) else 'B',
          negative_mirror_errors=len(pin_errors(mirrored, want_8ch))))

# 反例：对调 19/20 脚存盘读回必须报错
tmp = Path(tempfile.mkdtemp(prefix='d28neg-'))
b_sw = k.LoadBoard(str(PCB_PATH))
_, sw_pads = tail_nets(b_sw)
n1, n2 = sw_pads[19].GetNet(), sw_pads[20].GetNet()
sw_pads[19].SetNet(n2); sw_pads[20].SetNet(n1)
k.SaveBoard(str(tmp / 'swap.kicad_pcb'), b_sw)
_, sp = tail_nets(k.LoadBoard(str(tmp / 'swap.kicad_pcb')))
shutil.rmtree(tmp)
e_sw = pin_errors({n: p.GetNetname() for n, p in sp.items()}, want_8ch)
gate('pin_order_negative', len(e_sw) == 2 and report['pins_8ch']['negative_mirror_errors'] > 0,
     dict(swap_19_20_errors=len(e_sw), swap_pins=[x['pin'] for x in e_sw], mirror_errors=report['pins_8ch']['negative_mirror_errors']))

# ---------- 2. 表带 6 路（CH3..CH8）触点与 TPU 层对孔 + 胶囊底 6 触点（含双辅助 200k 串阻、零通孔） ----------
TPU = ROOT / 'hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/build.py'


def tpu_consts():
    want = ('PITCH', 'NORTH_YS', 'SOUTH_YS', 'LAYER_W', 'PN', 'DISC_D', 'HOLE_CLEAR')
    ns = {}
    for node in ast.parse(TPU.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in want:
            exec(compile(ast.Module([node], []), str(TPU), 'exec'), ns)
    return {n: ns[n] for n in want}


TC = tpu_consts()
NORTH_YS_EXPECT = (34.0, 42.0)
SOUTH_YS_8CH = tuple(TC['SOUTH_YS'][:4])      # 南前 4 岛 CH5..CH8
BOX_CH = (1, 2)
STRAP_CH = range(3, 9)
fps = list(board.GetFootprints())
contacts, topo = {}, []
for f in fps:
    m = re.fullmatch(r'E(\d+)([NP])', f.GetReference())
    if not m or int(m[1]) in BOX_CH:
        continue
    (p,) = list(f.Pads())
    contacts[f.GetReference()] = dict(ch=int(m[1]), pol=m[2], x=round(mm(p.GetPosition().x), 4), y=round(mm(p.GetPosition().y), 4),
                                      d=round(mm(p.GetSize(k.F_Cu).x), 4), circle=p.GetShape() == k.PAD_SHAPE_CIRCLE,
                                      smd=p.GetAttribute() == k.PAD_ATTRIB_SMD, drill=round(mm(p.GetDrillSize().x), 4),
                                      layers=sorted(board.GetLayerName(L) for L in p.GetLayerSet().Seq()),
                                      mask_margin=round(mm(p.GetLocalSolderMaskMargin() or 0), 4), net=p.GetNetname())
for ch in range(1, 9):
    for pol in 'NP':
        t, e = f'CH{ch}_{pol}', f'CH{ch}_{pol}_E'
        rs = [f for f in fps if {p.GetNetname() for p in f.Pads()} == {t, e}]
        es = [f for f in fps if f.GetReference() == f'E{ch}{pol}' and [p.GetNetname() for p in f.Pads()] == [e]]
        if len(rs) != 1 or len(es) != 1 or rs[0].GetValue() != '100k' or rs[0].GetLayerName() != ('B.Cu' if ch in BOX_CH else 'F.Cu'):
            topo.append(dict(net=t, resistors=len(rs), contacts=len(es)))
bad_pad = {r: c for r, c in contacts.items() if not (c['circle'] and c['smd'] and c['d'] == 6.5 and c['drill'] == 0
                                                     and c['layers'] == ['F.Cu', 'F.Mask', 'F.Paste'] and c['mask_margin'] == 0)}
pair_sp = {ch: round(contacts[f'E{ch}P']['y'] - contacts[f'E{ch}N']['y'], 4) for ch in STRAP_CH}
pcb_mask_margin = round(mm(board.GetDesignSettings().m_SolderMaskExpansion), 4)
n_res_total = sum(1 for f in fps if f.GetReference().startswith('R'))
gate('contacts_d2_8ch', len(contacts) == 12 and not bad_pad and not topo and all(v == 18.0 for v in pair_sp.values())
     and all(contacts[f'E{ch}N']['y'] == 41.0 for ch in STRAP_CH) and pcb_mask_margin == 0 and n_res_total == 18,
     dict(strap_contacts=len(contacts), total_resistors=n_res_total, bad_pads=bad_pad, topology_errors=topo,
          pair_spacing_mm=pair_sp, board_mask_margin=pcb_mask_margin))

holes_8ch = [(sx * TC['PN'] / 2, Y) for Y in NORTH_YS_EXPECT + SOUTH_YS_8CH for sx in (-1, 1)]
pairs, used = [], set()
for ref, c in sorted(contacts.items()):
    X, Y = 50.0 - c['y'], 58.0 - c['x']
    i, h = min(enumerate(holes_8ch), key=lambda t: math.dist(t[1], (X, Y)))
    used.add(i)
    pairs.append(dict(ref=ref, strap_xy=[round(X, 4), round(Y, 4)], hole=[h[0], h[1]], err_mm=round(math.dist(h, (X, Y)), 5)))
worst_al = max(p['err_mm'] for p in pairs)
gate('tpu_hole_alignment_8ch', len(pairs) == 12 and len(used) == len(holes_8ch) == 12 and worst_al <= 0.01,
     dict(tpu_build=str(TPU.relative_to(ROOT)), holes_8ch=len(holes_8ch), matched=len(used), worst_err_mm=worst_al, table=pairs))

# 胶囊底 6 触点 + 6 串阻核对（全部在单片 'a' 上，EB1/EB2 都是无孔实心 F.Cu Φ4.5 SMD，R33/R34 都是 B.Cu 200k 接 BIAS_DRV1）
r15 = {'a': load_copy(R15 / 'strap-a.kicad_pcb'), 'b': load_copy(R15 / 'strap-b.kicad_pcb')}
BOX_D = {'E1N': 6.5, 'E1P': 6.5, 'E2N': 6.5, 'E2P': 6.5, 'EB1': 4.5, 'EB2': 4.5}
EXPECT_PAD_NET = {'E1N': 'CH1_N_E', 'E1P': 'CH1_P_E', 'E2N': 'CH2_N_E', 'E2P': 'CH2_P_E', 'EB1': 'BIAS_DRV1_E', 'EB2': 'BIAS_DRV1_EB2_E'}
EXPECT_RES = {
    'R1': ('100k', {'CH1_P', 'CH1_P_E'}, 'a'),
    'R2': ('100k', {'CH1_N', 'CH1_N_E'}, 'a'),
    'R3': ('100k', {'CH2_P', 'CH2_P_E'}, 'a'),
    'R4': ('100k', {'CH2_N', 'CH2_N_E'}, 'a'),
    'R33': ('200k', {'BIAS_DRV1', 'BIAS_DRV1_E'}, 'a'),
    'R34': ('200k', {'BIAS_DRV1', 'BIAS_DRV1_EB2_E'}, 'b'),
}


def fpd(b):
    return {f.GetReference(): f for f in b.GetFootprints()}


def box_cmp_8ch(b):
    bad, moved, rows = [], {}, []
    here = fpd(b)
    if 'EB2A' in here:
        bad.append('残留双片对焊件 EB2A')
    for ref, dia in BOX_D.items():
        r15_side = 'b' if ref == 'EB2' else 'a'
        f, o = here.get(ref), fpd(r15[r15_side])[ref]
        if f is None or len(list(f.Pads())) != 1:
            bad.append(f'{ref} 缺'); continue
        (p,), (q,) = list(f.Pads()), list(o.Pads())
        err = math.dist((mm(p.GetPosition().x), mm(p.GetPosition().y)), (mm(q.GetPosition().x), mm(q.GetPosition().y)))
        lay = sorted(b.GetLayerName(L) for L in p.GetLayerSet().Seq())
        ok = (err <= 0.01 and p.GetNetname() == EXPECT_PAD_NET[ref]
              and p.GetShape() == k.PAD_SHAPE_CIRCLE and p.GetAttribute() == k.PAD_ATTRIB_SMD
              and round(mm(p.GetSize(k.F_Cu).x), 4) == dia and round(mm(p.GetSize(k.F_Cu).y), 4) == dia
              and mm(p.GetDrillSize().x) == 0 and lay == ['F.Cu', 'F.Mask', 'F.Paste']
              and (p.GetLocalSolderMaskMargin() or 0) == 0)
        rows.append(dict(ref=ref, net=p.GetNetname(), board=[round(mm(p.GetPosition().x), 4), round(mm(p.GetPosition().y), 4)],
                         err_vs_r15_mm=round(err, 5), d=round(mm(p.GetSize(k.F_Cu).x), 4), drill=round(mm(p.GetDrillSize().x), 4), layers=lay))
        if not ok:
            bad.append(ref)
    for ref, (val, exp_nets, r15_side) in EXPECT_RES.items():
        f, o = here.get(ref), fpd(r15[r15_side])[ref]
        if f is None:
            bad.append(f'{ref} 缺'); continue
        nets_here = {p.GetNetname() for p in f.Pads()}
        at_xy = [round(mm(f.GetPosition().x), 4), round(mm(f.GetPosition().y), 4)]
        ang = round(f.GetOrientationDegrees() % 180.0, 3)
        if f.GetValue() != val or nets_here != exp_nets or f.GetLayerName() != 'B.Cu' or len(list(f.Pads())) != 2:
            bad.append(ref)
        if ref == 'R34' and (at_xy != [45.5, 50.0] or ang != 0.0):
            bad.append(f'R34 位置或角度偏:{at_xy}/{ang}')
        moved[ref] = dict(value=f.GetValue(), nets=sorted(nets_here), layer=f.GetLayerName(),
                          at=at_xy, angle_deg=round(f.GetOrientationDegrees(), 3),
                          r15_at=[round(mm(o.GetPosition().x), 4), round(mm(o.GetPosition().y), 4)])
    pth_pads = [f'{f.GetReference()}.{p.GetNumber()}' for f in b.GetFootprints() for p in f.Pads() if mm(p.GetDrillSize().x) > 0]
    if pth_pads:
        bad.append(f'存在带孔焊盘:{pth_pads}')
    return dict(ok=not bad and len(rows) == 6 and len(moved) == 6, bad=bad, contacts=rows, resistors=moved)


def _bx_edit(fn):
    tmp_ = Path(tempfile.mkdtemp(prefix='d28box-'))
    b_ = k.LoadBoard(str(PCB_PATH))
    fn(b_)
    k.SaveBoard(str(tmp_ / 'x.kicad_pcb'), b_)
    nb_ = k.LoadBoard(str(tmp_ / 'x.kicad_pcb'))
    shutil.rmtree(tmp_)
    return nb_


def _neg_eb2_pth(b_):
    p = next(iter(fpd(b_)['EB2'].Pads()))
    p.SetAttribute(k.PAD_ATTRIB_PTH)
    p.SetDrillSize(k.VECTOR2I(k.FromMM(0.8), k.FromMM(0.8)))


def _neg_r34_val(b_):
    fpd(b_)['R34'].SetValue('100k')


def _neg_r34_net(b_):
    p = next(p for p in fpd(b_)['R34'].Pads() if p.GetNetname() == 'BIAS_DRV1')
    p.SetNet(b_.FindNet('AGND'))


def _neg_e1n_move(b_):
    f = fpd(b_)['E1N']
    f.SetPosition(k.VECTOR2I(f.GetPosition().x + k.FromMM(0.05), f.GetPosition().y))


def _neg_r34_move(b_):
    f = fpd(b_)['R34']
    f.SetPosition(k.VECTOR2I(f.GetPosition().x + k.FromMM(0.2), f.GetPosition().y))


box = box_cmp_8ch(board)
neg_box = {
    'EB2 改回 Φ0.8 通孔': not box_cmp_8ch(_bx_edit(_neg_eb2_pth))['ok'],
    'R34 阻值改 100k': not box_cmp_8ch(_bx_edit(_neg_r34_val))['ok'],
    'R34 尾侧改接 AGND': not box_cmp_8ch(_bx_edit(_neg_r34_net))['ok'],
    'E1N 右移 0.05': not box_cmp_8ch(_bx_edit(_neg_e1n_move))['ok'],
    'R34 右移 0.20': not box_cmp_8ch(_bx_edit(_neg_r34_move))['ok'],
}
gate('box_capsule_6pads_dual_bias', box['ok'] and all(neg_box.values()), dict(box, negatives_red=neg_box))

# 尾部几何与 R12 比对
ia, ir = items(board), items(r12_a)
fa = [p for p in ia['pads'] if p['ref'] == 'TAIL_A']
tip = round(min(p['rect'][0] for p in fa) - 0.2, 3)
wa = next(s_ for s_ in cross_section(ia, tip + 1.0)[0] if s_[0] < 50 < s_[1])
tip_r = round(min(p['rect'][0] for p in ir['pads'] if p['ref'] == 'TAIL_A') - 0.2, 3)
wr = next(s_ for s_ in cross_section(ir, tip_r + 1.0)[0] if s_[0] < 50 < s_[1])
ring = [r for r in ia['rings']['User.2'] if abs(min(x for x, _ in r) - tip) < 1e-3]
st_len = round(max(x for x, _ in ring[0]) - min(x for x, _ in ring[0]), 3) if ring else None
ext_mm = round(tip_r - tip, 3)
gate('tail_vs_r12', round(wa[1] - wa[0], 3) == round(wr[1] - wr[0], 3) == 17.5 and st_len == 2.5 and ext_mm == TAIL_EXT,
     dict(tip_x=tip, tip_x_r12=tip_r, extension_mm=ext_mm, width_mm=round(wa[1] - wa[0], 3), stiffener_len=st_len))

# ---------- 3. DRC（原样 + 重铺 + 反例） ----------


def drc(board_path, out, refill=False):
    subprocess.run([KC, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors', *(['--refill-zones'] if refill else []), '-o', str(out), str(board_path)],
                   check=True, capture_output=True)
    return json.loads(Path(out).read_text())


d = drc(PCB_PATH, HERE / 'drc.json')
tmp = Path(tempfile.mkdtemp(prefix='d28drc-'))
rf = drc(PCB_PATH, tmp / 'refill.json', refill=True)
shutil.rmtree(tmp)
gate('drc_8ch', not d['violations'] and not d['unconnected_items'] and not rf['violations'] and not rf['unconnected_items'],
     dict(violations=len(d['violations']), unconnected=len(d['unconnected_items']), kicad=d.get('kicad_version'),
          after_refill_zones=dict(violations=len(rf['violations']), unconnected=len(rf['unconnected_items']))))


def negative(edit):
    tmp_ = Path(tempfile.mkdtemp(prefix='d28negdrc-'))
    for ext in ('kicad_pro', 'kicad_dru'):
        shutil.copy(HERE / f'{STEM}.{ext}', tmp_ / f'{STEM}.{ext}')
    b_ = k.LoadBoard(str(PCB_PATH))
    edit(b_)
    k.SaveBoard(str(tmp_ / f'{STEM}.kicad_pcb'), b_)
    dd = drc(tmp_ / f'{STEM}.kicad_pcb', tmp_ / 'drc.json')
    shutil.rmtree(tmp_)
    return sorted({v['type'] + (' :' + re.search(r"'([^']+)'", v['description'])[1] if "'" in v['description'] else '') for v in dd['violations']})


def add_track(b_, net, pts, layer=k.F_Cu):
    for a, z in zip(pts, pts[1:]):
        t = k.PCB_TRACK(b_)
        t.SetStart(k.VECTOR2I(k.FromMM(a[0]), k.FromMM(a[1]))); t.SetEnd(k.VECTOR2I(k.FromMM(z[0]), k.FromMM(z[1])))
        t.SetWidth(k.FromMM(0.15)); t.SetLayer(layer); t.SetNet(b_.FindNet(net)); b_.Add(t)


def add_via(b_, net, p):
    v = k.PCB_VIA(b_)
    v.SetPosition(k.VECTOR2I(k.FromMM(p[0]), k.FromMM(p[1]))); v.SetWidth(k.FromMM(0.5)); v.SetDrill(k.FromMM(0.25))
    v.SetLayerPair(k.F_Cu, k.B_Cu); v.SetNet(b_.FindNet(net)); b_.Add(v)


def lane_y(x, net):
    return next(h[0] for h in cross_section(ia, x)[1] if h[1] == net and h[2] == 'F.Cu')


yp, yn = lane_y(80.0, 'CH5_P'), lane_y(80.0, 'CH5_N')
y5n, y6p = lane_y(80.0, 'CH5_N'), lane_y(80.0, 'CH6_P')


def jog(c):
    yj = y6p - c
    e = yj - y5n
    return lambda b_: add_track(b_, 'CH5_N', [(80.0, y5n), (80.0 + e, yj), (82.0 - e, yj), (82.0, y5n)])


ys_br = sorted(h[0] for h in cross_section(ia, 94.0)[1] if h[2] == 'F.Cu')
gap_br = max(zip(ys_br, ys_br[1:]), key=lambda t: t[1] - t[0])
negs = {
    'short_CH5_N_to_CH5_P': negative(lambda b_: add_track(b_, 'CH5_N', [(80.0, yn), (80.0, yp)])),
    'center_0.40_CH5_N_vs_CH6_P': negative(jog(0.40)),
    'positive_center_0.47_same_place': negative(jog(0.47)),
    'via_in_dynamic_A_bridge1': negative(lambda b_: add_via(b_, 'AGND', (94.0, round((gap_br[0] + gap_br[1]) / 2, 3)))),
}
neg_ok = (bool({'shorting_items', 'tracks_crossing'} & {x.split(' ')[0] for x in negs['short_CH5_N_to_CH5_P']})
          and any('中心距0.47' in x for x in negs['center_0.40_CH5_N_vs_CH6_P'])
          and not any('中心距0.47' in x for x in negs['positive_center_0.47_same_place'])
          and any(x.startswith('items_not_allowed') for x in negs['via_in_dynamic_A_bridge1']))
gate('drc_negative_controls', neg_ok, negs)

# ---------- 4. route_lint ----------
hard = ('odd_angle', 'sharp', 'tee_acute', 'width_jump', 'dangling', 'pad_exit', 'multi_width')
subprocess.run([KPY, str(LINT), str(PCB_PATH), str(HERE / 'lint.json')], check=True, capture_output=True)
L = json.loads((HERE / 'lint.json').read_text())['summary']
gate('route_lint_8ch', sum(L[h] for h in hard) == 0,
     dict(hard=sum(L[h] for h in hard), hard_items={h: L[h] for h in hard},
          report_only={x: L[x] for x in ('pad_exit_side', 'tee_90', 'pad_exit_rotated')}))

# ---------- 5. 分段等长 ----------
L_map = {}
for t in board.GetTracks():
    if t.GetClass() == 'PCB_TRACK':
        L_map[t.GetNetname()] = L_map.get(t.GetNetname(), 0) + mm(t.GetLength())
rows = []
for ch in range(1, 9):
    for seg, suf in (('尾→串阻', ''), ('串阻→触点', '_E')):
        p, n = L_map[f'CH{ch}_P{suf}'], L_map[f'CH{ch}_N{suf}']
        rows.append(dict(ch=ch, segment=seg, P_mm=round(p, 4), N_mm=round(n, 4), diff_mm=round(p - n, 4), diff_mil=round((p - n) / MIL, 3)))
with (HERE / 'lengths.csv').open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
worst = max(rows, key=lambda r: abs(r['diff_mil']))
gate('length_match', abs(worst['diff_mil']) <= 10 and len(rows) == 16,
     dict(segments=len(rows), worst_diff_mil=worst['diff_mil'], worst_at=f"CH{worst['ch']} {worst['segment']}", limit_mil=10))

# ---------- 6. 几何、补强、网格地、零盘中孔 ----------
m = measure(board)
g = m['geometry']
gate('geometry_8ch', g['min_center_between_different_nets_mm'] >= 0.47 - 1e-4 and g['min_center_within_pair_mm'] >= 0.30 - 1e-4
     and g['min_track_copper_to_outline_mm'] >= 0.305 - 1e-4 and (g['min_track_copper_to_hole_edge_mm'] or 9) >= 0.305 - 1e-4
     and g['min_via_copper_to_outline_mm'] >= 0.305 - 1e-4 and g['vias_in_dynamic_zones'] == 0 and g['track_widths'] == [0.15], g)
t_tail = m['tail']
gate('tail_vias_8ch', t_tail['via_copper_to_finger_copper_mm'] >= 0.3 and t_tail['via_hole_edge_to_finger_pad_mm'] >= 0.2, t_tail)
st = m['stiffener']
isl = st['layers'].get('User.2', {})
stiff_mat = material(ia['rings']['User.2'])
stiff_outside_mm2 = round(max(0.0, area(stiff_mat) - area(_and(stiff_mat, ia['board']))), 5)
gate('stiffener_8ch', st['fingers_backed_on_opposite_face'] and isl.get('pieces') == 14
     and isl.get('island_contacts_backed') == 18 and (isl.get('min_contact_coverage') or 0) >= 0.80
     and isl.get('res_pads_covered') == 0 and stiff_outside_mm2 <= 1e-4,
     dict(st, outside_outline_mm2=stiff_outside_mm2))
me = m['mesh']
gate('gnd_planes_8ch', all(v['orphan_pieces'] == 0 and v['pieces_under_0p5mm2'] == 0 and v['voids_narrower_than_0p15'] == 0
                           and 0.40 <= v['min_copper_vs_copperable'] and v['max_copper_vs_copperable'] <= 0.62 for v in me.values()), me)
cps = [p for p in ia['pads'] if p['circle'] and p['r'] > 2]
edge = min(min(ptseg(p['c'], a, z) for a, z in ia['segs']) - p['r'] for p in cps)
vip = min(((math.dist(v['c'], p['c']) - p['r'] - v['r'], v, p) for v in ia['vias'] for p in cps), key=lambda t: t[0])
vip_r = min(((ptrect(v['c'], p['rect']) - v['r'], v, p) for v in ia['vias'] for p in ia['pads'] if not p['circle']), key=lambda t: t[0])
gate('pad_edge_and_no_via_in_pad_8ch', edge >= 0.3 - 1e-4 and vip[0] >= 0.15 and vip_r[0] >= 0.15,
     dict(contact_pad_to_outline_min_mm=round(edge, 4), via_to_contact_pad_min_mm=round(vip[0], 4),
          nearest_contact=f"{vip[2]['ref']}", via_to_rect_pad_min_mm=round(vip_r[0], 4), nearest_rect=f"{vip_r[2]['ref']}.{vip_r[2]['num']}"))

# ---------- 7. 截面报告 ----------
SEC = [('尾（插接尾，折弯区）', 35.0, 50.0), ('北支', 33.0, 39.0), ('北岛间 CH4|CH3', 20.1, 39.0),
       ('出盒带（带根）', 80.0, 53.0), ('桥1（CH5|CH6）', 94.1, 53.0), ('桥2', 102.1, 53.0), ('桥3', 110.1, 53.0)]
wrows = []
for name, x, yref in SEC:
    a_ = band_stats(ia, x, yref)
    lay = [a_[L] for L in ('F.Cu', 'B.Cu') if L in a_]
    wrows.append(dict(segment=name, x=x, y=f"{a_['y0']}–{a_['y1']}", width=a_['width'], pairs=sum(v['pairs'] for v in lay)))
with (HERE / 'widths.csv').open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(wrows[0]), lineterminator='\n'); w.writeheader(); w.writerows(wrows)

# ---------- 8. 表带侧 6 岛等高 & 皮肤侧串阻槽 ----------
H0402 = 0.35
BODY0402 = (1.0, 0.5)
POCKET_M = 0.3
KEEP_PAD = 0.25


def strapside_8ch(b_):
    it_ = items(b_)
    ts = [float(m_[1]) for dr in b_.GetDrawings() if dr.GetClass() == 'PCB_TEXT'
          for m_ in [re.search(r'触点背面 PI 补强 Φ[\d.]+ 厚 ([\d.]+)', dr.GetText())] if m_]
    t_pi = ts[0]
    stiff = material(it_['rings']['User.2'])
    ys_ = [y for _, y in it_['outline']]
    discs = [r for r in it_['rings']['User.2'] if abs((max(x for x, _ in r) - min(x for x, _ in r)) - (max(y for _, y in r) - min(y for _, y in r))) < 0.01]
    hw = max((max(x for x, _ in r) - min(x for x, _ in r)) / 2 for r in discs)
    rows_, comps = [], []
    for f in b_.GetFootprints():
        m_ = re.fullmatch(r'E(\d+)N', f.GetReference())
        if not m_ or int(m_[1]) in BOX_CH:
            continue
        ch = int(m_[1])
        cx = mm(f.GetPosition().x)
        x0, y0, x1, y1 = cx - hw, min(ys_), cx + hw, max(ys_)
        r = pset([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        parts = []
        if area(_and(stiff, r)) > 1e-3:
            parts.append(t_pi)
        for fp_ in b_.GetFootprints():
            if fp_.GetLayer() == k.B_Cu and any(ptrect((mm(p.GetPosition().x), mm(p.GetPosition().y)), (x0, y0, x1, y1)) == 0 for p in fp_.Pads()):
                parts.append(H0402); comps.append(fp_.GetReference())
        rows_.append(max(parts, default=0.0))
    for fp_ in b_.GetFootprints():
        if fp_.GetLayer() == k.B_Cu and mm(fp_.GetPosition().x) >= 75.0 and fp_.GetReference() not in comps:
            comps.append(fp_.GetReference())
    return dict(islands=len(rows_), spread_mm=round(max(rows_) - min(rows_), 4), top_mm=max(rows_), comps=comps)


flat = strapside_8ch(board)
neg_flat_ok = bool(strapside_8ch(_bx_edit(lambda b_: fpd(b_)['R10'].SetLayerAndFlip(k.B_Cu)))['comps'])
gate('strapside_flat_8ch', flat['islands'] == 6 and flat['spread_mm'] <= 0.01 and not flat['comps'] and neg_flat_ok,
     dict(flat, negative_flip_r10_caught=neg_flat_ok))


def res_pockets_8ch(b_):
    out, worst_ = [], (9.0, None)
    contacts_ = [(f.GetReference(), (mm(f.GetPosition().x), mm(f.GetPosition().y)), mm(next(iter(f.Pads())).GetSize(k.F_Cu).x) / 2)
                 for f in b_.GetFootprints() if re.fullmatch(r'E\d+[NP]', f.GetReference())]
    for f in b_.GetFootprints():
        if not (f.GetReference().startswith('R') and f.GetValue() == '100k' and f.GetLayer() == k.F_Cu):
            continue
        pads_ = list(f.Pads())
        bbs = [p.GetBoundingBox() for p in pads_]
        x0, y0 = min(mm(q.GetLeft()) for q in bbs), min(mm(q.GetTop()) for q in bbs)
        x1, y1 = max(mm(q.GetRight()) for q in bbs), max(mm(q.GetBottom()) for q in bbs)
        cx, cy = mm(f.GetPosition().x), mm(f.GetPosition().y)
        x0, y0, x1, y1 = min(x0, cx - 0.5), min(y0, cy - 0.25), max(x1, cx + 0.5), max(y1, cy + 0.25)
        pk = (round(x0 - POCKET_M, 4), round(y0 - POCKET_M, 4), round(x1 + POCKET_M, 4), round(y1 + POCKET_M, 4))
        gaps = sorted((round(ptrect(c, pk) - r, 4), ref) for ref, c, r in contacts_)
        out.append(dict(ref=f.GetReference(), pocket_board=list(pk), gap_to_contact_pad_mm=gaps[0][0], nearest_contact=gaps[0][1]))
        if gaps[0][0] < worst_[0]:
            worst_ = (gaps[0][0], f"{f.GetReference()}->{gaps[0][1]}")
    return out, worst_


pk_rows, pk_worst = res_pockets_8ch(board)
_, neg_w = res_pockets_8ch(_bx_edit(lambda b_: fpd(b_)['R10'].SetPosition(k.VECTOR2I(fpd(b_)['R10'].GetPosition().x, fpd(b_)['R10'].GetPosition().y - k.FromMM(0.8)))))
gate('skinside_res_envelope_8ch', len(pk_rows) == 12 and pk_worst[0] >= KEEP_PAD - 1e-9 and neg_w[0] < KEEP_PAD,
     dict(pockets=len(pk_rows), worst_gap_mm=pk_worst[0], worst_at=pk_worst[1], negative_move_r10_gap_mm=neg_w[0]))
geo_path = HERE / 'geometry.json'
geo = json.loads(geo_path.read_text())
geo['f_res_pockets'] = dict(margin_mm=POCKET_M, part_height_mm=H0402, keep_from_pad_mm=KEEP_PAD, rects=pk_rows)
geo_path.write_text(json.dumps(geo, ensure_ascii=False, indent=1))

# ---------- 9. 穿壳缝检查 ----------
SLOT = geo['tray_tail_slot']
BEND_X = SLOT['board_x_of_bend_start']


def _rp(x0, y0, x1, y1):
    s_ = k.SHAPE_POLY_SET(); s_.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        s_.Append(round(x * 1e6), round(y * 1e6))
    return s_


ol_poly = k.SHAPE_POLY_SET(); board.GetBoardPolygonOutlines(ol_poly, False)
fxy = next(p['c'] for p in ia['pads'] if p['ref'] == 'TAIL_A')


def tail_slot_ok(P):
    north = _and(P, _rp(0, 0, BEND_X, 100)); north.Simplify()
    tails = []
    for i in range(north.OutlineCount()):
        ring = [(north.Outline(i).CPoint(j).x / 1e6, north.Outline(i).CPoint(j).y / 1e6) for j in range(north.Outline(i).PointCount())]
        one_ = k.SHAPE_POLY_SET(); one_.AddOutline(north.Outline(i))
        if one_.Contains(k.VECTOR2I(round(fxy[0] * 1e6), round(fxy[1] * 1e6))):
            at_bend = [y for x, y in ring if abs(x - BEND_X) < 1e-3]
            tails.append([round(min(at_bend) - 50, 3), round(max(at_bend) - 50, 3)] if at_bend else None)
    return len(tails) == 1 and tails[0] is not None and SLOT['box']['x0'] <= tails[0][0] and tails[0][1] <= SLOT['box']['x1']


q_bad = k.SHAPE_POLY_SET(ol_poly); q_bad.BooleanAdd(_rp(37.0, 40.5, BEND_X + 0.5, 41.6)); q_bad.Simplify()
gate('tray_tail_slot_8ch', tail_slot_ok(ol_poly) and not tail_slot_ok(q_bad),
     dict(slot_box=SLOT['box'], negative_bridge_slit_red=not tail_slot_ok(q_bad)))

# ---------- 10. 胶囊段 Z 轴叠层与现成 tray_d2 浅槽净空（防单片无垫片 0.153 mm 撞壳） ----------
D2_16CH_GEO = json.loads((ROOT / 'hardware/16ch-c08b-round/strap-fpc-d2/geometry.json').read_text())
TRAY_D2_Z = {r['ref']: r['pocket_z'][1] for r in D2_16CH_GEO['capsule_res_pockets']['rects']}


def capsule_z_check(b_):
    it_ = items(b_)
    ts = [float(m_[1]) for dr in b_.GetDrawings() if dr.GetClass() == 'PCB_TEXT'
          for m_ in [re.search(r'触点背面 PI 补强 Φ[\d.]+ 厚 ([\d.]+)', dr.GetText())] if m_]
    t_pi = ts[0] if ts else 0.0
    cap_zone = _rp(41.0, 36.5, 75.0, 63.5)
    cap_stiff = _and(material(it_['rings']['User.2']), cap_zone)
    cap_area = round(area(cap_stiff), 2)
    has_spacer = cap_area >= 500.0
    fpc_back_pressed = round(0.150 - (t_pi if has_spacer else 0.0), 4)
    body_wh = {'200k': (1.6, 0.8), '100k': (1.0, 0.5)}
    rows_z, worst_clr, res_hit_mm2 = [], 9.0, 0.0
    for ref in ('R1', 'R2', 'R3', 'R4', 'R33', 'R34'):
        f = fpd(b_)[ref]
        val = f.GetValue()
        h = 0.45 if val == '200k' else 0.35
        bl, bw = body_wh[val]
        cx, cy = mm(f.GetPosition().x), mm(f.GetPosition().y)
        bbs = [p.GetBoundingBox() for p in f.Pads()]
        x0 = min([mm(q.GetLeft()) for q in bbs] + [cx - bl / 2])
        x1 = max([mm(q.GetRight()) for q in bbs] + [cx + bl / 2])
        y0 = min([mm(q.GetTop()) for q in bbs] + [cy - bw / 2])
        y1 = max([mm(q.GetBottom()) for q in bbs] + [cy + bw / 2])
        res_hit_mm2 += area(_and(cap_stiff, _rp(x0, y0, x1, y1)))
        top_z = round(fpc_back_pressed + h, 4)
        clr = round(TRAY_D2_Z[ref] - top_z, 4)
        worst_clr = min(worst_clr, clr)
        rows_z.append(dict(ref=ref, part_top_z_pressed=top_z, tray_d2_pocket_z=TRAY_D2_Z[ref], clearance_mm=clr))
    ok_z = has_spacer and res_hit_mm2 <= 1e-5 and worst_clr >= 0.045
    return dict(ok=ok_z, spacer_area_mm2=cap_area, fpc_back_pressed_z=fpc_back_pressed,
                res_body_pad_overlap_mm2=round(res_hit_mm2, 6), worst_clearance_mm=worst_clr, resistors=rows_z)


def _neg_drop_cap_spacer(b_):
    for dr in list(b_.GetDrawings()):
        if dr.GetClass() == 'PCB_SHAPE' and dr.GetLayer() == k.User_2 and dr.GetShape() == k.SHAPE_T_POLY:
            pts = [(dr.GetPolyShape().Outline(0).CPoint(i).x / 1e6) for i in range(dr.GetPolyShape().Outline(0).PointCount())]
            if pts and 41.0 <= min(pts) and max(pts) <= 75.0:
                b_.Remove(dr)


cz = capsule_z_check(board)
cz_neg = capsule_z_check(_bx_edit(_neg_drop_cap_spacer))
gate('capsule_z_stack_vs_tray_d2', cz['ok'] and not cz_neg['ok'] and cz_neg['worst_clearance_mm'] < -0.10,
     dict(cz, negative_without_spacer_worst_clearance_mm=cz_neg['worst_clearance_mm'], negative_caught=not cz_neg['ok']))

after_sha = hashlib.sha256(PCB_PATH.read_bytes()).hexdigest()
gate('board_unchanged_by_check', after_sha == report['board_sha256'], dict(sha256=after_sha))
for prl in HERE.glob('*.kicad_prl'):
    prl.unlink()
report['fails'] = fails
(HERE / 'checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k_: v.get('ok') if isinstance(v, dict) and 'ok' in v else v for k_, v in report.items() if k_ != 'board_sha256'}, ensure_ascii=False))
sys.exit(1 if fails else 0)
