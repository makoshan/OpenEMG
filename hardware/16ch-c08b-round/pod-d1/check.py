"""小节门：实体探点（凹槽能装泡棉、凹槽上有底、槽能过带、唇边压得住、端墙在）+ 规格门（壁厚、凸出、腕围、电极间距）。
改坏版本必须判红。探点用实物尺寸（泡棉径、带宽），不拿生成时算出的孔径当答案。"""
import copy, json, math, sys
from pathlib import Path
import build123d as b
import build as m

def ins(p, x, y, z):
    return p.is_inside(b.Vector(x, y, z))

def ring(r, n=16):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]

def probe(pod, P=m, whole=True):
    """whole=False：pod 是整条平移到这一节居中，只核这一节的几何，不核包围盒和规格门。"""
    bad = []
    z0, z1, z2 = P.heights()
    for y in (-P.E_PITCH / 2, P.E_PITCH / 2):
        # 泡棉放得进：泡棉径 + 0.1 一圈在凹槽半深处是空的
        want = P.FOAM_T - P.PAD_PROUD
        for zz in (0.05, want / 2, want - 0.05):   # 复核 11-11：口部、半深、底部三层都扫，防缩口和台阶
            if any(ins(pod, dx, y + dy, zz) for dx, dy in ring(P.FOAM_D / 2 + 0.1)): bad.append(f'凹槽装不下 Φ{P.FOAM_D} 泡棉 y={y} z={zz:.2f}'); break
        # 凹槽深度：深度以上 0.1 是实的（有底），深度以下 0.1 是空的
        # 凹槽深度按「泡棉厚 − 目标凸出」核几何，不拿 POCKET_D 自己比
        for dx, dy in [(0, 0)] + ring(2.5, 8):   # 中心 + 半径 2.5 一圈，防锥底、环形底
            if not ins(pod, dx, y + dy, want + 0.1): bad.append(f'凹槽太深或没底（要 {want:.2f}）y={y}'); break
            if ins(pod, dx, y + dy, max(want - 0.1, 0.02)): bad.append(f'凹槽不够深（要 {want:.2f}）y={y}'); break
    # 复核 11-11：探点沿 x 多取几列，沿 y 每 1 mm 一点，防只在 x=0 探漏掉局部筋、缺唇、薄底
    xs = (-(P.POD_W / 2 - 0.25), -2.0, 0.0, 2.0, P.POD_W / 2 - 0.25)
    hb = max(P.ch_half() - 0.05, P.STRAP_W / 2 + 0.1)   # 带侧移贴墙也要过；不小于带宽本身（防槽窄于带时自比漏判）
    ys = [-hb + 0.5 * i for i in range(int(2 * hb / 0.5) + 1)] + [hb]
    for x in xs:
        for yy in ys:   # 带能过：整个槽宽、带厚 + 0.15 内全空
            for zz in (z0 + 0.1, z0 + P.STRAP_T + 0.15):
                if ins(pod, x, yy, zz): bad.append(f'带槽挡带 x={x:.2f} y={yy:.2f} z={zz:.2f}'); break
        for sg in (-1, 1):   # 唇边压住带边、端墙在
            if not ins(pod, x, sg * (P.STRAP_W / 2 - 0.5), z1 + P.LIP_T / 2): bad.append(f'唇边缺 x={x:.2f} {sg}')
            if not ins(pod, x, sg * (P.POD_L / 2 - 0.3), z0 + 0.5): bad.append(f'端墙缺 x={x:.2f} {sg}')
        if ins(pod, x, 0, z1 + P.LIP_T / 2): bad.append(f'顶上没开口 x={x:.2f}')
        for sg in (-1, 1):   # 唇边下 45° 斜撑（平放打印不悬空）
            if not ins(pod, x, sg * (P.ch_half() - 0.1), z1 - 0.3): bad.append(f'唇边下没斜撑 x={x:.2f} {sg}'); break
        for yy in [-P.POD_L / 2 + 0.3 + i for i in range(int(P.POD_L - 0.6) + 1)]:   # 底座全长实心到 BASE_T（凹槽外）
            if abs(abs(yy) - P.E_PITCH / 2) < (P.FOAM_D + P.POCKET_CLEAR) / 2 + 0.2: continue
            if not ins(pod, x, yy, P.BASE_T - 0.1) or not ins(pod, x, yy, 0.1): bad.append(f'底座缺/薄 x={x:.2f} y={yy:.2f}'); break
    if not whole:
        return bad
    # 整体：单实体、包围盒等于名义尺寸
    if len(pod.solids()) != 1: bad.append(f'实体数 {len(pod.solids())} ≠ 1')
    bb = pod.bounding_box()
    want = (P.POD_W, P.POD_L, z2)
    got = (bb.size.X, bb.size.Y, bb.size.Z)
    if any(abs(g - w) > 0.01 for g, w in zip(got, want)): bad.append(f'包围盒 {[round(g, 2) for g in got]} ≠ {want}')
    if bb.min.Z < -1e-6: bad.append('有东西低于皮肤面')
    # 规格门
    s = P.summary()
    # 铜片版（11-11）：总凸出 = 泡棉顶出 + FPC + 铜片，门 1.2–2.0（旧定表带电极同高 1.6）；泡棉压到底也要 ≥ 0.8
    if not 1.2 - 1e-9 <= s["contact_proud"] <= 2.0 + 1e-9: bad.append(f'铜片总凸出 {s["contact_proud"]} 不在 1.2–2.0')
    if s["contact_proud_bottomed"] < 0.8 - 1e-9: bad.append(f'泡棉压到底铜片只凸 {s["contact_proud_bottomed"]} < 0.8')
    if s["pad_proud"] < 0.2 - 1e-9: bad.append(f'泡棉只顶出 {s["pad_proud"]}，没有弹性行程')
    if P.E_D < P.FOAM_D + P.POCKET_CLEAR - 1e-9: bad.append(f'铜片 Φ{P.E_D} 比凹槽 Φ{P.FOAM_D + P.POCKET_CLEAR} 小，压到底会陷进凹槽')
    for k in ("floor_over_pocket", "side_wall_at_pocket", "end_wall_at_pocket", "end_wall_t"):
        if s[k] < P.MIN_WALL - 1e-9: bad.append(f'{k} {s[k]:.2f} < {P.MIN_WALL}')
    if P.LIP_T < P.MIN_WALL - 1e-9: bad.append(f'唇边厚 {P.LIP_T} < {P.MIN_WALL}')
    if not 0.8 - 1e-9 <= P.LIP_OVER <= 2.0 + 1e-9: bad.append(f'唇边伸出 {P.LIP_OVER} 不在 0.8–2.0')
    ov = (P.STRAP_W / 2 - P.CH_CLEAR_W / 2) - (P.ch_half() - P.LIP_OVER)
    if ov < 0.3 - 1e-9: bad.append(f'带侧移到底时唇边只压住 {ov:.2f} < 0.3')
    if P.CH_CLEAR_T < P.LIP_OVER + 0.15 - 1e-9: bad.append(f'槽高余量 {P.CH_CLEAR_T} < 斜撑 {P.LIP_OVER} + 0.15，带贴墙会顶到斜撑')
    if P.POCKET_CLEAR < 0.2 - 1e-9: bad.append(f'凹槽余量 {P.POCKET_CLEAR} < 0.2')
    if P.E_D + 2 * P.MIN_WALL > P.POD_W + 1e-9: bad.append(f'电极 Φ{P.E_D} 放不进节宽 {P.POD_W}')
    if P.E_PITCH / 2 + P.E_D / 2 + P.MIN_WALL > P.POD_L / 2 + 1e-9: bad.append('电极出节端')
    if abs(P.E_PITCH - 20.0) > 1e-9: bad.append(f'P/N 间距 {P.E_PITCH} ≠ 20（D1 定的）')
    if s["min_wrist_touching"] > P.WRIST_MAKO + 1e-9: bad.append(f'节贴节也要腕围 {s["min_wrist_touching"]} > Mako {P.WRIST_MAKO}')
    if P.FOAM_D > P.E_D + 1e-9: bad.append('泡棉比焊盘大')
    return bad

