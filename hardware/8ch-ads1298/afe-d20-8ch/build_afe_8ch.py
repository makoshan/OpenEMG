"""从 D20 / D20N 派生纯单面贴 8 通道采集板（afe-d20-8ch / afe-d20n-8ch）：
1. 只读遍历一次源板，全部转为纯 Python 纳米整数结构（避开 pcbnew Remove 后 SWIG 悬空指针）；
2. 删除背面全部封装（51 颗贴片 + TP903/904）及背面丝印；
3. 对原本借道背面焊盘连通正面器件的 7 个网络补齐精确纳米坐标 135°/共线桥接段；
4. 纯内存执行 T 接拆分 → 死端线段/单端过孔/孤立残岛迭代剪枝 → 同层同网同宽 180° 共线段合并；
5. 重新 LoadBoard 一次性批量删除/新增，重铺铜皮并生成泪滴。
"""
import collections, math, subprocess, sys
import pcbnew as k

SRC, DST, REV_TAG = sys.argv[1], sys.argv[2], sys.argv[3]  # e.g. D20-8CH or D20N-8CH

# ---------- Pass 1: Read-only extraction ----------
b0 = k.LoadBoard(SRC)

pads_py = []  # (nc, netname, set_of_layers, x, y, sx, sy, shape, pad_idx, poly_bbox, hit_fn_data)
# Since b0 is NEVER mutated in Pass 1, b0's pad.HitTest works 100% reliably!
top_pads_obj = []
for f in b0.GetFootprints():
    if f.IsFlipped():
        continue
    for p in f.Pads():
        nc = p.GetNetCode()
        if nc > 0:
            top_pads_obj.append((nc, p.GetNetname(), set(p.GetLayerSet().CuStack()), p))

zones_py = []
for z in b0.Zones():
    if not z.IsTeardropArea() and not z.GetIsRuleArea() and z.GetNetCode() > 0:
        zones_py.append((z.GetNetCode(), z.GetNetname(), set(z.GetLayerSet().CuStack()), z))

pad_counts = collections.Counter(nc for nc, _, _, _ in top_pads_obj)
zone_ncs = {nc for nc, _, _, _ in zones_py}
active_ncs = {nc for nc, cnt in pad_counts.items() if cnt >= 2} | zone_ncs
nc_by_name = {nn: nc for nc, nn, _, _ in top_pads_obj}

segs_py = []  # list of [nc, nn, layer, w, x1, y1, x2, y2]
vias_py = []  # list of [nc, nn, x, y, width, drill, vtype, ltop, lbot]
for t in b0.GetTracks():
    nc = t.GetNetCode()
    if nc not in active_ncs:
        continue
    nn = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        vp = t.GetPosition()
        vias_py.append([nc, nn, vp.x, vp.y, t.GetWidth(k.F_Cu), t.GetDrillValue(), t.GetViaType(), t.TopLayer(), t.BottomLayer()])
    elif t.GetClass() == 'PCB_TRACK':
        s, e = t.GetStart(), t.GetEnd()
        segs_py.append([nc, nn, t.GetLayer(), t.GetWidth(), s.x, s.y, e.x, e.y])

# Find exact nanometer endpoints for the 7 B.Cu bridges!
def find_ep_near(nn, lyr, x_mm, y_mm, tol_nm=20000):
    tx, ty = round(x_mm * 1_000_000), round(y_mm * 1_000_000)
    best = None
    for s in segs_py:
        if s[1] == nn and s[2] == lyr:
            for px, py in ((s[4], s[5]), (s[6], s[7])):
                d = math.hypot(px - tx, py - ty)
                if d <= tol_nm and (best is None or d < best[0]):
                    best = (d, px, py, s[3])
    assert best is not None, f"Endpoint not found for {nn} near ({x_mm}, {y_mm})"
    return best[1], best[2], best[3]

def find_via_near(nn, x_mm, y_mm, tol_nm=20000):
    tx, ty = round(x_mm * 1_000_000), round(y_mm * 1_000_000)
    for v in vias_py:
        if v[1] == nn and math.hypot(v[2] - tx, v[3] - ty) <= tol_nm:
            return v[2], v[3]
    raise AssertionError(f"Via not found for {nn} near ({x_mm}, {y_mm})")

