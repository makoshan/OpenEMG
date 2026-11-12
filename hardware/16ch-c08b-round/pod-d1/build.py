"""C08B 电极小节 D1（2026-11-11 Mako 选「电极小节 + 现成表带」的 D1）：16 节 TPU 小节，每节两个 Φ6.5 电极沿前臂相距 20 mm。
11-11 定电极：FPC Φ6.5 沉金焊盘上回流焊一片 Φ6.5×1.0 镀金 H62 铜片（淘宝 中通达五金 SMT 镀金铜片），焊盘背后小节挖凹槽塞 Φ6×2 EVA 双面胶泡棉，
泡棉把 FPC 顶出 0.5，铜片总共凸出 0.5 + FPC + 1.0 ≈ 1.6。泡棉压扁到底时铜片边（Φ6.5 > 凹槽 Φ6.4）由小节底面托住，凸出不低于 FPC + 铜片 ≈ 1.1。
表带从小节顶上的槽里过，两端唇边扣住带边。
11-11 Mako「TPU 凹槽可以连接成一个整体」：16 节用两端（|y| > 槽宽）皮肤面的薄 TPU 桥连成一整条，节距按腕围 182 定死，整条打印、整条穿带。
坐标：X 沿表带（节宽），Y 沿前臂（节长），Z 从皮肤面（0）往外。整条平放打印（皮肤面朝下）：唇边下面做 45° 斜撑，没有平悬空；泡棉凹槽顶 Φ6.4 是短桥。
标「假设」的等实物量了改常量，重跑 build.py → check.py → slice.sh。"""
from pathlib import Path
import json
import build123d as b

HERE = Path(__file__).parent

# ---- 布局 ----
N_PODS = 16
POD_W = 8.10           # 沿表带宽（凹槽 Φ6.4 两边各 0.85；整条后要给桥留缝）
PITCH = None           # 节距；None = (腕围 − 胶囊) / 节数，Mako 182 → 8.875
BRIDGE_T = 0.60        # 节间桥厚（皮肤面，Z 0..0.6）
BRIDGE_Y0 = 13.60      # 桥只在 |y| ≥ 13.6 到节端（避开凹槽口 13.4 和中间 FPC 走线）
POD_L = 30.00          # 沿前臂长（要比表带宽 25 多出两端唇边）
CAPSULE_L = 40.00      # 胶囊沿表带方向长度（C08B 46×40）
WRIST_MAKO = 182.0     # Mako 腕围（11-11）
E_PITCH = 20.00        # 同一路 P/N 中心距（Meta 20 mm）
E_D = 6.50             # 电极直径：FPC 焊盘与镀金铜片同 Φ6.5（Meta Φ6.5）
DISC_T = 1.00          # 镀金铜片厚（商品规格「圆形Φ6.5*厚1.0镀金1u」）
FPC_T = 0.11           # FPC 成品厚（嘉立创单面 0.11）

# ---- 泡棉 ----
FOAM_D = 6.00          # EVA 双面胶泡棉点直径（淘宝常见，假设）
FOAM_T = 2.00          # 泡棉厚（假设）
POCKET_CLEAR = 0.40    # 凹槽 = 泡棉径 + 0.4（TPU 孔会缩）
PAD_PROUD = 0.50       # 目标：泡棉把 FPC 顶出小节皮肤面 0.5（铜片自己再凸 1.0）
POCKET_D = 1.50        # 凹槽深；应 = FOAM_T − PAD_PROUD，check.py 按几何核

# ---- 截面 ----
MOUTH_CHAMFER = 0.20   # 凹槽口 45° 倒角（复核 11-11 P1：铜片压到底时 FPC 在口缘被压折）
BASE_T = 2.30          # 底座厚（凹槽上剩 0.8）
STRAP_W = 25.00        # 表带宽（Mako 11-10 量）
STRAP_T = 1.60         # 表带厚（**假设**，没量）
CH_CLEAR_W = 0.60      # 槽宽 = 带宽 + 0.6（带要能滑；带最多侧移 0.3）
CH_CLEAR_T = 1.20      # 槽高 = 带厚 + 1.2：斜撑在墙根低到 z1 − LIP_OVER，带侧移贴墙时带顶仍留 0.2（复核 11-11 P1）
LIP_OVER = 1.00        # 唇边往里伸，压住带边；带侧移到底另一边仍压住 0.4
LIP_T = 0.90           # 唇边厚
MIN_WALL = 0.80        # 嘉立创 / FDM TPU 薄处门


def ch_half():
    return (STRAP_W + CH_CLEAR_W) / 2


def heights():
    z_ch0 = BASE_T
    z_ch1 = z_ch0 + STRAP_T + CH_CLEAR_T
    return z_ch0, z_ch1, z_ch1 + LIP_T


def box(x0, x1, y0, y1, z0, z1):
    return b.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * b.Box(x1 - x0, y1 - y0, z1 - z0)


