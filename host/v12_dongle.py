"""经 XIAO 接收器（v12/ble-dongle-20261021/xiao-central，dongle_r01 档）采 F05 蓝牙数据。

Mac 直连时连接间隔固定 30 ms，R01 2 kHz 丢 3.5–13%；接收器当中心定 7.5 ms。
这里把接收器的 USB 串口包装成 v12_ble.capture 用到的那几个 Bleak 客户端接口，校验、解码、缺失统计全部复用 v12_ble。

串口帧（见接收器 main.cpp 头注释）：设备→电脑 A5|kind|len u16|t_us u32|payload；电脑→设备 A5|op|len u16|payload。
用法：python host/v12_dongle.py --port /dev/cu.usbmodemXXX --mode test --seconds 60 --expected <build_id> --out <新目录>
只许离体或过了安全门；不接人体由使用者负责（见 firmware-f05-ble-dout/README）。
"""
from pathlib import Path
import argparse, asyncio, json, struct, sys, threading, time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v12_ble  # noqa: E402

IMU_DATA = getattr(v12_ble, 'IMU_DATA', '7b24c101-3948-4f03-9d11-12bb9d000006')
READ_INDEX = {v12_ble.META: 3, v12_ble.STATUS: 4}


class Parser:
    """按 A5 帧头切帧；长度不对就丢一个字节重找，不猜内容。"""
    def __init__(self):
        self.buf = bytearray()
        self.junk = 0

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(0xA5)
            if i < 0:
                self.junk += len(self.buf); self.buf.clear(); return out
            if i:
                self.junk += i; del self.buf[:i]
            if len(self.buf) < 8:
                return out
            n = self.buf[2] | self.buf[3] << 8
            if n > 600:  # 接收器最长帧 8+247；超长就是错位
                self.junk += 1; del self.buf[:1]; continue
            if len(self.buf) < 8 + n:
                return out
            out.append((self.buf[1], struct.unpack_from('<I', self.buf, 4)[0], bytes(self.buf[8:8 + n])))
            del self.buf[:8 + n]


class _Char:
    def __init__(self, uuid):
        self.uuid = uuid


class _Service:
    characteristics = [_Char(u) for u in (v12_ble.DATA, v12_ble.META, v12_ble.STATUS, v12_ble.CONTROL, IMU_DATA)]


class _Services:
    def get_service(self, uuid):
        return _Service() if str(uuid).lower() == v12_ble.SERVICE else None


