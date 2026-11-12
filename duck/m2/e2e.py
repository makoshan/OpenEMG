"""M2 端到端：gesture_sim（--api）→ duck_bridge → netpadd → 仿真鸭。按手势顺序发 /sim，量仿真本体的位移和转角。
前提：duck-sim 无头已起、netpadd 已起、gesture_sim --api 和 duck_bridge 在后台跑。
用法：python3 e2e.py <gesture_sim 地址>
"""
import json, math, socket, sys, time, urllib.request

base = sys.argv[1]
body = socket.create_connection(("127.0.0.1", 7801)).makefile("rw")
body.write(json.dumps({"op": "hello", "protocol": 1, "joints": 15}) + "\n"); body.flush(); body.readline()


def pose():
    body.write('{"op":"read"}\n'); body.flush(); r = json.loads(body.readline())
    w, x, y, z = r["imu"]["quat"]
    g = 1 - 2 * (x * x + y * y)                       # 躯干竖直程度：1 = 直立，0 = 躺平
    return r["trunk"][:2], r["trunk"][2], math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)), g


def press(g):
    urllib.request.urlopen(urllib.request.Request(base + "/sim", data=json.dumps({"gesture": g}).encode(), method="POST"), timeout=2)


def watch(name, g, secs):
    p0, _, prev, _ = pose(); turned, t0, low = 0.0, time.monotonic(), 1.0
    if g: press(g)
    while time.monotonic() - t0 < secs:
        time.sleep(0.05); _, _, yaw, up = pose(); low = min(low, up)
        turned += math.atan2(math.sin(yaw - prev), math.cos(yaw - prev)); prev = yaw
    p1, z, _, up = pose()
    r = {"step": name, "s": secs, "moved_cm": round(math.dist(p0, p1) * 100, 1), "turned_deg": round(math.degrees(turned), 1),
         "trunk_z": round(z, 3), "upright": round(up, 3), "min_upright": round(low, 3)}   # 鞠躬时直立度会掉（前倾 27° ≈ 0.89）
    print(json.dumps(r, ensure_ascii=False), flush=True)
    return r


out = [watch("放松 2 s", None, 2), watch("上滑 → 走 4 s", "up", 4), watch("右滑 → 转（1 s）再观察 2 s", "right", 2),
       watch("左滑 → 转（1 s）再观察 2 s", "left", 2), watch("下滑 → 停，观察 2 s", "down", 2), watch("停住再看 2 s", None, 2),
       watch("唤起 → 鞠躬（B），观察 5 s", "summon", 5), watch("唤起 → 再鞠一躬，观察 5 s", "summon", 5)]
print("RESULT", json.dumps(out, ensure_ascii=False))