# Add exact 135-deg / collinear bridges on B.Cu:
# For vertical pair (x1, y1) with y1 < y2 and (x2, y2):
# Going UP from (x1, y1): 45-deg step (x2, y1 + |x2 - x1|) -> vertical to (x2, y2)!
for nn, (ax, ay), (bx, by) in [
    ("ADS_PWDN",  (24.200, 24.450), (24.250, 25.250)),
    ("ADS_RESET", (23.700, 24.450), (23.750, 25.250)),
    ("ADS_START", (22.750, 24.450), (22.750, 25.250)),
    ("AFE_GPIO3", (19.250, 24.450), (19.250, 25.250)),
    ("DIN_B",     (24.800, 24.450), (24.750, 25.250)),
    ("DOUT_B",    (20.300, 24.450), (20.250, 25.250)),
]:
    x1, y1, w = find_ep_near(nn, k.B_Cu, ax, ay)
    x2, y2, _ = find_ep_near(nn, k.B_Cu, bx, by)
    nc = nc_by_name[nn]
    dx = abs(x2 - x1)
    if dx <= 2000:
        segs_py.append([nc, nn, k.B_Cu, w, x1, y1, x2, y2])
    else:
        ym = y1 + dx  # exact 45-degree chamfer going north!
        assert ym < y2, (nn, y1, ym, y2)
        segs_py.append([nc, nn, k.B_Cu, w, x1, y1, x2, ym])
        segs_py.append([nc, nn, k.B_Cu, w, x2, ym, x2, y2])

# V4_-2.5V bridge: from (30.200, 19.950) west-going horizontal seg (31.300,19.950)->(30.200,19.950)
# Wait! That segment came WEST from (31.300, 19.950) to (30.200, 19.950)!
# If we go SOUTH from (30.200, 19.950), west->south is a 90-degree corner!
# Instead, to make a 135-degree corner from west-going (31.300, 19.950)->(x, 19.950) down-west to VIA (29.800, 18.950):
# Let's check! From (30.800, 19.950) -> 45-deg SW by (1.000, 1.000) -> lands EXACTLY on VIA (29.800, 18.950)!!
# Wait: 30.800 - 29.800 = 1.000 mm, and 19.950 - 18.950 = 1.000 mm!!
# Let's check if (30.800, 19.950) lies right on the existing segment (30.200, 19.950)->(31.300, 19.950)!
# YES!! 30.200 <= 30.800 <= 31.300! So going west to (30.800, 19.950) then SW 45° to (29.800, 18.950) is a PURE 135° angle, and the dead tail (30.800, 19.950)->(30.200, 19.950) gets pruned automatically!!
vx, vy = find_via_near("V4_-2.5V", 29.800, 18.950)
_, y_horz, w_m25 = find_ep_near("V4_-2.5V", k.B_Cu, 30.200, 19.950)
dy_m25 = y_horz - vy  # ~1.000 mm
jx = vx + dy_m25      # ~30.800 mm, exact 45-deg SW to (vx, vy)!
segs_py.append([nc_by_name["V4_-2.5V"], "V4_-2.5V", k.B_Cu, w_m25, jx, y_horz, vx, vy])

# ---------- Pure Python geometry helpers ----------
def pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

# Split T-junctions in segs_py
def split_tees_py(segs):
    changed = True
    while changed:
        changed = False
        n = len(segs)
        for i in range(n):
            nc, nn, lyr, w, x1, y1, x2, y2 = segs[i]
            for ex, ey in ((x1, y1), (x2, y2)):
                for j in range(n):
                    if i == j:
                        continue
                    s2 = segs[j]
                    if s2[0] != nc or s2[2] != lyr:
                        continue
                    ax, ay, bx, by = s2[4], s2[5], s2[6], s2[7]
                    if math.hypot(ex - ax, ey - ay) <= 1000 or math.hypot(ex - bx, ey - by) <= 1000:
                        continue
                    if pt_seg_dist(ex, ey, ax, ay, bx, by) <= 1000:
                        segs[j] = [s2[0], s2[1], s2[2], s2[3], ax, ay, ex, ey]
                        segs.append([s2[0], s2[1], s2[2], s2[3], ex, ey, bx, by])
                        changed = True
                        break
                if changed:
                    break
            if changed:
                break

split_tees_py(segs_py)

