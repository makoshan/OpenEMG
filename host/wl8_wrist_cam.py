"""摄像头给手腕角当「答案」（照 Meta 2025 Nature 的思路：采集时用相机测腕角，使用时只靠手环）。
前臂横放在笔记本前（画面里左右走向）、掌心朝下、前臂搁稳不动；手腕上下弯时，手在画面里上下摆。
腕角 = 手腕点(0) → 中指根(9) 连线相对画面水平线的仰角（度，向上为正）。只存角度和时间戳，不存任何画面。

    .venv-wrist/bin/python wl8_wrist_cam.py --check          # 合成关键点自检，不开摄像头
    .venv-wrist/bin/python wl8_wrist_cam.py --test 10        # 开摄像头 10 秒，出一张角度曲线图
    .venv-wrist/bin/python wl8_wrist_cam.py --video 手腕.MP4 --out wrist-take1   # 大疆 Action 8 等录好的视频，事后处理
    .venv-wrist/bin/python wl8_wrist_cam.py --preview --camera 1             # 实时预览摆位置：画关键点、显示认没认到手，按 q 退出（不保存画面）

事后处理的约定：相机架在前臂侧面；录像开始后先静止 2 秒，再**快速甩一下手腕**当同步标记，之后再做正式动作。
脚本会把这一下（角速度最大处）的视频时刻打印出来；肌电那边同一下在陀螺仪里也是一个尖峰，两边对齐就靠它。

依赖在 .venv-wrist（mediapipe 0.10.21；1.0.1 的新接口在本机强制用 Metal 会崩，所以用老接口 mp.solutions.hands）。
"""
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path


def wrist_angle(lm, w, h):
    """lm: 21 个归一化关键点 [(x, y), ...]；返回仰角（度）。画面 y 向下，所以取负；手朝左朝右都一样。"""
    dx = (lm[9][0] - lm[0][0]) * w; dy = (lm[9][1] - lm[0][1]) * h
    return math.degrees(math.atan2(-dy, abs(dx)))


def capture(seconds, camera=0, say=True):
    """开摄像头，返回 [(t 秒, 角度或 None)]。画面只在内存里算完就丢。"""
    import cv2
    import mediapipe as mp
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened(): sys.exit('摄像头打不开：系统设置 → 隐私与安全性 → 摄像头，给运行本脚本的终端 / App 打开权限')
    rows = []
    with mp.solutions.hands.Hands(max_num_hands=1, model_complexity=1, min_detection_confidence=.5, min_tracking_confidence=.5) as hands:
        for _ in range(10): cap.read()                       # 前几帧曝光还没稳
        if say: subprocess.Popen(['say', '-v', 'Tingting', '开始，手腕上下弯'])
        t0 = time.time()
        while time.time() - t0 < seconds:
            ok, frame = cap.read()
            if not ok: continue
            t = time.time() - t0; hh, ww = frame.shape[:2]
            r = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            lm = r.multi_hand_landmarks[0].landmark if r.multi_hand_landmarks else None
            rows.append((t, wrist_angle([(p.x, p.y) for p in lm], ww, hh) if lm else None))
    cap.release()
    if say: subprocess.Popen(['say', '-v', 'Tingting', '好了'])
    return rows


def read_video(path, rotate=0, every=1):
    """逐帧算腕角，时间用视频自己的时间戳（秒）。rotate: 0/90/180/270 顺时针转画面（相机竖着架时用）；every: 每几帧算一帧。"""
    import cv2
    import mediapipe as mp
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened(): sys.exit(f'打不开视频：{path}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); rows = []; i = 0
    rot = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}.get(rotate)
    with mp.solutions.hands.Hands(max_num_hands=1, model_complexity=1, min_detection_confidence=.5, min_tracking_confidence=.5) as hands:
        while True:
            ok, frame = cap.read()
            if not ok: break
            if i % every == 0:
                if rot is not None: frame = cv2.rotate(frame, rot)
                hh, ww = frame.shape[:2]
                r = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                lm = r.multi_hand_landmarks[0].landmark if r.multi_hand_landmarks else None
                rows.append((i / fps, wrist_angle([(p.x, p.y) for p in lm], ww, hh) if lm else None))
                if len(rows) % 300 == 0: print(f'  {len(rows)} 帧 / 约 {n // every}', flush=True)
            i += 1
    cap.release()
    return rows


def flick(rows, after=1.0):
    """同步标记：after 秒之后角速度（度/秒）最大的那一刻。返回 (时刻, 角速度)；没有相邻两帧都检测到手就返回 None。"""
    best = None
    for (t0, a0), (t1, a1) in zip(rows, rows[1:]):
        if a0 is None or a1 is None or t0 < after or t1 <= t0: continue
        v = abs(a1 - a0) / (t1 - t0)
        if best is None or v > best[1]: best = (t1, v)
    return best