def build_pod():
    hw, hl, ch = POD_W / 2, POD_L / 2, ch_half()
    z0, z1, z2 = heights()
    s = box(-hw, hw, -hl, hl, 0, BASE_T)
    for sg in (-1, 1):
        y_in, y_out = sorted((sg * ch, sg * hl))
        s += box(-hw, hw, y_in, y_out, z0, z2)                       # 端墙
        y_lip = sorted((sg * (ch - LIP_OVER), sg * ch))
        if LIP_OVER > 0:
            s += box(-hw, hw, y_lip[0], y_lip[1], z1, z2)             # 唇边
            # 唇边下 45° 斜撑：平放打印时唇边不再平悬空（截面三角：唇尖 z1 → 墙根 z1 − LIP_OVER）
            tri = b.Polygon((sg * (ch - LIP_OVER), z1), (sg * ch, z1), (sg * ch, z1 - LIP_OVER), align=None)
            s += b.extrude(b.Plane.YZ * tri, amount=hw, both=True)   # 以 x=0 为中面两边各挤 hw
    pd = FOAM_D + POCKET_CLEAR
    for y in (-E_PITCH / 2, E_PITCH / 2):
        s -= b.Pos(0, y, POCKET_D / 2 - 0.05) * b.Cylinder(pd / 2, POCKET_D + 0.1)
        if MOUTH_CHAMFER > 0:   # 口部倒角：皮肤面开口 Φ(pd + 2c)，往里收到 Φpd
            c = MOUTH_CHAMFER
            s -= b.Pos(0, y, -0.05) * b.Cone(pd / 2 + c + 0.05, pd / 2, c + 0.05, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
    return s.clean()


def pitch():
    return PITCH if PITCH is not None else (WRIST_MAKO - CAPSULE_L) / N_PODS


def pod_xs():
    return [(i - (N_PODS - 1) / 2) * pitch() for i in range(N_PODS)]


def build_strip():
    """16 节 + 节间桥，一个实体。"""
    pod, hw, hl = build_pod(), POD_W / 2, POD_L / 2
    xs = pod_xs()
    s = None
    for x in xs:
        s = b.Pos(x, 0, 0) * pod if s is None else s + b.Pos(x, 0, 0) * pod
    for xa, xb in zip(xs, xs[1:]):
        for sg in (-1, 1):
            y = sorted((sg * BRIDGE_Y0, sg * hl))
            s += box(xa + hw - 0.05, xb - hw + 0.05, y[0], y[1], 0, BRIDGE_T)
    return s.clean()


def mouth_sink():
    """泡棉压到底时铜片边陷进倒角口的深度：倒角斜面半径 r(z) = 凹槽半径 + c − z，铜片边 r = E_D/2 处的 z。"""
    z = (FOAM_D + POCKET_CLEAR) / 2 + MOUTH_CHAMFER - E_D / 2
    return min(max(z, 0.0), MOUTH_CHAMFER)


def summary():
    z0, z1, z2 = heights()
    return {"pod_wlh": [POD_W, POD_L, z2], "pocket_d": FOAM_D + POCKET_CLEAR, "pad_proud": FOAM_T - POCKET_D, "contact_proud": round(FOAM_T - POCKET_D + FPC_T + DISC_T, 3),
            "contact_proud_bottomed": round(FPC_T + DISC_T - mouth_sink(), 3),
            "floor_over_pocket": BASE_T - POCKET_D, "side_wall_at_pocket": POD_W / 2 - (FOAM_D + POCKET_CLEAR) / 2,
            "end_wall_at_pocket": POD_L / 2 - E_PITCH / 2 - (FOAM_D + POCKET_CLEAR) / 2,
            "channel_w": 2 * ch_half(), "lip_opening": 2 * (ch_half() - LIP_OVER), "end_wall_t": POD_L / 2 - ch_half(),
            "min_wrist_touching": CAPSULE_L + N_PODS * POD_W, "pitch": round(pitch(), 3), "gap": round(pitch() - POD_W, 3),
            "strip_len": round((N_PODS - 1) * pitch() + POD_W, 3), "strip_plus_capsule": round((N_PODS - 1) * pitch() + POD_W + CAPSULE_L, 3)}


if __name__ == "__main__":
    pod, strip = build_pod(), build_strip()
    b.export_step(pod, str(HERE / "pod_d1.step"))
    b.export_step(strip, str(HERE / "pod_strip_d1.step"))
    bb = strip.bounding_box()
    b.export_stl(b.Pos(-bb.min.X, -bb.min.Y, 0) * strip, str(HERE / "pod_strip_d1.stl"), tolerance=0.01, angular_tolerance=0.1)
    out = summary() | {"pod_mm3": round(pod.volume, 2), "strip_mm3": round(strip.volume, 1), "valid": strip.is_valid,
                       "solids": len(strip.solids()), "strip_bbox": [round(v, 3) for v in (bb.size.X, bb.size.Y, bb.size.Z)]}
    (HERE / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
