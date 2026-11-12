"""截面图：x = 8（过 E2、E5 壳底与腕型）和 x = 11.26（过 P44e 槽口与电池线 0 北出夹层），叠 155/190/230 腕围圆腕。先跑 model.py 出 host.step。
uv run --no-project --python 3.12 --with build123d --with matplotlib python section.py ."""
import math, build123d as b, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont('/System/Library/Fonts/Hiragino Sans GB.ttc'); plt.rcParams['axes.unicode_minus'] = False; plt.rcParams['font.family'] = fm.FontProperties(fname='/System/Library/Fonts/Hiragino Sans GB.ttc').get_name()
parts = {c.label: c for c in b.import_step('host.step').children}
fig, axs = plt.subplots(2, 1, figsize=(12, 7.5))
for ax, X, yhi in zip(axs, (8.0, 11.26), (3.4, 7.2)):
    for n, col in (('shell', '#888'), ('lid', '#bbb'), ('board_ADS1292_REAL_OUTLINE', '#2a7'), ('p44e_real_size', '#1f5a33'), ('metal_contact_E2_ASSUMED', '#c80'), ('metal_contact_E5_ASSUMED', '#c80'), ('battery_wire_0', '#d22')):
        if n not in parts: continue
        sec = parts[n] & (b.Pos(X, 0, 5) * b.Box(.01, 60, 30))
        if not sec: continue
        for f in [f for f in sec.faces() if abs(f.normal_at().X) > .9 and f.center().X > X]:
            for w in [f.outer_wire()]:
                pts = [(v.X, v.Y, v.Z) for v in w.positions([i / 200 for i in range(201)])]
                ax.fill([p[1] for p in pts], [p[2] for p in pts], color=col, alpha=.7, lw=0)
    for C, ls in ((155, '-'), (190, '--'), (230, ':')):
        r = C / 2 / math.pi; zc = (r - math.sqrt(r * r - 4.5 ** 2)) - r + .3   # 同 model.py：腕压在 Φ6 片内侧边 y = 4.5，触点平面 T0 = 0.3
        ys = [i / 10 for i in range(-200, 201)]
        ax.plot(ys, [zc + math.sqrt(r * r - y * y) for y in ys], 'b' + ls, lw=1, label=f'腕围 {C}')
    ax.set_xlim(-21, 21); ax.set_ylim(-1.8, yhi); ax.set_aspect('equal'); ax.grid(lw=.3); ax.legend(loc='upper right', fontsize=8)
    ax.set_title(f'x = {X} 截面（灰：壳/盖，绿：载板/P44e，橙：触点，红：电池线，蓝：腕）', fontsize=10)
fig.tight_layout(); fig.savefig(f'{__import__("sys").argv[1]}/section.png', dpi=110)