def preview(camera=0, rotate=0):
    """摆相机位置用：窗口里画手部关键点，左上角显示「认到手 / 没认到」、腕角和最近 3 秒认出率。按 q 或 Esc 退出；
    按 n 换下一个摄像头（OpenCV 的编号和系统列表不一定对得上，2026-10-03 实测 1 号不是 Action），画面上显示当前编号。只显示，不保存。"""
    import cv2
    import mediapipe as mp
    def open_cam(i):
        c = cv2.VideoCapture(i)
        return c if c.isOpened() else None
    cap = open_cam(camera)
    if cap is None: sys.exit('摄像头打不开：系统设置 → 隐私与安全性 → 摄像头，给运行本脚本的终端打开权限')
    rot = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}.get(rotate)
    draw, hands_mod, recent = mp.solutions.drawing_utils, mp.solutions.hands, []
    with hands_mod.Hands(max_num_hands=1, model_complexity=1, min_detection_confidence=.5, min_tracking_confidence=.5) as hands:
        while True:
            ok, frame = cap.read()
            if not ok: continue
            if rot is not None: frame = cv2.rotate(frame, rot)
            hh, ww = frame.shape[:2]
            r = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            got = bool(r.multi_hand_landmarks); recent = (recent + [got])[-90:]
            if got:
                lm = r.multi_hand_landmarks[0]; draw.draw_landmarks(frame, lm, hands_mod.HAND_CONNECTIONS)
                a = wrist_angle([(p.x, p.y) for p in lm.landmark], ww, hh)
                p0, p9 = lm.landmark[0], lm.landmark[9]
                cv2.line(frame, (int(p0.x * ww), int(p0.y * hh)), (int(p9.x * ww), int(p9.y * hh)), (0, 165, 255), 4)
                text = f'HAND OK  angle {a:+.0f} deg'
            else: text = 'NO HAND'
            rate = sum(recent) / len(recent)
            cv2.rectangle(frame, (0, 0), (ww, 70), (0, 0, 0), -1)
            cv2.putText(frame, f'CAM {camera} {ww}x{hh}  {text}  seen {rate:.0%}  n = next cam  q = quit', (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0) if got else (0, 0, 255), 3)
            cv2.imshow('wrist preview', cv2.resize(frame, (min(ww, 1280), int(hh * min(ww, 1280) / ww))))
            k = cv2.waitKey(1) & 0xFF
            if k in (ord('q'), 27): break
            if k == ord('n'):                                        # 换下一个能打开的摄像头
                cap.release()
                for step in range(1, 5):
                    nxt = open_cam((camera + step) % 5)
                    if nxt is not None: camera, cap, recent = (camera + step) % 5, nxt, []; break
                print(f'换到 {camera} 号摄像头', flush=True)
    cap.release(); cv2.destroyAllWindows()
    print(f'退出时用的是 {camera} 号摄像头', flush=True)


def summarize(rows):
    ang = [a for _, a in rows if a is not None]
    fps = len(rows) / rows[-1][0] if rows and rows[-1][0] else 0
    return {'frames': len(rows), 'fps': round(fps, 1), 'detected': round(len(ang) / max(1, len(rows)), 3),
            'min_deg': round(min(ang), 1) if ang else None, 'max_deg': round(max(ang), 1) if ang else None}