# Also split any segment where a same-net via sits in the middle of the segment (so stubs beyond vias prune cleanly!)
v_split = True
while v_split:
    v_split = False
    for v in vias_py:
        vnc, _, vx, vy, vw, *_ = v
        for j in range(len(segs_py)):
            s = segs_py[j]
            if s[0] != vnc:
                continue
            ax, ay, bx, by = s[4], s[5], s[6], s[7]
            if math.hypot(vx - ax, vy - ay) <= 2000 or math.hypot(vx - bx, vy - by) <= 2000:
                continue
            if pt_seg_dist(vx, vy, ax, ay, bx, by) <= 2000:
                segs_py[j] = [s[0], s[1], s[2], s[3], ax, ay, vx, vy]
                segs_py.append([s[0], s[1], s[2], s[3], vx, vy, bx, by])
                v_split = True
                break
        if v_split:
            break

def pt_on_top_pad(px, py, nc, lyr=None):
    P = k.VECTOR2I(px, py)
    for pnc, _, players, pobj in top_pads_obj:
        if pnc == nc and (lyr is None or lyr in players) and pobj.HitTest(P):
            return True
    return False

def pt_on_via(px, py, nc, vias):
    for v in vias:
        if v[0] == nc and math.hypot(px - v[2], py - v[3]) <= v[4] // 2:
            return True
    return False

# Iterative pruning of dangling segments and single-layer vias!
rm_seg_cnt = 0
rm_via_cnt = 0
changed = True
while changed:
    changed = False
    # Remove zero-length segments
    segs_py = [s for s in segs_py if math.hypot(s[6] - s[4], s[7] - s[5]) > 500]
    ep_deg = collections.Counter()
    for nc, nn, lyr, w, x1, y1, x2, y2 in segs_py:
        ep_deg[(nc, lyr, x1, y1)] += 1
        ep_deg[(nc, lyr, x2, y2)] += 1

    keep_segs = []
    for s in segs_py:
        nc, nn, lyr, w, x1, y1, x2, y2 = s
        d1 = ep_deg[(nc, lyr, x1, y1)] == 1 and not pt_on_top_pad(x1, y1, nc, lyr) and not pt_on_via(x1, y1, nc, vias_py)
        d2 = ep_deg[(nc, lyr, x2, y2)] == 1 and not pt_on_top_pad(x2, y2, nc, lyr) and not pt_on_via(x2, y2, nc, vias_py)
        if d1 or d2:
            rm_seg_cnt += 1
            changed = True
        else:
            keep_segs.append(s)
    segs_py = keep_segs
    if changed:
        continue

    # Check dead-end vias (including GND/AGND fanout vias that were outside zones? No, GND/AGND vias touch 4-layer GND/AGND zones; non-GND/AGND vias need >=2 connected layers)
    keep_vias = []
    for v in vias_py:
        nc, nn, vx, vy, vw, *_ = v
        if nn in ("GND", "AGND"):
            keep_vias.append(v)
            continue
        rad = vw // 2 + 2000
        lyrs = set()
        Vpt = k.VECTOR2I(vx, vy)
        for pnc, _, players, pobj in top_pads_obj:
            if pnc == nc and pobj.HitTest(Vpt, rad):
                lyrs |= players
        for s in segs_py:
            if s[0] == nc and pt_seg_dist(vx, vy, s[4], s[5], s[6], s[7]) <= rad:
                lyrs.add(s[2])
        for znc, _, zlayers, zobj in zones_py:
            if znc == nc and zobj.Outline().Contains(Vpt):
                lyrs |= zlayers
        if len(lyrs) < 2:
            rm_via_cnt += 1
            changed = True
        else:
            keep_vias.append(v)
    vias_py = keep_vias

# Remove any unanchored islands (segments/vias on non-GND/AGND nets that don't reach any Top pad or 3V3 zone)
n_s, n_v = len(segs_py), len(vias_py)
tot = n_s + n_v
par = list(range(tot))
def ufind(i):
    while par[i] != i:
        par[i] = par[par[i]]
        i = par[i]
    return i
def uunion(i, j):
    par[ufind(i)] = ufind(j)

anchored = set()
for i, s in enumerate(segs_py):
    nc, nn, lyr, w, x1, y1, x2, y2 = s
    if nn in ("GND", "AGND"):
        anchored.add(i); continue
    for pnc, _, players, pobj in top_pads_obj:
        if pnc == nc and lyr in players:
            if pobj.HitTest(k.VECTOR2I(x1, y1), 2000) or pobj.HitTest(k.VECTOR2I(x2, y2), 2000) or pt_seg_dist(pobj.GetPosition().x, pobj.GetPosition().y, x1, y1, x2, y2) <= min(pobj.GetSize().x, pobj.GetSize().y)//2:
                anchored.add(i); break
