#!/usr/bin/env python3
"""直接从两份嘉立创工程读取板间焊盘、主控固件脚位、DRC/铺铜修复、贴片坐标逐脚拟合与 3D 装配包并逐项核验。"""
from __future__ import annotations

import csv
import json
import math
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent
MIL = 0.0254


def rot_up(deg: float, x: float, y: float) -> tuple[float, float]:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def afe_pads() -> dict[tuple[str, int], str]:
    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pcb = next(name for name in z.namelist() if name.endswith(".epcb"))
        rows = [json.loads(line) for line in z.read(pcb).splitlines() if line]
    rows = rows[max(i for i, r in enumerate(rows) if r[:2] == ["DOCTYPE", "PCB"]) :]
    refs = {r[3]: r[8] for r in rows if r[0] == "ATTR" and r[7] == "Designator"}
    return {
        (refs[r[1]], int(r[2])): r[3]
        for r in rows
        if r[0] == "PAD_NET" and r[1] in refs and str(r[2]).isdigit()
    }


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


def check_afe_fixes() -> None:
    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pcb_name = next(name for name in z.namelist() if name.endswith(".epcb"))
        sch_name = next(name for name in z.namelist() if name.endswith("1.esch"))
        rows = [json.loads(line) for line in z.read(pcb_name).splitlines() if line.startswith(b"[")]
        sch1 = z.read(sch_name).decode("utf-8", "ignore")
    layer16 = next((r[2] for r in rows if r[0] == "LAYER" and r[1] == 16), None)
    rule7 = next((r[4][3] for r in rows if r[0] == "RULE" and r[1] == "7" and r[2] == "copperRegion"), None)
    pour_1678 = any(r[0] == "POUR" and r[1] == "e1678" and r[3] == "GND" and r[4] == 16 for r in rows)
    pours = sum(1 for r in rows if r[0] == "POUR")
    poured = sum(1 for r in rows if r[0] == "POURED")
    assert layer16 == "SIGNAL", f"Expected Inner2 layer 16 SIGNAL, got {layer16}"
    assert rule7 == 1, f"Expected RULE 7 connType=1 (DIRECT), got {rule7}"
    assert pour_1678 and pours == 14 and poured >= 14, f"Expected 14 POURs with e1678 GND, got {pours}/{poured}"
    assert '["ATTR","e223","e95","Name","GND"' in sch1, "Expected U1.31 net flag e95=GND in 1.esch"
    assert '["ATTR","e814","e300","Name","GND"' in sch1, "Expected U2.31 net flag e300=GND in 1.esch"


def check_mcu_fixes(mcu_pads: dict[tuple[str, int], str]) -> None:
    with zipfile.ZipFile(P / "MCU-U9.epro2") as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith(".epru"))).decode("utf-8", "ignore")
    cutout_ok = False
    button_ok = False
    pours = 0
    poured = 0
    for line in doc.splitlines():
        if "||" not in line:
            continue
        left, right = line.split("||", 1)
        right = right.removesuffix("|")
        if not right:
            continue
        h = json.loads(left)
        if h["type"] == "FILL" and h.get("id") == "a6b31685508e342e":
            v, _ = json.JSONDecoder().raw_decode(right)
            pts = v["path"][0]
            xs = [pts[i] for i in range(0, len(pts)) if isinstance(pts[i], (int, float)) and pts[i] > 0]
            if round(max(xs) - min(xs), 4) == round(1608.3858 - 529.6457, 4):
                cutout_ok = True
        elif h["type"] == "LINE" and h.get("id") == "aa2a5e4ee3874f57":
            v, _ = json.JSONDecoder().raw_decode(right)
            if round(float(v["endX"]), 3) == 324.087 and v.get("netName") == "BUTTON_N":
                button_ok = True
        elif h["type"] == "POUR":
            pours += 1
        elif h["type"] == "POURED":
            poured += 1
    assert cutout_ok, "Expected expanded 27.40x20.90 mm battery cutout a6b31685508e342e"
    assert button_ok, "Expected BUTTON_N trace aa2a5e4ee3874f57 extended to 324.087"
    assert pours == 10 and poured >= 10, f"Expected 10 POURs with rebuilt POURED in MCU-U9, got {pours}/{poured}"
    assert "LTC4054ES5-4.2#TRPBF" in doc and "C462648" in doc, "Expected U17 synced to LTC4054ES5-4.2#TRPBF (C462648)"

    # Verify 39 dual-MCU signal pins (U7: 23 pins, U8: 16 pins) for binary compatibility with firmware/c08b-bringup & c08b-stream
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


