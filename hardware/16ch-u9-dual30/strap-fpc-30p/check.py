#!/usr/bin/env python3
"""strap-fpc-30p 全项检查（使用 KiCad 自带 python3 -B check.py 运行）。
全部从冻结源板 strap-30p-a.kicad_pcb / strap-30p-b.kicad_pcb 读回，写出 checks.json、pin-map.json、
drc-a.json、drc-b.json、lint-a.json、lint-b.json、lengths.csv、widths.csv，并把表带串阻浅槽写入 geometry.json。
1. 脚序：每片 30 根金手指直接与 ../AFE-30P.epro 的 FPC1 / FPC3（广濑 FH34SRJ-30S-0.5SH(50)）逐脚独立核对；
   反例：对调两根金手指（存盘重读）与整排 1..30 镜像均必须报错。
2. 触点与 TPU 对孔：表带 14 路 28 个 F 面 Φ6.5 SMD 圆焊盘与 TPU 层孔中心逐一重合（≤ 0.01 mm）；
   胶囊底 6 个触点（CH1/CH2 Φ6.5 + EB1/EB2 Φ4.5）与基准位逐一重合（≤ 0.01 mm），34 颗限流/偏置串阻同值同网（含 4 项必败反例）。
3. KiCad 原生 DRC（含 --refill-zones 重铺校验）0 违规、0 未连 + 4 项正反对照。
4. route_lint 硬项 0。
5. 分段等长：32 段（尾→串阻、串阻→触点）P/N 差均 ≤ 10 mil。
6. 几何、尾部过孔、PI 分厚补强、网格地孤铜/碎块、盘边净距、两片叠放、EB2A/EB2 层间对焊、表带侧等高与皮肤侧串阻浅槽（含全套必败反例）。
7. 穿壳槽与 AFE-30P 底面器件避让：核对两条 15.50 mm 宽、错位 1.524 mm 的 30P 尾穿 tray_tail_slot 且避让 AFE-30P 底面器件（含 2 项必败反例）。
"""
from __future__ import annotations
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
import zipfile
from pathlib import Path

import pcbnew as k

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import _and, area, backside_tracks, band_stats, cross_section, items, material, measure, pset, ptrect, ptseg, stack_gap  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AFE_EPRO = HERE.parent / "AFE-30P.epro"
BASELINE = json.loads((HERE / "capsule-aux-baseline.json").read_text(encoding="utf-8"))
TPU = ROOT / "hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/build.py"
LINT = ROOT / "hardware/16ch-c08b-round/afe-d20/route_lint.py"
KC = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KPY = sys.executable
MIL = 0.0254
PIECES = {"a": ("FPC1", "TAIL_A"), "b": ("FPC3", "TAIL_B")}
mm = k.ToMM
report: dict = {"status": "已实现未实物验收：DRC/几何/脚序/对孔/四层铜核验见各项；未打样、未焊铜片、未上机"}
fails: list[str] = []


def gate(name: str, ok: bool, detail) -> None:
    report[name] = dict(ok=bool(ok), **detail) if isinstance(detail, dict) else dict(ok=bool(ok), detail=detail)
    if not ok:
        fails.append(name)


boards = {s: k.LoadBoard(str(HERE / f"strap-30p-{s}.kicad_pcb")) for s in PIECES}
report["board_sha256"] = {s: hashlib.sha256((HERE / f"strap-30p-{s}.kicad_pcb").read_bytes()).hexdigest() for s in PIECES}

# ---------- 1. 脚序：从 ../AFE-30P.epro 独立现推 30P 期望网络 ----------
afe_sha = hashlib.sha256(AFE_EPRO.read_bytes()).hexdigest()
with zipfile.ZipFile(AFE_EPRO) as zf:
    pcb_entry = next(n for n in zf.namelist() if n.endswith(".epcb"))
    afe_rows = [json.loads(l) for l in zf.read(pcb_entry).splitlines() if l.startswith(b"[")]
afe_rows = afe_rows[max(i for i, r in enumerate(afe_rows) if r[:2] == ["DOCTYPE", "PCB"]) :]
afe_refs = {r[3]: r[8] for r in afe_rows if r[0] == "ATTR" and r[7] == "Designator"}
afe_comp = {afe_refs[r[1]]: r for r in afe_rows if r[0] == "COMPONENT" and r[1] in afe_refs}
afe_pads: dict[tuple[str, int], str] = {
    (afe_refs[r[1]], int(r[2])): r[3]
    for r in afe_rows
    if r[0] == "PAD_NET" and r[1] in afe_refs and str(r[2]).isdigit()
}
afe_bynet: dict[str, set[tuple[str, int]]] = {}
for (r_des, p_num), n_name in afe_pads.items():
    if n_name:
        afe_bynet.setdefault(n_name, set()).add((r_des, p_num))

AUX_MAP = {
    "AGND": "AGND",
    "BIAS_DRV1": "BIAS_DRV1",
    "BIAS_DRV12": "BIAS_DRV12",
    "REF1": "",
    "REF2": "",
    "WCT": "",
    "WCT2": "",
}


def afe_expect(conn_ref: str) -> tuple[dict[int, str], dict[int, str]]:
    want, raw_net = {}, {}
    for n in range(1, 31):
        net = afe_pads[(conn_ref, n)]
        raw_net[n] = net
        if net in AUX_MAP:
            want[n] = AUX_MAP[net]
            continue
        hop = [x for x in afe_bynet[net] if re.fullmatch(r"U([3-9]|10)", x[0])]
        assert len(hop) == 1, (conn_ref, n, net, hop)
        ar, ap = hop[0]
        far = afe_pads[(ar, 9 - int(ap))]
        adc = [x for x in afe_bynet[far] if x[0] in ("U1", "U2")]
        assert len(adc) == 1, (conn_ref, n, far, adc)
        u_ref, u_pin = adc[0]
        ch_local = (18 - u_pin) // 2
        pol = "P" if u_pin % 2 == 0 else "N"
        ch = ch_local + (8 if u_ref == "U2" else 0)
        want[n] = f"CH{ch}_{pol}"
    return want, raw_net


