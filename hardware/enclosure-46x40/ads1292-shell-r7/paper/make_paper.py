"""ADS1292 R7 纸样：A4 两页 PDF，1:1。第 1 页装配视图（盒底、板顶面、两个 3:1 截面），第 2 页能剪下来折的盒子展开图。
先跑 ../model.py 出 host.step，再用 KiCad Python 跑 dump_board.py 出 board.json。
uv run --no-project --python 3.12 --with build123d --with matplotlib python make_paper.py
名义几何，不含公差；触点凸出在纸上做不出来，只画线。"""
import ast, json, math, re
from pathlib import Path
import build123d as b
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

R = Path(__file__).resolve().parent; S = R.parent
F = '/System/Library/Fonts/Hiragino Sans GB.ttc'; fm.fontManager.addfont(F)
plt.rcParams.update({'font.family': fm.FontProperties(fname=F).get_name(), 'axes.unicode_minus': False, 'font.size': 6.5})
src = (S / 'model.py').read_text()
const = lambda name: ast.literal_eval(re.search(rf'^{name} = (.+?)(?:\s+#|$)', src, re.M).group(1))
EL, ED, EX, EH = const('ELECTRODES'), const('ED'), const('EX'), const('EH')   # ED 对方条是 y 向宽，EX 是 x 向长
WMIN, GAP, FLOOR = 155, .1, .5   # 同 model.py 壳底凹槽参数
chk = json.load(open(S / 'checks.json'))['gaps']; LID, TOTAL = chk['盖内面'], chk['盒总厚']
YIN = min(7.5 - ED[n] / 2 for n in ED if EH[n] == max(EH.values()))   # 同 model.py：硬腕先碰 Φ6 平片内侧边
RW = WMIN / 2 / math.pi; WTOP = RW - math.sqrt(RW ** 2 - YIN ** 2) + GAP
BAND = math.sqrt(RW ** 2 - (RW - (WTOP - .6)) ** 2) if WTOP > .6 else 0   # 槽在壳底外表面上的半宽；槽顶低于壳外凸 0.6 时没有槽
brd = json.load(open(R / 'board.json'))
parts = {c.label: c for c in b.import_step(str(S / 'host.step')).children}
bbox = lambda n: parts[n].bounding_box()
T0 = round(min(bbox(f'metal_contact_{n}_ASSUMED').min.Z for n in EL), 3)   # 触点贴肤面高度，从模型量
KIND = '大点 Φ6×2.0、辅点方形 3×3×2 镀金平片'


def pad(ax, n, x, y, grow=0, **kw):
    """触点轮廓：方条画矩形，其余画圆。"""
    if n in EX: ax.add_patch(Rectangle((x - EX[n] / 2 - grow, y - ED[n] / 2 - grow), EX[n] + 2 * grow, ED[n] + 2 * grow, **kw))
    else: ax.add_patch(Circle((x, y), ED[n] / 2 + grow, **kw))
MM = 1 / 25.4


def panel(fig, x, y, xlim, ylim, k=1.0, title=''):
    """在页面 (x, y) mm 处放一个按 k:1 比例的坐标框，坐标单位 mm。"""
    w, h = (xlim[1] - xlim[0]) * k, (ylim[1] - ylim[0]) * k
    ax = fig.add_axes([x / 210, y / 297, w / 210, h / 297]); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off')
    if title: fig.text(x / 210, (y + h + 2) / 297, title, fontsize=8, weight='bold')
    return ax


def outline(ax, mirror=False, **kw):
    s = -1 if mirror else 1
    ax.add_patch(FancyBboxPatch((-23 + .0, -20), 46, 40, boxstyle='round,pad=0,rounding_size=4', fill=False, **kw))