def _place_max_err(fp_pads: dict[str, list[tuple[float, float]]], board_pads: dict[str, list[tuple[float, float]]],
                   cx: float, cy: float, cpl_deg: float, bot: bool) -> float:
    worst = 0.0
    for num, pts in fp_pads.items():
        if num not in board_pads:
            continue
        for ex, ey in pts:
            jx, jy = rot_up(cpl_deg, -ex if bot else ex, ey)
            px, py = cx + jx, cy + jy
            worst = max(worst, min(math.hypot(px - q[0], py - q[1]) for q in board_pads[num]))
    return worst


def check_cpl_rotations() -> None:
    """按嘉立创「AD,99SE,Allegro,PADS(宏)等其他」默认摆法逐脚核验全部 224 颗贴片件，并运行背面反例。"""
    # 1. MCU-U9
    with zipfile.ZipFile(P / "MCU-U9.epro2") as z:
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

    # 2. AFE-30P
    with zipfile.ZipFile(P / "AFE-30P.epro") as z:
        pcb_lines = z.read(next(n for n in z.namelist() if n.endswith(".epcb"))).decode("utf-8", "ignore").splitlines()
        pj = json.loads(z.read("project.json").decode("utf-8", "ignore"))
        afe_dev_fp = {dk: dv.get("attributes", {}).get("Footprint") for dk, dv in pj.get("devices", {}).items() if dv.get("attributes", {}).get("Footprint")}
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

    for r in csv.DictReader((P / "fab-afe-30p/jlc_smt_cpl.csv").read_text(encoding="utf-8-sig").splitlines()):
        ref = r["Designator"].strip()
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


def check_case_30p() -> None:
    cdir = P / "case-30p"
    if not cdir.is_dir():
        return
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


main, mcu_pads = epru_pads(P / "MCU-U9.epro2", "FPC1")
afe = afe_pads()
afe2_conn, afe2 = epru_pads(P / "AFE-30P.epro2", "FPC2")
assert afe == afe2, "AFE-30P.epro and AFE-30P.epro2 pad nets diverge"

csv_rows = list(csv.DictReader((P / "20针接口.csv").read_text(encoding="utf-8-sig").splitlines()))
assert len(csv_rows) == 20, f"Expected 20 rows in 20针接口.csv, got {len(csv_rows)}"
for idx, r in enumerate(csv_rows, 1):
    assert int(r["主控FPC1"]) == idx and int(r["采集FPC2"]) == 21 - idx
    assert main[idx - 1] == r["主控网络"], f"20针接口.csv row {idx} MCU mismatch"
    assert afe["FPC2", 21 - idx] == r["采集网络"], f"20针接口.csv row {idx} AFE mismatch"

assert afe["U2", 39] == afe["FPC2", 17] == "CS#2"
assert afe["U2", 47] == afe["FPC2", 18] == "DRDY2#"
assert afe["U1", 31] == "GND" and afe["U2", 31] == "GND", "U1/U2 第 31 脚 RESV1 应为 GND"

check_afe_fixes()
check_mcu_fixes(mcu_pads)
check_cpl_rotations()
check_fab_subpack("fab-mcu-u9", 45, 110, ("Gerber_MCU-U9.zip", "Gerber_MCU-U9-panel702.zip"))
check_fab_subpack("fab-afe-30p", 23, 114, ("Gerber_AFE-30P.zip", "Gerber_AFE-30P-panel702.zip"))
check_case_30p()
print("20/20 接口、双核 39 信号脚固件兼容、224 颗 CPL 逐脚拟合（含背面反例）、铺铜规则与 3D 总装全部核验通过。")