FPC_FREE_Y = 13.4   # 缝里 |y| < 13.4 必须全空：凹槽口外沿 10 + 3.2 + 0.2，FPC 走线和桨片都在这里


def strip_probe(strip, P=m):
    """整条：单实体、长度、每节凹槽都在、每个缝都有桥、桥下 FPC 走线区（|y| < 13.4）缝是空的、总长不超腕围。"""
    bad = []
    if len(strip.solids()) != 1: bad.append(f'整条实体数 {len(strip.solids())} ≠ 1')
    xs = P.pod_xs()
    want_len = (P.N_PODS - 1) * P.pitch() + P.POD_W
    bb = strip.bounding_box()
    if abs(bb.size.X - want_len) > 0.02: bad.append(f'整条长 {bb.size.X:.2f} ≠ {want_len:.2f}')
    for x in xs:
        for y in (-P.E_PITCH / 2, P.E_PITCH / 2):
            if ins(strip, x, y, 0.5): bad.append(f'节 x={x:.2f} 凹槽没了'); break
    z2 = P.heights()[2]
    if abs(bb.size.Y - P.POD_L) > 0.02 or abs(bb.size.Z - z2) > 0.02: bad.append(f'整条 Y/Z {bb.size.Y:.2f}/{bb.size.Z:.2f} ≠ {P.POD_L}/{z2:.2f}')
    for x in xs:   # 复核 11-11：每一节都按单节的几何门核（平移到原点），节距不均也会在这里红
        bad += [f'第 {xs.index(x) + 1} 节: {e}' for e in probe(b.Pos(-x, 0, 0) * strip, P, whole=False)]
    for xa, xb in zip(xs, xs[1:]):
        xm = (xa + xb) / 2
        yb = max(P.BRIDGE_Y0, FPC_FREE_Y)   # 中段全空按固定的 FPC 走线区核，不拿 BRIDGE_Y0 自比
        for yy in [-yb + 0.1 + 0.5 * i for i in range(int((2 * yb - 0.2) / 0.5) + 1)]:   # 缝中段全高都空
            if any(ins(strip, xm, yy, zz) for zz in (0.3, 1.5, 3.0, z2 - 0.2)): bad.append(f'缝 x={xm:.2f} y={yy:.1f} 被堵'); break
        for sg in (-1, 1):
            yb = P.BRIDGE_Y0
            for yy in [yb + 0.1 + 0.4 * i for i in range(int((P.POD_L / 2 - yb - 0.2) / 0.4) + 1)]:   # 桥：只在 |y| ≥ BRIDGE_Y0，只有 BRIDGE_T 厚
                if not ins(strip, xm, sg * yy, P.BRIDGE_T / 2): bad.append(f'缝 x={xm:.2f} 少桥 {sg}'); break
                if ins(strip, xm, sg * yy, P.BRIDGE_T + 0.2): bad.append(f'缝 x={xm:.2f} 桥变墙 {sg}'); break
    if P.pitch() - P.POD_W < 0.5 - 1e-9: bad.append(f'节间缝 {P.pitch() - P.POD_W:.3f} < 0.5，弯不动')
    if P.BRIDGE_T < 0.4 - 1e-9 or P.BRIDGE_T > 1.0 + 1e-9: bad.append(f'桥厚 {P.BRIDGE_T} 不在 0.4–1.0')
    if want_len + P.CAPSULE_L > P.WRIST_MAKO + 1e-9: bad.append(f'整条 + 胶囊 {want_len + P.CAPSULE_L:.1f} > 腕围 {P.WRIST_MAKO}')
    return bad


