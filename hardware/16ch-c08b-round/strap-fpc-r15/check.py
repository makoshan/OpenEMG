"""R14 全部检查（KiCad 自带 python3 运行）：python3 check.py
全部从 strap-a/b.kicad_pcb 文件读回（不用 build.py 内存里的数），写 checks.json、pin-map.json、drc-a/b.json、lint-a/b.json、
lengths.csv、widths.csv。任一项不过退出码 1，失败项写进 checks.json 的 fails。
1. 脚序：每片 34 根金手指的网 == 从 D17 源板现推的网（V4_FPC1/V4_FPC3 → 15k 阵列 → ADS1298 输入 → CHn_P/N）；
   并与 R12 金手指逐脚比对。反例：对调两根金手指存盘再读，必须报 2 脚错；整排镜像必须报错。
2. 触点、串阻：位置、焊盘、网名与 R12 逐个相同；每路尾侧网经 100k 到电极侧网，辅助 200k。尾尖、尾宽、金手指、补强长度同 R12。
3. KiCad DRC（工程 .kicad_dru）0 违规 0 未连。反例：P/N 短路、两对中心距 0.40（3W 规则）、动态区过孔，必须报出；
   阳性对照：同一处中心距 0.47 不报 3W。
4. route_lint 硬项 0。
5. 分段等长：尾侧 CHn_P/CHn_N、电极侧 CHn_P_E/CHn_N_E 各自差 ≤ 10 mil。
6. 几何：不同网走线最小中心距 ≥0.47、对内 ≥0.30、走线铜到板边 ≥0.305、动态区过孔 0、尾部过孔到金手指、
   串阻焊盘到触点焊盘（与 R12 同值）、岛补强盖满触点、GND 平面孤铜/碎块/碎孔 0、动态区实铜比例。
7. 各段带宽与 R12 逐段对比（同一 x 截面），每段 ≥ R12；同一 TPU 槽 A+B 合计宽 > R12。B 叠在 A 上方时不压 A 的串阻/触点。
"""
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew as k

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import backside_tracks, band_stats, cross_section, items, measure, res_web, stack_gap  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R12 = HERE
D17 = HERE.parent / 'afe-d20/afe-d20-silk.kicad_pcb'
D17_SHA = '87a6863f5c5b5d8de2264e6370b0c6d1670f891305c9b7820c71986956f011cb'
LINT = HERE.parent / 'afe-d20/route_lint.py'
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY = sys.executable
MIL = 0.0254
PIECES = {'a': ('V4_FPC1', 'TAIL_A'), 'b': ('V4_FPC3', 'TAIL_B')}
mm = k.ToMM
report = {'status': '已实现未验收：本机 DRC/几何/脚序检查结果见各项；未打样、未插实物、未贴肤'}
fails = []


def gate(name, ok, detail):
    report[name] = dict(ok=bool(ok), **detail) if isinstance(detail, dict) else dict(ok=bool(ok), detail=detail)
    if not ok:
        fails.append(name)


def load_copy(src):
    tmp = Path(tempfile.mkdtemp(prefix='r14chk-'))
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


pin_map = {}
for s, (ref, tref) in PIECES.items():
    want = d17_expect(ref)
    f, pads = tail_nets(boards[s], tref)
    nets = {n: p.GetNetname() for n, p in pads.items()}
    errs = pin_errors(nets, want)
    _, rpads = tail_nets(r12[s], tref)
    r12_diff = [n for n, p in rpads.items() if p.GetNetname() and p.GetNetname() != nets.get(n)]
    geo_diff = [n for n, p in rpads.items() if (round(mm(p.GetPosition().x), 4), round(mm(p.GetPosition().y), 4), round(mm(p.GetSize(k.F_Cu).x), 3), round(mm(p.GetSize(k.F_Cu).y), 3))
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
    tmp = Path(tempfile.mkdtemp(prefix='r14neg-'))
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

# ---------- 2. 触点、串阻、尾部与 R12 ----------


def fp_sig(b, shift_ext_to_r12=False):
    out = {}
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref.startswith('TAIL'):
            continue
        fy = round(mm(f.GetPosition().y), 3)
        raw_pads = list(f.Pads())
        is_ext = any(re.match(r'^CH([3-9]|1\d)_', p.GetNetname()) for p in raw_pads)
        dy = (1.0 if fy < 50.0 else -1.0) if (shift_ext_to_r12 and is_ext) else 0.0
        out[ref] = dict(at=(round(mm(f.GetPosition().x), 3), round(fy + dy, 3)),
                        raw_at=(round(mm(f.GetPosition().x), 3), fy),
                        is_ext=is_ext,
                        layer=f.GetLayerName(), value=f.GetValue(),
                        pads=sorted((p.GetNumber(), p.GetNetname(), round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y) + dy, 3),
                                     round(mm(p.GetBoundingBox().GetWidth()), 3), round(mm(p.GetBoundingBox().GetHeight()), 3)) for p in raw_pads))
    return out


