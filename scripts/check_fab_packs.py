#!/usr/bin/env python3
"""OpenEMG 全家族 15 套嘉立创直接上传制造包完整性与一致性门禁（纯 Python 3.12 标准库，含 --selftest 5 项必失败反例）。

核验范围：
1. 全家族 15 套直接上传制造包（01..15：主控 R4U6/R4U6N、8ch D20-8CH/D20N-8CH、8ch 软板 D2-8CH、
   16ch D20/D20N、16ch 软板 D2 A/B、2ch ADS1292-R9、转接板 P44e、新版 6 层圆角主控 MCU-U9、
   新版超薄双 30P 采集板 AFE-30P、新版双 30P 四层软板 strap-30p A/B）
   全部在仓内自包含存在，零外部下载目录依赖。
2. 逐包校验 Gerber.zip、BOM.csv、CPL.csv 与软板 .d356 的 SHA-256 指纹前缀锁定。
3. 穿透每个 Gerber.zip，核验铜层数（6 层、4 层或 P44e 2 层）、板框层、镀铜钻孔层非空，
   且 5 套表带四层软板必须包含拆分厚度的 0.10mm 与 0.20mm 实心 PI 补强 Gerber 层。
4. 解析全部 14 套 SMT 包的 BOM.csv 与 CPL.csv：
   - 核验立创料号格式（Cxxxx）、Quantity 与位号个数一致、零重复位号；
   - 核验 BOM 展开位号集合与 CPL 位号集合 1:1 完全相等（零孤儿、零漏贴）；
   - 核验 Top / Bottom 贴片层颗数精确等于锁定值（单面板断言 Bottom 颗数 = 0）。
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FabPackSpec:
    pack_id: str
    gerber_zip: str
    gerber_sha_prefix: str
    cu_layers: int
    is_fpc: bool = False
    bom_csv: str | None = None
    bom_sha_prefix: str | None = None
    cpl_csv: str | None = None
    cpl_sha_prefix: str | None = None
    d356_file: str | None = None
    d356_sha_prefix: str | None = None
    bom_rows: int = 0
    top_count: int = 0
    bot_count: int = 0


PACK_SPECS: tuple[FabPackSpec, ...] = (
    FabPackSpec(
        pack_id="01-mainboard-r4u6",
        gerber_zip="hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6-gerber.zip",
        gerber_sha_prefix="b714cccc443c646e",
        cu_layers=4,
        bom_csv="hardware/common-mainboard/mainboard-r4u6/jlc_smt_bom.csv",
        bom_sha_prefix="038dde47ae949409",
        cpl_csv="hardware/common-mainboard/mainboard-r4u6/jlc_smt_cpl.csv",
        cpl_sha_prefix="ac566c41c54efdce",
        bom_rows=47,
        top_count=66,
        bot_count=43,
    ),
    FabPackSpec(
        pack_id="02-mainboard-r4u6n",
        gerber_zip="hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N-gerber.zip",
        gerber_sha_prefix="68ef0932d104c68f",
        cu_layers=4,
        bom_csv="hardware/common-mainboard/mainboard-r4u6n/jlc_smt_bom.csv",
        bom_sha_prefix="038dde47ae949409",
        cpl_csv="hardware/common-mainboard/mainboard-r4u6n/jlc_smt_cpl.csv",
        cpl_sha_prefix="ac566c41c54efdce",
        bom_rows=47,
        top_count=66,
        bot_count=43,
    ),
    FabPackSpec(
        pack_id="03-8ch-afe-d20-8ch",
        gerber_zip="hardware/8ch-ads1298/afe-d20-8ch/fab/panel/c08b-afe-d20-8ch-panel-gerber.zip",
        gerber_sha_prefix="adefd36d29bb21ad",
        cu_layers=4,
        bom_csv="hardware/8ch-ads1298/afe-d20-8ch/fab/jlc_smt_bom.csv",
        bom_sha_prefix="4d330ad0a38bb4f6",
        cpl_csv="hardware/8ch-ads1298/afe-d20-8ch/fab/jlc_smt_cpl.csv",
        cpl_sha_prefix="ba082820fd36bf74",
        bom_rows=24,
        top_count=76,
        bot_count=0,
    ),
    FabPackSpec(
        pack_id="04-8ch-afe-d20n-8ch",
        gerber_zip="hardware/8ch-ads1298/afe-d20n-8ch/fab/panel/c08b-afe-d20n-8ch-panel-gerber.zip",
        gerber_sha_prefix="82ba95e5bf7ceb80",
        cu_layers=4,
        bom_csv="hardware/8ch-ads1298/afe-d20n-8ch/fab/jlc_smt_bom.csv",
        bom_sha_prefix="4d330ad0a38bb4f6",
        cpl_csv="hardware/8ch-ads1298/afe-d20n-8ch/fab/jlc_smt_cpl.csv",
        cpl_sha_prefix="ba082820fd36bf74",
        bom_rows=24,
        top_count=76,
        bot_count=0,
    ),
    FabPackSpec(
        pack_id="05-8ch-strap-fpc-d2-8ch",
        gerber_zip="hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/strap-d2-8ch-gerber.zip",
        gerber_sha_prefix="7ed551d45673be10",
        cu_layers=4,
        is_fpc=True,
        bom_csv="hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/jlc_smt_bom.csv",
        bom_sha_prefix="5ec689fdd81b3efc",
        cpl_csv="hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/jlc_smt_cpl.csv",
        cpl_sha_prefix="5c1213bdb81f0632",
        d356_file="hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/strap-d2-8ch.d356",
        d356_sha_prefix="86a917c5c54d3c83",
        bom_rows=2,
        top_count=12,
        bot_count=6,
    ),
    FabPackSpec(
        pack_id="06-16ch-afe-d20",
        gerber_zip="hardware/16ch-c08b-round/afe-d20/panel/c08b-afe-d20-panel-gerber.zip",
        gerber_sha_prefix="a5f52ffe98ec4ae0",
        cu_layers=4,
        bom_csv="hardware/16ch-c08b-round/afe-d20/jlc_smt_bom.csv",
        bom_sha_prefix="445bea42d74e8516",
        cpl_csv="hardware/16ch-c08b-round/afe-d20/jlc_smt_cpl.csv",
        cpl_sha_prefix="0c6c4d2299593026",
        bom_rows=24,
        top_count=76,
        bot_count=51,
    ),
    FabPackSpec(
        pack_id="07-16ch-afe-d20n",
        gerber_zip="hardware/16ch-c08b-round/afe-d20n/panel/c08b-afe-d20n-panel-gerber.zip",
        gerber_sha_prefix="511283a66f59d04a",
        cu_layers=4,
        bom_csv="hardware/16ch-c08b-round/afe-d20n/jlc_smt_bom.csv",
        bom_sha_prefix="445bea42d74e8516",
        cpl_csv="hardware/16ch-c08b-round/afe-d20n/jlc_smt_cpl.csv",
        cpl_sha_prefix="0c6c4d2299593026",
        bom_rows=24,
        top_count=76,
        bot_count=51,
    ),
    FabPackSpec(
        pack_id="08-16ch-strap-fpc-d2-a",
        gerber_zip="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-gerber.zip",
        gerber_sha_prefix="b7aa2a0929347eff",
        cu_layers=4,
        is_fpc=True,
        bom_csv="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-jlc-bom.csv",
        bom_sha_prefix="8f02ec3046a201c5",
        cpl_csv="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-jlc-cpl.csv",
        cpl_sha_prefix="d61ce0af6d76d476",
        d356_file="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a.d356",
        d356_sha_prefix="2a6397379717b406",
        bom_rows=2,
        top_count=12,
        bot_count=5,
    ),
    FabPackSpec(
        pack_id="09-16ch-strap-fpc-d2-b",
        gerber_zip="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-gerber.zip",
        gerber_sha_prefix="431751560e692bbd",
        cu_layers=4,
        is_fpc=True,
        bom_csv="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-jlc-bom.csv",
        bom_sha_prefix="cffbbd762a43c68c",
        cpl_csv="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-jlc-cpl.csv",
        cpl_sha_prefix="a45ef4a26777a4a4",
        d356_file="hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b.d356",
        d356_sha_prefix="b91204df384c8f79",
        bom_rows=2,
        top_count=16,
        bot_count=1,
    ),
    FabPackSpec(
        pack_id="10-2ch-ads1292-r9",
        gerber_zip="hardware/2ch-ads1292/board/fab/ads1292-2ch-panel-gerber.zip",
        gerber_sha_prefix="bdd44d3152454e9e",
        cu_layers=4,
        bom_csv="hardware/2ch-ads1292/board/fab/jlc_smt_bom.csv",
        bom_sha_prefix="614e0854fc13af44",
        cpl_csv="hardware/2ch-ads1292/board/fab/jlc_smt_cpl.csv",
        cpl_sha_prefix="2a2bc50e266dc316",
        bom_rows=22,
        top_count=47,
        bot_count=0,
    ),
    FabPackSpec(
        pack_id="11-adapter-p44e-xiao",
        gerber_zip="hardware/common-mainboard/adapter-p44e-xiao/fab-20261106/p44e-gerber.zip",
        gerber_sha_prefix="044240f64b3436a4",
        cu_layers=2,
    ),
    FabPackSpec(
        pack_id="12-16ch-u9-mcu-u9",
        gerber_zip="hardware/16ch-u9-dual30/fab-mcu-u9/OpenEMG-C08B-Mainboard-Rev0.01-panel702-Gerber.zip",
        gerber_sha_prefix="f45c32339db15145",
        cu_layers=6,
        bom_csv="hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_bom.csv",
        bom_sha_prefix="a20d1163277c3bd6",
        cpl_csv="hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_cpl.csv",
        cpl_sha_prefix="f1fc25052719958c",
        bom_rows=45,
        top_count=42,
        bot_count=68,
    ),
    FabPackSpec(
        pack_id="13-16ch-u9-afe-30p",
        gerber_zip="hardware/16ch-u9-dual30/fab-afe-30p/Gerber_AFE-30P-panel702.zip",
        gerber_sha_prefix="e986cb1f1304497b",
        cu_layers=4,
        bom_csv="hardware/16ch-u9-dual30/fab-afe-30p/jlc_smt_bom.csv",
        bom_sha_prefix="458954e0b51def98",
        cpl_csv="hardware/16ch-u9-dual30/fab-afe-30p/jlc_smt_cpl.csv",
        cpl_sha_prefix="05bb9036cbccb8d6",
        bom_rows=22,
        top_count=48,
        bot_count=34,
    ),
    FabPackSpec(
        pack_id="14-16ch-u9-strap-30p-a",
        gerber_zip="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-gerber.zip",
        gerber_sha_prefix="16e9cea8fdf6ae15",
        cu_layers=4,
        is_fpc=True,
        bom_csv="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-jlc-bom.csv",
        bom_sha_prefix="8f02ec3046a201c5",
        cpl_csv="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-jlc-cpl.csv",
        cpl_sha_prefix="d61ce0af6d76d476",
        d356_file="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a.d356",
        d356_sha_prefix="e660b6029004d619",
        bom_rows=2,
        top_count=12,
        bot_count=5,
    ),
    FabPackSpec(
        pack_id="15-16ch-u9-strap-30p-b",
        gerber_zip="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-gerber.zip",
        gerber_sha_prefix="c0e6164729913a07",
        cu_layers=4,
        is_fpc=True,
        bom_csv="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-jlc-bom.csv",
        bom_sha_prefix="cffbbd762a43c68c",
        cpl_csv="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-jlc-cpl.csv",
        cpl_sha_prefix="a45ef4a26777a4a4",
        d356_file="hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b.d356",
        d356_sha_prefix="ff42b45b60e7fcb0",
        bom_rows=2,
        top_count=16,
        bot_count=1,
    ),
)

LCSC_PART_RE = re.compile(r"^C[1-9]\d{2,}$")
COORD_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:mm)?$", re.IGNORECASE)


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_gerber_zip(zip_path: Path, spec: FabPackSpec) -> list[str]:
    errs: list[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_member = zf.testzip()
            if bad_member is not None:
                return [f"{spec.pack_id}: Gerber 压缩包损坏成员 {bad_member}"]
            infos = [zi for zi in zf.infolist() if not zi.is_dir()]
    except zipfile.BadZipFile as exc:
        return [f"{spec.pack_id}: 非法 ZIP 文件 ({exc})"]

    names = [zi.filename for zi in infos]
    lower_names = [n.lower() for n in names]
    empty_files = [zi.filename for zi in infos if zi.file_size == 0]
    if empty_files:
        errs.append(f"{spec.pack_id}: Gerber 压缩包含空文件 {empty_files}")

    has_top_cu = any(n.endswith((".gtl", "f_cu.gbr", "toplayer.gtl")) for n in lower_names)
    has_bot_cu = any(n.endswith((".gbl", "b_cu.gbr", "bottomlayer.gbl")) for n in lower_names)
    in_cu = [
        n
        for n in lower_names
        if n.endswith((".g1", ".g2", ".g3", ".g4", "in1_cu.gbr", "in2_cu.gbr", "in3_cu.gbr", "in4_cu.gbr"))
    ]
    cu_found = (1 if has_top_cu else 0) + (1 if has_bot_cu else 0) + len(in_cu)
    if cu_found != spec.cu_layers:
        errs.append(f"{spec.pack_id}: 铜层文件数 {cu_found} != 期望 {spec.cu_layers} ({names})")

    has_outline = any(n.endswith((".gko", ".gm1", "edge_cuts.gbr")) for n in lower_names)
    if not has_outline:
        errs.append(f"{spec.pack_id}: 缺少板框层 (.gko/.gm1/Edge_Cuts.gbr)")

    has_pth = any("pth" in n and n.endswith(".drl") and "npth" not in n for n in lower_names)
    if not has_pth:
        errs.append(f"{spec.pack_id}: 缺少镀铜钻孔文件 (*PTH*.drl)")

    if spec.is_fpc:
        has_stiff_010 = any(n.endswith("bot_stiff_0p10mm_pi.gbr") for n in lower_names)
        has_stiff_020 = any(n.endswith("bot_stiff_0p20mm_pi.gbr") for n in lower_names)
        if not (has_stiff_010 and has_stiff_020):
            errs.append(f"{spec.pack_id}: 四层软板缺少 0.10mm 或 0.20mm 实心 PI 补强 Gerber 层")

    return errs


def _check_bom_cpl(bom_path: Path, cpl_path: Path, spec: FabPackSpec) -> list[str]:
    errs: list[str] = []
    bom_rows = list(csv.DictReader(io.StringIO(bom_path.read_text(encoding="utf-8-sig"))))
    cpl_rows = list(csv.DictReader(io.StringIO(cpl_path.read_text(encoding="utf-8-sig"))))

    if len(bom_rows) != spec.bom_rows:
        errs.append(f"{spec.pack_id}: BOM 行数 {len(bom_rows)} != 期望 {spec.bom_rows}")

    bom_refs: list[str] = []
    for idx, row in enumerate(bom_rows, start=2):
        lcsc = (row.get("LCSC Part #") or row.get("JLCPCB Part #") or "").strip()
        if not LCSC_PART_RE.match(lcsc):
            errs.append(f"{spec.pack_id}: BOM 第 {idx} 行立创料号非法 '{lcsc}'")
        raw_des = (row.get("Designator") or "").strip()
        refs = [r.strip() for r in raw_des.split(",") if r.strip()]
        if not refs:
            errs.append(f"{spec.pack_id}: BOM 第 {idx} 行位号为空")
        qty_str = (row.get("Quantity") or "").strip()
        if qty_str:
            try:
                qty = int(qty_str)
                if qty != len(refs):
                    errs.append(f"{spec.pack_id}: BOM 第 {idx} 行 Quantity={qty} != 位号数 {len(refs)}")
            except ValueError:
                errs.append(f"{spec.pack_id}: BOM 第 {idx} 行 Quantity 非整数 '{qty_str}'")
        bom_refs.extend(refs)

    if len(bom_refs) != len(set(bom_refs)):
        errs.append(f"{spec.pack_id}: BOM 存在重复位号")

    cpl_refs: list[str] = []
    top_cnt = 0
    bot_cnt = 0
    for idx, row in enumerate(cpl_rows, start=2):
        ref = (row.get("Designator") or "").strip()
        if not ref:
            errs.append(f"{spec.pack_id}: CPL 第 {idx} 行位号为空")
        cpl_refs.append(ref)
        mx = (row.get("Mid X") or "").strip()
        my = (row.get("Mid Y") or "").strip()
        if not (COORD_RE.match(mx) and COORD_RE.match(my)):
            errs.append(f"{spec.pack_id}: CPL 第 {idx} 行 ({ref}) 坐标格式非法 ({mx}, {my})")
        layer = (row.get("Layer") or "").strip().lower()
        if layer in ("top", "toplayer"):
            top_cnt += 1
        elif layer in ("bottom", "bottomlayer"):
            bot_cnt += 1
        else:
            errs.append(f"{spec.pack_id}: CPL 第 {idx} 行 ({ref}) 贴片层名非法 '{row.get('Layer')}'")

    if len(cpl_refs) != len(set(cpl_refs)):
        errs.append(f"{spec.pack_id}: CPL 存在重复位号")

    bom_set, cpl_set = set(bom_refs), set(cpl_refs)
    if bom_set != cpl_set:
        only_bom = sorted(bom_set - cpl_set)
        only_cpl = sorted(cpl_set - bom_set)
        errs.append(f"{spec.pack_id}: BOM 与 CPL 位号失配 (only_bom={only_bom}, only_cpl={only_cpl})")

    if top_cnt != spec.top_count or bot_cnt != spec.bot_count:
        errs.append(
            f"{spec.pack_id}: 正反面贴片数 (Top={top_cnt}, Bottom={bot_cnt}) != 期望 (Top={spec.top_count}, Bottom={spec.bot_count})"
        )

    return errs


def verify_repo(repo_root: Path, check_hashes: bool = True) -> list[str]:
    errs: list[str] = []
    if len(PACK_SPECS) != 15:
        errs.append(f"制造包规格数量 {len(PACK_SPECS)} != 15")

    for spec in PACK_SPECS:
        gz = repo_root / spec.gerber_zip
        if not gz.is_file():
            errs.append(f"{spec.pack_id}: 缺少 Gerber 压缩包 {spec.gerber_zip}")
            continue
        if check_hashes and not _sha256_hex(gz).startswith(spec.gerber_sha_prefix):
            errs.append(
                f"{spec.pack_id}: Gerber SHA-256 {_sha256_hex(gz)[:16]} != 锁定前缀 {spec.gerber_sha_prefix}"
            )
        errs.extend(_check_gerber_zip(gz, spec))

        if spec.d356_file:
            d356_p = repo_root / spec.d356_file
            if not d356_p.is_file() or d356_p.stat().st_size == 0:
                errs.append(f"{spec.pack_id}: 缺少或空 IPC-D-356 文件 {spec.d356_file}")
            elif check_hashes and spec.d356_sha_prefix and not _sha256_hex(d356_p).startswith(spec.d356_sha_prefix):
                errs.append(
                    f"{spec.pack_id}: D356 SHA-256 {_sha256_hex(d356_p)[:16]} != 锁定前缀 {spec.d356_sha_prefix}"
                )

        if spec.bom_csv and spec.cpl_csv:
            bom_p = repo_root / spec.bom_csv
            cpl_p = repo_root / spec.cpl_csv
            if not bom_p.is_file():
                errs.append(f"{spec.pack_id}: 缺少 BOM 文件 {spec.bom_csv}")
                continue
            if not cpl_p.is_file():
                errs.append(f"{spec.pack_id}: 缺少 CPL 文件 {spec.cpl_csv}")
                continue
            if check_hashes and spec.bom_sha_prefix and not _sha256_hex(bom_p).startswith(spec.bom_sha_prefix):
                errs.append(
                    f"{spec.pack_id}: BOM SHA-256 {_sha256_hex(bom_p)[:16]} != 锁定前缀 {spec.bom_sha_prefix}"
                )
            if check_hashes and spec.cpl_sha_prefix and not _sha256_hex(cpl_p).startswith(spec.cpl_sha_prefix):
                errs.append(
                    f"{spec.pack_id}: CPL SHA-256 {_sha256_hex(cpl_p)[:16]} != 锁定前缀 {spec.cpl_sha_prefix}"
                )
            errs.extend(_check_bom_cpl(bom_p, cpl_p, spec))

    return errs


def run_selftest(repo_root: Path) -> int:
    base_errs = verify_repo(repo_root, check_hashes=True)
    if base_errs:
        print("check_fab_packs selftest 基线失败：", file=sys.stderr)
        for e in base_errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="fab-selftest-") as td_str:
        td = Path(td_str)
        # 仅复制 13 套制造包关联的轻量文件到临时沙箱做突变注入
        needed_rels: set[str] = set()
        for sp in PACK_SPECS:
            needed_rels.add(sp.gerber_zip)
            if sp.bom_csv:
                needed_rels.add(sp.bom_csv)
            if sp.cpl_csv:
                needed_rels.add(sp.cpl_csv)
            if sp.d356_file:
                needed_rels.add(sp.d356_file)
        for rel in needed_rels:
            dst = td / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo_root / rel, dst)

        assert verify_repo(td, check_hashes=True) == [], "沙箱干净副本应通过"

        # 反例 1：篡改 Gerber.zip 末尾注释字节，必须触发 SHA-256 指纹拦截
        p11 = td / PACK_SPECS[-1].gerber_zip
        orig_p11 = p11.read_bytes()
        p11.write_bytes(orig_p11 + b"\x00")
        e1 = verify_repo(td, check_hashes=True)
        assert any("Gerber SHA-256" in x for x in e1), f"反例 1 未拦截：{e1}"
        p11.write_bytes(orig_p11)

        # 反例 2：软板 Gerber.zip 删去 0.20mm 实心 PI 补强层，必须触发 FPC 补强层拦截
        p05 = td / PACK_SPECS[4].gerber_zip
        orig_p05 = p05.read_bytes()
        with zipfile.ZipFile(io.BytesIO(orig_p05), "r") as zin:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
                for name in zin.namelist():
                    if "0p20mm_PI" not in name:
                        zout.writestr(name, zin.read(name))
        p05.write_bytes(buf.getvalue())
        e2 = verify_repo(td, check_hashes=False)
        assert any("PI 补强 Gerber 层" in x for x in e2), f"反例 2 未拦截：{e2}"
        p05.write_bytes(orig_p05)

        # 反例 3：BOM 与 CPL 位号集合不一致，必须触发位号失配拦截
        cpl10 = td / (PACK_SPECS[9].cpl_csv or "")
        orig_cpl10 = cpl10.read_text(encoding="utf-8")
        cpl10.write_text(orig_cpl10 + "R999,0.0mm,0.0mm,Top,0.0\n", encoding="utf-8")
        e3 = verify_repo(td, check_hashes=False)
        assert any("BOM 与 CPL 位号失配" in x for x in e3), f"反例 3 未拦截：{e3}"
        cpl10.write_text(orig_cpl10, encoding="utf-8")

        # 反例 4：BOM 缺失立创 C 号，必须触发料号格式拦截
        bom05 = td / (PACK_SPECS[4].bom_csv or "")
        orig_bom05 = bom05.read_text(encoding="utf-8")
        bom05.write_text(orig_bom05.replace("C25741", ""), encoding="utf-8")
        e4 = verify_repo(td, check_hashes=False)
        assert any("立创料号非法" in x for x in e4), f"反例 4 未拦截：{e4}"
        bom05.write_text(orig_bom05, encoding="utf-8")

        # 反例 5：纯单面板混入 Bottom 层器件，必须触发正反面贴片数拦截
        cpl03 = td / (PACK_SPECS[2].cpl_csv or "")
        orig_cpl03 = cpl03.read_text(encoding="utf-8")
        cpl03.write_text(orig_cpl03.replace(",Top,", ",Bottom,", 1), encoding="utf-8")
        e5 = verify_repo(td, check_hashes=False)
        assert any("正反面贴片数" in x for x in e5), f"反例 5 未拦截：{e5}"
        cpl03.write_text(orig_cpl03, encoding="utf-8")

        assert verify_repo(td, check_hashes=True) == [], "恢复后沙箱应重新全绿"

    print("check_fab_packs selftest: 5/5 必失败反例（指纹/软板补强层/位号失配/缺C号/单面板串层）全部拦截，干净基线通过")
    return 0


def main() -> int:
    args = sys.argv[1:]
    repo_root = Path(__file__).resolve().parent.parent
    if args == ["--selftest"]:
        return run_selftest(repo_root)
    target = Path(args[0]).resolve() if args else repo_root
    errs = verify_repo(target, check_hashes=True)
    if errs:
        print(f"嘉立创制造包门禁失败（共 {len(errs)} 项）：", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"嘉立创制造包门禁通过：{target}（全家族 15 套 Gerber/BOM/CPL/D356 指纹与结构 0 违规）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