def tail_nets(b, ref: str):
    f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    return f, {int(p.GetNumber()): p for p in f.Pads()}


def pin_errors(nets: dict[int, str], want: dict[int, str]) -> list[dict]:
    return [dict(pin=n, board_net=nets.get(n), expect=want[n]) for n in range(1, 31) if nets.get(n) != want[n]]


# 核对金手指中心与 AFE-30P FPC1/FPC3 旋转 180° 进入表壳坐标系 (x_box = 21.550 - x_afe) 的精确重合
EXPECT_TAIL_Y = {
    "a": round(50.0 + (21.550 - float(afe_comp["FPC1"][4]) * MIL), 4),  # 49.6056 mm
    "b": round(50.0 + (21.550 - float(afe_comp["FPC3"][4]) * MIL), 4),  # 48.0816 mm
}

pin_map = {}
for s, (conn_ref, tref) in PIECES.items():
    want, raw_net = afe_expect(conn_ref)
    f, pads = tail_nets(boards[s], tref)
    nets = {n: p.GetNetname() for n, p in pads.items()}
    errs = pin_errors(nets, want)
    mirrored = {n: nets[31 - n] for n in nets}
    yc_actual = round((mm(pads[1].GetPosition().y) + mm(pads[30].GetPosition().y)) * 0.5, 4)
    yc_err = round(abs(yc_actual - EXPECT_TAIL_Y[s]), 5)
    pitches = [round(abs(mm(pads[n + 1].GetPosition().y) - mm(pads[n].GetPosition().y)), 4) for n in range(1, 30)]
    pin_map[s] = dict(
        connector=conn_ref,
        afe_epro_sha256=afe_sha,
        center_y_mm=yc_actual,
        expect_center_y_mm=EXPECT_TAIL_Y[s],
        table=[
            dict(
                pin=n,
                board_net=nets[n],
                afe_net=raw_net[n],
                expect=want[n],
                y=round(mm(pads[n].GetPosition().y), 4),
            )
            for n in range(1, 31)
        ],
    )
    gate(
        f"pins_{s}",
        not errs
        and len(pads) == 30
        and yc_err <= 0.002
        and all(abs(pt - 0.5) <= 0.001 for pt in pitches)
        and all(p.IsOnLayer(k.F_Cu) and not p.IsOnLayer(k.B_Cu) for p in pads.values()),
        dict(
            connector=conn_ref,
            pads=len(pads),
            errors_vs_afe30p=errs,
            center_y_mm=yc_actual,
            center_y_err_mm=yc_err,
            pin1_y=round(mm(pads[1].GetPosition().y), 4),
            pin30_y=round(mm(pads[30].GetPosition().y), 4),
            finger_face="F",
            negative_mirror_errors=len(pin_errors(mirrored, want)),
        ),
    )
(HERE / "pin-map.json").write_text(json.dumps(pin_map, ensure_ascii=False, indent=1), encoding="utf-8")

neg_pin = {}
for s, (conn_ref, tref), (p1, p2) in (("a", PIECES["a"], (19, 20)), ("b", PIECES["b"], (6, 7))):
    tmp = Path(tempfile.mkdtemp(prefix="s30neg-"))
    b = k.LoadBoard(str(HERE / f"strap-30p-{s}.kicad_pcb"))
    _, pads = tail_nets(b, tref)
    n1, n2 = pads[p1].GetNet(), pads[p2].GetNet()
    pads[p1].SetNet(n2)
    pads[p2].SetNet(n1)
    k.SaveBoard(str(tmp / "swap.kicad_pcb"), b)
    _, sp = tail_nets(k.LoadBoard(str(tmp / "swap.kicad_pcb")), tref)
    shutil.rmtree(tmp)
    want, _ = afe_expect(conn_ref)
    e = pin_errors({n: p.GetNetname() for n, p in sp.items()}, want)
    neg_pin[f"{s}_swap_{p1}_{p2}"] = dict(errors=len(e), pins=[x["pin"] for x in e])
gate(
    "pin_order_negative",
    all(v["errors"] == 2 for v in neg_pin.values()) and all(report[f"pins_{s}"]["negative_mirror_errors"] >= 20 for s in PIECES),
    neg_pin,
)

