#!/usr/bin/env python3
"""D2 16 路双片四层表带软板（strap-a + strap-b）嘉立创 FPC + SMT 制造包生成器（源板字节零改动）。
用法：/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -B make_fab.py
说明：每片板在独立子进程中执行 LoadBoard，杜绝跨板状态污染。
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
import pcbnew as k

HERE = Path(__file__).resolve().parent
BOARD_DIR = HERE.parent
GEOM_JSON = BOARD_DIR / "geometry.json"
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

PIECES = {
    "a": {
        "pcb": "strap-a.kicad_pcb",
        "sha": "3656028295ee5df66a6f9ee198d6b1b87e2abab06f9c93f2d8d537d11f2b83a1",
        "base": "strap-a",
        "title": "D2 表带软板 A片（CH1–CH8 + EB1 + EB2A对焊孔）— B面 PI 补强分厚定位图",
        "x_range": (9.0, 120.0),
        "island_cnt": 12,
    },
    "b": {
        "pcb": "strap-b.kicad_pcb",
        "sha": "7c229f21ac1b0005cbcd1b2eac82f34a28684d30a4a32c95617ebcfb08a5f640",
        "base": "strap-b",
        "title": "D2 表带软板 B片（CH9–CH16 + EB2对焊盘）— B面 PI 补强分厚定位图",
        "x_range": (27.0, 186.0),
        "island_cnt": 16,
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _gcoord(v_mm: float) -> int:
    return int(round(v_mm * 1_000_000))


def _poly_gbr(pts: list[tuple[float, float]]) -> list[str]:
    closed = list(pts)
    if closed[0] != closed[-1]:
        closed.append(closed[0])
    out = ["G36*", f"X{_gcoord(closed[0][0])}Y{_gcoord(-closed[0][1])}D02*"]
    for x, y in closed[1:]:
        out.append(f"X{_gcoord(x)}Y{_gcoord(-y)}D01*")
    out.append("G37*")
    return out


def make_stiffener_gerbers(geo_piece: dict, out_dir: Path, base: str) -> tuple[Path, Path]:
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
    r100k, r200k, cpl_rows, pad_rows, fp_draw = [], [], [], [], []

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


def render_stiffener_map(geo_piece: dict, fp_draw: list[dict], out_png: Path, title: str, x0: float, x1: float, island_cnt: int, y0: float = 34.0, y1: float = 66.0) -> None:
    scale = 18.0
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
        f'<text x="20" y="50" font-size="13" fill="#374151">'
        f'顶视图（不镜像，与 F_Cu 同视角） | 青色：B面 0.10mm PI 补强（34P 金手指背面） | 琥珀色：B面 0.20mm PI 补强（Φ7.2 岛区 ×{island_cnt}） | 绿圈：F面铜片焊盘 | 红块：B面串阻</text>',
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
            lines.append(f'<text x="{tx(rx0)-6:.1f}" y="{ty(ry0)-6:.1f}" font-size="11" font-weight="bold" fill="#0e7490">0.10mm PI</text>')
        elif "circle" in st:
            cx, cy, r = st["circle"]
            lines.append(
                f'<circle cx="{tx(cx):.2f}" cy="{ty(cy):.2f}" r="{r*scale:.2f}" '
                f'fill="{fill}" fill-opacity="0.38" stroke="{stroke}" stroke-width="1.5"/>'
            )

    for item in fp_draw:
        ref, fx, fy, side = item["ref"], item["x"], item["y"], item["side"]
        if ref.startswith("EB"):
            lines.append(f'<circle cx="{tx(fx):.2f}" cy="{ty(fy):.2f}" r="{2.25*scale:.2f}" fill="#16a34a" fill-opacity="0.08" stroke="#16a34a" stroke-width="1.5"/>')
            lines.append(f'<text x="{tx(fx)-12:.1f}" y="{ty(fy)+4:.1f}" font-size="10" font-weight="bold" fill="#15803d">{ref}</text>')
        elif ref.startswith("E"):
            lines.append(f'<circle cx="{tx(fx):.2f}" cy="{ty(fy):.2f}" r="{3.25*scale:.2f}" fill="#16a34a" fill-opacity="0.08" stroke="#16a34a" stroke-width="1.5"/>')
            lines.append(f'<text x="{tx(fx)-12:.1f}" y="{ty(fy)+4:.1f}" font-size="10" fill="#15803d">{ref}</text>')
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


def build_piece(piece_key: str) -> dict:
    cfg = PIECES[piece_key]
    src_pcb = BOARD_DIR / cfg["pcb"]
    raw = src_pcb.read_bytes()
    assert sha256_bytes(raw) == cfg["sha"], f"{cfg['pcb']} SHA-256 与锁定值不符"
    geo = json.loads(GEOM_JSON.read_text(encoding="utf-8"))

    base = cfg["base"]
    gbr_dir = HERE / f"gerber-{piece_key}"
    shutil.rmtree(gbr_dir, ignore_errors=True)
    gbr_dir.mkdir(parents=True)

    bom_path = HERE / f"{base}-jlc-bom.csv"
    cpl_path = HERE / f"{base}-jlc-cpl.csv"
    pads_path = HERE / f"{base}-pads.tsv"
    map_png = HERE / f"stiffener-map-{piece_key}.png"

    counts, fp_draw = extract_board_tables(src_pcb, bom_path, cpl_path, pads_path)

    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    subprocess.run([CLI, "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "-o", str(gbr_dir) + "/", str(src_pcb)], check=True, capture_output=True)
    subprocess.run([CLI, "pcb", "export", "drill", "--format", "excellon", "-u", "mm", "--excellon-separate-th", "-o", str(gbr_dir) + "/", str(src_pcb)], check=True, capture_output=True)
    make_stiffener_gerbers(geo[piece_key], gbr_dir, base)

    d356_path = HERE / f"{base}.d356"
    subprocess.run([CLI, "pcb", "export", "ipcd356", "-o", str(d356_path), str(src_pcb)], check=True, capture_output=True)

    zip_path = HERE / f"{base}-gerber.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(gbr_dir)):
            zf.write(gbr_dir / fn, fn)
    shutil.rmtree(gbr_dir, ignore_errors=True)

    render_stiffener_map(geo[piece_key], fp_draw, map_png, cfg["title"], cfg["x_range"][0], cfg["x_range"][1], cfg["island_cnt"])

    for prl in BOARD_DIR.glob("*.kicad_prl"):
        prl.unlink()
    assert sha256_bytes(src_pcb.read_bytes()) == cfg["sha"], f"{cfg['pcb']} 被意外改动"

    return {
        "board": f"hardware/16ch-c08b-round/strap-fpc-d2/{cfg['pcb']}",
        "source_sha256": cfg["sha"],
        "source_blob": git_blob_sha1(raw),
        "smt_counts": counts,
        "outputs": {
            p.name: {"sha256": sha256_bytes(p.read_bytes()), "bytes": p.stat().st_size}
            for p in (zip_path, d356_path, bom_path, cpl_path, pads_path, map_png)
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--piece", choices=("a", "b"), default=None)
    args = ap.parse_args()

    if args.piece:
        res = build_piece(args.piece)
        (HERE / f".piece-{args.piece}.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        return 0

    pieces_meta = {}
    for pk in ("a", "b"):
        subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--piece", pk], check=True)
        tmp_j = HERE / f".piece-{pk}.json"
        pieces_meta[pk] = json.loads(tmp_j.read_text(encoding="utf-8"))
        tmp_j.unlink()

    manifest = {
        "kicad": subprocess.run([CLI, "version"], capture_output=True, text=True).stdout.strip(),
        "pieces": pieces_meta,
        "production_released": False,
        "platform_verified": False,
    }
    (HERE / "SOURCE.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["outputs"] for k, v in pieces_meta.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