diff, topo, counts = {}, [], {}
box_unchanged, ext_shifted = [], []
for s in PIECES:
    a, r = fp_sig(boards[s], shift_ext_to_r12=True), fp_sig(r12[s], shift_ext_to_r12=False)
    for ref in sorted(set(a) | set(r)):
        ka, kr = a.get(ref), r.get(ref)
        if ka is None or kr is None or ka['at'] != kr['at'] or ka['pads'] != kr['pads'] or ka['layer'] != kr['layer']:
            diff[ref] = dict(r15_normalized=ka, r12=kr)
        elif ka['is_ext']:
            ext_shifted.append(dict(ref=ref, r12_y=kr['raw_at'][1], r15_y=ka['raw_at'][1], dy=round(ka['raw_at'][1] - kr['raw_at'][1], 3)))
        else:
            box_unchanged.append(dict(ref=ref, x=ka['raw_at'][0], y=ka['raw_at'][1]))
    counts[s] = dict(contacts=sum(1 for x in a if x.startswith('E')), resistors=sum(1 for x in a if x.startswith('R')))
    fps = list(boards[s].GetFootprints())
    chs = sorted({int(p.GetNetname()[2:].split('_')[0]) for f in fps for p in f.Pads() if p.GetNetname().startswith('CH')})
    for ch in chs:
        for pol in 'NP':
            t, e = f'CH{ch}_{pol}', f'CH{ch}_{pol}_E'
            rs = [f for f in fps if {p.GetNetname() for p in f.Pads()} == {t, e}]
            es = [f for f in fps if f.GetReference() == f'E{ch}{pol}' and [p.GetNetname() for p in f.Pads()] == [e]]
            if len(rs) != 1 or len(es) != 1 or rs[0].GetValue() != '100k' or rs[0].GetLayerName() != 'B.Cu':
                topo.append(dict(net=t, resistors=len(rs), contacts=len(es)))
    for net, eref in (('BIAS_DRV1', 'EB1'), ('BIAS_DRV12', 'EB2')):
        if any(p.GetNetname() == net for f in fps for p in f.Pads()):
            rs = [f for f in fps if {p.GetNetname() for p in f.Pads()} == {net, net + '_E'}]
            es = [f for f in fps if f.GetReference() == eref]
            if len(rs) != 1 or rs[0].GetValue() != '200k' or len(es) != 1:
                topo.append(dict(net=net, resistors=len(rs)))
n_contacts = sum(c['contacts'] for c in counts.values())
# 直接从板文件读回 16 路触点的对内中心距与腕周节距
all_contacts = {}
for s in PIECES:
    for f in boards[s].GetFootprints():
        ref = f.GetReference()
        if ref.startswith('E'):
            all_contacts[ref] = (round(mm(f.GetPosition().x), 3), round(mm(f.GetPosition().y), 3))
box_pair_dists = {f'CH{ch}': round(all_contacts[f'E{ch}P'][1] - all_contacts[f'E{ch}N'][1], 3) for ch in (1, 2)}
ext_pair_dists = {f'CH{ch}': round(all_contacts[f'E{ch}P'][1] - all_contacts[f'E{ch}N'][1], 3) for ch in range(3, 17)}
south_pitches = [round(all_contacts[f'E{ch + 1}N'][0] - all_contacts[f'E{ch}N'][0], 3) for ch in range(5, 16)]
north_pitch = round(all_contacts['E3N'][0] - all_contacts['E4N'][0], 3)
box_pitch = round(all_contacts['E2N'][0] - all_contacts['E1N'][0], 3)
meta_ok = (all(v == 16.0 for v in box_pair_dists.values())
           and all(v == 18.0 for v in ext_pair_dists.values())
           and all(p == 8.0 for p in south_pitches)
           and north_pitch == 8.0 and box_pitch == 15.0
           and len(box_unchanged) == 12 and len(ext_shifted) == 56
           and all(abs(x['dy']) == 1.0 for x in ext_shifted))