for k_i, v in enumerate(vias_py):
    idx = n_s + k_i
    nc, nn, vx, vy, vw, *_ = v
    if nn in ("GND", "AGND"):
        anchored.add(idx); continue
    Vpt = k.VECTOR2I(vx, vy); rad = vw // 2 + 2000
    if any(pnc == nc and pobj.HitTest(Vpt, rad) for pnc, _, _, pobj in top_pads_obj):
        anchored.add(idx)
    if any(znc == nc and zobj.Outline().Contains(Vpt) for znc, _, _, zobj in zones_py):
        anchored.add(idx)

for i in range(n_s):
    s1 = segs_py[i]
    if s1[1] in ("GND", "AGND"): continue
    for j in range(i + 1, n_s):
        s2 = segs_py[j]
        if s1[0] == s2[0] and s1[2] == s2[2]:
            if (pt_seg_dist(s1[4], s1[5], s2[4], s2[5], s2[6], s2[7]) <= 2000 or
                pt_seg_dist(s1[6], s1[7], s2[4], s2[5], s2[6], s2[7]) <= 2000 or
                pt_seg_dist(s2[4], s2[5], s1[4], s1[5], s1[6], s1[7]) <= 2000 or
                pt_seg_dist(s2[6], s2[7], s1[4], s1[5], s1[6], s1[7]) <= 2000):
                uunion(i, j)
    for k_i, v in enumerate(vias_py):
        if s1[0] == v[0] and pt_seg_dist(v[2], v[3], s1[4], s1[5], s1[6], s1[7]) <= v[4]//2 + 2000:
            uunion(i, n_s + k_i)

good_r = {ufind(i) for i in anchored}
segs_keep = [segs_py[i] for i in range(n_s) if ufind(i) in good_r]
vias_keep = [vias_py[k_i] for k_i in range(n_v) if ufind(n_s + k_i) in good_r]
island_cnt = (n_s - len(segs_keep)) + (n_v - len(vias_keep))
segs_py, vias_py = segs_keep, vias_keep

# Bevel the single remaining 90-deg corner on V4_REF2 F.Cu at (17.700, 16.400) where the pruned U2 via branched off
c_ref2 = (17_700_000, 16_400_000)
bev = 250_000  # 0.250 mm 45-degree chamfer -> (17.700, 16.150) to (17.450, 16.400)
ref2_vert = ref2_horz = None
for idx, s in enumerate(segs_py):
    if s[1] == "V4_REF2" and s[2] == k.F_Cu:
        pts = ((s[4], s[5]), (s[6], s[7]))
        if c_ref2 in pts:
            other = pts[1] if pts[0] == c_ref2 else pts[0]
            if other[0] == c_ref2[0] and other[1] < c_ref2[1]:
                ref2_vert = (idx, other)
            elif other[1] == c_ref2[1] and other[0] < c_ref2[0]:
                ref2_horz = (idx, other)
assert ref2_vert is not None and ref2_horz is not None, "Expected V4_REF2 90-deg corner at (17.7, 16.4)"
iv, pv = ref2_vert
ih, ph = ref2_horz
w_r2, nc_r2 = segs_py[iv][3], segs_py[iv][0]
p_bv1 = (c_ref2[0], c_ref2[1] - bev)
p_bv2 = (c_ref2[0] - bev, c_ref2[1])
segs_py[iv] = [nc_r2, "V4_REF2", k.F_Cu, w_r2, pv[0], pv[1], p_bv1[0], p_bv1[1]]
segs_py[ih] = [nc_r2, "V4_REF2", k.F_Cu, w_r2, p_bv2[0], p_bv2[1], ph[0], ph[1]]
segs_py.append([nc_r2, "V4_REF2", k.F_Cu, w_r2, p_bv1[0], p_bv1[1], p_bv2[0], p_bv2[1]])

