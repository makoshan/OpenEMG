"""C08B 采集板 总图（P0）：四个子页框 + 页间接口 + 数据/电源流向。
总图是整机框图，不是网表页，不走 finish 的逐脚比对；直接画框、流向箭头、接口网名。"""
from sch import *

def flow(x1, y1, x2, y2, net):
    """带箭头的流向线 + 网名（画在线旁）。"""
    line([(x1, y1), (x2, y2)], WIRE, 1.8)
    if x1 != x2:  # 水平
        d = 1 if x2 > x1 else -1
        svg.append(f'<polygon points="{x2},{y2} {x2-10*d},{y2-5} {x2-10*d},{y2+5}" fill="{SYM}"/>')
        text(net, (x1 + x2) / 2, y1 - 8, size=11, color='#555', anchor='middle')
    else:          # 垂直
        d = 1 if y2 > y1 else -1
        svg.append(f'<polygon points="{x2},{y2} {x2-5},{y2-10*d} {x2+5},{y2-10*d}" fill="{SYM}"/>')
        text(net, x1 + 10, (y1 + y2) / 2, size=11, color='#555', anchor='start')

def ext(label, x, y):
    """外部接口（电极 / 主控板）：虚线框。"""
    svg.append(f'<rect x="{x}" y="{y}" width="150" height="70" fill="none" stroke="{FRAME}" stroke-width="1.4" stroke-dasharray="6 4"/>')
    text(label, x + 75, y + 40, size=14, color='#333', anchor='middle', weight='bold')

# 四个子页框：电极输入 → 采集 → J_AFE；电源在下
block(230, 300, 510, 500, 'P2 电极输入保护', '16 对电极 → ESD → 15k 限流 → 22pF 差分滤波')
block(610, 300, 890, 500, 'P1 双 ADS1298 采集', '16 路差分 → 两颗 ADS1298 共用 SPI、分片选')
block(990, 300, 1270, 500, 'P4 J_AFE 接口', 'FH34SRJ-20S 20 芯 → 主控板')
block(610, 640, 890, 840, 'P3 模拟电源', '3V3（自主控板）→ LM27762 → ±2.5V')

ext('电极 ×16 对', 50, 365)
ext('主控板', 1400, 365)

# 流向
flow(200, 400, 230, 400, '')                       # 电极 → P2
flow(510, 400, 610, 400, '电极信号 IN1±…IN8±')      # P2 → P1
flow(890, 400, 990, 400, 'SPI / DRDY / CS / CLK')   # P1 → P4
flow(1270, 400, 1400, 400, '板对板')                # P4 → 主控板
flow(1130, 500, 1130, 740, '3V3')                   # J_AFE 3V3 ↓ P3（走右侧）
line([(1130, 500), (1130, 560)], WIRE, 1.8); line([(1130, 560), (890, 560)], WIRE, 1.8)
flow(750, 640, 750, 500, '±2.5V')                   # P3 → P1

finish0 = None
# 直接写 SVG（含图框 + 标题栏），不做网表比对
svg.insert(0, f'<rect x="10" y="10" width="{W-20}" height="{H-20}" fill="none" stroke="#333" stroke-width="2"/>')
svg.insert(0, f'<rect width="{W}" height="{H}" fill="#fffdf6"/>')
text('C08B 采集板原理图 · 总图（P0）', 40, 1125, size=22, color='#111', weight='bold')
text('电极 → 输入保护(P2) → 双 ADS1298(P1) → J_AFE(P4) → 主控板；模拟电源(P3) 3V3 → ±2.5V 供 P1。', 40, 1155, size=12, color='#555')
x0, y0 = 1180, 1094
svg.append(f'<rect x="{x0}" y="{y0}" width="470" height="84" fill="none" stroke="#333" stroke-width="1.4"/>')
for yy in (y0 + 28, y0 + 56): line([(x0, yy), (x0 + 470, yy)], '#333', 1)
for vx in (80, 300, 370): line([(x0 + vx, y0), (x0 + vx, y0 + 84)], '#333', 1)
for i, (k, v, k2, v2) in enumerate([('图名', 'C08B 采集板 · 总图', '版本', 'D20（16 路全贴）'), ('图页', '0 / 4', '日期', '2026-11-09'), ('说明', '总图为框图，不含网表', '尺寸', 'A3')]):
    yy = y0 + 19 + 28 * i
    text(k, x0 + 10, yy, size=12, color='#333'); text(v, x0 + 90, yy, size=12, color='#111')
    text(k2, x0 + 310, yy, size=12, color='#333'); text(v2, x0 + 380, yy, size=12, color='#111')
(P / 'page0.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="PingFang SC, Helvetica, sans-serif">' + ''.join(svg) + '</svg>')
print('page0 总图已写 page0.svg')