gate('contacts_resistors_vs_r12', not diff and not topo and n_contacts == 34 and sum(c['resistors'] for c in counts.values()) == 34 and meta_ok,
     dict(counts=counts, contacts_total=n_contacts, differs_from_r12_after_1mm_ext_shift=diff, topology_errors=topo,
          box_bottom_unchanged_count=len(box_unchanged), ext_shifted_count=len(ext_shifted),
          box_pair_spacing_mm=box_pair_dists, ext_pair_spacing_mm=ext_pair_dists,
          circumferential_pitches_mm=dict(north=north_pitch, box=box_pitch, south=south_pitches),
          note='盒底 6 触点 + 6 串阻与 R12 坐标 0 差（兼容 R12 外壳）；盒外 14 岛（28 触点 + 28 串阻）向南北各外扩 1.0 mm，对内中心距 18.0 mm（y=41.0/59.0），腕周节距 8.0 mm'))

tail_cmp = {}
for s, (ref, tref) in PIECES.items():
    ia, ir = items(boards[s]), items(r12[s])
    fa = [p for p in ia['pads'] if p['ref'] == tref]
    tip = round(min(p['rect'][0] for p in fa) - 0.2, 3)
    wa = next(s_ for s_ in cross_section(ia, tip + 1.0)[0] if s_[0] < 50 < s_[1])
    wr = next(s_ for s_ in cross_section(ir, tip + 1.0)[0] if s_[0] < 50 < s_[1])
    ring = [r for r in ia['rings']['User.2'] if abs(min(x for x, _ in r) - tip) < 1e-3]
    st_len = round(max(x for x, _ in ring[0]) - min(x for x, _ in ring[0]), 3) if ring else None
    tail_cmp[s] = dict(tip_x=tip, width_r14=round(wa[1] - wa[0], 3), width_r12=round(wr[1] - wr[0], 3), stiffener_len=st_len,
                       stiffener_side='B（金手指背面）' if ring else None)
gate('tail_vs_r12', all(v['width_r14'] == v['width_r12'] == 17.5 and v['stiffener_len'] == 2.5 for v in tail_cmp.values())
     and all(not report[f'pins_{s}']['finger_geometry_differs_from_r12'] for s in PIECES), tail_cmp)

# ---------- 3. DRC ----------


def drc(board_path, out, refill=False):
    subprocess.run([KC, 'pcb', 'drc', '--format', 'json', '--severity-all', *(['--refill-zones'] if refill else []), '-o', str(out), str(board_path)],
                   check=True, capture_output=True)
    return json.loads(Path(out).read_text())


for s in PIECES:
    d = drc(HERE / f'strap-{s}.kicad_pcb', HERE / f'drc-{s}.json')
    tmp = Path(tempfile.mkdtemp(prefix='r14drc-'))
    rf = drc(HERE / f'strap-{s}.kicad_pcb', tmp / 'refill.json', refill=True)         # 不存盘，只验证重铺后也干净
    shutil.rmtree(tmp)
    gate(f'drc_{s}', not d['violations'] and not d['unconnected_items'] and not rf['violations'] and not rf['unconnected_items'],
         dict(violations=len(d['violations']), unconnected=len(d['unconnected_items']), kicad=d.get('kicad_version'), rules=f'strap-{s}.kicad_dru',
              after_refill_zones=dict(violations=len(rf['violations']), unconnected=len(rf['unconnected_items']))))