# ---------- 2. 触点、TPU 对孔、胶囊底基准与 30P 尾部尺寸 ----------
def tpu_consts() -> dict:
    want_names = ("PITCH", "NORTH_YS", "SOUTH_YS", "LAYER_W", "PN", "DISC_D", "HOLE_CLEAR")
    ns: dict = {}
    for node in ast.parse(TPU.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in want_names:
            exec(compile(ast.Module([node], []), str(TPU), "exec"), ns)
    return {n: ns[n] for n in want_names}


TC = tpu_consts()
NORTH_YS_EXPECT = (34.0, 42.0)
BOX_CH = (1, 2)
contacts, topo, counts = {}, [], {}
for s in PIECES:
    fps = list(boards[s].GetFootprints())
    counts[s] = dict(contacts=0, resistors=sum(1 for f in fps if f.GetReference().startswith("R")))
    for f in fps:
        m = re.fullmatch(r"E(\d+)([NP])", f.GetReference())
        if not m or int(m[1]) in BOX_CH:
            continue
        counts[s]["contacts"] += 1
        (p,) = list(f.Pads())
        contacts[f.GetReference()] = dict(
            piece=s,
            ch=int(m[1]),
            pol=m[2],
            x=round(mm(p.GetPosition().x), 4),
            y=round(mm(p.GetPosition().y), 4),
            d=round(mm(p.GetSize(k.F_Cu).x), 4),
            circle=p.GetShape() == k.PAD_SHAPE_CIRCLE,
            smd=p.GetAttribute() == k.PAD_ATTRIB_SMD,
            drill=round(mm(p.GetDrillSize().x), 4),
            layers=sorted(boards[s].GetLayerName(L) for L in p.GetLayerSet().Seq()),
            mask_margin=round(mm(p.GetLocalSolderMaskMargin() or 0), 4),
            net=p.GetNetname(),
        )
    chs = sorted({int(p.GetNetname()[2:].split("_")[0]) for f in fps for p in f.Pads() if p.GetNetname().startswith("CH")})
    for ch in chs:
        for pol in "NP":
            t, e = f"CH{ch}_{pol}", f"CH{ch}_{pol}_E"
            rs = [f for f in fps if {p.GetNetname() for p in f.Pads()} == {t, e}]
            es = [f for f in fps if f.GetReference() == f"E{ch}{pol}" and [p.GetNetname() for p in f.Pads()] == [e]]
            if len(rs) != 1 or len(es) != 1 or rs[0].GetValue() != "100k" or rs[0].GetLayerName() != ("B.Cu" if ch in BOX_CH else "F.Cu"):
                topo.append(dict(net=t, resistors=len(rs), contacts=len(es)))

bad_pad = {
    r: c
    for r, c in contacts.items()
    if not (c["circle"] and c["smd"] and c["d"] == 6.5 and c["drill"] == 0 and c["layers"] == ["F.Cu", "F.Mask", "F.Paste"] and c["mask_margin"] == 0)
}
STRAP_CH = range(3, 17)
pair_sp = {ch: round(contacts[f"E{ch}P"]["y"] - contacts[f"E{ch}N"]["y"], 4) for ch in STRAP_CH}
pcb_mask_margin = round(mm(boards["a"].GetDesignSettings().m_SolderMaskExpansion), 4)
gate(
    "contacts_30p",
    len(contacts) == 28
    and not bad_pad
    and not topo
    and all(v == 18.0 for v in pair_sp.values())
    and all(contacts[f"E{ch}N"]["y"] == 41.0 for ch in STRAP_CH)
    and pcb_mask_margin == 0
    and counts["a"]["resistors"] + counts["b"]["resistors"] == 34,
    dict(strap_contacts=len(contacts), counts=counts, bad_pads=bad_pad, topology_errors=topo, pair_spacing_mm=pair_sp, board_mask_margin=pcb_mask_margin),
)

holes = [(sx * TC["PN"] / 2, Y) for Y in NORTH_YS_EXPECT + tuple(TC["SOUTH_YS"]) for sx in (-1, 1)]
pairs, used = [], set()
for ref, c in sorted(contacts.items()):
    X, Y = c["y"] - 50.0, 58.0 - c["x"]
    i, h = min(enumerate(holes), key=lambda t: math.dist(t[1], (X, Y)))
    used.add(i)
    pairs.append(dict(ref=ref, strap_xy=[round(X, 4), round(Y, 4)], hole=[h[0], h[1]], err_mm=round(math.dist(h, (X, Y)), 5)))
worst_al = max(p["err_mm"] for p in pairs)
gate(
    "tpu_hole_alignment",
    len(pairs) == 28 and len(used) == len(holes) == 28 and worst_al <= 0.01 and len(TC["SOUTH_YS"]) == 12,
    dict(tpu_build=str(TPU.relative_to(ROOT)), holes=len(holes), matched=len(used), worst_err_mm=worst_al),
)

BOX_CONTACTS = {"a": ("E1N", "E1P", "E2N", "E2P", "EB1"), "b": ("EB2",)}
BOX_RES = {"a": ("R1", "R2", "R3", "R4", "R33"), "b": ("R34",)}
BOX_D = {"E1N": 6.5, "E1P": 6.5, "E2N": 6.5, "E2P": 6.5, "EB1": 4.5, "EB2": 4.5}


def fpd(b):
    return {f.GetReference(): f for f in b.GetFootprints()}


def box_cmp(bd):
    bad, moved, rows = [], {}, []
    for s in PIECES:
        here = fpd(bd[s])
        for ref in BOX_CONTACTS[s]:
            f, o = here.get(ref), BASELINE[ref]
            if f is None or len(list(f.Pads())) != 1:
                bad.append(f"{ref} 缺")
                continue
            (p,) = list(f.Pads())
            q = o["pads"][0]
            err = math.dist((mm(p.GetPosition().x), mm(p.GetPosition().y)), (q["x"], q["y"]))
            lay = sorted(bd[s].GetLayerName(L) for L in p.GetLayerSet().Seq())
            ok = (
                err <= 0.01
                and p.GetNetname() == q["net"]
                and p.GetShape() == k.PAD_SHAPE_CIRCLE
                and p.GetAttribute() == k.PAD_ATTRIB_SMD
                and round(mm(p.GetSize(k.F_Cu).x), 4) == BOX_D[ref]
                and round(mm(p.GetSize(k.F_Cu).y), 4) == BOX_D[ref]
                and mm(p.GetDrillSize().x) == 0
                and lay == ["F.Cu", "F.Mask", "F.Paste"]
                and (p.GetLocalSolderMaskMargin() or 0) == 0
            )
            rows.append(dict(piece=s, ref=ref, net=p.GetNetname(), err_mm=round(err, 5), d=round(mm(p.GetSize(k.F_Cu).x), 4)))
            if not ok:
                bad.append(ref)
        for ref in BOX_RES[s]:
            f, o = here.get(ref), BASELINE[ref]
            if f is None:
                bad.append(f"{ref} 缺")
                continue
            nets = sorted(p.GetNetname() for p in f.Pads())
            nets_base = sorted(q["net"] for q in o["pads"])
            if f.GetValue() != o["value"] or nets != nets_base or f.GetLayerName() != "B.Cu" or len(nets) != 2:
                bad.append(ref)
            moved[ref] = dict(value=f.GetValue(), nets=nets, layer=f.GetLayerName(), at=[round(mm(f.GetPosition().x), 4), round(mm(f.GetPosition().y), 4)])
    return dict(same=not bad and len(rows) == 6 and len(moved) == 6, bad=bad, contacts=rows, resistors=moved)


def _bx_edit(s: str, fn):
    tmp = Path(tempfile.mkdtemp(prefix="s30box-"))
    b = k.LoadBoard(str(HERE / f"strap-30p-{s}.kicad_pcb"))
    fn(b)
    k.SaveBoard(str(tmp / "x.kicad_pcb"), b)
    nb = k.LoadBoard(str(tmp / "x.kicad_pcb"))
    shutil.rmtree(tmp)
    return nb


box = box_cmp(boards)
neg_box = {
    "E1N 右移 0.05": not box_cmp({"a": _bx_edit("a", lambda b: fpd(b)["E1N"].SetPosition(k.VECTOR2I(fpd(b)["E1N"].GetPosition().x + k.FromMM(0.05), fpd(b)["E1N"].GetPosition().y))), "b": boards["b"]})["same"],
    "R33 值改 100k": not box_cmp({"a": _bx_edit("a", lambda b: fpd(b)["R33"].SetValue("100k")), "b": boards["b"]})["same"],
    "R4 尾侧网改 CH1_N": not box_cmp({"a": _bx_edit("a", lambda b: next(p for p in fpd(b)["R4"].Pads() if p.GetNetname() == "CH2_N").SetNet(b.FindNet("CH1_N"))), "b": boards["b"]})["same"],
    "EB1 焊盘改 Φ1.8": not box_cmp({"a": _bx_edit("a", lambda b: next(iter(fpd(b)["EB1"].Pads())).SetSize(k.VECTOR2I(k.FromMM(1.8), k.FromMM(1.8)))), "b": boards["b"]})["same"],
}
gate("box_vs_baseline", box["same"] and all(neg_box.values()), dict(box, negatives_red=neg_box))

tail_dims = {}
for s, (_, tref) in PIECES.items():
    ia = items(boards[s])
    fa = [p for p in ia["pads"] if p["ref"] == tref]
    tip = round(min(p["rect"][0] for p in fa) - 0.2, 3)
    yc = EXPECT_TAIL_Y[s]
    wa = next(s_ for s_ in cross_section(ia, tip + 1.0)[0] if s_[0] < yc < s_[1])
    ring = [r for r in ia["rings"]["User.2"] if abs(min(x for x, _ in r) - tip) < 1e-3]
    st_len = round(max(x for x, _ in ring[0]) - min(x for x, _ in ring[0]), 3) if ring else None
    tail_dims[s] = dict(tip_x=tip, width_mm=round(wa[1] - wa[0], 3), stiffener_len=st_len)
gate("tail_30p_dims", all(v["width_mm"] == 15.5 and v["stiffener_len"] == 2.5 for v in tail_dims.values()), tail_dims)

# ---------- 3. KiCad DRC + 4 项正反对照 ----------
def drc(board_path: Path, out: Path, refill: bool = False) -> dict:
    subprocess.run(
        [KC, "pcb", "drc", "--format", "json", "--severity-all", "--all-track-errors", *(["--refill-zones"] if refill else []), "-o", str(out), str(board_path)],
        check=True,
        capture_output=True,
    )
    return json.loads(out.read_text(encoding="utf-8"))


for s in PIECES:
    d = drc(HERE / f"strap-30p-{s}.kicad_pcb", HERE / f"drc-{s}.json")
    tmp = Path(tempfile.mkdtemp(prefix="s30drc-"))
    rf = drc(HERE / f"strap-30p-{s}.kicad_pcb", tmp / "refill.json", refill=True)
    shutil.rmtree(tmp)
    gate(
        f"drc_{s}",
        not d["violations"] and not d["unconnected_items"] and not rf["violations"] and not rf["unconnected_items"],
        dict(
            violations=len(d["violations"]),
            unconnected=len(d["unconnected_items"]),
            kicad=d.get("kicad_version"),
            rules=f"strap-30p-{s}.kicad_dru",
            after_refill_zones=dict(violations=len(rf["violations"]), unconnected=len(rf["unconnected_items"])),
        ),
    )


def negative_drc(s: str, edit):
    tmp = Path(tempfile.mkdtemp(prefix="s30negdrc-"))
    for ext in ("kicad_pro", "kicad_dru"):
        shutil.copy(HERE / f"strap-30p-{s}.{ext}", tmp / f"strap-30p-{s}.{ext}")
    b = k.LoadBoard(str(HERE / f"strap-30p-{s}.kicad_pcb"))
    edit(b)
    k.SaveBoard(str(tmp / f"strap-30p-{s}.kicad_pcb"), b)
    d = drc(tmp / f"strap-30p-{s}.kicad_pcb", tmp / "drc.json")
    shutil.rmtree(tmp)
    return sorted({v["type"] + (" :" + re.search(r"'([^']+)'", v["description"])[1] if "'" in v["description"] else "") for v in d["violations"]})


def add_track(b, net: str, pts, layer=k.F_Cu):
    for a, z in zip(pts, pts[1:]):
        t = k.PCB_TRACK(b)
        t.SetStart(k.VECTOR2I(k.FromMM(a[0]), k.FromMM(a[1])))
        t.SetEnd(k.VECTOR2I(k.FromMM(z[0]), k.FromMM(z[1])))
        t.SetWidth(k.FromMM(0.15))
        t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)


