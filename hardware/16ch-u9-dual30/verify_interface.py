#!/usr/bin/env python3
"""直接从两份嘉立创工程读取板间焊盘并核验 DRC/网表修复与制造包。运行 python3 verify_interface.py。"""
import csv
import json
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent


def afe_pads():
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


def epru_pads(zpath, conn_des):
    with zipfile.ZipFile(zpath) as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith(".epru")))
    active = False
    pads, connectors, des_by_id = {}, set(), {}
    for line in doc.decode().splitlines():
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


def check_afe_fixes():
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


def check_mcu_fixes():
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


def check_fab_subpack(sub, bom_rows, smt_total):
    d = P / sub
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


main, _ = epru_pads(P / "MCU-U9.epro2", "FPC1")
afe = afe_pads()
afe2_conn, afe2 = epru_pads(P / "AFE-30P.epro2", "FPC2")
assert afe == afe2, "AFE-30P.epro and AFE-30P.epro2 pad nets diverge"

expected_main = [
    "GND",
    "",
    "AFE_DRDY_B",
    "AFE_CS_B",
    "AFE_DIN",
    "AFE_PWDN",
    "AFE_RESET",
    "",
    "AFE_START",
    "AFE_CS_A",
    "AFE_SCLK",
    "GND",
    "",
    "GND",
    "DOUT_B",
    "AFE_GPIO3",
    "ADS_DRDY_A",
    "",
    "3V3_AFE",
    "3V3_AFE",
]
expected_afe = [
    "GND",
    "GND",
    "DRDY2#",
    "CS#2",
    "DIN",
    "PWDN#",
    "RESET#",
    "CLK",
    "START",
    "CS#",
    "SCLK",
    "GND",
    "GND",
    "GND",
    "DOUT",
    "GPIO3",
    "DRDY#",
    "CLKSEL",
    "+3.3V",
    "+3.3V",
]
for i, (host, target) in enumerate(zip(expected_main, expected_afe), 1):
    assert (main[i - 1], afe["FPC2", 21 - i]) == (host, target), f"主控第 {i} 脚不匹配"
assert afe["U2", 39] == afe["FPC2", 17] and afe["U2", 47] == afe["FPC2", 18]
assert afe["U1", 31] == "GND" and afe["U2", 31] == "GND", "U1/U2 第 31 脚 RESV1 应为 GND"
check_afe_fixes()
check_mcu_fixes()
check_fab_subpack("fab-mcu-u9", 45, 110)
check_fab_subpack("fab-afe-30p", 23, 114)
print("20/20 脚与预期配对一致，U2 的 39/47 脚、U1/U2.31=GND、铺铜规则与制造包已全部核验通过。")