def section(ax, plane_x=None, plane_y=None):
    """用细薄片切 host.step，画出各零件截面。plane_x 给 YZ 截面（横轴 y），plane_y 给 XZ 截面（横轴 x）。"""
    col = {'shell': '#9a9a9a', 'lid': '#c4c4c4', 'board': '#3a9a5a', 'metal_contact': '#d08a00', 'battery_LP': '#6a8fd0', 'battery_tray': '#c9d6ee',
           'xiao': '#444', 'p44e_real': '#2f7a46', 'J1_': '#222', 'J2_': '#222', 'ffc': '#c06020', 'battery_wire': '#d22', 'U1_': '#555', 'U3_': '#555', 'foam': '#e8d27a', 'pcb_screw': '#777'}
    cut = b.Pos(plane_x, 0, 6) * b.Box(.01, 80, 30) if plane_x is not None else b.Pos(0, plane_y, 6) * b.Box(80, .01, 30)
    for n, p in parts.items():
        c = next((v for k_, v in col.items() if n.startswith(k_)), None)
        if not c: continue
        s = p & cut
        if not s: continue
        for f in s.faces():
            nv = f.normal_at()
            if (plane_x is not None and abs(nv.X) < .9) or (plane_y is not None and abs(nv.Y) < .9): continue
            pts = [(v.Y if plane_x is not None else v.X, v.Z) for v in f.outer_wire().positions([i / 160 for i in range(161)])]
            ax.add_patch(Polygon(pts, closed=True, fc=c, ec='none', alpha=.85))
    ax.axhline(T0, color='#888', lw=.3, ls=':'); ax.text(-23, T0 - .5, f'触点面 z {T0}', fontsize=5, va='top', color='#666')