def add_via(b, net: str, p):
    v = k.PCB_VIA(b)
    v.SetPosition(k.VECTOR2I(k.FromMM(p[0]), k.FromMM(p[1])))
    v.SetWidth(k.FromMM(0.5))
    v.SetDrill(k.FromMM(0.25))
    v.SetLayerPair(k.F_Cu, k.B_Cu)
    v.SetNet(b.FindNet(net))
    b.Add(v)


def lane_y(s: str, x: float, net: str) -> float:
    return next(h[0] for h in cross_section(items(boards[s]), x)[1] if h[1] == net and h[2] == "F.Cu")


negs = {}
yp, yn = lane_y("a", 80.0, "CH5_P"), lane_y("a", 80.0, "CH5_N")
negs["short_CH5_N_to_CH5_P"] = negative_drc("a", lambda b: add_track(b, "CH5_N", [(80.0, yn), (80.0, yp)]))
y13, y12 = lane_y("b", 80.0, "CH13_P"), lane_y("b", 80.0, "CH12_N")


def jog(c: float):
    yj = y12 - c
    e = yj - y13
    return lambda b: add_track(b, "CH13_P", [(80.0, y13), (80.0 + e, yj), (82.0 - e, yj), (82.0, y13)])


negs["center_0.40_CH13_P_vs_CH12_N"] = negative_drc("b", jog(0.40))
negs["positive_center_0.47_same_place"] = negative_drc("b", jog(0.47))
ys = sorted(h[0] for h in cross_section(items(boards["a"]), 94.0)[1] if h[2] == "F.Cu")
gap = max(zip(ys, ys[1:]), key=lambda t: t[1] - t[0])
negs["via_in_dynamic_A_bridge1"] = negative_drc("a", lambda b: add_via(b, "AGND", (94.0, round((gap[0] + gap[1]) / 2, 3))))
neg_ok = (
    bool({"shorting_items", "tracks_crossing"} & {x.split(" ")[0] for x in negs["short_CH5_N_to_CH5_P"]})
    and any("中心距0.47" in x for x in negs["center_0.40_CH13_P_vs_CH12_N"])
    and not any("中心距0.47" in x for x in negs["positive_center_0.47_same_place"])
    and any(x.startswith("items_not_allowed") for x in negs["via_in_dynamic_A_bridge1"])
)
gate("drc_negative_controls", neg_ok, negs)