def negative(s, edit):
    tmp = Path(tempfile.mkdtemp(prefix='r14neg-'))
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
r12web = {s: res_web(items(r12[s])) for s in PIECES}
for s, b in boards.items():
    m = measure(b)
    g = m['geometry']
    gate(f'geometry_{s}', g['min_center_between_different_nets_mm'] >= 0.47 - 1e-4 and g['min_center_within_pair_mm'] >= 0.30 - 1e-4
         and g['min_track_copper_to_outline_mm'] >= 0.305 - 1e-4 and (g['min_track_copper_to_hole_edge_mm'] or 9) >= 0.305 - 1e-4
         and g['vias_in_dynamic_zones'] == 0 and g['track_widths'] == [0.15], g)
    web = {w['pad']: w['gap_mm'] for w in m['res_pad_to_contact']}
    web12 = {w['pad']: w['gap_mm'] for w in r12web[s]}
    worse = {p: (v, web12.get(p)) for p, v in web.items() if web12.get(p) is None or v < web12[p] - 1e-3}
    gate(f'res_pad_to_contact_{s}', not worse,
         dict(min_gap_mm=min(web.values()), r12_min_gap_mm=min(web12.values()), worse_than_r12=worse,
              by_pad={p: v for p, v in sorted(web.items(), key=lambda t: t[1])},
              note='串阻位置照抄 R12，所以与 R12 同值；负值 = 0402 电极侧焊盘与同网触点焊盘相连（R12 盒底 R2/R4 即如此）'))
    t = m['tail']
    gate(f'tail_vias_{s}', t['via_copper_to_finger_copper_mm'] >= 0.3 and t['via_hole_edge_to_finger_pad_mm'] >= 0.2, t)
    st = m['stiffener']
    isl = st['layers'].get('User.2', {})
    n_isl = sum(1 for f in b.GetFootprints() if re.fullmatch(r'E(\d+)[NP]', f.GetReference()) and int(f.GetReference()[1:-1]) >= 3)
    gate(f'stiffener_{s}', st['fingers_backed_on_opposite_face'] and isl.get('island_contacts_backed') == n_isl
         and isl.get('min_contact_coverage') == 1.0 and isl.get('res_pads_covered') == 0, dict(island_contacts=n_isl, **st))
    me = m['mesh']
    gate(f'gnd_planes_{s}', all(v['orphan_pieces'] == 0 and v['pieces_under_0p5mm2'] == 0 and v['voids_narrower_than_0p15'] == 0
                                and 0.40 <= v['min_copper_vs_copperable'] and v['max_copper_vs_copperable'] <= 0.62 for v in me.values()), me)

# ---------- 7. 带宽：与 R12 同一 x 截面逐段对比 ----------
SEC = {
    'a': [('尾（插接尾，A 折弯区）', 35.0, 50.0), ('A 北支', 33.0, 40.0), ('A 北颈', 20.0, 47.8), ('A 出盒带（带根）', 80.0, 54.0),
          ('A 桥1', 94.0, 54.0), ('A 桥2', 102.0, 54.0), ('A 桥3', 110.0, 54.0)],
    'b': [('尾（插接尾，B 折弯区）', 36.5, 50.0), ('B 盒内头部', 60.0, 48.0), ('B 带根（与 A 并行）', 80.0, 48.0), ('B 过 A 桥1', 94.0, 48.0),
          ('B 过 A 桥2', 102.0, 48.0), ('B 过 A 桥3', 110.0, 48.0), ('B 过 A 桥4', 118.0, 48.0)]
         + [(f'B 桥{i}', 126.0 + 8 * (i - 1), 47.0) for i in range(1, 8)],
}
DYN = {'尾', 'A 北支', 'A 北颈', 'A 出盒带', 'A 桥', 'B 带根', 'B 过 A 桥', 'B 桥'}
wrows, wbad = [], []
it14 = {s: items(boards[s]) for s in PIECES}
it12 = {s: items(r12[s]) for s in PIECES}
for s, secs in SEC.items():
    for name, x, yref in secs:
        a14, a12 = band_stats(it14[s], x, yref), band_stats(it12[s], x, yref)
        row = dict(piece=s.upper(), segment=name, x=x, r12_y=f"{a12['y0']}–{a12['y1']}", r12_width=a12['width'],
                   r14_y=f"{a14['y0']}–{a14['y1']}", r14_width=a14['width'], delta=round(a14['width'] - a12['width'], 3))
        for tag, st in (('r12', a12), ('r14', a14)):
            lay = [st[L] for L in ('F.Cu', 'B.Cu') if L in st]
            row[f'{tag}_pairs'] = sum(v['pairs'] for v in lay if v['pairs'] > 1 or v['tracks'] > 1)
            row[f'{tag}_min_center_diff_net'] = min((v['min_center_diff_net'] for v in lay if v['min_center_diff_net']), default=None)
            row[f'{tag}_pair_pitch'] = '–'.join(sorted({str(v['pair_pitch_min']) for v in lay if v['pair_pitch_min']} | {str(v['pair_pitch_max']) for v in lay if v['pair_pitch_max']}))
            row[f'{tag}_edge_copper'] = f"{min((v['edge_copper_top'] for v in lay), default='')}/{min((v['edge_copper_bottom'] for v in lay), default='')}"
        wrows.append(row)
        if a14['width'] < a12['width'] - 1e-6:
            wbad.append(name)
