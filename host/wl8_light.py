"""先行阶段：唯理腕带 IMU → 对准即开关 → bleak 写灯（BLE_POINT_LIGHT_PLAN 3.5 节）。

  python3 wl8_light.py --ref 8.44,-1.16,4.38 --window 10 --addr <灯地址>      # 真跑
  python3 wl8_light.py --ref 8.44,-1.16,4.38 --dry                             # 不连灯，命中只打印（调角度窗）

--ref 来自 wl8_gyro_drift.py analyze 的 aim.ref_acc；--window 来自 pitch_window_deg。
串口铁律：不 reset_input_buffer（wl8.Wl8Rig 已遵守）；跑前确认 Codex 信号灯钩子没占接收器。
"""
import sys, time, json, argparse, asyncio, threading
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import wl8, aim_toggle, ble_light_probe as probe


class Light:
    def __init__(self, addr, dry):
        self.addr, self.dry, self.on, self.loop = addr, dry, False, asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.client = self.proto = None
        if not dry:
            self.client, self.proto = asyncio.run_coroutine_threadsafe(probe.connect(addr), self.loop).result(20)
            print(json.dumps(dict(connected=addr, proto=self.proto)), flush=True)

    def toggle(self, t):
        self.on = not self.on
        if self.dry:
            print(json.dumps(dict(t=round(t, 2), toggle=self.on, dry=True)), flush=True); return
        char, pkt = probe.packet(self.proto, self.on)
        t0 = time.monotonic()
        asyncio.run_coroutine_threadsafe(self.client.write_gatt_char(char, pkt, response=False), self.loop).result(5)
        print(json.dumps(dict(t=round(t, 2), toggle=self.on, write_ms=round((time.monotonic() - t0) * 1000, 1))), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True, help='标定重力向量 x,y,z（analyze 的 aim.ref_acc）')
    ap.add_argument('--window', type=float, default=10.0); ap.add_argument('--hold', type=float, default=0.5)
    ap.add_argument('--cooldown', type=float, default=2.0); ap.add_argument('--addr'); ap.add_argument('--dry', action='store_true')
    ap.add_argument('--port')
    a = ap.parse_args()
    if not a.dry and not a.addr:
        ap.error('--addr 或 --dry 二选一')
    sm = aim_toggle.AimToggle([float(v) for v in a.ref.split(',')], window_deg=a.window, hold_s=a.hold, cooldown_s=a.cooldown)
    light = Light(a.addr, a.dry)
    rig = wl8.Wl8Rig(a.port)
    t0, n = time.monotonic(), [0]

    def on_imu(imu):  # (m,6) int16：前三列陀螺 counts，后三列加速度 counts
        g = np.degrees(imu[:, :3].astype(float) * wl8.GYRO_SCALE)
        acc = imu[:, 3:].astype(float) * wl8.ACC_SCALE
        for gi, ai in zip(g, acc):
            n[0] += 1
            t = t0 + n[0] / 222.0                                        # 用帧计数当时钟，不用主机到达时间（读块是突发的）
            if sm.feed(ai, gi, t):
                light.toggle(t - t0)
    rig.imu_subscribers.append(on_imu)
    rig.open()
    print(json.dumps(dict(rig=rig.banner, window=a.window, hold=a.hold, cooldown=a.cooldown, dry=a.dry)), flush=True)
    try:
        while rig.streaming:
            time.sleep(0.5)
        print(json.dumps(dict(stopped=rig.banner)), flush=True)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