def run(**over):
    saved = {k: getattr(m, k) for k in over}
    try:
        for k, v in over.items(): setattr(m, k, v)
        try:
            pod = m.build_pod()
            strip = m.build_strip()
        except Exception as e:   # 参数坏到建不出模型也算红
            return [f'建模失败 {type(e).__name__}']
        return probe(pod) + strip_probe(strip)
    finally:
        for k, v in saved.items(): setattr(m, k, v)

res = {"main": run()}
neg = {
 "neg_pocket_tight": dict(POCKET_CLEAR=-0.3),
 "neg_pocket_shallow": dict(POCKET_D=1.0),
 "neg_disc_thin": dict(DISC_T=0.2),
 "neg_disc_small": dict(E_D=6.0),
 "neg_chamfer_big": dict(MOUTH_CHAMFER=0.6),
 "neg_pitch_big": dict(PITCH=9.5),
 "neg_gap_tiny": dict(POD_W=8.6),
 "neg_bridge_thin": dict(BRIDGE_T=0.2),
 "neg_bridge_into_fpc": dict(BRIDGE_Y0=11.0),
 "neg_pocket_through": dict(POCKET_D=2.5),
 "neg_proud_big": dict(FOAM_T=3.0, POCKET_D=1.5),
 "neg_channel_narrow": dict(CH_CLEAR_W=-0.6),
 "neg_channel_low": dict(CH_CLEAR_T=-0.5),
 "neg_no_lip": dict(LIP_OVER=0.0),
 "neg_lip_closed": dict(LIP_OVER=13.0),
 "neg_lip_thin": dict(LIP_T=0.4),
 "neg_pod_short": dict(POD_L=26.0),
 "neg_pod_narrow": dict(POD_W=7.0),
 "neg_pitch_18": dict(E_PITCH=18.0),
 "neg_too_many_pods": dict(N_PODS=18),
 "neg_base_thin": dict(BASE_T=1.9),
 "neg_foam_big": dict(FOAM_D=7.0),
}
for k, kw in neg.items(): res[k] = run(**kw)
_bp = m.build_pod   # 凹槽没开（几何真漏，参数都对）
def _no_pocket():
    hw, hl = m.POD_W / 2, m.POD_L / 2
    return m.box(-hw, hw, -hl, hl, 0, m.heights()[2])