# Merge collinear 180-deg equal-width segments
merged_cnt = 0
m_chg = True
while m_chg:
    m_chg = False
    ep_all = collections.Counter()
    ep_by_w = collections.defaultdict(list)
    for idx, s in enumerate(segs_py):
        nc, nn, lyr, w, x1, y1, x2, y2 = s
        ep_all[(nc, lyr, x1, y1)] += 1
        ep_all[(nc, lyr, x2, y2)] += 1
        ep_by_w[(nc, lyr, w, x1, y1)].append(idx)
        ep_by_w[(nc, lyr, w, x2, y2)].append(idx)
    for (nc, lyr, w, x, y), idxs in ep_by_w.items():
        if len(idxs) != 2 or ep_all[(nc, lyr, x, y)] != 2:
            continue
        if pt_on_via(x, y, nc, vias_py) or pt_on_top_pad(x, y, nc, lyr):
            continue
        i1, i2 = idxs
        if i1 == i2:
            continue
        s1, s2 = segs_py[i1], segs_py[i2]
        q1 = (s1[6], s1[7]) if (s1[4], s1[5]) == (x, y) else (s1[4], s1[5])
        q2 = (s2[6], s2[7]) if (s2[4], s2[5]) == (x, y) else (s2[4], s2[5])
        dx1, dy1 = q1[0] - x, q1[1] - y
        dx2, dy2 = q2[0] - x, q2[1] - y
        l1, l2 = math.hypot(dx1, dy1), math.hypot(dx2, dy2)
        if l1 > 0 and l2 > 0 and (dx1 * dx2 + dy1 * dy2) / (l1 * l2) < -0.9999:
            segs_py[i1] = [nc, s1[1], lyr, w, q1[0], q1[1], q2[0], q2[1]]
            segs_py.pop(i2)
            merged_cnt += 1
            m_chg = True
            break

# ---------- Pass 2: Fresh LoadBoard, single-batch Remove/Add, Save ----------
b = k.LoadBoard(SRC)
rm_fps = [f for f in b.GetFootprints() if f.IsFlipped()]
rm_tds = [z for z in b.Zones() if z.IsTeardropArea()]
rm_drw = [d for d in b.GetDrawings() if d.GetLayer() in (k.B_Fab, k.B_CrtYd) or (d.GetLayer() == k.B_SilkS and not (d.GetClass() == 'PCB_TEXT' and 'OpenEMG D20' in d.GetText()))]
rm_trk = list(b.GetTracks())
brd_txts = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and 'OpenEMG D20' in d.GetText()]

for x in rm_fps + rm_tds + rm_drw + rm_trk:
    b.Remove(x)

for nc, nn, lyr, w, x1, y1, x2, y2 in segs_py:
    t = k.PCB_TRACK(b)
    t.SetNetCode(nc); t.SetLayer(lyr); t.SetWidth(w)
    t.SetStart(k.VECTOR2I(x1, y1)); t.SetEnd(k.VECTOR2I(x2, y2))
    b.Add(t)

for nc, nn, vx, vy, vw, vdrill, vtype, ltop, lbot in vias_py:
    v = k.PCB_VIA(b)
    v.SetNetCode(nc); v.SetPosition(k.VECTOR2I(vx, vy))
    v.SetViaType(vtype); v.SetLayerPair(ltop, lbot)
    v.SetWidth(vw); v.SetDrill(vdrill)
    v.SetTeardropsEnabled(True)
    b.Add(v)

for f in b.GetFootprints():
    for pad in f.Pads():
        if f.GetReference() == 'J_AFE' and pad.GetNumber() in ('3', '4'):
            pad.SetNetCode(0)  # 8 通道单面版无背面 U2，DRDY_B/CS_B 置为 NC
        pad.SetTeardropsEnabled(True)

for d in brd_txts:
    if d.GetLayer() == k.F_SilkS:
        # 字高 0.95 mm、线宽 0.16 mm：高于嘉立创 0.80/0.15 下限，右端避开 D927 焊盘阻焊开窗
        d.SetText(f"OpenEMG {REV_TAG}")
        d.SetTextSize(k.VECTOR2I(k.FromMM(0.95), k.FromMM(0.95)))
        d.SetTextThickness(k.FromMM(0.16))
    elif d.GetLayer() == k.B_SilkS:
        d.SetText(f"OpenEMG {REV_TAG} B")

tb = b.GetTitleBlock(); tb.SetRevision(REV_TAG); tb.SetDate('2026-11-12'); tb.SetTitle(f'C08B AFE {REV_TAG} single-sided')
b.Save(DST)

subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli', 'pcb', 'drc', '--refill-zones', '--save-board', '-o', '/dev/null', DST], check=True)
b_chk = k.LoadBoard(DST)
td_cnt = sum(1 for z in b_chk.Zones() if z.IsTeardropArea())
print(f"[{REV_TAG}] Done! pruned_segs={rm_seg_cnt}, pruned_vias={rm_via_cnt}, islands={island_cnt}, merged={merged_cnt} -> tracks={len(segs_py)}, vias={len(vias_py)}, teardrops={td_cnt}")