def page1(pdf):
    fig = plt.figure(figsize=(210 * MM, 297 * MM))
    fig.text(12 / 210, 284 / 297, 'ADS1292 两路腕带 R7 纸样 · 第 1 页 装配视图', fontsize=12, weight='bold')
    fig.text(12 / 210, 278 / 297, f'打印选「实际大小 / 100%」，先量下面的 50 mm 比例尺。名义几何，盒 46 × 40 × {TOTAL}（含盖），x 沿前臂、y 绕腕。', fontsize=7)
    # A 盒底（从皮肤这面看，左右镜像）
    ax = panel(fig, 14, 216, (-25, 25), (-22, 22), title='A 盒底 1:1（从皮肤这面看，左右已镜像）')
    ax.add_patch(FancyBboxPatch((-23, -20), 46, 40, boxstyle='round,pad=0,rounding_size=4', fill=False, lw=.8))
    if BAND: ax.add_patch(Rectangle((-23, -BAND), 46, 2 * BAND, fc='#e6e6e6', ec='none'))
    ax.text(0, -20.8, f'灰带 = 壳底凹槽，宽 {2 * BAND:.1f}、中线深 {WTOP - .6:.2f}' if BAND else '壳底平（Φ6 平片下腕到壳已够，凹槽不起作用）', ha='center', va='top', fontsize=5.5, color='#555')
    for n, (x, y) in EL.items():
        pad(ax, n, -x, y, .2, fill=False, lw=.6); pad(ax, n, -x, y, fc='#d08a00')
        ax.text(-x, y - ED[n] / 2 - .5, n, ha='center', va='top', fontsize=6)
    ax.text(-23.5, 0, 'USB\n这边', ha='right', va='center', fontsize=5.5)
    ax.text(0, 20.6, '46（沿前臂） × 40（绕腕）', ha='center', fontsize=5.5)
    # B 板顶面 + 上方零件投影
    ax = panel(fig, 76, 216, (-25, 25), (-22, 22), title='B 盒内俯视 1:1（板顶面 + 上方零件轮廓）')
    ax.add_patch(FancyBboxPatch((-23, -20), 46, 40, boxstyle='round,pad=0,rounding_size=4', fill=False, lw=.5, ls='--', ec='#888'))
    for i, e in enumerate(brd['edge']): ax.add_patch(Polygon(e, closed=True, fill=False, lw=.6, ec='#2a7a40'))
    for p in brd['pads']:
        if p['side'] == 'F':
            for q in p['polys']: ax.add_patch(Polygon(q, closed=True, fc='#c08a20', ec='none'))
    for n, (x, y) in EL.items(): pad(ax, n, x, y, fill=False, lw=.4, ls=':', ec='#d08a00')
    for n, lab, c in (('battery_LP302025_MAX', '电池 302025', '#3a6fd0'), ('p44e_real_size', 'P44e', '#2f7a46'), ('xiao_official', 'XIAO', '#222')):
        bb = bbox(n); ax.add_patch(Rectangle((bb.min.X, bb.min.Y), bb.size.X, bb.size.Y, fill=False, lw=.6, ls='--', ec=c))
        ax.text(bb.min.X + .5, bb.max.Y - 1.6, lab, fontsize=5.5, color=c)
    for r in brd['refs']:
        if r['ref'] in ('U1', 'U3', 'J2', 'Q1', 'L1'): ax.text(r['at'][0], r['at'][1], r['ref'], fontsize=5, ha='center', va='center', color='#000', weight='bold')
    # C、D 截面 3:1
    ax = panel(fig, 12, 150, (-23.5, 23.5), (-1, 12), k=3.8, title='C 横截面 x = 8，过 E2、E5（3.8:1；横轴 y 绕腕，左南右北）')
    section(ax, plane_x=8.0)
    for C, ls in ((155, '-'), (230, ':')):
        r = C / 2 / math.pi; zc = (r - math.sqrt(r * r - YIN ** 2)) - r + T0; ys = [i / 10 for i in range(-200, 201)]
        ax.plot(ys, [zc + math.sqrt(r * r - y * y) for y in ys], 'b' + ls, lw=.5)
    ax.text(16, -.8, '蓝线：腕围 155（实）/ 230（虚）', fontsize=5, color='b')
    ax = panel(fig, 12, 82, (-23.5, 23.5), (-1, 12), k=3.8, title='D 纵截面 y = 0（3.8:1；横轴 x 沿前臂，右侧是 USB）')
    section(ax, plane_y=0.0)
    # 图例和比例尺
    ax = panel(fig, 12, 18, (0, 186), (0, 54))
    leg = [('#9a9a9a', '壳'), ('#c4c4c4', '盖'), ('#3a9a5a', '载板 0.8'), ('#2f7a46', 'P44e 0.8'), ('#444', 'XIAO'), ('#6a8fd0', '电池'), ('#d08a00', '触点 Φ6×2 / 方 3×3×2'),
           ('#c06020', '20P 排线'), ('#d22', '电池线'), ('#e8d27a', '泡棉')]
    for i, (c, t) in enumerate(leg):
        ax.add_patch(Rectangle((i % 5 * 37, 46 - i // 5 * 6, ), 4, 3, fc=c)); ax.text(i % 5 * 37 + 5.5, 47.5 - i // 5 * 6, t, va='center', fontsize=6)
    ax.add_patch(Rectangle((0, 20), 50, 1.2, fc='k')); [ax.plot([v, v], [19, 22.2], 'k', lw=.5) for v in range(0, 51, 10)]
    ax.text(0, 23.5, '比例尺 50 mm（打印后量，不是 50 就别用）', fontsize=6.5)
    ax.add_patch(Rectangle((60, 14), 10, 10, fill=False, lw=.6)); ax.text(72, 19, '10 × 10 mm', fontsize=6, va='center')
    ax.text(0, 8, f'数字来自 model.py / checks.json：盖内面 {LID}、盒总厚 {TOTAL}、腕压在 Φ6 片内侧边、腕到壳 155/190/230 = '
            f"{chk['腕到壳最近']['155']}/{chk['腕到壳最近']['190']}/{chk['腕到壳最近']['230']}。触点：{KIND}。", fontsize=5.5)
    pdf.savefig(fig); plt.close(fig)


def page2(pdf):
    """盒子展开图：外面朝上印。底在中间（从皮肤看，左右镜像，所以 USB 墙在左），四面墙围一圈，盖接在北墙上。"""
    H = round(TOTAL - .6, 2)   # 壳底外表面到盖顶；触点凸出的 0.6 纸上做不出
    fig = plt.figure(figsize=(210 * MM, 297 * MM))
    fig.text(12 / 210, 284 / 297, 'ADS1292 两路腕带 R7 纸样 · 第 2 页 盒子展开图 1:1', fontsize=12, weight='bold')
    fig.text(12 / 210, 278 / 297, f'实线剪、虚线折、灰色是粘贴边。墙高 {H}（不含触点凸出 0.6）。印的一面朝外；圆圈和方框可戳孔，触点位置照 A 图。圆角没画，剪成直角。', fontsize=7)
    ax = panel(fig, 20, 70, (-60, 110), (-80, 90))
    cut = dict(fill=False, lw=.7, ec='k'); fold = dict(lw=.5, ls='--', color='#555'); glue = dict(fc='#ddd', ec='k', lw=.5)
    ax.add_patch(Rectangle((-23, -20), 46, 40, **cut))
    for n, (x, y) in EL.items():
        pad(ax, n, -x, y, fill=False, lw=.6); ax.text(-x, y, n, ha='center', va='center', fontsize=5)
    if BAND: ax.add_patch(Rectangle((-23, -BAND), 46, 2 * BAND, fc='#eee', ec='none', zorder=-1)); ax.text(0, 0, '凹槽带（纸上只做记号）', ha='center', va='center', fontsize=5, color='#777')
    ax.text(0, -17, '底（贴皮肤面）', ha='center', fontsize=7)
    # 南北墙（46 宽）、东西墙（40 宽）
    ax.add_patch(Rectangle((-23, -20 - H), 46, H, **cut)); ax.text(0, -20 - H / 2, '南墙', ha='center', va='center', fontsize=6)
    ax.add_patch(Rectangle((-23, 20), 46, H, **cut)); ax.text(0, 20 + H / 2, '北墙', ha='center', va='center', fontsize=6)
    ax.add_patch(Rectangle((-23 - H, -20), H, 40, **cut)); ax.text(-23 - H / 2, 13, '东墙', ha='center', va='center', fontsize=6, rotation=90)
    ax.add_patch(Rectangle((23, -20), H, 40, **cut)); ax.text(23 + H / 2, 0, '西墙', ha='center', va='center', fontsize=6, rotation=90)
    # USB 开口在东墙：y ±5.3，离壳底外表面 3.9（4.8 − 0.6 − T0）起到墙顶
    z0 = 4.8 - .6 - T0;   # 开口下沿 z 4.8，壳外底在 0.6 + T0
    ax.add_patch(Rectangle((-23 - H, -5.3), H - z0, 10.6, fill=False, lw=.6, ec='r')); ax.text(-23 - H - .5, 0, 'USB 开口（剪掉）', fontsize=5, color='r', rotation=90, ha='right', va='center')
    # 粘贴边：南北墙两端
    for yb in (-20 - H, 20):
        for xs in (-23, 23):
            d = -1 if xs < 0 else 1
            ax.add_patch(Polygon([(xs, yb), (xs + d * 5, yb + 1), (xs + d * 5, yb + H - 1), (xs, yb + H)], closed=True, **glue))
    # 盖接在北墙上沿：绕北墙两道折线共翻 180°，图上的左边折好后正好在东边（USB），和底、东墙同侧
    ax.add_patch(Rectangle((-23, 20 + H), 46, 40, **cut)); ax.text(0, 20 + H + 20, '盖（外面）', ha='center', va='center', fontsize=7)
    ax.text(-21.5, 20 + H + 20, 'USB 一侧', rotation=90, ha='left', va='center', fontsize=6, color='r')
    for xs in (-23, 23):
        d = -1 if xs < 0 else 1
        ax.add_patch(Polygon([(xs, 20 + H + 2), (xs + d * 6, 20 + H + 5), (xs + d * 6, 20 + H + 35), (xs, 20 + H + 38)], closed=True, **glue))
    ax.add_patch(Polygon([(-21, 60 + H), (-18, 66 + H), (18, 66 + H), (21, 60 + H)], closed=True, **glue)); ax.text(0, 63 + H, '插进南墙内侧', ha='center', va='center', fontsize=5)
    for seg in (((-23, -20), (23, -20)), ((-23, 20), (23, 20)), ((-23, -20), (-23, 20)), ((23, -20), (23, 20)), ((-23, 20 + H), (23, 20 + H))):
        ax.plot(*zip(*seg), **fold)
    # 腕带示意：25 宽两段，贴在盒底南北两头（腕带绕腕走 y 方向）
    ax.add_patch(Rectangle((40, -75), 25, 120, fill=False, lw=.6)); ax.text(52.5, -15, '纸腕带 25 × 120\n（剪下贴在\n底的南北两头，\n绕腕后用胶带接）', ha='center', va='center', fontsize=5.5)
    ax.add_patch(Rectangle((75, -75), 25, 120, fill=False, lw=.6))
    ax.add_patch(Rectangle((-58, 84), 50, 1, fc='k')); ax.text(-58, 86.5, '50 mm 比例尺', fontsize=6)
    pdf.savefig(fig); plt.close(fig)


with PdfPages(R / 'ADS1292-R7-纸样-20261111.pdf') as pdf:
    page1(pdf); page2(pdf)
print('出图', R / 'ADS1292-R7-纸样-20261111.pdf')