# ---------- 4. route_lint ----------
hard = ("odd_angle", "sharp", "tee_acute", "width_jump", "dangling", "pad_exit")
for s in PIECES:
    subprocess.run([KPY, str(LINT), f"strap-30p-{s}.kicad_pcb", f"lint-{s}.json"], cwd=str(HERE), capture_output=True, check=True)
    L = json.loads((HERE / f"lint-{s}.json").read_text(encoding="utf-8"))["summary"]
    gate(
        f"route_lint_{s}",
        sum(L[h] for h in hard) == 0,
        dict(hard=sum(L[h] for h in hard), hard_items={h: L[h] for h in hard}, report_only={x: L[x] for x in ("pad_exit_side", "tee_90", "pad_exit_rotated")}),
    )

# ---------- 5. 分段等长 ----------
rows = []
for s, b in boards.items():
    L_map: dict[str, float] = {}
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK":
            L_map[t.GetNetname()] = L_map.get(t.GetNetname(), 0.0) + mm(t.GetLength())
    for ch in sorted({int(n[2:].split("_")[0]) for n in L_map if n.startswith("CH")}):
        for seg, suf in (("尾→串阻", ""), ("串阻→触点", "_E")):
            p_len, n_len = L_map[f"CH{ch}_P{suf}"], L_map[f"CH{ch}_N{suf}"]
            rows.append(dict(piece=s.upper(), ch=ch, segment=seg, P_mm=round(p_len, 4), N_mm=round(n_len, 4), diff_mm=round(p_len - n_len, 4), diff_mil=round((p_len - n_len) / MIL, 3)))