slot = []
for x, an, bn in ((80.0, 'A 出盒带（带根）', 'B 带根（与 A 并行）'), (94.0, 'A 桥1', 'B 过 A 桥1'), (102.0, 'A 桥2', 'B 过 A 桥2'), (110.0, 'A 桥3', 'B 过 A 桥3')):
    row = dict(x=x)
    for tag, it in (('r12', it12), ('r14', it14)):
        a_, b_ = band_stats(it['a'], x, 54.0), band_stats(it['b'], x, 48.0)
        lo, hi = min(a_['y0'], b_['y0']), max(a_['y1'], b_['y1'])
        row[tag] = dict(span=f'{lo}–{hi}', total=round(hi - lo, 3), a=a_['width'], b=b_['width'],
                        gap=round(max(a_['y0'], b_['y0']) - min(a_['y1'], b_['y1']), 3))
    slot.append(row)
with (HERE / 'widths.csv').open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(wrows[0]), lineterminator='\n'); w.writeheader(); w.writerows(wrows)
gate('widths_vs_r12', not wbad and all(r['r14']['total'] > r['r12']['total'] for r in slot),
     dict(narrower_than_r12=wbad, slot_same_tpu=slot, table='widths.csv', sections=wrows))
# 叠放：A 的 F 面贴肤，B 叠在 A 的 B 面后面。B 外形要让开 A 的 B 面串阻和 A 的触点（EB1 的端子从 B 的让位孔穿过）；
# B 的触点（EB2）要从 A 的让位孔穿到皮肤面，A 外形要让开 B 的触点。B 的串阻在 B 的 B 面（背离 A），不算。
is_res = lambda p: p['ref'].startswith('R')                                  # noqa: E731
is_contact = lambda p: p['circle'] and p['r'] > 0.8                          # noqa: E731
stack = {}
for tag, bb in (('r14', boards), ('r12', r12)):
    stack[tag] = {'B 外形 vs A 的串阻焊盘': stack_gap(bb['b'], bb['a'], {'k': is_res})['k'],
                  'B 外形（含让位孔）vs A 的触点焊盘': stack_gap(bb['b'], bb['a'], {'k': is_contact})['k'],
                  'A 外形（含让位孔）vs B 的触点焊盘': stack_gap(bb['a'], bb['b'], {'k': is_contact})['k']}
gate('stack_clearance', all(v['min_gap_mm'] >= 0.2 - 1e-4 for v in stack['r14'].values()),
     dict(note='带符号间隙：正 = 焊盘落在对方板外或让位孔里，值为焊盘边到对方材料边；负 = 压在对方材料上。门限 0.2。r12 同口径对照',
          **stack))
report['backside_tracks_report_only'] = {s: backside_tracks(boards[s]) for s in PIECES}

after = {s: hashlib.sha256((HERE / f'strap-{s}.kicad_pcb').read_bytes()).hexdigest() for s in PIECES}
gate('boards_unchanged_by_check', after == report['board_sha256'], dict(note='检查全程只读两块板（反例都在临时副本上做）'))
for prl in HERE.glob('*.kicad_prl'):                           # pcbnew 读板顺手写的本机界面状态，不入库
    prl.unlink()
report['fails'] = fails
(HERE / 'checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k_: v.get('ok') if isinstance(v, dict) and 'ok' in v else v for k_, v in report.items() if k_ != 'board_sha256'}, ensure_ascii=False))
sys.exit(1 if fails else 0)
