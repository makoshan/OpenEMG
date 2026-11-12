#!/usr/bin/env python3
"""从冻结源板 strap-d2-8ch.kicad_pcb 临时挂载 3D 模型导出满载 strap-d2-8ch-3d.step（源板字节零改动）。
用法：使用带 build123d 的 Python 3 环境执行 `python -B export_3d.py`
"""
from __future__ import annotations
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
SRC_PCB = HERE / "strap-d2-8ch.kicad_pcb"
OUT_STEP = HERE / "strap-d2-8ch-3d.step"
PINNED_SHA = "17c3693a3dbe7b1cedf0568637dd54fd8c443e4a9a18febe2f06f845b9f25b03"
MISSING_RE = (re.compile(r"^Could not add 3D model for (.+?)\.\s*$"), re.compile(r"^无法为 (.+?) 添加 3D 模型"))
KICAD_3D = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels/Resistor_SMD.3dshapes")


def main() -> int:
    raw = SRC_PCB.read_bytes()
    got_sha = hashlib.sha256(raw).hexdigest()
    assert got_sha == PINNED_SHA, f"源板哈希变化：{got_sha} != {PINNED_SHA}"

    with tempfile.TemporaryDirectory(prefix="d2-8ch-3d-") as td_str:
        td = Path(td_str)
        models_dir = td / "models"
        models_dir.mkdir()

        # 生成 Φ6.0×2.0 圆铜片与 3.0×3.0×2.0 方铜片（底面在 Z=0，朝 +Z 生长 2.0 mm）
        disc = b.Pos(0, 0, 1.0) * b.Cylinder(3.0, 2.0)
        sq = b.Pos(0, 0, 1.0) * b.Box(3.0, 3.0, 2.0)
        disc_step = models_dir / "disc_d6x2.step"
        sq_step = models_dir / "pad_sq_3x3x2.step"
        b.export_step(disc, str(disc_step))
        b.export_step(sq, str(sq_step))
        r0402_step = KICAD_3D / "R_0402_1005Metric.step"
        r0603_step = KICAD_3D / "R_0603_1608Metric.step"
        assert r0402_step.is_file() and r0603_step.is_file()

        text = raw.decode("utf-8")

        # 逐个 (footprint ...) 块在末尾注入 (model ...)；TAIL_A 为金手指裸焊盘不挂器件体
        def inject_models(pcb_text: str) -> tuple[str, int]:
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
                    if ch == '"' and pcb_text[j - 1] != '\\':
                        in_str = not in_str
                    elif not in_str:
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
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
                if ref in ("EB1", "EB2"):
                    model_path = sq_step
                elif ref.startswith("E"):
                    model_path = disc_step
                elif fpid == "R0402":
                    model_path = r0402_step
                elif fpid == "R0603":
                    model_path = r0603_step
                if model_path is not None:
                    model_sexpr = (
                        f'\t\t(model "{model_path}"\n'
                        f'\t\t\t(offset (xyz 0 0 0))\n'
                        f'\t\t\t(scale (xyz 1 1 1))\n'
                        f'\t\t\t(rotate (xyz 0 0 0))\n'
                        f'\t\t)\n\t)'
                    )
                    block = block[:-2] + model_sexpr
                    injected += 1
                out.append(block)
                i = j
            return "".join(out), injected

        staged_text, count = inject_models(text)
        assert count == 36, f"应挂载 36 颗器件 3D 模型，实际 {count}"
        staged_pcb = td / "strap-d2-8ch.kicad_pcb"
        staged_pcb.write_text(staged_text, encoding="utf-8")
        shutil.copy2(HERE / "strap-d2-8ch.kicad_pro", td / "strap-d2-8ch.kicad_pro")

        cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        proc = subprocess.run([cli, "pcb", "export", "step", "-f", "-o", str(OUT_STEP), str(staged_pcb)], capture_output=True, text=True)
        log = (proc.stdout or "") + "\n" + (proc.stderr or "")
        missing = [m.group(1) for ln in log.splitlines() for pat in MISSING_RE if (m := pat.match(ln.strip()))]
        if proc.returncode != 0 or missing:
            return 1 if missing else proc.returncode

    # 再次校验源板未被改动，并检查导出实体数量（1 裸板 + 36 器件 = 37 个 solid）
    assert hashlib.sha256(SRC_PCB.read_bytes()).hexdigest() == PINNED_SHA
    shp = b.import_step(str(OUT_STEP))
    solids = shp.solids()
    print(f"strap-d2-8ch-3d.step 实体数 = {len(solids)}，尺寸 = {shp.bounding_box().size}")
    assert len(solids) >= 37, f"预期至少 37 个实体（1 板 + 36 件），实际 {len(solids)}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