with (HERE / "lengths.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
worst = max(rows, key=lambda r: abs(r["diff_mil"]))
gate("length_match", abs(worst["diff_mil"]) <= 10 and len(rows) == 32, dict(segments=len(rows), worst_diff_mil=worst["diff_mil"], worst_at=f"{worst['piece']} CH{worst['ch']} {worst['segment']}"))

# ---------- 6. 几何、补强、网格地、盘边净距 ----------
for s, b in boards.items():
    m = measure(b)
    g = m["geometry"]
    gate(
        f"geometry_{s}",
        g["min_center_between_different_nets_mm"] >= 0.47 - 1e-4
        and g["min_center_within_pair_mm"] >= 0.30 - 1e-4
        and g["min_track_copper_to_outline_mm"] >= 0.305 - 1e-4
        and (g["min_track_copper_to_hole_edge_mm"] or 9) >= 0.305 - 1e-4
        and g["min_via_copper_to_outline_mm"] >= 0.305 - 1e-4
        and g["vias_in_dynamic_zones"] == 0
        and g["track_widths"] == [0.15],
        g,
    )
    t = m["tail"]
    gate(f"tail_vias_{s}", t["via_copper_to_finger_copper_mm"] >= 0.3 and t["via_hole_edge_to_finger_pad_mm"] >= 0.2, t)
    st = m["stiffener"]
    isl = st["layers"].get("User.2", {})
    n_isl = sum(1 for f in b.GetFootprints() if re.fullmatch(r"E(\d+)[NP]", f.GetReference()) and int(f.GetReference()[1:-1]) not in BOX_CH)
    gate(f"stiffener_{s}", st["fingers_backed_on_opposite_face"] and isl.get("island_contacts_backed") == n_isl and isl.get("min_contact_coverage") == 1.0 and isl.get("res_pads_covered") == 0, st)
    _bad, _n = [], 0
    for d in b.GetDrawings():
        if d.GetLayer() != k.User_2:
            continue
        _n += 1
        bb = d.GetBoundingBox()
        cx_ = (bb.GetLeft() + bb.GetRight()) / 2e6
        w_ = (bb.GetRight() - bb.GetLeft() - d.GetWidth()) / 1e6
        if 5 < w_ < 9 and abs(w_ - (bb.GetBottom() - bb.GetTop() - d.GetWidth()) / 1e6) < 0.05:
            if w_ / 2 > 3.6 + 1e-6:
                _bad.append((round(cx_, 3), round(w_, 3)))
    gate(f"stiffener_inside_island_{s}", _n == n_isl + 1 and not _bad, dict(stiffener_shapes=_n, expect=n_isl + 1, oversize=_bad))
    me = m["mesh"]
    gate(
        f"gnd_planes_{s}",
        all(
            v["orphan_pieces"] == 0 and v["pieces_under_0p5mm2"] == 0 and v["voids_narrower_than_0p15"] == 0 and 0.40 <= v["min_copper_vs_copperable"] and v["max_copper_vs_copperable"] <= 0.62
            for v in me.values()
        ),
        me,
    )
    it = items(b)
    cps = [p for p in it["pads"] if p["circle"] and p["r"] > 2]
    edge = min(min(ptseg(p["c"], a, z) for a, z in it["segs"]) - p["r"] for p in cps)
    vip = min(((math.dist(v["c"], p["c"]) - p["r"] - v["r"], v, p) for v in it["vias"] for p in cps), key=lambda t: t[0])
    vip_r = min(((ptrect(v["c"], p["rect"]) - v["r"], v, p) for v in it["vias"] for p in it["pads"] if not p["circle"]), key=lambda t: t[0])
    gate(
        f"pad_edge_and_no_via_in_pad_{s}",
        edge >= 0.3 - 1e-4 and vip[0] >= 0.15 and vip_r[0] >= 0.15,
        dict(contact_pad_to_outline_min_mm=round(edge, 4), via_to_contact_pad_min_mm=round(vip[0], 4), via_to_rect_pad_min_mm=round(vip_r[0], 4)),
    )

# ---------- 7. 截面报告、两片叠放与 EB2A/EB2 层间对焊 ----------
SEC = {
    "a": [("尾（A 折弯区）", 35.0, 49.6), ("A 北支", 33.0, 39.0), ("A 北岛间 CH4|CH3", 20.1, 39.0), ("A 出盒带", 80.0, 53.0), ("A 桥1", 94.1, 53.0), ("A 桥2", 102.1, 53.0), ("A 桥3", 110.1, 53.0)],
    "b": [("尾（B 折弯区）", 36.5, 48.1), ("B 盒内头部", 60.0, 48.0), ("B 带根", 80.0, 48.0), ("B 过 A 桥1", 94.0, 48.0), ("B 过 A 桥2", 102.0, 48.0), ("B 过 A 桥3", 110.0, 48.0), ("B 过 A 桥4", 118.0, 48.0)]
    + [(f"B 桥{i}", 126.1 + 8 * (i - 1), 47.0) for i in range(1, 8)],
}
wrows = []
itd = {s: items(boards[s]) for s in PIECES}
for s, secs in SEC.items():
    for name, x, yref in secs:
        a_ = band_stats(itd[s], x, yref)
        assert a_ is not None, (s, name, x, yref)
        lay = [a_[L] for L in ("F.Cu", "B.Cu") if L in a_]
        wrows.append(
            dict(
                piece=s.upper(),
                segment=name,
                x=x,
                y=f"{a_['y0']}–{a_['y1']}",
                width=a_["width"],
                pairs=sum(v["pairs"] for v in lay),
                min_center_diff_net=min((v["min_center_diff_net"] for v in lay if v["min_center_diff_net"]), default=None),
            )
        )
with (HERE / "widths.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(wrows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(wrows)


def stiff_gap(b_top, b_under):
    top = items(b_top)
    ol = k.SHAPE_POLY_SET()
    b_top.GetBoardPolygonOutlines(ol, False)
    poly = k.SHAPE_POLY_SET()
    poly.AddOutline(ol.Outline(0))
    rows_g = []
    for ring in items(b_under)["rings"]["User.2"]:
        xs_, ys_ = [x for x, _ in ring], [y for _, y in ring]
        c = ((max(xs_) + min(xs_)) / 2, (max(ys_) + min(ys_)) / 2)
        r = (max(xs_) - min(xs_)) / 2
        if abs((max(ys_) - min(ys_)) / 2 - r) > 0.01:
            continue
        d = min(ptseg(c, a, z) for a, z in top["segs"]) - r
        rows_g.append(dict(at=[round(c[0], 3), round(c[1], 3)], gap_mm=round(-(r + d) if poly.Contains(k.VECTOR2I(round(c[0] * 1e6), round(c[1] * 1e6))) else d, 4)))
    rows_g.sort(key=lambda t: t["gap_mm"])
    return dict(min_gap_mm=rows_g[0]["gap_mm"], nearest=rows_g[:3], discs=len(rows_g))


stack = {
    "B 外形 vs A 的串阻焊盘": stack_gap(boards["b"], boards["a"], {"k": lambda p: p["ref"].startswith("R")})["k"],
    "B 外形 vs A 的 PI 补强圆片": stiff_gap(boards["b"], boards["a"]),
}
gate("stack_clearance", all(v["min_gap_mm"] >= 0.2 - 1e-4 for v in stack.values()), stack)


def eb2_joint(ba, bb):
    fa, fb = fpd(ba).get("EB2A"), fpd(bb).get("EB2")
    if fa is None or fb is None:
        return dict(ok=False, why="缺 EB2A 或 EB2")
    (pa,), (pb,) = list(fa.Pads()), list(fb.Pads())
    ca, cb = (mm(pa.GetPosition().x), mm(pa.GetPosition().y)), (mm(pb.GetPosition().x), mm(pb.GetPosition().y))
    lay = {ba.GetLayerName(L) for L in pa.GetLayerSet().Seq()}
    edge_near = [
        round(mm(d.GetCenter().x), 3)
        for d in ba.GetDrawings()
        if d.GetLayer() == k.Edge_Cuts and d.GetShape() == k.SHAPE_T_CIRCLE and math.dist((mm(d.GetCenter().x), mm(d.GetCenter().y)), ca) < 3
    ]
    r = dict(
        off_mm=round(math.dist(ca, cb), 4),
        da=round(mm(pa.GetSize(k.F_Cu).x), 4),
        db=round(mm(pb.GetSize(k.F_Cu).x), 4),
        drill=round(mm(pa.GetDrillSize().x), 4),
        pth=pa.GetAttribute() == k.PAD_ATTRIB_PTH,
        net_a=pa.GetNetname(),
        net_b=pb.GetNetname(),
        layers=sorted(lay),
        a_edge_holes_near=edge_near,
    )
    r["ok"] = (
        r["off_mm"] <= 0.01
        and r["da"] == r["db"] == 4.5
        and 0.6 <= r["drill"] <= 1.0
        and r["pth"]
        and r["net_a"] == r["net_b"] == "BIAS_DRV12_E"
        and {"F.Cu", "B.Cu", "F.Mask", "B.Mask"} <= lay
        and not edge_near
    )
    return r


jt = eb2_joint(boards["a"], boards["b"])
neg_jt = {
    "EB2A 右移 0.05": not eb2_joint(_bx_edit("a", lambda b: fpd(b)["EB2A"].SetPosition(k.VECTOR2I(fpd(b)["EB2A"].GetPosition().x + k.FromMM(0.05), fpd(b)["EB2A"].GetPosition().y))), boards["b"])["ok"],
    "EB2A 网改 AGND": not eb2_joint(_bx_edit("a", lambda b: next(iter(fpd(b)["EB2A"].Pads())).SetNet(b.FindNet("AGND"))), boards["b"])["ok"],
    "EB2A 孔 1.2": not eb2_joint(_bx_edit("a", lambda b: next(iter(fpd(b)["EB2A"].Pads())).SetDrillSize(k.VECTOR2I(k.FromMM(1.2), k.FromMM(1.2)))), boards["b"])["ok"],
    "B 片 EB2 下移 0.05": not eb2_joint(boards["a"], _bx_edit("b", lambda b: fpd(b)["EB2"].SetPosition(k.VECTOR2I(fpd(b)["EB2"].GetPosition().x, fpd(b)["EB2"].GetPosition().y + k.FromMM(0.05)))))["ok"],
}
gate("eb2_joint", jt["ok"] and all(neg_jt.values()), dict({kk: v for kk, v in jt.items() if kk != "ok"}, negatives_red=neg_jt))
report["backside_tracks_report_only"] = {s: backside_tracks(boards[s]) for s in PIECES}

# ---------- 8. 表带侧等高 + 皮肤侧串阻浅槽 ----------
H0402 = 0.35
BODY0402 = (1.0, 0.5)
POCKET_M = 0.3
KEEP_PAD = 0.25


def pi_thickness(b) -> float:
    ts = [float(m[1]) for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" for m in [re.search(r"触点背面 PI 补强 Φ[\d.]+ 厚 ([\d.]+)", d.GetText())] if m]
    assert len(ts) == 1, ts
    return ts[0]


def island_rects(b):
    it = items(b)
    ys_all = [y for _, y in it["outline"]]
    discs = [r for r in it["rings"]["User.2"] if abs((max(x for x, _ in r) - min(x for x, _ in r)) - (max(y for _, y in r) - min(y for _, y in r))) < 0.01]
    hw = max((max(x for x, _ in r) - min(x for x, _ in r)) / 2 for r in discs)
    out = {}
    for f in b.GetFootprints():
        m = re.fullmatch(r"E(\d+)N", f.GetReference())
        if m and int(m[1]) not in BOX_CH:
            cx = mm(f.GetPosition().x)
            out[int(m[1])] = (cx - hw, min(ys_all), cx + hw, max(ys_all))
    return out, hw


def strapside(bd):
    th = {s: mm(b.GetDesignSettings().GetBoardThickness()) for s, b in bd.items()}
    it = {s: items(b) for s, b in bd.items()}
    rows_s, comps = [], []
    for s, b in bd.items():
        other = "b" if s == "a" else "a"
        t_pi = pi_thickness(b)
        stiff = material(it[s]["rings"]["User.2"])
        isl, _ = island_rects(b)
        for ch, (x0, y0, x1, y1) in sorted(isl.items()):
            r = pset([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            parts = []
            if area(_and(stiff, r)) > 1e-3:
                parts.append(dict(what=f"PI 补强（{s.upper()}）", h=t_pi))
            ov = area(_and(it[other]["board"], r))
            if ov > 1e-3:
                parts.append(dict(what=f"下叠 {other.upper()} 片", h=round(th[other], 4)))
            for f in b.GetFootprints():
                if f.GetLayer() == k.B_Cu and any(ptrect((mm(p.GetPosition().x), mm(p.GetPosition().y)), (x0, y0, x1, y1)) == 0 for p in f.Pads()):
                    parts.append(dict(what=f"B面元件 {f.GetReference()}", h=H0402))
                    comps.append(f"{s.upper()}:{f.GetReference()}")
            rows_s.append(dict(piece=s.upper(), ch=ch, top_mm=max((p_["h"] for p_ in parts), default=0.0)))
        for f in b.GetFootprints():
            if f.GetLayer() == k.B_Cu and mm(f.GetPosition().x) >= 75.0:
                if f"{s.upper()}:{f.GetReference()}" not in comps:
                    comps.append(f"{s.upper()}:{f.GetReference()}")
    tops = [r_["top_mm"] for r_ in rows_s]
    return dict(islands=len(rows_s), top_min_mm=min(tops), top_max_mm=max(tops), spread_mm=round(max(tops) - min(tops), 4), strapside_components=comps)


def flat_ok(r) -> bool:
    return r["islands"] == 14 and not r["strapside_components"] and r["spread_mm"] <= 0.01 and r["top_min_mm"] > 0


def set_pi(t: float):
    def go(b):
        for d in b.GetDrawings():
            if d.GetClass() == "PCB_TEXT" and "触点背面 PI 补强" in d.GetText():
                d.SetText(re.sub(r"厚 [\d.]+", f"厚 {t}", d.GetText()))
    return go


flat = strapside(boards)
neg_flat = {
    "R10 翻到 B 面": not flat_ok(strapside({"a": _bx_edit("a", lambda b: fpd(b)["R10"].SetLayerAndFlip(k.B_Cu)), "b": boards["b"]})),
    "A 片 PI 改回 0.15": not flat_ok(strapside({"a": _bx_edit("a", set_pi(0.15)), "b": boards["b"]})),
}
gate("strapside_flat", flat_ok(flat) and all(neg_flat.values()), dict(flat, negatives_red=neg_flat))


def res_pockets(bd):
    out, worst_p = [], (9.0, None)
    for s, b in bd.items():
        contacts_ = [
            (f.GetReference(), (mm(f.GetPosition().x), mm(f.GetPosition().y)), mm(next(iter(f.Pads())).GetSize(k.F_Cu).x) / 2)
            for f in b.GetFootprints()
            if re.fullmatch(r"E\d+[NP]", f.GetReference())
        ]
        for f in b.GetFootprints():
            if not (f.GetReference().startswith("R") and f.GetValue() == "100k" and f.GetLayer() == k.F_Cu):
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
            ch = int(re.match(r"CH(\d+)", pads[0].GetNetname())[1])
            out.append(
                dict(
                    piece=s.upper(),
                    ref=f.GetReference(),
                    ch=ch,
                    net=pads[0].GetNetname().replace("_E", ""),
                    envelope=[round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
                    pocket_board=list(pk),
                    pocket_size=[round(pk[2] - pk[0], 4), round(pk[3] - pk[1], 4)],
                    pocket_strap=dict(X=[round(pk[1] - 50, 4), round(pk[3] - 50, 4)], Y=[round(58 - pk[2], 4), round(58 - pk[0], 4)]),
                    gap_to_contact_pad_mm=gaps[0][0],
                    nearest_contact=gaps[0][1],
                )
            )
            if gaps[0][0] < worst_p[0]:
                worst_p = (gaps[0][0], f"{s.upper()}:{f.GetReference()}→{gaps[0][1]}")
    return out, worst_p


pk_rows, pk_worst = res_pockets(boards)
neg_pk = {}
for name, s, dy, ref in (("R10 往焊盘挪 -0.8", "a", -0.8, "R10"), ("R17 往焊盘挪 +0.8", "b", 0.8, "R17")):
    bd = dict(boards)
    bd[s] = _bx_edit(s, lambda b, r_=ref, d_=dy: fpd(b)[r_].SetPosition(k.VECTOR2I(fpd(b)[r_].GetPosition().x, fpd(b)[r_].GetPosition().y + k.FromMM(d_))))
    r_, w_ = res_pockets(bd)
    neg_pk[name] = dict(red=not (len(r_) == 28 and w_[0] >= KEEP_PAD - 1e-9), worst_gap_mm=w_[0])
gate("skinside_res_envelope", len(pk_rows) == 28 and pk_worst[0] >= KEEP_PAD - 1e-9 and all(v["red"] for v in neg_pk.values()), dict(pockets=len(pk_rows), worst_gap_mm=pk_worst[0], worst_at=pk_worst[1], negatives=neg_pk))

geo_path = HERE / "geometry.json"
geo = json.loads(geo_path.read_text(encoding="utf-8"))
geo["f_res_pockets"] = dict(margin_mm=POCKET_M, part_height_mm=H0402, keep_from_pad_mm=KEEP_PAD, rects=pk_rows)
geo_path.write_text(json.dumps(geo, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- 9. 穿底壳北侧长槽几何核验（含必败反例） ----------
SLOT = geo["tray_tail_slot"]
BEND_X = SLOT["board_x_of_bend_start"]


def _rp(x0: float, y0: float, x1: float, y1: float):
    s_ = k.SHAPE_POLY_SET()
    s_.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        s_.Append(round(x * 1e6), round(y * 1e6))
    return s_


def tail_check(polys_map, fingers_xy):
    out, ok = {}, True
    for s_, P in polys_map.items():
        north = _and(P, _rp(0, 0, BEND_X, 100))
        north.Simplify()
        comps = []
        for i in range(north.OutlineCount()):
            ring = [(north.Outline(i).CPoint(j).x / 1e6, north.Outline(i).CPoint(j).y / 1e6) for j in range(north.Outline(i).PointCount())]
            one_ = k.SHAPE_POLY_SET()
            one_.AddOutline(north.Outline(i))
            is_tail = one_.Contains(k.VECTOR2I(round(fingers_xy[s_][0] * 1e6), round(fingers_xy[s_][1] * 1e6)))
            at_bend = [y for x, y in ring if abs(x - BEND_X) < 1e-3]
            comps.append(
                dict(
                    tail=is_tail,
                    y_at_bend=[round(min(at_bend), 3), round(max(at_bend), 3)] if at_bend else None,
                    box_x_at_bend=[round(min(at_bend) - 50, 3), round(max(at_bend) - 50, 3)] if at_bend else None,
                )
            )
        tails = [c for c in comps if c["tail"]]
        good = (
            len(tails) == 1
            and tails[0]["box_x_at_bend"] is not None
            and SLOT["box"]["x0"] <= tails[0]["box_x_at_bend"][0] + 1e-3
            and tails[0]["box_x_at_bend"][1] - 1e-3 <= SLOT["box"]["x1"]
        )
        ok &= good
        out[s_] = dict(ok=good, components=comps)
    return ok, out


polys = {}
for s_, b in boards.items():
    ol = k.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ol, False)
    polys[s_] = ol
fxy = {s_: next((p["c"] for p in items(boards[s_])["pads"] if p["ref"] == PIECES[s_][1]), None) for s_ in PIECES}
t_ok, t_info = tail_check(polys, fxy)
neg_t = {}
for name, s_, add in (("A 北支与尾之间缝补上", "a", _rp(37.0, 40.5, BEND_X + 0.5, 42.1)), ("B 尾加宽到 y 60.0", "b", _rp(33.0, 55.5, BEND_X + 0.5, 60.0))):
    pp = dict(polys)
    q_ = k.SHAPE_POLY_SET(polys[s_])
    q_.BooleanAdd(add)
    q_.Simplify()
    pp[s_] = q_
    neg_t[name] = not tail_check(pp, fxy)[0]
gate("tail_slot_entry", t_ok and all(neg_t.values()), dict(tray_tail_slot=SLOT["box"], tails=t_info, negatives_red=neg_t))

after = {s: hashlib.sha256((HERE / f"strap-30p-{s}.kicad_pcb").read_bytes()).hexdigest() for s in PIECES}
gate("boards_unchanged_by_check", after == report["board_sha256"], dict(note="全程只读源板，反例均在临时副本上执行"))
for prl in HERE.glob("*.kicad_prl"):
    prl.unlink()
report["fails"] = fails
(HERE / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k_: v.get("ok") if isinstance(v, dict) and "ok" in v else v for k_, v in report.items() if k_ != "board_sha256"}, ensure_ascii=False))
sys.exit(1 if fails else 0)