def plot(rows, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.fontManager.addfont('/System/Library/Fonts/Hiragino Sans GB.ttc')
    plt.rcParams['font.family'] = ['Hiragino Sans GB', 'DejaVu Sans']; plt.rcParams['axes.unicode_minus'] = False
    s = summarize(rows); fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot([t for t, a in rows], [a if a is not None else float('nan') for t, a in rows], lw=1.6, color='#2563EB')
    for t, a in rows:
        if a is None: ax.axvline(t, color='#EF4444', alpha=.25, lw=2)
    f = flick(rows)
    if f: ax.axvline(f[0], color='#F59E0B', lw=2, ls='--'); ax.text(f[0], ax.get_ylim()[1] if ax.get_ylim()[1] else 1, ' 同步标记', color='#B45309', fontsize=9, va='top')
    ax.axhline(0, color='#888', lw=.8); ax.set_xlabel('秒'); ax.set_ylabel('腕角（度，向上为正）')
    ax.set_title(f"摄像头测腕角：{s['fps']} 帧/秒，检测到手 {s['detected']:.0%}，范围 {s['min_deg']}° ～ {s['max_deg']}°（红竖线 = 没检测到手）", fontsize=11)
    fig.tight_layout(); fig.savefig(out, dpi=110)


def check():
    lm = [(0., 0.)] * 21
    def hand(x0, y0, x9, y9): p = list(lm); p[0], p[9] = (x0, y0), (x9, y9); return p
    assert abs(wrist_angle(hand(.5, .5, .7, .5), 640, 480)) < 1e-9                       # 水平 = 0°
    assert abs(wrist_angle(hand(.5, .5, .5 + 100 / 640, .5 - 100 / 480), 640, 480) - 45) < 1e-6   # 往上 45°（y 向下，所以 y 变小）
    assert abs(wrist_angle(hand(.5, .5, .5 - 100 / 640, .5 - 100 / 480), 640, 480) - 45) < 1e-6   # 手朝左也是 +45°
    assert wrist_angle(hand(.5, .5, .7, .6), 640, 480) < 0                                # 往下为负
    assert abs(wrist_angle(hand(.5, .5, .5 + 100 / 640, .5 - 100 / 480), 1280, 720) - wrist_angle(hand(.5, .5, .5 + 100 / 1280, .5 - 100 / 720), 1280, 720)) > 1, '角度必须按像素算，不能按归一化坐标（否则宽高比会带偏）'
    s = summarize([(0., 1.), (.5, None), (1., -3.)]); assert s == {'frames': 3, 'fps': 3.0, 'detected': .667, 'min_deg': -3.0, 'max_deg': 1.0}, s
    # 同步标记：2.0 s 处 1 帧甩 30°，比之后的慢弯快；开头 1 s 内的大动作不算；缺帧不崩
    rows = [(i / 30, 0.) for i in range(30)] + [(1.0, 25.), (1.033, 0.)] + [(1.5 + i / 30, 0.) for i in range(15)] + [(2.0, 30.)] + [(2.0 + i / 30, 30. - i) for i in range(1, 20)]
    f = flick(rows); assert f and abs(f[0] - 2.0) < 1e-9 and f[1] > 800, f
    assert flick([(0., 1.), (.1, None), (.2, 5.)]) is None
    # 视频读取：写一段 1 秒 30 帧的空白视频，时间戳按帧序号 / fps，没手时角度为 None；every=3 只算 10 帧
    import tempfile, numpy as np, cv2
    with tempfile.TemporaryDirectory() as d:
        vp = Path(d) / 'blank.mp4'; w = cv2.VideoWriter(str(vp), cv2.VideoWriter_fourcc(*'mp4v'), 30, (320, 240))
        for _ in range(30): w.write(np.zeros((240, 320, 3), np.uint8))
        w.release()
        rows = read_video(vp, every=3)
        assert len(rows) == 10 and abs(rows[-1][0] - 27 / 30) < 1e-6 and all(a is None for _, a in rows), (len(rows), rows[-1])
    print('wl8_wrist_cam check passed: 水平 0°、向上为正、左右手朝向一致、向下为负、按像素算宽高比、汇总统计、同步标记（跳过开头 / 缺帧）、视频按帧时间戳读')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true'); ap.add_argument('--test', type=float, metavar='秒')
    ap.add_argument('--camera', type=int, default=0); ap.add_argument('--out', default='wrist-cam-test')
    ap.add_argument('--video', help='录好的视频文件（大疆 Action 8 等），事后处理'); ap.add_argument('--rotate', type=int, default=0, choices=(0, 90, 180, 270))
    ap.add_argument('--every', type=int, default=1, help='每几帧算一帧（60 帧视频可以给 2）')
    ap.add_argument('--preview', action='store_true', help='实时预览摆位置（不保存画面）')
    a = ap.parse_args()
    if a.check: check(); sys.exit()
    if a.preview: preview(a.camera, a.rotate); sys.exit()
    if a.video:
        rows = read_video(a.video, a.rotate, a.every); s = summarize(rows); f = flick(rows)
        print(json.dumps(s, ensure_ascii=False)); print('同步标记（甩腕）：', f'视频 {f[0]:.3f} s，{f[1]:.0f} 度/秒' if f else '没找到')
        Path(a.out + '.json').write_text(json.dumps({'source': str(a.video), 'rotate': a.rotate, 'every': a.every, 'flick': f, 'rows': rows}))
        plot(rows, a.out + '.png'); print('图：', a.out + '.png'); sys.exit()
    if a.test:
        rows = capture(a.test, a.camera); print(json.dumps(summarize(rows), ensure_ascii=False))
        Path(a.out + '.json').write_text(json.dumps(rows)); plot(rows, a.out + '.png'); print('图：', a.out + '.png')