class DongleClient:
    """实现 v12_ble.capture 与 c08b_stream.capture_c08b 共用的 Bleak 客户端子集（含 DATA + IMU_DATA 双流通知）。"""
    def __init__(self, ser):
        self.ser, self.services, self.parser = ser, _Services(), Parser()
        self.loop = asyncio.get_running_loop()
        self.waiting = {}          # op -> Future（同一时刻每种命令只发一条）
        self._notifies = {}        # uuid(lower) -> callback
        self.ready, self.mtu_size, self.link, self.start_connects = False, 23, None, None
        self.link_history = []
        self._stop = False
        threading.Thread(target=self._reader, daemon=True).start()

    @property
    def notify(self):
        return self._notifies.get(v12_ble.DATA)

    @notify.setter
    def notify(self, callback):
        if callback is None:
            self._notifies.pop(v12_ble.DATA, None)
        else:
            self._notifies[v12_ble.DATA] = callback

    def _reader(self):
        while not self._stop:
            try:
                data = self.ser.read(4096)
            except Exception:  # 收尾时串口先关，读线程会撞到；采集结果已在主线程里
                return
            if data:
                for kind, t, p in self.parser.feed(data):
                    self.loop.call_soon_threadsafe(self._dispatch, kind, t, p)

    def _dispatch(self, kind, t, p):
        if kind == 2:
            cb = self._notifies.get(v12_ble.DATA)
            if cb:
                cb(v12_ble.DATA, bytearray(p))
        elif kind == 6:
            cb = self._notifies.get(IMU_DATA)
            if cb:
                cb(IMU_DATA, bytearray(p))
        elif kind == 0x11 and len(p) >= 26:
            ci, phy, mtu, dl = struct.unpack_from('<HBHH', p, 1)
            self.ready, self.mtu_size = bool(p[0]), (mtu if 23 <= mtu <= 517 else 23)
            drops, notes, peak, conns = struct.unpack_from('<IIII', p, 10)
            self.link = dict(ready=self.ready, ci_1p25ms=ci, phy=phy, mtu=mtu, dle=dl,
                             dongle_ring_drops=drops, dongle_notifies=notes, dongle_ring_peak=peak, connects=conns)
            self.link_history.append(dict(host_ns=time.monotonic_ns(), dongle_us=t, **self.link))
        elif kind & 0x80:
            f = self.waiting.pop(kind & 0x7F, None)
            if f and not f.done():
                f.set_result(p)

    async def _cmd(self, op, payload=b'', timeout=3):
        f = self.loop.create_future()
        self.waiting[op] = f
        self.ser.write(bytes([0xA5, op]) + struct.pack('<H', len(payload)) + payload)
        try:
            p = await asyncio.wait_for(f, timeout)  # 端口选错或接收器没回应时不挂死
        finally:
            if self.waiting.get(op) is f:
                del self.waiting[op]  # 超时后清掉，迟到的应答不会被下一条同类命令领走
        if not p or p[0] != 0:
            raise RuntimeError(f'接收器命令 {chr(op)} 失败')
        return p[1:]

    @property
    def is_connected(self):
        # 链路帧每秒一次；connects 变了说明中途断开又重连，按断连处理，不把两条连接的数据拼进同一次采集
        return self.ready and (self.start_connects is None or (self.link or {}).get('connects') == self.start_connects)

    async def read_gatt_char(self, uuid):
        u = str(uuid).lower()
        res = bytearray(await self._cmd(ord('R'), bytes([READ_INDEX[u]])))
        if u == v12_ble.STATUS and len(res) not in (48, 64, 136, 163):
            # R01 在 ads.start() 6s 结束瞬间将 ATT MTU 从 23 升到 247；若正撞上 C6 按 MTU=23 分片长读（每片 22B），
            # NimBLE 看到 22 < 246 会提前以 BLE_HS_EDONE 截断返回（2026-10-25 实测）。立即按新 MTU 重读一次。
            res = bytearray(await self._cmd(ord('R'), bytes([READ_INDEX[u]])))
        return res

    async def write_gatt_char(self, uuid, data, response=True):
        if str(uuid).lower() != v12_ble.CONTROL:
            raise ValueError('接收器只转发控制特征写入')
        await self._cmd(ord('W'), bytes(data))

    async def start_notify(self, uuid, callback):
        u = str(uuid).lower()
        if u not in (v12_ble.DATA, IMU_DATA):
            raise ValueError('接收器只转发 DATA 与 IMU_DATA 特征通知')
        self._notifies[u] = callback

    async def stop_notify(self, uuid):
        self._notifies.pop(str(uuid).lower(), None)

    def close(self):
        self._stop = True


def hard_reset_dongle(ser, port, sleep=time.sleep):
    """ESP32-C6 USB-Serial-JTAG 硬复位（脉冲 EN，同 esptool HardReset uses_usb=True）：接收器卡死不应答时自动恢复。"""
    try:
        ser.dtr = False
        ser.rts = True
        ser.dtr = False
        sleep(0.2)
        ser.rts = False
        ser.dtr = False
    except OSError:
        pass
    try:
        ser.close()
    except OSError:
        pass
    sleep(0.5)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not Path(port).exists():
        sleep(0.05)


async def open_ready_dongle(port, open_ser, reset_fn=hard_reset_dongle, cmd_timeout=3):
    """打开接收器串口并用 Q 探活；若 C6 卡死超时（2026-10-25 实测），自动硬复位重开串口再验一次。"""
    ser = open_ser(port)
    ser.dtr = True
    client = DongleClient(ser)
    try:
        await client._cmd(ord('Q'), timeout=cmd_timeout)
        return ser, client
    except TimeoutError:
        client.close()
        reset_fn(ser, port)
        ser = open_ser(port)
        ser.dtr = True
        client = DongleClient(ser)
        try:
            await client._cmd(ord('Q'), timeout=cmd_timeout)
            return ser, client
        except Exception as err:
            client.close()
            try:
                ser.close()
            except OSError:
                pass
            raise RuntimeError(f'接收器 {port} 无应答，自动硬复位后仍未恢复（硬复位只对 C6 有效；nRF52840 接收器请拔插 USB）') from err


