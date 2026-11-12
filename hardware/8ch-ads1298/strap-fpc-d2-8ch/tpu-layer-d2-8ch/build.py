"""C08B 8通道单片版表带电极层 D2-8CH（适配 strap-d2-8ch 单片四层软板 + D20-8CH / D20N-8CH 单面采集板）。
叠层（从表带往皮肤）：现成 25 mm 表带 → 0.20 mm PI 圆形补强（Ø7.2，共 12 处）→ 单片四层 FPC（0.203 mm，F 面焊盘朝皮肤）
→ 3M 9448A 双面胶（0.10 mm，开 12 铜片孔 + 12 串阻窗）→ TPU 电极层（本件 0.80 mm，开孔 + 背面浅槽）→ 镀金铜片（Φ6×2.0，穿过 TPU 孔贴皮肤）。

与 16 通道版（hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2）的唯一结构差异：
- 北片同为 2 路（CH3 / CH4，Y = 34, 42），外形 26.2 × 16.2 × 0.80 mm，4 孔 + 4 背面串阻槽（R5–R8）；
- 南片按 8 通道单片软板裁为 4 路（CH5–CH8，Y = −32, −40, −48, −56），外形 26.2 × 32.2 × 0.80 mm（较 16ch 的 96.2 mm 缩短 64.0 mm，
  消除南侧悬空盲孔积汗带），8 孔 + 8 背面串阻槽（R9–R16）；
- CH1 / CH2 与 EB1 / EB2 仍在胶囊底（复用现成 hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2 的 cap_d2 与 tray_d2）。

坐标系（右手系）：Y 沿表带（北 +），X 沿前臂横跨带宽（中心 0），Z 从 TPU 贴 FPC 面（0）朝皮肤（+）。
FPC 板坐标 (bx, by, bz_入板) → 表带 TPU 坐标：X = 50 − by，Y = 58 − bx，Z = −bz（行列式 = +1，严禁套用盒底 X = by − 50 镜像式）。
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import build123d as b

HERE = Path(__file__).resolve().parent
FPC_DIR = HERE.parent
FPC_PCB = FPC_DIR / "strap-d2-8ch.kicad_pcb"
FPC_GEOM = FPC_DIR / "geometry.json"
PINNED_FPC_SHA256 = "17c3693a3dbe7b1cedf0568637dd54fd8c443e4a9a18febe2f06f845b9f25b03"

# ---- 布局（Y = 每路中心，沿表带） ----
PITCH = 8.0
NORTH_YS = (34.0, 42.0)                                  # CH3、CH4（与 16ch D2 同位）
SOUTH_YS = tuple(-32.0 - PITCH * k for k in range(4))    # CH5–CH8：−32, −40, −48, −56（共 4 路）
NORTH_PIN_Y, SOUTH_PIN_Y = 21.65, -21.20                 # R12/R13 生耳轴
LOOP_R = 1.90                                            # 带端包弹簧棒圆筒半径（Ø3.80）
LUG_GAP = 3.00                                           # 层离带端圆筒最小净距
RING_FROM_NORTH_PIN = 55.0                               # **假设**：日字扣环中心离北生耳约 55–60（取保守值 55，未实量）
RING_HALF = 1.5
STRAP_W = 25.0                                           # 表带宽（Mako 11-10 实测）
LAYER_W = 26.2                                           # TPU 层宽：比表带每边宽 0.6，给 Φ6.5 孔留 0.85 边壁
PN = 18.0                                                # 同一路 P/N 中心距
END_L = 1.1                                              # 端头余量（从 Φ6 铜片外沿算；孔 Φ6.5 时端壁 0.85）

# ---- 镀金铜片（Φ6×2.0） ----
DISC_D = 6.0
DISC_T = 2.0
HOLE_CLEAR = 0.50                                        # 孔径 = 6.5 mm（先焊铜片再套 TPU，单边留 0.25 mm 余量）

# ---- TPU 层与叠层厚度 ----
LAYER_T = 0.80                                           # 层厚 → 紧贴 FPC 时铜片凸出 1.20 mm（垫 0.10 mm 9448A 时凸出 1.10 mm）
MIN_WALL = 0.80
FPC_T = 0.203                                            # 嘉立创四层 FPC 压合成品厚（单片版）
PI_T = 0.20                                              # 焊盘背面 Ø7.2 圆形 PI 补强厚
TAPE_9448A_T = 0.10                                      # 3M 9448A 双面胶标称厚
RES_H = 0.35                                             # 0402 串阻高（KiCad R_0402_1005Metric 标称 0.35 mm）
POCKET_D = 0.45                                          # 背面浅槽深 = 0.45 mm；槽顶剩 0.35 mm（0.16 层高约两层）
KEY = 1.5                                                # 北端 +X 角 1.5 mm × 45° 防翻面切角


def hole_d() -> float:
    return DISC_D + HOLE_CLEAR


def span(ys: tuple[float, ...]) -> tuple[float, float]:
    return min(ys) - DISC_D / 2 - END_L, max(ys) + DISC_D / 2 + END_L


def pockets(ys: tuple[float, ...]) -> list[tuple[float, float, float, float]]:
    """读取 8ch 单片软板 geometry.json 的 f_res_pockets.pocket_board，按右手系换算为表带坐标 [X0, X1, Y0, Y1]。"""
    lo, hi = span(ys)
    rects = json.loads(FPC_GEOM.read_text(encoding="utf-8"))["f_res_pockets"]["rects"]
    out: list[tuple[float, float, float, float]] = []
    for r in rects:
        bx0, by0, bx1, by1 = r["pocket_board"]
        assert bx1 > bx0 and by1 > by0, f"pocket_board 坐标顺序异常：{r}"
        x0, x1 = round(50.0 - by1, 6), round(50.0 - by0, 6)
        y0, y1 = round(58.0 - bx1, 6), round(58.0 - bx0, 6)
        assert x1 > x0 and y1 > y0
        if lo < (y0 + y1) / 2 < hi:
            out.append((x0, x1, y0, y1))
    return out


def build_piece(ys: tuple[float, ...], label: str = "layer_d2_8ch"):
    lo, hi = span(ys)
    s = b.Pos(0, (lo + hi) / 2, LAYER_T / 2) * b.Box(LAYER_W, hi - lo, LAYER_T)
    for y in ys:
        for x in (-PN / 2, PN / 2):
            s -= b.Pos(x, y, LAYER_T / 2) * b.Cylinder(hole_d() / 2, LAYER_T + 0.2)
    for x0, x1, y0, y1 in pockets(ys):                  # 背面（Z=0，贴 FPC 侧）浅槽
        s -= b.Pos((x0 + x1) / 2, (y0 + y1) / 2, POCKET_D / 2 - 0.05) * b.Box(x1 - x0, y1 - y0, POCKET_D + 0.1)
    if KEY > 0:                                          # 北端 +X 角 45° 切角防翻面（翻面会让浅槽朝外压坏串阻）
        s -= b.Pos(LAYER_W / 2, hi, LAYER_T / 2) * b.Rot(0, 0, 45) * b.Box(KEY * 1.41421356, KEY * 1.41421356, LAYER_T + 0.2)
    cleaned = s.clean()
    cleaned.label = label
    return cleaned


def gaps() -> dict:
    n_lo, n_hi = span(NORTH_YS)
    s_lo, s_hi = span(SOUTH_YS)
    return {
        "north_to_loop": round(n_lo - (NORTH_PIN_Y + LOOP_R), 3),
        "north_to_ring": round((NORTH_PIN_Y + RING_FROM_NORTH_PIN - RING_HALF) - n_hi, 3),
        "south_to_loop": round((SOUTH_PIN_Y - LOOP_R) - s_hi, 3),
        "south_saved_vs_16ch_mm": round(96.2 - (s_hi - s_lo), 3),
        "north_y": [round(n_lo, 3), round(n_hi, 3)],
        "south_y": [round(s_lo, 3), round(s_hi, 3)],
    }


def summary() -> dict:
    hd = hole_d()
    pcb_sha = hashlib.sha256(FPC_PCB.read_bytes()).hexdigest()
    assert pcb_sha == PINNED_FPC_SHA256, f"源板哈希变化：{pcb_sha} != {PINNED_FPC_SHA256}"
    return {
        "variant": "D2-8CH",
        "source_fpc_pcb": "hardware/8ch-ads1298/strap-fpc-d2-8ch/strap-d2-8ch.kicad_pcb",
        "source_fpc_pcb_sha256": pcb_sha,
        "pitch": PITCH,
        "strap_channels": len(NORTH_YS) + len(SOUTH_YS),
        "total_system_channels": 2 + len(NORTH_YS) + len(SOUTH_YS),
        "hole_d": hd,
        "disc_proud_flush_mm": round(DISC_T - LAYER_T, 3),
        "disc_proud_with_9448a_mm": round(DISC_T - TAPE_9448A_T - LAYER_T, 3),
        "wall_to_edge": round(LAYER_W / 2 - PN / 2 - hd / 2, 3),
        "wall_between_ch": round(PITCH - hd, 3),
        "wall_to_end": round(END_L + DISC_D / 2 - hd / 2, 3),
        "disc_inside_strap": round(STRAP_W / 2 - PN / 2 - DISC_D / 2, 3),
        "stack_t_fpc_tpu_mm": round(FPC_T + LAYER_T, 3),
        "stack_t_with_pi_and_9448a_mm": round(PI_T + FPC_T + TAPE_9448A_T + LAYER_T, 3),
        "pocket_floor": round(LAYER_T - POCKET_D, 3),
        "pockets": {"north": len(pockets(NORTH_YS)), "south": len(pockets(SOUTH_YS))},
    } | gaps()


if __name__ == "__main__":
    out = summary()
    for name, ys in (("north", NORTH_YS), ("south", SOUTH_YS)):
        p = build_piece(ys, label=f"layer_d2_8ch_{name}")
        bb = p.bounding_box()
        step_path = HERE / f"layer_d2_8ch_{name}.step"
        stl_path = HERE / f"layer_d2_8ch_{name}.stl"
        b.export_step(p, str(step_path))
        b.export_stl(b.Pos(-bb.min.X, -bb.min.Y, 0) * p, str(stl_path), tolerance=0.01, angular_tolerance=0.1)
        out[name] = {
            "bbox": [round(v, 3) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
            "volume_mm3": round(p.volume, 1),
            "solids": len(p.solids()),
            "valid": p.is_valid,
        }
    (HERE / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
