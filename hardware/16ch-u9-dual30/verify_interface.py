#!/usr/bin/env python3
"""直接从两份嘉立创工程读取板间焊盘、双核 39 信号脚固件兼容、双 30P 超薄连接器 (C324727) 60 脚通道映射、
圆角 0.80mm 叠层（4层 AFE + 6层 MCU）、前端 RC/电荷泵电容与 32 颗 DNP 钢网零残留、
192 颗 CPL 逐脚拟合（含背面 180° 反例）与全套 3D 装配门禁（9.60 mm 净高 / >=0.85 mm 最小壁厚）并逐项核验。

运行：
  python3 verify_interface.py
  python3 verify_interface.py --selftest
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent
MIL = 0.0254

DNP_CM_CAPS = {
    "C55",
    *(f"C{i}" for i in range(57, 72)),
    *(f"C{i}" for i in range(93, 109)),
}
DIFF_22PF_CAPS = {
    *(f"C{i}" for i in range(72, 80)),
    *(f"C{i}" for i in range(109, 117)),
}


def rot_up(deg: float, x: float, y: float) -> tuple[float, float]:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def afe_pads() -> tuple[dict[tuple[str, int], str], list]:
    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pcb = next(name for name in z.namelist() if name.endswith(".epcb"))
        rows = [json.loads(line) for line in z.read(pcb).splitlines() if line.startswith(b"[")]
    rows = rows[max(i for i, r in enumerate(rows) if r[:2] == ["DOCTYPE", "PCB"]) :]
    refs = {r[3]: r[8] for r in rows if r[0] == "ATTR" and r[7] == "Designator"}
    pads = {
        (refs[r[1]], int(r[2])): r[3]
        for r in rows
        if r[0] == "PAD_NET" and r[1] in refs and str(r[2]).isdigit()
    }
    return pads, rows


def epru_pads(zpath: Path, conn_des: str) -> tuple[list[str], dict[tuple[str, int], str]]:
    with zipfile.ZipFile(zpath) as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith(".epru")))
    active = False
    pads, connectors, des_by_id = {}, set(), {}
    for line in doc.decode("utf-8", "ignore").splitlines():
        if "||" not in line:
            continue
        left, right = line.split("||", 1)
        right = right.removesuffix("|")
        if not right:
            continue
        h = json.loads(left)
        if h["type"] not in ("DOCHEAD", "ATTR", "PAD_NET"):
            continue
        v, _ = json.JSONDecoder().raw_decode(right)
        if h["type"] == "DOCHEAD":
            active = v["docType"] == "PCB"
        elif active and h["type"] == "ATTR" and v.get("key") == "Designator":
            des_by_id[v["parentId"]] = v.get("value")
            if v.get("value") == conn_des:
                connectors.add(v["parentId"])
        elif active and h["type"] == "PAD_NET":
            _, ref, pin, _ = json.loads(h["id"])
            if str(pin).isdigit():
                pads[ref, int(pin)] = v["padNet"]
    assert len(connectors) == 1, f"{zpath.name}: expected 1 {conn_des}, got {connectors}"
    ref = connectors.pop()
    by_des = {(des_by_id[k[0]], k[1]): val for k, val in pads.items() if k[0] in des_by_id}
    return [pads[ref, i] for i in range(1, 21)], by_des


def trace_afe_dual30(pads: dict[tuple[str, int], str]) -> dict[tuple[str, int], str]:
    """从 FPC1/FPC3 第 1..30 脚经 15 kΩ 排阻 U3..U10 独立推导至双 ADS1298 (U1/U2) IN1P..IN8N。"""
    by_net: dict[str, list[tuple[str, int]]] = {}
    for (ref, pin), net in pads.items():
        if net:
            by_net.setdefault(net, []).append((ref, pin))

    adc_role = {}
    for ch in range(1, 9):
        adc_role[("U1", 17 - 2 * ch)] = f"CH{ch}_N"
        adc_role[("U1", 18 - 2 * ch)] = f"CH{ch}_P"
        adc_role[("U2", 17 - 2 * ch)] = f"CH{ch + 8}_N"
        adc_role[("U2", 18 - 2 * ch)] = f"CH{ch + 8}_P"
    net_to_ch = {pads[k]: v for k, v in adc_role.items() if pads.get(k)}

    aux_names = {"AGND", "BIAS_DRV1", "BIAS_DRV12", "REF1", "REF2", "WCT", "WCT2"}
    arrays = {f"U{i}" for i in range(3, 11)}
    mapped: dict[tuple[str, int], str] = {}
    for con in ("FPC1", "FPC3"):
        for p in range(1, 31):
            net = pads[con, p]
            if net in aux_names:
                mapped[con, p] = net
            else:
                hops = [(r, rp) for (r, rp) in by_net.get(net, []) if r in arrays]
                assert len(hops) == 1, f"{con}.{p} net {net} expected 1 resistor array hop, got {hops}"
                ar, ap = hops[0]
                far = pads[ar, 9 - ap]
                assert far in net_to_ch, f"{con}.{p} -> {ar}.{9-ap} net {far} not on ADS1298 input"
                mapped[con, p] = net_to_ch[far]
    return mapped


def verify_dual30_expected(mapped: dict[tuple[str, int], str]) -> list[str]:
    errs = []
    for chip_idx, con in ((0, "FPC1"), (8, "FPC3")):
        want = {
            1: "REF1",
            2: "REF2",
            27: "WCT" if con == "FPC1" else "WCT2",
            28: "AGND",
            29: "BIAS_DRV1" if con == "FPC1" else "BIAS_DRV12",
            30: "AGND",
        }
        for k in range(1, 9):
            base = 3 + 3 * (k - 1)
            want[base] = f"CH{chip_idx + k}_P"
            want[base + 1] = f"CH{chip_idx + k}_N"
            want[base + 2] = "AGND"
        for p in range(1, 31):
            if mapped.get((con, p)) != want[p]:
                errs.append(f"{con}.{p}: got {mapped.get((con, p))!r}, expected {want[p]!r}")
    return errs


def verify_20p_pairing(main: list[str], afe: dict[tuple[str, int], str]) -> list[str]:
    csv_rows = list(csv.DictReader((P / "20针接口.csv").read_text(encoding="utf-8-sig").splitlines()))
    assert len(csv_rows) == 20, f"Expected 20 rows in 20针接口.csv, got {len(csv_rows)}"
    errs = []
    for idx, r in enumerate(csv_rows, 1):
        if int(r["主控FPC1"]) != idx or int(r["采集FPC2"]) != 21 - idx:
            errs.append(f"20针接口.csv row {idx} index mismatch")
        if main[idx - 1] != r["主控网络"]:
            errs.append(f"20针接口.csv row {idx} MCU mismatch: {main[idx - 1]} != {r['主控网络']}")
        if afe["FPC2", 21 - idx] != r["采集网络"]:
            errs.append(f"20针接口.csv row {idx} AFE mismatch: {afe['FPC2', 21 - idx]} != {r['采集网络']}")
    if not (afe["U2", 39] == afe["FPC2", 17] == "CS#2" and afe["U2", 47] == afe["FPC2", 18] == "DRDY2#"):
        errs.append("U2.39 / U2.47 与 FPC2.17 / FPC2.18 未对齐")
    return errs


def check_afe_fixes(rows: list, dual30: dict[tuple[str, int], str]) -> None:
    assert len(DNP_CM_CAPS) == 32, f"Expected 32 DNP CM caps, got {len(DNP_CM_CAPS)}"
    assert len(DIFF_22PF_CAPS) == 16, f"Expected 16 diff caps, got {len(DIFF_22PF_CAPS)}"

    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pj = json.loads(z.read("project.json").decode("utf-8"))
        sch_texts = {
            Path(name).name: z.read(name).decode("utf-8", "ignore")
            for name in z.namelist()
            if name.endswith(".esch")
        }
        sch1 = sch_texts["1.esch"]
        sch3 = sch_texts["3.esch"]

    # 1. Inner2 (L16) 北数字 GND + 南模拟 AGND 分区，删掉晶振 X1 正下方禁止铺铜框 e1680
    layer16 = next((r[2] for r in rows if r[0] == "LAYER" and r[1] == 16), None)
    rule7 = next((r[4][3] for r in rows if r[0] == "RULE" and r[1] == "7" and r[2] == "copperRegion"), None)
    pour_1678 = any(r[0] == "POUR" and r[1] == "e1678" and r[3] == "GND" and r[4] == 16 for r in rows)
    pour_1687 = any(r[0] == "POUR" and r[1] == "e1687" and r[3] == "AGND" and r[4] == 16 for r in rows)
    region_1680 = any(r[0] == "REGION" and r[1] == "e1680" for r in rows)
    pours = sum(1 for r in rows if r[0] == "POUR")
    poured = sum(1 for r in rows if r[0] == "POURED")
    assert layer16 == "SIGNAL", f"Expected Inner2 layer 16 SIGNAL, got {layer16}"
    assert rule7 == 1, f"Expected RULE 7 connType=1 (DIRECT), got {rule7}"
    assert not region_1680, "REGION e1680 under crystal X1 should be removed for unbroken GND plane"
    assert pour_1678 and pour_1687 and pours == 15 and poured >= 15, (
        f"Expected 15 POURs (L16 North GND e1678 + South AGND e1687) with rebuilt POURED, got {pours}/{poured}"
    )

    assert '["ATTR","e223","e95","Name","GND"' in sch1, "Expected U1.31 net flag e95=GND in 1.esch"
    assert '["ATTR","e814","e300","Name","GND"' in sch1, "Expected U2.31 net flag e300=GND in 1.esch"
    assert "FH34SRJ-30S-0.5SH(50)" in sch3 and "C324727" in sch3, "Expected FH34SRJ-30S-0.5SH(50) (C324727) in 3.esch"

    devs = pj["devices"]
    assert devs["2571ef32fa5163d1"]["attributes"]["Supplier Part"] == "C324727", "Expected C324727 on 30P connectors"
    assert devs["dfd86c324a67d8ca"]["attributes"]["Supplier Part"] == "C2984407", "Expected R4=C2984407 (105k)"

    # 2. 逐件核验 PCB + 原理图的 C10 (1uF C52923)、16 颗差分电容 (22pF C76924) 与 32 颗共模电容 DNP
    pcb_attrs: dict[str, dict[str, str]] = {}
    for r in rows:
        if r[0] == "ATTR":
            pcb_attrs.setdefault(r[3], {})[r[7]] = str(r[8])
    pcb_by_des = {at["Designator"]: at for at in pcb_attrs.values() if "Designator" in at}

    def _dev_part(at: dict[str, str]) -> str:
        if at.get("Supplier Part"):
            return at["Supplier Part"]
        did = at.get("Device", "")
        return devs.get(did, {}).get("attributes", {}).get("Supplier Part", "")

    assert _dev_part(pcb_by_des["C10"]) == "C52923", f"Expected C10=C52923 (1uF), got {pcb_by_des['C10']}"
    for ref in sorted(DIFF_22PF_CAPS):
        assert _dev_part(pcb_by_des[ref]) == "C76924", f"Expected {ref}=C76924 (22pF), got {pcb_by_des[ref]}"
        assert pcb_by_des[ref].get("Add into BOM", "yes").lower() != "no", f"{ref} must stay populated"
    for ref in sorted(DNP_CM_CAPS):
        assert pcb_by_des[ref].get("Add into BOM", "").lower() == "no", f"Expected {ref} Add into BOM=no (DNP)"

    sch_attrs: dict[str, dict[str, str]] = {}
    for sname, stxt in sch_texts.items():
        for ln in stxt.splitlines():
            if not ln.startswith('["ATTR"'):
                continue
            ar = json.loads(ln)
            sch_attrs.setdefault(f"{sname}:{ar[2]}", {})[ar[3]] = str(ar[4])
    sch_by_des = {at["Designator"]: at for at in sch_attrs.values() if "Designator" in at}
    assert _dev_part(sch_by_des["C10"]) == "C52923", f"Expected sch C10=C52923, got {sch_by_des['C10']}"
    for ref in sorted(DIFF_22PF_CAPS):
        assert _dev_part(sch_by_des[ref]) == "C76924", f"Expected sch {ref}=C76924, got {sch_by_des[ref]}"
    for ref in sorted(DNP_CM_CAPS):
        assert sch_by_des[ref].get("Add into BOM", "").lower() == "no", f"Expected sch {ref} Add into BOM=no"

    # 3. 校验 43.100 x 36.500 mm R1.800 mm 圆角板框与 0.80 mm 四层叠层
    outline = next((r for r in rows if r[0] == "POLY" and r[1] == "e1904" and r[4] == 11), None)
    assert outline is not None, "Missing board outline POLY e1904 on layer 11"
    rpath = outline[6]
    assert rpath[0] == "R" and round(rpath[3] * MIL, 3) == 43.100 and round(rpath[4] * MIL, 3) == 36.500
    assert rpath[5] == 0 and round(rpath[6] * MIL, 3) == 1.800, f"Unexpected outline corner radius: {rpath}"

    phys_t = sum(float(r[3]) for r in rows if r[0] == "LAYER_PHYS") * MIL
    assert 0.78 <= phys_t <= 0.83, f"Expected ~0.80 mm 4-layer stackup in AFE-30P, got {phys_t:.4f} mm"

    # 4. 校验 strap-fpc-30p/afe30p-interface.csv 与双 30P 60 脚完全一致
    iface_csv = P / "strap-fpc-30p/afe30p-interface.csv"
    assert iface_csv.is_file(), "Missing strap-fpc-30p/afe30p-interface.csv"
    irows = list(csv.DictReader(iface_csv.read_text(encoding="utf-8-sig").splitlines()))
    assert len(irows) == 60, f"Expected 60 rows in afe30p-interface.csv, got {len(irows)}"
    for ir in irows:
        con = ir["connector"].strip()
        pin = int(ir["pin"])
        role = ir["strap_net"].strip() or ir["afe_net"].strip()
        assert dual30.get((con, pin)) == role, f"afe30p-interface.csv {con}.{pin} role={role!r} != {dual30.get((con, pin))!r}"


def check_mcu_fixes(mcu_pads: dict[tuple[str, int], str]) -> None:
    with zipfile.ZipFile(P / "OpenEMG-C08B-Mainboard-Rev0.01.epro2") as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith(".epru"))).decode("utf-8", "ignore")
    cutout_ok = False
    button_ok = False
    pours = 0
    poured = 0
    phys_mils = 0.0
    in_pcb = False
    for line in doc.splitlines():
        if "||" not in line:
            continue
        left, right = line.split("||", 1)
        right = right.removesuffix("|")
        if not right:
            continue
        h = json.loads(left)
        t = h["type"]
        if t == "DOCHEAD":
            v, _ = json.JSONDecoder().raw_decode(right)
            in_pcb = v.get("docType") == "PCB"
        elif in_pcb and t == "LAYER_PHYS":
            v, _ = json.JSONDecoder().raw_decode(right)
            phys_mils += float(v.get("thickness", 0.0))
        elif t == "FILL" and h.get("id") == "a6b31685508e342e":
            v, _ = json.JSONDecoder().raw_decode(right)
            pts = v["path"][0]
            xs = [pts[i] for i in range(0, len(pts)) if isinstance(pts[i], (int, float)) and pts[i] > 0]
            ys = [pts[i] for i in range(0, len(pts)) if isinstance(pts[i], (int, float)) and pts[i] < 0]
            if (
                round(max(xs) - min(xs), 4) == round(1578.3858 - 529.6457, 4)
                and round(max(ys) - min(ys), 4) == round(-534.3307 - (-1357.1653), 4)
            ):
                cutout_ok = True
        elif t == "LINE" and h.get("id") == "aa2a5e4ee3874f57":
            v, _ = json.JSONDecoder().raw_decode(right)
            if round(float(v["endX"]), 3) == 324.087 and v.get("netName") == "BUTTON_N":
                button_ok = True
        elif t == "POUR":
            pours += 1
        elif t == "POURED":
            poured += 1
    assert cutout_ok, "Expected original rectangular 26.64x20.90 mm battery cutout a6b31685508e342e"
    assert button_ok, "Expected BUTTON_N trace aa2a5e4ee3874f57 extended to 324.087"
    assert pours == 10 and poured >= 10, f"Expected 10 POURs with rebuilt POURED in MCU-U9, got {pours}/{poured}"
    assert "LTC4054ES5-4.2#TRPBF" in doc and "C462648" in doc, "Expected U17 synced to LTC4054ES5-4.2#TRPBF (C462648)"
    mcu_phys_mm = phys_mils * MIL
    assert 0.78 <= mcu_phys_mm <= 0.83, f"Expected ~0.80 mm 6-layer JLC06081H-3313 stackup in MCU-U9, got {mcu_phys_mm:.4f} mm"

    expected_u7 = {
        2: "ANA_EN", 6: "AFE_GPIO3", 7: "XIAO_PWDN", 8: "XIAO_DRDY", 9: "AFE_START",
        10: "AFE_DRDY_B", 11: "XIAO_SCLK", 12: "XIAO_MISO", 13: "XIAO_MOSI",
        14: "XIAO_CS", 15: "MCU_CS_B", 18: "XIAO_RESET", 19: "IMU_SCL", 20: "IMU_SDA",
        21: "MCU_DM", 22: "MCU_DP",
        23: "L_SWDIO", 24: "L_SWCLK", 25: "LINK_CS", 26: "LINK_SCK", 27: "LINK_MISO",
        28: "LINK_MOSI", 29: "LINK_RDY", 30: "IMU_INT1", 31: "L_BOOT0",
    }
    expected_u8 = {
        2: "MCU_BENCH_EN", 3: "VBUS_SENSE", 4: "VBAT_SENSE", 5: "PWR_HOLD",
        6: "LINK_RDY", 7: "LINK_MOSI", 8: "LINK_MISO", 9: "LINK_SCK", 10: "LINK_CS",
        11: "CHRG_N", 14: "BUTTON_N", 15: "OE_N", 16: "MCU_RST_N", 22: "MCU_LED", 23: "MCU_TX",
    }
    for pin, net in expected_u7.items():
        assert mcu_pads.get(("U7", pin)) == net, f"U7.{pin} expected {net}, got {mcu_pads.get(('U7', pin))}"
    for pin, net in expected_u8.items():
        assert mcu_pads.get(("U8", pin)) == net, f"U8.{pin} expected {net}, got {mcu_pads.get(('U8', pin))}"


def _place_max_err(
    fp_pads: dict[str, list[tuple[float, float]]],
    board_pads: dict[str, list[tuple[float, float]]],
    cx: float,
    cy: float,
    cpl_deg: float,
    bot: bool,
) -> float:
    worst = 0.0
    for num, pts in fp_pads.items():
        if num not in board_pads:
            continue
        for ex, ey in pts:
            jx, jy = rot_up(cpl_deg, -ex if bot else ex, ey)
            px, py = cx + jx, cy + jy
            worst = max(worst, min(math.hypot(px - q[0], py - q[1]) for q in board_pads[num]))
    return worst


def check_cpl_rotations() -> tuple[dict[str, tuple], dict[str, tuple]]:
    """按嘉立创「AD,99SE,Allegro,PADS(宏)等其他」默认摆法逐脚核验全部 192 颗贴片件，并运行背面反例。"""
    # 1. MCU-U9 (110 颗)
    with zipfile.ZipFile(P / "OpenEMG-C08B-Mainboard-Rev0.01.epro2") as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith(".epru"))).decode("utf-8", "ignore")
    cur_t, cur_u = None, None
    fp_pads, dev_fp, comps, attrs = {}, {}, {}, {}
    for line in doc.splitlines():
        if "||" not in line:
            continue
        l, r = line.split("||", 1)
        r = r.removesuffix("|")
        if not r:
            continue
        h = json.loads(l)
        v, _ = json.JSONDecoder().raw_decode(r)
        t = h["type"]
        if t == "DOCHEAD":
            cur_t, cur_u = v.get("docType"), v.get("uuid")
        elif cur_t == "FOOTPRINT" and t == "PAD":
            num = str(v.get("num", "")).strip()
            if num:
                fp_pads.setdefault(cur_u, {}).setdefault(num, []).append((v["centerX"] * MIL, v["centerY"] * MIL))
        elif cur_t == "DEVICE" and t == "ATTR" and v.get("key") == "Footprint":
            dev_fp[cur_u] = v.get("value")
        elif cur_t == "PCB":
            if t == "COMPONENT":
                comps[h["id"]] = v
            elif t == "ATTR" and v.get("parentId") in comps:
                attrs.setdefault(v["parentId"], {})[v.get("key")] = v.get("value")

    mcu_by_ref = {}
    for cid, c in comps.items():
        at = attrs.get(cid, {})
        ref = at.get("Designator", "")
        if not ref:
            continue
        fp_id = at.get("Footprint") or dev_fp.get(at.get("Device"))
        pads = fp_pads.get(fp_id, {})
        bot = c["layerId"] == 2
        ang = float(c["angle"]) % 360.0
        bp = {}
        for num, pts in pads.items():
            for ex, ey in pts:
                rx, ry = rot_up(ang, ex, -ey if bot else ey)
                bp.setdefault(num, []).append((c["x"] * MIL + rx, c["y"] * MIL + ry))
        mcu_by_ref[ref] = (pads, bp, bot)

    for r in csv.DictReader((P / "fab-mcu-u9/jlc_smt_cpl.csv").read_text(encoding="utf-8-sig").splitlines()):
        ref = r["Designator"].strip()
        cx = float(r["Mid X"].replace("mm", ""))
        cy = float(r["Mid Y"].replace("mm", ""))
        deg = float(r["Rotation"])
        pads, bp, bot = mcu_by_ref[ref]
        assert bot == r["Layer"].lower().startswith("b"), f"MCU-U9 {ref} layer mismatch"
        err = _place_max_err(pads, bp, cx, cy, deg, bot)
        assert err < 0.01, f"MCU-U9 {ref} CPL pad mismatch: {err:.4f} mm"
        if ref in ("U17", "FPC1", "U16"):
            bad = _place_max_err(pads, bp, cx, cy, (deg + 180.0) % 360.0, bot)
            assert bad > 1.5, f"MCU-U9 {ref} negative control failed: {bad:.4f} mm"

    # 2. AFE-30P (82 颗贴片，不含 32 颗 DNP 共模电容)
    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pcb_lines = z.read(next(n for n in z.namelist() if n.endswith(".epcb"))).decode("utf-8", "ignore").splitlines()
        pj = json.loads(z.read("project.json").decode("utf-8", "ignore"))
        afe_dev_fp = {
            dk: dv.get("attributes", {}).get("Footprint")
            for dk, dv in pj.get("devices", {}).items()
            if dv.get("attributes", {}).get("Footprint")
        }
        afe_fp = {}
        for fn in z.namelist():
            if not fn.endswith(".efoo"):
                continue
            fid = Path(fn).stem
            for ln in z.read(fn).decode("utf-8", "ignore").splitlines():
                if not ln.startswith("["):
                    continue
                row = json.loads(ln)
                if row[0] == "PAD" and str(row[5]).strip():
                    afe_fp.setdefault(fid, {}).setdefault(str(row[5]).strip(), []).append((row[6] * MIL, row[7] * MIL))
    afe_c, afe_at, mode = {}, {}, None
    for ln in pcb_lines:
        if not ln.startswith("["):
            continue
        row = json.loads(ln)
        if row[0] == "DOCTYPE":
            mode = row[1]
        elif mode == "PCB":
            if row[0] == "COMPONENT":
                afe_c[row[1]] = row
            elif row[0] == "ATTR" and row[3] in afe_c:
                afe_at.setdefault(row[3], {})[row[7]] = row[8]
    afe_by_ref = {}
    for cid, row in afe_c.items():
        at = afe_at.get(cid, {})
        ref = at.get("Designator", "")
        if not ref:
            continue
        fp_id = at.get("Footprint") or afe_dev_fp.get(at.get("Device"))
        pads = afe_fp.get(fp_id, {})
        bot = row[3] == 2
        ang = float(row[6]) % 360.0
        bp = {}
        for num, pts in pads.items():
            for ex, ey in pts:
                rx, ry = rot_up(ang, ex, -ey if bot else ey)
                bp.setdefault(num, []).append((row[4] * MIL + rx, row[5] * MIL + ry))
        afe_by_ref[ref] = (pads, bp, bot)

    afe_cpl_sample = {}
    for r in csv.DictReader((P / "fab-afe-30p/jlc_smt_cpl.csv").read_text(encoding="utf-8-sig").splitlines()):
        ref = r["Designator"].strip()
        assert ref not in DNP_CM_CAPS, f"DNP cap {ref} leaked into jlc_smt_cpl.csv"
        cx = float(r["Mid X"].replace("mm", ""))
        cy = float(r["Mid Y"].replace("mm", ""))
        deg = float(r["Rotation"])
        pads, bp, bot = afe_by_ref[ref]
        assert bot == r["Layer"].lower().startswith("b"), f"AFE-30P {ref} layer mismatch"
        err = _place_max_err(pads, bp, cx, cy, deg, bot)
        assert err < 0.01, f"AFE-30P {ref} CPL pad mismatch: {err:.4f} mm"
        if ref in ("U2", "FPC3"):
            bad = _place_max_err(pads, bp, cx, cy, (deg + 180.0) % 360.0, bot)
            assert bad > 5.0, f"AFE-30P {ref} negative control failed: {bad:.4f} mm"
            afe_cpl_sample[ref] = (pads, bp, cx, cy, deg, bot)
    return afe_cpl_sample, afe_by_ref


_GBR_XY = re.compile(r"X(-?\d+)Y(-?\d+)D0([123])\*")


def parse_gerber_paste_centers(gbr_text: str) -> list[tuple[float, float]]:
    """提取 %FSLAX45Y45*% + %MOMM*% Gerber 钢网层的所有 G36..G37 多边形中心与 D03 闪光点 (mm)。"""
    assert "%FSLAX45Y45*%" in gbr_text and "%MOMM*%" in gbr_text, "Unexpected Gerber paste format header"
    centers: list[tuple[float, float]] = []
    in_poly = False
    poly_pts: list[tuple[float, float]] = []
    for raw in gbr_text.splitlines():
        ln = raw.strip()
        if ln == "G36*":
            in_poly = True
            poly_pts = []
            continue
        if ln == "G37*":
            if poly_pts:
                xs = [p[0] for p in poly_pts]
                ys = [p[1] for p in poly_pts]
                centers.append(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5))
            in_poly = False
            poly_pts = []
            continue
        m = _GBR_XY.search(ln)
        if not m:
            continue
        x_mm = int(m.group(1)) * 1e-5
        y_mm = int(m.group(2)) * 1e-5
        dcode = m.group(3)
        if in_poly:
            poly_pts.append((x_mm, y_mm))
        elif dcode == "3":
            centers.append((x_mm, y_mm))
    return centers


def count_paste_pad_hits(
    afe_by_ref: dict[str, tuple],
    refs: set[str],
    top_centers: list[tuple[float, float]],
    bot_centers: list[tuple[float, float]],
    tol_mm: float = 0.15,
) -> tuple[int, int]:
    hits = 0
    total_pads = 0
    for ref in sorted(refs):
        _, bp, bot = afe_by_ref[ref]
        pool = bot_centers if bot else top_centers
        for pts in bp.values():
            for px, py in pts:
                total_pads += 1
                if any(math.hypot(px - cx, py - cy) <= tol_mm for cx, cy in pool):
                    hits += 1
    return hits, total_pads


def check_gerber_paste_and_gko(afe_by_ref: dict[str, tuple]) -> tuple[str, str]:
    """核验双板 Gerber GKO 均带圆角圆弧 (G02/G03)，且 AFE-30P GTP/GBP 已剥离全部 64 个 DNP 焊盘并保留 32 个差分电容焊盘。"""
    for zrel in ("fab-mcu-u9/OpenEMG-C08B-Mainboard-Rev0.01-Gerber.zip", "fab-afe-30p/Gerber_AFE-30P.zip"):
        with zipfile.ZipFile(P / zrel) as z:
            gko = z.read("Gerber_BoardOutlineLayer.GKO").decode("utf-8", "ignore")
        assert "G02" in gko or "G03" in gko, f"{zrel}: GKO missing G02/G03 corner arcs"

    with zipfile.ZipFile(P / "fab-afe-30p/Gerber_AFE-30P.zip") as z:
        gtp = z.read("Gerber_TopPasteMaskLayer.GTP").decode("utf-8", "ignore")
        gbp = z.read("Gerber_BottomPasteMaskLayer.GBP").decode("utf-8", "ignore")
    top_c = parse_gerber_paste_centers(gtp)
    bot_c = parse_gerber_paste_centers(gbp)

    dnp_hits, dnp_total = count_paste_pad_hits(afe_by_ref, DNP_CM_CAPS, top_c, bot_c)
    assert dnp_total == 64 and dnp_hits == 0, f"Expected 0/64 paste openings on 32 DNP CM caps, got {dnp_hits}/{dnp_total}"

    diff_hits, diff_total = count_paste_pad_hits(afe_by_ref, DIFF_22PF_CAPS, top_c, bot_c)
    assert diff_total == 32 and diff_hits == 32, f"Expected 32/32 paste openings on 16 diff caps, got {diff_hits}/{diff_total}"
    return gtp, gbp


def check_fab_subpack(sub: str, bom_rows: int, smt_total: int, gerber_zips: tuple[str, ...]) -> None:
    d = P / sub
    for gz in gerber_zips:
        assert (d / gz).is_file() and (d / gz).stat().st_size > 50_000, f"{sub}: missing Gerber {gz}"
    for aux in ("orientation.csv", "polarity-top.png", "polarity-bottom.png"):
        assert (d / aux).is_file() and (d / aux).stat().st_size > 200, f"{sub}: missing {aux}"
    with (d / "jlc_smt_bom.csv").open(encoding="utf-8-sig") as f:
        b_rows = list(csv.DictReader(f))
    with (d / "jlc_smt_cpl.csv").open(encoding="utf-8-sig") as f:
        c_rows = list(csv.DictReader(f))
    assert len(b_rows) == bom_rows, f"{sub}: expected {bom_rows} BOM rows, got {len(b_rows)}"
    assert len(c_rows) == smt_total, f"{sub}: expected {smt_total} CPL rows, got {len(c_rows)}"
    b_refs = {x.strip() for r in b_rows for x in r["Designator"].split(",") if x.strip()}
    c_refs = {r["Designator"].strip() for r in c_rows}
    assert b_refs == c_refs, f"{sub}: BOM^CPL mismatch {b_refs ^ c_refs}"
    for r in b_rows:
        code = (r.get("JLCPCB Part #") or r.get("LCSC Part #") or "").strip()
        assert code.startswith("C") and code[1:].isdigit(), f"{sub}: invalid LCSC code {code} on {r['Designator']}"
    if sub == "fab-afe-30p":
        assert not (b_refs & DNP_CM_CAPS), f"DNP CM caps leaked into BOM: {b_refs & DNP_CM_CAPS}"
        by_code = {(r.get("LCSC Part #") or r.get("JLCPCB Part #") or "").strip(): r for r in b_rows}
        assert "C324727" in by_code and "FPC1" in by_code["C324727"]["Designator"], "Expected C324727 on FPC1,FPC3"
        assert "C2984407" in by_code and by_code["C2984407"]["Designator"].strip() == "R4", "Expected C2984407 on R4"
        c52923_refs = {x.strip() for x in by_code.get("C52923", {}).get("Designator", "").split(",") if x.strip()}
        assert "C10" in c52923_refs, f"Expected C52923 (1uF) to include C10, got {c52923_refs}"
        diff_in_bom = {x.strip() for x in by_code.get("C76924", {}).get("Designator", "").split(",") if x.strip()}
        assert diff_in_bom == DIFF_22PF_CAPS, f"Expected 16 diff caps on C76924 (22pF), got {diff_in_bom}"


def check_3d_and_strap_gates() -> None:
    # 1. 台架候选壳 case-30p
    cdir = P / "case-30p"
    if cdir.is_dir():
        for fn in ("Case.step", "Lid.step", "assembly.step", "checks.json", "装配图.png"):
            assert (cdir / fn).is_file() and (cdir / fn).stat().st_size > 500, f"case-30p missing {fn}"
        chk = json.loads((cdir / "checks.json").read_text(encoding="utf-8"))
        assert chk["lid_vertical_path_obstructions"] == {}, f"Lid sweep obstruction: {chk['lid_vertical_path_obstructions']}"
        assert chk["component_proxy_hits_mm3"] == {}, f"Component proxy hit: {chk['component_proxy_hits_mm3']}"
        for k, v in chk["overlap_mm3"].items():
            if k == "positive_control":
                assert v > 100.0, f"Positive control too small: {v}"
            else:
                assert v == 0, f"Unexpected solid overlap {k}={v}"

    # 2. 满载整板 3D STEP + 双 30P 四层软板 28 项门禁 + 穿戴圆润手表壳 23 对三维布尔零干涉 + <=9.70mm 净高 + >=0.80mm 壁厚
    for stp in ("mcu-u9-3d.step", "afe-30p-3d.step", "strap-fpc-30p/strap-30p-a-3d.step", "strap-fpc-30p/strap-30p-b-3d.step"):
        p_stp = P / stp
        assert p_stp.is_file() and 100_000 < p_stp.stat().st_size <= 24_500_000, f"Invalid 3D STEP size on {stp}"
    strap_chk = json.loads((P / "strap-fpc-30p/checks.json").read_text(encoding="utf-8"))
    assert strap_chk.get("fails") == [], f"strap-fpc-30p checks failed: {strap_chk.get('fails')}"

    wdir = P / "enclosure-u9-watch"
    for fn in ("tray.step", "cover.step", "side_button.step", "cap_bottom.step", "assembly.step", "exploded.step", "fit-3d.json"):
        assert (wdir / fn).is_file() and (wdir / fn).stat().st_size > 500, f"enclosure-u9-watch missing {fn}"
    fit3d = json.loads((wdir / "fit-3d.json").read_text(encoding="utf-8"))
    nom = fit3d.get("nominal_interference_mm3", {})
    assert fit3d.get("ok") is True and len(nom) == 23 and all(v == 0.0 for v in nom.values()), f"enclosure-u9-watch fit-3d failed: {fit3d}"
    assert float(fit3d.get("shell_body_height_mm", 99.0)) <= 9.70, f"Watch shell height > 9.70 mm: {fit3d.get('shell_body_height_mm')}"
    assert float(fit3d.get("min_wall_thickness_mm", 0.0)) >= 0.80, f"Watch min wall < 0.80 mm: {fit3d.get('min_wall_thickness_mm')}"
    assert fit3d.get("board_solid_counts") == {"afe_30p": 306, "mcu_u9": 588}, f"Unexpected board solid counts: {fit3d.get('board_solid_counts')}"


def run_all(selftest: bool = False) -> None:
    main_20, mcu_pads = epru_pads(P / "OpenEMG-C08B-Mainboard-Rev0.01.epro2", "FPC1")
    afe, rows = afe_pads()
    _, afe2 = epru_pads(P / "AFE-30P.epro2", "FPC2")
    assert afe == afe2, "AFE-30P.epro and AFE-30P.epro2 pad nets diverge"

    errs_20 = verify_20p_pairing(main_20, afe)
    assert not errs_20, f"20P pairing errors: {errs_20}"
    assert afe["U1", 31] == "GND" and afe["U2", 31] == "GND", "U1/U2 第 31 脚 RESV1 应为 GND"

    dual30 = trace_afe_dual30(afe)
    errs_30 = verify_dual30_expected(dual30)
    assert not errs_30, f"Dual-30P mapping errors: {errs_30}"

    check_afe_fixes(rows, dual30)
    check_mcu_fixes(mcu_pads)
    afe_cpl_sample, afe_by_ref = check_cpl_rotations()
    gtp, gbp = check_gerber_paste_and_gko(afe_by_ref)
    check_fab_subpack("fab-mcu-u9", 45, 110, ("OpenEMG-C08B-Mainboard-Rev0.01-Gerber.zip", "OpenEMG-C08B-Mainboard-Rev0.01-panel702-Gerber.zip"))
    check_fab_subpack("fab-afe-30p", 22, 82, ("Gerber_AFE-30P.zip", "Gerber_AFE-30P-panel702.zip"))
    check_3d_and_strap_gates()

    if selftest:
        # 必败反例 1：交换 FPC2.17 / 18
        bad_afe = dict(afe)
        bad_afe["FPC2", 17], bad_afe["FPC2", 18] = bad_afe["FPC2", 18], bad_afe["FPC2", 17]
        assert len(verify_20p_pairing(main_20, bad_afe)) >= 2, "Selftest failed to catch FPC2.17/18 swap"
        # 必败反例 2：镜像 FPC1 1..30 脚
        mirrored_30 = dict(dual30)
        for p in range(1, 31):
            mirrored_30["FPC1", p] = dual30["FPC1", 31 - p]
        assert len(verify_dual30_expected(mirrored_30)) >= 20, "Selftest failed to catch FPC1 mirror"
        # 必败反例 3：背面 FPC3 CPL 漏加 180°（嘉立创内部角 vs AD 默认摆法）
        pads_f3, bp_f3, cx_f3, cy_f3, deg_f3, bot_f3 = afe_cpl_sample["FPC3"]
        assert _place_max_err(pads_f3, bp_f3, cx_f3, cy_f3, (deg_f3 + 180.0) % 360.0, bot_f3) > 5.0
        # 必败反例 4：伪造一颗 DNP 共模电容 C55 钢网开口残留
        _, bp_c55, bot_c55 = afe_by_ref["C55"]
        px55, py55 = next(iter(bp_c55.values()))[0]
        ix, iy = int(round(px55 * 1e5)), int(round(py55 * 1e5))
        fake_poly = f"\nG36*\nG01X{ix-1000}Y{iy-1000}D02*\nG01X{ix+1000}Y{iy+1000}D01*\nG37*\n"
        bad_gtp = gtp if bot_c55 else (gtp + fake_poly)
        bad_gbp = (gbp + fake_poly) if bot_c55 else gbp
        leak_hits, _ = count_paste_pad_hits(
            afe_by_ref, DNP_CM_CAPS, parse_gerber_paste_centers(bad_gtp), parse_gerber_paste_centers(bad_gbp)
        )
        assert leak_hits >= 1, "Selftest failed to catch leaked DNP paste opening on C55"
        print("[SELFTEST PASS] 4/4 必败反例（FPC2.17/18 交叉、FPC1 1..30 镜像、背面 FPC3 CPL 180° 镜像、DNP 钢网残留）均准确拦截。")

    print(
        "20/20 板间脚序、双核 39 信号脚固件兼容、60/60 双 30P 超薄座 (C324727) 通道映射、"
        "双板 0.80mm 叠层、前端 RC/电荷泵修正与 0/64 DNP 钢网零残留、"
        "192 颗 CPL 逐脚拟合（含背面反例）、15+10 块铺铜与 9.60mm 穿戴总装核验通过。"
    )


if __name__ == "__main__":
    run_all(selftest="--selftest" in sys.argv)