async def run(a):
    import serial  # 只在真采时需要
    # 每次采集用一条新连接：F05 在同一连接上的第二次采集会发“重新配置”边界，新主机会话拒收；也防止两次连接的数据拼接
    ser, client = await open_ready_dongle(a.port, lambda p: serial.Serial(p, 115200, timeout=0.05))
    try:
        await asyncio.sleep(0.2)
        before = (client.link or {}).get('connects', 0)
        await client._cmd(ord('D'))
        for _ in range(150):  # 最多等 15 s 重新连上
            await client._cmd(ord('Q'))
            await asyncio.sleep(0.1)
            if client.ready and (client.link or {}).get('connects', 0) > before:
                break
        if not (client.ready and (client.link or {}).get('connects', 0) > before):
            raise SystemExit('接收器 15 秒内没重新连上 R01（看 R01 是否在广播、有没有被别的电脑连着）')
        client.start_connects = client.link['connects']
        print('接收器链路', json.dumps(client.link, ensure_ascii=False), flush=True)
        try:
            result = await v12_ble.capture(client, Path(a.out), a.seconds, a.mode, True, a.expected,
                                           on_first_data=getattr(a, 'on_first_data', None))
            result.update(transport='xiao_dongle')
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            query_error = None
            try:
                await client._cmd(ord('Q')); await asyncio.sleep(0.2)
            except Exception as error:
                query_error = str(error)
            if Path(a.out).is_dir():
                evidence = dict(link=client.link, history=client.link_history,
                                junk_bytes=client.parser.junk, final_query_error=query_error)
                (Path(a.out) / 'dongle.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    finally:
        client.close()
        try:
            ser.close()
        except OSError:
            pass



def selftest():
    """切帧、MTU 切换时 STATUS 长读截断重读、C6 卡死自动硬复位恢复。"""
    frame = lambda k, p: bytes([0xA5, k]) + struct.pack('<HI', len(p), 7) + p
    data = b'xx' + frame(2, b'abc') + frame(0x11, bytes(26)) + bytes([0xA5, 2, 0xFF, 0x0F]) + frame(0x80 | ord('R'), b'\x00ok')
    for step in (1, 3, len(data)):
        ps, out = Parser(), []
        for i in range(0, len(data), step):
            out += ps.feed(data[i:i + step])
        assert [(k, p) for k, _, p in out] == [(2, b'abc'), (0x11, bytes(26)), (0x80 | ord('R'), b'\x00ok')], out
        assert ps.junk >= 2

    class FakeSer:
        def __init__(self, replies):
            self.replies = list(replies)
            self.rx = bytearray()
            self.writes = []
            self.dtr = False
            self.rts = False
            self.closed = False
        def write(self, b):
            self.writes.append(bytes(b))
            if self.replies:
                r = self.replies.pop(0)
                if r is not None:
                    self.rx += r
        def read(self, n):
            if self.closed:
                raise OSError('closed')
            if not self.rx:
                time.sleep(0.002)
                return b''
            out = bytes(self.rx[:n]); del self.rx[:n]
            return out
        def close(self):
            self.closed = True

    async def check_async():
        # 1) MTU 23->247 切换瞬间 STATUS 长读第一次被 NimBLE 截断为 22B，自动重读第二次拿到 136B
        s1 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(22)), frame(0x80 | ord('R'), b'\x00' + bytes(136))])
        c1 = DongleClient(s1)
        try:
            got = await c1.read_gatt_char(v12_ble.STATUS)
            assert len(got) == 136 and len(s1.writes) == 2, (len(got), len(s1.writes))
        finally:
            c1.close()

        # 1b) 状态 v3（R01 dual，163B）是完整长度：一次读到就不重读；截断后重读也认 163B
        s3 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(163))])
        c3 = DongleClient(s3)
        try:
            got3 = await c3.read_gatt_char(v12_ble.STATUS)
            assert len(got3) == 163 and len(s3.writes) == 1, (len(got3), len(s3.writes))
        finally:
            c3.close()
        s4 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(22)), frame(0x80 | ord('R'), b'\x00' + bytes(163))])
        c4 = DongleClient(s4)
        try:
            got4 = await c4.read_gatt_char(v12_ble.STATUS)
            assert len(got4) == 163 and len(s4.writes) == 2, (len(got4), len(s4.writes))
        finally:
            c4.close()

        # 2) 若重读后仍为截断长度（如 22B），不死循环，原样返回交由上层报错
        s2 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(22)), frame(0x80 | ord('R'), b'\x00' + bytes(22))])
        c2 = DongleClient(s2)
        try:
            got2 = await c2.read_gatt_char(v12_ble.STATUS)
            assert len(got2) == 22 and len(s2.writes) == 2, (len(got2), len(s2.writes))
        finally:
            c2.close()

        # 3) C6 卡死（首次 Q 超时）-> 自动硬复位重开串口 -> 第二次 Q 成功应答
        ports = [FakeSer([None]), FakeSer([frame(0x80 | ord('Q'), b'\x00')])]
        resets = []
        ser_ok, cli_ok = await open_ready_dongle(
            '/dev/cu.fake', lambda _: ports.pop(0),
            reset_fn=lambda s, p: (resets.append(p), hard_reset_dongle(s, __file__, sleep=lambda _: None)),
            cmd_timeout=0.03)
        try:
            assert resets == ['/dev/cu.fake'] and not ser_ok.closed
        finally:
            cli_ok.close(); ser_ok.close()

        # 4) C6 两次 Q 均超时 -> 抛明确 RuntimeError 且关闭串口
        dead_ports = [FakeSer([None]), FakeSer([None])]
        try:
            await open_ready_dongle('/dev/cu.dead', lambda _: dead_ports.pop(0),
                                    reset_fn=lambda s, p: s.close(), cmd_timeout=0.03)
        except RuntimeError as err:
            assert '自动硬复位后仍未恢复' in str(err), err
        else:
            raise AssertionError('两次 Q 超时未抛 RuntimeError')

        # 5) C08B STATUS v1 (64B) 单次直读不重读，以及 22B -> 64B 截断重读恢复
        s5 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(64))])
        c5 = DongleClient(s5)
        try:
            got5 = await c5.read_gatt_char(v12_ble.STATUS)
            assert len(got5) == 64 and len(s5.writes) == 1, (len(got5), len(s5.writes))
        finally:
            c5.close()
        s6 = FakeSer([frame(0x80 | ord('R'), b'\x00' + bytes(22)), frame(0x80 | ord('R'), b'\x00' + bytes(64))])
        c6 = DongleClient(s6)
        try:
            got6 = await c6.read_gatt_char(v12_ble.STATUS)
            assert len(got6) == 64 and len(s6.writes) == 2, (len(got6), len(s6.writes))
        finally:
            c6.close()

        # 6) DATA (kind=2) + IMU_DATA (kind=6) 双流通知独立派发与取消订阅，以及非法特征必败反例
        s7 = FakeSer([])
        c7 = DongleClient(s7)
        try:
            svc = c7.services.get_service(v12_ble.SERVICE)
            assert IMU_DATA in {ch.uuid for ch in svc.characteristics}
            seen = []
            await c7.start_notify(v12_ble.DATA, lambda u, v: seen.append(('adc', u, bytes(v))))
            await c7.start_notify(IMU_DATA, lambda u, v: seen.append(('imu', u, bytes(v))))
            try:
                await c7.start_notify(v12_ble.META, lambda *_: None)
            except ValueError:
                pass
            else:
                raise AssertionError('对 META 调用 start_notify 未报错')
            s7.rx += frame(2, b'emg1') + frame(6, b'imu1')
            for _ in range(40):
                await asyncio.sleep(0.005)
                if len(seen) >= 2:
                    break
            assert seen == [('adc', v12_ble.DATA, b'emg1'), ('imu', IMU_DATA, b'imu1')], seen
            await c7.stop_notify(IMU_DATA)
            s7.rx += frame(6, b'imu2') + frame(2, b'emg2')
            for _ in range(40):
                await asyncio.sleep(0.005)
                if len(seen) >= 3:
                    break
            assert seen[-1] == ('adc', v12_ble.DATA, b'emg2') and len(seen) == 3, seen
        finally:
            c7.close()

    asyncio.run(check_async())
    print('selftest 通过：切帧、垃圾前缀、分块、超长错位、STATUS(64/136/163B) 截断重读、DATA+IMU 双流通知、接收器硬复位恢复')


def main():
    if sys.argv[1:] == ['selftest']:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', required=True)
    ap.add_argument('--mode', choices=list(v12_ble.COMMANDS), required=True)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--expected', required=True, help='R01 固件构建 ID')
    ap.add_argument('--out', required=True)
    asyncio.run(run(ap.parse_args()))


if __name__ == '__main__':
    main()
