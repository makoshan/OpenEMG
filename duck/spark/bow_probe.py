"""量 ground_pick 槽里那份策略做了什么：站稳 → 按一下 B（bit 1，默认绑 ground_pick）→ 看 7 s。
每 50 ms 从仿真本体（7801）读躯干高度和俯仰，打印一行 RESULT JSON：
最低躯干高度、最大前倾角、结束时高度 / 直立度、有没有摔（直立度 < 0.5）。
鞠躬要的样子：前倾明显、躯干不怎么降（腿不蹲）、最后站回原高度。
"""
import json, math, random, socket, struct, time

DUCK, BODY, B = ("127.0.0.1", 4210), ("127.0.0.1", 7801), 1 << 1
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq = random.getrandbits(32)
body = socket.create_connection(BODY).makefile("rw")
body.write(json.dumps({"op": "hello", "protocol": 1, "joints": 15}) + "\n"); body.flush(); body.readline()


def pose():
    body.write('{"op":"read"}\n'); body.flush(); r = json.loads(body.readline())
    w, x, y, z = r["imu"]["quat"]
    pitch = math.degrees(math.asin(max(-1., min(1., 2 * (w * y - z * x)))))
    j = r["positions"]                                        # 线上 15 关节：髋俯仰 2/12、膝 3/13、脖子 5、头俯仰 6；左右装向相反、符号相反，分开报
    return r["trunk"][2], pitch, 1 - 2 * (x * x + y * y), j[2], j[12], j[3], j[13], j[5], j[6]


def send(frames, buttons=0):
    global seq
    out = []
    for _ in range(frames):
        seq = (seq + 1) % 2**32
        s.sendto(b"DKPD" + struct.pack("<BBII6hH", 1, 0, seq, int(time.monotonic() * 1000) % 2**32, 0, 0, 0, 0, 0, 0, buttons), DUCK)
        time.sleep(1 / 30); out.append(pose())
    return out


send(60)                                   # 站稳 2 s；站立躯干约 0.116，没到 0.105 就判 valid=false
z0, p0, _, *j0 = pose()
trace = send(5, B) + send(205)             # 按 B 约 0.17 s，之后中立看 ~7 s（robotd 在 phase 0.7≈2.8 s 切回 velstand）
zs, ps, ups = (c for c in list(zip(*trace))[:3])
dev = [p - p0 for p in ps]
far = max(dev, key=abs)
peak = trace[dev.index(far)]
# 弯腰 vs 蹲：峰值时各关节离站姿多少弧度。弯腰 = 髋大、膝小；蹲 = 膝大、躯干降
joints = {k: round(peak[3 + i] - j0[i], 2) for i, k in enumerate(("hip_L", "hip_R", "knee_L", "knee_R", "neck_pitch", "head_pitch"))}
r = {"valid": z0 > 0.105, "joints_at_peak_rad": joints, "stand_z": round(z0, 3), "min_z": round(min(zs), 3), "max_pitch_dev_deg": round(far, 1),
     "end_z": round(zs[-1], 3), "end_pitch_dev_deg": round(dev[-1], 1), "end_upright": round(ups[-1], 3),
     "fell": min(ups) < 0.5, "t_peak_s": round(dev.index(far) / 30, 2)}
print("RESULT", json.dumps(r, ensure_ascii=False))
