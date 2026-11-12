#!/usr/bin/env python3
"""从上传给嘉立创的四层表带软板 Gerber.zip（4 层铜 + PTH 钻孔 + 分厚补强层）像素级重建连通关系，
与 pin-map.json 独立推导的期望网表逐焊盘核对（不读 .kicad_pcb 网名）。
用法：
  python3 -B gnet_fpc.py <8ch|a|b> <gerber.zip> <pads.tsv> <pin-map.json> <work_dir> [--out gnet.json] [open|short|nohole]
退出码：0 一致 / 1 不一致。
"""
from __future__ import annotations
import argparse
import collections
import io
import json
import pathlib
import re
import shutil
import sys
import zipfile
import numpy as np
from scipy import ndimage
from PIL import Image
from gerbonara import GerberFile
import resvg_py

Image.MAX_IMAGE_PIXELS = None

LAYERS = {"F.Cu": "F_Cu.gtl", "In1.Cu": "In1_Cu.g1", "In2.Cu": "In2_Cu.g2", "B.Cu": "B_Cu.gbl"}
BOUNDS = {
    "8ch": (10.0, 120.0, -66.0, -34.0),
    "a": (10.0, 120.0, -66.0, -34.0),
    "b": (28.0, 186.0, -66.0, -34.0),
}
SINGLE_VIA_KILL = {
    "8ch": (47.5, 50.0),   # BIAS_DRV1_EB2_E 唯一换层孔
    "a": (61.6, 58.6),     # BIAS_DRV1_E 唯一换层孔
    "b": (47.5, 50.0),     # BIAS_DRV12_E 唯一换层孔
}


