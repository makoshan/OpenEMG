"""板框、禁区和铺铜外形（CAD 坐标），build_board.py、prep_dsn.py、finish.py、check_board.py 共用。
板框同 C08A：43.1×36.5、四角 R4.6（Mako 11-04 定）；11-12 Mako 定拿掉东边 USB 缺口、取消板内 BAT 窗和电池线孔，并拿掉板中 XIAO_ANT 禁布区（XIAO 已在 P44e 转接板上，采集板允许走线铺地）。"""
import math
HW, HH, RC = 21.55, 18.25, 4.6            # 半宽、半高、角半径
HOLES = [(-19.05, -15.75), (-19.05, 15.75), (19.05, 15.75), (19.05, -15.75)]   # 同 C08A H901–H904，φ1.7
J2_AT = (12.0, -11.4)                     # 转角 0：开口朝南，焊盘排在北；20 脚 x 7.25、1 脚 x 16.75，和 P44e J1 的 1、20 脚同 x（XIAO 中心不动，P44e x .5–21.5、y ±8.89）
ELECTRODES = {'E1': (-8, 7.5), 'E2': (8, 7.5), 'E3': (0, 7.5), 'E4': (-8, -7.5), 'E5': (8, -7.5), 'E6': (0, -7.5)}   # 照 C08B 盒底：两排大—辅—大
ER = {'E1': 2.0, 'E2': 2.0, 'E3': 1.5, 'E4': 2.0, 'E5': 2.0, 'E6': 1.5}   # 盘半径：大点 Φ4，辅点 Φ3
outline = [(-HW + .3, HH - .3), (HW - .3, HH - .3), (HW - .3, -HH + .3), (-HW + .3, -HH + .3)]   # 铺铜：KiCad 按板框、孔、禁区再裁


def board_edge(edge, arc):
    """画板框。edge(点列) 画折线，arc(起点, 终点, 中点) 画圆弧。"""
    q = RC * (1 - math.sqrt(.5)); x, y = HW - RC, HH - RC
    edge([(-x, HH), (x, HH)]); arc((x, HH), (HW, y), (HW - q, HH - q))
    edge([(HW, y), (HW, -y)])
    arc((HW, -y), (x, -HH), (HW - q, -HH + q))
    edge([(x, -HH), (-x, -HH)]); arc((-x, -HH), (-HW, -y), (-HW + q, -HH + q))
    edge([(-HW, -y), (-HW, y)]); arc((-HW, y), (-x, HH), (-HW + q, HH - q))


def edge_polyline():
    """板框离散成线段，给布线器写禁布带；圆弧 12 段够 0.325 带宽。"""
    out = []
    def edge(p): out.extend(zip(p, p[1:]))
    def arc(st, en, mid):
        (ax, ay), (bx, by), (cx, cy) = st, mid, en
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
        r = math.hypot(ax - ux, ay - uy); a0 = math.atan2(ay - uy, ax - ux); a1 = math.atan2(cy - uy, cx - ux)
        sw = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        p = [(ux + r * math.cos(a0 + sw * i / 12), uy + r * math.sin(a0 + sw * i / 12)) for i in range(13)]
        out.extend(zip(p, p[1:]))
    board_edge(edge, arc)
    return out
