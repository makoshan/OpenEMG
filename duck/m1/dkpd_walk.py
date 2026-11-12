"""M1：按官方 DKPD 格式给 netpadd 发包，量仿真鸭走了多远。

用法：python3 dkpd_walk.py [--start]   （--start 额外测按一下 Start 的效果）
位置取自仿真本体（duck-body 的 TCP 7801，trunk 坐标），不是 robotd 的里程计。
"""
import json, math, random, socket, struct, sys, time

DUCK, BODY = ("127.0.0.1", 4210), ("127.0.0.1", 7801)
START = 1 << 6

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setblocking(False)
seq = random.getrandbits(32)  # 随机起点：重启的发送端不会被当成旧包
last = None                   # 最近一次 DKST 回包 (verdict, accepted, stale, malformed)

body = socket.create_connection(BODY).makefile("rw")
body.write(json.dumps({"op": "hello", "protocol": 1, "joints": 15}) + "\n"); body.flush(); body.readline()


def pose():
    body.write('{"op":"read"}\n'); body.flush(); r = json.loads(body.readline())
    w, x, y, z = r["imu"]["quat"]
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return r["trunk"][:2], r["trunk"][2], yaw


def pkt(seq, ly=0, rx=0, buttons=0):
    t_ms = int(time.monotonic() * 1000) % 2**32
    return b"DKPD" + struct.pack("<BBII6hH", 1, 0, seq, t_ms, 0, ly, rx, 0, 0, 0, buttons)


def drain():
    global last
    while True:
        try:
            d = s.recv(64)
        except BlockingIOError:
            return
        if d[:4] == b"DKST":
            _, verdict, _, acc, stale, bad = struct.unpack_from("<BBIIII", d, 4)
            last = (verdict, acc, stale, bad)


def hold(frames, ly=0, rx=0, buttons=0):
    """同一个状态每 1/30 s 发一次，同时累计转过的角度。"""
    global seq
    turned, prev = 0.0, pose()[2]
    for _ in range(frames):
        seq = (seq + 1) % 2**32
        s.sendto(pkt(seq, ly, rx, buttons), DUCK)
        time.sleep(1 / 30)
        drain()
        yaw = pose()[2]
        turned += math.atan2(math.sin(yaw - prev), math.cos(yaw - prev)); prev = yaw
    return turned


def leg(name, frames, **kw):
    (p0, _, _) = pose()
    t0, acc0 = time.monotonic(), (last[1] if last else 0)
    turned = hold(frames, **kw)
    (p1, z, _) = pose()
    dt = time.monotonic() - t0
    d = math.dist(p0, p1)
    r = {"leg": name, "s": round(dt, 2), "moved_cm": round(d * 100, 1), "mps": round(d / dt, 3),
         "deg_per_s": round(math.degrees(turned) / dt, 1), "trunk_z": round(z, 3),
         "dkst": {"verdict": last[0], "accepted_delta": last[1] - acc0, "stale": last[2],
                  "malformed": last[3]} if last else None}
    print(json.dumps(r, ensure_ascii=False))
    return r


out = [leg("中立", 10), leg("前进 ly=+1，3 s", 90, ly=32767), leg("中立", 15),
       leg("右转 rx=+1，3 s", 90, rx=32767)]
# 断流：什么都不发。stale_ms=300 后应停，timeout_ms=1000 后应坐下。
p0, _, _ = pose(); time.sleep(0.5); p1, z05, _ = pose(); time.sleep(1.5); p2, z2, _ = pose()
silence = {"leg": "断流 2 s", "moved_after_0.5s_cm": round(math.dist(p1, p2) * 100, 1),
           "trunk_z_0.5s": round(z05, 3), "trunk_z_2s": round(z2, 3)}
print(json.dumps(silence, ensure_ascii=False)); out.append(silence)

if "--start" in sys.argv:
    out.append(leg("中立重连", 30))
    out.append(leg("按 Start", 5, buttons=START))
    out.append(leg("松开等 3 s", 90))

print("RESULT", json.dumps(out, ensure_ascii=False))
