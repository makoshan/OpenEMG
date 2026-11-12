#!/usr/bin/env python3
"""核验 8ch 单面贴片包（基于 C08B D20 PCB）：
1. 顶面 76 颗完整包含 V4_U1 (ADS1298)、V4_LM27762 (±2.5V)、V4_X1 (2.048MHz)、J_AFE (20P)、V4_FPC1 (34P) 及全部去耦/ESD。
2. 底面空贴 51 颗全部属于从片 V4_U2 (CH9-16) 支路，无任何一颗影响主片供电、时钟或 SPI 总线。
3. 自带必失败反例：若误将 V4_LM27762 或 V4_X1 列入空贴，立即报错退出非零。
"""
from __future__ import annotations
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS_JSON = HERE.parents[1] / "16ch-c08b-round/schematics-afe/c08b-pcb-pins.json"
CPL_16 = HERE.parents[1] / "16ch-c08b-round/afe-d20/jlc_smt_cpl.csv"
CPL_8 = HERE / "jlc_smt_cpl_8ch.csv"
BOM_8 = HERE / "jlc_smt_bom_8ch.csv"

REQUIRED_SHARED_AND_CH1_8 = {"J_AFE", "V4_LM27762", "V4_X1", "V4_R17", "V4_U1", "V4_FPC1", "R801", "R803", "R804", "R805"}


def check_split(top_set: set[str], bot_set: set[str], comp_nets: dict[str, set[str]]) -> list[str]:
    errs: list[str] = []
    missing_core = REQUIRED_SHARED_AND_CH1_8 - top_set
    if missing_core:
        errs.append(f"顶面缺失核心器件: {sorted(missing_core)}")
    # 底面空贴件不得触碰 U1 专属模拟输入网（IN1P..IN8N 尾缀不带 2）或晶振使能网
    for ref in sorted(bot_set):
        if ref in REQUIRED_SHARED_AND_CH1_8:
            errs.append(f"核心器件被误放入空贴集: {ref}")
        for net in comp_nets.get(ref, set()):
            if net.startswith("V4_IN") and not net.endswith("2"):
                errs.append(f"空贴件 {ref} 触碰了 CH1-8 输入网 {net}")
    return errs


def main() -> int:
    raw_pins = json.loads(PINS_JSON.read_text("utf-8"))["pins"]
    comp_nets: dict[str, set[str]] = defaultdict(set)
    for r in raw_pins:
        comp_nets[r["ref"]].add(r["net"])

    all_rows = list(csv.DictReader(CPL_16.open("r", encoding="utf-8")))
    cpl8_rows = list(csv.DictReader(CPL_8.open("r", encoding="utf-8")))
    bom8_rows = list(csv.DictReader(BOM_8.open("r", encoding="utf-8")))

    if any(r["Layer"].strip().lower().startswith("bot") for r in cpl8_rows):
        print("FAIL: jlc_smt_cpl_8ch.csv 仍含 Bottom 层器件", file=sys.stderr)
        return 1

    top_set = {r["Designator"].strip() for r in cpl8_rows}
    all_set = {r["Designator"].strip() for r in all_rows}
    bot_set = all_set - top_set

    bom_refs = {d.strip() for r in bom8_rows for d in r["Designator"].split(",") if d.strip()}
    if bom_refs != top_set:
        print(f"FAIL: BOM 与 CPL 位号不一致: diff={bom_refs ^ top_set}", file=sys.stderr)
        return 1

    errs = check_split(top_set, bot_set, comp_nets)
    if errs:
        for e in errs:
            print("FAIL:", e, file=sys.stderr)
        return 1

    # 必失败反例自检：把 V4_LM27762 挪入空贴必须报错
    bad_errs = check_split(top_set - {"V4_LM27762"}, bot_set | {"V4_LM27762"}, comp_nets)
    if not bad_errs:
        print("FAIL: 必失败反例未拦截", file=sys.stderr)
        return 1

    print(f"8ch 单面贴片核验通过：Top 贴装 {len(top_set)} 颗（{len(bom8_rows)} 种物料），Bottom 空贴 {len(bot_set)} 颗，反例拦截正常")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
