#!/usr/bin/env python3
"""D2-8CH 8 路单片四层表带软板嘉立创 FPC + SMT 制造包生成器（源板字节零改动）。
用法：/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -B make_fab.py
输出（均位于本目录 fab/）：
  - strap-d2-8ch-gerber.zip（平铺：4 层铜 + 双面阻焊/钢网/丝印 + Edge_Cuts + PTH/NPTH 钻孔 + 0.10mm/0.20mm 分层实心补强 Gerber）
  - strap-d2-8ch.d356（IPC-D-356 飞针电测网表）
  - jlc_smt_bom.csv（嘉立创基础库 C25741 100k 0402 × 16 + C25811 200k 0603 × 2，零换料费）
  - jlc_smt_cpl.csv（18 颗串阻双面贴片坐标，0° 水平焊盘对齐）
  - pads.tsv（只含焊盘坐标与层，供 gnet_fpc.py 独立反推网表核对）
  - stiffener-map.png（B 面 0.10 mm 金手指补强与 0.20 mm 岛区/胶囊 6 窗垫片补强分色顶视工程图）
  - SOURCE.json（源板 SHA-256 与各产物指纹绑定）
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
import pcbnew as k

HERE = Path(__file__).resolve().parent
BOARD_DIR = HERE.parent
SRC_PCB = BOARD_DIR / "strap-d2-8ch.kicad_pcb"
GEOM_JSON = BOARD_DIR / "geometry.json"
PINNED_SHA = "17c3693a3dbe7b1cedf0568637dd54fd8c443e4a9a18febe2f06f845b9f25b03"
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _gcoord(v_mm: float) -> int:
    return int(round(v_mm * 1_000_000))


def _poly_gbr(pts: list[tuple[float, float]]) -> list[str]:
    """按 KiCad Gerber 顶视坐标（X = x_mm, Y = -y_mm）输出 G36..G37 实心区域。"""
    closed = list(pts)
    if closed[0] != closed[-1]:
        closed.append(closed[0])
    out = ["G36*", f"X{_gcoord(closed[0][0])}Y{_gcoord(-closed[0][1])}D02*"]
    for x, y in closed[1:]:
        out.append(f"X{_gcoord(x)}Y{_gcoord(-y)}D01*")
    out.append("G37*")
    return out


def make_stiffener_gerbers(geo_piece: dict, out_dir: Path, base: str) -> tuple[Path, Path]:
    """直接按 RS-274X X2 标准（%FSLAX46Y46*% 1nm 精度，与 kicad-cli 完全同坐标系）输出 0.10mm 与 0.20mm 分层实心补强 Gerber。
    注意 geometry.json 中 rect 与 holes 的四元组格式均为 [x0, x1, y0, y1]。
    """
    for thick, tag, idx in ((0.10, "0p10mm", 1), (0.20, "0p20mm", 2)):
        items = [s for s in geo_piece["stiffeners"] if abs(float(s["thickness_mm"]) - thick) < 1e-3]
        radii = sorted({round(float(s["circle"][2]), 6) for s in items if "circle" in s})
        ap_map = {r: 10 + i for i, r in enumerate(radii)}

        gbr = [
            f"%TF.FileFunction,Other,User,{idx}*",
            "%TF.FilePolarity,Positive*",
            "%FSLAX46Y46*%",
            "%MOMM*%",
            f"G04 {base} Bottom PI Stiffener {thick:.2f}mm (Top-view un-mirrored, matches F_Cu)*",
            "G01*",
        ]
        for r, code in ap_map.items():
            gbr.append(f"%ADD{code}C,{r * 2.0:.6f}*%")

        gbr.append("%LPD*%")
        for st in items:
            if "rect" in st:
                x0, x1, y0, y1 = st["rect"]
                assert x1 > x0 and y1 > y0, f"异常 rect 顺序：{st['rect']}"
                gbr.extend(_poly_gbr([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
            elif "circle" in st:
                cx, cy, r = st["circle"]
                code = ap_map[round(float(r), 6)]
                gbr.append(f"D{code}*")
                gbr.append(f"X{_gcoord(cx)}Y{_gcoord(-cy)}D03*")
            elif "poly" in st:
                gbr.extend(_poly_gbr([(p[0], p[1]) for p in st["poly"]]))
                if st.get("holes"):
                    gbr.append("%LPC*%")
                    for hx0, hx1, hy0, hy1 in st["holes"]:
                        assert hx1 > hx0 and hy1 > hy0, f"异常 hole 顺序：{[hx0, hx1, hy0, hy1]}"
                        gbr.extend(_poly_gbr([(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)]))
                    gbr.append("%LPD*%")
            else:
                raise ValueError(f"未知补强图元：{st}")
        gbr.append("M02*")
        (out_dir / f"{base}-BOT_STIFF_{tag}_PI.gbr").write_text("\n".join(gbr) + "\n", encoding="ascii")

    return out_dir / f"{base}-BOT_STIFF_0p10mm_PI.gbr", out_dir / f"{base}-BOT_STIFF_0p20mm_PI.gbr"


def extract_board_tables(board_path: Path, bom_path: Path, cpl_path: Path, pads_path: Path) -> tuple[dict, list[dict]]:
    tb = k.LoadBoard(str(board_path))
    r100k, r200k, cpl_rows = [], [], []
    pad_rows = []
    fp_draw = []

    def ref_sort_key(fp):
        ref = fp.GetReference()
        tail = ref[1:]
        return (0 if tail.isdigit() else 1, int(tail) if tail.isdigit() else 999, ref)

    for fp in sorted(tb.GetFootprints(), key=ref_sort_key):
        ref = fp.GetReference()
        pos = fp.GetPosition()
        fx, fy = round(k.ToMM(pos.x), 4), round(k.ToMM(pos.y), 4)
        side = "Bottom" if tb.GetLayerName(fp.GetLayer()) == "B.Cu" else "Top"
        fp_draw.append({"ref": ref, "x": fx, "y": fy, "side": side})

        for pd in fp.Pads():
            num = pd.GetNumber()
            px = round(k.ToMM(pd.GetPosition().x), 4)
            py = round(k.ToMM(pd.GetPosition().y), 4)
            cu_layers = [tb.GetLayerName(l) for l in pd.GetLayerSet().CuStack() if tb.GetLayerName(l) in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")]
            drill_mm = round(k.ToMM(pd.GetDrillSize().x), 4)
            pad_rows.append((ref, num, f"{px:.4f}", f"{py:.4f}", ",".join(cu_layers), f"{drill_mm:.4f}"))

        if not ref.startswith("R"):
            continue
        val = fp.GetValue().strip().lower()
        fpid = fp.GetFPIDAsString()
        pads = list(fp.Pads())
        dx = abs(k.ToMM(pads[0].GetPosition().x - pads[1].GetPosition().x))
        dy = abs(k.ToMM(pads[0].GetPosition().y - pads[1].GetPosition().y))
        rot = 0.0 if dx >= dy else 90.0
        cpl_rows.append((ref, f"{fx:.4f}mm", f"{-fy:.4f}mm", side, f"{rot:.1f}"))
        if val == "100k" and fpid == "R0402":
            r100k.append(ref)
        elif val == "200k" and fpid == "R0603":
            r200k.append(ref)
        else:
            raise ValueError(f"未预期阻容：{ref} {val} {fpid}")

    with bom_path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
        if r100k:
            w.writerow(["0402WGF1003TCE (100kΩ ±1%)", ",".join(r100k), "0402", "C25741", len(r100k)])
        if r200k:
            w.writerow(["0603WAF2003T5E (200kΩ ±1%)", ",".join(r200k), "0603", "C25811", len(r200k)])

    with cpl_path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in cpl_rows:
            w.writerow(row)

    with pads_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in pad_rows:
            f.write("\t".join(row) + "\n")

    return {"r100k_0402": len(r100k), "r200k_0603": len(r200k), "total_smt": len(cpl_rows)}, fp_draw


def render_stiffener_map(geo_piece: dict, fp_draw: list[dict], out_png: Path, title: str, x0: float = 9.0, x1: float = 120.0, y0: float = 34.0, y1: float = 66.0) -> None:
    """绘制 B 面分厚度 PI 补强顶视工程图（青色 0.10mm 金手指补强、琥珀色 0.20mm 岛区与胶囊 6 窗垫片补强、黑色板框、绿色贴肤铜片焊盘）。"""
    scale = 20.0
    W = int(round((x1 - x0) * scale))
    H = int(round((y1 - y0) * scale)) + 90

    def tx(x):
        return (x - x0) * scale

    def ty(y):
        return 65.0 + (y - y0) * scale

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>',
        f'<text x="20" y="28" font-size="18" font-weight="bold" fill="#111827">{title}</text>',
        '<text x="20" y="50" font-size="13" fill="#374151">'
        '顶视图（不镜像，与 F_Cu 同视角） | 青色：B面 0.10mm PI 补强（34P 金手指背面） | 琥珀色：B面 0.20mm PI 补强（Φ7.2 岛区 ×12 + 胶囊 6 窗垫片 ×1） | 绿圈：F面铜片焊盘 | 红块：B面串阻</text>',
    ]

    out_d = "M " + " L ".join(f"{tx(px):.2f},{ty(py):.2f}" for px, py in geo_piece["outline"]) + " Z"
    lines.append(f'<path d="{out_d}" fill="#f1f5f9" stroke="#334155" stroke-width="2.0"/>')

    for st in geo_piece["stiffeners"]:
        t = round(float(st["thickness_mm"]), 3)
        is_010 = abs(t - 0.10) < 1e-3
        fill = "#06b6d4" if is_010 else "#f59e0b"
        stroke = "#0e7490" if is_010 else "#b45309"
        if "rect" in st:
            rx0, rx1, ry0, ry1 = st["rect"]
            lines.append(
                f'<rect x="{tx(rx0):.2f}" y="{ty(ry0):.2f}" width="{(rx1-rx0)*scale:.2f}" height="{(ry1-ry0)*scale:.2f}" '
                f'fill="{fill}" fill-opacity="0.45" stroke="{stroke}" stroke-width="1.8"/>'
            )
            lines.append(
                f'<text x="{tx(rx0)-6:.1f}" y="{ty(ry0)-6:.1f}" font-size="11" font-weight="bold" fill="#0e7490">0.10mm PI (2.5×17.5)</text>'
            )
        elif "circle" in st:
            cx, cy, r = st["circle"]
            lines.append(
                f'<circle cx="{tx(cx):.2f}" cy="{ty(cy):.2f}" r="{r*scale:.2f}" '
                f'fill="{fill}" fill-opacity="0.38" stroke="{stroke}" stroke-width="1.5"/>'
            )
        elif "poly" in st:
            hole_paths = ""
            for hx0, hx1, hy0, hy1 in st.get("holes", []):
                hole_paths += f" M {tx(hx0):.2f},{ty(hy0):.2f} L {tx(hx0):.2f},{ty(hy1):.2f} L {tx(hx1):.2f},{ty(hy1):.2f} L {tx(hx1):.2f},{ty(hy0):.2f} Z"
            poly_d = "M " + " L ".join(f"{tx(px):.2f},{ty(py):.2f}" for px, py in st["poly"]) + " Z" + hole_paths
            lines.append(
                f'<path d="{poly_d}" fill-rule="evenodd" fill="{fill}" fill-opacity="0.38" stroke="{stroke}" stroke-width="1.8"/>'
            )

    for item in fp_draw:
        ref, fx, fy, side = item["ref"], item["x"], item["y"], item["side"]
        if ref.startswith("TAIL"):
            lines.append(f'<text x="{tx(fx)-34:.1f}" y="{ty(fy)+4:.1f}" font-size="10" font-weight="bold" fill="#1e3a8a">{ref}</text>')
        elif ref.startswith("EB"):
            lines.append(f'<circle cx="{tx(fx):.2f}" cy="{ty(fy):.2f}" r="{2.25*scale:.2f}" fill="#16a34a" fill-opacity="0.08" stroke="#16a34a" stroke-width="1.5"/>')
            lines.append(f'<text x="{tx(fx)-11:.1f}" y="{ty(fy)+4:.1f}" font-size="10" font-weight="bold" fill="#15803d">{ref}</text>')
        elif ref.startswith("E"):
            lines.append(f'<circle cx="{tx(fx):.2f}" cy="{ty(fy):.2f}" r="{3.25*scale:.2f}" fill="#16a34a" fill-opacity="0.08" stroke="#16a34a" stroke-width="1.5"/>')
            lines.append(f'<text x="{tx(fx)-11:.1f}" y="{ty(fy)+4:.1f}" font-size="10" fill="#15803d">{ref}</text>')
        elif ref.startswith("R") and side == "Bottom":
            w_mm, h_mm = (1.6, 0.8) if ref in ("R33", "R34") else (1.0, 0.5)
            lines.append(
                f'<rect x="{tx(fx - w_mm/2):.2f}" y="{ty(fy - h_mm/2):.2f}" width="{w_mm*scale:.2f}" height="{h_mm*scale:.2f}" '
                f'fill="#ef4444" fill-opacity="0.78" stroke="#991b1b" stroke-width="1.0"/>'
            )
            lines.append(f'<text x="{tx(fx)+12:.1f}" y="{ty(fy)+4:.1f}" font-size="10" font-weight="bold" fill="#991b1b">{ref}</text>')

    lines.append("</svg>")
    with tempfile.TemporaryDirectory(prefix="stiff-svg-") as td_str:
        svg_p = Path(td_str) / "map.svg"
        svg_p.write_text("\n".join(lines), encoding="utf-8")
        subprocess.run(["magick", "-font", FONT_PATH, "-density", "144", str(svg_p), str(out_png)], check=True, capture_output=True)


def main() -> int:
    raw = SRC_PCB.read_bytes()
    assert sha256_bytes(raw) == PINNED_SHA, "源板 SHA-256 与锁定值不符"
    geo = json.loads(GEOM_JSON.read_text(encoding="utf-8"))

    gbr_dir = HERE / "gerber"
    shutil.rmtree(gbr_dir, ignore_errors=True)
    gbr_dir.mkdir(parents=True)

    bom_path = HERE / "jlc_smt_bom.csv"
    cpl_path = HERE / "jlc_smt_cpl.csv"
    pads_path = HERE / "pads.tsv"
    map_png = HERE / "stiffener-map.png"

    counts, fp_draw = extract_board_tables(SRC_PCB, bom_path, cpl_path, pads_path)

    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    subprocess.run([CLI, "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "-o", str(gbr_dir) + "/", str(SRC_PCB)], check=True, capture_output=True)
    subprocess.run([CLI, "pcb", "export", "drill", "--format", "excellon", "-u", "mm", "--excellon-separate-th", "-o", str(gbr_dir) + "/", str(SRC_PCB)], check=True, capture_output=True)
    make_stiffener_gerbers(geo["a"], gbr_dir, "strap-d2-8ch")

    d356_path = HERE / "strap-d2-8ch.d356"
    subprocess.run([CLI, "pcb", "export", "ipcd356", "-o", str(d356_path), str(SRC_PCB)], check=True, capture_output=True)

    zip_path = HERE / "strap-d2-8ch-gerber.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(gbr_dir)):
            zf.write(gbr_dir / fn, fn)
    shutil.rmtree(gbr_dir, ignore_errors=True)

    render_stiffener_map(geo["a"], fp_draw, map_png, "D2-8CH 单片四层表带软板 — B面 PI 补强分厚定位图（0.10mm / 0.20mm）")

    for prl in BOARD_DIR.glob("*.kicad_prl"):
        prl.unlink()
    assert sha256_bytes(SRC_PCB.read_bytes()) == PINNED_SHA, "源板被意外改动"

    manifest = {
        "board": "hardware/8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch.kicad_pcb",
        "source_sha256": PINNED_SHA,
        "source_blob": git_blob_sha1(raw),
        "kicad": subprocess.run([CLI, "version"], capture_output=True, text=True).stdout.strip(),
        "smt_counts": counts,
        "outputs": {
            p.name: {"sha256": sha256_bytes(p.read_bytes()), "bytes": p.stat().st_size}
            for p in (zip_path, d356_path, bom_path, cpl_path, pads_path, map_png)
        },
        "production_released": False,
        "platform_verified": False,
    }
    (HERE / "SOURCE.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["outputs"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