m.build_pod = _no_pocket
try: res["neg_solid_block"] = probe(m.build_pod())
finally: m.build_pod = _bp
# 复核 11-11 漏判的几何坏件：参数都对，模型局部坏
_g = m.build_pod()
geo = {
 "neg_rib_in_channel_y5": _g + m.box(-1, 1, 4.5, 5.5, m.BASE_T, m.BASE_T + 1.0),
 "neg_half_lip_missing": _g - m.box(0, m.POD_W, -m.POD_L, m.POD_L, m.heights()[1] + 0.01, m.heights()[2] + 1),
 "neg_block_at_x3": _g + m.box(3, m.POD_W / 2, -2, 2, m.BASE_T, m.BASE_T + 1.0),
 "neg_base_thin_mid": _g - m.box(-m.POD_W, m.POD_W, -3, 3, 1.2, m.BASE_T + 0.01),
 "neg_taller": _g + m.box(-m.POD_W / 2, m.POD_W / 2, 13.5, 15, m.heights()[2] - 0.1, 6.5),
 "neg_floating_chip": _g + m.box(20, 21, 0, 1, 0, 1),
}
# 复核 11-11 第二轮：凹槽局部坏（参数都对）
def _ring_solid(y, r_out, r_in, z0, z1):
    return (b.Pos(0, y, (z0 + z1) / 2) * b.Cylinder(r_out, z1 - z0)) - (b.Pos(0, y, (z0 + z1) / 2) * b.Cylinder(r_in, z1 - z0))
_pr = (m.FOAM_D + m.POCKET_CLEAR) / 2
geo["neg_pocket_step_bottom"] = _g + _ring_solid(10, _pr + 0.01, 2.5, 1.1, 1.51)
geo["neg_pocket_mouth_narrow"] = _g + _ring_solid(10, _pr + m.MOUTH_CHAMFER + 0.01, 2.6, 0.0, 0.2)
geo["neg_pocket_cone_floor"] = _g + (b.Pos(0, 10, 1.2) * b.Cone(_pr, 0.5, 0.31, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN)))
for k, g in geo.items(): res[k] = probe(g)
_s = m.build_strip()   # 整条局部坏：少一座桥、多一个填缝块、两节之间断开
res["neg_strip_missing_bridge"] = strip_probe(_s - m.box(m.pod_xs()[7] + 4.1, m.pod_xs()[8] - 4.1, 13.5, 15.1, -0.1, 1.0))
res["neg_strip_gap_filled"] = strip_probe(_s + m.box(m.pod_xs()[3] + 4.0, m.pod_xs()[4] - 4.0, -2, 2, 0, 1))
res["neg_strip_split"] = strip_probe(_s - m.box(m.pod_xs()[10] + 4.0, m.pod_xs()[11] - 4.0, -16, 16, -0.1, 7))
res["neg_lip_no_chamfer"] = probe(m.build_pod() - m.box(-5, 5, 11.0, 13.05, m.heights()[1] - 1.3, m.heights()[1] - 0.001) - m.box(-5, 5, -13.05, -11.0, m.heights()[1] - 1.3, m.heights()[1] - 0.001))
ok = not res["main"] and all(res[k] for k in res if k.startswith("neg_"))
res["summary"] = m.summary(); res["pass"] = ok
(Path(__file__).parent / "checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: (v if k in ("pass", "summary") else [len(v)] + v[:1]) for k, v in res.items()}, ensure_ascii=False, indent=1))
sys.exit(0 if ok else 1)