def build_expected_netlist(mode: str, pin_map_path: pathlib.Path) -> dict[tuple[str, str], str]:
    pm = json.loads(pin_map_path.read_text(encoding="utf-8"))
    want: dict[tuple[str, str], str] = {}
    if mode == "8ch":
        for row in pm["table"]:
            want[("TAIL_A", str(row["pin"]))] = row["expect"]
        for ch in range(1, 9):
            want[(f"R{2*ch-1}", "1")] = f"CH{ch}_P"
            want[(f"R{2*ch-1}", "2")] = f"CH{ch}_P_E"
            want[(f"E{ch}P", "1")] = f"CH{ch}_P_E"
            want[(f"R{2*ch}", "1")] = f"CH{ch}_N"
            want[(f"R{2*ch}", "2")] = f"CH{ch}_N_E"
            want[(f"E{ch}N", "1")] = f"CH{ch}_N_E"
        want[("R33", "1")] = "BIAS_DRV1"
        want[("R33", "2")] = "BIAS_DRV1_E"
        want[("EB1", "1")] = "BIAS_DRV1_E"
        want[("R34", "1")] = "BIAS_DRV1"
        want[("R34", "2")] = "BIAS_DRV1_EB2_E"
        want[("EB2", "1")] = "BIAS_DRV1_EB2_E"
    elif mode == "a":
        for row in pm["a"]["table"]:
            want[("TAIL_A", str(row["pin"]))] = row["expect"]
        for ch in range(1, 9):
            want[(f"R{2*ch-1}", "1")] = f"CH{ch}_P"
            want[(f"R{2*ch-1}", "2")] = f"CH{ch}_P_E"
            want[(f"E{ch}P", "1")] = f"CH{ch}_P_E"
            want[(f"R{2*ch}", "1")] = f"CH{ch}_N"
            want[(f"R{2*ch}", "2")] = f"CH{ch}_N_E"
            want[(f"E{ch}N", "1")] = f"CH{ch}_N_E"
        want[("R33", "1")] = "BIAS_DRV1"
        want[("R33", "2")] = "BIAS_DRV1_E"
        want[("EB1", "1")] = "BIAS_DRV1_E"
        want[("EB2A", "1")] = "BIAS_DRV12_E"
    elif mode == "b":
        for row in pm["b"]["table"]:
            want[("TAIL_B", str(row["pin"]))] = row["expect"]
        for ch in range(9, 17):
            want[(f"R{2*ch-1}", "1")] = f"CH{ch}_P"
            want[(f"R{2*ch-1}", "2")] = f"CH{ch}_P_E"
            want[(f"E{ch}P", "1")] = f"CH{ch}_P_E"
            want[(f"R{2*ch}", "1")] = f"CH{ch}_N"
            want[(f"R{2*ch}", "2")] = f"CH{ch}_N_E"
            want[(f"E{ch}N", "1")] = f"CH{ch}_N_E"
        want[("R34", "1")] = "BIAS_DRV12"
        want[("R34", "2")] = "BIAS_DRV12_E"
        want[("EB2", "1")] = "BIAS_DRV12_E"
    else:
        raise ValueError(f"未知模式：{mode}")
    return want


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("8ch", "a", "b"))
    ap.add_argument("gerber_zip", type=pathlib.Path)
    ap.add_argument("pads_tsv", type=pathlib.Path)
    ap.add_argument("pin_map", type=pathlib.Path)
    ap.add_argument("work_dir", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("neg", nargs="?", default="")
    args = ap.parse_args()

    X0, X1, Y0, Y1 = BOUNDS[args.mode]
    PPM = 60  # 60 px/mm -> 0.15mm 线宽 = 9 px，最小铜距 0.15mm = 9 px
    W, H = int(round((X1 - X0) * PPM)), int(round((Y1 - Y0) * PPM))

    def px(x: float, yk: float) -> tuple[int, int]:
        return int(round((x - X0) * PPM)), int(round((yk + Y1) * PPM))

    src = args.work_dir / f"src_{args.mode}_{args.neg or 'nom'}"
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.gerber_zip) as zf:
        zf.extractall(src)

    # 校验分层补强 Gerber 均在压缩包内且可被 gerbonara 解析
    stiff_bounds = {}
    for tag in ("0p10mm", "0p20mm"):
        matches = list(src.glob(f"*-BOT_STIFF_{tag}_PI.gbr"))
        if len(matches) != 1:
            print(json.dumps({"error": f"缺少补强层 {tag}"}, ensure_ascii=False))
            return 1
        gf_st = GerberFile.open(matches[0])
        bb = gf_st.bounding_box()
        stiff_bounds[tag] = [[round(bb[0][0], 3), round(bb[0][1], 3)], [round(bb[1][0], 3), round(bb[1][1], 3)]]

    img = {}
    for L, suf in LAYERS.items():
        svg = str(GerberFile.open(next(src.glob("*" + suf))).to_svg(force_bounds=((X0, Y0), (X1, Y1)), fg="white", bg="black"))
        svg = re.sub(r'width="[\d.]+mm" height="[\d.]+mm"', f'width="{W}" height="{H}"', svg, count=1)
        arr = np.array(Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg, background="black")))).convert("L")) > 127
        assert arr.shape == (H, W), (L, arr.shape, (H, W))
        img[L] = arr

    pads = [l.rstrip("\n").split("\t") for l in args.pads_tsv.read_text(encoding="utf-8").splitlines() if l.strip()]
    want = build_expected_netlist(args.mode, args.pin_map)
    assert len(pads) == len(want), f"焊盘数不匹配：pads={len(pads)} want={len(want)}"

    holes = [
        (float(m.group(1)), -float(m.group(2)))
        for m in (re.match(r"X(-?[\d.]+)Y(-?[\d.]+)", l) for l in next(src.glob("*-PTH.drl")).read_text(encoding="ascii").splitlines())
        if m
    ]

    def pad_xy(ref: str, num: str) -> tuple[float, float]:
        return next((float(p[2]), float(p[3])) for p in pads if p[0] == ref and p[1] == num)

    if args.neg == "open":
        target_r = "R17" if args.mode == "b" else "R9"
        c, r = px(*pad_xy(target_r, "1"))
        img["F.Cu"][r - 45 : r + 45, c - 45 : c + 45] = False
    elif args.neg == "short":
        tail_ref = "TAIL_B" if args.mode == "b" else "TAIL_A"
        (c1, r1), (c2, r2) = px(*pad_xy(tail_ref, "5")), px(*pad_xy(tail_ref, "6"))
        img["F.Cu"][min(r1, r2) - 3 : max(r1, r2) + 4, min(c1, c2) - 3 : max(c1, c2) + 4] = True
    elif args.neg == "nohole":
        kx, ky = SINGLE_VIA_KILL[args.mode]
        n0 = len(holes)
        holes = [h for h in holes if not (abs(h[0] - kx) < 0.02 and abs(h[1] - ky) < 0.02)]
        assert len(holes) == n0 - 1, f"未找到待删过孔 {(kx, ky)}"
    elif args.neg:
        raise ValueError(f"未知反例：{args.neg}")

    lab = {L: ndimage.label(a, structure=np.ones((3, 3)))[0] for L, a in img.items()}
    par: dict[tuple[str, int], tuple[str, int]] = {}

    def find(a: tuple[str, int]) -> tuple[str, int]:
        while par.setdefault(a, a) != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    full = 0
    for x, y in holes:
        c, r = px(x, y)
        ids = [(L, int(lab[L][r, c])) for L in LAYERS if lab[L][r, c]]
        full += len(ids) == 4
        for i in ids[1:]:
            par[find(i)] = find(ids[0])

    net2root, root2net, nocu, checked = collections.defaultdict(set), collections.defaultdict(set), [], 0
    for ref, num, xs, ys, ls, drills in pads:
        w = want.get((ref, num))
        if w is None or not ls:
            nocu.append(f"{ref}.{num}:unmapped")
            continue
        L = ls.split(",")[0]
        x, y, d_mm = float(xs), float(ys), float(drills)
        sample_x = x + d_mm * 0.8 if d_mm > 0 else x
        c, r = px(sample_x, y)
        i = int(lab[L][r, c])
        checked += 1
        if not i:
            nocu.append(f"{ref}.{num}")
            continue
        rt = find((L, i))
        net2root[w].add(rt)
        root2net[rt].add(w)

    opens = {k: len(v) for k, v in net2root.items() if len(v) > 1}
    shorts = [sorted(v) for v in root2net.values() if len(v) > 1]
    res = {
        "mode": args.mode,
        "neg": args.neg or "nominal",
        "pth_holes": len(holes),
        "four_layer_holes": full,
        "checked_pads": checked,
        "nets": len(net2root),
        "stiffener_gerber_bounds": stiff_bounds,
        "nocu": nocu,
        "opens": opens,
        "shorts": shorts,
        "ok": not (nocu or opens or shorts),
    }
    shutil.rmtree(src, ignore_errors=True)
    if args.out and not args.neg:
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
