#!/usr/bin/env python3
"""从冻结源板 strap-a.kicad_pcb / strap-b.kicad_pcb 临时挂载 3D 模型导出满载整板 STEP（源板字节零改动）。
用法：使用带 build123d 的 Python 3 环境执行 `python -B export_3d.py`

物理装配映射（按 README §11-12「REF 挪到 A 片」）：
- strap-a（36 实体 = 1 裸板 + 35 器件）：
  - E1N..E8P（16 个圆电极）：Φ6.0×2.0 mm 镀金圆铜片（disc_d6x2）
  - EB1、EB2A（2 个胶囊辅点）：3.0×3.0×2.0 mm 方形镀金铜块（pad_sq_3x3x2），6 颗胶囊贴肤触点同在 A 片 F 面齐平
  - R1..R16（16 颗 0402 限流电阻）、R33（1 颗 0603 偏置电阻）
  - TAIL_A（34P 金手指裸焊盘，不挂器件体）
- strap-b（34 实体 = 1 裸板 + 33 器件）：
  - E9N..E16P（16 个表带圆电极）：Φ6.0×2.0 mm 镀金圆铜片（disc_d6x2）
  - R17..R32（16 颗 0402 限流电阻）、R34（1 颗 0603 参考电阻）
  - EB2 为贴在 A 片 EB2A 背面同心灌锡对焊的层间焊盘（不挂铜块，否则顶穿 A 片基材且撞底盖）
  - TAIL_B（34P 金手指裸焊盘，不挂器件体）
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
PINNED = {
    "a": ("strap-a.kicad_pcb", "strap-a.kicad_pro", "strap-a-3d.step", "3656028295ee5df66a6f9ee198d6b1b87e2abab06f9c93f2d8d537d11f2b83a1", 35, 36),
    "b": ("strap-b.kicad_pcb", "strap-b.kicad_pro", "strap-b-3d.step", "7c229f21ac1b0005cbcd1b2eac82f34a28684d30a4a32c95617ebcfb08a5f640", 33, 34),
}
MISSING_RE = (
    re.compile(r"^Could not add 3D model for (.+?)\.\s*$"),
    re.compile(r"^无法为 (.+?) 添加 3D 模型"),
)
KICAD_3D = Path(
    os.environ.get(
        "KICAD_3D_RES_DIR",
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels/Resistor_SMD.3dshapes",
    )
)


def inject_models(pcb_text: str, mode: str, disc_step: Path, sq_step: Path, r0402_step: Path, r0603_step: Path) -> tuple[str, int]:
    out = []
    i = 0
    n = len(pcb_text)
    injected = 0
    while i < n:
        idx = pcb_text.find("\t(footprint ", i)
        if idx == -1:
            out.append(pcb_text[i:])
            break
        out.append(pcb_text[i:idx])
        depth = 0
        j = idx
        in_str = False
        while j < n:
            ch = pcb_text[j]
            if ch == '"' and pcb_text[j - 1] != "\\":
                in_str = not in_str
            elif not in_str:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
            j += 1
        block = pcb_text[idx:j]
        m_ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        ref = m_ref.group(1) if m_ref else ""
        m_fp = re.match(r'\t\(footprint\s+"([^"]+)"', block)
        fpid = m_fp.group(1) if m_fp else ""

        model_path = None
        if mode == "a" and ref in ("EB1", "EB2A"):
            model_path = sq_step
        elif mode == "b" and ref == "EB2":
            # B 片 EB2 紧贴 A 片 EB2A 背面灌锡导通，铜块焊在 A 片 EB2A 正面，此处无独立器件体
            model_path = None
        elif ref.startswith("E"):
            model_path = disc_step
        elif fpid == "R0402":
            model_path = r0402_step
        elif fpid == "R0603":
            model_path = r0603_step

        if model_path is not None:
            model_sexpr = (
                f'\t\t(model "{model_path}"\n'
                f"\t\t\t(offset (xyz 0 0 0))\n"
                f"\t\t\t(scale (xyz 1 1 1))\n"
                f"\t\t\t(rotate (xyz 0 0 0))\n"
                f"\t\t)\n\t)"
            )
            block = block[:-2] + model_sexpr
            injected += 1
        out.append(block)
        i = j
    return "".join(out), injected


def main() -> int:
    r0402_step = KICAD_3D / "R_0402_1005Metric.step"
    r0603_step = KICAD_3D / "R_0603_1608Metric.step"
    assert r0402_step.is_file() and r0603_step.is_file(), f"缺少 KiCad 电阻 3D 模型：{KICAD_3D}"

    for mode, (pcb_name, pro_name, out_name, pinned_sha, exp_inj, exp_solids) in PINNED.items():
        raw = (HERE / pcb_name).read_bytes()
        got_sha = hashlib.sha256(raw).hexdigest()
        assert got_sha == pinned_sha, f"{pcb_name} 源板哈希变化：{got_sha} != {pinned_sha}"

    with tempfile.TemporaryDirectory(prefix="d2-16ch-3d-") as td_str:
        td = Path(td_str)
        models_dir = td / "models"
        models_dir.mkdir()

        # Φ6.0×2.0 圆铜片与 3.0×3.0×2.0 方形辅点铜块（底面 Z=0，朝 +Z 生长 2.0 mm）
        disc_step = models_dir / "disc_d6x2.step"
        sq_step = models_dir / "pad_sq_3x3x2.step"
        b.export_step(b.Pos(0, 0, 1.0) * b.Cylinder(3.0, 2.0), str(disc_step))
        b.export_step(b.Pos(0, 0, 1.0) * b.Box(3.0, 3.0, 2.0), str(sq_step))

        for mode, (pcb_name, pro_name, out_name, pinned_sha, exp_inj, exp_solids) in PINNED.items():
            text = (HERE / pcb_name).read_text(encoding="utf-8")
            staged_text, count = inject_models(text, mode, disc_step, sq_step, r0402_step, r0603_step)
            assert count == exp_inj, f"{pcb_name} 应挂载 {exp_inj} 颗器件模型，实际 {count}"
            staged_pcb = td / pcb_name
            staged_pcb.write_text(staged_text, encoding="utf-8")
            shutil.copy2(HERE / pro_name, td / pro_name)

            out_step = HERE / out_name
            cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
            env = dict(os.environ, LC_ALL="en_US.UTF-8" if sys.platform == "darwin" else "C.UTF-8")
            env.pop("LANGUAGE", None)
            proc = subprocess.run(
                [cli, "pcb", "export", "step", "-f", "-o", str(out_step), str(staged_pcb)],
                capture_output=True,
                text=True,
                env=env,
            )
            log = (proc.stdout or "") + "\n" + (proc.stderr or "")
            missing = [m.group(1) for ln in log.splitlines() for pat in MISSING_RE if (m := pat.match(ln.strip()))]
            if proc.returncode != 0 or missing:
                print(f"{out_name} 导出异常 rc={proc.returncode}, 缺模型={missing}\n{log[-400:]}", file=sys.stderr)
                return 1 if missing else proc.returncode

            assert hashlib.sha256((HERE / pcb_name).read_bytes()).hexdigest() == pinned_sha
            shp = b.import_step(str(out_step))
            solids = list(shp.solids())
            assert len(solids) == exp_solids, f"{out_name} 实体数量异常：预期 {exp_solids}，实际 {len(solids)}"
            print(f"OK {out_name}: solids={len(solids)}, sha256={hashlib.sha256(out_step.read_bytes()).hexdigest()[:12]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
